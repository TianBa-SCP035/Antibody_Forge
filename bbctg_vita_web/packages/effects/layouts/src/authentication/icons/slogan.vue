<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';

defineOptions({ name: 'SloganIcon' });

type PaletteKey =
  | 'antigen'
  | 'cdr'
  | 'disulfide'
  | 'dna'
  | 'glycan'
  | 'heavy'
  | 'light';

interface AtomNode {
  chain: number;
  order: number;
  palette: PaletteKey;
  phase: number;
  prog: number;
  radius: number;
  targets: Array<[number, number, number]>;
  vx: number;
  vy: number;
  vz: number;
  x: number;
  y: number;
  z: number;
}

interface BondLink {
  a: number;
  b: number;
  kind: 'backbone' | 'bridge' | 'dock' | 'rung';
  modes: boolean[];
  prog: number;
}

interface FlowSignal {
  from: number;
  mode: number;
  offset: number;
  speed: number;
  to: number;
}

interface AmbientMote {
  ang: number;
  orbitR: number;
  size: number;
  speed: number;
  tilt: number;
  yOff: number;
}

const canvasRef = ref<HTMLCanvasElement | null>(null);
const activeMode = ref(0);
const isDragging = ref(false);

const MODE_COUNT = 3;
const STAGE_TITLES = [
  '靶点识别 · 抗体诱导契合与变构传导',
  '基因重排 · B-DNA 双螺旋文库编码',
  '高通量筛选 · 候选克隆亲和力富集',
];

let rafId = 0;
let autoTimer = 0;
let ro: null | ResizeObserver = null;
let triggerModeSwitch: ((idx?: number) => void) | null = null;

function restartAutoCycle(isPaused: () => boolean) {
  if (autoTimer) window.clearInterval(autoTimer);
  autoTimer = window.setInterval(() => {
    if (!isPaused()) {
      triggerModeSwitch?.();
    }
  }, 8000);
}

function handleSelectMode(idx?: number) {
  triggerModeSwitch?.(idx);
}

function createJewelSprite(
  coreHex: string,
  midHex: string,
  rimRgba: string,
  haloRgba: string,
): HTMLCanvasElement {
  const size = 64;
  const c = document.createElement('canvas');
  c.width = size;
  c.height = size;
  const ctx = c.getContext('2d');
  if (!ctx) return c;

  const cx = size / 2;
  const cy = size / 2;
  const r = size * 0.25;

  const halo = ctx.createRadialGradient(cx, cy, r * 0.18, cx, cy, size * 0.47);
  halo.addColorStop(0, haloRgba);
  halo.addColorStop(0.52, rimRgba);
  halo.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = halo;
  ctx.beginPath();
  ctx.arc(cx, cy, size * 0.47, 0, Math.PI * 2);
  ctx.fill();

  const body = ctx.createRadialGradient(
    cx - r * 0.32,
    cy - r * 0.32,
    r * 0.05,
    cx,
    cy,
    r,
  );
  body.addColorStop(0, '#ffffff');
  body.addColorStop(0.34, coreHex);
  body.addColorStop(0.78, midHex);
  body.addColorStop(1, rimRgba);

  ctx.fillStyle = body;
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.fill();

  return c;
}

function buildMolecularSystem(): {
  atoms: AtomNode[];
  bonds: BondLink[];
  motes: AmbientMote[];
  signals: FlowSignal[];
} {
  const atoms: AtomNode[] = [];
  const bonds: BondLink[] = [];
  const signals: FlowSignal[] = [];

  const pushAtom = (
    chain: number,
    order: number,
    prog: number,
    palette: PaletteKey,
    radius: number,
    p0: [number, number, number],
  ) => {
    const idx = atoms.length;
    atoms.push({
      chain,
      order,
      palette,
      phase: idx * 0.39,
      prog,
      radius,
      targets: [p0, [0, 0, 0], [0, 0, 0]],
      vx: 0,
      vy: 0,
      vz: 0,
      x: p0[0],
      y: p0[1],
      z: p0[2],
    });
    return idx;
  };

  // ==================== 构象 0：3D Y 型 IgG 抗体 - 靶点抗原结合复合体 ====================
  // 1 & 2. 左右两条重链 (Heavy Chains: Fc CH3->CH2 -> Hinge -> Fab CH1->VH)
  const heavyLeftIds: number[] = [];
  const heavyRightIds: number[] = [];
  const H_STEPS = 32;

  for (let i = 0; i < H_STEPS; i++) {
    const t = i / (H_STEPS - 1); // 0 = Fc 底端, 0.42 = Hinge 铰链区, 1.0 = VH CDR 顶端
    let xL = 0;
    let yL = 0;
    let zL = 0;
    let xR = 0;
    let yR = 0;
    let zR = 0;

    if (t < 0.42) {
      // Fc 段：CH3 紧密配对，CH2 包围中央糖链呈马蹄形微拱，Hinge 处收拢交联
      const u = t / 0.42;
      const y = 140 - u * 114; // +140 -> +26
      const twist = u * Math.PI * 2.0;
      const spread = 13 + Math.sin(u * Math.PI) * 7;
      xL = -spread + Math.cos(twist) * 4.5;
      zL = Math.sin(twist) * 13;
      yL = y;

      xR = spread - Math.cos(twist) * 4.5;
      zR = -Math.sin(twist) * 13;
      yR = y;
    } else {
      // 铰链区 -> Fab 双臂 (CH1 -> VH 舒展 Y 型)
      const u = (t - 0.42) / 0.58;
      const ease = Math.pow(u, 0.9);
      const y = 26 - u * 106; // +26 -> -80
      const armX = 12 + ease * 96; // 12 -> 108
      const helix = u * Math.PI * 2.7;
      const rHelix = 8.5 * (1 - u * 0.2);

      xL = -armX + Math.cos(helix) * rHelix;
      yL = y + Math.sin(helix) * 3.8;
      zL = Math.sin(helix) * 14;

      xR = armX - Math.cos(helix) * rHelix;
      yR = y + Math.sin(helix) * 3.8;
      zR = -Math.sin(helix) * 14;
    }

    const isCdr = i >= H_STEPS - 4;
    const rad = isCdr ? 4.6 : i % 4 === 0 ? 3.9 : 2.8;
    const pal: PaletteKey = isCdr ? 'cdr' : 'heavy';

    const idL = pushAtom(1, i, t, pal, rad, [xL, yL, zL]);
    heavyLeftIds.push(idL);
    if (i > 0) {
      bonds.push({
        a: heavyLeftIds[i - 1]!,
        b: idL,
        kind: 'backbone',
        modes: [true, false, false],
        prog: t,
      });
    }

    const idR = pushAtom(2, i, t, pal, rad, [xR, yR, zR]);
    heavyRightIds.push(idR);
    if (i > 0) {
      bonds.push({
        a: heavyRightIds[i - 1]!,
        b: idR,
        kind: 'backbone',
        modes: [true, false, false],
        prog: t,
      });
    }
  }

  // 铰链二硫键与 Fc 域间桥接
  for (const step of [5, 11, 13, 14]) {
    bonds.push({
      a: heavyLeftIds[step]!,
      b: heavyRightIds[step]!,
      kind: 'bridge',
      modes: [true, false, false],
      prog: step / (H_STEPS - 1),
    });
  }

  // 3 & 4. 左右两条轻链 (Light Chains: CL -> VL，沿 Fab 外侧与重链伴行缠绕)
  const lightLeftIds: number[] = [];
  const lightRightIds: number[] = [];
  const L_STEPS = 20;

  for (let i = 0; i < L_STEPS; i++) {
    const u = i / (L_STEPS - 1);
    const prog = 0.45 + u * 0.55;
    const ease = Math.pow(u, 0.9);
    const y = 15 - u * 89; // +15 -> -74
    const armX = 31 + ease * 94; // 31 -> 125
    const helix = u * Math.PI * 2.7 + Math.PI * 0.9;
    const rHelix = 8.5;

    const xL = -armX + Math.cos(helix) * rHelix;
    const yL = y + Math.cos(helix) * 3.8;
    const zL = Math.sin(helix) * 14.5;

    const xR = armX - Math.cos(helix) * rHelix;
    const yR = y + Math.cos(helix) * 3.8;
    const zR = -Math.sin(helix) * 14.5;

    const isCdr = i >= L_STEPS - 3;
    const rad = isCdr ? 4.4 : i % 3 === 0 ? 3.7 : 2.7;
    const pal: PaletteKey = isCdr ? 'cdr' : 'light';

    const idL = pushAtom(3, i, prog, pal, rad, [xL, yL, zL]);
    lightLeftIds.push(idL);
    if (i > 0) {
      bonds.push({
        a: lightLeftIds[i - 1]!,
        b: idL,
        kind: 'backbone',
        modes: [true, false, false],
        prog,
      });
    }

    const idR = pushAtom(4, i, prog, pal, rad, [xR, yR, zR]);
    lightRightIds.push(idR);
    if (i > 0) {
      bonds.push({
        a: lightRightIds[i - 1]!,
        b: idR,
        kind: 'backbone',
        modes: [true, false, false],
        prog,
      });
    }

    if (i === 2 || i === 9 || i === 15 || i === L_STEPS - 2) {
      const hIdx = Math.min(H_STEPS - 1, 13 + i);
      bonds.push(
        {
          a: idL,
          b: heavyLeftIds[hIdx]!,
          kind: 'bridge',
          modes: [true, false, false],
          prog,
        },
        {
          a: idR,
          b: heavyRightIds[hIdx]!,
          kind: 'bridge',
          modes: [true, false, false],
          prog,
        },
      );
    }
  }

  // 5. Fc N297 糖基化核心与铰链二硫键亮点
  const glycanCoords: Array<[number, number, number]> = [
    [-6, 76, 5],
    [0, 70, 0],
    [6, 76, -5],
    [0, 24, 0],
    [-7, 20, 3],
    [7, 20, -3],
  ];
  glycanCoords.forEach((pt, idx) => {
    const isDisulfide = idx >= 3;
    pushAtom(
      5,
      idx,
      isDisulfide ? 0.44 : 0.26,
      isDisulfide ? 'disulfide' : 'glycan',
      isDisulfide ? 4.0 : 3.5,
      pt,
    );
  });

  // 6. 顶部悬浮的 3D 靶点抗原几何晶格核 (Target Antigen Polyhedron)
  const antigenIds: number[] = [];
  const AG_COUNT = 26;
  const goldenAngle = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < AG_COUNT; i++) {
    const yNorm = 1 - (i / (AG_COUNT - 1)) * 2;
    const rSlice = Math.sqrt(Math.max(0, 1 - yNorm * yNorm));
    const theta = goldenAngle * i;
    const rx = 44;
    const ry = 24;
    const rz = 30;
    const x = Math.cos(theta) * rSlice * rx;
    const y = -120 + yNorm * ry;
    const z = Math.sin(theta) * rSlice * rz;
    const isEpitope = y > -114 && Math.abs(x) > 18;
    const id = pushAtom(
      6,
      i,
      1.0,
      isEpitope ? 'cdr' : 'antigen',
      isEpitope ? 4.2 : 3.6,
      [x, y, z],
    );
    antigenIds.push(id);
  }

  for (let i = 0; i < antigenIds.length; i++) {
    for (let j = i + 1; j < antigenIds.length; j++) {
      const a = atoms[antigenIds[i]!]!.targets[0]!;
      const b = atoms[antigenIds[j]!]!.targets[0]!;
      const d = Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
      if (d < 26) {
        bonds.push({
          a: antigenIds[i]!,
          b: antigenIds[j]!,
          kind: 'bridge',
          modes: [true, false, true],
          prog: 1.0,
        });
      }
    }
  }

  // CDR 顶端与靶点抗原表位之间的 4 条特异性亲和力锁合光束
  const dockPairs: Array<[number, number]> = [
    [ antigenIds[18]!, heavyLeftIds[H_STEPS - 1]! ],
    [ antigenIds[22]!, lightLeftIds[L_STEPS - 1]! ],
    [ antigenIds[19]!, heavyRightIds[H_STEPS - 1]! ],
    [ antigenIds[23]!, lightRightIds[L_STEPS - 1]! ],
  ];
  dockPairs.forEach(([fromAg, toCdr], idx) => {
    bonds.push({
      a: fromAg,
      b: toCdr,
      kind: 'dock',
      modes: [true, false, false],
      prog: 1.0,
    });
    signals.push({
      from: fromAg,
      to: toCdr,
      mode: 0,
      offset: idx * 0.25,
      speed: 0.78,
    });
  });

  // 7. 外围环绕的真实右手 B-DNA 基因双螺旋环 (2.42 rad 大沟/小沟不对称几何)
  const dnaRingA: number[] = [];
  const dnaRingB: number[] = [];
  const RING_PAIRS = 16;
  const GROOVE_OFFSET = 2.42; // 140° 真实 Watson-Crick 大沟/小沟不对称偏移

  for (let i = 0; i < RING_PAIRS; i++) {
    const u = i / RING_PAIRS;
    const ang = u * Math.PI * 2;
    const ringR = 156;
    const twist = u * Math.PI * 6;
    const minorR = 11;

    const generateRingPt = (phaseOffset: number): [number, number, number] => {
      const rLocal = ringR + Math.cos(twist + phaseOffset) * minorR;
      const yLocal = Math.sin(twist + phaseOffset) * minorR;
      const rawX = Math.cos(ang) * rLocal;
      const rawZ = Math.sin(ang) * rLocal;
      const tilt = 0.44;
      const y = yLocal * Math.cos(tilt) - rawZ * Math.sin(tilt) + 14;
      const z = yLocal * Math.sin(tilt) + rawZ * Math.cos(tilt);
      return [rawX, y, z];
    };

    const idA = pushAtom(7, i, u, 'dna', 3.1, generateRingPt(0));
    const idB = pushAtom(8, i, u, 'light', 3.1, generateRingPt(GROOVE_OFFSET));
    dnaRingA.push(idA);
    dnaRingB.push(idB);

    if (i > 0) {
      bonds.push(
        {
          a: dnaRingA[i - 1]!,
          b: idA,
          kind: 'backbone',
          modes: [true, false, false],
          prog: u,
        },
        {
          a: dnaRingB[i - 1]!,
          b: idB,
          kind: 'backbone',
          modes: [true, false, false],
          prog: u,
        },
      );
    }
    if (i % 2 === 0) {
      bonds.push({
        a: idA,
        b: idB,
        kind: 'bridge',
        modes: [true, false, false],
        prog: u,
      });
    }
  }
  bonds.push(
    {
      a: dnaRingA[RING_PAIRS - 1]!,
      b: dnaRingA[0]!,
      kind: 'backbone',
      modes: [true, false, false],
      prog: 1,
    },
    {
      a: dnaRingB[RING_PAIRS - 1]!,
      b: dnaRingB[0]!,
      kind: 'backbone',
      modes: [true, false, false],
      prog: 1,
    },
  );

  // ==================== 构象 1：真实右手 B-DNA 双螺旋基因链 (含大沟/小沟与转录阅读波) ====================
  const total = atoms.length;
  const strandAIds: number[] = [];
  const strandBIds: number[] = [];
  const rungInteriorIds: number[] = [];

  for (let i = 0; i < total; i++) {
    if (i < 48) strandAIds.push(i);
    else if (i < 96) strandBIds.push(i);
    else rungInteriorIds.push(i);
  }

  const PAIRS = strandAIds.length;
  const tiltZ = 0.32;
  const cosT = Math.cos(tiltZ);
  const sinT = Math.sin(tiltZ);

  const rotateHelixPt = (
    x: number,
    y: number,
    z: number,
  ): [number, number, number] => [x * cosT - y * sinT, x * sinT + y * cosT, z];

  for (let k = 0; k < PAIRS; k++) {
    const u = k / (PAIRS - 1);
    const y = (u - 0.5) * 292;
    const theta = u * Math.PI * 4.6;
    const r = 64;

    const idA = strandAIds[k]!;
    const idB = strandBIds[k]!;
    // 采用 2.42 rad (~140°) 偏移，真实呈现 B-DNA 的大沟与小沟
    atoms[idA]!.targets[1] = rotateHelixPt(
      Math.cos(theta) * r,
      y,
      Math.sin(theta) * r,
    );
    atoms[idB]!.targets[1] = rotateHelixPt(
      Math.cos(theta + GROOVE_OFFSET) * r,
      y,
      Math.sin(theta + GROOVE_OFFSET) * r,
    );

    if (k > 0) {
      bonds.push(
        {
          a: strandAIds[k - 1]!,
          b: idA,
          kind: 'backbone',
          modes: [false, true, false],
          prog: u,
        },
        {
          a: strandBIds[k - 1]!,
          b: idB,
          kind: 'backbone',
          modes: [false, true, false],
          prog: u,
        },
      );
    }
    if (k % 2 === 0) {
      bonds.push({
        a: idA,
        b: idB,
        kind: 'rung',
        modes: [false, true, false],
        prog: u,
      });
      signals.push({
        from: idA,
        to: idB,
        mode: 1,
        offset: u,
        speed: 0.65,
      });
    }
  }

  for (let m = 0; m < rungInteriorIds.length; m++) {
    const id = rungInteriorIds[m]!;
    const pairIdx = Math.floor((m / rungInteriorIds.length) * (PAIRS - 1));
    const frac = m % 2 === 0 ? 0.35 : 0.65;
    const pA = atoms[strandAIds[pairIdx]!]!.targets[1]!;
    const pB = atoms[strandBIds[pairIdx]!]!.targets[1]!;
    atoms[id]!.targets[1] = [
      pA[0] + (pB[0] - pA[0]) * frac,
      pA[1] + (pB[1] - pA[1]) * frac,
      pA[2] + (pB[2] - pA[2]) * frac,
    ];
  }

  // ==================== 构象 2：3D 同心二十面体亲和力筛选球面矩阵 ====================
  const coreGroup: number[] = [];
  const outerGroup: number[] = [];
  for (let i = 0; i < total; i++) {
    if (atoms[i]!.chain === 5 || atoms[i]!.chain === 6) coreGroup.push(i);
    else outerGroup.push(i);
  }

  for (let k = 0; k < coreGroup.length; k++) {
    const id = coreGroup[k]!;
    const yN = 1 - ((k + 0.5) / coreGroup.length) * 2;
    const rS = Math.sqrt(Math.max(0, 1 - yN * yN));
    const ang = goldenAngle * k;
    const coreR = 42;
    atoms[id]!.targets[2] = [
      Math.cos(ang) * rS * coreR,
      yN * coreR,
      Math.sin(ang) * rS * coreR,
    ];
  }

  for (let k = 0; k < outerGroup.length; k++) {
    const id = outerGroup[k]!;
    const yN = 1 - ((k + 0.5) / outerGroup.length) * 2;
    const rS = Math.sqrt(Math.max(0, 1 - yN * yN));
    const ang = goldenAngle * k;
    const shellR = 128;
    atoms[id]!.targets[2] = [
      Math.cos(ang) * rS * shellR,
      yN * shellR,
      Math.sin(ang) * rS * shellR,
    ];
  }

  for (let i = 0; i < outerGroup.length; i++) {
    const idA = outerGroup[i]!;
    const pA = atoms[idA]!.targets[2]!;
    for (let j = i + 1; j < outerGroup.length; j++) {
      const idB = outerGroup[j]!;
      const pB = atoms[idB]!.targets[2]!;
      const d = Math.hypot(pA[0] - pB[0], pA[1] - pB[1], pA[2] - pB[2]);
      if (d < 40) {
        bonds.push({
          a: idA,
          b: idB,
          kind: 'bridge',
          modes: [false, false, true],
          prog: i / outerGroup.length,
        });
      }
    }
    if (i % 9 === 0) {
      const coreId = coreGroup[i % coreGroup.length]!;
      bonds.push({
        a: idA,
        b: coreId,
        kind: 'dock',
        modes: [false, false, true],
        prog: i / outerGroup.length,
      });
      signals.push({
        from: idA,
        to: coreId,
        mode: 2,
        offset: i * 0.09,
        speed: 0.72,
      });
    }
  }

  // 环境悬浮光子微粒
  const motes: AmbientMote[] = Array.from({ length: 24 }, (_, i) => ({
    ang: (i / 24) * Math.PI * 2,
    orbitR: i < 14 ? 152 : 106 + (i % 5) * 16,
    size: i < 14 ? 1.9 : 1.4,
    speed: (i % 2 === 0 ? 1 : -1) * (0.16 + (i % 4) * 0.04),
    tilt: i < 7 ? 0.45 : i < 14 ? -0.38 : (i % 3 - 1) * 0.6,
    yOff: i < 14 ? 6 : ((i % 7) - 3) * 24,
  }));

  return { atoms, bonds, motes, signals };
}

onMounted(() => {
  const canvas = canvasRef.value;
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const sprites: Record<PaletteKey, HTMLCanvasElement> = {
    heavy: createJewelSprite(
      '#93c5fd',
      '#2563eb',
      'rgba(37,99,235,0.42)',
      'rgba(59,130,246,0.2)',
    ),
    light: createJewelSprite(
      '#67e8f9',
      '#0891b2',
      'rgba(6,182,212,0.42)',
      'rgba(20,184,166,0.2)',
    ),
    cdr: createJewelSprite(
      '#fde68a',
      '#f59e0b',
      'rgba(244,63,94,0.52)',
      'rgba(251,191,36,0.3)',
    ),
    antigen: createJewelSprite(
      '#c7d2fe',
      '#6366f1',
      'rgba(99,102,241,0.45)',
      'rgba(129,140,248,0.22)',
    ),
    glycan: createJewelSprite(
      '#99f6e4',
      '#0d9488',
      'rgba(20,184,166,0.4)',
      'rgba(45,212,191,0.18)',
    ),
    disulfide: createJewelSprite(
      '#fef08a',
      '#eab308',
      'rgba(234,179,8,0.48)',
      'rgba(250,204,21,0.24)',
    ),
    dna: createJewelSprite(
      '#bfdbfe',
      '#3b82f6',
      'rgba(59,130,246,0.35)',
      'rgba(96,165,250,0.14)',
    ),
  };

  const { atoms, bonds, motes, signals } = buildMolecularSystem();

  let width = 580;
  let height = 450;
  let dpr = 1;

  const resize = () => {
    const rect = canvas.getBoundingClientRect();
    width = Math.max(320, rect.width || 580);
    height = Math.max(260, rect.height || 450);
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
  };
  resize();
  ro = new ResizeObserver(resize);
  ro.observe(canvas);

  let rotY = -0.26;
  let rotX = 0.16;
  let velY = 0.0026;
  let velX = 0;
  let pointerX = 0;
  let pointerY = 0;
  let pointerActive = false;
  let dragStartX = 0;
  let dragStartY = 0;
  let dragMoved = false;
  let pulseWave = 0;

  triggerModeSwitch = (idx?: number) => {
    if (typeof idx === 'number') {
      activeMode.value = ((idx % MODE_COUNT) + MODE_COUNT) % MODE_COUNT;
    } else {
      activeMode.value = (activeMode.value + 1) % MODE_COUNT;
    }
    pulseWave = 1;
    velY = (velY >= 0 ? 1 : -1) * 0.014;
    restartAutoCycle(() => isDragging.value || pointerActive);
  };
  restartAutoCycle(() => isDragging.value || pointerActive);

  const onPointerDown = (e: PointerEvent) => {
    isDragging.value = true;
    dragMoved = false;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    canvas.setPointerCapture?.(e.pointerId);
  };

  const onPointerMove = (e: PointerEvent) => {
    const rect = canvas.getBoundingClientRect();
    pointerX = e.clientX - rect.left - width / 2;
    pointerY = e.clientY - rect.top - height / 2;
    pointerActive = true;

    if (isDragging.value) {
      const dx = e.clientX - dragStartX;
      const dy = e.clientY - dragStartY;
      if (Math.abs(dx) + Math.abs(dy) > 5) {
        dragMoved = true;
      }
      velY = dx * 0.006;
      velX = dy * 0.005;
      rotY += velY;
      rotX = Math.max(-0.82, Math.min(0.82, rotX + velX));
      dragStartX = e.clientX;
      dragStartY = e.clientY;
    }
  };

  const onPointerUp = (e: PointerEvent) => {
    if (isDragging.value && !dragMoved) {
      triggerModeSwitch?.();
    }
    isDragging.value = false;
    canvas.releasePointerCapture?.(e.pointerId);
  };

  const onPointerLeave = () => {
    pointerActive = false;
    isDragging.value = false;
  };

  canvas.addEventListener('pointerdown', onPointerDown);
  canvas.addEventListener('pointermove', onPointerMove);
  canvas.addEventListener('pointerup', onPointerUp);
  canvas.addEventListener('pointerleave', onPointerLeave);

  const projected = atoms.map(() => ({
    alpha: 1,
    scale: 1,
    sx: 0,
    sy: 0,
    z: 0,
  }));
  const sortedIndices = atoms.map((_, idx) => idx);

  const startTime = performance.now();

  const drawOrbitalRing = (
    cx: number,
    cy: number,
    radius: number,
    tiltXAngle: number,
    tiltZAngle: number,
    rotYAngle: number,
    rotXCam: number,
    baseScale: number,
    fov: number,
    strokeStyle: string,
  ) => {
    const steps = 64;
    ctx.strokeStyle = strokeStyle;
    ctx.lineWidth = 1.15 * baseScale;
    ctx.beginPath();
    for (let s = 0; s <= steps; s++) {
      const a = (s / steps) * Math.PI * 2;
      const lx = Math.cos(a) * radius;
      const lz = Math.sin(a) * radius;
      const yTilt = -lz * Math.sin(tiltXAngle);
      const zTilt = lz * Math.cos(tiltXAngle);
      const xTilt = lx * Math.cos(tiltZAngle) - yTilt * Math.sin(tiltZAngle);
      const yTilt2 =
        lx * Math.sin(tiltZAngle) + yTilt * Math.cos(tiltZAngle) + 6;

      const cY = Math.cos(rotYAngle);
      const sY = Math.sin(rotYAngle);
      const cX = Math.cos(rotXCam);
      const sX = Math.sin(rotXCam);

      const x1 = xTilt * cY - zTilt * sY;
      const z1 = xTilt * sY + zTilt * cY;
      const y2 = yTilt2 * cX - z1 * sX;
      const z2 = yTilt2 * sX + z1 * cX;
      const p = fov / (fov + z2 + 210);
      const sx = cx + x1 * baseScale * p;
      const sy = cy + y2 * baseScale * p;
      if (s === 0) ctx.moveTo(sx, sy);
      else ctx.lineTo(sx, sy);
    }
    ctx.stroke();
  };

  const renderFrame = (now: number) => {
    const t = (now - startTime) * 0.001;
    const isDark = document.documentElement.classList.contains('dark');

    ctx.save();
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, width, height);

    const cx = width * 0.5;
    const cy = height * 0.51;
    // 适度放大的优雅比例（比最初版大 ~12%，四周留有呼吸感）
    const baseScale = Math.min(width, height) / 355;
    const fov = 580;

    const mode = activeMode.value;

    if (!isDragging.value) {
      // 在构象 0 (Y 型抗体) 下，当转到接近 90° 侧面时略微加快通过，在正面立体角放慢驻留，避免长时间侧扁
      const edgeFactor = Math.abs(Math.sin(rotY));
      const baseSpeed = mode === 0 ? 0.0022 + edgeFactor * 0.0018 : 0.0028;
      velY += (baseSpeed - velY) * 0.04;
      rotY += velY;
      const targetRotX = pointerActive
        ? Math.max(-0.38, Math.min(0.42, 0.14 + (pointerY / height) * 0.45))
        : 0.16 + Math.sin(t * 0.45) * 0.06;
      rotX += (targetRotX - rotX) * 0.05;
    }

    if (pulseWave > 0.005) {
      pulseWave *= 0.93;
    } else {
      pulseWave = 0;
    }

    // 1. 中心柔和生物光场晕染
    const bgGlow = ctx.createRadialGradient(
      cx,
      cy - 8 * baseScale,
      10 * baseScale,
      cx,
      cy,
      188 * baseScale,
    );
    if (isDark) {
      bgGlow.addColorStop(0, 'rgba(56, 189, 248, 0.16)');
      bgGlow.addColorStop(0.52, 'rgba(99, 102, 241, 0.08)');
      bgGlow.addColorStop(1, 'rgba(0, 0, 0, 0)');
    } else {
      bgGlow.addColorStop(0, 'rgba(37, 99, 235, 0.13)');
      bgGlow.addColorStop(0.55, 'rgba(6, 182, 212, 0.05)');
      bgGlow.addColorStop(1, 'rgba(255, 255, 255, 0)');
    }
    ctx.fillStyle = bgGlow;
    ctx.beginPath();
    ctx.arc(cx, cy, 188 * baseScale, 0, Math.PI * 2);
    ctx.fill();

    // 2. 双层纤细 3D 全息轨道丝环
    drawOrbitalRing(
      cx,
      cy,
      156,
      0.46,
      0.22,
      rotY * 0.55 + t * 0.12,
      rotX,
      baseScale,
      fov,
      isDark ? 'rgba(56, 189, 248, 0.15)' : 'rgba(37, 99, 235, 0.12)',
    );
    drawOrbitalRing(
      cx,
      cy,
      140,
      -0.4,
      -0.26,
      -rotY * 0.45 - t * 0.1,
      rotX,
      baseScale,
      fov,
      isDark ? 'rgba(45, 212, 191, 0.13)' : 'rgba(8, 145, 178, 0.1)',
    );

    // 3. 点击构象切换时的能量扩散涟漪
    if (pulseWave > 0.01) {
      const waveR = (1 - pulseWave) * 172 * baseScale + 16 * baseScale;
      ctx.strokeStyle = isDark
        ? `rgba(56, 189, 248, ${(pulseWave * 0.48).toFixed(3)})`
        : `rgba(37, 99, 235, ${(pulseWave * 0.36).toFixed(3)})`;
      ctx.lineWidth = 1.6 * baseScale;
      ctx.beginPath();
      ctx.arc(cx, cy, waveR, 0, Math.PI * 2);
      ctx.stroke();
    }

    const cosY = Math.cos(rotY);
    const sinY = Math.sin(rotY);
    const cosX = Math.cos(rotX);
    const sinX = Math.sin(rotX);

    // 4. 环境悬浮光子微粒
    for (let i = 0; i < motes.length; i++) {
      const m = motes[i]!;
      const a = m.ang + t * m.speed;
      const lx = Math.cos(a) * m.orbitR;
      const lz = Math.sin(a) * m.orbitR;
      const ly = m.yOff + Math.sin(a * 2 + i) * 7;
      const yT = ly * Math.cos(m.tilt) - lz * Math.sin(m.tilt);
      const zT = ly * Math.sin(m.tilt) + lz * Math.cos(m.tilt);

      const x1 = lx * cosY - zT * sinY;
      const z1 = lx * sinY + zT * cosY;
      const y2 = yT * cosX - z1 * sinX;
      const z2 = yT * sinX + z1 * cosX;
      const p = fov / (fov + z2 + 210);
      const sx = cx + x1 * baseScale * p;
      const sy = cy + y2 * baseScale * p;
      const twinkle = 0.24 + 0.52 * (0.5 + 0.5 * Math.sin(t * 2.1 + i * 1.7));

      ctx.fillStyle =
        i % 2 === 0
          ? `rgba(56, 189, 248, ${twinkle.toFixed(3)})`
          : `rgba(20, 184, 166, ${twinkle.toFixed(3)})`;
      ctx.beginPath();
      ctx.arc(sx, sy, m.size * baseScale * p, 0, Math.PI * 2);
      ctx.fill();
    }

    // ==================== 5. 具有生物学立意的内部真实运动 ====================
    // - 构象 0 (抗体结合)：诱导契合周期 (抗原轻嵌入 CDR 槽 -> Fab 双臂绕铰链微张合 ±3.8° -> 触发从 CDR 1.0 向 Fc 0.0 传导的变构波)
    // - 构象 1 (基因双螺旋)：转录阅读波从下向上 (0.0 -> 1.0) 顺序扫过碱基对横档
    // - 构象 2 (高通量筛选)：亲和力富集波从外层候选克隆球壳向中心靶点核汇聚
    const dockCycle = 0.5 + 0.5 * Math.sin(t * 0.95);
    const hingeFlex = (0.5 - dockCycle) * 0.068; // Fab 双臂绕铰链生理微张合
    const antigenDip = dockCycle * 7.5; // 靶点抗原诱导契合下沉
    const allostericWave =
      mode === 0
        ? 1.05 - ((t * 0.42) % 1.35) // CDR (1.0) -> Hinge (0.42) -> Fc (0.0)
        : (t * 0.38) % 1.2; // DNA 从下到上阅读波

    for (let i = 0; i < atoms.length; i++) {
      const atom = atoms[i]!;
      const target = atom.targets[mode]!;

      let tx = target[0];
      let ty = target[1];
      let tz = target[2];

      if (mode === 0) {
        if (atom.chain === 6) {
          // 顶部靶点抗原随诱导契合缓步下沉锁合
          ty += antigenDip - 3.5;
        } else if (
          (atom.chain === 1 || atom.chain === 3) &&
          atom.prog > 0.42
        ) {
          // 左 Fab 臂绕铰链支点 (-12, +26) 柔顺生理张合
          const dx = tx - -12;
          const dy = ty - 26;
          const c = Math.cos(hingeFlex);
          const s = Math.sin(hingeFlex);
          tx = -12 + dx * c - dy * s;
          ty = 26 + dx * s + dy * c;
        } else if (
          (atom.chain === 2 || atom.chain === 4) &&
          atom.prog > 0.42
        ) {
          // 右 Fab 臂绕铰链支点 (+12, +26) 对称张合
          const dx = tx - 12;
          const dy = ty - 26;
          const c = Math.cos(-hingeFlex);
          const s = Math.sin(-hingeFlex);
          tx = 12 + dx * c - dy * s;
          ty = 26 + dx * s + dy * c;
        } else if (atom.chain >= 7) {
          // 外围 B-DNA 基因环平稳公转
          const ringSpin = t * 0.22;
          const cR = Math.cos(ringSpin);
          const sR = Math.sin(ringSpin);
          const rx = tx * cR - tz * sR;
          const rz = tx * sR + tz * cR;
          tx = rx;
          tz = rz;
        }
      } else if (mode === 1) {
        // B-DNA 双螺旋随转录波轻微呼吸
        const readBoost = Math.max(0, 1 - Math.abs(atom.prog - allostericWave) / 0.14);
        tx *= 1 + readBoost * 0.04;
        tz *= 1 + readBoost * 0.04;
      } else {
        // 亲和力筛选球壳呼吸脉动
        const pulseScale = 1 + Math.sin(t * 1.6 + atom.prog * Math.PI * 2) * 0.032;
        tx *= pulseScale;
        ty *= pulseScale;
        tz *= pulseScale;
      }

      atom.vx = (atom.vx + (tx - atom.x) * 0.1) * 0.76;
      atom.vy = (atom.vy + (ty - atom.y) * 0.1) * 0.76;
      atom.vz = (atom.vz + (tz - atom.z) * 0.1) * 0.76;
      atom.x += atom.vx;
      atom.y += atom.vy;
      atom.z += atom.vz;

      const x1 = atom.x * cosY - atom.z * sinY;
      const z1 = atom.x * sinY + atom.z * cosY;
      const y2 = atom.y * cosX - z1 * sinX;
      const z2 = atom.y * sinX + z1 * cosX;

      const persp = fov / (fov + z2 + 210);
      let sx = cx + x1 * baseScale * persp;
      let sy = cy + y2 * baseScale * persp;

      if (pointerActive && !isDragging.value) {
        const dx = sx - (cx + pointerX);
        const dy = sy - (cy + pointerY);
        const distSq = dx * dx + dy * dy;
        const maxDist = 86 * baseScale;
        if (distSq < maxDist * maxDist && distSq > 1) {
          const dist = Math.sqrt(distSq);
          const force = (1 - dist / maxDist) * 9 * baseScale;
          sx += (dx / dist) * force;
          sy += (dy / dist) * force;
        }
      }

      const depthNorm = Math.max(0, Math.min(1, (190 - z2) / 380));
      const p = projected[i]!;
      p.sx = sx;
      p.sy = sy;
      p.z = z2;
      p.scale = persp * baseScale;
      p.alpha = 0.25 + depthNorm * 0.75;
    }

    // 6. 绘制流线型 3D 骨架丝带、碱基横档与亲和力光子桥
    ctx.lineCap = 'round';
    for (let i = 0; i < bonds.length; i++) {
      const bond = bonds[i]!;
      if (!bond.modes[mode]) continue;
      const pa = projected[bond.a]!;
      const pb = projected[bond.b]!;
      const avgAlpha = (pa.alpha + pb.alpha) * 0.5;
      const avgScale = (pa.scale + pb.scale) * 0.5;
      const waveHit = Math.max(0, 1 - Math.abs(bond.prog - allostericWave) / 0.14);

      if (bond.kind === 'dock') {
        const pulse = 0.55 + 0.45 * Math.sin(t * 3.6 + i);
        ctx.strokeStyle = isDark
          ? `rgba(251, 191, 36, ${(avgAlpha * pulse * 0.85).toFixed(3)})`
          : `rgba(245, 158, 11, ${(avgAlpha * pulse * 0.75).toFixed(3)})`;
        ctx.lineWidth = 2.0 * avgScale;
        ctx.beginPath();
        ctx.moveTo(pa.sx, pa.sy);
        ctx.lineTo(pb.sx, pb.sy);
        ctx.stroke();
      } else if (bond.kind === 'rung') {
        ctx.strokeStyle =
          waveHit > 0.15
            ? `rgba(251, 191, 36, ${(avgAlpha * (0.45 + waveHit * 0.45)).toFixed(3)})`
            : isDark
              ? `rgba(56, 189, 248, ${(avgAlpha * 0.42).toFixed(3)})`
              : `rgba(14, 165, 233, ${(avgAlpha * 0.34).toFixed(3)})`;
        ctx.lineWidth = (1.7 + waveHit * 0.7) * avgScale;
        ctx.beginPath();
        ctx.moveTo(pa.sx, pa.sy);
        ctx.lineTo(pb.sx, pb.sy);
        ctx.stroke();
      } else if (bond.kind === 'bridge') {
        ctx.strokeStyle = isDark
          ? `rgba(148, 163, 184, ${(avgAlpha * 0.28).toFixed(3)})`
          : `rgba(100, 116, 139, ${(avgAlpha * 0.22).toFixed(3)})`;
        ctx.lineWidth = 1.2 * avgScale;
        ctx.beginPath();
        ctx.moveTo(pa.sx, pa.sy);
        ctx.lineTo(pb.sx, pb.sy);
        ctx.stroke();
      } else {
        const chain = atoms[bond.a]!.chain;
        if (chain === 1 || chain === 2) {
          ctx.strokeStyle = isDark
            ? `rgba(96, 165, 250, ${(avgAlpha * 0.68).toFixed(3)})`
            : `rgba(37, 99, 235, ${(avgAlpha * 0.58).toFixed(3)})`;
          ctx.lineWidth = 3.5 * avgScale;
        } else if (chain === 3 || chain === 4) {
          ctx.strokeStyle = isDark
            ? `rgba(45, 212, 191, ${(avgAlpha * 0.68).toFixed(3)})`
            : `rgba(8, 145, 178, ${(avgAlpha * 0.58).toFixed(3)})`;
          ctx.lineWidth = 2.9 * avgScale;
        } else {
          ctx.strokeStyle = isDark
            ? `rgba(129, 140, 248, ${(avgAlpha * 0.34).toFixed(3)})`
            : `rgba(79, 70, 229, ${(avgAlpha * 0.26).toFixed(3)})`;
          ctx.lineWidth = 1.6 * avgScale;
        }
        ctx.beginPath();
        ctx.moveTo(pa.sx, pa.sy);
        ctx.lineTo(pb.sx, pb.sy);
        ctx.stroke();
      }
    }

    // 7. 沿结合桥与碱基对流动的生物信号光子
    for (let i = 0; i < signals.length; i++) {
      const sig = signals[i]!;
      if (sig.mode !== mode) continue;
      const pa = projected[sig.from]!;
      const pb = projected[sig.to]!;
      const prog = (t * sig.speed + sig.offset) % 1;
      const sx = pa.sx + (pb.sx - pa.sx) * prog;
      const sy = pa.sy + (pb.sy - pa.sy) * prog;
      const scale = (pa.scale + pb.scale) * 0.5;
      ctx.fillStyle = isDark
        ? 'rgba(254, 240, 138, 0.92)'
        : 'rgba(245, 158, 11, 0.88)';
      ctx.beginPath();
      ctx.arc(sx, sy, 2.3 * scale, 0, Math.PI * 2);
      ctx.fill();
    }

    // 8. 画家算法：按 Z 深度从远到近绘制晶莹节点（变构波经过时顺序点亮）
    sortedIndices.sort((a, b) => projected[b]!.z - projected[a]!.z);

    for (let k = 0; k < sortedIndices.length; k++) {
      const idx = sortedIndices[k]!;
      const atom = atoms[idx]!;
      const p = projected[idx]!;
      const sprite = sprites[atom.palette];

      const waveHit =
        atom.chain <= 6
          ? Math.max(0, 1 - Math.abs(atom.prog - allostericWave) / 0.13)
          : 0;
      const waveBoost = 1 + waveHit * 0.24;
      const drawR = atom.radius * p.scale * waveBoost * 2.15;

      ctx.globalAlpha = Math.min(1, p.alpha);
      ctx.drawImage(sprite, p.sx - drawR, p.sy - drawR, drawR * 2, drawR * 2);
    }

    ctx.globalAlpha = 1;
    ctx.restore();

    rafId = requestAnimationFrame(renderFrame);
  };

  rafId = requestAnimationFrame(renderFrame);
});

onBeforeUnmount(() => {
  if (rafId) cancelAnimationFrame(rafId);
  if (autoTimer) window.clearInterval(autoTimer);
  ro?.disconnect();
  triggerModeSwitch = null;
});
</script>

<template>
  <div class="relative flex w-full max-w-[600px] flex-col items-center select-none">
    <canvas
      ref="canvasRef"
      class="aspect-[580/450] w-full transition-transform duration-300"
      :class="isDragging ? 'cursor-grabbing' : 'cursor-grab'"
    />

    <!-- 底部极简无字构象切换指示条（悬停提示三套机制，不与下方主标题抢视觉） -->
    <div class="mt-1 flex items-center gap-2.5">
      <button
        v-for="idx in [0, 1, 2]"
        :key="idx"
        type="button"
        class="h-1.5 cursor-pointer rounded-full transition-all duration-300"
        :class="
          activeMode === idx
            ? 'w-7 bg-primary shadow-xs'
            : 'w-2 bg-foreground/20 hover:bg-foreground/40'
        "
        :title="STAGE_TITLES[idx]"
        :aria-label="STAGE_TITLES[idx]"
        @click.stop="handleSelectMode(idx)"
      />
    </div>
  </div>
</template>
