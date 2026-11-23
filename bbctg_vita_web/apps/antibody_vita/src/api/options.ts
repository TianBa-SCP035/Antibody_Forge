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

/** 「本表已录入靶点」搜索；各模块 api 用自己的接口地址包一层，交给 WorkbenchTargetFilter 的 search。 */
export async function fetchRecordedTargets(
  endpoint: string,
  keyword = '',
  limit = 50,
): Promise<RecordedTargetOption[]> {
  const data = await requestClient.get<{ items: RecordedTargetOption[] }>(
    endpoint,
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
