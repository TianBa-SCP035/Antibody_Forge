<template>
  <div class="prior-cell" @click.stop @mousedown.stop>
    <button type="button" class="prior-open" @click="open = true">
      <span v-if="text" class="prior-text">{{ text }}</span>
      <span v-if="images.length" class="prior-count">{{ images.length }}图</span>
      <span v-if="!text && !images.length" class="prior-empty">文字或图片</span>
    </button>
    <el-dialog
      v-model="open"
      title="既往筛选"
      width="520px"
      append-to-body
      @open="onOpen"
      @closed="onClosed"
    >
      <el-input
        v-model="draft"
        type="textarea"
        :rows="4"
        maxlength="2000"
        placeholder="文字"
        :disabled="!canEdit"
        @change="commitText"
      />
      <p v-if="canEdit" class="prior-hint">截图或复制图片后直接 Ctrl+V。点图片看原图，可缩放、前后翻</p>
      <div class="prior-images">
        <div v-for="item in images" :key="item.file" class="prior-thumb" :title="item.name">
          <el-image
            v-if="thumbs[item.file]"
            :src="thumbs[item.file]"
            :preview-src-list="previewList"
            :initial-index="previewIndex(item)"
            fit="cover"
            preview-teleported
            :z-index="5000"
          />
          <button v-if="canEdit" type="button" class="prior-remove" title="去掉这张" @click="remove(item)">×</button>
        </div>
        <label v-if="canEdit" class="prior-add">
          加图片
          <input type="file" accept="image/png,image/jpeg,image/gif,image/webp,image/bmp" multiple hidden @change="upload" />
        </label>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { ElDialog, ElImage, ElInput, ElMessage } from 'element-plus'

import { notifyApiError } from '#/api/errors'
import {
  removeDiscoveryPriorImage,
  uploadDiscoveryPriorImage,
} from '#/api/discoveryWorkbench'
import { clipboardHasImage, clipboardImageFiles } from '#/utils/clipboardImages'
import { fetchFileBlob } from '#/utils/file-resource'

export default {
  name: 'DiscoveryPriorScreeningCell',
  components: { ElDialog, ElImage, ElInput },
  props: {
    row: { type: Object, default: null },
    canEdit: { type: Boolean, default: false },
  },
  emits: ['commit', 'images'],
  data() {
    return {
      open: false,
      draft: '',
      thumbs: {},
      uploadChain: Promise.resolve(),
    }
  },
  computed: {
    text() {
      return String(this.row?.prior_screening || '').trim()
    },
    images() {
      const value = this.row?.prior_screening_images
      return Array.isArray(value) ? value.filter((item) => item?.file) : []
    },
    previewList() {
      return this.images.map((item) => this.thumbs[item.file]).filter(Boolean)
    },
  },
  watch: {
    open(value) {
      if (value) this.draft = this.row?.prior_screening || ''
    },
  },
  beforeUnmount() {
    this.unbindPaste()
    this.clearThumbs()
  },
  methods: {
    onOpen() {
      window.addEventListener('paste', this.onWindowPaste, true)
      this.loadThumbs()
    },
    onClosed() {
      this.unbindPaste()
      this.clearThumbs()
    },
    unbindPaste() {
      window.removeEventListener('paste', this.onWindowPaste, true)
    },
    onWindowPaste(event) {
      if (!this.open || !this.canEdit) return
      const files = clipboardImageFiles(event.clipboardData, '既往筛选')
      if (!files.length) {
        if (clipboardHasImage(event.clipboardData)) {
          event.preventDefault()
          ElMessage.warning('这种图片格式不支持，请用 PNG 或 JPG')
        }
        return
      }
      event.preventDefault()
      event.stopPropagation()
      this.uploadFiles(files)
    },
    previewIndex(item) {
      return Math.max(0, this.previewList.indexOf(this.thumbs[item.file]))
    },
    commitText() {
      if (!this.canEdit || !this.row) return
      const next = String(this.draft || '')
      if (next === String(this.row.prior_screening || '')) return
      this.row.prior_screening = next
      this.$emit('commit')
    },
    async loadThumbs() {
      this.clearThumbs()
      const id = this.row?.id
      if (!id) return
      const thumbs = {}
      await Promise.all(this.images.map(async (item) => {
        try {
          const blob = await fetchFileBlob(`/api/discovery/workbench/prior_screening/file?id=${id}&file=${encodeURIComponent(item.file)}`)
          thumbs[item.file] = URL.createObjectURL(blob)
        } catch {
          /* 单张失败不影响其他图片 */
        }
      }))
      this.thumbs = thumbs
    },
    clearThumbs() {
      Object.values(this.thumbs).forEach((url) => URL.revokeObjectURL(url))
      this.thumbs = {}
    },
    async upload(event) {
      const files = [...(event.target.files || [])]
      event.target.value = ''
      if (files.length) await this.uploadFiles(files)
    },
    uploadFiles(files) {
      this.uploadChain = files.reduce(
        (chain, file) => chain.then(() => this.uploadFile(file)),
        this.uploadChain,
      )
      return this.uploadChain
    },
    async uploadFile(file) {
      if (!this.canEdit || !this.row?.id || !this.open) return
      const body = new FormData()
      body.append('workbench_id', String(this.row.id))
      body.append('file', file)
      try {
        const data = await uploadDiscoveryPriorImage(body)
        this.$emit('images', data?.items || [])
        await this.loadThumbs()
      } catch (error) {
        notifyApiError(error, { messages: { default: '图片上传失败' } })
      }
    },
    async remove(item) {
      if (!this.canEdit || !this.row?.id || !item?.file) return
      try {
        const data = await removeDiscoveryPriorImage(this.row.id, item.file)
        this.$emit('images', data?.items || [])
        await this.loadThumbs()
      } catch (error) {
        notifyApiError(error, { messages: { default: '去掉图片失败' } })
      }
    },
  },
}
</script>

<style scoped>
.prior-cell {
  width: 100%;
}
.prior-open {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  min-height: 24px;
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.prior-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.prior-count,
.prior-empty {
  flex: none;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.prior-hint {
  margin: 8px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.prior-images {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}
.prior-thumb {
  position: relative;
  width: 88px;
  height: 88px;
  overflow: hidden;
  border-radius: 4px;
  background: var(--el-fill-color-light);
}
.prior-thumb :deep(.el-image) {
  width: 100%;
  height: 100%;
  cursor: zoom-in;
}
.prior-remove {
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
.prior-add {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 88px;
  height: 88px;
  border-radius: 4px;
  background: var(--el-fill-color-light);
  color: var(--el-text-color-secondary);
  font-size: 12px;
  cursor: pointer;
}
</style>
