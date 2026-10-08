<template>
  <div class="action-cell" @click.stop>
    <el-button-group>
      <el-button
        class="list-table-action-btn"
        type="primary"
        plain
        :icon="Document"
        :class="{ 'no-permission-btn': !canView }"
        :title="!canView ? '您没有权限查看文库质检' : ''"
        @click="$emit('qc', row)"
      >
        质检
      </el-button>
      <el-button
        class="list-table-action-btn"
        type="success"
        plain
        :icon="CopyDocument"
        :class="{ 'no-permission-btn': !canHandoff }"
        :title="!canHandoff ? '您没有权限交接工单' : '交接至下游模块'"
        @click="$emit('handoff', row)"
      >
        交接
      </el-button>
      <el-button
        class="list-table-action-btn"
        type="warning"
        plain
        :icon="Delete"
        :class="{ 'no-permission-btn': !canEdit }"
        :title="!canEdit ? '您没有权限删除工单' : ''"
        @click="$emit('delete', row)"
      >
        删除
      </el-button>
    </el-button-group>
  </div>
</template>

<script>
import { CopyDocument, Delete, Document } from '@element-plus/icons-vue'
import { ElButton, ElButtonGroup } from 'element-plus'

export default {
  name: 'LibraryRowActions',
  components: { ElButton, ElButtonGroup },
  props: {
    row: { type: Object, required: true },
    canEdit: { type: Boolean, default: false },
    canHandoff: { type: Boolean, default: false },
    canView: { type: Boolean, default: false },
  },
  emits: ['delete', 'handoff', 'qc'],
  setup() {
    return { CopyDocument, Delete, Document }
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
