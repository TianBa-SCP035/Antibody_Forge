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
          :disabled="!canDispatch()"
          @click="dispatchOrder"
        >
          发送
        </el-button>
        <el-button
          v-if="showConfirmExecutionButton"
          type="success"
          plain
          :disabled="!canEdit()"
          @click="confirmExecution"
        >
          确认执行
        </el-button>
        <el-button
          v-if="showCompleteButton"
          type="success"
          plain
          :disabled="!canEdit()"
          @click="completeOrder"
        >
          完成
        </el-button>
        <el-button
          v-if="showFailButton"
          type="danger"
          plain
          :disabled="!canEdit()"
          @click="failOrder"
        >
          执行失败
        </el-button>
        <el-button
          v-if="showPauseAckButton"
          type="warning"
          plain
          :disabled="!canEdit()"
          @click="acknowledgePause"
        >
          设备已暂停
        </el-button>
        <el-button
          v-if="showResumeAckButton"
          type="primary"
          plain
          :disabled="!canEdit()"
          @click="acknowledgeResume"
        >
          设备已恢复
        </el-button>
        <el-button
          v-if="showPauseButton"
          type="warning"
          plain
          :disabled="!canEdit()"
          @click="pauseOrder"
        >
          停止
        </el-button>
        <el-button
          v-if="showResumeButton"
          type="primary"
          plain
          :disabled="!canEdit()"
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

            <!-- 细胞板信息 -->
            <section class="panel">
              <div class="panel-head">
                <div class="panel-head-left">
                  <el-icon class="head-icon"><Menu /></el-icon>
                  <span class="panel-title">细胞板信息</span>
                  <span class="panel-hint">每块细胞板按 12 列维护，一列一份细胞</span>
                </div>
                <div class="panel-head-right">
                  <el-checkbox v-model="showExtraCellFields" size="small">更多字段</el-checkbox>
                  <el-button size="small" :disabled="fieldDisabled" @click="addCellPlate">
                    <el-icon><Plus /></el-icon>新增细胞板
                  </el-button>
                </div>
              </div>
              <el-tabs v-model="activeCellPlate" type="card" class="inner-tabs">
                <el-tab-pane
                  v-for="(plate, index) in order.cell_plates"
                  :key="'cell-tab-' + index"
                  :name="String(index)"
                >
                  <template #label>
                    <span class="tab-label">
                      细胞板-{{ index + 1 }}
                      <el-icon
                        v-if="order.cell_plates.length > 1 && !fieldDisabled"
                        class="tab-close"
                        @click.stop="removeCellPlate(index)"
                      ><Close /></el-icon>
                    </span>
                  </template>
                  <div class="cell-plate-barcode">
                    <span class="field-label">细胞板条码</span>
                    <el-input
                      v-model="plate.barcode"
                      size="small"
                      :disabled="fieldDisabled"
                      :class="{ 'is-invalid-control': hasFieldError(`cell_plates.${index}.barcode`) }"
                      placeholder="扫描/输入细胞板条码"
                      @focus="rememberCellBarcode(index, plate.barcode)"
                      @change="remapCellBarcode(index, plate.barcode)"
                    />
                  </div>
                  <el-table
                    ref="cellColumnsTable"
                    :data="plate.columns"
                    border
                    size="small"
                    class="info-table cell-columns-table"
                    row-key="column_no"
                  >
                    <el-table-column label="列" width="48" align="center" class-name="drag-cell">
                      <template #default="{ row }">
                        <div
                          class="row-drag-handle"
                          :class="{ 'is-disabled': fieldDisabled }"
                          title="拖动调整位置"
                          @click.stop
                        >
                          {{ row.column_no }}
                        </div>
                      </template>
                    </el-table-column>
                    <el-table-column label="类型" min-width="80">
                      <template #default="{ row }">
                        <el-select
                          v-model="row.cell_type"
                          size="small"
                          :disabled="fieldDisabled"
                          :class="{
                            'is-invalid-control': hasFieldError(
                              `cell_plates.${index}.columns.${row.column_no}.cell_type`,
                            ),
                          }"
                        >
                          <el-option v-for="t in cellTypeOptions" :key="t" :label="t" :value="t" />
                        </el-select>
                      </template>
                    </el-table-column>
                    <el-table-column label="细胞名称" min-width="150">
                      <template #default="{ row }">
                        <el-input
                          v-model="row.cell_name"
                          size="small"
                          :disabled="fieldDisabled"
                          :class="{
                            'is-invalid-control': hasFieldError(
                              `cell_plates.${index}.columns.${row.column_no}.cell_name`,
                            ),
                          }"
                          placeholder="细胞名称"
                        />
                      </template>
                    </el-table-column>
                    <el-table-column label="种属" min-width="70">
                      <template #default="{ row }">
                        <el-select v-model="row.species" size="small" clearable placeholder="" :disabled="fieldDisabled">
                          <el-option v-for="s in speciesOptions" :key="s" :label="s" :value="s" />
                        </el-select>
                      </template>
                    </el-table-column>
                    <el-table-column label="批次" min-width="80">
                      <template #default="{ row }">
                        <el-input v-model="row.batch" size="small" :disabled="fieldDisabled" />
                      </template>
                    </el-table-column>
                    <el-table-column label="代次" min-width="80">
                      <template #default="{ row }">
                        <el-input v-model="row.generation" size="small" :disabled="fieldDisabled" />
                      </template>
                    </el-table-column>
                    <el-table-column label="细胞量" min-width="80">
                      <template #default="{ row }">
                        <el-input v-model="row.cell_count" size="small" :disabled="fieldDisabled" />
                      </template>
                    </el-table-column>
                    <template v-if="showExtraCellFields">
                      <el-table-column label="货号" min-width="80">
                        <template #default="{ row }">
                          <el-input v-model="row.catalog_no" size="small" :disabled="fieldDisabled" />
                        </template>
                      </el-table-column>
                      <el-table-column label="来源" min-width="80">
                        <template #default="{ row }">
                          <el-input v-model="row.source" size="small" :disabled="fieldDisabled" />
                        </template>
                      </el-table-column>
                    </template>
                  </el-table>
                </el-tab-pane>
              </el-tabs>
            </section>

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
            <!-- 样本板布局 -->
            <section class="panel viz-panel">
              <div class="panel-head">
                <div class="panel-head-left">
                  <el-icon class="head-icon"><Files /></el-icon>
                  <span class="panel-title">样本板布局</span>
                </div>
                <PlateTabSwitch
                  v-model="activeSamplePlate"
                  :count="order.sample_plates.length"
                  prefix="样本板"
                />
              </div>

              <div class="plate-current-bar">
                <span class="current-code">{{ selectedSamplePlate.barcode || `样本板 ${Number(activeSamplePlate) + 1}` }}</span>
                <div class="legend">
                  <span v-for="t in wellTypeCycle" :key="'lg-' + t" class="legend-item">
                    <i class="legend-dot" :class="'well-' + t.toLowerCase()"></i>{{ wellTypeLabel(t) }}
                  </span>
                </div>
              </div>

              <!-- 孔位编辑条：未选中时回退 A01；选中后批量编辑 -->
              <div class="well-editor">
                <span class="well-editor-no">{{ editorWellLabel }}</span>
                <el-select
                  v-model="wellDraft.content_type"
                  size="small"
                  class="well-type-select"
                  :disabled="fieldDisabled || wellDragActive"
                  :placeholder="wellDraft.content_type ? undefined : '多种类型'"
                  @change="applyWellDraft"
                >
                  <el-option v-for="t in wellTypeCycle" :key="'wt-' + t" :label="wellTypeLabel(t)" :value="t" />
                </el-select>
                <el-select
                  v-if="isPcRefType(wellDraft.content_type)"
                  v-model="wellDraft.pc_id"
                  size="small"
                  clearable
                  filterable
                  class="well-value-input"
                  :disabled="fieldDisabled || wellDragActive"
                  placeholder="选择 PC"
                  @change="applyWellDraft"
                >
                  <el-option
                    v-for="pc in pcInfosForWellType(wellDraft.content_type)"
                    :key="pc.pc_id"
                    :label="pc.pc_name || '未命名'"
                    :value="pc.pc_id"
                  />
                </el-select>
                <el-input
                  v-else-if="isSampleType(wellDraft.content_type)"
                  v-model="wellDraft.sample_code"
                  size="small"
                  class="well-value-input"
                  :disabled="fieldDisabled || wellDragActive"
                  placeholder="样本编码（批量同步）"
                  @change="applyWellDraft"
                />
                <span v-else-if="wellDraft.content_type" class="well-editor-static">
                  {{ wellTypeLabel(wellDraft.content_type) }} 孔无需编码
                </span>
                <span class="well-editor-tip">提示：拖拽划选；右键批量切换类型</span>
              </div>

              <div class="plate-grid-wrap">
                <table class="plate-grid">
                  <thead>
                    <tr>
                      <th class="corner"></th>
                      <th v-for="col in 12" :key="'col-' + col">{{ col }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="rowLabel in plateRows" :key="'row-' + rowLabel">
                      <th class="row-head">{{ rowLabel }}</th>
                      <td
                        v-for="well in rowWells(selectedSamplePlate, rowLabel)"
                        :key="well.well_no"
                        class="well-cell"
                        :class="[
                          'well-' + String(well.content_type || 'sample').toLowerCase(),
                          {
                            'is-selected': selectedWellSet.has(well.well_no),
                            'is-drag-preview': wellDragPreviewSet.has(well.well_no),
                          },
                        ]"
                        :title="wellTooltip(well)"
                        @mousedown.prevent="onWellMouseDown(well, $event)"
                        @mouseenter="onWellMouseEnter(well)"
                        @contextmenu.prevent="cycleWellType(well)"
                      >
                        <span class="well-text">{{ wellCellText(well) }}</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>

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

      <el-tab-pane label="Payload" name="payload">
        <div class="json-layout json-layout--single">
          <section class="panel">
            <div class="panel-head">
              <span class="panel-title">下发 Payload</span>
              <span v-if="latestDispatch" class="panel-hint">{{ latestDispatch.dispatch_id }} · {{ latestDispatch.sent_at }}</span>
            </div>
            <pre class="json-panel">{{ formatJson(latestDispatch?.payload) }}</pre>
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
  Close,
  Delete,
  Files,
  Grid,
  Menu,
  Plus,
} from '@element-plus/icons-vue';
import {
  ElButton,
  ElCheckbox,
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
import PlateTabSwitch from './PlateTabSwitch.vue';

const PLATE_ROWS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'];
const SECONDARY_ANTIBODY_OPTIONS = ['人', '猴', '鼠', '狗'];
const SPECIES_OPTIONS = ['人', '猴', '鼠', '狗', '猫', '空白'];
const CELL_TYPE_OPTIONS = ['正常', '肿瘤'];
const WELL_TYPE_CYCLE = ['SAMPLE', 'PC', 'NC', 'ISO', 'TAG', 'BLANK'];
const WELL_PC_REF_TYPES = ['PC', 'ISO', 'TAG'];
const PC_INFO_TYPE_OPTIONS = ['SERUM', 'ISO', 'TAG'];
const WELL_TYPE_LABELS = {
  SAMPLE: '样本',
  PC: 'PC',
  NC: 'NC',
  ISO: 'ISO',
  TAG: 'TAG',
  BLANK: '空孔',
};
const EDITABLE_STATUSES = ['draft', 'validated', 'failed', 'execution_failed'];

function wellNo(row, col) {
  return `${row}${String(col).padStart(2, '0')}`;
}

function parseWellNo(no) {
  const match = String(no || '').match(/^([A-H])(\d{1,2})$/i);
  if (!match) return null;
  const rowIndex = PLATE_ROWS.indexOf(match[1].toUpperCase());
  const col = Number.parseInt(match[2], 10);
  if (rowIndex < 0 || col < 1 || col > 12) return null;
  return { rowIndex, col };
}

function wellsInRect(startNo, endNo) {
  const start = parseWellNo(startNo);
  const end = parseWellNo(endNo);
  if (!start || !end) return [];
  const minRow = Math.min(start.rowIndex, end.rowIndex);
  const maxRow = Math.max(start.rowIndex, end.rowIndex);
  const minCol = Math.min(start.col, end.col);
  const maxCol = Math.max(start.col, end.col);
  const result = [];
  for (let rowIndex = minRow; rowIndex <= maxRow; rowIndex += 1) {
    for (let col = minCol; col <= maxCol; col += 1) {
      result.push(wellNo(PLATE_ROWS[rowIndex], col));
    }
  }
  return result;
}

function formatWellSelectionLabel(nos) {
  if (!nos.length) return '';
  if (nos.length === 1) return nos[0];
  const parsed = nos
    .map((no) => {
      const pos = parseWellNo(no);
      return pos ? { no, ...pos } : null;
    })
    .filter(Boolean);
  if (parsed.length !== nos.length) return `已选 ${nos.length} 孔`;
  parsed.sort((a, b) => a.rowIndex - b.rowIndex || a.col - b.col);
  const first = parsed[0];
  const last = parsed[parsed.length - 1];
  const minRow = first.rowIndex;
  const maxRow = last.rowIndex;
  const minCol = first.col;
  const maxCol = last.col;
  const expectedCount = (maxRow - minRow + 1) * (maxCol - minCol + 1);
  if (parsed.length === expectedCount) {
    const startLabel = wellNo(PLATE_ROWS[minRow], minCol);
    const endLabel = wellNo(PLATE_ROWS[maxRow], maxCol);
    return startLabel === endLabel ? startLabel : `${startLabel}–${endLabel}`;
  }
  return `已选 ${nos.length} 孔`;
}

function wellPcInfoType(wellType) {
  const type = String(wellType || '').toUpperCase();
  if (type === 'PC') return 'SERUM';
  if (type === 'ISO' || type === 'TAG') return type;
  return '';
}

let samplePlateRowSeed = 0;
let localPcIdSeed = 0;

function createSamplePlateRowKey() {
  samplePlateRowSeed += 1;
  return `sp-${samplePlateRowSeed}`;
}

function createLocalPcId() {
  localPcIdSeed += 1;
  return `tmp-${localPcIdSeed}`;
}

function defaultOrder() {
  return {
    id: null,
    order_no: '',
    order_name: '',
    data_type: 'TITER',
    priority: 'normal',
    status: 'draft',
    base_info: { order_name: '', remark: '', pc_infos: [] },
    sample_plates: [],
    cell_plates: [],
    dispatches: [],
    content_hash: '',
  };
}

export default {
  name: 'MegaFlowWorkOrderDetail',
  components: {
    ArrowDown,
    ArrowLeft,
    ArrowRight,
    Check,
    CircleCheck,
    Close,
    Delete,
    ElButton,
    ElCheckbox,
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
    Files,
    Grid,
    Menu,
    Plus,
    PlateTabSwitch,
  },
  setup() {
    const userStore = useUserStore();
    return { userStore };
  },
  data() {
    return {
      loading: true,
      loadError: false,
      saving: false,
      activeTab: 'editor',
      activeSamplePlate: '0',
      activeCellPlate: '0',
      cellPickerExpanded: {},
      activeCellPickerRowKey: '',
      selectedWellNos: [],
      wellDraft: {
        content_type: '',
        pc_id: null,
        sample_code: '',
      },
      wellDragActive: false,
      wellDragStart: '',
      wellDragEnd: '',
      wellClickToggle: false,
      wellDragFrozenLabel: null,
      showExtraCellFields: false,
      order: defaultOrder(),
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
      wellTypeCycle: WELL_TYPE_CYCLE,
      plateRows: PLATE_ROWS,
      samplePlateSortable: null,
      cellColumnsSortable: null,
      validationIssues: [],
      cellBarcodeFocusCache: {},
      pausedLocalDirty: false,
      pausedDirtyInit: false,
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
      return !this.isViewMode && this.order.id && ['sent', 'running'].includes(this.order.status);
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
    /** 当前样本板已选孔位对象列表 */
    selectedWells() {
      if (!this.selectedWellNos.length) return [];
      const selected = this.selectedWellSet;
      return this.normalizedWells(this.selectedSamplePlate).filter((well) => selected.has(well.well_no));
    },
    selectedWellSet() {
      return new Set(this.selectedWellNos);
    },
    /** 拖拽预览孔位集合 */
    wellDragPreviewSet() {
      if (!this.wellDragActive || !this.wellDragStart) return new Set();
      return new Set(wellsInRect(this.wellDragStart, this.wellDragEnd || this.wellDragStart));
    },
    /** 编辑目标：有选中用选中孔，否则回退 A01（板面不高亮） */
    editorWells() {
      if (this.selectedWellNos.length) return this.selectedWells;
      const a01 = this.normalizedWells(this.selectedSamplePlate).find((well) => well.well_no === 'A01');
      return a01 ? [a01] : [];
    },
    editorWellLabel() {
      if (this.wellDragFrozenLabel != null) return this.wellDragFrozenLabel;
      return this.selectedWellNos.length
        ? formatWellSelectionLabel(this.selectedWellNos)
        : 'A01';
    },
    compactEvents() {
      return (this.order.dispatches || []).slice(0, 5);
    },
    latestDispatch() {
      const list = this.order.dispatches || [];
      return list.length ? list[0] : null;
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
  },
  async created() {
    await this.loadMeta();
    await this.loadDetail();
  },
  beforeUnmount() {
    this.destroySamplePlateSortable();
    this.destroyCellColumnsSortable();
    this.teardownWellDragListeners();
  },
  watch: {
    '$route.fullPath'() {
      if (this.$route.name !== 'MegaFlowWorkOrderDetail') return;
      const id = this.$route.query.id;
      if (id && String(id) === String(this.order.id) && !this.$route.query.copyFrom) return;
      this.loadDetail();
    },
    activeCellPlate() {
      this.scheduleCellColumnsSortableInit();
    },
    activeSamplePlate() {
      this.clearWellSelection();
    },
    fieldDisabled(value) {
      if (this.samplePlateSortable) {
        this.samplePlateSortable.option('disabled', value);
      }
      if (this.cellColumnsSortable) {
        this.cellColumnsSortable.option('disabled', value);
      }
    },
    order: {
      deep: true,
      handler() {
        if (this.order.status === 'paused' && !this.pausedDirtyInit) {
          this.pausedLocalDirty = true;
        }
      },
    },
  },
  methods: {
    samplePlateRowKey(row) {
      return row._rowKey;
    },
    clearValidationIssues() {
      this.validationIssues = [];
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
    async loadDetail() {
      this.clearValidationIssues();
      this.loading = true;
      const id = this.$route.query.id;
      const copyFrom = this.$route.query.copyFrom;
      if (!id && !copyFrom) {
        this.loadError = false;
        this.order = this.normalizeOrder(defaultOrder());
        this.resetPausedTracking();
        this.clearWellSelection();
        this.scheduleSamplePlateSortableInit();
        this.scheduleCellColumnsSortableInit();
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
        this.resetPausedTracking();
      } catch (error) {
        this.loadError = true;
        this.order = this.normalizeOrder(defaultOrder());
        this.resetPausedTracking();
        ElMessage.error(error?.message || '工单加载失败，请返回列表后重试');
      } finally {
        this.loading = false;
        this.clearWellSelection();
        this.$nextTick(() => {
          this.pausedDirtyInit = false;
        });
        this.scheduleSamplePlateSortableInit();
        this.scheduleCellColumnsSortableInit();
      }
    },
    normalizeOrder(data) {
      const order = {
        ...defaultOrder(),
        ...data,
        base_info: data?.base_info || { order_name: '', remark: '', pc_infos: [] },
        sample_plates: Array.isArray(data?.sample_plates) ? data.sample_plates : [],
        cell_plates: Array.isArray(data?.cell_plates) ? data.cell_plates : [],
        dispatches: Array.isArray(data?.dispatches) ? data.dispatches : [],
      };
      order.base_info.order_name = data?.order_name || order.base_info.order_name || '';
      order.base_info.remark = data?.remark ?? order.base_info.remark ?? '';
      if (!Array.isArray(order.base_info.pc_infos)) {
        order.base_info.pc_infos = [];
      }
      order.base_info.pc_infos = this.normalizePcInfos(order.base_info.pc_infos);
      if (!order.priority) {
        order.priority = 'normal';
      }
      if (!order.sample_plates.length) {
        order.sample_plates.push(this.defaultSamplePlate());
      }
      if (!order.cell_plates.length) {
        order.cell_plates.push({ barcode: '', columns: this.defaultColumns() });
      }
      order.sample_plates.forEach((plate) => {
        if (!plate._rowKey) {
          plate._rowKey = createSamplePlateRowKey();
        }
        plate.wells = (Array.isArray(plate.wells) && plate.wells.length)
          ? this.buildFullWells(plate.wells)
          : this.defaultWells();
        if (plate.project_no == null) plate.project_no = '';
        if (plate.target == null) plate.target = '';
        if (!plate.secondary_antibody) plate.secondary_antibody = '人';
        plate.cell_keys = this.normalizeCellKeys(plate);
      });
      order.cell_plates.forEach((plate) => {
        plate.columns = this.normalizeColumns(plate.columns);
      });
      return order;
    },
    defaultWells() {
      if (this.defaultSampleWells.length) {
        return JSON.parse(JSON.stringify(this.defaultSampleWells));
      }
      return PLATE_ROWS.flatMap((row) =>
        Array.from({ length: 12 }, (_, index) => ({
          well_no: wellNo(row, index + 1),
          content_type: index === 11 ? 'PC' : 'SAMPLE',
          sample_code: index === 11 ? '' : wellNo(row, index + 1),
          pc_id: null,
          batch: '',
          generation: '',
        })),
      );
    },
    normalizePcInfos(pcInfos) {
      return (Array.isArray(pcInfos) ? pcInfos : []).map((pc) => {
        const pcId = pc.pc_id || createLocalPcId();
        return {
          pc_id: pcId,
          pc_type: String(pc.pc_type || 'SERUM').toUpperCase(),
          pc_name: pc.pc_name || '',
          catalog_batch: pc.catalog_batch || '',
          source: pc.source || '',
          concentration: pc.concentration || '',
        };
      });
    },
    normalizeWell(well) {
      const normalized = { ...(well || {}) };
      const type = String(normalized.content_type || 'SAMPLE').toUpperCase();
      let pcId = normalized.pc_id;
      if (pcId != null && pcId !== '') {
        pcId = String(pcId);
      } else {
        pcId = null;
      }
      if (!WELL_PC_REF_TYPES.includes(type)) {
        pcId = null;
      }
      return {
        well_no: normalized.well_no,
        content_type: type,
        sample_code: normalized.sample_code || '',
        pc_id: pcId,
        batch: normalized.batch || '',
        generation: normalized.generation || '',
      };
    },
    defaultSamplePlate() {
      return {
        _rowKey: createSamplePlateRowKey(),
        barcode: '',
        project_no: '',
        target: '',
        secondary_antibody: '人',
        cell_keys: [],
        wells: this.defaultWells(),
      };
    },
    defaultColumns() {
      return this.normalizeColumns(
        this.defaultCellColumns.length ? JSON.parse(JSON.stringify(this.defaultCellColumns)) : [],
      );
    },
    normalizeColumns(columns) {
      const byNo = new Map(
        (Array.isArray(columns) ? columns : []).map((col, index) => [
          Number(col.column_no) || index + 1,
          col,
        ]),
      );
      return Array.from({ length: 12 }, (_, index) => {
        const columnNo = index + 1;
        return {
          cell_type: '正常',
          cell_name: '',
          generation: '',
          batch: '',
          species: '',
          cell_count: '',
          catalog_no: '',
          source: '',
          ...(byNo.get(columnNo) || {}),
          column_no: columnNo,
        };
      });
    },
    buildFullWells(existing) {
      const wells = Array.isArray(existing) ? existing : [];
      const byNo = new Map(wells.map((well) => [well.well_no, well]));
      return PLATE_ROWS.flatMap((row) =>
        Array.from({ length: 12 }, (_, index) => {
          const no = wellNo(row, index + 1);
          const base = byNo.get(no) || {
            well_no: no,
            content_type: 'BLANK',
            sample_code: '',
            pc_id: null,
            batch: '',
            generation: '',
          };
          return this.normalizeWell({ ...base, well_no: no });
        }),
      );
    },
    normalizedWells(plate) {
      return Array.isArray(plate?.wells) ? plate.wells : [];
    },
    rowWells(plate, rowLabel) {
      return this.normalizedWells(plate).filter((well) => String(well.well_no).startsWith(rowLabel));
    },
    cellKey(barcode, columnNo) {
      return `${barcode || ''}|${columnNo || ''}`;
    },
    cellPlateBarcode(plate, index) {
      return plate.barcode || `细胞板${index + 1}`;
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
    normalizeCellKeys(plate) {
      return Array.isArray(plate.cell_keys) ? plate.cell_keys.filter(Boolean) : [];
    },
    applyCellSelection(plate, value) {
      plate.cell_keys = Array.isArray(value) ? value : [];
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
    isCellSelected(plate, key) {
      return Array.isArray(plate.cell_keys) && plate.cell_keys.includes(key);
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
    selectedCountInPlate(plate, plateOption) {
      if (!Array.isArray(plate.cell_keys) || !plate.cell_keys.length) return 0;
      const live = new Set((plateOption.children || []).map((cell) => cell.value));
      return plate.cell_keys.filter((key) => live.has(key)).length;
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
        this.clearWellSelection();
      }
    },
    samplePlateRowClass({ row }) {
      const index = this.order.sample_plates.indexOf(row);
      return this.activeSamplePlate === String(index) ? 'is-active-row' : '';
    },
    addSamplePlate() {
      this.order.sample_plates.push(this.defaultSamplePlate());
      this.activeSamplePlate = String(this.order.sample_plates.length - 1);
      this.clearWellSelection();
    },
    removeSamplePlate(index) {
      this.order.sample_plates.splice(index, 1);
      if (Number(this.activeSamplePlate) >= this.order.sample_plates.length) {
        this.activeSamplePlate = String(Math.max(0, this.order.sample_plates.length - 1));
      }
    },
    async initSamplePlateSortable() {
      this.destroySamplePlateSortable();
      await this.$nextTick();
      const table = this.$refs.samplePlateTable;
      if (!table) return;
      const tbody = table.$el?.querySelector('.el-table__body-wrapper tbody');
      if (!tbody) return;

      const SortableModule = await import('sortablejs/modular/sortable.complete.esm.js');
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
      this.scheduleCellColumnsSortableInit();
    },
    removeCellPlate(index) {
      this.order.cell_plates.splice(index, 1);
      if (Number(this.activeCellPlate) >= this.order.cell_plates.length) {
        this.activeCellPlate = String(Math.max(0, this.order.cell_plates.length - 1));
      }
      this.scheduleCellColumnsSortableInit();
    },
    resolveCellColumnsTable() {
      const ref = this.$refs.cellColumnsTable;
      if (!ref) return null;
      if (Array.isArray(ref)) {
        return ref[Number(this.activeCellPlate)] || ref[0] || null;
      }
      return ref;
    },
    async initCellColumnsSortable() {
      this.destroyCellColumnsSortable();
      await this.$nextTick();
      const table = this.resolveCellColumnsTable();
      if (!table) return;
      const tbody = table.$el?.querySelector('.el-table__body-wrapper tbody');
      if (!tbody) return;

      const SortableModule = await import('sortablejs/modular/sortable.complete.esm.js');
      const Sortable = SortableModule.default;
      this.cellColumnsSortable = Sortable.create(tbody, {
        handle: '.row-drag-handle',
        animation: 200,
        disabled: this.fieldDisabled,
        ghostClass: 'sortable-ghost',
        onEnd: (evt) => this.handleCellColumnsDragEnd(evt),
      });
    },
    handleCellColumnsDragEnd(evt) {
      const { oldIndex, newIndex, item } = evt;
      if (oldIndex == null || newIndex == null || oldIndex === newIndex) return;
      // 撤销 SortableJS 对 DOM 的搬动，交回 Vue 按数据渲染
      const parent = item?.parentNode;
      if (parent) {
        const anchor =
          newIndex > oldIndex ? parent.children[oldIndex] : parent.children[oldIndex + 1];
        parent.insertBefore(item, anchor || null);
      }
      // 固定 1-12 列槽：只重排内容字段，column_no / 对象身份 / cell_keys 都不动
      const contentFields = [
        'cell_type',
        'cell_name',
        'species',
        'batch',
        'generation',
        'cell_count',
        'catalog_no',
        'source',
      ];
      const columns = this.selectedCellPlate.columns;
      const snapshots = columns.map((col) => {
        const snap = {};
        contentFields.forEach((field) => {
          snap[field] = col[field];
        });
        return snap;
      });
      const [moved] = snapshots.splice(oldIndex, 1);
      snapshots.splice(newIndex, 0, moved);
      columns.forEach((col, index) => {
        contentFields.forEach((field) => {
          col[field] = snapshots[index][field];
        });
      });
      // 原引用列变空后直接清掉，不保留失效残留
      this.pruneEmptyCellRefs();
    },
    destroyCellColumnsSortable() {
      if (this.cellColumnsSortable) {
        this.cellColumnsSortable.destroy();
        this.cellColumnsSortable = null;
      }
    },
    scheduleCellColumnsSortableInit() {
      this.$nextTick(() => {
        this.initCellColumnsSortable();
      });
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
    clearWellSelection() {
      this.selectedWellNos = [];
      this.resetWellDrag();
      this.syncWellDraftFromEditor();
    },
    setWellSelection(nos) {
      this.selectedWellNos = nos;
      this.syncWellDraftFromEditor();
    },
    resetWellDrag() {
      this.wellDragActive = false;
      this.wellDragStart = '';
      this.wellDragEnd = '';
      this.wellDragFrozenLabel = null;
    },
    teardownWellDragListeners() {
      document.removeEventListener('mouseup', this.onWellDragEnd);
    },
    syncWellDraftFromEditor() {
      const wells = this.editorWells;
      if (!wells.length) {
        this.wellDraft = { content_type: '', pc_id: null, sample_code: '' };
        return;
      }
      const types = [...new Set(wells.map((well) => String(well.content_type || 'SAMPLE').toUpperCase()))];
      const contentType = types.length === 1 ? types[0] : '';
      let pcId = null;
      if (contentType && this.isPcRefType(contentType)) {
        const pcIds = [
          ...new Set(
            wells
              .map((well) => (well.pc_id == null || well.pc_id === '' ? null : String(well.pc_id)))
              .filter(Boolean),
          ),
        ];
        pcId = pcIds.length === 1 ? pcIds[0] : null;
      }
      let sampleCode = '';
      if (contentType === 'SAMPLE') {
        const codes = [...new Set(wells.map((well) => String(well.sample_code || '').trim()).filter(Boolean))];
        sampleCode = codes.length === 1 ? codes[0] : '';
      }
      this.wellDraft = {
        content_type: contentType,
        pc_id: pcId,
        sample_code: sampleCode,
      };
    },
    applyWellDraft() {
      const wells = this.editorWells;
      if (!wells.length || !this.wellDraft.content_type) return;
      const { content_type: contentType, pc_id: pcId, sample_code: sampleCode } = this.wellDraft;
      wells.forEach((well) => {
        well.content_type = contentType;
        this.onWellTypeChange(well);
        if (this.isPcRefType(contentType)) {
          well.pc_id = pcId ?? null;
        } else if (this.isSampleType(contentType)) {
          well.sample_code = sampleCode || '';
        }
      });
    },
    onWellMouseDown(well, event) {
      if (this.fieldDisabled || event.button !== 0) return;
      this.teardownWellDragListeners();
      this.wellDragFrozenLabel = this.editorWellLabel;
      this.wellClickToggle =
        this.selectedWellNos.length === 1 && this.selectedWellNos[0] === well.well_no;
      this.selectedWellNos = [];
      this.wellDragActive = true;
      this.wellDragStart = well.well_no;
      this.wellDragEnd = well.well_no;
      document.addEventListener('mouseup', this.onWellDragEnd);
    },
    onWellMouseEnter(well) {
      if (!this.wellDragActive) return;
      this.wellDragEnd = well.well_no;
    },
    onWellDragEnd() {
      if (!this.wellDragActive) return;
      const start = this.wellDragStart;
      const end = this.wellDragEnd || start;
      const toggleOff = this.wellClickToggle;
      this.wellClickToggle = false;
      this.teardownWellDragListeners();
      this.resetWellDrag();
      if (!start) return;
      if (start === end && toggleOff) {
        this.clearWellSelection();
        return;
      }
      this.setWellSelection(start === end ? [start] : wellsInRect(start, end));
    },
    cycleWellType(well) {
      if (this.fieldDisabled) return;
      if (!this.selectedWellSet.has(well.well_no)) {
        this.selectedWellNos = [well.well_no];
      }
      const targets = this.selectedWells;
      if (!targets.length) return;
      const current = String(targets[0].content_type || 'SAMPLE').toUpperCase();
      const index = WELL_TYPE_CYCLE.indexOf(current);
      this.wellDraft.content_type = WELL_TYPE_CYCLE[(index + 1) % WELL_TYPE_CYCLE.length];
      this.applyWellDraft();
      this.syncWellDraftFromEditor();
    },
    onWellTypeChange(well) {
      const type = String(well.content_type || 'SAMPLE').toUpperCase();
      if (!this.isPcRefType(type)) {
        well.pc_id = null;
      } else if (well.pc_id != null) {
        const pc = this.pcInfoById(well.pc_id);
        if (!pc || pc.pc_type !== wellPcInfoType(type)) {
          well.pc_id = null;
        }
      }
      if (type !== 'SAMPLE') {
        well.sample_code = '';
      }
    },
    isPcRefType(type) {
      return WELL_PC_REF_TYPES.includes(String(type || '').toUpperCase());
    },
    isSampleType(type) {
      return String(type || '').toUpperCase() === 'SAMPLE';
    },
    pcInfoById(pcId) {
      if (pcId == null || pcId === '') return null;
      return this.pcInfos.find((pc) => pc.pc_id === String(pcId)) || null;
    },
    pcInfosForWellType(wellType) {
      const pcType = wellPcInfoType(wellType);
      if (!pcType) return [];
      return this.pcInfos.filter((pc) => pc.pc_type === pcType);
    },
    wellTypeLabel(type) {
      return WELL_TYPE_LABELS[String(type || 'SAMPLE').toUpperCase()] || '样本';
    },
    wellCellText(well) {
      const type = String(well.content_type || 'SAMPLE').toUpperCase();
      if (type === 'SAMPLE') return well.sample_code || '';
      if (type === 'BLANK') return '';
      return this.wellTypeLabel(type);
    },
    wellTooltip(well) {
      const contentType = String(well.content_type || 'SAMPLE').toUpperCase();
      const parts = [well.well_no, this.wellTypeLabel(contentType)];
      if (contentType === 'SAMPLE' && well.sample_code) {
        parts.push(well.sample_code);
      } else if (this.isPcRefType(contentType)) {
        const pcName = this.pcInfoById(well.pc_id)?.pc_name;
        if (pcName) parts.push(pcName);
      }
      return `${parts.join(' · ')} · 拖拽划选 · 右键切换类型`;
    },
    buildSavePayload() {
      return {
        id: this.order.id,
        order_name: this.order.base_info.order_name,
        order_no: this.order.order_no || '',
        remark: this.order.base_info.remark,
        data_type: this.order.data_type,
        priority: this.order.priority,
        expected_content_hash: this.order.content_hash || '',
        base_info: this.order.base_info,
        sample_plates: this.order.sample_plates,
        cell_plates: this.order.cell_plates,
      };
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
          ElMessage.success('校验通过');
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
          ElMessage.success('校验通过，修改已保存，此前下发记录已失效');
          return;
        }
        if (data.can_resume) {
          ElMessage.success('校验通过，内容未变化，可点击继续恢复发送状态');
          return;
        }
        ElMessage.success('校验通过');
      } catch (error) {
        if (error !== 'cancel' && error?.message !== 'cancel') {
          this.applyValidationResult({
            errors: [error?.message || '校验失败'],
          });
        }
      }
    },
    async dispatchOrder() {
      if (!this.order.id) return;
      try {
        const data = await dispatchFlowWorkOrder(this.order.id);
        this.order = this.normalizeOrder(data);
        this.activeTab = 'payload';
        ElMessage.success('已发送');
      } catch (error) {
        ElMessage.warning(error?.message || '发送失败，请确认已校验通过');
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
      if (!this.order.id) return;
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
      }
    },
    async acknowledgeResume() {
      if (!this.order.id) return;
      try {
        const data = await acknowledgeResumeFlowWorkOrder(this.order.id);
        this.order = this.normalizeOrder(data);
        ElMessage.success(
          data?.status === 'running' ? '设备已恢复，工单继续执行' : '设备已恢复，工单回到已发送状态',
        );
      } catch (error) {
        ElMessage.warning(error?.message || '确认设备恢复失败');
      }
    },
    async resumeOrder() {
      if (!this.order.id) return;
      try {
        const data = await resumeFlowWorkOrder(this.order.id);
        this.order = this.normalizeOrder(data);
        ElMessage.success('已请求恢复，等待设备确认');
      } catch (error) {
        ElMessage.warning(error?.message || '无法继续，请先校验确认修改');
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
      if (!value) return '暂无数据';
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
.is-invalid-control.el-select :deep(.el-select__wrapper) {
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

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.panel-head-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.panel-head-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.head-icon {
  font-size: 16px;
  color: $primary;
}

.panel-title {
  font-size: 15px;
  font-weight: 700;
  color: $title-color;
}

.panel-hint {
  font-size: 12px;
  color: $muted-color;
}

.field-label {
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

.row-drag-handle {
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

.cell-plate-barcode {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  max-width: 320px;
}

.inner-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: 10px;
  }

  :deep(.el-tabs__item) {
    padding: 0 12px;
    font-size: 13px;
  }

  :deep(.el-tabs__item.is-active) {
    border-bottom-color: $border-color;
  }
}

.tab-label {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.tab-close {
  font-size: 12px;
  color: $muted-color;

  &:hover {
    color: #f56c6c;
  }
}

/* 可视化面板 */
.viz-panel {
  background: #fff;
}

.plate-current-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.current-code {
  font-size: 13px;
  font-weight: 600;
  color: $title-color;
}

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: $muted-color;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border: 1px solid #d0d5dd;
  border-radius: 3px;

  &.well-sample { background: #eef5ff; }
  &.well-pc { background: #fff2e6; }
  &.well-nc { background: #eef2ff; }
  &.well-iso { background: #eafbf1; }
  &.well-tag { background: #f3effe; }
  &.well-blank { background: #f8fafc; }
}

/* 当前孔编辑条 */
.well-editor {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  min-height: 40px;
  padding: 8px 10px;
  margin-bottom: 10px;
  background: #f7f9fc;
  border: 1px solid #e8ebf1;
  border-radius: 6px;
}

.well-editor-no {
  padding: 2px 8px;
  font-size: 12px;
  font-weight: 700;
  color: #fff;
  background: $primary;
  border-radius: 4px;
}

.well-type-select {
  width: 96px;
}

.well-value-input {
  width: 220px;
  max-width: 60%;
}

.well-editor-static {
  font-size: 12px;
  color: $muted-color;
}

.well-editor-tip {
  margin-left: auto;
  font-size: 12px;
  color: $muted-color;
}

/* 96 孔板 */
.plate-grid-wrap {
  width: 100%;
  overflow-x: auto;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  user-select: none;
}

.plate-grid {
  width: 100%;
  min-width: 560px;
  border-collapse: collapse;
  table-layout: fixed;
  background: #fff;

  th,
  td {
    border: 1px solid #e6e9ef;
  }

  thead th {
    height: 26px;
    font-size: 11px;
    font-weight: 600;
    color: $label-color;
    background: #f5f7fa;
  }

  .corner {
    width: 26px;
  }

  .row-head {
    width: 26px;
    font-size: 11px;
    font-weight: 600;
    color: $label-color;
    background: #f5f7fa;
  }
}

.well-cell {
  height: 40px;
  padding: 2px;
  text-align: center;
  vertical-align: middle;
  cursor: pointer;
  transition: box-shadow 0.12s ease;

  .well-text {
    display: block;
    overflow: hidden;
    font-size: 10px;
    line-height: 1.2;
    color: #475569;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &.well-sample { background: #f4f9ff; }
  &.well-pc { background: #fff2e6; }
  &.well-nc { background: #eef2ff; }
  &.well-iso { background: #eafbf1; }
  &.well-tag { background: #f3effe; }
  &.well-blank { background: #fbfcfe; }

  &.well-pc .well-text,
  &.well-nc .well-text,
  &.well-iso .well-text,
  &.well-tag .well-text {
    font-weight: 700;
    color: $title-color;
  }

  /* 孔位交互态：拖选预览 / 正式选中 */
  $well-hover-border:rgba(111, 183, 255, 0.8);
  $well-selected-border:rgba(62, 158, 255, 0.8);

  &.is-drag-preview:not(.is-selected) {
    box-shadow: inset 0 0 0 1px $well-hover-border;
  }

  &.is-selected {
    box-shadow: inset 0 0 0 1px $well-selected-border;
  }
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
  .json-layout {
    grid-template-columns: minmax(0, 1fr);
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
