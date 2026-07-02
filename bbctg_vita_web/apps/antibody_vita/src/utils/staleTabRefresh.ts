import { onActivated, ref } from 'vue';

/**
 * keepAlive 页切走再回来时，超过 TTL 则静默重新拉数据。
 *
 * 仅依赖 Vue 的 `activated`（Tab 切回 / 从缓存恢复时触发）；
 * 用户一直停留在当前页时不会触发——那需要 visibility / 轮询等另做。
 */
export const TAB_DATA_TTL_MS = 10 * 60 * 1000;

export function shouldRefreshTabData(
  lastFetchedAt: number,
  ttlMs: number = TAB_DATA_TTL_MS,
): boolean {
  return lastFetchedAt > 0 && Date.now() - lastFetchedAt > ttlMs;
}

/** 组合式 API 页面：切回 Tab 时按 TTL 自动刷新 */
export function useStaleTabRefresh(onRefresh: () => void | Promise<void>) {
  const lastFetchedAt = ref(0);

  function markTabDataFetched() {
    lastFetchedAt.value = Date.now();
  }

  onActivated(() => {
    if (shouldRefreshTabData(lastFetchedAt.value)) {
      void onRefresh();
    }
  });

  return { markTabDataFetched };
}
