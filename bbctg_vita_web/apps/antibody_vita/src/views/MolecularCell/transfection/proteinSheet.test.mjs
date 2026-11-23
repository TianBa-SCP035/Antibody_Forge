import assert from 'node:assert/strict'
import test from 'node:test'

import { MAX_PROTEIN_ROWS, proteinRowsFromSheet, proteinRowsFromWorkbook } from './proteinSheet.js'

function book(sheets) {
  return { SheetNames: Object.keys(sheets), Sheets: sheets }
}
const readAt = (firstRow) => (rows) => ({ rows, firstRow })

test('按表头取三列，行号按 Excel 实际行号，其他列不读', () => {
  const rows = [
    [],
    ['编号', '轻链名称', ' 抗体 名称 ', '浓度', '重链名称', '备注'],
    [1, 'VK-1', 'A1', 0.5, 'VH-1', 'x'],
    ['', '', '', '', '', ''],
    [2, '', 42, '', 'VH-2'],
    [3, '', '', 0.8, '', '只有其他列'],
  ]
  assert.deepEqual(proteinRowsFromSheet(rows, 3), [
    { row: 5, protein_name: 'A1', heavy_chain: 'VH-1', light_chain: 'VK-1' },
    { row: 7, protein_name: '42', heavy_chain: 'VH-2', light_chain: '' },
  ])
})

test('认常见表头写法，表头上方的说明行不管', () => {
  const rows = [
    ['需求：重链2ug，轻链4ug'],
    ['抗体名称*', '重链名', '轻链'],
    ['A1', 'H1', 'L1'],
  ]
  assert.deepEqual(proteinRowsFromSheet(rows), [{ row: 3, protein_name: 'A1', heavy_chain: 'H1', light_chain: 'L1' }])
  assert.equal(proteinRowsFromSheet([['蛋白名称', '重链浓度', '轻链']]), null)
})

test('缺表头的表返回 null，工作簿里取第一张带表头的表', () => {
  assert.equal(proteinRowsFromSheet([['抗体名称', '重链']]), null)
  const items = proteinRowsFromWorkbook(
    book({ 说明: [['填写说明']], 蛋白: [['蛋白名称', '重链', '轻链'], ['A1', 'H1', '']] }),
    readAt(1),
  )
  assert.deepEqual(items, [{ row: 2, protein_name: 'A1', heavy_chain: 'H1', light_chain: '' }])
})

test('没有表头、没有数据、超出上限都报错', () => {
  assert.throws(() => proteinRowsFromWorkbook(book({ a: [['名称']] }), readAt(1)), /找不到表头/)
  assert.throws(() => proteinRowsFromWorkbook(book({ a: [['抗体名称', '重链名称', '轻链名称']] }), readAt(1)), /没有蛋白/)
  const many = [['抗体名称', '重链名称', '轻链名称'], ...Array.from({ length: MAX_PROTEIN_ROWS + 1 }, (_, i) => [`P${i}`, 'H', ''])]
  assert.throws(() => proteinRowsFromWorkbook(book({ a: many }), readAt(1)), /最多导入/)
})
