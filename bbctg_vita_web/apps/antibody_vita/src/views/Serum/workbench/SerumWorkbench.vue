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
        <el-option v-for="item in speciesCrossOptions" :key="item" :label="item" :value="item" />
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
            <h1 class="page-title">项目工作台</h1>
            <p class="page-subtitle">从计划筹备到实验结题，在同一队列中推进优先级、物料和方案。</p>
          </div>
        </div>
        <div class="console-actions">
          <button
            type="button"
            class="ready-summary"
            :class="{ 'is-active': listQuery.can_start === '是' }"
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
            <el-option v-for="item in optionLists.immuno_method" :key="item" :label="item" :value="item" />
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
          <el-button
            class="list-filter-action-button view-toggle-button"
            :class="{ 'is-sheet': viewMode === 'sheet' }"
            :title="viewMode === 'workbench' ? '当前为快速编辑，点击切换到批量 Sheet' : '当前为批量 Sheet，点击切换到快速编辑'"
            @click="toggleViewMode"
          >
            <el-icon><ViewIcon /></el-icon>
            <span>视图</span>
          </el-button>
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
        <el-table-column label="排序" align="center" width="62" class-name="sort-column-cell">
          <template #default="{ row }">
            <div class="sort-cell">
              <el-input
                v-if="canEditField(row, 'sort_order') && sortEditingId === row.id"
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
                :disabled="!canEditField(row, 'sort_order')"
                @click.stop="startSortEdit(row)"
              >
                {{ row.sort_order ?? '' }}
              </button>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="target_name" label="靶点名称" align="center" min-width="100" show-overflow-tooltip />
        <el-table-column prop="pm" label="PM" align="center" min-width="72" show-overflow-tooltip />
        <el-table-column prop="mouse_strain_category" label="归类鼠型" align="center" min-width="90" show-overflow-tooltip />
        <el-table-column prop="project_set_code" label="项目集编号" align="center" min-width="110" show-overflow-tooltip />
        <el-table-column prop="project_code" label="免疫项目号" align="center" min-width="120" show-overflow-tooltip />
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
            ref="sheetTable"
            :data="list"
            border
            show-overflow
            height="100%"
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
                :title="column.label"
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
                v-else-if="column.edit === 'select' || column.edit === 'species'"
                :field="column.key"
                :title="column.label"
                :width="column.width"
                :min-width="column.minWidth || column.width || 120"
                :show-overflow="column.key !== 'species_cross'"
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
                      :multiple="column.edit === 'species'"
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
                :title="column.label"
                :width="column.width"
                :min-width="column.minWidth || column.width || 120"
                :align="column.key === 'sort_order' ? 'center' : undefined"
                :header-align="column.key === 'sort_order' ? 'center' : undefined"
                :show-overflow="column.key !== 'species_cross'"
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
            :class="{ 'is-dragging': sheetDragging }"
            aria-hidden="true"
          />
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
                <el-select
                  v-else-if="field.type === 'target'"
                  v-model="editingRow.target_codes"
                  filterable
                  multiple
                  remote
                  remote-show-suffix
                  class="target-name-select"
                  :remote-method="searchTargetOptions"
                  :loading="targetLoading"
                  :placeholder="editingRow.target_name ? '' : '搜索靶点'"
                  style="width: 100%;"
                  :disabled="isFieldLocked(editingRow, field)"
                  @focus="searchTargetOptions('')"
                  @change="onRowTargetChange(editingRow)"
                >
                  <template #tag>
                    <span class="target-selected-text">{{ editingRow.target_name }}</span>
                  </template>
                  <el-option
                    v-for="item in targetOptions"
                    :key="item.snum"
                    :label="`${item.name}（${item.snum}）`"
                    :value="item.snum"
                  >
                    <span>{{ item.name }}</span>
                    <span class="target-option-code">{{ item.snum }}</span>
                  </el-option>
                </el-select>
                <el-input
                  v-else-if="field.type === 'target_codes'"
                  :model-value="codesText(editingRow)"
                  disabled
                  placeholder="自动带出"
                />
                <el-select
                  v-else-if="field.type === 'species'"
                  :model-value="speciesCrossList(editingRow)"
                  class="drawer-select species-cross-select"
                  multiple
                  filterable
                  style="width: 100%;"
                  :disabled="isFieldLocked(editingRow, field)"
                  @change="onSpeciesCrossChange(editingRow, $event)"
                >
                  <template #tag>
                    <span class="target-selected-text species-selected-text">
                      {{ speciesCrossText(editingRow) }}
                    </span>
                  </template>
                  <el-option v-for="item in speciesCrossOptions" :key="item" :label="item" :value="item" />
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
  Bottom,
  CopyDocument,
  Delete,
  Document,
  Download,
  Search,
  Tools,
  View as ViewIcon,
} from '@element-plus/icons-vue'
import {
  ElButton,
  ElButtonGroup,
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
  ElPopover,
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

const PLAN_STATUS_OPTIONS = [...WORKBENCH_PLAN_STATUS_OPTIONS]
const PRIORITY_OPTIONS = [...WORKBENCH_PRIORITY_OPTIONS]
const REVIEW_STATUS_OPTIONS = ['未审', '已通过', '驳回']
const MOUSE_STATUS_OPTIONS = ['未定', '扩繁中', '可运', '在途', '已到']
const ZYGOSITY_OPTIONS = ['纯合', '杂合']
const STUDY_TYPE_OPTIONS = [
  '数据包',
  '客户关注',
  '公司内部研发',
  '公司重点',
  '客户付钱',
  'PCC过会',
  '沈博关注',
  '大客户关注',
  '我也布吉岛',
]
const MOUSE_STRAIN_CATEGORY_OPTIONS = [...SERUM_MOUSE_STRAIN_CATEGORY_OPTIONS]
const SPECIES_CROSS_OPTIONS = ['人', '猴', '鼠', '狗', '猫', '空白']
const IMMUNO_METHOD_OPTIONS = ['蛋白', 'DNA', 'LNP', '细胞', '混合']
const ANTIGEN_SOURCE_OPTIONS = ['内部制备', '外购', '客户提供']
const CELL_PREP_OPTIONS = ['未开始', '进行中', '已完成', '不需要']
const MOUSE_REGION_OPTIONS = ['北京', '海门', '苏州', '客户']
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
const USER_FIELD_KEYS = new Set(['pm', 'owner', 'reviewer'])
const DATE_FIELD_KEYS = new Set(['mouse_birth_date', 'mouse_arrive_date', 'antigen_eta'])
const SHEET_RANGE_CLASS_NAMES = [
  'is-sheet-selected',
  'is-sheet-active',
]
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
      { key: 'reviewer', label: '审核人', type: 'select', optionsKey: 'reviewers' },
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
      { key: 'immuno_method', label: '免疫方式', type: 'select', optionsKey: 'immuno_method' },
      { key: 'mouse_strain_category', label: '归类鼠型', type: 'select', optionsKey: 'mouse_strain_category', lock: 'aligned' },
      { key: 'mouse_strain', label: '小鼠品系', type: 'text', lock: 'aligned' },
      { key: 'species_cross', label: '种属交叉', type: 'species', wide: true },
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
  { key: 'sort_order', label: '排序', width: 50, edit: 'number' },
  { key: 'priority', label: '优先级', width: 90, edit: 'select', optionsKey: 'priority' },
  { key: 'target_name', label: '靶点名称', edit: 'target' },
  { key: 'target_codes', label: '靶点编号', edit: 'target' },
  { key: 'pm', label: 'PM', width: 90, edit: 'select', optionsKey: 'pms' },
  { key: 'project_set_code', label: '项目集编号', edit: 'text' },
  { key: 'project_code', label: '免疫项目号', edit: 'text' },
  { key: 'study_type', label: '课题类型', edit: 'select', optionsKey: 'study_type' },
  { key: 'species_cross', label: '种属交叉', edit: 'species', minWidth: 160 },
  { key: 'owner', label: '开展人', width: 90, edit: 'select', optionsKey: 'owners' },
  { key: 'reviewer', label: '审核人', width: 90, edit: 'select', optionsKey: 'reviewers' },
  { key: 'review_status', label: '审核结果', width: 90, edit: 'select', optionsKey: 'review_status' },
  { key: 'immuno_method', label: '免疫方式', edit: 'select', optionsKey: 'immuno_method' },
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
const SHEET_HEADER_ALIASES = Object.freeze({
  优先级排序: 'sort_order',
  项目编号: 'project_code',
  运输状态: 'mouse_status',
  抗原到货情况: 'antigen_ready',
  是否代下扩繁: 'mouse_expand_requested',
  LNP是否下单: 'lnp_ordered',
  冲击细胞准备: 'cell_prep_status',
  是否可开展: 'can_start',
})
const WorkbenchStatusEditor = {
  name: 'WorkbenchStatusEditor',
  components: { ElPopover, ElTag },
  props: {
    value: { type: [String, Number], default: '' },
    options: { type: Array, default: () => [] },
    type: { type: String, default: 'info' },
    editable: { type: Boolean, default: false },
  },
  emits: ['change'],
  data() {
    return { visible: false }
  },
  computed: {
    displayValue() {
      return String(this.value ?? '').trim() || '—'
    },
  },
  watch: {
    editable(value) {
      if (!value) this.visible = false
    },
  },
  methods: {
    choose(value) {
      this.visible = false
      if (value !== this.value) this.$emit('change', value)
    },
  },
  template: `
    <el-popover
      v-model:visible="visible"
      placement="right"
      trigger="click"
      transition="el-zoom-in-left"
      :width="116"
      :disabled="!editable"
      :teleported="true"
    >
      <div class="workbench-status-option-list">
        <button
          v-for="item in options"
          :key="item"
          type="button"
          class="workbench-status-option"
          :class="{ 'is-current': item === value }"
          @click.stop="choose(item)"
        >
          {{ item }}
        </button>
      </div>
      <template #reference>
        <el-tag
          class="list-status-tag workbench-status-tag"
          :class="{ 'is-editable': editable }"
          :type="type"
          effect="plain"
          @click.stop
        >
          {{ displayValue }}
        </el-tag>
      </template>
    </el-popover>
  `,
}

const WorkbenchRowActions = {
  name: 'WorkbenchRowActions',
  components: { ElButton, ElButtonGroup },
  props: {
    row: { type: Object, required: true },
    canCopy: { type: Boolean, default: false },
    canDelete: { type: Boolean, default: false },
    canUnlist: { type: Boolean, default: false },
  },
  emits: ['scheme', 'copy', 'delete', 'unlist'],
  setup() {
    return { Bottom, CopyDocument, Delete, Document, ViewIcon }
  },
  template: `
    <div class="action-cell" @click.stop>
      <el-button-group>
        <el-button
          class="list-table-action-btn"
          type="primary"
          plain
          :icon="row.aligned_locked ? ViewIcon : Document"
          @click="$emit('scheme', row)"
        >
          {{ row.aligned_locked ? '详情' : '方案' }}
        </el-button>
        <el-button
          class="list-table-action-btn"
          type="success"
          plain
          :icon="CopyDocument"
          :class="{ 'no-permission-btn': !canCopy }"
          :title="!canCopy ? '您没有权限复制工作台记录' : ''"
          @click="$emit('copy', row)"
        >
          复制
        </el-button>
        <el-button
          class="list-table-action-btn"
          type="warning"
          plain
          :icon="row.aligned_locked ? Bottom : Delete"
          :class="{ 'no-permission-btn': !(row.aligned_locked ? canUnlist : canDelete) }"
          :title="!(row.aligned_locked ? canUnlist : canDelete) ? '您没有权限执行此操作' : ''"
          @click="$emit(row.aligned_locked ? 'unlist' : 'delete', row)"
        >
          {{ row.aligned_locked ? '下架' : '删除' }}
        </el-button>
      </el-button-group>
    </div>
  `,
}

export default {
  name: 'SerumWorkbench',
  components: {
    AdvancedOpsBar,
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
    ViewIcon,
    VxeColumn,
    VxeInput,
    VxeSelect,
    VxeTable,
    WorkbenchRowActions,
    WorkbenchStatusEditor,
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
      viewMode: 'workbench',
      showAdvancedOps: false,
      drawerVisible: false,
      editingId: null,
      editingRowData: null,
      ageEditingRowId: null,
      sortEditingId: null,
      sortInputRefs: {},
      pasteAnchor: null,
      sheetRange: null,
      sheetEditOriginal: null,
      sheetEditSource: '',
      sheetKeyboardChain: Promise.resolve(),
      sheetDragMode: '',
      sheetPointerDown: false,
      sheetDragging: false,
      sortable: null,
      sortableInitToken: 0,
      targetOptions: [],
      targetLoading: false,
      targetRequestToken: 0,
      allUserOptions: getCachedSerumUserOptions(),
      listRequestToken: 0,
      pendingDrawerSaves: new Set(),
      pendingSheetOps: new Set(),
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
        limit: 50,
        keyword: '',
        view_group: null,
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
        species_cross: [...SPECIES_CROSS_OPTIONS],
        immuno_method: [...IMMUNO_METHOD_OPTIONS],
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
      speciesCrossOptions: SPECIES_CROSS_OPTIONS,
      editorSections: EDITOR_SECTIONS,
      statusViews: STATUS_VIEWS,
      sheetColumns: SHEET_COLUMNS,
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
    hasActiveFilters() {
      return Boolean(this.activeViewGroup || this.hasSecondaryFilters)
    },
    canDragRows() {
      return this.canFullEdit
        && !this.hasActiveFilters
        && this.list.length > 1
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
    sheetKeyboardConfig() {
      return {
        isArrow: true,
        isDel: true,
        isEnter: true,
        isTab: true,
        isShift: true,
        isEdit: false,
        isClip: false,
      }
    },
    sheetEditConfig() {
      return {
        trigger: 'dblclick',
        mode: 'cell',
        showIcon: false,
        beforeEditMethod: this.sheetBeforeEdit,
      }
    },
  },
  watch: {
    viewMode(value) {
      this.clearSheetRange()
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
  },
  mounted() {
    this.scheduleSortable()
    this.onWindowMouseUp = () => {
      this.sheetPointerDown = false
      this.sheetDragging = false
      this.sheetDragMode = ''
    }
    window.addEventListener('mouseup', this.onWindowMouseUp)
    document.addEventListener('mousedown', this.onDocumentPointerDown, true)
  },
  beforeUnmount() {
    this.destroySortable()
    window.removeEventListener('mouseup', this.onWindowMouseUp)
    document.removeEventListener('mousedown', this.onDocumentPointerDown, true)
  },
  activated() {
    if (this.onWindowMouseUp) {
      window.addEventListener('mouseup', this.onWindowMouseUp)
    }
    document.addEventListener('mousedown', this.onDocumentPointerDown, true)
    if (this.loading) return
    this.getList()
  },
  deactivated() {
    this.closeEditor()
    this.destroySortable()
    if (this.onWindowMouseUp) {
      window.removeEventListener('mouseup', this.onWindowMouseUp)
    }
    document.removeEventListener('mousedown', this.onDocumentPointerDown, true)
  },
  methods: {
    async toggleViewMode() {
      if (this.viewMode === 'sheet' && !await this.flushPendingSheetEdits()) return
      this.viewMode = this.viewMode === 'workbench' ? 'sheet' : 'workbench'
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
        this.optionLists.study_type = this.uniq([
          ...STUDY_TYPE_OPTIONS,
          ...(data?.study_types || []),
        ])
        this.optionLists.immuno_method = this.uniq([
          ...IMMUNO_METHOD_OPTIONS,
          ...(data?.immuno_methods || []),
        ])
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
      if (field.type === 'species') return SPECIES_CROSS_OPTIONS
      if (field.key === 'mouse_strain_category') return MOUSE_STRAIN_CATEGORY_OPTIONS
      if (field.type === 'status' || field.optionsKey === 'plan_status') {
        if (row?.aligned_locked && row.display_status) return [row.display_status]
        return this.planStatusOptions
      }
      return this.mergedOptions(field.optionsKey || field.key)
    },
    splitSpeciesCross(value) {
      if (Array.isArray(value)) return this.normalizeSpeciesCrossSelection(value)
      const text = String(value || '').trim()
      if (!text) return []
      return this.normalizeSpeciesCrossSelection(
        text.split(/[,，]/).map((item) => item.trim()).filter(Boolean),
      )
    },
    joinSpeciesCross(values) {
      return this.normalizeSpeciesCrossSelection(values).join(',')
    },
    normalizeSpeciesCrossSelection(values) {
      const raw = (Array.isArray(values) ? values : [values]).map((item) => String(item || '').trim()).filter(Boolean)
      if (!raw.length) return []
      if (raw.some((item) => !SPECIES_CROSS_OPTIONS.includes(item))) return []
      return SPECIES_CROSS_OPTIONS.filter((item) => raw.includes(item))
    },
    speciesCrossList(row) {
      return this.splitSpeciesCross(row?.species_cross)
    },
    speciesCrossText(row) {
      return this.speciesCrossList(row).join('，')
    },
    onSpeciesCrossChange(row, values) {
      row.species_cross = this.normalizeSpeciesCrossSelection(values)
      this.persistRow(row, 'species_cross')
    },
    async searchTargetOptions(keyword) {
      const requestToken = ++this.targetRequestToken
      this.targetLoading = true
      try {
        const codes = [
          ...this.list.flatMap((row) => (Array.isArray(row.target_codes) ? row.target_codes : [])),
          ...(Array.isArray(this.editingRow?.target_codes) ? this.editingRow.target_codes : []),
        ]
        const data = await fetchSerumTargetOptions(keyword || '', [...new Set(codes)])
        if (requestToken !== this.targetRequestToken) return
        this.mergeTargetOptions(data?.items || [])
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
    onRowTargetChange(row) {
      const codes = Array.isArray(row.target_codes) ? row.target_codes : []
      row.target_codes = codes
      row.target_name = codes
        .map((code) => this.targetOptions.find((item) => item.snum === code)?.name || code)
        .join('&')
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
        || field?.key === 'immuno_method'
        || field?.key === 'mouse_strain_category'
        || field?.key === 'mouse_region'
        || field?.key === 'cell_prep_status'
    },
    drawerFieldValue(field, row) {
      if (field?.key === 'plan_status' && row?.aligned_locked) {
        return row.display_status || row.plan_status
      }
      return row?.[field?.key]
    },
    syncDrawerControlTooltip(event) {
      const target = event.target
      if (!(target instanceof Element)) return
      const control = target.closest('.el-input, .el-select')
      if (!(control instanceof HTMLElement)) return
      const content = control.querySelector(
        '.el-input__inner, .target-selected-text, .el-select__selected-item',
      )
      if (!(content instanceof HTMLElement)) {
        control.removeAttribute('title')
        return
      }
      const text = content instanceof HTMLInputElement
        ? content.value.trim()
        : String(content.textContent || '').trim()
      const clip = content.closest('.el-select__selection') || content
      const isOverflowing = content.scrollWidth > content.clientWidth
        || clip.scrollWidth > clip.clientWidth
        || content.getBoundingClientRect().right > clip.getBoundingClientRect().right
      if (text && isOverflowing) control.setAttribute('title', text)
      else control.removeAttribute('title')
    },
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
      if (this.drawerVisible && this.editingId === row.id) return
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
      if (field === 'species_cross') {
        return this.joinSpeciesCross(value)
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
    async flushPendingSheetEdits() {
      await this.sheetKeyboardChain
      await this.$refs.sheetTable?.clearEdit?.()
      if (!this.pendingSheetOps.size) return true
      const results = await Promise.allSettled([...this.pendingSheetOps])
      return !results.some((result) => result.status === 'rejected' || result.value === null)
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
    startSortEdit(row) {
      if (!this.canEditField(row, 'sort_order') || !row?.id) return
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
    formatSpeciesCross({ cellValue }) {
      return this.splitSpeciesCross(cellValue).join('，')
    },
    sheetFormatter(column) {
      if (column.key === 'target_codes') return this.formatCodes
      if (column.key === 'plan_status') return this.formatPlanStatus
      if (column.key === 'species_cross') return this.formatSpeciesCross
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
      if (key === 'mouse_strain_category') return [...MOUSE_STRAIN_CATEGORY_OPTIONS]
      if (key === 'species_cross' || column.edit === 'species') return SPECIES_CROSS_OPTIONS
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
      if (column.edit !== 'species') return row[column.key]
      const value = row[column.key]
      return Array.isArray(value)
        ? this.normalizeSpeciesCrossSelection(value).join('，')
        : String(value ?? '')
    },
    sheetPickerDisplayValue(row, column) {
      if (column.key === 'target_codes') return this.formatCodesText(row.target_codes)
      if (column.key === 'target_name') return row.target_name || ''
      if (column.key === 'plan_status') return row.plan_status || row.display_status || ''
      if (column.edit === 'species') return this.splitSpeciesCross(row[column.key]).join('，')
      return row[column.key] ?? ''
    },
    setSheetChoiceDirectValue(row, key, value) {
      row[key] = value
    },
    sheetEditRender(column) {
      if (column.edit === 'readonly') return undefined
      if (column.edit === 'number') {
        return {
          name: 'VxeNumberInput',
          props: {
            align: column.key === 'sort_order' ? 'center' : undefined,
            className: 'sheet-grid-editor',
            controlConfig: { showButton: false },
            min: 1,
            type: 'integer',
          },
        }
      }
      if (column.edit === 'date') {
        return {
          name: 'VxeInput',
          props: {
            className: 'sheet-grid-editor sheet-date-editor',
            clearable: false,
            editable: true,
            labelFormat: 'yyyy-MM-dd',
            placeholder: 'YYYY-MM-DD',
            type: 'date',
            valueFormat: 'yyyy-MM-dd',
          },
        }
      }
      return {
        name: 'VxeInput',
        props: {
          className: 'sheet-grid-editor',
          clearable: false,
          placeholder: '',
        },
      }
    },
    sheetBeforeEdit({ row, column }) {
      const key = column?.field
      const allowed = Boolean(key) && !this.isSheetCellLocked(row, key)
      if (!allowed) this.sheetEditSource = ''
      return allowed
    },
    isSheetCellLocked(row, key) {
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
      if (key === 'target_codes') return { ok: true, value: this.uniq(this.parseCodes(raw)) }
      if (DATE_FIELD_KEYS.has(key)) return this.normalizeSheetDate(raw)
      if (key === 'species_cross') {
        const next = this.splitSpeciesCross(raw)
        return next.length || raw === '' ? { ok: true, value: next } : { ok: false, reason: 'option' }
      }
      if (column.edit === 'number') {
        const value = Number(raw)
        return Number.isSafeInteger(value) && value > 0
          ? { ok: true, value }
          : { ok: false, reason: 'integer' }
      }
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
    normalizedSheetRange() {
      if (!this.sheetRange) return null
      const { r1, c1, r2, c2 } = this.sheetRange
      return {
        r1: Math.min(r1, r2),
        c1: Math.min(c1, c2),
        r2: Math.max(r1, r2),
        c2: Math.max(c1, c2),
      }
    },
    isInSheetRange(rowIndex, colIndex) {
      const range = this.normalizedSheetRange()
      if (!range || rowIndex < 0 || colIndex < 0) return false
      return rowIndex >= range.r1 && rowIndex <= range.r2 && colIndex >= range.c1 && colIndex <= range.c2
    },
    sheetRangeCellClasses(rowIndex, colIndex) {
      const range = this.normalizedSheetRange()
      if (!range || !this.isInSheetRange(rowIndex, colIndex)) return []
      const classes = ['is-sheet-selected']
      const activeColumn = this.sheetColumns.findIndex((item) => item.key === this.pasteAnchor?.colKey)
      if (rowIndex === this.pasteAnchor?.rowIndex && colIndex === activeColumn) {
        classes.push('is-sheet-active')
      }
      return classes
    },
    sheetCellClassName({ row, column }) {
      const classes = []
      const rowIndex = this.list.findIndex((item) => item.id === row.id)
      const colIndex = this.sheetColumns.findIndex((item) => item.key === column.field)
      classes.push(...this.sheetRangeCellClasses(rowIndex, colIndex))
      if (column.field === 'priority') classes.push(`sheet-tone-${this.priorityTone(row)}`)
      if (column.field === 'plan_status') classes.push(`sheet-tone-${this.statusTagType(row)}`)
      if (column.field === 'can_start' || column.field === 'antigen_ready') {
        classes.push(row[column.field] === '是' ? 'sheet-tone-success' : 'sheet-tone-info')
      }
      return classes.join(' ')
    },
    sheetHeaderCellClassName({ column }) {
      return column.field ? 'sheet-selectable-header' : ''
    },
    syncPasteAnchorFromRange() {
      if (!this.sheetRange) return
      const column = this.sheetColumns[this.sheetRange.c1]
      if (!column) return
      this.pasteAnchor = { rowIndex: this.sheetRange.r1, colKey: column.key }
    },
    setSheetRange(next) {
      this.sheetRange = next
      this.syncPasteAnchorFromRange()
      this.$nextTick(() => this.paintSheetRange())
    },
    clearSheetRange() {
      this.sheetRange = null
      this.sheetEditOriginal = null
      this.sheetEditSource = ''
      this.sheetDragMode = ''
      this.sheetPointerDown = false
      this.sheetDragging = false
      this.pasteAnchor = null
      this.$refs.sheetTable?.clearSelected?.()
      this.$nextTick(() => this.paintSheetRange())
    },
    paintSheetRange() {
      const wrap = this.$refs.sheetWrap
      const overlay = this.$refs.sheetRangeOverlay
      if (!wrap?.querySelectorAll || !overlay) return
      const hideOverlay = () => {
        overlay.style.display = 'none'
      }
      wrap.querySelectorAll('.vxe-body--column').forEach((el) => {
        el.classList.remove(...SHEET_RANGE_CLASS_NAMES)
      })
      const range = this.normalizedSheetRange()
      const $table = this.$refs.sheetTable
      if (!range || !$table) {
        hideOverlay()
        return
      }
      const selectedCells = []
      for (let r = range.r1; r <= range.r2; r += 1) {
        const row = this.list[r]
        const tr = row ? this.findSheetRowEl(row) : null
        if (!tr) continue
        const cells = [...tr.querySelectorAll('.vxe-body--column')]
        for (let c = range.c1; c <= range.c2; c += 1) {
          const column = this.sheetColumns[c]
          const meta = column && $table.getColumnByField ? $table.getColumnByField(column.key) : null
          const td = meta ? cells.find((cell) => cell.getAttribute('colid') === meta.id) : null
          const classes = this.sheetRangeCellClasses(r, c)
          if (td && classes.length) {
            td.classList.add(...classes)
            selectedCells.push(td)
          }
        }
      }
      if (!selectedCells.length) {
        hideOverlay()
        return
      }
      const stage = this.$refs.sheetTableStage
      const stageRect = stage?.getBoundingClientRect?.()
      const bodyRect = selectedCells[0]
        .closest('.vxe-table--body-wrapper')
        ?.getBoundingClientRect?.()
      if (!stageRect) {
        hideOverlay()
        return
      }
      const cellRects = selectedCells.map((cell) => cell.getBoundingClientRect())
      const clipRect = bodyRect || stageRect
      const left = Math.max(Math.min(...cellRects.map((rect) => rect.left)), clipRect.left)
      const top = Math.max(Math.min(...cellRects.map((rect) => rect.top)), clipRect.top)
      const right = Math.min(Math.max(...cellRects.map((rect) => rect.right)), clipRect.right)
      const bottom = Math.min(Math.max(...cellRects.map((rect) => rect.bottom)), clipRect.bottom)
      if (right <= left || bottom <= top) {
        hideOverlay()
        return
      }
      overlay.style.display = 'block'
      overlay.style.width = `${right - left + 2}px`
      overlay.style.height = `${bottom - top + 2}px`
      overlay.style.transform = `translate3d(${left - stageRect.left - 1}px, ${top - stageRect.top - 1}px, 0)`
    },
    onSheetScroll() {
      this.paintSheetRange()
    },
    findSheetRowEl(row) {
      const $table = this.$refs.sheetTable
      const wrap = this.$refs.sheetWrap
      const rowid = $table?.getRowid?.(row) || row.id
      return wrap?.querySelector?.(`tr[rowid="${rowid}"]`)
    },
    hitSheetCell(target) {
      const td = target?.closest?.('.vxe-body--column')
      if (!td) return null
      const $table = this.$refs.sheetTable
      const colid = td.getAttribute('colid')
      const column = colid && $table?.getColumnById ? $table.getColumnById(colid) : null
      const field = column?.field
      if (!field) return null
      const colIndex = this.sheetColumns.findIndex((item) => item.key === field)
      if (colIndex < 0) return null
      const tr = td.closest('tr')
      const node = tr && $table?.getRowNode ? $table.getRowNode(tr) : null
      const row = node?.item
      const rowIndex = row
        ? this.list.findIndex((item) => item.id === row.id)
        : this.list.findIndex((item) => String(item.id) === String(tr?.getAttribute('rowid')))
      if (rowIndex < 0) return null
      return { rowIndex, colIndex, field }
    },
    hitSheetHeader(target) {
      const th = target?.closest?.('.vxe-header--column')
      if (!th) return null
      const $table = this.$refs.sheetTable
      const colid = th.getAttribute('colid')
      const column = colid && $table?.getColumnById ? $table.getColumnById(colid) : null
      const field = column?.field
      const colIndex = this.sheetColumns.findIndex((item) => item.key === field)
      return colIndex < 0 ? null : { colIndex, field }
    },
    onSheetSelectStart(event) {
      if (event.target?.closest?.('input, textarea')) return
      event.preventDefault()
    },
    onSheetDblClickCapture(event) {
      if (event.target?.closest?.('input, textarea, .vxe-input, .vxe-select, .vxe-number-input')) return
      const hit = this.hitSheetCell(event.target)
      const row = hit ? this.list[hit.rowIndex] : null
      this.sheetEditSource = row && !this.isSheetCellLocked(row, hit.field) ? 'dblclick' : ''
    },
    sheetDirectTextValue(row, key) {
      if (key === 'target_codes') return this.formatCodesText(row.target_codes)
      if (key === 'species_cross') {
        return Array.isArray(row.species_cross)
          ? this.normalizeSpeciesCrossSelection(row.species_cross).join('，')
          : String(row.species_cross ?? '')
      }
      return String(row[key] ?? '')
    },
    focusSheetCellInput(row, key) {
      const input = this.$refs.sheetTable
        ?.getCellElement?.(row, key)
        ?.querySelector?.('input')
      if (!input) return
      input.focus()
      const end = String(input.value || '').length
      input.setSelectionRange?.(end, end)
    },
    startSheetTextEdit(event, mode, text = '') {
      const rowIndex = this.pasteAnchor?.rowIndex
      const key = this.pasteAnchor?.colKey
      const row = this.list[rowIndex]
      if (!row || !key) return
      if (mode !== 'composition') event.preventDefault()
      event.stopPropagation()
      if (this.isSheetCellLocked(row, key)) return
      const character = text || event.key
      const run = async () => {
        const continuing = this.sheetEditOriginal?.rowId === row.id
          && this.sheetEditOriginal?.key === key
        if (!continuing && this.sheetEditOriginal) {
          const previousKey = this.sheetEditOriginal.key
          await this.$refs.sheetTable?.clearEdit?.()
          if (
            ['target_codes', 'target_name'].includes(previousKey)
            && ['target_codes', 'target_name'].includes(key)
            && this.pendingSheetOps.size
          ) {
            await Promise.allSettled([...this.pendingSheetOps])
          }
        }
        if (!continuing) {
          this.sheetEditOriginal = {
            key,
            rowId: row.id,
            targetCodes: this.cloneSheetValue(row.target_codes),
            targetName: row.target_name,
            value: this.cloneSheetValue(row[key]),
          }
        }
        this.sheetEditSource = 'keyboard'
        if (mode === 'backspace') {
          row[key] = this.sheetDirectTextValue(row, key).slice(0, -1)
        } else if (mode === 'character' || mode === 'composition-text') {
          row[key] = `${this.sheetDirectTextValue(row, key)}${character}`
        }
        await this.$refs.sheetTable?.setEditCell?.(row, key)
        await this.$nextTick()
        if (
          this.list[this.pasteAnchor?.rowIndex]?.id === row.id
          && this.pasteAnchor?.colKey === key
        ) {
          this.focusSheetCellInput(row, key)
        }
      }
      this.sheetKeyboardChain = this.sheetKeyboardChain.then(run, run).catch(() => undefined)
      return this.sheetKeyboardChain
    },
    onSheetCompositionEnd(event) {
      if (event.target?.closest?.('input, textarea, .vxe-input, .vxe-select, .vxe-number-input')) {
        return
      }
      const text = String(event.data || '')
      if (text) this.startSheetTextEdit(event, 'composition-text', text)
    },
    onSheetKeydownCapture(event) {
      const editor = event.target?.closest?.(
        'input, textarea, .vxe-input, .vxe-select, .vxe-number-input',
      )
      if (editor) return
      if (event.key === 'Delete') {
        const row = this.list[this.pasteAnchor?.rowIndex]
        const key = this.pasteAnchor?.colKey
        if (row && key && this.isSheetCellLocked(row, key)) {
          event.preventDefault()
          event.stopPropagation()
        }
        return
      }
      if (
        event.key === 'Backspace'
        && !event.ctrlKey
        && !event.metaKey
        && !event.altKey
      ) {
        event.preventDefault()
        this.startSheetTextEdit(event, 'backspace')
        return
      }
      if ((event.ctrlKey || event.metaKey) && String(event.key).toLowerCase() === 'a') {
        event.preventDefault()
        this.selectAllSheetCells()
        return
      }
      const isComposition = event.key === 'Process' || event.keyCode === 229
      const isCharacter = String(event.key || '').length === 1
      if (event.ctrlKey || event.metaKey || event.altKey || (!isCharacter && !isComposition)) return
      this.startSheetTextEdit(event, isComposition ? 'composition' : 'character')
    },
    onSheetWrapMouseDown(event) {
      if (event.target?.closest?.('input, textarea, button, .el-button, .vxe-input, .vxe-select, .vxe-number-input')) {
        return
      }
      if (event.target?.closest?.('.vxe-cell--col-resizable')) return
      this.$refs.sheetWrap?.focus?.()
      const headerHit = this.hitSheetHeader(event.target)
      if (headerHit && this.list.length) {
        event.preventDefault()
        window.getSelection()?.removeAllRanges()
        this.$refs.sheetTable?.clearEdit?.()
        this.sheetDragMode = 'columns'
        this.sheetPointerDown = true
        this.sheetDragging = false
        this.setSheetRange({
          r1: 0,
          c1: headerHit.colIndex,
          r2: this.list.length - 1,
          c2: headerHit.colIndex,
        })
        return
      }
      const hit = this.hitSheetCell(event.target)
      if (!hit) return
      event.preventDefault()
      window.getSelection()?.removeAllRanges()
      this.sheetDragMode = hit.field === 'sort_order' ? 'rows' : 'cells'
      this.sheetPointerDown = true
      this.sheetDragging = false
      if (event.shiftKey && this.sheetRange) {
        this.setSheetRange(this.sheetDragMode === 'rows'
          ? {
              ...this.sheetRange,
              c1: 0,
              r2: hit.rowIndex,
              c2: this.sheetColumns.length - 1,
            }
          : { ...this.sheetRange, r2: hit.rowIndex, c2: hit.colIndex })
        return
      }
      const range = this.sheetDragMode === 'rows'
        ? {
            r1: hit.rowIndex,
            c1: 0,
            r2: hit.rowIndex,
            c2: this.sheetColumns.length - 1,
          }
        : { r1: hit.rowIndex, c1: hit.colIndex, r2: hit.rowIndex, c2: hit.colIndex }
      this.setSheetRange(range)
      const row = this.list[hit.rowIndex]
      if (row) this.$refs.sheetTable?.setSelectCell?.(row, hit.field)
    },
    onSheetWrapMouseOver(event) {
      if (!this.sheetPointerDown) return
      if (this.sheetDragMode === 'columns') {
        const headerHit = this.hitSheetHeader(event.target)
        if (!headerHit || !this.sheetRange || headerHit.colIndex === this.sheetRange.c2) return
        this.sheetDragging = true
        this.setSheetRange({ ...this.sheetRange, c2: headerHit.colIndex })
        return
      }
      const hit = this.hitSheetCell(event.target)
      if (!hit || !this.sheetRange) return
      if (this.sheetDragMode === 'rows') {
        if (hit.rowIndex === this.sheetRange.r2) return
        this.sheetDragging = true
        this.setSheetRange({
          ...this.sheetRange,
          r2: hit.rowIndex,
          c2: this.sheetColumns.length - 1,
        })
        return
      }
      if (hit.rowIndex === this.sheetRange.r2 && hit.colIndex === this.sheetRange.c2) return
      this.sheetDragging = true
      this.setSheetRange({ ...this.sheetRange, r2: hit.rowIndex, c2: hit.colIndex })
    },
    sheetRangeTsv() {
      const range = this.normalizedSheetRange()
      if (!range) return ''
      const lines = []
      for (let r = range.r1; r <= range.r2; r += 1) {
        const row = this.list[r]
        if (!row) continue
        const cells = []
        for (let c = range.c1; c <= range.c2; c += 1) {
          const column = this.sheetColumns[c]
          if (!column) continue
          let value = row[column.key]
          if (column.key === 'target_codes') value = this.formatCodesText(value)
          if (column.key === 'species_cross') value = this.joinSpeciesCross(value)
          if (column.key === 'plan_status') value = row.display_status || value
          if (column.key === 'mouse_age_weeks') value = this.mouseAgeWeeksValue(row, value)
          cells.push(value == null ? '' : String(value))
        }
        lines.push(cells.join('\t'))
      }
      return lines.join('\n')
    },
    onSheetCopy(event) {
      const text = this.sheetRangeTsv()
      if (!text) return
      if (event.target?.closest?.('input, textarea')) return
      event.preventDefault()
      event.clipboardData?.setData('text/plain', text)
    },
    onSheetCellSelected({ row, column, $event }) {
      const key = column?.field
      const rowIndex = this.list.findIndex((item) => item.id === row.id)
      const colIndex = this.sheetColumns.findIndex((item) => item.key === key)
      if (rowIndex < 0 || colIndex < 0) return
      if (this.sheetPointerDown && this.sheetDragMode === 'rows') {
        this.setSheetRange({
          r1: this.sheetRange?.r1 ?? rowIndex,
          c1: 0,
          r2: rowIndex,
          c2: this.sheetColumns.length - 1,
        })
        return
      }
      const extendsRange = $event?.shiftKey
        && ($event.type !== 'keydown' || String($event.key).startsWith('Arrow'))
      if (extendsRange && this.sheetRange) {
        this.setSheetRange({ ...this.sheetRange, r2: rowIndex, c2: colIndex })
        return
      }
      this.setSheetRange({ r1: rowIndex, c1: colIndex, r2: rowIndex, c2: colIndex })
    },
    async selectSheetRange(range) {
      const row = this.list[range.r1]
      const column = this.sheetColumns[range.c1]
      if (!row || !column) return
      await this.$refs.sheetTable?.setSelectCell?.(row, column.key)
      this.setSheetRange(range)
      this.$refs.sheetWrap?.focus?.()
    },
    selectAllSheetCells() {
      if (!this.list.length || !this.sheetColumns.length) return
      this.selectSheetRange({
        r1: 0,
        c1: 0,
        r2: this.list.length - 1,
        c2: this.sheetColumns.length - 1,
      })
    },
    cloneSheetValue(value) {
      return value == null ? value : JSON.parse(JSON.stringify(value))
    },
    sameSheetValue(key, left, right) {
      if (key === 'target_codes') {
        const normalize = (value) => this.uniq(
          Array.isArray(value) ? value : this.parseCodes(value),
        )
        return JSON.stringify(normalize(left)) === JSON.stringify(normalize(right))
      }
      if (key === 'species_cross') {
        return JSON.stringify(this.splitSpeciesCross(left))
          === JSON.stringify(this.splitSpeciesCross(right))
      }
      return String(left ?? '').trim() === String(right ?? '').trim()
    },
    onSheetEditActived({ row, column }) {
      const key = column?.field
      if (!key) return
      if (
        this.sheetEditSource === 'keyboard'
        && this.sheetEditOriginal?.rowId === row.id
        && this.sheetEditOriginal?.key === key
      ) {
        return
      }
      this.sheetEditOriginal = {
        key,
        rowId: row.id,
        targetCodes: this.cloneSheetValue(row.target_codes),
        targetName: row.target_name,
        value: this.cloneSheetValue(row[key]),
      }
    },
    takeSheetEditOriginal(row, key) {
      const original = this.sheetEditOriginal
      this.sheetEditOriginal = null
      if (original?.rowId === row.id && original.key === key) {
        return this.cloneSheetValue(original.value)
      }
      return this.cloneSheetValue(this.rowBaselines.get(row.id)?.[key])
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
      if (reason === 'length') return `${label}不能超过 255 个字符`
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
      return this.searchTargetOptions(searchValue)
    },
    onSheetTargetPickerChange(row) {
      const codes = this.uniq(Array.isArray(row.target_codes) ? row.target_codes : [])
      row.target_codes = codes
      row.target_name = codes
        .map((code) => this.targetOptions.find((item) => item.snum === code)?.name || code)
        .join('&')
    },
    onSheetPickerVisibleChange({ visible }) {
      if (!visible) this.$refs.sheetTable?.clearEdit?.()
    },
    async restoreSheetSelectedCell() {
      const $table = this.$refs.sheetTable
      if (!$table || $table.getEditRecord?.()) return
      const row = this.list[this.pasteAnchor?.rowIndex]
      const key = this.pasteAnchor?.colKey
      if (!row || !key) return
      await $table.setSelectCell?.(row, key)
      if ($table.getEditRecord?.()) return
      const activeElement = document.activeElement
      const wrap = this.$refs.sheetWrap
      if (
        !activeElement
        || activeElement === document.body
        || wrap?.contains?.(activeElement)
        || activeElement.closest?.('.sheet-picker-popup')
      ) {
        wrap?.focus?.()
      }
    },
    onSheetEditClosed(context) {
      const operation = this.finishSheetEdit(context)
      this.pendingSheetOps.add(operation)
      this.$nextTick(() => this.restoreSheetSelectedCell())
      return operation.finally(() => this.pendingSheetOps.delete(operation))
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
      next.species_cross = this.splitSpeciesCross(next.species_cross)
      return next
    },
    replaceRow(saved) {
      const normalized = this.normalizeRow(saved)
      const index = this.list.findIndex((item) => item.id === saved.id)
      if (index >= 0) {
        this.list.splice(index, 1, { ...this.list[index], ...normalized })
      }
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
        payload[field] = field === 'species_cross'
          ? this.joinSpeciesCross(row.species_cross)
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
        if (!this.hasActiveFilters) {
          const nextTotal = (this.total || 0) + 1
          this.listQuery.page = Math.max(1, Math.ceil(nextTotal / this.listQuery.limit))
        }
        await this.getList()
        if (saved?.id) this.openEditor(saved)
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
      if (!this.canCopy) return
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
        await this.getList()
        if (saved?.id) this.openEditor(saved)
      } catch (err) {
        notifyApiError(err, { messages: SERUM_ERRORS.workbench.copy })
      } finally {
        this.loading = false
      }
    },
    async handleUnlist(row) {
      if (!this.canFullEdit) return
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
      this.destroySortable()
      if (this.viewMode !== 'workbench' || !this.canDragRows) return
      await this.$nextTick()
      const tbody = this.workbenchTbody()
      if (!tbody || initToken !== this.sortableInitToken || !tbody.isConnected) return
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
      const moved = this.list[oldIndex]
      const target = this.list[newIndex]
      if (!moved || !target) return
      if (!this.canEditField(moved, 'sort_order')) {
        ElMessage.warning('只能调整草稿状态的工作台记录')
        return
      }
      const expectedRows = this.list.map((row) => ({
        id: row.id,
        sort_order: Number(row.sort_order),
        priority: this.rowPriority(row),
      }))
      const ids = this.list.map((row) => row.id)
      const [draggedId] = ids.splice(oldIndex, 1)
      ids.splice(newIndex, 0, draggedId)
      this.loading = true
      try {
        await reorderWorkbench(ids, draggedId, expectedRows)
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
      const startColKey = this.pasteAnchor?.colKey || SHEET_COLUMNS[0].key
      let startColIndex = SHEET_COLUMNS.findIndex((column) => column.key === startColKey)
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
          const key = hasHeader ? headerKeys[cellIndex] : SHEET_COLUMNS[startColIndex + cellIndex]?.key
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
            colIndex: SHEET_COLUMNS.findIndex((column) => column.key === key),
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
          const activeColumn = SHEET_COLUMNS[range.c1]
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

<style scoped>
.app-container {
  position: relative;
  padding: var(--list-page-padding);
  background-color: var(--list-page-bg);
  min-height: 100%;
}
.workbench-console {
  position: relative;
  overflow: hidden;
  margin-bottom: var(--list-page-gap);
  background: linear-gradient(90deg, #ffffff 0%, #fbfcff 68%, #f6f9fd 100%);
  border: var(--list-surface-border);
  border-radius: var(--list-surface-radius);
  box-shadow: var(--list-surface-shadow);
}
.console-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-width: 0;
  padding: 14px 18px 12px;
}
.console-brand {
  display: flex;
  align-items: center;
  min-width: 0;
}
.title-copy {
  min-width: 0;
}
.page-title {
  margin: 0;
  color: var(--el-text-color-primary);
  font-size: var(--list-page-title-size);
  font-weight: var(--list-page-title-weight);
  letter-spacing: 0.01em;
}
.page-subtitle {
  max-width: 620px;
  margin: 4px 0 0;
  color: var(--list-page-subtitle-color);
  font-size: var(--list-page-subtitle-size);
  font-weight: var(--list-page-subtitle-weight);
}
.console-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.ready-summary {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 30px;
  padding: 0 11px;
  border: 1px solid rgba(103, 194, 58, 0.2);
  border-radius: 999px;
  background: rgba(240, 249, 235, 0.68);
  color: #5c7d4a;
  font-size: 12px;
  cursor: pointer;
  transition: 0.18s ease;
}
.ready-summary:hover,
.ready-summary.is-active {
  border-color: rgba(103, 194, 58, 0.42);
  background: #f0f9eb;
}
.ready-summary strong {
  color: #3f6f2b;
  font-size: 14px;
  font-variant-numeric: tabular-nums;
}
.ready-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--el-color-success);
  box-shadow: 0 0 0 4px rgba(103, 194, 58, 0.12);
}
.lifecycle-nav {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  padding: 0;
  margin: 0 12px 12px;
  overflow: hidden;
  background: #fff;
  border: 1px solid rgba(218, 225, 234, 0.92);
  border-radius: 10px;
}
.lifecycle-item {
  --stage-color: #8090a5;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 9px;
  min-width: 0;
  min-height: 56px;
  padding: 8px 14px;
  border: 0;
  border-right: 1px solid rgba(211, 220, 231, 0.78);
  background: transparent;
  color: var(--el-text-color-secondary);
  text-align: left;
  cursor: pointer;
  transition: background 0.16s ease, color 0.16s ease;
  user-select: none;
}
.lifecycle-item:last-child {
  border-right: 0;
}
.lifecycle-item:not(.is-active):hover {
  background: rgba(32, 45, 64, 0.035);
}
.lifecycle-item.is-active {
  background: color-mix(in srgb, var(--stage-color) 7%, white);
  color: var(--el-text-color-primary);
}
.stage-marker {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 9px;
  background: color-mix(in srgb, var(--stage-color) 11%, white);
  color: var(--stage-color);
  font-size: 10px;
  font-weight: 700;
  transition: background 0.16s ease, color 0.16s ease, box-shadow 0.16s ease;
}
.lifecycle-item.is-active .stage-marker {
  color: #fff;
  background: var(--stage-color);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--stage-color) 12%, transparent);
}
.stage-copy {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.stage-copy strong {
  font-size: 13px;
  font-weight: 620;
}
.lifecycle-item.is-active .stage-copy strong {
  color: color-mix(in srgb, var(--stage-color) 72%, #172033);
  font-weight: 680;
}
.stage-copy small {
  margin-top: 2px;
  overflow: hidden;
  color: var(--el-text-color-secondary);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.stage-count {
  color: var(--stage-color);
  font-size: 18px;
  font-variant-numeric: tabular-nums;
  font-weight: 680;
}
.stage-all { --stage-color: #0f8b8d; }
.stage-planned { --stage-color: #409eff; }
.stage-ongoing { --stage-color: #8b5cf6; }
.stage-completed { --stage-color: #43b97f; }
.stage-cancelled { --stage-color: #8a94a6; }
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
.view-toggle-button.is-sheet {
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary-light-5);
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
.action-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
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
.sheet-wrap {
  --vxe-ui-font-family: var(--font-family);
  --vxe-ui-font-size-small: 14px;

  display: flex;
  flex-direction: column;
  height: calc(100vh - 350px);
  min-height: 480px;
  font-family: var(--font-family);
  outline: none;
  user-select: none;
  -webkit-user-select: none;
}
.sheet-table-stage {
  position: relative;
  flex: 1;
  min-height: 0;
}
.sheet-table-stage :deep(.vxe-table) {
  height: 100%;
}
.sheet-wrap :deep(.vxe-table),
.sheet-wrap :deep(.vxe-body--column),
.sheet-wrap :deep(.vxe-cell) {
  user-select: none;
  -webkit-user-select: none;
}
.sheet-range-overlay {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 8;
  display: none;
  box-sizing: border-box;
  pointer-events: none;
  border: 2px solid var(--el-color-primary);
  transition:
    width 120ms ease-out,
    height 120ms ease-out,
    transform 120ms ease-out;
  will-change: width, height, transform;
}
.sheet-range-overlay.is-dragging {
  transition: none;
}
.sheet-wrap :deep(.vxe-body--column.col--selected),
.sheet-wrap :deep(.vxe-body--column.col--active) {
  box-shadow: none !important;
}
.sheet-wrap :deep(.is-sheet-selected) {
  background-color: var(--el-color-primary-light-9) !important;
}
.sheet-wrap :deep(.is-sheet-active) {
  background-color: var(--el-bg-color) !important;
}
.sheet-wrap :deep(.sheet-selectable-header) {
  cursor: pointer;
}
.sheet-wrap :deep(.sheet-selectable-header:hover) {
  background-color: var(--el-color-primary-light-9) !important;
}
.sheet-wrap :deep(.vxe-body--column.col--active > .vxe-cell),
.sheet-wrap :deep(.vxe-body--column.col--active > .vxe-cell > .vxe-cell--wrapper) {
  width: 100%;
  height: 100%;
}
.sheet-wrap :deep(.vxe-body--column.col--active > .vxe-cell) {
  padding: 0 !important;
}
.sheet-wrap :deep(.sheet-grid-editor.vxe-input),
.sheet-wrap :deep(.sheet-grid-editor.vxe-number-input),
.sheet-wrap :deep(.sheet-grid-editor.vxe-select) {
  width: 100%;
  height: 100%;
  background: transparent;
  border: 0;
  border-radius: 0;
  box-shadow: none;
}
.sheet-wrap :deep(.sheet-grid-editor .vxe-input--inner),
.sheet-wrap :deep(.sheet-grid-editor .vxe-number-input--input) {
  padding: var(--vxe-ui-table-cell-padding-small);
  background: transparent;
}
.sheet-picker-editor {
  position: relative;
  display: flex;
  align-items: center;
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  padding: var(--vxe-ui-table-cell-padding-small);
  overflow: hidden;
  line-height: var(--vxe-ui-table-row-line-height);
}
.sheet-picker-editor__value {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sheet-wrap :deep(.sheet-picker-control.vxe-select) {
  position: absolute;
  inset: 0;
  z-index: 1;
}
.sheet-wrap :deep(.sheet-picker-control.vxe-select > .vxe-input) {
  opacity: 0;
}
.sheet-wrap :deep(.sheet-grid-editor.vxe-select > .vxe-input) {
  height: 100%;
  border: 0 !important;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}
.sheet-wrap :deep(.sheet-date-editor .vxe-input--suffix) {
  display: none;
}
.sheet-wrap :deep(.sheet-grid-editor .vxe-number-input--prefix),
.sheet-wrap :deep(.sheet-grid-editor .vxe-number-input--suffix) {
  display: none;
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
.drawer-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
}
.drawer-heading {
  min-width: 0;
}
.drawer-title {
  margin: 0;
  color: var(--el-text-color-primary);
  font-size: 16px;
  font-weight: 650;
  line-height: 1.3;
}
.drawer-header-meta {
  margin: 2px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.3;
}
.drawer-close {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  margin: -2px -4px 0 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: #909399;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
}
.drawer-close:hover {
  color: var(--el-text-color-primary);
}
.drawer-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 28px;
  margin: 0 0 8px;
}
.drawer-toolbar-actions,
.drawer-nav {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  gap: 6px;
}
.drawer-toolbar-actions :deep(.action-cell) {
  justify-content: flex-start;
}
.drawer-nav :deep(.el-button) {
  height: 28px;
  min-height: 28px;
  padding: 0 10px;
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
.species-cross-select :deep(.el-select__selection),
.species-cross-select :deep(.el-select__tags) {
  flex-wrap: nowrap;
  min-width: 0;
}
.species-selected-text {
  max-width: none;
  overflow: visible;
  text-overflow: clip;
  white-space: nowrap;
}
</style>

<style>
.workbench-status-tag.is-editable {
  cursor: pointer;
}
.workbench-status-option-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 2px;
}
.workbench-status-option {
  width: 100%;
  padding: 7px 10px;
  border: 0;
  border-radius: var(--list-inner-radius);
  background: transparent;
  color: var(--el-text-color-regular);
  font: inherit;
  line-height: 18px;
  text-align: left;
  cursor: pointer;
  transition: background-color .16s ease, color .16s ease;
}
.workbench-status-option:hover,
.workbench-status-option.is-current {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
}
.workbench-status-option.is-current {
  font-weight: 600;
}
.sheet-picker-popup {
  --vxe-ui-font-size-small: 14px;

  min-width: 220px !important;
}
.sheet-picker-popup .vxe-select--panel-wrapper {
  overflow: hidden;
  border-color: var(--el-border-color-light);
  border-radius: 6px;
  box-shadow: var(--el-box-shadow-light);
}
.sheet-picker-popup .vxe-select--panel-search {
  padding: 8px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.sheet-picker-popup .vxe-select-search--input {
  border-color: var(--el-border-color);
  border-radius: 4px;
}
.sheet-picker-popup .vxe-select-option {
  padding: 0 12px;
}
.sheet-picker-popup .vxe-select-option.is--selected {
  background-color: var(--el-color-primary-light-9);
}
/* append-to-body 抽屉即使关掉灰色遮罩，仍有全屏 overlay 会吃掉点击 */
.workbench-drawer .el-drawer__header {
  margin-bottom: 0;
  padding: 10px 16px 6px;
}
.workbench-drawer .el-drawer__body {
  padding: 4px 16px 16px;
}
.workbench-drawer-overlay,
.el-overlay:has(.workbench-drawer) {
  pointer-events: none !important;
  background: transparent !important;
}
.workbench-drawer-overlay .el-overlay-dialog,
.workbench-drawer-overlay .el-drawer__container,
.el-overlay:has(.workbench-drawer) .el-overlay-dialog,
.el-overlay:has(.workbench-drawer) .el-drawer__container {
  pointer-events: none !important;
}
.workbench-drawer-overlay .el-drawer,
.el-overlay:has(.workbench-drawer) .el-drawer {
  pointer-events: auto;
}
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
