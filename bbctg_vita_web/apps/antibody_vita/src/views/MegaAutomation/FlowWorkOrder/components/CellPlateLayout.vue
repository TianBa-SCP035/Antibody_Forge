<template>
  <section class="cell-plate-layout">
    <div class="panel-head">
      <div class="panel-head-left">
        <el-icon class="head-icon"><Menu /></el-icon>
        <span class="panel-title">{{ plateTitle || '细胞板' }}</span>
      </div>
    </div>

    <div class="plate-current-bar">
      <span
        v-if="disabled"
        class="current-info"
        :class="{ 'is-empty': !hasBarcode }"
        :title="barcodeLabel"
      >{{ barcodeLabel }}</span>
      <el-input
        v-else
        v-model="plate.barcode"
        size="small"
        class="barcode-input"
        placeholder="请输入细胞板条码"
        @focus="$emit('barcode-focus', plateIndex, plate.barcode)"
        @change="$emit('barcode-change', plateIndex, plate.barcode)"
      />
      <div class="legend">
        <span class="legend-item"><i class="legend-mark is-normal"></i>正常</span>
        <span class="legend-item"><i class="legend-mark is-tumor"></i>肿瘤</span>
        <span class="legend-item"><i class="legend-mark"></i>空列</span>
      </div>
    </div>

    <div class="cell-board">
      <div class="cell-board-cols">
        <div
          v-for="col in columns"
          :key="'col-' + col.column_no"
          class="cell-capsule"
          :class="capsuleClass(col)"
        >
          <span class="capsule-no">{{ col.column_no }}</span>

          <div class="capsule-bar-wrap" :title="columnTooltip(col)">
            <span class="capsule-tube">
              <span class="capsule-liquid" aria-hidden="true"></span>
            </span>
          </div>

          <div class="capsule-foot">
            <template v-if="isColumnFilled(col)">
              <span class="capsule-name" :title="columnCellName(col)">{{ columnCellName(col) }}</span>
              <span class="capsule-species" :title="ellipsisTitle(col.species)">{{ columnSpecies(col) }}</span>
              <span class="capsule-count" :title="ellipsisTitle(col.cell_count)">{{
                columnCellCount(col) || '—'
              }}</span>
            </template>
            <span v-else class="capsule-empty">空</span>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script>
import { Menu } from '@element-plus/icons-vue';
import { ElIcon, ElInput } from 'element-plus';

export default {
  name: 'MegaCellPlateLayout',
  components: {
    ElIcon,
    ElInput,
    Menu,
  },
  props: {
    disabled: Boolean,
    plate: { type: Object, required: true },
    plateIndex: { type: Number, default: 0 },
    plateTitle: { type: String, default: '' },
  },
  emits: ['barcode-change', 'barcode-focus'],
  computed: {
    columns() {
      return Array.isArray(this.plate?.columns) ? this.plate.columns : [];
    },
    hasBarcode() {
      return !!String(this.plate?.barcode || '').trim();
    },
    barcodeLabel() {
      return this.hasBarcode ? String(this.plate.barcode).trim() : '请输入细胞板条码';
    },
  },
  methods: {
    isColumnFilled(column) {
      return !!String(column?.cell_name || '').trim();
    },
    isTumorType(column) {
      return String(column?.cell_type || '').trim() === '肿瘤';
    },
    capsuleClass(column) {
      const filled = this.isColumnFilled(column);
      return {
        'is-filled': filled,
        'is-empty': !filled,
        'is-tumor': filled && this.isTumorType(column),
        'is-normal': filled && !this.isTumorType(column),
      };
    },
    columnCellName(column) {
      return String(column?.cell_name || '').trim();
    },
    columnSpecies(column) {
      return String(column?.species || '').trim() || '—';
    },
    columnCellCount(column) {
      return String(column?.cell_count || '').trim();
    },
    /** 仅有真实内容时挂 title，占位「—」不提示 */
    ellipsisTitle(value) {
      const text = String(value || '').trim();
      return text || undefined;
    },
    columnTooltip(column) {
      if (!this.isColumnFilled(column)) return `第 ${column.column_no} 列 · 空`;
      const parts = [`第 ${column.column_no} 列`, column.cell_name];
      if (column.cell_type) parts.push(column.cell_type);
      if (column.species) parts.push(column.species);
      if (column.cell_count) parts.push(`细胞量 ${column.cell_count}`);
      if (column.batch) parts.push(`批次 ${column.batch}`);
      if (column.generation) parts.push(`代次 ${column.generation}`);
      return parts.join(' · ');
    },
  },
};
</script>

<style lang="scss" scoped>
$primary: #409eff;
$title-color: #1f2937;
$label-color: #64748b;
$muted-color: #909399;
/* 徽章 / 液柱：手调配色入口 */
$normal-badge: rgb(35, 183, 252);
$tumor-badge: rgb(251, 126, 36);
$tube-radial: radial-gradient(ellipse 90% 38% at 50% 8%, rgb(255 255 255 / 70%) 0%, transparent 62%);
$tube-radial-sm: radial-gradient(ellipse 90% 45% at 50% 12%, rgb(255 255 255 / 60%) 0%, transparent 58%);
$empty-bar-fill: linear-gradient(180deg, #f8fafc 0%, #eef2f7 32%, #e2e8f0 68%, #cbd5e1 100%);
$normal-bar-fill: linear-gradient(
  180deg,
  #f0f9ff 0%,
  #bae6fd 28%,
  rgb(69, 199, 255) 62%,
  rgb(16, 167, 238) 100%
);
$tumor-bar-fill: linear-gradient(
  180deg,
  #fff7ed 0%,
  #fed7aa 28%,
  rgb(255, 152, 67) 62%,
  rgb(239, 111, 20) 100%
);

.panel-head,
.panel-head-left,
.plate-current-bar,
.legend,
.legend-item {
  display: flex;
  align-items: center;
}

.panel-head {
  margin-bottom: 10px;
}

.panel-head-left {
  gap: 8px;
  min-width: 0;
}

.panel-title {
  font-size: 15px;
  font-weight: 600;
  color: $title-color;
}

.head-icon {
  color: $primary;
}

.plate-current-bar {
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
  min-width: 0;
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
  flex-shrink: 0;
  gap: 10px;
}

.legend-item {
  gap: 5px;
  font-size: 12px;
  color: $muted-color;
}

.legend-mark {
  width: 8px;
  height: 20px;
  background: $tube-radial-sm, $empty-bar-fill;
  border: 1px solid #e8edf3;
  border-radius: 999px;
  box-sizing: border-box;

  &.is-normal {
    background: $tube-radial-sm, $normal-bar-fill;
    border-color: rgb(186 230 253 / 85%);
  }

  &.is-tumor {
    background: $tube-radial-sm, $tumor-bar-fill;
    border-color: rgb(254 215 170 / 85%);
  }
}

.cell-board {
  padding: 18px 12px 20px;
  background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
  border: 1px solid #e2e8f0;
  border-radius: 12px;
}

.cell-board-cols {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 8px;
}

.cell-capsule {
  display: grid;
  grid-template-rows: 26px minmax(0, 1fr) 54px;
  gap: 8px;
  align-items: stretch;
  min-width: 0;
  height: 236px;
  padding: 10px 5px;
  overflow: hidden;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  box-shadow: 0 1px 2px rgb(15 23 42 / 4%);
  transition: box-shadow 0.18s ease, transform 0.18s ease;

  &:hover {
    box-shadow: 0 6px 18px rgb(15 23 42 / 9%);
    transform: translateY(-1px);
  }

  &.is-empty {
    background: #fafbfc;
  }

  &.is-normal {
    background: linear-gradient(180deg, #fff 0%, #f7fcff 100%);
  }

  &.is-tumor {
    background: linear-gradient(180deg, #fff 0%, #fffcf7 100%);
  }
}

.capsule-no {
  justify-self: center;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
  color: #64748b;
  background: #eef2f7;
  border-radius: 999px;

  .is-filled & {
    color: #fff;
  }

  .is-normal & {
    background: $normal-badge;
  }

  .is-tumor & {
    background: $tumor-badge;
  }
}

.capsule-bar-wrap {
  display: flex;
  align-items: flex-end;
  justify-content: center;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.capsule-tube {
  display: flex;
  flex: 0 0 30px;
  align-items: flex-end;
  justify-content: center;
  width: 30px;
  height: 100%;
  overflow: hidden;
  background: #f8fafc;
  border: 1px solid #d8dee8;
  border-radius: 999px;

  .is-normal & {
    border-color: rgb(35 183 252 / 35%);
    background: rgb(240 249 255 / 45%);
  }

  .is-tumor & {
    border-color: rgb(251 126 36 / 35%);
    background: rgb(255 247 237 / 50%);
  }
}

.capsule-liquid {
  display: block;
  width: 100%;
  height: 16%;
  border-radius: 999px;
  background: $tube-radial, $empty-bar-fill;
  transition: height 0.2s ease;

  .is-filled & {
    height: 100%;
  }

  .is-normal & {
    background: $tube-radial, $normal-bar-fill;
  }

  .is-tumor & {
    background: $tube-radial, $tumor-bar-fill;
  }
}

.capsule-foot {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 2px;
  width: 100%;
  height: 54px;
  min-width: 0;
  padding-top: 6px;
  overflow: hidden;
  border-top: 1px solid #edf2f7;
  box-sizing: border-box;
}

.capsule-name,
.capsule-species,
.capsule-count {
  display: block;
  flex: 0 0 14px;
  height: 14px;
  min-width: 0;
  overflow: hidden;
  line-height: 14px;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.capsule-name {
  font-size: 11px;
  font-weight: 600;
  color: $title-color;
}

.capsule-species {
  font-size: 10px;
  font-weight: 500;
  color: $label-color;
}

.capsule-count {
  font-size: 10px;
  color: $muted-color;
}

.capsule-empty {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 500;
  color: #94a3b8;
}
</style>
