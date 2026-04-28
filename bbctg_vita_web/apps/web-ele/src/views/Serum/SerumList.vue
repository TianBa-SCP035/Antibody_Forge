<template>
  <div class="app-container">
    <!-- Advanced Ops: slide down overlay -->
    <transition name="ops-slide">
      <div v-show="showAdvancedOps" class="advanced-ops-bar">
        <div class="ops-bar-header">
          <div class="ops-title">
            <el-icon style="margin-right:6px;"><Tools /></el-icon>
            高级操作
          </div>

          <el-button type="text" :icon="Close" @click="showAdvancedOps = false" />
        </div>

        <div class="ops-actions">
          <el-button type="primary" :icon="Search" @click="handleCellInventory">
            细胞库存查询
          </el-button>
        </div>
      </div>
    </transition>

    <!-- Dashboard / Overview -->
    <el-row :gutter="20" class="panel-group">
      <!-- Total: Pie Chart Trigger -->
      <el-col :xs="12" :sm="12" :lg="6" class="card-panel-col">
        <div class="card-panel blue-panel" @click="handleTotalClick">
          <div class="card-panel-icon-wrapper icon-people">
            <el-icon class="card-panel-icon"><DataAnalysis /></el-icon>
          </div>
          <div class="card-panel-description">
            <div class="card-panel-text">实验总数</div>
            <div class="card-panel-num">{{ stats.total }}</div>
          </div>
        </div>
      </el-col>
      <!-- Ongoing: Filter Trigger -->
      <el-col :xs="12" :sm="12" :lg="6" class="card-panel-col">
        <div class="card-panel green-panel" :class="{'active-card': listQuery.project_status === 'ongoing'}" @click="handleStatusFilter('ongoing')">
          <div class="card-panel-icon-wrapper icon-message">
            <el-icon class="card-panel-icon"><Timer /></el-icon>
          </div>
          <div class="card-panel-description">
            <div class="card-panel-text">进行中</div>
            <div class="card-panel-num">{{ stats.status_counts.ongoing || 0 }}</div>
          </div>
        </div>
      </el-col>
      <!-- Completed: Filter Trigger -->
      <el-col :xs="12" :sm="12" :lg="6" class="card-panel-col">
        <div class="card-panel red-panel" :class="{'active-card': listQuery.project_status === 'completed'}" @click="handleStatusFilter('completed')">
          <div class="card-panel-icon-wrapper icon-money">
            <el-icon class="card-panel-icon"><CircleCheck /></el-icon>
          </div>
          <div class="card-panel-description">
            <div class="card-panel-text">已完成</div>
            <div class="card-panel-num">{{ stats.status_counts.completed || 0 }}</div>
          </div>
        </div>
      </el-col>
      <!-- Owner: User Filter Trigger -->
      <el-col :xs="12" :sm="12" :lg="6" class="card-panel-col">
        <div class="card-panel orange-panel" :class="{'active-card': listQuery.owner === currentOwnerName}" @click="handleOwnerFilter(currentOwnerName)">
          <div class="card-panel-icon-wrapper icon-shopping">
            <el-icon class="card-panel-icon"><UserFilled /></el-icon>
          </div>
          <div class="card-panel-description">
            <div class="card-panel-text">负责人</div>
            <!-- Displaying mock count for '王申森' or total owners? Use distinct owners count or specific user count if available. 
                 User asked for "number of admin users". Let's show distinct owner count for now. -->
            <div class="card-panel-num">{{ stats.owner_counts.length }}</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- Filter Header -->
    <div class="filter-wrapper">
        <el-row :gutter="15" type="flex" align="middle" style="flex-wrap: wrap;">
            <el-col :span="4">
               <el-input v-model="listQuery.project_code" placeholder="项目编号" class="filter-item" @keyup.enter="handleFilter" clearable :prefix-icon="Search" />
            </el-col>
            <el-col :span="4">
                <el-input v-model="listQuery.project_name" placeholder="项目名称" class="filter-item" @keyup.enter="handleFilter" clearable :prefix-icon="Search" />
            </el-col>
            <el-col :span="3">
                 <el-select 
                      v-model="listQuery.target_name" 
                      placeholder="靶点" 
                      clearable 
                      filterable 
                      :filter-method="q => setFilterQuery('target', q)"
                      @clear="setFilterQuery('target', '')"
                      style="width: 100%" 
                      @change="handleFilter">
                      <el-option v-for="item in filterOptions(allTargetOptions, targetFilterQuery)" :key="item" :label="item" :value="item" />
                  </el-select>
            </el-col>
            <el-col :span="3">
                 <el-select 
                      v-model="listQuery.owner" 
                      placeholder="负责人" 
                      clearable 
                      filterable 
                      :filter-method="q => setFilterQuery('owner', q)"
                      @clear="setFilterQuery('owner', '')"
                      style="width: 100%" 
                      @change="handleFilter">
                      <el-option v-for="item in filterOptions(allOwnerOptions, ownerFilterQuery)" :key="item" :label="item" :value="item" />
                  </el-select>
            </el-col>
             <el-col :span="5">
                <el-date-picker
                  v-model="dateRange"
                  type="daterange"
                  range-separator="至"
                  start-placeholder="开始"
                  end-placeholder="结束"
                  style="width: 100%;"
                  format="yyyy-MM-dd"
                  value-format="yyyy-MM-dd">
                </el-date-picker>
            </el-col>
            <el-col :span="1" style="text-align: center;">
                <span class="more-toggle-btn" title="看不见我" @click="toggleAdvanced">
                  <el-icon>
                    <ArrowUp v-if="showAdvancedFilters" />
                    <ArrowDown v-else />
                  </el-icon>
                </span>
            </el-col>
            <el-col :span="4" style="text-align: right;">
                <el-button type="primary" :icon="Search" @click="handleFilter">查询</el-button>
                <el-button type="success" :icon="Plus" @click="handleCreate">新建</el-button>
            </el-col>
        </el-row>
        <el-collapse-transition>
          <div v-show="showAdvancedFilters" class="advanced-filters">
            <el-row :gutter="15" type="flex" align="middle" style="flex-wrap: wrap;">
              <el-col :span="4">
                 <el-select 
                      v-model="listQuery.study_type" 
                      placeholder="课题类型" 
                      clearable 
                      filterable 
                      :filter-method="q => setFilterQuery('studyType', q)"
                      @clear="setFilterQuery('studyType', '')"
                      style="width: 100%" 
                      @change="handleFilter">
                      <el-option v-for="item in filterOptions(allStudyTypeOptions, studyTypeFilterQuery)" :key="item" :label="item" :value="item" />
                  </el-select>
              </el-col>
              <el-col :span="4">
                 <el-select 
                      v-model="listQuery.pm" 
                      placeholder="PM" 
                      clearable 
                      filterable 
                      :filter-method="q => setFilterQuery('pm', q)"
                      @clear="setFilterQuery('pm', '')"
                      style="width: 100%" 
                      @change="handleFilter">
                      <el-option v-for="item in filterOptions(allPMOptions, pmFilterQuery)" :key="item" :label="item" :value="item" />
                  </el-select>
              </el-col>
              <el-col :span="3">
                 <el-select 
                      v-model="listQuery.mouse_strain" 
                      placeholder="鼠型" 
                      clearable 
                      filterable 
                      :filter-method="q => setFilterQuery('mouseStrain', q)"
                      @clear="setFilterQuery('mouseStrain', '')"
                      style="width: 100%" 
                      @change="handleFilter">
                      <el-option v-for="item in filterOptions(allMouseStrainOptions, mouseStrainFilterQuery)" :key="item" :label="item" :value="item" />
                  </el-select>
              </el-col>
              <el-col :span="3">
                 <el-select 
                      v-model="listQuery.project_status" 
                      placeholder="状态" 
                      clearable 
                      filterable 
                      :filter-method="q => setFilterQuery('status', q)"
                      @clear="setFilterQuery('status', '')"
                      style="width: 100%" 
                      @change="handleFilter">
                      <el-option label="进行中" value="ongoing" />
                      <el-option label="已完成" value="completed" />
                      <el-option v-for="item in filterOptions(allStatusOptions, statusFilterQuery)" :key="item" :label="item" :value="item" />
                  </el-select>
              </el-col>
              <el-col :span="5">
                 <el-select 
                      v-model="listQuery.mouse_strain_category" 
                      placeholder="归类鼠型" 
                      clearable 
                      filterable 
                      :filter-method="q => setFilterQuery('mouseStrainCategory', q)"
                      @clear="setFilterQuery('mouseStrainCategory', '')"
                      style="width: 100%" 
                      @change="handleFilter">
                      <el-option v-for="item in filterOptions(allMouseStrainCategoryOptions, mouseStrainCategoryFilterQuery)" :key="item" :label="item" :value="item" />
                  </el-select>
              </el-col>
              <el-col :span="1" style="text-align: center;">
                <span class="more-toggle-btn" title="彻底疯狂" @click="toggleAdvancedOps">
                  <el-icon><Tools /></el-icon>
                </span>
              </el-col>
              <el-col :span="4" style="text-align: right;">
                <el-button type="danger" :icon="Refresh" @click="handleAutoUpdateStatus">曼波</el-button>
                <el-button type="warning" :icon="Download" @click="handleExport" @contextmenu.prevent="handleMouseRightClick">鼠鼠</el-button>
              </el-col>
            </el-row>
          </div>
        </el-collapse-transition>
    </div>

    <!-- Main Table -->
    <el-card shadow="never" class="table-card" :body-style="{ padding: '15px' }">
        <el-table
        ref="serumTable"
        v-loading="listLoading"
        :data="list"
        :row-key="row => row.id"
        :row-class-name="tableRowClassName"
        border
        stripe
        fit
        highlight-current-row
        style="width: 100%;"
        size="large"
        :header-cell-style="{background:'#F5F7FA', color:'#606266', fontWeight:'bold',  height: '50px'}"
        >
        <el-table-column label="编号" prop="project_code" align="left" width="135" sortable fixed>
            <template #default="{ row }">
               <div class="code-text" @click="handleView(row)">{{ row.project_code }}</div>
            </template>
        </el-table-column>
        
        <el-table-column label="项目名称" prop="project_name" align="left" min-width="250" sortable show-overflow-tooltip>
            <template #default="{ row }">
               <span class="project-name">{{ row.project_name }}</span>
            </template>
        </el-table-column>

        <el-table-column v-if="showExtraColumns" label="归类鼠型" prop="mouse_strain_category" align="center" min-width="100" show-overflow-tooltip />

        <el-table-column v-if="showExtraColumns" :label="isCageMode ? '笼位' : '实验备注'" prop="remark" align="center" min-width="130" show-overflow-tooltip>
            <template #default="{ row }">
               <el-input
                  v-if="isCageMode && editingRowId === row.id"
                  v-model="editingValue"
                  size="small"
                  style="width: 100%;"
                  placeholder="鼠鼠大House~"
                  @keyup.enter="handleEnter(row)"
                  @blur="handleBlur(row)"
               />
               <span v-else @click="handleCageClick(row)" :style="isCageMode && canEdit(row) ? 'cursor: pointer; min-height: 20px; display: inline-block; min-width: 20px;' : 'cursor: default; min-height: 20px; display: inline-block; min-width: 20px;'">
                  {{ isCageMode ? (row.cage_position_display || '') : (row.remark || '') }}
               </span>
            </template>
        </el-table-column>

        <el-table-column v-if="showExtraColumns" label="课题类型" prop="study_type" align="center" min-width="100" show-overflow-tooltip />

        <el-table-column v-if="showExtraColumns" label="PM" prop="pm" align="center" width="100" show-overflow-tooltip />

        <el-table-column v-if="showExtraColumns" label="鼠型" prop="mouse_strain" align="center" min-width="100" show-overflow-tooltip />

        <el-table-column label="靶点" prop="target_name" align="center" width="100" sortable />
        
        <el-table-column label="负责人" prop="owner" align="center" width="100" sortable>
            <template #default="{ row }">
               {{ row.owner }}
            </template>
        </el-table-column>
        
        <el-table-column label="开始日期" prop="start_date" align="center" width="120" sortable />
        
        <el-table-column label="状态" prop="project_status" align="center" width="100" sortable>
            <template #default="{ row }">
              <el-popover :visible="activeStatusRowId === row.id" placement="right" trigger="manual" :width="100" :append-to-body="false">
                <div style="max-height: 250px; overflow-y: auto;">
                  <div v-for="item in allStatusOptions" :key="item" style="padding: 8px 12px; cursor: pointer;" class="status-option" @click="saveStatus(row, item)">
                    {{ item }}
                  </div>
                </div>
                <template #reference>
                  <el-tag class="status-tag" :type="statusFilter(row.project_status)" effect="plain" :style="canEdit(row) ? 'cursor: pointer;' : 'cursor: default;'" @click="canEdit(row) && handleStatusClick(row)">
                    {{ row.project_status }}
                  </el-tag>
                </template>
              </el-popover>
            </template>
        </el-table-column>

        <el-table-column label="操作" align="center" width="280" fixed="right">
            <template #default="{ row }">
                <el-button-group>
                    <el-button class="table-action-btn" size="small" type="primary" plain :icon="View" @click="handleView(row)">
                        详情
                    </el-button>
                    <el-button 
                        size="small" 
                        class="table-action-btn"
                        type="success" 
                        plain 
                        :icon="Edit" 
                        :class="{'no-permission-btn': !canEdit(row)}"
                        @click="handleUpdate(row, 'scheme')"
                        :title="!canEdit(row) ? '您没有权限编辑此项目' : ''">
                        方案
                    </el-button>
                    <el-button 
                        size="small" 
                        class="table-action-btn"
                        type="warning" 
                        plain 
                        :icon="TrendCharts" 
                        :class="{'no-permission-btn': !canEditTiter(row)}"
                        @click="handleUpdate(row, 'titer')"
                        :title="!canEditTiter(row) ? '您没有权限编辑此项目' : ''">
                        数据
                    </el-button>
                </el-button-group>
            </template>
        </el-table-column>
        </el-table>

         <div class="pagination-container">
            <el-pagination
                v-if="paginationReady && total > 0"
                :current-page="listQuery.page"
                :page-size="listQuery.limit"
                :total="total"
                background
                layout="total, sizes, prev, pager, next, jumper"
                @size-change="handleSizeChange"
                @current-change="handleCurrentChange"
            />
         </div>
    </el-card>

    <!-- Pie Chart Dialog (Replaced with CSS Bar Chart to standard) -->
    <el-dialog v-model="chartVisible" title="☝️🤓疯狂牛马榜🐮🐴 o((>ω< ))o" width="500px" append-to-body>
        <div class="chart-container" style="padding: 0px 20px 20px 20px;">
           <div v-if="stats.owner_counts.length === 0" style="text-align: center; color: #999;">暂无数据</div>
           <div v-else>
               <div v-for="(item, index) in stats.owner_counts.slice(0, 10)" :key="index" class="bar-row" style="margin-bottom: 15px;">
                   <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                       <span style="font-weight: bold; color: #333;">{{ item.name }}</span>
                       <span style="color: #666;">{{ item.value }} 单</span>
                   </div>
                   <div style="height: 10px; background: #f0f0f0; border-radius: 5px; overflow: hidden;">
                       <div :style="{width: (stats.total > 0 ? (item.value / stats.total * 100) : 0) + '%', background: '#409EFF', height: '100%'}"></div>
                   </div>
               </div>
           </div>
        </div>
    </el-dialog>

  </div>
</template>

<script>
import { useUserStore } from '@vben/stores'

import {
  ArrowDown,
  ArrowUp,
  CircleCheck,
  Close,
  DataAnalysis,
  Download,
  Edit,
  Plus,
  Refresh,
  Search,
  Timer,
  Tools,
  TrendCharts,
  UserFilled,
  View,
} from '@element-plus/icons-vue'
import {
  ElButton,
  ElButtonGroup,
  ElCard,
  ElCol,
  ElCollapseTransition,
  ElDatePicker,
  ElDialog,
  ElIcon,
  ElInput,
  ElLoading,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElPagination,
  ElPopover,
  ElRow,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus'

import { fetchList, fetchStats, getSerumFilterOptions, updateSerumStatus, export_mouse, autoUpdateStatus, updateCagePosition } from '#/api/serum'

export default {
  name: 'SerumList',
  components: {
    ElButton,
    ElButtonGroup,
    ElCard,
    ElCol,
    ElCollapseTransition,
    ElDatePicker,
    ElDialog,
    ElIcon,
    ElInput,
    ElOption,
    ElPagination,
    ElPopover,
    ElRow,
    ElSelect,
    ElTable,
    ElTableColumn,
    ElTag,
    ArrowDown,
    ArrowUp,
    CircleCheck,
    DataAnalysis,
    Timer,
    Tools,
    UserFilled,
  },
  setup() {
    const userStore = useUserStore()
    return {
      Close,
      Download,
      Edit,
      Plus,
      Refresh,
      Search,
      TrendCharts,
      userStore,
      View,
    }
  },
  computed: {
    currentUserName() {
      return this.userStore.userInfo?.realName || this.userStore.userInfo?.username || ''
    },
    currentOwnerName() {
      return this.currentUserName.split(' ')[0] || ''
    },
    currentRoles() {
      return this.userStore.userRoles || this.userStore.userInfo?.roles || []
    },
  },
  watch: {
    showExtraColumns(newVal) {
      if (!newVal) return
      this.$nextTick(() => {
        setTimeout(() => {
          this.smoothScrollTableToRight()
        }, 200)
      })
    }
  },
  data() {
    return {
      list: [],
      total: 0,
      listLoading: true,
      paginationReady: false,
      stats: {
          total: 0,
          status_counts: {},
          owner_counts: []
      },
      listQuery: {
        page: 1,
        limit: 20,
        project_code: undefined,
        project_name: undefined,
        owner: undefined,
        target_name: undefined,
        study_type: undefined,
        pm: undefined,
        mouse_strain: undefined,
        mouse_strain_category: undefined,
        project_status: undefined,
        start_date: undefined,
        end_date: undefined
      },
      dateRange: [],
      ownerFilterQuery: '',
      chartVisible: false,
      allTargetOptions: [],
      targetFilterQuery: '',
      allOwnerOptions: [],
      allStudyTypeOptions: [],
      studyTypeFilterQuery: '',
      allPMOptions: [],
      pmFilterQuery: '',
      allMouseStrainOptions: [],
      mouseStrainFilterQuery: '',
      allMouseStrainCategoryOptions: [],
      mouseStrainCategoryFilterQuery: '',
      allStatusOptions: [],
      statusFilterQuery: '',
      showAdvancedFilters: false,
      showExtraColumns: false,
      activeStatusRowId: null,
      showAdvancedOps: false,
      isCageMode: false,
      editingRowId: null,
      editingValue: '',
      editingOriginalValue: '',
      isSaving: false,
      listInitialized: false,
      tableScrollAnimationFrame: 0
    }
  },
  created() {
    this.getStats()
    this.getFilterOptions()
  },
  mounted() {
    this.initializeListPage()
  },
  activated() {
    if (!this.list.length && !this.listLoading) {
      this.initializeListPage(true)
    }
  },
  beforeRouteLeave(to, from, next) {
    sessionStorage.setItem('serumListQuery', JSON.stringify(this.listQuery))
    sessionStorage.setItem('serumDateRange', JSON.stringify(this.dateRange))
    sessionStorage.setItem('serumShowAdvancedFilters', JSON.stringify(this.showAdvancedFilters))
    sessionStorage.setItem('serumShowExtraColumns', JSON.stringify(this.showExtraColumns))
    next()
  },
  beforeRouteEnter(to, from, next) {
    next(vm => {
      vm.initializeListPage()
    })
  },
  methods: {
    initializeListPage(force = false) {
      if (this.listInitialized && !force) {
        return
      }

      this.listInitialized = true
      this.paginationReady = false
      this.restoreListState()

      this.$nextTick(() => {
        this.paginationReady = true
        this.getList()
      })
    },
    restoreListState() {
      const savedListQuery = sessionStorage.getItem('serumListQuery')
      const savedDateRange = sessionStorage.getItem('serumDateRange')
      const savedShowAdvancedFilters = sessionStorage.getItem('serumShowAdvancedFilters')
      const savedShowExtraColumns = sessionStorage.getItem('serumShowExtraColumns')
      if (savedListQuery) {
        Object.assign(this.listQuery, JSON.parse(savedListQuery))
      }
      if (savedDateRange) {
        this.dateRange = JSON.parse(savedDateRange)
      }
      if (savedShowAdvancedFilters) {
        this.showAdvancedFilters = JSON.parse(savedShowAdvancedFilters)
      }
      if (savedShowExtraColumns) {
        this.showExtraColumns = JSON.parse(savedShowExtraColumns)
      }
    },
    statusFilter(status) {
      if (!status) return 'info'

      if (status === '无效价处死') {
        return 'danger'
      }

      if (status.includes('待') || status === '加免中') {
        return 'primary'
      }

      if (status === '结题' || status.includes('月上机')) {
        return 'success'
      }

      return 'info'
    },
    smoothScrollTableToRight() {
      const tableRef = this.$refs.serumTable
      const tableEl = tableRef?.$el
      const body = tableEl?.querySelector('.el-table__body-wrapper .el-scrollbar__wrap')
      if (!tableRef?.setScrollLeft || !body) return

      tableRef?.doLayout?.()

      if (this.tableScrollAnimationFrame) {
        cancelAnimationFrame(this.tableScrollAnimationFrame)
      }

      const startLeft = body.scrollLeft
      const targetLeft = body.scrollWidth - body.clientWidth
      const distance = targetLeft - startLeft
      const duration = 450
      const startTime = performance.now()

      const easeOutCubic = (progress) => 1 - Math.pow(1 - progress, 3)
      const step = (now) => {
        const progress = Math.min((now - startTime) / duration, 1)
        tableRef.setScrollLeft(startLeft + distance * easeOutCubic(progress))

        if (progress < 1) {
          this.tableScrollAnimationFrame = requestAnimationFrame(step)
        } else {
          this.tableScrollAnimationFrame = 0
        }
      }

      this.tableScrollAnimationFrame = requestAnimationFrame(step)
    },
    tableRowClassName({ row }) {
      return `serum-row-${row.id}`
    },
    handleCellInventory() {
      this.$router.push('/serum/cell')
    },
    toggleAdvancedOps() {
      this.activeStatusRowId = null
      this.showAdvancedOps = !this.showAdvancedOps
    },
    getCurrentFilterPayload() {
        const [startDate, endDate] = this.dateRange?.length === 2 ? this.dateRange : [undefined, undefined]

        let projectCode = this.listQuery.project_code
        let projectCodes = null
        
        if (projectCode) {
            const separators = [',', '\t', '\n', '\r', '，', '、', ' ']
            const hasSeparator = separators.some(sep => projectCode.includes(sep))
            
            if (hasSeparator) {
                projectCodes = projectCode.split(new RegExp('[,\\t\\n\\r，、 ]+')).map(code => code.trim()).filter(code => code)
                projectCode = null
            }
        }

        return {
            project_code: projectCode,
            project_codes: projectCodes,
            project_name: this.listQuery.project_name,
            owner: this.listQuery.owner,
            project_status: this.listQuery.project_status,
            target_name: this.listQuery.target_name,
            study_type: this.listQuery.study_type,
            pm: this.listQuery.pm,
            mouse_strain: this.listQuery.mouse_strain,
            mouse_strain_category: this.listQuery.mouse_strain_category,
            start_date: startDate,
            end_date: endDate,
            page: this.listQuery.page,
            limit: this.listQuery.limit
        }
    },
    getStats() {
        fetchStats().then(response => {
            if (response.data) {
                this.stats = response.data
                if (this.stats.owner_counts && Array.isArray(this.stats.owner_counts)) {
                    this.stats.owner_counts.sort((a, b) => b.value - a.value)
                }
            }
        })
    },
    getFilterOptions() {
        getSerumFilterOptions().then(response => {
            if (response.data) {
                this.allTargetOptions = response.data.targets || [];
                this.allOwnerOptions = response.data.owners || [];
                this.allStudyTypeOptions = response.data.study_types || [];
                this.allPMOptions = response.data.pms || [];
                this.allMouseStrainOptions = response.data.mouse_strains || [];
                this.allMouseStrainCategoryOptions = response.data.mouse_strain_categories || [];
                this.allStatusOptions = response.data.statuses || [];
            }
        })
    },
    getList() {
      this.listLoading = true
      // Handle Date Range
      if (this.dateRange && this.dateRange.length === 2) {
          this.listQuery.start_date = this.dateRange[0]
          this.listQuery.end_date = this.dateRange[1]
      } else {
          this.listQuery.start_date = undefined
          this.listQuery.end_date = undefined
      }

      const payload = this.getCurrentFilterPayload()
      fetchList(payload).then(response => {
        this.list = Array.isArray(response.data.items) ? response.data.items : []
        this.total = Number(response.data.total) || 0
        this.listLoading = false
      }).catch(() => {
         this.list = []
         this.total = 0
         this.listLoading = false
      })
    },
    toggleAdvanced() {
        this.activeStatusRowId = null
        const next = !this.showAdvancedFilters
        this.showAdvancedFilters = next
        this.showExtraColumns = next
    },
    handleSizeChange(size) {
      this.listQuery.limit = size
      this.listQuery.page = 1
      this.getList()
    },
    handleCurrentChange(page) {
      this.listQuery.page = page
      this.getList()
    },
    handleFilter() {
      this.listQuery.page = 1
      this.getList()
    },
    handleStatusFilter(status) {
        if (this.listQuery.project_status === status) {
            this.listQuery.project_status = undefined
        } else {
            this.listQuery.project_status = status
        }
        this.handleFilter()
    },
    handleOwnerFilter(owner) {
         if (this.listQuery.owner === owner) {
            this.listQuery.owner = undefined // Toggle off
        } else {
            this.listQuery.owner = owner // Toggle on
        }
        this.handleFilter()
    },
    handleTotalClick() {
        this.chartVisible = true
    },
    handleCreate() {
      this.$router.push('/serum/edit')
    },
    handleView(row) {
        this.$router.push({ path: '/serum/detail', query: { id: row.id } })
    },
    handleUpdate(row, type) {
        if (type === 'titer') {
            if (!this.canEditTiter(row)) {
                ElMessage.warning('您没有权限编辑此项目')
                return
            }
        } else {
            if (!this.canEdit(row)) {
                ElMessage.warning('您没有权限编辑此项目')
                return
            }
        }
        if (type === 'titer') {
            this.$router.push({ path: '/serum/titer', query: { id: row.id } })
        } else {
            this.$router.push({ path: '/serum/edit', query: { id: row.id } })
        }
    },
    isAdminRole(roles) {
        return ['DOGE', 'super', 'admin'].some(role => roles.includes(role))
    },
    canEdit(row) {
        // 获取当前用户信息
        const currentUser = this.currentUserName
        const currentRoles = this.currentRoles
        // 管理员角色可以编辑所有项目
        if (this.isAdminRole(currentRoles)) 
        {return true}
        // 项目负责人可以编辑自己的项目
        if (currentUser.includes(row.owner))
        {return true}
        // 其他情况不能编辑
        return false
    },
    canEditTiter(row) {
        const currentUser = this.currentUserName
        const currentRoles = this.currentRoles
        if (this.isAdminRole(currentRoles)) 
        {return true}
        if (currentRoles.includes('serum_titer'))
        {return true}
        if (currentUser.includes(row.owner))
        {return true}
        return false
    },
    setFilterQuery(key, query) {
        this[`${key}FilterQuery`] = query;
    },
    filterOptions(dataArray, query) {
        const queryLower = (query || '').toLowerCase();
        if (!queryLower) return dataArray;
        
        return dataArray
            .filter(item => item.toLowerCase().includes(queryLower))
            .sort((a, b) => {
                const aStarts = a.toLowerCase().startsWith(queryLower);
                const bStarts = b.toLowerCase().startsWith(queryLower);
                return aStarts === bStarts ? a.localeCompare(b) : (aStarts ? -1 : 1);
            });
    },
    handleStatusClick(row) {
      this.activeStatusRowId = (this.activeStatusRowId === row.id) ? null : row.id
    },
    handleMouseRightClick(event) {
      event.preventDefault()
      this.isCageMode = !this.isCageMode
      this.editingRowId = null
      this.editingValue = ''
      if (this.isCageMode) {
        ElMessage.info('已切换到笼位编辑模式')
      }
    },
    handleCageClick(row) {
      if (!this.isCageMode) {
        this.editingRowId = null
        return
      }
      if (!this.canEdit(row)) {
        ElMessage.warning('您没有权限编辑此项目')
        this.editingRowId = null
        return
      }
      this.editingRowId = row.id
      this.editingValue = row.cage_position_display || ''
      this.editingOriginalValue = this.editingValue
      this.$nextTick(() => {
        setTimeout(() => {
          const rowEl = this.$el.querySelector(`.serum-row-${row.id}`)
          const inputEl = rowEl && rowEl.querySelector('input')
          if (inputEl) {
            inputEl.focus()
            inputEl.select()
          }
        }, 0)
      })
    },
    handleEnter(row) {
      this.saveCagePosition(row)
    },
    handleBlur(row) {
      this.saveCagePosition(row)
    },
    saveCagePosition(row) {
      if (this.isSaving) {
        return
      }
      if (this.editingValue.trim() === this.editingOriginalValue) {
        this.editingRowId = null
        this.editingValue = ''
        return
      }
      this.isSaving = true
      updateCagePosition({ 
        id: row.id, 
        cage_position: this.editingValue.trim() 
      }).then(response => {
        if (response.data && response.data.message && response.data.message.includes('鼠鼠不存在')) {
          ElMessage.warning('鼠鼠不存在')
          row.cage_position = ''
          row.cage_position_display = ''
        } else {
          row.cage_position = this.editingValue.trim()
          row.cage_position_display = this.editingValue.trim()
          ElMessage.success('笼位更新成功')
        }
        this.editingRowId = null
        this.editingValue = ''
      }).catch(error => {
        this.editingRowId = null
        this.editingValue = ''
      }).finally(() => {
        this.isSaving = false
      })
    },
    saveStatus(row, newStatus) {
      updateSerumStatus({ id: row.id, project_status: newStatus }).then(() => {
        row.project_status = newStatus
        ElMessage.success('状态修改成功')
        this.getStats()
        this.activeStatusRowId = null
      })
    },
    handleExport() {
        const [startDate, endDate] = this.dateRange?.length === 2 ? this.dateRange : [undefined, undefined]
        
        if (!startDate || !endDate) {
            ElMessageBox.confirm('您未选择时间段，将导出所有数据，是否继续？', '提示', {
                confirmButtonText: '继续导出',
                cancelButtonText: '取消',
                type: 'warning'
            }).then(() => {
                this.performExport(startDate, endDate)
            }).catch(() => {
                
            })
        } else {
            this.performExport(startDate, endDate)
        }
    },
    
    performExport(startDate, endDate) {
        const loading = ElLoading.service({
            lock: true,
            text: '正在导出数据...',
            background: 'rgba(0, 0, 0, 0.7)'
        })
        
        const exportQuery = this.getCurrentFilterPayload()
        exportQuery.start_date = startDate
        exportQuery.end_date = endDate
        
        export_mouse(exportQuery).then(response => {
            const blob = response instanceof Blob ? response : new Blob([response], {
                type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            })
            const url = window.URL.createObjectURL(blob)
            const link = document.createElement('a')
            link.href = url
            link.download = `serum_mouse_${new Date().toISOString().slice(0, 10)}.xlsx`
            document.body.appendChild(link)
            link.click()
            document.body.removeChild(link)
            window.URL.revokeObjectURL(url)
            ElMessage.success('导出成功')
        }).catch(error => {
            console.error('导出失败:', error)
            ElMessage.error('导出失败，请重试')
        }).finally(() => {
            loading.close()
        })
    },
    
    handleAutoUpdateStatus() {
        ElMessageBox.confirm('确定要根据当前筛选条件自动更新所有实验的状态吗？', '提示', {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
        }).then(() => {
            const loading = ElLoading.service({
                lock: true,
                text: '正在哈基米南北绿豆ing...',
                background: 'rgba(0, 0, 0, 0.7)'
            })
            
            const updateQuery = this.getCurrentFilterPayload()
            
            autoUpdateStatus(updateQuery).then(response => {
                ElMessage.success('状态更新成功')
                this.getList()
                this.getStats()
            }).catch(error => {
                console.error('状态更新失败:', error)
                ElMessage.error('状态更新失败，请重试')
            }).finally(() => {
                loading.close()
            })
        }).catch(() => {
            
        })
    }
  }
}
</script>

<style scoped>
.app-container {
    position: relative;
    padding: 20px;
    background-color: #f5f7fa;
    min-height: 100vh;
}
.filter-wrapper {
    background: #fff;
    padding: 15px 20px;
    border-radius: 4px;
    margin-bottom: 20px;
    box-shadow: 0 1px 4px rgba(0,21,41,0.08);
}
.app-container :deep(.el-input:not(.el-input--small):not(.el-input--large)),
.app-container :deep(.el-select:not(.el-select--small):not(.el-select--large)),
.app-container :deep(.el-date-editor.el-input:not(.el-input--small):not(.el-input--large)) {
    font-size: 13px;
}
.app-container :deep(.el-input:not(.el-input--small):not(.el-input--large)) {
    --el-input-height: 30px;
}
.app-container :deep(.el-input:not(.el-input--small):not(.el-input--large) .el-input__wrapper),
.app-container :deep(.el-select:not(.el-select--small):not(.el-select--large) .el-select__wrapper) {
    min-height: 30px;
}
.app-container :deep(.el-button:not(.el-button--small):not(.el-button--large):not(.el-button--text)) {
    height: 30px;
    padding: 0 13px;
    font-size: 13px;
}
.filter-wrapper :deep(.el-button .el-icon + span),
.advanced-ops-bar :deep(.el-button .el-icon + span) {
    margin-left: 4px;
}
.table-action-btn {
    height: 30px;
    padding: 0 14px;
    font-size: 13px;
}
.status-tag {
    height: 27px;
    padding: 0 13px;
    font-size: 13px;
    border-radius: 10px;
}
.table-card {
    border-radius: 4px;
    border: none;
    box-shadow: 0 1px 4px rgba(0,21,41,0.08);
}
.filter-item {
    width: 100%;
}
.advanced-filters {
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px dashed #e8e8e8;
}
.more-toggle-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    color: #606266;
    background: #f5f7fa;
    cursor: pointer;
    margin-right: 6px;
    vertical-align: middle;
}
.more-toggle-btn .el-icon {
    font-size: 15px;
}
.more-toggle-btn:hover {
    color: #409EFF;
    background: #eef5ff;
}
.code-text {
    font-family: 'Consolas', monospace;
    color: #409EFF;
    cursor: pointer;
    font-weight: bold;
}
.code-text:hover {
    text-decoration: underline;
}
.project-name {
    font-weight: 500;
    color: #333;
}

/* 无权限按钮样式 */
.no-permission-btn {
    cursor: not-allowed;
}

/* Dashboard Panel Styles */
.panel-group {
  margin-top: 0px;
  margin-bottom: 20px;
}
.card-panel-col {
  margin-bottom: 20px;
}
.card-panel {
  height: 100px;
  cursor: pointer;
  font-size: 12px;
  position: relative;
  overflow: hidden;
  color: #fff;
  background: #fff;
  box-shadow: 4px 4px 40px rgba(0, 0, 0, .05);
  border-radius: 6px;
  display: flex;
  align-items: center;
  padding: 0 20px; 
  transition: all 0.3s;
}
.card-panel:hover {
    transform: translateY(-5px);
    box-shadow: 0 15px 30px rgba(0,0,0,0.1);
}
.active-card {
    border: 2px solid #333;
    transform: scale(1.02);
    box-shadow: 0 10px 20px rgba(0,0,0,0.2);
}

.card-panel-icon-wrapper {
  margin: 0; 
  padding: 10px;
  border-radius: 6px;
  background: rgba(255,255,255,0.2);
  display: flex;
  align-items: center;
  justify-content: center;
}
.card-panel-icon {
  font-size: 40px; 
}
.card-panel-icon :deep(svg) {
  width: 1em;
  height: 1em;
}
.card-panel-description {
  font-weight: bold;
  margin-left: auto; 
  text-align: right;
}
.card-panel-text {
  line-height: 18px;
  font-size: 14px;
  margin-bottom: 8px;
  opacity: 0.9;
}
.card-panel-num {
  font-size: 24px;
  font-weight: bold;
}

/* Gradient Backgrounds */
.blue-panel { background: linear-gradient(135deg, #36a3f7 0%, #1890ff 100%); }
.green-panel { background: linear-gradient(135deg, #58d68d 0%, #2ecc71 100%); }
.red-panel { background: linear-gradient(135deg, #8e44ad 0%, #9b59b6 100%); }
.orange-panel { background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%); }

.pagination-container {
    margin-top: 15px;
    text-align: right;
}
.status-option:hover {
    background-color: #f5f7fa;
    color: #409EFF;
}

/* 覆盖层本体 */
.advanced-ops-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;

  height: 140px;
  padding: 12px 16px;
  border-radius: 6px;

  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 10px 30px rgba(0,0,0,0.12);
  z-index: 50;

  backdrop-filter: blur(6px);
}

.ops-bar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.ops-title {
  font-weight: 700;
  color: #303133;
  display: flex;
  align-items: center;
}

.ops-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

/* 滑入动画 */
.ops-slide-enter-active,
.ops-slide-leave-active {
  transition: transform .25s ease, opacity .25s ease;
}
.ops-slide-enter,
.ops-slide-leave-to {
  transform: translateY(-110%);
  opacity: 0;
}
</style>
