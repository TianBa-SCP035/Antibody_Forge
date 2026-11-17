/**
 * 从宿主应用读取登录账号和菜单。本文件是宠物访问宿主状态的唯一入口，
 * 使只需账号或页面列表的模块无需引入业务 API。
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

/** 返回稳定的账号 ID，使同一浏览器上的多个用户各自保存宠物记忆。 */
export function currentUserKey(): string {
  try {
    const info: any = useUserStore().userInfo;
    return text(info?.userId ?? info?.id ?? info?.username);
  } catch {
    return '';
  }
}

let hostRouter: Router | null = null;

/** 宠物组件注册宿主路由；组件挂载在应用内部，因此可在其中调用 useRouter()。 */
export function setHostRouter(router: Router) {
  hostRouter = router;
}

export type MenuPage = { title: string; path: string };

/**
 * 返回当前账号可打开的菜单叶子页面；路由仅包含该账号有权访问的项。
 * 排除需要 ID 的页面、登录页和标题未翻译的页面。
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

/** 模拟用户点击菜单打开页面；拒绝不在菜单中的路径。 */
export async function openMenuPage(path: string): Promise<boolean> {
  if (!hostRouter || !menuPages().some((p) => p.path === path)) return false;
  await hostRouter.push(path);
  return hostRouter.currentRoute.value.path === path;
}
