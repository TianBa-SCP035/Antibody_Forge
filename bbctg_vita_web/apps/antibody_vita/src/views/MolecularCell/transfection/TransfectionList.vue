<template>
  <div class="transfection-page" :class="{ 'is-list-table-locked': listTableLocked }">
    <AdvancedOpsBar v-model="showAdvancedOps">
      <template v-if="showAdvancedOps">
        <el-date-picker
          v-model="finishedRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          v-bind="headerTop('finished_on', '完成日起', 'startPlaceholder')"
          end-placeholder="完成日止"
          @change="handleFilter"
        />
        <ListFilterSelect v-model="listQuery.mouse_strain" clearable v-bind="headerTop('mouse_strain', '小鼠品系')" @change="handleFilter">
          <el-option v-for="item in optionLists.mouse_strain" :key="item" :label="item" :value="item" />
        </ListFilterSelect>
        <UserSelect v-model="listQuery.pm" multi-gesture :options="optionLists.pm" v-bind="headerTop('pm', 'PM')" clearable @change="handleFilter" />
        <ListFilterSelect v-model="listQuery.study_type" clearable filterable v-bind="headerTop('study_type', '课题类型')" @change="handleFilter">
          <el-option v-for="item in optionLists.study_type" :key="item" :label="item" :value="item" />
        </ListFilterSelect>
        <el-input
          v-model="listQuery.source_library_order_id"
          clearable
          v-bind="headerTop('source_library_order_id', '来源文库工单')"
          title="多个编号用逗号、空格或换行分隔，按完整编号查找；只填一个时按包含查找"
          @keyup.enter="handleFilter"
          @clear="handleFilter"
        />
        <el-input
          v-model="listQuery.transfection_order_id"
          clearable
          v-bind="headerTop('transfection_order_id', '系统工单号')"
          title="多个编号用逗号、空格或换行分隔，按完整编号查找；只填一个时按包含查找"
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
        <h1 class="page-title">转染与表达</h1>
        <p class="page-subtitle">单细胞孔板交接来的 PCR 转染和自建的质粒转染，导入蛋白清单，完成后交接到合成与验证。</p>
      </div>
      <div class="header-actions">
        <span class="total-count text-secondary">共 {{ total }} 条工单</span>
        <el-button :icon="Tickets" @click="openProteinLibrary">转染表</el-button>
        <el-button
          type="primary"
          :icon="Plus"
          :class="{ 'no-permission-btn': !canEdit }"
          :title="!canEdit ? '您没有权限新建转染工单' : ''"
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
        v-model="listQuery.project_code"
        class="filter-item filter-keyword"
        clearable
        v-bind="headerTop('project_code', '项目编号')"
        title="多个编号用逗号、空格或换行分隔，按完整编号查找；只填一个时按包含查找"
        :prefix-icon="Search"
        @keyup.enter="handleFilter"
        @clear="handleFilter"
      />
      <WorkbenchTargetFilter
        v-model="listQuery.target_name"
        class="filter-item"
        v-bind="headerTop('target_name', '靶点')"
        :search="fetchTransfectionRecordedTargets"
        @change="handleFilter"
      />
      <ListFilterSelect v-model="listQuery.transfection_type" class="filter-item" clearable v-bind="headerTop('transfection_type', '转染类型')" @change="handleFilter">
        <el-option v-for="item in optionLists.transfection_type" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <el-input
        v-model="listQuery.protein_name"
        class="filter-item"
        clearable
        placeholder="蛋白名称"
        title="查找含有该蛋白的工单"
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
      <el-date-picker
        v-model="transfectedRange"
        class="filter-range"
        type="daterange"
        value-format="YYYY-MM-DD"
        range-separator="至"
        v-bind="headerTop('transfected_on', '转染日起', 'startPlaceholder')"
        end-placeholder="转染日止"
        @change="handleFilter"
      />
      <ListFilterSelect v-model="listQuery.priority" class="filter-item" clearable v-bind="headerTop('priority', '优先级')" @change="handleFilter">
        <el-option v-for="item in optionLists.priority" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
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
        pin-first="project_code"
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
        :row-class-name="workbenchRowClassName"
        @header-menu="openHeaderMenu"
        @row-click="onWorkbenchRowClick"
        @row-contextmenu="onWorkbenchRowContextMenu"
      >
        <template #priority="{ row }">
          <WorkbenchPriorityCell
            :value="row.priority"
            :options="optionLists.priority"
            :editable="canEdit"
            @change="(value) => persistRowValue(row, 'priority', value)"
          />
        </template>
        <template #status="{ row }">
          <WorkbenchStatusEditor
            :value="row.status"
            :options="optionLists.status"
            :type="statusTone(row.status)"
            :editable="canEditField(row, 'status')"
            @change="(value) => persistRowValue(row, 'status', value)"
          />
        </template>
        <template #transfected_on="{ row }">
          <WorkbenchInlineDatePicker
            v-model="row.transfected_on"
            class="inline-date"
            :disabled="!canEditField(row, 'transfected_on')"
            @change="persistRow(row, 'transfected_on')"
          />
        </template>
        <template #finished_on="{ row }">
          <WorkbenchInlineDatePicker
            v-model="row.finished_on"
            class="inline-date"
            :disabled="!canEditField(row, 'finished_on')"
            @change="persistRow(row, 'finished_on')"
          />
        </template>
        <template #actions="{ row }">
          <TransfectionRowActions
            :row="row"
            :can-edit="canEdit"
            @proteins="openOrderProteins"
            @handoff="handleHandoff"
            @delete="handleDelete"
          />
        </template>
      </WorkbenchDataTable>

      <WorkbenchSheet v-else>
        <template #actions="{ row }">
          <div @mousedown.stop @click.stop>
            <TransfectionRowActions
              :row="row"
              :can-edit="canEdit"
              @proteins="openOrderProteins"
              @handoff="handleHandoff"
              @delete="handleDelete"
            />
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
      label-width="92px"
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
          <span v-for="fact in drawerHeaderFacts" :key="fact.key" :class="{ 'is-type': fact.key === 'type' }">
            {{ fact.text }}
          </span>
        </div>
      </template>
      <template #actions>
        <TransfectionRowActions
          :row="editingRow"
          :can-edit="canEdit"
          @proteins="openOrderProteins"
          @handoff="handleHandoff"
          @delete="handleDelete"
        />
      </template>
      <template #field="{ field }">
        <WorkbenchLineInput
          v-if="field.type === 'plate-list'"
          :model-value="plateDraft"
          placeholder="一行一个板号"
          :disabled="!canEdit"
          @update:model-value="onPlateDraftInput"
          @blur="persistRow(editingRow, 'plate_nos')"
        />
        <WorkbenchDrawerField v-else v-bind="drawerFieldBind(field)" />
      </template>
      <template #after-fields>
        <TransfectionPcrRows
          v-if="editingRow.transfection_type === TYPE_PCR"
          :order-id="editingRow.id"
          :rows="editingRow.pcr_rows"
          :can-edit="canEdit"
          @change="onPcrRowsChange"
        />
        <TransfectionProteinPanel
          :order-id="editingRow.id"
          :order-code="editingRow.transfection_order_id"
          :can-edit="canEdit"
          :lock-reason="proteinLockReason"
          @changed="onProteinsChanged"
        />
      </template>
    </WorkbenchDrawer>

    <el-dialog v-model="createVisible" title="新建转染工单" width="460px" append-to-body>
      <el-radio-group v-model="createType" class="create-types">
        <el-radio v-for="type in optionLists.transfection_type" :key="type" :value="type" border>
          <span class="create-type-label">{{ type }}</span>
          <small class="create-type-hint">{{ typeHints[type] }}</small>
        </el-radio>
      </el-radio-group>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!createType" :loading="creating" @click="confirmCreate">创建</el-button>
      </template>
    </el-dialog>
    <WorkbenchHeaderMenu v-bind="headerMenuBind" />
  </div>
</template>

<script>
import { Download, Plus, Search, Tickets, Tools } from '@element-plus/icons-vue'
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
  ElRadio,
  ElRadioGroup,
} from 'element-plus'
import { useUserStore } from '@vben/stores'

import {
  batchSaveTransfectionOrders,
  deleteTransfectionOrder,
  exportTransfectionList,
  fetchTransfectionColumnValues,
  fetchTransfectionList,
  fetchTransfectionOptions,
  fetchTransfectionRecordedTargets,
  handoffTransfectionToSynthesis,
  saveTransfectionOrder,
  TRANSFECTION_EDIT,
} from '#/api/molecularTransfection'
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
  WorkbenchLineInput,
  WorkbenchPriorityCell,
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
import { plateNumbersFromText, plateNumbersText } from '../library/libraryColumns'
import TransfectionPcrRows from './TransfectionPcrRows.vue'
import TransfectionProteinPanel from './TransfectionProteinPanel.vue'
import TransfectionRowActions from './TransfectionRowActions.vue'
import {
  FIELDS,
  HANDOFF_LOCKED_KEYS,
  HEADER_MENU_COLUMNS,
  ORDER_EDITOR_SECTIONS,
  SHEET_COLUMN_ORDER,
  SHEET_COLUMNS,
  STATUS_DONE,
  STATUS_OPTIONS,
  statusTone,
  TRANSFECTION_VIEW_PREFS_KEY,
  TYPE_HINTS,
  TYPE_PCR,
  TYPE_PLASMID,
  WORKBENCH_COLUMNS,
} from './transfectionColumns'

function emptyQuery() {
  return {
    page: 1,
    limit: 20,
    transfection_order_id: '',
    transfection_type: '',
    source_library_order_id: '',
    project_code: '',
    target_name: '',
    study_type: '',
    status: '',
    priority: '',
    pm: '',
    owner: '',
    mouse_strain: '',
    protein_name: '',
    remark: '',
    transfected_on_start: '',
    transfected_on_end: '',
    finished_on_start: '',
    finished_on_end: '',
    sort_field: '',
    sort_dir: '',
  }
}

const STATUS_TILES = [
  { status: '待转染', hint: '还没开始转染', tone: 'stat-blue' },
  { status: '转染中', hint: '已填转染日期', tone: 'stat-orange' },
  { status: '已完成', hint: '可交接到合成与验证', tone: 'stat-green' },
  { status: '已取消', hint: '不再进行', tone: 'stat-gray' },
]
const READONLY_KEYS = new Set(['transfection_order_id', 'source_library_order_id', 'protein_count', 'synthesis_order_id'])
const DERIVED_FIELDS = ['status', 'transfected_on', 'finished_on']
const PEOPLE_FIELDS = ['pm', 'owner']
const OPTION_SOURCES = {
  types: 'transfection_type',
  statuses: 'status',
  priorities: 'priority',
  mouse_strains: 'mouse_strain',
}
const ADVANCED_FILTER_KEYS = ['mouse_strain', 'pm', 'study_type', 'source_library_order_id', 'transfection_order_id', 'remark']

export default {
  name: 'TransfectionList',
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
    ElRadio,
    ElRadioGroup,
    ListFilterSelect,
    Tools,
    TransfectionPcrRows,
    TransfectionProteinPanel,
    TransfectionRowActions,
    UserSelect,
    WorkbenchDataTable,
    WorkbenchDrawer,
    WorkbenchDrawerField,
    WorkbenchHeaderFilterChip,
    WorkbenchHeaderMenu,
    WorkbenchInlineDatePicker,
    WorkbenchLineInput,
    WorkbenchPriorityCell,
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
  listFilterKey: 'transfectionList',
  workbenchFields: FIELDS,
  workbenchApi: {
    list: fetchTransfectionList,
    save: saveTransfectionOrder,
    saveBatch: batchSaveTransfectionOrders,
    remove: deleteTransfectionOrder,
    export: exportTransfectionList,
    exportName: '转染与表达',
    columnValues: fetchTransfectionColumnValues,
    errors: { load: { default: '加载转染工单失败' } },
  },
  workbenchSheet: { columns: SHEET_COLUMNS, order: SHEET_COLUMN_ORDER },
  setup() {
    return { Download, fetchTransfectionRecordedTargets, Plus, Search, Tickets, TYPE_PCR, typeHints: TYPE_HINTS }
  },
  data() {
    return {
      viewPrefsStorageKey: TRANSFECTION_VIEW_PREFS_KEY,
      optionLists: { ...fieldOptionLists(FIELDS), pm: [], owner: [] },
      excelRowSelectKey: 'id',
      showAdvancedOps: false,
      loading: false,
      list: [],
      total: 0,
      stats: Object.fromEntries(STATUS_OPTIONS.map((status) => [status, 0])),
      listQuery: emptyQuery(),
      headerMenuColumns: HEADER_MENU_COLUMNS,
      transfectedRange: [],
      finishedRange: [],
      plateDraft: '',
      createVisible: false,
      createType: TYPE_PLASMID,
      creating: false,
      listLoaded: false,
      consumingFocus: false,
    }
  },
  computed: {
    canEdit() {
      return hasAccessCode(useUserStore().userInfo, TRANSFECTION_EDIT)
    },
    statusTiles() {
      return STATUS_TILES
    },
    workbenchColumns() {
      return WORKBENCH_COLUMNS
    },
    editorSections() {
      return ORDER_EDITOR_SECTIONS
    },
    hasAdvancedFilters() {
      return ADVANCED_FILTER_KEYS.some((key) => String(this.listQuery[key] || '').trim())
        || Boolean(this.finishedRange?.length)
    },
    drawerTitle() {
      return this.editingRow?.transfection_order_id || '转染工单'
    },
    drawerHeaderFacts() {
      const row = this.editingRow
      if (!row) return []
      const targetText = [row.target_name, uniqueTargetCodes(row.target_codes).join('、')].filter(Boolean).join(' · ')
      return [
        { key: 'type', text: row.transfection_type },
        { key: 'target', text: targetText || '靶点待关联' },
        ...(row.synthesis_order_id ? [{ key: 'synthesis', text: `已交接 ${row.synthesis_order_id}` }] : []),
      ]
    },
    proteinLockReason() {
      const id = this.editingRow?.synthesis_order_id
      return id ? `已交接到合成与验证 ${id}，蛋白清单不能再改` : ''
    },
  },
  watch: {
    '$route.query.order'() {
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
      return !this.handoffLockReason(row, key)
    },
    sheetCellLockReason(row, key) {
      if (!this.canEdit) return '你没有编辑权限'
      const handedOff = this.handoffLockReason(row, key)
      if (handedOff) return handedOff
      if (key === 'plate_nos' && Array.isArray(row?.plate_nos) && row.plate_nos.length > 1) {
        return '单元格只能写一行，多个板号请在详情里修改'
      }
      return this.sheetReadonlyLockReason(key)
    },
    drawerFieldValue(field, row) {
      if (field.key === 'source_library_order_id') return row?.source_library_order_id || '自建'
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
      this.transfectedRange = []
      this.finishedRange = []
      this.clearHeaderFilters()
      this.persistListFilters()
      this.getList()
    },
    listFilterExtras() {
      return { transfectedRange: this.transfectedRange, finishedRange: this.finishedRange }
    },
    restoreListFilterExtras(state) {
      if (Array.isArray(state.transfectedRange)) this.transfectedRange = state.transfectedRange
      if (Array.isArray(state.finishedRange)) this.finishedRange = state.finishedRange
    },
    buildQuery() {
      const [transfectedStart, transfectedEnd] = this.transfectedRange || []
      const [finishedStart, finishedEnd] = this.finishedRange || []
      const payload = {
        ...this.listQuery,
        transfected_on_start: transfectedStart || '',
        transfected_on_end: transfectedEnd || '',
        finished_on_start: finishedStart || '',
        finished_on_end: finishedEnd || '',
      }
      const fieldFilters = this.headerFilterPayload()
      if (fieldFilters.length) payload.field_filters = fieldFilters
      return payload
    },
    async loadOptionLists() {
      try {
        const data = await fetchTransfectionOptions()
        const people = uniqueNames(data?.people || [])
        PEOPLE_FIELDS.forEach((key) => { this.optionLists[key] = people })
        applyOptionLists(this.optionLists, data, OPTION_SOURCES)
      } catch (error) {
        notifyApiError(error, { messages: { default: '加载转染选项失败，暂用本地默认选项' } })
      }
    },
    onDrawerRowSynced(row) {
      this.plateDraft = plateNumbersText(row?.plate_nos)
    },
    onPcrRowsChange(rows) {
      if (!this.editingRow) return
      this.editingRow.pcr_rows = rows
      this.persistRow(this.editingRow, 'pcr_rows')
    },
    onPlateDraftInput(value) {
      if (!this.editingRow) return
      this.plateDraft = value
      this.editingRow.plate_nos = plateNumbersFromText(value)
    },
    async saveRowField(row, field, { force = false } = {}) {
      if (!this.canEdit || !row?.id) return
      if (!this.normalizeDrawerValue(row, field)) return
      const fields = this.drawerValueKeys(field)
      if (!force && this.rowFieldsUnchanged(row, fields)) return
      return this.submitRowFields(row, fields)
    },
    savedFieldKeys(fields) {
      const targets = fields.some((key) => key === 'target_codes' || key === 'target_name') ? ['target_codes', 'target_name'] : []
      return new Set([...fields, ...targets, ...DERIVED_FIELDS])
    },
    deleteBlockReason(row) {
      if (!this.canEdit) return '您没有删除权限'
      return row.synthesis_order_id ? `已交接到合成与验证 ${row.synthesis_order_id}，不能删除` : ''
    },
    deleteConfirmText(row) {
      return `确认删除 ${row.transfection_order_id}？本单登记、且别的工单没用到的蛋白会一并从转染表删除，无法恢复。`
    },
    handleCreate() {
      if (!this.canEdit) {
        ElMessage.warning('您没有权限新建转染工单')
        return
      }
      this.createType = TYPE_PLASMID
      this.createVisible = true
    },
    async confirmCreate() {
      if (this.creating || !this.createType) return
      this.creating = true
      try {
        const saved = await saveTransfectionOrder({ transfection_type: this.createType })
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
        ElMessage.warning('您没有权限交接转染工单')
        return
      }
      if (row.status !== STATUS_DONE) {
        ElMessage.warning('只有已完成的转染工单可以交接到合成与验证')
        return
      }
      if (!row.protein_count) {
        ElMessage.warning('请先在详情里导入转染蛋白')
        return
      }
      try {
        await ElMessageBox.confirm(
          `把 ${row.transfection_order_id} 交接到合成与验证？会新建一条内部转染的合成单（${row.protein_count} 个蛋白），直接进入待检测；交接后不能再改转染类型、状态、日期和蛋白清单。`,
          '交接确认',
          { type: 'warning', confirmButtonText: '交接' },
        )
      } catch {
        return
      }
      if (!await this.flushEditorForAction(row)) return
      try {
        const result = await handoffTransfectionToSynthesis(row.id)
        this.applySavedFields(result.order, ['synthesis_order_id'])
        ElMessage.success(`已交接为合成与验证单 ${result.synthesis_order_id}`)
      } catch (error) {
        notifyApiError(error, { messages: { default: '交接失败' } })
        await this.getList({ flushEditor: false, silent: true })
      }
    },
    onProteinsChanged(order) {
      this.applySavedFields(order, ['protein_count'])
    },
    openProteinLibrary() {
      this.$router.push({ name: 'TransfectionProteins' })
    },
    openOrderProteins(row) {
      this.$router.push({ name: 'TransfectionProteins', query: { order_code: row.transfection_order_id } })
    },
    /** 文库构建交接后跳过来时带 ?order=系统工单号：只按这个工单号筛选并打开它。返回是否已按它重新加载。 */
    async consumeFocusQuery() {
      if (this.$route.name !== 'TransfectionList' || this.consumingFocus) return false
      const raw = this.$route.query.order
      const code = String(Array.isArray(raw) ? raw[0] : raw || '').trim()
      if (!code) return false
      this.consumingFocus = true
      try {
        const nextQuery = { ...this.$route.query }
        delete nextQuery.order
        await this.$router.replace({ path: this.$route.path, query: nextQuery })
        this.listQuery = { ...emptyQuery(), limit: this.listQuery.limit, transfection_order_id: code }
        this.showAdvancedOps = true
        this.transfectedRange = []
        this.finishedRange = []
        this.clearHeaderFilters()
        this.persistListFilters()
        if (await this.getList()) {
          const row = this.list.find((item) => item.transfection_order_id === code)
          if (row && !this.isExcelMode) this.openDrawer(row)
        }
      } finally {
        this.consumingFocus = false
      }
      return true
    },
    sheetCellValue(row, key) {
      return key === 'plate_nos' ? plateNumbersText(row.plate_nos) : row[key]
    },
    sheetFormatter(column) {
      return column.key === 'plate_nos' ? this.formatSheetCellValue : this.sheetTypeFormatter(column)
    },
    coerceSheetValue(key, text, row) {
      if (key === 'plate_nos') {
        return { ok: true, value: plateNumbersFromText(Array.isArray(text) ? text.join('\n') : text) }
      }
      return this.coerceSheetField(key, text, row)
    },
    sheetPasteIdentityKey() {
      return 'transfection_order_id'
    },
  },
}
</script>

<style scoped src="#/components/workbench/workbenchPanel.css"></style>
<style src="#/components/workbench/workbenchDrawer.css"></style>
<style scoped>
.transfection-page {
  position: relative;
  min-height: 100%;
  padding: var(--list-page-padding);
  background: var(--list-page-bg);
}

.stats-strip {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.filter-item {
  flex: 1 1 100px;
  min-width: 100px;
}

.filter-keyword {
  flex: 2 1 150px;
}

.filter-strip :deep(.filter-range) {
  flex: 1 1 200px;
  width: auto;
  min-width: 100px;
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

.table-card :deep(.date-column-cell .cell) {
  padding: 4px 10px;
  overflow: hidden;
}

.inline-date {
  --el-date-editor-width: 100%;

  width: 100%;
  max-width: 100%;
}

.drawer-header-facts {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 10px;
  align-items: center;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 20px;
}

.drawer-header-facts span {
  white-space: nowrap;
}

.drawer-header-facts .is-type {
  padding: 0 7px;
  color: #4e5969;
  font-weight: 500;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-light);
  border-radius: 5px;
}

.create-types {
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: stretch;
}

.create-types :deep(.el-radio) {
  height: auto;
  margin-right: 0;
  padding: 10px 14px;
}

.create-types :deep(.el-radio__label) {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.create-type-label {
  font-weight: 600;
}

.create-type-hint {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  font-weight: 400;
  white-space: normal;
}

html.dark .drawer-header-facts .is-type {
  color: var(--el-text-color-regular);
}
</style>
