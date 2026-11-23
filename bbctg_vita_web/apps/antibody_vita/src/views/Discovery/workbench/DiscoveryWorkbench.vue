<template>
  <div class="app-container" :class="{ 'is-list-table-locked': listTableLocked }">
    <AdvancedOpsBar v-model="showAdvancedOps">
      <ListFilterSelect
        v-model="listQuery.study_type"
        clearable
        v-bind="headerTop('study_type', '课题类型')"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.study_type" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <div class="ops-user-select">
        <UserSelect
          v-model="listQuery.owner"
          multi-gesture
          :options="optionLists.owner"
          v-bind="headerTop('owner', '负责人')"
          clearable
          @change="handleFilter"
        />
      </div>
      <div class="ops-user-select">
        <UserSelect
          v-model="listQuery.immune_owner"
          multi-gesture
          :options="optionLists.immune_owner"
          v-bind="headerTop('immune_owner', '免疫负责人')"
          clearable
          @change="handleFilter"
        />
      </div>
      <div class="ops-user-select">
        <UserSelect
          v-model="listQuery.cell_collector"
          multi-gesture
          :options="optionLists.cell_collector"
          v-bind="headerTop('cell_collector', '细胞收集人')"
          clearable
          @change="handleFilter"
        />
      </div>
      <el-input
        v-model="listQuery.cage_position"
        clearable
        v-bind="headerTop('cage_position', '笼位')"
        @keyup.enter="handleFilter"
        @clear="handleFilter"
      />
      <ListFilterSelect
        v-model="listQuery.mouse_strain"
        clearable
        v-bind="headerTop('mouse_strain', '小鼠品系')"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.mouse_strain" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <el-input
        v-model="listQuery.mouse_nos"
        clearable
        v-bind="headerTop('mouse_nos', '鼠号')"
        @keyup.enter="handleFilter"
        @clear="handleFilter"
      />
      <el-input
        v-model="listQuery.plate_nos"
        clearable
        v-bind="headerTop('plate_nos', '板号')"
        @keyup.enter="handleFilter"
        @clear="handleFilter"
      />
      <ListFilterSelect
        v-model="listQuery.immune_antigen"
        clearable
        filterable
        allow-create
        default-first-option
        v-bind="headerTop('immune_antigen', '免疫抗原')"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.immune_antigen" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.screening_antigen"
        clearable
        filterable
        allow-create
        default-first-option
        v-bind="headerTop('screening_antigen', '筛选抗原')"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.screening_antigen" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.boost_antigen"
        clearable
        filterable
        allow-create
        default-first-option
        v-bind="headerTop('boost_antigen', '冲击免抗原')"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.boost_antigen" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <el-input
        v-model="listQuery.remark"
        clearable
        v-bind="headerTop('remark', '备注')"
        title="备注包含这段文字"
        @keyup.enter="handleFilter"
        @clear="handleFilter"
      />
      <el-date-picker
        v-model="boostRange"
        type="daterange"
        range-separator="至"
        v-bind="headerTop('boost_date', '冲击免起始', 'startPlaceholder')"
        end-placeholder="冲击免截止"
        value-format="YYYY-MM-DD"
        @change="handleFilter"
      />
      <template #actions>
        <el-button v-if="hasSecondaryFilters" @click="resetFilters">重置全部筛选</el-button>
        <el-button v-if="!isExcelMode" @click="openColumnPicker">显示字段</el-button>
        <el-button type="warning" :icon="Download" @click="handleListExport">列表导出</el-button>
      </template>
    </AdvancedOpsBar>

    <section class="workbench-console">
      <header class="console-header">
        <div class="console-brand">
          <div class="title-copy">
            <h1 class="page-title">发现工作台</h1>
            <p class="page-subtitle">安排剖鼠取细胞与筛选路径。工作台点行快改，也可切到 Excel 批量改。</p>
          </div>
        </div>
        <div class="console-actions">
          <button
            type="button"
            class="ready-summary"
            :class="{ 'is-active': Boolean(listQuery.boost_filter) }"
            :aria-pressed="Boolean(listQuery.boost_filter)"
            :title="boostFilterTitle"
            @click="toggleBoostFilter('boosting')"
            @contextmenu.prevent="toggleBoostFilter('missing_date')"
          >
            <span class="ready-dot" />
            <span v-if="listQuery.boost_filter === 'missing_date'"><strong>{{ stats.missing_date }}</strong> 个安排日期未填</span>
            <span v-else><strong>{{ stats.boosting }}</strong> 个项目冲击免中</span>
          </button>
          <el-button v-if="canEdit" type="primary" @click="handleCreate">
            新增安排
          </el-button>
        </div>
      </header>

      <nav class="lifecycle-nav" aria-label="安排视图">
        <button
          v-for="item in statusViews"
          :key="item.key || 'all'"
          type="button"
          class="lifecycle-item"
          :class="[`stage-${item.tone}`, { 'is-active': activeViewGroup === item.key }]"
          :aria-pressed="activeViewGroup === item.key"
          :title="lifecycleTitle(item)"
          @click="handleViewGroup(item.key)"
          @contextmenu="onLifecycleContextMenu(item, $event)"
        >
          <span class="stage-marker">{{ item.step }}</span>
          <span class="stage-copy">
            <strong>{{ item.label }}</strong>
            <small>{{ lifecycleHint(item) }}</small>
          </span>
          <span class="stage-count">{{ stats[item.valueKey] }}</span>
        </button>
      </nav>
    </section>

    <div class="filter-panel">
      <div class="data-toolbar list-filter-controls">
        <div class="filter-strip">
          <el-input
            v-model="listQuery.keyword"
            class="filter-keyword"
            placeholder="项目编号、实验号"
            title="搜索发现编号、项目编号或实验号"
            clearable
            @keyup.enter="handleFilter"
            @clear="handleFilter"
          />
          <WorkbenchTargetFilter
            v-model="listQuery.target_name"
            class="filter-select"
            v-bind="headerTop('target_name', '靶点')"
            :search="fetchDiscoveryWorkbenchRecordedTargets"
            @change="handleFilter"
          />
          <div class="filter-select">
            <UserSelect
              v-model="listQuery.pm"
              multi-gesture
              :options="optionLists.pm"
              v-bind="headerTop('pm', 'PM')"
              title="左键单选，右键追加"
              clearable
              @change="handleFilter"
            />
          </div>
          <ListFilterSelect
            v-model="listQuery.screening_methods"
            v-bind="headerTop('screening_methods', '筛选方式')"
            clearable
            class="filter-select"
            @change="handleFilter"
          >
            <el-option
              v-for="item in optionLists.screening_methods"
              :key="item"
              :label="item"
              :value="item"
            />
          </ListFilterSelect>
          <ListFilterSelect
            v-model="listQuery.status"
            v-bind="headerTop('status', '状态')"
            clearable
            class="filter-select"
            @change="handleFilter"
          >
            <el-option v-for="item in optionLists.status" :key="item" :label="item" :value="item" />
          </ListFilterSelect>
          <ListFilterSelect
            v-model="listQuery.priority"
            v-bind="headerTop('priority', '优先级')"
            clearable
            class="filter-select"
            @change="handleFilter"
          >
            <el-option v-for="item in optionLists.priority" :key="item" :label="item" :value="item" />
          </ListFilterSelect>
          <ListFilterSelect
            v-model="listQuery.mouse_strain_category"
            v-bind="headerTop('mouse_strain_category', '归类鼠型')"
            clearable
            class="filter-select"
            @change="handleFilter"
          >
            <el-option v-for="item in optionLists.mouse_strain_category" :key="item" :label="item" :value="item" />
          </ListFilterSelect>
          <el-date-picker
            v-model="harvestRange"
            class="harvest-range"
            type="daterange"
            range-separator="至"
            v-bind="headerTop('harvest_date', '剖鼠起始', 'startPlaceholder')"
            end-placeholder="剖鼠截止"
            value-format="YYYY-MM-DD"
            @change="handleFilter"
          />
        </div>
        <div class="data-view-controls list-filter-actions">
          <WorkbenchHeaderFilterChip v-bind="headerChipBind" />
          <button
            type="button"
            class="list-advanced-trigger"
            :class="{ 'is-active': showAdvancedOps || hasAdvancedFilters }"
            :title="hasAdvancedFilters ? '高级筛选已启用' : '更多筛选与操作'"
            @click="showAdvancedOps = !showAdvancedOps"
          >
            <el-icon><Tools /></el-icon>
          </button>
          <el-button class="list-filter-action-button" type="primary" title="右键清空筛选与表头排序" @click="handleFilter" @contextmenu.prevent="resetFilters">
            <el-icon><Search /></el-icon>
            <span>查询</span>
          </el-button>
          <WorkbenchViewToggle
            :model-value="viewMode"
            @toggle="toggleViewMode"
            @reset-columns="resetSheetColumnOrder"
          />
        </div>
      </div>
    </div>

    <el-card shadow="never" class="table-card list-table-card">
      <div ref="listTableBody" class="list-table-body">
      <WorkbenchDataTable
        v-if="viewMode === 'workbench'"
        ref="workbenchTable"
        :height="listTableHeight"
        v-loading="loading"
        :storage-key="viewPrefsStorageKey"
        :columns="workbenchColumns"
        :data="list"
        border
        stripe
        fit
        highlight-current-row
        size="large"
        class="list-data-table"
        :class="{ 'is-row-sortable': canDragRows }"
        style="width: 100%;"
        row-key="id"
        :row-class-name="workbenchRowClassName"
        :header-menu-states="headerMenuStates"
        @header-menu="openHeaderMenu"
        @row-click="onWorkbenchRowClick"
        @row-contextmenu="onWorkbenchRowContextMenu"
        @reorder="scheduleSortable"
      >
        <template #header-sort_order>
          <WorkbenchSortHeader
            :label="sortColumnLabel"
            :title="sortHeaderTitle"
            :active="isQueueSorted"
            @toggle="toggleQueueSort"
          />
        </template>
        <template #sort_order="{ row, $index }">
          <WorkbenchSortCell
            v-model="row.sort_order"
            :text="formatSortColumn(row, $index)"
            :editing="sortEditingId === row.id"
            :locked="!canEditSortCell(row)"
            @start="onSortCellClick(row)"
            @finish="finishSortEdit(row)"
          />
        </template>
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
            :type="planStatusTone(row.status)"
            :editable="canEdit"
            @change="(value) => persistRowValue(row, 'status', value)"
          />
        </template>
        <template #screening_methods="{ row }">
          <WorkbenchMultiTagEditor
            v-model="row.screening_methods"
            :options="optionLists.screening_methods"
            :tones="screeningMethodTones"
            :editable="canEdit"
            @change="persistRow(row, 'screening_methods')"
          />
        </template>
        <template #harvest_date="{ row }">
          <WorkbenchInlineDatePicker
            v-model="row.harvest_date"
            class="inline-date"
            placeholder="剖鼠/上机"
            :title="harvestDateLocked(row) ? '剖鼠日期已过，不能再改' : ''"
            :disabled="!canEdit || harvestDateLocked(row)"
            @change="persistRow(row, 'harvest_date')"
          />
        </template>
        <template #boost_date="{ row }">
          <WorkbenchInlineDatePicker
            v-model="row.boost_date"
            class="inline-date"
            placeholder="冲击免疫"
            :disabled="!canEdit"
            @change="persistRow(row, 'boost_date')"
          />
        </template>
        <template #actions="{ row }">
          <DiscoveryRowActions
            :row="row"
            :can-edit="canEdit"
            :can-handoff="canHandoff"
            @detail="openSerumProject"
            @handoff="handleHandoff"
            @delete="handleDelete"
            @freeze="openCellBank"
          />
        </template>
      </WorkbenchDataTable>

      <WorkbenchSheet v-else :row-class-name="workbenchRowClassName" actions-width="320">
        <template #actions="{ row }">
          <DiscoveryRowActions
            :row="row"
            :can-edit="canEdit"
            :can-handoff="canHandoff"
            @detail="openSerumProject"
            @handoff="handleHandoff"
            @delete="handleDelete"
            @freeze="openCellBank"
          />
        </template>
      </WorkbenchSheet>
      </div>

      <div class="list-pagination">
        <el-pagination
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          v-model:current-page="listQuery.page"
          v-model:page-size="listQuery.limit"
          :page-sizes="[20, 50, 100, 200, 500]"
          @current-change="getList"
          @size-change="handleFilter"
        />
      </div>
    </el-card>

    <WorkbenchDrawer
      v-model="drawerVisible"
      :title="drawerTitle"
      :meta="drawerMeta"
      :row="editingRow"
      :sections="editorSections"
      :disabled="!canEdit"
      :has-prev="hasPrevEditor"
      :has-next="hasNextEditor"
      @shift="shiftEditor"
    >
      <template #actions>
        <DiscoveryRowActions
          :row="editingRow"
          :can-edit="canEdit"
          :can-handoff="canHandoff"
          @detail="openSerumProject"
          @handoff="handleHandoff"
          @delete="handleDelete"
          @freeze="openCellBank"
        />
      </template>
      <template #field="{ field }">
        <WorkbenchMultiTagEditor
          v-if="field.type === 'multi'"
          :key="`screening-${editingRow.id}`"
          v-model="editingRow.screening_methods"
          :options="optionLists.screening_methods"
          :tones="screeningMethodTones"
          :editable="canEdit"
          align="start"
          @change="persistRow(editingRow, 'screening_methods')"
        />
        <div v-else-if="field.type === 'lines'" class="line-field">
          <WorkbenchLineInput
            v-model="editingRow[field.key]"
            :disabled="!canEdit"
            @focus="openLineSuggest(field, $event)"
            @input="placeLineSuggest($event)"
            @blur="closeLineSuggest(field)"
          />
          <teleport to="body">
            <div
              v-if="lineOpen === field.key && lineSuggestions(field).length"
              class="line-suggest"
              :style="lineSuggestStyle"
              @mousedown.prevent
            >
              <button
                v-for="item in lineSuggestions(field)"
                :key="item"
                type="button"
                class="line-suggest-item"
                :title="item"
                @mousedown.prevent="fillAntigenLine(field, item)"
              >
                {{ item }}
              </button>
            </div>
          </teleport>
        </div>
        <WorkbenchDrawerField v-else v-bind="drawerFieldBind(field)" />
      </template>
    </WorkbenchDrawer>
    <WorkbenchHeaderMenu v-bind="headerMenuBind" />
    <LibraryHandoffDialog
      v-model="handoffVisible"
      :discovery-row="handoffRow"
      @created="onLibraryHandoffCreated"
    />
    <DiscoveryCellBankDialog
      v-model="cellBankVisible"
      :row="cellBankRow"
      :can-edit="canEdit"
    />
  </div>
</template>

<script>
import {
  Download,
  Search,
  Tools,
} from '@element-plus/icons-vue'
import {
  ElButton,
  ElCard,
  ElDatePicker,
  ElIcon,
  ElInput,
  ElMessage,
  ElOption,
  ElPagination,
} from 'element-plus'
import { useUserStore } from '@vben/stores'

import AdvancedOpsBar from '#/components/AdvancedOpsBar.vue'
import LibraryHandoffDialog from '#/views/MolecularCell/library/LibraryHandoffDialog.vue'
import {
  fieldOptionLists,
  uniqueTargetCodes,
  WORKBENCH_VIEW,
  WorkbenchDataTable,
  WorkbenchDrawer,
  WorkbenchDrawerField,
  WorkbenchHeaderFilterChip,
  WorkbenchHeaderMenu,
  WorkbenchInlineDatePicker,
  WorkbenchLineInput,
  WorkbenchPriorityCell,
  WorkbenchSheet,
  workbenchCrudMixin,
  workbenchDrawerMixin,
  workbenchExcelMixin,
  workbenchQueueSortMixin,
  workbenchTargetMixin,
  workbenchHeaderMenuMixin,
  WorkbenchMultiTagEditor,
  WorkbenchSortCell,
  WorkbenchSortHeader,
  WorkbenchStatusEditor,
  WorkbenchTargetFilter,
  WorkbenchViewToggle,
} from '#/components/workbench'
import { listPageMixin } from '#/utils/listPage'
import { listTableLockMixin } from '#/utils/listTableLock'
import { notifyApiError } from '#/api/errors'
import { skipGlobalErrorHandler } from '#/api/request'
import {
  deleteDiscoveryWorkbench,
  exportDiscoveryWorkbenchList,
  fetchDiscoveryWorkbenchColumnValues,
  fetchDiscoveryWorkbenchList,
  fetchDiscoveryWorkbenchOptions,
  reorderDiscoveryWorkbench,
  saveDiscoveryWorkbench,
  saveDiscoveryWorkbenchBatch,
  DISCOVERY_WORKBENCH_CREATED_KEY,
  DISCOVERY_WORKBENCH_EDIT,
  fetchDiscoveryWorkbenchRecordedTargets,
} from '#/api/discoveryWorkbench'
import { SERUM_PAGE_DETAIL } from '#/api/serum'
import { LIBRARY_HANDOFF } from '#/api/molecularLibrary'
import { hasAccessCode } from '#/utils/accessCode'
import { applyOptionLists } from '#/utils/optionLists'
import { uniqueNames } from '#/utils/userOptions'
import ListFilterSelect from '#/components/ListFilterSelect.vue'
import UserSelect from '#/components/UserSelect.vue'
import { dateBreakRowClass } from '#/components/workbench/dateBreakRowClass'
import DiscoveryCellBankDialog from './DiscoveryCellBankDialog.vue'
import DiscoveryRowActions from './DiscoveryRowActions.vue'
import { hasDiscoveryFocus, takeDiscoveryFocus } from './discoveryFocus'
import { openSerumProject } from '../openSerumProject'
import {
  EDITOR_SECTIONS,
  FIELDS,
  HEADER_MENU_COLUMNS,
  SCREENING_METHOD_TONES,
  SHEET_COLUMN_ORDER,
  SHEET_COLUMNS,
  SHEET_HEADER_ALIASES,
  VIEW_PREFS_KEY,
  WORKBENCH_COLUMNS,
} from './discoveryColumns'

const QUEUE_TERMINAL_STATUSES = ['已完成', '已取消']
const QUEUE_KEYS = ['status', 'priority', 'sort_order']
/** 选项接口名单字段与 optionLists 字段键的映射。 */
const NAME_OPTION_SOURCES = {
  pms: 'pm',
  owners: 'owner',
  immune_owners: 'immune_owner',
  cell_collectors: 'cell_collector',
  immune_antigens: 'immune_antigen',
  boost_antigens: 'boost_antigen',
  screening_antigens: 'screening_antigen',
}
const STATUS_VIEWS = [
  { key: '', label: '全部安排', hint: '本台全部发现安排', valueKey: 'all', tone: 'all', step: '00' },
  { key: 'harvest', label: '待剖鼠', hint: '规划中、待冲击与待剖鼠', valueKey: 'harvest', tone: 'planned', step: '01' },
  { key: 'library', label: '待建库', hint: '待建库与待噬菌体', valueKey: 'library', tone: 'ongoing', step: '02' },
  { key: 'sequencing', label: '待测序', hint: '已交分子、等待测序', valueKey: 'sequencing', tone: 'completed', step: '03' },
  { key: 'cancelled', label: '已取消', hint: '已关闭的安排', valueKey: 'cancelled', tone: 'cancelled', step: '04' },
]
function antigenLines(value) {
  return String(value || '')
    .split(/\n+|、+/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function emptyQuery() {
  return {
    page: 1,
    limit: 20,
    keyword: '',
    target_name: '',
    remark: '',
    view_group: '',
    screening_methods: [],
    pm: '',
    owner: '',
    immune_owner: '',
    cell_collector: '',
    study_type: '',
    mouse_strain_category: '',
    status: '',
    priority: '',
    sort_field: '',
    sort_dir: '',
    cage_position: '',
    mouse_strain: '',
    mouse_nos: '',
    plate_nos: '',
    immune_antigen: '',
    screening_antigen: '',
    boost_antigen: '',
    boost_filter: '',
  }
}

export default {
  name: 'DiscoveryWorkbench',
  mixins: [
    workbenchExcelMixin,
    workbenchQueueSortMixin,
    workbenchDrawerMixin,
    workbenchCrudMixin,
    workbenchTargetMixin,
    listPageMixin,
    workbenchHeaderMenuMixin,
    listTableLockMixin,
  ],
  listFilterKey: 'discoveryWorkbench',
  workbenchFields: FIELDS,
  workbenchApi: {
    list: fetchDiscoveryWorkbenchList,
    save: saveDiscoveryWorkbench,
    saveBatch: saveDiscoveryWorkbenchBatch,
    remove: deleteDiscoveryWorkbench,
    export: exportDiscoveryWorkbenchList,
    exportName: '发现工作台',
    columnValues: fetchDiscoveryWorkbenchColumnValues,
    reorder: reorderDiscoveryWorkbench,
    errors: { load: { default: '加载发现工作台失败' } },
  },
  workbenchSheet: { columns: SHEET_COLUMNS, order: SHEET_COLUMN_ORDER, aliases: SHEET_HEADER_ALIASES },
  components: {
    AdvancedOpsBar,
    DiscoveryCellBankDialog,
    DiscoveryRowActions,
    LibraryHandoffDialog,
    ElButton,
    ElCard,
    ElDatePicker,
    ElIcon,
    ElInput,
    ElOption,
    ElPagination,
    WorkbenchDataTable,
    WorkbenchDrawer,
    WorkbenchDrawerField,
    WorkbenchHeaderFilterChip,
    WorkbenchHeaderMenu,
    WorkbenchInlineDatePicker,
    WorkbenchLineInput,
    WorkbenchPriorityCell,
    WorkbenchSheet,
    Search,
    ListFilterSelect,
    UserSelect,
    Tools,
    WorkbenchMultiTagEditor,
    WorkbenchSortCell,
    WorkbenchSortHeader,
    WorkbenchStatusEditor,
    WorkbenchTargetFilter,
    WorkbenchViewToggle,
  },
  setup() {
    const userStore = useUserStore()
    return { Download, fetchDiscoveryWorkbenchRecordedTargets, screeningMethodTones: SCREENING_METHOD_TONES, userStore }
  },
  data() {
    return {
      viewPrefsStorageKey: VIEW_PREFS_KEY,
      loading: false,
      list: [],
      total: 0,
      stats: { all: 0, harvest: 0, library: 0, sequencing: 0, cancelled: 0, boosting: 0, missing_date: 0 },
      showAdvancedOps: false,
      harvestRange: [],
      boostRange: [],
      listQuery: emptyQuery(),
      optionLists: {
        ...fieldOptionLists(FIELDS),
        pm: [],
        owner: [],
        immune_owner: [],
        cell_collector: [],
        immune_antigen: [],
        boost_antigen: [],
        screening_antigen: [],
      },
      lineOpen: '',
      lineSuggestStyle: {},
      editorSections: EDITOR_SECTIONS,
      statusViews: STATUS_VIEWS,
      workbenchColumns: WORKBENCH_COLUMNS.map((column) => (
        column.key === 'actions' ? { ...column, width: 320 } : column
      )),
      cellBankVisible: false,
      cellBankRow: null,
      headerMenuColumns: HEADER_MENU_COLUMNS,
      listLoaded: false,
      consumingCreated: false,
      handoffVisible: false,
      handoffRow: null,
    }
  },
  computed: {
    canEdit() {
      return hasAccessCode(this.userStore.userInfo, DISCOVERY_WORKBENCH_EDIT)
    },
    canHandoff() {
      return hasAccessCode(this.userStore.userInfo, ...LIBRARY_HANDOFF)
    },
    canViewSerumProject() {
      return hasAccessCode(this.userStore.userInfo, SERUM_PAGE_DETAIL)
    },
    harvestStatusExact() {
      return this.listQuery.view_group === 'harvest' && this.listQuery.status === '待剖鼠'
    },
    boostFilterTitle() {
      if (this.listQuery.boost_filter === 'missing_date') {
        return '当前只看剖鼠或冲击日期还空着的，不含已完成和已取消。右键取消；左键改看冲击免中。'
      }
      if (this.listQuery.boost_filter === 'boosting') {
        return '当前只看冲击免中。再点取消；右键改看剖鼠或冲击日期还空着的。'
      }
      return '左键只看冲击免中；右键只看剖鼠或冲击日期还空着的。'
    },
    activeViewGroup() {
      return this.listQuery.view_group || ''
    },
    drawerTitle() {
      const row = this.editingRow
      if (!row) return '安排详情'
      const name = String(row.target_name || '').trim()
      const code = String(row.project_code || '').trim()
      if (name) return name
      if (code) return code
      return '安排详情'
    },
    drawerMeta() {
      const row = this.editingRow
      if (!row) return ''
      return [
        row.experiment_id,
        this.formatCodesText(row.target_codes),
        this.editingIndex < 0 ? '当前筛选结果外' : '',
      ].filter(Boolean).join(' · ')
    },
    hasAdvancedFilters() {
      return Boolean(
        this.listQuery.study_type
        || this.listQuery.owner
        || this.listQuery.immune_owner
        || this.listQuery.cell_collector
        || this.listQuery.cage_position
        || this.listQuery.mouse_strain
        || this.listQuery.mouse_nos
        || this.listQuery.plate_nos
        || this.listQuery.immune_antigen
        || this.listQuery.screening_antigen
        || this.listQuery.boost_antigen
        || this.listQuery.remark
        || this.boostRange?.length,
      )
    },
    hasSecondaryFilters() {
      return Boolean(
        this.listQuery.keyword
        || this.listQuery.target_name
        || this.listQuery.screening_methods?.length
        || this.listQuery.pm
        || this.listQuery.owner
        || this.listQuery.immune_owner
        || this.listQuery.cell_collector
        || this.listQuery.study_type
        || this.listQuery.mouse_strain_category
        || this.listQuery.status
        || this.listQuery.priority
        || this.listQuery.cage_position
        || this.listQuery.mouse_strain
        || this.listQuery.mouse_nos
        || this.listQuery.plate_nos
        || this.listQuery.immune_antigen
        || this.listQuery.screening_antigen
        || this.listQuery.boost_antigen
        || this.listQuery.remark
        || this.harvestRange?.length
        || this.boostRange?.length
        || this.headerFiltering,
      )
    },
  },
  created() {
    this.loading = true
    this.loadOptions()
    const remembered = hasDiscoveryFocus()
    const listing = remembered ? this.openRememberedDiscovery() : this.getList()
    listing.finally(() => {
      this.listLoaded = true
      if (!remembered) this.consumeCreatedQuery()
    })
  },
  activated() {
    if (hasDiscoveryFocus()) {
      this.openRememberedDiscovery()
      return
    }
    if (this.listLoaded && this.isListDataStale()) this.getList()
  },
  watch: {
    '$route.query.created'() {
      if (this.listLoaded) this.consumeCreatedQuery()
    },
  },
  methods: {
    harvestDateLocked(row) {
      const text = String(row?.harvest_date || '').trim().slice(0, 10)
      if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) return false
      const now = new Date()
      const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
      return text < today
    },
    isDrawerFieldDisabled(field, row) {
      if (field?.key === 'harvest_date' && this.harvestDateLocked(row)) return true
      return !this.canEdit
    },
    drawerFieldBind(field) {
      const bind = workbenchDrawerMixin.methods.drawerFieldBind.call(this, field)
      if (field?.key === 'harvest_date' && this.harvestDateLocked(this.editingRow)) {
        bind.title = '剖鼠日期已过，不能再改'
      }
      return bind
    },
    sheetCellLockReason(row, key) {
      const fixed = this.sheetSortLockReason?.(row, key) || this.sheetReadonlyLockReason(key)
      if (fixed) return fixed
      if (!this.canEdit) return '你没有编辑权限'
      if (key === 'harvest_date' && this.harvestDateLocked(row)) return '剖鼠日期已过，不能再改'
      return ''
    },
    workbenchRowClassName({ row, rowIndex }) {
      return dateBreakRowClass({
        list: this.list,
        row,
        rowIndex,
        field: 'harvest_date',
        editingId: this.editingId,
      })
    },
    openCellBank(row) {
      if (!row?.id) return
      this.cellBankRow = row
      this.cellBankVisible = true
    },
    savedFieldKeys(fields) {
      const keys = new Set(fields)
      if (keys.has('target_codes') || keys.has('target_name')) {
        keys.add('target_codes')
        keys.add('target_name')
      }
      if (keys.has('harvest_date')) keys.add('boost_date')
      if (keys.has('boost_date') || keys.has('harvest_date')) keys.add('status')
      if (QUEUE_KEYS.some((key) => keys.has(key))) keys.add('sort_order')
      return keys
    },
    async saveRowField(row, field) {
      if (!this.canEdit || !row?.id) return
      if (!this.normalizeDrawerValue(row, field)) return
      if (this.rowFieldsUnchanged(row, [field])) return
      return this.submitRowFields(row, [field])
    },
    drawerSelectClass(field, row) {
      return field.key === 'status' ? `status-select status-tone-${this.planStatusTone(row?.status)}` : ''
    },
    lineSuggestions(field) {
      const options = uniqueNames(antigenLines(this.editingRow?.immune_antigen))
      const line = String(this.editingRow?.[field.key] || '').split('\n').pop().trim().toLowerCase()
      if (!line) return options
      if (options.some((item) => item.toLowerCase() === line)) return []
      return options.filter((item) => item.toLowerCase().includes(line))
    },
    placeLineSuggest(event) {
      const box = event?.target?.closest?.('.line-field')?.getBoundingClientRect()
      if (!box) return
      const gap = 6
      const spaceBelow = window.innerHeight - box.bottom
      const openUp = spaceBelow < 160 && box.top > spaceBelow
      const maxHeight = Math.min(220, (openUp ? box.top : spaceBelow) - gap - 8)
      this.lineSuggestStyle = {
        left: `${box.left}px`,
        width: `${box.width}px`,
        maxHeight: `${Math.max(maxHeight, 80)}px`,
        top: openUp ? 'auto' : `${box.bottom + gap}px`,
        bottom: openUp ? `${window.innerHeight - box.top + gap}px` : 'auto',
      }
    },
    openLineSuggest(field, event) {
      this.placeLineSuggest(event)
      this.lineOpen = field.key
    },
    closeLineSuggest(field) {
      if (this.lineOpen === field.key) this.lineOpen = ''
      this.persistRow(this.editingRow, field.key)
    },
    fillAntigenLine(field, value) {
      const picked = String(value || '').trim()
      if (!picked || !this.editingRow) return
      const lines = String(this.editingRow[field.key] || '').split('\n')
      lines[lines.length - 1] = picked
      this.editingRow[field.key] = lines.join('\n')
      this.lineOpen = field.key
    },
    formatCodesText(value) {
      return uniqueTargetCodes(value).join(',')
    },
    planStatusTone(value) {
      if (value === '已取消') return 'info'
      if (value === '已完成') return 'success'
      if (value === '待测序') return 'warning'
      if (value === '待建库' || value === '待噬菌体') return 'library'
      if (value.startsWith('待')) return 'primary'
      return 'info'
    },
    buildQuery() {
      const payload = { ...this.listQuery }
      if (!payload.view_group) delete payload.view_group
      if (!payload.boost_filter) delete payload.boost_filter
      if (!payload.status) delete payload.status
      if (!payload.priority) delete payload.priority
      if (!payload.sort_field) delete payload.sort_field
      if (!payload.sort_dir) delete payload.sort_dir
      if (Array.isArray(this.harvestRange) && this.harvestRange.length === 2) {
        payload.harvest_date_start = this.harvestRange[0]
        payload.harvest_date_end = this.harvestRange[1]
      }
      if (Array.isArray(this.boostRange) && this.boostRange.length === 2) {
        payload.boost_date_start = this.boostRange[0]
        payload.boost_date_end = this.boostRange[1]
      }
      const fieldFilters = this.headerFilterPayload()
      if (fieldFilters.length) payload.field_filters = fieldFilters
      return payload
    },
    async loadOptions() {
      try {
        const data = await fetchDiscoveryWorkbenchOptions(skipGlobalErrorHandler)
        applyOptionLists(this.optionLists, data, {
          screening_methods: 'screening_methods',
          statuses: 'status',
          priorities: 'priority',
          mouse_strain_categories: 'mouse_strain_category',
          mouse_strains: 'mouse_strain',
        })
        for (const [source, key] of Object.entries(NAME_OPTION_SOURCES)) {
          this.optionLists[key] = uniqueNames(data?.[source] || [])
        }
      } catch (error) {
        notifyApiError(error, { messages: { default: '加载发现工作台选项失败' } })
      }
    },
    /** 清空全部筛选和表头排序；视图分组和队列排序是视图模式，保留。 */
    resetFilters() {
      this.listQuery = {
        ...emptyQuery(),
        view_group: this.listQuery.view_group,
        sort_field: this.isQueueSorted ? 'sort_order' : '',
      }
      this.harvestRange = []
      this.boostRange = []
      this.clearHeaderFilters()
      this.getList()
    },
    listFilterExtras() {
      return { harvestRange: this.harvestRange, boostRange: this.boostRange }
    },
    restoreListFilterExtras(state) {
      if (Array.isArray(state.harvestRange)) this.harvestRange = state.harvestRange
      if (Array.isArray(state.boostRange)) this.boostRange = state.boostRange
    },
    lifecycleHint(item) {
      if (item.key === 'harvest' && this.harvestStatusExact) return '只看状态为待剖鼠'
      return item.hint
    },
    lifecycleTitle(item) {
      if (item.key !== 'harvest') return item.hint
      if (this.harvestStatusExact) {
        return '当前只看状态为待剖鼠。右键回到规划中、待冲击与待剖鼠。'
      }
      return '左键看规划中、待冲击与待剖鼠；右键只看状态为待剖鼠。'
    },
    onLifecycleContextMenu(item, event) {
      if (item.key !== 'harvest') return
      event.preventDefault()
      if (this.harvestStatusExact) {
        this.listQuery.status = ''
      } else {
        this.listQuery.view_group = 'harvest'
        this.listQuery.status = '待剖鼠'
      }
      this.handleFilter()
    },
    handleViewGroup(key) {
      if (!key || this.listQuery.status === '待剖鼠') {
        this.listQuery.status = ''
        this.dropHeaderFilter('status')
      }
      this.listQuery.view_group = key || ''
      this.handleFilter()
    },
    toggleBoostFilter(value) {
      this.listQuery.boost_filter = this.listQuery.boost_filter === value ? '' : value
      this.handleFilter()
    },
    isQueueTerminalRow(row) {
      return QUEUE_TERMINAL_STATUSES.includes(String(row?.status || '').trim())
    },
    openSerumProject(row) {
      return openSerumProject(this, row, String(row?.experiment_id || '').trim(), '请先填写实验号')
    },
    async consumeCreatedQuery() {
      if (this.$route.name !== 'DiscoveryWorkbench' || this.consumingCreated) return
      const raw = this.$route.query.created
      const id = Number(Array.isArray(raw) ? raw[0] : raw)
      if (!Number.isSafeInteger(id) || id <= 0) return
      this.consumingCreated = true
      try {
        let saved
        try {
          const rawSaved = sessionStorage.getItem(DISCOVERY_WORKBENCH_CREATED_KEY)
          if (rawSaved) {
            const parsed = JSON.parse(rawSaved)
            if (Number(parsed?.id) === id) saved = parsed
          }
          sessionStorage.removeItem(DISCOVERY_WORKBENCH_CREATED_KEY)
        } catch {
          /* 暂存缺失时仍按 id 打开。 */
        }
        const nextQuery = { ...this.$route.query }
        delete nextQuery.created
        await this.$router.replace({ path: this.$route.path, query: nextQuery })
        await this.revealCreatedRow(saved || { id })
      } finally {
        this.consumingCreated = false
      }
    },
    async openRememberedDiscovery() {
      const discoveryId = takeDiscoveryFocus()
      if (!discoveryId || this.$route.name !== 'DiscoveryWorkbench') return
      this.closeDrawer()
      this.listQuery = { ...emptyQuery(), keyword: discoveryId }
      this.harvestRange = []
      this.boostRange = []
      this.clearHeaderFilters()
      await this.getList()
      const row = this.list.find((item) => item.discovery_id === discoveryId)
      if (!row) {
        ElMessage.warning('未找到对应的发现工单')
        return
      }
      this.viewMode = WORKBENCH_VIEW
      this.openDrawer(row)
    },
    async handleCreate() {
      if (!this.canEdit) {
        ElMessage.warning('您没有权限编辑抗体发现工作台')
        return
      }
      if (!await this.flushPendingSheetEdits()) return
      this.loading = true
      try {
        const saved = await saveDiscoveryWorkbench({})
        await this.revealCreatedRow(saved)
      } catch (error) {
        notifyApiError(error, { messages: { default: '新增失败' } })
      } finally {
        this.loading = false
      }
    },
    handleHandoff(row) {
      if (!this.canHandoff) {
        ElMessage.warning('您没有权限交接至文库构建')
        return
      }
      this.handoffRow = row
      this.handoffVisible = true
    },
    onLibraryHandoffCreated() {
      this.getList({ flushEditor: false })
    },
    deleteConfirmText(row) {
      return `确认删除安排 ${row.project_code || row.target_name || `#${row.id}`}？删除后不可恢复。`
    },
  },
}
</script>

<style scoped src="#/components/workbench/workbenchConsole.css"></style>
<style src="#/components/workbench/workbenchDrawer.css"></style>

<style scoped>
.app-container {
  position: relative;
  min-height: 100%;
  padding: var(--list-page-padding);
  background-color: var(--list-page-bg);
}
.lifecycle-nav {
  grid-template-columns: repeat(5, minmax(0, 1fr));
}
.filter-keyword {
  flex: 2 1 120px;
  min-width: 100px;
}
.filter-select {
  flex: 1 1 100px;
  min-width: 100px;
}
.filter-strip :deep(.harvest-range) {
  flex: 1 1 120px;
  width: auto;
  min-width: 100px;
}
@media (max-width: 1100px) {
  .lifecycle-nav {
    grid-template-columns: repeat(5, minmax(130px, 1fr));
    overflow-x: auto;
  }
}
</style>

<style>
.line-field {
  flex: 1;
  width: 100%;
  min-width: 0;
}
.line-field .el-textarea {
  width: 100%;
}
.line-suggest {
  position: fixed;
  z-index: 4100;
  overflow: auto;
  padding: 6px 0;
  background: var(--el-bg-color-overlay);
  border: 1px solid var(--el-border-color-light);
  border-radius: var(--el-border-radius-base);
  box-shadow: var(--el-box-shadow-light);
}
.line-suggest-item {
  display: block;
  width: 100%;
  height: 34px;
  padding: 0 16px;
  overflow: hidden;
  border: 0;
  background: transparent;
  color: var(--el-text-color-regular);
  font-size: 14px;
  line-height: 34px;
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}
.line-suggest-item:hover {
  background: var(--el-fill-color-light);
}
</style>
