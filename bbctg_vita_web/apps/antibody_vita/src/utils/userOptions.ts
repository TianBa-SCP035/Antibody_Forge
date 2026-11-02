import { fetchUserOptions } from '#/api/options';

const cache = new Map<string, string[]>();
const inflight = new Map<string, Promise<string[]>>();
// 粘贴校验要拿到全部在职人员（现约 2200 人），下拉只给 VxeSelect（自带虚拟滚动）用。
const ALL_USERS_LIMIT = 5000;

function uniqueNames(values: Array<string | null | undefined>) {
  return [
    ...new Set(
      values.map((item) => String(item || '').trim()).filter(Boolean),
    ),
  ];
}

function cacheKey(keyword: string, limit: number) {
  return `${String(keyword || '').trim().toLowerCase()}|${limit}`;
}

/** 已缓存的无关键字名单（整份优先），给首次打开下拉用。 */
export function getCachedUserNames(): string[] {
  return cache.get(cacheKey('', ALL_USERS_LIMIT)) || cache.get(cacheKey('', 30)) || [];
}

export async function searchUserNames(keyword = '', limit = 30): Promise<string[]> {
  const key = cacheKey(keyword, limit);
  const hit = cache.get(key);
  if (hit) return hit;
  let request = inflight.get(key);
  if (!request) {
    request = fetchUserOptions(keyword, limit)
      .then((data) => {
        const items = uniqueNames(data?.items || []);
        cache.set(key, items);
        return items;
      })
      .finally(() => {
        inflight.delete(key);
      });
    inflight.set(key, request);
  }
  return request;
}

/** 整份在职人员名单，给表格粘贴校验和批量下拉用。 */
export function loadAllUserNames(): Promise<string[]> {
  return searchUserNames('', ALL_USERS_LIMIT);
}

export { uniqueNames };
