/** Shared geometry, asset bases, and storage keys for FatFish. */

/** On-screen character box (just under the 224px sidebar). Sprite inside is scaled to 0.80 and centered. */
export const SIZE = 220;
export const SIDEBAR_WIDTH = 224;
/** Free-floating collapsed size. Near a screen edge it becomes a slim half-capsule. */
export const BALL = 30;
export const CAP_PAD = 2;
export const CAP_H = BALL + CAP_PAD * 2; // 34, thickness stays
export const CAP_W = 64;
export const MAGNET_RANGE = 56;

export const BASE = `${import.meta.env.BASE_URL}fatfish/webm/`;
export const CURSOR_BASE = `${import.meta.env.BASE_URL}fatfish/cursors/`;
export const CURSOR_HOVER = `url(${CURSOR_BASE}cursor-hover.png) 7 3, pointer`;
export const CURSOR_GRABBING = `url(${CURSOR_BASE}cursor-grabbing.png) 12 12, grabbing`;
export const CURSOR_HAMMER = `url(${CURSOR_BASE}cursor-hammer.png) 9 5, pointer`;
export const BALL_IMG = `${import.meta.env.BASE_URL}fatfish/ball/whale-girl.png?v=3`;

export const PIN_KEY = 'fatfish-pinned';
export const CARE_KEY = 'fatfish-care';
export const QA_KEY = 'fatfish-qa';
export const MEMORY_SUMMARY_KEY = 'fatfish-memory-summary';
export const MEMORY_TURNS_SINCE_COMPRESS_KEY = 'fatfish-memory-turns-since-compress';
export const DAILY_REMARKS_KEY = 'fatfish-daily-remarks';
/** List endpoints the pet has seen pages call (per account; no tokens). */
export const DATA_SOURCES_KEY = 'fatfish-data-sources';

/** Raw turns kept for display / local QA list. */
export const QA_KEEP = 28;
/** Raw turns sent to the model (Cursor-like: summary + recent only). */
export const RECENT_HISTORY_SEND = 8;
/** Compress after this many new turns since last summary update. */
export const COMPRESS_EVERY_TURNS = 8;
/** Same hard cap as the proxy's SUMMARY_MAX_CHARS (the compress prompt aims for ≤400). */
export const MEMORY_SUMMARY_MAX = 800;
