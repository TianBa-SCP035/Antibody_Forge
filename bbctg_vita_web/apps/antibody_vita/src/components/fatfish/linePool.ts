/**
 * Model-written reaction lines (pet-proxy /api/pet/lines), mixed with the fixed ones in lines.ts.
 * Fetched in the background a few times an hour, never while the user waits; the fixed lines stay the fallback.
 */

/** Must match LINE_KINDS in pet-proxy/chat.py. */
export type FreshKind = 'poke' | 'flurry' | 'punch' | 'pet' | 'feed' | 'idle';

const FRESH_SHARE = 0.4;
const REFRESH_MS = 45 * 60_000;
/** A mood change may refresh early, but not more often than this. */
const MIN_GAP_MS = 10 * 60_000;

const pool: Partial<Record<FreshKind, string[]>> = {};
let fetchedAt = 0;
let inFlight = false;

export async function refreshLines(ctx: { careMood: string; ambient: string }, moodChanged = false) {
  if (inFlight || Date.now() - fetchedAt < (moodChanged ? MIN_GAP_MS : REFRESH_MS)) return;
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
      for (const [kind, lines] of Object.entries(data.lines)) {
        if (Array.isArray(lines)) pool[kind as FreshKind] = lines.map(String);
      }
      filled = true;
    }
  } catch {
    /* offline: fixed lines only */
  } finally {
    inFlight = false;
    // A failed fetch retries after the short gap instead of waiting a full refresh period.
    if (!filled) fetchedAt = Date.now() - REFRESH_MS + MIN_GAP_MS;
  }
}

/** A fresh line some of the time (each used once), otherwise one of the fixed lines. */
export function lineFor(kind: FreshKind, fixed: readonly string[]): string {
  const fresh = pool[kind];
  if (fresh?.length && Math.random() < FRESH_SHARE) {
    return fresh.splice(Math.floor(Math.random() * fresh.length), 1)[0]!;
  }
  return fixed[Math.floor(Math.random() * fixed.length)]!;
}
