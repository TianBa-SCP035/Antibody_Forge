import assert from 'node:assert/strict'
import { createRequire, register } from 'node:module'
import test from 'node:test'
import { pathToFileURL } from 'node:url'

// Vite resolves extensionless .ts imports, the `#/` alias and xlsx's ESM build (which exports CFB); node needs them spelled out.
// constants.ts reads import.meta.env; the page DOM, the host session and the weather key are stubbed.
const XLSX_ESM = pathToFileURL(createRequire(import.meta.url).resolve('xlsx').replace(/xlsx\.js$/, 'xlsx.mjs')).href
const stub = (code) => ({ url: 'data:text/javascript,' + encodeURIComponent(code), shortCircuit: true })
const STUBS = {
  './pageTable': 'export const readPageTables = () => globalThis.__ffTables || []',
  './session': "export const currentUserKey = () => 'u1'; export const menuPages = () => []; export const openMenuPage = async () => false",
  '#/constants/storageKeys': "export const WEATHER_CACHE_KEY = 'weather'",
}
register(`data:text/javascript,${encodeURIComponent(`
const STUBS = ${JSON.stringify(Object.fromEntries(Object.entries(STUBS).map(([k, v]) => [k, stub(v)])))}
export async function resolve(specifier, context, next) {
  if (specifier === 'xlsx') return next(${JSON.stringify(XLSX_ESM)}, context)
  if (STUBS[specifier]) return STUBS[specifier]
  if (specifier.startsWith('./') && !/\\.\\w+$/.test(specifier) && context.parentURL?.endsWith('.ts')) return next(specifier + '.ts', context)
  return next(specifier, context)
}
export async function load(url, context, next) {
  const r = await next(url, context)
  if (!url.endsWith('/fatfish/constants.ts')) return r
  return { ...r, source: String(r.source).replaceAll('import.meta.env', '({ BASE_URL: "/" })'), shortCircuit: true }
}`)}`)

const store = new Map()
globalThis.localStorage = {
  getItem: (k) => (store.has(k) ? store.get(k) : null),
  setItem: (k, v) => store.set(k, String(v)),
  removeItem: (k) => store.delete(k),
}

const { buildReport, reportFile } = await import('./reportBuilder.ts')
const { stateOf, useCare } = await import('./useCare.ts')
const { CFB } = await import('xlsx')

async function sheetXml(blob) {
  const zip = CFB.read(new Uint8Array(await blob.arrayBuffer()), { type: 'array' })
  const text = (path) => new TextDecoder().decode(CFB.find(zip, `/${path}`).content)
  return { text, workbook: text('xl/workbook.xml') }
}

test('report workbook: styled header, frozen/filtered sheets, 合计 row outside the filter, text never a formula', async () => {
  const rows = Array.from({ length: 12 }, (_, i) => ({
    负责人: ['张三', '李四', '王五'][i % 3],
    状态: ['进行中', '已结题'][i % 2],
    数量: i + 1,
    备注: i === 0 ? '=HYPERLINK("http://x")' : '',
  }))
  const built = buildReport({ columns: Object.keys(rows[0]), rows }, { title: '测试', group_by: ['负责人'], metrics: [{ op: 'count' }, { op: 'pct' }, { op: 'avg', column: '数量' }] })
  assert.equal(built.ok, true)
  const { blob, name } = await reportFile(built.report, ['来源：测试数据', '由大肥鱼整理'])
  assert.match(name, /^测试_\d{8}_\d{4}\.xlsx$/)

  const { text, workbook } = await sheetXml(blob)
  assert.match(workbook, /<sheet name="汇总"[^>]*\/><sheet name="明细"[^>]*\/><sheet name="说明"/)
  const summary = text('xl/worksheets/sheet1.xml')
  assert.match(summary, /showGridLines="0"/)
  assert.match(summary, /state="frozen"/)
  assert.match(summary, /<autoFilter ref="A1:D4"\/>/, '3 groups + header; the 合计 row (row 5) stays out of the filter')
  assert.match(summary, /<t xml:space="preserve">占比<\/t>/, '(%) moves from the header into the number format')
  assert.match(summary, /<v>1<\/v>/, '合计 share 100 is written as 1 (100%)')

  const detail = text('xl/worksheets/sheet2.xml')
  assert.ok(!detail.includes('<f>'), 'no formula cells')
  assert.match(detail, /t="inlineStr"><is><t xml:space="preserve">=HYPERLINK\(&quot;http:\/\/x&quot;\)<\/t>/)

  const styles = text('xl/styles.xml')
  assert.match(styles, /<fgColor rgb="FF1F4E79"\/>/)
  assert.match(styles, /formatCode="0\.0%"/)
  assert.match(text('xl/worksheets/sheet3.xml'), /<t xml:space="preserve">来源<\/t>.*<t xml:space="preserve">测试数据<\/t>/s)
})

test('a raw API field name still finds its column after the column got a Chinese header', () => {
  const rows = [{ 负责人: '张三', 状态: 1 }, { 负责人: '李四', 状态: 2 }, { 负责人: '张三', 状态: 2 }]
  const table = { columns: ['负责人', '状态'], rows, aliases: { owner: '负责人', status: '状态' } }
  const built = buildReport(table, { title: 't', where: [{ column: 'owner', op: '=', value: '张三' }], columns: ['owner', 'status'] })
  assert.equal(built.ok, true)
  assert.deepEqual(built.report.sheets[0].columns, ['负责人', '状态'])
  assert.equal(built.report.sheets[0].rows.length, 2)
})

test('learned source: table page names columns and codes; the model only fills the rest, once', async () => {
  store.clear()
  const STATUS = { 1: '进行中', 2: '已结题', 3: '暂停' }
  const items = [1, 2, 1, 2, 3, 1, 2, 3].map((s, i) => ({
    project_code: `P${100 + i}`, status: s, owner: ['张三', '李四'][i % 2], note: `备注${i}`, extra_code: `X${i}`, password: 'secret',
  }))
  const listJson = JSON.stringify({ code: 0, data: { items, total: items.length } })
  const labelCalls = []
  globalThis.window = globalThis
  globalThis.location = new URL('http://app.local/serum/list')
  globalThis.document = { title: '免疫实验列表 - Vita' }
  globalThis.fetch = async (url, init) => {
    if (String(url) === '/api/pet/labels') {
      labelCalls.push(JSON.parse(init.body))
      return new Response(JSON.stringify({ ok: true, labels: { note: '备注', extra_code: '负责人' } }), { headers: { 'content-type': 'application/json' } })
    }
    return new Response(listJson, { headers: { 'content-type': 'application/json' } })
  }
  globalThis.XMLHttpRequest = class {
    open() {}
    setRequestHeader() {}
    addEventListener(type, fn) { this.onEnd = fn }
    send() {
      this.status = 200
      this.responseType = ''
      this.responseText = listJson
      this.onEnd()
    }
  }
  const { installApiWatch, sourceForTable, fetchSource, sourceColumns } = await import('./apiWatch.ts')
  installApiWatch()
  const xhr = new XMLHttpRequest()
  xhr.open('POST', '/serum/list')
  xhr.setRequestHeader('Authorization', 'Bearer t')
  xhr.send(JSON.stringify({ page: 1, limit: 20 }))

  const table = {
    title: '免疫实验列表', kind: 'el-table', partial: true, columns: ['项目编号', '状态', '负责人'],
    rows: items.map((it) => ({ 项目编号: it.project_code, 状态: STATUS[it.status], 负责人: it.owner })),
  }
  const src = sourceForTable(table)
  assert.ok(src, 'the table lines up with the recorded response')
  assert.deepEqual(src.labels, { project_code: '项目编号', status: '状态', owner: '负责人' })

  const first = await fetchSource(src, 'page_filters')
  assert.equal(labelCalls.length, 1)
  assert.deepEqual(labelCalls[0].fields.map((f) => f.key).sort(), ['extra_code', 'note'], 'only unnamed, non-sensitive fields are asked about')
  assert.deepEqual(first.table.columns, ['项目编号', '状态', '负责人', '备注', 'extra_code'], 'a guess clashing with a page label keeps the raw key')
  assert.equal(first.table.rows[0]['状态'], '进行中', 'status code learned from the table')
  assert.ok(!first.table.columns.includes('password'))
  assert.equal(first.table.aliases.owner, '负责人')
  assert.deepEqual(sourceColumns(src).slice(0, 4), ['项目编号', '状态', '负责人', '备注'])

  await fetchSource(src, 'page_filters')
  assert.equal(labelCalls.length, 1, 'headers are asked for once per field')
})

function careAt(start) {
  let now = start
  const realNow = Date.now
  Date.now = () => now
  const care = useCare({ say() {}, pick: (p) => p[0], pinLines: { on: [], off: [] } })
  return { care, advance: (ms) => (now += ms), restore: () => (Date.now = realNow) }
}

test('care drifts on the one-minute tick instead of rounding the change away', () => {
  store.clear()
  const { care, advance, restore } = careAt(new Date(2026, 10, 10, 10, 0).getTime())
  try {
    const before = care.care.value.satiety
    for (let i = 0; i < 60; i += 1) {
      advance(60_000)
      care.tick(false)
    }
    assert.ok(Math.abs(care.care.value.satiety - (before - 2)) < 0.01, `one awake hour costs 2 satiety, got ${before - care.care.value.satiety}`)
  } finally {
    restore()
  }
})

test('mood never sinks to down from drift alone, even starving and exhausted', () => {
  const start = new Date(2026, 10, 10, 10, 0).getTime()
  store.clear()
  const { care, advance, restore } = careAt(start)
  try {
    care.care.value = { ...care.care.value, satiety: 0, energy: 0, mood: 50, ts: start }
    for (let i = 0; i < 16 * 60; i += 1) {
      advance(60_000)
      care.tick(false)
    }
    const { mood } = care.care.value
    assert.ok(mood >= 35 && stateOf({ satiety: 50, energy: 50, mood }) !== 'down', `mood ${mood}`)
  } finally {
    restore()
  }
})
