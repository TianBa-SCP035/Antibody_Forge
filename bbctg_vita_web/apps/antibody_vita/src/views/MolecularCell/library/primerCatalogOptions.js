import { fetchPrimerIndexOptions } from '#/api/molecularLibrary'

import { reverseComplement } from './primerSearch'

const CATALOG_LIMIT = 2000
const DNA_PATTERN = /^[ACGTN]+$/

let cachedPrimers = null
let catalogRequest = null

export async function loadPrimerCatalog() {
  if (cachedPrimers) return cachedPrimers
  if (!catalogRequest) {
    catalogRequest = fetchPrimerIndexOptions({ limit: CATALOG_LIMIT })
      .then((data) => {
        cachedPrimers = data?.items || []
        return cachedPrimers
      })
      .finally(() => {
        catalogRequest = null
      })
  }
  return catalogRequest
}

export function filterPrimerCatalog(items, query) {
  const keyword = String(query || '').trim()
  if (!keyword) return []
  const sequence = keyword.replace(/\s+/g, '').toUpperCase()
  const dna = DNA_PATTERN.test(sequence)
  const flipped = dna ? reverseComplement(sequence) : ''
  const nameQuery = keyword.toLowerCase()
  const textQuery = keyword.toUpperCase()
  return items.filter((item) => {
    if (String(item.name || '').toLowerCase().includes(nameQuery)) return true
    const display = String(item.short_sequence || '').toUpperCase()
    if (dna) return display.includes(sequence) || display.includes(flipped)
    return display.includes(textQuery)
  })
}
