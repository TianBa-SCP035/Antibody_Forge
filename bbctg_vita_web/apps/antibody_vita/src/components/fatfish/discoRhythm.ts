/** 节奏回合按歌曲小节网格排列：依次输入方向键，光标到达节拍点时按空格；每个乐句的最后一回合需按住空格直到结束小节。
 * 速度、相位和乐句终点根据内置音轨测得，所有判定必须读取同一个媒体 currentTime。 */
export const RHYTHM_BPM = 129.7;
export const BEAT_SECONDS = 60 / RHYTHM_BPM;
export const BAR_SECONDS = BEAT_SECONDS * 4;
export const FULL_TRACK_SECONDS = 187.402;
/** 第一条小节线：首拍出现在 0.176 秒，小节线落在其第四拍。 */
export const FIRST_BAR_SECONDS = 0.176 + 3 * BEAT_SECONDS;
/** 页面舞动网格从第一条小节线前一小节开始，使每四拍的第 0 拍为强拍。 */
export const BEAT_OFFSET_SECONDS = FIRST_BAR_SECONDS - BAR_SECONDS;
/** 从 FIRST_BAR_SECONDS 起计数的乐句收尾小节。 */
const PHRASE_ENDS = [8, 16, 24, 32, 40, 43, 51, 59, 67, 75, 83, 99];
/** 按小节划分的歌曲段落，用于难度和舞台标签。 */
const SECTION_STARTS = [1, 25, 44, 68];
export const SECTION_NAMES = ['前奏', '主歌', '推进', '高潮'] as const;
/** 各段落每组的方向键数量；普通组跨两小节，乐句长按前的一组跨一小节。 */
const ROW_ARROWS = [3, 4, 5, 6];
const SHORT_ROW_ARROWS = [2, 3, 3, 4];

export const ARROWS = ['ArrowLeft', 'ArrowUp', 'ArrowDown', 'ArrowRight'] as const;
export type Arrow = typeof ARROWS[number];
export type RhythmKey = Arrow | 'Space';
export type Verdict = 'Perfect' | 'Great' | 'Good' | 'Bad' | 'Miss';
/** 相对节拍点的秒数窗口；超过 Bad 窗口即为 Miss。 */
export const WINDOWS = { Perfect: 0.05, Great: 0.1, Good: 0.15, Bad: 0.22 } as const;
/** 在结束前此时间范围内松开仍算完成长按。 */
export const HOLD_RELEASE_GRACE = WINDOWS.Good;
const POINTS: Record<Verdict, number> = { Perfect: 1000, Great: 700, Good: 400, Bad: 150, Miss: 0 };
const HOLD_BONUS = 400;

export interface RhythmRound {
  id: number;
  /** 本组出现并允许输入的时间点，即一条小节线。 */
  start: number;
  /** 按空格的节拍点，即下一条小节线。 */
  hit: number;
  /** 长按回合中，空格必须保持到此小节线。 */
  hold?: number;
  arrows: Arrow[];
  section: number;
}
export type HoldPhase = 'start' | 'done' | 'broken';
export interface RoundResult { verdict: Verdict; delta: number; at: number; hold?: HoldPhase }
export interface RhythmGame {
  rounds: RhythmRound[];
  results: Map<number, RoundResult | 'Skipped'>;
  /** 当前回合已正确输入的方向键数量。 */
  typed: number;
  score: number; combo: number; maxCombo: number;
  counts: Record<Verdict, number>;
  last: (RoundResult & { round: number; combo: number }) | null;
  /** 最近一次按键，用于按下和错误闪烁效果。 */
  press: { key: RhythmKey; ok: boolean; at: number } | null;
  /** 长按回合的空格状态，在松开或长按结束时判定。 */
  holding: { round: number; verdict: Verdict; delta: number; at: number } | null;
}

export const barTime = (bar: number) => FIRST_BAR_SECONDS + bar * BAR_SECONDS;
export function sectionAt(time: number) {
  const bar = Math.floor((time - FIRST_BAR_SECONDS) / BAR_SECONDS);
  let s = 0;
  while (s + 1 < SECTION_STARTS.length && bar >= SECTION_STARTS[s + 1]!) s++;
  return s;
}

const MIRROR: Record<Arrow, Arrow> = { ArrowLeft: 'ArrowRight', ArrowRight: 'ArrowLeft', ArrowUp: 'ArrowUp', ArrowDown: 'ArrowDown' };
/** 键组随音乐重复：同一段落各乐句的相同位置使用同一组，奇偶乐句左右镜像。 */
function rowFor(section: number, slot: number, length: number, mirror: boolean): Arrow[] {
  let seed = ((section + 1) * 7919 + (slot + 1) * 104729) >>> 0 || 1;
  const next = () => { seed ^= seed << 13; seed >>>= 0; seed ^= seed >>> 17; seed ^= seed << 5; seed >>>= 0; return seed; };
  const row: Arrow[] = [];
  while (row.length < length) {
    const pick = ARROWS[next() % 4]!;
    // 禁止连续三个相同方向，避免看起来像误输入。
    if (row.length >= 2 && row.at(-1) === pick && row.at(-2) === pick) continue;
    row.push(pick);
  }
  return mirror ? row.map((a) => MIRROR[a]) : row;
}

/** 每个乐句按两小节分组；最后一组在收尾小节到点，并长按到下一乐句。 */
export function buildRhythmChart(duration = FULL_TRACK_SECONDS): RhythmRound[] {
  const rounds: RhythmRound[] = [];
  let first = 1;
  PHRASE_ENDS.forEach((end, phrase) => {
    let slot = 0;
    for (let bar = first; bar < end; bar += 2, slot++) {
      const last = bar + 2 >= end;
      const section = sectionAt(barTime(bar) + 0.01);
      const hit = last ? barTime(end) : barTime(bar + 2);
      const hold = last ? barTime(end + 1) : undefined;
      if ((hold ?? hit) + WINDOWS.Bad > duration) return;
      const length = (last && end - bar === 1 ? SHORT_ROW_ARROWS : ROW_ARROWS)[section]!;
      rounds.push({ id: rounds.length, start: barTime(bar), hit, hold, arrows: rowFor(section, slot, length, phrase % 2 === 1), section });
    }
    first = end + 1;
  });
  return rounds;
}

export function createRhythmGame(rounds = buildRhythmChart(), joinAt = 0): RhythmGame {
  const results = new Map<number, RoundResult | 'Skipped'>();
  // 中途加入时跳过已经显示的键组，避免因来不及阅读和输入而误判。
  if (joinAt > 0) for (const r of rounds) if (r.start < joinAt + 0.5) results.set(r.id, 'Skipped');
  return {
    rounds, results, typed: 0, score: 0, combo: 0, maxCombo: 0,
    counts: { Perfect: 0, Great: 0, Good: 0, Bad: 0, Miss: 0 }, last: null, press: null, holding: null,
  };
}

/** 歌曲中途返回舞台时，收起期间经过的键组记为跳过而非 Miss。 */
export function resumeRhythmGame(game: RhythmGame, now: number) {
  releaseSpace(game, now);
  game.typed = 0;
  for (const r of game.rounds) if (!game.results.has(r.id) && r.start < now + 0.5) game.results.set(r.id, 'Skipped');
  return game;
}

/** 返回长按完成数和参与数，供结算页显示。 */
export function holdTally(game: RhythmGame) {
  let done = 0, played = 0;
  for (const r of game.rounds) {
    const result = game.results.get(r.id);
    if (!r.hold || !result || result === 'Skipped') continue;
    played++;
    if (result.hold === 'done') done++;
  }
  return { done, played };
}

/** 返回已开始、未判定且判定窗口尚未关闭的当前回合。 */
export function openRound(game: RhythmGame, now: number) {
  return game.rounds.find((r) => !game.results.has(r.id) && game.holding?.round !== r.id
    && r.start <= now && now <= r.hit + WINDOWS.Bad);
}

/** 返回下一待玩回合，供准备预览。 */
export function upcomingRound(game: RhythmGame, now: number, after = -1) {
  return game.rounds.find((r) => r.id > after && !game.results.has(r.id) && game.holding?.round !== r.id
    && now <= r.hit + WINDOWS.Bad);
}

function settle(game: RhythmGame, round: RhythmRound, verdict: Verdict, now: number, delta = 0, hold?: HoldPhase) {
  const result: RoundResult = { verdict, delta, at: now, hold };
  game.results.set(round.id, result);
  game.counts[verdict]++;
  game.typed = 0;
  if (verdict === 'Perfect' || verdict === 'Great') {
    game.combo++;
    game.maxCombo = Math.max(game.maxCombo, game.combo);
  } else {
    game.combo = 0;
  }
  const lengthBonus = 1 + (round.arrows.length - 3) * 0.15;
  game.score += Math.round((POINTS[verdict] + (hold === 'done' ? HOLD_BONUS : 0)) * lengthBonus)
    + (verdict === 'Miss' ? 0 : Math.min(50, game.combo) * 20);
  game.last = { ...result, round: round.id, combo: game.combo };
  return game.last;
}

/** 判定窗口关闭前未按空格的回合记为 Miss；保持到终点的长按记为完成。 */
export function advanceRhythm(game: RhythmGame, now: number) {
  const h = game.holding;
  if (h) {
    const round = game.rounds[h.round]!;
    if (now >= round.hold!) { game.holding = null; settle(game, round, h.verdict, round.hold!, h.delta, 'done'); }
  }
  for (const r of game.rounds) {
    if (r.start > now) break;
    if (!game.results.has(r.id) && game.holding?.round !== r.id && now > r.hit + WINDOWS.Bad) settle(game, r, 'Miss', r.hit + WINDOWS.Bad);
  }
}

export function verdictFor(delta: number): Verdict {
  const d = Math.abs(delta);
  return d <= WINDOWS.Perfect ? 'Perfect' : d <= WINDOWS.Great ? 'Great' : d <= WINDOWS.Good ? 'Good' : d <= WINDOWS.Bad ? 'Bad' : 'Miss';
}

/** 方向正确时推进，错误时按原游戏规则清空并要求重输。 */
export function typeArrow(game: RhythmGame, key: Arrow, now: number) {
  advanceRhythm(game, now);
  const round = openRound(game, now);
  // 两组之间或本组完成后输入方向键只忽略，不记错。
  if (!round || game.typed >= round.arrows.length) {
    game.press = { key, ok: true, at: now };
    return false;
  }
  const ok = round.arrows[game.typed] === key;
  game.typed = ok ? game.typed + 1 : 0;
  game.press = { key, ok, at: now };
  return ok;
}

/** 空格用于判定当前回合；方向键未输完记为 Miss，长按回合命中后进入保持状态。 */
export function hitSpace(game: RhythmGame, now: number) {
  advanceRhythm(game, now);
  game.press = { key: 'Space', ok: true, at: now };
  if (game.holding) return null;
  const round = openRound(game, now);
  if (!round) return null;
  const delta = now - round.hit;
  if (delta < -WINDOWS.Bad * 2) return null; // 仍在输入阶段时，误按空格只忽略而不处罚。
  const verdict = game.typed < round.arrows.length ? 'Miss' : verdictFor(delta);
  game.press.ok = verdict !== 'Miss';
  if (round.hold && verdict !== 'Miss') {
    game.holding = { round: round.id, verdict, delta, at: now };
    game.last = { verdict, delta, at: now, hold: 'start', round: round.id, combo: game.combo };
    return game.last;
  }
  return settle(game, round, verdict, now, delta);
}

/** 松开空格时，提前结束长按会把本回合降为 Bad。 */
export function releaseSpace(game: RhythmGame, now: number) {
  const h = game.holding;
  if (!h) return null;
  const round = game.rounds[h.round]!;
  game.holding = null;
  return now < round.hold! - HOLD_RELEASE_GRACE
    ? settle(game, round, 'Bad', now, h.delta, 'broken')
    : settle(game, round, h.verdict, now, h.delta, 'done');
}

export function rhythmAccuracy(game: RhythmGame) {
  const c = game.counts;
  const played = c.Perfect + c.Great + c.Good + c.Bad + c.Miss;
  return played ? Math.round(100 * (c.Perfect + 0.8 * c.Great + 0.5 * c.Good + 0.2 * c.Bad) / played) : 100;
}

export function normalizeRhythmKey(code: string, key = ''): RhythmKey | null {
  if (code === 'Space' || key === ' ' || key === 'Spacebar') return 'Space';
  const pick = (v: string) => (ARROWS as readonly string[]).includes(v) ? v as Arrow : null;
  return pick(key) ?? pick(code);
}

/** 仅已挂载且激活的舞台接管按键，空闲页面和编辑器不得丢失键盘事件。 */
export function dispatchRhythmKey(
  event: Pick<KeyboardEvent, 'type' | 'code' | 'key' | 'repeat' | 'preventDefault' | 'stopImmediatePropagation'>,
  active: boolean, editing: boolean, hit: (key: RhythmKey) => void, release: () => void,
) {
  if (!active || editing) return false;
  const key = normalizeRhythmKey(event.code, event.key);
  if (!key) return false;
  event.preventDefault();
  event.stopImmediatePropagation();
  if (event.type === 'keyup') { if (key === 'Space') release(); }
  else if (!event.repeat) hit(key);
  return true;
}

export function sampleDiscoBeat(time: number) {
  const elapsed = Math.max(0, time - BEAT_OFFSET_SECONDS);
  const index = Math.floor(elapsed / BEAT_SECONDS);
  const phase = elapsed / BEAT_SECONDS - index;
  const heavy = index % 4 === 0;
  return { index, phase, heavy, pulse: Math.pow(Math.max(0, 1 - phase), 3) * (heavy ? 1 : .65) };
}

/** 页面各区域使用不同舞动幅度：页头跳动、侧栏摇摆、内容呼吸，宠物跳得最高。 */
export type DanceKind = 'pet' | 'header' | 'aside' | 'main';
const DANCE: Record<DanceKind, { lift: number; squash: number; sway: number }> = {
  pet: { lift: 25, squash: .035, sway: 0 },
  header: { lift: 12, squash: .01, sway: 0 },
  aside: { lift: 5, squash: 0, sway: 1.6 },
  main: { lift: 7, squash: .004, sway: 0 },
};
/** 四拍关键帧；调用方暂停动画，并用音频时间写入 currentTime。 */
export function discoMotionFrames(kind: DanceKind = 'main', reduced = false): Keyframe[] {
  const { lift, squash, sway } = DANCE[kind];
  const amp = (beat: number) => (reduced ? 1.5 : lift) * (beat % 4 === 0 ? 1.35 : 1);
  const s = reduced ? 0 : squash;
  const frames: Keyframe[] = [];
  for (let beat = 0; beat < 4; beat++) {
    // 峰值与 sampleDiscoBeat() 同样落在拍点，随后衰减、稳定，并短暂引向下一拍。
    const side = beat % 2 === 0 ? -1 : 1;
    const points = [
      { p: 0, e: 1, a: amp(beat), side },
      { p: .18, e: .551368, a: amp(beat), side },
      { p: .4, e: .216, a: amp(beat), side },
      { p: .68, e: .032768, a: amp(beat), side },
      { p: .92, e: 0, a: amp(beat), side },
      { p: 1, e: 1, a: amp(beat + 1), side: -side },
    ];
    for (const { p, e, a, side: dir } of points) {
      frames.push({
        offset: (beat + p) / 4,
        translate: `0 ${-(reduced ? a * .2 : a) * e}px`,
        scale: e > .9 ? `${1 - s / 2} ${1 + s}` : p === .92 ? `${1 + s / 2} ${1 - s / 2}` : '1 1',
        rotate: `${reduced ? 0 : sway * dir * e}deg`,
      });
    }
  }
  return frames;
}

/** 角落灯光每拍闪烁，小节首拍最亮。 */
export function discoLightFrames(reduced = false): Keyframe[] {
  const frames: Keyframe[] = [];
  for (let beat = 0; beat < 4; beat++) {
    const peak = reduced ? .35 : beat === 0 ? 1 : .6;
    frames.push({ offset: beat / 4, opacity: peak });
    frames.push({ offset: (beat + .55) / 4, opacity: reduced ? .3 : .18 });
  }
  frames.push({ offset: 1, opacity: reduced ? .35 : 1 });
  return frames;
}
