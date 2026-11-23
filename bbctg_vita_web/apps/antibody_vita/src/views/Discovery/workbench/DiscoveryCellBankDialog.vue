<template>
  <el-dialog
    :model-value="modelValue"
    title="留存细胞冻存入库"
    width="960px"
    append-to-body
    destroy-on-close
    @update:model-value="$emit('update:modelValue', $event)"
    @open="onOpen"
  >
    <p class="bank-meta">{{ headline }}</p>
    <el-form label-width="88px" class="bank-form" :disabled="!canEdit">
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="细胞类型">
            <el-select v-model="form.cell_kind" filterable allow-create default-first-option placeholder="脾细胞">
              <el-option v-for="item in cellKinds" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="冻存日期">
            <el-date-picker v-model="form.frozen_on" type="date" value-format="YYYY-MM-DD" placeholder="日期" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="管数">
            <el-input v-model="form.tube_count" placeholder="管数" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="细胞量">
            <el-input v-model="form.cell_count" placeholder="如 1e7/管" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="体积">
            <el-input v-model="form.volume" placeholder="如 1 mL" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="冻存位置">
            <el-input v-model="form.box_location" placeholder="盒位" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="操作人">
            <el-input v-model="form.operator" placeholder="操作人" />
          </el-form-item>
        </el-col>
        <el-col :span="16">
          <el-form-item label="鼠号">
            <el-input v-model="form.mouse_nos" placeholder="留存的鼠号" />
          </el-form-item>
        </el-col>
        <el-col :span="24">
          <el-form-item label="备注">
            <el-input v-model="form.remark" placeholder="备注" />
          </el-form-item>
        </el-col>
      </el-row>
      <div v-if="canEdit" class="bank-actions">
        <el-button type="primary" :loading="saving" @click="save">入库</el-button>
        <el-button @click="resetForm">清空</el-button>
      </div>
    </el-form>
    <el-table v-loading="loading" :data="items" size="small" max-height="280" empty-text="还没有冻存记录">
      <el-table-column prop="frozen_on" label="冻存日期" width="110" />
      <el-table-column prop="cell_kind" label="细胞类型" width="100" />
      <el-table-column prop="remark" label="备注" min-width="140" show-overflow-tooltip />
      <el-table-column prop="tube_count" label="管数" width="70" align="center" />
      <el-table-column prop="cell_count" label="细胞量" width="90" />
      <el-table-column prop="box_location" label="位置" min-width="100" show-overflow-tooltip />
      <el-table-column prop="operator" label="操作人" width="90" />
      <el-table-column prop="checked_out_by" label="出库人" width="90" show-overflow-tooltip />
      <el-table-column v-if="canEdit" label="操作" width="110" align="center">
        <template #default="{ row: record }">
          <el-button link type="primary" @click="checkout(record)">出库</el-button>
          <el-button link type="danger" @click="remove(record)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-dialog>
</template>

<script>
import {
  ElButton,
  ElCol,
  ElDatePicker,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElRow,
  ElSelect,
  ElTable,
  ElTableColumn,
} from 'element-plus'

import { notifyApiError } from '#/api/errors'
import {
  checkoutDiscoveryCellBank,
  deleteDiscoveryCellBank,
  fetchDiscoveryCellBank,
  saveDiscoveryCellBank,
} from '#/api/discoveryWorkbench'

const CELL_KINDS = ['脾细胞', '淋巴结', '骨髓', 'PBMC', '血浆细胞', '全细胞', '浆细胞', '其他']

function today() {
  const now = new Date()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${now.getFullYear()}-${month}-${day}`
}

export default {
  name: 'DiscoveryCellBankDialog',
  components: {
    ElButton,
    ElCol,
    ElDatePicker,
    ElDialog,
    ElForm,
    ElFormItem,
    ElInput,
    ElOption,
    ElRow,
    ElSelect,
    ElTable,
    ElTableColumn,
  },
  props: {
    modelValue: { type: Boolean, default: false },
    row: { type: Object, default: null },
    canEdit: { type: Boolean, default: false },
  },
  emits: ['update:modelValue'],
  data() {
    return {
      cellKinds: CELL_KINDS,
      items: [],
      loading: false,
      saving: false,
      form: {
        cell_kind: '脾细胞',
        mouse_nos: '',
        tube_count: '',
        cell_count: '',
        volume: '',
        box_location: '',
        frozen_on: '',
        operator: '',
        remark: '',
      },
    }
  },
  computed: {
    headline() {
      const row = this.row || {}
      return [row.project_code, row.target_name, row.discovery_id].filter(Boolean).join(' · ') || '未选择安排'
    },
  },
  methods: {
    emptyForm() {
      return {
        cell_kind: '脾细胞',
        mouse_nos: this.row?.mouse_nos || '',
        tube_count: '',
        cell_count: '',
        volume: '',
        box_location: '',
        frozen_on: today(),
        operator: '',
        remark: '',
      }
    },
    resetForm() {
      this.form = this.emptyForm()
    },
    onOpen() {
      this.resetForm()
      this.load()
    },
    async load() {
      const id = this.row?.id
      if (!id) {
        this.items = []
        return
      }
      this.loading = true
      try {
        const data = await fetchDiscoveryCellBank(id)
        this.items = data?.items || []
      } catch (error) {
        notifyApiError(error, { messages: { default: '冻存记录加载失败' } })
      } finally {
        this.loading = false
      }
    },
    async save() {
      if (!this.canEdit || !this.row?.id || this.saving) return
      this.saving = true
      try {
        await saveDiscoveryCellBank({
          workbench_id: this.row.id,
          ...this.form,
          tube_count: this.form.tube_count === '' ? null : this.form.tube_count,
        })
        ElMessage.success('已入库')
        this.resetForm()
        await this.load()
      } catch (error) {
        notifyApiError(error, { messages: { default: '冻存入库失败' } })
      } finally {
        this.saving = false
      }
    },
    async checkout(record) {
      if (!this.canEdit || !record?.id) return
      let name = ''
      try {
        const result = await ElMessageBox.prompt('填写出库人', '出库', {
          inputValue: record.checked_out_by || '',
          inputPlaceholder: '出库人',
          confirmButtonText: '出库',
        })
        name = String(result.value || '').trim()
      } catch {
        return
      }
      if (!name) {
        ElMessage.warning('请填写出库人')
        return
      }
      try {
        await checkoutDiscoveryCellBank(record.id, name)
        ElMessage.success('已出库')
        await this.load()
      } catch (error) {
        notifyApiError(error, { messages: { default: '出库失败' } })
      }
    },
    async remove(record) {
      if (!this.canEdit || !record?.id) return
      try {
        await ElMessageBox.confirm('删除这条冻存记录？删除后不可恢复。', '确认', { type: 'warning' })
      } catch {
        return
      }
      try {
        await deleteDiscoveryCellBank(record.id)
        ElMessage.success('已删除')
        await this.load()
      } catch (error) {
        notifyApiError(error, { messages: { default: '删除冻存记录失败' } })
      }
    },
  },
}
</script>

<style scoped>
.bank-meta {
  margin: 0 0 12px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.bank-form :deep(.el-select),
.bank-form :deep(.el-input) {
  width: 100%;
}
.bank-actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}
</style>
