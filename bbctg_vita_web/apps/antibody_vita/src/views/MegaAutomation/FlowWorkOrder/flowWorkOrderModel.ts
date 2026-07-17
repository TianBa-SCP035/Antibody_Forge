import type {
  FlowWorkOrder,
  FlowWorkOrderCellColumn,
  FlowWorkOrderCellPlate,
  FlowWorkOrderPcInfo,
  FlowWorkOrderSamplePlate,
  FlowWorkOrderSavePayload,
  FlowWorkOrderWell,
} from '#/api/megaAutomation';

export const PLATE_ROWS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'];
export const SECONDARY_ANTIBODY_OPTIONS = ['人', '猴', '鼠', '狗'];
export const SPECIES_OPTIONS = ['人', '猴', '鼠', '狗', '猫', '空白'];
export const CELL_TYPE_OPTIONS = ['正常', '肿瘤'];
export const WELL_TYPE_CYCLE = ['SAMPLE', 'PC', 'NC', 'ISO', 'TAG', 'BLANK'];
export const PC_INFO_TYPE_OPTIONS = ['SERUM', 'ISO', 'TAG'];
export const EDITABLE_STATUSES = ['draft', 'validated', 'failed', 'execution_failed'];

const WELL_PC_REF_TYPES = ['PC', 'ISO', 'TAG'];
const WELL_TYPE_LABELS: Record<string, string> = {
  BLANK: '空孔',
  ISO: 'ISO',
  NC: 'NC',
  PC: 'PC',
  SAMPLE: '样本',
  TAG: 'TAG',
};
const EMPTY_COLUMN = {
  batch: '',
  catalog_no: '',
  cell_count: '',
  cell_name: '',
  cell_type: '正常',
  generation: '',
  source: '',
  species: '',
};

export interface FlowWorkOrderDefaults {
  cellColumns?: FlowWorkOrderCellColumn[];
  sampleWells?: FlowWorkOrderWell[];
}

type LooseRecord = Record<string, any>;

let samplePlateRowSeed = 0;
let localPcIdSeed = 0;

function record(value: unknown): LooseRecord {
  return value && typeof value === 'object' ? value as LooseRecord : {};
}

function records(value: unknown): LooseRecord[] {
  return Array.isArray(value) ? value.map(record) : [];
}

function createSamplePlateRowKey() {
  return `sp-${++samplePlateRowSeed}`;
}

export function createLocalPcId() {
  return `tmp-${++localPcIdSeed}`;
}

function wellNo(row: string, column: number) {
  return `${row}${String(column).padStart(2, '0')}`;
}

function parseWellNo(value: unknown) {
  const match = String(value || '').match(/^([A-H])(\d{1,2})$/i);
  if (!match?.[1] || !match[2]) return null;
  const rowIndex = PLATE_ROWS.indexOf(match[1].toUpperCase());
  const column = Number.parseInt(match[2], 10);
  return rowIndex >= 0 && column >= 1 && column <= 12 ? { column, rowIndex } : null;
}

export function wellsInRect(startNo: string, endNo: string) {
  const start = parseWellNo(startNo);
  const end = parseWellNo(endNo);
  if (!start || !end) return [];
  const result: string[] = [];
  for (
    let rowIndex = Math.min(start.rowIndex, end.rowIndex);
    rowIndex <= Math.max(start.rowIndex, end.rowIndex);
    rowIndex += 1
  ) {
    for (
      let column = Math.min(start.column, end.column);
      column <= Math.max(start.column, end.column);
      column += 1
    ) {
      result.push(wellNo(PLATE_ROWS[rowIndex] || '', column));
    }
  }
  return result;
}

export function formatWellSelectionLabel(nos: string[]) {
  if (nos.length < 2) return nos[0] || '';
  const positions = nos
    .map(parseWellNo)
    .filter((position): position is { column: number; rowIndex: number } => position !== null);
  if (positions.length !== nos.length) return `已选 ${nos.length} 孔`;
  positions.sort((a, b) => a.rowIndex - b.rowIndex || a.column - b.column);
  const first = positions[0];
  const last = positions[positions.length - 1];
  if (!first || !last) return `已选 ${nos.length} 孔`;
  const expected =
    (Math.abs(last.rowIndex - first.rowIndex) + 1) *
    (Math.abs(last.column - first.column) + 1);
  return expected === nos.length
    ? `${wellNo(PLATE_ROWS[first.rowIndex] || '', first.column)}–${wellNo(
        PLATE_ROWS[last.rowIndex] || '',
        last.column,
      )}`
    : `已选 ${nos.length} 孔`;
}

export function wellPcInfoType(value: unknown) {
  const type = String(value || '').toUpperCase();
  return type === 'PC' ? 'SERUM' : ['ISO', 'TAG'].includes(type) ? type : '';
}

export function normalizedWells(plate?: Partial<FlowWorkOrderSamplePlate> | null) {
  return Array.isArray(plate?.wells) ? plate.wells : [];
}

export function rowWells(
  plate: Partial<FlowWorkOrderSamplePlate> | null | undefined,
  rowLabel: string,
) {
  return normalizedWells(plate).filter((well) => well.well_no.startsWith(rowLabel));
}

export function cellKey(barcode: unknown, columnNo: unknown) {
  return `${barcode || ''}|${columnNo || ''}`;
}

export function cellPlateBarcode(plate: Partial<FlowWorkOrderCellPlate>, index: number) {
  return plate.barcode || `细胞板${index + 1}`;
}

export function isCellSelected(plate: Partial<FlowWorkOrderSamplePlate>, key: string) {
  return Array.isArray(plate.cell_keys) && plate.cell_keys.includes(key);
}

export function selectedCountInPlate(
  plate: Partial<FlowWorkOrderSamplePlate>,
  option: { children?: Array<{ value: string }> },
) {
  const live = new Set((option.children || []).map((cell) => cell.value));
  return Array.isArray(plate.cell_keys)
    ? plate.cell_keys.filter((key) => live.has(key)).length
    : 0;
}

export function isPcRefType(value: unknown) {
  return WELL_PC_REF_TYPES.includes(String(value || '').toUpperCase());
}

export function isSampleType(value: unknown) {
  return String(value || '').toUpperCase() === 'SAMPLE';
}

export function wellTypeLabel(value: unknown) {
  return WELL_TYPE_LABELS[String(value || 'SAMPLE').toUpperCase()] || '样本';
}

export function createDefaultFlowWorkOrder(): FlowWorkOrder {
  return {
    base_info: { order_name: '', pc_infos: [], remark: '' },
    cell_plates: [],
    content_hash: '',
    data_type: 'TITER',
    dispatches: [],
    id: null,
    order_name: '',
    order_no: '',
    priority: 'normal',
    sample_plates: [],
    source_id: undefined,
    status: 'draft',
  };
}

function normalizePcInfos(value: unknown): FlowWorkOrderPcInfo[] {
  return records(value).map((pc) => ({
    catalog_batch: pc.catalog_batch || '',
    concentration: pc.concentration || '',
    pc_id: String(pc.pc_id || createLocalPcId()),
    pc_name: pc.pc_name || '',
    pc_type: String(pc.pc_type || 'SERUM').toUpperCase(),
    source: pc.source || '',
  }));
}

function normalizeWell(value: unknown): FlowWorkOrderWell {
  const well = record(value);
  const contentType = String(well.content_type || 'SAMPLE').toUpperCase();
  const pcId = well.pc_id == null || well.pc_id === '' ? null : String(well.pc_id);
  return {
    batch: well.batch || '',
    content_type: contentType,
    generation: well.generation || '',
    pc_id: WELL_PC_REF_TYPES.includes(contentType) ? pcId : null,
    sample_code: well.sample_code || '',
    well_no: String(well.well_no || ''),
  };
}

function buildFullWells(value: unknown): FlowWorkOrderWell[] {
  const byNo = new Map(records(value).map((well) => [String(well.well_no || ''), well]));
  return PLATE_ROWS.flatMap((row) =>
    Array.from({ length: 12 }, (_, index) => {
      const no = wellNo(row, index + 1);
      return normalizeWell(byNo.get(no) || { content_type: 'BLANK', well_no: no });
    }),
  );
}

function createDefaultWells(defaults: FlowWorkOrderDefaults) {
  if (defaults.sampleWells?.length) {
    return buildFullWells(defaults.sampleWells.map((well) => ({ ...well })));
  }
  return PLATE_ROWS.flatMap((row) =>
    Array.from({ length: 12 }, (_, index) => {
      const no = wellNo(row, index + 1);
      return normalizeWell({
        content_type: index === 11 ? 'PC' : 'SAMPLE',
        sample_code: index === 11 ? '' : no,
        well_no: no,
      });
    }),
  );
}

function normalizeColumns(value: unknown): FlowWorkOrderCellColumn[] {
  const byNo = new Map(
    records(value).map((column, index) => [Number(column.column_no) || index + 1, column]),
  );
  return Array.from({ length: 12 }, (_, index) => {
    const columnNo = index + 1;
    return { ...EMPTY_COLUMN, ...byNo.get(columnNo), column_no: columnNo };
  });
}

export function createDefaultColumns(defaults: FlowWorkOrderDefaults = {}) {
  return normalizeColumns(defaults.cellColumns);
}

export function createDefaultSamplePlate(
  defaults: FlowWorkOrderDefaults = {},
): FlowWorkOrderSamplePlate {
  return {
    _rowKey: createSamplePlateRowKey(),
    barcode: '',
    cell_keys: [],
    project_no: '',
    secondary_antibody: '人',
    target: '',
    wells: createDefaultWells(defaults),
  };
}

function normalizeSamplePlate(
  value: unknown,
  defaults: FlowWorkOrderDefaults,
): FlowWorkOrderSamplePlate {
  const plate = record(value);
  return {
    ...plate,
    _rowKey: plate._rowKey || createSamplePlateRowKey(),
    barcode: plate.barcode || '',
    cell_keys: Array.isArray(plate.cell_keys) ? plate.cell_keys.filter(Boolean) : [],
    project_no: plate.project_no || '',
    secondary_antibody: plate.secondary_antibody || '人',
    target: plate.target || '',
    wells: plate.wells?.length ? buildFullWells(plate.wells) : createDefaultWells(defaults),
  };
}

export function normalizeFlowWorkOrder(
  value: unknown,
  defaults: FlowWorkOrderDefaults = {},
): FlowWorkOrder {
  const source = record(value);
  const baseInfo = record(source.base_info);
  const samplePlates = records(source.sample_plates).map((plate) =>
    normalizeSamplePlate(plate, defaults),
  );
  const cellPlates = records(source.cell_plates).map((plate) => ({
    ...plate,
    barcode: plate.barcode || '',
    columns: normalizeColumns(plate.columns?.length ? plate.columns : defaults.cellColumns),
  }));
  return {
    ...createDefaultFlowWorkOrder(),
    ...source,
    base_info: {
      order_name: source.order_name || baseInfo.order_name || '',
      pc_infos: normalizePcInfos(baseInfo.pc_infos),
      remark: source.remark ?? baseInfo.remark ?? '',
    },
    cell_plates: cellPlates.length
      ? cellPlates
      : [{ barcode: '', columns: createDefaultColumns(defaults) }],
    dispatches: Array.isArray(source.dispatches) ? source.dispatches : [],
    order_name: source.order_name || baseInfo.order_name || '',
    priority: source.priority || 'normal',
    sample_plates: samplePlates.length ? samplePlates : [createDefaultSamplePlate(defaults)],
  };
}

export function buildFlowWorkOrderSavePayload(
  order: FlowWorkOrder,
): FlowWorkOrderSavePayload {
  return {
    base_info: order.base_info,
    cell_plates: order.cell_plates,
    data_type: order.data_type,
    expected_content_hash: order.content_hash || '',
    id: order.id,
    order_name: order.base_info.order_name,
    order_no: order.order_no || '',
    priority: order.priority,
    remark: order.base_info.remark,
    sample_plates: order.sample_plates,
    source_id: order.source_id || undefined,
  };
}
