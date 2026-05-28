<template>
  <div class="plate-card elisa-plate-card">
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
                <el-form-item label="Excel结果">
                  <el-select
                    v-model="plateData.excel_file_id"
                    placeholder="请从上方文件列表中选择"
                    filterable
                    clearable
                    :disabled="!isEditable"
                    style="width: 100%"
                    @change="onExcelSelect"
                    @clear="onClearExcel"
                  >
                    <el-option
                      v-for="file in excelFileOptions"
                      :key="file.id"
                      :label="file.file_name"
                      :value="file.id"
                    />
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
                  <el-input v-model="plateData.qr_code" placeholder="扫描或输入" :disabled="!isEditable" @change="autoSave" />
                </el-form-item>
                <el-form-item label="免疫阶段">
                  <el-select
                    v-model="plateData.immune_stage"
                    placeholder="请选择免疫阶段"
                    clearable
                    :disabled="!isEditable"
                    style="width: 100%"
                    @change="autoSave"
                  >
                    <el-option v-for="s in immuneStageOptions" :key="s" :label="s" :value="s" />
                  </el-select>
                </el-form-item>
                <el-form-item label="检测标靶">
                  <el-select
                    v-model="plateData.protein_target_id"
                    placeholder="请选择检测标靶"
                    clearable
                    :disabled="!isEditable"
                    style="width: 100%"
                    @change="autoSave"
                  >
                    <el-option v-for="t in targetOptions" :key="t.id" :label="t.name" :value="t.id" />
                  </el-select>
                </el-form-item>
                <el-form-item label="PC对照">
                  <el-select
                    v-model="plateData.pc_id"
                    placeholder="请选择PC"
                    clearable
                    :disabled="!isEditable"
                    style="width: 100%"
                    @change="autoSave"
                  >
                    <el-option v-for="pc in pcOptions" :key="pc.id" :label="pc.pc_name" :value="pc.id" />
                  </el-select>
                </el-form-item>
                <el-form-item label="小鼠组别">
                  <el-select
                    v-model="plateData.mouse_group"
                    placeholder="请选择组别"
                    clearable
                    :disabled="!isEditable"
                    style="width: 100%"
                    @change="autoSave"
                  >
                    <el-option v-for="g in groupOptions" :key="g" :label="g" :value="g" />
                  </el-select>
                </el-form-item>
                <el-form-item label="抗原类型">
                  <el-select
                    v-model="plateData.antigen_type"
                    placeholder="请选择或输入"
                    clearable
                    filterable
                    allow-create
                    default-first-option
                    :disabled="!isEditable"
                    style="width: 100%"
                    @change="autoSave"
                  >
                    <el-option v-for="a in antigenTypeOptions" :key="a" :label="a" :value="a" />
                  </el-select>
                </el-form-item>
                <el-form-item label="判定吸光度">
                  <el-input
                    :model-value="absorbanceWavelengthInput"
                    placeholder="如 450 nm"
                    class="absorbance-input"
                    :disabled="!isEditable"
                    @input="onAbsorbanceWavelengthInput"
                    @change="onAbsorbanceWavelengthChange"
                  />
                </el-form-item>
              </el-form>
            </div>
          </div>
        </div>

        <div class="right-panel">
          <div class="preview-section">
            <div class="section-title">
              <div class="header-left">
                <el-icon><Grid /></el-icon>
                <span>ELISA 结果预览</span>
              </div>
              <div class="header-right">
                <el-radio-group
                  v-if="absorbanceViewOptions.length > 1"
                  v-model="absView"
                  size="small"
                  class="abs-toggle"
                >
                  <el-radio-button
                    v-for="opt in absorbanceViewOptions"
                    :key="opt.index"
                    :label="opt.index"
                  >
                    {{ opt.label }}
                  </el-radio-button>
                </el-radio-group>
                <el-button type="text" class="delete-btn" :disabled="!isEditable" @click="handleDelete">
                  <el-icon><Delete /></el-icon>
                  <span>删除此板</span>
                </el-button>
              </div>
            </div>

            <div class="preview-display">
              <div class="plate-cluster">
                <div class="slot-editor upper-slot-editor">
                  <div class="slot-groups-row">
                    <div
                      v-for="(group, gi) in slotGroups"
                      :key="'g-' + gi"
                      class="slot-group-block"
                      :style="groupStyle(group)"
                      @mouseenter="updateGroupTooltipOverflow(gi)"
                    >
                      <el-tooltip
                        :content="group.label"
                        :disabled="!groupTooltipOverflow[gi]"
                        placement="top"
                        effect="dark"
                      >
                        <el-input
                          :ref="groupInputRef(gi)"
                          :model-value="group.label"
                          size="small"
                          placeholder="分组标题"
                          :disabled="!isEditable"
                          @input="setGroupLabel(gi, $event)"
                          @change="autoSave"
                        />
                      </el-tooltip>
                      <span v-if="isEditable" class="slot-group-remove" @click.stop="removeGroup(gi)">×</span>
                    </div>
                    <div
                      v-if="groupDragPreview"
                      class="slot-group-block drag-preview"
                      :style="groupStyle(groupDragPreview)"
                    >
                      {{ groupDragPreview.label || '新分组' }}
                    </div>
                  </div>

                  <div class="wells-row top-wells">
                    <div
                      v-for="item in upperSlotItems"
                      :key="'top-' + item.key"
                      class="well-input"
                      :class="getSlotClass('upper', item)"
                      :style="slotItemStyle(item)"
                      @mouseenter="onSlotMouseEnter('upper', item)"
                      @mouseup="onSlotMouseUp"
                    >
                      <el-input
                        :ref="slotInputRef('upper', item)"
                        :model-value="item.value"
                        size="small"
                        :disabled="!isEditable || item.disabled"
                        @input="setSlotValue('upper', item, $event)"
                        @mousedown="onSlotMouseDown($event, 'upper', item)"
                        @contextmenu.prevent="toggleSlotLayout('upper')"
                        @keydown.enter.prevent="focusNextSlot('upper', item)"
                        @paste="onSlotPaste($event, 'upper', item)"
                      />
                    </div>
                  </div>
                </div>

                <div class="plate-main-row">
                  <div class="elisa-grid-column">
                    <div class="elisa-grid-panel" :class="{ 'has-data': !!displayMatrix }">
                      <div class="elisa-grid-toolbar" :class="{ 'is-placeholder': !displayMatrix }">
                        <span v-if="displayMatrix" class="preview-meta">
                          {{ activeAbsorbance?.label || '吸光度' }}
                          <template v-if="displayWavelength"> · {{ displayWavelength }} nm</template>
                        </span>
                        <span v-else class="preview-meta preview-meta--placeholder">未导入吸光度数据</span>
                      </div>
                      <div class="plate-grid-wrap">
                    <div class="col-labels">
                      <span class="row-label-gap" />
                      <span v-for="c in 12" :key="'c' + c" class="col-label">{{ c }}</span>
                    </div>
                    <div
                      v-for="(rowLabel, ri) in plateRows"
                      :key="rowLabel"
                      class="plate-grid-row"
                    >
                      <span class="row-label">{{ rowLabel }}</span>
                      <div
                        v-for="ci in 12"
                        :key="rowLabel + ci"
                        class="grid-cell"
                        :class="cellClass(ri, ci - 1)"
                        :data-row="ri"
                        :data-col="ci - 1"
                        @mousedown.prevent="onWellMouseDown($event, ri, ci - 1)"
                        @mouseenter="onWellMouseEnter(ri, ci - 1)"
                      >
                        <span class="od-value">{{ cellOdText(ri, ci - 1) }}</span>
                      </div>
                    </div>
                    </div>
                    </div>
                  </div>

                  <div class="dilution-legend" aria-label="行稀释度">
                    <div class="dilution-legend__title">稀释度</div>
                    <div class="dilution-legend__header-gap" />
                    <div
                      v-for="rowIndex in plateRows.length"
                      :key="'dilution-' + rowIndex"
                      class="dilution-legend__row"
                    >
                      <span class="dilution-legend__row-value">{{ formatRowDilution(rowIndex - 1) }}</span>
                    </div>
                  </div>
                </div>

                <div class="slot-editor lower-slot-editor">
                  <div class="wells-row bottom-wells">
                    <div
                      v-for="item in lowerSlotItems"
                      :key="'bottom-' + item.key"
                      class="well-input"
                      :class="getSlotClass('lower', item)"
                      :style="slotItemStyle(item)"
                      @mouseenter="onSlotMouseEnter('lower', item)"
                      @mouseup="onSlotMouseUp"
                    >
                      <el-input
                        :ref="slotInputRef('lower', item)"
                        :model-value="item.value"
                        size="small"
                        :disabled="!isEditable || item.disabled"
                        @input="setSlotValue('lower', item, $event)"
                        @mousedown="onSlotMouseDown($event, 'lower', item)"
                        @contextmenu.prevent="toggleSlotLayout('lower')"
                        @keydown.enter.prevent="focusNextSlot('lower', item)"
                        @paste="onSlotPaste($event, 'lower', item)"
                      />
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
import { Delete, EditPen, FolderOpened, Grid, Loading } from '@element-plus/icons-vue'
import {
  ElButton,
  ElForm,
  ElFormItem,
  ElIcon,
  ElInput,
  ElOption,
  ElRadioButton,
  ElRadioGroup,
  ElSelect,
  ElTooltip,
} from 'element-plus'

import {
  collapseLayout6to5,
  createDefaultLowerSlotList,
  createDefaultUpperSlotList,
  DILUTION_LABELS,
  expandLayout5to6,
  formatOd,
  normalizeSlotGroups,
  normalizeSlotList,
  PLATE_ROWS,
  wellId,
} from '#/utils/elisaPlate'

function splitPasteTokens(text) {
  const normalized = (text || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n').trim()
  if (!normalized) return []
  const lines = normalized.split('\n').map((s) => s.trim()).filter(Boolean)
  if (lines.length > 1) return lines
  const line = lines[0]
  if (/[\t,;]/.test(line)) return line.split(/[\t,;]+/).map((s) => s.trim()).filter(Boolean)
  return [line]
}

export default {
  name: 'ElisaPlateCard',
  components: {
    Delete,
    EditPen,
    ElButton,
    ElForm,
    ElFormItem,
    ElIcon,
    ElInput,
    ElOption,
    ElRadioButton,
    ElRadioGroup,
    ElSelect,
    ElTooltip,
    FolderOpened,
    Grid,
    Loading,
  },
  props: {
    plateData: { type: Object, required: true },
    targetOptions: { type: Array, default: () => [] },
    pcOptions: { type: Array, default: () => [] },
    fileList: { type: Array, default: () => [] },
    immuneStageOptions: { type: Array, default: () => [] },
    groupOptions: { type: Array, default: () => [] },
    antigenTypeOptions: { type: Array, default: () => [] },
    extraAbsorbanceSheets: { type: Array, default: () => [] },
    isSaving: { type: Boolean, default: false },
    isEditable: { type: Boolean, default: true },
  },
  emits: ['delete', 'save', 'excel-file-change'],
  data() {
    return {
      absView: 1,
      absorbanceWavelengthInput: '',
      saveTimer: null,
      wellMatrix: Array(8).fill(null).map(() => Array(12).fill(false)),
      upperSlots: createDefaultUpperSlotList(),
      lowerSlots: createDefaultLowerSlotList(),
      dragState: { active: false, start: null, end: null },
      groupTooltipOverflow: {},
      wellDrag: null,
    }
  },
  computed: {
    plateRows() {
      return PLATE_ROWS
    },
    absorbanceViewOptions() {
      const opts = []
      if (this.plateData.absorbance_1?.matrix) {
        opts.push({ index: 1, label: '吸光度 1', data: this.plateData.absorbance_1 })
      }
      for (const sheet of this.extraAbsorbanceSheets) {
        if (!sheet?.data?.matrix) continue
        opts.push({
          index: sheet.index,
          label: sheet.label || `吸光度 ${sheet.index}`,
          data: sheet.data,
        })
      }
      return opts.sort((a, b) => a.index - b.index)
    },
    activeAbsorbance() {
      const hit = this.absorbanceViewOptions.find((o) => o.index === this.absView)
      return hit || this.absorbanceViewOptions[0] || null
    },
    wellSelectionRect() {
      const d = this.wellDrag
      if (!d?.active || d.startRow === null) return null
      return {
        r0: Math.min(d.startRow, d.endRow),
        r1: Math.max(d.startRow, d.endRow),
        c0: Math.min(d.startCol, d.endCol),
        c1: Math.max(d.startCol, d.endCol),
      }
    },
    excelFileOptions() {
      return this.fileList.filter((f) => /\.(xlsx|xls|csv)$/i.test(f.file_name || ''))
    },
    slotGroups() {
      return normalizeSlotGroups(this.plateData.slot_groups)
    },
    upperSlotItems() {
      return this.buildSlotItems('upper')
    },
    lowerSlotItems() {
      return this.buildSlotItems('lower')
    },
    displayMatrix() {
      return this.activeAbsorbance?.data?.matrix || null
    },
    displayWavelength() {
      return this.activeAbsorbance?.data?.wavelength ?? null
    },
    groupDragPreview() {
      if (!this.dragState.active || this.dragState.start === null) return null
      const start = Math.min(this.dragState.start, this.dragState.end ?? this.dragState.start) + 1
      const end = Math.max(this.dragState.start, this.dragState.end ?? this.dragState.start) + 1
      const source = this.slotGroups.find((g) => start >= g.start && start <= g.end)
      return { start, end, label: source?.label || '新分组' }
    },
    selectionRange() {
      if (!this.dragState.active || this.dragState.start === null) return null
      return {
        start: Math.min(this.dragState.start, this.dragState.end ?? this.dragState.start),
        end: Math.max(this.dragState.start, this.dragState.end ?? this.dragState.start),
      }
    },
  },
  watch: {
    'plateData.positive_well_list': {
      handler(wells) {
        this.initWellMatrix(Array.isArray(wells) ? wells : [])
      },
      immediate: true,
      deep: true,
    },
    'plateData.upper_slot_list': {
      handler(v) {
        this.upperSlots = normalizeSlotList(v, 'upper')
      },
      immediate: true,
      deep: true,
    },
    'plateData.lower_slot_list': {
      handler(v) {
        this.lowerSlots = normalizeSlotList(v, 'lower')
      },
      immediate: true,
      deep: true,
    },
    absorbanceViewOptions: {
      handler(opts) {
        if (!opts.length) return
        const current = Number(this.absView)
        if (!opts.some((o) => o.index === current)) {
          this.absView = opts[0].index
        }
      },
      immediate: true,
    },
    'plateData.absorbance_1': {
      handler(val) {
        const w = val?.wavelength
        this.absorbanceWavelengthInput = w === null || w === undefined ? '' : String(w)
      },
      immediate: true,
      deep: true,
    },
  },
  mounted() {
    document.addEventListener('mouseup', this.onDocumentMouseUp)
  },
  beforeUnmount() {
    document.removeEventListener('mouseup', this.onDocumentMouseUp)
    if (this.saveTimer) clearTimeout(this.saveTimer)
  },
  methods: {
    syncSlots() {
      this.plateData.upper_slot_list = { ...this.upperSlots }
      this.plateData.lower_slot_list = { ...this.lowerSlots }
    },
    onExcelSelect() {
      this.$emit('excel-file-change', { fileId: this.plateData.excel_file_id })
    },
    onClearExcel() {
      this.plateData.excel_file_id = null
      this.plateData.absorbance_1 = null
      this.plateData.positive_well_list = []
      this.absorbanceWavelengthInput = ''
      this.absView = 1
      this.$emit('excel-file-change', { fileId: null })
    },
    onAbsorbanceWavelengthInput(val) {
      this.absorbanceWavelengthInput = val?.target?.value ?? val
    },
    onAbsorbanceWavelengthChange() {
      if (!this.isEditable) return
      const raw = String(this.absorbanceWavelengthInput || '').trim()
      const wavelength = raw === '' ? null : Number.parseInt(raw, 10)
      const matrix = this.plateData.absorbance_1?.matrix ?? null
      this.plateData.absorbance_1 = { wavelength: Number.isNaN(wavelength) ? null : wavelength, matrix }
      this.autoSave()
    },
    autoSave() {
      if (!this.isEditable) return
      if (this.saveTimer) clearTimeout(this.saveTimer)
      this.saveTimer = setTimeout(() => {
        this.syncSlots()
        const toNullIfEmpty = (v) => (v === '' || v === undefined ? null : v)
        this.$emit('save', {
          ...this.plateData,
          plate_type: 'elisa',
          excel_file_id: toNullIfEmpty(this.plateData.excel_file_id),
          immune_stage: this.plateData.immune_stage ?? '',
          protein_target_id: toNullIfEmpty(this.plateData.protein_target_id),
          pc_id: toNullIfEmpty(this.plateData.pc_id),
          slot_groups: this.slotGroups,
          upper_slot_list: this.upperSlots,
          lower_slot_list: this.lowerSlots,
          positive_well_list: Array.isArray(this.plateData.positive_well_list)
            ? this.plateData.positive_well_list
            : [],
          absorbance_1: this.plateData.absorbance_1,
        })
      }, 200)
    },
    getSlotList(section) {
      return section === 'upper' ? this.upperSlots : this.lowerSlots
    },
    buildSlotItems(section) {
      const list = this.getSlotList(section)
      const ranges = list.layout === '6pair'
        ? [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9], [10, 11]]
        : [[0, 0], [1, 2], [3, 4], [5, 6], [7, 8], [9, 10], [11, 11]]

      return ranges.map(([start, end]) => {
        const disabled = list.layout === '5pair' && (start === 0 || start === 11)
        return {
          key: `${start}-${end}`,
          start,
          end,
          disabled,
          value: disabled ? 'N/A' : (list.values[start] || ''),
        }
      })
    },
    slotItemStyle(item) {
      return { gridColumn: `${item.start + 2} / ${item.end + 3}` }
    },
    slotInputRef(section, item) {
      return `${section}-slot-${item.start}-${item.end}`
    },
    focusSlotInput(section, item) {
      if (!item || item.disabled) return
      let ref = this.$refs[this.slotInputRef(section, item)]
      if (Array.isArray(ref)) ref = ref[0]
      if (!ref) return
      if (typeof ref.focus === 'function') {
        ref.focus()
        return
      }
      const input = ref.$el?.querySelector?.('input')
      if (input) {
        input.focus()
        input.select()
      }
    },
    getNextEditableSlot(section, item) {
      return this.buildSlotItems(section).find((next) => !next.disabled && next.start > item.start)
    },
    focusNextSlot(section, item) {
      const next = this.getNextEditableSlot(section, item)
      if (next) this.$nextTick(() => this.focusSlotInput(section, next))
    },
    handleDelete() {
      if (!this.isEditable) return
      this.$emit('delete', this.plateData)
    },
    groupStyle(group) {
      const start = Math.max(1, Math.min(12, Number(group.start))) - 1
      const end = Math.max(start, Math.min(11, Number(group.end) - 1))
      return {
        gridColumn: `${start + 2} / ${end + 3}`,
      }
    },
    groupInputRef(index) {
      return `group-input-${index}`
    },
    updateGroupTooltipOverflow(index) {
      const group = this.slotGroups[index]
      if (!group?.label) {
        this.groupTooltipOverflow = { ...this.groupTooltipOverflow, [index]: false }
        return
      }
      let ref = this.$refs[this.groupInputRef(index)]
      if (Array.isArray(ref)) ref = ref[0]
      const input = ref?.$el?.querySelector?.('input')
      const overflow = !!input && input.scrollWidth > input.clientWidth + 1
      this.groupTooltipOverflow = { ...this.groupTooltipOverflow, [index]: overflow }
    },
    setGroupLabel(index, val) {
      const v = val?.target?.value ?? val
      const groups = [...this.slotGroups]
      if (groups[index]) {
        groups[index].label = v
        this.plateData.slot_groups = groups
        this.$nextTick(() => this.updateGroupTooltipOverflow(index))
      }
    },
    removeGroup(index) {
      const groups = [...this.slotGroups]
      groups.splice(index, 1)
      this.plateData.slot_groups = groups
      this.autoSave()
    },
    setSlotValue(section, item, val) {
      if (!this.isEditable || item.disabled) return
      const v = val?.target?.value ?? val
      const list = { ...this.getSlotList(section), values: [...this.getSlotList(section).values] }
      for (let i = item.start; i <= item.end; i += 1) list.values[i] = v
      if (section === 'upper') this.upperSlots = list
      else this.lowerSlots = list
      this.syncSlots()
      this.autoSave()
    },
    onSlotPaste(event, section, startItem) {
      if (!this.isEditable) return
      const tokens = splitPasteTokens(event.clipboardData?.getData('text/plain'))
      if (tokens.length <= 1) return
      event.preventDefault()
      const list = { ...this.getSlotList(section), values: [...this.getSlotList(section).values] }
      let ti = 0
      const items = this.buildSlotItems(section).filter((item) => !item.disabled && item.start >= startItem.start)
      for (const item of items) {
        if (ti >= tokens.length) break
        const value = tokens[ti++]
        for (let i = item.start; i <= item.end; i += 1) list.values[i] = value
      }
      if (section === 'upper') this.upperSlots = list
      else this.lowerSlots = list
      this.syncSlots()
      this.autoSave()
      const next = items[ti] || items[items.length - 1]
      this.$nextTick(() => this.focusSlotInput(section, next))
    },
    onSlotMouseDown(event, section, item) {
      if (!this.isEditable) return
      if (event.altKey) {
        if (section !== 'upper' || item.disabled) return
        event.preventDefault()
        this.dragState = { active: true, start: item.start, end: item.end }
      }
    },
    onSlotMouseEnter(section, item) {
      if (this.dragState.active) {
        if (section !== 'upper' || item.disabled) return
        this.dragState.end = item.end
        return
      }
    },
    onSlotMouseUp() {
      this.finishSlotDrag()
    },
    onDocumentMouseUp() {
      this.finishSlotDrag()
      if (this.wellDrag?.active) {
        const d = this.wellDrag
        this.wellDrag = null
        const r0 = Math.min(d.startRow, d.endRow)
        const r1 = Math.max(d.startRow, d.endRow)
        const c0 = Math.min(d.startCol, d.endCol)
        const c1 = Math.max(d.startCol, d.endCol)
        this.applyWellRect(r0, c0, r1, c1, d.applyPositive)
      }
    },
    toggleSlotLayout(section) {
      if (!this.isEditable) return
      const slots = this.getSlotList(section)
      const next = slots.layout === '5pair' ? expandLayout5to6(slots) : collapseLayout6to5(slots)
      if (section === 'upper') this.upperSlots = next
      else this.lowerSlots = next
      this.syncSlots()
      this.autoSave()
    },
    finishSlotDrag() {
      if (!this.dragState.active) return
      const { start, end } = this.dragState
      this.dragState = { active: false, start: null, end: null }
      if (start === null || end === null) return
      const colStart = Math.min(start, end) + 1
      const colEnd = Math.max(start, end) + 1
      const groups = [...this.slotGroups]
      const sourceGroup = groups.find((g) => colStart >= g.start && colStart <= g.end)
      const nextGroups = []

      for (const group of groups) {
        const overlap = !(colEnd < group.start || colStart > group.end)
        if (!overlap) {
          nextGroups.push({ ...group })
          continue
        }
        if (group.start < colStart) {
          nextGroups.push({ ...group, end: colStart - 1 })
        }
        if (group.end > colEnd) {
          nextGroups.push({ ...group, start: colEnd + 1 })
        }
      }

      nextGroups.push({
        start: colStart,
        end: colEnd,
        label: sourceGroup?.label || '',
      })
      this.plateData.slot_groups = nextGroups.sort((a, b) => a.start - b.start)
      this.autoSave()
    },
    getSlotClass(section, item) {
      const range = this.selectionRange
      const selected = range && !(item.end < range.start || item.start > range.end)
      return {
        'corner-well': item.disabled,
        'drag-selected': selected && section === 'upper',
      }
    },
    cellOdText(row, col) {
      return formatOd(this.displayMatrix?.[row]?.[col])
    },
    formatRowDilution(rowIndex) {
      return rowIndex < DILUTION_LABELS.length ? DILUTION_LABELS[rowIndex] : ''
    },
    cellClass(row, col) {
      const rect = this.wellSelectionRect
      const inDrag =
        rect && row >= rect.r0 && row <= rect.r1 && col >= rect.c0 && col <= rect.c1
      const applyPositive = this.wellDrag?.applyPositive
      return {
        'is-positive': this.wellMatrix[row]?.[col],
        'is-empty': !this.displayMatrix,
        'well-drag-add': inDrag && applyPositive,
        'well-drag-remove': inDrag && !applyPositive,
      }
    },
    initWellMatrix(wells) {
      const matrix = Array(8).fill(null).map(() => Array(12).fill(false))
      wells.forEach((well) => {
        const m = String(well).match(/^([A-H])(\d+)$/i)
        if (!m) return
        const row = m[1].toUpperCase().charCodeAt(0) - 65
        const col = Number.parseInt(m[2], 10) - 1
        if (row >= 0 && row < 8 && col >= 0 && col < 12) matrix[row][col] = true
      })
      this.wellMatrix = matrix
    },
    onWellMouseDown(event, row, col) {
      if (!this.isEditable) return
      this.wellDrag = {
        active: true,
        startRow: row,
        startCol: col,
        endRow: row,
        endCol: col,
        applyPositive: !this.wellMatrix[row][col],
      }
    },
    onWellMouseEnter(row, col) {
      if (!this.wellDrag?.active) return
      this.wellDrag.endRow = row
      this.wellDrag.endCol = col
    },
    applyWellRect(r0, c0, r1, c1, positive) {
      const set = new Set(
        (Array.isArray(this.plateData.positive_well_list) ? this.plateData.positive_well_list : []).filter(Boolean),
      )
      let changed = false
      for (let r = r0; r <= r1; r += 1) {
        for (let c = c0; c <= c1; c += 1) {
          if (this.wellMatrix[r][c] === positive) continue
          this.wellMatrix[r][c] = positive
          changed = true
          const code = wellId(r, c + 1)
          if (positive) set.add(code)
          else set.delete(code)
        }
      }
      if (changed) {
        this.plateData.positive_well_list = [...set]
        this.autoSave()
      }
    },
  },
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

$plate-col-left-ratio: 2;
$plate-col-right-ratio: 7;
$plate-col-left-min: 300px;
$plate-col-right-min: 900px;
$plate-form-gap-min: 10px;
$plate-form-input-min: 96px;
$plate-form-cols: max-content minmax(#{$plate-form-gap-min}, 2fr) minmax(#{$plate-form-input-min}, 5fr);
$plate-legend-width: 72px;
$plate-legend-gap: 12px;
$plate-cell-w: 52px;
$plate-cell-h: 32px;
$plate-cell-gap: 8px;
$plate-row-gap: 2px;
$plate-row-label-w: 28px;
$plate-grid-w: $plate-row-label-w + 12 * $plate-cell-w + 12 * $plate-cell-gap;
$plate-panel-pad-x: 16px;
$plate-panel-pad-y: 12px;
$plate-toolbar-h: 18px;
$plate-toolbar-gap: 8px;
$plate-col-label-h: 16px;
$plate-col-label-gap: 4px;
$plate-panel-w: $plate-grid-w + 2 * $plate-panel-pad-x;
$plate-grid-header-h: $plate-panel-pad-y + $plate-toolbar-h + $plate-toolbar-gap + $plate-col-label-h + $plate-col-label-gap;
$plate-grid-body-h: 8 * ($plate-cell-h + $plate-row-gap);
$plate-panel-h: $plate-grid-header-h + $plate-grid-body-h + $plate-panel-pad-y;
$plate-legend-title-h: 28px;

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
      }

      .el-icon {
        color: #409eff;
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

        .absorbance-input :deep(.el-input__inner) {
          padding-right: 28px;
        }

        .absorbance-input {
          position: relative;

          &::after {
            content: 'nm';
            position: absolute;
            top: 50%;
            right: 10px;
            z-index: 1;
            transform: translateY(-50%);
            font-size: 12px;
            color: #909399;
            pointer-events: none;
          }
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

  .preview-section {
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

    .wavelength-tag {
      font-size: 12px;
      color: #909399;
      font-weight: normal;
    }

    .header-right {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }

    .abs-toggle {
      flex-shrink: 0;
    }

    .el-icon {
      color: #409eff;
      font-size: 14px;
    }

    .delete-btn {
      color: #f56c6c;
      height: auto;
      font-size: 14px;
      line-height: 1;
      padding: 0 4px;
    }

    .delete-btn .el-icon {
      color: inherit;
    }
  }

  .preview-display {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    background: #fafafa;
    border-radius: 8px;
    padding: 16px;
    min-height: 0;
    min-width: 0;
    overflow: auto;
  }

  .plate-cluster {
    display: grid;
    grid-template-columns: $plate-panel-w $plate-legend-gap $plate-legend-width;
    grid-auto-rows: auto;
    justify-content: center;
    align-items: start;
    gap: 12px;
    column-gap: 0;
    min-width: $plate-panel-w + $plate-legend-gap + $plate-legend-width;
    width: $plate-panel-w + $plate-legend-gap + $plate-legend-width;
  }

  .plate-main-row {
    display: contents;
  }

  .elisa-grid-column {
    grid-column: 1;
    grid-row: 2;
    flex: 0 1 auto;
    min-width: 0;
    max-width: 100%;
  }

  .dilution-legend {
    grid-column: 3;
    grid-row: 2;
    flex: 0 1 72px;
    width: 72px;
    min-width: 72px;
  }
}

@media (max-width: 1280px) {
  .plate-card.elisa-plate-card .right-panel {
    min-width: 0;
  }
}

.slot-editor {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  position: relative;
  width: $plate-panel-w;
  max-width: none;

  &.upper-slot-editor {
    grid-column: 1;
    grid-row: 1;
  }

  &.lower-slot-editor {
    grid-column: 1;
    grid-row: 3;
  }
}

.slot-groups-row {
  display: grid;
  grid-template-columns: $plate-row-label-w repeat(12, $plate-cell-w);
  grid-template-rows: 32px;
  gap: $plate-cell-gap;
  width: $plate-grid-w;
  height: 34px;
  flex-shrink: 0;
}

.slot-group-block {
  position: relative;
  grid-row: 1;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #409eff;
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
  display: grid;
  grid-template-columns: $plate-row-label-w repeat(12, $plate-cell-w);
  gap: $plate-cell-gap;
  width: $plate-grid-w;
  flex-shrink: 0;
  position: relative;

  .well-input {
    min-width: 0;

    :deep(.el-input) {
      width: 100%;
    }

    :deep(.el-input__inner) {
      text-align: center;
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

    &.drag-selected :deep(.el-input__wrapper) {
      box-shadow: 0 0 0 1px #409eff inset, 0 0 0 2px rgba(64, 158, 255, 0.15);
      background: #ecf5ff;
    }
  }
}

.elisa-grid-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  background: #fff;
  border-radius: 8px;
  outline: 2px dashed #e4e7ed;
  outline-offset: 0;
  padding: $plate-panel-pad-y $plate-panel-pad-x;
  box-sizing: border-box;

  &.has-data {
    outline-style: solid;
    outline-color: #e4e7ed;
  }
}

.elisa-grid-toolbar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: $plate-toolbar-h;
  margin-bottom: $plate-toolbar-gap;

  .preview-meta {
    font-size: 12px;
    color: #909399;
    white-space: nowrap;
  }

  &.is-placeholder .preview-meta--placeholder {
    color: #c0c4cc;
  }
}

.plate-grid-wrap {
  width: $plate-grid-w;
  max-width: 100%;
}

.col-labels {
  display: grid;
  grid-template-columns: $plate-row-label-w repeat(12, $plate-cell-w);
  gap: $plate-cell-gap;
  height: $plate-col-label-h;
  align-items: center;
  margin-bottom: $plate-col-label-gap;
  font-size: 11px;
  color: #909399;
  text-align: center;

  .row-label-gap {
    width: 28px;
  }
}

.plate-grid-row {
  display: grid;
  grid-template-columns: $plate-row-label-w repeat(12, $plate-cell-w);
  gap: $plate-cell-gap;
  height: $plate-cell-h;
  margin-bottom: $plate-row-gap;
}

.row-label {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: #606266;
}

.grid-cell {
  height: $plate-cell-h;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: #fff;
  user-select: none;

  .od-value {
    font-size: 10px;
    color: #303133;
  }

  &.is-positive {
    background: #fef0f0;
    border-color: #f56c6c;

    .od-value {
      color: #f56c6c;
      font-weight: 600;
    }
  }

  &.is-empty .od-value {
    color: #c0c4cc;
  }

  &.well-drag-add {
    background: #fef0f0;
    border-color: #f56c6c;
  }

  &.well-drag-remove {
    background: #f4f4f5;
    border-color: #909399;
  }
}

.dilution-legend {
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  height: $plate-panel-h;
  background: #fff;
  outline: 1px solid #e4e7ed;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  overflow: hidden;

  &__title {
    height: $plate-legend-title-h;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 600;
    color: #303133;
    border-bottom: 1px solid #ebeef5;
    background: #fafafa;
  }

  &__header-gap {
    height: $plate-grid-header-h - $plate-legend-title-h;
    border-bottom: 1px solid #f0f2f5;
  }

  &__row {
    height: $plate-cell-h + $plate-row-gap;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 10px;
    font-size: 12px;
    border-bottom: 1px solid #f5f7fa;

    &:last-child {
      border-bottom: none;
    }
  }

  &__row-value {
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    color: #409eff;
    text-align: center;
    flex: 1;
  }
}

</style>
