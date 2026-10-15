import { unzipSync } from 'fflate'

const MAX_FILE_COUNT = 400
const MAX_FILE_BYTES = 50 * 1024 * 1024
const MAX_BATCH_BYTES = 500 * 1024 * 1024

export function resultUploadLimitError(rows) {
  if (rows.length > MAX_FILE_COUNT) return `一次最多上传 ${MAX_FILE_COUNT} 个文件`
  if (rows.some((row) => row.file.size > MAX_FILE_BYTES)) return '单个文件不能超过 50MB'
  if (rows.reduce((total, row) => total + row.file.size, 0) > MAX_BATCH_BYTES) {
    return '一次上传总大小不能超过 500MB'
  }
  return ''
}

function readBatch(reader) {
  return new Promise((resolve, reject) => {
    const all = []
    const read = () => {
      reader.readEntries((batch) => {
        if (!batch.length) {
          resolve(all)
          return
        }
        all.push(...batch)
        read()
      }, reject)
    }
    read()
  })
}

function collectFile(state, file, path) {
  const key = `${path}\0${file.size}\0${file.lastModified}`
  if (state.seen.has(key)) return
  if (file.size > MAX_FILE_BYTES && !isZipPath(path)) throw new Error(`${path} 超过 50MB`)
  if (state.rows.length >= MAX_FILE_COUNT) {
    throw new Error(`文件数量超过 ${MAX_FILE_COUNT} 个，本次文件夹未加入上传`)
  }
  if (state.bytes + file.size > MAX_BATCH_BYTES) {
    throw new Error('文件总大小超过 500MB，本次文件夹未加入上传')
  }
  state.seen.add(key)
  state.bytes += file.size
  state.rows.push({ file, path })
}

async function filesFromEntry(entry, prefix, state) {
  if (entry.isFile) {
    const file = await new Promise((resolve, reject) => entry.file(resolve, reject))
    collectFile(state, file, `${prefix}${file.name}`)
    return
  }
  const children = await readBatch(entry.createReader())
  for (const child of children) {
    await filesFromEntry(child, `${prefix}${entry.name}/`, state)
  }
}

const PACKAGE_ROOT_FOLDERS = new Set(['测序结果', '拼接结果', '去载体序列'])

function isZipPath(path) {
  return String(path || '').toLowerCase().endsWith('.zip')
}

function parentPath(path) {
  const normalized = String(path || '').replaceAll('\\', '/').replace(/\/+$/, '')
  const index = normalized.lastIndexOf('/')
  return index >= 0 ? normalized.slice(0, index) : ''
}

function zipStem(path) {
  const base = String(path || '').replaceAll('\\', '/').split('/').pop() || 'package'
  return base.replace(/\.zip$/i, '') || 'package'
}

function cleanZipPath(value) {
  const parts = []
  for (const part of String(value || '').replaceAll('\\', '/').split('/')) {
    if (!part || part === '.' || part === '..') continue
    parts.push(part)
  }
  if (!parts.length || parts[0] === '__MACOSX') return ''
  const leaf = parts[parts.length - 1]
  if (leaf === '.DS_Store' || leaf === 'Thumbs.db') return ''
  return parts.join('/')
}

export function pathsFromZipEntries(entryNames, archivePath) {
  const cleaned = entryNames.map(cleanZipPath).filter(Boolean)
  const tops = new Set(cleaned.map((path) => path.split('/')[0]))
  const onlyTop = tops.size === 1 ? [...tops][0] : ''
  const prefix = !onlyTop || PACKAGE_ROOT_FOLDERS.has(onlyTop) ? zipStem(archivePath) : ''
  const parent = parentPath(archivePath)
  return cleaned.map((path) => [parent, prefix, path].filter(Boolean).join('/'))
}

export function zipEntryName(name) {
  const bytes = []
  for (const char of name) {
    const code = char.charCodeAt(0)
    if (code > 255) return name
    bytes.push(code)
  }
  try {
    return new TextDecoder('utf-8', { fatal: true }).decode(Uint8Array.from(bytes))
  } catch {
    return new TextDecoder('gbk').decode(Uint8Array.from(bytes))
  }
}

async function readZipEntries(file) {
  let files
  try {
    files = unzipSync(new Uint8Array(await file.arrayBuffer()), {
      filter(entry) {
        if (entry.name.endsWith('/')) return false
        if (entry.originalSize > MAX_FILE_BYTES) {
          throw new Error(`${zipEntryName(entry.name)} 超过 50MB`)
        }
        return true
      },
    })
  } catch (error) {
    if (String(error?.message || '').includes('超过')) throw error
    throw new Error('无法打开这个 zip，请先解开')
  }
  return Object.entries(files).map(([name, data]) => ({
    name: zipEntryName(name),
    data,
  }))
}

export async function expandResultArchives(rows) {
  const state = { rows: [], seen: new Set(), bytes: 0 }
  for (const row of rows || []) {
    const path = row.path || row.file?.name || ''
    if (!isZipPath(path)) {
      collectFile(state, row.file, path)
      continue
    }
    if (row.file.size > MAX_BATCH_BYTES) throw new Error(`${path} 超过 500MB`)
    const usable = (await readZipEntries(row.file)).filter((entry) => cleanZipPath(entry.name))
    if (!usable.length) throw new Error('压缩包里没有文件')
    const paths = pathsFromZipEntries(usable.map((entry) => entry.name), path)
    usable.forEach((entry, index) => {
      const relative = paths[index]
      const file = new File([entry.data], relative.split('/').pop(), { lastModified: index + 1 })
      collectFile(state, file, relative)
    })
  }
  return state.rows
}

export async function readDroppedFiles(dataTransfer) {
  const state = { rows: [], seen: new Set(), bytes: 0 }
  for (const item of Array.from(dataTransfer?.items || [])) {
    const entry = item.webkitGetAsEntry?.()
    if (entry) {
      await filesFromEntry(entry, '', state)
      continue
    }
    const file = item.getAsFile?.()
    if (file) collectFile(state, file, file.name)
  }
  if (!state.rows.length) {
    for (const file of Array.from(dataTransfer?.files || [])) {
      collectFile(state, file, file.name)
    }
  }
  return state.rows
}
