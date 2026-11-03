<template>
  <span class="assay-split-pill" :class="{ 'is-compact': compact }" @click.stop>
    <template v-for="badge in badges" :key="badge.key">
      <el-popover
        v-if="activeKey === badge.key"
        v-model:visible="visible"
        :placement="popoverPlacement(badge)"
        trigger="click"
        :transition="popoverTransition(badge)"
        :width="132"
        :disabled="!editable || !badge.editable"
        :teleported="true"
        @hide="scheduleDeactivate"
      >
        <div class="workbench-status-option-list">
          <button
            v-for="option in badge.options"
            :key="option.value"
            type="button"
            class="workbench-status-option"
            :class="{ 'is-current': option.value === badge.full }"
            @click.stop="choose(badge, option)"
          >
            {{ optionLabel(badge, option) }}
          </button>
        </div>
        <template #reference>
          <span
            class="assay-split-half is-editable"
            :class="`is-${badge.tone}`"
            :title="`${badge.full}（点击修改）`"
          >
            {{ badge.text }}
          </span>
        </template>
      </el-popover>
      <span
        v-else
        class="assay-split-half"
        :class="[`is-${badge.tone}`, { 'is-editable': editable && badge.editable }]"
        :title="editable && badge.editable ? `${badge.full}（点击修改）` : badge.full"
        @click.stop="activateAndOpen(badge)"
      >
        {{ badge.text }}
      </span>
    </template>
  </span>
</template>

<script>
import { ElPopover } from 'element-plus'

export default {
  name: 'SynthesisAssayStatusEditor',
  components: { ElPopover },
  props: {
    badges: { type: Array, default: () => [] },
    editable: { type: Boolean, default: false },
    compact: { type: Boolean, default: false },
  },
  emits: ['change'],
  data() {
    return {
      activeKey: '',
      visible: false,
      deactivateTimer: 0,
    }
  },
  computed: {
    single() {
      return this.badges.length === 1
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
    activateAndOpen(badge) {
      if (!this.editable || !badge.editable) return
      if (this.deactivateTimer) {
        clearTimeout(this.deactivateTimer)
        this.deactivateTimer = 0
      }
      this.activeKey = badge.key
      this.$nextTick(() => {
        this.visible = true
      })
    },
    scheduleDeactivate() {
      if (this.deactivateTimer) clearTimeout(this.deactivateTimer)
      this.deactivateTimer = window.setTimeout(() => {
        this.deactivateTimer = 0
        if (!this.visible) this.activeKey = ''
      }, 220)
    },
    optionLabel(badge, option) {
      return this.single ? `${badge.kind}·${option.label}` : option.label
    },
    popoverPlacement(badge) {
      return !this.single && badge.key === 'affinity' ? 'left' : 'right'
    },
    popoverTransition(badge) {
      return this.popoverPlacement(badge) === 'left'
        ? 'el-zoom-in-right'
        : 'el-zoom-in-left'
    },
    choose(badge, option) {
      this.visible = false
      if (option.value !== badge.full) {
        this.$emit('change', { key: badge.key, value: option.value })
      }
    },
  },
}
</script>

<style scoped>
.assay-split-pill {
  display: inline-flex;
  align-items: stretch;
  height: 25px;
  font-size: 13px;
  line-height: 1;
  white-space: nowrap;
  border-radius: var(--list-chip-radius);
}

.assay-split-half {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 8px;
  border: 1px solid;
}

.assay-split-half:first-child {
  border-top-left-radius: var(--list-chip-radius);
  border-bottom-left-radius: var(--list-chip-radius);
}

.assay-split-half:last-child {
  border-top-right-radius: var(--list-chip-radius);
  border-bottom-right-radius: var(--list-chip-radius);
}

.assay-split-half + .assay-split-half {
  margin-left: -1px;
}

.assay-split-half.is-editable {
  cursor: pointer;
}

.assay-split-pill.is-compact .assay-split-half {
  padding: 0 4px;
}

.assay-split-half.is-wait {
  color: #d48806;
  background: #fffdf8;
  border-color: var(--el-color-warning-light-5);
}

.assay-split-half.is-run {
  color: var(--el-color-primary);
  background: var(--el-fill-color-extra-light);
  border-color: var(--el-color-primary-light-5);
  z-index: 2;
}

.assay-split-half.is-done {
  color: var(--el-color-success-dark-2);
  background: #f6ffed;
  border-color: var(--el-color-success-light-5);
  z-index: 1;
}

html.dark .assay-split-half.is-wait {
  color: var(--el-color-warning);
  background: var(--el-color-warning-light-9);
}

html.dark .assay-split-half.is-done {
  color: var(--el-color-success);
  background: var(--el-color-success-light-9);
}

</style>
