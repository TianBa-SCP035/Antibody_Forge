<template>
  <el-dialog
    :model-value="modelValue"
    title="冻存细胞出库申请"
    width="1080px"
    append-to-body
    destroy-on-close
    @update:model-value="$emit('update:modelValue', $event)"
    @open="load"
  >
    <p class="checkout-meta">
      <span>{{ headline }}</span>
      <span v-if="summary">{{ summary }}</span>
    </p>
    <el-table
      ref="table"
      v-loading="loading"
      :data="items"
      size="small"
      max-height="460"
      row-key="cell_bank_id"
      empty-text="来源发现安排没有在库的冻存细胞"
      @selection-change="selected = $event"
    >
      <el-table-column type="selection" width="40" />
      <el-table-column prop="library_code" label="建库编号" width="110" show-overflow-tooltip />
      <el-table-column prop="target_name" label="靶点" min-width="110" show-overflow-tooltip />
      <el-table-column prop="instrument_on" label="上机日期" width="100" />
      <el-table-column prop="mouse_strain" label="鼠型" min-width="90" show-overflow-tooltip />
      <el-table-column prop="sample_source" label="样品来源" width="110" show-overflow-tooltip />
      <el-table-column prop="cell_kind" label="细胞类型" width="90" />
      <el-table-column prop="cell_count" label="细胞数量" width="90" show-overflow-tooltip />
      <el-table-column prop="tube_count" label="管数" width="60" align="center" />
      <el-table-column prop="box_location" label="冻存位置" min-width="100" show-overflow-tooltip />
      <el-table-column prop="remark" label="备注" min-width="120" show-overflow-tooltip />
    </el-table>
    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :disabled="!selected.length" :loading="submitting" @click="submit">
        提交出库申请{{ selected.length ? `（${selected.length} 条）` : '' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script>
import { ElButton, ElDialog, ElMessage, ElTable, ElTableColumn } from 'element-plus'

import { notifyApiError } from '#/api/errors'
import { fetchCellCheckoutCandidates, submitCellCheckout } from '#/api/molecularLibrary'

export default {
  name: 'LibraryCellCheckoutDialog',
  components: { ElButton, ElDialog, ElTable, ElTableColumn },
  props: {
    modelValue: { type: Boolean, default: false },
    /** { order_ids } 或 { filters }，原样传给后端 */
    selection: { type: Object, default: null },
    headline: { type: String, default: '' },
  },
  emits: ['update:modelValue', 'submitted'],
  data() {
    return {
      items: [],
      selected: [],
      stats: null,
      loading: false,
      submitting: false,
    }
  },
  computed: {
    summary() {
      const stats = this.stats
      if (!stats) return ''
      const parts = [`${stats.order_count} 条工单`, `可出库 ${this.items.length} 条冻存记录`]
      if (stats.order_count > stats.linked_count) parts.push(`${stats.order_count - stats.linked_count} 条手工建的工单没有来源发现安排`)
      if (stats.pending_count) parts.push(`${stats.pending_count} 条在审核中`)
      return parts.join('，')
    },
  },
  methods: {
    async load() {
      this.items = []
      this.selected = []
      this.stats = null
      if (!this.selection) return
      this.loading = true
      try {
        const data = await fetchCellCheckoutCandidates(this.selection)
        this.items = data?.items || []
        this.stats = data
        await this.$nextTick()
        this.items.forEach((item) => this.$refs.table?.toggleRowSelection(item, true))
      } catch (error) {
        notifyApiError(error, { messages: { default: '加载冻存细胞失败' } })
      } finally {
        this.loading = false
      }
    },
    async submit() {
      if (!this.selected.length || this.submitting) return
      this.submitting = true
      try {
        const saved = await submitCellCheckout({
          ...this.selection,
          cell_bank_ids: this.selected.map((item) => item.cell_bank_id),
        })
        ElMessage.success(`已提交出库申请 ${saved.request_no}，等待审核`)
        this.$emit('update:modelValue', false)
        this.$emit('submitted', saved)
      } catch (error) {
        notifyApiError(error, { messages: { default: '提交出库申请失败' } })
        await this.load()
      } finally {
        this.submitting = false
      }
    },
  },
}
</script>

<style scoped>
.checkout-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
  margin: 0 0 12px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
</style>
