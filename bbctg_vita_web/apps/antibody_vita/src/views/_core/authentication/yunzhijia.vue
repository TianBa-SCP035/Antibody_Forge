<script lang="ts" setup>
import { onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { LOGIN_PATH } from '@vben/constants';

import { ElMessage } from 'element-plus';

import { useAuthStore } from '#/store';

defineOptions({ name: 'YunzhijiaLogin' });

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const message = ref('正在通过云之家登录...');

onMounted(async () => {
  const ticket = String(route.query.ticket || route.query.code || '');
  if (!ticket) {
    message.value = '云之家登录参数缺失';
    ElMessage.error(message.value);
    await router.replace(LOGIN_PATH);
    return;
  }

  try {
    await authStore.authYunzhijiaLogin(ticket);
  } catch {
    message.value = '云之家登录失败，请联系管理员确认账号绑定';
  }
});
</script>

<template>
  <div class="yunzhijia-login">
    {{ message }}
  </div>
</template>

<style scoped>
.yunzhijia-login {
  padding: 48px;
  text-align: center;
}
</style>
