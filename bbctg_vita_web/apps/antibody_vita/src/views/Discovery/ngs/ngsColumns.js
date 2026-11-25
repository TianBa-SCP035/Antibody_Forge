import {
  createColumnOrder,
  defineFields,
  editorSections,
  headerMenuColumns,
  sheetColumns,
  TARGET_DRAWER_FIELD,
  workbenchColumns,
} from '#/components/workbench'
import { SERUM_MOUSE_STRAIN_OPTIONS } from '#/utils/serumMouseOptions'
import { WORKBENCH_STUDY_TYPE_OPTIONS } from '#/utils/workbenchStudyTypes'

export const NGS_VIEW_PREFS_KEY = 'ngsWorkbench.v1'

export const SAMPLE_LIBRARIES = ['Nano', 'Lite', '噬菌体', '研发库', '外来带样']
export const PROJECT_LEVELS = ['公司内部研发', '客户关注', '客户付钱', 'PCC过会', '数据包', '公司重点']
export const STATUS_OPTIONS = ['待上机', '已上机', '已送合成', '已完成', '已取消']
export const HANDOFF_LOCKED_KEYS = [
  'sample_library',
  'synthesis_code',
  'target_name',
  'target_codes',
  'mouse_strain',
  'pm',
  'project_code',
  'study_type',
]

export function statusTone(status) {
  if (status === '已完成' || status === '已送合成') return 'success'
  if (status === '已取消') return 'danger'
  if (status === '已上机') return 'primary'
  return 'info'
}

const recent = (top) => ({ type: 'text', values: 'recent', ...(top ? { top } : {}) })
const allValues = (type, top) => ({ type, values: 'all', ...(top ? { top } : {}) })
const dateField = (label, range) => ({
  label,
  type: 'date',
  header: allValues('date', range ? { range } : undefined),
  list: { minWidth: 130, className: 'date-column-cell', tooltip: false },
  sheet: { minWidth: 130 },
})
const textField = (label, extra = {}) => ({
  label,
  max: extra.max || 64,
  header: extra.header || recent(),
  list: { minWidth: extra.minWidth || 120 },
  sheet: { minWidth: extra.minWidth || 120 },
  ...(extra.drawer ? { drawer: extra.drawer } : {}),
})

export const FIELDS = defineFields({
  ngs_run_id: {
    label: '测序单号',
    header: recent({ query: 'ngs_run_id', kind: 'codes' }),
    list: { minWidth: 170 },
    sheet: { readonly: true, minWidth: 170 },
  },
  sample_library: {
    label: '样品库',
    type: 'select',
    options: SAMPLE_LIBRARIES,
    required: true,
    header: allValues('enum', { query: 'sample_library' }),
    list: { show: true, minWidth: 100 },
    sheet: { minWidth: 100 },
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
  source_library_order_id: {
    label: '来源文库工单',
    header: recent({ query: 'source_library_order_id', kind: 'codes' }),
    list: { minWidth: 170 },
    sheet: { readonly: true, minWidth: 170 },
  },
  library_code: {
    label: '建库编号',
    max: 64,
    header: recent({ query: 'library_code', kind: 'codes' }),
    list: { show: true, minWidth: 140 },
    sheet: { minWidth: 140 },
  },
  project_code: {
    label: '项目编号',
    max: 64,
    header: recent({ query: 'project_code', kind: 'codes' }),
    list: { minWidth: 130 },
    sheet: { minWidth: 120 },
  },
  project_level: {
    label: '项目级别',
    type: 'select',
    options: PROJECT_LEVELS,
    max: 64,
    header: allValues('enum', { query: 'project_level' }),
    list: { minWidth: 120 },
    sheet: { minWidth: 120 },
  },
  study_type: {
    label: '课题类型',
    type: 'select',
    options: [...WORKBENCH_STUDY_TYPE_OPTIONS],
    max: 64,
    header: allValues('enum', { query: 'study_type', kind: 'contains' }),
    list: { minWidth: 120 },
    sheet: { minWidth: 120 },
  },
  target_name: {
    label: '靶点',
    type: 'target',
    max: 128,
    header: { type: 'text', values: 'all', search: 'target', top: { query: 'target_name' } },
    list: { show: true, minWidth: 140 },
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
    options: [...SERUM_MOUSE_STRAIN_OPTIONS],
    max: 128,
    header: allValues('csv', { query: 'mouse_strain' }),
    list: { minWidth: 110 },
    sheet: { minWidth: 120 },
  },
  antigen_tag: textField('标签形式', { minWidth: 100 }),
  immunogen: {
    label: '具体免疫原',
    type: 'textarea',
    max: 1000,
    list: { minWidth: 160 },
    sheet: { minWidth: 160 },
    drawer: { wide: true },
  },
  cell_count: textField('细胞数量', { minWidth: 100 }),
  library_checked: textField('建库测序核对', { max: 128, minWidth: 140 }),
  load_note: {
    label: '上库备注',
    type: 'textarea',
    max: 255,
    list: { minWidth: 160 },
    sheet: { minWidth: 160 },
    drawer: { wide: true },
  },
  library_instrument_on: dateField('建库上机日期'),
  sequencing_date: {
    ...dateField('测序上机日期', 'sequencingRange'),
    list: { show: true, minWidth: 140, className: 'date-column-cell', tooltip: false },
  },
  instrument_no: {
    ...textField('仪器号', { header: recent({ query: 'instrument_no', kind: 'codes' }) }),
    list: { show: true, minWidth: 100 },
  },
  dissociation_buffer: textField('解离液', { max: 255, minWidth: 140 }),
  screening_antigen: {
    label: '筛选抗原',
    type: 'textarea',
    max: 1000,
    list: { minWidth: 160 },
    sheet: { minWidth: 160 },
    drawer: { wide: true },
  },
  batch_name: textField('批次号', { max: 128, minWidth: 120 }),
  synthesis_code: {
    label: '送合成转码',
    max: 64,
    header: recent({ query: 'synthesis_code', kind: 'codes' }),
    list: { show: true, minWidth: 150 },
    sheet: { minWidth: 150 },
  },
  synthesis_order_id: {
    label: '合成与验证单',
    list: { minWidth: 170 },
    sheet: { readonly: true, minWidth: 170, lockHint: '送合成后自动带出' },
  },
  rna_location: textField('RNA冻存位置', { max: 255, minWidth: 140 }),
  cdna_location: textField('cDNA冻存位置', { max: 255, minWidth: 140 }),
  library_location: textField('库冻存位置', { max: 255, minWidth: 140 }),
  sample_source: textField('样品来源', { max: 32, minWidth: 120 }),
  screening_goal: {
    label: '筛选目标',
    type: 'textarea',
    max: 1000,
    list: { minWidth: 160 },
    sheet: { minWidth: 160 },
    drawer: { wide: true },
  },
  fragment_size: textField('片段大小', { max: 32, minWidth: 100 }),
  barcode: textField('barcode', { minWidth: 120 }),
  sequenced: textField('是否已测序', { max: 16, minWidth: 110 }),
  owner: {
    label: '负责人',
    type: 'user',
    max: 64,
    header: allValues('enum', { query: 'owner' }),
    list: { show: true, minWidth: 100 },
    sheet: { minWidth: 100 },
  },
  remark: {
    label: '备注',
    type: 'textarea',
    max: 1000,
    header: { type: 'text', values: 'search', top: { query: 'remark', kind: 'contains' } },
    list: { minWidth: 180 },
    sheet: { minWidth: 180 },
    drawer: { wide: true },
  },
})

export const HEADER_MENU_COLUMNS = headerMenuColumns(FIELDS)

export const EDITOR_SECTIONS = editorSections(FIELDS, [
  {
    title: '上机',
    fields: ['status', 'owner', 'sequencing_date', 'instrument_no', 'dissociation_buffer', 'library_checked', 'load_note', 'remark'],
  },
  {
    title: '样品',
    fields: [
      'sample_library',
      'source_library_order_id',
      'library_code',
      'project_code',
      'project_level',
      'study_type',
      'pm',
      'mouse_strain',
      TARGET_DRAWER_FIELD,
      'antigen_tag',
      'immunogen',
      'cell_count',
      'library_instrument_on',
    ],
  },
  {
    title: '筛选与送合成',
    fields: [
      'screening_antigen',
      'batch_name',
      'synthesis_code',
      'synthesis_order_id',
      'rna_location',
      'cdna_location',
      'library_location',
    ],
  },
  {
    title: '噬菌体',
    fields: ['sample_source', 'screening_goal', 'fragment_size', 'barcode', 'sequenced'],
  },
])

const SHEET_KEYS = [
  'ngs_run_id',
  'sample_library',
  'library_code',
  'target_name',
  'target_codes',
  'project_code',
  'project_level',
  'mouse_strain',
  'pm',
  'sequencing_date',
  'instrument_no',
  'synthesis_code',
  'synthesis_order_id',
  'status',
  'owner',
  'screening_antigen',
  'remark',
]

export const SHEET_COLUMNS = sheetColumns(FIELDS, SHEET_KEYS)
export const SHEET_COLUMN_ORDER = createColumnOrder('ngsSheetColumnOrder.v1', SHEET_COLUMNS)

export const WORKBENCH_COLUMNS = workbenchColumns(FIELDS, [
  'library_code',
  'target_name',
  'sample_library',
  'sequencing_date',
  'instrument_no',
  'synthesis_code',
  'owner',
  'status',
  'project_code',
  'project_level',
  'mouse_strain',
  'pm',
  'study_type',
  'target_codes',
  'source_library_order_id',
  'ngs_run_id',
  'synthesis_order_id',
  'batch_name',
  'screening_antigen',
  'remark',
])
