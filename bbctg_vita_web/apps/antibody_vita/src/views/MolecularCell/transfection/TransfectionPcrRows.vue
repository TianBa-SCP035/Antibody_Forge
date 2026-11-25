<template>
  <div class="pcr-panel">
    <div class="pcr-head">
      <h3 class="pcr-title">
        板号与重轻链
        <span class="pcr-count">{{ draft.length }}</span>
      </h3>
      <ElButton v-if="canEdit" link type="primary" size="small" :icon="Plus" @click="addRow">添加行</ElButton>
    </div>
    <ElTable class="pcr-table" :data="draft" size="small" max-height="360" empty-text="点「添加行」填写板号、重链、轻链和数量">
      <ElTableColumn type="index" label="#" width="40" align="center" />
      <ElTableColumn label="板号" min-width="100">
        <template #default="{ row }">
          <ElInput v-model="row.plate_no" size="small" :disabled="!canEdit" maxlength="64" @blur="commit" />
        </template>
      </ElTableColumn>
      <ElTableColumn label="重链" min-width="110">
        <template #default="{ row }">
          <ElInput v-model="row.heavy_chain" size="small" :disabled="!canEdit" maxlength="128" @blur="commit" />
        </template>
      </ElTableColumn>
      <ElTableColumn label="轻链" min-width="110">
        <template #default="{ row }">
          <ElInput v-model="row.light_chain" size="small" :disabled="!canEdit" maxlength="128" @blur="commit" />
        </template>
      </ElTableColumn>
      <ElTableColumn label="数量" width="74">
        <template #default="{ row }">
          <ElInput v-model="row.quantity" size="small" :disabled="!canEdit" @blur="commit" />
        </template>
      </ElTableColumn>
      <ElTableColumn v-if="canEdit" width="36" align="center">
        <template #default="{ $index }">
          <ElButton link type="danger" size="small" :icon="Delete" title="删除这一行" @click="removeRow($index)" />
        </template>
      </ElTableColumn>
    </ElTable>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';

import { Delete, Plus } from '@element-plus/icons-vue';
import { ElButton, ElInput, ElMessage, ElTable, ElTableColumn } from 'element-plus';

type PcrRow = {
  heavy_chain: string;
  light_chain: string;
  plate_no: string;
  quantity: null | number | string;
};

const props = defineProps<{
  canEdit: boolean;
  orderId: number;
  rows?: PcrRow[];
}>();
const emit = defineEmits<{ change: [rows: PcrRow[]] }>();

const draft = ref<PcrRow[]>([]);

function blankRow(): PcrRow {
  return { plate_no: '', heavy_chain: '', light_chain: '', quantity: '' };
}

function isBlank(row: PcrRow) {
  return !row.plate_no?.trim() && !row.heavy_chain?.trim() && !row.light_chain?.trim() && !String(row.quantity ?? '').trim();
}

// 只在切换工单时从行数据重建草稿：保存回包晚到时不能盖掉正在填的下一行。
watch(
  () => props.orderId,
  () => {
    draft.value = (props.rows || []).map((row) => ({ ...blankRow(), ...row, quantity: row.quantity ?? '' }));
  },
  { immediate: true },
);

function filledRows() {
  return draft.value
    .filter((row) => !isBlank(row))
    .map((row) => ({
      plate_no: row.plate_no.trim(),
      heavy_chain: row.heavy_chain.trim(),
      light_chain: row.light_chain.trim(),
      quantity: String(row.quantity ?? '').trim() === '' ? null : String(row.quantity).trim(),
    }));
}

function commit() {
  if (!props.canEdit) return;
  const bad = draft.value.findIndex((row) => {
    const text = String(row.quantity ?? '').trim();
    return text !== '' && !/^\d+$/.test(text);
  });
  if (bad >= 0) {
    ElMessage.warning(`第 ${bad + 1} 行数量必须是非负整数`);
    return;
  }
  emit('change', filledRows());
}

function addRow() {
  draft.value.push(blankRow());
}

function removeRow(index: number) {
  const removed = draft.value.splice(index, 1)[0];
  if (removed && !isBlank(removed)) commit();
}
</script>

<style scoped>
.pcr-panel {
  margin-bottom: 16px;
}

.pcr-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.pcr-title {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 0;
  color: var(--el-text-color-primary);
  font-size: 13px;
  font-weight: 650;
  letter-spacing: 0.02em;
}

.pcr-title::before {
  flex-shrink: 0;
  width: 3px;
  height: 13px;
  background: var(--el-color-primary);
  border-radius: 2px;
  content: '';
}

.pcr-count {
  color: var(--el-text-color-secondary);
  font-weight: 500;
}

.pcr-table {
  width: 100%;
}

.pcr-table :deep(.el-table__header th) {
  background: var(--el-fill-color-lighter);
  color: var(--el-text-color-secondary);
  font-weight: 600;
}

.pcr-table :deep(.el-table__cell) {
  padding: 4px 0;
}
</style>
