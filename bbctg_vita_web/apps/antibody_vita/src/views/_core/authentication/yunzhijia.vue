<script lang="ts" setup>
import { onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { LOGIN_PATH } from '@vben/constants';

import { extractApiError } from '#/api/errors';
import { useAuthStore } from '#/store';

defineOptions({ name: 'YunzhijiaLogin' });

const MSG = {
  loading: '正在通过云之家登录...',
  missingTicket: '云之家登录参数缺失，请从云之家重新进入',
  notBound: '该云之家账号尚未绑定系统用户，请联系管理员',
  disabled: '账号已被禁用，请联系管理员',
  retry: '云之家登录未成功，请返回云之家重新进入',
} as const;

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const message = ref(MSG.loading);
const showRetryHint = ref(false);

function resolveFailure(err: unknown) {
  const backend = extractApiError(err).backendMessage || '';
  if (backend.includes('尚未绑定')) {
    return { message: MSG.notBound, showRetryHint: false };
  }
  if (backend.includes('未启用') || backend.includes('禁用')) {
    return { message: MSG.disabled, showRetryHint: false };
  }
  return { message: MSG.retry, showRetryHint: true };
}

onMounted(async () => {
  const ticket = String(route.query.ticket || route.query.code || '');
  if (!ticket) {
    message.value = MSG.missingTicket;
    showRetryHint.value = true;
    return;
  }

  try {
    await authStore.authYunzhijiaLogin(ticket);
  } catch (error: unknown) {
    const resolved = resolveFailure(error);
    message.value = resolved.message;
    showRetryHint.value = resolved.showRetryHint;
  }
});

function goPasswordLogin() {
  void router.replace(LOGIN_PATH);
}
</script>

<template>
  <div class="yunzhijia-login">
    <p :class="{ 'yunzhijia-login__error': message !== MSG.loading }">
      {{ message }}
    </p>
    <p v-if="showRetryHint" class="yunzhijia-login__hint">
      若仍无法进入，可关闭本页后从云之家再次打开应用重试。
    </p>
    <el-button
      v-if="message !== MSG.loading"
      class="yunzhijia-login__fallback"
      link
      type="primary"
      @click="goPasswordLogin"
    >
      改用账号密码登录
    </el-button>
  </div>
</template>

<style scoped>
.yunzhijia-login {
  padding: 48px 24px;
  text-align: center;
}

.yunzhijia-login__error {
  color: var(--el-color-danger);
}

.yunzhijia-login__hint {
  margin-top: 12px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.yunzhijia-login__fallback {
  margin-top: 16px;
}
</style>
