import assert from 'node:assert/strict'
import test from 'node:test'

// 弹窗、报错和下载的桩在共享 loader 里，调用记录仍经 globalThis.crudCalls / crudConfirm 传递
const { default: mixin } = await import('./workbenchCrudMixin.js')

function page({ api = {}, range = null, ...overrides } = {}) {
  let latest = 0
  const vm = {
    $options: { name: 'TestPage', workbenchApi: { exportName: '测试', ...api } },
    $data: { stats: { all: 0, done: 0 } },
    stats: { all: 0, done: 0 },
    list: [],
    total: 0,
    loading: false,
    canEdit: true,
    listQuery: { page: 1, limit: 20 },
    range,
    cleared: 0,
    flushed: 0,
    fetched: 0,
    discarded: [],
    beginListRequest() {
      const id = ++latest
      return () => id === latest
    },
    flushOk: true,
    async flushAllEdits() { this.flushed += 1; return this.flushOk },
    buildQuery() { return { page: this.listQuery.page } },
    acceptListRows() {},
    markListFetched() { this.fetched += 1 },
    normalizedSheetRange() { return this.range },
    clearSheetRange() { this.cleared += 1; this.range = null },
    async flushEditorForAction() { return true },
    discardDrawer(id) { this.discarded.push(id) },
    ...overrides,
  }
  for (const [name, fn] of Object.entries(mixin.methods)) if (!(name in overrides)) vm[name] = fn.bind(vm)
  return vm
}

function rows(count) {
  return Array.from({ length: count }, (_, index) => ({ id: index + 1 }))
}

test.beforeEach(() => {
  globalThis.crudCalls = []
  globalThis.crudConfirm = () => Promise.resolve()
})

test('getList 只认最后一次请求，填行、总数、页码和统计', async () => {
  const pending = []
  const vm = page({ api: { list: () => new Promise((resolve) => pending.push(resolve)) } })
  const first = vm.getList({ flushEditor: false })
  const second = vm.getList({ flushEditor: false })
  assert.equal(pending.length, 2)
  pending[1]({ items: rows(2), total: 2, page: 3, limit: 50, stats: { all: 2, extra: 9 } })
  assert.equal(await second, true)
  pending[0]({ items: rows(5), total: 5 })
  assert.equal(await first, false)
  assert.deepEqual(vm.list.map((row) => row.id), [1, 2])
  assert.equal(vm.total, 2)
  assert.deepEqual(vm.listQuery, { page: 3, limit: 50 })
  assert.deepEqual(vm.stats, { all: 2, done: 0 })
  assert.equal(vm.loading, false)
  assert.equal(vm.fetched, 1)
})

test('普通刷新清选区；静默刷新保留，行数变少越界才清', async () => {
  const vm = page({ api: { list: async () => ({ items: rows(3) }) }, range: { r1: 0, r2: 2 } })
  await vm.getList({ silent: true })
  assert.equal(vm.cleared, 0)
  vm.$options.workbenchApi.list = async () => ({ items: rows(2) })
  await vm.getList({ silent: true })
  assert.equal(vm.cleared, 1)
  vm.range = { r1: 0, r2: 0 }
  await vm.getList()
  assert.equal(vm.cleared, 2)
})

test('getList：编辑存不上就不拉列表，返回 false', async () => {
  let listed = 0
  const vm = page({ api: { list: async () => { listed += 1; return { items: rows(1) } } } })
  vm.flushOk = false
  assert.equal(await vm.getList(), false)
  assert.equal(listed, 0)
  assert.equal(vm.loading, false)
  assert.equal(await vm.getList({ flushEditor: false }), true)
  assert.equal(listed, 1)
})

test('getList 失败时报错并返回 false', async () => {
  const vm = page({ api: { list: async () => { throw new Error('x') }, errors: { load: { default: '加载失败了' } } } })
  assert.equal(await vm.getList(), false)
  assert.deepEqual(globalThis.crudCalls, [['error', '加载失败了']])
  assert.equal(vm.loading, false)
})

test('handleDelete：有阻止原因不弹确认；确认后删除、丢弃抽屉、刷新', async () => {
  const removed = []
  const vm = page({ api: { remove: async (id) => removed.push(id), list: async () => ({ items: [] }) } })
  vm.canEdit = false
  await vm.handleDelete({ id: 7 })
  assert.deepEqual(globalThis.crudCalls, [['warning', '您没有删除权限']])
  vm.canEdit = true
  globalThis.crudCalls = []
  await vm.handleDelete({ id: 7 })
  assert.deepEqual(removed, [7])
  assert.deepEqual(vm.discarded, [7])
  assert.deepEqual(globalThis.crudCalls.map(([kind]) => kind), ['confirm', 'success'])
  assert.equal(vm.flushed, 0)
  assert.equal(vm.fetched, 1)
})

test('handleDelete：取消确认不删；删除失败不丢抽屉不刷新', async () => {
  const vm = page({ api: { remove: async () => { throw new Error('x') }, list: async () => ({ items: [] }) } })
  globalThis.crudConfirm = () => Promise.reject(new Error('cancel'))
  await vm.handleDelete({ id: 1 })
  assert.deepEqual(globalThis.crudCalls.map(([kind]) => kind), ['confirm'])
  globalThis.crudConfirm = () => Promise.resolve()
  globalThis.crudCalls = []
  await vm.handleDelete({ id: 1 })
  assert.deepEqual(globalThis.crudCalls, [['confirm', '确认删除这条记录？删除后不可恢复。'], ['error', '删除失败']])
  assert.deepEqual(vm.discarded, [])
  assert.equal(vm.fetched, 0)
})

function rowSaver(api) {
  const log = []
  const vm = page({
    api,
    editingId: 1,
    editingRow: { id: 1, owner: '旧', remark: '旧' },
    drawerValueKeys: (key) => [key],
    cloneSheetValue: (value) => value,
    rowSavePayload: (row, fields) => ({ id: row.id, ...Object.fromEntries(fields.map((key) => [key, row[key]])) }),
    applySavedFields: (saved, fields) => log.push(['apply', saved.id, fields]),
    revertDrawerFields: (id, fields) => log.push(['revert', id, fields]),
    getList: async (options) => log.push(['reload', options]),
  })
  return { vm, log }
}

test('submitRowFields 成功：先同步抽屉副本，按 applyFields 回填', async () => {
  const sent = []
  const { vm, log } = rowSaver({ save: async (payload) => { sent.push(payload); return { id: 1 } } })
  const row = { id: 1, owner: '新', remark: '新' }
  assert.deepEqual(await vm.submitRowFields(row, ['owner'], { applyFields: null }), { id: 1 })
  assert.deepEqual(sent, [{ id: 1, owner: '新' }])
  assert.deepEqual(vm.editingRow, { id: 1, owner: '新', remark: '旧' })
  assert.deepEqual(log, [['apply', 1, null]])
})

test('submitRowFields 失败：报错、静默重载并还原抽屉字段', async () => {
  const { vm, log } = rowSaver({ save: async () => { throw new Error('x') }, errors: { save: { default: '存不上' } } })
  assert.equal(await vm.submitRowFields({ id: 1, owner: '新' }, ['owner'], { reload: { skipRemoteCheck: true } }), null)
  assert.deepEqual(globalThis.crudCalls, [['error', '存不上']])
  assert.deepEqual(log, [
    ['reload', { flushEditor: false, silent: true, skipRemoteCheck: true }],
    ['revert', 1, ['owner']],
  ])
})

test('handleListExport 用当前查询和 exportName 命名', async () => {
  const queries = []
  const vm = page({ api: { export: async (query) => queries.push(query) } })
  await vm.handleListExport()
  assert.deepEqual(globalThis.crudCalls, [['download', '测试_T.xlsx']])
  assert.deepEqual(queries, [{ page: 1 }])
})
