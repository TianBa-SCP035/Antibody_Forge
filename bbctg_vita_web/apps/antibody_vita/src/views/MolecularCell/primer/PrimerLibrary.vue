<template>
  <div class="primer-page" :class="{ 'is-list-table-locked': listTableLocked }">
    <AdvancedOpsBar v-model="showAdvancedOps" pinned>
      <ElSelect
        v-if="selectionMode"
        v-model="batchFamily"
        filterable
        allow-create
        default-first-option
        placeholder="改到这个系列"
      >
        <ElOption v-for="name in libraryNames" :key="name" :label="name" :value="name" />
      </ElSelect>
      <ElSelect v-if="selectionMode" v-model="batchDirection" clearable placeholder="改到这个方向">
        <ElOption label="正向" value="F" />
        <ElOption label="反向" value="R" />
      </ElSelect>
      <template #actions>
        <ElButton
          :type="selectionMode ? 'primary' : 'default'"
          :class="{ 'no-permission-btn': !canEdit }"
          @click="toggleSelectionMode"
        >
          {{ selectionMode ? '退出批量' : '批量编辑' }}
        </ElButton>
        <template v-if="selectionMode">
          <ElButton :disabled="!selectedIds.size || !batchFamily.trim()" :loading="batching" @click="runBatch({ family: batchFamily.trim() })">
            改系列
          </ElButton>
          <ElButton :disabled="!selectedIds.size || !batchDirection" :loading="batching" @click="runBatch({ direction: batchDirection })">
            改方向
          </ElButton>
          <ElButton :disabled="!selectedIds.size" :loading="batching" @click="runBatch({ active: false })">停用</ElButton>
          <ElButton :disabled="!selectedIds.size" :loading="batching" @click="runBatch({ active: true })">启用</ElButton>
          <ElButton
            type="warning"
            plain
            :disabled="!selectedIds.size"
            :loading="batching"
            @click="runBatch({ remove: true })"
          >
            删除
          </ElButton>
        </template>
      </template>
    </AdvancedOpsBar>
    <section class="workbench-panel">
      <div class="page-header-band">
        <div>
          <h1 class="page-title">引物库</h1>
          <p class="page-subtitle">达普仪器用达普Barcode，其他仪器或步骤用 UDP。输入新系列名即可自建。停用后不再出现在选项中。</p>
        </div>
        <div class="header-actions">
          <span class="total-count">共 {{ total }} 条</span>
          <ElButton :icon="Download" :loading="exporting" @click="handleExport">导出</ElButton>
          <ElButton
            :icon="Upload"
            :class="{ 'no-permission-btn': !canEdit }"
            @click="openImport"
          >
            导入
          </ElButton>
          <ElButton
            type="primary"
            :icon="Plus"
            :class="{ 'no-permission-btn': !canEdit }"
            @click="openCreate"
          >
            新增
          </ElButton>
        </div>
      </div>

      <div class="stats-strip">
        <button
          v-for="item in seriesCards"
          :key="item.value || 'all'"
          type="button"
          class="stat-tile"
          :class="[item.tone, { 'is-active': listQuery.family === item.value }]"
          @click="selectSeries(item.value)"
        >
          <span class="stat-copy">
            <span class="stat-label">{{ item.label }}</span>
            <small>{{ item.hint }}</small>
          </span>
          <strong class="stat-value">{{ item.count }}</strong>
        </button>
      </div>

      <div class="filter-strip list-filter-controls">
        <ElInput
          v-model="listQuery.name"
          class="filter-name"
          clearable
          v-bind="headerTop('name', '名称')"
          @keyup.enter="handleFilter"
          @clear="handleFilter"
        />
        <ElInput
          v-model="listQuery.sequence"
          class="filter-sequence"
          clearable
          v-bind="headerTop('short_sequence', '显示序列')"
          @keyup.enter="handleFilter"
          @clear="handleFilter"
        />
        <ElInput
          v-model="listQuery.checkKeyword"
          class="filter-check"
          clearable
          placeholder="核对序列"
          @keyup.enter="handleFilter"
          @clear="handleFilter"
        />
        <ElInput
          v-model="listQuery.note"
          class="filter-note"
          clearable
          v-bind="headerTop('note', '备注')"
          @keyup.enter="handleFilter"
          @clear="handleFilter"
        />
        <ListFilterSelect
          v-model="listQuery.direction"
          class="filter-item"
          clearable
          v-bind="headerTop('direction', '方向')"
          @change="handleFilter"
        >
          <ElOption label="正向" value="F" />
          <ElOption label="反向" value="R" />
        </ListFilterSelect>
        <ListFilterSelect
          v-model="listQuery.status"
          class="filter-item"
          clearable
          v-bind="headerTop('active', '状态')"
          @change="handleFilter"
        >
          <ElOption label="启用" value="active" />
          <ElOption label="停用" value="inactive" />
        </ListFilterSelect>
        <div class="list-filter-actions">
          <WorkbenchHeaderFilterChip v-bind="headerChipBind" />
          <button
            type="button"
            class="list-advanced-trigger"
            :class="{ 'is-active': showAdvancedOps }"
            title="高级操作"
            @click="showAdvancedOps = !showAdvancedOps"
          >
            <ElIcon><Tools /></ElIcon>
          </button>
          <ElButton type="primary" :icon="Search" title="右键清空筛选" @click="handleFilter" @contextmenu.prevent="reset">查询</ElButton>
          <ElButton :icon="Refresh" @click="reset">重置</ElButton>
        </div>
      </div>
    </section>

    <ElCard shadow="never" class="list-table-card">
      <p class="sheet-hint">
        拖拽划选单元格，Ctrl+C 复制，右键取消选中。点表头筛选或排序，按住表头选中整列。双击一行可编辑。
        <template v-if="selectionMode">勾选列可拖拽或按住 Shift 连选，表头菜单可当页全选、全部全选或取消。</template>
      </p>
      <div ref="listTableBody" class="list-table-body">
      <div
        ref="wrapRef"
        class="sheet-wrap"
        tabindex="0"
        @copy="onCopy"
        @click="onSheetClick"
        @contextmenu="onContextMenu"
        @keydown="onKeydown"
        @mousedown="onMouseDown"
        @mouseover="onMouseOver"
        @selectstart="onSelectStart"
      >
        <div ref="stageRef" class="sheet-stage">
          <vxe-table
            ref="tableRef"
            :height="listTableHeight"
            v-loading="loading"
            :data="items"
            border
            show-overflow
            size="small"
            :row-config="rowConfig"
            :cell-config="cellConfig"
            :column-config="columnConfig"
            :mouse-config="mouseConfig"
            :keyboard-config="keyboardConfig"
            :virtual-y-config="virtualYConfig"
            :row-class-name="rowClassName"
            :header-cell-class-name="sheetHeaderCellClass"
            empty-text="没有引物"
            @scroll="onScroll"
            @cell-selected="onCellSelected"
            @cell-dblclick="onDblclick"
          >
            <vxe-column v-if="selectionMode" width="40" fixed="left" align="center">
              <template #header>
                <div class="check-header" @mousedown.stop>
                  <ElDropdown trigger="click" @command="onSelectCommand">
                    <button type="button" class="check-menu" aria-label="选择范围">
                      <ElIcon><ArrowDown /></ElIcon>
                    </button>
                    <template #dropdown>
                      <ElDropdownMenu>
                        <ElDropdownItem command="page">当页全选</ElDropdownItem>
                        <ElDropdownItem command="all">全部全选</ElDropdownItem>
                        <ElDropdownItem command="clear">取消选择</ElDropdownItem>
                      </ElDropdownMenu>
                    </template>
                  </ElDropdown>
                </div>
              </template>
              <template #default="{ row, rowIndex }">
                <div
                  class="check-cell"
                  @mousedown.stop.prevent="onCheckDown($event, row, rowIndex)"
                  @mouseenter="onCheckEnter(row)"
                  @click.stop
                  @dblclick.stop
                >
                  <ElCheckbox :model-value="selectedIds.has(row.id)" class="check-readonly" />
                </div>
              </template>
            </vxe-column>
            <vxe-column
              v-for="column in columns"
              :key="column.key"
              :field="column.key"
              :title="column.title"
              :min-width="column.minWidth"
              :width="column.width"
              :align="column.align"
              :class-name="column.mono ? 'is-sequence' : ''"
            >
              <template #header>
                <WorkbenchHeaderLabel
                  v-if="headerMenuStates[column.key]"
                  :label="column.title"
                  v-bind="headerMenuStates[column.key]"
                />
                <template v-else>{{ column.title }}</template>
              </template>
              <template #default="{ row }">
                <ElTag
                  v-if="column.key === 'active'"
                  class="list-status-tag"
                  :type="row.active ? 'success' : 'info'"
                  effect="plain"
                >
                  {{ row.active ? '启用' : '停用' }}
                </ElTag>
                <template v-else>{{ displayCell(row, column.key) }}</template>
              </template>
            </vxe-column>
            <vxe-column title="操作" width="240" fixed="right" align="center">
              <template #default="{ row }">
                <div class="sheet-actions" @mousedown.stop @click.stop @dblclick.stop>
                  <ElButtonGroup>
                    <ElButton
                      class="list-table-action-btn"
                      type="primary"
                      plain
                      :icon="Edit"
                      :class="{ 'no-permission-btn': !canEdit }"
                      @click="openEdit(row)"
                    >
                      编辑
                    </ElButton>
                    <ElButton
                      class="list-table-action-btn"
                      type="success"
                      plain
                      :icon="row.active ? CircleClose : CircleCheck"
                      :loading="savingId === row.id"
                      :class="{ 'no-permission-btn': !canEdit }"
                      @click="toggleActive(row)"
                    >
                      {{ row.active ? '停用' : '启用' }}
                    </ElButton>
                    <ElButton
                      class="list-table-action-btn"
                      type="warning"
                      plain
                      :icon="Delete"
                      :loading="deletingId === row.id"
                      :class="{ 'no-permission-btn': !canEdit }"
                      @click="removeRow(row)"
                    >
                      删除
                    </ElButton>
                  </ElButtonGroup>
                </div>
              </template>
            </vxe-column>
          </vxe-table>
          <div ref="overlayRef" class="sheet-range" aria-hidden="true" />
        </div>
      </div>
      </div>

      <ElPagination
        v-show="total > 0"
        v-model:current-page="listQuery.page"
        v-model:page-size="listQuery.limit"
        :total="total"
        :page-sizes="[20, 50, 100, 200, 500]"
        layout="total, sizes, prev, pager, next, jumper"
        class="list-pagination"
        @size-change="changePageSize"
        @current-change="load"
      />
    </ElCard>

    <PrimerEditorDialog
      v-model="editorVisible"
      :libraries="libraryNames"
      :primer="editingRow"
      @saved="handleSaved"
    />
    <PrimerImportDialog v-model="importVisible" @saved="handleImported" />
    <WorkbenchHeaderMenu v-bind="headerMenuBind" />
  </div>
</template>

<script>
import { ref } from 'vue';

import {
  ArrowDown,
  CircleCheck,
  CircleClose,
  Delete,
  Download,
  Edit,
  Plus,
  Refresh,
  Search,
  Tools,
  Upload,
} from '@element-plus/icons-vue';
import { useUserStore } from '@vben/stores';
import {
  ElButton,
  ElButtonGroup,
  ElCard,
  ElCheckbox,
  ElDropdown,
  ElDropdownItem,
  ElDropdownMenu,
  ElIcon,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElPagination,
  ElSelect,
  ElTag,
} from 'element-plus';
import { VxeColumn, VxeTable } from 'vxe-table';

import AdvancedOpsBar from '#/components/AdvancedOpsBar.vue';
import ListFilterSelect from '#/components/ListFilterSelect.vue';
import {
  WorkbenchHeaderFilterChip,
  WorkbenchHeaderLabel,
  WorkbenchHeaderMenu,
  workbenchHeaderMenuMixin,
} from '#/components/workbench';
import { notifyApiError } from '#/api/errors';
import {
  batchDeletePrimers,
  batchUpdatePrimers,
  deletePrimer,
  exportPrimerCatalog,
  fetchPrimerCatalog,
  fetchPrimerColumnValues,
  fetchPrimerIds,
  savePrimer,
} from '#/api/primerCatalog';
import { clearPrimerCatalogCache } from '../library/primerCatalogOptions';
import { downloadListExcel, excelTimestamp } from '#/utils/downloadExcel';
import { listPageMixin } from '#/utils/listPage';
import { listTableLockMixin } from '#/utils/listTableLock';
import { canEditPrimerLibrary } from '#/utils/molecularPermission';

import '#/adapter/vxe-table';
import 'vxe-table/styles/cssvar.scss';

import PrimerEditorDialog from './PrimerEditorDialog.vue';
import PrimerImportDialog from './PrimerImportDialog.vue';
import {
  checkSequence,
  directionLabel,
  libraryHint,
  libraryTone,
  PRESET_LIBRARIES,
} from './primerSeries';
import { useSheetRange } from './sheetRange';

const COLUMNS = Object.freeze([
  { key: 'name', title: '名称', minWidth: 160 },
  { key: 'family', title: '系列', minWidth: 120 },
  { key: 'direction', title: '方向', minWidth: 60, align: 'center' },
  { key: 'short_sequence', title: '显示序列', minWidth: 160, mono: true },
  { key: 'check_sequence', title: '核对序列', minWidth: 160, mono: true },
  { key: 'note', title: '备注', minWidth: 180 },
  { key: 'active', title: '状态', width: 90, align: 'center' },
]);

// 核对序列是算出来的，只有顶部筛选
const PRIMER_HEADER_COLUMNS = Object.freeze({
  name: { type: 'text', label: '名称', values: 'recent', top: { query: 'name', kind: 'contains' } },
  family: { type: 'enum', label: '系列', values: 'all', top: { query: 'family' } },
  direction: { type: 'enum', label: '方向', values: 'all', top: { query: 'direction' } },
  short_sequence: { type: 'text', label: '显示序列', values: 'search', top: { query: 'sequence', kind: 'contains' } },
  note: { type: 'text', label: '备注', values: 'search', top: { query: 'note', kind: 'contains' } },
  active: { type: 'enum', label: '状态', values: 'all', top: { query: 'status' } },
});

const ROW_CONFIG = Object.freeze({ keyField: 'id', isHover: true });
const CELL_CONFIG = Object.freeze({ height: 40 });
const COLUMN_CONFIG = Object.freeze({ resizable: true });
const MOUSE_CONFIG = Object.freeze({ selected: true });
const VIRTUAL_Y_CONFIG = Object.freeze({ enabled: true, gt: 40, oSize: 10, immediate: true });
const KEYBOARD_CONFIG = Object.freeze({
  isArrow: true,
  isShift: true,
  isTab: true,
  isEdit: false,
  isDel: false,
  isEnter: false,
  isClip: false,
});

function emptyQuery() {
  return {
    name: '',
    sequence: '',
    checkKeyword: '',
    note: '',
    family: '',
    direction: '',
    status: '',
    sort_field: '',
    sort_dir: '',
    page: 1,
    limit: 20,
  };
}

function cellText(row, key) {
  if (key === 'active') return row.active ? '启用' : '停用';
  if (key === 'direction') return directionLabel(row.direction);
  if (key === 'check_sequence') return checkSequence(row.short_sequence);
  const value = row[key];
  return value == null ? '' : String(value);
}

function filterTerms(value) {
  return (Array.isArray(value) ? value : value ? [value] : []).filter(Boolean);
}

export default {
  name: 'PrimerLibrary',
  components: {
    AdvancedOpsBar,
    ArrowDown,
    ElButton,
    ElButtonGroup,
    ElCard,
    ElCheckbox,
    ElDropdown,
    ElDropdownItem,
    ElDropdownMenu,
    ElIcon,
    ElInput,
    ElOption,
    ElPagination,
    ElSelect,
    ElTag,
    ListFilterSelect,
    PrimerEditorDialog,
    PrimerImportDialog,
    Tools,
    VxeColumn,
    VxeTable,
    WorkbenchHeaderFilterChip,
    WorkbenchHeaderLabel,
    WorkbenchHeaderMenu,
  },
  mixins: [listTableLockMixin, listPageMixin, workbenchHeaderMenuMixin],
  listFilterKey: 'primerLibrary',
  setup() {
    const items = ref([]);
    const sheet = useSheetRange({
      rows: items,
      columns: COLUMNS,
      text: cellText,
      menuKeys: Object.keys(PRIMER_HEADER_COLUMNS),
    });
    return {
      ...sheet,
      items,
      userStore: useUserStore(),
      columns: COLUMNS,
      rowConfig: ROW_CONFIG,
      cellConfig: CELL_CONFIG,
      columnConfig: COLUMN_CONFIG,
      mouseConfig: MOUSE_CONFIG,
      virtualYConfig: VIRTUAL_Y_CONFIG,
      keyboardConfig: KEYBOARD_CONFIG,
      CircleCheck,
      CircleClose,
      Delete,
      Download,
      Edit,
      Plus,
      Refresh,
      Search,
      Upload,
    };
  },
  data() {
    return {
      listQuery: emptyQuery(),
      total: 0,
      statsTotal: 0,
      libraryStats: [],
      loading: false,
      exporting: false,
      savingId: null,
      deletingId: null,
      editorVisible: false,
      importVisible: false,
      showAdvancedOps: false,
      selectionMode: false,
      batchFamily: '',
      batchDirection: '',
      batching: false,
      selectedIds: new Set(),
      editingRow: null,
    };
  },
  computed: {
    headerMenuColumns() {
      return PRIMER_HEADER_COLUMNS;
    },
    canEdit() {
      return canEditPrimerLibrary(this.userStore.userInfo);
    },
    seriesCards() {
      return [
        { label: '全部', value: '', count: this.statsTotal, hint: '当前筛选', tone: 'tone-blue' },
        ...this.libraryStats.map((item, index) => ({
          label: item.name,
          value: item.name,
          count: item.count,
          hint: libraryHint(item.name),
          tone: libraryTone(item.name, index),
        })),
      ];
    },
    libraryNames() {
      const names = PRESET_LIBRARIES.map((item) => item.value);
      for (const item of this.libraryStats) {
        if (!names.includes(item.name)) names.push(item.name);
      }
      return names;
    },
  },
  watch: {
    showAdvancedOps(open) {
      if (!open) this.leaveSelection();
    },
  },
  created() {
    this._checkDrag = null;
    this._checkAnchor = -1;
  },
  mounted() {
    window.addEventListener('mouseup', this.finishCheckDrag);
    this.load();
  },
  activated() {
    if (this.isListDataStale()) this.load();
  },
  beforeUnmount() {
    window.removeEventListener('mouseup', this.finishCheckDrag);
  },
  methods: {
    displayCell(row, key) {
      return cellText(row, key) || '—';
    },
    rowClassName({ row }) {
      return row.active ? '' : 'is-inactive';
    },
    sheetHeaderCellClass({ column }) {
      return this.headerCellClass(column.field);
    },
    onSheetClick(event) {
      const field = this.headerMenuField(event);
      if (field) this.openHeaderMenu(field, event.target.closest('.vxe-header--column'));
    },
    replaceSelected(next) {
      this.selectedIds = next;
    },
    clearSelected() {
      this.replaceSelected(new Set());
      this._checkAnchor = -1;
    },
    buildQuery() {
      const query = this.listQuery;
      const statuses = filterTerms(query.status);
      return {
        name: query.name.trim() || undefined,
        sequence: query.sequence.trim() || undefined,
        check_keyword: query.checkKeyword.trim() || undefined,
        note: query.note.trim() || undefined,
        family: query.family || undefined,
        direction: query.direction || undefined,
        active: statuses.length === 1 ? statuses[0] === 'active' : undefined,
        field_filters: this.headerFilterPayload(),
        sort_field: query.sort_field || undefined,
        sort_dir: query.sort_dir || undefined,
        page: query.page,
        limit: query.limit,
      };
    },
    fetchHeaderValues(query) {
      // 顶部状态换算成了 active，取状态列的值时要一并去掉
      if (query.field === 'active') delete query.active;
      return fetchPrimerColumnValues(query);
    },
    async load() {
      const isLatest = this.beginListRequest();
      clearPrimerCatalogCache();
      this.loading = true;
      try {
        const data = await fetchPrimerCatalog(this.buildQuery());
        if (!isLatest()) return;
        this.items = data.items || [];
        this.total = data.total || 0;
        this.statsTotal = data.stats?.total || 0;
        this.libraryStats = data.stats?.families || [];
        this.markListFetched();
      } catch (error) {
        if (isLatest()) {
          notifyApiError(error, { messages: { default: '引物库加载失败' } });
        }
      } finally {
        if (isLatest()) this.loading = false;
      }
    },
    getList() {
      this.clearSelected();
      return this.load();
    },
    reset() {
      Object.assign(this.listQuery, { ...emptyQuery(), limit: this.listQuery.limit });
      this.clearHeaderFilters();
      this.getList();
    },
    selectPage() {
      const next = new Set(this.selectedIds);
      for (const row of this.items) next.add(row.id);
      this.replaceSelected(next);
    },
    onSelectCommand(command) {
      if (command === 'clear') {
        this.clearSelected();
        return;
      }
      if (command === 'page') {
        this.selectPage();
        return;
      }
      this.selectAllMatching();
    },
    async selectAllMatching() {
      try {
        const { page: _page, limit: _limit, ...filters } = this.buildQuery();
        const data = await fetchPrimerIds(filters);
        this.replaceSelected(new Set(data.ids || []));
        if (!data.ids?.length) ElMessage.info('当前筛选下没有引物');
      } catch (error) {
        notifyApiError(error, { messages: { default: '全选失败' } });
      }
    },
    onCheckDown(event, row, rowIndex) {
      if (event.button !== 0) return;
      const next = new Set(this.selectedIds);
      const index = Number.isInteger(rowIndex) ? rowIndex : this.items.findIndex((item) => item.id === row.id);
      if (event.shiftKey && this._checkAnchor >= 0 && index >= 0) {
        const start = Math.min(this._checkAnchor, index);
        const end = Math.max(this._checkAnchor, index);
        for (let cursor = start; cursor <= end; cursor += 1) {
          const item = this.items[cursor];
          if (item) next.add(item.id);
        }
        this.replaceSelected(next);
        return;
      }
      const checking = !next.has(row.id);
      if (checking) next.add(row.id);
      else next.delete(row.id);
      this.replaceSelected(next);
      this._checkAnchor = index;
      this._checkDrag = { checking };
    },
    onCheckEnter(row) {
      if (!this._checkDrag) return;
      const next = new Set(this.selectedIds);
      if (this._checkDrag.checking) next.add(row.id);
      else next.delete(row.id);
      this.replaceSelected(next);
    },
    finishCheckDrag() {
      this._checkDrag = null;
    },
    leaveSelection() {
      this.selectionMode = false;
      this.clearSelected();
      this.batchFamily = '';
      this.batchDirection = '';
    },
    toggleSelectionMode() {
      if (!this.editable()) return;
      if (this.selectionMode) {
        this.leaveSelection();
        return;
      }
      this.selectionMode = true;
    },
    async runBatch(action) {
      const ids = [...this.selectedIds];
      if (!ids.length) {
        ElMessage.warning('请先勾选引物');
        return;
      }
      const count = ids.length;
      try {
        if (action.remove) {
          await ElMessageBox.confirm(
            `确认删除选中的 ${count} 条？已被文库工单使用的会跳过。`,
            '删除确认',
            { type: 'warning', confirmButtonText: '删除' },
          );
        } else if (action.family) {
          await ElMessageBox.confirm(`确认把选中的 ${count} 条改到「${action.family}」？`, '改系列', { type: 'warning' });
        } else if (action.direction) {
          const label = action.direction === 'F' ? '正向' : '反向';
          await ElMessageBox.confirm(`确认把选中的 ${count} 条改为${label}？`, '改方向', { type: 'warning' });
        } else if (action.active === false) {
          await ElMessageBox.confirm(
            `确认停用选中的 ${count} 条？停用后不再出现在文库构建的引物选项里。`,
            '停用确认',
            { type: 'warning' },
          );
        } else {
          await ElMessageBox.confirm(`确认启用选中的 ${count} 条？`, '启用确认', { type: 'warning' });
        }
      } catch {
        return;
      }
      this.batching = true;
      try {
        if (action.remove) {
          const result = await batchDeletePrimers(ids);
          const skipped = result.skipped || [];
          ElMessage.success(skipped.length
            ? `已删除 ${result.deleted} 条，${skipped.slice(0, 8).join('、')}${skipped.length > 8 ? ' 等' : ''} 已被工单使用，已跳过`
            : `已删除 ${result.deleted} 条`);
        } else if (action.family) {
          await batchUpdatePrimers({ ids, family: action.family });
          ElMessage.success('系列已更新');
        } else if (action.direction) {
          await batchUpdatePrimers({ ids, direction: action.direction });
          ElMessage.success('方向已更新');
        } else {
          await batchUpdatePrimers({ ids, active: action.active });
          ElMessage.success(action.active ? '已启用' : '已停用');
        }
        this.batchFamily = '';
        this.batchDirection = '';
        this.clearSelected();
        await this.load();
      } catch (error) {
        notifyApiError(error, { messages: { default: '批量操作失败' } });
      } finally {
        this.batching = false;
      }
    },
    selectSeries(value) {
      this.listQuery.family = this.listQuery.family === value ? '' : value;
      // 点「全部」也要清掉表头里的系列条件，统计块高亮才和列表一致
      if (this.headerFilters.family) this.dropHeaderFilter('family');
      this.handleFilter();
    },
    changePageSize() {
      this.listQuery.page = 1;
      this.load();
    },
    editable() {
      if (this.canEdit) return true;
      ElMessage.warning('您没有权限编辑引物库');
      return false;
    },
    openCreate() {
      if (!this.editable()) return;
      this.editingRow = null;
      this.editorVisible = true;
    },
    openEdit(row) {
      if (!this.editable()) return;
      this.editingRow = row;
      this.editorVisible = true;
    },
    openImport() {
      if (!this.editable()) return;
      this.importVisible = true;
    },
    onDblclick({ row, column }) {
      if (!column?.field) return;
      this.openEdit(row);
    },
    async toggleActive(row) {
      if (!this.editable()) return;
      if (row.active) {
        try {
          await ElMessageBox.confirm(`确认停用「${row.name}」？停用后不会出现在文库构建的引物选项里。`, '提示', {
            type: 'warning',
          });
        } catch {
          return;
        }
      }
      this.savingId = row.id;
      try {
        await savePrimer({
          id: row.id,
          name: row.name,
          family: row.family,
          direction: row.direction,
          short_sequence: row.short_sequence,
          note: row.note,
          active: !row.active,
        });
        await this.load();
      } catch (error) {
        notifyApiError(error, { messages: { default: '状态更新失败' } });
      } finally {
        this.savingId = null;
      }
    },
    async removeRow(row) {
      if (!this.editable()) return;
      try {
        await ElMessageBox.confirm(
          `确认删除「${row.name}」？删除后不能恢复。已被文库工单使用的引物请改用停用。`,
          '删除确认',
          { type: 'warning', confirmButtonText: '删除' },
        );
      } catch {
        return;
      }
      this.deletingId = row.id;
      try {
        await deletePrimer(row.id);
        ElMessage.success('已删除');
        if (this.items.length === 1 && this.listQuery.page > 1) this.listQuery.page -= 1;
        await this.load();
      } catch (error) {
        notifyApiError(error, { messages: { default: '删除失败' } });
      } finally {
        this.deletingId = null;
      }
    },
    async handleExport() {
      this.exporting = true;
      try {
        await downloadListExcel(
          () => exportPrimerCatalog(this.buildQuery()),
          `引物库_${excelTimestamp()}.xlsx`,
        );
      } catch (error) {
        notifyApiError(error, { messages: { default: '导出失败' } });
      } finally {
        this.exporting = false;
      }
    },
    handleSaved() {
      this.editingRow = null;
      this.load();
    },
    handleImported() {
      this.listQuery.page = 1;
      this.load();
    },
  },
};
</script>

<style scoped>
.primer-page {
  position: relative;
  min-height: 100%;
  padding: var(--list-page-padding);
  background: var(--list-page-bg);
}

.workbench-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: var(--list-surface-padding-y) var(--list-surface-padding-x);
  margin-bottom: var(--list-page-gap);
  background: var(--list-surface-bg);
  border: var(--list-surface-border);
  border-radius: var(--list-surface-radius);
  box-shadow: var(--list-surface-shadow);
}

.page-header-band {
  display: flex;
  gap: 16px;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: linear-gradient(90deg, #e6f0ff 0%, #f2faf7 46%, var(--el-bg-color) 100%);
  border: 1px solid rgb(191 219 254 / 45%);
  border-radius: var(--list-mid-radius);
}

.page-title {
  margin: 0;
  font-size: var(--list-page-title-size);
  font-weight: var(--list-page-title-weight);
}

.page-subtitle {
  margin: 6px 0 0;
  color: var(--list-page-subtitle-color);
  font-size: var(--list-page-subtitle-size);
}

.header-actions {
  display: flex;
  flex-shrink: 0;
  gap: 8px;
  align-items: center;
}

.header-actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

.total-count {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  white-space: nowrap;
}

.stats-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 8px;
}

.stat-tile {
  position: relative;
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  min-height: 58px;
  padding: 8px 12px 8px 14px;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
  background: var(--list-mid-bg);
  border: var(--list-mid-border);
  border-radius: var(--list-mid-radius);
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease, background-color 0.18s ease;
}

.stat-tile::before {
  position: absolute;
  top: 14px;
  left: 0;
  width: 4px;
  height: 28px;
  content: '';
  border-radius: 0 999px 999px 0;
}

.stat-copy {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.stat-label {
  overflow: hidden;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stat-copy small {
  overflow: hidden;
  color: var(--el-text-color-placeholder);
  font-size: 12px;
  line-height: 18px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stat-value {
  color: var(--el-text-color-primary);
  font-size: 22px;
  font-weight: 600;
  line-height: 1;
}

.stat-tile:hover {
  background: var(--el-bg-color);
  border-color: #dce3ec;
  box-shadow: 0 8px 20px rgb(15 23 42 / 7%);
  transform: translateY(-2px);
}

.stat-tile.is-active {
  background: var(--el-bg-color);
  border-color: transparent;
  box-shadow: 0 6px 18px var(--stat-glow), 0 0 0 1.5px var(--stat-ring);
}

.stat-tile.is-active .stat-label {
  color: var(--el-text-color-primary);
  font-weight: 600;
}

.tone-blue { --stat-ring: rgb(64 158 255 / 34%); --stat-glow: rgb(64 158 255 / 12%); }
.tone-blue::before { background: var(--el-color-primary); }
.tone-purple { --stat-ring: rgb(139 92 246 / 34%); --stat-glow: rgb(139 92 246 / 12%); }
.tone-purple::before { background: #8b5cf6; }
.tone-orange { --stat-ring: rgb(255 159 67 / 38%); --stat-glow: rgb(255 159 67 / 13%); }
.tone-orange::before { background: #ff9f43; }
.tone-teal { --stat-ring: rgb(20 184 166 / 36%); --stat-glow: rgb(20 184 166 / 12%); }
.tone-teal::before { background: #14b8a6; }
.tone-slate { --stat-ring: rgb(100 116 139 / 36%); --stat-glow: rgb(100 116 139 / 12%); }
.tone-slate::before { background: #64748b; }

.filter-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  padding-top: 10px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.filter-name {
  flex: 3 1 140px;
  width: auto;
  min-width: 120px;
}

.filter-sequence,
.filter-check,
.filter-note {
  flex: 2 1 120px;
  width: auto;
  min-width: 120px;
}

.filter-item {
  flex: 1 1 120px;
  width: auto;
}

.check-header,
.check-cell {
  display: flex;
  gap: 2px;
  align-items: center;
  justify-content: center;
  height: 100%;
  cursor: pointer;
}

.check-menu {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  color: var(--el-text-color-secondary);
  cursor: pointer;
  background: transparent;
  border: 0;
}

.check-readonly {
  pointer-events: none;
}

.list-filter-actions {
  margin-left: auto;
}

.sheet-hint {
  margin: 0 0 8px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 18px;
}

.sheet-wrap {
  --vxe-ui-font-size-small: 14px;

  width: 100%;
  outline: none;
  user-select: none;
}

.sheet-stage {
  position: relative;
  width: 100%;
}

.sheet-wrap :deep(.vxe-body--column),
.sheet-wrap :deep(.vxe-header--column) {
  cursor: cell;
  user-select: none;
}

.sheet-wrap :deep(.vxe-cell--col-resizable) {
  cursor: col-resize;
}

.sheet-wrap :deep(.vxe-header--column) {
  font-weight: 600;
  background: var(--list-table-header-bg, var(--el-fill-color-light));
}

.sheet-wrap :deep(.vxe-header--column.wb-hf-cell) {
  cursor: pointer;
}

.sheet-wrap :deep(.vxe-body--column.col--selected) {
  box-shadow: none !important;
}

.sheet-wrap :deep(.vxe-body--row.row--hover > .vxe-body--column),
.sheet-wrap :deep(.vxe-body--row:hover > .vxe-body--column),
.sheet-wrap :deep(.vxe-table--fixed-left-wrapper .vxe-body--row.row--hover > .vxe-body--column),
.sheet-wrap :deep(.vxe-table--fixed-right-wrapper .vxe-body--row.row--hover > .vxe-body--column) {
  background-color: var(--vxe-ui-table-row-hover-background-color);
}

.sheet-wrap :deep(.is-sequence) {
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 15px;
}

.sheet-wrap :deep(.is-inactive) {
  color: var(--el-text-color-secondary);
}

.sheet-wrap :deep(.sheet-actions),
.sheet-wrap :deep(.sheet-actions *) {
  cursor: pointer;
}

.sheet-range {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 8;
  display: none;
  box-sizing: border-box;
  pointer-events: none;
  background: color-mix(in srgb, var(--el-color-primary) 10%, transparent);
  border: 2px solid var(--el-color-primary);
  will-change: width, height, transform;
}

@media (max-width: 760px) {
  .page-header-band,
  .header-actions {
    flex-wrap: wrap;
  }

  .page-header-band {
    align-items: flex-start;
    flex-direction: column;
  }

  .stats-strip {
    grid-template-columns: 1fr;
  }

  .filter-item,
  .filter-name,
  .filter-sequence,
  .filter-check,
  .filter-note {
    flex: 1 1 120px;
    width: auto;
  }
}

html.dark .page-header-band {
  background: var(--el-fill-color-extra-light);
  border-color: var(--el-border-color-light);
}

html.dark .stat-tile:hover {
  border-color: var(--el-border-color-light);
}
</style>
