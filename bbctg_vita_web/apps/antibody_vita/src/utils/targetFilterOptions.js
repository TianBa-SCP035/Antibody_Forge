export function normalizeTargetOptions(values) {
  return (values || []).map((item) => {
    if (item && typeof item === 'object') {
      const value = String(item.value || '').trim()
      const codes = Array.isArray(item.codes)
        ? item.codes.map((code) => String(code || '').trim()).filter(Boolean)
        : []
      const aliases = Array.isArray(item.aliases)
        ? item.aliases.map((name) => String(name || '').trim()).filter(Boolean)
        : []
      return { value, label: String(item.label || value), codes, aliases }
    }
    const value = String(item || '').trim()
    return { value, label: value, codes: [], aliases: [] }
  }).filter((item) => item.value)
}

export function filterTargetOptions(options, query) {
  const text = String(query || '').trim().toLowerCase()
  const list = options || []
  if (!text) return list
  const fields = (item) => ({
    label: String(item.label || '').toLowerCase(),
    aliases: (item.aliases || []).map((name) => String(name).toLowerCase()),
    codes: (item.codes || []).map((code) => String(code).toLowerCase()),
  })
  const rank = (item) => {
    const { label, aliases, codes } = fields(item)
    if (label.startsWith(text)) return 0
    if (aliases.some((name) => name.startsWith(text))) return 1
    if (codes.some((code) => code.startsWith(text))) return 2
    if (label.includes(text)) return 3
    if (aliases.some((name) => name.includes(text))) return 4
    return 5
  }
  return list
    .filter((item) => {
      const { label, aliases, codes } = fields(item)
      return label.includes(text)
        || aliases.some((name) => name.includes(text))
        || codes.some((code) => code.includes(text))
    })
    .sort((left, right) => {
      const gap = rank(left) - rank(right)
      if (gap) return gap
      return String(left.label).localeCompare(String(right.label))
    })
}

export function targetOptionExtra(item, query) {
  const text = String(query || '').trim().toLowerCase()
  if (!text) return ''
  if (String(item?.label || '').toLowerCase().includes(text)) return ''
  const extras = []
  for (const alias of item?.aliases || []) {
    const name = String(alias || '').trim()
    if (name && name.toLowerCase().includes(text)) extras.push(name)
  }
  for (const code of item?.codes || []) {
    const name = String(code || '').trim()
    if (name && name.toLowerCase().includes(text)) extras.push(name)
  }
  return extras.join('、')
}
