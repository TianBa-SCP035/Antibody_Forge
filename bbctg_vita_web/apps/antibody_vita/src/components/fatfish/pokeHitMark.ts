export type PokeHitKind = 'poke' | 'flurry' | 'punch' | 'fever';

/** Visible floating stamp after each pointerup. 100+ keeps 戳×N but uses a distinct gold class; never shows Lv. */
export function pokeHitPresentation(tapCount: number, punching: boolean): { text: string; kind: PokeHitKind } {
  if (punching) return { text: '咚', kind: 'punch' };
  if (tapCount >= 100) return { text: `戳×${tapCount}`, kind: 'fever' };
  if (tapCount >= 3) return { text: `戳×${tapCount}`, kind: 'flurry' };
  return { text: '戳', kind: 'poke' };
}