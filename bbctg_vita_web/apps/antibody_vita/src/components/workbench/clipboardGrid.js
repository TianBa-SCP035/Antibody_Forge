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

export function parseClipboardGrid(text) {
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
