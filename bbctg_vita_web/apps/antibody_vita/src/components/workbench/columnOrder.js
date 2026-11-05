const MIN_COLUMN_WIDTH = 40
const MAX_COLUMN_WIDTH = 1200

/** 个人设置的列字体颜色，只给固定色板；样式见 WorkbenchDataTable 的 wb-text-*。 */
export const COLUMN_TEXT_COLORS = [
  { value: 'red', label: '红' },
  { value: 'orange', label: '橙' },
  { value: 'green', label: '绿' },
  { value: 'blue', label: '蓝' },
  { value: 'purple', label: '紫' },
]
const TEXT_COLOR_VALUES = new Set(COLUMN_TEXT_COLORS.map((item) => item.value))

export function columnTextClass(color) {
  return TEXT_COLOR_VALUES.has(color) ? `wb-text-colored wb-text-${color}` : ''
}

function sanitizeColors(colors) {
  const result = {}
  if (!colors || typeof colors !== 'object') return result
  for (const [key, value] of Object.entries(colors)) {
    if (key && TEXT_COLOR_VALUES.has(value)) result[key] = value
  }
  return result
}

export function createColumnOrder(
  storageKey,
  defaultColumns,
  { pinFirstKey, pinLastKey, defaultHidden = [] } = {},
) {
  function isPinned(key) {
    return key === pinFirstKey || key === pinLastKey
  }

  function applyPins(ordered) {
    const next = [...ordered]
    if (pinFirstKey) {
      const index = next.findIndex((column) => column.key === pinFirstKey)
      if (index > 0) next.unshift(...next.splice(index, 1))
    }
    if (pinLastKey) {
      const index = next.findIndex((column) => column.key === pinLastKey)
      if (index >= 0 && index < next.length - 1) {
        next.push(...next.splice(index, 1))
      }
    }
    return next
  }

  function merge(cachedKeys) {
    const remaining = new Map(defaultColumns.map((column) => [column.key, column]))
    const ordered = []
    for (const key of cachedKeys || []) {
      const column = remaining.get(String(key || ''))
      if (!column) continue
      ordered.push(column)
      remaining.delete(column.key)
    }
    for (const column of defaultColumns) {
      if (remaining.has(column.key)) ordered.push(column)
    }
    return applyPins(ordered)
  }

  function move(columns, fromKey, toKey) {
    if (!fromKey || fromKey === toKey || isPinned(fromKey) || isPinned(toKey)) {
      return columns
    }
    const next = [...columns]
    const from = next.findIndex((column) => column.key === fromKey)
    const to = next.findIndex((column) => column.key === toKey)
    if (from < 0 || to < 0) return columns
    const [column] = next.splice(from, 1)
    next.splice(to, 0, column)
    return applyPins(next)
  }

  function readStore() {
    try {
      const raw = JSON.parse(localStorage.getItem(storageKey) || 'null')
      if (Array.isArray(raw)) return { order: raw, hidden: undefined, widths: {} }
      if (raw && typeof raw === 'object') {
        return {
          order: Array.isArray(raw.order) ? raw.order : (Array.isArray(raw.keys) ? raw.keys : []),
          hidden: Array.isArray(raw.hidden) ? raw.hidden : undefined,
          widths: sanitizeWidths(raw.widths),
          colors: sanitizeColors(raw.colors),
        }
      }
    } catch {
      /* ignore */
    }
    return null
  }

  function write(store) {
    try {
      localStorage.setItem(storageKey, JSON.stringify(store))
    } catch {
      /* ignore */
    }
  }

  function sanitizeWidths(widths) {
    const result = {}
    if (!widths || typeof widths !== 'object') return result
    const known = new Set(defaultColumns.map((column) => column.key))
    for (const [key, value] of Object.entries(widths)) {
      const width = Math.round(Number(value))
      if (known.has(key) && width >= MIN_COLUMN_WIDTH) {
        result[key] = Math.min(width, MAX_COLUMN_WIDTH)
      }
    }
    return result
  }

  function sanitizeHidden(hidden) {
    const known = new Set(defaultColumns.map((column) => column.key))
    return [...new Set(
      (hidden || [])
        .map((key) => String(key || ''))
        .filter((key) => key && known.has(key) && !isPinned(key)),
    )]
  }

  function load() {
    return merge(readStore()?.order || [])
  }

  function loadHidden() {
    const store = readStore()
    if (!store) return sanitizeHidden(defaultHidden)
    const seen = new Set((store.order || []).map((key) => String(key || '')))
    const storedHidden = sanitizeHidden(store.hidden || [])
    const unseen = sanitizeHidden(defaultHidden).filter((key) => !seen.has(key))
    return sanitizeHidden([...storedHidden, ...unseen])
  }

  function loadWidths() {
    return readStore()?.widths || {}
  }

  function loadColors() {
    return readStore()?.colors || {}
  }

  function save(columns, hidden) {
    const stored = readStore()
    write({
      order: (columns || []).map((column) => column.key),
      hidden: sanitizeHidden(
        hidden !== undefined ? hidden : (Array.isArray(stored?.hidden) ? stored.hidden : defaultHidden),
      ),
      widths: stored?.widths || {},
      colors: stored?.colors || {},
    })
  }

  // 只调了列宽或颜色时不写 order/hidden，免得把默认列序和显示字段固化下来。
  function patch(fields) {
    const stored = readStore()
    write(stored ? { order: stored.order, hidden: stored.hidden, widths: stored.widths, colors: stored.colors, ...fields } : fields)
  }

  function saveWidth(key, width) {
    patch({ widths: sanitizeWidths({ ...readStore()?.widths, [key]: width }) })
  }

  function saveColors(colors) {
    patch({ colors: sanitizeColors(colors) })
  }

  function clear() {
    try {
      localStorage.removeItem(storageKey)
    } catch {
      /* ignore */
    }
  }

  return { clear, load, loadColors, loadHidden, loadWidths, merge, move, save, saveColors, saveWidth }
}
