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

  <!-- 左键无工单 / 右键「新建」：上机选鼠向导 -->
  <el-dialog
    v-model="wizardVisible"
    width="960px"
    append-to-body
    destroy-on-close
    align-center
    class="tio-dialog tio-dialog--wizard"
    @open="handleWizardOpen"
    @closed="onWizardClosed"
  >
    <template #header>
      <div class="tio-header">
        <div class="tio-header-mark" aria-hidden="true" />
        <div class="tio-header-text">
          <h3 class="tio-title">上机工单</h3>
          <p class="tio-subtitle">确认鼠号死活，勾选待测个体后进入流式工单预填</p>
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

    <div class="tio-wizard-scroll">
      <section class="tio-stage">
        <div class="tio-stage-head">
          <span class="tio-stage-index">01</span>
          <div class="tio-stage-copy">
            <h4 class="tio-stage-title">小鼠分组</h4>
            <p class="tio-stage-desc">只读浏览 · 点击鼠号可登记死活并即时入库</p>
          </div>
        </div>
        <div class="tio-panel">
          <el-table
            v-loading="groupsLoading"
            :data="mouseGroups"
            size="small"
            class="tio-table"
            empty-text="暂无小鼠分组"
          >
            <el-table-column label="组别" prop="group_id" width="70" show-overflow-tooltip />
            <el-table-column label="品系" prop="mouse_strain" min-width="110" show-overflow-tooltip />
            <el-table-column label="性别" prop="sex" width="56" align="center" />
            <el-table-column label="数量" prop="mouse_count" width="56" align="center" />
            <el-table-column label="鼠号" min-width="150">
              <template #default="{ row }">
                <button
                  type="button"
                  class="tio-link"
                  :title="row.mouse_no_list || '编辑鼠号'"
                  @click="openMouseRegistryDialog(row)"
                >
                  {{ row.mouse_no_list || '点击编辑' }}
                </button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </section>

      <section class="tio-stage">
        <div class="tio-stage-head">
          <span class="tio-stage-index">02</span>
          <div class="tio-stage-copy">
            <h4 class="tio-stage-title">选择待测小鼠</h4>
            <p class="tio-stage-desc">拖拽划选 · 单击切换 · 死亡鼠不可选</p>
          </div>
          <div class="tio-stage-metrics">
            <div class="tio-metric">
              <span class="tio-metric-n">{{ selectionSummary.selected }}</span>
              <span class="tio-metric-l">已选</span>
            </div>
            <div class="tio-metric tio-metric--mute">
              <span class="tio-metric-n">{{ selectionSummary.alive }}</span>
              <span class="tio-metric-l">存活</span>
            </div>
            <div v-if="selectionSummary.dead" class="tio-metric tio-metric--mute">
              <span class="tio-metric-n">{{ selectionSummary.dead }}</span>
              <span class="tio-metric-l">死亡</span>
            </div>
          </div>
        </div>

        <div class="tio-board-hint">
          <span class="tio-hint-item">
            <i class="tio-hint-swatch tio-hint-swatch--pick" />划选加入
          </span>
          <span class="tio-hint-item">
            <i class="tio-hint-swatch tio-hint-swatch--drop" />划选取消
          </span>
        </div>

        <el-empty
          v-if="!groupsLoading && !plateGroups.length"
          description="暂无鼠号，请先在分组中编辑录入"
          :image-size="52"
          class="tio-empty"
        />

        <div v-for="group in plateGroups" :key="group.groupId" class="tio-board">
          <div class="tio-board-bar">
            <div class="tio-board-who">
              <span class="tio-board-gid">{{ group.groupId }}</span>
              <span v-if="group.strain" class="tio-board-strain">{{ group.strain }}</span>
            </div>
            <span class="tio-board-ratio">
              {{ group.selectedCount }}
              <span class="tio-board-ratio-sep">/</span>
              {{ group.aliveCount }}
            </span>
          </div>
          <div class="tio-plate-wrap">
            <table class="tio-plate">
              <thead>
                <tr>
                  <th class="tio-plate-corner" />
                  <th
                    v-for="col in plateColumnList"
                    :key="`${group.groupId}-c-${col}`"
                    class="tio-plate-col"
                  >{{ col }}</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="row in group.plateRows"
                  :key="`${group.groupId}-${row.rowLabel}`"
                >
                  <th class="tio-plate-row">{{ row.rowLabel }}</th>
                  <td
                    v-for="cell in row.cells"
                    :key="cell.key"
                    class="tio-well"
                    :class="wellCellClass(group.groupId, cell)"
                    :title="cellTitle(cell)"
                    @mousedown.prevent="onCellMouseDown(group.groupId, cell, $event)"
                    @mouseenter="onCellMouseEnter(group.groupId, cell)"
                  >
                    <span v-if="cell.no" class="tio-well-text">{{ cell.no }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>

    <MouseRegistryDialog
      v-model="mouseRegistryVisible"
      :group="mouseRegistryEditingRow"
      @confirm="onMouseRegistryConfirm"
    />

    <template #footer>
      <div class="tio-footer">
        <span class="tio-footer-hint">未选小鼠也可继续（如仅补对照）</span>
        <div class="tio-footer-actions">
          <el-button class="tio-btn" @click="wizardVisible = false">取消</el-button>
          <el-button
            type="primary"
            class="tio-btn tio-btn-accent"
            :loading="confirming"
            :disabled="groupsLoading || savingRegistry"
            @click="handleConfirm"
          >
            确定
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script>
import {
  ElButton,
  ElDialog,
  ElEmpty,
  ElMessage,
  ElMessageBox,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus';

import { notifyApiError } from '#/api/errors';
import { fetchFlowWorkOrdersBySource } from '#/api/megaAutomation';
import { fetchMouseGroups, saveMouseRegistry } from '#/api/serum';
import {
  orderStatusTagType,
  resolveOrderDisplayLabel,
  resolveOrderDisplayStatus,
} from '#/utils/megaFlowWorkOrderStatus';

import MouseRegistryDialog from '../shared/MouseRegistryDialog.vue';

import {
  TITER_INSTRUMENT_WIZARD_DRAFT_KEY,
  TITER_UPSTREAM_PREFILL_QUERY,
} from '#/views/MegaAutomation/FlowWorkOrder/flowWorkOrderTiterUpstream';

const PLATE_COLUMNS = 10;
const PLATE_COLUMN_LIST = Array.from({ length: PLATE_COLUMNS }, (_, i) => i + 1);
const ROW_LABELS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
const FLOW_ORDER_TYPE = 'TITER';

const IDENTITY_FIELDS = [
  { key: 'project_code', label: '项目编号', kind: 'text' },
  { key: 'target_name', label: '靶点', kind: 'text' },
  { key: 'cage_position', label: '笼位', kind: 'text' },
  { key: 'mouse_count', label: '只数', kind: 'number' },
  { key: 'assay_method', label: '检测方法', kind: 'text' },
  { key: 'facs_plate_count', label: 'FACS', kind: 'number' },
  { key: 'elisa_plate_count', label: 'ELISA', kind: 'number' },
];

function parseLegacyMouseTokens(str) {
  const text = (str || '').trim();
  if (!text) return [];
  const tokens = [];
  for (const part of text.split(/[，\n]+/)) {
    const match = part.match(/^[FM]：(.+)$/);
    const body = match?.[1] || part;
    body.split('、').forEach((token) => {
      const no = token.trim();
      if (no) tokens.push(no);
    });
  }
  return tokens;
}

function miceInGroup(group) {
  const registry = group?.mouse_registry?.mice;
  if (Array.isArray(registry) && registry.length) {
    return registry
      .map((mouse) => ({
        no: String(mouse?.no || '').trim(),
        alive: mouse?.alive !== false,
      }))
      .filter((mouse) => mouse.no);
  }
  return parseLegacyMouseTokens(group?.mouse_no_list || '').map((no) => ({ no, alive: true }));
}

function mouseSlotNo(rowLabel, column) {
  return `${rowLabel}${String(column).padStart(2, '0')}`;
}

function parseMouseSlotNo(value) {
  const match = String(value || '').match(/^([A-Z])(\d{1,2})$/i);
  if (!match?.[1] || !match[2]) return null;
  const rowIndex = ROW_LABELS.indexOf(match[1].toUpperCase());
  const column = Number.parseInt(match[2], 10);
  return rowIndex >= 0 && column >= 1 && column <= PLATE_COLUMNS
    ? { rowIndex, column }
    : null;
}

function mouseSlotsInRect(startNo, endNo) {
  const start = parseMouseSlotNo(startNo);
  const end = parseMouseSlotNo(endNo);
  if (!start || !end) return [];
  const result = [];
  const rowMin = Math.min(start.rowIndex, end.rowIndex);
  const rowMax = Math.max(start.rowIndex, end.rowIndex);
  const colMin = Math.min(start.column, end.column);
  const colMax = Math.max(start.column, end.column);
  for (let rowIndex = rowMin; rowIndex <= rowMax; rowIndex += 1) {
    for (let column = colMin; column <= colMax; column += 1) {
      result.push(mouseSlotNo(ROW_LABELS[rowIndex] || '', column));
    }
  }
  return result;
}

function layoutPlateRows(mice) {
  if (!mice.length) return [];
  const rows = [];
  for (let index = 0; index < mice.length; index += PLATE_COLUMNS) {
    const rowIndex = Math.floor(index / PLATE_COLUMNS);
    const rowLabel = ROW_LABELS[rowIndex] || String(rowIndex + 1);
    const cells = [];
    for (let column = 1; column <= PLATE_COLUMNS; column += 1) {
      const mouseIndex = index + column - 1;
      const slotNo = mouseSlotNo(rowLabel, column);
      if (mouseIndex < mice.length) {
        const mouse = mice[mouseIndex];
        cells.push({
          ...mouse,
          mouseIndex,
          slotNo,
          key: `m-${mouseIndex}`,
        });
      } else {
        cells.push({
          no: '',
          alive: false,
          mouseIndex: -1,
          slotNo,
          key: `empty-${rowIndex}-${column}`,
        });
      }
    }
    rows.push({ rowLabel, cells });
  }
  return rows;
}

function selectionKey(groupId, mouseIndex) {
  return `${groupId}::${mouseIndex}`;
}

function buildPlateGroup(group, selectedKeys) {
  const groupId = (group.group_id || '').trim();
  if (!groupId) return null;
  const mice = miceInGroup(group);
  if (!mice.length) return null;

  const plateRows = layoutPlateRows(mice);
  const cellBySlot = new Map();
  for (const row of plateRows) {
    for (const cell of row.cells) {
      if (cell.slotNo) cellBySlot.set(cell.slotNo, cell);
    }
  }

  let aliveCount = 0;
  let deadCount = 0;
  let selectedCount = 0;
  mice.forEach((mouse, mouseIndex) => {
    if (mouse.alive) {
      aliveCount += 1;
      if (selectedKeys.has(selectionKey(groupId, mouseIndex))) selectedCount += 1;
    } else {
      deadCount += 1;
    }
  });

  return {
    groupId,
    strain: (group.mouse_strain || '').trim(),
    plateRows,
    cellBySlot,
    aliveCount,
    deadCount,
    selectedCount,
  };
}

export default {
  name: 'TiterInstrumentOrderDialogs',
  components: {
    ElButton,
    ElDialog,
    ElEmpty,
    ElTable,
    ElTableColumn,
    ElTag,
    MouseRegistryDialog,
  },
  data() {
    return {
      plateColumnList: PLATE_COLUMN_LIST,
      titerOrder: null,
      canEditInstrument: false,
      leftClickBusy: false,

      flowListVisible: false,
      flowListLoading: false,
      flowListItems: [],

      wizardVisible: false,
      groupsLoading: false,
      savingRegistry: false,
      confirming: false,
      mouseGroups: [],
      selectedKeys: new Set(),
      mouseRegistryVisible: false,
      mouseRegistryEditingRow: null,

      cellDragActive: false,
      cellDragGroupId: '',
      cellDragStart: '',
      cellDragEnd: '',
      cellDragSelectMode: true,
    };
  },
  computed: {
    identityFields() {
      const order = this.titerOrder || {};
      return IDENTITY_FIELDS.map((field) => ({
        label: field.label,
        value: field.kind === 'number'
          ? (order[field.key] ?? 0)
          : (order[field.key] || '—'),
      }));
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
    cellDragPreviewSet() {
      if (!this.cellDragActive || !this.cellDragStart) return new Set();
      return new Set(mouseSlotsInRect(this.cellDragStart, this.cellDragEnd || this.cellDragStart));
    },
    plateGroups() {
      return this.mouseGroups
        .map((group) => buildPlateGroup(group, this.selectedKeys))
        .filter(Boolean);
    },
    selectionSummary() {
      return this.plateGroups.reduce(
        (acc, group) => {
          acc.alive += group.aliveCount;
          acc.dead += group.deadCount;
          acc.selected += group.selectedCount;
          return acc;
        },
        { alive: 0, dead: 0, selected: 0 },
      );
    },
  },
  beforeUnmount() {
    this.teardownCellDragListeners();
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

    handleWizardOpen() {
      this.selectedKeys = new Set();
      this.resetCellDrag();
      this.loadMouseGroups();
    },
    onWizardClosed() {
      this.teardownCellDragListeners();
      this.resetCellDrag();
      this.mouseGroups = [];
      this.selectedKeys = new Set();
      this.mouseRegistryVisible = false;
      this.mouseRegistryEditingRow = null;
      this.savingRegistry = false;
      this.confirming = false;
    },
    loadMouseGroups() {
      const experimentId = (this.titerOrder?.experiment_id || '').trim();
      if (!experimentId) {
        this.mouseGroups = [];
        ElMessage.warning('缺少实验 ID，无法加载小鼠分组');
        return;
      }
      this.groupsLoading = true;
      fetchMouseGroups(experimentId)
        .then((data) => {
          this.mouseGroups = data?.items || [];
          this.syncDefaultSelection();
        })
        .catch((error) => notifyApiError(error, { messages: { default: '加载小鼠分组失败' } }))
        .finally(() => {
          this.groupsLoading = false;
        });
    },
    syncDefaultSelection() {
      const next = new Set();
      for (const group of this.mouseGroups) {
        const groupId = (group.group_id || '').trim();
        if (!groupId) continue;
        miceInGroup(group).forEach((mouse, mouseIndex) => {
          if (mouse.alive) next.add(selectionKey(groupId, mouseIndex));
        });
      }
      this.selectedKeys = next;
    },
    isSelected(groupId, mouseIndex) {
      return mouseIndex >= 0 && this.selectedKeys.has(selectionKey(groupId, mouseIndex));
    },
    wellCellClass(groupId, cell) {
      const selected = !!(cell.no && cell.alive && this.isSelected(groupId, cell.mouseIndex));
      const preview = !!(
        cell.slotNo
        && this.cellDragActive
        && this.cellDragGroupId === groupId
        && this.cellDragPreviewSet.has(cell.slotNo)
      );
      return {
        'is-alive': !!(cell.no && cell.alive),
        'is-selected': selected,
        'is-dead': !!(cell.no && !cell.alive),
        'is-empty': !cell.no,
        'is-drag-add': preview && this.cellDragSelectMode,
        'is-drag-remove': preview && !this.cellDragSelectMode,
      };
    },
    cellTitle(cell) {
      if (!cell.no) return '';
      return cell.alive ? cell.no : `${cell.no}（死亡）`;
    },
    findCellBySlot(groupId, slotNo) {
      const group = this.plateGroups.find((item) => item.groupId === groupId);
      return group?.cellBySlot.get(slotNo) || null;
    },
    resetCellDrag() {
      this.cellDragActive = false;
      this.cellDragGroupId = '';
      this.cellDragStart = '';
      this.cellDragEnd = '';
      this.cellDragSelectMode = true;
    },
    teardownCellDragListeners() {
      document.removeEventListener('mouseup', this.onCellDragEnd);
    },
    onCellMouseDown(groupId, cell, event) {
      if (!cell.no || !cell.alive || event.button !== 0) return;
      this.teardownCellDragListeners();
      this.cellDragGroupId = groupId;
      this.cellDragStart = cell.slotNo;
      this.cellDragEnd = cell.slotNo;
      // 起点已选 → 本次划选取消；起点未选 → 本次划选选中
      this.cellDragSelectMode = !this.isSelected(groupId, cell.mouseIndex);
      this.cellDragActive = true;
      document.addEventListener('mouseup', this.onCellDragEnd);
    },
    onCellMouseEnter(groupId, cell) {
      if (!this.cellDragActive || this.cellDragGroupId !== groupId || !cell.slotNo) return;
      this.cellDragEnd = cell.slotNo;
    },
    onCellDragEnd() {
      if (!this.cellDragActive) return;
      const groupId = this.cellDragGroupId;
      const start = this.cellDragStart;
      const end = this.cellDragEnd || start;
      const selectMode = this.cellDragSelectMode;
      this.teardownCellDragListeners();
      this.resetCellDrag();
      if (!groupId || !start) return;

      const next = new Set(this.selectedKeys);
      for (const slot of mouseSlotsInRect(start, end)) {
        const cell = this.findCellBySlot(groupId, slot);
        if (!cell?.no || !cell.alive || cell.mouseIndex < 0) continue;
        const key = selectionKey(groupId, cell.mouseIndex);
        if (selectMode) next.add(key);
        else next.delete(key);
      }
      this.selectedKeys = next;
    },

    openMouseRegistryDialog(row) {
      this.mouseRegistryEditingRow = row;
      this.mouseRegistryVisible = true;
    },
    onMouseRegistryConfirm({ mouse_registry, mouse_no_list }) {
      const row = this.mouseRegistryEditingRow;
      if (!row) return;
      const experimentId = (this.titerOrder?.experiment_id || '').trim();
      if (!experimentId) {
        ElMessage.warning('缺少实验 ID');
        return;
      }
      this.savingRegistry = true;
      const previousCounts = new Map();
      for (const group of this.mouseGroups) {
        const groupId = (group.group_id || '').trim();
        if (!groupId) continue;
        previousCounts.set(groupId, miceInGroup(group).length);
      }
      saveMouseRegistry({
        experiment_id: experimentId,
        id: row.id,
        group_id: row.group_id,
        mouse_registry,
        mouse_no_list,
      })
        .then((updated) => {
          const index = this.mouseGroups.findIndex((item) => item.id === updated.id);
          if (index >= 0) {
            this.mouseGroups.splice(index, 1, { ...this.mouseGroups[index], ...updated });
          }
          this.reconcileSelectionAfterRegistryChange(previousCounts);
          ElMessage.success('鼠号信息已保存');
        })
        .catch((error) => notifyApiError(error, { messages: { default: '保存鼠号信息失败' } }))
        .finally(() => {
          this.savingRegistry = false;
        });
    },
    reconcileSelectionAfterRegistryChange(previousCounts = new Map()) {
      const next = new Set();
      for (const group of this.mouseGroups) {
        const groupId = (group.group_id || '').trim();
        if (!groupId) continue;
        const prevCount = previousCounts.get(groupId) || 0;
        miceInGroup(group).forEach((mouse, mouseIndex) => {
          if (!mouse.alive) return;
          const key = selectionKey(groupId, mouseIndex);
          // 保留原位已选；新增序号默认勾选
          if (this.selectedKeys.has(key) || mouseIndex >= prevCount) {
            next.add(key);
          }
        });
      }
      this.selectedKeys = next;
    },
    buildSelectionPayload() {
      const groups = [];
      for (const group of this.mouseGroups) {
        const groupId = (group.group_id || '').trim();
        if (!groupId) continue;
        const selected = miceInGroup(group)
          .filter((mouse, mouseIndex) => (
            mouse.alive && this.selectedKeys.has(selectionKey(groupId, mouseIndex))
          ))
          .map((mouse) => mouse.no);
        if (selected.length) {
          groups.push({ group_id: groupId, selected_mouse_nos: selected });
        }
      }
      return {
        experiment_id: this.titerOrder?.experiment_id || '',
        titer_order_id: this.titerOrder?.titer_order_id || '',
        project_code: this.titerOrder?.project_code || '',
        target_name: this.titerOrder?.target_name || '',
        groups,
      };
    },
    async handleConfirm() {
      if (this.confirming || this.savingRegistry || this.groupsLoading) return;
      if (this.selectionSummary.selected === 0) {
        try {
          await ElMessageBox.confirm(
            '当前未选择任何小鼠，可能仅补做对照组。是否继续？',
            '确认',
            { type: 'warning', confirmButtonText: '继续', cancelButtonText: '返回' },
          );
        } catch {
          return;
        }
      }
      this.confirming = true;
      try {
        sessionStorage.setItem(
          TITER_INSTRUMENT_WIZARD_DRAFT_KEY,
          JSON.stringify(this.buildSelectionPayload()),
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
            // KeepAlive 下同 prefill 需换 identity，否则不会重新灌板
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

<style lang="scss" scoped>
/* 青绿风格，整体偏浅、色条更鲜亮 */
$ink: #303133;
$slate: #606266;
$mist: #909399;
$line: #e4e7ed;
$wash: #f5f7fa;
$panel: #ffffff;
$accent-mid: #14b8a6;
$accent-deep: #0d9488;
$accent-soft: #e6fffa;
$drop: #f56c6c;

.tio-header {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding-right: 28px;
}

.tio-header-mark {
  flex-shrink: 0;
  width: 3px;
  height: 36px;
  margin-top: 2px;
  background: linear-gradient(180deg, #38bdf8 0%, #2dd4bf 55%, #14b8a6 100%);
  border-radius: 2px;
}

.tio-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  line-height: 1.4;
  color: $ink;
}

.tio-subtitle {
  margin: 4px 0 0;
  font-size: 12px;
  line-height: 1.45;
  color: $mist;
}

.tio-identity {
  padding: 8px 12px;
  margin-bottom: 14px;
  background: $wash;
  border: 1px solid #ebeef5;
  border-radius: 8px;
}

.tio-fields {
  display: grid;
  grid-template-columns:
    minmax(max-content, 1.2fr)
    minmax(max-content, 0.9fr)
    minmax(max-content, 1fr)
    minmax(max-content, 0.55fr)
    minmax(max-content, 1.3fr)
    minmax(max-content, 0.55fr)
    minmax(max-content, 0.55fr);
  gap: 8px 16px;
  align-items: start;
}

.tio-field {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.tio-field-k {
  font-size: 12px;
  font-weight: 400;
  color: $mist;
  white-space: nowrap;
}

.tio-field-v {
  font-size: 13px;
  font-weight: 500;
  line-height: 1.35;
  color: $ink;
  white-space: nowrap;
}

.tio-wizard-scroll {
  max-height: min(58vh, 600px);
  padding-right: 4px;
  overflow: auto;
  scrollbar-gutter: stable;
}

.tio-stage + .tio-stage {
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid #f0f2f5;
}

.tio-stage-head {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  margin-bottom: 12px;
}

.tio-stage-index {
  flex-shrink: 0;
  padding-top: 1px;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.2;
  color: $accent-mid;
  letter-spacing: 0.04em;
}

.tio-stage-copy {
  flex: 1;
  min-width: 0;
}

.tio-stage-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: $ink;
}

.tio-stage-desc {
  margin: 2px 0 0;
  font-size: 12px;
  color: $mist;
}

.tio-stage-metrics {
  display: flex;
  flex-shrink: 0;
  gap: 6px;
}

.tio-metric {
  min-width: 48px;
  padding: 4px 8px;
  text-align: center;
  background: $accent-soft;
  border: 1px solid rgb(45 212 191 / 28%);
  border-radius: 6px;

  &--mute {
    background: $panel;
    border-color: $line;

    .tio-metric-n {
      color: $slate;
    }
  }
}

.tio-metric-n {
  display: block;
  font-size: 15px;
  font-weight: 700;
  line-height: 1.1;
  color: $accent-deep;
}

.tio-metric-l {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  color: $mist;
}

.tio-board-hint {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 16px;
  align-items: center;
  margin-bottom: 10px;
}

.tio-hint-item {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  font-size: 12px;
  color: $slate;
}


.tio-hint-swatch {
  width: 14px;
  height: 14px;
  border-radius: 3px;

  &--pick {
    background: #f0fdfa;
    box-shadow: inset 0 0 0 1px rgb(20 184 166 / 40%);
  }

  &--drop {
    background: #fef0f0;
    box-shadow: inset 0 0 0 1px rgb(245 108 108 / 45%);
  }
}

.tio-panel {
  overflow: hidden;
  background: $panel;
  border: 1px solid $line;
  border-radius: 8px;
}

.tio-table {
  --el-table-border-color: #ebeef5;
  --el-table-header-bg-color: #fafafa;
  --el-table-row-hover-bg-color: #f0fdfa;

  :deep(.el-table__inner-wrapper::before),
  :deep(.el-table__inner-wrapper::after),
  :deep(.el-table__border-left-patch),
  :deep(.el-table__border-bottom-patch) {
    display: none !important;
  }

  :deep(.el-table__body tr:last-child > td.el-table__cell) {
    border-bottom: none !important;
  }

  :deep(.el-table__header th) {
    font-size: 12px;
    font-weight: 500;
    color: $slate;
  }

  :deep(.el-table__body td) {
    color: $ink;
  }
}

.tio-table--click :deep(.el-table__row) {
  cursor: pointer;
}

.tio-table--click :deep(.el-table__body tr:hover > td) {
  background: #f0fdfa !important;
}

.tio-link {
  max-width: 100%;
  padding: 0;
  overflow: hidden;
  font-size: 12px;
  font-weight: 500;
  color: $accent-deep;
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
  background: none;
  border: none;

  &:hover {
    color: $accent-mid;
    text-decoration: underline;
  }
}

.tio-empty {
  padding: 16px 0 8px;
}

.tio-board + .tio-board {
  margin-top: 14px;
}

.tio-board-bar {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.tio-board-who {
  display: flex;
  gap: 8px;
  align-items: baseline;
  min-width: 0;
}

.tio-board-gid {
  font-size: 13px;
  font-weight: 600;
  color: $ink;
}

.tio-board-strain {
  overflow: hidden;
  font-size: 12px;
  color: $mist;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tio-board-ratio {
  font-size: 12px;
  font-weight: 600;
  color: $accent-deep;
}

.tio-board-ratio-sep {
  margin: 0 2px;
  font-weight: 400;
  color: #c0c4cc;
}

.tio-plate-wrap {
  overflow-x: auto;
  background: #fafbfc;
  border: 1px solid $line;
  border-radius: 8px;
  user-select: none;
}

.tio-plate {
  width: 100%;
  min-width: 600px;
  border-collapse: separate;
  border-spacing: 0;
  table-layout: fixed;

  th,
  td {
    border-right: 1px solid #ebeef5;
    border-bottom: 1px solid #ebeef5;
  }

  th:last-child,
  td:last-child {
    border-right: none;
  }

  tr:last-child th,
  tr:last-child td {
    border-bottom: none;
  }
}

.tio-plate-corner,
.tio-plate-row {
  width: 36px;
  background: #f5f7fa;
}

.tio-plate-col,
.tio-plate-row {
  height: 28px;
  font-size: 11px;
  font-weight: 500;
  color: $mist;
  text-align: center;
  background: #f5f7fa;
}

.tio-well {
  height: 52px;
  padding: 0 3px;
  text-align: center;
  vertical-align: middle;
  background: transparent;
  transition: background-color 0.12s ease, box-shadow 0.12s ease;
  user-select: none;

  &.is-alive {
    cursor: pointer;
    background: $panel;

    &:hover:not(.is-selected):not(.is-drag-add):not(.is-drag-remove) {
      background: #f0fdfa;
    }
  }

  /* 已选 */
  &.is-selected {
    background: $accent-soft;
    box-shadow: inset 0 0 0 1.5px rgb(20 184 166 / 50%);

    .tio-well-text {
      font-weight: 600;
      color: $accent-deep;
    }
  }

  /* 划选加入预览：比已选更浅 */
  &.is-drag-add {
    background: #f3fffc;
    box-shadow: inset 0 0 0 1.5px rgb(45 212 191 / 40%);
  }

  &.is-drag-remove {
    background: #fef0f0;
    box-shadow: inset 0 0 0 1.5px rgb(245 108 108 / 55%);

    .tio-well-text {
      font-weight: 600;
      color: $drop;
    }
  }

  &.is-dead {
    cursor: not-allowed;
    background: #f5f7fa;

    .tio-well-text {
      color: #c0c4cc;
      text-decoration: line-through;
    }
  }

  &.is-empty {
    background: rgb(250 251 252 / 80%);
  }
}

.tio-well-text {
  display: block;
  overflow: hidden;
  font-size: 11px;
  line-height: 1.2;
  color: $slate;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tio-footer {
  display: flex;
  gap: 12px;
  align-items: center;
  width: 100%;
}

.tio-footer-hint {
  margin-right: auto;
  font-size: 12px;
  color: $mist;
}

.tio-footer-actions {
  display: flex;
  flex-shrink: 0;
  gap: 8px;
}

.tio-btn {
  min-width: 96px;
  height: 32px;
}
</style>

<style lang="scss">
.tio-dialog {
  border-radius: 8px !important;
  overflow: hidden;

  .el-dialog__header {
    padding: 16px 20px 12px;
    margin-right: 0;
    border-bottom: 1px solid #f0f2f5;
  }

  .el-dialog__body {
    padding: 14px 20px 10px;
  }

  .el-dialog__footer {
    padding: 12px 20px 16px;
    background: #fff !important;
    border-top: 1px solid #f0f2f5;
  }

  .el-dialog__headerbtn {
    top: 14px;
    right: 14px;
  }

  /* 浅绿主按钮，比原先墨绿更亮 */
  .tio-btn-accent {
    --el-button-bg-color: #14b8a6;
    --el-button-border-color: #14b8a6;
    --el-button-hover-bg-color: #0d9488;
    --el-button-hover-border-color: #0d9488;
    --el-button-active-bg-color: #0f766e;
    --el-button-active-border-color: #0f766e;
  }
}
</style>
