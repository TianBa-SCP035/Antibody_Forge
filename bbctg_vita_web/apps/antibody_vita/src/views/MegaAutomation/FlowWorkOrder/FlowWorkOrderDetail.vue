<template>
  <div class="app-container flow-order-detail">
    <!-- 顶部标题 + 操作 -->
    <div class="detail-header">
      <div class="header-title">
        <el-button text class="back-btn" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <div class="title-block">
          <h1 class="page-title">{{ isViewMode ? '流式工单详情（只读）' : '流式工单详情' }}</h1>
          <span class="page-subtitle">{{ loading ? '正在加载工单...' : pageSubtitle }}</span>
        </div>
        <el-tag v-if="!loading" :type="statusTagType(orderDisplayStatus)" effect="light" round>
          {{ orderDisplayLabel }}
        </el-tag>
      </div>
      <div v-if="!loading" class="header-actions">
        <el-button
          v-if="showSaveButton"
          type="primary"
          :loading="saving"
          :disabled="!canEdit()"
          @click="save"
        >
          保存
        </el-button>
        <el-button
          v-if="showValidateButton"
          type="success"
          plain
          :disabled="!canEdit()"
          @click="validate"
        >
          校验
        </el-button>
        <el-button
          v-if="showDispatchButton"
          type="warning"
          plain
          :loading="actionLoading"
          :disabled="!canDispatch()"
          @click="dispatchOrder"
        >
          发送
        </el-button>
        <el-button
          v-if="showConfirmExecutionButton"
          type="success"
          plain
          :disabled="!canDispatch()"
          @click="confirmExecution"
        >
          确认执行
        </el-button>
        <el-button
          v-if="showCompleteButton"
          type="success"
          plain
          :disabled="!canDispatch()"
          @click="completeOrder"
        >
          完成
        </el-button>
        <el-button
          v-if="showFailButton"
          type="danger"
          plain
          :disabled="!canDispatch()"
          @click="failOrder"
        >
          执行失败
        </el-button>
        <el-button
          v-if="showPauseAckButton"
          type="warning"
          plain
          :loading="actionLoading"
          :disabled="!canDispatch()"
          @click="acknowledgePause"
        >
          设备已暂停
        </el-button>
        <el-button
          v-if="showResumeAckButton"
          type="primary"
          plain
          :loading="actionLoading"
          :disabled="!canDispatch()"
          @click="acknowledgeResume"
        >
          设备已恢复
        </el-button>
        <el-button
          v-if="showPauseButton"
          type="warning"
          plain
          :disabled="!canDispatch()"
          @click="pauseOrder"
        >
          停止
        </el-button>
        <el-button
          v-if="showResumeButton"
          type="primary"
          plain
          :loading="actionLoading"
          :disabled="!canDispatch()"
          @click="resumeOrder"
        >
          继续
        </el-button>
        <el-button
          v-if="showDeleteButton"
          type="danger"
          plain
          :disabled="!canEdit()"
          @click="deleteOrder"
        >
          删除
        </el-button>
        <el-button
          v-if="showVoidButton"
          type="danger"
          plain
          :disabled="!canEdit()"
          @click="voidOrder"
        >
          作废
        </el-button>
      </div>
    </div>

    <div
      v-if="loading"
      v-loading="true"
      element-loading-text="正在读取并解析工单数据..."
      class="detail-loading"
    ></div>
    <div v-if="!loading && validationIssues.length" class="validation-banner">
      <div class="validation-banner-head">
        <strong>校验未通过（{{ validationIssues.length }}）</strong>
        <el-button text size="small" @click="clearValidationIssues">关闭</el-button>
      </div>
      <ul class="validation-banner-list">
        <li v-for="(item, index) in validationIssues" :key="item.field + '-' + index">
          {{ item.message }}
        </li>
      </ul>
    </div>
    <div
      v-if="!loading && order.status === 'validated' && optionalWellWarnings.total"
      class="optional-warning-banner"
    >
      校验已通过，但{{ optionalWellWarnings.text }}。这些内容为可选项，可直接发送；跟随提示可继续补充。
    </div>

    <div v-if="!loading && loadError" class="validation-banner">
      工单加载失败。为避免误建工单，当前页面已禁止保存和操作，请返回列表后重试。
    </div>
    <div v-else-if="!loading && !order.id" class="preview-banner">
      当前为未保存草稿，填写订单编号后可保存。
    </div>

    <!-- 基础信息 + 时间线 -->
    <section v-if="!loading" class="panel base-panel">
      <div class="panel-head">
        <div class="panel-head-left">
          <el-icon class="head-icon"><Menu /></el-icon>
          <span class="panel-title">基本信息</span>
        </div>
      </div>
      <div class="base-grid">
        <label class="base-field" :class="{ 'is-invalid': hasFieldError('order_no') }">
          <span class="field-label">订单编号</span>
          <el-input v-model="order.order_no" :disabled="fieldDisabled" placeholder="请输入订单编号" />
        </label>
        <label class="base-field">
          <span class="field-label">订单名称</span>
          <el-input v-model="order.base_info.order_name" :disabled="fieldDisabled" placeholder="请输入订单名称" />
        </label>
        <label class="base-field">
          <span class="field-label">检测类型</span>
          <el-select v-model="order.data_type" :disabled="fieldDisabled" class="field-control" placeholder="选择类型">
            <el-option v-for="item in dataTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </label>
        <label class="base-field">
          <span class="field-label">优先级</span>
          <el-select v-model="order.priority" :disabled="fieldDisabled" class="field-control" placeholder="优先级">
            <el-option v-for="item in priorityOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </label>
        <label class="base-field base-field--wide">
          <span class="field-label">备注</span>
          <el-input v-model="order.base_info.remark" :disabled="fieldDisabled" placeholder="备注（可选）" />
        </label>
      </div>
      <div class="timeline-strip">
        <span class="timeline-label">下发记录</span>
        <div class="timeline-chips">
          <span
            v-for="item in compactEvents"
            :key="item.id || item.dispatch_id"
            class="timeline-chip"
            :title="item.sent_at"
          >
            {{ dispatchChipLabel(item) }}
          </span>
          <span v-if="!compactEvents.length" class="timeline-chip is-empty">{{ orderDisplayLabel }}</span>
        </div>
      </div>
    </section>

    <el-tabs v-if="!loading" v-model="activeTab" class="detail-tabs">
      <el-tab-pane label="工单编辑" name="editor">
        <div class="editor-layout">
          <!-- 左侧：板级信息表格 -->
          <div class="editor-col editor-col--left">
            <!-- 工单表格：样本板 × 细胞 -->
            <section class="panel">
              <div class="panel-head">
                <div class="panel-head-left">
                  <el-icon class="head-icon"><Grid /></el-icon>
                  <span class="panel-title">工单表格</span>
                  <span class="panel-hint">序号即仪器执行顺序，按住 # 列拖动调整</span>
                </div>
                <el-button size="small" :disabled="fieldDisabled" @click="addSamplePlate">
                  <el-icon><Plus /></el-icon>新增样本板
                </el-button>
              </div>
              <el-table
                ref="samplePlateTable"
                :data="order.sample_plates"
                :row-key="samplePlateRowKey"
                border
                size="small"
                class="info-table sample-plate-table"
                :row-class-name="samplePlateRowClass"
                @row-click="selectSamplePlate"
              >
                <el-table-column label="#" width="48" align="center" class-name="drag-cell">
                  <template #default="{ $index }">
                    <div
                      class="row-drag-handle"
                      :class="{ 'is-disabled': fieldDisabled }"
                      title="按住拖动排序"
                      @click.stop
                    >
                      {{ $index + 1 }}
                    </div>
                  </template>
                </el-table-column>
                <el-table-column label="样本板条码" min-width="150">
                  <template #default="{ row, $index }">
                    <el-input
                      v-model="row.barcode"
                      size="small"
                      :disabled="fieldDisabled"
                      :class="{ 'is-invalid-control': hasFieldError(`sample_plates.${$index}.barcode`) }"
                      placeholder="扫描/输入条码"
                    />
                  </template>
                </el-table-column>
                <el-table-column label="项目号" min-width="110">
                  <template #default="{ row, $index }">
                    <el-input
                      v-model="row.project_no"
                      size="small"
                      :disabled="fieldDisabled"
                      :class="{ 'is-invalid-control': hasFieldError(`sample_plates.${$index}.project_no`) }"
                      placeholder="项目号"
                    />
                  </template>
                </el-table-column>
                <el-table-column label="靶点" min-width="90">
                  <template #default="{ row, $index }">
                    <el-input
                      v-model="row.target"
                      size="small"
                      :disabled="fieldDisabled"
                      :class="{ 'is-invalid-control': hasFieldError(`sample_plates.${$index}.target`) }"
                      placeholder="靶点"
                    />
                  </template>
                </el-table-column>
                <el-table-column label="检测细胞（种属）" min-width="150">
                  <template #default="{ row, $index }">
                    <el-popover
                      placement="bottom-start"
                      trigger="click"
                      :width="280"
                      :disabled="fieldDisabled"
                      :show-arrow="false"
                      transition="el-zoom-in-top"
                      popper-class="cell-picker-popper"
                      @show="onCellPickerShow(row)"
                      @hide="onCellPickerHide"
                    >
                      <template #reference>
                        <div
                          class="cell-select-trigger"
                          :class="{
                            'is-disabled': fieldDisabled,
                            'is-open': activeCellPickerRowKey === row._rowKey,
                            'is-invalid-control': hasFieldError(`sample_plates.${$index}.cell_keys`),
                          }"
                        >
                          <span v-if="cellSpeciesSummary(row)" class="cell-select-text">
                            {{ cellSpeciesSummary(row) }}
                          </span>
                          <span v-else class="cell-select-placeholder">选择细胞</span>
                          <el-icon class="cell-select-arrow"><ArrowDown /></el-icon>
                        </div>
                      </template>
                      <div class="cell-picker">
                        <template v-if="hasSelectableCells">
                          <div
                            v-for="(group, gIdx) in cellPickerOptions"
                            v-show="group.children.length"
                            :key="group.value"
                            class="cell-picker-group"
                            :class="{ 'is-open': isCellPlateExpanded(gIdx) }"
                          >
                            <div class="cell-picker-group-head" @click="toggleCellPlate(gIdx)">
                              <el-icon class="cell-picker-group-arrow"><ArrowRight /></el-icon>
                              <span class="cell-picker-group-name">{{ group.label }}</span>
                              <span
                                v-if="selectedCountInPlate(row, group)"
                                class="cell-picker-group-count"
                              >{{ selectedCountInPlate(row, group) }}</span>
                            </div>
                            <div v-show="isCellPlateExpanded(gIdx)" class="cell-picker-group-body">
                              <div
                                v-for="cell in group.children"
                                :key="cell.value"
                                class="cell-picker-option"
                                :class="{ 'is-selected': isCellSelected(row, cell.value) }"
                                @click="toggleCell(row, cell.value)"
                              >
                                <span class="cell-picker-option-name">
                                  {{ cell.cellName || '未命名细胞' }}
                                </span>
                                <span class="cell-picker-option-col">列{{ cell.columnNo }}</span>
                                <el-icon
                                  v-if="isCellSelected(row, cell.value)"
                                  class="cell-picker-option-check"
                                ><Check /></el-icon>
                              </div>
                            </div>
                          </div>
                        </template>
                        <div v-else class="cell-picker-empty">
                          暂无可选细胞，请先在下方填写细胞名称
                        </div>
                      </div>
                    </el-popover>
                  </template>
                </el-table-column>
                <el-table-column label="二抗" width="76">
                  <template #default="{ row }">
                    <el-select v-model="row.secondary_antibody" size="small" :disabled="fieldDisabled">
                      <el-option v-for="item in secondaryAntibodyOptions" :key="item" :label="item" :value="item" />
                    </el-select>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="56" align="center" class-name="sample-plate-op">
                  <template #default="{ $index }">
                    <el-button
                      text
                      type="danger"
                      size="small"
                      class="sample-plate-op"
                      title="删除"
                      :disabled="fieldDisabled || order.sample_plates.length <= 1"
                      @click.stop="removeSamplePlate($index)"
                    >
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </section>

            <CellPlateEditor
              v-model="activeCellPlate"
              class="panel flow-editor-panel"
              :plates="order.cell_plates"
              :disabled="fieldDisabled"
              :cell-type-options="cellTypeOptions"
              :species-options="speciesOptions"
              :has-field-error="hasFieldError"
              @add="addCellPlate"
              @remove="removeCellPlate"
              @barcode-focus="rememberCellBarcode"
              @barcode-change="remapCellBarcode"
              @reordered="handleCellColumnsReordered"
            />

            <!-- PC 信息 -->
            <section class="panel">
              <div class="panel-head">
                <div class="panel-head-left">
                  <el-icon class="head-icon"><CircleCheck /></el-icon>
                  <span class="panel-title">PC 信息</span>
                  <span class="panel-hint">样本板 PC / ISO / TAG 孔位引用此处</span>
                </div>
                <el-button size="small" :disabled="fieldDisabled" @click="addPcInfo">
                  <el-icon><Plus /></el-icon>新增 PC
                </el-button>
              </div>
              <el-table :data="pcInfos" border size="small" class="info-table" row-key="pc_id">
                <el-table-column label="PC 名称" min-width="160">
                  <template #default="{ row }">
                    <el-input v-model="row.pc_name" size="small" :disabled="fieldDisabled" placeholder="必填" />
                  </template>
                </el-table-column>
                <el-table-column label="类型" width="96">
                  <template #default="{ row }">
                    <el-select v-model="row.pc_type" size="small" :disabled="fieldDisabled">
                      <el-option v-for="t in pcInfoTypeOptions" :key="t" :label="t" :value="t" />
                    </el-select>
                  </template>
                </el-table-column>
                <el-table-column label="货号/批次" min-width="120">
                  <template #default="{ row }">
                    <el-input v-model="row.catalog_batch" size="small" :disabled="fieldDisabled" />
                  </template>
                </el-table-column>
                <el-table-column label="来源" min-width="100">
                  <template #default="{ row }">
                    <el-input v-model="row.source" size="small" :disabled="fieldDisabled" />
                  </template>
                </el-table-column>
                <el-table-column label="浓度" min-width="100">
                  <template #default="{ row }">
                    <el-input v-model="row.concentration" size="small" :disabled="fieldDisabled" />
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="52" align="center">
                  <template #default="{ $index }">
                    <el-button text type="danger" size="small" :disabled="fieldDisabled" @click="removePcInfo($index)">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
              <p v-if="!pcInfos.length" class="empty-hint">暂无 PC，点击右上角新增。</p>
            </section>
          </div>

          <!-- 右侧：孔位 / 板可视化 -->
          <div class="editor-col editor-col--right">
            <SamplePlateLayout
              ref="samplePlateLayout"
              v-model="activeSamplePlate"
              class="panel viz-panel flow-editor-panel"
              :plate="selectedSamplePlate"
              :plate-count="order.sample_plates.length"
              :pc-infos="pcInfos"
              :disabled="fieldDisabled"
              :warning-well-nos="activeOptionalWarningWells"
            />

            <!-- 细胞板视图（长条板转 90°：12 横向泳道） -->
            <section class="panel viz-panel">
              <div class="panel-head">
                <div class="panel-head-left">
                  <el-icon class="head-icon"><Menu /></el-icon>
                  <span class="panel-title">细胞板视图</span>
                  <span class="panel-hint">12 列整列加样，横向展开便于阅读</span>
                </div>
                <PlateTabSwitch
                  v-model="activeCellPlate"
                  :count="order.cell_plates.length"
                  prefix="细胞板"
                />
              </div>
              <div class="lane-list">
                <div
                  v-for="col in selectedCellPlate.columns"
                  :key="'lane-' + col.column_no"
                  class="cell-lane"
                  :class="{ 'is-filled': !!col.cell_name }"
                >
                  <div class="lane-wells">
                    <span v-for="n in 8" :key="'lw-' + col.column_no + '-' + n" class="lane-well"></span>
                  </div>
                  <div class="lane-no">第 {{ col.column_no }} 列</div>
                  <div class="lane-body">
                    <span class="lane-name">{{ col.cell_name || '空列' }}</span>
                    <span class="lane-meta">
                      {{ col.cell_type || '—' }}
                      <template v-if="col.generation"> · {{ col.generation }}</template>
                      <template v-if="col.batch"> · {{ col.batch }}</template>
                    </span>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="铺板" name="plating">
        <div class="plating-toolbar">
          <div class="plating-toolbar-left">
            <span class="plating-title">铺板对照</span>
            <span class="plating-stats">
              样本板 {{ order.sample_plates.length }} · 细胞板 {{ order.cell_plates.length }}
            </span>
            <span class="plating-hint">右侧点选跳转；锁定后避免误改</span>
          </div>
          <el-button size="small" @click="plateMapLocked = !plateMapLocked">
            <el-icon>
              <Lock v-if="plateMapLocked" />
              <Unlock v-else />
            </el-icon>
            {{ plateMapLocked ? '已锁定' : '解锁编辑' }}
          </el-button>
        </div>
        <div class="plating-layout">
          <div class="plating-main">
            <div
              v-for="(plate, index) in order.sample_plates"
              :id="'plating-sample-' + index"
              :key="'plating-sample-' + (plate._rowKey || index)"
              class="plating-plate-wrap"
              :class="{ 'is-plating-focus': platingFocus === `sample:${index}` }"
              @click="platingFocus = `sample:${index}`"
            >
              <SamplePlateLayout
                class="panel viz-panel flow-editor-panel plating-plate"
                :plate="plate"
                :plate-title="`样本板 ${index + 1}`"
                :pc-infos="pcInfos"
                :disabled="plateMapDisabled"
                standalone
              />
            </div>
            <div
              v-for="(plate, index) in order.cell_plates"
              :id="'plating-cell-' + index"
              :key="'plating-cell-' + index"
              class="plating-plate-wrap"
              :class="{ 'is-plating-focus': platingFocus === `cell:${index}` }"
              @click="platingFocus = `cell:${index}`"
            >
              <CellPlateLayout
                class="panel viz-panel flow-editor-panel plating-plate"
                :plate="plate"
                :plate-index="index"
                :plate-title="`细胞板 ${index + 1}`"
                :disabled="plateMapDisabled"
                @barcode-focus="rememberCellBarcode"
                @barcode-change="remapCellBarcode"
              />
            </div>
          </div>
          <aside class="plating-nav panel">
            <div class="plating-nav-head">
              <span class="plating-nav-title">板总览</span>
              <span class="plating-nav-hint">点击跳转</span>
            </div>
            <div class="plating-nav-group">
              <div class="plating-nav-label">样本板</div>
              <div class="plating-nav-sample-grid">
                <button
                  v-for="(plate, index) in order.sample_plates"
                  :key="'nav-sample-' + index"
                  type="button"
                  class="nav-sample-tile"
                  :class="{ 'is-active': platingFocus === `sample:${index}` }"
                  @click="jumpToPlatingPlate('sample', index)"
                >
                  <div class="nav-sample-line">
                    <span class="nav-id">S-{{ index + 1 }}</span>
                    <span class="nav-species" :title="platingSampleSpecies(plate)">{{ platingSampleSpecies(plate) }}</span>
                  </div>
                  <span class="nav-mini-grid nav-mini-grid--sample">
                    <i
                      v-for="well in plate.wells || []"
                      :key="'nsw-' + index + '-' + well.well_no"
                      class="nav-mini-well"
                      :class="'well-' + String(well.content_type || 'sample').toLowerCase()"
                    ></i>
                  </span>
                </button>
              </div>
            </div>
            <div class="plating-nav-group">
              <div class="plating-nav-label">细胞板</div>
              <div class="plating-nav-sample-grid">
                <button
                  v-for="(plate, index) in order.cell_plates"
                  :key="'nav-cell-' + index"
                  type="button"
                  class="nav-sample-tile"
                  :class="{ 'is-active': platingFocus === `cell:${index}` }"
                  @click="jumpToPlatingPlate('cell', index)"
                >
                  <div class="nav-sample-line">
                    <span class="nav-id">C-{{ index + 1 }}</span>
                    <span class="nav-species" :title="platingCellSpecies(plate)">{{ platingCellSpecies(plate) }}</span>
                  </div>
                  <span class="nav-mini-grid nav-mini-grid--cell">
                    <i
                      v-for="col in plate.columns || []"
                      :key="'ncw-' + index + '-' + col.column_no"
                      class="nav-mini-col"
                      :class="platingNavCellColClass(col)"
                      :title="col.cell_name || `第 ${col.column_no} 列`"
                    ></i>
                  </span>
                </button>
              </div>
            </div>
          </aside>
        </div>
      </el-tab-pane>

      <el-tab-pane label="Payload" name="payload">
        <div class="json-layout json-layout--single">
          <section v-loading="activePayloadLoading" class="panel">
            <div class="panel-head">
              <div class="panel-head-left">
                <span class="panel-title">当前生效下发</span>
                <span v-if="activePayloadDispatch" class="panel-hint">
                  {{ activePayloadDispatch.dispatch_id }} · {{ activePayloadDispatch.sent_at }}
                </span>
                <span v-else class="panel-hint">仅显示未结束的下发记录</span>
              </div>
              <el-button
                size="small"
                :disabled="!activePayload"
                @click="copyActivePayload"
              >
                复制 JSON
              </el-button>
            </div>
            <pre class="json-panel">{{ formatJson(activePayload) }}</pre>
          </section>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script>
import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  Check,
  CircleCheck,
  Delete,
  Grid,
  Lock,
  Menu,
  Plus,
  Unlock,
} from '@element-plus/icons-vue';
import {
  ElButton,
  ElIcon,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElPopover,
  ElSelect,
  ElTabPane,
  ElTable,
  ElTableColumn,
  ElTabs,
  ElTag,
} from 'element-plus';
import { useUserStore } from '@vben/stores';

import {
  acknowledgePauseFlowWorkOrder,
  acknowledgeResumeFlowWorkOrder,
  cancelFlowWorkOrder,
  completeFlowWorkOrder,
  confirmFlowWorkOrderExecution,
  deleteFlowWorkOrder,
  dispatchFlowWorkOrder,
  fetchActiveFlowWorkOrderPayload,
  fetchFlowWorkOrderDetail,
  fetchFlowWorkOrderMeta,
  failFlowWorkOrder,
  pauseFlowWorkOrder,
  resumeFlowWorkOrder,
  saveFlowWorkOrder,
  validateFlowWorkOrder,
} from '#/api/megaAutomation';
import {
  canDispatchMegaFlowWorkOrder,
  canEditMegaFlowWorkOrder,
} from '#/utils/serumPermission';
import {
  buildDispatchChipLabel,
  normalizePauseState,
  orderStatusTagType,
  resolveOrderDisplayLabel,
  resolveOrderDisplayStatus,
} from '#/utils/megaFlowWorkOrderStatus';
import CellPlateEditor from './components/CellPlateEditor.vue';
import CellPlateLayout from './components/CellPlateLayout.vue';
import PlateTabSwitch from './components/PlateTabSwitch.vue';
import SamplePlateLayout from './components/SamplePlateLayout.vue';
import {
  buildFlowWorkOrderSavePayload,
  cellKey,
  cellPlateBarcode,
  CELL_TYPE_OPTIONS,
  createDefaultColumns,
  createDefaultFlowWorkOrder,
  createDefaultSamplePlate,
  createLocalPcId,
  EDITABLE_STATUSES,
  isCellSelected,
  normalizeFlowWorkOrder,
  PC_INFO_TYPE_OPTIONS,
  SECONDARY_ANTIBODY_OPTIONS,
  selectedCountInPlate,
  SPECIES_OPTIONS,
} from './flowWorkOrderModel';

export default {
  name: 'MegaFlowWorkOrderDetail',
  components: {
    ArrowDown,
    ArrowLeft,
    ArrowRight,
    Check,
    CircleCheck,
    CellPlateEditor,
    CellPlateLayout,
    Delete,
    ElButton,
    ElIcon,
    ElInput,
    ElOption,
    ElPopover,
    ElSelect,
    ElTabPane,
    ElTable,
    ElTableColumn,
    ElTabs,
    ElTag,
    Grid,
    Lock,
    Menu,
    Plus,
    PlateTabSwitch,
    SamplePlateLayout,
    Unlock,
  },
  setup() {
    const userStore = useUserStore();
    return {
      cellKey,
      cellPlateBarcode,
      isCellSelected,
      selectedCountInPlate,
      userStore,
    };
  },
  data() {
    return {
      loading: true,
      loadError: false,
      loadedRouteIdentity: '',
      saving: false,
      actionLoading: false,
      activeTab: 'editor',
      plateMapLocked: true,
      platingFocus: 'sample:0',
      activePayload: null,
      activePayloadDispatch: null,
      activePayloadLoading: false,
      activeSamplePlate: '0',
      activeCellPlate: '0',
      cellPickerExpanded: {},
      activeCellPickerRowKey: '',
      order: createDefaultFlowWorkOrder(),
      defaultSampleWells: [],
      defaultCellColumns: [],
      dataTypeOptions: [
        { value: 'TITER', label: '效价' },
        { value: 'PLAS', label: '质粒' },
        { value: 'PCR', label: 'PCR' },
      ],
      priorityOptions: [
        { value: 'high', label: '高' },
        { value: 'normal', label: '普通' },
        { value: 'low', label: '低' },
      ],
      secondaryAntibodyOptions: SECONDARY_ANTIBODY_OPTIONS,
      speciesOptions: SPECIES_OPTIONS,
      cellTypeOptions: CELL_TYPE_OPTIONS,
      pcInfoTypeOptions: PC_INFO_TYPE_OPTIONS,
      samplePlateSortable: null,
      samplePlateSortableInitToken: 0,
      validationIssues: [],
      cellBarcodeFocusCache: {},
      pausedLocalDirty: false,
      pausedDirtyInit: false,
      pausedDirtyUnwatch: null,
      resumeBlocked: false,
    };
  },
  computed: {
    currentUserInfo() {
      return this.userStore.userInfo || {};
    },
    hasDispatches() {
      if (this.order.has_dispatches) return true;
      return Array.isArray(this.order.dispatches) && this.order.dispatches.length > 0;
    },
    isViewMode() {
      return String(this.$route.query.mode || '').toLowerCase() === 'view';
    },
    showSaveButton() {
      if (this.isViewMode) return false;
      return !this.order.id || EDITABLE_STATUSES.includes(this.order.status);
    },
    showValidateButton() {
      if (this.isViewMode) return false;
      const pausedAndReady = (
        this.order.status === 'paused'
        && normalizePauseState(this.latestDispatch?.pause_state) === 'paused'
      );
      return (
        this.order.id
        && (EDITABLE_STATUSES.includes(this.order.status) || pausedAndReady)
      );
    },
    showDispatchButton() {
      if (this.isViewMode) return false;
      return this.order.id && this.order.status === 'validated';
    },
    showPauseButton() {
      if (this.isViewMode) return false;
      if (!this.order.id || !['sent', 'running'].includes(this.order.status)) return false;
      const latest = this.latestDispatch;
      if (!latest) return false;
      if (!['pending', 'running'].includes(latest.status)) return false;
      return !normalizePauseState(latest.pause_state);
    },
    showPauseAckButton() {
      if (this.isViewMode) return false;
      if (!this.order.id || this.order.status !== 'paused') return false;
      const latest = this.latestDispatch;
      return latest && normalizePauseState(latest.pause_state) === 'pausing';
    },
    showResumeAckButton() {
      if (this.isViewMode) return false;
      if (!this.order.id || this.order.status !== 'paused') return false;
      const latest = this.latestDispatch;
      return latest && normalizePauseState(latest.pause_state) === 'resuming';
    },
    showConfirmExecutionButton() {
      if (this.isViewMode) return false;
      if (!this.order.id || this.order.status !== 'sent') return false;
      const latest = this.latestDispatch;
      if (!latest || normalizePauseState(latest.pause_state)) return false;
      return latest.status === 'pending';
    },
    showCompleteButton() {
      return !this.isViewMode && this.order.id && this.order.status === 'running';
    },
    showFailButton() {
      if (this.isViewMode || !this.order.id) return false;
      if (['sent', 'running'].includes(this.order.status)) return true;
      return (
        this.order.status === 'paused'
        && ['pending', 'running'].includes(this.latestDispatch?.status)
      );
    },
    showResumeButton() {
      if (this.isViewMode) return false;
      if (!this.order.id || this.order.status !== 'paused' || this.pausedLocalDirty || this.resumeBlocked) {
        return false;
      }
      const latest = this.latestDispatch;
      return latest && normalizePauseState(latest.pause_state) === 'paused';
    },
    showDeleteButton() {
      if (this.isViewMode) return false;
      return (
        this.order.id
        && !this.hasDispatches
        && !['cancelled', 'completed', 'sent', 'running', 'paused'].includes(this.order.status)
      );
    },
    showVoidButton() {
      if (this.isViewMode) return false;
      return (
        this.order.id
        && this.hasDispatches
        && !['cancelled', 'completed', 'sent', 'running'].includes(this.order.status)
        && (
          this.order.status !== 'paused'
          || normalizePauseState(this.latestDispatch?.pause_state) === 'paused'
        )
      );
    },
    fieldDisabled() {
      if (this.loadError || !this.canEdit()) return true;
      if (this.order.status === 'paused') {
        return normalizePauseState(this.latestDispatch?.pause_state) !== 'paused';
      }
      return !EDITABLE_STATUSES.includes(this.order.status);
    },
    plateMapDisabled() {
      return this.fieldDisabled || this.plateMapLocked;
    },
    orderDisplayLabel() {
      return resolveOrderDisplayLabel(this.order);
    },
    orderDisplayStatus() {
      return resolveOrderDisplayStatus(this.order);
    },
    pageSubtitle() {
      if (this.isViewMode) {
        return this.order.base_info?.order_name || this.order.order_no || '查看工单';
      }
      return this.order.base_info?.order_name || this.order.order_no || '新建工单（未保存）';
    },
    pcInfos() {
      return this.order.base_info.pc_infos;
    },
    selectedSamplePlate() {
      const index = Math.max(0, Number(this.activeSamplePlate) || 0);
      return this.order.sample_plates[index] || this.order.sample_plates[0] || { wells: [] };
    },
    selectedCellPlate() {
      const index = Math.max(0, Number(this.activeCellPlate) || 0);
      return this.order.cell_plates[index] || this.order.cell_plates[0] || { columns: [] };
    },
    compactEvents() {
      return (this.order.dispatches || []).slice(0, 5);
    },
    latestDispatch() {
      // 与后端 get_current_dispatch 一致：取最新未终止下发，勿用含 voided/completed/failed 的历史首条
      const terminal = new Set(['voided', 'completed', 'failed']);
      const list = this.order.dispatches || [];
      return list.find((item) => !terminal.has(String(item?.status || ''))) || null;
    },
    cellByKey() {
      const map = {};
      this.order.cell_plates.forEach((plate, plateIndex) => {
        const barcode = this.cellPlateBarcode(plate, plateIndex);
        (plate.columns || []).forEach((column) => {
          map[this.cellKey(barcode, column.column_no)] = column;
        });
      });
      return map;
    },
    cellPickerOptions() {
      return this.order.cell_plates.map((plate, plateIndex) => {
        const barcode = this.cellPlateBarcode(plate, plateIndex);
        return {
          label: `细胞板-${plateIndex + 1}`,
          value: barcode,
          // 只列出已命名的细胞（未命名的列对下发无意义）
          children: (plate.columns || [])
            .filter((column) => column.cell_name)
            .map((column) => ({
              cellName: column.cell_name || '',
              columnNo: column.column_no,
              value: this.cellKey(barcode, column.column_no),
            })),
        };
      });
    },
    hasSelectableCells() {
      return this.cellPickerOptions.some((group) => group.children.length);
    },
    optionalWellWarnings() {
      const byPlate = {};
      let pcCount = 0;
      let sampleCount = 0;
      (this.order.sample_plates || []).forEach((plate, plateIndex) => {
        const wellNos = [];
        (plate.wells || []).forEach((well) => {
          const type = String(well.content_type || '').toUpperCase();
          if (type === 'PC' && (well.pc_id == null || well.pc_id === '')) {
            pcCount += 1;
            wellNos.push(well.well_no);
          } else if (type === 'SAMPLE' && !String(well.sample_code || '').trim()) {
            sampleCount += 1;
            wellNos.push(well.well_no);
          }
        });
        byPlate[String(plateIndex)] = wellNos;
      });
      return {
        byPlate,
        text: [
          pcCount && `${pcCount} 个 PC 孔未关联信息`,
          sampleCount && `${sampleCount} 个样本孔未填写编码`,
        ]
          .filter(Boolean)
          .join('、'),
        total: pcCount + sampleCount,
      };
    },
    activeOptionalWarningWells() {
      if (this.order.status !== 'validated') return [];
      return this.optionalWellWarnings.byPlate[this.activeSamplePlate] || [];
    },
  },
  async created() {
    await this.loadMeta();
    await this.loadDetail();
  },
  activated() {
    if (!this.loading && this.loadedRouteIdentity !== this.detailRouteIdentity()) {
      this.loadDetail();
    }
  },
  beforeUnmount() {
    this.stopPausedDirtyWatch();
    this.samplePlateSortableInitToken += 1;
    this.destroySamplePlateSortable();
  },
  watch: {
    fieldDisabled(value) {
      if (this.samplePlateSortable) {
        this.samplePlateSortable.option('disabled', value);
      }
    },
    activeTab(value) {
      if (value === 'payload') {
        this.loadActivePayload();
      }
    },
    'order.status'(status) {
      if (status === 'paused') {
        this.startPausedDirtyWatch();
      } else {
        this.stopPausedDirtyWatch();
      }
    },
  },
  methods: {
    samplePlateRowKey(row) {
      return row._rowKey;
    },
    clearActivePayload() {
      this.activePayload = null;
      this.activePayloadDispatch = null;
    },
    jumpToPlatingPlate(kind, index) {
      this.platingFocus = `${kind}:${index}`;
      this.$nextTick(() => {
        const el = document.getElementById(`plating-${kind}-${index}`);
        el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    },
    platingSampleSpecies(plate) {
      const keys = Array.isArray(plate?.cell_keys) ? plate.cell_keys : [];
      if (!keys.length) return 'NA';
      const species = [];
      let hasNamed = false;
      keys.forEach((key) => {
        const col = this.cellByKey[key];
        if (!String(col?.cell_name || '').trim()) return;
        hasNamed = true;
        const token = String(col?.species || '').trim();
        if (token && !species.includes(token)) species.push(token);
      });
      if (!hasNamed) return 'NA';
      return species.length ? species.join('、') : 'NA';
    },
    platingCellSpecies(plate) {
      const columns = (plate?.columns || []).filter((column) => String(column?.cell_name || '').trim());
      if (!columns.length) return 'NA';
      const species = [];
      columns.forEach((column) => {
        const token = String(column?.species || '').trim();
        if (token && !species.includes(token)) species.push(token);
      });
      return species.length ? species.join('、') : 'NA';
    },
    platingNavCellColClass(column) {
      const filled = !!String(column?.cell_name || '').trim();
      if (!filled) return { 'is-empty': true };
      const isTumor = String(column?.cell_type || '').trim() === '肿瘤';
      return isTumor ? { 'is-tumor': true } : { 'is-normal': true };
    },
    async loadActivePayload() {
      if (!this.order.id) {
        this.clearActivePayload();
        return;
      }
      this.activePayloadLoading = true;
      try {
        const data = await fetchActiveFlowWorkOrderPayload(this.order.id);
        this.activePayload = data?.payload || null;
        this.activePayloadDispatch = data?.dispatch || null;
      } catch (error) {
        this.clearActivePayload();
        ElMessage.warning(error?.message || '加载生效下发失败');
      } finally {
        this.activePayloadLoading = false;
      }
    },
    async copyActivePayload() {
      if (!this.activePayload) return;
      try {
        await navigator.clipboard.writeText(JSON.stringify(this.activePayload, null, 2));
        ElMessage.success('已复制当前生效下发 JSON');
      } catch {
        ElMessage.warning('复制失败，请手动选择文本复制');
      }
    },
    clearValidationIssues() {
      this.validationIssues = [];
    },
    notifyValidationPassed(message) {
      if (this.optionalWellWarnings.total) {
        ElMessage.warning(`${message}，但${this.optionalWellWarnings.text}`);
      } else {
        ElMessage.success(message);
      }
    },
    applyValidationResult(data) {
      const issues = Array.isArray(data?.issues) ? data.issues : [];
      if (issues.length) {
        this.validationIssues = issues;
        return;
      }
      const errors = Array.isArray(data?.errors) ? data.errors : [];
      this.validationIssues = errors.map((message) => ({ field: '', message }));
    },
    hasFieldError(field) {
      if (!field || !this.validationIssues.length) return false;
      return this.validationIssues.some(
        (item) => item.field === field || String(item.field || '').startsWith(`${field}.`),
      );
    },
    focusFirstValidationIssue() {
      const first = this.validationIssues.find((item) => item.field);
      if (!first?.field) return;
      if (first.field.startsWith('cell_plates.')) {
        const parts = first.field.split('.');
        if (parts[1] != null) this.activeCellPlate = String(parts[1]);
      }
      if (first.field.startsWith('sample_plates.')) {
        const parts = first.field.split('.');
        if (parts[1] != null) this.activeSamplePlate = String(parts[1]);
      }
      this.activeTab = 'editor';
    },
    canEdit() {
      if (this.isViewMode || this.loadError) return false;
      return !this.order.id || canEditMegaFlowWorkOrder(this.currentUserInfo);
    },
    canDispatch() {
      if (this.isViewMode) return false;
      return !this.order.id || canDispatchMegaFlowWorkOrder(this.currentUserInfo);
    },
    async loadMeta() {
      try {
        const data = await fetchFlowWorkOrderMeta();
        this.defaultSampleWells = data?.default_sample_wells || [];
        this.defaultCellColumns = data?.default_cell_columns || [];
        if (data?.data_types?.length) {
          this.dataTypeOptions = data.data_types;
        }
        if (data?.priorities?.length) {
          this.priorityOptions = data.priorities;
        }
      } catch {
        this.defaultSampleWells = [];
        this.defaultCellColumns = [];
      }
    },
    resetPausedTracking() {
      this.pausedLocalDirty = false;
      this.resumeBlocked = false;
    },
    startPausedDirtyWatch() {
      if (this.pausedDirtyUnwatch) return;
      this.pausedDirtyUnwatch = this.$watch(
        () => this.order,
        () => {
          if (this.order.status === 'paused' && !this.pausedDirtyInit) {
            this.pausedLocalDirty = true;
          }
        },
        { deep: true },
      );
    },
    stopPausedDirtyWatch() {
      this.pausedDirtyUnwatch?.();
      this.pausedDirtyUnwatch = null;
    },
    detailRouteIdentity() {
      const id = this.$route.query.id;
      const copyFrom = this.$route.query.copyFrom;
      if (id) return `id:${id}`;
      if (copyFrom) return `copy:${copyFrom}`;
      return 'new';
    },
    async loadDetail() {
      this.clearValidationIssues();
      this.clearActivePayload();
      this.loading = true;
      const routeIdentity = this.detailRouteIdentity();
      const id = this.$route.query.id;
      const copyFrom = this.$route.query.copyFrom;
      if (!id && !copyFrom) {
        this.loadError = false;
        this.order = this.normalizeOrder(createDefaultFlowWorkOrder());
        this.resetPausedTracking();
        this.loadedRouteIdentity = routeIdentity;
        this.scheduleSamplePlateSortableInit();
        this.loading = false;
        return;
      }
      this.pausedDirtyInit = true;
      try {
        const data = await fetchFlowWorkOrderDetail(id || copyFrom);
        if (copyFrom && !id) {
          this.order = this.normalizeOrder({
            ...data,
            id: null,
            order_no: '',
            status: 'draft',
            content_hash: '',
            error_message: null,
            sent_at: null,
            dispatches: [],
            has_dispatches: false,
            pause_state: '',
            display_status: '',
            display_status_label: '',
          });
        } else {
          this.order = this.normalizeOrder(data);
        }
        this.loadError = false;
        this.loadedRouteIdentity = routeIdentity;
        this.resetPausedTracking();
      } catch (error) {
        this.loadError = true;
        this.order = this.normalizeOrder(createDefaultFlowWorkOrder());
        this.resetPausedTracking();
        ElMessage.error(error?.message || '工单加载失败，请返回列表后重试');
      } finally {
        this.loading = false;
        this.$nextTick(() => {
          this.pausedDirtyInit = false;
        });
        this.scheduleSamplePlateSortableInit();
      }
    },
    normalizeOrder(data) {
      return normalizeFlowWorkOrder(data, {
        cellColumns: this.defaultCellColumns,
        sampleWells: this.defaultSampleWells,
      });
    },
    defaultSamplePlate() {
      return createDefaultSamplePlate({
        cellColumns: this.defaultCellColumns,
        sampleWells: this.defaultSampleWells,
      });
    },
    defaultColumns() {
      return createDefaultColumns({
        cellColumns: this.defaultCellColumns,
        sampleWells: this.defaultSampleWells,
      });
    },
    rememberCellBarcode(index, value) {
      if (!this.cellBarcodeFocusCache) this.cellBarcodeFocusCache = {};
      this.cellBarcodeFocusCache[index] = String(value || '').trim() || `细胞板${index + 1}`;
    },
    /** 条码变更时同步改写样本板 cell_keys，避免占位条码与真实条码对不上 */
    remapCellBarcode(index, value) {
      const from = this.cellBarcodeFocusCache?.[index];
      const to = String(value || '').trim() || `细胞板${index + 1}`;
      if (!from || from === to) return;
      const fromPrefix = `${from}|`;
      this.order.sample_plates.forEach((plate) => {
        const keys = Array.isArray(plate.cell_keys) ? plate.cell_keys : [];
        plate.cell_keys = keys.map((key) =>
          key.startsWith(fromPrefix) ? `${to}|${key.slice(fromPrefix.length)}` : key,
        );
      });
      this.pruneEmptyCellRefs();
    },
    handleCellColumnsReordered({ plateIndex, oldIndex, newIndex }) {
      const plate = this.order.cell_plates[plateIndex];
      const columnCount = plate?.columns?.length || 0;
      if (
        !columnCount
        || oldIndex < 0
        || newIndex < 0
        || oldIndex >= columnCount
        || newIndex >= columnCount
      ) {
        return;
      }
      // 列拖动等同于剪切粘贴：内容移动到新列，所有受位移影响的细胞引用也随内容改写。
      const oldColumnAtNewIndex = Array.from({ length: columnCount }, (_, index) => index + 1);
      const [movedColumn] = oldColumnAtNewIndex.splice(oldIndex, 1);
      oldColumnAtNewIndex.splice(newIndex, 0, movedColumn);
      const newColumnByOldColumn = new Map(
        oldColumnAtNewIndex.map((oldColumn, index) => [oldColumn, index + 1]),
      );
      const prefix = `${this.cellPlateBarcode(plate, plateIndex)}|`;
      this.order.sample_plates.forEach((samplePlate) => {
        const keys = Array.isArray(samplePlate.cell_keys) ? samplePlate.cell_keys : [];
        samplePlate.cell_keys = keys.map((key) => {
          if (!key.startsWith(prefix)) return key;
          const oldColumn = Number(key.slice(prefix.length));
          const newColumn = newColumnByOldColumn.get(oldColumn);
          return newColumn ? `${prefix}${newColumn}` : key;
        });
      });
      this.pruneEmptyCellRefs();
    },
    cellSpeciesSummary(plate) {
      const keys = Array.isArray(plate.cell_keys) ? plate.cell_keys : [];
      if (!keys.length) return '';
      const map = this.cellByKey;
      const tokens = [];
      keys.forEach((key) => {
        const col = map[key];
        const name = String(col?.cell_name || '').trim();
        if (!name) return;
        const token = String(col?.species || '').trim() || name;
        if (token && !tokens.includes(token)) tokens.push(token);
      });
      return tokens.join('、');
    },
    toggleCell(plate, key) {
      const keys = Array.isArray(plate.cell_keys) ? [...plate.cell_keys] : [];
      const idx = keys.indexOf(key);
      if (idx >= 0) {
        keys.splice(idx, 1);
      } else {
        keys.push(key);
      }
      plate.cell_keys = keys;
    },
    /** 清除指向「无细胞名称」列的样本板引用 */
    pruneEmptyCellRefs() {
      const named = new Set(
        Object.entries(this.cellByKey)
          .filter(([, col]) => String(col?.cell_name || '').trim())
          .map(([key]) => key),
      );
      this.order.sample_plates.forEach((plate) => {
        const keys = Array.isArray(plate.cell_keys) ? plate.cell_keys : [];
        plate.cell_keys = keys.filter((key) => named.has(key));
      });
    },
    onCellPickerShow(plate) {
      this.activeCellPickerRowKey = plate._rowKey || '';
      const selected = Array.isArray(plate.cell_keys) ? plate.cell_keys : [];
      const expanded = {};
      this.cellPickerOptions.forEach((group, index) => {
        expanded[index] = group.children.some((cell) => selected.includes(cell.value));
      });
      if (!Object.values(expanded).some(Boolean)) {
        const firstIdx = this.cellPickerOptions.findIndex((group) => group.children.length);
        if (firstIdx >= 0) expanded[firstIdx] = true;
      }
      this.cellPickerExpanded = expanded;
    },
    onCellPickerHide() {
      this.activeCellPickerRowKey = '';
    },
    isCellPlateExpanded(index) {
      return !!this.cellPickerExpanded[index];
    },
    toggleCellPlate(index) {
      this.cellPickerExpanded = {
        ...this.cellPickerExpanded,
        [index]: !this.cellPickerExpanded[index],
      };
    },
    selectSamplePlate(row, column, event) {
      if (event?.target?.closest?.('.row-drag-handle, .sample-plate-op')) return;
      const index = this.order.sample_plates.indexOf(row);
      if (index >= 0) {
        this.activeSamplePlate = String(index);
        this.$refs.samplePlateLayout?.clearWellSelection();
      }
    },
    samplePlateRowClass({ row }) {
      const index = this.order.sample_plates.indexOf(row);
      return this.activeSamplePlate === String(index) ? 'is-active-row' : '';
    },
    addSamplePlate() {
      this.order.sample_plates.push(this.defaultSamplePlate());
      this.activeSamplePlate = String(this.order.sample_plates.length - 1);
    },
    removeSamplePlate(index) {
      this.order.sample_plates.splice(index, 1);
      if (Number(this.activeSamplePlate) >= this.order.sample_plates.length) {
        this.activeSamplePlate = String(Math.max(0, this.order.sample_plates.length - 1));
      }
    },
    async initSamplePlateSortable() {
      const initToken = ++this.samplePlateSortableInitToken;
      this.destroySamplePlateSortable();
      await this.$nextTick();
      const table = this.$refs.samplePlateTable;
      if (!table) return;
      const tbody = table.$el?.querySelector('.el-table__body-wrapper tbody');
      if (!tbody) return;

      const SortableModule = await import('sortablejs/modular/sortable.complete.esm.js');
      if (initToken !== this.samplePlateSortableInitToken || !tbody.isConnected) return;
      const Sortable = SortableModule.default;
      this.samplePlateSortable = Sortable.create(tbody, {
        handle: '.row-drag-handle',
        animation: 200,
        disabled: this.fieldDisabled,
        ghostClass: 'sortable-ghost',
        onEnd: (evt) => this.handleSamplePlateDragEnd(evt),
      });
    },
    handleSamplePlateDragEnd(evt) {
      const { oldIndex, newIndex, item } = evt;
      if (oldIndex == null || newIndex == null || oldIndex === newIndex) return;
      // 撤销 SortableJS 对真实 DOM 的搬动，交回给 Vue 依据数据数组统一渲染，
      // 否则 DOM 与虚拟 DOM 顺序不一致，下次重渲染（如新增行）时会跳回旧序。
      const parent = item?.parentNode;
      if (parent) {
        const anchor =
          newIndex > oldIndex ? parent.children[oldIndex] : parent.children[oldIndex + 1];
        parent.insertBefore(item, anchor || null);
      }
      const plates = this.order.sample_plates;
      const [moved] = plates.splice(oldIndex, 1);
      plates.splice(newIndex, 0, moved);
      this.syncActiveSamplePlateAfterReorder(oldIndex, newIndex);
    },
    destroySamplePlateSortable() {
      if (this.samplePlateSortable) {
        this.samplePlateSortable.destroy();
        this.samplePlateSortable = null;
      }
    },
    scheduleSamplePlateSortableInit() {
      this.$nextTick(() => {
        this.initSamplePlateSortable();
      });
    },
    syncActiveSamplePlateAfterReorder(oldIndex, newIndex) {
      const activeIdx = Number(this.activeSamplePlate);
      if (Number.isNaN(activeIdx)) return;
      if (activeIdx === oldIndex) {
        this.activeSamplePlate = String(newIndex);
      } else if (oldIndex < activeIdx && newIndex >= activeIdx) {
        this.activeSamplePlate = String(activeIdx - 1);
      } else if (oldIndex > activeIdx && newIndex <= activeIdx) {
        this.activeSamplePlate = String(activeIdx + 1);
      }
    },
    addCellPlate() {
      this.order.cell_plates.push({ barcode: '', columns: this.defaultColumns() });
      this.activeCellPlate = String(this.order.cell_plates.length - 1);
    },
    removeCellPlate(index) {
      const plates = this.order.cell_plates;
      const oldAliasByPlate = new Map(
        plates.map((plate, plateIndex) => [plate, this.cellPlateBarcode(plate, plateIndex)]),
      );
      const [removedPlate] = plates.splice(index, 1);
      const removedAlias = oldAliasByPlate.get(removedPlate);
      const aliasRemaps = plates
        .map((plate, plateIndex) => ({
          from: oldAliasByPlate.get(plate),
          to: this.cellPlateBarcode(plate, plateIndex),
        }))
        .filter(({ from, to }) => from && from !== to);
      const survivingAliases = new Set(plates.map((plate, plateIndex) =>
        this.cellPlateBarcode(plate, plateIndex)));

      this.order.sample_plates.forEach((samplePlate) => {
        const keys = Array.isArray(samplePlate.cell_keys) ? samplePlate.cell_keys : [];
        samplePlate.cell_keys = keys.flatMap((key) => {
          const remap = aliasRemaps.find(({ from }) => key.startsWith(`${from}|`));
          if (remap) return [`${remap.to}|${key.slice(remap.from.length + 1)}`];
          if (removedAlias && !survivingAliases.has(removedAlias) && key.startsWith(`${removedAlias}|`)) {
            return [];
          }
          return [key];
        });
      });
      this.pruneEmptyCellRefs();
      if (Number(this.activeCellPlate) >= plates.length) {
        this.activeCellPlate = String(Math.max(0, plates.length - 1));
      }
    },
    addPcInfo() {
      this.pcInfos.push({
        pc_id: createLocalPcId(),
        pc_type: 'SERUM',
        pc_name: '',
        catalog_batch: '',
        source: '',
        concentration: '',
      });
    },
    removePcInfo(index) {
      const removedId = this.pcInfos[index]?.pc_id;
      this.pcInfos.splice(index, 1);
      if (!removedId) return;
      this.order.sample_plates.forEach((plate) => {
        (plate.wells || []).forEach((well) => {
          if (well.pc_id === removedId) {
            well.pc_id = null;
          }
        });
      });
    },
    buildSavePayload() {
      return buildFlowWorkOrderSavePayload(this.order);
    },
    async save() {
      if (this.loadError) return false;
      if (!String(this.order.order_no || '').trim()) {
        ElMessage.warning('请先填写订单编号');
        return false;
      }
      this.saving = true;
      try {
        const data = await saveFlowWorkOrder(this.buildSavePayload());
        this.order = this.normalizeOrder(data);
        if (!this.$route.query.id && data?.id) {
          await this.$router.replace({
            name: 'MegaFlowWorkOrderDetail',
            query: { id: data.id, mode: this.$route.query.mode || 'edit' },
          });
        }
        ElMessage.success(data?.unchanged ? '内容无变化，未更新数据库' : '保存成功');
        return true;
      } catch (error) {
        ElMessage.warning(error?.message || '保存失败');
        return false;
      } finally {
        this.saving = false;
      }
    },
    async validate() {
      if (!this.order.id) return;
      if (this.order.status === 'paused') {
        await this.validatePaused();
        return;
      }
      const saved = await this.save();
      if (!saved || !this.order.id) return;
      try {
        const data = await validateFlowWorkOrder(this.order.id, {
          expected_content_hash: this.order.content_hash || '',
        });
        if (data.item) {
          this.order = this.normalizeOrder(data.item);
        }
        if (data.valid) {
          this.clearValidationIssues();
          this.notifyValidationPassed('校验通过');
        } else {
          this.applyValidationResult(data);
          this.focusFirstValidationIssue();
        }
      } catch (error) {
        this.applyValidationResult({
          errors: [error?.message || '校验失败'],
        });
      }
    },
    async validatePaused() {
      try {
        let data = await validateFlowWorkOrder(this.order.id, {
          expected_content_hash: this.order.content_hash || '',
          payload: this.buildSavePayload(),
        });
        if (data.needs_confirm) {
          await ElMessageBox.confirm(
            data.message || '工单内容已变更，确认后将使此前有效的下发记录失效，且无法再通过「继续」恢复。',
            '确认修改',
            {
              confirmButtonText: '确认修改',
              cancelButtonText: '取消',
              type: 'warning',
            },
          );
          this.resumeBlocked = true;
          data = await validateFlowWorkOrder(this.order.id, {
            expected_content_hash: this.order.content_hash || '',
            payload: this.buildSavePayload(),
            confirm_revoke: true,
          });
        }
        if (data.item) {
          this.pausedDirtyInit = true;
          this.order = this.normalizeOrder(data.item);
          this.resetPausedTracking();
          this.$nextTick(() => {
            this.pausedDirtyInit = false;
          });
        }
        if (!data.valid) {
          this.applyValidationResult(data);
          this.focusFirstValidationIssue();
          return;
        }
        this.clearValidationIssues();
        if (data.saved) {
          this.notifyValidationPassed('校验通过，修改已保存，此前下发记录已失效');
          return;
        }
        if (data.can_resume) {
          this.notifyValidationPassed('校验通过，内容未变化，可点击继续恢复发送状态');
          return;
        }
        this.notifyValidationPassed('校验通过');
      } catch (error) {
        if (error !== 'cancel' && error?.message !== 'cancel') {
          this.applyValidationResult({
            errors: [error?.message || '校验失败'],
          });
        }
      }
    },
    async dispatchOrder() {
      if (!this.order.id || this.actionLoading) return;
      this.actionLoading = true;
      try {
        if (this.optionalWellWarnings.total) {
          await ElMessageBox.confirm(
            `当前仍有${this.optionalWellWarnings.text}。这些内容为可选项，确认继续发送？`,
            '可选内容未填写',
            {
              confirmButtonText: '继续发送',
              cancelButtonText: '返回补充',
              type: 'warning',
            },
          );
        }
        const data = await dispatchFlowWorkOrder(this.order.id);
        this.order = this.normalizeOrder(data);
        if (this.activeTab === 'payload') {
          await this.loadActivePayload();
        } else {
          this.activeTab = 'payload';
        }
        ElMessage.success('已发送');
      } catch (error) {
        if (error !== 'cancel' && error?.message !== 'cancel') {
          ElMessage.warning(error?.message || '发送失败，请确认已校验通过');
        }
      } finally {
        this.actionLoading = false;
      }
    },
    async confirmExecution() {
      if (!this.order.id) return;
      try {
        await ElMessageBox.confirm(
          '确认设备端已开始执行该工单？\n确认后下发记录将变为执行中。',
          '确认执行',
          {
            confirmButtonText: '确认执行',
            cancelButtonText: '取消',
            type: 'info',
          },
        );
        const data = await confirmFlowWorkOrderExecution(this.order.id);
        this.order = this.normalizeOrder(data);
        ElMessage.success('已确认执行');
      } catch (error) {
        if (error !== 'cancel' && error?.message !== 'cancel') {
          ElMessage.warning(error?.message || '确认执行失败');
        }
      }
    },
    async pauseOrder() {
      if (!this.order.id) return;
      try {
        await ElMessageBox.confirm(
          '确认停止该工单？\n停止后可编辑，内容未实质修改时可恢复继续。',
          '停止确认',
          {
            confirmButtonText: '停止',
            cancelButtonText: '取消',
            type: 'warning',
          },
        );
        const data = await pauseFlowWorkOrder(this.order.id);
        this.pausedDirtyInit = true;
        this.order = this.normalizeOrder(data);
        this.resetPausedTracking();
        this.$nextTick(() => {
          this.pausedDirtyInit = false;
        });
        ElMessage.success('已请求暂停，等待设备确认');
      } catch (error) {
        if (error !== 'cancel' && error?.message !== 'cancel') {
          ElMessage.warning(error?.message || '停止失败');
        }
      }
    },
    async acknowledgePause() {
      if (!this.order.id || this.actionLoading) return;
      this.actionLoading = true;
      try {
        const data = await acknowledgePauseFlowWorkOrder(this.order.id);
        this.pausedDirtyInit = true;
        this.order = this.normalizeOrder(data);
        this.resetPausedTracking();
        this.$nextTick(() => {
          this.pausedDirtyInit = false;
        });
        ElMessage.success('设备已确认暂停，可编辑或继续');
      } catch (error) {
        ElMessage.warning(error?.message || '确认设备暂停失败');
      } finally {
        this.actionLoading = false;
      }
    },
    async acknowledgeResume() {
      if (!this.order.id || this.actionLoading) return;
      this.actionLoading = true;
      try {
        const data = await acknowledgeResumeFlowWorkOrder(this.order.id);
        this.order = this.normalizeOrder(data);
        this.resetPausedTracking();
        ElMessage.success(
          data?.status === 'running' ? '设备已恢复，工单继续执行' : '设备已恢复，工单回到已发送状态',
        );
      } catch (error) {
        ElMessage.warning(error?.message || '确认设备恢复失败');
      } finally {
        this.actionLoading = false;
      }
    },
    async resumeOrder() {
      if (!this.order.id || this.actionLoading) return;
      this.actionLoading = true;
      try {
        const data = await resumeFlowWorkOrder(this.order.id);
        this.pausedDirtyInit = true;
        this.order = this.normalizeOrder(data);
        this.$nextTick(() => {
          this.pausedDirtyInit = false;
        });
        ElMessage.success('已请求恢复，等待设备确认');
      } catch (error) {
        ElMessage.warning(error?.message || '无法继续，请先校验确认修改');
      } finally {
        this.actionLoading = false;
      }
    },
    async completeOrder() {
      if (!this.order.id) return;
      try {
        await ElMessageBox.confirm('确认该工单已经执行完成？', '完成确认', {
          confirmButtonText: '确认完成',
          cancelButtonText: '取消',
          type: 'success',
        });
        const data = await completeFlowWorkOrder(this.order.id);
        this.order = this.normalizeOrder(data);
        ElMessage.success('工单已完成');
      } catch (error) {
        if (error !== 'cancel' && error?.message !== 'cancel') {
          ElMessage.warning(error?.message || '完成操作失败');
        }
      }
    },
    async failOrder() {
      if (!this.order.id) return;
      try {
        const { value } = await ElMessageBox.prompt(
          '可填写设备返回的失败原因',
          '执行失败确认',
          {
            confirmButtonText: '确认失败',
            cancelButtonText: '取消',
            inputPlaceholder: '失败原因（可选）',
            type: 'warning',
          },
        );
        const data = await failFlowWorkOrder(this.order.id, value || '');
        this.order = this.normalizeOrder(data);
        ElMessage.success('已标记为执行失败');
      } catch (error) {
        if (error !== 'cancel' && error?.message !== 'cancel') {
          ElMessage.warning(error?.message || '标记执行失败失败');
        }
      }
    },
    async deleteOrder() {
      if (!this.order.id) return;
      const label = this.order.order_no || `#${this.order.id}`;
      try {
        await ElMessageBox.confirm(`确认删除工单 ${label}？删除后不可恢复。`, '删除确认', {
          confirmButtonText: '删除',
          cancelButtonText: '取消',
          type: 'warning',
        });
        await deleteFlowWorkOrder(this.order.id);
        ElMessage.success('已删除');
        this.goBack();
      } catch (error) {
        if (error !== 'cancel' && error?.message !== 'cancel') {
          ElMessage.warning(error?.message || '删除失败');
        }
      }
    },
    async voidOrder() {
      if (!this.order.id) return;
      const label = this.order.order_no || `#${this.order.id}`;
      try {
        await ElMessageBox.confirm(
          `确认作废工单 ${label}？\n作废后不可再编辑或发送，历史下发记录仍保留。`,
          '作废确认',
          {
            confirmButtonText: '作废',
            cancelButtonText: '取消',
            type: 'warning',
          },
        );
        const data = await cancelFlowWorkOrder(this.order.id);
        this.order = this.normalizeOrder(data);
        ElMessage.success('已作废');
      } catch (error) {
        if (error !== 'cancel' && error?.message !== 'cancel') {
          ElMessage.warning(error?.message || '作废失败');
        }
      }
    },
    dispatchChipLabel(item) {
      return buildDispatchChipLabel(item);
    },
    statusTagType(displayStatus) {
      return orderStatusTagType(displayStatus);
    },
    formatJson(value) {
      if (!value) return '当前没有生效中的下发记录';
      return JSON.stringify(value, null, 2);
    },
    goBack() {
      this.$router.push({ name: 'MegaFlowWorkOrderList' });
    },
  },
};
</script>

<style lang="scss" scoped>
$primary: #409eff;
$title-color: #303133;
$label-color: #606266;
$muted-color: #909399;
$border-color: #e4e7ed;
$radius: 8px;

.flow-order-detail {
  padding: 16px;
  font-size: 14px;
  color: $title-color;
}

.detail-loading {
  min-height: 320px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: $radius;
}

/* 顶部 */
.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding: 14px 18px;
  margin-bottom: 12px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: $radius;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.back-btn {
  font-size: 14px;
  color: $label-color;
}

.title-block {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  line-height: 1.3;
}

.page-subtitle {
  font-size: 12px;
  color: $muted-color;
}

.header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.preview-banner {
  padding: 10px 14px;
  margin-bottom: 12px;
  font-size: 13px;
  color: #8a5a00;
  background: #fff7e6;
  border: 1px solid #ffd591;
  border-radius: $radius;
}

.validation-banner {
  padding: 12px 14px;
  margin-bottom: 12px;
  font-size: 13px;
  color: #a8071a;
  background: #fff1f0;
  border: 1px solid #ffa39e;
  border-radius: $radius;
}

.optional-warning-banner {
  padding: 10px 14px;
  margin-bottom: 12px;
  font-size: 13px;
  color: #8a5a00;
  background: #fff7e6;
  border: 1px solid #ffd591;
  border-radius: $radius;
}

.validation-banner-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
}

.validation-banner-list {
  margin: 0;
  padding-left: 18px;
  line-height: 1.6;
}

.is-invalid :deep(.el-input__wrapper),
.is-invalid-control :deep(.el-input__wrapper),
.is-invalid-control.el-select :deep(.el-select__wrapper),
.flow-editor-panel :deep(.is-invalid-control .el-input__wrapper),
.flow-editor-panel :deep(.is-invalid-control.el-select .el-select__wrapper) {
  box-shadow: 0 0 0 1px #f56c6c inset !important;
}

.cell-select-trigger.is-invalid-control {
  box-shadow: 0 0 0 1px #f56c6c inset;
  background: #fff;
}

/* 通用面板 */
.panel {
  padding: 14px 16px;
  margin-bottom: 12px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: $radius;
  box-shadow: 0 1px 2px rgb(0 0 0 / 4%);
}

.panel-head,
.flow-editor-panel :deep(.panel-head) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.panel-head-left,
.flow-editor-panel :deep(.panel-head-left) {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.flow-editor-panel :deep(.panel-head-right) {
  display: flex;
  align-items: center;
  gap: 10px;
}

.head-icon,
.flow-editor-panel :deep(.head-icon) {
  font-size: 16px;
  color: $primary;
}

.panel-title,
.flow-editor-panel :deep(.panel-title) {
  font-size: 15px;
  font-weight: 700;
  color: $title-color;
}

.panel-hint,
.flow-editor-panel :deep(.panel-hint) {
  font-size: 12px;
  color: $muted-color;
}

.field-label,
.flow-editor-panel :deep(.field-label) {
  font-size: 13px;
  color: $label-color;
  white-space: nowrap;
}

.empty-hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: $muted-color;
}

/* 基础信息 */
.base-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px 16px;
  margin-top: 12px;
}

.base-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.base-field .field-control {
  width: 100%;
}

.base-field--wide {
  grid-column: 1 / -1;
}

:deep(.drag-cell .cell) {
  padding: 0;
}

.row-drag-handle,
.flow-editor-panel :deep(.row-drag-handle) {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 32px;
  font-size: 12px;
  font-weight: 600;
  color: $label-color;
  cursor: grab;
  user-select: none;
  transition: background-color 0.15s;

  &:hover {
    background: #f0f5ff;
  }

  &:active {
    cursor: grabbing;
  }

  &.is-disabled {
    cursor: not-allowed;
    color: $muted-color;

    &:hover {
      background: transparent;
    }
  }
}

:deep(.sortable-ghost) {
  opacity: 0.55;
  background: #f5f7fa;
}

.timeline-strip {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-top: 10px;
  margin-top: 12px;
  border-top: 1px solid #f0f2f5;
}

.timeline-label {
  flex-shrink: 0;
  font-size: 12px;
  color: $muted-color;
}

.timeline-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.timeline-chip {
  padding: 2px 10px;
  font-size: 12px;
  color: #475569;
  background: #f5f7fa;
  border: 1px solid #e5e7eb;
  border-radius: 999px;

  &.is-empty {
    color: $muted-color;
  }
}

/* 编辑区左右布局 */
.editor-layout {
  display: grid;
  grid-template-columns: minmax(0, 0.92fr) minmax(0, 1.08fr);
  gap: 14px;
  align-items: start;
}

.editor-col {
  min-width: 0;
}

/* 表格 */
.info-table {
  width: 100%;

  :deep(.el-table__cell) {
    padding: 4px 0;
  }

  :deep(.cell) {
    padding: 0 6px;
    line-height: 1.3;
  }

  :deep(th.el-table__cell) {
    font-size: 12px;
    font-weight: 600;
    color: $label-color;
    background: #f5f7fa;
  }

  :deep(.el-input__wrapper),
  :deep(.el-select__wrapper) {
    box-shadow: none;
    background: transparent;
  }

  :deep(.el-input__wrapper.is-focus),
  :deep(.el-input__wrapper:hover),
  :deep(.el-select__wrapper:hover) {
    box-shadow: 0 0 0 1px $primary inset;
    background: #fff;
  }

  :deep(.el-table__row.is-active-row > td.el-table__cell) {
    background: #ecf5ff;
  }
}

.cell-select-trigger {
  display: flex;
  align-items: center;
  gap: 4px;
  width: 100%;
  min-height: 24px;
  padding: 1px 8px;
  font-size: 12px;
  line-height: 1.3;
  color: $label-color;
  background: transparent;
  border: none;
  border-radius: 4px;
  box-shadow: none;
  transition: box-shadow 0.15s, background-color 0.15s;

  &:hover:not(.is-disabled),
  &.is-open {
    box-shadow: 0 0 0 1px $primary inset;
    background: #fff;
  }

  &.is-disabled {
    color: $muted-color;
    cursor: not-allowed;
    background: transparent;
  }
}

.cell-select-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cell-select-placeholder {
  flex: 1;
  color: #a8abb2;
}

.cell-select-arrow {
  flex-shrink: 0;
  font-size: 12px;
  color: $muted-color;
}

/* 可视化面板 */
.viz-panel {
  background: #fff;
}

/* 细胞板列视图（横向泳道） */
.lane-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.cell-lane {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px;
  background: #f8fafc;
  border: 1px solid #eceff4;
  border-left: 3px solid #dfe4ec;
  border-radius: 6px;

  &.is-filled {
    background: #f4f9ff;
    border-left-color: $primary;
  }
}

.lane-wells {
  display: flex;
  gap: 2px;
  flex-shrink: 0;
}

.lane-well {
  width: 7px;
  height: 7px;
  background: #dfe4ec;
  border-radius: 50%;

  .is-filled & {
    background: $primary;
  }
}

.lane-no {
  flex-shrink: 0;
  width: 52px;
  font-size: 12px;
  font-weight: 600;
  color: $label-color;
}

.lane-body {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.lane-name {
  overflow: hidden;
  font-size: 13px;
  font-weight: 600;
  color: $title-color;
  text-overflow: ellipsis;
  white-space: nowrap;

  .cell-lane:not(.is-filled) & {
    font-weight: 400;
    color: $muted-color;
  }
}

.lane-meta {
  font-size: 11px;
  color: $muted-color;
}

.plating-toolbar,
.plating-toolbar-left,
.plating-nav-head,
.nav-sample-line {
  display: flex;
  align-items: center;
}

.plating-toolbar {
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.plating-toolbar-left {
  gap: 10px;
  min-width: 0;
  flex-wrap: wrap;
}

.plating-title {
  font-size: 15px;
  font-weight: 600;
  color: $title-color;
}

.plating-stats {
  padding: 2px 8px;
  font-size: 12px;
  color: $label-color;
  background: #f2f5f9;
  border-radius: 999px;
}

.plating-hint,
.plating-nav-hint,
.plating-nav-label {
  font-size: 12px;
  color: $muted-color;
}

.plating-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}

.plating-main {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
  max-height: calc(100vh - 210px);
  overflow: auto;
  padding-right: 4px;
}

.plating-plate-wrap {
  scroll-margin-top: 12px;

  .plating-plate.panel {
    margin-bottom: 0;
  }

  &.is-plating-focus .plating-plate {
    border-color: #b3d8ff;
  }
}

.plating-nav {
  position: sticky;
  top: 0;
  padding: 12px;
  margin-bottom: 0;
  max-height: calc(100vh - 210px);
  overflow: auto;
}

.plating-nav-head {
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
  align-items: baseline;
}

.plating-nav-title {
  font-size: 14px;
  font-weight: 600;
  color: $title-color;
}

.plating-nav-group + .plating-nav-group {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid #ebeef5;
}

.plating-nav-label {
  margin-bottom: 8px;
}

/* 样本板：上方 S-1 + 种属，下方孔板缩略图 */
.plating-nav-sample-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 8px;
}

.nav-sample-tile {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
  padding: 8px;
  text-align: left;
  cursor: pointer;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 6px;

  &:hover {
    border-color: #d9e4f0;
  }

  &.is-active {
    background: #f5f9ff;
    border-color: #b3d8ff;
  }
}

.nav-mini-grid--sample {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 1px;
  width: 100%;
}

.nav-mini-well {
  display: block;
  aspect-ratio: 1;
  border-radius: 1px;

  &.well-sample { background: #cfe2ff; }
  &.well-pc { background: #ffd8a8; }
  &.well-nc { background: #d0d7ff; }
  &.well-iso { background: #b7f0c8; }
  &.well-tag { background: #dcc9ff; }
  &.well-blank { background: #e8ebf0; }
}

.nav-sample-line {
  justify-content: space-between;
  gap: 8px;
  min-width: 0;
}

.nav-id {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 700;
  color: $title-color;
}

.nav-species {
  overflow: hidden;
  font-size: 12px;
  color: $label-color;
  text-align: right;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.nav-mini-grid--cell {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 2px;
  width: 100%;
  height: 18px;
}

.nav-mini-col {
  display: block;
  height: 100%;
  background: #e8ebf0;
  border-radius: 999px;

  &.is-normal {
    background: #7dd3fc;
  }

  &.is-tumor {
    background:rgb(255, 156, 75);
  }
}

/* JSON */
.json-layout {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.json-layout--single {
  grid-template-columns: minmax(0, 1fr);
}

.json-panel {
  min-height: 360px;
  max-height: 600px;
  padding: 12px;
  margin: 0;
  overflow: auto;
  font-size: 12px;
  line-height: 1.5;
  color: #d1d5db;
  background: #111827;
  border-radius: 6px;
}

@media (max-width: 1180px) {
  .editor-layout,
  .json-layout,
  .plating-layout {
    grid-template-columns: minmax(0, 1fr);
  }

  .plating-main,
  .plating-nav {
    max-height: none;
  }

  .base-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .base-field--wide {
    grid-column: span 2;
  }
}
</style>

<style lang="scss">
/* 检测细胞选择器：popover 内容 teleport 到 body，需非 scoped 样式 */
.cell-picker-popper.el-popover.el-popper {
  padding: 0;
}

.cell-picker {
  max-height: 300px;
  overflow-y: auto;
  font-size: 13px;
  color: #606266;
}

/* 细胞板：一级，做成带底色的表头行 */
.cell-picker-group-head {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 34px;
  padding: 0 12px;
  color: #303133;
  cursor: pointer;
  background: #f5f7fa;
  border-top: 1px solid #ebeef5;

  &:hover {
    background: #eef1f6;
  }
}

.cell-picker-group:first-child .cell-picker-group-head {
  border-top: none;
}

.cell-picker-group-arrow {
  flex-shrink: 0;
  font-size: 12px;
  color: #909399;
  transition: transform 0.2s;
}

.cell-picker-group.is-open .cell-picker-group-arrow {
  transform: rotate(90deg);
}

.cell-picker-group-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cell-picker-group-count {
  flex-shrink: 0;
  font-size: 12px;
  color: #409eff;

  &::before {
    content: '已选 ';
    color: #a8abb2;
  }
}

/* 细胞：二级，缩进 + 左侧引导线 */
.cell-picker-group-body {
  padding: 2px 0;
}

.cell-picker-option {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  height: 32px;
  padding: 0 12px 0 30px;
  cursor: pointer;

  &::before {
    position: absolute;
    left: 17px;
    width: 1px;
    height: 32px;
    content: '';
    background: #ebeef5;
  }

  &:hover {
    background: #f5f7fa;
  }

  &.is-selected {
    color: #409eff;
    background: #ecf5ff;
  }
}

.cell-picker-option-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cell-picker-option-col {
  flex-shrink: 0;
  padding: 0 6px;
  font-size: 12px;
  line-height: 17px;
  color: #7a8699;
  background: #f2f4f7;
  border-radius: 4px;
}

.cell-picker-option.is-selected .cell-picker-option-col {
  color: #409eff;
  background: #d9ecff;
}

.cell-picker-option-check {
  flex-shrink: 0;
  font-size: 14px;
  color: #409eff;
}

.cell-picker-empty {
  padding: 20px 12px;
  color: #a8abb2;
  text-align: center;
}
</style>
