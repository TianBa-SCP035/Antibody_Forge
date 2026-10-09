<template>
  <ElDialog
    v-model="visible"
    :title="form.id ? '编辑引物' : '新增引物'"
    width="680px"
    append-to-body
    @open="fill"
  >
    <ElForm label-position="top" class="primer-form">
      <div class="form-grid form-grid-pair">
        <ElFormItem label="名称" required>
          <ElInput v-model="form.name" maxlength="128" placeholder="引物名称" />
        </ElFormItem>
        <ElFormItem label="状态" class="status-item">
          <ElSwitch v-model="form.active" active-text="启用" inactive-text="停用" />
        </ElFormItem>
        <ElFormItem label="系列" required>
          <ElSelect
            v-model="form.family"
            filterable
            allow-create
            default-first-option
            placeholder="选择或输入新系列"
          >
            <ElOption v-for="name in libraryOptions" :key="name" :label="name" :value="name" />
          </ElSelect>
          <p class="field-hint">输入新系列名后回车即可新建，最多 32 个字符。</p>
        </ElFormItem>
        <ElFormItem label="方向" required>
          <ElSelect v-model="form.direction" placeholder="选择方向">
            <ElOption label="正向" value="F" />
            <ElOption label="反向" value="R" />
          </ElSelect>
        </ElFormItem>
      </div>
      <div class="form-grid">
        <ElFormItem label="显示序列" required>
          <ElInput
            v-model="form.short_sequence"
            class="sequence-input"
            maxlength="64"
            placeholder="仅 A C G T N"
          />
        </ElFormItem>
        <ElFormItem label="核对序列">
          <div class="check-value" :class="{ 'is-empty': !checked }">
            {{ checked || '由显示序列自动算出' }}
          </div>
        </ElFormItem>
      </div>
      <ElFormItem label="备注">
        <ElInput v-model="form.note" type="textarea" :rows="2" maxlength="500" show-word-limit />
      </ElFormItem>
    </ElForm>
    <template #footer>
      <ElButton @click="visible = false">取消</ElButton>
      <ElButton type="primary" :loading="saving" @click="submit">保存</ElButton>
    </template>
  </ElDialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue';

import {
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElOption,
  ElSelect,
  ElSwitch,
} from 'element-plus';

import { notifyApiError } from '#/api/errors';
import {
  type PrimerItem,
  type PrimerSavePayload,
  savePrimer,
} from '#/api/primerCatalog';

import { checkSequence, cleanSequence } from './primerSeries';

type Draft = {
  id?: number;
  name: string;
  family: string;
  direction: string;
  short_sequence: string;
  note: string;
  active: boolean;
};

const props = withDefaults(
  defineProps<{
    libraries?: string[];
    modelValue: boolean;
    primer?: null | PrimerItem;
  }>(),
  { libraries: () => [], primer: null },
);
const emit = defineEmits<{
  saved: [];
  'update:modelValue': [value: boolean];
}>();

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
});
const saving = ref(false);
const form = reactive<Draft>(blank());
const checked = computed(() => checkSequence(form.short_sequence));
const libraryOptions = computed(() => {
  const names = [...props.libraries];
  const current = form.family.trim();
  if (current && !names.includes(current)) names.push(current);
  return names;
});

function blank(): Draft {
  return {
    name: '',
    family: '',
    direction: '',
    short_sequence: '',
    note: '',
    active: true,
  };
}

function fill() {
  const row = props.primer;
  Object.assign(form, row ? {
    id: row.id,
    name: row.name,
    family: row.family,
    direction: row.direction || '',
    short_sequence: row.short_sequence,
    note: row.note || '',
    active: row.active,
  } : blank());
}

function payload(): PrimerSavePayload {
  return {
    id: form.id,
    name: form.name.trim(),
    family: form.family.trim(),
    direction: form.direction,
    short_sequence: cleanSequence(form.short_sequence),
    note: form.note.trim() || null,
    active: form.active,
  };
}

function validate(data: PrimerSavePayload) {
  if (!data.name) return '请输入名称';
  if (!data.family) return '请选择或输入系列';
  if (data.family.length > 32) return '系列不能超过 32 个字符';
  if (!data.direction) return '请选择方向';
  if (!data.short_sequence) return '请输入显示序列';
  if (!/^[ACGTN]+$/.test(data.short_sequence)) return '序列仅支持 A、C、G、T、N';
  return '';
}

async function submit() {
  const data = payload();
  const message = validate(data);
  if (message) {
    ElMessage.warning(message);
    return;
  }
  saving.value = true;
  try {
    await savePrimer(data);
    ElMessage.success('保存成功');
    visible.value = false;
    emit('saved');
  } catch (error) {
    notifyApiError(error, { messages: { default: '保存失败' } });
  } finally {
    saving.value = false;
  }
}
</script>

<style scoped>
.primer-form :deep(.el-form-item) {
  margin-bottom: 14px;
}

.primer-form :deep(.el-select) {
  width: 100%;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
}

.form-grid-pair {
  grid-template-columns: minmax(0, 1fr) 188px;
  align-items: start;
}

.status-item :deep(.el-form-item__content) {
  height: 32px;
  align-items: center;
}

.field-hint {
  margin: 4px 0 0;
  color: var(--el-text-color-placeholder);
  font-size: 12px;
  line-height: 1.4;
}

.sequence-input :deep(.el-input__inner) {
  font-family: Consolas, ui-monospace, monospace;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.check-value {
  min-height: 32px;
  padding: 5px 11px;
  font-family: Consolas, ui-monospace, monospace;
  font-size: 14px;
  line-height: 22px;
  color: var(--el-text-color-regular);
  letter-spacing: 0.06em;
  word-break: break-all;
  background: var(--el-fill-color-light);
  border-radius: 4px;
}

.check-value.is-empty {
  font-family: inherit;
  color: var(--el-text-color-placeholder);
  letter-spacing: 0;
}
</style>
