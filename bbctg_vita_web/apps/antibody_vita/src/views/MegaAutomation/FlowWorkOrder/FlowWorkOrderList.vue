<template>
  <div class="app-container mega-flow-order-page">
    <section class="workbench-panel">
      <div class="page-header-band">
        <div>
          <h1 class="page-title">流式工单总览</h1>
          <p class="page-subtitle">维护样本板、细胞板与下发状态，在列表中查看工单摘要。</p>
        </div>
        <div class="header-actions">
          <span class="total-count">共 {{ total }} 条工单</span>
          <el-button type="primary" :disabled="!canEdit()" @click="createDraft">
            <el-icon><Plus /></el-icon>
            新建工单
          </el-button>
        </div>
      </div>

      <div class="stats-strip">
        <div
          v-for="item in statusOptions"
          :key="item.value"
          class="stat-tile"
          :class="{ 'stat-tile-active': listQuery.status === item.value }"
          @click="toggleStatus(item.value)"
        >
          <span class="stat-label">{{ item.label }}</span>
          <strong class="stat-value">{{ stats[item.value] || 0 }}</strong>
        </div>
      </div>

      <div class="filter-strip">
        <el-input
          v-model="listQuery.keyword"
          class="filter-item filter-keyword"
          clearable
          placeholder="订单编号 / 订单名称"
          :prefix-icon="Search"
          @keyup.enter="handleFilter"
        />
        <el-select
          v-model="listQuery.data_type"
          class="filter-item"
          clearable
          placeholder="检测类型"
          @change="handleFilter"
        >
          <el-option
            v-for="item in dataTypeOptions"
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
        <div class="filter-actions">
          <el-button type="primary" :icon="Search" @click="handleFilter">查询</el-button>
          <el-button :icon="Refresh" @click="resetFilter">重置</el-button>
        </div>
      </div>
    </section>

    <div v-if="backendUnavailable" class="preview-banner">
      当前数据库尚未初始化镁伽流式工单表或权限，页面已进入预览模式。可以先查看界面结构，保存和发送需建表后使用。
    </div>

    <el-card shadow="never" class="table-card">
      <el-table
        v-loading="listLoading"
        :data="list"
        border
        stripe
        highlight-current-row
        style="width: 100%"
        :header-cell-style="{ background: '#F5F7FA', color: '#606266', fontWeight: 'bold' }"
      >
        <!-- 列宽：全部用 min-width，表格会按这些最小值动态分配剩余空间；总宽不够则横向滚动 -->
        <el-table-column label="订单编号" prop="order_no" fixed min-width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="link-text" @click="goView(row)">{{ row.order_no || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="订单名称" prop="order_name" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.order_name || '—' }}</template>
        </el-table-column>
        <el-table-column label="检测类型" min-width="80" align="center">
          <template #default="{ row }">{{ dataTypeLabel(row.data_type) }}</template>
        </el-table-column>
        <el-table-column label="优先级" min-width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="priorityTagType(row.priority)" effect="plain" size="small">
              {{ priorityLabel(row.priority) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="项目号" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ formatArray(row.project_nos) }}</template>
        </el-table-column>
        <el-table-column label="靶点" min-width="80" show-overflow-tooltip>
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
        <el-table-column label="状态" prop="status" align="center" min-width="80">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row)" effect="plain">
              {{ statusLabel(row) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建人" prop="created_by" min-width="80" align="center" />
        <el-table-column label="发送时间" prop="sent_at" min-width="150" align="center">
          <template #default="{ row }">{{ row.sent_at || '—' }}</template>
        </el-table-column>
        <el-table-column label="更新时间" prop="updated_at" min-width="150" align="center" />
        <el-table-column label="操作" fixed="right" min-width="170" align="center">
          <template #default="{ row }">
            <el-button-group>
              <el-button class="table-action-btn" size="small" type="primary" plain @click="goView(row)">详情</el-button>
              <el-button
                class="table-action-btn"
                size="small"
                type="warning"
                plain
                :disabled="!canEdit()"
                @click="goOperate(row)"
              >
                操作
              </el-button>
              <el-button
                class="table-action-btn"
                size="small"
                type="success"
                plain
                :disabled="!canEdit()"
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
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        class="pagination"
        @size-change="fetchList"
        @current-change="fetchList"
      />
    </el-card>
  </div>
</template>

<script>
import {
  Plus,
  Refresh,
  Search,
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
} from '#/api/megaAutomation';
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
    data_type: '',
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
  },
  setup() {
    const userStore = useUserStore();
    return { userStore, Plus, Refresh, Search };
  },
  data() {
    return {
      list: [],
      total: 0,
      stats: {},
      listLoading: false,
      listQuery: emptyQuery(),
      statusOptions: DEFAULT_STATUS_OPTIONS,
      dataTypeOptions: [{ value: 'TITER', label: '效价' }],
      priorityOptions: [
        { value: 'high', label: '高' },
        { value: 'normal', label: '普通' },
        { value: 'low', label: '低' },
      ],
      backendUnavailable: false,
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
        this.dataTypeOptions = data?.data_types?.length ? data.data_types : this.dataTypeOptions;
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
        this.backendUnavailable = false;
      } catch (error) {
        if (requestId !== this.fetchSequence) return;
        this.list = [];
        this.total = 0;
        this.stats = {};
        this.backendUnavailable = true;
        ElMessage.error(error?.message || '工单列表加载失败');
      } finally {
        if (requestId === this.fetchSequence) this.listLoading = false;
      }
    },
    handleFilter() {
      this.listQuery.page = 1;
      this.fetchList();
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
    dataTypeLabel(value) {
      return this.dataTypeOptions.find((item) => item.value === value)?.label || value || '-';
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
      return this.backendUnavailable || canEditMegaFlowWorkOrder(this.currentUserInfo);
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
  padding: 16px;
  font-size: 14px;
  color: #303133;
}

.workbench-panel,
.table-card {
  border-radius: 8px;
}

.page-header-band {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  box-shadow: 0 1px 2px rgb(0 0 0 / 4%);
}

.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
}

.page-subtitle {
  margin: 4px 0 0;
  font-size: 12px;
  color: #909399;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.total-count {
  font-size: 13px;
  color: #909399;
}

.preview-banner {
  padding: 10px 14px;
  margin: 12px 0 0;
  font-size: 13px;
  color: #8a5a00;
  background: #fff7e6;
  border: 1px solid #ffd591;
  border-radius: 8px;
}

.stats-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(128px, 1fr));
  gap: 12px;
  margin: 12px 0;
}

.stat-tile {
  padding: 12px 16px;
  cursor: pointer;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  box-shadow: 0 1px 2px rgb(0 0 0 / 4%);
  transition: all 0.15s ease;
}

.stat-tile-active,
.stat-tile:hover {
  border-color: #409eff;
  box-shadow: 0 4px 12px rgb(64 158 255 / 12%);
}

.stat-label {
  display: block;
  font-size: 13px;
  color: #909399;
}

.stat-value {
  display: block;
  margin-top: 6px;
  font-size: 22px;
  font-weight: 700;
}

.filter-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 14px;
  margin-bottom: 12px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  box-shadow: 0 1px 2px rgb(0 0 0 / 4%);
}

.table-card {
  border: 1px solid #ebeef5;
  box-shadow: 0 1px 2px rgb(0 0 0 / 4%);
}

.filter-item {
  width: 180px;
}

.filter-keyword {
  width: 360px;
}

.filter-actions {
  display: flex;
  gap: 8px;
}

.link-text {
  color: #409eff;
  cursor: pointer;
}

.link-text:hover {
  text-decoration: underline;
}

.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}

/* 与效价工单列表操作按钮一致：small 语义 + 自定义 28px 高度 */
.table-card :deep(.table-action-btn) {
  height: 28px;
  min-height: 26px;
  padding: 0 12px;
  font-size: 13px;
}
</style>
