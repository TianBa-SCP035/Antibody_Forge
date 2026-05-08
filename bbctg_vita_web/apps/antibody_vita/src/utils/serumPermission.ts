const ADMIN_ROLES = new Set(['DOGE', 'super', 'admin']);

function normalizeRoles(roles: unknown): string[] {
  if (Array.isArray(roles)) {
    return roles.map(String).filter(Boolean);
  }
  if (typeof roles === 'string') {
    return roles
      .split(',')
      .map((role) => role.trim())
      .filter(Boolean);
  }
  return [];
}

export function getSerumUserName(userInfo: any): string {
  return userInfo?.realName || userInfo?.username || '';
}

export function getSerumUserRoles(userInfo: any): string[] {
  return normalizeRoles(userInfo?.roles);
}

export function isSerumAdmin(roles: unknown): boolean {
  return normalizeRoles(roles).some((role) => ADMIN_ROLES.has(role));
}

export function isSerumOwner(userInfo: any, owner?: string): boolean {
  if (!owner) {
    return false;
  }
  return getSerumUserName(userInfo).includes(owner);
}

export function canCreateSerumProject(userInfo: any): boolean {
  const roles = getSerumUserRoles(userInfo);
  return isSerumAdmin(roles) || roles.includes('serum_project_create');
}

export function canEditSerumProject(userInfo: any, project: any): boolean {
  const roles = getSerumUserRoles(userInfo);
  return isSerumAdmin(roles) || isSerumOwner(userInfo, project?.owner);
}

export function canEditSerumTiter(userInfo: any, project: any): boolean {
  const roles = getSerumUserRoles(userInfo);
  return (
    isSerumAdmin(roles) ||
    roles.includes('serum_titer') ||
    isSerumOwner(userInfo, project?.owner)
  );
}

export function canExportSerumMouse(userInfo: any): boolean {
  const roles = getSerumUserRoles(userInfo);
  return isSerumAdmin(roles) || roles.includes('serum_export');
}

export function canAutoUpdateSerumStatus(userInfo: any): boolean {
  return isSerumAdmin(getSerumUserRoles(userInfo));
}

export function canViewSerumCellInventory(userInfo: any): boolean {
  const roles = getSerumUserRoles(userInfo);
  return isSerumAdmin(roles) || roles.includes('serum_cell_inventory');
}

export function canUpdateSerumPrepStatus(userInfo: any, project: any): boolean {
  const roles = getSerumUserRoles(userInfo);
  return (
    isSerumAdmin(roles) ||
    roles.includes('serum_cell_prep') ||
    isSerumOwner(userInfo, project?.owner)
  );
}
