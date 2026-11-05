import { createColumnOrder } from '#/components/workbench';
import { SERUM_MOUSE_STRAIN_OPTIONS } from '#/utils/serumMouseOptions';
import { WORKBENCH_PRIORITY_OPTIONS } from '#/utils/serumProjectStatus';
import { WORKBENCH_STUDY_TYPE_OPTIONS } from '#/utils/workbenchStudyTypes';

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
export const ASSAY_COMBO_TERMS = AFFINITY_STATUS_OPTIONS.flatMap((affinity) =>
  FLOW_STATUS_OPTIONS.map((flow) => assayComboTerm(affinity, flow)),
);
export const STATUS_FILTER_GROUPS = [
  { label: '主状态', options: STATUS_OPTIONS },
  { label: '亲和力', options: AFFINITY_STATUS_OPTIONS },
  { label: '流式', options: FLOW_STATUS_OPTIONS },
];
export const PRIORITY_OPTIONS = [...WORKBENCH_PRIORITY_OPTIONS];
export const ORDER_KIND_OPTIONS = ['常规合成', '改造'];
export const SUPPLY_MODE_OPTIONS = ['合成到货', '内部转染', '改亚型'];
export const AFFINITY_RESULT_OPTIONS = ['正常', '阳性极少', '全阴'];
export const MOUSE_STRAIN_OPTIONS = [...SERUM_MOUSE_STRAIN_OPTIONS];
export const STUDY_TYPE_OPTIONS = [...WORKBENCH_STUDY_TYPE_OPTIONS];
export const DEFAULT_CORP_OPTIONS = ['君跻', '擎科', '金斯瑞', '内部'];
export const DEFAULT_TARGET_TYPE_OPTIONS = [
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
export const DEFAULT_SELECTION_METHOD_OPTIONS = [
  '补挑',
  'EYE',
  'DS',
  'JX_P',
  'JX_C',
  'RH_P',
  'RH_C',
  'D',
  'D模型',
  'D模型-3轮',
  'P',
];
export const DEFAULT_ENG_TYPE_OPTIONS = [
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
export const DEFAULT_ENG_METHOD_OPTIONS = [
  'AI',
  'NGS姐妹克隆',
  '理性设计',
  '饱和突变',
  '其他',
];

export const CSV_FIELD_OPTIONS = {
  mouse_strain: MOUSE_STRAIN_OPTIONS,
  selection_method: DEFAULT_SELECTION_METHOD_OPTIONS,
  eng_type: DEFAULT_ENG_TYPE_OPTIONS,
  eng_method: DEFAULT_ENG_METHOD_OPTIONS,
  affinity_owner: [],
};

export const DATE_KEYS = [
  'synthetic_date',
  'arrival_date',
  'flow_date',
  'affinity_date',
];

export const INT_COUNT_KEYS = [
  'synthetic_count',
  'arrival_count',
];

export const QUEUE_TERMINAL_STATUSES = ['已完成', '已取消'];

export const STRING_MAX = {
  target_name: 128,
  target_type: 64,
  mouse_strain: 128,
  selection_method: 128,
  synthesis_code: 64,
  order_no: 64,
  synthetic_corp: 64,
  affinity_result: 32,
  affinity_owner: 64,
  owner: 64,
  batch_label: 255,
  flow_note: 500,
  report_reason: 500,
  remark: 1000,
  eng_type: 128,
  eng_method: 128,
  eng_parent_seq: 500,
  eng_requirement: 1000,
  eng_result: 500,
  project_code: 64,
  study_type: 64,
  pm: 64,
};

export const BREAK_FIELDS = new Set([
  'flow_note',
  'report_reason',
  'remark',
  'eng_parent_seq',
  'eng_requirement',
  'eng_result',
]);

export const CLAIM_RETURN_DAYS = 7;

export const USER_OPTION_LIST = {
  affinity_owner: 'affinity_owners',
  owner: 'owners',
  pm: 'pms',
};

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

export const BASE_EDITOR_SECTIONS = [
  {
    title: '状态 / 归属',
    queue: true,
    fields: [
      { key: 'status', label: '状态', type: 'select', options: STATUS_OPTIONS },
      {
        key: 'priority',
        label: '优先级',
        type: 'select',
        options: PRIORITY_OPTIONS,
      },
      { key: 'owner', label: '负责人', type: 'user' },
      { key: 'sort_order', label: '排序', type: 'number' },
      {
        key: 'order_kind',
        label: '订单性质',
        type: 'select',
        options: ORDER_KIND_OPTIONS,
      },
      {
        key: 'supply_mode',
        label: '供应方式',
        type: 'select',
        options: SUPPLY_MODE_OPTIONS,
      },
    ],
  },
  {
    title: '项目信息',
    fields: [
      { key: 'project_code', label: '项目编号', type: 'text' },
      {
        key: 'mouse_strain',
        label: '小鼠品系',
        type: 'csv',
        options: MOUSE_STRAIN_OPTIONS,
      },
      { key: 'pm', label: 'PM', type: 'user' },
      {
        key: 'study_type',
        label: '课题类型',
        type: 'select',
        options: STUDY_TYPE_OPTIONS,
      },
      { key: 'target', label: '靶点', type: 'target', wide: true },
      {
        key: 'target_codes',
        label: '靶点编号',
        type: 'target_codes',
        wide: true,
      },
      { key: 'remark', label: '检测备注', type: 'textarea', wide: true },
    ],
  },
  {
    title: '合成订单',
    fields: [
      {
        key: 'selection_method',
        label: '挑选方式',
        type: 'csv',
        options: DEFAULT_SELECTION_METHOD_OPTIONS,
      },
      { key: 'synthesis_code', label: '送测转码', type: 'text' },
      { key: 'order_sender', label: '下单人', type: 'text', solo: true },
      { key: 'order_no', label: '订单号', type: 'text' },
      { key: 'synthetic_corp', label: '合成公司', type: 'corp_select' },
      { key: 'synthetic_count', label: '合成个数', type: 'number' },
      { key: 'synthetic_date', label: '合成日期', type: 'date' },
      { key: 'batch_label', label: '工单批次', type: 'text', wide: true },
    ],
  },
  {
    title: '到货与验证',
    fields: [
      { key: 'arrival_count', label: '到货个数', type: 'number' },
      { key: 'arrival_date', label: '到货日期', type: 'date' },
      { key: 'affinity_owner', label: '亲和力人员', type: 'user', multiple: true },
      {
        key: 'affinity_result',
        label: '亲和力结果',
        type: 'select',
        options: AFFINITY_RESULT_OPTIONS,
      },
      { key: 'affinity_date', label: '亲和力日期', type: 'date' },
      {
        key: 'report_reason',
        label: '未出原因',
        type: 'textarea',
        wide: true,
      },
      { key: 'flow_date', label: '流式日期', type: 'date' },
      {
        key: 'flow_note',
        label: '流式说明',
        type: 'textarea',
        wide: true,
      },
    ],
  },
];

export const ENGINEERING_EDITOR_SECTION = {
  title: '改造信息',
  engineering: true,
  fields: [
    {
      key: 'eng_type',
      label: '改造类型',
      type: 'csv',
      options: DEFAULT_ENG_TYPE_OPTIONS,
    },
    {
      key: 'eng_method',
      label: '改造方式',
      type: 'csv',
      options: DEFAULT_ENG_METHOD_OPTIONS,
    },
    {
      key: 'eng_parent_seq',
      label: '母本序列',
      type: 'textarea',
      wide: true,
    },
    {
      key: 'eng_requirement',
      label: '改造要求',
      type: 'textarea',
      wide: true,
    },
    { key: 'eng_result', label: '改造结果', type: 'textarea', wide: true },
  ],
};

export const WORKBENCH_COLUMNS = [
  {
    key: 'sort_order',
    label: '序号',
    defaultVisible: true,
    width: 62,
    className: 'sort-column-cell',
  },
  {
    key: 'priority',
    label: '优先级',
    defaultVisible: true,
    minWidth: 110,
  },
  {
    key: 'status',
    label: '状态',
    defaultVisible: true,
    minWidth: 132,
    className: 'status-column-cell',
  },
  {
    key: 'target_name',
    label: '靶点',
    defaultVisible: true,
    prop: 'target_name',
    minWidth: 110,
    showOverflowTooltip: true,
  },
  {
    key: 'target_type',
    label: '靶点类型',
    defaultVisible: true,
    prop: 'target_type',
    minWidth: 105,
    className: 'status-column-cell',
  },
  {
    key: 'mouse_strain',
    label: '小鼠品系',
    defaultVisible: true,
    prop: 'mouse_strain',
    minWidth: 100,
    showOverflowTooltip: true,
  },
  {
    key: 'synthesis_code',
    label: '送测转码',
    defaultVisible: true,
    prop: 'synthesis_code',
    minWidth: 150,
    showOverflowTooltip: true,
  },
  {
    key: 'order_no',
    label: '订单号',
    prop: 'order_no',
    minWidth: 150,
    showOverflowTooltip: true,
  },
  {
    key: 'synthetic_count',
    label: '合成个数',
    defaultVisible: true,
    prop: 'synthetic_count',
    minWidth: 90,
    showOverflowTooltip: true,
  },
  {
    key: 'synthetic_date',
    label: '合成日期',
    defaultVisible: true,
    prop: 'synthetic_date',
    minWidth: 110,
    showOverflowTooltip: true,
  },
  {
    key: 'arrival_count',
    label: '到货个数',
    defaultVisible: true,
    prop: 'arrival_count',
    minWidth: 90,
    showOverflowTooltip: true,
  },
  {
    key: 'arrival_date',
    label: '到货日期',
    defaultVisible: true,
    prop: 'arrival_date',
    minWidth: 110,
    showOverflowTooltip: true,
  },
  {
    key: 'affinity_date',
    label: '亲和力日期',
    defaultVisible: true,
    prop: 'affinity_date',
    minWidth: 110,
    showOverflowTooltip: true,
  },
  {
    key: 'affinity_owner',
    label: '亲和力人员',
    prop: 'affinity_owner',
    minWidth: 105,
    showOverflowTooltip: true,
  },
  {
    key: 'flow_date',
    label: '流式日期',
    defaultVisible: true,
    prop: 'flow_date',
    minWidth: 120,
    showOverflowTooltip: true,
  },
  {
    key: 'owner',
    label: '负责人',
    defaultVisible: true,
    prop: 'owner',
    minWidth: 96,
    showOverflowTooltip: true,
  },
  {
    key: 'selection_method',
    label: '挑选方式',
    prop: 'selection_method',
    minWidth: 100,
    showOverflowTooltip: true,
  },
  {
    key: 'batch_label',
    label: '工单批次',
    prop: 'batch_label',
    minWidth: 180,
    showOverflowTooltip: true,
  },
  {
    key: 'remark',
    label: '检测备注',
    prop: 'remark',
    minWidth: 160,
    showOverflowTooltip: true,
    keepLineBreaks: true,
  },
  {
    key: 'affinity_result',
    label: '亲和力结果',
    prop: 'affinity_result',
    minWidth: 96,
    showOverflowTooltip: true,
  },
  {
    key: 'report_reason',
    label: '未出原因',
    prop: 'report_reason',
    minWidth: 170,
    showOverflowTooltip: true,
    keepLineBreaks: true,
  },
  {
    key: 'flow_note',
    label: '流式说明',
    prop: 'flow_note',
    minWidth: 170,
    showOverflowTooltip: true,
    keepLineBreaks: true,
  },
  {
    key: 'synthetic_corp',
    label: '合成公司',
    prop: 'synthetic_corp',
    minWidth: 92,
    showOverflowTooltip: true,
  },
  {
    key: 'order_sender',
    label: '下单人',
    prop: 'order_sender',
    minWidth: 130,
    showOverflowTooltip: true,
  },
  {
    key: 'order_kind',
    label: '订单性质',
    prop: 'order_kind',
    minWidth: 96,
    showOverflowTooltip: true,
  },
  {
    key: 'supply_mode',
    label: '供应方式',
    prop: 'supply_mode',
    minWidth: 96,
    showOverflowTooltip: true,
  },
  {
    key: 'target_codes',
    label: '靶点编号',
    prop: 'target_codes',
    minWidth: 110,
    showOverflowTooltip: true,
  },
  {
    key: 'project_code',
    label: '项目编号',
    prop: 'project_code',
    minWidth: 120,
    showOverflowTooltip: true,
  },
  {
    key: 'pm',
    label: 'PM',
    prop: 'pm',
    minWidth: 90,
    showOverflowTooltip: true,
  },
  {
    key: 'study_type',
    label: '课题类型',
    prop: 'study_type',
    minWidth: 110,
    showOverflowTooltip: true,
  },
  {
    key: 'eng_type',
    label: '改造类型',
    prop: 'eng_type',
    minWidth: 120,
    showOverflowTooltip: true,
  },
  {
    key: 'eng_method',
    label: '改造方式',
    prop: 'eng_method',
    minWidth: 120,
    showOverflowTooltip: true,
  },
  {
    key: 'eng_parent_seq',
    label: '改造序列或母本',
    prop: 'eng_parent_seq',
    minWidth: 170,
    showOverflowTooltip: true,
    keepLineBreaks: true,
  },
  {
    key: 'eng_requirement',
    label: '改造要求',
    prop: 'eng_requirement',
    minWidth: 170,
    showOverflowTooltip: true,
    keepLineBreaks: true,
  },
  {
    key: 'eng_result',
    label: '改造结果',
    prop: 'eng_result',
    minWidth: 160,
    showOverflowTooltip: true,
    keepLineBreaks: true,
  },
  {
    key: 'actions',
    label: '操作',
    defaultVisible: true,
    width: 240,
    className: 'action-column-cell',
    fixed: 'right',
  },
];

/**
 * 表头菜单只对登记的列开放。
 * values：all 一次列全部值、本地搜索；recent 只列最近出现的 200 个、服务端搜索；search 输入后才查。
 * top：与顶部筛选器共用一份条件。kind 缺省为下拉选值；codes 是单号输入框（多个完整匹配、一个按包含）；
 * tokens 是逗号分隔、总按完整值匹配的输入框；
 * contains 是文本包含；range 是日期区间。topOnly 是顶部独有、表头表达不了的选项。
 */
export const HEADER_MENU_COLUMNS = Object.freeze({
  priority: { type: 'enum', values: 'all', top: { query: 'priority' } },
  status: { type: 'enum', values: 'all', top: { query: 'status', topOnly: ASSAY_COMBO_TERMS } },
  target_name: { type: 'text', label: '靶点', values: 'all', search: 'target', color: true, top: { query: 'target_name' } },
  target_codes: { type: 'csv', values: 'all' },
  target_type: { type: 'enum', values: 'all', top: { query: 'target_type', topOnly: ['非分泌型'] } },
  mouse_strain: { type: 'csv', values: 'all', top: { query: 'mouse_strain' } },
  selection_method: { type: 'csv', values: 'all', top: { query: 'selection_method' } },
  synthesis_code: { type: 'text', values: 'recent', top: { query: 'synthesis_code', kind: 'codes' } },
  order_no: { type: 'text', values: 'recent', top: { query: 'order_no', kind: 'codes' } },
  batch_label: { type: 'text', values: 'recent', top: { query: 'batch_label', kind: 'codes' } },
  synthetic_count: { type: 'number', values: 'all' },
  synthetic_date: { type: 'date', values: 'all', top: { range: 'syntheticDateRange' } },
  order_sender: { type: 'enum', values: 'all', top: { query: 'order_sender' } },
  arrival_count: { type: 'number', values: 'all' },
  arrival_date: { type: 'date', values: 'all', top: { range: 'arrivalDateRange' } },
  affinity_date: { type: 'date', values: 'all', top: { range: 'affinityDateRange' } },
  flow_date: { type: 'date', values: 'all', top: { range: 'flowDateRange' } },
  affinity_owner: { type: 'csv', values: 'all' },
  affinity_result: { type: 'enum', values: 'all', top: { query: 'affinity_result' } },
  owner: { type: 'enum', values: 'all', top: { query: 'owner' } },
  remark: { type: 'text', values: 'search', top: { query: 'remark', kind: 'contains' } },
  report_reason: { type: 'text', values: 'search', top: { query: 'report_reason', kind: 'contains' } },
  flow_note: { type: 'text', values: 'search', top: { query: 'flow_note', kind: 'contains' } },
  synthetic_corp: { type: 'enum', values: 'all', top: { query: 'synthetic_corp' } },
  order_kind: { type: 'enum', values: 'all', top: { query: 'order_kind' } },
  supply_mode: { type: 'enum', values: 'all', top: { query: 'supply_mode' } },
  project_code: { type: 'text', values: 'recent', top: { query: 'project_code', kind: 'codes' } },
  pm: { type: 'enum', values: 'all', top: { query: 'pm' } },
  study_type: { type: 'enum', values: 'all', top: { query: 'study_type' } },
  eng_type: { type: 'csv', values: 'all', top: { query: 'eng_type' } },
  eng_method: { type: 'csv', values: 'all', top: { query: 'eng_method' } },
  eng_parent_seq: { type: 'text', values: 'search' },
  eng_requirement: { type: 'text', values: 'search' },
  eng_result: { type: 'text', values: 'search' },
});

export const SHEET_COLUMNS = [
  { key: 'sort_order', label: '排序', edit: 'text', width: 64 },
  { key: 'priority', label: '优先级', edit: 'select', width: 100 },
  { key: 'status', label: '状态', edit: 'select', width: 126 },
  { key: 'target_name', label: '靶点名称', edit: 'target', minWidth: 120 },
  { key: 'target_type', label: '靶点类型', edit: 'select', width: 108 },
  { key: 'mouse_strain', label: '小鼠品系', edit: 'multi', minWidth: 115 },
  { key: 'selection_method', label: '挑选方式', edit: 'multi', minWidth: 115 },
  { key: 'synthesis_code', label: '送测转码', edit: 'text', minWidth: 150 },
  { key: 'order_no', label: '订单号', edit: 'text', minWidth: 150 },
  { key: 'batch_label', label: '工单批次', edit: 'text', minWidth: 180 },
  { key: 'synthetic_count', label: '合成个数', edit: 'text', width: 92 },
  { key: 'synthetic_date', label: '合成日期', edit: 'date', width: 120 },
  { key: 'arrival_count', label: '到货个数', edit: 'text', width: 92 },
  { key: 'arrival_date', label: '到货日期', edit: 'date', width: 120 },
  { key: 'remark', label: '检测备注', edit: 'text', minWidth: 160 },
  { key: 'affinity_owner', label: '亲和力人员', edit: 'multi', width: 105 },
  { key: 'affinity_date', label: '亲和力日期', edit: 'date', width: 120 },
  { key: 'affinity_result', label: '亲和力结果', edit: 'select', width: 100 },
  { key: 'report_reason', label: '未出原因', edit: 'text', minWidth: 170 },
  { key: 'flow_date', label: '流式日期', edit: 'date', width: 120 },
  { key: 'flow_note', label: '流式说明', edit: 'text', minWidth: 170 },
  { key: 'owner', label: '负责人', edit: 'select', width: 100 },
  { key: 'synthetic_corp', label: '合成公司', edit: 'select', width: 100 },
  { key: 'order_sender', label: '下单人', edit: 'readonly', lockHint: '下单人由 One 同步，不能修改', minWidth: 130 },
  { key: 'order_kind', label: '订单性质', edit: 'select', width: 100 },
  { key: 'supply_mode', label: '供应方式', edit: 'select', width: 100 },
  { key: 'target_codes', label: '靶点编号', edit: 'target', minWidth: 115 },
  { key: 'project_code', label: '项目编号', edit: 'text', minWidth: 120 },
  { key: 'pm', label: 'PM', edit: 'select', width: 95 },
  { key: 'study_type', label: '课题类型', edit: 'select', width: 110 },
  { key: 'eng_type', label: '改造类型', edit: 'multi', minWidth: 130 },
  { key: 'eng_method', label: '改造方式', edit: 'multi', minWidth: 125 },
  { key: 'eng_parent_seq', label: '改造序列或母本', edit: 'text', minWidth: 170 },
  { key: 'eng_requirement', label: '改造要求', edit: 'text', minWidth: 170 },
  { key: 'eng_result', label: '改造结果', edit: 'text', minWidth: 160 },
];

export const SHEET_COLUMN_ORDER = createColumnOrder(
  'discoverySynthesisSheetColumnOrder.v12',
  SHEET_COLUMNS,
  { pinFirstKey: 'sort_order' },
);

export const SHEET_HEADER_ALIASES = Object.freeze({
  排序: 'sort_order',
  序号: 'sort_order',
  优先级: 'priority',
  状态: 'status',
  订单性质: 'order_kind',
  供应方式: 'supply_mode',
  靶点: 'target_name',
  靶点名称: 'target_name',
  靶点类型: 'target_type',
  靶点编号: 'target_codes',
  鼠型: 'mouse_strain',
  小鼠品系: 'mouse_strain',
  挑选方式: 'selection_method',
  送测转码: 'synthesis_code',
  送合成转码: 'synthesis_code',
  合成批号: 'synthesis_code',
  订单号: 'order_no',
  合成公司订单号: 'order_no',
  合成订单号: 'order_no',
  合成公司: 'synthetic_corp',
  合成个数: 'synthetic_count',
  条数: 'synthetic_count',
  合成日期: 'synthetic_date',
  合成时间: 'synthetic_date',
  送合成日期: 'synthetic_date',
  到货个数: 'arrival_count',
  上清交付数: 'arrival_count',
  上清交付数目: 'arrival_count',
  到货日期: 'arrival_date',
  上清到货日期: 'arrival_date',
  流式日期: 'flow_date',
  亲和力日期: 'affinity_date',
  亲和力人员: 'affinity_owner',
  亲和力结果: 'affinity_result',
  亲和力是否全阴: 'affinity_result',
  负责人: 'owner',
  项目负责人: 'owner',
  流式说明: 'flow_note',
  流式检测说明: 'flow_note',
  流式备注: 'flow_note',
  检测说明: 'flow_note',
  未出原因: 'report_reason',
  未出报告原因: 'report_reason',
  亲和力未出报告原因: 'report_reason',
  工单: 'batch_label',
  工单批次: 'batch_label',
  工单批次说明: 'batch_label',
  项目编号: 'project_code',
  课题类型: 'study_type',
  PM: 'pm',
  改造类型: 'eng_type',
  改造方式: 'eng_method',
  序列: 'eng_parent_seq',
  母本序列: 'eng_parent_seq',
  改造序列或母本: 'eng_parent_seq',
  要求: 'eng_requirement',
  改造要求: 'eng_requirement',
  改造进度: 'eng_result',
  改造结果: 'eng_result',
  检测备注: 'remark',
  备注: 'remark',
});

export const EDITABLE_FIELDS = [
  'status',
  'priority',
  'sort_order',
  'order_kind',
  'supply_mode',
  'target_name',
  'target_codes',
  'mouse_strain',
  'selection_method',
  'synthesis_code',
  'order_no',
  'synthetic_corp',
  'synthetic_count',
  'synthetic_date',
  'arrival_count',
  'arrival_date',
  'flow_date',
  'affinity_date',
  'affinity_result',
  'affinity_owner',
  'owner',
  'batch_label',
  'flow_note',
  'report_reason',
  'remark',
  'eng_type',
  'eng_method',
  'eng_parent_seq',
  'eng_requirement',
  'eng_result',
  'project_code',
  'study_type',
  'pm',
];
