<template>
  <div class="ngs-page" :class="{ 'is-list-table-locked': listTableLocked }">
    <AdvancedOpsBar v-model="showAdvancedOps">
      <template v-if="showAdvancedOps">
        <el-date-picker
          v-model="sequencingRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          v-bind="headerTop('sequencing_date', '上机日起', 'startPlaceholder')"
          end-placeholder="上机日止"
          @change="handleFilter"
        />
        <ListFilterSelect v-model="listQuery.project_level" clearable v-bind="headerTop('project_level', '项目级别')" @change="handleFilter">
          <el-option v-for="item in optionLists.project_level" :key="item" :label="item" :value="item" />
        </ListFilterSelect>
        <ListFilterSelect v-model="listQuery.mouse_strain" clearable v-bind="headerTop('mouse_strain', '小鼠品系')" @change="handleFilter">
          <el-option v-for="item in optionLists.mouse_strain" :key="item" :label="item" :value="item" />
        </ListFilterSelect>
        <UserSelect v-model="listQuery.pm" multi-gesture :options="optionLists.pm" v-bind="headerTop('pm', 'PM')" clearable @change="handleFilter" />
        <el-input
          v-model="listQuery.source_library_order_id"
          clearable
          v-bind="headerTop('source_library_order_id', '来源文库工单')"
          @keyup.enter="handleFilter"
          @clear="handleFilter"
        />
        <el-input
          v-model="listQuery.ngs_run_id"
          clearable
          v-bind="headerTop('ngs_run_id', '测序单号')"
          @keyup.enter="handleFilter"
          @clear="handleFilter"
        />
        <el-input v-model="listQuery.remark" clearable v-bind="headerTop('remark', '备注')" @keyup.enter="handleFilter" @clear="handleFilter" />
      </template>
      <template #actions>
        <el-button v-if="!isExcelMode" @click="openColumnPicker">显示字段</el-button>
        <el-button type="warning" :icon="Download" @click="handleListExport">列表导出</el-button>
      </template>
    </AdvancedOpsBar>

    <div class="page-header-band">
      <div class="title-group">
        <h1 class="page-title">NGS测序</h1>
        <p class="page-subtitle">文库构建之后的测序上机。填好送合成转码后，交到合成与验证。</p>
      </div>
      <div class="header-actions">
        <span class="total-count text-secondary">共 {{ total }} 条</span>
        <el-button
          type="primary"
          :icon="Plus"
          :class="{ 'no-permission-btn': !canEdit }"
          :title="!canEdit ? '您没有权限新建测序单' : ''"
          @click="handleCreate"
        >
          新建
        </el-button>
      </div>
    </div>

    <section class="workbench-panel">
      <div class="stats-strip">
        <div
          v-for="item in statusTiles"
          :key="item.status"
          class="stat-tile stat-tile-interactive"
          :class="[item.tone, { 'stat-tile-active': listQuery.status === item.status }]"
          @click="selectStatus(item.status)"
        >
          <span class="stat-copy">
            <span class="stat-label">{{ item.status }}</span>
            <small class="text-hint">{{ item.hint }}</small>
          </span>
          <strong class="stat-value">{{ stats[item.status] || 0 }}</strong>
        </div>
      </div>
    </section>

    <div class="filter-strip list-filter-controls">
      <el-input
        v-model="listQuery.library_code"
        class="filter-item filter-keyword"
        clearable
        v-bind="headerTop('library_code', '建库编号')"
        :prefix-icon="Search"
        @keyup.enter="handleFilter"
        @clear="handleFilter"
      />
      <WorkbenchTargetFilter
        v-model="listQuery.target_name"
        class="filter-item"
        v-bind="headerTop('target_name', '靶点')"
        :search="fetchNgsRecordedTargets"
        @change="handleFilter"
      />
      <ListFilterSelect v-model="listQuery.sample_library" class="filter-item" clearable v-bind="headerTop('sample_library', '样品库')" @change="handleFilter">
        <el-option v-for="item in optionLists.sample_library" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <el-input
        v-model="listQuery.synthesis_code"
        class="filter-item"
        clearable
        v-bind="headerTop('synthesis_code', '送合成转码')"
        @keyup.enter="handleFilter"
        @clear="handleFilter"
      />
      <el-input
        v-model="listQuery.instrument_no"
        class="filter-item"
        clearable
        v-bind="headerTop('instrument_no', '仪器号')"
        @keyup.enter="handleFilter"
        @clear="handleFilter"
      />
      <UserSelect
        v-model="listQuery.owner"
        class="filter-item"
        multi-gesture
        :options="optionLists.owner"
        v-bind="headerTop('owner', '负责人')"
        clearable
        @change="handleFilter"
      />
      <div class="filter-actions list-filter-actions">
        <WorkbenchHeaderFilterChip v-bind="headerChipBind" />
        <button
          type="button"
          class="list-advanced-trigger"
          :class="{ 'is-active': showAdvancedOps || hasAdvancedFilters }"
          :title="hasAdvancedFilters ? '高级筛选已启用' : '高级操作'"
          @click="showAdvancedOps = !showAdvancedOps"
        >
          <el-icon><Tools /></el-icon>
        </button>
        <el-button
          class="list-filter-action-button"
          type="primary"
          :icon="Search"
          title="右键清空筛选"
          @click="handleFilter"
          @contextmenu.prevent="resetFilters"
        >查询</el-button>
        <WorkbenchViewToggle
          :model-value="viewMode"
          @toggle="toggleViewMode"
          @reset-columns="resetSheetColumnOrder"
        />
      </div>
    </div>

    <el-card shadow="never" class="table-card list-table-card">
      <div ref="listTableBody" class="list-table-body">
        <WorkbenchDataTable
          v-if="viewMode === 'workbench'"
          ref="workbenchTable"
          v-loading="loading"
          :height="listTableHeight"
          :storage-key="viewPrefsStorageKey"
          pin-first="library_code"
          :columns="workbenchColumns"
          :data="list"
          border
          stripe
          fit
          highlight-current-row
          size="large"
          class="list-data-table"
          style="width: 100%"
          row-key="id"
          :header-menu-states="headerMenuStates"
          @header-menu="openHeaderMenu"
          @row-click="onWorkbenchRowClick"
          @row-contextmenu="onWorkbenchRowContextMenu"
        >
          <template #status="{ row }">
            <WorkbenchStatusEditor
              :value="row.status"
              :options="optionLists.status"
              :type="statusTone(row.status)"
              :editable="canEditField(row, 'status')"
              @change="(value) => persistRowValue(row, 'status', value)"
            />
          </template>
          <template #sequencing_date="{ row }">
            <WorkbenchInlineDatePicker
              v-model="row.sequencing_date"
              class="inline-date"
              :disabled="!canEditField(row, 'sequencing_date')"
              @change="persistRow(row, 'sequencing_date')"
            />
          </template>
          <template #actions="{ row }">
            <NgsRowActions :row="row" :can-edit="canEdit" @handoff="handleHandoff" @delete="handleDelete" />
          </template>
        </WorkbenchDataTable>

        <WorkbenchSheet v-else>
          <template #actions="{ row }">
            <div @mousedown.stop @click.stop>
              <NgsRowActions :row="row" :can-edit="canEdit" @handoff="handleHandoff" @delete="handleDelete" />
            </div>
          </template>
        </WorkbenchSheet>
      </div>

      <el-pagination
        v-show="total > 0"
        v-model:current-page="listQuery.page"
        v-model:page-size="listQuery.limit"
        :total="total"
        :page-sizes="[20, 50, 100, 200, 500]"
        layout="total, sizes, prev, pager, next, jumper"
        class="list-pagination"
        @size-change="handleFilter"
        @current-change="getList"
      />
    </el-card>

    <WorkbenchDrawer
      v-model="drawerVisible"
      size="560px"
      label-width="108px"
      title-mark
      :title="drawerTitle"
      :row="editingRow"
      :sections="editorSections"
      :disabled="!canEdit"
      :has-prev="hasPrevEditor"
      :has-next="hasNextEditor"
      @shift="shiftEditor"
    >
      <template #meta>
        <div v-if="drawerHeaderFacts.length" class="drawer-header-facts">
          <span v-for="fact in drawerHeaderFacts" :key="fact.key" :class="{ 'is-type': fact.key === 'library' }">
            {{ fact.text }}
          </span>
        </div>
      </template>
      <template #actions>
        <NgsRowActions :row="editingRow" :can-edit="canEdit" @handoff="handleHandoff" @delete="handleDelete" />
      </template>
      <template #field="{ field }">
        <WorkbenchDrawerField v-bind="drawerFieldBind(field)" />
      </template>
    </WorkbenchDrawer>

    <el-dialog v-model="createVisible" title="新建测序单" width="420px" append-to-body>
      <ListFilterSelect v-model="createLibrary" placeholder="样品库" style="width: 100%">
        <el-option v-for="item in optionLists.sample_library" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!createLibrary" :loading="creating" @click="confirmCreate">创建</el-button>
      </template>
    </el-dialog>
    <WorkbenchHeaderMenu v-bind="headerMenuBind" />
  </div>
</template>

<script>
import { Download, Plus, Search, Tools } from '@element-plus/icons-vue'
import {
  ElButton,
  ElCard,
  ElDatePicker,
  ElDialog,
  ElIcon,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElPagination,
} from 'element-plus'
import { useUserStore } from '@vben/stores'

import {
  batchSaveNgsRuns,
  deleteNgsRun,
  exportNgsList,
  fetchNgsColumnValues,
  fetchNgsList,
  fetchNgsOptions,
  fetchNgsRecordedTargets,
  handoffNgsToSynthesis,
  NGS_EDIT,
  saveNgsRun,
} from '#/api/discoveryNgs'
import { notifyApiError } from '#/api/errors'
import AdvancedOpsBar from '#/components/AdvancedOpsBar.vue'
import ListFilterSelect from '#/components/ListFilterSelect.vue'
import UserSelect from '#/components/UserSelect.vue'
import {
  fieldOptionLists,
  uniqueTargetCodes,
  WorkbenchDataTable,
  WorkbenchDrawer,
  WorkbenchDrawerField,
  WorkbenchHeaderFilterChip,
  WorkbenchHeaderMenu,
  WorkbenchInlineDatePicker,
  WorkbenchSheet,
  WorkbenchStatusEditor,
  WorkbenchTargetFilter,
  WorkbenchViewToggle,
  workbenchCrudMixin,
  workbenchDrawerMixin,
  workbenchExcelMixin,
  workbenchHeaderMenuMixin,
  workbenchTargetMixin,
} from '#/components/workbench'
import { hasAccessCode } from '#/utils/accessCode'
import { listPageMixin } from '#/utils/listPage'
import { listTableLockMixin } from '#/utils/listTableLock'
import { applyOptionLists } from '#/utils/optionLists'
import { uniqueNames } from '#/utils/userOptions'
import NgsRowActions from './NgsRowActions.vue'
import {
  EDITOR_SECTIONS,
  FIELDS,
  HANDOFF_LOCKED_KEYS,
  HEADER_MENU_COLUMNS,
  NGS_VIEW_PREFS_KEY,
  SAMPLE_LIBRARIES,
  SHEET_COLUMN_ORDER,
  SHEET_COLUMNS,
  STATUS_OPTIONS,
  statusTone,
  WORKBENCH_COLUMNS,
} from './ngsColumns'

function emptyQuery() {
  return {
    page: 1,
    limit: 20,
    ngs_run_id: '',
    sample_library: '',
    library_code: '',
    synthesis_code: '',
    source_library_order_id: '',
    project_code: '',
    project_level: '',
    target_name: '',
    study_type: '',
    status: '',
    pm: '',
    owner: '',
    mouse_strain: '',
    instrument_no: '',
    remark: '',
    sequencing_date_start: '',
    sequencing_date_end: '',
    sort_field: '',
    sort_dir: '',
  }
}

const STATUS_TILES = [
  { status: '待上机', hint: '还没填上机日期', tone: 'stat-blue' },
  { status: '已上机', hint: '测序进行中', tone: 'stat-orange' },
  { status: '已送合成', hint: '已交到合成与验证', tone: 'stat-green' },
  { status: '已完成', hint: '本轮结束', tone: 'stat-green' },
  { status: '已取消', hint: '不再进行', tone: 'stat-gray' },
]
const READONLY_KEYS = new Set(['ngs_run_id', 'source_library_order_id', 'synthesis_order_id'])
const PEOPLE_FIELDS = ['pm', 'owner']
const OPTION_SOURCES = {
  sample_libraries: 'sample_library',
  project_levels: 'project_level',
  statuses: 'status',
  mouse_strains: 'mouse_strain',
}
const ADVANCED_FILTER_KEYS = [
  'project_level',
  'mouse_strain',
  'pm',
  'source_library_order_id',
  'ngs_run_id',
  'remark',
]

export default {
  name: 'NgsList',
  components: {
    AdvancedOpsBar,
    ElButton,
    ElCard,
    ElDatePicker,
    ElDialog,
    ElIcon,
    ElInput,
    ElOption,
    ElPagination,
    ListFilterSelect,
    NgsRowActions,
    Tools,
    UserSelect,
    WorkbenchDataTable,
    WorkbenchDrawer,
    WorkbenchDrawerField,
    WorkbenchHeaderFilterChip,
    WorkbenchHeaderMenu,
    WorkbenchInlineDatePicker,
    WorkbenchSheet,
    WorkbenchStatusEditor,
    WorkbenchTargetFilter,
    WorkbenchViewToggle,
  },
  mixins: [
    workbenchExcelMixin,
    workbenchDrawerMixin,
    workbenchCrudMixin,
    workbenchTargetMixin,
    listPageMixin,
    workbenchHeaderMenuMixin,
    listTableLockMixin,
  ],
  listFilterKey: 'ngsList',
  workbenchFields: FIELDS,
  workbenchApi: {
    list: fetchNgsList,
    save: saveNgsRun,
    saveBatch: batchSaveNgsRuns,
    remove: deleteNgsRun,
    export: exportNgsList,
    exportName: 'NGS测序',
    columnValues: fetchNgsColumnValues,
    errors: { load: { default: '加载测序单失败' } },
  },
  workbenchSheet: { columns: SHEET_COLUMNS, order: SHEET_COLUMN_ORDER },
  setup() {
    return { Download, fetchNgsRecordedTargets, Plus, Search }
  },
  data() {
    return {
      viewPrefsStorageKey: NGS_VIEW_PREFS_KEY,
      optionLists: { ...fieldOptionLists(FIELDS), pm: [], owner: [] },
      excelRowSelectKey: 'id',
      showAdvancedOps: false,
      loading: false,
      list: [],
      total: 0,
      stats: Object.fromEntries(STATUS_OPTIONS.map((status) => [status, 0])),
      listQuery: emptyQuery(),
      headerMenuColumns: HEADER_MENU_COLUMNS,
      sequencingRange: [],
      createVisible: false,
      createLibrary: SAMPLE_LIBRARIES[0],
      creating: false,
      listLoaded: false,
      consumingFocus: false,
    }
  },
  computed: {
    canEdit() {
      return hasAccessCode(useUserStore().userInfo, NGS_EDIT)
    },
    statusTiles() {
      return STATUS_TILES
    },
    workbenchColumns() {
      return WORKBENCH_COLUMNS
    },
    editorSections() {
      return EDITOR_SECTIONS
    },
    hasAdvancedFilters() {
      return ADVANCED_FILTER_KEYS.some((key) => String(this.listQuery[key] || '').trim())
        || Boolean(this.sequencingRange?.length)
    },
    drawerTitle() {
      return this.editingRow?.ngs_run_id || '测序单'
    },
    drawerHeaderFacts() {
      const row = this.editingRow
      if (!row) return []
      const targetText = [row.target_name, uniqueTargetCodes(row.target_codes).join('、')].filter(Boolean).join(' · ')
      return [
        { key: 'library', text: row.sample_library },
        { key: 'target', text: targetText || '靶点待关联' },
        ...(row.synthesis_order_id ? [{ key: 'synthesis', text: `已交接 ${row.synthesis_order_id}` }] : []),
      ]
    },
  },
  watch: {
    '$route.query.run'() {
      this.consumeFocusQuery()
    },
  },
  created() {
    this.loadOptionLists()
    this.initialLoad()
  },
  async activated() {
    if (!this.listLoaded) return
    if (!await this.consumeFocusQuery() && this.isListDataStale()) this.getList({ flushEditor: false })
  },
  methods: {
    statusTone,
    async initialLoad() {
      if (!await this.consumeFocusQuery()) await this.getList({ flushEditor: false })
      this.listLoaded = true
    },
    handoffLockReason(row, key) {
      if (!row?.synthesis_order_id || !HANDOFF_LOCKED_KEYS.includes(key)) return ''
      return `已交接到合成与验证 ${row.synthesis_order_id}，不能再改`
    },
    canEditField(row, key) {
      if (!this.canEdit || READONLY_KEYS.has(key)) return false
      const locked = key === 'target' ? 'target_name' : key
      return !this.handoffLockReason(row, locked)
    },
    sheetCellLockReason(row, key) {
      if (!this.canEdit) return '你没有编辑权限'
      return this.handoffLockReason(row, key) || this.sheetReadonlyLockReason(key)
    },
    drawerFieldValue(field, row) {
      if (field.key === 'source_library_order_id') return row?.source_library_order_id || '自建'
      if (field.key === 'synthesis_order_id') return row?.synthesis_order_id || '未送合成'
      return row?.[field.key]
    },
    async selectStatus(status) {
      if (this.isExcelMode && !await this.flushPendingSheetEdits()) return
      this.listQuery.status = this.listQuery.status === status ? '' : status
      if (this.headerFilters.status) this.dropHeaderFilter('status')
      this.handleFilter()
    },
    resetFilters() {
      this.listQuery = emptyQuery()
      this.sequencingRange = []
      this.clearHeaderFilters()
      this.persistListFilters()
      this.getList()
    },
    listFilterExtras() {
      return { sequencingRange: this.sequencingRange }
    },
    restoreListFilterExtras(state) {
      if (Array.isArray(state.sequencingRange)) this.sequencingRange = state.sequencingRange
    },
    buildQuery() {
      const [start, end] = this.sequencingRange || []
      const payload = {
        ...this.listQuery,
        sequencing_date_start: start || '',
        sequencing_date_end: end || '',
      }
      const fieldFilters = this.headerFilterPayload()
      if (fieldFilters.length) payload.field_filters = fieldFilters
      return payload
    },
    async loadOptionLists() {
      try {
        const data = await fetchNgsOptions()
        const people = uniqueNames(data?.people || [])
        PEOPLE_FIELDS.forEach((key) => { this.optionLists[key] = people })
        applyOptionLists(this.optionLists, data, OPTION_SOURCES)
      } catch (error) {
        notifyApiError(error, { messages: { default: '加载NGS选项失败，暂用本地默认选项' } })
      }
    },
    async saveRowField(row, field, { force = false } = {}) {
      if (!this.canEdit || !row?.id) return
      if (!this.normalizeDrawerValue(row, field)) return
      const fields = this.drawerValueKeys(field)
      if (!force && this.rowFieldsUnchanged(row, fields)) return
      return this.submitRowFields(row, fields)
    },
    savedFieldKeys(fields) {
      const extra = fields.includes('sequencing_date') ? ['status'] : []
      const targets = fields.some((key) => key === 'target_codes' || key === 'target_name')
        ? ['target_codes', 'target_name']
        : []
      return new Set([...fields, ...extra, ...targets])
    },
    handleCreate() {
      if (!this.canEdit) {
        ElMessage.warning('您没有权限新建测序单')
        return
      }
      this.createLibrary = this.optionLists.sample_library[0] || SAMPLE_LIBRARIES[0]
      this.createVisible = true
    },
    async confirmCreate() {
      if (this.creating || !this.createLibrary) return
      this.creating = true
      try {
        const saved = await saveNgsRun({ sample_library: this.createLibrary })
        this.createVisible = false
        this.listQuery.page = 1
        await this.getList({ flushEditor: false })
        if (!this.isExcelMode) this.openDrawer(this.list.find((row) => row.id === saved.id) || saved)
      } catch (error) {
        notifyApiError(error, { messages: { default: '新建失败' } })
      } finally {
        this.creating = false
      }
    },
    async handleHandoff(row) {
      if (row.synthesis_order_id) {
        ElMessage.info(`已交接到合成与验证 ${row.synthesis_order_id}`)
        return
      }
      if (!this.canEdit) {
        ElMessage.warning('您没有权限送合成')
        return
      }
      if (!String(row.synthesis_code || '').trim()) {
        ElMessage.warning('请先填写送合成转码')
        return
      }
      try {
        await ElMessageBox.confirm(
          `把 ${row.ngs_run_id} 送到合成与验证？会按转码 ${row.synthesis_code} 新建一条常规合成、合成到货的工单。送出后靶点、小鼠品系、PM 和转码不能再改。`,
          '送合成',
          { type: 'warning', confirmButtonText: '送合成' },
        )
      } catch {
        return
      }
      if (!await this.flushEditorForAction(row)) return
      try {
        const result = await handoffNgsToSynthesis(row.id)
        this.applySavedFields(result.order, ['synthesis_order_id', 'status'])
        ElMessage.success(`已交接为合成与验证单 ${result.synthesis_order_id}`)
      } catch (error) {
        notifyApiError(error, { messages: { default: '送合成失败' } })
        await this.getList({ flushEditor: false, silent: true })
      }
    },
    deleteBlockReason(row) {
      if (!this.canEdit) return '您没有删除权限'
      return row.synthesis_order_id ? `已交接到合成与验证 ${row.synthesis_order_id}，不能删除` : ''
    },
    deleteConfirmText(row) {
      return `确认删除 ${row.ngs_run_id}？删除后不能恢复。`
    },
    async consumeFocusQuery() {
      if (this.$route.name !== 'DiscoveryNgs' || this.consumingFocus) return false
      const raw = this.$route.query.run
      const code = String(Array.isArray(raw) ? raw[0] : raw || '').trim()
      if (!code) return false
      this.consumingFocus = true
      try {
        const nextQuery = { ...this.$route.query }
        delete nextQuery.run
        await this.$router.replace({ path: this.$route.path, query: nextQuery })
        this.listQuery = { ...emptyQuery(), limit: this.listQuery.limit, ngs_run_id: code }
        this.showAdvancedOps = true
        this.sequencingRange = []
        this.clearHeaderFilters()
        this.persistListFilters()
        if (await this.getList()) {
          const row = this.list.find((item) => item.ngs_run_id === code)
          if (row && !this.isExcelMode) this.openDrawer(row)
        }
      } finally {
        this.consumingFocus = false
      }
      return true
    },
    sheetPasteIdentityKey() {
      return 'ngs_run_id'
    },
  },
}
</script>

<style scoped src="#/components/workbench/workbenchPanel.css"></style>
<style src="#/components/workbench/workbenchDrawer.css"></style>
<style scoped>
.ngs-page {
  position: relative;
  min-height: 100%;
  padding: var(--list-page-padding);
  background: var(--list-page-bg);
}

.stats-strip {
  grid-template-columns: repeat(5, minmax(0, 1fr));
}

.filter-item {
  flex: 1 1 100px;
  min-width: 100px;
}

.filter-keyword {
  flex: 2 1 150px;
}

.filter-actions {
  flex: 0 0 auto;
  margin-left: auto;
}

.table-card :deep(.status-column-cell .cell),
.table-card :deep(.action-column-cell .cell),
.table-card :deep(.date-column-cell .cell) {
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
