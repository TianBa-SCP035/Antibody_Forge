import { ElMessage, ElMessageBox } from 'element-plus'
import { h } from 'vue'

import { notifyApiError } from '#/api/errors'
import { getTiterPriorityTone } from '#/utils/serumProjectStatus'
import { getCachedUserNames, loadAllUserNames } from '#/utils/userOptions'

import { readClipboardGrid } from './clipboardGrid'
import {
  coerceFieldValue,
  displayCodes,
  displayTags,
  fieldStringMax,
  joinTags,
  listFieldText,
  optionLabel,
  optionValue,
  splitTags,
} from './fieldSchema'
import sheetSelectionMixin from './sheetSelectionMixin'
import { uniqueTargetCodes } from './targetOptions'
import { coerceWorkbenchViewMode, EXCEL_VIEW, WORKBENCH_VIEW } from './viewMode'

const SHEET_CUSTOM_EDIT_RENDER = Object.freeze({ name: 'VxeInput' })
const SHEET_TARGET_POPUP_CONFIG = Object.freeze({
  className: 'sheet-picker-popup',
  placement: 'bottom',
  width: 300,
})
const SHEET_CHOICE_POPUP_CONFIG = Object.freeze({
  className: 'sheet-picker-popup',
  placement: 'bottom',
  width: 220,
})
const SHEET_CATALOG_POPUP_CONFIG = Object.freeze({
  className: 'sheet-picker-popup',
  placement: 'bottom',
  width: 280,
})
const SHEET_EDIT_RENDER_CACHE = new Map()
// 页面名 -> 上次的视图（工作台 / Excel）：离开再回来仍是那个视图，刷新页面后回到工作台视图
const LAST_VIEW_MODES = new Map()
const TARGET_KEYS = ['target_codes', 'target_name']
const USER_TYPES = new Set(['user', 'users'])
const choiceOption = (item) => (item && typeof item === 'object' ? item : { label: item, value: item })
const CHOICE_EDITS = new Set(['select', 'multi', 'tags'])
const SHEET_UNDO_TTL_MS = 10 * 60 * 1000
const SHEET_UNDO_LIMIT = 20
const SHEET_UNDO_PREVIEW = 5

/**
 * Excel 视图的编辑层：键入、双击编辑、批量编辑、删除、粘贴保存、撤回。划选和复制在 sheetSelectionMixin，队列排序在 workbenchQueueSortMixin。
 * 多格保存（粘贴、批量编辑、清空、撤回）都走 saveSheetCells；单格编辑走 finishSheetEdit。两条路径保存成功后各记一步撤回。
 * 约定见 docs/modules/workbench.md。
 * 页面需提供：list, canEdit，组件选项 workbenchFields（fieldSchema.js 的 defineFields）和 workbenchSheet（见 sheetSelectionMixin）。
 * 视图（viewMode）按页面名记住，切到 Excel 时加载全部人员名单 allUserOptions。
 * 字段相关的默认实现都按字段类型走：coerceSheetValue（校验转换，特殊列覆写后在末尾调 coerceSheetField）、
 * sheetChoiceOptionsMap / sheetChoiceSelectOptions（可选项）、isUserColumn、sheetFormatter / sheetDirectTextValue（显示）、
 * sheetStringMax（长度上限）。动态可选项由页面覆写 fieldOptions(field, row)，人员列再并入全部人员名单 allUserOptions。
 * finishSheetEdit / assignSheetValue / sheetValidationMessage 有默认实现：读值走 sheetEditInput，页面特有的校验原因写 sheetValidationExtraMessage。
 * 多格保存默认调组件选项 workbenchApi.saveBatch（见 workbenchCrudMixin）；其余环节都有默认实现，按需覆写 sheetPaste* 钩子。
 * 锁定规则覆写 sheetCellLockReason，返回原因文案；双击或键入锁定格时提示。只读列可在列定义写 lockHint。
 * 单格保存必须 patchExistingListRow，禁止 splice 换行对象。
 * 行选择列用 excelRowSelectKey：引用了 workbenchQueueSortMixin 的页面是 sort_order，其余页面设成自己的首列（如 id）。
 * WorkbenchSheet 的标准列按列定义 edit 分：target 靶点列、tags 多值列（可自填）、select / multi 选择列（isSheetChoiceColumn）、其余普通列。
 * 选择列钩子都有默认实现：sheetChoiceSelectOptions、isUserColumn（可搜索）、isSheetMultiColumn、sheetChoiceClearable、
 * sheetChoiceModelKey（下拉绑定的字段）、isSheetPickerCell（这一格是否给下拉）、sheetChoiceDirectValue / setSheetChoiceDirectValue（键入）。
 * 页面自带编辑器的列覆写 isSheetCustomPicker，整列自绘的覆写 isSheetCustomColumn，配合 WorkbenchSheet 的 picker / column 插槽。
 */
export default {
  mixins: [sheetSelectionMixin],
  data() {
    return {
      viewMode: coerceWorkbenchViewMode(LAST_VIEW_MODES.get(this.$options.name)),
      allUserOptions: getCachedUserNames(),
      pendingSheetOps: new Set(),
      sheetEditOriginal: null,
      sheetEditSource: '',
      sheetKeyboardChain: Promise.resolve(),
      sheetCustomEditRender: SHEET_CUSTOM_EDIT_RENDER,
      sheetTargetPopupConfig: SHEET_TARGET_POPUP_CONFIG,
      sheetChoicePopupConfig: SHEET_CHOICE_POPUP_CONFIG,
      sheetCatalogPopupConfig: SHEET_CATALOG_POPUP_CONFIG,
    }
  },
  computed: {
    isExcelMode() {
      return this.viewMode === EXCEL_VIEW
    },
    sheetStringMax() {
      return fieldStringMax(this.$options.workbenchFields)
    },
    sheetChoiceOptionsMap() {
      const map = Object.create(null)
      for (const column of this.sheetColumns || []) {
        const field = this.workbenchField(column.key)
        if (field && CHOICE_EDITS.has(column.edit)) map[column.key] = this.sheetFieldOptions(field).map(choiceOption)
      }
      return map
    },
    sheetEditConfig() {
      return Object.freeze({
        trigger: 'dblclick',
        mode: 'cell',
        showIcon: false,
        beforeEditMethod: this.sheetBeforeEdit,
      })
    },
  },
  watch: {
    viewMode(value) {
      LAST_VIEW_MODES.set(this.$options.name, value)
      this.clearSheetRange()
      this.loadSheetColumnColors()
      if (this.isExcelMode) this.loadAllUserOptions()
    },
  },
  created() {
    if (import.meta.env.DEV && !this.$options.workbenchFields) {
      console.warn(`[workbenchExcelMixin] ${this.$options.name} 没有声明 workbenchFields，单元格校验和请求体会缺字段`)
    }
    this.sheetBatchEdit = null
    this.sheetUndoBusy = false
    this.sheetUndoStack = []
    if (this.isExcelMode) this.loadAllUserOptions()
  },
  methods: {
    async toggleViewMode() {
      if (this.isExcelMode) {
        if (!await this.flushPendingSheetEdits()) return
        this.viewMode = WORKBENCH_VIEW
        return
      }
      this.closeDrawer?.()
      this.viewMode = EXCEL_VIEW
    },
    openColumnPicker() {
      this.$refs.workbenchTable?.openColumnPicker()
    },
    async resetSheetColumnOrder() {
      if (!this.isExcelMode) {
        this.$refs.workbenchTable?.resetColumnOrder()
        return
      }
      if (!await this.flushPendingSheetEdits()) return
      this.resetSheetColumns()
    },
    sheetBeforeEdit({ row, column }) {
      const key = column?.field
      const allowed = Boolean(key) && !this.isSheetCellLocked(row, key)
      if (!allowed) this.sheetEditSource = ''
      return allowed
    },
    sheetEditRender(column) {
      if (column?.edit === 'readonly') return undefined
      const cacheKey = column?.edit === 'date' ? `date:${column.key}` : `text:${column.key}`
      const cached = SHEET_EDIT_RENDER_CACHE.get(cacheKey)
      if (cached) return cached
      const render = Object.freeze(
        column?.edit === 'date'
          ? {
              name: 'VxeInput',
              props: {
                className: 'sheet-grid-editor sheet-date-editor',
                clearable: false,
                editable: true,
                labelFormat: 'yyyy-MM-dd',
                placeholder: 'YYYY-MM-DD',
                type: 'date',
                valueFormat: 'yyyy-MM-dd',
              },
            }
          : {
              name: 'VxeInput',
              props: {
                align: column?.key === 'sort_order' ? 'center' : undefined,
                className: 'sheet-grid-editor',
                clearable: false,
                placeholder: '',
                type: 'text',
              },
            },
      )
      SHEET_EDIT_RENDER_CACHE.set(cacheKey, render)
      return render
    },
    // 页面有自己的锁定规则时覆写这个方法，返回不可编辑的原因；空串表示可编辑。
    sheetCellLockReason(row, key) {
      if (!this.canEdit) return '你没有编辑权限'
      return this.sheetSortLockReason?.(row, key) || this.sheetReadonlyLockReason(key)
    },
    isSheetCellLocked(row, key) {
      return Boolean(this.sheetCellLockReason(row, key))
    },
    notifySheetCellLocked(row, key) {
      const reason = this.sheetCellLockReason(row, key)
      if (reason) ElMessage.info({ message: reason, grouping: true })
      return Boolean(reason)
    },
    sheetColumnLabel(key) {
      return this.sheetColumnByKey.get(key)?.column?.label
        || this.sheetPasteColumns().find((column) => column.key === key)?.label
        || '该字段'
    },
    sheetReadonlyLockReason(key) {
      const column = this.sheetColumnByKey.get(key)?.column
      if (column?.edit !== 'readonly') return ''
      return column.lockHint || `「${column.label}」不能在表格里修改`
    },
    async revealCreatedRow(saved, { skipRemoteCheck = false } = {}) {
      if (!saved?.id) return saved
      const loadPageOfSaved = () => {
        this.listQuery.page = this.queuePageOf?.(saved) || 1
        return this.getList({ skipRemoteCheck })
      }
      await loadPageOfSaved()
      let row = this.list.find((item) => item.id === saved.id)
      if (this.viewMode === WORKBENCH_VIEW) {
        this.openDrawer?.(row || saved)
        this.$nextTick(() => {
          this.$refs.workbenchTable?.$el
            ?.querySelector('.el-table__row.is-editing')
            ?.scrollIntoView?.({ block: 'nearest' })
        })
        return row || saved
      }
      if (!row && typeof this.resetFilters === 'function') {
        this.resetFilters()
        await loadPageOfSaved()
        row = this.list.find((item) => item.id === saved.id)
        ElMessage.info(row ? '已清空筛选和表头排序，显示新建的行' : '新建的行不在当前视图里')
      }
      if (row) {
        const rowIndex = this.list.indexOf(row)
        await this.$nextTick()
        await this.sheetEl('table')?.scrollToRow?.(row)
        await this.selectSheetRange({ r1: rowIndex, c1: 0, r2: rowIndex, c2: this.sheetColumns.length - 1 })
      }
      return row || saved
    },
    setSheetDirectValue(row, key, text) {
      row[key] = text
    },
    sheetValueSnapshot(row, key) {
      return this.cloneSheetValue(row?.[key])
    },
    restoreSheetEditValue(row, key, value) {
      if (key === 'target_codes') {
        row.target_codes = uniqueTargetCodes(value)
        return
      }
      row[key] = this.cloneSheetValue(value)
    },
    workbenchField(key) {
      return this.$options.workbenchFields?.[key]
    },
    /** 字段的可选项：页面 optionLists 里有这个字段键就用它，否则用字段定义的静态可选项；随行变化的覆写这里。 */
    fieldOptions(field) {
      return this.optionLists?.[field.key] ?? field.options ?? []
    },
    /** Excel 里的可选项：人员列并入全部人员名单，键入和粘贴都按它核对。 */
    sheetFieldOptions(field, row) {
      const options = this.fieldOptions(field, row)
      if (!USER_TYPES.has(field.type)) return options
      return [...new Set([...options, ...(this.allUserOptions || [])].map((item) => String(item ?? '').trim()).filter(Boolean))]
    },
    /** 按字段类型校验转换；页面覆写 coerceSheetValue 处理特殊列，其余调这里。 */
    coerceSheetField(key, text, row) {
      const field = this.workbenchField(key)
      if (!field) return { ok: false, reason: 'unknown' }
      return coerceFieldValue(field, text, this.sheetFieldOptions(field, row))
    },
    coerceSheetValue(key, text, row) {
      return this.coerceSheetField(key, text, row)
    },
    /** 下拉选项是 { value, label } 的字段显示 label。 */
    sheetOptionLabel(key, value) {
      return optionLabel(this.workbenchField(key)?.options, value)
    },
    /** 覆写 sheetCellValue 的列在这里返回 formatSheetCellValue，单元格才显示推算后的值。 */
    sheetFormatter(column) {
      return this.sheetTypeFormatter(column)
    },
    formatSheetCellValue({ row, column }) {
      return this.sheetDirectTextValue(row, column.field)
    },
    sheetFieldToneClass({ row, column }) {
      return column?.field === 'priority' ? `sheet-tone-${getTiterPriorityTone(row?.priority)}` : ''
    },
    /** 按字段类型的单元格显示；页面覆写 sheetFormatter 后，其余列调这里。 */
    sheetTypeFormatter(column) {
      const type = this.workbenchField(column.key)?.type
      if (type === 'sort') return this.formatSortColumnCell
      if (type === 'target_codes') return ({ cellValue }) => displayCodes(cellValue)
      if (type === 'multi') return ({ cellValue }) => (Array.isArray(cellValue) ? cellValue.join('，') : cellValue ?? '')
      if (type === 'tags' || type === 'users') return ({ cellValue }) => displayTags(cellValue)
      if (type === 'select') return ({ cellValue }) => this.sheetOptionLabel(column.key, cellValue) ?? ''
      return undefined
    },
    /** 单元格显示的值；显示的不是入库值的列（如按别的字段推算）覆写。 */
    sheetCellValue(row, key) {
      return row[key]
    },
    /** 单元格的文字：复制、比较、撤回、键入续写都用它。编辑中的靶点编号和多选是字符串，原样返回。 */
    sheetDirectTextValue(row, key) {
      if (!row) return ''
      const value = this.sheetCellValue(row, key)
      const type = this.workbenchField(key)?.type
      if (type === 'target_codes') {
        return typeof value === 'string' && this.sheetEditRecordFor(row, key) ? value : displayCodes(value)
      }
      if (type === 'multi' && Array.isArray(value)) return value.join('，')
      if (type === 'select') return String(this.sheetOptionLabel(key, value) ?? '')
      return value == null ? '' : String(value)
    },
    sheetPickerDisplayValue(row, column) {
      return column.edit === 'target'
        ? this.sheetTargetDirectValue(row, column.key)
        : this.sheetDirectTextValue(row, column.key)
    },
    // 键入中的靶点编号是字符串，原样返回，避免逗号被规整掉
    sheetTargetDirectValue(row, key) {
      const value = row?.[key]
      if (Array.isArray(value)) return uniqueTargetCodes(value).join(',')
      return value == null ? '' : String(value)
    },
    setSheetTargetDirectValue(row, key, value) {
      row[key] = value
    },
    isSheetCustomColumn() {
      return false
    },
    isSheetChoiceColumn(column) {
      return column?.edit === 'select' || column?.edit === 'multi'
    },
    isSheetMultiColumn(column) {
      return column?.edit === 'multi'
    },
    isSheetCustomPicker() {
      return false
    },
    isSheetPickerCell() {
      return true
    },
    isUserColumn(column) {
      return USER_TYPES.has(this.workbenchField(column?.key)?.type)
    },
    sheetChoiceClearable(column) {
      return !this.workbenchField(column?.key)?.required
    },
    sheetChoiceModelKey(column) {
      return column.key
    },
    /** 双击下拉的可选项，按这一行算（fieldOptions 可随行变化）。 */
    sheetChoiceSelectOptions(column, row) {
      const field = this.workbenchField(column?.key)
      if (!field || !row) return this.sheetChoiceOptionsMap[column?.key] || []
      return this.sheetFieldOptions(field, row).map(choiceOption)
    },
    /** tags 列双击编辑：可选项和这一格里自填的值。 */
    sheetTagOptions(row, column) {
      const field = this.workbenchField(column.key)
      const known = field?.type === 'tags' ? this.sheetFieldOptions(field, row).map(optionValue) : this.sheetFieldOptions(field, row)
      return [...known, ...splitTags(row[column.key]).filter((item) => !known.includes(item))]
    },
    sheetTagValues(row, column) {
      return splitTags(row[column.key])
    },
    onSheetTagsChange(row, column, values) {
      const field = this.workbenchField(column.key)
      row[column.key] = joinTags(field?.type === 'tags' ? this.sheetFieldOptions(field, row) : [], values)
    },
    sheetChoiceDirectValue(row, column) {
      return this.sheetDirectTextValue(row, column.key)
    },
    setSheetChoiceDirectValue(row, column, value) {
      this.setSheetDirectValue(row, column.key, value)
    },
    /** 单元格提交的原始值；同一列编辑态和展示态存在不同字段时覆写。 */
    sheetEditInput(row, key) {
      return row[key]
    },
    assignSheetValue(row, key, text) {
      const result = this.coerceSheetValue(key, text, row)
      if (!result.ok) return result
      this.restoreSheetEditValue(row, key, result.value)
      return { ok: true }
    },
    async finishSheetEdit({ row, column }) {
      const key = column?.field
      if (!key || !row?.id) return
      const editSource = this.sheetEditSource
      this.sheetEditSource = ''
      const record = this.takeSheetEditRecord(row, key)
      const originalValue = record.value
      if (this.isSheetCellLocked(row, key)) {
        this.restoreSheetEditValue(row, key, originalValue)
        return
      }
      if (editSource === 'dblclick' && this.sheetColumnByKey.get(key)?.column?.edit === 'target') {
        if (await this.applySheetTargetPick(row, record.targetCodes, record.targetName)) {
          return this.persistRow(row, 'target_codes')
        }
        return
      }
      const result = this.coerceSheetValue(key, this.sheetEditInput(row, key, editSource), row)
      if (!result.ok) {
        this.restoreSheetEditValue(row, key, originalValue)
        ElMessage.warning(this.sheetValidationMessage(key, result.reason))
        return
      }
      if (this.sameSheetValue(key, result.value, originalValue)) {
        this.restoreSheetEditValue(row, key, originalValue)
        return
      }
      this.restoreSheetEditValue(row, key, result.value)
      if (TARGET_KEYS.includes(key) && !await this.applySheetTargetText(row, key, originalValue)) return
      return this.persistRow(row, key)
    },
    sheetValidationMessage(key, reason) {
      const label = this.sheetColumnLabel(key)
      const custom = this.sheetValidationExtraMessage?.(key, reason, label)
      if (custom) return custom
      if (reason === 'date') return `${label}必须是 YYYY-MM-DD 格式的有效日期`
      if (reason === 'integer') return `${label}必须是 0 或正整数`
      if (reason === 'empty') return `${label}不能为空`
      if (reason === 'length') {
        const maxLen = this.sheetStringMax?.[key]
        return maxLen ? `${label}不能超过 ${maxLen} 个字` : `${label}超出长度限制`
      }
      if (reason === 'locked') return `${label}当前不可编辑`
      if (reason === 'unknown') return '粘贴内容包含无法识别的列'
      return `${label}必须与可选项完全匹配`
    },
    patchExistingListRow(saved, fields) {
      const current = saved?.id && this.list.find((item) => item.id === saved.id)
      if (!current) return
      const queued = this.queuedSaveKeys?.(saved.id) || new Set()
      const keys = fields?.length
        ? (this.savedFieldKeys?.(fields) ?? fields)
        : Object.keys(saved)
      keys.forEach((key) => {
        if (key in saved && !queued.has(key)) current[key] = saved[key]
      })
    },
    cloneSheetValue(value) {
      return value == null ? value : JSON.parse(JSON.stringify(value))
    },
    sameSheetValue(key, left, right) {
      const type = this.workbenchField(key)?.type
      if (type === 'target_codes') return uniqueTargetCodes(left).join(',') === uniqueTargetCodes(right).join(',')
      if (type === 'multi') return listFieldText(left) === listFieldText(right)
      return String(left ?? '').trim() === String(right ?? '').trim()
    },
    /** 开始编辑时的快照：value 用于退回，text 用于记撤回，靶点两列一起记，双击选择器改的是这一对。 */
    createSheetEditOriginal(row, key) {
      return {
        key,
        rowId: row.id,
        targetCodes: this.cloneSheetValue(row.target_codes),
        targetName: row.target_name,
        text: this.sheetCellText(row, key),
        value: this.cloneSheetValue(this.sheetValueSnapshot(row, key)),
      }
    },
    sheetCellText(row, key) {
      return String(this.sheetDirectTextValue(row, key) ?? '').trim()
    },
    async flushExcelKeyboardSwitch() {},
    async flushPendingSheetEdits() {
      await this.sheetKeyboardChain
      await this.sheetEl('table')?.clearEdit?.()
      if (!this.pendingSheetOps.size) return true
      const results = await Promise.allSettled([...this.pendingSheetOps])
      return !results.some((result) => result.status === 'rejected' || result.value === null || result.value === false)
    },
    onSheetPickerVisibleChange({ visible }) {
      if (!visible) this.sheetEl('table')?.clearEdit?.()
    },
    onSheetRangeCleared() {
      if (this.sheetEditOriginal !== null) this.sheetEditOriginal = null
      if (this.sheetEditSource !== '') this.sheetEditSource = ''
      this.sheetBatchEdit = null
    },
    onSheetDblClickCapture(event) {
      if (event.target?.closest?.('input, textarea, .vxe-input, .vxe-select')) return
      const hit = this.hitSheetCell(event.target)
      const row = hit ? this.list[hit.rowIndex] : null
      if (!row || this.notifySheetCellLocked(row, hit.field)) {
        this.sheetEditSource = ''
        return
      }
      this.sheetEditSource = 'dblclick'
      this.beginSheetBatchEdit(hit.rowIndex, hit.colIndex, this.sheetRangeBeforeClick, { fillOnCommit: true })
    },
    /**
     * 在多格选区里开始编辑（双击或键入）：选区收成编辑格所在的列，行不变，多于一行时记下这次批量编辑。
     * 双击开始的，提交就由 finishSheetBatchEdit 填满这几格；键入开始的和 Excel 一样，
     * Enter 只改当前格，Ctrl+Enter 才填满，免得想复制时手滑打字覆盖整列。
     */
    beginSheetBatchEdit(rowIndex, colIndex, range, { fillOnCommit }) {
      this.sheetBatchEdit = null
      const key = this.sheetColumns[colIndex]?.key
      const inside = range && key
        && rowIndex >= range.r1 && rowIndex <= range.r2
        && colIndex >= range.c1 && colIndex <= range.c2
      if (!inside || (range.r1 === range.r2 && range.c1 === range.c2)) return
      this.setSheetRange({ r1: range.r1, c1: colIndex, r2: range.r2, c2: colIndex })
      this.pasteAnchor = { rowIndex, colKey: key }
      const rowIds = this.list.slice(range.r1, range.r2 + 1).map((item) => item.id).filter((id) => id != null)
      if (rowIds.length > 1) this.sheetBatchEdit = { key, rowIds, fillOnCommit }
    },
    takeSheetBatchEdit({ row, column }) {
      const batch = this.sheetBatchEdit
      if (!batch || batch.key !== column?.field || !batch.rowIds.includes(row?.id)) return null
      this.sheetBatchEdit = null
      return batch.fillOnCommit ? batch : null
    },
    focusSheetCellInput(row, key) {
      const input = this.sheetEl('table')
        ?.getCellElement?.(row, key)
        ?.querySelector?.('input:not([type="hidden"]), textarea')
      if (!input) return
      input.focus()
      const end = String(input.value || '').length
      input.setSelectionRange?.(end, end)
    },
    startSheetTextEdit(event, mode, text = '') {
      const rowIndex = this.pasteAnchor?.rowIndex
      const key = this.pasteAnchor?.colKey
      const row = this.list[rowIndex]
      if (!row || !key) return
      if (mode !== 'composition') event.preventDefault()
      event.stopPropagation()
      if (this.notifySheetCellLocked(row, key)) return
      if (!this.sheetEditRecordFor(row, key)) {
        this.beginSheetBatchEdit(rowIndex, this.sheetColumnByKey.get(key)?.index ?? -1, this.normalizedSheetRange(), { fillOnCommit: false })
      }
      const character = text || event.key
      const run = async () => {
        const continuing = Boolean(this.sheetEditRecordFor(row, key))
        if (!continuing && this.sheetEditOriginal) {
          const previousKey = this.sheetEditOriginal.key
          await this.sheetEl('table')?.clearEdit?.()
          await this.flushExcelKeyboardSwitch(previousKey, key)
        }
        if (!continuing) {
          this.sheetEditOriginal = this.createSheetEditOriginal(row, key)
        }
        this.sheetEditSource = 'keyboard'
        if (mode === 'backspace') {
          this.setSheetDirectValue(row, key, this.sheetDirectTextValue(row, key).slice(0, -1))
        } else if (mode === 'character' || mode === 'composition-text') {
          this.setSheetDirectValue(row, key, `${this.sheetDirectTextValue(row, key)}${character}`)
        }
        const $table = this.sheetEl('table')
        const edit = $table?.getEditCell?.()
        const alreadyEditing = Boolean(
          edit
          && edit.column?.field === key
          && (edit.row === row || edit.row?.id === row.id),
        )
        if (!alreadyEditing) {
          await $table?.setEditCell?.(row, key)
          await this.$nextTick()
        }
        if (
          this.list[this.pasteAnchor?.rowIndex]?.id === row.id
          && this.pasteAnchor?.colKey === key
        ) {
          this.focusSheetCellInput(row, key)
        }
      }
      this.sheetKeyboardChain = this.sheetKeyboardChain.then(run, run).catch(() => undefined)
      return this.sheetKeyboardChain
    },
    onSheetCompositionEnd(event) {
      if (event.target?.closest?.('input, textarea, .vxe-input, .vxe-select')) {
        return
      }
      const text = String(event.data || '')
      if (text) this.startSheetTextEdit(event, 'composition-text', text)
    },
    onSheetKeydownCapture(event) {
      const editor = event.target?.closest?.(
        'input, textarea, .vxe-input, .vxe-select',
      )
      const withCtrl = event.ctrlKey || event.metaKey
      if (editor) {
        // Ctrl+Enter 提交并填满批量编辑的选区
        if (withCtrl && event.key === 'Enter') {
          event.preventDefault()
          event.stopPropagation()
          if (this.sheetBatchEdit) this.sheetBatchEdit.fillOnCommit = true
          this.sheetEl('table')?.clearEdit?.()
        }
        return
      }
      if (withCtrl && !event.shiftKey && String(event.key).toLowerCase() === 'z') {
        event.preventDefault()
        event.stopPropagation()
        this.undoSheetEdit()
        return
      }
      if (event.key === 'Delete') {
        if (!this.sheetRange) return
        event.preventDefault()
        event.stopPropagation()
        this.clearSelectedSheetCells()
        return
      }
      if (event.key === 'Backspace' && !withCtrl && !event.altKey) {
        event.preventDefault()
        this.startSheetTextEdit(event, 'backspace')
        return
      }
      if (withCtrl && String(event.key).toLowerCase() === 'a') {
        event.preventDefault()
        this.selectAllSheetCells()
        return
      }
      const isComposition = event.key === 'Process' || event.keyCode === 229
      const isCharacter = String(event.key || '').length === 1
      if (withCtrl || event.altKey || (!isCharacter && !isComposition)) return
      this.startSheetTextEdit(event, isComposition ? 'composition' : 'character')
    },
    /** Delete 清空选区：不可编辑的格子跳过，其余和粘贴一样整批校验、一次提交。 */
    async clearSelectedSheetCells() {
      if (!this.canEdit) return
      const range = this.normalizedSheetRange()
      if (!range || !await this.flushPendingSheetEdits()) return
      const cells = []
      for (let rowIndex = range.r1; rowIndex <= range.r2; rowIndex += 1) {
        for (let colIndex = range.c1; colIndex <= range.c2; colIndex += 1) {
          const key = this.sheetColumns[colIndex]?.key
          if (key && !this.isExcelRowSelectField(key)) cells.push({ rowIndex, key, text: '' })
        }
      }
      await this.saveSheetCells(cells, { action: '清空', skipLocked: true })
    },
    onSheetEditActived({ row, column }) {
      const key = column?.field
      if (!key) return
      if (this.sheetEditSource === 'keyboard' && this.sheetEditRecordFor(row, key)) return
      this.sheetEditOriginal = this.createSheetEditOriginal(row, key)
      if (this.sheetEditSource === 'dblclick') this.openSheetEditorPanel(row, key)
    },
    async loadAllUserOptions() {
      try {
        this.allUserOptions = await loadAllUserNames()
      } catch {
        this.allUserOptions = []
        ElMessage.warning('人员名单加载失败，人员列暂时无法选择或粘贴，请刷新页面重试')
      }
    },
    /**
     * 粘贴的公共开头：判断是否接管、识别表头、单个值填满选区、截掉超出列表的行。
     * 返回 null 表示不处理。limitRows 可传函数 (headerKeys, hasHeader) => boolean，
     * 返回 false 时不截行，由页面自己定位行（如按单号匹配）。
     */
    async prepareSheetPaste(event, labelToKey, { limitRows = true } = {}) {
      if (!this.canEdit) return null
      if (event.target?.closest?.('input, textarea')) return null
      const plain = event.clipboardData?.getData('text/plain') || ''
      const grid = readClipboardGrid(event.clipboardData)
      if (!grid.length) return null
      const singleValue = grid.length === 1
        && grid[0].length === 1
        && !String(grid[0][0]).includes('\n')
      if (!plain.includes('\t') && !plain.includes('\n') && singleValue && !this.sheetRange) return null
      event.preventDefault()
      if (!await this.flushPendingSheetEdits()) return null

      const headerKeys = grid[0].map((cell) => labelToKey.get(String(cell || '').trim()) || null)
      const nonEmptyHeaderCount = grid[0].filter((cell) => String(cell || '').trim()).length
      const matchedHeaderCount = headerKeys.filter(Boolean).length
      const hasHeader = matchedHeaderCount >= 2 && matchedHeaderCount === nonEmptyHeaderCount
      let dataRows = hasHeader ? grid.slice(1) : grid
      let startIndex = this.pasteAnchor?.rowIndex ?? 0
      const startColKey = this.pasteAnchor?.colKey || this.sheetColumns[0]?.key
      let startColIndex = this.sheetColumns.findIndex((column) => column.key === startColKey)
      if (startColIndex < 0) return null
      const selectedRange = this.normalizedSheetRange()
      const fillSelectedRange = !hasHeader
        && dataRows.length === 1
        && dataRows[0]?.length === 1
        && selectedRange
        && (selectedRange.r1 !== selectedRange.r2 || selectedRange.c1 !== selectedRange.c2)
      if (fillSelectedRange) {
        const value = dataRows[0][0]
        const rowCount = selectedRange.r2 - selectedRange.r1 + 1
        const columnCount = selectedRange.c2 - selectedRange.c1 + 1
        dataRows = Array.from({ length: rowCount }, () => Array(columnCount).fill(value))
        startIndex = selectedRange.r1
        startColIndex = selectedRange.c1
      }
      const limit = typeof limitRows === 'function' ? limitRows(headerKeys, hasHeader) : limitRows
      let skippedRowCount = 0
      if (limit) {
        const availableRowCount = Math.max(this.list.length - startIndex, 0)
        skippedRowCount = Math.max(dataRows.length - availableRowCount, 0)
        dataRows.splice(availableRowCount)
      }
      if (!dataRows.length) {
        ElMessage.warning('粘贴区域超出当前列表，本次未保存')
        return null
      }
      return { dataRows, hasHeader, headerKeys, skippedRowCount, startColIndex, startIndex }
    },
    /** 粘贴可识别的全部列：workbenchSheet.columns（列随类型变化的页面也是所有类型的列，带表头粘贴时才认得出）。 */
    sheetPasteColumns() {
      return this.$options.workbenchSheet?.columns || this.sheetColumns
    },
    /** 表头别名：workbenchSheet.aliases，{ 旧表头文字: 列键 }。 */
    sheetPasteAliases() {
      return this.$options.workbenchSheet?.aliases || {}
    },
    /** 带表头粘贴且含这一列时，按它的值找行，不再从选中位置往下排。 */
    sheetPasteIdentityKey() {
      return ''
    },
    /** 锁定格贴了不同的值时的原因，交给 sheetPasteInvalidMessage。 */
    sheetPasteLockedReason() {
      return 'locked'
    },
    sheetPasteInvalidMessage(invalid, count) {
      if (invalid.reason === 'identity') return '粘贴内容包含当前页不存在或重复的单号'
      if (invalid.reason === 'unknown') return '粘贴内容包含无法识别的列'
      if (!invalid.key) return `有 ${count} 个单元格不可编辑`
      const label = this.sheetColumnLabel(invalid.key)
      if (invalid.reason === 'locked') return `「${label}」当前不可编辑`
      return this.sheetValidationMessage(invalid.key, invalid.reason)
    },
    /** 同一行需要一起提交的字段，比如改质检结果时带上质检人。直接往 fields 里加。 */
    expandSheetPasteFields() {},
    /** 一行这些字段要提交的值：靶点编号和名称成对提交，空串存空值。页面要另行组装时覆写。 */
    rowPayload(row, fields) {
      const keys = new Set(fields)
      if (TARGET_KEYS.some((key) => keys.has(key)) && TARGET_KEYS.every((key) => this.workbenchField(key))) {
        TARGET_KEYS.forEach((key) => keys.add(key))
      }
      const payload = { id: row.id }
      keys.forEach((key) => {
        if (key === 'target_codes') payload[key] = uniqueTargetCodes(row[key])
        else payload[key] = row[key] === '' ? null : (row[key] ?? null)
      })
      return payload
    },
    /**
     * 保存请求体：rowPayload 的值，有入库基线时再把这些键的旧值放进 _expected，
     * 后端锁行后比对，别人先改过就拒绝保存，不会悄悄覆盖。
     */
    rowSavePayload(row, fields) {
      const payload = this.rowPayload(row, fields)
      const baseline = row?.id != null ? this.rowBaselines?.get(row.id) : null
      if (baseline) {
        payload._expected = Object.fromEntries(
          Object.keys(payload)
            .filter((key) => key !== 'id' && key in baseline)
            .map((key) => [key, baseline[key] ?? null]),
        )
      }
      return payload
    },
    /** entries 为 [{ row, fields, payload }]，提交后返回 { items: 保存后的行 }，返回空值表示取消；默认调 workbenchApi.saveBatch。 */
    async saveSheetPasteItems(entries) {
      return this.$options.workbenchApi.saveBatch({ items: entries.map(({ payload }) => payload) })
    },
    applySheetPasteSaved(saved, fields) {
      if (this.applySavedFields) this.applySavedFields(saved, fields)
      else this.patchExistingListRow(saved, fields)
    },
    sheetPasteErrorMessages() {
      return this.$options.workbenchApi?.errors?.save || { default: '表格保存失败' }
    },
    sameSheetPasteText(row, key, cell) {
      return String(cell ?? '').trim() === String(this.sheetDirectTextValue(row, key) ?? '').trim()
    },
    /** 粘贴：识别表头、按单号找行、单个值填满选区，转成单元格列表交给 saveSheetCells。 */
    async onSheetPaste(event) {
      const identityKey = this.sheetPasteIdentityKey()
      const pasteColumns = this.sheetPasteColumns()
      const labelToKey = new Map([
        ...Object.entries(this.sheetPasteAliases()),
        ...pasteColumns.map((column) => [column.label, column.key]),
      ])
      const paste = await this.prepareSheetPaste(event, labelToKey, {
        limitRows: (keys, header) => !(identityKey && header && keys.includes(identityKey)),
      })
      if (!paste) return
      const { dataRows, hasHeader, headerKeys, skippedRowCount, startColIndex, startIndex } = paste
      const identityIndex = identityKey && hasHeader ? headerKeys.indexOf(identityKey) : -1
      const rowIndexByIdentity = identityIndex >= 0
        ? new Map(this.list.map((row, index) => [String(row[identityKey] ?? '').trim(), index]))
        : null
      const matchedIdentities = new Set()
      const cells = []
      let invalid = null
      dataRows.forEach((rowCells, offset) => {
        if (invalid || rowCells.every((cell) => String(cell ?? '') === '')) return
        let rowIndex = startIndex + offset
        if (rowIndexByIdentity) {
          const identity = String(rowCells[identityIndex] ?? '').trim()
          const matchedIndex = rowIndexByIdentity.get(identity)
          if (!identity || matchedIndex === undefined || matchedIdentities.has(identity)) {
            invalid = { reason: 'identity' }
            return
          }
          matchedIdentities.add(identity)
          rowIndex = matchedIndex
        }
        const row = this.list[rowIndex]
        if (!row) return
        const multiCell = rowCells.length > 1 || hasHeader
        rowCells.forEach((text, cellIndex) => {
          const key = hasHeader ? headerKeys[cellIndex] : this.sheetColumns[startColIndex + cellIndex]?.key
          if (!key) {
            if (String(text ?? '').trim()) invalid ||= { reason: 'unknown' }
            return
          }
          // 整行贴入时排序列跟着别的列过来，空的或改不了就忽略，不拦整次粘贴
          if (
            this.isExcelRowSelectField(key) && multiCell
            && !this.sameSheetPasteText(row, key, text)
            && (this.isSheetCellLocked(row, key) || !String(text ?? '').trim())
          ) return
          cells.push({ rowIndex, key, text })
        })
      })
      if (invalid) {
        ElMessage.warning(`${this.sheetPasteInvalidMessage(invalid, 1)}，本次粘贴未保存`)
        return
      }
      await this.saveSheetCells(cells, {
        action: '粘贴',
        hint: skippedRowCount ? `，已忽略超出的 ${skippedRowCount} 行` : '',
      })
    },
    /**
     * 多格保存：粘贴、批量编辑、清空、撤回共用。cells 为 [{ rowIndex, key, text }]，text 是表格显示的文字。
     * 先在副本上逐格校验，有一格不合格整次不保存；和当前显示相同的格子不提交；只读列跳过；
     * 锁定格改了值默认拦下整次保存，skipLocked 时跳过；靶点统一解析；一次批量提交后刷新列表，并记一步撤回。
     * action 用在提示里（「已粘贴并保存」「本次粘贴未保存」）；校验或保存失败返回 false，已保存或没有要改的返回 true。
     */
    async saveSheetCells(cells, { action, skipLocked = false, record = true, hint = '' }) {
      if (this.awaitRowSaves && !await this.awaitRowSaves()) return false
      const readonlyKeys = new Set(
        this.sheetPasteColumns().filter((column) => column.edit === 'readonly').map((column) => column.key),
      )
      const workingRows = this.list.map((row) => this.cloneSheetValue(row))
      const dirtyByIndex = new Map()
      const unchangedTargetKeys = new Map()
      const invalidCells = []
      const touchedCells = []
      const changes = []
      let readonlySkipped = 0
      let lockedSkipped = 0
      cells.forEach(({ rowIndex, key, text }) => {
        const row = workingRows[rowIndex]
        if (!row) return
        if (this.sameSheetPasteText(row, key, text)) {
          touchedCells.push({ rowId: row.id, key })
          if (TARGET_KEYS.includes(key)) {
            unchangedTargetKeys.set(rowIndex, new Set([...(unchangedTargetKeys.get(rowIndex) || []), key]))
          }
          return
        }
        if (readonlyKeys.has(key)) {
          readonlySkipped += 1
          return
        }
        if (this.isSheetCellLocked(row, key)) {
          if (skipLocked) lockedSkipped += 1
          else invalidCells.push({ key, reason: this.sheetPasteLockedReason(row, key) })
          return
        }
        const before = this.sheetCellText(row, key)
        const result = this.assignSheetValue(row, key, text)
        if (result.skipped) return
        if (!result.ok) {
          invalidCells.push({ ...result, key })
          return
        }
        touchedCells.push({ rowId: row.id, key })
        changes.push({ rowId: row.id, key, before })
        const fields = dirtyByIndex.get(rowIndex) || new Set()
        fields.add(key)
        dirtyByIndex.set(rowIndex, fields)
      })
      if (invalidCells.length) {
        ElMessage.warning(`${this.sheetPasteInvalidMessage(invalidCells[0], invalidCells.length)}，本次${action}未保存`)
        return false
      }
      const skippedHint = [
        readonlySkipped ? `，只读列的 ${readonlySkipped} 格不能在表格里修改，已忽略` : '',
        lockedSkipped ? `，${lockedSkipped} 格当前不可编辑，已跳过` : '',
        hint,
      ].join('')
      if (!dirtyByIndex.size) {
        if (touchedCells.length || readonlySkipped || lockedSkipped) {
          await this.selectTouchedSheetCells(touchedCells)
          ElMessage.info(`没有需要保存的改动${skippedHint}`)
        }
        return true
      }
      // 靶点编号和名称同一行都有时，没变的那一列也参与核对，免得新编号配旧名称被静默改名
      dirtyByIndex.forEach((fields, rowIndex) => {
        if (TARGET_KEYS.some((key) => fields.has(key))) {
          unchangedTargetKeys.get(rowIndex)?.forEach((key) => fields.add(key))
        }
      })
      const entries = [...dirtyByIndex.entries()].map(([rowIndex, fields]) => ({ fields, row: workingRows[rowIndex] }))
      const targetEntries = entries.filter(({ fields }) => TARGET_KEYS.some((key) => fields.has(key)))
      if (targetEntries.length && this.resolveSheetTargets) {
        const error = await this.resolveSheetTargets(targetEntries)
        if (error) {
          ElMessage.warning(`${error}，本次${action}未保存`)
          return false
        }
        targetEntries.forEach(({ fields }) => TARGET_KEYS.forEach((key) => fields.add(key)))
      }
      entries.forEach((entry) => {
        this.expandSheetPasteFields(entry.row, entry.fields)
        entry.payload = this.rowSavePayload(entry.row, [...entry.fields])
      })
      try {
        const result = await this.saveSheetPasteItems(entries)
        if (!result) return false
        const fieldsById = new Map(entries.map(({ row, fields }) => [row.id, [...fields]]))
        ;(result.items || []).forEach((saved) => this.applySheetPasteSaved(saved, fieldsById.get(saved?.id)))
        await this.getList({ flushEditor: false, silent: true })
        await this.selectTouchedSheetCells(touchedCells)
        if (record) this.recordSheetUndo(changes)
        const savedCount = result.items?.length ?? entries.length
        ElMessage.success(`已${action}并保存 ${savedCount} 行${skippedHint}`)
        return true
      } catch (error) {
        await this.getList({ flushEditor: false, silent: true })
        notifyApiError(error, { messages: this.sheetPasteErrorMessages() })
        return false
      }
    },
    async selectTouchedSheetCells(touchedCells) {
      const cells = touchedCells
        .map(({ rowId, key }) => ({
          rowIndex: this.list.findIndex((row) => row.id === rowId),
          colIndex: this.sheetColumnByKey.get(key)?.index ?? -1,
        }))
        .filter(({ rowIndex, colIndex }) => rowIndex >= 0 && colIndex >= 0)
      if (!cells.length) return
      const rowIndexes = cells.map((cell) => cell.rowIndex)
      const colIndexes = cells.map((cell) => cell.colIndex)
      const range = {
        r1: Math.min(...rowIndexes),
        c1: Math.min(...colIndexes),
        r2: Math.max(...rowIndexes),
        c2: Math.max(...colIndexes),
      }
      await this.$nextTick()
      const activeRow = this.list[range.r1]
      const activeColumn = this.sheetColumns[range.c1]
      if (activeRow && activeColumn) {
        await this.sheetEl('table')?.setSelectCell?.(activeRow, activeColumn.key)
      }
      this.setSheetRange(range)
    },
    sheetSelectEditor() {
      return this.sheetEl('selectEditor') || null
    },
    onSheetSelectVisible(visible) {
      if (visible) return
      this.$nextTick(() => {
        if (this.sheetSelectEditor()?.isOpen()) return
        this.sheetEl('table')?.clearEdit?.()
      })
    },
    openSheetEditorPanel(row, key) {
      const open = () => {
        const select = this.sheetSelectEditor()
        if (select) {
          select.open()
          return true
        }
        // VxeSelect 和日期 VxeInput 在输入框获得焦点时弹出面板；已有焦点时先失焦才会再触发
        const cell = this.sheetEl('table')?.getCellElement?.(row, key)
        const input = cell?.querySelector?.('.vxe-select input, .vxe-input.type--date input')
        if (!input) return false
        if (document.activeElement === input) input.blur()
        input.focus()
        return true
      }
      this.$nextTick(() => {
        if (!open()) this.$nextTick(open)
      })
    },
    /** 这一格的编辑快照，不取走；不是这一格的返回 null。 */
    /** 下拉面板挂在 body 上，在里面按键不经过表格外层，所以 Esc 在 document 捕获阶段按编辑状态处理。 */
    onSheetDocumentKeydown(event) {
      if (event.key === 'Escape' && this.sheetEditOriginal) this.cancelSheetEdit()
    },
    /** Esc：编辑格退回编辑前的值，表格随后关闭编辑时看到没改就不保存，也不填满选区。 */
    cancelSheetEdit() {
      this.sheetBatchEdit = null
      const record = this.sheetEditOriginal
      const row = record && this.list.find((item) => item.id === record.rowId)
      if (!row) return
      this.restoreSheetEditValue(row, record.key, record.value)
      if (TARGET_KEYS.includes(record.key)) {
        row.target_codes = this.cloneSheetValue(record.targetCodes)
        row.target_name = record.targetName
      }
    },
    sheetEditRecordFor(row, key) {
      const record = this.sheetEditOriginal
      return record?.rowId === row?.id && record?.key === key ? record : null
    },
    /** 取走这一格的编辑快照；没有快照（如 vxe 直接删值）时按基线补一份，text 为 null。 */
    takeSheetEditRecord(row, key) {
      const record = this.sheetEditRecordFor(row, key)
      this.sheetEditOriginal = null
      if (record) return { ...record, value: this.cloneSheetValue(record.value) }
      const baseline = this.rowBaselines?.get(row.id) || {}
      return {
        targetCodes: this.cloneSheetValue(baseline.target_codes ?? []),
        targetName: baseline.target_name ?? '',
        text: null,
        value: this.cloneSheetValue(this.sheetValueSnapshot(baseline, key)),
      }
    },
    async restoreSheetSelectedCell() {
      const $table = this.sheetEl('table')
      if (!$table || $table.getEditCell?.()) return
      const row = this.list[this.pasteAnchor?.rowIndex]
      const key = this.pasteAnchor?.colKey
      if (!row || !key) return
      const selected = $table.getSelectedCell?.()
      if (!selected || selected.row !== row || selected.column?.field !== key) {
        await $table.setSelectCell?.(row, key)
      }
      if ($table.getEditCell?.()) return
      const activeElement = document.activeElement
      const wrap = this.sheetEl('wrap')
      if (
        !activeElement
        || activeElement === document.body
        || wrap?.contains?.(activeElement)
        || activeElement.closest?.('.sheet-picker-popup')
      ) {
        this.focusSheetWrap()
      }
    },
    onSheetEditClosed(context) {
      const batch = this.takeSheetBatchEdit(context)
      const operation = batch ? this.finishSheetBatchEdit(context, batch) : this.finishSheetEditWithUndo(context)
      this.pendingSheetOps.add(operation)
      this.$nextTick(() => this.restoreSheetSelectedCell())
      return operation.finally(() => this.pendingSheetOps.delete(operation))
    },
    async finishSheetEditWithUndo(context) {
      const { row, column } = context
      const before = this.sheetEditRecordFor(row, column?.field)?.text
      const result = await this.finishSheetEdit(context)
      if (before != null) this.recordSheetUndo([{ rowId: row.id, key: column.field, before }])
      return result
    },
    /**
     * 批量编辑提交：编辑格先按单格规则转成显示文字，再退回原值，整列选区交给 saveSheetCells 统一校验保存。
     * 双击靶点列时选择器已把编号和名称写好，直接取显示文字，名称和编号由 saveSheetCells 统一解析。
     */
    async finishSheetBatchEdit({ row }, { key, rowIds }) {
      const editSource = this.sheetEditSource
      this.sheetEditSource = ''
      const record = this.takeSheetEditRecord(row, key)
      const pickedTarget = editSource === 'dblclick' && this.sheetColumnByKey.get(key)?.column?.edit === 'target'
      const result = pickedTarget ? { ok: true } : this.assignSheetValue(row, key, this.sheetEditInput(row, key, editSource))
      const text = result.ok ? this.sheetCellText(row, key) : ''
      this.restoreSheetEditValue(row, key, record.value)
      if (TARGET_KEYS.includes(key)) {
        row.target_codes = this.cloneSheetValue(record.targetCodes)
        row.target_name = record.targetName
      }
      if (!result.ok) {
        ElMessage.warning(this.sheetValidationMessage(key, result.reason))
        return false
      }
      if (text === record.text) return true
      const cells = rowIds
        .map((id) => ({ rowIndex: this.sheetRowIndexById.get(String(id)) ?? -1, key, text }))
        .filter((cell) => cell.rowIndex >= 0)
      return this.saveSheetCells(cells, { action: '批量修改', skipLocked: true })
    },
    /** 记一步撤回：changes 为 [{ rowId, key, before }]，保存后读当前显示文字作 after，没变的格子不记。 */
    recordSheetUndo(changes) {
      const recorded = changes.flatMap((change) => {
        const row = this.list[this.sheetRowIndexById.get(String(change.rowId)) ?? -1]
        if (!row) return []
        const after = this.sheetCellText(row, change.key)
        return after === change.before ? [] : [{ ...change, after }]
      })
      if (!recorded.length) return
      this.sheetUndoStack.push({ at: Date.now(), changes: recorded })
      if (this.sheetUndoStack.length > SHEET_UNDO_LIMIT) this.sheetUndoStack.shift()
    },
    /** 当前页里还保持着 after 的格子才撤回；之后又改过或已不在当前页的跳过。 */
    collectSheetUndoCells(entry) {
      return entry.changes.flatMap((change) => {
        const rowIndex = this.sheetRowIndexById.get(String(change.rowId)) ?? -1
        const row = this.list[rowIndex]
        return row && this.sheetCellText(row, change.key) === change.after ? [{ ...change, rowIndex }] : []
      })
    },
    /**
     * Ctrl+Z：撤回最近一步表格修改（单格编辑、粘贴、批量编辑、清空）。只保留 10 分钟内、最多 20 步，
     * 确认框列出要恢复的内容，确认后按原文字重新保存。撤回本身不再记撤回。
     */
    async undoSheetEdit() {
      if (!this.canEdit || this.sheetUndoBusy) return
      this.sheetUndoBusy = true
      try {
        await this.runSheetUndo()
      } finally {
        this.sheetUndoBusy = false
      }
    },
    async runSheetUndo() {
      if (!await this.flushPendingSheetEdits()) return
      const now = Date.now()
      this.sheetUndoStack = this.sheetUndoStack.filter((entry) => now - entry.at <= SHEET_UNDO_TTL_MS)
      const entry = this.sheetUndoStack.pop()
      if (!entry) {
        ElMessage.info('没有可撤回的表格修改（只能撤回 10 分钟内的修改）')
        return
      }
      const preview = this.collectSheetUndoCells(entry)
      if (!preview.length) {
        if (!entry.changes.some((change) => this.sheetRowIndexById.has(String(change.rowId)))) {
          this.sheetUndoStack.push(entry)
          ElMessage.info('上一步改的行不在当前页，回到那一页再撤回')
          return
        }
        ElMessage.info('上一步改过的单元格之后又改过，无法撤回')
        return
      }
      try {
        await ElMessageBox.confirm(this.sheetUndoSummary(entry, preview), '撤回表格修改', {
          confirmButtonText: '撤回',
          cancelButtonText: '取消',
          type: 'warning',
        })
      } catch {
        this.sheetUndoStack.push(entry)
        return
      }
      const cells = this.collectSheetUndoCells(entry)
        .map(({ rowIndex, key, before }) => ({ rowIndex, key, text: before }))
      if (!await this.saveSheetCells(cells, { action: '撤回', skipLocked: true, record: false })) {
        this.sheetUndoStack.push(entry)
      }
    },
    sheetUndoSummary(entry, cells) {
      const minutes = Math.floor((Date.now() - entry.at) / 60000)
      const shorten = (text) => (text.length > 24 ? `${text.slice(0, 24)}…` : text) || '（空）'
      const lines = cells.slice(0, SHEET_UNDO_PREVIEW).map(({ rowIndex, key, before, after }) => (
        `第 ${rowIndex + 1} 行「${this.sheetColumnLabel(key)}」：${shorten(after)} → ${shorten(before)}`
      ))
      const skipped = entry.changes.length - cells.length
      return h('div', [
        h('p', `撤回${minutes < 1 ? '刚才' : ` ${minutes} 分钟前`}的修改，共 ${cells.length} 格：`),
        ...lines.map((line) => h('p', line)),
        cells.length > SHEET_UNDO_PREVIEW ? h('p', `……另有 ${cells.length - SHEET_UNDO_PREVIEW} 格`) : null,
        skipped ? h('p', `另有 ${skipped} 格之后又改过或不在当前页，不撤回`) : null,
      ])
    },
  },
}
