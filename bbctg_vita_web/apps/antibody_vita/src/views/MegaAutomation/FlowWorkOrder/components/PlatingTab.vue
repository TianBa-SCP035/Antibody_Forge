<template>
  <div class="plating-tab">
    <div class="plating-toolbar">
      <div class="plating-toolbar-left">
        <span class="plating-title">铺板对照</span>
        <span class="plating-stats">
          样本板 {{ order.sample_plates.length }} · 细胞板 {{ order.cell_plates.length }}
        </span>
        <span class="plating-hint">右侧点选跳转；锁定后避免误改</span>
      </div>
      <el-button size="small" :disabled="fieldDisabled" @click="plateMapLocked = !plateMapLocked">
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
            @barcode-focus="(index, value) => $emit('barcode-focus', index, value)"
            @barcode-change="(index, value) => $emit('barcode-change', index, value)"
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
                <span class="nav-species" :title="platingSampleSpecies(plate)">{{
                  platingSampleSpecies(plate)
                }}</span>
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
                <span class="nav-species" :title="platingCellSpecies(plate)">{{
                  platingCellSpecies(plate)
                }}</span>
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
  </div>
</template>

<script>
import { Lock, Unlock } from '@element-plus/icons-vue';
import { ElButton, ElIcon } from 'element-plus';

import { cellKey, cellPlateBarcode } from '../flowWorkOrderModel';
import CellPlateLayout from './CellPlateLayout.vue';
import SamplePlateLayout from './SamplePlateLayout.vue';

export default {
  name: 'MegaFlowWorkOrderPlatingTab',
  components: {
    CellPlateLayout,
    ElButton,
    ElIcon,
    Lock,
    SamplePlateLayout,
    Unlock,
  },
  props: {
    fieldDisabled: Boolean,
    order: { type: Object, required: true },
    pcInfos: { type: Array, default: () => [] },
  },
  emits: ['barcode-change', 'barcode-focus'],
  data() {
    return {
      plateMapLocked: true,
      platingFocus: 'sample:0',
    };
  },
  computed: {
    plateMapDisabled() {
      return this.fieldDisabled || this.plateMapLocked;
    },
    cellByKey() {
      const map = {};
      (this.order.cell_plates || []).forEach((plate, plateIndex) => {
        const barcode = cellPlateBarcode(plate, plateIndex);
        (plate.columns || []).forEach((column) => {
          map[cellKey(barcode, column.column_no)] = column;
        });
      });
      return map;
    },
  },
  methods: {
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
        const col = this.cellByKey[cellKey(key.barcode, key.column_no)];
        if (!String(col?.cell_name || '').trim()) return;
        hasNamed = true;
        const token = String(col?.species || '').trim();
        if (token && !species.includes(token)) species.push(token);
      });
      if (!hasNamed) return 'NA';
      return species.length ? species.join('、') : 'NA';
    },
    platingCellSpecies(plate) {
      const columns = (plate?.columns || []).filter((column) =>
        String(column?.cell_name || '').trim(),
      );
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
  },
};
</script>

<style lang="scss" scoped>
$title-color: #303133;
$label-color: #606266;
$muted-color: #909399;

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

  &.well-sample {
    background: #cfe2ff;
  }
  &.well-pc {
    background: #ffd8a8;
  }
  &.well-nc {
    background: #d0d7ff;
  }
  &.well-iso {
    background: #b7f0c8;
  }
  &.well-tag {
    background: #dcc9ff;
  }
  &.well-blank {
    background: #e8ebf0;
  }
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
    background: rgb(255, 156, 75);
  }
}

@media (max-width: 1180px) {
  .plating-layout {
    grid-template-columns: minmax(0, 1fr);
  }

  .plating-main,
  .plating-nav {
    max-height: none;
  }
}
</style>
