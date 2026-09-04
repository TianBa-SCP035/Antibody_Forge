<template>
  <el-popover
    v-model:visible="visible"
    placement="right"
    trigger="click"
    transition="el-zoom-in-left"
    :width="110"
    :disabled="!editable"
    :teleported="true"
    popper-class="serum-status-popper"
  >
    <div class="serum-status-option-list">
      <button
        v-for="item in options"
        :key="item"
        type="button"
        class="serum-status-option"
        :class="{ 'is-current': item === value }"
        @click.stop="choose(item)"
      >
        {{ item }}
      </button>
    </div>
    <template #reference>
      <el-tag
        class="list-status-tag serum-project-status-tag"
        :class="[{ 'is-editable': editable }, tagClass]"
        :type="tagType"
        effect="plain"
        @click.stop
      >
        {{ displayValue }}
      </el-tag>
    </template>
  </el-popover>
</template>

<script>
import { ElMessage, ElPopover, ElTag } from 'element-plus'

import { notifyApiError } from '#/api/errors'
import { updateSerumStatus } from '#/api/serum'
import { getSerumProjectStatusTagType, SERUM_PROJECT_STATUS_OPTIONS } from '#/utils/serumProjectStatus'

import { SERUM_ERRORS } from './errors'

export default {
  name: 'SerumProjectStatusEditor',
  components: { ElPopover, ElTag },
  props: {
    projectId: { type: [Number, String], default: null },
    value: { type: String, default: '' },
    options: { type: Array, default: () => [...SERUM_PROJECT_STATUS_OPTIONS] },
    editable: { type: Boolean, default: false },
    tagClass: { type: String, default: '' },
  },
  emits: ['change'],
  data() {
    return { visible: false }
  },
  computed: {
    displayValue() {
      return String(this.value ?? '').trim() || '-'
    },
    tagType() {
      return getSerumProjectStatusTagType(this.value)
    },
  },
  watch: {
    editable(value) {
      if (!value) this.visible = false
    },
  },
  methods: {
    choose(newStatus) {
      this.visible = false
      if (newStatus === this.value) {
        return
      }
      if (!this.editable) {
        ElMessage.warning('您没有权限编辑此项目')
        return
      }
      if (!this.projectId) {
        ElMessage.error('项目信息不完整，无法更新状态')
        return
      }
      updateSerumStatus({ id: this.projectId, project_status: newStatus }).then(() => {
        ElMessage.success('状态修改成功')
        this.$emit('change', newStatus)
      }).catch((error) => {
        notifyApiError(error, { messages: SERUM_ERRORS.list.updateStatus })
      })
    },
  },
}
</script>

<style>
.serum-project-status-tag.is-editable {
  cursor: pointer;
}

.serum-status-option-list {
  max-height: 250px;
  overflow-y: auto;
  padding: 4px;
}

.serum-status-option {
  width: 100%;
  padding: 8px 12px;
  border: 0;
  border-radius: var(--list-inner-radius);
  background: transparent;
  color: inherit;
  font: inherit;
  line-height: 18px;
  text-align: left;
  cursor: pointer;
  transition: background-color .16s ease, color .16s ease;
}

.serum-status-option:hover,
.serum-status-option.is-current {
  background-color: #f5f7fa;
  color: #409EFF;
}

.serum-status-option.is-current {
  font-weight: 600;
}

.serum-status-popper {
  z-index: 3000 !important;
  border-radius: var(--list-mid-radius);
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.16);
}
</style>
