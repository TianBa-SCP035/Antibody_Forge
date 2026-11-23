export interface TargetStructureMeta {
  broadGroup: '跨膜蛋白' | '膜关联蛋白' | '分泌蛋白' | '胞内蛋白' | '其他';
  isSecreted: boolean;
  isTransmembrane: boolean;
  label: string;
  serumType: null | string;
}

export interface ParsedTargetStructure {
  broadGroup: null | string;
  fullLabel: null | string;
  isSecreted: boolean;
  isTransmembrane: boolean;
  label: null | string;
  raw: null | string;
  rawFeature: null | string;
  serumType: null | string;
  tmCount: null | number;
}

export const STRUCTURAL_PROPERTIES_MAP: Record<string, TargetStructureMeta> = {
  'Single-pass transmembrane protein Type I': {
    label: 'I型跨膜',
    serumType: 'I型',
    broadGroup: '跨膜蛋白',
    isTransmembrane: true,
    isSecreted: false,
  },
  'Single-pass transmembrane protein Type II': {
    label: 'II型跨膜',
    serumType: 'II型',
    broadGroup: '跨膜蛋白',
    isTransmembrane: true,
    isSecreted: false,
  },
  'Single-pass transmembrane protein Type III': {
    label: 'III型跨膜',
    serumType: 'III型',
    broadGroup: '跨膜蛋白',
    isTransmembrane: true,
    isSecreted: false,
  },
  'Single-pass transmembrane protein Type IV': {
    label: 'IV型跨膜',
    serumType: 'I型',
    broadGroup: '跨膜蛋白',
    isTransmembrane: true,
    isSecreted: false,
  },
  'Single-pass transmembrane protein': {
    label: '单次跨膜',
    serumType: 'I型',
    broadGroup: '跨膜蛋白',
    isTransmembrane: true,
    isSecreted: false,
  },
  'Multi-pass transmembrane protein': {
    label: '多次穿膜',
    serumType: '多穿',
    broadGroup: '跨膜蛋白',
    isTransmembrane: true,
    isSecreted: false,
  },
  Secreted: {
    label: '分泌型',
    serumType: '分泌',
    broadGroup: '分泌蛋白',
    isTransmembrane: false,
    isSecreted: true,
  },
  'Intracellular protein': {
    label: '胞内蛋白',
    serumType: '胞内',
    broadGroup: '胞内蛋白',
    isTransmembrane: false,
    isSecreted: false,
  },
  'GPI-anchored protein': {
    label: 'GPI锚定',
    serumType: 'GPI',
    broadGroup: '膜关联蛋白',
    isTransmembrane: false,
    isSecreted: false,
  },
  'Peripheral membrane protein': {
    label: '外周膜蛋白',
    serumType: '胞内',
    broadGroup: '膜关联蛋白',
    isTransmembrane: false,
    isSecreted: false,
  },
  'lipid-anchor protein': {
    label: '脂锚定蛋白',
    serumType: '胞内',
    broadGroup: '膜关联蛋白',
    isTransmembrane: false,
    isSecreted: false,
  },
  'Cell membrane protein': {
    label: '细胞膜蛋白',
    serumType: 'I型',
    broadGroup: '膜关联蛋白',
    isTransmembrane: false,
    isSecreted: false,
  },
  Other: {
    label: '其他',
    serumType: null,
    broadGroup: '其他',
    isTransmembrane: false,
    isSecreted: false,
  },
};

const PLACEHOLDER_SET = new Set([
  '',
  'NA',
  'N/A',
  'NONE',
  'NULL',
  '-',
  '—',
  'TBD',
  '未知',
  '末知',
  '无',
  '/',
]);

export function extractTransmembraneCount(
  structureFeature?: null | string,
): null | number {
  const raw = String(structureFeature || '').trim();
  if (!raw || PLACEHOLDER_SET.has(raw.toUpperCase())) return null;
  if (raw === '一次' || raw === '单次' || raw === '单次跨膜') return 1;
  const match = raw.match(/^(\d+)(?:\s*次(?:跨膜|穿膜)?(?:蛋白)?)?$/);
  if (match) {
    const count = Number(match[1]);
    return count > 0 ? count : null;
  }
  return null;
}

/**
 * 公共映射函数：将靶点库的英文 `structural_properties` 与 `structure_feature`（跨膜次数）
 * 解析为中文归类、完整展示文案、跨膜次数以及下游模块（如小鼠免疫）的二次映射枚举。
 */
export function parseTargetStructure(
  structuralProperties?: null | string,
  structureFeature?: null | string,
): ParsedTargetStructure {
  const raw = String(structuralProperties || '').trim() || null;
  const rawFeature = String(structureFeature || '').trim() || null;
  let tmCount = extractTransmembraneCount(rawFeature);

  const meta = raw ? STRUCTURAL_PROPERTIES_MAP[raw] : undefined;
  let label: null | string = null;
  let serumType: null | string = null;
  let broadGroup: null | string = null;
  let isTransmembrane = false;
  let isSecreted = false;

  if (meta) {
    label = meta.label;
    serumType = meta.serumType;
    broadGroup = meta.broadGroup;
    isTransmembrane = meta.isTransmembrane;
    isSecreted = meta.isSecreted;
    if (isTransmembrane && tmCount === null && raw?.startsWith('Single-pass')) {
      tmCount = 1;
    }
  } else if (tmCount !== null) {
    isTransmembrane = true;
    broadGroup = '跨膜蛋白';
    if (tmCount === 1) {
      label = '单次跨膜';
      serumType = 'I型';
    } else {
      label = '多次穿膜';
      serumType = '多穿';
    }
  } else if (
    rawFeature &&
    (rawFeature.includes('分泌') || rawFeature.toLowerCase() === 'secreted')
  ) {
    label = '分泌型';
    serumType = '分泌';
    broadGroup = '分泌蛋白';
    isSecreted = true;
  } else if (rawFeature && rawFeature.includes('胞内')) {
    label = '胞内蛋白';
    serumType = '胞内';
    broadGroup = '胞内蛋白';
  } else if (raw) {
    label = raw;
  }

  const fullLabel =
    label && tmCount && tmCount > 0 ? `${label}（${tmCount}次跨膜）` : label;

  return {
    raw,
    rawFeature,
    label,
    fullLabel,
    tmCount,
    serumType,
    broadGroup,
    isTransmembrane,
    isSecreted,
  };
}

export function formatTargetStructureLabel(
  structuralProperties?: null | string,
  structureFeature?: null | string,
  fallback = '未标注',
): string {
  const parsed = parseTargetStructure(structuralProperties, structureFeature);
  return parsed.fullLabel || parsed.label || fallback;
}

export function toSerumTargetType(
  structuralProperties?: null | string,
  structureFeature?: null | string,
): null | string {
  return parseTargetStructure(structuralProperties, structureFeature).serumType;
}

/**
 * 根据所选靶点编号列表（多选时以第 1 个靶点为准）推导免疫模块的 `target_type`。
 */
export function inferSerumTargetTypeFromOptions(
  codes?: null | string[],
  options: Array<{
    snum?: string;
    structural_properties?: null | string;
    structure_feature?: null | string;
  }> = [],
): null | string {
  const firstCode = Array.isArray(codes) ? codes[0] : null;
  if (!firstCode) return null;
  const item = (options || []).find((opt) => opt?.snum === firstCode);
  if (!item) return null;
  return toSerumTargetType(item.structural_properties, item.structure_feature);
}
