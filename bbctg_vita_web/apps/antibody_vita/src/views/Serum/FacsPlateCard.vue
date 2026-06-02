<template>
  <div class="plate-card">
    <div class="plate-content">
      <div class="top-row">
        <div class="left-top-panel">
          <div class="left-form-grid">
          <div class="form-section form-section--files">
            <div class="section-header">
              <div class="header-left">
                <el-icon><FolderOpened /></el-icon>
                <span>文件选择</span>
              </div>
            </div>
            <el-form class="plate-form">
              <el-form-item label="96孔板图片">
                <el-select
                  v-model="plateData.image_file_id"
                  placeholder="请从上方文件列表中选择"
                  filterable
                  clearable
                  :disabled="!isEditable"
                  style="width: 100%"
                  @change="autoSave"
                  @clear="onClearFile('image')"
                >
                  <el-option
                    v-for="file in imageFileOptions"
                    :key="file.id"
                    :label="file.file_name"
                    :value="file.id"
                  >
                    <span style="float: left">{{ file.file_name }}</span>
                    <span style="float: right; color: #8492a6; font-size: 13px">{{ file.created_time }}</span>
                  </el-option>
                </el-select>
              </el-form-item>
              <el-form-item label="Excel结果">
                <el-select
                  v-model="plateData.excel_file_id"
                  placeholder="请从上方文件列表中选择"
                  filterable
                  clearable
                  :disabled="!isEditable"
                  style="width: 100%"
                  @change="onExcelFileChange"
                  @clear="onClearExcelFile"
                >
                  <el-option
                    v-for="file in excelFileOptions"
                    :key="file.id"
                    :label="file.file_name"
                    :value="file.id"
                  >
                    <span style="float: left">{{ file.file_name }}</span>
                    <span style="float: right; color: #8492a6; font-size: 13px">{{ file.created_time }}</span>
                  </el-option>
                </el-select>
              </el-form-item>
            </el-form>
          </div>

          <div class="form-section basic-info-section">
            <div class="section-header">
              <div class="header-left">
                <el-icon><EditPen /></el-icon>
                <span>基本信息</span>
              </div>
              <div v-if="isSaving" class="header-right">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span>保存中...</span>
              </div>
            </div>
            <el-form class="plate-form">
              <el-form-item label="二维码编号">
                <el-input v-model="plateData.qr_code" placeholder="扫描或输入二维码" :disabled="!isEditable" @change="autoSave" />
              </el-form-item>
              <el-form-item label="免疫阶段">
                <el-select v-model="plateData.immune_stage" placeholder="请选择免疫阶段" clearable :disabled="!isEditable" style="width: 100%" @change="autoSave" @clear="onClearFile('immune_stage')">
                  <el-option
                    v-for="stage in immuneStageOptions"
                    :key="stage"
                    :label="stage"
                    :value="stage"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="细胞标靶">
                <el-select v-model="plateData.cell_target_id" placeholder="请选择细胞标靶" clearable :disabled="!isEditable" style="width: 100%" @change="autoSave" @clear="onClearFile('cell_target_id')">
                  <el-option
                    v-for="target in targetOptions"
                    :key="target.id"
                    :label="target.name"
                    :value="target.id"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="纵坐标参数">
                <el-select
                  v-model="plateData.y_axis"
                  placeholder="如：SSC-H"
                  clearable
                  :disabled="!isEditable"
                  style="width: 100%"
                  @change="autoSave"
                >
                  <el-option
                    v-for="opt in yAxisOptions"
                    :key="opt"
                    :label="opt"
                    :value="opt"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="横坐标参数">
                <el-select
                  v-model="plateData.x_axis"
                  placeholder="如：RL1-H"
                  clearable
                  :disabled="!isEditable"
                  style="width: 100%"
                  @change="autoSave"
                >
                  <el-option
                    v-for="opt in xAxisOptions"
                    :key="opt"
                    :label="opt"
                    :value="opt"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="上半PC">
                <el-select v-model="plateData.pc_upper_id" placeholder="请选择上PC" clearable :disabled="!isEditable" style="width: 100%" @change="autoSave" @clear="onClearFile('pc_upper_id')">
                  <el-option
                    v-for="pc in pcOptions"
                    :key="pc.id"
                    :label="pc.pc_name"
                    :value="pc.id"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="下半PC">
                <el-select v-model="plateData.pc_lower_id" placeholder="请选择下PC" clearable :disabled="!isEditable" style="width: 100%" @change="autoSave" @clear="onClearFile('pc_lower_id')">
                  <el-option
                    v-for="pc in pcOptions"
                    :key="pc.id"
                    :label="pc.pc_name"
                    :value="pc.id"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="上半组别">
                <el-select v-model="plateData.upper_group" placeholder="请选择上半组别" clearable :disabled="!isEditable" style="width: 100%" @change="autoSave" @clear="onClearFile('upper_group')">
                  <el-option
                    v-for="group in groupOptions"
                    :key="group"
                    :label="group"
                    :value="group"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="下半组别">
                <el-select v-model="plateData.lower_group" placeholder="请选择下半组别" clearable :disabled="!isEditable" style="width: 100%" @change="autoSave" @clear="onClearFile('lower_group')">
                  <el-option
                    v-for="group in groupOptions"
                    :key="group"
                    :label="group"
                    :value="group"
                  />
                </el-select>
              </el-form-item>
            </el-form>
          </div>
          </div>
        </div>

        <div class="right-panel">
          <div class="image-section">
            <div class="section-title">
              <div class="header-left">
                <el-icon><Picture /></el-icon>
                <span>96孔板图片预览</span>
              </div>
              <div class="header-right">
                <el-button type="text" class="delete-btn" :disabled="!isEditable" @click="handleDelete">
                  <el-icon><Delete /></el-icon>
                  <span>删除此板</span>
                </el-button>
                <el-button type="text" class="mask-toggle-btn" :disabled="!isEditable" @click="handleMaskToggle" @contextmenu.prevent.stop="handleMaskContextMenu">
                  <el-icon><Setting /></el-icon>
                  <span>仪器类型: {{ plateData.instrument_type || '国产' }}</span>
                </el-button>
              </div>
            </div>

            <div class="image-display">
              <div
                class="image-cluster"
                :class="{ 'has-legend': selectedImageUrl && wellGridRect }"
              >
              <div class="slot-editor upper-slot-editor plate-column">
                <div class="slot-groups-row" :style="slotTrackStyle">
                  <div
                    v-for="(group, index) in upperSlotGroups"
                    :key="'upper-group-' + index"
                    class="slot-group-block"
                    :style="getGroupStyle(group)"
                    @mouseenter="updateGroupTooltipOverflow('upper', index)"
                  >
                    <el-tooltip
                      :content="group.label"
                      :disabled="!groupTooltipOverflow.upper[index]"
                      placement="top"
                      effect="dark"
                    >
                      <el-input
                        :ref="groupInputRef('upper', index)"
                        :model-value="group.label"
                        size="small"
                        placeholder="分组标题"
                        :disabled="!isEditable"
                        @input="setSlotGroupLabel('upper', index, $event)"
                        @change="autoSave"
                      />
                    </el-tooltip>
                    <span
                      v-if="isEditable"
                      class="slot-group-remove"
                      @click.stop="removeSlotGroup('upper', index)"
                    >×</span>
                  </div>
                  <div
                    v-if="selectionRange && dragState.section === 'upper'"
                    class="slot-group-block drag-preview"
                    :style="getGroupStyle(selectionRange)"
                  >
                    {{ getSelectionLabel('upper') }}
                  </div>
                </div>

                <div class="wells-row top-wells" :style="slotTrackStyle">
                  <div
                    v-for="i in slotCount"
                    :key="'top-' + i"
                    class="well-input"
                    :class="getSlotClass('upper', i - 1)"
                    @mouseenter="handleSlotMouseEnter('upper', i - 1)"
                    @mouseup="handleSlotMouseUp"
                  >
                    <el-input
                      :ref="'top-' + i"
                      :model-value="getUpperWell(i - 1)"
                      size="small"
                      :disabled="!isEditable"
                      @input="setSlotValue('upper', i - 1, $event)"
                      @mousedown="handleSlotMouseDown($event, 'upper', i - 1)"
                      @keydown.enter.prevent="handleWellEnter('top', i)"
                      @paste="handleWellPaste($event, 'top', i)"
                    />
                  </div>
                </div>
              </div>

              <div class="image-preview-area plate-column" ref="imageContainer">
                <div v-if="!selectedImageUrl" class="empty-image">
                  <el-icon><Picture /></el-icon>
                  <p>请先选择图片</p>
                </div>
                <img
                  v-else
                  :src="selectedImageUrl"
                  class="preview-image"
                  ref="previewImage"
                  @load="handleImageLoad"
                >
                <div
                  v-if="selectedImageUrl"
                  ref="wellGridOverlay"
                  class="well-grid-overlay"
                  :style="gridStyle"
                  @mousemove="handleWellGridMouseMove"
                >
                  <div
                    v-for="(row, rowIndex) in 8"
                    :key="'row-' + rowIndex"
                    class="grid-row"
                  >
                    <div
                      v-for="(col, colIndex) in 12"
                      :key="'cell-' + rowIndex + '-' + colIndex"
                      class="grid-cell"
                      :data-row="rowIndex"
                      :data-col="colIndex"
                      :class="getWellCellClass(rowIndex, colIndex)"
                      @mousedown.prevent="handleWellMouseDown($event, rowIndex, colIndex)"
                    >
                      <span class="cell-label">{{ String.fromCharCode(65 + rowIndex) }}{{ colIndex + 1 }}</span>
                      <el-icon v-if="wellMatrix[rowIndex][colIndex]" class="check-icon"><Check /></el-icon>
                    </div>
                  </div>
                </div>

                <div v-if="showMaskAdjuster" class="mask-adjuster">
                  <div class="adjuster-header">
                    <el-icon><Setting /></el-icon>
                    <span>遮罩调节器</span>
                  </div>
                  <div class="adjuster-content">
                    <div class="adjuster-row">
                        <span>上:</span>
                        <el-input-number v-model="maskOffset.top" :min="0" :max="50" :step="0.1" size="small" controls-position="right" :disabled="!isEditable" @change="updateGridBBox(false)" />
                        <span>下:</span>
                        <el-input-number v-model="maskOffset.bottom" :min="0" :max="50" :step="0.1" size="small" controls-position="right" :disabled="!isEditable" @change="updateGridBBox(false)" />
                      </div>
                      <div class="adjuster-row">
                        <span>左:</span>
                        <el-input-number v-model="maskOffset.left" :min="0" :max="50" :step="0.1" size="small" controls-position="right" :disabled="!isEditable" @change="updateGridBBox(false)" />
                        <span>右:</span>
                        <el-input-number v-model="maskOffset.right" :min="0" :max="50" :step="0.1" size="small" controls-position="right" :disabled="!isEditable" @change="updateGridBBox(false)" />
                      </div>
                    <div class="adjuster-presets">
                      <span class="preset-label">快速选项:</span>
                      <el-button size="small" :disabled="!isEditable" @click="setInstrument('国产')">国产</el-button>
                      <el-button size="small" :disabled="!isEditable" @click="setInstrument('赛多利斯')">赛多利斯</el-button>
                    </div>
                  </div>
                </div>
              </div>

              <div
                v-if="selectedImageUrl && wellGridRect"
                class="dilution-legend legend-column"
                aria-label="行稀释度"
              >
                <div class="dilution-legend__title" :style="dilutionLegend.title">稀释度</div>
                <div class="dilution-legend__rows" :style="dilutionLegend.rows">
                  <span class="dilution-legend__divider" aria-hidden="true" />
                  <div
                    v-for="(row, rowIndex) in plateRows"
                    :key="row"
                    class="dilution-legend__row"
                    :class="rowIndex < 4 ? 'is-upper' : 'is-lower'"
                    :style="dilutionLegend.row(rowIndex)"
                  >
                    <span>{{ row }}</span>
                    <span>{{ formatRowDilution(rowIndex) }}</span>
                  </div>
                </div>
              </div>

              <div class="slot-editor lower-slot-editor plate-column">
                <div class="wells-row bottom-wells" :style="slotTrackStyle">
                  <div
                    v-for="i in slotCount"
                    :key="'bottom-' + i"
                    class="well-input"
                    :class="getSlotClass('lower', i - 1)"
                    @mouseenter="handleSlotMouseEnter('lower', i - 1)"
                    @mouseup="handleSlotMouseUp"
                  >
                    <el-input
                      :ref="'bottom-' + i"
                      :model-value="getLowerWell(i - 1)"
                      size="small"
                      :disabled="!isEditable"
                      @input="setSlotValue('lower', i - 1, $event)"
                      @mousedown="handleSlotMouseDown($event, 'lower', i - 1)"
                      @keydown.enter.prevent="handleWellEnter('bottom', i)"
                      @paste="handleWellPaste($event, 'bottom', i)"
                    />
                  </div>
                </div>

                <div class="slot-groups-row" :style="slotTrackStyle">
                  <div
                    v-for="(group, index) in lowerSlotGroups"
                    :key="'lower-group-' + index"
                    class="slot-group-block"
                    :style="getGroupStyle(group)"
                    @mouseenter="updateGroupTooltipOverflow('lower', index)"
                  >
                    <el-tooltip
                      :content="group.label"
                      :disabled="!groupTooltipOverflow.lower[index]"
                      placement="top"
                      effect="dark"
                    >
                      <el-input
                        :ref="groupInputRef('lower', index)"
                        :model-value="group.label"
                        size="small"
                        placeholder="分组标题"
                        :disabled="!isEditable"
                        @input="setSlotGroupLabel('lower', index, $event)"
                        @change="autoSave"
                      />
                    </el-tooltip>
                    <span
                      v-if="isEditable"
                      class="slot-group-remove"
                      @click.stop="removeSlotGroup('lower', index)"
                    >×</span>
                  </div>
                  <div
                    v-if="selectionRange && dragState.section === 'lower'"
                    class="slot-group-block drag-preview"
                    :style="getGroupStyle(selectionRange)"
                  >
                    {{ getSelectionLabel('lower') }}
                  </div>
                </div>
              </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import {
  Check,
  Delete,
  EditPen,
  FolderOpened,
  Loading,
  Picture,
  Setting,
} from '@element-plus/icons-vue'
import {
  ElButton,
  ElForm,
  ElFormItem,
  ElIcon,
  ElInput,
  ElInputNumber,
  ElOption,
  ElSelect,
  ElTooltip,
} from 'element-plus'

const GATE_TEMPLATES = {
  domestic: { top: 7.3, left: 3.9, bottom: 4.4, right: 2.1 },
  cytomics: { top: 9.5, left: 6.6, bottom: 5.2, right: 3.6 }
}
const SLOT_COUNT = 12
const SLOT_WIDTH = 60
const SLOT_GAP = 8
const DEFAULT_SLOT_TRACK_STYLE = {
  width: `${SLOT_COUNT * SLOT_WIDTH + (SLOT_COUNT - 1) * SLOT_GAP}px`,
  margin: '0 auto',
  '--slot-well-width': `${SLOT_WIDTH}px`
}
const DEFAULT_SLOT_VALUES = ['NC', '', '', '', '', '', '', '', '', '', '', 'PC']
const X_AXIS_OPTIONS = ['RL1-H', 'BL1-H', 'APC-H']
const Y_AXIS_OPTIONS = ['SSC-H', 'BL1-H']
const PLATE_ROWS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
const DILUTION_EXPONENTS = [2, 3, 4, 5, 2, 3, 4, 5]
const DILUTION_SUPERSCRIPT = { 2: '²', 3: '³', 4: '⁴', 5: '⁵' }
const DILUTION_LEGEND_PADDING_X = 12
/** 将剪贴板文本拆成多个鼠号：多行、Tab/逗号/分号分隔的单行 */
function splitPasteTokens(text) {
  const normalized = (text || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n').trim()
  if (!normalized) return []

  const lines = normalized.split('\n').map(s => s.trim()).filter(Boolean)
  if (lines.length > 1) return lines

  const line = lines[0]
  if (/[\t,;]/.test(line)) {
    return line.split(/[\t,;]+/).map(s => s.trim()).filter(Boolean)
  }
  return [line]
}

export default {
  name: 'FacsPlateCard',
  components: {
    Check,
    Delete,
    EditPen,
    ElButton,
    ElForm,
    ElFormItem,
    ElIcon,
    ElInput,
    ElInputNumber,
    ElOption,
    ElSelect,
    ElTooltip,
    FolderOpened,
    Loading,
    Picture,
    Setting,
  },
  props: {
    plateData: {
      type: Object,
      default: () => ({
        id: null,
        experiment_id: '',
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
        upper_mouse_list: [],
        lower_mouse_list: [],
        upper_slot_groups: [],
        lower_slot_groups: [],
        positive_well_list: [],
        instrument_type: '国产',
        tempId: null
      })
    },
    targetOptions: {
      type: Array,
      default: () => []
    },
    pcOptions: {
      type: Array,
      default: () => []
    },
    fileList: {
      type: Array,
      default: () => []
    },
    immuneStageOptions: {
      type: Array,
      default: () => []
    },
    groupOptions: {
      type: Array,
      default: () => []
    },
    isActive: {
      type: Boolean,
      default: false
    },
    isSaving: {
      type: Boolean,
      default: false
    },
    isEditable: {
      type: Boolean,
      default: true
    }
  },
  data() {
    return {
      xAxisOptions: X_AXIS_OPTIONS,
      yAxisOptions: Y_AXIS_OPTIONS,
      imageNaturalSize: { width: 0, height: 0 },
      gridBBox: { x: 0, y: 0, width: 0, height: 0 },
      containRect: { dx: 0, dy: 0, scale: 1, dw: 0, dh: 0 },
      wellMatrix: Array(8).fill(null).map(() => Array(12).fill(false)),
      showMaskAdjuster: false,
      maskOffset: {
        top: 7.5,
        right: 2,
        bottom: 4,
        left: 4.1
      },
      dragState: {
        active: false,
        section: null,
        start: null,
        end: null
      },
      wellDragState: {
        active: false,
        startRow: null,
        startCol: null,
        endRow: null,
        endCol: null,
        applyPositive: true
      },
      groupTooltipOverflow: {
        upper: {},
        lower: {}
      },
      saveTimer: null
    }
  },
  computed: {
    slotCount() {
      return SLOT_COUNT
    },
    // 图片孔位区域在预览区内的像素矩形（overlay / 鼠号 / 稀释度行共用）
    wellGridRect() {
      const { dx, dy, scale, dw, dh } = this.containRect
      const { x, y, width, height } = this.gridBBox
      if (!width || !height || !scale || !dw || !dh) return null

      const gridWidth = width * scale
      const slotWidth = (gridWidth - (SLOT_COUNT - 1) * SLOT_GAP) / SLOT_COUNT
      return {
        left: dx + x * scale,
        top: dy + y * scale,
        width: gridWidth,
        height: height * scale,
        imageTop: dy,
        slotWidth: Number.isFinite(slotWidth) && slotWidth > 0 ? slotWidth : SLOT_WIDTH
      }
    },
    slotTrackStyle() {
      const rect = this.wellGridRect
      if (!this.selectedImageUrl || !rect) {
        return DEFAULT_SLOT_TRACK_STYLE
      }
      return {
        width: `${rect.width}px`,
        marginLeft: `${rect.left}px`,
        '--slot-well-width': `${rect.slotWidth}px`
      }
    },
    upperSlotGroups() {
      return Array.isArray(this.plateData.upper_slot_groups) ? this.plateData.upper_slot_groups : []
    },
    lowerSlotGroups() {
      return Array.isArray(this.plateData.lower_slot_groups) ? this.plateData.lower_slot_groups : []
    },
    plateRows() {
      return PLATE_ROWS
    },
    dilutionLegend() {
      const rect = this.wellGridRect
      if (!rect) return null
      const rowHeightPct = 100 / PLATE_ROWS.length

      return {
        title: { top: `${rect.imageTop}px` },
        rows: {
          position: 'absolute',
          left: `${DILUTION_LEGEND_PADDING_X}px`,
          right: `${DILUTION_LEGEND_PADDING_X}px`,
          top: `${rect.top}px`,
          height: `${rect.height}px`,
        },
        row: (rowIndex) => ({
          top: `${rowIndex * rowHeightPct}%`,
          height: `${rowHeightPct}%`,
        }),
      }
    },
    selectionRange() {
      if (!this.dragState.active || this.dragState.start === null || this.dragState.end === null) return null
      return {
        start: Math.min(this.dragState.start, this.dragState.end),
        end: Math.max(this.dragState.start, this.dragState.end)
      }
    },
    wellSelectionRect() {
      const d = this.wellDragState
      if (!d.active || d.startRow === null || d.endRow === null) return null
      return {
        r0: Math.min(d.startRow, d.endRow),
        r1: Math.max(d.startRow, d.endRow),
        c0: Math.min(d.startCol, d.endCol),
        c1: Math.max(d.startCol, d.endCol)
      }
    },
    imageFileOptions() {
      return this.fileList.filter(file => this.isImage(file.file_name))
    },
    excelFileOptions() {
      return this.fileList.filter(file => this.isExcel(file.file_name))
    },
    selectedImageFile() {
      if (!this.plateData.image_file_id) return null
      return this.fileList.find(f => f.id === this.plateData.image_file_id)
    },
    selectedImageUrl() {
      if (!this.selectedImageFile) return ''
      return this.getImageUrl(this.selectedImageFile)
    },
    gridStyle() {
      const rect = this.wellGridRect
      if (!rect) {
        return { display: 'none' }
      }

      return {
        position: 'absolute',
        left: `${rect.left}px`,
        top: `${rect.top}px`,
        width: `${rect.width}px`,
        height: `${rect.height}px`,
      }
    },
  },
  watch: {
    'plateData.positive_well_list': {
      handler(newVal) {
        if (Array.isArray(newVal)) {
          const wellLabels = newVal.filter(w => w && typeof w === 'string')
          this.initWellMatrix(wellLabels)
        } else {
          this.wellMatrix = Array(8).fill(null).map(() => Array(12).fill(false))
        }
      },
      immediate: true
    },
    'plateData.instrument_type': {
      handler(newVal) {
        const type = newVal === '赛多利斯' ? 'cytomics' : 'domestic'
        this.applyPreset(type, false)
      },
      immediate: true
    },
    isActive(val) {
      if (val) this.forceRecalc()
    },
    selectedImageFile: {
      handler(file) {
        if (file && !file.preview_object_url) {
          this.$emit('load-image-preview', file)
        }
      },
      immediate: true
    },
    'plateData.image_file_id'(fileId, prevId) {
      if (fileId === prevId) return
      // 首次挂载已有图片时不要清空，否则缓存图可能不触发 @load
      if (prevId !== undefined) {
        this.resetPlateLayoutMetrics()
      }
    }
  },
  methods: {
    formatRowDilution(rowIndex) {
      const exp = DILUTION_EXPONENTS[rowIndex] ?? 2
      return `10${DILUTION_SUPERSCRIPT[exp] ?? exp}`
    },
    isImage(filename) {
      const ext = filename.split('.').pop().toLowerCase()
      return ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'].includes(ext)
    },
    isExcel(filename) {
      const ext = filename.split('.').pop().toLowerCase()
      return ['xls', 'xlsx', 'csv'].includes(ext)
    },
    getImageUrl(file) {
      return file.preview_object_url || file.thumb_object_url || ''
    },
    autoSave() {
      if (!this.isEditable) return
      if (this.saveTimer) clearTimeout(this.saveTimer)
      this.saveTimer = setTimeout(() => {
        this.ensureWellArrays()
        const toNullIfEmpty = (v) => (v === '' || v === undefined ? null : v)
        const payload = {
          ...this.plateData,
          image_file_id: toNullIfEmpty(this.plateData.image_file_id),
          excel_file_id: toNullIfEmpty(this.plateData.excel_file_id),
          immune_stage: this.plateData.immune_stage === null ? '' : this.plateData.immune_stage,
          cell_target_id: toNullIfEmpty(this.plateData.cell_target_id),
          pc_upper_id: toNullIfEmpty(this.plateData.pc_upper_id),
          pc_lower_id: toNullIfEmpty(this.plateData.pc_lower_id),
          upper_group: this.plateData.upper_group === null ? '' : this.plateData.upper_group,
          lower_group: this.plateData.lower_group === null ? '' : this.plateData.lower_group,
          upper_mouse_list: this.normalizeSlotValues(this.plateData.upper_mouse_list),
          lower_mouse_list: this.normalizeSlotValues(this.plateData.lower_mouse_list),
          upper_slot_groups: this.normalizeSlotGroups(this.plateData.upper_slot_groups),
          lower_slot_groups: this.normalizeSlotGroups(this.plateData.lower_slot_groups)
        }
        this.$emit('save', payload)
      }, 200)
    },
    onExcelFileChange() {
      if (!this.isEditable) return
      this.$emit('excel-file-change', {
        fileId: this.plateData.excel_file_id,
      })
    },
    onClearExcelFile() {
      if (!this.isEditable) return
      this.plateData.excel_file_id = null
      this.plateData.positive_well_list = []
      this.autoSave()
    },
    onClearFile(type) {
      if (!this.isEditable) return
      if (type === 'image') this.plateData.image_file_id = null
      if (type === 'immune_stage') this.plateData.immune_stage = null
      if (type === 'cell_target_id') this.plateData.cell_target_id = null
      if (type === 'pc_upper_id') this.plateData.pc_upper_id = null
      if (type === 'pc_lower_id') this.plateData.pc_lower_id = null
      if (type === 'upper_group') this.plateData.upper_group = null
      if (type === 'lower_group') this.plateData.lower_group = null
      this.autoSave()
    },
    normalizeSlotValues(list) {
      if (Array.isArray(list) && list.length === 10) {
        return ['NC', ...list, 'PC']
      }

      const source = Array.isArray(list) ? list : []
      const normalized = DEFAULT_SLOT_VALUES.slice()
      for (let i = 0; i < Math.min(source.length, SLOT_COUNT); i += 1) {
        normalized[i] = source[i] === undefined || source[i] === null ? '' : source[i]
      }
      return normalized
    },
    normalizeSlotGroups(groups) {
      if (!Array.isArray(groups)) return []
      const normalized = groups
        .map(group => {
          const start = Number(group.start)
          const end = Number(group.end)
          if (Number.isNaN(start) || Number.isNaN(end)) return null
          const safeStart = Math.max(0, Math.min(SLOT_COUNT - 1, start))
          const safeEnd = Math.max(0, Math.min(SLOT_COUNT - 1, end))
          return {
            start: Math.min(safeStart, safeEnd),
            end: Math.max(safeStart, safeEnd),
            label: group.label || ''
          }
        })
        .filter(Boolean)
        .sort((a, b) => a.start - b.start)

      const result = []
      normalized.forEach(group => {
        const prev = result[result.length - 1]
        if (!prev || group.start > prev.end) {
          result.push(group)
        }
      })
      return result
    },
    ensureWellArrays() {
      this.plateData.upper_mouse_list = this.normalizeSlotValues(this.plateData.upper_mouse_list)
      this.plateData.lower_mouse_list = this.normalizeSlotValues(this.plateData.lower_mouse_list)
      this.plateData.upper_slot_groups = this.normalizeSlotGroups(this.plateData.upper_slot_groups)
      this.plateData.lower_slot_groups = this.normalizeSlotGroups(this.plateData.lower_slot_groups)
    },
    getUpperWell(idx) {
      return Array.isArray(this.plateData.upper_mouse_list)
        ? (this.plateData.upper_mouse_list[idx] || '')
        : ''
    },
    getLowerWell(idx) {
      return Array.isArray(this.plateData.lower_mouse_list)
        ? (this.plateData.lower_mouse_list[idx] || '')
        : ''
    },
    getMouseListField(section) {
      return section === 'upper' ? 'upper_mouse_list' : 'lower_mouse_list'
    },
    isCornerSlot(index) {
      return index === 0 || index === SLOT_COUNT - 1
    },
    setSlotValue(section, idx, val) {
      if (!this.isEditable) return
      const v = (val && val.target) ? val.target.value : val
      this.ensureWellArrays()
      this.plateData[this.getMouseListField(section)][idx] = v
      this.autoSave()
    },
    focusWellInput(row, index) {
      if (index < 1 || index > SLOT_COUNT) return
      const refKey = `${row}-${index}`
      let ref = this.$refs[refKey]
      if (Array.isArray(ref)) ref = ref[0]
      if (!ref) return
      if (typeof ref.focus === 'function') {
        ref.focus()
        return
      }
      const el = ref.$el ? ref.$el.querySelector('input') : null
      if (el) {
        el.focus()
        el.select()
      }
    },
    handleWellPaste(event, row, index) {
      if (!this.isEditable) return
      const values = splitPasteTokens(event.clipboardData?.getData('text/plain'))
      if (values.length <= 1) return

      event.preventDefault()
      const startIdx = index - 1
      this.ensureWellArrays()
      const field = this.getMouseListField(row === 'top' ? 'upper' : 'lower')
      const n = Math.min(values.length, SLOT_COUNT - startIdx)
      for (let i = 0; i < n; i += 1) {
        this.plateData[field][startIdx + i] = values[i]
      }
      this.autoSave()
      this.$nextTick(() => this.focusWellInput(row, Math.min(startIdx + n + 1, SLOT_COUNT)))
    },
    handleWellEnter(row, index) {
      const nextIndex = index + 1
      if (nextIndex > SLOT_COUNT) return
      this.focusWellInput(row, nextIndex)
    },
    getSlotClass(section, index) {
      const selected = this.selectionRange &&
        this.dragState.section === section &&
        index >= this.selectionRange.start &&
        index <= this.selectionRange.end

      return {
        'corner-well': this.isCornerSlot(index),
        'drag-selected': selected
      }
    },
    getGroupField(section) {
      return section === 'upper' ? 'upper_slot_groups' : 'lower_slot_groups'
    },
    getGroupsForSection(section) {
      const field = this.getGroupField(section)
      if (!Array.isArray(this.plateData[field])) {
        this.plateData[field] = []
      }
      return this.plateData[field]
    },
    getGroupStyle(group) {
      const slotWidth = this.wellGridRect?.slotWidth ?? SLOT_WIDTH
      const slotStep = slotWidth + SLOT_GAP
      const start = Math.max(0, Math.min(SLOT_COUNT - 1, Number(group.start)))
      const end = Math.max(start, Math.min(SLOT_COUNT - 1, Number(group.end)))
      const count = end - start + 1
      return {
        left: `${start * slotStep}px`,
        width: `${count * slotWidth + (count - 1) * SLOT_GAP}px`
      }
    },
    getSelectionLabel(section) {
      const range = this.selectionRange
      if (!range) return ''
      const source = this.getGroupsForSection(section).find(group => range.start >= group.start && range.start <= group.end)
      return source && source.label ? source.label : '新分组'
    },
    setSlotGroupLabel(section, index, value) {
      if (!this.isEditable) return
      const groups = this.getGroupsForSection(section)
      if (!groups[index]) return
      groups[index].label = value
      this.$nextTick(() => this.updateGroupTooltipOverflow(section, index))
      this.autoSave()
    },
    groupInputRef(section, index) {
      return `${section}-group-input-${index}`
    },
    updateGroupTooltipOverflow(section, index) {
      const group = this.getGroupsForSection(section)[index]
      const next = { ...this.groupTooltipOverflow[section] }
      if (!group?.label) {
        next[index] = false
        this.groupTooltipOverflow = { ...this.groupTooltipOverflow, [section]: next }
        return
      }
      let ref = this.$refs[this.groupInputRef(section, index)]
      if (Array.isArray(ref)) ref = ref[0]
      const input = ref?.$el?.querySelector?.('input')
      next[index] = !!input && input.scrollWidth > input.clientWidth + 1
      this.groupTooltipOverflow = { ...this.groupTooltipOverflow, [section]: next }
    },
    removeSlotGroup(section, index) {
      if (!this.isEditable) return
      const groups = [...this.getGroupsForSection(section)]
      groups.splice(index, 1)
      this.plateData[this.getGroupField(section)] = groups
      this.autoSave()
    },
    handleSlotMouseDown(event, section, index) {
      if (!this.isEditable || !event.altKey) return
      event.preventDefault()
      this.ensureWellArrays()
      this.dragState = {
        active: true,
        section,
        start: index,
        end: index
      }
    },
    handleSlotMouseEnter(section, index) {
      if (!this.dragState.active || this.dragState.section !== section) return
      this.dragState.end = index
    },
    handleSlotMouseUp() {
      this.finishSlotDrag()
    },
    handleDocumentMouseUp() {
      this.finishSlotDrag()
      this.finishWellDrag()
    },
    finishSlotDrag() {
      if (!this.dragState.active) return
      const section = this.dragState.section
      const range = this.selectionRange
      this.dragState = {
        active: false,
        section: null,
        start: null,
        end: null
      }
      if (!section || !range) return
      this.applySlotSelection(section, range)
    },
    applySlotSelection(section, range) {
      if (!this.isEditable) return
      const groups = this.getGroupsForSection(section)
      const sourceGroup = groups.find(group => range.start >= group.start && range.start <= group.end)
      const nextGroups = []

      groups.forEach(group => {
        const overlap = !(range.end < group.start || range.start > group.end)
        if (!overlap) {
          nextGroups.push({ ...group })
          return
        }
        if (group.start < range.start) {
          nextGroups.push({
            ...group,
            end: range.start - 1
          })
        }
        if (group.end > range.end) {
          nextGroups.push({
            ...group,
            start: range.end + 1
          })
        }
      })

      nextGroups.push({
        start: range.start,
        end: range.end,
        label: sourceGroup ? sourceGroup.label : ''
      })

      this.plateData[this.getGroupField(section)] = nextGroups.sort((a, b) => a.start - b.start)
      this.autoSave()
    },
    calcGridBBoxByMarginPct(iw, ih, { top, left, bottom, right }) {
      const x0 = iw * (left / 100)
      const y0 = ih * (top / 100)
      const w0 = iw * (1 - (left + right) / 100)
      const h0 = ih * (1 - (top + bottom) / 100)
      return { x: x0, y: y0, width: w0, height: h0 }
    },
    resetPlateLayoutMetrics() {
      this.imageNaturalSize = { width: 0, height: 0 }
      this.gridBBox = { x: 0, y: 0, width: 0, height: 0 }
      this.containRect = { dx: 0, dy: 0, scale: 1, dw: 0, dh: 0 }
    },
    handleImageLoad(event) {
      const img = event.target
      this.imageNaturalSize = { width: img.naturalWidth, height: img.naturalHeight }
      this.updateGridBBox(false)
      this.forceRecalc()
    },
    updateGridBBox(shouldSave = true) {
      if (!this.isEditable && shouldSave) return
      if (!this.imageNaturalSize.width) return

      const { width: iw, height: ih } = this.imageNaturalSize
      const { top, left, bottom, right } = this.maskOffset
      this.gridBBox = this.calcGridBBoxByMarginPct(iw, ih, { top, left, bottom, right })
      if (shouldSave) {
        this.autoSave()
      }
    },
    applyPreset(type, shouldSave = false) {
      const tpl = GATE_TEMPLATES[type]
      if (!tpl) return
      
      this.maskOffset = { ...tpl }
      if (this.imageNaturalSize.width) {
        this.updateGridBBox(shouldSave)
      }
    },
    setInstrument(label) {
      if (!this.isEditable) return
      this.plateData.instrument_type = label
      const type = label === '赛多利斯' ? 'cytomics' : 'domestic'
      this.applyPreset(type, true)
    },
    forceRecalc() {
      this.$nextTick(() => {
        requestAnimationFrame(() => {
          this.recalcOverlay()
          requestAnimationFrame(() => this.recalcOverlay())
        })
      })
    },
    recalcOverlay() {
      this.$nextTick(() => {
        const container = this.$refs.imageContainer
        const img = this.$refs.previewImage
        const { width: iw, height: ih } = this.imageNaturalSize
        
        if (!container || !img || !iw || !ih) return

        const c = container.getBoundingClientRect()
        const r = img.getBoundingClientRect()
        const dx = r.left - c.left
        const dy = r.top - c.top
        const scale = r.width / iw
        
        this.containRect = { dx, dy, scale, dw: r.width, dh: r.height }
      })
    },
    wellCodeAt(rowIndex, colIndex) {
      return `${String.fromCharCode(65 + rowIndex)}${colIndex + 1}`
    },
    getWellCellClass(rowIndex, colIndex) {
      const rect = this.wellSelectionRect
      const inDrag = rect &&
        rowIndex >= rect.r0 && rowIndex <= rect.r1 &&
        colIndex >= rect.c0 && colIndex <= rect.c1
      return {
        positive: this.wellMatrix[rowIndex][colIndex],
        'well-drag-preview': inDrag,
        'well-drag-add': inDrag && this.wellDragState.applyPositive,
        'well-drag-remove': inDrag && !this.wellDragState.applyPositive
      }
    },
    resetWellDragState() {
      this.wellDragState = {
        active: false,
        startRow: null,
        startCol: null,
        endRow: null,
        endCol: null,
        applyPositive: true
      }
    },
    updateWellDragEnd(rowIndex, colIndex) {
      if (!this.wellDragState.active) return
      if (rowIndex < 0 || rowIndex > 7 || colIndex < 0 || colIndex > 11) return
      this.wellDragState.endRow = rowIndex
      this.wellDragState.endCol = colIndex
    },
    handleWellMouseDown(event, rowIndex, colIndex) {
      if (!this.isEditable || event.button !== 0) return
      this.wellDragState = {
        active: true,
        startRow: rowIndex,
        startCol: colIndex,
        endRow: rowIndex,
        endCol: colIndex,
        applyPositive: !this.wellMatrix[rowIndex][colIndex]
      }
    },
    handleWellGridMouseMove(event) {
      if (!this.wellDragState.active) return
      const overlay = this.$refs.wellGridOverlay
      const cell = event.target.closest?.('.grid-cell')
      if (!cell || !overlay?.contains(cell)) return
      const row = Number(cell.dataset.row)
      const col = Number(cell.dataset.col)
      if (Number.isNaN(row) || Number.isNaN(col)) return
      this.updateWellDragEnd(row, col)
    },
    finishWellDrag() {
      if (!this.wellDragState.active) return
      const { startRow, startCol, endRow, endCol, applyPositive } = this.wellDragState
      this.resetWellDragState()
      if (!this.isEditable || startRow === null || endRow === null) return
      const r0 = Math.min(startRow, endRow)
      const r1 = Math.max(startRow, endRow)
      const c0 = Math.min(startCol, endCol)
      const c1 = Math.max(startCol, endCol)
      this.applyWellRectangle(r0, c0, r1, c1, applyPositive)
    },
    applyWellRectangle(r0, c0, r1, c1, positive) {
      if (!this.isEditable) return
      const listSet = new Set(
        (Array.isArray(this.plateData.positive_well_list) ? this.plateData.positive_well_list : [])
          .filter(w => w && typeof w === 'string')
      )
      let changed = false
      for (let r = r0; r <= r1; r += 1) {
        for (let c = c0; c <= c1; c += 1) {
          if (this.wellMatrix[r][c] === positive) continue
          this.wellMatrix[r][c] = positive
          changed = true
          const code = this.wellCodeAt(r, c)
          if (positive) listSet.add(code)
          else listSet.delete(code)
        }
      }
      if (!changed) return
      this.plateData.positive_well_list = [...listSet]
      this.autoSave()
    },
    handleMaskToggle() {
      if (!this.isEditable) return
      if (this.plateData.instrument_type === '国产') {
        this.plateData.instrument_type = '赛多利斯'
      } else {
        this.plateData.instrument_type = '国产'
      }
      this.autoSave()
    },
    handleMaskContextMenu() {
      if (!this.isEditable) return
      this.showMaskAdjuster = !this.showMaskAdjuster
    },
    handleDelete() {
      if (!this.isEditable) return
      this.$emit('delete', this.plateData)
    },
    getPlateData() {
      return this.plateData
    },
    initWellMatrix(wells) {
      const matrix = Array(8).fill(null).map(() => Array(12).fill(false))
      wells.forEach(well => {
        const match = well.match(/^([A-H])(\d+)$/)
        if (match) {
          const row = match[1].charCodeAt(0) - 65
          const col = parseInt(match[2]) - 1
          if (row >= 0 && row < 8 && col >= 0 && col < 12) {
            matrix[row][col] = true
          }
        }
      })
      this.wellMatrix = matrix
    }
  },
  mounted() {
    this.$nextTick(() => {
      this.ensureWellArrays()
      
      const el = this.$refs.imageContainer
      if (el && window.ResizeObserver) {
        this._ro = new ResizeObserver(() => this.recalcOverlay())
        this._ro.observe(el)
      }
      if (this.isActive) this.forceRecalc()
      
      const type = this.plateData.instrument_type === '赛多利斯' ? 'cytomics' : 'domestic'
      this.applyPreset(type)
      document.addEventListener('mouseup', this.handleDocumentMouseUp)
    })
  },
  beforeUnmount() {
    if (this._ro) this._ro.disconnect()
    if (this.saveTimer) clearTimeout(this.saveTimer)
    document.removeEventListener('mouseup', this.handleDocumentMouseUp)
    if (this.wellDragState.active) this.resetWellDragState()
  }
}
</script>

<style lang="scss" scoped>
.plate-card {
  .plate-content {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 20px 0 20px 20px;
    min-width: 0;
    overflow-x: auto;
  }
}

/* Component-local small size semantics */
.plate-card :deep(.el-button--small) {
  height: 28px;
  padding: 7px 15px;
  font-size: 12px;
  border-radius: 3px;
}

.plate-card :deep(.el-input--small),
.plate-card :deep(.el-select--small) {
  --el-input-height: 28px;
  font-size: 12px;
}

.plate-card :deep(.el-input--small .el-input__wrapper),
.plate-card :deep(.el-select--small .el-select__wrapper) {
  min-height: 28px;
  font-size: 12px;
}

.plate-card :deep(.el-input-number--small) {
  line-height: 26px;
  font-size: 12px;
}

.plate-card :deep(.el-input-number--small .el-input-number__decrease),
.plate-card :deep(.el-input-number--small .el-input-number__increase) {
  width: 28px;
  font-size: 12px;
}

// 左 2 : 右 7；宽度不足时由 min-width 顶住，再窄则整行横向滚动
$plate-col-left-ratio: 2;
$plate-col-right-ratio: 7;
$plate-col-left-min: 300px;
$plate-col-right-min: 900px;
// 表单行：最长标签宽(max-content) | 间距(2fr,min) | 输入框(5fr,min)，间距:输入框 = 2:5
$plate-form-gap-min: 10px;
$plate-form-input-min: 96px;
$plate-form-cols: max-content minmax(#{$plate-form-gap-min}, 2fr) minmax(#{$plate-form-input-min}, 5fr);
$plate-legend-width: 72px;
$plate-legend-gap: 12px;

.top-row {
  display: flex;
  gap: 20px;
  align-items: stretch;
  min-width: 0;
}

.left-top-panel {
  flex: $plate-col-left-ratio $plate-col-left-ratio 0%;
  min-width: $plate-col-left-min;
  align-self: stretch;
  display: flex;
  flex-direction: column;
  min-height: 0;

  .left-form-grid {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 12px;
    min-height: 0;
    width: 100%;
  }

  .form-section {
    min-width: 0;
    padding: 16px;
    box-sizing: border-box;
    background: #fff;
    border-radius: 8px;
    border: 1px solid #e4e7ed;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    display: grid;
    grid-template-columns: #{$plate-form-cols};
    row-gap: 10px;
    align-content: start;

    .section-header {
      grid-column: 1 / -1;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 2px;
      padding-bottom: 12px;
      border-bottom: 1px solid #ebeef5;
      font-size: 15px;
      font-weight: 700;
      color: #303133;

      .header-left {
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .header-right {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 12px;
        color: #909399;

        .el-icon {
          font-size: 14px;
        }
      }

      .el-icon {
        color: #409EFF;
        font-size: 14px;
      }
    }
  }

  .form-section--files {
    flex-shrink: 0;
  }

  .basic-info-section {
    flex: 1;
    min-height: 0;
  }

  .plate-form {
    grid-column: 1 / -1;
    display: grid;
    grid-template-columns: subgrid;
    row-gap: 10px;
    align-content: start;

    :deep(.el-form-item) {
      display: grid;
      grid-template-columns: subgrid;
      grid-column: 1 / -1;
      align-items: center;
      margin-bottom: 0 !important;

      .el-form-item__label {
        grid-column: 1;
        width: auto !important;
        max-width: none;
        float: none;
        text-align: left;
        justify-content: flex-start;
        padding-right: 0;
        font-size: 14px;
        font-weight: 700;
        line-height: 32px;
        color: #606266;
        white-space: nowrap;
      }

      .el-form-item__content {
        grid-column: 3;
        flex: 1;
        display: flex;
        width: 100%;
        min-width: 0;
        margin-left: 0 !important;

        .el-input,
        .el-select {
          width: 100%;
          min-width: 0;
          font-size: 14px;
        }

        .el-input__wrapper,
        .el-select__wrapper {
          min-width: 0;
        }

        .el-select__selected-item,
        .el-input__inner {
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .el-textarea__inner {
          width: 100%;
        }
      }
    }
  }
}

.right-panel {
  flex: $plate-col-right-ratio $plate-col-right-ratio 0%;
  min-width: $plate-col-right-min;
  display: flex;
  flex-direction: column;
  overflow: visible;

  .image-section {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: visible;
  }

  .section-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    font-size: 15px;
    font-weight: 700;
    color: #303133;
    margin-bottom: 8px;
    padding: 0 10px;

    .header-left {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .header-right {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .el-icon {
      color: #409EFF;
      font-size: 14px;
    }

    .delete-btn {
      color: #F56C6C;
      height: auto;
      font-size: 14px;
      line-height: 1;
      padding: 0 4px;
    }

    .mask-toggle-btn {
      color: #409EFF;
      height: auto;
      font-size: 14px;
      line-height: 1;
      padding: 0 4px;
    }

    .delete-btn .el-icon,
    .mask-toggle-btn .el-icon {
      color: inherit;
    }
  }

  .image-display {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    background: #fafafa;
    border-radius: 8px;
    padding: 12px;
    min-height: 0;
    min-width: 0;
    overflow: hidden;
  }

  .image-cluster {
    display: inline-grid;
    max-width: 100%;
    grid-template-columns: minmax(0, 808px);
    grid-template-rows: auto auto auto;
    row-gap: 8px;

    &.has-legend {
      grid-template-columns: minmax(0, 808px) #{$plate-legend-gap} #{$plate-legend-width};
    }

    .plate-column {
      grid-column: 1;
      min-width: 0;
    }

    .legend-column {
      grid-column: 3;
      grid-row: 2;
      align-self: stretch;
      position: relative;
      width: $plate-legend-width;
      min-height: 0;
    }
  }

  .slot-editor {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    width: 100%;
    max-width: 800px;
    justify-self: center;
    gap: 8px;
    flex-shrink: 0;
  }

  .slot-groups-row {
    position: relative;
    height: 34px;
    flex-shrink: 0;
  }

  .slot-group-block {
    position: absolute;
    top: 0;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid #409EFF;
    border-radius: 8px;
    background: rgba(64, 158, 255, 0.1);
    color: #306cb3;
    overflow: hidden;

    :deep(.el-input__wrapper) {
      box-shadow: none;
      background: transparent;
    }

    :deep(.el-input__inner) {
      height: 30px;
      line-height: 30px;
      padding: 0 16px 0 12px;
      border: none;
      background: transparent;
      color: #306cb3;
      text-align: center;
      font-size: 12px;
      font-weight: 600;
    }

    &.drag-preview {
      border-style: dashed;
      background: rgba(64, 158, 255, 0.18);
      font-size: 12px;
      font-weight: 600;
      pointer-events: none;
      z-index: 2;
    }

    .slot-group-remove {
      position: absolute;
      top: 8px;
      right: 6px;
      font-size: 15px;
      line-height: 1;
      cursor: pointer;
      opacity: 0;
      transition: opacity 0.2s;
    }

    &:hover .slot-group-remove {
      opacity: 0.75;
    }
  }

  .wells-row {
    display: flex;
    gap: 8px;
    flex-shrink: 0;

    .well-input {
      width: var(--slot-well-width, 60px);
      flex-shrink: 0;

      :deep(.el-input__inner) {
        padding-left: 5px;
        padding-right: 5px;
      }

      &.corner-well {
        :deep(.el-input__wrapper) {
          background: #f4f4f5;
          box-shadow: 0 0 0 1px #dcdfe6 inset;
        }

        :deep(.el-input__inner) {
          background: #f4f4f5;
          color: #606266;
          font-weight: 600;
          -webkit-text-fill-color: #606266;
        }
      }

      &.drag-selected {
        :deep(.el-input__wrapper) {
          box-shadow: 0 0 0 1px #409EFF inset, 0 0 0 2px rgba(64, 158, 255, 0.15);
          background: #ecf5ff;
        }
      }
    }
  }

  .dilution-legend {
    box-sizing: border-box;
    pointer-events: none;
    flex-shrink: 0;
    z-index: 11;
    background: #fff;
    border: 1px solid #e4e7ed;
    border-radius: 8px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);

    &__title {
      position: absolute;
      left: 0;
      right: 0;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0 15px;
      font-size: 13px;
      font-weight: 600;
      color: #303133;
      border-bottom: 1px solid #ebeef5;
      background: #fff;
      border-radius: 8px 8px 0 0;
    }

    &__rows {
      position: absolute;
    }

    &__divider {
      position: absolute;
      top: 50%;
      left: 0;
      right: 0;
      z-index: 0;
      height: 1px;
      transform: translateY(-50%);
      background: linear-gradient(90deg, transparent, #dcdfe6 15%, #dcdfe6 85%, transparent);
    }

    &__row {
      position: absolute;
      left: 0;
      right: 0;
      z-index: 1;
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 13px;
      color: #606266;

      span:first-child {
        font-weight: 600;
      }

      span:last-child {
        font-weight: 600;
        font-variant-numeric: tabular-nums;
      }

      &.is-upper span:last-child { color: #409EFF; }
      &.is-lower span:last-child { color: #67C23A; }
    }
  }

  .image-preview-area {
    display: flex;
    align-items: center;
    justify-content: center;
    background: #fff;
    border-radius: 8px;
    border: 2px dashed #e4e7ed;
    position: relative;
    width: 100%;
    max-width: 800px;
    justify-self: center;
    min-height: 450px;

    .empty-image {
      text-align: center;
      color: #c0c4cc;

      .el-icon {
        font-size: 64px;
        margin-bottom: 16px;
      }

      p {
        margin: 0;
        font-size: 14px;
      }
    }

    .preview-image {
      max-width: 100%;
      width: 100%;
      height: auto;
      object-fit: contain;
      display: block;
    }

    .well-grid-overlay {
      position: absolute;
      display: flex;
      flex-direction: column;
      pointer-events: auto;
      z-index: 10;
      user-select: none;
    }

    .mask-adjuster {
      position: absolute;
      top: 10px;
      right: 10px;
      background: rgba(255, 255, 255, 0.95);
      border-radius: 8px;
      padding: 12px;
      box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
      z-index: 20;
      min-width: 200px;

      .adjuster-header {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;
        font-weight: 600;
        color: #303133;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid #ebeef5;

        .el-icon {
          color: #409EFF;
        }
      }

      .adjuster-content {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .adjuster-row {
        display: flex;
        align-items: center;
        gap: 8px;

        span {
          font-size: 12px;
          color: #606266;
          min-width: 24px;
        }

        :deep(.el-input-number) {
          flex: 1;
          width: auto;

          .el-input__wrapper {
            padding-left: 8px;
            padding-right: 8px;
          }

          .el-input__inner {
            padding-left: 8px;
            padding-right: 8px;
          }
        }
      }

      .adjuster-presets {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 8px;
        padding-top: 8px;
        border-top: 1px solid #ebeef5;

        .preset-label {
          font-size: 12px;
          color: #606266;
          min-width: 60px;
        }
      }
    }

    .grid-row {
      display: flex;
      flex: 1;
    }

    .grid-cell {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
      cursor: pointer;
      border: 1px solid rgba(255, 255, 255, 0.5);
      background: rgba(0, 0, 0, 0);
      transition: all 0.2s ease;

      &:hover {
        background: rgba(0, 0, 0, 0.2);
        border-color: rgba(255, 255, 255, 0.7);
      }

      .cell-label {
        position: absolute;
        top: 2px;
        left: 4px;
        font-size: 10px;
        color: rgb(255, 255, 255);
        font-weight: 500;
        text-shadow: 0 1px 2px rgb(0, 0, 0);
      }

      .check-icon {
        position: absolute;
        top: 2px;
        right: 2px;
        color: #f03b3b;
        font-size: 16px;
        font-weight: bold;
        text-shadow: 0 1px 2px rgba(255, 255, 255, 0.8);
      }

      &.positive {
        background: rgba(100, 200, 255, 0.2);
        border-color: rgba(255, 255, 255, 0.6);

        &:hover {
          background: rgba(100, 200, 255, 0.5);
        }
      }

      &.well-drag-preview {
        z-index: 1;
      }

      &.well-drag-add {
        background: rgba(64, 158, 255, 0.45);
        border-color: #409EFF;
        box-shadow: inset 0 0 0 1px rgba(64, 158, 255, 0.6);
      }

      &.well-drag-remove {
        background: rgba(245, 108, 108, 0.35);
        border-color: #f56c6c;
        box-shadow: inset 0 0 0 1px rgba(245, 108, 108, 0.5);
      }
    }
  }
}

</style>
