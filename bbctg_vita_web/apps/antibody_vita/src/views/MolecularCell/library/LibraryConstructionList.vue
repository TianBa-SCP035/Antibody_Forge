<template>
  <div class="library-order-page">
    <AdvancedOpsBar v-model="showAdvancedOps">
      <template v-if="showAdvancedOps">
        <SerumUserSelect v-model="listQuery.pm" :options="selectedUserOptions(listQuery.pm)" placeholder="PM" clearable @change="handleFilter" />
        <el-input v-model="listQuery.study_type" clearable placeholder="课题类型" @keyup.enter="handleFilter" @clear="handleFilter" />
        <el-select v-model="listQuery.sample_type" clearable placeholder="样品类型" @change="handleFilter">
          <el-option v-for="item in sampleTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="listQuery.mouse_model" clearable placeholder="归类鼠型" @change="handleFilter">
          <el-option v-for="item in mouseCategoryOptions" :key="item" :label="mouseCategoryLabel(item)" :value="item" />
        </el-select>
        <el-input v-model="listQuery.cell_type" clearable placeholder="细胞类型" @keyup.enter="handleFilter" @clear="handleFilter" />
        <el-input v-model="listQuery.source_discovery_id" clearable placeholder="来源发现 ID" @keyup.enter="handleFilter" @clear="handleFilter" />
        <el-input v-model="listQuery.notebook_no" clearable placeholder="实验记录本号" @keyup.enter="handleFilter" @clear="handleFilter" />
        <el-input v-model="listQuery.remark" clearable placeholder="备注" @keyup.enter="handleFilter" @clear="handleFilter" />
        <el-date-picker
          v-model="startedRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          start-placeholder="开始日起"
          end-placeholder="开始日止"
          @change="handleFilter"
        />
        <el-date-picker
          v-model="finishedRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          start-placeholder="完成日起"
          end-placeholder="完成日止"
          @change="handleFilter"
        />
      </template>
      <template #actions>
        <el-button v-if="!isExcelMode" @click="openColumnPicker">显示字段</el-button>
        <el-button type="warning" :icon="Download" @click="handleListExport">列表导出</el-button>
      </template>
    </AdvancedOpsBar>

    <section class="workbench-panel">
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

      <div class="stats-strip">
        <div
          v-for="item in typeSheets"
          :key="item.value"
          class="stat-tile stat-tile-interactive"
          :class="[item.tone, { 'stat-tile-active': activeType === item.value }]"
          @click="selectType(item.value)"
        >
          <span class="stat-copy">
            <span class="stat-label">{{ item.label }}</span>
            <small class="text-hint">{{ item.hint }}</small>
          </span>
          <strong class="stat-value">{{ stats[item.value] || 0 }}</strong>
        </div>
      </div>

      <div class="filter-strip list-filter-controls">
        <el-input
          v-model="listQuery.keyword"
          class="filter-item filter-keyword"
          clearable
          placeholder="项目编号 / 建库编号 / 建库批号"
          :prefix-icon="Search"
          @keyup.enter="handleFilter"
          @clear="handleFilter"
        />
        <el-select v-model="listQuery.status" class="filter-item" clearable placeholder="状态" @change="handleFilter">
          <el-option v-for="item in statusOptions" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select v-model="listQuery.priority" class="filter-item" clearable placeholder="优先级" @change="handleFilter">
          <el-option v-for="item in priorityOptions" :key="item" :label="item" :value="item" />
        </el-select>
        <SerumUserSelect
          v-model="listQuery.owner"
          class="filter-item"
          :options="selectedUserOptions(listQuery.owner)"
          placeholder="负责人"
          clearable
          @change="handleFilter"
        />
        <el-select v-model="listQuery.sample_source" class="filter-item" clearable placeholder="样品来源" @change="handleFilter">
          <el-option v-for="item in sampleSourceOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select
          v-model="listQuery.target"
          class="filter-item"
          clearable
          filterable
          remote
          remote-show-suffix
          :remote-method="searchTargetFilter"
          :loading="targetFilterLoading"
          placeholder="搜索靶点"
          @change="onTargetFilterChange"
        >
          <el-option
            v-for="item in targetFilterOptions"
            :key="item.snum"
            :label="`${item.name}（${item.snum}）`"
            :value="item.snum"
          >
            <span>{{ item.name }}</span>
            <span class="target-option-code">{{ item.snum }}</span>
          </el-option>
        </el-select>
        <el-date-picker
          v-model="instrumentRange"
          class="filter-range"
          type="daterange"
          value-format="YYYY-MM-DD"
          range-separator="至"
          start-placeholder="上机日起"
          end-placeholder="上机日止"
          @change="handleFilter"
        />
        <div class="filter-actions list-filter-actions">
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
    </section>

    <el-card shadow="never" class="table-card list-table-card">
      <WorkbenchDataTable
        v-if="viewMode === 'workbench'"
        ref="workbenchTable"
        v-loading="loading"
        storage-key="libraryConstructionWorkbench.v4"
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
        :row-class-name="workbenchRowClassName"
        @row-click="onWorkbenchRowClick"
        @row-contextmenu="onWorkbenchRowContextMenu"
      >
        <template #build_type="{ row }">{{ buildTypeLabel(row.build_type) || '—' }}</template>
        <template #mouse_model="{ row }">{{ mouseCategoryLabel(row.mouse_model) || '—' }}</template>
        <template #sample_source="{ row }">{{ sampleSourceLabel(row.sample_source) || '—' }}</template>
        <template #sample_type="{ row }">{{ sampleTypeLabel(row.sample_type) || '—' }}</template>
        <template #priority="{ row }">
          <el-select
            v-if="canEdit"
            v-model="row.priority"
            size="small"
            class="inline-select"
            @click.stop
            @change="persistRow(row, 'priority')"
          >
            <el-option v-for="item in priorityOptions" :key="item" :label="item" :value="item" />
          </el-select>
          <span v-else>{{ row.priority || '—' }}</span>
        </template>
        <template #status="{ row }">
          <WorkbenchStatusEditor
            :value="row.status || '待处理'"
            :options="statusOptions"
            :type="statusTone(row.status)"
            :editable="canEdit"
            @change="(value) => updateStatus(row, value)"
          />
        </template>
        <template #received_on="{ row }">
          <el-date-picker
            v-model="row.received_on"
            class="inline-date"
            type="date"
            size="small"
            value-format="YYYY-MM-DD"
            :disabled="!canEdit"
            @click.stop
            @change="persistRow(row, 'received_on')"
          />
        </template>
        <template #actions="{ row }">
          <LibraryRowActions
            :row="row"
            :can-edit="canEdit"
            :can-handoff="canEdit"
            :can-view="canViewDetail"
            @qc="openResult"
            @handoff="handleDownstreamHandoff"
            @delete="handleDelete"
          />
        </template>
      </WorkbenchDataTable>

      <div
        v-else
        ref="sheetWrap"
        class="sheet-wrap"
        :class="{ 'is-column-moving': sheetDragMode === 'move-column' }"
        tabindex="0"
        @copy="onSheetCopy"
        @dblclick.capture="onSheetDblClickCapture"
        @keydown.capture="onSheetKeydownCapture"
        @compositionend.capture="onSheetCompositionEnd"
        @mousedown="onSheetWrapMouseDown"
        @mouseover="onSheetWrapMouseOver"
        @selectstart="onSheetSelectStart"
      >
        <div ref="sheetTableStage" class="sheet-table-stage">
          <vxe-table
            :key="sheetColumnOrderKey"
            ref="sheetTable"
            v-loading="loading"
            :data="list"
            border
            show-overflow
            size="small"
            :row-config="{ keyField: 'id', isHover: true, height: 48 }"
            :column-config="{ resizable: true }"
            :mouse-config="{ selected: true }"
            :keyboard-config="sheetKeyboardConfig"
            :clip-config="{ isCopy: false, isCut: false, isPaste: false }"
            :edit-config="sheetEditConfig"
            :header-cell-class-name="sheetHeaderCellClassName"
            :cell-class-name="sheetCellClassName"
            @scroll="onSheetScroll"
            @edit-actived="onSheetEditActived"
            @edit-closed="onSheetEditClosed"
            @cell-delete-value="onSheetEditClosed"
            @cell-selected="onSheetCellSelected"
          >
            <template v-for="column in sheetColumns" :key="column.key">
              <vxe-column
                v-if="column.edit === 'target'"
                :field="column.key"
                :title="sheetColumnTitle(column)"
                :min-width="column.minWidth || 120"
                :edit-render="{ name: 'VxeInput' }"
                :formatter="sheetFormatter(column)"
              >
                <template #edit="{ row }">
                  <VxeInput
                    :model-value="sheetTargetDirectValue(row, column.key)"
                    class-name="sheet-grid-editor"
                    @update:model-value="setSheetTargetDirectValue(row, column.key, $event)"
                  />
                </template>
              </vxe-column>
              <vxe-column
                v-else-if="isSheetChoiceColumn(column)"
                :field="column.key"
                :title="sheetColumnTitle(column)"
                :min-width="column.minWidth || 120"
                :edit-render="{ name: 'VxeInput' }"
                :formatter="sheetFormatter(column)"
              >
                <template #edit="{ row }">
                  <VxeSelect
                    v-if="sheetEditSource === 'dblclick' && isSheetChoiceForRow(column, row)"
                    v-model="row[column.key]"
                    class-name="sheet-grid-editor sheet-picker-control"
                    :filterable="isUserColumn(column)"
                    :options="sheetChoiceSelectOptions(column, row)"
                    :popup-config="{ className: 'sheet-picker-popup', placement: 'bottom', width: 220 }"
                  />
                  <VxeInput
                    v-else
                    :model-value="sheetDirectTextValue(row, column.key)"
                    class-name="sheet-grid-editor"
                    @update:model-value="setSheetDirectValue(row, column.key, $event)"
                  />
                </template>
              </vxe-column>
              <vxe-column
                v-else
                :field="column.key"
                :title="sheetColumnTitle(column)"
                :min-width="column.minWidth || column.width || 120"
                :edit-render="sheetEditRender(column)"
                :formatter="sheetFormatter(column)"
              />
            </template>
            <vxe-column title="操作" width="240" fixed="right" align="center">
              <template #default="{ row }">
                <div @mousedown.stop @click.stop>
                  <LibraryRowActions
                    :row="row"
                    :can-edit="canEdit"
                    :can-handoff="canEdit"
                    :can-view="canViewDetail"
                    @qc="openResult"
                    @handoff="handleDownstreamHandoff"
                    @delete="handleDelete"
                  />
                </div>
              </template>
            </vxe-column>
          </vxe-table>
          <div ref="sheetRangeOverlay" class="sheet-range-overlay" aria-hidden="true" />
          <div ref="sheetColumnDropLine" class="sheet-column-drop-line" aria-hidden="true" />
          <div ref="sheetColumnGhost" class="sheet-column-ghost" aria-hidden="true" />
        </div>
      </div>

      <el-pagination
        v-show="total > 0"
        v-model:current-page="listQuery.page"
        v-model:page-size="listQuery.limit"
        :total="total"
        :page-sizes="[20, 50, 100, 200]"
        layout="total, sizes, prev, pager, next, jumper"
        class="list-pagination"
        @size-change="handleFilter"
        @current-change="getList"
      />
    </el-card>

    <el-drawer
      v-model="drawerVisible"
      size="560px"
      append-to-body
      :modal="false"
      :show-close="false"
      :lock-scroll="false"
      title="文库工单"
      modal-class="workbench-drawer-overlay"
      class="workbench-drawer"
    >
      <template #header="{ close, titleId }">
        <div class="drawer-header">
          <div class="drawer-heading">
            <h2 :id="titleId" class="drawer-title">{{ drawerTitle }}</h2>
            <div v-if="drawerHeaderFacts.length" class="drawer-header-facts">
              <span
                v-for="fact in drawerHeaderFacts"
                :key="fact.key"
                :class="{ 'is-type': fact.key === 'type' }"
              >
                {{ fact.text }}
              </span>
            </div>
          </div>
          <button type="button" class="drawer-close" aria-label="关闭" @click="close">×</button>
        </div>
      </template>
      <div v-if="editingRow" class="drawer-toolbar">
        <div class="drawer-toolbar-actions">
          <LibraryRowActions
            :row="editingRow"
            :can-edit="canEdit"
            :can-handoff="canEdit"
            :can-view="canViewDetail"
            @qc="openResult"
            @handoff="handleDownstreamHandoff"
            @delete="handleDelete"
          />
        </div>
        <div class="drawer-nav">
          <el-button size="small" :disabled="!hasPrevEditor" @click="shiftEditor(-1)">上一条</el-button>
          <el-button size="small" :disabled="!hasNextEditor" @click="shiftEditor(1)">下一条</el-button>
        </div>
      </div>
      <div v-if="editingRow" class="drawer-fields">
        <el-form label-width="92px" size="small" class="drawer-form" @submit.prevent>
          <article
            v-for="section in editorSections"
            :key="section.title"
            class="drawer-card"
            :class="{ 'is-queue': section.queue }"
          >
            <h3 class="drawer-card-title">{{ section.title }}</h3>
            <div class="drawer-card-grid">
              <el-form-item
                v-for="field in section.fields"
                :key="field.key"
                :label="field.label"
                :label-width="field.type === 'primer-matrix' ? '0' : undefined"
                :class="['drawer-field', field.wide ? 'is-wide' : '']"
              >
                <el-date-picker
                  v-if="field.type === 'date'"
                  v-model="editingRow[field.key]"
                  type="date"
                  value-format="YYYY-MM-DD"
                  format="YYYY-MM-DD"
                  placeholder="选择日期"
                  style="width: 100%"
                  :disabled="!canEdit"
                  @change="persistRow(editingRow, field.key)"
                />
                <el-date-picker
                  v-else-if="field.type === 'datetime'"
                  v-model="editingRow[field.key]"
                  type="datetime"
                  value-format="YYYY-MM-DD HH:mm:ss"
                  format="YYYY-MM-DD HH:mm"
                  placeholder="选择时间"
                  style="width: 100%"
                  :disabled="!canEdit"
                  @change="persistRow(editingRow, field.key)"
                />
                <div v-else-if="field.type === 'primer-matrix'" class="primer-matrix">
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
                      remote
                      reserve-keyword
                      :loading="catalogLoading"
                      :remote-method="searchCatalog"
                      :disabled="!canEdit"
                      @change="(value) => onCatalogChange(editingRow, primer.forward, value)"
                      @visible-change="(visible) => visible && searchCatalog('')"
                    >
                      <el-option v-for="item in catalogOptions" :key="item.id" :label="item.name" :value="item.name" />
                    </el-select>
                    <el-select
                      v-model="editingRow[primer.reverse.key]"
                      allow-create
                      clearable
                      filterable
                      remote
                      reserve-keyword
                      :loading="catalogLoading"
                      :remote-method="searchCatalog"
                      :disabled="!canEdit"
                      @change="(value) => onCatalogChange(editingRow, primer.reverse, value)"
                      @visible-change="(visible) => visible && searchCatalog('')"
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
                <WorkbenchTargetSelect
                  v-else-if="field.type === 'target'"
                  v-model="editingRow.target_codes"
                  :display-name="editingRow.target_name"
                  :placeholder="editingRow.target_name ? '' : '搜索靶点'"
                  :disabled="!canEdit"
                  @change="(payload) => onDrawerTargetChange(editingRow, payload)"
                />
                <SerumUserSelect
                  v-else-if="field.type === 'user'"
                  v-model="editingRow[field.key]"
                  :options="selectedUserOptions(editingRow[field.key])"
                  :placeholder="`选择${field.label}`"
                  :disabled="!canEdit"
                  clearable
                  @change="persistRow(editingRow, field.key)"
                />
                <el-input
                  v-else-if="field.type === 'source-link'"
                  :model-value="editingRow[field.key] || '手工创建'"
                  readonly
                  :class="{ 'source-link-input': Boolean(editingRow[field.key]) }"
                  @click="openSourceDiscovery(editingRow[field.key])"
                >
                  <template v-if="editingRow[field.key]" #suffix>
                    <span class="source-link-action">查看</span>
                  </template>
                </el-input>
                <el-select
                  v-else-if="field.type === 'catalog-select'"
                  v-model="editingRow[field.key]"
                  allow-create
                  clearable
                  filterable
                  remote
                  reserve-keyword
                  :loading="catalogLoading"
                  :remote-method="searchCatalog"
                  style="width: 100%"
                  :disabled="!canEdit"
                  @change="(value) => onCatalogChange(editingRow, field, value)"
                  @visible-change="(visible) => visible && searchCatalog('')"
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
                <el-select
                  v-else-if="field.type === 'source-select'"
                  v-model="editingRow[field.key]"
                  clearable
                  style="width: 100%"
                  :disabled="!canEdit"
                  @change="persistRow(editingRow, field.key)"
                >
                  <el-option v-for="item in sourceOptionsForType" :key="item.value" :label="item.label" :value="item.value" />
                </el-select>
                <el-select
                  v-else-if="field.type === 'multi-select'"
                  v-model="editingRow[field.key]"
                  multiple
                  clearable
                  style="width: 100%"
                  :disabled="!canEdit"
                  @change="persistRow(editingRow, field.key)"
                >
                  <el-option v-for="item in field.options" :key="item.value || item" :label="item.label || item" :value="item.value || item" />
                </el-select>
                <el-input
                  v-else-if="field.type === 'plate-list'"
                  :model-value="plateDraft"
                  type="textarea"
                  :autosize="{ minRows: 1, maxRows: 6 }"
                  resize="none"
                  placeholder="输入板号；回车、逗号或制表符均可分隔"
                  :disabled="!canEdit"
                  @update:model-value="onPlateDraftInput"
                  @blur="persistRow(editingRow, 'plate_nos')"
                />
                <el-select
                  v-else-if="field.type === 'select'"
                  v-model="editingRow[field.key]"
                  style="width: 100%"
                  :disabled="!canEditField(editingRow, field.key)"
                  @change="persistRow(editingRow, field.key)"
                >
                  <el-option v-for="item in field.options" :key="item.value || item" :label="item.label || item" :value="item.value || item" />
                </el-select>
                <el-input
                  v-else
                  v-model="editingRow[field.key]"
                  :disabled="!canEdit"
                  :type="field.type === 'textarea' ? 'textarea' : 'text'"
                  :autosize="field.type === 'textarea' ? { minRows: 1, maxRows: 4 } : undefined"
                  @blur="persistRow(editingRow, field.key)"
                />
              </el-form-item>
            </div>
          </article>
        </el-form>
      </div>
    </el-drawer>
    <el-dialog v-model="createVisible" title="新增文库工单" width="420px" append-to-body>
      <el-form label-width="88px">
        <el-form-item label="类型" required>
          <el-select v-model="createType" style="width: 100%">
            <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { Download, Plus, Search, Tools } from '@element-plus/icons-vue'
import {
  ElButton,
  ElCard,
  ElDatePicker,
  ElDialog,
  ElDrawer,
  ElForm,
  ElFormItem,
  ElIcon,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElPagination,
  ElSelect,
} from 'element-plus'
import { VxeInput, VxeSelect } from 'vxe-pc-ui'
import { VxeColumn, VxeTable } from 'vxe-table'
import { useUserStore } from '@vben/stores'

import '#/adapter/vxe-table'
import 'vxe-pc-ui/styles/cssvar.scss'
import 'vxe-table/styles/cssvar.scss'

import {
  deleteLibraryOrder,
  exportLibraryOrderList,
  fetchLibraryMeta,
  fetchLibraryOrderList,
  fetchPrimerIndexOptions,
  LIBRARY_CREATED_KEY,
  saveLibraryOrder,
} from '#/api/molecularLibrary'
import { skipGlobalErrorHandler } from '#/api/request'
import { notifyApiError } from '#/api/errors'
import AdvancedOpsBar from '#/components/AdvancedOpsBar.vue'
import {
  coerceWorkbenchViewMode,
  createColumnOrder,
  EXCEL_VIEW,
  searchWorkbenchTargets,
  uniqueTargetCodes,
  WORKBENCH_VIEW,
  WorkbenchDataTable,
  workbenchExcelMixin,
  WorkbenchStatusEditor,
  WorkbenchTargetSelect,
  WorkbenchViewToggle,
} from '#/components/workbench'
import SerumUserSelect from '../../Serum/shared/SerumUserSelect.vue'
import LibraryRowActions from './LibraryRowActions.vue'
import { downloadListExcel, excelTimestamp } from '#/utils/downloadExcel'
import { canEditLibrary, canViewLibraryDetail } from '#/utils/molecularPermission'
import { loadSerumUserOptions } from '#/utils/serumUserOptions'
import { shouldRefreshTabData } from '#/utils/staleTabRefresh'
import {
  allSheetColumns,
  BUILD_POOLED_BCR,
  BUILD_TYPE_OPTIONS,
  buildTypeLabel,
  CELL_TYPE_OPTIONS,
  INDEX_MODE_OPTIONS,
  MOUSE_CATEGORY_LABELS,
  MOUSE_CATEGORY_OPTIONS,
  mouseCategoryLabel,
  normalizePlateInputText,
  optionsForBuild,
  orderEditorSections,
  plateNumbersFromText,
  plateNumbersText,
  PHAGE_EXPERIMENT_TYPE_OPTIONS,
  PRIORITY_OPTIONS,
  QC_RESULT_OPTIONS,
  SAMPLE_SOURCE_OPTIONS,
  SAMPLE_TYPE_OPTIONS,
  sampleSourceLabel,
  sampleTypeLabel,
  isSheetFieldApplicable,
  sheetColumnsForBuild,
  STATUS_OPTIONS,
  statusTone,
  TYPE_VALUES,
  typeGroup,
  WORKBENCH_COLUMNS,
} from './libraryColumns'

function emptyQuery() {
  return {
    page: 1,
    limit: 20,
    build_type: '',
    keyword: '',
    target: '',
    target_name: '',
    study_type: '',
    status: '',
    priority: '',
    pm: '',
    owner: '',
    sample_source: '',
    sample_type: '',
    cell_type: '',
    mouse_model: '',
    source_discovery_id: '',
    notebook_no: '',
    remark: '',
    instrument_on_start: '',
    instrument_on_end: '',
    started_at_start: '',
    started_at_end: '',
    finished_at_start: '',
    finished_at_end: '',
  }
}

const SHEET_COLUMN_ORDER = createColumnOrder(
  'libraryConstructionSheetColumnOrder.v4',
  allSheetColumns(),
  { pinFirstKey: 'library_order_id' },
)

export default {
  name: 'LibraryConstructionList',
  mixins: [workbenchExcelMixin],
  components: {
    AdvancedOpsBar,
    ElButton,
    ElCard,
    ElDatePicker,
    ElDialog,
    ElDrawer,
    ElForm,
    ElFormItem,
    ElIcon,
    ElInput,
    ElOption,
    ElPagination,
    ElSelect,
    LibraryRowActions,
    SerumUserSelect,
    Tools,
    WorkbenchDataTable,
    WorkbenchStatusEditor,
    WorkbenchTargetSelect,
    WorkbenchViewToggle,
    VxeColumn,
    VxeInput,
    VxeSelect,
    VxeTable,
  },
  setup() {
    return { Download, Plus, Search }
  },
  data() {
    return {
      excelRowSelectKey: 'id',
      showAdvancedOps: false,
      loading: false,
      listRequestId: 0,
      list: [],
      total: 0,
      stats: {},
      meta: null,
      listQuery: emptyQuery(),
      instrumentRange: [],
      startedRange: [],
      finishedRange: [],
      viewMode: WORKBENCH_VIEW,
      drawerVisible: false,
      editingId: null,
      editingRow: null,
      plateDraft: '',
      rowBaselines: new Map(),
      allUserOptions: [],
      catalogOptions: [],
      catalogLoading: false,
      targetFilterOptions: [],
      targetFilterLoading: false,
      consumingCreated: false,
      createVisible: false,
      createType: TYPE_VALUES[0],
      drawerPointerBound: false,
      sheetColumns: allSheetColumns(),
      listLoaded: false,
      tabDataFetchedAt: 0,
    }
  },
  computed: {
    canEdit() {
      return canEditLibrary(useUserStore().userInfo)
    },
    canViewDetail() {
      return canViewLibraryDetail(useUserStore().userInfo)
    },
    activeType() {
      return this.listQuery.build_type || ''
    },
    hasAdvancedFilters() {
      const keys = [
        'pm',
        'study_type',
        'sample_type',
        'mouse_model',
        'cell_type',
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
      return this.typeOptions.map((item, index) => ({
        ...item,
        tone: tones[index % tones.length],
        hint: item.hint,
      }))
    },
    statusOptions() {
      return this.meta?.statuses || STATUS_OPTIONS
    },
    priorityOptions() {
      return this.meta?.priorities || PRIORITY_OPTIONS
    },
    sampleSourceOptions() {
      return (this.meta?.sample_sources || SAMPLE_SOURCE_OPTIONS).map((item) => ({
        value: item.value || item.code,
        label: item.label,
      }))
    },
    sampleTypeOptions() {
      return (this.meta?.sample_types || SAMPLE_TYPE_OPTIONS).map((item) => ({
        value: item.value || item.code,
        label: item.label,
      }))
    },
    mouseCategoryOptions() {
      return MOUSE_CATEGORY_OPTIONS
    },
    workbenchColumns() {
      return WORKBENCH_COLUMNS
    },
    typeValues() {
      return this.typeOptions.map((item) => item.value)
    },
    typeOptions() {
      return BUILD_TYPE_OPTIONS
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
    editingIndex() {
      return this.list.findIndex((row) => row.id === this.editingId)
    },
    hasPrevEditor() {
      return this.editingIndex > 0
    },
    hasNextEditor() {
      return this.editingIndex >= 0 && this.editingIndex < this.list.length - 1
    },
    editorSections() {
      return orderEditorSections(typeGroup(this.editingRow?.build_type), this.editingRow)
    },
    sourceOptionsForType() {
      return optionsForBuild(SAMPLE_SOURCE_OPTIONS, this.editingRow?.build_type)
    },
  },
  created() {
    this.viewMode = coerceWorkbenchViewMode(this.viewMode)
    this.rebuildSheetColumns()
    this.loadAllUserOptions()
    this.loadMeta()
    this.getList({ flushEditor: false }).finally(() => {
      this.listLoaded = true
      this.consumeCreatedQuery()
    })
  },
  activated() {
    this.bindDrawerPointer()
    if (this.listLoaded && shouldRefreshTabData(this.tabDataFetchedAt)) {
      this.getList({ flushEditor: false })
    }
    this.consumeCreatedQuery()
  },
  mounted() {
    this.bindDrawerPointer()
  },
  beforeUnmount() {
    this.unbindDrawerPointer()
  },
  deactivated() {
    this.closeDrawer()
    this.unbindDrawerPointer()
  },
  watch: {
    '$route.query.created'() {
      this.consumeCreatedQuery()
    },
    'listQuery.build_type'() {
      this.rebuildSheetColumns()
    },
  },
  methods: {
    buildTypeLabel,
    mouseCategoryLabel,
    sampleSourceLabel,
    sampleTypeLabel,
    statusTone,
    typeGroup,
    bindDrawerPointer() {
      if (this.drawerPointerBound) return
      document.addEventListener('mousedown', this.onDocumentPointerDown, true)
      this.drawerPointerBound = true
    },
    unbindDrawerPointer() {
      if (!this.drawerPointerBound) return
      document.removeEventListener('mousedown', this.onDocumentPointerDown, true)
      this.drawerPointerBound = false
    },
    async loadMeta() {
      try {
        this.meta = await fetchLibraryMeta()
      } catch {
        this.meta = null
      }
    },
    async searchCatalog(query = '') {
      this.catalogLoading = true
      try {
        const data = await fetchPrimerIndexOptions({ query, limit: 100 })
        this.catalogOptions = data?.items || []
      } catch {
        this.catalogOptions = []
      } finally {
        this.catalogLoading = false
      }
    },
    async onCatalogChange(row, field, value) {
      if (!row) return
      const selected = this.catalogOptions.find((item) => item.name === value)
      row[field.catalogIdKey] = selected?.id || null
      if (field.sequenceKey) row[field.sequenceKey] = selected?.short_sequence || ''
      const payload = {
        id: row.id,
        [field.key]: value || null,
        [field.catalogIdKey]: row[field.catalogIdKey],
      }
      if (field.sequenceKey) payload[field.sequenceKey] = row[field.sequenceKey] || null
      try {
        const saved = await saveLibraryOrder(payload)
        this.applySavedFields(this.normalizeRow(saved))
      } catch (error) {
        const baseline = this.rowBaselines.get(row.id)
        if (baseline) Object.assign(row, this.normalizeRow(JSON.parse(JSON.stringify(baseline))))
        notifyApiError(error, { messages: { default: '保存引物或Index失败' } })
      }
    },
    canEditField(row, key) {
      if (!this.canEdit) return false
      if (key === 'build_type') return (row?.status || '待处理') === '待处理'
      return true
    },
    isSheetCellLocked(row, key) {
      if (!this.canEditField(row, key)) return true
      if (!isSheetFieldApplicable(row?.build_type, key)) return true
      const column = this.sheetColumns.find((item) => item.key === key)
      return column?.edit === 'readonly'
    },
    selectType(value) {
      this.listQuery.build_type = this.activeType === value ? '' : value
      this.handleFilter()
    },
    handleFilter() {
      this.listQuery.page = 1
      this.getList()
    },
    resetFilters() {
      this.listQuery = emptyQuery()
      this.instrumentRange = []
      this.startedRange = []
      this.finishedRange = []
      this.targetFilterOptions = []
      this.getList()
    },
    async searchTargetFilter(keyword) {
      this.targetFilterLoading = true
      try {
        const selected = this.listQuery.target ? [this.listQuery.target] : []
        this.targetFilterOptions = await searchWorkbenchTargets(keyword, selected)
      } catch {
        this.targetFilterOptions = []
      } finally {
        this.targetFilterLoading = false
      }
    },
    onTargetFilterChange(code) {
      const selected = this.targetFilterOptions.find((item) => item.snum === code)
      this.listQuery.target = code || ''
      this.listQuery.target_name = selected?.name || ''
      this.handleFilter()
    },
    openColumnPicker() {
      this.$refs.workbenchTable?.openColumnPicker()
    },
    buildQuery() {
      const [instrumentStart, instrumentEnd] = this.instrumentRange || []
      const [startedStart, startedEnd] = this.startedRange || []
      const [finishedStart, finishedEnd] = this.finishedRange || []
      return {
        ...this.listQuery,
        instrument_on_start: instrumentStart || '',
        instrument_on_end: instrumentEnd || '',
        started_at_start: startedStart || '',
        started_at_end: startedEnd || '',
        finished_at_start: finishedStart || '',
        finished_at_end: finishedEnd || '',
      }
    },
    normalizeRow(row) {
      return {
        ...row,
        target_codes: uniqueTargetCodes(row?.target_codes),
        target_forms: Array.isArray(row?.target_forms) ? row.target_forms : [],
        plate_nos: Array.isArray(row?.plate_nos) ? row.plate_nos : [],
      }
    },
    updateRowBaseline(row) {
      if (!row?.id) return
      this.rowBaselines.set(row.id, JSON.parse(JSON.stringify(row)))
    },
    async loadAllUserOptions() {
      try {
        this.allUserOptions = await loadSerumUserOptions()
      } catch {
        this.allUserOptions = []
      }
    },
    selectedUserOptions(value) {
      const text = String(value || '').trim()
      return text ? [text] : []
    },
    async getList({ flushEditor = true } = {}) {
      const requestId = ++this.listRequestId
      this.loading = true
      try {
        if (flushEditor) await this.flushPendingSheetEdits()
        const data = await fetchLibraryOrderList(this.buildQuery(), skipGlobalErrorHandler)
        if (requestId !== this.listRequestId) return
        this.list = (data?.items || []).map((row) => this.normalizeRow(row))
        this.list.forEach((row) => this.updateRowBaseline(row))
        this.total = data?.total || 0
        this.stats = { ...Object.fromEntries(this.typeOptions.map((item) => [item.value, 0])), ...(data?.stats || {}) }
        if (this.editingId) {
          const selected = this.list.find((row) => row.id === this.editingId)
          if (selected) {
            this.editingRow = this.normalizeRow(JSON.parse(JSON.stringify(selected)))
            this.plateDraft = plateNumbersText(this.editingRow.plate_nos)
          } else {
            this.closeDrawer()
          }
        }
        this.tabDataFetchedAt = Date.now()
      } catch (error) {
        if (requestId !== this.listRequestId) return
        notifyApiError(error, { messages: { default: '加载文库工单失败' } })
      } finally {
        if (requestId === this.listRequestId) this.loading = false
      }
    },
    rebuildSheetColumns() {
      const cols = sheetColumnsForBuild(this.activeType)
      const remaining = new Map(cols.map((column) => [column.key, column]))
      const ordered = []
      SHEET_COLUMN_ORDER.load().forEach((column) => {
        const next = remaining.get(column.key)
        if (!next) return
        ordered.push(next)
        remaining.delete(next.key)
      })
      cols.forEach((column) => {
        if (remaining.has(column.key)) ordered.push(column)
      })
      this.sheetColumns = ordered
    },
    persistSheetColumnOrder(columns) {
      const next = columns || this.sheetColumns
      this.sheetColumns = next
      const visibleKeys = new Set(next.map((column) => column.key))
      let visibleIndex = 0
      const merged = SHEET_COLUMN_ORDER.load().map((column) => {
        if (!visibleKeys.has(column.key)) return column
        const replacement = next[visibleIndex]
        visibleIndex += 1
        return replacement || column
      })
      if (visibleIndex < next.length) merged.push(...next.slice(visibleIndex))
      SHEET_COLUMN_ORDER.save(merged)
    },
    async resetSheetColumnOrder() {
      if (this.isExcelMode) {
        if (!await this.flushPendingSheetEdits()) return
        SHEET_COLUMN_ORDER.clear()
        this.rebuildSheetColumns()
        this.persistSheetColumnOrder(this.sheetColumns)
        this.clearSheetRange()
        return
      }
      this.$refs.workbenchTable?.resetColumnOrder()
    },
    async toggleViewMode() {
      if (this.isExcelMode && !await this.flushPendingSheetEdits()) return
      this.viewMode = this.viewMode === EXCEL_VIEW ? WORKBENCH_VIEW : EXCEL_VIEW
    },
    applySavedFields(saved, fields) {
      this.patchExistingListRow(saved, fields)
      if (this.editingId === saved?.id && this.editingRow) {
        Object.assign(this.editingRow, this.normalizeRow(saved))
        this.plateDraft = plateNumbersText(this.editingRow.plate_nos)
      }
      this.updateRowBaseline(this.normalizeRow(saved))
    },
    sameFieldValue(left, right) {
      if (Array.isArray(left) || Array.isArray(right) || (left && typeof left === 'object') || (right && typeof right === 'object')) {
        return JSON.stringify(left ?? null) === JSON.stringify(right ?? null)
      }
      return String(left ?? '') === String(right ?? '')
    },
    async persistRow(row, field) {
      if (!this.canEdit || !row?.id) return
      const baseline = this.rowBaselines.get(row.id)
      if (baseline && this.sameFieldValue(baseline[field], row[field])) {
        if (field !== 'target_codes' || this.sameFieldValue(baseline.target_name, row.target_name)) return
      }
      try {
        const payload = { id: row.id, [field]: row[field] }
        if (field === 'target_codes') payload.target_name = row.target_name
        const saved = await saveLibraryOrder(payload)
        const savedFields = field === 'target_codes'
          ? [field, 'target_name']
          : field === 'mouse_model'
            ? [field, 'sample_type']
            : [field]
        this.applySavedFields(
          this.normalizeRow(saved),
          field === 'build_type' ? undefined : savedFields,
        )
      } catch (error) {
        if (baseline) {
          row[field] = baseline[field]
          if (field === 'target_codes') row.target_name = baseline.target_name
          if (field === 'plate_nos') this.plateDraft = plateNumbersText(row.plate_nos)
        }
        notifyApiError(error, { messages: { default: '保存失败' } })
      }
    },
    onPlateDraftInput(value) {
      if (!this.editingRow) return
      this.plateDraft = normalizePlateInputText(value)
      this.editingRow.plate_nos = plateNumbersFromText(this.plateDraft)
    },
    async updateStatus(row, value) {
      row.status = value
      await this.persistRow(row, 'status')
    },
    onDrawerTargetChange(row, payload) {
      row.target_codes = payload.codes
      row.target_name = payload.name
      this.persistRow(row, 'target_codes')
    },
    openSourceDiscovery(discoveryId) {
      const id = String(discoveryId || '').trim()
      if (!id) return
      this.$router.push({ name: 'DiscoveryWorkbench', query: { focus: id } })
    },
    onWorkbenchRowClick(row, _column, event) {
      if (event?.target?.closest?.('.el-button, .el-input, .el-select, .el-date-editor, .action-cell, .workbench-status-tag')) {
        return
      }
      this.openDrawer(row)
    },
    workbenchRowClassName({ row }) {
      return row.id === this.editingId ? 'is-editing' : ''
    },
    shiftEditor(delta) {
      const next = this.list[this.editingIndex + delta]
      if (next) this.openDrawer(next)
    },
    onWorkbenchRowContextMenu(_row, _column, event) {
      event?.preventDefault?.()
      if (this.drawerVisible) this.closeDrawer()
    },
    onDocumentPointerDown(event) {
      if (!this.drawerVisible) return
      const target = event.target
      if (!(target instanceof Element)) return
      if (target.closest('.el-drawer, .el-popper, .el-select-dropdown, .el-picker-panel, .el-message-box, .el-overlay-message-box, .sheet-picker-popup')) {
        return
      }
      if (target.closest('.el-table__row, .vxe-body--row, .action-cell')) return
      this.closeDrawer()
    },
    closeDrawer() {
      this.drawerVisible = false
      this.editingId = null
      this.editingRow = null
      this.plateDraft = ''
    },
    openDrawer(row) {
      if (!row?.id) return
      if (this.drawerVisible && this.editingId === row.id) {
        this.closeDrawer()
        return
      }
      this.editingId = row.id
      this.editingRow = this.normalizeRow(JSON.parse(JSON.stringify(row)))
      this.plateDraft = plateNumbersText(this.editingRow.plate_nos)
      this.drawerVisible = true
    },
    openResult(row) {
      if (!this.canViewDetail) {
        ElMessage.warning('您没有权限查看文库详情')
        return
      }
      this.$router.push({ path: '/molecular-cell/library-construction/result', query: { id: row.id } })
    },
    handleDownstreamHandoff() {
      if (!this.canEdit) {
        ElMessage.warning('您没有权限交接文库工单')
        return
      }
      ElMessage.info('下游测序模块尚未开放')
    },
    async handleDelete(row) {
      if (!this.canEdit) {
        ElMessage.warning('您没有权限删除文库工单')
        return
      }
      try {
        const name = row.library_code || row.library_order_id || '这条工单'
        await ElMessageBox.confirm(
          `确认删除 ${name}？工单及其独占质检文件将一并删除，且无法恢复。`,
          '删除确认',
          { type: 'warning', confirmButtonText: '删除' },
        )
      } catch {
        return
      }
      try {
        await deleteLibraryOrder(row.id)
        if (this.editingId === row.id) this.closeDrawer()
        await this.getList({ flushEditor: false })
        ElMessage.success('已删除')
      } catch (error) {
        notifyApiError(error, { messages: { default: '删除失败' } })
      }
    },
    handleCreate() {
      if (!this.canEdit) {
        ElMessage.warning('您没有权限新建文库工单')
        return
      }
      this.createType = this.typeOptions.some((item) => item.value === this.activeType)
        ? this.activeType
        : this.typeOptions[0]?.value
      this.createVisible = true
    },
    async confirmCreate() {
      if (!this.typeValues.includes(this.createType)) {
        ElMessage.warning('请选择类型')
        return
      }
      try {
        const saved = await saveLibraryOrder({
          build_type: this.createType,
        })
        this.createVisible = false
        await this.getList({ flushEditor: false })
        this.openDrawer(this.normalizeRow(saved))
      } catch (error) {
        notifyApiError(error, { messages: { default: '新建失败' } })
      }
    },
    async handleListExport() {
      try {
        await downloadListExcel(
          () => exportLibraryOrderList(this.buildQuery()),
          `文库构建_${excelTimestamp()}.xlsx`,
        )
      } catch (error) {
        notifyApiError(error, { messages: { default: '列表导出失败' } })
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
            if (cached?.id === id) this.openDrawer(this.normalizeRow(cached))
          } catch {
            /* ignore */
          }
        }
      } finally {
        this.consumingCreated = false
      }
    },
    isUserColumn(column) {
      return ['pm', 'owner', 'qc_owner', 'pcr_owner', 'pcr_qc_owner', 'transfection_owner'].includes(column?.key)
    },
    isSheetChoiceColumn(column) {
      return column?.edit === 'select'
    },
    isSheetChoiceForRow(column, row) {
      return column.key !== 'cell_type' || row?.build_type === BUILD_POOLED_BCR
    },
    sheetChoiceSelectOptions(column, row) {
      if (column.key === 'priority') return this.priorityOptions.map((item) => ({ label: item, value: item }))
      if (column.key === 'status') return this.statusOptions.map((item) => ({ label: item, value: item }))
      if (column.key === 'build_type') return this.typeOptions
      if (column.key === 'mouse_model') {
        return this.mouseCategoryOptions.map((item) => ({ label: this.mouseCategoryLabel(item), value: item }))
      }
      if (column.key === 'sample_source') return optionsForBuild(SAMPLE_SOURCE_OPTIONS, row?.build_type)
      if (column.key === 'sample_type') return SAMPLE_TYPE_OPTIONS
      if (column.key === 'cell_type') return CELL_TYPE_OPTIONS.map((item) => ({ label: item, value: item }))
      if (column.key === 'source_experiment_type') {
        return PHAGE_EXPERIMENT_TYPE_OPTIONS.map((item) => ({ label: item, value: item }))
      }
      if (column.key === 'index_mode') return INDEX_MODE_OPTIONS
      if (column.key === 'qc_result') return QC_RESULT_OPTIONS.map((item) => ({ label: item, value: item }))
      if (this.isUserColumn(column)) return this.allUserOptions.map((item) => ({ label: item, value: item }))
      return []
    },
    sheetDirectTextValue(row, key) {
      if (!row) return ''
      if (key === 'build_type') return buildTypeLabel(row[key])
      if (key === 'mouse_model') return this.mouseCategoryLabel(row[key])
      if (key === 'sample_source') return sampleSourceLabel(row[key])
      if (key === 'sample_type') return sampleTypeLabel(row[key])
      if (key === 'index_mode') {
        return INDEX_MODE_OPTIONS.find((item) => item.value === row[key])?.label || row[key] || ''
      }
      if (key === 'target_codes') return uniqueTargetCodes(row[key]).join(',')
      if (['plate_nos', 'target_forms'].includes(key)) {
        return Array.isArray(row[key]) ? row[key].join('、') : (row[key] || '')
      }
      return row[key] == null ? '' : String(row[key])
    },
    sheetFormatter(column) {
      if (column.key === 'build_type') return ({ cellValue }) => buildTypeLabel(cellValue) || ''
      if (column.key === 'mouse_model') return ({ cellValue }) => this.mouseCategoryLabel(cellValue) || ''
      if (column.key === 'sample_source') return ({ cellValue }) => sampleSourceLabel(cellValue) || ''
      if (column.key === 'sample_type') return ({ cellValue }) => sampleTypeLabel(cellValue) || ''
      if (column.key === 'target_codes') return ({ row }) => uniqueTargetCodes(row.target_codes).join(',')
      if (['plate_nos', 'target_forms'].includes(column.key)) {
        return ({ cellValue }) => Array.isArray(cellValue) ? cellValue.join('、') : (cellValue || '')
      }
      return undefined
    },
    sheetTargetDirectValue(row, key) {
      return key === 'target_codes' ? uniqueTargetCodes(row.target_codes).join(',') : row.target_name
    },
    setSheetTargetDirectValue(row, key, value) {
      if (key === 'target_codes') {
        row.target_codes = uniqueTargetCodes(value)
        return
      }
      row.target_name = value
    },
    sheetOptionValue(options, raw) {
      const text = String(raw || '').trim().toLowerCase()
      const matched = options.find((item) => (
        String(item.value ?? item).toLowerCase() === text
        || String(item.label ?? item).toLowerCase() === text
      ))
      return matched ? (matched.value ?? matched) : undefined
    },
    coerceSheetValue(row, key, text) {
      const raw = String(text ?? '').trim()
      if (['plate_nos', 'target_forms'].includes(key)) {
        return {
          ok: true,
          value: raw ? raw.split(/[,，、\t\r\n]+/).map((item) => item.trim()).filter(Boolean) : [],
        }
      }
      if (['received_on', 'instrument_on', 'blood_collected_on', 'qc_on'].includes(key)) {
        if (!raw) return { ok: true, value: null }
        return /^\d{4}-\d{2}-\d{2}$/.test(raw) ? { ok: true, value: raw } : { ok: false, reason: 'date' }
      }
      if (['started_at', 'finished_at', 'pcr_started_at', 'pcr_finished_at', 'transfected_at'].includes(key)) {
        if (!raw) return { ok: true, value: null }
        return /^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}(:\d{2})?)?$/.test(raw)
          ? { ok: true, value: raw }
          : { ok: false, reason: 'datetime' }
      }
      if (key === 'build_type') {
        const value = this.sheetOptionValue(this.typeOptions, raw)
        return value ? { ok: true, value } : { ok: false, reason: 'option' }
      }
      if (key === 'mouse_model') {
        if (!raw) return { ok: true, value: null }
        if (MOUSE_CATEGORY_OPTIONS.includes(raw)) return { ok: true, value: raw }
        const matched = Object.entries(MOUSE_CATEGORY_LABELS).find(([, label]) => label === raw)
        return matched ? { ok: true, value: matched[0] } : { ok: false, reason: 'option' }
      }
      if (key === 'sample_source') {
        if (!raw) return { ok: true, value: null }
        const value = this.sheetOptionValue(optionsForBuild(SAMPLE_SOURCE_OPTIONS, row?.build_type), raw)
        return value
          ? { ok: true, value }
          : { ok: false, reason: 'option' }
      }
      if (key === 'sample_type') {
        if (!raw) return { ok: true, value: null }
        const value = this.sheetOptionValue(SAMPLE_TYPE_OPTIONS, raw)
        return value
          ? { ok: true, value }
          : { ok: false, reason: 'option' }
      }
      if (key === 'cell_type') {
        if (row?.build_type !== BUILD_POOLED_BCR) return { ok: true, value: raw || null }
        return !raw || CELL_TYPE_OPTIONS.includes(raw)
          ? { ok: true, value: raw || null }
          : { ok: false, reason: 'option' }
      }
      if (key === 'source_experiment_type') {
        return !raw || PHAGE_EXPERIMENT_TYPE_OPTIONS.includes(raw)
          ? { ok: true, value: raw || null }
          : { ok: false, reason: 'option' }
      }
      if (key === 'index_mode') {
        if (!raw) return { ok: true, value: null }
        const value = this.sheetOptionValue(INDEX_MODE_OPTIONS, raw)
        return value
          ? { ok: true, value }
          : { ok: false, reason: 'option' }
      }
      if (key === 'qc_result') {
        return !raw || QC_RESULT_OPTIONS.includes(raw)
          ? { ok: true, value: raw || null }
          : { ok: false, reason: 'option' }
      }
      if (key === 'status') return STATUS_OPTIONS.includes(raw) ? { ok: true, value: raw } : { ok: false, reason: 'option' }
      if (key === 'priority') return PRIORITY_OPTIONS.includes(raw) ? { ok: true, value: raw } : { ok: false, reason: 'option' }
      if (key === 'target_codes') return { ok: true, value: uniqueTargetCodes(raw) }
      return { ok: true, value: raw || null }
    },
    sheetValidationMessage(_key, reason) {
      if (reason === 'date') return '日期必须是 YYYY-MM-DD'
      if (reason === 'datetime') return '时间必须是 YYYY-MM-DD HH:MM'
      if (reason === 'option') return '不在允许的选项中'
      return '输入不合法'
    },
    restoreSheetEditValue(row, key, value) {
      if (key === 'target_codes') {
        row.target_codes = uniqueTargetCodes(value)
        return
      }
      row[key] = this.cloneSheetValue(value)
    },
    async finishSheetEdit(context) {
      const row = context?.row
      const key = context?.column?.field
      if (!key || !row?.id) return
      const originalValue = this.takeSheetEditOriginal(row, key)
      if (this.isSheetCellLocked(row, key)) {
        this.restoreSheetEditValue(row, key, originalValue)
        return
      }
      const source = key === 'target_codes' ? row.target_codes : row[key]
      const result = this.coerceSheetValue(row, key, source)
      if (!result.ok) {
        this.restoreSheetEditValue(row, key, originalValue)
        ElMessage.warning(this.sheetValidationMessage(key, result.reason))
        return
      }
      if (this.sameSheetValue(key, result.value, originalValue)) {
        this.restoreSheetEditValue(row, key, originalValue)
        return
      }
      this.restoreSheetEditValue(row, key, result.value)
      await this.persistRow(row, key)
    },
  },
}
</script>

<style scoped src="#/components/workbench/workbenchExcel.css"></style>
<style scoped src="#/components/workbench/workbenchDrawerChrome.css"></style>
<style src="#/components/workbench/workbenchDrawer.css"></style>
<style scoped>
.library-order-page {
  position: relative;
  min-height: 100%;
  padding: var(--list-page-padding);
  background: var(--list-page-bg);
}

.workbench-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: var(--list-surface-padding-y) var(--list-surface-padding-x);
  margin-bottom: var(--list-page-gap);
  background: var(--list-surface-bg);
  border: var(--list-surface-border);
  border-radius: var(--list-surface-radius);
  box-shadow: var(--list-surface-shadow);
}

.page-title {
  margin: 0;
  color: var(--el-text-color-primary);
  font-size: var(--list-page-title-size);
  font-weight: var(--list-page-title-weight);
  letter-spacing: 0.2px;
}

.text-secondary {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.text-hint {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  opacity: 0.92;
}

.page-header-band {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-width: 0;
  padding: 12px 16px;
  border: 1px solid rgb(191 219 254 / 45%);
  border-radius: var(--list-mid-radius);
  background: linear-gradient(90deg, #e6f0ff 0%, #f2faf7 46%, #ffffff 100%);
}

.title-group {
  min-width: 0;
}

.page-subtitle {
  max-width: 560px;
  margin: 6px 0 0;
  color: var(--list-page-subtitle-color);
  font-size: var(--list-page-subtitle-size);
  font-weight: var(--list-page-subtitle-weight);
}

.header-actions {
  display: flex;
  flex-shrink: 0;
  gap: 8px;
  align-items: center;
}

.total-count {
  display: flex;
  align-items: center;
  white-space: nowrap;
}

.stats-strip {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
}

.stat-tile {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 54px;
  padding: 8px 10px 8px 14px;
  text-align: left;
  background: var(--list-mid-bg);
  border: var(--list-mid-border);
  border-radius: var(--list-mid-radius);
  --stat-ring: rgba(64, 158, 255, 0.32);
  --stat-glow: rgba(64, 158, 255, 0.12);
}

.stat-tile-interactive {
  cursor: pointer;
  user-select: none;
  transition:
    transform 0.22s cubic-bezier(0.4, 0, 0.2, 1),
    box-shadow 0.22s ease,
    border-color 0.22s ease,
    background-color 0.22s ease;
}

.stat-tile-interactive:hover {
  transform: translateY(-2px);
  border-color: #dce3ec;
  background: #fff;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.07);
}

.stat-tile-interactive:active {
  transform: translateY(0) scale(0.985);
  background: #fff;
  border-color: transparent;
  box-shadow: 0 3px 10px var(--stat-glow), 0 0 0 1.5px var(--stat-ring);
  transition-duration: 0.08s;
}

.stat-tile-active {
  border-color: transparent;
  background: #fff;
  box-shadow: 0 6px 18px var(--stat-glow), 0 0 0 1.5px var(--stat-ring);
}

.stat-tile-active:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 24px var(--stat-glow), 0 0 0 1.5px var(--stat-ring);
}

.stat-tile-active:active {
  transform: translateY(0) scale(0.985);
  box-shadow: 0 3px 10px var(--stat-glow), 0 0 0 1.5px var(--stat-ring);
}

.stat-tile::before {
  position: absolute;
  top: 12px;
  left: 0;
  width: 4px;
  height: 28px;
  content: '';
  border-radius: 0 999px 999px 0;
  transition: height 0.22s ease, top 0.22s ease;
}

.stat-tile-interactive:hover::before,
.stat-tile-active::before {
  top: 10px;
  height: 32px;
}

.stat-copy {
  display: flex;
  flex: 1;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
}

.stat-label {
  display: block;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  font-weight: 500;
}

.stat-copy small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stat-tile-active .stat-label {
  color: var(--el-text-color-primary);
  font-weight: 600;
}

.stat-tile-active .stat-value {
  transform: scale(1.03);
}

.stat-value {
  flex: 0 0 auto;
  color: var(--el-text-color-primary);
  font-size: 22px;
  font-weight: 600;
  line-height: 1;
}

.stat-blue::before { background: var(--el-color-primary); }
.stat-blue { --stat-ring: rgba(64, 158, 255, 0.34); --stat-glow: rgba(64, 158, 255, 0.12); }
.stat-purple::before { background: #8b5cf6; }
.stat-purple { --stat-ring: rgba(139, 92, 246, 0.34); --stat-glow: rgba(139, 92, 246, 0.12); }
.stat-orange::before { background: #ff9f43; }
.stat-orange { --stat-ring: rgba(255, 159, 67, 0.38); --stat-glow: rgba(255, 159, 67, 0.13); }
.stat-red::before { background: #ff6b6b; }
.stat-red { --stat-ring: rgba(255, 107, 107, 0.36); --stat-glow: rgba(255, 107, 107, 0.12); }
.stat-slate::before { background: #4dd0e1; }
.stat-slate { --stat-ring: rgba(77, 208, 225, 0.38); --stat-glow: rgba(77, 208, 225, 0.13); }

.filter-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 10px;
  align-items: center;
  min-width: 0;
  padding-top: 10px;
  border-top: 1px solid #edf1f7;
}

.filter-item {
  flex: 1 1 100px;
  min-width: 100px;
}

.filter-keyword {
  flex: 2 1 250px;
  min-width: 200px;
}

.target-option-code {
  float: right;
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
}

.catalog-sequence {
  float: right;
  margin-left: 16px;
  color: #909399;
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 12px;
}

.filter-strip :deep(.filter-range) {
  flex: 1.4 1 240px;
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

.drawer-heading {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.drawer-title {
  color: #20252c;
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 18px;
  font-weight: 600;
  line-height: 1.2;
  letter-spacing: 0.01em;
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
  background: #f4f6f8;
  border: 1px solid #e5e9ef;
  border-radius: 5px;
}

.source-link-input {
  cursor: pointer;
}

.source-link-input :deep(.el-input__wrapper),
.source-link-input :deep(.el-input__inner) {
  cursor: pointer;
}

.source-link-action {
  color: var(--el-color-primary);
  font-size: 12px;
  font-weight: 600;
}

.drawer-fields {
  margin: 0;
  padding: 0;
  border: 0;
  min-width: 0;
}

.drawer-card {
  padding: 10px 0 2px;
  margin-bottom: 8px;
  background: transparent;
  border: 0;
  border-bottom: 1px solid #eef0f4;
  border-radius: 0;
}

.drawer-card:last-child {
  margin-bottom: 0;
  border-bottom: 0;
}

.drawer-card.is-queue {
  padding: 8px 10px 2px;
  margin-bottom: 8px;
  background: var(--list-mid-bg);
  border: var(--list-mid-border);
  border-radius: var(--list-mid-radius);
}

.drawer-card-title {
  display: flex;
  gap: 7px;
  align-items: center;
  margin: 0 0 10px;
  color: #303133;
  font-size: 13px;
  font-weight: 650;
  letter-spacing: 0.02em;
}

.drawer-card-title::before {
  width: 3px;
  height: 13px;
  background: var(--el-color-primary);
  border-radius: 2px;
  content: '';
}

.drawer-card.is-queue .drawer-card-title {
  color: #303133;
}

.drawer-card-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  column-gap: 12px;
}

.drawer-field.is-wide {
  grid-column: 1 / -1;
}

.drawer-form :deep(.el-form-item) {
  margin-bottom: 8px;
}

.drawer-form :deep(.el-form-item__label) {
  color: #606266;
  font-size: 13px;
  white-space: nowrap;
}

.drawer-form :deep(.el-form-item__content) {
  min-width: 0;
  justify-content: flex-start;
}

.primer-matrix {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr) minmax(0, 1fr) 72px;
  gap: 8px;
  align-items: center;
  width: 100%;
}

.primer-matrix-heading {
  color: #909399;
  font-size: 12px;
  line-height: 20px;
  text-align: center;
}

.primer-chain {
  color: #606266;
  font-size: 13px;
  text-align: center;
}

</style>
