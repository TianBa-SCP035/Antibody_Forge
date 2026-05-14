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

const forbiddenComponent = () => import('#/views/_core/fallback/forbidden.vue');

type FeatureState = {
  code: string;
  enabled: boolean;
  sort_order?: number;
  visible: boolean;
};

async function filterRoutesByFeatures(routes: any[]) {
  try {
    const result = await getSystemEffectiveFeaturesApi();
    const stateMap = new Map<string, FeatureState>(
      (result?.items || []).map((item) => [item.code, item]),
    );
    return filterRouteTree(routes, stateMap, false);
  } catch {
    ElMessage.warning('菜单特性配置暂不可用，已隐藏受数据库控制的菜单项');
    return filterRouteTree(routes, new Map(), true);
  }
}

function filterRouteTree(
  routes: any[],
  stateMap: Map<string, FeatureState>,
  treatMissingFeatureAsHidden: boolean,
): any[] {
  return routes
    .map((route) => {
      const featureCode = route.meta?.featureCode;
      const state = featureCode ? stateMap.get(featureCode) : undefined;
      const children = route.children
        ? filterRouteTree(route.children, stateMap, treatMissingFeatureAsHidden)
        : route.children;
      return {
        ...route,
        children,
        meta: {
          ...route.meta,
          order: state?.sort_order ?? route.meta?.order,
        },
      };
    })
    .filter((route) => {
      const featureCode = route.meta?.featureCode;
      if (!featureCode) return route.children === undefined || route.children.length > 0;
      const state = stateMap.get(featureCode);
      if (treatMissingFeatureAsHidden && !state) return false;
      if (state && (!state.enabled || !state.visible)) return false;
      return route.children === undefined || route.children.length > 0;
    });
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
    // 可以指定没有权限跳转403页面
    forbiddenComponent,
    // 如果 route.meta.menuVisibleWithForbidden = true
    layoutMap,
    pageMap,
    routes: featureRoutes,
  });
}

export { generateAccess };
