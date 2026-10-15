<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'

import { fetchFileBlob } from '#/utils/file-resource'

const props = defineProps({
  sourceUrl: { type: String, required: true },
  direction: { type: String, default: '' },
  primerLabel: { type: String, default: '' },
  targetSequence: { type: String, default: '' },
  height: { type: String, default: '100%' },
})

const ARM_BY_DIRECTION = {
  F: ['ACCGAGATCTACAC', 'ACACTCTTTCC'],
  R: ['AACTCCAGTCAC', 'ATCTCGTATGCC'],
}

const textContent = ref('')
const loading = ref(false)
const errorMessage = ref('')
const searchQuery = ref('')
const searchMatches = ref([])
const activeMatchIndex = ref(-1)
const searchKind = ref('manual')
const armViewIndex = ref(0)
const textBody = ref(null)
let requestVersion = 0
let controller = null

const directionInfo = computed(() => {
  const primer = props.primerLabel ? ` · ${props.primerLabel}` : ''
  if (props.direction === 'F') return { label: `正向 M13F${primer}`, arrow: '→', tone: 'forward' }
  if (props.direction === 'R') return { label: `反向 M13R${primer}`, arrow: '←', tone: 'reverse' }
  return { label: '方向未识别', arrow: '↔', tone: 'unknown' }
})

const searchSummary = computed(() => {
  if (searchKind.value === 'arm') {
    const view = armViews(props.direction)[armViewIndex.value]
    if (!view) return '未找到同源臂'
    const found = new Set(searchMatches.value.map((match) => match.term))
    if (view.terms.length > 1) {
      const present = view.terms
        .map((term, index) => (found.has(term) ? ['左臂', '右臂'][index] : ''))
        .filter(Boolean)
      if (!present.length) return '两侧 未找到'
      if (present.length < view.terms.length) return `两侧只找到${present.join('、')}`
      return `两侧 ${searchMatches.value.length} 处`
    }
    return searchMatches.value.length
      ? `${view.label} ${searchMatches.value.length} 处`
      : `${view.label} 未找到`
  }
  if (!normalizeSequence(searchQuery.value)) return ''
  if (!searchMatches.value.length) return '未找到'
  return `找到 ${activeMatchIndex.value + 1}/${searchMatches.value.length}`
})

const highlightedRanges = computed(() => {
  if (searchKind.value === 'arm') return searchMatches.value
  const current = searchMatches.value[activeMatchIndex.value]
  return current ? [current] : []
})

const textParts = computed(() => {
  const text = textContent.value
  const ranges = [...highlightedRanges.value]
    .filter((range) => range.start >= 0 && range.end > range.start && range.end <= text.length)
    .sort((left, right) => left.start - right.start || right.end - left.end)
  if (!text) return []
  if (!ranges.length) return [{ text, mark: false }]
  const parts = []
  let cursor = 0
  ranges.forEach((range) => {
    if (range.start < cursor) return
    if (range.start > cursor) parts.push({ text: text.slice(cursor, range.start), mark: false })
    parts.push({ text: text.slice(range.start, range.end), mark: true })
    cursor = range.end
  })
  if (cursor < text.length) parts.push({ text: text.slice(cursor), mark: false })
  return parts
})

function normalizeSequence(value) {
  return String(value || '').toUpperCase().replace(/[^ACGTN]/g, '')
}

function armViews(direction) {
  const terms = ARM_BY_DIRECTION[direction] || []
  if (terms.length < 2) return []
  return [
    { label: '左臂', terms: [terms[0]] },
    { label: '右臂', terms: [terms[1]] },
    { label: '两侧', terms },
  ]
}

function baseOffsets(text) {
  const offsets = []
  let lineStart = true
  let skipLine = false
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index]
    if (lineStart) {
      skipLine = char === '>'
      lineStart = false
    }
    if (char === '\n' || char === '\r') {
      lineStart = true
      skipLine = false
      continue
    }
    if (skipLine || /\s|\d/.test(char) || !/[ACGTNacgtn]/.test(char)) continue
    offsets.push(index)
  }
  return offsets
}

function findTermRanges(text, term) {
  const needle = normalizeSequence(term)
  if (!needle) return []
  const offsets = baseOffsets(text)
  const haystack = offsets.map((index) => text[index].toUpperCase()).join('')
  const ranges = []
  let offset = haystack.indexOf(needle)
  while (offset >= 0) {
    ranges.push({
      start: offsets[offset],
      end: offsets[offset + needle.length - 1] + 1,
      term: needle,
    })
    offset = haystack.indexOf(needle, offset + 1)
  }
  return ranges
}

function scrollToMark() {
  nextTick(() => {
    textBody.value?.querySelector('mark')?.scrollIntoView({ block: 'center', inline: 'nearest' })
  })
}

function showRanges(ranges, kind, query) {
  searchKind.value = kind
  searchMatches.value = ranges
  activeMatchIndex.value = ranges.length ? 0 : -1
  searchQuery.value = query
  scrollToMark()
}

function stepMatch(step) {
  if (searchKind.value === 'arm') {
    showArmView(armViewIndex.value + step)
    return
  }
  if (searchMatches.value.length < 2) return
  activeMatchIndex.value = (
    activeMatchIndex.value + step + searchMatches.value.length
  ) % searchMatches.value.length
  scrollToMark()
}

function showArmView(index) {
  const views = armViews(props.direction)
  if (!views.length) return
  const next = (index + views.length) % views.length
  const view = views[next]
  const ranges = view.terms.flatMap((term) => findTermRanges(textContent.value, term))
  ranges.sort((left, right) => left.start - right.start || right.end - left.end)
  armViewIndex.value = next
  showRanges(ranges, 'arm', view.terms.length === 1 ? view.terms[0] : '')
}

function searchArms() {
  if (searchKind.value === 'arm') {
    armViewIndex.value = 0
    runSearch(normalizeSequence(props.targetSequence), 'primer')
    return
  }
  showArmView(0)
}

function runSearch(term, kind = 'manual') {
  const needle = normalizeSequence(term)
  searchQuery.value = needle
  if (!needle) {
    showRanges([], 'manual', '')
    return
  }
  showRanges(findTermRanges(textContent.value, needle), kind, needle)
}

async function loadText() {
  const version = ++requestVersion
  controller?.abort()
  controller = new AbortController()
  textContent.value = ''
  errorMessage.value = ''
  searchMatches.value = []
  if (!props.sourceUrl) return
  loading.value = true
  try {
    const blob = await fetchFileBlob(props.sourceUrl, { signal: controller.signal })
    const text = await blob.text()
    if (version !== requestVersion) return
    const limit = 200_000
    textContent.value = text.length > limit ? text.slice(0, limit) : text
    runSearch(props.targetSequence, props.targetSequence ? 'primer' : 'manual')
  } catch (error) {
    if (error?.name === 'AbortError' || version !== requestVersion) return
    errorMessage.value = error?.message || '序列预览失败'
  } finally {
    if (version === requestVersion) loading.value = false
  }
}

watch(() => props.sourceUrl, loadText, { immediate: true })
watch(
  () => props.targetSequence,
  (value) => {
    if (!textContent.value) return
    armViewIndex.value = 0
    runSearch(value, value ? 'primer' : 'manual')
  },
)
onBeforeUnmount(() => {
  requestVersion += 1
  controller?.abort()
})
</script>

<template>
  <section v-loading="loading" class="seq-read-preview" :style="{ height }">
    <p v-if="errorMessage" class="seq-state is-error">{{ errorMessage }}</p>
    <template v-else>
      <header class="seq-head">
        <button
          v-if="direction === 'F' || direction === 'R'"
          type="button"
          class="direction-badge"
          :class="[`is-${directionInfo.tone}`, { 'is-arm': searchKind === 'arm' }]"
          :title="searchKind === 'arm' ? '回到完整引物' : '查找同源臂。上一个、下一个可切换左臂、右臂和两侧'"
          @click="searchArms"
        >
          <b>{{ directionInfo.arrow }}</b>
          {{ directionInfo.label }}
        </button>
        <span v-else class="direction-badge" :class="`is-${directionInfo.tone}`">
          <b>{{ directionInfo.arrow }}</b>
          {{ directionInfo.label }}
        </span>
      </header>
      <div class="seq-search">
        <input
          v-model="searchQuery"
          maxlength="120"
          placeholder="输入一段序列（A/C/G/T/N）"
          @keydown.enter.prevent="runSearch(searchQuery, 'manual')"
        >
        <button type="button" @click="runSearch(searchQuery, 'manual')">查找</button>
        <button
          type="button"
          :disabled="searchKind !== 'arm' && searchMatches.length < 2"
          @click="stepMatch(-1)"
        >
          上一个
        </button>
        <button
          type="button"
          :disabled="searchKind !== 'arm' && searchMatches.length < 2"
          @click="stepMatch(1)"
        >
          下一个
        </button>
        <span
          :class="{
            'is-found': searchMatches.length && !String(searchSummary).includes('只找到'),
            'is-primer': searchKind === 'primer',
            'is-empty': searchSummary && (!searchMatches.length || String(searchSummary).includes('只找到')),
          }"
        >
          {{ searchSummary }}
        </span>
      </div>
      <div ref="textBody" class="seq-text">
        <pre><template v-for="(part, index) in textParts" :key="index"><mark v-if="part.mark">{{ part.text }}</mark><template v-else>{{ part.text }}</template></template></pre>
      </div>
    </template>
  </section>
</template>

<style scoped>
.seq-read-preview {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  background: #fff;
}

.seq-state {
  align-self: center;
  margin: auto;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.seq-state.is-error {
  color: var(--el-color-danger);
}

.seq-head,
.seq-search {
  display: flex;
  flex: none;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  min-height: 34px;
  padding: 4px 12px;
  color: var(--el-text-color-secondary);
  font-size: 11px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.direction-badge {
  display: inline-flex;
  gap: 5px;
  align-items: center;
  padding: 2px 7px;
  color: var(--el-text-color-regular);
  font: inherit;
  background: var(--el-fill-color-light);
  border: 0;
  border-radius: 999px;
}

button.direction-badge {
  cursor: pointer;
}

button.direction-badge:hover,
button.direction-badge.is-arm {
  background: var(--el-color-primary-light-9);
}

.direction-badge b {
  font-size: 14px;
}

.direction-badge.is-forward b {
  color: var(--el-color-success);
}

.direction-badge.is-reverse b {
  color: var(--el-color-primary);
}

.seq-search input {
  flex: 1 1 180px;
  width: auto;
  min-width: 70px;
  height: 24px;
  padding: 0 8px;
  color: var(--el-text-color-regular);
  font: 11px Consolas, Monaco, monospace;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  outline: none;
}

.seq-search button {
  flex: none;
  height: 24px;
  padding: 0 8px;
  color: var(--el-text-color-regular);
  font-size: 11px;
  background: #fff;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  cursor: pointer;
}

.seq-search button:disabled {
  color: var(--el-text-color-placeholder);
  cursor: not-allowed;
  background: var(--el-fill-color-light);
}

.seq-search .is-found {
  color: var(--el-color-success);
}

.seq-search .is-primer {
  color: var(--el-color-primary);
}

.seq-search .is-empty {
  color: var(--el-color-danger);
}

.seq-text {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.seq-text pre {
  min-height: 100%;
  margin: 0;
  padding: 16px;
  color: var(--el-text-color-primary);
  font-family: Consolas, Monaco, monospace;
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.seq-text mark {
  padding: 1px 0;
  color: #7a4b00;
  background: var(--el-color-warning-light-7);
  border-radius: 2px;
}
</style>
