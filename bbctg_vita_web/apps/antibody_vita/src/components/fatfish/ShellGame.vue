<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

type Phase = 'ready' | 'show' | 'shuffle' | 'guess' | 'result';
type RoundResult = { round: number; win: boolean };

const props = withDefaults(defineProps<{ rounds?: number }>(), {
  rounds: 3,
});

const emit = defineEmits<{
  round: [payload: RoundResult];
  finish: [payload: { wins: number; rounds: number }];
  phase: [payload: Phase];
}>();

const phase = ref<Phase>('ready');
const round = ref(1);
const wins = ref(0);
const slots = ref([0, 1, 2]);
const ballCupId = ref(0);
const lifted = ref<number[]>([]);
const selectedCupId = ref<number | null>(null);
const won = ref(false);
const arcs = ref<Record<number, number>>({});
const shuffleMs = ref(420);
const reducedMotion = ref(false);
const totalRounds = computed(() => Math.max(1, Math.floor(props.rounds)));
const timers = new Set<ReturnType<typeof setTimeout>>();
let active = false;
let guessResolver: ((cupId: number) => void) | null = null;

const hints: Record<Exclude<Phase, 'result'>, string> = {
  ready: '看好饭团在哪个碗下面',
  show: '记住了吗？',
  shuffle: '盯紧…',
  guess: '在哪个碗下面？点它',
};

const hint = computed(() =>
  phase.value === 'result' ? (won.value ? '猜对了！' : '不对哦') : hints[phase.value],
);

function setPhase(next: Phase) {
  phase.value = next;
  emit('phase', next);
}

function wait(ms: number) {
  return new Promise<void>((resolve) => {
    const timer = setTimeout(() => {
      timers.delete(timer);
      resolve();
    }, ms);
    timers.add(timer);
  });
}

function cupStyle(cupId: number) {
  const slot = slots.value.indexOf(cupId);
  return {
    '--x': `${slot * 58}px`,
    '--arc': `${arcs.value[cupId] ?? 0}px`,
    '--speed': `${reducedMotion.value ? 80 : shuffleMs.value}ms`,
  };
}

function chooseCup(cupId: number) {
  if (phase.value !== 'guess' || !guessResolver) return;
  const resolve = guessResolver;
  guessResolver = null;
  resolve(cupId);
}

function onKeydown(event: KeyboardEvent) {
  const target = event.target as HTMLElement | null;
  if (target?.matches('input, textarea, select, [contenteditable="true"]')) return;
  const slot = ['1', '2', '3'].indexOf(event.key);
  const arrowSlot = ['ArrowLeft', 'ArrowDown', 'ArrowRight'].indexOf(event.key);
  const guessedSlot = slot >= 0 ? slot : arrowSlot;
  if (guessedSlot < 0 || phase.value !== 'guess') return;
  const cupId = slots.value[guessedSlot];
  if (cupId === undefined) return;
  event.preventDefault();
  event.stopPropagation();
  chooseCup(cupId);
}

async function shuffle() {
  const swapCounts = [4, 6, 8] as const;
  const speeds = [420, 340, 270] as const;
  const level = Math.min(Math.max(round.value - 1, 0), 2) as 0 | 1 | 2;
  shuffleMs.value = reducedMotion.value ? 80 : speeds[level];
  setPhase('shuffle');

  for (let index = 0; index < swapCounts[level] && active; index += 1) {
    const first = Math.floor(Math.random() * 3);
    let second = Math.floor(Math.random() * 2);
    if (second >= first) second += 1;
    const firstCup = slots.value[first]!;
    const secondCup = slots.value[second]!;
    arcs.value = reducedMotion.value ? {} : { [firstCup]: -8, [secondCup]: 4 };
    const next = [...slots.value];
    next[first] = secondCup;
    next[second] = firstCup;
    slots.value = next;
    await wait(shuffleMs.value);
    arcs.value = {};
    await wait(28);
  }
}

function awaitGuess() {
  return new Promise<number>((resolve) => {
    guessResolver = resolve;
  });
}

async function play() {
  setPhase('ready');
  await wait(900);

  for (let current = 1; current <= totalRounds.value && active; current += 1) {
    round.value = current;
    slots.value = [0, 1, 2];
    ballCupId.value = Math.floor(Math.random() * 3);
    selectedCupId.value = null;
    lifted.value = [0, 1, 2];
    setPhase('show');
    await wait(700);
    if (!active) return;
    lifted.value = [];
    await wait(180);
    await shuffle();
    if (!active) return;
    setPhase('guess');

    const guessedCup = await awaitGuess();
    if (!active) return;
    selectedCupId.value = guessedCup;
    won.value = guessedCup === ballCupId.value;
    if (won.value) wins.value += 1;
    lifted.value = won.value ? [guessedCup] : [guessedCup, ballCupId.value];
    setPhase('result');
    emit('round', { round: current, win: won.value });
    await wait(900);
  }

  if (active) emit('finish', { wins: wins.value, rounds: totalRounds.value });
}

function stop() {
  active = false;
  guessResolver = null;
  window.removeEventListener('keydown', onKeydown, true);
  timers.forEach(clearTimeout);
  timers.clear();
}

defineExpose({ stop });

onMounted(() => {
  reducedMotion.value = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  active = true;
  window.addEventListener('keydown', onKeydown, true);
  void play();
});

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown, true);
  stop();
});
</script>

<template>
  <section
    class="shell-game"
    @pointerdown.stop
    @pointerup.stop
    @click.stop
    @dblclick.stop
    @contextmenu.stop.prevent
  >
    <div class="shell-head">
      <span>{{ hint }}</span>
      <b>{{ round }}/{{ totalRounds }}</b>
    </div>
    <div class="shell-stage">
      <span
        v-if="phase === 'show' || phase === 'result'"
        class="rice-ball"
        :style="{ transform: `translateX(${slots.indexOf(ballCupId) * 58}px)` }"
      >🍙</span>
      <button
        v-for="cupId in [0, 1, 2]"
        :key="cupId"
        class="cup"
        :class="{
          lifted: lifted.includes(cupId),
          chosen: selectedCupId === cupId,
          correct: phase === 'result' && cupId === ballCupId,
        }"
        :style="cupStyle(cupId)"
        :aria-label="`第 ${slots.indexOf(cupId) + 1} 个碗`"
        :disabled="phase !== 'guess'"
        @click="chooseCup(cupId)"
      >
        <span class="bowl">🥣</span>
        <i v-if="phase === 'result' && (selectedCupId === cupId || ballCupId === cupId)">
          {{ ballCupId === cupId ? '✓' : '✗' }}
        </i>
      </button>
    </div>
  </section>
</template>

<style scoped>
.shell-game {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 8px;
  z-index: 7;
  width: calc(100% - 12px);
  height: 104px;
  margin: 0 6px;
  padding: 5px 8px 6px;
  border: 1px solid rgba(186, 230, 253, 0.8);
  border-radius: 14px;
  box-sizing: border-box;
  color: #0f172a;
  background: rgba(240, 249, 255, 0.88);
  box-shadow: 0 5px 14px rgba(15, 23, 42, 0.14);
  backdrop-filter: blur(4px);
  pointer-events: auto;
  user-select: none;
}
.shell-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 22px;
  padding: 0 4px 2px;
  font-size: 11px;
}
.shell-head b {
  color: #0284c7;
  font-size: 10px;
}
.shell-stage {
  position: relative;
  width: 168px;
  height: 68px;
  margin: 0 auto;
}
.rice-ball {
  position: absolute;
  left: 15px;
  bottom: 2px;
  z-index: 0;
  width: 32px;
  text-align: center;
  font-size: 21px;
  transition: transform var(--speed, 220ms) ease;
}
.cup {
  position: absolute;
  left: 0;
  bottom: 0;
  z-index: 1;
  width: 52px;
  height: 60px;
  padding: 0;
  border: 0;
  outline: none;
  color: #0f172a;
  background: transparent;
  cursor: pointer;
  transform: translate(var(--x), var(--arc));
  transition:
    transform var(--speed) cubic-bezier(0.4, 0, 0.2, 1),
    filter 160ms;
}
.cup:disabled {
  cursor: default;
}
.cup.lifted {
  transform: translate(var(--x), -22px);
}
.cup:not(:disabled):hover .bowl {
  filter: brightness(1.08);
}
.bowl {
  display: block;
  font-size: 34px;
  filter: drop-shadow(0 3px 3px rgba(15, 23, 42, 0.18));
}
.cup i {
  position: absolute;
  right: 0;
  top: 4px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  color: #fff;
  background: #ef4444;
  font: 700 13px/18px sans-serif;
  font-style: normal;
}
.cup.correct i {
  background: #22c55e;
}
@media (prefers-reduced-motion: reduce) {
  .cup,
  .rice-ball {
    transition-duration: 80ms;
  }
}
</style>
