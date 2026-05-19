/** FACS 阳性率 Excel/CSV 解析（国产 / 赛多利斯） */

export const POSITIVE_RATE_THRESHOLD = 10

export type FacsInstrumentType = '国产' | '赛多利斯'

export type ExcelRow = unknown[]

export interface ParseFacsExcelResult {
  instrumentType: FacsInstrumentType
  positiveWells: string[]
  error?: 'unknown_format' | 'matrix_not_found'
}

function cellStr(value: unknown): string {
  if (value === null || value === undefined) return ''
  return String(value).trim().replace(/^"|"$/g, '')
}

function rowText(row: ExcelRow | undefined): string {
  if (!row) return ''
  return row.map((c) => cellStr(c)).join(',')
}

/** 解析单元格为数值（尚未统一到 0–100 标度） */
export function parseRatePercent(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null
  if (typeof value === 'number' && !Number.isNaN(value)) return value
  const raw = cellStr(value).replace(/%/g, '')
  if (!raw) return null
  const n = Number.parseFloat(raw)
  return Number.isNaN(n) ? null : n
}

/**
 * 国产仪器导出：界面显示 19%，Excel 内常存 0.19（百分比格式）。
 * 赛多利斯导出：直接存 13.33 这类 0–100 标度，不做换算。
 */
export function normalizeDomesticRateMatrix(matrix: number[][]): number[][] {
  const positives = matrix.flat().filter((v) => v > 0)
  if (!positives.length) return matrix

  const max = Math.max(...positives)
  // 整张表最大值 ≤1 → 判定为 Excel 比例存储，统一 ×100
  if (max > 1) return matrix

  return matrix.map((row) => row.map((v) => (v > 0 ? v * 100 : v)))
}

/** 根据文件内容判断仪器类型 */
export function detectInstrumentTypeFromRows(rows: ExcelRow[]): FacsInstrumentType | null {
  const flat = rows
    .flat()
    .map((c) => cellStr(c))
    .join('\n')
  if (flat.includes('统计项')) return '国产'
  if (/Experiment\s*:/i.test(flat)) return '赛多利斯'
  return null
}

/** 国产：第三段「统计项 … %Parent」下 A–H × 12 列 */
export function parseDomesticRateMatrix(rows: ExcelRow[]): number[][] | null {
  let sectionRow = -1
  for (let i = 0; i < rows.length; i += 1) {
    const line = rowText(rows[i])
    if (line.includes('统计项') && line.includes('%Parent')) {
      sectionRow = i
      break
    }
  }
  if (sectionRow < 0) return null

  const dataStart = sectionRow + 2
  const matrix: number[][] = []
  for (let r = 0; r < 8; r += 1) {
    const row = rows[dataStart + r]
    if (!row) return null
    const values: number[] = []
    for (let c = 0; c < 12; c += 1) {
      const rate = parseRatePercent(row[c + 1])
      values.push(rate ?? 0)
    }
    matrix.push(values)
  }
  return normalizeDomesticRateMatrix(matrix)
}

/** 赛多利斯：元数据后的 A–H × 12 小数百分比 */
export function parseSartoriusRateMatrix(rows: ExcelRow[]): number[][] | null {
  let dataStart = -1
  for (let i = 0; i < rows.length; i += 1) {
    const label = cellStr(rows[i]?.[0]).toUpperCase()
    if (label !== 'A') continue
    if (parseRatePercent(rows[i]?.[1]) === null) continue
    dataStart = i
    break
  }
  if (dataStart < 0) return null

  const matrix: number[][] = []
  for (let r = 0; r < 8; r += 1) {
    const row = rows[dataStart + r]
    if (!row) return null
    const label = cellStr(row[0]).toUpperCase()
    if (label !== String.fromCharCode(65 + r)) return null
    const values: number[] = []
    for (let c = 0; c < 12; c += 1) {
      const rate = parseRatePercent(row[c + 1])
      values.push(rate ?? 0)
    }
    matrix.push(values)
  }
  return matrix
}

export function matrixToPositiveWells(
  matrix: number[][],
  threshold = POSITIVE_RATE_THRESHOLD,
): string[] {
  const wells: string[] = []
  for (let r = 0; r < matrix.length; r += 1) {
    const row = matrix[r]
    if (!row) continue
    for (let c = 0; c < row.length; c += 1) {
      const rate = row[c]
      if (rate !== undefined && rate > threshold) {
        wells.push(`${String.fromCharCode(65 + r)}${c + 1}`)
      }
    }
  }
  return wells
}

export function parseFacsExcelFromRows(rows: ExcelRow[]): ParseFacsExcelResult {
  const instrumentType = detectInstrumentTypeFromRows(rows)
  if (!instrumentType) {
    return { instrumentType: '国产', positiveWells: [], error: 'unknown_format' }
  }

  const matrix =
    instrumentType === '赛多利斯'
      ? parseSartoriusRateMatrix(rows)
      : parseDomesticRateMatrix(rows)

  if (!matrix) {
    return { instrumentType, positiveWells: [], error: 'matrix_not_found' }
  }

  return {
    instrumentType,
    positiveWells: matrixToPositiveWells(matrix),
  }
}
