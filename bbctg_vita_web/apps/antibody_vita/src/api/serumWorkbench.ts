import { requestClient, skipGlobalErrorHandler } from '#/api/request';

const SAVE_TIMEOUT = 5000;
const DOWNLOAD_TIMEOUT = 360_000;

type PostConfig = Parameters<typeof requestClient.post>[2];
type RequestConfig = Parameters<typeof requestClient.get>[1];
const downloadConfig = {
  skipErrorHandler: true,
} as Parameters<typeof requestClient.download>[1];

export function fetchWorkbenchList(data: any, config?: PostConfig) {
  return requestClient.post('/serum/workbench/list', data, config);
}

export function fetchWorkbenchOptions(config?: RequestConfig) {
  return requestClient.get('/serum/workbench/options', config);
}

export function exportWorkbenchList(data: any) {
  return requestClient.download('/serum/workbench/export_list', {
    data,
    method: 'POST',
    timeout: DOWNLOAD_TIMEOUT,
    ...downloadConfig,
  });
}

export function fetchWorkbenchDetail(id: number | string, config?: RequestConfig) {
  return requestClient.get('/serum/workbench/detail', {
    params: { id },
    ...skipGlobalErrorHandler,
    ...config,
  });
}

export function saveWorkbench(data: any) {
  return requestClient.post('/serum/workbench/save', data, {
    timeout: SAVE_TIMEOUT,
    ...skipGlobalErrorHandler,
  });
}

export function saveWorkbenchBatch(data: any) {
  return requestClient.post('/serum/workbench/save_batch', data, {
    timeout: SAVE_TIMEOUT,
    ...skipGlobalErrorHandler,
  });
}

export function saveWorkbenchScheme(data: any) {
  return requestClient.post('/serum/workbench/save_scheme', data, {
    timeout: SAVE_TIMEOUT,
    ...skipGlobalErrorHandler,
  });
}

export function deleteWorkbench(id: number | string) {
  return requestClient.post('/serum/workbench/delete', { id }, skipGlobalErrorHandler);
}

export function startWorkbench(id: number | string) {
  return requestClient.post(
    '/serum/workbench/start',
    { id },
    { timeout: SAVE_TIMEOUT, ...skipGlobalErrorHandler },
  );
}

export function unlistWorkbench(id: number | string) {
  return requestClient.post(
    '/serum/workbench/unlist',
    { id },
    { timeout: SAVE_TIMEOUT, ...skipGlobalErrorHandler },
  );
}

export function copyWorkbench(id: number | string) {
  return requestClient.post(
    '/serum/workbench/copy',
    { id },
    { timeout: SAVE_TIMEOUT, ...skipGlobalErrorHandler },
  );
}

export function reorderWorkbench(
  ids: Array<number | string>,
  movedId: number | string,
  expectedRows: Array<{ id: number | string; priority: string; sort_order: number }>,
) {
  return requestClient.post(
    '/serum/workbench/reorder',
    { ids, moved_id: movedId, expected_rows: expectedRows },
    { timeout: SAVE_TIMEOUT, ...skipGlobalErrorHandler },
  );
}
