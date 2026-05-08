<template>
  <div class="app-container">
    <div class="page-header">
      <h2>细胞库存查询</h2>
      <div class="header-actions">
        <el-button type="primary" @click="fetchData" :loading="loading">
          刷新数据
        </el-button>
      </div>
    </div>

    <div class="function-bar">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索靶点"
        clearable
        style="width: 200px"
      />
      <div class="function-switches">
        <el-switch
          v-model="mergeSameName"
          active-text="细胞同名合并"
        />
        <el-switch
          v-model="sortByStock"
          active-text="按库存排序"
        />
        <el-switch
          v-model="collapseByGenus"
          active-text="按种属折叠"
        />
      </div>
    </div>

    <div class="three-column-layout" v-loading="loading">
      <div class="column target-column">
        <div class="column-header">
          <h3>靶点列表</h3>
          <el-tag>{{ filteredTargets.length }} 个靶点</el-tag>
        </div>
        <div class="target-list">
          <div v-if="groupedTargets.group1.length > 0" class="target-group">
            <div class="group-header">
              <span>项目库靶点</span>
              <el-tag size="small" type="info">{{ groupedTargets.group1.length }}</el-tag>
            </div>
            <div
              v-for="target in groupedTargets.group1"
              :key="target.name"
              class="target-item"
              :class="{ active: selectedTarget === target.name }"
              @click="selectTarget(target.name)"
            >
              <div class="target-name">{{ target.name }}</div>
              <div v-if="target.projectCount > 0" class="target-meta">
                <el-tag size="small" type="info">{{ target.projectCount }} 个项目</el-tag>
                <el-tag 
                  v-if="targetStockStatusMap.statusMap[target.name] === 'danger'" 
                  size="small" 
                  type="danger"
                >
                  缺货
                </el-tag>
                <el-tag 
                  v-if="targetStockStatusMap.statusMap[target.name] === 'warning'" 
                  size="small" 
                  type="warning"
                >
                  预警
                </el-tag>
              </div>
            </div>
          </div>
          <div v-if="groupedTargets.group2.length > 0" class="target-group">
            <div class="group-header" @click="group2Expanded = !group2Expanded">
              <span>其他靶点</span>
              <div class="group-header-right">
                <el-tag size="small" type="info">{{ groupedTargets.group2.length }}</el-tag>
                <el-icon>
                  <ArrowUp v-if="group2Expanded" />
                  <ArrowDown v-else />
                </el-icon>
              </div>
            </div>
            <div v-show="group2Expanded">
              <div
                v-for="target in groupedTargets.group2"
                :key="target.name"
                class="target-item"
                :class="{ active: selectedTarget === target.name }"
                @click="selectTarget(target.name)"
              >
                <div class="target-name">{{ target.name }}</div>
                <div v-if="target.projectCount > 0" class="target-meta">
                  <el-tag size="small" type="info">{{ target.projectCount }} 个项目</el-tag>
                  <el-tag 
                    v-if="targetStockStatusMap.statusMap[target.name] === 'danger'" 
                    size="small" 
                    type="danger"
                  >
                    缺货
                  </el-tag>
                  <el-tag 
                    v-if="targetStockStatusMap.statusMap[target.name] === 'warning'" 
                    size="small" 
                    type="warning"
                  >
                    预警
                  </el-tag>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="column project-column">
        <div class="column-header">
          <h3>项目进度</h3>
          <el-tag v-if="selectedTarget">{{ filteredProjects.length }} 个项目</el-tag>
        </div>
        <div class="project-list">
          <div v-if="!selectedTarget" class="empty-tip">
            请选择靶点查看项目信息
          </div>
          
          <div v-if="waitingProjects.length > 0">
            <div class="project-section-header">
              <span>待制备项目</span>
              <el-tag size="small">{{ waitingProjects.length }}</el-tag>
            </div>
            <div
              v-for="project in waitingProjects"
              :key="project.experiment_id"
              class="project-item"
            >
              <div class="project-info">
                <el-tooltip :content="project.project_name" placement="top" :disabled="!project.project_name || project.project_name.length <= 20">
                  <div class="project-name">{{ project.project_name }}</div>
                </el-tooltip>
                <div class="project-meta">
                  <span class="project-code">{{ project.project_code }}</span>
                  <span v-if="project.start_date" class="project-date">{{ project.start_date }}</span>
                  <span v-if="project.owner" class="project-owner">{{ project.owner }}</span>
                  <span v-if="project.prep_status === '已制备'" class="project-prep">已制备</span>
                </div>
              </div>
              <div class="project-status">
                <el-tag
                  :type="project.prepared ? 'success' : getStatusType(project.project_status)"
                  :class="{ 'no-permission-tag': !canUpdatePrepStatus(project) }"
                  :title="!canUpdatePrepStatus(project) ? '您没有权限更新制备状态' : ''"
                  @click="toggleProjectPrepStatus(project)"
                  :style="canUpdatePrepStatus(project) ? 'cursor: pointer' : 'cursor: not-allowed'"
                >
                  {{ project.project_status }}
                </el-tag>
              </div>
            </div>
          </div>
          
          <div v-if="otherProjects.length > 0">
            <div class="project-section-header" @click="collapseOtherProjects = !collapseOtherProjects" style="cursor: pointer">
              <span>其他项目</span>
              <el-tag size="small">{{ otherProjects.length }}</el-tag>
              <el-icon style="margin-left: auto">
                <ArrowRight v-if="collapseOtherProjects" />
                <ArrowDown v-else />
              </el-icon>
            </div>
            <div v-show="!collapseOtherProjects">
              <div
                v-for="project in otherProjects"
                :key="project.experiment_id"
                class="project-item"
              >
                <div class="project-info">
                  <el-tooltip :content="project.project_name" placement="top" :disabled="!project.project_name || project.project_name.length <= 20">
                    <div class="project-name">{{ project.project_name }}</div>
                  </el-tooltip>
                  <div class="project-meta">
                    <span class="project-code">{{ project.project_code }}</span>
                    <span v-if="project.start_date" class="project-date">{{ project.start_date }}</span>
                    <span v-if="project.owner" class="project-owner">{{ project.owner }}</span>
                    <span v-if="project.prep_status === '已制备'" class="project-prep">已制备</span>
                  </div>
                </div>
                <div class="project-status">
                  <el-tag
                    :type="project.prepared ? 'success' : getStatusType(project.project_status)"
                    :class="{ 'no-permission-tag': !canUpdatePrepStatus(project) }"
                    :title="!canUpdatePrepStatus(project) ? '您没有权限更新制备状态' : ''"
                    @click="toggleProjectPrepStatus(project)"
                    :style="canUpdatePrepStatus(project) ? 'cursor: pointer' : 'cursor: not-allowed'"
                  >
                    {{ project.project_status }}
                  </el-tag>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="column cell-column">
        <div class="column-header">
          <h3>细胞库存</h3>
          <div v-if="selectedTarget" class="cell-stats">
            <el-tag v-if="overallStockStatus === 'danger'" type="danger">缺货</el-tag>
            <el-tag v-if="totalDemand > 0 && overallStockStatus !== 'success'" type="warning">需求量{{ eligibleProjects.length }}*4*{{ demandPerProject }}={{ totalDemand }}</el-tag>
            <el-tag v-if="overallStockStatus === 'success'" type="success">库存充足</el-tag>
            <el-tag type="success">{{ currentTotalStock }} 支</el-tag>
            <el-tag type="info">{{ currentCells.length }} 批次</el-tag>
          </div>
        </div>
        <div class="cell-list">
          <div v-if="!selectedTarget" class="empty-tip">
            请选择靶点查看细胞库存
          </div>
          <div v-else>
            <div
              v-for="(cells, genus) in groupedCells"
              :key="genus"
              class="genus-group"
            >
              <div class="genus-header">
                <strong>{{ genus }}</strong>
                <div class="genus-stats">
                  <el-tag v-if="genusDemand[genus] && genusDemand[genus] > 0" size="small" :type="genusStockStatus[genus]">需求{{ genusDemand[genus] }}</el-tag>
                  <el-tag size="small" type="success">存量{{ calculateGenusStock(cells) }}</el-tag>
                  <el-tag size="small">{{ cells.length }} {{ mergeSameName ? '个名称' : '个批次' }}</el-tag>
                </div>
              </div>
              <div class="cell-items" v-show="!collapseByGenus">
                <template v-if="cells.length > 0">
                  <template v-if="!mergeSameName">
                    <div
                      v-for="cell in cells"
                      :key="cell.id"
                      class="cell-item"
                    >
                      <div class="cell-info">
                        <div class="cell-name">{{ cell.samplename }}</div>
                        <div class="cell-details">
                          <span>批号: {{ cell.batch_no }}</span>
                          <span v-if="cell.generations">代次: {{ cell.generations }}</span>
                        </div>
                      </div>
                      <div class="cell-volume">
                        <el-tag type="success">
                          {{ cell.sample_storage_vol }} {{ getUnit(cell) }}
                        </el-tag>
                      </div>
                    </div>
                  </template>
                  <template v-else>
                    <div
                      v-for="mergedCell in cells"
                      :key="mergedCell.samplename"
                      class="cell-item"
                    >
                      <div class="cell-info">
                        <div class="cell-name">{{ mergedCell.samplename }}</div>
                        <div class="cell-details">
                          <el-tooltip :content="mergedCell.batches.join(', ')" placement="top" :disabled="mergedCell.batches.join(', ').length <= 30">
                            <span class="text-ellipsis">批号: {{ mergedCell.batches.join(', ') }}</span>
                          </el-tooltip>
                          <el-tooltip v-if="mergedCell.generations && mergedCell.generations.length > 0" :content="mergedCell.generations.join(', ')" placement="top" :disabled="mergedCell.generations.join(', ').length <= 30">
                            <span class="text-ellipsis">代次: {{ mergedCell.generations.join(', ') }}</span>
                          </el-tooltip>
                        </div>
                      </div>
                      <div class="cell-volume">
                        <el-tag type="info">
                          {{ mergedCell.batchCount }} 批次
                        </el-tag>
                        <el-tag type="success">
                          {{ mergedCell.totalStock }} 支
                        </el-tag>
                      </div>
                    </div>
                  </template>
                </template>
                <div v-else class="cell-item empty">
                  <div class="cell-info">
                    <div class="cell-name">暂无库存</div>
                  </div>
                </div>
              </div>
              <div class="cell-items collapsed" v-show="collapseByGenus">
                <div class="cell-item">
                  <div class="cell-info">
                    <div class="cell-name">{{ getTopStockCellName(cells) || '暂无库存' }}</div>
                    <div v-if="cells.length > 0" class="cell-details">
                      <span class="text-ellipsis">批号: {{ getMergedBatches(cells).join(', ') }}</span>
                      <span v-if="getMergedGenerations(cells).length > 0" class="text-ellipsis">代次: {{ getMergedGenerations(cells).join(', ') }}</span>
                    </div>
                  </div>
                  <div v-if="cells.length > 0" class="cell-volume">
                    <el-tag type="info">{{ getUniqueCellCount(cells) }} 种</el-tag>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <el-alert
      v-if="error"
      :title="'错误: ' + error"
      type="error"
      show-icon
      style="margin-top: 20px"
    />
  </div>
</template>

<script>
import { useUserStore } from '@vben/stores'

import {
  ArrowDown,
  ArrowRight,
  ArrowUp,
} from '@element-plus/icons-vue'
import {
  ElAlert,
  ElButton,
  ElIcon,
  ElInput,
  ElMessage,
  ElSwitch,
  ElTag,
  ElTooltip,
} from 'element-plus'

import request from '#/utils/request'
import { canUpdateSerumPrepStatus } from '#/utils/serumPermission'

export default {
  name: 'SerumCell',
  components: {
    ArrowDown,
    ArrowRight,
    ArrowUp,
    ElAlert,
    ElButton,
    ElIcon,
    ElInput,
    ElSwitch,
    ElTag,
    ElTooltip,
  },
  setup() {
    const userStore = useUserStore()
    return {
      userStore,
    }
  },
  data() {
    return {
      loading: false,
      targets: [],
      projects: {},
      cells: {},
      selectedTarget: null,
      error: null,
      searchKeyword: '',
      mergeSameName: false,
      sortByStock: false,
      group2Expanded: false,
      collapseByGenus: false,
      demandPerProject: 60,
      preparedProjects: [],
      collapseOtherProjects: true
    }
  },
  computed: {
    currentUserInfo() {
      return this.userStore.userInfo || {}
    },
    cellTargets() {
      const allTargets = new Set()
      
      Object.keys(this.cells).forEach(targetName => {
        allTargets.add(targetName)
      })
      
      this.targets.forEach(target => {
        allTargets.add(target.name)
      })
      
      return Array.from(allTargets).map(targetName => ({
        name: targetName,
        isFromProject: this.targets.some(t => t.name === targetName),
        hasCells: this.cells[targetName] && this.cells[targetName].length > 0,
        projectCount: this.calculateProjectCount(targetName)
      }))
    },
    targetStockStatusMap() {
      const statusMap = {}
      const stockMap = {}
      const fixedGenusOrder = ['hum', 'mus', 'dog', 'fas']
      
      this.cellTargets.filter(t => t.isFromProject).forEach(target => {
        const targetName = target.name
        const cells = this.cells[targetName] || []
        const projectCount = this.getTargetEligibleProjectCount(targetName)
        
        if (projectCount === 0) {
          statusMap[targetName] = 'success'
          stockMap[targetName] = cells.reduce((sum, cell) => sum + (cell.sample_storage_vol || 0), 0)
          return
        }
        
        if (cells.length === 0) {
          statusMap[targetName] = 'danger'
          stockMap[targetName] = 0
          return
        }
        
        const genusStock = {}
        fixedGenusOrder.forEach(genus => {
          genusStock[genus] = 0
        })
        
        cells.forEach(cell => {
          const genus = cell.genus
          if (fixedGenusOrder.includes(genus)) {
            genusStock[genus] += (cell.sample_storage_vol || 0)
          }
        })
        
        const demandPerGenus = projectCount * this.demandPerProject
        const hasDanger = fixedGenusOrder.some(genus => genusStock[genus] < demandPerGenus)
        const hasWarning = fixedGenusOrder.some(genus => genusStock[genus] >= demandPerGenus && genusStock[genus] < demandPerGenus * 1.2)
        
        if (hasDanger) {
          statusMap[targetName] = 'danger'
        } else if (hasWarning) {
          statusMap[targetName] = 'warning'
        } else {
          statusMap[targetName] = 'success'
        }
        
        stockMap[targetName] = cells.reduce((sum, cell) => sum + (cell.sample_storage_vol || 0), 0)
      })
      
      return { statusMap, stockMap }
    },
    currentTotalStock() {
      if (!this.selectedTarget) return 0
      const cells = this.cells[this.selectedTarget] || []
      return cells.reduce((sum, cell) => sum + (cell.sample_storage_vol || 0), 0)
    },
    filteredTargets() {
      let targets = [...this.cellTargets]
      if (this.searchKeyword) {
        targets = targets.filter(t => 
          t.name.toLowerCase().includes(this.searchKeyword.toLowerCase())
        )
      }
      if (this.sortByStock) {
        const { statusMap, stockMap } = this.targetStockStatusMap
        targets.sort((a, b) => {
          const statusA = statusMap[a.name] || 'success'
          const statusB = statusMap[b.name] || 'success'
          
          const statusPriority = { 'danger': 0, 'warning': 1, 'success': 2 }
          const priorityA = statusPriority[statusA]
          const priorityB = statusPriority[statusB]
          
          if (priorityA !== priorityB) {
            return priorityA - priorityB
          }
          
          const stockA = stockMap[a.name] || 0
          const stockB = stockMap[b.name] || 0
          return stockA - stockB
        })
      } else {
        targets.sort((a, b) => a.name.localeCompare(b.name))
      }
      return targets
    },
    groupedTargets() {
      const group1 = this.filteredTargets.filter(t => t.isFromProject)
      const group2 = this.filteredTargets.filter(t => !t.isFromProject)
      return { group1, group2 }
    },
    currentProjects() {
      if (!this.selectedTarget) return []
      return this.projects[this.selectedTarget] || []
    },
    filteredProjects() {
      return this.currentProjects
    },
    waitingProjects() {
      return this.currentProjects.filter(project => {
        const status = project.project_status || ''
        if (!status) return false
        return status.includes('待一免') || status.includes('待二免') || status.includes('待三免') || status.includes('待四免') || status.includes('待五免') || status.includes('待六免') || status.includes('待七免') || status.includes('待八免') || status.includes('待九免') || status.includes('待十免')
      })
    },
    otherProjects() {
      return this.currentProjects.filter(project => {
        const status = project.project_status || ''
        if (!status) return true
        return !status.includes('待一免') && !status.includes('待二免') && !status.includes('待三免') && !status.includes('待四免') && !status.includes('待五免') && !status.includes('待六免') && !status.includes('待七免') && !status.includes('待八免') && !status.includes('待九免') && !status.includes('待十免')
      })
    },
    eligibleProjects() {
      return this.currentProjects.filter(project => {
        if (this.preparedProjects.includes(project.experiment_id)) {
          return false
        }
        const status = project.project_status || ''
        if (!status) return false
        return status.includes('待三免') || status.includes('待四免') || status.includes('待五免') || status.includes('待六免') || status.includes('待七免') || status.includes('待八免') || status.includes('待九免') || status.includes('待十免')
      })
    },
    totalDemand() {
      const projectCount = this.eligibleProjects.length
      return projectCount * 4 * this.demandPerProject
    },
    genusDemand() {
      const projectCount = this.eligibleProjects.length
      const demandPerGenus = projectCount * this.demandPerProject
      return {
        'hum': demandPerGenus,
        'mus': demandPerGenus,
        'dog': demandPerGenus,
        'fas': demandPerGenus
      }
    },
    genusStockStatus() {
      const genusStock = this.calculateAllGenusStock(this.groupedCells)
      const demand = this.genusDemand
      const status = {}
      for (const genus in demand) {
        const stock = genusStock[genus] || 0
        const demandValue = demand[genus]
        if (stock < demandValue) {
          status[genus] = 'danger'
        } else if (stock < demandValue * 1.2) {
          status[genus] = 'warning'
        } else {
          status[genus] = 'success'
        }
      }
      return status
    },
    overallStockStatus() {
      const status = this.genusStockStatus
      const hasDanger = Object.values(status).some(s => s === 'danger')
      const hasWarning = Object.values(status).some(s => s === 'warning')
      if (hasDanger) return 'danger'
      if (hasWarning) return 'warning'
      return 'success'
    },
    currentCells() {
      if (!this.selectedTarget) return []
      return this.cells[this.selectedTarget] || []
    },
    groupedCells() {
      const fixedGenusOrder = ['hum', 'mus', 'dog', 'fas']
      const grouped = {}
      
      if (!this.mergeSameName) {
        this.currentCells.forEach(cell => {
          const genus = cell.genus || '未知'
          if (!grouped[genus]) {
            grouped[genus] = []
          }
          grouped[genus].push(cell)
        })
      } else {
        this.currentCells.forEach(cell => {
          const genus = cell.genus || '未知'
          const samplename = cell.samplename || '未知'
          if (!grouped[genus]) {
            grouped[genus] = {}
          }
          if (!grouped[genus][samplename]) {
            grouped[genus][samplename] = {
              samplename,
              genus,
              batches: [],
              generations: [],
              totalStock: 0,
              batchCount: 0
            }
          }
          grouped[genus][samplename].batches.push(cell.batch_no)
          if (cell.generations) {
            grouped[genus][samplename].generations.push(cell.generations)
          }
          grouped[genus][samplename].totalStock += cell.sample_storage_vol || 0
          grouped[genus][samplename].batchCount += 1
        })
        
        for (const genus in grouped) {
          if (typeof grouped[genus] === 'object') {
            grouped[genus] = Object.values(grouped[genus])
          }
        }
      }
      
      const result = {}
      fixedGenusOrder.forEach(genus => {
        if (grouped[genus]) {
          result[genus] = grouped[genus]
        } else {
          result[genus] = []
        }
      })
      
      for (const genus in grouped) {
        if (!result[genus]) {
          result[genus] = grouped[genus]
        }
      }
      
      return result
    }
  },
  mounted() {
    this.fetchData()
  },
  methods: {
    getTargetEligibleProjectCount(targetName) {
      const projects = this.projects[targetName] || []
      return projects.filter(project => {
        if (this.preparedProjects.includes(project.experiment_id)) {
          return false
        }
        const status = project.project_status || ''
        if (!status) return false
        return status.includes('待三免') || status.includes('待四免') || status.includes('待五免') || 
               status.includes('待六免') || status.includes('待七免') || status.includes('待八免') || 
               status.includes('待九免') || status.includes('待十免')
      }).length
    },
    calculateProjectCount(targetName) {
      const projects = this.projects[targetName] || []
      return projects.length
    },
    async fetchData() {
      this.loading = true
      this.error = null
      try {
        const response = await request({
          url: '/serum/cell_inventory/data',
          method: 'get'
        })
        
        if (response.code === 20000) {
          this.targets = response.data.targets || []
          this.projects = response.data.projects || {}
          this.cells = response.data.cells || {}
          
          this.preparedProjects = []
          for (const targetName in this.projects) {
            this.projects[targetName].forEach(project => {
              project.prepared = project.prep_status === '已制备'
              if (project.prepared) {
                this.preparedProjects.push(project.experiment_id)
              }
            })
          }
          
          if (this.targets.length > 0 && !this.selectedTarget) {
            this.selectedTarget = this.targets[0].name
          }
          
          ElMessage.success('数据加载成功')
        } else {
          this.error = '数据加载失败'
          ElMessage.error('数据加载失败')
        }
      } catch (error) {
        console.error('加载数据失败:', error)
        this.error = error.message || '网络请求失败'
        ElMessage.error('网络请求失败')
      } finally {
        this.loading = false
      }
    },
    selectTarget(targetName) {
      this.selectedTarget = targetName
    },
    async toggleProjectPrepStatus(project) {
      if (!this.canUpdatePrepStatus(project)) {
        ElMessage.warning('您没有权限更新制备状态')
        return
      }
      const newStatus = !project.prepared
      try {
        const response = await request({
          url: '/serum/project/prep_status',
          method: 'post',
          data: {
            experiment_id: project.experiment_id,
            prep_status: newStatus ? '已制备' : ''
          }
        })
        
        if (response.code === 20000) {
          project.prepared = newStatus
          project.prep_status = newStatus ? '已制备' : ''
          if (newStatus) {
            if (!this.preparedProjects.includes(project.experiment_id)) {
              this.preparedProjects.push(project.experiment_id)
            }
          } else {
            const index = this.preparedProjects.indexOf(project.experiment_id)
            if (index > -1) {
              this.preparedProjects.splice(index, 1)
            }
          }
          ElMessage.success('制备状态更新成功')
        } else {
          ElMessage.error('制备状态更新失败')
        }
      } catch (error) {
        console.error('更新制备状态失败:', error)
        ElMessage.error('网络请求失败')
      }
    },
    getStatusType(status) {
      if (!status) return 'info'
      if (status.includes('待三免') || status.includes('待四免') || status.includes('待五免') || status.includes('待六免') || status.includes('待七免') || status.includes('待八免') || status.includes('待九免') || status.includes('待十免')) return 'warning'
      return 'info'
    },
    canUpdatePrepStatus(project) {
      return canUpdateSerumPrepStatus(this.currentUserInfo, project)
    },
    calculateGenusStock(cells) {
      if (!cells || cells.length === 0) return 0
      return cells.reduce((sum, cell) => {
        if (this.mergeSameName) {
          return sum + (cell.totalStock || 0)
        } else {
          return sum + (cell.sample_storage_vol || 0)
        }
      }, 0)
    },
    calculateAllGenusStock(groupedCells) {
      const stock = {}
      for (const genus in groupedCells) {
        stock[genus] = this.calculateGenusStock(groupedCells[genus])
      }
      return stock
    },
    getTopStockCellName(cells) {
      if (!cells || cells.length === 0) return ''
      let topCell = null
      let maxStock = 0
      cells.forEach(cell => {
        const stock = this.mergeSameName ? (cell.totalStock || 0) : (cell.sample_storage_vol || 0)
        if (stock > maxStock) {
          maxStock = stock
          topCell = cell
        }
      })
      return topCell ? topCell.samplename : ''
    },
    getUniqueCellCount(cells) {
      if (!cells || cells.length === 0) return 0
      const uniqueNames = new Set()
      cells.forEach(cell => {
        if (cell.samplename) {
          uniqueNames.add(cell.samplename)
        }
      })
      return uniqueNames.size
    },
    mergeField(cells, arrayField, stringField) {
      if (!cells || cells.length === 0) return []
      const result = new Set()
      cells.forEach(cell => {
        if (Array.isArray(cell[arrayField])) {
          cell[arrayField].forEach(item => item && result.add(item))
          return
        }
        if (cell[stringField]) {
          result.add(cell[stringField])
        }
      })
      return Array.from(result)
    },
    getMergedBatches(cells) {
      return this.mergeField(cells, 'batches', 'batch_no')
    },
    getMergedGenerations(cells) {
      return this.mergeField(cells, 'generations', 'generations')
    },
    getUnit(cell) {
      return cell.sample_unit || '支'
    }
  }
}
</script>

<style scoped>
.app-container {
  padding: 20px;
  min-height: 100vh;
  background: #fff;
}

/* Page-local small tag semantics: Element UI mini ~= Element Plus small. */
.app-container :deep(.el-tag--small) {
  height: 20px;
  padding: 0 5px;
  font-size: 12px;
  line-height: 19px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18px;
}

.page-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 500;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.function-bar {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 16px 16px;
  background: #f5f7fa;
  border-radius: 5px;
  margin-bottom: 16px;
  font-size: 16px;
}

.function-switches {
  display: flex;
  gap: 20px;
  align-items: center;
}

.three-column-layout {
  display: flex;
  gap: 20px;
  height: calc(100vh - 200px);
  min-height: 500px;
}

.column {
  flex: 1;
  display: flex;
  flex-direction: column;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background: #fff;
  overflow: hidden;
}

.target-column {
  flex: 0 0 200px;
}

.project-column {
  flex: 0 0 350px;
}

.cell-column {
  flex: 1;
}

.cell-volume {
  display: flex;
  gap: 8px;
  align-items: center;
}

.cell-volume .el-tag {
  min-width: 60px;
  text-align: center;
}

.cell-stats {
  display: flex;
  gap: 8px;
  align-items: center;
}

.cell-stats .el-tag {
  min-width: 60px;
  text-align: center;
}

.genus-stats {
  display: flex;
  gap: 8px;
  align-items: center;
}

.genus-stats .el-tag {
  min-width: 60px;
  text-align: center;
}

.target-meta {
  display: flex;
  gap: 8px;
  align-items: center;
}

.target-meta .el-tag {
  min-width: 60px;
  text-align: center;
}

.column-header {
  padding: 15px;
  border-bottom: 1px solid #ebeef5;
  background: #f5f7fa;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.column-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
}

.target-list,
.project-list,
.cell-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

.target-item {
  padding: 12px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
  margin-bottom: 8px;
  border: 1px solid #ebeef5;
}

.target-item:hover {
  background: #f5f7fa;
  border-color: #409eff;
}

.target-item.active {
  background: #ecf5ff;
  border-color: #409eff;
}

.target-name {
  font-weight: 500;
  margin-bottom: 8px;
  color: #303133;
}

.project-item {
  padding: 12px;
  border-radius: 4px;
  margin-bottom: 8px;
  border: 1px solid #ebeef5;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.project-info {
  flex: 1;
  min-width: 0;
}

.project-name {
  font-weight: 500;
  color: #303133;
  margin-bottom: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.project-code {
  font-size: 12px;
  color: #909399;
}

.project-date {
  font-size: 12px;
  color: #67c23a;
}

.project-owner {
  font-size: 12px;
  color: #409eff;
}

.project-prep {
  font-size: 12px;
  color: #67c23a;
  font-weight: 500;
}

.no-permission-tag {
  opacity: 0.65;
}

.project-section-header {
  padding: 10px 12px;
  background: #f5f7fa;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 500;
  color: #606266;
  margin-bottom: 8px;
}

.genus-group {
  margin-bottom: 20px;
}

.genus-header {
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: #f5f7fa;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  color: #606266;
  margin-bottom: 8px;
}

.group-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.cell-items {
  padding-left: 10px;
}

.cell-item {
  padding: 12px;
  border-radius: 4px;
  margin-bottom: 8px;
  border: 1px solid #ebeef5;
  display: flex;
  align-items: center;
}

.cell-info {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.cell-name {
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.text-ellipsis {
  display: inline-block;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cell-details {
  font-size: 12px;
  color: #909399;
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
}

.cell-details span {
  margin-right: 15px;
}

.empty-tip {
  text-align: center;
  color: #909399;
  padding: 40px 20px;
  font-size: 14px;
}

.cell-volume .el-tag:not(.el-tag--small) {
  height: 24px;
  line-height: 22px;
}

.cell-volume .el-tag--small {
  height: 20px;
  line-height: 19px;
}

::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-track {
  background: #f1f1f1;
}

::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>
