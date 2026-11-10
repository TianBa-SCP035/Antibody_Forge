import { onBeforeUnmount, onMounted, ref } from 'vue';

import './fatfishDisco.css';
import {
  RHYTHM_BPM, BEAT_OFFSET_SECONDS, FULL_TRACK_SECONDS, discoLightFrames, discoMotionFrames, type DanceKind,
} from './discoRhythm';

// Tempo measured from the bundled track, shared with the rhythm chart and the page dance.
export const DISCO_BPM = RHYTHM_BPM;
export const POKE_GAP_MS = 1250;
export const POKE_THRESHOLD = 100;
/** Pause after the last poke (once past the threshold) before the party starts. */
export const SETTLE_MS = 700;
/** From the third poke on the streak owns the pet; one or two taps keep native drag, double-click and menu. */
const FLURRY = 3;
const BEAT_MS = 60_000 / DISCO_BPM;
const AUDIO_URL = `${import.meta.env.BASE_URL}fatfish/easter/friends-wine-dj-full.mp3`;
const EDITOR = 'input, textarea, select, [contenteditable]:not([contenteditable="false"])';
const DIALOG = '[role="dialog"], [aria-modal="true"], .el-overlay, .el-popper';

interface Options {
  enabled: () => boolean;
  prepare: () => void;
  resetPointer: (preserveTaps?: boolean) => void;
  /** `streak` is the hidden poke count including this one, so the visible stamp shows the real total. */
  tap: (ev: PointerEvent, streak: number) => void;
}

/** Pure streak state, also used by the Node regression tests (no real UI clicks). */
export function createPokeStreak() {
  let count = 0;
  let last = -Infinity;
  return {
    get count() { return count; },
    expire(now: number) { if (now - last > POKE_GAP_MS) count = 0; },
    release(now: number) {
      this.expire(now);
      last = now;
      count += 1;
      return count >= POKE_THRESHOLD;
    },
    reset() { count = 0; last = -Infinity; },
  };
}

/** Capture only the pet/ball hit-targets; cards, inputs and mini-games are excluded. */
export function useFatfishDisco(options: Options) {
  const active = ref(false);
  const pending = ref(false);
  const busy = ref(false);
  const message = ref('');
  const clock = ref(0);
  const duration = ref(FULL_TRACK_SECONDS);
  const finished = ref(false);
  const stageOpen = ref(false);
  const session = ref(0);
  const streak = createPokeStreak();
  let burstTimer: number | undefined;
  let clockFrame = 0;
  let frame = 0;
  let generation = 0;
  let disposed = false;
  let audio: HTMLAudioElement | undefined;
  let observer: MutationObserver | undefined;
  const targets = new Set<HTMLElement>();
  const motions = new Map<HTMLElement, Animation>();
  /** Beat-flashing corner lights over the page; created per dance, removed with it. */
  let lights: { el: HTMLElement; motion?: Animation } | undefined;
  const reduced = typeof window.matchMedia === 'function' ? window.matchMedia('(prefers-reduced-motion: reduce)') : undefined;
  let down: {
    id: number; x: number; y: number; time: number; distance: number;
    suppressed: boolean; hit: HTMLElement;
  } | undefined;

  function hitTarget(ev: Event) {
    const el = ev.target instanceof Element ? ev.target : null;
    if (!el || el.closest('.ff-pill, .ff-bubbles, .ff-menu, .ff-fall, .ff-shell-game, button:not(.ff-ball), input, textarea')) return null;
    return el.closest<HTMLElement>('.ff-pet, .ff-ball');
  }
  function swallow(ev: Event) {
    ev.preventDefault();
    ev.stopImmediatePropagation();
  }
  function releaseCapture() {
    if (!down) return;
    try {
      if (down.hit.hasPointerCapture(down.id)) down.hit.releasePointerCapture(down.id);
    } catch { /* Target may have unmounted during navigation. */ }
  }
  function clearBurst() {
    window.clearTimeout(burstTimer);
    streak.reset();
    busy.value = active.value || pending.value;
  }
  function clearMotion() {
    cancelAnimationFrame(clockFrame);
    clockFrame = 0;
    cancelAnimationFrame(frame);
    for (const motion of motions.values()) motion.cancel();
    motions.clear();
    frame = 0;
    observer?.disconnect();
    observer = undefined;
    lights?.motion?.cancel();
    lights?.el.remove();
    lights = undefined;
    for (const el of targets) el.classList.remove('ff-disco-target', 'ff-disco-paused');
    targets.clear();
    document.documentElement.classList.remove('ff-disco-running');
  }
  function stop() {
    generation += 1; // Invalidates a delayed play() promise, including after Esc/unmount.
    active.value = false;
    pending.value = false;
    message.value = '';
    stageOpen.value = false;
    finished.value = false;
    clock.value = 0;
    releaseCapture();
    down = undefined;
    clearBurst();
    options.resetPointer();
    clearMotion();
    if (audio) {
      audio.pause();
      audio.currentTime = 0;
    }
  }
  function syncTargets() {
    frame = 0;
    if (!active.value) return;
    // Verified Vben layout landmarks. Animate only these peers, never nested cards.
    // The pet's positioning stage is outside #app's layout and outside its WebM slots.
    const found = [...document.querySelectorAll<HTMLElement>(
      '#app aside.fixed, #app header.bg-header, #app main.bg-background-deep, .ff-stage',
    )].filter((el, i, all) => !all.some((parent, j) => i !== j && parent.contains(el)));
    for (const el of targets) {
      if (!found.includes(el)) {
        el.classList.remove('ff-disco-target', 'ff-disco-paused');
        motions.get(el)?.cancel();
        motions.delete(el);
        targets.delete(el);
      }
    }
    const focused = document.activeElement;
    const dialogOpen = [...document.querySelectorAll<HTMLElement>(DIALOG)]
      .some((el) => !el.closest('.ff-disco-overlay') && el.getClientRects().length > 0 && getComputedStyle(el).visibility !== 'hidden');
    found.forEach((el) => {
      // A focused editor's whole enclosing landmark stays still (no inverse transforms).
      const editing = focused instanceof Element && focused.matches(EDITOR) && el.contains(focused);
      el.classList.toggle('ff-disco-paused', editing || dialogOpen);
      if (!targets.has(el)) {
        el.classList.add('ff-disco-target');
        targets.add(el);
      }
      if (editing || dialogOpen) {
        motions.get(el)?.cancel();
        motions.delete(el);
      } else if (!motions.has(el) && typeof el.animate === 'function') {
        const motion = el.animate(discoMotionFrames(danceKind(el), !!reduced?.matches),
          { duration: BEAT_MS * 4, iterations: Infinity, easing: 'linear' });
        motion.pause();
        motions.set(el, motion);
      }
    });
    applyMotionClock();
  }
  function danceKind(el: HTMLElement): DanceKind {
    if (el.classList.contains('ff-stage')) return 'pet';
    const tag = el.tagName?.toLowerCase();
    return tag === 'aside' ? 'aside' : tag === 'header' ? 'header' : 'main';
  }
  function scheduleSync() {
    if (active.value && !frame) frame = requestAnimationFrame(syncTargets);
  }
  function lightUp() {
    if (!lights) {
      const el = document.createElement('div');
      el.className = 'ff-disco-lights';
      el.setAttribute('aria-hidden', 'true');
      document.body.append(el);
      lights = { el };
    }
    lights.motion?.cancel();
    lights.motion = typeof lights.el.animate === 'function'
      ? lights.el.animate(discoLightFrames(!!reduced?.matches), { duration: BEAT_MS * 4, iterations: Infinity, easing: 'linear' })
      : undefined;
    lights.motion?.pause();
  }
  function startMotion() {
    clearMotion();
    document.documentElement.classList.add('ff-disco-running');
    lightUp();
    syncTargets();
    observer = new MutationObserver((records) => {
      // Game notes and HUD update every frame; do not rescan business layout for those mutations.
      if (records.some((record) => {
        const el = record.target instanceof Element ? record.target : record.target.parentElement;
        return !el?.closest('.ff-disco-overlay, .ff-disco-controls');
      })) scheduleSync();
    });
    observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['style', 'aria-hidden', 'open'] });
  }
  function ensureAudio() {
    if (!audio) {
      audio = new Audio(AUDIO_URL);
      audio.preload = 'auto';
      audio.volume = 0.65;
      audio.addEventListener('ended', finish);
      audio.addEventListener('loadedmetadata', () => {
        if (audio && Number.isFinite(audio.duration) && audio.duration > 0) duration.value = audio.duration;
      });
      audio.addEventListener('error', () => {
        if (!active.value && !pending.value) return;
        generation += 1;
        active.value = false;
        pending.value = true;
        clearMotion();
        message.value = '配乐加载失败，点击重试';
      });
      audio.addEventListener('timeupdate', () => { if (audio?.ended) finish(); });
    }
    return audio;
  }
  function readTime() { return audio?.currentTime ?? clock.value; }
  function applyMotionClock() {
    const ms = Math.max(0, readTime() - BEAT_OFFSET_SECONDS) * 1000;
    for (const motion of motions.values()) motion.currentTime = ms;
    if (lights?.motion) lights.motion.currentTime = ms;
  }
  function tickClock() {
    if (!active.value || disposed) return;
    clock.value = readTime();
    applyMotionClock();
    clockFrame = requestAnimationFrame(tickClock);
  }
  function finish() {
    if (finished.value) return;
    audio?.pause();
    generation++;
    active.value = false;
    pending.value = false;
    finished.value = true;
    clock.value = Number.isFinite(audio?.duration) ? audio!.duration : duration.value;
    clearBurst();
    options.resetPointer();
    clearMotion();
  }
  function play() {
    if (disposed || active.value) return;
    const token = ++generation;
    const player = ensureAudio();
    if (finished.value || player.ended) { player.currentTime = 0; clock.value = 0; }
    if (player.currentTime <= .01) session.value++;
    finished.value = false;
    pending.value = true;
    busy.value = true;
    message.value = '';
    if (player.error) player.load();
    // The poke trigger runs from a timer; a hundred pokes give the page sticky activation, so
    // autoplay allows it. If a browser still refuses, the catch below offers a click-to-start.
    void player.play().then(() => {
      if (disposed || token !== generation) return;
      pending.value = false;
      active.value = true;
      if (Number.isFinite(player.duration) && player.duration > 0) duration.value = player.duration;
      startMotion();
      tickClock();
    }).catch(() => {
      if (disposed || token !== generation) return;
      active.value = false;
      pending.value = true;
      clearMotion();
      message.value = player.error ? '配乐加载失败，点击重试' : '播放被浏览器拦截，请点击开蹦';
    });
  }
  function openStage() { stageOpen.value = true; }
  function closeStage() { stageOpen.value = false; }
  function replay() {
    const reopen = stageOpen.value;
    stop();
    stageOpen.value = reopen;
    play();
  }
  function onDown(ev: PointerEvent) {
    if (ev.button !== 0 || !ev.isPrimary || !options.enabled()) return;
    const hit = hitTarget(ev);
    if (!hit || down) return;
    if (active.value || pending.value) { swallow(ev); return; }
    streak.expire(performance.now());
    window.clearTimeout(burstTimer);
    options.prepare();
    const suppressed = streak.count >= FLURRY;
    if (suppressed) options.resetPointer(true);
    down = {
      id: ev.pointerId, x: ev.clientX, y: ev.clientY, time: performance.now(),
      distance: 0, suppressed, hit,
    };
    if (suppressed) {
      swallow(ev);
      hit.setPointerCapture(ev.pointerId);
    }
    // Early presses still use the normal hold/drag handlers. A running flurry does not.
  }
  function onMove(ev: PointerEvent) {
    if (!down || ev.pointerId !== down.id) return;
    down.distance = Math.max(down.distance, Math.hypot(ev.clientX - down.x, ev.clientY - down.y));
    if (down.suppressed) swallow(ev);
  }
  function onUp(ev: PointerEvent) {
    if (!down || ev.pointerId !== down.id) return;
    const press = down;
    const valid = ev.button === 0 && ev.type === 'pointerup' && press.distance <= 8
      && Math.hypot(ev.clientX - press.x, ev.clientY - press.y) <= 8
      && performance.now() - press.time < 480;
    releaseCapture();
    down = undefined;
    if (!valid) {
      clearBurst();
      if (press.suppressed) { swallow(ev); options.resetPointer(); }
      return;
    }
    swallow(ev);
    options.resetPointer(true);
    busy.value = true;
    // Past the threshold the user may keep poking; the party starts once they let go.
    const ready = streak.release(performance.now());
    options.tap(ev, streak.count);
    burstTimer = window.setTimeout(() => {
      clearBurst();
      if (ready && !disposed) play();
    }, ready ? SETTLE_MS : POKE_GAP_MS);
  }
  /** True once the streak is past an ordinary double-tap, so its pairs must not open chat. */
  function flurrying() { return streak.count >= FLURRY; }
  function onCancel(ev: PointerEvent) {
    if (!down || ev.pointerId !== down.id) return;
    const suppressed = down.suppressed;
    releaseCapture();
    down = undefined;
    clearBurst();
    if (suppressed) { swallow(ev); options.resetPointer(); }
  }
  function onAux(ev: Event) {
    if (!hitTarget(ev)) return;
    if (active.value || pending.value || flurrying()) swallow(ev);
  }
  function onKey(ev: KeyboardEvent) {
    if (ev.key === 'Escape' && (active.value || pending.value || stageOpen.value)) {
      ev.preventDefault();
      ev.stopImmediatePropagation();
      stop();
    }
  }
  function onVisibility() { if (document.hidden) stop(); }
  function onBlur() {
    // Do not leave a captured pointer or latent double-click behind on an Alt-Tab.
    if (down || (!active.value && !pending.value)) {
      releaseCapture(); down = undefined; clearBurst(); options.resetPointer();
    }
  }
  function onMotionPreference() {
    for (const motion of motions.values()) motion.cancel();
    motions.clear();
    if (lights) lightUp();
    scheduleSync();
  }
  onMounted(() => {
    reduced?.addEventListener?.('change', onMotionPreference);
    window.addEventListener('keydown', onKey, true);
    window.addEventListener('blur', onBlur);
    document.addEventListener('visibilitychange', onVisibility);
    document.addEventListener('focusin', scheduleSync);
    document.addEventListener('focusout', scheduleSync);
  });
  onBeforeUnmount(() => {
    disposed = true;
    reduced?.removeEventListener?.('change', onMotionPreference);
    stop();
    window.removeEventListener('keydown', onKey, true);
    window.removeEventListener('blur', onBlur);
    document.removeEventListener('visibilitychange', onVisibility);
    document.removeEventListener('focusin', scheduleSync);
    document.removeEventListener('focusout', scheduleSync);
    audio?.removeAttribute('src');
    audio?.load();
    audio = undefined;
  });
  return { active, pending, busy, message, clock, duration, finished, stageOpen, session, readTime, flurrying, play, stop, replay, openStage, closeStage, onDown, onMove, onUp, onCancel, onAux };
}