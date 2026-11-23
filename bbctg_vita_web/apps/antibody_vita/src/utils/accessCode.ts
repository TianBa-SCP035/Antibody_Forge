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

/** 有任一权限码即为真，和后端 require(*codes) 一致。 */
export function hasAccessCode(userInfo: any, ...codes: string[]): boolean {
  if (!userInfo || typeof userInfo !== 'object') return false;
  const raw =
    userInfo.accessCodes || userInfo.permissions || userInfo.permissionCodes;
  const rawSig = codesSignature(raw);
  let cached = codeSetCache.get(userInfo);
  if (!cached || cached.rawSig !== rawSig) {
    cached = { rawSig, set: new Set(normalizeStringList(raw)) };
    codeSetCache.set(userInfo, cached);
  }
  const set = cached.set;
  return codes.some((code) => set.has(code));
}
