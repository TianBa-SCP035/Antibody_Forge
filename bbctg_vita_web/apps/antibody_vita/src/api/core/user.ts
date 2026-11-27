import type { UserInfo } from '@vben/types';

import { requestClient } from '#/api/request';

/** GET /user/info 返回的个人中心字段。 */
export interface ProfileUserInfo extends UserInfo {
  /** 空串为随机站内头像，text 为姓名文字，其余为图片地址。 */
  avatarSetting?: string;
  builtinAvatars?: string[];
  department?: string;
  email?: string;
  gender?: string;
  groupName?: string;
  hasPassword?: boolean;
  jobNo?: string;
  lastLoginAt?: string;
  mobile?: string;
  positionTitle?: string;
  profileSignature?: string;
}

export async function getUserInfoApi() {
  return requestClient.get<ProfileUserInfo>('/user/info');
}

export async function updateProfileSignatureApi(
  profileSignature: string,
  config?: Parameters<typeof requestClient.put>[2],
) {
  return requestClient.put<ProfileUserInfo>(
    '/auth/user/profile',
    { profileSignature },
    config,
  );
}

export async function updateAvatarApi(
  avatar: string,
  config?: Parameters<typeof requestClient.put>[2],
) {
  return requestClient.put<ProfileUserInfo>('/auth/user/avatar', { avatar }, config);
}

export async function uploadAvatarApi(
  file: File,
  config?: Parameters<typeof requestClient.post>[2],
) {
  const body = new FormData();
  body.append('file', file);
  return requestClient.post<ProfileUserInfo>('/auth/user/avatar/upload', body, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60_000,
    ...config,
  });
}

export async function changePasswordApi(
  data: { newPassword: string },
  config?: Parameters<typeof requestClient.post>[2],
) {
  return requestClient.post('/auth/user/change_password', data, config);
}
