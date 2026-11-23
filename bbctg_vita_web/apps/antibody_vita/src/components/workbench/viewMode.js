export const WORKBENCH_VIEW = 'workbench'
export const EXCEL_VIEW = 'excel'

export function coerceWorkbenchViewMode(value) {
  return value === EXCEL_VIEW || value === 'sheet' ? EXCEL_VIEW : WORKBENCH_VIEW
}
