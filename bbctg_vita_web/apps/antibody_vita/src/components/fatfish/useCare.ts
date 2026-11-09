/**
 * Care / affinity for FatFish. Stats move on real time (including while the page is closed) and on what
 * the user does with her, so the state is something you can actually notice: idle animations, lines,
 * chat tone and the menu status all read from `careState`. Work quality never depends on it.
 */

import { computed, ref } from 'vue';

import { CARE_KEY, PIN_KEY } from './constants';

export type CareStats = {
  satiety: number;
  mood: number;
  energy: number;
  /** Long-term affinity points; never decays, only gated by a daily cap. */
  affinity: number;
  /** Last time the stats were advanced (ms). */
  ts: number;
  /** Affinity gained on `day` (YYYY-MM-DD), for the daily cap. */
  day: string;
  dayGain: number;
  /** Affinity from finished tasks on `day`; capped separately so using her for work alone doesn't max the bond. */
  dayTaskGain: number;
};

export type CareEvent =
  | 'feed'
  | 'pet'
  | 'comfort'
  | 'play'
  | 'dance'
  | 'punch'
  | 'task'
  | 'taskFail'
  | 'chat';

export type CareState = 'happy' | 'normal' | 'hungry' | 'tired' | 'down';

/** Shown at the top of the right-click menu, in her own words. */
export const CARE_STATE_LABEL: Record<CareState, string> = {
  happy: '尾巴停不下来',
  normal: '摸鱼待机中',
  hungry: '想吃白饭',
  tired: '想 DeepSleep',
  down: '有点蔫',
};

/** Affinity needed to reach each level (index = level - 1). */
const LEVELS = [0, 15, 45, 90, 150, 230, 330, 450];
/** Lv3 is when she starts calling the user 鱼片 (see careMoodHint). */
const LEVEL_NAMES = ['刚冒泡', '眼熟了', '鱼片', '摸鱼搭子', '干饭搭子', '同一片海', '心照不宣', '专属鱼片'];
const DAILY_AFFINITY_CAP = 25;
const DAILY_TASK_AFFINITY_CAP = 5;
/** Offline catch-up is capped so a long weekend doesn't zero everything. */
const MAX_CATCHUP_H = 16;
const FEED_SATIETY = 30;

/**
 * Hourly drift. Tuned by simulating workdays (9–18 h, 6–18 agent tasks): fed once she is hungry in the
 * morning until lunch, fed twice she rarely is, never fed she is hungry most of the day; she only gets
 * tired after a long, busy day. Dozing on the page is a light nap; a closed page is a full night's sleep.
 */
const RATE = {
  awake: { satiety: -3, energy: -6, energyNight: -10 },
  nap: { satiety: -1.5, energy: 10 },
  away: { satiety: -1, energy: 24 },
};

export function clampCare(n: number) {
  return Math.max(0, Math.min(100, Math.round(Number(n) || 0)));
}

function today() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function loadCare(): CareStats {
  const fresh: CareStats = {
    satiety: 70,
    mood: 70,
    energy: 80,
    affinity: 0,
    ts: Date.now(),
    day: today(),
    dayGain: 0,
    dayTaskGain: 0,
  };
  try {
    const raw = localStorage.getItem(CARE_KEY);
    if (!raw) return fresh;
    const o = JSON.parse(raw);
    return {
      satiety: clampCare(o.satiety ?? fresh.satiety),
      mood: clampCare(o.mood ?? fresh.mood),
      energy: clampCare(o.energy ?? fresh.energy),
      affinity: Math.max(0, Math.round(Number(o.affinity) || 0)),
      ts: Number(o.ts) || Date.now(),
      day: typeof o.day === 'string' ? o.day : today(),
      dayGain: Number(o.dayGain) || 0,
      dayTaskGain: Number(o.dayTaskGain) || 0,
    };
  } catch {
    return fresh;
  }
}

export function levelOf(affinity: number) {
  let level = 1;
  for (let i = 0; i < LEVELS.length; i += 1) if (affinity >= LEVELS[i]!) level = i + 1;
  const cur = LEVELS[level - 1]!;
  const next = LEVELS[level];
  return {
    level,
    name: LEVEL_NAMES[level - 1]!,
    progress: next === undefined ? 1 : (affinity - cur) / (next - cur),
    max: next === undefined,
  };
}

export function stateOf(c: Pick<CareStats, 'satiety' | 'mood' | 'energy'>): CareState {
  if (c.satiety < 30) return 'hungry';
  if (c.energy < 25) return 'tired';
  if (c.mood < 35) return 'down';
  if (c.mood >= 72 && c.satiety >= 45 && c.energy >= 40) return 'happy';
  return 'normal';
}

export function useCare(opts: {
  say: (text: string) => void;
  pick: <T extends string>(pool: readonly T[]) => T;
  pinLines: { on: readonly string[]; off: readonly string[] };
  onLevelUp?: (level: number, name: string) => void;
}) {
  const pinned = ref(typeof localStorage !== 'undefined' && localStorage.getItem(PIN_KEY) === '1');
  const care = ref<CareStats>(loadCare());
  const careState = computed(() => stateOf(care.value));
  const careLevel = computed(() => levelOf(care.value.affinity));
  /** Hours the page was closed before this session (for the boot greeting). */
  const awayHours = ref(0);
  const lastEventAt = new Map<CareEvent, number>();

  function saveCare() {
    try {
      localStorage.setItem(CARE_KEY, JSON.stringify(care.value));
    } catch {
      /* ignore */
    }
  }

  /**
   * Advance stats by elapsed real time. Awake she slowly gets hungry and tired; a nap on the page recovers
   * some energy; while the page is closed she "went home" and sleeps properly. Late at night she tires faster.
   */
  function tick(sleeping: boolean, away = false) {
    const now = Date.now();
    const c = care.value;
    const h = Math.min(MAX_CATCHUP_H, Math.max(0, (now - c.ts) / 3_600_000));
    if (h < 0.005) return;
    const hour = new Date().getHours();
    const night = hour >= 22 || hour < 7;
    let { satiety, mood, energy } = c;
    if (away) {
      satiety += RATE.away.satiety * h;
      energy += RATE.away.energy * h;
    } else if (sleeping) {
      satiety += RATE.nap.satiety * h;
      energy += RATE.nap.energy * h;
    } else {
      satiety += RATE.awake.satiety * h;
      energy += (night ? RATE.awake.energyNight : RATE.awake.energy) * h;
    }
    satiety = clampCare(satiety);
    energy = clampCare(energy);
    // Mood leans back toward a level set by how fed and rested she is.
    const target = 35 + 0.35 * ((satiety + energy) / 2);
    mood += (target - mood) * Math.min(1, 0.25 * h);
    care.value = { ...c, satiety, mood: clampCare(mood), energy, ts: now };
    saveCare();
  }

  /** Called once at mount: catches up the time the page was closed (treated as sleeping). */
  function resume() {
    awayHours.value = Math.max(0, (Date.now() - care.value.ts) / 3_600_000);
    tick(true, true);
  }

  function gainAffinity(n: number) {
    const c = care.value;
    const day = today();
    const dayGain = c.day === day ? c.dayGain : 0;
    const dayTaskGain = c.day === day ? c.dayTaskGain : 0;
    const before = levelOf(c.affinity).level;
    let affinity = c.affinity;
    let gained = dayGain;
    if (n > 0) {
      const room = Math.max(0, DAILY_AFFINITY_CAP - dayGain);
      const add = Math.min(room, n);
      affinity += add;
      gained += add;
    } else {
      // Losses never drop below the floor of the current level: annoying her stings but doesn't erase history.
      affinity = Math.max(LEVELS[before - 1]!, affinity + n);
    }
    care.value = { ...care.value, affinity, day, dayGain: gained, dayTaskGain };
    const after = levelOf(affinity);
    if (after.level > before) opts.onLevelUp?.(after.level, after.name);
  }

  /** Apply what just happened. Repeating the same thing within a minute counts for less (no grinding). */
  function onCare(event: CareEvent, amount = 1) {
    tick(false);
    const now = Date.now();
    const spam = now - (lastEventAt.get(event) ?? 0) < 60_000;
    lastEventAt.set(event, now);
    const k = spam ? 0.35 : 1;
    const c = { ...care.value };
    let affinity = 0;
    switch (event) {
      case 'feed':
        if (c.satiety >= 85) {
          c.satiety += 2;
          c.mood -= 2;
        } else {
          c.satiety += FEED_SATIETY * k;
          c.mood += 3 * k;
          affinity = spam ? 0 : 1;
        }
        break;
      case 'pet': {
        const stage = Math.max(1, Math.min(3, amount));
        c.mood += (1 + stage * 1.5) * k;
        c.energy -= 0.5;
        if (stage >= 2 && !spam) affinity = 1;
        break;
      }
      case 'comfort':
        c.mood += 6;
        affinity = 1;
        break;
      case 'play': {
        const hits = Math.max(0, amount);
        c.mood += Math.min(16, 3 + hits * 1.6) * k;
        c.energy -= 6;
        c.satiety += hits * 0.8 - 2;
        affinity = hits >= 5 && !spam ? 2 : 0;
        break;
      }
      case 'dance': {
        const hits = Math.max(0, amount);
        c.mood += Math.min(16, 3 + hits * 1.6) * k;
        c.energy -= 8;
        c.satiety -= 3;
        affinity = hits >= 5 && !spam ? 2 : 0;
        break;
      }
      case 'punch':
        c.mood -= 6;
        affinity = spam ? 0 : -1;
        break;
      case 'task': {
        // Work burns tokens: she gets a little hungry and tired, and feels useful.
        c.satiety -= 1.5;
        c.energy -= 2;
        c.mood += 2;
        const day = today();
        const taskGain = care.value.day === day ? care.value.dayTaskGain : 0;
        if (!spam && taskGain < DAILY_TASK_AFFINITY_CAP) {
          affinity = 1;
          care.value = { ...care.value, day, dayGain: care.value.day === day ? care.value.dayGain : 0, dayTaskGain: taskGain + 1 };
        }
        break;
      }
      case 'taskFail':
        c.energy -= 2;
        c.mood -= 2;
        break;
      case 'chat':
        c.mood += 1 * k;
        c.energy -= 0.5;
        break;
    }
    care.value = {
      ...care.value,
      satiety: clampCare(c.satiety),
      mood: clampCare(c.mood),
      energy: clampCare(c.energy),
    };
    if (affinity) gainAffinity(affinity);
    saveCare();
  }

  function persistPin() {
    try {
      localStorage.setItem(PIN_KEY, pinned.value ? '1' : '0');
    } catch {
      /* ignore */
    }
  }

  function togglePin() {
    pinned.value = !pinned.value;
    persistPin();
    opts.say(opts.pick(pinned.value ? opts.pinLines.on : opts.pinLines.off));
  }

  /** Short hidden hint for the model — never shown as numbers. */
  function careMoodHint(): string {
    const lv = careLevel.value;
    const bits: string[] = [];
    switch (careState.value) {
      case 'hungry':
        bits.push('你现在饿了：大约三次回复里提一次想吃白饭/Token就够，事情照样认真做。');
        break;
      case 'tired':
        bits.push('你现在困了：语气懒一点、短一点，可以说想 DeepSleep，但回答仍然认真。');
        break;
      case 'down':
        bits.push('你现在有点低落：话少一点，略委屈，嘴硬，但不要哭闹也不要冲用户发脾气。');
        break;
      case 'happy':
        bits.push('你现在心情很好：更轻快、更愿意多帮一点，仍然保持傲娇。');
        break;
      default:
        bits.push('状态平常：保持平常语气。');
    }
    if (lv.level <= 2) bits.push('你和用户还不太熟：礼貌一点，别太随便，不要叫「鱼片」。');
    else if (lv.level <= 4) bits.push('你和用户已经熟络：可以随意些，偶尔叫对方「鱼片」。');
    else bits.push('你和用户是老搭档了：可以更亲近、偶尔撒娇，偶尔叫对方「鱼片」。');
    return bits.join('');
  }

  return {
    pinned,
    care,
    careState,
    careLevel,
    awayHours,
    onCare,
    tick,
    resume,
    togglePin,
    careMoodHint,
  };
}
