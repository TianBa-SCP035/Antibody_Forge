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
      <div class="ops-actions">
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
  height: 140px;
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

.advanced-ops-bar :deep(.el-button .el-icon + span) {
  margin-left: 4px;
}
</style>

<style>
.more-toggle-btn {
  display: inline-flex;
  flex: 0 0 26px;
  align-items: center;
  justify-content: center;
  align-self: center;
  box-sizing: border-box;
  width: 26px;
  height: 26px;
  min-width: 26px;
  min-height: 26px;
  max-width: 26px;
  max-height: 26px;
  padding: 0;
  margin: 0;
  color: #606266;
  line-height: 1;
  vertical-align: middle;
  cursor: pointer;
  background: #f5f7fa;
  border-radius: 50%;
}

.more-toggle-btn .el-icon {
  width: 15px;
  height: 15px;
  font-size: 15px;
}

.more-toggle-btn .el-icon svg {
  width: 15px;
  height: 15px;
}

.more-toggle-btn:hover {
  color: #409eff;
  background: #eef5ff;
}
</style>
