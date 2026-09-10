import { fetchSerumTargetOptions } from '#/api/serum'

export function uniqueTargetCodes(values) {
  return [
    ...new Set(
      (Array.isArray(values) ? values : String(values || '').split(/[,，]/))
        .map((item) => String(item || '').trim())
        .filter(Boolean),
    ),
  ]
}

export function targetNameFromCodes(codes, items = []) {
  return uniqueTargetCodes(codes)
    .map((code) => items.find((item) => item.snum === code)?.name || code)
    .join('&')
}

export async function searchWorkbenchTargets(keyword = '', codes = []) {
  const data = await fetchSerumTargetOptions(keyword || '', uniqueTargetCodes(codes))
  return data?.items || []
}

export function splitTargetNames(value) {
  return [
    ...new Set(
      String(value || '')
        .split(/[&＆]/)
        .map((item) => item.trim())
        .filter(Boolean),
    ),
  ]
}
