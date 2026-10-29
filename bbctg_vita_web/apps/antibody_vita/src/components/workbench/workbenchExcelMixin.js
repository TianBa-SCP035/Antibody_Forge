import { clipboardCell } from './clipboardGrid'

const SHEET_ROW_CONFIG = Object.freeze({ keyField: 'id', isHover: true })
const SHEET_CELL_CONFIG = Object.freeze({ height: 48 })
const SHEET_COLUMN_CONFIG = Object.freeze({ resizable: true })
const SHEET_MOUSE_CONFIG = Object.freeze({ selected: true })
const SHEET_KEYBOARD_CONFIG = Object.freeze({
  isArrow: true,
  isDel: true,
  isEnter: true,
  isTab: true,
  isShift: true,
  isEdit: false,
  isClip: false,
})
const SHEET_VIRTUAL_Y_CONFIG = Object.freeze({
  enabled: true,
  gt: 40,
  oSize: 10,
  immediate: true,
})
const SHEET_VIRTUAL_X_CONFIG = Object.freeze({
  enabled: true,
  gt: 18,
  oSize: 6,
  immediate: true,
})
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

/**
 * Excel 划选 / 键入 / 列序。约定见 docs/modules/workbench.md。
 * 页面需提供：list, sheetColumns, canEdit, persistSheetColumnOrder, finishSheetEdit。
 * 键入默认 row[key] = 文本；有双字段或展示转换时再覆写 sheetDirectTextValue。
 * 单格保存必须 patchExistingListRow，禁止 splice 换行对象。
 * 数字格普通输入，提交时由本页 coerceSheetValue 校验。
 * 行选择列用 excelRowSelectKey（默认 sort_order）。
 * 钉住的列用 sheetPinFirstKey / sheetPinLastKey，Shift 不能拖。默认钉住序号。
 */
export default {
  data() {
    return {
      excelRowSelectKey: 'sort_order',
      sheetPinFirstKey: 'sort_order',
      sheetPinLastKey: '',
      pasteAnchor: null,
      pendingSheetOps: new Set(),
      sheetRange: null,
      sheetEditOriginal: null,
      sheetEditSource: '',
      sheetKeyboardChain: Promise.resolve(),
      sheetDragMode: '',
      sheetPointerDown: false,
      sheetColumnMove: null,
      sortEditingId: null,
      sortInputRefs: {},
      sortable: null,
      sortableInitToken: 0,
      sheetRowConfig: SHEET_ROW_CONFIG,
      sheetCellConfig: SHEET_CELL_CONFIG,
      sheetColumnConfig: SHEET_COLUMN_CONFIG,
      sheetMouseConfig: SHEET_MOUSE_CONFIG,
      sheetVirtualYConfig: SHEET_VIRTUAL_Y_CONFIG,
      sheetVirtualXConfig: SHEET_VIRTUAL_X_CONFIG,
      sheetCustomEditRender: SHEET_CUSTOM_EDIT_RENDER,
      sheetTargetPopupConfig: SHEET_TARGET_POPUP_CONFIG,
      sheetChoicePopupConfig: SHEET_CHOICE_POPUP_CONFIG,
      sheetCatalogPopupConfig: SHEET_CATALOG_POPUP_CONFIG,
    }
  },
  computed: {
    isExcelMode() {
      return this.viewMode === 'excel'
    },
    sheetColumnOrderKey() {
      return this.sheetColumns.map((column) => column.key).join(',')
    },
    sheetRowIndexById() {
      const map = new Map()
      const rows = this.list || []
      for (let i = 0; i < rows.length; i += 1) {
        const row = rows[i]
        if (row?.id != null) map.set(String(row.id), i)
      }
      return map
    },
    sheetColumnByKey() {
      const map = new Map()
      const columns = this.sheetColumns || []
      for (let i = 0; i < columns.length; i += 1) {
        const column = columns[i]
        if (column?.key) map.set(column.key, { column, index: i })
      }
      return map
    },
    isQueueSorted() {
      return this.listQuery?.sort_field === 'sort_order'
    },
    sortColumnLabel() {
      return this.isQueueSorted ? '排序' : '序号'
    },
    sortHeaderTitle() {
      return this.isQueueSorted
        ? '当前按队列序，显示排序值。再点恢复最新在前'
        : '当前显示本页行号，按最新在前。点按队列序排列'
    },
    queuedRowCount() {
      return this.list.filter((row) => !this.isQueueTerminalRow?.(row)).length
    },
    canDragRows() {
      const allowed = this.canFullEdit ?? this.canEdit
      return Boolean(
        allowed
        && this.viewMode === 'workbench'
        && this.isQueueSorted
        && this.queuedRowCount > 1
      )
    },
    sheetKeyboardConfig() {
      return SHEET_KEYBOARD_CONFIG
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
    viewMode() {
      this.clearSheetRange()
    },
  },
  mounted() {
    this.onWindowMouseUp = () => this.finishSheetPointer()
    window.addEventListener('mouseup', this.onWindowMouseUp)
  },
  beforeUnmount() {
    this.destroySortable()
    if (this._sheetRangeRafId) {
      cancelAnimationFrame(this._sheetRangeRafId)
      this._sheetRangeRafId = 0
    }
    if (this.onWindowMouseUp) {
      window.removeEventListener('mouseup', this.onWindowMouseUp)
    }
    window.removeEventListener('mousemove', this.onSheetColumnPointerMove)
  },
  activated() {
    if (this.onWindowMouseUp) {
      window.addEventListener('mouseup', this.onWindowMouseUp)
    }
  },
  deactivated() {
    this.destroySortable()
    if (this._sheetRangeRafId) {
      cancelAnimationFrame(this._sheetRangeRafId)
      this._sheetRangeRafId = 0
    }
    if (this.onWindowMouseUp) {
      window.removeEventListener('mouseup', this.onWindowMouseUp)
    }
    window.removeEventListener('mousemove', this.onSheetColumnPointerMove)
  },
  methods: {
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
    isExcelRowSelectField(field) {
      return field === this.excelRowSelectKey
    },
    isSheetColumnPinned(column) {
      const key = column?.key
      if (!key) return false
      return key === this.sheetPinFirstKey || key === this.sheetPinLastKey
    },
    isSheetCellLocked(row, key) {
      if (!this.canEdit) return true
      if (this.isExcelRowSelectField(key) && (!this.isQueueSorted || this.isQueueTerminalRow?.(row))) return true
      const column = this.sheetColumnByKey.get(key)?.column
      return column?.edit === 'readonly'
    },
    canEditSortCell(row) {
      if (!this.isQueueSorted || this.isQueueTerminalRow?.(row)) return false
      if (typeof this.canEditField === 'function') return this.canEditField(row, 'sort_order')
      return Boolean(this.canEdit)
    },
    getSheetRowIndex(rowOrId) {
      if (rowOrId == null) return -1
      const id = typeof rowOrId === 'object' ? rowOrId.id : rowOrId
      if (id == null) return -1
      const idx = this.sheetRowIndexById.get(String(id))
      return idx === undefined ? -1 : idx
    },
    getSheetColIndexByColId(colid) {
      if (!colid) return undefined
      const column = this.$refs.sheetTable?.getColumnById?.(colid)
      const field = column?.field
      return field ? this.sheetColumnByKey.get(field)?.index : undefined
    },
    formatSortColumnCell({ row, rowIndex, $rowIndex }) {
      const idx = Number.isInteger(rowIndex) && rowIndex >= 0 ? rowIndex : $rowIndex
      return this.formatSortColumn(row, idx)
    },
    formatSortColumn(row, index) {
      if (!this.isQueueSorted) {
        const i = Number.isInteger(index) && index >= 0 ? index : this.getSheetRowIndex(row)
        return i >= 0 ? String(i + 1) : ''
      }
      const n = Number(row?.sort_order)
      return Number.isInteger(n) && n > 0 ? String(n) : '-'
    },
    toggleQueueSort() {
      if (this.listQuery && 'sort_dir' in this.listQuery) {
        this.listQuery.sort_dir = ''
      }
      this.listQuery.sort_field = this.isQueueSorted ? '' : 'sort_order'
      this.listQuery.page = 1
      this.getList()
    },
    isDateEmptyFiltered(field) {
      return Boolean(field && this.listQuery?.empty_date === field)
    },
    dateSortMark(field) {
      const sortMark = this.listQuery?.sort_field === field
        ? (this.listQuery?.sort_dir === 'desc' ? ' ↓' : ' ↑')
        : ''
      const emptyMark = this.isDateEmptyFiltered(field) ? ' ∅' : ''
      return `${sortMark}${emptyMark}`
    },
    dateSortTitle(field) {
      const col =
        this.sheetColumnByKey?.get(field)?.column
        || this.workbenchColumns?.find?.((c) => c.key === field)
      const label = col?.label || '日期'
      let sortHint = `左键按${label}从早到晚`
      if (this.listQuery?.sort_field === field) {
        sortHint = this.listQuery?.sort_dir === 'asc'
          ? '当前从早到晚，左键改为从晚到早'
          : '当前从晚到早，左键恢复最新在前'
      }
      const emptyHint = this.isDateEmptyFiltered(field)
        ? `当前只看未填${label}，右键取消`
        : `右键只看未填${label}`
      return `${sortHint}；${emptyHint}`
    },
    cycleDateSort(field) {
      if (!this.listQuery) return
      if (this.listQuery.sort_field === field && this.listQuery.sort_dir === 'asc') {
        this.listQuery.sort_dir = 'desc'
      } else if (this.listQuery.sort_field === field && this.listQuery.sort_dir === 'desc') {
        this.listQuery.sort_field = ''
        this.listQuery.sort_dir = ''
      } else {
        this.listQuery.sort_field = field
        this.listQuery.sort_dir = 'asc'
      }
      this.listQuery.page = 1
      this.getList()
    },
    toggleEmptyDate(field) {
      if (!this.listQuery || !field) return
      this.listQuery.empty_date = this.listQuery.empty_date === field ? '' : field
      this.listQuery.page = 1
      this.getList()
    },
    async revealCreatedRow(saved) {
      if (!saved?.id) return saved
      const limit = Math.max(1, Number(this.listQuery.limit) || 20)
      if (!this.isQueueSorted) {
        this.listQuery.page = 1
      } else {
        const n = Number(saved.sort_order)
        this.listQuery.page = Number.isInteger(n) && n > 0 ? Math.ceil(n / limit) : 1
      }
      await this.getList()
      const row = this.list.find((item) => item.id === saved.id) || saved
      if (this.viewMode === 'workbench') this.openEditor(row)
      this.$nextTick(() => {
        this.$refs.workbenchTable?.$el
          ?.querySelector('.el-table__row.is-editing')
          ?.scrollIntoView?.({ block: 'nearest' })
      })
      return row
    },
    sheetColumnTitle(column) {
      if (this.isExcelRowSelectField(column?.key)) return this.sortColumnLabel
      return `${column?.label || ''}${this.dateSortMark?.(column?.key) || ''}`
    },
    queueReorderPayload(oldIndex, newIndex) {
      const moved = this.list[oldIndex]
      const target = this.list[newIndex]
      if (!moved || !target || moved.id === target.id) return null
      if (this.isQueueTerminalRow?.(moved) || this.isQueueTerminalRow?.(target)) return null
      return { movedId: moved.id, targetId: target.id }
    },
    bindSortInput(id, el) {
      if (el) this.sortInputRefs[id] = el
      else delete this.sortInputRefs[id]
    },
    startSortEdit(row) {
      if (!this.canEditSortCell(row) || !row?.id) return
      this.sortEditingId = row.id
      this.$nextTick(() => {
        const input = this.sortInputRefs[row.id]
        input?.focus?.()
        const native = input?.input || input?.$el?.querySelector?.('input')
        native?.select?.()
      })
    },
    finishSortEdit(row) {
      if (this.sortEditingId !== row.id) return
      this.sortEditingId = null
      this.persistRow?.(row, 'sort_order')
    },
    workbenchTbody() {
      return this.$refs.workbenchTable?.$el?.querySelector('.el-table__body-wrapper tbody')
    },
    dataRowEls(tbody) {
      return [...(tbody?.children || [])].filter((tr) => tr.classList?.contains('el-table__row'))
    },
    scheduleSortable() {
      this.$nextTick(() => this.initSortable())
    },
    async initSortable() {
      const initToken = ++this.sortableInitToken
      if (this.viewMode !== 'workbench' || !this.canDragRows) {
        this.destroySortable()
        return
      }
      await this.$nextTick()
      const tbody = this.workbenchTbody()
      if (!tbody || initToken !== this.sortableInitToken || !tbody.isConnected) return
      if (this.sortable?.el === tbody) return
      this.destroySortable()
      const Sortable = (await import('sortablejs')).default
      if (initToken !== this.sortableInitToken || !tbody.isConnected) return
      this.sortable = Sortable.create(tbody, {
        animation: 180,
        handle: '.sort-column-cell',
        draggable: 'tr.el-table__row',
        ghostClass: 'wb-sortable-ghost',
        onEnd: (event) => this.handleDragEnd?.(event),
      })
    },
    destroySortable() {
      this.sortable?.destroy?.()
      this.sortable = null
    },
    revertDrag(item, oldIndex, newIndex) {
      const parent = item?.parentNode
      if (!parent || oldIndex == null || newIndex == null || oldIndex === newIndex) return
      const dataRows = this.dataRowEls(parent)
      const anchor = newIndex > oldIndex ? dataRows[oldIndex] : dataRows[oldIndex + 1]
      parent.insertBefore(item, anchor || null)
    },
    setSheetDirectValue(row, key, text) {
      row[key] = text
    },
    sheetDirectTextValue(row, key) {
      if (!row) return ''
      if (row[key] === null || row[key] === undefined) return ''
      return String(row[key])
    },
    sheetValueSnapshot(row, key) {
      return row?.[key]
    },
    patchExistingListRow(saved, fields) {
      if (!saved?.id) return { current: null, normalized: saved }
      const normalized = this.normalizeRow(saved)
      const current = this.list.find((item) => item.id === saved.id)
      if (current) {
        const keys = fields?.length
          ? (this.savedFieldKeys?.(fields) ?? fields)
          : null
        if (keys) {
          keys.forEach((key) => {
            if (key in normalized) current[key] = normalized[key]
          })
        } else {
          Object.assign(current, normalized)
        }
      }
      return { current, normalized }
    },
    cloneSheetValue(value) {
      return value == null ? value : JSON.parse(JSON.stringify(value))
    },
    sameSheetValue(_key, left, right) {
      return String(left ?? '').trim() === String(right ?? '').trim()
    },
    createSheetEditOriginal(row, key) {
      return {
        key,
        rowId: row.id,
        value: this.cloneSheetValue(this.sheetValueSnapshot(row, key)),
      }
    },
    async flushExcelKeyboardSwitch() {},
    persistSheetColumnOrder() {},
    async flushPendingSheetEdits() {
      await this.sheetKeyboardChain
      await this.$refs.sheetTable?.clearEdit?.()
      if (!this.pendingSheetOps.size) return true
      const results = await Promise.allSettled([...this.pendingSheetOps])
      return !results.some((result) => result.status === 'rejected' || result.value === null)
    },
    onSheetPickerVisibleChange({ visible }) {
      if (!visible) this.$refs.sheetTable?.clearEdit?.()
    },
    normalizedSheetRange() {
      if (!this.sheetRange) return null
      const { r1, c1, r2, c2 } = this.sheetRange
      return {
        r1: Math.min(r1, r2),
        c1: Math.min(c1, c2),
        r2: Math.max(r1, r2),
        c2: Math.max(c1, c2),
      }
    },
    sheetHeaderCellClassName({ column }) {
      if (!column.field) return ''
      const empty = this.isDateEmptyFiltered?.(column.field) ? ' is-empty-date-filtered' : ''
      const sorted = !empty && this.dateSortMark?.(column.field) ? ' is-date-sorted' : ''
      return `sheet-selectable-header${empty}${sorted}`
    },
    sheetCellClassName() {
      return ''
    },
    paintSheetColumnMove(event) {
      const wrap = this.$refs.sheetWrap
      const stage = this.$refs.sheetTableStage
      const line = this.$refs.sheetColumnDropLine
      const ghost = this.$refs.sheetColumnGhost
      const $table = this.$refs.sheetTable
      const move = this.sheetDragMode === 'move-column' ? this.sheetColumnMove : null
      wrap?.querySelectorAll('.is-column-from').forEach((el) => el.classList.remove('is-column-from'))
      if (!move || !wrap || !stage || !line || !ghost || !$table?.getColumnByField) {
        if (line) line.style.display = 'none'
        if (ghost) ghost.style.display = 'none'
        return
      }
      const fromId = $table.getColumnByField(this.sheetColumns[move.from]?.key)?.id
      if (fromId) {
        wrap.querySelectorAll(`[colid="${fromId}"]`).forEach((el) => el.classList.add('is-column-from'))
      }
      const stageRect = stage.getBoundingClientRect()
      if (event) {
        ghost.textContent = this.sheetColumnTitle(this.sheetColumns[move.from])
        ghost.style.display = 'block'
        ghost.style.transform = `translate3d(${event.clientX - stageRect.left + 12}px, ${event.clientY - stageRect.top + 16}px, 0)`
      }
      const toId = $table.getColumnByField(this.sheetColumns[move.to]?.key)?.id
      const header = toId
        && [...wrap.querySelectorAll(`.vxe-header--column[colid="${toId}"]`)]
          .find((el) => el.getBoundingClientRect().width > 2)
      if (!header || move.from === move.to) {
        line.style.display = 'none'
        return
      }
      const rect = header.getBoundingClientRect()
      const top = Math.max(rect.top, stageRect.top) - stageRect.top
      line.style.display = 'block'
      line.style.height = `${stageRect.height - top}px`
      line.style.transform = `translate3d(${(move.to > move.from ? rect.right : rect.left) - stageRect.left}px, ${top}px, 0)`
    },
    hitSheetColumnByX(clientX) {
      const wrap = this.$refs.sheetWrap
      const $table = this.$refs.sheetTable
      if (!wrap || !$table?.getColumnById) return null
      const byIndex = new Map()
      for (const el of wrap.querySelectorAll('.vxe-header--column')) {
        const column = $table.getColumnById(el.getAttribute('colid'))
        const field = column?.field
        const colIndex = field ? (this.sheetColumnByKey.get(field)?.index ?? -1) : -1
        const rect = el.getBoundingClientRect()
        if (colIndex < 0 || rect.width <= 2) continue
        const prev = byIndex.get(colIndex)
        if (!prev || rect.width > prev.rect.width) {
          byIndex.set(colIndex, { colIndex, field, rect })
        }
      }
      const headers = [...byIndex.values()].sort((a, b) => a.rect.left - b.rect.left)
      if (!headers.length) return null
      let nearest = headers[0]
      let best = Infinity
      for (const item of headers) {
        if (clientX >= item.rect.left && clientX <= item.rect.right) return item
        const dist = clientX < item.rect.left
          ? item.rect.left - clientX
          : clientX - item.rect.right
        if (dist < best) {
          best = dist
          nearest = item
        }
      }
      return nearest
    },
    onSheetColumnPointerMove(event) {
      if (this.sheetDragMode !== 'move-column' || !this.sheetColumnMove) return
      event.preventDefault()
      const hit = this.hitSheetColumnByX(event.clientX)
      if (hit && !this.isSheetColumnPinned(this.sheetColumns[hit.colIndex])) {
        this.sheetColumnMove.to = hit.colIndex
      }
      this.paintSheetColumnMove(event)
    },
    finishSheetPointer() {
      const move = this.sheetDragMode === 'move-column' ? this.sheetColumnMove : null
      window.removeEventListener('mousemove', this.onSheetColumnPointerMove)
      this._sheetPointerDown = false
      this._sheetSelectDragMode = ''
      if (this.sheetPointerDown) this.sheetPointerDown = false
      if (this.sheetDragMode) this.sheetDragMode = ''
      if (this.sheetColumnMove) this.sheetColumnMove = null
      if (move) this.paintSheetColumnMove()
      if (!move || move.from === move.to) return
      if (this.isSheetColumnPinned(this.sheetColumns[move.from]) || this.isSheetColumnPinned(this.sheetColumns[move.to])) return
      const next = [...this.sheetColumns]
      const [column] = next.splice(move.from, 1)
      if (!column) return
      next.splice(move.to, 0, column)
      this.sheetColumns = next
      this.persistSheetColumnOrder?.(next)
      this.clearSheetRange()
    },
    syncPasteAnchorFromRange() {
      if (!this.sheetRange) return
      const column = this.sheetColumns[this.sheetRange.c1]
      if (!column) return
      const prev = this.pasteAnchor
      if (prev && prev.rowIndex === this.sheetRange.r1 && prev.colKey === column.key) return
      this.pasteAnchor = { rowIndex: this.sheetRange.r1, colKey: column.key }
    },
    scheduleSheetRangePaint() {
      if (this._sheetRangeRafId) return
      this._sheetRangeRafId = requestAnimationFrame(() => {
        this._sheetRangeRafId = 0
        this.syncSheetRangeOverlay()
      })
    },
    setSheetRange(next) {
      const prev = this.sheetRange
      if (
        prev
        && next
        && prev.r1 === next.r1
        && prev.c1 === next.c1
        && prev.r2 === next.r2
        && prev.c2 === next.c2
      ) {
        return
      }
      this.sheetRange = next
      this.syncPasteAnchorFromRange()
      this.scheduleSheetRangePaint()
    },
    clearSheetRange() {
      window.removeEventListener('mousemove', this.onSheetColumnPointerMove)
      this._sheetPointerDown = false
      this._sheetSelectDragMode = ''
      if (this.sheetRange !== null) this.sheetRange = null
      if (this.sheetEditOriginal !== null) this.sheetEditOriginal = null
      if (this.sheetEditSource !== '') this.sheetEditSource = ''
      if (this.sheetDragMode !== '') this.sheetDragMode = ''
      if (this.sheetPointerDown !== false) this.sheetPointerDown = false
      if (this.sheetColumnMove !== null) this.sheetColumnMove = null
      if (this.pasteAnchor !== null) this.pasteAnchor = null
      this.paintSheetColumnMove()
      this.$refs.sheetTable?.clearSelected?.()
      this.scheduleSheetRangePaint()
    },
    paintSheetRange() {
      this.syncSheetRangeOverlay()
    },
    syncSheetRangeOverlay() {
      const wrap = this.$refs.sheetWrap
      const overlay = this.$refs.sheetRangeOverlay
      const $table = this.$refs.sheetTable
      const range = this.normalizedSheetRange()
      if (!wrap || !overlay || !$table || !range) {
        if (overlay) overlay.style.display = 'none'
        return
      }
      const bodyWrapper = wrap.querySelector('.vxe-table--main-wrapper .vxe-table--body-wrapper')
        || wrap.querySelector('.vxe-table--body-wrapper')
      const tbody = bodyWrapper?.querySelector('tbody')
      const stage = this.$refs.sheetTableStage
      if (!bodyWrapper || !tbody || !stage) {
        overlay.style.display = 'none'
        return
      }
      const rowIndexById = this.sheetRowIndexById
      const activeRow = this.pasteAnchor?.rowIndex
      const activeColumn = this.sheetColumnByKey.get(this.pasteAnchor?.colKey)?.index ?? -1
      let topTr = null
      let bottomTr = null
      let activeTr = null
      let topRow = Number.POSITIVE_INFINITY
      let bottomRow = Number.NEGATIVE_INFINITY
      for (const tr of tbody.children) {
        const rowid = tr.getAttribute('rowid')
        if (!rowid) continue
        const r = rowIndexById.get(String(rowid))
        if (r == null) continue
        if (r === activeRow) activeTr = tr
        if (r < range.r1 || r > range.r2) continue
        if (r < topRow) {
          topRow = r
          topTr = tr
        }
        if (r > bottomRow) {
          bottomRow = r
          bottomTr = tr
        }
      }
      if (!topTr || !bottomTr) {
        overlay.style.display = 'none'
        return
      }
      let leftTd = null
      let rightTd = null
      let leftCol = Number.POSITIVE_INFINITY
      let rightCol = Number.NEGATIVE_INFINITY
      for (const td of topTr.children) {
        const c = this.getSheetColIndexByColId(td.getAttribute('colid'))
        if (c == null || c < range.c1 || c > range.c2) continue
        if (c < leftCol) {
          leftCol = c
          leftTd = td
        }
        if (c > rightCol) {
          rightCol = c
          rightTd = td
        }
      }
      if (!leftTd || !rightTd) {
        overlay.style.display = 'none'
        return
      }
      const stageRect = stage.getBoundingClientRect()
      const bodyRect = bodyWrapper.getBoundingClientRect()
      let clipLeft = bodyRect.left
      let clipRight = bodyRect.right
      const clipTop = bodyRect.top
      const clipBottom = bodyRect.bottom
      const fixedLeft = wrap.querySelector('.vxe-table--fixed-left-wrapper')
      if (fixedLeft) {
        const flRect = fixedLeft.getBoundingClientRect()
        if (flRect.width > 1) clipLeft = Math.max(clipLeft, flRect.right)
      }
      const fixedRight = wrap.querySelector('.vxe-table--fixed-right-wrapper')
      if (fixedRight) {
        const frRect = fixedRight.getBoundingClientRect()
        if (frRect.width > 1) clipRight = Math.min(clipRight, frRect.left)
      }
      const topRect = topTr.getBoundingClientRect()
      const bottomRect = bottomTr.getBoundingClientRect()
      const leftRect = leftTd.getBoundingClientRect()
      const rightRect = rightTd.getBoundingClientRect()
      const rowH = topRect.height || 48
      const colW = leftRect.width || 120
      const rawTop = topRow > range.r1 ? topRect.top - (topRow - range.r1) * rowH : topRect.top
      const rawBottom = bottomRow < range.r2 ? bottomRect.bottom + (range.r2 - bottomRow) * rowH : bottomRect.bottom
      let rawLeft = leftRect.left
      for (let c = range.c1; c < leftCol; c += 1) {
        const colObj = $table.getColumnByField?.(this.sheetColumns[c]?.key)
        rawLeft -= colObj?.renderWidth || colW
      }
      let rawRight = rightRect.right
      for (let c = rightCol + 1; c <= range.c2; c += 1) {
        const colObj = $table.getColumnByField?.(this.sheetColumns[c]?.key)
        rawRight += colObj?.renderWidth || colW
      }
      const left = Math.max(rawLeft, clipLeft)
      const top = Math.max(rawTop, clipTop)
      const right = Math.min(rawRight, clipRight)
      const bottom = Math.min(rawBottom, clipBottom)
      if (right <= left || bottom <= top) {
        overlay.style.display = 'none'
        return
      }
      const isSingleCell = range.r1 === range.r2 && range.c1 === range.c2
      overlay.classList.toggle('is-single-cell', isSingleCell)
      overlay.classList.toggle('is-bottom-clipped', rawBottom > clipBottom + 1)
      overlay.classList.toggle('is-right-clipped', rawRight > clipRight + 1)
      if (!isSingleCell && activeTr && activeColumn >= range.c1 && activeColumn <= range.c2) {
        let activeTd = null
        for (const td of activeTr.children) {
          if (this.getSheetColIndexByColId(td.getAttribute('colid')) === activeColumn) {
            activeTd = td
            break
          }
        }
        const aRect = activeTd?.getBoundingClientRect()
        if (aRect && aRect.right > left && aRect.left < right && aRect.bottom > top && aRect.top < bottom) {
          const x1 = Math.max(0, Math.round(aRect.left - left))
          const y1 = Math.max(0, Math.round(aRect.top - top))
          const x2 = Math.max(x1, Math.round(aRect.right - left))
          const y2 = Math.max(y1, Math.round(aRect.bottom - top))
          overlay.style.setProperty(
            '--sheet-hole-clip',
            `polygon(0px 0px, 100% 0px, 100% 100%, 0px 100%, 0px 0px, ${x1}px ${y1}px, ${x1}px ${y2}px, ${x2}px ${y2}px, ${x2}px ${y1}px, ${x1}px ${y1}px, 0px 0px)`,
          )
        } else {
          overlay.style.setProperty('--sheet-hole-clip', 'none')
        }
      } else {
        overlay.style.setProperty('--sheet-hole-clip', 'none')
      }
      overlay.style.display = 'block'
      overlay.style.width = `${right - left + 2}px`
      overlay.style.height = `${bottom - top + 2}px`
      overlay.style.transform = `translate3d(${left - stageRect.left - 1}px, ${top - stageRect.top - 1}px, 0)`
    },
    onSheetScroll() {
      if (this.sheetDragMode === 'move-column') this.paintSheetColumnMove()
      if (!this.sheetRange) return
      this.syncSheetRangeOverlay()
      this.$nextTick(() => this.scheduleSheetRangePaint())
    },
    hitSheetCell(target) {
      const td = target?.closest?.('.vxe-body--column')
      if (!td) return null
      const $table = this.$refs.sheetTable
      const colid = td.getAttribute('colid')
      const column = colid && $table?.getColumnById ? $table.getColumnById(colid) : null
      const field = column?.field
      if (!field) return null
      const colIndex = this.sheetColumnByKey.get(field)?.index ?? -1
      if (colIndex < 0) return null
      const tr = td.closest('tr')
      const rowid = tr?.getAttribute('rowid')
      let rowIndex = rowid != null ? (this.sheetRowIndexById.get(String(rowid)) ?? -1) : -1
      if (rowIndex < 0 && tr && $table?.getRowNode) {
        const row = $table.getRowNode(tr)?.item
        rowIndex = this.getSheetRowIndex(row)
      }
      if (rowIndex < 0) return null
      return { rowIndex, colIndex, field }
    },
    hitSheetHeader(target) {
      const th = target?.closest?.('.vxe-header--column')
      if (!th) return null
      const $table = this.$refs.sheetTable
      const colid = th.getAttribute('colid')
      const column = colid && $table?.getColumnById ? $table.getColumnById(colid) : null
      const field = column?.field
      const colIndex = field ? (this.sheetColumnByKey.get(field)?.index ?? -1) : -1
      return colIndex < 0 ? null : { colIndex, field }
    },
    onSheetSelectStart(event) {
      if (event.target?.closest?.('input, textarea')) return
      event.preventDefault()
    },
    onSheetDblClickCapture(event) {
      if (event.target?.closest?.('input, textarea, .vxe-input, .vxe-select')) return
      const hit = this.hitSheetCell(event.target)
      const row = hit ? this.list[hit.rowIndex] : null
      if (!row || this.isSheetCellLocked(row, hit.field)) {
        this.sheetEditSource = ''
        if (row) this.onLockedSheetDblClick?.(row, hit.field)
        return
      }
      this.sheetEditSource = 'dblclick'
    },
    focusSheetCellInput(row, key) {
      const input = this.$refs.sheetTable
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
      if (this.isSheetCellLocked(row, key)) return
      const character = text || event.key
      const run = async () => {
        const continuing = this.sheetEditOriginal?.rowId === row.id
          && this.sheetEditOriginal?.key === key
        if (!continuing && this.sheetEditOriginal) {
          const previousKey = this.sheetEditOriginal.key
          await this.$refs.sheetTable?.clearEdit?.()
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
        const $table = this.$refs.sheetTable
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
      if (editor) return
      if (event.key === 'Delete') {
        if (!this.sheetRange) return
        event.preventDefault()
        event.stopPropagation()
        this.clearSelectedSheetCells()
        return
      }
      if (
        event.key === 'Backspace'
        && !event.ctrlKey
        && !event.metaKey
        && !event.altKey
      ) {
        event.preventDefault()
        this.startSheetTextEdit(event, 'backspace')
        return
      }
      if ((event.ctrlKey || event.metaKey) && String(event.key).toLowerCase() === 'a') {
        event.preventDefault()
        this.selectAllSheetCells()
        return
      }
      const isComposition = event.key === 'Process' || event.keyCode === 229
      const isCharacter = String(event.key || '').length === 1
      if (event.ctrlKey || event.metaKey || event.altKey || (!isCharacter && !isComposition)) return
      this.startSheetTextEdit(event, isComposition ? 'composition' : 'character')
    },
    onSheetWrapMouseDown(event) {
      if (event.target?.closest?.('input, textarea, button, .el-button, .vxe-input, .vxe-select')) {
        return
      }
      if (event.target?.closest?.('.vxe-cell--col-resizable')) return
      this.focusSheetWrap()
      const headerHit = this.hitSheetHeader(event.target)
      if (event.button !== 0) return
      if (headerHit && event.shiftKey && !this.isSheetColumnPinned(this.sheetColumns[headerHit.colIndex])) {
        event.preventDefault()
        window.getSelection()?.removeAllRanges()
        this.$refs.sheetTable?.clearEdit?.()
        this.$refs.sheetTable?.clearSelected?.()
        this.sheetRange = null
        this.pasteAnchor = null
        this.paintSheetRange()
        this.sheetDragMode = 'move-column'
        this._sheetSelectDragMode = 'move-column'
        this._sheetPointerDown = true
        this.sheetColumnMove = { from: headerHit.colIndex, to: headerHit.colIndex }
        this.paintSheetColumnMove(event)
        window.addEventListener('mousemove', this.onSheetColumnPointerMove, { passive: false })
        return
      }
      if (headerHit && this.isExcelRowSelectField(this.sheetColumns[headerHit.colIndex]?.key)) {
        event.preventDefault()
        window.getSelection()?.removeAllRanges()
        this.$refs.sheetTable?.clearEdit?.()
        this.toggleQueueSort?.()
        return
      }
      if (headerHit && this.excelHeaderClick?.(this.sheetColumns[headerHit.colIndex])) {
        event.preventDefault()
        window.getSelection()?.removeAllRanges()
        this.$refs.sheetTable?.clearEdit?.()
        return
      }
      if (headerHit && this.list.length) {
        event.preventDefault()
        window.getSelection()?.removeAllRanges()
        this.$refs.sheetTable?.clearEdit?.()
        this._sheetSelectDragMode = 'columns'
        this._sheetPointerDown = true
        this.setSheetRange({
          r1: 0,
          c1: headerHit.colIndex,
          r2: this.list.length - 1,
          c2: headerHit.colIndex,
        })
        return
      }
      const hit = this.hitSheetCell(event.target)
      if (!hit) return
      event.preventDefault()
      window.getSelection()?.removeAllRanges()
      const dragMode = this.isExcelRowSelectField(hit.field) ? 'rows' : 'cells'
      this._sheetSelectDragMode = dragMode
      this._sheetPointerDown = true
      if (event.shiftKey && this.sheetRange) {
        this.setSheetRange(dragMode === 'rows'
          ? {
              ...this.sheetRange,
              c1: 0,
              r2: hit.rowIndex,
              c2: this.sheetColumns.length - 1,
            }
          : { ...this.sheetRange, r2: hit.rowIndex, c2: hit.colIndex })
        return
      }
      const range = dragMode === 'rows'
        ? {
            r1: hit.rowIndex,
            c1: 0,
            r2: hit.rowIndex,
            c2: this.sheetColumns.length - 1,
          }
        : { r1: hit.rowIndex, c1: hit.colIndex, r2: hit.rowIndex, c2: hit.colIndex }
      this.setSheetRange(range)
      const row = this.list[hit.rowIndex]
      if (row) {
        const selected = this.$refs.sheetTable?.getSelectedCell?.()
        if (!selected || selected.row !== row || selected.column?.field !== hit.field) {
          this.$refs.sheetTable?.setSelectCell?.(row, hit.field)
        }
      }
    },
    onSheetWrapMouseOver(event) {
      if (!this._sheetPointerDown) return
      const dragMode = this.sheetDragMode === 'move-column' ? 'move-column' : this._sheetSelectDragMode
      if (dragMode === 'move-column') return
      if (dragMode === 'columns') {
        const headerHit = this.hitSheetHeader(event.target)
        if (!headerHit || !this.sheetRange || headerHit.colIndex === this.sheetRange.c2) return
        this.setSheetRange({ ...this.sheetRange, c2: headerHit.colIndex })
        return
      }
      const hit = this.hitSheetCell(event.target)
      if (!hit || !this.sheetRange) return
      if (dragMode === 'rows') {
        if (hit.rowIndex === this.sheetRange.r2) return
        this.setSheetRange({
          ...this.sheetRange,
          r2: hit.rowIndex,
          c2: this.sheetColumns.length - 1,
        })
        return
      }
      if (hit.rowIndex === this.sheetRange.r2 && hit.colIndex === this.sheetRange.c2) return
      this.setSheetRange({ ...this.sheetRange, r2: hit.rowIndex, c2: hit.colIndex })
    },
    sheetRangeTsv() {
      const range = this.normalizedSheetRange()
      if (!range) return ''
      const lines = []
      for (let r = range.r1; r <= range.r2; r += 1) {
        const row = this.list[r]
        if (!row) continue
        const cells = []
        for (let c = range.c1; c <= range.c2; c += 1) {
          const column = this.sheetColumns[c]
          if (!column) continue
          cells.push(clipboardCell(this.sheetDirectTextValue(row, column.key)))
        }
        lines.push(cells.join('\t'))
      }
      return lines.join('\n')
    },
    onSheetWrapContextMenu(event) {
      if (event.target?.closest?.('input, textarea')) return
      const headerHit = this.hitSheetHeader(event.target)
      if (headerHit && this.excelHeaderContextMenu?.(this.sheetColumns[headerHit.colIndex], event)) {
        event.preventDefault()
        this.$refs.sheetTable?.clearEdit?.()
        return
      }
      event.preventDefault()
      this.clearSheetRange()
    },
    async clearSelectedSheetCells() {
      if (!this.canEdit) return
      const range = this.normalizedSheetRange()
      if (!range) return
      for (let rowIndex = range.r1; rowIndex <= range.r2; rowIndex += 1) {
        const row = this.list[rowIndex]
        if (!row) continue
        for (let colIndex = range.c1; colIndex <= range.c2; colIndex += 1) {
          const key = this.sheetColumns[colIndex]?.key
          if (!key || this.isSheetCellLocked(row, key)) continue
          if (!String(this.sheetDirectTextValue(row, key) ?? '').trim()) continue
          this.sheetEditSource = ''
          this.sheetEditOriginal = this.createSheetEditOriginal(row, key)
          this.setSheetDirectValue(row, key, '')
          await this.finishSheetEdit({ row, column: { field: key } })
        }
      }
    },
    onSheetCopy(event) {
      const text = this.sheetRangeTsv()
      if (!text) return
      if (event.target?.closest?.('input, textarea')) return
      event.preventDefault()
      event.clipboardData?.setData('text/plain', text)
    },
    onSheetCellSelected({ row, column, $event }) {
      if (this.sheetDragMode === 'move-column') return
      if (this._sheetPointerDown || $event?.type !== 'keydown') return
      const key = column?.field
      const rowIndex = this.getSheetRowIndex(row)
      const colIndex = key ? (this.sheetColumnByKey.get(key)?.index ?? -1) : -1
      if (rowIndex < 0 || colIndex < 0) return
      const extendsRange = $event?.shiftKey && String($event.key).startsWith('Arrow')
      if (extendsRange && this.sheetRange) {
        this.setSheetRange({ ...this.sheetRange, r2: rowIndex, c2: colIndex })
        return
      }
      this.setSheetRange({ r1: rowIndex, c1: colIndex, r2: rowIndex, c2: colIndex })
    },
    async selectSheetRange(range) {
      const row = this.list[range.r1]
      const column = this.sheetColumns[range.c1]
      if (!row || !column) return
      await this.$refs.sheetTable?.setSelectCell?.(row, column.key)
      this.setSheetRange(range)
      this.focusSheetWrap()
    },
    selectAllSheetCells() {
      if (!this.list.length || !this.sheetColumns.length) return
      this.selectSheetRange({
        r1: 0,
        c1: 0,
        r2: this.list.length - 1,
        c2: this.sheetColumns.length - 1,
      })
    },
    onSheetEditActived({ row, column }) {
      const key = column?.field
      if (!key) return
      if (
        this.sheetEditSource === 'keyboard'
        && this.sheetEditOriginal?.rowId === row.id
        && this.sheetEditOriginal?.key === key
      ) {
        return
      }
      this.sheetEditOriginal = this.createSheetEditOriginal(row, key)
      if (this.sheetEditSource === 'dblclick') this.openSheetEditorPanel(row, key)
    },
    openSheetEditorPanel(row, key) {
      const open = () => {
        const cell = this.$refs.sheetTable?.getCellElement?.(row, key)
        const node = cell?.querySelector?.('.vxe-select, .vxe-input')
        const panel = node?.__vueParentComponent?.proxy
        if (typeof panel?.showPanel !== 'function') return false
        panel.showPanel()
        return true
      }
      this.$nextTick(() => {
        if (!open()) this.$nextTick(open)
      })
    },
    takeSheetEditOriginal(row, key) {
      const original = this.sheetEditOriginal
      this.sheetEditOriginal = null
      if (original?.rowId === row.id && original.key === key) {
        return this.cloneSheetValue(original.value)
      }
      return this.cloneSheetValue(this.sheetValueSnapshot(this.rowBaselines.get(row.id) || {}, key))
    },
    async restoreSheetSelectedCell() {
      const $table = this.$refs.sheetTable
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
      const wrap = this.$refs.sheetWrap
      if (
        !activeElement
        || activeElement === document.body
        || wrap?.contains?.(activeElement)
        || activeElement.closest?.('.sheet-picker-popup')
      ) {
        this.focusSheetWrap()
      }
    },
    focusSheetWrap() {
      this.$refs.sheetWrap?.focus?.({ preventScroll: true })
    },
    onSheetEditClosed(context) {
      const operation = this.finishSheetEdit(context)
      this.pendingSheetOps.add(operation)
      this.$nextTick(() => this.restoreSheetSelectedCell())
      return operation.finally(() => this.pendingSheetOps.delete(operation))
    },
  },
}
