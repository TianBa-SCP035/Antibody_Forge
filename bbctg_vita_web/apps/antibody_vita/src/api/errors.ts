import { ElMessage } from 'element-plus';

import { isUnauthorizedError } from '#/utils/auth-session';

export type MessageLevel = 'error' | 'warning';

export type OperationMessages = {
  default?: string;
  timeout?: string;
  forbidden?: string;
  notFound?: string;
  network?: string;
  errorCodes?: Record<string, { level?: MessageLevel; message: string }>;
};

export type ExtractedApiError = {
  backendMessage?: string;
  businessCode?: number;
  errorCode?: string;
  httpStatus?: number;
  isNetworkError: boolean;
  isTimeout: boolean;
};

function readBody(err: unknown): Record<string, unknown> {
  const e = err as {
    code?: unknown;
    data?: unknown;
    message?: unknown;
    response?: { data?: unknown };
  };
  const candidates = [e?.response?.data, e?.data, err];
  for (const candidate of candidates) {
    if (candidate && typeof candidate === 'object') {
      return candidate as Record<string, unknown>;
    }
  }
  return {};
}

export function extractApiError(err: unknown): ExtractedApiError {
  const e = err as {
    code?: string;
    message?: string;
    response?: { status?: number; data?: unknown };
    status?: number;
  };
  const body = readBody(err);
  const httpStatus = e?.response?.status ?? e?.status;
  const backendMessage =
    (typeof body.message === 'string' && body.message) ||
    (typeof body.detail === 'string' && body.detail) ||
    (typeof body.error === 'string' && body.error) ||
    undefined;
  const isTimeout =
    e?.code === 'ECONNABORTED' ||
    httpStatus === 408 ||
    /timeout/i.test(String(e?.message ?? ''));
  const isNetworkError =
    !httpStatus &&
    (e?.code === 'ERR_NETWORK' ||
      /network error/i.test(String(e?.message ?? '')));

  return {
    backendMessage,
    businessCode: typeof body.code === 'number' ? body.code : undefined,
    errorCode:
      (typeof body.errorCode === 'string' && body.errorCode) ||
      (typeof body.error_code === 'string' && body.error_code) ||
      undefined,
    httpStatus,
    isNetworkError,
    isTimeout,
  };
}

function matchErrorCodeMessage(
  errorCode: string | undefined,
  errorCodes: OperationMessages['errorCodes'],
): { level: MessageLevel; message: string } | null {
  if (!errorCode || !errorCodes?.[errorCode]) {
    return null;
  }
  const item = errorCodes[errorCode];
  return { level: item.level ?? 'error', message: item.message };
}

export function resolveUserMessage(
  err: unknown,
  opts?: { fallback?: string; messages?: OperationMessages },
): { level: MessageLevel; message: string } {
  const extracted = extractApiError(err);
  const messages = opts?.messages;

  const errorCodeHit = matchErrorCodeMessage(
    extracted.errorCode,
    messages?.errorCodes,
  );
  if (errorCodeHit) {
    return errorCodeHit;
  }

  if (extracted.isTimeout && messages?.timeout) {
    return { level: 'error', message: messages.timeout };
  }
  if (extracted.isNetworkError && messages?.network) {
    return { level: 'error', message: messages.network };
  }
  if (extracted.httpStatus === 403 && messages?.forbidden) {
    return { level: 'error', message: messages.forbidden };
  }
  if (extracted.httpStatus === 404 && messages?.notFound) {
    return { level: 'error', message: messages.notFound };
  }

  if (extracted.isTimeout) {
    return { level: 'error', message: '请求超时，请稍后再试' };
  }
  if (extracted.isNetworkError) {
    return { level: 'error', message: '网络异常，请检查连接' };
  }
  if (extracted.httpStatus === 403) {
    return { level: 'error', message: '没有权限执行此操作' };
  }
  if (extracted.httpStatus === 404) {
    return { level: 'error', message: '请求的资源不存在' };
  }
  if (extracted.httpStatus && extracted.httpStatus >= 500) {
    return { level: 'error', message: '服务器异常，请联系管理员' };
  }

  if (extracted.backendMessage) {
    return { level: 'error', message: extracted.backendMessage };
  }

  if (messages?.default) {
    return { level: 'error', message: messages.default };
  }

  return {
    level: 'error',
    message: opts?.fallback ?? '操作失败，请重试',
  };
}

export function toastApiError(err: unknown, vbenFallbackMsg = '') {
  if (isUnauthorizedError(err)) {
    return;
  }
  const { message } = resolveUserMessage(err, { fallback: vbenFallbackMsg });
  ElMessage.error(message);
}

export function notifyApiError(
  err: unknown,
  opts?: {
    fallback?: string;
    level?: MessageLevel;
    messages?: OperationMessages;
  },
) {
  if (isUnauthorizedError(err)) {
    return;
  }
  const resolved = resolveUserMessage(err, opts);
  const level = opts?.level ?? resolved.level;
  ElMessage[level](resolved.message);
}

export class ApiFetchError extends Error {
  readonly body?: unknown;
  readonly status?: number;

  constructor(message: string, status?: number, body?: unknown) {
    super(message);
    this.name = 'ApiFetchError';
    this.status = status;
    this.body = body;
  }
}

export async function fetchApiResource(
  url: string,
  init?: RequestInit,
): Promise<Response> {
  const response = await fetch(url, init);
  const contentType = response.headers.get('content-type') ?? '';

  if (response.ok) {
    if (contentType.includes('application/json')) {
      let body: unknown;
      try {
        body = await response.json();
      } catch {
        body = null;
      }
      const message =
        typeof (body as { message?: string })?.message === 'string'
          ? (body as { message: string }).message
          : '下载失败';
      throw new ApiFetchError(message, response.status, body);
    }
    return response;
  }

  let body: unknown;
  try {
    body = JSON.parse(await response.text());
  } catch {
    body = null;
  }
  const message =
    typeof (body as { message?: string })?.message === 'string'
      ? (body as { message: string }).message
      : `HTTP ${response.status}`;
  throw new ApiFetchError(message, response.status, body);
}
