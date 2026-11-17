/**
 * 客户端驱动的工具循环。pet-proxy（/api/pet/agent）向 DeepSeek 询问下一步，
 * 工具在此使用用户会话执行，方案统一收集到确认卡片。
 */

import type { ChatHistoryItem } from './memory';

import { describeSources } from './apiWatch';
import { scanPageForm } from './formBridge';
import { ambientHint, collectPageContext } from './pageContext';
import { readPageTables } from './pageTable';
import { hasRecentReport, lastReportContext, runPetTool, type Proposal, type ToolCall } from './petTools';
import { currentUserName, menuPages } from './session';

const MAX_STEPS = 10;
/** 除单步限制外设置整次请求时限，避免慢模型让宠物长时间占用。 */
const MAX_TOTAL_MS = 4 * 60_000;
const MAX_TOOL_CHARS = 14_000;

/**
 * 表示需要查询数据而非闲聊的领域词和 ID。
 * 不纳入「状态、几个、表格、检查」等日常词，避免将「你状态怎么样」误送到没有人设的代理路径。
 */
const TASK_HINT =
  /(项目|效价|滴度|titer|elisa|facs|进度|到哪|哪一步|下一步|采血|几免|[一二三四五]免|加强免|导出|下载|excel|拉个?表|清单|汇总|报表|分组|这页的?表|整理|工作表|sheet|求和|平均|合计|去重|占比|关联|联查|工单|表单|填|录入|补全|核对|校验|负责|靶点|小鼠|鼠型|方案|统计|结题|实验\s*id|编号|没(有)?(导出?|下载|生成)|卡片呢|文件呢|表呢)/i;
const ID_HINT = /\b[A-Za-z]{1,6}-?\d{3,}\b/;
/** 感谢、确认和关于宠物的问题绝不视为数据追问。 */
const SMALL_TALK =
  /^(谢谢|谢啦|谢了|多谢|好的?|好嘞|嗯+|哦+|噢+|ok|okay|收到|辛苦了?|厉害|真棒|棒|哈+|知道了|明白了?|行|可以|不用了?|不要了?|算了|没事了?|拜拜|再见|晚安|早安|午安)[!！。.~～啦呀哈谢\s]*$|你(今天|现在)?(心情|状态|饿|累|困|还好|怎么样|好吗|几岁|多大|喜欢|爱吃|吃了|吃饭|在干|开心|无聊)|你是谁|你叫什么|讲个?笑话|陪我聊|聊聊天/i;

/** 仅在上一份报表仍有效时识别「去掉已结题的，再按月拆开」等修改指令。 */
const REPORT_FOLLOWUP =
  /(去掉|去除|排除|剔除|不要.{0,6}的|只要|只看|只留|加一列|再加一列|改成|换成|改为|按.{0,8}(拆|分|排)|按[日天周月季年]|倒序|降序|升序|前\s*\d+|top\s*\d+|百分比|比例)/i;

const MENU_SUFFIX = /(总览|列表|管理|详情|数据|工作台|草稿|情报|库)$/;
const QUERY_WORD = /(多少|几[个条项只家位次]|哪些|哪几|列出|列一下|查一?下|查查|帮我查|有没有|统计|最近|最新|谁(负责|的|在))/;

/** 将菜单名扩展为可识别简称，如「引物库→引物」「合成与验证→合成/验证」。 */
function moduleStems(title: string): string[] {
  return title.split(/[与及和、]/).flatMap((part) => {
    const p = part.trim().replace(MENU_SUFFIX, '');
    return p.length >= 4 ? [p, p.slice(0, 2)] : p.length >= 2 ? [p] : [];
  });
}

/**
 * 完整提及菜单模块时直接视为数据问题。
 * 简称仅在同时出现查询词时生效，避免把「我发现……」等普通表达误判为数据查询。
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
