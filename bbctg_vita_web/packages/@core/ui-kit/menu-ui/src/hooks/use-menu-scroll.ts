import type { Ref } from 'vue';

import { watch } from 'vue';

import { useDebounceFn } from '@vueuse/core';

interface UseMenuScrollOptions {
  delay?: number;
  enable?: boolean | Ref<boolean>;
}

function findSidebarScroller(el: HTMLElement) {
  const aside = el.closest('aside');
  if (!aside) return null;

  let node: HTMLElement | null = el.parentElement;
  while (node && aside.contains(node)) {
    const { overflowY, overflow } = getComputedStyle(node);
    if (/(auto|scroll|overlay)/.test(`${overflowY}${overflow}`)) {
      return node;
    }
    node = node.parentElement;
  }

  return aside.querySelector<HTMLElement>(
    '[data-reka-scroll-area-viewport], [data-radix-scroll-area-viewport]',
  );
}

export function useMenuScroll(
  activePath: Ref<string | undefined>,
  options: UseMenuScrollOptions = {},
) {
  const { enable = true, delay = 320 } = options;

  function scrollToActiveItem() {
    const isEnabled = typeof enable === 'boolean' ? enable : enable.value;
    if (!isEnabled) return;

    const activeElement = document.querySelector(
      `aside a[role=menuitem].is-active`,
    );
    if (!(activeElement instanceof HTMLElement)) return;

    // 只滚侧栏容器。scrollIntoView({block:'center'}) 会带着 window 一起走，
    // 把 keepAlive 页刚还原的滚动位置盖掉。
    const scroller = findSidebarScroller(activeElement);
    if (!scroller) return;

    const box = scroller.getBoundingClientRect();
    const item = activeElement.getBoundingClientRect();
    scroller.scrollTo({
      top:
        scroller.scrollTop +
        (item.top + item.height / 2 - (box.top + box.height / 2)),
      behavior: 'smooth',
    });
  }

  const debouncedScroll = useDebounceFn(scrollToActiveItem, delay);

  watch(activePath, () => {
    const isEnabled = typeof enable === 'boolean' ? enable : enable.value;
    if (!isEnabled) return;

    debouncedScroll();
  });

  return {
    scrollToActiveItem,
  };
}
