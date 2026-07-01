import type { RouteLocationNormalized, Router } from 'vue-router';

import { LOGIN_PATH } from '@vben/constants';
import { preferences } from '@vben/preferences';
import { useAccessStore, useUserStore } from '@vben/stores';
import { startProgress, stopProgress } from '@vben/utils';

import { accessRoutes, coreRouteNames } from '#/router/routes';
import { useAuthStore } from '#/store';
import {
  createAccessChecker,
  resolveUserStartPath,
} from '#/views/Home/home-data';

import { generateAccess } from './access';

/** 仅浏览器 F5 冷启动时清空列表筛选暂存（站内 Tab 刷新不走此逻辑） */
function clearListFilterStorageOnColdStart() {
  ['serumListFilters', 'titerOrderListFilters'].forEach((key) =>
    sessionStorage.removeItem(key),
  );
}

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

/**
 * 通用守卫配置
 * @param router
 */
function setupCommonGuard(router: Router) {
  // 记录已经加载的页面
  const loadedPaths = new Set<string>();

  router.beforeEach((to) => {
    to.meta.loaded = loadedPaths.has(to.path);

    // 页面加载进度条
    if (!to.meta.loaded && preferences.transition.progress) {
      startProgress();
    }
    return true;
  });

  router.afterEach((to) => {
    // 记录页面是否加载,如果已经加载，后续的页面切换动画等效果不在重复执行

    loadedPaths.add(to.path);

    // 关闭页面加载进度条
    if (preferences.transition.progress) {
      stopProgress();
    }
  });
}

/**
 * 权限访问守卫配置
 * @param router
 */
function setupAccessGuard(router: Router) {
  router.beforeEach(async (to, from) => {
    const accessStore = useAccessStore();
    const userStore = useUserStore();
    const authStore = useAuthStore();

    // 基本路由，这些路由不需要进入权限拦截
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

    // accessToken 检查
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

      // 明确声明忽略权限访问权限，则可以访问
      if (to.meta.ignoreAccess) {
        return true;
      }

      // 没有访问权限，跳转登录页面
      if (to.fullPath !== LOGIN_PATH) {
        return {
          path: LOGIN_PATH,
          // 如不需要，直接删除 query
          query:
            to.fullPath === preferences.app.defaultHomePath
              ? {}
              : { redirect: encodeURIComponent(to.fullPath) },
          // 携带当前跳转的页面，登录后重新跳转该页面
          replace: true,
        };
      }
      return to;
    }

    // 是否已经生成过动态路由
    if (accessStore.isAccessChecked) {
      return true;
    }

    // 生成路由表
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

    // 生成菜单和路由
    const { accessibleMenus, accessibleRoutes } = await generateAccess({
      roles: userRoles,
      router,
      // 则会在菜单中显示，但是访问会被重定向到403
      routes: accessRoutes,
    });

    // 保存菜单信息和路由信息
    accessStore.setAccessMenus(accessibleMenus);
    accessStore.setAccessRoutes(accessibleRoutes);
    accessStore.setIsAccessChecked(true);
    clearListFilterStorageOnColdStart();

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

/**
 * 项目守卫配置
 * @param router
 */
function createRouterGuard(router: Router) {
  /** 通用 */
  setupCommonGuard(router);
  /** 权限访问 */
  setupAccessGuard(router);
}

export { createRouterGuard };
