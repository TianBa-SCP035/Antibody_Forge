import type { Recordable, UserInfo } from '@vben/types';

import { ref } from 'vue';
import { useRouter } from 'vue-router';

import { LOGIN_PATH } from '@vben/constants';
import { resetAllStores, useAccessStore, useUserStore } from '@vben/stores';

import { ElNotification } from 'element-plus';
import { defineStore } from 'pinia';

import {
  getAccessCodesApi,
  getUserInfoApi,
  loginApi,
  logoutApi,
  yunzhijiaLoginApi,
} from '#/api';
import { $t } from '#/locales';
import {
  createAccessChecker,
  resolveUserStartPath,
} from '#/views/Home/home-data';

export const useAuthStore = defineStore('auth', () => {
  const accessStore = useAccessStore();
  const userStore = useUserStore();
  const router = useRouter();

  const loginLoading = ref(false);
  const RECENT_LOGIN_ACCOUNTS_KEY = `ANTIBODY_RECENT_LOGIN_ACCOUNTS_${location.hostname}`;

  /**
   * 异步处理登录操作
   * Asynchronously handle the login process
   * @param params 登录表单数据
   */
  async function authLogin(
    params: Recordable<any>,
    onSuccess?: () => Promise<void> | void,
  ) {
    // 异步处理用户登录操作并获取 accessToken
    let userInfo: null | UserInfo = null;
    try {
      loginLoading.value = true;
      const { accessToken } = await loginApi(params);
      if (accessToken) {
        userInfo = await completeLogin(accessToken, onSuccess);
        saveRecentLoginAccount(String(params?.username || ''), userInfo);
      }
    } finally {
      loginLoading.value = false;
    }

    return {
      userInfo,
    };
  }

  async function authYunzhijiaLogin(ticket: string) {
    loginLoading.value = true;
    try {
      const { accessToken } = await yunzhijiaLoginApi(ticket);
      return await completeLogin(accessToken);
    } finally {
      loginLoading.value = false;
    }
  }

  async function completeLogin(
    accessToken: string,
    onSuccess?: () => Promise<void> | void,
  ) {
    accessStore.setAccessToken(accessToken);

    const [userInfo, accessCodes] = await Promise.all([
      fetchUserInfo(),
      getAccessCodesApi(),
    ]);

    userStore.setUserInfo(userInfo);
    accessStore.setAccessCodes(accessCodes);

    if (accessStore.loginExpired) {
      accessStore.setLoginExpired(false);
    } else {
      onSuccess
        ? await onSuccess?.()
        : await router.push(
            resolveUserStartPath(
              userInfo.homePath,
              createAccessChecker(accessStore.accessCodes),
            ),
          );
    }

    if (userInfo?.realName) {
      ElNotification({
        message: `${$t('authentication.loginSuccessDesc')}:${userInfo?.realName}`,
        title: $t('authentication.loginSuccess'),
        type: 'success',
      });
    }
    return userInfo;
  }

  async function logout(redirect: boolean = true) {
    try {
      await logoutApi();
    } catch {
      // 不做任何处理
    }
    resetAllStores();
    accessStore.setLoginExpired(false);

    // 回登录页带上当前路由地址
    await router.replace({
      path: LOGIN_PATH,
      query: redirect
        ? {
            redirect: encodeURIComponent(router.currentRoute.value.fullPath),
          }
        : {},
    });
  }

  async function fetchUserInfo() {
    const userInfo = await getUserInfoApi();
    userStore.setUserInfo(userInfo);
    return userInfo;
  }

  function $reset() {
    loginLoading.value = false;
  }

  function saveRecentLoginAccount(username: string, userInfo: null | UserInfo) {
    if (!username) return;
    const raw = localStorage.getItem(RECENT_LOGIN_ACCOUNTS_KEY);
    const accounts = raw ? JSON.parse(raw) : [];
    const nextAccount = {
      lastLoginAt: new Date().toISOString(),
      realName: userInfo?.realName || username,
      username,
    };
    const nextAccounts = [
      nextAccount,
      ...accounts.filter((item: any) => item?.username !== username),
    ].slice(0, 5);
    localStorage.setItem(RECENT_LOGIN_ACCOUNTS_KEY, JSON.stringify(nextAccounts));
  }

  return {
    $reset,
    authLogin,
    authYunzhijiaLogin,
    fetchUserInfo,
    loginLoading,
    logout,
  };
});
