<template>
  <div class="target-page" :class="{ 'archive-open': archiveExpanded }">
    <section class="control-deck">
      <article class="search-hero-card">
        <div class="hero-title-row">
          <div>
            <h1>靶点情报工作台</h1>
            <p>以靶点为入口，快速查看主数据及后续信息。</p>
          </div>
          <small>最近同步 {{ stats.synced_at || '等待首次同步' }}</small>
        </div>
        <form class="search-control" @submit.prevent="search">
          <el-icon><Search /></el-icon>
          <input v-model="query.keyword" placeholder="搜索靶点、基因、别名或 NCBI Gene ID" />
          <button
            v-if="query.keyword"
            class="clear-search"
            type="button"
            aria-label="清除搜索"
            @click="clearSearch"
          >
            <el-icon><Close /></el-icon>
          </button>
          <button class="search-submit" type="submit">搜索</button>
        </form>
      </article>

      <article class="status-filter-card">
        <div class="status-filter-heading">
          <div>
            <h2>开发状态</h2>
            <p>选择状态后立即更新左侧靶点列表</p>
          </div>
          <label class="inactive-filter">
            <input v-model="query.include_inactive" type="checkbox" @change="search" />
            <span>显示已下架</span>
          </label>
        </div>
        <div class="status-grid">
          <button
            v-for="item in statusFilters"
            :key="item.value"
            class="status-card"
            :class="{ active: query.status === item.value }"
            type="button"
            @click="filterByStatus(item.value)"
          >
            <span>{{ item.label }}</span>
            <strong>{{ item.count.toLocaleString() }}</strong>
          </button>
        </div>
      </article>
    </section>

    <div v-if="loadError" class="load-error">
      靶点数据加载失败，请稍后重试或确认接口权限。
    </div>

    <section
      ref="workspaceSection"
      class="content-grid"
      :style="lockedWorkspaceStyle"
    >
      <article class="list-card">
        <div class="list-header">
          <div>
            <h2>靶点浏览</h2>
            <p>当前条件下共 {{ total.toLocaleString() }} 个靶点</p>
          </div>
          <button class="reset-filter" type="button" @click="reset">重置筛选</button>
        </div>

        <div v-loading="loading" class="target-list">
          <button
            v-for="target in targets"
            :key="target.id"
            class="target-row"
            :class="{ selected: selectedTarget?.id === target.id }"
            type="button"
            @click="selectedTarget = target"
          >
            <span class="target-code">{{ target.snum }}</span>
            <span class="target-name">
              <strong>{{ target.name }}</strong>
              <small>{{ target.official_full_name || '暂无官方全名' }}</small>
            </span>
            <span class="target-gene">
              <span>Human {{ target.human_gene_official_name || '—' }}</span>
              <span>Mouse {{ target.mouse_gene_official_name || '—' }}</span>
            </span>
            <span class="target-status">
              <el-tag :type="statusMeta(target.status).type" effect="plain" size="small">
                {{ statusMeta(target.status).label }}
              </el-tag>
              <small v-if="selectedTarget?.id === target.id">正在查看</small>
            </span>
          </button>
          <el-empty v-if="!loading && targets.length === 0" description="没有符合条件的靶点" />
        </div>

        <div class="pagination-bar">
          <span>共 {{ total.toLocaleString() }} 条</span>
          <label>
            每页
            <select v-model.number="query.limit" @change="changePageSize">
              <option :value="10">10</option>
              <option :value="20">20</option>
              <option :value="50">50</option>
            </select>
            条
          </label>
          <div class="page-controls">
            <button type="button" :disabled="query.page <= 1" @click="goToPage(query.page - 1)">
              上一页
            </button>
            <strong>{{ query.page }} / {{ totalPages }}</strong>
            <button
              type="button"
              :disabled="query.page >= totalPages"
              @click="goToPage(query.page + 1)"
            >
              下一页
            </button>
          </div>
        </div>
      </article>

      <aside class="detail-column">
        <article class="spotlight-card">
          <template v-if="selectedTarget">
            <div class="spotlight-label">
              <div class="spotlight-title">
                <h2>靶点摘要</h2>
                <span>Target spotlight</span>
              </div>
              <el-tag :type="statusMeta(selectedTarget.status).type" effect="plain">
                {{ statusMeta(selectedTarget.status).label }}
              </el-tag>
            </div>

            <div class="spotlight-identity">
              <div class="target-name-line">
                <h2>{{ selectedTarget.name }}</h2>
                <span class="selected-code">{{ selectedTarget.snum }}</span>
              </div>
              <p>{{ selectedTarget.official_full_name || '暂无官方全名' }}</p>
            </div>

            <div class="fact-grid">
              <div>
                <span>人源基因</span>
                <strong>{{ selectedTarget.human_gene_official_name || '—' }}</strong>
              </div>
              <div>
                <span>鼠源基因</span>
                <strong>{{ selectedTarget.mouse_gene_official_name || '—' }}</strong>
              </div>
              <div>
                <span>NCBI Gene ID</span>
                <strong>
                  <a
                    v-if="ncbiGeneUrl(selectedTarget.human_ncbi_gene_id)"
                    class="ncbi-link"
                    :href="ncbiGeneUrl(selectedTarget.human_ncbi_gene_id)"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {{ selectedTarget.human_ncbi_gene_id }}
                  </a>
                  <span v-else>{{ selectedTarget.human_ncbi_gene_id || '—' }}</span>
                  /
                  <a
                    v-if="ncbiGeneUrl(selectedTarget.mouse_ncbi_gene_id)"
                    class="ncbi-link"
                    :href="ncbiGeneUrl(selectedTarget.mouse_ncbi_gene_id)"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {{ selectedTarget.mouse_ncbi_gene_id }}
                  </a>
                  <span v-else>{{ selectedTarget.mouse_ncbi_gene_id || '—' }}</span>
                </strong>
              </div>
              <div>
                <span>基因家族</span>
                <strong>{{ selectedTarget.gene_family || '未标注' }}</strong>
              </div>
              <div class="wide">
                <span>适应症</span>
                <strong>{{ selectedTarget.indication || '未标注' }}</strong>
              </div>
            </div>

            <div class="function-summary">
              <h3>功能摘要</h3>
              <p>{{ selectedTarget.gene_functional_desc || '暂无基因功能描述。' }}</p>
            </div>

            <div class="fact-tags">
              <span>KO致死 · {{ koLethalLabel(selectedTarget.ko_lethal_info) }}</span>
              <span>同源基因 · {{ booleanLabel(selectedTarget.is_homologous_gene) }}</span>
              <span>人鼠同源性 · {{ selectedTarget.human_mouse_homology || '未标注' }}</span>
            </div>
          </template>
          <el-empty v-else description="请从左侧选择靶点" />
        </article>

        <button
          v-if="selectedTarget"
          class="archive-toggle-card"
          :class="{ active: archiveExpanded }"
          type="button"
          :aria-expanded="archiveExpanded"
          @click="toggleArchive"
        >
          <div>
            <h3>完整靶点档案</h3>
            <p>{{ archiveExpanded ? '档案已在下方展开' : '点击后在当前页面下方展开全部信息' }}</p>
          </div>
          <span class="archive-toggle">
            <i></i>
          </span>
        </button>
      </aside>
    </section>

    <transition name="archive-expand">
      <section
        v-if="archiveExpanded && selectedTarget"
        ref="archiveSection"
        class="inline-archive"
      >
        <div class="archive-header">
          <div>
            <div class="target-name-line">
              <h2>{{ selectedTarget.name }}</h2>
              <span class="selected-code">{{ selectedTarget.snum }}</span>
            </div>
            <p>{{ selectedTarget.official_full_name || '暂无官方全名' }}</p>
          </div>
          <a
            class="target-source-link"
            :href="targetProjectUrl(selectedTarget.external_id)"
            target="_blank"
            rel="noopener noreferrer"
          >
            <span>项目管理详情</span>
            <el-icon><TopRight /></el-icon>
          </a>
        </div>

        <div class="archive-groups">
          <section v-for="group in detailGroups" :key="group.key" class="archive-group">
            <div class="group-title">
              <h3>{{ group.title }}</h3>
            </div>
            <div class="archive-fields">
              <div
                v-for="item in group.items"
                :key="item.label"
                class="archive-field"
                :class="{ wide: item.wide }"
              >
                <span>{{ item.label }}</span>
                <strong>
                  <a
                    v-if="item.href"
                    class="ncbi-link"
                    :href="item.href"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {{ item.value }}
                  </a>
                  <template v-else>{{ item.value }}</template>
                </strong>
              </div>
            </div>
          </section>
        </div>

        <footer class="archive-meta">
          <div class="archive-remark">
            <span>备注</span>
            <p>{{ selectedTarget.remark || '—' }}</p>
          </div>
          <div class="source-meta">
            <div>
              <span>数据状态</span>
              <strong>{{ selectedTarget.is_active ? '有效' : '已下架' }}</strong>
            </div>
            <div>
              <span>外部平台ID</span>
              <strong>{{ selectedTarget.external_id }}</strong>
            </div>
            <div>
              <span>最近同步</span>
              <strong>{{ selectedTarget.synced_at || '—' }}</strong>
            </div>
          </div>
        </footer>
      </section>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue';

import { Close, Search, TopRight } from '@element-plus/icons-vue';

import {
  fetchTargetList,
  type TargetItem,
  type TargetListQuery,
  type TargetStats,
} from '#/api/discovery';
import { useStaleTabRefresh } from '#/utils/staleTabRefresh';

interface DetailField {
  label: string;
  value: string;
  href?: string;
  wide?: boolean;
}

const TARGET_PM_BASE_URL = 'https://pm.biocytogen.com.cn';

const query = reactive<TargetListQuery>({
  page: 1,
  limit: 20,
  keyword: '',
  status: '',
  include_inactive: false,
});
const targets = ref<TargetItem[]>([]);
const selectedTarget = ref<TargetItem>();
const total = ref(0);
const loading = ref(false);
const loadError = ref(false);
const archiveExpanded = ref(false);
const archiveSection = ref<HTMLElement>();
const workspaceSection = ref<HTMLElement>();
const lockedWorkspaceHeight = ref<number>();
const stats = reactive<TargetStats>({
  total: 0,
  developed: 0,
  undeveloped: 0,
  unmarked: 0,
  synced_at: null,
});

const statusFilters = computed(() => [
  { label: '全部', value: '' as const, count: stats.total },
  { label: '已开发', value: '1' as const, count: stats.developed },
  { label: '未开发', value: '2' as const, count: stats.undeveloped },
  { label: '未标注', value: 'unknown' as const, count: stats.unmarked },
]);
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / query.limit)));
const lockedWorkspaceStyle = computed(() =>
  archiveExpanded.value && lockedWorkspaceHeight.value
    ? { flex: 'none', height: `${lockedWorkspaceHeight.value}px` }
    : undefined,
);

const detailGroups = computed(() => {
  const target = selectedTarget.value;
  if (!target) return [];
  return [
    group('basic', '基础信息', [
      field('靶点编号', target.snum),
      field('靶点名称', target.name),
      field('官方全名', target.official_full_name, true),
      field('开发状态', statusMeta(target.status).label),
      field('靶点类型', targetTypeLabel(target.type)),
    ]),
    group('human', '人源基因', [
      field('官方名称', target.human_gene_official_name),
      field(
        'NCBI Gene ID',
        target.human_ncbi_gene_id,
        false,
        ncbiGeneUrl(target.human_ncbi_gene_id),
      ),
      field('别名', target.human_gene_alias_name, true),
      field('染色体位置', chromosomePositionLabel(target.human_chromosome_position), true),
    ]),
    group('mouse', '鼠源基因', [
      field('官方名称', target.mouse_gene_official_name),
      field(
        'NCBI Gene ID',
        target.mouse_ncbi_gene_id,
        false,
        ncbiGeneUrl(target.mouse_ncbi_gene_id),
      ),
      field('别名', target.mouse_gene_alias_name, true),
      field('染色体位置', chromosomePositionLabel(target.mouse_chromosome_position), true),
    ]),
    group('homology', '跨物种同源性', [
      field('是否有同源基因', booleanLabel(target.is_homologous_gene)),
      field('人鼠同源性', target.human_mouse_homology),
      field('人猴同源性', target.human_monkey_homology),
      field('人犬同源性', target.human_dog_homology),
      field('人猫同源性', target.human_cat_homology),
      field('预期功能结构域人鼠同源性', target.human_mouse_homology_expect_functional_domain, true),
    ]),
    group('ko', 'KO与结构特征', [
      field('KO致死情况', koLethalLabel(target.ko_lethal_info)),
      field('KO致死备注', target.ko_lethal_info_desc, true),
      field('KO鼠表型 MGI', target.ko_mgi, true),
      field('KO鼠表型 IMPC', target.ko_impc),
      field('KO鼠表型 GT', target.ko_gt),
      field('结构特性', structureFeatureLabel(target.structure_feature)),
      field('形式备注', target.shape_remark),
      field('结构特性备注', target.structure_feature_remark, true),
    ]),
    group('function', '功能与免疫相关', [
      field('作用细胞', target.effect_cell, true),
      field('基因功能描述', target.gene_functional_desc, true),
      field('KO是否影响体液免疫', booleanLabel(target.is_ko_affect_humoral_immunity)),
      field('体液免疫影响备注', target.is_ko_affect_humoral_immunity_desc, true),
      field('配体或受体是否人鼠交叉', target.is_human_mouse_cross, true),
      field('适应症', target.indication),
      field('基因家族', target.gene_family),
      field('信号通路', target.signal_path, true),
    ]),
  ];
});

function field(label: string, value: unknown, wide = false, href?: string): DetailField {
  const displayValue = value === null || value === undefined || value === '' ? '—' : String(value);
  return { href, label, value: displayValue, wide };
}

function group(key: string, title: string, items: DetailField[]) {
  return { key, title, items };
}

async function loadTargets() {
  loading.value = true;
  loadError.value = false;
  try {
    const result = await fetchTargetList({ ...query });
    targets.value = result.items || [];
    total.value = result.total || 0;
    Object.assign(stats, result.stats || {});
    selectedTarget.value =
      targets.value.find((item) => item.id === selectedTarget.value?.id) || targets.value[0];
  } catch {
    targets.value = [];
    selectedTarget.value = undefined;
    total.value = 0;
    loadError.value = true;
  } finally {
    loading.value = false;
    markTabDataFetched();
  }
}

const { markTabDataFetched } = useStaleTabRefresh(loadTargets);

function search() {
  query.page = 1;
  loadTargets();
}

function clearSearch() {
  query.keyword = '';
  search();
}

function reset() {
  Object.assign(query, {
    page: 1,
    limit: 20,
    keyword: '',
    status: '',
    include_inactive: false,
  });
  loadTargets();
}

function filterByStatus(status: TargetListQuery['status']) {
  query.status = status;
  search();
}

function changePageSize() {
  query.page = 1;
  loadTargets();
}

function goToPage(page: number) {
  query.page = Math.min(Math.max(page, 1), totalPages.value);
  loadTargets();
}

async function toggleArchive() {
  if (archiveExpanded.value) {
    archiveExpanded.value = false;
    lockedWorkspaceHeight.value = undefined;
    return;
  }
  lockedWorkspaceHeight.value = workspaceSection.value?.getBoundingClientRect().height;
  archiveExpanded.value = true;
  await nextTick();
  archiveSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function statusMeta(status?: null | number) {
  if (status === 1) return { label: '已开发', type: 'success' as const };
  if (status === 2) return { label: '未开发', type: 'warning' as const };
  return { label: '未标注', type: 'info' as const };
}

function targetTypeLabel(value?: null | number) {
  const labels: Record<number, string> = {
    1: '内部-千鼠万抗',
    2: '内部-其他',
    3: '外部',
    4: 'NA',
  };
  return value == null ? '未标注' : labels[value] || '未知类型';
}

function koLethalLabel(value?: null | number) {
  const labels: Record<number, string> = {
    1: '致死',
    2: '存活',
    3: '致死数据冲突',
    4: 'NA',
  };
  return value == null ? '未标注' : labels[value] || '未知';
}

function booleanLabel(value?: boolean | null) {
  if (value === true) return '是';
  if (value === false) return '否';
  return '未标注';
}

function chromosomePositionLabel(value?: null | string) {
  const position = String(value || '').trim();
  if (!position) return '—';
  if (/^\d+$/.test(position)) return `${position}号染色体`;
  if (/^[XY]$/i.test(position)) return `${position.toUpperCase()}染色体`;
  return position;
}

function structureFeatureLabel(value?: null | string) {
  const feature = String(value || '').trim();
  if (!feature) return '—';
  return /^\d+$/.test(feature) ? `${feature}次跨膜` : feature;
}

function ncbiGeneUrl(value?: null | string) {
  const geneId = String(value || '').trim();
  return /^\d+$/.test(geneId) ? `https://www.ncbi.nlm.nih.gov/gene/${geneId}` : undefined;
}

function targetProjectUrl(externalId: number) {
  return `${TARGET_PM_BASE_URL}/#/target/detail/info/${externalId}`;
}

onMounted(loadTargets);
</script>

<style scoped>
.target-page {
  --target-text: #27303f;
  --target-muted: #7b8492;
  --target-border: #e4e9f0;
  --target-soft: #f6f8fb;

  box-sizing: border-box;
  display: flex;
  height: var(--vben-content-height, calc(100dvh - 88px));
  min-height: 100%;
  padding: var(--list-page-padding);
  overflow: hidden;
  flex-direction: column;
  color: var(--target-text);
  font-size: 13px;
  background: var(--list-page-bg);
}

.target-page.archive-open {
  height: auto;
  min-height: var(--vben-content-height, calc(100dvh - 88px));
  overflow: visible;
}

.selected-code {
  color: var(--el-color-primary);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.05em;
}

.search-hero-card h1 {
  margin: 0 0 3px;
  font-size: 19px;
  font-weight: 600;
  letter-spacing: -0.02em;
}

.hero-title-row p,
.status-filter-heading p,
.list-header p,
.archive-toggle-card p {
  margin: 0;
  color: var(--target-muted);
  font-size: 12px;
}

.control-deck {
  display: grid;
  grid-template-columns: minmax(340px, 0.92fr) minmax(480px, 1.08fr);
  flex-shrink: 0;
  gap: var(--list-page-gap);
  margin-bottom: var(--list-page-gap);
}

.search-hero-card,
.status-filter-card {
  padding: 13px 15px;
  background: #fff;
  border: 1px solid var(--target-border);
  border-radius: var(--list-surface-radius);
  box-shadow: var(--list-surface-shadow);
}

.search-hero-card {
  background:
    radial-gradient(circle at 96% 4%, rgb(64 158 255 / 9%), transparent 42%),
    #fff;
}

.hero-title-row,
.status-filter-heading {
  display: flex;
  gap: 14px;
  align-items: center;
  justify-content: space-between;
}

.hero-title-row small {
  flex-shrink: 0;
  color: var(--target-muted);
  font-size: 11px;
}

.search-hero-card .search-control {
  margin-top: 10px;
}

.status-filter-heading {
  margin-bottom: 10px;
}

.status-filter-heading h2 {
  margin: 0 0 2px;
  font-size: 14px;
  font-weight: 600;
}

.list-card,
.spotlight-card,
.archive-toggle-card,
.inline-archive {
  background: #fff;
  border: 1px solid var(--target-border);
  border-radius: var(--list-surface-radius);
  box-shadow: var(--list-surface-shadow);
}

.list-header,
.group-title,
.archive-header {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  justify-content: space-between;
}

.list-header h2,
.archive-toggle-card h3,
.function-summary h3 {
  margin: 0 0 3px;
  font-size: 14px;
  font-weight: 600;
}

.search-control {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto auto;
  height: 36px;
  align-items: center;
  overflow: hidden;
  background: #fff;
  border: 1px solid #d9e0e8;
  border-radius: var(--list-mid-radius);
  box-shadow: var(--list-surface-shadow);
}

.search-control:focus-within {
  background: #fff;
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 2px var(--el-color-primary-light-9);
}

.search-control > .el-icon {
  margin-left: 11px;
  color: var(--target-muted);
}

.search-control input {
  width: 100%;
  height: 100%;
  padding: 0 9px;
  color: var(--target-text);
  font: inherit;
  font-size: 13px;
  background: transparent;
  border: 0;
  outline: none;
}

.search-control input::placeholder {
  color: #a2a9b3;
}

.clear-search,
.search-submit,
.reset-filter {
  font: inherit;
  cursor: pointer;
  border: 0;
}

.clear-search {
  display: grid;
  padding: 8px;
  color: var(--target-muted);
  background: transparent;
  place-items: center;
}

.search-submit {
  align-self: stretch;
  min-width: 58px;
  font-size: 12px;
  color: #fff;
  background: var(--el-color-primary);
}

.search-submit:hover {
  background: var(--el-color-primary-dark-2);
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.status-card {
  display: grid;
  min-width: 0;
  gap: 2px;
  padding: 8px 10px;
  color: #596273;
  font: inherit;
  text-align: left;
  cursor: pointer;
  background: var(--target-soft);
  border: 1px solid var(--target-border);
  border-radius: var(--list-mid-radius);
}

.status-card span {
  color: var(--target-muted);
  font-size: 11px;
}

.status-card strong {
  overflow: hidden;
  font-size: 15px;
  font-weight: 600;
  text-overflow: ellipsis;
}

.status-card:hover,
.status-card.active {
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary-light-5);
}

.status-card.active span {
  color: var(--el-color-primary);
}

.inactive-filter {
  display: flex;
  gap: 5px;
  align-items: center;
  color: var(--target-muted);
  font-size: 12px;
  white-space: nowrap;
  cursor: pointer;
}

.inactive-filter input {
  width: 14px;
  height: 14px;
  margin: 0;
  accent-color: var(--el-color-primary);
}

.load-error {
  padding: 9px 13px;
  margin-bottom: var(--list-page-gap);
  color: #8a5a00;
  background: #fff7e6;
  border: 1px solid #ffd591;
  border-radius: var(--list-mid-radius);
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.72fr) minmax(300px, 0.88fr);
  min-height: 0;
  flex: 1;
  gap: var(--list-page-gap);
}

.list-card {
  height: 100%;
  display: flex;
  min-width: 0;
  overflow: hidden;
  flex-direction: column;
}

.list-header {
  flex-shrink: 0;
  align-items: center;
  padding: 13px 16px;
  border-bottom: 1px solid var(--target-border);
}

.reset-filter {
  padding: 6px 8px;
  color: var(--el-color-primary);
  background: transparent;
}

.target-list {
  min-height: 0;
  flex: 1;
  overflow-y: auto;
}

.target-row {
  display: grid;
  grid-template-columns: 82px minmax(160px, 1.1fr) minmax(190px, 1fr) 92px;
  width: 100%;
  gap: 14px;
  align-items: center;
  padding: 11px 16px;
  color: var(--target-text);
  text-align: left;
  cursor: pointer;
  background: #fff;
  border: 0;
  border-bottom: 1px solid #eff2f5;
}

.target-row:hover {
  background: #f9fbfd;
}

.target-row.selected {
  background: #eef5ff;
  box-shadow: inset 3px 0 0 var(--el-color-primary);
}

.target-code {
  color: var(--target-muted);
  font-size: 12px;
}

.target-name,
.target-gene,
.target-status {
  display: grid;
  min-width: 0;
  gap: 2px;
}

.target-name strong {
  overflow: hidden;
  font-size: 14px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.target-name small,
.target-gene span {
  overflow: hidden;
  color: var(--target-muted);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.target-status {
  justify-items: end;
}

.target-status small {
  color: var(--el-color-primary);
  font-size: 11px;
}

.pagination-bar {
  display: flex;
  flex-shrink: 0;
  gap: 18px;
  align-items: center;
  justify-content: flex-end;
  min-height: 44px;
  padding: 8px 14px;
  color: var(--target-muted);
  font-size: 12px;
  background: #fff;
  border-top: 1px solid var(--target-border);
}

.pagination-bar label,
.page-controls {
  display: flex;
  gap: 6px;
  align-items: center;
}

.pagination-bar select,
.page-controls button {
  height: 28px;
  padding: 0 9px;
  color: #596273;
  font: inherit;
  background: #fff;
  border: 1px solid var(--target-border);
  border-radius: 6px;
}

.page-controls button {
  cursor: pointer;
}

.page-controls button:hover:not(:disabled) {
  color: var(--el-color-primary);
  border-color: var(--el-color-primary-light-5);
}

.page-controls button:disabled {
  color: #b8bec7;
  cursor: not-allowed;
  background: #f6f7f9;
}

.page-controls strong {
  min-width: 58px;
  color: var(--target-text);
  font-size: 12px;
  font-weight: 600;
  text-align: center;
}

.detail-column {
  height: 100%;
  display: grid;
  min-width: 0;
  grid-template-rows: minmax(0, 1fr) auto;
  gap: var(--list-page-gap);
}

.spotlight-card,
.archive-toggle-card {
  padding: 16px;
}

.spotlight-card {
  overflow-y: auto;
}

.spotlight-label {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.spotlight-title {
  display: flex;
  gap: 8px;
  align-items: baseline;
}

.spotlight-title h2 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}

.spotlight-title span {
  color: var(--target-muted);
  font-size: 11px;
  font-weight: 500;
}

.spotlight-identity h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.target-name-line {
  display: flex;
  align-items: baseline;
  justify-content: flex-start;
}

.spotlight-identity .target-name-line {
  gap: 12px;
}

.archive-header .target-name-line {
  gap: 10px;
}

.spotlight-identity p,
.archive-header p {
  margin: 0;
  color: var(--target-muted);
  font-size: 12px;
}

.spotlight-identity p {
  margin-top: 3px;
  font-size: 12px;
}

.spotlight-identity {
  margin-bottom: 15px;
}

.fact-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1px;
  overflow: hidden;
  background: var(--target-border);
  border: 1px solid var(--target-border);
  border-radius: var(--list-mid-radius);
}

.fact-grid > div {
  display: grid;
  min-height: 62px;
  gap: 4px;
  align-content: center;
  padding: 10px;
  background: var(--target-soft);
}

.fact-grid .wide {
  grid-column: 1 / -1;
}

.fact-grid span,
.archive-field span {
  color: var(--target-muted);
  font-size: 11px;
}

.fact-grid strong {
  font-size: 13px;
  font-weight: 600;
  overflow-wrap: anywhere;
}

.ncbi-link {
  color: inherit;
  text-decoration: none;
  text-underline-offset: 2px;
}

.ncbi-link:hover {
  text-decoration: underline;
}

.function-summary {
  margin-top: 15px;
}

.function-summary p {
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  color: #596273;
  font-size: 12px;
  line-height: 1.7;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
}

.fact-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 13px;
}

.fact-tags span {
  padding: 5px 7px;
  color: #596273;
  font-size: 11px;
  background: #f1f4f7;
  border-radius: 6px;
}

.archive-toggle-card {
  display: flex;
  width: 100%;
  gap: 14px;
  align-items: center;
  justify-content: space-between;
  color: var(--target-text);
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.archive-toggle-card p {
  max-width: 230px;
  line-height: 1.5;
}

.archive-toggle-card:hover,
.archive-toggle-card.active {
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary-light-5);
}

.archive-toggle {
  position: relative;
  width: 38px;
  height: 22px;
  flex-shrink: 0;
  background: #c5cbd3;
  border-radius: 999px;
  transition: background-color 0.2s ease;
}

.archive-toggle i {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 16px;
  height: 16px;
  background: #fff;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgb(31 41 55 / 22%);
  transition: transform 0.2s ease;
}

.archive-toggle-card.active .archive-toggle {
  background: var(--el-color-primary);
}

.archive-toggle-card.active .archive-toggle i {
  transform: translateX(16px);
}

.inline-archive {
  padding: 0 18px 18px;
  margin-top: var(--list-page-gap);
}

.archive-header {
  align-items: center;
  padding: 16px 0;
  border-bottom: 1px solid var(--target-border);
}

.target-source-link {
  display: inline-flex;
  flex: none;
  gap: 5px;
  align-items: center;
  padding: 7px 10px;
  border: 1px solid var(--target-border);
  border-radius: 8px;
  color: var(--target-muted);
  font-size: 12px;
  line-height: 1;
  text-decoration: none;
  transition:
    color 0.2s ease,
    border-color 0.2s ease,
    background-color 0.2s ease;
}

.target-source-link:hover {
  border-color: color-mix(in srgb, var(--target-accent) 35%, var(--target-border));
  background: var(--target-soft);
  color: var(--target-accent);
}

.archive-header h2 {
  margin: 0 0 4px;
  font-size: 22px;
  font-weight: 600;
}

.archive-groups {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  padding-top: 14px;
}

.archive-group {
  padding: 14px;
  background: #fafbfc;
  border: 1px solid var(--target-border);
  border-radius: var(--list-mid-radius);
}

.group-title {
  padding-bottom: 9px;
  margin-bottom: 11px;
  border-bottom: 1px solid var(--target-border);
}

.group-title h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}

.archive-fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 18px;
}

.archive-field {
  display: grid;
  min-width: 0;
  gap: 3px;
}

.archive-field.wide {
  grid-column: 1 / -1;
}

.archive-field strong {
  font-size: 13px;
  font-weight: 400;
  line-height: 1.6;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}

.archive-meta {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(420px, 1fr);
  gap: 18px;
  padding: 15px;
  margin-top: 12px;
  background: var(--target-soft);
  border: 1px solid var(--target-border);
  border-radius: var(--list-mid-radius);
}

.archive-remark > span,
.source-meta span {
  color: var(--target-muted);
  font-size: 11px;
}

.archive-remark p {
  margin: 6px 0 0;
  color: #596273;
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
}

.source-meta {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.source-meta > div {
  display: grid;
  gap: 5px;
  align-content: start;
}

.source-meta strong {
  font-size: 13px;
  font-weight: 600;
  overflow-wrap: anywhere;
}

.archive-expand-enter-active,
.archive-expand-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}

.archive-expand-enter-from,
.archive-expand-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

@media (max-width: 1120px) {
  .control-deck {
    grid-template-columns: minmax(310px, 0.9fr) minmax(420px, 1.1fr);
  }

  .content-grid {
    grid-template-columns: minmax(0, 1.6fr) minmax(280px, 0.9fr);
  }

  .target-row {
    grid-template-columns: 72px minmax(145px, 1fr) minmax(155px, 0.85fr) 82px;
  }

  .archive-meta {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 860px) {
  .control-deck,
  .content-grid {
    grid-template-columns: 1fr;
  }

  .archive-groups {
    grid-template-columns: 1fr;
  }
}
</style>
