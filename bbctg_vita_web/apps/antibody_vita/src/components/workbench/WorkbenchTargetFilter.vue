<template>
  <ListFilterSelect
    :model-value="modelValue"
    class="workbench-target-filter"
    clearable
    filterable
    :filter-method="onFilter"
    :loading="loading"
    :placeholder="placeholder"
    v-bind="$attrs"
    @update:model-value="$emit('update:modelValue', $event)"
    @change="$emit('change', $event)"
    @clear="onFilter('')"
    @visible-change="onVisible"
  >
    <el-option
      v-for="item in displayed"
      :key="item.value"
      :label="item.label"
      :value="item.value"
    >
      <span>{{ item.label }}</span>
      <span v-if="extra(item)" class="target-option-code">{{ extra(item) }}</span>
    </el-option>
  </ListFilterSelect>
</template>

<script>
import { defineComponent } from 'vue'
import { ElOption } from 'element-plus'
import { fetchRecordedTargets, RECORDED_TARGET_ENDPOINTS } from '#/api/options'
import ListFilterSelect from '#/components/ListFilterSelect.vue'
import { createLatestRequest } from '#/utils/latestRequest'
import { normalizeTargetOptions, targetOptionExtra } from '#/utils/targetFilterOptions'

const SEARCH_DEBOUNCE_MS = 250

export default defineComponent({
  name: 'WorkbenchTargetFilter',
  components: { ListFilterSelect, ElOption },
  inheritAttrs: false,
  props: {
    modelValue: { type: [String, Array], default: '' },
    placeholder: { type: String, default: '靶点' },
    /** 本表已录入靶点的搜索接口，见 RECORDED_TARGET_ENDPOINTS */
    scope: {
      type: String,
      required: true,
      validator: (value) => Object.prototype.hasOwnProperty.call(RECORDED_TARGET_ENDPOINTS, value),
    },
  },
  emits: ['update:modelValue', 'change'],
  data() {
    return {
      loading: false,
      query: '',
      loadedKeyword: '',
      remote: [],
      remembered: {},
      searchTimer: 0,
    }
  },
  computed: {
    selectedValues() {
      if (Array.isArray(this.modelValue)) {
        return this.modelValue.map((item) => String(item || '').trim()).filter(Boolean)
      }
      const text = String(this.modelValue || '').trim()
      return text ? [text] : []
    },
    displayed() {
      const selected = this.selectedValues.map((value) => (
        this.remembered[value]
        || { value, label: value, aliases: [], codes: [] }
      ))
      const seen = new Set(selected.map((item) => item.value))
      return [...selected, ...this.remote.filter((item) => !seen.has(item.value))]
    },
  },
  created() {
    this.searchRequest = createLatestRequest()
  },
  beforeUnmount() {
    clearTimeout(this.searchTimer)
  },
  methods: {
    extra(item) {
      return targetOptionExtra(item, this.query)
    },
    onFilter(value) {
      this.query = String(value || '')
      clearTimeout(this.searchTimer)
      this.loading = true
      this.searchTimer = setTimeout(() => this.load(this.query), this.query ? SEARCH_DEBOUNCE_MS : 0)
    },
    async load(keyword) {
      const isLatest = this.searchRequest.begin()
      try {
        const items = normalizeTargetOptions(await fetchRecordedTargets(this.scope, keyword))
        if (!isLatest()) return
        this.remote = items
        this.loadedKeyword = keyword
        items.forEach((item) => {
          this.remembered[item.value] = item
        })
      } catch {
        if (isLatest()) this.remote = []
      } finally {
        if (isLatest()) this.loading = false
      }
    },
    onVisible(visible) {
      if (!visible) {
        this.query = ''
        return
      }
      if (!this.remote.length || this.loadedKeyword) this.onFilter('')
    },
  },
})
</script>

<style scoped>
.target-option-code {
  margin-left: 8px;
  color: #909399;
  font-size: 12px;
}
</style>
