import { requestClient, skipGlobalErrorHandler } from '#/api/request';

export const FLOW_WORK_ORDER_EDIT = 'mega.flow_work_order.edit';
export const FLOW_WORK_ORDER_DISPATCH = 'mega.flow_work_order.dispatch';

type RequestConfig = Parameters<typeof requestClient.get>[1];
type PostConfig = Parameters<typeof requestClient.post>[2];

const downloadConfig = {
  skipErrorHandler: true,
} as Parameters<typeof requestClient.download>[1];

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
  target_codes?: string[];
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
  field_filters?: Array<Record<string, unknown>>;
  orderType: string | string[];
  keyword: string;
  limit?: number;
  page?: number;
  project_no: string;
  sample_plate_barcode: string;
  sort_dir?: string;
  sort_field?: string;
  status: string | string[];
  target: string;
}

export interface FlowWorkOrderColumnValuesQuery extends FlowWorkOrderListQuery {
  field: string;
  value_keyword?: string;
  value_limit?: number;
  value_order?: string;
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

export function fetchFlowWorkOrderColumnValues(data: FlowWorkOrderColumnValuesQuery, config?: PostConfig) {
  return requestClient.post<{ items: Array<{ count: number; label?: string; value: string }>; truncated: boolean }>(
    '/mega-automation/flow-work-orders/column_values',
    data,
    {
      ...skipGlobalErrorHandler,
      ...config,
    },
  );
}

export function exportFlowWorkOrderList(data: FlowWorkOrderListQuery) {
  return requestClient.download('/mega-automation/flow-work-orders/export', {
    data,
    method: 'POST',
    timeout: 360_000,
    ...downloadConfig,
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

export interface CellPlateUsageColumn {
  batch: string;
  catalog_no: string;
  cell_count: string;
  cell_name: string;
  cell_type: string;
  column_no: number;
  conflict: boolean;
  generation: string;
  locked: boolean;
  source: string;
  source_order_id?: null | number;
  source_order_num: string;
  species: string;
  used_by: Array<{ id?: null | number; orderNum: string; status?: string }>;
}

export interface CellPlateUsage {
  barcode: string;
  columns: CellPlateUsageColumn[];
}

export function fetchCellPlateUsage(
  params: { barcode: string; exclude_order_id?: null | number },
  config?: RequestConfig,
) {
  return requestClient.get<CellPlateUsage>('/mega-automation/flow-work-orders/cell-plate-usage', {
    params: {
      barcode: params.barcode,
      exclude_order_id: params.exclude_order_id || undefined,
    },
    ...skipGlobalErrorHandler,
    ...config,
  });
}

export function fetchFlowWorkOrderDetail(id: number | string, config?: RequestConfig) {
  return requestClient.get<FlowWorkOrder>(`/mega-automation/flow-work-orders/${id}`, {
    ...skipGlobalErrorHandler,
    ...config,
  });
}

export interface FlowWorkOrderLabillionSyncResult {
  applied?: boolean;
  dispatchId?: string;
  execution_progress?: string;
  item?: FlowWorkOrder;
  labillion_status?: string;
  message?: string;
  reason?: string;
}

export function syncFlowWorkOrderLabillionStatus(id: number | string) {
  return requestClient.post<FlowWorkOrderLabillionSyncResult>(
    `/mega-automation/flow-work-orders/${id}/sync-labillion-status`,
    {},
    skipGlobalErrorHandler,
  );
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

export function dispatchFlowWorkOrder(id: number | string, simulate = false) {
  return requestClient.post<FlowWorkOrder>(
    `/mega-automation/flow-work-orders/${id}/dispatch`,
    simulate ? { simulate: true } : {},
    skipGlobalErrorHandler,
  );
}

export function pauseFlowWorkOrder(id: number | string, simulate = false) {
  return requestClient.post<FlowWorkOrder>(
    `/mega-automation/flow-work-orders/${id}/pause`,
    simulate ? { simulate: true } : {},
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

export function continueFlowWorkOrderExecution(id: number | string) {
  return requestClient.post<FlowWorkOrder>(
    `/mega-automation/flow-work-orders/${id}/continue-execution`,
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

export interface OrderSyncBoard {
  cell_name: null | string;
  csv_path: null | string;
  detect_barcode: null | string;
  dispatch_id: null | string;
  excel_file_id: null | number;
  experiment_date: null | string;
  experiment_id: null | string;
  facs_plate_id: null | number;
  id: number;
  image_file_id: null | number;
  image_path: null | string;
  import_message: null | string;
  import_status: string;
  order_no: string;
  received_at?: null | string;
  sample_barcode: null | string;
  seq: number;
  sync_id: number;
  trace_id?: string;
  updated_at: null | string;
  verify_message: null | string;
  verify_status: string;
  work_order_id: null | number;
}

export interface OrderSyncRecord {
  error_message: null | string;
  http_status: null | number;
  id: number;
  import_status: null | string;
  order_count: number;
  order_nos: null | string[];
  processed_at: null | string;
  received_at: null | string;
  status: string;
  status_label: string;
  trace_id: string;
}

export interface OrderSyncRecordDetail extends OrderSyncRecord {
  boards: OrderSyncBoard[];
  response_body: null | Record<string, unknown>;
}

export interface OrderSyncListQuery {
  import_status: string;
  keyword: string;
  limit: number;
  page: number;
  status: string;
}

export function fetchOrderSyncList(data: OrderSyncListQuery) {
  return requestClient.post<{
    items: OrderSyncRecord[];
    page: number;
    stats: Record<string, number>;
    total: number;
  }>('/mega-automation/order-sync/list', data, skipGlobalErrorHandler);
}

export function fetchOrderSyncDetail(id: number) {
  return requestClient.get<OrderSyncRecordDetail>(`/mega-automation/order-sync/${id}`, skipGlobalErrorHandler);
}

export function downloadOrderSyncRaw(id: number) {
  return requestClient.download(`/mega-automation/order-sync/${id}/raw`, downloadConfig);
}

export function reprocessOrderSync(id: number) {
  return requestClient.post<OrderSyncRecordDetail>(
    `/mega-automation/order-sync/${id}/reprocess`,
    {},
    skipGlobalErrorHandler,
  );
}

export function fetchWorkOrderSyncBoards(workOrderId: number, config?: RequestConfig) {
  return requestClient.get<{ items: OrderSyncBoard[] }>('/mega-automation/order-sync/boards', {
    params: { work_order_id: workOrderId },
    ...skipGlobalErrorHandler,
    ...config,
  });
}
