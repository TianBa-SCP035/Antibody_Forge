/**
 * Model-written lines (pet-proxy /api/pet/lines), mixed with the fixed ones in lines.ts.
 * Fetched in the background a few times an hour, never while the user waits; the fixed lines stay the fallback.
 * The pool is kept per account across reloads, so the next morning's greeting can be a fresh one too.
 */

import { LINE_POOL_KEY } from './constants';
import { readUserItem, writeUserItem } from './memory';

/** Must match LINE_KINDS in pet-proxy/chat.py. */
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

/** Rare scenes (once or twice a day) mostly get a fresh line; the fixed greetings carry usage hints, so they keep half. */
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
/** Kinds the model may write with the weather of the moment: dropped once that is old. */
const DATED: ReadonlySet<FreshKind> = new Set(['idle', 'lunch', 'offWork', 'lateNight']);
const DATED_TTL_MS = 2 * 3600_000;
const KEEP_TTL_MS = 24 * 3600_000;
const REFRESH_MS = 45 * 60_000;
/** A mood change may refresh early, but not more often than this. */
const MIN_GAP_MS = 10 * 60_000;

let pool: Partial<Record<FreshKind, string[]>> | null = null;
/** When the lines in `pool` were written. */
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
    /* fixed lines only */
  }
  return pool;
}

/** Account switch: the next read loads that account's pool. */
export function reloadLines() {
  pool = null;
  writtenAt = 0;
  fetchedAt = 0;
}

function persist() {
  try {
    writeUserItem(LINE_POOL_KEY, JSON.stringify({ at: writtenAt, lines: pool }));
  } catch {
    /* quota: keep in memory */
  }
}

/** Resolves true when a new batch replaced the pool. `moodChanged` (or newly known weather) allows the shorter gap. */
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
    /* offline: fixed lines only */
  } finally {
    inFlight = false;
    // A failed fetch retries after the short gap instead of waiting a full refresh period.
    if (!filled) fetchedAt = Date.now() - REFRESH_MS + MIN_GAP_MS;
  }
  return filled;
}

/** A fresh line some of the time (each used once, also across reloads), otherwise one of the fixed lines. */
export function lineFor(kind: FreshKind, fixed: readonly string[]): string {
  const fresh = load()[kind];
  if (fresh?.length && Math.random() < (FRESH_SHARE[kind] ?? DEFAULT_SHARE)) {
    const line = fresh.splice(Math.floor(Math.random() * fresh.length), 1)[0]!;
    persist();
    return line;
  }
  return fixed[Math.floor(Math.random() * fixed.length)]!;
}
