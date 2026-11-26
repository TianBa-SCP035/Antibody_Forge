/** 从粘贴事件里取出图片。浏览器常把同一张图同时放在 files 和 items 里，按内容去重。 */

const IMAGE_SUFFIX = {
  'image/png': 'png',
  'image/jpeg': 'jpg',
  'image/gif': 'gif',
  'image/webp': 'webp',
  'image/bmp': 'bmp',
}

function takeImage(file, namePrefix, seen, out) {
  if (!file || typeof file.type !== 'string' || !IMAGE_SUFFIX[file.type]) return
  const mark = `${file.type}:${file.size}:${file.lastModified ?? ''}`
  if (seen.has(mark)) return
  seen.add(mark)
  const suffix = IMAGE_SUFFIX[file.type]
  const keepName = /\.[a-z0-9]+$/i.test(file.name || '') && !/^image\./i.test(file.name || '')
  out.push(keepName ? file : new File([file], `${namePrefix}.${suffix}`, { type: file.type }))
}

export function clipboardImageFiles(data, namePrefix = '粘贴') {
  const out = []
  const seen = new Set()
  for (const file of data?.files || []) takeImage(file, namePrefix, seen, out)
  for (const item of data?.items || []) {
    if (item?.kind === 'file') takeImage(item.getAsFile?.(), namePrefix, seen, out)
  }
  return out
}

export function clipboardHasImage(data) {
  const files = [...(data?.files || [])]
  const items = [...(data?.items || [])]
  return files.some((file) => String(file?.type || '').startsWith('image/'))
    || items.some((item) => item?.kind === 'file' && String(item?.type || '').startsWith('image/'))
}
