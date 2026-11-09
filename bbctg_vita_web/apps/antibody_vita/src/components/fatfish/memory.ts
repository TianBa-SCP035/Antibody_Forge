/** localStorage durable summary + recent Q&A helpers (Cursor-like memory). */

import {
  COMPRESS_EVERY_TURNS,
  MEMORY_SUMMARY_KEY,
  MEMORY_SUMMARY_MAX,
  MEMORY_TURNS_SINCE_COMPRESS_KEY,
  QA_KEY,
  QA_KEEP,
  RECENT_HISTORY_SEND,
} from './constants';
import { currentUserKey } from './session';

export type QaItem = { id: number; role: 'user' | 'pet'; text: string };
export type ChatHistoryItem = { role: 'user' | 'assistant'; content: string };

/**
 * Conversation memory belongs to the signed-in account; another login on this browser starts fresh.
 * Signed out (e.g. on the login page) nothing is read or written, so no one inherits that talk.
 */
function scoped(key: string): string | null {
  const user = currentUserKey();
  return user ? `${key}:${user}` : null;
}

/** Reads the account's copy; the old shared key (before per-account memory) moves to the first account that loads it. */
function readScoped(key: string): string | null {
  const own = scoped(key);
  if (!own) return null;
  const value = localStorage.getItem(own);
  if (value != null) return value;
  const legacy = localStorage.getItem(key);
  if (legacy != null) {
    localStorage.setItem(own, legacy);
    localStorage.removeItem(key);
  }
  return legacy;
}

function writeScoped(key: string, value: string) {
  const own = scoped(key);
  if (own) localStorage.setItem(own, value);
}

export { readScoped as readUserItem, writeScoped as writeUserItem };

export function loadMemorySummary(): string {
  try {
    return readScoped(MEMORY_SUMMARY_KEY) || '';
  } catch {
    return '';
  }
}

export function saveMemorySummary(summary: string) {
  try {
    writeScoped(MEMORY_SUMMARY_KEY, String(summary || '').slice(0, MEMORY_SUMMARY_MAX));
  } catch {
    /* ignore */
  }
}

export function loadTurnsSinceCompress(): number {
  try {
    const n = Number(readScoped(MEMORY_TURNS_SINCE_COMPRESS_KEY) || '0');
    return Number.isFinite(n) && n > 0 ? Math.floor(n) : 0;
  } catch {
    return 0;
  }
}

export function saveTurnsSinceCompress(n: number) {
  try {
    writeScoped(MEMORY_TURNS_SINCE_COMPRESS_KEY, String(Math.max(0, Math.floor(n))));
  } catch {
    /* ignore */
  }
}

export function loadQa(): QaItem[] {
  try {
    const raw = readScoped(QA_KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw);
    if (!Array.isArray(arr)) return [];
    return arr
      .filter((x) => x && (x.role === 'user' || x.role === 'pet') && x.text)
      .slice(-QA_KEEP)
      .map((x, i) => ({
        id: i + 1,
        role: x.role as 'user' | 'pet',
        text: String(x.text).slice(0, 1000),
      }));
  } catch {
    return [];
  }
}

export function saveQa(history: QaItem[]) {
  try {
    writeScoped(
      QA_KEY,
      JSON.stringify(history.slice(-QA_KEEP).map(({ role, text }) => ({ role, text }))),
    );
  } catch {
    /* ignore */
  }
}

/** Map UI qaHistory → API recentHistory (last N only), without the question being sent now. */
export function toRecentHistory(history: QaItem[], current: string, n = RECENT_HISTORY_SEND): ChatHistoryItem[] {
  const last = history[history.length - 1];
  const prior = last?.role === 'user' && last.text === current.trim() ? history.slice(0, -1) : history;
  return prior.slice(-n).map((h) => ({
    role: h.role === 'pet' ? 'assistant' : 'user',
    content: h.text,
  }));
}

export function shouldCompress(historyLen: number, turnsSince: number, summary: string): boolean {
  if (historyLen < COMPRESS_EVERY_TURNS) return false;
  if (!summary.trim() && historyLen >= COMPRESS_EVERY_TURNS) return true;
  return turnsSince >= COMPRESS_EVERY_TURNS;
}

/**
 * Turns older than the recent window, folded into the summary. With compression every
 * COMPRESS_EVERY_TURNS exchanges, a turn is folded in before it drops out of the QA_KEEP list.
 */
export function olderTurnsForCompress(history: QaItem[]): ChatHistoryItem[] {
  if (history.length <= RECENT_HISTORY_SEND) return [];
  return history.slice(0, -RECENT_HISTORY_SEND).map((h) => ({
    role: h.role === 'pet' ? 'assistant' : 'user',
    content: h.text.slice(0, 500),
  }));
}

export async function requestCompress(
  summary: string,
  olderTurns: ChatHistoryItem[],
  signal?: AbortSignal,
): Promise<string | null> {
  if (!olderTurns.length) return null;
  try {
    const res = await fetch('/api/pet/compress', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal,
      body: JSON.stringify({ summary, olderTurns }),
    });
    if (!res.ok) return null;
    const data = await res.json();
    const next = String(data?.summary || '').trim();
    return next || null;
  } catch {
    return null;
  }
}
