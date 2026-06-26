import { LOGIN_PATH } from '@vben/constants';
import { useAccessStore } from '@vben/stores';

import { ElMessage } from 'element-plus';

import { router } from '#/router';
import { useAuthStore } from '#/store';

const MSG = {
  disabled: '账号已被禁用，请联系管理员',
  expired: '登录已过期，请重新登录',
  loginFailed: '用户名或密码错误',
} as const;

function isAuthRoute(path: string) {
  return path === LOGIN_PATH || path.startsWith('/auth/');
}

function readErrorBody(error: unknown): Record<string, unknown> {
  const e = error as { response?: { data?: unknown } };
  const candidates = [e?.response?.data, error];
  for (const candidate of candidates) {
    if (candidate && typeof candidate === 'object') {
      return candidate as Record<string, unknown>;
    }
  }
  return {};
}

function get401Detail(error: unknown): string {
  const data = readErrorBody(error);
  if (typeof data.message === 'string') return data.message;
  if (typeof data.detail === 'string') return data.detail;
  return '';
}

/** RequestClient 会把 axios 401 剥成 body；仅识别 session/账号状态类，不含登录密码错误 */
function isUnwrappedAuthSessionError(error: unknown): boolean {
  const data = readErrorBody(error);
  const msg =
    (typeof data.message === 'string' && data.message) ||
    (typeof data.detail === 'string' && data.detail) ||
    '';
  if (!msg) return false;
  return (
    msg.includes('登录已失效') ||
    msg.includes('用户不存在或已禁用') ||
    msg.includes('账号已被禁用') ||
    (msg.includes('禁用') && msg.includes('用户'))
  );
}

function isTokenExpired(token: string): boolean {
  try {
    const part = token.split('.')[0];
    if (!part) return false;
    const pad = '='.repeat((4 - (part.length % 4)) % 4);
    const { exp } = JSON.parse(
      atob(part.replaceAll('-', '+').replaceAll('_', '/') + pad),
    ) as { exp?: number };
    return !!exp && exp <= Math.floor(Date.now() / 1000);
  } catch {
    return false;
  }
}

export function isUnauthorizedError(error: unknown): boolean {
  const err = error as { response?: { status?: number }; status?: number };
  if (err?.response?.status === 401 || err?.status === 401) {
    return true;
  }
  return isUnwrappedAuthSessionError(error);
}

/** 业务页弹窗重登（保留表单）；登录页则跳回登录 */
async function promptReLogin(message: string, level: 'error' | 'warning') {
  const accessStore = useAccessStore();
  if (accessStore.loginExpired) return;

  ElMessage[level]({ duration: 5000, message, showClose: true });
  accessStore.setAccessToken(null);

  if (isAuthRoute(router.currentRoute.value.path)) {
    await useAuthStore().logout(false);
  } else {
    accessStore.setLoginExpired(true);
  }
}

/** 401 统一入口：登录失败 / 账号禁用 / session 过期 */
export async function handleUnauthorizedError(error: unknown) {
  if (!isUnauthorizedError(error)) return;

  const url = String((error as { config?: { url?: string } })?.config?.url ?? '');
  const detail = get401Detail(error);

  if (url.includes('/auth/login') || url.includes('/auth/yunzhijia')) {
    ElMessage.error(detail || MSG.loginFailed);
    return;
  }

  const message = detail.includes('禁用') ? MSG.disabled : detail || MSG.expired;
  await promptReLogin(message, detail.includes('禁用') ? 'error' : 'warning');
}

/** 冷启动时若本地 token 已过期，清掉后交给路由守卫跳转登录页 */
function clearExpiredTokenOnBoot() {
  const accessStore = useAccessStore();
  if (accessStore.accessToken && isTokenExpired(accessStore.accessToken)) {
    accessStore.setAccessToken(null);
    accessStore.setLoginExpired(false);
  }
}

/** 切回标签页时若 token 已过期则提前弹窗 */
export function initSessionExpiryWatcher() {
  clearExpiredTokenOnBoot();

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState !== 'visible') return;
    const { accessToken, loginExpired } = useAccessStore();
    if (accessToken && !loginExpired && isTokenExpired(accessToken)) {
      void promptReLogin(MSG.expired, 'warning');
    }
  });
}
