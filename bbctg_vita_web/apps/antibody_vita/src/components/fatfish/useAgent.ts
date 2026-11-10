/**
 * Client-driven tool loop. pet-proxy (/api/pet/agent) asks DeepSeek for the next step; tools run
 * here with the user's session (petTools.ts). Proposals are collected for confirmation cards.
 */

import type { ChatHistoryItem } from './memory';

import { describeSources } from './apiWatch';
import { scanPageForm } from './formBridge';
import { ambientHint, collectPageContext } from './pageContext';
import { readPageTables } from './pageTable';
import { hasRecentReport, lastReportContext, runPetTool, type Proposal, type ToolCall } from './petTools';
import { currentUserName, menuPages } from './session';

const MAX_STEPS = 10;
/** Whole-request budget on top of the per-step limit, so a slow model can't keep her busy for many minutes. */
const MAX_TOTAL_MS = 4 * 60_000;
const MAX_TOOL_CHARS = 14_000;

/**
 * Domain words / IDs that mean "go look at the data" rather than small talk. Everyday words like 状态/几个/
 * 表格/检查 are left out: "你状态怎么样" is about her, and the agent path has no persona.
 */
const TASK_HINT =
  /(项目|效价|滴度|titer|elisa|facs|进度|到哪|哪一步|下一步|采血|几免|[一二三四五]免|加强免|导出|下载|excel|拉个?表|清单|汇总|报表|分组|这页的?表|整理|工作表|sheet|求和|平均|合计|去重|占比|关联|联查|工单|表单|填|录入|补全|核对|校验|负责|靶点|小鼠|鼠型|方案|统计|结题|实验\s*id|编号|没(有)?(导出?|下载|生成)|卡片呢|文件呢|表呢)/i;
const ID_HINT = /\b[A-Za-z]{1,6}-?\d{3,}\b/;
/** Thanks, acknowledgements and questions about her — never a data follow-up. */
const SMALL_TALK =
  /^(谢谢|谢啦|谢了|多谢|好的?|好嘞|嗯+|哦+|噢+|ok|okay|收到|辛苦了?|厉害|真棒|棒|哈+|知道了|明白了?|行|可以|不用了?|不要了?|算了|没事了?|拜拜|再见|晚安|早安|午安)[!！。.~～啦呀哈谢\s]*$|你(今天|现在)?(心情|状态|饿|累|困|还好|怎么样|好吗|几岁|多大|喜欢|爱吃|吃了|吃饭|在干|开心|无聊)|你是谁|你叫什么|讲个?笑话|陪我聊|聊聊天/i;

/** Edits to the report just made ("去掉已结题的，再按月拆开") — only counted while one is fresh. */
const REPORT_FOLLOWUP =
  /(去掉|去除|排除|剔除|不要.{0,6}的|只要|只看|只留|加一列|再加一列|改成|换成|改为|按.{0,8}(拆|分|排)|按[日天周月季年]|倒序|降序|升序|前\s*\d+|top\s*\d+|百分比|比例)/i;

const MENU_SUFFIX = /(总览|列表|管理|详情|数据|工作台|草稿|情报|库)$/;
const QUERY_WORD = /(多少|几[个条项只家位次]|哪些|哪几|列出|列一下|查一?下|查查|帮我查|有没有|统计|最近|最新|谁(负责|的|在))/;

/** 引物库 → 引物, 合成与验证 → 合成 / 验证, 文库构建 → 文库构建 / 文库. */
function moduleStems(title: string): string[] {
  return title.split(/[与及和、]/).flatMap((part) => {
    const p = part.trim().replace(MENU_SUFFIX, '');
    return p.length >= 4 ? [p, p.slice(0, 2)] : p.length >= 2 ? [p] : [];
  });
}

/**
 * Naming a menu module ("合成与验证里有多少条") is about its data, whatever the other words are.
 * A shortened name ("引物有多少条") only counts next to a query word, so "我发现…" stays small talk.
 */
function mentionsModule(message: string): boolean {
  const asking = QUERY_WORD.test(message);
  return menuPages().some(
    (p) =>
      (p.title.length >= 3 && message.includes(p.title)) ||
      (asking && moduleStems(p.title).some((s) => message.includes(s))),
  );
}

export function looksLikeTask(message: string): boolean {
  return (
    TASK_HINT.test(message) ||
    ID_HINT.test(message) ||
    mentionsModule(message) ||
    (hasRecentReport() && REPORT_FOLLOWUP.test(message))
  );
}

export function looksLikeSmallTalk(message: string): boolean {
  return SMALL_TALK.test(message.trim());
}

export type AgentResult = {
  text?: string;
  voice?: string;
  proposals: Proposal[];
  offline?: boolean;
  aborted?: boolean;
  exhausted?: boolean;
};

export type AgentDeps = {
  message: string;
  history: ChatHistoryItem[];
  memorySummary: string;
  careMood?: string;
  signal: AbortSignal;
  onPhase: (text: string) => void;
};

type FillProposal = Extract<Proposal, { kind: 'fill' }>;

/** Batched propose_form_fill calls build one card; a later value for the same cell wins. */
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
  };
}

export async function runAgent(deps: AgentDeps): Promise<AgentResult> {
  const { message, memorySummary, signal, onPhase } = deps;
  const ctx = collectPageContext();
  // Also count forms the fill tools can see without a plain <input> (selects, dates, table cells behind a save button).
  const form = scanPageForm();
  const interactive = ctx.interactive || (!!form.saveButton && form.fields.length > 0);
  // Table names and columns up front, so a report on this page gets its column names right the first time.
  const tables = readPageTables()
    .slice(0, 3)
    .map((t) => `「${t.title}」（读到 ${t.rows.length} 行${t.total != null ? `，共 ${t.total} 条` : ''}）列：${t.columns.slice(0, 25).join('、')}`);
  const pageSummary = tables.length ? `${ctx.summary}\n页面表格：\n${tables.join('\n')}` : ctx.summary;
  const startedAt = Date.now();
  const requestId = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
  const messages: any[] = [{ role: 'user', content: message }];
  const proposals = new Map<string, Proposal>();
  let waitLabel = '想想怎么做…';

  for (let step = 0; step < MAX_STEPS; step += 1) {
    if (signal.aborted) return { aborted: true, proposals: [] };
    if (Date.now() - startedAt > MAX_TOTAL_MS) break;
    let data: any;
    // Model steps can take 10–40s (decode-bound); show what it's on and a seconds counter so it doesn't look stuck.
    const t0 = Date.now();
    onPhase(waitLabel);
    const ticker = window.setInterval(() => {
      const s = Math.round((Date.now() - t0) / 1000);
      if (s >= 3) onPhase(`${waitLabel} ${s}s`);
    }, 1000);
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
          ambient: ambientHint(),
          user: { name: currentUserName() },
          page: { path: ctx.path, summary: pageSummary, interactive },
          dataSources: describeSources(),
          lastReport: lastReportContext(),
        }),
      });
      data = await res.json().catch(() => null);
      if (!res.ok || !data?.ok) return { offline: true, proposals: [] };
    } catch (err) {
      if ((err as any)?.name === 'AbortError') return { aborted: true, proposals: [] };
      return { offline: true, proposals: [] };
    } finally {
      window.clearInterval(ticker);
    }

    if (data.type === 'final') {
      return { text: String(data.text || '').trim(), voice: data.voice, proposals: [...proposals.values()] };
    }

    messages.push(data.assistant);
    for (const call of (data.calls || []) as ToolCall[]) {
      onPhase(call.phase || '处理中…');
      let content: string;
      try {
        const out = await runPetTool(call, signal);
        content = out.content;
        if (out.proposal) {
          const p = out.proposal;
          // One report card per question: a later build_report (the corrected one) replaces earlier attempts.
          const key = p.kind === 'export' ? `export:${p.exportKind}` : p.kind;
          const prev = proposals.get(key);
          proposals.set(key, prev?.kind === 'fill' && out.proposal.kind === 'fill' ? mergeFill(prev, out.proposal) : out.proposal);
        }
      } catch (err) {
        if ((err as any)?.name === 'AbortError') return { aborted: true, proposals: [] };
        content = JSON.stringify({ error: '工具执行失败' });
      }
      // The proxy rejects bodies over 512KB and only forwards ~14k chars per result anyway.
      if (content.length > MAX_TOOL_CHARS) content = `${content.slice(0, MAX_TOOL_CHARS)}…（结果太长，已截断）`;
      messages.push({ role: 'tool', tool_call_id: call.id, name: call.name, content });
    }
    const names = new Set((data.calls || []).map((c: ToolCall) => c.name));
    waitLabel = names.has('propose_form_fill')
      ? proposals.has('fill') ? '接着整理下一部分…' : '调整填写建议…'
      : names.has('check_current_form') ? '规划要填哪些…' : '整理结果…';
  }
  return { exhausted: true, proposals: [...proposals.values()] };
}
