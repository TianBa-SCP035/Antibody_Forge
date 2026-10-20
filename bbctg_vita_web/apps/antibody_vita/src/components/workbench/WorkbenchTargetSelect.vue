<template>
  <el-select
    ref="selectRef"
    :model-value="modelValue"
    filterable
    multiple
    remote
    remote-show-suffix
    class="target-name-select"
    title="左键单选，右键追加"
    :remote-method="search"
    :loading="loading"
    :placeholder="placeholder"
    :disabled="disabled"
    style="width: 100%;"
    @focus="search('')"
    @update:model-value="onCodesChange"
    @visible-change="listen"
  >
    <template #tag>
      <span class="target-selected-text">{{ displayName }}</span>
    </template>
    <el-option
      v-for="item in options"
      :key="item.snum"
      :label="`${item.name}（${item.snum}）`"
      :value="item.snum"
    >
      <span>{{ item.name }}</span>
      <span class="target-option-code">{{ item.snum }}</span>
    </el-option>
  </el-select>
</template>

<script setup>
import { nextTick, onBeforeUnmount, ref } from 'vue'
import { ElOption, ElSelect } from 'element-plus'

import { searchWorkbenchTargets, targetNameFromCodes, uniqueTargetCodes } from './targetOptions'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  displayName: { type: String, default: '' },
  placeholder: { type: String, default: '搜索靶点' },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'change'])

const selectRef = ref(null)
const options = ref([])
const loading = ref(false)
let requestToken = 0
let menu = null

async function search(keyword) {
  const token = ++requestToken
  loading.value = true
  try {
    const items = await searchWorkbenchTargets(keyword, props.modelValue)
    if (token !== requestToken) return
    options.value = items
  } catch {
    if (token === requestToken) options.value = options.value || []
  } finally {
    if (token === requestToken) loading.value = false
  }
}

function onCodesChange(value) {
  const codes = uniqueTargetCodes(value)
  emit('update:modelValue', codes)
  emit('change', { codes, name: targetNameFromCodes(codes, options.value), items: options.value })
}

function onMenuClick(event) {
  const item = event.target instanceof Element ? event.target.closest('.el-select-dropdown__item') : null
  const option = item && selectRef.value?.optionsArray?.find((entry) => entry?.$el === item)
  if (!option || item.classList.contains('is-disabled')) return
  event.preventDefault()
  event.stopPropagation()
  if (event.type !== 'contextmenu') {
    onCodesChange([option.value])
    selectRef.value.expanded = false
    return
  }
  const next = uniqueTargetCodes(props.modelValue)
  const index = next.indexOf(option.value)
  if (index >= 0) next.splice(index, 1)
  else next.push(option.value)
  onCodesChange(next)
}

function listen(open) {
  if (menu) {
    menu.removeEventListener('click', onMenuClick, true)
    menu.removeEventListener('contextmenu', onMenuClick, true)
    menu = null
  }
  if (!open) return
  nextTick(() => {
    const root = selectRef.value?.tooltipRef?.popperRef?.contentRef
    if (!(root instanceof HTMLElement)) return
    menu = root
    menu.addEventListener('click', onMenuClick, true)
    menu.addEventListener('contextmenu', onMenuClick, true)
  })
}

onBeforeUnmount(() => listen(false))
</script>

<style scoped>
.target-option-code {
  float: right;
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
}
.target-selected-text {
  display: block;
  box-sizing: border-box;
  flex: 0 1 auto;
  max-width: calc(100% - 24px);
  min-width: 0;
  padding: 0 6px;
  overflow: hidden;
  color: var(--el-text-color-regular);
  font: inherit;
  line-height: normal;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.target-name-select :deep(.el-select__selection) {
  flex-wrap: nowrap;
  overflow: hidden;
}
.target-name-select :deep(.el-select__input-wrapper) {
  flex: 1 1 24px;
  min-width: 24px;
}
</style>
