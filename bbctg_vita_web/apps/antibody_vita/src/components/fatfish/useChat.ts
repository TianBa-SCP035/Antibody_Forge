/** 串联聊天、等待气泡、中止、记忆压缩、代理和确认卡片。 */

import { ref, type Ref } from 'vue';

import { ambientHint, collectPageContext } from './pageContext';
import { LINES } from './lines';
import { QA_KEEP, SESSION_GAP_MS } from './constants';
import {
  loadMemorySummary,
  loadMergedAt,
  loadQa,
  pendingForCompress,
  requestCompress,
  saveMemorySummary,
  saveMergedAt,
  saveQa,
  shouldCompress,
  toRecentHistory,
  type QaItem,
} from './memory';
import type { FillSnapshot } from './formBridge';
import { formLabels, sameForm } from './formBridge';
import { openAndLearn } from './apiWatch';
import { applyFillProposal, runExportProposal, runReportProposal, undoFillProposal, type Proposal } from './petTools';
import { allowRestOfTurn, revokeAllowRest, setHeldWriteHandler, type HeldWrite, type WriteResult } from './pageAct';
import { runAgent } from './useAgent';
import type { CareEvent } from './useCare';

export type BubbleKind = 'pet' | 'user' | 'sys' | 'wait' | 'card';
export type ChatIntent = 'chat' | 'comment' | 'fill';
export type CardAction = {
  id: 'apply' | 'export' | 'open' | 'cancel' | 'undo' | 'allow' | 'allowAll' | 'block';
  label: string;
  primary?: boolean;
  /** 收不回来的操作（删除），按钮标红。 */
  danger?: boolean;
};
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
/** 明确请求文件的词；单独的「表格」或「清单」不计入，因为「看看这页的表格」并非下载请求。 */
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
  /** 卡片正被看着（悬停、焦点在里面、输入框开着）。 */
  cardInUse: (id: number) => boolean;
}) {
  const qaHistory = ref<QaItem[]>(loadQa());
  const memorySummary = ref(loadMemorySummary());
  let qaSeq = Math.max(1, qaHistory.value.length + 1);
  let chatAbort: AbortController | null = null;
  let stoppedBy: 'stop' | 'takeover' = 'stop';
  let waitBubbleId: number | undefined;
  let waitRotateTimer: number | undefined;
  let mergedAt = loadMergedAt();
  let compressing = false;
  /** 切换账号时递增；旧账号还在路上的压缩结果不能写进新账号。 */
  let memoryOwner = 0;
  let sessionEndTimer: number | undefined;
  const lastUserQuestion = ref('');
  const retriedForQuestion = ref('');
  const cardProposals = new Map<number, Proposal>();
  /** 填写卡片生成时的页面；在其他页面应用可能误中同名字段。 */
  const cardPages = new Map<number, string>();
  const fillUndo = new Map<number, FillSnapshot[]>();
  const pageKey = () => location.pathname + location.search + location.hash;
  const HAS_ID = /[?&][\w-]*id=/i;
  /** 判断是否仍为 asked 页面；允许新记录自动保存后在 URL 中增加 ID。 */
  function stillSamePage(asked: string) {
    if (asked === pageKey()) return true;
    const [askedPath, askedQuery = ''] = asked.split('?');
    return askedPath === location.pathname && !HAS_ID.test(`?${askedQuery}`) && HAS_ID.test(location.search);
  }

  function saveQaNow() {
    saveQa(qaHistory.value);
  }

  function pushQa(role: QaItem['role'], text: string, did?: string): number | undefined {
    const clean = String(text || '').trim();
    if (!clean) return undefined;
    const id = qaSeq++;
    qaHistory.value = [...qaHistory.value.slice(-(QA_KEEP - 1)), { id, role, text: clean, at: Date.now(), ...(did ? { did } : {}) }];
    saveQaNow();
    return id;
  }

  /** 卡片是哪条回答出的；用户点了下载、取消或关掉时补记到那条的 did 上。 */
  const cardQa = new Map<number, number>();
  function noteCardOutcome(cardId: number, outcome: string) {
    const qaId = cardQa.get(cardId);
    const item = qaId == null ? undefined : qaHistory.value.find((r) => r.id === qaId);
    const p = cardProposals.get(cardId);
    const title = p ? proposalCard(p).title || '' : heldLabel.get(cardId);
    if (!item || title == null) return;
    item.did = `${item.did ? `${item.did}；` : ''}用户对卡片「${title}」：${outcome.split('\n')[0]}`;
    saveQaNow();
  }

  function patchBubble(id: number, patch: Partial<PetBubble>) {
    const idx = deps.bubbles.value.findIndex((b) => b.id === id);
    if (idx < 0) return;
    const next = [...deps.bubbles.value];
    next[idx] = { ...next[idx]!, ...patch };
    deps.bubbles.value = next;
  }

  /** 宠物操作页面时被拦下的写请求：卡片 id → 放行与否；卡片不处理就关掉算拦下。 */
  const heldWrites = new Map<number, (allow: boolean) => void>();
  /** 提交卡片 id → 「方法 路径」，补记动作记录用。 */
  const heldLabel = new Map<number, string>();
  /** 是删除的提交卡片：「本轮都放行」不替它做决定。 */
  const heldDeletes = new Set<number>();
  /** 提交卡片属于哪一轮、在哪个页面弹出：「本轮都放行」只管同一轮；换了页面再放行就作废。 */
  const heldTurn = new Map<number, number>();
  const heldPage = new Map<number, string>();
  /** 这一轮弹出的提交卡片；回答出来时还没处理的，之后的决定记到那条回答上。 */
  const turnHeld: number[] = [];
  const HELD_TITLE = '要提交到系统吗？';
  function settleHeld(id: number, allow: boolean) {
    heldWrites.get(id)?.(allow);
    heldWrites.delete(id);
  }
  const resultNote = (r: WriteResult) =>
    `系统返回 ${r.status || '（请求失败）'}${r.text ? `：${r.text.slice(0, 120)}` : ''}`;
  setHeldWriteHandler((w: HeldWrite) => {
    const what = `${w.method} ${w.path}`;
    if (w.auto) {
      deps.say(`已按「本轮都放行」提交 ${what}`, 'sys');
      void w.result.then((r) => deps.say(`${what} ${resultNote(r)}`, 'sys'));
      return Promise.resolve(true);
    }
    return new Promise<boolean>((resolve) => {
      const isDelete = w.kind === '删除';
      const id = deps.addCard({
        title: isDelete ? '要从系统里删除吗？' : HELD_TITLE,
        text: [
          `我刚才${w.trigger || '操作了页面'}，页面要向系统发一次「${w.kind}」：`,
          w.body ? `内容：${w.body}` : '',
          `（${what}）`,
          isDelete
            ? '删除放行后收不回来，这类提交每次都单独问。拦下则这次提交作废，页面可能提示失败。'
            : '放行后会真的写进系统；拦下则这次提交作废，页面可能提示失败。「本轮都放行」：这次任务里后面的提交（删除除外）不再逐个问，下次提问重新逐个确认。',
        ]
          .filter(Boolean)
          .join('\n'),
        actions: [
          isDelete ? { id: 'allow', label: '确认删除', danger: true } : { id: 'allow', label: '放行', primary: true },
          ...(isDelete ? [] : [{ id: 'allowAll' as const, label: '本轮都放行' }]),
          { id: 'block', label: '拦下' },
        ],
      });
      heldWrites.set(id, resolve);
      heldTurn.set(id, w.turn);
      heldPage.set(id, pageKey());
      if (isDelete) heldDeletes.add(id);
      heldLabel.set(id, `提交 ${what}`);
      turnHeld.push(id);
      void w.result.then((r) => {
        const note = `已放行，${resultNote(r)}`;
        patchBubble(id, { note, working: false });
        noteCardOutcome(id, note);
        removeLater(id, readMs(note, 8000));
      });
    });
  });

  /** 处理完的卡片过一会儿收起；用户正看着就再等等。 */
  function removeLater(id: number, ms: number) {
    window.setTimeout(() => {
      if (!deps.bubbles.value.some((b) => b.id === id)) return;
      if (deps.cardInUse(id)) removeLater(id, 4000);
      else removeBubble(id);
    }, ms);
  }
  const readMs = (note: string, base: number) => Math.max(base, 2500 + note.length * 120);

  function removeBubble(id: number) {
    settleHeld(id, false);
    heldLabel.delete(id);
    heldDeletes.delete(id);
    heldTurn.delete(id);
    heldPage.delete(id);
    deps.bubbles.value = deps.bubbles.value.filter((b) => b.id !== id);
    cardProposals.delete(id);
    cardPages.delete(id);
    cardQa.delete(id);
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

  /** takeover：宠物动过页面后用户自己点了或按了页面，算用户接手。 */
  function abortChat(by: 'stop' | 'takeover' = 'stop') {
    if (!deps.busy.value && !chatAbort) return;
    stoppedBy = by;
    try {
      chatAbort?.abort();
    } catch {
      /* 请求可能已经结束或中止。 */
    }
    chatAbort = null;
    clearWaitBubble();
    // 停止就是全停：还没决定的提交一律拦下，「本轮都放行」作废。
    revokeAllowRest();
    for (const id of [...heldWrites.keys()]) {
      settleHeld(id, false);
      noteCardOutcome(id, by === 'takeover' ? '用户接手页面，拦下' : '用户点了停止，拦下');
      patchBubble(id, { actions: [], note: '已停止，这次提交拦下了', working: false });
      removeLater(id, 4000);
    }
    deps.busy.value = false;
    void deps.playAnim(deps.pick(['sigh', 'pokeShy', 'look'] as const));
    deps.say(by === 'takeover' ? deps.pick(LINES.takeover) : deps.pick(LINES.cancelled));
    deps.pokeIdleClock();
  }

  async function maybeRunCompress() {
    const pending = pendingForCompress(qaHistory.value, mergedAt);
    if (compressing || !shouldCompress(pending)) return;
    compressing = true;
    const owner = memoryOwner;
    try {
      const next = await requestCompress(memorySummary.value, pending);
      if (next && owner === memoryOwner) {
        memorySummary.value = next;
        saveMemorySummary(next);
        mergedAt = pending[pending.length - 1]!.at;
        saveMergedAt(mergedAt);
      }
    } finally {
      if (owner === memoryOwner) compressing = false;
    }
  }

  /** 现在检查一次，这段对话结束时再检查一次，下次开口前就已并入摘要。 */
  function checkCompress() {
    void maybeRunCompress();
    window.clearTimeout(sessionEndTimer);
    sessionEndTimer = window.setTimeout(() => void maybeRunCompress(), SESSION_GAP_MS + 1000);
  }

  function rememberReply(text: string, did?: string): number | undefined {
    const retrying =
      retriedForQuestion.value && lastUserQuestion.value && retriedForQuestion.value === lastUserQuestion.value;
    const lastPet = retrying ? [...qaHistory.value].reverse().find((r) => r.role === 'pet') : undefined;
    if (lastPet) {
      lastPet.text = text;
      if (did) lastPet.did = did;
      else delete lastPet.did;
      saveQaNow();
      return lastPet.id;
    }
    return pushQa('pet', text, did);
  }

  function celebrate(event: 'chat' | 'task') {
    deps.onCare(event);
    deps.armSore(12000);
    // 完成任务会消耗少量饱腹度（「吃 Token」），因此动画偶尔表现为吃 Token。
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

  function showAgentAnswer(
    text: string,
    voice: string | undefined,
    proposals: Proposal[],
    askedToExport: boolean,
    actions: string[] = [],
  ) {
    celebrate('task');
    // 仅用户明确要求下载时才跳过卡片；模型自行选择或受数据内文本诱导的导出仍需点击确认。
    const autoExport = (p: Proposal): p is Extract<Proposal, { kind: 'export' }> => p.kind === 'export' && !!p.auto && askedToExport;
    // 模型再次建议同一页面时保留首张卡片及其问题，不重复创建。
    const shown = proposals.filter(
      (p) =>
        autoExport(p) ||
        !(p.kind === 'open_page' && [...cardProposals.values()].some((q) => q.kind === 'open_page' && q.path === p.path)),
    );
    const did = [
      actions.length ? `调用：${actions.join('；')}` : '没有调用工具',
      shown.length
        ? shown.map((p) => (autoExport(p) ? `直接开始下载「${p.label}」` : `出了卡片「${proposalCard(p).title || ''}」`)).join('；')
        : '没有出卡片',
    ].join('。');
    let qaId: number | undefined;
    if (text) {
      if (voice) deps.say(voice);
      if (text.length <= SHORT_ANSWER && !text.includes('\n')) deps.say(text);
      else deps.addCard({ text });
      qaId = rememberReply(text, did);
    }
    for (const p of shown) {
      if (autoExport(p)) {
        const owner = memoryOwner;
        void (async () => {
          deps.say(`正在导出：${p.label}${p.count != null ? `（${p.count}）` : ''}`);
          const note = await runExportProposal(p);
          if (owner === memoryOwner) deps.say(note);
        })();
        continue;
      }
      const id = deps.addCard(proposalCard(p));
      cardProposals.set(id, p);
      // 填写卡片只能应用到读表单的那个页面（不是提问时的页面：宠物常常先点进新建页才出建议）。
      if (p.kind === 'fill') cardPages.set(id, p.page);
      if (qaId != null) cardQa.set(id, qaId);
    }
    for (const id of turnHeld.splice(0)) if (qaId != null && heldWrites.has(id)) cardQa.set(id, qaId);
    checkCompress();
  }

  /** keep 为 true 时保留卡片，用备注列出仍需用户处理的内容。 */
  function finishCard(id: number, note: string, keep = false) {
    noteCardOutcome(id, note);
    patchBubble(id, { actions: [], note, working: false });
    cardProposals.delete(id);
    cardPages.delete(id);
    fillUndo.delete(id);
    if (!keep) removeLater(id, readMs(note, 6000));
  }

  async function onCardAction(id: number, action: CardAction['id'] | 'close') {
    const owner = memoryOwner;
    try {
      await handleCardAction(id, action, owner);
    } catch {
      if (owner === memoryOwner) finishCard(id, '这一步出错了，没做完；看看页面现在的样子，需要的话再问我一次', true);
    }
  }

  async function handleCardAction(id: number, action: CardAction['id'] | 'close', owner: number) {
    if (heldWrites.has(id)) {
      if ((action === 'allow' || action === 'allowAll') && !stillSamePage(heldPage.get(id) ?? '')) {
        settleHeld(id, false);
        noteCardOutcome(id, '页面已经换了，这次提交作废');
        patchBubble(id, { actions: [], note: '页面已经换了，这次提交作废；需要的话回到原页面重新操作', working: false });
        removeLater(id, 8000);
        return;
      }
      const allow = action === 'allow' || action === 'allowAll';
      if (action === 'allowAll') {
        const turn = heldTurn.get(id) ?? -1;
        allowRestOfTurn(turn);
        for (const other of [...heldWrites.keys()]) {
          if (other === id || heldDeletes.has(other) || heldTurn.get(other) !== turn) continue;
          settleHeld(other, true);
          patchBubble(other, { actions: [], working: true, note: '已放行（本轮都放行），等系统回复…' });
          noteCardOutcome(other, '放行');
        }
      }
      settleHeld(id, allow);
      noteCardOutcome(id, action === 'close' ? '没处理就关掉了，算拦下' : allow ? '放行' : '拦下');
      if (action === 'close') {
        removeBubble(id);
        return;
      }
      patchBubble(id, { actions: [], working: allow, note: allow ? '已放行，等系统回复…' : '已拦下，这次没有提交' });
      if (!allow) removeLater(id, 6000);
      return;
    }
    const p = cardProposals.get(id);
    if (action === 'close' || !p) {
      if (p) noteCardOutcome(id, '没处理就关掉了');
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
      // 请求由页面自身的自动保存发出，无法确认结果，因此不能声称保存成功。
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
      // 临时保留撤销按钮；若无待处理问题，卡片随后自动消失。
      fillUndo.set(id, snapshots);
      noteCardOutcome(id, note);
      patchBubble(id, { working: false, note, actions: [{ id: 'undo', label: '撤销这次填写' }] });
      if (!keep) {
        const expireUndo = (ms: number) =>
          window.setTimeout(() => {
            if (!fillUndo.has(id)) return;
            if (deps.cardInUse(id)) {
              expireUndo(4000);
              return;
            }
            cardProposals.delete(id);
            fillUndo.delete(id);
            removeBubble(id);
          }, ms);
        expireUndo(p.autoSave ? UNDO_WINDOW_MS * 2 : UNDO_WINDOW_MS);
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
      if (owner !== memoryOwner) return;
      if (p.question && deps.busy.value) {
        finishCard(id, `认识「${p.title}」了；我正忙着别的，忙完你再问我一次`);
        return;
      }
      finishCard(id, `认识「${p.title}」了${p.question ? '，接着回答' : ''}`);
      if (p.question) void chat(p.question, 'chat', true);
    }
  }

  /** forceAgent 用于宠物学习所需页面后重新提交数据问题；带图片的提问直接交给能看图的 agent。 */
  async function chat(message: string, intent: ChatIntent = 'chat', forceAgent = false, images: string[] = []) {
    if (deps.busy.value) return;
    deps.busy.value = true;
    deps.sleeping.value = false;
    void deps.playAnim(deps.pick(['think', 'mutter', 'code', 'busy'] as const), { loop: true, restart: true });
    // 普通提问先发给闲聊接口，由代理判断要不要查数据（要查就回 reroute）。
    const agentMode = forceAgent || intent === 'fill' || images.length > 0;
    turnHeld.length = 0;
    const fromDialog = deps.chatOpen.value && intent === 'chat';
    showWaitBubble(agentMode);
    const abort = new AbortController();
    chatAbort = abort;
    const recentHistory = toRecentHistory(qaHistory.value, message);
    try {
      const askAgent = async () => {
        const result = await runAgent({
          message: intent === 'fill' ? FILL_PROMPT : message,
          history: recentHistory,
          memorySummary: memorySummary.value || '',
          careMood: deps.careMoodHint(),
          openCards: [
            ...[...cardProposals.values()].map((p) => proposalCard(p).title || ''),
            ...[...heldWrites.keys()].map(() => HELD_TITLE),
          ],
          images,
          signal: abort.signal,
          onPhase: (phase) => {
            if (!abort.signal.aborted) patchWaitText(`${phase} ${STOP_HINT}`);
          },
          onTakeover: () => abortChat('takeover'),
        });
        // 被停下的这一轮可能晚到：那时进度气泡可能已经属于新的一轮。
        if (!abort.signal.aborted) clearWaitBubble();
        const unfinished = result.aborted || abort.signal.aborted || result.offline;
        // 中途停下或断了也已经动过页面：记下做过的，下一轮才知道页面被改过。
        if (unfinished && result.actions?.length) {
          const why = result.offline
            ? '（这一轮中途断了：连不上模型，或页面整页刷新了，没有回答）'
            : stoppedBy === 'takeover'
              ? '（宠物操作到一半，用户自己动手操作了页面，宠物停下，没有回答）'
              : '（这一轮被用户中途停下，没有回答）';
          rememberReply(why, `调用：${result.actions.join('；')}。没有出卡片`);
        }
        // 若用户点击停止时最后一步已在返回途中，丢弃回答、卡片和自动导出。
        if (result.aborted || abort.signal.aborted) return;
        if (result.offline) {
          void deps.playAnim('sigh');
          deps.say(deps.pick(LINES.offline), 'sys');
          return;
        }
        if (result.exhausted && !result.proposals.length) {
          if (result.actions?.length) rememberReply('（这一轮步数或时间用完了，没理清，没有回答）', `调用：${result.actions.join('；')}。没有出卡片`);
          deps.onCare('taskFail');
          void deps.playAnim('sigh');
          deps.say('翻了好几轮还没理清…换个说法，或者直接给我实验ID？');
          return;
        }
        for (const p of result.proposals) if (p.kind === 'open_page' && intent === 'chat') p.question = message;
        showAgentAnswer(result.text || '', result.voice, result.proposals, EXPORT_INTENT.test(message), result.actions);
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
      if (abort.signal.aborted) return;
      clearWaitBubble();
      if (data?.reroute === 'agent') {
        // 要查数据，或闲聊模型声称已填写、导出时，交给能用工具的查询流程。
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
      checkCompress();
    } catch (err) {
      if (abort.signal.aborted) return;
      clearWaitBubble();
      if ((err as { name?: string })?.name !== 'AbortError') {
        void deps.playAnim('scare');
        deps.say(deps.pick(LINES.error));
      }
    } finally {
      // 停止后 abortChat() 已重置状态，且此时状态可能已属于更新的聊天。
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
    if (deps.busy.value || !lastUserQuestion.value) return false;
    if (retriedForQuestion.value === lastUserQuestion.value) return false;
    if (!lastUserQuestion.value.trim()) return false;
    retriedForQuestion.value = lastUserQuestion.value;
    deps.say(deps.pick(LINES.retry));
    await chat(lastUserQuestion.value, 'chat');
    return true;
  }

  /** 未刷新页面时切换登录账号，应清除当前账号的对话和卡片并加载新账号内容。 */
  function reloadForUser() {
    try {
      chatAbort?.abort();
    } catch {
      /* 请求可能已经结束或中止。 */
    }
    chatAbort = null;
    clearWaitBubble();
    deps.busy.value = false;
    for (const id of [...heldWrites.keys()]) settleHeld(id, false);
    heldLabel.clear();
    heldDeletes.clear();
    heldTurn.clear();
    heldPage.clear();
    deps.bubbles.value = [];
    cardProposals.clear();
    cardPages.clear();
    cardQa.clear();
    fillUndo.clear();
    qaHistory.value = loadQa();
    memorySummary.value = loadMemorySummary();
    qaSeq = Math.max(1, qaHistory.value.length + 1);
    mergedAt = loadMergedAt();
    memoryOwner += 1;
    compressing = false;
    checkCompress();
    lastUserQuestion.value = '';
    retriedForQuestion.value = '';
  }

  function disposeChat() {
    setHeldWriteHandler(null);
    for (const id of [...heldWrites.keys()]) settleHeld(id, false);
    window.clearTimeout(sessionEndTimer);
    chatAbort?.abort();
  }

  // 上次离开时没来得及并入摘要的对话，打开页面就补上；刷新后没再说话的这段，结束时也会并入。
  checkCompress();

  return {
    disposeChat,
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
