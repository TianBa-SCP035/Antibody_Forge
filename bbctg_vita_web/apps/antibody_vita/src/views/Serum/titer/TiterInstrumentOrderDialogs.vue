<template>
  <!-- 右键：关联流式工单列表 -->
  <el-dialog
    v-model="flowListVisible"
    width="720px"
    append-to-body
    destroy-on-close
    align-center
    class="tio-dialog tio-dialog--list"
    @opened="loadFlowOrderList"
    @closed="onFlowListClosed"
  >
    <template #header>
      <div class="tio-header">
        <div class="tio-header-mark" aria-hidden="true" />
        <div class="tio-header-text">
          <h3 class="tio-title">关联流式工单</h3>
          <p class="tio-subtitle">
            {{ canEditInstrument
              ? '选择已有工单进入详情，或新建上机任务'
              : '选择已有工单进入只读详情' }}
          </p>
        </div>
      </div>
    </template>

    <div v-if="titerOrder" class="tio-identity">
      <div class="tio-fields">
        <div v-for="field in identityFields" :key="field.label" class="tio-field">
          <span class="tio-field-k">{{ field.label }}</span>
          <span class="tio-field-v">{{ field.value }}</span>
        </div>
      </div>
    </div>

    <div class="tio-panel">
      <el-table
        v-loading="flowListLoading"
        :data="flowListItems"
        size="small"
        max-height="340"
        class="tio-table tio-table--click"
        highlight-current-row
        empty-text="暂无关联流式工单"
        @row-click="onFlowOrderRowClick"
      >
        <el-table-column label="ID" prop="id" width="64" align="center" />
        <el-table-column label="订单编号" prop="orderNum" min-width="124" show-overflow-tooltip />
        <el-table-column label="订单名称" prop="orderName" min-width="100" show-overflow-tooltip />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="flowOrderStatusTagType(row)" effect="plain" size="small">
              {{ flowOrderStatusLabel(row) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" prop="updated_at" min-width="140" show-overflow-tooltip />
      </el-table>
    </div>

    <template #footer>
      <div class="tio-footer">
        <span class="tio-footer-hint">{{ flowListFooterHint }}</span>
        <div class="tio-footer-actions">
          <el-button class="tio-btn" @click="flowListVisible = false">关闭</el-button>
          <el-button
            v-if="canEditInstrument"
            type="primary"
            class="tio-btn tio-btn-accent"
            @click="openWizardFromFlowList"
          >
            新建上机工单
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>

  <TiterMouseSelectWizard
    v-model="wizardVisible"
    :titer-order="titerOrder"
    :confirming="confirming"
    @confirm="onWizardConfirm"
  />
</template>

<script>
import {
  ElButton,
  ElDialog,
  ElMessage,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus';

import { notifyApiError } from '#/api/errors';
import { fetchFlowWorkOrdersBySource } from '#/api/megaAutomation';
import {
  orderStatusTagType,
  resolveOrderDisplayLabel,
  resolveOrderDisplayStatus,
} from '#/utils/megaFlowWorkOrderStatus';

import {
  TITER_INSTRUMENT_WIZARD_DRAFT_KEY,
  TITER_UPSTREAM_PREFILL_QUERY,
} from '#/views/MegaAutomation/FlowWorkOrder/flowWorkOrderTiterUpstream';

import TiterMouseSelectWizard from './TiterMouseSelectWizard.vue';
import { titerOrderIdentityFields } from './titerMouseSelect';

const FLOW_ORDER_TYPE = 'TITER';

export default {
  name: 'TiterInstrumentOrderDialogs',
  components: {
    ElButton,
    ElDialog,
    ElTable,
    ElTableColumn,
    ElTag,
    TiterMouseSelectWizard,
  },
  data() {
    return {
      titerOrder: null,
      canEditInstrument: false,
      leftClickBusy: false,

      flowListVisible: false,
      flowListLoading: false,
      flowListItems: [],

      wizardVisible: false,
      confirming: false,
    };
  },
  computed: {
    identityFields() {
      return titerOrderIdentityFields(this.titerOrder);
    },
    flowListFooterHint() {
      if (this.flowListLoading) return '';
      const n = this.flowListItems.length;
      if (!n) {
        return this.canEditInstrument ? '暂无记录 · 可直接新建' : '暂无关联流式工单';
      }
      return this.canEditInstrument
        ? `共 ${n} 条 · 点击行打开详情`
        : `共 ${n} 条 · 点击行打开只读详情`;
    },
  },
  methods: {
    handleLeftClick(row, options = {}) {
      if (!row?.titer_order_id) {
        ElMessage.warning('缺少效价工单信息');
        return;
      }
      if (this.leftClickBusy) return;
      this.leftClickBusy = true;
      this.titerOrder = row;
      this.canEditInstrument = !!options.canEdit;
      fetchFlowWorkOrdersBySource({
        orderType: FLOW_ORDER_TYPE,
        source_id: row.titer_order_id,
        exclude_cancelled: true,
      })
        .then((data) => {
          const items = data?.items || [];
          if (!items.length) {
            if (!this.canEditInstrument) {
              ElMessage.info('暂无关联流式工单');
              return;
            }
            this.wizardVisible = true;
            return;
          }
          this.goFlowWorkOrderDetail(items[0]);
        })
        .catch((error) => notifyApiError(error, { messages: { default: '查询流式工单失败' } }))
        .finally(() => {
          this.leftClickBusy = false;
        });
    },
    handleRightClick(row, options = {}) {
      if (!row?.titer_order_id) {
        ElMessage.warning('缺少效价工单信息');
        return;
      }
      this.titerOrder = row;
      this.canEditInstrument = !!options.canEdit;
      this.flowListVisible = true;
    },

    loadFlowOrderList() {
      const sourceId = (this.titerOrder?.titer_order_id || '').trim();
      if (!sourceId) {
        this.flowListItems = [];
        return;
      }
      this.flowListLoading = true;
      fetchFlowWorkOrdersBySource({
        orderType: FLOW_ORDER_TYPE,
        source_id: sourceId,
        exclude_cancelled: false,
      })
        .then((data) => {
          this.flowListItems = data?.items || [];
        })
        .catch((error) => notifyApiError(error, { messages: { default: '加载流式工单失败' } }))
        .finally(() => {
          this.flowListLoading = false;
        });
    },
    onFlowListClosed() {
      this.flowListItems = [];
      this.flowListLoading = false;
    },
    flowOrderStatusLabel(row) {
      return resolveOrderDisplayLabel(row);
    },
    flowOrderStatusTagType(row) {
      return orderStatusTagType(resolveOrderDisplayStatus(row));
    },
    onFlowOrderRowClick(row) {
      if (!row?.id) return;
      this.flowListVisible = false;
      this.goFlowWorkOrderDetail(row);
    },
    openWizardFromFlowList() {
      if (!this.canEditInstrument) {
        ElMessage.warning('您没有权限新建上机工单');
        return;
      }
      this.flowListVisible = false;
      this.$nextTick(() => {
        this.wizardVisible = true;
      });
    },
    goFlowWorkOrderDetail(order) {
      if (!order?.id) return;
      this.$router.push({
        path: '/mega-automation/flow-work-orders/detail',
        query: {
          id: String(order.id),
          mode: this.canEditInstrument ? 'edit' : 'view',
        },
      });
    },
    async onWizardConfirm(payload) {
      if (this.confirming) return;
      this.confirming = true;
      try {
        sessionStorage.setItem(
          TITER_INSTRUMENT_WIZARD_DRAFT_KEY,
          JSON.stringify(payload),
        );
      } catch {
        this.confirming = false;
        ElMessage.error('无法暂存选鼠结果，请清理浏览器缓存后重试');
        return;
      }
      try {
        this.wizardVisible = false;
        await this.$router.push({
          name: 'MegaFlowWorkOrderDetail',
          query: {
            mode: 'edit',
            prefill: TITER_UPSTREAM_PREFILL_QUERY,
            n: String(Date.now()),
          },
        });
      } catch (error) {
        ElMessage.error(error?.message || '无法打开流式工单编辑页');
      } finally {
        this.confirming = false;
      }
    },
  },
};
</script>

<style lang="scss" scoped src="./titerInstrumentOrder.scss"></style>
<style lang="scss" src="./titerInstrumentOrderDialog.scss"></style>
