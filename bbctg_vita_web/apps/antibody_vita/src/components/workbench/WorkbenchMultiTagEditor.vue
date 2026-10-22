<template>
  <el-popover
    v-if="activated"
    v-model:visible="visible"
    placement="right"
    trigger="click"
    transition="el-zoom-in-left"
    :width="'auto'"
    :disabled="!editable"
    :teleported="true"
    popper-class="workbench-multi-tag-popper"
    @hide="scheduleDeactivate"
  >
    <div class="workbench-multi-tag-options">
      <button
        v-for="item in options"
        :key="item"
        type="button"
        class="workbench-multi-tag-option"
        :class="{ 'is-current': selected.includes(item) }"
        @click.stop="toggle(item)"
      >
        <el-tag
          class="list-status-tag"
          :class="{ 'is-purple': toneOf(item) === 'purple' }"
          :type="toneOf(item) === 'purple' ? 'info' : toneOf(item)"
          :effect="selected.includes(item) ? 'light' : 'plain'"
        >
          {{ item }}
        </el-tag>
      </button>
    </div>
    <template #reference>
      <div
        class="workbench-multi-tags"
        :class="{
          'is-editable': editable,
          'is-start': align === 'start',
        }"
        @click.stop
      >
        <el-tag
          v-for="item in selected"
          :key="item"
          class="list-status-tag workbench-status-tag"
          :class="{ 'is-editable': editable, 'is-purple': toneOf(item) === 'purple' }"
          :type="toneOf(item) === 'purple' ? 'info' : toneOf(item)"
          effect="plain"
        >
          {{ item }}
        </el-tag>
        <el-tag
          v-if="!selected.length"
          class="list-status-tag workbench-status-tag is-empty"
          :class="{ 'is-editable': editable }"
          type="info"
          effect="plain"
        >
          —
        </el-tag>
      </div>
    </template>
  </el-popover>
  <div
    v-else
    class="workbench-multi-tags"
    :class="{
      'is-editable': editable,
      'is-start': align === 'start',
    }"
    @click.stop="activateAndOpen"
  >
    <el-tag
      v-for="item in selected"
      :key="item"
      class="list-status-tag workbench-status-tag"
      :class="{ 'is-editable': editable, 'is-purple': toneOf(item) === 'purple' }"
      :type="toneOf(item) === 'purple' ? 'info' : toneOf(item)"
      effect="plain"
    >
      {{ item }}
    </el-tag>
    <el-tag
      v-if="!selected.length"
      class="list-status-tag workbench-status-tag is-empty"
      :class="{ 'is-editable': editable }"
      type="info"
      effect="plain"
    >
      —
    </el-tag>
  </div>
</template>

<script>
import { ElPopover, ElTag } from 'element-plus'

export default {
  name: 'WorkbenchMultiTagEditor',
  components: { ElPopover, ElTag },
  props: {
    modelValue: { type: Array, default: () => [] },
    options: { type: Array, default: () => [] },
    tones: { type: Object, default: () => ({}) },
    editable: { type: Boolean, default: false },
    align: { type: String, default: 'center' },
  },
  emits: ['update:modelValue', 'change'],
  data() {
    return { activated: false, visible: false, deactivateTimer: 0 }
  },
  computed: {
    selected() {
      const values = (Array.isArray(this.modelValue) ? this.modelValue : [])
        .map((item) => String(item).trim())
        .filter(Boolean)
      if (!this.options.length) return values
      const chosen = new Set(values)
      const ordered = this.options.filter((item) => chosen.has(item))
      const extra = values.filter((item) => !this.options.includes(item))
      return [...ordered, ...extra]
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
      this.deactivateTimer = window.setTimeout(() => {
        this.deactivateTimer = 0
        if (!this.visible) this.activated = false
      }, 220)
    },
    toneOf(item) {
      return this.tones[item] || 'info'
    },
    toggle(item) {
      const next = this.selected.includes(item)
        ? this.selected.filter((value) => value !== item)
        : this.options.filter((value) => value === item || this.selected.includes(value))
      this.$emit('update:modelValue', next)
      this.$emit('change', next)
    },
  },
}
</script>

<style>
.workbench-multi-tags {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 4px;
  max-width: 100%;
}
.workbench-multi-tags.is-editable {
  cursor: pointer;
}
.workbench-multi-tags.is-start {
  justify-content: flex-start;
}
.workbench-multi-tags .workbench-status-tag.is-empty {
  color: var(--el-text-color-placeholder);
}
.el-tag.list-status-tag.is-purple {
  --el-tag-text-color: #7c5cf0;
  --el-tag-border-color: #beaef8;
  color: #7c5cf0;
  border-color: #beaef8;
}
.el-tag.list-status-tag.is-purple.el-tag--light {
  --el-tag-bg-color: #f2effe;
  background-color: #f2effe;
}
.workbench-multi-tag-popper.el-popover.el-popper {
  min-width: 0;
  padding: 10px 12px;
}
.workbench-multi-tag-options {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.workbench-multi-tag-option {
  display: flex;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
}
.workbench-multi-tag-option .list-status-tag {
  min-width: 5.5em;
  height: 26px;
  justify-content: center;
  pointer-events: none;
}
.workbench-multi-tag-option:hover .list-status-tag,
.workbench-multi-tag-option.is-current .list-status-tag {
  box-shadow: 0 0 0 1px currentColor;
}
</style>
