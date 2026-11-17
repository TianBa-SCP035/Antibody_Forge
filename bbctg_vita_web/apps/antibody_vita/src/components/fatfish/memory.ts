/** 基于 localStorage 的持久摘要和近期问答工具，采用摘要加近期记录的记忆方式。 */

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
 * 对话记忆归属当前登录账号，同一浏览器切换账号后使用独立记忆。
 * 未登录时不读写任何记忆，避免后续用户继承对话。
 */
function scoped(key: string): string | null {
  const user = currentUserKey();
  return user ? `${key}:${user}` : null;
}

/** 读取账号副本；旧的共享键会迁移给首个加载它的账号。 */
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
    /* 存储不可用时保留内存状态。 */
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
    /* 存储不可用时保留内存状态。 */
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
    /* 存储不可用时保留内存状态。 */
  }
}

/** 将界面 qaHistory 映射为 API recentHistory，仅保留最近 N 条并排除本次问题。 */
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
 * 返回近期窗口之外、需折叠进摘要的轮次。
 * 每 COMPRESS_EVERY_TURNS 次交流压缩一次，确保轮次移出 QA_KEEP 前已写入摘要。
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
