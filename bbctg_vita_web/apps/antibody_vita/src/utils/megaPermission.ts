import { hasAccessCode } from '#/utils/accessCode';

export function canEditMegaFlowWorkOrder(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'mega.flow_work_order.edit');
}

export function canDispatchMegaFlowWorkOrder(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'mega.flow_work_order.dispatch');
}
