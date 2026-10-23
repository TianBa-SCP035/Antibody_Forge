<script lang="ts" setup>
import type { RendererElement } from 'vue';

defineOptions({
  name: 'CollapseTransition',
});

const reset = (el: RendererElement) => {
  el.style.maxHeight = '';
  el.style.overflow = el.dataset.oldOverflow;
  el.style.paddingTop = el.dataset.oldPaddingTop;
  el.style.paddingBottom = el.dataset.oldPaddingBottom;
};

const on = {
  afterEnter(el: RendererElement) {
    el.style.maxHeight = '';
    el.style.overflow = el.dataset.oldOverflow;
  },

  afterLeave(el: RendererElement) {
    reset(el);
  },

  beforeEnter(el: RendererElement) {
    if (!el.dataset) el.dataset = {};

    el.dataset.oldPaddingTop = el.style.paddingTop;
    el.dataset.oldMarginTop = el.style.marginTop;

    el.dataset.oldPaddingBottom = el.style.paddingBottom;
    el.dataset.oldMarginBottom = el.style.marginBottom;
    el.dataset.oldOverflow = el.style.overflow;
    if (el.style.height) el.dataset.elExistsHeight = el.style.height;

    el.style.maxHeight = '0px';
    el.style.paddingTop = '0px';
    el.style.marginTop = '0px';
    el.style.paddingBottom = '0px';
    el.style.marginBottom = '0px';
    el.style.overflow = 'hidden';
  },

  beforeLeave(el: RendererElement) {
    if (!el.dataset) el.dataset = {};
    el.dataset.oldPaddingTop = el.style.paddingTop;
    el.dataset.oldMarginTop = el.style.marginTop;
    el.dataset.oldPaddingBottom = el.style.paddingBottom;
    el.dataset.oldMarginBottom = el.style.marginBottom;
    el.dataset.oldOverflow = el.style.overflow;
    el.style.maxHeight = `${el.scrollHeight}px`;
    el.style.overflow = 'hidden';
    void el.offsetHeight;
  },

  enter(el: RendererElement) {
    requestAnimationFrame(() => {
      if (el.dataset.elExistsHeight) {
        el.style.maxHeight = el.dataset.elExistsHeight;
      } else if (el.scrollHeight === 0) {
        el.style.maxHeight = '0px';
      } else {
        el.style.maxHeight = `${el.scrollHeight}px`;
      }

      el.style.paddingTop = el.dataset.oldPaddingTop;
      el.style.paddingBottom = el.dataset.oldPaddingBottom;
      el.style.marginTop = el.dataset.oldMarginTop;
      el.style.marginBottom = el.dataset.oldMarginBottom;
      el.style.overflow = 'hidden';
    });
  },

  enterCancelled(el: RendererElement) {
    reset(el);
  },

  leave(el: RendererElement) {
    requestAnimationFrame(() => {
      if (el.scrollHeight !== 0) {
        el.style.maxHeight = '0px';
        el.style.paddingTop = '0px';
        el.style.paddingBottom = '0px';
        el.style.marginTop = '0px';
        el.style.marginBottom = '0px';
      }
    });
  },

  leaveCancelled(el: RendererElement) {
    reset(el);
  },
};
</script>

<template>
  <transition name="collapse-transition" v-on="on">
    <slot></slot>
  </transition>
</template>
