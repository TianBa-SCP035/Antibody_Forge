<script setup lang="ts">
import type { ProfileUserInfo } from '#/api';

import { computed, onMounted, ref } from 'vue';

import { preferences } from '@vben/preferences';
import { useUserStore } from '@vben/stores';

import {
  ElButton,
  ElCard,
  ElInput,
  ElMessage,
  ElTag,
} from 'element-plus';

import {
  changePasswordApi,
  getUserInfoApi,
  updateProfileSignatureApi,
} from '#/api';

defineOptions({ name: 'ProfilePage' });

const userStore = useUserStore();
const loading = ref(true);
const profile = ref<ProfileUserInfo | null>(null);
const signature = ref('');
const savingSignature = ref(false);
const passwordForm = ref({ newPassword: '', confirmPassword: '' });
const savingPassword = ref(false);

const avatarUrl = computed(() => {
  const avatar = profile.value?.avatar || preferences.app.defaultAvatar;
  if (!avatar) return '';
  if (/^https?:\/\//i.test(avatar)) return avatar;
  return avatar.startsWith('/') ? avatar : `/${avatar}`;
});

const displayName = computed(
  () => profile.value?.realName || profile.value?.username || '—',
);

const orgLine = computed(() =>
  [profile.value?.department, profile.value?.groupName].filter(Boolean).join(' · '),
);

const signaturePreview = computed(() => profile.value?.profileSignature?.trim() || '');

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
    const data = await updateProfileSignatureApi(signature.value);
    profile.value = data;
    userStore.setUserInfo(data);
    ElMessage.success('个性名片已保存');
  } catch (error: any) {
    ElMessage.error(error?.message || '保存失败');
  } finally {
    savingSignature.value = false;
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
    await changePasswordApi({ newPassword });
    passwordForm.value = { newPassword: '', confirmPassword: '' };
    await loadProfile();
    ElMessage.success(
      isFirst ? '登录密码已设置' : '密码已更新，下次请使用新密码登录',
    );
  } catch (error: any) {
    ElMessage.error(error?.message || '密码保存失败');
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
        <!-- 顶栏摘要 -->
        <ElCard shadow="never" class="panel-card panel-card--hero profile-layout__hero">
          <div class="hero-inner">
            <div class="hero-avatar-wrap">
              <img v-if="avatarUrl" :src="avatarUrl" alt="" class="hero-avatar" />
            </div>
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

        <!-- 左：我的信息（通高） -->
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

        <!-- 右：名片 + 密码（上下叠放） -->
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
  </div>
</template>

<style scoped>
.profile-shell {
  box-sizing: border-box;
  width: 100%;
  min-height: 100vh;
  padding: 20px 24px 32px;
  background: linear-gradient(180deg, #e8f0ff 0%, #f0f4f8 38%, #f8fafc 70%, #fff 100%);
}

.profile-inner {
  max-width: 1000px;
  margin: 0 auto;
}

/* 交错布局：顶栏通栏 + 左信息 / 右双卡 */
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

/* 通用卡片 */
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
    rgba(64, 158, 255, 0.1) 0%,
    rgba(255, 255, 255, 0.95) 48%,
    #fff 100%
  );
}

.panel-card--info :deep(.el-card__body) {
  padding-top: 4px;
  background: linear-gradient(180deg, #f4f8ff 0%, #fafcff 35%, #fff 100%);
}

.panel-card--signature :deep(.el-card__body) {
  background: linear-gradient(180deg, #f0faf4 0%, #f8fffb 40%, #fff 100%);
}

.panel-card--password :deep(.el-card__body) {
  background: linear-gradient(180deg, #fff9f2 0%, #fffcf8 40%, #fff 100%);
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

/* 标题区：标题旁小色条（非卡片侧边条） */
.panel-head {
  padding: 18px 20px 14px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
}

.panel-card--info .panel-head {
  background: linear-gradient(90deg, rgba(64, 158, 255, 0.07) 0%, transparent 70%);
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
  background: linear-gradient(180deg, #409eff, #79bbff);
}

.panel-head__mark--green {
  background: linear-gradient(180deg, #67c23a, #95d475);
}

.panel-head__mark--amber {
  background: linear-gradient(180deg, #e6a23c, #f3d19e);
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

/* Hero */
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
  flex-shrink: 0;
  padding: 2px;
  border-radius: 14px;
  background: linear-gradient(135deg, #409eff, #79bbff);
  box-shadow: 0 4px 14px rgba(64, 158, 255, 0.22);
}

.hero-avatar {
  display: block;
  width: 76px;
  height: 76px;
  border-radius: 12px;
  object-fit: cover;
  border: 2px solid #fff;
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
  color: #606266;
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

/* 内部表格：无边框、值右对齐 */
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
  color: #909399;
}

.info-table__value {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  text-align: right;
  word-break: break-word;
}

/* 名片 / 密码 */
.signature-input :deep(.el-textarea__inner) {
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.9);
  border-color: rgba(103, 194, 58, 0.22);
}

.signature-input :deep(.el-textarea__inner:focus) {
  border-color: #67c23a;
  background: #fff;
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
  color: #606266;
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
</style>
