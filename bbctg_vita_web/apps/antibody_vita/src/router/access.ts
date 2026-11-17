import type {
  ComponentRecordType,
  GenerateMenuAndRoutesOptions,
} from '@vben/types';

import { generateAccessible } from '@vben/access';
import { preferences } from '@vben/preferences';

import { ElMessage } from 'element-plus';

import { getAllMenusApi, getSystemEffectiveFeaturesApi } from '#/api';
import { BasicLayout, IFrameView } from '#/layouts';
import { $t } from '#/locales';

import {
  type FeatureState,
  filterRouteTree,
  setCachedFeatureFilter,
} from './featureFilter';

const forbiddenComponent = () => import('#/views/_core/fallback/forbidden.vue');

async function filterRoutesByFeatures(routes: any[]) {
  try {
    const result = await getSystemEffectiveFeaturesApi();
    const stateMap = new Map<string, FeatureState>(
      (result?.items || []).map((item) => [item.code, item]),
    );
    setCachedFeatureFilter(stateMap, false);
    return filterRouteTree(routes, stateMap, false);
  } catch {
    ElMessage.warning('菜单特性配置暂不可用，已隐藏受数据库控制的菜单项');
    const emptyMap = new Map<string, FeatureState>();
    setCachedFeatureFilter(emptyMap, true);
    return filterRouteTree(routes, emptyMap, true);
  }
}

async function generateAccess(options: GenerateMenuAndRoutesOptions) {
  const pageMap: ComponentRecordType = import.meta.glob('../views/**/*.vue');

  const layoutMap: ComponentRecordType = {
    BasicLayout,
    IFrameView,
  };

  const featureRoutes = await filterRoutesByFeatures(options.routes as any[]);

  return await generateAccessible(preferences.app.accessMode, {
    ...options,
    fetchMenuListAsync: async () => {
      ElMessage({
        duration: 1500,
        message: `${$t('common.loadingMenu')}...`,
      });
      return await getAllMenusApi();
    },
    // menuVisibleWithForbidden 路由无权限时仍显示菜单，但访问时进入 403 页面。
    forbiddenComponent,
    layoutMap,
    pageMap,
    routes: featureRoutes,
  });
}

export { generateAccess };
