<template>
  <el-select
    ref="selectRef"
    v-bind="boundAttrs"
    class="list-filter-select"
    :class="{ 'is-joined': joined }"
    :model-value="selectModel"
    :multiple="isMulti"
    :collapse-tags="isMulti && !joined"
    :collapse-tags-tooltip="isMulti && !joined"
    :max-collapse-tags="1"
    @update:model-value="onNativeUpdate"
    @clear="emit('clear', $event)"
    @visible-change="onVisible"
  >
    <template v-if="joined && terms.length" #tag>
      <span class="list-filter-joined">
        <slot name="tag" :values="terms">{{ terms.join('、') }}</slot>
      </span>
    </template>
    <slot />
  </el-select>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, useAttrs } from 'vue'

import { ElSelect } from 'element-plus'

defineOptions({
  name: 'ListFilterSelect',
  inheritAttrs: false,
})

const props = defineProps<{
  modelValue?: unknown
  /** 多个值时在框里显示拼接文本，不显示选项胶囊。 */
  joined?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: unknown]
  change: [value: unknown]
  clear: [event: Event]
  'visible-change': [visible: boolean]
}>()

const attrs = useAttrs()
const selectRef = ref<any>(null)
const boundAttrs = computed(() => ({ ...attrs }))

let applying = false
let popper: HTMLElement | null = null

const terms = computed(() => normalize(props.modelValue))
const isMulti = computed(() => (props.joined ? terms.value.length > 0 : terms.value.length > 1))
const selectModel = computed(() => (isMulti.value ? terms.value : (terms.value[0] ?? '')))

function normalize(value: unknown) {
  if (Array.isArray(value)) return value.filter((item) => item !== '' && item != null)
  if (value === '' || value == null) return []
  return [value]
}

function stored(value: unknown[]) {
  if (value.length === 0) return ''
  if (value.length === 1) return value[0]
  return value.slice()
}

function same(left: unknown, right: unknown) {
  const a = normalize(left)
  const b = normalize(right)
  return a.length === b.length && a.every((item, index) => item === b[index])
}

function optionList() {
  const raw = selectRef.value?.optionsArray
  return Array.isArray(raw) ? raw : []
}

function optionFromEvent(event: Event) {
  const target = event.target
  if (!(target instanceof Element)) return null
  const item = target.closest('.el-select-dropdown__item')
  if (!item || item.classList.contains('is-disabled')) return null
  return optionList().find((option) => option?.$el === item) || null
}

function setExpanded(open: boolean) {
  const inst = selectRef.value
  if (inst) inst.expanded = open
}

function unbindPopper() {
  if (!popper) return
  popper.removeEventListener('click', onOptionClick, true)
  popper.removeEventListener('contextmenu', onOptionContext, true)
  popper = null
}

function bindPopper() {
  unbindPopper()
  const root = selectRef.value?.tooltipRef?.popperRef?.contentRef
  if (!(root instanceof HTMLElement)) return
  popper = root
  popper.addEventListener('click', onOptionClick, true)
  popper.addEventListener('contextmenu', onOptionContext, true)
}

function willBeMulti(count: number) {
  return props.joined ? count > 0 : count > 1
}

function commit(next: unknown[], keepOpen: boolean) {
  const wasMulti = isMulti.value
  const value = stored(next)
  applying = true
  emit('update:modelValue', value)
  emit('change', value)
  if (!keepOpen) {
    setExpanded(false)
    nextTick(() => {
      applying = false
    })
    return
  }
  const modeChanged = wasMulti !== willBeMulti(next.length)
  nextTick(() => {
    setExpanded(true)
    if (!modeChanged) {
      bindPopper()
      applying = false
      return
    }
    nextTick(() => {
      bindPopper()
      applying = false
    })
  })
}

function onOptionClick(event: Event) {
  const option = optionFromEvent(event)
  if (!option) return
  event.preventDefault()
  event.stopPropagation()
  commit([option.value], false)
}

function onOptionContext(event: Event) {
  const option = optionFromEvent(event)
  if (!option) return
  event.preventDefault()
  event.stopPropagation()
  const next = terms.value.slice()
  const index = next.indexOf(option.value)
  if (index >= 0) next.splice(index, 1)
  else next.push(option.value)
  commit(next, true)
}

function onNativeUpdate(value: unknown) {
  if (applying || same(value, props.modelValue)) return
  commit(normalize(value), false)
}

function onVisible(visible: boolean) {
  if (visible) nextTick(bindPopper)
  else unbindPopper()
  emit('visible-change', visible)
}

onBeforeUnmount(unbindPopper)
</script>

<style scoped>
.list-filter-select.is-joined {
  width: 100%;
  max-width: 100%;
  min-width: 0;
}
.list-filter-select.is-joined:deep(.el-select__wrapper) {
  width: 100%;
  max-width: 100%;
}
.list-filter-select.is-joined:deep(.el-select__selection) {
  flex-wrap: nowrap;
}
.list-filter-select.is-joined:deep(.el-select__selection.is-near) {
  margin-left: 0;
}
.list-filter-joined {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  color: var(--el-text-color-regular);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.list-filter-select.is-joined:deep(.el-select__input-wrapper) {
  flex: 0 0 auto;
  max-width: none;
}
</style>
