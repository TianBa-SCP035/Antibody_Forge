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

export function canViewLibrary(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'molecular.page.library');
}

export function canViewLibraryDetail(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'molecular.page.library_detail');
}

export function canEditLibrary(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'molecular.library.edit');
}

export function canEditPrimerLibrary(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'molecular.primer.edit');
}

export function canManageLibraryFiles(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'molecular.library.file.manage');
}

export function canHandoffLibrary(userInfo: any): boolean {
  return (
    hasAccessCode(userInfo, 'discovery.workbench.edit')
    || hasAccessCode(userInfo, 'molecular.library.edit')
  );
}
