/**
 * Browser-side executors for the pet agent's tools (names match pet-proxy/agent_tools.py).
 *
 * Data comes from the normal API client or from replaying list requests the pages already made
 * (apiWatch.ts), always with the user's own token, so backend permissions apply. Numbers the model reports (counts, titers, day offsets) are computed
 * here; models are unreliable at arithmetic. `propose_*` tools never act — they return a
 * proposal the user must confirm on a card.
 */

import {
  exportScheme,
  exportSerumList,
  export_mouse,
  fetchDetail,
  fetchElisaPlates,
  fetchFacsPlates,
  fetchList,
  skipGlobalErrorHandler,
} from '#/api/serum';
import { downloadListExcel, excelTimestamp } from '#/utils/downloadExcel';
import { downloadBlob } from '#/utils/file-resource';
import {
  buildFacsConclusionForPage,
  type ConclusionCellValue,
  type FacsConclusionModel,
} from '#/utils/serumTiterConclusion';

import {
  applyFills,
  describePageForm,
  formLabels,
  resolveFill,
  scanPageForm,
  undoFills,
  type FillSnapshot,
  type ResolvedFill,
} from './formBridge';
import {
  allScopeFilterText,
  fetchSource,
  findSource,
  joinText,
  listSources,
  MAX_SOURCE_ROWS,
  pageFilterText,
  rememberJoin,
  sourceColumns,
  sourceForTable,
  unopenedPages,
} from './apiWatch';
import { pickPageTable, readPageTables } from './pageTable';
import {
  buildReport,
  columnValues,
  beijingIso,
  joinTables,
  reportFile,
  type BuiltReport,
  type Condition,
  type DataTable,
  type JoinSpec,
  type ReportSpec,
  type Row,
} from './reportBuilder';
import { currentUserKey, currentUserName, hasUserToken } from './session';

export type ToolCall = {
  id: string;
  name: string;
  args: Record<string, any>;
  error?: string | null;
  phase?: string;
};

export type FillItem = { table?: string; row?: number; field: string; value: string; reason?: string };
export type ManualFill = { label: string; value: string; why: string };
export type { ResolvedFill };

export type Proposal =
  | {
      kind: 'fill';
      fills: ResolvedFill[];
      manual: ManualFill[];
      autoSave?: boolean;
      /** Auto-save page for a record not created yet: applying creates it, and undo can't delete it. */
      newRecord?: boolean;
      formLabels?: string[];
    }
  | {
      kind: 'export';
      exportKind: 'project_list' | 'mouse_list' | 'scheme';
      filters: Record<string, any>;
      label: string;
      count?: number;
      projectId?: number;
      projectCode?: string;
      /** Skip the confirm card: filters are clear and the download is read-only. */
      auto?: boolean;
    }
  | {
      kind: 'report';
      report: BuiltReport;
      /** Lines of the 说明 sheet: source, filters, time, counts, partial-data warning. */
      info: string[];
      source: string;
      partialWhy?: string;
    }
  | {
      kind: 'open_page';
      path: string;
      title: string;
      /** The question to ask again once the page's list is learned (set by the chat, not the tool). */
      question?: string;
    };

export type ToolOutcome = { content: string; proposal?: Proposal };

const cfg = skipGlobalErrorHandler;
const MAX_LIST = 100;

class ForbiddenError extends Error {}

function isForbidden(err: unknown): boolean {
  const e = err as any;
  const status = e?.response?.status ?? e?.status ?? e?.code;
  if ([401, 403, '401', '403'].includes(status)) return true;
  const msg = String(e?.response?.data?.message || e?.response?.data?.detail || e?.message || '');
  return /无权限|没有权限|权限不足|未登录|forbidden|unauthorized/i.test(msg);
}

function abortIf(signal?: AbortSignal) {
  if (signal?.aborted) throw new DOMException('Aborted', 'AbortError');
}

function text(v: unknown): string {
  return v == null ? '' : String(v).trim();
}

function items(raw: any): any[] {
  if (Array.isArray(raw)) return raw;
  if (Array.isArray(raw?.items)) return raw.items;
  if (Array.isArray(raw?.data?.items)) return raw.data.items;
  return [];
}

function todayLocal(): string {
  return beijingIso().slice(0, 10);
}

function daysBetween(from: string, to: string): number | null {
  const a = Date.parse(from.slice(0, 10));
  const b = Date.parse(to.slice(0, 10));
  if (Number.isNaN(a) || Number.isNaN(b)) return null;
  return Math.round((b - a) / 86400000);
}

function projectBrief(row: any) {
  const out: Record<string, unknown> = {};
  for (const k of [
    'experiment_id',
    'project_code',
    'project_name',
    'target_name',
    'owner',
    'pm',
    'project_status',
    'start_date',
    'mouse_strain',
  ]) {
    if (text(row?.[k])) out[k] = text(row[k]);
  }
  return out;
}

async function listRows(filters: Record<string, any>, limit: number) {
  try {
    const raw: any = await fetchList({ ...filters, page: 1, limit }, cfg);
    return { rows: items(raw), total: Number(raw?.total ?? items(raw).length) };
  } catch (err) {
    if (isForbidden(err)) throw new ForbiddenError();
    throw err;
  }
}

function baseFilters(args: Record<string, any>) {
  const f: Record<string, any> = {};
  if (args.target_name) f.target_name = args.target_name;
  if (args.status) f.project_status = args.status;
  if (args.mine) {
    const me = currentUserName();
    if (me) f.owner = me;
  } else if (args.owner) {
    f.owner = args.owner;
  }
  return f;
}

/** The list API has no free-text keyword; try code/ID, name and target, then merge. */
async function keywordSearch(keyword: string, filters: Record<string, any>, limit: number) {
  const tries = await Promise.allSettled([
    listRows({ ...filters, project_code: keyword }, limit),
    listRows({ ...filters, project_name: keyword }, limit),
    listRows({ ...filters, target_name: keyword }, limit),
  ]);
  const seen = new Map<string, any>();
  let truncated = false;
  let forbidden = 0;
  for (const t of tries) {
    if (t.status === 'rejected') {
      if (t.reason instanceof ForbiddenError) forbidden += 1;
      continue;
    }
    if (t.value.total > t.value.rows.length) truncated = true;
    for (const r of t.value.rows) seen.set(String(r.id ?? r.experiment_id), r);
  }
  if (forbidden === tries.length) throw new ForbiddenError();
  return { rows: [...seen.values()], truncated };
}

type Resolved =
  | { ok: true; detail: any }
  | { ok: false; result: Record<string, unknown> };

async function resolveProject(ref: string, signal?: AbortSignal): Promise<Resolved> {
  const q = text(ref);
  if (!q) return { ok: false, result: { error: '缺少项目' } };
  const { rows, truncated } = await keywordSearch(q, {}, 20);
  abortIf(signal);
  const lower = q.toLowerCase();
  const exact = rows.filter((r) => text(r.experiment_id).toLowerCase() === lower);
  let pick: any = exact.length === 1 ? exact[0] : null;
  if (!pick && rows.length === 1) pick = rows[0];
  if (!pick) {
    if (!rows.length) return { ok: false, result: { not_found: true, query: q } };
    return {
      ok: false,
      result: {
        ambiguous: true,
        query: q,
        candidates: rows.slice(0, 10).map(projectBrief),
        candidate_count: truncated ? `${rows.length}+` : rows.length,
        hint: '请让用户从候选里指定实验ID',
      },
    };
  }
  try {
    const detail = await fetchDetail(pick.id, cfg);
    return { ok: true, detail: detail || pick };
  } catch (err) {
    if (isForbidden(err)) throw new ForbiddenError();
    throw err;
  }
}

async function searchProjects(args: Record<string, any>) {
  const limit = Math.max(1, Math.min(20, Number(args.limit) || 8));
  const filters = baseFilters(args);
  if (args.mine && !filters.owner) return { error: '拿不到当前登录用户名' };
  let rows: any[];
  let total: number | string;
  if (args.keyword) {
    const r = await keywordSearch(args.keyword, filters, MAX_LIST);
    rows = r.rows;
    total = r.truncated ? `${rows.length}+` : rows.length;
  } else {
    const r = await listRows(filters, MAX_LIST);
    rows = r.rows;
    total = r.total;
  }
  const result: Record<string, unknown> = {
    total,
    filters: { ...filters, ...(args.keyword ? { keyword: args.keyword } : {}) },
    shown: Math.min(limit, rows.length),
    items: rows.slice(0, limit).map(projectBrief),
  };
  if (typeof total === 'number' && total <= rows.length && rows.length > 1) {
    const byStatus: Record<string, number> = {};
    for (const r of rows) {
      const s = text(r.project_status) || '(空)';
      byStatus[s] = (byStatus[s] || 0) + 1;
    }
    result.status_counts = byStatus;
  }
  return result;
}

function stageOrder(steps: any[]) {
  const map = new Map<string, { stage: string; dates: Set<string>; groups: Set<string>; order: number }>();
  steps.forEach((s, i) => {
    const stage = text(s.stage_name) || '(未命名步骤)';
    const rec = map.get(stage) || { stage, dates: new Set(), groups: new Set(), order: i };
    if (text(s.date_actual)) rec.dates.add(text(s.date_actual).slice(0, 10));
    if (text(s.group_id)) rec.groups.add(text(s.group_id));
    rec.order = Math.min(rec.order, i);
    map.set(stage, rec);
  });
  return [...map.values()].sort((a, b) => {
    const da = [...a.dates].sort()[0] || '9999';
    const db = [...b.dates].sort()[0] || '9999';
    return da === db ? a.order - b.order : da.localeCompare(db);
  });
}

async function getProjectProgress(args: Record<string, any>, signal?: AbortSignal) {
  const r = await resolveProject(args.project, signal);
  if (!r.ok) return r.result;
  const d = r.detail;
  const today = todayLocal();
  const steps = (Array.isArray(d.steps) ? d.steps : []).slice().sort(
    (a: any, b: any) => (a.sort_order ?? 0) - (b.sort_order ?? 0),
  );
  const stages = stageOrder(steps).map((s) => {
    const dates = [...s.dates].sort();
    const first = dates[0];
    const last = dates[dates.length - 1];
    let state = '无日期';
    if (first && last) state = last < today ? '日期已过' : first > today ? '未到' : first === today || last === today ? '今天' : '进行中';
    return {
      stage: s.stage,
      date: first ? (first === last ? first : `${first}~${last}`) : '',
      groups: [...s.groups].join(','),
      state,
      days_from_today: first ? daysBetween(today, first) : null,
    };
  });
  const passed = stages.filter((s) => s.state === '日期已过');
  const next = stages.find((s) => s.state === '未到' || s.state === '今天' || s.state === '进行中');
  return {
    project: projectBrief(d),
    today,
    project_status: text(d.project_status),
    prep_status: text(d.prep_status) || undefined,
    stage_total: stages.length,
    stage_date_passed: passed.length,
    last_date_passed: passed.length ? passed[passed.length - 1] : null,
    next_step: next || null,
    stages: stages.slice(0, 20),
    ...(stages.length > 20 ? { stages_shown: 20 } : {}),
    note:
      '系统里只有计划日期，没有步骤执行记录：“日期已过”只表示计划日期已经过去，不代表做完了，回答时不要说“已完成”；实际进展以 project_status 为准。days_from_today 为负表示已过去多少天，为正表示还有多少天',
  };
}

async function getProjectDetail(args: Record<string, any>, signal?: AbortSignal) {
  const r = await resolveProject(args.project, signal);
  if (!r.ok) return r.result;
  const d = r.detail;
  const out: Record<string, unknown> = { project: projectBrief(d) };
  for (const k of [
    'lab_notebook',
    'project_purpose',
    'target_codes',
    'target_type',
    'target_size',
    'study_type',
    'assay_method',
    'immunization_interval',
    'mouse_strain_category',
    'remark',
  ]) {
    const v = d?.[k];
    if (Array.isArray(v) ? v.length : text(v)) out[k] = v;
  }
  const groups = Array.isArray(d.mouse_groups) ? d.mouse_groups : [];
  const compact = (obj: Record<string, unknown>) =>
    Object.fromEntries(Object.entries(obj).filter(([, v]) => text(v)));
  out.mouse_groups = groups.slice(0, 12).map((g: any) =>
    compact({
      group_id: g.group_id,
      mouse_strain: g.mouse_strain,
      mouse_strain_category: g.mouse_strain_category,
      mouse_count: g.mouse_count,
      age_weeks: g.age_weeks,
      sex: g.sex,
      vendor: g.vendor,
      cage_position: g.cage_position,
    }),
  );
  if (groups.length > 12) out.mouse_groups_total = groups.length;
  const counts = groups.map((g: any) => Number.parseInt(text(g.mouse_count), 10)).filter(Number.isFinite);
  if (counts.length) out.mouse_total = counts.reduce((a: number, b: number) => a + b, 0);
  const antigens = Array.isArray(d.antigens) ? d.antigens : [];
  if (antigens.length > 8) out.antigens_total = antigens.length;
  out.antigens = antigens.slice(0, 8).map((a: any) =>
    compact({
      antigen_id: a.antigen_id,
      antigen_name: a.antigen_name,
      species: a.species,
      antigen_type: a.antigen_type,
      catalog_no: a.catalog_no,
      stock_conc: a.stock_conc,
      vendor: a.vendor,
      adjuvant_type: a.adjuvant_type,
      adjuvant_source: a.adjuvant_source,
    }),
  );
  if (args.include_scheme !== false) {
    const steps = (Array.isArray(d.steps) ? d.steps : [])
      .slice()
      .sort((a: any, b: any) => text(a.group_id).localeCompare(text(b.group_id)) || (a.sort_order ?? 0) - (b.sort_order ?? 0));
    out.steps = steps.slice(0, 36).map((s: any) =>
      compact({
        group_id: s.group_id,
        stage_name: s.stage_name,
        day_relative: s.day_relative,
        date: s.date_actual,
        antigen_id: Array.isArray(s.antigen_id) ? s.antigen_id.join('+') : s.antigen_id,
        antigen_dose: s.antigen_dose,
        adjuvant_name: s.adjuvant_name,
        cpg_dose: s.cpg_dose,
        injection_volume: s.injection_volume,
        route: s.route,
        injection_site: s.injection_site,
      }),
    );
    if (steps.length > 36) out.steps_truncated = steps.length;
  }
  if (Array.isArray(d.titer_owners) && d.titer_owners.length) out.titer_owners = d.titer_owners;
  if (out.mouse_groups_total || out.antigens_total || out.steps_truncated) {
    out.note = '带 *_total / steps_truncated 的列表只给了前面一部分，不要据此说“全部”或做整体结论';
  }
  return out;
}

function numeric(v: ConclusionCellValue | undefined): v is number {
  return typeof v === 'number' && Number.isFinite(v) && v > 0;
}

/** Titers are dilution steps; with an even count take the lower middle value so the median is a titer that was actually measured. */
function median(values: number[]): number | null {
  if (!values.length) return null;
  const s = [...values].sort((a, b) => a - b);
  return s[Math.ceil(s.length / 2) - 1]!;
}

/** Flatten the conclusion model into per-row stats plus stage-over-stage fold changes. */
function summarizeTiter(model: FacsConclusionModel, stageFilter?: string, methodFilter?: string) {
  type Row = {
    stage: string;
    method: string;
    group: string;
    antigen: string;
    target: string;
    mice: Record<string, ConclusionCellValue>;
  };
  const rows: Row[] = [];
  const stagesSeen: string[] = [];
  for (const st of model.stages) {
    stagesSeen.push(st.stageName);
    for (const m of st.methods) {
      for (const t of m.groupTables) {
        for (const r of t.rows) {
          const mice: Record<string, ConclusionCellValue> = {};
          for (const mouse of t.mouseColumns) mice[mouse] = r.cells[mouse] ?? 'N/A';
          rows.push({
            stage: st.stageName,
            method: m.method,
            group: t.groupDisplayLabel || t.groupId,
            antigen: t.antigenLabel,
            target: [r.speciesTiterLabel || r.species, r.targetName].filter(Boolean).join(' '),
            mice,
          });
        }
      }
    }
  }
  const stageMatch = (s: string) => !stageFilter || s.includes(stageFilter) || stageFilter.includes(s);
  const picked = rows.filter((r) => stageMatch(r.stage) && (!methodFilter || r.method === methodFilter));

  const tables = picked.slice(0, 24).map((r) => {
    const entries = Object.entries(r.mice);
    const nums = entries.map(([, v]) => v).filter(numeric);
    const best = entries.filter(([, v]) => numeric(v)).sort((a, b) => (b[1] as number) - (a[1] as number));
    return {
      stage: r.stage,
      method: r.method,
      group: r.group,
      antigen: r.antigen || undefined,
      target: r.target,
      mice: Object.fromEntries(entries.slice(0, 20)),
      mouse_count: entries.length,
      positive_count: nums.length,
      negative_count: entries.filter(([, v]) => v === '-').length,
      no_data_count: entries.filter(([, v]) => v === 'N/A').length,
      max: nums.length ? Math.max(...nums) : null,
      max_mice: best.length ? best.filter(([, v]) => v === best[0]![1]).map(([k]) => k) : [],
      median: median(nums),
    };
  });

  const folds: Array<Record<string, unknown>> = [];
  const keyOf = (r: Row) => `${r.method}|${r.group}|${r.target}`;
  const byKey = new Map<string, Row[]>();
  for (const r of rows.filter((x) => !methodFilter || x.method === methodFilter)) {
    byKey.set(keyOf(r), [...(byKey.get(keyOf(r)) || []), r]);
  }
  for (const list of byKey.values()) {
    const ordered = list.sort((a, b) => stagesSeen.indexOf(a.stage) - stagesSeen.indexOf(b.stage));
    for (let i = 1; i < ordered.length; i += 1) {
      const prev = ordered[i - 1]!;
      const cur = ordered[i]!;
      if (stageFilter && !stageMatch(cur.stage)) continue;
      const perMouse: Record<string, number> = {};
      for (const [mouse, v] of Object.entries(cur.mice)) {
        const p = prev.mice[mouse];
        if (numeric(v) && numeric(p)) perMouse[mouse] = Math.round((v / p) * 100) / 100;
      }
      const ratios = Object.values(perMouse);
      if (!ratios.length) continue;
      folds.push({
        from: prev.stage,
        to: cur.stage,
        method: cur.method,
        group: cur.group,
        target: cur.target,
        per_mouse_fold: perMouse,
        rose: ratios.filter((x) => x > 1).length,
        flat: ratios.filter((x) => x === 1).length,
        fell: ratios.filter((x) => x < 1).length,
      });
    }
  }
  return {
    stages: stagesSeen,
    tables,
    ...(picked.length > tables.length ? { tables_shown: tables.length } : {}),
    total_rows: picked.length,
    folds: folds.slice(0, 12),
    ...(folds.length > 12 ? { folds_total: folds.length } : {}),
    stats_note:
      'max/median/阳性数按每行全部小鼠计算（mice 最多列 20 只）；median 偶数只时取中间两只里较低的实测值。' +
      (picked.length > tables.length || folds.length > 12 ? '表格或倍数变化只列了一部分，不要据此做全部组别的结论。' : ''),
  };
}

async function getTiterSummary(args: Record<string, any>, signal?: AbortSignal) {
  const r = await resolveProject(args.project, signal);
  if (!r.ok) return r.result;
  const d = r.detail;
  const eid = text(d.experiment_id);
  let facs: any;
  let elisa: any;
  try {
    [facs, elisa] = await Promise.all([
      fetchFacsPlates({ experiment_id: eid }, cfg),
      fetchElisaPlates({ experiment_id: eid }, cfg),
    ]);
  } catch (err) {
    if (isForbidden(err)) throw new ForbiddenError();
    throw err;
  }
  abortIf(signal);
  const model = buildFacsConclusionForPage(d, d.titer_targets, items(facs), items(elisa));
  if (!model.stages.length) {
    return { project: projectBrief(d), no_titer_data: true, warnings: model.warnings };
  }
  return {
    project: projectBrief(d),
    unit: '数值=该鼠最高阳性稀释倍数（ELISA 为稀释倍数，FACS 已换算为 10^n）；"-"=全阴性；"N/A"=无数据',
    ...summarizeTiter(model, text(args.immune_stage) || undefined, text(args.method) || undefined),
    warnings: model.warnings,
  };
}

// ---------------- current page form ----------------

function checkCurrentForm() {
  const form = scanPageForm();
  if (!form.fields.length && !form.tables.length) {
    return { no_form: true, hint: '当前页面没有扫到表单（可能需要先打开编辑弹窗或编辑页）' };
  }
  return { ...describePageForm(form), note: '只读取页面状态，未修改任何内容' };
}

function proposeFormFill(args: Record<string, any>): ToolOutcome {
  const form = scanPageForm();
  if (!form.saveButton) {
    return { content: JSON.stringify({ error: 'not_editable', note: '页面上没有保存/提交按钮，改动可能立即生效，不支持代填；请告诉用户原因' }) };
  }
  const fills: ResolvedFill[] = [];
  const manual: ManualFill[] = [];
  const rejected: Array<Record<string, string>> = [];
  const unchanged: string[] = [];
  for (const f of (args.fills || []) as FillItem[]) {
    const r = resolveFill(form, f);
    const where = f.table ? `${f.table} 第${f.row}行 ${f.field}` : f.field;
    if (r.ok && r.unchanged) unchanged.push(where);
    else if (r.ok) fills.push({ ...f, display: r.display });
    else if (r.manual) manual.push({ label: where, value: f.value, why: r.why });
    else rejected.push({ field: where, value: f.value, why: r.why });
  }
  if (!fills.length && !manual.length) {
    if (unchanged.length && !rejected.length) {
      return { content: JSON.stringify({ proposal_created: false, already_filled: unchanged, note: '这些字段页面上已经是这个值，不需要填' }) };
    }
    return { content: JSON.stringify({ error: '建议都没法用', rejected, hint: '按 rejected 的原因修正后再调用 propose_form_fill' }) };
  }
  // An auto-save page without a record id in the URL is a "new" form: the first save creates a record that undo can't remove.
  const newRecord = form.autoSave && !/[?&][\w-]*id=/i.test(location.search);
  return {
    content: JSON.stringify({
      proposal_created: true,
      will_fill: fills.length,
      needs_manual: manual.map((m) => m.label),
      already_filled: unchanged,
      rejected,
      ...(form.autoSave ? { auto_save: true } : {}),
      ...(newRecord ? { creates_record: true } : {}),
      note: [
        rejected.length
          ? '可用的建议已加入卡片；rejected 里的项可修正后再调用 propose_form_fill（会合并进同一张卡片）'
          : '已加入填写建议卡片（还有别的部分就继续调用，会合并）；等用户点“应用”，尚未填入',
        newRecord
          ? '这是自动保存的新建页：用户点应用后页面会自己新建一条记录，撤销删不掉它，回答里要明确提醒'
          : form.autoSave
            ? '这个页面会自动保存，用户点应用后几秒内就会写进系统，回答里要提醒'
            : '应用后也不会提交，用户自己点保存',
      ].join('；'),
    }),
    proposal: { kind: 'fill', fills, manual, autoSave: form.autoSave, newRecord, formLabels: formLabels(form) },
  };
}

export async function applyFillProposal(fills: ResolvedFill[]) {
  return applyFills(fills);
}

export async function undoFillProposal(snapshots: FillSnapshot[]) {
  return undoFills(snapshots);
}

// ---------------- export proposals ----------------

const EXPORT_NAMES = { project_list: '免疫项目列表', mouse_list: '小鼠免疫明细', scheme: '免疫方案' } as const;

const FILTER_LABELS: Record<string, string> = {
  project_code: '编号',
  project_name: '项目名',
  target_name: '靶点',
  owner: '负责人',
  project_status: '状态',
};

/** The list API filters one field at a time; find which of code / target / name the keyword hits. */
async function keywordHits(filters: Record<string, any>, keyword: string): Promise<Array<{ field: string; total: number }>> {
  const fields = ['project_code', 'target_name', 'project_name'];
  const totals = await Promise.all(fields.map((k) => listRows({ ...filters, [k]: keyword }, 1).then((r) => r.total)));
  return fields.map((field, i) => ({ field, total: totals[i]! })).filter((h) => h.total > 0);
}

/** For APIs that take one field: the field with the most hits (a code hit must not hide 40 target hits). */
async function keywordField(filters: Record<string, any>, keyword: string): Promise<string> {
  const hits = await keywordHits(filters, keyword);
  return hits.sort((a, b) => b.total - a.total)[0]?.field || '';
}

function describeFilters(filters: Record<string, any>) {
  const parts = Object.entries(filters).map(([k, v]) => {
    const val = k === 'project_status' ? ({ ongoing: '进行中', completed: '已结题' } as any)[v] || v : v;
    return `${FILTER_LABELS[k] || k}：${val}`;
  });
  return parts.length ? parts.join('，') : '全部项目（无筛选）';
}

async function proposeExport(args: Record<string, any>, signal?: AbortSignal): Promise<ToolOutcome> {
  const kind = args.kind as 'project_list' | 'mouse_list' | 'scheme';
  if (kind === 'scheme') {
    const r = await resolveProject(args.project, signal);
    if (!r.ok) return { content: JSON.stringify(r.result) };
    const d = r.detail;
    const code = text(d.project_code || d.experiment_id);
    return {
      content: JSON.stringify({
        proposal_created: true,
        kind,
        project: projectBrief(d),
        auto: true,
        note: '条数够少，允许跳过确认；只有用户原话明确要文件时才会直接下载，否则仍出确认卡片——回答写请点「确认导出」，不要说已经开始下载',
      }),
      proposal: {
        kind: 'export',
        exportKind: kind,
        filters: {},
        label: `${EXPORT_NAMES.scheme}：${code} ${text(d.project_name)}`,
        projectId: Number(d.id),
        projectCode: code,
        auto: true,
      },
    };
  }
  const filters = baseFilters(args);
  if (args.mine && !filters.owner) return { content: JSON.stringify({ error: '拿不到当前登录用户名' }) };
  const keyword = text(args.keyword || args.project);
  if (keyword) {
    const field = await keywordField(filters, keyword);
    if (!field) return { content: JSON.stringify({ not_found: true, keyword, filters }) };
    filters[field] = keyword;
  }
  const { total } = await listRows(filters, 1);
  abortIf(signal);
  if (!total) return { content: JSON.stringify({ empty: true, filters, note: '按这些条件没有项目，未生成导出' }) };
  const label = `${EXPORT_NAMES[kind]} · ${describeFilters(filters)}`;
  // Clear, bounded filters → download without a confirm card. "all projects" still asks.
  const auto = total != null && total > 0 && total <= 40 && Object.keys(filters).length > 0;
  return {
    content: JSON.stringify({
      proposal_created: true,
      kind,
      filters,
      project_count: total,
      auto,
      note: auto
        ? '条数够少，允许跳过确认；只有用户原话明确要文件时才会直接下载，否则仍出确认卡片——回答写请点「确认导出」，不要说已经开始下载'
        : '已生成导出确认卡片，等待用户点“确认导出”；尚未下载',
    }),
    proposal: { kind: 'export', exportKind: kind, filters, label, count: total, auto },
  };
}

function asBlob(res: any) {
  return res instanceof Blob
    ? res
    : new Blob([res], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
}

export async function runExportProposal(p: Extract<Proposal, { kind: 'export' }>): Promise<string> {
  try {
    if (p.exportKind === 'project_list') {
      await downloadListExcel(() => exportSerumList(p.filters), `免疫实验列表_${excelTimestamp()}.xlsx`);
    } else if (p.exportKind === 'mouse_list') {
      await downloadListExcel(async () => asBlob(await export_mouse(p.filters)), `小鼠免疫导出_${excelTimestamp()}.xlsx`);
    } else {
      if (!p.projectId) return '缺少项目 ID，没法导出';
      await downloadListExcel(async () => asBlob(await exportScheme({ ids: [p.projectId!] })), `免疫方案_${p.projectCode || p.projectId}_${excelTimestamp()}.xlsx`);
    }
    return '已开始下载';
  } catch (err) {
    if (isForbidden(err)) return '你的账号没有这个导出权限';
    return '导出失败了，稍后再试或去列表页导出';
  }
}

// ---------------- custom report (summary + Excel) ----------------

const REPORT_MAX_ROWS = MAX_SOURCE_ROWS;
const REPORT_PAGE = 500;

const joined = (v: unknown) => (Array.isArray(v) ? v.map(text).filter(Boolean).join(',') : text(v));

/** Same columns as the system's own list export, plus 开始月份 / 效价负责人 for grouping. */
const PROJECT_COLUMNS: Array<[string, (r: any) => string | number | null]> = [
  ['编号', (r) => text(r.project_code)],
  ['实验ID', (r) => text(r.experiment_id)],
  ['项目名称', (r) => text(r.project_name)],
  ['靶点', (r) => text(r.target_name)],
  ['靶点编号', (r) => joined(r.target_codes)],
  ['靶点类型', (r) => text(r.target_type)],
  ['靶点大小', (r) => text(r.target_size)],
  ['负责人', (r) => text(r.owner)],
  ['PM', (r) => text(r.pm)],
  ['状态', (r) => text(r.project_status)],
  ['制备状态', (r) => text(r.prep_status)],
  ['开始日期', (r) => text(r.start_date).slice(0, 10)],
  ['开始月份', (r) => text(r.start_date).slice(0, 7)],
  ['课题类型', (r) => text(r.study_type)],
  ['鼠型', (r) => text(r.mouse_strain)],
  ['归类鼠型', (r) => text(r.mouse_strain_category)],
  ['免疫间隔', (r) => text(r.immunization_interval)],
  ['检测方法', (r) => joined(r.assay_method)],
  ['FACS板数', (r) => (r.facs_plate_count == null || r.facs_plate_count === '' ? null : Number(r.facs_plate_count))],
  ['ELISA板数', (r) => (r.elisa_plate_count == null || r.elisa_plate_count === '' ? null : Number(r.elisa_plate_count))],
  ['效价负责人', (r) => joined(r.titer_owners)],
  ['笼位', (r) => text(r.cage_position)],
  ['实验记录本', (r) => text(r.lab_notebook)],
  ['实验备注', (r) => text(r.remark)],
  ['项目目的', (r) => text(r.project_purpose)],
];

async function projectTable(filters: Record<string, any>, signal?: AbortSignal) {
  const rows: any[] = [];
  let total = 0;
  for (let page = 1; rows.length < REPORT_MAX_ROWS; page += 1) {
    let raw: any;
    try {
      raw = await fetchList({ ...filters, page, limit: REPORT_PAGE }, cfg);
    } catch (err) {
      if (isForbidden(err)) throw new ForbiddenError();
      throw err;
    }
    abortIf(signal);
    const batch = items(raw);
    total = Number(raw?.total ?? rows.length + batch.length);
    rows.push(...batch);
    if (batch.length < REPORT_PAGE || rows.length >= total) break;
  }
  const table: DataTable = {
    columns: PROJECT_COLUMNS.map(([c]) => c),
    rows: rows.slice(0, REPORT_MAX_ROWS).map((r) => Object.fromEntries(PROJECT_COLUMNS.map(([c, get]) => [c, get(r)])) as Row),
  };
  return { table, total };
}

const OP_TEXT: Record<string, string> = {
  '=': '等于', '!=': '不等于', contains: '包含', not_contains: '不包含', '>': '大于', '>=': '不小于',
  '<': '小于', '<=': '不大于', empty: '为空', not_empty: '不为空', in: '属于',
};

function describeWhere(where: Condition[] = []) {
  return where.map((c) => `${c.column}${OP_TEXT[c.op] || c.op}${c.value ? ` ${c.value}` : ''}`).join('；');
}

function nowText() {
  return beijingIso().slice(0, 16).replace('T', ' ');
}

const JOIN_TEXT: Record<JoinSpec['how'], string> = {
  inner: '只保留两边都有的',
  left: '保留左边全部',
  anti: '只要左边对不上的',
  count: '统计右边对上的条数',
};

type Loaded =
  | { table: DataTable; label: string; shortName: string; info: string; partialWhy?: string; extra?: Record<string, unknown> }
  | { error: Record<string, unknown> };

function sourceCatalog() {
  return listSources().map((s) => ({ id: s.id, name: s.name, page: s.route, ...(s.total != null ? { total: s.total } : {}) }));
}

/**
 * One data source for a report: `projects` (built-in plugin), `page_table` (current page; pulls every page
 * through the page's own list request when it can), or a learned source id / name.
 * `useFilters`: the report's project filters apply to the main source only, not to a joined one.
 */
const UNKNOWN_COLUMN_HINT =
  'available_columns 里有同一个意思、只是叫法不同的列（如 负责人/owner）就换成它重试；' +
  '没有这个意思的列就不要换成别的列再调用，直接告诉用户数据里没有这一项，替代做法只在回答里提议';

const SOURCE_TTL_MS = 5 * 60_000;
const sourceCache = new Map<string, { at: number; loaded: Exclude<Loaded, { error: unknown }> }>();

/**
 * Same data within a few minutes is reused, so "now split it by month" doesn't refetch thousands of rows.
 * The current page's table is always read fresh (the user may have changed its filters).
 */
async function loadSource(ref: string, args: Record<string, any>, signal: AbortSignal | undefined, useFilters: boolean): Promise<Loaded> {
  if (ref === 'page_table') return loadSourceFresh(ref, args, signal, useFilters);
  const pick = (k: string) => (useFilters ? args[k] ?? null : null);
  const pageFilters = args.scope === 'page_filters';
  const key = JSON.stringify([
    currentUserKey(),
    ref,
    pageFilters ? 'page_filters' : 'all',
    // The page's filters may have changed since: they are part of what was fetched.
    pageFilters ? findSource(ref)?.lastParams ?? null : null,
    ...['keyword', 'target_name', 'owner', 'status', 'mine'].map(pick),
  ]);
  const hit = sourceCache.get(key);
  if (hit && Date.now() - hit.at < SOURCE_TTL_MS) {
    const time = new Date(hit.at).toTimeString().slice(0, 5);
    return { ...hit.loaded, info: `${hit.loaded.info}（${time} 取的数据，${Math.round(SOURCE_TTL_MS / 60_000)} 分钟内复用）` };
  }
  const loaded = await loadSourceFresh(ref, args, signal, useFilters);
  if (!('error' in loaded)) {
    for (const [k, v] of sourceCache) if (Date.now() - v.at >= SOURCE_TTL_MS) sourceCache.delete(k);
    sourceCache.set(key, { at: Date.now(), loaded });
  }
  return loaded;
}

const LAST_REPORT_MS = 30 * 60_000;
const REPORT_ARG_KEYS = ['source', 'scope', 'join', 'title', 'keyword', 'target_name', 'owner', 'status', 'mine', 'table',
  'where', 'group_by', 'metrics', 'columns', 'sort', 'split_by', 'limit'];
let lastReport: { user: string; at: number; args: Record<string, unknown> } | null = null;

/** The previous report's spec, so a follow-up ("drop the finished ones, split by month") can edit it. */
export function lastReportContext(): string {
  if (!lastReport || lastReport.user !== currentUserKey() || Date.now() - lastReport.at > LAST_REPORT_MS) return '';
  return JSON.stringify(lastReport.args);
}

export function hasRecentReport(): boolean {
  return !!lastReportContext();
}

async function loadSourceFresh(ref: string, args: Record<string, any>, signal: AbortSignal | undefined, useFilters: boolean): Promise<Loaded> {
  if (ref === 'projects') {
    const filters = useFilters ? baseFilters(args) : {};
    if (useFilters && args.mine && !filters.owner) return { error: { error: '拿不到当前登录用户名' } };
    const keyword = useFilters ? text(args.keyword) : '';
    let r: { table: DataTable; total: number };
    let label: string;
    if (keyword) {
      // Code, target and name hits are unioned: the list API only filters one field per request.
      const hits = await keywordHits(filters, keyword);
      if (!hits.length) return { error: { not_found: true, keyword, filters } };
      const parts = await Promise.all(hits.map((h) => projectTable({ ...filters, [h.field]: keyword }, signal)));
      const seen = new Set<string>();
      const rows: Row[] = [];
      for (const p of parts) {
        for (const row of p.table.rows) {
          const id = String(row['实验ID'] ?? '') || JSON.stringify(row);
          if (seen.has(id)) continue;
          seen.add(id);
          rows.push(row);
        }
      }
      const fetched = parts.reduce((n, p) => n + p.table.rows.length, 0);
      const total = parts.reduce((n, p) => n + p.total, 0);
      r = { table: { columns: parts[0]!.table.columns, rows }, total: rows.length + (total - fetched) };
      const kw = `编号/靶点/项目名含「${keyword}」`;
      label = `免疫项目列表（${Object.keys(filters).length ? `${describeFilters(filters)}，${kw}` : kw}）`;
    } else {
      r = await projectTable(filters, signal);
      label = `免疫项目列表（${describeFilters(filters)}）`;
    }
    return {
      table: r.table,
      label,
      shortName: '项目',
      info: `数据来源：${label}，共 ${r.total} 个项目`,
      partialWhy: r.total > r.table.rows.length ? `符合系统筛选的共 ${r.total} 个项目，只取了前 ${r.table.rows.length} 个` : undefined,
    };
  }

  if (ref === 'page_table') {
    const tables = readPageTables();
    if (!tables.length) return { error: { no_table: true, hint: '当前页面没有读到表格（可能还没加载出来，或者在没打开的标签页里）' } };
    const t = pickPageTable(tables, text(args.table));
    if (!t) return { error: { no_table: true } };
    const extra: Record<string, unknown> = tables.length > 1 ? { tables_on_page: tables.map((x) => `${x.title}（${x.rows.length}行）`) } : {};
    const src = t.partial ? sourceForTable(t) : null;
    if (src) {
      try {
        const r = await fetchSource(src, 'page_filters', signal);
        abortIf(signal);
        const label = `「${t.title}」（${location.pathname}，按页面当前筛选条件取全部）`;
        return {
          table: r.table,
          label,
          shortName: t.title,
          info: `数据来源：${label}，共 ${r.total ?? r.fetched} 条，取到 ${r.fetched} 条`,
          partialWhy: r.truncated ? `共 ${r.total} 条，只取了前 ${r.fetched} 条` : undefined,
          extra: { ...extra, fetched_all_pages: true, data_source_id: src.id },
        };
      } catch (err) {
        if ((err as any)?.name === 'AbortError') throw err;
        if ((err as any)?.status === 401 || (err as any)?.status === 403) throw new ForbiddenError();
        extra.fetch_all_failed = String((err as any)?.message || err).slice(0, 80);
      }
    }
    const label = `当前页面表格「${t.title}」（${location.pathname}）`;
    return { table: t, label, shortName: t.title, info: `数据来源：${label}，读取时页面上显示的 ${t.rows.length} 行`, partialWhy: t.partialWhy, extra };
  }

  const src = findSource(ref);
  if (!src) {
    return {
      error: {
        unknown_source: ref,
        known_sources: sourceCatalog(),
        hint: '这个 id 不在已认识的数据源里。页面名若在「还没打开过的页面」中，直接调用 propose_open_page，不要先问用户',
      },
    };
  }
  const scope = args.scope === 'page_filters' ? 'page_filters' : 'all';
  try {
    const r = await fetchSource(src, scope, signal);
    abortIf(signal);
    const allFilters = allScopeFilterText(src);
    const label = `${src.name}（${src.route}${scope === 'all' ? (allFilters ? `，页面最宽的请求也带着 ${allFilters}` : '') : '，按上次页面筛选'}）`;
    return {
      table: r.table,
      label,
      shortName: src.name.split(' · ').pop() || src.name,
      info: `数据来源：${label}，共 ${r.total ?? r.fetched} 条，取到 ${r.fetched} 条`,
      partialWhy: r.truncated ? `共 ${r.total} 条，只取了前 ${r.fetched} 条` : undefined,
      extra: { data_source_id: src.id },
    };
  } catch (err) {
    if ((err as any)?.name === 'AbortError') throw err;
    if ((err as any)?.status === 401 || (err as any)?.status === 403) throw new ForbiddenError();
    return { error: { error: '取数失败', source: src.name, message: String((err as any)?.message || err).slice(0, 80) } };
  }
}

/** What the pet knows how to fetch, with column names; refreshes column labels from tables on this page. */
function listDataSources() {
  for (const t of readPageTables()) sourceForTable(t);
  return {
    sources: listSources().map((s) => ({
      id: s.id,
      name: s.name,
      page: s.route,
      ...(s.total != null ? { total: s.total } : {}),
      current_page: s.route === location.pathname,
      ...(pageFilterText(s) ? { page_filters: pageFilterText(s) } : {}),
      ...(allScopeFilterText(s) ? { all_scope_filters: allScopeFilterText(s) } : {}),
      columns: sourceColumns(s).slice(0, 50),
      ...(s.joins?.length ? { verified_joins: joinText(s) } : {}),
    })),
    builtin: [{ id: 'projects', name: '免疫项目列表（内置，含中文列名）' }],
    not_opened_pages: unopenedPages().map((p) => p.title),
    note:
      '这些是用户打开过的列表页背后的数据，可在 query_data / build_report 的 source / join.source 里用 id；要的模块在 not_opened_pages 里就用 propose_open_page 请用户打开。' +
      'scope=all 取整个模块（有 all_scope_filters 时是带着这些条件的全部，说数量时要讲明），scope=page_filters 按 page_filters（页面上的标签/筛选，例如状态页签，不一定是某一列的值）取',
  };
}

/** Keeps what the model sees small (long remarks would blow the request size); the file keeps full text. */
function clipRow(row: Row): Row {
  return Object.fromEntries(Object.entries(row).map(([k, v]) => [k, typeof v === 'string' && v.length > 60 ? `${v.slice(0, 60)}…` : v]));
}

const QUERY_ROWS = 20;
const QUERY_COLS = 20;

/** `asFile=false` is query_data: the same spec answered in chat, no card and no 上一份报表. */
async function buildReportTool(args: Record<string, any>, signal?: AbortSignal, asFile = true): Promise<ToolOutcome> {
  const wrap = (obj: unknown): ToolOutcome => ({ content: JSON.stringify(obj) });
  const spec: ReportSpec = {
    title: text(args.title) || undefined,
    where: Array.isArray(args.where) ? args.where : undefined,
    group_by: Array.isArray(args.group_by) ? args.group_by : undefined,
    metrics: Array.isArray(args.metrics) ? args.metrics : undefined,
    columns: Array.isArray(args.columns) ? args.columns : undefined,
    sort: Array.isArray(args.sort) ? args.sort : undefined,
    split_by: text(args.split_by) || undefined,
    limit: Number(args.limit) > 0 ? Number(args.limit) : undefined,
  };
  if (!text(args.source)) {
    return wrap({ error: '缺少 source：projects / page_table / 已认识的数据源 id', known_sources: sourceCatalog() });
  }
  const main = await loadSource(text(args.source), args, signal, true);
  if ('error' in main) return wrap(main.error);
  let table = main.table;
  let source = main.label;
  const partials = main.partialWhy ? [main.partialWhy] : [];
  const info: string[] = [main.info];
  const extra: Record<string, unknown> = { ...main.extra };

  if (args.join && typeof args.join === 'object') {
    const j = args.join;
    const other = await loadSource(text(j.source), {}, signal, false);
    if ('error' in other) return wrap({ join_failed: true, ...other.error });
    const rightName = other.shortName;
    const joinSpec: JoinSpec = { how: j.how || 'left', leftOn: text(j.left_on), rightOn: text(j.right_on || j.left_on), rightName };
    const joined = joinTables(table, other.table, joinSpec);
    if (!joined.ok) {
      const hint =
        joined.error === 'no_match'
          ? '两边一行都没对上，关联列选错了。suggested_keys 是代码按真实数据算出的、值确实能对上的列组合（shared_values 越大越像编号类主键），挑语义合适的一组重试；为空就如实告诉用户两边没有共同字段'
          : '左右两边的关联列都要从各自的 available_columns 里选';
      return wrap({ join_failed: true, ...joined, hint });
    }
    rememberJoin(text(args.source), text(j.source), joinSpec.leftOn, joinSpec.rightOn, joined.matchedLeft, main.table.rows.length);
    table = joined.table;
    source = `${source} 关联 ${other.label}`;
    if (other.partialWhy) partials.push(`关联的${rightName}：${other.partialWhy}`);
    info.push(other.info, `关联方式：${JOIN_TEXT[joinSpec.how]}，按「${joinSpec.leftOn}」=「${joinSpec.rightOn}」，左边 ${joined.matchedLeft} 行对得上`);
    const leftRows = main.table.rows.length;
    extra.join = {
      how: joinSpec.how,
      left_rows: leftRows,
      left_rows_matched: joined.matchedLeft,
      rows_after_join: table.rows.length,
      meaning: `主数据 ${leftRows} 行里有 ${joined.matchedLeft} 行在${rightName}里对得上；关联后 ${table.rows.length} 行，where 条件是在关联之后才筛的，matched 才是最终行数`,
    };
  }
  const partialWhy = partials.join('；') || undefined;

  const built = buildReport(table, spec);
  if (!built.ok) {
    return wrap({
      ...built,
      hint: built.hint ?? (built.available_columns ? UNKNOWN_COLUMN_HINT : undefined),
    });
  }
  const { report, groups, countColumn } = built;
  // More first-level groups than we send: keep the biggest, so "谁最多" is never the one cut off.
  const subtotals =
    built.subtotals && built.subtotals.length > 30 && countColumn
      ? [...built.subtotals].sort((a, b) => (Number(b[countColumn]) || 0) - (Number(a[countColumn]) || 0))
      : built.subtotals;
  if (!report.matched) {
    const valuesSeen = Object.fromEntries(
      (spec.where || [])
        .filter((c) => c.op === '=' || c.op === 'in' || c.op === 'contains')
        .map((c) => [c.column, columnValues(table, c.column)]),
    );
    return wrap({
      empty: true,
      data_rows: report.total,
      matched: 0,
      ...(Object.keys(valuesSeen).length ? { values_seen: valuesSeen } : {}),
      note:
        '按这些条件没有符合的行，没有生成文件。values_seen 是这些列里实际出现的值和行数：条件值写得不对就照它改了重试，别直接回答 0。' +
        '要的是页签类状态（进行中/已结题）而列里没有这个值时，免疫项目改用 source=projects 加 status，别自己拼凑口径',
      ...extra,
    });
  }
  const detail = report.sheets.find((s) => s.name !== '汇总');
  const sendGroups = {
    ...(groups ? { groups: groups.slice(0, 30).map(clipRow), ...(groups.length > 30 ? { groups_total: groups.length } : {}) } : {}),
    ...(subtotals
      ? {
          subtotals: subtotals.slice(0, 30).map(clipRow),
          ...(subtotals.length > 30 ? { subtotals_total: subtotals.length, subtotals_note: '只给了数量最多的 30 个' } : {}),
        }
      : {}),
  };
  const detailRows = (n: number, cols: number) =>
    (detail?.rows ?? []).slice(0, n).map((r) => clipRow(Object.fromEntries(detail!.columns.slice(0, cols).map((c, i) => [c, r[i] ?? null]))));

  if (!asFile) {
    const shown = detailRows(QUERY_ROWS, QUERY_COLS);
    return wrap({
      source,
      data_rows: report.total,
      matched: report.matched,
      ...(partialWhy ? { partial: true, partial_why: partialWhy } : {}),
      ...sendGroups,
      rows: shown,
      ...(detail && detail.rows.length > shown.length ? { rows_total: detail.rows.length } : {}),
      ...(detail && detail.columns.length > QUERY_COLS ? { columns_total: detail.columns.length, columns_note: '只给了前 20 列，要别的列用 columns 指定' } : {}),
      ...extra,
      note:
        '只读查询结果，没有生成文件。matched / groups 是代码算的精确值，直接引用；rows 少于 rows_total 时不要说只有这几条。' +
        '用户要文件时再用 build_report' +
        (partialWhy ? '；数据不是全量，回答里必须说明 partial_why' : ''),
    });
  }

  const me = currentUserName();
  info.unshift(`标题：${report.title}`);
  if (spec.where?.length) info.push(`条件：${describeWhere(spec.where)}`);
  if (spec.group_by?.length) info.push(`分组：${spec.group_by.join('、')}`);
  if (spec.sort?.length) info.push(`排序：${spec.sort.map((s) => `${s.column}${s.desc ? '（降序）' : ''}`).join('、')}`);
  if (spec.limit) info.push(spec.group_by?.length ? `汇总只列前 ${spec.limit} 组（合计行仍是全部）` : `明细只取排序后的前 ${spec.limit} 行`);
  if (spec.split_by) info.push(`按「${spec.split_by}」拆成多个工作表`);
  if (spec.columns?.length) info.push(`明细列：${spec.columns.join('、')}`);
  info.push(`符合条件 ${report.matched} 行（读取到 ${report.total} 行）`);
  info.push(`工作表：${report.sheets.map((s) => `${s.name} ${s.rows.length} 行`).join('，')}`);
  info.push(`生成时间：${nowText()}${me ? `，账号：${me}（只含该账号有权限看到的数据）` : ''}`);
  if (partialWhy) info.push(`注意：不是全量数据——${partialWhy}`);
  info.push('由大肥鱼按提问整理，只读，没有修改系统里的任何数据。');
  lastReport = {
    user: currentUserKey(),
    at: Date.now(),
    args: Object.fromEntries(REPORT_ARG_KEYS.filter((k) => args[k] != null && args[k] !== '').map((k) => [k, args[k]])),
  };

  return {
    content: JSON.stringify({
      proposal_created: true,
      source,
      data_rows: report.total,
      matched: report.matched,
      ...(partialWhy ? { partial: true, partial_why: partialWhy } : {}),
      ...sendGroups,
      ...(detail ? { detail_preview: detailRows(5, 15) } : {}),
      sheets: report.sheets.map((s) => ({ name: s.name, rows: s.rows.length })),
      ...extra,
      note:
        '已生成 Excel 确认卡片，用户点“下载 Excel”才会生成文件，现在还没下载。groups / matched 是代码算的精确值，回答直接引用' +
        (subtotals ? '；subtotals 是按第一个分组列的合计，“哪个月/谁最多”以它为准，groups 只给了部分组时不要自己加总' : '') +
        (partialWhy ? '；数据不是全量，回答里必须说明 partial_why' : ''),
    }),
    proposal: { kind: 'report', report, info, source, partialWhy },
  };
}

export async function runReportProposal(p: Extract<Proposal, { kind: 'report' }>): Promise<string> {
  try {
    const { blob, name } = await reportFile(p.report, p.info);
    downloadBlob(blob, name);
    return `已生成并开始下载：${name}`;
  } catch {
    return '生成 Excel 失败了，稍后再试';
  }
}

/** A module the pet hasn't seen: a card that opens its menu page, so the page's own list request teaches her. */
function proposeOpenPage(args: Record<string, any>): ToolOutcome {
  const wrap = (obj: unknown): ToolOutcome => ({ content: JSON.stringify(obj) });
  const want = text(args.page);
  const learned = findSource(want);
  if (learned) return wrap({ already_known: true, source: learned.id, hint: `已经认识这个模块，直接用 source=${learned.id}` });
  const pages = unopenedPages();
  const page =
    pages.find((p) => p.title === want || p.path === want) ?? pages.find((p) => p.title.includes(want) || want.includes(p.title));
  if (!page) {
    return wrap({
      error: 'no_such_page',
      pages: pages.map((p) => p.title),
      hint: '菜单里没有这个页面：从 pages 里挑名称对得上的重试；都对不上就告诉用户系统菜单里没找到这个模块',
    });
  }
  return {
    content: JSON.stringify({
      proposal_created: true,
      page: page.title,
      note: '已生成“打开页面”卡片：用户点了才会跳过去；页面加载后会自动认识它的列表并接着回答这个问题。现在只告诉用户点卡片，不要编数据。',
    }),
    proposal: { kind: 'open_page', path: page.path, title: page.title },
  };
}

// ---------------- dispatcher ----------------

export async function runPetTool(call: ToolCall, signal?: AbortSignal): Promise<ToolOutcome> {
  const wrap = (obj: unknown): ToolOutcome => ({ content: JSON.stringify(obj) });
  if (call.error) return wrap({ error: `参数无效：${call.error}` });
  if (!hasUserToken()) return wrap({ error: 'not_logged_in' });
  abortIf(signal);
  try {
    switch (call.name) {
      case 'search_projects':
        return wrap(await searchProjects(call.args));
      case 'get_project_progress':
        return wrap(await getProjectProgress(call.args, signal));
      case 'get_project_detail':
        return wrap(await getProjectDetail(call.args, signal));
      case 'get_titer_summary':
        return wrap(await getTiterSummary(call.args, signal));
      case 'check_current_form':
        return wrap(checkCurrentForm());
      case 'propose_form_fill':
        return proposeFormFill(call.args);
      case 'propose_export':
        return await proposeExport(call.args, signal);
      case 'build_report':
        return await buildReportTool(call.args, signal);
      case 'query_data':
        return await buildReportTool(call.args, signal, false);
      case 'list_data_sources':
        return wrap(listDataSources());
      case 'propose_open_page':
        return proposeOpenPage(call.args);
      default:
        return wrap({ error: `未知工具 ${call.name}` });
    }
  } catch (err) {
    if ((err as any)?.name === 'AbortError') throw err;
    if (err instanceof ForbiddenError || isForbidden(err)) return wrap({ error: 'forbidden', message: '当前账号没有权限读取这项数据' });
    return wrap({ error: '查询失败', message: String((err as any)?.message || err).slice(0, 120) });
  }
}
