<template>
  <div
    ref="wrap"
    class="workbench-data-table"
    :class="{ 'is-column-moving': Boolean(drag) }"
  >
    <el-table v-bind="$attrs">
      <el-table-column
        v-for="col in displayColumns"
        :key="col.key"
        :prop="col.prop"
        :label="col.label"
        :width="col.width"
        :min-width="col.minWidth"
        :align="col.align || 'center'"
        :class-name="col.className"
        :fixed="col.fixed"
        :show-overflow-tooltip="col.showOverflowTooltip"
      >
        <template #header>
          <div
            class="wb-col-hd"
            :class="{ 'is-movable': !isPinned(col.key) }"
            :data-col-key="col.key"
            @mousedown="onHeaderMouseDown($event, col)"
          >
            <slot :name="'header-' + col.key" :column="col">{{ col.label }}</slot>
          </div>
        </template>
        <template v-if="$slots[col.key]" #default="scope">
          <slot :name="col.key" v-bind="scope" />
        </template>
        <template v-else #default="{ row }">
          {{ formatPlain(row[col.prop || col.key]) }}
        </template>
      </el-table-column>
    </el-table>
    <div ref="dropLine" class="wb-col-drop-line" aria-hidden="true" />
    <div ref="ghost" class="wb-col-ghost" aria-hidden="true" />
    <el-dialog
      v-model="pickerOpen"
      class="wb-col-picker-dialog"
      title="显示字段"
      width="720px"
      append-to-body
      align-center
      destroy-on-close
      :modal="false"
      :lock-scroll="false"
    >
      <p class="wb-col-picker-hint">与 Excel 相同的字段。拖动可调序，序号和操作固定。</p>
      <el-checkbox-group v-model="visibleDraft" class="wb-col-picker">
        <div
          v-for="col in orderDraft"
          :key="col.key"
          class="wb-col-picker-item"
          :class="{ 'is-pinned': isPinned(col.key), 'is-dragging': pickerDragFrom === col.key }"
          :draggable="!isPinned(col.key)"
          @dragstart="onPickerDragStart($event, col)"
          @dragover.prevent="onPickerDragOver(col)"
          @dragend="onPickerDragEnd"
        >
          <el-checkbox
            :label="col.key"
            :disabled="isPinned(col.key)"
          >
            {{ col.label }}
          </el-checkbox>
        </div>
      </el-checkbox-group>
      <template #footer>
        <el-button @click="pickerOpen = false">取消</el-button>
        <el-button type="primary" @click="applyColumnPicker">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ElButton, ElCheckbox, ElCheckboxGroup, ElDialog, ElTable, ElTableColumn } from 'element-plus'

import { createColumnOrder } from './columnOrder'

export default {
  name: 'WorkbenchDataTable',
  components: { ElButton, ElCheckbox, ElCheckboxGroup, ElDialog, ElTable, ElTableColumn },
  inheritAttrs: false,
  props: {
    columns: { type: Array, required: true },
    storageKey: { type: String, required: true },
    pinFirst: { type: String, default: 'sort_order' },
    pinLast: { type: String, default: 'actions' },
  },
  emits: ['reorder'],
  data() {
    return {
      orderedColumns: [],
      hiddenKeys: [],
      pickerOpen: false,
      visibleDraft: [],
      orderDraft: [],
      pickerDragFrom: '',
      drag: null,
    }
  },
  computed: {
    displayColumns() {
      const hidden = new Set(this.hiddenKeys)
      return this.orderedColumns.filter((column) => this.isPinned(column.key) || !hidden.has(column.key))
    },
  },
  created() {
    this.reloadColumns()
  },
  beforeUnmount() {
    this.unbindDrag()
  },
  methods: {
    columnOrder() {
      return createColumnOrder(this.storageKey, this.columns, {
        pinFirstKey: this.pinFirst,
        pinLastKey: this.pinLast,
        defaultHidden: this.columns
          .filter((column) => !this.isPinned(column.key) && column.defaultVisible !== true)
          .map((column) => column.key),
      })
    },
    persistColumns() {
      this.columnOrder().save(this.orderedColumns, this.hiddenKeys)
    },
    reloadColumns() {
      const order = this.columnOrder()
      this.orderedColumns = order.load()
      this.hiddenKeys = order.loadHidden()
    },
    resetColumnOrder() {
      this.columnOrder().clear()
      this.reloadColumns()
      this.$emit('reorder', this.orderedColumns)
    },
    formatPlain(value) {
      if (Array.isArray(value)) return value.filter(Boolean).join('、')
      if (value == null) return ''
      return String(value)
    },
    openColumnPicker() {
      this.orderDraft = [...this.orderedColumns]
      this.visibleDraft = this.orderDraft
        .filter((column) => this.isPinned(column.key) || !this.hiddenKeys.includes(column.key))
        .map((column) => column.key)
      this.pickerDragFrom = ''
      this.pickerOpen = true
    },
    applyColumnPicker() {
      const visible = new Set(this.visibleDraft)
      this.orderedColumns = this.orderDraft
      this.hiddenKeys = this.orderDraft
        .filter((column) => !this.isPinned(column.key) && !visible.has(column.key))
        .map((column) => column.key)
      this.persistColumns()
      this.pickerOpen = false
      this.$emit('reorder', this.orderedColumns)
    },
    onPickerDragStart(event, column) {
      if (this.isPinned(column.key) || event.target?.closest?.('.el-checkbox__input')) {
        event.preventDefault()
        return
      }
      this.pickerDragFrom = column.key
      event.dataTransfer.effectAllowed = 'move'
      event.dataTransfer.setData('text/plain', column.key)
    },
    onPickerDragOver(column) {
      if (!this.pickerDragFrom || this.isPinned(column.key)) return
      const next = this.columnOrder().move(this.orderDraft, this.pickerDragFrom, column.key)
      if (next !== this.orderDraft) this.orderDraft = next
    },
    onPickerDragEnd() {
      this.pickerDragFrom = ''
    },
    isPinned(key) {
      return key === this.pinFirst || key === this.pinLast
    },
    onHeaderMouseDown(event, column) {
      if (event.button !== 0 || !event.shiftKey || this.isPinned(column.key)) return
      if (event.target?.closest?.('button, input, textarea, .el-button')) return
      event.preventDefault()
      this.drag = { from: column.key, to: column.key }
      this.markSourceColumn(column.key)
      this.paint(event)
      window.addEventListener('mousemove', this.onHeaderMouseMove)
      window.addEventListener('mouseup', this.onHeaderMouseUp)
    },
    collectHeaders() {
      const wrap = this.$refs.wrap
      if (!wrap) return []
      const byKey = new Map()
      for (const el of wrap.querySelectorAll('.wb-col-hd[data-col-key]')) {
        const key = el.getAttribute('data-col-key') || ''
        if (!key || this.isPinned(key)) continue
        const rect = el.getBoundingClientRect()
        if (rect.width <= 2) continue
        const prev = byKey.get(key)
        if (!prev || rect.width > prev.rect.width) byKey.set(key, { key, rect })
      }
      return [...byKey.values()].sort((a, b) => a.rect.left - b.rect.left)
    },
    headerHit(clientX) {
      const headers = this.collectHeaders()
      if (!headers.length) return ''
      let nearest = headers[0]
      let best = Infinity
      for (const item of headers) {
        if (clientX >= item.rect.left && clientX <= item.rect.right) return item.key
        const dist = clientX < item.rect.left
          ? item.rect.left - clientX
          : clientX - item.rect.right
        if (dist < best) {
          best = dist
          nearest = item
        }
      }
      return nearest.key
    },
    onHeaderMouseMove(event) {
      if (!this.drag) return
      const key = this.headerHit(event.clientX)
      if (key) this.drag.to = key
      this.paint(event)
    },
    onHeaderMouseUp() {
      const move = this.drag
      this.unbindDrag()
      if (!move || move.from === move.to) return
      const next = this.columnOrder().move(this.orderedColumns, move.from, move.to)
      if (next === this.orderedColumns) return
      this.orderedColumns = next
      this.persistColumns()
      this.$emit('reorder', next)
    },
    unbindDrag() {
      window.removeEventListener('mousemove', this.onHeaderMouseMove)
      window.removeEventListener('mouseup', this.onHeaderMouseUp)
      this.drag = null
      this.markSourceColumn('')
      this.paint()
    },
    markSourceColumn(key) {
      const wrap = this.$refs.wrap
      wrap?.querySelectorAll('th.is-column-from').forEach((el) => {
        el.classList.remove('is-column-from')
      })
      if (!key || !wrap) return
      wrap.querySelector(`[data-col-key="${key}"]`)?.closest('th')?.classList.add('is-column-from')
    },
    paint(event) {
      const wrap = this.$refs.wrap
      const line = this.$refs.dropLine
      const ghost = this.$refs.ghost
      if (!this.drag || !wrap || !line || !ghost) {
        if (line) line.style.display = 'none'
        if (ghost) ghost.style.display = 'none'
        return
      }
      const wrapRect = wrap.getBoundingClientRect()
      if (event) {
        ghost.textContent = this.orderedColumns.find((column) => column.key === this.drag.from)?.label || ''
        ghost.style.display = 'block'
        ghost.style.transform = `translate3d(${event.clientX - wrapRect.left + 12}px, ${event.clientY - wrapRect.top + 16}px, 0)`
      }
      const to = wrap.querySelector(`[data-col-key="${this.drag.to}"]`)?.closest('th')
      if (!to) return
      const fromIndex = this.orderedColumns.findIndex((column) => column.key === this.drag.from)
      const toIndex = this.orderedColumns.findIndex((column) => column.key === this.drag.to)
      const rect = to.getBoundingClientRect()
      const insertRight = toIndex === fromIndex
        ? Boolean(event && event.clientX > (rect.left + rect.right) / 2)
        : toIndex > fromIndex
      line.style.display = 'block'
      line.style.height = `${Math.max(0, wrapRect.bottom - rect.top)}px`
      line.style.transform = `translate3d(${(insertRight ? rect.right : rect.left) - wrapRect.left}px, ${rect.top - wrapRect.top}px, 0)`
    },
  },
}
</script>

<style scoped>
.workbench-data-table {
  position: relative;
  width: 100%;
}

.workbench-data-table.is-column-moving {
  user-select: none;
}

.wb-col-hd {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 22px;
}

.wb-col-hd.is-movable {
  cursor: grab;
}

.workbench-data-table.is-column-moving .wb-col-hd {
  cursor: grabbing;
}

.workbench-data-table :deep(th.is-column-from) {
  opacity: 0.4;
}

.wb-col-drop-line {
  position: absolute;
  top: 0;
  left: -1px;
  z-index: 11;
  display: none;
  width: 2px;
  pointer-events: none;
  background: var(--el-color-primary);
  box-shadow: 0 0 0 1px var(--el-color-primary-light-7);
}

.wb-col-ghost {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 12;
  display: none;
  max-width: 200px;
  padding: 6px 10px;
  overflow: hidden;
  pointer-events: none;
  color: var(--el-color-primary);
  font-size: 13px;
  font-weight: 650;
  line-height: 1.3;
  white-space: nowrap;
  text-overflow: ellipsis;
  background: #fff;
  border: 1px solid var(--el-color-primary-light-5);
  border-radius: 4px;
  box-shadow: 0 6px 16px rgb(15 23 42 / 12%);
}
</style>

<style>
.wb-col-picker-dialog {
  border-radius: 8px;
  box-shadow: 0 12px 36px rgb(15 23 42 / 16%);
}

.wb-col-picker-dialog .el-dialog__body {
  padding: 8px 16px 4px;
}

.wb-col-picker-hint {
  margin: 0 0 10px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.4;
}

.wb-col-picker {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(128px, 1fr));
  gap: 2px 8px;
}

.wb-col-picker-item {
  cursor: grab;
}

.wb-col-picker-item.is-pinned {
  cursor: default;
}

.wb-col-picker-item.is-dragging {
  opacity: 0.4;
}

.wb-col-picker-item .el-checkbox {
  margin-right: 0;
  height: 30px;
  overflow: hidden;
}

.wb-col-picker-item .el-checkbox__label {
  overflow: hidden;
  font-size: 13px;
  text-overflow: ellipsis;
}
</style>
