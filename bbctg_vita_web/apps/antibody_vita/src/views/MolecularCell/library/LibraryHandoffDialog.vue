<template>
  <el-dialog
    :model-value="modelValue"
    title="交接至文库构建"
    width="720px"
    append-to-body
    destroy-on-close
    @close="close"
  >
    <div v-loading="loading">
      <section class="handoff-section">
        <h3>核对来源样品</h3>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="项目编号">{{ preview.project_code || '—' }}</el-descriptions-item>
          <el-descriptions-item label="课题类型">{{ preview.study_type || '—' }}</el-descriptions-item>
          <el-descriptions-item label="靶点">{{ preview.target_name || '—' }}</el-descriptions-item>
          <el-descriptions-item label="归类鼠型">{{ mouseCategoryLabel(preview.mouse_model) || '—' }}</el-descriptions-item>
          <el-descriptions-item label="上机日期">{{ preview.instrument_on || '未填' }}</el-descriptions-item>
          <el-descriptions-item label="阳性细胞数">{{ preview.positive_cell_count ?? '—' }}</el-descriptions-item>
          <el-descriptions-item label="筛选方式" :span="2">{{ preview.screening_methods || '—' }}</el-descriptions-item>
          <el-descriptions-item label="优先级">{{ preview.priority || '—' }}</el-descriptions-item>
        </el-descriptions>
      </section>

      <section class="handoff-section">
        <h3>已有建库工单</h3>
        <p v-if="!existing.length" class="empty-hint">这条发现安排还没有建库工单。</p>
        <el-table v-else :data="existing" size="small" border>
          <el-table-column label="建库类型" min-width="190">
            <template #default="{ row }">{{ buildTypeLabel(row.build_type) }}</template>
          </el-table-column>
          <el-table-column prop="library_code" label="建库编号" min-width="110" />
          <el-table-column prop="status" label="状态" width="90" />
          <el-table-column label="" width="80">
            <template #default="{ row }">
              <el-button v-if="canOpenLibrary" link type="primary" @click="openExisting(row)">打开</el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <section class="handoff-section">
        <h3>本次要建</h3>
        <el-checkbox-group v-model="selectedTypes" class="build-picks">
          <el-checkbox v-for="item in buildOptions" :key="item.value" :label="item.value">
            {{ item.label }}
            <span v-if="existingTypes.has(item.value)" class="exist-mark">已有</span>
          </el-checkbox>
        </el-checkbox-group>
        <div
          v-for="buildType in selectedTypes"
          :key="buildType"
          class="source-pick"
        >
          <span>{{ buildTypeLabel(buildType) }}来源</span>
          <el-select v-model="sourceSelections[buildType]" placeholder="选择样品来源">
            <el-option
              v-for="item in sourcesFor(buildType)"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </div>
        <p v-if="needsInstrumentDate && !preview.instrument_on" class="gate-hint">
          请先在发现台填写剖鼠日期；交接后将作为文库工单的上机日期。
        </p>
      </section>
    </div>
    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :disabled="!canSubmit" :loading="saving" @click="confirm">
        创建并继续
      </el-button>
    </template>
  </el-dialog>
</template>

<script>
import {
  ElButton,
  ElCheckbox,
  ElCheckboxGroup,
  ElDescriptions,
  ElDescriptionsItem,
  ElDialog,
  ElMessage,
  ElOption,
  ElSelect,
  ElTable,
  ElTableColumn,
} from 'element-plus'
import { useUserStore } from '@vben/stores'

import { fetchLibraryOrdersByDiscovery, handoffLibraryOrders, LIBRARY_CREATED_KEY } from '#/api/molecularLibrary'
import { notifyApiError } from '#/api/errors'
import { canViewLibrary } from '#/utils/molecularPermission'
import {
  BUILD_TYPE_OPTIONS,
  buildTypeLabel,
  INSTRUMENT_DATE_BUILDS,
  mouseCategoryLabel,
  optionsForBuild,
  SAMPLE_SOURCE_OPTIONS,
} from './libraryColumns'

export default {
  name: 'LibraryHandoffDialog',
  components: {
    ElButton,
    ElCheckbox,
    ElCheckboxGroup,
    ElDescriptions,
    ElDescriptionsItem,
    ElDialog,
    ElOption,
    ElSelect,
    ElTable,
    ElTableColumn,
  },
  props: {
    modelValue: { type: Boolean, default: false },
    discoveryRow: { type: Object, default: null },
  },
  emits: ['update:modelValue', 'created'],
  data() {
    return {
      loading: false,
      saving: false,
      preview: {},
      existing: [],
      selectedTypes: [],
      sourceSelections: {},
      loadRequestId: 0,
    }
  },
  computed: {
    canOpenLibrary() {
      return canViewLibrary(useUserStore().userInfo)
    },
    buildOptions() {
      return BUILD_TYPE_OPTIONS
    },
    existingTypes() {
      return new Set(
        this.existing
          .filter((item) => item.status !== '已取消')
          .map((item) => item.build_type),
      )
    },
    needsInstrumentDate() {
      return this.selectedTypes.some((item) => INSTRUMENT_DATE_BUILDS.includes(item))
    },
    canSubmit() {
      if (this.saving || !this.selectedTypes.length) return false
      if (this.needsInstrumentDate && !this.preview.instrument_on) return false
      return this.selectedTypes.every((item) => Boolean(this.sourceSelections[item]))
    },
  },
  watch: {
    modelValue(value) {
      if (value) this.load()
    },
  },
  methods: {
    buildTypeLabel,
    mouseCategoryLabel,
    sourcesFor(buildType) {
      return optionsForBuild(SAMPLE_SOURCE_OPTIONS, buildType)
    },
    close() {
      this.$emit('update:modelValue', false)
    },
    async load() {
      const row = this.discoveryRow
      if (!row?.id) return
      const requestId = ++this.loadRequestId
      this.loading = true
      try {
        const data = await fetchLibraryOrdersByDiscovery({ discovery_workbench_id: row.id })
        if (requestId !== this.loadRequestId || !this.modelValue) return
        this.preview = data?.discovery || {}
        this.existing = data?.items || []
        const suggestions = data?.suggested_items || []
        this.sourceSelections = Object.fromEntries(
          suggestions.map((item) => [item.build_type, item.sample_source]),
        )
        this.selectedTypes = [...new Set(suggestions.map((item) => item.build_type).filter(Boolean))]
      } catch (error) {
        if (requestId !== this.loadRequestId || !this.modelValue) return
        notifyApiError(error, { messages: { default: '加载交接信息失败' } })
        this.close()
      } finally {
        if (requestId === this.loadRequestId) this.loading = false
      }
    },
    openExisting(row) {
      this.close()
      this.$router.push({
        path: '/molecular-cell/library-construction',
        query: { created: row.id },
      })
    },
    async confirm() {
      if (!this.canSubmit) return
      this.saving = true
      try {
        const result = await handoffLibraryOrders({
          discovery_workbench_id: this.discoveryRow.id,
          items: this.selectedTypes.map((buildType) => ({
            build_type: buildType,
            sample_source: this.sourceSelections[buildType],
          })),
        })
        const created = result?.items || []
        ElMessage.success(`已创建 ${created.length} 条建库工单`)
        this.$emit('created', created)
        this.close()
        if (this.canOpenLibrary && created[0]?.id) {
          sessionStorage.setItem(LIBRARY_CREATED_KEY, JSON.stringify(created[0]))
          this.$router.push({
            path: '/molecular-cell/library-construction',
            query: { created: created[0].id },
          })
        }
      } catch (error) {
        notifyApiError(error, { messages: { default: '交接失败' } })
      } finally {
        this.saving = false
      }
    },
  },
}
</script>

<style scoped>
.handoff-section {
  margin-bottom: 18px;
}

.handoff-section h3 {
  margin: 0 0 8px;
  font-size: 14px;
}

.gate-hint,
.empty-hint,
.exist-mark {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.gate-hint {
  color: var(--el-color-warning);
  margin: 10px 0 0;
}

.exist-mark {
  margin-left: 6px;
}

.build-picks {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 16px;
}

.source-pick {
  display: grid;
  grid-template-columns: 190px minmax(0, 1fr);
  align-items: center;
  gap: 12px;
  margin-top: 10px;
}
</style>
