import { ElMessage } from 'element-plus'

import { getTiterPriorityTone } from '#/utils/serumProjectStatus'
import { uniqueNames } from '#/utils/userOptions'

import { cleanFieldValue, joinTags, multiValues, splitTags } from './fieldSchema'
import { syncTextareaHeights } from './textareaHeights'

const DRAWER_KEEP_OPEN_SELECTOR = [
  '.el-drawer',
  '.el-popper',
  '.el-select-dropdown',
  '.el-picker-panel',
  '.el-message-box',
  '.el-overlay-message-box',
  '.el-overlay-dialog',
  '.sheet-picker-popup',
  '.line-suggest',
  // 重新登录等 vben 弹窗及其遮罩
  '[role="dialog"]',
  '[data-dismissable-modal]',
].join(', ')
const DRAWER_ROW_SELECTOR = '.el-table__row, .vxe-body--row, .action-cell, .sort-column-cell, .sort-cell'
const ROW_CLICK_IGNORE_SELECTOR = [
  '.el-button',
  '.el-input',
  '.el-select',
  '.el-date-editor',
  '.action-cell',
  '.sort-column-cell',
  '.sort-cell',
  '.workbench-status-tag',
  '.wb-color-mark-btn',
].join(', ')
const DATE_TEXT_RE = /^\d{4}-\d{2}-\d{2}$/
const TARGET_KEYS = ['target_codes', 'target_name']
const DRAWER_FIELD_KINDS = {
  date: 'date',
  target: 'target',
  target_codes: 'codes',
  user: 'user',
  users: 'users',
  select: 'select',
  multi: 'multi',
  tags: 'tags',
  textarea: 'textarea',
}
const TAG_KINDS = new Set(['tags', 'users'])

/**
 * 工作台抽屉：点行打开，编辑行的副本 editingRow，字段 @change / @blur 时调 persistRow(editingRow, key) 逐字段保存。
 * 同一行的保存按顺序排队；关闭、切换行、做操作、刷新列表前 flushDrawer 兜底：失焦、把副本里还没存的字段补存。
 * 约定见 docs/modules/workbench.md。
 *
 * 依赖 workbenchExcelMixin 的 patchExistingListRow、flushPendingSheetEdits。
 * 页面需提供：list、editorSections（[{ fields: [{ key, type }] }]）、
 * saveRowField(row, field, options)：真正保存一个字段，开头调 normalizeDrawerValue，失败返回 null；成功后调 applySavedFields(saved, fields)。
 * 可覆写：drawerComparable（字段比较值）、savedFieldKeys（保存后要回填的联动字段）、drawerValueKeys（一个字段占用的值键）、
 * onDrawerRowSynced（副本被覆盖后同步页面自己的草稿状态）、onDrawerOpened（点开一行之后）、
 * releaseDrawerRow（切走前处理未入库的草稿）。
 * WorkbenchDrawer 给每个字段套 .drawer-field[data-field-key]，兜底时靠它认出正在输入的日期；自己写抽屉也要带上。
 *
 * 标准字段控件 <WorkbenchDrawerField v-bind="drawerFieldBind(field)" />：按字段 type 选控件（date / target / target_codes /
 * user / users / select / multi / tags / textarea / number，其余为单行文本），改完即调 persistRow；
 * multi 存按可选项排序的数组，tags / users 存顿号连接的文字。
 * 选项默认走 workbenchExcelMixin 的 fieldOptions(field, row)；人员候选再并入这一格现有的人。
 * 可覆写：drawerFieldOptions、drawerUserOptions、drawerSelectClass（下拉配色类）、drawerSelectProps（clearable / filterable / allowCreate）、
 * drawerFieldValue（显示值）、isDrawerFieldDisabled（默认看 canEditField，没有则看 canEdit）、onDrawerFieldChange。
 */
export default {
  data() {
    return {
      drawerVisible: false,
      editingId: null,
      editingRow: null,
      rowBaselines: new Map(),
      rowSaveChains: new Map(),
      rowQueuedKeys: new Map(),
    }
  },
  computed: {
    editingIndex() {
      return this.list.findIndex((row) => row.id === this.editingId)
    },
    hasPrevEditor() {
      return this.editingIndex > 0
    },
    hasNextEditor() {
      return this.editingIndex >= 0 && this.editingIndex < this.list.length - 1
    },
    drawerFieldDefs() {
      return (this.editorSections || []).flatMap((section) => section.fields || [])
    },
  },
  watch: {
    drawerVisible(open) {
      if (open) {
        this.syncDrawerTextareas()
        return
      }
      if (this.editingRow) this.closeDrawer()
    },
    editingId() {
      if (this.drawerVisible) this.syncDrawerTextareas()
    },
  },
  mounted() {
    if (import.meta.env.DEV && !Array.isArray(this.editorSections)) {
      console.warn(`[workbenchDrawerMixin] ${this.$options.name} 没有提供 editorSections，抽屉兜底补存不会生效`)
    }
    if (import.meta.env.DEV && typeof this.saveRowField !== 'function') {
      console.warn(`[workbenchDrawerMixin] ${this.$options.name} 没有实现 saveRowField，字段改完不会保存`)
    }
    document.addEventListener('mousedown', this.onDocumentPointerDown, true)
  },
  beforeUnmount() {
    document.removeEventListener('mousedown', this.onDocumentPointerDown, true)
  },
  activated() {
    document.addEventListener('mousedown', this.onDocumentPointerDown, true)
  },
  deactivated() {
    this.closeDrawer()
    document.removeEventListener('mousedown', this.onDocumentPointerDown, true)
  },
  methods: {
    updateRowBaseline(row) {
      if (!row?.id) return
      this.rowBaselines.set(row.id, JSON.parse(JSON.stringify(row)))
    },
    savedFieldKeys(fields) {
      return new Set(fields)
    },
    /**
     * saveRowField 开头调：按字段整理要存的值（文字见 cleanFieldValue），整数、排序按表格同一规则校验。
     * 不合法时退回入库值并提示，返回 false，调用方就此不存。
     */
    normalizeDrawerValue(row, key) {
      const field = this.workbenchField(key)
      row[key] = cleanFieldValue(field, row[key])
      if (field?.type !== 'int' && field?.type !== 'sort') return true
      const result = this.coerceSheetValue(key, row[key], row)
      if (result.ok) {
        row[key] = result.value
        return true
      }
      row[key] = this.rowBaselines.get(row.id)?.[key] ?? null
      ElMessage.warning(this.sheetValidationMessage(key, result.reason))
      return false
    },
    drawerComparable(key, row) {
      const value = row?.[key]
      if (value == null) return ''
      return typeof value === 'object' ? JSON.stringify(value) : String(value)
    },
    /** 这些字段都和入库基线相同（没改过，不用存）。 */
    rowFieldsUnchanged(row, fields) {
      const baseline = this.rowBaselines.get(row?.id)
      return Boolean(baseline) && fields.every((key) => this.drawerComparable(key, row) === this.drawerComparable(key, baseline))
    },
    /** 副本里与入库值不同的字段，只看抽屉上可编辑的字段。 */
    drawerDirtyFields(row = this.editingRow) {
      const baseline = this.rowBaselines.get(row?.id)
      if (!row || !baseline) return []
      const keys = new Set(this.drawerFieldDefs.map((field) => field.key))
      return [...keys].filter((key) => (
        key in baseline
        && (typeof this.canEditField !== 'function' || this.canEditField(row, key))
        && this.drawerComparable(key, row) !== this.drawerComparable(key, baseline)
      ))
    },
    /** 一个抽屉字段实际占用的值键：靶点同时写编号和名称，页面可再补自己的成对字段。 */
    drawerValueKeys(key) {
      return TARGET_KEYS.includes(key) ? TARGET_KEYS : [key]
    },
    onDrawerRowSynced() {},
    onDrawerOpened() {},
    releaseDrawerRow() {},
    /** WorkbenchDrawerField 的全部属性和事件。 */
    drawerFieldBind(field) {
      const row = this.editingRow
      const kind = this.drawerFieldKind(field, row)
      const options = this.drawerKindOptions(kind, field, row)
      return {
        field,
        kind,
        value: this.drawerKindValue(kind, field, row),
        disabled: this.isDrawerFieldDisabled(field, row),
        options,
        selectClass: kind === 'select' ? this.drawerSelectClassFor(field, row) : '',
        ...(kind === 'select' ? this.drawerSelectProps(field, row) : {}),
        targetName: row?.target_name || '',
        onInput: (value) => {
          row[field.key] = value
          if (field.sync) this.syncDrawerTextareas()
        },
        onChange: (value) => this.onDrawerFieldChange(row, field, this.drawerChangeValue(kind, options, value)),
        onBlur: () => this.persistRow(row, field.key),
        onTargetChange: (payload) => this.onDrawerTargetChange(row, payload),
      }
    },
    drawerFieldKind(field, row) {
      if (field.key === 'sort_order' && this.isQueueTerminalRow?.(row)) return 'dash'
      return DRAWER_FIELD_KINDS[field.type] || (field.sync ? 'textarea' : 'text')
    },
    drawerKindValue(kind, field, row) {
      if (kind === 'target' || kind === 'codes') return row?.target_codes
      if (TAG_KINDS.has(kind)) return splitTags(this.drawerFieldValue(field, row))
      return this.drawerFieldValue(field, row)
    },
    /** 控件给出的值换成要存的值：multi 按可选项顺序的数组，tags / users 顿号连接的文字。 */
    drawerChangeValue(kind, options, value) {
      if (kind === 'multi') return multiValues(options, value)
      if (TAG_KINDS.has(kind)) return joinTags(kind === 'tags' ? options : [], value)
      return value
    },
    drawerKindOptions(kind, field, row) {
      if (kind === 'select' || kind === 'multi' || kind === 'tags') return this.drawerFieldOptions(field, row)
      if (kind === 'user' || kind === 'users') return this.drawerUserOptions(field, row)
      return []
    },
    drawerFieldValue(field, row) {
      return row?.[field.key]
    },
    isDrawerFieldDisabled(field, row) {
      return typeof this.canEditField === 'function' ? !this.canEditField(row, field.key) : !this.canEdit
    },
    drawerFieldOptions(field, row) {
      const schema = this.workbenchField?.(field.key)
      return schema ? this.fieldOptions(schema, row) : field.options || []
    },
    drawerUserOptions(field, row) {
      const schema = this.workbenchField?.(field.key)
      return uniqueNames([...(schema ? this.fieldOptions(schema, row) : []), ...splitTags(row?.[field.key])])
    },
    /** 优先级按档位上色，其余下拉的配色由页面 drawerSelectClass 给。 */
    drawerSelectClassFor(field, row) {
      if (field.key === 'priority') return `priority-select status-tone-${getTiterPriorityTone(row?.priority)}`
      return this.drawerSelectClass(field, row)
    },
    drawerSelectClass() {
      return ''
    },
    drawerSelectProps(field) {
      return {
        clearable: field.clearable !== false,
        // 下拉默认可搜索；字段显式 filterable:false 时关掉（如是/否）。
        filterable: field.filterable !== false,
        allowCreate: Boolean(field.allowCreate),
      }
    },
    onDrawerFieldChange(row, field, value) {
      if (this.isDrawerFieldDisabled(field, row)) return
      return this.persistRowValue(row, field.key, value)
    },
    /** 控件给出新值（列表里的优先级、状态等）：写回行再保存。 */
    persistRowValue(row, key, value) {
      row[key] = value
      return this.persistRow(row, key)
    },
    /** 保存回来的值写回列表行、抽屉副本和基线；副本里还没存的字段不覆盖。 */
    applySavedFields(saved, fields) {
      if (!saved?.id) return
      this.patchExistingListRow(saved, fields)
      if (this.editingId === saved.id && this.editingRow) {
        const dirty = new Set(this.drawerDirtyFields().flatMap((key) => this.drawerValueKeys(key)))
        const keys = fields?.length ? this.savedFieldKeys(fields) : Object.keys(saved)
        keys.forEach((key) => {
          if (key === 'id' || !(key in saved) || dirty.has(key)) return
          this.editingRow[key] = saved[key] == null ? saved[key] : JSON.parse(JSON.stringify(saved[key]))
        })
        this.onDrawerRowSynced(this.editingRow)
      }
      this.updateRowBaseline(saved)
    },
    /**
     * 逐字段保存的唯一入口：同一行排队执行，避免后发先至覆盖新值。
     * 排队期间这些键记在 rowQueuedKeys，前一次保存的回包不回填它们，否则排在后面的新值会被旧回包盖掉、再被当成没改过跳过。
     */
    persistRow(row, field, options) {
      if (!row?.id) return this.saveRowField(row, field, options)
      const rowId = row.id
      const keys = this.drawerValueKeys(field)
      this.countQueuedKeys(rowId, keys, 1)
      const previous = this.rowSaveChains.get(rowId) || Promise.resolve()
      const task = previous.then(() => {
        this.countQueuedKeys(rowId, keys, -1)
        return this.saveRowField(row, field, options)
      })
      const chain = task.catch(() => null)
      this.rowSaveChains.set(rowId, chain)
      chain.then(() => {
        if (this.rowSaveChains.get(rowId) === chain) this.rowSaveChains.delete(rowId)
      })
      return task
    },
    countQueuedKeys(rowId, keys, delta) {
      const counts = this.rowQueuedKeys.get(rowId) || new Map()
      keys.forEach((key) => {
        const next = (counts.get(key) || 0) + delta
        if (next > 0) counts.set(key, next)
        else counts.delete(key)
      })
      if (counts.size) this.rowQueuedKeys.set(rowId, counts)
      else this.rowQueuedKeys.delete(rowId)
    },
    /** 这一行还排着队、没开始保存的值键；patchExistingListRow 不回填它们。 */
    queuedSaveKeys(rowId) {
      return new Set(this.rowQueuedKeys.get(rowId)?.keys() || [])
    },
    /** 等所有行的保存完成；有一次失败返回 false。 */
    async awaitRowSaves(rowId) {
      const chains = rowId == null ? [...this.rowSaveChains.values()] : [this.rowSaveChains.get(rowId)].filter(Boolean)
      if (!chains.length) return true
      const results = await Promise.all(chains)
      return !results.includes(null)
    },
    /** 日期框手输的文字不一定触发 change，失焦前先读进副本。 */
    takeTypedDrawerDate() {
      const active = document.activeElement
      if (!(active instanceof HTMLInputElement) || !this.editingRow) return
      const key = active.closest('.drawer-field[data-field-key]')?.getAttribute('data-field-key')
      const field = this.drawerFieldDefs.find((item) => item.key === key)
      if (field?.type !== 'date') return
      const value = active.value.trim()
      if (!value || DATE_TEXT_RE.test(value)) this.editingRow[key] = value || null
    },
    /**
     * 兜底补存：失焦让正在输入的字段走自己的保存，再补存副本里其余没存的字段，最后等这一行保存完。
     * 同步部分在返回前做完，调用方可以立即换掉 editingRow。
     */
    flushDrawer() {
      const row = this.editingRow
      if (!row?.id) return Promise.resolve(true)
      this.takeTypedDrawerDate()
      const active = document.activeElement
      if (active instanceof HTMLElement && active.closest('.el-drawer')) active.blur()
      const dirty = this.drawerDirtyFields(row)
      const targetDirty = dirty.some((key) => TARGET_KEYS.includes(key))
      dirty
        .filter((key) => key !== 'target_name' || !dirty.includes('target_codes'))
        .forEach((key) => this.persistRow(row, targetDirty && key === 'target_name' ? 'target_codes' : key))
      return this.awaitRowSaves(row.id)
    },
    /** 操作某一行前：表格里的编辑和这一行的抽屉都先存完，失败返回 false。 */
    async flushEditorForAction(row) {
      if (this.flushPendingSheetEdits && !await this.flushPendingSheetEdits()) return false
      if (row?.id && this.editingId === row.id) return this.flushDrawer()
      return this.awaitRowSaves(row?.id)
    },
    /** 刷新列表前：所有编辑存完，失败返回 false。 */
    async flushAllEdits() {
      if (this.flushPendingSheetEdits && !await this.flushPendingSheetEdits()) return false
      const drawerSaved = await this.flushDrawer()
      return await this.awaitRowSaves() && drawerSaved
    },
    /** 保存失败、列表已刷新后：抽屉副本里这几个字段退回入库值，免得兜底补存再提交一次。 */
    revertDrawerFields(rowId, fields) {
      if (this.editingId !== rowId || !this.editingRow) return
      const fresh = this.list.find((row) => row.id === rowId) || this.rowBaselines.get(rowId)
      if (!fresh) return
      fields.flatMap((key) => this.drawerValueKeys(key)).forEach((key) => {
        if (key in fresh) this.editingRow[key] = fresh[key] == null ? fresh[key] : JSON.parse(JSON.stringify(fresh[key]))
      })
      this.onDrawerRowSynced(this.editingRow)
    },
    /** 列表刷新后调用：抽屉副本里没改过的字段换成新数据，再把新数据记为基线；这一行不在新列表里就关掉抽屉。 */
    acceptListRows() {
      const selected = this.editingRow && this.editingId != null
        ? this.list.find((row) => row.id === this.editingId)
        : null
      if (this.editingRow && this.editingId != null && !selected) {
        this.closeDrawer()
      } else if (selected) {
        const dirty = new Set(this.drawerDirtyFields().flatMap((key) => this.drawerValueKeys(key)))
        Object.keys(selected).forEach((key) => {
          if (key === 'id' || dirty.has(key)) return
          this.editingRow[key] = selected[key] == null ? selected[key] : JSON.parse(JSON.stringify(selected[key]))
        })
        this.onDrawerRowSynced(this.editingRow)
      }
      this.list.forEach((row) => this.updateRowBaseline(row))
    },
    openDrawer(row) {
      if (!row?.id) return
      if (this.drawerVisible && this.editingId === row.id) {
        this.closeDrawer()
        return
      }
      this.releaseDrawerRow()
      this.flushDrawer()
      this.editingId = row.id
      this.editingRow = JSON.parse(JSON.stringify(row))
      if (!this.rowBaselines.has(row.id)) this.updateRowBaseline(this.editingRow)
      this.onDrawerRowSynced(this.editingRow)
      this.drawerVisible = true
      this.onDrawerOpened(this.editingRow)
    },
    closeDrawer() {
      this.releaseDrawerRow()
      const saving = this.flushDrawer()
      this.editingId = null
      this.editingRow = null
      this.drawerVisible = false
      return saving
    },
    /** 行已删除时关闭抽屉，不再补存。 */
    discardDrawer(rowId) {
      if (rowId != null && this.editingId !== rowId) return
      this.editingId = null
      this.editingRow = null
      this.drawerVisible = false
    },
    shiftEditor(delta) {
      const next = this.list[this.editingIndex + delta]
      if (next) this.openDrawer(next)
    },
    workbenchRowClassName({ row }) {
      return row.id === this.editingId ? 'is-editing' : ''
    },
    onWorkbenchRowClick(row, _column, event) {
      if (event?.target?.closest?.(ROW_CLICK_IGNORE_SELECTOR)) return
      this.openDrawer(row)
    },
    onWorkbenchRowContextMenu(_row, _column, event) {
      if (!this.drawerVisible) return
      event?.preventDefault?.()
      event?.stopPropagation?.()
      this.closeDrawer()
    },
    onDocumentPointerDown(event) {
      if (!this.drawerVisible) return
      const target = event.target
      if (!(target instanceof Element)) return
      if (target.closest(DRAWER_KEEP_OPEN_SELECTOR) || target.closest(DRAWER_ROW_SELECTOR)) return
      this.closeDrawer()
    },
    /** 等高文本框（.drawer-field.is-synced）对齐到内容最高的那个。 */
    syncDrawerTextareas() {
      this.$nextTick(() => syncTextareaHeights('.workbench-drawer .drawer-field.is-synced textarea'))
    },
  },
}
