import { cleanFieldText } from '#/components/workbench/clipboardGrid'
import { WORKBENCH_PRIORITY_OPTIONS } from '#/utils/serumProjectStatus'
import { SERUM_MOUSE_STRAIN_OPTIONS } from '#/utils/serumMouseOptions'
import { WORKBENCH_STUDY_TYPE_OPTIONS } from '#/utils/workbenchStudyTypes'

export const STUDY_TYPE_OPTIONS = [...WORKBENCH_STUDY_TYPE_OPTIONS]
export const BUILD_PLATE = 'plate_single_cell'
export const BUILD_POOLED_BCR = 'pooled_bcr'
export const BUILD_POOLED_BARCODE = 'pooled_barcode'
export const BUILD_PLASMA_NGS = 'plasma_ngs'
export const BUILD_PHAGE_DISPLAY = 'phage_display'
export const BUILD_PHAGE_NGS = 'phage_ngs'
export const BUILD_PERIPHERAL_BLOOD = 'peripheral_blood_bcr'
export const INSTRUMENT_DATE_BUILDS = [BUILD_PLATE, BUILD_POOLED_BCR, BUILD_POOLED_BARCODE, BUILD_PHAGE_DISPLAY]
export const CELL_TYPE_CHOICE_BUILDS = [BUILD_PLASMA_NGS, BUILD_PHAGE_DISPLAY]
const BARCODE_BUILD_TYPES = new Set([BUILD_POOLED_BARCODE, BUILD_PHAGE_NGS, BUILD_PERIPHERAL_BLOOD])

export const BUILD_TYPE_OPTIONS = [
  { value: BUILD_PLATE, label: '单细胞孔板', hint: 'Beacon、达普打板的细胞恢复' },
  { value: BUILD_POOLED_BCR, label: '混管 H/K/L', hint: '达普打管，文库补 H/K/L 引物' },
  { value: BUILD_POOLED_BARCODE, label: '混管 Barcode', hint: '达普打管，文库补测序 Barcode' },
  { value: BUILD_PERIPHERAL_BLOOD, label: '外周血 BCR', hint: '外周血样品 BCR 扩增' },
  { value: BUILD_PLASMA_NGS, label: '浆细胞 NGS', hint: 'Nano、Lite 样品 NGS 建库' },
  { value: BUILD_PHAGE_DISPLAY, label: '噬菌体展示', hint: '用于展示筛选的噬菌体建库' },
  { value: BUILD_PHAGE_NGS, label: '噬菌体 NGS', hint: '展示筛选产物的 NGS 建库' },
]
export const STAT_TILES = BUILD_TYPE_OPTIONS.flatMap((item) => {
  if (item.value !== BUILD_PLASMA_NGS) return [{ ...item, statKey: item.value, sampleType: '' }]
  return [
    { ...item, statKey: 'plasma_ngs:nano', label: '浆细胞 Nano', hint: 'Nano 样品 NGS 建库', sampleType: 'nano' },
    { ...item, statKey: 'plasma_ngs:lite', label: '浆细胞 Lite', hint: 'Lite 样品 NGS 建库', sampleType: 'lite' },
  ]
})
export const TYPE_VALUES = BUILD_TYPE_OPTIONS.map((item) => item.value)

const BUILD_LABELS = Object.fromEntries(BUILD_TYPE_OPTIONS.map((item) => [item.value, item.label]))
export function buildTypeLabel(value) {
  return BUILD_LABELS[value] || value || ''
}
export function typeGroup(value) {
  return TYPE_VALUES.includes(value) ? value : ''
}

export const SAMPLE_SOURCE_OPTIONS = [
  { value: 'beacon', label: 'Beacon', builds: [BUILD_PLATE] },
  { value: 'dapu_plate', label: '达普打板', builds: [BUILD_PLATE] },
  { value: 'beacon_dapu', label: 'Beacon+达普打板', builds: [BUILD_PLATE] },
  { value: 'dapu_tube', label: '达普打管', builds: [BUILD_POOLED_BCR, BUILD_POOLED_BARCODE] },
  { value: 'direct', label: '细胞/核酸', builds: [BUILD_PHAGE_DISPLAY] },
  { value: 'phage_display', label: '噬菌体展示产物', builds: [BUILD_PHAGE_NGS] },
  { value: 'phage_panning', label: '噬菌体筛选产物', builds: [BUILD_PHAGE_NGS] },
  { value: 'retro_orbital_blood', label: '眼眶血', builds: [BUILD_PERIPHERAL_BLOOD] },
  { value: 'other_blood', label: '其他外周血', builds: [BUILD_PERIPHERAL_BLOOD] },
  { value: 'spleen_grind', label: '脾脏研磨', builds: [BUILD_PLASMA_NGS] },
]
export const SAMPLE_TYPE_OPTIONS = [
  { value: 'nano', label: 'Nano' },
  { value: 'lite', label: 'Lite' },
  { value: 'rnvm_blood', label: 'RNVM眼眶血' },
  { value: 'phage', label: '噬菌体' },
]
export const PLASMA_SAMPLE_TYPE_OPTIONS = SAMPLE_TYPE_OPTIONS.filter((item) => item.value === 'nano' || item.value === 'lite')
export const PHAGE_EXPERIMENT_TYPE_OPTIONS = ['抗体发现', '亲和力改造']
export const INDEX_MODE_OPTIONS = [
  { value: 'none', label: '不加 Barcode' },
  { value: 'single_i7', label: 'i7' },
  { value: 'single_i5', label: 'i5' },
  { value: 'dual', label: '双端 i7 + i5' },
]
export const TARGET_FORM_OPTIONS = ['多穿', '分泌', 'I型', 'II型']
export const STATUS_OPTIONS = ['待处理', '建库中', '待质检', '质检待确认', '质检通过', '已完成', '质检不通过', '已取消']
export const PRIORITY_OPTIONS = [...WORKBENCH_PRIORITY_OPTIONS]
export const QC_RESULT_OPTIONS = ['待判定', '通过', '不通过']
export const REQUIRED_CHOICE_KEYS = ['build_type', 'status', 'priority']
export const CELL_TYPE_OPTIONS = ['全细胞', '浆细胞', '流穿液']

export const SYNC_TEXT_KEYS = new Set(['positive_cell_count', 'fragment_size_bp'])

export function isSyncedText(field) {
  return SYNC_TEXT_KEYS.has(field?.key)
}

export function persistValue(value) {
  if (Array.isArray(value)) return value
  if (value == null || (typeof value === 'string' && !value.trim())) return null
  return value
}

export function syncPairedTextareas(selector) {
  const nodes = [...document.querySelectorAll(selector)].filter((node) => node.getClientRects().length)
  if (!nodes.length) return
  nodes.forEach((node) => { node.style.height = 'auto' })
  const height = Math.max(...nodes.map((node) => node.scrollHeight))
  nodes.forEach((node) => { node.style.height = `${height}px` })
}

export function stampQcFields(row, ownerName) {
  if (!row?.qc_result) return []
  const fields = []
  if (!row.qc_owner && ownerName) {
    row.qc_owner = ownerName
    fields.push('qc_owner')
  }
  if (!row.qc_on) {
    const now = new Date()
    const month = String(now.getMonth() + 1).padStart(2, '0')
    const day = String(now.getDate()).padStart(2, '0')
    row.qc_on = `${now.getFullYear()}-${month}-${day}`
    fields.push('qc_on')
  }
  return fields
}

export function statusTone(status) {
  if (status === '已完成' || status === '质检通过') return 'success'
  if (status === '质检不通过' || status === '已取消') return 'danger'
  if (status === '建库中' || status === '待质检') return 'primary'
  if (status === '质检待确认') return 'warning'
  return 'info'
}

export const MOUSE_STRAIN_OPTIONS = [...SERUM_MOUSE_STRAIN_OPTIONS]

export function splitMouseStrain(value) {
  const tokens = Array.isArray(value) ? value : String(value || '').split(/[,，、+]/)
  const seen = new Set()
  const out = []
  for (const item of tokens) {
    const text = String(item || '').trim()
    if (!text || seen.has(text)) continue
    seen.add(text)
    out.push(text)
  }
  return out
}

export function joinMouseStrain(value) {
  const tokens = splitMouseStrain(value)
  const known = new Set(MOUSE_STRAIN_OPTIONS)
  const ordered = MOUSE_STRAIN_OPTIONS.filter((item) => tokens.includes(item))
  const extras = tokens.filter((item) => !known.has(item))
  return [...ordered, ...extras].join('、')
}

export function sampleSourceLabel(value) {
  return SAMPLE_SOURCE_OPTIONS.find((item) => item.value === value)?.label || value || ''
}
export function sampleTypeLabel(value) {
  return SAMPLE_TYPE_OPTIONS.find((item) => item.value === value)?.label || value || ''
}
export function indexModeLabel(value) {
  return INDEX_MODE_OPTIONS.find((item) => item.value === value)?.label || value || ''
}
export function optionsForBuild(options, buildType) {
  return options.filter((item) => !item.builds || item.builds.includes(buildType))
}

export const HANDOFF_METHOD_ROWS = [
  {
    method: '达普',
    tone: 'primary',
    picks: [
      { id: 'dapu-plate', buildType: BUILD_PLATE, source: 'dapu_plate', label: '单细胞孔板' },
      { id: 'dapu-tube', buildType: BUILD_POOLED_BCR, source: 'dapu_tube', label: '混管 H/K/L' },
      { id: 'dapu-tube-barcode', buildType: BUILD_POOLED_BARCODE, source: 'dapu_tube', label: '混管 Barcode' },
    ],
  },
  {
    method: 'Beacon',
    tone: 'success',
    picks: [
      { id: 'beacon-plate', buildType: BUILD_PLATE, source: 'beacon', label: '单细胞孔板' },
      {
        id: 'both-plate',
        buildType: BUILD_PLATE,
        source: 'beacon_dapu',
        label: 'Beacon+达普打板',
        hint: 'Beacon 与达普打在同一块板上',
      },
    ],
  },
  {
    method: '噬菌体',
    tone: 'warning',
    picks: [
      { id: 'phage-display', buildType: BUILD_PHAGE_DISPLAY, source: 'direct', label: '噬菌体展示', hint: '从细胞或核酸构建展示文库' },
      {
        id: 'phage-ngs',
        buildType: BUILD_PHAGE_NGS,
        source: 'phage_panning',
        label: '噬菌体测序',
        hint: '展示筛选之后的结果，建成可上 NGS 的文库',
      },
    ],
  },
  {
    method: 'NGS',
    tone: 'purple',
    picks: [
      { id: 'blood-retro', buildType: BUILD_PERIPHERAL_BLOOD, source: 'retro_orbital_blood', label: '眼眶血' },
      { id: 'blood-other', buildType: BUILD_PERIPHERAL_BLOOD, source: 'other_blood', label: '其他外周血' },
      { id: 'plasma-nano', buildType: BUILD_PLASMA_NGS, source: 'spleen_grind', sampleType: 'nano', label: '浆细胞 Nano' },
      { id: 'plasma-lite', buildType: BUILD_PLASMA_NGS, source: 'spleen_grind', sampleType: 'lite', label: '浆细胞 Lite' },
    ],
  },
]
export function normalizePlateInputText(value) {
  return cleanFieldText(value, { keepBreaks: true }).replace(/[，,、\t]+/g, '\n')
}
export function plateNumbersFromText(value) {
  return [...new Set(normalizePlateInputText(value).split('\n').map((item) => item.trim()).filter(Boolean))]
}
export function plateNumbersText(values) {
  return (Array.isArray(values) ? values : []).map((item) => String(item || '').trim()).filter(Boolean).join('\n')
}

const COMMON_IDENTITY = [
  { key: 'library_code', label: '建库编号' },
  { key: 'build_type', label: '建库类型', type: 'select', options: BUILD_TYPE_OPTIONS },
  { key: 'source_project_code', label: '项目编号' },
  { key: 'study_type', label: '课题类型', type: 'select', options: STUDY_TYPE_OPTIONS },
  { key: 'pm', label: 'PM', type: 'user' },
  { key: 'notebook_no', label: '实验记录本号' },
  { key: 'target_name', label: '靶点', type: 'target', wide: true },
  { key: 'mouse_strain', label: '小鼠品系', type: 'select', options: MOUSE_STRAIN_OPTIONS.map((item) => ({ value: item, label: item })) },
  { key: 'sample_type', label: '样品类型', type: 'select', options: SAMPLE_TYPE_OPTIONS },
]
const COMMON_SOURCE = [
  { key: 'sample_source', label: '样品来源', type: 'source-select' },
  { key: 'received_on', label: '交接日期', type: 'date' },
]
const COMMON_SCHEDULE = [
  { key: 'status', label: '状态', type: 'select', options: STATUS_OPTIONS },
  { key: 'priority', label: '优先级', type: 'select', options: PRIORITY_OPTIONS },
  { key: 'owner', label: '负责人', type: 'user' },
  { key: 'started_at', label: '开始时间', type: 'date' },
  { key: 'finished_at', label: '完成时间', type: 'date' },
  { key: 'source_discovery_id', label: '来源发现 ID', type: 'source-link' },
  { key: 'remark', label: '备注', type: 'textarea', wide: true },
]
export const PRIMER_ROWS = [
  {
    chain: 'H',
    forward: { key: 'h_forward_primer_name', catalogIdKey: 'h_forward_primer_id' },
    reverse: { key: 'h_reverse_primer_name', catalogIdKey: 'h_reverse_primer_id' },
    concentrationKey: 'h_primer_concentration',
  },
  {
    chain: 'K',
    forward: { key: 'k_forward_primer_name', catalogIdKey: 'k_forward_primer_id' },
    reverse: { key: 'k_reverse_primer_name', catalogIdKey: 'k_reverse_primer_id' },
    concentrationKey: 'k_primer_concentration',
  },
  {
    chain: 'L',
    forward: { key: 'l_forward_primer_name', catalogIdKey: 'l_forward_primer_id' },
    reverse: { key: 'l_reverse_primer_name', catalogIdKey: 'l_reverse_primer_id' },
    concentrationKey: 'l_primer_concentration',
  },
]
const PRIMER_MATRIX = [{ key: 'primer_matrix', label: '', type: 'primer-matrix', rows: PRIMER_ROWS, wide: true }]
export const CATALOG_NAME_FIELDS = {
  h_forward_primer_name: { idKey: 'h_forward_primer_id' },
  h_reverse_primer_name: { idKey: 'h_reverse_primer_id' },
  k_forward_primer_name: { idKey: 'k_forward_primer_id' },
  k_reverse_primer_name: { idKey: 'k_reverse_primer_id' },
  l_forward_primer_name: { idKey: 'l_forward_primer_id' },
  l_reverse_primer_name: { idKey: 'l_reverse_primer_id' },
  i7_name: { idKey: 'i7_catalog_id', sequenceKey: 'i7_sequence' },
  i5_name: { idKey: 'i5_catalog_id', sequenceKey: 'i5_sequence' },
}
const INDEX_FIELDS = [
  { key: 'index_mode', label: 'Barcode 方式', type: 'select', options: INDEX_MODE_OPTIONS, rowBreak: true },
  { key: 'i7_name', label: 'i7 名称', type: 'catalog-select', catalogIdKey: 'i7_catalog_id', sequenceKey: 'i7_sequence' },
  { key: 'i7_sequence', label: 'i7 序列' },
  { key: 'i5_name', label: 'i5 名称', type: 'catalog-select', catalogIdKey: 'i5_catalog_id', sequenceKey: 'i5_sequence' },
  { key: 'i5_sequence', label: 'i5 序列' },
]
function visibleIndexFields(order = {}) {
  const fields = [INDEX_FIELDS[0]]
  if (['single_i7', 'dual'].includes(order.index_mode)) fields.push(...INDEX_FIELDS.slice(1, 3))
  if (['single_i5', 'dual'].includes(order.index_mode)) fields.push(...INDEX_FIELDS.slice(3, 5))
  return fields
}
const INDEX_KEY_MODES = {
  i7_name: ['single_i7', 'dual'],
  i7_sequence: ['single_i7', 'dual'],
  i5_name: ['single_i5', 'dual'],
  i5_sequence: ['single_i5', 'dual'],
}
export function isIndexFieldRecorded(buildType, indexMode, key) {
  const modes = INDEX_KEY_MODES[key]
  if (!modes) return true
  return BARCODE_BUILD_TYPES.has(buildType) && modes.includes(indexMode)
}
const QC_FIELDS = [
  { key: 'qc_result', label: '质检结论', type: 'select', options: QC_RESULT_OPTIONS },
  { key: 'qc_owner', label: '质检人', type: 'user' },
  { key: 'qc_on', label: '质检日期', type: 'date' },
  { key: 'qc_note', label: '质检说明', type: 'textarea', wide: true },
]

const TUBE_MATERIAL_FIELDS = [
  { key: 'instrument_on', label: '上机日期', type: 'date', rowBreak: true },
  { key: 'positive_cell_count', label: '阳性细胞数' },
  { key: 'fragment_size_bp', label: '片段大小' },
  { key: 'rna_location', label: 'RNA 位置', rowBreak: true },
  { key: 'cdna_location', label: 'cDNA 位置' },
  { key: 'cdna_concentration', label: 'cDNA 浓度' },
  { key: 'library_location', label: '文库位置' },
  { key: 'library_concentration', label: '文库浓度' },
]
const PROFILE_SECTIONS = {
  [BUILD_PLATE]: [
    {
      title: '孔板样品',
      fields: [
        { key: 'instrument_on', label: '上机日期', type: 'date', rowBreak: true },
        { key: 'positive_cell_count', label: '阳性细胞数' },
        { key: 'cdna_location', label: 'cDNA 位置' },
        { key: 'plate_nos', label: '板号', type: 'plate-list', wide: true },
      ],
    },
  ],
  [BUILD_POOLED_BCR]: [
    { title: '混管与材料', fields: TUBE_MATERIAL_FIELDS },
    { title: 'H / K / L 引物', fields: PRIMER_MATRIX },
  ],
  [BUILD_POOLED_BARCODE]: [
    { title: '混管与材料', fields: TUBE_MATERIAL_FIELDS },
  ],
  [BUILD_PLASMA_NGS]: [
    {
      title: '浆细胞材料',
      fields: [
        { key: 'instrument_on', label: '上机日期', type: 'date', rowBreak: true },
        { key: 'positive_cell_count', label: '阳性细胞数' },
        { key: 'fragment_size_bp', label: '片段大小' },
        { key: 'cell_type', label: '细胞类型', type: 'select', options: CELL_TYPE_OPTIONS, rowBreak: true },
        { key: 'rna_location', label: 'RNA 位置' },
        { key: 'cdna_location', label: 'cDNA 位置' },
        { key: 'library_location', label: '文库位置' },
        { key: 'library_concentration', label: '文库浓度' },
      ],
    },
  ],
  [BUILD_PHAGE_DISPLAY]: [
    {
      title: '展示文库',
      fields: [
        { key: 'source_experiment_type', label: '实验类型', type: 'select', options: PHAGE_EXPERIMENT_TYPE_OPTIONS },
        { key: 'project_goal', label: '实验目标', type: 'textarea', wide: true },
        { key: 'instrument_on', label: '上机日期', type: 'date', rowBreak: true },
        { key: 'library_batch_no', label: '建库批号' },
        { key: 'target_forms', label: '靶点形式', type: 'select', options: TARGET_FORM_OPTIONS },
        { key: 'initial_library_size', label: '初始库容' },
        { key: 'effective_library_size', label: '有效库容' },
        { key: 'cell_type', label: '细胞类型', type: 'select', options: CELL_TYPE_OPTIONS },
        { key: 'rna_location', label: 'RNA 位置' },
        { key: 'cdna_location', label: 'cDNA 位置' },
        { key: 'library_location', label: '文库位置' },
      ],
    },
  ],
  [BUILD_PHAGE_NGS]: [
    {
      title: '噬菌体样品',
      fields: [
        { key: 'source_experiment_type', label: '实验类型', type: 'select', options: PHAGE_EXPERIMENT_TYPE_OPTIONS },
        { key: 'project_goal', label: '实验目标', type: 'textarea', wide: true },
        { key: 'library_batch_no', label: '建库批号' },
        { key: 'fragment_size_bp', label: '片段大小' },
        { key: 'library_location', label: '文库位置' },
        { key: 'library_concentration', label: '文库浓度' },
      ],
    },
  ],
  [BUILD_PERIPHERAL_BLOOD]: [
    {
      title: '外周血样品',
      fields: [
        { key: 'blood_collected_on', label: '采血日期', type: 'date' },
        { key: 'immunization_stage', label: '免疫阶段' },
        { key: 'positive_cell_count', label: '阳性细胞数' },
        { key: 'fragment_size_bp', label: '片段大小' },
        { key: 'rna_location', label: 'RNA 位置', rowBreak: true },
        { key: 'cdna_location', label: 'cDNA 位置' },
        { key: 'cdna_concentration', label: 'cDNA 浓度' },
        { key: 'library_location', label: '文库位置' },
        { key: 'library_concentration', label: '文库浓度' },
      ],
    },
  ],
}

function identityFields(buildType) {
  if (buildType !== BUILD_PLASMA_NGS) return COMMON_IDENTITY
  return COMMON_IDENTITY.map((field) => (
    field.key === 'sample_type' ? { ...field, options: PLASMA_SAMPLE_TYPE_OPTIONS } : field
  ))
}
export function orderEditorSections(buildType, order = {}) {
  const barcodeSections = BARCODE_BUILD_TYPES.has(buildType)
    ? [{ title: 'Barcode', fields: visibleIndexFields(order) }]
    : []
  return [
    { title: '工单安排', queue: true, fields: COMMON_SCHEDULE },
    { title: '基本信息', fields: identityFields(buildType) },
    { title: '样品交接', fields: COMMON_SOURCE },
    ...(PROFILE_SECTIONS[buildType] || []),
    ...barcodeSections,
    { title: '质控结果', fields: QC_FIELDS },
  ]
}

function def(key, label, edit = 'text', minWidth = 120) {
  return { key, label, edit, minWidth }
}

export const FIELD_DEFS = {
  library_order_id: def('library_order_id', '系统工单号', 'readonly', 170),
  source_discovery_id: def('source_discovery_id', '来源发现 ID', 'readonly', 160),
  library_code: def('library_code', '建库编号', 'text', 120),
  build_type: def('build_type', '建库类型', 'select', 150),
  sample_source: def('sample_source', '样品来源', 'select', 140),
  source_project_code: def('source_project_code', '项目编号', 'text', 120),
  study_type: def('study_type', '课题类型', 'select'),
  source_experiment_type: def('source_experiment_type', '实验类型', 'select'),
  project_goal: def('project_goal', '实验目标', 'text', 180),
  target_name: def('target_name', '靶点', 'target'),
  target_codes: def('target_codes', '靶点编号', 'target', 140),
  pm: def('pm', 'PM', 'select', 100),
  mouse_strain: def('mouse_strain', '小鼠品系', 'select'),
  sample_type: def('sample_type', '样品类型', 'select'),
  received_on: def('received_on', '交接日期', 'date', 130),
  instrument_on: def('instrument_on', '上机日期', 'date', 130),
  blood_collected_on: def('blood_collected_on', '采血日期', 'date', 130),
  positive_cell_count: def('positive_cell_count', '阳性细胞数'),
  plate_nos: def('plate_nos', '板号', 'text', 150),
  target_forms: def('target_forms', '靶点形式', 'select', 150),
  status: def('status', '状态', 'select', 110),
  priority: def('priority', '优先级', 'select', 110),
  owner: def('owner', '负责人', 'select', 110),
  started_at: def('started_at', '开始时间', 'date', 130),
  finished_at: def('finished_at', '完成时间', 'date', 130),
  cell_type: def('cell_type', '细胞类型', 'select'),
  notebook_no: def('notebook_no', '实验记录本号'),
  immunization_stage: def('immunization_stage', '免疫阶段'),
  library_batch_no: def('library_batch_no', '建库批号'),
  rna_location: def('rna_location', 'RNA 位置', 'text', 140),
  cdna_location: def('cdna_location', 'cDNA 位置', 'text', 140),
  library_location: def('library_location', '文库位置', 'text', 140),
  cdna_concentration: def('cdna_concentration', 'cDNA 浓度'),
  library_concentration: def('library_concentration', '文库浓度'),
  initial_library_size: def('initial_library_size', '初始库容'),
  effective_library_size: def('effective_library_size', '有效库容'),
  fragment_size_bp: def('fragment_size_bp', '片段大小'),
  h_forward_primer_name: def('h_forward_primer_name', 'H 正向引物', 'catalog', 150),
  h_reverse_primer_name: def('h_reverse_primer_name', 'H 反向引物', 'catalog', 150),
  h_primer_concentration: def('h_primer_concentration', 'H 浓度'),
  k_forward_primer_name: def('k_forward_primer_name', 'K 正向引物', 'catalog', 150),
  k_reverse_primer_name: def('k_reverse_primer_name', 'K 反向引物', 'catalog', 150),
  k_primer_concentration: def('k_primer_concentration', 'K 浓度'),
  l_forward_primer_name: def('l_forward_primer_name', 'L 正向引物', 'catalog', 150),
  l_reverse_primer_name: def('l_reverse_primer_name', 'L 反向引物', 'catalog', 150),
  l_primer_concentration: def('l_primer_concentration', 'L 浓度'),
  index_mode: def('index_mode', 'Barcode 方式', 'select'),
  i7_name: def('i7_name', 'i7 名称', 'catalog', 150),
  i7_sequence: def('i7_sequence', 'i7 序列', 'text', 150),
  i5_name: def('i5_name', 'i5 名称', 'catalog', 150),
  i5_sequence: def('i5_sequence', 'i5 序列', 'text', 150),
  qc_result: def('qc_result', '质检结论', 'select'),
  qc_owner: def('qc_owner', '质检人', 'select'),
  qc_on: def('qc_on', '质检日期', 'date', 130),
  qc_note: def('qc_note', '质检说明', 'text', 180),
  remark: def('remark', '备注', 'text', 180),
}

const SHEET_IDENTITY_KEYS = [
  'library_order_id',
  'source_discovery_id',
  'source_project_code',
  'target_name',
  'target_codes',
  'study_type',
  'pm',
  'mouse_strain',
  'sample_type',
  'build_type',
  'sample_source',
  'library_code',
  'notebook_no',
]
const SHEET_SCHEDULE_KEYS = [
  'status',
  'priority',
  'owner',
  'started_at',
  'finished_at',
  'received_on',
]
const SHEET_QC_KEYS = [
  'qc_result',
  'qc_owner',
  'qc_on',
  'qc_note',
  'remark',
]
const COMMON_SHEET_KEYS = [
  ...SHEET_IDENTITY_KEYS,
  ...SHEET_SCHEDULE_KEYS,
  ...SHEET_QC_KEYS,
]
const INDEX_SHEET_KEYS = ['index_mode', 'i7_name', 'i7_sequence', 'i5_name', 'i5_sequence']
const PROFILE_SHEET_KEYS = {
  [BUILD_PLATE]: [
    'instrument_on',
    'positive_cell_count',
    'cdna_location',
    'plate_nos',
  ],
  [BUILD_POOLED_BCR]: [
    'instrument_on',
    'positive_cell_count',
    'cdna_concentration',
    'library_concentration',
    'fragment_size_bp',
    'rna_location',
    'cdna_location',
    'library_location',
    'h_forward_primer_name',
    'h_reverse_primer_name',
    'h_primer_concentration',
    'k_forward_primer_name',
    'k_reverse_primer_name',
    'k_primer_concentration',
    'l_forward_primer_name',
    'l_reverse_primer_name',
    'l_primer_concentration',
  ],
  [BUILD_POOLED_BARCODE]: [
    'instrument_on',
    'positive_cell_count',
    'cdna_concentration',
    'library_concentration',
    'fragment_size_bp',
    'rna_location',
    'cdna_location',
    'library_location',
    ...INDEX_SHEET_KEYS,
  ],
  [BUILD_PLASMA_NGS]: [
    'instrument_on',
    'positive_cell_count',
    'cell_type',
    'rna_location',
    'cdna_location',
    'library_location',
    'library_concentration',
    'fragment_size_bp',
  ],
  [BUILD_PHAGE_DISPLAY]: [
    'source_experiment_type',
    'project_goal',
    'instrument_on',
    'library_batch_no',
    'cell_type',
    'target_forms',
    'initial_library_size',
    'effective_library_size',
    'rna_location',
    'cdna_location',
    'library_location',
  ],
  [BUILD_PHAGE_NGS]: [
    'source_experiment_type',
    'project_goal',
    'library_batch_no',
    'fragment_size_bp',
    'library_concentration',
    'library_location',
    ...INDEX_SHEET_KEYS,
  ],
  [BUILD_PERIPHERAL_BLOOD]: [
    'blood_collected_on',
    'immunization_stage',
    'positive_cell_count',
    'cdna_concentration',
    'library_concentration',
    'fragment_size_bp',
    'rna_location',
    'cdna_location',
    'library_location',
    ...INDEX_SHEET_KEYS,
  ],
}
const SHEET_KEYS = [
  ...SHEET_IDENTITY_KEYS,
  ...SHEET_SCHEDULE_KEYS,
  'instrument_on',
  'blood_collected_on',
  'positive_cell_count',
  'plate_nos',
  'cell_type',
  'immunization_stage',
  'target_forms',
  'source_experiment_type',
  'project_goal',
  'library_batch_no',
  'rna_location',
  'cdna_location',
  'library_location',
  'cdna_concentration',
  'library_concentration',
  'initial_library_size',
  'effective_library_size',
  'fragment_size_bp',
  'h_forward_primer_name',
  'h_reverse_primer_name',
  'h_primer_concentration',
  'k_forward_primer_name',
  'k_reverse_primer_name',
  'k_primer_concentration',
  'l_forward_primer_name',
  'l_reverse_primer_name',
  'l_primer_concentration',
  'index_mode',
  'i7_name',
  'i7_sequence',
  'i5_name',
  'i5_sequence',
  ...SHEET_QC_KEYS,
]
export function allSheetColumns() {
  return SHEET_KEYS.map((key) => ({ ...FIELD_DEFS[key] })).filter((item) => item.key)
}
export function sheetColumnsForBuild(buildType) {
  if (!PROFILE_SHEET_KEYS[buildType]) return allSheetColumns()
  const visible = new Set([...COMMON_SHEET_KEYS, ...PROFILE_SHEET_KEYS[buildType]])
  return SHEET_KEYS.filter((key) => visible.has(key)).map((key) => ({ ...FIELD_DEFS[key] }))
}

export function isSheetFieldApplicable(buildType, key) {
  if (!PROFILE_SHEET_KEYS[buildType]) return true
  return COMMON_SHEET_KEYS.includes(key) || PROFILE_SHEET_KEYS[buildType].includes(key)
}

export const WORKBENCH_COLUMNS = [
  { key: 'source_project_code', label: '项目编号', prop: 'source_project_code', minWidth: 130, defaultVisible: true, showOverflowTooltip: true },
  { key: 'target_name', label: '靶点', prop: 'target_name', minWidth: 150, defaultVisible: true, showOverflowTooltip: true },
  { key: 'build_type', label: '建库类型', prop: 'build_type', minWidth: 150, defaultVisible: true, showOverflowTooltip: true },
  { key: 'sample_source', label: '样品来源', minWidth: 130, defaultVisible: true, showOverflowTooltip: true },
  { key: 'sample_type', label: '样品类型', minWidth: 110, defaultVisible: true, showOverflowTooltip: true },
  { key: 'library_code', label: '建库编号', prop: 'library_code', minWidth: 120, defaultVisible: true, showOverflowTooltip: true },
  { key: 'owner', label: '负责人', prop: 'owner', minWidth: 100, defaultVisible: true, showOverflowTooltip: true },
  { key: 'status', label: '状态', minWidth: 110, defaultVisible: true, className: 'status-column-cell' },
  { key: 'priority', label: '优先级', minWidth: 112, defaultVisible: true },
  { key: 'mouse_strain', label: '小鼠品系', minWidth: 110, defaultVisible: false, showOverflowTooltip: true },
  { key: 'study_type', label: '课题类型', minWidth: 120, defaultVisible: false, showOverflowTooltip: true },
  { key: 'pm', label: 'PM', minWidth: 100, defaultVisible: false, showOverflowTooltip: true },
  { key: 'source_discovery_id', label: '来源发现 ID', minWidth: 160, defaultVisible: false, showOverflowTooltip: true },
  { key: 'notebook_no', label: '实验记录本号', minWidth: 140, defaultVisible: false, showOverflowTooltip: true },
  { key: 'received_on', label: '交接日期', minWidth: 130, defaultVisible: false, className: 'date-column-cell' },
  { key: 'instrument_on', label: '上机日期', minWidth: 130, defaultVisible: false },
  { key: 'started_at', label: '开始时间', minWidth: 130, defaultVisible: false, showOverflowTooltip: true },
  { key: 'finished_at', label: '完成时间', minWidth: 130, defaultVisible: false, showOverflowTooltip: true },
  { key: 'qc_result', label: '质检结论', minWidth: 110, defaultVisible: false },
  { key: 'qc_on', label: '质检日期', minWidth: 130, defaultVisible: false },
  { key: 'library_order_id', label: '系统工单号', minWidth: 170, defaultVisible: false, showOverflowTooltip: true },
  { key: 'target_codes', label: '靶点编号', minWidth: 140, defaultVisible: false, showOverflowTooltip: true },
  { key: 'blood_collected_on', label: '采血日期', minWidth: 130, defaultVisible: false, className: 'date-column-cell' },
  { key: 'positive_cell_count', label: '阳性细胞数', minWidth: 120, defaultVisible: false, showOverflowTooltip: true, keepLineBreaks: true },
  { key: 'plate_nos', label: '板号', minWidth: 150, defaultVisible: false, showOverflowTooltip: true },
  { key: 'cell_type', label: '细胞类型', minWidth: 120, defaultVisible: false, showOverflowTooltip: true },
  { key: 'immunization_stage', label: '免疫阶段', minWidth: 120, defaultVisible: false, showOverflowTooltip: true },
  { key: 'target_forms', label: '靶点形式', minWidth: 150, defaultVisible: false, showOverflowTooltip: true },
  { key: 'source_experiment_type', label: '实验类型', minWidth: 120, defaultVisible: false, showOverflowTooltip: true },
  { key: 'project_goal', label: '实验目标', minWidth: 180, defaultVisible: false, showOverflowTooltip: true, keepLineBreaks: true },
  { key: 'library_batch_no', label: '建库批号', minWidth: 130, defaultVisible: false, showOverflowTooltip: true },
  { key: 'rna_location', label: 'RNA 位置', minWidth: 140, defaultVisible: false, showOverflowTooltip: true },
  { key: 'cdna_location', label: 'cDNA 位置', minWidth: 140, defaultVisible: false, showOverflowTooltip: true },
  { key: 'library_location', label: '文库位置', minWidth: 140, defaultVisible: false, showOverflowTooltip: true },
  { key: 'cdna_concentration', label: 'cDNA 浓度', minWidth: 120, defaultVisible: false },
  { key: 'library_concentration', label: '文库浓度', minWidth: 120, defaultVisible: false },
  { key: 'initial_library_size', label: '初始库容', minWidth: 120, defaultVisible: false },
  { key: 'effective_library_size', label: '有效库容', minWidth: 120, defaultVisible: false },
  { key: 'fragment_size_bp', label: '片段大小', minWidth: 120, defaultVisible: false, showOverflowTooltip: true, keepLineBreaks: true },
  { key: 'h_forward_primer_name', label: 'H 正向引物', minWidth: 150, defaultVisible: false, showOverflowTooltip: true },
  { key: 'h_reverse_primer_name', label: 'H 反向引物', minWidth: 150, defaultVisible: false, showOverflowTooltip: true },
  { key: 'h_primer_concentration', label: 'H 浓度', minWidth: 120, defaultVisible: false },
  { key: 'k_forward_primer_name', label: 'K 正向引物', minWidth: 150, defaultVisible: false, showOverflowTooltip: true },
  { key: 'k_reverse_primer_name', label: 'K 反向引物', minWidth: 150, defaultVisible: false, showOverflowTooltip: true },
  { key: 'k_primer_concentration', label: 'K 浓度', minWidth: 120, defaultVisible: false },
  { key: 'l_forward_primer_name', label: 'L 正向引物', minWidth: 150, defaultVisible: false, showOverflowTooltip: true },
  { key: 'l_reverse_primer_name', label: 'L 反向引物', minWidth: 150, defaultVisible: false, showOverflowTooltip: true },
  { key: 'l_primer_concentration', label: 'L 浓度', minWidth: 120, defaultVisible: false },
  { key: 'index_mode', label: 'Barcode 方式', minWidth: 130, defaultVisible: false, showOverflowTooltip: true },
  { key: 'i7_name', label: 'i7 名称', minWidth: 150, defaultVisible: false, showOverflowTooltip: true },
  { key: 'i7_sequence', label: 'i7 序列', minWidth: 150, defaultVisible: false, showOverflowTooltip: true },
  { key: 'i5_name', label: 'i5 名称', minWidth: 150, defaultVisible: false, showOverflowTooltip: true },
  { key: 'i5_sequence', label: 'i5 序列', minWidth: 150, defaultVisible: false, showOverflowTooltip: true },
  { key: 'qc_owner', label: '质检人', minWidth: 110, defaultVisible: false, showOverflowTooltip: true },
  { key: 'qc_note', label: '质检说明', minWidth: 180, defaultVisible: false, showOverflowTooltip: true, keepLineBreaks: true },
  { key: 'remark', label: '备注', minWidth: 180, defaultVisible: false, showOverflowTooltip: true, keepLineBreaks: true },
  { key: 'actions', label: '操作', defaultVisible: true, width: 240, align: 'center', className: 'action-column-cell', fixed: 'right' },
]
