import { clipboardCell } from './clipboardGrid'
import { columnTextClass, createColumnOrder } from './columnOrder'
import './shiftHeld'

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
// 有表头菜单的列：按住表头超过这么久才选中整列，短按是开菜单
const SHEET_HEADER_HOLD_MS = 350

/**
 * 只读查询页的序号列：只是显示用的行号，和数据库无关，翻页后接着编号。
 * 页面把它放在列定义第一个，excelRowSelectKey、sheetPinFirstKey 和 createColumnOrder 的 pinFirstKey 都设成它的 key，
 * 取值用 sheetRowNo(row)。点序号选整行，点表头全选。
 */
export const SHEET_ROW_NO_COLUMN = Object.freeze({ key: 'row_no', label: '序号', width: 64, align: 'center' })

/**
 * vxe 表格的划选、复制、整列整行选择、Shift 拖列和列宽记忆，不含单元格编辑。
 * 只读表格直接混入本层；可编辑的工作台用 workbenchExcelMixin（已包含本层）。
 *
 * 页面需提供：list、loading、listTableHeight；列在组件选项 workbenchSheet 里声明：
 * { columns: 全部列定义（{ key, label }）, order: createColumnOrder 结果（记住列序和列宽）, aliases: 粘贴表头别名 }。
 * sheetColumns（当前显示的列）默认按 order 记住的列序初始化；列随类型变化的页面覆写 availableSheetColumns。
 * 模板用 <WorkbenchSheet>，外层和表格的事件、配置都由它接好；表格元素经 sheetEl(name) 取。
 * 单元格复制文本取 sheetDirectTextValue，有展示转换时覆写。
 */
export default {
  provide() {
    return { workbenchSheetHost: this }
  },
  data() {
    return {
      sheetColumns: this.$options.workbenchSheet?.order?.load() || [],
      excelRowSelectKey: '',
      sheetPinFirstKey: '',
      sheetPinLastKey: '',
      pasteAnchor: null,
      sheetRange: null,
      sheetDragMode: '',
      sheetColumnMove: null,
      sheetColumnWidths: {},
      sheetColumnColors: {},
      sheetLayoutVersion: 0,
      sheetRowConfig: SHEET_ROW_CONFIG,
      sheetCellConfig: SHEET_CELL_CONFIG,
      sheetColumnConfig: SHEET_COLUMN_CONFIG,
      sheetMouseConfig: SHEET_MOUSE_CONFIG,
      sheetVirtualYConfig: SHEET_VIRTUAL_Y_CONFIG,
      sheetVirtualXConfig: SHEET_VIRTUAL_X_CONFIG,
    }
  },
  computed: {
    sheetColumnOrderKey() {
      // 带上版本号：重置列宽时重建表格，清掉 vxe 内部记下的拖拽宽度。
      return `${this.sheetLayoutVersion}|${this.sheetColumns.map((column) => column.key).join(',')}`
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
    sheetKeyboardConfig() {
      return SHEET_KEYBOARD_CONFIG
    },
  },
  created() {
    if (import.meta.env.DEV && !this.$options.workbenchSheet?.order) {
      console.warn(`[sheetSelectionMixin] ${this.$options.name} 没有声明 workbenchSheet.order，Excel 列序和列宽不会记住`)
    }
    this.sheetView = null
    this.sheetRangeBeforeClick = null
    this.sheetColumnWidths = this.sheetColumnStore()?.loadWidths() || {}
    this.loadSheetColumnColors()
  },
  mounted() {
    this.onWindowMouseUp = () => this.finishSheetPointer()
    this.onSheetWindowResize = () => {
      if (this.sheetRange) this.scheduleSheetRangePaint()
    }
    window.addEventListener('mouseup', this.onWindowMouseUp)
    window.addEventListener('resize', this.onSheetWindowResize)
  },
  beforeUnmount() {
    this.releaseSheetPointer()
  },
  activated() {
    if (this.onWindowMouseUp) {
      window.addEventListener('mouseup', this.onWindowMouseUp)
      window.addEventListener('resize', this.onSheetWindowResize)
    }
  },
  deactivated() {
    this.releaseSheetPointer()
  },
  methods: {
    attachSheetView(view) {
      this.sheetView = view
    },
    detachSheetView(view) {
      if (this.sheetView === view) this.sheetView = null
    },
    /** WorkbenchSheet 里的元素：table（vxe 实例）、wrap、stage、rangeOverlay、dropLine、ghost；未挂载时为 null。 */
    sheetEl(name) {
      return this.sheetView?.[name]() ?? null
    },
    releaseSheetPointer() {
      this.cancelSheetHeaderPress()
      if (this._sheetRangeRafId) {
        cancelAnimationFrame(this._sheetRangeRafId)
        this._sheetRangeRafId = 0
      }
      if (this.onWindowMouseUp) {
        window.removeEventListener('mouseup', this.onWindowMouseUp)
        window.removeEventListener('resize', this.onSheetWindowResize)
      }
      window.removeEventListener('mousemove', this.onSheetColumnPointerMove)
    },
    isExcelRowSelectField(field) {
      return Boolean(field) && field === this.excelRowSelectKey
    },
    isSheetColumnPinned(column) {
      const key = column?.key
      if (!key) return false
      return key === this.sheetPinFirstKey || key === this.sheetPinLastKey
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
      const column = this.sheetEl('table')?.getColumnById?.(colid)
      const field = column?.field
      return field ? this.sheetColumnByKey.get(field)?.index : undefined
    },
    /** 序号列的值：按当前页码和每页条数接着编号。 */
    sheetRowNo(row) {
      const index = this.getSheetRowIndex(row)
      if (index < 0) return ''
      const { page = 1, limit = 0 } = this.listQuery || {}
      return String((page - 1) * limit + index + 1)
    },
    sheetColumnTitle(column) {
      if (this.isExcelRowSelectField(column?.key) && this.sortColumnLabel) return this.sortColumnLabel
      return column?.label || ''
    },
    sheetDirectTextValue(row, key) {
      if (!row) return ''
      if (row[key] === null || row[key] === undefined) return ''
      return String(row[key])
    },
    sheetColumnStore() {
      return this.$options.workbenchSheet?.order || null
    },
    sheetColumnWidth(column) {
      return this.sheetColumnWidths[column?.key] || column?.width
    },
    onSheetColumnResize({ resizeColumn, resizeWidth }) {
      const key = resizeColumn?.field
      const width = Math.round(Number(resizeWidth))
      if (!key || !width) return
      this.sheetColumnWidths = { ...this.sheetColumnWidths, [key]: width }
      this.sheetColumnStore()?.saveWidth(key, width)
    },
    resetSheetColumnWidths() {
      this.sheetColumnWidths = {}
      this.sheetLayoutVersion += 1
    },
    /** 当前可用的列；列随类型变化的页面覆写，返回该类型的列定义，空值表示记住的列全用。 */
    availableSheetColumns() {
      return this.$options.workbenchSheet?.columns || null
    },
    /** 按记住的列序排出 sheetColumns。 */
    rebuildSheetColumns() {
      const store = this.sheetColumnStore()
      const stored = store ? store.load() : this.sheetColumns
      const available = this.availableSheetColumns()
      if (!available) {
        this.sheetColumns = stored
        return
      }
      const remaining = new Map(available.map((column) => [column.key, column]))
      const ordered = []
      stored.forEach((column) => {
        const hit = remaining.get(column.key)
        if (!hit) return
        ordered.push(hit)
        remaining.delete(column.key)
      })
      this.sheetColumns = [...ordered, ...remaining.values()]
    },
    /** 存列序：只换掉当前可见的列在总列序里的位置，其他类型的列保持原位。 */
    persistSheetColumnOrder(columns) {
      const next = columns || this.sheetColumns
      this.sheetColumns = next
      const store = this.sheetColumnStore()
      if (!store) return
      const visibleKeys = new Set(next.map((column) => column.key))
      let visibleIndex = 0
      const merged = store.load().map((column) => {
        if (!visibleKeys.has(column.key)) return column
        const replacement = next[visibleIndex]
        visibleIndex += 1
        return replacement || column
      })
      if (visibleIndex < next.length) merged.push(...next.slice(visibleIndex))
      store.save(merged)
    },
    resetSheetColumns() {
      this.sheetColumnStore()?.clear()
      this.rebuildSheetColumns()
      this.persistSheetColumnOrder(this.sheetColumns)
      this.resetSheetColumnWidths()
      this.clearSheetRange()
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
      const classes = ['sheet-selectable-header']
      if (!this.isSheetColumnPinned({ key: column.field })) classes.push('sheet-movable-header')
      const menu = this.headerCellClass?.(column.field)
      if (menu) classes.push(menu)
      return classes.join(' ')
    },
    /** 页面自己的单元格配色类。 */
    sheetCellClassName() {
      return ''
    },
    /** 共用字段的配色类（如优先级），workbenchExcelMixin 按字段给。 */
    sheetFieldToneClass() {
      return ''
    },
    // 字体颜色在工作台视图「显示字段」里设置，与工作台表格共用 viewPrefsStorageKey。
    loadSheetColumnColors() {
      this.sheetColumnColors = this.viewPrefsStorageKey ? createColumnOrder(this.viewPrefsStorageKey, []).loadColors() : {}
    },
    sheetCellClass(params) {
      return [
        this.sheetFieldToneClass(params),
        this.sheetCellClassName(params),
        columnTextClass(this.sheetColumnColors[params.column?.field]),
      ]
        .filter(Boolean)
        .join(' ')
    },
    paintSheetColumnMove(event) {
      const wrap = this.sheetEl('wrap')
      const stage = this.sheetEl('stage')
      const line = this.sheetEl('dropLine')
      const ghost = this.sheetEl('ghost')
      const $table = this.sheetEl('table')
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
      const wrap = this.sheetEl('wrap')
      const $table = this.sheetEl('table')
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
      this.cancelSheetHeaderPress()
      const move = this.sheetDragMode === 'move-column' ? this.sheetColumnMove : null
      window.removeEventListener('mousemove', this.onSheetColumnPointerMove)
      this._sheetPointerDown = false
      this._sheetSelectDragMode = ''
      if (this.sheetDragMode) this.sheetDragMode = ''
      if (this.sheetColumnMove) this.sheetColumnMove = null
      if (move) this.paintSheetColumnMove()
      if (move && move.from === move.to) {
        this.extendSheetColumnsTo(move.from)
        return
      }
      if (!move) return
      if (this.isSheetColumnPinned(this.sheetColumns[move.from]) || this.isSheetColumnPinned(this.sheetColumns[move.to])) return
      const next = [...this.sheetColumns]
      const [column] = next.splice(move.from, 1)
      if (!column) return
      next.splice(move.to, 0, column)
      this.sheetColumns = next
      this.persistSheetColumnOrder(next)
      this.clearSheetRange()
    },
    /** Shift 点表头没拖动：从按下前选区的起始列选到这一列（整列），没有选区就选这一列。 */
    extendSheetColumnsTo(colIndex) {
      const previous = this._sheetShiftPrevRange
      this._sheetShiftPrevRange = null
      if (!this.list.length) return
      this.setSheetRange({ r1: 0, c1: previous ? previous.c1 : colIndex, r2: this.list.length - 1, c2: colIndex })
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
    /** 按住表头到时，或按着拖到别的列：从按下的列选到 toIndex。 */
    selectPressedSheetColumns(toIndex) {
      const press = this._sheetHeaderPress
      if (!press) return
      this.cancelSheetHeaderPress()
      this._sheetHeaderSelected = true
      this.setSheetRange({ r1: 0, c1: press.colIndex, r2: this.list.length - 1, c2: toIndex ?? press.colIndex })
    },
    cancelSheetHeaderPress() {
      if (!this._sheetHeaderPress) return
      clearTimeout(this._sheetHeaderPress.timer)
      this._sheetHeaderPress = null
    },
    /** 清选区时一并清掉的状态；编辑层覆写，复位编辑中的单元格。 */
    onSheetRangeCleared() {},
    clearSheetRange() {
      this.cancelSheetHeaderPress()
      window.removeEventListener('mousemove', this.onSheetColumnPointerMove)
      this._sheetPointerDown = false
      this._sheetSelectDragMode = ''
      if (this.sheetRange !== null) this.sheetRange = null
      this.onSheetRangeCleared()
      if (this.sheetDragMode !== '') this.sheetDragMode = ''
      if (this.sheetColumnMove !== null) this.sheetColumnMove = null
      if (this.pasteAnchor !== null) this.pasteAnchor = null
      this.paintSheetColumnMove()
      this.sheetEl('table')?.clearSelected?.()
      this.scheduleSheetRangePaint()
    },
    paintSheetRange() {
      this.syncSheetRangeOverlay()
    },
    syncSheetRangeOverlay() {
      const wrap = this.sheetEl('wrap')
      const overlay = this.sheetEl('rangeOverlay')
      const $table = this.sheetEl('table')
      const range = this.normalizedSheetRange()
      if (!wrap || !overlay || !$table || !range) {
        if (overlay) overlay.style.display = 'none'
        return
      }
      const bodyWrapper = wrap.querySelector('.vxe-table--main-wrapper .vxe-table--body-wrapper')
        || wrap.querySelector('.vxe-table--body-wrapper')
      const tbody = bodyWrapper?.querySelector('tbody')
      const stage = this.sheetEl('stage')
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
      const $table = this.sheetEl('table')
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
      const $table = this.sheetEl('table')
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
    onSheetWrapMouseDown(event) {
      if (event.target?.closest?.('input, textarea, button, .el-button, .el-checkbox, .vxe-input, .vxe-select')) {
        return
      }
      if (event.target?.closest?.('.vxe-cell--col-resizable')) return
      this.focusSheetWrap()
      const headerHit = this.hitSheetHeader(event.target)
      if (event.button !== 0) return
      this._sheetHeaderSelected = false
      if (headerHit && event.shiftKey && !this.isSheetColumnPinned(this.sheetColumns[headerHit.colIndex])) {
        event.preventDefault()
        window.getSelection()?.removeAllRanges()
        this.sheetEl('table')?.clearEdit?.()
        this.sheetEl('table')?.clearSelected?.()
        this._sheetShiftPrevRange = this.sheetRange
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
      if (headerHit && this.isExcelRowSelectField(headerHit.field)) {
        event.preventDefault()
        window.getSelection()?.removeAllRanges()
        this.sheetEl('table')?.clearEdit?.()
        // 排队页面点「序号」表头切换队列序；其他页面当作左上角，全选
        if (headerHit.field === 'sort_order' && this.toggleQueueSort) this.toggleQueueSort()
        else this.selectAllSheetCells()
        return
      }
      if (headerHit && this.list.length) {
        event.preventDefault()
        window.getSelection()?.removeAllRanges()
        this.sheetEl('table')?.clearEdit?.()
        this._sheetSelectDragMode = 'columns'
        this._sheetPointerDown = true
        if (this.headerMenuColumns?.[headerHit.field]) {
          // 单击要开菜单，先不选；按住到时或拖到别的列再选，松开前没选就交给 click 开菜单
          this.cancelSheetHeaderPress()
          this._sheetHeaderPress = {
            colIndex: headerHit.colIndex,
            timer: setTimeout(() => this.selectPressedSheetColumns(), SHEET_HEADER_HOLD_MS),
          }
          return
        }
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
      // 单击会把选区收成一格；双击的第二下（detail 2）不覆盖，编辑层据此判断是不是在原选区里双击
      if (event.detail <= 1) this.sheetRangeBeforeClick = event.shiftKey ? null : this.normalizedSheetRange()
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
        const selected = this.sheetEl('table')?.getSelectedCell?.()
        if (!selected || selected.row !== row || selected.column?.field !== hit.field) {
          this.sheetEl('table')?.setSelectCell?.(row, hit.field)
        }
      }
    },
    onSheetWrapMouseOver(event) {
      if (!this._sheetPointerDown) return
      const dragMode = this.sheetDragMode === 'move-column' ? 'move-column' : this._sheetSelectDragMode
      if (dragMode === 'move-column') return
      if (dragMode === 'columns') {
        const headerHit = this.hitSheetHeader(event.target)
        if (!headerHit) return
        if (this._sheetHeaderPress) {
          if (headerHit.colIndex !== this._sheetHeaderPress.colIndex) this.selectPressedSheetColumns(headerHit.colIndex)
          return
        }
        if (!this.sheetRange || headerHit.colIndex === this.sheetRange.c2) return
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
      event.preventDefault()
      this.clearSheetRange()
    },
    onSheetCopy(event) {
      const text = this.sheetRangeTsv()
      if (!text) return
      if (event.target?.closest?.('input, textarea')) return
      event.preventDefault()
      event.clipboardData?.setData('text/plain', text)
    },
    /** 只读表格的键盘处理：Ctrl+A 全选。编辑层覆写为完整的键入处理。 */
    onSheetKeydownCapture(event) {
      if (event.target?.closest?.('input, textarea')) return
      if ((event.ctrlKey || event.metaKey) && String(event.key).toLowerCase() === 'a') {
        event.preventDefault()
        this.selectAllSheetCells()
      }
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
      await this.sheetEl('table')?.setSelectCell?.(row, column.key)
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
    focusSheetWrap() {
      this.sheetEl('wrap')?.focus?.({ preventScroll: true })
    },
  },
}
