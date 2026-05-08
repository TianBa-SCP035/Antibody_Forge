import { RequestClient } from '@vben/request';

const serumApiURL = import.meta.env.VITE_SERUM_API_URL || '/serum-api';

const request = new RequestClient({
  baseURL: serumApiURL,
  timeout: 360_000,
  withCredentials: true,
});

request.addResponseInterceptor({
  fulfilled: (response) => {
    const responseType = response.config.responseType;
    const isBinary =
      responseType === 'blob' ||
      response.data instanceof Blob ||
      response.data instanceof ArrayBuffer;

    if (isBinary) {
      return response.data;
    }

    const data = response.data;
    if (data && typeof data === 'object' && 'code' in data && data.code !== 20000) {
      throw new Error(data.message || 'Error');
    }

    return data;
  },
});

export default function legacyRequest(config: any) {
  return request.request(config.url, config);
}
