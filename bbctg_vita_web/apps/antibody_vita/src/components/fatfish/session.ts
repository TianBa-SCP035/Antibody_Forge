/**
 * The signed-in account and the app's menu, read from the host app. The only place the pet touches host
 * state, so modules that just need "who is this" or "which pages exist" don't pull in business APIs.
 */

import type { Router } from 'vue-router';

import { useAccessStore, useUserStore } from '@vben/stores';

function text(v: unknown): string {
  return v == null ? '' : String(v).trim();
}

export function hasUserToken(): boolean {
  try {
    return Boolean(useAccessStore().accessToken);
  } catch {
    return false;
  }
}

export function currentUserName(): string {
  try {
    const info: any = useUserStore().userInfo;
    return text(info?.realName || info?.username);
  } catch {
    return '';
  }
}

/** Stable per-account id, so local pet memory stays apart when several people log in on one browser. */
export function currentUserKey(): string {
  try {
    const info: any = useUserStore().userInfo;
    return text(info?.userId ?? info?.id ?? info?.username);
  } catch {
    return '';
  }
}

let hostRouter: Router | null = null;

/** The pet component registers the app's router (it is mounted inside the app, so `useRouter()` works there). */
export function setHostRouter(router: Router) {
  hostRouter = router;
}

export type MenuPage = { title: string; path: string };

/**
 * Leaf pages of the menu the signed-in account can open (the router only holds routes the account may access).
 * Pages needing an id (`/edit/:id`), login pages and untranslated titles are left out.
 */
export function menuPages(): MenuPage[] {
  if (!hostRouter) return [];
  const out: MenuPage[] = [];
  for (const r of hostRouter.getRoutes()) {
    const title = text(r.meta?.title);
    if (!title || /^page\./.test(title) || r.meta?.hideInMenu || r.children?.length) continue;
    if (r.path.includes(':') || r.path.startsWith('/auth')) continue;
    if (!out.some((p) => p.path === r.path)) out.push({ title, path: r.path });
  }
  return out;
}

/** Opens a menu page as if the user clicked it; anything not in the menu is refused. */
export async function openMenuPage(path: string): Promise<boolean> {
  if (!hostRouter || !menuPages().some((p) => p.path === path)) return false;
  await hostRouter.push(path);
  return hostRouter.currentRoute.value.path === path;
}
