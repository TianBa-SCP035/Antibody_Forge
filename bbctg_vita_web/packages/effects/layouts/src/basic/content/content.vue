<script lang="ts" setup>
import type { RouteLocationNormalizedLoadedGeneric } from 'vue-router';

import { unref } from 'vue';
import { RouterView } from 'vue-router';

import { usePreferences } from '@vben/preferences';
import { storeToRefs, useTabbarStore } from '@vben/stores';

import { transformComponent, useLayoutHook } from '../../hooks';
import { IFrameRouterView } from '../../iframe';
import { RouteCachedPage, RouteCachedView } from '../../route-cached';

defineOptions({ name: 'LayoutContent' });

type AnimatablePageEl = HTMLElement & {
  _vbenEnterCleanup?: () => void;
  _vbenPageVm?: any;
};

const tabbarStore = useTabbarStore();
const { keepAlive } = usePreferences();

const { getCachedTabs, getExcludeCachedTabs, renderRouteView } =
  storeToRefs(tabbarStore);

const { getEnabledTransition, getTransitionName } = useLayoutHook();

/**
 * 是否显示component
 * @param route
 */
const showComponent = (route: RouteLocationNormalizedLoadedGeneric) => {
  return !route.meta.domCached && unref(renderRouteView);
};

function getRouteViewKey(route: RouteLocationNormalizedLoadedGeneric) {
  const { fullPath, path, meta: { fullPathKey } = {} } = route;
  const rawKey = fullPathKey === false ? path : (fullPath ?? path);
  try {
    return decodeURIComponent(rawKey);
  } catch {
    return rawKey;
  }
}

function bindPageVm(vnode: any) {
  const el = vnode?.el;
  const vm = vnode?.component;
  if (el instanceof HTMLElement && vm) {
    (el as AnimatablePageEl)._vbenPageVm = vm;
  }
}

/**
 * 递归从组件公开 subTree 中收集所有 ElTable 内部实例（包含 state.doLayout）。
 * 不依赖仅开发模式存在的 el.__vueParentComponent，保证生产构建（PROD）同样 100% 生效。
 */
function collectElTableInstances(root: Element): any[] {
  const result = new Set<any>();
  const pageVm = (root as AnimatablePageEl)._vbenPageVm;

  const visitVNode = (vnode: any) => {
    if (!vnode || typeof vnode !== 'object') return;
    const comp = vnode.component;
    if (comp) {
      if (comp.state?.doLayout && comp.layout) {
        result.add(comp);
      }
      if (comp.subTree) {
        visitVNode(comp.subTree);
      }
    }
    const children = vnode.children;
    if (Array.isArray(children)) {
      for (const child of children) {
        visitVNode(child);
      }
    }
  };

  if (pageVm?.subTree) {
    visitVNode(pageVm.subTree);
  }

  // 开发模式或兜底补充
  const tables = root.querySelectorAll('.el-table');
  for (const tableEl of tables) {
    const vm = (tableEl as any).__vueParentComponent;
    if (vm?.state?.doLayout) {
      result.add(vm);
    }
  }
  return [...result];
}

function pauseElTablesIn(root: Element) {
  const tableVms = collectElTableInstances(root);
  for (const vm of tableVms) {
    if (vm && vm.$ready) {
      vm.$ready = false;
      vm._vbenPausedReady = true;
    }
  }
  if (root.classList.contains('is-list-table-locked')) {
    const body = root.querySelector('.list-table-body');
    if (
      body instanceof HTMLElement &&
      body.querySelector('.el-table__body-wrapper')
    ) {
      body.classList.add('is-list-table-defer-body');
    }
  }
}

function resumeElTablesIn(root: Element) {
  if (!(root instanceof HTMLElement) || !root.isConnected) return;
  const tableVms = collectElTableInstances(root);
  for (const vm of tableVms) {
    const el = vm?.vnode?.el as HTMLElement | undefined;
    // 处于锁高大表延迟显现阶段的表格由 listTableLock 在进场动画后统一恢复
    if (el?.closest?.('.is-list-table-defer-body')) continue;
    if (vm && vm._vbenPausedReady) {
      const rs = vm.state?.resizeState?.value;
      const w = el ? el.offsetWidth : 0;
      const h = el ? el.offsetHeight : 0;
      const headerEl = el?.querySelector<HTMLElement>(
        '.el-table__header-wrapper',
      );
      const hh = headerEl ? headerEl.offsetHeight : (rs?.headerHeight ?? 0);
      const widthChanged = w > 0 && rs && rs.width !== w;
      if (rs && w > 0) {
        rs.width = w;
        rs.height = h;
        rs.headerHeight = hh;
      }
      vm.$ready = true;
      vm._vbenPausedReady = false;
      if (widthChanged) {
        vm.state?.doLayout?.();
      }
    }
  }
}

function cleanupEnterClasses(el: Element) {
  if (!(el instanceof HTMLElement)) return;
  const host = el as AnimatablePageEl;
  host._vbenEnterCleanup?.();
  host._vbenEnterCleanup = undefined;
  for (const cls of [...host.classList]) {
    if (
      cls.endsWith('-enter-from') ||
      cls.endsWith('-enter-active') ||
      cls.endsWith('-enter-to')
    ) {
      host.classList.remove(cls);
    }
  }
  resumeElTablesIn(host);
}

function onBeforeEnter(
  el: Element,
  route: RouteLocationNormalizedLoadedGeneric,
) {
  if (!(el instanceof HTMLElement)) return;
  cleanupEnterClasses(el);
  const name = getTransitionName(route);
  if (!name) return;
  el.classList.add(`${name}-enter-from`, `${name}-enter-active`);
}

function onEnter(
  el: Element,
  done: () => void,
  route: RouteLocationNormalizedLoadedGeneric,
) {
  if (!(el instanceof HTMLElement)) {
    done();
    return;
  }
  const name = getTransitionName(route);
  if (!name) {
    cleanupEnterClasses(el);
    done();
    return;
  }

  const host = el as AnimatablePageEl;
  let raf1 = 0;
  let raf2 = 0;
  let timer = 0;
  let finished = false;

  const finish = () => {
    if (finished) return;
    finished = true;
    cleanupEnterClasses(host);
    done();
  };

  const onTransitionEnd = (event: TransitionEvent) => {
    if (event.target !== host) return;
    finish();
  };

  host._vbenEnterCleanup = () => {
    if (raf1) cancelAnimationFrame(raf1);
    if (raf2) cancelAnimationFrame(raf2);
    if (timer) window.clearTimeout(timer);
    host.removeEventListener('transitionend', onTransitionEnd);
  };

  host.addEventListener('transitionend', onTransitionEnd);
  timer = window.setTimeout(finish, 380);

  raf1 = requestAnimationFrame(() => {
    raf1 = 0;
    raf2 = requestAnimationFrame(() => {
      raf2 = 0;
      if (finished) return;
      host.classList.remove(`${name}-enter-from`);
      host.classList.add(`${name}-enter-to`);
    });
  });
}

function onLeave(el: Element, done: () => void) {
  // 1. 在旧页面脱离文档进入 KeepAlive 离屏容器（0x0）之前，先将内部 el-table 的 $ready 置为 false 并隐藏大表 tbody，
  //    阻止 Element Plus 的 ResizeObserver 因尺寸变为 0x0 而在点击帧强行执行 doLayout() 重算 500 行；
  // 2. 使用 :css="false" 跳过 Vue 内置 Transition 的 forceReflow，使旧页面 0ms 瞬时离场。
  cleanupEnterClasses(el);
  pauseElTablesIn(el);
  done();
}
</script>

<template>
  <div class="relative h-full">
    <IFrameRouterView />
    <RouteCachedView />
    <RouterView v-slot="{ Component, route }">
      <RouteCachedPage
        :component="Component"
        :route="route"
        v-if="route.meta.domCached"
      />
      <Transition
        v-if="getEnabledTransition"
        :css="false"
        appear
        @before-enter="(el) => onBeforeEnter(el, route)"
        @enter="(el, done) => onEnter(el, done, route)"
        @after-enter="cleanupEnterClasses"
        @enter-cancelled="cleanupEnterClasses"
        @leave="onLeave"
      >
        <KeepAlive
          v-if="keepAlive"
          :exclude="getExcludeCachedTabs"
          :include="getCachedTabs"
        >
          <component
            :is="transformComponent(Component, route)"
            v-if="showComponent(route)"
            v-show="!route.meta.iframeSrc"
            :key="getRouteViewKey(route)"
            @vue:mounted="bindPageVm"
            @vue:updated="bindPageVm"
          />
        </KeepAlive>
        <component
          :is="Component"
          v-else-if="showComponent(route)"
          :key="getRouteViewKey(route)"
          @vue:mounted="bindPageVm"
          @vue:updated="bindPageVm"
        />
      </Transition>
      <template v-else>
        <KeepAlive
          v-if="keepAlive"
          :exclude="getExcludeCachedTabs"
          :include="getCachedTabs"
        >
          <component
            :is="transformComponent(Component, route)"
            v-if="showComponent(route)"
            v-show="!route.meta.iframeSrc"
            :key="getRouteViewKey(route)"
            @vue:mounted="bindPageVm"
            @vue:updated="bindPageVm"
          />
        </KeepAlive>
        <component
          :is="Component"
          v-else-if="showComponent(route)"
          :key="getRouteViewKey(route)"
          @vue:mounted="bindPageVm"
          @vue:updated="bindPageVm"
        />
      </template>
    </RouterView>
  </div>
</template>
