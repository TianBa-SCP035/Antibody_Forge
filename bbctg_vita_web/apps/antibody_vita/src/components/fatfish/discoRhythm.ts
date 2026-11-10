/** Classic dance-game rounds laid on the song's own bar grid: type the arrow row, then hit Space as
 * the cursor reaches the beat point. The last round of each phrase ends with a held Space through
 * the phrase's closing bar.
 * Tempo, phase and phrase ends were measured from the bundled track (onset autocorrelation and per-bar
 * energy), so beat points land on the music. Every judgement reads the SAME media currentTime. */
export const RHYTHM_BPM = 129.7;
export const BEAT_SECONDS = 60 / RHYTHM_BPM;
export const BAR_SECONDS = BEAT_SECONDS * 4;
export const FULL_TRACK_SECONDS = 187.402;
/** First bar line: the first beat is heard at 0.176s and bar lines fall on its fourth beat. */
export const FIRST_BAR_SECONDS = 0.176 + 3 * BEAT_SECONDS;
/** Grid origin for the page dance: one bar before the first bar line, so beat 0 of every four is a downbeat. */
export const BEAT_OFFSET_SECONDS = FIRST_BAR_SECONDS - BAR_SECONDS;
/** Bars (counted from FIRST_BAR_SECONDS) that close a phrase: the energy drops and the song breathes. */
const PHRASE_ENDS = [8, 16, 24, 32, 40, 43, 51, 59, 67, 75, 83, 99];
/** Song sections by bar, used for difficulty and the stage label. */
const SECTION_STARTS = [1, 25, 44, 68];
export const SECTION_NAMES = ['前奏', '主歌', '推进', '高潮'] as const;
/** Arrows per row by section: two-bar rows, and the one-bar row before a phrase's held Space. */
const ROW_ARROWS = [3, 4, 5, 6];
const SHORT_ROW_ARROWS = [2, 3, 3, 4];

export const ARROWS = ['ArrowLeft', 'ArrowUp', 'ArrowDown', 'ArrowRight'] as const;
export type Arrow = typeof ARROWS[number];
export type RhythmKey = Arrow | 'Space';
export type Verdict = 'Perfect' | 'Great' | 'Good' | 'Bad' | 'Miss';
/** Seconds from the beat point; anything later than Bad is a Miss. */
export const WINDOWS = { Perfect: 0.05, Great: 0.1, Good: 0.15, Bad: 0.22 } as const;
/** A hold released this close to its end still counts as held. */
export const HOLD_RELEASE_GRACE = WINDOWS.Good;
const POINTS: Record<Verdict, number> = { Perfect: 1000, Great: 700, Good: 400, Bad: 150, Miss: 0 };
const HOLD_BONUS = 400;

export interface RhythmRound {
  id: number;
  /** Row appears and typing opens (a bar line). */
  start: number;
  /** Beat point for Space (the next bar line). */
  hit: number;
  /** For a held round: Space must stay down until this bar line. */
  hold?: number;
  arrows: Arrow[];
  section: number;
}
export type HoldPhase = 'start' | 'done' | 'broken';
export interface RoundResult { verdict: Verdict; delta: number; at: number; hold?: HoldPhase }
export interface RhythmGame {
  rounds: RhythmRound[];
  results: Map<number, RoundResult | 'Skipped'>;
  /** Correct arrows typed so far in the open round. */
  typed: number;
  score: number; combo: number; maxCombo: number;
  counts: Record<Verdict, number>;
  last: (RoundResult & { round: number; combo: number }) | null;
  /** Last key press, for the press / wrong flash. */
  press: { key: RhythmKey; ok: boolean; at: number } | null;
  /** Space held on a held round, judged on release or at the hold's end. */
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
/** Rows repeat with the music: the same slot of every phrase in a section gets the same row,
 * mirrored left/right on alternate phrases. */
function rowFor(section: number, slot: number, length: number, mirror: boolean): Arrow[] {
  let seed = ((section + 1) * 7919 + (slot + 1) * 104729) >>> 0 || 1;
  const next = () => { seed ^= seed << 13; seed >>>= 0; seed ^= seed >>> 17; seed ^= seed << 5; seed >>>= 0; return seed; };
  const row: Arrow[] = [];
  while (row.length < length) {
    const pick = ARROWS[next() % 4]!;
    // Never three of the same in a row; it reads as a typo.
    if (row.length >= 2 && row.at(-1) === pick && row.at(-2) === pick) continue;
    row.push(pick);
  }
  return mirror ? row.map((a) => MIRROR[a]) : row;
}

/** Each phrase is cut into two-bar rows; its last row ends on the closing bar, held to the next phrase. */
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
  // Joining mid-song: a row already showing cannot be read and typed fairly, so it is skipped.
  if (joinAt > 0) for (const r of rounds) if (r.start < joinAt + 0.5) results.set(r.id, 'Skipped');
  return {
    rounds, results, typed: 0, score: 0, combo: 0, maxCombo: 0,
    counts: { Perfect: 0, Great: 0, Good: 0, Bad: 0, Miss: 0 }, last: null, press: null, holding: null,
  };
}

/** Back on stage mid-song: rows that ran while the stage was folded away are skipped, not missed. */
export function resumeRhythmGame(game: RhythmGame, now: number) {
  releaseSpace(game, now);
  game.typed = 0;
  for (const r of game.rounds) if (!game.results.has(r.id) && r.start < now + 0.5) game.results.set(r.id, 'Skipped');
  return game;
}

/** Held rounds completed / held rounds played, for the results screen. */
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

/** The round whose row is on screen: started, not yet judged, and its window not yet closed. */
export function openRound(game: RhythmGame, now: number) {
  return game.rounds.find((r) => !game.results.has(r.id) && game.holding?.round !== r.id
    && r.start <= now && now <= r.hit + WINDOWS.Bad);
}

/** The next round still to be played, for the "get ready" preview. */
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

/** Rounds whose window closed without a Space become Miss; a hold kept to its end completes. */
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

/** An arrow either advances the row or, like the original game, clears it so it must be retyped. */
export function typeArrow(game: RhythmGame, key: Arrow, now: number) {
  advanceRhythm(game, now);
  const round = openRound(game, now);
  // Between rows or after the row is complete an arrow is simply ignored, never counted as wrong.
  if (!round || game.typed >= round.arrows.length) {
    game.press = { key, ok: true, at: now };
    return false;
  }
  const ok = round.arrows[game.typed] === key;
  game.typed = ok ? game.typed + 1 : 0;
  game.press = { key, ok, at: now };
  return ok;
}

/** Space judges the open round; an unfinished row is a Miss. On a held round a good press starts the hold. */
export function hitSpace(game: RhythmGame, now: number) {
  advanceRhythm(game, now);
  game.press = { key: 'Space', ok: true, at: now };
  if (game.holding) return null;
  const round = openRound(game, now);
  if (!round) return null;
  const delta = now - round.hit;
  if (delta < -WINDOWS.Bad * 2) return null; // Still typing: a stray Space is ignored, not punished.
  const verdict = game.typed < round.arrows.length ? 'Miss' : verdictFor(delta);
  game.press.ok = verdict !== 'Miss';
  if (round.hold && verdict !== 'Miss') {
    game.holding = { round: round.id, verdict, delta, at: now };
    game.last = { verdict, delta, at: now, hold: 'start', round: round.id, combo: game.combo };
    return game.last;
  }
  return settle(game, round, verdict, now, delta);
}

/** Space released: letting go before the hold ends drops the round to Bad. */
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

/** Only an active mounted stage calls this; idle pages/editors never lose their keys. */
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

/** Each page area dances its own way: the header hops, the side menu sways, the content breathes,
 * the pet jumps highest. */
export type DanceKind = 'pet' | 'header' | 'aside' | 'main';
const DANCE: Record<DanceKind, { lift: number; squash: number; sway: number }> = {
  pet: { lift: 25, squash: .035, sway: 0 },
  header: { lift: 12, squash: .01, sway: 0 },
  aside: { lift: 5, squash: 0, sway: 1.6 },
  main: { lift: 7, squash: .004, sway: 0 },
};
/** Four-beat keyframes; caller pauses the animation and writes currentTime from audio. */
export function discoMotionFrames(kind: DanceKind = 'main', reduced = false): Keyframe[] {
  const { lift, squash, sway } = DANCE[kind];
  const amp = (beat: number) => (reduced ? 1.5 : lift) * (beat % 4 === 0 ? 1.35 : 1);
  const s = reduced ? 0 : squash;
  const frames: Keyframe[] = [];
  for (let beat = 0; beat < 4; beat++) {
    // Peak on the beat, just like sampleDiscoBeat(); decay, settle, then a short lead into the next kick.
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

/** Corner lights: a flash on every beat, brightest on the bar's first beat. */
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
