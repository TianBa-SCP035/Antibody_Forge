import { requestClient, skipGlobalErrorHandler } from '#/api/request';

const SAVE_TIMEOUT = 5000;
const REMOTE_CHECK_TIMEOUT = 3000;
const SYNC_NOW_TIMEOUT = 30_000;
const DOWNLOAD_TIMEOUT = 360_000;

type PostConfig = Parameters<typeof requestClient.post>[2];
type RequestConfig = Parameters<typeof requestClient.get>[1];
const downloadConfig = {
  skipErrorHandler: true,
} as Parameters<typeof requestClient.download>[1];

export function fetchDiscoverySynthesisList(data: any, config?: PostConfig) {
  return requestClient.post('/discovery/synthesis-progress/list', data, {
    ...skipGlobalErrorHandler,
    ...config,
  });
}

export function fetchDiscoverySynthesisOptions(config?: RequestConfig) {
  return requestClient.get('/discovery/synthesis-progress/options', {
    ...skipGlobalErrorHandler,
    ...config,
  });
}

export function checkRemoteDiscoverySynthesis(ids: number[], config?: PostConfig) {
  return requestClient.post(
    '/discovery/synthesis-progress/check_remote',
    { ids },
    {
      timeout: REMOTE_CHECK_TIMEOUT,
      ...skipGlobalErrorHandler,
      ...config,
    },
  );
}

export function saveDiscoverySynthesis(data: any) {
  return requestClient.post('/discovery/synthesis-progress/save', data, {
    timeout: SAVE_TIMEOUT,
    ...skipGlobalErrorHandler,
  });
}

export function saveDiscoverySynthesisBatch(data: any) {
  return requestClient.post('/discovery/synthesis-progress/save_batch', data, {
    timeout: SAVE_TIMEOUT,
    ...skipGlobalErrorHandler,
  });
}

export function deleteDiscoverySynthesis(id: number | string) {
  return requestClient.post(
    '/discovery/synthesis-progress/delete',
    { id },
    skipGlobalErrorHandler,
  );
}

export function claimDiscoverySynthesis(id: number | string) {
  return requestClient.post(
    '/discovery/synthesis-progress/claim',
    { id },
    {
      timeout: SAVE_TIMEOUT,
      ...skipGlobalErrorHandler,
    },
  );
}

export function reorderDiscoverySynthesis(
  movedId: number | string,
  targetId: number | string,
) {
  return requestClient.post(
    '/discovery/synthesis-progress/reorder',
    { moved_id: movedId, target_id: targetId },
    {
      timeout: SAVE_TIMEOUT,
      ...skipGlobalErrorHandler,
    },
  );
}

export function adoptDiscoverySynthesisSource(
  id: number | string,
  fields?: string[],
) {
  return requestClient.post(
    '/discovery/synthesis-progress/adopt_source',
    { id, fields },
    {
      timeout: SAVE_TIMEOUT,
      ...skipGlobalErrorHandler,
    },
  );
}

export function syncDiscoverySynthesisOrdersNow() {
  return requestClient.post(
    '/discovery/synthesis-progress/sync_now',
    {},
    {
      timeout: SYNC_NOW_TIMEOUT,
      ...skipGlobalErrorHandler,
    },
  );
}

export function exportDiscoverySynthesisList(data: any) {
  return requestClient.download('/discovery/synthesis-progress/export_list', {
    data,
    method: 'POST',
    timeout: DOWNLOAD_TIMEOUT,
    ...downloadConfig,
  });
}
