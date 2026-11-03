<template>
  <Teleport to="body">
    <transition name="wb-hm-fade">
      <div
        v-if="visible && column"
        ref="panel"
        class="wb-hm vxe-table--ignore-clear"
        :style="panelStyle"
        @mousedown.stop
        @click.stop
        @keydown="onPanelKeydown"
      >
        <div class="wb-hm-sort">
          <button
            type="button"
            class="wb-hm-item"
            :class="{ 'is-active': sortDir === 'asc' }"
            @click="$emit('sort', 'asc')"
          >
            <span class="wb-hm-icon">↑</span>{{ sortText.asc }}
          </button>
          <button
            type="button"
            class="wb-hm-item"
            :class="{ 'is-active': sortDir === 'desc' }"
            @click="$emit('sort', 'desc')"
          >
            <span class="wb-hm-icon">↓</span>{{ sortText.desc }}
          </button>
          <button
            v-if="sortDir"
            type="button"
            class="wb-hm-item is-muted"
            @click="$emit('sort', '')"
          >
            <span class="wb-hm-icon">×</span>清除排序
          </button>
        </div>

        <slot name="extra" />

        <div v-if="column.color && !column.sortOnly" class="wb-hm-sec">
          <div class="wb-hm-sec-hd">按颜色筛选</div>
          <div class="wb-hm-colors">
            <button
              v-for="item in colorOptions"
              :key="item.key"
              type="button"
              class="wb-hm-color"
              :class="{ 'is-active': colors.includes(item.key), 'is-none': item.key === 'none' }"
              :title="item.label"
              :style="{ '--swatch': item.swatch }"
              @click="toggleColor(item.key)"
            />
          </div>
        </div>

        <div v-if="!column.sortOnly" class="wb-hm-sec">
          <button
            type="button"
            class="wb-hm-item"
            :disabled="!filter"
            @click="$emit('apply', null)"
          >
            <span class="wb-hm-icon">⊘</span>清除“{{ column.label }}”的筛选
          </button>
          <div class="wb-hm-quick">
            <button
              type="button"
              class="wb-hm-chip"
              :class="{ 'is-active': condOp === 'blank' }"
              @click="applyQuick('blank')"
            >
              只看空白
            </button>
            <button
              type="button"
              class="wb-hm-chip"
              :class="{ 'is-active': condOp === 'not_blank' }"
              @click="applyQuick('not_blank')"
            >
              只看非空
            </button>
          </div>
          <div v-if="condOptions.length" class="wb-hm-cond">
            <el-select
              v-model="condOp"
              size="small"
              class="wb-hm-cond-op"
              placeholder="条件筛选"
              clearable
              :teleported="true"
              placement="bottom-start"
              :fallback-placements="popperFallbacks"
              popper-class="vxe-table--ignore-clear wb-hm-popper"
            >
              <el-option v-for="item in condOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
            <template v-if="condNeedsValue">
              <el-date-picker
                v-if="column.type === 'date'"
                v-model="condValue"
                type="date"
                size="small"
                value-format="YYYY-MM-DD"
                :placeholder="condOp === 'between' ? '开始' : '日期'"
                placement="bottom-start"
                :fallback-placements="popperFallbacks"
                popper-class="vxe-table--ignore-clear wb-hm-popper"
                class="wb-hm-cond-val"
              />
              <el-input
                v-else
                v-model="condValue"
                size="small"
                class="wb-hm-cond-val"
                :placeholder="condOp === 'between' ? '最小' : '值'"
                @keyup.enter="confirm"
              />
            </template>
          </div>
          <div v-if="condOp === 'between'" class="wb-hm-cond">
            <span class="wb-hm-cond-op wb-hm-cond-to">至</span>
            <el-date-picker
              v-if="column.type === 'date'"
              v-model="condValue2"
              type="date"
              size="small"
              value-format="YYYY-MM-DD"
              placeholder="结束"
              placement="bottom-start"
              :fallback-placements="popperFallbacks"
              popper-class="vxe-table--ignore-clear wb-hm-popper"
              class="wb-hm-cond-val"
            />
            <el-input
              v-else
              v-model="condValue2"
              size="small"
              class="wb-hm-cond-val"
              placeholder="最大"
              @keyup.enter="confirm"
            />
          </div>
        </div>

        <div v-if="!column.sortOnly" class="wb-hm-values">
          <el-input
            v-model="search"
            size="small"
            clearable
            placeholder="搜索"
            class="wb-hm-search"
            @input="scheduleSearch"
            @clear="scheduleSearch"
            @keyup.enter="confirm"
          />
          <div v-loading="loading" class="wb-hm-list">
            <div v-if="loadError" class="wb-hm-empty is-error">
              取值加载失败<button type="button" class="wb-hm-retry" @click="fetchValues">重试</button>
            </div>
            <div v-else-if="waitingKeyword" class="wb-hm-empty">输入关键字查找已有内容；也可用上方条件筛选</div>
            <label v-else-if="items.length" class="wb-hm-row is-all">
              <el-checkbox
                :model-value="allChecked"
                :indeterminate="someChecked && !allChecked"
                @change="toggleAll"
              />
              <span class="wb-hm-text">{{ allRowLabel }}</span>
            </label>
            <template v-for="row in rows" :key="row.id">
              <div v-if="row.group" class="wb-hm-row is-group">
                <button type="button" class="wb-hm-fold" @click="toggleGroup(row.group)">
                  {{ expanded.has(row.group) || searching ? '▾' : '▸' }}
                </button>
                <el-checkbox
                  :model-value="groupState(row.group) === 'all'"
                  :indeterminate="groupState(row.group) === 'some'"
                  @change="toggleGroupChecked(row.group, $event)"
                />
                <span class="wb-hm-text" @click="toggleGroup(row.group)">{{ row.label }}</span>
                <span class="wb-hm-count">{{ row.count }}</span>
              </div>
              <label v-else class="wb-hm-row" :class="{ 'is-child': row.child }">
                <el-checkbox
                  :model-value="isChecked(row.value)"
                  @change="toggleValue(row.value, $event)"
                />
                <span class="wb-hm-text" :class="{ 'is-blank': row.value === '' }">
                  {{ row.label }}<small v-if="row.hint" class="wb-hm-hint">{{ row.hint }}</small>
                </span>
                <span class="wb-hm-count">{{ row.count }}</span>
              </label>
            </template>
            <div v-if="!loading && !loadError && !waitingKeyword && !items.length" class="wb-hm-empty">无匹配项</div>
            <div v-if="truncateNote" class="wb-hm-empty">{{ truncateNote }}</div>
          </div>
        </div>

        <div v-if="externalHint" class="wb-hm-external">
          <span :title="externalHint">顶部筛选“{{ externalHint }}”表头无法表示</span>
          <button type="button" @click="$emit('clear-external')">清除</button>
        </div>

        <div v-if="!column.sortOnly" class="wb-hm-foot">
          <el-button size="small" @click="$emit('close')">取消</el-button>
          <el-button size="small" type="primary" :disabled="selectsNothing" @click="confirm">确定</el-button>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script>
import { ElButton, ElCheckbox, ElDatePicker, ElInput, ElOption, ElSelect, useZIndex } from 'element-plus'

import { createLatestRequest } from '#/utils/latestRequest'

import { CELL_COLOR_OPTIONS } from './WorkbenchColorMark.vue'

const PANEL_WIDTH = 268
const ALL_LIMIT = 1000
const RECENT_LIMIT = 200
const SEARCH_DEBOUNCE = 250
const POPPER_FALLBACKS = ['bottom-start', 'right-start', 'top-start']
const BLANK_LABEL = '(空白)'

const COND_OPTIONS = {
  text: [
    { value: 'contains', label: '包含' },
    { value: 'not_contains', label: '不包含' },
    { value: 'eq', label: '等于' },
    { value: 'neq', label: '不等于' },
    { value: 'starts', label: '开头是' },
    { value: 'ends', label: '结尾是' },
  ],
  number: [
    { value: 'eq', label: '等于' },
    { value: 'gte', label: '大于或等于' },
    { value: 'lte', label: '小于或等于' },
    { value: 'between', label: '介于' },
  ],
  date: [
    { value: 'eq', label: '等于' },
    { value: 'gte', label: '晚于或等于' },
    { value: 'lte', label: '早于或等于' },
    { value: 'between', label: '介于' },
  ],
}

const SORT_TEXT = {
  enum: { asc: '升序', desc: '降序' },
  number: { asc: '升序（小 → 大）', desc: '降序（大 → 小）' },
  date: { asc: '升序（旧 → 新）', desc: '降序（新 → 旧）' },
  default: { asc: '升序（A → Z）', desc: '降序（Z → A）' },
}

export default {
  name: 'WorkbenchHeaderMenu',
  components: { ElButton, ElCheckbox, ElDatePicker, ElInput, ElOption, ElSelect },
  props: {
    visible: { type: Boolean, default: false },
    anchor: { type: Object, default: null },
    column: { type: Object, default: null },
    filter: { type: Object, default: null },
    sortDir: { type: String, default: '' },
    loadValues: { type: Function, required: true },
    /** (items, keyword) => items；值已全部拿到时在本地搜索，规则与顶部下拉一致。 */
    searchValues: { type: Function, default: null },
    externalHint: { type: String, default: '' },
  },
  emits: ['sort', 'apply', 'close', 'clear-external'],
  setup() {
    const { nextZIndex } = useZIndex()
    return { nextZIndex }
  },
  data() {
    return {
      loading: false,
      loadError: false,
      items: [],
      // 未搜索时拿到的值；values=all 且未截断时，搜索直接在这里面过滤。
      baseItems: [],
      baseTruncated: false,
      truncated: false,
      search: '',
      activeKeyword: '',
      // 勾选模型：baseAll 表示默认全选，exceptions 记录与默认相反的值；搜索态单独记录未勾选的结果。
      baseAll: true,
      exceptions: new Set(),
      searchUnchecked: new Set(),
      expanded: new Set(),
      condOp: '',
      condValue: '',
      condValue2: '',
      colors: [],
      position: { left: 0, top: 0, maxHeight: 0 },
      zIndex: 3000,
      searchTimer: 0,
      followFrame: 0,
      popperFallbacks: POPPER_FALLBACKS,
      colorOptions: [...CELL_COLOR_OPTIONS, { key: 'none', label: '无颜色', swatch: 'transparent' }],
    }
  },
  computed: {
    panelStyle() {
      return {
        left: `${this.position.left}px`,
        top: `${this.position.top}px`,
        width: `${PANEL_WIDTH}px`,
        zIndex: this.zIndex,
        maxHeight: this.position.maxHeight ? `${Math.min(620, this.position.maxHeight)}px` : undefined,
      }
    },
    searching() {
      return Boolean(this.activeKeyword)
    },
    /** 一个值都没勾（含搜索无结果）时按 Excel 的做法不让确定，免得筛成空表。 */
    selectsNothing() {
      return this.buildState()?.values?.length === 0
    },
    valueMode() {
      return this.column?.values || 'all'
    },
    localSearch() {
      return this.valueMode === 'all' && !this.baseTruncated
    },
    waitingKeyword() {
      return this.valueMode === 'search' && !this.searching && !this.loading
    },
    allRowLabel() {
      if (!this.searching) return '(全选)'
      if (this.localSearch && !this.truncated) return '(选择所有搜索结果)'
      return `(所有包含“${this.activeKeyword}”的值)`
    },
    truncateNote() {
      if (!this.truncated) return ''
      const shown = this.items.filter((item) => item.value !== '').length
      if (this.searching) return `匹配较多，仅列出 ${shown} 个；全选搜索结果即按“包含”筛选`
      if (this.valueMode === 'recent') return `仅列出最近出现的 ${shown} 个，其余请搜索`
      return `值较多，仅列出前 ${shown} 个，其余请搜索`
    },
    sortText() {
      return SORT_TEXT[this.column?.type] || SORT_TEXT.default
    },
    condOptions() {
      const type = this.column?.type
      if (type === 'enum' || type === 'csv') return []
      return COND_OPTIONS[type] || COND_OPTIONS.text
    },
    condNeedsValue() {
      return Boolean(this.condOp) && !['blank', 'not_blank'].includes(this.condOp)
    },
    rows() {
      const rows = []
      if (this.column?.type !== 'date') {
        for (const item of this.items) {
          rows.push({
            id: `v:${item.value}`,
            value: item.value,
            label: item.label || this.labelOf(item.value),
            count: item.count,
            hint: item.hint || '',
          })
        }
        return rows
      }
      const groups = new Map()
      const blanks = []
      for (const item of this.items) {
        if (item.value === '') {
          blanks.push(item)
          continue
        }
        const month = String(item.value).slice(0, 7)
        if (!groups.has(month)) groups.set(month, [])
        groups.get(month).push(item)
      }
      for (const [month, list] of groups) {
        rows.push({
          id: `g:${month}`,
          group: month,
          label: month.replace('-', ' 年 ') + ' 月',
          count: list.reduce((sum, item) => sum + item.count, 0),
        })
        if (this.expanded.has(month) || this.searching) {
          for (const item of list) {
            rows.push({ id: `v:${item.value}`, value: item.value, label: item.value, count: item.count, child: true })
          }
        }
      }
      for (const item of blanks) {
        rows.push({ id: 'v:', value: '', label: BLANK_LABEL, count: item.count })
      }
      return rows
    },
    allChecked() {
      if (!this.searching) return this.baseAll && this.exceptions.size === 0
      return this.items.length > 0 && this.items.every((item) => this.isChecked(item.value))
    },
    someChecked() {
      if (!this.searching) return this.baseAll || this.exceptions.size > 0
      return this.items.some((item) => this.isChecked(item.value))
    },
  },
  watch: {
    visible: {
      handler(open) {
        if (open) this.init()
        this.toggleScrollFollow(open)
      },
    },
    'column.key'() {
      if (this.visible) this.init()
    },
  },
  created() {
    this.valuesRequest = createLatestRequest()
  },
  mounted() {
    document.addEventListener('mousedown', this.onDocumentMouseDown, true)
    document.addEventListener('contextmenu', this.onDocumentContextMenu, true)
    window.addEventListener('resize', this.close)
    document.addEventListener('keydown', this.onKeydown)
  },
  beforeUnmount() {
    clearTimeout(this.searchTimer)
    this.toggleScrollFollow(false)
    document.removeEventListener('mousedown', this.onDocumentMouseDown, true)
    document.removeEventListener('contextmenu', this.onDocumentContextMenu, true)
    window.removeEventListener('resize', this.close)
    document.removeEventListener('keydown', this.onKeydown)
  },
  methods: {
    labelOf(value) {
      return value === '' ? BLANK_LABEL : String(value)
    },
    close() {
      if (this.visible) this.$emit('close')
    },
    onKeydown(event) {
      if (event.key === 'Escape') this.close()
    },
    // Excel 视图的 vxe 在 document 上听键盘（Delete 清格子、方向键移格），菜单里的按键不能漏出去。
    onPanelKeydown(event) {
      event.stopPropagation()
      if (event.key === 'Escape') this.close()
    },
    toggleScrollFollow(on) {
      cancelAnimationFrame(this.followFrame)
      if (on) window.addEventListener('scroll', this.onAnyScroll, { capture: true, passive: true })
      else window.removeEventListener('scroll', this.onAnyScroll, { capture: true })
    },
    onAnyScroll(event) {
      const target = event.target
      if (target instanceof Element && (this.$refs.panel?.contains(target) || target.closest('.wb-hm-popper'))) return
      cancelAnimationFrame(this.followFrame)
      this.followFrame = requestAnimationFrame(this.follow)
    },
    /** 表头随页面或表格滚动时跟着走；表头滚出可视区就关闭。 */
    follow() {
      const anchor = this.anchor
      if (!this.visible || !anchor) return
      const rect = anchor.getBoundingClientRect?.()
      const box = anchor.closest?.('.el-table, .vxe-table')?.getBoundingClientRect()
      const gone = !anchor.isConnected
        || !rect
        || rect.width === 0
        || rect.bottom < 0
        || rect.top > window.innerHeight
        || (box && (rect.right < box.left + 8 || rect.left > box.right - 8))
      if (gone) this.close()
      else this.place()
    },
    isInsideMenu(target) {
      return this.$refs.panel?.contains(target) || target?.closest?.('.wb-hm-popper, .el-picker__popper, .el-select__popper')
    },
    // 右键交给 contextmenu 处理：mousedown 时就关掉的话，到 contextmenu 已判断不出要不要拦浏览器菜单。
    onDocumentMouseDown(event) {
      if (!this.visible || event.button === 2) return
      const target = event.target
      if (this.isInsideMenu(target) || this.anchor?.contains?.(target)) return
      this.close()
    },
    /** 菜单开着时右键任意表头（含自己那列）只收起菜单，不弹浏览器菜单。 */
    onDocumentContextMenu(event) {
      if (!this.visible || this.isInsideMenu(event.target)) return
      if (event.target?.closest?.('.wb-hf-cell')) event.preventDefault()
      this.close()
    },
    place() {
      const rect = this.anchor?.getBoundingClientRect?.()
      if (!rect) return
      const maxLeft = window.innerWidth - PANEL_WIDTH - 8
      const top = Math.min(rect.bottom + 2, window.innerHeight - 260)
      this.position = {
        left: Math.max(8, Math.min(rect.left, maxLeft)),
        top: Math.max(8, top),
        maxHeight: Math.max(240, window.innerHeight - Math.max(8, top) - 8),
      }
    },
    init() {
      clearTimeout(this.searchTimer)
      this.zIndex = this.nextZIndex()
      this.search = ''
      this.activeKeyword = ''
      this.expanded = new Set()
      this.searchUnchecked = new Set()
      const filter = this.filter || {}
      if (Array.isArray(filter.values)) {
        this.baseAll = false
        this.exceptions = new Set(filter.values)
      } else {
        this.baseAll = true
        this.exceptions = new Set(filter.exclude || [])
      }
      this.condOp = filter.condition?.op || ''
      this.condValue = filter.condition?.value ?? ''
      this.condValue2 = filter.condition?.value2 ?? ''
      this.colors = [...(filter.colors || [])]
      this.items = []
      this.baseItems = []
      this.baseTruncated = false
      this.truncated = false
      this.loadError = false
      this.place()
      if (this.valueMode !== 'search' && !this.column.sortOnly) this.fetchValues()
    },
    requestOptions(keyword) {
      if (this.valueMode !== 'all') return { keyword, limit: RECENT_LIMIT, order: 'recent' }
      return { keyword, limit: ALL_LIMIT, order: this.column.type === 'date' ? 'value_desc' : 'value' }
    },
    setKeyword(keyword) {
      if (keyword !== this.activeKeyword) this.searchUnchecked = new Set()
      this.activeKeyword = keyword
    },
    async fetchValues() {
      const keyword = this.search.trim()
      if (this.localSearch && this.baseItems.length) {
        this.valuesRequest.cancel()
        this.loading = false
        this.items = keyword ? this.filterLocal(keyword) : this.baseItems
        this.truncated = false
        this.setKeyword(keyword)
        return
      }
      if (!keyword && this.valueMode === 'search') {
        this.valuesRequest.cancel()
        this.loading = false
        this.items = []
        this.truncated = false
        this.setKeyword('')
        return
      }
      const isLatest = this.valuesRequest.begin()
      this.loading = true
      this.loadError = false
      try {
        const data = await this.loadValues(this.column.key, this.requestOptions(keyword))
        if (!isLatest()) return
        this.items = data?.items || []
        this.truncated = Boolean(data?.truncated)
        if (!keyword) {
          this.baseItems = this.items
          this.baseTruncated = this.truncated
        }
        this.setKeyword(keyword)
      } catch {
        if (isLatest()) {
          this.items = []
          this.loadError = true
        }
      } finally {
        if (isLatest()) this.loading = false
      }
      this.$nextTick(this.place)
    },
    filterLocal(keyword) {
      if (this.searchValues) return this.searchValues(this.baseItems, keyword)
      const text = keyword.toLowerCase()
      return this.baseItems.filter((item) => item.value !== '' && String(item.value).toLowerCase().includes(text))
    },
    scheduleSearch() {
      clearTimeout(this.searchTimer)
      if (this.localSearch && this.baseItems.length) {
        this.fetchValues()
        return
      }
      this.searchTimer = window.setTimeout(this.fetchValues, SEARCH_DEBOUNCE)
    },
    isChecked(value) {
      if (this.searching) return !this.searchUnchecked.has(value)
      return this.baseAll !== this.exceptions.has(value)
    },
    toggleColor(key) {
      const idx = this.colors.indexOf(key)
      if (idx >= 0) this.colors.splice(idx, 1)
      else this.colors.push(key)
    },
    toggleValue(value, on) {
      if (this.searching) {
        const next = new Set(this.searchUnchecked)
        if (on) next.delete(value)
        else next.add(value)
        this.searchUnchecked = next
        return
      }
      const next = new Set(this.exceptions)
      if (on === this.baseAll) next.delete(value)
      else next.add(value)
      this.exceptions = next
    },
    toggleAll(on) {
      if (this.searching) {
        this.searchUnchecked = on ? new Set() : new Set(this.items.map((item) => item.value))
        return
      }
      this.baseAll = on
      this.exceptions = new Set()
    },
    toggleGroup(month) {
      const next = new Set(this.expanded)
      if (next.has(month)) next.delete(month)
      else next.add(month)
      this.expanded = next
    },
    groupValues(month) {
      return this.items.filter((item) => item.value && String(item.value).startsWith(month)).map((item) => item.value)
    },
    groupState(month) {
      const values = this.groupValues(month)
      const hit = values.filter((v) => this.isChecked(v)).length
      if (!hit) return 'none'
      return hit === values.length ? 'all' : 'some'
    },
    toggleGroupChecked(month, on) {
      for (const value of this.groupValues(month)) this.toggleValue(value, on)
    },
    applyQuick(op) {
      this.$emit('apply', this.buildState({ op, ignoreValues: true }))
    },
    valueSelection() {
      if (this.loadError) {
        const { values, exclude } = this.filter || {}
        return { ...(values && { values }), ...(exclude && { exclude }) }
      }
      if (this.searching) {
        const checked = this.items.map((item) => item.value).filter((v) => this.isChecked(v))
        const serverSearched = this.truncated || !this.localSearch
        if (serverSearched && checked.length && checked.length === this.items.length) {
          return { condition: { op: 'contains', value: this.activeKeyword } }
        }
        return { values: checked }
      }
      if (this.baseAll) return this.exceptions.size ? { exclude: [...this.exceptions] } : {}
      return { values: [...this.exceptions] }
    },
    buildState({ op = this.condOp, ignoreValues = false } = {}) {
      const state = ignoreValues ? {} : this.valueSelection()
      const needsValue = op && !['blank', 'not_blank'].includes(op)
      const value = this.condValue ?? ''
      const value2 = this.condValue2 ?? ''
      if (op && (!needsValue || String(value).trim() || String(value2).trim())) {
        state.condition = needsValue
          ? { op, value, value2: op === 'between' ? value2 : '' }
          : { op }
      }
      if (this.colors.length) state.colors = [...this.colors]
      return Object.keys(state).length ? state : null
    },
    async confirm() {
      if (this.search.trim() !== this.activeKeyword) {
        clearTimeout(this.searchTimer)
        await this.fetchValues()
      }
      if (this.selectsNothing) return
      this.$emit('apply', this.buildState())
    },
  },
}
</script>

<style>
.wb-hm {
  position: fixed;
  display: flex;
  flex-direction: column;
  max-height: min(620px, calc(100vh - 24px));
  padding: 6px 0 8px;
  overflow: hidden;
  color: var(--el-text-color-regular);
  font-size: 12.5px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  box-shadow: 0 10px 28px rgb(15 23 42 / 16%);
}

.wb-hm-fade-enter-active,
.wb-hm-fade-leave-active {
  transition: opacity 0.12s ease, transform 0.12s ease;
}

.wb-hm-fade-enter-from,
.wb-hm-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.wb-hm-sort,
.wb-hm-sec {
  display: flex;
  flex-direction: column;
  padding: 2px 6px 6px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.wb-hm-sec {
  padding-top: 6px;
}

.wb-hm-sec-hd {
  padding: 0 6px 4px;
  color: var(--el-text-color-secondary);
  font-size: 11.5px;
}

.wb-hm-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 5px 6px;
  color: inherit;
  font-size: 12.5px;
  text-align: left;
  background: transparent;
  border: 0;
  border-radius: 4px;
  cursor: pointer;
}

.wb-hm-item:hover:not(:disabled) {
  background: var(--el-fill-color-light);
}

.wb-hm-item:disabled {
  color: var(--el-text-color-disabled);
  cursor: default;
}

.wb-hm-item.is-active {
  color: var(--el-color-primary);
  font-weight: 650;
  background: var(--el-color-primary-light-9);
}

.wb-hm-item.is-muted {
  color: var(--el-text-color-secondary);
}

.wb-hm-icon {
  display: inline-flex;
  justify-content: center;
  width: 14px;
  font-weight: 700;
}

.wb-hm-colors {
  display: flex;
  gap: 6px;
  padding: 0 6px;
}

.wb-hm-color {
  width: 18px;
  height: 18px;
  padding: 0;
  background: var(--swatch);
  border: 2px solid var(--el-bg-color);
  border-radius: 50%;
  box-shadow: 0 0 0 1px var(--el-border-color);
  cursor: pointer;
}

.wb-hm-color.is-none {
  border: 1px dashed #94a3b8;
  box-shadow: none;
}

.wb-hm-color.is-active {
  box-shadow: 0 0 0 2px var(--el-color-primary);
}

.wb-hm-quick {
  display: flex;
  gap: 6px;
  padding: 4px 6px 2px;
}

.wb-hm-chip {
  padding: 2px 10px;
  color: var(--el-text-color-regular);
  font-size: 12px;
  background: var(--el-fill-color-lighter);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 999px;
  cursor: pointer;
}

.wb-hm-chip:hover,
.wb-hm-chip.is-active {
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary-light-5);
}

.wb-hm-cond {
  display: flex;
  gap: 6px;
  align-items: center;
  padding: 6px 6px 0;
}

.wb-hm-cond-op {
  flex: 0 0 104px;
  width: 104px;
}

.wb-hm-cond-to {
  color: var(--el-text-color-secondary);
  text-align: right;
}

.wb-hm-cond-val {
  flex: 1;
  min-width: 0;
}

.wb-hm-cond-val.el-date-editor.el-input {
  width: 100%;
}

.wb-hm-sort,
.wb-hm-sec,
.wb-hm-external,
.wb-hm-foot {
  flex-shrink: 0;
}

.wb-hm-values {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  padding: 8px 12px 0;
}

.wb-hm-list {
  flex: 1 1 auto;
  min-height: 60px;
  max-height: 240px;
  margin-top: 6px;
  padding: 2px 0;
  overflow: auto;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
}

.wb-hm-row {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 26px;
  padding: 0 8px;
  cursor: pointer;
}

.wb-hm-row:hover {
  background: var(--el-fill-color-light);
}

.wb-hm-row .el-checkbox {
  height: 20px;
  margin-right: 0;
}

.wb-hm-row.is-child {
  padding-left: 34px;
}

.wb-hm-row.is-all {
  font-weight: 600;
}

.wb-hm-fold {
  width: 14px;
  padding: 0;
  color: var(--el-text-color-secondary);
  background: transparent;
  border: 0;
  cursor: pointer;
}

.wb-hm-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.wb-hm-text.is-blank {
  color: var(--el-text-color-secondary);
  font-style: italic;
}

.wb-hm-hint {
  margin-left: 6px;
  color: var(--el-text-color-placeholder);
  font-size: 11px;
}

.wb-hm-count {
  color: var(--el-text-color-placeholder);
  font-size: 11.5px;
}

.wb-hm-empty {
  padding: 6px 10px;
  color: var(--el-text-color-placeholder);
  font-size: 12px;
}

.wb-hm-empty.is-error {
  color: var(--el-color-danger);
}

.wb-hm-retry {
  margin-left: 8px;
  padding: 0;
  color: var(--el-color-primary);
  font-size: 12px;
  background: transparent;
  border: 0;
  cursor: pointer;
}

.wb-hm-external {
  display: flex;
  gap: 8px;
  align-items: center;
  margin: 8px 12px 0;
  padding: 4px 8px;
  color: var(--el-color-warning-dark-2);
  font-size: 12px;
  background: var(--el-color-warning-light-9);
  border-radius: 4px;
}

.wb-hm-external span {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.wb-hm-external button {
  padding: 0;
  color: var(--el-color-primary);
  font-size: 12px;
  background: transparent;
  border: 0;
  cursor: pointer;
}

.wb-hm-foot {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
  padding: 10px 12px 0;
}

.is-header-filtered .el-select__wrapper,
.is-header-filtered.el-input .el-input__wrapper,
.el-date-editor.is-header-filtered {
  box-shadow: 0 0 0 1px var(--el-color-primary) inset;
}

.is-header-filtered .el-select__placeholder,
.is-header-filtered input::placeholder {
  color: var(--el-color-primary);
}

.wb-hf-chip {
  display: inline-flex;
  flex-shrink: 0;
  gap: 4px;
  align-items: center;
  height: 28px;
  padding: 0 10px;
  color: var(--el-color-primary);
  font-size: 12px;
  white-space: nowrap;
  background: var(--el-color-primary-light-9);
  border: 1px solid var(--el-color-primary-light-5);
  border-radius: 999px;
  cursor: pointer;
}

.wb-hf-chip:hover {
  background: var(--el-color-primary-light-8);
}

.wb-hf-chip-x {
  font-size: 14px;
  line-height: 1;
}

.wb-hf-label {
  display: inline-flex;
  gap: 3px;
  align-items: center;
  justify-content: center;
  max-width: 100%;
  white-space: nowrap;
}

.wb-hf-label.is-active {
  color: var(--el-color-primary);
  font-weight: 650;
}

.wb-hf-mark {
  font-size: 11px;
  font-style: normal;
  line-height: 1;
}

.wb-hf-caret {
  color: var(--el-text-color-placeholder);
  font-size: 10px;
  font-style: normal;
  opacity: 0;
  transition: opacity 0.12s ease;
}

th.wb-hf-cell,
.vxe-header--column.wb-hf-cell {
  cursor: pointer;
}

/* el-table 调列宽只给 body 设 col-resize，表头自身的光标会把它盖住。
   只点名带光标的表头元素：写 * 会让 body 每次改 style 都重算整页样式。 */
body[style*="col-resize"] th.wb-hf-cell,
body[style*="col-resize"] th.el-table__cell .wb-col-hd {
  cursor: col-resize;
}

th.wb-hf-cell:hover,
.vxe-header--column.wb-hf-cell:hover,
th.wb-hf-cell.is-open,
.vxe-header--column.wb-hf-cell.is-open {
  background-color: var(--el-fill-color) !important;
}

th.wb-hf-cell:hover .wb-hf-caret,
.vxe-header--column.wb-hf-cell:hover .wb-hf-caret,
th.wb-hf-cell.is-open .wb-hf-caret,
.vxe-header--column.wb-hf-cell.is-open .wb-hf-caret {
  opacity: 1;
}
</style>
