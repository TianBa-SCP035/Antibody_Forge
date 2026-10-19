<template>
  <el-select
    ref="selectRef"
    v-bind="boundAttrs"
    class="list-filter-select"
    :model-value="selectModel"
    :multiple="isMulti"
    :collapse-tags="isMulti"
    :collapse-tags-tooltip="isMulti"
    :max-collapse-tags="1"
    @update:model-value="onNativeUpdate"
    @clear="emit('clear', $event)"
    @visible-change="onVisible"
  >
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
}>()

const emit = defineEmits<{
  'update:modelValue': [value: unknown]
  change: [value: unknown]
  clear: [event: Event]
  'visible-change': [visible: boolean]
}>()

const attrs = useAttrs()
const selectRef = ref<any>(null)
const boundAttrs = computed(() => ({
  title: '左键单选并收起，右键追加或取消',
  ...attrs,
}))

let applying = false
let popper: HTMLElement | null = null

const terms = computed(() => normalize(props.modelValue))
const isMulti = computed(() => terms.value.length > 1)
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
  const willMulti = next.length > 1
  if (wasMulti !== willMulti) {
    nextTick(() => {
      setExpanded(true)
      nextTick(() => {
        bindPopper()
        applying = false
      })
    })
    return
  }
  applying = false
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
