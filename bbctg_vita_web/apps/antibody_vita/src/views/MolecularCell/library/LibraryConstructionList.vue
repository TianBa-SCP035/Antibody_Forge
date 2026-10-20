<template>
  <div class="library-order-page" :class="{ 'is-list-table-locked': listTableLocked }">
    <AdvancedOpsBar v-model="showAdvancedOps">
      <template v-if="showAdvancedOps">
        <el-input
          v-model="listQuery.source_project_code"
          clearable
          placeholder="项目编号"
          title="多个编号用逗号、空格或换行分隔，按完整编号查找；只填一个时按包含查找"
          @keyup.enter="handleFilter"
          @clear="handleFilter"
        />
        <el-input
          v-model="listQuery.library_batch_no"
          clearable
          placeholder="建库批号"
          title="多个批号用逗号、空格或换行分隔，按完整批号查找；只填一个时按包含查找"
          @keyup.enter="handleFilter"
          @clear="handleFilter"
        />
        <ListFilterSelect
          :model-value="listQuery.build_type"
          clearable
          placeholder="建库类型"
          @change="onBuildTypeFilter"
        >
          <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </ListFilterSelect>
        <SerumUserSelect v-model="listQuery.pm" multi-gesture :options="selectedUserOptions(listQuery.pm)" placeholder="PM" clearable @change="handleFilter" />
        <ListFilterSelect v-model="listQuery.study_type" clearable filterable placeholder="课题类型" @change="handleFilter">
          <el-option v-for="item in studyTypeOptions" :key="item" :label="item" :value="item" />
        </ListFilterSelect>
        <ListFilterSelect v-model="listQuery.sample_type" clearable placeholder="样品类型" @change="handleFilter">
          <el-option v-for="item in sampleTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </ListFilterSelect>
        <ListFilterSelect v-model="listQuery.mouse_strain" clearable placeholder="小鼠品系" @change="handleFilter">
          <el-option v-for="item in mouseStrainOptions" :key="item" :label="item" :value="item" />
        </ListFilterSelect>
        <ListFilterSelect
          v-model="listQuery.cell_type"
          clearable
          filterable
          allow-create
          default-first-option
          placeholder="细胞类型"
          @change="handleFilter"
        >
          <el-option v-for="item in cellTypeOptions" :key="item" :label="item" :value="item" />
        </ListFilterSelect>
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
        <el-button v-if="canManageFiles" type="primary" :icon="Upload" @click="resultUploadVisible = true">批量质检上传</el-button>
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

      <div class="filter-strip list-filter-controls">
        <el-input
          v-model="listQuery.library_code"
          class="filter-item filter-keyword"
          clearable
          placeholder="建库编号"
          title="多个编号用逗号、空格或换行分隔，按完整编号查找；只填一个时按包含查找"
          :prefix-icon="Search"
          @keyup.enter="handleFilter"
          @clear="handleFilter"
        />
        <ListFilterSelect v-model="listQuery.status" class="filter-item" clearable placeholder="状态" @change="handleFilter">
          <el-option v-for="item in statusOptions" :key="item" :label="item" :value="item" />
        </ListFilterSelect>
        <ListFilterSelect v-model="listQuery.priority" class="filter-item" clearable placeholder="优先级" @change="handleFilter">
          <el-option v-for="item in priorityOptions" :key="item" :label="item" :value="item" />
        </ListFilterSelect>
        <SerumUserSelect
          v-model="listQuery.owner"
          class="filter-item"
          multi-gesture
          :options="selectedUserOptions(listQuery.owner)"
          placeholder="负责人"
          clearable
          @change="handleFilter"
        />
        <ListFilterSelect v-model="listQuery.sample_source" class="filter-item" clearable placeholder="样品来源" @change="handleFilter">
          <el-option v-for="item in sampleSourceOptions" :key="item.value" :label="item.label" :value="item.value" />
        </ListFilterSelect>
        <ListFilterSelect
          v-model="listQuery.target_name"
          class="filter-item"
          clearable
          filterable
          :filter-method="setTargetFilterQuery"
          placeholder="靶点"
          @clear="setTargetFilterQuery('')"
          @change="handleFilter"
        >
          <el-option
            v-for="item in filteredTargetOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          >
            <span>{{ item.label }}</span>
            <span v-if="targetOptionExtra(item)" class="target-option-code">{{ targetOptionExtra(item) }}</span>
          </el-option>
        </ListFilterSelect>
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
      <div ref="listTableBody" class="list-table-body">
      <WorkbenchDataTable
        v-if="viewMode === 'workbench'"
        ref="workbenchTable"
        :height="listTableHeight"
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
        @header-contextmenu="onWorkbenchHeaderContextMenu"
      >
        <template #header-library_code>
          <span class="library-code-head" :class="{ 'is-asc': libraryCodeOldestFirst }" :title="libraryCodeHeadTitle">建库编号</span>
        </template>
        <template #build_type="{ row }">{{ buildTypeLabel(row.build_type) || '—' }}</template>
        <template #mouse_strain="{ row }">{{ row.mouse_strain || '—' }}</template>
        <template #sample_source="{ row }">{{ sampleSourceLabel(row.sample_source) || '—' }}</template>
        <template #sample_type="{ row }">{{ sampleTypeLabel(row.sample_type) || '—' }}</template>
        <template #index_mode="{ row }">{{ indexModeLabel(row.index_mode) || '—' }}</template>
        <template #priority="{ row }">
          <el-select
            v-if="canEdit"
            v-model="row.priority"
            size="small"
            class="inline-select priority-select"
            :class="'status-tone-' + priorityTone(row)"
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
        @paste="onSheetPaste"
        @dblclick.capture="onSheetDblClickCapture"
        @keydown.capture="onSheetKeydownCapture"
        @compositionend.capture="onSheetCompositionEnd"
        @mousedown="onSheetWrapMouseDown"
        @mouseover="onSheetWrapMouseOver"
        @contextmenu="onSheetContextMenu"
        @selectstart="onSheetSelectStart"
      >
        <div ref="sheetTableStage" class="sheet-table-stage">
          <vxe-table
            :key="sheetColumnOrderKey"
            ref="sheetTable"
            :height="listTableHeight"
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
                  <div v-if="sheetEditSource === 'dblclick'" class="sheet-picker-editor">
                    <span class="sheet-picker-editor__value">{{ sheetPickerDisplayValue(row, column) }}</span>
                    <VxeSelect
                      v-model="row.target_codes"
                      class-name="sheet-grid-editor sheet-picker-control"
                      filterable
                      multiple
                      remote
                      :options="sheetTargetSelectOptions"
                      :popup-config="{ className: 'sheet-picker-popup', placement: 'bottom', width: 300 }"
                      :remote-config="{ autoLoad: true, queryMethod: querySheetTargetOptions }"
                      empty-text="未找到匹配靶点"
                      @change="onSheetTargetPickerChange(row)"
                      @visible-change="onSheetPickerVisibleChange"
                    />
                  </div>
                  <VxeInput
                    v-else
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
                  <ListFilterSelect
                    v-if="column.key === 'mouse_strain' && sheetEditSource === 'dblclick'"
                    :model-value="splitMouseStrain(row.mouse_strain)"
                    joined
                    filterable
                    allow-create
                    default-first-option
                    class="sheet-strain-select"
                    popper-class="vxe-table--ignore-clear"
                    clearable
                    @change="onMouseStrainChange(row, $event, false)"
                    @visible-change="onMouseStrainSheetVisible"
                  >
                    <el-option v-for="item in mouseStrainOptions" :key="item" :label="item" :value="item" />
                    <el-option
                      v-for="item in extraMouseStrains(row.mouse_strain)"
                      :key="`extra-${item}`"
                      :label="item"
                      :value="item"
                    />
                  </ListFilterSelect>
                  <div v-else-if="sheetEditSource === 'dblclick' && isSheetChoiceForRow(column, row)" class="sheet-picker-editor">
                    <span class="sheet-picker-editor__value">{{ sheetPickerDisplayValue(row, column) }}</span>
                    <VxeSelect
                      v-model="row[column.key]"
                      class-name="sheet-grid-editor sheet-picker-control"
                      :filterable="isUserColumn(column)"
                      :clearable="!isRequiredChoice(column.key)"
                      :options="sheetChoiceSelectOptions(column, row)"
                      :popup-config="{ className: 'sheet-picker-popup', placement: 'bottom', width: 220 }"
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
              </vxe-column>
              <vxe-column
                v-else-if="column.edit === 'catalog'"
                :field="column.key"
                :title="sheetColumnTitle(column)"
                :min-width="column.minWidth || 150"
                :edit-render="{ name: 'VxeInput' }"
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
                      :popup-config="{ className: 'sheet-picker-popup', placement: 'bottom', width: 280 }"
                      :remote-config="{ autoLoad: false, queryMethod: querySheetCatalogOptions }"
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
              </vxe-column>
              <vxe-column
                v-else
                :field="column.key"
                :title="sheetColumnTitle(column)"
                :min-width="column.minWidth || column.width || 120"
                :edit-render="sheetEditRender(column)"
                :formatter="sheetFormatter(column)"
              >
                <template v-if="column.key === 'library_code'" #header>
                  <span class="library-code-head" :class="{ 'is-asc': libraryCodeOldestFirst }" :title="libraryCodeHeadTitle">建库编号</span>
                </template>
              </vxe-column>
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
          <div ref="sheetRangeOverlay" class="sheet-range-overlay" aria-hidden="true">
            <button
              v-if="showLibraryCodeFillHandle"
              type="button"
              class="library-code-fill-handle"
              title="往下按序号填充建库编号"
              aria-label="往下按序号填充建库编号"
              @mousedown.stop.prevent="onLibraryCodeFillStart"
            />
          </div>
          <div ref="sheetColumnDropLine" class="sheet-column-drop-line" aria-hidden="true" />
          <div ref="sheetColumnGhost" class="sheet-column-ghost" aria-hidden="true" />
        </div>
      </div>
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
              <template v-for="field in section.fields" :key="field.key">
              <el-form-item
                :label="field.label"
                :label-width="field.type === 'primer-matrix' ? '0' : undefined"
                :class="['drawer-field', field.wide ? 'is-wide' : '', isSyncedText(field) ? 'is-synced' : '']"
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
                <ListFilterSelect
                  v-else-if="field.key === 'mouse_strain'"
                  :model-value="splitMouseStrain(editingRow.mouse_strain)"
                  joined
                  filterable
                  allow-create
                  default-first-option
                  clearable
                  placeholder="选择小鼠品系"
                  style="width: 100%"
                  :disabled="!canEditField(editingRow, field.key)"
                  @change="onMouseStrainChange(editingRow, $event)"
                >
                  <el-option v-for="item in mouseStrainOptions" :key="item" :label="item" :value="item" />
                  <el-option
                    v-for="item in extraMouseStrains(editingRow.mouse_strain)"
                    :key="`extra-${item}`"
                    :label="item"
                    :value="item"
                  />
                </ListFilterSelect>
                <el-select
                  v-else-if="field.type === 'select'"
                  v-model="editingRow[field.key]"
                  style="width: 100%"
                  :clearable="!isRequiredChoice(field.key)"
                  :disabled="!canEditField(editingRow, field.key)"
                  @change="persistRow(editingRow, field.key)"
                >
                  <el-option v-for="item in field.options" :key="item.value || item" :label="item.label || item" :value="item.value || item" />
                </el-select>
                <el-input
                  v-else
                  v-model="editingRow[field.key]"
                  :disabled="!canEdit"
                  :type="isSyncedText(field) || field.type === 'textarea' ? 'textarea' : 'text'"
                  :rows="isSyncedText(field) ? 1 : undefined"
                  :autosize="isSyncedText(field) ? false : (field.type === 'textarea' ? { minRows: 1, maxRows: 4 } : undefined)"
                  @input="isSyncedText(field) && syncDrawerTextareas()"
                  @blur="persistRow(editingRow, field.key)"
                />
              </el-form-item>
              <div v-if="field.rowBreak" class="drawer-field-break" aria-hidden="true" />
              </template>
            </div>
          </article>
        </el-form>
      </div>
    </el-drawer>
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
        <el-button type="primary" :disabled="!createPick" @click="confirmCreate">创建</el-button>
      </template>
    </el-dialog>
    <LibraryResultUploadDialog v-model="resultUploadVisible" @uploaded="getList" />
  </div>
</template>

<script>
import { Download, Plus, Search, Tools, Upload } from '@element-plus/icons-vue'
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
  batchSaveLibraryOrders,
  deleteLibraryOrder,
  exportLibraryOrderList,
  fetchLibraryFilterOptions,
  fetchLibraryOrderList,
  LIBRARY_CREATED_KEY,
  saveLibraryOrder,
} from '#/api/molecularLibrary'
import { skipGlobalErrorHandler } from '#/api/request'
import { notifyApiError } from '#/api/errors'
import AdvancedOpsBar from '#/components/AdvancedOpsBar.vue'
import ListFilterSelect from '#/components/ListFilterSelect.vue'
import {
  cleanFieldText,
  coerceWorkbenchViewMode,
  createColumnOrder,
  readClipboardGrid,
  EXCEL_VIEW,
  searchWorkbenchTargets,
  splitTargetNames,
  targetNameFromCodes,
  uniqueTargetCodes,
  WORKBENCH_VIEW,
  WorkbenchDataTable,
  workbenchExcelMixin,
  WorkbenchStatusEditor,
  WorkbenchTargetSelect,
  WorkbenchViewToggle,
} from '#/components/workbench'
import SerumUserSelect from '../../Serum/shared/SerumUserSelect.vue'
import LibraryResultUploadDialog from './LibraryResultUploadDialog.vue'
import LibraryRowActions from './LibraryRowActions.vue'
import { downloadListExcel, excelTimestamp } from '#/utils/downloadExcel'
import { listTableLockMixin } from '#/utils/listTableLock'
import { canEditLibrary, canManageLibraryFiles, canViewLibraryDetail } from '#/utils/molecularPermission'
import { rememberDiscoveryFocus } from '#/views/Discovery/workbench/DiscoveryWorkbench.vue'
import { getSerumUserName } from '#/utils/serumPermission'
import { loadSerumUserOptions } from '#/utils/serumUserOptions'
import { getTiterPriorityTone } from '#/utils/serumProjectStatus'
import { loadListFilters, saveListFilters } from '#/utils/listFilterStorage'
import { shouldRefreshTabData } from '#/utils/staleTabRefresh'
import {
  allSheetColumns,
  BUILD_PLASMA_NGS,
  BUILD_TYPE_OPTIONS,
  buildTypeLabel,
  HANDOFF_METHOD_ROWS,
  CATALOG_NAME_FIELDS,
  CELL_TYPE_OPTIONS,
  INDEX_MODE_OPTIONS,
  MOUSE_STRAIN_OPTIONS,
  joinMouseStrain,
  splitMouseStrain,
  normalizePlateInputText,
  optionsForBuild,
  orderEditorSections,
  plateNumbersFromText,
  persistValue,
  plateNumbersText,
  isSyncedText,
  SYNC_TEXT_KEYS,
  syncPairedTextareas,
  PHAGE_EXPERIMENT_TYPE_OPTIONS,
  PLASMA_SAMPLE_TYPE_OPTIONS,
  CELL_TYPE_CHOICE_BUILDS,
  PRIORITY_OPTIONS,
  QC_RESULT_OPTIONS,
  REQUIRED_CHOICE_KEYS,
  SAMPLE_SOURCE_OPTIONS,
  SAMPLE_TYPE_OPTIONS,
  indexModeLabel,
  sampleSourceLabel,
  sampleTypeLabel,
  stampQcFields,
  isIndexFieldRecorded,
  isSheetFieldApplicable,
  sheetColumnsForBuild,
  STAT_TILES,
  STATUS_OPTIONS,
  STUDY_TYPE_OPTIONS,
  statusTone,
  TARGET_FORM_OPTIONS,
  typeGroup,
  WORKBENCH_COLUMNS,
} from './libraryColumns'
import { filterPrimerCatalog, loadPrimerCatalog } from './primerCatalogOptions'
import { filterTargetOptions, normalizeTargetOptions, targetOptionExtra as targetOptionHint } from '#/utils/targetFilterOptions'

const LIBRARY_LIST_FILTER_KEY = 'libraryConstructionList'

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
    order: '',
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
    if (code.length > SHEET_STRING_MAX.library_code) return null
    codes.push(code)
  }
  return codes
}

const SHEET_COLUMN_ORDER = createColumnOrder(
  'libraryConstructionSheetColumnOrder.v5',
  allSheetColumns(),
  { pinFirstKey: 'library_order_id' },
)
const INDEX_LINKED_KEYS = ['i7_catalog_id', 'i7_name', 'i7_sequence', 'i5_catalog_id', 'i5_name', 'i5_sequence']
const DERIVED_FIELDS = ['status', 'started_at', 'finished_at']
const SHEET_DATE_KEYS = [
  'received_on',
  'instrument_on',
  'blood_collected_on',
  'qc_on',
  'started_at',
  'finished_at',
]
const TEXT_BREAK_KEYS = new Set(['remark', 'qc_note', 'project_goal'])

function keepsLineBreaks(key) {
  return key === 'plate_nos' || SYNC_TEXT_KEYS.has(key) || TEXT_BREAK_KEYS.has(key)
}

const SHEET_STRING_MAX = {
  library_code: 64,
  source_project_code: 64,
  study_type: 64,
  project_goal: 1000,
  target_name: 128,
  pm: 64,
  mouse_strain: 128,
  positive_cell_count: 64,
  fragment_size_bp: 64,
  cell_type: 64,
  notebook_no: 64,
  immunization_stage: 64,
  library_batch_no: 64,
  owner: 64,
  rna_location: 255,
  cdna_location: 255,
  library_location: 255,
  initial_library_size: 64,
  effective_library_size: 64,
  cdna_concentration: 64,
  library_concentration: 64,
  h_primer_concentration: 64,
  k_primer_concentration: 64,
  l_primer_concentration: 64,
  h_forward_primer_name: 128,
  h_reverse_primer_name: 128,
  k_forward_primer_name: 128,
  k_reverse_primer_name: 128,
  l_forward_primer_name: 128,
  l_reverse_primer_name: 128,
  i7_name: 128,
  i7_sequence: 64,
  i5_name: 128,
  i5_sequence: 64,
  qc_owner: 64,
  qc_note: 1000,
  remark: 1000,
}

export default {
  name: 'LibraryConstructionList',
  mixins: [workbenchExcelMixin, listTableLockMixin],
  components: {
    AdvancedOpsBar,
    ListFilterSelect,
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
    LibraryResultUploadDialog,
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
    return { Download, Plus, Search, Upload }
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
      targetOptions: [],
      targetRequestToken: 0,
      catalogQuery: '',
      primerCatalog: [],
      catalogLoading: false,
      recordedTargetOptions: [],
      targetFilterQuery: '',
      consumingCreated: false,
      createVisible: false,
      resultUploadVisible: false,
      createPick: '',
      drawerPointerBound: false,
      sheetColumns: allSheetColumns(),
      listLoaded: false,
      tabDataFetchedAt: 0,
      libraryCodeFill: null,
    }
  },
  computed: {
    catalogOptions() {
      return filterPrimerCatalog(this.primerCatalog, this.catalogQuery)
    },
    canEdit() {
      return canEditLibrary(useUserStore().userInfo)
    },
    libraryCodeOldestFirst() {
      return this.listQuery.order === 'id_asc'
    },
    libraryCodeHeadTitle() {
      return this.libraryCodeOldestFirst
        ? '当前按创建时间正序，右键恢复倒序'
        : '右键改为按创建时间正序，方便接着往下编号'
    },
    showLibraryCodeFillHandle() {
      if (!this.canEdit || !this.isExcelMode || !this.libraryCodeOldestFirst) return false
      const range = this.normalizedSheetRange()
      if (!range || range.c1 !== range.c2) return false
      if (this.sheetColumns[range.c1]?.key !== 'library_code') return false
      return Boolean(this.libraryCodeFill) || range.r1 === range.r2
    },
    canViewDetail() {
      return canViewLibraryDetail(useUserStore().userInfo)
    },
    canManageFiles() {
      return canManageLibraryFiles(useUserStore().userInfo)
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
      return STAT_TILES.map((item, index) => ({
        ...item,
        tone: tones[index % tones.length],
      }))
    },
    statusOptions() {
      return STATUS_OPTIONS
    },
    priorityOptions() {
      return PRIORITY_OPTIONS
    },
    sheetTargetSelectOptions() {
      return this.targetOptions.map((item) => ({
        label: `${item.name}（${item.snum}）`,
        value: item.snum,
      }))
    },
    sheetCatalogSelectOptions() {
      const options = this.catalogOptions.map((item) => ({
        label: item.short_sequence ? `${item.name} ${item.short_sequence}` : item.name,
        value: item.name,
      }))
      return options
    },
    sampleSourceOptions() {
      return SAMPLE_SOURCE_OPTIONS.map((item) => ({
        value: item.value,
        label: item.label,
      }))
    },
    sampleTypeOptions() {
      return SAMPLE_TYPE_OPTIONS.map((item) => ({
        value: item.value,
        label: item.label,
      }))
    },
    mouseStrainOptions() {
      return MOUSE_STRAIN_OPTIONS
    },
    workbenchColumns() {
      return WORKBENCH_COLUMNS
    },
    typeOptions() {
      return BUILD_TYPE_OPTIONS
    },
    studyTypeOptions() {
      return STUDY_TYPE_OPTIONS
    },
    cellTypeOptions() {
      return CELL_TYPE_OPTIONS
    },
    createRows() {
      return HANDOFF_METHOD_ROWS
    },
    createPicks() {
      return HANDOFF_METHOD_ROWS.flatMap((row) => row.picks)
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
    filteredTargetOptions() {
      return filterTargetOptions(this.recordedTargetOptions, this.targetFilterQuery)
    },
  },
  created() {
    this.restoreListFilters()
    this.viewMode = coerceWorkbenchViewMode(this.viewMode)
    this.rebuildSheetColumns()
    this.loadAllUserOptions()
    this.loadTargetFilterOptions()
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
  beforeRouteLeave(_to, _from, next) {
    this.persistListFilters()
    next()
  },
  beforeUnmount() {
    this.persistListFilters()
    this.stopLibraryCodeFill()
    this.unbindDrawerPointer()
  },
  deactivated() {
    this.stopLibraryCodeFill()
    this.closeDrawer()
    this.unbindDrawerPointer()
  },
  watch: {
    '$route.query.created'() {
      this.consumeCreatedQuery()
    },
    'listQuery.build_type'() {
      this.clearSheetRange()
      this.rebuildSheetColumns()
    },
    drawerVisible(open) {
      if (open) this.syncDrawerTextareas()
    },
    editingId() {
      if (this.drawerVisible) this.syncDrawerTextareas()
    },
  },
  methods: {
    isSyncedText,
    syncDrawerTextareas() {
      this.$nextTick(() => syncPairedTextareas('.workbench-drawer .drawer-field.is-synced textarea'))
    },
    buildTypeLabel,
    indexModeLabel,
    joinMouseStrain,
    splitMouseStrain,
    sampleSourceLabel,
    sampleTypeLabel,
    statusTone,
    priorityTone(row) {
      return getTiterPriorityTone(row?.priority)
    },
    typeGroup,
    isRequiredChoice(key) {
      return REQUIRED_CHOICE_KEYS.includes(key)
    },
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
    async filterCatalog(query = '') {
      this.catalogQuery = String(query || '')
      if (!this.catalogQuery.trim() || this.primerCatalog.length) return
      this.catalogLoading = true
      try {
        this.primerCatalog = await loadPrimerCatalog()
      } catch {
        this.primerCatalog = []
      } finally {
        this.catalogLoading = false
      }
    },
    async onCatalogChange(row, field, value) {
      if (!row) return
      const selected = this.primerCatalog.find((item) => item.name === value)
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
      if (key === 'build_type') return !this.activeType && (row?.status || '待处理') === '待处理'
      return true
    },
    isSheetCellLocked(row, key) {
      if (!this.canEditField(row, key)) return true
      if (!isSheetFieldApplicable(row?.build_type, key)) return true
      if (!isIndexFieldRecorded(row?.build_type, row?.index_mode, key)) return true
      const column = this.sheetColumns.find((item) => item.key === key)
      return column?.edit === 'readonly'
    },
    onLockedSheetDblClick(row, key) {
      const label = this.sheetColumns.find((item) => item.key === key)?.label || '该字段'
      if (!isSheetFieldApplicable(row?.build_type, key)) {
        ElMessage.info(`${buildTypeLabel(row.build_type) || '当前建库类型'}没有「${label}」`)
        return
      }
      if (!isIndexFieldRecorded(row?.build_type, row?.index_mode, key)) {
        ElMessage.info(`当前 Barcode 方式不填写「${label}」`)
      }
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
    handleFilter() {
      this.listQuery.page = 1
      this.getList()
    },
    onWorkbenchHeaderContextMenu(column, event) {
      if (column?.key !== 'library_code') return
      event.preventDefault()
      this.showLibraryCodesInCreatedOrder()
    },
    onSheetContextMenu(event) {
      const headerHit = this.hitSheetHeader(event.target)
      const column = headerHit ? this.sheetColumns[headerHit.colIndex] : null
      if (column?.key === 'library_code') {
        event.preventDefault()
        this.showLibraryCodesInCreatedOrder()
        return
      }
      this.onSheetWrapContextMenu(event)
    },
    async showLibraryCodesInCreatedOrder() {
      if (this.isExcelMode && !await this.flushPendingSheetEdits()) return
      this.clearSheetRange?.()
      const oldestFirst = !this.libraryCodeOldestFirst
      this.listQuery.order = oldestFirst ? 'id_asc' : ''
      this.listQuery.page = oldestFirst ? 1_000_000 : 1
      if (await this.getList()) {
        ElMessage.success(oldestFirst ? '已改为创建时间正序' : '已恢复创建时间倒序')
      }
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
      if (!hit || hit.colIndex !== fill.colIndex || hit.rowIndex < fill.rowIndex) return
      if (this.sheetRange?.r2 === hit.rowIndex && this.sheetRange?.c2 === fill.colIndex) return
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
      const range = this.normalizedSheetRange()
      this.stopLibraryCodeFill()
      if (!fill || !range || range.r2 <= fill.rowIndex) {
        if (fill) {
          this.setSheetRange({
            r1: fill.rowIndex,
            c1: fill.colIndex,
            r2: fill.rowIndex,
            c2: fill.colIndex,
          })
        }
        return
      }
      await this.fillLibraryCodesDown(fill.rowIndex, range.r2, fill.colIndex)
    },
    async fillLibraryCodesDown(startIndex, endIndex, colIndex) {
      if (!this.libraryCodeOldestFirst) return
      if (!await this.flushPendingSheetEdits()) return
      const column = this.sheetColumns[colIndex]
      const seedRow = this.list[startIndex]
      if (!seedRow || column?.key !== 'library_code') return
      const targets = this.list.slice(startIndex + 1, endIndex + 1)
      if (targets.some((row) => this.isSheetCellLocked(row, 'library_code'))) {
        ElMessage.warning('选中的建库编号有不能修改的格子，本次未填充')
        this.setSheetRange({ r1: startIndex, c1: colIndex, r2: startIndex, c2: colIndex })
        return
      }
      const codes = libraryCodeSeries(seedRow.library_code, targets.length)
      if (!codes) {
        ElMessage.warning('建库编号末尾要有数字才能往下填充')
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
        const saved = await batchSaveLibraryOrders(targets.map((row, index) => ({
          id: row.id,
          library_code: codes[index],
        })))
        const savedById = new Map((saved?.items || []).map((item) => [item.id, item]))
        targets.forEach((row) => {
          const item = savedById.get(row.id)
          if (item) this.applySavedFields(this.normalizeRow(item), ['library_code'])
        })
        ElMessage.success(`已填充 ${targets.length} 个建库编号`)
        this.setSheetRange({ r1: startIndex, c1: colIndex, r2: endIndex, c2: colIndex })
      } catch (error) {
        notifyApiError(error, { messages: { default: '建库编号填充失败' } })
        this.setSheetRange({ r1: startIndex, c1: colIndex, r2: startIndex, c2: colIndex })
      }
    },
    resetFilters() {
      this.listQuery = emptyQuery()
      this.instrumentRange = []
      this.startedRange = []
      this.finishedRange = []
      this.targetFilterQuery = ''
      this.persistListFilters()
      this.getList()
    },
    persistListFilters() {
      saveListFilters(LIBRARY_LIST_FILTER_KEY, {
        // 排序不存，正序下的页码换到默认倒序里是另一批行
        listQuery: { ...this.listQuery, order: undefined, page: this.listQuery.order ? 1 : this.listQuery.page },
        instrumentRange: this.instrumentRange,
        startedRange: this.startedRange,
        finishedRange: this.finishedRange,
      })
    },
    restoreListFilters() {
      const state = loadListFilters(LIBRARY_LIST_FILTER_KEY)
      if (!state) return
      if (state.listQuery && typeof state.listQuery === 'object') {
        const saved = { ...state.listQuery }
        if (saved.keyword && !saved.library_code) saved.library_code = saved.keyword
        delete saved.keyword
        if (saved.target) saved.target_name = ''
        delete saved.target
        Object.assign(this.listQuery, saved)
      }
      if (Array.isArray(state.instrumentRange)) this.instrumentRange = state.instrumentRange
      if (Array.isArray(state.startedRange)) this.startedRange = state.startedRange
      if (Array.isArray(state.finishedRange)) this.finishedRange = state.finishedRange
    },
    setTargetFilterQuery(query) {
      this.targetFilterQuery = query || ''
    },
    targetOptionExtra(item) {
      return targetOptionHint(item, this.targetFilterQuery)
    },
    async loadTargetFilterOptions() {
      try {
        const data = await fetchLibraryFilterOptions()
        this.recordedTargetOptions = normalizeTargetOptions(data?.targets)
      } catch {
        this.recordedTargetOptions = []
      }
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
      if (Array.isArray(value)) return value.map((item) => String(item || '').trim()).filter(Boolean)
      const text = String(value || '').trim()
      return text ? [text] : []
    },
    async getList({ flushEditor = true } = {}) {
      const requestId = ++this.listRequestId
      this.loading = true
      try {
        if (flushEditor) await this.flushPendingSheetEdits()
        const data = await fetchLibraryOrderList(this.buildQuery(), skipGlobalErrorHandler)
        if (requestId !== this.listRequestId) return false
        this.list = (data?.items || []).map((row) => this.normalizeRow(row))
        this.list.forEach((row) => this.updateRowBaseline(row))
        this.total = data?.total || 0
        if (data?.page) this.listQuery.page = data.page
        this.stats = { ...Object.fromEntries(this.typeSheets.map((item) => [item.statKey, 0])), ...(data?.stats || {}) }
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
        return true
      } catch (error) {
        if (requestId !== this.listRequestId) return false
        notifyApiError(error, { messages: { default: '加载文库工单失败' } })
        return false
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
    async persistRow(row, field, { linkCatalog = false } = {}) {
      if (!this.canEdit || !row?.id) return
      const baseline = this.rowBaselines.get(row.id)
      const catalogMeta = linkCatalog ? CATALOG_NAME_FIELDS[field] : null
      if (typeof row[field] === 'string') {
        row[field] = cleanFieldText(row[field], {
          keepBreaks: keepsLineBreaks(field),
        })
      }
      row[field] = persistValue(row[field])
      if (catalogMeta) {
        const selected = row[field] ? this.primerCatalog.find((item) => item.name === row[field]) : null
        row[catalogMeta.idKey] = selected?.id || null
        if (catalogMeta.sequenceKey) row[catalogMeta.sequenceKey] = selected?.short_sequence || null
      }
      const targetField = field === 'target_codes' || field === 'target_name'
      const catalogDirty = Boolean(catalogMeta) && (
        !this.sameFieldValue(baseline?.[catalogMeta.idKey], row[catalogMeta.idKey])
        || (catalogMeta.sequenceKey && !this.sameFieldValue(baseline?.[catalogMeta.sequenceKey], row[catalogMeta.sequenceKey]))
      )
      if (baseline && this.sameFieldValue(baseline[field], row[field]) && !catalogDirty) {
        const pairedTargetUnchanged = this.sameFieldValue(baseline.target_name, row.target_name)
          && this.sameFieldValue(baseline.target_codes, row.target_codes)
        if (!targetField || pairedTargetUnchanged) return
      }
      const qcFields = field === 'qc_result'
        ? stampQcFields(row, getSerumUserName(useUserStore().userInfo))
        : []
      try {
        const payload = { id: row.id, [field]: row[field] }
        if (targetField) {
          payload.target_codes = row.target_codes
          payload.target_name = row.target_name
        }
        if (catalogMeta) {
          payload[catalogMeta.idKey] = row[catalogMeta.idKey] || null
          if (catalogMeta.sequenceKey) payload[catalogMeta.sequenceKey] = row[catalogMeta.sequenceKey] || null
        }
        qcFields.forEach((key) => {
          payload[key] = row[key]
        })
        const saved = await saveLibraryOrder(payload)
        const savedFields = targetField
          ? ['target_codes', 'target_name']
          : catalogMeta
            ? [field, catalogMeta.idKey, ...(catalogMeta.sequenceKey ? [catalogMeta.sequenceKey] : [])]
            : field === 'mouse_strain'
              ? [field, 'sample_type']
              : field === 'index_mode'
                ? [field, ...INDEX_LINKED_KEYS]
                : [field]
        this.applySavedFields(
          this.normalizeRow(saved),
          field === 'build_type' ? undefined : [...savedFields, ...qcFields, ...DERIVED_FIELDS],
        )
      } catch (error) {
        if (baseline) {
          row[field] = baseline[field]
          if (field === 'target_codes') row.target_name = baseline.target_name
          if (catalogMeta) {
            row[catalogMeta.idKey] = baseline[catalogMeta.idKey]
            if (catalogMeta.sequenceKey) row[catalogMeta.sequenceKey] = baseline[catalogMeta.sequenceKey]
          }
          qcFields.forEach((key) => {
            row[key] = baseline[key]
          })
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
      rememberDiscoveryFocus(id)
      this.$router.push({ name: 'DiscoveryWorkbench' })
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
    flushDrawerEdit() {
      const active = document.activeElement
      if (!(active instanceof HTMLElement) || !active.closest('.el-drawer')) return
      active.blur()
    },
    closeDrawer() {
      this.flushDrawerEdit()
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
      this.flushDrawerEdit()
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
      const matched = this.createPicks.filter((item) => {
        if (item.buildType !== this.activeType) return false
        return !item.sampleType || item.sampleType === this.listQuery.sample_type
      })
      this.createPick = (matched[0] || this.createPicks[0])?.id || ''
      this.createVisible = true
    },
    async confirmCreate() {
      const pick = this.createPicks.find((item) => item.id === this.createPick)
      if (!pick) {
        ElMessage.warning('请选择类型')
        return
      }
      try {
        const saved = await saveLibraryOrder({
          build_type: pick.buildType,
          sample_source: pick.source,
          ...(pick.sampleType ? { sample_type: pick.sampleType } : {}),
        })
        this.createVisible = false
        if (this.isExcelMode) {
          this.listQuery.page = this.libraryCodeOldestFirst ? 1_000_000 : 1
          await this.getList({ flushEditor: false })
          return
        }
        await this.getList({ flushEditor: false })
        this.openDrawer(this.normalizeRow(saved))
      } catch (error) {
        notifyApiError(error, { messages: { default: '新建失败' } })
      }
    },
    async handleListExport() {
      try {
        await downloadListExcel(
          () => {
            const query = this.buildQuery()
            delete query.order
            return exportLibraryOrderList(query)
          },
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
      return ['pm', 'owner', 'qc_owner'].includes(column?.key)
    },
    isSheetChoiceColumn(column) {
      return column?.edit === 'select'
    },
    extraMouseStrains(value) {
      const known = new Set(MOUSE_STRAIN_OPTIONS)
      return splitMouseStrain(value).filter((item) => !known.has(item))
    },
    onMouseStrainChange(row, values, persist = true) {
      row.mouse_strain = joinMouseStrain(values) || null
      if (persist && this.sheetEditSource !== 'dblclick') this.persistRow(row, 'mouse_strain')
    },
    mouseStrainSheetSelect() {
      return document.querySelector('.sheet-strain-select')?.__vueParentComponent?.proxy
    },
    onMouseStrainSheetVisible(visible) {
      if (visible) return
      this.$nextTick(() => {
        if (this.mouseStrainSheetSelect()?.expanded) return
        this.$refs.sheetTable?.clearEdit?.()
      })
    },
    openSheetEditorPanel(row, key) {
      if (key !== 'mouse_strain') {
        workbenchExcelMixin.methods.openSheetEditorPanel.call(this, row, key)
        return
      }
      const open = () => {
        const select = this.mouseStrainSheetSelect()
        if (!select) return false
        select.expanded = true
        return true
      }
      this.$nextTick(() => {
        if (!open()) this.$nextTick(open)
      })
    },
    isSheetChoiceForRow(column, row) {
      return column.key !== 'cell_type' || CELL_TYPE_CHOICE_BUILDS.includes(row?.build_type)
    },
    sheetChoiceSelectOptions(column, row) {
      if (column.key === 'study_type') return STUDY_TYPE_OPTIONS.map((item) => ({ label: item, value: item }))
      if (column.key === 'target_forms') return TARGET_FORM_OPTIONS.map((item) => ({ label: item, value: item }))
      if (column.key === 'priority') return this.priorityOptions.map((item) => ({ label: item, value: item }))
      if (column.key === 'status') return this.statusOptions.map((item) => ({ label: item, value: item }))
      if (column.key === 'build_type') return this.typeOptions
      if (column.key === 'sample_source') return optionsForBuild(SAMPLE_SOURCE_OPTIONS, row?.build_type)
      if (column.key === 'sample_type') {
        return row?.build_type === BUILD_PLASMA_NGS ? PLASMA_SAMPLE_TYPE_OPTIONS : SAMPLE_TYPE_OPTIONS
      }
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
      if (key === 'sample_source') return sampleSourceLabel(row[key])
      if (key === 'sample_type') return sampleTypeLabel(row[key])
      if (key === 'index_mode') return indexModeLabel(row[key])
      if (key === 'target_codes') return uniqueTargetCodes(row[key]).join(',')
      if (key === 'plate_nos') {
        return Array.isArray(row[key]) ? row[key].join('、') : (row[key] || '')
      }
      return row[key] == null ? '' : String(row[key])
    },
    sheetFormatter(column) {
      if (column.key === 'build_type') return ({ cellValue }) => buildTypeLabel(cellValue) || ''
      if (column.key === 'sample_source') return ({ cellValue }) => sampleSourceLabel(cellValue) || ''
      if (column.key === 'sample_type') return ({ cellValue }) => sampleTypeLabel(cellValue) || ''
      if (column.key === 'index_mode') return ({ cellValue }) => indexModeLabel(cellValue) || ''
      if (column.key === 'target_codes') return ({ row }) => uniqueTargetCodes(row.target_codes).join(',')
      if (column.key === 'plate_nos') {
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
    sheetPickerDisplayValue(row, column) {
      return column.edit === 'target'
        ? this.sheetTargetDirectValue(row, column.key)
        : this.sheetDirectTextValue(row, column.key)
    },
    async searchTargetOptions(keyword, selectedCodes) {
      const requestToken = ++this.targetRequestToken
      try {
        const items = await searchWorkbenchTargets(keyword, selectedCodes)
        if (requestToken === this.targetRequestToken) this.targetOptions = items
      } catch {
        if (requestToken === this.targetRequestToken) this.targetOptions = this.targetOptions || []
      }
    },
    querySheetTargetOptions({ searchValue }) {
      const row = this.list[this.pasteAnchor?.rowIndex]
      return this.searchTargetOptions(searchValue, row?.target_codes)
    },
    onSheetTargetPickerChange(row) {
      const codes = uniqueTargetCodes(row.target_codes)
      row.target_codes = codes
      row.target_name = targetNameFromCodes(codes, this.targetOptions)
    },
    querySheetCatalogOptions({ searchValue }) {
      return this.filterCatalog(searchValue)
    },
    sheetOptionValue(options, raw) {
      const text = String(raw || '').trim().toLowerCase()
      const matched = options.find((item) => (
        String(item.value ?? item).toLowerCase() === text
        || String(item.label ?? item).toLowerCase() === text
      ))
      return matched ? (matched.value ?? matched) : undefined
    },
    normalizeSheetDate(text) {
      const raw = String(text ?? '').trim()
      if (!raw) return { ok: true, value: null }
      const match = /^(\d{4})-(\d{2})-(\d{2})(?:\s+\d{2}:\d{2}(?::\d{2})?)?$/.exec(raw)
      if (!match) return { ok: false, reason: 'date' }
      const year = Number(match[1])
      const month = Number(match[2])
      const day = Number(match[3])
      const date = new Date(Date.UTC(year, month - 1, day))
      const valid = date.getUTCFullYear() === year
        && date.getUTCMonth() === month - 1
        && date.getUTCDate() === day
      return valid ? { ok: true, value: `${match[1]}-${match[2]}-${match[3]}` } : { ok: false, reason: 'date' }
    },
    normalizeSheetSequence(text) {
      const raw = String(text ?? '').replace(/\s+/g, '').toUpperCase()
      if (!raw) return { ok: true, value: null }
      if (raw.length > SHEET_STRING_MAX.i7_sequence) return { ok: false, reason: 'length' }
      return /^[ACGTRYSWKMBDHVN]+$/.test(raw)
        ? { ok: true, value: raw }
        : { ok: false, reason: 'sequence' }
    },
    sheetTextLimit(key, raw) {
      const maxLen = SHEET_STRING_MAX[key]
      if (maxLen && String(raw || '').length > maxLen) return { ok: false, reason: 'length' }
      return { ok: true, value: raw || null }
    },
    coerceSheetValue(row, key, text) {
      const keepBreaks = keepsLineBreaks(key)
      const raw = Array.isArray(text)
        ? text.join(',')
        : cleanFieldText(text, { keepBreaks })
      if (key === 'plate_nos') {
        return {
          ok: true,
          value: plateNumbersFromText(raw),
        }
      }
      if (key === 'target_forms') {
        if (!raw) return { ok: true, value: null }
        const value = this.sheetOptionValue(TARGET_FORM_OPTIONS.map((item) => ({ label: item, value: item })), raw)
        return value ? { ok: true, value } : { ok: false, reason: 'option' }
      }
      if (key === 'study_type') {
        if (!raw) return { ok: true, value: null }
        const value = this.sheetOptionValue(STUDY_TYPE_OPTIONS.map((item) => ({ label: item, value: item })), raw)
        return value ? { ok: true, value } : { ok: false, reason: 'option' }
      }
      if (SHEET_DATE_KEYS.includes(key)) return this.normalizeSheetDate(raw)
      if (key === 'build_type') {
        const value = this.sheetOptionValue(this.typeOptions, raw)
        return value ? { ok: true, value } : { ok: false, reason: 'option' }
      }
      if (key === 'mouse_strain') {
        if (!raw) return { ok: true, value: null }
        const value = joinMouseStrain(raw)
        return value ? { ok: true, value } : { ok: true, value: null }
      }
      if (key === 'sample_source') {
        if (!raw) return { ok: true, value: null }
        const allowed = optionsForBuild(SAMPLE_SOURCE_OPTIONS, row?.build_type)
        const value = this.sheetOptionValue(allowed, raw)
        if (value) return { ok: true, value }
        return { ok: false, reason: this.sheetOptionValue(SAMPLE_SOURCE_OPTIONS, raw) ? 'source' : 'option' }
      }
      if (key === 'sample_type') {
        if (!raw) return { ok: true, value: null }
        const plasma = row?.build_type === BUILD_PLASMA_NGS
        const options = plasma ? PLASMA_SAMPLE_TYPE_OPTIONS : SAMPLE_TYPE_OPTIONS
        const value = this.sheetOptionValue(options, raw)
        if (value) return { ok: true, value }
        const known = this.sheetOptionValue(SAMPLE_TYPE_OPTIONS, raw)
        return { ok: false, reason: plasma && known ? 'plasma' : 'option' }
      }
      if (key === 'cell_type' && CELL_TYPE_CHOICE_BUILDS.includes(row?.build_type) && raw && !CELL_TYPE_OPTIONS.includes(raw)) {
        return { ok: false, reason: 'cell' }
      }
      if (key === 'source_experiment_type') {
        return !raw || PHAGE_EXPERIMENT_TYPE_OPTIONS.includes(raw)
          ? { ok: true, value: raw || null }
          : { ok: false, reason: 'option' }
      }
      if (key === 'index_mode') {
        if (!raw) return { ok: true, value: null }
        const value = this.sheetOptionValue(INDEX_MODE_OPTIONS, raw)
        return value ? { ok: true, value } : { ok: false, reason: 'option' }
      }
      if (key === 'qc_result') {
        return !raw || QC_RESULT_OPTIONS.includes(raw)
          ? { ok: true, value: raw || null }
          : { ok: false, reason: 'option' }
      }
      if (key === 'status') return STATUS_OPTIONS.includes(raw) ? { ok: true, value: raw } : { ok: false, reason: 'option' }
      if (key === 'priority') return PRIORITY_OPTIONS.includes(raw) ? { ok: true, value: raw } : { ok: false, reason: 'option' }
      if (this.isUserColumn({ key })) {
        if (!raw) return { ok: true, value: null }
        const hit = this.allUserOptions.find((item) => item === raw || item.toLowerCase() === raw.toLowerCase())
        return hit ? { ok: true, value: hit } : { ok: false, reason: 'option' }
      }
      if (key === 'i7_sequence' || key === 'i5_sequence') return this.normalizeSheetSequence(raw)
      if (key === 'library_code') return this.sheetTextLimit(key, raw.toUpperCase())
      if (key === 'target_codes') return { ok: true, value: uniqueTargetCodes(raw.split(/[,，、]/)) }
      if (key === 'target_name') return this.sheetTextLimit(key, raw)
      return this.sheetTextLimit(key, raw)
    },
    assignSheetValue(row, key, text) {
      const column = allSheetColumns().find((item) => item.key === key)
      if (!column) return { ok: false, reason: 'unknown' }
      const result = this.coerceSheetValue(row, key, text)
      if (this.isSheetCellLocked(row, key)) {
        if (result.ok && this.sameSheetValue(key, result.value, row[key])) return { ok: true, skipped: true }
        if (!isSheetFieldApplicable(row?.build_type, key)) return { ok: false, reason: 'inapplicable' }
        if (!isIndexFieldRecorded(row?.build_type, row?.index_mode, key)) return { ok: false, reason: 'index' }
        return { ok: false, reason: column.edit === 'readonly' ? 'readonly' : 'locked' }
      }
      if (!result.ok) return result
      this.restoreSheetEditValue(row, key, result.value)
      return { ok: true }
    },
    sheetValidationMessage(key, reason) {
      const label = this.sheetColumns.find((item) => item.key === key)?.label
        || allSheetColumns().find((item) => item.key === key)?.label
        || '当前字段'
      if (reason === 'date') return `${label}必须是 YYYY-MM-DD 格式的有效日期`
      if (reason === 'sequence') return `${label}只能包含 IUPAC 碱基字符`
      if (reason === 'index') return `当前 Barcode 方式不填写「${label}」`
      if (reason === 'plasma') return '浆细胞 NGS 的样品类型只能是 Nano 或 Lite'
      if (reason === 'source') return '样品来源与当前建库类型不匹配'
      if (reason === 'cell') return '细胞类型只能是全细胞、浆细胞或流穿液'
      if (reason === 'inapplicable') return `当前建库类型没有「${label}」`
      if (reason === 'length') {
        const maxLen = SHEET_STRING_MAX[key]
        return maxLen ? `${label}不能超过 ${maxLen} 个字` : `${label}超出长度限制`
      }
      if (reason === 'readonly') return `${label}与当前行不一致`
      if (reason === 'locked') return `${label}当前不可编辑`
      if (reason === 'unknown') return '粘贴内容包含无法识别的列'
      return `${label}必须与可选项完全匹配`
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
      const pickingTarget = this.sheetEditSource === 'dblclick' && (key === 'target_codes' || key === 'target_name')
      const pickingCatalog = this.sheetEditSource === 'dblclick' && Boolean(CATALOG_NAME_FIELDS[key])
      this.sheetEditSource = ''
      if (!key || !row?.id) return
      const originalValue = this.takeSheetEditOriginal(row, key)
      if (this.isSheetCellLocked(row, key)) {
        if (pickingTarget) this.restoreSheetTarget(row, key, originalValue)
        else this.restoreSheetEditValue(row, key, originalValue)
        return
      }
      const source = key === 'target_codes' ? row.target_codes : row[key]
      const result = this.coerceSheetValue(row, key, source)
      if (!result.ok) {
        if (pickingTarget) this.restoreSheetTarget(row, key, originalValue)
        else this.restoreSheetEditValue(row, key, originalValue)
        ElMessage.warning(this.sheetValidationMessage(key, result.reason))
        return
      }
      if (!pickingTarget && !pickingCatalog && this.sameSheetValue(key, result.value, originalValue)) {
        this.restoreSheetEditValue(row, key, originalValue)
        return
      }
      this.restoreSheetEditValue(row, key, result.value)
      if (pickingTarget) {
        const baseline = this.rowBaselines.get(row.id)
        if (
          this.sameSheetValue('target_codes', row.target_codes, baseline?.target_codes)
          && this.sameSheetValue('target_name', row.target_name, baseline?.target_name)
        ) {
          return
        }
      }
      if (key === 'target_codes' || key === 'target_name') {
        if (!await this.applySheetTarget(row, pickingTarget ? 'target_codes' : key, originalValue)) return
      }
      const baseline = this.rowBaselines.get(row.id)
      const unchanged = key === 'target_codes' || key === 'target_name'
        ? this.sameSheetValue('target_codes', row.target_codes, baseline?.target_codes)
          && this.sameSheetValue('target_name', row.target_name, baseline?.target_name)
        : this.sameSheetValue(key, row[key], originalValue)
      if (unchanged) {
        this.restoreSheetEditValue(row, key, originalValue)
        if ((key === 'target_codes' || key === 'target_name') && baseline) {
          row.target_codes = this.cloneSheetValue(baseline.target_codes)
          row.target_name = baseline.target_name
        }
        return
      }
      await this.persistRow(row, key, { linkCatalog: pickingCatalog })
    },
    async resolveTargetCodes(codes) {
      const normalized = uniqueTargetCodes(codes)
      if (!normalized.length) return { missing: [], nameByCode: new Map(), names: [] }
      const items = await searchWorkbenchTargets('', normalized)
      const nameByCode = new Map(items.map((item) => [item.snum, item.name]))
      return {
        missing: normalized.filter((code) => !nameByCode.has(code)),
        nameByCode,
        names: normalized.map((code) => nameByCode.get(code)),
      }
    },
    async resolveTargetNames(value) {
      const names = splitTargetNames(value)
      if (!names.length) return { ambiguous: [], items: [], missing: [] }
      const results = await Promise.all(names.map(async (name) => {
        const items = await searchWorkbenchTargets(name)
        const exact = items.filter((item) => String(item.name || '').trim().toLowerCase() === name.toLowerCase())
        return { exact, name }
      }))
      const missing = results.filter((item) => item.exact.length === 0).map((item) => item.name)
      const ambiguous = results.filter((item) => item.exact.length > 1).map((item) => item.name)
      const matched = results.filter((item) => item.exact.length === 1)
      return {
        ambiguous,
        items: matched.map((item) => item.exact[0]),
        missing,
      }
    },
    async applySheetTarget(row, key, originalValue) {
      const submittedCodes = uniqueTargetCodes(row.target_codes)
      const submittedName = String(row.target_name || '')
      try {
        if (key === 'target_codes') {
          const resolved = await this.resolveTargetCodes(submittedCodes)
          if (!this.sameSheetValue('target_codes', row.target_codes, submittedCodes)) return false
          if (resolved.missing.length) {
            this.restoreSheetTarget(row, key, originalValue)
            ElMessage.warning(`未找到靶点编号：${resolved.missing.join('、')}`)
            return false
          }
          row.target_codes = submittedCodes
          row.target_name = resolved.names.join('&')
          return true
        }
        const resolved = await this.resolveTargetNames(submittedName)
        if (!this.sameSheetValue('target_name', row.target_name, submittedName)) return false
        if (resolved.missing.length) {
          this.restoreSheetTarget(row, key, originalValue)
          ElMessage.warning(`未找到靶点名称：${resolved.missing.join('、')}`)
          return false
        }
        if (resolved.ambiguous.length) {
          this.restoreSheetTarget(row, key, originalValue)
          ElMessage.warning(`靶点名称不唯一，请改用靶点编号：${resolved.ambiguous.join('、')}`)
          return false
        }
        row.target_codes = resolved.items.map((item) => item.snum)
        row.target_name = resolved.items.map((item) => item.name).join('&')
        return true
      } catch {
        this.restoreSheetTarget(row, key, originalValue)
        ElMessage.warning('靶点校验失败，本次修改未保存')
        return false
      }
    },
    restoreSheetTarget(row, key, originalValue) {
      const baseline = this.rowBaselines.get(row.id)
      if (!baseline) {
        this.restoreSheetEditValue(row, key, originalValue)
        return
      }
      row.target_codes = this.cloneSheetValue(baseline.target_codes)
      row.target_name = baseline.target_name
    },
    async onSheetPaste(event) {
      if (!this.canEdit) return
      if (event.target?.closest?.('input, textarea')) return
      const plain = event.clipboardData?.getData('text/plain') || ''
      const grid = readClipboardGrid(event.clipboardData)
      if (!grid.length) return
      const singleValue = grid.length === 1
        && grid[0].length === 1
        && !String(grid[0][0]).includes('\n')
      if (!plain.includes('\t') && !plain.includes('\n') && singleValue && !this.sheetRange) return
      event.preventDefault()
      if (!await this.flushPendingSheetEdits()) return
      const columns = allSheetColumns()
      const labelToKey = new Map(columns.map((column) => [column.label, column.key]))
      const headerKeys = grid[0].map((cell) => labelToKey.get(String(cell || '').trim()) || null)
      const nonEmptyHeaderCount = grid[0].filter((cell) => String(cell || '').trim()).length
      const matchedHeaderCount = headerKeys.filter(Boolean).length
      const hasHeader = matchedHeaderCount >= 2 && matchedHeaderCount === nonEmptyHeaderCount
      const orderIdHeaderIndex = hasHeader ? headerKeys.indexOf('library_order_id') : -1
      const matchRowsByOrderId = orderIdHeaderIndex >= 0
      let dataRows = hasHeader ? grid.slice(1) : grid
      let startIndex = this.pasteAnchor?.rowIndex ?? 0
      const startColKey = this.pasteAnchor?.colKey || this.sheetColumns[0]?.key
      let startColIndex = this.sheetColumns.findIndex((column) => column.key === startColKey)
      if (startColIndex < 0) return
      const selectedRange = this.normalizedSheetRange()
      const fillSelectedRange = !hasHeader
        && dataRows.length === 1
        && dataRows[0]?.length === 1
        && selectedRange
        && (selectedRange.r1 !== selectedRange.r2 || selectedRange.c1 !== selectedRange.c2)
      if (fillSelectedRange) {
        const value = dataRows[0][0]
        const rowCount = selectedRange.r2 - selectedRange.r1 + 1
        const columnCount = selectedRange.c2 - selectedRange.c1 + 1
        dataRows = Array.from({ length: rowCount }, () => Array(columnCount).fill(value))
        startIndex = selectedRange.r1
        startColIndex = selectedRange.c1
      }
      let skippedRowCount = 0
      if (!matchRowsByOrderId) {
        const availableRowCount = Math.max(this.list.length - startIndex, 0)
        skippedRowCount = Math.max(dataRows.length - availableRowCount, 0)
        dataRows.splice(availableRowCount)
      }
      if (!dataRows.length) {
        ElMessage.warning('粘贴区域超出当前列表，本次未保存')
        return
      }
      const workingRows = this.list.map((row) => this.normalizeRow(JSON.parse(JSON.stringify(row))))
      const rowIndexByOrderId = new Map(
        workingRows.map((row, index) => [String(row.library_order_id || '').trim(), index]),
      )
      const matchedOrderIds = new Set()
      const dirtyByIndex = new Map()
      const targetFieldsByIndex = new Map()
      const invalidCells = []
      const touchedCells = []
      dataRows.forEach((cells, offset) => {
        if (cells.every((cell) => String(cell ?? '') === '')) return
        let rowIndex = startIndex + offset
        if (matchRowsByOrderId) {
          const orderId = String(cells[orderIdHeaderIndex] || '').trim()
          const matchedIndex = rowIndexByOrderId.get(orderId)
          if (!orderId || matchedIndex === undefined || matchedOrderIds.has(orderId)) {
            invalidCells.push({ reason: 'identity' })
            return
          }
          matchedOrderIds.add(orderId)
          rowIndex = matchedIndex
        }
        const row = workingRows[rowIndex]
        if (!row) return
        cells.forEach((cell, cellIndex) => {
          const key = hasHeader ? headerKeys[cellIndex] : this.sheetColumns[startColIndex + cellIndex]?.key
          if (!key) {
            if (String(cell ?? '').trim()) invalidCells.push({ reason: 'unknown' })
            return
          }
          const result = this.assignSheetValue(row, key, cell)
          if (result.skipped) return
          if (!result.ok) {
            invalidCells.push({ ...result, key })
            return
          }
          if (this.sameSheetValue(key, row[key], this.list[rowIndex]?.[key])) return
          touchedCells.push({ rowId: row.id, key })
          const fields = dirtyByIndex.get(rowIndex) || new Set()
          fields.add(key)
          dirtyByIndex.set(rowIndex, fields)
          if (key === 'target_codes' || key === 'target_name') {
            const targetFields = targetFieldsByIndex.get(rowIndex) || new Set()
            targetFields.add(key)
            targetFieldsByIndex.set(rowIndex, targetFields)
          }
        })
      })
      if (invalidCells.length) {
        const firstInvalid = invalidCells[0]
        const message = firstInvalid.reason === 'identity'
          ? '粘贴内容包含当前页不存在或重复的系统工单号，本次粘贴未保存'
          : firstInvalid.reason === 'unknown'
            ? '粘贴内容包含无法识别的列，本次粘贴未保存'
            : firstInvalid.key
              ? `${this.sheetValidationMessage(firstInvalid.key, firstInvalid.reason)}，本次粘贴未保存`
              : `有 ${invalidCells.length} 个单元格不可编辑，本次粘贴未保存`
        ElMessage.warning(message)
        return
      }
      if (!dirtyByIndex.size) return
      const targetEntries = [...targetFieldsByIndex.entries()]
        .map(([rowIndex, fields]) => ({ fields, row: workingRows[rowIndex] }))
      if (targetEntries.length) {
        try {
          const codeEntries = targetEntries.filter(({ fields }) => fields.has('target_codes'))
          const resolvedCodes = await this.resolveTargetCodes(codeEntries.flatMap(({ row }) => row.target_codes || []))
          if (resolvedCodes.missing.length) {
            ElMessage.warning(`未找到靶点编号：${resolvedCodes.missing.join('、')}，本次粘贴未保存`)
            return
          }
          codeEntries.forEach(({ fields, row }) => {
            const canonicalNames = (row.target_codes || []).map((code) => resolvedCodes.nameByCode.get(code))
            if (fields.has('target_name')) {
              const submittedNames = splitTargetNames(row.target_name)
              const matches = submittedNames.length === canonicalNames.length
                && submittedNames.every((name, index) => name.toLowerCase() === String(canonicalNames[index] || '').toLowerCase())
              if (!matches) throw new Error('target-mismatch')
            }
            row.target_name = canonicalNames.join('&')
            fields.add('target_name')
          })
          const nameOnlyEntries = targetEntries.filter(({ fields }) => fields.has('target_name') && !fields.has('target_codes'))
          const resolvedNames = await this.resolveTargetNames(nameOnlyEntries.flatMap(({ row }) => splitTargetNames(row.target_name)).join('&'))
          if (resolvedNames.missing.length) {
            ElMessage.warning(`未找到靶点名称：${resolvedNames.missing.join('、')}，本次粘贴未保存`)
            return
          }
          if (resolvedNames.ambiguous.length) {
            ElMessage.warning(`靶点名称不唯一：${resolvedNames.ambiguous.join('、')}，本次粘贴未保存`)
            return
          }
          nameOnlyEntries.forEach(({ fields, row }) => {
            const targetItems = splitTargetNames(row.target_name).map((name) => (
              resolvedNames.items.find((item) => String(item.name || '').toLowerCase() === name.toLowerCase())
            ))
            row.target_codes = targetItems.map((item) => item.snum)
            row.target_name = targetItems.map((item) => item.name).join('&')
            fields.add('target_codes')
          })
        } catch {
          ElMessage.warning('靶点名称与编号不匹配或校验失败，本次粘贴未保存')
          return
        }
      }
      const qcActor = getSerumUserName(useUserStore().userInfo)
      const entries = [...dirtyByIndex.entries()].map(([rowIndex, fields]) => {
        const row = workingRows[rowIndex]
        if (fields.has('qc_result')) {
          stampQcFields(row, qcActor).forEach((key) => fields.add(key))
        }
        if (fields.has('target_codes') || fields.has('target_name')) {
          fields.add('target_codes')
          fields.add('target_name')
        }
        const payload = { id: row.id }
        fields.forEach((field) => {
          payload[field] = row[field]
        })
        return { fields, payload }
      })
      try {
        const result = await batchSaveLibraryOrders(entries.map(({ payload }) => payload))
        const savedById = new Map((result?.items || []).map((item) => [item.id, item]))
        entries.forEach(({ fields, payload }) => {
          const saved = savedById.get(payload.id)
          if (!saved) return
          const savedFields = [...fields]
          if (fields.has('mouse_strain')) savedFields.push('sample_type')
          if (fields.has('index_mode')) savedFields.push(...INDEX_LINKED_KEYS)
          savedFields.push(...DERIVED_FIELDS)
          fields.forEach((field) => {
            const catalogMeta = CATALOG_NAME_FIELDS[field]
            if (!catalogMeta) return
            savedFields.push(catalogMeta.idKey)
            if (catalogMeta.sequenceKey) savedFields.push(catalogMeta.sequenceKey)
          })
          this.applySavedFields(
            this.normalizeRow(saved),
            fields.has('build_type') ? undefined : [...new Set(savedFields)],
          )
        })
        const savedCount = entries.length
        const selectedCells = touchedCells
          .map(({ rowId, key }) => ({
            rowIndex: this.list.findIndex((row) => row.id === rowId),
            colIndex: this.sheetColumns.findIndex((column) => column.key === key),
          }))
          .filter(({ rowIndex, colIndex }) => rowIndex >= 0 && colIndex >= 0)
        if (selectedCells.length) {
          const rowIndexes = selectedCells.map((cell) => cell.rowIndex)
          const colIndexes = selectedCells.map((cell) => cell.colIndex)
          const range = {
            r1: Math.min(...rowIndexes),
            c1: Math.min(...colIndexes),
            r2: Math.max(...rowIndexes),
            c2: Math.max(...colIndexes),
          }
          await this.$nextTick()
          const activeRow = this.list[range.r1]
          const activeColumn = this.sheetColumns[range.c1]
          if (activeRow && activeColumn) {
            await this.$refs.sheetTable?.setSelectCell?.(activeRow, activeColumn.key)
          }
          this.setSheetRange(range)
        }
        const skippedHint = skippedRowCount ? `，已忽略超出的 ${skippedRowCount} 行` : ''
        ElMessage.success(`已粘贴并保存 ${savedCount} 行${skippedHint}`)
      } catch (error) {
        await this.getList({ flushEditor: false })
        notifyApiError(error, { messages: { default: '粘贴保存失败' } })
      }
    },
  },
}
</script>

<style scoped src="#/components/workbench/workbenchExcel.css"></style>
<style scoped src="#/components/workbench/workbenchDrawerChrome.css"></style>
<style src="#/components/workbench/workbenchDrawer.css"></style>
<style scoped>
.library-code-head.is-asc {
  color: var(--el-color-primary);
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
  border: 1px solid #fff;
}

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
  grid-template-columns: repeat(4, minmax(0, 1fr));
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
  flex: 2 1 150px;
  min-width: 100px;
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

.table-card :deep(.priority-select.status-tone-info .el-select__wrapper) {
  background-color: var(--el-color-info-light-9);
}
.table-card :deep(.priority-select.status-tone-info .el-select__selected-item) {
  color: var(--el-color-info);
}
.table-card :deep(.priority-select.status-tone-warning .el-select__wrapper) {
  background-color: var(--el-color-warning-light-9);
}
.table-card :deep(.priority-select.status-tone-warning .el-select__selected-item) {
  color: var(--el-color-warning);
}
.table-card :deep(.priority-select.status-tone-danger .el-select__wrapper) {
  background-color: var(--el-color-danger-light-9);
}
.table-card :deep(.priority-select.status-tone-danger .el-select__selected-item) {
  color: var(--el-color-danger);
}
.table-card :deep(.priority-select.status-tone-king .el-select__wrapper) {
  background-color: #efe8f6;
}
.table-card :deep(.priority-select.status-tone-king .el-select__selected-item) {
  color: #6f4d9c;
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

.source-link.is-link,
.source-link.is-link :deep(.el-input__wrapper),
.source-link.is-link :deep(.el-input__inner),
.source-link.is-link :deep(.el-input__suffix) {
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

.drawer-field.is-synced :deep(.el-textarea__inner) {
  resize: none;
}

.drawer-field-break {
  grid-column: 2;
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
.create-name.tone-info { color: var(--el-text-color-secondary); }

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

</style>
