<template>
  <div class="app-container titer-order-page">
    <AdvancedOpsBar v-model="showAdvancedOps">
      <el-select
        v-model="listQuery.order_status"
        clearable
        placeholder="工单状态"
        style="width: 220px;"
        @change="handleFilter"
      >
        <el-option
          v-for="item in flowOrderStatusOptions"
          :key="item.value"
          :label="item.label"
          :value="item.value"
        />
      </el-select>
      <el-button type="warning" :icon="Download" @click="handleListExport">
        列表导出
      </el-button>
    </AdvancedOpsBar>

    <section class="workbench-panel">
      <div class="page-header-band">
        <div class="title-group">
          <h1 class="page-title">效价实验列表</h1>
          <p class="page-subtitle text-secondary">按效价工单安排负责人与检测日期，在列表中维护血清状态和效价小结。</p>
        </div>
        <div class="header-actions">
          <span class="total-count text-secondary">共 {{ total }} 条工单</span>
          <el-button
            type="primary"
            :class="{ 'no-permission-btn': !canEditTiterOrder() }"
            :title="!canEditTiterOrder() ? '您没有权限编辑效价工单' : ''"
            @click="openCreateDialog"
          >
            <el-icon><Plus /></el-icon>
            新增
          </el-button>
        </div>
      </div>

      <div class="stats-strip">
        <div
          class="stat-tile stat-blue stat-tile-interactive"
          :class="{ 'stat-tile-active': statFilterActive.unassigned }"
          @click="handleStatFilter('unassigned')"
        >
          <span class="stat-copy">
            <span class="stat-label">待安排</span>
            <small class="text-hint">未指定负责人</small>
          </span>
          <strong class="stat-value">{{ stats.unassigned }}</strong>
        </div>
        <div
          class="stat-tile stat-purple stat-tile-interactive"
          :class="{ 'stat-tile-active': statFilterActive.pending }"
          title="左键：已采血且未填检测日期；右键：未填检测日期"
          @click="handlePendingStatFilter('blooded')"
          @contextmenu.prevent="handlePendingStatFilter('empty')"
        >
          <span class="stat-copy">
            <span class="stat-label">待检测</span>
            <small class="text-hint">FACS {{ stats.pendingFacsPlates }} 板 · ELISA {{ stats.pendingElisaPlates }} 板</small>
          </span>
          <strong class="stat-value">{{ stats.pending }}</strong>
        </div>
        <div
          class="stat-tile stat-orange stat-tile-interactive"
          :class="{ 'stat-tile-active': statFilterActive.thisWeek }"
          title="左键：检测日期在本周；右键：已填检测日期但尚未改为已检测"
          @click="handleThisWeekStatFilter('week')"
          @contextmenu.prevent="handleThisWeekStatFilter('unsubmitted')"
        >
          <span class="stat-copy">
            <span class="stat-label">本周检测</span>
            <small class="text-hint">检测日期在本周</small>
          </span>
          <strong class="stat-value">{{ stats.thisWeek }}</strong>
        </div>
        <div
          class="stat-tile stat-red stat-tile-interactive"
          :class="{ 'stat-tile-active': statFilterActive.toReport }"
          @click="handleStatFilter('toReport')"
        >
          <span class="stat-copy">
            <span class="stat-label">待汇报</span>
            <small class="text-hint">已检测未写小结</small>
          </span>
          <strong class="stat-value">{{ stats.toReport }}</strong>
        </div>
        <div
          class="stat-tile stat-slate stat-tile-interactive"
          :class="{ 'stat-tile-active': statFilterActive.owners }"
          @click="handleStatFilter('owners')"
          @contextmenu.prevent="openOwnerStatsDialog"
        >
          <span class="stat-copy">
            <span class="stat-label">负责人</span>
            <small class="text-hint">效价人员与统计</small>
          </span>
          <strong class="stat-value">{{ allOwnerOptions.length }}</strong>
        </div>
      </div>

      <div class="filter-strip">
        <el-input
          v-model="listQuery.project_code"
          class="filter-item"
          clearable
          placeholder="项目编号"
          :prefix-icon="Search"
          @keyup.enter="handleFilter"
        />
        <el-select
          v-model="listQuery.target_name"
          class="filter-item"
          clearable
          filterable
          popper-class="titer-select-dropdown"
          :filter-method="filterMethodFor('targetFilterQuery')"
          placeholder="靶点"
          @clear="clearFilterQuery('targetFilterQuery')"
          @change="handleFilter"
        >
          <el-option
            v-for="item in filterOptions(allTargetOptions, targetFilterQuery)"
            :key="item"
            :label="item"
            :value="item"
          />
        </el-select>
        <el-select
          v-model="listQuery.assay_method"
          class="filter-item"
          clearable
          filterable
          popper-class="titer-select-dropdown"
          :filter-method="filterMethodFor('assayMethodFilterQuery')"
          placeholder="检测方法"
          @clear="clearFilterQuery('assayMethodFilterQuery')"
          @change="handleFilter"
        >
          <el-option label="FACS" :value="ASSAY_FILTER_FACS" />
          <el-option label="ELISA" :value="ASSAY_FILTER_ELISA" />
          <el-option label="FACS+ELISA" :value="ASSAY_FILTER_FACS_ELISA" />
          <el-option
            v-for="item in filterOptions(allAssayMethodOptions, assayMethodFilterQuery)"
            :key="item"
            :label="item"
            :value="item"
          />
        </el-select>
        <el-select
          v-model="listQuery.immune_owner"
          class="filter-item"
          clearable
          filterable
          popper-class="titer-select-dropdown"
          :filter-method="filterMethodFor('immuneOwnerFilterQuery')"
          placeholder="免疫负责人"
          @clear="clearFilterQuery('immuneOwnerFilterQuery')"
          @change="handleFilter"
        >
          <el-option
            v-for="name in filterOptions(allImmuneOwnerOptions, immuneOwnerFilterQuery)"
            :key="name"
            :label="name"
            :value="name"
          />
        </el-select>
        <el-select
          v-model="listQuery.titer_owner"
          class="filter-item"
          clearable
          filterable
          popper-class="titer-select-dropdown"
          :filter-method="filterMethodFor('ownerFilterQuery')"
          placeholder="效价负责人"
          @clear="clearFilterQuery('ownerFilterQuery')"
          @change="handleTiterOwnerFilterChange"
        >
          <el-option
            v-for="name in filterOptions(allOwnerOptions, ownerFilterQuery)"
            :key="name"
            :label="name"
            :value="name"
          />
        </el-select>
        <el-select
          v-model="listQuery.immune_status"
          class="filter-item"
          clearable
          filterable
          popper-class="titer-select-dropdown"
          :filter-method="filterMethodFor('immuneStatusFilterQuery')"
          placeholder="免疫状态"
          @clear="clearFilterQuery('immuneStatusFilterQuery')"
          @change="handleFilter"
        >
          <el-option
            v-for="item in filterOptions(allImmuneStatusOptions, immuneStatusFilterQuery)"
            :key="item"
            :label="item"
            :value="item"
          />
        </el-select>
        <el-date-picker
          v-model="bloodCollectionRange"
          class="filter-item"
          type="daterange"
          range-separator="至"
          start-placeholder="采血起始"
          end-placeholder="采血截止"
          value-format="YYYY-MM-DD"
          @change="handleFilter"
        />
        <el-date-picker
          v-model="testDatesRange"
          class="filter-item"
          type="daterange"
          range-separator="至"
          start-placeholder="检测起始"
          end-placeholder="检测截止"
          value-format="YYYY-MM-DD"
          @change="handleTestDatesFilterChange"
        />
        <el-select
          v-model="listQuery.serum_status"
          class="filter-item"
          clearable
          placeholder="血清状态"
          @change="handleSerumStatusFilterChange"
        >
          <el-option
            v-for="item in allSerumStatusOptions"
            :key="item"
            :label="item"
            :value="item"
          />
        </el-select>
        <el-select
          v-model="listQuery.priority"
          class="filter-item"
          clearable
          placeholder="检测优先级"
          @change="handleFilter"
        >
          <el-option
            v-for="item in titerPriorityOptions"
            :key="item"
            :label="item"
            :value="item"
          />
        </el-select>
        <el-select
          v-model="listQuery.summary_status"
          class="filter-item"
          clearable
          placeholder="小结状态"
          @change="handleSummaryStatusFilterChange"
        >
          <el-option label="未填写小结" value="empty" />
          <el-option label="已填写小结" value="filled" />
        </el-select>
        <div class="filter-actions">
          <span class="more-toggle-btn" title="高级操作" @click="showAdvancedOps = !showAdvancedOps">
            <el-icon><Tools /></el-icon>
          </span>
          <el-button type="primary" :icon="Search" @click="handleFilter">查询</el-button>
          <el-button :icon="Refresh" @click="resetFilter">重置</el-button>
        </div>
      </div>
    </section>

    <el-card shadow="never" class="table-card" :body-style="{ padding: '15px' }">
      <div
        ref="tablePlateWrap"
        class="table-plate-wrap"
        :class="{ 'is-plate-dragging': plateDragging }"
      >
        <el-table
          ref="orderTable"
          v-loading="listLoading"
          :data="list"
          border
          stripe
          fit
          highlight-current-row
          style="width: 100%"
          :header-cell-style="{ background: '#F5F7FA', color: '#606266', fontWeight: 'bold' }"
          @sort-change="handleSortChange"
        >
        <el-table-column label="项目编号" prop="project_code" align="left" sortable="custom" fixed min-width="130" show-overflow-tooltip>
          <template #default="{ row }">
            <span
              class="code-text"
              @click="goDetail(row)"
              @contextmenu.prevent="openOrderDialog(row)"
            >{{ row.project_code || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="靶点" prop="target_name" align="center" min-width="100" show-overflow-tooltip />
        <el-table-column label="笼位" prop="cage_position" align="center" min-width="90" show-overflow-tooltip />
        <el-table-column label="采血日期" prop="blood_collection_date" align="center" sortable="custom" min-width="110" />
        <el-table-column prop="mouse_count" align="center" min-width="80" class-name="plate-col-mouse">
          <template #header>
            <el-popover v-model:visible="colFilterOpen.mouse_count" trigger="click" width="220">
              <el-radio-group v-model="listQuery.mouse_count_zero" size="small" class="col-filter-zero">
                <el-radio-button label="">全部</el-radio-button>
                <el-radio-button label="hide">排除0</el-radio-button>
                <el-radio-button label="only">只看0</el-radio-button>
              </el-radio-group>
              <div class="col-filter-range">
                <el-input-number v-model="listQuery.mouse_count_min" :min="0" :controls="false" placeholder="最小" />
                <span>—</span>
                <el-input-number v-model="listQuery.mouse_count_max" :min="0" :controls="false" placeholder="最大" />
              </div>
              <div class="col-filter-actions">
                <el-button size="small" @click="resetColFilter('mouse_count')">重置</el-button>
                <el-button size="small" type="primary" @click="applyColFilter('mouse_count')">确定</el-button>
              </div>
              <template #reference>
                <button type="button" class="col-filter-head" :class="{ 'is-active': isColFilterActive('mouse_count') }" @click.stop>只数</button>
              </template>
            </el-popover>
          </template>
          <template #default="{ row, $index }">
            <div
              class="plate-select-cell"
              @mousedown="onPlateCellMouseDown('mouse', $index, $event)"
              @mouseenter="onPlateCellMouseEnter('mouse', $index)"
              @contextmenu.prevent="onPlateCellContextMenu('mouse')"
            >
              {{ row.mouse_count ?? 0 }}
            </div>
          </template>
        </el-table-column>
        <el-table-column label="检测方法" prop="assay_method" align="center" min-width="130" show-overflow-tooltip />
        <el-table-column prop="facs_plate_count" align="center" min-width="80" class-name="plate-col-facs">
          <template #header>
            <el-popover v-model:visible="colFilterOpen.facs_plate" trigger="click" width="220">
              <el-radio-group v-model="listQuery.facs_plate_zero" size="small" class="col-filter-zero">
                <el-radio-button label="">全部</el-radio-button>
                <el-radio-button label="hide">排除0</el-radio-button>
                <el-radio-button label="only">只看0</el-radio-button>
              </el-radio-group>
              <div class="col-filter-range">
                <el-input-number v-model="listQuery.facs_plate_min" :min="0" :controls="false" placeholder="最小" />
                <span>—</span>
                <el-input-number v-model="listQuery.facs_plate_max" :min="0" :controls="false" placeholder="最大" />
              </div>
              <div class="col-filter-actions">
                <el-button size="small" @click="resetColFilter('facs_plate')">重置</el-button>
                <el-button size="small" type="primary" @click="applyColFilter('facs_plate')">确定</el-button>
              </div>
              <template #reference>
                <button type="button" class="col-filter-head" :class="{ 'is-active': isColFilterActive('facs_plate') }" @click.stop>FACS</button>
              </template>
            </el-popover>
          </template>
          <template #default="{ row, $index }">
            <div
              class="plate-select-cell"
              @mousedown="onPlateCellMouseDown('facs', $index, $event)"
              @mouseenter="onPlateCellMouseEnter('facs', $index)"
              @contextmenu.prevent="onPlateCellContextMenu('facs')"
            >
              {{ row.facs_plate_count ?? 0 }}
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="elisa_plate_count" align="center" min-width="80" class-name="plate-col-elisa">
          <template #header>
            <el-popover v-model:visible="colFilterOpen.elisa_plate" trigger="click" width="220">
              <el-radio-group v-model="listQuery.elisa_plate_zero" size="small" class="col-filter-zero">
                <el-radio-button label="">全部</el-radio-button>
                <el-radio-button label="hide">排除0</el-radio-button>
                <el-radio-button label="only">只看0</el-radio-button>
              </el-radio-group>
              <div class="col-filter-range">
                <el-input-number v-model="listQuery.elisa_plate_min" :min="0" :controls="false" placeholder="最小" />
                <span>—</span>
                <el-input-number v-model="listQuery.elisa_plate_max" :min="0" :controls="false" placeholder="最大" />
              </div>
              <div class="col-filter-actions">
                <el-button size="small" @click="resetColFilter('elisa_plate')">重置</el-button>
                <el-button size="small" type="primary" @click="applyColFilter('elisa_plate')">确定</el-button>
              </div>
              <template #reference>
                <button type="button" class="col-filter-head" :class="{ 'is-active': isColFilterActive('elisa_plate') }" @click.stop>ELISA</button>
              </template>
            </el-popover>
          </template>
          <template #default="{ row, $index }">
            <div
              class="plate-select-cell"
              @mousedown="onPlateCellMouseDown('elisa', $index, $event)"
              @mouseenter="onPlateCellMouseEnter('elisa', $index)"
              @contextmenu.prevent="onPlateCellContextMenu('elisa')"
            >
              {{ row.elisa_plate_count ?? 0 }}
            </div>
          </template>
        </el-table-column>
        <el-table-column label="免疫负责人" prop="immune_owner" align="center" min-width="100" show-overflow-tooltip />
        <el-table-column label="效价负责人" align="center" min-width="180" class-name="plate-col-owner">
          <template #default="{ row, $index }">
            <div
              class="plate-select-cell plate-select-cell--field"
              @mousedown="onFieldCellMouseDown('owner', $index, $event)"
              @mouseenter="onPlateCellMouseEnter('owner', $index)"
              @contextmenu.prevent="onPlateCellContextMenu('owner')"
            >
              <el-select
                :ref="'ownerSelect_' + row.id"
                v-model="row.titer_owners"
                class="owner-select inline-cell-control"
                size="small"
                multiple
                allow-create
                filterable
                :reserve-keyword="false"
                :disabled="!canEditTiterOrderOwner()"
                popper-class="titer-select-dropdown"
                placeholder="选择负责人"
                @change="onTiterOwnerChange(row)"
              >
                <template #tag="{ data, deleteTag, selectDisabled }">
                  <div
                    v-for="item in data"
                    :key="ownerTagName(item)"
                    class="el-select__selected-item"
                  >
                    <el-tag
                      class="owner-tag"
                      :style="ownerTagStyle(item)"
                      :closable="!selectDisabled"
                      disable-transitions
                      @close="(event) => deleteTag(event, item)"
                    >
                      {{ ownerTagName(item) }}
                    </el-tag>
                  </div>
                </template>
                <el-option v-for="name in allOwnerOptions" :key="name" :label="name" :value="name" />
              </el-select>
            </div>
          </template>
        </el-table-column>
        <el-table-column
          label="检测日期"
          prop="test_dates_display"
          align="center"
          sortable="custom"
          min-width="160"
          class-name="plate-col-test-dates"
        >
          <template #default="{ row, $index }">
            <div
              class="plate-select-cell plate-select-cell--field"
              @mousedown="onFieldCellMouseDown('test_dates', $index, $event)"
              @mouseenter="onPlateCellMouseEnter('test_dates', $index)"
              @contextmenu.prevent="onPlateCellContextMenu('test_dates')"
            >
              <el-tooltip
                :content="row.test_dates_display"
                placement="top"
                :disabled="!isOverflowTooltip(row.id, 'test_dates')"
              >
                <div
                  class="cell-tooltip-target"
                  @mouseenter="handleOverflowMouseEnter($event, row.id, 'test_dates', row.test_dates_display)"
                  @mouseleave="handleOverflowMouseLeave(row.id, 'test_dates')"
                >
                  <el-date-picker
                    v-model="row.test_dates"
                    class="test-dates-picker inline-cell-control"
                    size="small"
                    type="dates"
                    value-format="YYYY-MM-DD"
                    placeholder="选择检测日"
                    :disabled="!canEditTiterOrderRecord(row)"
                    @change="onTestDatesChange(row)"
                  />
                </div>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
        <el-table-column
          label="血清状态"
          prop="serum_status"
          align="center"
          sortable="custom"
          min-width="140"
          class-name="status-column-cell plate-col-serum-status"
        >
          <template #default="{ row, $index }">
            <div
              class="plate-select-cell plate-select-cell--field"
              @mousedown="onFieldCellMouseDown('serum_status', $index, $event)"
              @mouseenter="onPlateCellMouseEnter('serum_status', $index)"
              @contextmenu.prevent="onPlateCellContextMenu('serum_status')"
            >
              <el-select
                v-model="row.serum_status"
                class="inline-cell-control serum-status-select"
                :class="row.serum_status ? 'status-tone-' + getSerumTiterStatusTagType(row.serum_status) : ''"
                size="small"
                clearable
                :disabled="!canEditTiterOrderRecordOpen()"
                placeholder="选择状态"
                @change="onSerumStatusChange(row)"
              >
                <el-option
                  v-for="item in titerSerumStatusOptions"
                  :key="item"
                  :label="item"
                  :value="item"
                />
              </el-select>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="优先级" prop="priority" align="center" sortable="custom" min-width="120" class-name="status-column-cell plate-col-priority">
          <template #default="{ row, $index }">
            <div
              class="plate-select-cell plate-select-cell--field"
              @mousedown="onFieldCellMouseDown('priority', $index, $event)"
              @mouseenter="onPlateCellMouseEnter('priority', $index)"
              @contextmenu.prevent="onPlateCellContextMenu('priority')"
            >
              <el-select
                v-model="row.priority"
                class="inline-cell-control priority-select"
                :class="'status-tone-' + getTiterPriorityTone(row.priority)"
                size="small"
                :disabled="!canEditTiterOrderRecordOpen()"
                @change="onPriorityChange(row)"
              >
                <el-option
                  v-for="item in titerPriorityOptions"
                  :key="item"
                  :label="item"
                  :value="item"
                />
              </el-select>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="备注" align="center" min-width="180">
          <template #default="{ row }">
            <el-tooltip
              :content="row.remark"
              placement="top"
              :disabled="!isOverflowTooltip(row.id, 'remark')"
            >
              <div
                class="cell-tooltip-target"
                @mouseenter="handleOverflowMouseEnter($event, row.id, 'remark', row.remark)"
                @mouseleave="handleOverflowMouseLeave(row.id, 'remark')"
              >
                <el-input
                  v-model="row.remark"
                  class="inline-cell-control"
                  size="small"
                  maxlength="500"
                  placeholder="备注"
                  :disabled="!canEditTiterOrderRecord(row)"
                  @change="saveRow(row, '备注')"
                />
              </div>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="效价小结" align="center" min-width="180">
          <template #default="{ row }">
            <el-tooltip
              :content="row.summary"
              placement="top"
              :disabled="!isOverflowTooltip(row.id, 'summary')"
            >
              <div
                class="cell-tooltip-target"
                @mouseenter="handleOverflowMouseEnter($event, row.id, 'summary', row.summary)"
                @mouseleave="handleOverflowMouseLeave(row.id, 'summary')"
              >
                <el-input
                  v-model="row.summary"
                  class="inline-cell-control"
                  size="small"
                  maxlength="500"
                  placeholder="填写小结"
                  :disabled="!canEditTiterOrderRecord(row)"
                  @change="saveRow(row, '效价小结')"
                />
              </div>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="工单状态" prop="order_status" align="center" min-width="100" class-name="status-column-cell">
          <template #default="{ row }">
            <el-tag
              v-if="row.order_status"
              class="status-tag"
              :type="orderStatusTagType(row.order_status)"
              effect="plain"
            >
              {{ row.order_status_label }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="免疫状态" prop="immune_status" align="center" min-width="100" class-name="status-column-cell">
          <template #default="{ row }">
            <el-tag
              v-if="row.immune_status"
              class="status-tag"
              :type="getSerumProjectStatusTagType(row.immune_status)"
              effect="plain"
            >
              {{ row.immune_status }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" min-width="236" align="center">
          <template #default="{ row }">
            <el-button-group>
              <el-button
                class="table-action-btn"
                size="small"
                type="primary"
                plain
                :icon="Document"
                @click="goInstrumentOrder(row)"
                @contextmenu.prevent="openInstrumentFlowList(row)"
              >
                工单
              </el-button>
              <el-button class="table-action-btn" size="small" type="warning" plain :icon="DataAnalysis" @click="goSequencing(row)">
                测序
              </el-button>
              <el-button
                class="table-action-btn"
                size="small"
                type="success"
                plain
                :icon="TrendCharts"
                :class="{ 'no-permission-btn': !canEditTiter(row) }"
                :title="!canEditTiter(row) ? '您没有权限编辑此项目' : ''"
                @click="goTiterAudit(row)"
              >
                数据
              </el-button>
            </el-button-group>
          </template>
        </el-table-column>
        </el-table>

        <div v-if="plateDragging" class="plate-select-overlay">
          <div
            v-for="rect in plateOverlayRects"
            :key="rect.key"
            class="plate-select-region"
            :style="rect.style"
          />
        </div>
        <TransitionGroup v-else name="plate-region" tag="div" class="plate-select-overlay">
          <div
            v-for="rect in plateOverlayRects"
            :key="rect.key"
            class="plate-select-region"
            :style="rect.style"
          />
        </TransitionGroup>

        <Transition name="plate-bubble">
          <div
            v-if="plateBubbleVisible"
            class="plate-select-bubble"
            :style="plateBubbleStyle"
          >
            {{ plateSelectBubbleText }}
          </div>
        </Transition>
      </div>

      <el-pagination
        v-show="total > 0"
        v-model:current-page="listQuery.page"
        v-model:page-size="listQuery.limit"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        class="pagination"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </el-card>

    <TiterOrderCreateDialog
      v-model="createDialogVisible"
      :edit-order="dialogEditOrder"
      :can-save-batch="canEditTiterOrder()"
      :can-delete="canDeleteTiterOrder()"
      @changed="onTiterOrderChanged"
      @closed="dialogEditOrder = null"
    />

    <TiterInstrumentOrderDialogs ref="instrumentOrderDialogsRef" />

    <el-dialog
      v-model="ownerStatsVisible"
      title="效价实验统计Ciallo～(∠・ω< )⌒★"
      width="960px"
      append-to-body
      class="owner-stats-dialog"
      @opened="loadOwnerStats"
    >
      <div class="owner-stats-toolbar">
        <div class="owner-stats-filter">
          <span class="owner-stats-filter-label">检测月份</span>
          <el-date-picker
            v-model="ownerStatsMonthRange"
            class="owner-stats-month-picker"
            type="monthrange"
            range-separator="至"
            start-placeholder="起始月"
            end-placeholder="截止月"
            value-format="YYYY-MM"
            clearable
            @change="loadOwnerStats"
          />
          <el-button size="small" :icon="Download" @click="exportOwnerStatsExcel">导出 Excel</el-button>
        </div>
        <span class="owner-stats-note text-hint">实验按人头计，板数多人共担按人均分 · 已完成为「已检测 / 已交接」</span>
      </div>
      <el-table
        v-loading="ownerStatsLoading"
        :data="ownerStatsTableRows"
        border
        highlight-current-row
        max-height="440"
        class="owner-stats-table"
        :row-class-name="ownerStatsRowClassName"
        :header-cell-style="ownerStatsHeaderStyle"
        :cell-style="ownerStatsCellStyle"
        empty-text="暂无负责人数据"
      >
        <el-table-column label="负责人" fixed min-width="88" align="center">
          <template #default="{ row }">
            <span :class="{ 'owner-stats-total-name': row.isTotal }">{{ row.owner }}</span>
          </template>
        </el-table-column>
        <el-table-column label="总计" align="center">
          <el-table-column prop="total_orders" label="实验" min-width="60" align="center" :formatter="workloadOrderFormatter" />
          <el-table-column prop="total_facs" label="FACS" min-width="60" align="center" :formatter="workloadPlateFormatter" />
          <el-table-column prop="total_elisa" label="ELISA" min-width="60" align="center" :formatter="workloadPlateFormatter" />
        </el-table-column>
        <el-table-column label="已完成" align="center">
          <el-table-column prop="completed_orders" label="实验" min-width="60" align="center" :formatter="workloadOrderFormatter" />
          <el-table-column prop="completed_facs" label="FACS" min-width="60" align="center" :formatter="workloadPlateFormatter" />
          <el-table-column prop="completed_elisa" label="ELISA" min-width="60" align="center" :formatter="workloadPlateFormatter" />
        </el-table-column>
        <el-table-column label="未完成" align="center">
          <el-table-column prop="remaining_orders" label="实验" min-width="60" align="center" :formatter="workloadOrderFormatter" />
          <el-table-column prop="remaining_facs" label="FACS" min-width="60" align="center" :formatter="workloadPlateFormatter" />
          <el-table-column prop="remaining_elisa" label="ELISA" min-width="60" align="center" :formatter="workloadPlateFormatter" />
        </el-table-column>
        <el-table-column v-if="ownerStatsHasPeriod" :label="ownerStatsPeriodLabel" align="center">
          <el-table-column prop="period_orders" label="实验" min-width="60" align="center" :formatter="workloadOrderFormatter" />
          <el-table-column prop="period_facs" label="FACS" min-width="60" align="center" :formatter="workloadPlateFormatter" />
          <el-table-column prop="period_elisa" label="ELISA" min-width="60" align="center" :formatter="workloadPlateFormatter" />
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script>
import { DataAnalysis, Document, Download, Plus, Refresh, Search, Tools, TrendCharts } from '@element-plus/icons-vue';
import { markRaw } from 'vue';
import * as XLSX from 'xlsx';
import {
  ElButton,
  ElButtonGroup,
  ElCard,
  ElDatePicker,
  ElDialog,
  ElIcon,
  ElInput,
  ElInputNumber,
  ElMessage,
  ElOption,
  ElPagination,
  ElPopover,
  ElRadioButton,
  ElRadioGroup,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTag,
  ElTooltip,
} from 'element-plus';

import { notifyApiError } from '#/api/errors';
import { skipGlobalErrorHandler } from '#/api/request';
import {
  fetchTiterOrderList,
  fetchTiterOrderMeta,
  fetchTiterOrderOwnerStats,
  fetchTiterOrderStats,
  exportTiterOrderList,
  saveTiterOrder,
} from '#/api/serum';
import AdvancedOpsBar from '#/components/AdvancedOpsBar.vue';
import { downloadListExcel, excelTimestamp } from '#/utils/downloadExcel';
import { getSerumProjectStatusTagType, getSerumTiterStatusTagType, getTiterPriorityTone, mergeTiterSerumStatusOptions, TITER_PRIORITY_DEFAULT, TITER_PRIORITY_OPTIONS, TITER_SERUM_STATUS_OPTIONS } from '#/utils/serumProjectStatus';
import { FLOW_WORK_ORDER_STATUS_OPTIONS, orderStatusTagType } from '#/utils/megaFlowWorkOrderStatus';
import {
  canDeleteTiterOrder,
  canEditSerumTiter,
  canEditTiterOrder,
  canEditTiterOrderOwner,
  canEditTiterOrderRecord,
  canEditTiterOrderRecordOpen,
  getSerumUserName,
} from '#/utils/serumPermission';
import { useUserStore } from '@vben/stores';

import { shouldRefreshTabData } from '#/utils/staleTabRefresh';
import TiterInstrumentOrderDialogs from './TiterInstrumentOrderDialogs.vue';
import TiterOrderCreateDialog from './TiterOrderCreateDialog.vue';

const TITER_ORDER_LIST_FILTER_KEY = 'titerOrderListFilters';

const DEFAULT_STATS = {
  pending: 0,
  pendingElisaPlates: 0,
  pendingFacsPlates: 0,
  thisWeek: 0,
  toReport: 0,
  unassigned: 0,
};

const STATS_AFFECTING_LABELS = new Set(['效价负责人', '检测日期', '血清状态', '效价小结']);

/** 可划选后改一处同步的列；值仅用于选区计数，无板数含义 */
const FIELD_SELECT_COLUMNS = new Set(['owner', 'test_dates', 'serum_status', 'priority']);

const ASSAY_FILTER_FACS = '__facs__';
const ASSAY_FILTER_ELISA = '__elisa__';
const ASSAY_FILTER_FACS_ELISA = '__facs_elisa__';

const SERUM_STATUS_PENDING_TEST = '已采血';

/** 统计「待汇报」：已检测且效价小结为空 */
const SERUM_STATUS_TESTED = '已检测';

function formatLocalDate(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

/** 与后端 _current_week_range 一致：周一至周日 */
function getCurrentWeekRange() {
  const now = new Date();
  const weekday = now.getDay();
  const diffToMonday = weekday === 0 ? -6 : 1 - weekday;
  const monday = new Date(now);
  monday.setDate(now.getDate() + diffToMonday);
  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);
  return [formatLocalDate(monday), formatLocalDate(sunday)];
}

function isSameDateRange(left, right) {
  return Array.isArray(left)
    && Array.isArray(right)
    && left.length === 2
    && right.length === 2
    && left[0] === right[0]
    && left[1] === right[1];
}

function createDefaultStatFilterActive() {
  return {
    unassigned: false,
    pending: false,
    thisWeek: false,
    toReport: false,
    owners: false,
  };
}

function flattenOwnerStatsItem(item) {
  const pick = (src, prefix) => ({
    [`${prefix}_orders`]: Number(src?.orders) || 0,
    [`${prefix}_facs`]: Number(src?.facs) || 0,
    [`${prefix}_elisa`]: Number(src?.elisa) || 0,
  });
  return {
    owner: item.owner,
    ...pick(item.total, 'total'),
    ...pick(item.completed, 'completed'),
    ...pick(item.remaining, 'remaining'),
    ...pick(item.period, 'period'),
  };
}

function formatWorkloadOrder(value) {
  return String(Math.round(Number(value) || 0));
}

function formatWorkloadPlate(value) {
  return (Number(value) || 0).toFixed(1);
}

function currentMonthKey() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

function formatMonthLabel(monthKey) {
  const [year, month] = String(monthKey || '').split('-');
  if (!year || !month) {
    return monthKey || '';
  }
  return `${year}年${Number(month)}月`;
}

function formatMonthRangeLabel(startMonth, endMonth) {
  if (!endMonth || startMonth === endMonth) {
    return formatMonthLabel(startMonth);
  }
  return `${formatMonthLabel(startMonth)} - ${formatMonthLabel(endMonth)}`;
}

/** 效价负责人标签：17 色法式马卡龙（清透 pastel，色相拉开） */
const OWNER_TAG_COLORS = [
  { bg: '#eef4fc', color: '#70b0e8' }, // 天蓝
  { bg: '#ffe6e4', color: '#e06058' }, // 珊瑚
  { bg: '#e6f8ec', color: '#38b068' }, // 翠绿
  { bg: '#f6eaf6', color: '#b068b0' }, // 丁香
  { bg: '#fff8dc', color: '#d8b820' }, // 柠檬
  { bg: '#e8ecfc', color: '#5c78d0' }, // 矢车菊
  { bg: '#fff0e6', color: '#e07850' }, // 蜜桃
  { bg: '#eee6f8', color: '#7860b8' }, // 靛紫
  { bg: '#daf0f0', color: '#28a0a0' }, // 青碧
  { bg: '#ffe8f0', color: '#d85890' }, // 浅樱
  { bg: '#e8ecf6', color: '#5c6cc4' }, // 蓝莓
  { bg: '#fff8e0', color: '#c8a828' }, // 香草
  { bg: '#f0e6f6', color: '#9a60c0' }, // 薰衣草
  { bg: '#e6faf4', color: '#34b898' }, // 薄荷
  { bg: '#ffeff4', color: '#e888a8' }, // 玫瑰
  { bg: '#e8f6fc', color: '#50a8d8' }, // 冰蓝
  { bg: '#f4eef6', color: '#a878a0' }, // 香芋
];

export default {
  name: 'SerumTiterOrderList',
  components: {
    ElButton,
    ElButtonGroup,
    ElCard,
    ElDatePicker,
    ElDialog,
    ElIcon,
    ElInput,
    ElInputNumber,
    ElOption,
    ElPagination,
    ElPopover,
    ElRadioButton,
    ElRadioGroup,
    ElSelect,
    ElTable,
    ElTableColumn,
    ElTag,
    ElTooltip,
    AdvancedOpsBar,
    Plus,
    Tools,
    TiterInstrumentOrderDialogs,
    TiterOrderCreateDialog,
  },
  setup() {
    const userStore = useUserStore();
    return { userStore };
  },
  computed: {
    currentUserInfo() {
      return this.userStore.userInfo || {};
    },
    currentUserName() {
      return getSerumUserName(this.currentUserInfo);
    },
    currentOwnerName() {
      return this.currentUserName.split(' ')[0] || '';
    },
    ownerStatsHasPeriod() {
      const range = this.ownerStatsMonthRange;
      return Array.isArray(range) && Boolean(range[0]);
    },
    ownerStatsPeriodLabel() {
      const [startMonth, endMonth] = this.ownerStatsMonthRange;
      return formatMonthRangeLabel(startMonth, endMonth || startMonth);
    },
    ownerStatsTableRows() {
      const rows = this.ownerStatsItems.map((item) => flattenOwnerStatsItem(item));
      if (!rows.length) {
        return rows;
      }
      const sortKey = this.ownerStatsHasPeriod ? 'period_orders' : 'total_orders';
      rows.sort((left, right) => {
        const diff = (right[sortKey] || 0) - (left[sortKey] || 0);
        return diff || String(left.owner).localeCompare(String(right.owner), 'zh-CN');
      });
      const totalRow = {
        ...flattenOwnerStatsItem({ owner: '合计', ...this.ownerStatsSummary }),
        owner: '合计',
        isTotal: true,
      };
      return [...rows, totalRow];
    },
    plateBubbleVisible() {
      if (this.plateDragging) {
        return Boolean(this.plateSelectColumn);
      }
      return Boolean(this.plateSelectColumn)
        && Object.keys(this.plateSelectedCounts).length > 0
        && this.plateOverlayRects.length > 0;
    },
    plateSelectBubbleText() {
      const column = this.plateSelectColumn;
      if (!column) {
        return '';
      }
      const { sum, count } = this.getPlateSelectionSummary(column, this.plateDragging);
      if (FIELD_SELECT_COLUMNS.has(column)) {
        return count > 0 ? `已选 ${count} 条 · 改一处同步` : '划选多行后改一处同步';
      }
      if (column === 'mouse') {
        return `鼠鼠共计 ${sum} 只`;
      }
      const label = column === 'facs' ? 'FACS' : 'ELISA';
      return `${label} ${sum} 板 · ${count} 条`;
    },
  },
  data() {
    return {
      ASSAY_FILTER_FACS,
      ASSAY_FILTER_ELISA,
      ASSAY_FILTER_FACS_ELISA,
      DataAnalysis: markRaw(DataAnalysis),
      Document: markRaw(Document),
      Download: markRaw(Download),
      Refresh: markRaw(Refresh),
      Search: markRaw(Search),
      TrendCharts: markRaw(TrendCharts),
      _filterMethodCache: Object.create(null),
      createDialogVisible: false,
      showAdvancedOps: false,
      dialogEditOrder: null,
      list: [],
      listLoading: false,
      listQuery: {
        limit: 20,
        page: 1,
        project_code: '',
        assay_method: '',
        immune_owner: '',
        immune_status: '',
        serum_status: '',
        summary_status: '',
        priority: '',
        test_dates_empty: false,
        tested_unsubmitted: false,
        order_status: '',
        target_name: '',
        titer_owner: '',
        mouse_count_zero: '',
        mouse_count_min: null,
        mouse_count_max: null,
        facs_plate_zero: '',
        facs_plate_min: null,
        facs_plate_max: null,
        elisa_plate_zero: '',
        elisa_plate_min: null,
        elisa_plate_max: null,
        sort_field: undefined,
        sort_order: undefined,
      },
      allOwnerOptions: [],
      allTargetOptions: [],
      allAssayMethodOptions: [],
      allImmuneOwnerOptions: [],
      allImmuneStatusOptions: [],
      allSerumStatusOptions: mergeTiterSerumStatusOptions(),
      titerSerumStatusOptions: [...TITER_SERUM_STATUS_OPTIONS],
      titerPriorityOptions: [...TITER_PRIORITY_OPTIONS],
      flowOrderStatusOptions: FLOW_WORK_ORDER_STATUS_OPTIONS,
      ownerFilterQuery: '',
      targetFilterQuery: '',
      assayMethodFilterQuery: '',
      immuneOwnerFilterQuery: '',
      immuneStatusFilterQuery: '',
      stats: { ...DEFAULT_STATS },
      bloodCollectionRange: [],
      testDatesRange: [],
      overflowCellKeys: {},
      statFilterActive: createDefaultStatFilterActive(),
      testDateStatScope: '',
      pendingStatScope: '',
      applyingStatDateRange: false,
      ownerStatsVisible: false,
      ownerStatsLoading: false,
      ownerStatsItems: [],
      ownerStatsSummary: { total: {}, completed: {}, remaining: {}, period: {} },
      ownerStatsMonthRange: [],
      total: 0,
      plateSelectColumn: null,
      plateSelectedCounts: {},
      plateDragging: false,
      plateDragPending: null,
      plateDragStartIndex: -1,
      plateDragEndIndex: -1,
      plateBubbleStyle: {
        top: '0px',
        left: '0px',
        transform: 'translate3d(0px, 0px, 0) translateX(-50%)',
      },
      plateBubblePos: null,
      plateOverlayRects: [],
      tabDataFetchedAt: 0,
      colFilterOpen: {
        mouse_count: false,
        facs_plate: false,
        elisa_plate: false,
      },
    };
  },
  mounted() {
    this.restoreListFilters();
    this.loadPageMeta();
    this.getList();
    this.onPlateDragMouseUp = () => this.finishPlateDrag();
    this.onPlateTableScroll = () => this.updatePlateSelectionUi();
    document.addEventListener('mouseup', this.onPlateDragMouseUp);
    this.$nextTick(() => this.bindPlateTableScroll());
  },
  activated() {
    if (shouldRefreshTabData(this.tabDataFetchedAt)) {
      this.refreshTabData();
    }
  },
  beforeRouteLeave(_to, _from, next) {
    this.persistListFilters();
    next();
  },
  beforeUnmount() {
    this.persistListFilters();
    document.removeEventListener('mouseup', this.onPlateDragMouseUp);
    this.unbindPlateTableScroll();
  },
  methods: {
    persistListFilters() {
      sessionStorage.setItem(
        TITER_ORDER_LIST_FILTER_KEY,
        JSON.stringify({
          listQuery: { ...this.listQuery, sort_field: undefined, sort_order: undefined },
          bloodCollectionRange: this.bloodCollectionRange,
          testDatesRange: this.testDatesRange,
          statFilterActive: this.statFilterActive,
          testDateStatScope: this.testDateStatScope,
          pendingStatScope: this.pendingStatScope,
        }),
      );
    },
    restoreListFilters() {
      const raw = sessionStorage.getItem(TITER_ORDER_LIST_FILTER_KEY);
      if (!raw) {
        return;
      }
      try {
        const state = JSON.parse(raw);
        if (state.listQuery) {
          Object.assign(this.listQuery, state.listQuery);
        }
        if (state.bloodCollectionRange) {
          this.bloodCollectionRange = state.bloodCollectionRange;
        }
        if (state.testDatesRange) {
          this.testDatesRange = state.testDatesRange;
        }
        if (state.statFilterActive) {
          this.statFilterActive = state.statFilterActive;
        }
        if (state.testDateStatScope !== undefined) {
          this.testDateStatScope = state.testDateStatScope;
        }
        if (state.pendingStatScope !== undefined) {
          this.pendingStatScope = state.pendingStatScope;
        }
        this.listQuery.test_dates_empty = Boolean(this.listQuery.test_dates_empty);
        this.listQuery.tested_unsubmitted = Boolean(this.listQuery.tested_unsubmitted);
      } catch {
        /* ignore */
      }
    },
    getSerumProjectStatusTagType,
    getSerumTiterStatusTagType,
    getTiterPriorityTone,
    orderStatusTagType,
    bindPlateTableScroll() {
      this.unbindPlateTableScroll();
      const tableEl = this.$refs.orderTable?.$el;
      const scrollEl = tableEl?.querySelector('.el-table__body-wrapper .el-scrollbar__wrap')
        || tableEl?.querySelector('.el-table__body-wrapper');
      if (scrollEl) {
        scrollEl.addEventListener('scroll', this.onPlateTableScroll, { passive: true });
        this.plateTableBodyEl = scrollEl;
      }
    },
    unbindPlateTableScroll() {
      if (this.plateTableBodyEl) {
        this.plateTableBodyEl.removeEventListener('scroll', this.onPlateTableScroll);
        this.plateTableBodyEl = null;
      }
    },
    getTableDisplayRows() {
      const data = this.$refs.orderTable?.store?.states?.data;
      if (Array.isArray(data)) {
        return data;
      }
      if (Array.isArray(data?.value)) {
        return data.value;
      }
      return this.list;
    },
    getPlateSelectValue(row, column) {
      if (FIELD_SELECT_COLUMNS.has(column)) {
        return 1;
      }
      if (column === 'mouse') {
        return Number(row.mouse_count) || 0;
      }
      const value = column === 'facs' ? row.facs_plate_count : row.elisa_plate_count;
      return Number(value) || 0;
    },
    getPlateColClass(column) {
      const map = {
        facs: 'plate-col-facs',
        elisa: 'plate-col-elisa',
        mouse: 'plate-col-mouse',
        owner: 'plate-col-owner',
        test_dates: 'plate-col-test-dates',
        serum_status: 'plate-col-serum-status',
        priority: 'plate-col-priority',
      };
      return map[column] || '';
    },
    /** 点在下拉/日期上先挂起，拖到其他行再亮选区，避免单击闪框 */
    onFieldCellMouseDown(column, index, event) {
      if (event.button !== 0) {
        return;
      }
      if (event.target.closest?.('.el-select, .el-date-editor, .el-input, .el-tag')) {
        this.plateDragPending = { column, index };
        return;
      }
      this.plateDragPending = null;
      this.onPlateCellMouseDown(column, index, event);
    },
    canEditFieldForRow(row, label) {
      if (label === '效价负责人') {
        return this.canEditTiterOrderOwner();
      }
      if (label === '检测日期' || label === '备注' || label === '效价小结') {
        return this.canEditTiterOrderRecord(row);
      }
      if (label === '血清状态' || label === '优先级') {
        return this.canEditTiterOrderRecordOpen();
      }
      return false;
    },
    async syncSelectedField(sourceRow, column, label, assignFn) {
      const keys = this.plateSelectColumn === column
        ? Object.keys(this.plateSelectedCounts)
        : [];
      const inSelection = keys.some((id) => String(id) === String(sourceRow.id));
      const selected = inSelection && keys.length > 1
        ? this.getTableDisplayRows().filter((row) => keys.includes(String(row.id)))
        : [sourceRow];
      // 赋值前跳过无权限行，界面也不改
      const targets = selected.filter((row) => this.canEditFieldForRow(row, label));
      const skipped = selected.length - targets.length;
      if (!targets.length) {
        ElMessage.warning(`您没有权限编辑${label}`);
        return;
      }
      if (targets.length === 1) {
        await this.saveRow(targets[0], label);
        if (skipped > 0) {
          ElMessage.warning(`${label}：已跳过 ${skipped} 条无权限`);
        }
        return;
      }
      for (const target of targets) {
        if (String(target.id) !== String(sourceRow.id)) {
          assignFn(target, sourceRow);
        }
      }
      const results = await Promise.all(
        targets.map((target) => this.saveRow(target, label, { silent: true })),
      );
      const ok = results.filter(Boolean).length;
      if (ok > 0) {
        ElMessage.success(`${label}已保存 ${ok} 条`);
        if (STATS_AFFECTING_LABELS.has(label)) {
          this.refreshStats();
        }
      }
      if (skipped > 0) {
        ElMessage.warning(`${label}：已跳过 ${skipped} 条无权限`);
      }
    },
    getPlateSelectSegments(column) {
      const sorted = this.getPlateSelectRowIndices(column);
      if (!sorted.length) {
        return [];
      }
      const segments = [];
      let start = sorted[0];
      let prev = sorted[0];
      for (let index = 1; index < sorted.length; index += 1) {
        if (sorted[index] === prev + 1) {
          prev = sorted[index];
          continue;
        }
        segments.push([start, prev]);
        start = sorted[index];
        prev = sorted[index];
      }
      segments.push([start, prev]);
      return segments;
    },
    getPlateSelectRowIndices(column) {
      const indices = new Set();
      const rows = this.getTableDisplayRows();
      if (column === this.plateSelectColumn) {
        for (const rowId of Object.keys(this.plateSelectedCounts)) {
          const index = rows.findIndex((row) => String(row.id) === String(rowId));
          if (index >= 0) {
            indices.add(index);
          }
        }
      }
      if (this.plateDragging && column === this.plateSelectColumn) {
        const min = Math.min(this.plateDragStartIndex, this.plateDragEndIndex);
        const max = Math.max(this.plateDragStartIndex, this.plateDragEndIndex);
        for (let index = min; index <= max; index += 1) {
          indices.add(index);
        }
      }
      return [...indices].sort((left, right) => left - right);
    },
    updatePlateSelectionUi() {
      this.$nextTick(() => {
        const wrapEl = this.$refs.tablePlateWrap;
        const tableEl = this.$refs.orderTable?.$el;
        const column = this.plateSelectColumn;
        if (!wrapEl || !tableEl || !column) {
          this.plateOverlayRects = [];
          return;
        }
        const colClass = this.getPlateColClass(column);
        const bodyRows = tableEl.querySelector('.el-table__body-wrapper tbody')?.rows;
        if (!bodyRows?.length) {
          this.plateOverlayRects = [];
          return;
        }
        const wrapRect = wrapEl.getBoundingClientRect();
        const segments = this.getPlateSelectSegments(column);
        const rects = [];

        for (const [start, end] of segments) {
          const topRow = bodyRows[start];
          const bottomRow = bodyRows[end];
          if (!topRow || !bottomRow) {
            continue;
          }
          const topCell = topRow.querySelector(`td.${colClass}`);
          const bottomCell = bottomRow.querySelector(`td.${colClass}`);
          if (!topCell || !bottomCell) {
            continue;
          }
          const topRect = topCell.getBoundingClientRect();
          const bottomRect = bottomCell.getBoundingClientRect();
          rects.push({
            key: this.plateDragging ? `drag-${rects.length}` : `${start}-${end}`,
            style: {
              top: `${topRect.top - wrapRect.top}px`,
              left: `${topRect.left - wrapRect.left}px`,
              width: `${topRect.width}px`,
              height: `${bottomRect.bottom - topRect.top}px`,
            },
          });
        }

        this.plateOverlayRects = rects;

        if (rects.length) {
          const last = rects[rects.length - 1];
          const x = parseFloat(last.style.left) + parseFloat(last.style.width) / 2;
          const y = parseFloat(last.style.top) + parseFloat(last.style.height) + 6;
          // 短时长 + 按距微调；用 transform 走合成层，才能接近显示器刷新率
          const prev = this.plateBubblePos;
          let duration = 0.12;
          if (prev) {
            const dist = Math.hypot(x - prev.x, y - prev.y);
            duration = Math.min(0.2, Math.max(0.08, dist / 1400));
          }
          this.plateBubblePos = { x, y };
          this.plateBubbleStyle = {
            top: '0px',
            left: '0px',
            transform: `translate3d(${x}px, ${y}px, 0) translateX(-50%)`,
            transitionDuration: `${duration.toFixed(3)}s`,
          };
        }
      });
    },
    getPlateSelectionSummary(column, includeDragPreview = false) {
      const selected = column === this.plateSelectColumn ? this.plateSelectedCounts : {};
      let sum = 0;
      let count = 0;
      const seen = new Set();
      for (const [rowId, plates] of Object.entries(selected)) {
        seen.add(String(rowId));
        sum += plates;
        count += 1;
      }
      if (includeDragPreview && this.plateDragging && column === this.plateSelectColumn) {
        const rows = this.getTableDisplayRows();
        const min = Math.min(this.plateDragStartIndex, this.plateDragEndIndex);
        const max = Math.max(this.plateDragStartIndex, this.plateDragEndIndex);
        for (let index = min; index <= max; index += 1) {
          const row = rows[index];
          if (row?.id == null) {
            continue;
          }
          const rowId = String(row.id);
          if (seen.has(rowId)) {
            continue;
          }
          seen.add(rowId);
          sum += this.getPlateSelectValue(row, column);
          count += 1;
        }
      }
      return { sum, count };
    },
    onPlateCellMouseDown(column, index, event) {
      if (event.button !== 0) {
        return;
      }
      event.preventDefault();
      this.plateDragPending = null;
      // 换列：立刻清选区，不做淡出，避免和左右滑动叠在一起发卡
      if (this.plateSelectColumn && this.plateSelectColumn !== column) {
        this.plateSelectedCounts = {};
        this.plateOverlayRects = [];
        this.plateDragStartIndex = -1;
        this.plateDragEndIndex = -1;
      }
      this.plateSelectColumn = column;
      this.plateDragging = true;
      this.plateDragStartIndex = index;
      this.plateDragEndIndex = index;
      this.updatePlateSelectionUi();
    },
    onPlateCellMouseEnter(column, index) {
      const pending = this.plateDragPending;
      if (pending) {
        if (pending.column !== column || pending.index === index) {
          return;
        }
        this.plateDragPending = null;
        if (this.plateSelectColumn && this.plateSelectColumn !== column) {
          this.plateSelectedCounts = {};
          this.plateOverlayRects = [];
        }
        this.plateSelectColumn = column;
        this.plateDragging = true;
        this.plateDragStartIndex = pending.index;
        this.plateDragEndIndex = index;
        document.activeElement?.blur?.();
        this.updatePlateSelectionUi();
        return;
      }
      if (!this.plateDragging || column !== this.plateSelectColumn) {
        return;
      }
      if (this.plateDragEndIndex === index) {
        return;
      }
      this.plateDragEndIndex = index;
      this.updatePlateSelectionUi();
    },
    finishPlateDrag() {
      if (this.plateDragPending) {
        this.plateDragPending = null;
        return;
      }
      if (!this.plateDragging) {
        return;
      }
      const column = this.plateSelectColumn;
      const rows = this.getTableDisplayRows();
      const min = Math.min(this.plateDragStartIndex, this.plateDragEndIndex);
      const max = Math.max(this.plateDragStartIndex, this.plateDragEndIndex);
      const isClick = min === max;
      let nextCounts = { ...this.plateSelectedCounts };

      if (isClick) {
        const row = rows[min];
        if (row?.id != null) {
          if (Object.prototype.hasOwnProperty.call(nextCounts, row.id)) {
            delete nextCounts[row.id];
          } else {
            nextCounts[row.id] = this.getPlateSelectValue(row, column);
          }
        }
      } else {
        for (let index = min; index <= max; index += 1) {
          const row = rows[index];
          if (row?.id != null) {
            nextCounts[row.id] = this.getPlateSelectValue(row, column);
          }
        }
      }

      this.plateDragging = false;
      this.plateDragStartIndex = -1;
      this.plateDragEndIndex = -1;

      if (!Object.keys(nextCounts).length) {
        this.clearPlateSelection();
        return;
      }

      this.plateSelectColumn = column;
      this.plateSelectedCounts = nextCounts;
      this.updatePlateSelectionUi();
    },
    onPlateCellContextMenu(column) {
      if (this.plateSelectColumn !== column && !this.plateDragging) {
        return;
      }
      this.clearPlateSelection();
    },
    clearPlateSelection() {
      this.plateSelectColumn = null;
      this.plateSelectedCounts = {};
      this.plateDragging = false;
      this.plateDragPending = null;
      this.plateDragStartIndex = -1;
      this.plateDragEndIndex = -1;
      this.plateOverlayRects = [];
      this.plateBubblePos = null;
    },
    buildQuery() {
      const { summary_status, project_code, test_dates_empty, tested_unsubmitted, ...rest } = this.listQuery;
      const payload = {
        ...rest,
        ...this.buildProjectCodeFilter(project_code),
        summary_empty: summary_status === 'empty',
        summary_filled: summary_status === 'filled',
      };
      this.appendDateRange(payload, this.bloodCollectionRange, 'blood_collection_start', 'blood_collection_end');
      if (test_dates_empty) {
        payload.test_dates_empty = true;
      } else if (tested_unsubmitted) {
        payload.tested_unsubmitted = true;
      } else {
        this.appendDateRange(payload, this.testDatesRange, 'test_dates_start', 'test_dates_end');
      }
      if (this.statFilterActive.unassigned) {
        payload.titer_owner_unassigned = true;
      }
      return payload;
    },
    applyColFilter(prefix) {
      this.colFilterOpen[prefix] = false;
      this.listQuery.page = 1;
      this.persistListFilters();
      this.getList();
    },
    isColFilterActive(prefix) {
      return Boolean(this.listQuery[`${prefix}_zero`])
        || this.listQuery[`${prefix}_min`] != null
        || this.listQuery[`${prefix}_max`] != null;
    },
    resetColFilter(prefix) {
      this.listQuery[`${prefix}_zero`] = '';
      this.listQuery[`${prefix}_min`] = null;
      this.listQuery[`${prefix}_max`] = null;
      this.applyColFilter(prefix);
    },
    appendDateRange(payload, range, startKey, endKey) {
      if (Array.isArray(range) && range.length === 2 && range[0] && range[1]) {
        payload[startKey] = range[0];
        payload[endKey] = range[1];
      }
    },
    buildProjectCodeFilter(projectCode) {
      const value = String(projectCode || '').trim();
      if (!value) {
        return {};
      }
      const separators = [',', '\t', '\n', '\r', '，', '、', ' '];
      if (separators.some((sep) => value.includes(sep))) {
        const project_codes = value.split(/[,\t\n\r，、 ]+/).map((code) => code.trim()).filter(Boolean);
        return project_codes.length ? { project_codes } : {};
      }
      return { project_code: value };
    },
    filterMethodFor(queryKey) {
      if (!this._filterMethodCache[queryKey]) {
        this._filterMethodCache[queryKey] = (query) => {
          this[queryKey] = query;
        };
      }
      return this._filterMethodCache[queryKey];
    },
    clearFilterQuery(queryKey) {
      this[queryKey] = '';
    },
    filterOptions(dataArray, query) {
      const queryLower = (query || '').toLowerCase();
      if (!queryLower) {
        return dataArray;
      }
      return dataArray
        .filter((item) => item.toLowerCase().includes(queryLower))
        .sort((a, b) => {
          const aStarts = a.toLowerCase().startsWith(queryLower);
          const bStarts = b.toLowerCase().startsWith(queryLower);
          return aStarts === bStarts ? a.localeCompare(b, 'zh-CN') : (aStarts ? -1 : 1);
        });
    },
    cellOverflowKey(rowId, field) {
      return `${rowId}-${field}`;
    },
    isOverflowTooltip(rowId, field) {
      return !!this.overflowCellKeys[this.cellOverflowKey(rowId, field)];
    },
    getOverflowElement(root) {
      return (
        root.querySelector('.el-input__inner')
        || root.querySelector('input')
        || root.querySelector('.el-input__wrapper')
        || root.querySelector('.el-date-editor .el-input__wrapper')
        || root
      );
    },
    isElementOverflow(element) {
      if (!element) {
        return false;
      }
      return element.scrollWidth > element.clientWidth || element.scrollHeight > element.clientHeight;
    },
    handleOverflowMouseEnter(event, rowId, field, content) {
      if (this.plateDragging || this.plateDragPending) {
        return;
      }
      const key = this.cellOverflowKey(rowId, field);
      if (!content) {
        this.overflowCellKeys = { ...this.overflowCellKeys, [key]: false };
        return;
      }
      const target = this.getOverflowElement(event.currentTarget);
      this.overflowCellKeys = { ...this.overflowCellKeys, [key]: this.isElementOverflow(target) };
    },
    handleOverflowMouseLeave(rowId, field) {
      if (this.plateDragging || this.plateDragPending) {
        return;
      }
      const key = this.cellOverflowKey(rowId, field);
      this.overflowCellKeys = { ...this.overflowCellKeys, [key]: false };
    },
    async loadPageMeta() {
      try {
        const meta = await fetchTiterOrderMeta(skipGlobalErrorHandler);
        this.stats = { ...DEFAULT_STATS, ...meta.stats };
        this.allOwnerOptions = meta.owners || [];
        this.allTargetOptions = meta.targets || [];
        this.allAssayMethodOptions = meta.assay_methods || [];
        this.allImmuneOwnerOptions = meta.immune_owners || [];
        this.allImmuneStatusOptions = meta.immune_statuses || [];
        this.allSerumStatusOptions = mergeTiterSerumStatusOptions(meta.serum_statuses);
      } catch (error) {
        notifyApiError(error, { messages: { default: '加载效价列表信息失败' } });
      }
    },
    async refreshStats() {
      try {
        const stats = await fetchTiterOrderStats(skipGlobalErrorHandler);
        this.stats = { ...DEFAULT_STATS, ...stats };
      } catch (error) {
        notifyApiError(error, { messages: { default: '刷新统计失败' } });
      }
    },
    mergeOwnerOptions(names) {
      let changed = false;
      for (const name of names || []) {
        const trimmed = String(name || '').trim();
        if (trimmed && !this.allOwnerOptions.includes(trimmed)) {
          this.allOwnerOptions.push(trimmed);
          changed = true;
        }
      }
      if (changed) {
        this.allOwnerOptions.sort((a, b) => a.localeCompare(b, 'zh-CN'));
      }
    },
    onTiterOrderChanged() {
      this.getList();
      this.refreshStats();
    },
    refreshTabData() {
      this.getList();
      this.refreshStats();
    },
    getList() {
      this.listLoading = true;
      fetchTiterOrderList(this.buildQuery(), skipGlobalErrorHandler)
        .then((response) => {
          this.list = Array.isArray(response.items)
            ? response.items.map((item) => ({
                ...item,
                titer_owners: Array.isArray(item.titer_owners) ? item.titer_owners : [],
                test_dates: Array.isArray(item.test_dates) ? item.test_dates : [],
                test_dates_display: item.test_dates_display || '',
                priority: item.priority || TITER_PRIORITY_DEFAULT,
              }))
            : [];
          this.total = Number(response.total) || 0;
        })
        .catch((error) => {
          this.list = [];
          this.total = 0;
          notifyApiError(error, { messages: { default: '加载效价工单失败' } });
        })
        .finally(() => {
          this.listLoading = false;
          this.tabDataFetchedAt = Date.now();
          this.$nextTick(() => {
            this.bindPlateTableScroll();
            this.updatePlateSelectionUi();
          });
        });
    },
    goDetail(row) {
      this.$router.push({ path: '/serum/detail', query: { id: row.project_id } });
    },
    openOrderDialog(row) {
      if (!row?.id) {
        return;
      }
      if (!this.canEditTiterOrder()) {
        ElMessage.warning('您没有权限编辑此工单');
        return;
      }
      this.dialogEditOrder = row;
      this.createDialogVisible = true;
    },
    goInstrumentOrder(row) {
      this.$refs.instrumentOrderDialogsRef?.handleLeftClick(row, {
        canEdit: this.canEditTiterOrderRecord(row),
      });
    },
    openInstrumentFlowList(row) {
      this.$refs.instrumentOrderDialogsRef?.handleRightClick(row, {
        canEdit: this.canEditTiterOrderRecord(row),
      });
    },
    goSequencing(_row) {
      ElMessage.info('测序功能待接入');
    },
    goTiterAudit(row) {
      if (!this.canEditTiter(row)) {
        ElMessage.warning('您没有权限编辑此项目');
        return;
      }
      this.$router.push({ path: '/serum/titer', query: { id: row.project_id } });
    },
    handleCurrentChange(page) {
      this.listQuery.page = page;
      this.getList();
    },
    handleFilter() {
      this.clearPlateSelection();
      this.listQuery.page = 1;
      this.getList();
    },
    handleSortChange({ prop, order }) {
      const sort_field = order ? prop : undefined;
      const sort_order = order === 'ascending' ? 'asc' : order === 'descending' ? 'desc' : undefined;
      if (this.listQuery.sort_field === sort_field && this.listQuery.sort_order === sort_order) {
        return;
      }
      this.listQuery.sort_field = sort_field;
      this.listQuery.sort_order = sort_order;
      this.listQuery.page = 1;
      this.getList();
    },
    async handleListExport() {
      try {
        await downloadListExcel(
          () => exportTiterOrderList(this.buildQuery()),
          `效价实验列表_${excelTimestamp()}.xlsx`,
        );
      } catch (error) {
        notifyApiError(error, { messages: { default: '列表导出失败，请重试' } });
      }
    },
    openOwnerStatsDialog() {
      const month = currentMonthKey();
      this.ownerStatsMonthRange = [month, month];
      this.ownerStatsVisible = true;
    },
    loadOwnerStats() {
      this.ownerStatsLoading = true;
      const [monthStart, monthEnd] = this.ownerStatsMonthRange;
      fetchTiterOrderOwnerStats(monthStart ? { monthStart, monthEnd: monthEnd || monthStart } : {})
        .then((data) => {
          this.ownerStatsItems = data.items;
          this.ownerStatsSummary = data.summary;
        })
        .catch((error) => notifyApiError(error, { messages: { default: '加载负责人统计失败' } }))
        .finally(() => {
          this.ownerStatsLoading = false;
        });
    },
    exportOwnerStatsExcel() {
      const rows = this.ownerStatsTableRows;
      if (!rows.length) {
        ElMessage.warning('暂无数据可导出');
        return;
      }
      const subCols = ['实验', 'FACS', 'ELISA'];
      const groups = ['总计', '已完成', '未完成'];
      if (this.ownerStatsHasPeriod) {
        groups.push(this.ownerStatsPeriodLabel);
      }
      const headerRow1 = ['负责人'];
      groups.forEach((label) => {
        headerRow1.push(label, '', '');
      });
      const headerRow2 = ['', ...groups.flatMap(() => subCols)];
      const body = rows.map((row) => {
        const line = [
          row.owner,
          formatWorkloadOrder(row.total_orders), formatWorkloadPlate(row.total_facs), formatWorkloadPlate(row.total_elisa),
          formatWorkloadOrder(row.completed_orders), formatWorkloadPlate(row.completed_facs), formatWorkloadPlate(row.completed_elisa),
          formatWorkloadOrder(row.remaining_orders), formatWorkloadPlate(row.remaining_facs), formatWorkloadPlate(row.remaining_elisa),
        ];
        if (this.ownerStatsHasPeriod) {
          line.push(
            formatWorkloadOrder(row.period_orders),
            formatWorkloadPlate(row.period_facs),
            formatWorkloadPlate(row.period_elisa),
          );
        }
        return line;
      });
      const sheet = XLSX.utils.aoa_to_sheet([headerRow1, headerRow2, ...body]);
      const merges = [{ s: { r: 0, c: 0 }, e: { r: 1, c: 0 } }];
      groups.forEach((_label, index) => {
        const startCol = 1 + index * 3;
        merges.push({ s: { r: 0, c: startCol }, e: { r: 0, c: startCol + 2 } });
      });
      sheet['!merges'] = merges;
      const workbook = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(workbook, sheet, '效价实验统计');
      const range = this.ownerStatsMonthRange;
      const monthTag = Array.isArray(range) && range[0]
        ? `_${range[0]}${range[1] && range[1] !== range[0] ? `-${range[1]}` : ''}`
        : '';
      XLSX.writeFile(workbook, `效价实验统计${monthTag}.xlsx`);
    },
    workloadOrderFormatter(_row, _column, value) {
      return formatWorkloadOrder(value);
    },
    workloadPlateFormatter(_row, _column, value) {
      return formatWorkloadPlate(value);
    },
    ownerStatsZone(prop = '') {
      if (prop.startsWith('total_')) {
        return { bg: '#fff8f9', headerBg: '#fff0f3', color: '#606266' };
      }
      if (prop.startsWith('completed_')) {
        return { bg: '#f6ffed', headerBg: '#edf9f0', color: '#389e6b' };
      }
      if (prop.startsWith('remaining_')) {
        return { bg: '#fffbe6', headerBg: '#fff7e8', color: '#d48806' };
      }
      if (prop.startsWith('period_')) {
        return { bg: '#f5faff', headerBg: '#eef6ff', color: '#337ecc' };
      }
      return null;
    },
    ownerStatsRowClassName({ row }) {
      return row.isTotal ? 'owner-stats-summary-row' : '';
    },
    ownerStatsHeaderStyle({ column }) {
      const zone = this.ownerStatsZone(column?.property || '');
      return {
        background: zone?.headerBg || '#F5F7FA',
        color: zone?.color || '#606266',
        fontWeight: 'bold',
      };
    },
    ownerStatsCellStyle({ row, column }) {
      const zone = this.ownerStatsZone(column?.property || '');
      if (row.isTotal) {
        return {
          fontWeight: 700,
          background: '#eaf4ff',
          color: zone?.color || '#303133',
        };
      }
      if (!zone) {
        return {};
      }
      return {
        background: zone.bg,
        color: zone.color,
        fontWeight: 600,
      };
    },
    handleStatFilter(key) {
      const turningOff = this.statFilterActive[key];
      this.statFilterActive[key] = !turningOff;
      if (key === 'unassigned') {
        if (!turningOff) {
          this.listQuery.titer_owner = '';
          this.ownerFilterQuery = '';
          this.statFilterActive.owners = false;
        }
      } else if (key === 'toReport') {
        if (turningOff) {
          if (this.listQuery.serum_status === SERUM_STATUS_TESTED) {
            this.listQuery.serum_status = '';
          }
          if (this.listQuery.summary_status === 'empty') {
            this.listQuery.summary_status = '';
          }
        } else {
          this.clearPendingStatFilter();
          this.clearThisWeekStatFilter();
          this.listQuery.serum_status = SERUM_STATUS_TESTED;
          this.listQuery.summary_status = 'empty';
        }
      } else if (key === 'owners') {
        if (turningOff) {
          if (this.listQuery.titer_owner === this.currentOwnerName) {
            this.listQuery.titer_owner = '';
            this.ownerFilterQuery = '';
          }
        } else if (this.currentOwnerName) {
          this.statFilterActive.unassigned = false;
          this.listQuery.titer_owner = this.currentOwnerName;
        } else {
          this.statFilterActive.owners = false;
          ElMessage.warning('无法识别当前用户姓名');
        }
      }
      this.handleFilter();
    },
    handlePendingStatFilter(scope) {
      const turningOff = this.statFilterActive.pending && this.pendingStatScope === scope;
      if (turningOff) {
        this.clearPendingStatFilter();
      } else {
        this.statFilterActive.pending = true;
        this.pendingStatScope = scope;
        this.statFilterActive.toReport = false;
        this.clearThisWeekStatFilter();
        this.listQuery.test_dates_empty = true;
        this.listQuery.serum_status = scope === 'blooded' ? SERUM_STATUS_PENDING_TEST : '';
        if (this.listQuery.summary_status === 'empty') {
          this.listQuery.summary_status = '';
        }
      }
      this.handleFilter();
    },
    clearPendingStatFilter(options = {}) {
      const clearSerum = options.clearSerum !== false
        && this.statFilterActive.pending
        && this.pendingStatScope === 'blooded';
      this.statFilterActive.pending = false;
      this.pendingStatScope = '';
      this.listQuery.test_dates_empty = false;
      if (clearSerum && this.listQuery.serum_status === SERUM_STATUS_PENDING_TEST) {
        this.listQuery.serum_status = '';
      }
    },
    handleThisWeekStatFilter(scope) {
      const turningOff = this.statFilterActive.thisWeek && this.testDateStatScope === scope;
      if (turningOff) {
        this.clearThisWeekStatFilter();
      } else {
        this.statFilterActive.thisWeek = true;
        this.testDateStatScope = scope;
        this.clearPendingStatFilter({ clearSerum: false });
        this.statFilterActive.toReport = false;
        if (this.listQuery.summary_status === 'empty') {
          this.listQuery.summary_status = '';
        }
        if (scope === 'unsubmitted') {
          this.testDatesRange = [];
          this.listQuery.tested_unsubmitted = true;
          this.listQuery.serum_status = '';
        } else {
          this.listQuery.tested_unsubmitted = false;
          this.applyingStatDateRange = true;
          this.testDatesRange = getCurrentWeekRange();
          this.$nextTick(() => {
            this.applyingStatDateRange = false;
          });
        }
      }
      this.handleFilter();
    },
    clearThisWeekStatFilter() {
      this.statFilterActive.thisWeek = false;
      this.testDateStatScope = '';
      this.testDatesRange = [];
      this.listQuery.tested_unsubmitted = false;
    },
    handleTiterOwnerFilterChange() {
      if (this.listQuery.titer_owner) {
        this.statFilterActive.unassigned = false;
      }
      if (this.listQuery.titer_owner !== this.currentOwnerName) {
        this.statFilterActive.owners = false;
      }
      this.handleFilter();
    },
    handleSerumStatusFilterChange() {
      if (this.statFilterActive.pending && this.pendingStatScope === 'blooded'
        && this.listQuery.serum_status !== SERUM_STATUS_PENDING_TEST) {
        this.clearPendingStatFilter({ clearSerum: false });
      }
      if (this.listQuery.serum_status !== SERUM_STATUS_TESTED) {
        this.statFilterActive.toReport = false;
      }
      this.handleFilter();
    },
    handleSummaryStatusFilterChange() {
      if (this.listQuery.summary_status !== 'empty') {
        this.statFilterActive.toReport = false;
      }
      this.handleFilter();
    },
    handleTestDatesFilterChange() {
      if (Array.isArray(this.testDatesRange) && this.testDatesRange.length === 2 && this.testDatesRange[0]) {
        this.clearPendingStatFilter({ clearSerum: false });
        this.listQuery.tested_unsubmitted = false;
        if (this.testDateStatScope === 'unsubmitted') {
          this.statFilterActive.thisWeek = false;
          this.testDateStatScope = '';
        }
      }
      if (this.applyingStatDateRange) {
        this.handleFilter();
        return;
      }
      const weekRange = getCurrentWeekRange();
      if (isSameDateRange(this.testDatesRange, weekRange)) {
        this.statFilterActive.thisWeek = true;
        this.testDateStatScope = 'week';
      } else if (this.testDateStatScope !== 'unsubmitted') {
        this.statFilterActive.thisWeek = false;
        this.testDateStatScope = '';
      }
      this.handleFilter();
    },
    handleSizeChange(size) {
      this.listQuery.limit = size;
      this.listQuery.page = 1;
      this.getList();
    },
    resetFilter() {
      this.clearPlateSelection();
      this.listQuery = {
        limit: this.listQuery.limit,
        page: 1,
        project_code: '',
        assay_method: '',
        immune_owner: '',
        immune_status: '',
        serum_status: '',
        summary_status: '',
        priority: '',
        test_dates_empty: false,
        tested_unsubmitted: false,
        order_status: '',
        target_name: '',
        titer_owner: '',
        mouse_count_zero: '',
        mouse_count_min: null,
        mouse_count_max: null,
        facs_plate_zero: '',
        facs_plate_min: null,
        facs_plate_max: null,
        elisa_plate_zero: '',
        elisa_plate_min: null,
        elisa_plate_max: null,
        sort_field: undefined,
        sort_order: undefined,
      };
      this.$refs.orderTable?.clearSort?.();
      this.testDatesRange = [];
      this.bloodCollectionRange = [];
      this.targetFilterQuery = '';
      this.ownerFilterQuery = '';
      this.assayMethodFilterQuery = '';
      this.immuneOwnerFilterQuery = '';
      this.immuneStatusFilterQuery = '';
      this.statFilterActive = createDefaultStatFilterActive();
      this.testDateStatScope = '';
      this.pendingStatScope = '';
      this.applyingStatDateRange = false;
      this.colFilterOpen = { mouse_count: false, facs_plate: false, elisa_plate: false };
      this.persistListFilters();
      this.getList();
    },
    openCreateDialog() {
      if (!this.canEditTiterOrder()) {
        ElMessage.warning('您没有权限编辑效价工单');
        return;
      }
      this.dialogEditOrder = null;
      this.createDialogVisible = true;
    },
    canEditTiterOrder() {
      return canEditTiterOrder(this.currentUserInfo);
    },
    canDeleteTiterOrder() {
      return canDeleteTiterOrder(this.currentUserInfo);
    },
    canEditTiterOrderOwner() {
      return canEditTiterOrderOwner(this.currentUserInfo);
    },
    canEditTiterOrderRecord(row) {
      return canEditTiterOrderRecord(this.currentUserInfo, row);
    },
    canEditTiterOrderRecordOpen() {
      return canEditTiterOrderRecordOpen(this.currentUserInfo);
    },
    canEditTiter(row) {
      return canEditSerumTiter(this.currentUserInfo, {
        owner: row.immune_owner,
        titer_owners: row.titer_owners,
      });
    },
    ownerTagName(data) {
      if (data == null) {
        return '';
      }
      if (typeof data === 'string' || typeof data === 'number') {
        return String(data).trim();
      }
      return String(data.currentLabel ?? data.label ?? data.value ?? '').trim();
    },
    ownerTagStyle(data) {
      const name = this.ownerTagName(data);
      let hash = 0;
      for (let i = 0; i < name.length; i++) {
        hash = (hash * 31 + name.charCodeAt(i)) >>> 0;
      }
      const palette = OWNER_TAG_COLORS[name ? hash % OWNER_TAG_COLORS.length : 0];
      return {
        backgroundColor: palette.bg,
        color: palette.color,
      };
    },
    onTestDatesChange(row) {
      row.test_dates_display = (row.test_dates || []).join('、');
      this.syncSelectedField(row, 'test_dates', '检测日期', (target, source) => {
        target.test_dates = [...(source.test_dates || [])];
        target.test_dates_display = source.test_dates_display;
      });
    },
    onTiterOwnerChange(row) {
      this.syncSelectedField(row, 'owner', '效价负责人', (target, source) => {
        target.titer_owners = [...(source.titer_owners || [])];
      });
      this.$nextTick(() => {
        const selectRef = this.$refs[`ownerSelect_${row.id}`];
        const ins = Array.isArray(selectRef) ? selectRef[0] : selectRef;
        ins?.blur?.();
      });
    },
    onSerumStatusChange(row) {
      this.syncSelectedField(row, 'serum_status', '血清状态', (target, source) => {
        target.serum_status = source.serum_status;
      });
    },
    onPriorityChange(row) {
      this.syncSelectedField(row, 'priority', '优先级', (target, source) => {
        target.priority = source.priority;
      });
    },
    saveRow(row, label, options = {}) {
      const silent = Boolean(options.silent);
      const payload = { id: row.id };
      if (label === '效价负责人') {
        if (!this.canEditTiterOrderOwner()) {
          ElMessage.warning('您没有权限编辑效价负责人');
          return Promise.resolve(false);
        }
        payload.titer_owners = row.titer_owners;
      } else if (label === '检测日期') {
        if (!this.canEditTiterOrderRecord(row)) {
          ElMessage.warning('您没有权限编辑检测日期');
          return Promise.resolve(false);
        }
        payload.test_dates = row.test_dates;
      } else if (label === '血清状态') {
        if (!this.canEditTiterOrderRecordOpen()) {
          ElMessage.warning('您没有权限编辑血清状态');
          return Promise.resolve(false);
        }
        payload.serum_status = row.serum_status ?? null;
      } else if (label === '备注') {
        if (!this.canEditTiterOrderRecord(row)) {
          ElMessage.warning('您没有权限编辑备注');
          return Promise.resolve(false);
        }
        payload.remark = row.remark;
      } else if (label === '效价小结') {
        if (!this.canEditTiterOrderRecord(row)) {
          ElMessage.warning('您没有权限编辑效价小结');
          return Promise.resolve(false);
        }
        payload.summary = row.summary;
      } else if (label === '优先级') {
        if (!this.canEditTiterOrderRecordOpen()) {
          ElMessage.warning('您没有权限编辑优先级');
          return Promise.resolve(false);
        }
        payload.priority = row.priority || TITER_PRIORITY_DEFAULT;
      } else {
        return Promise.resolve(false);
      }
      return saveTiterOrder(payload)
        .then(() => {
          if (!silent) {
            ElMessage.success(`${label}已保存`);
          }
          if (label === '效价负责人') {
            this.mergeOwnerOptions(row.titer_owners);
          }
          if (!silent && STATS_AFFECTING_LABELS.has(label)) {
            this.refreshStats();
          }
          return true;
        })
        .catch((error) => {
          notifyApiError(error, { messages: { default: `${label}保存失败` } });
          return false;
        });
    },
  },
};
</script>

<style scoped>
/*
 * 尺寸维护约定（L1 页面壳子 / L2 数据区）：
 * 1. 整表密度 → 只改 el-table 的 size 一处，表头勿写 fontSize
 * 2. 说明文字 → .text-secondary / .text-hint
 * 3. 统计数字 → .stat-value
 * 4. 表格内勿用 :deep 覆盖 font-size
 * 5. 数据行边距 → 只改 .table-card :deep(.el-table__body .cell)，勿改表头
 * 6. 负责人标签色 → 只改 OWNER_TAG_COLORS
 * 7. 表面圆角/边框/阴影 → 用 --list-* token（见 list-page-surface.css）
 */

.titer-order-page {
  position: relative;
  min-height: 100%;
  padding: var(--list-page-padding);
  background: var(--list-page-bg);
}

.page-title {
  margin: 0;
  color: var(--el-text-color-primary);
  font-size: 20px;
  font-weight: 600;
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
  text-align: right;
  transition: transform 0.22s ease;
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

.page-header-band {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-width: 0;
  padding: 12px 16px;
  margin: 0;
  border: 1px solid rgba(64, 158, 255, 0.12);
  border-radius: var(--list-mid-radius);
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.10), rgba(103, 194, 58, 0.06));
}

.title-group {
  min-width: 0;
}

.page-subtitle {
  max-width: 560px;
  margin: 6px 0 0;
  line-height: 1.5;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
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

.stat-blue::before {
  background: var(--el-color-primary);
}

.stat-blue {
  --stat-ring: rgba(64, 158, 255, 0.34);
  --stat-glow: rgba(64, 158, 255, 0.12);
}

.stat-purple::before {
  background: #8b5cf6;
}

.stat-purple {
  --stat-ring: rgba(139, 92, 246, 0.34);
  --stat-glow: rgba(139, 92, 246, 0.12);
}

.stat-orange::before {
  background: #ff9f43;
}

.stat-orange {
  --stat-ring: rgba(255, 159, 67, 0.38);
  --stat-glow: rgba(255, 159, 67, 0.13);
}

.stat-red::before {
  background: #ff6b6b;
}

.stat-red {
  --stat-ring: rgba(255, 107, 107, 0.36);
  --stat-glow: rgba(255, 107, 107, 0.12);
}

.stat-slate::before {
  background: #4dd0e1;
}

.stat-slate {
  --stat-ring: rgba(77, 208, 225, 0.38);
  --stat-glow: rgba(77, 208, 225, 0.13);
}

.filter-strip {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  grid-template-rows: repeat(2, auto);
  gap: 8px 10px;
  align-items: center;
  padding-top: 10px;
  border-top: 1px solid #edf1f7;
}

.filter-strip .filter-item {
  width: 100%;
  min-width: 0;
}

.filter-strip :deep(.el-date-editor),
.filter-strip :deep(.el-select),
.filter-strip :deep(.el-input) {
  width: 100%;
  min-width: 0;
  font-size: 13px;
}

.filter-strip :deep(.el-input) {
  --el-input-height: 30px;
}

.filter-strip :deep(.el-input__wrapper),
.filter-strip :deep(.el-select__wrapper) {
  min-height: 30px;
}

.filter-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: flex-end;
  white-space: nowrap;
}

.filter-actions .more-toggle-btn {
  margin-right: 10px;
}

.filter-actions :deep(.el-button) {
  height: 30px;
  min-height: 30px;
  padding: 0 13px;
  font-size: 13px;
}

.filter-actions :deep(.el-button .el-icon + span) {
  margin-left: 4px;
}

.table-card {
  overflow: hidden;
  border: var(--list-surface-border);
  border-radius: var(--list-surface-radius);
  box-shadow: var(--list-surface-shadow);
}

.table-plate-wrap {
  position: relative;
}

.table-card :deep(td.plate-col-facs),
.table-card :deep(td.plate-col-elisa),
.table-card :deep(td.plate-col-mouse),
.table-card :deep(td.plate-col-owner),
.table-card :deep(td.plate-col-test-dates),
.table-card :deep(td.plate-col-serum-status),
.table-card :deep(td.plate-col-priority) {
  height: 1px;
  padding: 0;
}

.table-card :deep(td.plate-col-facs .cell),
.table-card :deep(td.plate-col-elisa .cell),
.table-card :deep(td.plate-col-mouse .cell),
.table-card :deep(td.plate-col-owner .cell),
.table-card :deep(td.plate-col-test-dates .cell),
.table-card :deep(td.plate-col-serum-status .cell),
.table-card :deep(td.plate-col-priority .cell) {
  position: relative;
  height: 100%;
  padding: 0;
}

.plate-select-overlay {
  position: absolute;
  inset: 0;
  z-index: 3;
  pointer-events: none;
}

.plate-select-cell {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  cursor: cell;
  user-select: none;
}

.plate-select-cell--field {
  justify-content: stretch;
  padding: 6px 8px;
}

.plate-select-cell--field .inline-cell-control,
.plate-select-cell--field .cell-tooltip-target {
  flex: 1 1 auto;
  width: 100%;
  min-width: 0;
}

.table-plate-wrap.is-plate-dragging .plate-select-cell--field .inline-cell-control {
  pointer-events: none;
}

.plate-select-region {
  position: absolute;
  box-sizing: border-box;
  pointer-events: none;
  background: rgba(64, 158, 255, 0.16);
  border: 1px solid rgba(64, 158, 255, 0.45);
  /* 只过渡纵向拉伸；左右/宽度瞬切，换列不会横滑卡顿 */
  transition: top 0.12s ease, height 0.12s ease;
}

.plate-region-enter-active {
  transition: opacity 0.18s ease;
}

.plate-region-leave-active {
  transition: opacity 0.14s ease;
}

.plate-region-enter-from,
.plate-region-leave-to {
  opacity: 0;
}

.plate-select-bubble {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 6;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.4;
  color: #1d5fbf;
  white-space: nowrap;
  pointer-events: none;
  background: rgba(236, 245, 255, 0.94);
  border: 1px solid #b3d8ff;
  border-radius: var(--list-mid-radius);
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.18);
  will-change: transform;
  /* transform 合成层插值才跟得上刷新率；时长由 JS 写入，默认偏短 */
  transition-property: transform;
  transition-duration: 0.12s;
  transition-timing-function: linear;
}

.plate-bubble-enter-active {
  transition: opacity 0.18s ease;
}

.plate-bubble-leave-active {
  transition: opacity 0.14s ease;
}

.plate-bubble-enter-from,
.plate-bubble-leave-to {
  opacity: 0;
}

.table-card :deep(.el-table__body .cell) {
  padding-top: 6px;
  padding-right: 8px;
  padding-bottom: 6px;
  padding-left: 8px;
}

.table-card :deep(.el-table__header .cell) {
  white-space: nowrap;
}

.col-filter-head {
  padding: 0;
  font: inherit;
  font-weight: bold;
  color: inherit;
  cursor: pointer;
  background: transparent;
  border: none;
}

.col-filter-head:hover,
.col-filter-head.is-active {
  color: var(--el-color-primary);
}

.col-filter-zero {
  width: 100%;
}

.col-filter-zero :deep(.el-radio-button) {
  flex: 1;
}

.col-filter-zero :deep(.el-radio-button__inner) {
  width: 100%;
}

.col-filter-range {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 6px;
  align-items: center;
  margin-top: 10px;
}

.col-filter-range :deep(.el-input-number) {
  width: 100%;
}

.col-filter-range :deep(.el-input__wrapper) {
  min-height: 28px;
  padding: 0 8px;
  font-size: 13px;
}

.col-filter-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 10px;
}

.table-card :deep(.table-action-btn) {
  height: 28px;
  min-height: 28px;
  padding: 0 10px;
  font-size: 13px;
}

.no-permission-btn {
  cursor: not-allowed;
}

.table-card :deep(.el-button-group) {
  display: inline-flex;
  flex-wrap: nowrap;
  vertical-align: middle;
}

.status-tag {
  height: 25px;
  padding: 0 8px;
  font-size: 13px;
  border-radius: var(--list-chip-radius);
}

/* 血清状态：沿用 el-tag 色系，仅给选中项轻量着色 */
.table-card :deep(.serum-status-select.status-tone-info .el-select__wrapper) {
  background-color: var(--el-color-info-light-9);
}

.table-card :deep(.serum-status-select.status-tone-info .el-select__selected-item) {
  color: var(--el-color-info);
}

.table-card :deep(.serum-status-select.status-tone-primary .el-select__wrapper) {
  background-color: var(--el-color-primary-light-9);
}

.table-card :deep(.serum-status-select.status-tone-primary .el-select__selected-item) {
  color: var(--el-color-primary);
}

.table-card :deep(.serum-status-select.status-tone-warning .el-select__wrapper) {
  background-color: var(--el-color-warning-light-9);
}

.table-card :deep(.serum-status-select.status-tone-warning .el-select__selected-item) {
  color: var(--el-color-warning);
}

.table-card :deep(.serum-status-select.status-tone-success .el-select__wrapper) {
  background-color: var(--el-color-success-light-9);
}

.table-card :deep(.serum-status-select.status-tone-success .el-select__selected-item) {
  color: var(--el-color-success);
}

.table-card :deep(.serum-status-select.status-tone-danger .el-select__wrapper) {
  background-color: var(--el-color-danger-light-9);
}

.table-card :deep(.serum-status-select.status-tone-danger .el-select__selected-item) {
  color: var(--el-color-danger);
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

.table-card :deep(.status-column-cell .cell) {
  padding-left: 5px;
  padding-right: 5px;
}

/* 与免疫列表一致：右侧 fixed「操作」左侧硬分割线（不占布局，避免拖列宽错位） */
.table-card :deep(.el-table--border .el-table-fixed-column--right.is-first-column.el-table__cell) {
  box-shadow: -1px 0 0 0 var(--el-table-border-color);
}

/* 效价负责人多选：标签胶囊样式 */
.owner-select {
  width: 100%;
}

/* 效价负责人 → 优先级：行内控件统一空态高度 */
.table-card :deep(.inline-cell-control .el-select__wrapper),
.table-card :deep(.inline-cell-control .el-input__wrapper) {
  min-height: 24px;
  padding-top: 2px;
  padding-bottom: 2px;
}

.table-card :deep(.inline-cell-control.el-date-editor),
.table-card :deep(.test-dates-picker) {
  width: 100%;
}

.cell-tooltip-target {
  width: 100%;
  min-width: 0;
}

.table-card :deep(.cell-tooltip-target .test-dates-picker .el-input__wrapper),
.table-card :deep(.cell-tooltip-target .inline-cell-control .el-input__wrapper) {
  overflow: hidden;
}

.table-card :deep(.cell-tooltip-target .test-dates-picker .el-input__inner),
.table-card :deep(.cell-tooltip-target .inline-cell-control .el-input__inner) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.table-card :deep(.owner-select .owner-tag) {
  height: auto;
  min-height: 22px;
  padding: 0 3px 0 6px;
  border: none;
  font-size: 12px;
  line-height: 20px;
  -webkit-font-smoothing: antialiased;
}

.table-card :deep(.owner-select .owner-tag .el-tag__close) {
  margin-left: 1px;
  margin-right: 0;
  color: inherit;
}

.table-card :deep(.owner-select .owner-tag .el-tag__close:hover) {
  background-color: rgba(0, 0, 0, 0.06);
  color: inherit;
}

.code-text {
  font-family: Consolas, monospace;
  color: var(--el-color-primary);
  cursor: pointer;
  font-weight: bold;
}

.code-text:hover {
  text-decoration: underline;
}

.pagination {
  justify-content: flex-start;
  margin-top: 12px;
}

.owner-stats-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  padding: 10px 12px;
  background: var(--list-mid-bg);
  border: var(--list-mid-border);
  border-radius: var(--list-mid-radius);
}

.owner-stats-filter {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.owner-stats-filter-label {
  color: #606266;
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
}

.owner-stats-month-picker {
  width: 260px;
}

.owner-stats-note {
  font-size: 12px;
  line-height: 1.5;
  text-align: right;
}

:global(.owner-stats-dialog .owner-stats-total-name) {
  color: var(--el-color-primary);
  font-weight: 700;
}

:global(.owner-stats-dialog .owner-stats-summary-row > td.el-table__cell) {
  border-top: 2px solid #79bbff !important;
}

:global(.owner-stats-dialog .owner-stats-table .el-table__body tr:not(.owner-stats-summary-row):hover > td.el-table__cell) {
  box-shadow: inset 0 0 0 9999px rgba(64, 158, 255, 0.06);
}

:global(.owner-stats-dialog .owner-stats-table .el-table__body tr.current-row:not(.owner-stats-summary-row) > td.el-table__cell) {
  box-shadow: inset 0 0 0 9999px rgba(64, 158, 255, 0.12);
}

:global(.titer-select-dropdown .el-select-dropdown__wrap) {
  max-height: 240px;
}

@media (max-width: 1280px) {
  .stats-strip {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .page-header-band {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-actions {
    width: 100%;
    justify-content: space-between;
  }

  .stats-strip {
    grid-template-columns: 1fr;
  }
}
</style>
