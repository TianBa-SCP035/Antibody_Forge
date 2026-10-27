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
        :icon="User"
        :class="{ 'no-permission-btn': !canClaim }"
        :title="!canClaim ? '您没有权限认领合成结果' : '认领该批次合成结果'"
        @click="$emit('claim', row)"
      >
        认领
      </el-button>
      <el-button
        class="list-table-action-btn"
        type="warning"
        plain
        :icon="Delete"
        :class="{ 'no-permission-btn': !canDelete }"
        :title="!canDelete ? '您没有权限删除该工单' : ''"
        @click="$emit('delete', row)"
      >
        删除
      </el-button>
    </el-button-group>
  </div>
</template>

<script>
import { Delete, Document, User } from '@element-plus/icons-vue'
import { ElButton, ElButtonGroup } from 'element-plus'

export default {
  name: 'SynthesisRowActions',
  components: { ElButton, ElButtonGroup },
  props: {
    row: { type: Object, required: true },
    canClaim: { type: Boolean, default: false },
    canDelete: { type: Boolean, default: false },
  },
  emits: ['detail', 'claim', 'delete'],
  setup() {
    return { Delete, Document, User }
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
