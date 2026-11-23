<script setup>
import { computed, ref } from 'vue'

import { ElInput } from 'element-plus'

/**
 * 一行一项的多行文本框（板号、抗原等）：不自动折行，框高等于行数、每一项都看得到；
 * 不显示滚动条，长行用光标、拖选、Shift+滚轮或触控板左右滚动，失焦回到行首。
 * 用法同 ElInput（v-model、disabled、maxlength、placeholder、focus / blur / input 等原样透传）。
 * ElInput 的 autosize 用隐藏的折行文本框量高，不折行时会多算行，所以这里按行数直接给 rows。
 */
defineOptions({ name: 'WorkbenchLineInput', inheritAttrs: false })

const props = defineProps({
  modelValue: { type: null, default: '' },
})

const emit = defineEmits(['update:modelValue', 'blur'])

const inputRef = ref()
const rows = computed(() => String(props.modelValue ?? '').split('\n').length)

function onBlur(event) {
  const textarea = inputRef.value?.textarea
  if (textarea) textarea.scrollLeft = 0
  emit('blur', event)
}
</script>

<template>
  <ElInput
    ref="inputRef"
    v-bind="$attrs"
    class="workbench-line-input"
    :model-value="modelValue"
    type="textarea"
    resize="none"
    :rows="rows"
    @update:model-value="emit('update:modelValue', $event)"
    @blur="onBlur"
  />
</template>

<style scoped>
.workbench-line-input :deep(.el-textarea__inner) {
  white-space: pre;
  scrollbar-width: none;
}
</style>
