/**
 * 将模型生成的台词（pet-proxy /api/pet/lines）与 lines.ts 固定台词混用。
 * 每小时后台获取数次，用户等待期间不请求，固定台词始终作为降级方案。
 * 台词池按账号跨刷新保存，使次日问候也可使用新台词。
 */

import { LINE_POOL_KEY } from './constants';
import { readUserItem, writeUserItem } from './memory';

/** 必须与 pet-proxy/chat.py 中的 LINE_KINDS 一致。 */
export type FreshKind =
  | 'poke'
  | 'flurry'
  | 'punch'
  | 'pet'
  | 'feed'
  | 'idle'
  | 'greet'
  | 'morning'
  | 'welcomeBack'
  | 'lunch'
  | 'offWork'
  | 'lateNight'
  | 'saved';

/** 每天仅出现一两次的场景优先使用新台词；固定问候含使用提示，因此仍保留一半概率。 */
const FRESH_SHARE: Partial<Record<FreshKind, number>> = {
  greet: 0.5,
  morning: 0.7,
  welcomeBack: 0.7,
  lunch: 0.7,
  offWork: 0.7,
  lateNight: 0.7,
  saved: 0.7,
};
const DEFAULT_SHARE = 0.4;
/** 可能包含即时天气的台词类型，过期后丢弃。 */
const DATED: ReadonlySet<FreshKind> = new Set(['idle', 'lunch', 'offWork', 'lateNight']);
const DATED_TTL_MS = 2 * 3600_000;
const KEEP_TTL_MS = 24 * 3600_000;
const REFRESH_MS = 45 * 60_000;
/** 心情变化可提前刷新，但间隔不得短于此值。 */
const MIN_GAP_MS = 10 * 60_000;

let pool: Partial<Record<FreshKind, string[]>> | null = null;
/** pool 中台词的生成时间。 */
let writtenAt = 0;
let fetchedAt = 0;
let inFlight = false;

function load(): Partial<Record<FreshKind, string[]>> {
  if (pool) return pool;
  pool = {};
  try {
    const saved = JSON.parse(readUserItem(LINE_POOL_KEY) || 'null');
    const age = Date.now() - Number(saved?.at);
    if (saved?.lines && age >= 0 && age < KEEP_TTL_MS) {
      for (const [kind, lines] of Object.entries(saved.lines)) {
        if (Array.isArray(lines) && !(age >= DATED_TTL_MS && DATED.has(kind as FreshKind))) {
          pool[kind as FreshKind] = lines.map(String);
        }
      }
      writtenAt = Number(saved.at);
      fetchedAt = writtenAt;
    }
  } catch {
    /* 读取失败时仅使用固定台词。 */
  }
  return pool;
}

/** 账号切换后，下次读取加载对应账号的台词池。 */
export function reloadLines() {
  pool = null;
  writtenAt = 0;
  fetchedAt = 0;
}

function persist() {
  try {
    writeUserItem(LINE_POOL_KEY, JSON.stringify({ at: writtenAt, lines: pool }));
  } catch {
    /* 存储配额不足时仅保留内存副本。 */
  }
}

/** 新批次替换台词池时返回 true；心情变化或刚获得天气时允许使用较短间隔。 */
export async function refreshLines(ctx: { careMood: string; ambient: string }, moodChanged = false): Promise<boolean> {
  load();
  if (inFlight || Date.now() - fetchedAt < (moodChanged ? MIN_GAP_MS : REFRESH_MS)) return false;
  inFlight = true;
  fetchedAt = Date.now();
  let filled = false;
  try {
    const res = await fetch('/api/pet/lines', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(ctx),
    });
    const data = res.ok ? await res.json().catch(() => null) : null;
    if (data?.ok && data.lines) {
      const next: Partial<Record<FreshKind, string[]>> = {};
      for (const [kind, lines] of Object.entries(data.lines)) {
        if (Array.isArray(lines)) next[kind as FreshKind] = lines.map(String);
      }
      pool = next;
      writtenAt = Date.now();
      persist();
      filled = true;
    }
  } catch {
    /* 离线时仅使用固定台词。 */
  } finally {
    inFlight = false;
    // 请求失败后按短间隔重试，不等待完整刷新周期。
    if (!filled) fetchedAt = Date.now() - REFRESH_MS + MIN_GAP_MS;
  }
  return filled;
}

/** 按概率使用一条未用过的新台词，否则使用固定台词；新台词的已用状态跨刷新保留。 */
export function lineFor(kind: FreshKind, fixed: readonly string[]): string {
  const fresh = load()[kind];
  if (fresh?.length && Math.random() < (FRESH_SHARE[kind] ?? DEFAULT_SHARE)) {
    const line = fresh.splice(Math.floor(Math.random() * fresh.length), 1)[0]!;
    persist();
    return line;
  }
  return fixed[Math.floor(Math.random() * fixed.length)]!;
}
