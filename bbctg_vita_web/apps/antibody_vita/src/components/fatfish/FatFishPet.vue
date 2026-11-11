<script lang="ts" setup>
/**
 * FatFish floating pet — Antibody Vita desktop companion.
 * WebM: PC2005-cloud/dsh-pet (entertainment/internal). See ATTRIBUTION.txt.
 */
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { useRouter } from 'vue-router';

import {
  BALL,
  BALL_IMG,
  BASE,
  CURSOR_GRABBING,
  CURSOR_HAMMER,
  CURSOR_HOVER,
  SIDEBAR_WIDTH,
  SIZE,
  DAILY_REMARKS_KEY,
} from './constants';
import { reloadSources } from './apiWatch';
import { scanPageForm } from './formBridge';
import { LINES } from './lines';
import { lineFor, refreshLines, reloadLines, type FreshKind } from './linePool';
import ShellGame from './ShellGame.vue';
import FatfishDiscoStage from './FatfishDiscoStage.vue';
import { pokeHitPresentation } from './pokeHitMark';
import { useFatfishDisco } from './useFatfishDisco';
import { ambientHint, collectPageContext, weatherNow } from './pageContext';
import { currentUserKey, setHostRouter } from './session';
import {
  animateSnap,
  avatarOriginInCapsule as avatarOriginInCapsuleOf,
  clamp,
  expandFromBall,
  magnetSnapTarget,
  nearMagnetEdge as nearMagnetEdgeOf,
  petH as petHOf,
  petW as petWOf,
  settleAsFreeBall as settleAsFreeBallOf,
} from './useBall';
import { CARE_STATE_LABEL, useCare, type CareState } from './useCare';
import { useChat, type CardInput, type PetBubble } from './useChat';

defineOptions({ name: 'FatFishPet' });
setHostRouter(useRouter());

type AnimKey = string;

// Care/pin — say/pick are function declarations (hoisted) so this is safe.
const {
  pinned,
  care,
  careState,
  careLevel,
  awayHours,
  onCare,
  tick: careTick,
  resume: resumeCare,
  togglePin,
  careMoodHint,
} = useCare({
  say: (t) => {
    say(t);
  },
  pick,
  pinLines: {
    on: ['好，先站这儿不乱跑', '固定了，你忙你的', '行，我不乱晃'] as const,
    off: ['解除固定～', '那我可以走走了', '嗯，自由活动'] as const,
  },
  onLevelUp: (level, name) => {
    window.setTimeout(() => {
      void playAnim(pickAnim(['celebrate', 'curtsy', 'flower']));
      const line = LINES.levelUpAt[level] || pick(LINES.levelUp);
      say(`${line}（熟悉度 Lv${level} · ${name}）`);
    }, 1600);
  },
});

const ANIM: Record<string, string> = {
  idle: '待机呼吸休闲.webm',
  look: '东张西望.webm',
  floatStep: '原地漂浮踏步.webm',
  stretch: '超大伸懒腰.webm',
  sleepStart: '睡觉-开始.webm',
  sleepLoop: '睡觉-循环.webm',
  wake: '睡觉-起来.webm',
  nap: '原地小憩沉眠.webm',
  yawn: '哈欠连天.webm',
  pokeHappy: '点击回应-开心跃动.webm',
  pokeWave: '点击回应-元气挥手.webm',
  pokeShy: '点击回应-害羞惊讶.webm',
  pokeAngry: '点击回应-傲娇生气.webm',
  pokeTickle: '点击回应-挠痒咯咯笑.webm',
  knock: '原地敲击桌面互动.webm',
  jump: '原地跳跃抓碎头顶物品.webm',
  tailSlap: '用鲸鱼尾巴拍打地面.webm',
  curtsy: '女仆屈膝礼仪.webm',
  spin: '小幅度原地360度旋转展示.webm',
  drag: '被鼠标拖拽悬空反馈.webm',
  squash: '原地重力下蹲压缩.webm',
  run: '侧身急躁跑.webm',
  trot: '开心小跑.webm',
  runTurn: '原地左转奔跑.webm',
  crab: '螃蟹走路.webm',
  pace: '工作状态-原地踱步张望.webm',
  eat: '大口吃零食.webm',
  eatCaught: '偷吃零食被抓住.webm',
  eatRice: '吃白饭.webm',
  eatLunch: '吃午餐.webm',
  eatBowl: '吃饭·碗饭.webm',
  eatIce: '吃冰淇淋融化.webm',
  eatMelon: '吃西瓜.webm',
  eatToken: '吃Token.webm',
  hungry: '期待开饭.webm',
  whatEat: '是啊，吃什么.webm',
  cube: '原地专心玩魔方.webm',
  juggle: '三球抛接.webm',
  toyCar: '原地蹲下玩玩具汽车.webm',
  top: '抽陀螺.webm',
  magic: '扑克魔术.webm',
  waterGun: '玩水枪.webm',
  rageGame: '玩游戏气急败坏.webm',
  go: '下五子棋.webm',
  shuttle: '踢毽子.webm',
  hobbyhorse: '骑木马.webm',
  petCat: '撸猫.webm',
  flute: '吹笛子.webm',
  violin: '小提琴演奏.webm',
  kite: '放风筝.webm',
  fan: '摇扇纳凉.webm',
  gift: '拆礼物.webm',
  snowman: '堆雪人.webm',
  fireworks: '放烟花.webm',
  lion: '舞狮头.webm',
  bubbles: '鲸鱼吐泡泡特效.webm',
  note: '轻快记录.webm',
  dance: '可爱宅舞.webm',
  sway: '轻快摇摆舞.webm',
  maidDance: '优雅女仆舞.webm',
  swing: '荡秋千.webm',
  think: '工作状态-思考冒泡.webm',
  code: '写代码.webm',
  busy: '工作状态-忙碌点按.webm',
  archive: '工作状态-清点归档.webm',
  celebrate: '工作状态-雀跃庆祝.webm',
  sigh: '工作状态-垂头叹气冒汗.webm',
  mutter: '深度思考碎碎念.webm',
  mutterIdle: '碎碎念-发呆碎碎念.webm',
  mutterScreen: '碎碎念-对屏碎碎念.webm',
  mutterWipe: '碎碎念-擦桌碎碎念.webm',
  hum: '悠闲哼歌.webm',
  scare: '被吓一跳.webm',
  wakeScare: '打瞌睡被惊醒.webm',
  flower: '凭空生花.webm',
  bees: '蝴蝶蜜蜂环绕头顶开花.webm',
  animals: '动物环绕.webm',
  ghost: '萌化小幽灵.webm',
  whale: '蓝鲸现世.webm',
  mirror: '照镜子.webm',
  balloon: '吹气球.webm',
  brush: '晨间刷牙.webm',
  dress: '整体换装试色.webm',
  pigeon: '变鸽子.webm',
  redPacket: '收红包.webm',
};

const PLAYFUL_ANIMS: AnimKey[] = [
  'cube', 'juggle', 'toyCar', 'top', 'magic', 'go', 'rageGame',
  'shuttle', 'hobbyhorse', 'petCat', 'gift', 'bubbles', 'dance', 'whale', 'ghost',
];
const DANCE_ANIMS: AnimKey[] = ['dance', 'sway', 'maidDance', 'swing', 'spin', 'lion', 'fireworks'];

/** Props that only make sense for the day outside: heat, snow, spring wind, the Spring Festival season. */
function seasonalAnims(): AnimKey[] {
  const month = new Date().getMonth() + 1;
  const w = weatherNow();
  const hot = w?.temp != null ? w.temp >= 28 : month >= 6 && month <= 8;
  const snowy = w ? w.sky === '下雪' || (w.temp != null && w.temp <= 0 && (month === 12 || month <= 2)) : false;
  const out: AnimKey[] = [];
  if (hot) out.push('fan', 'eatIce', 'eatMelon', 'waterGun');
  if (snowy) out.push('snowman');
  if (month >= 3 && month <= 5 && w?.sky !== '下雨') out.push('kite');
  if (month <= 2) out.push('lion', 'redPacket', 'fireworks');
  return out;
}

function hourNow() {
  return new Date().getHours();
}

type Bubble = PetBubble;

const pos = reactive({ x: 0, y: 0 });
const vel = reactive({ x: 0, y: 0 });
const collapsed = ref(false);
const busy = ref(false);
const sleeping = ref(false);
watch(sleeping, (_now, was) => careTick(was));
const dragging = ref(false);
const holding = ref(false);
const pressing = ref(false);
const ballDragging = ref(false);
const hovered = ref(false);
type HitMark = { id: number; x: number; y: number; text: string; kind: import('./pokeHitMark').PokeHitKind };
/** Little 戳 / 咚 marks where each tap lands. */
const hitMarks = ref<HitMark[]>([]);
const hitShake = ref(false);
const menuOpen = ref(false);
const menuPos = reactive({ x: 0, y: 0 });
const menuEl = ref<HTMLElement | null>(null);
const dockEdge = ref<'left' | 'right' | 'top' | 'bottom'>('left');
const docked = ref(false);
const draft = ref('');
const bubbles = ref<Bubble[]>([]);
const facing = ref<1 | -1>(1);
const squish = ref(1);

/** Dual-buffer videos: load into the back slot, then swap when its first frame is painted (blended only for mid-clip cuts). */
const slotA = ref<HTMLVideoElement | null>(null);
const slotB = ref<HTMLVideoElement | null>(null);
const frontIsA = ref(true);
const srcA = ref(BASE + ANIM.idle);
const srcB = ref(BASE + ANIM.idle);
const opA = ref(1);
const opB = ref(0);
const loopA = ref(true);
const loopB = ref(true);
const currentAnim = ref<AnimKey>('idle');

let bubbleSeq = 1;
let sleepTimer: number | undefined;
let holdTimer: number | undefined;
let wanderTimer: number | undefined;
let observeTimer: number | undefined;
let physicsRaf = 0;
let roamRaf = 0;
let pendingEnd: (() => void) | null = null;
let animGen = 0;
let lastHoverSay = 0;
let punchCount = 0;
let punchTimer: number | undefined;
const fleeing = ref(false);
let fleeTimer: number | undefined;
let fleeRaf = 0;
let caughtAt = 0;

/** After chat reply or being punched, clicks call doPunch(); petting comforts. */
const soreUntil = ref(0);
let soreTick: number | undefined;
let ballDown: { x: number; y: number; px: number; py: number; t: number } | null = null;
let ballMoved = false;
let snapRaf = 0;
let pointerMode: 'none' | 'pending' | 'drag' | 'stroke' | 'hold' = 'none';
let downAt = { x: 0, y: 0, t: 0 };
let dragOff = { x: 0, y: 0 };
let lastDrag = { x: 0, y: 0, t: 0 };
let lastFlipAt = 0;
let strokeWindow: { x: number; count: number } | null = null;
let clickCount = 0;
let clickDecayTimer: number | undefined;
const TAP_GAP_MS = 260;
let tapCount = 0;
let tapTimer: number | undefined;
let petStage = 0;

const preloaded = new Map<string, HTMLVideoElement>();
// Repeated pokes are captured before chat/drag/menu handlers; normal first-press dragging stays intact.
const {
  active: discoActive, pending: discoPending, busy: discoBusy, message: discoMessage,
  play: playDisco, stop: stopDisco, replay: replayDisco,
  clock: discoClock, duration: discoDuration, finished: discoFinished, session: discoSession, unlocked: discoUnlocked,
  stageOpen: discoStageOpen, readTime: discoReadTime, flurrying: discoFlurrying,
  openStage: openDiscoStage, closeStage: closeDiscoStage,
  onDown: discoDown, onMove: discoMove, onUp: discoUp,
  onCancel: discoCancel, onAux: discoAux,
} = useFatfishDisco({
  enabled: () => !rhythm.value && !shellPlay.value,
  prepare: () => {
    closeMenu();
    stopFlee();
    cancelAnimationFrame(physicsRaf);
    cancelAnimationFrame(roamRaf);
    cancelAnimationFrame(snapRaf);
  },
  resetPointer: (preserveTaps = false) => {
    if (preserveTaps) {
      // Reset only physical press/drag state; the native 260ms poke burst is independent.
      window.clearTimeout(holdTimer);
      window.clearTimeout(tapTimer);
      tapTimer = undefined;
      pointerMode = 'none';
      pressing.value = false;
      dragging.value = false;
      holding.value = false;
      squish.value = 1;
    } else {
      resetPointer();
    }
    ballDown = null;
    ballMoved = false;
    ballDragging.value = false;
    vel.x = 0;
    vel.y = 0;
  },
  tap: recordPetTap,
});

let discoPetBefore: { collapsed: boolean; docked: boolean; x: number; y: number; sleeping: boolean } | undefined;
watch(discoActive, (dancing) => {
  if (dancing) {
    discoPetBefore = { collapsed: collapsed.value, docked: docked.value, x: pos.x, y: pos.y, sleeping: sleeping.value };
    closeMenu();
    if (chatOpen.value) closeChatDialog();
    stopFlee();
    clearRhythm();
    clearPlay();
    resetPointer();
    cancelAnimationFrame(physicsRaf);
    cancelAnimationFrame(roamRaf);
    cancelAnimationFrame(snapRaf);
    collapsed.value = false;
    docked.value = false;
    expandFromBall(pos);
    sleeping.value = false;
    window.clearTimeout(sleepTimer);
    clearAnimQueue();
    // Real dance WebM plus the outer audio-driven stage motion; never animate either WebM buffer slot.
    void playAnim('dance', { loop: true, restart: true, priority: 'urgent' });
  } else if (discoPetBefore) {
    const before = discoPetBefore;
    discoPetBefore = undefined;
    collapsed.value = before.collapsed;
    docked.value = before.docked;
    pos.x = before.x;
    pos.y = before.y;
    sleeping.value = before.sleeping;
    if (before.collapsed) { slotA.value?.pause(); slotB.value?.pause(); }
    else {
      void playAnim(before.sleeping ? 'sleepLoop' : 'idle', { loop: true, restart: true, priority: 'urgent' });
      if (!before.sleeping) pokeIdleClock();
    }
  }
});
watch(discoUnlocked, (now, before) => {
  if (now && !before) say('解锁蹦迪啦！以后右键我选「蹦迪」就能直接开跳，不用再戳一百下～');
});
/** Hover = character pointer; only press/drag uses grabbing hand. */
const petCursor = computed(() => {
  // Grab only after a real hold or drag — a plain click / hammer tap must not flash the grab hand.
  if (dragging.value || holding.value || ballDragging.value) {
    return CURSOR_GRABBING;
  }
  if (Date.now() < soreUntil.value) {
    return CURSOR_HAMMER;
  }
  return CURSOR_HOVER;
});

/**
 * Viewport-first bubble placement, then convert to stage-local.
 * NEVER use `inset - pos.x` (that teleports the stack to viewport x≈10).
 * Right side of screen → stack glued to her LEFT; left side → her RIGHT.
 * Top corners: drop the head-anchor so the stack does not clip off-screen.
 */
/**
 * Place UI beside her HEAD toward SCREEN CENTER (inner side).
 * left/bottom-left/top-left → her RIGHT; right/*-right → her LEFT.
 * Candidates sit fully beside the sprite (not overlapping her face).
 */
function glueBesideHer(w: number, gap: number, inset: number) {
  const vw = window.innerWidth || 1280;
  const box = petBox();
  const herCenter = pos.x + box / 2;
  // Prefer the inner side (toward viewport center).
  const preferLeftOfHer = herCenter >= vw * 0.5;
  const leftCandidate = pos.x - gap - w; // fully left of stage
  const rightCandidate = pos.x + box + gap; // fully right of stage
  let side: 'left' | 'right' = preferLeftOfHer ? 'left' : 'right';
  let vx = preferLeftOfHer ? leftCandidate : rightCandidate;
  const lo = inset;
  const hi = Math.max(lo, vw - inset - w);
  const fits = (x: number) => x >= lo && x + w <= vw - inset;
  if (!fits(vx)) {
    const otherSide: 'left' | 'right' = side === 'left' ? 'right' : 'left';
    const other = otherSide === 'left' ? leftCandidate : rightCandidate;
    if (fits(other)) {
      side = otherSide;
      vx = other;
    } else {
      // Both clipped (narrow / corner): keep inner preference, clamp without teleporting away.
      vx = Math.max(lo, Math.min(hi, vx));
      // If clamp would park the stack over her torso, nudge just outside her nearer edge.
      const overlap = vx < pos.x + box && vx + w > pos.x;
      if (overlap) {
        if (preferLeftOfHer) {
          vx = Math.max(lo, Math.min(hi, pos.x - gap - w));
          side = 'left';
          if (vx + w > pos.x + 8) {
            vx = Math.max(lo, Math.min(hi, pos.x + box + gap));
            side = 'right';
          }
        } else {
          vx = Math.max(lo, Math.min(hi, pos.x + box + gap));
          side = 'right';
          if (vx < pos.x + box - 8) {
            vx = Math.max(lo, Math.min(hi, pos.x - gap - w));
            side = 'left';
          }
        }
      }
    }
  }
  return { side, localLeft: vx - pos.x };
}

function petW() {
  return petWOf(collapsed.value, docked.value, dockEdge.value);
}

function petH() {
  return petHOf(collapsed.value, docked.value, dockEdge.value);
}

function avatarOriginInCapsule() {
  return avatarOriginInCapsuleOf(dockEdge.value);
}

function petBox() {
  return petW();
}

function headLocalBottom(mode: 'bubbles' | 'pill') {
  // Bubbles always sit on her head (same spot whether chat is open or not).
  // Pill sits at shoulder height on her side. Extra messages scroll instead of
  // shifting the whole column.
  const inset = 10;
  const vh = window.innerHeight || 800;
  const box = petH();
  let localBottom = mode === 'pill' ? Math.round(box * 0.40) : Math.round(box * 0.90);
  // The rhythm lanes (.ff-fall: bottom 6%, 220px tall) reach above her head; keep lines clear of the hint.
  if (mode === 'bubbles' && rhythm.value) localBottom = Math.max(localBottom, Math.round(SIZE * 0.06) + 220 + 4);
  const viewBottom = pos.y + box - localBottom;
  if (viewBottom > vh - inset) {
    localBottom = Math.max(localBottom, pos.y + SIZE - (vh - inset));
  }
  return localBottom;
}

/** Shell game at her feet on the screen-centre side. The sprite sits ~58px inside the box, so a 52px reach stays just off her. */
const shellGameStyle = computed(() => {
  const w = 190;
  const reach = 52;
  const vw = window.innerWidth || 1280;
  const vx = petOnLeftHalf() ? pos.x + SIZE - reach : pos.x + reach - w;
  return {
    left: `${Math.round(Math.max(10, Math.min(vw - 10 - w, vx)) - pos.x)}px`,
    bottom: '36px',
    width: `${w}px`,
    height: '104px',
  };
});

const bubbleStackStyle = computed(() => {
  // Same column above her head for idle chat and the input-open history.
  // Flush to her outer edge (not centered) so leftover side space is used.
  // Only the input pill moves to her left/right.
  const w = hasCard.value ? 300 : 220;
  const inset = 10;
  const vw = window.innerWidth || 1280;
  const localBottom = headLocalBottom('bubbles');
  const box = petBox();
  const onLeft = pos.x + box / 2 < vw * 0.5;
  // Character: flush to the outer edge. A docked ball hangs halfway off-screen,
  // so park the stack on the inward (visible) side.
  let vx = collapsed.value
    ? (onLeft ? Math.max(inset, pos.x + box) : pos.x - w)
    : (onLeft ? pos.x : pos.x + box - w);
  const lo = inset;
  const hi = Math.max(lo, vw - inset - w);
  vx = Math.max(lo, Math.min(hi, vx));
  const localLeft = vx - pos.x;
  const style: Record<string, string> = {
    left: `${Math.round(localLeft)}px`,
    right: 'auto',
    width: `${w}px`,
    bottom: `${localBottom}px`,
    transform: 'none',
  };
  if (chatOpen.value || hasCard.value) {
    // Stack sits above her head and grows upward: use space to the top of the screen.
    // (Old formula used vh - pos.y, i.e. space below her, so the lower she sat the less you saw.)
    const stackBottom = pos.y + petH() - localBottom;
    const roomAbove = Math.floor(stackBottom - inset);
    style.maxHeight = `${Math.max(48, Math.min(400, roomAbove))}px`;
  }
  return style;
});

function petOnLeftHalf() {
  return pos.x + SIZE / 2 < (window.innerWidth || 1280) * 0.5;
}

/** Hers (pet/sys/wait) vs ours (user). On the left half: she left, we right; reverse on the right half. */
function bubbleOnLeft(kind: Bubble['kind']) {
  const hers = kind !== 'user';
  return hers ? petOnLeftHalf() : !petOnLeftHalf();
}

function bubbleAlignClass(kind: Bubble['kind']) {
  return bubbleOnLeft(kind) ? 'align-left' : 'align-right';
}

function bubbleTailClass(kind: Bubble['kind']) {
  // Flipped again for symmetry: left bubbles sharp bottom-right, right bubbles sharp bottom-left.
  return bubbleOnLeft(kind) ? 'tail-left' : 'tail-right';
}

/** Input pill glued under/ beside the bubble stack — same clamp, tiny gap. */
const chatPillStyle = computed(() => {
  // Input stays beside her. When chat is open, keep a gap from the
  // bubble column so the field does not sit on top of the history.
  const w = 210;
  const inset = 10;
  const pillH = 36;
  const gap = bubbles.value.length > 1 ? 8 : -8;
  const { localLeft } = glueBesideHer(w, gap, inset);
  let localBottom = headLocalBottom('pill');
  if (bubbles.value.length) {
    const boxH = petH();
    const boxW = petW();
    const vw = window.innerWidth || 1280;
    const bubbleBottom = headLocalBottom('bubbles');
    const stackW = 220;
    const onLeft = pos.x + boxW / 2 < vw * 0.5;
    let stackVx = collapsed.value
      ? (onLeft ? Math.max(inset, pos.x + boxW) : pos.x - stackW)
      : (onLeft ? pos.x : pos.x + boxW - stackW);
    const hi = Math.max(inset, vw - inset - stackW);
    stackVx = Math.max(inset, Math.min(hi, stackVx));
    const stackLeft = stackVx - pos.x;
    const roomAbove = Math.max(48, pos.y + boxH - bubbleBottom - inset);
    const stackH = Math.min(400, Math.min(roomAbove, 28 + Math.max(1, bubbles.value.length) * 38));
    const stackTopY = boxH - bubbleBottom - stackH;
    const stackBotY = boxH - bubbleBottom;
    const pillTopY = boxH - localBottom - pillH;
    const pillBotY = boxH - localBottom;
    const hitX = localLeft < stackLeft + stackW && localLeft + w > stackLeft;
    const hitY = pillTopY < stackBotY && pillBotY > stackTopY;
    if (hitX && hitY) {
      localBottom = bubbleBottom - 8 - pillH;
      if (localBottom < 4) localBottom = 4;
    }
  }
  return {
    left: `${Math.round(localLeft)}px`,
    right: 'auto',
    width: `${w}px`,
    bottom: `${localBottom}px`,
    transform: 'none',
  } as Record<string, string>;
});

const chatOpen = ref(false);
const chatInputEl = ref<HTMLInputElement | null>(null);
const bubblesEl = ref<HTMLElement | null>(null);
/** Fade the stack edges only where messages are scrolled out of view. */
const stackFade = reactive({ top: false, bottom: false });

function updateStackFade() {
  const el = bubblesEl.value;
  if (!el || el.scrollHeight <= el.clientHeight + 1) {
    stackFade.top = false;
    stackFade.bottom = false;
    return;
  }
  stackFade.top = el.scrollTop > 2;
  stackFade.bottom = el.scrollTop + el.clientHeight < el.scrollHeight - 2;
}
let chatCloseTimer: number | undefined;
let careDecayTimer: number | undefined;

const {
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
} = useChat({
  busy,
  sleeping,
  chatOpen,
  say,
  addCard,
  pick,
  playAnim,
  onCare,
  careMoodHint,
  armSore,
  pokeIdleClock,
  closeChatDialog,
  focusInput: () => nextTick(() => chatInputEl.value?.focus()),
  bubbles,
});
// The pet lives above the router, so logging out and in as someone else doesn't remount her.
watch(currentUserKey, (now, was) => {
  if (now === was) return;
  chatOpen.value = false;
  reloadForUser();
  reloadSources();
  reloadLines();
});
type ArrowDir = 'up' | 'down' | 'left' | 'right';
const ARROW_DIRS: ArrowDir[] = ['left', 'down', 'up', 'right'];
const ARROW_GLYPH: Record<ArrowDir, string> = {
  left: '←',
  down: '↓',
  up: '↑',
  right: '→',
};

type FallNote = {
  id: number;
  dir: ArrowDir;
  spawnAt: number;
  hitAt: number;
  missAt: number;
  judged?: 'hit' | 'miss';
};
type RhythmState = {
  mode: 'dance' | 'play';
  notes: FallNote[];
  hits: number;
  misses: number;
  /** First note leaves the top here; before it a 3-2-1 countdown shows. */
  startAt: number;
  endAt: number;
  pulseTimer?: number;
  endTimer?: number;
};
const rhythm = ref<RhythmState | null>(null);
const RHYTHM_COUNTDOWN_MS = 2400;
const rhythmHint = computed(() => {
  const r = rhythm.value;
  if (!r) return '';
  const left = r.startAt - fallNow.value;
  return left > 0 ? `准备… ${Math.ceil(left / (RHYTHM_COUNTDOWN_MS / 3))}` : '方向键跟随箭头';
});
const beatPulse = ref(false);
let beatPulseClearTimer: number | undefined;
const fallNow = ref(0);
const lastLaneFlash = ref<{ dir: ArrowDir; kind: 'hit' | 'miss'; until: number } | null>(null);

const shellPlay = ref(false);
const shellGameRef = ref<{ stop: () => void } | null>(null);

function noteProgress(n: FallNote, now: number) {
  const span = Math.max(1, n.missAt - n.spawnAt);
  return Math.min(1.15, Math.max(0, (now - n.spawnAt) / span));
}
function fallNotesFor(dir: ArrowDir) {
  const r = rhythm.value;
  if (!r) return [] as FallNote[];
  const now = fallNow.value;
  return r.notes.filter((n) => n.dir === dir && now >= n.spawnAt - 40 && now <= n.missAt + 200);
}
function laneFlashKind(dir: ArrowDir) {
  const f = lastLaneFlash.value;
  if (!f || f.dir !== dir || fallNow.value > f.until) return '';
  return f.kind;
}
let lastIdleSay = 0;
const IDLE_SAY_COOLDOWN = 10000;
/** `fresh`: also draw from the model-written lines for this kind (see linePool.ts). */
function maybeIdleSay(pool: readonly string[], chance = 0.35, fresh?: FreshKind) {
  if (chatOpen.value) return; // while input open, keep stack for real Q&A only
  const now = Date.now();
  if (now - lastIdleSay < IDLE_SAY_COOLDOWN) return;
  if (Math.random() > chance) return;
  lastIdleSay = now;
  say(fresh ? lineFor(fresh, pool) : pick(pool));
}



function syncBubblesFromQaHistory() {
  const waits = bubbles.value.filter((b) => b.kind === 'wait' || b.kind === 'card');
  const recent = qaHistory.value.slice(-16);
  // Keep QA ids stable so reopening chat doesn't remount every bubble and replay ff-pop.
  bubbles.value = [
    ...recent.map((row) => ({
      id: row.id,
      text: row.text,
      kind: (row.role === 'user' ? 'user' : 'pet') as Bubble['kind'],
      sticky: true,
    })),
    ...waits,
  ];
  bubbleSeq = Math.max(bubbleSeq, ...recent.map((r) => r.id), 1) + 1;
}

function scrollBubblesToEnd() {
  nextTick(() => {
    const el = document.querySelector('.ff-bubbles.chat-open') as HTMLElement | null;
    if (el) el.scrollTop = el.scrollHeight;
  });
}

function openChatDialog() {
  window.clearTimeout(chatCloseTimer);
  menuOpen.value = false;
  chatOpen.value = true;
  // Show recent real Q&A in the glued stack (not a far window). Sticky while input open.
  if (qaHistory.value.length) {
    syncBubblesFromQaHistory();
  } else {
    say(pick(LINES.openChat), 'pet');
  }
  scrollBubblesToEnd();
  nextTick(() => {
    chatInputEl.value?.focus();
  });
}

/** Double-click opens the input; double-click again puts it away. */
function toggleChatDialog() {
  if (chatOpen.value) closeChatDialog();
  else openChatDialog();
}

function closeChatDialog() {
  window.clearTimeout(chatCloseTimer);
  chatOpen.value = false;
  // Resume compact auto-dismiss: keep last couple, then fade. Cards stay until the user closes them.
  const lastIds = new Set(
    bubbles.value.filter((b) => b.kind !== 'wait' && b.kind !== 'card').slice(-2).map((b) => b.id),
  );
  clearWaitBubble();
  bubbles.value = bubbles.value
    .filter((b) => b.kind === 'card' || lastIds.has(b.id))
    .map((b) => (b.kind === 'card' ? b : { ...b, sticky: false }));
  for (const b of bubbles.value) {
    if (b.kind === 'card') continue;
    const id = b.id;
    window.setTimeout(() => {
      if (chatOpen.value) return;
      bubbles.value = bubbles.value.filter((x) => x.id !== id);
    }, 2800);
  }
}



function urlOf(key: AnimKey) {
  return BASE + (ANIM[key] || ANIM.idle);
}

function placeDefault() {
  // Sit in the left sidebar column: canvas matches sidebar width, art centered.
  const sidebarW = measureSidebarWidth();
  pos.x = Math.round((sidebarW - SIZE) / 2);
  pos.y = Math.max(24, window.innerHeight - SIZE - 72);
}

function measureSidebarWidth() {
  const el = document.querySelector(".bg-sidebar") as HTMLElement | null;
  const w = el?.getBoundingClientRect().width || 0;
  return w >= 160 ? Math.round(w) : SIDEBAR_WIDTH;
}

function say(text: string, kind: Bubble['kind'] = 'pet') {
  // Live comic bubbles only — idle/互动 废话 never enter qaHistory.
  const prev = bubbles.value.filter((b) => b.kind !== 'card').at(-1);
  if (kind === 'pet' && !chatOpen.value && prev?.kind === 'pet' && prev.text === text) return prev.id;
  const id = bubbleSeq++;
  let list = bubbles.value;
  if (kind === 'wait') {
    list = list.filter((b) => b.kind !== 'wait');
  }
  // While input is open: keep Q&A/wait sticky (no auto-dismiss) and allow a longer stack.
  const sticky =
    chatOpen.value && (kind === 'user' || kind === 'pet' || kind === 'sys' || kind === 'wait');
  const keep = chatOpen.value ? 20 : 4;
  const kept = new Set(list.filter((b) => b.kind !== 'card').slice(-(keep - 1)).map((b) => b.id));
  bubbles.value = [...list.filter((b) => b.kind === 'card' || kept.has(b.id)), { id, text, kind, sticky }];
  if (!sticky && kind !== 'wait') {
    window.setTimeout(() => {
      if (chatOpen.value) return; // opened mid-timer — leave history alone
      bubbles.value = bubbles.value.filter((b) => b.id !== id);
    }, 4200);
  }
  if (chatOpen.value) scrollBubblesToEnd();
  return id;
}

const MAX_CARDS = 3;
const hoveredCard = ref<number | null>(null);

/** Answer cards fade after a reading-time delay (the text stays in chat history); hovering or an open chat holds them. */
function expireCard(id: number, ms: number) {
  window.setTimeout(() => {
    if (!bubbles.value.some((b) => b.id === id)) return;
    if (chatOpen.value || hoveredCard.value === id) {
      expireCard(id, 8000);
      return;
    }
    bubbles.value = bubbles.value.filter((b) => b.id !== id);
  }, ms);
}

/** Wide card for agent answers / confirmations. Cards with actions wait for the user. */
function addCard(card: CardInput) {
  const id = bubbleSeq++;
  const cards = bubbles.value.filter((b) => b.kind === 'card');
  const drop = new Set(
    cards.filter((b) => !b.actions?.length).slice(0, Math.max(0, cards.length - MAX_CARDS + 1)).map((b) => b.id),
  );
  bubbles.value = [...bubbles.value.filter((b) => !drop.has(b.id)), { id, kind: 'card', sticky: true, ...card }];
  if (!card.actions?.length) expireCard(id, Math.min(60_000, 12_000 + card.text.length * 60));
  scrollBubblesToEnd();
  return id;
}

const hasCard = computed(() => bubbles.value.some((b) => b.kind === 'card'));

watch(
  () => [bubbles.value.length, bubbles.value.at(-1)?.text, chatOpen.value, hasCard.value, bubbleStackStyle.value.maxHeight],
  () => nextTick(updateStackFade),
);


function preload(key: AnimKey) {
  const u = urlOf(key);
  if (preloaded.has(u)) return preloaded.get(u)!;
  const v = document.createElement('video');
  v.muted = true;
  v.playsInline = true;
  v.preload = 'auto';
  v.src = u;
  try {
    v.load();
  } catch {
    /* ignore */
  }
  preloaded.set(u, v);
  return v;
}

function preloadMany(keys: AnimKey[]) {
  keys.forEach((k) => preload(k));
}

function pick<T extends string>(pool: readonly T[]): T {
  return pool[Math.floor(Math.random() * pool.length)]!;
}

/** Random clip from a pool, skipping the one already on screen (restarting it reads as a glitch). */
function pickAnim(pool: readonly AnimKey[]): AnimKey {
  const others = pool.filter((k) => k !== currentAnim.value);
  return pick(others.length ? others : pool);
}

/** Shuffle bag per pool: every clip in it plays once before any of them repeats. */
const animBags = new Map<string, { bag: AnimKey[]; last?: AnimKey }>();
function drawAnim(pool: readonly AnimKey[]): AnimKey {
  const id = pool.join();
  const entry = animBags.get(id) ?? { bag: [] };
  if (!entry.bag.length) {
    const bag = [...pool];
    for (let i = bag.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [bag[i], bag[j]] = [bag[j]!, bag[i]!];
    }
    // A fresh round must not open with the clip the last round ended on.
    if (bag.length > 1 && bag.at(-1) === entry.last) [bag[0], bag[bag.length - 1]] = [bag.at(-1)!, bag[0]!];
    entry.bag = bag;
    animBags.set(id, entry);
  }
  entry.last = entry.bag.pop()!;
  return entry.last;
}

/**
 * Every clip (5 or 10 s) ends in the pose it started from, so a cut at a clip
 * boundary is a small pose change while a mid-clip cut is a visible pose jump.
 * - ambient: things she does on her own (idle cycle, nudges, dozing off) wait for the current clip to end.
 * - react:   answers to the user (poke, pet, feed, chat result) let the current reaction read for REACT_HOLD_MS first.
 * - urgent:  physical or state changes (drag, hold, throw, punch, wake) cut in at once.
 */
type AnimPriority = 'ambient' | 'react' | 'urgent';
type AnimOpts = {
  loop?: boolean;
  thenIdle?: boolean;
  /** Restart a loop that is already playing. How soon a clip cuts in is decided by `priority` alone. */
  restart?: boolean;
  then?: AnimKey;
  priority?: AnimPriority;
  /** Runs when the clip actually appears (it may have waited in the queue). */
  onStart?: () => void;
};
const REACT_HOLD_MS = 2000;
const SWAP_TIMEOUT_MS = 3000;
/** Must cover the CSS fade in `.ff-video.blend` (incoming 140ms; outgoing 120ms after a 70ms delay). */
const BLEND_MS = 220;
const blending = ref(false);
let blendTimer: number | undefined;
/** A back-slot load is in progress; the front clip ending meanwhile must not start a competing swap. */
let swapping = false;

let clip: { priority: AnimPriority; loop: boolean; startedAt: number } = {
  priority: 'ambient',
  loop: true,
  startedAt: 0,
};
let queuedAnim: { key: AnimKey; opts: AnimOpts } | null = null;
let animQueueTimer: number | undefined;
let idleSince = Date.now();

function clearAnimQueue() {
  queuedAnim = null;
  window.clearTimeout(animQueueTimer);
  animQueueTimer = undefined;
}

function runQueuedAnim() {
  const q = queuedAnim;
  clearAnimQueue();
  if (q && !collapsed.value) void swapTo(q.key, q.opts);
}

/** Let the looping front clip finish its current cycle so `ended` fires at a clean boundary. */
function endFrontLoop() {
  if (frontIsA.value) loopA.value = false;
  else loopB.value = false;
}

/** How long she has been sitting in plain idle with nothing waiting (0 if busy with a clip). */
function idleMs() {
  return currentAnim.value === 'idle' && !queuedAnim ? Date.now() - idleSince : 0;
}

function playAnim(key: AnimKey, opts: AnimOpts = {}) {
  if (collapsed.value) return;
  if (!opts.restart && key === currentAnim.value && opts.loop) return;
  const priority = opts.priority ?? 'react';
  // Already doing exactly this; restarting would snap her back to the clip's first frame.
  if (priority !== 'urgent' && !opts.loop && key === currentAnim.value) return;

  if (priority === 'urgent') {
    clearAnimQueue();
    void swapTo(key, opts);
    return;
  }

  if (priority === 'ambient') {
    if (queuedAnim) return;
    if (clip.loop && clip.priority !== 'ambient') return;
    queuedAnim = { key, opts };
    if (clip.loop) endFrontLoop();
    return;
  }

  const elapsed = Date.now() - clip.startedAt;
  const reactionShowing = !clip.loop && clip.priority !== 'ambient' && elapsed < REACT_HOLD_MS;
  if (!reactionShowing) {
    clearAnimQueue();
    void swapTo(key, opts);
    return;
  }
  if (key === currentAnim.value) return;
  queuedAnim = { key, opts };
  window.clearTimeout(animQueueTimer);
  animQueueTimer = window.setTimeout(runQueuedAnim, REACT_HOLD_MS - elapsed);
}

/** Dual-buffer swap: load into the back slot, promote it only once it has a painted frame. */
async function swapTo(key: AnimKey, opts: AnimOpts) {
  if (collapsed.value) return;
  const wantLoop = !!opts.loop;
  const priority: AnimPriority = key === 'idle' ? 'ambient' : (opts.priority ?? 'react');
  const nextUrl = urlOf(key);
  preload(key);
  clip = { priority, loop: wantLoop, startedAt: Date.now() };

  const swapGen = (animGen += 1);
  pendingEnd = null;
  swapping = true;
  const useA = !frontIsA.value;
  // Even at a clip boundary the rest poses differ in hair, tail and face, so blend every cut from a painted frame.
  const outgoingNow = useA ? slotB.value : slotA.value;
  const blend = !!outgoingNow && outgoingNow.readyState >= 2;
  if (useA) {
    srcA.value = nextUrl;
    loopA.value = wantLoop;
  } else {
    srcB.value = nextUrl;
    loopB.value = wantLoop;
  }
  await nextTick();
  if (swapGen !== animGen) return;
  const v = useA ? slotA.value : slotB.value;
  if (!v) {
    swapping = false;
    return;
  }

  let promoted = false;
  const promote = () => {
    if (promoted || swapGen !== animGen) return;
    promoted = true;
    window.clearTimeout(watchdog);
    swapping = false;
    window.clearTimeout(blendTimer);
    blending.value = blend;
    if (useA) {
      opA.value = 1;
      opB.value = 0;
    } else {
      opB.value = 1;
      opA.value = 0;
    }
    const outgoing = useA ? slotB.value : slotA.value;
    const stopOutgoing = () => {
      if (!outgoing || outgoing === v || (frontIsA.value ? slotA.value : slotB.value) === outgoing) return;
      try {
        outgoing.pause();
      } catch {
        /* ignore */
      }
    };
    if (blend) {
      // Keep the old clip moving while it fades out; a frozen frame under the fade reads as a stutter.
      blendTimer = window.setTimeout(() => {
        blending.value = false;
        if (swapGen === animGen) stopOutgoing();
      }, BLEND_MS);
    } else {
      stopOutgoing();
    }
    frontIsA.value = useA;
    if (key === 'idle' && currentAnim.value !== 'idle') idleSince = Date.now();
    currentAnim.value = key;
    // An ambient clip queued while this one was loading must not wait behind an endless loop.
    if (wantLoop && queuedAnim && queuedAnim.opts.priority === 'ambient') endFrontLoop();
    opts.onStart?.();
    if (!wantLoop) {
      const endGen = swapGen;
      pendingEnd = () => {
        if (endGen !== animGen || currentAnim.value !== key) return;
        if (dragging.value || holding.value) return;
        if (opts.then) {
          void swapTo(opts.then, { loop: false, priority, thenIdle: opts.thenIdle });
          return;
        }
        if (opts.thenIdle !== false) {
          void swapTo(sleeping.value ? 'sleepLoop' : 'idle', { loop: true, priority: 'ambient' });
        }
      };
    } else {
      pendingEnd = null;
    }
  };

  // Only promote a frame from the clip's start; a reused slot may still hold the frame it was paused on.
  let frameTries = 0;
  const afterPlay = () => {
    if (swapGen !== animGen) return;
    const anyV = v as HTMLVideoElement & {
      requestVideoFrameCallback?: (cb: (now: number, meta: { mediaTime: number }) => void) => number;
    };
    if (typeof anyV.requestVideoFrameCallback !== 'function') {
      promote();
      return;
    }
    anyV.requestVideoFrameCallback((_now, meta) => {
      if (meta.mediaTime > 0.5 && frameTries++ < 6) afterPlay();
      else promote();
    });
  };

  // A clip that fails to load must not leave her frozen on the old one forever.
  const fail = () => {
    window.clearTimeout(watchdog);
    if (promoted || swapGen !== animGen) return;
    swapping = false;
    if (key !== 'idle') void swapTo('idle', { loop: true, priority: 'ambient' });
  };
  const watchdog = window.setTimeout(fail, SWAP_TIMEOUT_MS);
  v.addEventListener('error', fail, { once: true });

  const start = () => {
    if (swapGen !== animGen) return;
    const playP = v.play();
    if (playP && typeof (playP as Promise<void>).then === 'function') {
      (playP as Promise<void>).then(afterPlay).catch(fail);
    } else {
      afterPlay();
    }
  };

  let readyHandled = false;
  const onReady = () => {
    if (readyHandled) return;
    readyHandled = true;
    v.removeEventListener('loadeddata', onReady);
    if (swapGen !== animGen) return;
    if (v.currentTime > 0.05) {
      v.addEventListener('seeked', start, { once: true });
      v.currentTime = 0;
    } else {
      start();
    }
  };

  v.addEventListener('loadeddata', onReady);
  // If already decoded for this src, loadeddata may not re-fire.
  if (v.readyState >= 2) {
    onReady();
  }
}

function onEnded(which: 'a' | 'b') {
  const isFront = (which === 'a') === frontIsA.value;
  if (!isFront || swapping) return;
  if (queuedAnim) {
    runQueuedAnim();
    return;
  }
  if (sleeping.value && (currentAnim.value === 'sleepStart' || currentAnim.value === 'nap')) {
    void swapTo('sleepLoop', { loop: true, priority: 'ambient' });
    return;
  }
  if (pendingEnd) {
    const fn = pendingEnd;
    pendingEnd = null;
    fn();
  } else if (!dragging.value && !holding.value) {
    void swapTo(sleeping.value ? 'sleepLoop' : 'idle', { loop: true, priority: 'ambient' });
  }
}

/** How long she stays awake without attention, and how long a nap lasts before she wakes on her own. */
function idleTimings() {
  switch (careState.value) {
    case 'tired':
      return { awake: 45_000, nap: 4 * 60_000 };
    case 'happy':
      return { awake: 5 * 60_000, nap: 90_000 };
    default:
      return { awake: 3 * 60_000, nap: 2 * 60_000 };
  }
}

function wakeOnOwn() {
  if (!sleeping.value || busy.value || dragging.value || holding.value) return;
  sleeping.value = false;
  void playAnim('wake', {
    then: 'stretch',
    priority: 'ambient',
    onStart: () => maybeIdleSay(LINES.wakeSelf, 0.6),
  });
  pokeIdleClock();
}

function pokeIdleClock() {
  window.clearTimeout(sleepTimer);
  sleeping.value = false;
  const { awake, nap } = idleTimings();
  sleepTimer = window.setTimeout(() => {
    if (collapsed.value || dragging.value || busy.value || menuOpen.value || holding.value) return;
    sleeping.value = true;
    sleepTimer = window.setTimeout(wakeOnOwn, nap);
    const start = Math.random() > 0.55 ? 'sleepStart' : Math.random() > 0.5 ? 'yawn' : 'nap';
    // Doze off once the current clip is done, not mid-move; dozing outranks any idle flourish still queued.
    clearAnimQueue();
    void playAnim(start, {
      thenIdle: false,
      priority: 'ambient',
      then: start === 'yawn' ? 'sleepStart' : undefined,
      onStart: () => maybeIdleSay(LINES.sleep, 0.55),
    });
  }, awake);
}

/** The dedicated 点击回应 clips carry most pokes; the prop tricks are the occasional surprise. */
const POKE_ANIMS: AnimKey[] = ['pokeHappy', 'pokeWave', 'pokeShy', 'pokeTickle', 'curtsy', 'knock'];
const POKE_SURPRISE_ANIMS: AnimKey[] = ['jump', 'spin', 'flower', 'bubbles', 'balloon', 'pigeon'];
/** Kept apart so a poke never looks like a hit and a hit never looks like a poke. */
const FLURRY_ANIMS: AnimKey[] = ['pokeAngry', 'tailSlap', 'rageGame'];
const PUNCH_ANIMS: AnimKey[][] = [
  ['squash', 'scare'],
  ['wakeScare', 'sigh', 'squash'],
  ['sigh', 'scare', 'wakeScare'],
];

function pickPoke(): AnimKey {
  if (clickCount >= 5) return pickAnim(['pokeAngry', 'tailSlap']);
  if (clickCount >= 3 && Math.random() > 0.45) return pickAnim(['pokeAngry', 'pokeShy']);
  return pickAnim(Math.random() < 0.75 ? POKE_ANIMS : POKE_SURPRISE_ANIMS);
}

function notePoke(times = 1) {
  clickCount += times;
  window.clearTimeout(clickDecayTimer);
  clickDecayTimer = window.setTimeout(() => {
    clickCount = 0;
  }, 2800);
}

function placeMenu() {
  const pad = 8;
  const gap = 8;
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const petL = pos.x;
  const petT = pos.y;
  const petR = pos.x + petW();
  const petB = pos.y + petH();
  const el = menuEl.value;
  const w = el && el.offsetWidth ? el.offsetWidth : 168;
  const h = el && el.offsetHeight ? el.offsetHeight : 12 + (collapsed.value ? 5 : 8) * 34;

  const roomRight = vw - pad - (petR + gap);
  const roomLeft = petL - gap - pad;
  const roomBottom = vh - pad - (petB + gap);
  const roomTop = petT - gap - pad;

  let x: number;
  let y: number;

  // Prefer sitting beside her on the side with more room, so the menu does not cover her.
  if (roomRight >= w && roomRight >= roomLeft) {
    x = petR + gap;
  } else if (roomLeft >= w) {
    x = petL - gap - w;
  } else if (roomRight >= w) {
    x = petR + gap;
  } else if (roomRight >= roomLeft) {
    x = petR + gap;
  } else {
    x = petL - gap - w;
  }

  y = petT;
  if (y + h > vh - pad) y = vh - pad - h;
  if (y < pad) y = pad;

  const overlaps = !(x + w <= petL + 1 || x >= petR - 1 || y + h <= petT + 1 || y >= petB - 1);
  if (overlaps) {
    if (roomBottom >= h) {
      y = petB + gap;
      x = Math.min(Math.max(pad, petL), Math.max(pad, vw - pad - w));
    } else if (roomTop >= h) {
      y = petT - gap - h;
      x = Math.min(Math.max(pad, petL), Math.max(pad, vw - pad - w));
    }
  }

  x = Math.min(Math.max(pad, x), Math.max(pad, vw - pad - w));
  y = Math.min(Math.max(pad, y), Math.max(pad, vh - pad - h));
  menuPos.x = Math.round(x);
  menuPos.y = Math.round(y);
}

function onContextMenu(ev: MouseEvent) {
  // Non-blocking custom popover — never use window.confirm / native menus.
  // Only cancel the browser context menu on the pet hit-target itself.
  // Opening/moving over the menu must NOT start body animations.
  ev.preventDefault();
  ev.stopPropagation();
  // Right-click again puts the menu away, like the double-click toggle for the input.
  if (menuOpen.value) {
    closeMenu();
    return;
  }
  careTick(sleeping.value);
  menuOpen.value = true;
  placeMenu();
  nextTick(() => placeMenu());
}

function closeMenu() {
  menuOpen.value = false;
}

function dropTaps() {
  window.clearTimeout(tapTimer);
  tapTimer = undefined;
  tapCount = 0;
}

function resetPointer() {
  window.clearTimeout(holdTimer);
  dropTaps();
  pointerMode = 'none';
  pressing.value = false;
  dragging.value = false;
  holding.value = false;
  squish.value = 1;
}

function onPointerDown(ev: PointerEvent) {
  if (collapsed.value || ev.button !== 0) return;
  (ev.currentTarget as HTMLElement).setPointerCapture(ev.pointerId);
  // Keep counting taps across presses; only a release decides whether the burst is over.
  window.clearTimeout(tapTimer);
  tapTimer = undefined;
  cancelAnimationFrame(physicsRaf);
  physicsRaf = 0;
  pointerMode = 'pending';
  pressing.value = true;
  dragging.value = false;
  holding.value = false;
  petStage = 0;
  squish.value = 0.96;
  if (rhythm.value || shellPlay.value) {
    // Rhythm is keyboard-only; the shell game handles its own pointer events with .stop.
    dropTaps();
    pointerMode = 'none';
    pressing.value = false;
    squish.value = 1;
    try {
      (ev.currentTarget as HTMLElement).releasePointerCapture(ev.pointerId);
    } catch {
      /* ignore */
    }
    return;
  }
  if (fleeing.value) {
    onCaughtWhileFleeing();
  }
  downAt = { x: ev.clientX, y: ev.clientY, t: Date.now() };
  dragOff = { x: ev.clientX - pos.x, y: ev.clientY - pos.y };
  lastDrag = { x: ev.clientX, y: ev.clientY, t: performance.now() };
  strokeWindow = { x: ev.clientX, count: 0 };
  closeMenu();
  vel.x = 0;
  vel.y = 0;
  window.clearTimeout(holdTimer);
  // snappier hold → squish
  holdTimer = window.setTimeout(() => {
    if (pointerMode !== 'pending') return;
    dropTaps();
    pointerMode = 'hold';
    holding.value = true;
    squish.value = 0.76;
    void playAnim('squash', { loop: true, restart: true, priority: 'urgent' });
    maybeIdleSay(LINES.hold, 0.4);
  }, 520);
}

function onPointerMove(ev: PointerEvent) {
  if (pointerMode === 'none') return;
  const dx = ev.clientX - downAt.x;
  const dy = ev.clientY - downAt.y;
  const dist = Math.hypot(dx, dy);

  if (pointerMode === 'pending' || pointerMode === 'hold' || pointerMode === 'stroke') {
    if (strokeWindow) {
      const moved = Math.abs(ev.clientX - strokeWindow.x);
      if (moved > 7) {
        strokeWindow.count += 1;
        strokeWindow.x = ev.clientX;
      }
    }
    if (dist > 28) {
      window.clearTimeout(holdTimer);
      if (Math.abs(dy) > Math.abs(dx) * 0.7 || dist > 40) {
        dropTaps();
        pointerMode = 'drag';
        dragging.value = true;
        holding.value = false;
        squish.value = 1;
        sleeping.value = false;
        void playAnim('drag', { loop: true, restart: true, priority: 'urgent' });
      } else if (strokeWindow && strokeWindow.count >= 1 && dist < 100) {
        dropTaps();
        pointerMode = 'stroke';
        holding.value = false;
        squish.value = 1;
        sleeping.value = false;
        const stage = strokeWindow.count;
        if (stage >= 6 && petStage < 3) {
          petStage = 3;
          onCare('pet', 3);
          void playAnim(pickAnim(['petCat', 'pokeTickle', 'balloon', 'hum']));
          maybeIdleSay(LINES.pet3, 0.45, 'pet');
        } else if (stage >= 3 && petStage < 2) {
          petStage = 2;
          onCare('pet', 2);
          void playAnim(pickAnim(['pokeTickle', 'pokeHappy', 'sway', 'fan']));
          maybeIdleSay(LINES.pet2, 0.4, 'pet');
        } else if (petStage < 1) {
          petStage = 1;
          onCare('pet', 1);
          void playAnim(pickAnim(['pokeShy', 'pokeWave', 'look']));
          maybeIdleSay(LINES.pet1, 0.4, 'pet');
        }
      }
    }
  }

  if (pointerMode === 'drag') {
    const now = performance.now();
    const dt = Math.max(6, now - lastDrag.t);
    vel.x = ((ev.clientX - lastDrag.x) / dt) * 16;
    vel.y = ((ev.clientY - lastDrag.y) / dt) * 16;
    lastDrag = { x: ev.clientX, y: ev.clientY, t: now };
    pos.x = clamp(ev.clientX - dragOff.x, 0, window.innerWidth - SIZE);
    pos.y = clamp(ev.clientY - dragOff.y, 0, window.innerHeight - SIZE);
    // Turn only on a clear sideways move; hand jitter used to mirror her back and forth (flicker).
    const dir = vel.x < 0 ? -1 : 1;
    if (Math.abs(vel.x) > 2.5 && dir !== facing.value && now - lastFlipAt > 300) {
      facing.value = dir;
      lastFlipAt = now;
    }
  }
}

function onPointerUp(ev: PointerEvent) {
  if (pointerMode === 'none') return;
  window.clearTimeout(holdTimer);
  try {
    (ev.currentTarget as HTMLElement).releasePointerCapture(ev.pointerId);
  } catch {
    /* ignore */
  }
  const mode = pointerMode;
  pointerMode = 'none';
  pressing.value = false;
  const held = Date.now() - downAt.t;
  const dist = Math.hypot(ev.clientX - downAt.x, ev.clientY - downAt.y);

  if (mode === 'hold') {
    holding.value = false;
    squish.value = 1.14;
    window.setTimeout(() => {
      squish.value = 1;
    }, 120);
    void playAnim('jump', { then: 'spin', priority: 'urgent' });
    maybeIdleSay(LINES.pop, 0.35);
    pokeIdleClock();
    return;
  }

  if (mode === 'drag') {
    dragging.value = false;
    const speed = Math.hypot(vel.x, vel.y);
    if (speed > 9) {
      void playAnim('scare', { priority: 'urgent' });
      maybeIdleSay(LINES.throw, 0.5);
      startPhysics();
    } else {
      // soft land → bounce recover
      void playAnim('squash', { priority: 'urgent' });
      maybeIdleSay(LINES.softLand, 0.4);
      pokeIdleClock();
    }
    return;
  }

  if (mode === 'stroke') {
    if (Date.now() < soreUntil.value) {
      soreUntil.value = 0;
      punchCount = 0;
      onCare('comfort');
      void playAnim(pickAnim(['pokeShy', 'hum', 'petCat', 'curtsy', 'pokeHappy']));
      say(pick(LINES.comfort));
      stopFlee();
      punchCount = 0;
    } else if (petStage >= 2) {
      void playAnim(pickAnim(['celebrate', 'hum', 'petCat', 'redPacket']));
    }
    pokeIdleClock();
    return;
  }

  if (dist < 22 && held < 480) {
    recordPetTap(ev);
    return;
  }
  squish.value = 1;
}

/** Shared native visual/interaction path for ordinary and easter-egg captured pointerup. */
function recordPetTap(ev: PointerEvent, streak?: number) {
  const hit = (ev.target as Element).closest('.ff-pet');
  if (!hit) return;
  // Every tap answers at once (mark + squish); what the burst means is decided once the taps stop.
  window.clearTimeout(tapTimer);
  tapCount += 1;
  const box = hit.getBoundingClientRect();
  const at = { x: ev.clientX - box.left, y: ev.clientY - box.top };
  // The easter-egg streak survives the 260ms burst gap, so it is the count worth showing.
  const mark = pokeHitPresentation(Math.max(tapCount, streak ?? 0), Date.now() < soreUntil.value);
  if (mark.kind === 'punch') {
    squish.value = 0.88;
    shakeHit();
  } else {
    squish.value = 1.04;
    if (tapCount === 3 && !sleeping.value) startFlurry();
  }
  showHitMark(at, mark.text, mark.kind);
  window.setTimeout(() => {
    if (pointerMode === 'none') squish.value = 1;
  }, 130);
  tapTimer = window.setTimeout(resolveTaps, TAP_GAP_MS);
}


let hitMarkSeq = 0;
function showHitMark(at: { x: number; y: number }, text: string, kind: HitMark['kind']) {
  const id = ++hitMarkSeq;
  hitMarks.value = [...hitMarks.value.slice(-5), { id, x: at.x, y: at.y, text, kind }];
  window.setTimeout(() => {
    hitMarks.value = hitMarks.value.filter((m) => m.id !== id);
  }, 700);
}

let hitShakeTimer: number | undefined;
function shakeHit() {
  hitShake.value = true;
  window.clearTimeout(hitShakeTimer);
  hitShakeTimer = window.setTimeout(() => {
    hitShake.value = false;
  }, 260);
}

/** The third quick poke gets a reaction right away instead of after the burst ends. */
function startFlurry() {
  void playAnim(pickAnim(FLURRY_ANIMS), { priority: 'urgent' });
  say(lineFor('flurry', LINES.pokeFlurry));
}

/** Taps within TAP_GAP_MS of each other form one burst: 1 = poke, 2 = open chat, 3+ = a poke flurry. */
function resolveTaps() {
  const n = tapCount;
  dropTaps();
  if (!n || collapsed.value || dragging.value || holding.value || discoActive.value || discoPending.value) return;
  // The press that caught her mid-flee already got its reaction; it is not also a punch.
  if (Date.now() - caughtAt < 1000) return;
  if (sleeping.value) {
    sleeping.value = false;
    void playAnim('wake', { then: 'wakeScare', priority: 'urgent' });
    maybeIdleSay(n >= 3 ? LINES.pokeFlurry : LINES.wake, 0.55);
    pokeIdleClock();
    return;
  }
  if (n === 2) {
    if (!discoFlurrying()) toggleChatDialog();
    return;
  }
  // After a recent reply (or punch streak), a tap is a 揍 — a flurry counts as several hits.
  if (Date.now() < soreUntil.value) {
    punchCount += Math.max(0, n - 2);
    doPunch();
    return;
  }
  notePoke(n);
  if (n >= 3) {
    // startFlurry() already reacted on the third tap; a long burst only gets one more word.
    if (n >= 6) say(lineFor('flurry', LINES.pokeFlurry));
  } else {
    void playAnim(pickPoke());
    maybeIdleSay(LINES.poke, 0.38, 'poke');
  }
  pokeIdleClock();
}


function startPhysics() {
  cancelAnimationFrame(physicsRaf);
  const step = () => {
    vel.y += 0.92;
    vel.x *= 0.991;
    pos.x += vel.x;
    pos.y += vel.y;
    const maxX = window.innerWidth - SIZE;
    const maxY = window.innerHeight - SIZE;
    if (pos.x < 0) {
      pos.x = 0;
      vel.x *= -0.5;
      facing.value = 1;
    } else if (pos.x > maxX) {
      pos.x = maxX;
      vel.x *= -0.5;
      facing.value = -1;
    }
    if (pos.y >= maxY) {
      pos.y = maxY;
      if (Math.abs(vel.y) < 2.6 && Math.abs(vel.x) < 1.5) {
        vel.x = 0;
        vel.y = 0;
        // The throw clip carries the whole flight; only the final landing swaps clips.
        void playAnim('squash', { priority: 'urgent' });
        maybeIdleSay(LINES.hardLand, 0.4);
        pokeIdleClock();
        return;
      }
      vel.y *= -0.5;
      vel.x *= 0.84;
    }
    physicsRaf = requestAnimationFrame(step);
  };
  physicsRaf = requestAnimationFrame(step);
}



function releaseDockToBall() {
  if (!docked.value) return;
  const origin = avatarOriginInCapsule();
  pos.x += origin.x;
  pos.y += origin.y;
  docked.value = false;
}

function settleAsFreeBall() {
  docked.value = false;
  settleAsFreeBallOf(pos);
}

function nearMagnetEdge() {
  return nearMagnetEdgeOf(pos);
}

function magnetSnapBall() {
  const { edge, targetX, targetY } = magnetSnapTarget(pos);
  // Keep the avatar where it is while the stage grows into a capsule, then slide the stage.
  const avatar = { x: pos.x, y: pos.y };
  dockEdge.value = edge;
  const o = avatarOriginInCapsuleOf(edge);
  pos.x = avatar.x - o.x;
  pos.y = avatar.y - o.y;
  docked.value = true;
  snapRaf = animateSnap(pos, targetX, targetY, snapRaf);
}

function onBallPointerDown(ev: PointerEvent) {
  if (ev.button !== 0) return;
  (ev.currentTarget as HTMLElement).setPointerCapture(ev.pointerId);
  cancelAnimationFrame(snapRaf);
  snapRaf = 0;
  ballDragging.value = false;
  ballMoved = false;
  pressing.value = true;
  ballDown = { x: ev.clientX, y: ev.clientY, px: pos.x, py: pos.y, t: Date.now() };
  closeMenu();
}

function onBallPointerMove(ev: PointerEvent) {
  if (!ballDown) return;
  const dx = ev.clientX - ballDown.x;
  const dy = ev.clientY - ballDown.y;
  if (!ballMoved && Math.hypot(dx, dy) > 8) {
    ballMoved = true;
    ballDragging.value = true;
    releaseDockToBall();
    ballDown.px = pos.x;
    ballDown.py = pos.y;
  }
  if (!ballMoved) return;
  pos.x = clamp(ballDown.px + dx, 0, window.innerWidth - BALL);
  pos.y = clamp(ballDown.py + dy, 0, window.innerHeight - BALL);
}

function onBallPointerUp(ev: PointerEvent) {
  if (!ballDown) return;
  try {
    (ev.currentTarget as HTMLElement).releasePointerCapture(ev.pointerId);
  } catch {
    /* ignore */
  }
  const moved = ballMoved;
  ballDown = null;
  pressing.value = false;
  ballDragging.value = false;
  if (!moved) return;
  if (nearMagnetEdge()) magnetSnapBall();
  else settleAsFreeBall();
}

function onBallDblClick(ev: MouseEvent) {
  ev.preventDefault();
  ev.stopPropagation();
  toggleChatDialog();
}


function toggleCollapse() {
  closeMenu();
  clearRhythm();
  clearPlay();
  collapsed.value = !collapsed.value;
  // Keep the visual center: the pet box is SIZE, the ball is BALL.
  const centerShift = (SIZE - BALL) / 2;
  if (collapsed.value) {
    docked.value = false;
    pos.x += centerShift;
    pos.y += centerShift;
    settleAsFreeBall();
    animGen += 1;
    pendingEnd = null;
    swapping = false;
    window.clearTimeout(blendTimer);
    blending.value = false;
    clearAnimQueue();
    dropTaps();
    hovered.value = false;
    slotA.value?.pause();
    slotB.value?.pause();
  } else {
    docked.value = false;
    pos.x -= centerShift;
    pos.y -= centerShift;
    expandFromBall(pos);
    void playAnim('pokeWave', { priority: 'urgent' });
    maybeIdleSay(LINES.expand, 0.4);
    pokeIdleClock();
  }
}





function armSore(ms = 20000) {
  soreUntil.value = Date.now() + ms;
  // Nudge cursor computed while window open (Date.now() alone is not reactive).
  window.clearInterval(soreTick);
  soreTick = window.setInterval(() => {
    if (Date.now() >= soreUntil.value) {
      window.clearInterval(soreTick);
      soreTick = undefined;
      soreUntil.value = 0;
    } else {
      // touch ref to refresh cursor
      soreUntil.value = soreUntil.value;
    }
  }, 400);
}

function stopFlee() {
  fleeing.value = false;
  window.clearTimeout(fleeTimer);
  cancelAnimationFrame(fleeRaf);
}

function startFlee() {
  stopFlee();
  fleeing.value = true;
  const maxX = Math.max(8, window.innerWidth - SIZE - 8);
  const maxY = Math.max(8, window.innerHeight - SIZE - 8);
  const ang = Math.random() * Math.PI * 2;
  const dist = 160 + Math.random() * 280;
  let tx = pos.x + Math.cos(ang) * dist;
  let ty = pos.y + Math.sin(ang) * dist;
  tx = Math.min(maxX, Math.max(8, tx));
  ty = Math.min(maxY, Math.max(8, ty));
  if (Math.hypot(tx - pos.x, ty - pos.y) < 90) {
    tx = Math.min(maxX, Math.max(8, pos.x - Math.cos(ang) * dist));
    ty = Math.min(maxY, Math.max(8, pos.y - Math.sin(ang) * dist));
  }
  facing.value = tx >= pos.x ? 1 : -1;
  const gait = pick(['run', 'trot', 'runTurn', 'crab', 'scare', 'spin']);
  void playAnim(gait, { loop: true, restart: true, priority: 'urgent' });
  say(pick([...LINES.flee, ...LINES.punchMore]));
  const t0 = performance.now();
  const startX = pos.x;
  const startY = pos.y;
  const dur = 520 + Math.random() * 420;
  const step = (now: number) => {
    if (!fleeing.value) return;
    const u = Math.min(1, (now - t0) / dur);
    const e = 1 - Math.pow(1 - u, 2);
    pos.x = startX + (tx - startX) * e;
    pos.y = startY + (ty - startY) * e;
    if (u < 1) fleeRaf = requestAnimationFrame(step);
    else {
      void playAnim(pickAnim(['squash', 'spin', 'scare']), { priority: 'urgent' });
      fleeTimer = window.setTimeout(() => {
        fleeing.value = false;
        pokeIdleClock();
      }, 900);
    }
  };
  fleeRaf = requestAnimationFrame(step);
}

function onCaughtWhileFleeing() {
  caughtAt = Date.now();
  stopFlee();
  armSore(12000);
  void playAnim(pickAnim(['scare', 'pokeShy', 'wakeScare', 'squash', 'spin']), { priority: 'urgent' });
  say(pick(LINES.caught));
  pokeIdleClock();
}


function doPunch() {
  // 「揍她」— escalate on repeat punches within a short window.
  punchCount += 1;
  armSore(12000);
  window.clearTimeout(punchTimer);
  punchTimer = window.setTimeout(() => {
    punchCount = 0;
  }, 4500);
  sleeping.value = false;
  onCare('punch');
  const n = punchCount;
  if (n < 4) void playAnim(pickAnim(PUNCH_ANIMS[n - 1]!), { priority: 'urgent' });
  if (n <= 1) {
    say(lineFor('punch', LINES.punch1));
  } else if (n === 2) {
    say(pick(LINES.punch2));
    // After a recent real reply, sometimes 重新回答 (once per question).
    if (lastUserQuestion.value && Math.random() > 0.35) {
      void maybeRetryAnswer();
    }
  } else if (n === 3) {
    say(pick(LINES.punch3));
    if (lastUserQuestion.value && retriedForQuestion.value !== lastUserQuestion.value && Math.random() > 0.55) {
      void maybeRetryAnswer();
    }
  } else {
    startFlee();
    return;
  }
  pokeIdleClock();
}

function flashBeat(ms = 200) {
  beatPulse.value = true;
  window.clearTimeout(beatPulseClearTimer);
  beatPulseClearTimer = window.setTimeout(() => {
    beatPulse.value = false;
  }, ms);
}

function clearRhythm() {
  window.removeEventListener('keydown', onRhythmKey, true);
  const r = rhythm.value;
  if (r?.pulseTimer) cancelAnimationFrame(r.pulseTimer);
  if (r?.endTimer) window.clearTimeout(r.endTimer);
  rhythm.value = null;
  beatPulse.value = false;
  window.clearTimeout(beatPulseClearTimer);
  lastLaneFlash.value = null;
}

function finishRhythm() {
  const r = rhythm.value;
  if (!r) return;
  const hits = r.hits;
  const mode = r.mode;
  clearRhythm();
  onCare(mode === 'dance' ? 'dance' : 'play', hits);
  if (hits >= 5) {
    void playAnim(pickAnim(['celebrate', 'pokeHappy', 'curtsy', 'spin']));
    say(pick(LINES.rhythmWin));
  } else {
    void playAnim(pickAnim(['sigh', 'pokeShy', 'look', 'yawn']));
    say(pick(LINES.rhythmMeh));
  }
  pokeIdleClock();
}

function clearPlay() {
  shellGameRef.value?.stop();
  shellPlay.value = false;
}

function onShellRound(p: { round: number; win: boolean }) {
  if (p.win) {
    void playAnim(pickAnim(['celebrate', 'pokeHappy', 'curtsy']));
    maybeIdleSay(LINES.playWin, 0.7);
  } else {
    void playAnim(pickAnim(['pokeShy', 'sigh', 'look']));
    maybeIdleSay(LINES.playMeh, 0.55);
  }
}

/** One watching loop per shuffle; only round results get their own clip, so the game doesn't strobe through clips. */
function onShellPhase(phase: 'ready' | 'show' | 'shuffle' | 'guess' | 'result') {
  if (phase === 'shuffle') void playAnim('think', { loop: true });
}

function onShellFinish(p: { wins: number; rounds: number }) {
  shellPlay.value = false;
  onCare('play', Math.max(1, p.wins * 3));
  if (p.wins >= Math.ceil(p.rounds / 2)) {
    void playAnim(pickAnim(['celebrate', 'pokeHappy', 'eat', 'curtsy']));
    say(pick(LINES.playWin));
  } else {
    void playAnim(pickAnim(['sigh', 'pokeShy', 'look', 'yawn']));
    say(pick(LINES.playMeh));
  }
  pokeIdleClock();
}

function startPlay() {
  if (fleeing.value) stopFlee();
  clearRhythm();
  clearPlay();
  say(pick(LINES.playGo));
  shellPlay.value = true;
}

function startRhythm(mode: 'dance' | 'play') {
  if (fleeing.value) stopFlee();
  clearRhythm();
  clearPlay();
  const count = 8 + Math.floor(Math.random() * 3);
  const travel = 1600;
  const gap = mode === 'dance' ? 560 : 620;
  const startAt = performance.now() + RHYTHM_COUNTDOWN_MS;
  const tStart = startAt + travel;
  const notes: FallNote[] = [];
  let prev: ArrowDir | null = null;
  for (let i = 0; i < count; i++) {
    const pool = ARROW_DIRS.filter((d) => d !== prev);
    const dir = pick(pool.length ? pool : ARROW_DIRS);
    prev = dir;
    const hitAt = tStart + i * gap;
    notes.push({
      id: i + 1,
      dir,
      spawnAt: hitAt - travel,
      hitAt,
      missAt: hitAt + 180,
    });
  }
  const state: RhythmState = {
    mode,
    notes,
    hits: 0,
    misses: 0,
    startAt,
    endAt: (notes[notes.length - 1]?.missAt ?? performance.now()) + 480,
  };
  void playAnim(pickAnim(mode === 'dance' ? DANCE_ANIMS : PLAYFUL_ANIMS), { loop: true, restart: true, priority: 'urgent' });
  say(pick(LINES.rhythmGo));
  window.addEventListener('keydown', onRhythmKey, true);
  fallNow.value = performance.now();
  const tick = () => {
    const cur = rhythm.value;
    if (!cur) return;
    const now = performance.now();
    fallNow.value = now;
    for (const n of cur.notes) {
      if (!n.judged && now > n.missAt) {
        n.judged = 'miss';
        cur.misses += 1;
        lastLaneFlash.value = { dir: n.dir, kind: 'miss', until: now + 180 };
      }
    }
    cur.pulseTimer = requestAnimationFrame(tick);
  };
  state.pulseTimer = requestAnimationFrame(tick);
  state.endTimer = window.setTimeout(() => finishRhythm(), Math.max(0, state.endAt - performance.now()));
  rhythm.value = state;
}

function onRhythmKey(ev: KeyboardEvent) {
  if (!rhythm.value || performance.now() < rhythm.value.startAt) return;
  if (ev.repeat) return;
  const el = ev.target as HTMLElement | null;
  if (el && el.closest('input, textarea')) return;
  const map: Record<string, ArrowDir> = {
    ArrowLeft: 'left',
    ArrowRight: 'right',
    ArrowUp: 'up',
    ArrowDown: 'down',
    a: 'left',
    A: 'left',
    d: 'right',
    D: 'right',
    w: 'up',
    W: 'up',
    s: 'down',
    S: 'down',
  };
  const dir = map[ev.key];
  if (!dir) return;
  ev.preventDefault();
  ev.stopPropagation();
  const r = rhythm.value;
  const now = performance.now();
  let best: FallNote | null = null;
  let bestDt = 240;
  for (const n of r.notes) {
    if (n.judged || n.dir !== dir) continue;
    const dt = Math.abs(n.hitAt - now);
    if (dt < bestDt) {
      bestDt = dt;
      best = n;
    }
  }
  if (best) {
    best.judged = 'hit';
    r.hits += 1;
    lastLaneFlash.value = { dir, kind: 'hit', until: now + 200 };
    flashBeat(180);
  } else {
    lastLaneFlash.value = { dir, kind: 'miss', until: now + 150 };
  }
}

async function menuAction(kind: string) {
  closeMenu();
  if (kind === 'chat') {
    openChatDialog();
    return;
  }
  if (kind === 'pin') {
    togglePin();
    return;
  }
  if (kind === 'look') {
    const ctx = collectPageContext();
    await chat(`看看我在看什么，俏皮点评一句并给个小建议。\n${ctx.heading || ctx.title}`, 'comment');
    return;
  }
  if (kind === 'fill') {
    if (!scanPageForm().fields.length && !collectPageContext().interactive) {
      say(pick(LINES.noForm));
      return;
    }
    await chat('检查当前表单', 'fill');
    return;
  }
  if (kind === 'feed') {
    // Always play an eat clip — even when "full" / anti-grind grants little satiety. 白饭 is her staple.
    const eats: AnimKey[] = ['eat', 'eatRice', 'eatRice', 'eatBowl', 'eatToken'];
    const hour = hourNow();
    if (hour >= 11 && hour < 14) eats.push('eatLunch', 'eatLunch');
    eats.push(...seasonalAnims().filter((k) => k.startsWith('eat')));
    const before = careState.value;
    const stuffed = care.value.satiety >= 85;
    // Picked from the menu on purpose, so it cuts in right away.
    void playAnim(pickAnim(stuffed ? ['eatCaught', 'fan'] : eats), { priority: 'urgent' });
    onCare('feed');
    say(stuffed ? pick(LINES.feedFull) : before === 'hungry' ? pick(LINES.feedHungry) : lineFor('feed', LINES.feed));
    pokeIdleClock();
    return;
  }
  if (kind === 'play') {
    startPlay();
    return;
  }
  if (kind === 'dance') {
    startRhythm('dance');
    return;
  }
  if (kind === 'disco') {
    // Must stay before any await: the menu click is the user gesture that lets the song autoplay.
    if (!discoActive.value && !discoPending.value) playDisco();
    return;
  }
  if (kind === 'ball') toggleCollapse();
}

function sendDraft() {
  const text = draft.value.trim();
  if (!text) return;
  draft.value = '';
  noteUserQuestion(text);
  say(text, 'user');
  void chat(text, 'chat');
}

function onKey(ev: KeyboardEvent) {
  if (ev.key === 'Enter' && !ev.shiftKey) {
    ev.preventDefault();
    sendDraft();
  }
  if (ev.key === 'Escape') {
    closeChatDialog();
    closeMenu();
  }
}

function onBubblesWheel(ev: WheelEvent) {
  if (!chatOpen.value && !hasCard.value) return;
  const el = ev.currentTarget as HTMLElement;
  ev.preventDefault();
  ev.stopPropagation();
  const dy = ev.deltaMode === 1 ? ev.deltaY * 16 : ev.deltaMode === 2 ? ev.deltaY * el.clientHeight : ev.deltaY;
  el.scrollTop += dy;
}

function onDocClick() {
  // Lightweight dismiss — does not capture or block page clicks.
  if (menuOpen.value) closeMenu();
  if (chatOpen.value) closeChatDialog();
}

function onHoverEnter() {
  hovered.value = true;
  // No playAnim on hover — mouse sweeping used to force-refresh look/pokeShy/curtsy constantly.
  if (collapsed.value || dragging.value || busy.value || sleeping.value || holding.value || menuOpen.value)
    return;
  // Rare bubble only (long cooldown); never interrupt the current clip.
  const now = Date.now();
  if (now - lastHoverSay > 28000) {
    lastHoverSay = now;
    maybeIdleSay(LINES.hover, 0.1);
  }
}

function onHoverLeave() {
  hovered.value = false;
}

function blocked() {
  return (
    discoBusy.value ||
    collapsed.value ||
    dragging.value ||
    busy.value ||
    sleeping.value ||
    menuOpen.value ||
    holding.value ||
    !!rhythm.value ||
    !!shellPlay.value ||
    pointerMode !== 'none'
  );
}

/** Natural idle cycle: glance / stretch / hum / props / wander — more often. */
const STATE_ANIMS: Partial<Record<CareState, AnimKey[]>> = {
  hungry: ['hungry', 'whatEat', 'eatCaught', 'sigh'],
  tired: ['yawn', 'nap', 'floatStep', 'yawn'],
  down: ['sigh', 'mutterIdle', 'pokeShy', 'look'],
};
const STATE_LINES: Partial<Record<CareState, readonly string[]>> = {
  hungry: LINES.stateHungry,
  tired: LINES.stateTired,
  down: LINES.stateDown,
  happy: LINES.stateHappy,
};
/** State lines are rarer than idle chatter: a mood you notice, not a nag. */
const STATE_SAY_COOLDOWN = 5 * 60_000;
let lastStateSay = 0;

function maybeSayState() {
  const pool = STATE_LINES[careState.value];
  if (!pool || chatOpen.value || Date.now() - lastStateSay < STATE_SAY_COOLDOWN) return;
  if (Math.random() > (careState.value === 'happy' ? 0.15 : 0.35)) return;
  lastStateSay = Date.now();
  say(pick(pool));
}

/** Plain idle she keeps between self-started clips (each clip already runs ~10 s). */
function ambientGap() {
  switch (careState.value) {
    case 'happy':
      return 12_000;
    case 'normal':
      return 20_000;
    default:
      return 30_000;
  }
}

/** Self-started clips only from plain idle, and never under the cursor — that reads as a hover reaction. */
function canAmbient() {
  return !blocked() && !hovered.value && idleMs() >= ambientGap();
}

function ambient(key: AnimKey, onStart?: () => void) {
  void playAnim(key, { priority: 'ambient', onStart });
}

function wanderStep() {
  if (!canAmbient()) return;
  const state = careState.value;
  const stateAnims = STATE_ANIMS[state];
  if (stateAnims && Math.random() < 0.5) {
    ambient(drawAnim(stateAnims), maybeSayState);
    return;
  }
  const lively = state === 'happy';
  const sayMood = lively ? maybeSayState : undefined;
  const hour = hourNow();
  const seasonal = seasonalAnims();
  const playToy = () =>
    ambient(drawAnim(PLAYFUL_ANIMS), () =>
      maybeIdleSay(['自己玩会儿～', '嘿！', '看我的～', '摸鱼时间到', '发明新游戏', '自娱自乐中'], 0.22, 'idle'),
    );

  // Bands: small 18% · calm 15% · seasonal (else toys) 10% · walk 27% · toys 16% · in place 14%.
  const roll = Math.random();
  if (roll < 0.18) {
    const small: AnimKey[] = ['look', 'stretch', 'floatStep'];
    if (hour >= 5 && hour < 10) small.push('brush');
    if (hour >= 22 || hour < 5 || hour === 14) small.push('yawn', 'yawn');
    ambient(drawAnim(small), sayMood);
    return;
  }
  if (roll < 0.33) {
    const calm = ['hum', 'mutterIdle', 'mutterScreen', 'mutterWipe', 'mirror', 'flute', 'violin', 'note'];
    const playful = ['sway', 'bees', 'flower', 'balloon', 'spin'];
    ambient(drawAnim(lively ? playful : calm), sayMood);
    return;
  }
  // Tired/hungry/down she stays put instead of roaming or playing.
  if (stateAnims) {
    ambient(drawAnim(['mutterIdle', 'mutterWipe', 'look', 'floatStep', 'hum']));
    return;
  }
  if (roll < 0.43) {
    if (seasonal.length) ambient(drawAnim(seasonal), sayMood);
    else playToy();
    return;
  }
  if (roll < 0.7 && !pinned.value) {
    const maxX = window.innerWidth - SIZE;
    const dir: 1 | -1 = pos.x < 60 ? 1 : pos.x > maxX - 60 ? -1 : Math.random() > 0.5 ? 1 : -1;
    const gait = drawAnim(['trot', 'run', 'crab', 'pace', 'runTurn']);
    ambient(gait, () => roam(gait, dir));
    return;
  }
  if (roll >= 0.7 && roll < 0.86) {
    playToy();
    return;
  }
  // In-place flourish (also where a pinned pet's walk turns go).
  ambient(
    drawAnim(
      lively
        ? ['sway', 'bees', 'animals', 'flower', 'balloon', 'pigeon', 'celebrate', 'dance', 'maidDance', 'swing']
        : ['sway', 'bees', 'flower', 'dress', 'note', 'archive', 'code', 'busy', 'mutter', 'mutterScreen'],
    ),
    sayMood,
  );
}

/** Glide sideways as a gait clip starts, easing to a stop; the clip itself still plays to its end. */
function roam(gait: AnimKey, dir: 1 | -1) {
  facing.value = dir;
  cancelAnimationFrame(roamRaf);
  const distance = 90 + Math.random() * 150;
  const dur = 1400 + Math.random() * 1200;
  const t0 = performance.now();
  const x0 = pos.x;
  const step = (now: number) => {
    if (currentAnim.value !== gait || dragging.value || holding.value || pinned.value || collapsed.value) return;
    const u = Math.min(1, (now - t0) / dur);
    const eased = 1 - Math.pow(1 - u, 2);
    pos.x = clamp(x0 + dir * distance * eased, 0, window.innerWidth - SIZE);
    if (u < 1) roamRaf = requestAnimationFrame(step);
  };
  roamRaf = requestAnimationFrame(step);
}

function bootGreeting(): { text: string; anim: AnimKey } {
  const hour = new Date().getHours();
  const state = careState.value;
  if (state === 'hungry') return { text: pick(LINES.bootHungry), anim: 'hungry' };
  if (awayHours.value >= 6 && hour >= 5 && hour < 11) {
    return { text: lineFor('morning', LINES.bootMorning), anim: pick(['stretch', 'brush']) };
  }
  if (awayHours.value >= 6) return { text: lineFor('welcomeBack', LINES.bootBack), anim: 'pokeWave' };
  if (hour >= 22 || hour < 5) return { text: lineFor('lateNight', LINES.bootLate), anim: 'yawn' };
  return { text: lineFor('greet', LINES.boot), anim: 'pokeWave' };
}

/** Unprompted remarks (time of day, page events) share one budget so they never pile up. */
const NUDGE_COOLDOWN = 3 * 60_000;
let lastNudgeAt = 0;
function canNudge() {
  return (
    !discoBusy.value && !collapsed.value && !busy.value && !document.hidden && !chatOpen.value && !hasCard.value &&
    !rhythm.value && !shellPlay.value && Date.now() - lastNudgeAt > NUDGE_COOLDOWN
  );
}
function nudge(pool: readonly string[], anim?: AnimKey, fresh?: FreshKind) {
  lastNudgeAt = Date.now();
  if (sleeping.value) {
    pokeIdleClock();
    void playAnim('wake', { then: anim ?? 'stretch' });
  } else if (anim) {
    ambient(anim);
  }
  say(fresh ? lineFor(fresh, pool) : pick(pool));
}

const DAILY_REMARKS: Array<{ id: string; from: number; to: number; pool: readonly string[]; anim: AnimKey; fresh: FreshKind }> = [
  { id: 'lunch', from: 11.67, to: 13, pool: LINES.lunch, anim: 'whatEat', fresh: 'lunch' },
  { id: 'offWork', from: 17.83, to: 19, pool: LINES.offWork, anim: 'stretch', fresh: 'offWork' },
  { id: 'late', from: 21.5, to: 24, pool: LINES.lateNight, anim: 'yawn', fresh: 'lateNight' },
];
function dailyRemark() {
  if (!canNudge()) return;
  const now = new Date();
  const hour = now.getHours() + now.getMinutes() / 60;
  const day = now.toDateString();
  let said: { day: string; ids: string[] } = { day, ids: [] };
  try {
    const saved = JSON.parse(localStorage.getItem(DAILY_REMARKS_KEY) || 'null');
    if (saved?.day === day) said = saved;
  } catch {
    /* fresh day */
  }
  const due = DAILY_REMARKS.find((r) => hour >= r.from && hour < r.to && !said.ids.includes(r.id));
  if (!due) return;
  said.ids.push(due.id);
  localStorage.setItem(DAILY_REMARKS_KEY, JSON.stringify(said));
  nudge(due.pool, due.anim, due.fresh);
}

let hiddenAt = 0;
function onVisibility() {
  if (document.hidden) {
    hiddenAt = Date.now();
    return;
  }
  if (hiddenAt && Date.now() - hiddenAt > 20 * 60_000 && canNudge()) nudge(LINES.welcomeBack, 'pokeWave', 'welcomeBack');
  hiddenAt = 0;
}

/** React to the host app's own toast messages (Element Plus), without knowing anything about the page. */
let toastObserver: MutationObserver | undefined;
function watchAppToasts() {
  toastObserver = new MutationObserver((records) => {
    for (const r of records) {
      for (const node of Array.from(r.addedNodes)) {
        if (!(node instanceof HTMLElement) || !node.classList.contains('el-message')) continue;
        const text = node.innerText || '';
        if (node.classList.contains('el-message--success') && /保存|提交|创建|更新/.test(text)) {
          if (canNudge() && Math.random() < 0.5) nudge(LINES.saved, pick(['celebrate', 'pokeHappy', 'curtsy']), 'saved');
        } else if (node.classList.contains('el-message--error')) {
          if (canNudge() && Math.random() < 0.4) nudge(LINES.appError, 'pokeShy');
        }
      }
    }
  });
  toastObserver.observe(document.body, { childList: true });
}

/** First visit to a page with a real form (save button + several fields) gets one quiet hint. */
const hintedFormPages = new Set<string>();
let lastPath = '';
function checkNewPage() {
  const path = location.pathname + location.search;
  if (path === lastPath) return;
  lastPath = path;
  if (hintedFormPages.has(location.pathname) || !canNudge()) return;
  window.setTimeout(() => {
    if (location.pathname + location.search !== path || !canNudge()) return;
    const form = scanPageForm();
    if (!form.saveButton || form.fields.length < 4) return;
    hintedFormPages.add(location.pathname);
    if (Math.random() < 0.5) nudge(LINES.formPage, 'pokeWave');
  }, 2500);
}

/**
 * Offer help only when the user seems stuck on an empty field (same field across two checks), at most once
 * per page per session, and with a local line — no model call, no interrupting real work.
 */
const offeredHelpOn = new Set<string>();
let stuckOn = '';
function offerFormHelp() {
  checkNewPage();
  if (collapsed.value || busy.value || document.hidden || sleeping.value || chatOpen.value || hasCard.value) return;
  const ctx = collectPageContext();
  const f = ctx.focused;
  const key = f && !f.value ? `${ctx.path}|${f.name || f.placeholder || ''}` : '';
  if (!key || key !== stuckOn) {
    stuckOn = key;
    return;
  }
  if (offeredHelpOn.has(ctx.path)) return;
  offeredHelpOn.add(ctx.path);
  if (canNudge()) nudge(LINES.offerHelp);
}

let linesBootTimer: number | undefined;
/** False while the current batch was written before the home page had fetched the weather. */
let linesKnewWeather = true;

/** Background refill of the model-written reaction lines; skipped while the models are serving the user. */
function refreshFreshLines(moodChanged = false) {
  if (busy.value) return;
  const knew = weatherNow() !== null;
  void refreshLines({ careMood: careMoodHint(), ambient: ambientHint() }, moodChanged).then((filled) => {
    if (filled) linesKnewWeather = knew;
  });
}

watch(careState, () => refreshFreshLines(true));

onMounted(() => {
  placeDefault();
  preloadMany([
    'idle',
    'look',
    'stretch',
    'drag',
    'squash',
    'jump',
    'pokeHappy',
    'pokeWave',
    'pokeTickle',
    'pokeShy',
    'sleepStart',
    'sleepLoop',
    'wake',
    'think',
    'trot',
    'run',
    'dance',
    'eat',
    'bubbles',
    'spin',
    'scare',
  ]);
  resumeCare();
  const greet = bootGreeting();
  void playAnim(greet.anim);
  say(greet.text);
  pokeIdleClock();
  wanderTimer = window.setInterval(wanderStep, 5000);
  careDecayTimer = window.setInterval(() => {
    careTick(sleeping.value);
    dailyRemark();
    refreshFreshLines(!linesKnewWeather && weatherNow() !== null);
  }, 60_000);
  linesBootTimer = window.setTimeout(() => refreshFreshLines(), 15_000);
  lastPath = location.pathname + location.search;
  observeTimer = window.setInterval(offerFormHelp, 15000);
  document.addEventListener('visibilitychange', onVisibility);
  watchAppToasts();
  window.addEventListener('resize', onWindowResize);
  document.addEventListener('click', onDocClick);
});

function onWindowResize() {
  pos.x = clamp(pos.x, 0, window.innerWidth - SIZE);
  pos.y = clamp(pos.y, 0, window.innerHeight - SIZE);
}

onBeforeUnmount(() => {
  window.clearTimeout(sleepTimer);
  window.clearTimeout(holdTimer);
  window.clearTimeout(punchTimer);
  window.clearTimeout(tapTimer);
  window.clearTimeout(animQueueTimer);
  window.clearTimeout(linesBootTimer);
  window.clearTimeout(blendTimer);
  window.clearTimeout(chatCloseTimer);
  window.clearInterval(wanderTimer);
  window.clearInterval(careDecayTimer);
  window.clearInterval(observeTimer);
  window.clearInterval(soreTick);
  document.removeEventListener('visibilitychange', onVisibility);
  window.removeEventListener('resize', onWindowResize);
  toastObserver?.disconnect();
  clearWaitBubble();
  clearRhythm();
  clearPlay();
  stopFlee();
  window.clearTimeout(beatPulseClearTimer);
  abortChat();
  cancelAnimationFrame(physicsRaf);
  cancelAnimationFrame(roamRaf);
  cancelAnimationFrame(snapRaf);
  document.removeEventListener('click', onDocClick);
});
</script>

<template>
  <div class="ff-root" aria-live="polite">
    <div
      class="ff-stage"
      @pointerdown.capture="discoDown"
      @pointermove.capture="discoMove"
      @pointerup.capture="discoUp"
      @pointercancel.capture="discoCancel"
      @dblclick.capture="discoAux"
      @contextmenu.capture="discoAux"
      :style="{
        left: `${pos.x}px`,
        top: `${pos.y}px`,
        width: collapsed ? `${petW()}px` : `${SIZE}px`,
        height: collapsed ? `${petH()}px` : `${SIZE}px`,
      }"
    >
      <div
        ref="bubblesEl"
        class="ff-bubbles"
        :class="{
          'chat-open': chatOpen,
          'has-card': hasCard,
          'fade-top': stackFade.top,
          'fade-bottom': stackFade.bottom,
        }"
        :style="bubbleStackStyle"
        @scroll.passive="updateStackFade"
        @wheel.prevent.stop="onBubblesWheel"
      >
        <template v-for="b in bubbles" :key="b.id">
          <div
            v-if="b.kind === 'card'"
            class="ff-bubble card"
            :class="[bubbleAlignClass(b.kind), bubbleTailClass(b.kind)]"
            @click.stop
            @pointerdown.stop
            @pointerenter="hoveredCard = b.id"
            @pointerleave="hoveredCard = null"
          >
            <div class="ff-card-head">
              <span class="ff-card-title">{{ b.title || '' }}</span>
              <button type="button" class="ff-card-x" aria-label="关闭" @click="onCardAction(b.id, 'close')">×</button>
            </div>
            <div class="ff-card-body">{{ b.text }}</div>
            <div v-if="b.note" class="ff-card-note">{{ b.note }}</div>
            <div v-if="b.actions?.length && !b.working" class="ff-card-actions">
              <button
                v-for="a in b.actions"
                :key="a.id"
                type="button"
                :class="{ primary: a.primary }"
                @click="onCardAction(b.id, a.id)"
              >
                {{ a.label }}
              </button>
            </div>
          </div>
          <div
            v-else
            class="ff-bubble"
            :class="[b.kind, bubbleAlignClass(b.kind), bubbleTailClass(b.kind)]"
            @click.stop="b.kind === 'wait' ? abortChat() : undefined"
          >
            {{ b.text }}
          </div>
        </template>
      </div>

      <div
        v-if="chatOpen"
        class="ff-pill"
        :style="chatPillStyle"
        @click.stop
        @pointerdown.stop
      >
        <input
          ref="chatInputEl"
          v-model="draft"
          type="text"
          maxlength="200"
          placeholder="想说点什么…"
          :disabled="busy"
          @keydown="onKey"
        />
        <button type="button" class="ff-pill-send" :disabled="busy" @click="sendDraft">发送</button>
      </div>

      <ShellGame
        v-if="shellPlay"
        ref="shellGameRef"
        :style="shellGameStyle"
        @round="onShellRound"
        @phase="onShellPhase"
        @finish="onShellFinish"
      />

      <button
        v-if="collapsed"
        type="button"
        class="ff-ball"
        :class="['dock-' + dockEdge, { dragging: ballDragging, docked }]"
        aria-label="展开大肥鱼"
        :style="{ cursor: petCursor }"
        @pointerdown="onBallPointerDown"
        @pointermove="onBallPointerMove"
        @pointerup="onBallPointerUp"
        @pointercancel="onBallPointerUp"
        @click.stop
        @dblclick="onBallDblClick"
        @contextmenu="onContextMenu"
      >
        <img class="ff-ball-img" :src="BALL_IMG" alt="" draggable="false" />
      </button>

      <!-- v-show, not v-else: remounting the videos on expand shows blank frames until they decode. -->
      <div
        v-show="!collapsed"
        class="ff-pet"
        :class="{ 'beat-pulse': beatPulse, 'in-rhythm': !!rhythm, hit: hitShake }"
        :style="{ transform: `scale(${squish})`, cursor: petCursor }"
                @pointerdown="onPointerDown"
        @pointermove="onPointerMove"
        @pointerup="onPointerUp"
        @pointercancel="resetPointer"
        @click.stop
        @pointerenter="onHoverEnter"
        @pointerleave="onHoverLeave"
        @contextmenu="onContextMenu"
      >
        <div class="ff-beat-ring" :class="{ on: beatPulse }" aria-hidden="true" />
        <span
          v-for="m in hitMarks"
          :key="m.id"
          class="ff-hit"
          :class="m.kind"
          :style="{ left: `${m.x}px`, top: `${m.y}px` }"
          aria-hidden="true"
        >{{ m.text }}</span>
        <div v-if="rhythm" class="ff-fall" :class="rhythm.mode" aria-hidden="true">
          <div class="ff-fall-hint">{{ rhythmHint }}</div>
          <div class="ff-fall-lanes">
            <div
              v-for="dir in ARROW_DIRS"
              :key="dir"
              class="ff-fall-lane"
              :class="laneFlashKind(dir)"
            >
              <div
                v-for="n in fallNotesFor(dir)"
                :key="n.id"
                class="ff-fall-note"
                :class="n.judged"
                :style="{ top: `${Math.min(100, noteProgress(n, fallNow) * 100)}%` }"
              >
                {{ ARROW_GLYPH[n.dir] }}
              </div>
              <div class="ff-fall-hit">{{ ARROW_GLYPH[dir] }}</div>
            </div>
          </div>
        </div>
        <video
          ref="slotA"
          class="ff-video"
          :class="{ flip: facing < 0, front: frontIsA, blend: blending }"
          :style="{ opacity: opA }"
          :src="srcA"
          :loop="loopA"
          muted
          playsinline
          preload="auto"
          @ended="onEnded('a')"
        />
        <video
          ref="slotB"
          class="ff-video"
          :class="{ flip: facing < 0, front: !frontIsA, blend: blending }"
          :style="{ opacity: opB }"
          :src="srcB"
          :loop="loopB"
          muted
          playsinline
          preload="auto"
          @ended="onEnded('b')"
        />
      </div>
</div>
    <!-- Non-blocking popover: no full-screen capture layer; page stays interactive.
         Clicks outside dismiss via document listener; menu only receives its own hits. -->
    <div
      v-if="menuOpen"
      ref="menuEl"
      class="ff-menu"
      role="menu"
      :style="{ left: `${menuPos.x}px`, top: `${menuPos.y}px` }"
      @click.stop
      @contextmenu.prevent
      @pointerdown.stop
    >
      <div class="ff-status" :class="`is-${careState}`">
        <div class="ff-status-head">
          <span class="ff-status-state">{{ CARE_STATE_LABEL[careState] }}</span>
          <span class="ff-status-level" :title="careLevel.max ? '熟悉度已满' : `熟悉度：离下一级还差 ${Math.round((1 - careLevel.progress) * 100)}%`">
            Lv{{ careLevel.level }} {{ careLevel.name }}
          </span>
        </div>
        <div class="ff-status-aff"><i :style="{ width: `${Math.round(careLevel.progress * 100)}%` }" /></div>
      </div>
      <button type="button" @click="menuAction('chat')">聊聊</button>
      <button type="button" @click="menuAction('pin')">{{ pinned ? '取消固定' : '固定' }}</button>
      <button type="button" @click="menuAction('look')">看看页面</button>
      <button type="button" @click="menuAction('fill')">帮填表</button>
      <template v-if="collapsed">
        <button v-if="discoUnlocked" type="button" @click="menuAction('disco')">蹦迪</button>
        <button type="button" @click="menuAction('ball')">展开</button>
      </template>
      <template v-else>
        <button type="button" @click="menuAction('feed')">投喂</button>
        <button type="button" @click="menuAction('play')">玩耍</button>
        <button type="button" @click="menuAction('dance')">跳舞</button>
        <button v-if="discoUnlocked" type="button" @click="menuAction('disco')">蹦迪</button>
        <button type="button" @click="menuAction('ball')">收成球</button>
      </template>
    </div>
  </div>
  <Teleport to="body">
    <div v-if="(discoActive || discoPending) && !discoStageOpen" class="ff-disco-controls" role="status">
      <span>{{ discoMessage || (discoPending ? '正在准备全曲…' : '大肥鱼蹦迪中 · Esc 停止') }}</span>
      <button v-if="discoPending" type="button" @click="playDisco">点击开蹦</button>
      <button type="button" @click="openDiscoStage">进入节奏舞台</button>
      <button type="button" @click="stopDisco">停止蹦迪</button>
    </div>
  </Teleport>
  <FatfishDiscoStage v-if="discoStageOpen"
    :active="discoActive" :pending="discoPending" :ended="discoFinished"
    :clock="discoClock" :duration="discoDuration" :session="discoSession"
    :message="discoMessage" :read-time="discoReadTime"
    @play="playDisco" @replay="replayDisco" @close="closeDiscoStage" @stop="stopDisco" />
</template>

<style scoped>
/* The pet is a self-contained character skin with its own fixed palette; it does not follow the dark theme. */
@property --ff-fade-top {
  syntax: '<length>';
  inherits: false;
  initial-value: 0px;
}
@property --ff-fade-bottom {
  syntax: '<length>';
  inherits: false;
  initial-value: 0px;
}
.ff-root {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 4800;
  font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}
.ff-stage {
  position: absolute;
  pointer-events: none;
  overflow: visible;
}
.ff-pet {
  position: relative;
  width: 100%;
  height: 100%;
  pointer-events: auto;
  /* cursor set inline: hover = character pointer; press/drag = grabbing */
  touch-action: none;
  user-select: none;
  transform-origin: center bottom;
  transition: transform 0.1s ease-out;
  filter: drop-shadow(0 14px 24px rgba(15, 23, 42, 0.24));
}
/* `translate` is separate from the inline squish `transform`, so the two don't fight. */
.ff-pet.hit {
  animation: ff-hit-shake 0.26s ease-out;
}
@keyframes ff-hit-shake {
  0%,
  100% {
    translate: 0 0;
  }
  25% {
    translate: -5px 2px;
  }
  50% {
    translate: 4px 0;
  }
  75% {
    translate: -2px 1px;
  }
}
.ff-hit {
  position: absolute;
  z-index: 3;
  pointer-events: none;
  font-weight: 800;
  font-size: 15px;
  white-space: nowrap;
  color: #38bdf8;
  text-shadow:
    0 1px 0 #fff, /* theme-ok */
    0 0 4px rgba(255, 255, 255, 0.9);
  transform: translate(-50%, -100%);
  animation: ff-hit-rise 0.7s ease-out forwards;
}
.ff-hit.flurry {
  font-size: 17px;
  color: #f97316;
}
.ff-hit.fever {
  font-size: 17px;
  color: #ffd400; /* theme-ok: comic gold, distinct from flurry orange and punch red */
  text-shadow:
    0 1px 0 #6b3a00, /* theme-ok */
    0 0 6px #ffb703; /* theme-ok */
}
/* Little flame in front of 戳×N once past 100: a teardrop with its point up, flickering. */
.ff-hit.fever::before {
  content: '';
  display: inline-block;
  width: 10px;
  height: 10px;
  margin: 0 5px 0 2px;
  vertical-align: 1px;
  border-radius: 50% 0 50% 50%;
  background: radial-gradient(circle at 60% 40%, #fff7c2 0 15%, #ffd400 38%, #ff7a00 70%, #e2330d 100%); /* theme-ok */
  box-shadow: 0 0 6px #ff9a00; /* theme-ok */
  transform: rotate(-45deg);
  transform-origin: 50% 50%;
  animation: ff-flame 0.15s ease-in-out infinite alternate;
}
@keyframes ff-flame {
  to {
    transform: rotate(-38deg) scale(1.15, 0.92);
  }
}
.ff-hit.punch {
  font-size: 22px;
  color: #ef4444;
  animation-name: ff-hit-bang;
}
@keyframes ff-hit-rise {
  from {
    opacity: 1;
    transform: translate(-50%, -100%) scale(0.8);
  }
  to {
    opacity: 0;
    transform: translate(-50%, -190%) scale(1);
  }
}
@keyframes ff-hit-bang {
  0% {
    opacity: 1;
    transform: translate(-50%, -100%) scale(1.5) rotate(-8deg);
  }
  30% {
    transform: translate(-50%, -110%) scale(1) rotate(4deg);
  }
  100% {
    opacity: 0;
    transform: translate(-50%, -150%) scale(0.9) rotate(0);
  }
}
.ff-video {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center bottom;
  transform: scale(0.80);
  transform-origin: center center;
  background: transparent;
  pointer-events: none;
  image-rendering: -webkit-optimize-contrast;
  transition: none;
  will-change: opacity;
}
.ff-video.front {
  z-index: 1;
}
/* Every cut: the incoming clip fades in on top while the outgoing one stays opaque a moment longer,
   so the two alpha layers never both sit at half opacity (that reads as her turning see-through). */
.ff-video.blend.front {
  transition: opacity 0.14s ease-out;
}
.ff-video.blend:not(.front) {
  transition: opacity 0.12s ease-in 0.07s;
}
.ff-video.flip {
  transform: scale(-0.80, 0.80);
  transform-origin: center center;
}
button.ff-ball,
.ff-ball {
  --ff-plate: linear-gradient(180deg, #ffffff 0%, #f6f6f8 100%); /* theme-ok */
  appearance: none;
  -webkit-appearance: none;
  pointer-events: auto;
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  margin: 0;
  padding: 0;
  border: 0 !important;
  outline: none !important;
  border-radius: 999px;
  background: transparent !important;
  background-color: transparent !important;
  background-image: none !important;
  box-shadow:
    0 0 0 1.5px #ffffff, /* theme-ok */
    0 1px 2px rgba(15, 23, 42, 0.10),
    0 3px 8px rgba(15, 23, 42, 0.10);
  line-height: 0;
  cursor: pointer;
  overflow: visible;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.18s ease, padding 0.18s ease, box-shadow 0.18s ease;
}
.ff-ball.docked {
  padding: 2px;
  overflow: hidden;
  background: var(--ff-plate) !important;
  background-color: #ffffff !important; /* theme-ok */
  background-image: var(--ff-plate) !important;
  box-shadow:
    0 0 0 1px rgba(15, 23, 42, 0.04),
    0 1px 2px rgba(15, 23, 42, 0.05),
    0 3px 8px rgba(15, 23, 42, 0.08);
}
.ff-ball.docked.dock-left { justify-content: flex-end; }
.ff-ball.docked.dock-right { justify-content: flex-start; }
.ff-ball.docked.dock-top {
  flex-direction: column;
  justify-content: flex-end;
}
.ff-ball.docked.dock-bottom {
  flex-direction: column;
  justify-content: flex-start;
}
button.ff-ball:hover,
button.ff-ball:focus,
button.ff-ball:focus-visible,
button.ff-ball:active {
  transform: none;
  outline: none !important;
  background: transparent !important;
  background-image: none !important;
}
.ff-ball.docked:hover,
.ff-ball.docked:focus,
.ff-ball.docked:focus-visible,
.ff-ball.docked:active {
  background: var(--ff-plate) !important;
  background-image: var(--ff-plate) !important;
}
.ff-ball.dragging {
  cursor: grabbing;
  justify-content: center;
  flex-direction: row;
}
.ff-ball-img {
  display: block;
  width: 100%;
  height: 100%;
  flex: none;
  border-radius: 50%;
  object-fit: cover;
  pointer-events: none;
  user-select: none;
}
.ff-ball.docked .ff-ball-img {
  width: 30px;
  height: 30px;
}

.ff-bubbles {
  position: absolute;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: stretch;
  gap: 5px;
  pointer-events: none;
  z-index: 2;
}
.ff-bubble.align-left {
  align-self: flex-start;
  max-width: calc(100% - 20px);
}
.ff-bubble.align-right {
  align-self: flex-end;
  max-width: calc(100% - 20px);
}
.ff-bubbles.chat-open {
  pointer-events: auto;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  justify-content: flex-start;
  background: transparent;
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.ff-bubbles.chat-open::-webkit-scrollbar {
  display: none;
  width: 0;
  height: 0;
}
.ff-bubble.wait {
  pointer-events: auto;
  cursor: pointer;
  border-style: dashed;
  opacity: 0.95;
}
.ff-bubble.wait:hover {
  filter: brightness(1.05);
}
.ff-pet.beat-pulse {
  /* Never set transform here — inline squish scale wins and kills it. */
  filter: drop-shadow(0 14px 24px rgba(15, 23, 42, 0.24))
    drop-shadow(0 0 28px rgba(56, 189, 248, 0.95))
    drop-shadow(0 0 48px rgba(125, 211, 252, 0.75))
    brightness(1.12);
}
.ff-pet.in-rhythm {
  cursor: pointer;
}
.ff-fall {
  position: absolute;
  left: 50%;
  bottom: 6%;
  width: 196px;
  height: 220px;
  transform: translateX(-50%);
  z-index: 6;
  pointer-events: none;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.ff-fall-hint {
  align-self: center;
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 11px;
  color: #0f172a;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 4px 10px rgba(15, 23, 42, 0.12);
}
.ff-fall-lanes {
  flex: 1;
  display: flex;
  gap: 6px;
  min-height: 0;
  padding: 2px 4px 6px;
}
.ff-fall-lane {
  flex: 1;
  position: relative;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.22);
  overflow: hidden;
}
.ff-fall-lane.hit {
  background: rgba(34, 197, 94, 0.4);
}
.ff-fall-lane.miss {
  background: rgba(239, 68, 68, 0.36);
}
.ff-fall-note {
  position: absolute;
  left: 50%;
  width: 28px;
  height: 28px;
  margin-left: -14px;
  margin-top: -14px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
  background: #fff; /* theme-ok */
  box-shadow: 0 4px 12px rgba(14, 165, 233, 0.35);
}
.ff-fall.dance .ff-fall-note {
  background: #e0f2fe;
}
.ff-fall.play .ff-fall-note {
  background: #fef9c3;
}
.ff-fall-note.hit {
  background: #86efac;
}
.ff-fall-note.miss {
  background: #fecaca;
  opacity: 0.55;
}
.ff-fall-hit {
  position: absolute;
  left: 50%;
  bottom: 10px;
  width: 30px;
  height: 30px;
  margin-left: -15px;
  border-radius: 9px;
  border: 2px solid rgba(255, 255, 255, 0.95);
  box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  color: #fff;
  background: rgba(14, 165, 233, 0.38);
}
.ff-beat-ring {
  position: absolute;
  left: 50%;
  top: 48%;
  width: 78%;
  height: 78%;
  translate: -50% -50%;
  border-radius: 50%;
  border: 3px solid rgba(125, 211, 252, 0.15);
  box-shadow: 0 0 0 0 rgba(56, 189, 248, 0);
  pointer-events: none;
  z-index: 3;
  opacity: 0.25;
  transform: scale(0.82);
  transition: opacity 0.12s ease, transform 0.12s ease, box-shadow 0.12s ease, border-color 0.12s ease;
}
.ff-beat-ring.on {
  opacity: 1;
  transform: scale(1.12);
  border-color: rgba(255, 255, 255, 0.95);
  box-shadow:
    0 0 0 6px rgba(56, 189, 248, 0.35),
    0 0 28px 8px rgba(125, 211, 252, 0.65),
    0 0 48px 14px rgba(14, 165, 233, 0.4);
}

.ff-pill {
  pointer-events: auto;
  position: absolute;
  z-index: 3;
  display: flex;
  gap: 6px;
  align-items: center;
  padding: 4px 6px 4px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.95);
  border: 1.5px solid rgba(125, 211, 252, 0.7);
  box-shadow: 0 6px 14px rgba(14, 165, 233, 0.14);
}
.ff-pill input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  font-size: 12.5px;
  background: transparent;
  color: #0f172a;
}
.ff-pill input::placeholder {
  color: #94a3b8;
}
.ff-pill-send {
  border: none;
  border-radius: 999px;
  padding: 5px 11px;
  background: linear-gradient(135deg, #7dd3fc, #38bdf8);
  color: #fff;
  font-size: 12px;
  cursor: pointer;
}
.ff-pill-send:disabled {
  opacity: 0.55;
  cursor: default;
}
.ff-bubble {
  max-width: 210px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.95);
  color: #1e293b;
  font-size: 12.5px;
  line-height: 1.45;
  box-shadow: 0 6px 16px rgba(14, 165, 233, 0.12);
  border: 1px solid rgba(186, 230, 253, 0.8);
  animation: ff-pop 0.14s ease-out;
  word-break: break-word;
}
.ff-bubble.tail-left {
  border-radius: 16px 16px 4px 16px;
}
.ff-bubble.tail-right {
  border-radius: 16px 16px 16px 4px;
}
.ff-bubble.user {
  background: #e0f2fe;
  border-color: rgba(125, 211, 252, 0.7);
}
.ff-bubble.sys {
  background: #f8fafc; /* theme-ok */
  color: #64748b;
}
.ff-bubbles.has-card {
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-width: none;
}
.ff-bubbles {
  --ff-fade-top: 0px;
  --ff-fade-bottom: 0px;
  transition: --ff-fade-top 0.18s ease, --ff-fade-bottom 0.18s ease;
}
.ff-bubbles.fade-top {
  --ff-fade-top: 36px;
}
.ff-bubbles.fade-bottom {
  --ff-fade-bottom: 22px;
}
.ff-bubbles.chat-open,
.ff-bubbles.has-card {
  -webkit-mask-image: linear-gradient(
    to bottom,
    transparent 0,
    #000 var(--ff-fade-top),
    #000 calc(100% - var(--ff-fade-bottom)),
    transparent 100%
  );
  mask-image: linear-gradient(
    to bottom,
    transparent 0,
    #000 var(--ff-fade-top),
    #000 calc(100% - var(--ff-fade-bottom)),
    transparent 100%
  );
}
.ff-bubble.card {
  pointer-events: auto;
  max-width: 100%;
  width: 100%;
  box-sizing: border-box;
  padding: 8px 10px 9px;
  border-color: rgba(56, 189, 248, 0.55);
}
.ff-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  min-height: 16px;
}
.ff-card-title {
  font-weight: 600;
  color: #0369a1;
  font-size: 12px;
}
.ff-card-x {
  border: none;
  background: transparent;
  color: #94a3b8;
  font-size: 15px;
  line-height: 1;
  cursor: pointer;
  padding: 0 2px;
}
.ff-card-x:hover {
  color: #475569;
}
.ff-card-body {
  white-space: pre-wrap;
  margin-top: 2px;
}
.ff-card-note {
  white-space: pre-line;
  margin-top: 6px;
  font-size: 11.5px;
  color: #0f766e;
}
.ff-card-actions {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
  margin-top: 8px;
}
.ff-card-actions button {
  border: 1px solid #bae6fd;
  background: #fff; /* theme-ok */
  color: #0369a1;
  border-radius: 999px;
  padding: 3px 12px;
  font-size: 12px;
  cursor: pointer;
}
.ff-card-actions button.primary {
  background: #0ea5e9;
  border-color: #0ea5e9;
  color: #fff;
}
.ff-card-actions button:hover {
  filter: brightness(1.05);
}
.ff-menu {
  /* Isolated hit-target only — no modal/backdrop that steals page input. */
  pointer-events: auto;
  position: fixed;
  z-index: 4801;
  display: flex;
  flex-direction: column;
  min-width: 140px;
  padding: 6px;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.92);
  backdrop-filter: blur(10px);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.28);
  animation: ff-menu-in 0.14s ease-out;
  will-change: transform, opacity;
}
@keyframes ff-menu-in {
  from {
    opacity: 0;
    transform: translateY(4px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
.ff-menu button {
  border: none;
  border-radius: 8px;
  padding: 8px 10px;
  text-align: left;
  font-size: 12px;
  color: #f8fafc; /* theme-ok */
  background: transparent;
  cursor: pointer;
}
.ff-menu button:hover {
  background: rgba(125, 211, 252, 0.2);
}
.ff-status {
  margin: 0 0 4px;
  padding: 6px 8px 8px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.2);
  font-size: 11px;
  color: #cbd5e1;
}
.ff-status-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 4px;
}
.ff-status-state {
  font-weight: 600;
  color: #f8fafc; /* theme-ok */
}
.ff-status.is-happy .ff-status-state {
  color: #fcd34d;
}
.ff-status.is-hungry .ff-status-state,
.ff-status.is-tired .ff-status-state,
.ff-status.is-down .ff-status-state {
  color: #fda4af;
}
.ff-status-level {
  color: #7dd3fc;
  white-space: nowrap;
}
.ff-status-aff {
  height: 2px;
  border-radius: 1px;
  background: rgba(125, 211, 252, 0.15);
  overflow: hidden;
}
.ff-status-aff i {
  display: block;
  height: 100%;
  background: #7dd3fc;
}


@keyframes ff-pop {
  from {
    transform: translateY(6px) scale(0.96);
    opacity: 0;
  }
  to {
    transform: none;
    opacity: 1;
  }
}
</style>
