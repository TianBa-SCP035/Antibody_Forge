/**
 * FACS 效价结论聚合：从板 positive_well_list 推导每鼠最高阳性稀释度（不落库）。
 * 以板槽位鼠号为主；鼠号按免疫方案匹配组别，未匹配归入「未分组小鼠」。
 */

export const FACS_DILUTION_EXPONENTS = [2, 3, 4, 5, 2, 3, 4, 5] as const
export const UNKNOWN_TARGET_KEY = '__unknown__'
export const UNKNOWN_TARGET_LABEL = '未知标靶'
export const UNGROUPED_GROUP_ID = '__ungrouped__'
export const UNGROUPED_GROUP_LABEL = '未分组小鼠'
export const EMPTY_STAGE_LABEL = '未填写阶段'

export type ConclusionCellValue = number | 'N/A' | '-'

export interface ConclusionRow {
  targetKey: string
  /** 种属 + 效价，如「人效价」；无种属时为空 */
  speciesTiterLabel: string
  targetName: string
  cells: Record<string, ConclusionCellValue>
}

export interface ConclusionGroupTable {
  groupId: string
  /** 组别展示名：与 FACS 板组别下拉一致（组别-鼠型） */
  groupDisplayLabel: string
  antigenLabel: string
  mouseColumns: string[]
  rows: ConclusionRow[]
}

export interface ConclusionMethodBlock {
  method: 'FACS' | 'ELISA'
  groupTables: ConclusionGroupTable[]
}

export interface ConclusionStageBlock {
  stageName: string
  methods: ConclusionMethodBlock[]
}

export interface FacsConclusionModel {
  stages: ConclusionStageBlock[]
  warnings: string[]
}

export interface BuildFacsConclusionInput {
  project: ProjectLike | null
  facsPlates: FacsPlateLike[]
}

interface ProjectLike {
  mouse_groups?: MouseGroupLike[]
  steps?: StepLike[]
  antigens?: AntigenLike[]
  titer_targets?: TiterTargetLike[]
}

interface MouseGroupLike {
  group_id?: string
  mouse_strain?: string
  sex?: string
  mouse_no_list?: string
  mouse_registry?: { mice?: Array<{ no?: string; sex?: string; alive?: boolean }> }
}

interface StepLike {
  group_id?: string
  stage_name?: string
  antigen_id?: string
}

interface AntigenLike {
  antigen_id?: string
  antigen_type?: string
}

interface TiterTargetLike {
  id?: number
  name?: string
  species?: string
}

export interface FacsPlateLike {
  id?: number | null
  tempId?: number | null
  immune_stage?: string | null
  cell_target_id?: number | null
  upper_group?: string | null
  lower_group?: string | null
  upper_mouse_list?: unknown
  lower_mouse_list?: unknown
  positive_well_list?: unknown
}

interface Observation {
  hasData: boolean
  maxExponent: number
  plateSortKey: number
}

type ObsMap = Map<string, Observation>

function normalizeMouseList(raw: unknown): string[] {
  const source = Array.isArray(raw) ? raw : []
  const out = new Array(12).fill('')
  for (let i = 0; i < Math.min(source.length, 12); i += 1) {
    const v = source[i]
    out[i] = v === undefined || v === null ? '' : String(v).trim()
  }
  if (source.length === 10) {
    return ['NC', ...out, 'PC']
  }
  if (out[0] === '' && out[11] === '') {
    out[0] = 'NC'
    out[11] = 'PC'
  }
  return out
}

function parseLegacyMouseTokens(str: string): string[] {
  const text = (str || '').trim()
  if (!text) return []
  const tokens: string[] = []
  const dual = text.split('，')
  for (const part of dual) {
    const m = part.match(/^[FM]：(.+)$/)
    if (m?.[1]) {
      m[1].split('、').forEach((t) => {
        const n = t.trim()
        if (n) tokens.push(n)
      })
    } else {
      part.split('、').forEach((t) => {
        const n = t.trim()
        if (n) tokens.push(n)
      })
    }
  }
  return tokens
}

function listMiceInGroup(group: MouseGroupLike): string[] {
  const registry = group.mouse_registry?.mice
  if (Array.isArray(registry) && registry.length) {
    return registry
      .filter((m) => m && m.alive !== false)
      .map((m) => String(m.no || '').trim())
      .filter(Boolean)
  }
  return parseLegacyMouseTokens(group.mouse_no_list || '')
}

/** 组别展示名对齐 FACS 板上下半组别：group_id + '-' + mouse_strain */
function buildGroupDisplayLabel(
  groupId: string,
  mouseGroups: MouseGroupLike[] | undefined,
  schemeGroupIds: Set<string>,
): string {
  if (groupId === UNGROUPED_GROUP_ID) return UNGROUPED_GROUP_LABEL
  if (!schemeGroupIds.has(groupId)) return groupId
  const strain = (mouseGroups || [])
    .find((g) => (g.group_id || '').trim() === groupId)
    ?.mouse_strain
  const s = (strain || '').trim()
  return s ? `${groupId}-${s}` : groupId
}

/** 鼠号 → 免疫方案组别（一只鼠只取首次匹配） */
export function buildMouseToGroupMap(mouseGroups: MouseGroupLike[] | undefined): Map<string, string> {
  const map = new Map<string, string>()
  for (const g of mouseGroups || []) {
    const groupId = (g.group_id || '').trim()
    if (!groupId) continue
    for (const no of listMiceInGroup(g)) {
      if (!map.has(no)) map.set(no, groupId)
    }
  }
  return map
}

/** 仅方案内组别展示抗原拼接；板字段回退分组不重复显示副标题 */
function resolveGroupAntigenLabel(
  groupId: string,
  steps: StepLike[] | undefined,
  antigens: AntigenLike[] | undefined,
  schemeGroupIds: Set<string>,
): string {
  if (groupId === UNGROUPED_GROUP_ID) return UNGROUPED_GROUP_LABEL
  if (!schemeGroupIds.has(groupId)) return ''
  return buildGroupAntigenLabel(groupId, steps, antigens)
}

export function buildGroupAntigenLabel(
  groupId: string,
  steps: StepLike[] | undefined,
  antigens: AntigenLike[] | undefined,
): string {
  if (groupId === UNGROUPED_GROUP_ID) return UNGROUPED_GROUP_LABEL
  const antigenById = new Map<string, AntigenLike>()
  for (const a of antigens || []) {
    const aid = (a.antigen_id || '').trim()
    if (aid) antigenById.set(aid, a)
  }
  const types = new Set<string>()
  for (const step of steps || []) {
    if ((step.group_id || '').trim() !== groupId) continue
    const raw = step.antigen_id
    if (!raw) continue
    for (const aid of String(raw).split(',').map((s) => s.trim()).filter(Boolean)) {
      const ag = antigenById.get(aid)
      const t = (ag?.antigen_type || '').trim()
      if (t) types.add(t)
    }
  }
  const joined = [...types].join('+')
  return joined || groupId
}

function resolveStage(plate: FacsPlateLike): string {
  const s = (plate.immune_stage || '').trim()
  return s || EMPTY_STAGE_LABEL
}

function targetKeyFromId(
  cellTargetId: number | null | undefined,
  targets: TiterTargetLike[] | undefined,
): string {
  if (cellTargetId == null) return UNKNOWN_TARGET_KEY
  const t = (targets || []).find((x) => x.id === cellTargetId)
  const name = (t?.name || '').trim()
  if (!name) return UNKNOWN_TARGET_KEY
  return name
}

function targetDisplayName(targetKey: string): string {
  return targetKey === UNKNOWN_TARGET_KEY ? UNKNOWN_TARGET_LABEL : targetKey
}

/** 靶标种属 →「人效价」；空白/未填则不展示 */
export function buildSpeciesTiterLabel(species: string | undefined | null): string {
  const s = (species || '').trim()
  if (!s || s === '空白') return ''
  return `${s}效价`
}

function rowTargetFields(
  targetKey: string,
  targets: TiterTargetLike[] | undefined,
): Pick<ConclusionRow, 'targetName' | 'speciesTiterLabel'> {
  if (targetKey === UNKNOWN_TARGET_KEY) {
    return { targetName: UNKNOWN_TARGET_LABEL, speciesTiterLabel: '' }
  }
  const t = (targets || []).find((x) => (x.name || '').trim() === targetKey)
  return {
    targetName: targetDisplayName(targetKey),
    speciesTiterLabel: buildSpeciesTiterLabel(t?.species),
  }
}

function wellCode(rowIndex: number, colIndex: number): string {
  return `${String.fromCharCode(65 + rowIndex)}${colIndex + 1}`
}

function maxPositiveExponent(
  positiveWells: Set<string>,
  rowStart: number,
  colIndex: number,
): number {
  let max = 0
  for (let r = rowStart; r < rowStart + 4; r += 1) {
    if (positiveWells.has(wellCode(r, colIndex))) {
      const exp = FACS_DILUTION_EXPONENTS[r] ?? 2
      if (exp > max) max = exp
    }
  }
  return max
}

function plateSortKey(plate: FacsPlateLike): number {
  if (plate.id != null) return Number(plate.id)
  return 1_000_000_000 + (Number(plate.tempId) || 0)
}

function obsKey(stage: string, groupId: string, targetKey: string, mouseNo: string): string {
  return `${stage}\0${groupId}\0${targetKey}\0${mouseNo}`
}

function setObservation(
  map: ObsMap,
  stage: string,
  groupId: string,
  targetKey: string,
  mouseNo: string,
  maxExponent: number,
  sortKey: number,
): void {
  if (!mouseNo) return
  const key = obsKey(stage, groupId, targetKey, mouseNo)
  const next: Observation = {
    hasData: true,
    maxExponent,
    plateSortKey: sortKey,
  }
  const prev = map.get(key)
  if (!prev || sortKey >= prev.plateSortKey) {
    map.set(key, next)
  }
}

/** 阶段 Tab 顺序：先按免疫方案步骤出现顺序，再按板数据首次出现的阶段补全 */
function buildStageAppearanceOrder(
  steps: StepLike[] | undefined,
  facsPlates: FacsPlateLike[],
): Map<string, number> {
  const order = new Map<string, number>()
  let idx = 0
  const add = (name: string) => {
    const n = (name || '').trim()
    if (!n || order.has(n)) return
    order.set(n, idx++)
  }
  for (const step of steps || []) {
    add(step.stage_name || '')
  }
  for (const plate of facsPlates || []) {
    add(resolveStage(plate))
  }
  return order
}

function plateHalfGroupLabel(plate: FacsPlateLike, section: 'upper' | 'lower'): string {
  const raw = section === 'upper' ? plate.upper_group : plate.lower_group
  return (raw || '').trim()
}

/**
 * 优先免疫方案鼠号表；未匹配时用该半板录入的 upper_group / lower_group 原文作分组（防遗漏）。
 */
function resolveGroupForMouse(
  mouseNo: string,
  mouseToGroup: Map<string, string>,
  plateHalfGroup: string,
): string {
  const fromScheme = mouseToGroup.get(mouseNo)
  if (fromScheme) return fromScheme
  if (plateHalfGroup) return plateHalfGroup
  return UNGROUPED_GROUP_ID
}

function processHalf(
  map: ObsMap,
  plate: FacsPlateLike,
  section: 'upper' | 'lower',
  stage: string,
  targetKey: string,
  sortKey: number,
  mouseToGroup: Map<string, string>,
): void {
  const mouseList = normalizeMouseList(
    section === 'upper' ? plate.upper_mouse_list : plate.lower_mouse_list,
  )
  const rowStart = section === 'upper' ? 0 : 4
  const halfGroup = plateHalfGroupLabel(plate, section)
  const positives = new Set(
    (Array.isArray(plate.positive_well_list) ? plate.positive_well_list : [])
      .filter((w): w is string => typeof w === 'string' && !!w.trim())
      .map((w) => w.trim().toUpperCase()),
  )

  for (let col = 0; col < 12; col += 1) {
    if (col === 0 || col === 11) continue
    const mouseNo = (mouseList[col] || '').trim()
    if (!mouseNo || /^NC$/i.test(mouseNo) || /^PC$/i.test(mouseNo)) continue
    const groupId = resolveGroupForMouse(mouseNo, mouseToGroup, halfGroup)
    const maxExp = maxPositiveExponent(positives, rowStart, col)
    setObservation(map, stage, groupId, targetKey, mouseNo, maxExp, sortKey)
  }
}

function sortMouseColumns(list: string[]): string[] {
  return [...list].sort((a, b) => {
    const na = Number(a)
    const nb = Number(b)
    if (!Number.isNaN(na) && !Number.isNaN(nb) && String(na) === a && String(nb) === b) {
      return na - nb
    }
    return a.localeCompare(b, undefined, { numeric: true })
  })
}

function sortGroupIds(a: string, b: string): number {
  if (a === UNGROUPED_GROUP_ID) return 1
  if (b === UNGROUPED_GROUP_ID) return -1
  return a.localeCompare(b, 'zh-CN')
}

function sortTargetKeys(a: string, b: string): number {
  const la = targetDisplayName(a)
  const lb = targetDisplayName(b)
  return la.localeCompare(lb, 'zh-CN')
}

function formatCellValue(obs: Observation | undefined): ConclusionCellValue {
  if (!obs?.hasData) return 'N/A'
  if (obs.maxExponent <= 0) return '-'
  return 10 ** obs.maxExponent
}

export function formatConclusionCell(value: ConclusionCellValue): string {
  if (value === 'N/A' || value === '-') return value
  return String(value)
}

/** 用于防抖刷新：仅当板数据实质变化时才重算 */
export function fingerprintFacsPlates(plates: FacsPlateLike[] | undefined): string {
  return (plates || [])
    .map((p) => {
      const pos = Array.isArray(p.positive_well_list)
        ? [...p.positive_well_list].map(String).sort().join(',')
        : ''
      return [
        p.id ?? '',
        p.tempId ?? '',
        p.immune_stage ?? '',
        p.cell_target_id ?? '',
        p.upper_group ?? '',
        p.lower_group ?? '',
        JSON.stringify(p.upper_mouse_list ?? []),
        JSON.stringify(p.lower_mouse_list ?? []),
        pos,
      ].join('|')
    })
    .join(';;')
}

export function buildFacsConclusionForPage(
  project: ProjectLike | null | undefined,
  titerTargets: TiterTargetLike[] | undefined,
  facsPlates: FacsPlateLike[],
): FacsConclusionModel {
  const targets = titerTargets ?? project?.titer_targets
  return buildFacsConclusion({
    project: project
      ? {
          mouse_groups: project.mouse_groups,
          steps: project.steps,
          antigens: project.antigens,
          titer_targets: targets,
        }
      : null,
    facsPlates: facsPlates || [],
  })
}

export function buildFacsConclusion(input: BuildFacsConclusionInput): FacsConclusionModel {
  const { project, facsPlates } = input
  const warnings: string[] = []
  const mouseGroups = project?.mouse_groups || []
  const steps = project?.steps || []
  const antigens = project?.antigens || []
  const targets = project?.titer_targets || []
  const mouseToGroup = buildMouseToGroupMap(mouseGroups)
  const stageOrder = buildStageAppearanceOrder(steps, facsPlates || [])
  const schemeGroupIds = new Set(
    mouseGroups.map((g) => (g.group_id || '').trim()).filter(Boolean),
  )

  const obsMap: ObsMap = new Map()
  let hasEmptyStagePlate = false

  for (const plate of facsPlates || []) {
    if (!(plate.immune_stage || '').trim()) hasEmptyStagePlate = true
    const stage = resolveStage(plate)
    const sortKey = plateSortKey(plate)
    const targetKey = targetKeyFromId(plate.cell_target_id, targets)
    processHalf(obsMap, plate, 'upper', stage, targetKey, sortKey, mouseToGroup)
    processHalf(obsMap, plate, 'lower', stage, targetKey, sortKey, mouseToGroup)
  }

  if (hasEmptyStagePlate) {
    warnings.push(`部分 FACS 板未填写免疫阶段，已归入「${EMPTY_STAGE_LABEL}」`)
  }

  const stageNames = [...new Set([...obsMap.keys()].map((k) => k.split('\0')[0]!))].sort(
    (a, b) => (stageOrder.get(a) ?? 0) - (stageOrder.get(b) ?? 0),
  )

  const stages: ConclusionStageBlock[] = stageNames.map((stageName) => {
    const groupIds = new Set<string>()
    for (const key of obsMap.keys()) {
      const [st, gid] = key.split('\0')
      if (st === stageName && gid) groupIds.add(gid)
    }

    const groupTables: ConclusionGroupTable[] = [...groupIds].sort(sortGroupIds).map((groupId) => {
      const targetKeys = new Set<string>()
      const miceSet = new Set<string>()
      for (const key of obsMap.keys()) {
        const [st, gid, tk, mouseNo] = key.split('\0')
        if (st !== stageName || gid !== groupId) continue
        if (tk) targetKeys.add(tk)
        if (mouseNo) miceSet.add(mouseNo)
      }

      const mouseColumns = sortMouseColumns([...miceSet])
      const rows: ConclusionRow[] = [...targetKeys].sort(sortTargetKeys).map((targetKey) => {
        const cells: Record<string, ConclusionCellValue> = {}
        for (const mouseNo of mouseColumns) {
          cells[mouseNo] = formatCellValue(obsMap.get(obsKey(stageName, groupId, targetKey, mouseNo)))
        }
        return {
          targetKey,
          ...rowTargetFields(targetKey, targets),
          cells,
        }
      })

      const antigenLabel = resolveGroupAntigenLabel(
        groupId,
        steps,
        antigens,
        schemeGroupIds,
      )

      return {
        groupId,
        groupDisplayLabel: buildGroupDisplayLabel(groupId, mouseGroups, schemeGroupIds),
        antigenLabel,
        mouseColumns,
        rows,
      }
    })

    return {
      stageName,
      methods: [
        {
          method: 'FACS' as const,
          groupTables,
        },
      ],
    }
  })

  return { stages, warnings: [...new Set(warnings)] }
}
