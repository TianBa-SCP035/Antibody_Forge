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
} from '#/components/workbench';
import { SERUM_MOUSE_STRAIN_OPTIONS } from '#/utils/serumMouseOptions';
import { WORKBENCH_STUDY_TYPE_OPTIONS } from '#/utils/workbenchStudyTypes';

/** 列顺序、列宽等视图偏好的本地存储键，已发布不要改值 */
export const SYNTHESIS_VIEW_PREFS_KEY = 'discoverySynthesisViewPrefs.v8';

export const STATUS_OPTIONS = [
  '待下单',
  '合成中',
  '待检测',
  '检测中',
  '已完成',
  '已取消',
];
export const AFFINITY_STATUS_OPTIONS = [
  '亲和力待检测',
  '亲和力检测中',
  '亲和力已完成',
];
export const FLOW_STATUS_OPTIONS = [
  '流式待检测',
  '流式已完成',
  '流式不适用',
];
/** 状态筛选的组合项「亲和力X且流式Y」：两项都满足，与后端 _assay_combo_term 一致。 */
export const assayComboTerm = (affinity, flow) => `${affinity}且${flow}`;
const ASSAY_COMBO_TERMS = AFFINITY_STATUS_OPTIONS.flatMap((affinity) =>
  FLOW_STATUS_OPTIONS.map((flow) => assayComboTerm(affinity, flow)),
);
export const STATUS_FILTER_GROUPS = [
  { label: '主状态', options: STATUS_OPTIONS },
  { label: '亲和力', options: AFFINITY_STATUS_OPTIONS },
  { label: '流式', options: FLOW_STATUS_OPTIONS },
];
const TARGET_TYPE_OPTIONS = [
  '分泌型',
  'I型跨膜',
  'II型跨膜',
  'III型跨膜',
  'IV型跨膜',
  '单次跨膜',
  '多次穿膜',
  'GPI锚定',
  '细胞膜蛋白',
  '外周膜蛋白',
  '脂锚定蛋白',
  '胞内蛋白',
  '其他',
];
const SELECTION_METHOD_OPTIONS = [
  'EYE',
  'DS',
  'DS_JX',
  'DS_RH',
  'JX_P',
  'JX_C',
  'RH_P',
  'RH_C',
  'D',
  'D_JX',
  'D_RH',
  'D模型',
  'D模型-3轮',
  'P',
];
const ENG_TYPE_OPTIONS = [
  '亲和力',
  '人源化',
  '去PTM',
  'Tm',
  'PI',
  '亲水性',
  '稳定性',
  'CIC',
  'HIC',
  'Tagg',
  '糖基化',
  '氧化风险',
  '脱酰胺风险',
  '同家族交叉',
  'VHH序列改造',
  '改亚型',
  '其他',
];
const ENG_METHOD_OPTIONS = [
  'AI',
  'NGS姐妹克隆',
  '理性设计',
  '饱和突变',
  '其他',
];

export const QUEUE_TERMINAL_STATUSES = ['已完成', '已取消'];

export const CLAIM_RETURN_DAYS = 7;

export const STATUS_VIEWS = [
  {
    key: '',
    label: '全部批次',
    hint: '全部合成与验证记录',
    valueKey: 'all',
    tone: 'all',
    step: '00',
  },
  {
    key: 'synthesizing',
    label: '合成中',
    hint: '已下合成订单，等待到货',
    valueKey: 'synthesizing',
    tone: 'ongoing',
    step: '01',
  },
  {
    key: 'assay',
    label: '待测 / 检测中',
    hint: '已到货待检或流式/亲和力验证中',
    valueKey: 'assay',
    tone: 'ongoing',
    step: '02',
  },
  {
    key: 'completed',
    label: '已完成',
    hint: '已完成挑选序列实验验证',
    valueKey: 'completed',
    tone: 'completed',
    step: '03',
  },
  {
    key: 'engineering',
    label: '序列改造',
    hint: '亲和力、人源化与理化改造批次',
    valueKey: 'engineering',
    tone: 'planned',
    step: '04',
  },
];

export const PM_EDIT_FIELD_KEYS = new Set([
  'priority',
  'sort_order',
  'order_kind',
  'supply_mode',
  'owner',
  'project_code',
  'study_type',
  'target',
  'target_name',
  'target_codes',
  'mouse_strain',
  'eng_type',
  'eng_method',
  'eng_parent_seq',
  'eng_requirement',
  'remark',
]);

export const AFFINITY_EDIT_FIELD_KEYS = new Set([
  'affinity_status',
  'affinity_owner',
  'affinity_result',
  'affinity_date',
  'report_reason',
]);

export const FLOW_EDIT_FIELD_KEYS = new Set([
  'flow_status',
  'flow_date',
  'flow_note',
]);

/** 改造实验员只管改造 / 内部转染 / 改亚型的工单，下列字段之外都能改。 */
export const ENG_LOCKED_FIELD_KEYS = new Set([
  'owner',
  'target_color',
  'synthesis_order_id',
  'order_sender',
  ...AFFINITY_EDIT_FIELD_KEYS,
  ...FLOW_EDIT_FIELD_KEYS,
]);
const ENG_SUPPLY_MODES = new Set(['内部转染', '改亚型']);
export const ENG_ROW_MESSAGE = '改造实验员只能操作改造、内部转染或改亚型的工单';

export function isEngineeringRow(row) {
  return row?.order_kind === '改造' || ENG_SUPPLY_MODES.has(row?.supply_mode);
}

/** 新建时先在页面上填，下列字段齐了才真正保存；target 指靶点名称或编号任填其一。 */
export const CREATE_REQUIRED_FIELDS = [
  ['order_kind', '订单性质'],
  ['supply_mode', '供应方式'],
  ['mouse_strain', '小鼠品系'],
  ['pm', 'PM'],
  ['target', '靶点'],
];

export const ENGINEERING_REQUIRED_FIELDS = [
  ['eng_type', '改造类型'],
  ['eng_method', '改造方式'],
  ['eng_parent_seq', '母本序列'],
  ['eng_requirement', '改造要求'],
];

/** 工单保存前不能填的字段：检测进度、状态和排序都要等工单存在后再改。 */
export const DRAFT_LOCKED_FIELD_KEYS = new Set([
  'status',
  'sort_order',
  'synthesis_order_id',
  'order_sender',
  ...AFFINITY_EDIT_FIELD_KEYS,
  ...FLOW_EDIT_FIELD_KEYS,
]);

export const FIELDS = defineFields({
  sort_order: SORT_FIELD,
  priority: PRIORITY_FIELD,
  status: {
    label: '状态',
    type: 'select',
    options: STATUS_OPTIONS,
    required: true,
    header: { type: 'enum', values: 'all', top: { query: 'status', topOnly: ASSAY_COMBO_TERMS } },
    list: { show: true, minWidth: 132, className: 'status-column-cell', tooltip: false },
    sheet: { width: 126 },
  },
  target_name: {
    label: '靶点名称',
    type: 'target',
    max: 128,
    header: { type: 'text', label: '靶点', values: 'all', search: 'target', color: true, top: { query: 'target_name' } },
    list: { label: '靶点', show: true, minWidth: 110 },
    sheet: { minWidth: 120 },
  },
  target_type: {
    label: '靶点类型',
    type: 'select',
    options: TARGET_TYPE_OPTIONS,
    allowCreate: true,
    max: 64,
    header: { type: 'enum', values: 'all', top: { query: 'target_type', topOnly: ['非分泌型'] } },
    list: { show: true, minWidth: 105, className: 'status-column-cell', tooltip: false },
    sheet: { width: 108 },
  },
  mouse_strain: {
    label: '小鼠品系',
    type: 'tags',
    options: SERUM_MOUSE_STRAIN_OPTIONS,
    max: 128,
    header: { type: 'csv', values: 'all', top: { query: 'mouse_strain' } },
    list: { show: true, minWidth: 100 },
    sheet: { minWidth: 115 },
  },
  synthesis_code: {
    label: '送测转码',
    type: 'text',
    max: 64,
    header: { type: 'text', values: 'recent', top: { query: 'synthesis_code', kind: 'codes' } },
    list: { show: true, minWidth: 150 },
    sheet: { minWidth: 150 },
    drawer: { solo: true },
  },
  order_no: {
    label: '订单号',
    type: 'text',
    max: 64,
    header: { type: 'text', values: 'recent', top: { query: 'order_no', kind: 'codes' } },
    list: { minWidth: 150 },
    sheet: { minWidth: 150 },
  },
  synthetic_count: {
    label: '合成个数',
    type: 'int',
    header: { type: 'number', values: 'all' },
    list: { show: true, minWidth: 90 },
    sheet: { width: 92 },
  },
  synthetic_date: {
    label: '合成日期',
    type: 'date',
    header: { type: 'date', values: 'all', top: { range: 'syntheticDateRange' } },
    list: { show: true, minWidth: 110 },
    sheet: { width: 120 },
  },
  arrival_count: {
    label: '到货个数',
    type: 'int',
    header: { type: 'number', values: 'all' },
    list: { show: true, minWidth: 90 },
    sheet: { width: 92 },
  },
  arrival_date: {
    label: '到货日期',
    type: 'date',
    header: { type: 'date', values: 'all', top: { range: 'arrivalDateRange' } },
    list: { show: true, minWidth: 110 },
    sheet: { width: 120 },
  },
  affinity_date: {
    label: '亲和力日期',
    type: 'date',
    header: { type: 'date', values: 'all', top: { range: 'affinityDateRange' } },
    list: { show: true, minWidth: 110 },
    sheet: { width: 120 },
  },
  affinity_owner: {
    label: '亲和力人员',
    type: 'users',
    max: 64,
    header: { type: 'csv', values: 'all', top: { query: 'affinity_owner' } },
    list: { minWidth: 105 },
    sheet: { width: 105 },
  },
  flow_date: {
    label: '流式日期',
    type: 'date',
    header: { type: 'date', values: 'all', top: { range: 'flowDateRange' } },
    list: { show: true, minWidth: 120 },
    sheet: { width: 120 },
  },
  owner: {
    label: '负责人',
    type: 'user',
    max: 64,
    header: { type: 'enum', values: 'all', top: { query: 'owner' } },
    list: { show: true, minWidth: 96 },
    sheet: { width: 100 },
  },
  selection_method: {
    label: '挑选方式',
    type: 'tags',
    options: SELECTION_METHOD_OPTIONS,
    max: 128,
    header: { type: 'csv', values: 'all', top: { query: 'selection_method' } },
    list: { minWidth: 100 },
    sheet: { minWidth: 115 },
  },
  is_rechoose: {
    label: '是否补挑',
    type: 'select',
    options: ['是', '否'],
    header: { type: 'enum', values: 'all', top: { query: 'is_rechoose' } },
    list: { minWidth: 90, tooltip: false },
    sheet: { width: 96 },
  },
  batch_label: {
    label: '工单批次',
    type: 'text',
    max: 255,
    header: { type: 'text', values: 'recent', top: { query: 'batch_label', kind: 'codes' } },
    list: { minWidth: 180 },
    sheet: { minWidth: 180 },
    drawer: { wide: true },
  },
  remark: {
    label: '检测备注',
    type: 'textarea',
    max: 1000,
    header: { type: 'text', values: 'search', top: { query: 'remark', kind: 'contains' } },
    list: { minWidth: 160 },
    sheet: { minWidth: 160 },
    drawer: { wide: true },
  },
  affinity_result: {
    label: '亲和力结果',
    type: 'select',
    options: ['正常', '阳性极少', '全阴'],
    header: { type: 'enum', values: 'all', top: { query: 'affinity_result' } },
    list: { minWidth: 96 },
    sheet: { width: 100 },
  },
  report_reason: {
    label: '未出原因',
    type: 'textarea',
    max: 500,
    header: { type: 'text', values: 'search', top: { query: 'report_reason', kind: 'contains' } },
    list: { minWidth: 170 },
    sheet: { minWidth: 170 },
    drawer: { wide: true },
  },
  flow_note: {
    label: '流式说明',
    type: 'textarea',
    max: 500,
    header: { type: 'text', values: 'search', top: { query: 'flow_note', kind: 'contains' } },
    list: { minWidth: 170 },
    sheet: { minWidth: 170 },
    drawer: { wide: true },
  },
  synthetic_corp: {
    label: '合成公司',
    type: 'select',
    options: ['君跻', '擎科', '金斯瑞', '内部'],
    allowCreate: true,
    max: 64,
    header: { type: 'enum', values: 'all', top: { query: 'synthetic_corp' } },
    list: { minWidth: 92 },
    sheet: { width: 100 },
  },
  order_sender: {
    label: '下单人',
    type: 'text',
    header: { type: 'enum', values: 'all', top: { query: 'order_sender' } },
    list: { minWidth: 130 },
    sheet: { readonly: true, lockHint: '下单人由 One 同步，不能修改', minWidth: 130 },
  },
  order_kind: {
    label: '订单性质',
    type: 'select',
    options: ['常规合成', '改造'],
    required: true,
    header: { type: 'enum', values: 'all', top: { query: 'order_kind' } },
    list: { minWidth: 96 },
    sheet: { width: 100 },
  },
  supply_mode: {
    label: '供应方式',
    type: 'select',
    options: ['合成到货', '内部转染', '改亚型'],
    required: true,
    header: { type: 'enum', values: 'all', top: { query: 'supply_mode' } },
    list: { minWidth: 96 },
    sheet: { width: 100 },
  },
  target_codes: {
    label: '靶点编号',
    type: 'target_codes',
    header: { type: 'csv', values: 'all' },
    list: { minWidth: 110 },
    sheet: { minWidth: 115 },
    drawer: { wide: true },
  },
  project_code: {
    label: '项目编号',
    type: 'text',
    max: 64,
    header: { type: 'text', values: 'recent', top: { query: 'project_code', kind: 'codes' } },
    list: { minWidth: 120 },
    sheet: { minWidth: 120 },
  },
  pm: {
    label: 'PM',
    type: 'user',
    max: 64,
    header: { type: 'enum', values: 'all', top: { query: 'pm' } },
    list: { minWidth: 90 },
    sheet: { width: 95 },
  },
  study_type: {
    label: '课题类型',
    type: 'select',
    options: WORKBENCH_STUDY_TYPE_OPTIONS,
    header: { type: 'enum', values: 'all', top: { query: 'study_type' } },
    list: { minWidth: 110 },
    sheet: { width: 110 },
  },
  eng_type: {
    label: '改造类型',
    type: 'tags',
    options: ENG_TYPE_OPTIONS,
    max: 128,
    header: { type: 'csv', values: 'all', top: { query: 'eng_type' } },
    list: { minWidth: 120 },
    sheet: { minWidth: 130 },
  },
  eng_method: {
    label: '改造方式',
    type: 'tags',
    options: ENG_METHOD_OPTIONS,
    max: 128,
    header: { type: 'csv', values: 'all', top: { query: 'eng_method' } },
    list: { minWidth: 120 },
    sheet: { minWidth: 125 },
  },
  eng_parent_seq: {
    label: '改造序列或母本',
    type: 'textarea',
    max: 500,
    header: { type: 'text', values: 'search' },
    list: { minWidth: 170 },
    sheet: { minWidth: 170 },
    drawer: { label: '母本序列', wide: true },
  },
  eng_requirement: {
    label: '改造要求',
    type: 'textarea',
    max: 1000,
    header: { type: 'text', values: 'search' },
    list: { minWidth: 170 },
    sheet: { minWidth: 170 },
    drawer: { wide: true },
  },
  eng_result: {
    label: '改造结果',
    type: 'textarea',
    max: 500,
    header: { type: 'text', values: 'search' },
    list: { minWidth: 160 },
    sheet: { minWidth: 160 },
    drawer: { wide: true },
  },
});

export const WORKBENCH_COLUMNS = workbenchColumns(FIELDS, [
  'sort_order', 'priority', 'status', 'target_name', 'target_type', 'mouse_strain', 'synthesis_code', 'order_no',
  'synthetic_count', 'synthetic_date', 'arrival_count', 'arrival_date', 'affinity_date', 'affinity_owner', 'flow_date',
  'owner', 'selection_method', 'is_rechoose', 'batch_label', 'remark', 'affinity_result', 'report_reason', 'flow_note',
  'synthetic_corp', 'order_sender', 'order_kind', 'supply_mode', 'target_codes', 'project_code', 'pm', 'study_type',
  'eng_type', 'eng_method', 'eng_parent_seq', 'eng_requirement', 'eng_result',
]);

export const SHEET_COLUMNS = sheetColumns(FIELDS, [
  'sort_order', 'priority', 'status', 'target_name', 'target_type', 'mouse_strain', 'selection_method', 'is_rechoose',
  'synthesis_code', 'order_no', 'batch_label', 'synthetic_count', 'synthetic_date', 'arrival_count', 'arrival_date',
  'remark', 'affinity_owner', 'affinity_date', 'affinity_result', 'report_reason', 'flow_date', 'flow_note', 'owner',
  'synthetic_corp', 'order_sender', 'order_kind', 'supply_mode', 'target_codes', 'project_code', 'pm', 'study_type',
  'eng_type', 'eng_method', 'eng_parent_seq', 'eng_requirement', 'eng_result',
]);

export const SHEET_COLUMN_ORDER = createColumnOrder(
  'discoverySynthesisSheetColumnOrder.v12',
  SHEET_COLUMNS,
  { pinFirstKey: 'sort_order' },
);

const [QUEUE_SECTION, ...DETAIL_SECTIONS] = editorSections(FIELDS, [
  {
    title: '状态 / 归属',
    queue: true,
    fields: ['status', 'priority', 'owner', 'sort_order', 'order_kind', 'supply_mode'],
  },
  {
    title: '项目信息',
    fields: ['project_code', 'mouse_strain', 'pm', 'study_type', TARGET_DRAWER_FIELD, 'target_codes', 'remark'],
  },
  {
    title: '合成订单',
    fields: [
      'selection_method', 'is_rechoose', 'order_sender', 'synthesis_code', 'order_no', 'synthetic_corp',
      'synthetic_count', 'synthetic_date', 'batch_label',
    ],
  },
  {
    title: '到货与验证',
    fields: [
      'arrival_count', 'arrival_date', 'affinity_owner', 'affinity_result', 'affinity_date', 'report_reason',
      'flow_date', 'flow_note',
    ],
  },
]);
const [ENGINEERING_SECTION] = editorSections(FIELDS, [
  {
    title: '改造信息',
    accent: true,
    fields: ['eng_type', 'eng_method', 'eng_parent_seq', 'eng_requirement', 'eng_result'],
  },
]);
export const EDITOR_SECTIONS = [QUEUE_SECTION, ...DETAIL_SECTIONS];
/** 改造类工单：改造信息紧跟在状态分组后面。 */
export const ENGINEERING_EDITOR_SECTIONS = [QUEUE_SECTION, ENGINEERING_SECTION, ...DETAIL_SECTIONS];

export const HEADER_MENU_COLUMNS = headerMenuColumns(FIELDS);

export const SHEET_HEADER_ALIASES = Object.freeze({
  序号: 'sort_order',
  靶点: 'target_name',
  鼠型: 'mouse_strain',
  补挑: 'is_rechoose',
  送合成转码: 'synthesis_code',
  合成批号: 'synthesis_code',
  合成公司订单号: 'order_no',
  合成订单号: 'order_no',
  条数: 'synthetic_count',
  合成时间: 'synthetic_date',
  送合成日期: 'synthetic_date',
  上清交付数: 'arrival_count',
  上清交付数目: 'arrival_count',
  上清到货日期: 'arrival_date',
  亲和力是否全阴: 'affinity_result',
  项目负责人: 'owner',
  流式检测说明: 'flow_note',
  流式备注: 'flow_note',
  检测说明: 'flow_note',
  未出报告原因: 'report_reason',
  亲和力未出报告原因: 'report_reason',
  工单: 'batch_label',
  工单批次说明: 'batch_label',
  序列: 'eng_parent_seq',
  母本序列: 'eng_parent_seq',
  要求: 'eng_requirement',
  改造进度: 'eng_result',
  备注: 'remark',
});
