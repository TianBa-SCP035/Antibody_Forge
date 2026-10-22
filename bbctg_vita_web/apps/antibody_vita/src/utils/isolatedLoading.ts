import type { Directive, DirectiveBinding } from 'vue';
import { nextTick } from 'vue';

const FADE_MS = 240;

type LoadState = {
  overlay: HTMLElement;
  box: HTMLElement;
  gen: number;
  addedHostClass: boolean;
  cleanupEvents: (() => void) | null;
};

type HostEl = HTMLElement & {
  _vitaLoad?: LoadState;
};

function isOn(value: unknown) {
  return Boolean(value);
}

function waitFrames(n: number) {
  return new Promise<void>((resolve) => {
    const step = (left: number) => {
      if (left <= 0) {
        resolve();
        return;
      }
      requestAnimationFrame(() => step(left - 1));
    };
    requestAnimationFrame(() => step(n - 1));
  });
}

function ensureHostPosition(el: HTMLElement): boolean {
  if (el.classList.contains('vita-iso-host')) return true;
  const pos = window.getComputedStyle(el).position;
  if (!pos || pos === 'static') {
    el.classList.add('vita-iso-host');
    return true;
  }
  return false;
}

function applyText(el: HTMLElement, box: HTMLElement) {
  const text = el.getAttribute('element-loading-text');
  let label = box.querySelector('.vita-iso-load__text');
  if (!text) {
    label?.remove();
    return;
  }
  if (!label) {
    label = document.createElement('p');
    label.className = 'vita-iso-load__text';
    box.append(label);
  }
  label.textContent = text;
}

/**
 * 遮罩本身使用 position: absolute; inset: 0 嵌在宿主内部，由浏览器合成器原生同步滚动，0px 漂移；
 * 此处仅通过事件驱动（捕获祖先滚动 + ResizeObserver）处理：
 * 1. 若宿主自身是带 scrollTop 的滚动容器，对齐 scrollTop/scrollLeft；
 * 2. 求宿主与所有裁剪/滚动祖先及视口的可见交集，将转圈图标精准居中于可见区域。
 */
function syncOverlayOffset(el: HTMLElement, overlay: HTMLElement) {
  if (!el.isConnected) return;
  const st = el.scrollTop;
  const sl = el.scrollLeft;
  if (st !== 0 || sl !== 0) {
    overlay.style.transform = `translate3d(${sl}px, ${st}px, 0)`;
  } else if (overlay.style.transform) {
    overlay.style.transform = '';
  }

  const r = el.getBoundingClientRect();
  const overlayH = el.clientHeight || r.height;
  if (overlayH <= 0) return;

  let visTop = Math.max(r.top, 0);
  let visBottom = Math.min(r.bottom, window.innerHeight);

  const main = document.getElementById('__vben_main_content');
  if (main?.contains(el)) {
    const chrome = document.querySelector('._scroll__fixed_');
    if (chrome) {
      visTop = Math.max(visTop, chrome.getBoundingClientRect().bottom);
    }
  }

  let parent = el.parentElement;
  while (parent && parent !== document.body && parent !== document.documentElement) {
    const style = window.getComputedStyle(parent);
    const overflowY = style.overflowY || style.overflow;
    if (overflowY === 'auto' || overflowY === 'scroll' || overflowY === 'hidden' || overflowY === 'clip') {
      const pr = parent.getBoundingClientRect();
      visTop = Math.max(visTop, pr.top);
      visBottom = Math.min(visBottom, pr.bottom);
    }
    parent = parent.parentElement;
  }

  if (visBottom > visTop) {
    const overlayTop = r.top + (el.clientTop || 0);
    const rawCenter = (visTop + visBottom) / 2 - overlayTop;
    const minPad = Math.min(24, overlayH / 2);
    const maxPad = Math.max(overlayH / 2, overlayH - 24);
    const clampedCenter = Math.min(Math.max(minPad, rawCenter), maxPad);
    overlay.style.setProperty('--vita-spin-y', `${Math.round(clampedCenter * 10) / 10}px`);
  } else {
    overlay.style.removeProperty('--vita-spin-y');
  }
}

const BLOCKED_EVENTS = [
  'pointerdown',
  'pointerup',
  'mousedown',
  'mouseup',
  'click',
  'dblclick',
  'contextmenu',
  'keydown',
  'keyup',
  'keypress',
] as const;

function bindActiveEvents(el: HostEl, state: LoadState) {
  state.cleanupEvents?.();
  const onScrollOrResize = () => syncOverlayOffset(el, state.overlay);
  const onBlock = (event: Event) => {
    event.stopPropagation();
    event.preventDefault();
  };
  const onFocusIn = (event: FocusEvent) => {
    event.stopPropagation();
    const target = event.target as HTMLElement | null;
    target?.blur?.();
  };

  if (document.activeElement instanceof HTMLElement && el.contains(document.activeElement)) {
    document.activeElement.blur();
  }

  // capture: true 可捕获任意嵌套滚动祖先的 scroll 事件，无需 rAF 轮询
  window.addEventListener('scroll', onScrollOrResize, { capture: true, passive: true });
  window.addEventListener('resize', onScrollOrResize, { passive: true });
  el.addEventListener('scroll', onScrollOrResize, { passive: true });

  let ro: ResizeObserver | null = null;
  if (typeof ResizeObserver !== 'undefined') {
    ro = new ResizeObserver(onScrollOrResize);
    ro.observe(el);
    let p = el.parentElement;
    while (p && p !== document.body && p !== document.documentElement) {
      const oy = window.getComputedStyle(p).overflowY;
      if (oy === 'auto' || oy === 'scroll' || oy === 'hidden') {
        ro.observe(p);
      }
      p = p.parentElement;
    }
  }

  for (const type of BLOCKED_EVENTS) {
    el.addEventListener(type, onBlock, true);
  }
  el.addEventListener('focusin', onFocusIn, true);
  el.classList.add('vita-iso-busy');
  el.setAttribute('aria-busy', 'true');

  state.cleanupEvents = () => {
    window.removeEventListener('scroll', onScrollOrResize, true);
    window.removeEventListener('resize', onScrollOrResize);
    el.removeEventListener('scroll', onScrollOrResize);
    ro?.disconnect();
    ro = null;
    for (const type of BLOCKED_EVENTS) {
      el.removeEventListener(type, onBlock, true);
    }
    el.removeEventListener('focusin', onFocusIn, true);
    el.classList.remove('vita-iso-busy');
    el.removeAttribute('aria-busy');
    state.cleanupEvents = null;
  };
}

function ensureLayer(el: HostEl): LoadState {
  const addedHostClass = ensureHostPosition(el);
  if (el._vitaLoad) {
    if (addedHostClass) el._vitaLoad.addedHostClass = true;
    if (el._vitaLoad.overlay.parentElement !== el) {
      el.append(el._vitaLoad.overlay);
    }
    return el._vitaLoad;
  }

  const overlay = document.createElement('div');
  overlay.className = 'vita-iso-load';
  overlay.setAttribute('aria-busy', 'true');

  const box = document.createElement('div');
  box.className = 'vita-iso-load__box';
  box.innerHTML = '<div class="vita-iso-load__spin"></div>';
  overlay.append(box);
  el.append(overlay);

  const state: LoadState = {
    overlay,
    box,
    gen: 0,
    addedHostClass,
    cleanupEvents: null,
  };
  el._vitaLoad = state;
  return state;
}

function teardown(el: HostEl) {
  const state = el._vitaLoad;
  if (!state) return;
  state.cleanupEvents?.();
  if (state.addedHostClass) {
    el.classList.remove('vita-iso-host');
  }
  state.overlay.remove();
  delete el._vitaLoad;
}

function show(el: HostEl) {
  const state = ensureLayer(el);
  state.gen += 1;
  applyText(el, state.box);
  syncOverlayOffset(el, state.overlay);
  bindActiveEvents(el, state);
  state.overlay.classList.remove('is-leaving');
  state.overlay.classList.add('is-on');
}

function hide(el: HostEl) {
  const state = el._vitaLoad;
  if (!state || !state.overlay.classList.contains('is-on')) return;

  const gen = state.gen;
  state.overlay.classList.add('is-leaving');
  state.cleanupEvents?.();

  void (async () => {
    await nextTick();
    await waitFrames(1);
    if (el._vitaLoad?.gen !== gen) return;
    state.overlay.classList.remove('is-on');
    window.setTimeout(() => {
      if (el._vitaLoad?.gen !== gen) return;
      teardown(el);
    }, FADE_MS);
  })();
}

export const isolatedLoadingDirective: Directive = {
  mounted(el: HostEl, binding: DirectiveBinding) {
    if (isOn(binding.value)) show(el);
  },
  updated(el: HostEl, binding: DirectiveBinding) {
    const next = isOn(binding.value);
    const prev = isOn(binding.oldValue);
    if (next && el._vitaLoad && el._vitaLoad.overlay.parentElement !== el) {
      el.append(el._vitaLoad.overlay);
    }
    if (next === prev) return;
    if (next) show(el);
    else hide(el);
  },
  unmounted(el: HostEl) {
    teardown(el);
  },
};
