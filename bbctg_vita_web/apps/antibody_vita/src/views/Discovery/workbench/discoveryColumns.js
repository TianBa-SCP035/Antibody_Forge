import {
  createColumnOrder,
  defineFields,
  editorSections,
  headerMenuColumns,
  PRIORITY_FIELD,
  sheetColumns,
  SORT_FIELD,
  TARGET_DRAWER_FIELD,
  workbenchColumns,
} from '#/components/workbench'
import { SERUM_MOUSE_STRAIN_CATEGORY_OPTIONS, SERUM_MOUSE_STRAIN_OPTIONS } from '#/utils/serumMouseOptions'
import { WORKBENCH_STUDY_TYPE_OPTIONS } from '#/utils/workbenchStudyTypes'

export const PLAN_STATUS_OPTIONS = ['规划中', '待冲击', '待剖鼠', '待建库', '待噬菌体', '待测序', '已完成', '已取消']
export const SCREENING_METHOD_TONES = Object.freeze({
  达普: 'primary',
  噬菌体: 'warning',
  Beacon: 'success',
  NGS: 'purple',
})

export const FIELDS = defineFields({
  sort_order: SORT_FIELD,
  priority: PRIORITY_FIELD,
  status: {
    label: '状态',
    type: 'select',
    options: PLAN_STATUS_OPTIONS,
    required: true,
    header: { type: 'enum', values: 'all', top: { query: 'status' } },
    list: { show: true, minWidth: 100, className: 'status-column-cell', tooltip: false },
    sheet: { width: 110 },
  },
  pm: {
    label: 'PM',
    type: 'user',
    max: 64,
    header: { type: 'enum', values: 'all', top: { query: 'pm' } },
    list: { show: true, minWidth: 90 },
    sheet: { width: 90 },
  },
  project_code: {
    label: '项目编号',
    type: 'text',
    max: 64,
    header: { type: 'text', values: 'recent' },
    list: { show: true, minWidth: 120 },
    sheet: { minWidth: 120 },
  },
  target_name: {
    label: '靶点名称',
    type: 'target',
    max: 128,
    header: { type: 'text', values: 'all', search: 'target', top: { query: 'target_name' } },
    list: { show: true, minWidth: 100 },
  },
  mouse_strain: {
    label: '小鼠品系',
    type: 'tags',
    options: SERUM_MOUSE_STRAIN_OPTIONS,
    max: 128,
    header: { type: 'csv', values: 'all', top: { query: 'mouse_strain' } },
    list: { show: true, minWidth: 120 },
    sheet: { minWidth: 140 },
  },
  mouse_count: {
    label: '只数',
    type: 'int',
    header: { type: 'number', values: 'all' },
    list: { show: true, minWidth: 80 },
    sheet: { width: 80 },
  },
  screening_methods: {
    label: '筛选方式',
    type: 'multi',
    options: ['达普', '噬菌体', 'Beacon', 'NGS'],
    header: { type: 'csv', values: 'all', top: { query: 'screening_methods' } },
    list: { show: true, minWidth: 150, tooltip: false },
    sheet: { minWidth: 160 },
    drawer: { wide: true },
  },
  screening_antigen: {
    label: '筛选抗原',
    type: 'textarea',
    max: 1000,
    header: { type: 'text', values: 'search', top: { query: 'screening_antigen', kind: 'contains' } },
    list: { show: true, minWidth: 120 },
    sheet: { minWidth: 140 },
    drawer: { wide: true, resize: 'none' },
  },
  boost_antigen: {
    label: '冲击免抗原',
    type: 'textarea',
    max: 1000,
    header: { type: 'text', values: 'search', top: { query: 'boost_antigen', kind: 'contains' } },
    list: { show: true, minWidth: 120 },
    sheet: { minWidth: 140 },
    drawer: { type: 'lines', wide: true },
  },
  harvest_date: {
    label: '剖鼠日期',
    type: 'date',
    header: { type: 'date', values: 'all', top: { range: 'harvestRange' } },
    list: { show: true, minWidth: 135, className: 'date-column-cell', tooltip: false },
    sheet: { width: 120 },
  },
  boost_date: {
    label: '冲击日期',
    type: 'date',
    header: { type: 'date', values: 'all', top: { range: 'boostRange' } },
    list: { show: true, minWidth: 135, className: 'date-column-cell', tooltip: false },
    sheet: { width: 120 },
  },
  remark: {
    label: '备注',
    type: 'textarea',
    max: 1000,
    header: { type: 'text', values: 'search', top: { query: 'remark', kind: 'contains' } },
    list: { minWidth: 140 },
    sheet: { minWidth: 180 },
    drawer: { wide: true },
  },
  owner: {
    label: '负责人',
    type: 'user',
    max: 64,
    header: { type: 'enum', values: 'all', top: { query: 'owner' } },
    list: { minWidth: 90 },
    sheet: { width: 90 },
  },
  immune_owner: {
    label: '免疫负责人',
    type: 'user',
    max: 64,
    header: { type: 'enum', values: 'all', top: { query: 'immune_owner' } },
    list: { minWidth: 110 },
    sheet: { width: 110 },
  },
  cell_collector: {
    label: '细胞收集人',
    type: 'user',
    max: 64,
    header: { type: 'enum', values: 'all', top: { query: 'cell_collector' } },
    list: { minWidth: 110 },
    sheet: { width: 110 },
  },
  experiment_id: {
    label: '实验号',
    type: 'text',
    max: 64,
    header: { type: 'text', values: 'recent' },
    list: { minWidth: 130 },
    sheet: { minWidth: 130 },
  },
  target_codes: {
    label: '靶点编号',
    type: 'target_codes',
    header: { type: 'csv', values: 'all' },
    list: { minWidth: 140 },
    sheet: { minWidth: 140 },
    drawer: { wide: true },
  },
  study_type: {
    label: '课题类型',
    type: 'select',
    options: WORKBENCH_STUDY_TYPE_OPTIONS,
    header: { type: 'enum', values: 'all', top: { query: 'study_type' } },
    list: { minWidth: 110 },
  },
  mouse_strain_category: {
    label: '归类鼠型',
    type: 'tags',
    options: SERUM_MOUSE_STRAIN_CATEGORY_OPTIONS,
    max: 128,
    header: { type: 'csv', values: 'all', top: { query: 'mouse_strain_category' } },
    list: { minWidth: 100 },
    sheet: { minWidth: 140 },
  },
  cage_position: {
    label: '笼位',
    type: 'text',
    max: 64,
    header: { type: 'text', values: 'recent', top: { query: 'cage_position', kind: 'contains' } },
    list: { minWidth: 100 },
    sheet: { minWidth: 100 },
  },
  mouse_nos: {
    label: '鼠号',
    type: 'textarea',
    max: 1000,
    header: { type: 'text', values: 'search', top: { query: 'mouse_nos', kind: 'contains' } },
    list: { minWidth: 140 },
    sheet: { minWidth: 180 },
    drawer: { wide: true },
  },
  serum_titer: {
    label: '血清效价',
    type: 'textarea',
    max: 1000,
    header: { type: 'text', values: 'search' },
    list: { minWidth: 110 },
    sheet: { minWidth: 180 },
    drawer: { sync: true },
  },
  immune_antigen: {
    label: '免疫抗原',
    type: 'textarea',
    max: 1000,
    header: { type: 'text', values: 'search', top: { query: 'immune_antigen', kind: 'contains' } },
    list: { minWidth: 140 },
    sheet: { minWidth: 140 },
    drawer: { wide: true, resize: 'none' },
  },
  boost_cells: {
    label: '冲击免细胞',
    type: 'textarea',
    max: 1000,
    header: { type: 'text', values: 'search' },
    list: { minWidth: 140 },
    sheet: { minWidth: 140 },
    drawer: { wide: true, resize: 'none' },
  },
  positive_cell_count: {
    label: '阳性细胞数',
    type: 'textarea',
    max: 64,
    header: { type: 'text', values: 'recent' },
    list: { minWidth: 110 },
    sheet: { minWidth: 110 },
    drawer: { sync: true },
  },
  plate_nos: {
    label: '板号',
    type: 'textarea',
    max: 1000,
    header: { type: 'text', values: 'search', top: { query: 'plate_nos', kind: 'contains' } },
    list: { minWidth: 140 },
    sheet: { minWidth: 140 },
    drawer: { wide: true },
  },
})

export const WORKBENCH_COLUMNS = workbenchColumns(FIELDS, [
  'sort_order', 'priority', 'status', 'pm', 'project_code', 'target_name', 'mouse_strain', 'mouse_count',
  'screening_methods', 'screening_antigen', 'boost_antigen', 'harvest_date', 'boost_date', 'remark', 'owner',
  'immune_owner', 'cell_collector', 'experiment_id', 'target_codes', 'study_type', 'mouse_strain_category',
  'cage_position', 'mouse_nos', 'serum_titer', 'immune_antigen', 'boost_cells', 'positive_cell_count', 'plate_nos',
])

export const SHEET_COLUMNS = sheetColumns(FIELDS, [
  'sort_order', 'priority', 'target_codes', 'project_code', 'target_name', 'pm', 'study_type', 'mouse_strain',
  'screening_methods', 'harvest_date', 'mouse_count', 'mouse_nos', 'serum_titer', 'immune_antigen', 'boost_date',
  'boost_antigen', 'boost_cells', 'screening_antigen', 'positive_cell_count', 'plate_nos', 'owner', 'immune_owner',
  'cell_collector', 'mouse_strain_category', 'cage_position', 'remark', 'experiment_id', 'status',
])

export const EDITOR_SECTIONS = editorSections(FIELDS, [
  { title: '队列 / 状态', queue: true, fields: ['status', 'priority', 'owner', 'sort_order'] },
  { title: '项目', fields: ['project_code', 'experiment_id', 'pm', 'study_type', TARGET_DRAWER_FIELD, 'target_codes'] },
  { title: '小鼠', fields: ['mouse_strain_category', 'mouse_strain', 'cage_position', 'mouse_count', 'mouse_nos'] },
  {
    title: '筛选',
    fields: ['screening_methods', 'immune_antigen', 'screening_antigen', 'serum_titer', 'positive_cell_count', 'plate_nos'],
  },
  {
    title: '日程',
    fields: ['harvest_date', 'boost_date', 'immune_owner', 'cell_collector', 'boost_antigen', 'boost_cells', 'remark'],
  },
])

export const HEADER_MENU_COLUMNS = headerMenuColumns(FIELDS)

// 本地存储键已发布，不要改值
export const VIEW_PREFS_KEY = 'discoveryWorkbenchViewPrefs.v4'
export const SHEET_COLUMN_ORDER = createColumnOrder(
  'discoveryWorkbenchSheetColumnOrder.v4',
  SHEET_COLUMNS,
  { pinFirstKey: 'sort_order' },
)

export const SHEET_HEADER_ALIASES = Object.freeze({
  序号: 'sort_order',
  剖鼠: 'harvest_date',
  剖鼠日: 'harvest_date',
  冲击免: 'boost_date',
  冲击免日: 'boost_date',
  冲击免日期: 'boost_date',
  冲击抗原: 'boost_antigen',
  小鼠只数: 'mouse_count',
  品系: 'mouse_strain',
})
