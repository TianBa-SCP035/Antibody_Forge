<script lang="ts" setup>
import type { VbenFormSchema } from '@vben/common-ui';

import { computed, onMounted, ref } from 'vue';

import { AuthenticationLogin, z } from '@vben/common-ui';
import { $t } from '@vben/locales';

import { useAuthStore } from '#/store';

defineOptions({ name: 'Login' });

const authStore = useAuthStore();
const loginRef = ref<any>(null);
const recentAccounts = ref<Array<{ lastLoginAt?: string; realName?: string; username: string }>>([]);
const RECENT_LOGIN_ACCOUNTS_KEY = `ANTIBODY_RECENT_LOGIN_ACCOUNTS_${location.hostname}`;

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
  if (!username) return;
  loginRef.value?.getFormApi?.().setFieldValue('username', username);
}

onMounted(loadRecentAccounts);
</script>

<template>
  <div>
    <AuthenticationLogin
      ref="loginRef"
      :form-schema="formSchema"
      :loading="authStore.loginLoading"
      @submit="authStore.authLogin"
    />
  </div>
</template>
