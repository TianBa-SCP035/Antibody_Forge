<template>
  <div class="protein-page" :class="{ 'is-list-table-locked': listTableLocked }">
    <div class="page-header-band">
      <div class="title-group">
        <h1 class="page-title">转染表</h1>
        <p class="page-subtitle">蛋白与重链、轻链质粒的对应，在转染工单里导入。</p>
      </div>
      <div class="header-actions">
        <span class="total-count">共 {{ total }} 个蛋白</span>
        <ElButton :icon="Back" @click="backToOrders">转染与表达</ElButton>
        <ElButton type="warning" :icon="Download" :loading="exporting" @click="handleExport">导出</ElButton>
      </div>
    </div>

    <section class="workbench-panel">
      <div class="stats-strip">
        <button
          v-for="item in sourceTiles"
          :key="item.value || 'all'"
          type="button"
          class="stat-tile stat-tile-interactive"
          :class="[item.tone, { 'stat-tile-active': listQuery.source === item.value }]"
          @click="selectSource(item.value)"
        >
          <span class="stat-copy">
            <span class="stat-label">{{ item.label }}</span>
            <small>{{ item.hint }}</small>
          </span>
          <strong class="stat-value">{{ stats[item.statKey] || 0 }}</strong>
        </button>
      </div>
    </section>

    <div class="filter-strip list-filter-controls">
      <ElInput
        v-model="listQuery.protein_name"
        class="filter-item filter-keyword"
        clearable
        :prefix-icon="Search"
        v-bind="headerTop('protein_name', '蛋白名称')"
        @keyup.enter="handleFilter"
        @clear="handleFilter"
      />
      <ElInput
        v-model="listQuery.heavy_chain"
        class="filter-item"
        clearable
        v-bind="headerTop('heavy_chain', '重链')"
        @keyup.enter="handleFilter"
        @clear="handleFilter"
      />
      <ElInput
        v-model="listQuery.light_chain"
        class="filter-item"
        clearable
        v-bind="headerTop('light_chain', '轻链')"
        @keyup.enter="handleFilter"
        @clear="handleFilter"
      />
      <ElInput
        v-model="listQuery.order_code"
        class="filter-item"
        clearable
        placeholder="使用工单"
        title="多个工单号用逗号、空格或换行分隔，按完整编号查找；只填一个时按包含查找"
        @keyup.enter="handleFilter"
        @clear="handleFilter"
      />
      <div class="filter-actions list-filter-actions">
        <WorkbenchHeaderFilterChip v-bind="headerChipBind" />
        <ElButton type="primary" :icon="Search" title="右键清空筛选" @click="handleFilter" @contextmenu.prevent="reset">查询</ElButton>
        <ElButton :icon="Refresh" @click="reset">重置</ElButton>
      </div>
    </div>

    <ElCard shadow="never" class="list-table-card">
      <div ref="listTableBody" class="list-table-body">
      <WorkbenchSheet :cell-config="cellConfig" :keyboard-config="keyboardConfig" empty-text="没有蛋白">
        <template #columns>
          <VxeColumn
            v-for="column in sheetColumns"
            :key="column.key"
            :field="column.key"
            :title="column.label"
            :min-width="column.minWidth"
            :width="sheetColumnWidth(column)"
            :align="column.align"
          >
            <template #header>
              <WorkbenchHeaderLabel v-if="headerMenuStates[column.key]" :label="column.label" v-bind="headerMenuStates[column.key]" />
              <template v-else>{{ column.label }}</template>
            </template>
            <template #default="{ row }">{{ sheetDirectTextValue(row, column.key) || '—' }}</template>
          </VxeColumn>
        </template>
      </WorkbenchSheet>
      </div>

      <ElPagination
        v-show="total > 0"
        v-model:current-page="listQuery.page"
        v-model:page-size="listQuery.limit"
        :total="total"
        :page-sizes="[20, 50, 100, 200, 500]"
        layout="total, sizes, prev, pager, next, jumper"
        class="list-pagination"
        @size-change="handleFilter"
        @current-change="load"
      />
    </ElCard>
    <WorkbenchHeaderMenu v-bind="headerMenuBind" />
  </div>
</template>

<script>
import { Back, Download, Refresh, Search } from '@element-plus/icons-vue'
import { ElButton, ElCard, ElInput, ElPagination } from 'element-plus'
import { VxeColumn } from 'vxe-table'

import { notifyApiError } from '#/api/errors'
import {
  exportTransfectionProteins,
  fetchTransfectionProteinColumnValues,
  fetchTransfectionProteins,
} from '#/api/molecularTransfection'
import {
  createColumnOrder,
  SHEET_ROW_NO_COLUMN,
  sheetSelectionMixin,
  WorkbenchHeaderFilterChip,
  WorkbenchHeaderLabel,
  WorkbenchHeaderMenu,
  workbenchHeaderMenuMixin,
  WorkbenchSheet,
} from '#/components/workbench'
import { downloadListExcel, excelTimestamp } from '#/utils/downloadExcel'
import { listPageMixin } from '#/utils/listPage'
import { listTableLockMixin } from '#/utils/listTableLock'

const COLUMNS = Object.freeze([
  SHEET_ROW_NO_COLUMN,
  { key: 'protein_name', label: '蛋白名称', minWidth: 160 },
  { key: 'heavy_chain', label: '重链', minWidth: 150 },
  { key: 'light_chain', label: '轻链', minWidth: 150 },
  { key: 'target_name', label: '靶点', minWidth: 140 },
  { key: 'target_codes', label: '靶点编号', minWidth: 140 },
  { key: 'mouse_strain', label: '小鼠品系', minWidth: 110 },
  { key: 'source_order', label: '登记工单', minWidth: 170 },
  { key: 'orders', label: '使用工单', minWidth: 220 },
  { key: 'created_at', label: '登记时间', minWidth: 160 },
])
const SHEET_COLUMN_ORDER = createColumnOrder('transfectionProteinSheetColumnOrder', COLUMNS, {
  pinFirstKey: SHEET_ROW_NO_COLUMN.key,
})

const HEADER_COLUMNS = Object.freeze({
  protein_name: { type: 'text', label: '蛋白名称', values: 'recent', top: { query: 'protein_name', kind: 'contains' } },
  heavy_chain: { type: 'text', label: '重链', values: 'recent', top: { query: 'heavy_chain', kind: 'contains' } },
  light_chain: { type: 'text', label: '轻链', values: 'recent', top: { query: 'light_chain', kind: 'contains' } },
  target_name: { type: 'text', label: '靶点', values: 'all', search: 'target' },
  mouse_strain: { type: 'csv', label: '小鼠品系', values: 'all' },
})

const SOURCE_TILES = Object.freeze([
  { value: '', statKey: 'total', label: '全部', hint: '当前筛选', tone: 'stat-blue' },
  { value: 'order', statKey: 'order', label: '工单登记', hint: '转染工单导入时首次登记', tone: 'stat-green' },
  { value: 'history', statKey: 'history', label: '历史录入', hint: '历史数据，不能在工单里改', tone: 'stat-gray' },
])

const CELL_CONFIG = Object.freeze({ height: 40 })
// 只读表格不启用 Delete/Enter，避免 vxe 清空单元格或进入编辑。
const KEYBOARD_CONFIG = Object.freeze({
  isArrow: true,
  isShift: true,
  isTab: true,
  isEdit: false,
  isDel: false,
  isEnter: false,
  isClip: false,
})

function emptyQuery() {
  return {
    protein_name: '',
    heavy_chain: '',
    light_chain: '',
    order_code: '',
    source: '',
    sort_field: '',
    sort_dir: '',
    page: 1,
    limit: 20,
  }
}

export default {
  name: 'TransfectionProteins',
  components: {
    ElButton,
    ElCard,
    ElInput,
    ElPagination,
    VxeColumn,
    WorkbenchHeaderFilterChip,
    WorkbenchHeaderLabel,
    WorkbenchHeaderMenu,
    WorkbenchSheet,
  },
  mixins: [listTableLockMixin, listPageMixin, workbenchHeaderMenuMixin, sheetSelectionMixin],
  listFilterKey: 'transfectionProteins',
  workbenchSheet: { order: SHEET_COLUMN_ORDER },
  setup() {
    return { Back, Download, Refresh, Search, cellConfig: CELL_CONFIG, keyboardConfig: KEYBOARD_CONFIG }
  },
  data() {
    return {
      list: [],
      listQuery: emptyQuery(),
      excelRowSelectKey: SHEET_ROW_NO_COLUMN.key,
      sheetPinFirstKey: SHEET_ROW_NO_COLUMN.key,
      total: 0,
      stats: { total: 0, order: 0, history: 0 },
      loading: false,
      exporting: false,
      listLoaded: false,
      consumingOrder: false,
    }
  },
  computed: {
    headerMenuColumns() {
      return HEADER_COLUMNS
    },
    sourceTiles() {
      return SOURCE_TILES
    },
  },
  watch: {
    '$route.query.order_code'() {
      this.consumeOrderQuery()
    },
  },
  created() {
    this.initialLoad()
  },
  async activated() {
    if (!this.listLoaded) return
    if (!await this.consumeOrderQuery() && this.isListDataStale()) this.load()
  },
  methods: {
    async initialLoad() {
      if (!await this.consumeOrderQuery()) await this.load()
      this.listLoaded = true
    },
    sheetDirectTextValue(row, key) {
      if (!row) return ''
      if (key === SHEET_ROW_NO_COLUMN.key) return this.sheetRowNo(row)
      const value = row[key]
      if (Array.isArray(value)) return value.join('、')
      return value == null ? '' : String(value)
    },
    buildQuery() {
      return { ...this.listQuery, field_filters: this.headerFilterPayload() }
    },
    fetchHeaderValues(query) {
      return fetchTransfectionProteinColumnValues(query)
    },
    async load() {
      const isLatest = this.beginListRequest()
      this.loading = true
      try {
        const data = await fetchTransfectionProteins(this.buildQuery())
        if (!isLatest()) return
        this.clearSheetRange()
        this.list = data?.items || []
        this.total = data?.total || 0
        if (data?.page) this.listQuery.page = data.page
        this.stats = { total: 0, order: 0, history: 0, ...data?.stats }
        this.markListFetched()
      } catch (error) {
        if (isLatest()) notifyApiError(error, { messages: { default: '转染表加载失败' } })
      } finally {
        if (isLatest()) this.loading = false
      }
    },
    getList() {
      return this.load()
    },
    reset() {
      this.listQuery = { ...emptyQuery(), limit: this.listQuery.limit }
      this.clearHeaderFilters()
      this.persistListFilters()
      this.load()
    },
    selectSource(value) {
      this.listQuery.source = this.listQuery.source === value ? '' : value
      this.handleFilter()
    },
    /** 从工单详情跳过来时带 ?order_code=系统工单号：只看这个工单用到的蛋白。返回是否已按它重新加载。 */
    async consumeOrderQuery() {
      if (this.$route.name !== 'TransfectionProteins' || this.consumingOrder) return false
      const raw = this.$route.query.order_code
      const code = String(Array.isArray(raw) ? raw[0] : raw || '').trim()
      if (!code) return false
      this.consumingOrder = true
      try {
        const nextQuery = { ...this.$route.query }
        delete nextQuery.order_code
        await this.$router.replace({ path: this.$route.path, query: nextQuery })
        this.listQuery = { ...emptyQuery(), limit: this.listQuery.limit, order_code: code }
        this.clearHeaderFilters()
        this.persistListFilters()
        await this.load()
      } finally {
        this.consumingOrder = false
      }
      return true
    },
    backToOrders() {
      this.$router.push({ name: 'TransfectionList' })
    },
    async handleExport() {
      this.exporting = true
      try {
        await downloadListExcel(() => exportTransfectionProteins(this.buildQuery()), `转染表_${excelTimestamp()}.xlsx`)
      } catch (error) {
        notifyApiError(error, { messages: { default: '导出失败' } })
      } finally {
        this.exporting = false
      }
    },
  },
}
</script>

<style scoped src="#/components/workbench/workbenchPanel.css"></style>
<style scoped>
.protein-page {
  position: relative;
  min-height: 100%;
  padding: var(--list-page-padding);
  background: var(--list-page-bg);
}

.stats-strip {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.filter-item {
  flex: 1 1 120px;
  width: auto;
  min-width: 110px;
}

.filter-keyword {
  flex: 2 1 160px;
}

.filter-actions {
  flex: 0 0 auto;
  margin-left: auto;
}

.sheet-wrap :deep(.vxe-header--column) {
  font-weight: 600;
  background: var(--list-table-header-bg, var(--el-fill-color-light));
}
</style>
