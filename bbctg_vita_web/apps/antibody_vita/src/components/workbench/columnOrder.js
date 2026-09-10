export function createColumnOrder(storageKey, defaultColumns, { pinFirstKey } = {}) {
  function merge(cachedKeys) {
    const remaining = new Map(defaultColumns.map((column) => [column.key, column]))
    const ordered = []
    const keys = [...(cachedKeys || [])]
    if (pinFirstKey && remaining.has(pinFirstKey) && !keys.includes(pinFirstKey)) {
      keys.unshift(pinFirstKey)
    }
    for (const key of keys) {
      const column = remaining.get(String(key || ''))
      if (!column) continue
      ordered.push(column)
      remaining.delete(column.key)
    }
    for (const column of defaultColumns) {
      if (remaining.has(column.key)) ordered.push(column)
    }
    return ordered
  }

  function load() {
    try {
      const keys = JSON.parse(localStorage.getItem(storageKey) || '[]')
      return merge(Array.isArray(keys) ? keys : [])
    } catch {
      return [...defaultColumns]
    }
  }

  function save(columns) {
    try {
      localStorage.setItem(storageKey, JSON.stringify((columns || []).map((column) => column.key)))
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

  return { clear, load, merge, save }
}
