<template>
  <el-button
    class="list-filter-action-button view-toggle-button"
    :class="{ 'is-excel': modelValue === 'excel' }"
    :title="title"
    @click="$emit('toggle')"
    @contextmenu.prevent="$emit('reset-columns')"
  >
    <el-icon><ViewIcon /></el-icon>
    <span>视图</span>
  </el-button>
</template>

<script>
import { View as ViewIcon } from '@element-plus/icons-vue'
import { ElButton, ElIcon } from 'element-plus'

export default {
  name: 'WorkbenchViewToggle',
  components: { ElButton, ElIcon, ViewIcon },
  props: {
    modelValue: { type: String, default: 'workbench' },
  },
  emits: ['toggle', 'reset-columns'],
  computed: {
    title() {
      if (this.modelValue === 'excel') {
        return '当前为 Excel。Shift 拖列表头可调列顺序，右键此按钮恢复默认。点击切换到工作台。'
      }
      return '当前为工作台。点击切换到 Excel。右键此按钮可恢复默认列顺序。'
    },
  },
}
</script>

<style scoped>
.view-toggle-button.is-excel {
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary-light-5);
}
</style>
