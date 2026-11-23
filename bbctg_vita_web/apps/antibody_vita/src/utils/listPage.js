import { createLatestRequest } from './latestRequest'
import { loadListFilters, saveListFilters } from './listFilterStorage'
import { shouldRefreshTabData } from './staleTabRefresh'

/**
 * 选项式列表页骨架：筛选暂存、只认最后一次列表请求、切回时判断数据是否过期、查询与翻页。
 *
 * 页面提供 listQuery（page、limit、sort_field、sort_dir 和各筛选项）与 getList()：
 * - getList 开头 `const isLatest = this.beginListRequest()`，响应回来先 `if (!isLatest()) return`，成功后 `this.markListFetched()`。
 * - 要记住筛选就在组件选项里写 listFilterKey。listQuery（含排序、页码）和表头筛选自动存取，
 *   别的筛选（日期区间等）由 listFilterExtras() 返回、restoreListFilterExtras(state) 读回。
 * - 进页和切回时怎么拉数据各页不同，这里不自动拉；activated 里用 isListDataStale() 判断。
 */
export const listPageMixin = {
  data() {
    return {
      tabDataFetchedAt: 0,
    }
  },
  created() {
    this.listRequest = createLatestRequest()
    this.restoreListFilters()
  },
  deactivated() {
    this.persistListFilters()
  },
  beforeUnmount() {
    this.persistListFilters()
    this.listRequest.cancel()
  },
  methods: {
    beginListRequest() {
      return this.listRequest.begin()
    },
    markListFetched() {
      this.tabDataFetchedAt = Date.now()
    },
    isListDataStale() {
      return shouldRefreshTabData(this.tabDataFetchedAt)
    },
    handleFilter() {
      this.listQuery.page = 1
      this.getList()
    },
    handleCurrentChange(page) {
      this.listQuery.page = page
      this.getList()
    },
    handleSizeChange(limit) {
      this.listQuery.limit = limit
      this.listQuery.page = 1
      this.getList()
    },
    listFilterExtras() {
      return {}
    },
    restoreListFilterExtras() {},
    persistListFilters() {
      const key = this.$options.listFilterKey
      if (!key) return
      saveListFilters(key, {
        ...this.listFilterExtras(),
        listQuery: { ...this.listQuery },
        headerFilters: this.headerFilters,
      })
    },
    restoreListFilters() {
      const key = this.$options.listFilterKey
      const state = key ? loadListFilters(key) : null
      if (!state) return
      if (state.listQuery && typeof state.listQuery === 'object') Object.assign(this.listQuery, state.listQuery)
      this.restoreHeaderFilters?.(state.headerFilters)
      this.restoreListFilterExtras(state)
    },
  },
}
