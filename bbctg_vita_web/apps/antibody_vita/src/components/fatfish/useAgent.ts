/**
 * 客户端驱动的工具循环。pet-proxy（/api/pet/agent）向 DeepSeek 询问下一步，
 * 工具在此使用用户会话执行，方案统一收集到确认卡片。
 */

import type { ChatHistoryItem } from './memory';

import { describeSources } from './apiWatch';
import { scanPageForm } from './formBridge';
import { ambientHint, collectPageContext } from './pageContext';
import { readPageTables } from './pageTable';
import { lastReportContext, runPetTool, type Proposal, type ToolCall } from './petTools';
import { currentUserName } from './session';

const MAX_STEPS = 10;
/** 除单步限制外设置整次请求时限，避免慢模型让宠物长时间占用。 */
const MAX_TOTAL_MS = 4 * 60_000;
const MAX_TOOL_CHARS = 14_000;

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
  };
}

export async function runAgent(deps: AgentDeps): Promise<AgentResult> {
  const { message, memorySummary, signal, onPhase } = deps;
  const ctx = collectPageContext();
  // 还需识别填写工具可见但没有普通 input 的表单，如下拉框、日期框和保存按钮后的表格单元格。
  const form = scanPageForm();
  const interactive = ctx.interactive || (!!form.saveButton && form.fields.length > 0);
  // 预先提供表名和列名，使当前页报表首次生成时即可使用正确列名。
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
    // 模型单步可能因解码耗时 10 至 40 秒，需显示当前阶段和秒数，避免看似卡死。
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
          // 每个问题只保留一张报表卡片，后续修正后的 build_report 替换先前尝试。
          const key = p.kind === 'export' ? `export:${p.exportKind}` : p.kind;
          const prev = proposals.get(key);
          proposals.set(key, prev?.kind === 'fill' && out.proposal.kind === 'fill' ? mergeFill(prev, out.proposal) : out.proposal);
        }
      } catch (err) {
        if ((err as any)?.name === 'AbortError') return { aborted: true, proposals: [] };
        content = JSON.stringify({ error: '工具执行失败' });
      }
      // 代理拒绝超过 512KB 的请求体，且每个结果最多转发约 1.4 万字符。
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
