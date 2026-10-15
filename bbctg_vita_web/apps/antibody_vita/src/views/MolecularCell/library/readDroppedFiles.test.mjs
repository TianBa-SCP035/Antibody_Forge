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

test('a zip whose files sit at the root uses the zip name as the folder', () => {
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

test('a zip that already contains one folder keeps that folder name', () => {
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

test('zip names without the utf-8 flag are read as utf-8 or gbk', () => {
  assert.equal(zipEntryName(latin1(Buffer.from('b2e2d0f2bde1b9fb2f612e736571', 'hex'))), '测序结果/a.seq')
  assert.equal(zipEntryName(latin1(Buffer.from('测序结果/a.seq'))), '测序结果/a.seq')
  assert.equal(zipEntryName('测序结果/a.seq'), '测序结果/a.seq')
})

test('expandResultArchives unpacks zips next to plain files', async () => {
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

test('a zip is limited by the batch size, not the single file size', async () => {
  const dropped = await readDroppedFiles({ items: [], files: [{ name: 'big.zip', size: 60 * MB }] })
  assert.equal(dropped.length, 1)
  await assert.rejects(
    expandResultArchives([{ file: { name: 'huge.zip', size: 600 * MB }, path: 'huge.zip' }]),
    /huge\.zip 超过 500MB/,
  )
})
