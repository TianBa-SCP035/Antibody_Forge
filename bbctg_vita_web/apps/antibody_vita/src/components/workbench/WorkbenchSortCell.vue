<template>
  <div class="sort-cell">
    <el-input
      v-if="editing"
      ref="input"
      :model-value="modelValue"
      class="sort-order-input"
      size="small"
      type="number"
      min="1"
      @update:model-value="$emit('update:modelValue', $event)"
      @click.stop
      @mousedown.stop
      @blur="$emit('finish')"
      @keyup.enter="$emit('finish')"
    />
    <button
      v-else
      type="button"
      class="sort-order-value"
      :class="{ 'is-locked': locked }"
      @click.stop="$emit('start')"
    >
      {{ text }}
    </button>
  </div>
</template>

<script>
import { ElInput } from 'element-plus'

/** 工作台视图排序列的单元格，配合 workbenchQueueSortMixin 使用。 */
export default {
  name: 'WorkbenchSortCell',
  components: { ElInput },
  props: {
    modelValue: { type: [Number, String], default: null },
    text: { type: String, default: '' },
    editing: { type: Boolean, default: false },
    locked: { type: Boolean, default: false },
  },
  emits: ['update:modelValue', 'start', 'finish'],
  watch: {
    editing: {
      flush: 'post',
      handler(value) {
        if (value) this.focusInput()
      },
    },
  },
  mounted() {
    if (this.editing) this.focusInput()
  },
  methods: {
    focusInput() {
      this.$refs.input?.focus?.()
      this.$refs.input?.select?.()
    },
  },
}
</script>

<style scoped>
.sort-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
}
.sort-order-value {
  min-width: 22px;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--el-text-color-regular);
  font: inherit;
  line-height: 1.2;
  cursor: text;
}
.sort-order-value.is-locked {
  cursor: default;
}
.sort-order-input {
  width: 36px;
}
.sort-order-input :deep(.el-input__wrapper) {
  padding: 0 4px;
}
</style>
