<template>
  <transition name="ops-slide">
    <div
      v-show="modelValue"
      ref="barRef"
      class="advanced-ops-bar"
      :class="{ 'is-pinned': pinned }"
      :style="pinStyle"
    >
      <div class="ops-bar-header">
        <div class="ops-title">
          <el-icon style="margin-right: 6px;"><Tools /></el-icon>
          高级操作
        </div>
        <el-button link :icon="Close" @click="$emit('update:modelValue', false)" />
      </div>
      <div class="ops-actions list-filter-controls">
        <slot />
        <slot name="actions" />
      </div>
    </div>
  </transition>
</template>

<script>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';

import { Close, Tools } from '@element-plus/icons-vue';
import { ElButton, ElIcon } from 'element-plus';

export default {
  name: 'AdvancedOpsBar',
  components: {
    ElButton,
    ElIcon,
    Tools,
  },
  props: {
    modelValue: {
      type: Boolean,
      default: false,
    },
    pinned: {
      type: Boolean,
      default: false,
    },
  },
  emits: ['update:modelValue'],
  setup(props) {
    const barRef = ref(null);
    const pinStyle = ref({});
    let observer = null;

    function place() {
      if (!props.pinned) {
        pinStyle.value = {};
        return;
      }
      const parent = barRef.value?.parentElement;
      if (!parent) return;
      const rect = parent.getBoundingClientRect();
      pinStyle.value = {
        left: `${rect.left}px`,
        width: `${rect.width}px`,
      };
    }

    onMounted(() => {
      if (!props.pinned) return;
      const parent = barRef.value?.parentElement;
      if (parent) {
        observer = new ResizeObserver(place);
        observer.observe(parent);
      }
      window.addEventListener('resize', place);
      place();
    });

    onBeforeUnmount(() => {
      observer?.disconnect();
      window.removeEventListener('resize', place);
    });

    watch(() => props.modelValue, (open) => {
      if (open) place();
    });

    return { Close, barRef, pinStyle };
  },
};
</script>

<style scoped>
.advanced-ops-bar {
  position: absolute;
  top: 0;
  right: 0;
  left: 0;
  z-index: 50;
  min-height: 140px;
  height: auto;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.98);
  border-radius: var(--list-mid-radius);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.12);
  backdrop-filter: blur(6px);
}

.ops-bar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.ops-title {
  display: flex;
  align-items: center;
  color: #303133;
  font-weight: 700;
}

.ops-actions {
  --ops-cols: 8;
  --ops-gap: 10px;
  --ops-field-width: calc((100% - (var(--ops-cols) - 1) * var(--ops-gap)) / var(--ops-cols));
  display: flex;
  flex-wrap: wrap;
  gap: var(--ops-gap);
  align-items: center;
}

.ops-actions > :not(.el-button) {
  box-sizing: border-box;
  flex: 0 0 var(--ops-field-width);
  width: var(--ops-field-width);
  min-width: 0;
}

.ops-actions > :not(.el-button) :deep(.el-select),
.ops-actions > :not(.el-button) :deep(.el-input),
.ops-actions > :not(.el-button) :deep(.el-date-editor) {
  width: 100%;
}

.ops-actions > .el-date-editor {
  --el-date-editor-width: 100%;
}

.ops-actions > .el-button {
  flex: 0 0 auto;
  width: auto;
}

.advanced-ops-bar.is-pinned {
  position: fixed;
  top: var(--vben-header-height, 90px);
  right: auto;
  z-index: 80;
}

.ops-slide-enter-active,
.ops-slide-leave-active {
  transition: transform 0.25s ease, opacity 0.25s ease;
}

.ops-slide-enter-from,
.ops-slide-leave-to {
  transform: translateY(-110%);
  opacity: 0;
}
</style>
