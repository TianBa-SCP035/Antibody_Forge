import { requestClient, skipGlobalErrorHandler } from '#/api/request';

const BASE = '/molecular-cell/library-orders/catalog';
const downloadConfig = {
  skipErrorHandler: true,
} as Parameters<typeof requestClient.download>[1];

export interface PrimerItem {
  id: number;
  name: string;
  family: string;
  direction: null | string;
  version: null | string;
  short_sequence: string;
  homology_arm_1: null | string;
  homology_arm_2: null | string;
  note: null | string;
  active: boolean;
  updated_at?: null | string;
}

export interface PrimerListQuery {
  name?: string;
  sequence?: string;
  check_keyword?: string;
  note?: string;
  family?: string;
  direction?: string;
  active?: boolean;
  page?: number;
  limit?: number;
}

export type PrimerSavePayload = Omit<
  PrimerItem,
  'id' | 'updated_at' | 'version' | 'homology_arm_1' | 'homology_arm_2'
> & { id?: number };

export interface PrimerListResult {
  items: PrimerItem[];
  total: number;
  page: number;
  limit: number;
  stats: {
    total: number;
    families: { name: string; count: number }[];
  };
}

export function fetchPrimerCatalog(data: PrimerListQuery = {}) {
  return requestClient.post<PrimerListResult>(`${BASE}/list`, data);
}

export function savePrimer(data: PrimerSavePayload) {
  return requestClient.post<PrimerItem>(`${BASE}/save`, data, {
    timeout: 5000,
    ...skipGlobalErrorHandler,
  });
}

export function fetchPrimerIds(data: PrimerListQuery = {}) {
  return requestClient.post<{ ids: number[] }>(`${BASE}/ids`, data);
}

export function batchUpdatePrimers(data: { ids: number[]; active?: boolean; family?: string }) {
  return requestClient.post<{ total: number }>(`${BASE}/batch_update`, data, {
    timeout: 30_000,
    ...skipGlobalErrorHandler,
  });
}

export function batchDeletePrimers(ids: number[]) {
  return requestClient.post<{ deleted: number; skipped: string[] }>(`${BASE}/batch_delete`, { ids }, {
    timeout: 30_000,
    ...skipGlobalErrorHandler,
  });
}

export function deletePrimer(id: number) {
  return requestClient.post<{ id: number }>(`${BASE}/delete`, { id }, {
    timeout: 5000,
    ...skipGlobalErrorHandler,
  });
}

export function batchSavePrimers(items: PrimerSavePayload[]) {
  return requestClient.post<{ created: number; total: number; updated: number }>(
    `${BASE}/batch_save`,
    { items },
    { timeout: 120_000, ...skipGlobalErrorHandler },
  );
}

export function exportPrimerCatalog(data: PrimerListQuery) {
  return requestClient.download(`${BASE}/export`, {
    data,
    method: 'POST',
    timeout: 360_000,
    ...downloadConfig,
  });
}
