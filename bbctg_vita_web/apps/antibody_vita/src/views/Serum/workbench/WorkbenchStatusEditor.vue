<template>
  <el-popover
    v-model:visible="visible"
    placement="right"
    trigger="click"
    transition="el-zoom-in-left"
    :width="116"
    :disabled="!editable"
    :teleported="true"
  >
    <div class="workbench-status-option-list">
      <button
        v-for="item in options"
        :key="item"
        type="button"
        class="workbench-status-option"
        :class="{ 'is-current': item === value }"
        @click.stop="choose(item)"
      >
        {{ item }}
      </button>
    </div>
    <template #reference>
      <el-tag
        class="list-status-tag workbench-status-tag"
        :class="{ 'is-editable': editable }"
        :type="type"
        effect="plain"
        @click.stop
      >
        {{ displayValue }}
      </el-tag>
    </template>
  </el-popover>
</template>

<script>
import { ElPopover, ElTag } from 'element-plus'

export default {
  name: 'WorkbenchStatusEditor',
  components: { ElPopover, ElTag },
  props: {
    value: { type: [String, Number], default: '' },
    options: { type: Array, default: () => [] },
    type: { type: String, default: 'info' },
    editable: { type: Boolean, default: false },
  },
  emits: ['change'],
  data() {
    return { visible: false }
  },
  computed: {
    displayValue() {
      return String(this.value ?? '').trim() || '—'
    },
  },
  watch: {
    editable(value) {
      if (!value) this.visible = false
    },
  },
  methods: {
    choose(value) {
      this.visible = false
      if (value !== this.value) this.$emit('change', value)
    },
  },
}
</script>

<style>
.workbench-status-tag.is-editable {
  cursor: pointer;
}
.workbench-status-option-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 2px;
}
.workbench-status-option {
  width: 100%;
  padding: 7px 10px;
  border: 0;
  border-radius: var(--list-inner-radius);
  background: transparent;
  color: var(--el-text-color-regular);
  font: inherit;
  line-height: 18px;
  text-align: left;
  cursor: pointer;
  transition: background-color .16s ease, color .16s ease;
}
.workbench-status-option:hover,
.workbench-status-option.is-current {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
}
.workbench-status-option.is-current {
  font-weight: 600;
}
</style>
