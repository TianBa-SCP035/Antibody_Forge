import { requestClient, skipGlobalErrorHandler } from '#/api/request';

export interface CatalogTargetOption {
  name: string;
  snum: string;
  structural_properties?: string | null;
  structure_feature?: string | null;
}

export interface RecordedTargetOption {
  value: string;
  label: string;
  aliases?: string[];
  codes?: string[];
}

export function fetchCatalogTargetOptions(
  keyword = '',
  codes: string[] = [],
  limit = 20,
) {
  return requestClient.get<{ items: CatalogTargetOption[] }>('/options/targets', {
    params: { keyword, codes: codes.join(','), limit },
    ...skipGlobalErrorHandler,
  });
}

/** 各列表页「本表已录入靶点」搜索接口；顶部靶点筛选按页面取对应一项。 */
export const RECORDED_TARGET_ENDPOINTS = {
  discoveryWorkbench: '/discovery/workbench/recorded_targets',
  library: '/molecular-cell/library-orders/recorded_targets',
  serumList: '/serum/recorded_targets',
  serumWorkbench: '/serum/workbench/recorded_targets',
  synthesisProgress: '/discovery/synthesis-progress/recorded_targets',
  titerOrder: '/serum/titer/order/recorded_targets',
} as const;

export type RecordedTargetScope = keyof typeof RECORDED_TARGET_ENDPOINTS;

export async function fetchRecordedTargets(
  scope: RecordedTargetScope,
  keyword = '',
  limit = 50,
): Promise<RecordedTargetOption[]> {
  const data = await requestClient.get<{ items: RecordedTargetOption[] }>(
    RECORDED_TARGET_ENDPOINTS[scope],
    { params: { keyword, limit }, ...skipGlobalErrorHandler },
  );
  return data?.items || [];
}

export function fetchUserOptions(keyword = '', limit = 30) {
  return requestClient.get<{ items: string[] }>('/options/users', {
    params: { keyword, limit },
    ...skipGlobalErrorHandler,
  });
}
