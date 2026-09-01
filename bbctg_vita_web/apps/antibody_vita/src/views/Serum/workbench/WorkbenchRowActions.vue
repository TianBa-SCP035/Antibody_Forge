<template>
  <div class="action-cell" @click.stop>
    <el-button-group>
      <el-button
        class="list-table-action-btn"
        type="primary"
        plain
        :icon="row.aligned_locked ? ViewIcon : Document"
        @click="$emit('scheme', row)"
      >
        {{ row.aligned_locked ? '详情' : '方案' }}
      </el-button>
      <el-button
        class="list-table-action-btn"
        type="success"
        plain
        :icon="CopyDocument"
        :class="{ 'no-permission-btn': !canCopy }"
        :title="!canCopy ? '您没有权限复制工作台记录' : ''"
        @click="$emit('copy', row)"
      >
        复制
      </el-button>
      <el-button
        class="list-table-action-btn"
        type="warning"
        plain
        :icon="row.aligned_locked ? Bottom : Delete"
        :class="{ 'no-permission-btn': !(row.aligned_locked ? canUnlist : canDelete) }"
        :title="!(row.aligned_locked ? canUnlist : canDelete) ? '您没有权限执行此操作' : ''"
        @click="$emit(row.aligned_locked ? 'unlist' : 'delete', row)"
      >
        {{ row.aligned_locked ? '下架' : '删除' }}
      </el-button>
    </el-button-group>
  </div>
</template>

<script>
import {
  Bottom,
  CopyDocument,
  Delete,
  Document,
  View as ViewIcon,
} from '@element-plus/icons-vue'
import { ElButton, ElButtonGroup } from 'element-plus'

export default {
  name: 'WorkbenchRowActions',
  components: { ElButton, ElButtonGroup },
  props: {
    row: { type: Object, required: true },
    canCopy: { type: Boolean, default: false },
    canDelete: { type: Boolean, default: false },
    canUnlist: { type: Boolean, default: false },
  },
  emits: ['scheme', 'copy', 'delete', 'unlist'],
  setup() {
    return { Bottom, CopyDocument, Delete, Document, ViewIcon }
  },
}
</script>

<style scoped>
.action-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
}
</style>
