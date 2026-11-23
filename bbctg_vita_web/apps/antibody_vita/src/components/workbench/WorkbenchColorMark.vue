<template>
  <button
    v-if="editable"
    ref="btnRef"
    type="button"
    class="wb-color-mark-btn"
    :class="{ 'has-color': Boolean(currentOption), 'is-open': visible }"
    :style="currentOption ? { '--dot-color': currentOption.swatch } : undefined"
    title="标记格子底色"
    @dblclick.stop
    @click.stop="activateAndOpen"
  />
  <el-popover
    v-if="activated && editable"
    v-model:visible="visible"
    :virtual-ref="$refs.btnRef"
    virtual-triggering
    placement="bottom"
    trigger="click"
    transition="el-fade-in-linear"
    :show-after="0"
    :hide-after="0"
    :width="'auto'"
    :offset="6"
    :teleported="true"
    popper-class="wb-color-mark-popper vxe-table--ignore-clear"
  >
    <div class="wb-color-swatch-bar" @click.stop>
      <button
        v-for="item in options"
        :key="item.key"
        type="button"
        class="wb-color-swatch-item"
        :class="{ 'is-current': item.key === value }"
        :title="item.label"
        :style="{ '--swatch-color': item.swatch, '--swatch-bg': item.bg }"
        @click.stop="choose(item.key === value ? null : item.key)"
      />
      <button
        type="button"
        class="wb-color-swatch-clear"
        :class="{ 'is-current': !value }"
        title="清除颜色"
        @click.stop="choose(null)"
      >
        ×
      </button>
    </div>
  </el-popover>
</template>

<script>
import { ElPopover } from 'element-plus'

export const CELL_COLOR_OPTIONS = Object.freeze([
  { key: 'yellow', label: '明黄', swatch: '#f59e0b', bg: '#fef3c7' },
  { key: 'orange', label: '柔橙', swatch: '#f97316', bg: '#ffedd5' },
  { key: 'red', label: '珊瑚红', swatch: '#f43f5e', bg: '#ffe4e6' },
  { key: 'green', label: '薄荷绿', swatch: '#10b981', bg: '#dcfce7' },
  { key: 'blue', label: '晴空蓝', swatch: '#3b82f6', bg: '#dbeafe' },
  { key: 'purple', label: '丁香紫', swatch: '#a855f7', bg: '#f3e8ff' },
])

const CELL_COLOR_MAP = new Map(CELL_COLOR_OPTIONS.map((item) => [item.key, item]))

export function cellColorClass(color, withHost = true) {
  const key = String(color || '').trim()
  const tone = CELL_COLOR_MAP.has(key) ? `wb-cell-color-${key}` : ''
  return withHost ? (tone ? `wb-color-cell ${tone}` : 'wb-color-cell') : tone
}

let activeMark = null

export default {
  name: 'WorkbenchColorMark',
  components: { ElPopover },
  props: {
    value: { type: String, default: '' },
    editable: { type: Boolean, default: false },
  },
  emits: ['change'],
  data() {
    return { activated: false, visible: false, deactivateTimer: 0, options: CELL_COLOR_OPTIONS }
  },
  computed: {
    currentOption() {
      return CELL_COLOR_MAP.get(String(this.value || '').trim()) || null
    },
  },
  watch: {
    editable(val) {
      if (!val) this.closeNow()
    },
    visible(val) {
      if (val) {
        if (activeMark && activeMark !== this) activeMark.closeNow()
        activeMark = this
      } else {
        if (activeMark === this) activeMark = null
        this.scheduleDeactivate()
      }
    },
  },
  deactivated() {
    this.closeNow()
  },
  beforeUnmount() {
    this.closeNow()
  },
  methods: {
    activateAndOpen() {
      if (!this.editable) return
      if (this.deactivateTimer) {
        clearTimeout(this.deactivateTimer)
        this.deactivateTimer = 0
      }
      if (this.activated) return
      if (activeMark && activeMark !== this) activeMark.closeNow()
      this.activated = true
      this.$nextTick(() => {
        this.visible = true
      })
    },
    closeNow() {
      if (this.deactivateTimer) {
        clearTimeout(this.deactivateTimer)
        this.deactivateTimer = 0
      }
      this.visible = false
      this.activated = false
      if (activeMark === this) activeMark = null
    },
    scheduleDeactivate() {
      if (this.deactivateTimer) clearTimeout(this.deactivateTimer)
      this.deactivateTimer = window.setTimeout(() => {
        this.deactivateTimer = 0
        if (!this.visible) this.activated = false
      }, 160)
    },
    choose(nextVal) {
      this.visible = false
      const norm = nextVal || null
      if ((this.value || null) !== norm) {
        this.$emit('change', norm)
      }
    },
  },
}
</script>

<style>
td.wb-color-cell,
.vxe-body--column.wb-color-cell {
  position: relative;
}
td.wb-color-cell > .cell,
.vxe-body--column.wb-color-cell > .vxe-cell {
  position: static;
}

td.wb-cell-color-yellow, .vxe-body--column.wb-cell-color-yellow { --wb-cell-bg: #fef3c7; --wb-cell-bg-hover: #fde68a; --wb-cell-fg: #78350f; }
td.wb-cell-color-orange, .vxe-body--column.wb-cell-color-orange { --wb-cell-bg: #ffedd5; --wb-cell-bg-hover: #fed7aa; --wb-cell-fg: #7c2d12; }
td.wb-cell-color-red, .vxe-body--column.wb-cell-color-red { --wb-cell-bg: #ffe4e6; --wb-cell-bg-hover: #fecdd3; --wb-cell-fg: #881337; } /* theme-ok */
td.wb-cell-color-green, .vxe-body--column.wb-cell-color-green { --wb-cell-bg: #dcfce7; --wb-cell-bg-hover: #bbf7d0; --wb-cell-fg: #14532d; }
td.wb-cell-color-blue, .vxe-body--column.wb-cell-color-blue { --wb-cell-bg: #dbeafe; --wb-cell-bg-hover: #bfdbfe; --wb-cell-fg: #1e3a8a; } /* theme-ok */
td.wb-cell-color-purple, .vxe-body--column.wb-cell-color-purple { --wb-cell-bg: #f3e8ff; --wb-cell-bg-hover: #e9d5ff; --wb-cell-fg: #581c87; }

.el-table td[class*="wb-cell-color-"],
.el-table--striped .el-table__body tr.el-table__row--striped td[class*="wb-cell-color-"],
.vxe-table .vxe-body--column[class*="wb-cell-color-"] {
  background-color: var(--wb-cell-bg) !important;
  color: var(--wb-cell-fg);
}
.el-table__body tr:hover > td[class*="wb-cell-color-"],
.el-table__body tr.hover-row > td[class*="wb-cell-color-"],
.vxe-table .vxe-body--row.row--hover > .vxe-body--column[class*="wb-cell-color-"],
.vxe-table .vxe-body--row:hover > .vxe-body--column[class*="wb-cell-color-"] {
  background-color: var(--wb-cell-bg-hover) !important;
}

.wb-color-mark-btn {
  position: absolute;
  left: 3px;
  top: 50%;
  transform: translateY(-50%);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: transparent;
  cursor: pointer;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.14s ease;
  z-index: 3;
}
.vxe-body--column .wb-color-mark-btn {
  left: auto;
  right: 2px;
}
.wb-color-mark-btn::after {
  content: '';
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 1.5px solid rgba(255, 255, 255, 0.92);
  background:
    radial-gradient(circle, rgba(255, 255, 255, 0.55) 0%, rgba(255, 255, 255, 0) 62%),
    conic-gradient(from 0deg, #fbbf24, #fb7185, #c084fc, #60a5fa, #34d399, #fbbf24);
  transition: transform 0.14s ease;
}
.wb-color-mark-btn.has-color::after {
  background: var(--dot-color);
  border-color: rgba(255, 255, 255, 0.95);
}
td:hover .wb-color-mark-btn,
.vxe-body--column:hover .wb-color-mark-btn,
.wb-color-mark-btn.is-open {
  opacity: 1;
  pointer-events: auto;
}
.wb-color-mark-btn:hover::after,
.wb-color-mark-btn.is-open::after {
  transform: scale(1.16);
}
.wb-color-mark-btn:active::after {
  transform: scale(0.9);
}

.wb-color-mark-popper.el-popover.el-popper {
  min-width: 0;
  padding: 6px 8px;
}
.wb-color-swatch-bar {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px;
}
.wb-color-swatch-item {
  width: 18px;
  height: 18px;
  padding: 0;
  border-radius: 50%;
  border: 2px solid var(--swatch-color);
  background: var(--swatch-bg);
  cursor: pointer;
  transition: transform 0.12s ease;
}
.wb-color-swatch-item:hover,
.wb-color-swatch-item.is-current {
  background: var(--swatch-color);
  transform: scale(1.14);
}
.wb-color-swatch-clear {
  width: 18px;
  height: 18px;
  padding: 0;
  border-radius: 50%;
  border: 1px dashed #cbd5e1;
  background: var(--el-bg-color);
  color: #64748b;
  font-size: 13px;
  line-height: 16px;
  text-align: center;
  cursor: pointer;
  transition: transform 0.12s ease, border-color 0.12s ease, color 0.12s ease;
}
.wb-color-swatch-clear:hover {
  border-color: #64748b;
  color: #0f172a;
  transform: scale(1.12);
}

html.dark .wb-color-swatch-clear {
  border-color: var(--el-border-color);
  color: var(--el-text-color-secondary);
}

html.dark .wb-color-swatch-clear:hover {
  border-color: var(--el-text-color-secondary);
  color: var(--el-text-color-primary);
}
</style>
