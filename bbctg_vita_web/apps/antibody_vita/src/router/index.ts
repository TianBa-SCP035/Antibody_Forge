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

let restoreTimer = 0;
let restoreStartTimer = 0;
let restoreUntil = 0;
let unbindUserScroll: (() => void) | null = null;

function getRouteScrollKey(route: RouteLocationNormalized) {
  const { fullPath, path, meta: { fullPathKey } = {} } = route;
  const rawKey = fullPathKey === false ? path : (fullPath ?? path);
  try {
    return decodeURIComponent(rawKey);
  } catch {
    return rawKey;
  }
}

function stopRestoreTicks() {
  if (restoreStartTimer) {
    window.clearTimeout(restoreStartTimer);
    restoreStartTimer = 0;
  }
  if (restoreTimer) {
    window.clearInterval(restoreTimer);
    restoreTimer = 0;
  }
}

function cancelPendingRestore(userTookOver = false) {
  stopRestoreTicks();
  unbindUserScroll?.();
  unbindUserScroll = null;
  if (userTookOver) {
    restoreUntil = 0;
  }
}

function rememberRouteScroll(from: RouteLocationNormalized) {
  if (!from.name || !from.meta.keepAlive) {
    return;
  }
  const key = getRouteScrollKey(from);
  const left = window.scrollX;
  const top = window.scrollY;
  const prev = routeScrollMap.get(key);
  // 进场还原尚未结束时又发生一次导航，此时滚动常已被 out-in 夹成 0，不能覆盖旧记忆
  if (
    prev &&
    top <= 0 &&
    left <= 0 &&
    (prev.top > 0 || prev.left > 0) &&
    Date.now() < restoreUntil
  ) {
    return;
  }
  routeScrollMap.set(key, { left, top });
}

function resolveRouteScroll(to: RouteLocationNormalized) {
  if (!to.meta.keepAlive) {
    return null;
  }
  return routeScrollMap.get(getRouteScrollKey(to)) ?? null;
}

function restoreRouteScroll(to: RouteLocationNormalized) {
  cancelPendingRestore();
  const cached = resolveRouteScroll(to);
  if (!cached || (cached.top <= 0 && cached.left <= 0)) {
    return;
  }

  const apply = () => window.scrollTo(cached.left, cached.top);
  const onUserScroll = () => cancelPendingRestore(true);
  const onUserPointer = () => stopRestoreTicks();
  window.addEventListener('wheel', onUserScroll, { passive: true });
  window.addEventListener('touchmove', onUserScroll, { passive: true });
  window.addEventListener('pointerdown', onUserPointer, { passive: true });
  unbindUserScroll = () => {
    window.removeEventListener('wheel', onUserScroll);
    window.removeEventListener('touchmove', onUserScroll);
    window.removeEventListener('pointerdown', onUserPointer);
    unbindUserScroll = null;
  };

  // 已访问过的页会走 fade-slide out-in（约 300ms 离场），等新页进 DOM 再开始补还
  const startDelay = to.meta.loaded ? 320 : 0;
  restoreUntil = Date.now() + startDelay + 800;
  restoreStartTimer = window.setTimeout(() => {
    restoreStartTimer = 0;
    apply();
    let stable = 0;
    restoreTimer = window.setInterval(() => {
      apply();
      const maxY = document.documentElement.scrollHeight - window.innerHeight;
      if (
        maxY >= cached.top - 2 &&
        Math.abs(window.scrollY - cached.top) <= 2
      ) {
        stable += 1;
        if (stable >= 3) {
          cancelPendingRestore(true);
        }
        return;
      }
      stable = 0;
      if (Date.now() >= restoreUntil) {
        cancelPendingRestore();
      }
    }, 50);
  }, startDelay);
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
  scrollBehavior(to, _from, savedPosition) {
    if (savedPosition) {
      return savedPosition;
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

router.beforeEach((_, from) => {
  cancelPendingRestore();
  rememberRouteScroll(from);
  return true;
});

const resetRoutes = () => resetStaticRoutes(router, routes);

// 创建路由守卫
createRouterGuard(router);

router.afterEach((to) => {
  restoreRouteScroll(to);
});

export { resetRoutes, router };
