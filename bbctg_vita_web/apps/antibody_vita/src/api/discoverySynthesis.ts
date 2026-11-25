import { requestClient, skipGlobalErrorHandler } from '#/api/request';
import { fetchRecordedTargets } from '#/api/options';

export const SYNTHESIS_EDIT = 'discovery.synthesis_progress.edit';
export const SYNTHESIS_PM_EDIT = 'discovery.synthesis_progress.pm_edit';
export const SYNTHESIS_ENG_EDIT = 'discovery.synthesis_progress.eng_edit';
export const SYNTHESIS_AFFINITY_EDIT = 'discovery.synthesis_progress.affinity_edit';
export const SYNTHESIS_FLOW_EDIT = 'discovery.synthesis_progress.flow_edit';

const SAVE_TIMEOUT = 5000;
const REMOTE_CHECK_TIMEOUT = 3000;
const SYNC_NOW_TIMEOUT = 30_000;
const DOWNLOAD_TIMEOUT = 360_000;
// 合成公司查询接口大单要几十秒
const PLATE_QUERY_TIMEOUT = 90_000;

type PostConfig = Parameters<typeof requestClient.post>[2];
type RequestConfig = Parameters<typeof requestClient.get>[1];
const downloadConfig = {
  skipErrorHandler: true,
} as Parameters<typeof requestClient.download>[1];

export function fetchSynthesisRecordedTargets(keyword = '') {
  return fetchRecordedTargets('/discovery/synthesis-progress/recorded_targets', keyword);
}

export function fetchDiscoverySynthesisList(data: any, config?: PostConfig) {
  return requestClient.post('/discovery/synthesis-progress/list', data, {
    ...skipGlobalErrorHandler,
    ...config,
  });
}

export function fetchDiscoverySynthesisColumnValues(data: any, config?: PostConfig) {
  return requestClient.post('/discovery/synthesis-progress/column_values', data, {
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

export function fetchSynthesisTransfectionPairs(id: number | string) {
  return requestClient.get('/discovery/synthesis-progress/transfection_pairs', {
    params: { id },
    ...skipGlobalErrorHandler,
  });
}

export function exportSynthesisPlateLayout(id: number | string) {
  return requestClient.download('/discovery/synthesis-progress/plate_layout', {
    params: { id },
    timeout: DOWNLOAD_TIMEOUT,
    ...downloadConfig,
  });
}

export function fetchSynthesisPlateLayoutPreview(id: number | string) {
  return requestClient.get('/discovery/synthesis-progress/plate_layout/preview', {
    params: { id },
    ...skipGlobalErrorHandler,
  });
}

export function querySynthesisPlateLayout(id: number | string) {
  return requestClient.post(
    '/discovery/synthesis-progress/plate_layout/query',
    {},
    { params: { id }, timeout: PLATE_QUERY_TIMEOUT, ...skipGlobalErrorHandler },
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
