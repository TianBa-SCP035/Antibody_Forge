<template>
  <el-table :data="boards" row-key="id" border stripe size="small" empty-text="没有检测板" class="sync-board-table">
    <el-table-column v-if="showSync" label="回传时间" min-width="150" align="center">
      <template #default="{ row }">{{ row.received_at || '—' }}</template>
    </el-table-column>
    <el-table-column v-if="showSync" label="trace_id" min-width="150" show-overflow-tooltip>
      <template #default="{ row }">{{ row.trace_id || '—' }}</template>
    </el-table-column>
    <el-table-column v-else label="订单号" min-width="150" show-overflow-tooltip>
      <template #default="{ row }">{{ row.order_no || '—' }}</template>
    </el-table-column>
    <el-table-column label="检测板条码" min-width="110" show-overflow-tooltip>
      <template #default="{ row }">{{ row.detect_barcode || '—' }}</template>
    </el-table-column>
    <el-table-column label="样本板条码" min-width="110" show-overflow-tooltip>
      <template #default="{ row }">{{ row.sample_barcode || '—' }}</template>
    </el-table-column>
    <el-table-column label="细胞" min-width="120" show-overflow-tooltip>
      <template #default="{ row }">{{ row.cell_name || '—' }}</template>
    </el-table-column>
    <el-table-column label="效价实验" min-width="110" show-overflow-tooltip>
      <template #default="{ row }">{{ row.experiment_id || '—' }}</template>
    </el-table-column>
    <el-table-column label="核对" width="86" align="center">
      <template #default="{ row }">
        <el-tag :type="boardVerifyTag(row.verify_status)" effect="plain">{{ boardVerifyLabel(row.verify_status) }}</el-tag>
      </template>
    </el-table-column>
    <el-table-column label="核对说明" min-width="220">
      <template #default="{ row }"><span class="message-text">{{ row.verify_message || '—' }}</span></template>
    </el-table-column>
    <el-table-column label="导入" width="96" align="center">
      <template #default="{ row }">
        <el-tag :type="boardImportTag(row.import_status)" effect="plain">{{ boardImportLabel(row.import_status) }}</el-tag>
      </template>
    </el-table-column>
    <el-table-column label="导入说明" min-width="180">
      <template #default="{ row }"><span class="message-text">{{ row.import_message || '—' }}</span></template>
    </el-table-column>
  </el-table>
</template>

<script>
import { ElTable, ElTableColumn, ElTag } from 'element-plus';

import {
  boardImportLabel,
  boardImportTag,
  boardVerifyLabel,
  boardVerifyTag,
} from '../orderSyncStatus';

export default {
  name: 'OrderSyncBoardTable',
  components: { ElTable, ElTableColumn, ElTag },
  props: {
    boards: { type: Array, default: () => [] },
    showSync: { type: Boolean, default: false },
  },
  methods: {
    boardImportLabel,
    boardImportTag,
    boardVerifyLabel,
    boardVerifyTag,
  },
};
</script>

<style scoped>
.sync-board-table {
  width: 100%;
}

.message-text {
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
