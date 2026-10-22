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

type CachedPermMeta = {
  rawCodes: unknown;
  codeSet: Set<string>;
  rawNamesKey: string;
  aliasSet: Set<string>;
  aliasList: string[];
};

const permCache = new WeakMap<object, CachedPermMeta>();

function codesSignature(rawCodes: unknown): string {
  if (Array.isArray(rawCodes)) return rawCodes.map(String).join('\0');
  if (typeof rawCodes === 'string') return rawCodes;
  return '';
}

function getPermMeta(userInfo: any): CachedPermMeta | null {
  if (!userInfo || typeof userInfo !== 'object') return null;
  const rawCodes =
    userInfo.accessCodes || userInfo.permissions || userInfo.permissionCodes;
  const rawCodesSig = codesSignature(rawCodes);
  const rawNamesKey = `${userInfo.realName ?? ''}|${userInfo.displayName ?? ''}|${userInfo.display_name ?? ''}|${userInfo.username ?? ''}`;
  let cached = permCache.get(userInfo);
  // 用内容签名而非引用相等：原地改权限数组时也能失效缓存
  if (cached && cached.rawCodes === rawCodesSig && cached.rawNamesKey === rawNamesKey) {
    return cached;
  }
  const codeSet = new Set(normalizeStringList(rawCodes));
  const names = [
    normalizeName(userInfo.realName),
    normalizeName(userInfo.displayName),
    normalizeName(userInfo.display_name),
    normalizeName(userInfo.username),
  ].filter(Boolean);
  const aliasList = [
    ...new Set(
      names.flatMap((name) => {
        const firstPart = name.split(/\s+/)[0] || '';
        return firstPart && firstPart !== name ? [name, firstPart] : [name];
      }),
    ),
  ];
  cached = {
    rawCodes: rawCodesSig,
    codeSet,
    rawNamesKey,
    aliasSet: new Set(aliasList),
    aliasList,
  };
  permCache.set(userInfo, cached);
  return cached;
}

function hasAccessCode(userInfo: any, code: string): boolean {
  const meta = getPermMeta(userInfo);
  if (!meta) return false;
  return meta.codeSet.has('*') || meta.codeSet.has(code);
}

function normalizeName(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function isProjectOwner(userInfo: any, project: any): boolean {
  const owner = normalizeName(project?.owner);
  if (!owner) return false;
  const meta = getPermMeta(userInfo);
  return Boolean(meta && meta.aliasSet.has(owner));
}

export function getSerumUserName(userInfo: any): string {
  return userInfo?.realName || userInfo?.username || '';
}

export function getSerumUserRoles(userInfo: any): string[] {
  return normalizeRoles(userInfo?.roles);
}

export function canAccessWorkbench(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'serum.page.workbench');
}

export function canEditWorkbench(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'serum.workbench.edit');
}

export function canEditWorkbenchDraft(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'serum.workbench.draft_edit');
}

export function canEditWorkbenchSupport(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'serum.workbench.support_edit');
}

export function canAccessSerumDetail(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'serum.page.detail');
}

export function canAccessSerumEdit(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'serum.page.edit');
}

export function canCreateSerumProject(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'serum.project.create');
}

export function canEditAllSerumProjects(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'serum.project.edit_all');
}

export function hasSerumProjectEditPermission(userInfo: any): boolean {
  return (
    canEditAllSerumProjects(userInfo) || hasAccessCode(userInfo, 'serum.project.edit')
  );
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

export function canOpenSerumEdit(userInfo: any, project: any): boolean {
  return canAccessSerumEdit(userInfo) && canEditSerumProject(userInfo, project);
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
    (canEditAllSerumTiter(userInfo) ||
      isProjectOwner(userInfo, project) ||
      isTiterOwner(userInfo, project))
  );
}

export function canManageSerumTiterFiles(userInfo: any, project: any): boolean {
  return (
    hasAccessCode(userInfo, 'serum.file.manage') &&
    (canEditAllSerumTiter(userInfo) ||
      isProjectOwner(userInfo, project) ||
      isTiterOwner(userInfo, project))
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
  const meta = getPermMeta(userInfo);
  if (!meta || !meta.aliasSet.size) return false;
  const owners = Array.isArray(row?.titer_owners) ? row.titer_owners : [];
  return owners.some((owner: unknown) => {
    const name = normalizeName(owner);
    return Boolean(name && meta.aliasSet.has(name));
  });
}

export function canViewTiterOrderPage(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'serum.page.titer_order');
}

export function canEditTiterOrder(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'serum.titer_order.edit');
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

/** 血清状态、检测优先级：有 record.edit 即可，不校验负责人。 */
export function canEditTiterOrderRecordOpen(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'serum.titer_order.record.edit');
}

export function canEditTiterOrderRecord(userInfo: any, row: any): boolean {
  return (
    canEditTiterOrderRecordOpen(userInfo) &&
    (canEditAllTiterOrderRecord(userInfo) ||
      isTiterOwner(userInfo, row) ||
      isProjectOwner(userInfo, { owner: row?.immune_owner }))
  );
}
