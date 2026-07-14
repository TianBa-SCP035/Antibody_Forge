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

    <Transition name="detail-fade" mode="out-in">
      <div
        v-if="loading"
        key="loading"
        v-loading="true"
        element-loading-text="正在读取并解析工单数据..."
        class="detail-loading"
      ></div>
      <div v-else key="content" class="detail-content">
      <div v-if="validationIssues.length" class="validation-banner">
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
        v-if="order.status === 'validated' && optionalWellWarnings.total"
        class="optional-warning-banner"
      >
        校验已通过，但{{ optionalWellWarnings.text }}。这些内容为可选项，可直接发送；跟随提示可继续补充。
      </div>

      <div v-if="loadError" class="validation-banner">
        工单加载失败。为避免误建工单，当前页面已禁止保存和操作，请返回列表后重试。
      </div>
      <div v-else-if="!order.id" class="preview-banner">
        当前为未保存草稿，填写订单编号后可保存。
      </div>

      <!-- 基础信息 + 时间线 -->
      <section class="panel base-panel">
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

      <el-tabs v-model="activeTab" class="detail-tabs">
        <el-tab-pane label="工单编辑" name="editor">
          <EditorTab
            ref="editorTab"
            v-model:active-sample-plate="activeSamplePlate"
            v-model:active-cell-plate="activeCellPlate"
            :order="order"
            :field-disabled="fieldDisabled"
            :validation-issues="validationIssues"
            :default-sample-wells="defaultSampleWells"
            :default-cell-columns="defaultCellColumns"
            :warning-well-nos="activeOptionalWarningWells"
            @barcode-focus="rememberCellBarcode"
            @barcode-change="remapCellBarcode"
            @columns-reordered="handleCellColumnsReordered"
          />
        </el-tab-pane>

        <el-tab-pane label="铺板" name="plating">
          <PlatingTab
            :order="order"
            :field-disabled="fieldDisabled"
            :pc-infos="pcInfos"
            @barcode-focus="rememberCellBarcode"
            @barcode-change="remapCellBarcode"
          />
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
    </Transition>
  </div>
</template>

<script>
import { ArrowLeft, Menu } from '@element-plus/icons-vue';
import {
  ElButton,
  ElIcon,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElSelect,
  ElTabPane,
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
} from '#/utils/megaPermission';
import {
  buildDispatchChipLabel,
  normalizePauseState,
  orderStatusTagType,
  resolveOrderDisplayLabel,
  resolveOrderDisplayStatus,
} from '#/utils/megaFlowWorkOrderStatus';
import EditorTab from './components/EditorTab.vue';
import PlatingTab from './components/PlatingTab.vue';
import {
  buildFlowWorkOrderSavePayload,
  cellKey,
  cellPlateBarcode,
  createDefaultFlowWorkOrder,
  EDITABLE_STATUSES,
  normalizeFlowWorkOrder,
} from './flowWorkOrderModel';

export default {
  name: 'MegaFlowWorkOrderDetail',
  components: {
    ArrowLeft,
    EditorTab,
    ElButton,
    ElIcon,
    ElInput,
    ElOption,
    ElSelect,
    ElTabPane,
    ElTabs,
    ElTag,
    Menu,
    PlatingTab,
  },
  setup() {
    const userStore = useUserStore();
    return {
      cellKey,
      cellPlateBarcode,
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
      activePayload: null,
      activePayloadDispatch: null,
      activePayloadLoading: false,
      activeSamplePlate: '0',
      activeCellPlate: '0',
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
    this.reloadIfRouteIdentityChanged();
  },
  beforeUnmount() {
    this.stopPausedDirtyWatch();
  },
  watch: {
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
    // fullPathKey:false 下仅 query 变化不会重挂载；从列表再进另一工单时靠这里拉数
    '$route.query.id'() {
      this.reloadIfRouteIdentityChanged();
    },
    '$route.query.copyFrom'() {
      this.reloadIfRouteIdentityChanged();
    },
  },
  methods: {
    clearActivePayload() {
      this.activePayload = null;
      this.activePayloadDispatch = null;
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
    reloadIfRouteIdentityChanged() {
      // 返回列表时路由已切走，详情组件可能仍处在离开动画中；勿按「无 id」当成新建草稿重载
      if (this.$route.name !== 'MegaFlowWorkOrderDetail') return;
      if (this.loading) return;
      if (this.loadedRouteIdentity === this.detailRouteIdentity()) return;
      this.loadDetail();
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
        this.loading = false;
        this.$nextTick(() => {
          this.$refs.editorTab?.scheduleSamplePlateSortableInit();
        });
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
          this.$refs.editorTab?.scheduleSamplePlateSortableInit();
        });
      }
    },
    normalizeOrder(data) {
      return normalizeFlowWorkOrder(data, {
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
          // 先对齐 identity，避免 replace 触发 query watch 后又去全屏重载
          this.loadedRouteIdentity = `id:${data.id}`;
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
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 360px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: $radius;
}

.detail-content {
  min-width: 0;
}

.detail-fade-enter-active,
.detail-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.detail-fade-enter-from {
  opacity: 0;
  transform: translateY(6px);
}

.detail-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
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
:deep(.is-invalid-control .el-input__wrapper),
:deep(.is-invalid-control.el-select .el-select__wrapper) {
  box-shadow: 0 0 0 1px #f56c6c inset !important;
}

:deep(.cell-select-trigger.is-invalid-control) {
  box-shadow: 0 0 0 1px #f56c6c inset;
  background: #fff;
}

/* 通用面板（含 EditorTab / PlatingTab 内：需 :deep 才能穿透子组件） */
.panel,
:deep(.panel) {
  padding: 14px 16px;
  margin-bottom: 12px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: $radius;
  box-shadow: 0 1px 2px rgb(0 0 0 / 4%);
}

.panel-head,
:deep(.panel-head) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.panel-head-left,
:deep(.panel-head-left) {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

:deep(.panel-head-right) {
  display: flex;
  align-items: center;
  gap: 10px;
}

.head-icon,
:deep(.head-icon) {
  font-size: 16px;
  color: $primary;
}

.panel-title,
:deep(.panel-title) {
  font-size: 15px;
  font-weight: 700;
  color: $title-color;
}

.panel-hint,
:deep(.panel-hint) {
  font-size: 12px;
  color: $muted-color;
}

.field-label,
:deep(.field-label) {
  font-size: 13px;
  color: $label-color;
  white-space: nowrap;
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
