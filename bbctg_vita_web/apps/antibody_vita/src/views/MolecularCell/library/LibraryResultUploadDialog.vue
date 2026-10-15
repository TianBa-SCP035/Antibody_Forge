<template>
  <el-dialog
    :model-value="modelValue"
    :title="hasResult ? '上传结果' : '批量质检上传'"
    width="min(860px, calc(100vw - 32px))"
    append-to-body
    :close-on-click-modal="!uploading"
    :close-on-press-escape="!uploading"
    :show-close="!uploading"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <div class="batch-layout">
      <section class="batch-source">
        <button
          type="button"
          class="batch-pick"
          :class="{ 'is-over': dragOver }"
          :disabled="uploading"
          @click="pickFiles"
          @contextmenu.prevent.stop="pickFolder"
          @dragenter.prevent="dragOver = true"
          @dragover.prevent="dragOver = true"
          @dragleave.self.prevent="dragOver = false"
          @drop.prevent="onDrop"
        >
          <el-icon><UploadFilled /></el-icon>
          <strong>上传结果文件</strong>
          <span>拖入文件或文件夹</span>
          <small>标准测序包须同时包含“测序结果”“拼接结果”“去载体序列”。zip 会自动展开，右键可选已解开的文件夹</small>
        </button>
        <input ref="fileInput" class="batch-file-input" type="file" multiple @change="onFilePick" />
        <input ref="folderInput" class="batch-file-input" type="file" webkitdirectory multiple @change="onFolderPick" />
      </section>

      <section class="batch-review">
        <header>
          <strong>{{ report.length ? '上传结果' : uploading ? '正在上传' : checking ? '正在检查' : '待上传内容' }}</strong>
          <el-button v-if="selected.length && !uploading" text size="small" @click="clearSelection">清空</el-button>
          <span v-else>{{ cards.length }} 组</span>
        </header>
        <div v-if="!cards.length" class="batch-empty">选择后在这里核对</div>
        <div v-else class="batch-card-list">
          <article v-for="(card, index) in cards" :key="`${card.key}-${index}`" class="batch-pack">
            <header>
              <strong>{{ card.title }}</strong>
              <span>{{ card.headline }}</span>
            </header>
            <div v-if="card.lines.length" class="batch-table">
              <div class="batch-line is-head">
                <span>编号</span>
                <span>结果</span>
                <span>说明</span>
                <span>文件</span>
              </div>
              <div v-for="(line, lineIndex) in card.lines" :key="`${line.code}-${lineIndex}`" class="batch-line" :class="line.tone">
                <button v-if="line.orderId" type="button" class="batch-code-link" @click="openOrder(line.orderId)">{{ line.code }}</button>
                <b v-else>{{ line.code }}</b>
                <em>{{ line.result }}</em>
                <small>{{ line.note }}</small>
                <span class="batch-count">
                  <template v-if="line.count !== ''">
                    <b>{{ line.count }}</b>
                    <i>个</i>
                  </template>
                </span>
              </div>
            </div>
            <p v-for="(note, noteIndex) in card.notes" :key="`note-${noteIndex}`" class="batch-note">{{ note }}</p>
            <p v-for="(warning, warningIndex) in card.warnings" :key="`warn-${warningIndex}`" class="batch-note is-warn">{{ warning }}</p>
          </article>
        </div>
      </section>
    </div>

    <template #footer>
      <el-button :disabled="uploading" @click="$emit('update:modelValue', false)">关闭</el-button>
      <el-button v-if="hasResult" type="primary" @click="clearSelection">清空</el-button>
      <el-button v-else type="primary" :loading="uploading || checking" :disabled="!uploadableRows.length" @click="submit">
        上传 {{ uploadableRows.length ? `(${uploadableRows.length})` : '' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script>
import { UploadFilled } from '@element-plus/icons-vue'
import { ElButton, ElDialog, ElIcon, ElMessage } from 'element-plus'

import { preflightLibraryFileBatch, uploadLibraryFileBatch } from '#/api/molecularLibrary'
import { notifyApiError } from '#/api/errors'
import { expandResultArchives, readDroppedFiles, resultUploadLimitError } from './readDroppedFiles'

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function uniqueCodes(codes) {
  return [...new Set((codes || []).map((code) => String(code || '').trim()).filter(Boolean))]
}

function splitIssues(issues) {
  const unmatched = []
  let ignoredDirectory = false
  const warnings = []
  ;(issues || []).forEach((issue) => {
    const reason = String(issue?.reason || '').trim()
    const count = Number(issue?.count || 0)
    if (!reason) return
    const missingOrder = reason.match(/^建库编号 (.+) 还没有对应工单$/)
    if (missingOrder) {
      unmatched.push({ code: missingOrder[1], count: count || 1 })
      return
    }
    if (reason.startsWith('忽略其他子目录：')) {
      ignoredDirectory = true
      return
    }
    warnings.push(count > 1 ? `${reason} · ${count} 个` : reason)
  })
  return { unmatched, ignoredDirectory, warnings }
}

function qcTone(status) {
  if (status === '质检通过' || status === '已完成') return 'is-pass'
  if (status === '质检不通过') return 'is-fail'
  if (status === '质检待确认') return 'is-warn'
  return ''
}

function qcChecks(orders) {
  return (orders || [])
    .map((row) => ({
      orderId: Number(row?.id) || 0,
      code: String(row?.library_code || '').trim(),
      status: String(row?.status || '').trim(),
      detail: String(row?.detail || '').trim(),
      tone: qcTone(String(row?.status || '').trim()),
    }))
    .filter((row) => row.code && row.status)
}

function packageHeadline(item) {
  const linkedCount = Number(item.newly_linked || 0)
  if (item.outcome === 'already') return '已经上传过'
  if (item.outcome === 'pinned') return linkedCount ? `新关联 ${linkedCount} 个` : '已挂到当前工单'
  if (item.outcome === 'reused') return linkedCount ? `新关联 ${linkedCount} 个` : '复用已有文件夹'
  if (linkedCount) return `新关联 ${linkedCount} 个`
  return '已保存'
}

function fileCount(counts, code) {
  const count = counts.get(code)
  return count ? String(count) : ''
}

function matchedCounts(item) {
  const counts = new Map()
  ;(item.matched_files || []).forEach((row) => {
    const code = String(row?.code || '').trim()
    if (code) counts.set(code, Number(row.count || 0))
  })
  return counts
}

function describeItem(item, phase) {
  const { unmatched, ignoredDirectory, warnings } = splitIssues(item.issues)
  const isPackage = item.kind === 'package'
  const skipped = item.outcome === 'skipped'
  const keptInFolder = isPackage && !skipped
  const savedCount = Number(item.accepted_count ?? item.file_count ?? 0)
  const counts = matchedCounts(item)
  const lines = []

  if (phase === 'pending') {
    uniqueCodes(item.matched_codes).forEach((code) => {
      lines.push({
        code,
        result: '已匹配',
        note: '',
        count: fileCount(counts, code),
        tone: 'is-pass',
      })
    })
  } else if (!skipped) {
    qcChecks(item.orders).forEach((row) => {
      lines.push({
        orderId: row.orderId,
        code: row.code,
        result: row.status,
        note: row.detail,
        count: fileCount(counts, row.code),
        tone: row.tone,
      })
    })
  }
  unmatched.forEach((row) => {
    lines.push({
      code: row.code,
      result: keptInFolder ? '未匹配' : '未上传',
      note: keptInFolder ? '仍留在文件夹里' : '',
      count: String(row.count),
      tone: 'is-fail',
    })
  })

  let headline = ''
  if (phase === 'pending') {
    headline = skipped ? '不上传' : `${isPackage ? '保存' : '上传'} ${savedCount} 个文件`
  } else if (skipped) {
    headline = '未保存'
  } else if (isPackage) {
    headline = packageHeadline(item)
  } else {
    const linkedCount = Number(item.newly_linked || 0)
    headline = item.outcome === 'already'
      ? '已经上传过'
      : (linkedCount ? `新关联 ${linkedCount} 个` : '已保存')
  }

  const notes = []
  if (isPackage && ignoredDirectory) {
    notes.push(phase === 'pending' ? '其他子目录不上传' : '其他子目录未上传')
  }
  return { headline, lines, notes, warnings }
}

function summaryCard(item, rows, phase) {
  const describedItem = describeItem(item, phase)
  return {
    key: item.group_id || item.name,
    title: summaryTitle(item, rows),
    headline: describedItem.headline,
    lines: describedItem.lines,
    notes: describedItem.notes,
    warnings: describedItem.warnings,
  }
}

function summaryTitle(item, rows) {
  const duplicated = rows.filter((row) => row.name === item.name).length > 1
  return duplicated ? (item.source_path || item.name) : item.name
}

function mergeUploadSummary(uploaded, checked) {
  const result = uploaded.map((item) => ({ ...item, issues: [...(item.issues || [])] }))
  checked.forEach((preview) => {
    const previewKey = preview.group_id || preview.name
    const current = result.find((item) => (item.group_id || item.name) === previewKey)
    if (!current) {
      if (preview.outcome === 'skipped') result.push(preview)
      return
    }
    current.matched_codes = preview.matched_codes || current.matched_codes || []
    current.matched_files = preview.matched_files || current.matched_files || []
    const issues = new Map(current.issues.map((issue) => [issue.reason, Number(issue.count || 0)]))
    ;(preview.issues || []).forEach((issue) => {
      issues.set(issue.reason, Math.max(issues.get(issue.reason) || 0, Number(issue.count || 0)))
    })
    current.issues = [...issues].map(([reason, count]) => ({ reason, count }))
  })
  return result
}

export default {
  name: 'LibraryResultUploadDialog',
  components: { ElButton, ElDialog, ElIcon, UploadFilled },
  props: {
    modelValue: { type: Boolean, default: false },
  },
  emits: ['update:modelValue', 'uploaded'],
  data() {
    return {
      selected: [],
      acceptedIndexes: [],
      preflightSummary: [],
      report: [],
      checking: false,
      uploading: false,
      dragOver: false,
      preflightVersion: 0,
    }
  },
  computed: {
    cards() {
      if (this.report.length) return this.report
      if (this.preflightSummary.length) {
        return this.preflightSummary.map((item) => summaryCard(item, this.preflightSummary, 'pending'))
      }
      return this.previewCards
    },
    uploadableRows() {
      return this.acceptedIndexes
        .map((index) => this.selected[index])
        .filter(Boolean)
    },
    hasResult() {
      return Boolean(this.report.length && !this.selected.length)
    },
    previewCards() {
      const groups = new Map()
      this.selected.forEach((row) => {
        const parts = row.path.split('/').filter(Boolean)
        const key = parts.length > 1 ? parts[0] : 'loose'
        if (!groups.has(key)) {
          groups.set(key, {
            key,
            title: key === 'loose' ? '零散文件' : key,
            count: 0,
            bytes: 0,
          })
        }
        const group = groups.get(key)
        group.count += 1
        group.bytes += Number(row.file.size || 0)
      })
      return [...groups.values()].map((group) => ({
        key: group.key,
        title: group.title,
        headline: `${group.count} 个 · ${formatSize(group.bytes)}`,
        lines: [],
        notes: [],
        warnings: [],
      }))
    },
  },
  watch: {
    modelValue(visible) {
      this.preflightVersion += 1
      if (!visible) return
      this.selected = []
      this.acceptedIndexes = []
      this.preflightSummary = []
      this.report = []
      this.checking = false
      this.dragOver = false
    },
  },
  methods: {
    pickFiles() {
      if (this.uploading) return
      this.$refs.fileInput.value = ''
      this.$refs.fileInput.click()
    },
    pickFolder() {
      if (this.uploading) return
      this.$refs.folderInput.value = ''
      this.$refs.folderInput.click()
    },
    onFilePick(event) {
      this.useFiles(Array.from(event.target.files || []).map((file) => ({
        file,
        path: file.name,
      })))
    },
    onFolderPick(event) {
      this.useFiles(Array.from(event.target.files || []).map((file) => ({
        file,
        path: String(file.webkitRelativePath || file.name || '').replaceAll('\\', '/'),
      })))
    },
    async onDrop(event) {
      this.dragOver = false
      try {
        this.useFiles(await readDroppedFiles(event.dataTransfer))
      } catch (error) {
        notifyApiError(error, { messages: { default: '读取文件夹失败' } })
      }
    },
    async useFiles(files) {
      if (this.uploading) return
      let incoming = files
      try {
        incoming = await expandResultArchives(files)
      } catch (error) {
        notifyApiError(error, { messages: { default: '读取压缩包失败' } })
        return
      }
      this.report = []
      const unique = new Map()
      ;[...this.selected, ...incoming].forEach((row) => {
        unique.set(`${row.path}\0${row.file.size}\0${row.file.lastModified}`, {
          file: row.file,
          path: row.path,
        })
      })
      const next = [...unique.values()]
      const limitError = resultUploadLimitError(next)
      if (limitError) {
        ElMessage.warning(limitError)
        return
      }
      this.selected = next
      this.runPreflight()
    },
    async runPreflight() {
      const version = ++this.preflightVersion
      if (!this.selected.length) {
        this.acceptedIndexes = []
        this.preflightSummary = []
        return
      }
      this.checking = true
      this.acceptedIndexes = []
      this.preflightSummary = []
      try {
        const result = await preflightLibraryFileBatch(this.selected.map((row) => row.path))
        if (version !== this.preflightVersion) return
        this.acceptedIndexes = (result?.accepted_indexes || []).filter(
          (index) => Number.isInteger(index) && index >= 0 && index < this.selected.length,
        )
        this.preflightSummary = result?.summary || []
      } catch (error) {
        if (version !== this.preflightVersion) return
        notifyApiError(error, { messages: { default: '上传前检查失败' } })
      } finally {
        if (version === this.preflightVersion) this.checking = false
      }
    },
    openOrder(orderId) {
      const href = this.$router.resolve({
        path: '/molecular-cell/library-construction/result',
        query: { id: String(orderId) },
      }).href
      window.open(href, '_blank', 'noopener')
    },
    clearSelection() {
      this.preflightVersion += 1
      this.selected = []
      this.acceptedIndexes = []
      this.preflightSummary = []
      this.report = []
      this.checking = false
    },
    async submit() {
      if (!this.uploadableRows.length || this.checking || this.uploading) return
      const checkedSummary = this.preflightSummary
      const form = new FormData()
      this.uploadableRows.forEach((row) => {
        form.append('files', row.file)
        form.append('paths', row.path)
      })
      this.uploading = true
      try {
        const saved = await uploadLibraryFileBatch(form)
        const summary = mergeUploadSummary(saved?.summary || [], checkedSummary)
        this.report = summary.map((item) => summaryCard(item, summary, 'result'))
        this.preflightVersion += 1
        this.selected = []
        this.acceptedIndexes = []
        this.preflightSummary = []
        const linked = summary.reduce((total, item) => total + Number(item.newly_linked || 0), 0)
        const savedCount = summary.filter((item) => item.outcome !== 'skipped').length
        if (savedCount) {
          ElMessage.success(linked ? `已关联 ${linked} 个质检结果` : `已处理 ${savedCount} 组`)
        } else {
          ElMessage.warning('没有文件被保存，请查看未保存原因')
        }
        this.$emit('uploaded', saved)
      } catch (error) {
        notifyApiError(error, { messages: { default: '上传失败' } })
      } finally {
        this.uploading = false
      }
    },
  },
}
</script>

<style scoped>
.batch-layout {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 16px;
  height: min(440px, calc(100vh - 260px));
  min-height: 320px;
  max-height: 440px;
  align-items: stretch;
}

.batch-source,
.batch-review {
  min-width: 0;
  min-height: 0;
  height: 100%;
}

.batch-pick {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  min-height: 0;
  padding: 24px;
  cursor: pointer;
  background: var(--el-color-primary-light-9);
  border: 1px dashed var(--el-color-primary-light-5);
  border-radius: 6px;
  transition: background-color 0.16s ease, border-color 0.16s ease;
}

.batch-pick:hover,
.batch-pick.is-over {
  background: var(--el-color-primary-light-8);
  border-color: var(--el-color-primary);
}

.batch-pick:disabled {
  cursor: not-allowed;
  opacity: 0.62;
}

.batch-pick .el-icon {
  margin-bottom: 5px;
  color: var(--el-color-primary);
  font-size: 22px;
}

.batch-pick strong {
  color: var(--el-color-primary);
  font-size: 12px;
  font-weight: 600;
}

.batch-pick span {
  margin-top: 3px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.batch-pick small {
  max-width: 220px;
  margin-top: 18px;
  color: var(--el-text-color-placeholder);
  font-size: 11px;
  line-height: 1.6;
}

.batch-file-input {
  display: none;
}

.batch-review {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
}

.batch-review > header {
  display: flex;
  flex: none;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.batch-review > header strong {
  color: var(--el-text-color-primary);
  font-size: 14px;
}

.batch-review > header span {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.batch-empty {
  display: grid;
  flex: 1;
  place-items: center;
  color: var(--el-text-color-placeholder);
  font-size: 13px;
}

.batch-card-list {
  flex: 1;
  min-height: 0;
  padding: 4px 12px 12px;
  overflow-y: auto;
}

.batch-pack {
  padding: 10px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.batch-pack:last-child {
  border-bottom: 0;
}

.batch-pack > header {
  display: flex;
  gap: 16px;
  align-items: baseline;
  justify-content: space-between;
}

.batch-pack strong {
  min-width: 0;
  overflow: hidden;
  color: var(--el-text-color-primary);
  font-size: 14px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.batch-pack > header span {
  flex: none;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.batch-table {
  margin-top: 12px;
}

.batch-line {
  display: grid;
  grid-template-columns: minmax(88px, 1fr) 96px minmax(0, 1.6fr) 56px;
  column-gap: 16px;
  align-items: baseline;
  padding: 7px 0;
  font-size: 13px;
  line-height: 1.4;
}

.batch-line.is-head {
  padding: 0 0 6px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.batch-line.is-head span:last-child {
  text-align: right;
}

.batch-line b {
  font-weight: 600;
}

.batch-line em,
.batch-line small {
  font-style: normal;
  font-weight: 400;
}

.batch-line small {
  color: var(--el-text-color-secondary);
}

.batch-count {
  display: flex;
  justify-content: flex-end;
  font-variant-numeric: tabular-nums;
}

.batch-count b {
  min-width: 2ch;
  font-weight: 600;
  text-align: right;
}

.batch-count i {
  margin-left: 2px;
  font-style: normal;
}

.batch-note {
  margin: 8px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.batch-note.is-warn,
.batch-line.is-warn em {
  color: var(--el-color-warning);
}

.batch-line.is-pass em {
  color: var(--el-color-success);
}

.batch-line.is-fail em {
  color: var(--el-color-danger);
}

.batch-code-link {
  padding: 0;
  overflow: hidden;
  color: inherit;
  font: inherit;
  font-weight: 600;
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
  background: none;
  border: 0;
}

.batch-code-link:hover {
  text-decoration: underline;
}

@media (max-width: 720px) {
  .batch-layout {
    grid-template-columns: minmax(0, 1fr);
    height: auto;
    max-height: none;
  }

  .batch-source {
    height: 180px;
    min-height: 180px;
  }

  .batch-pick {
    height: 180px;
    min-height: 180px;
  }

  .batch-review {
    height: 220px;
    min-height: 220px;
  }
}
</style>
