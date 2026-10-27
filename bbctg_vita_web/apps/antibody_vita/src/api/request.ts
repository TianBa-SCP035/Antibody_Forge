/**
 * 该文件可自行根据业务逻辑进行调整
 */
import type { RequestClientOptions } from '@vben/request';

import { useAppConfig } from '@vben/hooks';
import { preferences } from '@vben/preferences';
import {
  defaultResponseInterceptor,
  errorMessageResponseInterceptor,
  RequestClient,
} from '@vben/request';
import { useAccessStore } from '@vben/stores';

import { toastApiError } from '#/api/errors';
import { cleanFieldText } from '#/components/workbench/clipboardGrid';
import {
  handleUnauthorizedError,
  isUnauthorizedError,
} from '#/utils/auth-session';

const { apiURL } = useAppConfig(import.meta.env, import.meta.env.PROD);

function sanitizeRequestPayload(value: unknown, key = ''): unknown {
  if (key && key.toLowerCase().includes('password')) {
    return value;
  }
  if (typeof value === 'string') {
    return cleanFieldText(value, { keepBreaks: true });
  }
  if (Array.isArray(value)) {
    return value.map((item) => sanitizeRequestPayload(item));
  }
  if (
    value &&
    typeof value === 'object' &&
    Object.prototype.toString.call(value) === '[object Object]'
  ) {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      out[k] = sanitizeRequestPayload(v, k);
    }
    return out;
  }
  return value;
}

function createRequestClient(baseURL: string, options?: RequestClientOptions) {
  const client = new RequestClient({
    ...options,
    baseURL,
  });

  function formatToken(token: null | string) {
    return token ? `Bearer ${token}` : null;
  }

  client.addRequestInterceptor({
    fulfilled: async (config) => {
      const accessStore = useAccessStore();

      config.headers.Authorization = formatToken(accessStore.accessToken);
      config.headers['Accept-Language'] = preferences.app.locale;
      if (config.data !== undefined) {
        config.data = sanitizeRequestPayload(config.data);
      }
      return config;
    },
  });

  client.addResponseInterceptor(
    defaultResponseInterceptor({
      codeField: 'code',
      dataField: 'data',
      successCode: 0,
    }),
  );

  client.addResponseInterceptor({
    rejected: async (error) => {
      await handleUnauthorizedError(error);
      throw error;
    },
  });

  client.addResponseInterceptor(
    errorMessageResponseInterceptor((msg: string, error) => {
      if (isUnauthorizedError(error)) {
        return;
      }
      if (
        (error as { config?: { skipErrorHandler?: boolean } })?.config
          ?.skipErrorHandler
      ) {
        return;
      }
      toastApiError(error, msg);
    }),
  );

  return client;
}

export const requestClient = createRequestClient(apiURL, {
  responseReturn: 'data',
});

export const skipGlobalErrorHandler = {
  skipErrorHandler: true,
} as Parameters<typeof requestClient.get>[1];

export const baseRequestClient = new RequestClient({ baseURL: apiURL });
