<template>
  <div class="detail-titer-tab">
    <!-- 1. Files -->
    <el-card class="section-card">
      <template #header>
        <div class="section-header">
          <div class="section-title">
            <el-icon><Files /></el-icon>
            <span>文件预览</span>
            <el-tag v-if="fileList.length" size="small" type="info" effect="plain">
              {{ fileList.length }}
            </el-tag>
          </div>
        </div>
      </template>

      <div v-if="!experimentId" class="empty-inline">实验 ID 缺失，无法加载文件</div>
      <div v-else v-loading="filesLoading" class="file-preview-panel">
        <div v-if="fileList.length" class="file-grid">
        <div v-for="file in fileList" :key="file.id" class="file-card-wrapper">
          <div class="file-card" @click="handleFileClick(file)">
            <div class="file-preview-area">
              <el-image
                v-if="isImage(file.file_name)"
                :src="file.thumb_object_url || ''"
                fit="cover"
                class="file-thumb"
              >
                <template #placeholder>
                  <div class="image-slot">
                    <el-icon class="is-loading"><Loading /></el-icon>
                  </div>
                </template>
                <template #error>
                  <div class="image-slot">
                    <el-icon><Picture /></el-icon>
                  </div>
                </template>
              </el-image>
              <div v-else class="file-icon-box">
                <el-icon class="type-icon" :class="getFileIconClass(file.file_name)">
                  <component :is="getFileIcon(file.file_name)" />
                </el-icon>
                <span class="ext-tag">{{ file.file_name.split('.').pop().toUpperCase() }}</span>
              </div>
              <div class="file-overlay">
                <span class="view-btn"><el-icon><View /></el-icon> 查看</span>
              </div>
            </div>
            <div class="file-info-area">
              <div class="file-name-text" :title="file.file_name">{{ file.file_name }}</div>
              <div class="file-meta-text">{{ file.created_time ? file.created_time.split(' ')[0] : '' }}</div>
            </div>
          </div>
        </div>
        </div>
        <div v-if="!filesLoading && fileList.length === 0" class="empty-state">
          <div class="empty-content">
            <el-icon><FolderOpened /></el-icon>
            <p>暂无文件数据</p>
            <span class="sub-text">请在效价编辑页上传相关实验文件</span>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 2. Targets & PC（列宽比例 14:10，与效价编辑页一致） -->
    <div class="data-tables-section">
      <el-row :gutter="16" class="targets-tables-row">
        <el-col :xs="24" :lg="14" class="flex-col">
          <el-card shadow="never" class="table-card full-height">
            <template #header>
              <span class="table-title">
                <el-icon><Aim /></el-icon>
                效价检测靶标
              </span>
            </template>
            <div class="table-card-body">
              <div v-if="!titerTargets.length" class="empty-inline">暂无靶标数据</div>
              <el-table
                v-else
                :data="titerTargets"
                border
                size="small"
                class="refined-table"
                style="width: 100%"
              >
                <el-table-column prop="name" label="名称" min-width="120" />
                <el-table-column prop="type" label="类型" min-width="70" />
                <el-table-column prop="species" label="种属" min-width="70" />
                <el-table-column prop="batch_no" label="批次" min-width="80" />
                <el-table-column prop="passage" label="代次" min-width="60" />
                <el-table-column prop="cell_count" label="细胞量" min-width="80" />
                <el-table-column prop="catalog_no" label="货号" min-width="80" />
                <el-table-column prop="source" label="来源" min-width="80" />
              </el-table>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="24" :lg="10" class="flex-col">
          <el-card shadow="never" class="table-card full-height">
            <template #header>
              <span class="table-title">
                <el-icon><Medal /></el-icon>
                阳性对照
              </span>
            </template>
            <div class="table-card-body">
              <div v-if="!titerPcs.length" class="empty-inline">暂无 PC 数据</div>
              <el-table
                v-else
                :data="titerPcs"
                border
                size="small"
                class="refined-table"
                style="width: 100%"
              >
                <el-table-column prop="pc_name" label="PC名称" min-width="120" />
                <el-table-column prop="catalog_batch" label="货号/批次" min-width="80" />
                <el-table-column prop="source" label="来源" min-width="80" />
                <el-table-column prop="concentration" label="浓度" min-width="80" />
              </el-table>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 3. Plates -->
    <el-card class="section-card">
      <template #header>
        <div class="section-header">
          <div class="section-title">
            <el-icon><Grid /></el-icon>
            <span>TITER 板</span>
          </div>
        </div>
      </template>

      <div v-if="!experimentId" class="empty-inline">实验 ID 缺失，无法加载板卡</div>
      <template v-else>
        <div v-loading="platesLoading">
          <el-tabs v-if="sortedAllPlates.length" v-model="activePlateName" type="card" class="plates-tabs" :key="plateTabsKey">
            <el-tab-pane
              v-for="(plate, index) in sortedAllPlates"
              :key="getPlateKey(plate)"
              :name="getPlateKey(plate)"
              lazy
            >
              <template #label>
                <span :class="{ 'is-stage-end': isStageGroupEnd(index) }">
                  {{ getPlateTabLabel(plate) }}
                </span>
              </template>
              <FacsPlateCard
                v-if="plate.plate_type === 'facs'"
                :plate-data="plate"
                :target-options="titerTargets"
                :pc-options="titerPcs"
                :file-list="fileList"
                :immune-stage-options="immuneStageOptions"
                :group-options="groupOptions"
                :is-active="activePlateName === getPlateKey(plate)"
                read-only
                @load-image-preview="loadPreviewImage"
              />
              <ElisaPlateCard
                v-else
                :plate-data="plate"
                :target-options="titerTargets"
                :pc-options="titerPcs"
                :file-list="fileList"
                :immune-stage-options="immuneStageOptions"
                :group-options="groupOptions"
                :antigen-type-options="antigenTypeOptions"
                :extra-absorbance-sheets="getElisaExtraAbsorbance(plate)"
                read-only
              />
            </el-tab-pane>
          </el-tabs>
          <div v-if="!platesLoading && sortedAllPlates.length === 0" class="empty-plates">
            <div class="empty-content">
              <el-icon><FolderOpened /></el-icon>
              <p>暂无板卡数据</p>
              <span class="sub-text">请在效价编辑页新建 FACS 或 ELISA 板</span>
            </div>
          </div>
        </div>
      </template>
    </el-card>

    <!-- 4. Conclusion -->
    <el-card class="section-card">
      <template #header>
        <div class="section-header">
          <div class="section-title">
            <el-icon><Collection /></el-icon>
            <span>效价结论</span>
          </div>
        </div>
      </template>
      <TiterConclusionPanel :model="facsConclusionModel" />
    </el-card>

    <!-- File preview dialog -->
    <el-dialog
      v-model="detailDialogVisible"
      :title="currentFile ? currentFile.file_name : '文件详情'"
      width="1100px"
      class="serum-detail-dialog serum-detail-dialog--compact"
      @close="handleDialogClose"
    >
      <div v-if="currentFile" class="dialog-flex-layout">
        <div class="dialog-preview-side">
          <div v-if="isImage(currentFile.file_name)" class="preview-container">
            <el-image
              :src="currentFile.preview_object_url || currentFile.thumb_object_url || ''"
              fit="contain"
              class="full-image"
              :preview-src-list="[currentFile.preview_object_url || currentFile.thumb_object_url || '']"
            />
          </div>
          <div v-else-if="isExcel(currentFile.file_name)" class="excel-preview-area">
            <div v-loading="excelLoading" class="excel-scroll-box">
              <table v-if="excelData.length > 0" class="modern-excel-table">
                <tbody>
                  <tr v-for="(row, rowIndex) in excelData" :key="'row-' + rowIndex">
                    <td v-for="(cell, colIndex) in row" :key="'cell-' + rowIndex + '-' + colIndex">
                      {{ cell }}
                    </td>
                  </tr>
                </tbody>
              </table>
              <div v-else-if="!excelLoading" class="excel-error">
                <el-icon><Warning /></el-icon>
                <p>无法读取 Excel 文件内容</p>
              </div>
            </div>
          </div>
          <div v-else class="generic-preview-area">
            <el-icon class="huge-icon" :class="getFileIconClass(currentFile.file_name)">
              <component :is="getFileIcon(currentFile.file_name)" />
            </el-icon>
            <div class="huge-ext">{{ currentFile.file_name.split('.').pop().toUpperCase() }}</div>
          </div>
        </div>
        <div class="dialog-info-side">
          <div class="meta-section">
            <h3 class="side-title">基本信息 <small>Information</small></h3>
            <div class="meta-list">
              <div class="meta-item">
                <span class="m-label">上传人员:</span>
                <span class="m-value">{{ currentFile.upload_user || '-' }}</span>
              </div>
              <div class="meta-item">
                <span class="m-label">创建时间:</span>
                <span class="m-value">{{ currentFile.created_time || '-' }}</span>
              </div>
              <div class="meta-item">
                <span class="m-label">最后更新:</span>
                <span class="m-value">{{ currentFile.updated_time || '-' }}</span>
              </div>
            </div>
          </div>

          <div class="action-section">
            <h3 class="side-title">操作列表 <small>Actions</small></h3>
            <div class="button-group">
              <el-button type="primary" plain @click="handleDownload(currentFile)">
                <el-icon><Download /></el-icon>
                <span>立即下载</span>
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { useAccessStore } from '@vben/stores'

import {
  Aim,
  Collection,
  Document,
  DocumentCopy,
  Download,
  Files,
  FolderOpened,
  Grid,
  Loading,
  Medal,
  Monitor,
  Picture,
  View,
  Warning,
} from '@element-plus/icons-vue'
import {
  ElButton,
  ElCard,
  ElCol,
  ElDialog,
  ElIcon,
  ElImage,
  ElMessage,
  ElRow,
  ElTabPane,
  ElTable,
  ElTableColumn,
  ElTabs,
  ElTag,
} from 'element-plus'
import * as XLSX from 'xlsx'

import { ApiFetchError, fetchApiResource, notifyApiError } from '#/api/errors'
import { fetchElisaPlates, fetchFacsPlates, fetchIndexFiles, skipGlobalErrorHandler } from '#/api/serum'
import { handleUnauthorizedError } from '#/utils/auth-session'
import { SERUM_ERRORS } from '../shared/errors'
import {
  createDefaultLowerSlotList,
  createDefaultUpperSlotList,
  parseElisaArrayBuffer,
} from '#/utils/elisaPlate'
import {
  buildFacsConclusionForPage,
} from '#/utils/serumTiterConclusion'

import ElisaPlateCard from './ElisaPlateCard.vue'
import FacsPlateCard from './FacsPlateCard.vue'
import TiterConclusionPanel from './TiterConclusionPanel.vue'

const serumApiBaseUrl = '/api'

export default {
  name: 'SerumDetailTiterTab',
  components: {
    Aim,
    Collection,
    DocumentCopy,
    Download,
    ElButton,
    ElCard,
    ElCol,
    ElDialog,
    ElIcon,
    ElImage,
    ElRow,
    ElTabPane,
    ElTable,
    ElTableColumn,
    ElTabs,
    ElTag,
    ElisaPlateCard,
    FacsPlateCard,
    Files,
    FolderOpened,
    Grid,
    Loading,
    Medal,
    Picture,
    TiterConclusionPanel,
    View,
    Warning,
  },
  props: {
    project: {
      type: Object,
      required: true,
    },
    active: {
      type: Boolean,
      default: false,
    },
  },
  setup() {
    const accessStore = useAccessStore()
    return { accessStore }
  },
  data() {
    return {
      loadedExperimentId: null,
      fileList: [],
      filesLoading: false,
      facsPlates: [],
      elisaPlates: [],
      elisaAbsPreviewCache: {},
      platesLoading: false,
      activePlateName: '',
      facsConclusionModel: null,
      fileObjectUrls: {},
      detailDialogVisible: false,
      currentFile: null,
      excelData: [],
      excelLoading: false,
    }
  },
  computed: {
    experimentId() {
      return this.project?.experiment_id || ''
    },
    titerTargets() {
      return this.project?.titer_targets || []
    },
    titerPcs() {
      return this.project?.titer_pcs || []
    },
    immuneStageOptions() {
      const steps = this.project?.steps || []
      const stages = steps.map((s) => s.stage_name).filter((s) => s && s.trim())
      return [...new Set(stages)]
    },
    groupOptions() {
      const groups = this.project?.mouse_groups || []
      const seen = new Set()
      const options = []
      for (const g of groups) {
        const id = (g.group_id || '').trim()
        if (!id || seen.has(id)) continue
        seen.add(id)
        const strain = (g.mouse_strain || '').trim()
        options.push(strain ? `${id}-${strain}` : id)
      }
      return options
    },
    antigenTypeOptions() {
      const types = new Set()
      ;(this.project?.antigens || []).forEach((a) => {
        if (a?.antigen_type?.trim()) types.add(a.antigen_type.trim())
      })
      return [...types]
    },
    sortedAllPlates() {
      const stages = this.immuneStageOptions
      const stageIdx = (s) => {
        const key = (s || '').trim()
        if (!key) return stages.length + 1
        const i = stages.indexOf(key)
        return i >= 0 ? i : stages.length
      }
      return [...(this.facsPlates || []), ...(this.elisaPlates || [])].sort((a, b) => {
        const sd = stageIdx(a.immune_stage) - stageIdx(b.immune_stage)
        if (sd) return sd
        const skA = (a.immune_stage || '').trim()
        const skB = (b.immune_stage || '').trim()
        if (skA !== skB) return skA.localeCompare(skB, 'zh-CN')
        const td = (a.plate_type === 'elisa' ? 1 : 0) - (b.plate_type === 'elisa' ? 1 : 0)
        if (td) return td
        if (a.id && !b.id) return -1
        if (!a.id && b.id) return 1
        if (a.id && b.id) return a.id - b.id
        return (a.tempId || 0) - (b.tempId || 0)
      })
    },
    plateTabsKey() {
      return this.sortedAllPlates
        .map((p) => `${this.getPlateKey(p)}@${(p.immune_stage || '').trim()}`)
        .join('|')
    },
  },
  watch: {
    active: {
      immediate: true,
      handler() {
        this.tryLoadTiterData()
      },
    },
    experimentId(newVal, oldVal) {
      if (newVal !== oldVal) {
        this.resetTiterState()
        this.tryLoadTiterData()
      }
    },
  },
  beforeUnmount() {
    this.resetTiterState()
  },
  methods: {
    tryLoadTiterData() {
      if (!this.active || !this.experimentId) return
      if (this.loadedExperimentId === this.experimentId) return
      this.loadedExperimentId = this.experimentId
      this.getFiles()
      this.getPlates()
    },
    resetTiterState() {
      Object.values(this.fileObjectUrls).forEach((url) => URL.revokeObjectURL(url))
      this.fileObjectUrls = {}
      this.fileList = []
      this.facsPlates = []
      this.elisaPlates = []
      this.elisaAbsPreviewCache = {}
      this.activePlateName = ''
      this.facsConclusionModel = null
      this.loadedExperimentId = null
      this.filesLoading = false
      this.platesLoading = false
      this.detailDialogVisible = false
      this.currentFile = null
      this.excelData = []
      this.excelLoading = false
    },
    getFiles() {
      const expId = this.experimentId
      if (!expId) return
      this.filesLoading = true
      fetchIndexFiles({ experiment_id: expId }, skipGlobalErrorHandler)
        .then((res) => {
          if (this.experimentId !== expId) return
          this.fileList = res?.items || []
          this.restoreElisaAbsorbancePreviews()
          return this.loadImageThumbs()
        })
        .catch((err) => {
          if (this.experimentId !== expId) return
          this.fileList = []
          notifyApiError(err, { messages: SERUM_ERRORS.titer.load })
        })
        .finally(() => {
          if (this.experimentId === expId) {
            this.filesLoading = false
          }
        })
    },
    getPlates() {
      const expId = this.experimentId
      if (!expId) return
      this.platesLoading = true
      Promise.all([
        fetchFacsPlates({ experiment_id: expId }, skipGlobalErrorHandler),
        fetchElisaPlates({ experiment_id: expId }, skipGlobalErrorHandler),
      ])
        .then(([facsRes, elisaRes]) => {
          if (this.experimentId !== expId) return
          this.facsPlates = (facsRes.items || []).map((p) => ({
            ...p,
            plate_type: 'facs',
            tempId: p.tempId || null,
          }))
          this.elisaPlates = (elisaRes.items || []).map((p) => ({
            ...p,
            plate_type: 'elisa',
            tempId: p.tempId || null,
            upper_slot_list: p.upper_slot_list || createDefaultUpperSlotList(),
            lower_slot_list: p.lower_slot_list || createDefaultLowerSlotList(),
            slot_groups: p.slot_groups || [],
          }))
          const first = this.sortedAllPlates[0]
          if (first) this.activePlateName = this.getPlateKey(first)
          this.restoreElisaAbsorbancePreviews()
          this.updateFacsConclusion()
        })
        .catch((err) => {
          if (this.experimentId !== expId) return
          this.facsPlates = []
          this.elisaPlates = []
          this.activePlateName = ''
          this.facsConclusionModel = null
          notifyApiError(err, { messages: SERUM_ERRORS.titer.load })
        })
        .finally(() => {
          if (this.experimentId === expId) {
            this.platesLoading = false
          }
        })
    },
    getPlateKey(plate) {
      return plate.id ? `id_${plate.id}` : `tmp_${plate.tempId}`
    },
    getPlateTabLabel(plate) {
      const type = plate.plate_type === 'elisa' ? 'ELISA' : 'FACS'
      const sk = (plate.immune_stage || '').trim()
      const n = this.sortedAllPlates.filter(
        (p) => p.plate_type === plate.plate_type && (p.immune_stage || '').trim() === sk,
      ).findIndex((p) => this.getPlateKey(p) === this.getPlateKey(plate)) + 1
      return `${type}板-${n || 1}`
    },
    isStageGroupEnd(index) {
      const plates = this.sortedAllPlates
      if (index >= plates.length - 1) return false
      const stage = (s) => (s || '').trim()
      return stage(plates[index].immune_stage) !== stage(plates[index + 1].immune_stage)
    },
    getElisaExtraAbsorbance(plate) {
      return this.elisaAbsPreviewCache[this.getPlateKey(plate)] || []
    },
    restoreElisaAbsorbancePreviews() {
      if (!this.elisaPlates.length || !this.fileList.length) return
      const tasks = this.elisaPlates
        .filter((plate) => plate.excel_file_id && !this.elisaAbsPreviewCache[this.getPlateKey(plate)])
        .map(async (plate) => {
          const file = this.fileList.find((f) => f.id === plate.excel_file_id)
          if (!file || !this.isExcel(file.file_name)) return null
          try {
            const blob = await this.fetchFileBlob(this.getDownloadUrl(file, true))
            const parsed = parseElisaArrayBuffer(await blob.arrayBuffer(), file.file_name)
            if (parsed.error || !parsed.primary?.matrix) return null
            return { key: this.getPlateKey(plate), sheets: parsed.extraSheets || [] }
          } catch (error) {
            console.error('恢复 ELISA 吸光度预览失败:', error)
            return null
          }
        })
      if (!tasks.length) return
      const expId = this.experimentId
      Promise.all(tasks).then((items) => {
        if (this.experimentId !== expId) return
        const next = { ...this.elisaAbsPreviewCache }
        for (const item of items) {
          if (!item) continue
          if (item.sheets.length) next[item.key] = item.sheets
          else delete next[item.key]
        }
        this.elisaAbsPreviewCache = next
      })
    },
    updateFacsConclusion() {
      this.facsConclusionModel = buildFacsConclusionForPage(
        this.project,
        this.titerTargets,
        this.facsPlates || [],
        this.elisaPlates || [],
      )
    },
    async handleFileClick(file) {
      this.currentFile = file
      this.excelData = []
      if (this.isExcel(file.file_name)) {
        this.detailDialogVisible = true
        await this.loadExcelData(file)
        return
      }
      if (this.isImage(file.file_name)) {
        try {
          if (!file.preview_object_url) {
            await this.loadPreviewImage(file)
          }
          this.detailDialogVisible = true
        } catch {
          // 错误已在 loadPreviewImage 中提示
        }
        return
      }
      this.detailDialogVisible = true
    },
    handleDialogClose() {
      this.excelData = []
      this.currentFile = null
    },
    async handleDownload(file) {
      try {
        const blob = await this.fetchFileBlob(this.getDownloadUrl(file))
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = file.file_name
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(url)
      } catch (error) {
        notifyApiError(error, { messages: SERUM_ERRORS.titer.download })
      }
    },
    getDownloadUrl(file, isPreview = false) {
      let url = `${serumApiBaseUrl}/serum/titer/file/download?id=${file.id}`
      if (isPreview) url += '&preview=true'
      if (file._timestamp) url += `&_t=${file._timestamp}`
      return url
    },
    getThumbnailUrl(file) {
      let url = file.thumb_url
        ? serumApiBaseUrl + (file.thumb_url.startsWith('/') ? file.thumb_url : `/${file.thumb_url}`)
        : `${serumApiBaseUrl}/serum/titer/file/download?id=${file.id}&thumb=true&w=400&h=400`
      if (file._timestamp) url += `&_t=${file._timestamp}`
      return url
    },
    getFileExt(filename) {
      return String(filename || '').split('.').pop().toLowerCase()
    },
    getFileIcon(filename) {
      const ext = this.getFileExt(filename)
      if (['xls', 'xlsx', 'csv'].includes(ext)) return Grid
      if (['doc', 'docx'].includes(ext)) return DocumentCopy
      if (['ppt', 'pptx'].includes(ext)) return Monitor
      if (['pdf'].includes(ext)) return Collection
      return Document
    },
    getFileIconClass(filename) {
      const ext = this.getFileExt(filename)
      if (['xls', 'xlsx', 'csv'].includes(ext)) return 'excel-color'
      if (['doc', 'docx'].includes(ext)) return 'word-color'
      if (['ppt', 'pptx'].includes(ext)) return 'ppt-color'
      if (['pdf'].includes(ext)) return 'pdf-color'
      if (['zip', 'rar', '7z'].includes(ext)) return 'zip-color'
      return ''
    },
    isImage(filename) {
      const ext = this.getFileExt(filename)
      return ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'].includes(ext)
    },
    isExcel(filename) {
      const ext = this.getFileExt(filename)
      return ['xls', 'xlsx', 'csv'].includes(ext)
    },
    authHeaders() {
      const token = this.accessStore.accessToken
      return token ? { Authorization: `Bearer ${token}` } : {}
    },
    async fetchFileBlob(url) {
      try {
        const response = await fetchApiResource(url, { headers: this.authHeaders() })
        return await response.blob()
      } catch (error) {
        if (error instanceof ApiFetchError && error.status === 401) {
          await handleUnauthorizedError({ response: { status: 401 } })
        }
        throw error
      }
    },
    setFileObjectUrl(file, field, key, blob) {
      const previous = file[field]
      if (previous) URL.revokeObjectURL(previous)
      const url = URL.createObjectURL(blob)
      file[field] = url
      this.fileObjectUrls[key] = url
      return url
    },
    async loadImageThumbs() {
      const expId = this.experimentId
      let downloadErrorNotified = false
      await Promise.all(
        this.fileList
          .filter((file) => this.isImage(file.file_name))
          .map(async (file) => {
            const key = `thumb_${file.id}_${file._timestamp || ''}`
            try {
              const blob = await this.fetchFileBlob(this.getThumbnailUrl(file))
              if (this.experimentId !== expId) return
              this.setFileObjectUrl(file, 'thumb_object_url', key, blob)
            } catch (error) {
              if (!downloadErrorNotified) {
                downloadErrorNotified = true
                notifyApiError(error, { messages: SERUM_ERRORS.titer.download })
              }
            }
          }),
      )
    },
    async loadPreviewImage(file) {
      const key = `preview_${file.id}_${file._timestamp || ''}`
      try {
        const blob = await this.fetchFileBlob(this.getDownloadUrl(file, true))
        this.setFileObjectUrl(file, 'preview_object_url', key, blob)
      } catch (error) {
        notifyApiError(error, { messages: SERUM_ERRORS.titer.download })
        throw error
      }
    },
    async loadExcelData(file) {
      this.excelLoading = true
      this.excelData = []
      try {
        const blob = await this.fetchFileBlob(this.getDownloadUrl(file, true))
        const arrayBuffer = await blob.arrayBuffer()
        const workbook = XLSX.read(arrayBuffer, { type: 'array' })
        const firstSheetName = workbook.SheetNames[0]
        if (!firstSheetName) {
          ElMessage.warning('Excel 文件无工作表')
          return
        }
        const worksheet = workbook.Sheets[firstSheetName]
        const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1, defval: '' })
        if (jsonData.length > 0) {
          this.excelData = jsonData
        }
      } catch (error) {
        notifyApiError(error, { messages: SERUM_ERRORS.titer.download })
      } finally {
        this.excelLoading = false
      }
    },
  },
}
</script>

<style scoped lang="scss">
.detail-titer-tab {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.section-card {
  border-radius: 12px;
  border: 1px solid #eef2f7;
  box-shadow: 0 6px 18px rgba(16, 24, 40, 0.05);
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

.empty-inline {
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px dashed #dfe6ef;
  background: #fbfcfe;
  color: #6b7a88;
  font-size: 12px;
}

.data-tables-section {
  width: 100%;
}

.targets-tables-row {
  align-items: stretch;

  :deep(.el-col) {
    display: flex;
  }
}

.flex-col {
  display: flex;
  flex-direction: column;
}

.table-card {
  border-radius: 12px;
  border: 1px solid #eef2f7;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);

  &.full-height {
    flex: 1;
    display: flex;
    flex-direction: column;
    height: 100%;
  }

  :deep(.el-card__header) {
    padding: 14px 20px;
    border-bottom: 1px solid #f0f2f5;
  }

  :deep(.el-card__body) {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 20px;
    min-height: 150px;
  }
}

.table-card-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 80px;
}

.table-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;

  .el-icon {
    color: #409eff;
  }
}

.refined-table {
  border-radius: 4px;
  overflow: hidden;

  :deep(.el-table) {
    --el-table-border-color: #ebeef5;
  }

  :deep(.el-table--border::before),
  :deep(.el-table--border::after) {
    background-color: #ebeef5;
  }

  :deep(.el-table__header-wrapper th) {
    background-color: #f8f9fb;
    color: #444;
    font-weight: 600;
    height: 32px;
    border-bottom: 1px solid #eef1f6;
  }

  :deep(.el-table__row td) {
    height: 32px;
    border-bottom: 1px solid #f0f0f0;
  }

  :deep(.el-table__cell) {
    padding: 4px 0;
  }
}

.file-preview-panel {
  min-height: 48px;
}

.file-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.empty-state,
.empty-plates {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;

  .empty-content {
    text-align: center;
    color: #c0c4cc;

    .el-icon {
      font-size: 48px;
      margin-bottom: 10px;
      opacity: 0.5;
    }

    p {
      margin: 0;
      font-size: 15px;
      color: #909399;
      font-weight: 500;
    }

    .sub-text {
      font-size: 12px;
      margin-top: 6px;
      display: block;
    }
  }
}

.empty-state {
  padding: 36px 0;
}

.empty-plates {
  padding: 40px 0;
}

.file-card-wrapper {
  width: calc(16.66% - 14px);
  min-width: 150px;
  max-width: 200px;
}

.file-card {
  background: #fff;
  border: 1px solid #eef2f7;
  border-radius: 10px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.25s ease;

  &:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 16px rgba(16, 24, 40, 0.08);
    border-color: #409eff;

    .file-overlay {
      opacity: 1;
    }
  }
}

.file-preview-area {
  height: 120px;
  position: relative;
  background: #f7f9fc;
  display: flex;
  align-items: center;
  justify-content: center;

  .file-thumb {
    width: 100%;
    height: 100%;
  }

  .file-icon-box {
    display: flex;
    flex-direction: column;
    align-items: center;

    .type-icon {
      font-size: 40px;
      color: #909399;
      margin-bottom: 6px;
    }

    .ext-tag {
      font-size: 11px;
      font-weight: 700;
      color: #fff;
      background: #909399;
      padding: 2px 6px;
      border-radius: 4px;
    }
  }

  .file-overlay {
    position: absolute;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0;
    transition: opacity 0.25s;

    .view-btn {
      color: #fff;
      font-size: 12px;
      background: rgba(255, 255, 255, 0.2);
      padding: 4px 10px;
      border-radius: 16px;
      border: 1px solid rgba(255, 255, 255, 0.5);
      display: flex;
      align-items: center;
      gap: 4px;
    }
  }
}

.file-info-area {
  padding: 10px 12px;
  border-top: 1px solid #f0f2f5;

  .file-name-text {
    font-size: 12px;
    color: #1f2d3d;
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    margin-bottom: 2px;
  }

  .file-meta-text {
    font-size: 11px;
    color: #9aa7b3;
  }
}

.image-slot {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  color: #909399;
}

.excel-color { color: #217346 !important; }
.word-color { color: #2b579a !important; }
.ppt-color { color: #d24726 !important; }
.pdf-color { color: #b30b00 !important; }
.zip-color { color: #e6a23c !important; }

.plates-tabs :deep(.el-tabs__header) {
  margin-bottom: 12px;
}

.plates-tabs :deep(.el-tabs__item:has(.is-stage-end)) {
  border-right: 3px solid #67c23a;
}

/* 文件详情弹窗（与 SerumTiter 同源，右侧只读且无重命名/替换/删除） */
:global(.el-dialog.serum-detail-dialog) {
  border-radius: 12px;
  overflow: hidden;
  margin-left: auto !important;
  margin-right: auto !important;
  display: flex;
  flex-direction: column;
}

:global(.el-dialog.serum-detail-dialog--compact) {
  width: min(1100px, 94vw) !important;
  max-width: 94vw;
}

:global(.el-dialog.serum-detail-dialog .el-dialog__header) {
  padding: 20px 24px;
  border-bottom: 1px solid #f0f2f5;
}

:global(.el-dialog.serum-detail-dialog .el-dialog__title) {
  font-weight: 600;
}

:global(.el-dialog.serum-detail-dialog .el-dialog__body) {
  padding: 0;
}

.dialog-flex-layout {
  display: flex;
  height: 520px;
}

.dialog-preview-side {
  flex: 1;
  min-width: 0;
  background: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: center;
  border-right: 1px solid #f0f2f5;
  overflow: hidden;

  .preview-container,
  .full-image {
    width: 100%;
    height: 100%;
  }

  .excel-preview-area {
    width: 100%;
    height: 100%;

    .excel-scroll-box {
      width: 100%;
      height: 100%;
      overflow: auto;
      padding: 2px;
    }
  }

  .generic-preview-area {
    text-align: center;

    .huge-icon {
      font-size: 120px;
      color: #dcdfe6;
    }

    .huge-ext {
      font-size: 24px;
      font-weight: bold;
      color: #c0c4cc;
      margin-top: 10px;
    }
  }
}

.dialog-info-side {
  flex: 0 0 340px;
  width: 340px;
  padding: 24px 22px;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  box-sizing: border-box;
  background: #fff;

  .side-title {
    margin: 0 0 16px;
    font-size: 16px;
    color: #303133;
    display: flex;
    align-items: baseline;
    justify-content: space-between;

    small {
      font-weight: normal;
      font-size: 12px;
      color: #909399;
    }
  }

  .meta-section {
    margin-bottom: 0;

    .meta-list {
      background: #f9fafc;
      padding: 16px;
      border-radius: 8px;
    }

    .meta-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 12px;
      font-size: 13px;
      line-height: 1.4;

      &:last-child {
        margin-bottom: 0;
      }

      .m-label {
        flex-shrink: 0;
        color: #909399;
        white-space: nowrap;
      }

      .m-value {
        flex-shrink: 0;
        color: #303133;
        font-weight: 500;
        text-align: right;
        white-space: nowrap;
      }
    }
  }

  .action-section {
    margin-top: 20px;

    .button-group {
      margin-top: 12px;
      display: flex;
      flex-direction: column;
      gap: 12px;

      .el-button {
        margin: 0;
        width: 100%;
        display: block;
      }
    }
  }
}

.modern-excel-table {
  border-collapse: collapse;
  width: max-content;
  background: #fff;
  border: 1px solid #ebeef5;
  font-size: 12px;

  td {
    border: 1px solid #ebeef5;
    padding: 10px 14px;
    white-space: nowrap;
    color: #606266;
  }

  tr:nth-child(even) {
    background-color: #fafbfc;
  }

  tr:hover td {
    background-color: #ecf5ff;
  }
}

.excel-error {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #909399;

  .el-icon {
    font-size: 40px;
    margin-bottom: 12px;
  }
}
</style>
