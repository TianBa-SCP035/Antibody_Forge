<template>
  <el-select
    :model-value="modelValue"
    filterable
    :filter-method="handleFilter"
    :loading="loading"
    :placeholder="placeholder"
    :disabled="disabled"
    :clearable="clearable"
    style="width: 100%;"
    @update:model-value="$emit('update:modelValue', normalizeValue($event))"
    @change="$emit('change', normalizeValue($event))"
    @visible-change="handleVisibleChange"
  >
    <el-option
      v-for="item in displayedOptions"
      :key="item"
      :label="item"
      :value="item"
    />
  </el-select>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { ElOption, ElSelect } from 'element-plus';

import {
  getCachedSerumUserOptions,
  loadSerumUserOptions,
  uniqueNames,
} from '#/utils/serumUserOptions';

const props = withDefaults(
  defineProps<{
    modelValue?: string;
    options?: string[];
    placeholder?: string;
    disabled?: boolean;
    clearable?: boolean;
  }>(),
  {
    modelValue: '',
    options: () => [],
    placeholder: '选择人员',
    disabled: false,
    clearable: false,
  },
);

defineEmits<{
  change: [value: string];
  'update:modelValue': [value: string];
}>();

const query = ref('');
const allUserNames = ref<string[]>(getCachedSerumUserOptions());
const loading = ref(false);

function normalizeValue(value: unknown) {
  return value == null ? '' : String(value)
}

const displayedOptions = computed(() => {
  const keyword = query.value.trim().toLocaleLowerCase();
  if (!keyword) return uniqueNames([props.modelValue, ...props.options]);
  return uniqueNames([
    props.modelValue,
    ...allUserNames.value.filter((item) => item.toLocaleLowerCase().includes(keyword)),
  ]);
});

async function handleFilter(value: string) {
  query.value = value;
  if (!value.trim() || allUserNames.value.length) return;
  loading.value = true;
  try {
    allUserNames.value = await loadSerumUserOptions();
  } catch {
    allUserNames.value = [];
  } finally {
    loading.value = false;
  }
}

function handleVisibleChange(visible: boolean) {
  if (!visible) query.value = '';
}
</script>
