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
      if (Array.isArray(raw)) return { order: raw, hidden: undefined }
      if (raw && typeof raw === 'object') {
        return {
          order: Array.isArray(raw.order) ? raw.order : (Array.isArray(raw.keys) ? raw.keys : []),
          hidden: Array.isArray(raw.hidden) ? raw.hidden : undefined,
        }
      }
    } catch {
      /* ignore */
    }
    return null
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

  function save(columns, hidden) {
    try {
      const stored = readStore()?.hidden
      localStorage.setItem(storageKey, JSON.stringify({
        order: (columns || []).map((column) => column.key),
        hidden: sanitizeHidden(
          hidden !== undefined ? hidden : (Array.isArray(stored) ? stored : defaultHidden),
        ),
      }))
    } catch {
      /* ignore */
    }
  }

  function clear() {
    try {
      localStorage.removeItem(storageKey)
    } catch {
      /* ignore */
    }
  }

  return { clear, load, loadHidden, merge, move, save }
}
