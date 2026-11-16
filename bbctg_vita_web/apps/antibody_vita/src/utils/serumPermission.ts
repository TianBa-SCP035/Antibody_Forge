// 免疫与效价里“本人负责的项目才能改”这类规则；只看一个权限码的地方直接用 hasAccessCode。

import {
  SERUM_CAGE_UPDATE,
  SERUM_FILE_MANAGE,
  SERUM_PAGE_EDIT,
  SERUM_PROJECT_EDIT,
  SERUM_PROJECT_EDIT_ALL,
  SERUM_STATUS_UPDATE,
  SERUM_TITER_EDIT,
  SERUM_TITER_EDIT_ALL,
  TITER_ORDER_RECORD_EDIT,
  TITER_ORDER_RECORD_EDIT_ALL,
} from '#/api/serum';
import { hasAccessCode } from '#/utils/accessCode';

function normalizeName(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

const aliasCache = new WeakMap<object, { key: string; aliases: Set<string> }>();

/** 当前用户可能出现在负责人字段里的写法：姓名、账号，以及“姓名 英文名”取第一段。 */
function userAliases(userInfo: any): Set<string> {
  if (!userInfo || typeof userInfo !== 'object') return new Set();
  const key = `${userInfo.realName ?? ''}|${userInfo.displayName ?? ''}|${userInfo.display_name ?? ''}|${userInfo.username ?? ''}`;
  const cached = aliasCache.get(userInfo);
  if (cached && cached.key === key) return cached.aliases;
  const names = [userInfo.realName, userInfo.displayName, userInfo.display_name, userInfo.username]
    .map(normalizeName)
    .filter(Boolean);
  const aliases = new Set(
    names.flatMap((name) => {
      const firstPart = name.split(/\s+/)[0] || '';
      return firstPart && firstPart !== name ? [name, firstPart] : [name];
    }),
  );
  aliasCache.set(userInfo, { key, aliases });
  return aliases;
}

function isAnyAlias(userInfo: any, values: unknown[]): boolean {
  const aliases = userAliases(userInfo);
  return values.some((value) => {
    const name = normalizeName(value);
    return Boolean(name && aliases.has(name));
  });
}

function isProjectMember(userInfo: any, project: any): boolean {
  return isAnyAlias(userInfo, [project?.owner, project?.reviewer]);
}

function isTiterOwner(userInfo: any, row: any): boolean {
  return isAnyAlias(userInfo, Array.isArray(row?.titer_owners) ? row.titer_owners : []);
}

export function getSerumUserName(userInfo: any): string {
  return userInfo?.realName || userInfo?.username || '';
}

export function getSerumUserRoles(userInfo: any): string[] {
  const roles = userInfo?.roles;
  if (Array.isArray(roles)) return roles.map(String).filter(Boolean);
  if (typeof roles === 'string') {
    return roles
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);
  }
  return [];
}

export function canEditSerumProject(userInfo: any, project: any): boolean {
  if (hasAccessCode(userInfo, SERUM_PROJECT_EDIT_ALL)) return true;
  return hasAccessCode(userInfo, SERUM_PROJECT_EDIT) && isProjectMember(userInfo, project);
}

export function canOpenSerumEdit(userInfo: any, project: any): boolean {
  return hasAccessCode(userInfo, SERUM_PAGE_EDIT) && canEditSerumProject(userInfo, project);
}

export function canUpdateSerumStatus(userInfo: any, project: any): boolean {
  return (
    hasAccessCode(userInfo, SERUM_STATUS_UPDATE) &&
    (hasAccessCode(userInfo, SERUM_PROJECT_EDIT_ALL) || isProjectMember(userInfo, project))
  );
}

export function canUpdateSerumCage(userInfo: any, project: any): boolean {
  return (
    hasAccessCode(userInfo, SERUM_CAGE_UPDATE) &&
    (hasAccessCode(userInfo, SERUM_PROJECT_EDIT_ALL) || isProjectMember(userInfo, project))
  );
}

export function canEditSerumTiter(userInfo: any, project: any): boolean {
  return (
    hasAccessCode(userInfo, SERUM_TITER_EDIT) &&
    (hasAccessCode(userInfo, SERUM_TITER_EDIT_ALL) ||
      isProjectMember(userInfo, project) ||
      isTiterOwner(userInfo, project))
  );
}

export function canManageSerumTiterFiles(userInfo: any, project: any): boolean {
  return (
    hasAccessCode(userInfo, SERUM_FILE_MANAGE) &&
    (hasAccessCode(userInfo, SERUM_TITER_EDIT_ALL) ||
      isProjectMember(userInfo, project) ||
      isTiterOwner(userInfo, project))
  );
}

export function canEditTiterOrderRecord(userInfo: any, row: any): boolean {
  return (
    hasAccessCode(userInfo, TITER_ORDER_RECORD_EDIT) &&
    (hasAccessCode(userInfo, TITER_ORDER_RECORD_EDIT_ALL) ||
      isTiterOwner(userInfo, row) ||
      isProjectMember(userInfo, { owner: row?.immune_owner, reviewer: row?.reviewer }))
  );
}
