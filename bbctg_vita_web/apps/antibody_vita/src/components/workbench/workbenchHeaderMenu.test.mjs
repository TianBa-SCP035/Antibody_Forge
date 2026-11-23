import assert from 'node:assert/strict'
import test from 'node:test'

const { default: mixin } = await import('./workbenchHeaderMenu.js')

const COLUMNS = {
  status: { type: 'enum', top: { query: 'status' } },
  remark: { type: 'text', top: { query: 'remark', kind: 'contains' } },
  batch: { type: 'text', top: { query: 'batch', kind: 'codes' } },
  instrument_on: { type: 'date', top: { range: 'instrumentRange' } },
  plates: { type: 'csv', top: { query: 'plates', kind: 'tokens' } },
  pm: { type: 'enum' },
}

function page(listQuery = {}) {
  const vm = {
    ...mixin.data(),
    ...mixin.methods,
    headerMenuColumns: COLUMNS,
    listQuery: { status: '', remark: '', batch: '', plates: '', page: 3, limit: 50, ...listQuery },
    instrumentRange: [],
    loads: 0,
    getList() { this.loads += 1 },
    buildQuery() {
      const [start, end] = this.instrumentRange
      return {
        ...this.listQuery,
        instrument_on_start: start || '',
        instrument_on_end: end || '',
        field_filters: this.headerFilterPayload(),
      }
    },
  }
  for (const [name, getter] of Object.entries(mixin.computed)) {
    Object.defineProperty(vm, name, { get: getter })
  }
  return vm
}

function apply(vm, key, state) {
  vm.headerMenu = { key, anchor: null }
  vm.onHeaderMenuApply(state)
}

test('顶部下拉能表达的值选直接写回顶部下拉', () => {
  const vm = page()
  apply(vm, 'status', { values: ['进行中'] })
  assert.equal(vm.listQuery.status, '进行中')
  assert.deepEqual(vm.headerFilters, {})
  assert.equal(vm.listQuery.page, 1)
  assert.equal(vm.loads, 1)

  apply(vm, 'status', { values: ['进行中', '已完成'] })
  assert.deepEqual(vm.listQuery.status, ['进行中', '已完成'])
  assert.deepEqual(vm.headerFilterState('status'), { values: ['进行中', '已完成'] })
})

test('顶部表达不了的条件留在表头并清空顶部', () => {
  const vm = page({ status: '进行中' })
  apply(vm, 'status', { values: ['进行中', ''] })
  assert.equal(vm.listQuery.status, '')
  assert.deepEqual(vm.headerFilters.status, { values: ['进行中', ''] })
  assert.deepEqual(vm.headerTop('status', '状态'), { placeholder: '表头：选 2 项', class: 'is-header-filtered' })
  assert.deepEqual(vm.headerFilterPayload(), [{ field: 'status', values: ['进行中', ''] }])
  assert.equal(vm.headerFilterCount, 1)

  apply(vm, 'remark', { condition: { op: 'not_contains', value: '旧' } })
  assert.equal(vm.listQuery.remark, '')
  assert.deepEqual(vm.headerTop('remark', '备注'), { placeholder: '表头：不包含 旧', class: 'is-header-filtered' })
})

test('在表头应用会替换先前的表头或顶部条件', () => {
  const vm = page()
  apply(vm, 'remark', { condition: { op: 'not_contains', value: '旧' } })
  apply(vm, 'remark', { condition: { op: 'contains', value: ' 新 ' } })
  assert.equal(vm.listQuery.remark, '新')
  assert.deepEqual(vm.headerFilters, {})

  apply(vm, 'remark', null)
  assert.equal(vm.listQuery.remark, '')
  assert.equal(vm.headerFilterState('remark'), null)
})

test('编码顶部框：多值回填顶部框，单值或含分隔符的编码留在表头精确筛选', () => {
  const vm = page({ batch: 'B1, B2' })
  assert.deepEqual(vm.headerFilterState('batch'), { values: ['B1', 'B2'] })
  vm.listQuery.batch = 'B1'
  assert.deepEqual(vm.headerFilterState('batch'), { condition: { op: 'contains', value: 'B1' } })

  apply(vm, 'batch', { values: ['B3', 'B4'] })
  assert.equal(vm.listQuery.batch, 'B3,B4')
  apply(vm, 'batch', { condition: { op: 'contains', value: 'B5 B6' } })
  assert.equal(vm.listQuery.batch, '')
  assert.deepEqual(vm.headerFilters.batch, { condition: { op: 'contains', value: 'B5 B6' } })

  apply(vm, 'batch', { values: ['P1'] })
  assert.equal(vm.listQuery.batch, '')
  assert.deepEqual(vm.headerFilters.batch, { values: ['P1'] })

  apply(vm, 'batch', { values: ['批次 A', 'B2'] })
  assert.equal(vm.listQuery.batch, '')
  assert.deepEqual(vm.headerFilters.batch, { values: ['批次 A', 'B2'] })
})

test('令牌顶部框始终按精确值选，单值也不例外', () => {
  const vm = page({ plates: 'P1' })
  assert.deepEqual(vm.headerFilterState('plates'), { values: ['P1'] })
  vm.listQuery.plates = 'P1, P2'
  assert.deepEqual(vm.headerFilterState('plates'), { values: ['P1', 'P2'] })

  apply(vm, 'plates', { values: ['P3', 'P4'] })
  assert.equal(vm.listQuery.plates, 'P3,P4')
  apply(vm, 'plates', { values: ['P5', ''] })
  assert.equal(vm.listQuery.plates, '')
  assert.deepEqual(vm.headerFilters.plates, { values: ['P5', ''] })
  apply(vm, 'plates', { values: ['A B'] })
  assert.deepEqual(vm.headerFilters.plates, { values: ['A B'] })
})

test('默认的值搜索同时匹配标签', () => {
  const vm = page()
  vm.headerMenu = { key: 'pm', anchor: null }
  const items = [{ value: 'TITER', label: '效价' }, { value: 'PCR' }, { value: '', count: 2 }]
  assert.deepEqual(vm.headerMenuSearch(items, '效价').map((item) => item.value), ['TITER'])
  assert.deepEqual(vm.headerMenuSearch(items, 'pc').map((item) => item.value), ['PCR'])
})

test('多词包含的顶部条件只作提示，不成表头状态', () => {
  const vm = page({ remark: ['甲', '乙'] })
  assert.equal(vm.headerFilterState('remark'), null)
  assert.equal(vm.headerExternalHint('remark'), '甲、乙')
  assert.equal(vm.headerMenuStates.remark.filtered, true)
})

test('日期范围双向映射为区间，开区间留在表头', () => {
  const vm = page()
  vm.instrumentRange = ['2026-10-01', '2026-10-31']
  assert.deepEqual(vm.headerFilterState('instrument_on'), {
    condition: { op: 'between', value: '2026-10-01', value2: '2026-10-31' },
  })

  apply(vm, 'instrument_on', { condition: { op: 'between', value: '2026-11-01', value2: '2026-11-02' } })
  assert.deepEqual(vm.instrumentRange, ['2026-11-01', '2026-11-02'])

  apply(vm, 'instrument_on', { condition: { op: 'gte', value: '2026-11-01' } })
  assert.deepEqual(vm.instrumentRange, [])
  assert.deepEqual(vm.headerFilters.instrument_on, { condition: { op: 'gte', value: '2026-11-01' } })
})

test('没有顶部框的列，所有条件都留在表头', () => {
  const vm = page()
  apply(vm, 'pm', { values: ['张三'] })
  assert.deepEqual(vm.headerFilters.pm, { values: ['张三'] })
  assert.deepEqual(vm.headerTop('pm', '项目经理'), { placeholder: '表头：张三', class: 'is-header-filtered' })
})

test('加载候选值时去掉本列顶部条件，保留其他筛选', () => {
  const vm = page({ status: '进行中', remark: '新' })
  vm.instrumentRange = ['2026-10-01', '2026-10-31']
  vm.headerFilters = { pm: { values: ['张三'] } }
  const calls = []
  vm.fetchHeaderValues = (query) => calls.push(query)

  vm.loadHeaderMenuValues('status')
  assert.equal('status' in calls[0], false)
  assert.equal('page' in calls[0], false)
  assert.equal(calls[0].remark, '新')
  assert.equal(calls[0].field, 'status')
  assert.deepEqual(calls[0].field_filters, [{ field: 'pm', values: ['张三'] }])

  vm.loadHeaderMenuValues('instrument_on', { keyword: '2026', limit: 20, order: 'count' })
  assert.equal('instrument_on_start' in calls[1], false)
  assert.equal('instrument_on_end' in calls[1], false)
  assert.equal(calls[1].status, '进行中')
  assert.deepEqual([calls[1].value_keyword, calls[1].value_limit, calls[1].value_order], ['2026', 20, 'count'])
})

test('表头排序只对已注册列算作筛选中', () => {
  const vm = page({ sort_field: 'status', sort_dir: 'desc' })
  assert.equal(vm.headerSortActive, true)
  assert.equal(vm.headerFiltering, true)
  assert.equal(vm.headerMenuStates.status.sortDir, 'desc')

  vm.listQuery.sort_field = 'queue'
  assert.equal(vm.headerSortActive, false)
  assert.equal(vm.headerFiltering, false)
})
