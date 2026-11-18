<template>
  <div class="action-cell" @click.stop>
    <el-button-group>
      <el-button
        class="list-table-action-btn"
        type="primary"
        plain
        :icon="Document"
        title="在转染表中查看本单蛋白"
        @click="$emit('proteins', row)"
      >
        蛋白
      </el-button>
      <el-button
        class="list-table-action-btn"
        type="success"
        plain
        :icon="CopyDocument"
        :class="{ 'no-permission-btn': !canEdit }"
        :title="handoffTitle"
        @click="$emit('handoff', row)"
      >
        {{ row.synthesis_order_id ? '已交接' : '交接' }}
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
  name: 'TransfectionRowActions',
  components: { ElButton, ElButtonGroup },
  props: {
    row: { type: Object, required: true },
    canEdit: { type: Boolean, default: false },
  },
  emits: ['delete', 'handoff', 'proteins'],
  setup() {
    return { CopyDocument, Delete, Document }
  },
  computed: {
    handoffTitle() {
      if (this.row.synthesis_order_id) return `已交接到合成与验证 ${this.row.synthesis_order_id}`
      return this.canEdit ? '交接到合成与验证' : '您没有权限交接工单'
    },
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
