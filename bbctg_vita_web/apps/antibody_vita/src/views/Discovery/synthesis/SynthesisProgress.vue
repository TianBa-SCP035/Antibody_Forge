<template>
  <div class="app-container" :class="{ 'is-list-table-locked': listTableLocked }">
    <AdvancedOpsBar v-model="showAdvancedOps">
      <!-- 8 列 × 3 行，按列对齐：1 编号、2 人员、3-5 属性、6-8 到货/亲和力/流式（上行日期、下行说明） -->
      <!-- 第 1 行：项目与队列 + 三个日期区间 -->
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
          :options="optionLists.pm"
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
        <el-option v-for="item in optionLists.study_type" :key="item" :label="item" :value="item" />
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

      <!-- 第 2 行：合成订单 + 三项文本说明 -->
      <el-input
        v-model="listQuery.batch_label"
        clearable
        v-bind="headerTop('batch_label', '工单批次')"
        title="多个工单批次用逗号、空格或换行分隔，按完整批次查找；只填一个时按包含查找"
        @keyup.enter="handleFilter"
        @clear="handleFilter"
      />
      <div class="ops-user-select">
        <UserSelect
          v-model="listQuery.order_sender"
          multi-gesture
          :options="optionLists.order_sender"
          v-bind="headerTop('order_sender', '下单人')"
          clearable
          @change="handleFilter"
        />
      </div>
      <ListFilterSelect
        v-model="listQuery.selection_method"
        clearable
        v-bind="headerTop('selection_method', '挑选方式')"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.selection_method" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.is_rechoose"
        clearable
        v-bind="headerTop('is_rechoose', '是否补挑')"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.is_rechoose" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-if="canFullEdit"
        v-model="listQuery.synthetic_corp"
        clearable
        v-bind="headerTop('synthetic_corp', '合成公司')"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.synthetic_corp" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <div v-else aria-hidden="true" />
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

      <!-- 第 3 行：送测转码、亲和力人员、订单类型与序列改造 + 操作按钮 -->
      <el-input
        v-model="listQuery.synthesis_code"
        clearable
        v-bind="headerTop('synthesis_code', '送测转码')"
        title="多个送测转码用逗号、空格或换行分隔，按完整转码查找；只填一个时按包含查找"
        @keyup.enter="handleFilter"
        @clear="handleFilter"
      />
      <div class="ops-user-select">
        <UserSelect
          v-model="listQuery.affinity_owner"
          multi-gesture
          :options="optionLists.affinity_owner"
          v-bind="headerTop('affinity_owner', '亲和力人员')"
          clearable
          @change="handleFilter"
        />
      </div>
      <ListFilterSelect
        v-model="listQuery.order_kind"
        clearable
        v-bind="headerTop('order_kind', '订单性质')"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.order_kind" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.supply_mode"
        clearable
        v-bind="headerTop('supply_mode', '供应方式')"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.supply_mode" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.eng_type"
        clearable
        v-bind="headerTop('eng_type', '改造类型')"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.eng_type" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <ListFilterSelect
        v-model="listQuery.eng_method"
        clearable
        v-bind="headerTop('eng_method', '改造方式')"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.eng_method" :key="item" :label="item" :value="item" />
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
            @contextmenu.prevent="toggleQuickFilter('has_drift')"
          >
            <span class="ready-dot" />
            <span v-if="listQuery.quick_filter === 'has_drift'">
              <strong>{{ stats.has_drift }}</strong> 个批次有变更
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
            :search="fetchSynthesisRecordedTargets"
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
            <el-option v-for="item in optionLists.target_type" :key="item" :label="item" :value="item" />
          </ListFilterSelect>
          <ListFilterSelect
            v-model="listQuery.mouse_strain"
            v-bind="headerTop('mouse_strain', '小鼠品系')"
            clearable
            class="filter-select"
            @change="handleFilter"
          >
            <el-option v-for="item in optionLists.mouse_strain" :key="item" :label="item" :value="item" />
          </ListFilterSelect>
          <div class="filter-select">
            <UserSelect
              v-model="listQuery.owner"
              multi-gesture
              :options="optionLists.owner"
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
            <el-option v-for="item in optionLists.affinity_result" :key="item" :label="item" :value="item" />
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
            {{ listQuery.quick_filter === 'has_drift' ? '只看有变更' : '只看无人问津' }}
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
              :editable="canEditField(row, 'priority')"
              :lock-reason="fieldLockReason(row, 'priority')"
              @change="(value) => persistRowValue(row, 'priority', value)"
            />
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
              :value="row.status"
              :options="mainStatusOptions(row)"
              :type="statusTone(row.status)"
              :editable="canEditField(row, 'status')"
              @change="(val) => persistRowValue(row, 'status', val)"
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
              :options="optionLists.target_type"
              :tag-class="targetTypeTone(row.target_type) ? `target-tone-${targetTypeTone(row.target_type)}` : ''"
              :editable="canEditField(row, 'target_type')"
              @change="(val) => { row.target_type = val; persistRow(row, 'target_type') }"
              @locked="notifyLocked(fieldLockReason(row, 'target_type'))"
            />
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
              @pairing="openPairing"
            />
          </template>
        </WorkbenchDataTable>

        <WorkbenchSheet v-else :actions-width="460">
          <template #cell-target_name="{ row }">
            <WorkbenchColorMark
              :value="row.target_color"
              :editable="canFullEdit"
              @change="(val) => onTargetColorChange(row, val)"
            />
            <span>{{ row.target_name || '' }}</span>
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
              @pairing="openPairing"
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

    <WorkbenchDrawer
      v-model="drawerVisible"
      :title="drawerTitle"
      :meta="drawerMeta"
      :row="editingRow"
      :sections="editorSections"
      :disabled="!canEdit || draftSaving"
      :required-keys="draftRequiredKeys"
      :has-prev="hasPrevEditor"
      :has-next="hasNextEditor"
      @shift="shiftEditor"
    >
      <template #actions>
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
          @pairing="openPairing"
        />
        <el-button
          v-if="String(editingRow.order_no || '').trim()"
          class="list-table-action-btn"
          type="primary"
          plain
          :icon="Download"
          title="下载合成公司发来的版布局"
          @click="downloadPlateLayout(editingRow)"
        >
          版布局
        </el-button>
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
      </template>
      <template #field="{ field }">
        <div class="drawer-field-stack">
          <div class="drawer-control">
            <SynthesisAssayStatusEditor
              v-if="field.key === 'status' && assayStatusBadges(editingRow).length"
              :badges="assayStatusBadges(editingRow)"
              :editable="canEditAssayStatuses(editingRow)"
              @change="(change) => updateAssayStatus(editingRow, change)"
              @locked="(badge) => notifyLocked(badge.lockReason)"
            />
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
            <WorkbenchDrawerField v-else v-bind="drawerFieldBind(field)" />
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
      </template>
    </WorkbenchDrawer>
    <SynthesisPairingDialog v-model="pairingVisible" :row="pairingRow" />
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
  ElIcon,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElOptionGroup,
  ElPagination,
  ElPopover,
} from 'element-plus'
import { useUserStore } from '@vben/stores'

import AdvancedOpsBar from '#/components/AdvancedOpsBar.vue'
import ListFilterSelect from '#/components/ListFilterSelect.vue'
import {
  CELL_COLOR_OPTIONS,
  cellColorClass,
  fieldOptionLists,
  syncDrawerControlTooltip,
  uniqueTargetCodes,
  WorkbenchColorMark,
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
  workbenchQueueSortMixin,
  workbenchTargetMixin,
  workbenchHeaderMenuMixin,
  WorkbenchStatusEditor,
  WorkbenchViewToggle,
} from '#/components/workbench'
import {
  adoptDiscoverySynthesisSource,
  checkRemoteDiscoverySynthesis,
  claimDiscoverySynthesis,
  deleteDiscoverySynthesis,
  exportDiscoverySynthesisList,
  exportSynthesisPlateLayout,
  fetchDiscoverySynthesisColumnValues,
  fetchDiscoverySynthesisList,
  fetchDiscoverySynthesisOptions,
  reorderDiscoverySynthesis,
  saveDiscoverySynthesis,
  saveDiscoverySynthesisBatch,
  syncDiscoverySynthesisOrdersNow,
  fetchSynthesisRecordedTargets,
  SYNTHESIS_AFFINITY_EDIT,
  SYNTHESIS_EDIT,
  SYNTHESIS_ENG_EDIT,
  SYNTHESIS_FLOW_EDIT,
  SYNTHESIS_PM_EDIT,
} from '#/api/discoverySynthesis'
import { notifyApiError } from '#/api/errors'
import { downloadListExcel } from '#/utils/downloadExcel'
import { skipGlobalErrorHandler } from '#/api/request'
import { SERUM_PAGE_DETAIL } from '#/api/serum'
import { hasAccessCode } from '#/utils/accessCode'
import { listPageMixin } from '#/utils/listPage'
import { listTableLockMixin } from '#/utils/listTableLock'
import { copyToClipboard } from '#/utils/clipboard'
import { WORKBENCH_PRIORITY_DEFAULT } from '#/utils/serumProjectStatus'
import { applyOptionLists } from '#/utils/optionLists'
import { uniqueNames } from '#/utils/userOptions'
import UserSelect from '#/components/UserSelect.vue'
import SynthesisAssayStatusEditor from './SynthesisAssayStatusEditor.vue'
import SynthesisPairingDialog from './SynthesisPairingDialog.vue'
import SynthesisRowActions from './SynthesisRowActions.vue'
import { openSerumProject } from '../openSerumProject'
import {
  AFFINITY_EDIT_FIELD_KEYS,
  AFFINITY_STATUS_OPTIONS,
  assayComboTerm,
  CLAIM_RETURN_DAYS,
  CREATE_REQUIRED_FIELDS,
  DRAFT_LOCKED_FIELD_KEYS,
  EDITOR_SECTIONS,
  ENG_LOCKED_FIELD_KEYS,
  ENG_ROW_MESSAGE,
  ENGINEERING_EDITOR_SECTIONS,
  ENGINEERING_REQUIRED_FIELDS,
  FIELDS,
  FLOW_EDIT_FIELD_KEYS,
  FLOW_STATUS_OPTIONS,
  HEADER_MENU_COLUMNS,
  isEngineeringRow,
  isTransfectionOrderNo,
  PM_EDIT_FIELD_KEYS,
  QUEUE_TERMINAL_STATUSES,
  SHEET_COLUMN_ORDER,
  SHEET_COLUMNS,
  SHEET_HEADER_ALIASES,
  STATUS_FILTER_GROUPS,
  STATUS_VIEWS,
  SYNTHESIS_VIEW_PREFS_KEY,
  TRANSFECTION_ORDER_NO_MESSAGE,
  WORKBENCH_COLUMNS,
} from './synthesisColumns'

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
const FIELD_LABELS = Object.freeze({
  ...Object.fromEntries(Object.values(FIELDS).map((field) => [field.key, field.label])),
  target: '靶点',
  affinity_status: '亲和力状态',
  flow_status: '流式状态',
})
/** 选项接口里的名单字段 -> optionLists 的字段键。 */
const NAME_OPTION_SOURCES = {
  owners: 'owner',
  pms: 'pm',
  order_senders: 'order_sender',
  affinity_owners: 'affinity_owner',
}
const COMPLETED_ASSAY_MESSAGE = '工单已完成，不能再改实验状态；需要重新检测请先打回待检测'
const ASSAY_MAIN_STATUS_MESSAGE = '实验员只能把已完成的工单打回待检测，或把工单改为已取消'
const ASSAY_STATUS_KEYS = new Set(['affinity_status', 'flow_status'])
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
    order_sender: '',
    affinity_owner: '',
    is_rechoose: '',
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
  listFilterKey: 'synthesisProgress',
  workbenchFields: FIELDS,
  workbenchApi: {
    list: fetchDiscoverySynthesisList,
    save: saveDiscoverySynthesis,
    saveBatch: saveDiscoverySynthesisBatch,
    remove: deleteDiscoverySynthesis,
    export: exportDiscoverySynthesisList,
    exportName: '合成进度',
    columnValues: fetchDiscoverySynthesisColumnValues,
    reorder: reorderDiscoverySynthesis,
    errors: { load: { default: '加载合成与验证列表失败' } },
  },
  workbenchSheet: { columns: SHEET_COLUMNS, order: SHEET_COLUMN_ORDER, aliases: SHEET_HEADER_ALIASES },
  components: {
    AdvancedOpsBar,
    ElAutocomplete,
    ElButton,
    ElCard,
    ElDatePicker,
    ElIcon,
    ElInput,
    ElOption,
    ElOptionGroup,
    ElPagination,
    ElPopover,
    ListFilterSelect,
    Search,
    UserSelect,
    SynthesisAssayStatusEditor,
    SynthesisPairingDialog,
    SynthesisRowActions,
    Tools,
    WorkbenchColorMark,
    WorkbenchDataTable,
    WorkbenchDrawer,
    WorkbenchDrawerField,
    WorkbenchHeaderFilterChip,
    WorkbenchHeaderMenu,
    WorkbenchPriorityCell,
    WorkbenchSheet,
    WorkbenchSortCell,
    WorkbenchSortHeader,
    WorkbenchStatusEditor,
    WorkbenchTargetFilter,
    WorkbenchViewToggle,
  },
  setup() {
    const userStore = useUserStore()
    return { CopyDocument, DRAFT_ACTION_TITLE, Download, fetchSynthesisRecordedTargets, Refresh, userStore }
  },
  data() {
    return {
      viewPrefsStorageKey: SYNTHESIS_VIEW_PREFS_KEY,
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
        has_drift: 0,
      },
      showAdvancedOps: false,
      draftRow: null,
      draftSaving: false,
      syntheticDateRange: [],
      arrivalDateRange: [],
      flowDateRange: [],
      affinityDateRange: [],
      listQuery: emptyQuery(),
      optionLists: {
        ...fieldOptionLists(FIELDS),
        owner: [],
        pm: [],
        order_sender: [],
        affinity_owner: [],
      },
      statusFilterGroups: STATUS_FILTER_GROUPS,
      statusViews: STATUS_VIEWS,
      assayCardEl: null,
      assayBreakdownVisible: false,
      assayBreakdown: ASSAY_BREAKDOWN,
      assayBreakdownCounts: null,
      assayBreakdownLoading: false,
      assayBreakdownSlow: false,
      workbenchColumns: WORKBENCH_COLUMNS.map((column) => (
        column.key === 'actions' ? { ...column, width: 460 } : column
      )),
      pairingVisible: false,
      pairingRow: null,
      headerMenuColumns: HEADER_MENU_COLUMNS,
      cellColorOptions: CELL_COLOR_OPTIONS,
      remoteDuplicatesById: {},
      remoteCandidatesById: {},
      remoteUnavailableWarned: false,
      listLoaded: false,
    }
  },
  computed: {
    canFullEdit() {
      return hasAccessCode(this.userStore.userInfo, SYNTHESIS_EDIT)
    },
    canPmEdit() {
      return hasAccessCode(this.userStore.userInfo, SYNTHESIS_PM_EDIT)
    },
    canEngEdit() {
      return hasAccessCode(this.userStore.userInfo, SYNTHESIS_ENG_EDIT)
    },
    canAffinityEdit() {
      return hasAccessCode(this.userStore.userInfo, SYNTHESIS_AFFINITY_EDIT)
    },
    canFlowEdit() {
      return hasAccessCode(this.userStore.userInfo, SYNTHESIS_FLOW_EDIT)
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
      return hasAccessCode(this.userStore.userInfo, SERUM_PAGE_DETAIL)
    },
    activeViewGroup() {
      return this.listQuery.view_group || ''
    },
    statusTerms() {
      const status = this.listQuery.status
      return (Array.isArray(status) ? status : [status]).filter(Boolean)
    },
    quickFilterTitle() {
      if (this.listQuery.quick_filter === 'has_drift') {
        return '当前只看和 One 来源不一致的批次。右键取消；左键改看无人问津待认领。'
      }
      if (this.listQuery.quick_filter === 'unassigned') {
        return '当前只看负责人为无人问津的待认领批次。再点取消；右键改看有变更的批次。'
      }
      return '左键只看无人问津待认领；右键只看有变更的批次。'
    },
    editorSections() {
      return this.editingRow?.order_kind === '改造' ? ENGINEERING_EDITOR_SECTIONS : EDITOR_SECTIONS
    },
    isDraftEditing() {
      return Boolean(this.draftRow && this.editingRow === this.draftRow)
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
          this.listQuery.order_sender ||
          this.listQuery.affinity_owner ||
          this.listQuery.is_rechoose ||
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
  },
  activated() {
    if (this.listLoaded && this.isListDataStale()) this.getList()
  },
  methods: {
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
    canClaimRow(row) {
      if (!this.canClaim || !row?.id) return false
      const owner = String(row.owner || '').trim()
      if (this.canFullEdit) return !owner || owner === '无人问津'
      return (
        owner === '无人问津' ||
        (!owner && !String(row.pm || '').trim()) ||
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
      if (!owner) {
        return String(row?.pm || '').trim()
          ? '该批次尚未开放认领，标记为「无人问津」后才能认领'
          : '该批次没有 PM 和负责人，认领后 PM 设为本人'
      }
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
      if (fieldKey === 'order_no' && isTransfectionOrderNo(row?.order_no)) return false
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
      if (fieldKey === 'status' && this.canAssayMainEdit) return this.savedStatus(row) !== '已取消'
      return false
    },
    savedStatus(row) {
      const base = (row?.id && this.rowBaselines.get(row.id)) || row
      return String(base?.status || '').trim()
    },
    isCompletedRow(row) {
      return this.savedStatus(row) === '已完成'
    },
    /** 双权限实验员：已完成可打回待检测，未取消的都可改为已取消。 */
    mainStatusOptions(row) {
      if (this.canFullEdit || this.engCoversRow(row)) return this.optionLists.status
      const status = this.savedStatus(row)
      const reachable = status === '已完成' ? ['待检测', '已取消'] : ['已取消']
      return this.optionLists.status.filter((item) => item === status || reachable.includes(item))
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
      if (key === 'order_no' && isTransfectionOrderNo(row.order_no)) return TRANSFECTION_ORDER_NO_MESSAGE
      if (key === 'sort_order' && this.isQueueTerminalRow(row)) return '已结束的记录不在队列里，不能改排序'
      if (!row.id && DRAFT_LOCKED_FIELD_KEYS.has(key)) return `工单保存后才能填写「${label}」`
      if (!this.canEdit) return '你没有编辑合成与验证的权限'
      if (ASSAY_STATUS_KEYS.has(key) && this.isCompletedRow(row)) return COMPLETED_ASSAY_MESSAGE
      if (key === 'pm' && this.canPmEdit) {
        return row.id && !String(row.pm || '').trim() && !String(row.owner || '').trim()
          ? '没有 PM 和负责人时，点「认领」可把 PM 设为本人'
          : 'PM 由新建人自动填写，不能修改'
      }
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
    openSerumProject(row) {
      return openSerumProject(this, row, String(row?.experiment_id || row?.project_code || '').trim(), '请先填写项目编号')
    },
    openPairing(row) {
      if (!row?.id) return
      this.pairingRow = row
      this.pairingVisible = true
    },
    async downloadPlateLayout(row) {
      if (!row?.id) return
      if (!String(row.order_no || '').trim()) {
        ElMessage.warning('请先填写订单号')
        return
      }
      try {
        await downloadListExcel(() => exportSynthesisPlateLayout(row.id), `版布局_${row.order_no}.xlsx`)
      } catch (error) {
        notifyApiError(error, { messages: { default: '版布局下载失败' } })
      }
    },
    async handleClaim(row) {
      if (!row?.id) return
      if (!this.canClaimRow(row)) {
        ElMessage.warning(this.claimButtonTitle(row))
        return
      }
      const claimAsPm = !this.canFullEdit && !String(row.owner || '').trim()
      if (claimAsPm) {
        try {
          await ElMessageBox.confirm(
            `认领后${this.rowConfirmSubject(row)}的 PM 设为你本人，之后不能自行取消或改给他人，确认认领吗？`,
            '认领为 PM',
            { type: 'warning', confirmButtonText: '确认认领', cancelButtonText: '再想想' },
          )
        } catch {
          return
        }
      }
      if (!(await this.flushEditorForAction(row))) return
      try {
        const saved = await claimDiscoverySynthesis(row.id)
        this.applySavedFields(saved, ['owner', 'pm'])
        if (this.canFullEdit) {
          ElMessage.success(saved?.owner === '无人问津' ? '已标记为无人问津' : '已取消无人问津标记')
        } else if (claimAsPm) {
          ElMessage.success(`已设为 PM：${saved?.pm || ''}`)
        } else {
          ElMessage.success(
            saved?.owner === '无人问津' ? '已改回无人问津' : `已认领：${saved?.owner || ''}`,
          )
        }
      } catch (error) {
        notifyApiError(error, { messages: { default: '认领失败' } })
      }
    },
    releaseDrawerRow() {
      this.releaseDraftEditor()
    },
    onDrawerOpened(row) {
      if ((row.synthesis_code || row.batch_label) && !(String(row.id) in this.remoteCandidatesById)) {
        this.scheduleRemoteCheck([row])
      }
    },
    async saveRowField(row, field) {
      if (!row || !this.canEditField(row, field)) return
      if (!this.normalizeDrawerValue(row, field)) return
      if (!row.id) return row === this.draftRow ? this.commitDraft() : undefined
      if (this.rowFieldsUnchanged(row, [field])) return
      const saved = await this.submitRowFields(row, [field], {
        save: (payload) => this.saveConfirmingCompletion(saveDiscoverySynthesis, payload),
        reload: { skipRemoteCheck: true },
      })
      if (saved && (field === 'order_no' || field === 'synthesis_code' || field === 'batch_label')) {
        this.scheduleRemoteCheck([saved], { triggerFields: [field] })
      }
      return saved
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
    statusTone(value) {
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
      row[field] = change.value
      if (await this.persistRow(row, field)) ElMessage.success('实验状态已更新')
    },
    targetTypeTone(value) {
      const text = String(value || '').trim()
      return text ? (text.includes('分泌') ? 'secreted' : 'cell') : ''
    },
    drawerSelectClass(field, row) {
      return field.key === 'status' ? `status-select status-tone-${this.statusTone(row?.status)}` : ''
    },
    /** 主状态按行限定可选项；PM 只能在本人和无人问津之间认领负责人。 */
    fieldOptions(field, row) {
      if (row && field.key === 'status') return this.mainStatusOptions(row)
      if (row && field.key === 'owner' && !this.canFullEdit && this.canPmEdit) return this.pmOwnerChoices(row)
      return this.optionLists[field.key] ?? field.options ?? []
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
    async loadOptions() {
      try {
        const data = await fetchDiscoverySynthesisOptions(skipGlobalErrorHandler)
        for (const [source, key] of Object.entries(NAME_OPTION_SOURCES)) {
          this.optionLists[key] = uniqueNames(data?.[source] || [])
        }
        applyOptionLists(this.optionLists, data, {
          synthetic_corps: 'synthetic_corp',
          target_types: 'target_type',
          selection_methods: 'selection_method',
          eng_types: 'eng_type',
          eng_methods: 'eng_method',
          statuses: 'status',
          priorities: 'priority',
          order_kinds: 'order_kind',
          supply_modes: 'supply_mode',
          affinity_results: 'affinity_result',
          mouse_strains: 'mouse_strain',
        })
      } catch (error) {
        notifyApiError(error, { messages: { default: '加载合成进度选项失败' } })
      }
    },
    onListLoaded(data, { skipRemoteCheck = false } = {}) {
      workbenchCrudMixin.methods.onListLoaded.call(this, data)
      if (!skipRemoteCheck) this.scheduleRemoteCheck(this.list)
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
    isQueueTerminalRow(row) {
      return QUEUE_TERMINAL_STATUSES.includes(String(row?.status || '').trim())
    },
    releaseDraftEditor() {
      if (!this.isDraftEditing) return
      this.editingRow = null
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
        priority: WORKBENCH_PRIORITY_DEFAULT,
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
      if (this.editingId) this.closeDrawer()
      this.draftRow = draft
      this.editingId = null
      this.editingRow = draft
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
      ;[...Object.keys(FIELDS), 'experiment_id'].forEach((key) => {
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
        if (this.editingRow === draft && !this.isExcelMode) {
          this.editingId = saved.id
          this.editingRow = saved
          this.updateRowBaseline(this.editingRow)
          this.listQuery.page = this.queuePageOf(saved)
          await this.getList({ flushEditor: false, skipRemoteCheck: true })
        } else {
          if (this.editingRow === draft) this.closeDrawer()
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
      if (!await this.flushPendingSheetEdits() || !await this.awaitRowSaves()) return
      const nextColor = color || null
      const changed = rows.filter((r) => (r.target_color || null) !== nextColor)
      if (!changed.length) return
      const items = changed.map((r) => this.rowSavePayload({ ...r, target_color: nextColor }, ['target_color']))
      try {
        const res = await saveDiscoverySynthesisBatch({ items })
        ;(res?.items || []).forEach((saved) => this.applySavedFields(saved, ['target_color']))
        ElMessage.success(`已批量更新 ${changed.length} 行靶点颜色`)
      } catch (error) {
        notifyApiError(error, { messages: { default: '批量更新颜色失败' } })
        await this.getList({ flushEditor: false, silent: true, skipRemoteCheck: true })
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
      const source = this.editingRow?.id === row.id ? this.editingRow : row
      const baseKeys = [
        'priority',
        'order_kind',
        'supply_mode',
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
        'is_rechoose',
        'synthesis_code',
        'batch_label',
      ]
      const values = {}
      baseKeys.forEach((key) => {
        const val = source[key]
        if (!this.canSetOnCreate(key, source)) {
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
    /** 已关联 One 合成订单的工单不能删，删除按钮改为取消工单。 */
    handleDelete(row) {
      if (row.source_one_id) return this.handleCancelOrder(row)
      return workbenchCrudMixin.methods.handleDelete.call(this, row)
    },
    deleteConfirmText(row) {
      return `确认删除${this.rowConfirmSubject(row)}？删除后不可恢复。`
    },
    async handleCancelOrder(row) {
      const blockReason = this.deleteBlockReason(row)
      if (blockReason) {
        ElMessage.warning(blockReason)
        return
      }
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
      if (await this.persistRowValue(row, 'status', '已取消')) ElMessage.success('工单已取消')
    },
    formatCodesText(value) {
      return uniqueTargetCodes(value).join(',')
    },
    sheetChoiceSelectOptions(column, row) {
      if (column?.key === 'owner' && !this.canFullEdit && this.canPmEdit) {
        return this.pmOwnerChoices(row).map((item) => ({ label: item, value: item }))
      }
      return workbenchExcelMixin.methods.sheetChoiceSelectOptions.call(this, column, row)
    },
    formatStatusCell({ row }) {
      const badges = this.assayStatusBadges(row)
      return badges.length
        ? badges.map((item) => item.text).join('  ')
        : row.status
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
      return column.key === 'status' ? this.formatStatusCell : this.sheetTypeFormatter(column)
    },
    coerceSheetValue(key, text, row) {
      if (key === 'owner' && !this.canFullEdit && this.canPmEdit && !String(text ?? '').trim()) {
        return { ok: false, reason: 'empty' }
      }
      if (this.workbenchField(key)?.type === 'int' && typeof text === 'string') {
        return this.coerceSheetField(key, text.replace(/个|条/g, ''), row)
      }
      return this.coerceSheetField(key, text, row)
    },
    async saveSheetPasteItems(entries) {
      return this.saveConfirmingCompletion(saveDiscoverySynthesisBatch, { items: entries.map(({ payload }) => payload) })
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

html.dark .target-corner-badge.is-eng {
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
