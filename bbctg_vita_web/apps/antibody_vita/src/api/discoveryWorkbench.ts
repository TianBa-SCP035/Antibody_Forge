import { requestClient, skipGlobalErrorHandler } from '#/api/request';

export const DISCOVERY_WORKBENCH_CREATED_KEY = 'discovery.workbench.created';

const SAVE_TIMEOUT = 5000;
const DOWNLOAD_TIMEOUT = 360_000;

type PostConfig = Parameters<typeof requestClient.post>[2];
type RequestConfig = Parameters<typeof requestClient.get>[1];
const downloadConfig = {
  skipErrorHandler: true,
} as Parameters<typeof requestClient.download>[1];

export function fetchDiscoveryWorkbenchList(data: any, config?: PostConfig) {
  return requestClient.post('/discovery/workbench/list', data, config);
}

export function fetchDiscoveryWorkbenchOptions(config?: RequestConfig) {
  return requestClient.get('/discovery/workbench/options', config);
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

export function copyDiscoveryWorkbench(id: number | string) {
  return requestClient.post('/discovery/workbench/copy', { id }, skipGlobalErrorHandler);
}

export function deleteDiscoveryWorkbench(id: number | string) {
  return requestClient.post('/discovery/workbench/delete', { id }, skipGlobalErrorHandler);
}

export function reorderDiscoveryWorkbench(movedId: number | string, targetId: number | string) {
  return requestClient.post(
    '/discovery/workbench/reorder',
    { moved_id: movedId, target_id: targetId },
    { timeout: SAVE_TIMEOUT, ...skipGlobalErrorHandler },
  );
}
