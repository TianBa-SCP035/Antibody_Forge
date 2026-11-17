import type { RouteLocationNormalized, Router } from 'vue-router';

import { LOGIN_PATH } from '@vben/constants';
import { preferences } from '@vben/preferences';
import { useAccessStore, useUserStore } from '@vben/stores';
import { startProgress, stopProgress } from '@vben/utils';

import { accessRoutes, coreRouteNames } from '#/router/routes';
import { useAuthStore } from '#/store';
import { clearAllListFilters } from '#/utils/listFilterStorage';
import {
  createAccessChecker,
  resolveUserStartPath,
} from '#/views/Home/home-data';

import { generateAccess } from './access';

/** 弹窗重登仅适用于已进入业务布局的页面；冷启动/404 应跳转登录页 */
function shouldPreservePageForReLogin(
  to: RouteLocationNormalized,
  isAccessChecked: boolean,
  loginExpired: boolean,
) {
  return (
    loginExpired &&
    isAccessChecked &&
    to.name !== 'FallbackNotFound'
  );
}

function setupCommonGuard(router: Router) {
  // 已加载页面不再重复执行首次进入动画。
  const loadedPaths = new Set<string>();

  router.beforeEach((to) => {
    to.meta.loaded = loadedPaths.has(to.path);

    if (!to.meta.loaded && preferences.transition.progress) {
      startProgress();
    }
    return true;
  });

  router.afterEach((to) => {
    loadedPaths.add(to.path);

    if (preferences.transition.progress) {
      stopProgress();
    }
  });
}

function setupAccessGuard(router: Router) {
  router.beforeEach(async (to, from) => {
    const accessStore = useAccessStore();
    const userStore = useUserStore();
    const authStore = useAuthStore();

    if (coreRouteNames.includes(to.name as string)) {
      if (to.path === LOGIN_PATH && accessStore.accessToken) {
        const hasAccessByCodes = createAccessChecker(accessStore.accessCodes);
        const startPath = resolveUserStartPath(
          userStore.userInfo?.homePath,
          hasAccessByCodes,
        );
        return decodeURIComponent(
          (to.query?.redirect as string) || startPath,
        );
      }
      return true;
    }

    if (!accessStore.accessToken) {
      if (
        shouldPreservePageForReLogin(
          to,
          accessStore.isAccessChecked,
          accessStore.loginExpired,
        )
      ) {
        return true;
      }

      if (to.meta.ignoreAccess) {
        return true;
      }

      if (to.fullPath !== LOGIN_PATH) {
        return {
          path: LOGIN_PATH,
          query:
            to.fullPath === preferences.app.defaultHomePath
              ? {}
              : { redirect: encodeURIComponent(to.fullPath) },
          replace: true,
        };
      }
      return to;
    }

    if (accessStore.isAccessChecked) {
      return true;
    }

    let userInfo = userStore.userInfo;
    if (!userInfo) {
      try {
        userInfo = await authStore.fetchUserInfo();
      } catch {
        // 冷启动鉴权失败：401 拦截器可能已置 loginExpired，此处统一跳登录页
        accessStore.setLoginExpired(false);
        return {
          path: LOGIN_PATH,
          query: { redirect: encodeURIComponent(to.fullPath) },
          replace: true,
        };
      }
    }
    const userRoles = [
      ...(userInfo.roles ?? []),
      ...((userInfo as any).accessCodes ?? []),
      ...accessStore.accessCodes,
    ];

    const { accessibleMenus, accessibleRoutes } = await generateAccess({
      roles: userRoles,
      router,
      routes: accessRoutes,
    });

    accessStore.setAccessMenus(accessibleMenus);
    accessStore.setAccessRoutes(accessibleRoutes);
    accessStore.setIsAccessChecked(true);
    // 只有 F5 冷启动会走到这里，站内 Tab 刷新不清筛选
    clearAllListFilters();

    const hasAccessByCodes = createAccessChecker(accessStore.accessCodes);
    const startPath = resolveUserStartPath(userInfo.homePath, hasAccessByCodes);
    const redirectPath = (from.query.redirect ??
      (to.path === preferences.app.defaultHomePath ? startPath : to.fullPath)) as string;

    return {
      ...router.resolve(decodeURIComponent(redirectPath)),
      replace: true,
    };
  });
}

function createRouterGuard(router: Router) {
  setupCommonGuard(router);
  setupAccessGuard(router);
}

export { createRouterGuard };
