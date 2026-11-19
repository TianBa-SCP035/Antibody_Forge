<template>
  <div class="mega-order-sync-page" :class="{ 'is-list-table-locked': listTableLocked }">
    <div class="page-header-band">
      <div class="title-group">
        <h1 class="page-title">回传记录</h1>
        <p class="page-subtitle">镁伽推送的检测结果：核对结论、回给镁伽的回复，以及导入效价的进度。</p>
      </div>
      <div class="header-actions">
        <span class="total-count">共 {{ total }} 条回传</span>
        <el-button :icon="Back" @click="backToOrders">流式工单总览</el-button>
      </div>
    </div>

    <section class="workbench-panel">
      <div class="stats-strip">
        <div
          v-for="item in statusOptions"
          :key="item.value"
          class="stat-tile stat-tile-interactive"
          :class="[`stat-tone-${item.value}`, { 'stat-tile-active': listQuery.status === item.value }]"
          @click="toggleStatus(item.value)"
        >
          <span class="stat-label">{{ item.label }}</span>
          <strong class="stat-value">{{ stats[item.value] || 0 }}</strong>
        </div>
      </div>
    </section>

    <div class="filter-strip list-filter-controls">
      <el-input
        v-model="listQuery.keyword"
        class="filter-item"
        clearable
        placeholder="trace_id / 订单号"
        :prefix-icon="Search"
        @keyup.enter="handleFilter"
      />
      <el-select
        v-model="listQuery.status"
        class="filter-item"
        clearable
        placeholder="核对结论"
        @change="handleFilter"
      >
        <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <el-select
        v-model="listQuery.import_status"
        class="filter-item"
        clearable
        placeholder="导入进度"
        @change="handleFilter"
      >
        <el-option v-for="item in importOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <div class="filter-actions list-filter-actions">
        <el-button class="list-filter-action-button" type="primary" :icon="Search" @click="handleFilter">查询</el-button>
        <el-button class="list-filter-action-button" :icon="Refresh" @click="resetFilter">重置</el-button>
      </div>
    </div>

    <el-card shadow="never" class="list-table-card">
      <div ref="listTableBody" class="list-table-body">
        <el-table
          :height="listTableHeight"
          v-loading="listLoading"
          :data="list"
          row-key="id"
          border
          stripe
          highlight-current-row
          size="large"
          class="list-data-table"
          style="width: 100%"
          empty-text="暂无回传记录"
        >
          <el-table-column label="接收时间" min-width="160" align="center">
            <template #default="{ row }">{{ row.received_at || '—' }}</template>
          </el-table-column>
          <el-table-column label="trace_id" min-width="180" show-overflow-tooltip>
            <template #default="{ row }"><span class="list-code-text">{{ row.trace_id }}</span></template>
          </el-table-column>
          <el-table-column label="订单号" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">{{ formatArray(row.order_nos) }}</template>
          </el-table-column>
          <el-table-column label="核对结论" min-width="110" align="center">
            <template #default="{ row }">
              <el-tag class="list-status-tag" :type="syncStatusTag(row.status)" effect="plain">{{ row.status_label }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="回复码" min-width="80" align="center">
            <template #default="{ row }">{{ row.http_status || '—' }}</template>
          </el-table-column>
          <el-table-column label="导入进度" min-width="100" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.import_status" class="list-status-tag" :type="syncImportTag(row.import_status)" effect="plain">
                {{ syncImportLabel(row.import_status) }}
              </el-tag>
              <span v-else>—</span>
            </template>
          </el-table-column>
          <el-table-column label="说明" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">{{ row.error_message || '—' }}</template>
          </el-table-column>
          <el-table-column label="最近处理" min-width="160" align="center">
            <template #default="{ row }">{{ row.processed_at || '—' }}</template>
          </el-table-column>
          <el-table-column label="操作" fixed="right" width="100" align="center">
            <template #default="{ row }">
              <el-button class="list-table-action-btn" type="primary" plain :icon="View" @click="openDetail(row)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <el-pagination
        v-show="total > 0"
        v-model:current-page="listQuery.page"
        v-model:page-size="listQuery.limit"
        :total="total"
        :page-sizes="[20, 50, 100, 200]"
        layout="total, sizes, prev, pager, next, jumper"
        class="list-pagination"
        @size-change="handleFilter"
        @current-change="getList"
      />
    </el-card>

    <el-drawer v-model="detailVisible" size="70%" :title="detailTitle" destroy-on-close>
      <div v-loading="detailLoading" class="sync-detail">
        <template v-if="detail">
          <div class="detail-actions">
            <el-button :icon="Refresh" @click="loadDetail(detail.id)">刷新</el-button>
            <el-button :icon="Download" @click="downloadRaw">下载原文</el-button>
            <el-button
              type="warning"
              :icon="RefreshRight"
              :loading="reprocessing"
              :class="{ 'no-permission-btn': !canEdit() }"
              :title="!canEdit() ? '您没有权限重新处理回传' : ''"
              @click="handleReprocess"
            >
              重新处理
            </el-button>
          </div>

          <el-descriptions :column="3" border size="small">
            <el-descriptions-item label="trace_id">{{ detail.trace_id }}</el-descriptions-item>
            <el-descriptions-item label="接收时间">{{ detail.received_at || '—' }}</el-descriptions-item>
            <el-descriptions-item label="最近处理">{{ detail.processed_at || '—' }}</el-descriptions-item>
            <el-descriptions-item label="核对结论">
              <el-tag :type="syncStatusTag(detail.status)" effect="plain">{{ detail.status_label }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="回复码">{{ detail.http_status || '—' }}</el-descriptions-item>
            <el-descriptions-item label="导入进度">{{ syncImportLabel(detail.import_status) }}</el-descriptions-item>
            <el-descriptions-item label="订单号" :span="3">{{ formatArray(detail.order_nos) }}</el-descriptions-item>
            <el-descriptions-item v-if="detail.error_message" label="说明" :span="3">{{ detail.error_message }}</el-descriptions-item>
          </el-descriptions>

          <h3 class="detail-section-title">检测板</h3>
          <OrderSyncBoardTable :boards="detail.boards" />

          <h3 class="detail-section-title">回给镁伽的回复</h3>
          <pre class="json-panel">{{ responseText }}</pre>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<script>
import { Back, Download, Refresh, RefreshRight, Search, View } from '@element-plus/icons-vue';
import {
  ElButton,
  ElCard,
  ElDescriptions,
  ElDescriptionsItem,
  ElDrawer,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElPagination,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus';
import { useUserStore } from '@vben/stores';

import {
  downloadOrderSyncRaw,
  fetchOrderSyncDetail,
  fetchOrderSyncList,
  FLOW_WORK_ORDER_EDIT,
  reprocessOrderSync,
} from '#/api/megaAutomation';
import { notifyApiError } from '#/api/errors';
import { hasAccessCode } from '#/utils/accessCode';
import { downloadBlob } from '#/utils/file-resource';
import { listPageMixin } from '#/utils/listPage';
import { listTableLockMixin } from '#/utils/listTableLock';

import OrderSyncBoardTable from './components/OrderSyncBoardTable.vue';
import {
  SYNC_IMPORT_OPTIONS,
  SYNC_STATUS_OPTIONS,
  syncImportLabel,
  syncImportTag,
  syncStatusTag,
} from './orderSyncStatus';

function emptyQuery() {
  return {
    page: 1,
    limit: 20,
    keyword: '',
    status: '',
    import_status: '',
  };
}

export default {
  name: 'MegaOrderSyncRecords',
  mixins: [listTableLockMixin, listPageMixin],
  components: {
    ElButton,
    ElCard,
    ElDescriptions,
    ElDescriptionsItem,
    ElDrawer,
    ElInput,
    ElOption,
    ElPagination,
    ElSelect,
    ElTable,
    ElTableColumn,
    ElTag,
    OrderSyncBoardTable,
  },
  setup() {
    const userStore = useUserStore();
    return { userStore, Back, Download, Refresh, RefreshRight, Search, View };
  },
  data() {
    return {
      list: [],
      total: 0,
      stats: {},
      listLoading: false,
      listQuery: emptyQuery(),
      statusOptions: SYNC_STATUS_OPTIONS,
      importOptions: SYNC_IMPORT_OPTIONS,
      detailVisible: false,
      detailLoading: false,
      detail: null,
      reprocessing: false,
    };
  },
  computed: {
    detailTitle() {
      return this.detail ? `回传详情 · ${this.detail.trace_id}` : '回传详情';
    },
    responseText() {
      const body = this.detail?.response_body;
      return body ? JSON.stringify(body, null, 2) : '没有保存回复（旧数据或仍在处理）';
    },
  },
  created() {
    this.getList();
  },
  activated() {
    if (this.isListDataStale()) this.getList();
  },
  methods: {
    syncImportLabel,
    syncImportTag,
    syncStatusTag,
    async getList() {
      const isLatest = this.beginListRequest();
      this.listLoading = true;
      try {
        const data = await fetchOrderSyncList(this.listQuery);
        if (!isLatest()) return;
        this.list = data?.items || [];
        this.total = data?.total || 0;
        this.stats = data?.stats || {};
        this.markListFetched();
      } catch (error) {
        if (!isLatest()) return;
        this.list = [];
        this.total = 0;
        this.stats = {};
        notifyApiError(error, { fallback: '回传记录加载失败' });
      } finally {
        if (isLatest()) this.listLoading = false;
      }
    },
    resetFilter() {
      this.listQuery = emptyQuery();
      this.getList();
    },
    toggleStatus(status) {
      this.listQuery.status = this.listQuery.status === status ? '' : status;
      this.handleFilter();
    },
    formatArray(value) {
      return Array.isArray(value) && value.length ? value.join(', ') : '—';
    },
    canEdit() {
      return hasAccessCode(this.userStore.userInfo || {}, FLOW_WORK_ORDER_EDIT);
    },
    backToOrders() {
      this.$router.push({ name: 'MegaFlowWorkOrderList' });
    },
    openDetail(row) {
      this.detail = null;
      this.detailVisible = true;
      this.loadDetail(row.id);
    },
    async loadDetail(id) {
      this.detailLoading = true;
      try {
        this.detail = await fetchOrderSyncDetail(id);
      } catch (error) {
        notifyApiError(error, { fallback: '回传详情加载失败' });
      } finally {
        this.detailLoading = false;
      }
    },
    async downloadRaw() {
      try {
        const blob = await downloadOrderSyncRaw(this.detail.id);
        downloadBlob(blob, `${this.detail.trace_id}.json`);
      } catch (error) {
        notifyApiError(error, { fallback: '原文下载失败' });
      }
    },
    async handleReprocess() {
      if (!this.canEdit()) {
        ElMessage.warning('您没有权限重新处理回传');
        return;
      }
      try {
        await ElMessageBox.confirm(
          '按存档原文和当前工单数据重新核对，并重新导入效价（人工改过的板卡不覆盖）。当初回给镁伽的回复不变。',
          '重新处理',
          { type: 'warning', confirmButtonText: '重新处理', cancelButtonText: '取消' },
        );
      } catch {
        return;
      }
      this.reprocessing = true;
      try {
        this.detail = await reprocessOrderSync(this.detail.id);
        ElMessage.success('已重新核对，效价导入在后台进行，稍后刷新查看');
        this.getList();
      } catch (error) {
        notifyApiError(error, { fallback: '重新处理失败' });
      } finally {
        this.reprocessing = false;
      }
    },
  },
};
</script>

<style scoped src="#/components/workbench/workbenchPanel.css"></style>
<style scoped>
.mega-order-sync-page {
  position: relative;
  min-height: 100%;
  padding: var(--list-page-padding);
  font-size: 14px;
  color: var(--el-text-color-primary);
  background: var(--list-page-bg);
}

.stats-strip {
  grid-template-columns: repeat(auto-fit, minmax(136px, 1fr));
}

.stat-tone-passed {
  --stat-accent: #45c97a;
}

.stat-tone-partial {
  --stat-accent: #ecc94b;
}

.stat-tone-rejected {
  --stat-accent: #ef7878;
}

.stat-tone-invalid {
  --stat-accent: #ec6aad;
}

.stat-tone-error {
  --stat-accent: #8b97a8;
}

.filter-strip {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) repeat(2, minmax(0, 1fr)) auto;
  gap: 10px var(--list-filter-action-gap);
}

.filter-item {
  width: 100%;
  min-width: 0;
}

.sync-detail {
  min-height: 200px;
}

.detail-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.detail-section-title {
  margin: 18px 0 10px;
  font-size: 14px;
  font-weight: 600;
}

.json-panel {
  max-height: 360px;
  padding: 12px;
  margin: 0;
  overflow: auto;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
}
</style>
