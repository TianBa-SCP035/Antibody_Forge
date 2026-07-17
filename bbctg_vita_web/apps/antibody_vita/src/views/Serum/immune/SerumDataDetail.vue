<template>
  <div class="serum-detail app-container" v-loading="loading">
    <!-- Header -->
    <div class="page-header">
      <div class="title-wrap">
        <div class="title-row">
          <div class="page-title">
            {{ postForm.project_name || '免疫实验详情' }}
          </div>

          <el-tag
            class="status-tag"
            :type="statusType"
            effect="dark"
            size="small"
          >
            {{ statusLabel }}
          </el-tag>
        </div>

        <div class="sub-row">
          <span class="sub-item">
            <el-icon><Tickets /></el-icon>
            实验ID：<b>{{ postForm.experiment_id || '-' }}</b>
          </span>

          <span class="dot">•</span>

          <span class="sub-item">
            <el-icon><CollectionTag /></el-icon>
            项目编号：<b>{{ postForm.project_code || '-' }}</b>
          </span>
          <el-button
            class="copy-btn"
            link
            :disabled="!postForm.project_code"
            @click="copyText(postForm.project_code)"
          >
            <el-icon><DocumentCopy /></el-icon>
            <span>复制</span>
          </el-button>

          <span class="dot">•</span>

          <span class="sub-item">
            <el-icon><User /></el-icon>
            负责人：<b>{{ postForm.owner || '-' }}</b>
          </span>
        </div>
      </div>

      <div class="action-wrap">
        <el-button size="large" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          <span>返回</span>
        </el-button>
        <span
          title="左键导出 Excel，右键打印"
          @contextmenu.prevent="handlePrintScheme"
        >
          <el-button
            size="large"
            :disabled="!postForm.id"
            :loading="schemeExportLoading"
            @click="handleExportScheme"
          >
            <el-icon><Download /></el-icon>
            <span>导出方案</span>
          </el-button>
        </span>
        <el-button
          size="large"
          type="primary"
          :disabled="!postForm.id || !canEdit()"
          @click="goEdit"
        >
          <el-icon><Edit /></el-icon>
          <span>编辑</span>
        </el-button>
      </div>
    </div>

    <!-- KPI -->
    <el-row :gutter="16" class="kpi-row">
      <el-col :xs="12" :sm="6">
        <div class="kpi-card">
          <div class="kpi-label">分组数</div>
          <div class="kpi-value">{{ groupCount }}</div>
          <div class="kpi-hint">Mouse Groups</div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="kpi-card">
          <div class="kpi-label">总鼠数</div>
          <div class="kpi-value">{{ totalMice }}</div>
          <div class="kpi-hint">Sum of mouse_count</div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="kpi-card">
          <div class="kpi-label">抗原数</div>
          <div class="kpi-value">{{ antigenCount }}</div>
          <div class="kpi-hint">Antigens</div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="kpi-card">
          <div class="kpi-label">步骤数</div>
          <div class="kpi-value">{{ stepCount }}</div>
          <div class="kpi-hint">Immunization Steps</div>
        </div>
      </el-col>
    </el-row>

    <!-- Basic Info -->
    <el-card class="section-card">
      <template #header>
        <div class="section-header">
          <div class="section-title">
            <el-icon><InfoFilled /></el-icon>
            <span>基础信息</span>
          </div>
        </div>
      </template>

      <el-descriptions :column="4" border class="desc">
        <el-descriptions-item label="项目名称">
          {{ postForm.project_name || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="项目编号">
          {{ postForm.project_code || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="实验ID">
          {{ postForm.experiment_id || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="项目状态">
          <el-tag :type="statusType" size="small">
            {{ statusLabel }}
          </el-tag>
        </el-descriptions-item>

        <el-descriptions-item label="负责人">
          {{ postForm.owner || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="开始日期">
          {{ postForm.start_date || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="免疫间隔">
          <span v-if="postForm.immunization_interval">
            {{ postForm.immunization_interval }} 天
          </span>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="检测方法">
          {{ postForm.assay_method || '-' }}
        </el-descriptions-item>

        <el-descriptions-item label="靶点名称">
          {{ postForm.target_name || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="靶点类型">
          {{ postForm.target_type || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="靶点大小">
          {{ postForm.target_size || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="PM">
          {{ postForm.pm || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="课题类型">
          {{ postForm.study_type || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">
          {{ postForm.remark || '-' }}
        </el-descriptions-item>
      </el-descriptions>

      <div class="long-text">
        <div class="long-title">项目目的</div>
        <div class="long-body">
          {{ postForm.project_purpose || '—' }}
        </div>
      </div>
    </el-card>

    <!-- Main Tabs -->
    <el-tabs v-model="activeTab" type="card" class="main-tabs">
      <!-- Schedule -->
      <el-tab-pane label="免疫方案" name="schedule">
        <div v-if="!groupCount" class="empty-block">
          <el-icon><Warning /></el-icon>
          <div class="empty-title">暂无分组信息</div>
          <div class="empty-sub">请在编辑页添加 Mouse Groups 与免疫步骤</div>
        </div>

        <div v-else class="group-list">
          <el-card
            v-for="(group, idx) in postForm.mouse_groups"
            :key="group.group_id || idx"
            class="group-card"
          >
            <template #header>
              <div class="group-header">
                <div class="group-title">
                  <span class="group-badge">{{ group.group_id || 'G?' }}</span>
                  <span class="group-name">
                    {{ group.mouse_strain || '-' }}
                  </span>
                </div>

                <div class="group-meta">
                  <el-tag size="small" type="info" effect="plain">
                    {{ (stepsByGroup[group.group_id] || []).length }} steps
                  </el-tag>
                </div>
              </div>
            </template>

            <el-row :gutter="16">
              <!-- Left Column: Group Info and Antigen Info -->
              <el-col :xs="24" :md="10">
                <!-- Group Info -->
                <div class="subsection-title">
                  <el-icon><User /></el-icon>
                  分组信息
                </div>

                <el-descriptions :column="2" border class="desc">
                  <el-descriptions-item label="分组ID">
                    {{ group.group_id || '-' }}
                  </el-descriptions-item>
                  <el-descriptions-item label="品系/名称">
                    {{ group.mouse_strain || '-' }}
                  </el-descriptions-item>

                  <el-descriptions-item label="数量">
                    {{ group.mouse_count || '-' }}
                  </el-descriptions-item>
                  <el-descriptions-item label="归类鼠型">
                    {{ group.mouse_strain_category || '-' }}
                  </el-descriptions-item>

                  <el-descriptions-item label="周龄">
                    {{ group.age_weeks || '-' }}
                  </el-descriptions-item>
                  <el-descriptions-item label="性别">
                    {{ group.sex || '-' }}
                  </el-descriptions-item>
                  
                  <el-descriptions-item label="笼位">
                    {{ group.cage_position || '-' }}
                  </el-descriptions-item>
                  <el-descriptions-item label="供应商">
                    {{ group.vendor || '-' }}
                  </el-descriptions-item>

                  <el-descriptions-item label="鼠号列表" :span="2">
                      {{ group.mouse_no_list || '-' }}
                  </el-descriptions-item>

                  <el-descriptions-item label="备注" :span="2">
                    {{ group.remark || '-' }}
                  </el-descriptions-item>
                </el-descriptions>

                <!-- Antigen Info -->
                <div class="subsection-title" style="margin-top: 16px;">
                  <el-icon><Collection /></el-icon>
                  抗原信息
                </div>

                <el-table
                  :data="getAntigensByGroup(group.group_id)"
                  border
                  size="small"
                  class="table"
                  style="margin-bottom: 10px;"
                >
                  <el-table-column label="ID" width="60">
                    <template #default="{ row }">
                      <el-tag size="small" type="info">{{ row.antigen_id }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="antigen_name" label="抗原名称" min-width="120" />
                  <el-table-column prop="species" label="物种" width="70" />
                  <el-table-column prop="antigen_type" label="类型" width="70" />
                </el-table>
              </el-col>

              <!-- Right Column: Schedule Timeline -->
              <el-col :xs="24" :md="14">
                <div class="subsection-title">
                  <el-icon><Calendar /></el-icon>
                  免疫进度
                </div>

                <div v-if="!(stepsByGroup[group.group_id] || []).length" class="empty-inline">
                  暂无步骤
                </div>

                <div v-else class="schedule-wrap">
                  <!-- Timeline Only -->
                  <div class="timeline">
                    <div
                      v-for="(s, i) in stepsByGroup[group.group_id]"
                      :key="`${group.group_id}-${i}`"
                      class="timeline-item"
                    >
                      <div class="tl-dot" />
                      <div class="tl-content">
                        <div class="tl-top">
                          <span class="tl-stage">{{ s.stage_name || '-' }}</span>
                          <span class="tl-date">{{ s.date_actual || '-' }}</span>
                        </div>
                        <div class="tl-mid">
                          <span class="tl-chip">
                            Day {{ s.day_relative || '-' }}
                          </span>
                          <span class="tl-chip">
                            抗原：{{ s.antigen_name_display || '-' }}
                          </span>
                        </div>
                        <div class="tl-bottom" v-if="s.remark">
                          备注：{{ s.remark }}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </el-col>
            </el-row>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- Plan Details -->
      <el-tab-pane label="方案详情" name="plan-details">
        <!-- 第一张表：抗原信息表 -->
        <el-card class="section-card">
          <template #header>
            <div class="section-header">
              <div class="section-title">
                <el-icon><Collection /></el-icon>
                <span>1. 抗原信息 (Antigens)</span>
              </div>
            </div>
          </template>

          <div v-if="!antigenCount" class="empty-block">
            <el-icon><Collection /></el-icon>
            <div class="empty-title">暂无抗原信息</div>
            <div class="empty-sub">请在编辑页添加 Antigens</div>
          </div>

          <el-table
            v-else
            :data="postForm.antigens"
            border
            size="small"
            class="table"
          >
            <el-table-column label="ID" width="70">
              <template #default="{ row }">
                <el-tag size="small" type="info">{{ row.antigen_id }}</el-tag>
              </template>
            </el-table-column>

            <el-table-column prop="antigen_name" label="抗原名称" min-width="160" />
            <el-table-column prop="species" label="物种" width="90" />
            <el-table-column prop="antigen_type" label="类型" width="90" />

            <el-table-column prop="catalog_no" label="货号" min-width="120" />
            <el-table-column prop="lot_no" label="批号" min-width="120" />
            <el-table-column prop="stock_conc" label="库存浓度" width="110" />
            <el-table-column prop="vendor" label="供应商" width="120" />

            <el-table-column prop="adjuvant_type" label="佐剂类型" min-width="110" />
            <el-table-column prop="adjuvant_source" label="佐剂来源" width="90" />
          </el-table>
        </el-card>

        <!-- 第二张表：按组分栏的步骤详情表 -->
        <el-card class="section-card" style="margin-top: 16px;">
          <template #header>
            <div class="section-header">
              <div class="section-title">
                <el-icon><Calendar /></el-icon>
                <span>2. 免疫步骤详情 (Immunization Steps)</span>
              </div>
            </div>
          </template>

          <div v-if="!stepCount" class="empty-block">
            <el-icon><Calendar /></el-icon>
            <div class="empty-title">暂无免疫步骤</div>
            <div class="empty-sub">请在编辑页添加 Immunization Steps</div>
          </div>

          <div v-else>
            <el-tabs v-model="activeGroupTab" type="card" class="group-tabs">
              <el-tab-pane
                v-for="(group, idx) in postForm.mouse_groups"
                :key="group.group_id || idx"
                :label="`${group.group_id || 'G?'}`"
                :name="safeGroupName(group, idx)"
              >
                <div class="group-subtitle">
                  <span class="group-info">{{ group.mouse_strain || '-' }} - {{ group.mouse_count || '-' }}只</span>
                </div>
                
                <el-table
                  :data="stepsByGroup[group.group_id] || []"
                  border
                  size="small"
                  class="table"
                >
                  <el-table-column prop="stage_name" label="阶段" width="80" />
                  <el-table-column prop="date_actual" label="日期" width="110" />
                  <el-table-column prop="day_relative" label="Day" width="70" />
                  <el-table-column prop="antigen_name_display" label="抗原" min-width="130" />
                  <el-table-column prop="antigen_dose" label="剂量" width="80" />
                  <el-table-column prop="adjuvant_name" label="佐剂" width="90" />
                  <el-table-column prop="cpg_dose" label="CPG" width="70" />
                  <el-table-column prop="injection_volume" label="体积" width="70" />
                  <el-table-column prop="route" label="途径" width="90" />
                  <el-table-column prop="injection_site" label="部位" min-width="120" />
                  <el-table-column prop="remark" label="备注" min-width="140" />
                </el-table>
              </el-tab-pane>
            </el-tabs>
          </div>
        </el-card>

        <!-- 第三张表：小鼠信息总表 -->
        <el-card class="section-card" style="margin-top: 16px;">
          <template #header>
            <div class="section-header">
              <div class="section-title">
                <el-icon><User /></el-icon>
                <span>3. 小鼠信息总表 (Mouse Groups)</span>
              </div>
            </div>
          </template>

          <div v-if="!groupCount" class="empty-block">
            <el-icon><User /></el-icon>
            <div class="empty-title">暂无小鼠分组信息</div>
            <div class="empty-sub">请在编辑页添加 Mouse Groups</div>
          </div>

          <el-table
            v-else
            :data="postForm.mouse_groups"
            border
            size="small"
            class="table"
          >
            <el-table-column prop="group_id" label="分组ID" width="100" />
            <el-table-column prop="mouse_strain" label="品系" min-width="150" />
            <el-table-column prop="mouse_strain_category" label="归类鼠型" min-width="140" />
            <el-table-column prop="mouse_count" label="数量" width="80" />
            <el-table-column prop="age_weeks" label="周龄" width="80" />
            <el-table-column prop="sex" label="性别" width="80" />
            <el-table-column prop="cage_position" label="笼位" min-width="120" />
            <el-table-column prop="vendor" label="供应商" min-width="150" />
            <el-table-column prop="mouse_no_list" label="小鼠编号" min-width="200" />
            <el-table-column prop="remark" label="备注" min-width="150" />
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- Titer -->
      <el-tab-pane label="效价检测" name="titer">
        <SerumDetailTiterTab
          :project="postForm"
          :active="activeTab === 'titer'"
        />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script>
import { useUserStore } from '@vben/stores'

import {
  ArrowLeft,
  Calendar,
  Collection,
  CollectionTag,
  DocumentCopy,
  Download,
  Edit,
  InfoFilled,
  Tickets,
  User,
  Warning,
} from '@element-plus/icons-vue'
import {
  ElButton,
  ElCard,
  ElCol,
  ElDescriptions,
  ElDescriptionsItem,
  ElIcon,
  ElMessage,
  ElRow,
  ElTabPane,
  ElTable,
  ElTableColumn,
  ElTabs,
  ElTag,
} from 'element-plus'

import { notifyApiError } from '#/api/errors'
import { exportScheme, exportSchemePdf, fetchDetail } from '#/api/serum'
import { SERUM_ERRORS } from '../shared/errors'
import {
  canEditSerumProject,
  getSerumUserName,
  getSerumUserRoles,
} from '#/utils/serumPermission'
import { getSerumProjectStatusTagType } from '#/utils/serumProjectStatus'
import { shouldRefreshTabData } from '#/utils/staleTabRefresh'

import SerumDetailTiterTab from '../titer/SerumDetailTiterTab.vue'

function compareImmStepOrder(a, b) {
  const orderDiff = (Number(a.sort_order) || 0) - (Number(b.sort_order) || 0)
  if (orderDiff !== 0) return orderDiff
  const aid = Number(a.step_id)
  const bid = Number(b.step_id)
  if (Number.isFinite(aid) && Number.isFinite(bid) && aid !== bid) return aid - bid
  return 0
}

export default {
  name: 'SerumDataDetail',
  components: {
    ArrowLeft,
    Calendar,
    Collection,
    CollectionTag,
    DocumentCopy,
    Download,
    Edit,
    ElButton,
    ElCard,
    ElCol,
    ElDescriptions,
    ElDescriptionsItem,
    ElIcon,
    ElRow,
    ElTabPane,
    ElTable,
    ElTableColumn,
    ElTabs,
    ElTag,
    InfoFilled,
    SerumDetailTiterTab,
    Tickets,
    User,
    Warning,
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
      schemeExportLoading: false,
      activeTab: 'schedule',
      activeGroupTab: '', // 用于跟踪免疫步骤详情中的分组标签
      postForm: {
        id: undefined,
        experiment_id: '',
        project_code: '',
        project_name: '',
        project_purpose: '',
        owner: '',
        start_date: '',
        project_status: 'draft',
        target_name: '',
        target_type: '',
        target_size: '',
        pm: '',
        study_type: '',
        assay_method: '',
        immunization_interval: '',
        remark: '',
        mouse_groups: [],
        steps: [],
        antigens: [],
        titer_targets: [],
        titer_pcs: []
      },
      tabDataFetchedAt: 0,
    }
  },
  computed: {
    currentUserInfo() {
      return this.userStore.userInfo || {}
    },
    currentUserName() {
      return getSerumUserName(this.currentUserInfo)
    },
    currentRoles() {
      return getSerumUserRoles(this.currentUserInfo)
    },
    statusLabel() {
      return this.postForm.project_status || '未知'
    },
    statusType() {
      return getSerumProjectStatusTagType(this.postForm.project_status)
    },
    antigenCount() {
      return (this.postForm.antigens || []).length
    },
    groupCount() {
      return (this.postForm.mouse_groups || []).length
    },
    stepCount() {
      return (this.postForm.steps || []).length
    },
    totalMice() {
      const groups = this.postForm.mouse_groups || []
      return groups.reduce((sum, g) => {
        const n = parseInt(g.mouse_count, 10)
        return sum + (isNaN(n) ? 0 : n)
      }, 0)
    },
    antigenMap() {
      const map = {}
      ;(this.postForm.antigens || []).forEach(a => {
        if (a && a.antigen_id != null) map[String(a.antigen_id)] = a
      })
      return map
    },
    processedSteps() {
      const steps = this.postForm.steps || []
      return steps.map(s => {
        let antigenNameDisplay = '-'
        
        if (s.antigen_id) {
          const names = (s.antigen_id.split(',').map(id => id.trim()))
            .map(id => {
              const a = this.antigenMap[String(id)]
              return a ? a.antigen_name : id
            })
            .filter(name => name)
          antigenNameDisplay = names.length > 0 ? names.join(' + ') : '-'
        }
        
        return {
          ...s,
          antigen_name_display: antigenNameDisplay
        }
      })
    },
    stepsByGroup() {
      const res = {}
      const steps = this.processedSteps || []
      steps.forEach((s) => {
        const gid = s.group_id || 'UNKNOWN'
        if (!res[gid]) res[gid] = []
        res[gid].push(s)
      })
      Object.keys(res).forEach((gid) => {
        res[gid].sort(compareImmStepOrder)
      })
      return res
    }
  },
  created() {
    const id = this.$route.query.id
    if (id) this.fetchData(id)
  },
  activated() {
    if (shouldRefreshTabData(this.tabDataFetchedAt)) {
      const id = this.$route.query.id
      if (id) this.fetchData(id)
    }
  },
  watch: {
    '$route.query.id'(val) {
      if (val) this.fetchData(val)
    },
    activeTab(newVal) {
      if (newVal === 'plan-details' && this.postForm.mouse_groups && this.postForm.mouse_groups.length > 0) {
        const firstGroup = this.postForm.mouse_groups[0]
        this.activeGroupTab = this.safeGroupName(firstGroup, 0)
      }
    }
  },
  methods: {
    safeGroupName(group, idx) {
      const safe = encodeURIComponent(group.group_id || idx)
      return `group-${safe}`
    },
    getAntigensByGroup(groupId) {
      const steps = this.stepsByGroup[groupId] || []
      const antigenIds = new Set()
      steps.forEach(s => {
        if (s.antigen_id) {
          s.antigen_id.split(',').forEach(id => {
            const trimmed = id.trim()
            if (trimmed) antigenIds.add(trimmed)
          })
        }
      })
      const allAntigens = this.postForm.antigens || []
      return allAntigens.filter(a => antigenIds.has(String(a.antigen_id)))
    },
    canEdit() {
        return canEditSerumProject(this.currentUserInfo, this.postForm)
    },
    fetchData(id) {
      this.loading = true
      fetchDetail(id)
        .then((res) => {
          this.postForm = { ...this.postForm, ...(res || {}) }
          
          if (this.activeTab === 'plan-details' && this.postForm.mouse_groups && this.postForm.mouse_groups.length > 0) {
            const firstGroup = this.postForm.mouse_groups[0]
            this.activeGroupTab = this.safeGroupName(firstGroup, 0)
          }
        })
        .catch((err) => {
          notifyApiError(err, { messages: SERUM_ERRORS.edit.loadPage })
        })
        .finally(() => {
          this.loading = false
          this.tabDataFetchedAt = Date.now()
        })
    },
    goBack() {
      this.$router.go(-1)
    },
    goEdit() {
      // 尽量不强依赖你的具体路由；你可以按项目实际路由改这里
      // 常见写法：跳到编辑页并带 id
      this.$router.push({
        path: '/serum/edit',
        query: { id: this.postForm.id }
      }).catch(() => {})
    },
    asResponseBlob(response, mimeType) {
      return response instanceof Blob ? response : new Blob([response], { type: mimeType })
    },
    handleExportScheme() {
      if (!this.postForm.id || this.schemeExportLoading) return
      this.schemeExportLoading = true
      exportScheme({ ids: [this.postForm.id] })
        .then((response) => {
          const blob = this.asResponseBlob(
            response,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          )
          const url = window.URL.createObjectURL(blob)
          const link = document.createElement('a')
          link.href = url
          const code = this.postForm.project_code || this.postForm.id
          const timestamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14)
          link.download = `免疫方案_${code}_${timestamp}.xlsx`
          document.body.appendChild(link)
          link.click()
          document.body.removeChild(link)
          window.URL.revokeObjectURL(url)
          ElMessage.success('免疫方案已导出')
        })
        .catch((err) => {
          notifyApiError(err, { messages: SERUM_ERRORS.detail.exportScheme })
        })
        .finally(() => {
          this.schemeExportLoading = false
        })
    },
    handlePrintScheme() {
      if (!this.postForm.id || this.schemeExportLoading) return
      this.schemeExportLoading = true
      const loadingMsg = ElMessage({
        message: '正在生成打印预览，请稍候…',
        type: 'info',
        duration: 0,
      })
      exportSchemePdf({ ids: [this.postForm.id] })
        .then((response) => {
          const blob = this.asResponseBlob(response, 'application/pdf')
          const url = window.URL.createObjectURL(blob)
          const printWindow = window.open(url, '_blank')
          if (!printWindow) {
            window.URL.revokeObjectURL(url)
            throw new Error('浏览器拦截了弹窗，请允许弹窗后重试')
          }
          setTimeout(() => {
            printWindow.focus()
            printWindow.print()
            window.URL.revokeObjectURL(url)
          }, 1000)
        })
        .catch((err) => {
          if (err instanceof Error && err.message.includes('浏览器拦截')) {
            ElMessage.error(err.message)
            return
          }
          notifyApiError(err, { messages: SERUM_ERRORS.detail.exportPdf })
        })
        .finally(() => {
          loadingMsg.close()
          this.schemeExportLoading = false
        })
    },
    copyText(text) {
      if (!text) return
      // 兼容：navigator.clipboard 不一定存在
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(String(text)).then(() => {
          ElMessage.success('已复制到剪贴板')
        }).catch(() => {
          this.fallbackCopy(String(text))
        })
      } else {
        this.fallbackCopy(String(text))
      }
    },
    fallbackCopy(text) {
      try {
        const input = document.createElement('textarea')
        input.value = text
        input.setAttribute('readonly', 'readonly')
        input.style.position = 'fixed'
        input.style.opacity = '0'
        document.body.appendChild(input)
        input.select()
        document.execCommand('copy')
        document.body.removeChild(input)
        ElMessage.success('已复制到剪贴板')
      } catch (e) {
        ElMessage.warning('复制失败，请手动复制')
      }
    }
  }
}
</script>

<style scoped>
.serum-detail {
  padding: 14px 18px 26px;
  background: linear-gradient(180deg, #f6f9ff 0%, #ffffff 40%);
  min-height: calc(100vh - 40px);
}

/* Header */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 18px;
  margin-bottom: 14px;
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.10), rgba(103, 194, 58, 0.06));
  border: 1px solid rgba(64, 158, 255, 0.12);
}

.title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.page-title {
  font-size: 18px;
  font-weight: 700;
  color: #1f2d3d;
  letter-spacing: 0.2px;
}

.status-tag {
  border-radius: 999px;
}

.sub-row {
  margin-top: 8px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  color: #5a6b7b;
  font-size: 12px;
}

.sub-item :deep(.el-icon) {
  margin-right: 4px;
  color: #6b7a88;
}

.dot {
  opacity: 0.6;
}

.copy-btn {
  padding: 0;
}

.action-wrap {
  display: flex;
  gap: 10px;
  align-items: center;
}

/* KPI */
.kpi-row {
  margin-bottom: 14px;
}

.kpi-card {
  background: #ffffff;
  border: 1px solid #eef2f7;
  border-radius: 12px;
  padding: 12px 14px;
  box-shadow: 0 6px 18px rgba(16, 24, 40, 0.05);
}

.kpi-label {
  font-size: 12px;
  color: #6b7a88;
}

.kpi-value {
  margin-top: 4px;
  font-size: 22px;
  font-weight: 800;
  color: #1f2d3d;
}

.kpi-hint {
  margin-top: 2px;
  font-size: 12px;
  color: #9aa7b3;
}

/* Sections */
.section-card {
  border-radius: 12px;
  border: 1px solid #eef2f7;
  box-shadow: 0 6px 18px rgba(16, 24, 40, 0.05);
  margin-bottom: 14px;
}

.section-card :deep(.el-card__header) {
  padding: 18px 20px;
}

.section-card :deep(.el-card__body) {
  padding: 20px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  color: #1f2d3d;
}

.desc {
  margin-top: 4px;
}

.desc :deep(.el-descriptions__table.is-bordered .el-descriptions__cell) {
  padding: 8px 10px;
  font-size: 12px;
  line-height: 1.5;
}

.desc :deep(.el-descriptions__label) {
  width: 100px;
  min-width: 100px;
}

.desc :deep(.el-descriptions__label.is-bordered-label) {
  color: #909399;
  font-weight: 700;
  background: #fafafa;
}

.desc :deep(.el-descriptions__content) {
  width: calc(100% - 100px);
}

.main-tabs :deep(.el-tabs__header) {
  margin: 0 0 15px;
}

.main-tabs :deep(.el-tabs__item) {
  height: 40px;
  padding: 0 20px;
  font-size: 14px;
  font-weight: 500;
  line-height: 40px;
  color: #303133;
}

.main-tabs :deep(.el-tabs__item.is-active),
.main-tabs :deep(.el-tabs__item:hover) {
  color: #409eff;
}

.long-text {
  margin-top: 12px;
  border-radius: 10px;
  padding: 12px 14px;
  background: #f7f9fc;
  border: 1px dashed #dfe6ef;
}

.long-title {
  font-size: 12px;
  color: #6b7a88;
  margin-bottom: 6px;
}

.long-body {
  color: #1f2d3d;
  line-height: 1.7;
  white-space: pre-wrap;
}

/* Tabs */
.main-tabs {
  margin-top: 8px;
}

.group-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.group-card {
  border-radius: 12px;
  border: 1px solid #eef2f7;
  box-shadow: 0 6px 18px rgba(16, 24, 40, 0.05);
}

.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.group-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.group-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px 10px;
  height: 22px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, #409eff, #67c23a);
}

.group-name {
  font-weight: 700;
  color: #1f2d3d;
}

.subsection-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  color: #1f2d3d;
  margin: 4px 0 10px;
}

.schedule-wrap {
  margin-top: 2px;
}

.timeline {
  position: relative;
  padding-left: 16px;
  margin-bottom: 12px;
}

.timeline-item {
  position: relative;
  display: flex;
  gap: 10px;
  padding: 10px 0;
}

.tl-dot {
  position: absolute;
  left: 0;
  top: 16px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #409eff;
  box-shadow: 0 0 0 4px rgba(64, 158, 255, 0.15);
}

.tl-content {
  margin-left: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid #eef2f7;
  background: #ffffff;
  width: 100%;
}

.tl-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-weight: 700;
  color: #1f2d3d;
}

.tl-stage {
  font-size: 13px;
}

.tl-date {
  font-size: 12px;
  color: #6b7a88;
  font-weight: 600;
}

.tl-mid {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tl-chip {
  display: inline-flex;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  color: #4a5a68;
  background: #f2f6fc;
  border: 1px solid #e6edf5;
}

.tl-bottom {
  margin-top: 6px;
  font-size: 12px;
  color: #6b7a88;
  line-height: 1.5;
  white-space: pre-wrap;
}

.step-table {
  border-radius: 10px;
  overflow: hidden;
}

/* Sub cards */
.sub-card {
  border-radius: 12px;
  border: 1px solid #eef2f7;
  box-shadow: 0 6px 18px rgba(16, 24, 40, 0.05);
}

.sub-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  color: #1f2d3d;
}

.table {
  border-radius: 0;
  overflow: hidden;
}

/* Empty */
.empty-block {
  padding: 34px 12px;
  text-align: center;
  border-radius: 12px;
  border: 1px dashed #dfe6ef;
  background: #fbfcfe;
  color: #6b7a88;
}

.empty-block i {
  font-size: 24px;
  margin-bottom: 8px;
}

.empty-title {
  font-weight: 800;
  color: #1f2d3d;
}

.empty-sub {
  margin-top: 6px;
  font-size: 12px;
  color: #7b8a97;
}

.empty-inline {
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px dashed #dfe6ef;
  background: #fbfcfe;
  color: #6b7a88;
  font-size: 12px;
}

/* Group Tabs */
.group-tabs {
  margin-top: 10px;
}

.group-subtitle {
  margin-bottom: 10px;
  padding: 8px 12px;
  background: #f7f9fc;
  border-radius: 8px;
  border-left: 4px solid #409eff;
}

.group-info {
  font-size: 14px;
  color: #1f2d3d;
  font-weight: 600;
}
</style>
