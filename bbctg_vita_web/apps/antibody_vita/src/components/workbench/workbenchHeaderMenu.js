import { defineComponent, h } from 'vue'
import { Filter } from '@element-plus/icons-vue'
import { ElIcon } from 'element-plus'

import { filterTargetOptions, targetOptionExtra } from '#/utils/targetFilterOptions'

/**
 * 通用表头菜单（类 Excel 自动筛选）。
 *
 * 页面需提供：
 * - headerMenuColumns：{ [key]: { type, label?, color?, values?, search?, top? } }，只有登记的列才有菜单。
 *   type: text | enum | csv | date | number；values: all | recent | search；search 指定搜索匹配规则；
 *   top 描述对应的顶部筛选器，见 synthesisColumns.js。
 *   两种视图列键不同但是同一字段时写 { alias: '主键' }，条件、排序都记在主键上。
 * - listQuery.sort_field / sort_dir：与队列排序共用。
 * - fetchHeaderValues(query)：返回 { items: [{ value, label?, count }], truncated }，空值用 ''。
 *   query 是列表条件加 field / value_keyword / value_limit / value_order；
 *   取值时去掉本列自己的条件（表头和顶部都去掉），日期区间参数按 `${key}_start/_end` 约定。
 * - buildQuery() 中合并 headerFilterPayload()；resetFilters() 中调 clearHeaderFilters()；getList()。
 *
 * 模板接入：
 * - <WorkbenchHeaderMenu v-bind="headerMenuBind" />，工具栏 <WorkbenchHeaderFilterChip v-bind="headerChipBind" />。
 * - WorkbenchDataTable 传 :header-menu-states 与 @header-menu="openHeaderMenu"；
 *   Excel 列表头 <WorkbenchHeaderLabel :label v-bind="headerMenuStates[key]" />，表格外层 @click="onSheetHeaderMenuClick"。
 * - 顶部控件 v-bind="headerTop(key, '占位文字')"，日期区间用 headerTop(key, '起始', 'startPlaceholder')。
 * - 「重置全部筛选」的显示条件里加 headerFiltering。
 *
 * 每个字段只有一份条件：顶部筛选器能表达的（选值、包含、日期区间）写回顶部，
 * 表达不了的（排除、空白、颜色、其他条件）留在表头，顶部显示“表头：…”。任一边改动都覆盖另一边。
 */
export const WorkbenchHeaderLabel = defineComponent({
  name: 'WorkbenchHeaderLabel',
  props: {
    label: { type: String, default: '' },
    sortDir: { type: String, default: '' },
    filtered: { type: Boolean, default: false },
  },
  render() {
    const active = Boolean(this.sortDir || this.filtered)
    return h('span', { class: ['wb-hf-label', { 'is-active': active }] }, [
      h('span', null, this.label),
      this.sortDir ? h('i', { class: 'wb-hf-mark' }, this.sortDir === 'desc' ? '↓' : '↑') : null,
      this.filtered ? h(ElIcon, { class: 'wb-hf-mark', title: '已筛选' }, () => h(Filter)) : null,
      active ? null : h('i', { class: 'wb-hf-caret' }, '▾'),
    ])
  },
})

/** 工具栏里的「表头筛选 N ×」：列被隐藏或滚出视野时，留在表头的条件在这里也能看到和清除。 */
export const WorkbenchHeaderFilterChip = defineComponent({
  name: 'WorkbenchHeaderFilterChip',
  props: {
    count: { type: Number, default: 0 },
    title: { type: String, default: '' },
  },
  emits: ['clear'],
  render() {
    if (!this.count) return null
    return h('button', { type: 'button', class: 'wb-hf-chip', title: this.title, onClick: () => this.$emit('clear') }, [
      `表头筛选 ${this.count}`,
      h('span', { class: 'wb-hf-chip-x' }, '×'),
    ])
  },
})

const CODE_SPLIT = /[,，\s]+/

const COND_TEXT = {
  contains: '包含',
  not_contains: '不包含',
  eq: '等于',
  neq: '不等于',
  starts: '开头是',
  ends: '结尾是',
  gte: '≥',
  lte: '≤',
  between: '介于',
  blank: '仅空白',
  not_blank: '仅非空',
}

/** 表头搜索与顶部下拉用同一套匹配：默认不区分大小写的包含，靶点按正式名、别名、编号匹配。 */
const SEARCH_MATCHERS = {
  default(items, keyword) {
    const text = keyword.toLowerCase()
    return items.filter((item) => item.value !== ''
      && [item.value, item.label].some((word) => word != null && String(word).toLowerCase().includes(text)))
  },
  target(items, keyword) {
    const options = items
      .filter((item) => item.value !== '')
      .map((item) => ({
        ...item,
        label: item.label || String(item.value),
        aliases: item.aliases || [],
        codes: item.codes || [],
      }))
    return filterTargetOptions(options, keyword).map((item) => ({ ...item, hint: targetOptionExtra(item, keyword) }))
  },
}

function listTerms(value) {
  if (Array.isArray(value)) return value.map((item) => String(item ?? '').trim()).filter(Boolean)
  const text = String(value ?? '').trim()
  return text ? [text] : []
}

function storedTerms(list) {
  if (!list.length) return ''
  return list.length === 1 ? list[0] : list.slice()
}

function onlyKeys(state, keys) {
  const own = Object.keys(state || {})
  return own.length > 0 && own.every((key) => keys.includes(key))
}

export default {
  data() {
    return {
      headerFilters: {},
      headerMenu: { key: '', anchor: null },
    }
  },
  computed: {
    headerMenuColumn() {
      const key = this.headerMenu.key
      const config = key ? this.headerMenuColumns?.[key] : null
      if (!config) return null
      return { ...config, key, label: this.headerMenuLabel(key) }
    },
    headerMenuStates() {
      const states = {}
      for (const column of Object.keys(this.headerMenuColumns || {})) {
        const key = this.headerKey(column)
        states[column] = {
          sortDir: this.headerSortDir(key),
          filtered: Boolean(this.headerFilters[key] || this.headerTopState(key)),
        }
      }
      return states
    },
    headerMenuFilter() {
      return this.headerMenu.key ? this.headerFilterState(this.headerMenu.key) : null
    },
    headerFilterCount() {
      return Object.keys(this.headerFilters).length
    },
    /** 当前排序来自表头菜单（队列排序等页面自有的排序模式不算）。 */
    headerSortActive() {
      return Boolean(this.headerMenuColumns?.[this.listQuery?.sort_field])
    },
    /** 有表头条件或表头排序：「重置全部筛选」应当出现。 */
    headerFiltering() {
      return this.headerFilterCount > 0 || this.headerSortActive
    },
    headerMenuBind() {
      const column = this.headerMenuColumn
      return {
        visible: Boolean(column),
        anchor: this.headerMenu.anchor,
        column,
        filter: this.headerMenuFilter,
        sortDir: column ? this.headerSortDir(column.key) : '',
        loadValues: this.loadHeaderMenuValues,
        searchValues: this.headerMenuSearch,
        externalHint: column ? this.headerExternalHint(column.key) : '',
        onSort: this.onHeaderMenuSort,
        onApply: this.onHeaderMenuApply,
        onClose: this.closeHeaderMenu,
        onClearExternal: this.clearHeaderExternal,
      }
    },
    headerChipBind() {
      return {
        count: this.headerFilterCount,
        title: this.headerFilterCount ? this.headerFiltersTitle() : '',
        onClear: this.resetHeaderFilters,
      }
    },
  },
  created() {
    for (const [key, config] of Object.entries(this.headerMenuColumns || {})) {
      if (!config.top) continue
      this.$watch(
        () => JSON.stringify(this.headerTopRaw(key) ?? ''),
        (raw) => {
          if (raw !== '""' && raw !== '[]' && this.headerFilters[key]) this.dropHeaderFilter(key)
        },
      )
    }
  },
  methods: {
    headerKey(column) {
      return this.headerMenuColumns?.[column]?.alias || column
    },
    headerMenuLabel(key) {
      if (this.headerMenuColumns?.[key]?.label) return this.headerMenuColumns[key].label
      const column = (this.workbenchColumns || []).find((item) => item.key === key)
        || (this.sheetColumns || []).find((item) => item.key === key)
      return column?.label || key
    },
    headerSortDir(key) {
      if (this.listQuery?.sort_field !== key) return ''
      return this.listQuery.sort_dir === 'desc' ? 'desc' : 'asc'
    },
    headerTopRaw(key) {
      const top = this.headerMenuColumns?.[key]?.top
      if (!top) return null
      return top.range ? this[top.range] : this.listQuery?.[top.query]
    },
    /** 顶部筛选器当前值换算成表头状态；顶部独有的选项返回 hint。 */
    headerTopState(key) {
      const top = this.headerMenuColumns?.[key]?.top
      if (!top) return null
      if (top.range) {
        const range = this[top.range]
        if (!Array.isArray(range) || range.length !== 2 || !range[0]) return null
        return { state: { condition: { op: 'between', value: range[0], value2: range[1] } } }
      }
      const raw = this.listQuery?.[top.query]
      if (top.kind === 'contains') {
        const terms = listTerms(raw)
        if (terms.length > 1) return { hint: terms.join('、') }
        return terms.length ? { state: { condition: { op: 'contains', value: terms[0] } } } : null
      }
      if (top.kind === 'codes' || top.kind === 'tokens') {
        const codes = String(raw ?? '').split(CODE_SPLIT).map((item) => item.trim()).filter(Boolean)
        if (!codes.length) return null
        if (codes.length === 1 && top.kind === 'codes') return { state: { condition: { op: 'contains', value: codes[0] } } }
        return { state: { values: codes } }
      }
      const terms = listTerms(raw)
      if (!terms.length) return null
      const only = terms.filter((item) => (top.topOnly || []).includes(item))
      if (only.length) return { hint: terms.join('、') }
      return { state: { values: terms } }
    },
    headerFilterState(key) {
      return this.headerFilters[key] || this.headerTopState(key)?.state || null
    },
    /** 能用顶部筛选器表达就写回顶部并返回 true。 */
    headerWriteTop(key, state) {
      const top = this.headerMenuColumns?.[key]?.top
      if (!top || !state) return false
      const cond = state.condition
      if (top.range) {
        if (!onlyKeys(state, ['condition']) || cond.op !== 'between' || !cond.value || !cond.value2) return false
        this[top.range] = [cond.value, cond.value2]
        return true
      }
      if (top.kind === 'contains') {
        if (!onlyKeys(state, ['condition']) || cond.op !== 'contains' || !String(cond.value).trim()) return false
        this.listQuery[top.query] = String(cond.value).trim()
        return true
      }
      if (top.kind === 'codes') {
        if (onlyKeys(state, ['condition']) && cond.op === 'contains' && !CODE_SPLIT.test(String(cond.value).trim())) {
          this.listQuery[top.query] = String(cond.value).trim()
          return true
        }
        if (!onlyKeys(state, ['values']) || !state.values.length || state.values.includes('')) return false
        this.listQuery[top.query] = state.values.join(',')
        return true
      }
      if (top.kind === 'tokens') {
        if (!onlyKeys(state, ['values']) || !state.values.length) return false
        if (state.values.some((value) => !String(value).trim() || CODE_SPLIT.test(String(value)))) return false
        this.listQuery[top.query] = state.values.join(',')
        return true
      }
      if (!onlyKeys(state, ['values']) || !state.values.length || state.values.includes('')) return false
      this.listQuery[top.query] = storedTerms(state.values.map(String))
      return true
    },
    headerClearTop(key) {
      const top = this.headerMenuColumns?.[key]?.top
      if (!top) return
      if (top.range) this[top.range] = []
      else this.listQuery[top.query] = top.kind ? '' : storedTerms([])
    },
    dropHeaderFilter(key) {
      const next = { ...this.headerFilters }
      delete next[key]
      this.headerFilters = next
    },
    headerExternalHint(key) {
      return this.headerTopState(key)?.hint || ''
    },
    clearHeaderExternal() {
      this.headerClearTop(this.headerMenu.key)
      this.reloadAfterHeaderChange()
    },
    reloadAfterHeaderChange() {
      this.listQuery.page = 1
      this.closeHeaderMenu()
      this.getList()
    },
    headerFilterText(key) {
      const state = this.headerFilters[key]
      if (!state) return ''
      const parts = []
      if (state.values) parts.push(state.values.length === 1 ? (state.values[0] || '(空白)') : `选 ${state.values.length} 项`)
      if (state.exclude?.length) parts.push(`排除 ${state.exclude.length} 项`)
      if (state.condition?.op) {
        const { op, value, value2 } = state.condition
        const text = COND_TEXT[op] || op
        parts.push(op === 'between' ? `${value || '…'} 至 ${value2 || '…'}` : value ? `${text} ${value}` : text)
      }
      if (state.colors?.length) parts.push('按颜色')
      return parts.join('，')
    },
    /** 顶部控件的绑定：条件留在表头时变蓝框，占位文字显示条件摘要。 */
    headerTop(key, base, prop = 'placeholder') {
      const text = this.headerFilterText(key)
      return { [prop]: text ? `表头：${text}` : base, class: text ? 'is-header-filtered' : '' }
    },
    headerCellClass(key) {
      return this.headerMenuStates[key] ? 'wb-hf-cell' : ''
    },
    /** 打开中的高亮直接改锚点 class：放进 headerMenuStates 会让整张表的表头跟着重渲染。 */
    openHeaderMenu(column, anchor) {
      const key = this.headerKey(column)
      if (!this.headerMenuColumns?.[key] || !anchor) return
      if (this.headerMenu.key === key) {
        this.closeHeaderMenu()
        return
      }
      this.headerMenu.anchor?.classList.remove('is-open')
      anchor.classList.add('is-open')
      this.headerMenu = { key, anchor }
    },
    closeHeaderMenu() {
      this.headerMenu.anchor?.classList.remove('is-open')
      this.headerMenu = { key: '', anchor: null }
    },
    onHeaderMenuSort(dir) {
      const key = this.headerMenu.key
      if (!key) return
      if (dir) {
        this.listQuery.sort_field = key
        this.listQuery.sort_dir = dir
      } else if (this.listQuery.sort_field === key) {
        this.listQuery.sort_field = ''
        this.listQuery.sort_dir = ''
      }
      this.reloadAfterHeaderChange()
    },
    onHeaderMenuApply(state) {
      const key = this.headerMenu.key
      if (!key) return
      this.dropHeaderFilter(key)
      this.headerClearTop(key)
      if (state && !this.headerWriteTop(key, state)) {
        this.headerFilters = { ...this.headerFilters, [key]: state }
      }
      this.reloadAfterHeaderChange()
    },
    headerMenuSearch(items, keyword) {
      const matcher = SEARCH_MATCHERS[this.headerMenuColumn?.search] || SEARCH_MATCHERS.default
      return matcher(items, keyword)
    },
    loadHeaderMenuValues(key, { keyword = '', limit = 200, order = 'value' } = {}) {
      const query = this.buildQuery()
      delete query.page
      delete query.limit
      const top = this.headerMenuColumns?.[key]?.top
      if (top?.range) {
        delete query[`${key}_start`]
        delete query[`${key}_end`]
      } else if (top?.query) {
        delete query[top.query]
      }
      return this.fetchHeaderValues({ ...query, field: key, value_keyword: keyword, value_limit: limit, value_order: order })
    },
    headerFilterPayload() {
      return Object.entries(this.headerFilters).map(([field, state]) => ({ field, ...state }))
    },
    clearHeaderFilters() {
      this.headerFilters = {}
    },
    /** 恢复本地保存的表头条件：只认当前登记且不是别名的列。 */
    restoreHeaderFilters(saved) {
      if (!saved || typeof saved !== 'object') return
      const next = {}
      for (const [key, state] of Object.entries(saved)) {
        const config = this.headerMenuColumns?.[key]
        if (config && !config.alias && state && typeof state === 'object') next[key] = state
      }
      this.headerFilters = next
    },
    /** 留在表头的条件逐列列出，供工具栏胶囊悬停查看。 */
    headerFiltersTitle() {
      const lines = Object.keys(this.headerFilters).map((key) => `${this.headerMenuLabel(key)}：${this.headerFilterText(key)}`)
      return `${lines.join('\n')}\n点击清除全部表头筛选`
    },
    resetHeaderFilters() {
      this.clearHeaderFilters()
      this.reloadAfterHeaderChange()
    },
    onSheetHeaderMenuClick(event) {
      if (event.shiftKey || event.button !== 0) return
      // 这次是按住或拖动选了整列，松开不算单击
      if (this._sheetHeaderSelected) return
      const hit = this.hitSheetHeader?.(event.target)
      if (!hit || !this.headerMenuColumns?.[hit.field]) return
      // 开菜单时清掉旧选区，免得关菜单后 Delete/粘贴落到别处
      this.clearSheetRange?.()
      this.openHeaderMenu(hit.field, event.target.closest('.vxe-header--column'))
    },
  },
}
