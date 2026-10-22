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

const codeSetCache = new WeakMap<object, { rawSig: string; set: Set<string> }>();

function codesSignature(raw: unknown): string {
  if (Array.isArray(raw)) return raw.map(String).join('\0');
  if (typeof raw === 'string') return raw;
  return '';
}

function hasAccessCode(userInfo: any, code: string): boolean {
  if (!userInfo || typeof userInfo !== 'object') return false;
  const raw =
    userInfo.accessCodes || userInfo.permissions || userInfo.permissionCodes;
  const rawSig = codesSignature(raw);
  let cached = codeSetCache.get(userInfo);
  if (!cached || cached.rawSig !== rawSig) {
    cached = { rawSig, set: new Set(normalizeStringList(raw)) };
    codeSetCache.set(userInfo, cached);
  }
  return cached.set.has('*') || cached.set.has(code);
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
