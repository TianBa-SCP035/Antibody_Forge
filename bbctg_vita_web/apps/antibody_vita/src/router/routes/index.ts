import type { RouteRecordRaw } from 'vue-router';

import { mergeRouteModules, traverseTreeValues } from '@vben/utils';

import { coreRoutes, fallbackNotFoundRoute } from './core';

const dynamicRouteFiles = import.meta.glob('./modules/**/*.ts', {
  eager: true,
});

const dynamicRoutes: RouteRecordRaw[] = mergeRouteModules(dynamicRouteFiles);

const staticRoutes: RouteRecordRaw[] = [];
const externalRoutes: RouteRecordRaw[] = [];

/** 基础路由、外部路由和 404 兜底不参与权限校验。 */
const routes: RouteRecordRaw[] = [
  ...coreRoutes,
  ...externalRoutes,
  fallbackNotFoundRoute,
];

const coreRouteNames = traverseTreeValues(coreRoutes, (route) => route.name);

/** 动态路由和静态路由参与权限校验。 */
const accessRoutes = [...dynamicRoutes, ...staticRoutes];
export { accessRoutes, coreRouteNames, routes };
