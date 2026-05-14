<script setup lang="ts">
import type { SystemFeatureFlag, SystemJobRunLog } from '#/api';

import { computed, onMounted, reactive, ref } from 'vue';

import { useAccessStore, useUserStore } from '@vben/stores';

import {
  ArrowDown,
  ArrowUp,
} from '@element-plus/icons-vue';

import {
  ElAlert,
  ElButton,
  ElCard,
  ElDatePicker,
  ElMessage,
  ElOption,
  ElSelect,
  ElSpace,
  ElSwitch,
  ElTabPane,
  ElTable,
  ElTableColumn,
  ElTabs,
  ElTag,
  ElTimePicker,
} from 'element-plus';

import {
  getSystemFeaturesApi,
  getSystemFeatureStatusApi,
  getSystemJobRunLogsApi,
  saveSystemFeatureApi,
} from '#/api';

defineOptions({ name: 'SystemFeatures' });

type ConfiguredFeature = SystemFeatureFlag & { config: Record<string, any> };
type FeatureRow = ConfiguredFeature & { children?: FeatureRow[] };

const accessStore = useAccessStore();
const userStore = useUserStore();

const activeTab = ref('menu');
const loading = ref(false);
const logLoading = ref(false);
const savingCode = ref('');
const errorMessage = ref('');
const features = ref<SystemFeatureFlag[]>([]);
const jobLogs = ref<SystemJobRunLog[]>([]);
const systemStatus = ref<{ server_time?: string; timezone?: string }>({});

const logQuery = reactive({
  date_range: defaultDateRange(),
  job_code: '',
  limit: 50,
  result: '',
});

const currentAccessCodes = computed(() => {
  const userInfo = userStore.userInfo as any;
  return new Set<string>([
    ...accessStore.accessCodes,
    ...((userInfo?.accessCodes as string[] | undefined) || []),
    ...((userInfo?.permissions as string[] | undefined) || []),
  ]);
});

const canManageFeatures = computed(() => {
  const userInfo = userStore.userInfo as any;
  return Boolean(userInfo?.isSuperuser) || currentAccessCodes.value.has('system.feature.manage');
});

const configuredFeatures = computed(() => features.value.map((item) => ({ ...item, config: item.config || {} })));
const menuFeatures = computed(() => sortFeatures(configuredFeatures.value.filter((item) => item.category === 'menu')));
const featureFlags = computed(() => sortFeatures(configuredFeatures.value.filter((item) => item.category === 'feature')));
const jobFeatures = computed(() => sortFeatures(configuredFeatures.value.filter((item) => item.category === 'job')));

const menuTree = computed(() => {
  const rows = menuFeatures.value.map((item) => ({ ...item, children: [] as FeatureRow[] }));
  const byCode = new Map(rows.map((item) => [item.code, item]));
  const roots: FeatureRow[] = [];
  for (const row of rows) {
    const parentCode = row.config?.parent_code;
    if (parentCode && byCode.has(parentCode)) {
      byCode.get(parentCode)?.children?.push(row);
    } else {
      roots.push(row);
    }
  }
  return roots;
});

async function loadFeatures() {
  loading.value = true;
  errorMessage.value = '';
  try {
    const result = await getSystemFeaturesApi();
    features.value = (result?.items || []).map(hydrateFeature);
    await Promise.all([loadJobLogs(), loadSystemStatus()]);
  } catch (error: any) {
    errorMessage.value = error?.message || '系统功能配置加载失败';
  } finally {
    loading.value = false;
  }
}

async function loadSystemStatus() {
  try {
    systemStatus.value = await getSystemFeatureStatusApi();
  } catch {
    systemStatus.value = {};
  }
}

async function loadJobLogs() {
  logLoading.value = true;
  try {
    const [startDate, endDate] = logQuery.date_range || [];
    const result = await getSystemJobRunLogsApi({
      end_date: endDate,
      job_code: logQuery.job_code,
      limit: logQuery.limit,
      result: logQuery.result,
      start_date: startDate,
    });
    jobLogs.value = result?.items || [];
  } finally {
    logLoading.value = false;
  }
}

async function saveFeature(feature: SystemFeatureFlag, showMessage = true) {
  if (!canManageFeatures.value) {
    ElMessage.warning('当前账号没有系统功能管理权限');
    await loadFeatures();
    return;
  }
  savingCode.value = feature.code;
  try {
    normalizeBeforeSave(feature);
    const saved = await saveSystemFeatureApi(feature);
    replaceFeature(saved);
    if (showMessage) {
      ElMessage.success('系统功能配置已保存');
    }
  } catch (error: any) {
    ElMessage.error(error?.message || '系统功能配置保存失败');
    await loadFeatures();
  } finally {
    savingCode.value = '';
  }
}

async function moveMenu(row: SystemFeatureFlag, direction: 'down' | 'up') {
  const siblings = menuFeatures.value.filter((item) => item.config?.parent_code === row.config?.parent_code);
  const index = siblings.findIndex((item) => item.code === row.code);
  const targetIndex = direction === 'up' ? index - 1 : index + 1;
  if (index < 0 || targetIndex < 0 || targetIndex >= siblings.length) return;
  const target = siblings[targetIndex];
  if (!target) return;
  const currentOrder = row.sort_order || 0;
  row.sort_order = target.sort_order || 0;
  target.sort_order = currentOrder;
  await saveFeature(row, false);
  await saveFeature(target, false);
  ElMessage.success('菜单排序已保存');
}

function replaceFeature(feature: SystemFeatureFlag) {
  const hydrated = hydrateFeature(feature);
  const index = features.value.findIndex((item) => item.code === feature.code);
  if (index >= 0) {
    features.value[index] = hydrated;
  }
}

function normalizeBeforeSave(feature: SystemFeatureFlag) {
  if (feature.category === 'job') {
    const { hour, minute } = parseRunTime(feature.config?.run_time, feature.config?.hour, feature.config?.minute);
    feature.config = {
      ...(feature.config || {}),
      cron: `${minute} ${hour} * * *`,
      hour,
      minute,
      restart_required: true,
      run_time: formatRunTime(hour, minute),
    };
  }
}

function hydrateFeature(feature: SystemFeatureFlag) {
  const config = { ...(feature.config || {}) };
  if (feature.category === 'job') {
    const { hour, minute } = parseRunTime(config.run_time, config.hour, config.minute);
    config.hour = hour;
    config.minute = minute;
    config.run_time = formatRunTime(hour, minute);
  }
  return { ...feature, config };
}

function sortFeatures<T extends SystemFeatureFlag>(items: T[]) {
  return [...items].sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
}

function boundNumber(value: unknown, min: number, max: number, fallback: number) {
  const numberValue = Number(value);
  if (!Number.isFinite(numberValue)) return fallback;
  return Math.min(Math.max(Math.trunc(numberValue), min), max);
}

function parseRunTime(runTime: unknown, fallbackHour: unknown, fallbackMinute: unknown) {
  if (typeof runTime === 'string' && /^\d{2}:\d{2}$/.test(runTime)) {
    const [hourText, minuteText] = runTime.split(':');
    return {
      hour: boundNumber(hourText, 0, 23, 0),
      minute: boundNumber(minuteText, 0, 59, 0),
    };
  }
  return {
    hour: boundNumber(fallbackHour, 0, 23, 0),
    minute: boundNumber(fallbackMinute, 0, 59, 0),
  };
}

function formatRunTime(hour: number, minute: number) {
  return `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
}

function featurePath(feature: SystemFeatureFlag) {
  return feature.config?.path || '-';
}

function menuKey(feature: SystemFeatureFlag) {
  return feature.code.replace(/^menu\./, '');
}

function formatDuration(ms?: number) {
  if (ms === undefined || ms === null) return '-';
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

function formatJobDetail(log: SystemJobRunLog) {
  const detail = log.detail || {};
  if (log.job_code === 'job.employee_profile_sync') {
    const skipped = detail.skipped && typeof detail.skipped === 'object'
      ? Object.values(detail.skipped).reduce((sum: number, value: any) => sum + Number(value || 0), 0)
      : 0;
    return `新增 ${detail.created || 0}，更新 ${detail.updated || 0}，跳过 ${skipped}`;
  }
  if (log.summary) return log.summary;
  if (Object.keys(detail).length === 0) return '-';
  return JSON.stringify(detail);
}

function defaultDateRange() {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - 6);
  return [formatDate(start), formatDate(end)];
}

function formatDate(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

onMounted(loadFeatures);
</script>

<template>
  <div class="system-page">
    <div class="system-header">
      <div>
        <h2>系统功能</h2>
        <p>菜单显示、功能开关、定时任务；基础管理为扩展占位（站点与主题等由部署与产品默认控制）。</p>
      </div>
    </div>

    <el-alert
      v-if="errorMessage"
      class="section-gap"
      :title="errorMessage"
      show-icon
      type="error"
    />

    <div class="summary-grid section-gap">
      <el-card shadow="never">
        <span>服务器时间</span>
        <strong>{{ systemStatus.server_time || '-' }}</strong>
      </el-card>
      <el-card shadow="never">
        <span>时区</span>
        <strong>{{ systemStatus.timezone || '-' }}</strong>
      </el-card>
      <el-card shadow="never">
        <span>运行时配置</span>
        <strong>数据库保存</strong>
      </el-card>
    </div>

    <el-alert
      class="section-gap"
      show-icon
      type="info"
      title="此处数据库仅保存菜单、功能开关与定时任务相关项；站点标题/主题/语言/首页等由部署与前端 preferences 控制。数据库连接与密钥仍放 config/env。菜单显示不替代权限。"
    />

    <el-card shadow="never" class="main-card section-gap">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="菜单显示" name="menu">
          <div class="section-card">
            <div class="section-title">
              <div>
                <strong>导航菜单</strong>
                <p>控制导航栏入口是否显示和同级排序；隐藏菜单不影响直接访问时的权限校验。</p>
              </div>
            </div>
            <el-table
              v-loading="loading"
              :data="menuTree"
              border
              default-expand-all
              row-key="code"
              stripe
            >
              <el-table-column label="菜单" min-width="160">
                <template #default="{ row }">
                  <span>{{ row.name }}</span>
                </template>
              </el-table-column>
              <el-table-column label="配置键" min-width="200" show-overflow-tooltip>
                <template #default="{ row }">{{ menuKey(row) }}</template>
              </el-table-column>
              <el-table-column label="路径" min-width="180">
                <template #default="{ row }">{{ featurePath(row) }}</template>
              </el-table-column>
              <el-table-column prop="sort_order" label="排序值" width="90" />
              <el-table-column label="状态" width="110">
                <template #default="{ row }">
                  <el-tag :type="row.visible ? 'success' : 'info'">
                    {{ row.visible ? '显示' : '隐藏' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="显示" width="110">
                <template #default="{ row }">
                  <el-switch
                    v-model="row.visible"
                    :disabled="!canManageFeatures"
                    :loading="savingCode === row.code"
                    @change="saveFeature(row)"
                  />
                </template>
              </el-table-column>
              <el-table-column align="center" label="顺序" width="112">
                <template #default="{ row }">
                  <el-space class="sort-actions">
                    <el-button
                      class="sort-btn-square"
                      plain
                      size="small"
                      :icon="ArrowUp"
                      title="上移"
                      @click="moveMenu(row, 'up')"
                    />
                    <el-button
                      class="sort-btn-square"
                      plain
                      size="small"
                      :icon="ArrowDown"
                      title="下移"
                      @click="moveMenu(row, 'down')"
                    />
                  </el-space>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>

        <el-tab-pane label="功能开关" name="feature">
          <div class="feature-card-grid">
            <el-card v-for="item in featureFlags" :key="item.code" shadow="never" class="feature-card">
              <div class="feature-card-header">
                <div>
                  <strong>{{ item.name }}</strong>
                  <p>{{ item.description }}</p>
                </div>
                <el-tag :type="item.enabled ? 'success' : 'info'">
                  {{ item.enabled ? '已启用' : '已关闭' }}
                </el-tag>
              </div>
              <div class="feature-card-footer">
                <small>{{ item.code }}</small>
                <el-switch
                  v-model="item.enabled"
                  :disabled="!canManageFeatures"
                  :loading="savingCode === item.code"
                  @change="saveFeature(item)"
                />
              </div>
            </el-card>
          </div>
        </el-tab-pane>

        <el-tab-pane label="定时任务" name="job">
          <el-alert
            class="tab-tip"
            show-icon
            type="warning"
            title="数据库里的任务开关和执行时间只在调度器启动时生效；本地 APP_ENV=local 且 ENABLE_SCHEDULER=false 时不会启动定时任务。"
          />

          <div class="section-card">
            <div class="section-title">
              <div>
                <strong>任务配置</strong>
                <p>调整任务启停和每日执行时间，保存后重启后端生效。</p>
              </div>
            </div>
            <el-table v-loading="loading" :data="jobFeatures" border stripe>
              <el-table-column label="任务" min-width="240">
                <template #default="{ row }">
                  <div class="primary-cell">
                    <span>{{ row.name }}</span>
                    <small>{{ row.code }}</small>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="执行时间" width="160">
                <template #default="{ row }">
                  <el-time-picker
                    v-model="row.config.run_time"
                    :clearable="false"
                    :disabled="!canManageFeatures"
                    format="HH:mm"
                    placeholder="选择时间"
                    size="small"
                    style="width: 120px"
                    value-format="HH:mm"
                  />
                </template>
              </el-table-column>
              <el-table-column label="启用" width="100">
                <template #default="{ row }">
                  <el-switch v-model="row.enabled" :disabled="!canManageFeatures" />
                </template>
              </el-table-column>
              <el-table-column label="生效方式" width="110">
                <template #default>
                  <el-tag type="warning">重启生效</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="110">
                <template #default="{ row }">
                  <el-button
                    link
                    type="primary"
                    :disabled="!canManageFeatures"
                    :loading="savingCode === row.code"
                    @click="saveFeature(row)"
                  >
                    保存
                  </el-button>
                </template>
              </el-table-column>
              <el-table-column prop="description" label="任务说明" min-width="260" />
            </el-table>
          </div>

          <div class="section-card section-gap">
            <div class="section-title">
              <div>
                <strong>运行结果</strong>
                <p>按任务、结果和日期范围查询所有定时任务的通用运行记录。</p>
              </div>
            </div>
            <div class="toolbar">
              <el-select v-model="logQuery.job_code" clearable placeholder="全部任务" style="width: 220px">
                <el-option
                  v-for="job in jobFeatures"
                  :key="job.code"
                  :label="job.name"
                  :value="job.code"
                />
              </el-select>
              <el-select v-model="logQuery.result" clearable placeholder="全部结果" style="width: 120px">
                <el-option label="成功" value="success" />
                <el-option label="失败" value="failed" />
              </el-select>
              <el-date-picker
                v-model="logQuery.date_range"
                end-placeholder="结束日期"
                range-separator="至"
                start-placeholder="开始日期"
                type="daterange"
                value-format="YYYY-MM-DD"
              />
              <el-button :loading="logLoading" type="primary" @click="loadJobLogs">查询</el-button>
            </div>
            <el-table v-loading="logLoading" :data="jobLogs" border stripe>
              <el-table-column prop="job_name" label="任务" min-width="170" />
              <el-table-column prop="started_at" label="开始时间" min-width="170" />
              <el-table-column label="耗时" width="100">
                <template #default="{ row }">{{ formatDuration(row.duration_ms) }}</template>
              </el-table-column>
              <el-table-column label="结果" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.result === 'success' ? 'success' : 'danger'">
                    {{ row.result === 'success' ? '成功' : '失败' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="执行内容" min-width="260">
                <template #default="{ row }">{{ formatJobDetail(row) }}</template>
              </el-table-column>
              <el-table-column prop="error_message" label="错误" min-width="220" />
            </el-table>
          </div>
        </el-tab-pane>

        <el-tab-pane label="基础管理" name="setting">
          <div class="section-card setting-tab">
            <el-alert
              class="section-gap"
              show-icon
              type="info"
              title="站点名称、默认主题/语言/首页等不再写入 sys_feature_flag，由前端 preferences、构建配置与部署环境控制。"
            />
            <div class="settings-grid">
              <el-card shadow="never" class="setting-card">
                <template #header>系统状态</template>
                <div class="status-line">
                  <span>服务器时间</span>
                  <strong>{{ systemStatus.server_time || '-' }}</strong>
                </div>
                <div class="status-line">
                  <span>时区</span>
                  <strong>{{ systemStatus.timezone || '-' }}</strong>
                </div>
                <div class="setting-help">系统时间仅展示，不建议在页面内修改服务器时间。</div>
              </el-card>

              <el-card shadow="never" class="setting-card">
                <template #header>后续可放在此处</template>
                <ul class="future-list">
                  <li>只读健康检查、版本与依赖摘要</li>
                  <li>内部工具入口（需单独权限点）</li>
                  <li>与数据库无关的运行时开关说明或运维提示</li>
                </ul>
              </el-card>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<style scoped>
.system-page {
  padding: 20px;
}

.system-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.system-header h2 {
  margin: 0 0 6px;
  font-size: 22px;
}

.system-header p,
.section-title p,
.setting-help {
  margin: 4px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.main-card,
.section-card,
.setting-card {
  border-radius: 12px;
}

.section-gap {
  margin-top: 16px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.summary-grid :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.summary-grid span,
.status-line span {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.summary-grid strong {
  font-size: 16px;
}

.section-card {
  padding: 4px 0;
}

.section-title {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 12px;
}

.primary-cell {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.primary-cell small,
.feature-card-footer small {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.feature-card-grid,
.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.feature-card-header {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  justify-content: space-between;
}

.feature-card-header p {
  margin: 6px 0 0;
  color: var(--el-text-color-secondary);
}

.feature-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 16px;
  margin-top: 16px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.future-list {
  margin: 0;
  padding-left: 1.25em;
  line-height: 1.75;
  color: var(--el-text-color-secondary);
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
}

.sort-actions {
  justify-content: center;
}

.sort-btn-square {
  width: 28px;
  min-width: 28px;
  height: 28px;
  padding: 0;
}

.tab-tip {
  margin-bottom: 12px;
}

.status-line {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
}
</style>
