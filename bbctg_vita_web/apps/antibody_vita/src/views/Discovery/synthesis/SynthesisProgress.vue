<template>
  <div class="app-container" :class="{ 'is-list-table-locked': listTableLocked }">
    <AdvancedOpsBar v-model="showAdvancedOps">
      <ListFilterSelect
        v-model="listQuery.synthetic_corp"
        clearable
        placeholder="合成公司"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.synthetic_corps" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.order_kind"
        clearable
        placeholder="订单性质"
        @change="handleFilter"
      >
        <el-option v-for="item in orderKindOptions" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.supply_mode"
        clearable
        placeholder="供应方式"
        @change="handleFilter"
      >
        <el-option v-for="item in supplyModeOptions" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.eng_type"
        clearable
        placeholder="改造类型"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.eng_types" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.eng_method"
        clearable
        placeholder="改造方式"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.eng_methods" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.priority"
        clearable
        placeholder="优先级"
        @change="handleFilter"
      >
        <el-option v-for="item in priorityOptions" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <el-input
        v-model="listQuery.assay_note"
        clearable
        placeholder="检测说明"
        @keyup.enter="handleFilter"
        @clear="handleFilter"
      />
      <el-input
        v-model="listQuery.remark"
        clearable
        placeholder="备注"
        @keyup.enter="handleFilter"
        @clear="handleFilter"
      />
      <el-date-picker
        v-model="arrivalDateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="到货起始"
        end-placeholder="到货截止"
        value-format="YYYY-MM-DD"
        @change="handleFilter"
      />
      <el-date-picker
        v-model="flowDateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="流式起始"
        end-placeholder="流式截止"
        value-format="YYYY-MM-DD"
        @change="handleFilter"
      />
      <el-date-picker
        v-model="affinityDateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="亲和力起始"
        end-placeholder="亲和力截止"
        value-format="YYYY-MM-DD"
        @change="handleFilter"
      />
      <el-input
        v-model="listQuery.project_code"
        clearable
        placeholder="项目编号"
        title="多个项目编号或实验号用逗号、空格或换行分隔，按完整编号查找；只填一个时按包含查找"
        @keyup.enter="handleFilter"
        @clear="handleFilter"
      />
      <div class="ops-user-select">
        <SerumUserSelect
          v-model="listQuery.pm"
          multi-gesture
          :options="optionLists.pms"
          placeholder="PM"
          clearable
          @change="handleFilter"
        />
      </div>
      <ListFilterSelect
        v-model="listQuery.study_type"
        clearable
        placeholder="课题类型"
        @change="handleFilter"
      >
        <el-option v-for="item in studyTypeOptions" :key="item" :label="item" :value="item" />
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
            <h1 class="page-title">合成与验证</h1>
            <p class="page-subtitle">
              跟踪算法挑选序列的合成到货，以及流式结合与亲和力实验验证进度。
            </p>
          </div>
        </div>
        <div class="console-actions">
          <button
            type="button"
            class="ready-summary"
            :class="{ 'is-active': Boolean(listQuery.quick_filter) }"
            :aria-pressed="Boolean(listQuery.quick_filter)"
            :title="quickFilterTitle"
            @click="toggleQuickFilter('unassigned')"
            @contextmenu.prevent="toggleQuickFilter('has_issue')"
          >
            <span class="ready-dot" />
            <span v-if="listQuery.quick_filter === 'has_issue'">
              <strong>{{ stats.has_issue }}</strong> 个批次有检测说明或异常
            </span>
            <span v-else>
              <strong>{{ stats.unassigned }}</strong> 个批次无人问津待认领
            </span>
          </button>
          <el-button
            v-if="canFullEdit"
            :loading="syncingNow"
            :icon="Refresh"
            title="按工单批次、送测转码或订单号向 One 系统拉取更新合成与到货信息"
            @click="handleSyncNow"
          >
            同步One数据
          </el-button>
          <el-button v-if="canCreate" type="primary" @click="handleCreate">
            新建工单
          </el-button>
        </div>
      </header>

      <nav class="lifecycle-nav" aria-label="合成进度视图">
        <button
          v-for="item in statusViews"
          :key="item.key || 'all'"
          type="button"
          class="lifecycle-item"
          :class="[`stage-${item.tone}`, { 'is-active': activeViewGroup === item.key }]"
          :aria-pressed="activeViewGroup === item.key"
          :title="item.hint"
          @click="handleViewGroup(item.key)"
        >
          <span class="stage-marker">{{ item.step }}</span>
          <span class="stage-copy">
            <strong>{{ item.label }}</strong>
            <small>{{ item.hint }}</small>
          </span>
          <span class="stage-count">{{ stats[item.valueKey] || 0 }}</span>
        </button>
      </nav>
    </section>

    <div class="filter-panel">
      <div class="data-toolbar list-filter-controls">
        <div class="filter-strip">
          <el-input
            v-model="listQuery.batch_label"
            class="filter-select"
            placeholder="工单批次"
            title="多个工单批次用逗号、空格或换行分隔，按完整批次查找；只填一个时按包含查找"
            clearable
            @keyup.enter="handleFilter"
            @clear="handleFilter"
          />
          <el-input
            v-model="listQuery.synthesis_code"
            class="filter-select"
            placeholder="送测转码"
            title="多个送测转码用逗号、空格或换行分隔，按完整转码查找；只填一个时按包含查找"
            clearable
            @keyup.enter="handleFilter"
            @clear="handleFilter"
          />
          <el-input
            v-model="listQuery.order_no"
            class="filter-select"
            placeholder="订单号"
            title="多个订单号用逗号、空格或换行分隔，按完整单号查找；只填一个时按包含查找"
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
              <span v-if="targetOptionExtra(item)" class="target-option-code">
                {{ targetOptionExtra(item) }}
              </span>
            </el-option>
          </ListFilterSelect>
          <ListFilterSelect
            v-model="listQuery.mouse_strain"
            placeholder="小鼠品系"
            clearable
            class="filter-select"
            @change="handleFilter"
          >
            <el-option v-for="item in mouseStrainOptions" :key="item" :label="item" :value="item" />
          </ListFilterSelect>
          <div class="filter-select">
            <SerumUserSelect
              v-model="listQuery.owner"
              multi-gesture
              :options="optionLists.owners"
              placeholder="负责人"
              title="左键单选，右键追加"
              clearable
              @change="handleFilter"
            />
          </div>
          <ListFilterSelect
            v-model="listQuery.status"
            placeholder="状态"
            clearable
            class="filter-select"
            @change="handleFilter"
          >
            <el-option v-for="item in statusOptions" :key="item" :label="item" :value="item" />
          </ListFilterSelect>
          <el-date-picker
            v-model="syntheticDateRange"
            class="harvest-range"
            type="daterange"
            range-separator="至"
            start-placeholder="合成起始"
            end-placeholder="合成截止"
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
          <el-button
            class="list-filter-action-button"
            type="primary"
            title="右键清空筛选"
            @click="handleFilter"
            @contextmenu.prevent="resetFilters"
          >
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
          storage-key="discoverySynthesisViewPrefs.v3"
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
            <WorkbenchInlineSelect
              v-if="canEditField(row, 'priority')"
              v-model="row.priority"
              :options="priorityOptions"
              class="inline-select priority-select"
              :class="'status-tone-' + priorityTone(row)"
              @change="persistRow(row, 'priority')"
            />
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
              :value="row.status || '待下单'"
              :options="statusOptions"
              :type="statusTone(row.status)"
              :editable="canEditField(row, 'status')"
              @change="(val) => updateOrderStatus(row, val)"
            />
          </template>
          <template #target_name="{ row }">
            <span>{{ row.target_name || '' }}</span>
            <span v-if="targetCornerBadges(row).length" class="target-corner-badges">
              <i
                v-for="badge in targetCornerBadges(row)"
                :key="badge.text"
                class="target-corner-badge"
                :class="badge.cls"
                :title="badge.title"
              >{{ badge.text }}</i>
            </span>
          </template>
          <template #mouse_strain="{ row }">
            {{ displayCsvField(row.mouse_strain) }}
          </template>
          <template #eng_type="{ row }">
            {{ displayCsvField(row.eng_type) }}
          </template>
          <template #eng_method="{ row }">
            {{ displayCsvField(row.eng_method) }}
          </template>
          <template #target_codes="{ row }">
            {{ formatCodesText(row.target_codes) }}
          </template>
          <template #header-synthetic_date>
            <button
              type="button"
              class="sort-header-btn"
              :class="{ 'is-active': listQuery.sort_field === 'synthetic_date' }"
              :title="dateSortTitle('synthetic_date')"
              @click.stop="cycleDateSort('synthetic_date')"
            >
              合成日期{{ dateSortMark('synthetic_date') }}
            </button>
          </template>
          <template #header-arrival_date>
            <button
              type="button"
              class="sort-header-btn"
              :class="{ 'is-active': listQuery.sort_field === 'arrival_date' }"
              :title="dateSortTitle('arrival_date')"
              @click.stop="cycleDateSort('arrival_date')"
            >
              到货日期{{ dateSortMark('arrival_date') }}
            </button>
          </template>
          <template #header-flow_date>
            <button
              type="button"
              class="sort-header-btn"
              :class="{ 'is-active': listQuery.sort_field === 'flow_date' }"
              :title="dateSortTitle('flow_date')"
              @click.stop="cycleDateSort('flow_date')"
            >
              流式日期{{ dateSortMark('flow_date') }}
            </button>
          </template>
          <template #header-affinity_date>
            <button
              type="button"
              class="sort-header-btn"
              :class="{ 'is-active': listQuery.sort_field === 'affinity_date' }"
              :title="dateSortTitle('affinity_date')"
              @click.stop="cycleDateSort('affinity_date')"
            >
              亲和力日期{{ dateSortMark('affinity_date') }}
            </button>
          </template>
          <template #actions="{ row }">
            <SynthesisRowActions
              :row="row"
              :can-claim="canClaim"
              :can-delete="canDeleteRow(row)"
              @detail="openSerumProject"
              @claim="handleClaim"
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
              :row-config="sheetRowConfig"
              :cell-config="sheetCellConfig"
              :column-config="sheetColumnConfig"
              :mouse-config="sheetMouseConfig"
              :keyboard-config="sheetKeyboardConfig"
              :virtual-y-config="sheetVirtualYConfig"
              :virtual-x-config="sheetVirtualXConfig"
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
                  :edit-render="sheetCustomEditRender"
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
                        :popup-config="sheetTargetPopupConfig"
                        :remote-config="sheetTargetRemoteConfig"
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
                  :edit-render="sheetCustomEditRender"
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
                        v-model="row[column.key]"
                        class-name="sheet-grid-editor sheet-picker-control"
                        :filterable="isUserColumn(column)"
                        :options="sheetChoiceSelectOptions(column)"
                        :popup-config="sheetChoicePopupConfig"
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
                  <SynthesisRowActions
                    :row="row"
                    :can-claim="canClaim"
                    :can-delete="canDeleteRow(row)"
                    @detail="openSerumProject"
                    @claim="handleClaim"
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
      size="540px"
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
          <SynthesisRowActions
            :row="editingRow"
            :can-claim="canClaim"
            :can-delete="canDeleteRow(editingRow)"
            @detail="openSerumProject"
            @claim="handleClaim"
            @delete="handleDelete"
          />
          <el-button
            v-if="canCreate"
            class="list-table-action-btn"
            type="primary"
            plain
            :icon="CopyDocument"
            title="复制当前工单的基础与改造需求信息，新建一笔合成单（若同转码在 One 库有未关联新单将自动拉取）"
            @click="handleDuplicateTask(editingRow)"
          >
            加单
          </el-button>
          <el-button
            v-if="editingRow.has_drift && canFullEdit"
            class="list-table-action-btn"
            type="warning"
            plain
            @click="handleAdoptAll(editingRow)"
          >
            全部采用 ({{ editingRow.drift_fields?.length || 0 }})
          </el-button>
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
        <el-form label-width="82px" size="small" class="drawer-form" @submit.prevent>
          <article
            v-for="section in activeEditorSections"
            :key="section.title"
            class="drawer-card"
            :class="{ 'is-queue': section.queue, 'is-eng-section': section.engineering }"
          >
            <h3 class="drawer-card-title">{{ section.title }}</h3>
            <div class="drawer-card-grid">
              <el-form-item
                v-for="field in section.fields"
                :key="field.key"
                :label="field.label"
                :class="['drawer-field', field.wide ? 'is-wide' : '']"
              >
                <div class="drawer-field-stack">
                  <el-date-picker
                    v-if="field.type === 'date'"
                    v-model="editingRow[field.key]"
                    type="date"
                    value-format="YYYY-MM-DD"
                    format="YYYY-MM-DD"
                    placeholder="选择日期"
                    style="width: 100%;"
                    :disabled="!canEditField(editingRow, field.key)"
                    @change="persistRow(editingRow, field.key)"
                  />
                  <WorkbenchTargetSelect
                    v-else-if="field.type === 'target'"
                    v-model="editingRow.target_codes"
                    :display-name="editingRow.target_name"
                    :placeholder="editingRow.target_name ? '' : '搜索靶点'"
                    :disabled="!canEditField(editingRow, field.key)"
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
                    :disabled="!canEditField(editingRow, field.key)"
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
                    :disabled="!canEditField(editingRow, field.key)"
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
                    v-else-if="field.type === 'select' || field.type === 'corp_select'"
                    v-model="editingRow[field.key]"
                    class="drawer-select"
                    :class="drawerSelectClass(field)"
                    :clearable="
                      field.key !== 'status' &&
                      field.key !== 'priority' &&
                      field.key !== 'order_kind' &&
                      field.key !== 'supply_mode'
                    "
                    :filterable="field.type !== 'select'"
                    :allow-create="field.type !== 'select'"
                    default-first-option
                    style="width: 100%;"
                    :disabled="!canEditField(editingRow, field.key)"
                    @change="persistRow(editingRow, field.key)"
                  >
                    <el-option
                      v-for="item in fieldOptions(field)"
                      :key="item"
                      :label="item"
                      :value="item"
                    />
                  </el-select>
                  <el-input
                    v-else-if="field.type === 'textarea'"
                    v-model="editingRow[field.key]"
                    type="textarea"
                    :autosize="{ minRows: 1, maxRows: 4 }"
                    :disabled="!canEditField(editingRow, field.key)"
                    @blur="persistRow(editingRow, field.key)"
                  />
                  <span v-else-if="field.key === 'sort_order' && isQueueTerminalRow(editingRow)">-</span>
                  <el-autocomplete
                    v-else-if="isCodeField(field.key)"
                    v-model="editingRow[field.key]"
                    style="width: 100%;"
                    :debounce="0"
                    :disabled="!canEditField(editingRow, field.key)"
                    :fetch-suggestions="(q, cb) => fetchCodeSuggestions(field.key, q, cb)"
                    @select="persistRow(editingRow, field.key)"
                    @blur="persistRow(editingRow, field.key)"
                  >
                    <template #default="{ item }">
                      <div class="code-suggest-row">
                        <span class="code-suggest-val">{{ item.value }}</span>
                        <span v-if="item.hint" class="code-suggest-hint">{{ item.hint }}</span>
                      </div>
                    </template>
                  </el-autocomplete>
                  <el-input
                    v-else
                    v-model="editingRow[field.key]"
                    :type="field.type === 'number' ? 'number' : 'text'"
                    :min="field.key === 'sort_order' ? 1 : (field.type === 'number' ? 0 : undefined)"
                    :disabled="!canEditField(editingRow, field.key)"
                    @blur="persistRow(editingRow, field.key)"
                  />

                  <div
                    v-if="fieldDrift(editingRow, field.key)"
                    class="drift-banner"
                    :title="`来源最新：${fieldDrift(editingRow, field.key).remote}（右键复制）`"
                    @contextmenu.prevent="copyBannerCode(fieldDrift(editingRow, field.key).remote)"
                  >
                    <span class="drift-banner-text">
                      来源最新：<strong>{{ fieldDrift(editingRow, field.key).remote }}</strong>
                    </span>
                    <button
                      v-if="canFullEdit"
                      type="button"
                      class="drift-adopt-btn"
                      @click="handleAdoptField(editingRow, field.key)"
                    >
                      采用
                    </button>
                  </div>
                  <div
                    v-if="fieldDuplicateWarning(editingRow, field.key)"
                    class="drift-banner"
                    :title="`${fieldDuplicateWarning(editingRow, field.key)}（右键复制编号）`"
                    @contextmenu.prevent="copyDuplicateCode(editingRow, field.key)"
                  >
                    <span class="drift-banner-text">
                      {{ fieldDuplicateWarning(editingRow, field.key) }}
                    </span>
                  </div>
                </div>
              </el-form-item>
            </div>
          </article>
        </el-form>
      </fieldset>
    </el-drawer>
  </div>
</template>

<script>
import {
  CopyDocument,
  Download,
  Refresh,
  Search,
  Tools,
} from '@element-plus/icons-vue'
import {
  ElAutocomplete,
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
import ListFilterSelect from '#/components/ListFilterSelect.vue'
import {
  cleanFieldText,
  coerceOptionalNonnegInt,
  coerceRequiredPositiveInt,
  coerceWorkbenchViewMode,
  EXCEL_VIEW,
  readClipboardGrid,
  searchWorkbenchTargets,
  splitTargetNames,
  syncDrawerControlTooltip,
  targetNameFromCodes,
  uniqueTargetCodes,
  WORKBENCH_VIEW,
  WorkbenchDataTable,
  WorkbenchInlineSelect,
  workbenchExcelMixin,
} from '#/components/workbench'
import WorkbenchStatusEditor from '#/components/workbench/WorkbenchStatusEditor.vue'
import WorkbenchTargetSelect from '#/components/workbench/WorkbenchTargetSelect.vue'
import WorkbenchViewToggle from '#/components/workbench/WorkbenchViewToggle.vue'
import {
  adoptDiscoverySynthesisSource,
  checkRemoteDiscoverySynthesis,
  claimDiscoverySynthesis,
  deleteDiscoverySynthesis,
  exportDiscoverySynthesisList,
  fetchDiscoverySynthesisList,
  fetchDiscoverySynthesisOptions,
  reorderDiscoverySynthesis,
  saveDiscoverySynthesis,
  saveDiscoverySynthesisBatch,
  syncDiscoverySynthesisOrdersNow,
} from '#/api/discoverySynthesis'
import { notifyApiError } from '#/api/errors'
import { skipGlobalErrorHandler } from '#/api/request'
import { fetchSerumDetailByExperimentId } from '#/api/serum'
import {
  canEditDiscoverySynthesis,
  canPmEditDiscoverySynthesis,
} from '#/utils/discoveryPermission'
import { downloadListExcel, excelTimestamp } from '#/utils/downloadExcel'
import { listTableLockMixin } from '#/utils/listTableLock'
import { canAccessSerumDetail } from '#/utils/serumPermission'
import {
  canonicalizeWorkbenchPriority,
  getTiterPriorityTone,
} from '#/utils/serumProjectStatus'
import { loadSerumUserOptions, uniqueNames } from '#/utils/serumUserOptions'
import { shouldRefreshTabData } from '#/utils/staleTabRefresh'
import {
  filterTargetOptions,
  normalizeTargetOptions,
  targetOptionExtra as targetOptionHint,
} from '#/utils/targetFilterOptions'
import SerumUserSelect from '../../Serum/shared/SerumUserSelect.vue'
import SynthesisRowActions from './SynthesisRowActions.vue'
import {
  BASE_EDITOR_SECTIONS,
  BREAK_FIELDS,
  CSV_FIELD_OPTIONS,
  DATE_KEYS,
  DEFAULT_CORP_OPTIONS,
  DEFAULT_ENG_METHOD_OPTIONS,
  DEFAULT_ENG_TYPE_OPTIONS,
  EDITABLE_FIELDS,
  ENGINEERING_EDITOR_SECTION,
  INT_COUNT_KEYS,
  MOUSE_STRAIN_OPTIONS,
  ORDER_KIND_OPTIONS,
  PM_EDIT_FIELD_KEYS,
  PRIORITY_OPTIONS,
  QUEUE_KEYS,
  QUEUE_TERMINAL_STATUSES,
  SHEET_COLUMN_ORDER,
  SHEET_COLUMNS,
  SHEET_HEADER_ALIASES,
  STATUS_OPTIONS,
  STATUS_VIEWS,
  STRING_MAX,
  STUDY_TYPE_OPTIONS,
  SUPPLY_MODE_OPTIONS,
  USER_OPTION_LIST,
  WORKBENCH_COLUMNS,
} from './synthesisColumns'

let lastViewMode = WORKBENCH_VIEW

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

function joinCsvField(options, value) {
  const tokens = splitCategories(value)
  if (!tokens.length) return null
  const known = new Set(options || [])
  const present = new Set(tokens)
  const ordered = (options || []).filter((item) => present.has(item))
  const extras = tokens.filter((item) => !known.has(item))
  return [...ordered, ...extras].join('、') || null
}

function emptyQuery() {
  return {
    page: 1,
    limit: 20,
    keyword: '',
    order_no: '',
    synthesis_code: '',
    target_name: '',
    mouse_strain: '',
    owner: '',
    pm: '',
    status: '',
    priority: '',
    order_kind: '',
    supply_mode: '',
    synthetic_corp: '',
    study_type: '',
    project_code: '',
    eng_type: '',
    eng_method: '',
    batch_label: '',
    assay_note: '',
    remark: '',
    view_group: '',
    quick_filter: '',
    sort_field: '',
    sort_dir: '',
  }
}

export default {
  name: 'DiscoverySynthesisProgress',
  mixins: [workbenchExcelMixin, listTableLockMixin],
  components: {
    AdvancedOpsBar,
    ElAutocomplete,
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
    ListFilterSelect,
    Search,
    SerumUserSelect,
    SynthesisRowActions,
    Tools,
    VxeColumn,
    VxeInput,
    VxeSelect,
    VxeTable,
    WorkbenchDataTable,
    WorkbenchInlineSelect,
    WorkbenchStatusEditor,
    WorkbenchTargetSelect,
    WorkbenchViewToggle,
  },
  setup() {
    const userStore = useUserStore()
    return { CopyDocument, Download, Refresh, userStore }
  },
  data() {
    return {
      loading: false,
      syncingNow: false,
      list: [],
      total: 0,
      stats: {
        all: 0,
        wait_order: 0,
        synthesizing: 0,
        assay: 0,
        completed: 0,
        engineering: 0,
        cancelled: 0,
        unassigned: 0,
        has_issue: 0,
      },
      viewMode: coerceWorkbenchViewMode(lastViewMode),
      showAdvancedOps: false,
      drawerVisible: false,
      editingId: null,
      editingRowData: null,
      syntheticDateRange: [],
      arrivalDateRange: [],
      flowDateRange: [],
      affinityDateRange: [],
      listQuery: emptyQuery(),
      optionLists: {
        targets: [],
        owners: [],
        pms: [],
        synthetic_corps: [...DEFAULT_CORP_OPTIONS],
        eng_types: [...DEFAULT_ENG_TYPE_OPTIONS],
        eng_methods: [...DEFAULT_ENG_METHOD_OPTIONS],
      },
      statusOptions: [...STATUS_OPTIONS],
      priorityOptions: [...PRIORITY_OPTIONS],
      orderKindOptions: [...ORDER_KIND_OPTIONS],
      supplyModeOptions: [...SUPPLY_MODE_OPTIONS],
      mouseStrainOptions: [...MOUSE_STRAIN_OPTIONS],
      studyTypeOptions: [...STUDY_TYPE_OPTIONS],
      statusViews: STATUS_VIEWS,
      sheetColumns: SHEET_COLUMN_ORDER.load(),
      workbenchColumns: WORKBENCH_COLUMNS,
      pendingDrawerSaves: new Set(),
      rowBaselines: new Map(),
      remoteDuplicatesById: {},
      remoteCandidatesById: {},
      listRequestToken: 0,
      listLoaded: false,
      tabDataFetchedAt: 0,
      allUserOptions: [],
      targetOptions: [],
      targetRequestToken: 0,
      targetFilterQuery: '',
    }
  },
  computed: {
    canFullEdit() {
      return canEditDiscoverySynthesis(this.userStore.userInfo || {})
    },
    canPmEdit() {
      return canPmEditDiscoverySynthesis(this.userStore.userInfo || {})
    },
    canEdit() {
      return this.canFullEdit || this.canPmEdit
    },
    canCreate() {
      return this.canFullEdit || this.canPmEdit
    },
    canClaim() {
      return this.canFullEdit || this.canPmEdit
    },
    canViewSerumProject() {
      return canAccessSerumDetail(this.userStore.userInfo || {})
    },
    activeViewGroup() {
      return this.listQuery.view_group || ''
    },
    quickFilterTitle() {
      if (this.listQuery.quick_filter === 'has_issue') {
        return '当前只看填写了检测说明或异常的批次。右键取消；左键改看无人问津待认领。'
      }
      if (this.listQuery.quick_filter === 'unassigned') {
        return '当前只看未完成且负责人为空或无人问津的批次。再点取消；右键改看有检测说明或异常的批次。'
      }
      return '左键只看无人问津待认领；右键只看有检测说明或异常的批次。'
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
    activeEditorSections() {
      if (this.editingRow?.order_kind === '改造') {
        return [
          BASE_EDITOR_SECTIONS[0],
          ENGINEERING_EDITOR_SECTION,
          ...BASE_EDITOR_SECTIONS.slice(1),
        ]
      }
      return BASE_EDITOR_SECTIONS
    },
    drawerTitle() {
      const row = this.editingRow
      if (!row) return '工单详情'
      const target = String(row.target_name || '').trim()
      const orderNo = String(row.order_no || '').trim()
      const synCode = String(row.synthesis_code || '').trim()
      if (target && orderNo) return `${target} · ${orderNo}`
      return target || orderNo || synCode || '工单详情'
    },
    drawerMeta() {
      const row = this.editingRow
      if (!row) return ''
      return [
        row.synthesis_order_id,
        row.synthesis_code,
        this.formatCodesText(row.target_codes),
        this.editingIndex < 0 ? '当前筛选结果外' : '',
      ]
        .filter(Boolean)
        .join(' · ')
    },
    hasAdvancedFilters() {
      return Boolean(
        this.listQuery.project_code ||
          this.listQuery.pm ||
          this.listQuery.study_type ||
          this.listQuery.priority ||
          this.listQuery.order_kind ||
          this.listQuery.supply_mode ||
          this.listQuery.synthetic_corp ||
          this.listQuery.eng_type ||
          this.listQuery.eng_method ||
          this.listQuery.assay_note ||
          this.listQuery.remark ||
          this.arrivalDateRange?.length ||
          this.flowDateRange?.length ||
          this.affinityDateRange?.length,
      )
    },
    hasSecondaryFilters() {
      return Boolean(
        this.listQuery.keyword ||
          this.listQuery.batch_label ||
          this.listQuery.order_no ||
          this.listQuery.synthesis_code ||
          this.listQuery.target_name ||
          this.listQuery.mouse_strain ||
          this.listQuery.owner ||
          this.listQuery.status ||
          this.syntheticDateRange?.length ||
          this.hasAdvancedFilters,
      )
    },
    sheetTargetSelectOptions() {
      return this.targetOptions.map((item) => ({
        label: `${item.name}（${item.snum}）`,
        value: item.snum,
      }))
    },
    sheetTargetRemoteConfig() {
      return Object.freeze({
        autoLoad: true,
        queryMethod: this.querySheetTargetOptions,
      })
    },
    sheetChoiceOptionsMap() {
      const map = Object.create(null)
      map.priority = this.priorityOptions.map((item) => ({ label: item, value: item }))
      map.status = this.statusOptions.map((item) => ({ label: item, value: item }))
      map.order_kind = this.orderKindOptions.map((item) => ({ label: item, value: item }))
      map.supply_mode = this.supplyModeOptions.map((item) => ({ label: item, value: item }))
      map.study_type = this.studyTypeOptions.map((item) => ({ label: item, value: item }))
      map.synthetic_corp = (this.optionLists.synthetic_corps || []).map((item) => ({
        label: item,
        value: item,
      }))
      for (const [key, listKey] of Object.entries(USER_OPTION_LIST)) {
        map[key] = this.uniq([
          ...(this.optionLists[listKey] || []),
          ...this.allUserOptions,
        ]).map((item) => ({ label: item, value: item }))
      }
      return map
    },
  },
  created() {
    this.loading = true
    this.loadOptions()
    this.getList().finally(() => {
      this.listLoaded = true
    })
    if (this.isExcelMode) this.loadAllUserOptions()
  },
  mounted() {
    document.addEventListener('mousedown', this.onDocumentPointerDown, true)
    this.scheduleSortable()
  },
  beforeUnmount() {
    document.removeEventListener('mousedown', this.onDocumentPointerDown, true)
  },
  activated() {
    document.addEventListener('mousedown', this.onDocumentPointerDown, true)
    if (this.listLoaded && shouldRefreshTabData(this.tabDataFetchedAt)) {
      this.getList()
    } else {
      this.scheduleSortable()
    }
  },
  deactivated() {
    this.closeEditor()
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
      if (!open && this.editingId) {
        this.rememberDrawerSave(this.flushDirtyEditor())
        this.editingId = null
        this.editingRowData = null
      }
    },
  },
  methods: {
    splitCsv,
    splitCategories,
    displayCsvField,
    syncDrawerControlTooltip,
    uniq(values) {
      return uniqueNames(values)
    },
    normalizeRow(row) {
      const next = { ...row }
      next.target_codes = Array.isArray(next.target_codes)
        ? next.target_codes
        : splitCsv(next.target_codes)
      next.status = next.status || '待下单'
      next.priority = canonicalizeWorkbenchPriority(next.priority)
      next.order_kind = next.order_kind || '常规合成'
      next.supply_mode = next.supply_mode || '合成到货'
      next.drift_fields = Array.isArray(next.drift_fields) ? next.drift_fields : []
      next.has_drift = Boolean(next.drift_fields.length)
      return next
    },
    comparableValue(field, value) {
      if (field === 'target_codes') {
        return splitCsv(Array.isArray(value) ? value.join(',') : value).join(',')
      }
      if (INT_COUNT_KEYS.includes(field) || field === 'sort_order') {
        return value === null || value === undefined || value === '' ? '' : String(value)
      }
      return String(value ?? '')
    },
    sameSheetValue(key, left, right) {
      if (key === 'target_codes') {
        return this.comparableValue('target_codes', left) === this.comparableValue('target_codes', right)
      }
      return String(left ?? '').trim() === String(right ?? '').trim()
    },
    fieldComparable(row, field) {
      if (!row) return ''
      if (field === 'target_codes') return this.comparableValue(field, row.target_codes)
      return this.comparableValue(field, row[field])
    },
    payloadRow(row, fields) {
      const payload = { id: row.id }
      const list = [...fields]
      if (list.includes('target_codes') && !list.includes('target_name')) list.push('target_name')
      if (list.includes('target_name') && !list.includes('target_codes')) list.push('target_codes')
      list.forEach((field) => {
        if (field === 'synthesis_order_id') return
        if (field === 'target_codes') {
          payload.target_codes = uniqueTargetCodes(row.target_codes)
        } else if (INT_COUNT_KEYS.includes(field)) {
          payload[field] = row[field] === '' || row[field] == null ? null : row[field]
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
      if (keys.has('order_kind')) {
        keys.add('owner')
        keys.add('pm')
      }
      if (keys.has('order_no') || keys.has('synthesis_code') || keys.has('batch_label')) {
        keys.add('source_one_id')
        keys.add('source_one_type')
        keys.add('order_no')
        keys.add('synthesis_code')
        keys.add('batch_label')
      }
      keys.add('status')
      keys.add('sort_order')
      keys.add('drift_fields')
      keys.add('has_drift')
      return keys
    },
    syncDrawerFromSaved(normalized, fields) {
      if (this.editingId !== normalized?.id || !this.editingRowData) return
      const dirty = new Set(this.drawerDirtyFields(this.editingRowData))
      const keys = fields ? this.savedFieldKeys(fields) : Object.keys(normalized)
      keys.forEach((key) => {
        if (key === 'id' || !(key in normalized)) return
        if (key === 'target_codes' && dirty.has('target_codes')) return
        if (dirty.has(key)) return
        this.editingRowData[key] = normalized[key]
      })
    },
    applySavedFields(saved, fields) {
      const { normalized } = this.patchExistingListRow(saved, fields)
      this.syncDrawerFromSaved(normalized, fields)
      this.updateRowBaseline(normalized)
    },
    canEditField(row, fieldKey) {
      if (fieldKey === 'synthesis_order_id') {
        return false
      }
      if (fieldKey === 'sort_order' && this.isQueueTerminalRow(row)) {
        return false
      }
      if (this.canFullEdit) return true
      return this.canPmEdit && PM_EDIT_FIELD_KEYS.has(fieldKey)
    },
    canDeleteRow(row) {
      if (this.canFullEdit) return true
      return this.canPmEdit && String(row?.status || '').trim() === '待下单'
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
      if (!(await this.flushEditorForAction(row))) return
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
    async handleClaim(row) {
      if (!this.canClaim) {
        ElMessage.warning('您没有权限认领合成结果')
        return
      }
      if (!row?.id) return
      if (!(await this.flushEditorForAction(row))) return
      try {
        const saved = await claimDiscoverySynthesis(row.id)
        this.applySavedFields(saved, ['owner'])
        ElMessage.success(`已认领：${saved?.owner || ''}`)
      } catch (error) {
        notifyApiError(error, { messages: { default: '认领失败' } })
      }
    },
    async persistRow(row, field) {
      if (!this.canEditField(row, field) || !row?.id) return
      if (typeof row[field] === 'string') {
        row[field] = cleanFieldText(row[field], {
          keepBreaks: BREAK_FIELDS.has(field),
        })
      }
      if (INT_COUNT_KEYS.includes(field) || field === 'sort_order') {
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
      if (baseline) {
        if (field === 'target_codes' || field === 'target_name') {
          baseline.target_codes = this.cloneSheetValue(row.target_codes)
          baseline.target_name = row.target_name
        } else {
          baseline[field] = this.cloneSheetValue(row[field])
        }
      }
      try {
        const saved = await saveDiscoverySynthesis(this.payloadRow(row, [field]))
        if (QUEUE_KEYS.includes(field)) {
          await this.getList({ flushEditor: false })
          return saved
        }
        this.applySavedFields(saved, [field])
        if (field === 'order_no' || field === 'synthesis_code' || field === 'batch_label') {
          this.scheduleRemoteCheck([saved], { triggerFields: [field] })
        }
        return saved
      } catch (error) {
        notifyApiError(error, { messages: { default: '保存失败' } })
        this.getList({ flushEditor: false })
        return null
      }
    },
    updateOrderStatus(row, value) {
      row.status = value
      return this.persistRow(row, 'status')
    },
    rowPriority(row) {
      return canonicalizeWorkbenchPriority(row?.priority)
    },
    priorityTone(row) {
      return getTiterPriorityTone(this.rowPriority(row))
    },
    statusTone(status) {
      const value = String(status || '').trim() || '待下单'
      if (value === '已取消') return 'info'
      if (value === '已完成') return 'success'
      if (value === '待检测' || value === '检测中') return 'warning'
      if (value === '合成中') return 'primary'
      return 'info'
    },
    drawerSelectClass(field) {
      if (field?.key === 'status') {
        return `status-select status-tone-${this.statusTone(this.editingRow?.status)}`
      }
      if (field?.key === 'priority') {
        return `priority-select status-tone-${this.priorityTone(this.editingRow)}`
      }
      return ''
    },
    fieldOptions(field) {
      if (field?.key === 'eng_type') return this.optionLists.eng_types
      if (field?.key === 'eng_method') return this.optionLists.eng_methods
      if (field?.options) return field.options
      if (field?.type === 'corp_select') return this.optionLists.synthetic_corps
      if (field?.key === 'status') return this.statusOptions
      if (field?.key === 'priority') return this.priorityOptions
      if (field?.key === 'order_kind') return this.orderKindOptions
      if (field?.key === 'supply_mode') return this.supplyModeOptions
      return []
    },
    usedUserOptions(field) {
      return this.uniq([
        ...(this.optionLists[USER_OPTION_LIST[field?.key]] || []),
        this.editingRow?.[field?.key],
      ])
    },
    fieldDrift(row, key) {
      return (row?.drift_fields || []).find((item) => item.field === key) || null
    },
    fieldDuplicateWarning(row, key) {
      if (!row?.id || !['order_no', 'batch_label', 'synthesis_code'].includes(key)) return ''
      if (key !== 'order_no' && row.source_one_id) return ''
      const val = String(row[key] || '').trim()
      if (!val) return ''
      const matches = this.remoteDuplicatesById[String(row.id)]?.[key]
      if (!matches?.length) return ''
      return `已存在：${matches.join('、')}`
    },
    copyDuplicateCode(row, key) {
      const matches = this.remoteDuplicatesById[String(row?.id)]?.[key]
      if (!matches?.length) return
      const codes = matches.map((item) => String(item || '').trim()).filter(Boolean)
      if (!codes.length) return
      const joined = codes.join('\n')
      const msg = codes.length > 1 ? `已复制 ${codes.length} 个编号（换行分隔）` : `已复制：${codes[0]}`
      this.copyBannerCode(joined, msg)
    },
    copyBannerCode(text, customMessage) {
      const val = String(text ?? '').trim()
      if (!val) return
      const onSuccess = () => ElMessage.success(customMessage || `已复制：${val}`)
      if (navigator.clipboard?.writeText) {
        navigator.clipboard
          .writeText(val)
          .then(onSuccess)
          .catch(() => this.fallbackCopyText(val, onSuccess))
        return
      }
      this.fallbackCopyText(val, onSuccess)
    },
    fallbackCopyText(val, onSuccess) {
      try {
        const input = document.createElement('textarea')
        input.value = val
        input.setAttribute('readonly', 'readonly')
        input.style.position = 'fixed'
        input.style.opacity = '0'
        document.body.appendChild(input)
        input.select()
        document.execCommand('copy')
        document.body.removeChild(input)
        onSuccess()
      } catch {
        ElMessage.warning('复制失败，请手动复制')
      }
    },
    isCodeField(key) {
      return key === 'order_no' || key === 'batch_label' || key === 'synthesis_code'
    },
    fetchCodeSuggestions(key, _query, cb) {
      const row = this.editingRow
      if (!row?.id) return cb([])
      const curVal = String(row[key] || '').trim().toUpperCase()
      const curBatch = String(row.batch_label || '').split('|')[0].trim().toUpperCase()
      const cands = [...(this.remoteCandidatesById[String(row.id)] || [])]
      if (key === 'order_no' && curBatch) {
        cands.sort((a, b) => {
          const aMatch = String(a.batch_label || '').toUpperCase() === curBatch ? 0 : 1
          const bMatch = String(b.batch_label || '').toUpperCase() === curBatch ? 0 : 1
          return aMatch - bMatch
        })
      }
      const seen = new Set()
      const list = []
      for (const cand of cands) {
        const val = String(cand[key] || '').trim()
        if (!val || val.toUpperCase() === curVal || seen.has(val.toUpperCase())) continue
        seen.add(val.toUpperCase())
        const hintParts = []
        if (key !== 'order_no' && cand.order_no) hintParts.push(cand.order_no)
        if (key !== 'batch_label' && cand.batch_label) hintParts.push(cand.batch_label)
        if (cand.synthetic_count) hintParts.push(`${cand.synthetic_count}个`)
        if (cand.synthetic_date) hintParts.push(cand.synthetic_date)
        list.push({ value: val, hint: hintParts.join(' · ') })
      }
      cb(list)
    },
    driftSummaryText(row) {
      return (row?.drift_fields || [])
        .map((item) => `${item.label}：${item.current} → ${item.remote}`)
        .join('\n')
    },
    async handleAdoptField(row, key) {
      if (!this.canFullEdit || !row?.id) return
      try {
        const saved = await adoptDiscoverySynthesisSource(row.id, [key])
        this.applySavedFields(saved)
        ElMessage.success('已采用来源最新值')
      } catch (error) {
        notifyApiError(error, { messages: { default: '采用失败' } })
      }
    },
    async handleAdoptAll(row) {
      if (!this.canFullEdit || !row?.id) return
      try {
        const saved = await adoptDiscoverySynthesisSource(row.id)
        this.applySavedFields(saved)
        ElMessage.success('已全部采用来源最新值')
      } catch (error) {
        notifyApiError(error, { messages: { default: '采用失败' } })
      }
    },
    async handleSyncNow() {
      if (!this.canFullEdit || this.syncingNow) return
      this.syncingNow = true
      try {
        const res = await syncDiscoverySynthesisOrdersNow()
        if (res?.skipped) {
          ElMessage.info(res.message || '未配置外部 One 库连接')
          return
        }
        const linked = Number(res?.linked || 0)
        const updated = Number(res?.updated || 0)
        ElMessage.success(`同步完成：新关联 ${linked} 条，更新 ${updated} 条`)
        if (linked > 0 || updated > 0) {
          await this.getList({ flushEditor: false, skipRemoteCheck: true })
        }
      } catch (error) {
        notifyApiError(error, { messages: { default: '同步 One 订单失败' } })
      } finally {
        this.syncingNow = false
      }
    },
    scheduleRemoteCheck(rows, { triggerFields } = {}) {
      const targetRows = (rows || []).filter(
        (row) =>
          row?.id &&
          (row.source_one_id || row.order_no || row.synthesis_code || row.batch_label),
      )
      const ids = targetRows.map((row) => row.id)
      if (!ids.length) return Promise.resolve(null)
      const listToken = this.listRequestToken
      return checkRemoteDiscoverySynthesis(ids)
        .then((res) => {
          if (listToken !== this.listRequestToken) return null
          if (res?.duplicates && typeof res.duplicates === 'object') {
            const nextDups = { ...this.remoteDuplicatesById }
            ids.forEach((id) => {
              delete nextDups[String(id)]
            })
            Object.assign(nextDups, res.duplicates)
            this.remoteDuplicatesById = nextDups
          }
          if (res?.candidates && typeof res.candidates === 'object' && ids.length === 1) {
            const singleKey = String(ids[0])
            this.remoteCandidatesById = {
              ...this.remoteCandidatesById,
              [singleKey]: res.candidates[singleKey] || [],
            }
          }
          const updated = res?.updated_items || []
          updated.forEach((saved) => {
            this.applySavedFields(saved)
          })
          if (!this.drawerVisible && triggerFields?.length && targetRows.length === 1) {
            const current = updated[0] || targetRows[0]
            for (const f of triggerFields) {
              const warn = this.fieldDuplicateWarning(current, f)
              if (warn) {
                ElMessage.warning(warn)
                break
              }
            }
          }
          return res
        })
        .catch(() => {
          /* Phase 2 remote check fails silently so Phase 1 UI stays smooth */
          return null
        })
    },
    buildQuery() {
      const payload = { ...this.listQuery }
      if (!payload.view_group) delete payload.view_group
      if (!payload.quick_filter) delete payload.quick_filter
      if (!payload.status) delete payload.status
      if (!payload.priority) delete payload.priority
      if (!payload.order_kind) delete payload.order_kind
      if (!payload.supply_mode) delete payload.supply_mode
      if (!payload.sort_field) delete payload.sort_field
      if (!payload.sort_dir) delete payload.sort_dir
      if (Array.isArray(this.syntheticDateRange) && this.syntheticDateRange.length === 2) {
        payload.synthetic_date_start = this.syntheticDateRange[0]
        payload.synthetic_date_end = this.syntheticDateRange[1]
      }
      if (Array.isArray(this.arrivalDateRange) && this.arrivalDateRange.length === 2) {
        payload.arrival_date_start = this.arrivalDateRange[0]
        payload.arrival_date_end = this.arrivalDateRange[1]
      }
      if (Array.isArray(this.flowDateRange) && this.flowDateRange.length === 2) {
        payload.flow_date_start = this.flowDateRange[0]
        payload.flow_date_end = this.flowDateRange[1]
      }
      if (Array.isArray(this.affinityDateRange) && this.affinityDateRange.length === 2) {
        payload.affinity_date_start = this.affinityDateRange[0]
        payload.affinity_date_end = this.affinityDateRange[1]
      }
      return payload
    },
    async loadOptions() {
      try {
        const data = await fetchDiscoverySynthesisOptions(skipGlobalErrorHandler)
        this.optionLists.targets = normalizeTargetOptions(data?.targets)
        this.optionLists.owners = this.uniq(data?.owners || [])
        this.optionLists.pms = this.uniq(data?.pms || [])
        if (Array.isArray(data?.synthetic_corps) && data.synthetic_corps.length) {
          this.optionLists.synthetic_corps = data.synthetic_corps
        }
        if (Array.isArray(data?.eng_types) && data.eng_types.length) {
          this.optionLists.eng_types = data.eng_types
        }
        if (Array.isArray(data?.eng_methods) && data.eng_methods.length) {
          this.optionLists.eng_methods = data.eng_methods
        }
      } catch (error) {
        notifyApiError(error, { messages: { default: '加载合成进度选项失败' } })
      }
    },
    async getList({ flushEditor = true, silent = false, skipRemoteCheck = false } = {}) {
      if (!silent) this.loading = true
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
        const data = await fetchDiscoverySynthesisList(this.buildQuery(), skipGlobalErrorHandler)
        if (requestToken !== this.listRequestToken) return
        this.list = (data?.items || []).map((row) => this.normalizeRow(row))
        this.list.forEach((row) => this.updateRowBaseline(row))
        this.total = data?.total || 0
        this.stats = {
          all: data?.stats?.all || 0,
          wait_order: data?.stats?.wait_order || 0,
          synthesizing: data?.stats?.synthesizing || 0,
          assay: data?.stats?.assay || 0,
          completed: data?.stats?.completed || 0,
          engineering: data?.stats?.engineering || 0,
          cancelled: data?.stats?.cancelled || 0,
          unassigned: data?.stats?.unassigned || 0,
          has_issue: data?.stats?.has_issue || 0,
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
        if (!skipRemoteCheck) {
          this.scheduleRemoteCheck(this.list)
        }
      } catch (error) {
        if (requestToken === this.listRequestToken) {
          notifyApiError(error, { messages: { default: '加载合成与验证列表失败' } })
        }
      } finally {
        if (requestToken === this.listRequestToken) this.loading = false
      }
    },
    handleFilter() {
      this.listQuery.page = 1
      this.getList()
    },
    handleViewGroup(key) {
      this.listQuery.view_group = key || ''
      this.handleFilter()
    },
    toggleQuickFilter(value) {
      this.listQuery.quick_filter = this.listQuery.quick_filter === value ? '' : value
      this.handleFilter()
    },
    resetFilters() {
      const viewGroup = this.listQuery.view_group
      const sortField = this.listQuery.sort_field
      const sortDir = this.listQuery.sort_dir
      this.listQuery = {
        ...emptyQuery(),
        view_group: viewGroup,
        sort_field: sortField,
        sort_dir: sortDir,
      }
      this.syntheticDateRange = []
      this.arrivalDateRange = []
      this.flowDateRange = []
      this.affinityDateRange = []
      this.getList()
    },
    excelHeaderClick(column) {
      if (!DATE_KEYS.includes(column?.key)) return false
      this.cycleDateSort(column.key)
      return true
    },
    async toggleViewMode() {
      if (this.isExcelMode && !(await this.flushPendingSheetEdits())) return
      this.viewMode = this.isExcelMode ? WORKBENCH_VIEW : EXCEL_VIEW
      if (this.isExcelMode) this.closeEditor()
    },
    async resetSheetColumnOrder() {
      if (this.isExcelMode) {
        if (!(await this.flushPendingSheetEdits())) return
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
    drawerDirtyFields(row) {
      const baseline = this.rowBaselines.get(row?.id)
      if (!row || !baseline) return []
      const dirty = []
      if (
        this.comparableValue('target_codes', row.target_codes) !==
        this.comparableValue('target_codes', baseline.target_codes)
      ) {
        dirty.push('target_codes')
      }
      EDITABLE_FIELDS.forEach((field) => {
        if (field === 'target_codes') return
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
      return saveDiscoverySynthesis(this.payloadRow(row, fields))
        .then((saved) => {
          this.applySavedFields(saved)
          const codeFields = fields.filter(
            (f) => f === 'order_no' || f === 'synthesis_code' || f === 'batch_label',
          )
          if (codeFields.length) {
            this.scheduleRemoteCheck([saved], { triggerFields: codeFields })
          }
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
      if (!(await this.flushPendingSheetEdits())) return false
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
      if (
        (row.synthesis_code || row.batch_label) &&
        !(String(row.id) in this.remoteCandidatesById)
      ) {
        this.scheduleRemoteCheck([this.editingRowData])
      }
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
    targetCornerBadges(row) {
      if (!row) return []
      const list = []
      if (row.order_kind === '改造') {
        list.push({ text: '改造', cls: 'is-eng', title: '序列改造批次' })
      }
      if (row.supply_mode === '内部转染') {
        list.push({ text: '转染', cls: 'is-internal', title: '供应方式：内部转染' })
      } else if (row.supply_mode === '改亚型') {
        list.push({ text: '亚型', cls: 'is-isotype', title: '供应方式：改亚型' })
      }
      if (row.has_drift) {
        list.push({ text: '变更', cls: 'is-drift', title: this.driftSummaryText(row) })
      }
      return list
    },
    workbenchRowClassName({ row }) {
      return row.id === this.editingId ? 'is-editing' : ''
    },
    onWorkbenchRowClick(row, _column, event) {
      if (
        event?.target?.closest?.(
          '.el-button, .el-input, .el-select, .el-date-editor, .action-cell, .sort-column-cell, .workbench-status-tag',
        )
      ) {
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
      if (
        target.closest(
          '.el-drawer, .el-popper, .el-select-dropdown, .el-picker-panel, .el-message-box, .el-overlay-message-box, .sheet-picker-popup',
        )
      ) {
        return
      }
      if (target.closest('.el-table__row, .vxe-body--row, .action-cell')) {
        return
      }
      this.closeEditor()
    },
    async handleCreate() {
      if (!this.canCreate) {
        ElMessage.warning('您没有权限新建合成与验证工单')
        return
      }
      if (!(await this.flushPendingSheetEdits())) return
      this.loading = true
      try {
        const defaultKind = this.listQuery.view_group === 'engineering' ? '改造' : '常规合成'
        const saved = await saveDiscoverySynthesis({ order_kind: defaultKind })
        await this.revealCreatedRow(saved)
      } catch (error) {
        notifyApiError(error, { messages: { default: '新建工单失败' } })
      } finally {
        this.loading = false
      }
    },
    async handleDuplicateTask(row) {
      if (!this.canCreate || !row?.id) return
      if (!(await this.flushEditorForAction(row))) return
      const source = this.editingRowData?.id === row.id ? this.editingRowData : row
      const baseKeys = [
        'priority',
        'order_kind',
        'owner',
        'pm',
        'project_code',
        'experiment_id',
        'study_type',
        'target_name',
        'target_codes',
        'mouse_strain',
        'eng_type',
        'eng_method',
        'eng_parent_seq',
        'eng_requirement',
        'remark',
      ]
      if (this.canFullEdit) {
        baseKeys.push('supply_mode', 'synthesis_code', 'batch_label')
      }
      const payload = {}
      baseKeys.forEach((key) => {
        const val = source[key]
        if (Array.isArray(val)) {
          if (val.length) payload[key] = [...val]
        } else if (val !== null && val !== undefined && String(val).trim() !== '') {
          payload[key] = val
        }
      })
      this.loading = true
      try {
        const saved = await saveDiscoverySynthesis(payload)
        let linkedOrderNo = ''
        if (saved?.id && (saved.synthesis_code || saved.batch_label)) {
          const checkRes = await this.scheduleRemoteCheck([saved])
          if (checkRes?.linked > 0 && checkRes.updated_items?.[0]?.order_no) {
            linkedOrderNo = checkRes.updated_items[0].order_no
          }
        }
        await this.revealCreatedRow(saved)
        if (linkedOrderNo) {
          ElMessage.success(`已加单，并自动关联下一笔订单：${linkedOrderNo}`)
        } else {
          ElMessage.success('已复制基础与改造信息生成新单，请填写新订单信息')
        }
      } catch (error) {
        notifyApiError(error, { messages: { default: '加单失败' } })
      } finally {
        this.loading = false
      }
    },
    async handleDelete(row) {
      if (!this.canDeleteRow(row)) {
        ElMessage.warning(
          this.canPmEdit ? 'PM 权限只能删除待下单状态的工单' : '您没有权限删除合成与验证工单',
        )
        return
      }
      const label = row.order_no || row.synthesis_code || row.target_name || `#${row.id}`
      try {
        await ElMessageBox.confirm(`确认删除订单 ${label}？删除后不可恢复。`, '删除确认', {
          type: 'warning',
          confirmButtonText: '删除',
          cancelButtonText: '取消',
        })
      } catch {
        return
      }
      if (!(await this.flushEditorForAction(row))) return
      try {
        await deleteDiscoverySynthesis(row.id)
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
          () => exportDiscoverySynthesisList(this.buildQuery()),
          `合成进度_${excelTimestamp()}.xlsx`,
        )
      } catch (error) {
        notifyApiError(error, { messages: { default: '列表导出失败' } })
      }
    },
    isUserColumn(column) {
      return Object.prototype.hasOwnProperty.call(USER_OPTION_LIST, column?.key)
    },
    isSheetChoiceColumn(column) {
      return column?.edit === 'multi' || column?.edit === 'select'
    },
    categorySheetSelect() {
      return document.querySelector('.sheet-category-select')?.__vueParentComponent?.proxy
    },
    isCsvField(key) {
      return Object.prototype.hasOwnProperty.call(CSV_FIELD_OPTIONS, key)
    },
    csvFieldOptions(key) {
      if (key === 'eng_type') return this.optionLists.eng_types || DEFAULT_ENG_TYPE_OPTIONS
      if (key === 'eng_method') return this.optionLists.eng_methods || DEFAULT_ENG_METHOD_OPTIONS
      return CSV_FIELD_OPTIONS[key] || []
    },
    extraCsvOptions(key, value) {
      const known = new Set(this.csvFieldOptions(key))
      return splitCategories(value).filter((item) => !known.has(item))
    },
    onCsvFieldChange(row, key, values) {
      row[key] = joinCsvField(this.csvFieldOptions(key), values)
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
      return key === 'target_codes' ? this.sheetDirectTextValue(row, key) : row.target_name
    },
    setSheetTargetDirectValue(row, key, value) {
      row[key] = value
    },
    sheetPickerDisplayValue(row, column) {
      if (column.key === 'target_codes') return this.formatCodesText(row.target_codes)
      if (column.key === 'target_name') return row.target_name || ''
      return row[column.key] ?? ''
    },
    sheetChoiceSelectOptions(column) {
      return this.sheetChoiceOptionsMap[column?.key] || []
    },
    sheetChoiceDirectValue(row, column) {
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
        ['target_codes', 'target_name'].includes(previousKey) &&
        ['target_codes', 'target_name'].includes(nextKey) &&
        this.pendingSheetOps.size
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
    formatCodes({ row }) {
      return this.formatCodesText(row.target_codes)
    },
    formatCsvCell({ cellValue }) {
      return displayCsvField(cellValue)
    },
    isSheetCellLocked(row, key) {
      if (!row?.id) return true
      if (key === 'sort_order' && !this.isQueueSorted) return true
      if (!this.canEditField(row, key)) return true
      const column = this.sheetColumnByKey.get(key)?.column
      return column?.edit === 'readonly'
    },
    sheetCellClassName({ row, column }) {
      const classes = []
      if (column?.field === 'priority') {
        classes.push(`sheet-tone-${this.priorityTone(row)}`)
      }
      if (column?.field === 'status') {
        classes.push(`sheet-tone-${this.statusTone(row?.status)}`)
      }
      return classes.join(' ')
    },
    sheetFormatter(column) {
      if (column.key === 'sort_order') return this.formatSortColumnCell
      if (this.isCsvField(column.key)) return this.formatCsvCell
      if (column.key === 'target_codes') return this.formatCodes
      return undefined
    },
    sheetDirectTextValue(row, key) {
      if (!row) return ''
      if (key === 'sort_order') return row.sort_order == null ? '' : String(row.sort_order)
      if (key === 'target_codes') {
        if (typeof row.target_codes === 'string' && this.sheetEditOriginal?.rowId === row.id && this.sheetEditOriginal?.key === key) {
          return row.target_codes
        }
        return this.formatCodesText(row.target_codes)
      }
      if (row[key] === null || row[key] === undefined) return ''
      return String(row[key])
    },
    sheetValueSnapshot(row, key) {
      if (!row) return null
      if (key === 'target_codes') return [...uniqueTargetCodes(row.target_codes)]
      return row[key]
    },
    restoreSheetEditValue(row, key, value) {
      if (key === 'target_codes') {
        row.target_codes = uniqueTargetCodes(value)
        return
      }
      row[key] = this.cloneSheetValue(value)
    },
    normalizeSheetDate(text) {
      const raw = String(text ?? '').trim()
      if (!raw) return { ok: true, value: null }
      const match = /^(\d{4})[./-]?(\d{1,2})[./-]?(\d{1,2})$/.exec(raw)
      if (!match) return { ok: false, reason: 'date' }
      const year = Number(match[1])
      const month = Number(match[2])
      const day = Number(match[3])
      const date = new Date(Date.UTC(year, month - 1, day))
      const valid =
        date.getUTCFullYear() === year &&
        date.getUTCMonth() === month - 1 &&
        date.getUTCDate() === day
      if (!valid) return { ok: false, reason: 'date' }
      const formatted = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
      return { ok: true, value: formatted }
    },
    matchSheetOption(options, text) {
      const hit = (options || []).find(
        (item) => item === text || String(item).toLowerCase() === text.toLowerCase(),
      )
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
        return PRIORITY_OPTIONS.includes(canon)
          ? { ok: true, value: canon }
          : { ok: false, reason: 'option' }
      }
      if (key === 'status') {
        const val = String(raw || '').trim()
        if (!val) return { ok: false, reason: 'option' }
        return this.matchSheetOption(this.statusOptions, val)
      }
      if (key === 'order_kind') {
        const val = String(raw || '').trim()
        if (!val) return { ok: false, reason: 'option' }
        return this.matchSheetOption(this.orderKindOptions, val)
      }
      if (key === 'supply_mode') {
        const val = String(raw || '').trim()
        if (!val) return { ok: false, reason: 'option' }
        return this.matchSheetOption(this.supplyModeOptions, val)
      }
      if (key === 'study_type') {
        const val = String(raw || '').trim()
        if (!val) return { ok: true, value: null }
        return this.matchSheetOption(this.studyTypeOptions, val)
      }
      if (this.isUserColumn({ key })) {
        const val = String(raw || '').trim()
        if (!val) return { ok: true, value: null }
        return this.matchSheetOption(
          this.uniq([...(this.optionLists[USER_OPTION_LIST[key]] || []), ...this.allUserOptions]),
          val,
        )
      }
      if (INT_COUNT_KEYS.includes(key)) {
        const cleaned = String(raw ?? '')
          .trim()
          .replace(/个|条/g, '')
          .trim()
        return coerceOptionalNonnegInt(cleaned)
      }
      if (DATE_KEYS.includes(key)) return this.normalizeSheetDate(raw)
      if (this.isCsvField(key)) {
        return { ok: true, value: joinCsvField(this.csvFieldOptions(key), raw) }
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
          this.sameSheetValue('target_codes', codes, originalCodes) &&
          this.sameSheetValue('target_name', submittedName, originalName)
        ) {
          return
        }
        try {
          const resolved = await this.resolveTargetCodes(codes)
          if (resolved.missing.length) throw new Error('target-missing')
          row.target_codes = codes
          row.target_name = resolved.names.join('&')
          return this.persistRow(row, 'target_codes')
        } catch {
          row.target_codes = this.cloneSheetValue(originalCodes)
          row.target_name = originalName
          ElMessage.warning('靶点校验失败，本次修改未保存')
        }
        return
      }
      const source = key === 'target_codes' ? row.target_codes : row[key]
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
            !this.sameSheetValue('target_codes', row.target_codes, submittedCodes) ||
            !this.sameSheetValue('target_name', row.target_name, submittedName)
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
            !this.sameSheetValue('target_codes', row.target_codes, submittedCodes) ||
            !this.sameSheetValue('target_name', row.target_name, submittedName)
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
            !this.sameSheetValue('target_name', row.target_name, submittedName) ||
            !this.sameSheetValue('target_codes', row.target_codes, submittedCodes)
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
            !this.sameSheetValue('target_name', row.target_name, submittedName) ||
            !this.sameSheetValue('target_codes', row.target_codes, submittedCodes)
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
      const singleValue =
        grid.length === 1 && grid[0].length === 1 && !String(grid[0][0]).includes('\n')
      if (!plain.includes('\t') && !plain.includes('\n') && singleValue && !this.sheetRange) return
      event.preventDefault()
      if (!(await this.flushPendingSheetEdits())) return

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
      const fillSelectedRange =
        !hasHeader &&
        dataRows.length === 1 &&
        dataRows[0]?.length === 1 &&
        selectedRange &&
        (selectedRange.r1 !== selectedRange.r2 || selectedRange.c1 !== selectedRange.c2)
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
          const key = hasHeader
            ? headerKeys[cellIndex]
            : this.sheetColumns[startColIndex + cellIndex]?.key
          if (!key) {
            if (String(cell ?? '').trim()) invalidCells.push({ reason: 'unknown' })
            return
          }
          if (
            key === 'sort_order' &&
            (cells.length > 1 || hasHeader) &&
            (this.isSheetCellLocked(row, key) || !String(cell ?? '').trim())
          ) {
            return
          }
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
        const message =
          firstInvalid.reason === 'unknown'
            ? '粘贴内容包含无法识别的列，本次粘贴未保存'
            : `${this.sheetValidationMessage(firstInvalid.key, firstInvalid.reason)}，本次粘贴未保存`
        ElMessage.warning(message)
        return
      }
      if (!dirtyByIndex.size) return

      const targetEntries = [...targetFieldsByIndex.entries()].map(([rowIndex, fields]) => ({
        fields,
        row: workingRows[rowIndex],
      }))
      if (targetEntries.length) {
        try {
          const codeEntries = targetEntries.filter(
            ({ fields, row }) =>
              fields.has('target_codes') &&
              ((row.target_codes || []).length > 0 ||
                !fields.has('target_name') ||
                !splitTargetNames(row.target_name).length),
          )
          const resolvedCodes = await this.resolveTargetCodes(
            codeEntries.flatMap(({ row }) => row.target_codes || []),
          )
          if (resolvedCodes.missing.length) {
            ElMessage.warning(`未找到靶点编号：${resolvedCodes.missing.join('、')}，本次粘贴未保存`)
            return
          }
          codeEntries.forEach(({ fields, row }) => {
            const canonicalNames = (row.target_codes || []).map((code) =>
              resolvedCodes.nameByCode.get(code),
            )
            if (fields.has('target_name')) {
              const submittedNames = splitTargetNames(row.target_name)
              if (submittedNames.length) {
                const matches =
                  submittedNames.length === canonicalNames.length &&
                  submittedNames.every(
                    (name, index) =>
                      name.toLowerCase() === String(canonicalNames[index] || '').toLowerCase(),
                  )
                if (!matches) throw new Error('target-mismatch')
              }
            }
            row.target_name = canonicalNames.join('&')
          })
          const nameOnlyEntries = targetEntries.filter(
            ({ fields, row }) =>
              fields.has('target_name') &&
              (!fields.has('target_codes') ||
                (!(row.target_codes || []).length && splitTargetNames(row.target_name).length > 0)),
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
            const targetItems = splitTargetNames(row.target_name).map((name) =>
              resolvedNames.itemByName.get(name.toLowerCase()),
            )
            row.target_codes = targetItems.map((item) => item.snum)
            row.target_name = targetItems.map((item) => item.name).join('&')
          })
        } catch {
          ElMessage.warning('靶点名称与编号不匹配或校验失败，本次粘贴未保存')
          return
        }
      }

      const items = [...dirtyByIndex.entries()].map(([rowIndex, fields]) =>
        this.payloadRow(workingRows[rowIndex], [...fields]),
      )
      try {
        const result = await saveDiscoverySynthesisBatch({ items })
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
    async handleDragEnd(event) {
      const { oldIndex, newIndex, item } = event
      this.revertDrag(item, oldIndex, newIndex)
      if (!this.canDragRows || oldIndex == null || newIndex == null || oldIndex === newIndex) return
      const payload = this.queueReorderPayload(oldIndex, newIndex)
      if (!payload) return
      this.loading = true
      try {
        await reorderDiscoverySynthesis(payload.movedId, payload.targetId)
        await this.getList({ flushEditor: false })
      } catch (error) {
        notifyApiError(error, { messages: { default: '调整排序失败' } })
        await this.getList({ flushEditor: false })
      } finally {
        this.loading = false
      }
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
.filter-select {
  flex: 1 1 100px;
  min-width: 100px;
}
.filter-strip :deep(.harvest-range) {
  flex: 1 1 140px;
  width: auto;
  min-width: 100px;
}
.table-card :deep(td.target-column-cell) {
  position: relative;
}
.table-card :deep(td.target-column-cell .cell) {
  position: static;
}
.target-corner-badges {
  position: absolute;
  top: 2px;
  right: 3px;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  pointer-events: none;
}
.target-corner-badge {
  padding: 0 3.5px;
  font-size: 10px;
  font-style: normal;
  font-weight: 500;
  line-height: 13px;
  white-space: nowrap;
  border-radius: 3px;
}
.target-corner-badge.is-eng {
  color: #6b21a8;
  background: #f5eeff;
  border: 1px solid #dfd0f7;
}
.target-corner-badge.is-internal {
  color: #0958d9;
  background: #edf5ff;
  border: 1px solid #c9e0ff;
}
.target-corner-badge.is-isotype {
  color: #006d75;
  background: #e6fffb;
  border: 1px solid #b5f5ec;
}
.target-corner-badge.is-drift {
  color: #d46b08;
  background: #fff7e6;
  border: 1px solid #ffd591;
}
.drawer-card.is-eng-section {
  padding: 8px 10px 4px;
  margin-bottom: 8px;
  background: #faf6ff;
  border: 1px solid #eadcff;
  border-radius: var(--list-mid-radius);
}
.drawer-card.is-eng-section .drawer-card-title {
  color: #722ed1;
}
.drawer-field-stack {
  display: flex;
  flex-direction: column;
  width: 100%;
  min-width: 0;
}
.drift-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  margin-top: 3px;
  padding: 2px 7px;
  border-radius: 5px;
  background: #fff4e5;
  color: #b76e00;
  font-size: 11.5px;
  line-height: 18px;
}
.drift-banner-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.drift-adopt-btn {
  padding: 1px 8px;
  border: 1px solid #f59e0b;
  border-radius: 4px;
  background: #fff;
  color: #b76e00;
  font-size: 11px;
  cursor: pointer;
  flex-shrink: 0;
}
.drift-adopt-btn:hover {
  background: #fef3c7;
}
.code-suggest-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 12px;
}
.code-suggest-val {
  color: var(--el-text-color-primary);
  font-weight: 500;
}
.code-suggest-hint {
  color: var(--el-text-color-secondary);
  font-size: 11px;
  overflow: hidden;
  text-overflow: ellipsis;
}
@media (max-width: 1100px) {
  .lifecycle-nav {
    grid-template-columns: repeat(5, minmax(130px, 1fr));
    overflow-x: auto;
  }
}
</style>
