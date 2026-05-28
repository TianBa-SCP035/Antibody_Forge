<template>
  <div class="app-container serum-titer-page">
    <div class="content-wrapper">
      <!-- 1. Page Header -->
      <div class="page-header">
        <div class="header-left">
          <span class="header-icon">
            <el-icon><DataAnalysis /></el-icon>
          </span>
          <h1 class="page-title">血清效价数据管理 <span class="sub-title">Serum Titer Data</span></h1>
        </div>
        <div class="header-right">
          <el-button plain @click="goBack">
            <el-icon><ArrowLeft /></el-icon>
            <span>返回列表</span>
          </el-button>
        </div>
      </div>

      <!-- 2. Top Section: Upload & Project Info -->
      <el-row :gutter="16" class="top-section">
        <!-- 2:4 Ratio => 8:16 -->
        <el-col :md="8" :lg="8" :sm="24" class="upload-col">
          <el-card shadow="never" class="upload-card">
            <template #header>
              <div class="card-header">
                <span><el-icon><FolderOpened /></el-icon> 文件上传 (Upload)</span>
              </div>
            </template>
            <el-upload
              class="titer-upload"
              action=""
              :http-request="handleFileUpload"
              :disabled="!canManageFiles()"
              drag
              multiple
              :show-file-list="false"
            >
              <div class="dragger-wrapper">
                <el-icon class="upload-icon"><UploadFilled /></el-icon>
                <div class="el-upload__text">拖拽或<em>点击</em>上传</div>
                <div class="el-upload__tip">效价数据&实验相关文件</div>
              </div>
            </el-upload>
          </el-card>
        </el-col>
        
        <el-col :md="16" :lg="16" :sm="24" class="info-col">
          <el-card shadow="never" class="info-card">
            <template #header>
              <div class="card-header">
                <span><el-icon><Document /></el-icon> 项目信息 (Project Info)</span>
              </div>
            </template>
            <div v-if="project" class="project-info-content">
              <el-descriptions :column="2" border>
                <el-descriptions-item label="项目编号">{{ project.project_code }}</el-descriptions-item>
                <el-descriptions-item label="实验ID">{{ project.experiment_id }}</el-descriptions-item>
                <el-descriptions-item label="项目名称" :span="2">{{ project.project_name }}</el-descriptions-item>
                <el-descriptions-item label="归类鼠型">{{ project.mouse_strain || '-' }}</el-descriptions-item>
                <el-descriptions-item label="负责人">{{ project.owner }}</el-descriptions-item>
                
                <el-descriptions-item label="靶点类型">{{ project.target_type || '-' }}</el-descriptions-item>
                <el-descriptions-item label="检测方法">{{ project.assay_method || '-' }}</el-descriptions-item>
                <el-descriptions-item label="备注" :span="2">{{ project.remark || '-' }}</el-descriptions-item>
              </el-descriptions>
            </div>
            <div v-else class="info-empty">
              <el-skeleton :rows="5" animated />
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 3. File Preview Section -->
      <div class="file-preview-section">
        <div class="section-header">
          <h2 class="section-title">
            <span class="title-text"><el-icon><Files /></el-icon> 文件预览 <small class="eng">File Preview</small></span>
            <span v-if="fileList.length > 0" class="custom-file-badge">{{ fileList.length }}</span>
          </h2>
        </div>
        
        <el-card shadow="never" class="file-list-card">
          <div v-loading="filesLoading" class="file-grid">
            <div v-for="file in fileList" :key="file.id" class="file-card-wrapper">
              <div class="file-card" @click="handleFileClick(file)">
                <div class="file-preview-area">
                  <!-- Image Preview -->
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
                  <!-- Other File Icon -->
                  <div v-else class="file-icon-box">
                    <el-icon class="type-icon" :class="getFileIconClass(file.file_name)">
                      <component :is="getFileIcon(file.file_name)" />
                    </el-icon>
                    <span class="ext-tag">{{ file.file_name.split('.').pop().toUpperCase() }}</span>
                  </div>
                  
                  <div class="file-overlay">
                    <span class="view-btn"><el-icon><View /></el-icon> 查看详情</span>
                  </div>
                </div>
                <div class="file-info-area">
                  <div class="file-name-text" :title="file.file_name">{{ file.file_name }}</div>
                  <div class="file-meta-text">{{ file.created_time ? file.created_time.split(' ')[0] : '' }}</div>
                </div>
              </div>
            </div>
            
            <div v-if="!filesLoading && fileList.length === 0" class="empty-state">
              <div class="empty-content">
                <el-icon><FolderOpened /></el-icon>
                <p>暂无文件数据</p>
                <span class="sub-text">请在上方区域上传相关实验文件</span>
              </div>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 4. Data Tables Section -->
      <div class="data-tables-section" style="margin-top: 16px;">
        <el-row :gutter="16">
          <!-- Target Table -->
          <el-col :span="14" class="flex-col">
            <el-card shadow="never" class="table-card full-height">
              <template #header>
                <div class="card-header space-between">
                  <span class="table-title"><el-icon><Aim /></el-icon> 效价检测靶标</span>
                  <el-button type="text" class="add-btn" :disabled="!canEditTiter()" @click="handleAddTarget">+ 新增</el-button>
                </div>
              </template>
              <el-table :data="titer_targets" size="small" border class="refined-table" style="width: 100%">
                <el-table-column label="名称" min-width="120">
                  <template #default="{row}">
                    <el-input v-model="row.name" size="small" placeholder="必填" @change="autoSaveTargets" />
                  </template>
                </el-table-column>
                <el-table-column label="类型" min-width="70">
                  <template #default="{row}">
                     <el-select v-model="row.type" size="small" placeholder="选择" @change="autoSaveTargets">
                        <el-option label="细胞" value="细胞" />
                        <el-option label="蛋白" value="蛋白" />
                     </el-select>
                  </template>
                </el-table-column>
                <el-table-column label="种属" min-width="70">
                  <template #default="{row}">
                    <el-select v-model="row.species" size="small" placeholder="选择" @change="autoSaveTargets">
                      <el-option label="人" value="人" />
                      <el-option label="猴" value="猴" />
                      <el-option label="鼠" value="鼠" />
                      <el-option label="狗" value="狗" />
                      <el-option label="猫" value="猫" />
                      <el-option label="空白" value="空白" />
                    </el-select>
                  </template>
                </el-table-column>
                <el-table-column label="批次" min-width="80">
                  <template #default="{row}">
                    <el-input v-model="row.batch_no" size="small" placeholder="-" @change="autoSaveTargets" />
                  </template>
                </el-table-column>
                <el-table-column label="代次" min-width="60">
                  <template #default="{row}">
                    <el-input v-model="row.passage" size="small" placeholder="-" @change="autoSaveTargets" />
                  </template>
                </el-table-column>
                <el-table-column label="细胞量" min-width="80">
                  <template #default="{row}">
                    <el-input v-model="row.cell_count" size="small" placeholder="-" @change="autoSaveTargets" />
                  </template>
                </el-table-column>
                <el-table-column label="货号" min-width="80">
                  <template #default="{row}">
                    <el-input v-model="row.catalog_no" size="small" placeholder="-" @change="autoSaveTargets" />
                  </template>
                </el-table-column>
                <el-table-column label="来源" min-width="80">
                  <template #default="{row}">
                    <el-input v-model="row.source" size="small" placeholder="-" @change="autoSaveTargets" />
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="50px" align="center">
                  <template #default="scope">
                    <el-button type="text" class="danger-text" :disabled="!canEditTiter()" @click="handleDeleteTarget(scope.$index)">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
          </el-col>
          
          <!-- PC Table -->
          <el-col :span="10" class="flex-col">
            <el-card shadow="never" class="table-card full-height">
              <template #header>
                <div class="card-header space-between">
                  <span class="table-title"><el-icon><Medal /></el-icon> 阳性对照</span>
                  <el-button type="text" class="add-btn" :disabled="!canEditTiter()" @click="handleAddPc">+ 新增</el-button>
                </div>
              </template>
              <el-table :data="titer_pcs" size="small" border class="refined-table" style="width: 100%">
                <el-table-column label="PC名称" min-width="120">
                  <template #default="{row}">
                    <el-input v-model="row.pc_name" size="small" placeholder="必填" @change="autoSavePcs" />
                  </template>
                </el-table-column>
                <el-table-column label="货号/批次" min-width="80">
                  <template #default="{row}">
                    <el-input v-model="row.catalog_batch" size="small" placeholder="-" @change="autoSavePcs" />
                  </template>
                </el-table-column>
                <el-table-column label="来源" min-width="80">
                  <template #default="{row}">
                    <el-input v-model="row.source" size="small" placeholder="-" @change="autoSavePcs" />
                  </template>
                </el-table-column>
                <el-table-column label="浓度" min-width="80">
                  <template #default="{row}">
                    <el-input v-model="row.concentration" size="small" placeholder="-" @change="autoSavePcs" />
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="50px" align="center">
                  <template #default="scope">
                     <el-button type="text" class="danger-text" :disabled="!canEditTiter()" @click="handleDeletePc(scope.$index)">
                       <el-icon><Delete /></el-icon>
                     </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
          </el-col>
        </el-row>
      </div>

      <!-- 5. FACS Plate Management Section -->
      <div class="facs-plate-section" style="margin-top: 16px;">
        <div class="section-header">
          <h2 class="section-title">
            <span class="title-text"><el-icon><Grid /></el-icon> TITER板管理 <small class="eng">TITER Plate Management</small></span>
          </h2>
          <div class="header-buttons">
            <el-button type="primary" class="plate-create-btn" :disabled="!canEditTiter()" @click="handleAddPlate">
              <el-icon><Plus /></el-icon>
              <span>新建FACS板</span>
            </el-button>
            <el-button type="success" class="plate-create-btn" :disabled="!canEditTiter()" @click="handleAddElisaPlate">
              <el-icon><Plus /></el-icon>
              <span>新建Elisa板</span>
            </el-button>
          </div>
        </div>

        <el-tabs v-model="activePlateName" type="card" class="plates-tabs">
          <el-tab-pane
            v-for="(plate, index) in sortedAllPlates"
            :key="getPlateKey(plate)"
            :name="getPlateKey(plate)"
            lazy
          >
            <template #label>
              <span
                title="右键复制鼠号和分组标题"
                @contextmenu.prevent="openPlateCopyDialog(plate)"
              >
                {{ getPlateTabLabel(plate, index) }}
              </span>
            </template>
            <FacsPlateCard
              v-if="plate.plate_type === 'facs'"
              :plate-data="plate"
              :target-options="titer_targets"
              :pc-options="titer_pcs"
              :file-list="fileList"
              :immune-stage-options="immuneStageOptions"
              :group-options="groupOptions"
              :is-active="activePlateName === getPlateKey(plate)"
              :is-saving="savingPlateKeys[getPlateKey(plate)]"
              :is-editable="canEditTiter()"
              @delete="handleDeletePlate"
              @excel-file-change="(payload) => handlePlateExcelChange(payload, plate)"
              @load-image-preview="loadPreviewImage"
              @save="handleSavePlate"
            />
            <ElisaPlateCard
              v-else
              :plate-data="plate"
              :target-options="titer_targets"
              :pc-options="titer_pcs"
              :file-list="fileList"
              :immune-stage-options="immuneStageOptions"
              :group-options="groupOptions"
              :antigen-type-options="antigenTypeOptions"
              :extra-absorbance-sheets="getElisaExtraAbsorbance(plate)"
              :is-saving="savingPlateKeys[getPlateKey(plate)]"
              :is-editable="canEditTiter()"
              @delete="handleDeletePlate"
              @excel-file-change="(payload) => handleElisaExcelChange(payload, plate)"
              @save="handleSavePlate"
            />
          </el-tab-pane>
        </el-tabs>

        <div v-if="!platesLoading && sortedAllPlates.length === 0" class="empty-plates">
          <div class="empty-content">
            <el-icon><FolderOpened /></el-icon>
            <p>暂无板卡数据</p>
            <span class="sub-text">点击上方「新建FACS板」或「新建Elisa板」添加</span>
          </div>
        </div>
      </div>

      <!-- 6. Titer Conclusion (read-only, computed from plates) -->
      <div class="titer-conclusion-section" style="margin-top: 8px; margin-bottom: 36px;">
        <div class="section-header">
          <h2 class="section-title">
            <span class="title-text">
              <el-icon><Collection /></el-icon>
              效价结论
              <small class="eng">Titer Conclusion</small>
            </span>
          </h2>
        </div>
        <el-card shadow="never" class="conclusion-card">
          <TiterConclusionPanel :model="facsConclusionModel" />
        </el-card>
      </div>
    </div>

    <el-dialog
      v-model="plateCopyDialogVisible"
      title="复制鼠号和分组标题"
      width="620px"
    >
      <el-form label-width="85px">
        <el-form-item label="来源板">
          <el-input :value="copySourcePlateLabel" disabled />
        </el-form-item>
        <el-form-item label="目标板">
          <div class="copy-target-row">
            <el-select
              v-model="copyTargetPlateKeys"
              multiple
              collapse-tags
              collapse-tags-tooltip
              :max-collapse-tags="2"
              class="copy-target-select"
              placeholder="请选择同类型目标板（可多选）"
            >
              <el-option
                v-for="option in copyTargetPlateOptions"
                :key="option.key"
                :label="option.label"
                :value="option.key"
              />
            </el-select>
            <div class="copy-target-actions">
              <el-button @click="plateCopyDialogVisible = false">取消</el-button>
              <el-button type="primary" :disabled="!copyTargetPlateKeys.length" @click="confirmCopyPlateSlots">确定复制</el-button>
            </div>
          </div>
        </el-form-item>
      </el-form>
    </el-dialog>

    <!-- 4. File Detail Dialog -->
    <el-dialog
      :title="currentFile ? currentFile.file_name : '文件详情'"
      v-model="detailDialogVisible"
      width="70%"
      class="serum-detail-dialog"
      @close="handleDialogClose"
    >
      <div v-if="currentFile" class="dialog-flex-layout">
        <div class="dialog-preview-side">
          <!-- Large Preview -->
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
            <el-form label-position="top">
              <el-form-item label="重命名 (Rename)">
                <el-input v-model="editFileName" placeholder="输入新文件名">
                  <template #append>
                    <el-button type="primary" :disabled="!canManageFiles()" @click="handleRename">保存</el-button>
                  </template>
                </el-input>
              </el-form-item>
              
              <div class="button-group">
                <el-button type="primary" plain @click="handleDownload(currentFile)">
                  <el-icon><Download /></el-icon>
                  <span>立即下载</span>
                </el-button>
                <el-upload
                  action=""
                  :http-request="handleReplaceFile"
                  :show-file-list="false"
                  :disabled="!canManageFiles()"
                  class="replace-uploader"
                >
                  <el-button type="warning" plain :disabled="!canManageFiles()">
                    <el-icon><Refresh /></el-icon>
                    <span>替换文件</span>
                  </el-button>
                </el-upload>
                <el-button type="danger" plain :disabled="!canManageFiles()" @click="handleDeleteFile(currentFile)">
                  <el-icon><Delete /></el-icon>
                  <span>删除文件</span>
                </el-button>
              </div>
            </el-form>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { useAccessStore, useUserStore } from '@vben/stores'

import {
  Aim,
  ArrowLeft,
  DataAnalysis,
  Collection,
  Delete,
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
  Plus,
  Refresh,
  View,
  Warning,
  UploadFilled,
} from '@element-plus/icons-vue'
import {
  ElButton,
  ElCard,
  ElCol,
  ElDescriptions,
  ElDescriptionsItem,
  ElDialog,
  ElForm,
  ElFormItem,
  ElIcon,
  ElImage,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElRow,
  ElSelect,
  ElSkeleton,
  ElTabPane,
  ElTable,
  ElTableColumn,
  ElTabs,
  ElUpload,
} from 'element-plus'
import * as XLSX from 'xlsx'
import FacsPlateCard from './FacsPlateCard.vue'
import ElisaPlateCard from './ElisaPlateCard.vue'
import TiterConclusionPanel from './TiterConclusionPanel.vue'
import {
  deleteElisaPlate,
  deleteFacsPlate,
  fetchDetail,
  fetchElisaPlates,
  fetchFacsPlates,
  fetchIndexFiles,
  renameIndexFile,
  replaceIndexFile,
  saveElisaPlate,
  saveFacsPlate,
  saveIndexFile,
  deleteIndexFile,
  saveTiterPcs,
  saveTiterTargets,
} from '#/api/serum'
import {
  computeAutoPositiveFromPlate,
  createDefaultLowerSlotList,
  createDefaultUpperSlotList,
  normalizeSlotList,
  parseElisaArrayBuffer,
} from '#/utils/elisaPlate'
import { parseFacsExcelFromRows, POSITIVE_RATE_THRESHOLD } from '#/utils/facsExcelPositive'
import {
  buildFacsConclusionForPage,
  fingerprintElisaPlates,
  fingerprintFacsPlates,
} from '#/utils/serumTiterConclusion'
import {
  canEditSerumTiter,
  canManageSerumTiterFiles,
  getSerumUserName,
} from '#/utils/serumPermission'

const serumApiBaseUrl = import.meta.env.VITE_SERUM_API_URL || '/serum-api'

/** handleSavePlate 写入后端的防抖 */
const PLATE_SAVE_DEBOUNCE_MS = 500
/** 结论刷新固定延迟 */
const CONCLUSION_REFRESH_DELAY_MS = 300

export default {
  name: 'SerumTiter',
  components: {
    Aim,
    ArrowLeft,
    DataAnalysis,
    Collection,
    Delete,
    Document,
    DocumentCopy,
    Download,
    ElButton,
    ElCard,
    ElCol,
    ElDescriptions,
    ElDescriptionsItem,
    ElDialog,
    ElForm,
    ElFormItem,
    ElIcon,
    ElImage,
    ElInput,
    ElOption,
    ElRow,
    ElSelect,
    ElSkeleton,
    ElTabPane,
    ElTable,
    ElTableColumn,
    ElTabs,
    ElUpload,
    ElisaPlateCard,
    FacsPlateCard,
    TiterConclusionPanel,
    Files,
    FolderOpened,
    Grid,
    Loading,
    Medal,
    Monitor,
    Picture,
    Plus,
    Refresh,
    UploadFilled,
    View,
    Warning,
  },
  setup() {
    const accessStore = useAccessStore()
    const userStore = useUserStore()

    return {
      accessStore,
      userStore,
    }
  },
  data() {
    return {
      project_id: null,
      experiment_id: null,
      project: null,
      fileList: [],
      filesLoading: false,
      
      // Dialog
      detailDialogVisible: false,
      currentFile: null,
      editFileName: '',
      
      // Excel Preview
      excelData: [],
      excelLoading: false,

      // Target & PC Tables
      titer_targets: [],
      titer_pcs: [],
      targetsLoading: false,
      pcsLoading: false,
      targetsTimer: null,
      pcsTimer: null,

      // Plates
      facsPlates: [],
      elisaPlates: [],
      elisaAbsPreviewCache: {},
      platesLoading: false,
      activePlateName: '',
      plateCopyDialogVisible: false,
      copySourcePlateKey: '',
      copyTargetPlateKeys: [],
      plateTimers: {},
      plateSaveSeq: {},
      savingPlateKeys: {},
      fileObjectUrls: {},

      facsConclusionModel: null,
      conclusionRefreshTimer: null,
      conclusionFingerprint: '',
    }
  },
  computed: {
    currentUserInfo() {
      return this.userStore.userInfo || {}
    },
    currentUserName() {
      return getSerumUserName(this.currentUserInfo) || 'unknown'
    },
    immuneStageOptions() {
      if (!this.project || !this.project.steps) return []
      const stages = this.project.steps.map(s => s.stage_name).filter(s => s && s.trim())
      return [...new Set(stages)]
    },
    groupOptions() {
      if (!this.project?.mouse_groups) return []
      const seen = new Set()
      const options = []
      for (const g of this.project.mouse_groups) {
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
      return [...(this.facsPlates || []), ...(this.elisaPlates || [])].sort((a, b) => {
        const aHas = !!a.id
        const bHas = !!b.id
        if (aHas && !bHas) return -1
        if (!aHas && bHas) return 1
        if (aHas && bHas) return a.id - b.id
        return (a.tempId || 0) - (b.tempId || 0)
      })
    },
    copySourcePlate() {
      return this.sortedAllPlates.find((plate) => this.getPlateKey(plate) === this.copySourcePlateKey) || null
    },
    copySourcePlateLabel() {
      if (!this.copySourcePlate) return ''
      const index = this.sortedAllPlates.findIndex((plate) => this.getPlateKey(plate) === this.copySourcePlateKey)
      return this.getPlateTabLabel(this.copySourcePlate, index)
    },
    copyTargetPlateOptions() {
      const source = this.copySourcePlate
      if (!source) return []
      return this.sortedAllPlates
        .map((plate, index) => ({ plate, index, key: this.getPlateKey(plate) }))
        .filter((item) => item.key !== this.copySourcePlateKey && item.plate.plate_type === source.plate_type)
        .map((item) => ({
          key: item.key,
          label: this.getPlateTabLabel(item.plate, item.index),
        }))
    },
  },
  watch: {
    facsPlates: {
      handler() {
        this.scheduleFacsConclusionRefresh()
      },
      deep: true,
    },
    elisaPlates: {
      handler() {
        this.scheduleFacsConclusionRefresh()
      },
      deep: true,
    },
    titer_targets: {
      handler() {
        this.scheduleFacsConclusionRefresh()
      },
      deep: true,
    },
    project: {
      handler() {
        this.scheduleFacsConclusionRefresh()
      },
      deep: false,
    },
  },
  created() {
    this.project_id = this.$route.query.id
    this.experiment_id = this.$route.query.experiment_id
    
    if (this.project_id) {
      this.getProjectInfo()
    } else if (this.experiment_id) {
      this.project = { experiment_id: this.experiment_id }
      this.getFiles()
      this.getPlates()
    }
  },
  beforeUnmount() {
    this.clearMemory()
  },
  beforeRouteLeave(to, from, next) {
    this.clearMemory()
    next()
  },
  methods: {
    scheduleFacsConclusionRefresh(immediate = false) {
      if (this.conclusionRefreshTimer) {
        clearTimeout(this.conclusionRefreshTimer)
        this.conclusionRefreshTimer = null
      }
      if (immediate) {
        this.refreshFacsConclusion()
        return
      }
      this.conclusionRefreshTimer = setTimeout(() => {
        this.conclusionRefreshTimer = null
        this.refreshFacsConclusion()
      }, CONCLUSION_REFRESH_DELAY_MS)
    },
    /**
     * 结论刷新判定指纹（最小依赖集）：
     * - FACS 板位与阳性孔
     * - 靶标 id/name/species
     * - 方案里的分组/步骤/抗原类型
     */
    buildFacsConclusionFingerprint() {
      const plateFp = fingerprintFacsPlates(this.facsPlates)
      const elisaFp = fingerprintElisaPlates(this.elisaPlates)
      const targetsFp = JSON.stringify(
        (this.titer_targets || []).map((t) => [t?.id ?? '', t?.name ?? '', t?.species ?? '']),
      )
      const projectFp = JSON.stringify({
        mouse_groups: (this.project?.mouse_groups || []).map((g) => ({
          group_id: g?.group_id ?? '',
          mouse_strain: g?.mouse_strain ?? '',
          mouse_no_list: g?.mouse_no_list ?? '',
          mice: (g?.mouse_registry?.mice || []).map((m) => ({
            no: m?.no ?? '',
            alive: m?.alive !== false,
          })),
        })),
        steps: (this.project?.steps || []).map((s) => ({
          group_id: s?.group_id ?? '',
          stage_name: s?.stage_name ?? '',
          antigen_id: s?.antigen_id ?? '',
        })),
        antigens: (this.project?.antigens || []).map((a) => ({
          antigen_id: a?.antigen_id ?? '',
          antigen_type: a?.antigen_type ?? '',
        })),
      })
      return [plateFp, elisaFp, targetsFp, projectFp].join('@@')
    },
    refreshFacsConclusion() {
      const fp = this.buildFacsConclusionFingerprint()
      if (fp === this.conclusionFingerprint && this.facsConclusionModel) return
      this.conclusionFingerprint = fp
      this.facsConclusionModel = buildFacsConclusionForPage(
        this.project,
        this.titer_targets,
        this.facsPlates || [],
        this.elisaPlates || [],
      )
    },
    clearMemory() {
      if (this.targetsTimer) {
        clearTimeout(this.targetsTimer)
        this.targetsTimer = null
      }
      if (this.pcsTimer) {
        clearTimeout(this.pcsTimer)
        this.pcsTimer = null
      }
      Object.values(this.plateTimers).forEach(t => clearTimeout(t))
      this.plateTimers = {}
      if (this.conclusionRefreshTimer) {
        clearTimeout(this.conclusionRefreshTimer)
        this.conclusionRefreshTimer = null
      }
      
      this.excelData = []
      this.facsConclusionModel = null
      this.conclusionFingerprint = ''
      this.currentFile = null
      this.fileList = []
      Object.values(this.fileObjectUrls).forEach(url => URL.revokeObjectURL(url))
      this.fileObjectUrls = {}
      
      this.titer_targets = []
      this.titer_pcs = []
    },
    getProjectInfo() {
      fetchDetail(this.project_id).then(res => {
        if (res.data) {
          this.project = res.data
          this.titer_targets = this.project.titer_targets || []
          this.titer_pcs = this.project.titer_pcs || []
          if (!this.experiment_id) {
            this.experiment_id = this.project.experiment_id
          }
          this.getFiles()
          this.getPlates()
        }
      })
    },
    goBack() {
      this.$router.go(-1)
    },
    // --- File Methods ---
    getFiles() {
      const expId = this.experiment_id || (this.project ? this.project.experiment_id : null)
      if (!expId) return
      
      this.filesLoading = true
      fetchIndexFiles({ experiment_id: expId }).then(res => {
        this.fileList = res.data.items || []
        this.restoreElisaAbsorbancePreviews()
        this.loadImageThumbs()
        this.filesLoading = false
      }).catch(() => { this.filesLoading = false })
    },
    handleFileUpload(param) {
      if (!this.canManageFiles()) {
        ElMessage.warning('您没有权限编辑此项目')
        return
      }
      if (!this.experiment_id) {
        ElMessage.error('实验ID不存在，无法上传')
        return
      }
      const formData = new FormData()
      formData.append('file', param.file)
      formData.append('experiment_id', this.experiment_id)
      
      saveIndexFile(formData).then(res => {
        ElMessage.success('上传成功')
        this.getFiles()
      }).catch(err => {
        console.error(err)
        ElMessage.error('上传失败')
      })
    },
    
    // --- Detail & Actions ---
    handleFileClick(file) {
      this.currentFile = file
      this.editFileName = file.file_name
      
      if (this.isExcel(file.file_name)) {
        this.loadExcelData(file)
      } else if (this.isImage(file.file_name)) {
        this.loadPreviewImage(file)
      } else {
        this.excelData = []
      }
      
      this.detailDialogVisible = true
    },
    handleDialogClose() {
      this.clearDialogMemory()
    },
    clearDialogMemory() {
      this.excelData = []
      this.currentFile = null
      this.editFileName = ''
    },
    handleRename() {
      if (!this.canManageFiles()) {
        ElMessage.warning('您没有权限编辑此项目')
        return
      }
      if (!this.currentFile || !this.editFileName) return
      if (this.editFileName === this.currentFile.file_name) return
      
      renameIndexFile({ 
        id: this.currentFile.id, 
        new_name: this.editFileName,
      }).then(res => {
        ElMessage.success('重命名成功')
        this.currentFile.file_name = this.editFileName 
        this.getFiles() 
      }).catch(() => {
        ElMessage.error('重命名失败')
      })
    },
    handleReplaceFile(param) {
      if (!this.canManageFiles()) {
        ElMessage.warning('您没有权限编辑此项目')
        return
      }
      if (!this.currentFile) return
      
      ElMessageBox.confirm('确定要替换当前文件吗? 原文件将被覆盖。', '警告', {
        type: 'warning'
      }).then(() => {
        const formData = new FormData()
        formData.append('file', param.file)
        formData.append('id', this.currentFile.id)
        
        replaceIndexFile(formData).then(res => {
          ElMessage.success('替换成功')
          
          const savedFile = res.data || {}
          const uploadUser = savedFile.upload_user || this.currentUserName
          const now = new Date().toISOString().replace('T', ' ').substring(0, 19)
          const newFileName = savedFile.file_name || param.file.name
          
          this.currentFile.file_name = newFileName
          this.currentFile.upload_user = uploadUser
          this.currentFile.updated_time = savedFile.updated_time || now
          this.currentFile._timestamp = Date.now()
          this.editFileName = newFileName
          
          if (this.isExcel(newFileName)) {
            this.loadExcelData(this.currentFile)
          }
          
          const fileInList = this.fileList.find(f => f.id === this.currentFile.id)
          if (fileInList) {
            fileInList.file_name = newFileName
            fileInList.upload_user = uploadUser
            fileInList.updated_time = savedFile.updated_time || now
            fileInList._timestamp = Date.now()
          }
        }).catch(err => {
          console.error('替换文件失败:', err)
          ElMessage.error('替换失败')
        })
      }).catch(() => {})
    },
    handleDeleteFile(file) {
      if (!this.canManageFiles()) {
        ElMessage.warning('您没有权限编辑此项目')
        return
      }
      ElMessageBox.confirm(`确定删除文件 "${file.file_name}" 吗?`, '提示', {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消'
      }).then(() => {
        deleteIndexFile({ id: file.id }).then(() => {
          ElMessage.success('删除成功')
          this.detailDialogVisible = false
          this.getFiles()
        })
      }).catch(() => {})
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
        console.error('下载文件失败:', error)
        ElMessage.error('下载失败')
      }
    },
    
    getDownloadUrl(file, isPreview = false) {
      let url = serumApiBaseUrl + `/serum/titer/file/download?id=${file.id}`
      if (isPreview) {
        url += '&preview=true'
      }
      if (file._timestamp) {
        url += `&_t=${file._timestamp}`
      }
      return url
    },
    getImageUrl(file) {
      return file.thumb_object_url || ''
    },
    getThumbnailUrl(file) {
      let url = file.thumb_url
        ? serumApiBaseUrl + (file.thumb_url.startsWith('/') ? file.thumb_url : `/${file.thumb_url}`)
        : serumApiBaseUrl + `/serum/titer/file/download?id=${file.id}&thumb=true&w=400&h=400`
      if (file._timestamp) {
        url += `&_t=${file._timestamp}`
      }
      return url
    },
    getFileIcon(filename) {
      const ext = filename.split('.').pop().toLowerCase()
      if (['xls', 'xlsx', 'csv'].includes(ext)) return Grid
      if (['doc', 'docx'].includes(ext)) return DocumentCopy
      if (['ppt', 'pptx'].includes(ext)) return Monitor
      if (['pdf'].includes(ext)) return Collection
      if (['zip', 'rar', '7z'].includes(ext)) return FolderOpened
      return Document
    },
    getFileIconClass(filename) {
      const ext = filename.split('.').pop().toLowerCase()
      if (['xls', 'xlsx', 'csv'].includes(ext)) return 'excel-color'
      if (['doc', 'docx'].includes(ext)) return 'word-color'
      if (['ppt', 'pptx'].includes(ext)) return 'ppt-color'
      if (['pdf'].includes(ext)) return 'pdf-color'
      if (['zip', 'rar', '7z'].includes(ext)) return 'zip-color'
      return ''
    },
    isImage(filename) {
      const ext = filename.split('.').pop().toLowerCase()
      return ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'].includes(ext)
    },
    isExcel(filename) {
      const ext = filename.split('.').pop().toLowerCase()
      return ['xls', 'xlsx', 'csv'].includes(ext)
    },
    authHeaders() {
      const token = this.accessStore.accessToken
      return token ? { Authorization: `Bearer ${token}` } : {}
    },
    async fetchFileBlob(url) {
      const response = await fetch(url, { headers: this.authHeaders() })
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      return await response.blob()
    },
    setFileObjectUrl(file, field, key, blob) {
      const previous = file[field]
      if (previous) {
        URL.revokeObjectURL(previous)
      }
      const url = URL.createObjectURL(blob)
      file[field] = url
      this.fileObjectUrls[key] = url
      return url
    },
    async loadImageThumbs() {
      await Promise.all(
        this.fileList
          .filter(file => this.isImage(file.file_name))
          .map(async file => {
            const key = `thumb_${file.id}_${file._timestamp || ''}`
            try {
              const blob = await this.fetchFileBlob(this.getThumbnailUrl(file))
              this.setFileObjectUrl(file, 'thumb_object_url', key, blob)
            } catch (error) {
              console.error('加载缩略图失败:', error)
            }
          })
      )
    },
    async loadPreviewImage(file) {
      const key = `preview_${file.id}_${file._timestamp || ''}`
      try {
        const blob = await this.fetchFileBlob(this.getDownloadUrl(file, true))
        this.setFileObjectUrl(file, 'preview_object_url', key, blob)
      } catch (error) {
        console.error('加载图片预览失败:', error)
      }
    },
    async loadExcelSheetRows(file) {
      const url = this.getDownloadUrl(file, true)
      const blob = await this.fetchFileBlob(url)
      const arrayBuffer = await blob.arrayBuffer()
      const workbook = XLSX.read(arrayBuffer, { type: 'array' })
      const firstSheetName = workbook.SheetNames[0]
      const worksheet = workbook.Sheets[firstSheetName]
      return XLSX.utils.sheet_to_json(worksheet, { header: 1, defval: '' })
    },
    async loadExcelData(file) {
      this.excelLoading = true
      this.excelData = []

      try {
        const jsonData = await this.loadExcelSheetRows(file)
        if (jsonData.length > 0) {
          this.excelData = jsonData
        }
      } catch (error) {
        console.error('读取 Excel 文件失败:', error)
      } finally {
        this.excelLoading = false
      }
    },
    async handlePlateExcelChange({ fileId }, plate) {
      if (!this.canEditTiter() || !plate) return

      if (!fileId) {
        plate.positive_well_list = []
        this.handleSavePlate(plate)
        return
      }

      const file = this.fileList.find((f) => f.id === fileId)
      if (!file || !this.isExcel(file.file_name)) {
        ElMessage.warning('未找到有效的 Excel 文件')
        return
      }

      try {
        const rows = await this.loadExcelSheetRows(file)
        const { instrumentType, positiveWells, error } = parseFacsExcelFromRows(rows)

        if (error) {
          ElMessage.warning('无法识别 Excel 格式或阳性率表格，请检查文件')
          return
        }

        plate.instrument_type = instrumentType
        plate.positive_well_list = positiveWells
        this.handleSavePlate(plate)

        ElMessage.success(
          `已识别为${instrumentType}仪器，自动标注 ${positiveWells.length} 个阳性孔（>${POSITIVE_RATE_THRESHOLD}%）`,
        )
      } catch (error) {
        console.error('解析 Excel 阳性率失败:', error)
        ElMessage.error('读取或解析 Excel 失败')
      }
    },

    // --- Table Actions ---
    handleAddTarget() {
      if (!this.canEditTiter()) {
        ElMessage.warning('您没有权限编辑此项目')
        return
      }
      this.titer_targets.push({
        name: '', type: '', species: '', batch_no: '', passage: '', cell_count: '', catalog_no: '', source: '', isNew: true
      })
      this.autoSaveTargets()
    },
    handleDeleteTarget(index) {
      if (!this.canEditTiter()) {
        ElMessage.warning('您没有权限编辑此项目')
        return
      }
      this.titer_targets.splice(index, 1)
      this.autoSaveTargets()
    },
    autoSaveTargets() {
      if (!this.canEditTiter()) return
      if (!this.experiment_id || this.targetsLoading) return
      this.targetsLoading = true
      if (this.targetsTimer) clearTimeout(this.targetsTimer)
      this.targetsTimer = setTimeout(() => {
        saveTiterTargets({
          experiment_id: this.experiment_id,
          targets: this.titer_targets
        }).then(res => {
          if (res.data && res.data.items) {
            this.titer_targets = res.data.items
          }
        }).catch(err => {
          console.error('保存失败:', err)
          ElMessage.error('保存失败')
        }).finally(() => {
          this.targetsLoading = false
        })
      }, 500)
    },

    handleAddPc() {
      if (!this.canEditTiter()) {
        ElMessage.warning('您没有权限编辑此项目')
        return
      }
      this.titer_pcs.push({
        pc_name: '', catalog_batch: '', source: '', concentration: '', isNew: true
      })
      this.autoSavePcs()
    },
    handleDeletePc(index) {
      if (!this.canEditTiter()) {
        ElMessage.warning('您没有权限编辑此项目')
        return
      }
      this.titer_pcs.splice(index, 1)
      this.autoSavePcs()
    },
    autoSavePcs() {
      if (!this.canEditTiter()) return
      if (!this.experiment_id || this.pcsLoading) return
      this.pcsLoading = true
      if (this.pcsTimer) clearTimeout(this.pcsTimer)
      this.pcsTimer = setTimeout(() => {
        saveTiterPcs({
          experiment_id: this.experiment_id,
          pcs: this.titer_pcs
        }).then(res => {
          if (res.data && res.data.items) {
            this.titer_pcs = res.data.items
          }
        }).catch(err => {
          console.error('保存失败:', err)
          ElMessage.error('保存失败')
        }).finally(() => {
          this.pcsLoading = false
        })
      }, 500)
    },

    // --- Plate Methods ---
    getPlates() {
      const expId = this.experiment_id || (this.project ? this.project.experiment_id : null)
      if (!expId) return

      this.platesLoading = true
      Promise.all([
        fetchFacsPlates({ experiment_id: expId }),
        fetchElisaPlates({ experiment_id: expId }),
      ])
        .then(([facsRes, elisaRes]) => {
          this.facsPlates = (facsRes.data.items || []).map((p) => ({
            ...p,
            plate_type: 'facs',
            tempId: p.tempId || null,
            _uid: p.id ? `id_${p.id}` : `tmp_${p.tempId}`,
          }))
          this.elisaPlates = (elisaRes.data.items || []).map((p) => ({
            ...p,
            plate_type: 'elisa',
            tempId: p.tempId || null,
            _uid: p.id ? `id_${p.id}` : `tmp_${p.tempId}`,
            upper_slot_list: p.upper_slot_list || createDefaultUpperSlotList(),
            lower_slot_list: p.lower_slot_list || createDefaultLowerSlotList(),
            slot_groups: p.slot_groups || [],
          }))
          const first = this.sortedAllPlates[0]
          if (first) this.activePlateName = this.getPlateKey(first)
          this.restoreElisaAbsorbancePreviews()
          this.platesLoading = false
          this.scheduleFacsConclusionRefresh(true)
        })
        .catch(() => {
          this.platesLoading = false
        })
    },
    getPlateKey(plate) {
      return plate.id ? `id_${plate.id}` : `tmp_${plate.tempId}`
    },
    getPlateName(plate) {
      if (!plate._uid) {
        plate._uid = plate.tempId ? `tmp_${plate.tempId}` : `db_${plate.id}`
      }
      return plate._uid
    },
    getPlateTabLabel(plate, index) {
      const type = plate.plate_type === 'elisa' ? 'ELISA' : 'FACS'
      const sameType = this.sortedAllPlates.filter((p) => p.plate_type === plate.plate_type)
      const typeIndex = sameType.findIndex((p) => this.getPlateKey(p) === this.getPlateKey(plate)) + 1
      return `${type}板-${typeIndex || index + 1}`
    },
    getElisaExtraAbsorbance(plate) {
      return this.elisaAbsPreviewCache[this.getPlateKey(plate)] || []
    },
    openPlateCopyDialog(plate) {
      if (!this.canEditTiter()) {
        ElMessage.warning('您没有权限编辑此项目')
        return
      }
      this.copySourcePlateKey = this.getPlateKey(plate)
      this.copyTargetPlateKeys = []
      this.plateCopyDialogVisible = true
    },
    cloneJson(value, fallback) {
      if (value === undefined || value === null) return fallback
      return JSON.parse(JSON.stringify(value))
    },
    clonePlateSlotPayload(sourcePlate) {
      if (sourcePlate.plate_type === 'elisa') {
        return {
          upper_slot_list: this.cloneJson(sourcePlate.upper_slot_list, createDefaultUpperSlotList()),
          lower_slot_list: this.cloneJson(sourcePlate.lower_slot_list, createDefaultLowerSlotList()),
          slot_groups: this.cloneJson(sourcePlate.slot_groups, []),
        }
      }
      return {
        upper_mouse_list: this.cloneJson(sourcePlate.upper_mouse_list, []),
        lower_mouse_list: this.cloneJson(sourcePlate.lower_mouse_list, []),
        upper_slot_groups: this.cloneJson(sourcePlate.upper_slot_groups, []),
        lower_slot_groups: this.cloneJson(sourcePlate.lower_slot_groups, []),
      }
    },
    applyPlateSlotPayload(targetPlate, payload) {
      Object.assign(targetPlate, this.cloneJson(payload, {}))
    },
    confirmCopyPlateSlots() {
      const source = this.copySourcePlate
      const targets = this.sortedAllPlates.filter((plate) => this.copyTargetPlateKeys.includes(this.getPlateKey(plate)))
      if (!source) {
        ElMessage.warning('来源板异常')
        return
      }
      if (!targets.length) {
        ElMessage.warning('请选择至少一个目标板')
        return
      }
      if (targets.some((plate) => plate.plate_type !== source.plate_type)) {
        ElMessage.warning('只能复制到同类型板')
        return
      }

      const payload = this.clonePlateSlotPayload(source)
      targets.forEach((target) => {
        this.applyPlateSlotPayload(target, payload)
        this.handleSavePlate(target)
      })
      const targetNames = targets.map((target) => {
        const index = this.sortedAllPlates.findIndex((plate) => this.getPlateKey(plate) === this.getPlateKey(target))
        return this.getPlateTabLabel(target, index)
      })
      ElMessage.success(`已复制到 ${targetNames.join('、')}`)
      this.plateCopyDialogVisible = false
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
      Promise.all(tasks).then((items) => {
        const next = { ...this.elisaAbsPreviewCache }
        for (const item of items) {
          if (!item) continue
          if (item.sheets.length) next[item.key] = item.sheets
          else delete next[item.key]
        }
        this.elisaAbsPreviewCache = next
      })
    },
    handleAddPlate() {
      if (!this.canEditTiter()) {
        ElMessage.warning('您没有权限编辑此项目')
        return
      }
      const tempId = Date.now()
      const newPlate = {
        _uid: `tmp_${tempId}`,
        id: null,
        tempId,
        experiment_id: this.experiment_id || this.project?.experiment_id,
        qr_code: '',
        image_file_id: null,
        excel_file_id: null,
        immune_stage: '',
        x_axis: '',
        y_axis: '',
        cell_target_id: null,
        pc_upper_id: null,
        pc_lower_id: null,
        upper_group: '',
        lower_group: '',
        upper_mouse_list: ['NC', '', '', '', '', '', '', '', '', '', '', 'PC'],
        lower_mouse_list: ['NC', '', '', '', '', '', '', '', '', '', '', 'PC'],
        upper_slot_groups: [],
        lower_slot_groups: [],
        positive_well_list: [],
        instrument_type: '国产'
      }
      this.facsPlates.push({ ...newPlate, plate_type: 'facs' })
      this.activePlateName = this.getPlateKey(newPlate)
      ElMessage.success('已创建新的FACS板')
    },
    handleAddElisaPlate() {
      if (!this.canEditTiter()) {
        ElMessage.warning('您没有权限编辑此项目')
        return
      }
      const tempId = Date.now()
      const newPlate = {
        _uid: `tmp_${tempId}`,
        id: null,
        tempId,
        plate_type: 'elisa',
        experiment_id: this.experiment_id || this.project?.experiment_id,
        qr_code: '',
        excel_file_id: null,
        immune_stage: '',
        protein_target_id: null,
        pc_id: null,
        mouse_group: '',
        antigen_type: '',
        slot_groups: [],
        upper_slot_list: createDefaultUpperSlotList(),
        lower_slot_list: createDefaultLowerSlotList(),
        positive_well_list: [],
        absorbance_1: null,
      }
      this.elisaPlates.push(newPlate)
      this.activePlateName = this.getPlateKey(newPlate)
      ElMessage.success('已创建新的ELISA板')
    },
    handleDeletePlate(plateData) {
      if (!this.canEditTiter()) {
        ElMessage.warning('您没有权限编辑此项目')
        return
      }
      if (!plateData) return
      const deletedKey = this.getPlateKey(plateData)
      const deletedIndex = this.sortedAllPlates.findIndex((p) => this.getPlateKey(p) === deletedKey)
      const isElisa = plateData.plate_type === 'elisa'
      const label = isElisa ? 'ELISA' : 'FACS'

      ElMessageBox.confirm(`确定要删除这个${label}板吗？`, '提示', {
        type: 'warning',
      }).then(() => {
        const removeLocal = () => {
          const list = isElisa ? this.elisaPlates : this.facsPlates
          const index = plateData.id
            ? list.findIndex((p) => p.id === plateData.id)
            : list.findIndex((p) => p.tempId === plateData.tempId)
          if (index !== -1) list.splice(index, 1)
          if (isElisa) delete this.elisaAbsPreviewCache[deletedKey]
          this.cleanupPlateState(deletedKey)
          this.activatePlateAfterDelete(deletedKey, deletedIndex)
          this.scheduleFacsConclusionRefresh(true)
          ElMessage.success(`${label}板已删除`)
        }
        if (plateData.id) {
          const req = isElisa ? deleteElisaPlate(plateData.id) : deleteFacsPlate(plateData.id)
          req.then(removeLocal).catch(() => ElMessage.error('删除失败'))
        } else {
          removeLocal()
        }
      }).catch(() => {})
    },
    cleanupPlateState(plateKey) {
      if (this.plateTimers[plateKey]) {
        clearTimeout(this.plateTimers[plateKey])
        delete this.plateTimers[plateKey]
      }
      delete this.plateSaveSeq[plateKey]
      delete this.savingPlateKeys[plateKey]
    },
    activatePlateAfterDelete(deletedKey, deletedIndex) {
      if (this.activePlateName && this.activePlateName !== deletedKey) return
      const plates = this.sortedAllPlates
      if (!plates.length) {
        this.activePlateName = ''
        return
      }
      const nextIndex = Math.min(Math.max(deletedIndex, 0), plates.length - 1)
      this.activePlateName = this.getPlateKey(plates[nextIndex])
    },
    handleSavePlate(plateData) {
      if (!this.canEditTiter()) return
      if (!this.experiment_id) return

      const isElisa = plateData.plate_type === 'elisa'
      const stableKey = plateData.id ? `id_${plateData.id}` : `tmp_${plateData.tempId}`

      const seq = (this.plateSaveSeq[stableKey] || 0) + 1
      this.plateSaveSeq[stableKey] = seq
      this.savingPlateKeys[stableKey] = true

      if (this.plateTimers[stableKey]) clearTimeout(this.plateTimers[stableKey])

      this.plateTimers[stableKey] = setTimeout(async () => {
        const mySeq = seq
        const myKey = stableKey
        let finalKey = myKey

        try {
          const payload = isElisa
            ? { ...plateData, experiment_id: this.experiment_id, immune_stage: plateData.immune_stage ?? '' }
            : plateData
          const res = isElisa ? await saveElisaPlate(payload) : await saveFacsPlate(payload)

          if (this.plateSaveSeq[myKey] !== mySeq) return

          if (res.data?.id) {
            const newId = res.data.id
            const newKey = `id_${newId}`
            const oldKey = plateData.id ? `id_${plateData.id}` : `tmp_${plateData.tempId}`
            const list = isElisa ? this.elisaPlates : this.facsPlates
            const index = list.findIndex((p) => p._uid === myKey || (!p.id && p.tempId === plateData.tempId))
            if (index === -1) return

            if (isElisa) {
              list[index].id = newId
              list[index]._uid = newKey
              if (res.data.absorbance_1 !== undefined) list[index].absorbance_1 = res.data.absorbance_1
              if (res.data.positive_well_list !== undefined) {
                list[index].positive_well_list = res.data.positive_well_list
              }
            } else {
              list[index].id = newId
              list[index]._uid = newKey
            }

            if (oldKey !== newKey) {
              delete this.plateTimers[oldKey]
              if (this.plateSaveSeq[oldKey] !== undefined && this.plateSaveSeq[newKey] === undefined) {
                this.plateSaveSeq[newKey] = this.plateSaveSeq[oldKey]
                delete this.plateSaveSeq[oldKey]
              }
              if (this.savingPlateKeys[oldKey] !== undefined && this.savingPlateKeys[newKey] === undefined) {
                this.savingPlateKeys[newKey] = this.savingPlateKeys[oldKey]
                delete this.savingPlateKeys[oldKey]
              }
              if (isElisa && this.elisaAbsPreviewCache[oldKey]) {
                const nextCache = { ...this.elisaAbsPreviewCache, [newKey]: this.elisaAbsPreviewCache[oldKey] }
                delete nextCache[oldKey]
                this.elisaAbsPreviewCache = nextCache
              }
              finalKey = newKey
            }

            if (this.activePlateName === myKey) {
              this.activePlateName = newKey
            }
          }
        } catch (err) {
          console.error('保存失败:', err)
          ElMessage.error('保存失败')
        } finally {
          if (this.plateSaveSeq[myKey] === mySeq) {
            this.savingPlateKeys[myKey] = false
          }
          if (finalKey !== myKey && this.plateSaveSeq[finalKey] === mySeq) {
            this.savingPlateKeys[finalKey] = false
          }
          if (this.plateSaveSeq[myKey] === mySeq || this.plateSaveSeq[finalKey] === mySeq) {
            this.scheduleFacsConclusionRefresh(true)
          }
        }
      }, PLATE_SAVE_DEBOUNCE_MS)
    },
    async handleElisaExcelChange({ fileId }, plate) {
      if (!this.canEditTiter() || !plate) return
      const cacheKey = this.getPlateKey(plate)

      if (!fileId) {
        plate.absorbance_1 = null
        plate.positive_well_list = []
        const next = { ...this.elisaAbsPreviewCache }
        delete next[cacheKey]
        this.elisaAbsPreviewCache = next
        this.handleSavePlate(plate)
        return
      }

      const file = this.fileList.find((f) => f.id === fileId)
      if (!file || !this.isExcel(file.file_name)) {
        ElMessage.warning('未找到有效的 Excel 文件')
        return
      }

      try {
        const blob = await this.fetchFileBlob(this.getDownloadUrl(file, true))
        const parsed = parseElisaArrayBuffer(await blob.arrayBuffer(), file.file_name)
        if (parsed.error || !parsed.primary?.matrix) {
          ElMessage.warning('无法解析 ELISA 吸光度表格，请检查文件')
          return
        }
        plate.absorbance_1 = parsed.primary
        if (parsed.extraSheets.length) {
          this.elisaAbsPreviewCache = { ...this.elisaAbsPreviewCache, [cacheKey]: parsed.extraSheets }
        } else {
          const next = { ...this.elisaAbsPreviewCache }
          delete next[cacheKey]
          this.elisaAbsPreviewCache = next
        }
        const lower = normalizeSlotList(plate.lower_slot_list, 'lower')
        plate.positive_well_list = computeAutoPositiveFromPlate(parsed.primary.matrix, lower)
        this.handleSavePlate(plate)
        const extraHint = parsed.extraSheets.length ? `，另有 ${parsed.extraSheets.length} 张吸光度可预览` : ''
        ElMessage.success(
          `已导入吸光度 1（${parsed.primary.wavelength ?? '-'} nm），自动标注 ${plate.positive_well_list.length} 个阳性孔${extraHint}`,
        )
      } catch (error) {
        console.error('解析 ELISA Excel 失败:', error)
        ElMessage.error('读取或解析 Excel 失败')
      }
    },
    canEditTiter() {
      return canEditSerumTiter(this.currentUserInfo, this.project || {})
    },
    canManageFiles() {
      return canManageSerumTiterFiles(this.currentUserInfo, this.project || {})
    }
  }
}
</script>

<style lang="scss" scoped>
.serum-titer-page {
  padding: clamp(8px, 1vw, 16px);
  background-color: #f5f7fa;
  min-height: 100vh;
  position: relative;

  .content-wrapper {
    width: 100%;
    max-width: 100%;
    margin: 0 auto;
    min-width: 0;
  }
}

/* Page-local size semantics */
.serum-titer-page :deep(.el-table--small),
.serum-titer-page :deep(.el-input--small),
.serum-titer-page :deep(.el-select--small) {
  font-size: 12px;
}

.serum-titer-page :deep(.el-table--small .el-table__cell) {
  padding: 4px 0;
}

.serum-titer-page :deep(.el-descriptions:not(.el-descriptions--small):not(.el-descriptions--large) .el-descriptions__cell) {
  padding: 10px;
  font-size: 13px;
  line-height: 1.5;
}

.copy-target-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}

.copy-target-select {
  flex: 1;
  min-width: 0;
}

.copy-target-actions {
  display: flex;
  flex: 0 0 auto;
  gap: 8px;

  .el-button + .el-button {
    margin-left: 0;
  }
}

@media (max-width: 640px) {
  .copy-target-row {
    align-items: stretch;
    flex-direction: column;
  }

  .copy-target-actions {
    justify-content: flex-end;
  }
}

/* Header */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  background: #fff;
  padding: 12px 16px;
  border-radius: 12px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);

  .header-left {
    display: flex;
    align-items: center;
    
    .header-icon {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 36px;
      height: 36px;
      margin-right: 12px;
      background: #ecf5ff;
      border-radius: 8px;

      .el-icon {
        margin: 0;
        color: #409EFF;
        font-size: 20px;
      }
    }

    .page-title {
      margin: 0;
      font-size: 18px;
      font-weight: 600;
      color: #303133;
      
      .sub-title {
        font-size: 13px;
        color: #909399;
        font-weight: normal;
        margin-left: 8px;
      }
    }
  }
}

/* Cards & Layout */
.top-section {
  margin-bottom: 16px;
  /* Flex layout is handled by Element Plus row styles. */
}

.upload-col, .info-col {
  /* Stretch columns so the paired cards keep the same height. */
  display: flex;
  flex-direction: column; 
}

.upload-card, .info-card {
  height: 100%;
  border: none;
  border-radius: 12px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);

  /* Flex column for full height cards */
  display: flex;
  flex-direction: column;

  &:hover {
    box-shadow: 0 4px 16px 0 rgba(0,0,0,0.08);
  }

  /* Body needs to flex to fill */
  :deep(.el-card__body) {
     flex: 1;
     display: flex;
     flex-direction: column;
     padding: 20px;
  }
}

.file-list-card {
  height: 100%;
  border: none;
  border-radius: 12px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);

  /* Flex column for full height cards */
  display: flex;
  flex-direction: column;

  &:hover {
    box-shadow: 0 4px 16px 0 rgba(0,0,0,0.08);
  }

  /* Body needs to flex to fill */
  :deep(.el-card__body) {
     flex: 1;
     display: flex;
     flex-direction: column;
     padding: 14px;
  }
}

.card-header {
  display: flex;
  align-items: center;
  font-weight: 700;
  font-size: 15px;
  color: #303133;
  width: 100%;
  
  &.space-between {
    justify-content: space-between;
  }

  .el-icon {
    margin-right: 8px;
    color: #409EFF;
  }
}

/* Styles for unified data table card */
.table-card {
  border-radius: 12px;
  border: none;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
  
  :deep(.el-card__body) {
     padding: 20px;
     min-height: 150px;
  }
}

.table-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  .el-icon { margin-right: 6px; color: #409EFF; }
}

.add-btn {
  font-size: 14px;
  padding: 0;
}

/* Flex col wrapper */
.flex-col {
  display: flex;
  flex-direction: column;
}

.full-height {
  flex: 1;
}

.danger-text { color: #F56C6C; }

/* Custom Table Refined Styles */
.refined-table {
  border-radius: 4px;
  overflow: hidden;
  border-color: #f0f0f0;

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

  :deep(.el-input--small),
  :deep(.el-select--small) {
    width: calc(100% - 8px);
    margin: 0 4px;
  }

  :deep(.el-input__inner) {
    background: transparent;
    border: none;
    box-shadow: none;
  }

  :deep(.el-input__wrapper),
  :deep(.el-select__wrapper) {
    box-sizing: border-box;
    height: 24px;
    min-height: 24px;
    background: transparent;
    box-shadow: 0 0 0 1px transparent inset;
    transition: all 0.2s;
  }

  :deep(.el-input--small .el-input__wrapper),
  :deep(.el-select--small .el-select__wrapper) {
    padding-right: 4px;
    padding-left: 4px;
  }

  :deep(.el-input__wrapper:hover),
  :deep(.el-select__wrapper:hover) {
    background: rgba(64, 158, 255, 0.04);
    box-shadow: 0 0 0 1px #dcdfe6 inset;
  }

  :deep(.el-input__wrapper.is-focus),
  :deep(.el-select__wrapper.is-focused) {
    background: #fff;
    box-shadow:
      0 0 0 1px #409eff inset,
      0 0 0 2px rgba(64, 158, 255, 0.1);
  }

  :deep(.el-select) {
    width: 100%;
    .el-input__inner {
      cursor: pointer;
    }
    .el-input__suffix {
      display: none; /* Hide arrow for ultra-minimal look, or keep if preferred */
    }
    &:hover .el-input__suffix {
      display: block;
    }
  }
}

/* Upload Styling */
.titer-upload {
  height: 100%;
  display: flex;
  flex-direction: column;
  
  :deep(.el-upload) {
    width: 100%;
    height: 100%;
    flex: 1;
    .el-upload-dragger {
      width: 100%;
      height: 200px;
      min-height: 200px;
      padding: 0;
      box-sizing: border-box;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      border: 2px dashed #e0e6ed;
      border-radius: 10px;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      background-color: #fbfcfd;

      &:hover {
        background-color: #f0f7ff;
        border-color: #409EFF;
        .upload-icon {
          color: #409EFF;
          transform: translateY(-5px);
        }
      }

      .dragger-wrapper {
        padding: 20px;
        text-align: center;
      }

      .upload-icon {
        margin-bottom: 16px;
        font-size: 54px;
        color: #a0cfff;
        transition: all 0.3s;
      }
      
      .el-upload__text {
        font-size: 15px;
        color: #606266;
        line-height: 1.6;
        em {
          color: #409EFF;
          font-style: normal;
          font-weight: 500;
        }
      }

      .el-upload__tip {
        margin-top: 8px;
        font-size: 12px;
        color: #909399;
      }
    }
  }
}

/* Project Info */
.project-info-content {
  :deep(.el-descriptions__label.is-bordered-label) {
    width: 120px;
    color: #606266;
    font-weight: bold;
    background: #f9fafc;
  }

  :deep(.el-descriptions__content.is-bordered-content) {
    color: #303133;
  }
}

.info-empty {
  padding: 10px 0;
}

/* File Preview Grid */
.file-preview-section {
  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;

    .section-title {
      margin: 0;
      font-size: 18px;
      font-weight: 700;
      color: #333;
      display: flex;
      align-items: center;
      gap: 12px;

      .title-text {
        display: flex;
        align-items: baseline;
        gap: 8px;
        .el-icon { color: #409EFF; }
        .eng { font-size: 13px; color: #999; font-weight: 400; }
      }

      .custom-file-badge { 
        background: #f0f2f5;
        color: #666;
        font-size: 13px;
        font-weight: bold;
        padding: 0 10px;
        border-radius: 10px;
        height: 22px;
        line-height: 22px;
        border: 1px solid #e4e7ed;
      }
    }
  }

  .file-list-card {
    padding: 10px;
  }
}

.file-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  min-height: 150px;
}

.file-card-wrapper {
  width: calc(16.66% - 17px);
  min-width: 160px;
  max-width: 220px;
}

.file-card {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(.25,.8,.25,1);

  &:hover {
    transform: translateY(-5px);
    box-shadow: 0 8px 16px rgba(0,0,0,0.1);
    border-color: #409EFF;

    .file-overlay {
      opacity: 1;
    }
  }

  .file-preview-area {
    height: 140px;
    position: relative;
    background: #f5f7fa;
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
        font-size: 48px;
        color: #909399;
        margin-bottom: 8px;
      }
      
      .ext-tag {
        font-size: 12px;
        font-weight: 700;
        color: #fff;
        background: #909399;
        padding: 2px 6px;
        border-radius: 4px;
        text-transform: uppercase;
      }
    }

    .file-overlay {
      position: absolute;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0,0,0,0.4);
      display: flex;
      align-items: center;
      justify-content: center;
      opacity: 0;
      transition: opacity 0.3s;

      .view-btn {
        color: #fff;
        font-size: 13px;
        background: rgba(255,255,255,0.2);
        padding: 6px 12px;
        border-radius: 20px;
        border: 1px solid rgba(255,255,255,0.5);
      }
    }
  }

  .file-info-area {
    padding: 12px;
    border-top: 1px solid #f0f2f5;

    .file-name-text {
      font-size: 13px;
      color: #303133;
      font-weight: 500;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      margin-bottom: 4px;
    }

    .file-meta-text {
      font-size: 12px;
      color: #909399;
    }
  }
}

/* Icon Colors */
.excel-color { color: #217346 !important; }
.word-color { color: #2b579a !important; }
.ppt-color { color: #d24726 !important; }
.pdf-color { color: #b30b00 !important; }
.zip-color { color: #e6a23c !important; }

/* Empty State */
.empty-state {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 0;

  .empty-content {
    text-align: center;
    color: #c0c4cc;

    .el-icon { font-size: 64px; margin-bottom: 16px; opacity: 0.5; }
    p { margin: 0; font-size: 16px; color: #909399; font-weight: 500; }
    .sub-text { font-size: 13px; margin-top: 8px; display: block; }
  }
}

/* Dialog Styling */
:global(.el-dialog.serum-detail-dialog) {
  border-radius: 12px;
  overflow: hidden;
  margin-left: auto !important;
  margin-right: auto !important;
  display: flex;
  flex-direction: column;
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
  flex: 1.5;
  background: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: center;
  border-right: 1px solid #f0f2f5;
  overflow: hidden;

  .preview-container, .full-image { width: 100%; height: 100%; }

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
    .huge-icon { font-size: 120px; color: #dcdfe6; }
    .huge-ext { font-size: 24px; font-weight: bold; color: #c0c4cc; margin-top: 10px; }
  }
}

.dialog-info-side {
  flex: 1;
  padding: 24px;
  display: flex;
  flex-direction: column;
  overflow-y: auto;

  .side-title {
    margin: 0 0 16px;
    font-size: 16px;
    color: #303133;
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    
    small { font-weight: normal; font-size: 12px; color: #909399; }
  }

  .meta-section {
    margin-bottom: 30px;
    
    .meta-list {
      background: #f9fafc;
      padding: 16px;
      border-radius: 8px;
    }
    
    .meta-item {
      display: flex;
      justify-content: space-between;
      margin-bottom: 12px;
      font-size: 13px;
      
      &:last-child { margin-bottom: 0; }
      
      .m-label { color: #909399; }
      .m-value { color: #303133; font-weight: 500; }
    }
  }

  .action-section {
    margin-top: auto; /* Push to bottom if space allows */
    
    .button-group {
      margin-top: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;

      .el-button { 
        margin: 0; 
        width: 100%;
        display: block; /* Ensure it takes full width */
      }
      .replace-uploader { 
        width: 100%;
        :deep(.el-upload) {
            width: 100%;
            display: block;
        }
      }
    }
  }
}

/* Modern Excel Style */
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

  tr:nth-child(even) { background-color: #fafbfc; }
  tr:hover td { background-color: #ecf5ff; }
}

.excel-error {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #909399;
  .el-icon { font-size: 40px; margin-bottom: 12px; }
}

/* FACS Plate Section */
.facs-plate-section {
  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;

    .section-title {
      margin: 0;
      font-size: 18px;
      font-weight: 600;
      color: #333;
      display: flex;
      align-items: center;
      gap: 12px;

      .title-text {
        display: flex;
        align-items: baseline;
        gap: 8px;
        .el-icon { color: #409EFF; }
        .eng { font-size: 13px; color: #999; font-weight: normal; }
      }
    }

    .header-buttons {
      display: flex;
      gap: 10px;

      .plate-create-btn {
        height: 32px;
        padding: 0 14px;
        font-size: 14px;
      }
    }
  }

  .plates-tabs {
    :deep(.el-tabs__header) {
      margin: 0 0 8px 0;
    }

    :deep(.el-tabs__nav-wrap) {
      padding: 0 clamp(8px, 1.2vw, 20px);
    }

    :deep(.el-tabs__item) {
      font-size: 14px;
      height: 40px;
      line-height: 40px;
      padding: 0 20px;

      &:hover {
        color: #409EFF;
      }

      &.is-active {
        color: #409EFF;
        font-weight: 600;
      }
    }

    :deep(.el-tabs__content) {
      padding: 0;
    }
  }

  .empty-plates {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 80px 0;

    .empty-content {
      text-align: center;
      color: #c0c4cc;

      .el-icon { font-size: 64px; margin-bottom: 16px; opacity: 0.5; }
      p { margin: 0; font-size: 16px; color: #909399; font-weight: 500; }
      .sub-text { font-size: 13px; margin-top: 8px; display: block; }
    }
  }
}

.titer-conclusion-section {
  .section-header {
    display: flex;
    align-items: center;
    margin-bottom: 20px;

    .section-title {
      margin: 0;
      font-size: 18px;
      font-weight: 700;
      color: #333;
      display: flex;
      align-items: center;
      gap: 12px;

      .title-text {
        display: flex;
        align-items: baseline;
        gap: 8px;
        .el-icon { color: #409EFF; }
        .eng { font-size: 13px; color: #999; font-weight: 400; }
      }
    }
  }

  .conclusion-card {
    border: none;
    border-radius: 12px;
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);

    :deep(.el-card__body) {
      padding: 16px 18px;
    }
  }
}
</style>
