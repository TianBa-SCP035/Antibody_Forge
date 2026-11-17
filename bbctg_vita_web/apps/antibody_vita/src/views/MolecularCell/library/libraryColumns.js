import {
  createColumnOrder,
  defineFields,
  editorSections,
  headerMenuColumns,
  PRIORITY_FIELD,
  sheetColumns,
  TARGET_DRAWER_FIELD,
  workbenchColumns,
} from '#/components/workbench'
import { cleanFieldText } from '#/utils/fieldText'
import { WORKBENCH_PRIORITY_OPTIONS } from '#/utils/serumProjectStatus'
import { SERUM_MOUSE_STRAIN_OPTIONS } from '#/utils/serumMouseOptions'
import { WORKBENCH_STUDY_TYPE_OPTIONS } from '#/utils/workbenchStudyTypes'

/** 列顺序、列宽等视图偏好的本地存储键，已发布不要改值 */
export const LIBRARY_VIEW_PREFS_KEY = 'libraryConstructionWorkbench.v4'

const STUDY_TYPE_OPTIONS = [...WORKBENCH_STUDY_TYPE_OPTIONS]
export const BUILD_PLATE = 'plate_single_cell'
export const BUILD_POOLED_BCR = 'pooled_bcr'
export const BUILD_POOLED_BARCODE = 'pooled_barcode'
export const BUILD_PLASMA_NGS = 'plasma_ngs'
export const BUILD_PHAGE_DISPLAY = 'phage_display'
export const BUILD_PHAGE_NGS = 'phage_ngs'
export const BUILD_PERIPHERAL_BLOOD = 'peripheral_blood_bcr'
export const INSTRUMENT_DATE_BUILDS = [BUILD_PLATE, BUILD_POOLED_BCR, BUILD_POOLED_BARCODE, BUILD_PHAGE_DISPLAY]
const BARCODE_BUILD_TYPES = new Set([BUILD_POOLED_BARCODE, BUILD_PHAGE_NGS, BUILD_PERIPHERAL_BLOOD])

const BUILD_TYPE_OPTIONS = [
  { value: BUILD_PLATE, label: '单细胞孔板', hint: 'Beacon、达普打板的细胞恢复' },
  { value: BUILD_POOLED_BCR, label: '混管 H/K/L', hint: '达普打管，文库补 H/K/L 引物' },
  { value: BUILD_POOLED_BARCODE, label: '混管 Barcode', hint: '达普打管或浆细胞直测，文库补测序 Barcode' },
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
const TYPE_VALUES = BUILD_TYPE_OPTIONS.map((item) => item.value)

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
  { value: 'plasma_direct', label: '浆细胞直测', builds: [BUILD_POOLED_BARCODE] },
]
const SAMPLE_TYPE_OPTIONS = [
  { value: 'nano', label: 'Nano' },
  { value: 'lite', label: 'Lite' },
  { value: 'rnvm_blood', label: 'RNVM眼眶血' },
  { value: 'phage', label: '噬菌体' },
]
const PLASMA_SAMPLE_TYPE_OPTIONS = SAMPLE_TYPE_OPTIONS.filter((item) => item.value === 'nano' || item.value === 'lite')
const PHAGE_EXPERIMENT_TYPE_OPTIONS = ['抗体发现', '亲和力改造']
const INDEX_MODE_OPTIONS = [
  { value: 'none', label: '不加 Barcode' },
  { value: 'single_i7', label: 'i7' },
  { value: 'single_i5', label: 'i5' },
  { value: 'dual', label: '双端 i7 + i5' },
]
const TARGET_FORM_OPTIONS = ['多穿', '分泌', 'I型', 'II型']
export const STATUS_OPTIONS = ['待处理', '建库中', '待质检', '质检待确认', '质检通过', '已完成', '质检不通过', '已取消']
export const PRIORITY_OPTIONS = [...WORKBENCH_PRIORITY_OPTIONS]
export const QC_RESULT_OPTIONS = ['待判定', '通过', '不通过']
const CELL_TYPE_OPTIONS = ['全细胞', '浆细胞', '流穿液']
const MOUSE_STRAIN_OPTIONS = [...SERUM_MOUSE_STRAIN_OPTIONS]

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

export function sampleSourceLabel(value) {
  return SAMPLE_SOURCE_OPTIONS.find((item) => item.value === value)?.label || value || ''
}
export function sampleTypeLabel(value) {
  return SAMPLE_TYPE_OPTIONS.find((item) => item.value === value)?.label || value || ''
}
export function optionsForBuild(options, buildType) {
  return options.filter((item) => !item.builds || item.builds.includes(buildType))
}
/** 随建库类型变化的可选项：样品来源按类型过滤，浆细胞 NGS 的样品类型只有 Nano / Lite；其余返回 null。 */
export function libraryFieldOptions(field, row) {
  if (field.key === 'sample_source') return optionsForBuild(SAMPLE_SOURCE_OPTIONS, row?.build_type)
  if (field.key === 'sample_type' && row?.build_type === BUILD_PLASMA_NGS) return PLASMA_SAMPLE_TYPE_OPTIONS
  return null
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
      {
        id: 'plasma-direct',
        buildType: BUILD_POOLED_BARCODE,
        source: 'plasma_direct',
        label: '浆细胞直测',
        hint: '不用试剂盒挑选，按打管工艺建库；Nano/Lite 按小鼠品系带出，可到文库构建里改',
      },
    ],
  },
]
/** scope 是后端按建库类型权限给出的可见类型（build_type_scope），null 表示不限；超出范围的类型看不到也建不了。 */
export function inBuildTypeScope(scope, buildType) {
  return !scope || scope.includes(buildType)
}
export function buildTypeOptions(scope) {
  return BUILD_TYPE_OPTIONS.filter((item) => inBuildTypeScope(scope, item.value))
}
export function handoffRowsInScope(scope) {
  return HANDOFF_METHOD_ROWS
    .map((row) => ({ ...row, picks: row.picks.filter((pick) => inBuildTypeScope(scope, pick.buildType)) }))
    .filter((row) => row.picks.length)
}
/** 一行一个板号，行内原样保留（逗号、点号常用来写同前缀的多块板），与后端、发现台交接同一规则。 */
export function plateNumbersFromText(value) {
  return [...new Set(cleanFieldText(value, { keepBreaks: true }).split('\n').map((item) => item.trim()).filter(Boolean))]
}
export function plateNumbersText(values) {
  return (Array.isArray(values) ? values : []).map((item) => String(item || '').trim()).filter(Boolean).join('\n')
}

const PRIMER_ROWS = [
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

const recent = (top) => ({ type: 'text', values: 'recent', ...(top ? { top } : {}) })
const allValues = (type, top) => ({ type, values: 'all', ...(top ? { top } : {}) })
const searchText = (top) => ({ type: 'text', values: 'search', ...(top ? { top } : {}) })
const primerName = (label) => ({
  label,
  max: 128,
  header: allValues('enum'),
  list: { minWidth: 150 },
  sheet: { edit: 'catalog', minWidth: 150 },
})
const shortText = (label, header = recent()) => ({ label, max: 64, header, list: { minWidth: 120 }, sheet: { minWidth: 120 } })
const location = (label, type = 'text') => ({ label, type, max: 255, header: recent(), list: { minWidth: 140 }, sheet: { minWidth: 140 } })
const dateField = (label, header = allValues('date'), list = {}) => ({
  label,
  type: 'date',
  header,
  list: { minWidth: 130, ...list },
  sheet: { minWidth: 130 },
})

export const FIELDS = defineFields({
  library_order_id: { label: '系统工单号', header: recent(), list: { minWidth: 170 }, sheet: { readonly: true, minWidth: 170 } },
  source_discovery_id: {
    label: '来源发现 ID',
    header: recent({ query: 'source_discovery_id', kind: 'codes' }),
    list: { minWidth: 160 },
    sheet: { readonly: true, minWidth: 160 },
    drawer: { type: 'source-link' },
  },
  library_code: {
    label: '建库编号',
    max: 64,
    header: recent({ query: 'library_code', kind: 'codes' }),
    list: { show: true, minWidth: 120 },
    sheet: { minWidth: 120 },
  },
  build_type: {
    label: '建库类型',
    type: 'select',
    options: BUILD_TYPE_OPTIONS,
    required: true,
    header: allValues('enum', { query: 'build_type' }),
    list: { show: true, minWidth: 150 },
    sheet: { minWidth: 150 },
  },
  sample_source: {
    label: '样品来源',
    type: 'select',
    options: SAMPLE_SOURCE_OPTIONS,
    header: allValues('enum', { query: 'sample_source' }),
    list: { show: true, minWidth: 130 },
    sheet: { minWidth: 140 },
  },
  source_project_code: {
    label: '项目编号',
    max: 64,
    header: recent({ query: 'source_project_code', kind: 'codes' }),
    list: { show: true, minWidth: 130 },
    sheet: { minWidth: 120 },
  },
  study_type: {
    label: '课题类型',
    type: 'select',
    options: STUDY_TYPE_OPTIONS,
    max: 64,
    header: allValues('enum', { query: 'study_type', kind: 'contains' }),
    list: { minWidth: 120 },
    sheet: { minWidth: 120 },
  },
  source_experiment_type: {
    label: '实验类型',
    type: 'select',
    options: PHAGE_EXPERIMENT_TYPE_OPTIONS,
    header: allValues('enum'),
    list: { minWidth: 120 },
    sheet: { minWidth: 120 },
  },
  project_goal: {
    label: '实验目标',
    type: 'textarea',
    max: 1000,
    header: searchText(),
    list: { minWidth: 180 },
    sheet: { minWidth: 180 },
    drawer: { wide: true },
  },
  target_name: {
    label: '靶点',
    type: 'target',
    max: 128,
    header: { type: 'text', values: 'all', search: 'target', top: { query: 'target_name' } },
    list: { show: true, minWidth: 150 },
    sheet: { minWidth: 120 },
  },
  target_codes: { label: '靶点编号', type: 'target_codes', list: { minWidth: 140 }, sheet: { minWidth: 140 } },
  pm: {
    label: 'PM',
    type: 'user',
    max: 64,
    header: allValues('enum', { query: 'pm', kind: 'contains' }),
    list: { minWidth: 100 },
    sheet: { minWidth: 100 },
  },
  mouse_strain: {
    label: '小鼠品系',
    type: 'tags',
    options: MOUSE_STRAIN_OPTIONS,
    max: 128,
    header: allValues('csv', { query: 'mouse_strain' }),
    list: { minWidth: 110 },
    sheet: { minWidth: 120 },
  },
  sample_type: {
    label: '样品类型',
    type: 'select',
    options: SAMPLE_TYPE_OPTIONS,
    header: allValues('enum', { query: 'sample_type' }),
    list: { show: true, minWidth: 110 },
    sheet: { minWidth: 120 },
  },
  received_on: dateField('交接日期', allValues('date'), { className: 'date-column-cell', tooltip: false }),
  instrument_on: dateField('上机日期', allValues('date', { range: 'instrumentRange' })),
  blood_collected_on: dateField('采血日期', allValues('date'), { className: 'date-column-cell' }),
  positive_cell_count: { ...shortText('阳性细胞数'), type: 'textarea', drawer: { sync: true } },
  plate_nos: {
    label: '板号',
    header: allValues('csv'),
    list: { minWidth: 150, keepLineBreaks: true, format: plateNumbersText },
    sheet: { minWidth: 150 },
    drawer: { type: 'plate-list', wide: true },
  },
  target_forms: {
    label: '靶点形式',
    type: 'select',
    options: TARGET_FORM_OPTIONS,
    header: allValues('enum'),
    list: { minWidth: 150 },
    sheet: { minWidth: 150 },
  },
  status: {
    label: '状态',
    type: 'select',
    options: STATUS_OPTIONS,
    required: true,
    header: allValues('enum', { query: 'status' }),
    list: { show: true, minWidth: 110, className: 'status-column-cell', tooltip: false },
    sheet: { minWidth: 110 },
  },
  priority: PRIORITY_FIELD,
  owner: {
    label: '负责人',
    type: 'user',
    max: 64,
    header: allValues('enum', { query: 'owner' }),
    list: { show: true, minWidth: 100 },
    sheet: { minWidth: 110 },
  },
  started_at: dateField('开始时间', allValues('date', { range: 'startedRange' })),
  finished_at: dateField('完成时间', allValues('date', { range: 'finishedRange' })),
  cell_type: {
    label: '细胞类型',
    type: 'select',
    options: CELL_TYPE_OPTIONS,
    max: 64,
    header: allValues('enum', { query: 'cell_type', kind: 'contains' }),
    list: { minWidth: 120 },
    sheet: { minWidth: 120 },
  },
  notebook_no: { ...shortText('实验记录本号', recent({ query: 'notebook_no', kind: 'contains' })), list: { minWidth: 140 } },
  immunization_stage: shortText('免疫阶段', allValues('enum')),
  library_batch_no: { ...shortText('建库批号', recent({ query: 'library_batch_no', kind: 'codes' })), list: { minWidth: 130 } },
  rna_location: location('RNA 位置'),
  cdna_location: location('cDNA 位置'),
  library_location: location('文库位置', 'textarea'),
  cdna_concentration: shortText('cDNA 浓度'),
  library_concentration: shortText('文库浓度'),
  initial_library_size: shortText('初始库容'),
  effective_library_size: shortText('有效库容'),
  fragment_size_bp: { ...shortText('片段大小'), type: 'textarea', drawer: { sync: true } },
  h_forward_primer_name: primerName('H 正向引物'),
  h_reverse_primer_name: primerName('H 反向引物'),
  h_primer_concentration: shortText('H 浓度'),
  k_forward_primer_name: primerName('K 正向引物'),
  k_reverse_primer_name: primerName('K 反向引物'),
  k_primer_concentration: shortText('K 浓度'),
  l_forward_primer_name: primerName('L 正向引物'),
  l_reverse_primer_name: primerName('L 反向引物'),
  l_primer_concentration: shortText('L 浓度'),
  index_mode: {
    label: 'Barcode 方式',
    type: 'select',
    options: INDEX_MODE_OPTIONS,
    header: allValues('enum'),
    list: { minWidth: 130 },
    sheet: { minWidth: 120 },
  },
  i7_name: {
    ...primerName('i7 名称'),
    drawer: { type: 'catalog-select', catalogIdKey: 'i7_catalog_id', sequenceKey: 'i7_sequence' },
  },
  i7_sequence: { ...shortText('i7 序列'), list: { minWidth: 150 }, sheet: { minWidth: 150 } },
  i5_name: {
    ...primerName('i5 名称'),
    drawer: { type: 'catalog-select', catalogIdKey: 'i5_catalog_id', sequenceKey: 'i5_sequence' },
  },
  i5_sequence: { ...shortText('i5 序列'), list: { minWidth: 150 }, sheet: { minWidth: 150 } },
  qc_result: {
    label: '质检结论',
    type: 'select',
    options: QC_RESULT_OPTIONS,
    header: allValues('enum'),
    list: { minWidth: 110 },
    sheet: { minWidth: 120 },
  },
  qc_owner: { label: '质检人', type: 'user', max: 64, header: allValues('enum'), list: { minWidth: 110 }, sheet: { minWidth: 110 } },
  qc_on: dateField('质检日期'),
  qc_note: {
    label: '质检说明',
    type: 'textarea',
    max: 1000,
    header: searchText(),
    list: { minWidth: 180 },
    sheet: { minWidth: 180 },
    drawer: { wide: true },
  },
  remark: {
    label: '备注',
    type: 'textarea',
    max: 1000,
    header: searchText({ query: 'remark', kind: 'contains' }),
    list: { minWidth: 180 },
    sheet: { minWidth: 180 },
    drawer: { wide: true },
  },
})

export const HEADER_MENU_COLUMNS = headerMenuColumns(FIELDS)

const PRIMER_MATRIX = { key: 'primer_matrix', label: '', type: 'primer-matrix', rows: PRIMER_ROWS, wide: true, labelWidth: '0' }
const TUBE_MATERIAL_FIELDS = [
  { key: 'instrument_on', rowBreak: true },
  'positive_cell_count',
  'fragment_size_bp',
  { key: 'rna_location', rowBreak: true },
  'cdna_location',
  'cdna_concentration',
  'library_location',
  'library_concentration',
]
const PROFILE_SECTIONS = {
  [BUILD_PLATE]: [
    { title: '孔板样品', fields: [{ key: 'instrument_on', rowBreak: true }, 'positive_cell_count', 'cdna_location', 'plate_nos'] },
  ],
  [BUILD_POOLED_BCR]: [
    { title: '混管与材料', fields: TUBE_MATERIAL_FIELDS },
    { title: 'H / K / L 引物', fields: [PRIMER_MATRIX] },
  ],
  [BUILD_POOLED_BARCODE]: [
    { title: '混管与材料', fields: TUBE_MATERIAL_FIELDS },
  ],
  [BUILD_PLASMA_NGS]: [
    {
      title: '浆细胞材料',
      fields: [
        { key: 'instrument_on', rowBreak: true },
        'positive_cell_count',
        'fragment_size_bp',
        { key: 'cell_type', rowBreak: true },
        'rna_location',
        'cdna_location',
        'library_location',
        'library_concentration',
      ],
    },
  ],
  [BUILD_PHAGE_DISPLAY]: [
    {
      title: '展示文库',
      fields: [
        'source_experiment_type',
        'project_goal',
        { key: 'instrument_on', rowBreak: true },
        'library_batch_no',
        'target_forms',
        'initial_library_size',
        'effective_library_size',
        'cell_type',
        'rna_location',
        'cdna_location',
        'library_location',
      ],
    },
  ],
  [BUILD_PHAGE_NGS]: [
    {
      title: '噬菌体样品',
      fields: [
        'source_experiment_type',
        'project_goal',
        'library_batch_no',
        'fragment_size_bp',
        'library_location',
        'library_concentration',
      ],
    },
  ],
  [BUILD_PERIPHERAL_BLOOD]: [
    {
      title: '外周血样品',
      fields: [
        'blood_collected_on',
        'immunization_stage',
        'positive_cell_count',
        'fragment_size_bp',
        { key: 'rna_location', rowBreak: true },
        'cdna_location',
        'cdna_concentration',
        'library_location',
        'library_concentration',
      ],
    },
  ],
}

export function orderEditorSections(buildType, order) {
  const indexFields = Object.keys(INDEX_KEY_MODES).filter((key) => INDEX_KEY_MODES[key].includes(order?.index_mode))
  return editorSections(FIELDS, [
    {
      title: '工单安排',
      queue: true,
      fields: ['status', 'priority', 'owner', 'started_at', 'finished_at', 'source_discovery_id', 'remark'],
    },
    {
      title: '基本信息',
      fields: [
        'library_code',
        'build_type',
        'source_project_code',
        'study_type',
        'pm',
        'notebook_no',
        TARGET_DRAWER_FIELD,
        'mouse_strain',
        'sample_type',
      ],
    },
    { title: '样品交接', fields: ['sample_source', 'received_on'] },
    ...(PROFILE_SECTIONS[buildType] || []),
    ...(BARCODE_BUILD_TYPES.has(buildType)
      ? [{ title: 'Barcode', fields: [{ key: 'index_mode', rowBreak: true }, ...indexFields] }]
      : []),
    { title: '质控结果', fields: ['qc_result', 'qc_owner', 'qc_on', 'qc_note'] },
  ])
}

const COMMON_SHEET_KEYS = [
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
  'status',
  'priority',
  'owner',
  'started_at',
  'finished_at',
  'received_on',
  'qc_result',
  'qc_owner',
  'qc_on',
  'qc_note',
  'remark',
]
const INDEX_SHEET_KEYS = ['index_mode', 'i7_name', 'i7_sequence', 'i5_name', 'i5_sequence']
const MATERIAL_SHEET_KEYS = [
  'cdna_concentration',
  'library_concentration',
  'fragment_size_bp',
  'rna_location',
  'cdna_location',
  'library_location',
]
const PROFILE_SHEET_KEYS = {
  [BUILD_PLATE]: ['instrument_on', 'positive_cell_count', 'cdna_location', 'plate_nos'],
  [BUILD_POOLED_BCR]: [
    'instrument_on',
    'positive_cell_count',
    ...MATERIAL_SHEET_KEYS,
    ...PRIMER_ROWS.flatMap((primer) => [primer.forward.key, primer.reverse.key, primer.concentrationKey]),
  ],
  [BUILD_POOLED_BARCODE]: ['instrument_on', 'positive_cell_count', ...MATERIAL_SHEET_KEYS, ...INDEX_SHEET_KEYS],
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
    ...MATERIAL_SHEET_KEYS,
    ...INDEX_SHEET_KEYS,
  ],
}

/** 全部类型的 Excel 列；按类型筛选时只显示公共列和该类型的列。 */
export const SHEET_COLUMNS = sheetColumns(FIELDS, [
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
  'status',
  'priority',
  'owner',
  'started_at',
  'finished_at',
  'received_on',
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
  ...INDEX_SHEET_KEYS,
  'qc_result',
  'qc_owner',
  'qc_on',
  'qc_note',
  'remark',
])
export const SHEET_COLUMN_ORDER = createColumnOrder('libraryConstructionSheetColumnOrder.v5', SHEET_COLUMNS)

export function isSheetFieldApplicable(buildType, key) {
  if (!PROFILE_SHEET_KEYS[buildType]) return true
  return COMMON_SHEET_KEYS.includes(key) || PROFILE_SHEET_KEYS[buildType].includes(key)
}
export function sheetColumnsForBuild(buildType) {
  return SHEET_COLUMNS.filter((column) => isSheetFieldApplicable(buildType, column.key))
}

export const WORKBENCH_COLUMNS = workbenchColumns(FIELDS, [
  'source_project_code',
  'target_name',
  'build_type',
  'sample_source',
  'sample_type',
  'library_code',
  'owner',
  'status',
  'priority',
  'mouse_strain',
  'study_type',
  'pm',
  'source_discovery_id',
  'notebook_no',
  'received_on',
  'instrument_on',
  'started_at',
  'finished_at',
  'qc_result',
  'qc_on',
  'library_order_id',
  'target_codes',
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
  'qc_owner',
  'qc_note',
  'remark',
])
