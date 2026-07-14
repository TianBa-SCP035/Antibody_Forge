<template>
  <section class="cell-plate-editor">
    <div class="panel-head">
      <div class="panel-head-left">
        <el-icon class="head-icon"><Menu /></el-icon>
        <span class="panel-title">细胞板信息</span>
        <span class="panel-hint">每块细胞板按 12 列维护，一列一份细胞</span>
      </div>
      <div class="panel-head-right">
        <el-checkbox v-model="showExtraFields" size="small">更多字段</el-checkbox>
        <el-button size="small" :disabled="disabled" @click="requestAdd">
          <el-icon><Plus /></el-icon>新增细胞板
        </el-button>
      </div>
    </div>

    <el-tabs
      :model-value="modelValue"
      type="card"
      class="inner-tabs"
      @update:model-value="$emit('update:modelValue', String($event))"
    >
      <el-tab-pane
        v-for="(plate, index) in plates"
        :key="'cell-tab-' + index"
        :name="String(index)"
      >
        <template #label>
          <span class="tab-label">
            细胞板-{{ index + 1 }}
            <el-icon
              v-if="plates.length > 1 && !disabled"
              class="tab-close"
              @click.stop="requestRemove(index)"
            ><Close /></el-icon>
          </span>
        </template>

        <div class="cell-plate-barcode">
          <span class="field-label">细胞板条码</span>
          <el-input
            v-model="plate.barcode"
            size="small"
            :disabled="disabled"
            :class="{ 'is-invalid-control': hasFieldError(`cell_plates.${index}.barcode`) }"
            placeholder="扫描/输入细胞板条码"
            @focus="$emit('barcode-focus', index, plate.barcode)"
            @change="$emit('barcode-change', index, plate.barcode)"
          />
        </div>

        <el-table
          ref="columnsTable"
          :data="plate.columns"
          border
          size="small"
          class="info-table"
          row-key="column_no"
        >
          <el-table-column label="列" width="48" align="center" class-name="drag-cell">
            <template #default="{ row }">
              <div
                class="row-drag-handle"
                :class="{ 'is-disabled': disabled }"
                title="拖动调整位置"
                @click.stop
              >
                {{ row.column_no }}
              </div>
            </template>
          </el-table-column>
          <el-table-column label="类型" min-width="80">
            <template #default="{ row, $index }">
              <el-select
                v-model="row.cell_type"
                size="small"
                :disabled="disabled"
                :class="{
                  'is-invalid-control': hasFieldError(
                    `cell_plates.${index}.columns.${$index}.cell_type`,
                  ),
                }"
              >
                <el-option v-for="type in cellTypeOptions" :key="type" :label="type" :value="type" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="细胞名称" min-width="150">
            <template #default="{ row, $index }">
              <el-input
                v-model="row.cell_name"
                size="small"
                :disabled="disabled"
                :class="{
                  'is-invalid-control': hasFieldError(
                    `cell_plates.${index}.columns.${$index}.cell_name`,
                  ),
                }"
                placeholder="细胞名称"
              />
            </template>
          </el-table-column>
          <el-table-column label="种属" min-width="70">
            <template #default="{ row }">
              <el-select v-model="row.species" size="small" clearable :disabled="disabled">
                <el-option v-for="species in speciesOptions" :key="species" :label="species" :value="species" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="批次" min-width="80">
            <template #default="{ row }">
              <el-input v-model="row.batch" size="small" :disabled="disabled" />
            </template>
          </el-table-column>
          <el-table-column label="代次" min-width="80">
            <template #default="{ row }">
              <el-input v-model="row.generation" size="small" :disabled="disabled" />
            </template>
          </el-table-column>
          <el-table-column label="细胞量" min-width="80">
            <template #default="{ row }">
              <el-input v-model="row.cell_count" size="small" :disabled="disabled" />
            </template>
          </el-table-column>
          <template v-if="showExtraFields">
            <el-table-column label="货号" min-width="80">
              <template #default="{ row }">
                <el-input v-model="row.catalog_no" size="small" :disabled="disabled" />
              </template>
            </el-table-column>
            <el-table-column label="来源" min-width="80">
              <template #default="{ row }">
                <el-input v-model="row.source" size="small" :disabled="disabled" />
              </template>
            </el-table-column>
          </template>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </section>
</template>

<script>
import { Close, Menu, Plus } from '@element-plus/icons-vue';
import {
  ElButton,
  ElCheckbox,
  ElIcon,
  ElInput,
  ElOption,
  ElSelect,
  ElTabPane,
  ElTable,
  ElTableColumn,
  ElTabs,
} from 'element-plus';

const CONTENT_FIELDS = [
  'cell_type',
  'cell_name',
  'species',
  'batch',
  'generation',
  'cell_count',
  'catalog_no',
  'source',
];

export default {
  name: 'MegaCellPlateEditor',
  components: {
    Close,
    ElButton,
    ElCheckbox,
    ElIcon,
    ElInput,
    ElOption,
    ElSelect,
    ElTabPane,
    ElTable,
    ElTableColumn,
    ElTabs,
    Menu,
    Plus,
  },
  props: {
    cellTypeOptions: { type: Array, default: () => [] },
    disabled: Boolean,
    hasFieldError: { type: Function, default: () => false },
    modelValue: { type: String, default: '0' },
    plates: { type: Array, default: () => [] },
    speciesOptions: { type: Array, default: () => [] },
  },
  emits: [
    'add',
    'barcode-change',
    'barcode-focus',
    'remove',
    'reordered',
    'update:modelValue',
  ],
  data() {
    return {
      showExtraFields: false,
      sortable: null,
      sortableInitToken: 0,
    };
  },
  computed: {
    activePlate() {
      const index = Math.max(0, Number(this.modelValue) || 0);
      return this.plates[index] || this.plates[0] || { columns: [] };
    },
  },
  watch: {
    disabled(value) {
      this.sortable?.option('disabled', value);
    },
    modelValue() {
      this.scheduleSortableInit();
    },
    plates() {
      this.scheduleSortableInit();
    },
  },
  mounted() {
    this.scheduleSortableInit();
  },
  beforeUnmount() {
    this.sortableInitToken += 1;
    this.destroySortable();
  },
  methods: {
    requestAdd() {
      this.$emit('add');
      this.scheduleSortableInit();
    },
    requestRemove(index) {
      this.$emit('remove', index);
      this.scheduleSortableInit();
    },
    resolveTable() {
      const ref = this.$refs.columnsTable;
      if (!ref) return null;
      if (Array.isArray(ref)) {
        return ref[Number(this.modelValue)] || ref[0] || null;
      }
      return ref;
    },
    async initSortable() {
      const initToken = ++this.sortableInitToken;
      this.destroySortable();
      await this.$nextTick();
      const tbody = this.resolveTable()?.$el?.querySelector('.el-table__body-wrapper tbody');
      if (!tbody) return;
      const Sortable = (await import('sortablejs/modular/sortable.complete.esm.js')).default;
      if (initToken !== this.sortableInitToken || !tbody.isConnected) return;
      this.sortable = Sortable.create(tbody, {
        animation: 200,
        disabled: this.disabled,
        ghostClass: 'sortable-ghost',
        handle: '.row-drag-handle',
        onEnd: (event) => this.handleDragEnd(event),
      });
    },
    handleDragEnd({ oldIndex, newIndex, item }) {
      if (oldIndex == null || newIndex == null || oldIndex === newIndex) return;
      const parent = item?.parentNode;
      if (parent) {
        const anchor =
          newIndex > oldIndex ? parent.children[oldIndex] : parent.children[oldIndex + 1];
        parent.insertBefore(item, anchor || null);
      }
      const columns = this.activePlate.columns || [];
      const snapshots = columns.map((column) =>
        Object.fromEntries(CONTENT_FIELDS.map((field) => [field, column[field]])),
      );
      const [moved] = snapshots.splice(oldIndex, 1);
      snapshots.splice(newIndex, 0, moved);
      columns.forEach((column, index) => {
        Object.assign(column, snapshots[index]);
      });
      this.$emit('reordered', {
        newIndex,
        oldIndex,
        plateIndex: Number(this.modelValue) || 0,
      });
    },
    destroySortable() {
      this.sortable?.destroy();
      this.sortable = null;
    },
    scheduleSortableInit() {
      this.$nextTick(() => this.initSortable());
    },
  },
};
</script>

<style lang="scss" scoped>
$border-color: #e4e7ed;

.cell-plate-barcode,
.tab-label {
  display: flex;
  align-items: center;
}

.cell-plate-barcode {
  gap: 8px;
  max-width: 320px;
  margin-bottom: 10px;
}

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
    color: #606266;
    background: #f5f7fa;
  }

  :deep(.el-input__wrapper),
  :deep(.el-select__wrapper) {
    background: transparent;
    box-shadow: none;
  }
}

.inner-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: 10px;
  }

  :deep(.el-tabs__item) {
    padding: 0 12px;
    font-size: 13px;
  }

  /* card 选中项默认去掉底边；与拆分前 Detail 页样式一致，补回底边线 */
  :deep(.el-tabs__item.is-active) {
    border-bottom-color: $border-color;
  }
}

.tab-label {
  gap: 4px;
}

.tab-close {
  font-size: 12px;
  color: #909399;

  &:hover {
    color: #f56c6c;
  }
}

:deep(.drag-cell .cell) {
  padding: 0;
}

</style>
