<template>
  <div class="app-container">
    <AdvancedOpsBar v-model="showAdvancedOps">
      <el-select
        v-model="listQuery.pm"
        clearable
        filterable
        placeholder="PM"
        style="width: 180px;"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.pms" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select
        v-model="listQuery.priority"
        clearable
        placeholder="优先级"
        style="width: 180px;"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.priority" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select
        v-model="listQuery.owner"
        clearable
        filterable
        placeholder="开展人"
        style="width: 180px;"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.owners" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select
        v-model="listQuery.reviewer"
        clearable
        filterable
        placeholder="审核人"
        style="width: 180px;"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.reviewers" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select
        v-model="listQuery.display_status"
        clearable
        filterable
        placeholder="状态"
        style="width: 180px;"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.statuses" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select
        v-model="listQuery.species_cross"
        clearable
        placeholder="种属交叉"
        style="width: 180px;"
        @change="handleFilter"
      >
        <el-option v-for="item in tokenMultiOptions('species_cross')" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select
        v-model="listQuery.mouse_strain"
        clearable
        filterable
        placeholder="小鼠品系"
        style="width: 180px;"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.mouse_strain" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select
        v-model="listQuery.mouse_zygosity"
        clearable
        placeholder="纯合/杂合"
        style="width: 180px;"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.mouse_zygosity" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select
        v-model="listQuery.mouse_region"
        clearable
        placeholder="提供地区"
        style="width: 180px;"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.mouse_region" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select
        v-model="listQuery.mouse_expand_requested"
        clearable
        placeholder="代下扩繁"
        style="width: 180px;"
        @change="handleFilter"
      >
        <el-option v-for="item in yesNoOptions" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select
        v-model="listQuery.antigen_source"
        clearable
        placeholder="抗原来源"
        style="width: 180px;"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.antigen_source" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select
        v-model="listQuery.lnp_ordered"
        clearable
        placeholder="LNP下单"
        style="width: 180px;"
        @change="handleFilter"
      >
        <el-option v-for="item in yesNoOptions" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select
        v-model="listQuery.cell_prep_status"
        clearable
        placeholder="冲击细胞"
        style="width: 180px;"
        @change="handleFilter"
      >
        <el-option v-for="item in optionLists.cell_prep_status" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select
        v-model="listQuery.has_scheme_data"
        clearable
        placeholder="方案内容"
        style="width: 180px;"
        @change="handleFilter"
      >
        <el-option label="有内容" value="是" />
        <el-option label="未填写" value="否" />
      </el-select>
      <el-button v-if="hasSecondaryFilters" @click="resetFilters">重置全部筛选</el-button>
      <el-button type="warning" :icon="Download" @click="handleListExport">列表导出</el-button>
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
            placeholder="搜索靶点、项目、实验号、PM 或开展人"
            clearable
            @keyup.enter="handleFilter"
            @clear="handleFilter"
          />
          <el-select
            v-model="listQuery.study_type"
            placeholder="课题类型"
            clearable
            filterable
            class="filter-select"
            @change="handleFilter"
          >
            <el-option v-for="item in optionLists.study_type" :key="item" :label="item" :value="item" />
          </el-select>
          <el-select
            v-model="listQuery.immuno_method"
            placeholder="免疫方式"
            clearable
            class="filter-select"
            @change="handleFilter"
          >
            <el-option v-for="item in tokenMultiOptions('immuno_method')" :key="item" :label="item" :value="item" />
          </el-select>
          <el-select
            v-model="listQuery.mouse_strain_category"
            placeholder="归类鼠型"
            clearable
            filterable
            class="filter-select"
            @change="handleFilter"
          >
            <el-option v-for="item in optionLists.mouse_strain_category" :key="item" :label="item" :value="item" />
          </el-select>
          <el-select
            v-model="listQuery.mouse_status"
            placeholder="小鼠运输"
            clearable
            class="filter-select"
            @change="handleFilter"
          >
            <el-option v-for="item in optionLists.mouse_status" :key="item" :label="item" :value="item" />
          </el-select>
          <el-select
            v-model="listQuery.antigen_ready"
            placeholder="抗原到货"
            clearable
            class="filter-select"
            @change="handleFilter"
          >
            <el-option v-for="item in yesNoOptions" :key="item" :label="item" :value="item" />
          </el-select>
          <el-select
            v-model="listQuery.review_status"
            placeholder="审核结果"
            clearable
            class="filter-select"
            @change="handleFilter"
          >
            <el-option v-for="item in optionLists.review_status" :key="item" :label="item" :value="item" />
          </el-select>
          <el-select
            v-model="listQuery.can_start"
            placeholder="开展条件"
            clearable
            class="filter-select"
            @change="handleFilter"
          >
            <el-option v-for="item in yesNoOptions" :key="item" :label="item === '是' ? '可开展' : '暂不可开展'" :value="item" />
          </el-select>
        </div>
        <div class="data-view-controls list-filter-actions">
          <button
            type="button"
            class="list-advanced-trigger"
            :class="{ 'is-active': showAdvancedOps }"
            title="更多筛选与操作"
            @click="showAdvancedOps = !showAdvancedOps"
          >
            <el-icon><Tools /></el-icon>
          </button>
          <el-button class="list-filter-action-button" type="primary" @click="handleFilter">
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
      v-loading="loading"
      shadow="never"
      class="table-card list-table-card"
    >
      <el-table
        v-if="viewMode === 'workbench'"
        ref="workbenchTable"
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
      >
        <el-table-column :label="sortColumnLabel" align="center" width="62" class-name="sort-column-cell">
          <template #header>
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
          <template #default="{ row, $index }">
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
        </el-table-column>
        <el-table-column prop="target_name" label="靶点名称" align="center" min-width="100" show-overflow-tooltip />
        <el-table-column prop="pm" label="PM" align="center" min-width="72" show-overflow-tooltip />
        <el-table-column prop="mouse_strain_category" label="归类鼠型" align="center" min-width="90" show-overflow-tooltip />
        <el-table-column prop="project_code" label="免疫项目号" align="center" min-width="120" show-overflow-tooltip />
        <el-table-column prop="remark" label="备注" align="center" min-width="120" show-overflow-tooltip />
        <el-table-column label="状态" align="center" min-width="110" class-name="status-column-cell">
          <template #default="{ row }">
            <WorkbenchStatusEditor
              :value="row.aligned_locked ? row.display_status : row.plan_status"
              :options="planStatusOptions"
              :type="statusTagType(row) === 'king' ? 'info' : statusTagType(row)"
              :editable="canEditField(row, 'plan_status') && !row.aligned_locked"
              @change="value => updateStatusField(row, 'plan_status', value)"
            />
          </template>
        </el-table-column>
        <el-table-column label="小鼠运输" align="center" min-width="100" class-name="status-column-cell">
          <template #default="{ row }">
            <WorkbenchStatusEditor
              :value="row.mouse_status"
              :options="optionLists.mouse_status"
              :type="mouseStatusTone(row.mouse_status)"
              :editable="canEditField(row, 'mouse_status')"
              @change="value => updateStatusField(row, 'mouse_status', value)"
            />
          </template>
        </el-table-column>
        <el-table-column label="抗原到货" align="center" min-width="90" class-name="status-column-cell">
          <template #default="{ row }">
            <WorkbenchStatusEditor
              :value="row.antigen_ready"
              :options="yesNoOptions"
              :type="yesNoTagType(row.antigen_ready)"
              :editable="canEditField(row, 'antigen_ready')"
              @change="value => updateStatusField(row, 'antigen_ready', value)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="review_status" label="审核结果" align="center" min-width="90" class-name="status-column-cell">
          <template #default="{ row }">
            <WorkbenchStatusEditor
              :value="row.review_status"
              :options="optionLists.review_status"
              :type="reviewTone(row.review_status)"
              :editable="canEditField(row, 'review_status')"
              @change="value => updateStatusField(row, 'review_status', value)"
            />
          </template>
        </el-table-column>
        <el-table-column label="可否开展" align="center" min-width="90" class-name="status-column-cell">
          <template #default="{ row }">
            <WorkbenchStatusEditor
              :value="row.can_start"
              :options="yesNoOptions"
              :type="yesNoTagType(row.can_start)"
              :editable="canEditField(row, 'can_start')"
              @change="value => updateStatusField(row, 'can_start', value)"
            />
          </template>
        </el-table-column>
        <el-table-column label="优先级" align="center" min-width="112">
          <template #default="{ row }">
            <el-select
              v-if="canEditField(row, 'priority')"
              v-model="row.priority"
              size="small"
              class="inline-select priority-select"
              :class="'status-tone-' + priorityTone(row)"
              @click.stop
              @change="persistRow(row, 'priority')"
            >
              <el-option v-for="item in optionLists.priority" :key="item" :label="item" :value="item" />
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
        </el-table-column>
        <el-table-column label="操作" align="center" width="240" fixed="right" class-name="action-column-cell">
          <template #default="{ row }">
            <WorkbenchRowActions
              :row="row"
              :can-copy="canCopy"
              :can-delete="canDeleteRow(row)"
              :can-unlist="canFullEdit"
              @scheme="openScheme"
              @copy="handleCopy"
              @delete="handleDelete"
              @unlist="handleUnlist"
            />
          </template>
        </el-table-column>
      </el-table>

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
        @selectstart="onSheetSelectStart"
      >
        <div ref="sheetTableStage" class="sheet-table-stage">
          <vxe-table
            :key="sheetColumnOrderKey"
            ref="sheetTable"
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
            :header-cell-style="headerCellStyle"
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
                v-else-if="column.edit === 'select' || isMultiSelectColumn(column)"
                :field="column.key"
                :title="sheetColumnTitle(column)"
                :width="column.width"
                :min-width="column.minWidth || column.width || 120"
                :show-overflow="!isTokenMultiKey(column.key)"
                :edit-render="{ name: 'VxeInput' }"
                :formatter="sheetFormatter(column)"
              >
                <template #edit="{ row }">
                  <div v-if="sheetEditSource === 'dblclick'" class="sheet-picker-editor">
                    <span class="sheet-picker-editor__value">
                      {{ sheetPickerDisplayValue(row, column) }}
                    </span>
                    <VxeSelect
                      v-model="row[column.key]"
                      class-name="sheet-grid-editor sheet-picker-control"
                      :filterable="isUserField(column)"
                      :multiple="isMultiSelectColumn(column)"
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
                    @update:model-value="setSheetChoiceDirectValue(row, column.key, $event)"
                  />
                </template>
              </vxe-column>
              <vxe-column
                v-else
                :field="column.key"
                :title="sheetColumnTitle(column)"
                :width="column.width"
                :min-width="column.minWidth || column.width || 120"
                :align="column.key === 'sort_order' ? 'center' : undefined"
                :header-align="column.key === 'sort_order' ? 'center' : undefined"
                :show-overflow="!isTokenMultiKey(column.key)"
                :edit-render="sheetEditRender(column)"
                :formatter="sheetFormatter(column)"
              />
            </template>
            <vxe-column title="操作" width="240" fixed="right" align="center">
              <template #default="{ row }">
                <WorkbenchRowActions
                  :row="row"
                  :can-copy="canCopy"
                  :can-delete="canDeleteRow(row)"
                  :can-unlist="canFullEdit"
                  @scheme="openScheme"
                  @copy="handleCopy"
                  @delete="handleDelete"
                  @unlist="handleUnlist"
                />
              </template>
            </vxe-column>
          </vxe-table>
          <div
            ref="sheetRangeOverlay"
            class="sheet-range-overlay"
            aria-hidden="true"
          />
          <div ref="sheetColumnDropLine" class="sheet-column-drop-line" aria-hidden="true" />
          <div ref="sheetColumnGhost" class="sheet-column-ghost" aria-hidden="true" />
        </div>
      </div>

      <div class="list-pagination">
        <el-pagination
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          v-model:current-page="listQuery.page"
          v-model:page-size="listQuery.limit"
          :page-sizes="[20, 50, 100, 200]"
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
          <WorkbenchRowActions
            :row="editingRow"
            :can-copy="canCopy"
            :can-delete="canDeleteRow(editingRow)"
            :can-unlist="canFullEdit"
            @scheme="openScheme"
            @copy="handleCopy"
            @delete="handleDelete"
            @unlist="handleUnlist"
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
                :class="['drawer-field', field.wide ? 'is-wide' : '']"
                :data-field-key="field.key"
              >
                <el-date-picker
                  v-if="field.type === 'date'"
                  v-model="editingRow[field.key]"
                  type="date"
                  value-format="YYYY-MM-DD"
                  format="YYYY-MM-DD"
                  placeholder="选择日期"
                  style="width: 100%;"
                  :disabled="isFieldLocked(editingRow, field)"
                  @change="persistRow(editingRow, field.key)"
                />
                <WorkbenchTargetSelect
                  v-else-if="field.type === 'target'"
                  v-model="editingRow.target_codes"
                  :display-name="editingRow.target_name"
                  :placeholder="editingRow.target_name ? '' : '搜索靶点'"
                  :disabled="isFieldLocked(editingRow, field)"
                  @change="onDrawerTargetChange(editingRow, $event)"
                />
                <el-input
                  v-else-if="field.type === 'target_codes'"
                  :model-value="codesText(editingRow)"
                  disabled
                  placeholder="自动带出"
                />
                <el-select
                  v-else-if="field.type === 'multi'"
                  :model-value="tokenMultiList(editingRow, field.key)"
                  class="drawer-select token-multi-select"
                  multiple
                  filterable
                  style="width: 100%;"
                  :disabled="isFieldLocked(editingRow, field)"
                  @change="onTokenMultiChange(editingRow, field.key, $event)"
                >
                  <template #tag>
                    <span class="target-selected-text token-multi-selected-text">
                      {{ tokenMultiText(editingRow, field.key) }}
                    </span>
                  </template>
                  <el-option v-for="item in tokenMultiOptions(field.key)" :key="item" :label="item" :value="item" />
                </el-select>
                <SerumUserSelect
                  v-else-if="isUserField(field)"
                  v-model="editingRow[field.key]"
                  :options="usedUserOptions(field)"
                  :placeholder="`选择${field.label}`"
                  :disabled="isFieldLocked(editingRow, field)"
                  clearable
                  @change="persistRow(editingRow, field.key)"
                />
                <el-select
                  v-else-if="field.type === 'select' || field.type === 'yesno' || field.type === 'status'"
                  :model-value="drawerFieldValue(field, editingRow)"
                  class="drawer-select"
                  :class="drawerSelectClass(field, editingRow)"
                  :clearable="!isRequiredStatusField(field)"
                  :filterable="!isDirectChoiceField(field)"
                  default-first-option
                  style="width: 100%;"
                  :disabled="isFieldLocked(editingRow, field)"
                  @change="onDrawerSelectChange(editingRow, field, $event)"
                >
                  <el-option
                    v-for="item in fieldOptions(field, editingRow)"
                    :key="item"
                    :label="item"
                    :value="item"
                  />
                </el-select>
                <el-input
                  v-else-if="field.type === 'age'"
                  :model-value="mouseAgeWeeksValue(editingRow)"
                  :disabled="isFieldLocked(editingRow, field)"
                  @focus="beginMouseAgeWeeksEdit(editingRow)"
                  @update:model-value="onMouseAgeWeeksInput(editingRow, $event)"
                  @blur="finishMouseAgeWeeksEdit(editingRow, field.key)"
                />
                <el-input
                  v-else-if="field.type === 'textarea'"
                  v-model="editingRow[field.key]"
                  type="textarea"
                  :autosize="{ minRows: 1, maxRows: 4 }"
                  :maxlength="field.maxlength"
                  :disabled="isFieldLocked(editingRow, field)"
                  @blur="persistRow(editingRow, field.key)"
                />
                <span v-else-if="field.key === 'sort_order' && isQueueTerminalRow(editingRow)">-</span>
                <el-input
                  v-else
                  v-model="editingRow[field.key]"
                  :type="field.key === 'sort_order' ? 'number' : 'text'"
                  :min="field.key === 'sort_order' ? 1 : undefined"
                  :maxlength="field.maxlength"
                  :disabled="isFieldLocked(editingRow, field)"
                  @blur="persistRow(editingRow, field.key)"
                />
              </el-form-item>
            </div>
          </article>
        </el-form>
      </fieldset>
    </el-drawer>

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
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus'
import { VxeInput, VxeSelect } from 'vxe-pc-ui'
import { VxeColumn, VxeTable } from 'vxe-table'

import '#/adapter/vxe-table'
import 'vxe-pc-ui/styles/cssvar.scss'
import 'vxe-table/styles/cssvar.scss'

import AdvancedOpsBar from '#/components/AdvancedOpsBar.vue'
import {
  coerceRequiredPositiveInt,
  coerceWorkbenchViewMode,
  createColumnOrder,
  EXCEL_VIEW,
  WORKBENCH_VIEW,
  syncDrawerControlTooltip,
  workbenchExcelMixin,
} from '#/components/workbench'
import WorkbenchViewToggle from '#/components/workbench/WorkbenchViewToggle.vue'
import { notifyApiError } from '#/api/errors'
import { fetchSerumTargetOptions } from '#/api/serum'
import {
  copyWorkbench,
  deleteWorkbench,
  exportWorkbenchList,
  fetchWorkbenchList,
  fetchWorkbenchOptions,
  reorderWorkbench,
  saveWorkbench,
  saveWorkbenchBatch,
  unlistWorkbench,
} from '#/api/serumWorkbench'
import {
  canAccessSerumDetail,
  canEditWorkbench,
  canEditWorkbenchDraft,
  canEditWorkbenchSupport,
  canOpenSerumEdit,
  getSerumUserName,
} from '#/utils/serumPermission'
import { SERUM_MOUSE_STRAIN_CATEGORY_OPTIONS } from '#/utils/serumMouseOptions'
import { WORKBENCH_STUDY_TYPE_OPTIONS } from '#/utils/workbenchStudyTypes'
import {
  WORKBENCH_PLAN_STATUS_OPTIONS,
  WORKBENCH_PRIORITY_OPTIONS,
  canonicalizeWorkbenchPriority,
  getTiterPriorityTone,
  getWorkbenchDisplayStatusTagType,
} from '#/utils/serumProjectStatus'
import {
  getCachedSerumUserOptions,
  loadSerumUserOptions,
} from '#/utils/serumUserOptions'
import { downloadListExcel, excelTimestamp } from '#/utils/downloadExcel'
import { SERUM_ERRORS } from '../shared/errors'
import SerumUserSelect from '../shared/SerumUserSelect.vue'
import WorkbenchStatusEditor from '#/components/workbench/WorkbenchStatusEditor.vue'
import WorkbenchTargetSelect from '#/components/workbench/WorkbenchTargetSelect.vue'
import WorkbenchRowActions from './WorkbenchRowActions.vue'

const PLAN_STATUS_OPTIONS = [...WORKBENCH_PLAN_STATUS_OPTIONS]
const PRIORITY_OPTIONS = [...WORKBENCH_PRIORITY_OPTIONS]
const REVIEW_STATUS_OPTIONS = ['未审', '已通过', '驳回']
const MOUSE_STATUS_OPTIONS = ['未定', '扩繁中', '可运', '在途', '已到']
const ZYGOSITY_OPTIONS = ['纯合', '杂合', '混合']
const STUDY_TYPE_OPTIONS = [...WORKBENCH_STUDY_TYPE_OPTIONS]
const MOUSE_STRAIN_CATEGORY_OPTIONS = [...SERUM_MOUSE_STRAIN_CATEGORY_OPTIONS]
const SPECIES_CROSS_OPTIONS = ['人', '猴', '鼠', '狗', '猫', '空白']
const IMMUNO_METHOD_OPTIONS = ['蛋白', 'DNA', 'LNP', '细胞', '混合']
const TOKEN_MULTI_OPTIONS = {
  species_cross: SPECIES_CROSS_OPTIONS,
  immuno_method: IMMUNO_METHOD_OPTIONS,
}
const ANTIGEN_SOURCE_OPTIONS = ['内部制备', '外购', '客户提供']
const CELL_PREP_OPTIONS = ['未开始', '进行中', '已完成', '不需要']
const MOUSE_REGION_OPTIONS = ['北京', '海门', '客户']
const YES_NO_OPTIONS = ['是', '否']
const REQUIRED_STATUS_DEFAULTS = Object.freeze({
  priority: '正常',
  plan_status: '草稿',
  can_start: '否',
  review_status: '未审',
  mouse_status: '未定',
  antigen_ready: '否',
})
const REQUIRED_STATUS_FIELD_KEYS = new Set(Object.keys(REQUIRED_STATUS_DEFAULTS))
const QUEUE_TERMINAL_PLAN_STATUSES = ['已取消', '小鼠KO致死']
const QUEUE_TERMINAL_PROJECT_STATUSES = ['结题', '无效价处死']
const USER_FIELD_KEYS = new Set(['pm', 'owner'])
const DATE_FIELD_KEYS = new Set(['mouse_birth_date', 'mouse_arrive_date', 'antigen_eta'])
const ALIGNED_FIELDS = new Set([
  'experiment_id',
  'project_code',
  'project_name',
  'project_purpose',
  'start_date',
  'immunization_interval',
  'target_codes',
  'target_name',
  'target_type',
  'target_size',
  'owner',
  'pm',
  'study_type',
  'assay_method',
  'facs_plate_count',
  'elisa_plate_count',
  'remark',
  'mouse_strain',
  'mouse_strain_category',
])
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
const EDITOR_SECTIONS = [
  {
    title: '队列 / 状态',
    queue: true,
    fields: [
      { key: 'priority', label: '优先级', type: 'select', optionsKey: 'priority', tone: 'priority' },
      { key: 'plan_status', label: '状态', type: 'status', optionsKey: 'plan_status', tone: 'status', lock: 'aligned' },
      { key: 'can_start', label: '可开展', type: 'yesno', tone: 'yesno' },
      { key: 'sort_order', label: '排序', type: 'text' },
      { key: 'reviewer', label: '审核人', type: 'text', maxlength: 64 },
      { key: 'review_status', label: '审核结果', type: 'select', optionsKey: 'review_status', tone: 'review' },
    ],
  },
  {
    title: '身份',
    fields: [
      { key: 'project_code', label: '项目编号', type: 'text' },
      { key: 'project_set_code', label: '项目集编号', type: 'text' },
      { key: 'pm', label: 'PM', type: 'select', optionsKey: 'pms', lock: 'aligned' },
      { key: 'owner', label: '开展人', type: 'select', optionsKey: 'owners', lock: 'aligned' },
      { key: 'target', label: '靶点', type: 'target', lock: 'aligned', wide: true },
      { key: 'target_codes', label: '靶点编号', type: 'target_codes', lock: 'aligned', wide: true },
    ],
  },
  {
    title: '方案要点',
    fields: [
      { key: 'study_type', label: '课题类型', type: 'select', optionsKey: 'study_type', lock: 'aligned' },
      { key: 'immuno_method', label: '免疫方式', type: 'multi' },
      { key: 'mouse_strain_category', label: '归类鼠型', type: 'select', optionsKey: 'mouse_strain_category', lock: 'aligned' },
      { key: 'mouse_strain', label: '小鼠品系', type: 'text', lock: 'aligned' },
      { key: 'species_cross', label: '种属交叉', type: 'multi', wide: true },
      { key: 'remark', label: '备注', type: 'textarea', maxlength: 255, lock: 'aligned', wide: true },
    ],
  },
  {
    title: '小鼠后勤',
    fields: [
      { key: 'mouse_scheme_no', label: '小鼠方案号', type: 'text' },
      { key: 'mouse_count', label: '数量', type: 'text' },
      { key: 'mouse_zygosity', label: '纯合/杂合', type: 'select', optionsKey: 'mouse_zygosity' },
      { key: 'mouse_birth_date', label: '出生日期', type: 'date' },
      { key: 'mouse_age_weeks', label: '周龄', type: 'age' },
      { key: 'mouse_region', label: '提供地区', type: 'select', optionsKey: 'mouse_region' },
      { key: 'mouse_room', label: '房间号', type: 'text' },
      { key: 'mouse_status', label: '运输状态', type: 'select', optionsKey: 'mouse_status', tone: 'mouse' },
      { key: 'mouse_arrive_date', label: '到鼠时间', type: 'date' },
      { key: 'mouse_expand_requested', label: '代下扩繁', type: 'yesno' },
      { key: 'mouse_remark', label: '小鼠备注', type: 'textarea', maxlength: 255, wide: true },
    ],
  },
  {
    title: '抗原',
    fields: [
      { key: 'antigen_source', label: '抗原来源', type: 'select', optionsKey: 'antigen_source' },
      { key: 'antigen_ready', label: '抗原到货', type: 'yesno', tone: 'yesno' },
      { key: 'antigen_eta', label: '抗原预计日', type: 'date' },
      { key: 'lnp_ordered', label: 'LNP下单', type: 'yesno' },
      { key: 'cell_prep_status', label: '冲击细胞', type: 'select', optionsKey: 'cell_prep_status' },
      { key: 'antigen_remark', label: '抗原备注', type: 'textarea', maxlength: 255, wide: true },
    ],
  },
]
const STATUS_VIEWS = [
  { key: '', label: '全部项目', hint: '查看完整工作队列', valueKey: 'all', tone: 'all', step: 'ALL' },
  { key: 'planned', label: '计划中', hint: '尚未正式开展', valueKey: 'planned', tone: 'planned', step: '01' },
  { key: 'ongoing', label: '进行中', hint: '实验正在推进', valueKey: 'ongoing', tone: 'ongoing', step: '02' },
  { key: 'completed', label: '已完成', hint: '结题或终止实验', valueKey: 'completed', tone: 'completed', step: '03' },
  { key: 'cancelled', label: '已取消', hint: '未开展即关闭', valueKey: 'cancelled', tone: 'cancelled', step: '04' },
]
const SHEET_COLUMNS = [
  { key: 'sort_order', label: '排序', width: 50, edit: 'text' },
  { key: 'priority', label: '优先级', width: 90, edit: 'select', optionsKey: 'priority' },
  { key: 'target_name', label: '靶点名称', edit: 'target' },
  { key: 'target_codes', label: '靶点编号', edit: 'target' },
  { key: 'pm', label: 'PM', width: 90, edit: 'select', optionsKey: 'pms' },
  { key: 'project_set_code', label: '项目集编号', edit: 'text' },
  { key: 'project_code', label: '免疫项目号', edit: 'text' },
  { key: 'study_type', label: '课题类型', edit: 'select', optionsKey: 'study_type' },
  { key: 'species_cross', label: '种属交叉', edit: 'multi', minWidth: 160 },
  { key: 'owner', label: '开展人', width: 90, edit: 'select', optionsKey: 'owners' },
  { key: 'reviewer', label: '审核人', width: 90, edit: 'text' },
  { key: 'review_status', label: '审核结果', width: 90, edit: 'select', optionsKey: 'review_status' },
  { key: 'immuno_method', label: '免疫方式', edit: 'multi', minWidth: 140 },
  { key: 'remark', label: '备注', edit: 'text' },
  { key: 'mouse_scheme_no', label: '小鼠方案号', edit: 'text' },
  { key: 'mouse_strain_category', label: '归类鼠型', edit: 'select', optionsKey: 'mouse_strain_category' },
  { key: 'mouse_strain', label: '小鼠品系', edit: 'text' },
  { key: 'mouse_count', label: '数量', width: 80, edit: 'text' },
  { key: 'mouse_zygosity', label: '纯合/杂合', width: 90, edit: 'select', optionsKey: 'mouse_zygosity' },
  { key: 'mouse_birth_date', label: '出生日期', width: 110, edit: 'date' },
  { key: 'mouse_age_weeks', label: '周龄', width: 80, edit: 'text' },
  { key: 'mouse_region', label: '提供地区', edit: 'select', optionsKey: 'mouse_region' },
  { key: 'mouse_room', label: '房间号', width: 90, edit: 'text' },
  { key: 'mouse_status', label: '小鼠运输', width: 90, edit: 'select', optionsKey: 'mouse_status' },
  { key: 'mouse_arrive_date', label: '到鼠时间', width: 110, edit: 'date' },
  { key: 'mouse_remark', label: '小鼠备注', edit: 'text', minWidth: 160 },
  { key: 'antigen_source', label: '抗原来源', edit: 'select', optionsKey: 'antigen_source' },
  { key: 'antigen_ready', label: '抗原到货', width: 110, edit: 'select', optionsKey: 'yesno' },
  { key: 'antigen_eta', label: '抗原预计日', width: 110, edit: 'date' },
  { key: 'mouse_expand_requested', label: '代下扩繁', width: 110, edit: 'select', optionsKey: 'yesno' },
  { key: 'lnp_ordered', label: 'LNP下单', width: 110, edit: 'select', optionsKey: 'yesno' },
  { key: 'cell_prep_status', label: '冲击细胞', edit: 'select', optionsKey: 'cell_prep_status' },
  { key: 'antigen_remark', label: '抗原备注', edit: 'text', minWidth: 160 },
  { key: 'can_start', label: '可否开展', width: 100, edit: 'select', optionsKey: 'yesno' },
  { key: 'plan_status', label: '状态', width: 110, edit: 'select', optionsKey: 'plan_status' },
  { key: 'experiment_id', label: '实验号', width: 190, edit: 'readonly' },
]
const SHEET_COLUMN_ORDER = createColumnOrder('workbenchSheetColumnOrder', SHEET_COLUMNS)
let lastViewMode = WORKBENCH_VIEW
const SHEET_HEADER_ALIASES = Object.freeze({
  排序: 'sort_order',
  序号: 'sort_order',
  优先级排序: 'sort_order',
  项目编号: 'project_code',
  运输状态: 'mouse_status',
  抗原到货情况: 'antigen_ready',
  是否代下扩繁: 'mouse_expand_requested',
  LNP是否下单: 'lnp_ordered',
  冲击细胞准备: 'cell_prep_status',
  是否可开展: 'can_start',
})
export default {
  name: 'SerumWorkbench',
  mixins: [workbenchExcelMixin],
  components: {
    AdvancedOpsBar,
    WorkbenchViewToggle,
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
    ElTable,
    ElTableColumn,
    ElTag,
    Search,
    SerumUserSelect,
    Tools,
    VxeColumn,
    VxeInput,
    VxeSelect,
    VxeTable,
    WorkbenchRowActions,
    WorkbenchStatusEditor,
    WorkbenchTargetSelect,
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
      stats: { all: 0, planned: 0, ongoing: 0, completed: 0, cancelled: 0, can_start: 0 },
      viewMode: coerceWorkbenchViewMode(lastViewMode),
      showAdvancedOps: false,
      drawerVisible: false,
      editingId: null,
      editingRowData: null,
      ageEditingRowId: null,
      sortEditingId: null,
      sortInputRefs: {},
      sortable: null,
      sortableInitToken: 0,
      targetOptions: [],
      targetLoading: false,
      targetRequestToken: 0,
      allUserOptions: getCachedSerumUserOptions(),
      listRequestToken: 0,
      pendingDrawerSaves: new Set(),
      rowSaveChains: new Map(),
      rowBaselines: new Map(),
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
        view_group: null,
        sort_field: '',
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
        pms: [],
        owners: [],
        reviewers: [],
        study_type: [...STUDY_TYPE_OPTIONS],
        mouse_strain: [],
        mouse_strain_category: [...MOUSE_STRAIN_CATEGORY_OPTIONS],
        antigen_source: [...ANTIGEN_SOURCE_OPTIONS],
        cell_prep_status: [...CELL_PREP_OPTIONS],
        mouse_region: [...MOUSE_REGION_OPTIONS],
        mouse_status: [...MOUSE_STATUS_OPTIONS],
        mouse_zygosity: [...ZYGOSITY_OPTIONS],
        review_status: [...REVIEW_STATUS_OPTIONS],
        statuses: [...PLAN_STATUS_OPTIONS],
        priority: [...PRIORITY_OPTIONS],
        yesno: [...YES_NO_OPTIONS],
        plan_status: [...PLAN_STATUS_OPTIONS],
      },
      yesNoOptions: YES_NO_OPTIONS,
      editorSections: EDITOR_SECTIONS,
      statusViews: STATUS_VIEWS,
      sheetColumns: SHEET_COLUMN_ORDER.load(),
    }
  },
  computed: {
    canFullEdit() {
      return canEditWorkbench(this.userStore.userInfo || {})
    },
    canDraftEdit() {
      return canEditWorkbenchDraft(this.userStore.userInfo || {})
    },
    canSupportEdit() {
      return canEditWorkbenchSupport(this.userStore.userInfo || {})
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
    planStatusOptions() {
      return PLAN_STATUS_OPTIONS.filter((item) => item !== '已开展')
    },
    activeViewGroup() {
      return this.listQuery.view_group || ''
    },
    hasSecondaryFilters() {
      return [
        'keyword',
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
      ].some((key) => Boolean(this.listQuery[key]))
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
        this.codesText(row),
        this.editingIndex < 0 ? '当前筛选结果外' : '',
      ].filter(Boolean).join(' · ')
    },
    sheetTargetSelectOptions() {
      return this.targetOptions.map((item) => ({
        label: `${item.name}（${item.snum}）`,
        value: item.snum,
      }))
    },
  },
  watch: {
    viewMode(value) {
      lastViewMode = coerceWorkbenchViewMode(value)
      if (value === 'workbench') {
        this.scheduleSortable()
      } else {
        this.destroySortable()
        this.loadAllUserOptions()
      }
    },
    drawerVisible(open) {
      if (!open) {
        this.rememberDrawerSave(this.flushDirtyEditor())
        this.ageEditingRowId = null
        this.editingId = null
        this.editingRowData = null
      }
    },
  },
  created() {
    this.loadFilterOptions()
    this.getList()
    if (this.isExcelMode) this.loadAllUserOptions()
  },
  mounted() {
    this.scheduleSortable()
    document.addEventListener('mousedown', this.onDocumentPointerDown, true)
  },
  beforeUnmount() {
    this.destroySortable()
    document.removeEventListener('mousedown', this.onDocumentPointerDown, true)
  },
  activated() {
    document.addEventListener('mousedown', this.onDocumentPointerDown, true)
    if (this.loading) return
    this.getList()
  },
  deactivated() {
    this.closeEditor()
    this.destroySortable()
    document.removeEventListener('mousedown', this.onDocumentPointerDown, true)
  },
  methods: {
    async toggleViewMode() {
      if (this.isExcelMode && !await this.flushPendingSheetEdits()) return
      this.viewMode = this.isExcelMode ? WORKBENCH_VIEW : EXCEL_VIEW
    },
    async resetSheetColumnOrder() {
      if (this.isExcelMode && !await this.flushPendingSheetEdits()) return
      SHEET_COLUMN_ORDER.clear()
      this.sheetColumns = [...SHEET_COLUMNS]
      this.persistSheetColumnOrder(this.sheetColumns)
      this.clearSheetRange()
    },
    persistSheetColumnOrder(columns) {
      SHEET_COLUMN_ORDER.save(columns)
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
    async loadAllUserOptions() {
      try {
        this.allUserOptions = await loadSerumUserOptions()
      } catch {
        this.allUserOptions = []
      }
    },
    uniq(values) {
      return [...new Set((values || []).map((item) => String(item || '').trim()).filter(Boolean))]
    },
    async loadFilterOptions() {
      try {
        const data = await fetchWorkbenchOptions()
        this.optionLists.pms = this.uniq(data?.pms || [])
        this.optionLists.owners = this.uniq(data?.owners || [])
        this.optionLists.reviewers = this.uniq(data?.reviewers || [])
        this.optionLists.statuses = this.uniq([
          ...PLAN_STATUS_OPTIONS,
          '已开展',
          ...(data?.statuses || []),
        ])
        this.optionLists.mouse_strain = this.uniq(data?.mouse_strains || [])
        this.optionLists.mouse_strain_category = this.uniq([
          ...MOUSE_STRAIN_CATEGORY_OPTIONS,
          ...(data?.mouse_strain_categories || []),
        ])
      } catch {
        // 选项加载失败时仍可用本地预设
      }
    },
    isUserField(field) {
      return USER_FIELD_KEYS.has(field?.key)
    },
    usedUserOptions(field) {
      const optionKey = field?.optionsKey || `${field?.key || ''}s`
      const values = [
        ...(this.optionLists[optionKey] || []),
        this.editingRow?.[field?.key],
      ]
      return this.uniq(values)
    },
    fieldOptions(field, row = null) {
      if (field.type === 'yesno') return this.optionLists.yesno
      if (field.type === 'multi') return this.tokenMultiOptions(field.key)
      if (field.key === 'study_type') return STUDY_TYPE_OPTIONS
      if (field.key === 'mouse_strain_category') return MOUSE_STRAIN_CATEGORY_OPTIONS
      if (field.key === 'mouse_region') return MOUSE_REGION_OPTIONS
      if (field.key === 'mouse_zygosity') return ZYGOSITY_OPTIONS
      if (field.key === 'antigen_source') return ANTIGEN_SOURCE_OPTIONS
      if (field.type === 'status' || field.optionsKey === 'plan_status') {
        if (row?.aligned_locked && row.display_status) return [row.display_status]
        return this.planStatusOptions
      }
      return this.mergedOptions(field.optionsKey || field.key)
    },
    isTokenMultiKey(key) {
      return Boolean(TOKEN_MULTI_OPTIONS[key])
    },
    isMultiSelectColumn(column) {
      return column?.edit === 'multi' || this.isTokenMultiKey(column?.key)
    },
    tokenMultiOptions(key) {
      return TOKEN_MULTI_OPTIONS[key] || []
    },
    normalizeTokenMulti(key, values) {
      const options = this.tokenMultiOptions(key)
      const raw = (Array.isArray(values) ? values : [values]).map((item) => String(item || '').trim()).filter(Boolean)
      if (!raw.length) return []
      if (raw.some((item) => !options.includes(item))) return []
      return options.filter((item) => raw.includes(item))
    },
    splitTokenMulti(key, value) {
      if (Array.isArray(value)) return this.normalizeTokenMulti(key, value)
      const text = String(value || '').trim()
      if (!text) return []
      return this.normalizeTokenMulti(
        key,
        text.split(/[,，]/).map((item) => item.trim()).filter(Boolean),
      )
    },
    joinTokenMulti(key, values) {
      return this.normalizeTokenMulti(key, values).join(',')
    },
    tokenMultiList(row, key) {
      return this.splitTokenMulti(key, row?.[key])
    },
    tokenMultiText(row, key) {
      return this.tokenMultiList(row, key).join('，')
    },
    onTokenMultiChange(row, key, values) {
      row[key] = this.normalizeTokenMulti(key, values)
      this.persistRow(row, key)
    },
    async searchTargetOptions(keyword, selectedCodes) {
      const requestToken = ++this.targetRequestToken
      this.targetLoading = true
      try {
        const codes = Array.isArray(selectedCodes)
          ? selectedCodes
          : (Array.isArray(this.editingRow?.target_codes) ? this.editingRow.target_codes : [])
        const data = await fetchSerumTargetOptions(keyword || '', codes)
        if (requestToken !== this.targetRequestToken) return
        this.targetOptions = data?.items || []
      } catch {
        if (requestToken === this.targetRequestToken) {
          this.targetOptions = this.targetOptions || []
        }
      } finally {
        if (requestToken === this.targetRequestToken) this.targetLoading = false
      }
    },
    mergeTargetOptions(items) {
      const map = new Map((this.targetOptions || []).map((item) => [item.snum, item]))
      items.forEach((item) => {
        if (item?.snum) map.set(item.snum, item)
      })
      this.targetOptions = [...map.values()]
    },
    onDrawerTargetChange(row, payload) {
      row.target_codes = payload.codes
      row.target_name = payload.name
      this.mergeTargetOptions(payload.items)
      this.saveRow(row, { fields: ['target_codes', 'target_name'] })
    },
    mergedOptions(key) {
      const base = this.optionLists[key] || []
      const extra = this.list.map((row) => row[key]).filter(Boolean)
      return this.uniq([...base, ...extra])
    },
    isDraftRow(row) {
      return !row?.aligned_locked && String(row?.plan_status || '草稿').trim() === '草稿'
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
    isFieldLocked(row, field) {
      if (!this.canEditField(row, field.key)) return true
      return field.lock === 'aligned' && row.aligned_locked
    },
    drawerSelectClass(field, row) {
      if (field.tone === 'status' || field.type === 'status') {
        return `status-select status-tone-${this.statusTagType(row)}`
      }
      if (field.tone === 'priority' || field.key === 'priority') {
        return `priority-select status-tone-${this.priorityTone(row)}`
      }
      if (field.tone === 'yesno' || field.type === 'yesno') {
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
    isRequiredStatusField(field) {
      return REQUIRED_STATUS_FIELD_KEYS.has(field?.key)
    },
    isDirectChoiceField(field) {
      return this.isRequiredStatusField(field)
        || field?.type === 'yesno'
        || field?.key === 'study_type'
        || field?.key === 'mouse_strain_category'
        || field?.key === 'mouse_zygosity'
        || field?.key === 'mouse_region'
        || field?.key === 'antigen_source'
        || field?.key === 'cell_prep_status'
    },
    drawerFieldValue(field, row) {
      if (field?.key === 'plan_status' && row?.aligned_locked) {
        return row.display_status || row.plan_status
      }
      return row?.[field?.key]
    },
    syncDrawerControlTooltip,
    onDrawerSelectChange(row, field, value) {
      if (this.isFieldLocked(row, field)) return
      row[field.key] = value
      this.persistRow(row, field.key)
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
    workbenchRowClassName({ row }) {
      return row?.id === this.editingId ? 'is-editing' : ''
    },
    rowPriority(row) {
      return canonicalizeWorkbenchPriority(row?.priority)
    },
    priorityTone(row) {
      return getTiterPriorityTone(this.rowPriority(row))
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
    async persistRow(row, field) {
      if (!this.canEditField(row, field)) return
      if (field === 'plan_status' && row.plan_status === '已开展') {
        ElMessage.warning('请到方案草稿页核对方案后再开展')
        await this.getList({ flushEditor: false })
        return
      }
      if (field === 'review_status') {
        row.reviewer = getSerumUserName(this.userStore.userInfo || {}) || ''
      }
      return this.saveRow(row, {
        fields: field === 'review_status' ? ['review_status', 'reviewer'] : [field],
        resort: field === 'sort_order' || field === 'priority',
      })
    },
    formatCodesText(value) {
      return Array.isArray(value) ? value.join(',') : (value || '')
    },
    codesText(row) {
      return this.formatCodesText(row?.target_codes)
    },
    parseCodes(text) {
      return String(text || '')
        .split(/[,，]/)
        .map((item) => item.trim())
        .filter(Boolean)
    },
    openEditor(row) {
      if (!row?.id) return
      if (this.drawerVisible && this.editingId === row.id) {
        this.closeEditor()
        return
      }
      if (this.editingId) {
        this.rememberDrawerSave(this.flushDirtyEditor())
      }
      this.ageEditingRowId = null
      this.editingId = row.id
      this.editingRowData = this.normalizeRow(JSON.parse(JSON.stringify(row)))
      if (!this.rowBaselines.has(row.id)) this.updateRowBaseline(this.editingRowData)
      this.drawerVisible = true
      this.searchTargetOptions('')
    },
    closeEditor() {
      this.rememberDrawerSave(this.flushDirtyEditor())
      this.ageEditingRowId = null
      this.drawerVisible = false
      this.editingId = null
      this.editingRowData = null
    },
    rememberDrawerSave(savePromise) {
      if (!savePromise) return null
      const pending = Promise.resolve(savePromise).finally(() => {
        this.pendingDrawerSaves.delete(pending)
      })
      this.pendingDrawerSaves.add(pending)
      return pending
    },
    drawerComparableValue(field, value) {
      if (field === 'target_codes') {
        return JSON.stringify(Array.isArray(value) ? value : this.parseCodes(value))
      }
      if (this.isTokenMultiKey(field)) {
        return this.joinTokenMulti(field, value)
      }
      return String(value ?? '')
    },
    drawerDirtyFields(row) {
      const baseline = this.rowBaselines.get(row?.id)
      if (!row || !baseline) return []
      const fields = this.editorSections
        .flatMap((section) => section.fields)
        .filter((field) => field.key !== 'target')
        .filter((field) => this.canEditField(row, field.key))
        .map((field) => field.key)
      const dirty = [...new Set(fields)].filter(
        (field) => this.drawerComparableValue(field, row[field])
          !== this.drawerComparableValue(field, baseline[field]),
      )
      if (dirty.includes('target_codes') && !dirty.includes('target_name')) {
        dirty.push('target_name')
      }
      return dirty
    },
    flushDirtyEditor() {
      const row = this.editingRowData
      const activeElement = document.activeElement
      if (!row) return null
      if (activeElement instanceof Element) {
        const fieldElement = activeElement.closest('.drawer-field[data-field-key]')
        const fieldKey = fieldElement?.getAttribute('data-field-key')
        const field = this.editorSections
          .flatMap((section) => section.fields)
          .find((item) => item.key === fieldKey)
        if (field?.type === 'date' && activeElement instanceof HTMLInputElement) {
          const value = activeElement.value.trim()
          if (!value || /^\d{4}-\d{2}-\d{2}$/.test(value)) {
            row[field.key] = value || null
          }
        }
      }
      const fields = this.drawerDirtyFields(row)
      if (!fields.length) return null
      this.ageEditingRowId = null
      return this.saveRow(row, {
        fields,
        resort: fields.includes('sort_order') || fields.includes('priority'),
      })
    },
    async flushEditorForAction(row) {
      if (!row?.id) return true
      if (!await this.flushPendingSheetEdits()) return false
      if (this.editingId === row.id) {
        const savePromise = this.rememberDrawerSave(this.flushDirtyEditor())
        if (savePromise) return Boolean(await savePromise)
      }
      const pending = this.rowSaveChains.get(row.id)
      if (!pending) return true
      try {
        await pending
        return true
      } catch {
        return false
      }
    },
    onDocumentPointerDown(event) {
      if (!this.drawerVisible) return
      const target = event.target
      if (!(target instanceof Element)) return
      if (target.closest('.el-drawer, .el-popper, .el-select-dropdown, .el-picker-panel, .el-message-box, .el-overlay-message-box')) {
        return
      }
      if (target.closest('.el-table__row, .vxe-body--row, .action-cell, .sort-cell')) {
        return
      }
      this.closeEditor()
    },
    onWorkbenchRowClick(row, _column, event) {
      if (event?.target?.closest?.('.el-button, .el-input, .el-select, .sort-cell, .action-cell')) {
        return
      }
      this.openEditor(row)
    },
    onWorkbenchRowContextMenu(_row, _column, event) {
      if (!this.drawerVisible) return
      event?.preventDefault?.()
      event?.stopPropagation?.()
      this.closeEditor()
    },
    shiftEditor(delta) {
      const next = this.list[this.editingIndex + delta]
      if (next) this.openEditor(next)
    },
    bindSortInput(id, el) {
      if (el) this.sortInputRefs[id] = el
      else delete this.sortInputRefs[id]
    },
    isQueueTerminalRow(row) {
      const plan = String(row?.plan_status || '').trim()
      if (QUEUE_TERMINAL_PLAN_STATUSES.includes(plan)) return true
      const projectStatus = String(row?.display_status || row?.project_status || '').trim()
      return Boolean(row?.aligned_locked && QUEUE_TERMINAL_PROJECT_STATUSES.includes(projectStatus))
    },
    startSortEdit(row) {
      if (!this.canEditSortCell(row) || !row?.id) return
      this.sortEditingId = row.id
      this.$nextTick(() => {
        const input = this.sortInputRefs[row.id]
        input?.focus?.()
        const native = input?.input || input?.$el?.querySelector?.('input')
        native?.select?.()
      })
    },
    finishSortEdit(row) {
      if (this.sortEditingId !== row.id) return
      this.sortEditingId = null
      this.saveRow(row, { fields: ['sort_order'], resort: true })
    },
    formatCodes({ cellValue }) {
      return this.formatCodesText(cellValue)
    },
    formatPlanStatus({ row, cellValue }) {
      return row?.display_status || cellValue || ''
    },
    formatTokenMultiCell({ column, cellValue }) {
      return this.splitTokenMulti(column?.field, cellValue).join('，')
    },
    sheetFormatter(column) {
      if (column.key === 'sort_order') return this.formatSortColumnCell
      if (column.key === 'target_codes') return this.formatCodes
      if (column.key === 'plan_status') return this.formatPlanStatus
      if (this.isTokenMultiKey(column.key)) return this.formatTokenMultiCell
      if (column.key === 'mouse_age_weeks') return this.formatMouseAgeWeeks
      return undefined
    },
    formatMouseAgeWeeks({ row, cellValue }) {
      return this.mouseAgeWeeksValue(row, cellValue)
    },
    sheetSelectOptions(column) {
      const key = column.optionsKey === 'plan_status' ? 'plan_status' : (column.optionsKey || column.key)
      if (key === 'plan_status') return this.planStatusOptions
      if (key === 'priority') return [...PRIORITY_OPTIONS]
      if (key === 'study_type') return [...STUDY_TYPE_OPTIONS]
      if (key === 'mouse_strain_category') return [...MOUSE_STRAIN_CATEGORY_OPTIONS]
      if (key === 'mouse_region') return [...MOUSE_REGION_OPTIONS]
      if (key === 'mouse_zygosity') return [...ZYGOSITY_OPTIONS]
      if (key === 'antigen_source') return [...ANTIGEN_SOURCE_OPTIONS]
      if (this.isMultiSelectColumn(column)) return this.tokenMultiOptions(key)
      if (this.isUserField(column)) {
        return this.uniq([
          ...this.usedUserOptions(column),
          ...this.allUserOptions,
        ])
      }
      return this.mergedOptions(key)
    },
    sheetChoiceSelectOptions(column) {
      return this.sheetSelectOptions(column).map((value) => ({ label: value, value }))
    },
    sheetChoiceDirectValue(row, column) {
      if (!this.isMultiSelectColumn(column)) return row[column.key]
      const value = row[column.key]
      return Array.isArray(value)
        ? this.normalizeTokenMulti(column.key, value).join('，')
        : String(value ?? '')
    },
    sheetPickerDisplayValue(row, column) {
      if (column.key === 'target_codes') return this.formatCodesText(row.target_codes)
      if (column.key === 'target_name') return row.target_name || ''
      if (column.key === 'plan_status') return row.plan_status || row.display_status || ''
      if (this.isMultiSelectColumn(column)) return this.splitTokenMulti(column.key, row[column.key]).join('，')
      if (column.key === 'sort_order') return this.formatSortColumn(row)
      return row[column.key] ?? ''
    },
    setSheetChoiceDirectValue(row, key, value) {
      row[key] = value
    },
    isSheetCellLocked(row, key) {
      if (key === 'sort_order' && !this.isQueueSorted) return true
      if (!this.canEditField(row, key)) return true
      const column = this.sheetColumns.find((item) => item.key === key)
      if (column?.edit === 'readonly') return true
      if (key === 'plan_status' && row.aligned_locked) return true
      if (key === 'project_code') return false
      return Boolean(row.aligned_locked && ALIGNED_FIELDS.has(key))
    },
    normalizeYesNo(text) {
      const raw = String(text || '').trim()
      return YES_NO_OPTIONS.includes(raw) ? raw : ''
    },
    normalizeSheetDate(text) {
      const raw = String(text ?? '').trim()
      if (!raw) return { ok: true, value: '' }
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
    coerceSheetValue(key, text) {
      const raw = String(text ?? '').trim()
      const column = this.sheetColumns.find((item) => item.key === key)
      if (!column) return { ok: false, reason: 'unknown' }
      if (['remark', 'mouse_remark', 'antigen_remark'].includes(key) && raw.length > 255) {
        return { ok: false, reason: 'length' }
      }
      if (key === 'reviewer' && raw.length > 64) {
        return { ok: false, reason: 'length' }
      }
      if (key === 'target_codes') return { ok: true, value: this.uniq(this.parseCodes(raw)) }
      if (DATE_FIELD_KEYS.has(key)) return this.normalizeSheetDate(raw)
      if (this.isTokenMultiKey(key)) {
        const next = this.splitTokenMulti(key, Array.isArray(text) ? text : raw)
        const empty = Array.isArray(text)
          ? text.every((item) => !String(item || '').trim())
          : raw === ''
        return next.length || empty ? { ok: true, value: next } : { ok: false, reason: 'option' }
      }
      if (key === 'sort_order') return coerceRequiredPositiveInt(raw)
      if (!raw && REQUIRED_STATUS_FIELD_KEYS.has(key)) {
        return { ok: false, reason: 'empty' }
      }
      if (key === 'plan_status') {
        if (raw === '已开展') return { ok: false, reason: 'started' }
        const options = this.planStatusOptions
        return options.includes(raw)
          ? { ok: true, value: raw }
          : { ok: false, reason: 'option' }
      }
      if (column.edit === 'select') {
        if (!raw) return { ok: true, value: '' }
        if (key === 'priority') {
          const canon = canonicalizeWorkbenchPriority(raw)
          if (PRIORITY_OPTIONS.includes(canon)) return { ok: true, value: canon }
          return { ok: false, reason: 'option' }
        }
        if (column.optionsKey === 'yesno') {
          const yn = this.normalizeYesNo(raw)
          return yn ? { ok: true, value: yn } : { ok: false, reason: 'option' }
        }
        const options = this.sheetSelectOptions(column)
        const hit = options.find((item) => item === raw || String(item).toLowerCase() === raw.toLowerCase())
        return hit ? { ok: true, value: hit } : { ok: false, reason: 'option' }
      }
      return { ok: true, value: raw }
    },
    assignSheetValue(row, key, text) {
      if (this.isSheetCellLocked(row, key)) return { ok: false, reason: 'locked' }
      const result = this.coerceSheetValue(key, text)
      if (!result.ok) return result
      row[key] = result.value
      return { ok: true }
    },
    sheetCellClassName({ row, column }) {
      const classes = []
      if (column.field === 'priority') classes.push(`sheet-tone-${this.priorityTone(row)}`)
      if (column.field === 'plan_status') classes.push(`sheet-tone-${this.statusTagType(row)}`)
      if (column.field === 'can_start' || column.field === 'antigen_ready') {
        classes.push(row[column.field] === '是' ? 'sheet-tone-success' : 'sheet-tone-info')
      }
      return classes.join(' ')
    },
    sheetDirectTextValue(row, key) {
      if (!row) return ''
      if (key === 'target_codes') return this.formatCodesText(row.target_codes)
      if (this.isTokenMultiKey(key)) {
        return Array.isArray(row[key])
          ? this.normalizeTokenMulti(key, row[key]).join('，')
          : String(row[key] ?? '')
      }
      if (key === 'plan_status') return String(row.display_status || row[key] || '')
      if (key === 'mouse_age_weeks') {
        const value = this.mouseAgeWeeksValue(row, row[key])
        return value == null ? '' : String(value)
      }
      if (row[key] === null || row[key] === undefined) return ''
      return String(row[key])
    },
    sameSheetValue(key, left, right) {
      if (key === 'target_codes') {
        const normalize = (value) => this.uniq(
          Array.isArray(value) ? value : this.parseCodes(value),
        )
        return JSON.stringify(normalize(left)) === JSON.stringify(normalize(right))
      }
      if (this.isTokenMultiKey(key)) {
        return JSON.stringify(this.splitTokenMulti(key, left))
          === JSON.stringify(this.splitTokenMulti(key, right))
      }
      return String(left ?? '').trim() === String(right ?? '').trim()
    },
    restoreSheetEditValue(row, key, value) {
      row[key] = this.cloneSheetValue(value)
    },
    sheetValidationMessage(key, reason) {
      const label = this.sheetColumns.find((item) => item.key === key)?.label || '当前字段'
      if (reason === 'date') return `${label}必须是 YYYY-MM-DD 格式的有效日期`
      if (reason === 'integer') return `${label}必须是大于 0 的整数`
      if (reason === 'empty') return `${label}不能为空`
      if (reason === 'locked') return `${label}当前不可编辑`
      if (reason === 'unknown') return '粘贴内容包含无法识别的列'
      if (reason === 'started') return '请到方案草稿页核对方案后再开展'
      if (reason === 'length') {
        return `${label}不能超过 ${key === 'reviewer' ? 64 : 255} 个字`
      }
      return `${label}必须与可选项完全匹配`
    },
    async resolveTargetCodes(codes) {
      const normalized = this.uniq(codes)
      if (!normalized.length) return { missing: [], nameByCode: new Map(), names: [] }
      const data = await fetchSerumTargetOptions('', normalized)
      const items = data?.items || []
      this.mergeTargetOptions(items)
      const nameByCode = new Map(items.map((item) => [item.snum, item.name]))
      return {
        missing: normalized.filter((code) => !nameByCode.has(code)),
        nameByCode,
        names: normalized.map((code) => nameByCode.get(code)),
      }
    },
    splitTargetNames(value) {
      return this.uniq(String(value || '').split(/[&＆]/))
    },
    async resolveTargetNames(value) {
      const names = this.splitTargetNames(value)
      if (!names.length) {
        return { ambiguous: [], itemByName: new Map(), items: [], missing: [] }
      }
      const results = await Promise.all(
        names.map(async (name) => {
          const data = await fetchSerumTargetOptions(name)
          const exact = (data?.items || []).filter(
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
    sheetTargetDirectValue(row, key) {
      return key === 'target_codes' ? this.formatCodesText(row.target_codes) : row.target_name
    },
    setSheetTargetDirectValue(row, key, value) {
      row[key] = value
    },
    querySheetTargetOptions({ searchValue }) {
      const row = this.list[this.pasteAnchor?.rowIndex]
      return this.searchTargetOptions(searchValue, row?.target_codes)
    },
    onSheetTargetPickerChange(row) {
      const codes = this.uniq(Array.isArray(row.target_codes) ? row.target_codes : [])
      row.target_codes = codes
      row.target_name = codes
        .map((code) => this.targetOptions.find((item) => item.snum === code)?.name || code)
        .join('&')
    },
    async finishSheetEdit({ row, column }) {
      const key = column?.field
      if (!key) return
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
        const baseline = this.rowBaselines.get(row.id)
        const originalCodes = originalRecord?.targetCodes ?? baseline?.target_codes ?? []
        const originalName = originalRecord?.targetName ?? baseline?.target_name ?? ''
        const codes = this.uniq(Array.isArray(row.target_codes) ? row.target_codes : [])
        const submittedName = String(row.target_name || '')
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
          return this.saveRow(row, { fields: ['target_codes', 'target_name'] })
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
      const result = this.coerceSheetValue(key, row[key])
      if (!result.ok) {
        this.restoreSheetEditValue(row, key, originalValue)
        ElMessage.warning(this.sheetValidationMessage(key, result.reason))
        return
      }
      if (this.sameSheetValue(key, result.value, originalValue)) {
        row[key] = this.cloneSheetValue(originalValue)
        return
      }
      row[key] = result.value
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
      } else if (key === 'target_name') {
        const submittedName = String(row.target_name || '').trim()
        const submittedCodes = this.cloneSheetValue(row.target_codes)
        try {
          const resolved = await this.resolveTargetNames(submittedName)
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
      if (key === 'review_status') return this.persistRow(row, key)
      const fields = key === 'target_codes' || key === 'target_name'
        ? ['target_codes', 'target_name']
        : [key]
      return this.saveRow(row, { fields, resort: key === 'sort_order' || key === 'priority' })
    },
    handleViewGroup(key) {
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
      this.handleFilter()
    },
    handleFilter() {
      this.listQuery.page = 1
      this.getList()
    },
    async handleListExport() {
      try {
        await downloadListExcel(
          () => exportWorkbenchList({ ...this.listQuery }),
          `免疫工作台列表_${excelTimestamp()}.xlsx`,
        )
      } catch (error) {
        notifyApiError(error, { messages: SERUM_ERRORS.workbench.exportList })
      }
    },
    async getList({ flushEditor = true } = {}) {
      if (flushEditor) {
        await this.flushPendingSheetEdits()
        await this.rememberDrawerSave(this.flushDirtyEditor())
        if (this.pendingDrawerSaves.size) {
          await Promise.all([...this.pendingDrawerSaves])
        }
        if (this.rowSaveChains.size) {
          await Promise.allSettled([...this.rowSaveChains.values()])
        }
      }
      const requestToken = ++this.listRequestToken
      this.loading = true
      try {
        const data = await fetchWorkbenchList({ ...this.listQuery })
        if (requestToken !== this.listRequestToken) return
        this.list = (data?.items || []).map((row) => this.normalizeRow(row))
        this.list.forEach((row) => this.updateRowBaseline(row))
        this.total = data?.total || 0
        this.stats = {
          all: data?.stats?.all || 0,
          planned: data?.stats?.planned || 0,
          ongoing: data?.stats?.ongoing || 0,
          completed: data?.stats?.completed || 0,
          cancelled: data?.stats?.cancelled || 0,
          can_start: data?.stats?.can_start || 0,
        }
        const selected = this.list.find((row) => row.id === this.editingId)
        const editorIsDirty = this.drawerDirtyFields(this.editingRowData).length > 0
        if (selected && !editorIsDirty && !this.rowSaveChains.has(this.editingId)) {
          this.editingRowData = this.normalizeRow(JSON.parse(JSON.stringify(selected)))
        }
        this.clearSheetRange()
        this.searchTargetOptions('')
        this.scheduleSortable()
      } catch (err) {
        if (requestToken === this.listRequestToken) {
          notifyApiError(err, { messages: SERUM_ERRORS.workbench.load })
        }
      } finally {
        if (requestToken === this.listRequestToken) this.loading = false
      }
    },
    normalizeRow(row) {
      const next = { ...row }
      if (!Array.isArray(next.target_codes)) {
        next.target_codes = this.parseCodes(next.target_codes)
      }
      Object.entries(REQUIRED_STATUS_DEFAULTS).forEach(([key, fallback]) => {
        if (!String(next[key] ?? '').trim()) next[key] = fallback
      })
      next.priority = canonicalizeWorkbenchPriority(next.priority)
      next.species_cross = this.splitTokenMulti('species_cross', next.species_cross)
      next.immuno_method = this.splitTokenMulti('immuno_method', next.immuno_method)
      return next
    },
    replaceRow(saved) {
      const { normalized } = this.patchExistingListRow(saved)
      if (this.editingId === saved.id && this.editingRowData) {
        Object.assign(this.editingRowData, normalized)
      }
      this.updateRowBaseline(normalized)
    },
    updateRowBaseline(row) {
      if (!row?.id) return
      this.rowBaselines.set(row.id, JSON.parse(JSON.stringify(row)))
    },
    payloadRow(row, fields = []) {
      const payload = { id: row.id }
      fields.forEach((field) => {
        payload[field] = this.isTokenMultiKey(field)
          ? this.joinTokenMulti(field, row[field])
          : row[field]
      })
      return payload
    },
    async saveRow(row, { fields = [], resort = false } = {}) {
      if (!row?.id || !fields.length || fields.some((field) => !this.canEditField(row, field))) return
      const rowId = row.id
      const changedValues = Object.fromEntries(
        fields.map((field) => [field, JSON.parse(JSON.stringify(row[field] ?? null))]),
      )
      const previous = this.rowSaveChains.get(rowId) || Promise.resolve()
      const task = previous
        .catch(() => undefined)
        .then(async () => {
          const payload = this.payloadRow({ id: rowId, ...changedValues }, fields)
          const baseline = this.rowBaselines.get(rowId)
          if (baseline) {
            payload._expected = Object.fromEntries(
              fields.map((field) => [field, baseline[field] ?? null]),
            )
          }
          const saved = await saveWorkbench(payload)
          const normalized = this.normalizeRow(saved)
          this.updateRowBaseline(normalized)
          if (resort) {
            await this.getList({ flushEditor: false })
            const refreshed = this.list.find((item) => item.id === rowId)
            if (refreshed && this.editingId === rowId && this.editingRowData) {
              Object.assign(this.editingRowData, this.normalizeRow(JSON.parse(JSON.stringify(refreshed))))
            }
            return saved
          }

          const current = this.list.find((item) => item.id === rowId)
          const editor = this.editingId === rowId ? this.editingRowData : null
          if (current || editor) {
            fields.forEach((field) => {
              if (current) current[field] = normalized[field]
              if (editor) editor[field] = normalized[field]
            })
            if (fields.includes('project_code')) {
              if (current) current.experiment_id = normalized.experiment_id
              if (editor) editor.experiment_id = normalized.experiment_id
            }
            if (current) current.display_status = normalized.display_status
            if (editor) editor.display_status = normalized.display_status
          }
          return saved
        })
      this.rowSaveChains.set(rowId, task)
      try {
        return await task
      } catch (err) {
        notifyApiError(err, { messages: SERUM_ERRORS.workbench.save })
        if (this.rowSaveChains.get(rowId) === task) {
          await this.getList({ flushEditor: false })
          const refreshed = this.list.find((item) => item.id === rowId)
          if (refreshed && this.editingId === rowId && this.editingRowData) {
            Object.assign(this.editingRowData, this.normalizeRow(JSON.parse(JSON.stringify(refreshed))))
          }
        }
        return null
      } finally {
        if (this.rowSaveChains.get(rowId) === task) {
          this.rowSaveChains.delete(rowId)
        }
      }
    },
    async handleCreate() {
      if (!this.canCreate) return
      this.loading = true
      try {
        const saved = await saveWorkbench({})
        await this.revealCreatedRow(saved)
      } catch (err) {
        notifyApiError(err, { messages: SERUM_ERRORS.workbench.save })
      } finally {
        this.loading = false
      }
    },
    async handleDelete(row) {
      if (!this.canDeleteRow(row)) {
        ElMessage.warning(
          this.canDraftEdit ? '只能删除草稿状态的工作台记录' : '您没有权限删除工作台记录',
        )
        return
      }
      try {
        await ElMessageBox.confirm('删除后将同时清除挂在临时实验号下的方案子表，确定删除？', '删除工作台记录', {
          type: 'warning',
        })
      } catch {
        return
      }
      if (!await this.flushEditorForAction(row)) return
      try {
        await deleteWorkbench(row.id)
        if (this.editingId === row.id) this.drawerVisible = false
        ElMessage.success('已删除')
        this.getList()
      } catch (err) {
        notifyApiError(err, { messages: SERUM_ERRORS.workbench.delete })
      }
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
        this.replaceRow(saved)
        ElMessage.success(`已下架，临时实验号 ${saved.experiment_id}`)
        await this.getList()
      } catch (err) {
        notifyApiError(err, { messages: SERUM_ERRORS.workbench.unlist })
      } finally {
        this.loading = false
      }
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
        await reorderWorkbench(payload.movedId, payload.targetId)
        await this.getList()
      } catch (err) {
        notifyApiError(err, { messages: SERUM_ERRORS.workbench.reorder })
        await this.getList()
      } finally {
        this.loading = false
      }
    },
    async openScheme(row) {
      if (!await this.flushEditorForAction(row)) return
      if (row.aligned_locked && row.serum_project_id) {
        const userInfo = this.userStore.userInfo || {}
        if (canOpenSerumEdit(userInfo, row)) {
          this.$router.push({ path: '/serum/edit', query: { id: row.serum_project_id } })
          return
        }
        if (canAccessSerumDetail(userInfo)) {
          this.$router.push({ path: '/serum/detail', query: { id: row.serum_project_id } })
          return
        }
      }
      const workbenchId = Number(row?.id)
      if (!Number.isSafeInteger(workbenchId) || workbenchId <= 0) {
        ElMessage.warning('工作台记录尚未保存，请刷新列表后重试')
        return
      }
      this.$router.push({ name: 'SerumWorkbenchScheme', query: { id: workbenchId } })
    },
    async onSheetPaste(event) {
      if (!this.canEdit) return
      if (event.target?.closest?.('input, textarea')) return
      const text = event.clipboardData?.getData('text/plain') || ''
      if (!text) return
      if (!text.includes('\t') && !text.includes('\n') && !this.sheetRange) return
      event.preventDefault()
      if (!await this.flushPendingSheetEdits()) return
      const lines = text.replace(/\r/g, '').split('\n')
      if (lines.at(-1) === '') lines.pop()
      const grid = lines.map((line) => line.split('\t'))
      if (!grid.length) return

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

      const pendingRowSaves = [...this.rowSaveChains.values()]
      if (pendingRowSaves.length) {
        const results = await Promise.allSettled(pendingRowSaves)
        if (results.some((result) => result.status === 'rejected')) return
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
          if (column?.edit === 'readonly') return
          const result = this.assignSheetValue(row, key, cell)
          if (result.ok) {
            touchedCells.push({ rowId: row.id, key })
            const fields = dirtyByIndex.get(rowIndex) || new Set()
            fields.add(key)
            if (key === 'target_codes' || key === 'target_name') {
              fields.add(key === 'target_codes' ? 'target_name' : 'target_codes')
              const targetFields = targetFieldsByIndex.get(rowIndex) || new Set()
              targetFields.add(key)
              targetFieldsByIndex.set(rowIndex, targetFields)
            }
            dirtyByIndex.set(rowIndex, fields)
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
              const submittedNames = this.splitTargetNames(row.target_name)
              const matches = submittedNames.length === canonicalNames.length
                && submittedNames.every(
                  (name, index) => name.toLowerCase() === String(canonicalNames[index]).toLowerCase(),
                )
              if (!matches) throw new Error('target-mismatch')
            }
            row.target_name = canonicalNames.join('&')
          })

          const nameOnlyEntries = targetEntries.filter(
            ({ fields }) => fields.has('target_name') && !fields.has('target_codes'),
          )
          const resolvedNames = await this.resolveTargetNames(
            nameOnlyEntries.flatMap(({ row }) => this.splitTargetNames(row.target_name)).join('&'),
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
            const targetItems = this.splitTargetNames(row.target_name)
              .map((name) => resolvedNames.itemByName.get(name.toLowerCase()))
            row.target_codes = targetItems.map((item) => item.snum)
            row.target_name = targetItems.map((item) => item.name).join('&')
          })
        } catch {
          ElMessage.warning('靶点名称与编号不匹配或校验失败，本次粘贴未保存')
          return
        }
      }

      const items = [...dirtyByIndex.entries()].map(([rowIndex, fields]) => {
        const row = workingRows[rowIndex]
        const fieldList = [...fields]
        const payload = this.payloadRow(row, fieldList)
        const baseline = this.rowBaselines.get(row.id)
        if (baseline) {
          payload._expected = Object.fromEntries(
            fieldList.map((field) => [field, baseline[field] ?? null]),
          )
        }
        return payload
      })
      try {
        const result = await saveWorkbenchBatch({ items })
        const savedCount = result?.items?.length || 0
        await this.getList()
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
      } catch (err) {
        notifyApiError(err, { messages: SERUM_ERRORS.workbench.save })
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
  padding: var(--list-page-padding);
  background-color: var(--list-page-bg);
  min-height: 100%;
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
  flex: 2 1 260px;
  width: auto;
  min-width: 220px;
}
.filter-select {
  flex: 1 1 112px;
  width: auto;
  min-width: 104px;
}
.data-view-controls {
  flex-shrink: 0;
  align-self: flex-start;
  margin-left: auto;
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
.table-card :deep(.el-table__header .cell) {
  white-space: nowrap;
}
.table-card :deep(.status-column-cell .cell),
.table-card :deep(.action-column-cell .cell) {
  display: flex;
  justify-content: center;
}
.table-card :deep(.is-editing > td) {
  background: #ecf5ff !important;
}
.list-status-tag.status-tone-king {
  color: #6f4d9c;
  background: #efe8f6;
  border-color: #d4c4ea;
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
.table-card :deep(.status-select.status-tone-info .el-select__wrapper),
.table-card :deep(.inline-select.status-tone-info .el-select__wrapper) {
  background-color: var(--el-color-info-light-9);
}
.table-card :deep(.status-select.status-tone-info .el-select__selected-item),
.table-card :deep(.inline-select.status-tone-info .el-select__selected-item) {
  color: var(--el-color-info);
}
.table-card :deep(.status-select.status-tone-primary .el-select__wrapper) {
  background-color: var(--el-color-primary-light-9);
}
.table-card :deep(.status-select.status-tone-primary .el-select__selected-item) {
  color: var(--el-color-primary);
}
.table-card :deep(.status-select.status-tone-warning .el-select__wrapper),
.table-card :deep(.priority-select.status-tone-warning .el-select__wrapper) {
  background-color: var(--el-color-warning-light-9);
}
.table-card :deep(.status-select.status-tone-warning .el-select__selected-item),
.table-card :deep(.priority-select.status-tone-warning .el-select__selected-item) {
  color: var(--el-color-warning);
}
.table-card :deep(.status-select.status-tone-success .el-select__wrapper),
.table-card :deep(.inline-select.status-tone-success .el-select__wrapper) {
  background-color: var(--el-color-success-light-9);
}
.table-card :deep(.status-select.status-tone-success .el-select__selected-item),
.table-card :deep(.inline-select.status-tone-success .el-select__selected-item) {
  color: var(--el-color-success);
}
.table-card :deep(.status-select.status-tone-danger .el-select__wrapper),
.table-card :deep(.priority-select.status-tone-danger .el-select__wrapper) {
  background-color: var(--el-color-danger-light-9);
}
.table-card :deep(.status-select.status-tone-danger .el-select__selected-item),
.table-card :deep(.priority-select.status-tone-danger .el-select__selected-item) {
  color: var(--el-color-danger);
}
.table-card :deep(.priority-select.status-tone-info .el-select__wrapper) {
  background-color: var(--el-color-info-light-9);
}
.table-card :deep(.priority-select.status-tone-info .el-select__selected-item) {
  color: var(--el-color-info);
}
.table-card :deep(.priority-select.status-tone-king .el-select__wrapper) {
  background-color: #efe8f6;
}
.table-card :deep(.priority-select.status-tone-king .el-select__selected-item) {
  color: #6f4d9c;
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
  -webkit-user-select: none;
}
.table-card :deep(.el-table.is-row-sortable td.sort-column-cell) {
  touch-action: none;
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
.sheet-wrap :deep(.sheet-tone-info) {
  color: var(--el-color-info);
}
.sheet-wrap :deep(.sheet-tone-primary) {
  color: var(--el-color-primary);
}
.sheet-wrap :deep(.sheet-tone-warning) {
  color: var(--el-color-warning);
}
.sheet-wrap :deep(.sheet-tone-success) {
  color: var(--el-color-success);
}
.sheet-wrap :deep(.sheet-tone-danger) {
  color: var(--el-color-danger);
}
.sheet-wrap :deep(.sheet-tone-king) {
  color: #6f4d9c;
}
.target-option-code {
  float: right;
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
}
.target-selected-text {
  display: block;
  box-sizing: border-box;
  flex: 0 1 auto;
  max-width: calc(100% - 24px);
  min-width: 0;
  padding: 0 6px;
  overflow: hidden;
  color: var(--el-text-color-regular);
  font: inherit;
  line-height: normal;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.target-name-select :deep(.el-select__selection) {
  flex-wrap: nowrap;
  overflow: hidden;
}
.target-name-select :deep(.el-select__input-wrapper) {
  flex: 1 1 24px;
  min-width: 24px;
}
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
}
.token-multi-select :deep(.el-select__selection),
.token-multi-select :deep(.el-select__tags) {
  flex-wrap: nowrap;
  min-width: 0;
}
.token-multi-selected-text {
  max-width: none;
  overflow: visible;
  text-overflow: clip;
  white-space: nowrap;
}
</style>

<style>
.workbench-drawer .status-select.status-tone-info .el-select__wrapper,
.workbench-drawer .drawer-select.status-tone-info .el-select__wrapper {
  background-color: var(--el-color-info-light-9);
}
.workbench-drawer .status-select.status-tone-info .el-select__selected-item,
.workbench-drawer .drawer-select.status-tone-info .el-select__selected-item {
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
.workbench-drawer .status-select.status-tone-success .el-select__wrapper,
.workbench-drawer .drawer-select.status-tone-success .el-select__wrapper {
  background-color: var(--el-color-success-light-9);
}
.workbench-drawer .status-select.status-tone-success .el-select__selected-item,
.workbench-drawer .drawer-select.status-tone-success .el-select__selected-item {
  color: var(--el-color-success);
}
.workbench-drawer .status-select.status-tone-danger .el-select__wrapper,
.workbench-drawer .priority-select.status-tone-danger .el-select__wrapper {
  background-color: var(--el-color-danger-light-9);
}
.workbench-drawer .status-select.status-tone-danger .el-select__selected-item,
.workbench-drawer .priority-select.status-tone-danger .el-select__selected-item {
  color: var(--el-color-danger);
}
.workbench-drawer .priority-select.status-tone-info .el-select__wrapper {
  background-color: var(--el-color-info-light-9);
}
.workbench-drawer .priority-select.status-tone-info .el-select__selected-item {
  color: var(--el-color-info);
}
.workbench-drawer .priority-select.status-tone-king .el-select__wrapper {
  background-color: #efe8f6;
}
.workbench-drawer .priority-select.status-tone-king .el-select__selected-item {
  color: #6f4d9c;
}
</style>
