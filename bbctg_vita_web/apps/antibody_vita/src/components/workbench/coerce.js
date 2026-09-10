export function coerceRequiredPositiveInt(raw) {
  const text = String(raw ?? '').trim()
  if (!/^\d+$/.test(text) || Number(text) < 1) return { ok: false, reason: 'integer' }
  return { ok: true, value: Number(text) }
}

export function coerceOptionalNonnegInt(raw) {
  const text = String(raw ?? '').trim()
  if (!text) return { ok: true, value: null }
  if (!/^\d+$/.test(text)) return { ok: false, reason: 'integer' }
  return { ok: true, value: Number(text) }
}
