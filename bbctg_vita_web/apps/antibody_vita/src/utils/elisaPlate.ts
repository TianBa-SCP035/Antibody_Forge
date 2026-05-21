/** ELISA 板：12 列槽位 + SkanIt Excel 吸光度解析 */

import * as XLSX from 'xlsx'

export type ElisaLayout = '5pair' | '6pair'

export interface ElisaSlotList {
  layout: ElisaLayout
  values: string[]
}

export const PLATE_ROWS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'] as const
export const DILUTION_LABELS = ['100', '500', '2500', '12500', '62500', '312500', '1562500'] as const
export const SLOT_COUNT = 12

const EMPTY_12 = () => Array(SLOT_COUNT).fill('') as string[]

function migrateLegacy7To12(values: string[]): string[] {
  const v = EMPTY_12()
  const pair = (legacyIdx: number, colA: number, colB: number) => {
    const text = values[legacyIdx] || ''
    v[colA] = text
    v[colB] = text
  }
  pair(1, 1, 2)
  pair(2, 3, 4)
  pair(3, 5, 6)
  pair(4, 7, 8)
  pair(5, 9, 10)
  return v
}

function migrateLegacy6To12(values: string[]): string[] {
  const v = EMPTY_12()
  for (let i = 0; i < 6; i += 1) {
    const text = values[i] || ''
    v[i * 2] = text
    v[i * 2 + 1] = text
  }
  return v
}

export function normalizeSlotList(raw: unknown, kind: 'upper' | 'lower'): ElisaSlotList {
  const layout: ElisaLayout =
    raw && typeof raw === 'object' && (raw as ElisaSlotList).layout === '6pair' ? '6pair' : '5pair'
  const source =
    raw && typeof raw === 'object' && Array.isArray((raw as ElisaSlotList).values)
      ? (raw as ElisaSlotList).values
      : []

  let values: string[]
  if (source.length === SLOT_COUNT) {
    values = source.map((x) => (x === undefined || x === null ? '' : String(x)))
  } else if (source.length === 7) {
    values = migrateLegacy7To12(source.map(String))
  } else if (source.length === 6) {
    values = migrateLegacy6To12(source.map(String))
  } else {
    values = EMPTY_12()
  }

  if (kind === 'lower' && layout === '5pair' && values.every((x) => !x)) {
    values[7] = 'NC'
    values[8] = 'NC'
    values[9] = 'PC'
    values[10] = 'PC'
  }

  return { layout, values }
}

export function createDefaultUpperSlotList(): ElisaSlotList {
  return { layout: '5pair', values: EMPTY_12() }
}

export function createDefaultLowerSlotList(): ElisaSlotList {
  const values = EMPTY_12()
  values[7] = 'NC'
  values[8] = 'NC'
  values[9] = 'PC'
  values[10] = 'PC'
  return { layout: '5pair', values }
}

export function expandLayout5to6(list: ElisaSlotList): ElisaSlotList {
  if (list.layout === '6pair') return list
  const source = [
    list.values[1] || '',
    list.values[3] || '',
    list.values[5] || '',
    list.values[7] || '',
    list.values[9] || '',
    '',
  ]
  const values = EMPTY_12()
  source.forEach((text, i) => {
    values[i * 2] = text
    values[i * 2 + 1] = text
  })
  return { layout: '6pair', values }
}

export function collapseLayout6to5(list: ElisaSlotList): ElisaSlotList {
  if (list.layout === '5pair') return list
  const source = [
    list.values[0] || '',
    list.values[2] || '',
    list.values[4] || '',
    list.values[6] || '',
    list.values[8] || '',
  ]
  const values = EMPTY_12()
  source.forEach((text, i) => {
    const start = 1 + i * 2
    values[start] = text
    values[start + 1] = text
  })
  return { layout: '5pair', values }
}

export function wellId(rowIndex: number, col: number): string {
  const row = PLATE_ROWS[rowIndex]
  if (!row || col < 1 || col > SLOT_COUNT) return ''
  return `${row}${col}`
}

export function getNcWellsFromLowerList(lower: ElisaSlotList): string[] {
  const wells: string[] = []
  lower.values.forEach((label, index) => {
    if (!/^NC$/i.test((label || '').trim())) return
    wells.push(wellId(7, index + 1))
  })
  return wells
}

export interface SlotGroup {
  start: number
  end: number
  label: string
}

export function normalizeSlotGroups(groups: unknown): SlotGroup[] {
  if (!Array.isArray(groups)) return []
  return groups
    .map((g) => {
      const start = Number((g as SlotGroup).start)
      const end = Number((g as SlotGroup).end)
      if (Number.isNaN(start) || Number.isNaN(end)) return null
      const s = Math.max(1, Math.min(SLOT_COUNT, start))
      const e = Math.max(s, Math.min(SLOT_COUNT, end))
      return { start: s, end: e, label: String((g as SlotGroup).label || '') }
    })
    .filter((g): g is SlotGroup => g !== null)
}

type ExcelRow = unknown[]

export interface AbsorbanceData {
  wavelength: number | null
  matrix: number[][]
}

export interface ElisaAbsorbanceSheet {
  index: number
  label: string
  data: AbsorbanceData
}

export interface ParseElisaExcelResult {
  primary: AbsorbanceData | null
  extraSheets: ElisaAbsorbanceSheet[]
  error?: 'unknown_format' | 'matrix_not_found'
}

function cellStr(value: unknown): string {
  if (value === null || value === undefined) return ''
  return String(value).trim().replace(/^"|"$/g, '')
}

function parseOd(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null
  if (typeof value === 'number' && !Number.isNaN(value)) return value
  const raw = cellStr(value)
  if (!raw || /^nan$/i.test(raw)) return null
  const n = Number.parseFloat(raw)
  return Number.isNaN(n) ? null : n
}

function parseWavelength(rows: ExcelRow[]): number | null {
  for (let i = 0; i < Math.min(rows.length, 20); i += 1) {
    const m = cellStr(rows[i]?.[0]).match(/波长[：:]\s*(\d+)\s*nm/i)
    if (m?.[1]) return Number.parseInt(m[1], 10)
  }
  return null
}

function parseAbsorbanceMatrix(rows: ExcelRow[]): number[][] | null {
  let dataStart = -1
  for (let i = 0; i < rows.length; i += 1) {
    if (cellStr(rows[i]?.[0]) === '吸光值') {
      dataStart = i + 1
      break
    }
  }
  if (dataStart < 0) return null

  const matrix: number[][] = []
  for (let r = 0; r < 8; r += 1) {
    const row = rows[dataStart + r]
    if (!row || cellStr(row[0]).toUpperCase() !== String.fromCharCode(65 + r)) return null
    const values: number[] = []
    for (let c = 0; c < 12; c += 1) values.push(parseOd(row[c + 1]) ?? 0)
    matrix.push(values)
  }
  return matrix
}

function parseSheet(rows: ExcelRow[]): AbsorbanceData | null {
  const matrix = parseAbsorbanceMatrix(rows)
  if (!matrix) return null
  return { wavelength: parseWavelength(rows), matrix }
}

function parseAbsorbanceSheets(wb: XLSX.WorkBook): ElisaAbsorbanceSheet[] {
  const sheets: ElisaAbsorbanceSheet[] = []
  for (const name of wb.SheetNames) {
    const m = name.match(/吸光度\s*(\d+)/)
    if (!m?.[1] || !wb.Sheets[name]) continue
    const rows = XLSX.utils.sheet_to_json(wb.Sheets[name], { header: 1, defval: '' }) as ExcelRow[]
    const data = parseSheet(rows)
    if (!data) continue
    sheets.push({
      index: Number.parseInt(m[1], 10),
      label: name.trim(),
      data,
    })
  }
  sheets.sort((a, b) => a.index - b.index)
  return sheets
}

export function parseElisaArrayBuffer(buffer: ArrayBuffer, fileName: string): ParseElisaExcelResult {
  const wb = /\.csv$/i.test(fileName)
    ? XLSX.read(new TextDecoder('utf-8').decode(buffer), { type: 'string' })
    : XLSX.read(buffer, { type: 'array' })
  const all = parseAbsorbanceSheets(wb)
  const primarySheet = all.find((s) => s.index === 1) ?? all[0] ?? null
  const primary = primarySheet?.data ?? null
  if (!primary) {
    return {
      primary: null,
      extraSheets: [],
      error: all.length ? 'matrix_not_found' : 'unknown_format',
    }
  }
  return {
    primary,
    extraSheets: all.filter((s) => s.index !== primarySheet!.index),
  }
}

export function computeAutoPositiveFromPlate(matrix: number[][], lower: ElisaSlotList): string[] {
  const ncWells = getNcWellsFromLowerList(lower)
  const vals = ncWells
    .map((w) => {
      const row = w.charCodeAt(0) - 65
      const col = Number.parseInt(w.slice(1), 10) - 1
      return matrix[row]?.[col]
    })
    .filter((v): v is number => v !== null && !Number.isNaN(v))
  if (!vals.length) return []
  const threshold = Math.min(...vals) * 2
  const wells: string[] = []
  for (let r = 0; r < 8; r += 1) {
    for (let c = 0; c < 12; c += 1) {
      const v = matrix[r]?.[c]
      if (v !== undefined && v > threshold) wells.push(wellId(r, c + 1))
    }
  }
  return wells
}

export function formatOd(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return value.toFixed(4)
}
