/**
 * 转染蛋白导入表：按表头找名称、重链、轻链三列，重链、轻链两列可以没有（只给名称时后端按名称查重轻链）。
 * 这里只找表头、按行取值；名称重复、和转染表不一致等规则由后端统一校验。
 */

/** 每列认的表头写法，比较时去掉空白和末尾的 *。 */
const HEADER_ALIASES = {
  protein_name: ['抗体名称', '抗体名', '蛋白名称', '蛋白名'],
  heavy_chain: ['重链名称', '重链名', '重链', '重链质粒名称', '重链质粒名', '重链质粒'],
  light_chain: ['轻链名称', '轻链名', '轻链', '轻链质粒名称', '轻链质粒名', '轻链质粒'],
}
export const PROTEIN_HEADERS = Object.freeze(
  Object.fromEntries(Object.entries(HEADER_ALIASES).flatMap(([key, names]) => names.map((name) => [name, key]))),
)
export const MAX_PROTEIN_ROWS = 5000

function text(value) {
  return String(value ?? '').trim()
}

function headerColumns(cells) {
  const columns = {}
  cells.forEach((cell, index) => {
    const key = PROTEIN_HEADERS[text(cell).replace(/\s+/g, '').replace(/[*＊]+$/, '')]
    if (key && columns[key] === undefined) columns[key] = index
  })
  return columns.protein_name === undefined ? null : columns
}

/**
 * 从一张表的二维数组里读蛋白行。firstRow 是数组第一行在 Excel 里的行号，用来标出问题行。
 * 表头是第一行有名称列表头的行，上面的说明行不管；其他列不读，三列都空的行跳过。没有表头返回 null。
 */
export function proteinRowsFromSheet(rows, firstRow = 1) {
  const lines = Array.isArray(rows) ? rows : []
  for (const [index, row] of lines.entries()) {
    const columns = headerColumns(Array.isArray(row) ? row : [])
    if (!columns) continue
    return lines
      .slice(index + 1)
      .map((cells, offset) => ({
        row: firstRow + index + 1 + offset,
        protein_name: text(cells?.[columns.protein_name]),
        heavy_chain: columns.heavy_chain === undefined ? '' : text(cells?.[columns.heavy_chain]),
        light_chain: columns.light_chain === undefined ? '' : text(cells?.[columns.light_chain]),
      }))
      .filter((item) => item.protein_name || item.heavy_chain || item.light_chain)
  }
  return null
}

/** 整个工作簿：取第一张带表头的表。readSheet(sheet) 返回 { rows, firstRow }。 */
export function proteinRowsFromWorkbook(book, readSheet) {
  for (const name of book?.SheetNames || []) {
    const { rows, firstRow } = readSheet(book.Sheets[name])
    const items = proteinRowsFromSheet(rows, firstRow)
    if (!items) continue
    if (!items.length) throw new Error('文件里没有蛋白')
    if (items.length > MAX_PROTEIN_ROWS) throw new Error(`单次最多导入 ${MAX_PROTEIN_ROWS} 个蛋白`)
    return items
  }
  throw new Error('找不到表头：至少需要抗体名称一列（重链名称、轻链名称可选）')
}
