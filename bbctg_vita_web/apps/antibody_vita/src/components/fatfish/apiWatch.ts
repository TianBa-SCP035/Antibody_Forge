/**
 * Learns the host app's list endpoints by watching the requests its own pages send, so the pet can pull a
 * whole module's data without per-module code.
 *
 * Only requests a page itself made are ever replayed, only when the response looked like a list, and only
 * the paging parameters are changed. Paths with write-like words are never recorded. Auth headers are
 * reused in memory for the replay and never stored or sent to the model.
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
  /** Same-origin request path without query string. */
  path: string;
  /** Non-paging query / body params of the broadest request seen (fewest filters) and of the latest one. */
  baseParams: Record<string, unknown>;
  lastParams: Record<string, unknown>;
  pageKey?: string;
  /** First page number the page sent (some backends count from 0). */
  pageBase?: 0 | 1;
  sizeKey?: string;
  itemsPath: string[];
  totalPath?: string[];
  /** Response field → column label on the page (matched by values); unmatched fields keep their key. */
  labels: Record<string, string>;
  fields: string[];
  total?: number;
  seenAt: number;
  /** Joins that matched real rows before, so the next cross-module question doesn't have to guess the key. */
  joins?: VerifiedJoin[];
};

/** `matched` of `rows` rows in `countedOn` (the main source of that report) found a partner. */
export type VerifiedJoin = { with: string; on: string; withOn: string; matched: number; rows: number; countedOn: string; at: number };
const MAX_JOINS_PER_SOURCE = 5;

const MAX_SOURCES = 40;
const MAX_RESPONSE_CHARS = 8_000_000;
export const MAX_SOURCE_ROWS = 5000;
const REPLAY_PAGE_SIZE = 500;

/** Words in a path that suggest a request changes data (or isn't a list); such requests are never learned. */
const WRITE_WORDS = new Set(
  ('update delete del remove save create add insert import upload submit batch set copy move sync approve audit confirm send ' +
    'start stop reset auto export download login logout refresh token password apply cancel bind unbind publish execute run ' +
    'edit modify change generate assign allocate archive restore transfer notify push lock unlock revoke reject enable disable ' +
    'finish complete commit merge clear init calc compute put patch upsert destroy').split(' '),
);
/** POST isn't read-only by convention, so a POST is only learned when its path also says it reads. */
const READ_WORDS = new Set(
  'list lists page query search find get select catalog options tree records stat stats statistics summary overview detail details count lookup'.split(' '),
);

/** `/serum/auto_update_status`, `/user/resetPassword` → individual lower-case words. */
function pathWords(path: string): string[] {
  return path.split(/[/_\-.]+|(?=[A-Z])/).map((w) => w.toLowerCase());
}

function replayable(method: string, path: string): boolean {
  const words = pathWords(path);
  if (words.some((w) => WRITE_WORDS.has(w))) return false;
  return method === 'GET' || words.some((w) => READ_WORDS.has(w));
}
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
    /* quota: keep in memory */
  }
}

/** Account switch: forget the in-memory copy so the next read loads the new account's sources. */
export function reloadSources() {
  sources = null;
  lastResponse.clear();
  authHeaders = {};
}

function getPath(obj: any, path: string[]): any {
  return path.reduce((o, k) => (o == null ? undefined : o[k]), obj);
}

/** Finds the row array (and a sibling total) in a JSON response, e.g. `{code:0,data:{items:[…],total:9}}`. */
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
  // An empty result is still the page's current filter for a source we already know (a tab with 0 rows).
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
  // Other pages call the same list API for dropdowns etc.; those calls must not rewrite the owning page's
  // filters or total, only offer a broader request.
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

/** Once the page has rendered the rows, pair its tables with the responses so column names are learned on visit. */
function scheduleTableMatch() {
  clearTimeout(matchTimer);
  matchTimer = setTimeout(() => {
    try {
      for (const t of readPageTables()) sourceForTable(t);
    } catch {
      /* best effort */
    }
  }, 1200);
}

/** Patches XHR and fetch once to observe responses; never changes requests or responses. */
export function installApiWatch() {
  if (installed || typeof window === 'undefined') return;
  installed = true;
  const P = XMLHttpRequest.prototype;
  const open = P.open;
  const send = P.send;
  const setHeader = P.setRequestHeader;
  P.open = function (this: any, method: string, url: string | URL, ...rest: any[]) {
    this.__ffReq = { method, url: String(url), headers: {} as Record<string, string> };
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
          /* observing must never break the page */
        }
      });
    }
    return send.call(this, body);
  };
  const origFetch = window.fetch;
  window.fetch = async function (input: RequestInfo | URL, init?: RequestInit) {
    const res = await origFetch.call(window, input, init);
    try {
      const url = typeof input === 'string' || input instanceof URL ? String(input) : input.url;
      const method = init?.method || (input instanceof Request ? input.method : 'GET');
      if (res.ok && /json/i.test(res.headers.get('content-type') || '') && !(init as any)?.__ffReplay) {
        void res
          .clone()
          .text()
          .then((t) => record(method, url, init?.body, t))
          .catch(() => {});
      }
    } catch {
      /* ignore */
    }
    return res;
  };
}

function norm(v: unknown): string {
  if (v == null) return '';
  if (Array.isArray(v)) return v.map(norm).filter(Boolean).join(',');
  return String(v).replace(/[\s,，、;；]+/g, ',').replace(/^,|,$/g, '').trim().toLowerCase();
}

/** 2 = same value, 1 = one is a long prefix of the other (a cut-off cell), 0 = different. */
function sameValue(a: string, b: string): number {
  if (!a || !b) return 0;
  if (a === b) return 2;
  const na = Number(a);
  const nb = Number(b);
  if (Number.isFinite(na) && Number.isFinite(nb) && na === nb) return 2;
  return a.length >= 8 && b.length >= 8 && (a.startsWith(b) || b.startsWith(a)) ? 1 : 0;
}

/** Pairs page columns with response fields by comparing values row by row (no framework internals needed). */
function matchLabels(items: any[], table: PageTable): Record<string, string> {
  const n = Math.min(items.length, table.rows.length, 30);
  if (!n) return {};
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
        if (!a && !b) continue;
        both += 1;
        const s = sameValue(a, b);
        if (s) hit += 1;
        if (s === 2) exact += 1;
      }
      // Exact matches outrank prefix matches: "25D285601" is project_code, not experiment_id "25D28560101".
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
  return out;
}

/**
 * The learned source behind a table on the current page: its latest response rows must line up with what
 * the table shows. Also refreshes the field → label map and the source name.
 */
export function sourceForTable(table: PageTable): DataSource | null {
  let best: { src: DataSource; labels: Record<string, string> } | null = null;
  let bestResp: SeenResponse | undefined;
  for (const src of load()) {
    const resp = lastResponse.get(`${src.method} ${src.path}`);
    if (!resp?.items.length || resp.route !== location.pathname) continue;
    const labels = matchLabels(resp.items, table);
    const matched = Object.keys(labels).length;
    if (matched >= Math.min(2, table.columns.length) && (!best || matched > Object.keys(best.labels).length)) {
      best = { src, labels };
      bestResp = resp;
    }
  }
  if (!best || !bestResp) return null;
  // The table the user sees decides which page owns this API (it may first have been seen as a dropdown elsewhere).
  if (best.src.route !== location.pathname) {
    best.src.route = location.pathname;
    best.src.labels = {};
  }
  best.src.lastParams = bestResp.params;
  // One label per column name: a newer match takes the name over from an older (wrong) field.
  const merged = { ...best.src.labels };
  for (const [key, label] of Object.entries(best.labels)) {
    for (const k of Object.keys(merged)) if (merged[k] === label) delete merged[k];
    merged[key] = label;
  }
  best.src.labels = merged;
  if (table.title && !best.src.name.includes(table.title)) {
    const page = document.title.split(/\s+-\s+/)[0]?.trim();
    best.src.name = page && page !== table.title ? `${page} · ${table.title}` : table.title;
  }
  persist();
  return best.src;
}

/**
 * A response with rows isn't necessarily a data module (menus, options, config). Count it only when it pages,
 * reports a total, or its rows lined up with a table the user saw.
 */
function isModule(s: DataSource) {
  const rowKey = s.itemsPath[s.itemsPath.length - 1] || '';
  return !!s.pageKey || (!!s.totalPath && ITEM_KEYS.includes(rowKey)) || Object.keys(s.labels).length >= 2;
}

export function listSources(): DataSource[] {
  return load().filter(isModule);
}

/** Filters the page last sent (scope=page_filters), e.g. a status tab that isn't a column value. */
export function pageFilterText(src: DataSource): string {
  return paramText(src.lastParams);
}

/** Filters still present in the broadest request seen: scope=all is "everything with these", not the whole table. */
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
 * Records a join that matched rows, on every learned source involved (the built-in `projects` is not one).
 * `leftRef` / `rightRef` are what build_report was given: a source id, `projects` or `page_table`.
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
 * One line per learned source for the model's context, e.g. `s2 免疫工作台（/serum/workbench，277条，当前页）`,
 * then the menu pages not opened yet.
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

/** Menu pages whose list the pet hasn't seen yet: opening one is how she learns it. */
export function unopenedPages(): MenuPage[] {
  const learned = new Set(listSources().map((s) => s.route));
  return menuPages().filter((p) => !learned.has(p.path) && p.path !== location.pathname);
}

/**
 * Opens a menu page (after the user agreed on a card) and waits for its own list request to be learned.
 * The page loads exactly as if the user had clicked it in the menu; nothing is requested on its behalf.
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

/** Column names the model can use: page labels for matched fields, raw keys for the rest. */
export function sourceColumns(src: DataSource): string[] {
  const labeled = (src.fields || []).filter((k) => k in src.labels).map((k) => src.labels[k]!);
  return [...new Set([...labeled, ...(src.fields || []).filter((k) => !(k in src.labels))])];
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
  // Credential and contact fields are dropped entirely: they must not reach the model or the file.
  const keys = [...new Set(items.slice(0, 50).flatMap((it) => Object.keys(it || {})))].filter(
    (k) => items.slice(0, 50).some((it) => !isPlainObject(it?.[k])) && !isSensitiveName(k) && !isSensitiveName(src.labels[k] || ''),
  );
  const ordered = [...keys.filter((k) => k in src.labels), ...keys.filter((k) => !(k in src.labels))].slice(0, 60);
  const colOf = (k: string) => src.labels[k] || k;
  return {
    columns: ordered.map(colOf),
    rows: items.map((it) => Object.fromEntries(ordered.map((k) => [colOf(k), flatten(it?.[k])])) as Row),
  };
}

export type FetchResult = { table: DataTable; total?: number; fetched: number; truncated: boolean; scope: 'page_filters' | 'all' };

/**
 * Replays a learned request page by page. `scope`: `page_filters` keeps the filters the page last used,
 * `all` uses the broadest request seen. Nothing but the paging parameters is changed.
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
  // What the backend really returns per page: it may cap below what we ask for, so it's taken from page one.
  let pageSize = 0;
  let firstOfLast = '';
  // 60 pages still covers 5000 rows at 100 a page.
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
    if (!Array.isArray(batch)) break;
    if (src.totalPath) {
      const t = Number(getPath(json, src.totalPath));
      if (Number.isFinite(t)) total = t;
    }
    // A backend that ignores the page number returns page one again: stop instead of duplicating it.
    const first = JSON.stringify(batch[0] ?? null);
    if (page > 0 && first === firstOfLast) break;
    firstOfLast = first;
    rows.push(...batch);
    if (!pageSize) pageSize = batch.length;
    if (!src.pageKey || !batch.length || (total != null ? rows.length >= total : batch.length < pageSize)) break;
  }
  const kept = rows.slice(0, maxRows);
  return {
    table: toTable(src, kept),
    total,
    fetched: kept.length,
    truncated: total != null ? total > kept.length : rows.length > maxRows,
    scope,
  };
}
