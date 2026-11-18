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
import { SERUM_MOUSE_STRAIN_OPTIONS } from '#/utils/serumMouseOptions'
import { WORKBENCH_STUDY_TYPE_OPTIONS } from '#/utils/workbenchStudyTypes'
import { plateNumbersText } from '../library/libraryColumns'

/** 列顺序、列宽等视图偏好的本地存储键，已发布不要改值 */
export const TRANSFECTION_VIEW_PREFS_KEY = 'transfectionWorkbench.v1'

export const TYPE_PCR = 'PCR转染'
export const TYPE_PLASMID = '质粒转染'
export const TYPE_OPTIONS = [TYPE_PCR, TYPE_PLASMID]
export const TYPE_HINTS = {
  [TYPE_PCR]: '文库构建单细胞孔板的下一步，转染表达后做 PCR 检测',
  [TYPE_PLASMID]: '不经上游，直接转染已有质粒验证结果',
}
export const STATUS_OPTIONS = ['待转染', '转染中', '已完成', '已取消']
export const STATUS_DONE = '已完成'
/** 交接到合成与验证后不能再改的字段，和后端 HANDOFF_LOCKED_FIELDS 一致。 */
export const HANDOFF_LOCKED_KEYS = ['transfection_type', 'status', 'transfected_on', 'finished_on']

export function statusTone(status) {
  if (status === '已完成') return 'success'
  if (status === '已取消') return 'danger'
  if (status === '转染中') return 'primary'
  return 'info'
}

const recent = (top) => ({ type: 'text', values: 'recent', ...(top ? { top } : {}) })
const allValues = (type, top) => ({ type, values: 'all', ...(top ? { top } : {}) })
const dateField = (label, range) => ({
  label,
  type: 'date',
  header: allValues('date', range ? { range } : undefined),
  list: { show: true, minWidth: 130, className: 'date-column-cell', tooltip: false },
  sheet: { minWidth: 130 },
})

export const FIELDS = defineFields({
  transfection_order_id: {
    label: '系统工单号',
    header: recent({ query: 'transfection_order_id', kind: 'codes' }),
    list: { minWidth: 170 },
    sheet: { readonly: true, minWidth: 170 },
  },
  transfection_type: {
    label: '转染类型',
    type: 'select',
    options: TYPE_OPTIONS,
    required: true,
    header: allValues('enum', { query: 'transfection_type' }),
    list: { show: true, minWidth: 110 },
    sheet: { minWidth: 110 },
  },
  source_library_order_id: {
    label: '来源文库工单',
    header: recent({ query: 'source_library_order_id', kind: 'codes' }),
    list: { minWidth: 170 },
    sheet: { readonly: true, minWidth: 170 },
  },
  project_code: {
    label: '项目编号',
    max: 64,
    header: recent({ query: 'project_code', kind: 'codes' }),
    list: { show: true, minWidth: 130 },
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
    options: [...SERUM_MOUSE_STRAIN_OPTIONS],
    max: 128,
    header: allValues('csv', { query: 'mouse_strain' }),
    list: { minWidth: 110 },
    sheet: { minWidth: 120 },
  },
  plate_nos: {
    label: '板号',
    header: allValues('csv'),
    list: { minWidth: 150, keepLineBreaks: true, format: plateNumbersText },
    sheet: { minWidth: 150 },
    drawer: { type: 'plate-list', wide: true },
  },
  protein_count: {
    label: '蛋白数',
    type: 'int',
    list: { show: true, minWidth: 90, align: 'center' },
    sheet: { readonly: true, minWidth: 90, align: 'center', lockHint: '蛋白清单在详情里导入' },
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
  transfected_on: dateField('转染日期', 'transfectedRange'),
  finished_on: dateField('完成日期', 'finishedRange'),
  synthesis_order_id: {
    label: '合成与验证单',
    list: { minWidth: 170 },
    sheet: { readonly: true, minWidth: 170, lockHint: '交接到合成与验证后自动带出' },
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

export const ORDER_EDITOR_SECTIONS = editorSections(FIELDS, [
  {
    title: '工单安排',
    queue: true,
    fields: ['status', 'priority', 'owner', 'transfected_on', 'finished_on', 'remark'],
  },
  {
    title: '基本信息',
    fields: [
      'transfection_type',
      'source_library_order_id',
      'project_code',
      'study_type',
      'pm',
      'mouse_strain',
      TARGET_DRAWER_FIELD,
      'plate_nos',
    ],
  },
])

export const SHEET_COLUMNS = sheetColumns(FIELDS, [
  'transfection_order_id',
  'source_library_order_id',
  'project_code',
  'target_name',
  'target_codes',
  'study_type',
  'pm',
  'mouse_strain',
  'transfection_type',
  'plate_nos',
  'protein_count',
  'owner',
  'status',
  'transfected_on',
  'finished_on',
  'priority',
  'synthesis_order_id',
  'remark',
])
export const SHEET_COLUMN_ORDER = createColumnOrder('transfectionSheetColumnOrder.v1', SHEET_COLUMNS)

export const WORKBENCH_COLUMNS = workbenchColumns(FIELDS, [
  'project_code',
  'target_name',
  'transfection_type',
  'protein_count',
  'owner',
  'status',
  'transfected_on',
  'finished_on',
  'priority',
  'mouse_strain',
  'pm',
  'study_type',
  'target_codes',
  'source_library_order_id',
  'plate_nos',
  'transfection_order_id',
  'synthesis_order_id',
  'remark',
])
