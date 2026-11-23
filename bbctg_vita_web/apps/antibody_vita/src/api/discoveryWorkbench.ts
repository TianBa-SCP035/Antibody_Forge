import { requestClient, skipGlobalErrorHandler } from '#/api/request';
import { fetchRecordedTargets } from '#/api/options';

export const DISCOVERY_WORKBENCH_EDIT = 'discovery.workbench.edit';
/** 别的页面新建发现行后跳过来定位（sessionStorage），键值已发布不要改 */
export const DISCOVERY_WORKBENCH_CREATED_KEY = 'discovery.workbench.created';

const SAVE_TIMEOUT = 5000;
const DOWNLOAD_TIMEOUT = 360_000;

type PostConfig = Parameters<typeof requestClient.post>[2];
type RequestConfig = Parameters<typeof requestClient.get>[1];
const downloadConfig = {
  skipErrorHandler: true,
} as Parameters<typeof requestClient.download>[1];

export function fetchDiscoveryWorkbenchRecordedTargets(keyword = '') {
  return fetchRecordedTargets('/discovery/workbench/recorded_targets', keyword);
}

export function fetchDiscoveryWorkbenchList(data: any, config?: PostConfig) {
  return requestClient.post('/discovery/workbench/list', data, {
    ...skipGlobalErrorHandler,
    ...config,
  });
}

export function fetchDiscoveryWorkbenchColumnValues(data: any, config?: PostConfig) {
  return requestClient.post('/discovery/workbench/column_values', data, {
    ...skipGlobalErrorHandler,
    ...config,
  });
}

export function fetchDiscoveryWorkbenchOptions(config?: RequestConfig) {
  return requestClient.get('/discovery/workbench/options', {
    ...skipGlobalErrorHandler,
    ...config,
  });
}

export function exportDiscoveryWorkbenchList(data: any) {
  return requestClient.download('/discovery/workbench/export_list', {
    data,
    method: 'POST',
    timeout: DOWNLOAD_TIMEOUT,
    ...downloadConfig,
  });
}

export function saveDiscoveryWorkbench(data: any) {
  return requestClient.post('/discovery/workbench/save', data, {
    timeout: SAVE_TIMEOUT,
    ...skipGlobalErrorHandler,
  });
}

export function saveDiscoveryWorkbenchBatch(data: any) {
  return requestClient.post('/discovery/workbench/save_batch', data, {
    timeout: SAVE_TIMEOUT,
    ...skipGlobalErrorHandler,
  });
}

export function deleteDiscoveryWorkbench(id: number | string) {
  return requestClient.post('/discovery/workbench/delete', { id }, skipGlobalErrorHandler);
}

export function fetchDiscoveryCellBank(workbenchId: number | string) {
  return requestClient.get('/discovery/workbench/cell_bank', {
    params: { workbench_id: workbenchId },
    ...skipGlobalErrorHandler,
  });
}

export function saveDiscoveryCellBank(data: any) {
  return requestClient.post('/discovery/workbench/cell_bank/save', data, {
    timeout: SAVE_TIMEOUT,
    ...skipGlobalErrorHandler,
  });
}

export function deleteDiscoveryCellBank(id: number | string) {
  return requestClient.post('/discovery/workbench/cell_bank/delete', { id }, skipGlobalErrorHandler);
}

export function reorderDiscoveryWorkbench(movedId: number | string, targetId: number | string) {
  return requestClient.post(
    '/discovery/workbench/reorder',
    { moved_id: movedId, target_id: targetId },
    { timeout: SAVE_TIMEOUT, ...skipGlobalErrorHandler },
  );
}
