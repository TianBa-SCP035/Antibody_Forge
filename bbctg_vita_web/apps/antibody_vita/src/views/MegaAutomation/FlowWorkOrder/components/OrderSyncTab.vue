<template>
  <section v-loading="loading" class="panel">
    <div class="panel-head">
      <div class="panel-head-left">
        <span class="panel-title">镁伽回传检测板</span>
        <span class="panel-hint">每次回传各占一行，最新在前；看整次回传请到「回传记录」</span>
      </div>
      <div class="panel-head-right">
        <el-button size="small" :icon="Refresh" :disabled="!workOrderId" @click="load">刷新</el-button>
        <el-button size="small" :icon="Tickets" @click="openRecords">回传记录</el-button>
      </div>
    </div>
    <OrderSyncBoardTable :boards="boards" show-sync />
  </section>
</template>

<script>
import { Refresh, Tickets } from '@element-plus/icons-vue';
import { ElButton } from 'element-plus';

import { fetchWorkOrderSyncBoards } from '#/api/megaAutomation';
import { notifyApiError } from '#/api/errors';
import { createLatestRequest } from '#/utils/latestRequest';

import OrderSyncBoardTable from './OrderSyncBoardTable.vue';

export default {
  name: 'OrderSyncTab',
  components: { ElButton, OrderSyncBoardTable },
  props: {
    workOrderId: { type: Number, default: null },
  },
  setup() {
    return { Refresh, Tickets };
  },
  data() {
    return {
      boards: [],
      loading: false,
    };
  },
  watch: {
    workOrderId() {
      this.load();
    },
  },
  created() {
    this.request = createLatestRequest();
    this.load();
  },
  beforeUnmount() {
    this.request.cancel();
  },
  methods: {
    async load() {
      const isLatest = this.request.begin();
      if (!this.workOrderId) {
        this.boards = [];
        this.loading = false;
        return;
      }
      this.loading = true;
      try {
        const data = await fetchWorkOrderSyncBoards(this.workOrderId);
        if (!isLatest()) return;
        this.boards = data?.items || [];
      } catch (error) {
        if (!isLatest()) return;
        this.boards = [];
        notifyApiError(error, { fallback: '回传结果加载失败', level: 'warning' });
      } finally {
        if (isLatest()) this.loading = false;
      }
    },
    openRecords() {
      this.$router.push({ name: 'MegaOrderSyncRecords' });
    },
  },
};
</script>
