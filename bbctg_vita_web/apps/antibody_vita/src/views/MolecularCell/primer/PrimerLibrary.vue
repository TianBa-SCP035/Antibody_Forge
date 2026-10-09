<template>
  <div class="primer-page">
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
          :class="[item.tone, { 'is-active': query.family === item.value }]"
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
          v-model="query.name"
          class="filter-name"
          clearable
          placeholder="名称"
          @keyup.enter="search"
          @clear="search"
        />
        <ElInput
          v-model="query.sequence"
          class="filter-sequence"
          clearable
          placeholder="显示序列"
          @keyup.enter="search"
          @clear="search"
        />
        <ElInput
          v-model="query.checkKeyword"
          class="filter-check"
          clearable
          placeholder="核对序列"
          @keyup.enter="search"
          @clear="search"
        />
        <ElInput
          v-model="query.note"
          class="filter-note"
          clearable
          placeholder="备注"
          @keyup.enter="search"
          @clear="search"
        />
        <ElSelect
          v-model="query.direction"
          class="filter-item"
          clearable
          placeholder="方向"
          @change="search"
        >
          <ElOption label="正向" value="F" />
          <ElOption label="反向" value="R" />
        </ElSelect>
        <ElSelect
          v-model="query.status"
          class="filter-item"
          clearable
          placeholder="状态"
          @change="search"
        >
          <ElOption label="启用" value="active" />
          <ElOption label="停用" value="inactive" />
        </ElSelect>
        <div class="list-filter-actions">
          <button
            type="button"
            class="list-advanced-trigger"
            :class="{ 'is-active': showAdvancedOps }"
            title="高级操作"
            @click="showAdvancedOps = !showAdvancedOps"
          >
            <ElIcon><Tools /></ElIcon>
          </button>
          <ElButton type="primary" :icon="Search" @click="search">查询</ElButton>
          <ElButton :icon="Refresh" @click="reset">重置</ElButton>
        </div>
      </div>
    </section>

    <ElCard shadow="never" class="list-table-card">
      <p class="sheet-hint">
        拖拽划选单元格，Ctrl+C 复制，右键取消选中。双击一行可编辑。
        <template v-if="selectionMode">勾选列可拖拽或按住 Shift 连选，表头菜单可当页全选、全部全选或取消。</template>
      </p>
      <div
        ref="wrapRef"
        class="sheet-wrap"
        tabindex="0"
        @copy="onCopy"
        @contextmenu="onContextMenu"
        @keydown="onKeydown"
        @mousedown="onMouseDown"
        @mouseover="onMouseOver"
        @selectstart="onSelectStart"
      >
        <div ref="stageRef" class="sheet-stage">
          <vxe-table
            ref="tableRef"
            v-loading="loading"
            :data="items"
            border
            show-overflow
            size="small"
            :row-config="{ keyField: 'id', isHover: true, height: 40 }"
            :column-config="{ resizable: true }"
            :mouse-config="{ selected: true }"
            :keyboard-config="keyboardConfig"
            :clip-config="{ isCopy: false, isCut: false, isPaste: false }"
            :row-class-name="rowClassName"
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
            <vxe-column title="操作" width="210" fixed="right" align="center">
              <template #default="{ row }">
                <div class="sheet-actions" @mousedown.stop @click.stop @dblclick.stop>
                  <ElButtonGroup>
                    <ElButton
                      class="list-table-action-btn"
                      type="primary"
                      plain
                      :class="{ 'no-permission-btn': !canEdit }"
                      @click="openEdit(row)"
                    >
                      编辑
                    </ElButton>
                    <ElButton
                      class="list-table-action-btn"
                      type="success"
                      plain
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

      <ElPagination
        v-show="total > 0"
        v-model:current-page="query.page"
        v-model:page-size="query.limit"
        :total="total"
        :page-sizes="[20, 50, 100, 200]"
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
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';

import { ArrowDown, Download, Plus, Refresh, Search, Tools, Upload } from '@element-plus/icons-vue';
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
import { notifyApiError } from '#/api/errors';
import {
  batchDeletePrimers,
  batchUpdatePrimers,
  deletePrimer,
  exportPrimerCatalog,
  fetchPrimerCatalog,
  fetchPrimerIds,
  type PrimerItem,
  type PrimerListQuery,
  savePrimer,
} from '#/api/primerCatalog';
import { downloadListExcel, excelTimestamp } from '#/utils/downloadExcel';
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

type StatusFilter = '' | 'active' | 'inactive';
type SheetColumn = {
  key: string;
  title: string;
  minWidth?: number;
  width?: number;
  align?: 'center';
  mono?: boolean;
};

const columns: SheetColumn[] = [
  { key: 'name', title: '名称', minWidth: 160 },
  { key: 'family', title: '系列', minWidth: 120 },
  { key: 'direction', title: '方向', minWidth: 60, align: 'center' as const },
  { key: 'short_sequence', title: '显示序列', minWidth: 160, mono: true },
  { key: 'check_sequence', title: '核对序列', minWidth: 160, mono: true },
  { key: 'note', title: '备注', minWidth: 180 },
  { key: 'active', title: '状态', width: 90, align: 'center' as const },
];

const keyboardConfig = {
  isArrow: true,
  isShift: true,
  isTab: true,
  isEdit: false,
  isDel: false,
  isEnter: false,
  isClip: false,
};

const userStore = useUserStore();
const canEdit = computed(() => canEditPrimerLibrary(userStore.userInfo));
const query = reactive({
  name: '',
  sequence: '',
  checkKeyword: '',
  note: '',
  family: '',
  direction: '',
  status: '' as StatusFilter,
  page: 1,
  limit: 20,
});
const items = ref<PrimerItem[]>([]);
const total = ref(0);
const statsTotal = ref(0);
const libraryStats = ref<{ count: number; name: string }[]>([]);
const loading = ref(false);
const exporting = ref(false);
const savingId = ref<null | number>(null);
const deletingId = ref<null | number>(null);
const editorVisible = ref(false);
const importVisible = ref(false);
const showAdvancedOps = ref(false);
const selectionMode = ref(false);
const batchFamily = ref('');
const batching = ref(false);
const selectedIds = ref(new Set<number>());
let checkDrag: { checking: boolean } | null = null;
let checkAnchor = -1;
const editingRow = ref<null | PrimerItem>(null);
let requestId = 0;

const seriesCards = computed(() => [
  { label: '全部', value: '', count: statsTotal.value, hint: '当前筛选', tone: 'tone-blue' },
  ...libraryStats.value.map((item, index) => ({
    label: item.name,
    value: item.name,
    count: item.count,
    hint: libraryHint(item.name),
    tone: libraryTone(item.name, index),
  })),
]);
const libraryNames = computed(() => {
  const names = PRESET_LIBRARIES.map((item) => item.value as string);
  for (const item of libraryStats.value) {
    if (!names.includes(item.name)) names.push(item.name);
  }
  return names;
});

const {
  wrapRef,
  stageRef,
  overlayRef,
  tableRef,
  onContextMenu,
  onMouseDown,
  onMouseOver,
  onSelectStart,
  onScroll,
  onCellSelected,
  onKeydown,
  onCopy,
} = useSheetRange({
  rows: items,
  columns,
  text: cellText,
});

function cellText(row: PrimerItem, key: string) {
  if (key === 'active') return row.active ? '启用' : '停用';
  if (key === 'direction') return directionLabel(row.direction);
  if (key === 'check_sequence') return checkSequence(row.short_sequence);
  const value = row[key as keyof PrimerItem];
  return value == null ? '' : String(value);
}

function displayCell(row: PrimerItem, key: string) {
  return cellText(row, key) || '—';
}

function rowClassName({ row }: { row: PrimerItem }) {
  return row.active ? '' : 'is-inactive';
}

function replaceSelected(next: Set<number>) {
  selectedIds.value = next;
}

function clearSelected() {
  replaceSelected(new Set());
  checkAnchor = -1;
}

function listPayload(): PrimerListQuery {
  return {
    name: query.name.trim() || undefined,
    sequence: query.sequence.trim() || undefined,
    check_keyword: query.checkKeyword.trim() || undefined,
    note: query.note.trim() || undefined,
    family: query.family || undefined,
    direction: query.direction || undefined,
    active: query.status === '' ? undefined : query.status === 'active',
    page: query.page,
    limit: query.limit,
  };
}

async function load() {
  const current = ++requestId;
  loading.value = true;
  try {
    const data = await fetchPrimerCatalog(listPayload());
    if (current !== requestId) return;
    items.value = data.items || [];
    total.value = data.total || 0;
    statsTotal.value = data.stats?.total || 0;
    libraryStats.value = data.stats?.families || [];
  } catch (error) {
    if (current === requestId) {
      notifyApiError(error, { messages: { default: '引物库加载失败' } });
    }
  } finally {
    if (current === requestId) loading.value = false;
  }
}

function search() {
  query.page = 1;
  clearSelected();
  load();
}

function reset() {
  Object.assign(query, {
    name: '',
    sequence: '',
    checkKeyword: '',
    note: '',
    family: '',
    direction: '',
    status: '',
    page: 1,
  });
  clearSelected();
  load();
}

function selectPage() {
  const next = new Set(selectedIds.value);
  for (const row of items.value) next.add(row.id);
  replaceSelected(next);
}

function onSelectCommand(command: string) {
  if (command === 'clear') {
    clearSelected();
    return;
  }
  if (command === 'page') {
    selectPage();
    return;
  }
  selectAllMatching();
}

async function selectAllMatching() {
  try {
    const { page: _page, limit: _limit, ...filters } = listPayload();
    const data = await fetchPrimerIds(filters);
    replaceSelected(new Set(data.ids || []));
    if (!data.ids?.length) ElMessage.info('当前筛选下没有引物');
  } catch (error) {
    notifyApiError(error, { messages: { default: '全选失败' } });
  }
}

function onCheckDown(event: MouseEvent, row: PrimerItem, rowIndex: number) {
  if (event.button !== 0) return;
  const next = new Set(selectedIds.value);
  const index = Number.isInteger(rowIndex) ? rowIndex : items.value.findIndex((item) => item.id === row.id);
  if (event.shiftKey && checkAnchor >= 0 && index >= 0) {
    const start = Math.min(checkAnchor, index);
    const end = Math.max(checkAnchor, index);
    for (let cursor = start; cursor <= end; cursor += 1) {
      const item = items.value[cursor];
      if (item) next.add(item.id);
    }
    replaceSelected(next);
    return;
  }
  const checking = !next.has(row.id);
  if (checking) next.add(row.id);
  else next.delete(row.id);
  replaceSelected(next);
  checkAnchor = index;
  checkDrag = { checking };
}

function onCheckEnter(row: PrimerItem) {
  if (!checkDrag) return;
  const next = new Set(selectedIds.value);
  if (checkDrag.checking) next.add(row.id);
  else next.delete(row.id);
  replaceSelected(next);
}

function finishCheckDrag() {
  checkDrag = null;
}

function leaveSelection() {
  selectionMode.value = false;
  clearSelected();
  batchFamily.value = '';
}

function toggleSelectionMode() {
  if (!editable()) return;
  if (selectionMode.value) {
    leaveSelection();
    return;
  }
  selectionMode.value = true;
}

watch(showAdvancedOps, (open) => {
  if (!open) leaveSelection();
});

async function runBatch(action: { active?: boolean; family?: string; remove?: boolean }) {
  const ids = [...selectedIds.value];
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
  batching.value = true;
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
    } else {
      await batchUpdatePrimers({ ids, active: action.active });
      ElMessage.success(action.active ? '已启用' : '已停用');
    }
    batchFamily.value = '';
    clearSelected();
    await load();
  } catch (error) {
    notifyApiError(error, { messages: { default: '批量操作失败' } });
  } finally {
    batching.value = false;
  }
}

function selectSeries(value: string) {
  query.family = query.family === value ? '' : value;
  search();
}

function changePageSize() {
  query.page = 1;
  load();
}

function editable() {
  if (canEdit.value) return true;
  ElMessage.warning('您没有权限编辑引物库');
  return false;
}

function openCreate() {
  if (!editable()) return;
  editingRow.value = null;
  editorVisible.value = true;
}

function openEdit(row: PrimerItem) {
  if (!editable()) return;
  editingRow.value = row;
  editorVisible.value = true;
}

function openImport() {
  if (!editable()) return;
  importVisible.value = true;
}

function onDblclick({ row, column }: { row: PrimerItem; column?: { field?: string } }) {
  if (!column?.field) return;
  openEdit(row);
}

async function toggleActive(row: PrimerItem) {
  if (!editable()) return;
  if (row.active) {
    try {
      await ElMessageBox.confirm(`确认停用「${row.name}」？停用后不会出现在文库构建的引物选项里。`, '提示', {
        type: 'warning',
      });
    } catch {
      return;
    }
  }
  savingId.value = row.id;
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
    await load();
  } catch (error) {
    notifyApiError(error, { messages: { default: '状态更新失败' } });
  } finally {
    savingId.value = null;
  }
}

async function removeRow(row: PrimerItem) {
  if (!editable()) return;
  try {
    await ElMessageBox.confirm(
      `确认删除「${row.name}」？删除后不能恢复。已被文库工单使用的引物请改用停用。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除' },
    );
  } catch {
    return;
  }
  deletingId.value = row.id;
  try {
    await deletePrimer(row.id);
    ElMessage.success('已删除');
    if (items.value.length === 1 && query.page > 1) query.page -= 1;
    await load();
  } catch (error) {
    notifyApiError(error, { messages: { default: '删除失败' } });
  } finally {
    deletingId.value = null;
  }
}

async function handleExport() {
  exporting.value = true;
  try {
    await downloadListExcel(
      () => exportPrimerCatalog(listPayload()),
      `引物库_${excelTimestamp()}.xlsx`,
    );
  } catch (error) {
    notifyApiError(error, { messages: { default: '导出失败' } });
  } finally {
    exporting.value = false;
  }
}

function handleSaved() {
  editingRow.value = null;
  load();
}

function handleImported() {
  query.page = 1;
  load();
}

onMounted(() => {
  window.addEventListener('mouseup', finishCheckDrag);
  load();
});
onBeforeUnmount(() => {
  window.removeEventListener('mouseup', finishCheckDrag);
});
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
  background: linear-gradient(90deg, #e6f0ff 0%, #f2faf7 46%, #fff 100%);
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
  background: #fff;
  border-color: #dce3ec;
  box-shadow: 0 8px 20px rgb(15 23 42 / 7%);
  transform: translateY(-2px);
}

.stat-tile.is-active {
  background: #fff;
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
  border-top: 1px solid #edf1f7;
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
  background: var(--list-table-header-bg, #f5f7fa);
}

.sheet-wrap :deep(.vxe-body--column.col--selected) {
  box-shadow: none !important;
}

.sheet-wrap :deep(.is-sheet-selected) {
  background: var(--el-color-primary-light-9) !important;
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
  border: 2px solid var(--el-color-primary);
}

.sheet-range.is-scrolling {
  transition: none;
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
</style>
