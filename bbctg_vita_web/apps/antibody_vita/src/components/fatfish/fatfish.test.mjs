import assert from 'node:assert/strict'
import test from 'node:test'

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

test('报表工作簿：表头样式、冻结与筛选、合计在筛选外、文本不成公式', async () => {
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
  assert.match(styles, /formatCode="0\.0%"/)
  assert.match(text('xl/worksheets/sheet3.xml'), /<t xml:space="preserve">来源<\/t>.*<t xml:space="preserve">测试数据<\/t>/s)
})

test('列改成中文表头后，原始 API 字段名仍能找到该列', () => {
  const rows = [{ 负责人: '张三', 状态: 1 }, { 负责人: '李四', 状态: 2 }, { 负责人: '张三', 状态: 2 }]
  const table = { columns: ['负责人', '状态'], rows, aliases: { owner: '负责人', status: '状态' } }
  const built = buildReport(table, { title: 't', where: [{ column: 'owner', op: '=', value: '张三' }], columns: ['owner', 'status'] })
  assert.equal(built.ok, true)
  assert.deepEqual(built.report.sheets[0].columns, ['负责人', '状态'])
  assert.equal(built.report.sheets[0].rows.length, 2)
})

test('学习数据源：页面定列名与编码，模型只补其余且只问一次', async () => {
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
    addEventListener(type, fn) { (this.ends ??= []).push(fn) }
    send() {
      this.status = 200
      this.responseType = ''
      this.responseText = listJson
      for (const fn of this.ends ?? []) fn()
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

test('分钟级 tick 按比例扣饱食，不把小变化舍成零', () => {
  store.clear()
  const { care, advance, restore } = careAt(new Date(2026, 10, 10, 10, 0).getTime())
  try {
    const before = care.care.value.satiety
    advance(60_000)
    care.tick(false)
    const dropped = before - care.care.value.satiety
    assert.ok(dropped > 0, '一分钟的变化不应被舍掉')
    assert.ok(Math.abs(dropped - 2 / 60) < 0.001, `一分钟应扣 ${2 / 60} 饱食，实际扣 ${dropped}`)
    advance(59 * 60_000)
    care.tick(false)
    assert.ok(Math.abs(care.care.value.satiety - (before - 2)) < 0.01, '累计一小时应扣 2 饱食')
  } finally {
    restore()
  }
})

test('空腹又耗尽时心情只回落到 35，不会因漂移跌入低落', () => {
  const start = new Date(2026, 10, 10, 10, 0).getTime()
  store.clear()
  const { care, advance, restore } = careAt(start)
  try {
    care.care.value = { ...care.care.value, satiety: 0, energy: 0, mood: 50, ts: start }
    advance(3_600_000)
    care.tick(false)
    assert.equal(care.care.value.mood, 46.25)
    advance(15 * 3_600_000)
    care.tick(false)
    const { mood } = care.care.value
    assert.equal(mood, 35)
    assert.notEqual(stateOf({ satiety: 50, energy: 50, mood }), 'down')
  } finally {
    restore()
  }
})

test('隔了半小时以上再聊，旧对话原文不再发给模型', async () => {
  const { toRecentHistory } = await import('./memory.ts')
  const now = new Date(2026, 10, 19, 15, 0).getTime()
  const qa = (role, text, minutesAgo) => ({ id: minutesAgo, role, text, at: now - minutesAgo * 60_000 })
  const yesterday = [qa('user', '昨天的问题', 24 * 60), qa('pet', '昨天的回答', 24 * 60 - 1)]
  const today = [qa('user', 'BJ001 进度', 10), qa('pet', '在免疫第二针', 9), qa('user', '那下一针呢', 0)]
  assert.deepEqual(
    toRecentHistory([...yesterday, ...today], '那下一针呢', now).map((h) => h.content),
    ['BJ001 进度', '在免疫第二针'],
  )
  assert.deepEqual(toRecentHistory([...yesterday, qa('user', '你好', 0)], '你好', now), [])
  const chain = Array.from({ length: 12 }, (_, i) => qa(i % 2 ? 'pet' : 'user', `句${i}`, 12 - i))
  assert.equal(toRecentHistory(chain, '新问题', now).length, 8)
})

test('离开原文窗口的对话并入摘要：对话结束就压缩，并过的不再重复', async () => {
  const { pendingForCompress, shouldCompress } = await import('./memory.ts')
  const now = new Date(2026, 10, 19, 15, 0).getTime()
  const qa = (text, minutesAgo) => ({ id: minutesAgo, role: 'user', text, at: now - minutesAgo * 60_000 })
  const short = [qa('下周三我请假', 50), qa('统计按负责人分', 45)]
  assert.deepEqual(pendingForCompress(short, 0, now - 40 * 60_000), [])
  const ended = pendingForCompress(short, 0, now)
  assert.equal(ended.length, 2)
  assert.ok(shouldCompress(ended, now))
  assert.deepEqual(pendingForCompress(short, short[1].at, now), [])
  const session = (n) => Array.from({ length: n }, (_, i) => qa(`句${i}`, n - i))
  const overflow = pendingForCompress(session(12), 0, now)
  assert.equal(overflow.length, 4)
  assert.equal(shouldCompress(overflow, now), false)
  assert.ok(shouldCompress(pendingForCompress(session(16), 0, now), now))
})
