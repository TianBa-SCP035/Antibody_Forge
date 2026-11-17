<template>
  <div class="app-container" :class="{ 'is-list-table-locked': listTableLocked }">
    <AdvancedOpsBar v-model="showAdvancedOps">
      <ListFilterSelect
        v-model="listQuery.review_status"
        clearable
        v-bind="headerTop('review_status', '审核结果')"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.review_status" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.can_start"
        clearable
        v-bind="headerTop('can_start', '开展条件')"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.can_start" :key="item" :label="item === '是' ? '可开展' : '暂不可开展'" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.priority"
        clearable
        v-bind="headerTop('priority', '优先级')"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.priority" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.owner"
        clearable
        filterable
        v-bind="headerTop('owner', '开展人')"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.owner" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.reviewer"
        clearable
        filterable
        v-bind="headerTop('reviewer', '审核人')"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.reviewer" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.display_status"
        clearable
        filterable
        v-bind="headerTop('status', '状态')"
        @change="handleFilter"
      >
        <el-option v-for="item in filterLists.display_status" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.species_cross"
        clearable
        v-bind="headerTop('species_cross', '种属交叉')"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.species_cross" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.mouse_strain"
        clearable
        filterable
        placeholder="小鼠品系"
        @change="handleFilter"
      >
        <el-option v-for="item in filterLists.mouse_strain" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.mouse_zygosity"
        clearable
        v-bind="headerTop('mouse_zygosity', '纯合/杂合')"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.mouse_zygosity" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.mouse_region"
        clearable
        v-bind="headerTop('mouse_region', '提供地区')"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.mouse_region" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.mouse_expand_requested"
        clearable
        v-bind="headerTop('mouse_expand_requested', '代下扩繁')"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.mouse_expand_requested" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.antigen_source"
        clearable
        v-bind="headerTop('antigen_source', '抗原来源')"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.antigen_source" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.lnp_ordered"
        clearable
        v-bind="headerTop('lnp_ordered', 'LNP下单')"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.lnp_ordered" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.cell_prep_status"
        clearable
        v-bind="headerTop('cell_prep_status', '冲击细胞')"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.cell_prep_status" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.has_scheme_data"
        clearable
        placeholder="方案内容"
        @change="handleFilter"
      >
        <el-option label="有内容" value="是" />
        <el-option label="未填写" value="否" />
      </ListFilterSelect>
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
            <h1 class="page-title">免疫工作台</h1>
            <p class="page-subtitle">从计划筹备到实验结题，在同一队列中推进优先级、物料和方案。</p>
          </div>
        </div>
        <div class="console-actions">
          <button
            type="button"
            class="ready-summary"
            :class="{ 'is-active': listQuery.can_start === '是' }"
            :aria-pressed="listQuery.can_start === '是'"
            title="只看已经具备开展条件的计划"
            @click="showReadyPlans"
          >
            <span class="ready-dot" />
            <span><strong>{{ stats.can_start }}</strong> 个计划已可开展</span>
          </button>
          <el-button v-if="canCreate" type="primary" @click="handleCreate">新增计划</el-button>
        </div>
      </header>

      <nav class="lifecycle-nav" aria-label="项目阶段视图">
        <button
          v-for="item in statusViews"
          :key="item.key || 'all'"
          type="button"
          class="lifecycle-item"
          :class="[`stage-${item.tone}`, { 'is-active': activeViewGroup === item.key }]"
          :aria-pressed="activeViewGroup === item.key"
          @click="handleViewGroup(item.key)"
        >
          <span class="stage-marker">{{ item.step }}</span>
          <span class="stage-copy">
            <strong>{{ item.label }}</strong>
            <small>{{ item.hint }}</small>
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
            title="搜索项目名称、项目编号、项目集编号或实验号"
            clearable
            @keyup.enter="handleFilter"
            @clear="handleFilter"
          />
          <WorkbenchTargetFilter
            v-model="listQuery.target_name"
            class="filter-select"
            placeholder="靶点"
            :search="fetchSerumWorkbenchRecordedTargets"
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
            v-model="listQuery.study_type"
            v-bind="headerTop('study_type', '课题类型')"
            clearable
            filterable
            class="filter-select"
            @change="handleFilter"
          >
            <el-option v-for="item in optionLists.study_type" :key="item" :label="item" :value="item" />
          </ListFilterSelect>
          <ListFilterSelect
            v-model="listQuery.immuno_method"
            v-bind="headerTop('immuno_method', '免疫方式')"
            clearable
            class="filter-select"
            @change="handleFilter"
          >
            <el-option v-for="item in optionLists.immuno_method" :key="item" :label="item" :value="item" />
          </ListFilterSelect>
          <ListFilterSelect
            v-model="listQuery.mouse_strain_category"
            placeholder="归类鼠型"
            clearable
            filterable
            class="filter-select"
            @change="handleFilter"
          >
            <el-option v-for="item in filterLists.mouse_strain_category" :key="item" :label="item" :value="item" />
          </ListFilterSelect>
          <ListFilterSelect
            v-model="listQuery.mouse_status"
            v-bind="headerTop('mouse_status', '小鼠运输')"
            clearable
            class="filter-select"
            @change="handleFilter"
          >
            <el-option v-for="item in optionLists.mouse_status" :key="item" :label="item" :value="item" />
          </ListFilterSelect>
          <ListFilterSelect
            v-model="listQuery.antigen_ready"
            v-bind="headerTop('antigen_ready', '抗原到货')"
            clearable
            class="filter-select"
            @change="handleFilter"
          >
            <el-option v-for="item in optionLists.antigen_ready" :key="item" :label="item" :value="item" />
          </ListFilterSelect>
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
          <el-button class="list-filter-action-button" type="primary" title="右键清空筛选" @click="handleFilter" @contextmenu.prevent="resetFilters">
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

    <el-card
      shadow="never"
      class="table-card list-table-card"
    >
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
        :header-menu-states="headerMenuStates"
        @header-menu="openHeaderMenu"
        :row-class-name="workbenchRowClassName"
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
        <template #status="{ row }">
          <WorkbenchStatusEditor
            :value="row.aligned_locked ? row.display_status : row.plan_status"
            :options="optionLists.plan_status"
            :type="statusTagType(row) === 'king' ? 'info' : statusTagType(row)"
            :editable="canEditField(row, 'plan_status') && !row.aligned_locked"
            @change="value => updateStatusField(row, 'plan_status', value)"
          />
        </template>
        <template #mouse_status="{ row }">
          <WorkbenchStatusEditor
            :value="row.mouse_status"
            :options="optionLists.mouse_status"
            :type="mouseStatusTone(row.mouse_status)"
            :editable="canEditField(row, 'mouse_status')"
            @change="value => updateStatusField(row, 'mouse_status', value)"
          />
        </template>
        <template #antigen_ready="{ row }">
          <WorkbenchStatusEditor
            :value="row.antigen_ready"
            :options="optionLists.antigen_ready"
            :type="yesNoTagType(row.antigen_ready)"
            :editable="canEditField(row, 'antigen_ready')"
            @change="value => updateStatusField(row, 'antigen_ready', value)"
          />
        </template>
        <template #review_status="{ row }">
          <WorkbenchStatusEditor
            :value="row.review_status"
            :options="optionLists.review_status"
            :type="reviewTone(row.review_status)"
            :editable="canEditField(row, 'review_status')"
            @change="value => updateStatusField(row, 'review_status', value)"
          />
        </template>
        <template #can_start="{ row }">
          <WorkbenchStatusEditor
            :value="row.can_start"
            :options="optionLists.can_start"
            :type="yesNoTagType(row.can_start)"
            :editable="canEditField(row, 'can_start')"
            @change="value => updateStatusField(row, 'can_start', value)"
          />
        </template>
        <template #priority="{ row }">
          <WorkbenchPriorityCell
            :value="row.priority"
            :options="optionLists.priority"
            :editable="canEditField(row, 'priority')"
            @change="(value) => persistRowValue(row, 'priority', value)"
          />
        </template>
        <template #actions="{ row }">
          <WorkbenchRowActions
            :row="row"
            :can-copy="canCopy"
            :can-delete="canDeleteRow(row)"
            :can-unlist="canFullEdit"
            @scheme="openScheme"
            @view="openStartedDetail"
            @edit="openStartedEdit"
            @copy="handleCopy"
            @delete="handleDelete"
            @unlist="handleUnlist"
          />
        </template>
      </WorkbenchDataTable>

      <WorkbenchSheet v-else :header-cell-style="headerCellStyle">
        <template #actions="{ row }">
          <WorkbenchRowActions
            :row="row"
            :can-copy="canCopy"
            :can-delete="canDeleteRow(row)"
            :can-unlist="canFullEdit"
            @scheme="openScheme"
            @view="openStartedDetail"
            @edit="openStartedEdit"
            @copy="handleCopy"
            @delete="handleDelete"
            @unlist="handleUnlist"
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
        <WorkbenchRowActions
          :row="editingRow"
          :can-copy="canCopy"
          :can-delete="canDeleteRow(editingRow)"
          :can-unlist="canFullEdit"
          @scheme="openScheme"
          @view="openStartedDetail"
          @edit="openStartedEdit"
          @copy="handleCopy"
          @delete="handleDelete"
          @unlist="handleUnlist"
        />
      </template>
      <template #field="{ field }">
        <el-input
          v-if="field.type === 'age'"
          :model-value="mouseAgeWeeksValue(editingRow)"
          :disabled="isDrawerFieldDisabled(field, editingRow)"
          @focus="beginMouseAgeWeeksEdit(editingRow)"
          @update:model-value="onMouseAgeWeeksInput(editingRow, $event)"
          @blur="finishMouseAgeWeeksEdit(editingRow, field.key)"
        />
        <WorkbenchDrawerField v-else v-bind="drawerFieldBind(field)" />
      </template>
    </WorkbenchDrawer>

    <WorkbenchHeaderMenu v-bind="headerMenuBind" />
  </div>
</template>

<script>
import { useUserStore } from '@vben/stores'
import {
  Download,
  Search,
  Tools,
} from '@element-plus/icons-vue'
import {
  ElButton,
  ElCard,
  ElIcon,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElPagination,
} from 'element-plus'

import AdvancedOpsBar from '#/components/AdvancedOpsBar.vue'
import {
  fieldOptionLists,
  uniqueTargetCodes,
  WorkbenchDataTable,
  WorkbenchDrawer,
  WorkbenchDrawerField,
  WorkbenchHeaderFilterChip,
  WorkbenchHeaderMenu,
  WorkbenchPriorityCell,
  WorkbenchSheet,
  WorkbenchSortCell,
  WorkbenchSortHeader,
  WorkbenchTargetFilter,
  workbenchCrudMixin,
  workbenchDrawerMixin,
  workbenchExcelMixin,
  workbenchHeaderMenuMixin,
  workbenchQueueSortMixin,
  workbenchTargetMixin,
  WorkbenchViewToggle,
  WorkbenchStatusEditor,
} from '#/components/workbench'
import { listPageMixin } from '#/utils/listPage'
import { listTableLockMixin } from '#/utils/listTableLock'
import { notifyApiError } from '#/api/errors'
import {
  copyWorkbench,
  deleteWorkbench,
  exportWorkbenchList,
  fetchWorkbenchColumnValues,
  fetchWorkbenchList,
  fetchWorkbenchOptions,
  reorderWorkbench,
  saveWorkbench,
  saveWorkbenchBatch,
  unlistWorkbench,
  fetchSerumWorkbenchRecordedTargets,
  SERUM_WORKBENCH_DRAFT_EDIT,
  SERUM_WORKBENCH_EDIT,
  SERUM_WORKBENCH_SUPPORT_EDIT,
} from '#/api/serumWorkbench'
import { SERUM_PAGE_DETAIL } from '#/api/serum'
import { hasAccessCode } from '#/utils/accessCode'
import { canOpenSerumEdit, getSerumUserName } from '#/utils/serumPermission'
import { getWorkbenchDisplayStatusTagType } from '#/utils/serumProjectStatus'
import { uniqueNames } from '#/utils/userOptions'
import { SERUM_ERRORS } from '../shared/errors'
import ListFilterSelect from '#/components/ListFilterSelect.vue'
import UserSelect from '#/components/UserSelect.vue'
import WorkbenchRowActions from './WorkbenchRowActions.vue'

import {
  ALIGNED_FIELDS,
  EDITOR_SECTIONS,
  FIELDS,
  HEADER_MENU_COLUMNS,
  PLAN_STATUS_OPTIONS,
  SHEET_COLUMN_ORDER,
  SHEET_COLUMNS,
  SHEET_HEADER_ALIASES,
  VIEW_PREFS_KEY,
  WORKBENCH_COLUMNS,
} from './serumColumns'

const QUEUE_TERMINAL_PLAN_STATUSES = ['已取消', '小鼠KO致死']
const QUEUE_TERMINAL_PROJECT_STATUSES = ['结题', '无效价处死']
const DRAFT_PROTECTED_FIELDS = new Set(['plan_status', 'reviewer', 'review_status', 'can_start'])
const SUPPORT_EDIT_FIELDS = new Set([
  'mouse_scheme_no',
  'mouse_count',
  'mouse_zygosity',
  'mouse_birth_date',
  'mouse_age_weeks',
  'mouse_expand_requested',
  'mouse_region',
  'mouse_room',
  'mouse_status',
  'mouse_arrive_date',
  'mouse_remark',
  'antigen_source',
  'antigen_ready',
  'antigen_eta',
  'lnp_ordered',
  'cell_prep_status',
  'antigen_remark',
])
const STATUS_VIEWS = [
  { key: '', label: '全部项目', hint: '查看完整工作队列', valueKey: 'all', tone: 'all', step: 'ALL' },
  { key: 'planned', label: '计划中', hint: '尚未正式开展', valueKey: 'planned', tone: 'planned', step: '01' },
  { key: 'ongoing', label: '进行中', hint: '实验正在推进', valueKey: 'ongoing', tone: 'ongoing', step: '02' },
  { key: 'completed', label: '已完成', hint: '结题或终止实验', valueKey: 'completed', tone: 'completed', step: '03' },
  { key: 'cancelled', label: '已取消', hint: '未开展即关闭', valueKey: 'cancelled', tone: 'cancelled', step: '04' },
]
const NAME_OPTION_SOURCES = {
  pms: 'pm',
  owners: 'owner',
  reviewers: 'reviewer',
}

export default {
  name: 'SerumWorkbench',
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
  listFilterKey: 'serumWorkbench',
  workbenchFields: FIELDS,
  workbenchApi: {
    list: fetchWorkbenchList,
    save: saveWorkbench,
    saveBatch: saveWorkbenchBatch,
    remove: deleteWorkbench,
    export: exportWorkbenchList,
    exportName: '免疫工作台列表',
    columnValues: fetchWorkbenchColumnValues,
    reorder: reorderWorkbench,
    errors: {
      load: SERUM_ERRORS.workbench.load,
      remove: SERUM_ERRORS.workbench.delete,
      export: SERUM_ERRORS.workbench.exportList,
      save: SERUM_ERRORS.workbench.save,
    },
  },
  workbenchSheet: { columns: SHEET_COLUMNS, order: SHEET_COLUMN_ORDER, aliases: SHEET_HEADER_ALIASES },
  components: {
    AdvancedOpsBar,
    WorkbenchDrawer,
    WorkbenchDrawerField,
    WorkbenchHeaderFilterChip,
    WorkbenchHeaderMenu,
    WorkbenchSheet,
    WorkbenchSortCell,
    WorkbenchSortHeader,
    WorkbenchViewToggle,
    ElButton,
    ElCard,
    ElIcon,
    ElInput,
    ElOption,
    ElPagination,
    WorkbenchDataTable,
    WorkbenchPriorityCell,
    Search,
    ListFilterSelect,
    UserSelect,
    Tools,
    WorkbenchRowActions,
    WorkbenchStatusEditor,
    WorkbenchTargetFilter,
  },
  setup() {
    const userStore = useUserStore()
    return { Download, fetchSerumWorkbenchRecordedTargets, userStore }
  },
  data() {
    return {
      viewPrefsStorageKey: VIEW_PREFS_KEY,
      loading: false,
      schemeReturnRefresh: false,
      list: [],
      total: 0,
      stats: { all: 0, planned: 0, ongoing: 0, completed: 0, cancelled: 0, can_start: 0 },
      showAdvancedOps: false,
      ageEditingRowId: null,
      headerCellStyle: {
        background: 'var(--list-table-header-bg)',
        color: 'var(--list-table-header-color)',
        height: '48px',
        fontSize: '14px',
        fontWeight: 'var(--list-table-header-weight)',
      },
      listQuery: {
        page: 1,
        limit: 20,
        keyword: '',
        target_name: '',
        view_group: null,
        sort_field: '',
        sort_dir: '',
        can_start: '',
        study_type: '',
        immuno_method: '',
        mouse_strain_category: '',
        species_cross: '',
        mouse_status: '',
        antigen_ready: '',
        pm: '',
        priority: '',
        owner: '',
        reviewer: '',
        review_status: '',
        display_status: '',
        mouse_strain: '',
        mouse_zygosity: '',
        mouse_region: '',
        mouse_expand_requested: '',
        antigen_source: '',
        lnp_ordered: '',
        cell_prep_status: '',
        has_scheme_data: '',
      },
      optionLists: {
        ...fieldOptionLists(FIELDS),
        pm: [],
        owner: [],
        reviewer: [],
      },
      // 顶部筛选需包含数据库已有值，包括开展后的项目状态和方案分组中的品系。
      filterLists: {
        display_status: [...PLAN_STATUS_OPTIONS, '已开展'],
        mouse_strain: [...FIELDS.mouse_strain.options],
        mouse_strain_category: [...FIELDS.mouse_strain_category.options],
      },
      editorSections: EDITOR_SECTIONS,
      statusViews: STATUS_VIEWS,
      workbenchColumns: WORKBENCH_COLUMNS,
      headerMenuColumns: HEADER_MENU_COLUMNS,
    }
  },
  computed: {
    canFullEdit() {
      return hasAccessCode(this.userStore.userInfo, SERUM_WORKBENCH_EDIT)
    },
    canDraftEdit() {
      return hasAccessCode(this.userStore.userInfo, SERUM_WORKBENCH_DRAFT_EDIT)
    },
    canSupportEdit() {
      return hasAccessCode(this.userStore.userInfo, SERUM_WORKBENCH_SUPPORT_EDIT)
    },
    canEdit() {
      return this.canFullEdit || this.canDraftEdit || this.canSupportEdit
    },
    canCreate() {
      return this.canFullEdit || this.canDraftEdit
    },
    canCopy() {
      return this.canFullEdit || this.canDraftEdit
    },
    activeViewGroup() {
      return this.listQuery.view_group || ''
    },
    hasAdvancedFilters() {
      return [
        'review_status',
        'can_start',
        'priority',
        'owner',
        'reviewer',
        'display_status',
        'species_cross',
        'mouse_strain',
        'mouse_zygosity',
        'mouse_region',
        'mouse_expand_requested',
        'antigen_source',
        'lnp_ordered',
        'cell_prep_status',
        'has_scheme_data',
      ].some((key) => Boolean(this.listQuery[key]))
    },
    hasSecondaryFilters() {
      return [
        'keyword',
        'target_name',
        'can_start',
        'study_type',
        'immuno_method',
        'mouse_strain_category',
        'species_cross',
        'mouse_status',
        'antigen_ready',
        'pm',
        'priority',
        'owner',
        'reviewer',
        'review_status',
        'display_status',
        'mouse_strain',
        'mouse_zygosity',
        'mouse_region',
        'mouse_expand_requested',
        'antigen_source',
        'lnp_ordered',
        'cell_prep_status',
        'has_scheme_data',
      ].some((key) => Boolean(this.listQuery[key])) || this.headerFiltering
    },
    drawerTitle() {
      const row = this.editingRow
      if (!row) return '筹备信息'
      const name = String(row.target_name || '').trim()
      const code = String(row.project_code || '').trim()
      if (name) return name
      if (code) return code
      return '筹备信息'
    },
    drawerMeta() {
      const row = this.editingRow
      if (!row) return ''
      return [
        row.experiment_id,
        uniqueTargetCodes(row.target_codes).join(','),
        this.editingIndex < 0 ? '当前筛选结果外' : '',
      ].filter(Boolean).join(' · ')
    },
  },
  created() {
    this.loading = true
    this.loadFilterOptions()
    this.getList()
  },
  activated() {
    if (this.loading) return
    if (this.schemeReturnRefresh) {
      this.schemeReturnRefresh = false
      this.getList()
      return
    }
    if (this.isListDataStale()) this.getList()
  },
  methods: {
    async loadFilterOptions() {
      try {
        const data = await fetchWorkbenchOptions()
        for (const [source, key] of Object.entries(NAME_OPTION_SOURCES)) {
          this.optionLists[key] = uniqueNames(data?.[source] || [])
        }
        this.filterLists.display_status = uniqueNames([...PLAN_STATUS_OPTIONS, '已开展', ...(data?.statuses || [])])
        this.filterLists.mouse_strain = uniqueNames([...FIELDS.mouse_strain.options, ...(data?.mouse_strains || [])])
        this.filterLists.mouse_strain_category = uniqueNames([
          ...FIELDS.mouse_strain_category.options,
          ...(data?.mouse_strain_categories || []),
        ])
      } catch (error) {
        notifyApiError(error, { messages: { default: '加载筛选选项失败，人员下拉暂时为空，状态与鼠型使用本地预设' } })
      }
    },
    fieldOptions(field, row) {
      if (row?.aligned_locked && field.key === 'plan_status' && row.display_status) return [row.display_status]
      return this.optionLists[field.key] ?? field.options ?? []
    },
    targetSearchCodes() {
      return Array.isArray(this.editingRow?.target_codes) ? this.editingRow.target_codes : []
    },
    isDraftRow(row) {
      return !row?.aligned_locked && row?.plan_status === '草稿'
    },
    canEditField(row, fieldKey) {
      const key = fieldKey === 'target' ? 'target_codes' : fieldKey
      if (key === 'sort_order' && this.isQueueTerminalRow(row)) return false
      if (this.canFullEdit) return true
      if (this.canDraftEdit && this.isDraftRow(row) && !DRAFT_PROTECTED_FIELDS.has(key)) {
        return true
      }
      return this.canSupportEdit && SUPPORT_EDIT_FIELDS.has(key)
    },
    canDeleteRow(row) {
      return this.canFullEdit || (this.canDraftEdit && this.isDraftRow(row))
    },
    isGroupStrainLocked(row, key) {
      return Number(row?.mouse_group_count) >= 2 && (key === 'mouse_strain' || key === 'mouse_strain_category')
    },
    /** 开展后以正式项目为准的字段（状态取项目状态）。 */
    isAlignedLocked(row, key) {
      if (!row?.aligned_locked) return false
      return key === 'plan_status' || ALIGNED_FIELDS.has(key === 'target' ? 'target_codes' : key)
    },
    isDrawerFieldDisabled(field, row) {
      if (!this.canEditField(row, field.key)) return true
      return this.isGroupStrainLocked(row, field.key) || this.isAlignedLocked(row, field.key)
    },
    drawerSelectClass(field, row) {
      if (field.tone === 'status') {
        return `status-select status-tone-${this.statusTagType(row)}`
      }
      if (field.tone === 'yesno') {
        return this.yesNoToneClass(row?.[field.key])
      }
      if (field.tone === 'review') {
        return `status-select status-tone-${this.reviewTone(row?.[field.key])}`
      }
      if (field.tone === 'mouse') {
        return `status-select status-tone-${this.mouseStatusTone(row?.[field.key])}`
      }
      return ''
    },
    drawerFieldValue(field, row) {
      if (field?.key === 'plan_status' && row?.aligned_locked) {
        return row.display_status || row.plan_status
      }
      return row?.[field?.key]
    },
    calculatedMouseAgeWeeks(birthDate) {
      const match = /^(\d{4})-(\d{1,2})-(\d{1,2})/.exec(String(birthDate || '').trim())
      if (!match) return ''
      const birth = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
      if (Number.isNaN(birth.getTime())) return ''
      const today = new Date()
      today.setHours(0, 0, 0, 0)
      const elapsedDays = Math.max(0, Math.floor((today.getTime() - birth.getTime()) / 86_400_000))
      return String(Math.ceil(elapsedDays / 7))
    },
    mouseAgeWeeksValue(row, storedValue = row?.mouse_age_weeks) {
      if (this.ageEditingRowId === row?.id) {
        return String(row?.mouse_age_weeks ?? '')
      }
      const manualValue = String(storedValue ?? '').trim()
      return manualValue || this.calculatedMouseAgeWeeks(row?.mouse_birth_date)
    },
    beginMouseAgeWeeksEdit(row) {
      this.ageEditingRowId = row?.id ?? null
    },
    onMouseAgeWeeksInput(row, value) {
      row.mouse_age_weeks = value
    },
    finishMouseAgeWeeksEdit(row, field) {
      this.ageEditingRowId = null
      this.persistRow(row, field)
    },
    statusTagType(row) {
      return getWorkbenchDisplayStatusTagType(row)
    },
    mouseStatusTone(value) {
      if (value === '已到') return 'success'
      if (value === '在途' || value === '扩繁中') return 'warning'
      if (value === '可运') return 'primary'
      return 'info'
    },
    yesNoTagType(value) {
      return value === '是' ? 'success' : 'info'
    },
    yesNoToneClass(value) {
      return value === '是' ? 'status-tone-success' : 'status-tone-info'
    },
    reviewTone(value) {
      if (value === '已通过') return 'success'
      if (value === '驳回') return 'danger'
      return 'info'
    },
    updateStatusField(row, field, value) {
      if (!this.canEditField(row, field) || !row?.id || row[field] === value) return
      row[field] = value
      if (field === 'plan_status') row.display_status = value
      return this.persistRow(row, field)
    },
    /** 保存失败时刷新列表，并将抽屉中的相关字段恢复为入库值。 */
    async saveRowField(row, field) {
      if (!row?.id || !this.canEditField(row, field)) return
      if (field === 'plan_status' && row.plan_status === '已开展') {
        ElMessage.warning('请到方案草稿页核对方案后再开展')
        await this.getList({ flushEditor: false })
        this.revertDrawerFields(row.id, ['plan_status', 'display_status'])
        return
      }
      let fields = this.drawerValueKeys(field)
      if (!fields.every((key) => this.normalizeDrawerValue(row, key))) return
      if (this.rowFieldsUnchanged(row, fields)) return
      if (field === 'review_status' && !row.aligned_locked) {
        row.reviewer = getSerumUserName(this.userStore.userInfo || {}) || ''
        fields = ['review_status', 'reviewer']
      }
      if (fields.some((key) => !this.canEditField(row, key))) return
      return this.submitRowFields(row, fields)
    },
    /** 粘贴改了审核结果、没一起粘审核人时，和单格修改一样记当前用户为审核人。 */
    expandSheetPasteFields(row, fields) {
      if (!fields.has('review_status') || fields.has('reviewer') || row.aligned_locked) return
      if (!this.canEditField(row, 'reviewer')) return
      row.reviewer = getSerumUserName(this.userStore.userInfo || {}) || ''
      fields.add('reviewer')
    },
    releaseDrawerRow() {
      this.ageEditingRowId = null
    },
    isQueueTerminalRow(row) {
      const plan = String(row?.plan_status || '').trim()
      if (QUEUE_TERMINAL_PLAN_STATUSES.includes(plan)) return true
      const projectStatus = String(row?.display_status || row?.project_status || '').trim()
      return Boolean(row?.aligned_locked && QUEUE_TERMINAL_PROJECT_STATUSES.includes(projectStatus))
    },
    sheetFormatter(column) {
      if (column.key === 'plan_status' || column.key === 'mouse_age_weeks') return this.formatSheetCellValue
      return this.sheetTypeFormatter(column)
    },
    sheetCellValue(row, key) {
      if (key === 'plan_status') return row.display_status || row.plan_status
      if (key === 'mouse_age_weeks') return this.mouseAgeWeeksValue(row)
      return row[key]
    },
    sheetCellLockReason(row, key) {
      const label = this.sheetColumnLabel(key)
      const fixed = this.sheetSortLockReason(row, key) || this.sheetReadonlyLockReason(key)
      if (fixed) return fixed
      if (this.isGroupStrainLocked(row, key)) return `有多组小鼠，${label}请到方案页按组修改`
      if (!this.canEditField(row, key)) {
        if (this.canDraftEdit && !this.isDraftRow(row) && !DRAFT_PROTECTED_FIELDS.has(key)) {
          return '你只能修改草稿记录'
        }
        return `你没有修改「${label}」的权限`
      }
      if (!this.isAlignedLocked(row, key)) return ''
      return key === 'plan_status' ? '项目已开展，状态以正式项目为准' : `项目已开展，${label}请到正式项目修改`
    },
    coerceSheetValue(key, text, row) {
      if (key === 'plan_status' && String(text ?? '').trim() === '已开展') return { ok: false, reason: 'started' }
      return this.coerceSheetField(key, text, row)
    },
    sheetCellClassName({ row, column }) {
      const classes = []
      if (column.field === 'plan_status') classes.push(`sheet-tone-${this.statusTagType(row)}`)
      if (column.field === 'can_start' || column.field === 'antigen_ready') {
        classes.push(row[column.field] === '是' ? 'sheet-tone-success' : 'sheet-tone-info')
      }
      return classes.join(' ')
    },
    // 鼠龄为空时仅展示按出生日期推算的周数；撤回和批量编辑只能使用实际填写值。
    sheetCellText(row, key) {
      if (key === 'mouse_age_weeks') return String(row?.mouse_age_weeks ?? '').trim()
      return String(this.sheetDirectTextValue(row, key) ?? '').trim()
    },
    sheetValidationExtraMessage(_key, reason, label) {
      if (reason === 'integer') return `${label}必须是大于 0 的整数`
      if (reason === 'started') return '请到方案草稿页核对方案后再开展'
      return ''
    },
    handleViewGroup(key) {
      this.listQuery.display_status = ''
      this.dropHeaderFilter('status')
      this.listQuery.view_group = key || null
      this.handleFilter()
    },
    showReadyPlans() {
      const alreadyActive = this.activeViewGroup === 'planned' && this.listQuery.can_start === '是'
      this.listQuery.view_group = alreadyActive ? null : 'planned'
      this.listQuery.can_start = alreadyActive ? '' : '是'
      this.handleFilter()
    },
    resetFilters() {
      Object.assign(this.listQuery, {
        keyword: '',
        target_name: '',
        can_start: '',
        study_type: '',
        immuno_method: '',
        mouse_strain_category: '',
        species_cross: '',
        mouse_status: '',
        antigen_ready: '',
        pm: '',
        priority: '',
        owner: '',
        reviewer: '',
        review_status: '',
        display_status: '',
        mouse_strain: '',
        mouse_zygosity: '',
        mouse_region: '',
        mouse_expand_requested: '',
        antigen_source: '',
        lnp_ordered: '',
        cell_prep_status: '',
        has_scheme_data: '',
      })
      if (this.headerSortActive) Object.assign(this.listQuery, { sort_field: '', sort_dir: '' })
      this.clearHeaderFilters()
      this.handleFilter()
      this.persistListFilters()
    },
    buildQuery() {
      const payload = { ...this.listQuery }
      if (!payload.sort_dir) delete payload.sort_dir
      const fieldFilters = this.headerFilterPayload()
      if (fieldFilters.length) payload.field_filters = fieldFilters
      return payload
    },
    savedFieldKeys(fields) {
      const keys = new Set(fields)
      if (keys.has('target_codes') || keys.has('target_name')) {
        keys.add('target_codes')
        keys.add('target_name')
        keys.add('target_type')
        keys.add('project_name')
      }
      if (keys.has('mouse_strain') || keys.has('mouse_strain_category')) {
        keys.add('mouse_strain')
        keys.add('mouse_strain_category')
        keys.add('mouse_group_count')
        keys.add('project_name')
      }
      if (keys.has('project_code')) {
        keys.add('experiment_id')
      }
      keys.add('display_status')
      return keys
    },
    async handleCreate() {
      if (!this.canCreate) return
      this.loading = true
      try {
        const pm = String(getSerumUserName(this.userStore.userInfo || {}) || '').trim()
        const saved = await saveWorkbench(pm ? { pm } : {})
        await this.revealCreatedRow(saved)
      } catch (err) {
        notifyApiError(err, { messages: SERUM_ERRORS.workbench.save })
      } finally {
        this.loading = false
      }
    },
    deleteBlockReason(row) {
      if (this.canDeleteRow(row)) return ''
      return this.canDraftEdit ? '只能删除草稿状态的工作台记录' : '您没有权限删除工作台记录'
    },
    deleteConfirmText() {
      return '删除后将同时清除挂在临时实验号下的方案子表，确定删除？'
    },
    async handleCopy(row) {
      if (!this.canCopy) {
        ElMessage.warning('您没有权限复制工作台记录')
        return
      }
      try {
        await ElMessageBox.confirm(
          `将「${row.target_name || row.experiment_id || row.id}」复制为新的草稿。只带方案骨架（靶点、品系、抗原、步骤等），不带项目编号、小鼠方案号和后勤/审核现场信息。`,
          '复制工作台记录',
          { type: 'info' },
        )
      } catch {
        return
      }
      if (!await this.flushEditorForAction(row)) return
      this.loading = true
      try {
        const saved = await copyWorkbench(row.id)
        ElMessage.success(`已复制为新草稿，实验号 ${saved.experiment_id}`)
        await this.revealCreatedRow(saved)
      } catch (err) {
        notifyApiError(err, { messages: SERUM_ERRORS.workbench.copy })
      } finally {
        this.loading = false
      }
    },
    async handleUnlist(row) {
      if (!this.canFullEdit) {
        ElMessage.warning('您没有权限下架工作台记录')
        return
      }
      try {
        await ElMessageBox.confirm(
          `确认下架「${row.target_name || row.experiment_id || row.id}」？将删除免疫实验主表，方案子表改回新的临时实验号，工作台回到草稿。仅规划中且无效应工单 / 板次数据时可下架。`,
          '确认下架',
          { type: 'warning' },
        )
      } catch {
        return
      }
      if (!await this.flushEditorForAction(row)) return
      this.loading = true
      try {
        const saved = await unlistWorkbench(row.id)
        this.applySavedFields(saved)
        ElMessage.success(`已下架，临时实验号 ${saved.experiment_id}`)
        await this.getList()
      } catch (err) {
        notifyApiError(err, { messages: SERUM_ERRORS.workbench.unlist })
      } finally {
        this.loading = false
      }
    },
    async openScheme(row) {
      if (!await this.flushEditorForAction(row)) return
      const workbenchId = Number(row?.id)
      if (!Number.isSafeInteger(workbenchId) || workbenchId <= 0) {
        ElMessage.warning('工作台记录尚未保存，请刷新列表后重试')
        return
      }
      this.schemeReturnRefresh = true
      this.$router.push({ name: 'SerumWorkbenchScheme', query: { id: workbenchId } })
    },
    async openStartedDetail(row) {
      if (!await this.flushEditorForAction(row)) return
      if (!row?.serum_project_id) {
        ElMessage.warning('开展后的实验记录不存在')
        return
      }
      if (!hasAccessCode(this.userStore.userInfo, SERUM_PAGE_DETAIL)) {
        ElMessage.warning('没有查看详情的权限')
        return
      }
      this.$router.push({ path: '/serum/detail', query: { id: row.serum_project_id } })
    },
    async openStartedEdit(row) {
      if (!await this.flushEditorForAction(row)) return
      if (!row?.serum_project_id) {
        ElMessage.warning('开展后的实验记录不存在')
        return
      }
      if (!canOpenSerumEdit(this.userStore.userInfo || {}, row)) {
        ElMessage.warning('没有编辑该实验的权限')
        return
      }
      this.$router.push({ path: '/serum/edit', query: { id: row.serum_project_id } })
    },
  },
}
</script>

<style scoped src="#/components/workbench/workbenchConsole.css"></style>
<style src="#/components/workbench/workbenchDrawer.css"></style>

<style scoped>
.app-container {
  position: relative;
  padding: var(--list-page-padding);
  background-color: var(--list-page-bg);
  min-height: 100%;
}
.lifecycle-nav {
  grid-template-columns: repeat(5, minmax(0, 1fr));
}
.filter-keyword {
  flex: 2 1 150px;
  width: auto;
  min-width: 100px;
}
.filter-select {
  flex: 1 1 100px;
  width: auto;
  min-width: 100px;
}
.table-card :deep(.el-table__header .cell) {
  white-space: nowrap;
}
@media (max-width: 1100px) {
  .console-header,
  .data-toolbar {
    flex-wrap: wrap;
  }
  .lifecycle-nav {
    grid-template-columns: repeat(5, minmax(130px, 1fr));
    overflow-x: auto;
  }
  .data-view-controls {
    width: 100%;
    justify-content: flex-end;
  }
}
@media (max-width: 720px) {
  .console-header {
    padding: 16px;
  }
  .console-actions {
    width: 100%;
    justify-content: space-between;
  }
  .lifecycle-nav {
    margin-right: 6px;
    margin-left: 6px;
  }
  .filter-strip,
  .data-view-controls {
    width: 100%;
  }
  .filter-keyword {
    flex-basis: 100%;
    width: 100%;
  }
  .data-view-controls {
    justify-content: flex-end;
  }
}
</style>
