<script lang="ts">
import type { RhythmGame } from './discoRhythm';

/** Lets 收起舞台 → 进入节奏舞台 keep the score within the same song session. */
let kept = null as { session: number; game: RhythmGame } | null;
</script>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue';
import { BASE, DISCO_BEST_KEY } from './constants';
import {
  ARROWS, BEAT_SECONDS, RHYTHM_BPM, SECTION_NAMES, advanceRhythm, buildRhythmChart, createRhythmGame,
  dispatchRhythmKey, hitSpace, holdTally, openRound, releaseSpace, resumeRhythmGame, rhythmAccuracy,
  sampleDiscoBeat, sectionAt, typeArrow, upcomingRound, type Arrow, type RhythmKey,
} from './discoRhythm';

const props = defineProps<{
  active: boolean; pending: boolean; ended: boolean; clock: number; duration: number;
  session: number; message: string; readTime: () => number;
}>();
const emit = defineEmits<{ play: []; replay: []; close: []; stop: [] }>();
const GLYPH: Record<RhythmKey, string> = { ArrowLeft: '←', ArrowUp: '↑', ArrowDown: '↓', ArrowRight: '→', Space: '空格' };
const VERDICT_TEXT = { Perfect: 'PERFECT', Great: 'GREAT', Good: 'GOOD', Bad: 'BAD', Miss: 'MISS' } as const;
const HOLD_TEXT = { start: '按住!', done: '长按成功', broken: '松早了' } as const;
const KEYS: RhythmKey[] = [...ARROWS, 'Space'];
/** Combo from which the console glows gold. */
const FEVER_COMBO = 5;
const stage = ref<HTMLElement | null>(null);
const game = shallowRef(kept?.session === props.session
  ? (props.ended ? kept.game : resumeRhythmGame(kept.game, props.clock))
  : createRhythmGame(buildRhythmChart(props.duration), props.clock));
const revision = ref(0);
const spaceDown = ref(false);
const best = ref(readBest());
const newRecord = ref(false);
let previousFocus: HTMLElement | null = null;
let mounted = false;

const beat = computed(() => sampleDiscoBeat(props.clock));
const view = computed(() => {
  void revision.value;
  const g = game.value;
  const now = props.clock;
  const holding = g.holding ? g.rounds[g.holding.round]! : null;
  const open = holding ?? openRound(g, now);
  const round = open ?? upcomingRound(g, now);
  const typed = holding ? holding.arrows.length : open ? g.typed : 0;
  const complete = !!open && typed >= open.arrows.length;
  const last = g.last && now - g.last.at < 0.9 ? g.last : null;
  return {
    round, open: !!open, holding: !!holding, typed, complete, last,
    // Once the row is typed (or between rows) the next one is shown early, so it can be read ahead.
    next: round && (complete || !open) ? upcomingRound(g, now, round.id) : undefined,
    sparkle: last && (last.verdict === 'Perfect' || last.verdict === 'Great') && last.hold !== 'start' ? last : null,
    press: g.press && now - g.press.at < 0.14 ? g.press : null,
    wrong: !!g.press && !g.press.ok && g.press.key !== 'Space' && now - g.press.at < 0.3,
    score: g.score, combo: g.combo, maxCombo: g.maxCombo, counts: g.counts, accuracy: rhythmAccuracy(g),
    holds: holdTally(g),
  };
});
/** Timeline of the shown round: its beats as ticks, the beat point, the hold bar, and the cursor. */
const timeline = computed(() => {
  const r = view.value.round;
  if (!r) return null;
  const end = (r.hold ?? r.hit) + BEAT_SECONDS / 2;
  const x = (t: number) => Math.min(100, Math.max(0, 100 * (t - r.start) / (end - r.start)));
  const ticks: { x: number; bar: boolean }[] = [];
  for (let i = 1; r.start + i * BEAT_SECONDS < end - 1e-3; i++) ticks.push({ x: x(r.start + i * BEAT_SECONDS), bar: i % 4 === 0 });
  return {
    ticks, hit: x(r.hit), hold: r.hold ? x(r.hold) : null,
    cursor: view.value.open ? x(props.clock) : null,
    held: view.value.holding ? x(props.clock) : null,
  };
});
/** Beats until the next row while waiting, so the count lands on the music. */
const countdown = computed(() => {
  const r = view.value.round;
  if (!props.active || !r || view.value.open) return 0;
  const wait = r.start - props.clock;
  return wait > 0 && wait <= BEAT_SECONDS * 4 ? Math.ceil(wait / BEAT_SECONDS - 1e-3) : 0;
});
const hint = computed(() => {
  const v = view.value;
  if (!v.round) return props.active ? '本曲已无新的一组' : '开始后这里出现方向键';
  if (!v.open) return '准备，下一组马上来';
  if (v.holding) return '按住别松，撑到金条结束！';
  if (v.wrong) return '按错了，从头再敲';
  if (!v.complete) return '按顺序敲方向键';
  return v.round.hold ? '光标到黄点时按住空格' : '光标到黄点时按空格';
});
const section = computed(() => SECTION_NAMES[sectionAt(props.clock)]);
const grade = computed(() => {
  const a = view.value.accuracy;
  return a >= 95 ? 'S' : a >= 85 ? 'A' : a >= 70 ? 'B' : 'C';
});
const progress = computed(() => Math.min(100, 100 * props.clock / Math.max(1, props.duration)));
const seconds = (value: number) => `${Math.floor(value / 60)}:${String(Math.floor(value % 60)).padStart(2, '0')}`;

function readBest() {
  try { return Math.max(0, Number(localStorage.getItem(DISCO_BEST_KEY)) || 0); } catch { return 0; }
}
function resetGame(joinAt = 0) {
  game.value = createRhythmGame(buildRhythmChart(props.duration), joinAt);
  spaceDown.value = false;
  newRecord.value = false;
  revision.value++;
}
watch(() => props.session, () => resetGame(props.clock));
watch(() => props.clock, (now) => {
  if (props.active || props.ended) {
    advanceRhythm(game.value, now);
    revision.value++;
  }
});
watch(() => props.ended, (ended) => {
  const score = game.value.score;
  if (!ended || score <= best.value) return;
  newRecord.value = true;
  best.value = score;
  try { localStorage.setItem(DISCO_BEST_KEY, String(score)); } catch { /* Private mode: the record just is not kept. */ }
});
function hit(key: RhythmKey) {
  if (!props.active || props.ended) return;
  // Judge against the media element at the key event, not the previous animation frame.
  const now = props.readTime();
  if (key === 'Space') { spaceDown.value = true; hitSpace(game.value, now); }
  else typeArrow(game.value, key as Arrow, now);
  revision.value++;
}
function release() {
  if (!spaceDown.value) return;
  spaceDown.value = false;
  releaseSpace(game.value, props.readTime());
  revision.value++;
}
function lift(key: RhythmKey) {
  if (key === 'Space') release();
}
function focusable() {
  return [...(stage.value?.querySelectorAll<HTMLElement>('button:not([disabled]), [tabindex="0"]') ?? [])];
}
function onKey(ev: KeyboardEvent) {
  if (!mounted || !stage.value) return;
  const el = ev.target instanceof Element ? ev.target : null;
  if (el?.closest('input, textarea, select, [contenteditable]:not([contenteditable="false"])')) return;
  if (ev.key === 'Tab') {
    if (ev.type !== 'keydown') return;
    const buttons = focusable();
    const first = buttons[0], last = buttons.at(-1);
    if (first && last && (ev.shiftKey ? document.activeElement === first : document.activeElement === last)) {
      ev.preventDefault(); (ev.shiftKey ? last : first).focus();
    }
    return;
  }
  dispatchRhythmKey(ev, props.active && !props.ended, false, hit, release);
}
function begin() { emit('play'); }
function replay() { resetGame(); emit('replay'); }
onMounted(() => {
  mounted = true;
  previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  window.addEventListener('keydown', onKey, true);
  window.addEventListener('keyup', onKey, true);
  // A key-up lost to another window must not leave the hold stuck down.
  window.addEventListener('blur', release);
  void nextTick(() => stage.value?.focus({ preventScroll: true }));
});
onBeforeUnmount(() => {
  mounted = false;
  kept = { session: props.session, game: game.value };
  window.removeEventListener('keydown', onKey, true);
  window.removeEventListener('keyup', onKey, true);
  window.removeEventListener('blur', release);
  if (previousFocus?.isConnected) previousFocus.focus({ preventScroll: true });
});
</script>

<template>
  <Teleport to="body">
    <section ref="stage" class="ff-disco-overlay" role="dialog" aria-modal="true" aria-label="大肥鱼节奏舞台" tabindex="-1"
      :style="{ '--ff-stage-pulse': beat.pulse }" @pointerdown.stop @click.stop>
      <header class="ff-dance-top">
        <div class="ff-dance-title">
          <p class="ff-dance-eyebrow">FATFISH · RHYTHM PARTY</p>
          <h2>大肥鱼蹦迪派对</h2>
          <div class="ff-dance-meta">
            <span>{{ Math.round(RHYTHM_BPM) }} BPM</span>
            <em v-if="active">{{ section }}</em>
            <div class="ff-dance-progress"><i :style="{ width: `${progress}%` }" /></div>
            <small>{{ seconds(clock) }} / {{ seconds(duration) }}</small>
          </div>
        </div>
        <nav aria-label="舞台控制">
          <button type="button" @click="emit('close')">收起舞台</button>
          <button type="button" class="ff-dance-stop" @click="emit('stop')">停止蹦迪</button>
        </nav>
      </header>

      <div class="ff-dance-floor">
        <div class="ff-dance-light left" aria-hidden="true" />
        <div class="ff-dance-light right" aria-hidden="true" />
        <div class="ff-dance-orbit" aria-hidden="true" />
        <div class="ff-dance-glow" aria-hidden="true" />
        <div class="ff-dance-avatar" :class="{ dancing: active, miss: view.last?.verdict === 'Miss' || view.last?.hold === 'broken' || view.wrong }">
          <video :key="active ? 'dance' : 'idle'" :src="BASE + (active ? '可爱宅舞.webm' : '待机呼吸休闲.webm')"
            autoplay muted loop playsinline :aria-label="active ? '大肥鱼伴舞' : '大肥鱼'" />
        </div>
        <div v-if="view.last" :key="`${view.last.round}-${view.last.hold ?? ''}`" class="ff-dance-verdict"
          :class="view.last.verdict.toLowerCase()" aria-live="polite">
          <strong>{{ VERDICT_TEXT[view.last.verdict] }}</strong>
          <span v-if="view.last.hold">{{ HOLD_TEXT[view.last.hold] }}</span>
          <span v-else-if="view.last.combo > 1">×{{ view.last.combo }}</span>
        </div>
        <p v-else-if="countdown" :key="countdown" class="ff-dance-countdown">{{ countdown }}</p>
        <div v-if="view.sparkle" :key="`spark-${view.sparkle.round}`" class="ff-dance-sparkle" aria-hidden="true">
          <i>✦</i><i>✦</i><i>✦</i>
        </div>
        <aside class="ff-dance-board" aria-label="本局分数">
          <span>得分</span><strong>{{ view.score.toLocaleString() }}</strong>
          <span>连击</span><strong :class="{ fever: view.combo >= FEVER_COMBO }">{{ view.combo }}</strong>
          <span>准确率</span><strong>{{ view.accuracy }}%</strong>
          <small v-if="best">本机最高 {{ best.toLocaleString() }}</small>
        </aside>
      </div>

      <div class="ff-dance-console" :class="{ fever: view.combo >= FEVER_COMBO }">
        <div class="ff-dance-row" :class="{ wrong: view.wrong, preview: !view.open }" aria-label="方向键序列">
          <span v-if="view.round" class="ff-dance-level" :class="{ hold: view.round.hold }">
            {{ view.round.arrows.length }} 键{{ view.round.hold ? ' · 长按' : '' }}
          </span>
          <template v-if="view.round">
            <span v-for="(arrow, i) in view.round.arrows" :key="`${view.round.id}-${i}`" class="ff-dance-arrow"
              :class="{ done: i < view.typed, next: view.open && i === view.typed }">{{ GLYPH[arrow] }}</span>
          </template>
          <span class="ff-dance-hint" :class="{ bad: view.wrong, go: view.complete || view.holding }">{{ hint }}</span>
        </div>
        <div class="ff-dance-next" :class="{ shown: view.next }" aria-hidden="true">
          <template v-if="view.next">
            <span>下一组</span>
            <i v-for="(arrow, i) in view.next.arrows" :key="`${view.next.id}-${i}`">{{ GLYPH[arrow] }}</i>
            <span v-if="view.next.hold" class="hold">长按</span>
          </template>
        </div>
        <div class="ff-dance-bar" :class="{ holding: view.holding }" aria-hidden="true">
          <template v-if="timeline">
            <i v-for="(t, i) in timeline.ticks" :key="i" class="ff-dance-tick" :class="{ bar: t.bar }" :style="{ left: `${t.x}%` }" />
            <i v-if="timeline.hold !== null" class="ff-dance-hold" :style="{ left: `${timeline.hit}%`, width: `${timeline.hold - timeline.hit}%` }" />
            <i v-if="timeline.held !== null" class="ff-dance-held" :style="{ left: `${timeline.hit}%`, width: `${timeline.held - timeline.hit}%` }" />
            <i class="ff-dance-point" :style="{ left: `${timeline.hit}%` }" />
            <i v-if="timeline.cursor !== null" class="ff-dance-cursor" :style="{ left: `${timeline.cursor}%` }" />
          </template>
        </div>
        <div class="ff-dance-keys">
          <button v-for="key in KEYS" :key="key" type="button" :aria-label="`按 ${GLYPH[key]}`"
            :class="{ space: key === 'Space', on: view.press?.key === key || (key === 'Space' && spaceDown), bad: view.press?.key === key && !view.press.ok }"
            @pointerdown.prevent="hit(key)" @pointerup="lift(key)" @pointercancel="lift(key)" @pointerleave="lift(key)">{{ GLYPH[key] }}</button>
        </div>
      </div>

      <div v-if="!active" class="ff-dance-curtain">
        <template v-if="ended">
          <h3>全曲完成！</h3>
          <p class="ff-dance-grade">{{ grade }}</p>
          <strong class="ff-dance-final">{{ view.score.toLocaleString() }}</strong>
          <p v-if="newRecord" class="ff-dance-record">新纪录！</p>
          <p v-else-if="best">本机最高 {{ best.toLocaleString() }}</p>
          <p>最高连击 {{ view.maxCombo }} · 准确率 {{ view.accuracy }}% · 长按 {{ view.holds.done }}/{{ view.holds.played }}</p>
          <p class="ff-dance-tally">
            <span class="perfect">PERFECT {{ view.counts.Perfect }}</span>
            <span class="great">GREAT {{ view.counts.Great }}</span>
            <span class="good">GOOD {{ view.counts.Good }}</span>
            <span class="bad">BAD {{ view.counts.Bad }}</span>
            <span class="miss">MISS {{ view.counts.Miss }}</span>
          </p>
          <div class="ff-dance-actions">
            <button type="button" class="ff-dance-primary" @click="replay">再来一曲</button>
            <button type="button" @click="emit('stop')">结束</button>
          </div>
        </template>
        <template v-else>
          <p class="ff-dance-eyebrow">FATFISH · RHYTHM PARTY</p>
          <h3>节奏舞台</h3>
          <p class="ff-dance-legend">
            <kbd>←</kbd><kbd>↑</kbd><kbd>↓</kbd><kbd>→</kbd> 按顺序敲箭头
            <kbd class="wide">空格</kbd> 光标到黄点时按
          </p>
          <p>按错一个就从头再敲；越准分越高，PERFECT / GREAT 连起来算连击，连击 {{ FEVER_COMBO }} 起进入 FEVER。</p>
          <p>标着「长按」的一组：黄点时<b>按住空格</b>，撑到金条结束再松。</p>
          <p>节拍点、长按都踩在这首歌的小节和乐句上 · Esc 随时结束</p>
          <p v-if="best">本机最高 {{ best.toLocaleString() }}</p>
          <p v-if="message" class="ff-dance-message">{{ message }}</p>
          <button type="button" class="ff-dance-primary" @click="begin">{{ pending ? '点击开蹦' : '开始' }}</button>
          <small>透过舞台仍能看到页面随拍跳动 · 成绩只存在本机，不写入业务数据</small>
        </template>
      </div>
    </section>
  </Teleport>
</template>

<style scoped>
/* Semi-transparent on purpose: the page keeps dancing behind the stage. Only the panels are dark. */
.ff-disco-overlay { position: fixed; inset: 0; z-index: 7200; display: flex; flex-direction: column; gap: 10px; padding: clamp(10px, 1.6vw, 22px); color: hsl(210 100% 97%); background: linear-gradient(180deg, hsl(255 60% 10% / .45), hsl(265 60% 12% / .62)); font-family: 'Segoe UI', 'PingFang SC', sans-serif; outline: none; overflow: hidden; overscroll-behavior: contain; user-select: none; text-shadow: 0 1px 3px hsl(240 60% 8% / .8); }
button { padding: 7px 13px; border: 1px solid hsl(200 90% 80% / .45); border-radius: 10px; color: inherit; background: hsl(228 55% 20% / .85); cursor: pointer; white-space: nowrap; font: inherit; font-size: 13px; }
button:hover { background: hsl(250 70% 40% / .9); }
button:focus-visible { outline: 2px solid hsl(176 100% 75%); outline-offset: 3px; }
p { margin: 3px 0; font-size: 13px; }
.ff-dance-eyebrow { margin: 0; font-size: 10px; letter-spacing: .24em; color: hsl(180 95% 74%); }

.ff-dance-top { position: relative; z-index: 3; display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; }
.ff-dance-title { padding: 8px 16px 10px; border: 1px solid hsl(200 90% 85% / .2); border-radius: 16px; background: hsl(242 60% 10% / .8); }
.ff-dance-title h2 { margin: 1px 0 6px; font-size: clamp(18px, 2vw, 26px); letter-spacing: .04em; }
.ff-dance-meta { display: flex; align-items: center; gap: 10px; font-size: 12px; color: hsl(200 70% 85%); }
.ff-dance-meta em { padding: 1px 8px; border-radius: 999px; font-style: normal; color: hsl(42 95% 12%); text-shadow: none; background: hsl(48 100% 68%); }
.ff-dance-meta small { font-size: 11px; font-variant-numeric: tabular-nums; }
.ff-dance-progress { width: clamp(100px, 20vw, 300px); height: 5px; border-radius: 5px; background: hsl(215 75% 85% / .2); overflow: hidden; }
.ff-dance-progress i { display: block; height: 100%; background: linear-gradient(90deg, hsl(178 100% 65%), hsl(47 100% 69%)); }
nav { display: flex; gap: 8px; }
.ff-dance-stop { border-color: hsl(345 100% 75% / .8); }

.ff-dance-floor { position: relative; flex: 1; min-height: 0; display: flex; align-items: flex-end; justify-content: center; }
.ff-dance-light { position: absolute; top: -10%; width: 30%; height: 120%; opacity: calc(.12 + var(--ff-stage-pulse) * .3); pointer-events: none; filter: blur(14px); }
.ff-dance-light.left { left: 12%; background: linear-gradient(200deg, hsl(300 100% 70% / .45), transparent 70%); clip-path: polygon(40% 0, 60% 0, 100% 100%, 0 100%); transform: rotate(-14deg); }
.ff-dance-light.right { right: 12%; background: linear-gradient(160deg, hsl(185 100% 65% / .45), transparent 70%); clip-path: polygon(40% 0, 60% 0, 100% 100%, 0 100%); transform: rotate(14deg); }
.ff-dance-orbit { position: absolute; bottom: 6%; height: min(78%, 46vh); aspect-ratio: 1; border: 1px solid hsl(182 100% 74% / .55); border-radius: 50%; scale: calc(.95 + var(--ff-stage-pulse) * .08); box-shadow: 0 0 calc(12px + var(--ff-stage-pulse) * 22px) hsl(280 95% 65% / .35), inset 0 0 35px hsl(210 100% 65% / .18); pointer-events: none; }
.ff-dance-glow { position: absolute; bottom: 0; width: min(46vw, 520px); aspect-ratio: 4 / 1; border-radius: 50%; background: radial-gradient(closest-side, hsl(290 100% 70% / calc(.22 + var(--ff-stage-pulse) * .35)), transparent); pointer-events: none; }
/* The WebM frame has wide margins around the sprite (feet ~30% above its bottom), hence the extra
   scale and the drop that puts her feet on the floor line. */
.ff-dance-avatar { position: relative; z-index: 1; height: min(100%, 62vh); aspect-ratio: 1; scale: 1.6; translate: 0 48%; transform-origin: 50% 100%; pointer-events: none; }
.ff-dance-avatar.dancing { translate: 0 calc(48% - var(--ff-stage-pulse) * 18px); }
.ff-dance-avatar.miss { animation: ff-dance-shake .3s; }
.ff-dance-avatar video { width: 100%; height: 100%; object-fit: contain; filter: drop-shadow(0 12px 28px hsl(185 100% 75% / .35)); }
.ff-dance-verdict { position: absolute; z-index: 2; top: 4%; left: 50%; display: flex; align-items: baseline; gap: 12px; translate: -50% 0; font-weight: 900; font-style: italic; letter-spacing: .06em; animation: ff-dance-pop .9s ease-out forwards; text-shadow: 0 3px 14px hsl(240 100% 20% / .9); pointer-events: none; }
.ff-dance-verdict strong { font-size: clamp(34px, 6vw, 72px); }
.ff-dance-verdict span { font-size: clamp(18px, 2.6vw, 32px); color: hsl(50 100% 80%); }
.ff-dance-verdict.perfect strong { background: linear-gradient(180deg, hsl(52 100% 80%), hsl(32 100% 58%)); background-clip: text; color: transparent; }
.ff-dance-verdict.great strong { color: hsl(185 100% 70%); }
.ff-dance-verdict.good strong { color: hsl(130 70% 66%); }
.ff-dance-verdict.bad strong { color: hsl(275 80% 75%); }
.ff-dance-verdict.miss strong { color: hsl(350 40% 72%); }
.ff-dance-countdown { position: absolute; z-index: 2; top: 4%; left: 50%; translate: -50% 0; font-size: clamp(48px, 8vw, 96px); font-weight: 900; color: hsl(50 100% 75%); animation: ff-dance-tick .45s ease-out; }
.ff-dance-sparkle { position: absolute; z-index: 2; top: 12%; left: 50%; width: 0; height: 0; pointer-events: none; }
.ff-dance-sparkle i { position: absolute; font-style: normal; font-size: 40px; color: hsl(50 100% 75%); text-shadow: 0 0 12px hsl(45 100% 60%); animation: ff-dance-spark .7s ease-out forwards; }
.ff-dance-sparkle i:nth-child(1) { --dx: -170px; --dy: -10px; }
.ff-dance-sparkle i:nth-child(2) { --dx: 160px; --dy: -30px; animation-delay: .05s; }
.ff-dance-sparkle i:nth-child(3) { --dx: 20px; --dy: 70px; animation-delay: .1s; font-size: 28px; }
.ff-dance-board { position: absolute; z-index: 2; right: 2%; top: 50%; translate: 0 -50%; display: flex; flex-direction: column; gap: 2px; padding: 14px 20px; border-radius: 16px; background: hsl(242 60% 10% / .72); border: 1px solid hsl(188 100% 75% / .2); }
.ff-dance-board span { font-size: 12px; letter-spacing: .1em; opacity: .85; }
.ff-dance-board strong { margin-bottom: 6px; font-size: clamp(20px, 2.6vw, 34px); color: hsl(50 100% 72%); font-variant-numeric: tabular-nums; }
.ff-dance-board strong.fever { color: hsl(28 100% 62%); text-shadow: 0 0 14px hsl(28 100% 55%); }
.ff-dance-board small { font-size: 11px; color: hsl(200 70% 83%); }

.ff-dance-console { position: relative; z-index: 3; display: flex; flex-direction: column; gap: 8px; width: min(100%, 880px); margin: 0 auto; padding: 12px clamp(12px, 2.4vw, 28px); border: 1px solid hsl(188 100% 75% / .3); border-radius: 18px; background: hsl(242 60% 9% / .78); box-shadow: 0 0 calc(10px + var(--ff-stage-pulse) * 16px) hsl(185 90% 65% / .25); transition: border-color .2s, box-shadow .2s; }
.ff-dance-console.fever { border-color: hsl(45 100% 65% / .8); box-shadow: 0 0 calc(14px + var(--ff-stage-pulse) * 22px) hsl(40 100% 55% / .45); }
.ff-dance-row { position: relative; display: flex; align-items: center; justify-content: center; gap: clamp(6px, 1vw, 12px); min-height: 64px; padding: 0 130px; transition: opacity .15s; }
.ff-dance-row.preview { opacity: .5; }
.ff-dance-row.wrong { animation: ff-dance-shake .3s; }
.ff-dance-level { position: absolute; left: 0; padding: 3px 9px; border: 1px solid hsl(50 100% 70% / .6); border-radius: 999px; font-size: 12px; color: hsl(50 100% 78%); }
.ff-dance-level.hold { border-color: hsl(32 100% 65%); background: hsl(32 100% 50% / .2); }
.ff-dance-arrow { display: grid; place-items: center; width: clamp(40px, 5vw, 58px); height: clamp(40px, 5vw, 58px); border: 2px solid hsl(210 60% 80% / .5); border-radius: 12px; background: hsl(230 50% 18% / .85); font-size: clamp(22px, 3vw, 34px); font-weight: 900; color: hsl(210 40% 88%); transition: background .08s, transform .08s; }
.ff-dance-arrow.next { border-color: hsl(185 100% 75%); box-shadow: 0 0 12px hsl(185 100% 65% / .6); transform: translateY(-3px); }
.ff-dance-arrow.done { border-color: hsl(50 100% 75%); background: linear-gradient(140deg, hsl(42 100% 55%), hsl(30 100% 55%)); color: hsl(30 80% 12%); text-shadow: none; transform: scale(1.06); }
.ff-dance-row.wrong .ff-dance-arrow { border-color: hsl(350 100% 70%); background: hsl(350 70% 35% / .85); color: hsl(0 0% 100%); }
.ff-dance-hint { position: absolute; right: 0; max-width: 124px; font-size: 12px; text-align: right; color: hsl(207 60% 84%); }
.ff-dance-hint.bad { color: hsl(350 100% 78%); }
.ff-dance-hint.go { color: hsl(50 100% 76%); }
.ff-dance-next { display: flex; align-items: center; justify-content: center; gap: 6px; min-height: 22px; font-size: 12px; color: hsl(207 60% 82%); opacity: 0; transition: opacity .2s; }
.ff-dance-next.shown { opacity: .8; }
.ff-dance-next i { display: grid; place-items: center; width: 22px; height: 22px; border: 1px solid hsl(210 60% 80% / .4); border-radius: 6px; font-style: normal; font-weight: 800; }
.ff-dance-next .hold { color: hsl(32 100% 70%); }
.ff-dance-bar { position: relative; height: 18px; margin: 4px 2%; border-radius: 9px; background: linear-gradient(90deg, hsl(250 60% 30% / .7), hsl(200 70% 30% / .7)); box-shadow: inset 0 0 0 1px hsl(200 90% 80% / .3); }
.ff-dance-tick { position: absolute; top: 5px; bottom: 5px; width: 2px; translate: -1px 0; background: hsl(210 80% 85% / .3); }
.ff-dance-tick.bar { top: 2px; bottom: 2px; background: hsl(210 80% 90% / .6); }
.ff-dance-hold { position: absolute; top: 3px; bottom: 3px; border-radius: 6px; background: linear-gradient(90deg, hsl(45 100% 60% / .55), hsl(32 100% 55% / .55)); }
.ff-dance-held { position: absolute; top: 3px; bottom: 3px; border-radius: 6px; background: linear-gradient(90deg, hsl(52 100% 72%), hsl(36 100% 60%)); box-shadow: 0 0 12px hsl(45 100% 60%); }
.ff-dance-point { position: absolute; top: -6px; bottom: -6px; width: 14px; translate: -7px 0; border-radius: 7px; background: hsl(50 100% 65%); box-shadow: 0 0 calc(8px + var(--ff-stage-pulse) * 14px) hsl(45 100% 60%); }
.ff-dance-cursor { position: absolute; top: -9px; bottom: -9px; width: 4px; translate: -2px 0; border-radius: 2px; background: hsl(0 0% 100%); box-shadow: 0 0 10px hsl(185 100% 75%); }
.ff-dance-keys { display: grid; grid-template-columns: repeat(4, minmax(44px, 70px)) minmax(120px, 220px); justify-content: center; gap: 8px; }
.ff-dance-keys button { padding: 8px 0; font-size: 18px; font-weight: 800; touch-action: none; transition: transform .06s, background .06s; }
.ff-dance-keys button.space { font-size: 14px; color: hsl(52 100% 76%); }
.ff-dance-keys button.on { transform: translateY(2px); background: hsl(185 80% 40%); }
.ff-dance-keys button.bad { background: hsl(350 70% 42%); }

.ff-dance-curtain { position: absolute; inset: 0; z-index: 4; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; padding: 20px; text-align: center; background: hsl(240 48% 11% / .76); }
.ff-dance-curtain h3 { margin: 0 0 8px; font-size: clamp(22px, 2.6vw, 34px); }
.ff-dance-curtain p { font-size: 14px; line-height: 1.7; }
.ff-dance-curtain b { color: hsl(50 100% 74%); }
.ff-dance-curtain small { margin-top: 10px; font-size: 11px; color: hsl(203 65% 83%); }
.ff-dance-legend { display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 6px; margin-bottom: 6px !important; }
.ff-dance-legend kbd { display: inline-grid; place-items: center; min-width: 30px; height: 30px; padding: 0 6px; border: 1px solid hsl(200 90% 80% / .5); border-bottom-width: 3px; border-radius: 7px; font: inherit; font-weight: 800; background: hsl(230 55% 20% / .9); }
.ff-dance-legend kbd.wide { min-width: 74px; margin-left: 14px; color: hsl(52 100% 76%); }
.ff-dance-message { color: hsl(45 100% 74%); }
.ff-dance-grade { font-size: clamp(56px, 9vw, 110px) !important; font-weight: 900; font-style: italic; line-height: 1 !important; color: hsl(48 100% 70%); text-shadow: 0 4px 20px hsl(32 100% 50% / .6); }
.ff-dance-final { font-size: 42px; color: hsl(48 100% 75%); font-variant-numeric: tabular-nums; }
.ff-dance-record { font-weight: 900; letter-spacing: .1em; color: hsl(28 100% 65%); animation: ff-dance-tick .6s ease-out; }
.ff-dance-tally { display: flex; flex-wrap: wrap; justify-content: center; gap: 12px; font-weight: 700; }
.ff-dance-tally .perfect { color: hsl(48 100% 70%); }
.ff-dance-tally .great { color: hsl(185 100% 70%); }
.ff-dance-tally .good { color: hsl(130 70% 66%); }
.ff-dance-tally .bad { color: hsl(275 80% 75%); }
.ff-dance-tally .miss { color: hsl(350 40% 74%); }
.ff-dance-actions { display: flex; align-items: center; gap: 10px; margin-top: 12px; }
.ff-dance-primary { margin-top: 12px; padding: 12px 28px; font-size: 17px; font-weight: 800; color: hsl(42 95% 12%); text-shadow: none; background: linear-gradient(110deg, hsl(46 100% 65%), hsl(32 100% 66%)); border-color: hsl(51 100% 80%); }
.ff-dance-actions button { padding: 12px 22px; font-size: 15px; }
.ff-dance-actions .ff-dance-primary { margin-top: 0; padding: 12px 28px; font-size: 17px; }

@keyframes ff-dance-pop { 0% { opacity: 0; scale: .6; } 15% { opacity: 1; scale: 1.15; } 30% { scale: 1; } 80% { opacity: 1; } 100% { opacity: 0; translate: -50% -14px; } }
@keyframes ff-dance-tick { from { scale: 1.4; opacity: .4; } to { scale: 1; opacity: 1; } }
@keyframes ff-dance-spark { from { opacity: 1; transform: translate(-50%, -50%) scale(.4) rotate(0); } to { opacity: 0; transform: translate(calc(-50% + var(--dx)), calc(-50% + var(--dy))) scale(1.6) rotate(70deg); } }
@keyframes ff-dance-shake { 0%, 100% { transform: translateX(0); } 25% { transform: translateX(-6px); } 75% { transform: translateX(6px); } }
@media (max-width: 860px) {
  .ff-dance-board, .ff-dance-eyebrow { display: none; }
  .ff-dance-row { flex-wrap: wrap; padding: 0; }
  .ff-dance-level, .ff-dance-hint { position: static; max-width: none; }
  .ff-dance-meta { flex-wrap: wrap; }
}
@media (prefers-reduced-motion: reduce) {
  .ff-dance-avatar.dancing { translate: 0 48%; }
  .ff-dance-orbit { scale: 1; box-shadow: none; }
  .ff-dance-avatar.miss, .ff-dance-row.wrong, .ff-dance-verdict, .ff-dance-countdown, .ff-dance-record, .ff-dance-sparkle i { animation: none; }
  .ff-dance-sparkle { display: none; }
  .ff-dance-light { opacity: .3; }
}
</style>
