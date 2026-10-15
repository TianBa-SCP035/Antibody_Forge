/**
 * 列表筛选暂存。
 *
 * 同一 tabGroup 的子页面会顶掉列表页签，列表实例随之销毁；离开前存一份，重新挂载时恢复。
 * F5 冷启动由路由守卫按前缀统一清空，新列表接入时不用再去守卫里登记。
 */
const KEY_PREFIX = 'listFilters:';

export function saveListFilters(name: string, state: Record<string, unknown>) {
  sessionStorage.setItem(KEY_PREFIX + name, JSON.stringify(state));
}

export function loadListFilters(name: string): null | Record<string, any> {
  try {
    const state = JSON.parse(sessionStorage.getItem(KEY_PREFIX + name) || 'null');
    return state && typeof state === 'object' ? state : null;
  } catch {
    return null;
  }
}

export function clearAllListFilters() {
  Object.keys(sessionStorage)
    .filter((key) => key.startsWith(KEY_PREFIX))
    .forEach((key) => sessionStorage.removeItem(key));
}
