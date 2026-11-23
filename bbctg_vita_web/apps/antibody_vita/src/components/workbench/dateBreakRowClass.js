/** 相邻行日期不同时加分隔线；同时保留正在编辑的行标记。 */
export function dateBreakRowClass({ list, row, rowIndex, field, editingId }) {
  const classes = []
  if (editingId != null && row?.id === editingId) classes.push('is-editing')
  if (rowIndex > 0) {
    const current = String(row?.[field] || '').slice(0, 10)
    const previous = String(list?.[rowIndex - 1]?.[field] || '').slice(0, 10)
    if (current !== previous) classes.push('is-date-break')
  }
  return classes.join(' ')
}
