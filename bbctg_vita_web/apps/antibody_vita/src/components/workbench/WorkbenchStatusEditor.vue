<template>
  <el-popover
    v-if="activated"
    v-model:visible="visible"
    placement="right"
    trigger="click"
    transition="el-zoom-in-left"
    :width="132"
    :disabled="!editable"
    :teleported="true"
    @hide="scheduleDeactivate"
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
        :class="[tagClass, toneClass, { 'is-editable': editable }]"
        :type="tagType"
        effect="plain"
        disable-transitions
        @click.stop
      >
        {{ displayValue }}
      </el-tag>
    </template>
  </el-popover>
  <el-tag
    v-else
    class="list-status-tag workbench-status-tag"
    :class="[tagClass, toneClass, { 'is-editable': editable }]"
    :type="tagType"
    effect="plain"
    disable-transitions
    @click.stop="activateAndOpen"
  >
    {{ displayValue }}
  </el-tag>
</template>

<script>
import { ElPopover, ElTag } from 'element-plus'

const EL_TAG_TYPES = ['primary', 'success', 'info', 'warning', 'danger']

export default {
  name: 'WorkbenchStatusEditor',
  components: { ElPopover, ElTag },
  props: {
    value: { type: [String, Number], default: '' },
    options: { type: Array, default: () => [] },
    type: { type: String, default: 'info' },
    tagClass: { type: String, default: '' },
    editable: { type: Boolean, default: false },
  },
  emits: ['change'],
  data() {
    return { activated: false, visible: false, deactivateTimer: 0 }
  },
  computed: {
    displayValue() {
      return String(this.value ?? '').trim() || '—'
    },
    // el-tag 只认 5 种 type，其余色调（如 library）走 status-tone-* 样式。
    tagType() {
      return EL_TAG_TYPES.includes(this.type) ? this.type : 'info'
    },
    toneClass() {
      return EL_TAG_TYPES.includes(this.type) ? '' : `status-tone-${this.type}`
    },
  },
  watch: {
    editable(value) {
      if (!value) this.visible = false
    },
    visible(value) {
      if (!value) this.scheduleDeactivate()
    },
  },
  beforeUnmount() {
    if (this.deactivateTimer) clearTimeout(this.deactivateTimer)
  },
  methods: {
    activateAndOpen() {
      if (!this.editable) return
      if (this.deactivateTimer) {
        clearTimeout(this.deactivateTimer)
        this.deactivateTimer = 0
      }
      this.activated = true
      this.$nextTick(() => {
        this.visible = true
      })
    },
    scheduleDeactivate() {
      if (this.deactivateTimer) clearTimeout(this.deactivateTimer)
      // 等 popover 退场动画结束后再卸载，避免残留 Popper / 选项 DOM
      this.deactivateTimer = window.setTimeout(() => {
        this.deactivateTimer = 0
        if (!this.visible) this.activated = false
      }, 220)
    },
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
.el-tag.workbench-status-tag.status-tone-king {
  --el-tag-text-color: var(--vita-king-text);
  --el-tag-bg-color: var(--vita-king-bg);
  --el-tag-border-color: var(--vita-king-border);
  color: var(--vita-king-text);
  background-color: var(--vita-king-bg);
  border-color: var(--vita-king-border);
}
.el-tag.workbench-status-tag.status-tone-library {
  --el-tag-text-color: var(--vita-library-text);
  --el-tag-bg-color: var(--el-fill-color-blank);
  --el-tag-border-color: var(--vita-library-border);
  color: var(--vita-library-text);
  background-color: var(--el-fill-color-blank);
  border-color: var(--vita-library-border);
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
