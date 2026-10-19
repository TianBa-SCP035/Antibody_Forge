const HIDDEN_CHARS = /[\u00AD\u200B-\u200F\u202A-\u202E\u2060-\u2064\uFEFF]/g
const CONTROL_CHARS = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g

export function cleanFieldText(value, { keepBreaks = false } = {}) {
  let text = String(value ?? '')
    .replace(/\u00A0/g, ' ')
    .replace(HIDDEN_CHARS, '')
    .replace(CONTROL_CHARS, '')
  if (keepBreaks) {
    return text.replace(/\r\n/g, '\n').replace(/\r/g, '\n').replace(/^\n+|\n+$/g, '')
  }
  return text.replace(/[\r\n\t]+/g, ' ').trim()
}

function parseClipboardGrid(text) {
  const source = String(text ?? '').replace(/\r\n/g, '\n').replace(/\r/g, '\n')
  const rows = []
  let row = []
  let cell = ''
  let quoted = false

  for (let index = 0; index < source.length; index += 1) {
    const char = source[index]
    if (quoted) {
      if (char === '"') {
        if (source[index + 1] === '"') {
          cell += '"'
          index += 1
        } else {
          quoted = false
        }
      } else {
        cell += char
      }
      continue
    }
    if (char === '"' && cell === '') {
      quoted = true
      continue
    }
    if (char === '\t') {
      row.push(cell)
      cell = ''
      continue
    }
    if (char === '\n') {
      row.push(cell)
      rows.push(row)
      row = []
      cell = ''
      continue
    }
    cell += char
  }

  if (cell !== '' || row.length) {
    row.push(cell)
    rows.push(row)
  }
  return rows
}

export function clipboardCell(value) {
  const text = value == null ? '' : String(value)
  if (/["\t\n\r]/.test(text)) return `"${text.replaceAll('"', '""')}"`
  return text
}

const BLOCK_TAGS = new Set(['DIV', 'P', 'LI', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'PRE', 'BLOCKQUOTE'])

function appendPiece(text, raw) {
  let value = String(raw).replace(/\r\n/g, '\n').replace(/\r/g, '\n')
  if (!value) return text
  if (/^\s+$/.test(value) && value.includes('\n')) return text
  if (text.endsWith('\n')) value = value.replace(/^\n[ \t]*/, '')
  return text + value
}

function readNodes(nodes) {
  let text = ''
  const walk = (node) => {
    if (node.nodeType === 3) {
      text = appendPiece(text, node.nodeValue)
      return
    }
    if (node.nodeType !== 1) return
    const name = node.tagName
    if (name === 'BR') {
      text += '\n'
      return
    }
    if (name === 'TABLE' || name === 'STYLE' || name === 'SCRIPT') return
    if (BLOCK_TAGS.has(name)) {
      if (text && !text.endsWith('\n')) text += '\n'
      const mark = text.length
      for (const child of node.childNodes) walk(child)
      if (text.length === mark) text += '\n'
      else if (!text.endsWith('\n')) text += '\n'
      return
    }
    for (const child of node.childNodes) walk(child)
  }
  for (const node of nodes) walk(node)
  return text
}

function directRows(table) {
  const rows = []
  const sections = [...table.children].filter((element) => (
    element.tagName === 'THEAD' || element.tagName === 'TBODY' || element.tagName === 'TFOOT'
  ))
  for (const parent of (sections.length ? sections : [table])) {
    for (const child of parent.children) {
      if (child.tagName === 'TR') rows.push(child)
    }
  }
  return rows
}

function placeSpans(rawRows) {
  const grid = []
  const pending = new Map()
  for (const cells of rawRows) {
    const row = []
    let col = 0
    const takePending = () => {
      while (pending.has(col)) {
        const item = pending.get(col)
        row.push('')
        item.left -= 1
        if (item.left <= 0) pending.delete(col)
        col += 1
      }
    }
    for (const cell of cells) {
      takePending()
      for (let offset = 0; offset < cell.colspan; offset += 1) {
        row.push(offset === 0 ? cell.text : '')
        if (cell.rowspan > 1) pending.set(col, { left: cell.rowspan - 1 })
        col += 1
      }
    }
    takePending()
    grid.push(row)
  }
  return grid
}

function tableGrid(table) {
  const rawRows = directRows(table).map((row) => [...row.children]
    .filter((cell) => cell.tagName === 'TD' || cell.tagName === 'TH')
    .map((cell) => ({
      text: readNodes(cell.childNodes).replace(/^\n+|\n+$/g, ''),
      colspan: cell.colSpan || 1,
      rowspan: cell.rowSpan || 1,
    })))
  return placeSpans(rawRows)
}

function parseClipboardTable(html) {
  const source = String(html ?? '')
  if (!/<table[\s>]/i.test(source)) return null
  const parsed = new DOMParser().parseFromString(source, 'text/html')
  let best = null
  let bestCount = 0
  for (const table of parsed.querySelectorAll('table')) {
    const grid = tableGrid(table)
    const count = grid.reduce((sum, row) => sum + row.length, 0)
    if (count > bestCount) {
      best = grid
      bestCount = count
    }
  }
  return best
}

export function readClipboardGrid(clipboardData) {
  const plain = clipboardData?.getData?.('text/plain') || ''
  const table = parseClipboardTable(clipboardData?.getData?.('text/html') || '')
  if (table?.some((row) => row.some((cell) => cell !== ''))) return table
  return parseClipboardGrid(plain)
}
