<script lang="ts" setup>
// FatFishPet 位于 app.vue，需覆盖登录页和业务页。
import { computed, watch } from 'vue';
import { useRouter } from 'vue-router';

import { AuthenticationLoginExpiredModal } from '@vben/common-ui';
import { useWatermark } from '@vben/hooks';
import { BasicLayout, LockScreen, UserDropdown } from '@vben/layouts';
import { preferences } from '@vben/preferences';
import { useAccessStore, useUserStore } from '@vben/stores';

import { $t } from '#/locales';
import { useAuthStore } from '#/store';
import LoginForm from '#/views/_core/authentication/login.vue';

const router = useRouter();
const userStore = useUserStore();
const authStore = useAuthStore();
const accessStore = useAccessStore();
const { destroyWatermark, updateWatermark } = useWatermark();

const menus = computed(() => [
  {
    handler: () => {
      router.push({ name: 'Profile' });
    },
    icon: 'lucide:user',
    text: $t('page.auth.profile'),
  },
]);

const avatar = computed(() => {
  return userStore.userInfo?.avatar ?? preferences.app.defaultAvatar;
});

const userDisplayName = computed(() => {
  return (
    userStore.userInfo?.realName ||
    userStore.userInfo?.username ||
    ''
  );
});

const userTagText = computed(() => {
  const info = userStore.userInfo as Record<string, any> | null;
  return info?.department || info?.groupName || 'Biocytogen';
});

const userDescription = computed(() => {
  const info = userStore.userInfo as Record<string, any> | null;
  return (
    info?.profileSignature ||
    info?.email ||
    'Biocytogen'
  );
});

async function handleLogout() {
  await authStore.logout(false);
}

watch(
  () => ({
    enable: preferences.app.watermark,
    content: preferences.app.watermarkContent,
  }),
  async ({ enable, content }) => {
    if (enable) {
      await updateWatermark({
        content:
          content ||
          [userStore.userInfo?.username, userStore.userInfo?.realName].filter(Boolean).join(' - ') || 'Biocytogen',
      });
    } else {
      destroyWatermark();
    }
  },
  {
    immediate: true,
  },
);
</script>

<template>
  <BasicLayout @clear-preferences-and-logout="handleLogout">
    <template #user-dropdown>
      <UserDropdown
        :avatar
        :description="userDescription"
        :menus
        :tag-text="userTagText"
        :text="userDisplayName"
        @logout="handleLogout"
      />
    </template>
    <template #extra>
      <AuthenticationLoginExpiredModal
        v-model:open="accessStore.loginExpired"
        :avatar
      >
        <LoginForm
          :show-code-login="false"
          :show-qrcode-login="false"
          :show-third-party-login="false"
        />
      </AuthenticationLoginExpiredModal>
    </template>
    <template #lock-screen>
      <LockScreen :avatar @to-login="handleLogout" />
    </template>
  </BasicLayout>
</template>
