import { requestClient, skipGlobalErrorHandler } from '#/api/request';

type RequestConfig = Parameters<typeof requestClient.get>[1];
type PostConfig = Parameters<typeof requestClient.post>[2];

export interface FlowWorkOrderOption {
  label: string;
  value: string;
}

export interface FlowWorkOrderPcInfo {
  catalog_batch: string;
  concentration: string;
  pc_id: string;
  pc_name: string;
  pc_type: string;
  source: string;
}

export interface FlowWorkOrderWell {
  content_type: string;
  pc_id: null | string;
  sample_code: string;
  well_no: string;
}

export interface FlowWorkOrderCellKey {
  barcode: string;
  column_no: number;
}

export interface FlowWorkOrderSamplePlate {
  _rowKey?: string;
  barcode: string;
  cell_keys: FlowWorkOrderCellKey[];
  project_no: string;
  secondary_antibody: string;
  target: string;
  wells: FlowWorkOrderWell[];
}

export interface FlowWorkOrderCellColumn {
  batch: string;
  catalog_no: string;
  cell_count: string;
  cell_name: string;
  cell_type: string;
  column_no: number;
  generation: string;
  source: string;
  species: string;
}

export interface FlowWorkOrderCellPlate {
  barcode: string;
  columns: FlowWorkOrderCellColumn[];
}

export interface FlowWorkOrderDispatch {
  created_by?: string;
  dispatchId: string;
  id: number;
  pause_state?: string;
  payload?: Record<string, unknown>;
  sent_at?: null | string;
  status: string;
}

export interface FlowWorkOrder {
  base_info: {
    orderName: string;
    pc_infos: FlowWorkOrderPcInfo[];
    remark: string;
  };
  cell_plates: FlowWorkOrderCellPlate[];
  content_hash: string;
  created_at?: null | string;
  created_by?: string;
  orderType: string;
  dispatches: FlowWorkOrderDispatch[];
  display_status?: string;
  display_status_label?: string;
  error_message?: null | string;
  has_dispatches?: boolean;
  id: null | number;
  orderName: string;
  orderNum: string;
  pause_state?: string;
  priority: string;
  project_nos?: string[];
  remark?: string;
  sample_plates: FlowWorkOrderSamplePlate[];
  sample_plate_barcodes?: string[];
  sent_at?: null | string;
  source_id?: string;
  status: string;
  targets?: string[];
  updated_at?: null | string;
  cell_plate_barcodes?: string[];
}

export interface FlowWorkOrderMeta {
  orderTypes: FlowWorkOrderOption[];
  default_cell_columns: FlowWorkOrderCellColumn[];
  default_sample_wells: FlowWorkOrderWell[];
  priorities: FlowWorkOrderOption[];
  statuses: FlowWorkOrderOption[];
}

export interface FlowWorkOrderListQuery {
  cell_plate_barcode: string;
  orderType: string;
  keyword: string;
  limit: number;
  page: number;
  project_no: string;
  sample_plate_barcode: string;
  status: string;
  target: string;
}

export type FlowWorkOrderListItem = Pick<
  FlowWorkOrder,
  'cell_plate_barcodes' | 'created_at' | 'created_by' | 'orderType' | 'display_status'
  | 'display_status_label' | 'error_message' | 'id' | 'orderName' | 'orderNum' | 'priority'
  | 'project_nos' | 'remark' | 'sample_plate_barcodes' | 'sent_at' | 'source_id' | 'status'
  | 'targets' | 'updated_at'
>;

export interface FlowWorkOrderListResult {
  items: FlowWorkOrderListItem[];
  stats: Record<string, number>;
  total: number;
}

export interface FlowWorkOrderSavePayload {
  base_info: FlowWorkOrder['base_info'];
  cell_plates: FlowWorkOrderCellPlate[];
  orderType: string;
  expected_content_hash: string;
  id: null | number;
  orderName: string;
  orderNum: string;
  priority: string;
  remark: string;
  sample_plates: FlowWorkOrderSamplePlate[];
  source_id?: string;
}

export interface FlowWorkOrderValidationResult {
  can_resume?: boolean;
  content_changed?: boolean;
  errors: string[];
  issues: Array<{ field: string; message: string }>;
  item?: FlowWorkOrder;
  message?: string;
  needs_confirm?: boolean;
  saved?: boolean;
  valid: boolean;
}

export function fetchFlowWorkOrderMeta(config?: RequestConfig) {
  return requestClient.get<FlowWorkOrderMeta>('/mega-automation/flow-work-orders/meta', {
    ...skipGlobalErrorHandler,
    ...config,
  });
}

export function fetchFlowWorkOrderList(data: FlowWorkOrderListQuery, config?: PostConfig) {
  return requestClient.post<FlowWorkOrderListResult>('/mega-automation/flow-work-orders/list', data, {
    ...skipGlobalErrorHandler,
    ...config,
  });
}

export function fetchFlowWorkOrdersBySource(
  data: { orderType: string; exclude_cancelled?: boolean; source_id: string },
  config?: PostConfig,
) {
  return requestClient.post<{ items: FlowWorkOrderListItem[] }>(
    '/mega-automation/flow-work-orders/by-source',
    data,
    {
      ...skipGlobalErrorHandler,
      ...config,
    },
  );
}

export function fetchFlowWorkOrderDetail(id: number | string, config?: RequestConfig) {
  return requestClient.get<FlowWorkOrder>(`/mega-automation/flow-work-orders/${id}`, {
    ...skipGlobalErrorHandler,
    ...config,
  });
}

export function fetchActiveFlowWorkOrderPayload(id: number | string, config?: RequestConfig) {
  return requestClient.get<{
    dispatch: FlowWorkOrderDispatch | null;
    payload: null | Record<string, unknown>;
  }>(`/mega-automation/flow-work-orders/${id}/active-payload`, {
    ...skipGlobalErrorHandler,
    ...config,
  });
}

export function saveFlowWorkOrder(data: FlowWorkOrderSavePayload) {
  return requestClient.post<FlowWorkOrder & { unchanged?: boolean }>(
    '/mega-automation/flow-work-orders/save',
    data,
    skipGlobalErrorHandler,
  );
}

export function validateFlowWorkOrder(id: number | string, data: Record<string, unknown> = {}) {
  return requestClient.post<FlowWorkOrderValidationResult>(
    `/mega-automation/flow-work-orders/${id}/validate`,
    data,
    skipGlobalErrorHandler,
  );
}

export function dispatchFlowWorkOrder(id: number | string) {
  return requestClient.post<FlowWorkOrder>(
    `/mega-automation/flow-work-orders/${id}/dispatch`,
    {},
    skipGlobalErrorHandler,
  );
}

export function pauseFlowWorkOrder(id: number | string) {
  return requestClient.post<FlowWorkOrder>(
    `/mega-automation/flow-work-orders/${id}/pause`,
    {},
    skipGlobalErrorHandler,
  );
}

export function resumeFlowWorkOrder(id: number | string) {
  return requestClient.post<FlowWorkOrder>(
    `/mega-automation/flow-work-orders/${id}/resume`,
    {},
    skipGlobalErrorHandler,
  );
}

export function confirmFlowWorkOrderExecution(id: number | string) {
  return requestClient.post<FlowWorkOrder>(
    `/mega-automation/flow-work-orders/${id}/confirm-execution`,
    {},
    skipGlobalErrorHandler,
  );
}

export function completeFlowWorkOrder(id: number | string) {
  return requestClient.post<FlowWorkOrder>(
    `/mega-automation/flow-work-orders/${id}/complete`,
    {},
    skipGlobalErrorHandler,
  );
}

export function failFlowWorkOrder(id: number | string, errorMessage = '') {
  return requestClient.post<FlowWorkOrder>(
    `/mega-automation/flow-work-orders/${id}/fail`,
    { error_message: errorMessage },
    skipGlobalErrorHandler,
  );
}

export function acknowledgePauseFlowWorkOrder(id: number | string) {
  return requestClient.post<FlowWorkOrder>(
    `/mega-automation/flow-work-orders/${id}/pause-ack`,
    {},
    skipGlobalErrorHandler,
  );
}

export function acknowledgeResumeFlowWorkOrder(id: number | string) {
  return requestClient.post<FlowWorkOrder>(
    `/mega-automation/flow-work-orders/${id}/resume-ack`,
    {},
    skipGlobalErrorHandler,
  );
}

export function deleteFlowWorkOrder(id: number | string) {
  return requestClient.post<{ deleted: boolean; id: number }>(
    `/mega-automation/flow-work-orders/${id}/delete`,
    {},
    skipGlobalErrorHandler,
  );
}

export function cancelFlowWorkOrder(id: number | string) {
  return requestClient.post<FlowWorkOrder>(
    `/mega-automation/flow-work-orders/${id}/cancel`,
    {},
    skipGlobalErrorHandler,
  );
}
