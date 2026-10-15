<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { EchartsUI, useEcharts } from '@vben/plugins/echarts'

const props = defineProps({
  trace: {
    type: Object,
    required: true,
  },
  height: {
    type: String,
    default: '430px',
  },
  direction: {
    type: String,
    default: '',
  },
  primerLabel: {
    type: String,
    default: '',
  },
  targetSequence: {
    type: String,
    default: '',
  },
})

const COLORS = {
  A: '#16a05d',
  C: '#2f6feb',
  G: '#374151',
  T: '#e5484d',
}

const chartRef = ref()
const sequenceLayer = ref(null)
const { renderEcharts } = useEcharts(chartRef)
const baseCount = computed(() => props.trace?.bases?.length || 0)
const sequenceMarks = ref([])
const searchQuery = ref('')
const searchMatches = ref([])
const activeMatchIndex = ref(-1)
const activeMatchRange = ref(null)
const searchKind = ref('manual')
const armViewIndex = ref(0)
let activeChart = null
let resizeObserver = null
let resizeFrame = 0
let lastSearchTerm = ''

const ARM_BY_DIRECTION = {
  F: ['ACCGAGATCTACAC', 'ACACTCTTTCC'],
  R: ['AACTCCAGTCAC', 'ATCTCGTATGCC'],
}

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

const directionInfo = computed(() => {
  const primer = props.primerLabel ? ` · ${props.primerLabel}` : ''
  if (props.direction === 'F') {
    return { label: `正向 M13F${primer}`, arrow: '→', tone: 'forward' }
  }
  if (props.direction === 'R') {
    return { label: `反向 M13R${primer}`, arrow: '←', tone: 'reverse' }
  }
  return { label: '方向未识别', arrow: '↔', tone: 'unknown' }
})

function nearestBaseIndex(sample) {
  const bases = props.trace?.bases || []
  if (!bases.length) return -1
  let low = 0
  let high = bases.length - 1
  while (low <= high) {
    const middle = Math.floor((low + high) / 2)
    if (bases[middle].position < sample) low = middle + 1
    else high = middle - 1
  }
  const right = bases[Math.min(low, bases.length - 1)]
  const left = bases[Math.max(0, low - 1)]
  if (!right) return Math.max(0, low - 1)
  if (!left) return Math.min(low, bases.length - 1)
  return Math.abs(right.position - sample) < Math.abs(left.position - sample)
    ? Math.min(low, bases.length - 1)
    : Math.max(0, low - 1)
}

function normalizeSequence(value) {
  return String(value || '').toUpperCase().replace(/[^ACGTN]/g, '')
}

function armTerms(direction) {
  return ARM_BY_DIRECTION[direction] || []
}

function armViews(direction) {
  const terms = armTerms(direction)
  if (terms.length < 2) return []
  return [
    { label: '左臂', terms: [terms[0]] },
    { label: '右臂', terms: [terms[1]] },
    { label: '两侧', terms },
  ]
}

function highlightedMatches() {
  if (searchKind.value === 'arm') return searchMatches.value
  return activeMatchRange.value ? [activeMatchRange.value] : []
}

function calledSequence() {
  return (props.trace?.bases || [])
    .map((item) => {
      const base = String(item.base || '').toUpperCase()
      return /^[ACGTN]$/.test(base) ? base : 'N'
    })
    .join('')
}

function baseSampleSpacing() {
  const bases = props.trace?.bases || []
  const gaps = []
  for (let index = 1; index < bases.length; index += 1) {
    const gap = Number(bases[index].position) - Number(bases[index - 1].position)
    if (Number.isFinite(gap) && gap > 0) gaps.push(gap)
  }
  if (!gaps.length) return 12
  gaps.sort((left, right) => left - right)
  return gaps[Math.floor((gaps.length - 1) * 0.2)] || 12
}

function readableSampleSpan() {
  const sampleMax = Math.max((props.trace?.sample_count || 1) - 1, 1)
  const width = sequenceLayer.value?.clientWidth
    || activeChart?.getDom()?.clientWidth
    || 600
  const usableWidth = Math.max(width - 36, 120)
  const visibleBaseCount = Math.max(8, Math.floor(usableWidth / 14))
  return Math.min(sampleMax, Math.max(baseSampleSpacing() * visibleBaseCount, 1))
}

function tooltipText(params) {
  const rows = Array.isArray(params) ? params : [params]
  const sample = Number(rows[0]?.axisValue ?? rows[0]?.value?.[0] ?? 0)
  const baseIndex = nearestBaseIndex(sample)
  const base = props.trace?.bases?.[baseIndex]
  const traceRows = rows
    .filter((item) => COLORS[item.seriesName])
    .map((item) => `${item.marker}${item.seriesName}：${Math.round(item.value?.[1] ?? 0)}`)
    .join('<br>')
  const baseText = base
    ? `<strong style="color:${COLORS[base.base] || '#606266'}">${base.base}</strong>`
      + ` · 碱基 ${baseIndex + 1}`
      + (base.quality == null ? '' : ` · Q${base.quality}`)
    : '—'
  return `${baseText}<br><span style="color:#909399">峰位 ${sample}</span><br>${traceRows}`
}

function zoomRange() {
  const zoom = activeChart?.getOption()?.dataZoom?.[0] || {}
  const sampleMax = Math.max((props.trace?.sample_count || 1) - 1, 1)
  const startValue = Number(zoom.startValue)
  const endValue = Number(zoom.endValue)
  const start = Number.isFinite(startValue)
    ? startValue
    : sampleMax * (Number(zoom.start) || 0) / 100
  const end = Number.isFinite(endValue)
    ? endValue
    : sampleMax * (Number(zoom.end) || 100) / 100
  return { start, end, sampleMax }
}

function chartOptions() {
  const trace = props.trace
  const signalMax = Math.max(Number(trace.signal_max) || 1, 1)
  const maxVisibleSpan = readableSampleSpan()
  const initialSpan = Math.min(
    Math.max(Number(trace.initial_window) || maxVisibleSpan, 1),
    maxVisibleSpan,
  )
  const lineSeries = Object.keys(COLORS).map((base) => ({
    id: `trace-${base}`,
    name: base,
    type: 'line',
    data: (trace.channels?.[base] || []).map((value, index) => [
      index,
      Math.min(Number(value) || 0, signalMax),
    ]),
    showSymbol: false,
    animation: false,
    lineStyle: {
      color: COLORS[base],
      width: 1.35,
    },
    emphasis: {
      disabled: true,
    },
  }))
  const highlightSeries = {
    id: 'match-highlight',
    type: 'line',
    data: [[0, 0], [Math.max((trace.sample_count || 1) - 1, 1), 0]],
    showSymbol: false,
    silent: true,
    tooltip: { show: false },
    lineStyle: { opacity: 0 },
    markArea: {
      silent: true,
      itemStyle: {
        color: 'rgba(230, 162, 60, 0.16)',
      },
      data: [],
    },
  }

  return {
    animation: false,
    color: Object.values(COLORS),
    grid: {
      top: 48,
      right: 18,
      bottom: 62,
      left: 18,
      containLabel: false,
    },
    legend: {
      top: 8,
      left: 14,
      itemWidth: 18,
      itemHeight: 3,
      selectedMode: true,
      data: Object.keys(COLORS),
      textStyle: {
        fontSize: 12,
      },
    },
    tooltip: {
      trigger: 'axis',
      confine: true,
      transitionDuration: 0,
      axisPointer: {
        type: 'line',
        snap: false,
        lineStyle: {
          color: '#a8abb2',
          type: 'dashed',
        },
      },
      formatter: tooltipText,
    },
    xAxis: {
      type: 'value',
      min: 0,
      max: Math.max((trace.sample_count || 1) - 1, 1),
      axisLine: {
        lineStyle: {
          color: '#dcdfe6',
        },
      },
      axisTick: {
        show: false,
      },
      axisLabel: {
        color: '#909399',
        fontSize: 10,
        formatter: (value) => {
          const index = nearestBaseIndex(Number(value))
          return index < 0 ? '' : index + 1
        },
      },
      splitLine: {
        show: false,
      },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: signalMax * 1.18,
      show: false,
      splitNumber: 4,
      splitLine: {
        show: true,
        lineStyle: {
          color: '#ebeef5',
        },
      },
    },
    dataZoom: [
      {
        id: 'inside-zoom',
        type: 'inside',
        xAxisIndex: 0,
        startValue: 0,
        endValue: initialSpan,
        maxValueSpan: maxVisibleSpan,
        filterMode: 'none',
        zoomOnMouseWheel: true,
        moveOnMouseMove: true,
        moveOnMouseWheel: false,
        preventDefaultMouseMove: true,
      },
      {
        id: 'slider-zoom',
        type: 'slider',
        xAxisIndex: 0,
        startValue: 0,
        endValue: initialSpan,
        maxValueSpan: maxVisibleSpan,
        filterMode: 'none',
        height: 18,
        bottom: 14,
        borderColor: '#dcdfe6',
        backgroundColor: '#f5f7fa',
        fillerColor: 'rgba(64, 158, 255, 0.16)',
        handleStyle: {
          color: '#409eff',
          borderColor: '#409eff',
        },
        moveHandleStyle: {
          color: '#79bbff',
        },
        showDetail: false,
        brushSelect: false,
      },
    ],
    series: [...lineSeries, highlightSeries],
  }
}

function syncSequenceMarks() {
  if (!activeChart || !sequenceLayer.value) {
    sequenceMarks.value = []
    return
  }
  const chartWidth = activeChart.getDom()?.clientWidth || 0
  const layerWidth = sequenceLayer.value.clientWidth || 0
  const width = chartWidth || layerWidth
  if (width <= 0) {
    sequenceMarks.value = []
    return
  }
  const { start, end } = zoomRange()
  const visible = (props.trace?.bases || [])
    .map((item, index) => ({ ...item, index: index + 1 }))
    .filter((item) => item.position >= start && item.position <= end)
  if (!visible.length) {
    sequenceMarks.value = []
    return
  }
  const ranges = highlightedMatches()
  sequenceMarks.value = visible.flatMap((item) => {
    const point = activeChart.convertToPixel({ xAxisIndex: 0, yAxisIndex: 0 }, [item.position, 0])
    if (!Array.isArray(point)) return []
    const x = point[0]
    if (!Number.isFinite(x) || x < -12 || x > width + 12) return []
    return [{
      key: `${item.index}-${item.position}`,
      base: item.base,
      index: item.index,
      quality: item.quality,
      matched: ranges.some((match) => item.index - 1 >= match.start && item.index - 1 < match.end),
      left: `${(x / width) * 100}%`,
      color: COLORS[item.base] || '#606266',
    }]
  })
}

function matchSampleRange(match) {
  const bases = props.trace?.bases || []
  const first = bases[match.start]
  const last = bases[match.end - 1]
  if (!first || !last) return null
  const spacing = baseSampleSpacing()
  const previous = bases[match.start - 1]
  const next = bases[match.end]
  return {
    start: previous
      ? (Number(previous.position) + Number(first.position)) / 2
      : Math.max(0, Number(first.position) - spacing / 2),
    end: next
      ? (Number(last.position) + Number(next.position)) / 2
      : Math.min((props.trace?.sample_count || 1) - 1, Number(last.position) + spacing / 2),
  }
}

function renderMatchHighlight() {
  if (!activeChart) return
  const areas = highlightedMatches()
    .map((match) => matchSampleRange(match))
    .filter(Boolean)
    .map((range) => [{ xAxis: range.start }, { xAxis: range.end }])
  activeChart.setOption({
    series: [{
      id: 'match-highlight',
      markArea: {
        silent: true,
        itemStyle: {
          color: 'rgba(230, 162, 60, 0.16)',
        },
        data: areas,
      },
    }],
  })
  syncSequenceMarks()
}

function focusMatch(match) {
  if (!activeChart) return
  const range = matchSampleRange(match)
  if (!range) return
  const sampleMax = Math.max((props.trace?.sample_count || 1) - 1, 1)
  const maxSpan = readableSampleSpan()
  const matchSpan = Math.max(range.end - range.start, baseSampleSpacing())
  const windowSpan = Math.min(
    maxSpan,
    Math.max(matchSpan + baseSampleSpacing() * 8, maxSpan * 0.55),
  )
  const center = (range.start + range.end) / 2
  const start = Math.max(0, Math.min(center - windowSpan / 2, sampleMax - windowSpan))
  activeChart.dispatchAction({
    type: 'dataZoom',
    dataZoomId: 'inside-zoom',
    startValue: start,
    endValue: Math.min(sampleMax, start + windowSpan),
  })
}

function focusMatches(matches) {
  if (!matches.length) return
  if (matches.length === 1) {
    focusMatch(matches[0])
    return
  }
  const ranges = matches.map((match) => matchSampleRange(match)).filter(Boolean)
  if (!ranges.length || !activeChart) return
  const sampleMax = Math.max((props.trace?.sample_count || 1) - 1, 1)
  const maxSpan = readableSampleSpan()
  const start = Math.min(...ranges.map((range) => range.start))
  const end = Math.max(...ranges.map((range) => range.end))
  if (end - start > maxSpan) {
    focusMatch(matches[0])
    return
  }
  const pad = baseSampleSpacing() * 4
  const windowSpan = Math.min(maxSpan, Math.max(end - start + pad * 2, baseSampleSpacing() * 20))
  const center = (start + end) / 2
  const zoomStart = Math.max(0, Math.min(center - windowSpan / 2, sampleMax - windowSpan))
  activeChart.dispatchAction({
    type: 'dataZoom',
    dataZoomId: 'inside-zoom',
    startValue: zoomStart,
    endValue: Math.min(sampleMax, zoomStart + windowSpan),
  })
}

function collectArmMatches(terms) {
  const sequence = calledSequence()
  const matches = []
  terms.forEach((term) => {
    let offset = sequence.indexOf(term)
    while (offset >= 0) {
      matches.push({ start: offset, end: offset + term.length, term })
      offset = sequence.indexOf(term, offset + 1)
    }
  })
  matches.sort((left, right) => left.start - right.start || right.end - left.end)
  return matches
}

function showArmView(index) {
  const views = armViews(props.direction)
  if (!views.length) return
  const next = (index + views.length) % views.length
  const view = views[next]
  const matches = collectArmMatches(view.terms)
  armViewIndex.value = next
  searchKind.value = 'arm'
  searchMatches.value = matches
  activeMatchIndex.value = matches.length ? 0 : -1
  activeMatchRange.value = matches[0] || null
  lastSearchTerm = '\0arm'
  searchQuery.value = view.terms.length === 1 ? view.terms[0] : ''
  renderMatchHighlight()
  focusMatches(matches)
}

function searchArms() {
  if (searchKind.value === 'arm') {
    armViewIndex.value = 0
    searchQuery.value = normalizeSequence(props.targetSequence)
    lastSearchTerm = ''
    runSearch(0, props.targetSequence ? 'primer' : 'manual')
    return
  }
  showArmView(0)
}

function runSearch(step = 0, kind = 'manual') {
  if (kind === 'arm' && step) {
    showArmView(armViewIndex.value + step)
    return
  }
  const term = normalizeSequence(searchQuery.value)
  searchQuery.value = term
  searchKind.value = kind
  if (!term) {
    lastSearchTerm = ''
    searchMatches.value = []
    activeMatchIndex.value = -1
    activeMatchRange.value = null
    renderMatchHighlight()
    return
  }
  if (term !== lastSearchTerm) {
    const sequence = calledSequence()
    const matches = []
    let offset = sequence.indexOf(term)
    while (offset >= 0) {
      matches.push({ start: offset, end: offset + term.length })
      offset = sequence.indexOf(term, offset + 1)
    }
    lastSearchTerm = term
    searchMatches.value = matches
    activeMatchIndex.value = matches.length ? 0 : -1
  } else if (searchMatches.value.length && step) {
    activeMatchIndex.value = (
      activeMatchIndex.value + step + searchMatches.value.length
    ) % searchMatches.value.length
  }
  activeMatchRange.value = searchMatches.value[activeMatchIndex.value] || null
  renderMatchHighlight()
  if (activeMatchRange.value) focusMatch(activeMatchRange.value)
}

function updateZoomLimit() {
  if (!activeChart) return
  const maxSpan = readableSampleSpan()
  activeChart.setOption({
    dataZoom: [
      { id: 'inside-zoom', maxValueSpan: maxSpan },
      { id: 'slider-zoom', maxValueSpan: maxSpan },
    ],
  })
  const { start, end, sampleMax } = zoomRange()
  if (end - start > maxSpan) {
    const center = (start + end) / 2
    const nextStart = Math.max(0, Math.min(center - maxSpan / 2, sampleMax - maxSpan))
    activeChart.dispatchAction({
      type: 'dataZoom',
      dataZoomId: 'inside-zoom',
      startValue: nextStart,
      endValue: Math.min(sampleMax, nextStart + maxSpan),
    })
  }
  syncSequenceMarks()
}

function onViewerResize() {
  cancelAnimationFrame(resizeFrame)
  resizeFrame = requestAnimationFrame(() => {
    activeChart?.resize()
    updateZoomLimit()
  })
}

async function draw() {
  if (!props.trace) return
  activeChart = await renderEcharts(chartOptions())
  if (!activeChart) return
  activeChart.off('datazoom', syncSequenceMarks)
  activeChart.off('finished', syncSequenceMarks)
  activeChart.on('datazoom', syncSequenceMarks)
  activeChart.on('finished', syncSequenceMarks)
  await nextTick()
  lastSearchTerm = ''
  runSearch(
    0,
    normalizeSequence(searchQuery.value) === normalizeSequence(props.targetSequence)
      ? 'primer'
      : 'manual',
  )
}

onMounted(() => {
  resizeObserver = new ResizeObserver(onViewerResize)
  if (sequenceLayer.value) resizeObserver.observe(sequenceLayer.value)
  draw()
})
watch(() => props.trace, draw)
watch(
  () => props.targetSequence,
  (value) => {
    searchQuery.value = normalizeSequence(value)
    lastSearchTerm = ''
    if (activeChart) runSearch(0, 'primer')
  },
  { immediate: true },
)
onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  cancelAnimationFrame(resizeFrame)
  activeChart?.off('datazoom', syncSequenceMarks)
  activeChart?.off('finished', syncSequenceMarks)
  activeChart = null
})
</script>

<template>
  <div class="abi-trace-viewer" :style="{ height }">
    <header class="trace-head">
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
      <span>{{ baseCount }} bp · 滚轮缩放 · 拖动平移</span>
    </header>
    <div class="trace-search">
      <input
        v-model="searchQuery"
        maxlength="120"
        placeholder="输入一段序列（A/C/G/T/N）"
        @keydown.enter.prevent="runSearch(0, 'manual')"
      >
      <button type="button" @click="runSearch(0, 'manual')">查找</button>
      <button
        type="button"
        :disabled="searchKind !== 'arm' && searchMatches.length < 2"
        @click="runSearch(-1, searchKind)"
      >
        上一个
      </button>
      <button
        type="button"
        :disabled="searchKind !== 'arm' && searchMatches.length < 2"
        @click="runSearch(1, searchKind)"
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
    <div ref="sequenceLayer" class="sequence-layer" aria-label="与峰图对齐的序列">
      <span
        v-for="item in sequenceMarks"
        v-show="item.index === 1 || item.index % 10 === 0"
        :key="`scale-${item.key}`"
        class="sequence-scale-mark"
        :style="{ left: item.left }"
      >
        {{ item.index }}
      </span>
      <span
        v-for="item in sequenceMarks"
        :key="`base-${item.key}`"
        class="sequence-base-mark"
        :class="{
          'is-low-quality': item.quality != null && item.quality < 20,
          'is-match': item.matched,
        }"
        :style="{ left: item.left, color: item.color }"
        :title="`碱基 ${item.index}${item.quality == null ? '' : ` · Q${item.quality}`}`"
      >
        <b>{{ item.base }}</b>
      </span>
    </div>
    <div class="trace-chart">
      <EchartsUI ref="chartRef" height="100%" />
    </div>
  </div>
</template>

<style scoped>
.abi-trace-viewer {
  position: relative;
  display: flex;
  flex-direction: column;
  width: 100%;
  min-width: 0;
  overflow: hidden;
  background: #fff;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}

.trace-head {
  display: flex;
  flex: none;
  align-items: center;
  justify-content: space-between;
  min-height: 34px;
  padding: 6px 12px;
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

.trace-search {
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

.trace-search input {
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

.trace-search input::placeholder {
  color: var(--el-text-color-placeholder);
}

.trace-search input:focus {
  border-color: var(--el-color-primary);
}

.trace-search button {
  flex: none;
  height: 24px;
  padding: 0 8px;
  color: var(--el-text-color-regular);
  font-size: 11px;
  background: #fff;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  cursor: pointer;
  white-space: nowrap;
}

.trace-search button:disabled {
  color: var(--el-text-color-placeholder);
  cursor: not-allowed;
  background: var(--el-fill-color-light);
}

.trace-search .is-empty {
  color: var(--el-color-danger);
}

.trace-search .is-found {
  color: var(--el-color-success);
}

.trace-search .is-primer {
  color: var(--el-color-primary);
}

.trace-search .is-primer.is-empty {
  color: var(--el-color-danger);
}

.trace-search span {
  flex: none;
  white-space: nowrap;
}

.sequence-layer {
  position: relative;
  flex: none;
  height: 38px;
  overflow: hidden;
  background: var(--el-fill-color-extra-light);
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.sequence-scale-mark,
.sequence-base-mark {
  position: absolute;
  text-align: center;
  white-space: nowrap;
  transform: translateX(-50%);
  pointer-events: none;
}

.sequence-scale-mark {
  top: 2px;
  color: var(--el-text-color-placeholder);
  font: 8px/10px Arial, sans-serif;
}

.sequence-base-mark {
  top: 16px;
  font-family: Consolas, Monaco, monospace;
}

.sequence-base-mark b {
  font-size: 12px;
  line-height: 16px;
}

.sequence-base-mark.is-low-quality b {
  padding: 0 1px;
  background: var(--el-color-warning-light-8);
  border-radius: 2px;
}

.sequence-base-mark.is-match b {
  padding: 1px 2px;
  color: #7a4b00;
  background: var(--el-color-warning-light-7);
  border: 1px solid var(--el-color-warning);
  border-radius: 3px;
}

.trace-chart {
  flex: 1;
  min-height: 0;
}

.abi-trace-viewer :deep(canvas) {
  cursor: grab;
}
</style>
