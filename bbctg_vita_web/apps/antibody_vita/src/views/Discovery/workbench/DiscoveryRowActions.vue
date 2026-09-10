<template>
  <div class="action-cell" @click.stop>
    <el-button-group>
      <el-button
        class="list-table-action-btn"
        type="primary"
        plain
        :icon="Document"
        @click="$emit('detail', row)"
      >
        详情
      </el-button>
      <el-button
        class="list-table-action-btn"
        type="success"
        plain
        :icon="CopyDocument"
        :class="{ 'no-permission-btn': !canEdit }"
        :title="!canEdit ? '您没有权限复制安排' : ''"
        @click="$emit('copy', row)"
      >
        复制
      </el-button>
      <el-button
        class="list-table-action-btn"
        type="warning"
        plain
        :icon="Delete"
        :class="{ 'no-permission-btn': !canEdit }"
        :title="!canEdit ? '您没有权限删除安排' : ''"
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
  name: 'DiscoveryRowActions',
  components: { ElButton, ElButtonGroup },
  props: {
    row: { type: Object, required: true },
    canEdit: { type: Boolean, default: false },
  },
  emits: ['detail', 'copy', 'delete'],
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
