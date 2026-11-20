/**
 * 通过观察宿主页面发出的请求学习列表接口，使宠物无需模块专用代码即可读取整个模块的数据。
 *
 * 仅重放页面实际发出且响应形似列表的请求，并且只修改分页参数。含写操作词的路径不记录。
 * 鉴权请求头仅在内存中供重放使用，不持久化也不发送给模型。
 */

import { DATA_SOURCES_KEY } from './constants';
import { readUserItem, writeUserItem } from './memory';
import { isSensitiveName } from './pageContext';
import { readPageTables, type PageTable } from './pageTable';
import type { DataTable, Row } from './reportBuilder';
import { menuPages, openMenuPage, type MenuPage } from './session';

export type DataSource = {
  id: string;
  name: string;
  route: string;
  method: 'GET' | 'POST';
  /** 不含查询字符串的同源请求路径。 */
  path: string;
  /** 已观察到的最宽请求和最新请求中的非分页查询或正文参数。 */
  baseParams: Record<string, unknown>;
  lastParams: Record<string, unknown>;
  pageKey?: string;
  /** 页面发送的首页页码；部分后端从 0 开始。 */
  pageBase?: 0 | 1;
  sizeKey?: string;
  itemsPath: string[];
  totalPath?: string[];
  /** 响应字段到页面列名的映射，通过值匹配；未匹配字段保留原键。 */
  labels: Record<string, string>;
  /** 模型为无页面列名的字段生成的表头，每字段仅询问一次；labels 优先，无法命名时映射到字段自身。 */
  guessed?: Record<string, string>;
  /** 代码字段到“原始值→页面文本”的映射，如 status 的 1 映射为「进行中」；未展示过的代码保留原值。 */
  values?: Record<string, Record<string, string>>;
  fields: string[];
  total?: number;
  seenAt: number;
  /** 曾匹配真实行的关联，供后续跨模块问题复用关联键。 */
  joins?: VerifiedJoin[];
};

/** countedOn 主数据源的 rows 行中，有 matched 行找到关联项。 */
export type VerifiedJoin = { with: string; on: string; withOn: string; matched: number; rows: number; countedOn: string; at: number };
const MAX_JOINS_PER_SOURCE = 5;

const MAX_SOURCES = 40;
const MAX_RESPONSE_CHARS = 8_000_000;
export const MAX_SOURCE_ROWS = 5000;
const REPLAY_PAGE_SIZE = 500;

/** 表示请求可能修改数据或并非列表的路径词；命中后绝不学习该请求。 */
const WRITE_WORDS = new Set(
  ('update delete del remove save create add insert import upload submit batch set copy move sync approve audit confirm send ' +
    'start stop reset auto export download login logout refresh token password apply cancel bind unbind publish execute run ' +
    'edit modify change generate assign allocate archive restore transfer notify push lock unlock revoke reject enable disable ' +
    'finish complete commit merge clear init calc compute put patch upsert destroy').split(' '),
);
/** POST 默认不视为只读，仅在路径同时含读取语义时学习。 */
const READ_WORDS = new Set(
  'list lists page query search find get select catalog options tree records stat stats statistics summary overview detail details count lookup'.split(' '),
);

/** 将 `/serum/auto_update_status`、`/user/resetPassword` 拆为独立小写词。 */
function pathWords(path: string): string[] {
  return path.split(/[/_\-.]+|(?=[A-Z])/).map((w) => w.toLowerCase());
}

function replayable(method: string, path: string): boolean {
  const words = pathWords(path);
  if (words.some((w) => WRITE_WORDS.has(w))) return false;
  return method === 'GET' || words.some((w) => READ_WORDS.has(w));
}

/**
 * 只读查询：宠物自己的接口、不带用户身份的外站请求（统计、CDN），或路径语义是查询的请求。其余都可能改数据。
 * 外站请求带着 Cookie 或 Authorization 就是以用户身份调用（接口在另一个域名的系统很常见），和同源一样判断。
 */
export function isQueryRequest(method: string, rawUrl: string, asUser = true): boolean {
  let url: URL;
  try {
    url = new URL(rawUrl, location.href);
  } catch {
    return false;
  }
  if (url.pathname.startsWith('/api/pet/')) return true;
  if (url.origin !== location.origin && !asUser) return true;
  const m = method.toUpperCase();
  return m === 'HEAD' || m === 'OPTIONS' || replayable(m, url.pathname);
}

function fetchAsUser(input: RequestInfo | URL, init?: RequestInit): boolean {
  const req = input instanceof Request ? input : null;
  const credentials = init?.credentials ?? req?.credentials;
  try {
    return credentials === 'include' || new Headers(init?.headers ?? req?.headers).has('authorization');
  } catch {
    return true;
  }
}

/** onResult 由持有方挂上；放行的请求完成后带着状态码和响应开头回调。 */
export type HeldRequest = { method: string; url: string; body: unknown; onResult?: (status: number, text: string) => void };
type WriteHold = (req: HeldRequest) => Promise<boolean>;
let writeHold: WriteHold | null = null;

/** 设置后，页面发出的每个请求先交给它；返回 false 的请求不发出（页面收到中止）。 */
export function setWriteHold(fn: WriteHold | null) {
  writeHold = fn;
}

/** 页面自己发出、还没返回的请求数（不含宠物自己的 /api/pet/）；操作后据此等页面加载完。 */
let inflight = 0;
export function pendingRequests() {
  return inflight;
}
const ownRequest = (url: string) => /\/api\/pet\//.test(url);
const PAGE_KEYS = ['page', 'pageNum', 'pageNo', 'page_no', 'pageIndex', 'page_index', 'current'];
const SIZE_KEYS = ['limit', 'pageSize', 'page_size', 'size', 'per_page', 'perPage'];
const ITEM_KEYS = ['items', 'list', 'records', 'rows', 'data', 'results', 'content'];
const TOTAL_KEYS = ['total', 'count', 'totalCount', 'total_count', 'totalElements', 'totalRecords'];

let installed = false;
let authHeaders: Record<string, string> = {};
type SeenResponse = { items: any[]; route: string; params: Record<string, unknown>; total?: number };
const lastResponse = new Map<string, SeenResponse>();
let sources: DataSource[] | null = null;

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return !!v && typeof v === 'object' && !Array.isArray(v);
}

function load(): DataSource[] {
  if (sources) return sources;
  try {
    const arr = JSON.parse(readUserItem(DATA_SOURCES_KEY) || '[]');
    sources = Array.isArray(arr) ? arr : [];
  } catch {
    sources = [];
  }
  return sources;
}

function persist() {
  try {
    writeUserItem(DATA_SOURCES_KEY, JSON.stringify(load().slice(0, MAX_SOURCES)));
  } catch {
    /* 存储配额不足时仅保留内存副本。 */
  }
}

/** 账号切换时清空内存副本，使下次读取加载新账号的数据源。 */
export function reloadSources() {
  sources = null;
  lastResponse.clear();
  authHeaders = {};
}

function getPath(obj: any, path: string[]): any {
  return path.reduce((o, k) => (o == null ? undefined : o[k]), obj);
}

/** 在 JSON 响应中查找行数组及同级总数，如 `{code:0,data:{items:[…],total:9}}`。 */
function findList(json: any): { itemsPath: string[]; totalPath?: string[] } | null {
  const rowsLike = (v: unknown) => Array.isArray(v) && v.length > 0 && v.slice(0, 5).every(isPlainObject);
  if (rowsLike(json)) return { itemsPath: [] };
  const queue: Array<{ obj: any; path: string[] }> = [{ obj: json, path: [] }];
  while (queue.length) {
    const { obj, path } = queue.shift()!;
    if (!isPlainObject(obj) || path.length > 3) continue;
    const keys = Object.keys(obj).sort((a, b) => Number(!ITEM_KEYS.includes(a)) - Number(!ITEM_KEYS.includes(b)));
    for (const k of keys) {
      if (rowsLike(obj[k])) {
        const t = TOTAL_KEYS.find((tk) => typeof obj[tk] === 'number');
        return { itemsPath: [...path, k], totalPath: t ? [...path, t] : undefined };
      }
    }
    for (const k of keys) if (isPlainObject(obj[k])) queue.push({ obj: obj[k], path: [...path, k] });
  }
  return null;
}

function nonEmptyCount(params: Record<string, unknown>) {
  return Object.values(params).filter((v) => v != null && v !== '' && !(Array.isArray(v) && !v.length)).length;
}

function splitParams(params: Record<string, unknown>) {
  const pageKey = PAGE_KEYS.find((k) => k in params);
  const sizeKey = SIZE_KEYS.find((k) => k in params);
  const rest = { ...params };
  if (pageKey) delete rest[pageKey];
  if (sizeKey) delete rest[sizeKey];
  return { pageKey, sizeKey, rest };
}

function record(method: string, rawUrl: string, body: unknown, responseText: string) {
  const m = method.toUpperCase();
  if (m !== 'GET' && m !== 'POST') return;
  let url: URL;
  try {
    url = new URL(rawUrl, location.href);
  } catch {
    return;
  }
  if (url.origin !== location.origin || !replayable(m, url.pathname) || url.pathname.startsWith('/api/pet/')) return;
  if (!responseText || responseText.length > MAX_RESPONSE_CHARS || !/^\s*[[{]/.test(responseText)) return;
  let json: any;
  try {
    json = JSON.parse(responseText);
  } catch {
    return;
  }
  if (isPlainObject(json) && 'code' in json && json.code !== 0 && json.code !== 200) return;
  const known = load().find((s) => s.method === m && s.path === url.pathname);
  // 已知数据源的空结果仍代表页面当前筛选状态，例如结果为 0 行的标签页。
  const found =
    findList(json) ??
    (known && Array.isArray(getPath(json, known.itemsPath)) ? { itemsPath: known.itemsPath, totalPath: known.totalPath } : null);
  if (!found) return;
  let params: Record<string, unknown> = {};
  if (m === 'GET') params = Object.fromEntries(url.searchParams.entries());
  else if (typeof body === 'string') {
    try {
      const parsed = JSON.parse(body);
      if (!isPlainObject(parsed)) return;
      params = parsed;
    } catch {
      return;
    }
  } else if (body != null) return;
  const { pageKey, sizeKey, rest } = splitParams(params);
  const items = getPath(json, found.itemsPath) as any[];
  const total = found.totalPath ? Number(getPath(json, found.totalPath)) : undefined;
  const key = `${m} ${url.pathname}`;
  lastResponse.set(key, { items, route: location.pathname, params: rest, total });

  const list = load();
  let src = known;
  // 其他页面可能为下拉框调用同一列表接口；这类调用只能提供更宽请求，不能改写归属页面的筛选或总数。
  const home = !src || src.route === location.pathname;
  if (!src) {
    src = {
      id: `s${Math.max(0, ...list.map((s) => Number(s.id.slice(1)) || 0)) + 1}`,
      name: document.title.split(/\s+-\s+/)[0]?.trim() || url.pathname,
      route: location.pathname,
      method: m,
      path: url.pathname,
      baseParams: rest,
      lastParams: rest,
      itemsPath: found.itemsPath,
      labels: {},
      fields: [],
      seenAt: Date.now(),
    };
    list.unshift(src);
  }
  if (items.length) {
    src.fields = [...new Set(items.slice(0, 20).flatMap((it) => Object.keys(it || {})))]
      .filter((k) => !isSensitiveName(k) && items.slice(0, 20).some((it) => !isPlainObject(it?.[k])))
      .slice(0, 80);
  }
  const broadest = home ? nonEmptyCount(rest) <= nonEmptyCount(src.baseParams) : nonEmptyCount(rest) < nonEmptyCount(src.baseParams);
  if (broadest) {
    src.baseParams = rest;
    if (Number.isFinite(total)) src.total = total;
  }
  if (home) {
    src.lastParams = rest;
    src.pageKey = pageKey;
    const pageNo = pageKey ? Number(params[pageKey]) : NaN;
    if (pageNo === 0 || pageNo === 1) src.pageBase = pageNo;
    src.sizeKey = sizeKey;
    src.itemsPath = found.itemsPath;
    src.totalPath = found.totalPath;
    src.seenAt = Date.now();
  }
  sources = [src, ...list.filter((s) => s !== src)].slice(0, MAX_SOURCES);
  persist();
  scheduleTableMatch();
}

let matchTimer: ReturnType<typeof setTimeout> | undefined;

/** 页面渲染行后，将表格与响应配对，以便在访问时学习列名。 */
function scheduleTableMatch() {
  clearTimeout(matchTimer);
  matchTimer = setTimeout(() => {
    try {
      for (const t of readPageTables()) sourceForTable(t);
    } catch {
      /* 匹配失败不得影响页面。 */
    }
  }, 1200);
}

const RESULT_HEAD = 400;

function responseHead(xhr: XMLHttpRequest): string {
  try {
    if (xhr.responseType === '' || xhr.responseType === 'text') return xhr.responseText.slice(0, RESULT_HEAD);
    if (xhr.responseType === 'json' && xhr.response) return JSON.stringify(xhr.response).slice(0, RESULT_HEAD);
  } catch {
    /* 读不到响应就只报状态码。 */
  }
  return '';
}

/**
 * 仅修补一次 XHR 和 fetch 以观察响应，不改变请求或响应。
 * 唯一的例外是 setWriteHold：宠物操作页面期间，可能改数据的请求要等用户放行才发出。
 */
export function installApiWatch() {
  if (installed || typeof window === 'undefined') return;
  installed = true;
  const P = XMLHttpRequest.prototype;
  const open = P.open;
  const send = P.send;
  const setHeader = P.setRequestHeader;
  P.open = function (this: any, method: string, url: string | URL, ...rest: any[]) {
    this.__ffReq = { method, url: String(url), headers: {} as Record<string, string> };
    this.__ffOpen = (this.__ffOpen ?? 0) + 1;
    return (open as any).call(this, method, url, ...rest);
  } as typeof P.open;
  P.setRequestHeader = function (this: any, name: string, value: string) {
    if (this.__ffReq && /^(authorization|accept-language|x-[\w-]+)$/i.test(name)) this.__ffReq.headers[name] = value;
    return setHeader.call(this, name, value);
  };
  P.send = function (this: any, body?: any) {
    const req = this.__ffReq;
    if (req) {
      this.addEventListener('loadend', () => {
        try {
          if (Object.keys(req.headers).length) authHeaders = { ...authHeaders, ...req.headers };
          if (this.status !== 200) return;
          const text =
            this.responseType === '' || this.responseType === 'text'
              ? this.responseText
              : this.responseType === 'json' && this.response
                ? JSON.stringify(this.response)
                : '';
          record(req.method, req.url, body, text);
        } catch {
          /* 观察逻辑不得影响页面。 */
        }
      }, { once: true });
    }
    const counted = !req || !ownRequest(req.url);
    const go = () => {
      if (counted) {
        inflight += 1;
        this.addEventListener('loadend', () => (inflight = Math.max(0, inflight - 1)), { once: true });
      }
      return send.call(this, body);
    };
    const hold = writeHold;
    const asUser = !!this.withCredentials || Object.keys(req?.headers ?? {}).some((h) => /^authorization$/i.test(h));
    if (hold && req && !isQueryRequest(req.method, req.url, asUser)) {
      // 还没 send 时 abort() 不触发任何事件，页面会一直等，所以自己派发中止。
      const refuse = () => {
        this.dispatchEvent(new ProgressEvent('abort'));
        this.dispatchEvent(new ProgressEvent('loadend'));
      };
      const held: HeldRequest = { method: req.method, url: req.url, body };
      const opened = this.__ffOpen;
      void hold(held).then((ok) => {
        if (!ok) return refuse();
        // 等确认期间页面可能已经 abort 并拿这个 XHR 发了别的请求，那这次就不该再发。
        if (this.__ffOpen !== opened || this.readyState !== XMLHttpRequest.OPENED) return;
        this.addEventListener('loadend', () => held.onResult?.(this.status, responseHead(this)), { once: true });
        try {
          go();
        } catch {
          refuse();
        }
      }, refuse);
      return;
    }
    return go();
  };
  const origFetch = window.fetch;
  window.fetch = async function (input: RequestInfo | URL, init?: RequestInit) {
    const url = typeof input === 'string' || input instanceof URL ? String(input) : input.url;
    const method = init?.method || (input instanceof Request ? input.method : 'GET');
    const hold = writeHold;
    let held: HeldRequest | null = null;
    if (hold && !isQueryRequest(method, url, fetchAsUser(input, init))) {
      held = { method, url, body: init?.body };
      if (!(await hold(held).catch(() => false))) throw new DOMException('用户拦下了这次提交', 'AbortError');
    }
    const counted = !ownRequest(url);
    if (counted) inflight += 1;
    let res: Response;
    try {
      res = await origFetch.call(window, input, init);
    } catch (err) {
      held?.onResult?.(0, String((err as Error)?.message || err));
      throw err;
    } finally {
      if (counted) inflight = Math.max(0, inflight - 1);
    }
    if (held?.onResult) {
      const report = held.onResult;
      void res
        .clone()
        .text()
        .then((t) => report(res.status, t.slice(0, RESULT_HEAD)))
        .catch(() => report(res.status, ''));
    }
    try {
      if (res.ok && /json/i.test(res.headers.get('content-type') || '') && !(init as any)?.__ffReplay) {
        void res
          .clone()
          .text()
          .then((t) => record(method, url, init?.body, t))
          .catch(() => {});
      }
    } catch {
      /* 观察失败不得影响页面请求。 */
    }
    return res;
  };
  holdFormSubmits();
}

/** 原生表单提交整页跳转、不经过 XHR/fetch：页面自己没拦下（单页应用一般会拦）时同样先暂停。 */
function holdFormSubmits() {
  if (typeof HTMLFormElement === 'undefined') return;
  const nativeSubmit = HTMLFormElement.prototype.submit;
  const approved = new WeakSet<HTMLFormElement>();
  const held = (form: HTMLFormElement, submitter?: HTMLElement | null): boolean => {
    const hold = writeHold;
    const method = (submitter?.getAttribute('formmethod') || form.getAttribute('method') || 'GET').toUpperCase();
    const url = submitter?.getAttribute('formaction') || form.action;
    if (!hold || isQueryRequest(method, url)) return false;
    let body: URLSearchParams | undefined;
    try {
      body = new URLSearchParams([...new FormData(form)].map(([k, v]) => [k, typeof v === 'string' ? v : '[文件]']));
    } catch {
      /* 读不到内容也照样暂停。 */
    }
    void hold({ method, url, body }).then(
      (ok) => {
        if (!ok) return;
        if (submitter && typeof form.requestSubmit === 'function') {
          // requestSubmit 同步派发 submit；校验没过就不派发，标记不能留到下一次提交。
          approved.add(form);
          try {
            form.requestSubmit(submitter);
          } finally {
            approved.delete(form);
          }
        } else {
          nativeSubmit.call(form);
        }
      },
      () => {},
    );
    return true;
  };
  window.addEventListener('submit', (e) => {
    const form = e.target as HTMLFormElement;
    if (approved.has(form) || e.defaultPrevented) return;
    if (held(form, (e as SubmitEvent).submitter)) e.preventDefault();
  });
  HTMLFormElement.prototype.submit = function (this: HTMLFormElement) {
    if (!held(this)) nativeSubmit.call(this);
  };
}

function norm(v: unknown): string {
  if (v == null) return '';
  if (Array.isArray(v)) return v.map(norm).filter(Boolean).join(',');
  return String(v).replace(/[\s,，、;；]+/g, ',').replace(/^,|,$/g, '').trim().toLowerCase();
}

/** 返回 2 表示值相同，1 表示一方是另一方的长前缀（单元格被截断），0 表示不同。 */
function sameValue(a: string, b: string): number {
  if (!a || !b) return 0;
  if (a === b) return 2;
  const na = Number(a);
  const nb = Number(b);
  if (Number.isFinite(na) && Number.isFinite(nb) && na === nb) return 2;
  return a.length >= 8 && b.length >= 8 && (a.startsWith(b) || b.startsWith(a)) ? 1 : 0;
}

/** 页面用于表示空值的文本。 */
const EMPTY_TEXT = /^(-+|—+|\/|无|暂无|n\/a)$/;
const MAX_CODE_LEN = 32;
const MAX_CODES_PER_FIELD = 60;
const MAX_CODE_FIELDS = 20;

function codeOf(v: unknown): string | null {
  if (typeof v === 'number') return Number.isFinite(v) ? String(v) : null;
  if (typeof v === 'boolean') return String(v);
  if (typeof v !== 'string') return null;
  const s = v.trim();
  return s && s.length <= MAX_CODE_LEN ? s : null;
}

/**
 * 识别页面已翻译的枚举类字段，如 status 的 1 显示为「进行中」。
 * 原始值与列文本必须在至少 4 行中一一对应且存在重复，避免把唯一的 id 与名称列误认成代码表。
 */
function matchCodes(items: any[], table: PageTable, n: number, keys: string[], labels: string[]) {
  const out: Array<{ key: string; label: string; map: Record<string, string>; rows: number }> = [];
  for (const label of labels) {
    for (const key of keys) {
      const fwd = new Map<string, string>();
      const back = new Map<string, string>();
      let rows = 0;
      let ok = true;
      for (let i = 0; i < n && ok; i += 1) {
        const text = String(table.rows[i]![label] ?? '').trim();
        const raw = items[i]?.[key];
        // 空值在页面显示为「-」或空白，没有可学习的代码。
        if (raw == null || raw === '') continue;
        const code = codeOf(raw);
        if (!text || code == null || text === '***') {
          ok = false;
          break;
        }
        rows += 1;
        if ((fwd.get(code) ?? text) !== text || (back.get(text) ?? code) !== code) ok = false;
        fwd.set(code, text);
        back.set(text, code);
      }
      if (!ok || rows < 4 || fwd.size < 2 || fwd.size > rows / 2) continue;
      // 页面仅以不同格式显示原值时，不视为翻译映射。
      if ([...fwd].every(([c, t]) => norm(c) === norm(t))) continue;
      out.push({ key, label, map: Object.fromEntries(fwd), rows });
    }
  }
  return out.sort((a, b) => b.rows - a.rows);
}

/** 逐行比较值，将页面列与响应字段配对，无需读取框架内部状态。 */
function matchLabels(items: any[], table: PageTable): { labels: Record<string, string>; values: Record<string, Record<string, string>> } {
  const n = Math.min(items.length, table.rows.length, 30);
  if (!n) return { labels: {}, values: {} };
  const keys = [...new Set(items.slice(0, n).flatMap((it) => Object.keys(it || {})))];
  const scored: Array<{ key: string; label: string; score: number }> = [];
  for (const label of table.columns) {
    for (const key of keys) {
      let both = 0;
      let hit = 0;
      let exact = 0;
      for (let i = 0; i < n; i += 1) {
        const a = norm(table.rows[i]![label]);
        const b = norm(items[i]?.[key]);
        if (!b && (!a || EMPTY_TEXT.test(a))) continue;
        both += 1;
        const s = sameValue(a, b);
        if (s) hit += 1;
        if (s === 2) exact += 1;
      }
      // 精确匹配优先于前缀匹配，例如「25D285601」应匹配 project_code，而非「25D28560101」的 experiment_id。
      if (both && hit >= 1 && hit / both >= 0.8) scored.push({ key, label, score: exact * 2 + hit + hit / both });
    }
  }
  scored.sort((x, y) => y.score - x.score);
  const out: Record<string, string> = {};
  const usedLabels = new Set<string>();
  for (const s of scored) {
    if (s.key in out || usedLabels.has(s.label)) continue;
    out[s.key] = s.label;
    usedLabels.add(s.label);
  }
  const values: Record<string, Record<string, string>> = {};
  const freeKeys = keys.filter((k) => !(k in out) && !isSensitiveName(k));
  const freeLabels = table.columns.filter((l) => !usedLabels.has(l) && !isSensitiveName(l));
  for (const c of matchCodes(items, table, n, freeKeys, freeLabels)) {
    if (c.key in out || usedLabels.has(c.label)) continue;
    out[c.key] = c.label;
    usedLabels.add(c.label);
    values[c.key] = c.map;
  }
  return { labels: out, values };
}

/**
 * 查找当前页面表格背后的已学习数据源；其最新响应行必须与表格展示一致。
 * 同时刷新字段到列名的映射和数据源名称。
 */
export function sourceForTable(table: PageTable): DataSource | null {
  let best: { src: DataSource } & ReturnType<typeof matchLabels> | null = null;
  let bestResp: SeenResponse | undefined;
  for (const src of load()) {
    const resp = lastResponse.get(`${src.method} ${src.path}`);
    if (!resp?.items.length || resp.route !== location.pathname) continue;
    const m = matchLabels(resp.items, table);
    const matched = Object.keys(m.labels).length;
    if (matched >= Math.min(2, table.columns.length) && (!best || matched > Object.keys(best.labels).length)) {
      best = { src, ...m };
      bestResp = resp;
    }
  }
  if (!best || !bestResp) return null;
  const src = best.src;
  // 用户实际看到的表格决定接口归属页面；该接口可能最初只作为其他页面的下拉数据源被观察到。
  if (src.route !== location.pathname) {
    src.route = location.pathname;
    src.labels = {};
    src.values = {};
  }
  src.lastParams = bestResp.params;
  // 每个列名只对应一个字段，新匹配会从旧的错误字段接管该列名。
  const merged = { ...src.labels };
  const values = { ...src.values };
  for (const [key, label] of Object.entries(best.labels)) {
    for (const k of Object.keys(merged)) {
      if (merged[k] === label && k !== key) {
        delete merged[k];
        delete values[k];
      }
    }
    merged[key] = label;
    // 代码映射跨访问累积；普通值匹配出现后，终止该字段的代码映射。
    const learned = best.values[key];
    if (learned) values[key] = Object.fromEntries(Object.entries({ ...values[key], ...learned }).slice(-MAX_CODES_PER_FIELD));
    else delete values[key];
  }
  src.labels = merged;
  src.values = Object.fromEntries(Object.entries(values).slice(0, MAX_CODE_FIELDS));
  if (table.title && !src.name.includes(table.title)) {
    const page = document.title.split(/\s+-\s+/)[0]?.trim();
    src.name = page && page !== table.title ? `${page} · ${table.title}` : table.title;
  }
  persist();
  return src;
}

/**
 * 含行的响应未必是数据模块，也可能是菜单、选项或配置。
 * 只有存在分页、报告总数，或响应行与用户看到的表格一致时才计为模块。
 */
function isModule(s: DataSource) {
  const rowKey = s.itemsPath[s.itemsPath.length - 1] || '';
  return !!s.pageKey || (!!s.totalPath && ITEM_KEYS.includes(rowKey)) || Object.keys(s.labels).length >= 2;
}

export function listSources(): DataSource[] {
  return load().filter(isModule);
}

/** 页面最近发送的筛选条件，对应 scope=page_filters，例如并非列值的状态标签页。 */
export function pageFilterText(src: DataSource): string {
  return paramText(src.lastParams);
}

/** 最宽请求仍携带的筛选条件；scope=all 表示满足这些条件的全部数据，并非整张表。 */
export function allScopeFilterText(src: DataSource): string {
  return paramText(src.baseParams);
}

function paramText(params: Record<string, unknown>): string {
  return Object.entries(params)
    .filter(([, v]) => v != null && v !== '' && v !== false && !(Array.isArray(v) && !v.length))
    .map(([k, v]) => `${k}=${typeof v === 'object' ? JSON.stringify(v) : String(v)}`)
    .join('&')
    .slice(0, 160);
}

/**
 * 在涉及的每个已学习数据源上记录成功匹配行的关联；内置 projects 不记录。
 * leftRef 和 rightRef 是 build_report 收到的数据源 ID、projects 或 page_table。
 */
export function rememberJoin(leftRef: string, rightRef: string, leftOn: string, rightOn: string, matched: number, rows: number) {
  if (!matched) return;
  const left = leftRef === 'page_table' ? undefined : findSource(leftRef);
  const right = rightRef === 'page_table' ? undefined : findSource(rightRef);
  const leftId = left?.id ?? (leftRef === 'projects' ? 'projects' : '');
  const rightId = right?.id ?? (rightRef === 'projects' ? 'projects' : '');
  if (!leftId || !rightId) return;
  const put = (src: DataSource | undefined, entry: VerifiedJoin) => {
    if (!src) return;
    const rest = (src.joins || []).filter((j) => !(j.with === entry.with && j.on === entry.on && j.withOn === entry.withOn));
    src.joins = [entry, ...rest].slice(0, MAX_JOINS_PER_SOURCE);
  };
  const at = Date.now();
  put(left, { with: rightId, on: leftOn, withOn: rightOn, matched, rows, countedOn: leftId, at });
  put(right, { with: leftId, on: rightOn, withOn: leftOn, matched, rows, countedOn: leftId, at });
  persist();
}

/** `s5 按 实验ID=实验编号（本表 1903 行里 831 行对上）` */
export function joinText(src: DataSource): string {
  return (src.joins || [])
    .map((j) => `${j.with} 按 ${j.on}=${j.withOn}（${j.countedOn === src.id ? '本表' : j.countedOn} ${j.rows} 行里 ${j.matched} 行对上）`)
    .join('；');
}

/**
 * 为模型上下文按行描述每个已学习数据源，随后列出尚未打开的菜单页面。
 */
export function describeSources(limit = 20): string {
  const unopened = unopenedPages()
    .slice(0, 30)
    .map((p) => p.title)
    .join('、');
  const learned = listSources()
    .slice(0, limit)
    .map((s) => {
      const cols = sourceColumns(s).slice(0, 12).join('、');
      const filters = pageFilterText(s);
      const allFilters = allScopeFilterText(s);
      const joins = joinText(s);
      return (
        `${s.id} ${s.name}（${s.route}${s.total != null ? `，${s.total}条` : ''}${s.route === location.pathname ? '，当前页' : ''}）` +
        `${allFilters ? ` 全量也带着：${allFilters}` : ''}${filters ? ` 页面筛选：${filters}` : ''}${cols ? ` 列：${cols}` : ''}` +
        `${joins ? ` 验证过的关联：${joins}` : ''}`
      );
    });
  return [...learned, unopened ? `还没打开过的页面：${unopened}` : ''].filter(Boolean).join('\n');
}

/** 宠物尚未观察到列表请求的菜单页面；打开页面后才能学习。 */
export function unopenedPages(): MenuPage[] {
  const learned = new Set(listSources().map((s) => s.route));
  return menuPages().filter((p) => !learned.has(p.path) && p.path !== location.pathname);
}

/**
 * 用户在卡片中同意后打开菜单页面，并等待学习该页面自己的列表请求。
 * 页面加载过程与用户点击菜单一致，不代替页面额外发起请求。
 */
export async function openAndLearn(path: string, timeoutMs = 12_000): Promise<DataSource | null> {
  if (!(await openMenuPage(path))) return null;
  const until = Date.now() + timeoutMs;
  while (Date.now() < until) {
    const src = listSources().find((s) => s.route === path);
    if (src) return src;
    await new Promise((r) => setTimeout(r, 400));
  }
  return null;
}

export function findSource(ref: string): DataSource | undefined {
  const r = ref.trim();
  const list = listSources();
  return list.find((s) => s.id === r) || list.find((s) => s.name === r) || list.find((s) => s.name.includes(r) || s.route === r);
}

function headerOf(src: DataSource, key: string): string {
  if (src.labels[key]) return src.labels[key]!;
  const guess = src.guessed?.[key];
  // 后学习的页面列可能占用同名表头，两个字段不得共享一个表头。
  return guess && !Object.values(src.labels).includes(guess) ? guess : key;
}

/** 模型可用的列名依次采用页面标签、模型生成表头和原始键。 */
export function sourceColumns(src: DataSource): string[] {
  const fields = src.fields || [];
  return [...new Set([...fields.filter((k) => k in src.labels), ...fields.filter((k) => !(k in src.labels))].map((k) => headerOf(src, k)))];
}

/** 页面未命名的字段由模型为每个数据源生成一次表头，失败时保留原始键。 */
async function guessHeaders(src: DataSource, items: any[], signal?: AbortSignal) {
  const sample = items.slice(0, 50);
  const keys = [...new Set(sample.flatMap((it) => Object.keys(it || {})))]
    .filter((k) => !(k in src.labels) && !(k in (src.guessed || {})) && !isSensitiveName(k))
    .filter((k) => sample.some((it) => flatten(it?.[k]) != null))
    .slice(0, 80);
  if (!keys.length) return;
  const fields = keys.map((key) => ({
    key,
    samples: [...new Set(sample.map((it) => flatten(it?.[key])).filter((v) => v != null && v !== ''))].slice(0, 3),
  }));
  try {
    const res = await window.fetch('/api/pet/labels', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal,
      body: JSON.stringify({ source: src.name, fields }),
    });
    const data = res.ok ? await res.json() : null;
    if (!data?.ok) return;
    const taken = new Set(Object.values(src.labels));
    const guessed = { ...src.guessed };
    for (const key of keys) {
      const label = String(data.labels?.[key] || '').trim();
      guessed[key] = label && !taken.has(label) && !isSensitiveName(label) ? label : key;
      taken.add(guessed[key]);
    }
    src.guessed = guessed;
    persist();
  } catch (err) {
    if ((err as any)?.name === 'AbortError') throw err;
  }
}

function flatten(v: unknown): string | number | null {
  if (v == null) return null;
  if (typeof v === 'number') return Number.isFinite(v) ? v : null;
  if (typeof v === 'boolean') return v ? '是' : '否';
  if (Array.isArray(v)) return v.map((x) => (isPlainObject(x) ? '' : String(x))).filter(Boolean).join(',') || null;
  if (isPlainObject(v)) return null;
  return String(v).slice(0, 500);
}

function toTable(src: DataSource, items: any[]): DataTable {
  // 凭据和联系方式字段必须彻底移除，不得进入模型或文件。
  const keys = [...new Set(items.slice(0, 50).flatMap((it) => Object.keys(it || {})))].filter(
    (k) => items.slice(0, 50).some((it) => !isPlainObject(it?.[k])) && !isSensitiveName(k) && !isSensitiveName(src.labels[k] || ''),
  );
  const ordered = [...keys.filter((k) => k in src.labels), ...keys.filter((k) => !(k in src.labels))].slice(0, 60);
  const header = new Map(ordered.map((k) => [k, headerOf(src, k)]));
  const colOf = (k: string) => header.get(k)!;
  const cell = (k: string, v: unknown) => {
    const code = src.values?.[k] ? codeOf(v) : null;
    return (code != null && src.values![k]![code]) || flatten(v);
  };
  return {
    columns: ordered.map(colOf),
    rows: items.map((it) => Object.fromEntries(ordered.map((k) => [colOf(k), cell(k, it?.[k])])) as Row),
    aliases: Object.fromEntries(ordered.filter((k) => colOf(k) !== k).map((k) => [k, colOf(k)])),
  };
}

export type FetchResult = { table: DataTable; total?: number; fetched: number; truncated: boolean; scope: 'page_filters' | 'all' };

/**
 * 逐页重放已学习请求。scope=page_filters 保留页面最近的筛选，scope=all 使用已观察到的最宽请求。
 * 除分页参数外不修改任何内容。
 */
export async function fetchSource(
  src: DataSource,
  scope: FetchResult['scope'],
  signal?: AbortSignal,
  maxRows = MAX_SOURCE_ROWS,
): Promise<FetchResult> {
  if (!replayable(src.method, src.path)) throw new Error('这个接口看起来不是只读查询，不重放');
  if (!Object.keys(authHeaders).length) throw new Error('还没看到页面发过请求，刷新或点一下页面再试');
  const params = { ...(scope === 'all' ? src.baseParams : src.lastParams) };
  const rows: any[] = [];
  let total: number | undefined;
  const size = src.sizeKey ? REPLAY_PAGE_SIZE : 0;
  const base = src.pageBase ?? 1;
  // 后端可能将每页数量限制在请求值以下，因此以第一页实际返回量为准。
  let pageSize = 0;
  let firstOfLast = '';
  // 看到了最后一页（或无法再翻）；页数或行数到上限退出时没看到，就不能说取全了。
  let ended = false;
  // 最多 60 页可覆盖每页 100 行时的 5000 行上限。
  for (let page = 0; rows.length < maxRows && page < 60; page += 1) {
    const p: Record<string, unknown> = { ...params };
    if (src.pageKey) p[src.pageKey] = base + page;
    if (src.sizeKey) p[src.sizeKey] = size;
    let url = src.path;
    const init: RequestInit & { __ffReplay?: boolean } = {
      method: src.method,
      headers: { ...authHeaders, Accept: 'application/json' },
      credentials: 'same-origin',
      signal,
      __ffReplay: true,
    };
    if (src.method === 'GET') {
      const qs = new URLSearchParams(Object.entries(p).map(([k, v]) => [k, v == null ? '' : String(v)]));
      url = `${src.path}?${qs}`;
    } else {
      (init.headers as Record<string, string>)['Content-Type'] = 'application/json';
      init.body = JSON.stringify(p);
    }
    const res = await window.fetch(url, init);
    if (res.status === 401 || res.status === 403) throw Object.assign(new Error('forbidden'), { status: res.status });
    if (!res.ok) throw new Error(`请求失败 ${res.status}`);
    const json = await res.json();
    if (isPlainObject(json) && 'code' in json && json.code !== 0 && json.code !== 200) {
      throw new Error(String(json.message || json.msg || `业务错误 ${json.code}`).slice(0, 80));
    }
    const batch = getPath(json, src.itemsPath);
    if (!Array.isArray(batch)) {
      ended = true;
      break;
    }
    if (src.totalPath) {
      const t = Number(getPath(json, src.totalPath));
      if (Number.isFinite(t)) total = t;
    }
    // 后端忽略页码并重复返回第一页时停止，避免复制重复数据。
    const first = JSON.stringify(batch[0] ?? null);
    if (page > 0 && first === firstOfLast) {
      ended = true;
      break;
    }
    firstOfLast = first;
    rows.push(...batch);
    if (!pageSize) pageSize = batch.length;
    if (!src.pageKey || !batch.length || (total != null ? rows.length >= total : batch.length < pageSize)) {
      ended = true;
      break;
    }
  }
  const kept = rows.slice(0, maxRows);
  await guessHeaders(src, kept, signal);
  return {
    table: toTable(src, kept),
    total,
    fetched: kept.length,
    truncated: total != null ? total > kept.length : rows.length > maxRows || !ended,
    scope,
  };
}
