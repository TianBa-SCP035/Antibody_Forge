/**
 * Reads the tables rendered on the current page (Element Plus, vxe-table, plain <table>) into flat rows.
 *
 * Works on any page without page-specific code, but it only sees what the page rendered: one page of a
 * paginated list, or the visible window of a virtual-scroll table. `partial` says so.
 */

import { tableTitleOf } from './formBridge';
import { isSecretInput, isSensitiveName } from './pageContext';
import type { DataTable, Row } from './reportBuilder';

export type PageTable = DataTable & {
  title: string;
  kind: 'el-table' | 'vxe-table' | 'table';
  /** Rows the backend says exist (pagination "共 N 条"), when the page shows it. */
  total?: number;
  partial: boolean;
  partialWhy?: string;
};

const MAX_ROWS = 2000;
const MAX_COLS = 40;
const SKIP_HEADER = /^(操作|操作栏|管理)$/;
/** Sort / filter glyphs some headers render as text. */
const HEADER_ICONS = /[▾▼▲△▽↑↓⇅⌄]/g;
const OWN_UI = '.ff-root';

function shown(el: Element): boolean {
  return !!(el as HTMLElement).offsetParent || el.getClientRects().length > 0;
}

function squashText(s: string) {
  return s.replace(/\s+/g, ' ').trim().slice(0, 500);
}

/** Placeholder text an empty select renders as a span ("请选择"); it is not a value. */
const PLACEHOLDER = '.el-select__placeholder.is-transparent, .el-select__placeholder:empty, .el-input__placeholder';

/** Cell text plus the values of inputs inside it (never password-like inputs). */
function cellText(cell: HTMLTableCellElement): string {
  let t = cell.innerText || '';
  for (const p of Array.from(cell.querySelectorAll(PLACEHOLDER))) {
    const pt = (p as HTMLElement).innerText;
    if (pt) t = t.replace(pt, '');
  }
  const values = Array.from(
    cell.querySelectorAll('input:not([type=hidden]):not([type=checkbox]):not([type=radio]), textarea'),
  )
    .filter((i) => !isSecretInput(i))
    .map((i) => (i as HTMLInputElement).value.trim())
    .filter((v) => v && !t.includes(v));
  return squashText([t, ...values].map((s) => s.trim()).filter(Boolean).join(' '));
}

const TOTAL_ROW = /^(合计|总计|汇总|小计|total)$/i;

/** Expands rowspan/colspan into a full grid (merged values repeat in every covered cell). */
function grid(trs: HTMLTableRowElement[]): string[][] {
  const out: string[][] = trs.map(() => []);
  trs.forEach((tr, r) => {
    let c = 0;
    for (const cell of Array.from(tr.cells)) {
      if (cell.classList.contains('gutter')) continue;
      while (out[r]![c] !== undefined) c += 1;
      const rs = Math.max(1, cell.rowSpan || 1);
      const cs = Math.max(1, cell.colSpan || 1);
      const t = cellText(cell);
      for (let i = 0; i < rs && r + i < trs.length; i += 1) {
        for (let j = 0; j < cs; j += 1) out[r + i]![c + j] = t;
      }
      c += cs;
    }
  });
  return out;
}

/** Leaf column names; grouped headers become "组 / 列". */
function headerNames(head: string[][], width: number): string[] {
  const names: string[] = [];
  for (let c = 0; c < width; c += 1) {
    const parts: string[] = [];
    for (const row of head) {
      const t = (row[c] || '').replace(HEADER_ICONS, '').trim();
      if (t && parts[parts.length - 1] !== t) parts.push(t);
    }
    names.push(parts.join(' / '));
  }
  return names;
}

const DATA_TABLES = '.el-table, .vxe-table';

/** The pager that belongs to this table: visible, and in the nearest container that holds no other visible table. */
function paginationNear(table: Element): { total?: number; paged: boolean } {
  let cur: Element | null = table.parentElement;
  for (let depth = 0; depth < 5 && cur; depth += 1, cur = cur.parentElement) {
    const others = Array.from(cur.querySelectorAll(DATA_TABLES)).filter(
      (t) => t !== table && shown(t) && !t.contains(table) && !table.contains(t) && !t.parentElement?.closest(DATA_TABLES),
    );
    if (others.length) break;
    const pager = Array.from(cur.querySelectorAll('.el-pagination, .vxe-pager')).find((p) => shown(p) && !p.closest(OWN_UI));
    if (pager) {
      const totalText = (pager.querySelector('.el-pagination__total, .vxe-pager--total') as HTMLElement | null)?.innerText || '';
      const m = /(\d[\d,]*)/.exec(totalText);
      const pages = pager.querySelectorAll('.el-pager li, .vxe-pager--num-btn').length;
      return { total: m ? Number(m[1]!.replace(/,/g, '')) : undefined, paged: pages > 1 };
    }
  }
  return { paged: false };
}

function toTable(
  root: Element,
  kind: PageTable['kind'],
  headRows: HTMLTableRowElement[],
  bodyRows: HTMLTableRowElement[],
  index: number,
): PageTable | null {
  if (!bodyRows.length) return null;
  const body = grid(bodyRows.slice(0, MAX_ROWS));
  const head = grid(headRows);
  const width = Math.max(...body.map((r) => r.length), ...head.map((r) => r.length), 0);
  const names = head.length ? headerNames(head, width) : Array.from({ length: width }, (_, i) => `列${i + 1}`);
  const keep: Array<{ i: number; name: string }> = [];
  const seen = new Map<string, number>();
  names.forEach((raw, i) => {
    if (!raw || SKIP_HEADER.test(raw) || keep.length >= MAX_COLS) return;
    const n = (seen.get(raw) || 0) + 1;
    seen.set(raw, n);
    keep.push({ i, name: n > 1 ? `${raw}${n}` : raw });
  });
  if (!keep.length) return null;
  // Credential and contact columns are masked: their values must not reach the model or the file.
  const rows: Row[] = body
    .map((cells) => Object.fromEntries(keep.map(({ i, name }) => [name, isSensitiveName(name) ? '***' : cells[i] ?? ''])) as Row)
    .filter((r) => Object.values(r).some((v) => String(v ?? '').trim()))
    // A 合计 row inside the body would be counted again by every sum.
    .filter((r) => !TOTAL_ROW.test(String(Object.values(r).find((v) => String(v ?? '').trim()) ?? '').trim()));
  if (!rows.length) return null;

  const { total, paged } = paginationNear(root);
  const reasons: string[] = [];
  let virtual = false;
  if (kind === 'vxe-table') {
    // Virtual scrolling renders only the visible window, so a bigger page size wouldn't help.
    const wrap = root.querySelector('.vxe-table--body-wrapper') as HTMLElement | null;
    const bodyTable = wrap?.querySelector('table') as HTMLElement | null;
    const ySpace = root.querySelector('.vxe-body--y-space') as HTMLElement | null;
    const xSpace = root.querySelector('.vxe-body--x-space') as HTMLElement | null;
    if (ySpace && bodyTable && ySpace.offsetHeight > bodyTable.offsetHeight + 40) {
      reasons.push('表格是滚动加载的，只读到了当前渲染出来的行');
      virtual = true;
    }
    if (xSpace && bodyTable && xSpace.offsetWidth > bodyTable.offsetWidth + 40) {
      reasons.push('右侧还有没渲染出来的列');
      virtual = true;
    }
  }
  const hint = virtual ? '' : '（可以把每页条数调大后再让我读）';
  if (bodyRows.length > MAX_ROWS) reasons.push(`页面上有 ${bodyRows.length} 行，只读了前 ${MAX_ROWS} 行`);
  else if (total != null && total > rows.length) reasons.push(`列表共 ${total} 条，页面上只读到 ${rows.length} 条${hint}`);
  else if (total == null && paged) reasons.push(`列表有分页，只读到了当前这一页${hint}`);
  const partialWhy = reasons.join('；') || undefined;
  const pageName = document.title.split(/\s+-\s+/)[0]?.trim();
  return {
    title: tableTitleOf(root) || (pageName ? `${pageName}${index ? index + 1 : ''}` : `表格${index + 1}`),
    kind,
    columns: keep.map((k) => k.name),
    rows,
    total,
    partial: !!partialWhy,
    partialWhy,
  };
}

function rowsOf(scope: Element | null, selector: string): HTMLTableRowElement[] {
  return scope ? (Array.from(scope.querySelectorAll(selector)) as HTMLTableRowElement[]) : [];
}

export function readPageTables(): PageTable[] {
  const out: PageTable[] = [];
  for (const el of Array.from(document.querySelectorAll('.el-table'))) {
    if (el.closest(OWN_UI) || !shown(el) || el.parentElement?.closest('.el-table')) continue;
    const head = rowsOf(el.querySelector('.el-table__header-wrapper'), 'thead > tr');
    const body = rowsOf(el.querySelector('.el-table__body-wrapper'), 'tbody > tr').filter(
      (tr) => !tr.querySelector(':scope > td.el-table__expanded-cell'),
    );
    const t = toTable(el, 'el-table', head, body, out.length);
    if (t) out.push(t);
  }
  for (const el of Array.from(document.querySelectorAll('.vxe-table'))) {
    if (el.closest(OWN_UI) || !shown(el) || el.parentElement?.closest('.vxe-table')) continue;
    const main = el.querySelector('.vxe-table--main-wrapper') || el;
    const head = rowsOf(main.querySelector('.vxe-table--header-wrapper'), 'thead > tr');
    const body = rowsOf(main.querySelector('.vxe-table--body-wrapper'), 'tbody > tr.vxe-body--row');
    const t = toTable(el, 'vxe-table', head, body, out.length);
    if (t) out.push(t);
  }
  for (const el of Array.from(document.querySelectorAll('table'))) {
    if (el.closest(`${OWN_UI}, .el-table, .vxe-table, .el-picker-panel, .el-calendar, .el-descriptions`) || !shown(el)) continue;
    const tbl = el as HTMLTableElement;
    const all = Array.from(tbl.rows);
    let head = tbl.tHead ? Array.from(tbl.tHead.rows) : [];
    if (!head.length && all[0] && Array.from(all[0].cells).every((c) => c.tagName === 'TH')) head = [all[0]];
    if (!head.length) continue;
    const body = all.filter((r) => !head.includes(r) && r.parentElement?.tagName !== 'TFOOT');
    const t = toTable(el, 'table', head, body, out.length);
    if (t) out.push(t);
  }
  return out.slice(0, 8);
}

/** Exact or partial title match; otherwise the table with the most rows. */
export function pickPageTable(tables: PageTable[], want?: string): PageTable | undefined {
  const w = (want || '').trim();
  if (w) {
    const hit = tables.find((t) => t.title === w) || tables.find((t) => t.title.includes(w) || w.includes(t.title));
    if (hit) return hit;
  }
  return [...tables].sort((a, b) => b.rows.length - a.rows.length)[0];
}
