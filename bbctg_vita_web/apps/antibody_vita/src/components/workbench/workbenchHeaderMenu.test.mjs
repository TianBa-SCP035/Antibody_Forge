import assert from 'node:assert/strict'
import { register } from 'node:module'
import test from 'node:test'

// node 不认 vite 的 #/ 别名；Element Plus 只在渲染函数里用到，这里换成空模块。
const SRC = new URL('../../', import.meta.url).href
register(`data:text/javascript,${encodeURIComponent(`
const STUBS = {
  'element-plus': 'export const ElIcon = {}',
  '@element-plus/icons-vue': 'export const Filter = {}',
}
export async function resolve(specifier, context, next) {
  if (STUBS[specifier]) return { url: 'data:text/javascript,' + encodeURIComponent(STUBS[specifier]), shortCircuit: true }
  if (specifier.startsWith('#/')) return next(new URL(specifier.slice(2) + '.js', ${JSON.stringify(SRC)}).href, context)
  return next(specifier, context)
}`)}`)

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

test('a value pick the top select can express is written to the top select', () => {
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

test('conditions the top cannot express stay in the header and clear the top', () => {
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

test('applying in the header replaces the earlier header or top condition', () => {
  const vm = page()
  apply(vm, 'remark', { condition: { op: 'not_contains', value: '旧' } })
  apply(vm, 'remark', { condition: { op: 'contains', value: ' 新 ' } })
  assert.equal(vm.listQuery.remark, '新')
  assert.deepEqual(vm.headerFilters, {})

  apply(vm, 'remark', null)
  assert.equal(vm.listQuery.remark, '')
  assert.equal(vm.headerFilterState('remark'), null)
})

test('code tops split on commas and spaces into a value pick', () => {
  const vm = page({ batch: 'B1, B2' })
  assert.deepEqual(vm.headerFilterState('batch'), { values: ['B1', 'B2'] })
  vm.listQuery.batch = 'B1'
  assert.deepEqual(vm.headerFilterState('batch'), { condition: { op: 'contains', value: 'B1' } })

  apply(vm, 'batch', { values: ['B3', 'B4'] })
  assert.equal(vm.listQuery.batch, 'B3,B4')
  apply(vm, 'batch', { condition: { op: 'contains', value: 'B5 B6' } })
  assert.equal(vm.listQuery.batch, '')
  assert.deepEqual(vm.headerFilters.batch, { condition: { op: 'contains', value: 'B5 B6' } })
})

test('token tops are always an exact value pick, even for a single value', () => {
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

test('the default value search also matches labels', () => {
  const vm = page()
  vm.headerMenu = { key: 'pm', anchor: null }
  const items = [{ value: 'TITER', label: '效价' }, { value: 'PCR' }, { value: '', count: 2 }]
  assert.deepEqual(vm.headerMenuSearch(items, '效价').map((item) => item.value), ['TITER'])
  assert.deepEqual(vm.headerMenuSearch(items, 'pc').map((item) => item.value), ['PCR'])
})

test('a multi-term contains top is shown as a hint instead of a header state', () => {
  const vm = page({ remark: ['甲', '乙'] })
  assert.equal(vm.headerFilterState('remark'), null)
  assert.equal(vm.headerExternalHint('remark'), '甲、乙')
  assert.equal(vm.headerMenuStates.remark.filtered, true)
})

test('date ranges map to between in both directions; open ranges stay in the header', () => {
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

test('columns without a top keep every condition in the header', () => {
  const vm = page()
  apply(vm, 'pm', { values: ['张三'] })
  assert.deepEqual(vm.headerFilters.pm, { values: ['张三'] })
  assert.deepEqual(vm.headerTop('pm', '项目经理'), { placeholder: '表头：张三', class: 'is-header-filtered' })
})

test('loading values drops the column own top condition and keeps the other filters', () => {
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

test('header sort counts as filtering only for registered columns', () => {
  const vm = page({ sort_field: 'status', sort_dir: 'desc' })
  assert.equal(vm.headerSortActive, true)
  assert.equal(vm.headerFiltering, true)
  assert.equal(vm.headerMenuStates.status.sortDir, 'desc')

  vm.listQuery.sort_field = 'queue'
  assert.equal(vm.headerSortActive, false)
  assert.equal(vm.headerFiltering, false)
})
