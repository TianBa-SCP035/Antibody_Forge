import type { RouteRecordRaw } from 'vue-router';

import { filterRouteTree, type FeatureFilterState } from './featureFilter';

function normalizeRoutePath(path: string): string {
  const raw = path.split(/[?#]/)[0]?.trim() || '';
  if (!raw) return '';
  const withSlash = raw.startsWith('/') ? raw : `/${raw}`;
  return withSlash.length > 1 ? withSlash.replace(/\/+$/, '') : withSlash;
}

function joinRoutePath(parentPath: string, childPath: string): string {
  if (!childPath) return parentPath;
  if (childPath.startsWith('/')) return normalizeRoutePath(childPath);
  const base = parentPath === '/' ? '' : parentPath.replace(/\/+$/, '');
  return normalizeRoutePath(`${base}/${childPath}`);
}

function findRouteChain(
  routes: RouteRecordRaw[],
  targetPath: string,
  parentPath = '',
  ancestors: RouteRecordRaw[] = [],
): null | RouteRecordRaw[] {
  for (const route of routes) {
    const currentPath = joinRoutePath(parentPath, route.path);
    const chain = [...ancestors, route];
    if (currentPath === targetPath) {
      return chain;
    }
    if (route.children?.length) {
      const matched = findRouteChain(
        route.children,
        targetPath,
        currentPath,
        chain,
      );
      if (matched) {
        return matched;
      }
    }
  }
  return null;
}

// 链上每一级的 authority 都要命中；只显示 403 页的路由（menuVisibleWithForbidden）不算能进入
function hasRouteChainAuthority(
  chain: RouteRecordRaw[],
  hasAccessByCodes: (codes: string[]) => boolean,
): boolean {
  return chain.every((route) => {
    const authority = route.meta?.authority;
    return !authority || hasAccessByCodes(authority);
  });
}

export function canAccessRoutePath(
  path: string,
  routes: RouteRecordRaw[],
  hasAccessByCodes: (codes: string[]) => boolean,
  featureFilter?: FeatureFilterState | null,
): boolean {
  const targetPath = normalizeRoutePath(path);
  if (!targetPath) return true;

  const rawChain = findRouteChain(routes, targetPath);
  if (!rawChain) {
    return true;
  }

  let activeChain: null | RouteRecordRaw[] = rawChain;
  if (featureFilter) {
    const filteredRoutes = filterRouteTree(
      routes,
      featureFilter.stateMap,
      featureFilter.treatMissingFeatureAsHidden,
    ) as RouteRecordRaw[];
    activeChain = findRouteChain(filteredRoutes, targetPath);
    if (!activeChain) {
      return false;
    }
  }

  return hasRouteChainAuthority(activeChain, hasAccessByCodes);
}
