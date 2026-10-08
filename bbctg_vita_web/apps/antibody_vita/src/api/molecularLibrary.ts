import { requestClient, skipGlobalErrorHandler } from '#/api/request';

export const LIBRARY_CREATED_KEY = 'molecular.library.created';

const SAVE_TIMEOUT = 5000;
const DOWNLOAD_TIMEOUT = 360_000;
const LONG_TIMEOUT = 120_000;

type PostConfig = Parameters<typeof requestClient.post>[2];
const downloadConfig = {
  skipErrorHandler: true,
} as Parameters<typeof requestClient.download>[1];

export function fetchLibraryOrderList(data: any, config?: PostConfig) {
  return requestClient.post('/molecular-cell/library-orders/list', data, config);
}

export function fetchLibraryMeta() {
  return requestClient.get('/molecular-cell/library-orders/meta');
}

export function fetchPrimerIndexOptions(params: {
  query?: string;
  family?: string;
  limit?: number;
} = {}) {
  return requestClient.get('/molecular-cell/library-orders/catalog/options', { params });
}

export function fetchLibraryOrdersByDiscovery(params: {
  discovery_workbench_id?: number | string;
  discovery_id?: string;
}) {
  return requestClient.get('/molecular-cell/library-orders/by-discovery', {
    params,
    ...skipGlobalErrorHandler,
  });
}

export function exportLibraryOrderList(data: any) {
  return requestClient.download('/molecular-cell/library-orders/export_list', {
    data,
    method: 'POST',
    timeout: DOWNLOAD_TIMEOUT,
    ...downloadConfig,
  });
}

export function saveLibraryOrder(data: any) {
  return requestClient.post('/molecular-cell/library-orders/save', data, {
    timeout: SAVE_TIMEOUT,
    ...skipGlobalErrorHandler,
  });
}

export function handoffLibraryOrders(data: any) {
  return requestClient.post('/molecular-cell/library-orders/handoff', data, {
    timeout: SAVE_TIMEOUT,
    ...skipGlobalErrorHandler,
  });
}

export function deleteLibraryOrder(id: number | string) {
  return requestClient.post(
    '/molecular-cell/library-orders/delete',
    { id },
    skipGlobalErrorHandler,
  );
}

export function fetchLibraryFiles(orderId: number | string) {
  return requestClient.post(
    '/molecular-cell/library-orders/files/list',
    { order_id: orderId },
    skipGlobalErrorHandler,
  );
}

export function uploadLibraryFile(data: FormData) {
  return requestClient.post('/molecular-cell/library-orders/files/upload', data, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: LONG_TIMEOUT,
    ...skipGlobalErrorHandler,
  });
}

export function deleteLibraryFile(data: { link_id: number; order_id?: number }) {
  return requestClient.post(
    '/molecular-cell/library-orders/files/delete',
    data,
    skipGlobalErrorHandler,
  );
}

export function updateLibraryFile(data: {
  link_id: number;
  order_id: number | string;
  original_name?: string;
  is_final_qc?: boolean;
  qc_regions?: null | Array<{
    x: number;
    y: number;
    width: number;
    height: number;
    label?: string;
  }>;
}) {
  return requestClient.post(
    '/molecular-cell/library-orders/files/update',
    data,
    skipGlobalErrorHandler,
  );
}

export function libraryFileDownloadUrl(id: number, extra = '') {
  return `/api/molecular-cell/library-orders/files/download?id=${id}${extra}`;
}
