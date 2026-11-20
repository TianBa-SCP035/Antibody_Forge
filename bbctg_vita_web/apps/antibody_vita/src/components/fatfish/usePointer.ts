/**
 * 宠物操作页面时的可见反馈：从宠物身上飞出的虚拟指针、目标高亮框和一句说明。
 * 浏览器不允许网页移动真实鼠标，这里只是画出来给用户看宠物在点哪里。
 *
 * 一轮里指针只出现一次：第一步从宠物身上飞出，之后每步从上一处飞到下一处，
 * 两步之间（等模型想下一步）停在原处变淡；这一轮结束才淡出。高亮框在指针到达后才出现，
 * 每帧按目标当前的位置摆放，页面滚动、元素点完变长变短都跟着走。
 */

import { reactive } from 'vue';

import type { Pointer, PointerKind } from './pageAct';

const FLY_MIN_MS = 260;
const FLY_MAX_MS = 650;
const CLICK_MS = 160;
const LINGER_MS = 900;
const POINT_LINGER_MS = 6000;
/** 没收到这一轮结束（异常退出）时的兜底。 */
const IDLE_MAX_MS = 20000;
/** 和 .ff-pointer-label 的 max-width、行高一致，用来把说明留在屏幕里。 */
const LABEL_W = 260;
const LABEL_H = 24;

type Box = { left: number; top: number; width: number; height: number };

const reducedMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
const ease = (p: number) => (p < 0.5 ? 4 * p * p * p : 1 - (-2 * p + 2) ** 3 / 2);

/** 输入框的可见边框通常画在外面一两层包装上（如 Element Plus 的 wrapper），框选那一层。 */
function frameOf(el: Element): Element {
  if (!el.matches('input, textarea')) return el;
  const inner = el.getBoundingClientRect();
  let p = el.parentElement;
  for (let i = 0; p && i < 3; i += 1, p = p.parentElement) {
    const st = getComputedStyle(p);
    if (parseFloat(st.borderTopWidth) > 0 || st.boxShadow !== 'none') {
      const outer = p.getBoundingClientRect();
      return outer.width - inner.width < 64 && outer.height - inner.height < 28 ? p : el;
    }
  }
  return el;
}

export function usePointer(opts: { origin: () => { x: number; y: number }; face: (x: number) => void; look: () => void }) {
  const state = reactive({
    visible: false,
    idle: false,
    x: 0,
    y: 0,
    clicking: false,
    box: null as Box | null,
    labelAt: { left: 0, top: 0 },
    label: '',
    kind: 'click' as PointerKind,
  });
  let target: Element | null = null;
  let frameEl: Element | null = null;
  let aim = { x: 0, y: 0 };
  let flight: { x: number; y: number; start: number; ms: number } | null = null;
  let boxOn = false;
  let ending = false;
  let frame = 0;
  let boxTimer: number | undefined;
  let idleTimer: number | undefined;
  const wait = (ms: number) => new Promise((r) => window.setTimeout(r, ms));

  /** 按目标现在的位置算指针落点、高亮框和说明的位置；目标没了返回 false。 */
  function measure(): boolean {
    if (!target?.isConnected || !frameEl?.isConnected) return false;
    const r = frameEl.getBoundingClientRect();
    aim = { x: r.left + Math.min(r.width / 2, 40), y: r.top + r.height / 2 };
    if (!boxOn) return true;
    const box = { left: r.left - 4, top: r.top - 4, width: r.width + 8, height: r.height + 8 };
    if (!state.box) state.box = box;
    else Object.assign(state.box, box);
    const below = r.bottom + 10;
    state.labelAt.left = Math.max(4, Math.min(r.left - 4, window.innerWidth - LABEL_W - 4));
    state.labelAt.top = below + LABEL_H > window.innerHeight ? Math.max(4, r.top - 10 - LABEL_H) : below;
    return true;
  }

  function tick(now: number) {
    frame = 0;
    if (target && !measure()) {
      target = null;
      frameEl = null;
      state.box = null;
    }
    if (flight) {
      const p = flight.ms ? Math.min(1, (now - flight.start) / flight.ms) : 1;
      state.x = flight.x + (aim.x - flight.x) * ease(p);
      state.y = flight.y + (aim.y - flight.y) * ease(p);
      if (p >= 1) flight = null;
    } else if (target) {
      state.x = aim.x;
      state.y = aim.y;
    }
    if (target || flight) frame = requestAnimationFrame(tick);
  }

  function loop() {
    if (!frame) frame = requestAnimationFrame(tick);
  }

  function hide() {
    window.clearTimeout(boxTimer);
    window.clearTimeout(idleTimer);
    cancelAnimationFrame(frame);
    frame = 0;
    target = null;
    frameEl = null;
    flight = null;
    boxOn = false;
    ending = false;
    state.visible = false;
    state.idle = false;
    state.box = null;
    state.label = '';
  }

  /** 收起高亮框，指针留在原处变淡，等下一步或这一轮结束。 */
  function park() {
    boxOn = false;
    state.box = null;
    state.idle = true;
    target = null;
    frameEl = null;
  }

  const pointer: Pointer = {
    async show(el, label, kind) {
      window.clearTimeout(boxTimer);
      window.clearTimeout(idleTimer);
      ending = false;
      if (!state.visible) {
        const o = opts.origin();
        state.x = o.x;
        state.y = o.y;
        state.visible = true;
      }
      state.idle = false;
      boxOn = false;
      state.box = null;
      state.label = label;
      state.kind = kind;
      target = el;
      frameEl = frameOf(el);
      measure();
      const dist = Math.hypot(aim.x - state.x, aim.y - state.y);
      const ms = reducedMotion() ? 0 : Math.round(Math.min(FLY_MAX_MS, Math.max(FLY_MIN_MS, 200 + dist * 0.35)));
      flight = { x: state.x, y: state.y, start: performance.now(), ms };
      opts.face(aim.x);
      opts.look();
      loop();
      await wait(ms);
      if (target !== el) return;
      flight = null;
      state.x = aim.x;
      state.y = aim.y;
      boxOn = true;
      measure();
      loop();
      if (kind === 'click') {
        state.clicking = true;
        window.setTimeout(() => (state.clicking = false), 320);
        await wait(CLICK_MS);
      }
    },
    done() {
      window.clearTimeout(boxTimer);
      boxTimer = window.setTimeout(() => (ending ? hide() : park()), state.kind === 'point' ? POINT_LINGER_MS : LINGER_MS);
      window.clearTimeout(idleTimer);
      idleTimer = window.setTimeout(hide, IDLE_MAX_MS);
    },
    end(immediate) {
      if (!state.visible) return;
      // 指给用户看的高亮要留够时间，其余（以及用户停下、接手时）直接淡出。
      if (!immediate && state.kind === 'point' && boxOn) ending = true;
      else hide();
    },
  };

  function dispose() {
    hide();
  }

  return { pointerState: state, pointer, disposePointer: dispose };
}
