import type { Directive, DirectiveBinding } from 'vue';
import { nextTick } from 'vue';

const FADE_MS = 300;

type HostEl = HTMLElement & {
  _vitaLoad?: {
    overlay: HTMLElement;
    gen: number;
    raf: number;
  };
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

function coverBox(el: HTMLElement) {
  const r = el.getBoundingClientRect();
  let top = r.top;
  const main = document.getElementById('__vben_main_content');
  if (main?.contains(el)) {
    const chrome = document.querySelector('._scroll__fixed_');
    if (chrome) {
      top = Math.max(top, chrome.getBoundingClientRect().bottom);
    }
  }
  const left = Math.floor(r.left);
  top = Math.floor(top);
  return {
    left,
    top,
    width: Math.max(0, Math.ceil(r.right) - left),
    height: Math.max(0, Math.ceil(r.bottom) - top),
  };
}

function applyText(el: HTMLElement, overlay: HTMLElement) {
  const text = el.getAttribute('element-loading-text');
  let label = overlay.querySelector('.vita-iso-load__text');
  if (!text) {
    label?.remove();
    return;
  }
  if (!label) {
    label = document.createElement('p');
    label.className = 'vita-iso-load__text';
    overlay.append(label);
  }
  label.textContent = text;
}

function syncRect(el: HTMLElement, overlay: HTMLElement) {
  if (!el.isConnected) {
    overlay.style.visibility = 'hidden';
    return;
  }
  const box = coverBox(el);
  if (box.width < 1 || box.height < 1) {
    overlay.style.visibility = 'hidden';
    return;
  }
  overlay.style.visibility = 'visible';
  overlay.style.top = `${box.top}px`;
  overlay.style.left = `${box.left}px`;
  overlay.style.width = `${box.width}px`;
  overlay.style.height = `${box.height}px`;
}

function startTrack(el: HostEl) {
  const state = el._vitaLoad;
  if (!state || state.raf) return;
  const tick = () => {
    const current = el._vitaLoad;
    if (!current) return;
    syncRect(el, current.overlay);
    current.raf = requestAnimationFrame(tick);
  };
  state.raf = requestAnimationFrame(tick);
}

function stopTrack(el: HostEl) {
  const state = el._vitaLoad;
  if (!state?.raf) return;
  cancelAnimationFrame(state.raf);
  state.raf = 0;
}

function ensureLayer(el: HostEl) {
  if (el._vitaLoad) return el._vitaLoad;

  const overlay = document.createElement('div');
  overlay.className = 'vita-iso-load';
  overlay.setAttribute('aria-busy', 'true');
  overlay.innerHTML = '<div class="vita-iso-load__spin"></div>';
  document.body.append(overlay);

  const state = { overlay, gen: 0, raf: 0 };
  el._vitaLoad = state;
  return state;
}

function teardown(el: HostEl) {
  const state = el._vitaLoad;
  if (!state) return;
  stopTrack(el);
  state.overlay.remove();
  delete el._vitaLoad;
}

function show(el: HostEl) {
  const state = ensureLayer(el);
  state.gen += 1;
  applyText(el, state.overlay);
  syncRect(el, state.overlay);
  state.overlay.classList.remove('is-leaving');
  void state.overlay.offsetWidth;
  state.overlay.classList.add('is-on');
  startTrack(el);
}

function hide(el: HostEl) {
  const state = el._vitaLoad;
  if (!state || !state.overlay.classList.contains('is-on')) return;

  const gen = state.gen;
  state.overlay.classList.add('is-leaving');

  void (async () => {
    await nextTick();
    await waitFrames(2);
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
    if (next === prev) return;
    if (next) show(el);
    else hide(el);
  },
  unmounted(el: HostEl) {
    teardown(el);
  },
};
