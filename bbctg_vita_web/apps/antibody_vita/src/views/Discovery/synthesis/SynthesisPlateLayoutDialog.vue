<template>
  <el-dialog
    :model-value="modelValue"
    title="上清板布局"
    width="1080px"
    append-to-body
    destroy-on-close
    @update:model-value="$emit('update:modelValue', $event)"
    @open="open"
  >
    <div
      v-loading="loading || querying"
      :element-loading-text="querying ? '正在向合成公司查询，大订单可能要一分多钟…' : ''"
      class="plate-body"
    >
      <p class="plate-meta">{{ headline }}</p>
      <template v-if="!plates.length && !loading">
        <el-empty :description="emptyText" :image-size="72" />
        <div v-if="missing.length" class="plate-missing">
          <span class="plate-missing-label">未合成 {{ missing.length }} 个</span>{{ missing.join('、') }}
        </div>
      </template>
      <el-tabs v-else-if="plates.length" v-model="tab">
        <el-tab-pane label="布局" name="grid">
          <div v-for="(plate, index) in grids" :key="plate.plate_no" class="plate-block">
            <div class="plate-title">96孔板{{ index + 1 }}<span>板号 {{ plate.plate_no || '-' }} · {{ plate.count }} 孔</span></div>
            <div class="plate-scroll">
              <table class="plate-grid">
                <thead>
                  <tr>
                    <th></th>
                    <th v-for="col in COLUMNS" :key="col">{{ col }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="letter in ROWS" :key="letter">
                    <th>{{ letter }}</th>
                    <td v-for="col in COLUMNS" :key="col" :title="cellTitle(plate.cells[letter + col])">
                      {{ plate.cells[letter + col]?.sample_name || '' }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <div v-if="missing.length" class="plate-missing">
            <span class="plate-missing-label">未合成 {{ missing.length }} 个</span>{{ missing.join('、') }}
          </div>
        </el-tab-pane>
        <el-tab-pane label="孔位明细" name="detail">
          <el-table :data="details" size="small" max-height="460">
            <el-table-column prop="plate_no" label="板号" min-width="110" show-overflow-tooltip />
            <el-table-column prop="well_no" label="孔号" width="80" />
            <el-table-column prop="sample_name" label="蛋白名称" min-width="180" show-overflow-tooltip />
            <el-table-column prop="potency" label="浓度(ug/mL)" width="110" align="right" />
            <el-table-column prop="specs" label="规格(mL/支)" width="110" align="right" />
            <el-table-column prop="volume" label="体积(mL)" width="96" align="right" />
            <el-table-column prop="sample_enter_vol" label="质粒量(ug)" width="104" align="right" />
            <el-table-column prop="received_at" label="接收时间" width="140" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>
    <template #footer>
      <el-button
        v-if="canQuery"
        :icon="Refresh"
        :loading="querying"
        :disabled="loading"
        title="向合成公司查询这单的上清板布局，有更新就入库"
        @click="query"
      >
        刷新
      </el-button>
      <el-button type="primary" :icon="Download" :disabled="!plates.length || querying" @click="download">
        下载 Excel
      </el-button>
      <el-button @click="$emit('update:modelValue', false)">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script>
import { Download, Refresh } from '@element-plus/icons-vue'
import {
  ElButton,
  ElDialog,
  ElEmpty,
  ElMessage,
  ElTabPane,
  ElTable,
  ElTableColumn,
  ElTabs,
} from 'element-plus'

import { notifyApiError } from '#/api/errors'
import {
  exportSynthesisPlateLayout,
  fetchSynthesisPlateLayoutPreview,
  querySynthesisPlateLayout,
} from '#/api/discoverySynthesis'
import { downloadListExcel } from '#/utils/downloadExcel'

const ROWS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
const COLUMNS = Array.from({ length: 12 }, (_, index) => index + 1)

export default {
  name: 'SynthesisPlateLayoutDialog',
  components: { ElButton, ElDialog, ElEmpty, ElTabPane, ElTable, ElTableColumn, ElTabs },
  props: {
    modelValue: { type: Boolean, default: false },
    row: { type: Object, default: null },
  },
  emits: ['update:modelValue', 'refreshed'],
  setup() {
    return { COLUMNS, Download, Refresh, ROWS }
  },
  data() {
    return {
      loading: false,
      querying: false,
      tab: 'grid',
      preview: null,
      notice: '',
    }
  },
  computed: {
    plates() {
      return this.preview?.plates || []
    },
    missing() {
      return this.preview?.missing || []
    },
    canQuery() {
      return this.row?.supply_mode === '合成到货'
    },
    grids() {
      return this.plates.map((plate) => {
        const cells = {}
        plate.wells.forEach((well) => {
          const text = String(well.well_no || '')
          cells[text.slice(0, 1) + Number(text.slice(1))] = well
        })
        return { plate_no: plate.plate_no, count: plate.wells.length, cells }
      })
    },
    details() {
      const rows = this.plates.flatMap((plate) => plate.wells.map((well) => ({ ...well, plate_no: plate.plate_no })))
      return rows.concat(this.missing.map((name) => ({ plate_no: '', well_no: '未合成', sample_name: name })))
    },
    headline() {
      const data = this.preview || {}
      const wells = this.plates.reduce((sum, plate) => sum + plate.wells.length, 0)
      const parts = [data.order_no || this.row?.order_no || '', data.target_name || '']
      if (wells) parts.push(`已收到 ${wells} 孔`)
      if (this.missing.length) parts.push(`未合成 ${this.missing.length} 个`)
      if (data.supernatant_checked_at) parts.push(`上次向合成公司查询 ${data.supernatant_checked_at}`)
      return parts.filter(Boolean).join(' · ')
    },
    emptyText() {
      if (this.notice) return this.notice
      return this.preview?.message || '还没收到合成公司的上清板布局'
    },
  },
  methods: {
    async open() {
      this.preview = null
      this.notice = ''
      this.tab = 'grid'
      await this.load()
      if (this.preview && !this.plates.length && !this.missing.length && this.canQuery) await this.query()
    },
    async load() {
      if (!this.row?.id) return
      this.loading = true
      try {
        this.preview = await fetchSynthesisPlateLayoutPreview(this.row.id)
      } catch (error) {
        notifyApiError(error, { messages: { default: '版布局加载失败，请稍后再试' } })
      } finally {
        this.loading = false
      }
    },
    async query() {
      if (!this.row?.id || this.querying) return
      this.querying = true
      try {
        const res = await querySynthesisPlateLayout(this.row.id)
        if (res?.row) this.$emit('refreshed', res.row)
        if (res?.state === 'found' && Number(res.wells) > 0) {
          const missing = Number(res.not_synthesized) || 0
          this.notice = ''
          ElMessage.success(`已从合成公司刷新：${res.wells} 孔${missing ? `，未合成 ${missing} 个` : ''}`)
        } else {
          this.notice = res?.message || '合成公司还没有这单的上清板布局'
          ElMessage({ type: res?.state === 'failed' ? 'warning' : 'info', message: this.notice, grouping: true })
        }
      } catch (error) {
        notifyApiError(error, { messages: { default: '向合成公司查询失败，请稍后再试' } })
      } finally {
        this.querying = false
      }
      await this.load()
    },
    async download() {
      if (!this.row?.id || !this.plates.length) return
      const target = String(this.preview?.target_name || '').trim()
      const name = `${this.preview?.order_no || this.row.order_no}孔板上清布局${target ? `-${target}` : ''}.xlsx`
      try {
        await downloadListExcel(() => exportSynthesisPlateLayout(this.row.id), name)
      } catch (error) {
        notifyApiError(error, { messages: { default: '版布局下载失败，请稍后再试' } })
      }
    },
    cellTitle(well) {
      if (!well) return ''
      const parts = [`${well.well_no} ${well.sample_name}`]
      if (well.potency != null) parts.push(`浓度 ${well.potency} ug/mL`)
      if (well.volume != null) parts.push(`体积 ${well.volume} mL`)
      if (well.received_at) parts.push(`接收 ${well.received_at}`)
      return parts.join(' · ')
    },
  },
}
</script>

<style scoped>
.plate-body {
  min-height: 160px;
}

.plate-meta {
  margin: 0 0 8px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.plate-block + .plate-block {
  margin-top: 16px;
}

.plate-title {
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.plate-title span {
  margin-left: 8px;
  font-weight: 400;
  color: var(--el-text-color-secondary);
}

.plate-scroll {
  overflow-x: auto;
}

.plate-grid {
  width: 100%;
  min-width: 960px;
  border-collapse: collapse;
  table-layout: fixed;
  font-size: 12px;
}

.plate-grid th,
.plate-grid td {
  height: 26px;
  padding: 0 4px;
  border: 1px solid var(--el-border-color-lighter);
  overflow: hidden;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.plate-grid th {
  background: var(--el-fill-color-light);
  color: var(--el-text-color-regular);
  font-weight: 500;
}

.plate-grid thead th:first-child,
.plate-grid tbody th {
  width: 32px;
}

.plate-missing {
  margin-top: 12px;
  font-size: 12px;
  line-height: 20px;
  color: var(--el-text-color-regular);
}

.plate-missing-label {
  margin-right: 8px;
  color: var(--el-text-color-secondary);
}
</style>
