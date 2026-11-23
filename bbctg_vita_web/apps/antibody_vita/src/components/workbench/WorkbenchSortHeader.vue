<template>
  <button
    type="button"
    class="sort-header-btn"
    :class="{ 'is-active': active }"
    :title="title"
    @click.stop="$emit('toggle')"
  >
    {{ label }}
  </button>
</template>

<script>
/** 工作台视图排序列的表头：点击在「最新在前」和队列序之间切换，配合 workbenchQueueSortMixin 使用。 */
export default {
  name: 'WorkbenchSortHeader',
  props: {
    label: { type: String, default: '' },
    title: { type: String, default: '' },
    active: { type: Boolean, default: false },
  },
  emits: ['toggle'],
}
</script>

<style scoped>
.sort-header-btn {
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  cursor: pointer;
}
.sort-header-btn.is-active {
  color: var(--el-color-primary);
  font-weight: 650;
}
</style>
