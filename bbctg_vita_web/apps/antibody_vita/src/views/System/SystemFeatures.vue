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
  runSystemJobApi,
  saveSystemFeatureApi,
} from '#/api';
import { notifyApiError, resolveUserMessage } from '#/api/errors';
import { skipGlobalErrorHandler } from '#/api/request';
import { useStaleTabRefresh } from '#/utils/staleTabRefresh';
import { SYSTEM_ERRORS } from './errors';

defineOptions({ name: 'SystemFeatures' });

const jobSchedules = [
  { value: 'daily', label: '每天' },
  { value: 'weekly', label: '每周' },
  { value: 'monthly', label: '每月' },
  { value: 'interval', label: '每隔' },
];
const jobWeekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
const jobMonthDays = Array.from({ length: 28 }, (_, index) => index + 1);
const defaultJobInterval = { every: 1, unit: 'hour', label: '1 小时' };
const jobIntervals = [
  defaultJobInterval,
  { every: 2, unit: 'hour', label: '2 小时' },
  { every: 3, unit: 'hour', label: '3 小时' },
  { every: 4, unit: 'hour', label: '4 小时' },
  { every: 6, unit: 'hour', label: '6 小时' },
  { every: 8, unit: 'hour', label: '8 小时' },
  { every: 12, unit: 'hour', label: '12 小时' },
  { every: 2, unit: 'day', label: '2 天' },
  { every: 3, unit: 'day', label: '3 天' },
  { every: 7, unit: 'day', label: '7 天' },
  { every: 14, unit: 'day', label: '14 天' },
];

type ConfiguredFeature = SystemFeatureFlag & { config: Record<string, any> };
type FeatureRow = ConfiguredFeature & { children?: FeatureRow[] };

const accessStore = useAccessStore();
const userStore = useUserStore();

const activeTab = ref('menu');
const loading = ref(false);
const logLoading = ref(false);
const savingCode = ref('');
const runningJobCode = ref('');
const errorMessage = ref('');
const features = ref<SystemFeatureFlag[]>([]);
const jobLogs = ref<SystemJobRunLog[]>([]);
const systemStatus = ref<{ app_env?: string; scheduler_running?: boolean; server_time?: string; timezone?: string }>({});

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
    const result = await getSystemFeaturesApi(skipGlobalErrorHandler);
    features.value = (result?.items || []).map(hydrateFeature);
    await Promise.all([loadJobLogs(), loadSystemStatus()]);
  } catch (error: unknown) {
    errorMessage.value = resolveUserMessage(error, {
      messages: SYSTEM_ERRORS.loadFeatures,
    }).message;
  } finally {
    loading.value = false;
    markTabDataFetched();
  }
}

const { markTabDataFetched } = useStaleTabRefresh(loadFeatures);

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
    const saved = await saveSystemFeatureApi(feature, skipGlobalErrorHandler);
    replaceFeature(saved);
    if (showMessage) {
      ElMessage.success('系统功能配置已保存');
    }
  } catch (error: unknown) {
    notifyApiError(error, { messages: SYSTEM_ERRORS.saveFeature });
    await loadFeatures();
  } finally {
    savingCode.value = '';
  }
}

async function saveJobFeature(feature: SystemFeatureFlag) {
  await saveFeature(feature, false);
}

async function runJobNow(feature: SystemFeatureFlag) {
  if (!canManageFeatures.value) {
    ElMessage.warning('当前账号没有系统功能管理权限');
    return;
  }
  runningJobCode.value = feature.code;
  try {
    await runSystemJobApi(feature.code, skipGlobalErrorHandler);
    ElMessage.success('任务已开始执行，请稍后在运行结果中查看');
    window.setTimeout(() => {
      loadJobLogs();
    }, 1200);
  } catch (error: unknown) {
    notifyApiError(error, { messages: { default: '任务触发失败' } });
  } finally {
    runningJobCode.value = '';
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
  if (feature.category === 'job') syncJobConfig(feature);
}

function hydrateFeature(feature: SystemFeatureFlag) {
  const copy = { ...feature, config: { ...(feature.config || {}) } };
  if (copy.category === 'job') syncJobConfig(copy);
  return copy;
}

function syncJobConfig(feature: SystemFeatureFlag) {
  const config = feature.config || {};
  const schedule = jobSchedules.some((item) => item.value === config.schedule) ? config.schedule : 'daily';
  const { hour, minute } = parseRunTime(config.run_time, config.hour, config.minute);
  const interval =
    jobIntervals.find((item) => `${item.every}-${item.unit}` === config.interval_key) ||
    jobIntervals.find((item) => item.every === Number(config.every) && item.unit === config.unit) ||
    defaultJobInterval;
  const next = {
    schedule,
    hour,
    minute,
    weekday: boundNumber(config.weekday, 0, 6, 0),
    day: boundNumber(config.day, 1, 28, 1),
    every: interval.every,
    unit: interval.unit,
    interval_key: `${interval.every}-${interval.unit}`,
    run_time: formatRunTime(hour, minute),
  };
  feature.config = next;
  const source = features.value.find((item) => item.code === feature.code);
  if (source && source !== feature) source.config = next;
}

const schedulerAlert = computed(() => {
  if (systemStatus.value.scheduler_running) {
    return '调度正在运行。保存后，下一次执行时间立即更新，不用重启后端。';
  }
  const env = systemStatus.value.app_env || 'local';
  return `当前是${env}环境，定时任务没有启动。本地和测试默认如此；这里的修改会先存进数据库，等调度进程启动后再按新时间计时。生产环境会启动调度。`;
});

function jobClockTitle(config: Record<string, any> | undefined) {
  const clock = config?.run_time || formatRunTime(config?.hour, config?.minute);
  if (config?.schedule === 'weekly') return `每${jobWeekdays[config.weekday] || '周一'} ${clock}`;
  if (config?.schedule === 'monthly') return `每月 ${config.day} 日 ${clock}`;
  if (config?.schedule === 'interval') {
    const label = jobIntervals.find((item) => item.every === config.every && item.unit === config.unit)?.label || '1 小时';
    return `每 ${label}，从 ${clock} 起`;
  }
  return `每天 ${clock}`;
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
  return log.summary?.trim() || '-';
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
          <el-alert
            class="tab-tip"
            show-icon
            type="success"
            title="功能开关保存后立即生效，无需重启。DRM 还需部署服务端与动态库；仅打开开关但环境未配齐时会自动跳过。"
          />
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
            :title="schedulerAlert"
          />

          <div class="section-card">
            <div class="section-title">
              <div>
                <strong>任务配置</strong>
                <p>每天、每周、每月按所选时刻执行。每隔则从该时刻起，按固定的几小时或几天重复。</p>
              </div>
            </div>
            <el-table v-loading="loading" class="job-table" :data="jobFeatures" border stripe>
              <el-table-column label="任务" min-width="240">
                <template #default="{ row }">
                  <div class="primary-cell">
                    <span>{{ row.name }}</span>
                    <small>{{ row.code }}</small>
                  </div>
                </template>
              </el-table-column>
              <el-table-column class-name="job-control" label="周期" width="120">
                <template #default="{ row }">
                  <el-select
                    v-model="row.config.schedule"
                    class="job-field"
                    :disabled="!canManageFeatures || savingCode === row.code"
                    size="small"
                    @change="saveJobFeature(row)"
                  >
                    <el-option v-for="item in jobSchedules" :key="item.value" :label="item.label" :value="item.value" />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column class-name="job-control" label="设定" width="120">
                <template #default="{ row }">
                  <el-select
                    v-if="row.config.schedule === 'weekly'"
                    v-model="row.config.weekday"
                    class="job-field"
                    :disabled="!canManageFeatures || savingCode === row.code"
                    size="small"
                    @change="saveJobFeature(row)"
                  >
                    <el-option v-for="(label, index) in jobWeekdays" :key="label" :label="label" :value="index" />
                  </el-select>
                  <el-select
                    v-else-if="row.config.schedule === 'monthly'"
                    v-model="row.config.day"
                    class="job-field"
                    :disabled="!canManageFeatures || savingCode === row.code"
                    size="small"
                    title="29 日至 31 日在较短的月份会跳过，所以只到 28 日"
                    @change="saveJobFeature(row)"
                  >
                    <el-option v-for="item in jobMonthDays" :key="item" :label="`${item} 日`" :value="item" />
                  </el-select>
                  <el-select
                    v-else-if="row.config.schedule === 'interval'"
                    v-model="row.config.interval_key"
                    class="job-field"
                    :disabled="!canManageFeatures || savingCode === row.code"
                    size="small"
                    @change="saveJobFeature(row)"
                  >
                    <el-option
                      v-for="item in jobIntervals"
                      :key="`${item.every}-${item.unit}`"
                      :label="item.label"
                      :value="`${item.every}-${item.unit}`"
                    />
                  </el-select>
                  <span v-else class="job-blank">—</span>
                </template>
              </el-table-column>
              <el-table-column class-name="job-control" label="时刻" width="120">
                <template #default="{ row }">
                  <el-time-picker
                    v-model="row.config.run_time"
                    class="job-field"
                    :clearable="false"
                    :disabled="!canManageFeatures || savingCode === row.code"
                    format="HH:mm"
                    placeholder="时刻"
                    size="small"
                    :title="jobClockTitle(row.config)"
                    value-format="HH:mm"
                    @change="saveJobFeature(row)"
                  />
                </template>
              </el-table-column>
              <el-table-column align="center" label="启用" width="80">
                <template #default="{ row }">
                  <el-switch
                    v-model="row.enabled"
                    :disabled="!canManageFeatures"
                    :loading="savingCode === row.code"
                    @change="saveJobFeature(row)"
                  />
                </template>
              </el-table-column>
              <el-table-column align="center" label="生效" width="100">
                <template #default>
                  <el-tag :type="systemStatus.scheduler_running ? 'success' : 'info'">
                    {{ systemStatus.scheduler_running ? '保存即生效' : '未启动' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column align="center" label="操作" width="100">
                <template #default="{ row }">
                  <el-button
                    link
                    type="primary"
                    :disabled="!canManageFeatures"
                    :loading="runningJobCode === row.code"
                    @click="runJobNow(row)"
                  >
                    立即执行
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
  font-size: var(--list-page-title-size);
  font-weight: var(--list-page-title-weight);
}

.system-header p {
  margin: 4px 0 0;
  color: var(--list-page-subtitle-color);
  font-size: var(--list-page-subtitle-size);
  font-weight: var(--list-page-subtitle-weight);
}

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

.job-table :deep(td.job-control .cell) {
  display: flex;
  align-items: center;
}

.job-field {
  width: 100%;
}

.job-table :deep(.job-field.el-date-editor) {
  --el-date-editor-width: 100%;
}

.job-blank {
  width: 100%;
  color: var(--el-text-color-placeholder);
  text-align: center;
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
