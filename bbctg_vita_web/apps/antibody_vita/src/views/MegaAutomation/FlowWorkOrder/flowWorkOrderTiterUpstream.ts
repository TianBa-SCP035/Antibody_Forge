/**
 * 效价工单 → 流式工单：样本板预填（仅本推送路径使用，不是流式工单默认布局）。
 *
 * 布局：第 1 列 NC、第 12 列 PC；样本仅 A02–A11、E02–E11；其余空孔。
 * 选中鼠号按组序、组内原序连续装填，装满一板再开下一板。
 */
import type { FlowWorkOrder, FlowWorkOrderSamplePlate, FlowWorkOrderWell } from '#/api/megaAutomation';

import { createDefaultFlowWorkOrder, createDefaultSamplePlate, PLATE_ROWS } from './flowWorkOrderModel';

export const TITER_INSTRUMENT_WIZARD_DRAFT_KEY = 'titer-instrument-wizard-draft';
export const TITER_UPSTREAM_PREFILL_QUERY = 'titer-wizard';

export interface TiterInstrumentWizardDraft {
  experiment_id: string;
  groups: Array<{ group_id: string; selected_mouse_nos: string[] }>;
  project_code?: string;
  target_name?: string;
  titer_order_id: string;
}

function wellNo(row: string, column: number) {
  return `${row}${String(column).padStart(2, '0')}`;
}

/** 每板样本孔顺序：A2–A11，再 E2–E11 */
const TITER_UPSTREAM_SAMPLE_SLOTS: string[] = [
  ...Array.from({ length: 10 }, (_, index) => wellNo('A', index + 2)),
  ...Array.from({ length: 10 }, (_, index) => wellNo('E', index + 2)),
];

function emptyWell(well_no: string, content_type: string, sample_code = ''): FlowWorkOrderWell {
  return {
    batch: '',
    content_type,
    generation: '',
    pc_id: null,
    sample_code,
    well_no,
  };
}

function buildTiterUpstreamPlateWells(mouseNos: string[]): FlowWorkOrderWell[] {
  const sampleByWell = new Map<string, string>();
  mouseNos.forEach((no, index) => {
    const slot = TITER_UPSTREAM_SAMPLE_SLOTS[index];
    if (slot) sampleByWell.set(slot, no);
  });

  return PLATE_ROWS.flatMap((row) =>
    Array.from({ length: 12 }, (_, index) => {
      const column = index + 1;
      const no = wellNo(row, column);
      if (column === 1) return emptyWell(no, 'NC');
      if (column === 12) return emptyWell(no, 'PC');
      if (sampleByWell.has(no)) return emptyWell(no, 'SAMPLE', sampleByWell.get(no) || '');
      return emptyWell(no, 'BLANK');
    }),
  );
}

/** 组序 × 组内原序；不去重、不重排（同鼠号可重复出现） */
function flattenSelectedMouseNos(draft: TiterInstrumentWizardDraft): string[] {
  const nos: string[] = [];
  for (const group of draft.groups || []) {
    for (const no of group.selected_mouse_nos || []) {
      const text = String(no || '').trim();
      if (text) nos.push(text);
    }
  }
  return nos;
}

function buildTiterUpstreamSamplePlates(
  mouseNos: string[],
  experimentId: string,
  targetName: string,
): FlowWorkOrderSamplePlate[] {
  const slots = TITER_UPSTREAM_SAMPLE_SLOTS.length;
  const plateCount = Math.max(1, Math.ceil(mouseNos.length / slots));
  const plates: FlowWorkOrderSamplePlate[] = [];
  for (let plateIndex = 0; plateIndex < plateCount; plateIndex += 1) {
    const start = plateIndex * slots;
    plates.push({
      ...createDefaultSamplePlate(),
      project_no: experimentId,
      target: targetName,
      wells: buildTiterUpstreamPlateWells(mouseNos.slice(start, start + slots)),
    });
  }
  return plates;
}

function buildTiterUpstreamOrderNo(titerOrderId: string): string {
  const base = String(titerOrderId || '').trim() || 'TITER';
  const suffix = Math.random().toString(36).slice(2, 6).toUpperCase();
  return `${base}-${suffix}`;
}

function buildTiterUpstreamOrderName(draft: TiterInstrumentWizardDraft): string {
  const project = String(draft.project_code || draft.experiment_id || '').trim();
  const target = String(draft.target_name || '').trim();
  return [project, target, '效价检测'].filter(Boolean).join('-') || '效价检测';
}

export function buildFlowWorkOrderFromTiterWizardDraft(
  draft: TiterInstrumentWizardDraft,
): FlowWorkOrder {
  const experimentId = String(draft.experiment_id || '').trim();
  const targetName = String(draft.target_name || '').trim();
  const orderName = buildTiterUpstreamOrderName(draft);
  const orderNo = buildTiterUpstreamOrderNo(draft.titer_order_id);
  return {
    ...createDefaultFlowWorkOrder(),
    data_type: 'TITER',
    order_name: orderName,
    order_no: orderNo,
    source_id: String(draft.titer_order_id || '').trim() || undefined,
    base_info: {
      order_name: orderName,
      pc_infos: [],
      remark: '',
    },
    sample_plates: buildTiterUpstreamSamplePlates(
      flattenSelectedMouseNos(draft),
      experimentId,
      targetName,
    ),
  };
}

export function readTiterInstrumentWizardDraft(): null | TiterInstrumentWizardDraft {
  try {
    const raw = sessionStorage.getItem(TITER_INSTRUMENT_WIZARD_DRAFT_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return null;
    return parsed as TiterInstrumentWizardDraft;
  } catch {
    return null;
  }
}

export function clearTiterInstrumentWizardDraft() {
  try {
    sessionStorage.removeItem(TITER_INSTRUMENT_WIZARD_DRAFT_KEY);
  } catch {
    /* ignore */
  }
}
