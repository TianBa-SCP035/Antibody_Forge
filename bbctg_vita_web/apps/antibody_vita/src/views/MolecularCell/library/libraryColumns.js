export const BUILD_PLATE = 'plate_single_cell'
export const BUILD_POOLED_BCR = 'pooled_bcr'
export const BUILD_PHAGE_DISPLAY = 'phage_display'
export const BUILD_PHAGE_NGS = 'phage_ngs'
export const BUILD_PERIPHERAL_BLOOD = 'peripheral_blood_bcr'
export const INSTRUMENT_DATE_BUILDS = [BUILD_PLATE, BUILD_POOLED_BCR, BUILD_PHAGE_DISPLAY]

export const BUILD_TYPE_OPTIONS = [
  { value: BUILD_PLATE, label: '单细胞孔板', hint: 'Beacon、达普打板的单细胞恢复' },
  { value: BUILD_POOLED_BCR, label: '混管 BCR', hint: '达普打管样品的 BCR 扩增' },
  { value: BUILD_PHAGE_DISPLAY, label: '噬菌体展示', hint: '用于展示筛选的噬菌体建库' },
  { value: BUILD_PHAGE_NGS, label: '噬菌体 NGS', hint: '展示筛选产物的 NGS 建库' },
  { value: BUILD_PERIPHERAL_BLOOD, label: '外周血 BCR', hint: '外周血样品的 BCR 扩增' },
]
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
  { value: 'dapu_tube', label: '达普打管', builds: [BUILD_POOLED_BCR] },
  { value: 'direct', label: '细胞/核酸', builds: [BUILD_PHAGE_DISPLAY] },
  { value: 'phage_display', label: '噬菌体展示产物', builds: [BUILD_PHAGE_NGS] },
  { value: 'phage_panning', label: '噬菌体筛选产物', builds: [BUILD_PHAGE_NGS] },
  { value: 'retro_orbital_blood', label: '眼眶血', builds: [BUILD_PERIPHERAL_BLOOD] },
  { value: 'other_blood', label: '其他外周血', builds: [BUILD_PERIPHERAL_BLOOD] },
]
export const SAMPLE_TYPE_OPTIONS = [
  { value: 'nano', label: 'Nano' },
  { value: 'lite', label: 'Lite' },
  { value: 'rnvm_blood', label: 'RNVM眼眶血' },
  { value: 'phage', label: '噬菌体' },
]
export const PHAGE_EXPERIMENT_TYPE_OPTIONS = ['抗体发现', '亲和力改造']
export const INDEX_MODE_OPTIONS = [
  { value: 'none', label: '不加 Barcode' },
  { value: 'single_i7', label: 'i7' },
  { value: 'single_i5', label: 'i5' },
  { value: 'dual', label: '双端 i7 + i5' },
]
export const TARGET_FORM_OPTIONS = ['多穿', '分泌', 'I型', 'II型']
export const STATUS_OPTIONS = ['待处理', '建库中', '待质检', '已完成', '质检不通过', '已取消']
export const PRIORITY_OPTIONS = ['吉吉国王', '非常紧急', '加急', '正常']
export const QC_RESULT_OPTIONS = ['待判定', '通过', '不通过']
export const CELL_TYPE_OPTIONS = ['全细胞', '浆细胞', '流穿液']

export function statusTone(status) {
  if (status === '已完成') return 'success'
  if (status === '质检不通过' || status === '已取消') return 'danger'
  if (status === '建库中' || status === '待质检') return 'warning'
  return 'info'
}

export const MOUSE_CATEGORY_OPTIONS = [
  'RL-KO',
  'RN-KO',
  'RM-KO',
  'RL',
  'RN',
  'RM',
  'RN-VM',
  'RN-VR',
  'RN-VM-KO',
]
export const MOUSE_CATEGORY_LABELS = {
  RN: 'Nano',
  RL: 'Lite',
  RM: 'RenMab',
  'RN-VM': 'Nano-VM',
  'RN-VR': 'Nano-VR',
  'RN-KO': 'Nano-KO',
  'RL-KO': 'Lite-KO',
  'RM-KO': 'RenMab-KO',
  'RN-VM-KO': 'Nano-VM-KO',
}
export function mouseCategoryLabel(code) {
  const text = String(code || '').trim()
  if (!text) return ''
  return text
    .split(/[,，、]/)
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item) => MOUSE_CATEGORY_LABELS[item] || item)
    .join('、')
}

export function sampleSourceLabel(value) {
  return SAMPLE_SOURCE_OPTIONS.find((item) => item.value === value)?.label || value || ''
}
export function sampleTypeLabel(value) {
  return SAMPLE_TYPE_OPTIONS.find((item) => item.value === value)?.label || value || ''
}
export function optionsForBuild(options, buildType) {
  return options.filter((item) => !item.builds || item.builds.includes(buildType))
}
export function normalizePlateInputText(value) {
  return String(value || '').replace(/\r\n?/g, '\n').replace(/[，,\t]+/g, '\n')
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
  { key: 'study_type', label: '课题类型' },
  { key: 'pm', label: 'PM', type: 'user' },
  { key: 'notebook_no', label: '实验记录本号' },
  { key: 'target_name', label: '靶点', type: 'target', wide: true },
  { key: 'mouse_model', label: '归类鼠型', type: 'select', options: MOUSE_CATEGORY_OPTIONS.map((item) => ({ value: item, label: mouseCategoryLabel(item) })) },
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
  { key: 'started_at', label: '开始时间', type: 'datetime' },
  { key: 'finished_at', label: '完成时间', type: 'datetime' },
  { key: 'source_discovery_id', label: '来源发现 ID', type: 'source-link' },
  { key: 'remark', label: '备注', type: 'textarea', wide: true },
]
const LOCATIONS = [
  { key: 'rna_location', label: 'RNA 位置' },
  { key: 'cdna_location', label: 'cDNA 位置' },
  { key: 'library_location', label: '文库位置' },
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
const INDEX_FIELDS = [
  { key: 'index_mode', label: 'Barcode 方式', type: 'select', options: INDEX_MODE_OPTIONS },
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
const QC_FIELDS = [
  { key: 'qc_result', label: '质检结论', type: 'select', options: QC_RESULT_OPTIONS },
  { key: 'qc_owner', label: '质检人', type: 'user' },
  { key: 'qc_on', label: '质检日期', type: 'date' },
  { key: 'qc_note', label: '质检说明', type: 'textarea', wide: true },
]

const PROFILE_SECTIONS = {
  [BUILD_PLATE]: [
    {
      title: '孔板样品',
      fields: [
        { key: 'instrument_on', label: '上机日期', type: 'date' },
        { key: 'positive_cell_count', label: '阳性细胞数' },
        { key: 'plate_nos', label: '板号', type: 'plate-list', wide: true },
      ],
    },
    {
      title: 'PCR 与转染',
      fields: [
        { key: 'pcr_started_at', label: 'PCR 开始', type: 'datetime' },
        { key: 'pcr_finished_at', label: 'PCR 结束', type: 'datetime' },
        { key: 'pcr_owner', label: 'PCR 操作人', type: 'user' },
        { key: 'pcr_qc_owner', label: 'PCR 检测人', type: 'user' },
        { key: 'transfected_at', label: '转染时间', type: 'datetime' },
        { key: 'transfection_owner', label: '转染人', type: 'user' },
      ],
    },
  ],
  [BUILD_POOLED_BCR]: [
    {
      title: '混管与材料',
      fields: [
        { key: 'instrument_on', label: '上机日期', type: 'date' },
        { key: 'positive_cell_count', label: '阳性细胞数' },
        { key: 'cell_type', label: '细胞类型', type: 'select', options: CELL_TYPE_OPTIONS },
        { key: 'cdna_concentration', label: 'cDNA 浓度' },
        ...LOCATIONS,
      ],
    },
    { title: 'H / K / L 引物', fields: PRIMER_MATRIX },
  ],
  [BUILD_PHAGE_DISPLAY]: [
    {
      title: '展示文库',
      fields: [
        { key: 'source_experiment_type', label: '实验类型', type: 'select', options: PHAGE_EXPERIMENT_TYPE_OPTIONS },
        { key: 'project_goal', label: '实验目标', type: 'textarea', wide: true },
        { key: 'instrument_on', label: '上机日期', type: 'date' },
        { key: 'cell_type', label: '细胞类型' },
        { key: 'target_forms', label: '靶点形式', type: 'multi-select', options: TARGET_FORM_OPTIONS },
        { key: 'initial_library_size', label: '初始库容' },
        { key: 'effective_library_size', label: '有效库容' },
        ...LOCATIONS,
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
        ...LOCATIONS,
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
        { key: 'cdna_concentration', label: 'cDNA 浓度' },
        { key: 'fragment_size_bp', label: '片段大小' },
        ...LOCATIONS,
      ],
    },
  ],
}

export function orderEditorSections(buildType, order = {}) {
  const barcodeSections = buildType && buildType !== BUILD_POOLED_BCR
    ? [{ title: 'Barcode', fields: visibleIndexFields(order) }]
    : []
  return [
    { title: '工单安排', queue: true, fields: COMMON_SCHEDULE },
    { title: '基本信息', fields: COMMON_IDENTITY },
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
  study_type: def('study_type', '课题类型'),
  source_experiment_type: def('source_experiment_type', '实验类型', 'select'),
  project_goal: def('project_goal', '实验目标', 'text', 180),
  target_name: def('target_name', '靶点', 'target'),
  target_codes: def('target_codes', '靶点编号', 'target', 140),
  pm: def('pm', 'PM', 'select', 100),
  mouse_model: def('mouse_model', '归类鼠型', 'select'),
  sample_type: def('sample_type', '样品类型', 'select'),
  received_on: def('received_on', '交接日期', 'date', 130),
  instrument_on: def('instrument_on', '上机日期', 'date', 130),
  blood_collected_on: def('blood_collected_on', '采血日期', 'date', 130),
  positive_cell_count: def('positive_cell_count', '阳性细胞数'),
  plate_nos: def('plate_nos', '板号', 'text', 150),
  target_forms: def('target_forms', '靶点形式', 'text', 150),
  status: def('status', '状态', 'select', 110),
  priority: def('priority', '优先级', 'select', 110),
  owner: def('owner', '负责人', 'select', 110),
  started_at: def('started_at', '开始时间', 'datetime', 160),
  finished_at: def('finished_at', '完成时间', 'datetime', 160),
  pcr_started_at: def('pcr_started_at', 'PCR 开始', 'datetime', 160),
  pcr_finished_at: def('pcr_finished_at', 'PCR 结束', 'datetime', 160),
  pcr_owner: def('pcr_owner', 'PCR 操作人', 'select', 120),
  pcr_qc_owner: def('pcr_qc_owner', 'PCR 检测人', 'select', 120),
  transfected_at: def('transfected_at', '转染时间', 'datetime', 160),
  transfection_owner: def('transfection_owner', '转染人', 'select', 110),
  cell_type: def('cell_type', '细胞类型', 'select'),
  notebook_no: def('notebook_no', '实验记录本号'),
  immunization_stage: def('immunization_stage', '免疫阶段'),
  library_batch_no: def('library_batch_no', '建库批号'),
  rna_location: def('rna_location', 'RNA 位置', 'text', 140),
  cdna_location: def('cdna_location', 'cDNA 位置', 'text', 140),
  library_location: def('library_location', '文库位置', 'text', 140),
  cdna_concentration: def('cdna_concentration', 'cDNA 浓度'),
  initial_library_size: def('initial_library_size', '初始库容'),
  effective_library_size: def('effective_library_size', '有效库容'),
  fragment_size_bp: def('fragment_size_bp', '片段大小'),
  h_forward_primer_name: def('h_forward_primer_name', 'H 正向引物', 'text', 150),
  h_reverse_primer_name: def('h_reverse_primer_name', 'H 反向引物', 'text', 150),
  h_primer_concentration: def('h_primer_concentration', 'H 浓度'),
  k_forward_primer_name: def('k_forward_primer_name', 'K 正向引物', 'text', 150),
  k_reverse_primer_name: def('k_reverse_primer_name', 'K 反向引物', 'text', 150),
  k_primer_concentration: def('k_primer_concentration', 'K 浓度'),
  l_forward_primer_name: def('l_forward_primer_name', 'L 正向引物', 'text', 150),
  l_reverse_primer_name: def('l_reverse_primer_name', 'L 反向引物', 'text', 150),
  l_primer_concentration: def('l_primer_concentration', 'L 浓度'),
  index_mode: def('index_mode', 'Barcode 方式', 'select'),
  i7_name: def('i7_name', 'i7 名称', 'text', 150),
  i7_sequence: def('i7_sequence', 'i7 序列', 'text', 150),
  i5_name: def('i5_name', 'i5 名称', 'text', 150),
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
  'mouse_model',
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
const PROFILE_SHEET_KEYS = {
  [BUILD_PLATE]: [
    'instrument_on',
    'positive_cell_count',
    'plate_nos',
    'pcr_started_at',
    'pcr_finished_at',
    'pcr_owner',
    'pcr_qc_owner',
    'transfected_at',
    'transfection_owner',
    'index_mode',
    'i7_name',
    'i7_sequence',
    'i5_name',
    'i5_sequence',
  ],
  [BUILD_POOLED_BCR]: [
    'instrument_on',
    'positive_cell_count',
    'cell_type',
    'cdna_concentration',
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
  [BUILD_PHAGE_DISPLAY]: [
    'source_experiment_type',
    'project_goal',
    'instrument_on',
    'cell_type',
    'target_forms',
    'initial_library_size',
    'effective_library_size',
    'rna_location',
    'cdna_location',
    'library_location',
    'index_mode',
    'i7_name',
    'i7_sequence',
    'i5_name',
    'i5_sequence',
  ],
  [BUILD_PHAGE_NGS]: [
    'source_experiment_type',
    'project_goal',
    'library_batch_no',
    'fragment_size_bp',
    'rna_location',
    'cdna_location',
    'library_location',
    'index_mode',
    'i7_name',
    'i7_sequence',
    'i5_name',
    'i5_sequence',
  ],
  [BUILD_PERIPHERAL_BLOOD]: [
    'blood_collected_on',
    'immunization_stage',
    'positive_cell_count',
    'cdna_concentration',
    'fragment_size_bp',
    'rna_location',
    'cdna_location',
    'library_location',
    'index_mode',
    'i7_name',
    'i7_sequence',
    'i5_name',
    'i5_sequence',
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
  'pcr_started_at',
  'pcr_finished_at',
  'pcr_owner',
  'pcr_qc_owner',
  'transfected_at',
  'transfection_owner',
  'rna_location',
  'cdna_location',
  'library_location',
  'cdna_concentration',
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
  { key: 'mouse_model', label: '归类鼠型', minWidth: 110, defaultVisible: false, showOverflowTooltip: true },
  { key: 'study_type', label: '课题类型', minWidth: 120, defaultVisible: false, showOverflowTooltip: true },
  { key: 'pm', label: 'PM', minWidth: 100, defaultVisible: false, showOverflowTooltip: true },
  { key: 'source_discovery_id', label: '来源发现 ID', minWidth: 160, defaultVisible: false, showOverflowTooltip: true },
  { key: 'notebook_no', label: '实验记录本号', minWidth: 140, defaultVisible: false, showOverflowTooltip: true },
  { key: 'received_on', label: '交接日期', minWidth: 130, defaultVisible: false, className: 'date-column-cell' },
  { key: 'instrument_on', label: '上机日期', minWidth: 130, defaultVisible: false },
  { key: 'started_at', label: '开始时间', minWidth: 160, defaultVisible: false, showOverflowTooltip: true },
  { key: 'finished_at', label: '完成时间', minWidth: 160, defaultVisible: false, showOverflowTooltip: true },
  { key: 'qc_result', label: '质检结论', minWidth: 110, defaultVisible: false },
  { key: 'qc_on', label: '质检日期', minWidth: 130, defaultVisible: false },
  { key: 'actions', label: '操作', defaultVisible: true, width: 240, align: 'center', className: 'action-column-cell', fixed: 'right' },
]
