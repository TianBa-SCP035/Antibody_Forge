export type PokeHitKind = 'poke' | 'flurry' | 'punch' | 'fever';

/** 每次 pointerup 后显示浮动标记；达到 100 次仍显示「戳×N」，但改用金色样式且不显示等级。 */
export function pokeHitPresentation(tapCount: number, punching: boolean): { text: string; kind: PokeHitKind } {
  if (punching) return { text: '咚', kind: 'punch' };
  if (tapCount >= 100) return { text: `戳×${tapCount}`, kind: 'fever' };
  if (tapCount >= 3) return { text: `戳×${tapCount}`, kind: 'flurry' };
  return { text: '戳', kind: 'poke' };
}