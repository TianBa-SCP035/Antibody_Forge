<template>
  <div class="app-container" :class="{ 'is-list-table-locked': listTableLocked }">
    <AdvancedOpsBar v-model="showAdvancedOps">
      <!-- 第 1 行（8 格）：合成与批次属性 5 项 + 3 项文本说明（检测备注/未出原因/流式说明） -->
      <el-input
        v-model="listQuery.batch_label"
        clearable
        v-bind="headerTop('batch_label', '工单批次')"
        title="多个工单批次用逗号、空格或换行分隔，按完整批次查找；只填一个时按包含查找"
        @keyup.enter="handleFilter"
        @clear="handleFilter"
      />
      <el-input
        v-model="listQuery.synthesis_code"
        clearable
        v-bind="headerTop('synthesis_code', '送测转码')"
        title="多个送测转码用逗号、空格或换行分隔，按完整转码查找；只填一个时按包含查找"
        @keyup.enter="handleFilter"
        @clear="handleFilter"
      />
      <ListFilterSelect
        v-if="canFullEdit"
        v-model="listQuery.synthetic_corp"
        clearable
        v-bind="headerTop('synthetic_corp', '合成公司')"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.synthetic_corps" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.selection_method"
        clearable
        v-bind="headerTop('selection_method', '挑选方式')"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.selection_methods" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.supply_mode"
        clearable
        v-bind="headerTop('supply_mode', '供应方式')"
        @change="handleFilter"
      >
        <el-option v-for="item in supplyModeOptions" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <el-input
        v-model="listQuery.remark"
        clearable
        v-bind="headerTop('remark', '检测备注')"
        @keyup.enter="handleFilter"
        @clear="handleFilter"
      />
      <el-input
        v-model="listQuery.report_reason"
        clearable
        v-bind="headerTop('report_reason', '未出原因')"
        @keyup.enter="handleFilter"
        @clear="handleFilter"
      />
      <el-input
        v-model="listQuery.flow_note"
        clearable
        v-bind="headerTop('flow_note', '流式说明')"
        @keyup.enter="handleFilter"
        @clear="handleFilter"
      />

      <!-- 第 2 行（8 格）：项目与队列属性 5 项 + 3 个验证日期区间（与上方检测备注/未出原因/流式说明纵向对齐） -->
      <el-input
        v-model="listQuery.project_code"
        clearable
        v-bind="headerTop('project_code', '项目编号')"
        title="多个项目编号或实验号用逗号、空格或换行分隔，按完整编号查找；只填一个时按包含查找"
        @keyup.enter="handleFilter"
        @clear="handleFilter"
      />
      <div class="ops-user-select">
        <UserSelect
          v-model="listQuery.pm"
          multi-gesture
          :options="optionLists.pms"
          v-bind="headerTop('pm', 'PM')"
          clearable
          @change="handleFilter"
        />
      </div>
      <ListFilterSelect
        v-model="listQuery.study_type"
        clearable
        v-bind="headerTop('study_type', '课题类型')"
        @change="handleFilter"
      >
        <el-option v-for="item in studyTypeOptions" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.priority"
        clearable
        v-bind="headerTop('priority', '优先级')"
        @change="handleFilter"
      >
        <el-option v-for="item in priorityOptions" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.status"
        clearable
        v-bind="headerTop('status', '状态')"
        @change="handleFilter"
      >
        <el-option-group v-for="group in statusFilterGroups" :key="group.label" :label="group.label">
          <el-option v-for="item in group.options" :key="item" :label="item" :value="item" />
        </el-option-group>
      </ListFilterSelect>
      <el-date-picker
        v-model="arrivalDateRange"
        type="daterange"
        range-separator="至"
        v-bind="headerTop('arrival_date', '到货起始', 'startPlaceholder')"
        end-placeholder="到货截止"
        value-format="YYYY-MM-DD"
        @change="handleFilter"
      />
      <el-date-picker
        v-model="affinityDateRange"
        type="daterange"
        range-separator="至"
        v-bind="headerTop('affinity_date', '亲和力起始', 'startPlaceholder')"
        end-placeholder="亲和力截止"
        value-format="YYYY-MM-DD"
        @change="handleFilter"
      />
      <el-date-picker
        v-model="flowDateRange"
        type="daterange"
        range-separator="至"
        v-bind="headerTop('flow_date', '流式起始', 'startPlaceholder')"
        end-placeholder="流式截止"
        value-format="YYYY-MM-DD"
        @change="handleFilter"
      />

      <!-- 第 3 行（3 格 + 操作按钮）：订单性质与序列改造筛选项 -->
      <ListFilterSelect
        v-model="listQuery.order_kind"
        clearable
        v-bind="headerTop('order_kind', '订单性质')"
        @change="handleFilter"
      >
        <el-option v-for="item in orderKindOptions" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.eng_type"
        clearable
        v-bind="headerTop('eng_type', '改造类型')"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.eng_types" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.eng_method"
        clearable
        v-bind="headerTop('eng_method', '改造方式')"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.eng_methods" :key="item" :label="item" :value="item" />
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
          :ref="item.key === 'assay' ? setAssayCardEl : undefined"
          type="button"
          class="lifecycle-item"
          :class="[`stage-${item.tone}`, { 'is-active': activeViewGroup === item.key }]"
          :aria-pressed="activeViewGroup === item.key"
          :title="item.key === 'assay' ? `${item.hint}；选中后再点一次看子状态分布` : item.hint"
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
      <el-popover
        v-if="activeViewGroup === 'assay' && assayCardEl"
        v-model:visible="assayBreakdownVisible"
        :virtual-ref="assayCardEl"
        virtual-triggering
        trigger="click"
        placement="bottom"
        :width="360"
        transition="el-zoom-in-top"
        @show="loadAssayBreakdown"
      >
        <div v-loading="assayBreakdownSlow" class="assay-breakdown" :class="{ 'is-loading': assayBreakdownLoading }">
          <div class="assay-breakdown-main">
            <button
              v-for="item in assayBreakdown.main"
              :key="item.value"
              type="button"
              class="assay-breakdown-chip"
              v-bind="assayPick(item)"
            >
              {{ item.label }}
              <strong :class="assayCountClass(item.value)">{{ assayCount(item.value) }}</strong>
            </button>
          </div>
          <div class="assay-breakdown-table">
            <span class="assay-breakdown-cell is-corner"><i>流式</i><i>亲和力</i></span>
            <button
              v-for="item in assayBreakdown.flows"
              :key="item.value"
              type="button"
              class="assay-breakdown-cell is-head"
              v-bind="assayPick(item)"
            >
              {{ item.label }}
            </button>
            <span class="assay-breakdown-cell is-head">合计</span>
            <template v-for="row in assayBreakdown.affinities" :key="row.value">
              <button type="button" class="assay-breakdown-cell is-head" v-bind="assayPick(row)">{{ row.label }}</button>
              <button
                v-for="item in row.combos"
                :key="item.value"
                type="button"
                class="assay-breakdown-cell"
                :title="item.label"
                v-bind="assayPick(item)"
              >
                <strong :class="assayCountClass(item.value)">{{ assayCount(item.value) }}</strong>
              </button>
              <button type="button" class="assay-breakdown-cell is-total" v-bind="assayPick(row)">
                <strong :class="assayCountClass(row.value)">{{ assayCount(row.value) }}</strong>
              </button>
            </template>
            <span class="assay-breakdown-cell is-head">合计</span>
            <button
              v-for="item in [...assayBreakdown.flows, assayBreakdown.all]"
              :key="item.value"
              type="button"
              class="assay-breakdown-cell is-total"
              :title="item.label"
              v-bind="assayPick(item)"
            >
              <strong :class="assayCountClass(item.value)">{{ assayCount(item.value) }}</strong>
            </button>
          </div>
          <p class="assay-breakdown-tip">格子要两项都满足；左键只看这一项，右键追加或取消</p>
        </div>
      </el-popover>
    </section>

    <div class="filter-panel">
      <div class="data-toolbar list-filter-controls">
        <div class="filter-strip">
          <el-input
            v-model="listQuery.order_no"
            class="filter-select"
            v-bind="headerTop('order_no', '订单号')"
            title="多个订单号用逗号、空格或换行分隔，按完整单号查找；只填一个时按包含查找"
            clearable
            @keyup.enter="handleFilter"
            @clear="handleFilter"
          />
          <WorkbenchTargetFilter
            v-model="listQuery.target_name"
            class="filter-select"
            v-bind="headerTop('target_name', '靶点')"
            scope="synthesisProgress"
            @change="handleFilter"
          />
          <ListFilterSelect
            v-model="listQuery.target_type"
            v-bind="headerTop('target_type', '靶点类型')"
            clearable
            class="filter-select"
            @change="handleFilter"
          >
            <el-option label="非分泌型" value="非分泌型" />
            <el-option v-for="item in optionLists.target_types" :key="item" :label="item" :value="item" />
          </ListFilterSelect>
          <ListFilterSelect
            v-model="listQuery.mouse_strain"
            v-bind="headerTop('mouse_strain', '小鼠品系')"
            clearable
            class="filter-select"
            @change="handleFilter"
          >
            <el-option v-for="item in mouseStrainOptions" :key="item" :label="item" :value="item" />
          </ListFilterSelect>
          <div class="filter-select">
            <UserSelect
              v-model="listQuery.owner"
              multi-gesture
              :options="optionLists.owners"
              v-bind="headerTop('owner', '负责人')"
              title="左键单选，右键追加"
              clearable
              @change="handleFilter"
            />
          </div>
          <ListFilterSelect
            v-model="listQuery.affinity_result"
            v-bind="headerTop('affinity_result', '亲和力结果')"
            clearable
            class="filter-select"
            @change="handleFilter"
          >
            <el-option v-for="item in affinityResultOptions" :key="item" :label="item" :value="item" />
          </ListFilterSelect>
          <el-date-picker
            v-model="syntheticDateRange"
            class="harvest-range"
            type="daterange"
            range-separator="至"
            v-bind="headerTop('synthetic_date', '合成起始', 'startPlaceholder')"
            end-placeholder="合成截止"
            value-format="YYYY-MM-DD"
            @change="handleFilter"
          />
        </div>
        <div class="data-view-controls list-filter-actions">
          <button
            v-if="listQuery.quick_filter"
            type="button"
            class="wb-hf-chip"
            title="右上角快捷筛选，点击取消"
            @click="toggleQuickFilter(listQuery.quick_filter)"
          >
            {{ listQuery.quick_filter === 'has_issue' ? '只看异常' : '只看无人问津' }}
            <span class="wb-hf-chip-x">×</span>
          </button>
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
          <el-button
            class="list-filter-action-button"
            type="primary"
            title="右键清空筛选与表头排序"
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
          :cell-class-name="workbenchCellClassName"
          :header-menu-states="headerMenuStates"
          @header-menu="openHeaderMenu"
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
                :class="{ 'is-locked': !canEditSortCell(row) }"
                @click.stop="onSortValueClick(row)"
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
              @click.stop="notifyLocked(fieldLockReason(row, 'priority'))"
            >
              {{ rowPriority(row) }}
            </el-tag>
          </template>
          <template #status="{ row }">
            <SynthesisAssayStatusEditor
              v-if="assayStatusBadges(row).length"
              :badges="assayStatusBadges(row)"
              :editable="canEditAssayStatuses(row)"
              compact
              @change="(change) => updateAssayStatus(row, change)"
              @locked="(badge) => notifyLocked(badge.lockReason)"
            />
            <WorkbenchStatusEditor
              v-else
              :value="row.status || '待下单'"
              :options="mainStatusOptions(row)"
              :type="statusTone(row.status)"
              :editable="canEditField(row, 'status')"
              @change="(val) => updateOrderStatus(row, val)"
              @locked="notifyLocked(fieldLockReason(row, 'status'))"
            />
          </template>
          <template #target_name="{ row }">
            <WorkbenchColorMark
              :value="row.target_color"
              :editable="canFullEdit"
              @change="(val) => onTargetColorChange(row, val)"
            />
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
          <template #target_type="{ row }">
            <WorkbenchStatusEditor
              :value="row.target_type"
              :options="optionLists.target_types"
              :tag-class="targetTypeTone(row.target_type) ? `target-tone-${targetTypeTone(row.target_type)}` : ''"
              :editable="canEditField(row, 'target_type')"
              @change="(val) => { row.target_type = val; persistRow(row, 'target_type') }"
              @locked="notifyLocked(fieldLockReason(row, 'target_type'))"
            />
          </template>
          <template #mouse_strain="{ row }">
            {{ displayCsvField(row.mouse_strain) }}
          </template>
          <template #selection_method="{ row }">
            {{ displayCsvField(row.selection_method) }}
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
          <template #actions="{ row }">
            <SynthesisRowActions
              :row="row"
              :can-claim="canClaimRow(row)"
              :claim-title="claimButtonTitle(row)"
              :can-delete="canDeleteRow(row)"
              :delete-title="deleteButtonTitle(row)"
              :cancel-mode="Boolean(row.source_one_id)"
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
          @click="onSheetHeaderMenuClick"
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
              @column-resizable-change="onSheetColumnResize"
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
                  :width="sheetColumnWidth(column)"
                  :min-width="column.minWidth || column.width || 120"
                  :edit-render="sheetCustomEditRender"
                  :formatter="sheetFormatter(column)"
                >
                  <template v-if="headerMenuStates[column.key]" #header>
                    <WorkbenchHeaderLabel :label="column.label" v-bind="headerMenuStates[column.key]" />
                  </template>
                  <template v-if="column.key === 'target_name'" #default="{ row }">
                    <WorkbenchColorMark
                      :value="row.target_color"
                      :editable="canFullEdit"
                      @change="(val) => onTargetColorChange(row, val)"
                    />
                    <span>{{ row.target_name || '' }}</span>
                  </template>
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
                  :width="sheetColumnWidth(column)"
                  :min-width="column.minWidth || column.width || 120"
                  :edit-render="sheetCustomEditRender"
                  :formatter="sheetFormatter(column)"
                >
                  <template v-if="headerMenuStates[column.key]" #header>
                    <WorkbenchHeaderLabel :label="column.label" v-bind="headerMenuStates[column.key]" />
                  </template>
                  <template #edit="{ row }">
                    <ListFilterSelect
                      v-if="isCsvField(column.key) && sheetEditSource === 'dblclick'"
                      :model-value="splitCategories(row[column.key])"
                      joined
                      filterable
                      allow-create
                      default-first-option
                      ref="sheetSelectEditor"
                      class="sheet-category-select"
                      popper-class="vxe-table--ignore-clear"
                      clearable
                      @change="onCsvFieldChange(row, column.key, $event)"
                      @visible-change="onSheetSelectVisible"
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
                        :options="sheetChoiceSelectOptions(column, row)"
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
                  :width="sheetColumnWidth(column)"
                  :min-width="column.minWidth || column.width || 120"
                  :edit-render="sheetEditRender(column)"
                  :formatter="sheetFormatter(column)"
                >
                  <template v-if="headerMenuStates[column.key]" #header>
                    <WorkbenchHeaderLabel :label="column.label" v-bind="headerMenuStates[column.key]" />
                  </template>
                </vxe-column>
              </template>
              <vxe-column title="操作" width="240" fixed="right" align="center">
                <template #default="{ row }">
                  <SynthesisRowActions
                    :row="row"
                    :can-claim="canClaimRow(row)"
                    :claim-title="claimButtonTitle(row)"
                    :can-delete="canDeleteRow(row)"
                    :delete-title="deleteButtonTitle(row)"
                    :cancel-mode="Boolean(row.source_one_id)"
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

    <WorkbenchHeaderMenu v-bind="headerMenuBind">
      <template v-if="headerMenuColumn?.key === 'target_name' && isExcelMode && selectedSheetRowsForColor().length > 1" #extra>
        <div class="wb-hm-sec">
          <div class="wb-hm-sec-hd">批量标记选中 {{ selectedSheetRowsForColor().length }} 行</div>
          <div class="wb-hm-colors">
            <button
              v-for="item in cellColorOptions"
              :key="item.key"
              type="button"
              class="wb-hm-color"
              :title="item.label"
              :style="{ '--swatch': item.swatch }"
              @click="applyBatchTargetColor(item.key); closeHeaderMenu()"
            />
            <button
              type="button"
              class="wb-hm-color is-none"
              title="清除选中行颜色"
              @click="applyBatchTargetColor(null); closeHeaderMenu()"
            />
          </div>
        </div>
      </template>
    </WorkbenchHeaderMenu>

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
            :disabled="!editingRow.id"
            :disabled-title="DRAFT_ACTION_TITLE"
            :can-claim="canClaimRow(editingRow)"
            :claim-title="claimButtonTitle(editingRow)"
            :can-delete="canDeleteRow(editingRow)"
            :delete-title="deleteButtonTitle(editingRow)"
            :cancel-mode="Boolean(editingRow.source_one_id)"
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
            :disabled="!editingRow.id"
            :title="
              editingRow.id
                ? '复制当前工单的基础与改造需求信息，新建一笔合成单（若同转码在 One 库有未关联新单将自动拉取）'
                : DRAFT_ACTION_TITLE
            "
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
        :disabled="!canEdit || draftSaving"
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
                :required="draftRequiredKeys.has(field.key)"
                :class="['drawer-field', field.wide ? 'is-wide' : '', field.solo ? 'is-solo' : '']"
              >
                <div class="drawer-field-stack">
                  <div class="drawer-control">
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
                    <UserSelect
                      v-else-if="field.type === 'user' && field.multiple"
                      :model-value="splitCategories(editingRow[field.key])"
                      multi-gesture
                      joined
                      :options="usedUserOptions(field)"
                      :placeholder="`选择${field.label}`"
                      :disabled="!canEditField(editingRow, field.key)"
                      clearable
                      title="左键单选，右键追加"
                      @change="onCsvFieldChange(editingRow, field.key, $event)"
                    />
                    <UserSelect
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
                    <SynthesisAssayStatusEditor
                      v-else-if="field.key === 'status' && assayStatusBadges(editingRow).length"
                      :badges="assayStatusBadges(editingRow)"
                      :editable="canEditAssayStatuses(editingRow)"
                      @change="(change) => updateAssayStatus(editingRow, change)"
                      @locked="(badge) => notifyLocked(badge.lockReason)"
                    />
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
                    <span
                      v-if="drawerLockReason(field)"
                      class="drawer-lock-mask"
                      @mouseenter="syncDrawerLockTitle($event, drawerLockReason(field))"
                      @click="notifyLocked(drawerLockReason(field))"
                    />
                  </div>

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
  ElOptionGroup,
  ElPagination,
  ElPopover,
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
  CELL_COLOR_OPTIONS,
  cellColorClass,
  cleanFieldText,
  coerceOptionalNonnegInt,
  coerceRequiredPositiveInt,
  coerceWorkbenchViewMode,
  EXCEL_VIEW,
  splitTargetNames,
  syncDrawerControlTooltip,
  uniqueTargetCodes,
  WORKBENCH_VIEW,
  WorkbenchColorMark,
  WorkbenchDataTable,
  WorkbenchHeaderFilterChip,
  WorkbenchHeaderLabel,
  WorkbenchHeaderMenu,
  WorkbenchInlineSelect,
  WorkbenchTargetFilter,
  workbenchExcelMixin,
  workbenchTargetMixin,
  workbenchHeaderMenuMixin,
  WorkbenchStatusEditor,
  WorkbenchTargetSelect,
  WorkbenchViewToggle,
} from '#/components/workbench'
import {
  adoptDiscoverySynthesisSource,
  checkRemoteDiscoverySynthesis,
  claimDiscoverySynthesis,
  deleteDiscoverySynthesis,
  exportDiscoverySynthesisList,
  fetchDiscoverySynthesisColumnValues,
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
  canAffinityEditDiscoverySynthesis,
  canEditDiscoverySynthesis,
  canEngEditDiscoverySynthesis,
  canFlowEditDiscoverySynthesis,
  canPmEditDiscoverySynthesis,
} from '#/utils/discoveryPermission'
import { downloadListExcel, excelTimestamp } from '#/utils/downloadExcel'
import { listPageMixin } from '#/utils/listPage'
import { listTableLockMixin } from '#/utils/listTableLock'
import { canAccessSerumDetail } from '#/utils/serumPermission'
import { copyToClipboard } from '#/utils/clipboard'
import {
  canonicalizeWorkbenchPriority,
  getTiterPriorityTone,
} from '#/utils/serumProjectStatus'
import { applyOptionLists } from '#/utils/optionLists'
import { uniqueNames } from '#/utils/userOptions'
import { WORKBENCH_VIEW_PREFS_KEYS } from '#/constants/storageKeys'
import UserSelect from '#/components/UserSelect.vue'
import SynthesisAssayStatusEditor from './SynthesisAssayStatusEditor.vue'
import SynthesisRowActions from './SynthesisRowActions.vue'
import {
  AFFINITY_EDIT_FIELD_KEYS,
  AFFINITY_RESULT_OPTIONS,
  AFFINITY_STATUS_OPTIONS,
  assayComboTerm,
  BASE_EDITOR_SECTIONS,
  BREAK_FIELDS,
  CLAIM_RETURN_DAYS,
  CREATE_REQUIRED_FIELDS,
  CSV_FIELD_OPTIONS,
  DATE_KEYS,
  DEFAULT_CORP_OPTIONS,
  DEFAULT_ENG_METHOD_OPTIONS,
  DEFAULT_ENG_TYPE_OPTIONS,
  DEFAULT_SELECTION_METHOD_OPTIONS,
  DEFAULT_TARGET_TYPE_OPTIONS,
  DRAFT_LOCKED_FIELD_KEYS,
  EDITABLE_FIELDS,
  ENG_LOCKED_FIELD_KEYS,
  ENG_ROW_MESSAGE,
  ENGINEERING_EDITOR_SECTION,
  ENGINEERING_REQUIRED_FIELDS,
  FLOW_EDIT_FIELD_KEYS,
  FLOW_STATUS_OPTIONS,
  HEADER_MENU_COLUMNS,
  INT_COUNT_KEYS,
  isEngineeringRow,
  MOUSE_STRAIN_OPTIONS,
  ORDER_KIND_OPTIONS,
  PM_EDIT_FIELD_KEYS,
  PRIORITY_OPTIONS,
  QUEUE_TERMINAL_STATUSES,
  SHEET_COLUMN_ORDER,
  SHEET_COLUMNS,
  SHEET_HEADER_ALIASES,
  STATUS_FILTER_GROUPS,
  STATUS_OPTIONS,
  STATUS_VIEWS,
  STRING_MAX,
  STUDY_TYPE_OPTIONS,
  SUPPLY_MODE_OPTIONS,
  USER_OPTION_LIST,
  WORKBENCH_COLUMNS,
} from './synthesisColumns'

let lastViewMode = WORKBENCH_VIEW

const BADGE_TEXT = Object.freeze({
  亲和力待检测: '待测',
  亲和力检测中: '测中',
  亲和力已完成: '完成',
  流式待检测: '待测',
  流式已完成: '完成',
  流式不适用: '不做',
})
const badgeOptions = (values) =>
  Object.freeze(values.filter((value) => BADGE_TEXT[value]).map((value) => ({ value, label: BADGE_TEXT[value] })))
const AFFINITY_BADGE_OPTIONS = badgeOptions(AFFINITY_STATUS_OPTIONS)
const FLOW_BADGE_OPTIONS = badgeOptions(FLOW_STATUS_OPTIONS)
const FIELD_LABELS = Object.freeze(
  Object.fromEntries([
    ...SHEET_COLUMNS.map((column) => [column.key, column.label]),
    ...[...BASE_EDITOR_SECTIONS, ENGINEERING_EDITOR_SECTION].flatMap((section) =>
      section.fields.map((field) => [field.key, field.label]),
    ),
    ['affinity_status', '亲和力状态'],
    ['flow_status', '流式状态'],
  ]),
)
const COMPLETED_ASSAY_MESSAGE = '工单已完成，不能再改实验状态；需要重新检测请先打回待检测'
const ASSAY_MAIN_STATUS_MESSAGE = '实验员只能把已完成的工单打回待检测'
const ASSAY_STATUS_KEYS = new Set(['affinity_status', 'flow_status'])
const ASSAY_ROLLBACK_OPTIONS = Object.freeze(['已完成', '待检测'])
const DRAFT_ACTION_TITLE = '工单保存后才能操作'
const UNCLAIMED_OWNER = '无人问津'
function badgeTone(status) {
  if (status?.endsWith('已完成') || status === '流式不适用') return 'done'
  if (status?.endsWith('检测中')) return 'run'
  return 'wait'
}
const breakdownItem = (value, label, tone = badgeTone(value)) => ({ value, label, tone })
const ASSAY_FLOW_ITEMS = [
  breakdownItem('流式待检测', '流·待检'),
  breakdownItem('流式不适用', '流·不做', 'skip'),
  breakdownItem('流式已完成', '流·完成'),
]
/** 子弹窗：整单一排按钮，其下亲和力（行）× 流式（列）交叉表，格子是两项同时满足的组合，末行末列是合计。 */
const ASSAY_BREAKDOWN = Object.freeze({
  main: [breakdownItem('待检测', '待检测'), breakdownItem('检测中', '检测中')],
  flows: ASSAY_FLOW_ITEMS,
  affinities: [
    breakdownItem('亲和力待检测', '亲·待检'),
    breakdownItem('亲和力检测中', '亲·测中'),
    breakdownItem('亲和力已完成', '亲·完成'),
  ].map((row) => ({
    ...row,
    combos: ASSAY_FLOW_ITEMS.map((flow) =>
      breakdownItem(assayComboTerm(row.value, flow.value), `${row.label} 且 ${flow.label}`, 'combo'),
    ),
  })),
  all: breakdownItem('', '全部待检测、检测中', 'all'),
})

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
    target_type: '',
    mouse_strain: '',
    selection_method: '',
    affinity_result: '',
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
    flow_note: '',
    report_reason: '',
    remark: '',
    view_group: '',
    quick_filter: '',
    sort_field: '',
    sort_dir: '',
  }
}

export default {
  name: 'DiscoverySynthesisProgress',
  mixins: [workbenchExcelMixin, workbenchTargetMixin, listPageMixin, workbenchHeaderMenuMixin, listTableLockMixin],
  listFilterKey: 'synthesisProgress',
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
    ElOptionGroup,
    ElPagination,
    ElPopover,
    ElSelect,
    ElTag,
    ListFilterSelect,
    Search,
    UserSelect,
    SynthesisAssayStatusEditor,
    SynthesisRowActions,
    Tools,
    VxeColumn,
    VxeInput,
    VxeSelect,
    VxeTable,
    WorkbenchColorMark,
    WorkbenchDataTable,
    WorkbenchHeaderFilterChip,
    WorkbenchHeaderLabel,
    WorkbenchHeaderMenu,
    WorkbenchInlineSelect,
    WorkbenchStatusEditor,
    WorkbenchTargetFilter,
    WorkbenchTargetSelect,
    WorkbenchViewToggle,
  },
  setup() {
    const userStore = useUserStore()
    return { CopyDocument, DRAFT_ACTION_TITLE, Download, Refresh, userStore }
  },
  data() {
    return {
      viewPrefsStorageKey: WORKBENCH_VIEW_PREFS_KEYS.synthesis,
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
      draftRow: null,
      draftSaving: false,
      syntheticDateRange: [],
      arrivalDateRange: [],
      flowDateRange: [],
      affinityDateRange: [],
      listQuery: emptyQuery(),
      optionLists: {
        owners: [],
        pms: [],
        affinity_owners: [],
        synthetic_corps: [...DEFAULT_CORP_OPTIONS],
        target_types: [...DEFAULT_TARGET_TYPE_OPTIONS],
        selection_methods: [...DEFAULT_SELECTION_METHOD_OPTIONS],
        eng_types: [...DEFAULT_ENG_TYPE_OPTIONS],
        eng_methods: [...DEFAULT_ENG_METHOD_OPTIONS],
      },
      statusOptions: [...STATUS_OPTIONS],
      statusFilterGroups: STATUS_FILTER_GROUPS,
      priorityOptions: [...PRIORITY_OPTIONS],
      orderKindOptions: [...ORDER_KIND_OPTIONS],
      supplyModeOptions: [...SUPPLY_MODE_OPTIONS],
      affinityResultOptions: [...AFFINITY_RESULT_OPTIONS],
      mouseStrainOptions: [...MOUSE_STRAIN_OPTIONS],
      studyTypeOptions: [...STUDY_TYPE_OPTIONS],
      statusViews: STATUS_VIEWS,
      assayCardEl: null,
      assayBreakdownVisible: false,
      assayBreakdown: ASSAY_BREAKDOWN,
      assayBreakdownCounts: null,
      assayBreakdownLoading: false,
      assayBreakdownSlow: false,
      sheetColumns: SHEET_COLUMN_ORDER.load(),
      workbenchColumns: WORKBENCH_COLUMNS,
      headerMenuColumns: HEADER_MENU_COLUMNS,
      cellColorOptions: CELL_COLOR_OPTIONS,
      pendingDrawerSaves: new Set(),
      rowBaselines: new Map(),
      remoteDuplicatesById: {},
      remoteCandidatesById: {},
      remoteUnavailableWarned: false,
      listLoaded: false,
      allUserOptions: [],
    }
  },
  computed: {
    canFullEdit() {
      return canEditDiscoverySynthesis(this.userStore.userInfo || {})
    },
    canPmEdit() {
      return canPmEditDiscoverySynthesis(this.userStore.userInfo || {})
    },
    canEngEdit() {
      return canEngEditDiscoverySynthesis(this.userStore.userInfo || {})
    },
    canAffinityEdit() {
      return canAffinityEditDiscoverySynthesis(this.userStore.userInfo || {})
    },
    canFlowEdit() {
      return canFlowEditDiscoverySynthesis(this.userStore.userInfo || {})
    },
    canAssayMainEdit() {
      return this.canAffinityEdit && this.canFlowEdit
    },
    canEdit() {
      return this.canFullEdit || this.canPmEdit || this.canEngEdit || this.canAffinityEdit || this.canFlowEdit
    },
    canCreate() {
      return this.canFullEdit || this.canPmEdit || this.canEngEdit
    },
    canClaim() {
      return this.canFullEdit || this.canPmEdit
    },
    currentPersonName() {
      const info = this.userStore.userInfo || {}
      const raw = String(info.realName || info.display_name || info.username || '').trim()
      return raw ? raw.split(/\s+/)[0] : ''
    },
    canViewSerumProject() {
      return canAccessSerumDetail(this.userStore.userInfo || {})
    },
    activeViewGroup() {
      return this.listQuery.view_group || ''
    },
    statusTerms() {
      const status = this.listQuery.status
      return (Array.isArray(status) ? status : [status]).filter(Boolean)
    },
    quickFilterTitle() {
      if (this.listQuery.quick_filter === 'has_issue') {
        return '当前只看填写了检测说明或异常的批次。右键取消；左键改看无人问津待认领。'
      }
      if (this.listQuery.quick_filter === 'unassigned') {
        return '当前只看负责人为无人问津的待认领批次。再点取消；右键改看有检测说明或异常的批次。'
      }
      return '左键只看无人问津待认领；右键只看有检测说明或异常的批次。'
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
    isDraftEditing() {
      return Boolean(this.draftRow && this.editingRowData === this.draftRow)
    },
    draftRequiredKeys() {
      if (!this.isDraftEditing) return new Set()
      const keys = CREATE_REQUIRED_FIELDS.map(([key]) => key)
      if (this.draftRow.order_kind === '改造') keys.push(...ENGINEERING_REQUIRED_FIELDS.map(([key]) => key))
      return new Set(keys)
    },
    drawerTitle() {
      const row = this.editingRow
      if (!row) return '工单详情'
      if (!row.id) return ['新建工单', String(row.target_name || '').trim()].filter(Boolean).join(' · ')
      const target = String(row.target_name || '').trim()
      const orderNo = String(row.order_no || '').trim()
      const synCode = String(row.synthesis_code || '').trim()
      if (target && orderNo) return `${target} · ${orderNo}`
      return target || orderNo || synCode || '工单详情'
    },
    drawerMeta() {
      const row = this.editingRow
      if (!row) return ''
      if (!row.id) {
        const missing = this.draftMissingFields(row)
        if (missing.length) return `填完必填项后自动保存，还差：${missing.join('、')}`
        return this.draftTypeError(row) || '正在保存…'
      }
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
        this.listQuery.batch_label ||
          this.listQuery.synthesis_code ||
          this.listQuery.project_code ||
          this.listQuery.pm ||
          this.listQuery.study_type ||
          this.listQuery.priority ||
          this.listQuery.order_kind ||
          this.listQuery.supply_mode ||
          this.listQuery.selection_method ||
          this.listQuery.status ||
          this.listQuery.synthetic_corp ||
          this.listQuery.eng_type ||
          this.listQuery.eng_method ||
          this.listQuery.flow_note ||
          this.listQuery.report_reason ||
          this.listQuery.remark ||
          this.arrivalDateRange?.length ||
          this.flowDateRange?.length ||
          this.affinityDateRange?.length,
      )
    },
    hasSecondaryFilters() {
      return Boolean(
        this.listQuery.keyword ||
          this.listQuery.order_no ||
          this.listQuery.target_name ||
          this.listQuery.target_type ||
          this.listQuery.mouse_strain ||
          this.listQuery.owner ||
          this.listQuery.affinity_result ||
          this.syntheticDateRange?.length ||
          this.headerFiltering ||
          this.hasAdvancedFilters,
      )
    },
    sheetChoiceOptionsMap() {
      const map = Object.create(null)
      map.priority = this.priorityOptions.map((item) => ({ label: item, value: item }))
      map.status = this.statusOptions.map((item) => ({ label: item, value: item }))
      map.order_kind = this.orderKindOptions.map((item) => ({ label: item, value: item }))
      map.supply_mode = this.supplyModeOptions.map((item) => ({ label: item, value: item }))
      map.affinity_result = this.affinityResultOptions.map((item) => ({ label: item, value: item }))
      map.study_type = this.studyTypeOptions.map((item) => ({ label: item, value: item }))
      map.target_type = (this.optionLists.target_types || []).map((item) => ({
        label: item,
        value: item,
      }))
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
    if (!this.canFullEdit) {
      this.headerMenuColumns = Object.freeze(
        Object.fromEntries(Object.entries(HEADER_MENU_COLUMNS).filter(([key]) => key !== 'synthetic_corp')),
      )
    }
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
    if (this.listLoaded && this.isListDataStale()) {
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
      if (!open) this.releaseDraftEditor()
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
        } else {
          payload[field] = row[field] === '' || row[field] == null ? null : row[field]
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
        keys.add('target_type')
      }
      if (keys.has('order_kind')) {
        keys.add('owner')
        keys.add('pm')
      }
      if (keys.has('owner')) {
        keys.add('owner_claimed_at')
      }
      if (keys.has('affinity_date')) {
        keys.add('affinity_result')
      }
      if (keys.has('order_no') || keys.has('synthesis_code') || keys.has('batch_label')) {
        keys.add('source_one_id')
        keys.add('source_one_type')
        keys.add('order_no')
        keys.add('synthesis_code')
        keys.add('batch_label')
      }
      keys.add('status')
      keys.add('affinity_status')
      keys.add('affinity_owner')
      keys.add('flow_status')
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
    canClaimRow(row) {
      if (!this.canClaim || !row?.id) return false
      const owner = String(row.owner || '').trim()
      if (this.canFullEdit) return !owner || owner === '无人问津'
      return (
        owner === '无人问津' ||
        (Boolean(this.currentPersonName) && owner === this.currentPersonName && this.canReturnClaim(row))
      )
    },
    canReturnClaim(row) {
      const claimedAt = Date.parse(String(row?.owner_claimed_at || '').replace(' ', 'T'))
      return Number.isFinite(claimedAt) && Date.now() - claimedAt <= CLAIM_RETURN_DAYS * 86400000
    },
    pmOwnerChoices(row) {
      const base = (row?.id && this.rowBaselines.get(row.id)) || row || {}
      const owner = String(base.owner || '').trim()
      const me = this.currentPersonName
      if (!me) return []
      if (owner === '无人问津' || (owner === me && this.canReturnClaim(base))) return [me, '无人问津']
      return []
    },
    claimButtonTitle(row) {
      if (!this.canClaim) return '您没有权限认领合成结果'
      const owner = String(row?.owner || '').trim()
      if (this.canFullEdit) {
        if (!owner) return '标记为无人问津，开放 PM 认领'
        if (owner === '无人问津') return '取消无人问津标记'
        return `该批次已由 ${owner} 负责，如需调整请直接修改负责人`
      }
      if (owner === '无人问津') return '认领该批次合成结果'
      if (!owner) return '该批次尚未开放认领，标记为「无人问津」后才能认领'
      if (this.currentPersonName && owner === this.currentPersonName) {
        return this.canReturnClaim(row)
          ? '将该批次改回无人问津'
          : `认领已超过 ${CLAIM_RETURN_DAYS} 天，不能退回「无人问津」`
      }
      return `该批次已被 ${owner} 认领，不可重复认领`
    },
    claimedOwner(row) {
      const base = (row?.id && this.rowBaselines.get(row.id)) || row || {}
      const owner = String(base.owner || '').trim()
      return owner === '无人问津' ? '' : owner
    },
    pmOwnsRow(row) {
      if (!row?.id) return true
      const base = this.rowBaselines.get(row.id) || row
      const me = this.currentPersonName
      return Boolean(me) && me === (this.claimedOwner(base) || String(base.pm || '').trim())
    },
    pmOwnershipReason(row) {
      const owner = this.claimedOwner(row)
      if (owner) return `该工单由 ${owner} 负责，只有负责人可以操作`
      return '该工单还没有负责人，只有本人是 PM 时可以操作'
    },
    canSetOnCreate(fieldKey, draft) {
      if (DRAFT_LOCKED_FIELD_KEYS.has(fieldKey)) return false
      if (this.canFullEdit) return true
      // 兼有 PM 权限时，非改造类工单按 PM 新建，改造实验员的字段要等选成改造类才放开
      const engDraft = this.canEngEdit && (!this.canPmEdit || isEngineeringRow(draft))
      if (engDraft && !ENG_LOCKED_FIELD_KEYS.has(fieldKey)) return true
      return this.canPmEdit && PM_EDIT_FIELD_KEYS.has(fieldKey) && fieldKey !== 'owner'
    },
    engCoversRow(row) {
      return this.canEngEdit && isEngineeringRow((row?.id && this.rowBaselines.get(row.id)) || row)
    },
    canEditField(row, fieldKey) {
      if (row && !row.id) return this.canSetOnCreate(fieldKey, row)
      if (fieldKey === 'synthesis_order_id' || fieldKey === 'order_sender') {
        return false
      }
      if (fieldKey === 'sort_order' && this.isQueueTerminalRow(row)) {
        return false
      }
      if (ASSAY_STATUS_KEYS.has(fieldKey) && this.isCompletedRow(row)) return false
      if (this.canFullEdit) return true
      if (!ENG_LOCKED_FIELD_KEYS.has(fieldKey) && this.engCoversRow(row)) return true
      if (this.canPmEdit && PM_EDIT_FIELD_KEYS.has(fieldKey)) {
        if (fieldKey === 'owner') return this.pmOwnerChoices(row).length > 0
        if (this.pmOwnsRow(row)) return true
      }
      if (this.canAffinityEdit && AFFINITY_EDIT_FIELD_KEYS.has(fieldKey)) return true
      if (this.canFlowEdit && FLOW_EDIT_FIELD_KEYS.has(fieldKey)) return true
      if (fieldKey === 'status' && this.canAssayMainEdit) return this.isCompletedRow(row)
      return false
    },
    isCompletedRow(row) {
      const base = (row?.id && this.rowBaselines.get(row.id)) || row
      return String(base?.status || '').trim() === '已完成'
    },
    mainStatusOptions(row) {
      return this.canFullEdit || this.engCoversRow(row) ? this.statusOptions : ASSAY_ROLLBACK_OPTIONS
    },
    deleteBlockReason(row) {
      if (row?.source_one_id) {
        if (String(row.status || '').trim() === '已取消') return '工单已取消'
        const canCancel = this.canEditField(row, 'status') && this.mainStatusOptions(row).includes('已取消')
        return canCancel ? '' : '已关联 One 合成订单，不能删除；你没有取消该工单的权限'
      }
      if (this.canFullEdit || this.engCoversRow(row)) return ''
      if (this.canPmEdit) {
        if (!this.pmOwnsRow(row)) return this.pmOwnershipReason(row)
        return String(row?.status || '').trim() === '待下单' ? '' : 'PM 权限只能删除待下单状态的工单'
      }
      return this.canEngEdit ? ENG_ROW_MESSAGE : '您没有权限删除合成与验证工单'
    },
    canDeleteRow(row) {
      return !this.deleteBlockReason(row)
    },
    deleteButtonTitle(row) {
      const reason = this.deleteBlockReason(row)
      if (reason) return reason
      return row?.source_one_id ? '已关联 One 合成订单，不能删除，可改为「已取消」' : '删除该工单'
    },
    rowConfirmSubject(row) {
      const label = [
        String(row?.target_name || '').trim(),
        String(row?.order_no || row?.synthesis_code || row?.batch_label || '').trim(),
      ]
        .filter(Boolean)
        .join(' · ')
      return label ? `工单「${label}」` : '这条工单'
    },
    fieldLockReason(row, key) {
      if (!row || this.canEditField(row, key)) return ''
      const label = FIELD_LABELS[key] || '该字段'
      if (key === 'synthesis_order_id' || key === 'order_sender') return `「${label}」由系统自动生成，不能修改`
      if (key === 'sort_order' && this.isQueueTerminalRow(row)) return '已结束的记录不在队列里，不能改排序'
      if (!row.id && DRAFT_LOCKED_FIELD_KEYS.has(key)) return `工单保存后才能填写「${label}」`
      if (!this.canEdit) return '你没有编辑合成与验证的权限'
      if (ASSAY_STATUS_KEYS.has(key) && this.isCompletedRow(row)) return COMPLETED_ASSAY_MESSAGE
      if (key === 'pm' && this.canPmEdit) return 'PM 由新建人自动填写，不能修改'
      if (key === 'owner' && this.canPmEdit) {
        return row.id ? this.claimButtonTitle(row) : '负责人需在工单保存后通过认领设置'
      }
      if (key === 'owner' && this.canEngEdit) return '负责人通过认领设置，改造实验员不能修改'
      if (row.id && this.canPmEdit && PM_EDIT_FIELD_KEYS.has(key)) return this.pmOwnershipReason(row)
      if (row.id && this.canEngEdit && !ENG_LOCKED_FIELD_KEYS.has(key)) return ENG_ROW_MESSAGE
      if (key === 'status') {
        if (this.canAssayMainEdit) return ASSAY_MAIN_STATUS_MESSAGE
        if (row.status === '已完成' && (this.canAffinityEdit || this.canFlowEdit)) {
          return '工单已完成；需要重新检测请联系有全部编辑权限或同时有亲和力、流式权限的同事打回待检测'
        }
        return '状态随合成、到货和检测进度自动变化，只有全部编辑或同时有亲和力、流式权限的人可以手动修改'
      }
      if (key === 'target_type') return '靶点类型只有全部编辑权限可以修改'
      return `你没有修改「${label}」的权限`
    },
    drawerLockReason(field) {
      const row = this.editingRow
      if (!row) return ''
      if (field.type === 'target_codes') return '靶点编号随「靶点」自动带出，请修改靶点'
      if (field.key === 'status' && this.assayStatusBadges(row).length) return ''
      return this.fieldLockReason(row, field.key)
    },
    sortLockReason(row) {
      return (
        this.fieldLockReason(row, 'sort_order') ||
        (this.isQueueSorted ? '' : '先点表头「序号」切到队列排序，再改排序')
      )
    },
    onSortValueClick(row) {
      if (this.canEditSortCell(row)) this.startSortEdit(row)
      else this.notifyLocked(this.sortLockReason(row))
    },
    notifyLocked(reason) {
      if (reason) ElMessage.info({ message: reason, grouping: true })
    },
    syncDrawerLockTitle(event, reason) {
      const mask = event.currentTarget
      const control = mask.parentElement?.querySelector('.el-input, .el-select')
      if (control) syncDrawerControlTooltip({ target: control })
      const value = control?.getAttribute('title')
      mask.title = value ? `${value}\n${reason}` : reason
    },
    async openSerumProject(row) {
      const lookupCode = String(row?.experiment_id || row?.project_code || '').trim()
      if (!this.canViewSerumProject) {
        ElMessage.warning('您没有免疫实验详情权限')
        return
      }
      if (!lookupCode) {
        ElMessage.warning('请先填写项目编号')
        return
      }
      if (!(await this.flushEditorForAction(row))) return
      try {
        const detail = await fetchSerumDetailByExperimentId(lookupCode)
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
      if (!row?.id) return
      if (!this.canClaimRow(row)) {
        ElMessage.warning(this.claimButtonTitle(row))
        return
      }
      if (!(await this.flushEditorForAction(row))) return
      try {
        const saved = await claimDiscoverySynthesis(row.id)
        this.applySavedFields(saved, ['owner'])
        if (this.canFullEdit) {
          ElMessage.success(saved?.owner === '无人问津' ? '已标记为无人问津' : '已取消无人问津标记')
        } else {
          ElMessage.success(
            saved?.owner === '无人问津' ? '已改回无人问津' : `已认领：${saved?.owner || ''}`,
          )
        }
      } catch (error) {
        notifyApiError(error, { messages: { default: '认领失败' } })
      }
    },
    async persistRow(row, field) {
      if (!row || !this.canEditField(row, field)) return
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
      if (!row.id) return row === this.draftRow ? this.commitDraft() : undefined
      const baseline = this.rowBaselines.get(row.id)
      if (baseline && this.fieldComparable(row, field) === this.fieldComparable(baseline, field)) {
        return
      }
      if (this.editingId === row.id && this.editingRowData && row !== this.editingRowData) {
        if (field === 'target_codes' || field === 'target_name') {
          this.editingRowData.target_codes = this.cloneSheetValue(row.target_codes)
          this.editingRowData.target_name = row.target_name
        } else {
          this.editingRowData[field] = this.cloneSheetValue(row[field])
        }
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
        const saved = await this.saveConfirmingCompletion(saveDiscoverySynthesis, this.payloadRow(row, [field]))
        if (!saved) {
          this.getList({ flushEditor: false })
          return null
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
    async saveConfirmingCompletion(save, payload) {
      const result = await save(payload)
      if (!result?.needs_confirm) return result
      try {
        await ElMessageBox.confirm(result.message, '整单完成确认', {
          type: 'warning',
          confirmButtonText: '确认完成',
          cancelButtonText: '再想想',
        })
      } catch {
        ElMessage.info('已取消，本次修改未保存')
        return null
      }
      return save({ ...payload, confirm_complete: true })
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
    assayStatusBadges(row) {
      if (!row || !['待检测', '检测中'].includes(String(row.status || '').trim())) return []
      const flowSkip = String(row.target_type || '').trim() === '分泌型'
      const affPrefix = flowSkip ? '亲和力·' : '亲·'
      const badges = []
      const affLabel = BADGE_TEXT[row.affinity_status]
      if (affLabel) {
        const lockReason = this.assayLockReason(row, 'affinity_status')
        const hasReason = Boolean(String(row.report_reason || '').trim())
        badges.push({
          key: 'affinity',
          kind: '亲和力',
          full: row.affinity_status,
          text: `${affPrefix}${affLabel}`,
          options: hasReason
            ? AFFINITY_BADGE_OPTIONS.filter((option) => option.value !== '亲和力检测中')
            : AFFINITY_BADGE_OPTIONS,
          tone: badgeTone(row.affinity_status),
          editable: !lockReason,
          lockReason,
        })
      }
      const flowLabel = !flowSkip && BADGE_TEXT[row.flow_status]
      if (flowLabel) {
        const lockReason = this.assayLockReason(row, 'flow_status')
        badges.push({
          key: 'flow',
          kind: '流式',
          full: row.flow_status,
          text: `流·${flowLabel}`,
          options: FLOW_BADGE_OPTIONS,
          tone: badgeTone(row.flow_status),
          editable: !lockReason,
          lockReason,
        })
      }
      return badges
    },
    assayLockReason(row, key) {
      if (!this.canEditAssayStatuses(row) || !this.canEditField(row, key)) return this.fieldLockReason(row, key)
      const canCloseWithReason = this.canFullEdit || this.canAssayMainEdit
      if (key === 'affinity_status' && !canCloseWithReason && String(row.report_reason || '').trim()) {
        return '请先清除未出原因，再修改亲和力状态'
      }
      return ''
    },
    canEditAssayStatuses(row) {
      if (!(this.canFullEdit || this.canAffinityEdit || this.canFlowEdit) || !row?.id) return false
      return String(row.status || '').trim() !== '已取消'
    },
    async updateAssayStatus(row, change) {
      if (!this.canEditAssayStatuses(row) || !change?.key || !change?.value) return
      const field = change.key === 'affinity' ? 'affinity_status' : 'flow_status'
      if (!this.canEditField(row, field)) return
      try {
        const saved = await this.saveConfirmingCompletion(saveDiscoverySynthesis, { id: row.id, [field]: change.value })
        if (!saved) return
        this.applySavedFields(saved, [field])
        ElMessage.success('实验状态已更新')
      } catch (error) {
        notifyApiError(error, { messages: { default: '实验状态更新失败' } })
      }
    },
    targetTypeTone(value) {
      const text = String(value || '').trim()
      return text ? (text.includes('分泌') ? 'secreted' : 'cell') : ''
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
      if (field?.key === 'selection_method') return this.optionLists.selection_methods
      if (field?.key === 'eng_type') return this.optionLists.eng_types
      if (field?.key === 'eng_method') return this.optionLists.eng_methods
      if (field?.options) return field.options
      if (field?.type === 'corp_select') return this.optionLists.synthetic_corps
      if (field?.key === 'status') return this.mainStatusOptions(this.editingRow)
      if (field?.key === 'priority') return this.priorityOptions
      if (field?.key === 'order_kind') return this.orderKindOptions
      if (field?.key === 'supply_mode') return this.supplyModeOptions
      if (field?.key === 'affinity_result') return this.affinityResultOptions
      return []
    },
    usedUserOptions(field) {
      if (field?.key === 'owner' && !this.canFullEdit && this.canPmEdit) {
        return this.uniq([...this.pmOwnerChoices(this.editingRow), this.editingRow?.owner])
      }
      return this.uniq([
        ...(this.optionLists[USER_OPTION_LIST[field?.key]] || []),
        ...splitCategories(this.editingRow?.[field?.key]),
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
    async copyBannerCode(text, customMessage) {
      const val = String(text ?? '').trim()
      if (!val) return
      if (await copyToClipboard(val)) ElMessage.success(customMessage || `已复制：${val}`)
      else ElMessage.warning('复制失败，请手动复制')
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
        const created = Number(res?.created || 0)
        const updated = Number(res?.updated || 0)
        ElMessage.success(`同步完成：新建 ${created} 条，新关联 ${linked} 条，更新 ${updated} 条`)
        if (linked > 0 || created > 0 || updated > 0) {
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
      const sameList = this.listRequest.peek()
      return checkRemoteDiscoverySynthesis(ids)
        .then((res) => {
          if (!sameList()) return null
          if (res?.remote_available === false) {
            if (!this.remoteUnavailableWarned) ElMessage.warning('外部订单库暂时连不上，本次未核对外部订单')
            this.remoteUnavailableWarned = true
          } else if (res) {
            this.remoteUnavailableWarned = false
          }
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
      const fieldFilters = this.headerFilterPayload()
      if (fieldFilters.length) payload.field_filters = fieldFilters
      return payload
    },
    fetchHeaderValues(query) {
      return fetchDiscoverySynthesisColumnValues(query)
    },
    async loadOptions() {
      try {
        const data = await fetchDiscoverySynthesisOptions(skipGlobalErrorHandler)
        this.optionLists.owners = this.uniq(data?.owners || [])
        this.optionLists.pms = this.uniq(data?.pms || [])
        this.optionLists.affinity_owners = this.uniq(data?.affinity_owners || [])
        applyOptionLists(this.optionLists, data, [
          'synthetic_corps',
          'target_types',
          'selection_methods',
          'eng_types',
          'eng_methods',
        ])
        applyOptionLists(this, data, {
          statuses: 'statusOptions',
          priorities: 'priorityOptions',
          order_kinds: 'orderKindOptions',
          supply_modes: 'supplyModeOptions',
          affinity_results: 'affinityResultOptions',
          mouse_strains: 'mouseStrainOptions',
        })
      } catch (error) {
        notifyApiError(error, { messages: { default: '加载合成进度选项失败' } })
      }
    },
    async getList({ flushEditor = true, silent = false, skipRemoteCheck = false } = {}) {
      if (!silent) this.loading = true
      const isLatest = this.beginListRequest()
      try {
        if (flushEditor) {
          await this.flushPendingSheetEdits()
          await this.rememberDrawerSave(this.flushDirtyEditor())
          if (this.pendingDrawerSaves.size) {
            await Promise.all([...this.pendingDrawerSaves])
          }
        }
        if (!isLatest()) return
        const data = await fetchDiscoverySynthesisList(this.buildQuery(), skipGlobalErrorHandler)
        if (!isLatest()) return
        const editorIsDirty = this.drawerDirtyFields(this.editingRowData).length > 0
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
        if (selected && !editorIsDirty) {
          this.editingRowData = this.normalizeRow(JSON.parse(JSON.stringify(selected)))
        }
        this.markListFetched()
        this.clearSheetRange()
        this.scheduleSortable()
        if (!skipRemoteCheck) {
          this.scheduleRemoteCheck(this.list)
        }
      } catch (error) {
        if (isLatest()) {
          notifyApiError(error, { messages: { default: '加载合成与验证列表失败' } })
        }
      } finally {
        if (isLatest()) this.loading = false
      }
    },
    setAssayCardEl(el) {
      if (el && el !== this.assayCardEl) this.assayCardEl = el
    },
    /** 重开时保留上次的数字淡显着刷新，超过 300ms 才转圈，快的时候不闪。 */
    async loadAssayBreakdown() {
      this.assayBreakdownLoading = true
      const slowTimer = setTimeout(() => {
        this.assayBreakdownSlow = true
      }, 300)
      try {
        const query = this.buildQuery()
        delete query.page
        delete query.limit
        delete query.status
        const data = await this.fetchHeaderValues({ ...query, field: 'status_breakdown' })
        this.assayBreakdownCounts = Object.fromEntries((data?.items || []).map((item) => [item.value, item.count]))
      } catch (error) {
        this.assayBreakdownCounts = null
        notifyApiError(error, { messages: { default: '子状态统计加载失败' } })
      } finally {
        clearTimeout(slowTimer)
        this.assayBreakdownLoading = false
        this.assayBreakdownSlow = false
      }
    },
    /** 总合计的 value 为空：左右键都清空状态条件看全部。 */
    assayPick(item) {
      const active = item.value ? this.statusTerms.includes(item.value) : !this.statusTerms.length
      return {
        class: [`tone-${item.tone}`, { 'is-active': active }],
        onClick: () => this.pickAssayBreakdown(item.value),
        onContextmenu: (event) => {
          event.preventDefault()
          this.pickAssayBreakdown(item.value, Boolean(item.value))
        },
      }
    },
    /** 空值是右下角总合计：整单待检测加检测中。 */
    assayCount(value) {
      const counts = this.assayBreakdownCounts
      if (!counts) return ''
      return value ? counts[value] || 0 : (counts['待检测'] || 0) + (counts['检测中'] || 0)
    },
    assayCountClass(value) {
      return { 'is-pending': !this.assayBreakdownCounts, 'is-zero': !this.assayCount(value) }
    },
    pickAssayBreakdown(value, append = false) {
      const terms = this.statusTerms
      const picked = terms.includes(value)
      let next = !value || (picked && terms.length === 1) ? [] : [value]
      if (append) next = picked ? terms.filter((term) => term !== value) : [...terms, value]
      this.listQuery.status = next.length > 1 ? next : next[0] || ''
      if (!append) this.assayBreakdownVisible = false
      this.handleFilter()
    },
    handleViewGroup(key) {
      if (key === 'assay' && this.activeViewGroup === 'assay') return
      this.listQuery.status = ''
      this.dropHeaderFilter('status')
      this.listQuery.view_group = key || ''
      this.handleFilter()
    },
    toggleQuickFilter(value) {
      this.listQuery.quick_filter = this.listQuery.quick_filter === value ? '' : value
      this.handleFilter()
    },
    /** 清空全部筛选和表头排序；统计块视图和队列排序是视图模式，保留。 */
    resetFilters() {
      this.listQuery = {
        ...emptyQuery(),
        view_group: this.listQuery.view_group,
        sort_field: this.isQueueSorted ? 'sort_order' : '',
      }
      this.syntheticDateRange = []
      this.arrivalDateRange = []
      this.flowDateRange = []
      this.affinityDateRange = []
      this.clearHeaderFilters()
      this.getList()
    },
    listFilterExtras() {
      return {
        syntheticDateRange: this.syntheticDateRange,
        arrivalDateRange: this.arrivalDateRange,
        flowDateRange: this.flowDateRange,
        affinityDateRange: this.affinityDateRange,
      }
    },
    restoreListFilterExtras(state) {
      if (Array.isArray(state.syntheticDateRange)) this.syntheticDateRange = state.syntheticDateRange
      if (Array.isArray(state.arrivalDateRange)) this.arrivalDateRange = state.arrivalDateRange
      if (Array.isArray(state.flowDateRange)) this.flowDateRange = state.flowDateRange
      if (Array.isArray(state.affinityDateRange)) this.affinityDateRange = state.affinityDateRange
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
        this.resetSheetColumnWidths()
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
    sheetColumnStore() {
      return SHEET_COLUMN_ORDER
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
      return this.saveConfirmingCompletion(saveDiscoverySynthesis, this.payloadRow(row, fields))
        .then((saved) => {
          if (!saved) return null
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
      this.releaseDraftEditor()
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
      this.releaseDraftEditor()
      this.rememberDrawerSave(this.flushDirtyEditor())
      this.editingId = null
      this.editingRowData = null
      this.drawerVisible = false
    },
    releaseDraftEditor() {
      if (!this.isDraftEditing) return
      this.editingRowData = null
      if (this.draftMissingFields(this.draftRow).length) {
        ElMessage.info('必填项还没填完，草稿已保留，再点「新建工单」可继续')
      } else if (this.draftTypeError(this.draftRow)) {
        ElMessage.info(`${this.draftTypeError(this.draftRow)}，草稿已保留，再点「新建工单」可继续`)
      }
    },
    draftTypeError(row) {
      if (this.canFullEdit || this.canPmEdit || !this.canEngEdit || isEngineeringRow(row)) return ''
      return '改造实验员只能新建改造、内部转染或改亚型的工单'
    },
    newDraft(values = {}) {
      const engineering = this.listQuery.view_group === 'engineering'
      const engOnly = this.canEngEdit && !this.canFullEdit && !this.canPmEdit
      return {
        id: null,
        status: '待下单',
        priority: canonicalizeWorkbenchPriority(''),
        order_kind: engineering ? '改造' : '常规合成',
        supply_mode: engOnly && !engineering ? '内部转染' : '合成到货',
        owner: '',
        pm: this.canFullEdit && !engineering ? '' : this.currentPersonName,
        target_name: '',
        target_codes: [],
        drift_fields: [],
        ...values,
      }
    },
    openDraft(draft) {
      if (this.editingId) this.closeEditor()
      this.draftRow = draft
      this.editingId = null
      this.editingRowData = draft
      this.drawerVisible = true
    },
    draftMissingFields(row) {
      if (!row) return []
      const filled = (key) =>
        key === 'target'
          ? Boolean(String(row.target_name || '').trim() || uniqueTargetCodes(row.target_codes).length)
          : Boolean(String(row[key] ?? '').trim())
      const required =
        row.order_kind === '改造' ? [...CREATE_REQUIRED_FIELDS, ...ENGINEERING_REQUIRED_FIELDS] : CREATE_REQUIRED_FIELDS
      return required.filter(([key]) => !filled(key)).map(([, label]) => label)
    },
    draftPayload(draft) {
      const payload = {}
      ;[...EDITABLE_FIELDS, 'experiment_id', 'target_type'].forEach((key) => {
        if (!this.canEditField(draft, key)) return
        if (key === 'target_codes') {
          const codes = uniqueTargetCodes(draft.target_codes)
          if (codes.length) payload.target_codes = codes
          return
        }
        const value = draft[key]
        if (value !== null && value !== undefined && String(value).trim() !== '') payload[key] = value
      })
      return payload
    },
    async commitDraft({ success = '工单已保存', linked = '已新建', failed = '新建工单失败' } = {}) {
      const draft = this.draftRow
      if (!draft || this.draftSaving || this.draftMissingFields(draft).length || this.draftTypeError(draft)) {
        return null
      }
      this.draftSaving = true
      try {
        const saved = await saveDiscoverySynthesis(this.draftPayload(draft))
        if (this.draftRow === draft) this.draftRow = null
        if (this.editingRowData === draft && !this.isExcelMode) {
          this.editingId = saved.id
          this.editingRowData = this.normalizeRow(saved)
          this.updateRowBaseline(this.editingRowData)
          const limit = Math.max(1, Number(this.listQuery.limit) || 20)
          const n = Number(saved.sort_order)
          this.listQuery.page = this.isQueueSorted && Number.isInteger(n) && n > 0 ? Math.ceil(n / limit) : 1
          await this.getList({ flushEditor: false, skipRemoteCheck: true })
        } else {
          if (this.editingRowData === draft) this.closeEditor()
          await this.revealCreatedRow(saved, { skipRemoteCheck: true })
        }
        ElMessage.success(success)
        if (saved?.id && (saved.synthesis_code || saved.batch_label)) {
          this.scheduleRemoteCheck([saved]).then((res) => {
            const fresh = res?.updated_items?.find((item) => item.id === saved.id)
            if (res?.linked > 0 && fresh?.order_no) {
              ElMessage.success(`${linked}，并自动关联下一笔订单：${fresh.order_no}`)
            }
          })
        }
        return saved
      } catch (error) {
        notifyApiError(error, { messages: { default: failed } })
        return null
      } finally {
        this.draftSaving = false
      }
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
    workbenchCellClassName({ row, column }) {
      if (column?.property === 'target_name') return cellColorClass(row?.target_color)
      return column?.property === 'owner' && row?.owner === UNCLAIMED_OWNER ? 'owner-unclaimed' : ''
    },
    selectedSheetRowsForColor(clickedRow = null) {
      if (!this.canFullEdit || !this.isExcelMode || !this.sheetRange) return []
      const range = this.normalizedSheetRange()
      if (!range || range.r2 <= range.r1) return []
      const rows = this.list.slice(range.r1, range.r2 + 1).filter((r) => r?.id)
      if (clickedRow && !rows.some((r) => r.id === clickedRow.id)) return []
      return rows
    },
    async applyBatchTargetColor(color, rows = this.selectedSheetRowsForColor()) {
      const nextColor = color || null
      const changed = rows.filter((r) => (r.target_color || null) !== nextColor)
      if (!changed.length) return
      const items = changed.map((r) => ({ id: r.id, target_color: nextColor }))
      try {
        const res = await saveDiscoverySynthesisBatch({ items })
        ;(res?.items || []).forEach((saved) => this.applySavedFields(saved, ['target_color']))
        ElMessage.success(`已批量更新 ${changed.length} 行靶点颜色`)
      } catch (error) {
        notifyApiError(error, { messages: { default: '批量更新颜色失败' } })
      }
    },
    onTargetColorChange(row, color) {
      const batchRows = this.selectedSheetRowsForColor(row)
      if (batchRows.length > 1) {
        return this.applyBatchTargetColor(color, batchRows)
      }
      row.target_color = color
      return this.persistRow(row, 'target_color')
    },
    onWorkbenchRowClick(row, _column, event) {
      if (
        event?.target?.closest?.(
          '.el-button, .el-input, .el-select, .el-date-editor, .action-cell, .sort-column-cell, .workbench-status-tag, .wb-color-mark-btn',
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
      if (this.isDraftEditing) return
      this.openDraft(this.draftRow || this.newDraft())
    },
    async handleDuplicateTask(row) {
      if (!this.canCreate || !row?.id) return
      if (!(await this.flushEditorForAction(row))) return
      const source = this.editingRowData?.id === row.id ? this.editingRowData : row
      const baseKeys = [
        'priority',
        'order_kind',
        'supply_mode',
        'owner',
        'pm',
        'project_code',
        'experiment_id',
        'study_type',
        'target_name',
        'target_codes',
        'target_type',
        'mouse_strain',
        'eng_type',
        'eng_method',
        'eng_parent_seq',
        'eng_requirement',
        'remark',
        'selection_method',
        'synthesis_code',
        'batch_label',
      ]
      const values = {}
      baseKeys.forEach((key) => {
        const val = source[key]
        if (!this.canSetOnCreate(key, source) || (key === 'owner' && val === '无人问津')) {
          return
        }
        if (Array.isArray(val)) {
          if (val.length) values[key] = [...val]
        } else if (val !== null && val !== undefined && String(val).trim() !== '') {
          values[key] = val
        }
      })
      const draft = this.newDraft(values)
      const missing = this.draftMissingFields(draft)
      const typeError = this.draftTypeError(draft)
      if (missing.length || typeError) {
        this.openDraft(draft)
        ElMessage.info(missing.length ? `已复制基础信息，还需填写：${missing.join('、')}` : typeError)
        return
      }
      this.draftRow = draft
      await this.commitDraft({
        success: '已复制基础与改造信息生成新单，请填写新订单信息',
        linked: '已加单',
        failed: '加单失败',
      })
    },
    async handleDelete(row) {
      const blockReason = this.deleteBlockReason(row)
      if (blockReason) {
        ElMessage.warning(blockReason)
        return
      }
      if (row.source_one_id) return this.handleCancelOrder(row)
      try {
        await ElMessageBox.confirm(`确认删除${this.rowConfirmSubject(row)}？删除后不可恢复。`, '删除确认', {
          type: 'warning',
          confirmButtonText: '删除',
          cancelButtonText: '再想想',
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
    async handleCancelOrder(row) {
      try {
        await ElMessageBox.confirm(
          `${this.rowConfirmSubject(row)}已关联 One 合成订单，不能删除。确认改为「已取消」吗？取消后移出排队，之后仍可在状态里改回。`,
          '取消工单',
          { type: 'warning', confirmButtonText: '改为已取消', cancelButtonText: '再想想' },
        )
      } catch {
        return
      }
      if (!(await this.flushEditorForAction(row))) return
      if (await this.updateOrderStatus(row, '已取消')) ElMessage.success('工单已取消')
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
    isCsvField(key) {
      return Object.prototype.hasOwnProperty.call(CSV_FIELD_OPTIONS, key)
    },
    csvFieldOptions(key) {
      if (key === 'selection_method') {
        return this.optionLists.selection_methods || DEFAULT_SELECTION_METHOD_OPTIONS
      }
      if (key === 'eng_type') return this.optionLists.eng_types || DEFAULT_ENG_TYPE_OPTIONS
      if (key === 'eng_method') return this.optionLists.eng_methods || DEFAULT_ENG_METHOD_OPTIONS
      if (key === 'mouse_strain') return this.mouseStrainOptions
      if (this.isUserColumn({ key })) return this.uniq([...(this.optionLists[USER_OPTION_LIST[key]] || []), ...this.allUserOptions])
      return CSV_FIELD_OPTIONS[key] || []
    },
    extraCsvOptions(key, value) {
      const known = new Set(this.csvFieldOptions(key))
      return splitCategories(value).filter((item) => !known.has(item))
    },
    joinCsvValue(key, values) {
      return joinCsvField(this.isUserColumn({ key }) ? [] : this.csvFieldOptions(key), values)
    },
    onCsvFieldChange(row, key, values) {
      row[key] = this.joinCsvValue(key, values)
      if (this.sheetEditSource === 'dblclick') return
      this.persistRow(row, key)
    },
    formatCodesText(value) {
      return uniqueTargetCodes(value).join(',')
    },
    onDrawerTargetChange(row, payload) {
      row.target_codes = payload.codes
      row.target_name = payload.name
      this.mergeTargetOptions(payload.items)
      this.persistRow(row, 'target_codes')
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
    sheetChoiceSelectOptions(column, row) {
      if (column?.key === 'owner' && !this.canFullEdit && this.canPmEdit) {
        return this.pmOwnerChoices(row).map((item) => ({ label: item, value: item }))
      }
      return this.sheetChoiceOptionsMap[column?.key] || []
    },
    sheetChoiceDirectValue(row, column) {
      return row[column.key] ?? ''
    },
    setSheetChoiceDirectValue(row, column, value) {
      this.setSheetDirectValue(row, column.key, value)
    },
    formatCodes({ row }) {
      return this.formatCodesText(row.target_codes)
    },
    formatCsvCell({ cellValue }) {
      return displayCsvField(cellValue)
    },
    formatStatusCell({ row }) {
      const badges = this.assayStatusBadges(row)
      return badges.length
        ? badges.map((item) => item.text).join('  ')
        : String(row?.status || '待下单')
    },
    sheetCellLockReason(row, key) {
      if (!row?.id) return '记录还没保存'
      const fixed = this.sheetSortLockReason(row, key) || this.sheetReadonlyLockReason(key)
      return fixed || this.fieldLockReason(row, key)
    },
    sheetCellClassName({ row, column }) {
      const classes = []
      if (column?.field === 'target_name') {
        classes.push(cellColorClass(row?.target_color))
      }
      if (column?.field === 'priority') {
        classes.push(`sheet-tone-${this.priorityTone(row)}`)
      }
      if (column?.field === 'status') {
        classes.push(`sheet-tone-${this.statusTone(row?.status)}`)
      }
      if (column?.field === 'target_type' && row?.target_type) {
        classes.push(`sheet-tone-${this.targetTypeTone(row.target_type)}`)
      }
      if (column?.field === 'owner' && row?.owner === UNCLAIMED_OWNER) {
        classes.push('owner-unclaimed')
      }
      return classes.join(' ')
    },
    sheetFormatter(column) {
      if (column.key === 'sort_order') return this.formatSortColumnCell
      if (column.key === 'status') return this.formatStatusCell
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
        return this.priorityOptions.includes(canon)
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
      if (key === 'affinity_result') {
        const val = String(raw || '').trim()
        if (!val) return { ok: true, value: null }
        return this.matchSheetOption(this.affinityResultOptions, val)
      }
      if (key === 'study_type') {
        const val = String(raw || '').trim()
        if (!val) return { ok: true, value: null }
        return this.matchSheetOption(this.studyTypeOptions, val)
      }
      if (this.isUserColumn({ key })) {
        const val = String(raw || '').trim()
        if (key === 'owner' && !this.canFullEdit && this.canPmEdit && !val) {
          return { ok: false, reason: 'option' }
        }
        if (!val) return { ok: true, value: null }
        const names = this.uniq([...(this.optionLists[USER_OPTION_LIST[key]] || []), ...this.allUserOptions])
        if (!this.isCsvField(key)) return this.matchSheetOption(names, val)
        const picked = splitCategories(val).map((name) => this.matchSheetOption(names, name))
        return picked.find((item) => !item.ok) || { ok: true, value: this.joinCsvValue(key, picked.map((item) => item.value)) }
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
        return { ok: true, value: this.joinCsvValue(key, raw) }
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
        const originalCodes = originalRecord?.targetCodes ?? originalValue
        const originalName = originalRecord?.targetName ?? this.rowBaselines.get(row.id)?.target_name ?? ''
        if (await this.applySheetTargetPick(row, originalCodes, originalName)) {
          return this.persistRow(row, 'target_codes')
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
      if ((key === 'target_codes' || key === 'target_name') && !await this.applySheetTargetText(row, key, originalValue)) return
      return this.persistRow(row, key)
    },
    async onSheetPaste(event) {
      const labelToKey = new Map([
        ...Object.entries(SHEET_HEADER_ALIASES),
        ...SHEET_COLUMNS.map((column) => [column.label, column.key]),
      ])
      const paste = await this.prepareSheetPaste(event, labelToKey)
      if (!paste) return
      const { dataRows, hasHeader, headerKeys, skippedRowCount, startColIndex, startIndex } = paste

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
        const result = await this.saveConfirmingCompletion(saveDiscoverySynthesisBatch, { items })
        ;(result?.items || []).forEach((saved) => this.applySavedFields(saved))
        await this.getList({ flushEditor: false, silent: true })
        if (!result) return
        const savedCount = result.items?.length || 0
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
.table-card :deep(.el-tag.target-tone-secreted) { color: #be185d; background: #fdf2f8; border-color: #f9a8d4; }
.table-card :deep(.el-tag.target-tone-cell) { color: #0f766e; background: #f0fdfa; border-color: #99f6e4; }
.sheet-wrap :deep(.sheet-tone-secreted) { color: #be185d; }
.sheet-wrap :deep(.sheet-tone-cell) { color: #0f766e; }
.table-card :deep(.owner-unclaimed .cell),
.sheet-wrap :deep(.owner-unclaimed) {
  color: #dd6b20;
}
.assay-breakdown {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.assay-breakdown-main {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.assay-breakdown-chip {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 32px;
  color: var(--el-text-color-regular);
  font-size: 12px;
  background: var(--el-fill-color-light);
  border: 1px solid transparent;
  border-radius: 6px;
  cursor: pointer;
}
.assay-breakdown-chip strong { font-size: 14px; }
.assay-breakdown-chip:hover { border-color: var(--el-color-primary-light-5); }
.assay-breakdown-chip.is-active {
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary);
}
/* 1px 间隙露出底色当表格线，所有格子同宽同高 */
.assay-breakdown-table {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 1px;
  overflow: hidden;
  background: var(--el-border-color-lighter);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
}
.assay-breakdown-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 0;
  height: 30px;
  padding: 0 6px;
  color: var(--el-text-color-regular);
  font-size: 12px;
  white-space: nowrap;
  background: var(--el-bg-color);
  border: 0;
  border-radius: 0;
}
button.assay-breakdown-cell { cursor: pointer; }
button.assay-breakdown-cell:hover { background: var(--el-fill-color); }
.assay-breakdown-cell.is-head {
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color-light);
}
.assay-breakdown-cell.is-total { background: var(--el-fill-color-lighter); }
.assay-breakdown-cell.is-corner {
  position: relative;
  background: linear-gradient(
    to top right,
    var(--el-fill-color-light) calc(50% - 0.5px),
    var(--el-border-color) 50%,
    var(--el-fill-color-light) calc(50% + 0.5px)
  );
}
.assay-breakdown-cell.is-corner i {
  position: absolute;
  color: var(--el-text-color-secondary);
  font-size: 10px;
  font-style: normal;
  line-height: 1;
}
.assay-breakdown-cell.is-corner i:first-child { top: 4px; right: 6px; }
.assay-breakdown-cell.is-corner i:last-child { bottom: 4px; left: 6px; }
.assay-breakdown strong {
  font-variant-numeric: tabular-nums;
  transition: opacity 0.2s;
}
.assay-breakdown .tone-wait strong { color: var(--el-color-warning); }
.assay-breakdown .tone-run strong { color: var(--el-color-primary); }
.assay-breakdown .tone-done strong { color: var(--el-color-success); }
.assay-breakdown .tone-skip strong { color: var(--el-color-primary-light-3); }
.assay-breakdown strong.is-zero { color: var(--el-text-color-placeholder); }
.assay-breakdown strong.is-pending { opacity: 0; }
.assay-breakdown.is-loading strong:not(.is-pending) { opacity: 0.35; }
.assay-breakdown-cell.is-active,
.assay-breakdown-cell.is-active:hover {
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  box-shadow: inset 0 0 0 1px var(--el-color-primary);
}
.assay-breakdown-tip {
  margin: 0;
  color: var(--el-text-color-placeholder);
  font-size: 11px;
  line-height: 16px;
}
.table-card :deep(.status-column-cell .cell) {
  padding-right: 4px;
  padding-left: 4px;
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
  background: var(--el-color-primary-light-9);
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
.drawer-control {
  position: relative;
  width: 100%;
  min-width: 0;
}
.drawer-lock-mask {
  position: absolute;
  inset: 0;
  z-index: 2;
  cursor: not-allowed;
}
.sort-order-value.is-locked {
  cursor: default;
}
.drawer-field.is-solo + .drawer-field {
  grid-column-start: 1;
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
  background: var(--el-bg-color);
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

html.dark .table-card :deep(.owner-unclaimed .cell),
html.dark .sheet-wrap :deep(.owner-unclaimed) {
  color: #f6ad55;
}

html.dark .table-card :deep(.el-tag.target-tone-secreted) {
  color: var(--el-color-danger);
  background: var(--el-color-danger-light-9);
  border-color: var(--el-color-danger-light-7);
}

html.dark .table-card :deep(.el-tag.target-tone-cell) {
  color: var(--vita-library-text);
  background: var(--vita-library-bg);
  border-color: var(--vita-library-border);
}

html.dark .target-corner-badge.is-eng,
html.dark .drawer-card.is-eng-section {
  color: var(--vita-king-text);
  background: var(--vita-king-bg);
  border-color: var(--vita-king-border);
}

html.dark .target-corner-badge.is-internal {
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary-light-7);
}

html.dark .target-corner-badge.is-isotype {
  color: var(--vita-library-text);
  background: var(--vita-library-bg);
  border-color: var(--vita-library-border);
}

html.dark .target-corner-badge.is-drift {
  color: var(--el-color-warning);
  background: var(--el-color-warning-light-9);
  border-color: var(--el-color-warning-light-7);
}

html.dark .drawer-card.is-eng-section .drawer-card-title {
  color: var(--vita-king-text);
}

html.dark .drift-banner {
  color: var(--el-color-warning);
  background: var(--el-color-warning-light-9);
}

html.dark .drift-adopt-btn {
  color: var(--el-color-warning);
  border-color: var(--el-color-warning);
}

html.dark .drift-adopt-btn:hover {
  background: var(--el-color-warning-light-9);
}
</style>
