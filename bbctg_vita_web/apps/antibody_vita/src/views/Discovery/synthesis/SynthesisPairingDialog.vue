<template>
  <el-dialog
    :model-value="modelValue"
    title="转染配对"
    width="760px"
    append-to-body
    destroy-on-close
    @update:model-value="$emit('update:modelValue', $event)"
    @open="load"
  >
    <p class="pair-meta">{{ headline }}</p>
    <el-table v-loading="loading" :data="items" size="small" max-height="420" empty-text="这张工单还没有转染配对">
      <el-table-column type="index" label="序号" width="64" align="center" />
      <el-table-column prop="protein_name" label="蛋白名称" min-width="180" show-overflow-tooltip />
      <el-table-column prop="heavy_chain" label="重链" min-width="180" show-overflow-tooltip />
      <el-table-column prop="light_chain" label="轻链" min-width="160" show-overflow-tooltip />
    </el-table>
    <template #footer>
      <el-button v-if="transfectionOrderId" type="primary" plain @click="openTable">在转染表中查看</el-button>
      <el-button @click="$emit('update:modelValue', false)">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script>
import { ElButton, ElDialog, ElMessage, ElTable, ElTableColumn } from 'element-plus'

import { notifyApiError } from '#/api/errors'
import { fetchSynthesisTransfectionPairs } from '#/api/discoverySynthesis'

export default {
  name: 'SynthesisPairingDialog',
  components: { ElButton, ElDialog, ElTable, ElTableColumn },
  props: {
    modelValue: { type: Boolean, default: false },
    row: { type: Object, default: null },
  },
  emits: ['update:modelValue'],
  data() {
    return {
      loading: false,
      items: [],
      transfectionOrderId: '',
      message: '',
    }
  },
  computed: {
    headline() {
      const code = this.transfectionOrderId || this.row?.order_no || ''
      return [code, this.message].filter(Boolean).join(' · ')
    },
  },
  methods: {
    async load() {
      this.items = []
      this.transfectionOrderId = ''
      this.message = ''
      if (!this.row?.id) return
      this.loading = true
      try {
        const data = await fetchSynthesisTransfectionPairs(this.row.id)
        this.items = data?.items || []
        this.transfectionOrderId = data?.transfection_order_id || ''
        this.message = data?.message || ''
      } catch (error) {
        notifyApiError(error, { messages: { default: '转染配对加载失败' } })
      } finally {
        this.loading = false
      }
    },
    openTable() {
      if (!this.transfectionOrderId) return
      this.$emit('update:modelValue', false)
      this.$router.push({
        name: 'TransfectionProteins',
        query: { order_code: this.transfectionOrderId },
      }).catch(() => {
        ElMessage.warning('没有权限打开转染表')
      })
    },
  },
}
</script>

<style scoped>
.pair-meta {
  margin: 0 0 8px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
</style>
