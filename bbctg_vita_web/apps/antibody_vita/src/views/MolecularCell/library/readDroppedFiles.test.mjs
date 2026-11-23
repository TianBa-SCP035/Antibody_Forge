import assert from 'node:assert/strict'
import test from 'node:test'

import { strToU8, zipSync } from 'fflate'

import {
  expandResultArchives,
  pathsFromZipEntries,
  readDroppedFiles,
  zipEntryName,
} from './readDroppedFiles.js'

const MB = 1024 * 1024

function zipFile(name, entries) {
  const files = Object.fromEntries(Object.entries(entries).map(([path, text]) => [path, strToU8(text)]))
  return new File([zipSync(files)], name)
}

function latin1(bytes) {
  return String.fromCharCode(...bytes)
}

test('zip 内文件在根目录时用 zip 名作文件夹', () => {
  assert.deepEqual(
    pathsFromZipEntries([
      '测序结果/a.seq',
      '拼接结果/b.txt',
      '去载体序列/c.txt',
      '明细表.xlsx',
    ], 'TJ6936.zip'),
    [
      'TJ6936/测序结果/a.seq',
      'TJ6936/拼接结果/b.txt',
      'TJ6936/去载体序列/c.txt',
      'TJ6936/明细表.xlsx',
    ],
  )
})

test('zip 内只有标记文件夹时用 zip 名作文件夹', () => {
  assert.deepEqual(
    pathsFromZipEntries(['测序合格结果/a.ab1', '完成/b.seq'], 'batch.zip'),
    ['batch/测序合格结果/a.ab1', 'batch/完成/b.seq'],
  )
  assert.deepEqual(
    pathsFromZipEntries(['完成/a.seq'], 'CN.zip'),
    ['CN/完成/a.seq'],
  )
})

test('zip 内已有一个文件夹时保留该文件夹名', () => {
  assert.deepEqual(
    pathsFromZipEntries([
      'TJ6936-/测序结果/a.seq',
      'TJ6936-/拼接结果/b.txt',
      '__MACOSX/._a.seq',
    ], 'download.zip'),
    [
      'TJ6936-/测序结果/a.seq',
      'TJ6936-/拼接结果/b.txt',
    ],
  )
})

test('zip 文件名无 UTF-8 标记时按 UTF-8 或 GBK 解码', () => {
  assert.equal(zipEntryName(latin1(Buffer.from('b2e2d0f2bde1b9fb2f612e736571', 'hex'))), '测序结果/a.seq')
  assert.equal(zipEntryName(latin1(Buffer.from('测序结果/a.seq'))), '测序结果/a.seq')
  assert.equal(zipEntryName('测序结果/a.seq'), '测序结果/a.seq')
})

test('解压结果包时 zip 与普通文件并列展开', async () => {
  const rows = await expandResultArchives([
    {
      file: zipFile('TJ6936.zip', {
        '测序结果/a.seq': 'ATGC',
        '拼接结果/b.txt': 'asm',
        '去载体序列/c.txt': 'trim',
      }),
      path: 'TJ6936.zip',
    },
    { file: zipFile('TJ7241.zip', { 'TJ7241-8位/测序结果/a.seq': 'ATGC' }), path: 'TJ7241.zip' },
    { file: new File(['gel'], 'gel.png'), path: 'gel.png' },
  ])
  const texts = Object.fromEntries(
    await Promise.all(rows.map(async (row) => [row.path, await row.file.text()])),
  )
  assert.deepEqual(texts, {
    'TJ6936/测序结果/a.seq': 'ATGC',
    'TJ6936/拼接结果/b.txt': 'asm',
    'TJ6936/去载体序列/c.txt': 'trim',
    'TJ7241-8位/测序结果/a.seq': 'ATGC',
    'gel.png': 'gel',
  })
})

test('zip 按整批大小限制，不按单文件大小限制', async () => {
  const dropped = await readDroppedFiles({ items: [], files: [{ name: 'big.zip', size: 60 * MB }] })
  assert.equal(dropped.length, 1)
  await assert.rejects(
    expandResultArchives([{ file: { name: 'huge.zip', size: 600 * MB }, path: 'huge.zip' }]),
    /huge\.zip 超过 500MB/,
  )
})
