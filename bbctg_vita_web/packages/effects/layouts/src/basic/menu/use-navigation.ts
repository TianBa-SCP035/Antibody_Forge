import type { RouteRecordNormalized } from 'vue-router';

import { ref } from 'vue';
import { useRouter } from 'vue-router';

import { isHttpUrl, openRouteInNewWindow, openWindow } from '@vben/utils';

const pendingNavPath = ref('');
let pendingNavRaf = 0;
let pendingNavTimer = 0;

function cancelPendingNavSchedule() {
  if (pendingNavRaf) {
    cancelAnimationFrame(pendingNavRaf);
    pendingNavRaf = 0;
  }
  if (pendingNavTimer) {
    window.clearTimeout(pendingNavTimer);
    pendingNavTimer = 0;
  }
}

function scheduleNextFrameNavigation(
  task: () => Promise<unknown>,
  targetPath: string,
) {
  cancelPendingNavSchedule();
  pendingNavPath.value = targetPath;
  return new Promise<void>((resolve) => {
    let ran = false;
    const run = () => {
      if (ran) return;
      ran = true;
      cancelPendingNavSchedule();
      void task().finally(() => {
        if (pendingNavPath.value === targetPath) {
          pendingNavPath.value = '';
        }
        resolve();
      });
    };
    pendingNavRaf = requestAnimationFrame(run);
    pendingNavTimer = window.setTimeout(run, 32);
  });
}

function useNavigation() {
  const router = useRouter();
  const routeMetaMap = new Map<string, RouteRecordNormalized>();

  // 初始化路由映射
  const initRouteMetaMap = () => {
    const routes = router.getRoutes();
    routes.forEach((route) => {
      routeMetaMap.set(route.path, route);
    });
  };

  initRouteMetaMap();

  const getRoute = (path: string) => {
    let route = routeMetaMap.get(path);
    if (!route) {
      initRouteMetaMap();
      route = routeMetaMap.get(path);
    }
    return route;
  };

  // 检查是否应该在新窗口打开
  const shouldOpenInNewWindow = (path: string): boolean => {
    if (isHttpUrl(path)) {
      return true;
    }
    const route = getRoute(path);
    // 如果有外链或者设置了在新窗口打开，返回 true
    return !!(route?.meta?.link || route?.meta?.openInNewWindow);
  };

  const resolveHref = (path: string): string => {
    return router.resolve(path).href;
  };

  const navigation = async (path: string) => {
    try {
      const route = getRoute(path);
      const { openInNewWindow = false, query = {}, link } = route?.meta ?? {};

      // 检查是否有外链
      if (link && typeof link === 'string') {
        openWindow(link, { target: '_blank' });
        return;
      }

      if (isHttpUrl(path)) {
        openWindow(path, { target: '_blank' });
      } else if (openInNewWindow) {
        openRouteInNewWindow(resolveHref(path));
      } else {
        // 先让点击帧（< 0.5ms）把左侧菜单与顶部标签栏的高亮画上屏，下一帧立即执行路由跳转
        await scheduleNextFrameNavigation(
          () =>
            router.push({
              path,
              query,
            }),
          path,
        );
      }
    } catch (error) {
      console.error('Navigation failed:', error);
      throw error;
    }
  };

  const willOpenedByWindow = (path: string) => {
    return shouldOpenInNewWindow(path);
  };

  return { navigation, willOpenedByWindow };
}

export { pendingNavPath, scheduleNextFrameNavigation, useNavigation };
