function normalizeStringList(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.map(String).filter(Boolean);
  }
  if (typeof value === 'string') {
    return value
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);
  }
  return [];
}

function getAccessCodes(userInfo: any): string[] {
  return normalizeStringList(
    userInfo?.accessCodes || userInfo?.permissions || userInfo?.permissionCodes,
  );
}

function hasAccessCode(userInfo: any, code: string): boolean {
  const codes = getAccessCodes(userInfo);
  return codes.includes('*') || codes.includes(code);
}

export function canViewMegaFlowWorkOrderPage(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'mega.page.flow_work_order');
}

export function canEditMegaFlowWorkOrder(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'mega.flow_work_order.edit');
}

export function canDispatchMegaFlowWorkOrder(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'mega.flow_work_order.dispatch');
}
