export interface ProteinSheetRow {
  row: number
  protein_name: string
  heavy_chain: string
  light_chain: string
}

export interface ProteinSheetRead {
  rows: unknown[][]
  firstRow: number
}

export const PROTEIN_HEADERS: Readonly<Record<string, string>>

export const MAX_PROTEIN_ROWS: number

export function proteinRowsFromSheet(rows: unknown, firstRow?: number): ProteinSheetRow[] | null

export function proteinRowsFromWorkbook<Sheet>(
  book: { SheetNames: string[]; Sheets: Record<string, Sheet> },
  readSheet: (sheet: Sheet) => ProteinSheetRead,
): ProteinSheetRow[]
