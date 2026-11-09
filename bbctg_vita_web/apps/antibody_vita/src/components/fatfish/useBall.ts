/** Collapse / dock / magnet geometry helpers for FatFish ball+capsule. */

import { BALL, CAP_H, CAP_PAD, CAP_W, MAGNET_RANGE, SIZE } from './constants';

export type DockEdge = 'left' | 'right' | 'top' | 'bottom';

export function clamp(n: number, a: number, b: number) {
  return Math.max(a, Math.min(b, n));
}

export function viewSize() {
  return {
    vw: window.innerWidth || 1280,
    vh: window.innerHeight || 800,
  };
}

export function dockVertical(edge: DockEdge) {
  return edge === 'top' || edge === 'bottom';
}

export function petW(collapsed: boolean, docked: boolean, edge: DockEdge) {
  if (!collapsed) return SIZE;
  if (!docked) return BALL;
  return dockVertical(edge) ? CAP_H : CAP_W;
}

export function petH(collapsed: boolean, docked: boolean, edge: DockEdge) {
  if (!collapsed) return SIZE;
  if (!docked) return BALL;
  return dockVertical(edge) ? CAP_W : CAP_H;
}

export function avatarOriginInCapsule(edge: DockEdge) {
  const pad = CAP_PAD;
  switch (edge) {
    case 'left':
      return { x: CAP_W - pad - BALL, y: pad };
    case 'right':
      return { x: pad, y: pad };
    case 'top':
      return { x: pad, y: CAP_W - pad - BALL };
    default:
      return { x: pad, y: pad };
  }
}

export function nearMagnetEdge(pos: { x: number; y: number }) {
  const { vw, vh } = viewSize();
  const cx = pos.x + BALL / 2;
  const cy = pos.y + BALL / 2;
  return Math.min(cx, vw - cx, cy, vh - cy) < MAGNET_RANGE;
}

export function settleAsFreeBall(pos: { x: number; y: number }) {
  const { vw, vh } = viewSize();
  const inset = 8;
  pos.x = clamp(pos.x, inset, Math.max(inset, vw - BALL - inset));
  pos.y = clamp(pos.y, inset, Math.max(inset, vh - BALL - inset));
}

/** Compute capsule dock snap target; caller animates and sets dockEdge/docked. */
export function magnetSnapTarget(pos: { x: number; y: number }): {
  edge: DockEdge;
  targetX: number;
  targetY: number;
} {
  const { vw, vh } = viewSize();
  const cx = pos.x + BALL / 2;
  const cy = pos.y + BALL / 2;
  const distL = cx;
  const distR = vw - cx;
  const distT = cy;
  const distB = vh - cy;
  const inset = 8;
  const hang = CAP_W - CAP_H;
  let edge: DockEdge;
  let targetX = pos.x;
  let targetY = pos.y;
  if (Math.min(distT, distB) + 24 < Math.min(distL, distR)) {
    if (distT <= distB) {
      edge = 'top';
      targetY = -hang;
      targetX = clamp(pos.x, inset, Math.max(inset, vw - CAP_H - inset));
    } else {
      edge = 'bottom';
      targetY = vh - CAP_H;
      targetX = clamp(pos.x, inset, Math.max(inset, vw - CAP_H - inset));
    }
  } else if (distL <= distR) {
    edge = 'left';
    targetX = -hang;
    targetY = clamp(pos.y, inset, Math.max(inset, vh - CAP_H - inset));
  } else {
    edge = 'right';
    targetX = vw - CAP_H;
    targetY = clamp(pos.y, inset, Math.max(inset, vh - CAP_H - inset));
  }
  return { edge, targetX, targetY };
}

export function expandFromBall(pos: { x: number; y: number }) {
  const inset = 10;
  const { vw, vh } = viewSize();
  pos.x = clamp(pos.x, inset, Math.max(inset, vw - SIZE - inset));
  pos.y = clamp(pos.y, inset, Math.max(inset, vh - SIZE - inset));
}

/** Animate pos toward target over ~220ms; returns cancel handle. */
export function animateSnap(
  pos: { x: number; y: number },
  targetX: number,
  targetY: number,
  prevRaf: number,
): number {
  cancelAnimationFrame(prevRaf);
  const startX = pos.x;
  const startY = pos.y;
  const t0 = performance.now();
  const dur = 220;
  let raf = 0;
  const step = (now: number) => {
    const u = Math.min(1, (now - t0) / dur);
    const e = 1 - Math.pow(1 - u, 3);
    pos.x = startX + (targetX - startX) * e;
    pos.y = startY + (targetY - startY) * e;
    if (u < 1) raf = requestAnimationFrame(step);
  };
  raf = requestAnimationFrame(step);
  return raf;
}
