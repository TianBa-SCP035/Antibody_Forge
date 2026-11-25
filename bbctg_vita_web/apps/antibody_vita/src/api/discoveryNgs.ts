import { requestClient, skipGlobalErrorHandler } from '#/api/request';
import { fetchRecordedTargets } from '#/api/options';
import { LIBRARY_EDIT } from '#/api/molecularLibrary';

export const NGS_PAGE = 'discovery.page.ngs';
export const NGS_EDIT = 'discovery.ngs.edit';
/** 从文库构建把测序类工单交接过来：有任一权限即可 */
export const NGS_LIBRARY_HANDOFF = [NGS_EDIT, LIBRARY_EDIT];

const SAVE_TIMEOUT = 5000;
const DOWNLOAD_TIMEOUT = 360_000;
const BASE = '/discovery/ngs';

type PostConfig = Parameters<typeof requestClient.post>[2];
const downloadConfig = {
  skipErrorHandler: true,
} as Parameters<typeof requestClient.download>[1];

export function fetchNgsRecordedTargets(keyword = '') {
  return fetchRecordedTargets(`${BASE}/recorded_targets`, keyword);
}

export function fetchNgsOptions() {
  return requestClient.get(`${BASE}/options`, skipGlobalErrorHandler);
}

export function fetchNgsList(data: any, config?: PostConfig) {
  return requestClient.post(`${BASE}/list`, data, { ...skipGlobalErrorHandler, ...config });
}

export function fetchNgsColumnValues(data: any, config?: PostConfig) {
  return requestClient.post(`${BASE}/column_values`, data, { ...skipGlobalErrorHandler, ...config });
}

export function exportNgsList(data: any) {
  return requestClient.download(`${BASE}/export_list`, {
    data,
    method: 'POST',
    timeout: DOWNLOAD_TIMEOUT,
    ...downloadConfig,
  });
}

export function saveNgsRun(data: any) {
  return requestClient.post(`${BASE}/save`, data, { timeout: SAVE_TIMEOUT, ...skipGlobalErrorHandler });
}

export function batchSaveNgsRuns(data: any) {
  return requestClient.post(`${BASE}/batch_save`, data, { timeout: SAVE_TIMEOUT, ...skipGlobalErrorHandler });
}

export function deleteNgsRun(id: number | string) {
  return requestClient.post(`${BASE}/delete`, { id }, skipGlobalErrorHandler);
}

export function handoffLibraryToNgs(libraryOrderId: number | string) {
  return requestClient.post(
    `${BASE}/handoff_library`,
    { library_order_id: libraryOrderId },
    { timeout: SAVE_TIMEOUT, ...skipGlobalErrorHandler },
  );
}

export function handoffNgsToSynthesis(id: number | string) {
  return requestClient.post(`${BASE}/handoff_synthesis`, { id }, { timeout: SAVE_TIMEOUT, ...skipGlobalErrorHandler });
}
