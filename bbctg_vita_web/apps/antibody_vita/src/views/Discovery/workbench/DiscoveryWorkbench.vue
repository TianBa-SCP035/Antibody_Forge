<template>
  <div class="app-container" :class="{ 'is-list-table-locked': listTableLocked }">
    <AdvancedOpsBar v-model="showAdvancedOps">
      <ListFilterSelect
        v-model="listQuery.study_type"
        clearable
        placeholder="课题类型"
        @change="handleFilter"
      >
        <el-option v-for="item in studyTypeOptions" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <div class="ops-user-select">
        <SerumUserSelect
          v-model="listQuery.owner"
          multi-gesture
          :options="optionLists.owners"
          placeholder="负责人"
          clearable
          @change="handleFilter"
        />
      </div>
      <el-input
        v-model="listQuery.cage_position"
        clearable
        placeholder="笼位"
        @keyup.enter="handleFilter"
        @clear="handleFilter"
      />
      <ListFilterSelect
        v-model="listQuery.mouse_strain"
        clearable
        placeholder="小鼠品系"
        @change="handleFilter"
      >
        <el-option v-for="item in mouseStrainOptions" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <el-input
        v-model="listQuery.mouse_nos"
        clearable
        placeholder="鼠号"
        @keyup.enter="handleFilter"
        @clear="handleFilter"
      />
      <el-input
        v-model="listQuery.plate_nos"
        clearable
        placeholder="板号"
        @keyup.enter="handleFilter"
        @clear="handleFilter"
      />
      <ListFilterSelect
        v-model="listQuery.immune_antigen"
        clearable
        filterable
        allow-create
        default-first-option
        placeholder="免疫抗原"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.immune_antigens" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.screening_antigen"
        clearable
        filterable
        allow-create
        default-first-option
        placeholder="筛选抗原"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.screening_antigens" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.boost_antigen"
        clearable
        filterable
        allow-create
        default-first-option
        placeholder="冲击免抗原"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.boost_antigens" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <el-input
        v-model="listQuery.remark"
        clearable
        placeholder="备注"
        title="备注包含这段文字"
        @keyup.enter="handleFilter"
        @clear="handleFilter"
      />
      <el-date-picker
        v-model="boostRange"
        type="daterange"
        range-separator="至"
        start-placeholder="冲击免起始"
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
            @contextmenu.prevent="toggleBoostFilter('need_boost')"
          >
            <span class="ready-dot" />
            <span><strong>{{ stats.boosting }}</strong> 个项目冲击免中</span>
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
            title="搜索发现编号、项目编号或实验号"
            clearable
            @keyup.enter="handleFilter"
            @clear="handleFilter"
          />
          <ListFilterSelect
            v-model="listQuery.target_name"
            class="filter-select"
            clearable
            filterable
            placeholder="靶点"
            :filter-method="setTargetFilterQuery"
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
          <div class="filter-select">
            <SerumUserSelect
              v-model="listQuery.pm"
              multi-gesture
              :options="optionLists.pms"
              placeholder="PM"
              title="左键单选，右键追加"
              clearable
              @change="handleFilter"
            />
          </div>
          <ListFilterSelect
            v-model="listQuery.screening_methods"
            placeholder="筛选方式"
            clearable
            class="filter-select"
            @change="handleFilter"
          >
            <el-option
              v-for="item in screeningMethodOptions"
              :key="item"
              :label="item"
              :value="item"
            />
          </ListFilterSelect>
          <ListFilterSelect
            v-model="listQuery.status"
            placeholder="状态"
            clearable
            class="filter-select"
            @change="handleFilter"
          >
            <el-option v-for="item in planStatusOptions" :key="item" :label="item" :value="item" />
          </ListFilterSelect>
          <ListFilterSelect
            v-model="listQuery.priority"
            placeholder="优先级"
            clearable
            class="filter-select"
            @change="handleFilter"
          >
            <el-option v-for="item in priorityOptions" :key="item" :label="item" :value="item" />
          </ListFilterSelect>
          <ListFilterSelect
            v-model="listQuery.mouse_strain_category"
            placeholder="归类鼠型"
            clearable
            class="filter-select"
            @change="handleFilter"
          >
            <el-option v-for="item in mouseStrainCategoryOptions" :key="item" :label="item" :value="item" />
          </ListFilterSelect>
          <el-date-picker
            v-model="harvestRange"
            class="harvest-range"
            type="daterange"
            range-separator="至"
            start-placeholder="剖鼠起始"
            end-placeholder="剖鼠截止"
            value-format="YYYY-MM-DD"
            @change="handleFilter"
          />
        </div>
        <div class="data-view-controls list-filter-actions">
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

    <el-card shadow="never" class="table-card list-table-card">
      <div ref="listTableBody" class="list-table-body">
      <WorkbenchDataTable
        v-if="viewMode === 'workbench'"
        ref="workbenchTable"
        :height="listTableHeight"
        v-loading="loading"
        storage-key="discoveryWorkbenchViewPrefs.v2"
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
        @row-click="onWorkbenchRowClick"
        @row-contextmenu="onWorkbenchRowContextMenu"
        @reorder="scheduleSortable"
      >
        <template #header-sort_order>
          <button
            type="button"
            class="sort-header-btn"
            :class="{ 'is-active': isQueueSorted }"
            :title="sortHeaderTitle"
            @click.stop="toggleQueueSort"
          >
            {{ sortColumnLabel }}
          </button>
        </template>
        <template #sort_order="{ row, $index }">
          <div class="sort-cell">
            <el-input
              v-if="canEditSortCell(row) && sortEditingId === row.id"
              :ref="(el) => bindSortInput(row.id, el)"
              v-model="row.sort_order"
              class="sort-order-input"
              size="small"
              type="number"
              min="1"
              @click.stop
              @blur="finishSortEdit(row)"
              @keyup.enter="finishSortEdit(row)"
              @mousedown.stop
            />
            <button
              v-else
              type="button"
              class="sort-order-value"
              :disabled="!canEditSortCell(row)"
              @click.stop="startSortEdit(row)"
            >
              {{ formatSortColumn(row, $index) }}
            </button>
          </div>
        </template>
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
          <el-tag
            v-else
            class="list-status-tag"
            :class="{ 'status-tone-king': priorityTone(row) === 'king' }"
            :type="priorityTone(row) === 'king' ? 'info' : priorityTone(row)"
            effect="plain"
          >
            {{ rowPriority(row) }}
          </el-tag>
        </template>
        <template #status="{ row }">
          <WorkbenchStatusEditor
            :value="row.status || '规划中'"
            :options="planStatusOptions"
            :type="planStatusTone(row.status)"
            :editable="canEdit"
            @change="value => updatePlanStatus(row, value)"
          />
        </template>
        <template #mouse_strain_category="{ row }">
          {{ displayCsvField(row.mouse_strain_category) }}
        </template>
        <template #mouse_strain="{ row }">
          {{ displayCsvField(row.mouse_strain) }}
        </template>
        <template #screening_methods="{ row }">
          <WorkbenchMultiTagEditor
            v-model="row.screening_method_list"
            :options="screeningMethodOptions"
            :tones="screeningMethodTones"
            :editable="canEdit"
            @change="persistRow(row, 'screening_methods')"
          />
        </template>
        <template #header-harvest_date>
          <button
            type="button"
            class="sort-header-btn"
            :class="{ 'is-active': listQuery.sort_field === 'harvest_date' }"
            :title="dateSortTitle('harvest_date')"
            @click.stop="cycleDateSort('harvest_date')"
          >
            剖鼠日期{{ dateSortMark('harvest_date') }}
          </button>
        </template>
        <template #harvest_date="{ row }">
          <el-date-picker
            v-model="row.harvest_date"
            class="inline-date"
            type="date"
            size="small"
            value-format="YYYY-MM-DD"
            placeholder="剖鼠/上机"
            :disabled="!canEdit"
            @click.stop
            @change="persistRow(row, 'harvest_date')"
          />
        </template>
        <template #header-boost_date>
          <button
            type="button"
            class="sort-header-btn"
            :class="{ 'is-active': listQuery.sort_field === 'boost_date' }"
            :title="dateSortTitle('boost_date')"
            @click.stop="cycleDateSort('boost_date')"
          >
            冲击日期{{ dateSortMark('boost_date') }}
          </button>
        </template>
        <template #boost_date="{ row }">
          <el-date-picker
            v-model="row.boost_date"
            class="inline-date"
            type="date"
            size="small"
            value-format="YYYY-MM-DD"
            placeholder="冲击免疫"
            :disabled="!canEdit"
            @click.stop
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
        @contextmenu="onSheetWrapContextMenu"
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
                :width="column.width"
                :min-width="column.minWidth || column.width || 120"
                :edit-render="{ name: 'VxeInput' }"
                :formatter="sheetFormatter(column)"
              >
                <template #edit="{ row }">
                  <div v-if="sheetEditSource === 'dblclick'" class="sheet-picker-editor">
                    <span class="sheet-picker-editor__value">
                      {{ sheetPickerDisplayValue(row, column) }}
                    </span>
                    <VxeSelect
                      v-model="row.target_codes"
                      class-name="sheet-grid-editor sheet-picker-control"
                      filterable
                      multiple
                      remote
                      :options="sheetTargetSelectOptions"
                      :popup-config="{
                        className: 'sheet-picker-popup',
                        placement: 'bottom',
                        width: 300,
                      }"
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
                :width="column.width"
                :min-width="column.minWidth || column.width || 120"
                :edit-render="{ name: 'VxeInput' }"
                :formatter="sheetFormatter(column)"
              >
                <template #edit="{ row }">
                  <ListFilterSelect
                    v-if="isCsvField(column.key) && sheetEditSource === 'dblclick'"
                    :model-value="splitCategories(row[column.key])"
                    joined
                    filterable
                    allow-create
                    default-first-option
                    class="sheet-category-select"
                    popper-class="vxe-table--ignore-clear"
                    clearable
                    @change="onCsvFieldChange(row, column.key, $event)"
                    @visible-change="onCategorySheetVisible"
                  >
                    <el-option
                      v-for="item in csvFieldOptions(column.key)"
                      :key="item"
                      :label="item"
                      :value="item"
                    />
                    <el-option
                      v-for="item in extraCsvOptions(column.key, row[column.key])"
                      :key="`extra-${item}`"
                      :label="item"
                      :value="item"
                    />
                  </ListFilterSelect>
                  <div v-else-if="sheetEditSource === 'dblclick'" class="sheet-picker-editor">
                    <span class="sheet-picker-editor__value">
                      {{ sheetPickerDisplayValue(row, column) }}
                    </span>
                    <VxeSelect
                      v-model="row[column.key === 'screening_methods' ? 'screening_method_list' : column.key]"
                      class-name="sheet-grid-editor sheet-picker-control"
                      :filterable="isUserColumn(column)"
                      :multiple="column.edit === 'multi'"
                      :options="sheetChoiceSelectOptions(column)"
                      :popup-config="{
                        className: 'sheet-picker-popup',
                        placement: 'bottom',
                        width: 220,
                      }"
                      @visible-change="onSheetPickerVisibleChange"
                    />
                  </div>
                  <VxeInput
                    v-else
                    :model-value="sheetChoiceDirectValue(row, column)"
                    class-name="sheet-grid-editor"
                    @update:model-value="setSheetChoiceDirectValue(row, column, $event)"
                  />
                </template>
              </vxe-column>
              <vxe-column
                v-else
                :field="column.key"
                :title="sheetColumnTitle(column)"
                :width="column.width"
                :min-width="column.minWidth || column.width || 120"
                :edit-render="sheetEditRender(column)"
                :formatter="sheetFormatter(column)"
              />
            </template>
            <vxe-column title="操作" width="240" fixed="right" align="center">
              <template #default="{ row }">
                <DiscoveryRowActions
                  :row="row"
                  :can-edit="canEdit"
                  :can-handoff="canHandoff"
                  @detail="openSerumProject"
                  @handoff="handleHandoff"
                  @delete="handleDelete"
                />
              </template>
            </vxe-column>
          </vxe-table>
          <div ref="sheetRangeOverlay" class="sheet-range-overlay" aria-hidden="true" />
          <div ref="sheetColumnDropLine" class="sheet-column-drop-line" aria-hidden="true" />
          <div ref="sheetColumnGhost" class="sheet-column-ghost" aria-hidden="true" />
        </div>
      </div>
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

    <el-drawer
      v-model="drawerVisible"
      size="520px"
      append-to-body
      :modal="false"
      :show-close="false"
      :lock-scroll="false"
      :title="drawerTitle"
      modal-class="workbench-drawer-overlay"
      class="workbench-drawer"
    >
      <template #header="{ close, titleId }">
        <div class="drawer-header">
          <div class="drawer-heading">
            <h2 :id="titleId" class="drawer-title">{{ drawerTitle }}</h2>
            <p v-if="drawerMeta" class="drawer-header-meta">{{ drawerMeta }}</p>
          </div>
          <button type="button" class="drawer-close" aria-label="关闭" @click="close">×</button>
        </div>
      </template>
      <div v-if="editingRow" class="drawer-toolbar">
        <div class="drawer-toolbar-actions">
          <DiscoveryRowActions
            :row="editingRow"
            :can-edit="canEdit"
            :can-handoff="canHandoff"
            @detail="openSerumProject"
            @handoff="handleHandoff"
            @delete="handleDelete"
          />
        </div>
        <div class="drawer-nav">
          <el-button size="small" :disabled="!hasPrevEditor" @click="shiftEditor(-1)">上一条</el-button>
          <el-button size="small" :disabled="!hasNextEditor" @click="shiftEditor(1)">下一条</el-button>
        </div>
      </div>
      <fieldset
        v-if="editingRow"
        class="drawer-fieldset"
        :disabled="!canEdit"
        @mouseover="syncDrawerControlTooltip"
      >
        <el-form label-width="80px" size="small" class="drawer-form" @submit.prevent>
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
                :class="['drawer-field', field.wide ? 'is-wide' : '', field.sync ? 'is-synced' : '']"
              >
                <el-date-picker
                  v-if="field.type === 'date'"
                  v-model="editingRow[field.key]"
                  type="date"
                  value-format="YYYY-MM-DD"
                  format="YYYY-MM-DD"
                  placeholder="选择日期"
                  style="width: 100%;"
                  :disabled="!canEdit"
                  @change="persistRow(editingRow, field.key)"
                />
                <WorkbenchTargetSelect
                  v-else-if="field.type === 'target'"
                  v-model="editingRow.target_codes"
                  :display-name="editingRow.target_name"
                  :placeholder="editingRow.target_name ? '' : '搜索靶点'"
                  :disabled="!canEdit"
                  @change="onDrawerTargetChange(editingRow, $event)"
                />
                <el-input
                  v-else-if="field.type === 'target_codes'"
                  :model-value="formatCodesText(editingRow.target_codes)"
                  disabled
                  placeholder="自动带出"
                />
                <SerumUserSelect
                  v-else-if="field.type === 'user'"
                  v-model="editingRow[field.key]"
                  :options="usedUserOptions(field)"
                  :placeholder="`选择${field.label}`"
                  :disabled="!canEdit"
                  clearable
                  @change="persistRow(editingRow, field.key)"
                />
                <ListFilterSelect
                  v-else-if="field.type === 'csv'"
                  :model-value="splitCategories(editingRow[field.key])"
                  joined
                  filterable
                  allow-create
                  default-first-option
                  clearable
                  :placeholder="`选择${field.label}`"
                  style="width: 100%;"
                  :disabled="!canEdit"
                  @change="onCsvFieldChange(editingRow, field.key, $event)"
                >
                  <el-option
                    v-for="item in fieldOptions(field)"
                    :key="item"
                    :label="item"
                    :value="item"
                  />
                  <el-option
                    v-for="item in extraCsvOptions(field.key, editingRow[field.key])"
                    :key="`extra-${item}`"
                    :label="item"
                    :value="item"
                  />
                </ListFilterSelect>
                <el-select
                  v-else-if="field.type === 'select'"
                  v-model="editingRow[field.key]"
                  class="drawer-select"
                  :class="drawerSelectClass(field)"
                  :clearable="field.key === 'study_type'"
                  default-first-option
                  style="width: 100%;"
                  :disabled="!canEdit"
                  @change="persistRow(editingRow, field.key)"
                >
                  <el-option
                    v-for="item in fieldOptions(field)"
                    :key="item"
                    :label="item"
                    :value="item"
                  />
                </el-select>
                <WorkbenchMultiTagEditor
                  v-else-if="field.type === 'multi'"
                  :key="`screening-${editingRow.id}`"
                  v-model="editingRow.screening_method_list"
                  :options="screeningMethodOptions"
                  :tones="screeningMethodTones"
                  :editable="canEdit"
                  align="start"
                  @change="persistRow(editingRow, 'screening_methods')"
                />
                <div v-else-if="field.type === 'lines'" class="line-field">
                  <el-input
                    v-model="editingRow[field.key]"
                    type="textarea"
                    resize="none"
                    :autosize="{ minRows: 1, maxRows: 4 }"
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
                        @mousedown.prevent="fillAntigenLine(field, item)"
                      >
                        {{ item }}
                      </button>
                    </div>
                  </teleport>
                </div>
                <el-input
                  v-else-if="field.type === 'textarea'"
                  v-model="editingRow[field.key]"
                  type="textarea"
                  :rows="field.sync ? 1 : 2"
                  :resize="field.resize"
                  :autosize="field.sync ? false : { minRows: 1, maxRows: 4 }"
                  :disabled="!canEdit"
                  @input="field.sync && syncDrawerTextareas()"
                  @blur="persistRow(editingRow, field.key)"
                />
                <span v-else-if="field.key === 'sort_order' && isQueueTerminalRow(editingRow)">-</span>
                <el-input
                  v-else
                  v-model="editingRow[field.key]"
                  :type="field.key === 'sort_order' ? 'number' : 'text'"
                  :min="field.key === 'sort_order' ? 1 : undefined"
                  :disabled="!canEdit"
                  @blur="persistRow(editingRow, field.key)"
                />
              </el-form-item>
            </div>
          </article>
        </el-form>
      </fieldset>
    </el-drawer>
    <LibraryHandoffDialog
      v-model="handoffVisible"
      :discovery-row="handoffRow"
      @created="onLibraryHandoffCreated"
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
  ElTag,
} from 'element-plus'
import { VxeInput, VxeSelect } from 'vxe-pc-ui'
import { VxeColumn, VxeTable } from 'vxe-table'
import { useUserStore } from '@vben/stores'

import '#/adapter/vxe-table'
import 'vxe-pc-ui/styles/cssvar.scss'
import 'vxe-table/styles/cssvar.scss'

import AdvancedOpsBar from '#/components/AdvancedOpsBar.vue'
import LibraryHandoffDialog from '#/views/MolecularCell/library/LibraryHandoffDialog.vue'
import {
  coerceOptionalNonnegInt,
  coerceRequiredPositiveInt,
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
  syncDrawerControlTooltip,
  WorkbenchDataTable,
  workbenchExcelMixin,
} from '#/components/workbench'
import { listTableLockMixin } from '#/utils/listTableLock'
import WorkbenchMultiTagEditor from '#/components/workbench/WorkbenchMultiTagEditor.vue'
import WorkbenchStatusEditor from '#/components/workbench/WorkbenchStatusEditor.vue'
import WorkbenchTargetSelect from '#/components/workbench/WorkbenchTargetSelect.vue'
import WorkbenchViewToggle from '#/components/workbench/WorkbenchViewToggle.vue'
import { notifyApiError } from '#/api/errors'
import { skipGlobalErrorHandler } from '#/api/request'
import {
  DISCOVERY_WORKBENCH_CREATED_KEY,
  deleteDiscoveryWorkbench,
  exportDiscoveryWorkbenchList,
  fetchDiscoveryWorkbenchList,
  fetchDiscoveryWorkbenchOptions,
  reorderDiscoveryWorkbench,
  saveDiscoveryWorkbench,
  saveDiscoveryWorkbenchBatch,
} from '#/api/discoveryWorkbench'
import { fetchSerumDetailByExperimentId } from '#/api/serum'
import { downloadListExcel, excelTimestamp } from '#/utils/downloadExcel'
import { canEditDiscoveryWorkbench } from '#/utils/discoveryPermission'
import { canHandoffLibrary } from '#/utils/molecularPermission'
import { canAccessSerumDetail } from '#/utils/serumPermission'
import { SERUM_MOUSE_STRAIN_CATEGORY_OPTIONS, SERUM_MOUSE_STRAIN_OPTIONS } from '#/utils/serumMouseOptions'
import {
  WORKBENCH_PRIORITY_OPTIONS,
  canonicalizeWorkbenchPriority,
  getTiterPriorityTone,
} from '#/utils/serumProjectStatus'
import {
  loadSerumUserOptions,
  uniqueNames,
} from '#/utils/serumUserOptions'
import { WORKBENCH_STUDY_TYPE_OPTIONS } from '#/utils/workbenchStudyTypes'
import { shouldRefreshTabData } from '#/utils/staleTabRefresh'
import { filterTargetOptions, normalizeTargetOptions, targetOptionExtra as targetOptionHint } from '#/utils/targetFilterOptions'
import ListFilterSelect from '#/components/ListFilterSelect.vue'
import SerumUserSelect from '../../Serum/shared/SerumUserSelect.vue'
import DiscoveryRowActions from './DiscoveryRowActions.vue'

const SCREENING_METHOD_OPTIONS = ['达普', '噬菌体', 'Beacon', 'NGS']
const SCREENING_METHOD_TONES = {
  达普: 'primary',
  噬菌体: 'warning',
  Beacon: 'success',
  NGS: 'purple',
}
const PLAN_STATUS_OPTIONS = ['规划中', '待冲击', '待剖鼠', '待建库', '待噬菌体', '待测序', '已完成', '已取消']
const PRIORITY_OPTIONS = [...WORKBENCH_PRIORITY_OPTIONS]
const STUDY_TYPE_OPTIONS = [...WORKBENCH_STUDY_TYPE_OPTIONS]
const MOUSE_STRAIN_CATEGORY_OPTIONS = [...SERUM_MOUSE_STRAIN_CATEGORY_OPTIONS]
const MOUSE_STRAIN_OPTIONS = [...SERUM_MOUSE_STRAIN_OPTIONS]
const CSV_FIELD_OPTIONS = {
  mouse_strain_category: MOUSE_STRAIN_CATEGORY_OPTIONS,
  mouse_strain: MOUSE_STRAIN_OPTIONS,
}
const DATE_KEYS = ['harvest_date', 'boost_date']
const QUEUE_KEYS = ['status', 'priority', 'sort_order']
const QUEUE_TERMINAL_STATUSES = ['已完成', '已取消']
const STRING_MAX = {
  project_code: 64,
  experiment_id: 64,
  target_name: 128,
  study_type: 64,
  pm: 64,
  owner: 64,
  mouse_strain_category: 128,
  mouse_strain: 128,
  cage_position: 64,
  mouse_nos: 512,
  serum_titer: 255,
  immune_antigen: 255,
  screening_antigen: 255,
  positive_cell_count: 64,
  plate_nos: 512,
  boost_antigen: 255,
  boost_cells: 255,
  immune_owner: 64,
  cell_collector: 64,
  remark: 500,
}
const BREAK_FIELDS = new Set([
  'mouse_nos',
  'plate_nos',
  'serum_titer',
  'positive_cell_count',
  'immune_antigen',
  'screening_antigen',
  'boost_antigen',
  'boost_cells',
  'remark',
])
const USER_OPTION_LIST = {
  owner: 'owners',
  pm: 'pms',
  immune_owner: 'immune_owners',
  cell_collector: 'cell_collectors',
}
const STATUS_VIEWS = [
  { key: '', label: '全部安排', hint: '本台全部发现安排', valueKey: 'all', tone: 'all', step: '00' },
  { key: 'harvest', label: '待剖鼠', hint: '规划中、待冲击与待剖鼠', valueKey: 'harvest', tone: 'planned', step: '01' },
  { key: 'library', label: '待建库', hint: '待建库与待噬菌体', valueKey: 'library', tone: 'ongoing', step: '02' },
  { key: 'sequencing', label: '待测序', hint: '已交分子、等待测序', valueKey: 'sequencing', tone: 'completed', step: '03' },
  { key: 'cancelled', label: '已取消', hint: '已关闭的安排', valueKey: 'cancelled', tone: 'cancelled', step: '04' },
]
const EDITOR_SECTIONS = [
  {
    title: '队列 / 状态',
    queue: true,
    fields: [
      { key: 'status', label: '状态', type: 'select', options: PLAN_STATUS_OPTIONS },
      { key: 'priority', label: '优先级', type: 'select', options: PRIORITY_OPTIONS },
      { key: 'owner', label: '负责人', type: 'user' },
      { key: 'sort_order', label: '排序', type: 'number' },
    ],
  },
  {
    title: '项目',
    fields: [
      { key: 'project_code', label: '项目编号', type: 'text' },
      { key: 'experiment_id', label: '实验号', type: 'text' },
      { key: 'pm', label: 'PM', type: 'user' },
      { key: 'study_type', label: '课题类型', type: 'select', options: STUDY_TYPE_OPTIONS },
      { key: 'target', label: '靶点', type: 'target', wide: true },
      { key: 'target_codes', label: '靶点编号', type: 'target_codes', wide: true },
    ],
  },
  {
    title: '小鼠',
    fields: [
      { key: 'mouse_strain_category', label: '归类鼠型', type: 'csv', options: MOUSE_STRAIN_CATEGORY_OPTIONS },
      { key: 'mouse_strain', label: '小鼠品系', type: 'csv', options: MOUSE_STRAIN_OPTIONS },
      { key: 'cage_position', label: '笼位', type: 'text' },
      { key: 'mouse_count', label: '只数', type: 'text' },
      { key: 'mouse_nos', label: '鼠号', type: 'textarea', wide: true },
    ],
  },
  {
    title: '筛选',
    fields: [
      { key: 'screening_methods', label: '筛选方式', type: 'multi', wide: true },
      { key: 'immune_antigen', label: '免疫抗原', type: 'textarea', wide: true, resize: 'none' },
      { key: 'screening_antigen', label: '筛选抗原', type: 'textarea', wide: true, resize: 'none' },
      { key: 'serum_titer', label: '血清效价', type: 'textarea', sync: true },
      { key: 'positive_cell_count', label: '阳性细胞数', type: 'textarea', sync: true },
      { key: 'plate_nos', label: '板号', type: 'textarea', wide: true },
    ],
  },
  {
    title: '日程',
    fields: [
      { key: 'harvest_date', label: '剖鼠日期', type: 'date' },
      { key: 'boost_date', label: '冲击日期', type: 'date' },
      { key: 'immune_owner', label: '免疫负责人', type: 'user' },
      { key: 'cell_collector', label: '细胞收集人', type: 'user' },
      { key: 'boost_antigen', label: '冲击免抗原', type: 'lines', wide: true },
      { key: 'boost_cells', label: '冲击免细胞', type: 'textarea', wide: true, resize: 'none' },
      { key: 'remark', label: '备注', type: 'textarea', wide: true },
    ],
  },
]
const SHEET_COLUMNS = [
  { key: 'sort_order', label: '排序', edit: 'text', width: 64 },
  { key: 'priority', label: '优先级', edit: 'select', width: 100 },
  { key: 'target_codes', label: '靶点编号', edit: 'target', minWidth: 140 },
  { key: 'project_code', label: '项目编号', edit: 'text', minWidth: 120 },
  { key: 'target_name', label: '靶点名称', edit: 'target' },
  { key: 'pm', label: 'PM', edit: 'select', width: 90 },
  { key: 'study_type', label: '课题类型', edit: 'select' },
  { key: 'mouse_strain', label: '小鼠品系', edit: 'multi', minWidth: 140 },
  { key: 'screening_methods', label: '筛选方式', edit: 'multi', minWidth: 160 },
  { key: 'harvest_date', label: '剖鼠日期', edit: 'date', width: 120 },
  { key: 'mouse_count', label: '只数', edit: 'text', width: 80 },
  { key: 'mouse_nos', label: '鼠号', edit: 'text', minWidth: 140 },
  { key: 'serum_titer', label: '血清效价', edit: 'text' },
  { key: 'immune_antigen', label: '免疫抗原', edit: 'text', minWidth: 140 },
  { key: 'boost_date', label: '冲击日期', edit: 'date', width: 120 },
  { key: 'boost_antigen', label: '冲击免抗原', edit: 'text', minWidth: 140 },
  { key: 'boost_cells', label: '冲击免细胞', edit: 'text', minWidth: 140 },
  { key: 'screening_antigen', label: '筛选抗原', edit: 'text', minWidth: 140 },
  { key: 'positive_cell_count', label: '阳性细胞数', edit: 'text', minWidth: 110 },
  { key: 'plate_nos', label: '板号', edit: 'text', minWidth: 140 },
  { key: 'owner', label: '负责人', edit: 'select', width: 90 },
  { key: 'immune_owner', label: '免疫负责人', edit: 'select', width: 110 },
  { key: 'cell_collector', label: '细胞收集人', edit: 'select', width: 110 },
  { key: 'mouse_strain_category', label: '归类鼠型', edit: 'multi', minWidth: 140 },
  { key: 'cage_position', label: '笼位', edit: 'text', minWidth: 100 },
  { key: 'remark', label: '备注', edit: 'text', minWidth: 180 },
  { key: 'experiment_id', label: '实验号', edit: 'text', minWidth: 130 },
  { key: 'status', label: '状态', edit: 'select', width: 110 },
]
const SHEET_COLUMN_ORDER = createColumnOrder(
  'discoveryWorkbenchSheetColumnOrder.v4',
  SHEET_COLUMNS,
  { pinFirstKey: 'sort_order' },
)
const WORKBENCH_COLUMNS = [
  { key: 'sort_order', label: '序号', defaultVisible: true, width: 62, className: 'sort-column-cell' },
  { key: 'priority', label: '优先级', defaultVisible: true, minWidth: 110 },
  { key: 'status', label: '状态', defaultVisible: true, minWidth: 100, className: 'status-column-cell' },
  { key: 'pm', label: 'PM', defaultVisible: true, prop: 'pm', minWidth: 90, showOverflowTooltip: true },
  { key: 'project_code', label: '项目编号', defaultVisible: true, prop: 'project_code', minWidth: 120, showOverflowTooltip: true },
  { key: 'target_name', label: '靶点名称', defaultVisible: true, prop: 'target_name', minWidth: 100, showOverflowTooltip: true },
  { key: 'mouse_strain', label: '小鼠品系', defaultVisible: true, prop: 'mouse_strain', minWidth: 110, showOverflowTooltip: true },
  { key: 'screening_methods', label: '筛选方式', defaultVisible: true, minWidth: 145 },
  { key: 'screening_antigen', label: '筛选抗原', defaultVisible: true, prop: 'screening_antigen', minWidth: 120, showOverflowTooltip: true, keepLineBreaks: true },
  { key: 'boost_antigen', label: '冲击抗原', defaultVisible: true, prop: 'boost_antigen', minWidth: 120, showOverflowTooltip: true, keepLineBreaks: true },
  { key: 'harvest_date', label: '剖鼠日期', defaultVisible: true, minWidth: 135, className: 'date-column-cell' },
  { key: 'boost_date', label: '冲击日期', defaultVisible: true, minWidth: 135, className: 'date-column-cell' },
  { key: 'remark', label: '备注', defaultVisible: true, prop: 'remark', minWidth: 140, showOverflowTooltip: true, keepLineBreaks: true },
  { key: 'owner', label: '负责人', prop: 'owner', minWidth: 90, showOverflowTooltip: true },
  { key: 'immune_owner', label: '免疫负责人', prop: 'immune_owner', minWidth: 110, showOverflowTooltip: true },
  { key: 'cell_collector', label: '细胞收集人', prop: 'cell_collector', minWidth: 110, showOverflowTooltip: true },
  { key: 'experiment_id', label: '实验号', prop: 'experiment_id', minWidth: 130, showOverflowTooltip: true },
  { key: 'target_codes', label: '靶点编号', prop: 'target_codes', minWidth: 140, showOverflowTooltip: true },
  { key: 'study_type', label: '课题类型', prop: 'study_type', minWidth: 110, showOverflowTooltip: true },
  { key: 'mouse_strain_category', label: '归类鼠型', prop: 'mouse_strain_category', minWidth: 100, showOverflowTooltip: true },
  { key: 'cage_position', label: '笼位', prop: 'cage_position', minWidth: 100, showOverflowTooltip: true },
  { key: 'mouse_count', label: '只数', prop: 'mouse_count', minWidth: 80, showOverflowTooltip: true },
  { key: 'mouse_nos', label: '鼠号', prop: 'mouse_nos', minWidth: 140, showOverflowTooltip: true, keepLineBreaks: true },
  { key: 'serum_titer', label: '血清效价', prop: 'serum_titer', minWidth: 110, showOverflowTooltip: true, keepLineBreaks: true },
  { key: 'immune_antigen', label: '免疫抗原', prop: 'immune_antigen', minWidth: 140, showOverflowTooltip: true, keepLineBreaks: true },
  { key: 'boost_cells', label: '冲击免细胞', prop: 'boost_cells', minWidth: 140, showOverflowTooltip: true, keepLineBreaks: true },
  { key: 'positive_cell_count', label: '阳性细胞数', prop: 'positive_cell_count', minWidth: 110, showOverflowTooltip: true, keepLineBreaks: true },
  { key: 'plate_nos', label: '板号', prop: 'plate_nos', minWidth: 140, showOverflowTooltip: true, keepLineBreaks: true },
  { key: 'actions', label: '操作', defaultVisible: true, width: 240, className: 'action-column-cell', fixed: 'right' },
]
const SHEET_HEADER_ALIASES = Object.freeze({
  排序: 'sort_order',
  序号: 'sort_order',
  优先级: 'priority',
  状态: 'status',
  靶点编号: 'target_codes',
  剖鼠: 'harvest_date',
  剖鼠日: 'harvest_date',
  剖鼠日期: 'harvest_date',
  冲击免: 'boost_date',
  冲击免日: 'boost_date',
  冲击免日期: 'boost_date',
  冲击日期: 'boost_date',
  只数: 'mouse_count',
  小鼠只数: 'mouse_count',
  阳性细胞数: 'positive_cell_count',
  板号: 'plate_nos',
  笼位: 'cage_position',
  小鼠品系: 'mouse_strain',
  品系: 'mouse_strain',
  负责人: 'owner',
  免疫负责人: 'immune_owner',
  细胞收集人: 'cell_collector',
  冲击免细胞: 'boost_cells',
})
let lastViewMode = WORKBENCH_VIEW
const EDITABLE_FIELDS = [
  'project_code',
  'experiment_id',
  'target_name',
  'target_codes',
  'study_type',
  'pm',
  'owner',
  'immune_owner',
  'cell_collector',
  'mouse_strain_category',
  'mouse_strain',
  'cage_position',
  'mouse_count',
  'mouse_nos',
  'serum_titer',
  'immune_antigen',
  'screening_methods',
  'positive_cell_count',
  'screening_antigen',
  'plate_nos',
  'harvest_date',
  'boost_date',
  'boost_antigen',
  'boost_cells',
  'remark',
  'status',
  'priority',
  'sort_order',
]

function antigenLines(value) {
  return String(value || '')
    .split(/\n+|、+/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function splitCsv(value) {
  return String(value || '')
    .replace(/，/g, ',')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

function splitCategories(value) {
  const tokens = Array.isArray(value) ? value : String(value || '').split(/[,，、+]/)
  return tokens.map((item) => String(item || '').trim()).filter(Boolean)
}

function displayCsvField(value) {
  return splitCategories(value).join('、')
}

function joinCsvField(key, value) {
  const options = CSV_FIELD_OPTIONS[key] || []
  const tokens = splitCategories(value)
  const known = new Set(options)
  const present = new Set(tokens)
  const ordered = options.filter((item) => present.has(item))
  const extras = tokens.filter((item) => !known.has(item))
  return [...ordered, ...extras].join('、')
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

let pendingDiscoveryId = ''

export function rememberDiscoveryFocus(discoveryId) {
  pendingDiscoveryId = String(discoveryId || '').trim()
}

export default {
  name: 'DiscoveryWorkbench',
  mixins: [workbenchExcelMixin, listTableLockMixin],
  components: {
    AdvancedOpsBar,
    DiscoveryRowActions,
    LibraryHandoffDialog,
    ElButton,
    ElCard,
    ElDatePicker,
    ElDrawer,
    ElForm,
    ElFormItem,
    ElIcon,
    ElInput,
    ElOption,
    ElPagination,
    ElSelect,
    ElTag,
    WorkbenchDataTable,
    Search,
    ListFilterSelect,
    SerumUserSelect,
    Tools,
    WorkbenchMultiTagEditor,
    WorkbenchStatusEditor,
    WorkbenchTargetSelect,
    WorkbenchViewToggle,
    VxeColumn,
    VxeInput,
    VxeSelect,
    VxeTable,
  },
  setup() {
    const userStore = useUserStore()
    return { Download, userStore }
  },
  data() {
    return {
      loading: false,
      list: [],
      total: 0,
      stats: { all: 0, harvest: 0, library: 0, sequencing: 0, cancelled: 0, boosting: 0, need_boost: 0 },
      viewMode: coerceWorkbenchViewMode(lastViewMode),
      sortEditingId: null,
      sortInputRefs: {},
      sortable: null,
      sortableInitToken: 0,
      showAdvancedOps: false,
      drawerVisible: false,
      editingId: null,
      editingRowData: null,
      harvestRange: [],
      boostRange: [],
      listQuery: emptyQuery(),
      optionLists: {
        targets: [],
        pms: [],
        owners: [],
        immune_owners: [],
        cell_collectors: [],
        immune_antigens: [],
        boost_antigens: [],
        screening_antigens: [],
      },
      lineOpen: '',
      lineSuggestStyle: {},
      screeningMethodOptions: [...SCREENING_METHOD_OPTIONS],
      screeningMethodTones: { ...SCREENING_METHOD_TONES },
      planStatusOptions: [...PLAN_STATUS_OPTIONS],
      priorityOptions: [...PRIORITY_OPTIONS],
      studyTypeOptions: [...STUDY_TYPE_OPTIONS],
      mouseStrainCategoryOptions: [...MOUSE_STRAIN_CATEGORY_OPTIONS],
      mouseStrainOptions: [...MOUSE_STRAIN_OPTIONS],
      editorSections: EDITOR_SECTIONS,
      statusViews: STATUS_VIEWS,
      sheetColumns: SHEET_COLUMN_ORDER.load(),
      workbenchColumns: WORKBENCH_COLUMNS,
      pendingDrawerSaves: new Set(),
      rowBaselines: new Map(),
      listRequestToken: 0,
      listLoaded: false,
      consumingCreated: false,
      tabDataFetchedAt: 0,
      allUserOptions: [],
      targetOptions: [],
      targetRequestToken: 0,
      targetFilterQuery: '',
      handoffVisible: false,
      handoffRow: null,
    }
  },
  computed: {
    canEdit() {
      return canEditDiscoveryWorkbench(this.userStore.userInfo || {})
    },
    canHandoff() {
      return canHandoffLibrary(this.userStore.userInfo || {})
    },
    canViewSerumProject() {
      return canAccessSerumDetail(this.userStore.userInfo || {})
    },
    boostFilterTitle() {
      if (this.listQuery.boost_filter === 'need_boost') {
        return '当前只看已排剖鼠、未排冲击免。右键取消；左键改看冲击免中。'
      }
      if (this.listQuery.boost_filter === 'boosting') {
        return '当前只看冲击免中。再点取消；右键改看未排冲击免。'
      }
      return '左键只看冲击免中；右键只看已排剖鼠但未排冲击免。'
    },
    activeViewGroup() {
      return this.listQuery.view_group || ''
    },
    filteredTargetOptions() {
      return filterTargetOptions(this.optionLists.targets, this.targetFilterQuery)
    },
    editingRow() {
      return this.editingRowData
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
        || this.boostRange?.length,
      )
    },
    screeningSelectOptions() {
      return this.screeningMethodOptions.map((item) => ({ label: item, value: item }))
    },
    sheetTargetSelectOptions() {
      return this.targetOptions.map((item) => ({
        label: `${item.name}（${item.snum}）`,
        value: item.snum,
      }))
    },
  },
  created() {
    this.loading = true
    this.loadOptions()
    const remembered = Boolean(pendingDiscoveryId)
    const listing = remembered ? this.openRememberedDiscovery() : this.getList()
    listing.finally(() => {
      this.listLoaded = true
      if (!remembered) this.consumeCreatedQuery()
    })
    if (this.isExcelMode) this.loadAllUserOptions()
  },
  mounted() {
    document.addEventListener('mousedown', this.onDocumentPointerDown, true)
    this.scheduleSortable()
  },
  beforeUnmount() {
    this.destroySortable()
    document.removeEventListener('mousedown', this.onDocumentPointerDown, true)
  },
  activated() {
    document.addEventListener('mousedown', this.onDocumentPointerDown, true)
    if (pendingDiscoveryId) {
      this.openRememberedDiscovery()
      return
    }
    if (this.listLoaded && shouldRefreshTabData(this.tabDataFetchedAt)) {
      this.getList()
    } else {
      this.scheduleSortable()
    }
  },
  deactivated() {
    this.closeEditor()
    this.destroySortable()
    document.removeEventListener('mousedown', this.onDocumentPointerDown, true)
  },
  watch: {
    viewMode(value) {
      lastViewMode = coerceWorkbenchViewMode(value)
      if (this.isExcelMode) {
        this.destroySortable()
        this.loadAllUserOptions()
      } else {
        this.scheduleSortable()
      }
    },
    drawerVisible(open) {
      if (open) this.syncDrawerTextareas()
      if (!open && this.editingId) {
        this.rememberDrawerSave(this.flushDirtyEditor())
        this.editingId = null
        this.editingRowData = null
      }
    },
    editingId() {
      if (this.drawerVisible) this.syncDrawerTextareas()
    },
    '$route.query.created'() {
      if (this.listLoaded) this.consumeCreatedQuery()
    },
  },
  methods: {
    syncDrawerTextareas() {
      this.$nextTick(() => {
        const nodes = [...document.querySelectorAll('.workbench-drawer .drawer-field.is-synced textarea')]
        if (nodes.length < 2) return
        nodes.forEach((node) => { node.style.height = 'auto' })
        const height = Math.max(...nodes.map((node) => node.scrollHeight))
        nodes.forEach((node) => { node.style.height = `${height}px` })
      })
    },
    splitCsv,
    formatMethods(row) {
      const list = row?.screening_method_list || splitCsv(row?.screening_methods)
      return list.length ? list.join('，') : ''
    },
    normalizeRow(row) {
      const next = { ...row }
      const codes = Array.isArray(next.target_codes) ? next.target_codes : splitCsv(next.target_codes)
      next.target_codes = codes
      const methodList = Array.isArray(next.screening_method_list) ? next.screening_method_list : []
      next.screening_method_list = methodList.length
        ? splitCsv(methodList.join(','))
        : splitCsv(next.screening_methods)
      next.status = next.status || '规划中'
      next.priority = canonicalizeWorkbenchPriority(next.priority)
      return next
    },
    comparableValue(field, value) {
      if (field === 'target_codes') {
        return splitCsv(Array.isArray(value) ? value.join(',') : value).join(',')
      }
      if (field === 'screening_methods') {
        return splitCsv(Array.isArray(value) ? value.join(',') : value).join(',')
      }
      if (field === 'mouse_count') {
        return value === null || value === undefined || value === '' ? '' : String(value)
      }
      return String(value ?? '')
    },
    sameSheetValue(key, left, right) {
      if (key === 'target_codes') {
        return this.comparableValue('target_codes', left) === this.comparableValue('target_codes', right)
      }
      if (key === 'screening_methods') {
        return this.comparableValue('screening_methods', left)
          === this.comparableValue('screening_methods', right)
      }
      return String(left ?? '').trim() === String(right ?? '').trim()
    },
    fieldComparable(row, field) {
      if (!row) return ''
      if (field === 'screening_methods') return this.comparableValue(field, row.screening_method_list)
      if (field === 'target_codes') return this.comparableValue(field, row.target_codes)
      return this.comparableValue(field, row[field])
    },
    payloadRow(row, fields) {
      const payload = { id: row.id }
      const list = [...fields]
      if (list.includes('target_codes') && !list.includes('target_name')) list.push('target_name')
      if (list.includes('target_name') && !list.includes('target_codes')) list.push('target_codes')
      list.forEach((field) => {
        if (field === 'discovery_id') return
        if (field === 'target_codes') {
          payload.target_codes = uniqueTargetCodes(row.target_codes)
        } else if (field === 'screening_methods') {
          payload.screening_methods = row.screening_method_list || splitCsv(row.screening_methods)
        } else if (field === 'mouse_count') {
          payload.mouse_count = row.mouse_count === '' || row.mouse_count == null ? null : row.mouse_count
        } else {
          payload[field] = row[field]
        }
      })
      return payload
    },
    updateRowBaseline(row) {
      if (!row?.id) return
      this.rowBaselines.set(row.id, JSON.parse(JSON.stringify(row)))
    },
    savedFieldKeys(fields) {
      const keys = new Set(fields)
      if (keys.has('target_codes') || keys.has('target_name')) {
        keys.add('target_codes')
        keys.add('target_name')
      }
      if (keys.has('screening_methods')) keys.add('screening_method_list')
      if (keys.has('harvest_date')) keys.add('boost_date')
      if (keys.has('boost_date') || keys.has('harvest_date')) keys.add('status')
      return keys
    },
    syncDrawerFromSaved(normalized, fields) {
      if (this.editingId !== normalized?.id || !this.editingRowData) return
      const dirty = new Set(this.drawerDirtyFields(this.editingRowData))
      const keys = fields ? this.savedFieldKeys(fields) : Object.keys(normalized)
      keys.forEach((key) => {
        if (key === 'id' || !(key in normalized)) return
        if (key === 'target_codes' && dirty.has('target_codes')) return
        if ((key === 'screening_methods' || key === 'screening_method_list') && dirty.has('screening_methods')) return
        if (dirty.has(key)) return
        this.editingRowData[key] = normalized[key]
      })
    },
    applySavedFields(saved, fields) {
      const { normalized } = this.patchExistingListRow(saved, fields)
      this.syncDrawerFromSaved(normalized, fields)
      this.updateRowBaseline(normalized)
    },
    async persistRow(row, field) {
      if (!this.canEdit || !row?.id) return
      if (typeof row[field] === 'string') {
        row[field] = cleanFieldText(row[field], {
          keepBreaks: BREAK_FIELDS.has(field),
        })
      }
      if (field === 'mouse_count' || field === 'sort_order') {
        const result = this.coerceSheetValue(field, row[field])
        if (!result.ok) {
          const baseline = this.rowBaselines.get(row.id)
          row[field] = baseline?.[field] ?? null
          ElMessage.warning(this.sheetValidationMessage(field, result.reason))
          return
        }
        row[field] = result.value
      }
      const baseline = this.rowBaselines.get(row.id)
      if (baseline && this.fieldComparable(row, field) === this.fieldComparable(baseline, field)) {
        return
      }
      try {
        const saved = await saveDiscoveryWorkbench(this.payloadRow(row, [field]))
        if (QUEUE_KEYS.includes(field)) {
          await this.getList({ flushEditor: false })
          return saved
        }
        this.applySavedFields(saved, [field])
        return saved
      } catch (error) {
        notifyApiError(error, { messages: { default: '保存失败' } })
        this.getList({ flushEditor: false })
        return null
      }
    },
    updatePlanStatus(row, value) {
      row.status = value
      return this.persistRow(row, 'status')
    },
    uniq(values) {
      return uniqueNames(values)
    },
    syncDrawerControlTooltip,
    drawerSelectClass(field) {
      if (field?.key === 'status') {
        return `status-select status-tone-${this.planStatusTone(this.editingRow?.status)}`
      }
      if (field?.key === 'priority') {
        return `priority-select status-tone-${this.priorityTone(this.editingRow)}`
      }
      return ''
    },
    fieldOptions(field) {
      if (field?.options) return field.options
      if (field?.key === 'status') return this.planStatusOptions
      if (field?.key === 'priority') return this.priorityOptions
      return []
    },
    usedUserOptions(field) {
      return this.uniq([
        ...(this.optionLists[USER_OPTION_LIST[field?.key]] || []),
        this.editingRow?.[field?.key],
      ])
    },
    lineSuggestions(field) {
      const options = this.uniq(antigenLines(this.editingRow?.immune_antigen))
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
    isUserColumn(column) {
      return Object.prototype.hasOwnProperty.call(USER_OPTION_LIST, column?.key)
    },
    isSheetChoiceColumn(column) {
      return column?.edit === 'multi' || column?.edit === 'select'
    },
    splitCategories,
    displayCsvField,
    categorySheetSelect() {
      return document.querySelector('.sheet-category-select')?.__vueParentComponent?.proxy
    },
    isCsvField(key) {
      return Object.prototype.hasOwnProperty.call(CSV_FIELD_OPTIONS, key)
    },
    csvFieldOptions(key) {
      return CSV_FIELD_OPTIONS[key] || []
    },
    extraCsvOptions(key, value) {
      const known = new Set(this.csvFieldOptions(key))
      return splitCategories(value).filter((item) => !known.has(item))
    },
    onCsvFieldChange(row, key, values) {
      row[key] = joinCsvField(key, values) || null
      if (this.sheetEditSource === 'dblclick') return
      this.persistRow(row, key)
    },
    onCategorySheetVisible(visible) {
      if (visible) return
      this.$nextTick(() => {
        if (this.categorySheetSelect()?.expanded) return
        this.$refs.sheetTable?.clearEdit?.()
      })
    },
    openSheetEditorPanel(row, key) {
      if (!this.isCsvField(key)) {
        workbenchExcelMixin.methods.openSheetEditorPanel.call(this, row, key)
        return
      }
      const open = () => {
        const select = this.categorySheetSelect()
        if (!select) return false
        select.expanded = true
        return true
      }
      this.$nextTick(() => {
        if (!open()) this.$nextTick(open)
      })
    },
    formatCodesText(value) {
      return uniqueTargetCodes(value).join(',')
    },
    async loadAllUserOptions() {
      try {
        this.allUserOptions = await loadSerumUserOptions()
      } catch {
        this.allUserOptions = []
      }
    },
    mergeTargetOptions(items) {
      const map = new Map((this.targetOptions || []).map((item) => [item.snum, item]))
      ;(items || []).forEach((item) => {
        if (item?.snum) map.set(item.snum, item)
      })
      this.targetOptions = [...map.values()]
    },
    onDrawerTargetChange(row, payload) {
      row.target_codes = payload.codes
      row.target_name = payload.name
      this.mergeTargetOptions(payload.items)
      this.persistRow(row, 'target_codes')
    },
    setTargetFilterQuery(query) {
      this.targetFilterQuery = query || ''
    },
    targetOptionExtra(item) {
      return targetOptionHint(item, this.targetFilterQuery)
    },
    async searchTargetOptions(keyword, selectedCodes) {
      const requestToken = ++this.targetRequestToken
      try {
        const items = await searchWorkbenchTargets(keyword, selectedCodes)
        if (requestToken !== this.targetRequestToken) return
        this.mergeTargetOptions(items)
        this.targetOptions = items
      } catch {
        if (requestToken === this.targetRequestToken) {
          this.targetOptions = this.targetOptions || []
        }
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
    sheetTargetDirectValue(row, key) {
      return key === 'target_codes' ? this.formatCodesText(row.target_codes) : row.target_name
    },
    setSheetTargetDirectValue(row, key, value) {
      if (key === 'target_codes') {
        row.target_codes = uniqueTargetCodes(value)
        return
      }
      row.target_name = value
    },
    sheetPickerDisplayValue(row, column) {
      if (column.key === 'target_codes') return this.formatCodesText(row.target_codes)
      if (column.key === 'target_name') return row.target_name || ''
      if (column.key === 'screening_methods') return this.formatMethods(row)
      return row[column.key] ?? ''
    },
    sheetChoiceSelectOptions(column) {
      if (column.key === 'screening_methods') return this.screeningSelectOptions
      if (column.key === 'priority') {
        return this.priorityOptions.map((item) => ({ label: item, value: item }))
      }
      if (column.key === 'status') {
        return this.planStatusOptions.map((item) => ({ label: item, value: item }))
      }
      if (this.isUserColumn(column)) {
        return this.uniq([
          ...(this.optionLists[USER_OPTION_LIST[column.key]] || []),
          ...this.allUserOptions,
        ]).map((item) => ({
          label: item,
          value: item,
        }))
      }
      if (column.key === 'study_type') {
        return this.studyTypeOptions.map((item) => ({
          label: item,
          value: item,
        }))
      }
      return []
    },
    sheetChoiceDirectValue(row, column) {
      if (column.key === 'screening_methods') return this.sheetDirectTextValue(row, column.key)
      return row[column.key] ?? ''
    },
    setSheetChoiceDirectValue(row, column, value) {
      this.setSheetDirectValue(row, column.key, value)
    },
    createSheetEditOriginal(row, key) {
      return {
        key,
        rowId: row.id,
        targetCodes: this.cloneSheetValue(row.target_codes),
        targetName: row.target_name,
        value: this.cloneSheetValue(this.sheetValueSnapshot(row, key)),
      }
    },
    async flushExcelKeyboardSwitch(previousKey, nextKey) {
      if (
        ['target_codes', 'target_name'].includes(previousKey)
        && ['target_codes', 'target_name'].includes(nextKey)
        && this.pendingSheetOps.size
      ) {
        await Promise.allSettled([...this.pendingSheetOps])
      }
    },
    async resolveTargetCodes(codes) {
      const normalized = uniqueTargetCodes(codes)
      if (!normalized.length) return { missing: [], nameByCode: new Map(), names: [] }
      const items = await searchWorkbenchTargets('', normalized)
      this.mergeTargetOptions(items)
      const nameByCode = new Map(items.map((item) => [item.snum, item.name]))
      return {
        missing: normalized.filter((code) => !nameByCode.has(code)),
        nameByCode,
        names: normalized.map((code) => nameByCode.get(code)).filter(Boolean),
      }
    },
    async resolveTargetNames(value) {
      const names = splitTargetNames(value)
      if (!names.length) {
        return { ambiguous: [], itemByName: new Map(), items: [], missing: [] }
      }
      const results = await Promise.all(
        names.map(async (name) => {
          const items = await searchWorkbenchTargets(name)
          const exact = items.filter(
            (item) => String(item.name || '').trim().toLowerCase() === name.toLowerCase(),
          )
          this.mergeTargetOptions(exact)
          return { exact, name }
        }),
      )
      const missing = results.filter((item) => item.exact.length === 0).map((item) => item.name)
      const ambiguous = results.filter((item) => item.exact.length > 1).map((item) => item.name)
      const matched = results.filter((item) => item.exact.length === 1)
      return {
        ambiguous,
        itemByName: new Map(matched.map((item) => [item.name.toLowerCase(), item.exact[0]])),
        items: matched.map((item) => item.exact[0]),
        missing,
      }
    },
    rowPriority(row) {
      return canonicalizeWorkbenchPriority(row?.priority)
    },
    priorityTone(row) {
      return getTiterPriorityTone(this.rowPriority(row))
    },
    planStatusTone(status) {
      const value = String(status || '').trim() || '规划中'
      if (value === '已取消') return 'info'
      if (value === '已完成') return 'success'
      if (value === '待测序') return 'warning'
      if (value.startsWith('待')) return 'primary'
      return 'info'
    },
    drawerDirtyFields(row) {
      const baseline = this.rowBaselines.get(row?.id)
      if (!row || !baseline) return []
      const dirty = []
      if (this.comparableValue('target_codes', row.target_codes) !== this.comparableValue('target_codes', baseline.target_codes)) {
        dirty.push('target_codes')
      }
      if (this.comparableValue('screening_methods', row.screening_method_list) !== this.comparableValue('screening_methods', baseline.screening_method_list)) {
        dirty.push('screening_methods')
      }
      EDITABLE_FIELDS.forEach((field) => {
        if (field === 'target_codes' || field === 'screening_methods') return
        if (this.comparableValue(field, row[field]) !== this.comparableValue(field, baseline[field])) {
          dirty.push(field)
        }
      })
      return dirty
    },
    flushDirtyEditor() {
      const row = this.editingRowData
      const fields = this.drawerDirtyFields(row)
      if (!fields.length) return null
      return saveDiscoveryWorkbench(this.payloadRow(row, fields))
        .then((saved) => {
          this.applySavedFields(saved)
          return saved
        })
        .catch((error) => {
          notifyApiError(error, { messages: { default: '保存失败' } })
          return null
        })
    },
    rememberDrawerSave(savePromise) {
      if (!savePromise) return null
      const pending = Promise.resolve(savePromise).finally(() => {
        this.pendingDrawerSaves.delete(pending)
      })
      this.pendingDrawerSaves.add(pending)
      return pending
    },
    async flushEditorForAction(row) {
      if (!row?.id) return true
      if (!await this.flushPendingSheetEdits()) return false
      if (this.editingId === row.id) {
        const savePromise = this.rememberDrawerSave(this.flushDirtyEditor())
        if (savePromise) return Boolean(await savePromise)
      }
      return true
    },
    openEditor(row) {
      if (!row?.id) return
      if (this.drawerVisible && this.editingId === row.id) {
        this.closeEditor()
        return
      }
      if (this.editingId) this.rememberDrawerSave(this.flushDirtyEditor())
      this.editingId = row.id
      this.editingRowData = this.normalizeRow(JSON.parse(JSON.stringify(row)))
      if (!this.rowBaselines.has(row.id)) this.updateRowBaseline(this.editingRowData)
      this.drawerVisible = true
    },
    closeEditor() {
      this.rememberDrawerSave(this.flushDirtyEditor())
      this.editingId = null
      this.editingRowData = null
      this.drawerVisible = false
    },
    shiftEditor(delta) {
      const next = this.list[this.editingIndex + delta]
      if (next) this.openEditor(next)
    },
    workbenchRowClassName({ row }) {
      return row.id === this.editingId ? 'is-editing' : ''
    },
    onWorkbenchRowClick(row, _column, event) {
      if (event?.target?.closest?.('.el-button, .el-input, .el-select, .el-date-editor, .action-cell, .sort-column-cell, .workbench-status-tag')) {
        return
      }
      this.openEditor(row)
    },
    onWorkbenchRowContextMenu(_row, _column, event) {
      if (!this.drawerVisible) return
      event?.preventDefault?.()
      this.closeEditor()
    },
    onDocumentPointerDown(event) {
      if (!this.drawerVisible) return
      const target = event.target
      if (!(target instanceof Element)) return
      if (target.closest('.el-drawer, .el-popper, .el-select-dropdown, .el-picker-panel, .el-message-box, .el-overlay-message-box, .sheet-picker-popup, .line-suggest')) {
        return
      }
      if (target.closest('.el-table__row, .vxe-body--row, .action-cell')) {
        return
      }
      this.closeEditor()
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
      return payload
    },
    async loadOptions() {
      try {
        const data = await fetchDiscoveryWorkbenchOptions(skipGlobalErrorHandler)
        if (Array.isArray(data?.screening_methods) && data.screening_methods.length) {
          this.screeningMethodOptions = data.screening_methods
        }
        this.optionLists.targets = normalizeTargetOptions(data?.targets)
        this.optionLists.pms = this.uniq(data?.pms || [])
        this.optionLists.owners = this.uniq(data?.owners || [])
        this.optionLists.immune_owners = this.uniq(data?.immune_owners || [])
        this.optionLists.cell_collectors = this.uniq(data?.cell_collectors || [])
        this.optionLists.immune_antigens = this.uniq(data?.immune_antigens || [])
        this.optionLists.boost_antigens = this.uniq(data?.boost_antigens || [])
        this.optionLists.screening_antigens = this.uniq(data?.screening_antigens || [])
      } catch (error) {
        notifyApiError(error, { messages: { default: '加载发现工作台选项失败' } })
      }
    },
    async getList({ flushEditor = true } = {}) {
      this.loading = true
      const requestToken = ++this.listRequestToken
      try {
        if (flushEditor) {
          await this.flushPendingSheetEdits()
          await this.rememberDrawerSave(this.flushDirtyEditor())
          if (this.pendingDrawerSaves.size) {
            await Promise.all([...this.pendingDrawerSaves])
          }
        }
        if (requestToken !== this.listRequestToken) return
        const data = await fetchDiscoveryWorkbenchList(this.buildQuery(), skipGlobalErrorHandler)
        if (requestToken !== this.listRequestToken) return
        this.list = (data?.items || []).map((row) => this.normalizeRow(row))
        this.list.forEach((row) => this.updateRowBaseline(row))
        this.total = data?.total || 0
        this.stats = {
          all: data?.stats?.all || 0,
          harvest: data?.stats?.harvest || 0,
          library: data?.stats?.library || 0,
          sequencing: data?.stats?.sequencing || 0,
          cancelled: data?.stats?.cancelled || 0,
          boosting: data?.stats?.boosting || 0,
          need_boost: data?.stats?.need_boost || 0,
        }
        this.listQuery.page = data?.page || this.listQuery.page
        this.listQuery.limit = data?.limit || this.listQuery.limit
        const selected = this.list.find((row) => row.id === this.editingId)
        if (selected && !this.drawerDirtyFields(this.editingRowData).length) {
          this.editingRowData = this.normalizeRow(JSON.parse(JSON.stringify(selected)))
        }
        this.tabDataFetchedAt = Date.now()
        this.clearSheetRange()
        this.scheduleSortable()
      } catch (error) {
        if (requestToken === this.listRequestToken) {
          notifyApiError(error, { messages: { default: '加载发现工作台失败' } })
        }
      } finally {
        if (requestToken === this.listRequestToken) this.loading = false
      }
    },
    handleFilter() {
      this.listQuery.page = 1
      this.getList()
    },
    toggleQueueSort() {
      this.listQuery.sort_dir = ''
      this.listQuery.sort_field = this.isQueueSorted ? '' : 'sort_order'
      this.listQuery.page = 1
      this.getList()
    },
    dateSortMark(field) {
      if (this.listQuery.sort_field !== field) return ''
      return this.listQuery.sort_dir === 'desc' ? ' ↓' : ' ↑'
    },
    dateSortTitle(field) {
      const label = field === 'boost_date' ? '冲击日期' : '剖鼠日期'
      if (this.listQuery.sort_field !== field) return `左键按${label}从早到晚`
      if (this.listQuery.sort_dir === 'asc') return '当前从早到晚。再点改为从晚到早'
      return '当前从晚到早。再点恢复最新在前'
    },
    excelHeaderClick(column) {
      if (column?.key !== 'harvest_date' && column?.key !== 'boost_date') return false
      this.cycleDateSort(column.key)
      return true
    },
    cycleDateSort(field) {
      if (this.listQuery.sort_field === field && this.listQuery.sort_dir === 'asc') {
        this.listQuery.sort_dir = 'desc'
      } else if (this.listQuery.sort_field === field && this.listQuery.sort_dir === 'desc') {
        this.listQuery.sort_field = ''
        this.listQuery.sort_dir = ''
      } else {
        this.listQuery.sort_field = field
        this.listQuery.sort_dir = 'asc'
      }
      this.listQuery.page = 1
      this.getList()
    },
    resetFilters() {
      const viewGroup = this.listQuery.view_group
      const sortField = this.listQuery.sort_field
      const sortDir = this.listQuery.sort_dir
      this.listQuery = { ...emptyQuery(), view_group: viewGroup, sort_field: sortField, sort_dir: sortDir }
      this.harvestRange = []
      this.boostRange = []
      this.getList()
    },
    handleViewGroup(key) {
      this.listQuery.view_group = key || ''
      this.handleFilter()
    },
    toggleBoostFilter(value) {
      this.listQuery.boost_filter = this.listQuery.boost_filter === value ? '' : value
      this.handleFilter()
    },
    async toggleViewMode() {
      if (this.isExcelMode && !await this.flushPendingSheetEdits()) return
      this.viewMode = this.isExcelMode ? WORKBENCH_VIEW : EXCEL_VIEW
      if (this.isExcelMode) this.closeEditor()
    },
    async resetSheetColumnOrder() {
      if (this.isExcelMode) {
        if (!await this.flushPendingSheetEdits()) return
        SHEET_COLUMN_ORDER.clear()
        this.sheetColumns = [...SHEET_COLUMNS]
        this.persistSheetColumnOrder(this.sheetColumns)
        this.clearSheetRange()
        return
      }
      this.$refs.workbenchTable?.resetColumnOrder()
    },
    openColumnPicker() {
      this.$refs.workbenchTable?.openColumnPicker()
    },
    persistSheetColumnOrder(columns) {
      SHEET_COLUMN_ORDER.save(columns)
    },
    isQueueTerminalRow(row) {
      return QUEUE_TERMINAL_STATUSES.includes(String(row?.status || '').trim())
    },
    async openSerumProject(row) {
      const experimentId = String(row?.experiment_id || '').trim()
      if (!this.canViewSerumProject) {
        ElMessage.warning('您没有免疫实验详情权限')
        return
      }
      if (!experimentId) {
        ElMessage.warning('请先填写实验号')
        return
      }
      if (!await this.flushEditorForAction(row)) return
      try {
        const detail = await fetchSerumDetailByExperimentId(experimentId)
        const projectId = Number(detail?.id)
        if (!Number.isSafeInteger(projectId) || projectId <= 0) {
          ElMessage.warning('未找到对应的免疫项目')
          return
        }
        this.$router.push({ path: '/serum/detail', query: { id: projectId } })
      } catch (error) {
        notifyApiError(error, { messages: { default: '未找到对应的免疫项目' } })
      }
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
          /* 没有暂存仍按 id 打开 */
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
      const discoveryId = pendingDiscoveryId
      pendingDiscoveryId = ''
      if (!discoveryId || this.$route.name !== 'DiscoveryWorkbench') return
      this.closeEditor()
      this.listQuery = { ...emptyQuery(), keyword: discoveryId }
      this.harvestRange = []
      this.boostRange = []
      await this.getList()
      const row = this.list.find((item) => item.discovery_id === discoveryId)
      if (!row) {
        ElMessage.warning('未找到对应的发现工单')
        return
      }
      this.viewMode = WORKBENCH_VIEW
      this.openEditor(row)
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
    async handleDelete(row) {
      if (!this.canEdit) {
        ElMessage.warning('您没有权限删除抗体发现工作台')
        return
      }
      try {
        await ElMessageBox.confirm(`确认删除安排 ${row.project_code || row.target_name || `#${row.id}`}？删除后不可恢复。`, '删除确认', {
          type: 'warning',
          confirmButtonText: '删除',
          cancelButtonText: '取消',
        })
      } catch {
        return
      }
      if (!await this.flushEditorForAction(row)) return
      try {
        await deleteDiscoveryWorkbench(row.id)
        if (this.editingId === row.id) {
          this.drawerVisible = false
          this.editingId = null
          this.editingRowData = null
        }
        ElMessage.success('已删除')
        this.getList({ flushEditor: false })
      } catch (error) {
        notifyApiError(error, { messages: { default: '删除失败' } })
      }
    },
    async handleListExport() {
      try {
        await downloadListExcel(
          () => exportDiscoveryWorkbenchList(this.buildQuery()),
          `发现工作台_${excelTimestamp()}.xlsx`,
        )
      } catch (error) {
        notifyApiError(error, { messages: { default: '列表导出失败' } })
      }
    },
    formatCodes({ row }) {
      return this.formatCodesText(row.target_codes)
    },
    formatMethodsCell({ row }) {
      return this.sheetDirectTextValue(row, 'screening_methods')
    },
    sheetFormatter(column) {
      if (column.key === 'sort_order') return this.formatSortColumnCell
      if (column.key === 'screening_methods') return this.formatMethodsCell
      if (column.key === 'mouse_strain' || column.key === 'mouse_strain_category') {
        return ({ cellValue }) => displayCsvField(cellValue)
      }
      if (column.key === 'target_codes') return this.formatCodes
      return undefined
    },
    sheetDirectTextValue(row, key) {
      if (!row) return ''
      if (key === 'sort_order') return row.sort_order == null ? '' : String(row.sort_order)
      if (key === 'screening_methods') {
        if (typeof row.screening_methods === 'string' && this.sheetEditOriginal?.rowId === row.id && this.sheetEditOriginal?.key === key) {
          return row.screening_methods
        }
        return this.formatMethods(row)
      }
      if (key === 'target_codes') return this.formatCodesText(row.target_codes)
      if (row[key] === null || row[key] === undefined) return ''
      return String(row[key])
    },
    sheetValueSnapshot(row, key) {
      if (!row) return null
      if (key === 'screening_methods') return [...(row.screening_method_list || splitCsv(row.screening_methods))]
      if (key === 'target_codes') return [...uniqueTargetCodes(row.target_codes)]
      return row[key]
    },
    restoreSheetEditValue(row, key, value) {
      if (key === 'screening_methods') {
        const list = Array.isArray(value) ? [...value] : splitCsv(value)
        row.screening_method_list = list
        row.screening_methods = list.join(',')
        return
      }
      if (key === 'target_codes') {
        row.target_codes = uniqueTargetCodes(value)
        return
      }
      row[key] = this.cloneSheetValue(value)
    },
    normalizeSheetDate(text) {
      const raw = String(text ?? '').trim()
      if (!raw) return { ok: true, value: null }
      const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(raw)
      if (!match) return { ok: false, reason: 'date' }
      const year = Number(match[1])
      const month = Number(match[2])
      const day = Number(match[3])
      const date = new Date(Date.UTC(year, month - 1, day))
      const valid = date.getUTCFullYear() === year
        && date.getUTCMonth() === month - 1
        && date.getUTCDate() === day
      return valid ? { ok: true, value: raw } : { ok: false, reason: 'date' }
    },
    matchSheetOption(options, text) {
      const hit = (options || []).find((item) => item === text || String(item).toLowerCase() === text.toLowerCase())
      return hit ? { ok: true, value: hit } : { ok: false, reason: 'option' }
    },
    coerceSheetValue(key, text) {
      const column = this.sheetColumns.find((item) => item.key === key)
      if (!column) return { ok: false, reason: 'unknown' }
      const raw = Array.isArray(text)
        ? text
        : cleanFieldText(text, { keepBreaks: BREAK_FIELDS.has(key) })
      if (key === 'sort_order') return coerceRequiredPositiveInt(raw)
      if (key === 'priority') {
        const canon = canonicalizeWorkbenchPriority(raw)
        return PRIORITY_OPTIONS.includes(canon) ? { ok: true, value: canon } : { ok: false, reason: 'option' }
      }
      if (key === 'status') {
        const text = String(raw || '').trim()
        if (!text) return { ok: false, reason: 'option' }
        return this.matchSheetOption(this.planStatusOptions, text)
      }
      if (key === 'study_type') {
        const text = String(raw || '').trim()
        if (!text) return { ok: true, value: null }
        return this.matchSheetOption(this.studyTypeOptions, text)
      }
      if (this.isUserColumn({ key })) {
        const text = String(raw || '').trim()
        if (!text) return { ok: true, value: null }
        return this.matchSheetOption(
          this.uniq([...(this.optionLists[USER_OPTION_LIST[key]] || []), ...this.allUserOptions]),
          text,
        )
      }
      if (key === 'mouse_count') return coerceOptionalNonnegInt(raw)
      if (DATE_KEYS.includes(key)) return this.normalizeSheetDate(raw)
      if (this.isCsvField(key)) {
        const tokens = splitCategories(raw)
        if (!tokens.length) return { ok: true, value: null }
        return { ok: true, value: joinCsvField(key, tokens) }
      }
      if (key === 'screening_methods') {
        const options = this.screeningMethodOptions
        const tokens = splitCsv(Array.isArray(raw) ? raw.join(',') : raw)
        if (tokens.some((token) => !options.includes(token))) {
          return { ok: false, reason: 'option' }
        }
        return { ok: true, value: options.filter((item) => tokens.includes(item)) }
      }
      if (key === 'target_codes') {
        return { ok: true, value: uniqueTargetCodes(raw) }
      }
      const maxLen = STRING_MAX[key]
      if (maxLen && String(raw || '').length > maxLen) return { ok: false, reason: 'length' }
      return { ok: true, value: raw === '' ? null : raw }
    },
    assignSheetValue(row, key, text) {
      if (this.isSheetCellLocked(row, key)) return { ok: false, reason: 'locked' }
      const result = this.coerceSheetValue(key, text)
      if (!result.ok) return result
      this.restoreSheetEditValue(row, key, result.value)
      return { ok: true }
    },
    sheetValidationMessage(key, reason) {
      const label = this.sheetColumns.find((item) => item.key === key)?.label || '当前字段'
      if (reason === 'date') return `${label}必须是 YYYY-MM-DD 格式的有效日期`
      if (reason === 'integer') return `${label}必须是 0 或正整数`
      if (reason === 'length') {
        const maxLen = STRING_MAX[key]
        return maxLen ? `${label}不能超过 ${maxLen} 个字` : `${label}超出长度限制`
      }
      if (reason === 'locked') return `${label}当前不可编辑`
      if (reason === 'unknown') return '粘贴内容包含无法识别的列'
      return `${label}必须与可选项完全匹配`
    },
    async finishSheetEdit({ row, column }) {
      const key = column?.field
      if (!key || !row?.id) return
      const editSource = this.sheetEditSource
      this.sheetEditSource = ''
      const originalRecord = this.sheetEditOriginal
      const originalValue = this.takeSheetEditOriginal(row, key)
      if (this.isSheetCellLocked(row, key)) {
        this.restoreSheetEditValue(row, key, originalValue)
        return
      }
      const columnConfig = this.sheetColumns.find((item) => item.key === key)
      if (editSource === 'dblclick' && columnConfig?.edit === 'target') {
        const codes = uniqueTargetCodes(row.target_codes)
        const submittedName = String(row.target_name || '')
        const originalCodes = originalRecord?.targetCodes ?? originalValue
        const originalName = originalRecord?.targetName ?? this.rowBaselines.get(row.id)?.target_name ?? ''
        if (
          this.sameSheetValue('target_codes', codes, originalCodes)
          && this.sameSheetValue('target_name', submittedName, originalName)
        ) {
          return
        }
        try {
          const resolved = await this.resolveTargetCodes(codes)
          if (
            !this.sameSheetValue('target_codes', row.target_codes, codes)
            || !this.sameSheetValue('target_name', row.target_name, submittedName)
          ) {
            return
          }
          if (resolved.missing.length) throw new Error('target-missing')
          row.target_codes = codes
          row.target_name = resolved.names.join('&')
          return this.persistRow(row, 'target_codes')
        } catch {
          if (
            !this.sameSheetValue('target_codes', row.target_codes, codes)
            || !this.sameSheetValue('target_name', row.target_name, submittedName)
          ) {
            return
          }
          row.target_codes = this.cloneSheetValue(originalCodes)
          row.target_name = originalName
          ElMessage.warning('靶点校验失败，本次修改未保存')
        }
        return
      }
      const source = key === 'screening_methods'
        ? (editSource === 'dblclick' ? row.screening_method_list : row.screening_methods)
        : (key === 'target_codes' ? row.target_codes : row[key])
      const result = this.coerceSheetValue(key, source)
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
      if (key === 'target_codes') {
        const submittedCodes = [...row.target_codes]
        const submittedName = String(row.target_name || '')
        try {
          const resolved = await this.resolveTargetCodes(submittedCodes)
          if (
            !this.sameSheetValue('target_codes', row.target_codes, submittedCodes)
            || !this.sameSheetValue('target_name', row.target_name, submittedName)
          ) {
            return
          }
          if (resolved.missing.length) {
            this.restoreSheetEditValue(row, key, originalValue)
            ElMessage.warning(`未找到靶点编号：${resolved.missing.join('、')}`)
            return
          }
          row.target_name = resolved.names.join('&')
        } catch {
          if (
            !this.sameSheetValue('target_codes', row.target_codes, submittedCodes)
            || !this.sameSheetValue('target_name', row.target_name, submittedName)
          ) {
            return
          }
          this.restoreSheetEditValue(row, key, originalValue)
          ElMessage.warning('靶点校验失败，本次修改未保存')
          return
        }
      }
      if (key === 'target_name') {
        const submittedName = String(row.target_name || '').trim()
        const submittedCodes = this.cloneSheetValue(row.target_codes)
        try {
          const resolved = await this.resolveTargetNames(row.target_name)
          if (
            !this.sameSheetValue('target_name', row.target_name, submittedName)
            || !this.sameSheetValue('target_codes', row.target_codes, submittedCodes)
          ) {
            return
          }
          if (resolved.missing.length) {
            this.restoreSheetEditValue(row, key, originalValue)
            ElMessage.warning(`未找到靶点名称：${resolved.missing.join('、')}`)
            return
          }
          if (resolved.ambiguous.length) {
            this.restoreSheetEditValue(row, key, originalValue)
            ElMessage.warning(`靶点名称不唯一，请双击选择：${resolved.ambiguous.join('、')}`)
            return
          }
          row.target_codes = resolved.items.map((item) => item.snum)
          row.target_name = resolved.items.map((item) => item.name).join('&')
        } catch {
          if (
            !this.sameSheetValue('target_name', row.target_name, submittedName)
            || !this.sameSheetValue('target_codes', row.target_codes, submittedCodes)
          ) {
            return
          }
          this.restoreSheetEditValue(row, key, originalValue)
          ElMessage.warning('靶点校验失败，本次修改未保存')
          return
        }
      }
      return this.persistRow(row, key)
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

      const labelToKey = new Map([
        ...Object.entries(SHEET_HEADER_ALIASES),
        ...SHEET_COLUMNS.map((column) => [column.label, column.key]),
      ])
      const headerKeys = grid[0].map((cell) => labelToKey.get(String(cell || '').trim()) || null)
      const nonEmptyHeaderCount = grid[0].filter((cell) => String(cell || '').trim()).length
      const matchedHeaderCount = headerKeys.filter(Boolean).length
      const hasHeader = matchedHeaderCount >= 2 && matchedHeaderCount === nonEmptyHeaderCount
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
      const availableRowCount = Math.max(this.list.length - startIndex, 0)
      const skippedRowCount = Math.max(dataRows.length - availableRowCount, 0)
      dataRows.splice(availableRowCount)
      if (!dataRows.length) {
        ElMessage.warning('粘贴区域超出当前列表，本次未保存')
        return
      }

      const workingRows = this.list.map((row) => this.normalizeRow(JSON.parse(JSON.stringify(row))))
      const dirtyByIndex = new Map()
      const targetFieldsByIndex = new Map()
      const invalidCells = []
      const touchedCells = []
      dataRows.forEach((cells, offset) => {
        if (cells.every((cell) => String(cell ?? '') === '')) return
        const rowIndex = startIndex + offset
        const row = workingRows[rowIndex]
        if (!row) return
        cells.forEach((cell, cellIndex) => {
          const key = hasHeader ? headerKeys[cellIndex] : this.sheetColumns[startColIndex + cellIndex]?.key
          if (!key) {
            if (String(cell ?? '').trim()) invalidCells.push({ reason: 'unknown' })
            return
          }
          const column = SHEET_COLUMNS.find((item) => item.key === key)
          if (!column) return
          const result = this.assignSheetValue(row, key, cell)
          if (result.ok) {
            touchedCells.push({ rowId: row.id, key })
            const fields = dirtyByIndex.get(rowIndex) || new Set()
            fields.add(key)
            dirtyByIndex.set(rowIndex, fields)
            if (key === 'target_codes' || key === 'target_name') {
              const targetFields = targetFieldsByIndex.get(rowIndex) || new Set()
              targetFields.add(key)
              targetFieldsByIndex.set(rowIndex, targetFields)
            }
            return
          }
          invalidCells.push({ ...result, key })
        })
      })
      if (invalidCells.length) {
        const firstInvalid = invalidCells[0]
        const message = firstInvalid.reason === 'unknown'
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
          const resolvedCodes = await this.resolveTargetCodes(
            codeEntries.flatMap(({ row }) => row.target_codes || []),
          )
          if (resolvedCodes.missing.length) {
            ElMessage.warning(`未找到靶点编号：${resolvedCodes.missing.join('、')}，本次粘贴未保存`)
            return
          }
          codeEntries.forEach(({ fields, row }) => {
            const canonicalNames = (row.target_codes || [])
              .map((code) => resolvedCodes.nameByCode.get(code))
            if (fields.has('target_name')) {
              const submittedNames = splitTargetNames(row.target_name)
              const matches = submittedNames.length === canonicalNames.length
                && submittedNames.every(
                  (name, index) => name.toLowerCase() === String(canonicalNames[index] || '').toLowerCase(),
                )
              if (!matches) throw new Error('target-mismatch')
            }
            row.target_name = canonicalNames.join('&')
          })
          const nameOnlyEntries = targetEntries.filter(
            ({ fields }) => fields.has('target_name') && !fields.has('target_codes'),
          )
          const resolvedNames = await this.resolveTargetNames(
            nameOnlyEntries.flatMap(({ row }) => splitTargetNames(row.target_name)).join('&'),
          )
          if (resolvedNames.missing.length) {
            ElMessage.warning(`未找到靶点名称：${resolvedNames.missing.join('、')}，本次粘贴未保存`)
            return
          }
          if (resolvedNames.ambiguous.length) {
            ElMessage.warning(`靶点名称不唯一：${resolvedNames.ambiguous.join('、')}，本次粘贴未保存`)
            return
          }
          nameOnlyEntries.forEach(({ row }) => {
            const targetItems = splitTargetNames(row.target_name)
              .map((name) => resolvedNames.itemByName.get(name.toLowerCase()))
            row.target_codes = targetItems.map((item) => item.snum)
            row.target_name = targetItems.map((item) => item.name).join('&')
          })
        } catch {
          ElMessage.warning('靶点名称与编号不匹配或校验失败，本次粘贴未保存')
          return
        }
      }

      const items = [...dirtyByIndex.entries()].map(([rowIndex, fields]) => (
        this.payloadRow(workingRows[rowIndex], [...fields])
      ))
      try {
        const result = await saveDiscoveryWorkbenchBatch({ items })
        const savedCount = result?.items?.length || 0
        await this.getList({ flushEditor: false })
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
        notifyApiError(error, { messages: { default: '粘贴保存失败' } })
      }
    },
    bindSortInput(id, el) {
      if (el) this.sortInputRefs[id] = el
      else delete this.sortInputRefs[id]
    },
    startSortEdit(row) {
      if (!this.canEditSortCell(row) || !row?.id) return
      this.sortEditingId = row.id
      this.$nextTick(() => this.sortInputRefs[row.id]?.focus?.())
    },
    finishSortEdit(row) {
      if (this.sortEditingId !== row.id) return
      this.sortEditingId = null
      this.persistRow(row, 'sort_order')
    },
    workbenchTbody() {
      return this.$refs.workbenchTable?.$el?.querySelector('.el-table__body-wrapper tbody')
    },
    dataRowEls(tbody) {
      return [...(tbody?.children || [])].filter((tr) => tr.classList?.contains('el-table__row'))
    },
    scheduleSortable() {
      this.$nextTick(() => this.initSortable())
    },
    async initSortable() {
      const initToken = ++this.sortableInitToken
      if (this.viewMode !== 'workbench' || !this.canDragRows) {
        this.destroySortable()
        return
      }
      await this.$nextTick()
      const tbody = this.workbenchTbody()
      if (!tbody || initToken !== this.sortableInitToken || !tbody.isConnected) return
      if (this.sortable?.el === tbody) return
      this.destroySortable()
      const Sortable = (await import('sortablejs')).default
      if (initToken !== this.sortableInitToken || !tbody.isConnected) return
      this.sortable = Sortable.create(tbody, {
        animation: 180,
        handle: '.sort-column-cell',
        draggable: 'tr.el-table__row',
        ghostClass: 'wb-sortable-ghost',
        onEnd: (event) => this.handleDragEnd(event),
      })
    },
    destroySortable() {
      this.sortable?.destroy?.()
      this.sortable = null
    },
    revertDrag(item, oldIndex, newIndex) {
      const parent = item?.parentNode
      if (!parent || oldIndex == null || newIndex == null || oldIndex === newIndex) return
      const dataRows = this.dataRowEls(parent)
      const anchor = newIndex > oldIndex ? dataRows[oldIndex] : dataRows[oldIndex + 1]
      parent.insertBefore(item, anchor || null)
    },
    async handleDragEnd(event) {
      const { oldIndex, newIndex, item } = event
      this.revertDrag(item, oldIndex, newIndex)
      if (!this.canDragRows || oldIndex == null || newIndex == null || oldIndex === newIndex) return
      const payload = this.queueReorderPayload(oldIndex, newIndex)
      if (!payload) return
      this.loading = true
      try {
        await reorderDiscoveryWorkbench(payload.movedId, payload.targetId)
        await this.getList({ flushEditor: false })
      } catch (error) {
        notifyApiError(error, { messages: { default: '调整排序失败' } })
        await this.getList({ flushEditor: false })
      } finally {
        this.loading = false
      }
    },
    sheetCellClassName({ row, column }) {
      const classes = []
      if (column?.field === 'priority') classes.push(`sheet-tone-${this.priorityTone(row)}`)
      return classes.join(' ')
    },
  },
}
</script>

<style scoped src="#/components/workbench/workbenchConsole.css"></style>
<style scoped src="#/components/workbench/workbenchExcel.css"></style>
<style scoped src="#/components/workbench/workbenchDrawerChrome.css"></style>
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
.filter-panel {
  padding: var(--list-surface-padding-y) var(--list-surface-padding-x);
  margin-bottom: var(--list-page-gap);
  background: var(--list-surface-bg);
  border: var(--list-surface-border);
  border-radius: var(--list-surface-radius);
  box-shadow: var(--list-surface-shadow);
}
.data-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--list-filter-action-gap);
}
.filter-strip {
  display: flex;
  flex: 1 1 0;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 10px;
  min-width: 0;
}
.filter-keyword {
  flex: 2 1 120px;
  min-width: 100px;
}
.ops-user-select {
  min-width: 0;
}
.filter-select {
  flex: 1 1 100px;
  min-width: 100px;
}
.target-option-code {
  margin-left: 8px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.filter-strip :deep(.harvest-range) {
  flex: 1 1 120px;
  width: auto;
  min-width: 100px;
}
.data-view-controls {
  flex-shrink: 0;
  margin-left: auto;
}
.table-card :deep(.is-editing > td) {
  background: #ecf5ff !important;
}
.table-card :deep(.status-column-cell .cell),
.table-card :deep(.action-column-cell .cell),
.table-card :deep(.date-column-cell .cell) {
  display: flex;
  justify-content: center;
  align-items: center;
}
.table-card :deep(.date-column-cell .cell) {
  padding: 4px 10px;
}
.inline-date {
  width: 100%;
  --el-date-editor-width: 100%;
}
.inline-select {
  width: 100%;
}
.inline-select :deep(.el-select__wrapper) {
  min-height: 28px;
  padding: 0 8px;
  box-shadow: 0 0 0 1px #e6e8ee inset;
  background: var(--list-mid-bg);
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
.list-status-tag.status-tone-king {
  color: #6f4d9c;
  background: #efe8f6;
  border-color: #d4c4ea;
}
.sort-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
}
.table-card :deep(td.sort-column-cell .cell) {
  padding-right: 6px;
  padding-left: 6px;
}
.sort-header-btn {
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  cursor: pointer;
}
.sort-header-btn.is-active {
  color: var(--el-color-primary);
  font-weight: 650;
}
.sort-order-value {
  min-width: 22px;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--el-text-color-regular);
  font: inherit;
  line-height: 1.2;
  cursor: text;
}
.sort-order-value:disabled {
  cursor: default;
}
.table-card :deep(.el-table.is-row-sortable td.sort-column-cell),
.table-card :deep(.el-table.is-row-sortable td.sort-column-cell .sort-order-value) {
  cursor: grab;
  user-select: none;
}
.table-card :deep(.el-table.is-row-sortable td.sort-column-cell:active),
.table-card :deep(.el-table.is-row-sortable td.sort-column-cell .sort-order-value:active) {
  cursor: grabbing;
}
.sort-order-input {
  width: 36px;
}
.sort-order-input :deep(.el-input__wrapper) {
  padding: 0 4px;
}
.app-container :deep(.wb-sortable-ghost) {
  opacity: 0.65;
  background: #ecf5ff;
}
.sheet-wrap :deep(.sheet-tone-info) { color: var(--el-color-info); }
.sheet-wrap :deep(.sheet-tone-warning) { color: var(--el-color-warning); }
.sheet-wrap :deep(.sheet-tone-danger) { color: var(--el-color-danger); }
.sheet-wrap :deep(.sheet-tone-king) { color: #6f4d9c; }
.drawer-fieldset {
  margin: 0;
  padding: 0;
  border: 0;
  min-width: 0;
}
.drawer-card {
  padding: 6px 0 0;
  margin-bottom: 6px;
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
  margin: 0 0 6px;
  color: #909399;
  font-size: 12px;
  font-weight: 650;
  letter-spacing: 0.04em;
}
.drawer-card.is-queue .drawer-card-title {
  color: #303133;
}
.drawer-card-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  column-gap: 12px;
}
.drawer-field.is-wide {
  grid-column: 1 / -1;
}
.drawer-field.is-synced :deep(.el-textarea__inner) {
  resize: none;
}
.drawer-form :deep(.el-form-item) {
  margin-bottom: 8px;
}
.drawer-form :deep(.el-form-item__label) {
  color: #606266;
  font-size: 13px;
}
.drawer-form :deep(.el-form-item__content) {
  min-width: 0;
  justify-content: flex-start;
}
.sheet-category-select {
  width: 100%;
}
@media (max-width: 1100px) {
  .lifecycle-nav {
    grid-template-columns: repeat(5, minmax(130px, 1fr));
    overflow-x: auto;
  }
}
</style>

<style>
.workbench-drawer .status-select.status-tone-info .el-select__wrapper,
.workbench-drawer .priority-select.status-tone-info .el-select__wrapper {
  background-color: var(--el-color-info-light-9);
}
.workbench-drawer .status-select.status-tone-info .el-select__selected-item,
.workbench-drawer .priority-select.status-tone-info .el-select__selected-item {
  color: var(--el-color-info);
}
.workbench-drawer .status-select.status-tone-primary .el-select__wrapper {
  background-color: var(--el-color-primary-light-9);
}
.workbench-drawer .status-select.status-tone-primary .el-select__selected-item {
  color: var(--el-color-primary);
}
.workbench-drawer .status-select.status-tone-warning .el-select__wrapper,
.workbench-drawer .priority-select.status-tone-warning .el-select__wrapper {
  background-color: var(--el-color-warning-light-9);
}
.workbench-drawer .status-select.status-tone-warning .el-select__selected-item,
.workbench-drawer .priority-select.status-tone-warning .el-select__selected-item {
  color: var(--el-color-warning);
}
.workbench-drawer .status-select.status-tone-success .el-select__wrapper {
  background-color: var(--el-color-success-light-9);
}
.workbench-drawer .status-select.status-tone-success .el-select__selected-item {
  color: var(--el-color-success);
}
.workbench-drawer .priority-select.status-tone-danger .el-select__wrapper {
  background-color: var(--el-color-danger-light-9);
}
.workbench-drawer .priority-select.status-tone-danger .el-select__selected-item {
  color: var(--el-color-danger);
}
.workbench-drawer .priority-select.status-tone-king .el-select__wrapper {
  background-color: #efe8f6;
}
.workbench-drawer .priority-select.status-tone-king .el-select__selected-item {
  color: #6f4d9c;
}
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
  border: 0;
  background: transparent;
  color: var(--el-text-color-regular);
  font-size: 14px;
  line-height: 34px;
  text-align: left;
  cursor: pointer;
}
.line-suggest-item:hover {
  background: var(--el-fill-color-light);
}
</style>
