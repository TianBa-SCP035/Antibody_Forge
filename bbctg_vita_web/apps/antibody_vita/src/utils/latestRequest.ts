/**
 * 同一类请求只认最后发出的那次：慢的旧响应回来时直接丢弃，不覆盖新结果。
 *
 * const listRequest = createLatestRequest()
 * const isLatest = listRequest.begin()
 * const data = await fetchList()
 * if (!isLatest()) return
 */
export function createLatestRequest() {
  let current = 0;
  return {
    begin(): () => boolean {
      const id = ++current;
      return () => id === current;
    },
    /** 让进行中的请求全部作废，例如离开页面或切换对象时。 */
    cancel() {
      current += 1;
    },
  };
}

export type LatestRequest = ReturnType<typeof createLatestRequest>;
