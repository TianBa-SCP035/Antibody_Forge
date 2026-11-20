/**
 * 客户端驱动的工具循环。pet-proxy（/api/pet/agent）向 DeepSeek 询问下一步，
 * 工具在此使用用户会话执行，方案统一收集到确认卡片。
 */

import type { ChatHistoryItem } from './memory';

import { describeSources } from './apiWatch';
import { scanPageForm } from './formBridge';
import { beginTurn, endTurn, labelOf, pageListing } from './pageAct';
import { ambientHint, collectPageContext } from './pageContext';
import { readPageTables } from './pageTable';
import { lastReportContext, runPetTool, type Proposal, type ToolCall } from './petTools';
import { currentUserName } from './session';

/** 操作页面时一步只点一下，步数要够走完「打开、填、选、确认」这类流程。 */
const MAX_STEPS = 20;
/** 除单步限制外设置整次请求时限，避免慢模型让宠物长时间占用。 */
const MAX_TOTAL_MS = 6 * 60_000;
const MAX_TOOL_CHARS = 14_000;
const STEPS_USED_UP = '这一轮的操作步数用完了，没有执行。停下来如实告诉用户做到了哪一步、还差什么';
/** 每步都会重发整轮消息，只保留最近几张图片，更早的换成文字说明。 */
const KEEP_IMAGES = 2;

export type AgentResult = {
  text?: string;
  voice?: string;
  proposals: Proposal[];
  /** 这一轮实际调用过的工具（含参数和结果概况），记进对话记录。 */
  actions?: string[];
  offline?: boolean;
  aborted?: boolean;
  exhausted?: boolean;
};

export type AgentDeps = {
  message: string;
  history: ChatHistoryItem[];
  memorySummary: string;
  careMood?: string;
  /** 屏幕上还等用户点的卡片标题；代理据此判断「点卡片」这类说法是否属实。 */
  openCards: string[];
  /** 用户随问题贴的图片（data URL）。 */
  images?: string[];
  signal: AbortSignal;
  onPhase: (text: string) => void;
  /** 宠物动过页面后用户自己点了或按了页面：交还给用户。 */
  onTakeover: () => void;
};

type FillProposal = Extract<Proposal, { kind: 'fill' }>;

/** 多次 propose_form_fill 调用合并为一张卡片，同一单元格以后一次值为准。 */
function mergeFill(a: FillProposal, b: FillProposal): FillProposal {
  const keyOf = (f: { table?: string; row?: number; field: string }) => `${f.table || ''}|${f.row || 0}|${f.field}`;
  const fills = new Map(a.fills.map((f) => [keyOf(f), f]));
  for (const f of b.fills) {
    fills.delete(keyOf(f));
    fills.set(keyOf(f), f);
  }
  const manual = new Map([...a.manual, ...b.manual].map((m) => [m.label, m]));
  for (const f of fills.values()) manual.delete(f.table ? `${f.table} 第${f.row}行 ${f.field}` : f.field);
  return {
    ...a,
    fills: [...fills.values()],
    manual: [...manual.values()],
    autoSave: a.autoSave || b.autoSave,
    newRecord: a.newRecord || b.newRecord,
    formLabels: a.formLabels?.length ? a.formLabels : b.formLabels,
    page: b.page,
  };
}

/** 当前页面的概况；每步重新取，宠物点了菜单跳到别的页面后，模型拿到的是新页面。 */
function pageNow(first: boolean) {
  const ctx = collectPageContext();
  // 还需识别填写工具可见但没有普通 input 的表单，如下拉框、日期框和保存按钮后的表格单元格。
  const form = scanPageForm();
  const interactive = ctx.interactive || (!!form.saveButton && form.fields.length > 0);
  // 预先提供表名和列名，使当前页报表首次生成时即可使用正确列名。
  const tables = readPageTables()
    .slice(0, 3)
    .map((t) => `「${t.title}」（读到 ${t.rows.length} 行${t.total != null ? `，共 ${t.total} 条` : ''}）列：${t.columns.slice(0, 25).join('、')}`);
  const summary = tables.length ? `${ctx.summary}\n页面表格：\n${tables.join('\n')}` : ctx.summary;
  return { path: ctx.path, summary, interactive, ...(first ? { listing: pageListing() } : {}) };
}

export async function runAgent(deps: AgentDeps): Promise<AgentResult> {
  // 用户停止和整轮时限共用一个停止信号：到点时正在等的模型请求、页面操作和提交确认一起停下。
  const ctrl = new AbortController();
  const stop = () => ctrl.abort();
  deps.signal.addEventListener('abort', stop);
  if (deps.signal.aborted) ctrl.abort();
  let timedOut = false;
  const deadline = window.setTimeout(() => {
    timedOut = true;
    ctrl.abort();
  }, MAX_TOTAL_MS);
  const turn: Turn = { no: 0, render: () => {} };
  // 秒数整轮都在走：模型解码、页面操作、等用户点卡片时都不会看起来像卡死。
  const ticker = window.setInterval(() => turn.render(), 1000);
  try {
    const result = await runSteps({ ...deps, signal: ctrl.signal }, turn);
    if (timedOut && result.aborted && !deps.signal.aborted) return { exhausted: true, proposals: result.proposals, actions: result.actions };
    return result;
  } finally {
    window.clearInterval(ticker);
    window.clearTimeout(deadline);
    deps.signal.removeEventListener('abort', stop);
    endTurn(turn.no);
  }
}

type Turn = { no: number; render: () => void };

async function runSteps(deps: AgentDeps, turn: Turn): Promise<AgentResult> {
  const { message, memorySummary, signal, onPhase } = deps;
  const startedAt = Date.now();
  const requestId = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
  const messages: any[] = [{ role: 'user', content: message, ...(deps.images?.length ? { images: deps.images } : {}) }];
  const proposals = new Map<string, Proposal>();
  const actions: string[] = [];
  const stopped = (): AgentResult => ({ aborted: true, proposals: [...proposals.values()], actions });
  let waitLabel = '想想怎么做…';
  // 第几步、在做什么、一共用了多久；多步操作时用户能看到进展，随时可以点停。
  let stepNo = 0;
  let current = waitLabel;
  const elapsed = () => Math.round((Date.now() - startedAt) / 1000);
  const render = () => onPhase(`${stepNo ? `第${stepNo}步 · ` : ''}${current}${elapsed() >= 5 ? ` · ${elapsed()}s` : ''}`);
  const show = (text: string) => {
    current = text;
    render();
  };
  turn.render = render;
  turn.no = beginTurn(signal, show, deps.onTakeover);

  for (let step = 0; step < MAX_STEPS; step += 1) {
    if (signal.aborted) return stopped();
    let data: any;
    show(waitLabel);
    try {
      const res = await fetch('/api/pet/agent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal,
        body: JSON.stringify({
          requestId,
          step,
          maxSteps: MAX_STEPS,
          messages,
          history: deps.history,
          memorySummary,
          careMood: deps.careMood || '',
          openCards: deps.openCards,
          ambient: ambientHint(),
          user: { name: currentUserName() },
          page: pageNow(step === 0),
          dataSources: describeSources(),
          lastReport: lastReportContext(),
        }),
      });
      data = await res.json().catch(() => null);
      if (!res.ok || !data?.ok) return { offline: true, proposals: [], actions };
    } catch (err) {
      if ((err as any)?.name === 'AbortError') return stopped();
      return { offline: true, proposals: [], actions };
    }

    if (data.type === 'final') {
      return { text: String(data.text || '').trim(), voice: data.voice, proposals: [...proposals.values()], actions };
    }

    messages.push(data.assistant);
    const said = String(data.assistant?.content || '').trim();
    for (const call of (data.calls || []) as ToolCall[]) {
      // 模型一次可以要好几个工具，步数按实际执行的工具算。
      if (stepNo >= MAX_STEPS) {
        messages.push({ role: 'tool', tool_call_id: call.id, name: call.name, content: JSON.stringify({ error: STEPS_USED_UP }) });
        continue;
      }
      stepNo += 1;
      show(stepText(call) || (said ? said.slice(0, 40) : call.phase || '处理中…'));
      let content: string;
      let images: string[] | undefined;
      try {
        const out = await runPetTool(call, signal);
        content = out.content;
        images = out.images;
        if (out.proposal) {
          const p = out.proposal;
          // 每个问题只保留一张报表卡片，后续修正后的 build_report 替换先前尝试。
          const key = p.kind === 'export' ? `export:${p.exportKind}` : p.kind;
          const prev = proposals.get(key);
          proposals.set(key, prev?.kind === 'fill' && out.proposal.kind === 'fill' ? mergeFill(prev, out.proposal) : out.proposal);
        }
      } catch (err) {
        if ((err as any)?.name === 'AbortError') return stopped();
        content = JSON.stringify({ error: '工具执行失败' });
      }
      // 代理拒绝超过 8MB 的请求体，且每个结果最多转发约 1.4 万字符。
      if (content.length > MAX_TOOL_CHARS) content = `${content.slice(0, MAX_TOOL_CHARS)}…（结果太长，已截断）`;
      messages.push({ role: 'tool', tool_call_id: call.id, name: call.name, content, ...(images?.length ? { images } : {}) });
      actions.push(describeAction(call, content));
    }
    pruneImages(messages);
    const names = new Set((data.calls || []).map((c: ToolCall) => c.name));
    waitLabel = names.has('propose_form_fill')
      ? proposals.has('fill') ? '接着整理下一部分…' : '调整填写建议…'
      : names.has('check_current_form') ? '规划要填哪些…' : [...names].some((n) => PAGE_STEPS[n as string]) ? '看看下一步…' : '整理结果…';
  }
  return { exhausted: true, proposals: [...proposals.values()], actions };
}

const PAGE_STEPS: Record<string, string> = {
  click: '点',
  type_text: '填写',
  choose_option: '选择',
  hover: '鼠标移到',
  drag: '拖动',
  point_at: '指出',
  look_at: '看看',
  scroll: '滚动到',
  read_page: '读页面',
  press_key: '按键',
};

/** 页面操作的进度说法：说清对哪个元素做了什么，比如「点按钮「保存」」。 */
function stepText(call: ToolCall): string {
  const verb = PAGE_STEPS[call.name];
  if (!verb) return '';
  const a = call.args || {};
  if (call.name === 'read_page') return a.keyword ? `在页面上找「${a.keyword}」` : '读页面';
  if (call.name === 'press_key') return `按 ${a.key}`;
  const target = a.ref ? labelOf(a.ref) : '';
  if (call.name === 'type_text') return `${target ? `在${target}` : ''}输入「${String(a.text ?? '').slice(0, 16)}」`;
  if (call.name === 'choose_option') return `${target ? `在${target}` : ''}选「${String(a.option ?? '').slice(0, 16)}」`;
  if (call.name === 'look_at') return target ? `看${target}` : '看看页面';
  return target ? `${verb}${target}` : verb;
}

function pruneImages(messages: any[]) {
  let kept = 0;
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const m = messages[i];
    if (!m.images?.length || m.role === 'user') continue;
    if (kept + m.images.length <= KEEP_IMAGES) {
      kept += m.images.length;
      continue;
    }
    delete m.images;
    m.content = `${m.content}\n（这次附的图片已省略，需要再看就重新截图）`;
  }
}

const PAGE_ACTS = new Set(['click', 'type_text', 'choose_option', 'hover', 'drag', 'scroll', 'press_key']);

/** 一次工具调用的概况：条件原样保留，下一轮改口径时能在上面改。 */
function describeAction(call: ToolCall, content: string): string {
  let out: any = null;
  try {
    out = JSON.parse(content);
  } catch {
    /* 截断的结果不是合法 JSON，只记调用本身。 */
  }
  const args = JSON.stringify(call.args ?? {});
  // 页面编号下一轮就失效了；记下操作对象和改前的值，用户说“改回去”时有据可依。
  const what =
    PAGE_ACTS.has(call.name) && typeof out?.done === 'string' ? ` ${out.done.slice(0, 120)}` : args.length > 2 ? ` ${args.slice(0, 240)}` : '';
  const result = !out
    ? ''
    : out.error
      ? ` → 出错：${String(out.error).slice(0, 60)}`
      : Array.isArray(out.held_writes)
        ? ` → 提交：${out.held_writes
            .map((w: any) => `${w.request} ${w.decision}${w.status != null ? `，系统返回 ${w.status} ${String(w.response || '').slice(0, 60)}` : ''}`)
            .join('；')}`
        : out.page_changed_to
          ? ` → 跳到 ${out.page_changed_to}`
          : out.proposal_created
        ? ' → 出了卡片'
        : out.empty || out.not_found
          ? ' → 没有结果'
          : out.matched != null
            ? ` → ${out.matched} 行`
            : '';
  return `${call.name}${what}${result}`;
}
