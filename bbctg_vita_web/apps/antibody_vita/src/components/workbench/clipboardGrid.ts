const HIDDEN_CHARS = /[\u00AD\u200B-\u200F\u202A-\u202E\u2060-\u2064\uFEFF]/g
const CONTROL_CHARS = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g

export interface CleanFieldTextOptions {
  keepBreaks?: boolean
}

export function cleanFieldText(
  value: unknown,
  { keepBreaks = false }: CleanFieldTextOptions = {},
): string {
  const text = String(value ?? '')
    .replace(/\u00A0/g, ' ')
    .replace(HIDDEN_CHARS, '')
    .replace(CONTROL_CHARS, '')
  if (keepBreaks) {
    return text
      .replace(/\r\n/g, '\n')
      .replace(/\r/g, '\n')
      .replace(/\t+/g, ' ')
      .replace(/^[ \n]+|[ \n]+$/g, '')
  }
  return text.replace(/[\r\n\t]+/g, ' ').trim()
}

function parseClipboardGrid(text: unknown): string[][] {
  const source = String(text ?? '').replace(/\r\n/g, '\n').replace(/\r/g, '\n')
  const rows: string[][] = []
  let row: string[] = []
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

export function clipboardCell(value: unknown): string {
  const text = value == null
    ? ''
    : String(value)
        .replace(/\u00A0/g, ' ')
        .replace(HIDDEN_CHARS, '')
        .replace(CONTROL_CHARS, '')
        .replace(/\r\n/g, '\n')
        .replace(/\r/g, '\n')
        .replace(/\t+/g, ' ')
  if (/["\t\n\r]/.test(text)) return `"${text.replaceAll('"', '""')}"`
  return text
}

const BLOCK_TAGS = new Set(['DIV', 'P', 'LI', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'PRE', 'BLOCKQUOTE'])

function appendPiece(text: string, raw: unknown): string {
  let value = String(raw ?? '').replace(/\r\n/g, '\n').replace(/\r/g, '\n')
  if (!value) return text
  if (/^\s+$/.test(value) && value.includes('\n')) return text
  if (text.endsWith('\n')) value = value.replace(/^\n[ \t]*/, '')
  return text + value
}

function readNodes(nodes: Iterable<ChildNode>): string {
  let text = ''
  const walk = (node: ChildNode) => {
    if (node.nodeType === 3) {
      text = appendPiece(text, node.nodeValue)
      return
    }
    if (node.nodeType !== 1) return
    const element = node as Element
    const name = element.tagName
    if (name === 'BR') {
      text += '\n'
      return
    }
    if (name === 'TABLE' || name === 'STYLE' || name === 'SCRIPT') return
    if (BLOCK_TAGS.has(name)) {
      if (text && !text.endsWith('\n')) text += '\n'
      const mark = text.length
      for (const child of Array.from(element.childNodes)) walk(child)
      if (text.length === mark) text += '\n'
      else if (!text.endsWith('\n')) text += '\n'
      return
    }
    for (const child of Array.from(element.childNodes)) walk(child)
  }
  for (const node of nodes) walk(node)
  return text
}

function directRows(table: Element): Element[] {
  const rows: Element[] = []
  const sections = Array.from(table.children).filter((element) => (
    element.tagName === 'THEAD' || element.tagName === 'TBODY' || element.tagName === 'TFOOT'
  ))
  for (const parent of (sections.length ? sections : [table])) {
    for (const child of Array.from(parent.children)) {
      if (child.tagName === 'TR') rows.push(child)
    }
  }
  return rows
}

interface RawTableCell {
  text: string
  colspan: number
  rowspan: number
}

function placeSpans(rawRows: RawTableCell[][]): string[][] {
  const grid: string[][] = []
  const pending = new Map<number, { left: number }>()
  for (const cells of rawRows) {
    const row: string[] = []
    let col = 0
    const takePending = () => {
      while (pending.has(col)) {
        const item = pending.get(col)!
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

function tableGrid(table: Element): string[][] {
  const rawRows = directRows(table).map((row) => Array.from(row.children)
    .filter((cell): cell is HTMLTableCellElement => cell.tagName === 'TD' || cell.tagName === 'TH')
    .map((cell) => ({
      text: readNodes(Array.from(cell.childNodes)).replace(/^\n+|\n+$/g, ''),
      colspan: cell.colSpan || 1,
      rowspan: cell.rowSpan || 1,
    })))
  return placeSpans(rawRows)
}

function parseClipboardTable(html: unknown): string[][] | null {
  const source = String(html ?? '')
  if (!/<table[\s>]/i.test(source)) return null
  const parsed = new DOMParser().parseFromString(source, 'text/html')
  let best: string[][] | null = null
  let bestCount = 0
  for (const table of Array.from(parsed.querySelectorAll('table'))) {
    const grid = tableGrid(table)
    const count = grid.reduce((sum, row) => sum + row.length, 0)
    if (count > bestCount) {
      best = grid
      bestCount = count
    }
  }
  return best
}

export function readClipboardGrid(
  clipboardData: DataTransfer | null | undefined,
): string[][] {
  const plain = clipboardData?.getData?.('text/plain') || ''
  const table = parseClipboardTable(clipboardData?.getData?.('text/html') || '')
  if (table?.some((row) => row.some((cell) => cell !== ''))) return table
  return parseClipboardGrid(plain)
}
