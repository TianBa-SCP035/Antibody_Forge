<script setup>
import { ElButton, ElDrawer, ElForm, ElFormItem } from 'element-plus'

import { syncDrawerControlTooltip } from './drawerOverflowTooltip'

/**
 * 工作台抽屉外壳：标题栏、操作栏（上一条 / 下一条）、按 sections 分卡片排字段。
 * 字段控件由页面在 #field 插槽里渲染：特殊控件自己写，其余交给 WorkbenchDrawerField，保存走 workbenchDrawerMixin 的 persistRow。
 * 字段定义可用：wide 占整行、sync 并排多行文本等高、solo 独占左列、rowBreak 之后换行、labelWidth。
 * 分组可用：queue 排队信息底色、accent 强调底色、mark 是否显示小标题色条（缺省跟随 titleMark）。
 * 插槽：meta 标题下的摘要、actions 行操作、before-fields / after-fields 字段前后的附加内容（如明细表）。
 */
defineOptions({ name: 'WorkbenchDrawer' })

defineProps({
  modelValue: { type: Boolean, default: false },
  row: { type: Object, default: null },
  title: { type: String, default: '' },
  meta: { type: String, default: '' },
  sections: { type: Array, default: () => [] },
  size: { type: String, default: '520px' },
  labelWidth: { type: String, default: '80px' },
  titleMark: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  hasPrev: { type: Boolean, default: false },
  hasNext: { type: Boolean, default: false },
  requiredKeys: { type: Set, default: null },
})

const emit = defineEmits(['update:modelValue', 'shift'])

function fieldClasses(field) {
  return [
    'drawer-field',
    {
      'is-wide': field.wide,
      'is-synced': field.sync,
      'is-solo': field.solo,
    },
  ]
}
</script>

<template>
  <ElDrawer
    :model-value="modelValue"
    :size="size"
    append-to-body
    :modal="false"
    :show-close="false"
    :lock-scroll="false"
    :title="title"
    modal-class="workbench-drawer-overlay"
    class="workbench-drawer"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <template #header="{ close, titleId }">
      <div class="drawer-header">
        <div class="drawer-heading">
          <h2 :id="titleId" class="drawer-title">{{ title }}</h2>
          <slot name="meta">
            <p v-if="meta" class="drawer-header-meta">{{ meta }}</p>
          </slot>
        </div>
        <button type="button" class="drawer-close" aria-label="关闭" @click="close">×</button>
      </div>
    </template>
    <template v-if="row">
      <div class="drawer-toolbar">
        <div class="drawer-toolbar-actions">
          <slot name="actions" />
        </div>
        <div class="drawer-nav">
          <ElButton size="small" :disabled="!hasPrev" @click="emit('shift', -1)">上一条</ElButton>
          <ElButton size="small" :disabled="!hasNext" @click="emit('shift', 1)">下一条</ElButton>
        </div>
      </div>
      <slot name="before-fields" />
      <fieldset class="drawer-fieldset" :disabled="disabled" @mouseover="syncDrawerControlTooltip">
        <ElForm :label-width="labelWidth" size="small" class="drawer-form" @submit.prevent>
          <article
            v-for="section in sections"
            :key="section.title"
            class="drawer-card"
            :class="{ 'is-queue': section.queue, 'is-accent': section.accent }"
          >
            <h3 class="drawer-card-title" :class="{ 'is-marked': section.mark ?? titleMark }">{{ section.title }}</h3>
            <div class="drawer-card-grid">
              <template v-for="field in section.fields" :key="field.key">
                <ElFormItem
                  :label="field.label"
                  :label-width="field.labelWidth"
                  :required="requiredKeys?.has(field.key)"
                  :class="fieldClasses(field)"
                  :data-field-key="field.key"
                >
                  <slot name="field" :field="field" :section="section" :row="row" />
                </ElFormItem>
                <div v-if="field.rowBreak" class="drawer-field-break" aria-hidden="true"></div>
              </template>
            </div>
          </article>
        </ElForm>
      </fieldset>
      <section v-if="$slots['after-fields']" class="drawer-card drawer-card-extra">
        <slot name="after-fields" />
      </section>
    </template>
  </ElDrawer>
</template>

<style scoped>
.drawer-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
}
.drawer-heading {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.drawer-title {
  margin: 0;
  color: var(--el-text-color-primary);
  font-size: 16px;
  font-weight: 650;
  line-height: 1.3;
}
.drawer-header-meta {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.3;
}
.drawer-close {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  margin: -2px -4px 0 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--el-text-color-secondary);
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
}
.drawer-close:hover {
  color: var(--el-text-color-primary);
}
.drawer-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  min-height: 28px;
  margin: 0 0 8px;
}
.drawer-toolbar-actions,
.drawer-nav {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  gap: 4px;
}
.drawer-toolbar-actions :deep(.action-cell) {
  width: auto;
  flex: 0 0 auto;
  justify-content: flex-start;
}
.drawer-toolbar-actions :deep(> .el-button),
.drawer-nav :deep(.el-button + .el-button) {
  margin-left: 0;
  flex-shrink: 0;
}
.drawer-nav :deep(.el-button) {
  height: 28px;
  min-height: 28px;
  padding: 0 8px;
  flex-shrink: 0;
}
.drawer-fieldset {
  margin: 0;
  padding: 0;
  border: 0;
  min-width: 0;
}
.drawer-card {
  padding: 6px 0 0;
  margin-bottom: 6px;
  background: transparent;
  border: 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
  border-radius: 0;
}
.drawer-card:last-child {
  margin-bottom: 0;
  border-bottom: 0;
}
.drawer-card-extra {
  margin-top: 6px;
  border-top: 1px solid var(--el-border-color-lighter);
}
.drawer-card.is-queue {
  padding: 8px 10px 2px;
  margin-bottom: 8px;
  background: var(--list-mid-bg);
  border: var(--list-mid-border);
  border-radius: var(--list-mid-radius);
}
.drawer-card.is-accent {
  padding: 8px 10px 4px;
  margin-bottom: 8px;
  background: #faf6ff;
  border: 1px solid #eadcff;
  border-radius: var(--list-mid-radius);
}
.drawer-card-title {
  margin: 0 0 6px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  font-weight: 650;
  letter-spacing: 0.04em;
}
.drawer-card-title.is-marked {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 8px;
  color: var(--el-text-color-primary);
  font-size: 13px;
  letter-spacing: 0.02em;
}
.drawer-card-title.is-marked::before {
  flex-shrink: 0;
  width: 3px;
  height: 13px;
  background: var(--el-color-primary);
  border-radius: 2px;
  content: '';
}
.drawer-card.is-queue .drawer-card-title {
  color: var(--el-text-color-primary);
}
.drawer-card.is-accent .drawer-card-title {
  color: #722ed1;
}
.drawer-card.is-accent .drawer-card-title.is-marked::before {
  background: #722ed1;
}
.drawer-card-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  align-items: start;
  column-gap: 12px;
}
.drawer-field.is-wide {
  grid-column: 1 / -1;
}
.drawer-field.is-solo + .drawer-field {
  grid-column-start: 1;
}
.drawer-field.is-synced :deep(.el-textarea__inner) {
  resize: none;
}
.drawer-field-break {
  grid-column: 2;
}
.drawer-form :deep(.el-form-item) {
  margin-bottom: 8px;
}
.drawer-form :deep(.el-form-item__label) {
  color: var(--el-text-color-regular);
  font-size: 13px;
  white-space: nowrap;
}
.drawer-form :deep(.el-form-item__content) {
  min-width: 0;
  align-items: flex-start;
  justify-content: flex-start;
}
html.dark .drawer-card.is-accent {
  background: var(--vita-king-bg);
  border-color: var(--vita-king-border);
}
html.dark .drawer-card.is-accent .drawer-card-title {
  color: var(--vita-king-text);
}
html.dark .drawer-card.is-accent .drawer-card-title.is-marked::before {
  background: var(--vita-king-text);
}
</style>
