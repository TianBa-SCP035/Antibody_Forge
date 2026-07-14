<template>
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
          :model-value="activeCellPlate" @update:model-value="setActiveCellPlate"
          class="panel flow-editor-panel"
          :plates="order.cell_plates"
          :disabled="fieldDisabled"
          :cell-type-options="cellTypeOptions"
          :species-options="speciesOptions"
          :has-field-error="hasFieldError"
          @add="addCellPlate"
          @remove="removeCellPlate"
          @barcode-focus="(index, value) => $emit('barcode-focus', index, value)"
          @barcode-change="(index, value) => $emit('barcode-change', index, value)"
          @reordered="$emit('columns-reordered', $event)"
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
          :model-value="activeSamplePlate" @update:model-value="setActiveSamplePlate"
          class="panel viz-panel flow-editor-panel"
          :plate="selectedSamplePlate"
          :plate-count="order.sample_plates.length"
          :pc-infos="pcInfos"
          :disabled="fieldDisabled"
          :warning-well-nos="warningWellNos"
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
              :model-value="activeCellPlate" @update:model-value="setActiveCellPlate"
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
</template>

<script>
import { ArrowDown, ArrowRight, Check, CircleCheck, Delete, Grid, Menu, Plus } from '@element-plus/icons-vue';
import {
  ElButton,
  ElIcon,
  ElInput,
  ElOption,
  ElPopover,
  ElSelect,
  ElTable,
  ElTableColumn,
} from 'element-plus';

import {
  cellKey,
  cellPlateBarcode,
  CELL_TYPE_OPTIONS,
  createDefaultColumns,
  createDefaultSamplePlate,
  createLocalPcId,
  isCellSelected,
  PC_INFO_TYPE_OPTIONS,
  SECONDARY_ANTIBODY_OPTIONS,
  selectedCountInPlate,
  SPECIES_OPTIONS,
} from '../flowWorkOrderModel';
import CellPlateEditor from './CellPlateEditor.vue';
import PlateTabSwitch from './PlateTabSwitch.vue';
import SamplePlateLayout from './SamplePlateLayout.vue';

export default {
  name: 'MegaFlowWorkOrderEditorTab',
  components: {
    ArrowDown,
    ArrowRight,
    Check,
    CircleCheck,
    CellPlateEditor,
    Delete,
    ElButton,
    ElIcon,
    ElInput,
    ElOption,
    ElPopover,
    ElSelect,
    ElTable,
    ElTableColumn,
    Grid,
    Menu,
    Plus,
    PlateTabSwitch,
    SamplePlateLayout,
  },
  props: {
    activeCellPlate: { type: String, default: '0' },
    activeSamplePlate: { type: String, default: '0' },
    defaultCellColumns: { type: Array, default: () => [] },
    defaultSampleWells: { type: Array, default: () => [] },
    fieldDisabled: Boolean,
    order: { type: Object, required: true },
    validationIssues: { type: Array, default: () => [] },
    warningWellNos: { type: Array, default: () => [] },
  },
  emits: [
    'update:activeCellPlate',
    'update:activeSamplePlate',
    'barcode-change',
    'barcode-focus',
    'columns-reordered',
  ],
  setup() {
    return {
      cellKey,
      cellPlateBarcode,
      isCellSelected,
      selectedCountInPlate,
    };
  },
  data() {
    return {
      cellPickerExpanded: {},
      activeCellPickerRowKey: '',
      secondaryAntibodyOptions: SECONDARY_ANTIBODY_OPTIONS,
      speciesOptions: SPECIES_OPTIONS,
      cellTypeOptions: CELL_TYPE_OPTIONS,
      pcInfoTypeOptions: PC_INFO_TYPE_OPTIONS,
      samplePlateSortable: null,
      samplePlateSortableInitToken: 0,
    };
  },
  computed: {
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
  watch: {
    fieldDisabled(value) {
      if (this.samplePlateSortable) {
        this.samplePlateSortable.option('disabled', value);
      }
    },
    'order.sample_plates.length'() {
      this.scheduleSamplePlateSortableInit();
    },
  },
  mounted() {
    this.scheduleSamplePlateSortableInit();
  },
  beforeUnmount() {
    this.samplePlateSortableInitToken += 1;
    this.destroySamplePlateSortable();
  },
  methods: {
    setActiveSamplePlate(value) {
      this.$emit('update:activeSamplePlate', String(value));
    },
    setActiveCellPlate(value) {
      this.$emit('update:activeCellPlate', String(value));
    },
    samplePlateRowKey(row) {
      return row._rowKey;
    },
    hasFieldError(field) {
      if (!field || !this.validationIssues.length) return false;
      return this.validationIssues.some(
        (item) => item.field === field || String(item.field || '').startsWith(`${field}.`),
      );
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
        this.setActiveSamplePlate(index);
        this.$refs.samplePlateLayout?.clearWellSelection();
      }
    },
    samplePlateRowClass({ row }) {
      const index = this.order.sample_plates.indexOf(row);
      return this.activeSamplePlate === String(index) ? 'is-active-row' : '';
    },
    addSamplePlate() {
      this.order.sample_plates.push(this.defaultSamplePlate());
      this.setActiveSamplePlate(this.order.sample_plates.length - 1);
    },
    removeSamplePlate(index) {
      this.order.sample_plates.splice(index, 1);
      if (Number(this.activeSamplePlate) >= this.order.sample_plates.length) {
        this.setActiveSamplePlate(Math.max(0, this.order.sample_plates.length - 1));
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
        this.setActiveSamplePlate(newIndex);
      } else if (oldIndex < activeIdx && newIndex >= activeIdx) {
        this.setActiveSamplePlate(activeIdx - 1);
      } else if (oldIndex > activeIdx && newIndex <= activeIdx) {
        this.setActiveSamplePlate(activeIdx + 1);
      }
    },
    addCellPlate() {
      this.order.cell_plates.push({ barcode: '', columns: this.defaultColumns() });
      this.setActiveCellPlate(this.order.cell_plates.length - 1);
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
      const survivingAliases = new Set(
        plates.map((plate, plateIndex) => this.cellPlateBarcode(plate, plateIndex)),
      );

      this.order.sample_plates.forEach((samplePlate) => {
        const keys = Array.isArray(samplePlate.cell_keys) ? samplePlate.cell_keys : [];
        samplePlate.cell_keys = keys.flatMap((key) => {
          const remap = aliasRemaps.find(({ from }) => key.startsWith(`${from}|`));
          if (remap) return [`${remap.to}|${key.slice(remap.from.length + 1)}`];
          if (
            removedAlias
            && !survivingAliases.has(removedAlias)
            && key.startsWith(`${removedAlias}|`)
          ) {
            return [];
          }
          return [key];
        });
      });
      this.pruneEmptyCellRefs();
      if (Number(this.activeCellPlate) >= plates.length) {
        this.setActiveCellPlate(Math.max(0, plates.length - 1));
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
  },
};
</script>

<style scoped lang="scss">
$primary: #409eff;
$title-color: #303133;
$label-color: #606266;
$muted-color: #909399;

.empty-hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: $muted-color;
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

  &.is-invalid-control {
    box-shadow: 0 0 0 1px #f56c6c inset;
    background: #fff;
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

@media (max-width: 1180px) {
  .editor-layout {
    grid-template-columns: minmax(0, 1fr);
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
