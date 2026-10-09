<template>
  <ElDialog v-model="visible" title="批量导入" width="760px" append-to-body @open="reset">
    <ElAlert
      title="表头按本页导出：名称、系列、方向、显示序列、核对序列、备注、状态。同名记录会被更新。"
      type="info"
      :closable="false"
      show-icon
    />
    <ElUpload
      class="upload"
      drag
      :auto-upload="false"
      accept=".xlsx,.xls,.csv"
      :show-file-list="false"
      :on-change="readFile"
    >
      <ElIcon class="upload-icon"><UploadFilled /></ElIcon>
      <div class="el-upload__text">拖入 Excel 文件，或<em>点击选择</em></div>
    </ElUpload>

    <template v-if="rows.length">
      <p class="summary">
        共 {{ rows.length }} 条，
        <span :class="{ error: errorCount }">
          {{ errorCount ? `${errorCount} 条有误` : '校验通过' }}
        </span>
      </p>
      <ElTable :data="rows" border size="small" max-height="280">
        <ElTableColumn prop="sourceRow" label="来源" width="132" show-overflow-tooltip />
        <ElTableColumn prop="name" label="名称" min-width="120" show-overflow-tooltip />
        <ElTableColumn prop="family" label="系列" width="148" show-overflow-tooltip />
        <ElTableColumn label="方向" width="72" align="center">
          <template #default="{ row }">{{ directionLabel(row.direction) || '—' }}</template>
        </ElTableColumn>
        <ElTableColumn prop="short_sequence" label="显示序列" min-width="112" show-overflow-tooltip />
        <ElTableColumn prop="error" label="校验" min-width="120">
          <template #default="{ row }">
            <span :class="row.error ? 'error' : 'success'">{{ row.error || '通过' }}</span>
          </template>
        </ElTableColumn>
      </ElTable>
    </template>

    <template #footer>
      <ElButton @click="visible = false">取消</ElButton>
      <ElButton
        type="primary"
        :loading="saving"
        :disabled="!rows.length || errorCount > 0"
        @click="submit"
      >
        导入
      </ElButton>
    </template>
  </ElDialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';

import { UploadFilled } from '@element-plus/icons-vue';
import {
  ElAlert,
  ElButton,
  ElDialog,
  ElIcon,
  ElMessage,
  ElTable,
  ElTableColumn,
  ElUpload,
  type UploadFile,
} from 'element-plus';

import { notifyApiError } from '#/api/errors';
import {
  batchSavePrimers,
  type PrimerSavePayload,
} from '#/api/primerCatalog';

import { checkSequence, cleanSequence, directionLabel } from './primerSeries';

type ImportRow = PrimerSavePayload & { error: string; sourceRow: string };
type Field = 'name' | 'family' | 'direction' | 'short_sequence' | 'note' | 'active';
type ColumnKey = Field | 'check';

const HEADER_MAP: Record<string, ColumnKey> = {
  名称: 'name',
  系列: 'family',
  方向: 'direction',
  显示序列: 'short_sequence',
  核对序列: 'check',
  备注: 'note',
  状态: 'active',
};
const REQUIRED_HEADERS: Field[] = ['name', 'family', 'direction', 'short_sequence'];

const props = defineProps<{ modelValue: boolean }>();
const emit = defineEmits<{
  saved: [];
  'update:modelValue': [value: boolean];
}>();

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
});
const rows = ref<ImportRow[]>([]);
const saving = ref(false);
const errorCount = computed(() => rows.value.filter((row) => row.error).length);

function reset() {
  rows.value = [];
}

function text(value: unknown) {
  return String(value ?? '').trim();
}

function sequence(value: unknown) {
  return cleanSequence(text(value));
}

function active(value: unknown) {
  return !['0', 'false', '停用', '否'].includes(text(value).toLowerCase());
}

function directionOf(value: unknown) {
  const token = text(value);
  if (token === 'F' || token === '正向') return 'F';
  if (token === 'R' || token === '反向') return 'R';
  return token.toUpperCase();
}

function validate(item: PrimerSavePayload, check = '') {
  if (!item.name) return '名称不能为空';
  if (!item.family) return '请填写系列';
  if (item.family.length > 32) return '系列不能超过 32 个字符';
  if (!item.short_sequence) return '显示序列不能为空';
  if (item.direction !== 'F' && item.direction !== 'R') return '方向只能是正向或反向';
  if (!/^[ACGTN]+$/.test(item.short_sequence)) return '序列格式不正确';
  if (check && check !== checkSequence(item.short_sequence)) return '核对序列与显示序列不一致';
  return '';
}

function blankItem(sourceRow: string): ImportRow {
  return {
    name: '',
    family: '',
    direction: null,
    short_sequence: '',
    note: null,
    active: true,
    error: '',
    sourceRow,
  };
}

function pushItem(collected: ImportRow[], names: Set<string>, item: ImportRow) {
  if (!item.error && names.has(item.name)) item.error = '名称重复';
  if (item.name) names.add(item.name);
  collected.push(item);
}

function parseFlat(sheetName: string, source: unknown[][]) {
  const content = source.filter((row) => row.some((cell) => text(cell)));
  if (!content.length) return null;
  const columns = new Map<ColumnKey, number>();
  content[0]?.forEach((cell, index) => {
    const field = HEADER_MAP[text(cell).replace(/\s+/g, '')];
    if (field) columns.set(field, index);
  });
  if (REQUIRED_HEADERS.some((field) => !columns.has(field))) return null;
  const names = new Set<string>();
  const collected: ImportRow[] = [];
  content.slice(1).forEach((row, index) => {
    const read = (field: ColumnKey) => row[columns.get(field) ?? -1];
    const item = blankItem(`${sheetName} 第 ${index + 2} 行`);
    Object.assign(item, {
      name: text(read('name')),
      family: text(read('family')),
      direction: directionOf(read('direction')) || null,
      short_sequence: sequence(read('short_sequence')),
      note: text(read('note')) || null,
      active: columns.has('active') ? active(read('active')) : true,
    });
    if (!item.name && !item.short_sequence) return;
    item.error = validate(item, columns.has('check') ? sequence(read('check')) : '');
    pushItem(collected, names, item);
  });
  return collected;
}

function parseWorkbook(book: { SheetNames: string[]; Sheets: Record<string, unknown> }, utils: {
  sheet_to_json: <T>(sheet: unknown, options: { defval: string; header: 1 }) => T;
}) {
  let matched = false;
  const parsed: ImportRow[] = [];
  book.SheetNames.forEach((name) => {
    const result = parseFlat(
      name,
      utils.sheet_to_json<unknown[]>(book.Sheets[name], { defval: '', header: 1 }),
    );
    if (!result) return;
    matched = true;
    parsed.push(...result);
  });
  if (!matched) throw new Error('第一行表头需要包含名称、系列、方向、显示序列');
  if (!parsed.length) throw new Error('文件中没有可导入的引物');
  if (parsed.length > 1000) throw new Error('单次最多导入 1000 条引物');
  rows.value = parsed;
}

async function readFile(file: UploadFile) {
  if (!file.raw) return;
  try {
    const XLSX = await import('xlsx');
    const workbook = XLSX.read(await file.raw.arrayBuffer(), { type: 'array' });
    parseWorkbook(workbook, XLSX.utils);
  } catch (error) {
    rows.value = [];
    notifyApiError(error, { messages: { default: '文件解析失败' } });
  }
}

async function submit() {
  if (!rows.value.length || errorCount.value) return;
  saving.value = true;
  try {
    const items = rows.value.map(({ error: _error, sourceRow: _row, ...item }) => item);
    const result = await batchSavePrimers(items);
    ElMessage.success(`新增 ${result.created} 条，更新 ${result.updated} 条`);
    visible.value = false;
    emit('saved');
  } catch (error) {
    notifyApiError(error, { messages: { default: '导入失败' } });
  } finally {
    saving.value = false;
  }
}
</script>

<style scoped>
.upload {
  margin-top: 14px;
}

.upload-icon {
  margin-bottom: 8px;
  color: var(--el-color-primary);
  font-size: 34px;
}

.summary {
  margin: 14px 0 8px;
  color: var(--el-text-color-regular);
  font-size: 13px;
}

.error {
  color: var(--el-color-danger);
}

.success {
  color: var(--el-color-success);
}
</style>
