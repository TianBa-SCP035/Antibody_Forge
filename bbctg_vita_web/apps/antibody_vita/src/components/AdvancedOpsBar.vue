<template>
  <transition name="ops-slide">
    <div v-show="modelValue" class="advanced-ops-bar">
      <div class="ops-bar-header">
        <div class="ops-title">
          <el-icon style="margin-right: 6px;"><Tools /></el-icon>
          高级操作
        </div>
        <el-button link :icon="Close" @click="$emit('update:modelValue', false)" />
      </div>
      <div class="ops-actions list-filter-controls">
        <slot />
      </div>
    </div>
  </transition>
</template>

<script>
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
  },
  emits: ['update:modelValue'],
  setup() {
    return { Close };
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
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
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
