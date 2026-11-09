/** Chat / wait-bubble / abort / memory compress / agent + confirmation-card wiring. */

import { ref, type Ref } from 'vue';

import { ambientHint, collectPageContext } from './pageContext';
import { LINES } from './lines';
import { QA_KEEP } from './constants';
import {
  loadMemorySummary,
  loadQa,
  loadTurnsSinceCompress,
  olderTurnsForCompress,
  requestCompress,
  saveMemorySummary,
  saveQa,
  saveTurnsSinceCompress,
  shouldCompress,
  toRecentHistory,
  type QaItem,
} from './memory';
import type { FillSnapshot } from './formBridge';
import { formLabels, sameForm } from './formBridge';
import { openAndLearn } from './apiWatch';
import { applyFillProposal, runExportProposal, runReportProposal, undoFillProposal, type Proposal } from './petTools';
import { looksLikeSmallTalk, looksLikeTask, runAgent } from './useAgent';
import type { CareEvent } from './useCare';

export type BubbleKind = 'pet' | 'user' | 'sys' | 'wait' | 'card';
export type ChatIntent = 'chat' | 'comment' | 'fill';
export type CardAction = { id: 'apply' | 'export' | 'open' | 'cancel' | 'undo'; label: string; primary?: boolean };
export type PetBubble = {
  id: number;
  text: string;
  kind: BubbleKind;
  sticky?: boolean;
  title?: string;
  actions?: CardAction[];
  note?: string;
  working?: boolean;
};
export type CardInput = Pick<PetBubble, 'text' | 'title' | 'actions'>;

const FILL_PROMPT =
  '先检查我当前页面的表单：哪些必填没填、哪些有校验错误。如果能从页面信息或我提到的项目里确定某些字段该填什么，就给出填写建议（不要提交）。';

const STOP_HINT = '（点停）';
const SHORT_ANSWER = 70;
/** Replies right after a data answer ("BALB/c，5只") keep going to the agent. */
const AGENT_FOLLOW_UP_MS = 3 * 60_000;
/** Words that clearly ask for a file. "表格" / "清单" alone are left out: "看看这页的表格" is not a download request. */
const EXPORT_INTENT = /导出|下载|excel|xlsx|拉个?表|出个?表|导个?表|做个?表/i;
const UNDO_WINDOW_MS = 30_000;

export function useChat(deps: {
  busy: Ref<boolean>;
  sleeping: Ref<boolean>;
  chatOpen: Ref<boolean>;
  say: (text: string, kind?: BubbleKind) => number;
  addCard: (card: CardInput) => number;
  pick: <T extends string>(pool: readonly T[]) => T;
  playAnim: (key: string, opts?: { loop?: boolean; restart?: boolean }) => Promise<void> | void;
  onCare: (event: CareEvent, amount?: number) => void;
  careMoodHint: () => string;
  armSore: (ms?: number) => void;
  pokeIdleClock: () => void;
  closeChatDialog: () => void;
  focusInput: () => void;
  bubbles: Ref<PetBubble[]>;
}) {
  const qaHistory = ref<QaItem[]>(loadQa());
  const memorySummary = ref(loadMemorySummary());
  let qaSeq = Math.max(1, qaHistory.value.length + 1);
  let chatAbort: AbortController | null = null;
  let waitBubbleId: number | undefined;
  let waitRotateTimer: number | undefined;
  let turnsSinceCompress = loadTurnsSinceCompress();
  let lastAgentAt = 0;
  const lastUserQuestion = ref('');
  const retriedForQuestion = ref('');
  const cardProposals = new Map<number, Proposal>();
  /** Page a fill card was made for; applying it anywhere else could hit look-alike fields. */
  const cardPages = new Map<number, string>();
  const fillUndo = new Map<number, FillSnapshot[]>();
  const pageKey = () => location.pathname + location.search + location.hash;
  const HAS_ID = /[?&][\w-]*id=/i;
  /** Same page as `asked`, allowing for a new record whose id the page adds to the URL once it auto-saves. */
  function stillSamePage(asked: string) {
    if (asked === pageKey()) return true;
    const [askedPath, askedQuery = ''] = asked.split('?');
    return askedPath === location.pathname && !HAS_ID.test(`?${askedQuery}`) && HAS_ID.test(location.search);
  }

  function saveQaNow() {
    saveQa(qaHistory.value);
  }

  function pushQa(role: QaItem['role'], text: string) {
    const clean = String(text || '').trim();
    if (!clean) return;
    qaHistory.value = [...qaHistory.value.slice(-(QA_KEEP - 1)), { id: qaSeq++, role, text: clean }];
    saveQaNow();
  }

  function patchBubble(id: number, patch: Partial<PetBubble>) {
    const idx = deps.bubbles.value.findIndex((b) => b.id === id);
    if (idx < 0) return;
    const next = [...deps.bubbles.value];
    next[idx] = { ...next[idx]!, ...patch };
    deps.bubbles.value = next;
  }

  function removeBubble(id: number) {
    deps.bubbles.value = deps.bubbles.value.filter((b) => b.id !== id);
    cardProposals.delete(id);
    cardPages.delete(id);
    fillUndo.delete(id);
  }

  function clearWaitBubble() {
    if (waitBubbleId != null) {
      removeBubble(waitBubbleId);
      waitBubbleId = undefined;
    }
    window.clearInterval(waitRotateTimer);
    waitRotateTimer = undefined;
  }

  function patchWaitText(text: string) {
    if (waitBubbleId != null) patchBubble(waitBubbleId, { text });
  }

  function showWaitBubble(agentMode: boolean) {
    clearWaitBubble();
    if (agentMode) {
      waitBubbleId = deps.say(`想想怎么查… ${STOP_HINT}`, 'wait');
      return;
    }
    waitBubbleId = deps.say(`${deps.pick(LINES.think)} ${STOP_HINT}`, 'wait');
    waitRotateTimer = window.setInterval(() => {
      if (!deps.busy.value || waitBubbleId == null) {
        clearWaitBubble();
        return;
      }
      patchWaitText(`${deps.pick(LINES.think)} ${STOP_HINT}`);
    }, 2200);
  }

  function abortChat() {
    if (!deps.busy.value && !chatAbort) return;
    try {
      chatAbort?.abort();
    } catch {
      /* ignore */
    }
    chatAbort = null;
    clearWaitBubble();
    deps.busy.value = false;
    void deps.playAnim(deps.pick(['sigh', 'pokeShy', 'look'] as const));
    deps.say(deps.pick(LINES.cancelled));
    deps.pokeIdleClock();
  }

  async function maybeRunCompress() {
    const summary = memorySummary.value;
    if (!shouldCompress(qaHistory.value.length, turnsSinceCompress, summary)) return;
    const older = olderTurnsForCompress(qaHistory.value);
    if (!older.length) return;
    const next = await requestCompress(summary, older);
    if (next) {
      memorySummary.value = next;
      saveMemorySummary(next);
      turnsSinceCompress = 0;
      saveTurnsSinceCompress(0);
    }
  }

  function rememberReply(text: string) {
    const retrying =
      retriedForQuestion.value && lastUserQuestion.value && retriedForQuestion.value === lastUserQuestion.value;
    const lastPet = retrying ? [...qaHistory.value].reverse().find((r) => r.role === 'pet') : undefined;
    if (lastPet) {
      lastPet.text = text;
      saveQaNow();
    } else {
      pushQa('pet', text);
    }
    turnsSinceCompress += 1;
    saveTurnsSinceCompress(turnsSinceCompress);
  }

  function celebrate(event: 'chat' | 'task') {
    deps.onCare(event);
    deps.armSore(12000);
    // A finished task costs her a little satiety ("吃 Token"), so sometimes that is what she does.
    const pool = event === 'task' ? (['celebrate', 'pokeHappy', 'eatToken'] as const) : (['pokeHappy', 'celebrate', 'curtsy'] as const);
    void deps.playAnim(deps.pick(pool));
  }

  function proposalCard(p: Proposal): CardInput {
    if (p.kind === 'fill') {
      const parts: string[] = [];
      let group = '';
      for (const f of p.fills) {
        const head = f.table ? `${f.table.replace(/\s*\([^)]*\)/g, '')} 第${f.row}行` : '';
        if (head !== group) {
          parts.push(head ? `【${head}】` : '【基本信息】');
          group = head;
        }
        parts.push(`· ${f.field}：${f.display}${f.reason ? `（${f.reason}）` : ''}`);
      }
      if (p.manual.length) {
        parts.push('需要你手动处理：', ...p.manual.map((m) => `· ${m.label}：${m.value}（${m.why}）`));
      }
      if (p.newRecord && p.fills.length) {
        parts.unshift('注意：这是新建页，点应用后页面会自动新建一条记录。撤销只能把字段改回去，删不掉这条记录和自动加的行，确定要建再点。');
      } else if (p.autoSave && p.fills.length) {
        parts.unshift('注意：这个页面会自动保存，点应用后几秒内就会写进系统。');
      }
      return {
        title: p.newRecord ? '填写建议（应用后会新建记录）' : p.autoSave ? '填写建议（此页会自动保存）' : '填写建议（不会提交）',
        text: parts.join('\n'),
        actions: p.fills.length
          ? [
              { id: 'apply', label: p.autoSave ? `应用 ${p.fills.length} 项并自动保存` : `应用 ${p.fills.length} 项`, primary: true },
              { id: 'cancel', label: '算了' },
            ]
          : [{ id: 'cancel', label: '知道了' }],
      };
    }
    if (p.kind === 'open_page') {
      return {
        title: `打开「${p.title}」`,
        text:
          '这个模块我还没见过它的数据。打开后页面会照常加载列表，我跟着认识它' +
          (p.question ? `，然后接着回答：${p.question}` : '。'),
        actions: [
          { id: 'open', label: '打开页面', primary: true },
          { id: 'cancel', label: '不用了' },
        ],
      };
    }
    if (p.kind === 'report') {
      const first = p.report.sheets[0];
      const preview = first
        ? [first.columns.join(' | '), ...first.rows.slice(0, 3).map((r) => r.map((v) => v ?? '').join(' | '))]
        : [];
      return {
        title: `生成 Excel：${p.report.title}`,
        text: [
          p.source,
          `符合条件 ${p.report.matched} 行`,
          ...p.report.sheets.map((s) => `· 工作表「${s.name}」${s.rows.length} 行`),
          p.partialWhy ? `注意：不是全量数据——${p.partialWhy}` : '',
          preview.length ? `预览：\n${preview.join('\n')}` : '',
        ]
          .filter(Boolean)
          .join('\n'),
        actions: [
          { id: 'export', label: '下载 Excel', primary: true },
          { id: 'cancel', label: '取消' },
        ],
      };
    }
    return {
      title: '导出 Excel',
      text: `${p.label}${p.count != null ? `\n共 ${p.count} 个项目` : ''}`,
      actions: [
        { id: 'export', label: '确认导出', primary: true },
        { id: 'cancel', label: '取消' },
      ],
    };
  }

  /** `askedOn`: the page the question was asked on; a fill card made for it must not apply to a page opened meanwhile. */
  function showAgentAnswer(
    text: string,
    voice: string | undefined,
    proposals: Proposal[],
    askedOn: string,
    askedToExport: boolean,
  ) {
    celebrate('task');
    if (text) {
      if (voice) deps.say(voice);
      if (text.length <= SHORT_ANSWER && !text.includes('\n')) deps.say(text);
      else deps.addCard({ text });
      rememberReply(text);
    }
    for (const p of proposals) {
      // Downloads skip the card only when the user asked for one; an export the model chose on its own
      // (or was talked into by text inside the data) still waits for a click.
      if (p.kind === 'export' && p.auto && askedToExport) {
        void (async () => {
          deps.say(`正在导出：${p.label}${p.count != null ? `（${p.count}）` : ''}`);
          const note = await runExportProposal(p);
          deps.say(note);
        })();
        continue;
      }
      // Offering the same page again (the model re-mentioning its card) keeps the first card and its question.
      if (p.kind === 'open_page' && [...cardProposals.values()].some((q) => q.kind === 'open_page' && q.path === p.path)) {
        continue;
      }
      const id = deps.addCard(proposalCard(p));
      cardProposals.set(id, p);
      cardPages.set(id, askedOn);
    }
    void maybeRunCompress();
  }

  /** `keep`: leave the card up (the note lists things the user still has to fix). */
  function finishCard(id: number, note: string, keep = false) {
    patchBubble(id, { actions: [], note, working: false });
    cardProposals.delete(id);
    cardPages.delete(id);
    fillUndo.delete(id);
    if (!keep) window.setTimeout(() => removeBubble(id), 6000);
  }

  async function onCardAction(id: number, action: CardAction['id'] | 'close') {
    const p = cardProposals.get(id);
    if (action === 'close' || !p) {
      removeBubble(id);
      return;
    }
    if (action === 'cancel') {
      finishCard(id, '已取消');
      return;
    }
    if (p.kind === 'fill' && (action === 'apply' || action === 'undo') && !stillSamePage(cardPages.get(id) ?? '')) {
      finishCard(id, '页面已经换了，这张建议作废，回到原页面再让我看一次', true);
      return;
    }
    if (p.kind === 'fill' && action === 'apply' && !sameForm(p.formLabels, formLabels())) {
      finishCard(id, '页面上的表单已经换了（可能开了别的弹窗），这张建议作废，再让我看一次', true);
      return;
    }
    if (p.kind === 'fill' && action === 'apply') {
      patchBubble(id, { working: true, note: '填写中…' });
      const { applied, missed, overridden, snapshots } = await applyFillProposal(p.fills);
      // The page's own auto-save sends the request; we can't see whether it succeeded, so don't claim it did.
      const savedHint = p.autoSave
        ? '已写入页面，页面会自己保存（是否保存成功以页面提示为准），不对就点撤销'
        : '还没保存，检查后自己点保存';
      const lines = [
        applied.length ? `已填入 ${applied.length} 项（蓝框闪一下的就是），${savedHint}` : '一项都没填进去，表单可能已经变了',
        missed.length ? `没对上：${missed.join('、')}` : '',
        overridden.length ? `被页面联动改掉了：${overridden.map((o) => `${o.label}→${o.now}`).join('、')}` : '',
      ];
      const note = lines.filter(Boolean).join('\n');
      const keep = !!(missed.length || overridden.length || p.manual.length);
      if (applied.length) void deps.playAnim('celebrate');
      if (!snapshots.length) {
        finishCard(id, note, keep);
        return;
      }
      // Keep an undo button for a while; the card leaves on its own unless something still needs fixing.
      fillUndo.set(id, snapshots);
      patchBubble(id, { working: false, note, actions: [{ id: 'undo', label: '撤销这次填写' }] });
      if (!keep) {
        window.setTimeout(() => {
          if (fillUndo.has(id)) {
            cardProposals.delete(id);
            fillUndo.delete(id);
            removeBubble(id);
          }
        }, p.autoSave ? UNDO_WINDOW_MS * 2 : UNDO_WINDOW_MS);
      }
      return;
    }
    if (p.kind === 'fill' && action === 'undo') {
      const snaps = fillUndo.get(id);
      if (!snaps) return;
      patchBubble(id, { working: true, note: '撤销中…' });
      const { restored, skipped, changedSince } = await undoFillProposal(snaps);
      const lines = [
        `已恢复 ${restored} 项${p.autoSave && restored ? '，页面会自己保存恢复后的值（以页面提示为准）' : ''}`,
        changedSince.length ? `填完后又被改过的没动（保留现在的值）：${changedSince.join('、')}` : '',
        skipped.length ? `新加的行或找不到的格子需要你手动处理：${skipped.join('、')}` : '',
      ];
      finishCard(id, lines.filter(Boolean).join('\n'), !!(skipped.length || changedSince.length));
      return;
    }
    if (p.kind === 'export' && action === 'export') {
      patchBubble(id, { working: true, note: '导出中…' });
      finishCard(id, await runExportProposal(p));
      return;
    }
    if (p.kind === 'report' && action === 'export') {
      patchBubble(id, { working: true, note: '生成中…' });
      finishCard(id, await runReportProposal(p));
      return;
    }
    if (p.kind === 'open_page' && action === 'open') {
      patchBubble(id, { working: true, note: '打开中…' });
      const src = await openAndLearn(p.path);
      if (!src) {
        finishCard(id, '页面打开了，但还没认出列表数据（可能要先点查询或选个页签），弄好后再问我一次', true);
        return;
      }
      finishCard(id, `认识「${p.title}」了${p.question ? '，接着回答' : ''}`);
      if (p.question) void chat(p.question, 'chat', true);
    }
  }

  /** `forceAgent`: a data question asked again after the pet learned the page it needed. */
  async function chat(message: string, intent: ChatIntent = 'chat', forceAgent = false) {
    if (deps.busy.value) return;
    deps.busy.value = true;
    deps.sleeping.value = false;
    void deps.playAnim(deps.pick(['think', 'mutter', 'code', 'busy'] as const), { loop: true, restart: true });
    // "谢谢" or "你累吗" right after a data answer is still small talk, not a follow-up question.
    const followUp = Date.now() - lastAgentAt < AGENT_FOLLOW_UP_MS && !looksLikeSmallTalk(message);
    const agentMode = forceAgent || intent === 'fill' || (intent === 'chat' && (looksLikeTask(message) || followUp));
    const fromDialog = deps.chatOpen.value && intent === 'chat';
    showWaitBubble(agentMode);
    const abort = new AbortController();
    chatAbort = abort;
    const askedOn = pageKey();
    const recentHistory = toRecentHistory(qaHistory.value, message);
    try {
      const askAgent = async () => {
        const result = await runAgent({
          message: intent === 'fill' ? FILL_PROMPT : message,
          history: recentHistory,
          memorySummary: memorySummary.value || '',
          careMood: deps.careMoodHint(),
          signal: abort.signal,
          onPhase: (phase) => patchWaitText(`${phase} ${STOP_HINT}`),
        });
        clearWaitBubble();
        // Stop clicked while the last step was already on its way back: drop the answer, cards and auto-export.
        if (result.aborted || abort.signal.aborted) return;
        if (result.offline) {
          void deps.playAnim('sigh');
          deps.say(deps.pick(LINES.offline), 'sys');
          return;
        }
        if (result.exhausted && !result.proposals.length) {
          deps.onCare('taskFail');
          void deps.playAnim('sigh');
          deps.say('翻了好几轮还没理清…换个说法，或者直接给我实验ID？');
          return;
        }
        lastAgentAt = Date.now();
        for (const p of result.proposals) if (p.kind === 'open_page' && intent === 'chat') p.question = message;
        showAgentAnswer(result.text || '', result.voice, result.proposals, askedOn, EXPORT_INTENT.test(message));
      };
      if (agentMode) {
        await askAgent();
        return;
      }

      const res = await fetch('/api/pet/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: abort.signal,
        body: JSON.stringify({
          message,
          intent,
          memorySummary: memorySummary.value || '',
          recentHistory,
          pageContext: collectPageContext().summary,
          careMood: deps.careMoodHint(),
          ambient: ambientHint(),
        }),
      });
      const data = res.ok ? await res.json().catch(() => null) : null;
      clearWaitBubble();
      if (abort.signal.aborted) return;
      if (data?.reroute === 'agent') {
        // Small-talk model drifted into "I filled / exported it" — it has no tools, so let the agent actually do it.
        showWaitBubble(true);
        await askAgent();
        return;
      }
      if (!data?.ok || !data.reply) {
        void deps.playAnim('sigh');
        deps.say(deps.pick(LINES.offline), 'sys');
        return;
      }
      celebrate('chat');
      deps.say(String(data.reply));
      if (intent === 'chat') rememberReply(String(data.reply));
      void maybeRunCompress();
    } catch (err) {
      clearWaitBubble();
      if ((err as { name?: string })?.name !== 'AbortError') {
        void deps.playAnim('scare');
        deps.say(deps.pick(LINES.error));
      }
    } finally {
      // After a stop, abortChat() already reset everything — and a newer chat may own the state by now.
      if (!abort.signal.aborted) {
        chatAbort = null;
        clearWaitBubble();
        deps.busy.value = false;
        deps.pokeIdleClock();
        if (deps.chatOpen.value) {
          if (fromDialog) deps.focusInput();
          else window.setTimeout(() => deps.closeChatDialog(), 700);
        }
      }
    }
  }

  function noteUserQuestion(text: string) {
    lastUserQuestion.value = text;
    if (retriedForQuestion.value && retriedForQuestion.value !== text) retriedForQuestion.value = '';
    pushQa('user', text);
  }

  async function maybeRetryAnswer() {
    if (!lastUserQuestion.value) return false;
    if (retriedForQuestion.value === lastUserQuestion.value) return false;
    if (!lastUserQuestion.value.trim()) return false;
    retriedForQuestion.value = lastUserQuestion.value;
    deps.say(deps.pick(LINES.retry));
    await chat(lastUserQuestion.value, 'chat');
    return true;
  }

  /** Another account signed in (or out) without a page reload: drop this account's talk and cards, load the next one's. */
  function reloadForUser() {
    try {
      chatAbort?.abort();
    } catch {
      /* ignore */
    }
    chatAbort = null;
    clearWaitBubble();
    deps.busy.value = false;
    deps.bubbles.value = [];
    cardProposals.clear();
    cardPages.clear();
    fillUndo.clear();
    qaHistory.value = loadQa();
    memorySummary.value = loadMemorySummary();
    qaSeq = Math.max(1, qaHistory.value.length + 1);
    turnsSinceCompress = loadTurnsSinceCompress();
    lastAgentAt = 0;
    lastUserQuestion.value = '';
    retriedForQuestion.value = '';
  }

  return {
    qaHistory,
    reloadForUser,
    clearWaitBubble,
    abortChat,
    chat,
    onCardAction,
    noteUserQuestion,
    maybeRetryAnswer,
    lastUserQuestion,
    retriedForQuestion,
  };
}
