import {
  createRouter,
  createWebHashHistory,
  createWebHistory,
  type RouteLocationNormalized,
} from 'vue-router';

import { resetStaticRoutes } from '@vben/utils';

import { createRouterGuard } from './guard';
import { routes } from './routes';

/** keepAlive 页面离开时的窗口滚动位置（Tab 切换时恢复） */
const routeScrollMap = new Map<string, { left: number; top: number }>();

function getRouteScrollKey(route: RouteLocationNormalized) {
  const { fullPath, path, meta: { fullPathKey } = {} } = route;
  const rawKey = fullPathKey === false ? path : (fullPath ?? path);
  try {
    return decodeURIComponent(rawKey);
  } catch {
    return rawKey;
  }
}

function rememberRouteScroll(from: RouteLocationNormalized) {
  if (!from.meta.keepAlive) {
    return;
  }
  routeScrollMap.set(getRouteScrollKey(from), {
    left: window.scrollX,
    top: window.scrollY,
  });
}

function resolveRouteScroll(to: RouteLocationNormalized) {
  if (!to.meta.keepAlive) {
    return null;
  }
  return routeScrollMap.get(getRouteScrollKey(to)) ?? null;
}

/**
 *  @zh_CN 创建vue-router实例
 */
const router = createRouter({
  history:
    import.meta.env.VITE_ROUTER_HISTORY === 'hash'
      ? createWebHashHistory(import.meta.env.VITE_BASE)
      : createWebHistory(import.meta.env.VITE_BASE),
  // 应该添加到路由的初始路由列表。
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition;
    }
    if (from.name) {
      rememberRouteScroll(from);
    }
    if (to.hash) {
      return { behavior: 'smooth', el: to.hash };
    }
    const cached = resolveRouteScroll(to);
    if (cached) {
      return new Promise((resolve) => {
        requestAnimationFrame(() => resolve(cached));
      });
    }
    return { left: 0, top: 0 };
  },
  // 是否应该禁止尾部斜杠。
  // strict: true,
});

const resetRoutes = () => resetStaticRoutes(router, routes);

// 创建路由守卫
createRouterGuard(router);

export { resetRoutes, router };
