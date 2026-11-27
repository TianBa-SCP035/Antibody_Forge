<script setup lang="ts">
import type { ProfileUserInfo } from '#/api';

import { computed, onMounted, ref, watch } from 'vue';

import { useUserStore } from '@vben/stores';

import {
  ElButton,
  ElCard,
  ElDialog,
  ElInput,
  ElMessage,
  ElTag,
} from 'element-plus';

import {
  changePasswordApi,
  getUserInfoApi,
  updateAvatarApi,
  updateProfileSignatureApi,
  uploadAvatarApi,
} from '#/api';
import { notifyApiError } from '#/api/errors';
import { skipGlobalErrorHandler } from '#/api/request';
import { SYSTEM_ERRORS } from '#/views/System/errors';

defineOptions({ name: 'ProfilePage' });

const userStore = useUserStore();
const loading = ref(true);
const profile = ref<ProfileUserInfo | null>(null);
const signature = ref('');
const savingSignature = ref(false);
const passwordForm = ref({ newPassword: '', confirmPassword: '' });
const savingPassword = ref(false);

const AVATAR_MAX_MB = 5;
const avatarDialog = ref(false);
const avatarBroken = ref(false);
const savingAvatar = ref(false);
const avatarLink = ref('');
const avatarFileInput = ref<HTMLInputElement | null>(null);

const avatarUrl = computed(() => {
  const avatar = profile.value?.avatar || '';
  if (!avatar) return '';
  if (/^https?:\/\//i.test(avatar)) return avatar;
  return avatar.startsWith('/') ? avatar : `/${avatar}`;
});

const avatarSetting = computed(() => profile.value?.avatarSetting || '');
const builtinAvatars = computed(() => profile.value?.builtinAvatars || []);
const customAvatar = computed(() => {
  const value = avatarSetting.value;
  return value && value !== 'text' && !builtinAvatars.value.includes(value) ? value : '';
});

watch(avatarUrl, () => {
  avatarBroken.value = false;
});

const displayName = computed(
  () => profile.value?.realName || profile.value?.username || '—',
);

const avatarText = computed(() => displayName.value.slice(-2).toUpperCase());

const orgLine = computed(() =>
  [profile.value?.department, profile.value?.groupName].filter(Boolean).join(' · '),
);

const hasPassword = computed(() => Boolean(profile.value?.hasPassword));

const passwordMismatch = computed(() => {
  const { newPassword, confirmPassword } = passwordForm.value;
  if (!confirmPassword) return false;
  return newPassword !== confirmPassword;
});

const lastLoginText = computed(() => {
  const raw = profile.value?.lastLoginAt;
  if (!raw) return '';
  const date = new Date(raw);
  return Number.isNaN(date.getTime())
    ? raw
    : date.toLocaleString('zh-CN', { hour12: false });
});

function displayValue(value?: string | null) {
  return value?.trim() ? value : '—';
}

function formatGender(value?: string | null) {
  const map: Record<string, string> = {
    female: '女',
    male: '男',
    unknown: '未知',
  };
  return value ? map[value] || value : '—';
}

const orgFields = computed(() => {
  const p = profile.value;
  return [
    { label: '姓名', value: displayValue(p?.realName) },
    { label: '登录ID', value: displayValue(p?.username) },
    { label: '工号', value: displayValue(p?.jobNo) },
    { label: '部门', value: displayValue(p?.department) },
    { label: '组别', value: displayValue(p?.groupName) },
    { label: '职位', value: displayValue(p?.positionTitle) },
    { label: '性别', value: formatGender(p?.gender) },
    { label: '邮箱', value: displayValue(p?.email) },
    { label: '手机号', value: displayValue(p?.mobile) },
  ];
});

async function loadProfile() {
  loading.value = true;
  try {
    const data = await getUserInfoApi();
    profile.value = data;
    signature.value = data.profileSignature || '';
    userStore.setUserInfo(data);
  } finally {
    loading.value = false;
  }
}

async function handleSaveSignature() {
  savingSignature.value = true;
  try {
    const data = await updateProfileSignatureApi(signature.value, skipGlobalErrorHandler);
    profile.value = data;
    userStore.setUserInfo(data);
    ElMessage.success('个性名片已保存');
  } catch (error: unknown) {
    notifyApiError(error, { messages: SYSTEM_ERRORS.saveProfile });
  } finally {
    savingSignature.value = false;
  }
}

function openAvatarDialog() {
  avatarLink.value = /^https?:\/\//i.test(customAvatar.value) ? customAvatar.value : '';
  avatarDialog.value = true;
}

function applyAvatar(data: ProfileUserInfo) {
  profile.value = data;
  userStore.setUserInfo(data);
  ElMessage.success('头像已更换');
}

async function pickAvatar(value: string) {
  if (savingAvatar.value) return;
  savingAvatar.value = true;
  try {
    applyAvatar(await updateAvatarApi(value, skipGlobalErrorHandler));
  } catch (error: unknown) {
    notifyApiError(error, { messages: SYSTEM_ERRORS.saveAvatar });
  } finally {
    savingAvatar.value = false;
  }
}

function useAvatarLink() {
  const link = avatarLink.value.trim();
  if (!/^https?:\/\/\S+$/i.test(link)) {
    ElMessage.warning('请填写 http:// 或 https:// 开头的图片链接');
    return;
  }
  pickAvatar(link);
}

async function handleAvatarFile(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = '';
  if (!file) return;
  if (file.size > AVATAR_MAX_MB * 1024 * 1024) {
    ElMessage.warning(`图片不能超过 ${AVATAR_MAX_MB}MB`);
    return;
  }
  savingAvatar.value = true;
  try {
    applyAvatar(await uploadAvatarApi(file, skipGlobalErrorHandler));
  } catch (error: unknown) {
    notifyApiError(error, { messages: SYSTEM_ERRORS.saveAvatar });
  } finally {
    savingAvatar.value = false;
  }
}

async function handleSavePassword() {
  const { newPassword, confirmPassword } = passwordForm.value;
  if (newPassword.length < 6) {
    ElMessage.warning('新密码至少需要 6 位');
    return;
  }
  if (newPassword !== confirmPassword) {
    ElMessage.warning('两次输入的新密码不一致');
    return;
  }
  const isFirst = !hasPassword.value;
  savingPassword.value = true;
  try {
    await changePasswordApi({ newPassword }, skipGlobalErrorHandler);
    passwordForm.value = { newPassword: '', confirmPassword: '' };
    await loadProfile();
    ElMessage.success(
      isFirst ? '登录密码已设置' : '密码已更新，下次请使用新密码登录',
    );
  } catch (error: unknown) {
    notifyApiError(error, { messages: SYSTEM_ERRORS.savePassword });
  } finally {
    savingPassword.value = false;
  }
}

onMounted(loadProfile);
</script>

<template>
  <div v-loading="loading" class="profile-shell">
    <div class="profile-inner">
      <div class="profile-layout">
        <ElCard shadow="never" class="panel-card panel-card--hero profile-layout__hero">
          <div class="hero-inner">
            <button
              type="button"
              class="hero-avatar-wrap"
              title="更换头像"
              :disabled="!profile"
              @click="openAvatarDialog"
            >
              <img
                v-if="avatarUrl && !avatarBroken"
                :src="avatarUrl"
                alt=""
                class="hero-avatar"
                @error="avatarBroken = true"
              />
              <span v-else class="hero-avatar hero-avatar--text">{{ avatarText }}</span>
              <span class="hero-avatar-edit">更换</span>
            </button>
            <div class="hero-meta">
              <h1 class="hero-name">{{ displayName }}</h1>
              <p v-if="profile?.username" class="hero-id">{{ profile.username }}</p>
              <p v-if="orgLine" class="hero-org">{{ orgLine }}</p>
              <div v-if="profile?.roles?.length || lastLoginText" class="hero-footer">
                <div v-if="profile?.roles?.length" class="hero-roles">
                  <ElTag
                    v-for="role in profile.roles"
                    :key="role"
                    size="small"
                    round
                    effect="plain"
                  >
                    {{ role }}
                  </ElTag>
                </div>
                <p v-if="lastLoginText" class="hero-login">
                  上次登录 {{ lastLoginText }}
                </p>
              </div>
            </div>
          </div>
        </ElCard>

        <ElCard shadow="never" class="panel-card panel-card--info profile-layout__info">
          <template #header>
            <div class="panel-head">
              <div class="panel-head__title-row">
                <span class="panel-head__mark panel-head__mark--blue" />
                <span class="panel-head__title">我的信息</span>
              </div>
              <p class="panel-head__desc">以下信息由人事同步，仅用于展示</p>
            </div>
          </template>
          <div class="info-table">
            <div
              v-for="row in orgFields"
              :key="row.label"
              class="info-table__row"
            >
              <span class="info-table__label">{{ row.label }}</span>
              <span class="info-table__value">{{ row.value }}</span>
            </div>
          </div>
        </ElCard>

        <div class="profile-layout__aside">
          <ElCard shadow="never" class="panel-card panel-card--signature">
            <template #header>
              <div class="panel-head">
                <div class="panel-head__title-row">
                  <span class="panel-head__mark panel-head__mark--green" />
                  <span class="panel-head__title">个性名片</span>
                </div>
                <p class="panel-head__desc">仅您本人可编辑，保存后更新顶栏展示</p>
              </div>
            </template>
            <ElInput
              v-model="signature"
              type="textarea"
              :rows="4"
              maxlength="255"
              show-word-limit
              placeholder="写一句简介，展示在协作场景中"
              class="signature-input"
            />
            <div class="card-actions">
              <ElButton
                type="primary"
                :loading="savingSignature"
                @click="handleSaveSignature"
              >
                保存名片
              </ElButton>
            </div>
          </ElCard>

          <ElCard shadow="never" class="panel-card panel-card--password">
            <template #header>
              <div class="panel-head">
                <div class="panel-head__title-row">
                  <span class="panel-head__mark panel-head__mark--amber" />
                  <span class="panel-head__title">登录密码</span>
                </div>
                <p class="panel-head__desc">已登录即可修改，无需原密码</p>
              </div>
            </template>
            <div class="password-fields">
              <div class="form-row">
                <label class="form-row__label">登录账号</label>
                <ElInput :model-value="profile?.username || ''" readonly />
              </div>
              <div class="form-row">
                <label class="form-row__label">新密码</label>
                <ElInput
                  v-model="passwordForm.newPassword"
                  type="password"
                  show-password
                  autocomplete="new-password"
                  placeholder="至少 6 位"
                />
              </div>
              <div class="form-row" :class="{ 'form-row--error': passwordMismatch }">
                <label class="form-row__label">确认新密码</label>
                <ElInput
                  v-model="passwordForm.confirmPassword"
                  type="password"
                  show-password
                  autocomplete="new-password"
                  placeholder="再次输入新密码"
                />
                <p v-if="passwordMismatch" class="form-row__error">
                  两次输入的新密码不一致
                </p>
              </div>
            </div>
            <div class="card-actions">
              <ElButton
                type="primary"
                :loading="savingPassword"
                :disabled="passwordMismatch"
                @click="handleSavePassword"
              >
                {{ hasPassword ? '更新密码' : '设置密码' }}
              </ElButton>
            </div>
          </ElCard>
        </div>
      </div>
    </div>

    <ElDialog v-model="avatarDialog" title="更换头像" width="600px" append-to-body>
      <div v-loading="savingAvatar" class="avatar-picker">
        <div class="avatar-grid">
          <button
            type="button"
            class="avatar-option avatar-option--label"
            :class="{ 'is-active': !avatarSetting }"
            title="每天随机换一张站内动图"
            @click="pickAvatar('')"
          >
            随机
          </button>
          <button
            type="button"
            class="avatar-option avatar-option--name"
            :class="{ 'is-active': avatarSetting === 'text' }"
            title="显示姓名文字"
            @click="pickAvatar('text')"
          >
            {{ avatarText }}
          </button>
          <button
            v-if="customAvatar"
            type="button"
            class="avatar-option is-active"
            title="当前自定义头像"
          >
            <img :src="customAvatar" alt="" />
          </button>
          <button
            v-for="src in builtinAvatars"
            :key="src"
            type="button"
            class="avatar-option"
            :class="{ 'is-active': avatarSetting === src }"
            @click="pickAvatar(src)"
          >
            <img :src="src" alt="" loading="lazy" />
          </button>
        </div>
        <p class="avatar-hint">
          默认「随机」：每天从站内动图里随机一张，当天刷新不变；「{{ avatarText }}」为姓名文字头像，不参与随机。
        </p>
        <div class="avatar-custom">
          <ElButton @click="avatarFileInput?.click()">上传图片 / 动图</ElButton>
          <input
            ref="avatarFileInput"
            type="file"
            accept="image/png,image/jpeg,image/gif,image/webp,image/bmp"
            hidden
            @change="handleAvatarFile"
          />
          <ElInput
            v-model="avatarLink"
            clearable
            placeholder="或粘贴图片 / 动图链接 https://…"
            @keyup.enter="useAvatarLink"
          />
          <ElButton type="primary" :disabled="!avatarLink.trim()" @click="useAvatarLink">
            使用链接
          </ElButton>
        </div>
      </div>
    </ElDialog>
  </div>
</template>

<style scoped>
.profile-shell {
  box-sizing: border-box;
  width: 100%;
  min-height: 100vh;
  padding: 20px 24px 32px;
  background: linear-gradient(180deg, #e8f0ff 0%, var(--el-fill-color) 38%, var(--el-fill-color-extra-light) 70%, var(--el-bg-color) 100%);
}

.profile-inner {
  max-width: 1000px;
  margin: 0 auto;
}

.profile-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-areas:
    'hero hero'
    'info aside';
  gap: 16px;
  align-items: stretch;
}

.profile-layout__hero {
  grid-area: hero;
}

.profile-layout__info {
  grid-area: info;
  height: 100%;
}

.profile-layout__aside {
  grid-area: aside;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 100%;
}

@media (max-width: 767px) {
  .profile-layout {
    grid-template-columns: 1fr;
    grid-template-areas:
      'hero'
      'info'
      'aside';
  }
}

.panel-card {
  overflow: hidden;
  border: none;
  border-radius: 14px;
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 8px 24px rgba(15, 23, 42, 0.06);
}

.panel-card :deep(.el-card__header) {
  padding: 0;
  border: none;
  background: transparent;
}

.panel-card :deep(.el-card__body) {
  padding: 0 20px 20px;
}

.panel-card--hero :deep(.el-card__body) {
  padding: 20px 24px;
  background: linear-gradient(
    135deg,
    color-mix(in srgb, var(--el-color-primary) 10%, transparent) 0%,
    rgba(255, 255, 255, 0.95) 48%,
    var(--el-bg-color) 100%
  );
}

.panel-card--info :deep(.el-card__body) {
  padding-top: 4px;
  background: linear-gradient(180deg, var(--el-color-primary-light-9) 0%, var(--el-fill-color-extra-light) 35%, var(--el-bg-color) 100%);
}

.panel-card--signature :deep(.el-card__body) {
  background: linear-gradient(180deg, #f0faf4 0%, #f8fffb 40%, var(--el-bg-color) 100%);
}

.panel-card--password :deep(.el-card__body) {
  background: linear-gradient(180deg, var(--el-color-warning-light-9) 0%, #fffcf8 40%, var(--el-bg-color) 100%);
}

.panel-card--info {
  display: flex;
  flex-direction: column;
}

.panel-card--info :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.panel-head {
  padding: 18px 20px 14px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
}

.panel-card--info .panel-head {
  background: linear-gradient(90deg, color-mix(in srgb, var(--el-color-primary) 7%, transparent) 0%, transparent 70%);
}

.panel-card--signature .panel-head {
  background: linear-gradient(90deg, rgba(103, 194, 58, 0.07) 0%, transparent 70%);
}

.panel-card--password .panel-head {
  background: linear-gradient(90deg, rgba(230, 162, 60, 0.07) 0%, transparent 70%);
}

.panel-head__title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-head__mark {
  width: 3px;
  height: 15px;
  flex-shrink: 0;
  border-radius: 2px;
}

.panel-head__mark--blue {
  background: linear-gradient(180deg, var(--el-color-primary), var(--el-color-primary-light-3));
}

.panel-head__mark--green {
  background: linear-gradient(180deg, var(--el-color-success), var(--el-color-success-light-3));
}

.panel-head__mark--amber {
  background: linear-gradient(180deg, var(--el-color-warning), var(--el-color-warning-light-5));
}

.panel-head__title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2d3d;
  line-height: 1.3;
}

.panel-head__desc {
  margin: 8px 0 0 11px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--el-text-color-secondary);
}

.hero-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  width: 100%;
  min-width: 0;
}

@media (min-width: 640px) {
  .hero-inner {
    flex-direction: row;
    align-items: center;
    gap: 20px;
  }
}

.hero-avatar-wrap {
  position: relative;
  flex-shrink: 0;
  padding: 2px;
  border: none;
  border-radius: 14px;
  background: linear-gradient(135deg, var(--el-color-primary), var(--el-color-primary-light-3));
  box-shadow: 0 4px 14px color-mix(in srgb, var(--el-color-primary) 22%, transparent);
  cursor: pointer;
}

.hero-avatar-edit {
  position: absolute;
  inset: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  font-size: 13px;
  color: #fff;
  background: rgba(15, 23, 42, 0.45);
  opacity: 0;
  transition: opacity 0.15s;
}

.hero-avatar-wrap:hover .hero-avatar-edit {
  opacity: 1;
}

.hero-avatar {
  display: block;
  width: 76px;
  height: 76px;
  border-radius: 12px;
  object-fit: cover;
  border: 2px solid var(--el-bg-color);
  box-sizing: border-box;
}

.hero-avatar--text {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  font-weight: 600;
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}

.avatar-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(64px, 1fr));
  gap: 10px;
}

.avatar-option {
  display: flex;
  align-items: center;
  justify-content: center;
  aspect-ratio: 1;
  padding: 0;
  overflow: hidden;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  background: var(--el-fill-color-extra-light);
  cursor: pointer;
  transition: box-shadow 0.15s, border-color 0.15s;
}

.avatar-option:hover {
  border-color: var(--el-color-primary-light-5);
}

.avatar-option.is-active {
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 2px var(--el-color-primary-light-7);
}

.avatar-option img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-option--label {
  font-size: 14px;
  color: var(--el-text-color-regular);
}

.avatar-option--name {
  font-size: 18px;
  font-weight: 600;
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}

.avatar-hint {
  margin: 12px 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--el-text-color-secondary);
}

.avatar-custom {
  display: flex;
  gap: 8px;
  margin-top: 14px;
}

.hero-meta {
  min-width: 0;
  flex: 1;
  text-align: center;
}

@media (min-width: 640px) {
  .hero-meta {
    text-align: left;
  }
}

.hero-name {
  margin: 0;
  font-size: clamp(1.4rem, 2.8vw, 1.75rem);
  font-weight: 700;
  color: #1f2d3d;
  line-height: 1.25;
}

.hero-id {
  margin: 6px 0 0;
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-regular);
}

.hero-org {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.hero-footer {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 8px 14px;
  margin-top: 10px;
}

@media (min-width: 640px) {
  .hero-footer {
    justify-content: flex-start;
  }
}

.hero-roles {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.hero-login {
  margin: 0;
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

.info-table {
  flex: 1;
  padding: 4px 0 8px;
}

.info-table__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 44px;
  padding: 0 4px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
}

.info-table__row:last-child {
  border-bottom: none;
}

.info-table__label {
  flex-shrink: 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.info-table__value {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  text-align: right;
  word-break: break-word;
}

.signature-input :deep(.el-textarea__inner) {
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.9);
  border-color: rgba(103, 194, 58, 0.22);
}

.signature-input :deep(.el-textarea__inner:focus) {
  border-color: var(--el-color-success);
  background: var(--el-bg-color);
}

.password-fields {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-row__label {
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-regular);
}

.form-row--error :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px var(--el-color-danger) inset;
}

.form-row__error {
  margin: 0;
  font-size: 12px;
  line-height: 1.4;
  color: var(--el-color-danger);
}

.form-row :deep(.el-input__wrapper) {
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.92);
}

.card-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.card-actions .el-button {
  min-width: 108px;
  border-radius: 8px;
}

html.dark .profile-shell {
  background: var(--el-bg-color-page);
}

html.dark .panel-card--hero :deep(.el-card__body),
html.dark .panel-card--signature :deep(.el-card__body),
html.dark .panel-card--password :deep(.el-card__body) {
  background: var(--el-bg-color);
}

html.dark .panel-head,
html.dark .info-table__row {
  border-color: var(--el-border-color-lighter);
}

html.dark .panel-head__title,
html.dark .hero-name {
  color: var(--el-text-color-primary);
}

html.dark .signature-input :deep(.el-textarea__inner),
html.dark .form-row :deep(.el-input__wrapper) {
  background: var(--el-fill-color-blank);
}
</style>
