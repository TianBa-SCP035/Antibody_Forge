<template>
  <component
    :is="multiGesture ? ListFilterSelect : ElSelect"
    :model-value="modelValue"
    filterable
    :filter-method="handleFilter"
    :loading="loading"
    :placeholder="placeholder"
    :disabled="disabled"
    :clearable="clearable"
    style="width: 100%;"
    @update:model-value="emitValue"
    @change="emitValue($event, true)"
    @visible-change="handleVisibleChange"
  >
    <el-option
      v-for="item in displayedOptions"
      :key="item"
      :label="item"
      :value="item"
    />
  </component>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { ElOption, ElSelect } from 'element-plus';

import ListFilterSelect from '#/components/ListFilterSelect.vue';

import {
  getCachedSerumUserOptions,
  loadSerumUserOptions,
  uniqueNames,
} from '#/utils/serumUserOptions';

const props = withDefaults(
  defineProps<{
    modelValue?: string | string[];
    options?: string[];
    placeholder?: string;
    disabled?: boolean;
    clearable?: boolean;
    multiGesture?: boolean;
  }>(),
  {
    modelValue: '',
    options: () => [],
    placeholder: '选择人员',
    disabled: false,
    clearable: false,
    multiGesture: false,
  },
);

const emit = defineEmits<{
  change: [value: string | string[]];
  'update:modelValue': [value: string | string[]];
}>();

const query = ref('');
const allUserNames = ref<string[]>(getCachedSerumUserOptions());
const loading = ref(false);

function currentNames() {
  if (Array.isArray(props.modelValue)) {
    return props.modelValue.map((item) => String(item || '').trim()).filter(Boolean);
  }
  const text = String(props.modelValue || '').trim();
  return text ? [text] : [];
}

function emitValue(value: unknown, notify = false) {
  const next = Array.isArray(value)
    ? value.map((item) => String(item || '').trim()).filter(Boolean)
    : value == null ? '' : String(value);
  const stored = Array.isArray(next) && next.length <= 1 ? (next[0] || '') : next;
  emit('update:modelValue', stored);
  if (notify) emit('change', stored);
}

const displayedOptions = computed(() => {
  const keyword = query.value.trim().toLocaleLowerCase();
  const selected = currentNames();
  if (!keyword) return uniqueNames([...selected, ...props.options]);
  return uniqueNames([
    ...selected,
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
