/**
 * Custom summaries and Excel files from a flat table plus a model-written spec.
 *
 * The model only describes what it wants (filters, grouping, metrics, columns, sort); every count and
 * sum is computed here so the numbers in the answer and in the file are the same and exact.
 * No business imports: any source that can produce `DataTable` works.
 */

export type Cell = string | number | null;
export type Row = Record<string, Cell>;
export type DataTable = { columns: string[]; rows: Row[] };

export const CONDITION_OPS = ['=', '!=', 'contains', 'not_contains', '>', '>=', '<', '<=', 'empty', 'not_empty', 'in'] as const;
export const METRIC_OPS = ['count', 'pct', 'count_distinct', 'sum', 'avg', 'min', 'max'] as const;
export type Condition = { column: string; op: (typeof CONDITION_OPS)[number]; value?: string };
export type Metric = { op: (typeof METRIC_OPS)[number]; column?: string };
type SortKey = { column: string; desc?: boolean };

export type ReportSpec = {
  title?: string;
  where?: Condition[];
  group_by?: string[];
  metrics?: Metric[];
  columns?: string[];
  sort?: SortKey[];
  split_by?: string;
  limit?: number;
};

export type Sheet = { name: string; columns: string[]; rows: Cell[][] };
export type BuiltReport = { title: string; sheets: Sheet[]; matched: number; total: number };
export type BuildResult =
  | { ok: true; report: BuiltReport; groups?: Row[]; subtotals?: Row[]; countColumn?: string }
  | {
      ok: false;
      error: string;
      column?: string;
      available_columns?: string[];
      values_seen?: Array<[string, number]>;
      hint?: string;
    };

const MAX_GROUPS = 5000;
const MAX_SPLIT_SHEETS = 20;
const EMPTY = '(空)';

function str(v: Cell | undefined): string {
  return v == null ? '' : String(v).trim();
}

function squash(s: string) {
  return s.toLowerCase().replace(/[\s_\-·（）()]/g, '');
}

/** Exact, then case/space-insensitive, then a unique partial match ("负责" → "负责人"). */
export function resolveColumn(name: string, columns: string[]): string | null {
  const want = str(name);
  if (!want) return null;
  if (columns.includes(want)) return want;
  const sq = squash(want);
  const loose = columns.filter((c) => squash(c) === sq);
  if (loose.length === 1) return loose[0]!;
  // "靶点名称" may mean "靶点", but "实验ID" must not fall back to a bare "id" key.
  const partial = columns.filter((c) => squash(c).includes(sq) || (/[^\x00-\x7f]/.test(c) && sq.includes(squash(c))));
  return partial.length === 1 ? partial[0]! : null;
}

export function toNumber(v: Cell | undefined): number | null {
  if (typeof v === 'number') return Number.isFinite(v) ? v : null;
  const s = str(v).replace(/[,，\s]/g, '').replace(/%$/, '');
  // Leading zeros mean an ID ("0012"), not the number 12.
  if (!s || /^[-+]?0\d/.test(s)) return null;
  const pow = /^([-+]?\d+\.?\d*)?[x×*]?10\^([-+]?\d+)$/i.exec(s);
  if (pow) return Number(pow[1] ?? 1) * 10 ** Number(pow[2]);
  if (!/^[-+]?(\d+\.?\d*|\.\d+)(e[-+]?\d+)?$/i.test(s)) return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

const DATE_RE = /^(\d{4})\s*[-/.年]\s*(\d{1,2})\s*[-/.月]\s*(\d{1,2})\s*日?/;
// Epoch timestamps between 2000 and 2100, in milliseconds (13 digits) or seconds (10 digits).
const EPOCH_RE = /^(\d{13}|\d{10})$/;

/** `2026-9-5 08:00`, `2026年9月5日`, an epoch timestamp → `2026-09-05`; null for anything else or an impossible date. */
function dateKey(s: string): string | null {
  if (EPOCH_RE.test(s)) {
    const ms = Number(s) * (s.length === 10 ? 1000 : 1);
    if (ms < 946684800000 || ms > 4102444800000) return null;
    const d = new Date(ms);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  }
  const m = DATE_RE.exec(s);
  if (!m) return null;
  const [y, mo, d] = [Number(m[1]), Number(m[2]), Number(m[3])];
  const t = new Date(Date.UTC(y, mo - 1, d));
  if (t.getUTCMonth() !== mo - 1 || t.getUTCDate() !== d) return null;
  return `${m[1]}-${m[2]!.padStart(2, '0')}-${m[3]!.padStart(2, '0')}`;
}

/** Sort key keeping the time of day: `2026-9-28 8:00` → `2026-09-28 8:00`. */
function dateTimeKey(s: string): string | null {
  const d = dateKey(s);
  return d && !EPOCH_RE.test(s) ? `${d} ${s.replace(DATE_RE, '').trim()}`.trim() : d;
}

/** Equality for filters: case-insensitive text, numbers by value, a bare date matches any time on that day. */
function sameCell(s: string, want: string): boolean {
  if (s.toLowerCase() === want.toLowerCase()) return true;
  const ns = toNumber(s);
  const nw = toNumber(want);
  if (ns != null && nw != null) return ns === nw;
  const dw = want.length <= 10 ? dateKey(want) : null;
  return !!dw && dateKey(s) === dw;
}

/** Beijing wall-clock time as an ISO string, whatever the browser's time zone. */
export function beijingIso(offsetDays = 0): string {
  return new Date(Date.now() + 8 * 3600_000 + offsetDays * 86_400_000).toISOString();
}

function localDate(offsetDays = 0): string {
  return beijingIso(offsetDays).slice(0, 10);
}

/** `today`, `today-30`, `today+7` → YYYY-MM-DD, so "overdue" style filters don't need the model to know the date math. */
function expandValue(raw: string): string {
  const m = /^today\s*([+-]\s*\d+)?$/i.exec(raw.trim());
  return m ? localDate(m[1] ? Number(m[1].replace(/\s/g, '')) : 0) : raw.trim();
}

function compare(a: Cell | undefined, b: string): number | null {
  const sa = str(a);
  if (!sa) return null;
  const na = toNumber(a);
  const nb = toNumber(b);
  if (na != null && nb != null) return na - nb;
  // "N/A" or "待测" is not greater than 10: a number compares only with a number.
  if (nb != null) return null;
  const da = dateKey(sa);
  const db = b.length <= 10 ? dateKey(b) : null;
  if (da && db) return da.localeCompare(db);
  return sa.localeCompare(b, 'zh-CN', { numeric: true });
}

function matches(row: Row, c: Condition): boolean {
  const v = row[c.column];
  const s = str(v);
  const want = expandValue(c.value ?? '');
  switch (c.op) {
    case 'empty':
      return !s;
    case 'not_empty':
      return !!s;
    case '=':
      return sameCell(s, want);
    case '!=':
      return !sameCell(s, want);
    case 'contains':
      return s.toLowerCase().includes(want.toLowerCase());
    case 'not_contains':
      return !s.toLowerCase().includes(want.toLowerCase());
    case 'in':
      return want
        .split(/[,，、;；]/)
        .map((x) => x.trim())
        .filter(Boolean)
        .some((x) => sameCell(s, x));
    default: {
      const d = compare(v, want);
      if (d == null) return false;
      return c.op === '>' ? d > 0 : c.op === '>=' ? d >= 0 : c.op === '<' ? d < 0 : d <= 0;
    }
  }
}

function metricLabel(m: Metric): string {
  if (m.op === 'count') return '数量';
  if (m.op === 'pct') return m.column ? `${m.column}占比(%)` : '占比(%)';
  const col = m.column!;
  return { count_distinct: `${col}（去重数）`, sum: `${col}合计`, avg: `${col}平均`, min: `${col}最小`, max: `${col}最大` }[m.op];
}

function sumOf(rows: Row[], column: string): number {
  return rows.reduce((a, r) => a + (toNumber(r[column]) ?? 0), 0);
}

/** `all` = every matched row, the denominator for `pct`. */
function metricValue(m: Metric, rows: Row[], all: Row[]): Cell {
  if (m.op === 'count') return rows.length;
  if (m.op === 'pct') {
    const whole = m.column ? sumOf(all, m.column) : all.length;
    const part = m.column ? sumOf(rows, m.column) : rows.length;
    return whole ? Math.round((part / whole) * 1000) / 10 : null;
  }
  if (m.op === 'count_distinct') return new Set(rows.map((r) => str(r[m.column!])).filter(Boolean)).size;
  const nums = rows.map((r) => toNumber(r[m.column!])).filter((n): n is number => n != null);
  if (m.op === 'min' || m.op === 'max') {
    const texts = rows.map((r) => str(r[m.column!])).filter(Boolean);
    if (!texts.length) return null;
    if (nums.length === texts.length) return nums.reduce((a, b) => (m.op === 'min' ? Math.min(a, b) : Math.max(a, b)));
    // Dates (keeping the time of day) and other text: earliest / latest in natural order, as written.
    const keyed = texts
      .map((t) => ({ t, k: dateTimeKey(t) ?? t }))
      .sort((a, b) => a.k.localeCompare(b.k, 'zh-CN', { numeric: true }));
    return m.op === 'min' ? keyed[0]!.t : keyed[keyed.length - 1]!.t;
  }
  if (!nums.length) return null;
  const total = nums.reduce((a, b) => a + b, 0);
  // 12 significant digits drop float noise (0.1 + 0.2) without rounding small values away.
  if (m.op === 'sum') return Number(total.toPrecision(12));
  const avg = total / nums.length;
  return Math.abs(avg) >= 1 ? Math.round(avg * 100) / 100 : Number(avg.toPrecision(4));
}

function sortRows<T>(rows: T[], keys: Array<{ get: (r: T) => Cell | undefined; desc?: boolean }>): T[] {
  if (!keys.length) return rows;
  return [...rows].sort((a, b) => {
    for (const k of keys) {
      const va = k.get(a);
      const vb = k.get(b);
      const ea = !str(va);
      const eb = !str(vb);
      if (ea || eb) {
        if (ea !== eb) return ea ? 1 : -1;
        continue;
      }
      const na = toNumber(va);
      const nb = toNumber(vb);
      const d = na != null && nb != null ? na - nb : str(va).localeCompare(str(vb), 'zh-CN', { numeric: true });
      if (d) return k.desc ? -d : d;
    }
    return 0;
  });
}

const SHEET_BAD = /[\\/?*[\]:]/g;

function sheetName(raw: string, used: Set<string>): string {
  const base = (raw.replace(SHEET_BAD, ' ').trim() || 'Sheet').slice(0, 28);
  let name = base;
  // Excel compares sheet names case-insensitively.
  for (let i = 2; used.has(name.toLowerCase()); i += 1) name = `${base.slice(0, 25)}_${i}`;
  used.add(name.toLowerCase());
  return name;
}

function weekStart(d: string): string {
  const t = new Date(`${d}T00:00:00Z`);
  t.setUTCDate(t.getUTCDate() - ((t.getUTCDay() + 6) % 7));
  return t.toISOString().slice(0, 10);
}

const BUCKETS: Record<string, { label: string; key: (d: string) => string }> = {
  day: { label: '日', key: (d) => d },
  week: { label: '周，周一', key: weekStart },
  month: { label: '月', key: (d) => d.slice(0, 7) },
  quarter: { label: '季度', key: (d) => `${d.slice(0, 4)}-Q${Math.ceil(Number(d.slice(5, 7)) / 3)}` },
  year: { label: '年', key: (d) => d.slice(0, 4) },
};
const BUCKET_ALIASES: Record<string, string> = { 日: 'day', 天: 'day', 周: 'week', 月: 'month', 季: 'quarter', 季度: 'quarter', 年: 'year' };

/** `开始日期:month` style references become derived columns such as 「开始日期（月）」 holding `2026-11`. */
function deriveBuckets(table: DataTable, refs: string[]) {
  const rename = new Map<string, string>();
  const derived = new Set<string>();
  let { columns, rows } = table;
  for (const raw of refs) {
    const ref = str(raw);
    const m = /^(.+?)\s*[:：]\s*([a-z]+|[\u4e00-\u9fa5]+)$/i.exec(ref);
    if (!m || rename.has(ref) || table.columns.includes(ref)) continue;
    const unit = BUCKETS[m[2]!.toLowerCase()] ? m[2]!.toLowerCase() : BUCKET_ALIASES[m[2]!];
    const base = unit ? resolveColumn(m[1]!, table.columns) : null;
    if (!unit || !base) continue;
    const name = `${base}（${BUCKETS[unit]!.label}）`;
    rename.set(ref, name);
    if (derived.has(name)) continue;
    const key = BUCKETS[unit]!.key;
    columns = [...columns, name];
    rows = rows.map((r) => {
      const d = dateKey(str(r[base]));
      return { ...r, [name]: d ? key(d) : null };
    });
    derived.add(name);
  }
  return { table: { columns, rows }, rename, derived };
}

export function buildReport(input: DataTable, spec: ReportSpec): BuildResult {
  const refs = [
    ...(spec.where || []).map((c) => c.column),
    ...(spec.group_by || []),
    ...(spec.columns || []),
    ...(spec.sort || []).map((s) => s.column),
    ...(spec.metrics || []).map((m) => m.column || ''),
    spec.split_by || '',
  ];
  const { table, rename, derived } = deriveBuckets(input, refs);
  const cols = table.columns;
  const unknown = (column: string): BuildResult => ({
    ok: false,
    error: 'unknown_column',
    column,
    available_columns: cols,
  });
  const col = (name: string | undefined) => (name ? rename.get(str(name)) ?? resolveColumn(name, cols) : null);

  const where: Condition[] = [];
  for (const c of spec.where || []) {
    const name = col(c.column);
    if (!name) return unknown(c.column);
    if (!CONDITION_OPS.includes(c.op)) return { ok: false, error: `不支持的条件 ${c.op}，可用 ${CONDITION_OPS.join(' ')}` };
    if (c.op !== 'empty' && c.op !== 'not_empty' && !str(c.value as Cell)) {
      return { ok: false, error: `条件「${name} ${c.op}」没写 value（只有 empty / not_empty 可以不写）` };
    }
    where.push({ ...c, column: name });
  }
  const groupBy: string[] = [];
  for (const g of spec.group_by || []) {
    const name = col(g);
    if (!name) return unknown(g);
    if (!groupBy.includes(name)) groupBy.push(name);
  }
  const metrics: Metric[] = [];
  for (const m of spec.metrics || []) {
    if (!METRIC_OPS.includes(m.op)) return { ok: false, error: `不支持的统计 ${m.op}，可用 ${METRIC_OPS.join(' ')}` };
    if (m.op === 'count' || (m.op === 'pct' && !m.column)) {
      metrics.push({ op: m.op });
      continue;
    }
    const name = col(m.column);
    if (!name) return unknown(m.column || '(没写列)');
    metrics.push({ op: m.op, column: name });
  }
  if (groupBy.length && !metrics.some((m) => m.op === 'count')) metrics.unshift({ op: 'count' });
  const detailCols: string[] = [];
  for (const c of spec.columns || []) {
    const name = col(c);
    if (!name) return unknown(c);
    if (!detailCols.includes(name)) detailCols.push(name);
  }
  const split = spec.split_by ? col(spec.split_by) : null;
  if (spec.split_by && !split) return unknown(spec.split_by);

  // A metric title must not collide with a grouped column ("数量" as both), or the row object loses one.
  const labels: string[] = [];
  for (const m of metrics) {
    let label = metricLabel(m);
    while (groupBy.includes(label) || labels.includes(label)) label = `${label}（统计）`;
    labels.push(label);
  }
  const countLabel = labels[metrics.findIndex((m) => m.op === 'count')];
  const header = [...groupBy, ...labels];

  // Sort keys must resolve somewhere: summary headers when grouped, otherwise / also the data columns.
  const groupSort: Array<{ get: (r: Row) => Cell | undefined; desc?: boolean }> = [];
  const detailSort: Array<{ get: (r: Row) => Cell | undefined; desc?: boolean }> = [];
  for (const s of spec.sort || []) {
    const wantsCount = /^(count|计数|条数|个数|行数)$/i.test(str(s.column));
    const inHeader = groupBy.length ? (wantsCount && countLabel) || resolveColumn(rename.get(str(s.column)) ?? s.column, header) : null;
    const inCols = col(s.column);
    if (!inHeader && !inCols) {
      return { ok: false, error: 'unknown_sort_column', column: s.column, available_columns: groupBy.length ? [...header, ...cols] : cols };
    }
    if (inHeader) groupSort.push({ get: (r) => r[inHeader], desc: s.desc });
    if (inCols) detailSort.push({ get: (r) => r[inCols], desc: s.desc });
  }

  // An exclusion that removes nothing is almost always a misspelt value (已结题 vs 结题): fail loudly, not silently.
  for (const c of where) {
    if ((c.op === '!=' || c.op === 'not_contains') && table.rows.length && table.rows.every((r) => matches(r, c))) {
      return {
        ok: false,
        error: 'condition_no_effect',
        column: c.column,
        values_seen: columnValues(table, c.column),
        hint: `「${c.column} ${c.op} ${str(c.value as Cell)}」一行都没排除掉，这个值在列里不存在。照 values_seen 里的真实取值改了再调用`,
      };
    }
  }

  const matched = table.rows.filter((r) => where.every((c) => matches(r, c)));
  const sheets: Sheet[] = [];
  const used = new Set<string>();
  let groupRows: Row[] | undefined;
  let subtotals: Row[] | undefined;

  if (groupBy.length) {
    const buckets = new Map<string, { key: Cell[]; rows: Row[] }>();
    for (const r of matched) {
      const key = groupBy.map((g) => str(r[g]) || EMPTY);
      const k = JSON.stringify(key);
      const b = buckets.get(k) || { key, rows: [] };
      b.rows.push(r);
      buckets.set(k, b);
    }
    if (buckets.size > MAX_GROUPS) {
      return { ok: false, error: `分组后有 ${buckets.size} 组，太多了（上限 ${MAX_GROUPS}），换个分组列或先加筛选` };
    }
    const list = [...buckets.values()].map((b) => {
      const row: Row = {};
      groupBy.forEach((g, i) => (row[g] = b.key[i]!));
      metrics.forEach((m, i) => (row[labels[i]!] = metricValue(m, b.rows, matched)));
      return row;
    });
    // Time buckets read best in time order; other groups biggest first.
    const defaultSort = derived.has(groupBy[0]!)
      ? [{ get: (r: Row) => r[groupBy[0]!] }]
      : [{ get: (r: Row) => r[countLabel!], desc: true }];
    // The "(空)" group still sorts last, like an empty cell.
    const keys = (groupSort.length ? groupSort : defaultSort).map((k) => ({
      ...k,
      get: (r: Row) => {
        const v = k.get(r);
        return v === EMPTY ? null : v;
      },
    }));
    groupRows = sortRows(list, keys);
    if (groupBy.length > 1) {
      // Per first-column totals, so "which month had the most" doesn't need every (month × owner) group.
      const first = groupBy[0]!;
      const byFirst = new Map<Cell, Row[]>();
      for (const r of groupRows) if (!byFirst.has(r[first]!)) byFirst.set(r[first]!, []);
      for (const r of matched) byFirst.get(str(r[first]) || EMPTY)?.push(r);
      const sharePct = !metrics.some((m) => m.op === 'pct' && !m.column);
      subtotals = [...byFirst].map(([k, rows]) => {
        const row: Row = { [first]: k };
        metrics.forEach((m, i) => (row[labels[i]!] = metricValue(m, rows, matched)));
        if (sharePct) row['占比(%)'] = metricValue({ op: 'pct' }, rows, matched);
        return row;
      });
    }
    // With grouping, `limit` means "top N groups"; the 合计 row still covers every matched row.
    if (spec.limit && spec.limit > 0) groupRows = groupRows.slice(0, spec.limit);
    const out = groupRows.map((r) => header.map((h) => r[h] ?? null));
    out.push(['合计', ...groupBy.slice(1).map(() => ''), ...metrics.map((m) => metricValue(m, matched, matched))]);
    sheets.push({ name: sheetName('汇总', used), columns: header, rows: out });
  } else if (metrics.length) {
    // "金额合计是多少" with no grouping: one summary row over every matched row.
    const row: Row = {};
    metrics.forEach((m, i) => (row[labels[i]!] = metricValue(m, matched, matched)));
    groupRows = [row];
    sheets.push({ name: sheetName('汇总', used), columns: labels, rows: [labels.map((l) => row[l] ?? null)] });
  }

  const showCols = detailCols.length ? detailCols : cols;
  let detail = sortRows(matched, detailSort);
  if (!groupBy.length && spec.limit && spec.limit > 0) detail = detail.slice(0, spec.limit);
  const toCells = (rows: Row[]) => rows.map((r) => showCols.map((c) => r[c] ?? null));

  if (split) {
    const parts = new Map<string, Row[]>();
    for (const r of detail) {
      const k = str(r[split]) || EMPTY;
      parts.set(k, [...(parts.get(k) || []), r]);
    }
    if (parts.size > MAX_SPLIT_SHEETS) {
      return { ok: false, error: `按「${split}」分表会有 ${parts.size} 个工作表（上限 ${MAX_SPLIT_SHEETS}），换个列或用 group_by 汇总` };
    }
    for (const [k, rows] of parts) sheets.push({ name: sheetName(k, used), columns: showCols, rows: toCells(rows) });
  } else {
    sheets.push({ name: sheetName(groupBy.length ? '明细' : spec.title || '数据', used), columns: showCols, rows: toCells(detail) });
  }

  return {
    ok: true,
    report: { title: str(spec.title) || '整理结果', sheets, matched: matched.length, total: table.rows.length },
    groups: groupRows,
    subtotals,
    countColumn: countLabel,
  };
}

export const JOIN_HOWS = ['inner', 'left', 'anti', 'count'] as const;
export type JoinSpec = { how: (typeof JOIN_HOWS)[number]; leftOn: string; rightOn: string; rightName: string };
const MAX_JOINED_ROWS = 20000;

function distinctKeys(t: DataTable, c: string): Set<string> {
  const s = new Set<string>();
  for (const r of t.rows) {
    const v = str(r[c]).toLowerCase();
    if (v.length >= 2) s.add(v);
  }
  return s;
}

/**
 * Column pairs whose values actually overlap, ranked by how many distinct values they share,
 * so ID-like keys beat low-cardinality columns such as owner names.
 */
export function suggestKeys(left: DataTable, right: DataTable, top = 3) {
  const rightSets = right.columns.slice(0, 60).map((c) => [c, distinctKeys(right, c)] as const).filter(([, s]) => s.size > 1);
  const found: Array<{ lc: string; rc: string; rs: Set<string>; shared: number }> = [];
  for (const lc of left.columns.slice(0, 60)) {
    const ls = distinctKeys(left, lc);
    if (ls.size < 2) continue;
    for (const [rc, rs] of rightSets) {
      let shared = 0;
      for (const v of ls) if (rs.has(v)) shared += 1;
      if (shared >= 2) found.push({ lc, rc, rs, shared });
    }
  }
  return found
    .sort((a, b) => b.shared - a.shared)
    .slice(0, top)
    .map(({ lc, rc, rs, shared }) => ({
      left_on: lc,
      right_on: rc,
      shared_values: shared,
      left_rows_matched: left.rows.filter((r) => rs.has(str(r[lc]).toLowerCase())).length,
    }));
}

/** Most common values of a column, for telling the model what a filter could have matched. */
export function columnValues(table: DataTable, column: string, top = 15): Array<[string, number]> {
  const name = resolveColumn(column, table.columns);
  if (!name) return [];
  const counts = new Map<string, number>();
  for (const r of table.rows) {
    const v = str(r[name]) || EMPTY;
    counts.set(v, (counts.get(v) || 0) + 1);
  }
  return [...counts].sort((a, b) => b[1] - a[1]).slice(0, top);
}

/**
 * Joins two tables on one key column (trimmed, case-insensitive):
 * inner / left = one row per match (SQL semantics), anti = left rows with no match,
 * count = every left row plus a "<rightName>条数" column.
 */
export function joinTables(
  left: DataTable,
  right: DataTable,
  spec: JoinSpec,
): { ok: true; table: DataTable; matchedLeft: number } | ({ ok: false; error: string } & Record<string, unknown>) {
  const lk = resolveColumn(spec.leftOn, left.columns);
  if (!lk) return { ok: false, error: 'unknown_column', column: spec.leftOn, available_columns: left.columns };
  const rk = resolveColumn(spec.rightOn, right.columns);
  if (!rk) return { ok: false, error: 'unknown_column', column: spec.rightOn, available_columns: right.columns };
  if (!JOIN_HOWS.includes(spec.how)) return { ok: false, error: `join.how 只能是 ${JOIN_HOWS.join(' / ')}` };
  const keyOf = (v: Cell | undefined) => str(v).toLowerCase();
  const index = new Map<string, Row[]>();
  for (const r of right.rows) {
    const k = keyOf(r[rk]);
    if (k) index.set(k, [...(index.get(k) || []), r]);
  }
  const matchedLeft = left.rows.filter((r) => index.has(keyOf(r[lk]))).length;
  // Zero overlap almost always means the wrong key column; an anti join would silently return everything.
  if (!matchedLeft && left.rows.length && right.rows.length) {
    return {
      ok: false,
      error: 'no_match',
      left_on: lk,
      right_on: rk,
      left_key_samples: left.rows.slice(0, 5).map((r) => str(r[lk])),
      right_key_samples: right.rows.slice(0, 5).map((r) => str(r[rk])),
      suggested_keys: suggestKeys(left, right),
    };
  }
  if (spec.how === 'anti') {
    return { ok: true, table: { columns: left.columns, rows: left.rows.filter((r) => !index.has(keyOf(r[lk]))) }, matchedLeft };
  }
  if (spec.how === 'count') {
    let col = `${spec.rightName}条数`;
    while (left.columns.includes(col)) col = `${col}（关联）`;
    return {
      ok: true,
      table: { columns: [...left.columns, col], rows: left.rows.map((r) => ({ ...r, [col]: index.get(keyOf(r[lk]))?.length || 0 })) },
      matchedLeft,
    };
  }
  const rename = new Map(right.columns.filter((c) => c !== rk).map((c) => [c, left.columns.includes(c) ? `${spec.rightName}·${c}` : c]));
  const columns = [...left.columns, ...rename.values()];
  const rows: Row[] = [];
  for (const l of left.rows) {
    const hits = index.get(keyOf(l[lk]));
    if (!hits) {
      if (spec.how === 'left') rows.push({ ...l, ...Object.fromEntries([...rename.values()].map((c) => [c, null])) });
      continue;
    }
    for (const r of hits) {
      rows.push({ ...l, ...Object.fromEntries([...rename].map(([from, to]) => [to, r[from] ?? null])) });
      if (rows.length > MAX_JOINED_ROWS) {
        return { ok: false, error: `关联后超过 ${MAX_JOINED_ROWS} 行（一对多太多），先加筛选或改用 how=count` };
      }
    }
  }
  return { ok: true, table: { columns, rows }, matchedLeft };
}

function textWidth(v: Cell): number {
  let w = 0;
  for (const ch of str(v)) w += /[\u0000-\u00ff]/.test(ch) ? 1 : 2;
  return w;
}

function stamp(): string {
  const d = beijingIso();
  return `${d.slice(0, 10).replace(/-/g, '')}_${d.slice(11, 16).replace(':', '')}`;
}

/**
 * Writes an .xlsx (never CSV: xlsx stores "=…" text as a string cell, so cell text can't run as a formula).
 * `info` becomes a leading 说明 sheet: source, filters, time, row counts, whether the data is partial.
 */
export async function buildWorkbook(report: BuiltReport, info: string[]) {
  const XLSX = await import('xlsx');
  const wb = XLSX.utils.book_new();
  const used = new Set(report.sheets.map((s) => s.name));
  const infoName = sheetName('说明', used);
  const infoSheet = XLSX.utils.aoa_to_sheet(info.map((line) => [line]));
  infoSheet['!cols'] = [{ wch: 80 }];
  for (const s of report.sheets) {
    const ws = XLSX.utils.aoa_to_sheet([s.columns, ...s.rows]);
    ws['!cols'] = s.columns.map((c, i) => ({
      wch: Math.min(40, Math.max(6, textWidth(c), ...s.rows.slice(0, 200).map((r) => textWidth(r[i] ?? null))) + 2),
    }));
    XLSX.utils.book_append_sheet(wb, ws, s.name);
  }
  XLSX.utils.book_append_sheet(wb, infoSheet, infoName);
  return { XLSX, wb };
}

export async function downloadReport(report: BuiltReport, info: string[]): Promise<string> {
  const { XLSX, wb } = await buildWorkbook(report, info);
  const file = `${report.title.replace(/[\\/:*?"<>|]/g, ' ').trim().slice(0, 40) || '整理结果'}_${stamp()}.xlsx`;
  XLSX.writeFile(wb, file);
  return file;
}
