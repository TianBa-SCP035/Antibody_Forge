<template>
  <button type="button" class="check-mark" :disabled="disabled" :title="title" @click.stop="$emit('open')">
    <span class="check-result" :class="resultClass">{{ resultText }}</span>
    <span v-if="summary?.judged" class="check-count">{{ summary.judged }}/{{ summary.total }}</span>
  </button>
</template>

<script>
export default {
  name: 'AntigenCheckMark',
  props: {
    summary: { type: Object, default: null },
    disabled: { type: Boolean, default: false },
    disabledTip: { type: String, default: '' },
  },
  emits: ['open'],
  computed: {
    resultText() {
      return this.summary?.result || '未判定'
    },
    resultClass() {
      if (this.summary?.result === '是') return 'is-yes'
      if (this.summary?.result === '否') return 'is-no'
      return 'is-none'
    },
    title() {
      if (this.disabled) return this.disabledTip
      return '查看活性验证（SEC-HPLC、SDS-PAGE、ELISA、FACS、荧光）'
    },
  },
}
</script>

<style scoped>
.check-mark {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0;
  border: 0;
  background: transparent;
  font: inherit;
  cursor: pointer;
}
.check-mark:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
.check-result {
  padding: 0 6px;
  border-radius: 3px;
  font-size: 12px;
  line-height: 18px;
}
.check-result.is-yes {
  background: var(--el-color-success-light-9);
  color: var(--el-color-success);
}
.check-result.is-no {
  background: var(--el-color-danger-light-9);
  color: var(--el-color-danger);
}
.check-result.is-none {
  background: var(--el-fill-color-light);
  color: var(--el-text-color-secondary);
}
.check-count {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
</style>
