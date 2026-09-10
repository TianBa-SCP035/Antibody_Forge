<template>
  <el-dialog
    :model-value="modelValue"
    width="960px"
    append-to-body
    destroy-on-close
    align-center
    class="tio-dialog tio-dialog--wizard"
    @update:model-value="$emit('update:modelValue', $event)"
    @open="handleWizardOpen"
    @closed="onWizardClosed"
  >
    <template #header>
      <div class="tio-header">
        <div class="tio-header-mark" aria-hidden="true" />
        <div class="tio-header-text">
          <h3 class="tio-title">{{ title }}</h3>
          <p class="tio-subtitle">{{ subtitle }}</p>
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
        <span class="tio-footer-hint">{{ footerHint }}</span>
        <div class="tio-footer-actions">
          <el-button class="tio-btn" @click="$emit('update:modelValue', false)">取消</el-button>
          <el-button
            type="primary"
            class="tio-btn tio-btn-accent"
            :loading="busy"
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
} from 'element-plus';

import { notifyApiError } from '#/api/errors';
import { fetchMouseGroups, saveMouseRegistry } from '#/api/serum';

import MouseRegistryDialog from '../shared/MouseRegistryDialog.vue';

import {
  PLATE_COLUMN_LIST,
  buildPlateGroup,
  miceInGroup,
  mouseSlotsInRect,
  selectionKey,
  titerOrderIdentityFields,
} from './titerMouseSelect';

export default {
  name: 'TiterMouseSelectWizard',
  components: {
    ElButton,
    ElDialog,
    ElEmpty,
    ElTable,
    ElTableColumn,
    MouseRegistryDialog,
  },
  props: {
    modelValue: { type: Boolean, default: false },
    titerOrder: { type: Object, default: null },
    title: { type: String, default: '上机工单' },
    subtitle: { type: String, default: '确认鼠号死活，勾选待测个体后进入流式工单预填' },
    footerHint: { type: String, default: '未选小鼠也可继续（如仅补对照）' },
    requireSelection: { type: Boolean, default: false },
    confirming: { type: Boolean, default: false },
  },
  emits: ['update:modelValue', 'confirm'],
  data() {
    return {
      plateColumnList: PLATE_COLUMN_LIST,
      groupsLoading: false,
      savingRegistry: false,
      confirmBusy: false,
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
      return titerOrderIdentityFields(this.titerOrder);
    },
    busy() {
      return this.confirming || this.confirmBusy;
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
      this.confirmBusy = false;
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
        cage_position: this.titerOrder?.cage_position || '',
        groups,
        mouseGroups: this.mouseGroups,
      };
    },
    async handleConfirm() {
      if (this.busy || this.savingRegistry || this.groupsLoading) return;
      if (this.selectionSummary.selected === 0) {
        if (this.requireSelection) {
          ElMessage.warning('请至少选择一只小鼠');
          return;
        }
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
      this.confirmBusy = true;
      try {
        this.$emit('confirm', this.buildSelectionPayload());
      } finally {
        this.confirmBusy = false;
      }
    },
  },
};
</script>

<style lang="scss" scoped src="./titerInstrumentOrder.scss"></style>
<style lang="scss" src="./titerInstrumentOrderDialog.scss"></style>
