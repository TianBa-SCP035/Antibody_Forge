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
        <div class="title-group">
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
          class="stat-tile stat-tile-interactive"
          :class="[item.tone, { 'stat-tile-active': listQuery.family === item.value }]"
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
        <div class="filter-actions list-filter-actions">
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
      <WorkbenchSheet
        :cell-config="cellConfig"
        :keyboard-config="keyboardConfig"
        :row-class-name="rowClassName"
        empty-text="没有引物"
        @cell-dblclick="onDblclick"
      >
        <template #columns>
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
            v-for="column in sheetColumns"
            :key="column.key"
            :field="column.key"
            :title="column.label"
            :min-width="column.minWidth"
            :width="sheetColumnWidth(column)"
            :align="column.align"
            :class-name="column.mono ? 'is-sequence' : ''"
          >
            <template #header>
              <WorkbenchHeaderLabel
                v-if="headerMenuStates[column.key]"
                :label="column.label"
                v-bind="headerMenuStates[column.key]"
              />
              <template v-else>{{ column.label }}</template>
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
        </template>
        <template #actions="{ row }">
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
      </WorkbenchSheet>
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
import { VxeColumn } from 'vxe-table';

import AdvancedOpsBar from '#/components/AdvancedOpsBar.vue';
import ListFilterSelect from '#/components/ListFilterSelect.vue';
import {
  createColumnOrder,
  sheetSelectionMixin,
  WorkbenchHeaderFilterChip,
  WorkbenchHeaderLabel,
  WorkbenchHeaderMenu,
  workbenchHeaderMenuMixin,
  WorkbenchSheet,
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
  PRIMER_EDIT,
} from '#/api/primerCatalog';
import { clearPrimerCatalogCache } from '../library/primerCatalogOptions';
import { downloadListExcel, excelTimestamp } from '#/utils/downloadExcel';
import { listPageMixin } from '#/utils/listPage';
import { listTableLockMixin } from '#/utils/listTableLock';
import { hasAccessCode } from '#/utils/accessCode';

import PrimerEditorDialog from './PrimerEditorDialog.vue';
import PrimerImportDialog from './PrimerImportDialog.vue';
import {
  checkSequence,
  directionLabel,
  libraryHint,
  libraryTone,
  PRESET_LIBRARIES,
} from './primerSeries';

const COLUMNS = Object.freeze([
  { key: 'name', label: '名称', minWidth: 160 },
  { key: 'family', label: '系列', minWidth: 120 },
  { key: 'direction', label: '方向', minWidth: 60, align: 'center' },
  { key: 'short_sequence', label: '显示序列', minWidth: 160, mono: true },
  { key: 'check_sequence', label: '核对序列', minWidth: 160, mono: true },
  { key: 'note', label: '备注', minWidth: 180 },
  { key: 'active', label: '状态', width: 90, align: 'center' },
]);
const SHEET_COLUMN_ORDER = createColumnOrder('primerLibrarySheetColumnOrder', COLUMNS);

// 核对序列是算出来的，只有顶部筛选
const PRIMER_HEADER_COLUMNS = Object.freeze({
  name: { type: 'text', label: '名称', values: 'recent', top: { query: 'name', kind: 'contains' } },
  family: { type: 'enum', label: '系列', values: 'all', top: { query: 'family' } },
  direction: { type: 'enum', label: '方向', values: 'all', top: { query: 'direction' } },
  short_sequence: { type: 'text', label: '显示序列', values: 'search', top: { query: 'sequence', kind: 'contains' } },
  note: { type: 'text', label: '备注', values: 'search', top: { query: 'note', kind: 'contains' } },
  active: { type: 'enum', label: '状态', values: 'all', top: { query: 'status' } },
});

const CELL_CONFIG = Object.freeze({ height: 40 });
// 只读表格：不开 Delete/Enter，免得 vxe 清空或进入编辑
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
    WorkbenchHeaderFilterChip,
    WorkbenchHeaderLabel,
    WorkbenchHeaderMenu,
    WorkbenchSheet,
  },
  mixins: [listTableLockMixin, listPageMixin, workbenchHeaderMenuMixin, sheetSelectionMixin],
  listFilterKey: 'primerLibrary',
  workbenchSheet: { order: SHEET_COLUMN_ORDER },
  setup() {
    return {
      userStore: useUserStore(),
      cellConfig: CELL_CONFIG,
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
      list: [],
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
      return hasAccessCode(this.userStore.userInfo, PRIMER_EDIT);
    },
    seriesCards() {
      return [
        { label: '全部', value: '', count: this.statsTotal, hint: '当前筛选', tone: 'stat-blue' },
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
    sheetDirectTextValue(row, key) {
      return row ? cellText(row, key) : '';
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
        this.clearSheetRange();
        this.list = data.items || [];
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
      for (const row of this.list) next.add(row.id);
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
      const index = Number.isInteger(rowIndex) ? rowIndex : this.list.findIndex((item) => item.id === row.id);
      if (event.shiftKey && this._checkAnchor >= 0 && index >= 0) {
        const start = Math.min(this._checkAnchor, index);
        const end = Math.max(this._checkAnchor, index);
        for (let cursor = start; cursor <= end; cursor += 1) {
          const item = this.list[cursor];
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
        if (this.list.length === 1 && this.listQuery.page > 1) this.listQuery.page -= 1;
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

<style scoped src="#/components/workbench/workbenchPanel.css"></style>
<style scoped>
.primer-page {
  position: relative;
  min-height: 100%;
  padding: var(--list-page-padding);
  background: var(--list-page-bg);
}

.stats-strip {
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
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

.sheet-hint {
  margin: 0 0 8px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 18px;
}

.sheet-wrap :deep(.vxe-header--column) {
  font-weight: 600;
  background: var(--list-table-header-bg, var(--el-fill-color-light));
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

@media (max-width: 760px) {
  .filter-item,
  .filter-name,
  .filter-sequence,
  .filter-check,
  .filter-note {
    flex: 1 1 120px;
    width: auto;
  }
}
</style>
