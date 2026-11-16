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
import { WORKBENCH_PLAN_STATUS_OPTIONS } from '#/utils/serumProjectStatus'
import { WORKBENCH_STUDY_TYPE_OPTIONS } from '#/utils/workbenchStudyTypes'

export const PLAN_STATUS_OPTIONS = [...WORKBENCH_PLAN_STATUS_OPTIONS]
const YES_NO_OPTIONS = ['是', '否']
/** 开展后这些字段以正式项目为准，工作台只读（项目编号除外，改了会同步过去）。 */
export const ALIGNED_FIELDS = new Set([
  'experiment_id',
  'target_codes',
  'target_name',
  'owner',
  'pm',
  'study_type',
  'remark',
  'mouse_strain',
  'mouse_strain_category',
  'reviewer',
])

export const FIELDS = defineFields({
  sort_order: SORT_FIELD,
  priority: PRIORITY_FIELD,
  status: {
    label: '状态',
    type: 'text',
    header: { type: 'enum', values: 'all', top: { query: 'display_status' } },
    list: { show: true, minWidth: 110, className: 'status-column-cell', tooltip: false },
  },
  plan_status: {
    label: '状态',
    type: 'select',
    options: PLAN_STATUS_OPTIONS,
    required: true,
    header: { alias: 'status' },
    sheet: { width: 110 },
    drawer: { tone: 'status' },
  },
  can_start: {
    label: '可否开展',
    type: 'select',
    options: YES_NO_OPTIONS,
    required: true,
    header: { type: 'enum', values: 'all', top: { query: 'can_start' } },
    list: { show: true, minWidth: 90, className: 'status-column-cell', tooltip: false },
    sheet: { width: 100 },
    drawer: { label: '可开展', tone: 'yesno', filterable: false },
  },
  reviewer: {
    label: '审核人',
    type: 'user',
    max: 64,
    header: { type: 'enum', values: 'all', top: { query: 'reviewer' } },
    list: { minWidth: 90 },
    sheet: { width: 90 },
  },
  review_status: {
    label: '审核结果',
    type: 'select',
    options: ['未审', '已通过', '驳回'],
    required: true,
    header: { type: 'enum', values: 'all', top: { query: 'review_status' } },
    list: { show: true, minWidth: 90, className: 'status-column-cell', tooltip: false },
    sheet: { width: 90 },
    drawer: { tone: 'review' },
  },
  project_code: {
    label: '免疫项目号',
    type: 'text',
    max: 64,
    header: { type: 'text', values: 'recent' },
    list: { show: true, minWidth: 120 },
    drawer: { label: '项目编号' },
  },
  project_set_code: {
    label: '项目集编号',
    type: 'text',
    max: 64,
    header: { type: 'text', values: 'recent' },
    list: { minWidth: 120 },
  },
  pm: {
    label: 'PM',
    type: 'user',
    max: 64,
    header: { type: 'enum', values: 'all', top: { query: 'pm' } },
    list: { show: true, minWidth: 72 },
    sheet: { width: 90 },
  },
  owner: {
    label: '开展人',
    type: 'user',
    max: 64,
    header: { type: 'enum', values: 'all', top: { query: 'owner' } },
    list: { minWidth: 90 },
    sheet: { width: 90 },
  },
  target_name: {
    label: '靶点名称',
    type: 'target',
    max: 128,
    list: { show: true, minWidth: 100 },
  },
  target_codes: {
    label: '靶点编号',
    type: 'target_codes',
    list: { minWidth: 140 },
    drawer: { wide: true },
  },
  study_type: {
    label: '课题类型',
    type: 'select',
    options: WORKBENCH_STUDY_TYPE_OPTIONS,
    header: { type: 'enum', values: 'all', top: { query: 'study_type' } },
    list: { minWidth: 110 },
  },
  immuno_method: {
    label: '免疫方式',
    type: 'multi',
    options: ['蛋白', 'DNA', 'LNP', '细胞', '混合'],
    header: { type: 'csv', values: 'all', top: { query: 'immuno_method' } },
    list: { minWidth: 140 },
    sheet: { minWidth: 140 },
  },
  species_cross: {
    label: '种属交叉',
    type: 'multi',
    options: ['人', '猴', '鼠', '狗', '猫', '空白'],
    header: { type: 'csv', values: 'all', top: { query: 'species_cross' } },
    list: { minWidth: 160 },
    sheet: { minWidth: 160 },
    drawer: { wide: true },
  },
  remark: {
    label: '备注',
    type: 'textarea',
    max: 255,
    header: { type: 'text', values: 'search' },
    list: { show: true, minWidth: 120 },
    drawer: { wide: true },
  },
  mouse_scheme_no: {
    label: '小鼠方案号',
    type: 'text',
    max: 64,
    header: { type: 'text', values: 'recent' },
    list: { minWidth: 120 },
  },
  mouse_strain_category: {
    label: '归类鼠型',
    type: 'select',
    options: SERUM_MOUSE_STRAIN_CATEGORY_OPTIONS,
    list: { show: true, minWidth: 90 },
  },
  mouse_strain: {
    label: '小鼠品系',
    type: 'select',
    options: SERUM_MOUSE_STRAIN_OPTIONS,
    list: { minWidth: 110 },
    drawer: { filterable: true },
  },
  mouse_count: {
    label: '数量',
    type: 'text',
    max: 32,
    header: { type: 'text', values: 'all' },
    list: { minWidth: 80 },
    sheet: { width: 80 },
  },
  mouse_zygosity: {
    label: '纯合/杂合',
    type: 'select',
    options: ['纯合', '杂合', '混合'],
    header: { type: 'enum', values: 'all', top: { query: 'mouse_zygosity' } },
    list: { minWidth: 90 },
    sheet: { width: 90 },
  },
  mouse_birth_date: {
    label: '出生日期',
    type: 'date',
    header: { type: 'date', values: 'all' },
    list: { minWidth: 110 },
    sheet: { width: 110 },
  },
  mouse_age_weeks: {
    label: '周龄',
    type: 'text',
    max: 32,
    list: { minWidth: 80 },
    sheet: { width: 80 },
    drawer: { type: 'age' },
  },
  mouse_region: {
    label: '提供地区',
    type: 'select',
    options: ['北京', '海门', '客户'],
    header: { type: 'enum', values: 'all', top: { query: 'mouse_region' } },
    list: { minWidth: 100 },
  },
  mouse_room: {
    label: '房间号',
    type: 'text',
    max: 64,
    header: { type: 'text', values: 'recent' },
    list: { minWidth: 90 },
    sheet: { width: 90 },
  },
  mouse_status: {
    label: '小鼠运输',
    type: 'select',
    options: ['未定', '扩繁中', '可运', '在途', '已到'],
    required: true,
    header: { type: 'enum', values: 'all', top: { query: 'mouse_status' } },
    list: { show: true, minWidth: 100, className: 'status-column-cell', tooltip: false },
    sheet: { width: 90 },
    drawer: { label: '运输状态', tone: 'mouse' },
  },
  mouse_arrive_date: {
    label: '到鼠时间',
    type: 'date',
    header: { type: 'date', values: 'all' },
    list: { minWidth: 110 },
    sheet: { width: 110 },
  },
  mouse_expand_requested: {
    label: '代下扩繁',
    type: 'select',
    options: YES_NO_OPTIONS,
    header: { type: 'enum', values: 'all', top: { query: 'mouse_expand_requested' } },
    list: { minWidth: 110 },
    sheet: { width: 110 },
    drawer: { tone: 'yesno', filterable: false },
  },
  mouse_remark: {
    label: '小鼠备注',
    type: 'textarea',
    max: 255,
    header: { type: 'text', values: 'search' },
    list: { minWidth: 160 },
    sheet: { minWidth: 160 },
    drawer: { wide: true },
  },
  antigen_source: {
    label: '抗原来源',
    type: 'select',
    options: ['内部制备', '外购', '客户提供'],
    header: { type: 'enum', values: 'all', top: { query: 'antigen_source' } },
    list: { minWidth: 110 },
  },
  antigen_ready: {
    label: '抗原到货',
    type: 'select',
    options: YES_NO_OPTIONS,
    required: true,
    header: { type: 'enum', values: 'all', top: { query: 'antigen_ready' } },
    list: { show: true, minWidth: 90, className: 'status-column-cell', tooltip: false },
    sheet: { width: 110 },
    drawer: { tone: 'yesno', filterable: false },
  },
  antigen_eta: {
    label: '抗原预计日',
    type: 'date',
    header: { type: 'text', values: 'recent' },
    list: { minWidth: 110 },
    sheet: { width: 110 },
  },
  lnp_ordered: {
    label: 'LNP下单',
    type: 'select',
    options: YES_NO_OPTIONS,
    header: { type: 'enum', values: 'all', top: { query: 'lnp_ordered' } },
    list: { minWidth: 110 },
    sheet: { width: 110 },
    drawer: { tone: 'yesno', filterable: false },
  },
  cell_prep_status: {
    label: '冲击细胞',
    type: 'select',
    options: ['未开始', '进行中', '已完成', '不需要'],
    header: { type: 'enum', values: 'all', top: { query: 'cell_prep_status' } },
    list: { minWidth: 110 },
  },
  antigen_remark: {
    label: '抗原备注',
    type: 'textarea',
    max: 255,
    header: { type: 'text', values: 'search' },
    list: { minWidth: 160 },
    sheet: { minWidth: 160 },
    drawer: { wide: true },
  },
  experiment_id: {
    label: '实验号',
    type: 'text',
    max: 64,
    header: { type: 'text', values: 'recent' },
    list: { minWidth: 190 },
    sheet: { width: 190, readonly: true, lockHint: '实验号由系统生成，改项目编号时自动更新' },
  },
})

export const WORKBENCH_COLUMNS = workbenchColumns(FIELDS, [
  'sort_order', 'target_name', 'pm', 'mouse_strain_category', 'project_code', 'remark', 'status', 'mouse_status',
  'antigen_ready', 'review_status', 'can_start', 'priority', 'target_codes', 'project_set_code', 'study_type',
  'species_cross', 'owner', 'reviewer', 'immuno_method', 'mouse_scheme_no', 'mouse_strain', 'mouse_count',
  'mouse_zygosity', 'mouse_birth_date', 'mouse_age_weeks', 'mouse_region', 'mouse_room', 'mouse_arrive_date',
  'mouse_remark', 'antigen_source', 'antigen_eta', 'mouse_expand_requested', 'lnp_ordered', 'cell_prep_status',
  'antigen_remark', 'experiment_id',
])

export const SHEET_COLUMNS = sheetColumns(FIELDS, [
  'sort_order', 'priority', 'target_name', 'target_codes', 'pm', 'project_set_code', 'project_code', 'study_type',
  'species_cross', 'owner', 'reviewer', 'review_status', 'immuno_method', 'remark', 'mouse_scheme_no',
  'mouse_strain_category', 'mouse_strain', 'mouse_count', 'mouse_zygosity', 'mouse_birth_date', 'mouse_age_weeks',
  'mouse_region', 'mouse_room', 'mouse_status', 'mouse_arrive_date', 'mouse_remark', 'antigen_source', 'antigen_ready',
  'antigen_eta', 'mouse_expand_requested', 'lnp_ordered', 'cell_prep_status', 'antigen_remark', 'can_start',
  'plan_status', 'experiment_id',
])

export const EDITOR_SECTIONS = editorSections(FIELDS, [
  {
    title: '队列 / 状态',
    queue: true,
    fields: ['priority', 'plan_status', 'can_start', 'sort_order', 'reviewer', 'review_status'],
  },
  { title: '身份', fields: ['project_code', 'project_set_code', 'pm', 'owner', TARGET_DRAWER_FIELD, 'target_codes'] },
  {
    title: '方案要点',
    fields: ['study_type', 'immuno_method', 'mouse_strain_category', 'mouse_strain', 'species_cross', 'remark'],
  },
  {
    title: '小鼠后勤',
    fields: [
      'mouse_scheme_no', 'mouse_count', 'mouse_zygosity', 'mouse_birth_date', 'mouse_age_weeks', 'mouse_region',
      'mouse_room', 'mouse_status', 'mouse_arrive_date', 'mouse_expand_requested', 'mouse_remark',
    ],
  },
  {
    title: '抗原',
    fields: ['antigen_source', 'antigen_ready', 'antigen_eta', 'lnp_ordered', 'cell_prep_status', 'antigen_remark'],
  },
])

/** 靶点、品系沿用顶部筛选（品系显示的是方案分组合并值）；周龄是按出生日期推算的，不放表头。 */
export const HEADER_MENU_COLUMNS = headerMenuColumns(FIELDS)

// 本地存储键已发布，不要改值
export const VIEW_PREFS_KEY = 'serumWorkbenchViewPrefs'
export const SHEET_COLUMN_ORDER = createColumnOrder('workbenchSheetColumnOrder', SHEET_COLUMNS, {
  pinFirstKey: 'sort_order',
})

export const SHEET_HEADER_ALIASES = Object.freeze({
  序号: 'sort_order',
  优先级排序: 'sort_order',
  项目编号: 'project_code',
  运输状态: 'mouse_status',
  抗原到货情况: 'antigen_ready',
  是否代下扩繁: 'mouse_expand_requested',
  LNP是否下单: 'lnp_ordered',
  冲击细胞准备: 'cell_prep_status',
  是否可开展: 'can_start',
})
