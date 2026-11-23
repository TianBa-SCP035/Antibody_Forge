import { ElMessage, ElMessageBox } from 'element-plus'

import { notifyApiError } from '#/api/errors'
import { isUnauthorizedError } from '#/utils/auth-session'
import { downloadListExcel, excelTimestamp } from '#/utils/downloadExcel'

/**
 * 工作台的列表、删除、导出默认实现；多格保存的默认实现在 workbenchExcelMixin，同样读 workbenchApi.saveBatch。
 * 页面在组件选项写 workbenchApi：
 * - list(query)：列表接口，返回 { items, total, page, limit, stats }。
 * - save(payload)：保存一行（submitRowFields 默认用它），返回保存后的行。
 * - saveBatch({ items })：批量保存，返回 { items }。
 * - remove(id)：删除一行。
 * - export(query)、exportName：列表导出和文件名前缀。
 * - columnValues(query)：表头筛选的取值接口（fetchHeaderValues 默认用它）。
 * - reorder(movedId, targetId)：拖行排队（workbenchQueueSortMixin 用）。
 * - errors：{ load, remove, export, save }，各环节失败时交给 notifyApiError 的 messages，不写用通用文案。
 * 钩子：onListLoaded(data, options) 列表回来后（默认填 stats）；deleteBlockReason(row) 不能删的原因；deleteConfirmText(row) 删除确认文案。
 * 逐字段保存（saveRowField）的提交走 submitRowFields：成功回填，失败提示、静默刷新并退回抽屉副本。
 * 依赖 listPageMixin、workbenchDrawerMixin、workbenchExcelMixin；页面提供 list、total、loading、listQuery、buildQuery。
 * 列表行原样使用接口返回值：数组、默认值等由后端序列化保证，前端不再补形。
 */
export default {
  created() {
    if (import.meta.env.DEV && !this.$options.workbenchApi) {
      console.warn(`[workbenchCrudMixin] ${this.$options.name} 没有声明 workbenchApi`)
    }
    if (import.meta.env.DEV && typeof this.buildQuery !== 'function') {
      console.warn(`[workbenchCrudMixin] ${this.$options.name} 没有实现 buildQuery，列表和导出拿不到查询条件`)
    }
  },
  methods: {
    /**
     * 拉列表：先存完所有编辑（有存不上的就不刷新，失败已由保存处提示），只认最后一次请求；返回是否成功。
     * 普通刷新（筛选、翻页、删除后）清空表格选区；silent 静默刷新（保存后、失败回滚）保留选区，行数变少越界时才清空。
     */
    async getList(options = {}) {
      const { flushEditor = true, silent = false } = options
      const api = this.$options.workbenchApi
      const isLatest = this.beginListRequest()
      if (!silent) this.loading = true
      try {
        if (flushEditor && !await this.flushAllEdits()) return false
        if (!isLatest()) return false
        const data = await api.list(this.buildQuery())
        if (!isLatest()) return false
        this.list = data?.items || []
        this.acceptListRows()
        this.total = data?.total || 0
        if (data?.page) this.listQuery.page = data.page
        if (data?.limit) this.listQuery.limit = data.limit
        this.onListLoaded(data, options)
        this.markListFetched()
        const range = this.normalizedSheetRange()
        if (!silent || (range && range.r2 >= this.list.length)) this.clearSheetRange()
        return true
      } catch (error) {
        if (!isLatest()) return false
        notifyApiError(error, { messages: api.errors?.load || { default: '加载列表失败' } })
        return false
      } finally {
        if (isLatest()) this.loading = false
      }
    },
    /** 列表回来后的钩子；默认按页面 data.stats 已有的键取接口统计，缺的记 0。 */
    onListLoaded(data) {
      if (!this.$data.stats) return
      this.stats = Object.fromEntries(Object.keys(this.stats).map((key) => [key, data?.stats?.[key] || 0]))
    },
    async handleDelete(row) {
      const blocked = this.deleteBlockReason(row)
      if (blocked) {
        ElMessage.warning(blocked)
        return
      }
      try {
        await ElMessageBox.confirm(this.deleteConfirmText(row), '删除确认', {
          type: 'warning',
          confirmButtonText: '删除',
          cancelButtonText: '取消',
        })
      } catch {
        return
      }
      if (!await this.flushEditorForAction(row)) return
      const api = this.$options.workbenchApi
      try {
        await api.remove(row.id)
      } catch (error) {
        notifyApiError(error, { messages: api.errors?.remove || { default: '删除失败' } })
        return
      }
      this.discardDrawer(row.id)
      ElMessage.success('已删除')
      await this.getList({ flushEditor: false })
    },
    /**
     * 提交一行的这些字段。save 返回空值表示取消（如确认框点了取消），按失败处理。
     * 表格里改的正是抽屉打开的那一行时，先把值同步到抽屉副本。
     * 登录失效时不刷新、不退回，抽屉里的值留到重新登录后由兜底补存提交。
     */
    async submitRowFields(row, fields, options = {}) {
      const api = this.$options.workbenchApi
      const {
        save = api.save,
        messages = api.errors?.save || { default: '保存失败' },
        applyFields = fields,
        reload = {},
      } = options
      if (this.editingId === row.id && this.editingRow && row !== this.editingRow) {
        fields.flatMap((key) => this.drawerValueKeys(key)).forEach((key) => {
          this.editingRow[key] = this.cloneSheetValue(row[key])
        })
      }
      let saved = null
      try {
        saved = await save(this.rowSavePayload(row, fields))
      } catch (error) {
        notifyApiError(error, { messages })
        if (isUnauthorizedError(error)) return null
      }
      if (!saved) {
        await this.getList({ flushEditor: false, silent: true, ...reload })
        this.revertDrawerFields(row.id, fields)
        return null
      }
      this.applySavedFields(saved, applyFields)
      return saved
    },
    fetchHeaderValues(query) {
      return this.$options.workbenchApi.columnValues(query)
    },
    deleteBlockReason() {
      return this.canEdit ? '' : '您没有删除权限'
    },
    deleteConfirmText() {
      return '确认删除这条记录？删除后不可恢复。'
    },
    async handleListExport() {
      const api = this.$options.workbenchApi
      try {
        await downloadListExcel(() => api.export(this.buildQuery()), `${api.exportName}_${excelTimestamp()}.xlsx`)
      } catch (error) {
        notifyApiError(error, { messages: api.errors?.export || { default: '列表导出失败' } })
      }
    },
  },
}
