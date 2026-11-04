<script lang="ts" setup>
import type { VbenFormSchema } from '@vben/common-ui';

import { computed, onMounted, ref } from 'vue';

import { AuthenticationLogin, z } from '@vben/common-ui';
import { $t } from '@vben/locales';

import { RECENT_LOGIN_ACCOUNTS_KEY } from '#/constants/storageKeys';
import { useAuthStore } from '#/store';

/** 登录过期弹窗把 show-* 开关传给本组件，需透传给 AuthenticationLogin。 */
defineOptions({ name: 'Login', inheritAttrs: false });

const authStore = useAuthStore();
const loginRef = ref<any>(null);
const recentAccounts = ref<Array<{ lastLoginAt?: string; realName?: string; username: string }>>([]);

const formSchema = computed((): VbenFormSchema[] => {
  const recentAccountSchema: VbenFormSchema[] = recentAccounts.value.length
    ? [
        {
          component: 'VbenSelect',
          componentProps: {
            allowClear: true,
            options: recentAccounts.value.map((account) => ({
              label: account.realName || account.username,
              value: account.username,
            })),
            placeholder: '快速选择账号',
            'onUpdate:modelValue': selectRecentAccount,
          },
          fieldName: 'recentAccount',
          label: '快速选择账号',
        },
      ]
    : [];

  return [
    ...recentAccountSchema,
    {
      component: 'VbenInput',
      componentProps: {
        placeholder: '请输入账号',
      },
      fieldName: 'username',
      label: '账号',
      rules: z.string().min(1, { message: '请输入账号' }),
    },
    {
      component: 'VbenInputPassword',
      componentProps: {
        placeholder: $t('authentication.password'),
      },
      fieldName: 'password',
      label: $t('authentication.password'),
      rules: z.string().min(1, { message: $t('authentication.passwordTip') }),
    },
  ];
});

function loadRecentAccounts() {
  const raw = localStorage.getItem(RECENT_LOGIN_ACCOUNTS_KEY);
  recentAccounts.value = raw ? JSON.parse(raw) : [];
}

function selectRecentAccount(username?: string) {
  const formApi = loginRef.value?.getFormApi?.();
  if (!username || !formApi) return;
  formApi.setFieldValue('username', username);
  const passwordEl = formApi.getFieldComponentRef('password')?.$el;
  (passwordEl?.querySelector?.('input') ?? passwordEl)?.focus?.();
}

onMounted(loadRecentAccounts);
</script>

<template>
  <div>
    <AuthenticationLogin
      v-bind="$attrs"
      ref="loginRef"
      :form-schema="formSchema"
      :loading="authStore.loginLoading"
      @submit="authStore.authLogin"
    />
  </div>
</template>

<style>
/*
 * 登录过期弹窗的层级取页面最大 z-index + 1，可能顶到 2147483647，下拉固定 2000 会被盖住。
 * 下拉层同取最大值、又挂在 body 末尾，同层级时排在后面的在上面；包装层是行内 z-index，只能 !important。
 */
[data-reka-popper-content-wrapper]:has(> [role='listbox']) {
  z-index: 2147483647 !important;
}
</style>
