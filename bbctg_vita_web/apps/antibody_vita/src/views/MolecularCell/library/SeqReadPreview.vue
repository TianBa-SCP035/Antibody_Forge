<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'

import { fetchFileBlob } from '#/utils/file-resource'

import {
  SEARCH_STEPS,
  complementQueryText,
  matchCount,
  matchSpans,
  normalizeSequence,
  MIN_CHECK_BASES,
  openingSearch,
  pairSearch,
  readDirectionInfo,
  searchSummaryText,
  searchTarget,
  viewForStep,
} from './primerSearch'

const props = defineProps({
  sourceUrl: { type: String, required: true },
  direction: { type: String, default: '' },
  sequenceStatus: { type: String, default: '' },
  targetSequence: { type: String, default: '' },
  height: { type: String, default: '100%' },
})

const textContent = ref('')
const loading = ref(false)
const errorMessage = ref('')
const searchQuery = ref('')
const complementOn = ref(false)
const searchMatches = ref([])
const activeMatchIndex = ref(-1)
const searchKind = ref('manual')
const searchStep = ref(0)
const armViewIndex = ref(0)
const textBody = ref(null)
let requestVersion = 0
let controller = null

const sequenceText = computed(() => {
  const text = textContent.value
  return baseOffsets(text).map((index) => text[index]).join('')
})
const baseCount = computed(() => sequenceText.value.length)
const lengthIsShort = computed(() => baseCount.value <= MIN_CHECK_BASES)

const directionInfo = computed(() => readDirectionInfo(
  props.direction,
  props.sequenceStatus,
  textContent.value,
  props.targetSequence,
))

const searchSummary = computed(() => searchSummaryText(
  searchKind.value,
  armViewIndex.value,
  searchMatches.value.length,
  activeMatchIndex.value,
  searchQuery.value,
))

const canStep = computed(() => matchCount(
  searchMatches.value.length,
  pairSearch(searchKind.value, armViewIndex.value),
) >= 2)

const highlightedRanges = computed(() => matchSpans(
  searchMatches.value,
  activeMatchIndex.value,
  pairSearch(searchKind.value, armViewIndex.value),
))

const textParts = computed(() => {
  const text = sequenceText.value
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
    parts.push({
      text: text.slice(range.start, range.end),
      mark: true,
      active: true,
    })
    cursor = range.end
  })
  if (cursor < text.length) parts.push({ text: text.slice(cursor), mark: false })
  return parts
})

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
  const haystack = text.toUpperCase()
  const ranges = []
  let offset = haystack.indexOf(needle)
  while (offset >= 0) {
    ranges.push({
      start: offset,
      end: offset + needle.length,
      term: needle,
    })
    offset = haystack.indexOf(needle, offset + 1)
  }
  return ranges
}

function findFlankRanges(text, left, right) {
  const haystack = text.toUpperCase()
  const ranges = []
  let from = 0
  while (from <= haystack.length) {
    const leftAt = haystack.indexOf(left, from)
    if (leftAt < 0) break
    const rightAt = haystack.indexOf(right, leftAt + left.length)
    if (rightAt < 0) break
    ranges.push({ start: leftAt, end: leftAt + left.length })
    ranges.push({ start: rightAt, end: rightAt + right.length })
    from = rightAt + right.length
  }
  return ranges
}

function scrollToMark() {
  nextTick(() => {
    const root = textBody.value
    const active = root?.querySelector('mark.is-active') || root?.querySelector('mark')
    active?.scrollIntoView({ block: 'center', inline: 'nearest' })
  })
}

function applySearch(kind = 'manual') {
  const target = searchTarget(searchQuery.value, false)
  searchKind.value = target.flank && kind !== 'arm' ? 'flank' : kind
  const ranges = target.flank
    ? findFlankRanges(sequenceText.value, target.left, target.right)
    : (target.term ? findTermRanges(sequenceText.value, target.term) : [])
  searchMatches.value = ranges
  activeMatchIndex.value = ranges.length ? 0 : -1
  scrollToMark()
}

function showStep(step) {
  const view = viewForStep(step, props.direction, props.targetSequence)
  searchStep.value = view.stepIndex
  armViewIndex.value = view.armIndex
  searchQuery.value = complementOn.value ? complementQueryText(view.query) : view.query
  applySearch(view.kind)
}

function applyOpening() {
  const opening = openingSearch(
    props.sequenceStatus,
    props.direction,
    textContent.value,
    props.targetSequence,
  )
  complementOn.value = opening.complement
  showStep(opening.step)
}

function stepMatch(step) {
  const paired = pairSearch(searchKind.value, armViewIndex.value)
  const count = matchCount(searchMatches.value.length, paired)
  if (count < 2) return
  const current = Math.floor(activeMatchIndex.value / (paired ? 2 : 1))
  activeMatchIndex.value = ((current + step + count) % count) * (paired ? 2 : 1)
  scrollToMark()
}

function cycleSearch() {
  showStep(SEARCH_STEPS[(searchStep.value + 1) % SEARCH_STEPS.length])
}

function toggleComplement() {
  if (!normalizeSequence(searchQuery.value)) return
  complementOn.value = !complementOn.value
  searchQuery.value = complementQueryText(searchQuery.value)
  applySearch(searchKind.value)
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
    applyOpening()
  } catch (error) {
    if (error?.name === 'AbortError' || version !== requestVersion) return
    errorMessage.value = error?.message || '序列预览失败'
  } finally {
    if (version === requestVersion) loading.value = false
  }
}

watch(() => props.sourceUrl, loadText, { immediate: true })
watch(
  () => [props.targetSequence, props.sequenceStatus, props.direction],
  () => {
    if (!textContent.value) return
    applyOpening()
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
          title="点击切换：完整引物、两侧同源臂、左臂、右臂"
          @click="cycleSearch"
        >
          <b v-if="directionInfo.arrow">{{ directionInfo.arrow }}</b>
          {{ directionInfo.label }}
        </button>
        <span v-else class="direction-badge" :class="`is-${directionInfo.tone}`">
          <b v-if="directionInfo.arrow">{{ directionInfo.arrow }}</b>
          {{ directionInfo.label }}
        </span>
        <span v-if="!loading" class="read-length" :class="{ 'is-short': lengthIsShort }">{{ baseCount }} bp</span>
      </header>
      <div class="seq-search">
        <input
          v-model="searchQuery"
          maxlength="120"
          placeholder="输入一段序列（A/C/G/T/N）"
          @keydown.enter.prevent="applySearch('manual')"
        >
        <button type="button" @click="applySearch('manual')">查找</button>
        <button
          type="button"
          title="按下后搜索框换成反向互补，再按一次换回"
          :class="{ 'is-on': complementOn }"
          :aria-pressed="complementOn"
          :disabled="!normalizeSequence(searchQuery)"
          @click="toggleComplement"
        >
          反补
        </button>
        <button
          type="button"
          :disabled="!canStep"
          @click="stepMatch(-1)"
        >
          上一个
        </button>
        <button
          type="button"
          :disabled="!canStep"
          @click="stepMatch(1)"
        >
          下一个
        </button>
        <span
          :class="{
            'is-found': searchMatches.length,
            'is-primer': searchKind === 'primer',
            'is-empty': searchSummary && !searchMatches.length,
          }"
        >
          {{ searchSummary }}
        </span>
      </div>
      <div ref="textBody" class="seq-text">
        <pre><template v-for="(part, index) in textParts" :key="index"><mark v-if="part.mark" :class="{ 'is-active': part.active }">{{ part.text }}</mark><template v-else>{{ part.text }}</template></template></pre>
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

.read-length {
  margin-left: auto;
}

.read-length.is-short {
  color: var(--el-color-danger);
  font-weight: 600;
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

.seq-search button.is-on {
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary-light-5);
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
  width: 100%;
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

.seq-text mark.is-active {
  background: var(--el-color-warning-light-5);
}
</style>
