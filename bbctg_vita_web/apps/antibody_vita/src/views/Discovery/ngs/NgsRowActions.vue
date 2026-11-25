<template>
  <div class="action-cell" @click.stop>
    <el-button-group>
      <el-button
        class="list-table-action-btn"
        type="success"
        plain
        :icon="CopyDocument"
        :class="{ 'no-permission-btn': !canEdit }"
        :title="handoffTitle"
        @click="$emit('handoff', row)"
      >
        {{ row.synthesis_order_id ? '已送合成' : '送合成' }}
      </el-button>
      <el-button
        class="list-table-action-btn"
        type="warning"
        plain
        :icon="Delete"
        :class="{ 'no-permission-btn': !canEdit }"
        :title="!canEdit ? '您没有权限删除测序单' : ''"
        @click="$emit('delete', row)"
      >
        删除
      </el-button>
    </el-button-group>
  </div>
</template>

<script>
import { CopyDocument, Delete } from '@element-plus/icons-vue'
import { ElButton, ElButtonGroup } from 'element-plus'

export default {
  name: 'NgsRowActions',
  components: { ElButton, ElButtonGroup },
  props: {
    row: { type: Object, required: true },
    canEdit: { type: Boolean, default: false },
  },
  emits: ['delete', 'handoff'],
  setup() {
    return { CopyDocument, Delete }
  },
  computed: {
    handoffTitle() {
      if (!this.canEdit) return '您没有权限送合成'
      if (this.row.synthesis_order_id) return `已交接到合成与验证 ${this.row.synthesis_order_id}`
      return '按送合成转码新建一条合成与验证单'
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
