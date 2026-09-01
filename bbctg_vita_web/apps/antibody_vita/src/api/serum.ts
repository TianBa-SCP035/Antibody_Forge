import { requestClient, skipGlobalErrorHandler } from '#/api/request';

export { skipGlobalErrorHandler };

const SAVE_TIMEOUT = 5000;
const AUTO_UPDATE_STATUS_TIMEOUT = 20_000;
const LONG_TIMEOUT = 360_000;

type RequestConfig = Parameters<typeof requestClient.get>[1];
type PostConfig = Parameters<typeof requestClient.post>[2];

const downloadConfig = {
  skipErrorHandler: true,
} as Parameters<typeof requestClient.download>[1];

export function fetchStats(config?: RequestConfig) {
  return requestClient.get('/serum/stats', config);
}

export function fetchList(data: any, config?: PostConfig) {
  return requestClient.post('/serum/list', data, config);
}

export function fetchDetail(id: any, config?: RequestConfig) {
  return requestClient.get('/serum/detail', {
    params: { id },
    ...skipGlobalErrorHandler,
    ...config,
  });
}

export interface SerumTargetOption {
  name: string;
  snum: string;
}

export function fetchSerumTargetOptions(keyword = '', codes: string[] = []) {
  return requestClient.get<{ items: SerumTargetOption[] }>('/serum/target_options', {
    params: { keyword, codes: codes.join(',') },
    ...skipGlobalErrorHandler,
  });
}

export function fetchSerumUserOptions() {
  return requestClient.get<{ items: string[] }>('/serum/user_options', {
    ...skipGlobalErrorHandler,
  });
}

export function saveSerum(data: any) {
  return requestClient.post('/serum/save', data, {
    timeout: SAVE_TIMEOUT,
    ...skipGlobalErrorHandler,
  });
}

export interface SerumDeleteResult {
  action: 'deleted' | 'reverted';
  message: string;
}

export function deleteSerum(id: any) {
  return requestClient.post<SerumDeleteResult>('/serum/delete', { id }, skipGlobalErrorHandler);
}

export function getSerumFilterOptions(config?: RequestConfig) {
  return requestClient.get('/serum/filter_options', {
    ...skipGlobalErrorHandler,
    ...config,
  });
}

export function updateSerumStatus(data: any) {
  return requestClient.post('/serum/update_status', data, skipGlobalErrorHandler);
}

export function updateCagePosition(data: any) {
  return requestClient.post('/serum/update_cage_position', data, skipGlobalErrorHandler);
}

export function updateLabNotebook(data: any) {
  return requestClient.post('/serum/update_lab_notebook', data, skipGlobalErrorHandler);
}

export function export_mouse(data: any) {
  return requestClient.download('/serum/export_mouse', {
    data,
    method: 'POST',
    timeout: LONG_TIMEOUT,
    ...downloadConfig,
  });
}

export function exportSerumList(data: any) {
  return requestClient.download('/serum/export_list', {
    data,
    method: 'POST',
    timeout: LONG_TIMEOUT,
    ...downloadConfig,
  });
}

export function exportScheme(data: { id?: number; ids?: number[] }) {
  return requestClient.download('/serum/export_scheme', {
    data,
    method: 'POST',
    timeout: LONG_TIMEOUT,
    ...downloadConfig,
  });
}

export function exportSchemePdf(data: { id?: number; ids?: number[] }) {
  return requestClient.download('/serum/export_scheme_pdf', {
    data,
    method: 'POST',
    timeout: LONG_TIMEOUT,
    ...downloadConfig,
  });
}

export function autoUpdateStatus(data: any) {
  return requestClient.post('/serum/auto_update_status', data, {
    timeout: AUTO_UPDATE_STATUS_TIMEOUT,
    ...skipGlobalErrorHandler,
  });
}

export function fetchCellInventoryData() {
  return requestClient.get('/serum/cell_inventory/data', skipGlobalErrorHandler);
}

export function updateProjectPrepStatus(data: {
  experiment_id: string;
  prep_status: string;
}) {
  return requestClient.post('/serum/project/prep_status', data, skipGlobalErrorHandler);
}

export function fetchIndexFiles(data: any, config?: PostConfig) {
  return requestClient.post('/serum/titer/file/list', data, config);
}

export function saveIndexFile(data: FormData) {
  return requestClient.post('/serum/titer/file/save', data, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: LONG_TIMEOUT,
    ...skipGlobalErrorHandler,
  });
}

export function deleteIndexFile(data: any) {
  return requestClient.post('/serum/titer/file/delete', data, skipGlobalErrorHandler);
}

export function renameIndexFile(data: any) {
  return requestClient.post('/serum/titer/file/rename', data, skipGlobalErrorHandler);
}

export function replaceIndexFile(data: FormData) {
  return requestClient.post('/serum/titer/file/replace', data, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: LONG_TIMEOUT,
    ...skipGlobalErrorHandler,
  });
}

export function saveTiterTargets(data: any) {
  return requestClient.post('/serum/titer/target/save', data, skipGlobalErrorHandler);
}

export function saveTiterPcs(data: any) {
  return requestClient.post('/serum/titer/pc/save', data, skipGlobalErrorHandler);
}

export function fetchFacsPlates(data: any, config?: PostConfig) {
  return requestClient.post('/serum/titer/plate/list', data, config);
}

export function saveFacsPlate(data: any) {
  return requestClient.post('/serum/titer/plate/save', data, skipGlobalErrorHandler);
}

export function deleteFacsPlate(id: any) {
  return requestClient.post('/serum/titer/plate/delete', { id }, skipGlobalErrorHandler);
}

export function fetchElisaPlates(data: any, config?: PostConfig) {
  return requestClient.post('/serum/titer/elisa/plate/list', data, config);
}

export function saveElisaPlate(data: any) {
  return requestClient.post('/serum/titer/elisa/plate/save', data, skipGlobalErrorHandler);
}

export function deleteElisaPlate(id: any) {
  return requestClient.post('/serum/titer/elisa/plate/delete', { id }, skipGlobalErrorHandler);
}

export function fetchTiterOrderMeta(config?: RequestConfig) {
  return requestClient.get('/serum/titer/order/meta', {
    ...skipGlobalErrorHandler,
    ...config,
  });
}

export function fetchTiterOrderStats(config?: RequestConfig) {
  return requestClient.get('/serum/titer/order/stats', {
    ...skipGlobalErrorHandler,
    ...config,
  });
}

export function fetchTiterOrderOwnerStats(
  params: { monthStart?: string; monthEnd?: string } = {},
  config?: RequestConfig,
) {
  const query: Record<string, string> = {};
  if (params.monthStart) {
    query.month_start = params.monthStart;
    query.month_end = params.monthEnd ?? params.monthStart;
  }
  return requestClient.get('/serum/titer/order/owner_stats', {
    params: Object.keys(query).length ? query : undefined,
    ...skipGlobalErrorHandler,
    ...config,
  });
}

export function fetchTiterOrderProjectOptions(params: {
  keyword?: string;
  limit?: number;
} = {}) {
  return requestClient.get('/serum/titer/order/project_options', {
    params,
    ...skipGlobalErrorHandler,
  });
}

export function fetchTiterOrderBatchPreview(experimentId: string, config?: RequestConfig) {
  return requestClient.get('/serum/titer/order/batch_preview', {
    params: { experiment_id: experimentId },
    ...skipGlobalErrorHandler,
    ...config,
  });
}

export function fetchTiterOrderList(data: any, config?: PostConfig) {
  return requestClient.post('/serum/titer/order/list', data, config);
}

export function exportTiterOrderList(data: any) {
  return requestClient.download('/serum/titer/order/export', {
    data,
    method: 'POST',
    timeout: LONG_TIMEOUT,
    ...downloadConfig,
  });
}

export function saveTiterOrder(data: any) {
  return requestClient.post('/serum/titer/order/save', data, skipGlobalErrorHandler);
}

export function deleteTiterOrder(id: number | string) {
  return requestClient.post('/serum/titer/order/delete', { id }, skipGlobalErrorHandler);
}

export interface SerumMouseGroup {
  age_weeks?: string;
  cage_position?: string;
  experiment_id?: string;
  group_id?: string;
  id?: number;
  mouse_count?: string;
  mouse_no_list?: string;
  mouse_registry?: { mice?: Array<{ alive?: boolean; no?: string; sex?: string }> } | null;
  mouse_strain?: string;
  mouse_strain_category?: string;
  remark?: string;
  sex?: string;
  vendor?: string;
}

export function fetchMouseGroups(experimentId: string, config?: RequestConfig) {
  return requestClient.get<{ items: SerumMouseGroup[] }>('/serum/mouse-groups', {
    params: { experiment_id: experimentId },
    ...skipGlobalErrorHandler,
    ...config,
  });
}

export function saveMouseRegistry(data: {
  experiment_id: string;
  group_id?: string;
  id?: number;
  mouse_no_list?: string;
  mouse_registry?: SerumMouseGroup['mouse_registry'];
}) {
  return requestClient.post<SerumMouseGroup>('/serum/mouse-registry/save', data, skipGlobalErrorHandler);
}
