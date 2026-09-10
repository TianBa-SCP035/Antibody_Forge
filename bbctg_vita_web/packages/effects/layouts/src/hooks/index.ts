import type { VNode } from 'vue';
import type { RouteLocationNormalizedLoadedGeneric } from 'vue-router';

import { computed } from 'vue';

import { preferences } from '@vben/preferences';

/**
 * 转换组件，自动添加 name
 * @param component
 * @param route
 */
export function transformComponent(
  component: VNode,
  route: RouteLocationNormalizedLoadedGeneric,
) {
  // 组件视图未找到，如果有设置后备视图，则返回后备视图，如果没有，则抛出错误
  if (!component) {
    console.error(
      'Component view not found，please check the route configuration',
    );
    return undefined;
  }

  const routeName = route.name as string;
  // 如果组件没有 name，则直接返回
  if (!routeName) {
    return component;
  }
  const componentName = (component?.type as any)?.name;

  // 已经设置过 name，则直接返回
  if (componentName) {
    return component;
  }

  // componentName 与 routeName 一致，则直接返回
  if (componentName === routeName) {
    return component;
  }

  // 设置 name
  component.type ||= {};
  (component.type as any).name = routeName;

  return component;
}

/**
 * Layout相关hook
 */
export function useLayoutHook() {
  /**
   * 是否使用动画
   */
  const getEnabledTransition = computed(() => {
    const { transition } = preferences;
    const transitionName = transition.name;
    return transitionName && transition.enable;
  });

  /**
   * 获取路由过渡动画
   */
  function getTransitionName(route?: { meta?: { loaded?: boolean } }) {
    const { transition } = preferences;
    if (!transition.name || !transition.enable) {
      return;
    }
    // 第一次进页由整页罩盖住，不再滑，避免底下排版抢主线程把方块卡顿
    if (route && !route.meta?.loaded) {
      return;
    }
    return transition.name;
  }

  return {
    getEnabledTransition,
    getTransitionName,
  };
}
