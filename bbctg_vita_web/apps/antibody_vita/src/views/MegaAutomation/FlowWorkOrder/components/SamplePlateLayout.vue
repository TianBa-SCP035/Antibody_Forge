<template>
  <section class="sample-plate-layout">
    <div class="panel-head">
      <div class="panel-head-left">
        <el-icon class="head-icon"><Files /></el-icon>
        <span class="panel-title">{{ standalone ? (plateTitle || '样本板') : '样本板布局' }}</span>
      </div>
      <PlateTabSwitch
        v-if="!standalone"
        :model-value="modelValue"
        :count="plateCount"
        prefix="样本板"
        @update:model-value="$emit('update:modelValue', $event)"
      />
    </div>

    <div class="plate-current-bar">
      <!-- 工单编辑：只展示；铺板解锁后与细胞板一致，条码可录入 -->
      <span
        v-if="!standalone || disabled"
        class="current-info"
        :class="{ 'is-empty': !hasBarcode }"
        :title="currentBarcode"
      >{{ currentBarcode }}</span>
      <el-input
        v-else
        v-model="plate.barcode"
        size="small"
        class="barcode-input"
        placeholder="请输入样本板条码"
      />
      <div class="legend">
        <span v-for="type in wellTypeCycle" :key="'lg-' + type" class="legend-item">
          <i class="legend-dot" :class="'well-' + type.toLowerCase()"></i>
          {{ wellTypeLabel(type) }}
        </span>
      </div>
    </div>

    <div class="well-editor">
      <span class="well-editor-no">{{ editorWellLabel }}</span>
      <el-select
        v-model="wellDraft.content_type"
        size="small"
        class="well-type-select"
        :disabled="disabled || wellDragActive"
        :placeholder="wellDraft.content_type ? undefined : '多种类型'"
        @change="applyWellDraft"
      >
        <el-option
          v-for="type in wellTypeCycle"
          :key="'wt-' + type"
          :label="wellTypeLabel(type)"
          :value="type"
        />
      </el-select>
      <el-select
        v-if="isPcRefType(wellDraft.content_type)"
        v-model="wellDraft.pc_id"
        size="small"
        clearable
        filterable
        class="well-value-input"
        :disabled="disabled || wellDragActive"
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
        :disabled="disabled || wellDragActive"
        placeholder="样本编码（批量同步）"
        @change="applyWellDraft"
      />
      <span v-else-if="wellDraft.content_type" class="well-editor-static">
        {{ wellTypeLabel(wellDraft.content_type) }} 孔无需编码
      </span>
      <span v-if="!standalone" class="well-editor-tip">提示：拖拽划选；右键批量切换类型</span>
    </div>

    <div class="plate-grid-wrap">
      <table class="plate-grid">
        <thead>
          <tr>
            <th class="corner"></th>
            <th v-for="column in 12" :key="'col-' + column">{{ column }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="rowLabel in plateRows" :key="'row-' + rowLabel">
            <th class="row-head">{{ rowLabel }}</th>
            <td
              v-for="well in rowWells(plate, rowLabel)"
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
              <el-icon
                v-if="warningWellSet.has(well.well_no)"
                class="well-warning-mark"
                aria-label="可选内容未填写"
              >
                <WarningFilled />
              </el-icon>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script>
import { Files, WarningFilled } from '@element-plus/icons-vue';
import {
  ElIcon,
  ElInput,
  ElOption,
  ElSelect,
} from 'element-plus';

import {
  formatWellSelectionLabel,
  isPcRefType,
  isSampleType,
  normalizedWells,
  PLATE_ROWS,
  rowWells,
  WELL_TYPE_CYCLE,
  wellPcInfoType,
  wellTypeLabel,
  wellsInRect,
} from '../flowWorkOrderModel';
import PlateTabSwitch from './PlateTabSwitch.vue';

export default {
  name: 'MegaSamplePlateLayout',
  components: {
    ElIcon,
    ElInput,
    ElOption,
    ElSelect,
    Files,
    PlateTabSwitch,
    WarningFilled,
  },
  props: {
    disabled: Boolean,
    modelValue: { type: String, default: '0' },
    pcInfos: { type: Array, default: () => [] },
    plate: { type: Object, required: true },
    plateCount: { type: Number, default: 0 },
    plateTitle: { type: String, default: '' },
    standalone: Boolean,
    warningWellNos: { type: Array, default: () => [] },
  },
  emits: ['update:modelValue'],
  data() {
    return {
      plateRows: PLATE_ROWS,
      selectedWellNos: [],
      wellClickToggle: false,
      wellDraft: { content_type: '', pc_id: null, sample_code: '' },
      wellDragActive: false,
      wellDragEnd: '',
      wellDragFrozenLabel: null,
      wellDragStart: '',
      wellTypeCycle: WELL_TYPE_CYCLE,
    };
  },
  computed: {
    hasBarcode() {
      return !!String(this.plate?.barcode || '').trim();
    },
    currentBarcode() {
      return this.hasBarcode ? String(this.plate.barcode).trim() : '请输入样本板条码';
    },
    selectedWellSet() {
      return new Set(this.selectedWellNos);
    },
    selectedWells() {
      if (!this.selectedWellNos.length) return [];
      return normalizedWells(this.plate).filter((well) => this.selectedWellSet.has(well.well_no));
    },
    wellDragPreviewSet() {
      if (!this.wellDragActive || !this.wellDragStart) return new Set();
      return new Set(wellsInRect(this.wellDragStart, this.wellDragEnd || this.wellDragStart));
    },
    warningWellSet() {
      return new Set(this.warningWellNos);
    },
    editorWells() {
      if (this.selectedWellNos.length) return this.selectedWells;
      const a01 = normalizedWells(this.plate).find((well) => well.well_no === 'A01');
      return a01 ? [a01] : [];
    },
    editorWellLabel() {
      if (this.wellDragFrozenLabel != null) return this.wellDragFrozenLabel;
      return this.selectedWellNos.length
        ? formatWellSelectionLabel(this.selectedWellNos)
        : 'A01';
    },
  },
  watch: {
    modelValue() {
      this.clearWellSelection();
    },
    plate() {
      this.clearWellSelection();
    },
  },
  mounted() {
    this.syncWellDraftFromEditor();
  },
  beforeUnmount() {
    this.teardownWellDragListeners();
  },
  methods: {
    isPcRefType,
    isSampleType,
    rowWells,
    wellTypeLabel,
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
      const types = [...new Set(
        wells.map((well) => String(well.content_type || 'SAMPLE').toUpperCase()),
      )];
      const contentType = types.length === 1 ? types[0] : '';
      const pcIds = contentType && isPcRefType(contentType)
        ? [...new Set(
            wells
              .map((well) => (well.pc_id == null || well.pc_id === '' ? null : String(well.pc_id)))
              .filter(Boolean),
          )]
        : [];
      const sampleCodes = contentType === 'SAMPLE'
        ? [...new Set(wells.map((well) => String(well.sample_code || '').trim()).filter(Boolean))]
        : [];
      this.wellDraft = {
        content_type: contentType,
        pc_id: pcIds.length === 1 ? pcIds[0] : null,
        sample_code: sampleCodes.length === 1 ? sampleCodes[0] : '',
      };
    },
    applyWellDraft() {
      const wells = this.editorWells;
      if (!wells.length || !this.wellDraft.content_type) return;
      const { content_type: contentType, pc_id: pcId, sample_code: sampleCode } = this.wellDraft;
      wells.forEach((well) => {
        well.content_type = contentType;
        this.onWellTypeChange(well);
        if (isPcRefType(contentType)) well.pc_id = pcId ?? null;
        if (isSampleType(contentType)) well.sample_code = sampleCode || '';
      });
    },
    onWellMouseDown(well, event) {
      if (this.disabled || event.button !== 0) return;
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
      if (this.wellDragActive) this.wellDragEnd = well.well_no;
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
      if (this.disabled) return;
      if (!this.selectedWellSet.has(well.well_no)) {
        this.selectedWellNos = [well.well_no];
        this.syncWellDraftFromEditor();
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
      if (!isPcRefType(type)) {
        well.pc_id = null;
      } else if (well.pc_id != null) {
        const pc = this.pcInfoById(well.pc_id);
        if (!pc || pc.pc_type !== wellPcInfoType(type)) well.pc_id = null;
      }
      if (type !== 'SAMPLE') well.sample_code = '';
    },
    pcInfoById(pcId) {
      if (pcId == null || pcId === '') return null;
      return this.pcInfos.find((pc) => pc.pc_id === String(pcId)) || null;
    },
    pcInfosForWellType(wellType) {
      const pcType = wellPcInfoType(wellType);
      return pcType ? this.pcInfos.filter((pc) => pc.pc_type === pcType) : [];
    },
    wellCellText(well) {
      const type = String(well.content_type || 'SAMPLE').toUpperCase();
      if (type === 'SAMPLE') return well.sample_code || '';
      return type === 'BLANK' ? '' : wellTypeLabel(type);
    },
    wellTooltip(well) {
      const type = String(well.content_type || 'SAMPLE').toUpperCase();
      const parts = [well.well_no, wellTypeLabel(type)];
      if (type === 'SAMPLE' && well.sample_code) {
        parts.push(well.sample_code);
      } else if (isPcRefType(type)) {
        const pcName = this.pcInfoById(well.pc_id)?.pc_name;
        if (pcName) parts.push(pcName);
      }
      if (this.warningWellSet.has(well.well_no)) parts.push('可选内容未填写');
      return `${parts.join(' · ')} · 拖拽划选 · 右键切换类型`;
    },
  },
};
</script>

<style lang="scss" scoped>
$primary: #409eff;
$title-color: #1f2937;
$label-color: #606266;
$muted-color: #909399;

.plate-current-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: nowrap;
  margin-bottom: 10px;
}

.current-info {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  font-size: 13px;
  font-weight: 600;
  color: $title-color;
  text-overflow: ellipsis;
  white-space: nowrap;

  &.is-empty {
    font-weight: 400;
    color: $muted-color;
  }
}

.barcode-input {
  flex: 1;
  max-width: 280px;
}

.legend {
  display: flex;
  flex-shrink: 0;
  flex-wrap: nowrap;
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

.well-editor-static,
.well-editor-tip {
  font-size: 12px;
  color: $muted-color;
}

.well-editor-tip {
  margin-left: auto;
}

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

  .corner,
  .row-head {
    width: 26px;
  }

  .row-head {
    font-size: 11px;
    font-weight: 600;
    color: $label-color;
    background: #f5f7fa;
  }
}

.well-cell {
  position: relative;
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

  &.is-drag-preview:not(.is-selected) {
    box-shadow: inset 0 0 0 1px rgb(111 183 255 / 80%);
  }

  &.is-selected {
    box-shadow: inset 0 0 0 1px rgb(62 158 255 / 80%);
  }
}

.well-warning-mark {
  position: absolute;
  top: 2px;
  right: 2px;
  font-size: 13px;
  color:rgb(240, 198, 121);
  pointer-events: none;
}
</style>
