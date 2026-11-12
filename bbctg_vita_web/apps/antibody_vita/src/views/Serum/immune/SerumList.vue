<template>
  <div class="app-container" :class="{ 'is-list-table-locked': listTableLocked }">
    <!-- Advanced Ops: slide down overlay -->
    <AdvancedOpsBar v-model="showAdvancedOps">
      <el-input
        v-model="listQuery.lab_notebook"
        placeholder="实验记录本"
        title="输入「空」可查找未填写"
        clearable
        :prefix-icon="Search"
        @keyup.enter="handleFilter"
        @clear="handleFilter"
      />
      <el-input
        v-model="listQuery.cage_position"
        placeholder="笼位"
        title="输入「空」可查找未填写"
        clearable
        :prefix-icon="Search"
        @keyup.enter="handleFilter"
        @clear="handleFilter"
      />
      <ListFilterSelect
        v-model="listQuery.reviewer"
        v-bind="headerTop('reviewer', '审核人')"
        clearable
        filterable
        :filter-method="q => setFilterQuery('reviewer', q)"
        @clear="setFilterQuery('reviewer', '')"
        @change="handleFilter">
        <el-option v-for="item in filteredReviewerOptions" :key="item" :label="item" :value="item" />
      </ListFilterSelect>
      <template #actions>
        <el-button
          type="primary"
          :class="{'no-permission-btn': !canViewCellInventory()}"
          :icon="Search"
          :title="!canViewCellInventory() ? '您没有权限查看细胞库存' : ''"
          @click="handleCellInventory"
        >
          细胞库存查询
        </el-button>
        <el-button type="warning" :icon="Download" @click="handleListExport">
          列表导出
        </el-button>
      </template>
    </AdvancedOpsBar>

    <!-- Dashboard / Overview -->
    <el-row :gutter="20" class="panel-group">
      <!-- Total: Pie Chart Trigger -->
      <el-col :xs="12" :sm="12" :lg="6" class="card-panel-col">
        <div class="card-panel blue-panel" @click="handleTotalClick">
          <div class="card-panel-icon-wrapper">
            <el-icon class="card-panel-icon"><DataAnalysis /></el-icon>
          </div>
          <div class="card-panel-description">
            <div class="card-panel-text">实验总数</div>
            <div class="card-panel-num">{{ stats.total }}</div>
          </div>
        </div>
      </el-col>
      <!-- Ongoing: Filter Trigger -->
      <el-col :xs="12" :sm="12" :lg="6" class="card-panel-col">
        <div class="card-panel green-panel" :class="{'active-card': listQuery.project_status === 'ongoing'}" @click="handleStatusFilter('ongoing')">
          <div class="card-panel-icon-wrapper">
            <el-icon class="card-panel-icon"><Timer /></el-icon>
          </div>
          <div class="card-panel-description">
            <div class="card-panel-text">进行中</div>
            <div class="card-panel-num">{{ stats.status_counts.ongoing || 0 }}</div>
          </div>
        </div>
      </el-col>
      <!-- Completed: Filter Trigger -->
      <el-col :xs="12" :sm="12" :lg="6" class="card-panel-col">
        <div class="card-panel red-panel" :class="{'active-card': listQuery.project_status === 'completed'}" @click="handleStatusFilter('completed')">
          <div class="card-panel-icon-wrapper">
            <el-icon class="card-panel-icon"><CircleCheck /></el-icon>
          </div>
          <div class="card-panel-description">
            <div class="card-panel-text">已完成</div>
            <div class="card-panel-num">{{ stats.status_counts.completed || 0 }}</div>
          </div>
        </div>
      </el-col>
      <!-- Owner: User Filter Trigger -->
      <el-col :xs="12" :sm="12" :lg="6" class="card-panel-col">
        <div class="card-panel orange-panel" :class="{'active-card': listQuery.owner === currentOwnerName}" @click="handleOwnerFilter(currentOwnerName)">
          <div class="card-panel-icon-wrapper">
            <el-icon class="card-panel-icon"><UserFilled /></el-icon>
          </div>
          <div class="card-panel-description">
            <div class="card-panel-text">负责人</div>
            <div class="card-panel-num">{{ stats.owner_counts.length }}</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- Filter Header -->
    <div class="filter-wrapper list-filter-controls">
        <el-row :gutter="15" type="flex" align="middle" style="flex-wrap: wrap;">
            <el-col :span="4">
               <el-input v-model="listQuery.project_code" v-bind="headerTop('project_code', '项目编号')" class="filter-item" @keyup.enter="handleFilter" clearable :prefix-icon="Search" />
            </el-col>
            <el-col :span="4">
                <el-input v-model="listQuery.project_name" v-bind="headerTop('project_name', '项目名称')" class="filter-item" @keyup.enter="handleFilter" clearable :prefix-icon="Search" />
            </el-col>
            <el-col :span="3">
                 <WorkbenchTargetFilter
                      v-model="listQuery.target_name"
                      v-bind="headerTop('target_name', '靶点')"
                      scope="serumList"
                      style="width: 100%"
                      @change="handleFilter" />
            </el-col>
            <el-col :span="3">
                 <ListFilterSelect 
                      v-model="listQuery.owner" 
                      v-bind="headerTop('owner', '负责人')"
                      clearable 
                      filterable 
                      :filter-method="q => setFilterQuery('owner', q)"
                      @clear="setFilterQuery('owner', '')"
                      style="width: 100%" 
                      @change="handleFilter">
                      <el-option v-for="item in filteredOwnerOptions" :key="item" :label="item" :value="item" />
                  </ListFilterSelect>
            </el-col>
             <el-col :span="5">
                <el-date-picker
                  v-model="dateRange"
                  type="daterange"
                  range-separator="至"
                  v-bind="headerTop('start_date', '开始', 'startPlaceholder')"
                  end-placeholder="结束"
                  style="width: 100%;"
                  format="YYYY-MM-DD"
                  value-format="YYYY-MM-DD">
                </el-date-picker>
            </el-col>
            <el-col :span="1" style="text-align: center;">
                <button
                  type="button"
                  class="list-advanced-trigger"
                  :class="{ 'is-active': showAdvancedFilters }"
                  title="看不见我"
                  @click="toggleAdvanced"
                >
                  <el-icon class="advanced-trigger-icon" :class="{ 'is-expanded': showAdvancedFilters }">
                    <ArrowDown />
                  </el-icon>
                </button>
            </el-col>
            <el-col :span="4" style="text-align: right;">
                <div class="list-filter-actions">
                  <WorkbenchHeaderFilterChip v-bind="headerChipBind" />
                  <el-button class="list-filter-action-button" type="primary" :icon="Search" title="右键清空筛选" @click="handleFilter" @contextmenu.prevent="resetFilters">查询</el-button>
                  <el-button
                    class="list-filter-action-button"
                    type="success"
                    :class="{'no-permission-btn': !canCreateProject()}"
                    :icon="Plus"
                    :title="!canCreateProject() ? '您没有权限新建项目' : ''"
                    @click="handleCreate"
                  >
                    新建
                  </el-button>
                </div>
            </el-col>
        </el-row>
        <div
          class="advanced-filters-collapse"
          :class="{ 'is-expanded': showAdvancedFilters }"
          @transitionend="onAdvancedFiltersTransitionEnd"
        >
          <div class="advanced-filters-inner">
          <div class="advanced-filters">
            <el-row :gutter="15" type="flex" align="middle" style="flex-wrap: wrap;">
              <el-col :span="4">
                 <ListFilterSelect 
                      v-model="listQuery.study_type" 
                      v-bind="headerTop('study_type', '课题类型')"
                      clearable 
                      filterable 
                      :filter-method="q => setFilterQuery('studyType', q)"
                      @clear="setFilterQuery('studyType', '')"
                      style="width: 100%" 
                      @change="handleFilter">
                      <el-option v-for="item in filteredStudyTypeOptions" :key="item" :label="item" :value="item" />
                  </ListFilterSelect>
              </el-col>
              <el-col :span="4">
                 <ListFilterSelect 
                      v-model="listQuery.pm" 
                      v-bind="headerTop('pm', 'PM')"
                      clearable 
                      filterable 
                      :filter-method="q => setFilterQuery('pm', q)"
                      @clear="setFilterQuery('pm', '')"
                      style="width: 100%" 
                      @change="handleFilter">
                      <el-option v-for="item in filteredPMOptions" :key="item" :label="item" :value="item" />
                  </ListFilterSelect>
              </el-col>
              <el-col :span="3">
                 <ListFilterSelect 
                      v-model="listQuery.mouse_strain" 
                      v-bind="headerTop('mouse_strain', '鼠型')"
                      clearable 
                      filterable 
                      :filter-method="q => setFilterQuery('mouseStrain', q)"
                      @clear="setFilterQuery('mouseStrain', '')"
                      style="width: 100%" 
                      @change="handleFilter">
                      <el-option v-for="item in filteredMouseStrainOptions" :key="item" :label="item" :value="item" />
                  </ListFilterSelect>
              </el-col>
              <el-col :span="3">
                 <ListFilterSelect 
                      v-model="listQuery.project_status" 
                      v-bind="headerTop('project_status', '状态')"
                      clearable 
                      filterable 
                      :filter-method="q => setFilterQuery('status', q)"
                      @clear="setFilterQuery('status', '')"
                      style="width: 100%" 
                      @change="handleFilter">
                      <el-option label="进行中" value="ongoing" />
                      <el-option label="已完成" value="completed" />
                      <el-option v-for="item in filteredStatusOptions" :key="item" :label="item" :value="item" />
                  </ListFilterSelect>
              </el-col>
              <el-col :span="5">
                 <ListFilterSelect 
                      v-model="listQuery.mouse_strain_category" 
                      v-bind="headerTop('mouse_strain_category', '归类鼠型')"
                      clearable 
                      filterable 
                      :filter-method="q => setFilterQuery('mouseStrainCategory', q)"
                      @clear="setFilterQuery('mouseStrainCategory', '')"
                      style="width: 100%" 
                      @change="handleFilter">
                      <el-option v-for="item in filteredMouseStrainCategoryOptions" :key="item" :label="item" :value="item" />
                  </ListFilterSelect>
              </el-col>
              <el-col :span="1" style="text-align: center;">
                <button
                  type="button"
                  class="list-advanced-trigger"
                  :class="{ 'is-active': showAdvancedOps }"
                  title="彻底疯狂"
                  @click="toggleAdvancedOps"
                >
                  <el-icon><Tools /></el-icon>
                </button>
              </el-col>
              <el-col :span="4" style="text-align: right;">
                <div class="list-filter-actions">
                  <el-button
                    class="list-filter-action-button"
                    type="danger"
                    :class="{'no-permission-btn': !canAutoUpdateStatus()}"
                    :icon="Refresh"
                    :title="!canAutoUpdateStatus() ? '您没有权限自动更新状态' : ''"
                    @click="handleAutoUpdateStatus"
                  >
                    曼波
                  </el-button>
                  <el-button
                    class="list-filter-action-button"
                    type="warning"
                    :class="{'no-permission-btn': !canExportMouse()}"
                    :icon="Download"
                    :title="!canExportMouse() ? '您没有权限导出小鼠免疫数据' : ''"
                    @click="handleExport"
                    @contextmenu.prevent="handleMouseRightClick"
                  >
                    鼠鼠
                  </el-button>
                </div>
              </el-col>
            </el-row>
          </div>
          </div>
        </div>
    </div>

    <!-- Main Table -->
    <el-card shadow="never" class="list-table-card">
        <div ref="listTableBody" class="list-table-body">
        <el-table
        ref="serumTable"
        :height="listTableHeight"
        v-loading="listLoading"
        :data="list"
        row-key="id"
        :row-class-name="tableRowClassName"
        border
        stripe
        fit
        highlight-current-row
        size="large"
        class="list-data-table"
        style="width: 100%;"
        :header-cell-class-name="headerCellClassName"
        @header-click="onTableHeaderClick"
        >
        <el-table-column column-key="project_code" prop="project_code" align="left" width="135" fixed>
            <template #header><WorkbenchHeaderLabel label="编号" v-bind="headerMenuStates.project_code" /></template>
            <template #default="{ row }">
               <div class="list-code-text is-clickable" @click="handleView(row)">{{ row.project_code }}</div>
            </template>
        </el-table-column>
        
        <el-table-column column-key="project_name" prop="project_name" align="left" min-width="240" show-overflow-tooltip>
            <template #header><WorkbenchHeaderLabel label="项目名称" v-bind="headerMenuStates.project_name" /></template>
            <template #default="{ row }">
               <span class="project-name">{{ row.project_name }}</span>
            </template>
        </el-table-column>

        <el-table-column v-if="showExtraColumns" column-key="lab_notebook" prop="lab_notebook" align="center" min-width="110" show-overflow-tooltip class-name="inline-edit-cell">
            <template #header><WorkbenchHeaderLabel label="实验记录本" v-bind="headerMenuStates.lab_notebook" /></template>
            <template #default="{ row }">
               <el-input
                  v-if="editingField === 'lab_notebook' && editingRowId === row.id"
                  v-model="editingValue"
                  class="inline-edit-input"
                  placeholder="实验记录本号"
                  @keyup.enter="saveInlineField(row, 'lab_notebook')"
                  @blur="saveInlineField(row, 'lab_notebook')"
               />
               <button
                  v-else
                  type="button"
                  class="inline-edit-trigger"
                  :class="{ 'is-editable': canEdit(row) }"
                  @click="handleInlineEditClick(row, 'lab_notebook')"
               >
                  {{ row.lab_notebook || '' }}
               </button>
            </template>
        </el-table-column>

        <el-table-column v-if="showExtraColumns" column-key="reviewer" prop="reviewer" align="center" min-width="90" show-overflow-tooltip class-name="inline-edit-cell">
            <template #header><WorkbenchHeaderLabel label="审核人" v-bind="headerMenuStates.reviewer" /></template>
            <template #default="{ row }">
               <UserSelect
                  v-if="editingField === 'reviewer' && editingRowId === row.id"
                  v-model="editingValue"
                  class="inline-edit-input"
                  :options="allReviewerOptions"
                  placeholder="选择审核人"
                  clearable
                  automatic-dropdown
                  @change="saveInlineField(row, 'reviewer')"
                  @visible-change="visible => visible || stopInlineEditIfCurrent(row.id, 'reviewer')"
               />
               <button
                  v-else
                  type="button"
                  class="inline-edit-trigger"
                  :class="{ 'is-editable': canEdit(row) }"
                  @click="handleInlineEditClick(row, 'reviewer')"
               >
                  {{ row.reviewer || '' }}
               </button>
            </template>
        </el-table-column>

        <el-table-column v-if="showExtraColumns" column-key="mouse_strain_category" prop="mouse_strain_category" align="center" min-width="110" show-overflow-tooltip>
            <template #header><WorkbenchHeaderLabel label="归类鼠型" v-bind="headerMenuStates.mouse_strain_category" /></template>
        </el-table-column>

        <el-table-column v-if="showExtraColumns" :column-key="isCageMode ? '' : 'remark'" prop="remark" align="center" min-width="130" show-overflow-tooltip :class-name="isCageMode ? 'inline-edit-cell' : ''">
            <template #header>
               <span v-if="isCageMode">笼位</span>
               <WorkbenchHeaderLabel v-else label="实验备注" v-bind="headerMenuStates.remark" />
            </template>
            <template #default="{ row }">
               <el-input
                  v-if="isCageMode && editingField === 'cage' && editingRowId === row.id"
                  v-model="editingValue"
                  class="inline-edit-input"
                  placeholder="鼠鼠大House~"
                  @keyup.enter="handleEnter(row)"
                  @blur="handleBlur(row)"
               />
               <button
                  v-else-if="isCageMode"
                  type="button"
                  class="inline-edit-trigger"
                  :class="{ 'is-editable': canUpdateCage(row) }"
                  @click="handleCageClick(row)"
               >
                  {{ row.cage_position_display || '' }}
               </button>
               <span v-else>{{ row.remark || '' }}</span>
            </template>
        </el-table-column>

        <el-table-column v-if="showExtraColumns" column-key="study_type" prop="study_type" align="center" min-width="100" show-overflow-tooltip>
            <template #header><WorkbenchHeaderLabel label="课题类型" v-bind="headerMenuStates.study_type" /></template>
        </el-table-column>

        <el-table-column v-if="showExtraColumns" column-key="pm" prop="pm" align="center" width="100" show-overflow-tooltip>
            <template #header><WorkbenchHeaderLabel label="PM" v-bind="headerMenuStates.pm" /></template>
        </el-table-column>

        <el-table-column v-if="showExtraColumns" column-key="mouse_strain" prop="mouse_strain" align="center" min-width="100" show-overflow-tooltip>
            <template #header><WorkbenchHeaderLabel label="鼠型" v-bind="headerMenuStates.mouse_strain" /></template>
        </el-table-column>

        <el-table-column column-key="target_name" prop="target_name" align="center" width="100">
            <template #header><WorkbenchHeaderLabel label="靶点" v-bind="headerMenuStates.target_name" /></template>
        </el-table-column>
        
        <el-table-column column-key="owner" prop="owner" align="center" width="100">
            <template #header><WorkbenchHeaderLabel label="负责人" v-bind="headerMenuStates.owner" /></template>
            <template #default="{ row }">
               {{ row.owner }}
            </template>
        </el-table-column>
        
        <el-table-column column-key="start_date" prop="start_date" align="center" width="120">
            <template #header><WorkbenchHeaderLabel label="开始日期" v-bind="headerMenuStates.start_date" /></template>
        </el-table-column>
        
        <el-table-column column-key="project_status" prop="project_status" align="center" width="100" class-name="status-column-cell">
            <template #header><WorkbenchHeaderLabel label="状态" v-bind="headerMenuStates.project_status" /></template>
            <template #default="{ row }">
              <SerumProjectStatusEditor
                :project-id="row.id"
                :value="row.project_status"
                :editable="canUpdateStatus(row)"
                @change="status => onProjectStatusChange(row, status)"
              />
            </template>
        </el-table-column>

        <el-table-column label="操作" align="center" width="240" fixed="right">
            <template #default="{ row }">
                <el-button-group>
                    <el-button
                        class="list-table-action-btn"
                        type="primary"
                        plain
                        :icon="View"
                        title="左键详情，右键打印"
                        @click="handleView(row)"
                        @contextmenu.prevent="handlePrintScheme(row)"
                    >
                        详情
                    </el-button>
                    <el-button
                        class="list-table-action-btn"
                        type="success"
                        plain
                        :icon="Edit"
                        :class="{'no-permission-btn': !canEdit(row)}"
                        @click="handleUpdate(row, 'scheme')"
                        :title="!canEdit(row) ? '您没有权限编辑此项目' : ''">
                        方案
                    </el-button>
                    <el-button
                        class="list-table-action-btn"
                        type="warning"
                        plain
                        :icon="TrendCharts"
                        :class="{'no-permission-btn': !canEditTiter(row)}"
                        @click="handleUpdate(row, 'titer')"
                        :title="!canEditTiter(row) ? '您没有权限编辑此项目' : ''">
                        数据
                    </el-button>
                </el-button-group>
            </template>
        </el-table-column>
        </el-table>
        </div>

         <div class="list-pagination">
            <el-pagination
                v-if="paginationReady && total > 0"
                :current-page="listQuery.page"
                :page-size="listQuery.limit"
                :total="total"
                :page-sizes="[20, 50, 100, 200, 500]"
                layout="total, sizes, prev, pager, next, jumper"
                @size-change="handleSizeChange"
                @current-change="handleCurrentChange"
            />
         </div>
    </el-card>

    <!-- Pie Chart Dialog (Replaced with CSS Bar Chart to standard) -->
    <el-dialog v-model="chartVisible" title="☝️🤓疯狂牛马榜🐮🐴 o((>ω< ))o" width="500px" append-to-body>
        <div style="padding: 0px 20px 20px 20px;">
           <div v-if="stats.owner_counts.length === 0" style="text-align: center; color: var(--el-text-color-secondary);">暂无数据</div>
           <div v-else>
               <div v-for="(item, index) in stats.owner_counts.slice(0, 10)" :key="index" style="margin-bottom: 15px;">
                   <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                       <span style="font-weight: bold; color: var(--el-text-color-primary);">{{ item.name }}</span>
                       <span style="color: var(--el-text-color-regular);">{{ item.value }} 单</span>
                   </div>
                   <div style="height: 10px; background: var(--el-fill-color); border-radius: 5px; overflow: hidden;">
                       <div :style="{width: (stats.total > 0 ? (item.value / stats.total * 100) : 0) + '%', background: 'var(--el-color-primary)', height: '100%'}"></div>
                   </div>
               </div>
           </div>
        </div>
    </el-dialog>

    <WorkbenchHeaderMenu v-bind="headerMenuBind" />
  </div>
</template>

<script>
import { useUserStore } from '@vben/stores'

import {
  ArrowDown,
  CircleCheck,
  DataAnalysis,
  Download,
  Edit,
  Plus,
  Refresh,
  Search,
  Timer,
  Tools,
  TrendCharts,
  UserFilled,
  View,
} from '@element-plus/icons-vue'
import {
  ElButton,
  ElButtonGroup,
  ElCard,
  ElCol,
  ElDatePicker,
  ElDialog,
  ElIcon,
  ElInput,
  ElLoading,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElPagination,
  ElRow,
  ElTable,
  ElTableColumn,
} from 'element-plus'

import { notifyApiError, resolveUserMessage } from '#/api/errors'
import { fetchList, fetchSerumColumnValues, fetchStats, getSerumFilterOptions, export_mouse, exportSerumList, autoUpdateStatus, updateCagePosition, updateLabNotebook, updateSerumReviewer, exportSchemePdf } from '#/api/serum'
import { skipGlobalErrorHandler } from '#/api/request'
import { SERUM_ERRORS } from '../shared/errors'
import AdvancedOpsBar from '#/components/AdvancedOpsBar.vue'
import UserSelect from '#/components/UserSelect.vue'
import ListFilterSelect from '#/components/ListFilterSelect.vue'
import SerumProjectStatusEditor from '../shared/SerumProjectStatusEditor.vue'
import { downloadListExcel, excelTimestamp } from '#/utils/downloadExcel'
import { listPageMixin } from '#/utils/listPage'
import { listTableLockMixin } from '#/utils/listTableLock'
import { downloadBlob } from '#/utils/file-resource'
import {
  canAutoUpdateSerumStatus,
  canCreateSerumProject,
  canEditSerumProject,
  canEditSerumTiter,
  canExportSerumMouse,
  canUpdateSerumCage,
  canUpdateSerumStatus,
  canViewSerumCellInventory,
  getSerumUserName,
  getSerumUserRoles,
} from '#/utils/serumPermission'
import { SERUM_MOUSE_STRAIN_CATEGORY_OPTIONS, SERUM_MOUSE_STRAIN_OPTIONS } from '#/utils/serumMouseOptions'
import WorkbenchTargetFilter from '#/components/workbench/WorkbenchTargetFilter.vue'
import {
  WorkbenchHeaderFilterChip,
  WorkbenchHeaderLabel,
  WorkbenchHeaderMenu,
  workbenchHeaderMenuMixin,
} from '#/components/workbench'

// 实验记录本顶部框输入「空」表示未填写，与表头的「包含」不同口径，所以不联动
const SERUM_HEADER_COLUMNS = Object.freeze({
  project_code: { type: 'text', label: '编号', values: 'recent', top: { query: 'project_code', kind: 'codes' } },
  project_name: { type: 'text', label: '项目名称', values: 'search', top: { query: 'project_name', kind: 'contains' } },
  lab_notebook: { type: 'text', label: '实验记录本', values: 'recent' },
  reviewer: { type: 'enum', label: '审核人', values: 'all', top: { query: 'reviewer' } },
  mouse_strain_category: { type: 'csv', label: '归类鼠型', values: 'all', top: { query: 'mouse_strain_category' } },
  remark: { type: 'text', label: '实验备注', values: 'search' },
  study_type: { type: 'enum', label: '课题类型', values: 'all', top: { query: 'study_type' } },
  pm: { type: 'enum', label: 'PM', values: 'all', top: { query: 'pm' } },
  mouse_strain: { type: 'csv', label: '鼠型', values: 'all', top: { query: 'mouse_strain' } },
  target_name: { type: 'text', label: '靶点', values: 'all', search: 'target', top: { query: 'target_name' } },
  owner: { type: 'enum', label: '负责人', values: 'all', top: { query: 'owner' } },
  start_date: { type: 'date', label: '开始日期', values: 'all', top: { range: 'dateRange' } },
  project_status: { type: 'enum', label: '状态', values: 'all', top: { query: 'project_status', topOnly: ['ongoing', 'completed'] } },
})

const INLINE_EDIT_FIELDS = Object.freeze({
  lab_notebook: {
    normalize: (value) => String(value || '').replace(/\s+/g, ''),
    save: updateLabNotebook,
    success: '实验记录本更新成功',
    errors: SERUM_ERRORS.list.updateLabNotebook,
  },
  reviewer: {
    normalize: (value) => String(value || '').trim(),
    save: updateSerumReviewer,
    success: '审核人更新成功',
    errors: SERUM_ERRORS.list.updateReviewer,
  },
})

export default {
  name: 'SerumList',
  mixins: [listTableLockMixin, listPageMixin, workbenchHeaderMenuMixin],
  listFilterKey: 'serumList',
  components: {
    ElButton,
    ElButtonGroup,
    ElCard,
    ElCol,
    ElDatePicker,
    ElDialog,
    ElIcon,
    ElInput,
    ElOption,
    ElPagination,
    ElRow,
    ElTable,
    ElTableColumn,
    AdvancedOpsBar,
    ListFilterSelect,
    SerumProjectStatusEditor,
    UserSelect,
    WorkbenchTargetFilter,
    WorkbenchHeaderFilterChip,
    WorkbenchHeaderLabel,
    WorkbenchHeaderMenu,
    ArrowDown,
    CircleCheck,
    DataAnalysis,
    Timer,
    Tools,
    UserFilled,
  },
  setup() {
    const userStore = useUserStore()
    return {
      Download,
      Edit,
      Plus,
      Refresh,
      Search,
      TrendCharts,
      userStore,
      View,
    }
  },
  computed: {
    headerMenuColumns() {
      return SERUM_HEADER_COLUMNS
    },
    currentUserInfo() {
      return this.userStore.userInfo || {}
    },
    currentUserName() {
      return getSerumUserName(this.currentUserInfo)
    },
    currentOwnerName() {
      return this.currentUserName.split(' ')[0] || ''
    },
    currentRoles() {
      return getSerumUserRoles(this.currentUserInfo)
    },
    filteredOwnerOptions() {
      return this.filterOptions(this.allOwnerOptions, this.ownerFilterQuery)
    },
    filteredReviewerOptions() {
      return this.filterOptions(this.allReviewerOptions, this.reviewerFilterQuery)
    },
    filteredStudyTypeOptions() {
      return this.filterOptions(this.allStudyTypeOptions, this.studyTypeFilterQuery)
    },
    filteredPMOptions() {
      return this.filterOptions(this.allPMOptions, this.pmFilterQuery)
    },
    filteredMouseStrainOptions() {
      return this.filterOptions(this.allMouseStrainOptions, this.mouseStrainFilterQuery)
    },
    filteredStatusOptions() {
      return this.filterOptions(this.allStatusOptions, this.statusFilterQuery)
    },
    filteredMouseStrainCategoryOptions() {
      return this.filterOptions(this.allMouseStrainCategoryOptions, this.mouseStrainCategoryFilterQuery)
    },
  },
  data() {
    return {
      list: [],
      total: 0,
      listLoading: true,
      paginationReady: false,
      stats: {
          total: 0,
          status_counts: {},
          owner_counts: []
      },
      listQuery: {
        page: 1,
        limit: 20,
        project_code: undefined,
        project_name: undefined,
        lab_notebook: undefined,
        cage_position: undefined,
        reviewer: undefined,
        owner: undefined,
        target_name: undefined,
        study_type: undefined,
        pm: undefined,
        mouse_strain: undefined,
        mouse_strain_category: undefined,
        project_status: undefined,
        start_date: undefined,
        end_date: undefined,
        sort_field: '',
        sort_dir: ''
      },
      dateRange: [],
      ownerFilterQuery: '',
      chartVisible: false,
      allOwnerOptions: [],
      allReviewerOptions: [],
      reviewerFilterQuery: '',
      allStudyTypeOptions: [],
      studyTypeFilterQuery: '',
      allPMOptions: [],
      pmFilterQuery: '',
      allMouseStrainOptions: [...SERUM_MOUSE_STRAIN_OPTIONS],
      mouseStrainFilterQuery: '',
      allMouseStrainCategoryOptions: [...SERUM_MOUSE_STRAIN_CATEGORY_OPTIONS],
      mouseStrainCategoryFilterQuery: '',
      allStatusOptions: [],
      statusFilterQuery: '',
      showAdvancedFilters: false,
      showExtraColumns: false,
      showAdvancedOps: false,
      isCageMode: false,
      editingRowId: null,
      editingField: '',
      editingValue: '',
      editingOriginalValue: '',
      savingKeys: {},
      schemePrintLoading: false,
      tableScrollAnimationFrame: 0,
      extraColumnsTimer: 0,
      statsRequestToken: 0,
      statsKey: '',
    }
  },
  created() {
    this.initListMeta()
  },
  mounted() {
    this.paginationReady = false
    this.$nextTick(() => {
      this.paginationReady = true
      this.getList()
    })
  },
  activated() {
    if (this.isListDataStale()) {
      this.refreshTabData()
    }
  },
  beforeUnmount() {
    if (this.tableScrollAnimationFrame) {
      cancelAnimationFrame(this.tableScrollAnimationFrame)
    }
    if (this.extraColumnsTimer) {
      clearTimeout(this.extraColumnsTimer)
      this.extraColumnsTimer = 0
    }
  },
  methods: {
    listFilterExtras() {
      return {
        dateRange: this.dateRange,
        showAdvancedFilters: this.showAdvancedFilters,
        showExtraColumns: this.showAdvancedFilters,
      }
    },
    restoreListFilterExtras(state) {
      if (state.dateRange) {
        this.dateRange = state.dateRange
      }
      if (typeof state.showAdvancedFilters === 'boolean') {
        this.showAdvancedFilters = state.showAdvancedFilters
        this.showExtraColumns = state.showAdvancedFilters
      } else if (typeof state.showExtraColumns === 'boolean') {
        this.showExtraColumns = state.showExtraColumns
      }
    },
    smoothScrollTableToRight(skipLayout = false) {
      const tableRef = this.$refs.serumTable
      const tableEl = tableRef?.$el
      const body = tableEl?.querySelector('.el-table__body-wrapper .el-scrollbar__wrap')
      if (!tableRef?.setScrollLeft || !body) return

      if (!skipLayout) {
        tableRef?.doLayout?.()
      }

      if (this.tableScrollAnimationFrame) {
        cancelAnimationFrame(this.tableScrollAnimationFrame)
      }

      const startLeft = body.scrollLeft
      const targetLeft = body.scrollWidth - body.clientWidth
      const distance = targetLeft - startLeft
      const duration = 450
      const startTime = performance.now()

      const easeOutCubic = (progress) => 1 - Math.pow(1 - progress, 3)
      const step = (now) => {
        const progress = Math.min((now - startTime) / duration, 1)
        tableRef.setScrollLeft(startLeft + distance * easeOutCubic(progress))

        if (progress < 1) {
          this.tableScrollAnimationFrame = requestAnimationFrame(step)
        } else {
          this.tableScrollAnimationFrame = 0
        }
      }

      this.tableScrollAnimationFrame = requestAnimationFrame(step)
    },
    tableRowClassName({ row }) {
      return `serum-row-${row.id}`
    },
    handleCellInventory() {
      if (!this.canViewCellInventory()) {
        ElMessage.warning('您没有权限查看细胞库存')
        return
      }
      this.$router.push('/serum/cell')
    },
    toggleAdvancedOps() {
      this.showAdvancedOps = !this.showAdvancedOps
    },
    buildQuery() {
        const [startDate, endDate] = this.dateRange?.length === 2 ? this.dateRange : [undefined, undefined]

        let projectCode = this.listQuery.project_code
        let projectCodes = null
        
        if (projectCode) {
            const separators = [',', '\t', '\n', '\r', '，', '、', ' ']
            const hasSeparator = separators.some(sep => projectCode.includes(sep))
            
            if (hasSeparator) {
                projectCodes = projectCode.split(new RegExp('[,\\t\\n\\r，、 ]+')).map(code => code.trim()).filter(code => code)
                projectCode = null
            }
        }

        return {
            project_code: projectCode,
            project_codes: projectCodes,
            project_name: this.listQuery.project_name,
            lab_notebook: this.listQuery.lab_notebook,
            cage_position: this.listQuery.cage_position,
            reviewer: this.listQuery.reviewer,
            owner: this.listQuery.owner,
            project_status: this.listQuery.project_status,
            target_name: this.listQuery.target_name,
            study_type: this.listQuery.study_type,
            pm: this.listQuery.pm,
            mouse_strain: this.listQuery.mouse_strain,
            mouse_strain_category: this.listQuery.mouse_strain_category,
            start_date: startDate,
            end_date: endDate,
            page: this.listQuery.page,
            limit: this.listQuery.limit,
            sort_field: this.listQuery.sort_field,
            sort_dir: this.listQuery.sort_dir,
            field_filters: this.headerFilterPayload()
        }
    },
    fetchHeaderValues(query) {
      if (query.field === 'project_code') delete query.project_codes
      if (query.field === 'start_date') {
        delete query.start_date
        delete query.end_date
      }
      return fetchSerumColumnValues(query)
    },
    async initListMeta() {
      try {
        const filterOptions = await getSerumFilterOptions(skipGlobalErrorHandler)
        if (filterOptions) {
          this.allOwnerOptions = filterOptions.owners || []
          this.allReviewerOptions = filterOptions.reviewers || []
          this.allStudyTypeOptions = filterOptions.study_types || []
          this.allPMOptions = filterOptions.pms || []
          this.allMouseStrainOptions = [
            ...new Set([...SERUM_MOUSE_STRAIN_OPTIONS, ...(filterOptions.mouse_strains || [])]),
          ]
          this.allMouseStrainCategoryOptions = [
            ...new Set([
              ...SERUM_MOUSE_STRAIN_CATEGORY_OPTIONS,
              ...(filterOptions.mouse_strain_categories || []),
            ]),
          ]
          this.allStatusOptions = filterOptions.statuses || []
        }
      } catch (error) {
        notifyApiError(error, { messages: SERUM_ERRORS.list.initMeta })
      }
    },
    /** 统计块跟随列表筛选；状态和负责人由统计块自己切换，不传。 */
    statsPayload() {
      const { page, limit, sort_field, sort_dir, project_status, owner, ...scope } = this.buildQuery()
      return scope
    },
    getStats() {
        const payload = this.statsPayload()
        this.statsKey = JSON.stringify(payload)
        const statsToken = ++this.statsRequestToken
        fetchStats(payload, skipGlobalErrorHandler).then((response) => {
            if (statsToken !== this.statsRequestToken || !response) return
            this.stats = response
            if (this.stats.owner_counts && Array.isArray(this.stats.owner_counts)) {
                this.stats.owner_counts.sort((a, b) => b.value - a.value)
            }
        }).catch((error) => {
            if (statsToken !== this.statsRequestToken) return
            notifyApiError(error, { messages: SERUM_ERRORS.list.initMeta })
        })
    },
    refreshTabData() {
      this.getList()
      this.getStats()
    },
    getList() {
      const isLatest = this.beginListRequest()
      this.listLoading = true
      // Handle Date Range
      if (this.dateRange && this.dateRange.length === 2) {
          this.listQuery.start_date = this.dateRange[0]
          this.listQuery.end_date = this.dateRange[1]
      } else {
          this.listQuery.start_date = undefined
          this.listQuery.end_date = undefined
      }

      const payload = this.buildQuery()
      if (JSON.stringify(this.statsPayload()) !== this.statsKey) this.getStats()
      fetchList(payload, skipGlobalErrorHandler).then((response) => {
        if (!isLatest()) return
        this.list = Array.isArray(response.items) ? response.items : []
        this.total = Number(response.total) || 0;
      }).catch((error) => {
         if (!isLatest()) return
         this.list = []
         this.total = 0
         notifyApiError(error, { messages: SERUM_ERRORS.list.loadList })
      }).finally(() => {
        if (!isLatest()) return
        this.listLoading = false
        this.markListFetched()
      })
    },
    toggleAdvanced() {
      const next = !this.showAdvancedFilters
      this.showAdvancedFilters = next
      if (this.extraColumnsTimer) {
        clearTimeout(this.extraColumnsTimer)
        this.extraColumnsTimer = 0
      }
      const tableVm = this.$refs.serumTable?.$
      if (tableVm && tableVm.$ready) {
        tableVm.$ready = false
        tableVm._vbenFilterPaused = true
      }
      // 1. 点击瞬间仅播放 220ms 筛选栏展开/收起过渡动画（期间冻结 ElTable.$ready，0ms 表格重排）；
      // 2. 待筛选栏过渡定格后（transitionend 或 250ms 兜底），再批量切换 6 个扩展列。
      this.extraColumnsTimer = window.setTimeout(() => {
        this.extraColumnsTimer = 0
        this.commitExtraColumnsSync()
      }, 250)
    },
    onAdvancedFiltersTransitionEnd(event) {
      if (event.target !== event.currentTarget || event.propertyName !== 'grid-template-rows') return
      if (this.extraColumnsTimer) {
        clearTimeout(this.extraColumnsTimer)
        this.extraColumnsTimer = 0
      }
      this.commitExtraColumnsSync()
    },
    commitExtraColumnsSync() {
      const next = this.showAdvancedFilters
      const tableRef = this.$refs.serumTable
      const tableVm = tableRef?.$
      if (this.showExtraColumns === next) {
        if (tableVm?._vbenFilterPaused) {
          tableVm.$ready = true
          tableVm._vbenFilterPaused = false
          tableRef?.doLayout?.()
        }
        return
      }
      if (tableVm && tableVm.$ready) {
        tableVm.$ready = false
        tableVm._vbenFilterPaused = true
      }
      this.showExtraColumns = next
      this.$nextTick(() => {
        if (tableVm) {
          tableVm.$ready = true
          tableVm._vbenFilterPaused = false
          tableVm.store?.updateColumns?.()
        }
        tableRef?.doLayout?.()
        if (next) {
          requestAnimationFrame(() => {
            this.smoothScrollTableToRight(true)
          })
        }
      })
    },
    resetFilters() {
      const { limit } = this.listQuery
      this.listQuery = {
        page: 1,
        limit,
        project_code: undefined,
        project_name: undefined,
        lab_notebook: undefined,
        cage_position: undefined,
        reviewer: undefined,
        owner: undefined,
        target_name: undefined,
        study_type: undefined,
        pm: undefined,
        mouse_strain: undefined,
        mouse_strain_category: undefined,
        project_status: undefined,
        start_date: undefined,
        end_date: undefined,
        sort_field: '',
        sort_dir: '',
      }
      this.clearHeaderFilters()
      this.dateRange = []
      this.ownerFilterQuery = ''
      this.reviewerFilterQuery = ''
      this.studyTypeFilterQuery = ''
      this.pmFilterQuery = ''
      this.mouseStrainFilterQuery = ''
      this.mouseStrainCategoryFilterQuery = ''
      this.statusFilterQuery = ''
      this.persistListFilters()
      this.getList()
    },
    handleStatusFilter(status) {
        if (this.listQuery.project_status === status) {
            this.listQuery.project_status = undefined
        } else {
            this.listQuery.project_status = status
        }
        this.handleFilter()
    },
    handleOwnerFilter(owner) {
         if (this.listQuery.owner === owner) {
            this.listQuery.owner = undefined // Toggle off
        } else {
            this.listQuery.owner = owner // Toggle on
        }
        this.handleFilter()
    },
    handleTotalClick() {
        this.chartVisible = true
    },
    handleCreate() {
      if (!this.canCreateProject()) {
        ElMessage.warning('您没有权限新建项目')
        return
      }
      this.$router.push('/serum/edit')
    },
    handleView(row) {
        this.$router.push({ path: '/serum/detail', query: { id: row.id } })
    },
    handlePrintScheme(row) {
      if (!row?.id || this.schemePrintLoading) return
      this.schemePrintLoading = true
      const loadingMsg = ElMessage({
        message: '正在生成打印预览，请稍候…',
        type: 'info',
        duration: 0,
      })
      exportSchemePdf({ ids: [row.id] })
        .then((response) => {
          const blob = response instanceof Blob ? response : new Blob([response], { type: 'application/pdf' })
          const url = window.URL.createObjectURL(blob)
          const printWindow = window.open(url, '_blank')
          if (!printWindow) {
            window.URL.revokeObjectURL(url)
            throw new Error('浏览器拦截了弹窗，请允许弹窗后重试')
          }
          setTimeout(() => {
            printWindow.focus()
            printWindow.print()
            window.URL.revokeObjectURL(url)
          }, 1000)
        })
        .catch((err) => {
          if (err instanceof Error && err.message.includes('浏览器拦截')) {
            ElMessage.error(err.message)
            return
          }
          notifyApiError(err, { messages: SERUM_ERRORS.detail.exportPdf })
        })
        .finally(() => {
          loadingMsg.close()
          this.schemePrintLoading = false
        })
    },
    handleUpdate(row, type) {
        if (type === 'titer') {
            if (!this.canEditTiter(row)) {
                ElMessage.warning('您没有权限编辑此项目')
                return
            }
        } else {
            if (!this.canEdit(row)) {
                ElMessage.warning('您没有权限编辑此项目')
                return
            }
        }
        if (type === 'titer') {
            this.$router.push({ path: '/serum/titer', query: { id: row.id } })
        } else {
            this.$router.push({ path: '/serum/edit', query: { id: row.id } })
        }
    },
    canCreateProject() {
        return canCreateSerumProject(this.currentUserInfo)
    },
    canEdit(row) {
        return canEditSerumProject(this.currentUserInfo, row)
    },
    canEditTiter(row) {
        return canEditSerumTiter(this.currentUserInfo, row)
    },
    canUpdateStatus(row) {
        return canUpdateSerumStatus(this.currentUserInfo, row)
    },
    canUpdateCage(row) {
        return canUpdateSerumCage(this.currentUserInfo, row)
    },
    canExportMouse() {
        return canExportSerumMouse(this.currentUserInfo)
    },
    canAutoUpdateStatus() {
        return canAutoUpdateSerumStatus(this.currentUserInfo)
    },
    canViewCellInventory() {
        return canViewSerumCellInventory(this.currentUserInfo)
    },
    setFilterQuery(key, query) {
        this[`${key}FilterQuery`] = query;
    },
    filterOptions(dataArray, query) {
        const queryLower = (query || '').toLowerCase();
        if (!queryLower) return dataArray;
        
        return dataArray
            .filter(item => item.toLowerCase().includes(queryLower))
            .sort((a, b) => {
                const aStarts = a.toLowerCase().startsWith(queryLower);
                const bStarts = b.toLowerCase().startsWith(queryLower);
                return aStarts === bStarts ? a.localeCompare(b) : (aStarts ? -1 : 1);
            });
    },
    handleMouseRightClick(event) {
      event.preventDefault()
      this.isCageMode = !this.isCageMode
      this.editingRowId = null
      this.editingField = ''
      this.editingValue = ''
      if (this.isCageMode) {
        ElMessage.info('已切换到笼位编辑模式')
      }
    },
    handleCageClick(row) {
      if (!this.isCageMode) {
        return
      }
      if (!this.canUpdateCage(row)) {
        ElMessage.warning('您没有权限编辑此项目')
        return
      }
      this.startInlineEdit(row.id, 'cage', row.cage_position_display || '')
      this.focusInlineInput(row.id, 'input')
    },
    handleEnter(row) {
      this.saveCagePosition(row)
    },
    handleBlur(row) {
      this.saveCagePosition(row)
    },
    saveCagePosition(row) {
      const field = 'cage'
      const key = `${row.id}:${field}`
      if (this.savingKeys[key]) {
        return
      }
      if (this.editingField !== field || this.editingRowId !== row.id) {
        return
      }
      if (this.editingValue.trim() === this.editingOriginalValue) {
        this.stopInlineEditIfCurrent(row.id, field)
        return
      }
      if (!this.canUpdateCage(row)) {
        ElMessage.warning('您没有权限编辑此项目')
        this.stopInlineEditIfCurrent(row.id, field)
        return
      }
      const value = this.editingValue.trim()
      const previous = row.cage_position_display || ''
      row.cage_position = value
      row.cage_position_display = value
      this.savingKeys[key] = true
      updateCagePosition({
        id: row.id,
        cage_position: value,
      }).then(() => {
        ElMessage.success('笼位更新成功')
        this.stopInlineEditIfCurrent(row.id, field)
      }).catch((error) => {
        const resolved = resolveUserMessage(error, {
          messages: SERUM_ERRORS.list.updateCage,
        })
        if (resolved.level === 'warning') {
          ElMessage.warning(resolved.message)
          row.cage_position = ''
          row.cage_position_display = ''
        } else {
          row.cage_position = previous
          row.cage_position_display = previous
          notifyApiError(error, { messages: SERUM_ERRORS.list.updateCage })
        }
        this.stopInlineEditIfCurrent(row.id, field)
      }).finally(() => {
        this.savingKeys[key] = false
      })
    },
    handleInlineEditClick(row, field) {
      if (!this.canEdit(row)) {
        ElMessage.warning('您没有权限编辑此项目')
        return
      }
      this.startInlineEdit(row.id, field, row[field] || '')
      this.focusInlineInput(row.id, '.inline-edit-input input')
    },
    startInlineEdit(rowId, field, value) {
      this.editingRowId = rowId
      this.editingField = field
      this.editingValue = value
      this.editingOriginalValue = value
    },
    focusInlineInput(rowId, selector) {
      this.$nextTick(() => {
        setTimeout(() => {
          const rowEl = this.$el.querySelector(`.serum-row-${rowId}`)
          const inputEl = rowEl && rowEl.querySelector(selector)
          if (inputEl) {
            inputEl.focus()
            inputEl.select()
          }
        }, 0)
      })
    },
    stopInlineEditIfCurrent(rowId, field) {
      if (this.editingRowId !== rowId || this.editingField !== field) {
        return
      }
      this.editingRowId = null
      this.editingField = ''
      this.editingValue = ''
    },
    saveInlineField(row, field) {
      const spec = INLINE_EDIT_FIELDS[field]
      const key = `${row.id}:${field}`
      if (this.savingKeys[key]) {
        return
      }
      if (this.editingField !== field || this.editingRowId !== row.id) {
        return
      }
      const value = spec.normalize(this.editingValue)
      if (value === (row[field] || '')) {
        this.stopInlineEditIfCurrent(row.id, field)
        return
      }
      if (!this.canEdit(row)) {
        ElMessage.warning('您没有权限编辑此项目')
        this.stopInlineEditIfCurrent(row.id, field)
        return
      }
      const previous = row[field] || ''
      row[field] = value
      this.savingKeys[key] = true
      spec.save({
        id: row.id,
        [field]: value,
      }).then((response) => {
        row[field] = response?.[field] ?? value
        ElMessage.success(spec.success)
        this.stopInlineEditIfCurrent(row.id, field)
      }).catch((error) => {
        row[field] = previous
        notifyApiError(error, { messages: spec.errors })
        this.stopInlineEditIfCurrent(row.id, field)
      }).finally(() => {
        this.savingKeys[key] = false
      })
    },
    onProjectStatusChange(row, newStatus) {
      row.project_status = newStatus
      this.getStats()
    },
    handleExport() {
        if (!this.canExportMouse()) {
            ElMessage.warning('您没有权限导出小鼠免疫数据')
            return
        }
        const [startDate, endDate] = this.dateRange?.length === 2 ? this.dateRange : [undefined, undefined]
        
        if (!startDate || !endDate) {
            ElMessageBox.confirm('您未选择时间段，将导出所有数据，是否继续？', '提示', {
                confirmButtonText: '继续导出',
                cancelButtonText: '取消',
                type: 'warning'
            }).then(() => {
                this.performExport(startDate, endDate)
            }).catch(() => {
                
            })
        } else {
            this.performExport(startDate, endDate)
        }
    },
    async handleListExport() {
        try {
            await downloadListExcel(
                () => exportSerumList(this.buildQuery()),
                `免疫实验列表_${excelTimestamp()}.xlsx`,
            )
        } catch (error) {
            notifyApiError(error, { messages: SERUM_ERRORS.list.exportList })
        }
    },
    
    performExport(startDate, endDate) {
        const loading = ElLoading.service({
            lock: true,
            text: '正在导出数据...',
            background: 'rgba(0, 0, 0, 0.7)'
        })
        
        const exportQuery = this.buildQuery()
        exportQuery.start_date = startDate
        exportQuery.end_date = endDate
        
        export_mouse(exportQuery).then(response => {
            const blob = response instanceof Blob ? response : new Blob([response], {
                type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            })
            const timestamp = new Date(Date.now() + 8 * 60 * 60 * 1000)
                .toISOString()
                .slice(0, 16)
                .replace('T', '_')
                .replace(':', '')
            downloadBlob(blob, `小鼠免疫导出_${timestamp}.xlsx`)
            ElMessage.success('导出成功')
        }).catch((error) => {
            notifyApiError(error, { messages: SERUM_ERRORS.list.exportMouse })
        }).finally(() => {
            loading.close()
        })
    },
    
    handleAutoUpdateStatus() {
        if (!this.canAutoUpdateStatus()) {
            ElMessage.warning('您没有权限自动更新状态')
            return
        }
        ElMessageBox.confirm('确定要根据当前筛选条件自动更新所有实验的状态吗？', '提示', {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
        }).then(() => {
            const loading = ElLoading.service({
                lock: true,
                text: '正在哈基米南北绿豆ing...',
                background: 'rgba(0, 0, 0, 0.7)'
            })
            
            const updateQuery = this.buildQuery()
            
            autoUpdateStatus(updateQuery).then(response => {
                ElMessage.success('状态更新成功')
                this.getList()
                this.getStats()
            }).catch((error) => {
                notifyApiError(error, { messages: SERUM_ERRORS.list.autoUpdateStatus })
            }).finally(() => {
                loading.close()
            })
        }).catch(() => {
            
        })
    }
  }
}
</script>

<style scoped>
.app-container {
    position: relative;
    padding: var(--list-page-padding);
    background-color: var(--list-page-bg);
    min-height: 100%;
}
.filter-wrapper {
    background: var(--list-surface-bg);
    padding: var(--list-surface-padding-y) var(--list-surface-padding-x);
    border: var(--list-surface-border);
    border-radius: var(--list-surface-radius);
    margin-bottom: var(--list-page-gap);
    box-shadow: var(--list-surface-shadow);
}
.app-container :deep(.status-column-cell .cell) {
    padding-left: 5px;
    padding-right: 5px;
}
.app-container :deep(td.inline-edit-cell) {
    height: 1px;
    padding: 0;
}
.app-container :deep(.inline-edit-cell .cell) {
    height: 100%;
    padding: 0;
}
.app-container :deep(.inline-edit-cell .inline-edit-trigger) {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
    padding: 0 8px;
    border: 0;
    background: transparent;
    color: inherit;
    font: inherit;
    line-height: inherit;
    cursor: default;
}
.app-container :deep(.inline-edit-cell .inline-edit-trigger.is-editable) {
    cursor: pointer;
}
.app-container :deep(.inline-edit-cell .inline-edit-input) {
    width: 100%;
    height: 100%;
    --el-input-height: 100%;
}
.app-container :deep(.inline-edit-cell .inline-edit-input .el-input__wrapper),
.app-container :deep(.inline-edit-cell .inline-edit-input .el-select__wrapper) {
    height: 100%;
    min-height: 100%;
    border-radius: 0;
}
.filter-item {
    width: 100%;
}
.advanced-trigger-icon {
    transition: transform 0.22s cubic-bezier(0.22, 1, 0.36, 1);
}
.advanced-trigger-icon.is-expanded {
    transform: rotate(180deg);
}
.advanced-filters-collapse {
    display: grid;
    grid-template-rows: 0fr;
    opacity: 0;
    margin-top: 0;
    pointer-events: none;
    transition:
        grid-template-rows 0.22s cubic-bezier(0.22, 1, 0.36, 1),
        opacity 0.18s ease,
        margin-top 0.22s cubic-bezier(0.22, 1, 0.36, 1);
}
.advanced-filters-collapse.is-expanded {
    grid-template-rows: 1fr;
    opacity: 1;
    margin-top: 10px;
    pointer-events: auto;
}
.advanced-filters-inner {
    min-height: 0;
    overflow: hidden;
}
.advanced-filters {
    padding-top: 10px;
    border-top: 1px dashed var(--el-border-color-light);
}
.project-name {
    font-weight: 500;
    color: var(--el-text-color-primary);
}

/* Dashboard Panel Styles */
.panel-group {
  margin-top: 0px;
  margin-bottom: 20px;
}
.card-panel-col {
  margin-bottom: var(--list-page-gap);
}
.card-panel {
  height: 100px;
  cursor: pointer;
  font-size: 12px;
  position: relative;
  overflow: hidden;
  color: #fff;
  background: var(--el-bg-color);
  box-shadow: 4px 4px 40px rgba(0, 0, 0, .05);
  border-radius: var(--list-mid-radius);
  display: flex;
  align-items: center;
  padding: 0 20px; 
  transition:
    transform 0.25s cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 0.25s ease;
}
.card-panel:hover {
    transform: translateY(-5px);
    box-shadow: 0 15px 30px rgba(0,0,0,0.1);
}
.active-card {
    border: 2px solid var(--el-text-color-primary);
    transform: scale(1.02);
    box-shadow: 0 10px 20px rgba(0,0,0,0.2);
}

.card-panel-icon-wrapper {
  margin: 0; 
  padding: 10px;
  border-radius: var(--list-inner-radius);
  background: rgba(255,255,255,0.2);
  display: flex;
  align-items: center;
  justify-content: center;
}
.card-panel-icon {
  font-size: 40px; 
}
.card-panel-icon :deep(svg) {
  width: 1em;
  height: 1em;
}
.card-panel-description {
  font-weight: bold;
  margin-left: auto; 
  text-align: right;
}
.card-panel-text {
  line-height: 18px;
  font-size: 14px;
  margin-bottom: 8px;
  opacity: 0.9;
}
.card-panel-num {
  font-size: 24px;
  font-weight: bold;
}

/* Gradient Backgrounds */
.blue-panel { background: linear-gradient(135deg, #36a3f7 0%, #1890ff 100%); }
.green-panel { background: linear-gradient(135deg, #58d68d 0%, #2ecc71 100%); }
.red-panel { background: linear-gradient(135deg, #8e44ad 0%, #9b59b6 100%); }
.orange-panel { background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%); }

html.dark .card-panel { filter: brightness(0.86) saturate(0.9); }
</style>
