<template>
  <WorkbenchInlineSelect
    v-if="editable"
    :model-value="value"
    :options="options"
    class="inline-select priority-select workbench-priority-select"
    :class="`status-tone-${tone}`"
    @change="(next) => emit('change', next)"
  />
  <ElTag
    v-else
    class="list-status-tag workbench-priority-tag"
    :class="{ 'status-tone-king': tone === 'king' }"
    :type="tone === 'king' ? 'info' : tone"
    effect="plain"
    @click="onLockedClick"
  >
    {{ value }}
  </ElTag>
</template>

<script setup>
import { ElMessage, ElTag } from 'element-plus'
import { computed } from 'vue'

import { getTiterPriorityTone } from '#/utils/serumProjectStatus'

import { WorkbenchInlineSelect } from './WorkbenchDataTable.vue'

/**
 * 工作台列表的优先级列：能改时是按档位上色的下拉，改完 emit change(新值)，由页面写回行并保存；
 * 不能改时是标签，给了 lockReason 就点击提示原因（不再冒泡打开抽屉）。
 */
const props = defineProps({
  value: { type: String, default: '' },
  options: { type: Array, default: () => [] },
  editable: { type: Boolean, default: false },
  lockReason: { type: String, default: '' },
})
const emit = defineEmits(['change'])

const tone = computed(() => getTiterPriorityTone(props.value))

function onLockedClick(event) {
  if (!props.lockReason) return
  event.stopPropagation()
  ElMessage.info({ message: props.lockReason, grouping: true })
}
</script>

<style>
.el-select.workbench-priority-select.status-tone-info .el-select__wrapper {
  background-color: var(--el-color-info-light-9);
}
.el-select.workbench-priority-select.status-tone-info .el-select__selected-item {
  color: var(--el-color-info);
}
.el-select.workbench-priority-select.status-tone-warning .el-select__wrapper {
  background-color: var(--el-color-warning-light-9);
}
.el-select.workbench-priority-select.status-tone-warning .el-select__selected-item {
  color: var(--el-color-warning);
}
.el-select.workbench-priority-select.status-tone-danger .el-select__wrapper {
  background-color: var(--el-color-danger-light-9);
}
.el-select.workbench-priority-select.status-tone-danger .el-select__selected-item {
  color: var(--el-color-danger);
}
.el-select.workbench-priority-select.status-tone-king .el-select__wrapper {
  background-color: var(--vita-king-bg);
}
.el-select.workbench-priority-select.status-tone-king .el-select__selected-item {
  color: var(--vita-king-text);
}
.el-tag.workbench-priority-tag.status-tone-king {
  color: var(--vita-king-text);
  background: var(--vita-king-bg);
  border-color: var(--vita-king-border);
}
</style>
