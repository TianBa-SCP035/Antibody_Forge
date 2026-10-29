<template>
  <el-popover
    v-if="activated"
    v-model:visible="visible"
    placement="bottom"
    trigger="click"
    transition="el-zoom-in-top"
    :width="'auto'"
    :offset="6"
    :disabled="!editable"
    :teleported="true"
    popper-class="wb-color-mark-popper vxe-table--ignore-clear"
    @hide="scheduleDeactivate"
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
    <template #reference>
      <button
        v-if="editable"
        type="button"
        class="wb-color-mark-btn"
        :class="{ 'has-color': Boolean(currentOption), 'is-open': visible }"
        :style="currentOption ? { '--dot-color': currentOption.swatch } : undefined"
        title="标记格子底色"
        @dblclick.stop
        @click.stop
      />
    </template>
  </el-popover>
  <button
    v-else-if="editable"
    type="button"
    class="wb-color-mark-btn"
    :class="{ 'has-color': Boolean(currentOption) }"
    :style="currentOption ? { '--dot-color': currentOption.swatch } : undefined"
    title="标记格子底色"
    @dblclick.stop
    @click.stop="activateAndOpen"
  />
</template>

<script>
import { defineComponent, h } from 'vue'
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

function normalizeSelectedColors(val) {
  if (Array.isArray(val)) return val.map((v) => String(v || '').trim()).filter(Boolean)
  return String(val || '')
    .split(',')
    .map((v) => v.trim())
    .filter(Boolean)
}

export const WorkbenchColorFilterHeader = defineComponent({
  name: 'WorkbenchColorFilterHeader',
  props: {
    modelValue: { type: [Array, String], default: '' },
    label: { type: String, default: '' },
    batchCount: { type: Number, default: 0 },
  },
  emits: ['update:modelValue', 'change', 'batch-mark'],
  data() {
    return { visible: false }
  },
  computed: {
    selectedList() {
      return normalizeSelectedColors(this.modelValue)
    },
    singleActiveSwatch() {
      if (this.selectedList.length !== 1) return ''
      return CELL_COLOR_MAP.get(this.selectedList[0])?.swatch || ''
    },
  },
  methods: {
    emitValue(list) {
      const next = list.join(',')
      this.$emit('update:modelValue', next)
      this.$emit('change', next)
    },
    onItemClick(key, isRightClick = false) {
      const cur = [...this.selectedList]
      if (!isRightClick) {
        const next = cur.length === 1 && cur[0] === key ? [] : [key]
        this.visible = false
        this.emitValue(next)
        return
      }
      const idx = cur.indexOf(key)
      if (idx >= 0) cur.splice(idx, 1)
      else cur.push(key)
      this.emitValue(cur)
    },
    clearFilter() {
      this.visible = false
      this.emitValue([])
    },
    onBatchMark(colorKey) {
      this.visible = false
      this.$emit('batch-mark', colorKey)
    },
  },
  render() {
    const filterItems = [
      ...CELL_COLOR_OPTIONS,
      { key: 'none', label: '无颜色', swatch: 'transparent', isNone: true },
    ]
    const active = this.selectedList.length > 0
    return h(
      'span',
      { class: ['wb-color-header-wrap', { 'is-active': active, 'is-open': this.visible }] },
      [
        this.$slots.default ? this.$slots.default() : h('span', null, this.label),
        h(
          ElPopover,
          {
            visible: this.visible,
            'onUpdate:visible': (v) => {
              this.visible = v
            },
            placement: 'bottom',
            trigger: 'click',
            width: 196,
            offset: 6,
            teleported: true,
            popperClass: 'wb-color-filter-popper vxe-table--ignore-clear',
          },
          {
            reference: () =>
              h('button', {
                type: 'button',
                class: [
                  'wb-color-mark-btn',
                  'is-header',
                  {
                    'has-color': Boolean(this.singleActiveSwatch),
                    'is-active': active,
                    'is-open': this.visible,
                  },
                ],
                style: this.singleActiveSwatch
                  ? { '--dot-color': this.singleActiveSwatch }
                  : undefined,
                title: '按颜色筛选（左键单选，右键多选）',
                onClick: (e) => e.stopPropagation(),
              }),
            default: () =>
              h('div', { class: 'wb-color-filter-panel', onClick: (e) => e.stopPropagation() }, [
                this.batchCount > 1
                  ? h('div', { class: 'wb-color-batch-sec' }, [
                      h('div', { class: 'wb-color-panel-hd' }, `批量标记选中 (${this.batchCount}行)`),
                      h('div', { class: 'wb-color-swatch-bar' }, [
                        ...CELL_COLOR_OPTIONS.map((item) =>
                          h('button', {
                            key: item.key,
                            type: 'button',
                            class: 'wb-color-swatch-item',
                            title: item.label,
                            style: { '--swatch-color': item.swatch, '--swatch-bg': item.bg },
                            onClick: () => this.onBatchMark(item.key),
                          }),
                        ),
                        h(
                          'button',
                          {
                            type: 'button',
                            class: 'wb-color-swatch-clear',
                            title: '清除选中行颜色',
                            onClick: () => this.onBatchMark(null),
                          },
                          '×',
                        ),
                      ]),
                    ])
                  : null,
                h('div', { class: 'wb-color-panel-hd' }, [
                  h('span', null, '颜色筛选（右键多选）'),
                  active
                    ? h(
                        'button',
                        { type: 'button', class: 'wb-color-reset-btn', onClick: this.clearFilter },
                        '重置',
                      )
                    : null,
                ]),
                h(
                  'div',
                  { class: 'wb-color-filter-list' },
                  filterItems.map((item) => {
                    const itemActive = this.selectedList.includes(item.key)
                    return h(
                      'button',
                      {
                        key: item.key,
                        type: 'button',
                        class: ['wb-color-filter-opt', { 'is-active': itemActive }],
                        onClick: () => this.onItemClick(item.key, false),
                        onContextmenu: (e) => {
                          e.preventDefault()
                          e.stopPropagation()
                          this.onItemClick(item.key, true)
                        },
                      },
                      [
                        h('i', {
                          class: ['wb-color-opt-dot', { 'is-none': item.isNone }],
                          style: item.isNone ? undefined : { backgroundColor: item.swatch },
                        }),
                        h('span', { class: 'wb-color-opt-label' }, item.label),
                        itemActive ? h('span', { class: 'wb-color-opt-check' }, '✓') : null,
                      ],
                    )
                  }),
                ),
              ]),
          },
        ),
      ],
    )
  },
})

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
      if (!val) this.visible = false
    },
    visible(val) {
      if (!val) this.scheduleDeactivate()
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
.vxe-body--column.wb-color-cell:has(.wb-color-mark-btn):hover > .vxe-cell {
  padding-right: 22px;
}

td.wb-cell-color-yellow, .vxe-body--column.wb-cell-color-yellow { --wb-cell-bg: #fef3c7; --wb-cell-bg-hover: #fde68a; --wb-cell-fg: #78350f; }
td.wb-cell-color-orange, .vxe-body--column.wb-cell-color-orange { --wb-cell-bg: #ffedd5; --wb-cell-bg-hover: #fed7aa; --wb-cell-fg: #7c2d12; }
td.wb-cell-color-red, .vxe-body--column.wb-cell-color-red { --wb-cell-bg: #ffe4e6; --wb-cell-bg-hover: #fecdd3; --wb-cell-fg: #881337; }
td.wb-cell-color-green, .vxe-body--column.wb-cell-color-green { --wb-cell-bg: #dcfce7; --wb-cell-bg-hover: #bbf7d0; --wb-cell-fg: #14532d; }
td.wb-cell-color-blue, .vxe-body--column.wb-cell-color-blue { --wb-cell-bg: #dbeafe; --wb-cell-bg-hover: #bfdbfe; --wb-cell-fg: #1e3a8a; }
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
.wb-color-mark-btn.is-header {
  left: calc(100% + 1px);
  right: auto;
  width: 20px;
  height: 20px;
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
.wb-color-mark-btn.is-header::after {
  width: 13px;
  height: 13px;
}
.wb-color-mark-btn.has-color::after {
  background: var(--dot-color);
  border-color: rgba(255, 255, 255, 0.95);
}
td:hover .wb-color-mark-btn,
.vxe-body--column:hover .wb-color-mark-btn,
th:hover .wb-color-mark-btn.is-header,
.vxe-header--column:hover .wb-color-mark-btn.is-header,
.wb-color-mark-btn.is-active,
.wb-color-mark-btn.is-open {
  opacity: 1;
  pointer-events: auto;
}
.wb-color-mark-btn:hover::after,
.wb-color-mark-btn.is-open::after {
  transform: scale(1.16);
}

.wb-color-header-wrap {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.wb-color-header-wrap.is-active {
  color: var(--el-color-primary);
  font-weight: 650;
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
  background: #fff;
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

.wb-color-filter-popper.el-popover.el-popper {
  padding: 8px 10px;
}
.wb-color-filter-panel {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.wb-color-batch-sec {
  padding-bottom: 7px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.wb-color-panel-hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11.5px;
  color: var(--el-text-color-secondary);
}
.wb-color-reset-btn {
  padding: 0 2px;
  border: 0;
  background: transparent;
  color: var(--el-color-primary);
  font-size: 11.5px;
  cursor: pointer;
}
.wb-color-filter-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.wb-color-filter-opt {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 5px 8px;
  border: 0;
  border-radius: 5px;
  background: transparent;
  color: var(--el-text-color-regular);
  font-size: 12.5px;
  text-align: left;
  cursor: pointer;
}
.wb-color-filter-opt:hover,
.wb-color-filter-opt.is-active {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
}
.wb-color-opt-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
}
.wb-color-opt-dot.is-none {
  border: 1px dashed #94a3b8;
}
.wb-color-opt-label {
  flex: 1;
}
.wb-color-opt-check {
  font-weight: 700;
}
</style>
