/** FACS 阳性率 Excel/CSV 解析（国产 / 赛多利斯） */

export const POSITIVE_RATE_THRESHOLD = 15

export type FacsInstrumentType = '国产' | '赛多利斯'
export type ExcelRow = unknown[]

export interface ParseFacsExcelResult {
  instrumentType: FacsInstrumentType
  positiveWells: string[]
  error?: 'unknown_format' | 'matrix_not_found'
}

function cellStr(v: unknown): string {
  if (v == null) return ''
  return String(v).trim().replace(/^"|"$/g, '')
}

function parseNum(v: unknown): number | null {
  if (v == null || v === '') return null
  if (typeof v === 'number' && !Number.isNaN(v)) return v
  const raw = cellStr(v).replace(/%/g, '')
  if (!raw) return null
  const n = Number.parseFloat(raw)
  return Number.isNaN(n) ? null : n
}

function detectInstrument(rows: ExcelRow[]): FacsInstrumentType | null {
  const text = rows.flat().map(cellStr).join('\n')
  if (text.includes('统计项')) return '国产'
  if (/Experiment\s*:/i.test(text)) return '赛多利斯'
  return null
}

/** 孔 1 所在列下标（仅在扫描区间内找 1…12 表头） */
function wellColStart(rows: ExcelRow[], fromRow: number, stopRow: number): number {
  for (let i = fromRow; i < stopRow; i += 1) {
    const row = rows[i]
    if (!row) continue
    for (let s = 0; s <= 3; s += 1) {
      if (cellStr(row[s]) === '1' && cellStr(row[s + 11]) === '12') return s
    }
  }
  return 1
}

function scanStopRow(rows: ExcelRow[], fromRow: number): number {
  for (let i = fromRow; i < rows.length; i += 1) {
    const first = cellStr(rows[i]?.[0])
    if (first === '样品' || first === '已计算') return i
  }
  return rows.length
}

/** 国产：从「统计项 … %Parent」行起扫，避免误读其它表 */
function domesticScanFrom(rows: ExcelRow[]): number {
  for (let i = 0; i < rows.length; i += 1) {
    const line = (rows[i] || []).map(cellStr).join(',')
    if (line.includes('统计项') && line.includes('%Parent')) return i
  }
  return 0
}

/** 按 A–H 行号、1–12 列提取；允许非满板、空孔 */
function extractMatrix(rows: ExcelRow[], fromRow = 0): number[][] | null {
  const stopRow = scanStopRow(rows, fromRow)
  const matrix = Array.from({ length: 8 }, () => Array(12).fill(0))
  const cs = wellColStart(rows, fromRow, stopRow)
  let any = false

  for (let i = fromRow; i < stopRow; i += 1) {
    const row = rows[i]
    if (!row?.length) continue
    const label = cellStr(row[0]).toUpperCase()
    if (label.length !== 1 || label < 'A' || label > 'H') continue
    const ri = label.charCodeAt(0) - 65
    for (let c = 0; c < 12; c += 1) {
      const v = parseNum(row[cs + c])
      if (v != null) {
        matrix[ri][c] = v
        any = true
      }
    }
  }
  return any ? matrix : null
}

/** 国产 Excel 常存 0.19 表示 19%，最大值 ≤1 时统一 ×100 */
function scaleDomestic(matrix: number[][]): number[][] {
  const vals = matrix.flat().filter((v) => v > 0)
  if (!vals.length || Math.max(...vals) > 1) return matrix
  return matrix.map((r) => r.map((v) => (v > 0 ? v * 100 : v)))
}

function toPositiveWells(matrix: number[][], threshold = POSITIVE_RATE_THRESHOLD): string[] {
  const wells: string[] = []
  for (let r = 0; r < 8; r += 1) {
    for (let c = 0; c < 12; c += 1) {
      if (matrix[r][c] > threshold) wells.push(`${String.fromCharCode(65 + r)}${c + 1}`)
    }
  }
  return wells
}

export function parseFacsExcelFromRows(rows: ExcelRow[]): ParseFacsExcelResult {
  const instrumentType = detectInstrument(rows)
  if (!instrumentType) {
    return { instrumentType: '国产', positiveWells: [], error: 'unknown_format' }
  }

  const fromRow = instrumentType === '国产' ? domesticScanFrom(rows) : 0
  let matrix = extractMatrix(rows, fromRow)
  if (!matrix) {
    return { instrumentType, positiveWells: [], error: 'matrix_not_found' }
  }
  if (instrumentType === '国产') matrix = scaleDomestic(matrix)

  return { instrumentType, positiveWells: toPositiveWells(matrix) }
}
