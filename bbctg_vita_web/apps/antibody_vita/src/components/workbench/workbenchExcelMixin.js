/**
 * Excel 划选 / 键入 / 列序。约定见 docs/modules/workbench.md。
 * 页面需提供：list, sheetColumns, canEdit, persistSheetColumnOrder, finishSheetEdit。
 * 键入默认 row[key] = 文本；有双字段或展示转换时再覆写 sheetDirectTextValue。
 * 单格保存必须 patchExistingListRow，禁止 splice 换行对象。
 * 数字格普通输入，提交时由本页 coerceSheetValue 校验。
 * 行选择列用 excelRowSelectKey（默认 sort_order）。
 */
export default {
  data() {
    return {
      excelRowSelectKey: 'sort_order',
      pasteAnchor: null,
      pendingSheetOps: new Set(),
      sheetRange: null,
      sheetEditOriginal: null,
      sheetEditSource: '',
      sheetKeyboardChain: Promise.resolve(),
      sheetDragMode: '',
      sheetPointerDown: false,
      sheetColumnMove: null,
    }
  },
  computed: {
    isExcelMode() {
      return this.viewMode === 'excel'
    },
    sheetColumnOrderKey() {
      return this.sheetColumns.map((column) => column.key).join(',')
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
      return {
        isArrow: true,
        isDel: true,
        isEnter: true,
        isTab: true,
        isShift: true,
        isEdit: false,
        isClip: false,
      }
    },
    sheetEditConfig() {
      return {
        trigger: 'dblclick',
        mode: 'cell',
        showIcon: false,
        beforeEditMethod: this.sheetBeforeEdit,
      }
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
      const cache = this._sheetEditRenderCache || (this._sheetEditRenderCache = new Map())
      const cacheKey = column?.edit === 'date' ? `date:${column.key}` : `text:${column.key}`
      const cached = cache.get(cacheKey)
      if (cached) return cached
      const render = column?.edit === 'date'
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
          }
      cache.set(cacheKey, render)
      return render
    },
    isExcelRowSelectField(field) {
      return field === this.excelRowSelectKey
    },
    isSheetCellLocked(row, key) {
      if (!this.canEdit) return true
      if (this.isExcelRowSelectField(key) && (!this.isQueueSorted || this.isQueueTerminalRow?.(row))) return true
      const column = this.sheetColumns.find((item) => item.key === key)
      return column?.edit === 'readonly'
    },
    canEditSortCell(row) {
      if (!this.isQueueSorted || this.isQueueTerminalRow?.(row)) return false
      if (typeof this.canEditField === 'function') return this.canEditField(row, 'sort_order')
      return Boolean(this.canEdit)
    },
    formatSortColumnCell({ row }) {
      return this.formatSortColumn(row)
    },
    formatSortColumn(row, index) {
      if (!this.isQueueSorted) {
        const i = Number.isInteger(index) && index >= 0 ? index : this.list.indexOf(row)
        return i >= 0 ? String(i + 1) : ''
      }
      const n = Number(row?.sort_order)
      return Number.isInteger(n) && n > 0 ? String(n) : '-'
    },
    toggleQueueSort() {
      this.listQuery.sort_field = this.isQueueSorted ? '' : 'sort_order'
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
      return column?.label || ''
    },
    queueReorderPayload(oldIndex, newIndex) {
      const moved = this.list[oldIndex]
      const target = this.list[newIndex]
      if (!moved || !target || moved.id === target.id) return null
      if (this.isQueueTerminalRow?.(moved) || this.isQueueTerminalRow?.(target)) return null
      return { movedId: moved.id, targetId: target.id }
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
      return column.field ? 'sheet-selectable-header' : ''
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
        const colIndex = this.sheetColumns.findIndex((item) => item.key === field)
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
      if (hit) this.sheetColumnMove.to = hit.colIndex
      this.paintSheetColumnMove(event)
    },
    finishSheetPointer() {
      const move = this.sheetDragMode === 'move-column' ? this.sheetColumnMove : null
      window.removeEventListener('mousemove', this.onSheetColumnPointerMove)
      this.sheetPointerDown = false
      this.sheetDragMode = ''
      this.sheetColumnMove = null
      this.paintSheetColumnMove()
      if (!move || move.from === move.to) return
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
      this.pasteAnchor = { rowIndex: this.sheetRange.r1, colKey: column.key }
    },
    setSheetRange(next) {
      this.sheetRange = next
      this.syncPasteAnchorFromRange()
      this.$nextTick(() => this.paintSheetRange())
    },
    clearSheetRange() {
      window.removeEventListener('mousemove', this.onSheetColumnPointerMove)
      this.sheetRange = null
      this.sheetEditOriginal = null
      this.sheetEditSource = ''
      this.sheetDragMode = ''
      this.sheetPointerDown = false
      this.sheetColumnMove = null
      this.pasteAnchor = null
      this.paintSheetColumnMove()
      this.$refs.sheetTable?.clearSelected?.()
      this.$nextTick(() => this.paintSheetRange())
    },
    paintSheetRange() {
      const wrap = this.$refs.sheetWrap
      const overlay = this.$refs.sheetRangeOverlay
      if (!wrap?.querySelectorAll || !overlay) return
      overlay.classList.remove('is-scrolling')
      wrap.querySelectorAll('.is-sheet-selected, .is-sheet-active').forEach((el) => {
        el.classList.remove('is-sheet-selected', 'is-sheet-active')
      })
      const range = this.normalizedSheetRange()
      const $table = this.$refs.sheetTable
      if (!range || !$table) {
        overlay.style.display = 'none'
        return
      }
      const rowIndexById = new Map(
        this.list.map((row, index) => [String($table.getRowid?.(row) || row.id), index]),
      )
      const columnIndexById = new Map()
      this.sheetColumns.forEach((column, index) => {
        const id = $table.getColumnByField?.(column.key)?.id
        if (id) columnIndexById.set(id, index)
      })
      const activeRow = this.pasteAnchor?.rowIndex
      const activeColumn = this.sheetColumns.findIndex(
        (column) => column.key === this.pasteAnchor?.colKey,
      )
      for (const tr of wrap.querySelectorAll('.vxe-table--body-wrapper tr[rowid]')) {
        const r = rowIndexById.get(String(tr.getAttribute('rowid') || ''))
        if (r == null || r < range.r1 || r > range.r2) continue
        for (const td of tr.querySelectorAll('.vxe-body--column')) {
          const c = columnIndexById.get(td.getAttribute('colid'))
          if (c == null || c < range.c1 || c > range.c2) continue
          td.classList.add('is-sheet-selected')
          if (r === activeRow && c === activeColumn) td.classList.add('is-sheet-active')
        }
      }
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
      const rowIndexById = new Map(
        this.list.map((row, index) => [String($table.getRowid?.(row) || row.id), index]),
      )
      const columnIndexById = new Map()
      this.sheetColumns.forEach((column, index) => {
        const id = $table.getColumnByField?.(column.key)?.id
        if (id) columnIndexById.set(id, index)
      })
      let firstCell = null
      let topCell = null
      let bottomCell = null
      let leftCell = null
      let rightCell = null
      let topRow = Number.POSITIVE_INFINITY
      let bottomRow = Number.NEGATIVE_INFINITY
      let leftColumn = Number.POSITIVE_INFINITY
      let rightColumn = Number.NEGATIVE_INFINITY
      for (const tr of wrap.querySelectorAll('.vxe-table--body-wrapper tr[rowid]')) {
        const r = rowIndexById.get(String(tr.getAttribute('rowid') || ''))
        if (r == null || r < range.r1 || r > range.r2) continue
        for (const td of tr.querySelectorAll('.vxe-body--column')) {
          const c = columnIndexById.get(td.getAttribute('colid'))
          if (c == null || c < range.c1 || c > range.c2) continue
          firstCell ||= td
          if (r < topRow) {
            topRow = r
            topCell = td
          }
          if (r > bottomRow) {
            bottomRow = r
            bottomCell = td
          }
          if (c < leftColumn) {
            leftColumn = c
            leftCell = td
          }
          if (c > rightColumn) {
            rightColumn = c
            rightCell = td
          }
        }
      }
      const stage = this.$refs.sheetTableStage
      const stageRect = stage?.getBoundingClientRect?.()
      const bodyRect = firstCell
        ?.closest?.('.vxe-table--body-wrapper')
        ?.getBoundingClientRect?.()
      if (!stageRect || !firstCell || !topCell || !bottomCell || !leftCell || !rightCell) {
        overlay.style.display = 'none'
        return
      }
      const clipRect = bodyRect || stageRect
      const left = Math.max(leftCell.getBoundingClientRect().left, clipRect.left)
      const top = Math.max(topCell.getBoundingClientRect().top, clipRect.top)
      const right = Math.min(rightCell.getBoundingClientRect().right, clipRect.right)
      const bottom = Math.min(bottomCell.getBoundingClientRect().bottom, clipRect.bottom)
      if (right <= left || bottom <= top) {
        overlay.style.display = 'none'
        return
      }
      overlay.style.display = 'block'
      overlay.style.width = `${right - left + 2}px`
      overlay.style.height = `${bottom - top + 2}px`
      overlay.style.transform = `translate3d(${left - stageRect.left - 1}px, ${top - stageRect.top - 1}px, 0)`
    },
    onSheetScroll() {
      if (this.sheetDragMode === 'move-column') this.paintSheetColumnMove()
      if (!this.sheetRange) return
      this.$refs.sheetRangeOverlay?.classList.add('is-scrolling')
      this.syncSheetRangeOverlay()
    },
    hitSheetCell(target) {
      const td = target?.closest?.('.vxe-body--column')
      if (!td) return null
      const $table = this.$refs.sheetTable
      const colid = td.getAttribute('colid')
      const column = colid && $table?.getColumnById ? $table.getColumnById(colid) : null
      const field = column?.field
      if (!field) return null
      const colIndex = this.sheetColumns.findIndex((item) => item.key === field)
      if (colIndex < 0) return null
      const tr = td.closest('tr')
      const node = tr && $table?.getRowNode ? $table.getRowNode(tr) : null
      const row = node?.item
      const rowIndex = row
        ? this.list.findIndex((item) => item.id === row.id)
        : this.list.findIndex((item) => String(item.id) === String(tr?.getAttribute('rowid')))
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
      const colIndex = this.sheetColumns.findIndex((item) => item.key === field)
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
      this.sheetEditSource = row && !this.isSheetCellLocked(row, hit.field) ? 'dblclick' : ''
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
        const edit = $table?.getEditRecord?.()
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
        const row = this.list[this.pasteAnchor?.rowIndex]
        const key = this.pasteAnchor?.colKey
        if (row && key && this.isSheetCellLocked(row, key)) {
          event.preventDefault()
          event.stopPropagation()
        }
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
      if (headerHit && event.shiftKey) {
        event.preventDefault()
        window.getSelection()?.removeAllRanges()
        this.$refs.sheetTable?.clearEdit?.()
        this.$refs.sheetTable?.clearSelected?.()
        this.sheetRange = null
        this.pasteAnchor = null
        this.paintSheetRange()
        this.sheetDragMode = 'move-column'
        this.sheetPointerDown = true
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
      if (headerHit && this.list.length) {
        event.preventDefault()
        window.getSelection()?.removeAllRanges()
        this.$refs.sheetTable?.clearEdit?.()
        this.sheetDragMode = 'columns'
        this.sheetPointerDown = true
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
      this.sheetDragMode = this.isExcelRowSelectField(hit.field) ? 'rows' : 'cells'
      this.sheetPointerDown = true
      if (event.shiftKey && this.sheetRange) {
        this.setSheetRange(this.sheetDragMode === 'rows'
          ? {
              ...this.sheetRange,
              c1: 0,
              r2: hit.rowIndex,
              c2: this.sheetColumns.length - 1,
            }
          : { ...this.sheetRange, r2: hit.rowIndex, c2: hit.colIndex })
        return
      }
      const range = this.sheetDragMode === 'rows'
        ? {
            r1: hit.rowIndex,
            c1: 0,
            r2: hit.rowIndex,
            c2: this.sheetColumns.length - 1,
          }
        : { r1: hit.rowIndex, c1: hit.colIndex, r2: hit.rowIndex, c2: hit.colIndex }
      this.setSheetRange(range)
      const row = this.list[hit.rowIndex]
      if (row) this.$refs.sheetTable?.setSelectCell?.(row, hit.field)
    },
    onSheetWrapMouseOver(event) {
      if (!this.sheetPointerDown) return
      if (this.sheetDragMode === 'move-column') return
      if (this.sheetDragMode === 'columns') {
        const headerHit = this.hitSheetHeader(event.target)
        if (!headerHit || !this.sheetRange || headerHit.colIndex === this.sheetRange.c2) return
        this.setSheetRange({ ...this.sheetRange, c2: headerHit.colIndex })
        return
      }
      const hit = this.hitSheetCell(event.target)
      if (!hit || !this.sheetRange) return
      if (this.sheetDragMode === 'rows') {
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
          cells.push(this.sheetDirectTextValue(row, column.key))
        }
        lines.push(cells.join('\t'))
      }
      return lines.join('\n')
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
      const key = column?.field
      const rowIndex = this.list.findIndex((item) => item.id === row.id)
      const colIndex = this.sheetColumns.findIndex((item) => item.key === key)
      if (rowIndex < 0 || colIndex < 0) return
      if (this.sheetPointerDown && this.sheetDragMode === 'rows') {
        this.setSheetRange({
          r1: this.sheetRange?.r1 ?? rowIndex,
          c1: 0,
          r2: rowIndex,
          c2: this.sheetColumns.length - 1,
        })
        return
      }
      const extendsRange = $event?.shiftKey
        && ($event.type !== 'keydown' || String($event.key).startsWith('Arrow'))
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
      if (!$table || $table.getEditRecord?.()) return
      const row = this.list[this.pasteAnchor?.rowIndex]
      const key = this.pasteAnchor?.colKey
      if (!row || !key) return
      await $table.setSelectCell?.(row, key)
      if ($table.getEditRecord?.()) return
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
