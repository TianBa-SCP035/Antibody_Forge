<template>
  <div class="library-order-page" :class="{ 'is-list-table-locked': listTableLocked }">
    <AdvancedOpsBar v-model="showAdvancedOps">
      <template v-if="showAdvancedOps">
        <el-input
          v-model="listQuery.source_project_code"
          clearable
          v-bind="headerTop('source_project_code', '项目编号')"
          title="多个编号用逗号、空格或换行分隔，按完整编号查找；只填一个时按包含查找"
          @keyup.enter="handleFilter"
          @clear="handleFilter"
        />
        <el-input
          v-model="listQuery.library_batch_no"
          clearable
          v-bind="headerTop('library_batch_no', '建库批号')"
          title="多个批号用逗号、空格或换行分隔，按完整批号查找；只填一个时按包含查找"
          @keyup.enter="handleFilter"
          @clear="handleFilter"
        />
        <ListFilterSelect
          :model-value="listQuery.build_type"
          clearable
          v-bind="headerTop('build_type', '建库类型')"
          @change="onBuildTypeFilter"
        >
          <el-option v-for="item in optionLists.build_type" :key="item.value" :label="item.label" :value="item.value" />
        </ListFilterSelect>
        <UserSelect v-model="listQuery.pm" multi-gesture :options="optionLists.pm" v-bind="headerTop('pm', 'PM')" clearable @change="handleFilter" />
        <ListFilterSelect v-model="listQuery.study_type" clearable filterable v-bind="headerTop('study_type', '课题类型')" @change="handleFilter">
          <el-option v-for="item in optionLists.study_type" :key="item" :label="item" :value="item" />
        </ListFilterSelect>
        <ListFilterSelect v-model="listQuery.sample_type" clearable v-bind="headerTop('sample_type', '样品类型')" @change="handleFilter">
          <el-option v-for="item in optionLists.sample_type" :key="item.value" :label="item.label" :value="item.value" />
        </ListFilterSelect>
        <ListFilterSelect v-model="listQuery.mouse_strain" clearable v-bind="headerTop('mouse_strain', '小鼠品系')" @change="handleFilter">
          <el-option v-for="item in optionLists.mouse_strain" :key="item" :label="item" :value="item" />
        </ListFilterSelect>
        <ListFilterSelect
          v-model="listQuery.cell_type"
          clearable
          filterable
          allow-create
          default-first-option
          v-bind="headerTop('cell_type', '细胞类型')"
          @change="handleFilter"
        >
          <el-option v-for="item in optionLists.cell_type" :key="item" :label="item" :value="item" />
        </ListFilterSelect>
        <el-input v-model="listQuery.source_discovery_id" clearable v-bind="headerTop('source_discovery_id', '来源发现 ID')" @keyup.enter="handleFilter" @clear="handleFilter" />
        <el-input v-model="listQuery.notebook_no" clearable v-bind="headerTop('notebook_no', '实验记录本号')" @keyup.enter="handleFilter" @clear="handleFilter" />
        <el-input v-model="listQuery.remark" clearable v-bind="headerTop('remark', '备注')" @keyup.enter="handleFilter" @clear="handleFilter" />
        <el-date-picker
          v-model="startedRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          v-bind="headerTop('started_at', '开始日起', 'startPlaceholder')"
          end-placeholder="开始日止"
          @change="handleFilter"
        />
        <el-date-picker
          v-model="finishedRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          v-bind="headerTop('finished_at', '完成日起', 'startPlaceholder')"
          end-placeholder="完成日止"
          @change="handleFilter"
        />
      </template>
      <template #actions>
        <el-button v-if="!isExcelMode" @click="openColumnPicker">显示字段</el-button>
        <el-button type="warning" :icon="Download" @click="handleListExport">列表导出</el-button>
        <el-button v-if="canManageFiles" type="primary" :icon="Upload" @click="resultUploadVisible = true">批量质检上传</el-button>
      </template>
    </AdvancedOpsBar>

    <div class="page-header-band">
      <div class="title-group">
        <h1 class="page-title">文库构建</h1>
        <p class="page-subtitle">按实际建库工艺安排任务，记录必要来源、产物与质控信息。</p>
      </div>
      <div class="header-actions">
        <span class="total-count text-secondary">共 {{ total }} 条工单</span>
        <el-button
          type="primary"
          :icon="Plus"
          :class="{ 'no-permission-btn': !canEdit }"
          :title="!canEdit ? '您没有权限新建文库工单' : ''"
          @click="handleCreate"
        >
          新建
        </el-button>
      </div>
    </div>

    <section class="workbench-panel">
      <div class="stats-strip">
        <div
          v-for="item in typeSheets"
          :key="item.statKey"
          class="stat-tile stat-tile-interactive"
          :class="[item.tone, { 'stat-tile-active': activeStatKey === item.statKey }]"
          @click="selectType(item)"
        >
          <span class="stat-copy">
            <span class="stat-label">{{ item.label }}</span>
            <small class="text-hint">{{ item.hint }}</small>
          </span>
          <strong class="stat-value">{{ stats[item.statKey] || 0 }}</strong>
        </div>
      </div>
    </section>

    <div class="filter-strip list-filter-controls">
      <el-input
        v-model="listQuery.library_code"
        class="filter-item filter-keyword"
        clearable
        v-bind="headerTop('library_code', '建库编号')"
        title="多个编号用逗号、空格或换行分隔，按完整编号查找；只填一个时按包含查找"
        :prefix-icon="Search"
        @keyup.enter="handleFilter"
        @clear="handleFilter"
      />
      <ListFilterSelect v-model="listQuery.status" class="filter-item" clearable v-bind="headerTop('status', '状态')" @change="handleFilter">
        <el-option v-for="item in optionLists.status" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect v-model="listQuery.priority" class="filter-item" clearable v-bind="headerTop('priority', '优先级')" @change="handleFilter">
        <el-option v-for="item in optionLists.priority" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <UserSelect
        v-model="listQuery.owner"
        class="filter-item"
        multi-gesture
        :options="optionLists.owner"
        v-bind="headerTop('owner', '负责人')"
        clearable
        @change="handleFilter"
      />
      <ListFilterSelect v-model="listQuery.sample_source" class="filter-item" clearable v-bind="headerTop('sample_source', '样品来源')" @change="handleFilter">
        <el-option v-for="item in optionLists.sample_source" :key="item.value" :label="item.label" :value="item.value" />
      </ListFilterSelect>
      <WorkbenchTargetFilter
        v-model="listQuery.target_name"
        class="filter-item"
        v-bind="headerTop('target_name', '靶点')"
        :search="fetchLibraryRecordedTargets"
        @change="handleFilter"
      />
      <el-date-picker
        v-model="instrumentRange"
        class="filter-range"
        type="daterange"
        value-format="YYYY-MM-DD"
        range-separator="至"
        v-bind="headerTop('instrument_on', '上机日起', 'startPlaceholder')"
        end-placeholder="上机日止"
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
        :height="listTableHeight"
        v-loading="loading"
        :storage-key="viewPrefsStorageKey"
        pin-first="source_project_code"
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
        <template #source_project_code="{ row }">
          <span
            v-if="row.source_discovery_id"
            class="list-code-text is-clickable"
            title="查看来源发现安排"
            @click.stop="openSourceDiscovery(row.source_discovery_id)"
          >{{ row.source_project_code }}</span>
          <span v-else class="list-code-text">{{ row.source_project_code }}</span>
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
            :type="statusTone(row.status)"
            :editable="canEdit"
            @change="(value) => persistRowValue(row, 'status', value)"
          />
        </template>
        <template #received_on="{ row }">
          <WorkbenchInlineDatePicker
            v-model="row.received_on"
            class="inline-date"
            :disabled="!canEdit"
            @change="persistRow(row, 'received_on')"
          />
        </template>
        <template #actions="{ row }">
          <LibraryRowActions
            :row="row"
            :can-edit="canEdit"
            :can-handoff="canHandoff"
            :can-view="canViewDetail"
            @qc="openResult"
            @handoff="handleDownstreamHandoff"
            @delete="handleDelete"
          />
        </template>
      </WorkbenchDataTable>

      <WorkbenchSheet v-else :row-class-name="workbenchRowClassName">
        <template #column="{ column }">
          <VxeColumn
            :field="column.key"
            :title="sheetColumnTitle(column)"
            :width="sheetColumnWidth(column)"
            :min-width="column.minWidth || 150"
            :edit-render="sheetCustomEditRender"
          >
            <template #edit="{ row }">
              <div v-if="sheetEditSource === 'dblclick'" class="sheet-picker-editor">
                <span class="sheet-picker-editor__value">{{ sheetPickerDisplayValue(row, column) }}</span>
                <VxeSelect
                  v-model="row[column.key]"
                  class-name="sheet-grid-editor sheet-picker-control"
                  filterable
                  remote
                  clearable
                  :options="sheetCatalogSelectOptions"
                  :popup-config="sheetCatalogPopupConfig"
                  :remote-config="sheetCatalogRemoteConfig"
                  empty-text="输入名称或序列"
                  @visible-change="onSheetPickerVisibleChange"
                />
              </div>
              <VxeInput
                v-else
                :model-value="sheetDirectTextValue(row, column.key)"
                class-name="sheet-grid-editor"
                @update:model-value="setSheetDirectValue(row, column.key, $event)"
              />
            </template>
          </VxeColumn>
        </template>
        <template #actions="{ row }">
          <div @mousedown.stop @click.stop>
            <LibraryRowActions
              :row="row"
              :can-edit="canEdit"
              :can-handoff="canHandoff"
              :can-view="canViewDetail"
              @qc="openResult"
              @handoff="handleDownstreamHandoff"
              @delete="handleDelete"
            />
          </div>
        </template>
        <template #range-overlay>
          <button
            v-if="showLibraryCodeFillHandle"
            type="button"
            class="library-code-fill-handle"
            title="往上或往下拖，按末尾数字递增填充建库编号"
            aria-label="往上或往下拖，按末尾数字递增填充建库编号"
            @mousedown.stop.prevent="onLibraryCodeFillStart"
          />
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
          <span
            v-for="fact in drawerHeaderFacts"
            :key="fact.key"
            :class="{ 'is-type': fact.key === 'type' }"
          >
            {{ fact.text }}
          </span>
        </div>
      </template>
      <template #actions>
        <LibraryRowActions
          :row="editingRow"
          :can-edit="canEdit"
          :can-handoff="canHandoff"
          :can-view="canViewDetail"
          @qc="openResult"
          @handoff="handleDownstreamHandoff"
          @delete="handleDelete"
        />
      </template>
      <template #field="{ field }">
                <div v-if="field.type === 'primer-matrix'" class="primer-matrix">
                  <span />
                  <span class="primer-matrix-heading">正向引物</span>
                  <span class="primer-matrix-heading">反向引物</span>
                  <span class="primer-matrix-heading">浓度</span>
                  <template v-for="primer in field.rows" :key="primer.chain">
                    <strong class="primer-chain">{{ primer.chain }}</strong>
                    <el-select
                      v-model="editingRow[primer.forward.key]"
                      allow-create
                      clearable
                      filterable
                      no-data-text="输入名称或序列"
                      :loading="catalogLoading"
                      :filter-method="filterCatalog"
                      :disabled="!canEdit"
                      @change="(value) => onCatalogChange(editingRow, primer.forward, value)"
                    >
                      <el-option v-for="item in catalogOptions" :key="item.id" :label="item.name" :value="item.name" />
                    </el-select>
                    <el-select
                      v-model="editingRow[primer.reverse.key]"
                      allow-create
                      clearable
                      filterable
                      no-data-text="输入名称或序列"
                      :loading="catalogLoading"
                      :filter-method="filterCatalog"
                      :disabled="!canEdit"
                      @change="(value) => onCatalogChange(editingRow, primer.reverse, value)"
                    >
                      <el-option v-for="item in catalogOptions" :key="item.id" :label="item.name" :value="item.name" />
                    </el-select>
                    <el-input
                      v-model="editingRow[primer.concentrationKey]"
                      :disabled="!canEdit"
                      @blur="persistRow(editingRow, primer.concentrationKey)"
                    />
                  </template>
                </div>
                <div
                  v-else-if="field.type === 'source-link'"
                  class="source-link"
                  :class="{ 'is-link': Boolean(editingRow[field.key]) }"
                  @click="openSourceDiscovery(editingRow[field.key])"
                >
                  <el-input :model-value="editingRow[field.key] || '手工创建'" readonly>
                    <template v-if="editingRow[field.key]" #suffix>
                      <span class="source-link-action">查看</span>
                    </template>
                  </el-input>
                </div>
                <el-select
                  v-else-if="field.type === 'catalog-select'"
                  v-model="editingRow[field.key]"
                  allow-create
                  clearable
                  filterable
                  no-data-text="输入名称或序列"
                  :loading="catalogLoading"
                  :filter-method="filterCatalog"
                  style="width: 100%"
                  :disabled="!canEdit"
                  @change="(value) => onCatalogChange(editingRow, field, value)"
                >
                  <el-option
                    v-for="item in catalogOptions"
                    :key="item.id"
                    :label="item.name"
                    :value="item.name"
                  >
                    <span>{{ item.name }}</span>
                    <span v-if="item.short_sequence" class="catalog-sequence">{{ item.short_sequence }}</span>
                  </el-option>
                </el-select>
                <WorkbenchLineInput
                  v-else-if="field.type === 'plate-list'"
                  :model-value="plateDraft"
                  placeholder="一行一个板号"
                  :disabled="!canEdit"
                  @update:model-value="onPlateDraftInput"
                  @blur="persistRow(editingRow, 'plate_nos')"
                />
                <WorkbenchDrawerField v-else v-bind="drawerFieldBind(field)" />
      </template>
    </WorkbenchDrawer>
    <el-dialog v-model="createVisible" title="新增文库工单" width="640px" append-to-body>
      <div class="create-rows">
        <section v-for="row in createRows" :key="row.method" class="create-row">
          <div class="create-name" :class="`tone-${row.tone}`">{{ row.method }}</div>
          <div class="create-picks">
            <button
              v-for="pick in row.picks"
              :key="pick.id"
              type="button"
              class="create-chip"
              :class="{ on: createPick === pick.id }"
              :title="pick.hint || ''"
              @click="createPick = pick.id"
            >
              {{ pick.label }}
            </button>
          </div>
        </section>
      </div>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!createPick" :loading="creating" @click="confirmCreate">创建</el-button>
      </template>
    </el-dialog>
    <LibraryResultUploadDialog v-model="resultUploadVisible" @uploaded="getList" />
    <WorkbenchHeaderMenu v-bind="headerMenuBind" />
  </div>
</template>

<script>
import { Download, Plus, Search, Tools, Upload } from '@element-plus/icons-vue'
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
  ElSelect,
} from 'element-plus'
import { VxeInput, VxeSelect } from 'vxe-pc-ui'
import { VxeColumn } from 'vxe-table'
import { useUserStore } from '@vben/stores'

import {
  batchSaveLibraryOrders,
  deleteLibraryOrder,
  exportLibraryOrderList,
  fetchLibraryOrderColumnValues,
  fetchLibraryOrderList,
  fetchLibraryOrderOptions,
  saveLibraryOrder,
  fetchLibraryRecordedTargets,
  LIBRARY_CREATED_KEY,
  LIBRARY_EDIT,
  LIBRARY_FILE_MANAGE,
  LIBRARY_PAGE_DETAIL,
} from '#/api/molecularLibrary'
import {
  handoffLibraryToTransfection,
  TRANSFECTION_LIBRARY_HANDOFF,
  TRANSFECTION_PAGE,
} from '#/api/molecularTransfection'
import { notifyApiError } from '#/api/errors'
import { dateBreakRowClass } from '#/components/workbench/dateBreakRowClass'
import AdvancedOpsBar from '#/components/AdvancedOpsBar.vue'
import ListFilterSelect from '#/components/ListFilterSelect.vue'
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
  workbenchCrudMixin,
  workbenchDrawerMixin,
  workbenchExcelMixin,
  workbenchHeaderMenuMixin,
  workbenchTargetMixin,
  WorkbenchStatusEditor,
  WorkbenchViewToggle,
  WorkbenchTargetFilter,
} from '#/components/workbench'
import UserSelect from '#/components/UserSelect.vue'
import LibraryResultUploadDialog from './LibraryResultUploadDialog.vue'
import LibraryRowActions from './LibraryRowActions.vue'
import { listPageMixin } from '#/utils/listPage'
import { listTableLockMixin } from '#/utils/listTableLock'
import { hasAccessCode } from '#/utils/accessCode'
import { rememberDiscoveryFocus } from '#/views/Discovery/workbench/discoveryFocus'
import { getSerumUserName } from '#/utils/serumPermission'
import { applyOptionLists } from '#/utils/optionLists'
import { uniqueNames } from '#/utils/userOptions'
import {
  BUILD_PLASMA_NGS,
  BUILD_PLATE,
  buildTypeLabel,
  buildTypeOptions,
  CATALOG_NAME_FIELDS,
  FIELDS,
  handoffRowsInScope,
  HEADER_MENU_COLUMNS,
  inBuildTypeScope,
  isIndexFieldRecorded,
  isSheetFieldApplicable,
  LIBRARY_VIEW_PREFS_KEY,
  libraryFieldOptions,
  optionsForBuild,
  orderEditorSections,
  plateNumbersFromText,
  plateNumbersText,
  SAMPLE_SOURCE_OPTIONS,
  SHEET_COLUMN_ORDER,
  SHEET_COLUMNS,
  sheetColumnsForBuild,
  STAT_TILES,
  stampQcFields,
  statusTone,
  typeGroup,
  WORKBENCH_COLUMNS,
} from './libraryColumns'
import { filterPrimerCatalog, loadPrimerCatalog } from './primerCatalogOptions'

function emptyQuery() {
  return {
    page: 1,
    limit: 20,
    build_type: '',
    library_code: '',
    source_project_code: '',
    library_batch_no: '',
    target_name: '',
    study_type: '',
    status: '',
    priority: '',
    pm: '',
    owner: '',
    sample_source: '',
    sample_type: '',
    cell_type: '',
    mouse_strain: '',
    source_discovery_id: '',
    notebook_no: '',
    remark: '',
    instrument_on_start: '',
    instrument_on_end: '',
    started_at_start: '',
    started_at_end: '',
    finished_at_start: '',
    finished_at_end: '',
    sort_field: '',
    sort_dir: '',
  }
}

function libraryCodeSeries(seed, count) {
  const text = String(seed || '').trim().toUpperCase()
  const matched = text.match(/^(.*?)(\d+)$/)
  if (!matched || count < 1) return null
  const prefix = matched[1]
  const width = matched[2].length
  const start = Number(matched[2])
  if (!Number.isSafeInteger(start)) return null
  const codes = []
  for (let step = 1; step <= count; step += 1) {
    const next = start + step
    if (!Number.isSafeInteger(next) || next < 0) return null
    const code = `${prefix}${String(next).padStart(width, '0')}`
    if (code.length > FIELDS.library_code.max) return null
    codes.push(code)
  }
  return codes
}

const INDEX_LINKED_KEYS = ['i7_catalog_id', 'i7_name', 'i7_sequence', 'i5_catalog_id', 'i5_name', 'i5_sequence']
const DERIVED_FIELDS = ['status', 'started_at', 'finished_at']
const PEOPLE_FIELDS = ['pm', 'owner', 'qc_owner']
const OPTION_SOURCES = {
  statuses: 'status',
  priorities: 'priority',
  qc_results: 'qc_result',
  cell_types: 'cell_type',
  mouse_strains: 'mouse_strain',
}
const ROW_OPTION_REASONS = { sample_source: 'source', sample_type: 'plasma' }

/** 保存一个字段后后端会联动改写的字段，回包时一起回填。 */
function linkedFields(field) {
  if (field === 'target_codes' || field === 'target_name') return ['target_codes', 'target_name']
  const catalog = CATALOG_NAME_FIELDS[field]
  if (catalog) return [field, catalog.idKey, ...(catalog.sequenceKey ? [catalog.sequenceKey] : [])]
  if (field === 'mouse_strain') return [field, 'sample_type']
  if (field === 'index_mode') return [field, ...INDEX_LINKED_KEYS]
  return [field]
}

export default {
  name: 'LibraryConstructionList',
  mixins: [
    workbenchExcelMixin,
    workbenchDrawerMixin,
    workbenchCrudMixin,
    workbenchTargetMixin,
    listPageMixin,
    workbenchHeaderMenuMixin,
    listTableLockMixin,
  ],
  listFilterKey: 'libraryConstructionList',
  workbenchFields: FIELDS,
  workbenchApi: {
    list: fetchLibraryOrderList,
    save: saveLibraryOrder,
    saveBatch: batchSaveLibraryOrders,
    remove: deleteLibraryOrder,
    export: exportLibraryOrderList,
    exportName: '文库构建',
    columnValues: fetchLibraryOrderColumnValues,
    errors: { load: { default: '加载文库工单失败' } },
  },
  workbenchSheet: { columns: SHEET_COLUMNS, order: SHEET_COLUMN_ORDER },
  components: {
    AdvancedOpsBar,
    ListFilterSelect,
    WorkbenchDrawer,
    WorkbenchDrawerField,
    WorkbenchHeaderFilterChip,
    WorkbenchHeaderMenu,
    WorkbenchLineInput,
    WorkbenchSheet,
    WorkbenchTargetFilter,
    ElButton,
    ElCard,
    ElDatePicker,
    ElDialog,
    ElIcon,
    ElInput,
    ElOption,
    ElPagination,
    ElSelect,
    LibraryResultUploadDialog,
    LibraryRowActions,
    UserSelect,
    Tools,
    WorkbenchDataTable,
    WorkbenchInlineDatePicker,
    WorkbenchPriorityCell,
    WorkbenchStatusEditor,
    WorkbenchViewToggle,
    VxeColumn,
    VxeInput,
    VxeSelect,
  },
  setup() {
    return { Download, fetchLibraryRecordedTargets, Plus, Search, Upload }
  },
  data() {
    return {
      viewPrefsStorageKey: LIBRARY_VIEW_PREFS_KEY,
      optionLists: { ...fieldOptionLists(FIELDS), pm: [], owner: [], qc_owner: [] },
      buildTypeScope: null,
      excelRowSelectKey: 'id',
      showAdvancedOps: false,
      loading: false,
      list: [],
      total: 0,
      stats: Object.fromEntries(STAT_TILES.map((item) => [item.statKey, 0])),
      listQuery: emptyQuery(),
      headerMenuColumns: HEADER_MENU_COLUMNS,
      instrumentRange: [],
      startedRange: [],
      finishedRange: [],
      plateDraft: '',
      catalogQuery: '',
      primerCatalog: [],
      catalogLoading: false,
      consumingCreated: false,
      createVisible: false,
      creating: false,
      resultUploadVisible: false,
      createPick: '',
      listLoaded: false,
      libraryCodeFill: null,
    }
  },
  computed: {
    catalogOptions() {
      return filterPrimerCatalog(this.primerCatalog, this.catalogQuery)
    },
    canEdit() {
      return hasAccessCode(useUserStore().userInfo, LIBRARY_EDIT)
    },
    showLibraryCodeFillHandle() {
      if (!this.canEdit || !this.isExcelMode) return false
      const range = this.normalizedSheetRange()
      if (!range || range.c1 !== range.c2) return false
      if (this.sheetColumns[range.c1]?.key !== 'library_code') return false
      return Boolean(this.libraryCodeFill) || range.r1 === range.r2
    },
    canViewDetail() {
      return hasAccessCode(useUserStore().userInfo, LIBRARY_PAGE_DETAIL)
    },
    canHandoff() {
      return hasAccessCode(useUserStore().userInfo, ...TRANSFECTION_LIBRARY_HANDOFF)
    },
    canViewTransfection() {
      return hasAccessCode(useUserStore().userInfo, TRANSFECTION_PAGE)
    },
    canManageFiles() {
      return hasAccessCode(useUserStore().userInfo, LIBRARY_FILE_MANAGE)
    },
    activeType() {
      return this.listQuery.build_type || ''
    },
    activeStatKey() {
      const type = this.activeType
      if (type === BUILD_PLASMA_NGS && ['nano', 'lite'].includes(this.listQuery.sample_type)) {
        return `${BUILD_PLASMA_NGS}:${this.listQuery.sample_type}`
      }
      return type
    },
    hasAdvancedFilters() {
      const keys = [
        'pm',
        'study_type',
        'sample_type',
        'mouse_strain',
        'cell_type',
        'source_project_code',
        'library_batch_no',
        'source_discovery_id',
        'notebook_no',
        'remark',
      ]
      return keys.some((key) => String(this.listQuery[key] || '').trim())
        || Boolean(this.startedRange?.length)
        || Boolean(this.finishedRange?.length)
    },
    typeSheets() {
      const tones = ['stat-blue', 'stat-purple', 'stat-orange', 'stat-red', 'stat-slate']
      return STAT_TILES
        .map((item, index) => ({ ...item, tone: tones[index % tones.length] }))
        .filter((item) => inBuildTypeScope(this.buildTypeScope, item.value))
    },
    sheetCatalogSelectOptions() {
      const options = this.catalogOptions.map((item) => ({
        label: item.short_sequence ? `${item.name} ${item.short_sequence}` : item.name,
        value: item.name,
      }))
      return options
    },
    sheetCatalogRemoteConfig() {
      return Object.freeze({
        autoLoad: false,
        queryMethod: this.querySheetCatalogOptions,
      })
    },
    workbenchColumns() {
      return WORKBENCH_COLUMNS
    },
    createRows() {
      return handoffRowsInScope(this.buildTypeScope)
    },
    createPicks() {
      return this.createRows.flatMap((row) => row.picks)
    },
    drawerTitle() {
      const row = this.editingRow
      if (!row) return '文库构建工单'
      return row.library_order_id || '系统工单号待生成'
    },
    drawerHeaderFacts() {
      const row = this.editingRow
      if (!row) return []
      const targets = uniqueTargetCodes(row.target_codes)
      const targetText = [row.target_name, targets.join('、')].filter(Boolean).join(' · ')
      return [
        { key: 'type', text: buildTypeLabel(row.build_type) || '类型待定' },
        { key: 'target', text: targetText || '靶点待关联' },
      ]
    },
    editorSections() {
      return orderEditorSections(typeGroup(this.editingRow?.build_type), this.editingRow)
    },
  },
  created() {
    this.rebuildSheetColumns()
    this.loadOptionLists()
    this.getList({ flushEditor: false }).finally(() => {
      this.listLoaded = true
      this.consumeCreatedQuery()
    })
  },
  activated() {
    if (this.listLoaded && this.isListDataStale()) {
      this.getList({ flushEditor: false })
    }
    this.consumeCreatedQuery()
  },
  beforeUnmount() {
    this.stopLibraryCodeFill()
  },
  deactivated() {
    this.stopLibraryCodeFill()
  },
  watch: {
    '$route.query.created'() {
      this.consumeCreatedQuery()
    },
    'listQuery.build_type'() {
      this.clearSheetRange()
      this.rebuildSheetColumns()
    },
  },
  methods: {
    workbenchRowClassName({ row, rowIndex }) {
      return dateBreakRowClass({
        list: this.list,
        row,
        rowIndex,
        field: 'instrument_on',
        editingId: this.editingId,
      })
    },
    statusTone,
    async filterCatalog(query = '') {
      this.catalogQuery = String(query || '')
      if (!this.catalogQuery.trim() || this.primerCatalog.length) return
      this.catalogLoading = true
      try {
        this.primerCatalog = await loadPrimerCatalog()
      } catch (error) {
        this.primerCatalog = []
        notifyApiError(error, { messages: { default: '加载引物与 Index 字典失败，请稍后重试' } })
      } finally {
        this.catalogLoading = false
      }
    },
    onCatalogChange(row, field, value) {
      if (!row) return
      row[field.key] = value || null
      // 名称没变也要存：后端按名称回绑字典 ID（纯文本同名条目选字典时才会带上 id）。
      return this.persistRow(row, field.key, { force: true })
    },
    canEditField(row, key) {
      if (!this.canEdit) return false
      if (key === 'build_type') return !this.activeType && row?.status === '待处理'
      return true
    },
    sheetCellLockReason(row, key) {
      const label = this.sheetColumnLabel(key)
      if (!this.canEdit) return '你没有编辑权限'
      if (!this.canEditField(row, key)) {
        return this.activeType ? '按建库类型筛选时不能改建库类型' : '只有待处理的工单能改建库类型'
      }
      if (!isSheetFieldApplicable(row?.build_type, key)) {
        return `${buildTypeLabel(row.build_type) || '当前建库类型'}没有「${label}」`
      }
      if (!isIndexFieldRecorded(row?.build_type, row?.index_mode, key)) {
        return `当前 Barcode 方式不填写「${label}」`
      }
      if (key === 'plate_nos' && Array.isArray(row?.plate_nos) && row.plate_nos.length > 1) {
        return '单元格只能写一行，多个板号请在详情里修改'
      }
      return this.sheetReadonlyLockReason(key)
    },
    async onBuildTypeFilter(value) {
      if (this.isExcelMode && !await this.flushPendingSheetEdits()) return
      const terms = Array.isArray(value) ? value.filter(Boolean) : (value ? [value] : [])
      const next = terms.length <= 1 ? (terms[0] || '') : terms
      const leavingPlasma = this.listQuery.build_type === BUILD_PLASMA_NGS
        && next !== BUILD_PLASMA_NGS
        && ['nano', 'lite'].includes(this.listQuery.sample_type)
      this.listQuery.build_type = next
      if (leavingPlasma) this.listQuery.sample_type = ''
      if (terms.length === 1 && this.listQuery.sample_source) {
        const allowed = optionsForBuild(SAMPLE_SOURCE_OPTIONS, terms[0])
          .some((item) => item.value === this.listQuery.sample_source)
        if (!allowed) this.listQuery.sample_source = ''
      }
      this.handleFilter()
    },
    async selectType(tile) {
      if (this.isExcelMode && !await this.flushPendingSheetEdits()) return
      const active = this.activeStatKey === tile.statKey
      const leavingPlasma = this.listQuery.build_type === BUILD_PLASMA_NGS && Boolean(this.listQuery.sample_type)
      if (active) {
        this.listQuery.build_type = ''
        if (tile.sampleType) this.listQuery.sample_type = ''
      } else {
        this.listQuery.build_type = tile.value
        if (tile.sampleType) this.listQuery.sample_type = tile.sampleType
        else if (leavingPlasma) this.listQuery.sample_type = ''
      }
      this.handleFilter()
    },
    onLibraryCodeFillStart() {
      const range = this.normalizedSheetRange()
      if (!range || !this.showLibraryCodeFillHandle) return
      this.libraryCodeFill = { rowIndex: range.r1, colIndex: range.c1 }
      window.addEventListener('mousemove', this.onLibraryCodeFillMove)
      window.addEventListener('mouseup', this.onLibraryCodeFillEnd)
    },
    onLibraryCodeFillMove(event) {
      const fill = this.libraryCodeFill
      if (!fill) return
      const hit = this.hitSheetCell(event.target)
      if (!hit || hit.colIndex !== fill.colIndex) return
      this.setSheetRange({
        r1: fill.rowIndex,
        c1: fill.colIndex,
        r2: hit.rowIndex,
        c2: fill.colIndex,
      })
    },
    stopLibraryCodeFill() {
      window.removeEventListener('mousemove', this.onLibraryCodeFillMove)
      window.removeEventListener('mouseup', this.onLibraryCodeFillEnd)
      this.libraryCodeFill = null
    },
    async onLibraryCodeFillEnd() {
      const fill = this.libraryCodeFill
      const endIndex = this.sheetRange?.r2
      this.stopLibraryCodeFill()
      if (!fill) return
      if (endIndex == null || endIndex === fill.rowIndex) {
        this.setSheetRange({
          r1: fill.rowIndex,
          c1: fill.colIndex,
          r2: fill.rowIndex,
          c2: fill.colIndex,
        })
        return
      }
      await this.fillLibraryCodes(fill.rowIndex, endIndex, fill.colIndex)
    },
    /** 从种子格往拖动方向逐格加 1：默认新工单在上，从最近的编号往上拖，编号就和创建先后一致。 */
    async fillLibraryCodes(startIndex, endIndex, colIndex) {
      if (!await this.flushPendingSheetEdits() || !await this.awaitRowSaves()) {
        this.setSheetRange({ r1: startIndex, c1: colIndex, r2: startIndex, c2: colIndex })
        return
      }
      const column = this.sheetColumns[colIndex]
      const seedRow = this.list[startIndex]
      if (!seedRow || column?.key !== 'library_code') return
      const targets = endIndex > startIndex
        ? this.list.slice(startIndex + 1, endIndex + 1)
        : this.list.slice(endIndex, startIndex).reverse()
      if (targets.some((row) => this.isSheetCellLocked(row, 'library_code'))) {
        ElMessage.warning('选中的建库编号有不能修改的格子，本次未填充')
        this.setSheetRange({ r1: startIndex, c1: colIndex, r2: startIndex, c2: colIndex })
        return
      }
      const codes = libraryCodeSeries(seedRow.library_code, targets.length)
      if (!codes) {
        ElMessage.warning('建库编号末尾要有数字才能填充')
        this.setSheetRange({ r1: startIndex, c1: colIndex, r2: startIndex, c2: colIndex })
        return
      }
      const overwritten = targets.filter((row, index) => row.library_code && row.library_code !== codes[index]).length
      if (overwritten) {
        try {
          await ElMessageBox.confirm(
            `其中 ${overwritten} 行已有建库编号，填充后会被改掉。`,
            '覆盖确认',
            { type: 'warning', confirmButtonText: '覆盖' },
          )
        } catch {
          this.setSheetRange({ r1: startIndex, c1: colIndex, r2: startIndex, c2: colIndex })
          return
        }
      }
      try {
        const saved = await batchSaveLibraryOrders({
          items: targets.map((row, index) => this.rowSavePayload({ ...row, library_code: codes[index] }, ['library_code'])),
        })
        const savedById = new Map((saved?.items || []).map((item) => [item.id, item]))
        targets.forEach((row) => {
          const item = savedById.get(row.id)
          if (item) this.applySavedFields(item, ['library_code'])
        })
        ElMessage.success(`已填充 ${targets.length} 个建库编号`)
        this.setSheetRange({ r1: startIndex, c1: colIndex, r2: endIndex, c2: colIndex })
      } catch (error) {
        notifyApiError(error, { messages: { default: '建库编号填充失败' } })
        await this.getList({ flushEditor: false, silent: true })
        this.setSheetRange({ r1: startIndex, c1: colIndex, r2: startIndex, c2: colIndex })
      }
    },
    resetFilters() {
      this.listQuery = emptyQuery()
      this.instrumentRange = []
      this.startedRange = []
      this.finishedRange = []
      this.clearHeaderFilters()
      this.persistListFilters()
      this.getList()
    },
    listFilterExtras() {
      return {
        instrumentRange: this.instrumentRange,
        startedRange: this.startedRange,
        finishedRange: this.finishedRange,
      }
    },
    restoreListFilterExtras(state) {
      if (Array.isArray(state.instrumentRange)) this.instrumentRange = state.instrumentRange
      if (Array.isArray(state.startedRange)) this.startedRange = state.startedRange
      if (Array.isArray(state.finishedRange)) this.finishedRange = state.finishedRange
    },
    buildQuery() {
      const [instrumentStart, instrumentEnd] = this.instrumentRange || []
      const [startedStart, startedEnd] = this.startedRange || []
      const [finishedStart, finishedEnd] = this.finishedRange || []
      const payload = {
        ...this.listQuery,
        instrument_on_start: instrumentStart || '',
        instrument_on_end: instrumentEnd || '',
        started_at_start: startedStart || '',
        started_at_end: startedEnd || '',
        finished_at_start: finishedStart || '',
        finished_at_end: finishedEnd || '',
      }
      const fieldFilters = this.headerFilterPayload()
      if (fieldFilters.length) payload.field_filters = fieldFilters
      return payload
    },
    fieldOptions(field, row) {
      return (row && libraryFieldOptions(field, row)) ?? this.optionLists[field.key] ?? field.options ?? []
    },
    async loadOptionLists() {
      try {
        const data = await fetchLibraryOrderOptions()
        this.buildTypeScope = data?.build_type_scope ?? null
        this.optionLists.build_type = buildTypeOptions(this.buildTypeScope)
        const people = uniqueNames(data?.people || [])
        PEOPLE_FIELDS.forEach((key) => { this.optionLists[key] = people })
        applyOptionLists(this.optionLists, data, OPTION_SOURCES)
      } catch (error) {
        notifyApiError(error, { messages: { default: '加载文库选项失败，暂用本地默认选项' } })
      }
    },
    availableSheetColumns() {
      return sheetColumnsForBuild(this.activeType)
    },
    onDrawerRowSynced(row) {
      this.plateDraft = plateNumbersText(row?.plate_nos)
    },
    async saveRowField(row, field, { force = false } = {}) {
      if (!this.canEdit || !row?.id) return
      if (!this.normalizeDrawerValue(row, field)) return
      const valueKeys = this.drawerValueKeys(field)
      if (!force && this.rowFieldsUnchanged(row, valueKeys)) return
      const qcFields = field === 'qc_result'
        ? stampQcFields(row, getSerumUserName(useUserStore().userInfo))
        : []
      const fields = [...valueKeys, ...qcFields]
      return this.submitRowFields(row, fields, {
        messages: { default: CATALOG_NAME_FIELDS[field] ? '保存引物或Index失败' : '保存失败' },
        // 建库类型会联动清空不适用字段，因此需整行回填。
        applyFields: field === 'build_type' ? null : fields,
      })
    },
    savedFieldKeys(fields) {
      return new Set([...fields.flatMap(linkedFields), ...DERIVED_FIELDS])
    },
    onPlateDraftInput(value) {
      if (!this.editingRow) return
      this.plateDraft = value
      this.editingRow.plate_nos = plateNumbersFromText(value)
    },
    openSourceDiscovery(discoveryId) {
      const id = String(discoveryId || '').trim()
      if (!id) return
      rememberDiscoveryFocus(id)
      this.$router.push({ name: 'DiscoveryWorkbench' })
    },
    openResult(row) {
      if (!this.canViewDetail) {
        ElMessage.warning('您没有权限查看文库详情')
        return
      }
      this.$router.push({ path: '/molecular-cell/library-construction/result', query: { id: row.id } })
    },
    async handleDownstreamHandoff(row) {
      if (!this.canHandoff) {
        ElMessage.warning('您没有权限交接文库工单')
        return
      }
      if (row.build_type !== BUILD_PLATE) {
        ElMessage.info('只有单细胞孔板工单交接到转染与表达')
        return
      }
      try {
        await ElMessageBox.confirm(
          `把 ${row.library_code || row.library_order_id} 交接到转染与表达？会新建一条 PCR 转染工单，带上项目、靶点、PM、小鼠品系和板号；交接后这条文库工单不能删除。`,
          '交接确认',
          { type: 'warning', confirmButtonText: '交接' },
        )
      } catch {
        return
      }
      if (!await this.flushEditorForAction(row)) return
      let created
      try {
        created = await handoffLibraryToTransfection(row.id)
      } catch (error) {
        notifyApiError(error, { messages: { default: '交接失败' } })
        return
      }
      const code = created.transfection_order_id
      if (!this.canViewTransfection) {
        ElMessage.success(`已交接为转染工单 ${code}`)
        return
      }
      try {
        await ElMessageBox.confirm(`已交接为转染工单 ${code}，现在去转染与表达查看？`, '交接成功', {
          type: 'success',
          confirmButtonText: '去查看',
          cancelButtonText: '留在本页',
        })
      } catch {
        return
      }
      this.$router.push({ name: 'TransfectionList', query: { order: code } })
    },
    deleteConfirmText(row) {
      return `确认删除 ${row.library_code || row.library_order_id || '这条工单'}？工单及其独占质检文件将一并删除，且无法恢复。`
    },
    handleCreate() {
      if (!this.canEdit) {
        ElMessage.warning('您没有权限新建文库工单')
        return
      }
      const matched = this.createPicks.filter((item) => {
        if (item.buildType !== this.activeType) return false
        return !item.sampleType || item.sampleType === this.listQuery.sample_type
      })
      this.createPick = (matched[0] || this.createPicks[0])?.id || ''
      this.createVisible = true
    },
    async confirmCreate() {
      if (this.creating) return
      const pick = this.createPicks.find((item) => item.id === this.createPick)
      if (!pick) {
        ElMessage.warning('请选择类型')
        return
      }
      this.creating = true
      try {
        const saved = await saveLibraryOrder({
          build_type: pick.buildType,
          sample_source: pick.source,
          ...(pick.sampleType ? { sample_type: pick.sampleType } : {}),
        })
        this.createVisible = false
        if (this.isExcelMode) {
          this.listQuery.page = 1
          await this.getList({ flushEditor: false })
          return
        }
        await this.getList({ flushEditor: false })
        this.openDrawer(saved)
      } catch (error) {
        notifyApiError(error, { messages: { default: '新建失败' } })
      } finally {
        this.creating = false
      }
    },
    async consumeCreatedQuery() {
      if (this.$route.name !== 'LibraryConstructionList' || this.consumingCreated) return
      const raw = this.$route.query.created
      const id = Number(Array.isArray(raw) ? raw[0] : raw)
      if (!Number.isSafeInteger(id) || id <= 0) return
      this.consumingCreated = true
      try {
        const cachedRaw = sessionStorage.getItem(LIBRARY_CREATED_KEY)
        sessionStorage.removeItem(LIBRARY_CREATED_KEY)
        const nextQuery = { ...this.$route.query }
        delete nextQuery.created
        await this.$router.replace({ path: this.$route.path, query: nextQuery })
        await this.getList({ flushEditor: false })
        const row = this.list.find((item) => item.id === id)
        if (row) {
          this.openDrawer(row)
          return
        }
        if (cachedRaw) {
          try {
            const cached = JSON.parse(cachedRaw)
            if (cached?.id === id) this.openDrawer(cached)
          } catch {
            /* 缓存无效时仅使用列表数据。 */
          }
        }
      } finally {
        this.consumingCreated = false
      }
    },
    isSheetCustomColumn(column) {
      return column.edit === 'catalog'
    },
    sheetCellValue(row, key) {
      return key === 'plate_nos' ? plateNumbersText(row.plate_nos) : row[key]
    },
    sheetFormatter(column) {
      return column.key === 'plate_nos' ? this.formatSheetCellValue : this.sheetTypeFormatter(column)
    },
    querySheetCatalogOptions({ searchValue }) {
      return this.filterCatalog(searchValue)
    },
    normalizeSheetSequence(key, text) {
      const raw = String(text ?? '').replace(/\s+/g, '').toUpperCase()
      if (!raw) return { ok: true, value: null }
      if (raw.length > this.sheetStringMax[key]) return { ok: false, reason: 'length' }
      return /^[ACGTRYSWKMBDHVN]+$/.test(raw) ? { ok: true, value: raw } : { ok: false, reason: 'sequence' }
    },
    coerceSheetValue(key, text, row) {
      if (key === 'plate_nos') {
        return { ok: true, value: plateNumbersFromText(Array.isArray(text) ? text.join('\n') : text) }
      }
      if (key === 'i7_sequence' || key === 'i5_sequence') return this.normalizeSheetSequence(key, text)
      if (key === 'library_code') return this.coerceSheetField(key, String(text ?? '').toUpperCase(), row)
      const result = this.coerceSheetField(key, text, row)
      if (result.reason === 'option' && ROW_OPTION_REASONS[key] && this.coerceSheetField(key, text).ok) {
        return { ok: false, reason: ROW_OPTION_REASONS[key] }
      }
      return result
    },
    sheetPasteIdentityKey() {
      return 'library_order_id'
    },
    sheetPasteLockedReason(row, key) {
      if (!isSheetFieldApplicable(row?.build_type, key)) return 'inapplicable'
      if (!isIndexFieldRecorded(row?.build_type, row?.index_mode, key)) return 'index'
      return 'locked'
    },
    expandSheetPasteFields(row, fields) {
      if (fields.has('qc_result')) {
        stampQcFields(row, getSerumUserName(useUserStore().userInfo)).forEach((key) => fields.add(key))
      }
    },
    applySheetPasteSaved(saved, fields = []) {
      this.applySavedFields(saved, fields.includes('build_type') ? undefined : fields)
    },
    sheetValidationExtraMessage(_key, reason, label) {
      if (reason === 'sequence') return `${label}只能包含 IUPAC 碱基字符`
      if (reason === 'index') return `当前 Barcode 方式不填写「${label}」`
      if (reason === 'plasma') return '浆细胞 NGS 的样品类型只能是 Nano 或 Lite'
      if (reason === 'source') return '样品来源与当前建库类型不匹配'
      if (reason === 'inapplicable') return `当前建库类型没有「${label}」`
      return ''
    },
  },
}
</script>

<style scoped src="#/components/workbench/workbenchPanel.css"></style>
<style src="#/components/workbench/workbenchDrawer.css"></style>
<style scoped>
.table-card :deep(tr.is-date-break > td) {
  border-top: 3px solid #2563eb !important;
}
.library-code-fill-handle {
  position: absolute;
  right: -5px;
  bottom: -5px;
  z-index: 1;
  width: 8px;
  height: 8px;
  padding: 0;
  pointer-events: auto;
  cursor: crosshair;
  background: var(--el-color-primary);
  border: 1px solid var(--el-bg-color);
}

.library-order-page {
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
  min-width: 100px;
}

.catalog-sequence {
  float: right;
  margin-left: 16px;
  color: var(--el-text-color-secondary);
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 12px;
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

.inline-select,
.inline-date {
  width: 100%;
  max-width: 100%;
}

.inline-date {
  --el-date-editor-width: 100%;
}

.inline-select :deep(.el-select__wrapper) {
  min-height: 28px;
  padding: 0 8px;
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
  line-height: 20px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-light);
  border-radius: 5px;
}

.source-link.is-link {
  cursor: pointer;
}

/* 只读用户的抽屉整组禁用，禁用的输入框吃掉点击，点击要落到外层 div 上 */
.source-link.is-link :deep(.el-input) {
  pointer-events: none;
}

.source-link-action {
  color: var(--el-color-primary);
  font-size: 12px;
  font-weight: 600;
}

.primer-matrix {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr) minmax(0, 1fr) 72px;
  gap: 8px;
  align-items: center;
  width: 100%;
}

.primer-matrix-heading {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 20px;
  text-align: center;
}

.primer-chain {
  color: var(--el-text-color-regular);
  font-size: 13px;
  text-align: center;
}

.create-rows {
  border-top: 1px solid var(--el-border-color-lighter);
}

.create-row {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  min-height: 52px;
  padding: 8px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.create-name {
  font-size: 14px;
  font-weight: 600;
}

.create-name.tone-primary { color: var(--el-color-primary); }
.create-name.tone-success { color: var(--el-color-success); }
.create-name.tone-warning { color: var(--el-color-warning); }
.create-name.tone-purple { color: #7c5cf0; }

.create-picks {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.create-chip {
  height: 30px;
  padding: 0 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  background: var(--el-fill-color-blank);
  color: var(--el-text-color-regular);
  font-size: 13px;
  cursor: pointer;
}

.create-chip.on {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
}

html.dark .drawer-header-facts .is-type {
  color: var(--el-text-color-regular);
}

</style>
