<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'

import { fetchFileJson } from '#/utils/file-resource'

import AbiTraceViewer from './AbiTraceViewer.vue'

const props = defineProps({
  sourceUrl: { type: String, required: true },
  direction: { type: String, default: '' },
  primerLabel: { type: String, default: '' },
  targetSequence: { type: String, default: '' },
  height: { type: String, default: '100%' },
})

const trace = ref(null)
const loading = ref(false)
const errorMessage = ref('')
let requestVersion = 0
let controller = null

async function loadTrace() {
  const version = ++requestVersion
  controller?.abort()
  controller = new AbortController()
  trace.value = null
  errorMessage.value = ''
  if (!props.sourceUrl) return

  loading.value = true
  try {
    const result = await fetchFileJson(props.sourceUrl, {
      signal: controller.signal,
    })
    if (version === requestVersion) trace.value = result
  } catch (error) {
    if (error?.name === 'AbortError' || version !== requestVersion) return
    errorMessage.value = error?.message || '峰图预览失败'
  } finally {
    if (version === requestVersion) loading.value = false
  }
}

watch(() => props.sourceUrl, loadTrace, { immediate: true })

onBeforeUnmount(() => {
  requestVersion += 1
  controller?.abort()
})
</script>

<template>
  <section v-loading="loading" class="abi-trace-preview" :style="{ height }">
    <p v-if="errorMessage" class="preview-state is-error">{{ errorMessage }}</p>
    <AbiTraceViewer
      v-else-if="trace"
      :trace="trace"
      :direction="direction"
      :primer-label="primerLabel"
      :target-sequence="targetSequence"
      height="100%"
    />
  </section>
</template>

<style scoped>
.abi-trace-preview {
  display: flex;
  flex: 1;
  min-width: 0;
  min-height: 0;
}

.abi-trace-preview > :deep(.abi-trace-viewer) {
  flex: 1;
}

.preview-state {
  align-self: center;
  width: 100%;
  margin: 0;
  padding: 20px;
  color: var(--el-color-danger);
  font-size: 13px;
  text-align: center;
}
</style>
