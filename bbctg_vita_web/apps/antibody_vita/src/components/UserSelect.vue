<template>
  <component
    :is="multiGesture ? ListFilterSelect : ElSelect"
    :model-value="modelValue"
    filterable
    remote
    :remote-method="handleFilter"
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

import { createLatestRequest } from '#/utils/latestRequest';
import { searchUserNames, uniqueNames } from '#/utils/userOptions';

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
const remoteNames = ref<string[]>([]);
const loading = ref(false);
const remoteRequest = createLatestRequest();

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

/** 没输关键字只列页面给的常用人员；输了再并上服务端按关键字查到的在职人员。 */
const displayedOptions = computed(() => {
  const keyword = query.value.trim().toLocaleLowerCase();
  if (!keyword) return uniqueNames([...currentNames(), ...props.options]);
  return uniqueNames([
    ...currentNames(),
    ...props.options.filter((item) => item.toLocaleLowerCase().includes(keyword)),
    ...remoteNames.value,
  ]);
});

async function handleFilter(value: string) {
  query.value = value;
  const isLatest = remoteRequest.begin();
  if (!value.trim()) {
    remoteNames.value = [];
    loading.value = false;
    return;
  }
  loading.value = true;
  try {
    const items = await searchUserNames(value, 30);
    if (isLatest()) remoteNames.value = items;
  } catch {
    if (isLatest()) remoteNames.value = [];
  } finally {
    if (isLatest()) loading.value = false;
  }
}

function handleVisibleChange(visible: boolean) {
  if (!visible) handleFilter('');
}
</script>
