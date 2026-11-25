<template>
  <el-dialog
    :model-value="modelValue"
    title="冻存细胞出库审核"
    width="1080px"
    append-to-body
    destroy-on-close
    @update:model-value="$emit('update:modelValue', $event)"
    @open="load"
  >
    <div class="review-toolbar">
      <el-radio-group v-model="status" size="small" @change="load">
        <el-radio-button v-for="item in statusTabs" :key="item.value" :value="item.value">{{ item.label }}</el-radio-button>
      </el-radio-group>
      <span class="review-hint">点行左侧箭头查看明细；通过后冻存记录按申请人、审核当天记为出库</span>
    </div>
    <el-table v-loading="loading" :data="items" size="small" max-height="520" row-key="id" empty-text="没有出库申请">
      <el-table-column type="expand" width="36">
        <template #default="{ row }">
          <el-table :data="row.items" size="small" class="review-detail">
            <el-table-column prop="library_code" label="建库编号" width="110" show-overflow-tooltip />
            <el-table-column prop="target_name" label="靶点" min-width="110" show-overflow-tooltip />
            <el-table-column prop="instrument_on" label="上机日期" width="100" />
            <el-table-column prop="mouse_strain" label="鼠型" min-width="90" show-overflow-tooltip />
            <el-table-column prop="cell_count" label="细胞数量" width="90" show-overflow-tooltip />
            <el-table-column prop="sample_source" label="样品来源" width="110" show-overflow-tooltip />
            <el-table-column prop="cell_kind" label="细胞类型" width="90" />
            <el-table-column prop="tube_count" label="管数" width="60" align="center" />
            <el-table-column prop="box_location" label="冻存位置" min-width="100" show-overflow-tooltip />
            <el-table-column prop="remark" label="备注" min-width="120" show-overflow-tooltip />
          </el-table>
        </template>
      </el-table-column>
      <el-table-column prop="request_no" label="申请单号" width="170" />
      <el-table-column prop="applicant" label="出库申请人" width="100" show-overflow-tooltip />
      <el-table-column prop="item_count" label="数量" width="70" align="center" />
      <el-table-column prop="applied_on" label="申请日期" width="100" />
      <el-table-column label="状态" width="80" align="center">
        <template #default="{ row }">
          <el-tag :type="statusTone(row.status)" size="small" effect="plain">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="reviewer" label="审核人" width="90" show-overflow-tooltip />
      <el-table-column prop="reviewed_at" label="审核时间" width="150" />
      <el-table-column prop="review_note" label="审核意见" min-width="120" show-overflow-tooltip />
      <el-table-column v-if="canReview" label="操作" width="110" align="center">
        <template #default="{ row }">
          <template v-if="row.status === '待审核'">
            <el-button link type="primary" @click="approve(row)">通过</el-button>
            <el-button link type="danger" @click="reject(row)">驳回</el-button>
          </template>
        </template>
      </el-table-column>
    </el-table>
  </el-dialog>
</template>

<script>
import {
  ElButton,
  ElDialog,
  ElMessage,
  ElMessageBox,
  ElRadioButton,
  ElRadioGroup,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus'

import { notifyApiError } from '#/api/errors'
import { fetchCellCheckoutRequests, reviewCellCheckout } from '#/api/molecularLibrary'

const STATUS_TABS = [
  { value: '待审核', label: '待审核' },
  { value: '已通过', label: '已通过' },
  { value: '已驳回', label: '已驳回' },
  { value: '', label: '全部' },
]
const STATUS_TONES = { 待审核: 'warning', 已通过: 'success', 已驳回: 'info' }

export default {
  name: 'LibraryCellCheckoutReviewDialog',
  components: { ElButton, ElDialog, ElRadioButton, ElRadioGroup, ElTable, ElTableColumn, ElTag },
  props: {
    modelValue: { type: Boolean, default: false },
    canReview: { type: Boolean, default: false },
  },
  emits: ['update:modelValue', 'reviewed'],
  data() {
    return {
      statusTabs: STATUS_TABS,
      status: '待审核',
      items: [],
      loading: false,
    }
  },
  methods: {
    statusTone(status) {
      return STATUS_TONES[status] || 'info'
    },
    async load() {
      this.loading = true
      try {
        const data = await fetchCellCheckoutRequests(this.status)
        this.items = data?.items || []
      } catch (error) {
        notifyApiError(error, { messages: { default: '加载出库申请失败' } })
      } finally {
        this.loading = false
      }
    },
    async approve(row) {
      try {
        await ElMessageBox.confirm(
          `通过 ${row.request_no}？${row.item_count} 条冻存细胞将记为已出库，出库人 ${row.applicant || '申请人'}。`,
          '出库审核',
          { type: 'warning', confirmButtonText: '通过' },
        )
      } catch {
        return
      }
      await this.submitReview(row, true)
    },
    async reject(row) {
      let note = ''
      try {
        const result = await ElMessageBox.prompt('驳回原因（可不填）', `驳回 ${row.request_no}`, {
          inputPlaceholder: '驳回原因',
          confirmButtonText: '驳回',
          inputValidator: (value) => String(value || '').length <= 500 || '不能超过 500 个字',
        })
        note = String(result.value || '').trim()
      } catch {
        return
      }
      await this.submitReview(row, false, note)
    },
    async submitReview(row, approve, note = '') {
      try {
        await reviewCellCheckout({ id: row.id, approve, note })
        ElMessage.success(approve ? '已通过，冻存细胞已出库' : '已驳回')
        this.$emit('reviewed')
      } catch (error) {
        notifyApiError(error, { messages: { default: '审核失败' } })
      }
      await this.load()
    },
  },
}
</script>

<style scoped>
.review-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 12px;
}
.review-hint {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.review-detail {
  padding: 4px 12px 8px 36px;
}
</style>
