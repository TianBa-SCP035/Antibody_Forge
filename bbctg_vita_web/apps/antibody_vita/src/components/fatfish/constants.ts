/** 大肥鱼共用的尺寸、资源路径和存储键。 */

/** 角色容器略窄于 224px 侧栏，内部精灵缩放为 0.8 并居中。 */
export const SIZE = 220;
export const SIDEBAR_WIDTH = 224;
/** 自由悬浮时的收起尺寸；靠近屏幕边缘时变成窄半胶囊。 */
export const BALL = 30;
export const CAP_PAD = 2;
export const CAP_H = BALL + CAP_PAD * 2; // 固定厚度为 34。
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
export const LINE_POOL_KEY = 'fatfish-line-pool';
/** 当前浏览器的节奏舞台最高分。 */
export const DISCO_BEST_KEY = 'fatfish-disco-best';
/** 戳击彩蛋触发后写入，宠物菜单随后直接显示「蹦迪」。 */
export const DISCO_UNLOCKED_KEY = 'fatfish-disco-unlocked';
/** 宠物观察到的列表接口，按账号隔离且不含令牌。 */
export const DATA_SOURCES_KEY = 'fatfish-data-sources';

/** 用于展示和本地问答列表的原始轮次上限。 */
export const QA_KEEP = 28;
/** 发送给模型的近期原始轮次上限；更早内容只发送摘要。 */
export const RECENT_HISTORY_SEND = 8;
/** 摘要更新后累积到此轮次时再次压缩。 */
export const COMPRESS_EVERY_TURNS = 8;
/** 与代理的 SUMMARY_MAX_CHARS 硬上限一致；压缩提示词以不超过 400 字为目标。 */
export const MEMORY_SUMMARY_MAX = 800;
