export interface PrimerCatalogItem {
  name?: string
  short_sequence?: string
  [key: string]: unknown
}

export function loadPrimerCatalog(): Promise<PrimerCatalogItem[]>

export function clearPrimerCatalogCache(): void

export function filterPrimerCatalog(items: PrimerCatalogItem[], query: unknown): PrimerCatalogItem[]
