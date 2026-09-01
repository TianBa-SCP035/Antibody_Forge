<template>
  <div class="mega-flow-order-page">
    <AdvancedOpsBar v-model="showAdvancedOps">
      <el-button type="warning" :icon="Download" @click="handleListExport">
        列表导出
      </el-button>
    </AdvancedOpsBar>

    <section class="workbench-panel">
      <div class="page-header-band">
        <div>
          <h1 class="page-title">流式工单总览</h1>
          <p class="page-subtitle">维护样本板、细胞板与下发状态，在列表中查看工单摘要。</p>
        </div>
        <div class="header-actions">
          <span class="total-count">共 {{ total }} 条工单</span>
          <el-button
            type="primary"
            :icon="Plus"
            :class="{ 'no-permission-btn': !canEdit() }"
            :title="!canEdit() ? '您没有权限新建流式工单' : ''"
            @click="createDraft"
          >
            新建
          </el-button>
        </div>
      </div>

      <div class="stats-strip">
        <div
          v-for="item in statusOptions"
          :key="item.value"
          class="stat-tile"
          :class="[
            `stat-tone-${item.value}`,
            { 'stat-tile-active': listQuery.status === item.value },
          ]"
          @click="toggleStatus(item.value)"
        >
          <span class="stat-label">{{ item.label }}</span>
          <strong class="stat-value">{{ stats[item.value] || 0 }}</strong>
        </div>
      </div>

      <div class="filter-strip list-filter-controls">
        <el-input
          v-model="listQuery.keyword"
          class="filter-item filter-keyword"
          clearable
          placeholder="订单编号 / 订单名称"
          :prefix-icon="Search"
          @keyup.enter="handleFilter"
        />
        <el-select
          v-model="listQuery.orderType"
          class="filter-item"
          clearable
          placeholder="检测类型"
          @change="handleFilter"
        >
          <el-option
            v-for="item in orderTypeOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
        <el-select
          v-model="listQuery.status"
          class="filter-item"
          clearable
          placeholder="状态"
          @change="handleFilter"
        >
          <el-option
            v-for="item in statusOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
        <el-input
          v-model="listQuery.project_no"
          class="filter-item"
          clearable
          placeholder="项目号"
          @keyup.enter="handleFilter"
        />
        <el-input
          v-model="listQuery.target"
          class="filter-item"
          clearable
          placeholder="靶点"
          @keyup.enter="handleFilter"
        />
        <el-input
          v-model="listQuery.sample_plate_barcode"
          class="filter-item"
          clearable
          placeholder="样本板条码"
          @keyup.enter="handleFilter"
        />
        <el-input
          v-model="listQuery.cell_plate_barcode"
          class="filter-item"
          clearable
          placeholder="细胞板条码"
          @keyup.enter="handleFilter"
        />
        <button
          type="button"
          class="list-advanced-trigger"
          :class="{ 'is-active': showAdvancedOps }"
          title="高级操作"
          @click="showAdvancedOps = !showAdvancedOps"
        >
          <el-icon><Tools /></el-icon>
        </button>
        <div class="filter-actions list-filter-actions">
          <el-button class="list-filter-action-button" type="primary" :icon="Search" @click="handleFilter">查询</el-button>
          <el-button class="list-filter-action-button" :icon="Refresh" @click="resetFilter">重置</el-button>
        </div>
      </div>
    </section>

    <div v-if="listLoadError" class="preview-banner">
      工单列表加载失败，请稍后重试或联系管理员确认接口与权限。
    </div>

    <el-card shadow="never" class="list-table-card">
      <el-table
        v-loading="listLoading"
        :data="list"
        border
        stripe
        highlight-current-row
        size="large"
        class="list-data-table"
        style="width: 100%"
      >
        <!-- 列宽：全部用 min-width，表格会按这些最小值动态分配剩余空间；总宽不够则横向滚动 -->
        <el-table-column label="订单编号" prop="orderNum" fixed min-width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="list-code-text is-clickable" @click="goView(row)">{{ row.orderNum || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="订单名称" prop="orderName" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.orderName || '—' }}</template>
        </el-table-column>
        <el-table-column label="类型" min-width="80" align="center">
          <template #default="{ row }">{{ orderTypeLabel(row.orderType) }}</template>
        </el-table-column>
        <el-table-column label="优先级" min-width="80" align="center">
          <template #default="{ row }">
            <el-tag class="list-status-tag" :type="priorityTagType(row.priority)" effect="plain">
              {{ priorityLabel(row.priority) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="项目号" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ formatArray(row.project_nos) }}</template>
        </el-table-column>
        <el-table-column label="靶点" min-width="100" show-overflow-tooltip>
          <template #default="{ row }">{{ formatArray(row.targets) }}</template>
        </el-table-column>
        <el-table-column label="样本板" min-width="100" show-overflow-tooltip>
          <template #default="{ row }">{{ formatArray(row.sample_plate_barcodes) }}</template>
        </el-table-column>
        <el-table-column label="细胞板" min-width="100" show-overflow-tooltip>
          <template #default="{ row }">{{ formatArray(row.cell_plate_barcodes) }}</template>
        </el-table-column>
        <el-table-column label="备注" prop="remark" min-width="100" show-overflow-tooltip>
          <template #default="{ row }">{{ row.remark || '—' }}</template>
        </el-table-column>
        <el-table-column label="状态" prop="status" align="center" min-width="90">
          <template #default="{ row }">
            <el-tag class="list-status-tag" :type="statusTagType(row)" effect="plain">
              {{ statusLabel(row) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建人" prop="created_by" min-width="90" align="center" />
        <el-table-column label="发送时间" prop="sent_at" min-width="160" align="center">
          <template #default="{ row }">{{ row.sent_at || '—' }}</template>
        </el-table-column>
        <el-table-column label="更新时间" prop="updated_at" min-width="160" align="center" />
        <el-table-column label="操作" fixed="right" width="240" align="center">
          <template #default="{ row }">
            <el-button-group>
              <el-button class="list-table-action-btn" type="primary" plain :icon="View" @click="goView(row)">详情</el-button>
              <el-button
                class="list-table-action-btn"
                type="warning"
                plain
                :icon="Edit"
                :class="{ 'no-permission-btn': !canEdit() }"
                :title="!canEdit() ? '您没有权限操作流式工单' : ''"
                @click="goOperate(row)"
              >
                操作
              </el-button>
              <el-button
                class="list-table-action-btn"
                type="success"
                plain
                :icon="CopyDocument"
                :class="{ 'no-permission-btn': !canEdit() }"
                :title="!canEdit() ? '您没有权限复制流式工单' : ''"
                @click="copyRow(row)"
              >
                复制
              </el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-show="total > 0"
        v-model:current-page="listQuery.page"
        v-model:page-size="listQuery.limit"
        :total="total"
        :page-sizes="[20, 50, 100, 200]"
        layout="total, sizes, prev, pager, next, jumper"
        class="list-pagination"
        @size-change="fetchList"
        @current-change="fetchList"
      />
    </el-card>
  </div>
</template>

<script>
import {
  CopyDocument,
  Download,
  Edit,
  Plus,
  Refresh,
  Search,
  Tools,
  View,
} from '@element-plus/icons-vue';
import {
  ElButton,
  ElButtonGroup,
  ElCard,
  ElIcon,
  ElInput,
  ElMessage,
  ElOption,
  ElPagination,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus';
import { useUserStore } from '@vben/stores';

import {
  fetchFlowWorkOrderList,
  fetchFlowWorkOrderMeta,
  exportFlowWorkOrderList,
} from '#/api/megaAutomation';
import AdvancedOpsBar from '#/components/AdvancedOpsBar.vue';
import { downloadListExcel, excelTimestamp } from '#/utils/downloadExcel';
import {
  canEditMegaFlowWorkOrder,
} from '#/utils/megaPermission';
import {
  orderStatusTagType,
  resolveOrderDisplayLabel,
  resolveOrderDisplayStatus,
} from '#/utils/megaFlowWorkOrderStatus';

const DEFAULT_STATUS_OPTIONS = [
  { value: 'draft', label: '草稿' },
  { value: 'validated', label: '已校验' },
  { value: 'sent', label: '已发送' },
  { value: 'running', label: '执行中' },
  { value: 'paused', label: '已暂停' },
  { value: 'execution_failed', label: '执行失败' },
  { value: 'completed', label: '已完成' },
  { value: 'failed', label: '校验失败' },
  { value: 'cancelled', label: '已作废' },
];

function emptyQuery() {
  return {
    page: 1,
    limit: 20,
    keyword: '',
    orderType: '',
    status: '',
    project_no: '',
    target: '',
    sample_plate_barcode: '',
    cell_plate_barcode: '',
  };
}

export default {
  name: 'MegaFlowWorkOrderList',
  components: {
    ElButton,
    ElButtonGroup,
    ElCard,
    ElIcon,
    ElInput,
    ElOption,
    ElPagination,
    ElSelect,
    ElTable,
    ElTableColumn,
    ElTag,
    AdvancedOpsBar,
    Tools,
  },
  setup() {
    const userStore = useUserStore();
    return {
      userStore,
      CopyDocument,
      Download,
      Edit,
      Plus,
      Refresh,
      Search,
      View,
    };
  },
  data() {
    return {
      list: [],
      total: 0,
      stats: {},
      listLoading: false,
      showAdvancedOps: false,
      listQuery: emptyQuery(),
      statusOptions: DEFAULT_STATUS_OPTIONS,
      orderTypeOptions: [{ value: 'TITER', label: '效价' }],
      priorityOptions: [
        { value: 'high', label: '高' },
        { value: 'normal', label: '普通' },
        { value: 'low', label: '低' },
      ],
      listLoadError: false,
      fetchSequence: 0,
      listLoaded: false,
    };
  },
  computed: {
    currentUserInfo() {
      return this.userStore.userInfo || {};
    },
  },
  created() {
    this.loadMeta();
    this.fetchList().finally(() => {
      this.listLoaded = true;
    });
  },
  activated() {
    if (this.listLoaded) {
      this.fetchList();
    }
  },
  methods: {
    async loadMeta() {
      try {
        const data = await fetchFlowWorkOrderMeta();
        this.statusOptions = data?.statuses?.length ? data.statuses : DEFAULT_STATUS_OPTIONS;
        this.orderTypeOptions = data?.orderTypes?.length ? data.orderTypes : this.orderTypeOptions;
        this.priorityOptions = data?.priorities?.length ? data.priorities : this.priorityOptions;
      } catch {
        // 列表仍可用，元数据失败时使用本地默认值。
      }
    },
    async fetchList() {
      const requestId = ++this.fetchSequence;
      this.listLoading = true;
      try {
        const data = await fetchFlowWorkOrderList(this.listQuery);
        if (requestId !== this.fetchSequence) return;
        this.list = data?.items || [];
        this.total = data?.total || 0;
        this.stats = data?.stats || {};
        this.listLoadError = false;
      } catch (error) {
        if (requestId !== this.fetchSequence) return;
        this.list = [];
        this.total = 0;
        this.stats = {};
        this.listLoadError = true;
        ElMessage.error(error?.message || '工单列表加载失败');
      } finally {
        if (requestId === this.fetchSequence) this.listLoading = false;
      }
    },
    handleFilter() {
      this.listQuery.page = 1;
      this.fetchList();
    },
    async handleListExport() {
      try {
        await downloadListExcel(
          () => exportFlowWorkOrderList(this.listQuery),
          `流式工单总览_${excelTimestamp()}.xlsx`,
        );
      } catch (error) {
        ElMessage.error(error?.message || '列表导出失败，请重试');
      }
    },
    resetFilter() {
      this.listQuery = emptyQuery();
      this.fetchList();
    },
    toggleStatus(status) {
      this.listQuery.status = this.listQuery.status === status ? '' : status;
      this.handleFilter();
    },
    statusLabel(row) {
      return resolveOrderDisplayLabel(row);
    },
    statusTagType(row) {
      return orderStatusTagType(resolveOrderDisplayStatus(row));
    },
    orderTypeLabel(value) {
      return this.orderTypeOptions.find((item) => item.value === value)?.label || value || '-';
    },
    priorityLabel(value) {
      return this.priorityOptions.find((item) => item.value === value)?.label || '普通';
    },
    priorityTagType(value) {
      if (value === 'high') return 'danger';
      if (value === 'low') return 'info';
      return 'warning';
    },
    formatArray(value) {
      return Array.isArray(value) && value.length ? value.join(', ') : '—';
    },
    canEdit() {
      return canEditMegaFlowWorkOrder(this.currentUserInfo);
    },
    createDraft() {
      if (!this.canEdit()) {
        ElMessage.warning('您没有权限新建流式工单');
        return;
      }
      this.$router.push({
        name: 'MegaFlowWorkOrderDetail',
        query: { mode: 'edit' },
      });
    },
    goView(row) {
      this.$router.push({
        name: 'MegaFlowWorkOrderDetail',
        query: { id: row.id, mode: 'view' },
      });
    },
    goOperate(row) {
      if (!this.canEdit()) {
        ElMessage.warning('您没有权限操作流式工单');
        return;
      }
      this.$router.push({
        name: 'MegaFlowWorkOrderDetail',
        query: { id: row.id, mode: 'edit' },
      });
    },
    copyRow(row) {
      if (!this.canEdit()) {
        ElMessage.warning('您没有权限复制流式工单');
        return;
      }
      this.$router.push({
        name: 'MegaFlowWorkOrderDetail',
        query: { copyFrom: row.id, mode: 'edit' },
      });
    },
  },
};
</script>

<style scoped>
.mega-flow-order-page {
  position: relative;
  min-height: 100%;
  padding: var(--list-page-padding);
  font-size: 14px;
  color: #303133;
  background: var(--list-page-bg);
}

/* 标题 + 统计 + 筛选同一白底，表格单独；比两两组合更不散 */
.workbench-panel {
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
  min-width: 0;
  padding: 12px 16px;
  margin: 0;
  border: 1px solid rgb(191 219 254 / 45%);
  border-radius: var(--list-mid-radius);
  background: linear-gradient(90deg, #e6f0ff 0%, #f2faf7 46%, #ffffff 100%);
}

.page-title {
  margin: 0;
  font-size: var(--list-page-title-size);
  font-weight: var(--list-page-title-weight);
  letter-spacing: -0.01em;
}

.page-subtitle {
  margin: 4px 0 0;
  color: var(--list-page-subtitle-color);
  font-size: var(--list-page-subtitle-size);
  font-weight: var(--list-page-subtitle-weight);
}

.header-actions {
  display: flex;
  flex-shrink: 0;
  gap: 12px;
  align-items: center;
}

.total-count {
  font-size: 13px;
  color: #909399;
  white-space: nowrap;
}

.preview-banner {
  padding: 10px 14px;
  margin: 0 0 12px;
  font-size: 13px;
  color: #8a5a00;
  background: #fff7e6;
  border: 1px solid #ffd591;
  border-radius: var(--list-mid-radius);
}

.stats-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(118px, 1fr));
  gap: 8px;
  padding: 12px 0;
  margin: 0;
  border-bottom: 1px solid #eef0f4;
}

.stat-tile {
  position: relative;
  padding: 11px 12px 11px 16px;
  overflow: hidden;
  cursor: pointer;
  background: var(--list-mid-bg);
  border: var(--list-mid-border);
  border-radius: var(--list-mid-radius);
  box-shadow: none;
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease,
    background-color 0.15s ease,
    transform 0.15s ease;
  --stat-accent: #5b9ef0;
}

.stat-tile::before {
  position: absolute;
  top: 10px;
  bottom: 10px;
  left: 0;
  width: 4px;
  content: '';
  background: var(--stat-accent);
  border-radius: 0 4px 4px 0;
}

.stat-tile:hover {
  background: #fff;
  border-color: color-mix(in srgb, var(--stat-accent) 38%, #fff);
  box-shadow: 0 4px 12px rgb(15 23 42 / 6%);
  transform: translateY(-1px);
}

.stat-tile:active {
  transform: scale(0.98);
}

.stat-tile-active {
  background: color-mix(in srgb, var(--stat-accent) 14%, #fff);
  border-color: color-mix(in srgb, var(--stat-accent) 42%, #fff);
  box-shadow:
    0 0 0 1px color-mix(in srgb, var(--stat-accent) 28%, #fff),
    0 4px 12px rgb(15 23 42 / 6%);
}

.stat-tile-active:hover {
  background: color-mix(in srgb, var(--stat-accent) 14%, #fff);
  border-color: color-mix(in srgb, var(--stat-accent) 42%, #fff);
  box-shadow:
    0 0 0 1px color-mix(in srgb, var(--stat-accent) 28%, #fff),
    0 4px 12px rgb(15 23 42 / 6%);
  transform: translateY(-1px);
}

.stat-tile-active:active,
.stat-tile-active:hover:active {
  transform: scale(0.98);
}

/* 状态色条：按 status value 绑 class */
.stat-tone-draft {
  --stat-accent: #5b9ef0;
}

.stat-tone-validated {
  --stat-accent: #9b85f0;
}

.stat-tone-sent {
  --stat-accent: #2fc4b2;
}

.stat-tone-running {
  --stat-accent: #f08a3a;
}

.stat-tone-paused {
  --stat-accent: #ecc94b;
}

.stat-tone-execution_failed {
  --stat-accent: #ef7878;
}

.stat-tone-completed {
  --stat-accent: #45c97a;
}

.stat-tone-failed {
  --stat-accent: #ec6aad;
}

.stat-tone-cancelled {
  --stat-accent: #8b97a8;
}

.stat-label {
  display: block;
  font-size: 12px;
  color: #909399;
}

.stat-tile-active .stat-label {
  font-weight: 600;
  color: #606266;
}

.stat-value {
  display: block;
  margin-top: 5px;
  font-size: 22px;
  font-weight: 700;
  line-height: 1.15;
  color: #303133;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}

.filter-strip {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) repeat(6, minmax(0, 1fr)) auto auto;
  gap: 10px var(--list-filter-action-gap);
  align-items: center;
  padding: 12px 2px 2px;
}

.filter-item,
.filter-keyword {
  width: 100%;
  min-width: 0;
}

.filter-strip :deep(.el-select),
.filter-strip :deep(.el-input) {
  width: 100%;
}

.filter-actions {
  flex-shrink: 0;
}

@media (max-width: 960px) {
  .page-header-band {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (prefers-reduced-motion: reduce) {
  .stat-tile {
    transition: none;
  }

  .stat-tile:hover,
  .stat-tile-active:hover {
    transform: none;
  }
}
</style>
