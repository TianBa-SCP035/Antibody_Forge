<template>
  <el-dialog
    :model-value="modelValue"
    title="交接至文库构建"
    width="720px"
    append-to-body
    @close="close"
  >
    <div v-loading="loading" class="handoff-body">
      <div class="handoff-meta">
        <div class="meta-title">
          <strong>{{ preview.project_code || '未填项目编号' }}</strong>
          <span>{{ preview.target_name || '未填靶点' }}</span>
        </div>
        <div class="meta-line">
          <span v-for="item in metaItems" :key="item.label">
            {{ item.label }}
            <b :class="{ empty: !item.value }">{{ item.value || '未填' }}</b>
          </span>
        </div>
      </div>
      <p v-if="!loading && !methodNames.length" class="muted method-hint">未标筛选方式，下面四行仍可直接选</p>
      <p v-else-if="!loading" class="muted method-hint">只交接已标的筛选方式，其余路线不能选</p>

      <div v-if="existing.length" class="handoff-existing">
        <span class="existing-label">已有</span>
        <button
          v-for="item in existing"
          :key="item.id"
          type="button"
          class="existing-link"
          @click="openExisting(item)"
        >
          {{ item.library_code || item.library_order_id }}
          {{ buildTypeLabel(item.build_type) }}
          <em>{{ sourceLabel(item.sample_source) }}</em>
          <span>{{ item.status }}</span>
        </button>
      </div>

      <div class="handoff-rows">
        <section
          v-for="row in rows"
          :key="row.method"
          class="handoff-row"
        >
          <div class="row-name" :class="`tone-${row.tone}`">{{ row.method }}</div>
          <div class="row-picks">
            <button
              v-for="pick in row.picks"
              :key="pick.id"
              type="button"
              class="handoff-chip"
              :class="{ on: selectedIds.includes(pick.id) }"
              :disabled="!pickOpen(row, pick)"
              :title="pickTitle(row, pick)"
              @click="toggle(row, pick)"
            >
              {{ pick.label }}
              <em v-if="alreadyHas(pick)">已有</em>
            </button>
          </div>
        </section>
      </div>

      <p v-if="needsInstrumentDate && !preview.instrument_on" class="gate-hint">
        孔板、混管和噬菌体展示需要先在发现台填写剖鼠日期，交接后写入上机日期。
      </p>
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
import { ElButton, ElDialog, ElMessage } from 'element-plus'
import { useUserStore } from '@vben/stores'

import { notifyApiError } from '#/api/errors'
import { fetchLibraryOrdersByDiscovery, handoffLibraryOrders, LIBRARY_CREATED_KEY } from '#/api/molecularLibrary'
import { canViewLibrary } from '#/utils/molecularPermission'

import {
  buildTypeLabel,
  HANDOFF_METHOD_ROWS,
  INSTRUMENT_DATE_BUILDS,
  sampleSourceLabel,
} from './libraryColumns'

export default {
  name: 'LibraryHandoffDialog',
  components: {
    ElButton,
    ElDialog,
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
      selectedIds: [],
      loadRequestId: 0,
    }
  },
  computed: {
    canOpenLibrary() {
      return canViewLibrary(useUserStore().userInfo)
    },
    methodNames() {
      return String(this.preview.screening_methods || '')
        .split(/[,，]/)
        .map((item) => item.trim())
        .filter(Boolean)
    },
    metaItems() {
      return [
        { label: '课题类型', value: this.preview.study_type },
        { label: '小鼠品系', value: this.preview.mouse_strain },
        { label: '优先级', value: this.preview.priority },
        { label: '上机日期', value: this.preview.instrument_on },
        { label: '阳性细胞', value: this.preview.positive_cell_count },
      ]
    },
    rows() {
      return HANDOFF_METHOD_ROWS
    },
    picks() {
      return this.rows.flatMap((row) => row.picks)
    },
    selectedPicks() {
      return this.picks.filter((item) => this.selectedIds.includes(item.id))
    },
    needsInstrumentDate() {
      return this.selectedPicks.some((item) => INSTRUMENT_DATE_BUILDS.includes(item.buildType))
    },
    canSubmit() {
      return !this.saving && this.selectedPicks.length > 0 && !(this.needsInstrumentDate && !this.preview.instrument_on)
    },
  },
  watch: {
    modelValue(value) {
      if (value) this.load()
    },
  },
  methods: {
    buildTypeLabel,
    sourceLabel: sampleSourceLabel,
    alreadyHas(pick) {
      return this.existing.some((item) => {
        if (item.status === '已取消' || item.build_type !== pick.buildType) return false
        if (pick.id === 'phage-ngs') return true
        if (item.sample_source !== pick.source) return false
        return !pick.sampleType || item.sample_type === pick.sampleType
      })
    },
    pickOpen(row, pick) {
      if (!this.methodNames.length) return true
      if (!this.methodNames.includes(row.method)) return false
      if (pick.id !== 'both-plate') return true
      return this.methodNames.includes('达普') && this.methodNames.includes('Beacon')
    },
    pickTitle(row, pick) {
      if (this.pickOpen(row, pick)) return pick.hint || ''
      if (pick.id === 'both-plate' && this.methodNames.includes(row.method)) {
        return '需要同时标达普和 Beacon'
      }
      return '这条安排未标该筛选方式'
    },
    toggle(row, pick) {
      if (!this.pickOpen(row, pick)) return
      if (this.selectedIds.includes(pick.id)) {
        this.selectedIds = this.selectedIds.filter((item) => item !== pick.id)
        return
      }
      let next = [...this.selectedIds]
      if (pick.id === 'both-plate') {
        next = next.filter((item) => item !== 'dapu-plate' && item !== 'beacon-plate')
      } else if (pick.id === 'dapu-plate' || pick.id === 'beacon-plate') {
        next = next.filter((item) => item !== 'both-plate')
      }
      next.push(pick.id)
      this.selectedIds = next
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
        const ids = []
        suggestions.forEach((item) => {
          const pick = this.pickFor(item.build_type, item.sample_source)
          if (pick && !ids.includes(pick.id)) ids.push(pick.id)
        })
        this.selectedIds = ids
      } catch (error) {
        if (requestId !== this.loadRequestId || !this.modelValue) return
        notifyApiError(error, { messages: { default: '加载交接信息失败' } })
        this.close()
      } finally {
        if (requestId === this.loadRequestId) this.loading = false
      }
    },
    pickFor(buildType, source) {
      return this.picks.find((item) => item.buildType === buildType && item.source === source)
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
          items: this.selectedPicks.map((pick) => ({
            build_type: pick.buildType,
            sample_source: pick.source,
            ...(pick.sampleType ? { sample_type: pick.sampleType } : {}),
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
.handoff-body {
  min-height: 280px;
}

.handoff-meta {
  padding: 12px 14px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  background: var(--el-fill-color-light);
}

.meta-title {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px 12px;
}

.meta-title strong {
  color: var(--el-text-color-primary);
  font-size: 16px;
  font-weight: 600;
}

.meta-title span {
  color: var(--el-text-color-regular);
  font-size: 14px;
}

.meta-line {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 18px;
  margin-top: 8px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.meta-line b {
  margin-left: 4px;
  color: var(--el-text-color-primary);
  font-weight: 500;
  white-space: pre-line;
}

.meta-line b.empty {
  color: var(--el-text-color-placeholder);
  font-weight: 400;
}

.method-hint {
  margin: 8px 0 0;
}

.muted {
  color: var(--el-text-color-placeholder);
  font-size: 12px;
}

.handoff-existing {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 14px;
}

.existing-label {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.existing-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 8px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
  background: var(--el-fill-color-blank);
  color: var(--el-text-color-regular);
  font-size: 12px;
  cursor: pointer;
}

.existing-link em,
.handoff-chip em {
  color: var(--el-text-color-secondary);
  font-style: normal;
}

.handoff-rows {
  margin-top: 16px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.handoff-row {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
  min-height: 52px;
  padding: 8px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.row-name {
  padding-top: 5px;
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-secondary);
}

.row-name.tone-primary { color: var(--el-color-primary); }
.row-name.tone-success { color: var(--el-color-success); }
.row-name.tone-warning { color: var(--el-color-warning); }
.row-name.tone-purple { color: #7c5cf0; }

.row-picks {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding-top: 1px;
}

.handoff-chip {
  height: 30px;
  padding: 0 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  background: var(--el-fill-color-blank);
  color: var(--el-text-color-regular);
  font-size: 13px;
  cursor: pointer;
}

.handoff-chip.on {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
}

.handoff-chip:disabled {
  border-color: var(--el-border-color-lighter);
  background: var(--el-fill-color-light);
  color: var(--el-text-color-placeholder);
  cursor: not-allowed;
}

.handoff-chip em {
  margin-left: 6px;
  font-size: 12px;
}

.gate-hint {
  margin: 12px 0 0;
  color: var(--el-color-warning);
  font-size: 12px;
}
</style>
