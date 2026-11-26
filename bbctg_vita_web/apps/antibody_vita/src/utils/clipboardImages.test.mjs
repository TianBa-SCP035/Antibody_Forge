import assert from 'node:assert/strict'
import test from 'node:test'

import { clipboardHasImage, clipboardImageFiles } from './clipboardImages.js'

test('截图的默认文件名改掉，files 和 items 里同一张只留一张', () => {
  const png = new File([Uint8Array.of(1, 2, 3)], 'image.png', { type: 'image/png' })
  const files = clipboardImageFiles({
    files: [png],
    items: [{ kind: 'file', type: 'image/png', getAsFile: () => png }],
  }, '既往筛选')
  assert.equal(files.length, 1)
  assert.equal(files[0].name, '既往筛选.png')
})

test('自己复制的图片保留原名，不支持的格式不算可粘贴', () => {
  const named = new File([Uint8Array.of(4)], '胶图.jpg', { type: 'image/jpeg' })
  const tiff = new File([Uint8Array.of(5)], 'a.tiff', { type: 'image/tiff' })
  assert.deepEqual(clipboardImageFiles({ files: [named, tiff] }).map((file) => file.name), ['胶图.jpg'])
  assert.equal(clipboardHasImage({ files: [tiff] }), true)
  assert.equal(clipboardHasImage({ items: [{ kind: 'string', type: 'text/plain' }] }), false)
})
