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

function normalizeRoles(roles: unknown): string[] {
  return normalizeStringList(roles);
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

function normalizeName(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function getUserNameAliases(userInfo: any): string[] {
  const names = [
    normalizeName(userInfo?.realName),
    normalizeName(userInfo?.displayName),
    normalizeName(userInfo?.display_name),
    normalizeName(userInfo?.username),
  ].filter(Boolean);
  return [
    ...new Set(
      names.flatMap((name) => {
        const firstPart = name.split(/\s+/)[0] || '';
        return firstPart && firstPart !== name ? [name, firstPart] : [name];
      }),
    ),
  ];
}

function isProjectOwner(userInfo: any, project: any): boolean {
  const owner = normalizeName(project?.owner);
  return Boolean(owner && getUserNameAliases(userInfo).includes(owner));
}

export function getSerumUserName(userInfo: any): string {
  return userInfo?.realName || userInfo?.username || '';
}

export function getSerumUserRoles(userInfo: any): string[] {
  return normalizeRoles(userInfo?.roles);
}

export function canCreateSerumProject(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'serum.project.create');
}

export function canEditAllSerumProjects(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'serum.project.edit_all');
}

export function canEditAllSerumTiter(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'serum.titer.edit_all');
}

export function canEditSerumProject(userInfo: any, project: any): boolean {
  if (canEditAllSerumProjects(userInfo)) {
    return true;
  }
  return hasAccessCode(userInfo, 'serum.project.edit') && isProjectOwner(userInfo, project);
}

export function canDeleteSerumProject(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'serum.project.delete');
}

export function canUpdateSerumStatus(userInfo: any, project: any): boolean {
  return (
    hasAccessCode(userInfo, 'serum.status.update') &&
    (canEditAllSerumProjects(userInfo) || isProjectOwner(userInfo, project))
  );
}

export function canUpdateSerumCage(userInfo: any, project: any): boolean {
  return (
    hasAccessCode(userInfo, 'serum.cage.update') &&
    (canEditAllSerumProjects(userInfo) || isProjectOwner(userInfo, project))
  );
}

export function canEditSerumTiter(userInfo: any, project: any): boolean {
  return (
    hasAccessCode(userInfo, 'serum.titer.edit') &&
    (canEditAllSerumTiter(userInfo) || isProjectOwner(userInfo, project))
  );
}

export function canManageSerumTiterFiles(userInfo: any, project: any): boolean {
  return (
    hasAccessCode(userInfo, 'serum.file.manage') &&
    (canEditAllSerumTiter(userInfo) || isProjectOwner(userInfo, project))
  );
}

export function canExportSerumMouse(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'serum.mouse.export');
}

export function canAutoUpdateSerumStatus(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'serum.status.auto_update');
}

export function canViewSerumCellInventory(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'serum.cell.view');
}

export function canUpdateSerumPrepStatus(userInfo: any, _project?: any): boolean {
  return hasAccessCode(userInfo, 'serum.cell.prep_status.update');
}

function isTiterOwner(userInfo: any, row: any): boolean {
  const aliases = getUserNameAliases(userInfo);
  const owners = Array.isArray(row?.titer_owners) ? row.titer_owners : [];
  return owners.some((owner: unknown) => {
    const name = normalizeName(owner);
    return Boolean(name && aliases.includes(name));
  });
}

export function canViewTiterOrderPage(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'serum.page.titer_order');
}

export function canCreateTiterOrder(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'serum.titer_order.create');
}

export function canEditTiterOrderBatch(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'serum.titer_order.batch.edit');
}

export function canDeleteTiterOrder(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'serum.titer_order.delete');
}

export function canEditTiterOrderOwner(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'serum.titer_order.owner.edit');
}

export function canEditAllTiterOrderRecord(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'serum.titer_order.record.edit_all');
}

export function canEditTiterOrderRecord(userInfo: any, row: any): boolean {
  return (
    hasAccessCode(userInfo, 'serum.titer_order.record.edit') &&
    (canEditAllTiterOrderRecord(userInfo) ||
      isTiterOwner(userInfo, row) ||
      isProjectOwner(userInfo, { owner: row?.immune_owner }))
  );
}

export function canEditAllTiterOrderSummary(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'serum.titer_order.summary.edit_all');
}

export function canEditTiterOrderSummary(userInfo: any, row: any): boolean {
  return (
    hasAccessCode(userInfo, 'serum.titer_order.summary.edit') &&
    (canEditAllTiterOrderSummary(userInfo) ||
      isProjectOwner(userInfo, { owner: row?.immune_owner }))
  );
}
