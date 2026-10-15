<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import { fetchFileBlob } from '#/utils/file-resource'

const props = defineProps({
  sourceUrl: { type: String, default: '' },
  fileName: { type: String, default: '' },
  mimeType: { type: String, default: '' },
  height: { type: String, default: '100%' },
})

const emit = defineEmits(['loading-change'])

const loading = ref(false)
const errorMessage = ref('')
const objectUrl = ref('')
const playbackError = ref(false)
const textContent = ref('')
const tableRows = ref([])
const previewNote = ref('')
let requestVersion = 0
let controller = null

const extension = computed(() => {
  const name = String(props.fileName || '').toLowerCase()
  return name.includes('.') ? name.split('.').pop() : ''
})

const kind = computed(() => {
  const ext = extension.value
  if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'].includes(ext)
    || String(props.mimeType || '').startsWith('image/')) return 'image'
  if (['seq', 'txt', 'fa', 'fasta', 'md', 'log'].includes(ext)) return 'text'
  if (['xls', 'xlsx', 'csv'].includes(ext)) return 'sheet'
  if (ext === 'pdf') return 'pdf'
  if (ext === 'docx') return 'docx'
  if (['mp4', 'webm', 'ogg', 'ogv', 'mov'].includes(ext)
    || String(props.mimeType || '').startsWith('video/')) return 'video'
  return 'unsupported'
})

const videoType = computed(() => {
  const types = {
    mp4: 'video/mp4',
    webm: 'video/webm',
    ogg: 'video/ogg',
    ogv: 'video/ogg',
    mov: 'video/quicktime',
  }
  return types[extension.value] || (String(props.mimeType || '').startsWith('video/') ? props.mimeType : '')
})

function clearObjectUrl() {
  if (objectUrl.value) URL.revokeObjectURL(objectUrl.value)
  objectUrl.value = ''
}

function resetPreview() {
  clearObjectUrl()
  playbackError.value = false
  errorMessage.value = ''
  textContent.value = ''
  tableRows.value = []
  previewNote.value = ''
}

async function loadPreview() {
  const version = ++requestVersion
  controller?.abort()
  controller = new AbortController()
  resetPreview()
  if (!props.sourceUrl || kind.value === 'unsupported') {
    loading.value = false
    emit('loading-change', false)
    return
  }

  loading.value = true
  emit('loading-change', true)
  try {
    const blob = await fetchFileBlob(props.sourceUrl, {
      signal: controller.signal,
    })
    if (version !== requestVersion) return

    if (kind.value === 'image' || kind.value === 'pdf') {
      objectUrl.value = URL.createObjectURL(blob)
      return
    }
    if (kind.value === 'video') {
      const type = blob.type?.startsWith('video/') ? blob.type : videoType.value
      objectUrl.value = URL.createObjectURL(type ? new Blob([blob], { type }) : blob)
      return
    }
    if (kind.value === 'text') {
      const text = await blob.text()
      if (version !== requestVersion) return
      const limit = 200_000
      textContent.value = text.length > limit
        ? `${text.slice(0, limit)}\n\n……内容过长，仅显示前 ${limit.toLocaleString()} 个字符`
        : text
      return
    }
    const arrayBuffer = await blob.arrayBuffer()
    if (version !== requestVersion) return
    if (kind.value === 'sheet') {
      const XLSX = await import('xlsx')
      if (version !== requestVersion) return
      const workbook = XLSX.read(arrayBuffer, { type: 'array' })
      const sheet = workbook.Sheets[workbook.SheetNames[0]]
      const rows = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: '' })
      tableRows.value = rows.slice(0, 200).map((row) => row.slice(0, 24))
      if (rows.length > 200 || rows.some((row) => row.length > 24)) {
        previewNote.value = '表格内容较大，仅显示首个工作表的前 200 行、24 列'
      }
      return
    }
    if (kind.value === 'docx') {
      const mammoth = await import('mammoth/mammoth.browser.js')
      if (version !== requestVersion) return
      const result = await mammoth.extractRawText({ arrayBuffer })
      if (version !== requestVersion) return
      const text = result.value || ''
      const limit = 200_000
      textContent.value = text.length > limit
        ? `${text.slice(0, limit)}\n\n……内容过长，仅显示前 ${limit.toLocaleString()} 个字符`
        : text
      previewNote.value = text.length > limit
        ? 'DOCX 文本预览，复杂排版已简化；内容已截断'
        : 'DOCX 文本预览，复杂排版已简化'
    }
  } catch (error) {
    if (error?.name === 'AbortError' || version !== requestVersion) return
    errorMessage.value = error?.message || '文件预览失败'
  } finally {
    if (version === requestVersion) {
      loading.value = false
      emit('loading-change', false)
    }
  }
}

watch(
  () => [props.sourceUrl, props.fileName, props.mimeType],
  loadPreview,
  { immediate: true },
)

onBeforeUnmount(() => {
  requestVersion += 1
  controller?.abort()
  clearObjectUrl()
})
</script>

<template>
  <section v-loading="loading" class="file-previewer" :style="{ height }">
    <p v-if="errorMessage" class="preview-state is-error">{{ errorMessage }}</p>
    <p v-else-if="kind === 'unsupported'" class="preview-state">
      该格式暂不支持直接预览，可以下载查看。
    </p>
    <img
      v-else-if="kind === 'image' && objectUrl"
      class="preview-image"
      :src="objectUrl"
      :alt="fileName"
    />
    <video
      v-else-if="kind === 'video' && objectUrl && !playbackError"
      class="preview-video"
      :src="objectUrl"
      controls
      preload="metadata"
      @error="playbackError = true"
    />
    <p v-else-if="kind === 'video' && playbackError" class="preview-state">
      这个视频当前浏览器无法播放，可以下载查看。
    </p>
    <iframe
      v-else-if="kind === 'pdf' && objectUrl"
      class="preview-pdf"
      :src="objectUrl"
      :title="fileName"
    />
    <div v-else-if="kind === 'sheet' && tableRows.length" class="preview-sheet">
      <small v-if="previewNote">{{ previewNote }}</small>
      <table>
        <tbody>
          <tr v-for="(row, rowIndex) in tableRows" :key="rowIndex">
            <td v-for="(cell, colIndex) in row" :key="colIndex">{{ cell }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else-if="['text', 'docx'].includes(kind) && textContent" class="preview-text">
      <small v-if="previewNote">{{ previewNote }}</small>
      <pre>{{ textContent }}</pre>
    </div>
    <p v-else-if="!loading" class="preview-state">这个文件读不出可预览内容。</p>
  </section>
</template>

<style scoped>
.file-previewer {
  display: flex;
  flex: 1;
  align-items: stretch;
  justify-content: center;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  background: var(--el-bg-color);
}

.preview-state {
  align-self: center;
  margin: 0;
  padding: 20px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  text-align: center;
}

.preview-state.is-error {
  color: var(--el-color-danger);
}

.preview-image,
.preview-video {
  max-width: 100%;
  max-height: 100%;
  margin: auto;
}

.preview-image {
  object-fit: contain;
}

.preview-video {
  background: #111;
}

.preview-pdf {
  width: 100%;
  height: 100%;
  border: 0;
}

.preview-text,
.preview-sheet {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow: auto;
}

.preview-text small,
.preview-sheet small {
  display: block;
  padding: 7px 12px;
  color: var(--el-text-color-secondary);
  font-size: 11px;
  background: var(--el-fill-color-light);
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.preview-text pre {
  min-height: 100%;
  margin: 0;
  padding: 16px;
  color: var(--el-text-color-primary);
  font-family: Consolas, 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.preview-sheet table {
  min-width: 100%;
  border-collapse: collapse;
  background: var(--el-bg-color);
}

.preview-sheet td {
  max-width: 260px;
  padding: 7px 10px;
  overflow: hidden;
  color: var(--el-text-color-regular);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
  border: 1px solid var(--el-border-color-lighter);
}
</style>
