import { ElMessage } from 'element-plus'

import { notifyApiError } from '#/api/errors'

import { WORKBENCH_VIEW } from './viewMode'

/**
 * 队列排序：排序列（sort_order）显示与改值、表头切换队列序、工作台视图拖行。约定见 docs/modules/workbench.md。
 * 放在 workbenchExcelMixin 之后，才会把行选择列和首列固定改成 sort_order。
 * 页面需提供：list, listQuery, getList()（刷新前先存完编辑）, viewMode, canEdit（或 canFullEdit / canEditField）, persistRow,
 * 组件选项 workbenchApi.reorder(movedId, targetId)；已结束、不参与排队的行用 isQueueTerminalRow(row) 标出。
 * 模板用 WorkbenchSortHeader / WorkbenchSortCell，表格加 :class="{ 'is-row-sortable': canDragRows }" 和 @reorder="scheduleSortable"，
 * 列定义给排序列 className: 'sort-column-cell'（拖拽手柄）。
 */
export default {
  data() {
    return {
      excelRowSelectKey: 'sort_order',
      sheetPinFirstKey: 'sort_order',
      sortEditingId: null,
      sortable: null,
      sortableInitToken: 0,
    }
  },
  computed: {
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
        && this.viewMode === WORKBENCH_VIEW
        && this.isQueueSorted
        && this.queuedRowCount > 1
      )
    },
  },
  watch: {
    viewMode(value) {
      if (value === WORKBENCH_VIEW) this.scheduleSortable()
      else this.destroySortable()
    },
    list() {
      this.scheduleSortable()
    },
    canDragRows() {
      this.scheduleSortable()
    },
  },
  mounted() {
    this.scheduleSortable()
  },
  activated() {
    this.scheduleSortable()
  },
  deactivated() {
    this.destroySortable()
  },
  beforeUnmount() {
    this.destroySortable()
  },
  methods: {
    queueSortLockReason(row) {
      if (this.isQueueTerminalRow?.(row)) return '已结束的记录不在队列里，不能改排序'
      if (!this.isQueueSorted) return '先点表头「序号」切到队列排序，再改排序'
      return ''
    },
    sheetSortLockReason(row, key) {
      return key === 'sort_order' ? this.queueSortLockReason(row) : ''
    },
    sortCellLockReason(row) {
      if (this.isQueueTerminalRow?.(row)) return this.queueSortLockReason(row)
      const allowed = typeof this.canEditField === 'function'
        ? this.canEditField(row, 'sort_order')
        : this.canEdit
      if (!allowed) return this.fieldLockReason?.(row, 'sort_order') || '你没有修改排序的权限'
      return this.queueSortLockReason(row)
    },
    canEditSortCell(row) {
      return Boolean(row) && !this.sortCellLockReason(row)
    },
    formatSortColumnCell({ row, rowIndex, $rowIndex }) {
      const idx = Number.isInteger(rowIndex) && rowIndex >= 0 ? rowIndex : $rowIndex
      return this.formatSortColumn(row, idx)
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
      if (this.listQuery && 'sort_dir' in this.listQuery) {
        this.listQuery.sort_dir = ''
      }
      this.listQuery.sort_field = this.isQueueSorted ? '' : 'sort_order'
      this.listQuery.page = 1
      this.getList()
    },
    /** 队列序下新建行所在的页；不在队列序时返回 1。 */
    queuePageOf(saved) {
      const limit = Math.max(1, Number(this.listQuery.limit) || 20)
      const n = Number(saved?.sort_order)
      return this.isQueueSorted && Number.isInteger(n) && n > 0 ? Math.ceil(n / limit) : 1
    },
    onSortCellClick(row) {
      if (this.canEditSortCell(row)) {
        if (row?.id) this.sortEditingId = row.id
        return
      }
      const reason = this.sortCellLockReason(row)
      if (reason) ElMessage.info({ message: reason, grouping: true })
    },
    finishSortEdit(row) {
      if (this.sortEditingId !== row.id) return
      this.sortEditingId = null
      this.persistRow(row, 'sort_order')
    },
    scheduleSortable() {
      this.$nextTick(() => this.initSortable())
    },
    async initSortable() {
      const initToken = ++this.sortableInitToken
      if (this.viewMode !== WORKBENCH_VIEW || !this.canDragRows) {
        this.destroySortable()
        return
      }
      await this.$nextTick()
      const tbody = this.$refs.workbenchTable?.$el?.querySelector('.el-table__body-wrapper tbody')
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
        onEnd: (event) => this.handleDragEnd(event),
      })
    },
    destroySortable() {
      this.sortable?.destroy?.()
      this.sortable = null
    },
    /** Sortable 已经挪了 DOM，先挪回原位，交给列表刷新重排，免得和 Vue 的渲染打架。 */
    revertDrag(item, oldIndex, newIndex) {
      const parent = item?.parentNode
      if (!parent || oldIndex == null || newIndex == null || oldIndex === newIndex) return
      const dataRows = [...parent.children].filter((tr) => tr.classList?.contains('el-table__row'))
      const anchor = newIndex > oldIndex ? dataRows[oldIndex] : dataRows[oldIndex + 1]
      parent.insertBefore(item, anchor || null)
    },
    async handleDragEnd({ oldIndex, newIndex, item }) {
      this.revertDrag(item, oldIndex, newIndex)
      if (!this.canDragRows || oldIndex == null || newIndex == null || oldIndex === newIndex) return
      const moved = this.list[oldIndex]
      const target = this.list[newIndex]
      if (!moved || !target || moved.id === target.id) return
      if (this.isQueueTerminalRow?.(moved) || this.isQueueTerminalRow?.(target)) return
      this.loading = true
      try {
        await this.$options.workbenchApi.reorder(moved.id, target.id)
      } catch (error) {
        notifyApiError(error, { messages: { default: '调整排序失败' } })
      } finally {
        await this.getList()
        this.loading = false
      }
    },
  },
}
