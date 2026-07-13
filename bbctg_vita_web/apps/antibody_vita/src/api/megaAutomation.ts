import { requestClient, skipGlobalErrorHandler } from '#/api/request';

type RequestConfig = Parameters<typeof requestClient.get>[1];
type PostConfig = Parameters<typeof requestClient.post>[2];

export function fetchFlowWorkOrderMeta(config?: RequestConfig) {
  return requestClient.get('/mega-automation/flow-work-orders/meta', {
    ...skipGlobalErrorHandler,
    ...config,
  });
}

export function fetchFlowWorkOrderList(data: any, config?: PostConfig) {
  return requestClient.post('/mega-automation/flow-work-orders/list', data, {
    ...skipGlobalErrorHandler,
    ...config,
  });
}

export function fetchFlowWorkOrderDetail(id: number | string, config?: RequestConfig) {
  return requestClient.get(`/mega-automation/flow-work-orders/${id}`, {
    ...skipGlobalErrorHandler,
    ...config,
  });
}

export function saveFlowWorkOrder(data: any) {
  return requestClient.post(
    '/mega-automation/flow-work-orders/save',
    data,
    skipGlobalErrorHandler,
  );
}

export function validateFlowWorkOrder(id: number | string, data: Record<string, unknown> = {}) {
  return requestClient.post(
    `/mega-automation/flow-work-orders/${id}/validate`,
    data,
    skipGlobalErrorHandler,
  );
}

export function dispatchFlowWorkOrder(id: number | string) {
  return requestClient.post(
    `/mega-automation/flow-work-orders/${id}/dispatch`,
    {},
    skipGlobalErrorHandler,
  );
}

export function pauseFlowWorkOrder(id: number | string) {
  return requestClient.post(
    `/mega-automation/flow-work-orders/${id}/pause`,
    {},
    skipGlobalErrorHandler,
  );
}

export function resumeFlowWorkOrder(id: number | string) {
  return requestClient.post(
    `/mega-automation/flow-work-orders/${id}/resume`,
    {},
    skipGlobalErrorHandler,
  );
}

export function confirmFlowWorkOrderExecution(id: number | string) {
  return requestClient.post(
    `/mega-automation/flow-work-orders/${id}/confirm-execution`,
    {},
    skipGlobalErrorHandler,
  );
}

export function completeFlowWorkOrder(id: number | string) {
  return requestClient.post(
    `/mega-automation/flow-work-orders/${id}/complete`,
    {},
    skipGlobalErrorHandler,
  );
}

export function failFlowWorkOrder(id: number | string, errorMessage = '') {
  return requestClient.post(
    `/mega-automation/flow-work-orders/${id}/fail`,
    { error_message: errorMessage },
    skipGlobalErrorHandler,
  );
}

export function acknowledgePauseFlowWorkOrder(id: number | string) {
  return requestClient.post(
    `/mega-automation/flow-work-orders/${id}/pause-ack`,
    {},
    skipGlobalErrorHandler,
  );
}

export function acknowledgeResumeFlowWorkOrder(id: number | string) {
  return requestClient.post(
    `/mega-automation/flow-work-orders/${id}/resume-ack`,
    {},
    skipGlobalErrorHandler,
  );
}

export function deleteFlowWorkOrder(id: number | string) {
  return requestClient.post(
    `/mega-automation/flow-work-orders/${id}/delete`,
    {},
    skipGlobalErrorHandler,
  );
}

export function cancelFlowWorkOrder(id: number | string) {
  return requestClient.post(
    `/mega-automation/flow-work-orders/${id}/cancel`,
    {},
    skipGlobalErrorHandler,
  );
}
