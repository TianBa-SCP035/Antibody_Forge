import { useAccessStore } from '@vben/stores';

import { ApiFetchError, fetchApiResource } from '#/api/errors';
import { handleUnauthorizedError } from '#/utils/auth-session';

function withAccessToken(init: RequestInit = {}): RequestInit {
  const headers = new Headers(init.headers);
  const token = useAccessStore().accessToken;
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  return { ...init, headers };
}

async function fetchWithSession(
  url: string,
  init: RequestInit = {},
  options: { allowJson?: boolean } = {},
) {
  try {
    return await fetchApiResource(url, withAccessToken(init), options);
  } catch (error) {
    if (error instanceof ApiFetchError && error.status === 401) {
      await handleUnauthorizedError({ response: { status: 401 } });
    }
    throw error;
  }
}

export async function fetchFileBlob(
  url: string,
  init: RequestInit = {},
): Promise<Blob> {
  return (await fetchWithSession(url, init)).blob();
}

export async function fetchFileJson<T>(
  url: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetchWithSession(url, init, { allowJson: true });
  return response.json() as Promise<T>;
}

export function downloadBlob(blob: Blob, fileName: string) {
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = fileName || 'download';
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}

export async function downloadFile(
  url: string,
  fileName: string,
  init: RequestInit = {},
) {
  downloadBlob(await fetchFileBlob(url, init), fileName);
}
