<template>
  <div class="action-cell" @click.stop>
    <el-button-group>
      <el-button
        class="list-table-action-btn"
        type="primary"
        plain
        :icon="Document"
        :disabled="disabled"
        :title="disabled ? disabledTitle : ''"
        @click="$emit('detail', row)"
      >
        详情
      </el-button>
      <el-button
        class="list-table-action-btn"
        type="success"
        plain
        :icon="User"
        :disabled="disabled"
        :class="{ 'no-permission-btn': !disabled && !canClaim }"
        :title="disabled ? disabledTitle : claimTitle || (!canClaim ? '您没有权限认领合成结果' : '认领该批次合成结果')"
        @click="$emit('claim', row)"
      >
        认领
      </el-button>
      <el-button
        class="list-table-action-btn"
        type="warning"
        plain
        :icon="cancelMode ? CircleClose : Delete"
        :disabled="disabled"
        :class="{ 'no-permission-btn': !disabled && !canDelete }"
        :title="disabled ? disabledTitle : deleteTitle || (!canDelete ? '您没有权限删除该工单' : '')"
        @click="$emit('delete', row)"
      >
        {{ cancelMode ? '取消' : '删除' }}
      </el-button>
    </el-button-group>
  </div>
</template>

<script>
import { CircleClose, Delete, Document, User } from '@element-plus/icons-vue'
import { ElButton, ElButtonGroup } from 'element-plus'

export default {
  name: 'SynthesisRowActions',
  components: { ElButton, ElButtonGroup },
  props: {
    row: { type: Object, required: true },
    canClaim: { type: Boolean, default: false },
    claimTitle: { type: String, default: '' },
    canDelete: { type: Boolean, default: false },
    deleteTitle: { type: String, default: '' },
    cancelMode: { type: Boolean, default: false },
    disabled: { type: Boolean, default: false },
    disabledTitle: { type: String, default: '' },
  },
  emits: ['detail', 'claim', 'delete'],
  setup() {
    return { CircleClose, Delete, Document, User }
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
