import type { CSSProperties } from 'vue';

import type { VisibleDomRect } from '@vben-core/shared/utils';

import { computed, onMounted, onUnmounted, ref, watch } from 'vue';

/** 整页罩亮起及淡出期间抬到表格之上，淡出结束后回落；开始淡出即放开鼠标穿透 */
export const contentOverlayActive = ref(false);
export const contentOverlayBlocking = ref(false);

import {
  CSS_VARIABLE_LAYOUT_CONTENT_HEIGHT,
  CSS_VARIABLE_LAYOUT_CONTENT_WIDTH,
  CSS_VARIABLE_LAYOUT_FOOTER_HEIGHT,
  CSS_VARIABLE_LAYOUT_HEADER_HEIGHT,
} from '@vben-core/shared/constants';
import { getElementVisibleRect } from '@vben-core/shared/utils';

import { useCssVar, useDebounceFn } from '@vueuse/core';

/**
 * @zh_CN content style
 */
export function useLayoutContentStyle() {
  let resizeObserver: null | ResizeObserver = null;
  const contentElement = ref<HTMLDivElement | null>(null);
  const visibleDomRect = ref<null | VisibleDomRect>(null);
  const contentHeight = useCssVar(CSS_VARIABLE_LAYOUT_CONTENT_HEIGHT);
  const contentWidth = useCssVar(CSS_VARIABLE_LAYOUT_CONTENT_WIDTH);
  const headerHeightVar = useCssVar(CSS_VARIABLE_LAYOUT_HEADER_HEIGHT);

  const syncVisibleRect = () => {
    if (!contentElement.value) return;
    visibleDomRect.value = getElementVisibleRect(contentElement.value);
    contentHeight.value = `${visibleDomRect.value.height}px`;
    contentWidth.value = `${visibleDomRect.value.width}px`;
  };

  watch(contentOverlayActive, (active) => {
    // 已有 ResizeObserver 维护的尺寸时，不在 cover() 当帧同步测量旧大表，保证遮罩在点击帧直接上屏
    if (active && !visibleDomRect.value) {
      syncVisibleRect();
    }
  });

  const overlayStyle = computed((): CSSProperties => {
    const { left = 0, top: rawTop = 0, width = 0 } = visibleDomRect.value ?? {};
    const active = contentOverlayActive.value;
    const blocking = contentOverlayBlocking.value;
    const headerH = Number.parseInt(`${headerHeightVar.value}`, 10) || 0;
    const top = Math.max(rawTop, headerH);
    const viewH = typeof window !== 'undefined' ? window.innerHeight : 0;
    const height = Math.max(0, viewH - top);
    return {
      height: `${height}px`,
      left: `${left}px`,
      pointerEvents: blocking ? 'auto' : 'none',
      position: 'fixed',
      top: `${top}px`,
      width: `${width}px`,
      zIndex: active ? 1900 : 150,
    };
  });

  const debouncedCalcHeight = useDebounceFn(
    (_entries: ResizeObserverEntry[]) => {
      syncVisibleRect();
    },
    16,
  );

  onMounted(() => {
    if (contentElement.value && !resizeObserver) {
      syncVisibleRect();
      resizeObserver = new ResizeObserver(debouncedCalcHeight);
      resizeObserver.observe(contentElement.value);
    }
  });

  onUnmounted(() => {
    resizeObserver?.disconnect();
    resizeObserver = null;
  });

  return { contentElement, overlayStyle, visibleDomRect };
}

export function useLayoutHeaderStyle() {
  const headerHeight = useCssVar(CSS_VARIABLE_LAYOUT_HEADER_HEIGHT);

  return {
    getLayoutHeaderHeight: () => {
      return Number.parseInt(`${headerHeight.value}`, 10);
    },
    setLayoutHeaderHeight: (height: number) => {
      headerHeight.value = `${height}px`;
    },
  };
}

export function useLayoutFooterStyle() {
  const footerHeight = useCssVar(CSS_VARIABLE_LAYOUT_FOOTER_HEIGHT);

  return {
    getLayoutFooterHeight: () => {
      return Number.parseInt(`${footerHeight.value}`, 10);
    },
    setLayoutFooterHeight: (height: number) => {
      footerHeight.value = `${height}px`;
    },
  };
}
