import { requestClient, skipGlobalErrorHandler } from '#/api/request';
import { fetchRecordedTargets } from '#/api/options';
import { LIBRARY_EDIT } from '#/api/molecularLibrary';

export const TRANSFECTION_PAGE = 'molecular.page.transfection';
export const TRANSFECTION_EDIT = 'molecular.transfection.edit';
/** 从文库构建把单细胞孔板交接过来：有任一权限即可 */
export const TRANSFECTION_LIBRARY_HANDOFF = [TRANSFECTION_EDIT, LIBRARY_EDIT];

const SAVE_TIMEOUT = 5000;
const LONG_TIMEOUT = 120_000;
const DOWNLOAD_TIMEOUT = 360_000;
const BASE = '/molecular-cell/transfection';

type PostConfig = Parameters<typeof requestClient.post>[2];
const downloadConfig = {
  skipErrorHandler: true,
} as Parameters<typeof requestClient.download>[1];

export type ProteinImportItem = {
  row: number;
  protein_name: string;
  heavy_chain: string;
  light_chain: string;
};

export function fetchTransfectionRecordedTargets(keyword = '') {
  return fetchRecordedTargets(`${BASE}/recorded_targets`, keyword);
}

export function fetchTransfectionOptions() {
  return requestClient.get(`${BASE}/options`, skipGlobalErrorHandler);
}

export function fetchTransfectionList(data: any, config?: PostConfig) {
  return requestClient.post(`${BASE}/list`, data, { ...skipGlobalErrorHandler, ...config });
}

export function fetchTransfectionColumnValues(data: any, config?: PostConfig) {
  return requestClient.post(`${BASE}/column_values`, data, { ...skipGlobalErrorHandler, ...config });
}

export function exportTransfectionList(data: any) {
  return requestClient.download(`${BASE}/export_list`, {
    data,
    method: 'POST',
    timeout: DOWNLOAD_TIMEOUT,
    ...downloadConfig,
  });
}

export function saveTransfectionOrder(data: any) {
  return requestClient.post(`${BASE}/save`, data, { timeout: SAVE_TIMEOUT, ...skipGlobalErrorHandler });
}

export function batchSaveTransfectionOrders(data: any) {
  return requestClient.post(`${BASE}/batch_save`, data, { timeout: LONG_TIMEOUT, ...skipGlobalErrorHandler });
}

export function deleteTransfectionOrder(id: number | string) {
  return requestClient.post(`${BASE}/delete`, { id }, skipGlobalErrorHandler);
}

export function handoffLibraryToTransfection(libraryOrderId: number | string) {
  return requestClient.post(
    `${BASE}/handoff_library`,
    { library_order_id: libraryOrderId },
    { timeout: SAVE_TIMEOUT, ...skipGlobalErrorHandler },
  );
}

export function handoffTransfectionToSynthesis(id: number | string) {
  return requestClient.post(`${BASE}/handoff_synthesis`, { id }, { timeout: SAVE_TIMEOUT, ...skipGlobalErrorHandler });
}

export function fetchOrderProteins(orderId: number | string) {
  return requestClient.get(`${BASE}/order_proteins`, { params: { order_id: orderId }, ...skipGlobalErrorHandler });
}

export function importTransfectionProteins(orderId: number | string, items: ProteinImportItem[]) {
  return requestClient.post(
    `${BASE}/proteins/import`,
    { order_id: orderId, items },
    { timeout: LONG_TIMEOUT, ...skipGlobalErrorHandler },
  );
}

export function clearTransfectionProteins(orderId: number | string) {
  return requestClient.post(`${BASE}/proteins/clear`, { id: orderId }, { timeout: SAVE_TIMEOUT, ...skipGlobalErrorHandler });
}

export function exportOrderProteins(orderId: number | string) {
  return requestClient.download(`${BASE}/order_proteins/export`, {
    params: { order_id: orderId },
    timeout: DOWNLOAD_TIMEOUT,
    ...downloadConfig,
  });
}

export function fetchTransfectionProteins(data: any, config?: PostConfig) {
  return requestClient.post(`${BASE}/proteins/list`, data, { ...skipGlobalErrorHandler, ...config });
}

export function fetchTransfectionProteinColumnValues(data: any, config?: PostConfig) {
  return requestClient.post(`${BASE}/proteins/column_values`, data, { ...skipGlobalErrorHandler, ...config });
}

export function exportTransfectionProteins(data: any) {
  return requestClient.download(`${BASE}/proteins/export`, {
    data,
    method: 'POST',
    timeout: DOWNLOAD_TIMEOUT,
    ...downloadConfig,
  });
}