import type { UserInfo } from '@vben/types';

import { requestClient } from '#/api/request';

/** Personal center fields returned by GET /user/info */
export interface ProfileUserInfo extends UserInfo {
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

export async function updateProfileSignatureApi(profileSignature: string) {
  return requestClient.put<ProfileUserInfo>('/auth/user/profile', {
    profileSignature,
  });
}

export async function changePasswordApi(data: { newPassword: string }) {
  return requestClient.post('/auth/user/change_password', data);
}
