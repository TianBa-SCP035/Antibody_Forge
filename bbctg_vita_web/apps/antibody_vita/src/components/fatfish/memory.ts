/**
 * 基于 localStorage 的记忆：近期原文（只发当前这段对话）加长期摘要。
 * 离开原文窗口的记录按时间并入摘要，mergedAt 记到哪条为止，同一条不重复压缩。
 */

import {
  COMPRESS_BATCH,
  MEMORY_MERGED_AT_KEY,
  MEMORY_SUMMARY_KEY,
  MEMORY_SUMMARY_MAX,
  QA_KEY,
  QA_KEEP,
  RECENT_HISTORY_SEND,
  SESSION_GAP_MS,
} from './constants';
import { currentUserKey } from './session';

/** at 为记录时间（毫秒）。 */
export type QaItem = { id: number; role: 'user' | 'pet'; text: string; at: number };
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

export function loadMergedAt(): number {
  try {
    return Number(readScoped(MEMORY_MERGED_AT_KEY)) || 0;
  } catch {
    return 0;
  }
}

export function saveMergedAt(at: number) {
  try {
    writeScoped(MEMORY_MERGED_AT_KEY, String(at));
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
        at: Number(x.at) || 0,
      }));
  } catch {
    return [];
  }
}

export function saveQa(history: QaItem[]) {
  try {
    writeScoped(
      QA_KEY,
      JSON.stringify(history.slice(-QA_KEEP).map(({ role, text, at }) => ({ role, text, at }))),
    );
  } catch {
    /* 存储不可用时保留内存状态。 */
  }
}

/**
 * 原文发送窗口的起点：只取当前这段对话（相邻两句间隔都小于 SESSION_GAP_MS）的最近几条。
 * 隔了一阵再来时不带旧原文，模型会沿用自己旧回复的口吻和错误；之前的内容靠摘要承接。
 */
function windowStart(items: QaItem[], now: number): number {
  let start = items.length;
  let next = now;
  while (start > 0 && next - items[start - 1]!.at < SESSION_GAP_MS) {
    start -= 1;
    next = items[start]!.at;
  }
  return Math.max(start, items.length - RECENT_HISTORY_SEND);
}

/** 将界面 qaHistory 映射为 API recentHistory，排除本次问题。 */
export function toRecentHistory(history: QaItem[], current: string, now = Date.now()): ChatHistoryItem[] {
  const last = history[history.length - 1];
  const prior = last?.role === 'user' && last.text === current.trim() ? history.slice(0, -1) : history;
  return prior.slice(windowStart(prior, now)).map((h) => ({
    role: h.role === 'pet' ? 'assistant' : 'user',
    content: h.text,
  }));
}

/** 已不在原文窗口里、也还没并入摘要的记录。 */
export function pendingForCompress(history: QaItem[], mergedAt: number, now = Date.now()): QaItem[] {
  return history.slice(0, windowStart(history, now)).filter((h) => h.at > mergedAt);
}

/** 攒够一批，或这些记录所在的那段对话已经结束（下次开口就要用到）时压缩。 */
export function shouldCompress(pending: QaItem[], now = Date.now()): boolean {
  const newest = pending[pending.length - 1];
  return !!newest && (pending.length >= COMPRESS_BATCH || now - newest.at >= SESSION_GAP_MS);
}

/** 每条带上时间，压缩时把“下周三”这类说法换成具体日期。 */
export async function requestCompress(summary: string, pending: QaItem[], signal?: AbortSignal): Promise<string | null> {
  if (!pending.length) return null;
  const olderTurns = pending.map((h) => ({
    role: h.role === 'pet' ? 'assistant' : 'user',
    content: h.text.slice(0, 500),
    at: h.at,
  }));
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
