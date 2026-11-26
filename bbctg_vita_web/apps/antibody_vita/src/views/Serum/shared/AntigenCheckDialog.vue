<template>
  <el-dialog
    :model-value="modelValue"
    :title="title"
    width="720px"
    append-to-body
    @update:model-value="$emit('update:modelValue', $event)"
    @open="onOpen"
    @closed="onClosed"
  >
    <div v-loading="loading" class="check-body">
      <p v-if="canEdit" class="check-hint">截图后直接 Ctrl+V，粘到高亮的这一项；点另一项再粘就是那一项</p>
      <div
        v-for="item in items"
        :key="item.assay"
        class="check-section"
        :class="{ 'is-paste-target': canEdit && item.assay === pasteAssay }"
        @mousedown="pasteAssay = item.assay"
      >
        <div class="check-head">
          <span class="check-assay">{{ item.assay }}</span>
          <div class="check-judge">
            <span class="check-label">是否合格</span>
            <el-radio-group
              :model-value="item.qualified || ''"
              size="small"
              :disabled="!canEdit || saving[item.assay]"
              @change="value => saveResult(item.assay, value)"
            >
              <el-radio-button value="是">是</el-radio-button>
              <el-radio-button value="否">否</el-radio-button>
            </el-radio-group>
            <el-button
              v-if="canEdit && item.qualified"
              link
              size="small"
              :disabled="saving[item.assay]"
              @click="saveResult(item.assay, '')"
            >清空</el-button>
          </div>
        </div>
        <div class="check-images">
          <div v-for="image in item.images" :key="image.file" class="check-thumb">
            <el-image
              v-if="thumbs[image.file]"
              :src="thumbs[image.file]"
              :preview-src-list="previewList(item)"
              :initial-index="previewIndex(item, image)"
              fit="cover"
              preview-teleported
            />
            <button
              v-if="canEdit"
              type="button"
              class="check-remove"
              title="去掉这张"
              @click="removeImage(item.assay, image)"
            >×</button>
          </div>
          <label v-if="canEdit" class="check-add">
            <span>加图片</span>
            <input type="file" accept="image/png,image/jpeg,image/gif,image/webp,image/bmp" multiple hidden @change="onPick($event, item.assay)" />
          </label>
          <span v-if="!canEdit && !item.images.length" class="check-empty">暂无图片</span>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script>
import { ElButton, ElDialog, ElImage, ElMessage, ElRadioButton, ElRadioGroup } from 'element-plus'

import { notifyApiError } from '#/api/errors'
import {
  fetchAntigenCheck,
  removeAntigenCheckImage,
  saveAntigenCheck,
  uploadAntigenCheckImage,
} from '#/api/serumWorkbench'
import { clipboardHasImage, clipboardImageFiles } from '#/utils/clipboardImages'
import { fetchFileBlob } from '#/utils/file-resource'

export default {
  name: 'AntigenCheckDialog',
  components: { ElButton, ElDialog, ElImage, ElRadioButton, ElRadioGroup },
  props: {
    modelValue: { type: Boolean, default: false },
    antigen: { type: Object, default: null },
    canEdit: { type: Boolean, default: false },
  },
  emits: ['update:modelValue', 'changed'],
  data() {
    return {
      loading: false,
      items: [],
      thumbs: {},
      saving: {},
      pasteAssay: '',
      uploadChain: Promise.resolve(),
    }
  },
  computed: {
    title() {
      const name = this.antigen?.antigen_name || this.antigen?.antigen_id || ''
      return name ? `抗原活性验证 · ${name}` : '抗原活性验证'
    },
  },
  beforeUnmount() {
    this.unbindPaste()
    this.clearThumbs()
  },
  methods: {
    onOpen() {
      window.addEventListener('paste', this.onWindowPaste, true)
      this.load()
    },
    onClosed() {
      this.unbindPaste()
      this.reset()
    },
    unbindPaste() {
      window.removeEventListener('paste', this.onWindowPaste, true)
    },
    onWindowPaste(event) {
      if (!this.modelValue || !this.canEdit || !this.pasteAssay) return
      const files = clipboardImageFiles(event.clipboardData, `${this.pasteAssay}-粘贴`)
      if (!files.length) {
        if (clipboardHasImage(event.clipboardData)) {
          event.preventDefault()
          ElMessage.warning('这种图片格式不支持，请用 PNG 或 JPG')
        }
        return
      }
      event.preventDefault()
      event.stopPropagation()
      this.uploadFiles(this.pasteAssay, files)
    },
    async load() {
      const id = this.antigen?.id
      if (!id) return
      this.loading = true
      try {
        this.apply(await fetchAntigenCheck(id))
      } catch (error) {
        notifyApiError(error, { messages: { default: '加载活性验证失败' } })
      } finally {
        this.loading = false
      }
    },
    apply(data, { notify = false } = {}) {
      this.items = Array.isArray(data?.items) ? data.items : []
      if (!this.items.some((item) => item.assay === this.pasteAssay)) this.pasteAssay = this.items[0]?.assay || ''
      this.loadThumbs()
      if (notify) this.$emit('changed', { antigen_row_id: this.antigen?.id, ...data?.summary })
    },
    async loadThumbs() {
      const id = this.antigen?.id
      const wanted = new Set(this.items.flatMap((item) => item.images.map((image) => image.file)))
      Object.keys(this.thumbs).forEach((file) => {
        if (wanted.has(file)) return
        URL.revokeObjectURL(this.thumbs[file])
        delete this.thumbs[file]
      })
      await Promise.all([...wanted].filter((file) => !this.thumbs[file]).map(async (file) => {
        try {
          const blob = await fetchFileBlob(`/api/serum/workbench/antigen_check/image?antigen_row_id=${id}&file=${encodeURIComponent(file)}`)
          this.thumbs = { ...this.thumbs, [file]: URL.createObjectURL(blob) }
        } catch {
          /* 单张失败不影响其他图片 */
        }
      }))
    },
    clearThumbs() {
      Object.values(this.thumbs).forEach((url) => URL.revokeObjectURL(url))
      this.thumbs = {}
    },
    reset() {
      this.clearThumbs()
      this.items = []
      this.pasteAssay = ''
    },
    previewList(item) {
      return item.images.map((image) => this.thumbs[image.file]).filter(Boolean)
    },
    previewIndex(item, image) {
      return Math.max(0, item.images.filter((one) => this.thumbs[one.file]).findIndex((one) => one.file === image.file))
    },
    async saveResult(assay, value) {
      if (!this.canEdit || !this.antigen?.id) return
      this.saving = { ...this.saving, [assay]: true }
      try {
        this.apply(await saveAntigenCheck({ antigen_row_id: this.antigen.id, assay, qualified: value || null }), { notify: true })
      } catch (error) {
        notifyApiError(error, { messages: { default: '保存判定失败' } })
      } finally {
        this.saving = { ...this.saving, [assay]: false }
      }
    },
    onPick(event, assay) {
      const files = [...(event.target.files || [])]
      event.target.value = ''
      this.pasteAssay = assay
      if (files.length) this.uploadFiles(assay, files)
    },
    uploadFiles(assay, files) {
      this.uploadChain = files.reduce(
        (chain, file) => chain.then(() => this.upload(assay, file)),
        this.uploadChain,
      )
      return this.uploadChain
    },
    async upload(assay, file) {
      if (!this.canEdit || !this.antigen?.id || !this.modelValue) return
      const body = new FormData()
      body.append('antigen_row_id', String(this.antigen.id))
      body.append('assay', assay)
      body.append('file', file)
      try {
        this.apply(await uploadAntigenCheckImage(body), { notify: true })
      } catch (error) {
        notifyApiError(error, { messages: { default: '图片上传失败' } })
      }
    },
    async removeImage(assay, image) {
      if (!this.canEdit || !this.antigen?.id) return
      try {
        this.apply(await removeAntigenCheckImage(this.antigen.id, assay, image.file), { notify: true })
      } catch (error) {
        notifyApiError(error, { messages: { default: '去掉图片失败' } })
      }
    },
  },
}
</script>

<style scoped>
.check-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 120px;
}
.check-section {
  padding: 10px 12px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
  outline: none;
}
.check-section.is-paste-target {
  border-color: var(--el-color-primary-light-5);
}
.check-hint {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.check-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}
.check-assay {
  color: var(--el-text-color-primary);
  font-size: 13px;
  font-weight: 600;
}
.check-judge {
  display: flex;
  align-items: center;
  gap: 8px;
}
.check-label {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.check-images {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.check-thumb {
  position: relative;
  width: 72px;
  height: 72px;
  overflow: hidden;
  border-radius: 4px;
  background: var(--el-fill-color-light);
}
.check-thumb .el-image {
  width: 100%;
  height: 100%;
}
.check-remove {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 18px;
  height: 18px;
  padding: 0;
  border: 0;
  border-radius: 9px;
  background: var(--el-overlay-color-lighter);
  color: #fff;
  line-height: 18px;
  cursor: pointer;
}
.check-add {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  width: 104px;
  height: 72px;
  border-radius: 4px;
  background: var(--el-fill-color-light);
  color: var(--el-text-color-secondary);
  font-size: 12px;
  cursor: pointer;
}
.check-empty {
  color: var(--el-text-color-placeholder);
  font-size: 12px;
  line-height: 24px;
}
</style>
