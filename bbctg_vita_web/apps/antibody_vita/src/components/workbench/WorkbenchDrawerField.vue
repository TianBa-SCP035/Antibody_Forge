<script setup>
import { computed } from 'vue'

import { ElDatePicker, ElInput, ElOption, ElSelect } from 'element-plus'

import ListFilterSelect from '#/components/ListFilterSelect.vue'
import UserSelect from '#/components/UserSelect.vue'

import { optionValue } from './fieldSchema'
import { uniqueTargetCodes } from './targetOptions'
import WorkbenchLineInput from './WorkbenchLineInput.vue'
import WorkbenchTargetSelect from './WorkbenchTargetSelect.vue'

/**
 * 抽屉标准字段控件。属性和事件由 workbenchDrawerMixin 的 drawerFieldBind(field) 给出：
 * <WorkbenchDrawerField v-else v-bind="drawerFieldBind(field)" />，页面特殊控件写在前面的 v-if 分支里。
 * kind：date 日期、target 靶点、codes 靶点编号（只读）、user 人员、users 多个人员、select 下拉、multi 多选（只能选可选项）、
 * tags 多值（可自填）、textarea 多行文本、text 单行文本、dash 只显示「-」。
 * 日期、下拉、人员、多值选完即 change（multi / tags / users 手势相同：左键单选，右键追加，可搜索，选中项拼成一行显示），
 * 靶点选完 target-change；
 * 文本输入时 input、失焦时 blur；单行文本回车、多行文本 Ctrl+回车即失焦。
 * 日期选中时先 input 写回：ElDatePicker 关面板时用传入的 modelValue 判断是否 change，不写回就永远不触发保存。
 * 字段定义可用：maxlength；textarea 的 resize、nowrap（一行一项的字段，改用 WorkbenchLineInput）；
 * sync 并排等高（单行文本也按一行高的多行框渲染）；type: 'number' 数字框。
 */
defineOptions({ name: 'WorkbenchDrawerField' })

const props = defineProps({
  field: { type: Object, required: true },
  kind: { type: String, default: 'text' },
  value: { type: null, default: null },
  disabled: { type: Boolean, default: false },
  options: { type: Array, default: () => [] },
  selectClass: { type: [String, Array, Object], default: '' },
  clearable: { type: Boolean, default: true },
  filterable: { type: Boolean, default: false },
  allowCreate: { type: Boolean, default: false },
  targetName: { type: String, default: '' },
})

const emit = defineEmits(['input', 'change', 'blur', 'target-change'])

const choiceOptions = computed(() => props.options.map((item) => (
  item && typeof item === 'object' ? { label: item.label ?? item.value, value: item.value } : { label: item, value: item }
)))
const tagOptions = computed(() => {
  const known = props.options.map(optionValue)
  const extras = (Array.isArray(props.value) ? props.value : []).filter((item) => !known.includes(item))
  return [...known, ...extras]
})
function joinedLabels(values) {
  return values.map((item) => choiceOptions.value.find((option) => option.value === item)?.label ?? item).join('、')
}
const numeric = computed(() => props.field.type === 'number' || props.field.key === 'sort_order')
const numberMin = computed(() => {
  if (props.field.key === 'sort_order') return 1
  return props.field.type === 'number' ? 0 : undefined
})
/** 输入法选词时的回车不算。 */
function blurOnEnter(event) {
  if (!event.isComposing) event.target.blur()
}
</script>

<template>
  <ElDatePicker
    v-if="kind === 'date'"
    :model-value="value"
    type="date"
    value-format="YYYY-MM-DD"
    format="YYYY-MM-DD"
    placeholder="选择日期"
    style="width: 100%;"
    :disabled="disabled"
    @update:model-value="emit('input', $event)"
    @change="emit('change', $event)"
  />
  <WorkbenchTargetSelect
    v-else-if="kind === 'target'"
    :model-value="value || []"
    :display-name="targetName"
    :placeholder="targetName ? '' : '搜索靶点'"
    :disabled="disabled"
    @change="emit('target-change', $event)"
  />
  <ElInput
    v-else-if="kind === 'codes'"
    :model-value="uniqueTargetCodes(value).join(',')"
    disabled
    placeholder="自动带出"
  />
  <UserSelect
    v-else-if="kind === 'user'"
    :model-value="value || ''"
    :options="options"
    :placeholder="`选择${field.label}`"
    :disabled="disabled"
    clearable
    @change="emit('change', $event)"
  />
  <UserSelect
    v-else-if="kind === 'users'"
    :model-value="value || []"
    multi-gesture
    joined
    :options="options"
    :placeholder="`选择${field.label}`"
    :disabled="disabled"
    clearable
    title="左键单选，右键追加"
    @change="emit('change', $event)"
  />
  <ListFilterSelect
    v-else-if="kind === 'tags'"
    :model-value="value || []"
    joined
    filterable
    allow-create
    default-first-option
    clearable
    :placeholder="`选择${field.label}`"
    style="width: 100%;"
    :disabled="disabled"
    @change="emit('change', $event)"
  >
    <ElOption v-for="item in tagOptions" :key="item" :label="item" :value="item" />
  </ListFilterSelect>
  <ListFilterSelect
    v-else-if="kind === 'multi'"
    :model-value="value || []"
    joined
    filterable
    :clearable="clearable"
    :placeholder="`选择${field.label}`"
    title="左键单选，右键追加"
    style="width: 100%;"
    :disabled="disabled"
    @change="emit('change', $event)"
  >
    <template #tag="{ values }">{{ joinedLabels(values) }}</template>
    <ElOption v-for="item in choiceOptions" :key="item.value" :label="item.label" :value="item.value" />
  </ListFilterSelect>
  <ElSelect
    v-else-if="kind === 'select'"
    :model-value="value"
    class="drawer-select"
    :class="selectClass"
    :clearable="clearable"
    :filterable="filterable"
    :allow-create="allowCreate"
    default-first-option
    style="width: 100%;"
    :disabled="disabled"
    @change="emit('change', $event)"
  >
    <ElOption
      v-for="item in choiceOptions"
      :key="item.value"
      :label="item.label"
      :value="item.value"
    />
  </ElSelect>
  <WorkbenchLineInput
    v-else-if="kind === 'textarea' && field.nowrap"
    :model-value="value"
    :maxlength="field.maxlength"
    :disabled="disabled"
    @update:model-value="emit('input', $event)"
    @keydown.ctrl.enter="blurOnEnter"
    @blur="emit('blur')"
  />
  <ElInput
    v-else-if="kind === 'textarea'"
    :model-value="value"
    type="textarea"
    :rows="field.sync ? 1 : undefined"
    :autosize="field.sync ? false : { minRows: 1, maxRows: 4 }"
    :resize="field.resize"
    :maxlength="field.maxlength"
    :disabled="disabled"
    @update:model-value="emit('input', $event)"
    @keydown.ctrl.enter="blurOnEnter"
    @blur="emit('blur')"
  />
  <span v-else-if="kind === 'dash'">-</span>
  <ElInput
    v-else
    :model-value="value"
    :type="numeric ? 'number' : 'text'"
    :min="numberMin"
    :maxlength="field.maxlength"
    :disabled="disabled"
    @update:model-value="emit('input', $event)"
    @keydown.enter="blurOnEnter"
    @blur="emit('blur')"
  />
</template>
