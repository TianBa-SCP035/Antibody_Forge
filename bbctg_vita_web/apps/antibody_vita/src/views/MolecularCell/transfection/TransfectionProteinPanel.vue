<template>
  <div class="protein-panel">
    <div class="protein-head">
      <h3 class="protein-title">
        转染蛋白
        <span class="protein-count">{{ items.length }}</span>
      </h3>
      <div class="protein-tools">
        <ElButton v-if="importable && items.length" link type="danger" size="small" :loading="clearing" @click="clearAll">
          整批删除
        </ElButton>
        <ElButton
          link
          type="primary"
          size="small"
          title="按导入格式导出本单清单，改好后直接导入；清单为空时就是导入模板"
          @click="exportList"
        >
          导出
        </ElButton>
        <ElButton link type="primary" size="small" @click="openLibrary">在转染表中查看</ElButton>
      </div>
    </div>

    <ElUpload
      v-if="importable"
      v-loading="importing"
      class="protein-upload"
      drag
      :auto-upload="false"
      accept=".xlsx,.xls,.csv"
      :show-file-list="false"
      :disabled="importing"
      :on-change="readFile"
    >
      <ElIcon class="protein-upload-icon"><UploadFilled /></ElIcon>
      <div class="protein-upload-hint">抗体名称、重链名称、轻链名称（只填名称会自动查重轻链） · 整份替换 · 有问题整份不导入</div>
    </ElUpload>
    <p v-else-if="lockReason" class="protein-lock">{{ lockReason }}</p>

    <ElAlert
      v-if="problems"
      class="protein-problems"
      type="error"
      show-icon
      :title="problems"
      @close="problems = ''"
    />

    <ElTable
      v-loading="loading"
      class="protein-table"
      :data="items"
      size="small"
      max-height="320"
      empty-text="还没有导入蛋白"
    >
      <ElTableColumn type="index" label="#" width="44" align="center" />
      <ElTableColumn prop="protein_name" label="蛋白名称" min-width="120" show-overflow-tooltip />
      <ElTableColumn prop="heavy_chain" label="重链" min-width="100" show-overflow-tooltip />
      <ElTableColumn label="轻链" min-width="100" show-overflow-tooltip>
        <template #default="{ row }">{{ row.light_chain || '—' }}</template>
      </ElTableColumn>
      <ElTableColumn label="来源" width="78" align="center">
        <template #default="{ row }">{{ row.registered_here ? '本单登记' : '已有' }}</template>
      </ElTableColumn>
    </ElTable>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRouter } from 'vue-router';

import { UploadFilled } from '@element-plus/icons-vue';
import {
  ElAlert,
  ElButton,
  ElIcon,
  ElMessage,
  ElMessageBox,
  ElTable,
  ElTableColumn,
  ElUpload,
  type UploadFile,
} from 'element-plus';

import type { WorkSheet } from 'xlsx';

import { extractApiError, notifyApiError } from '#/api/errors';
import {
  clearTransfectionProteins,
  exportOrderProteins,
  fetchOrderProteins,
  importTransfectionProteins,
} from '#/api/molecularTransfection';
import { downloadBlob } from '#/utils/file-resource';

import { proteinRowsFromWorkbook } from './proteinSheet';

type OrderProtein = {
  id: number;
  protein_name: string;
  heavy_chain: string;
  light_chain: null | string;
  registered_here: boolean;
};

const props = defineProps<{
  canEdit: boolean;
  lockReason?: string;
  orderCode?: string;
  orderId: number;
}>();
const emit = defineEmits<{ changed: [order: Record<string, unknown>] }>();

const router = useRouter();
const items = ref<OrderProtein[]>([]);
const loading = ref(false);
const importing = ref(false);
const clearing = ref(false);
const problems = ref('');
const importable = computed(() => props.canEdit && !props.lockReason);
let loadSeq = 0;

async function load() {
  const seq = ++loadSeq;
  loading.value = true;
  try {
    const data = await fetchOrderProteins(props.orderId);
    if (seq === loadSeq) items.value = data?.items || [];
  } catch (error) {
    if (seq === loadSeq) {
      items.value = [];
      notifyApiError(error, { messages: { default: '加载转染蛋白失败' } });
    }
  } finally {
    if (seq === loadSeq) loading.value = false;
  }
}

watch(
  () => props.orderId,
  () => {
    problems.value = '';
    items.value = [];
    load();
  },
  { immediate: true },
);

async function readRows(file: File) {
  const XLSX = await import('xlsx');
  const workbook = XLSX.read(await file.arrayBuffer(), { type: 'array' });
  return proteinRowsFromWorkbook(workbook, (sheet: WorkSheet) => ({
    rows: sheet ? XLSX.utils.sheet_to_json(sheet, { defval: '', header: 1 }) : [],
    firstRow: sheet?.['!ref'] ? XLSX.utils.decode_range(sheet['!ref']).s.r + 1 : 1,
  }));
}

async function readFile(file: UploadFile) {
  if (!file.raw || importing.value) return;
  const orderId = props.orderId;
  problems.value = '';
  let rows;
  try {
    rows = await readRows(file.raw);
  } catch (error) {
    ElMessage.warning(error instanceof Error && error.message ? error.message : '文件解析失败');
    return;
  }
  if (items.value.length) {
    try {
      await ElMessageBox.confirm(
        `用文件里的 ${rows.length} 个蛋白替换本单当前的 ${items.value.length} 个？本单登记、且别的工单没用到的蛋白，不在文件里时会从转染表删除。`,
        '替换蛋白清单',
        { type: 'warning', confirmButtonText: '替换' },
      );
    } catch {
      return;
    }
  }
  importing.value = true;
  try {
    const result = await importTransfectionProteins(orderId, rows);
    const looked = [
      result.from_table ? `转染表补全 ${result.from_table} 个` : '',
      result.from_api ? `基因名接口补全 ${result.from_api} 个` : '',
    ].filter(Boolean);
    ElMessage.success(
      `已导入 ${result.total} 个蛋白：新登记 ${result.created} 个，改重轻链 ${result.updated} 个，从转染表删除 ${result.removed} 个${looked.length ? `；只填名称的行${looked.join('、')}` : ''}`,
    );
    emit('changed', result.order);
    if (orderId === props.orderId) await load();
  } catch (error) {
    const { backendMessage, httpStatus } = extractApiError(error);
    if (httpStatus === 422 && backendMessage) problems.value = backendMessage;
    else notifyApiError(error, { messages: { default: '导入转染蛋白失败' } });
  } finally {
    importing.value = false;
  }
}

async function clearAll() {
  const orderId = props.orderId;
  if (clearing.value) return;
  try {
    await ElMessageBox.confirm(
      `删除本单全部 ${items.value.length} 个蛋白？本单登记、且别的工单没用到的，会一并从转染表删除。`,
      '整批删除',
      { type: 'warning', confirmButtonText: '删除' },
    );
  } catch {
    return;
  }
  clearing.value = true;
  try {
    const result = await clearTransfectionProteins(orderId);
    ElMessage.success(`已删除本单 ${result.total} 个蛋白，其中 ${result.removed} 个从转染表删除`);
    emit('changed', result.order);
    if (orderId === props.orderId) await load();
  } catch (error) {
    notifyApiError(error, { messages: { default: '删除蛋白失败' } });
  } finally {
    clearing.value = false;
  }
}

async function exportList() {
  try {
    downloadBlob(await exportOrderProteins(props.orderId), `转染蛋白_${props.orderCode || props.orderId}.xlsx`);
  } catch (error) {
    notifyApiError(error, { messages: { default: '导出失败' } });
  }
}

function openLibrary() {
  router.push({ name: 'TransfectionProteins', query: props.orderCode ? { order_code: props.orderCode } : {} });
}
</script>

<style scoped>
.protein-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.protein-title {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 0;
  color: var(--el-text-color-primary);
  font-size: 13px;
  font-weight: 650;
  letter-spacing: 0.02em;
}

.protein-title::before {
  flex-shrink: 0;
  width: 3px;
  height: 13px;
  background: var(--el-color-primary);
  border-radius: 2px;
  content: '';
}

.protein-count {
  color: var(--el-text-color-secondary);
  font-weight: 500;
}

.protein-tools {
  display: flex;
  flex-shrink: 0;
  gap: 4px;
}

.protein-upload {
  width: 100%;
  margin-bottom: 8px;
}

.protein-upload :deep(.el-upload),
.protein-upload :deep(.el-upload-dragger) {
  width: 100%;
}

.protein-upload :deep(.el-upload-dragger) {
  padding: 10px 12px;
  background: var(--el-fill-color-blank);
  border-radius: 6px;
}

.protein-upload-icon {
  color: var(--el-text-color-placeholder);
  font-size: 24px;
}

.protein-upload-hint {
  margin-top: 2px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.4;
}

.protein-lock {
  margin: 0 0 8px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.4;
}

.protein-problems {
  margin-bottom: 8px;
}

.protein-problems :deep(.el-alert__title) {
  white-space: pre-line;
  line-height: 1.55;
}

.protein-table {
  width: 100%;
}

.protein-table :deep(.el-table__header th) {
  background: var(--el-fill-color-lighter);
  color: var(--el-text-color-secondary);
  font-weight: 600;
}

.protein-table :deep(.el-table__cell) {
  padding: 6px 0;
}
</style>
