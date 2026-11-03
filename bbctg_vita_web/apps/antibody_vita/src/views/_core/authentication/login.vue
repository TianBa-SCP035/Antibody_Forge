<script lang="ts" setup>
import type { VbenFormSchema } from '@vben/common-ui';

import { computed, defineComponent, h, onMounted, ref } from 'vue';

import { AuthenticationLogin, VbenButton, z } from '@vben/common-ui';
import { $t } from '@vben/locales';

import { RECENT_LOGIN_ACCOUNTS_KEY } from '#/constants/storageKeys';
import { useAuthStore } from '#/store';

/** 登录过期弹窗把 show-* 开关传给本组件，需透传给 AuthenticationLogin。 */
defineOptions({ name: 'Login', inheritAttrs: false });

const authStore = useAuthStore();
const loginRef = ref<any>(null);
const recentAccounts = ref<Array<{ lastLoginAt?: string; realName?: string; username: string }>>([]);

// 用按钮而不是下拉：下拉层级低于登录过期弹窗会被盖住，且只有一个账号时选了也不触发变化。
const RecentAccounts = defineComponent({
  name: 'RecentAccounts',
  inheritAttrs: false,
  setup() {
    return () =>
      h('div', { class: 'flex w-full flex-wrap items-center gap-2' }, [
        h('span', { class: 'text-muted-foreground text-sm' }, '最近登录'),
        ...recentAccounts.value.map((account) =>
          h(
            VbenButton,
            {
              class: 'h-7 px-3',
              size: 'sm',
              title: account.username,
              type: 'button',
              variant: 'outline',
              onClick: () => selectRecentAccount(account.username),
            },
            () => account.realName || account.username,
          ),
        ),
      ]);
  },
});

const formSchema = computed((): VbenFormSchema[] => {
  const recentAccountSchema: VbenFormSchema[] = recentAccounts.value.length
    ? [
        {
          component: RecentAccounts,
          fieldName: 'recentAccount',
          label: '最近登录',
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

function selectRecentAccount(username: string) {
  const formApi = loginRef.value?.getFormApi?.();
  if (!formApi) return;
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
