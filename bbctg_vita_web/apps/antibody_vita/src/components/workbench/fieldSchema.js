import { WORKBENCH_PRIORITY_DEFAULT, WORKBENCH_PRIORITY_OPTIONS } from '#/utils/serumProjectStatus'

import { cleanFieldText } from '#/utils/fieldText'
import { coerceOptionalNonnegInt, coerceRequiredPositiveInt } from './coerce'
import { uniqueTargetCodes } from './targetOptions'

/**
 * 工作台字段定义：一个字段只写一次，工作台列、Excel 列、抽屉字段、表头菜单、长度上限和表格校验都从它推出。
 * 模块列定义文件写 FIELDS = defineFields({ 键: 字段 })，各视图只列字段键和顺序（workbenchColumns / sheetColumns / editorSections）。
 *
 * 字段：
 * - label：名称；某个视图叫法不同写在该视图属性里（list.label、sheet.label、drawer.label）。
 * - type：text 单行文本、textarea 多行文本（保留换行）、int 非负整数（可空）、sort 队列排序、date 日期、
 *   select 单选、multi 多选（值为数组）、tags 顿号连接的多值（可选项排前，可自填）、
 *   user 人员、users 多个人员（顿号连接）、target 靶点名称、target_codes 靶点编号。
 * - options：静态可选项（字符串或 { value, label }）。来自接口的放页面 data 的 optionLists[字段键]
 *   （初值用 fieldOptionLists(FIELDS)），随行变化的覆写 fieldOptions(field, row)。
 * - required：不能为空。emptyValue：表格里清空或贴空时改存这个值（如优先级回到「正常」），不算为空。max：最多几个字。allowCreate：select 可填可选项以外的值（抽屉可新建，表格键入不校验可选项）。
 * - header：表头菜单登记，格式见 workbenchHeaderMenu.js。
 * - list：工作台列属性 show（默认显示）、width、minWidth、className、align、tooltip（false 不要溢出提示）、label。
 * - sheet：Excel 列属性 width、minWidth、align、readonly、lockHint、label。
 * - drawer：抽屉字段属性，原样带给 WorkbenchDrawerField 和页面的 #field 插槽；type 可换成页面自己的控件。
 */

const SHEET_EDIT = {
  date: 'date',
  multi: 'multi',
  select: 'select',
  tags: 'tags',
  target: 'target',
  target_codes: 'target',
  user: 'select',
  users: 'tags',
}
const DRAWER_TYPE = {
  int: 'number',
  sort: 'number',
}
const TAG_TYPES = new Set(['tags', 'users'])
const TAG_SEPARATOR = /[,，、+\r\n\t]/
const LIST_SEPARATOR = /[,，、]/
const SHEET_DATE_RE = /^(\d{4})[./-]?(\d{1,2})[./-]?(\d{1,2})(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?$/

export const ACTIONS_COLUMN = Object.freeze({
  key: 'actions',
  label: '操作',
  defaultVisible: true,
  width: 240,
  align: 'center',
  className: 'action-column-cell',
  fixed: 'right',
})

/** 队列排序字段，接入 workbenchQueueSortMixin 的页面直接用。 */
export const SORT_FIELD = Object.freeze({
  label: '排序',
  type: 'sort',
  list: { label: '序号', show: true, width: 62, className: 'sort-column-cell', tooltip: false },
  sheet: { width: 64, align: 'center' },
})

/** 优先级字段：表格里清空或贴空回到「正常」，和后端空优先级按默认处理一致。 */
export const PRIORITY_FIELD = Object.freeze({
  label: '优先级',
  type: 'select',
  options: WORKBENCH_PRIORITY_OPTIONS,
  required: true,
  emptyValue: WORKBENCH_PRIORITY_DEFAULT,
  header: { type: 'enum', values: 'all', top: { query: 'priority' } },
  list: { show: true, minWidth: 112, tooltip: false },
  sheet: { width: 100 },
})

/** 抽屉里的靶点选择：同时写靶点编号和名称，不是单独的数据字段。 */
export const TARGET_DRAWER_FIELD = Object.freeze({ key: 'target', label: '靶点', type: 'target', wide: true })

export function defineFields(fields) {
  return Object.freeze(Object.fromEntries(
    Object.entries(fields).map(([key, field]) => [key, Object.freeze({ ...field, key })]),
  ))
}

function fieldOf(fields, key) {
  const field = fields[key]
  if (!field) throw new Error(`[fieldSchema] 未定义的字段：${key}`)
  return field
}

/** 工作台列：按 keys 顺序，末尾自动加操作列。 */
export function workbenchColumns(fields, keys) {
  return [
    ...keys.map((key) => {
      const field = fieldOf(fields, key)
      const { show, tooltip, label, ...rest } = field.list || {}
      const plain = tooltip !== false
      return {
        key,
        label: label || field.label,
        ...(show ? { defaultVisible: true } : {}),
        ...(plain ? { prop: key, showOverflowTooltip: true } : {}),
        ...(plain && field.type === 'textarea' ? { keepLineBreaks: true } : {}),
        ...(plain && (TAG_TYPES.has(field.type) || field.type === 'multi') ? { format: displayTags } : {}),
        ...(plain && field.type === 'target_codes' ? { format: displayCodes } : {}),
        ...(plain && field.type === 'select' && field.options?.some((item) => typeof item === 'object')
          ? { format: (value) => optionLabel(field.options, value) ?? '' }
          : {}),
        ...rest,
      }
    }),
    ACTIONS_COLUMN,
  ]
}

/** Excel 列：edit 由字段类型推出，只读列 edit 为 readonly。 */
export function sheetColumns(fields, keys) {
  return keys.map((key) => {
    const field = fieldOf(fields, key)
    const { readonly, label, ...rest } = field.sheet || {}
    return { key, label: label || field.label, edit: readonly ? 'readonly' : SHEET_EDIT[field.type] || 'text', ...rest }
  })
}

/** 抽屉分组：fields 里写字段键，或 { key, ...本处属性 }；键不在 FIELDS 里的对象是抽屉独有的控件，原样保留。 */
export function editorSections(fields, sections) {
  return sections.map((section) => ({
    ...section,
    fields: section.fields.map((entry) => {
      const { key, ...placement } = typeof entry === 'string' ? { key: entry } : entry
      if (typeof entry !== 'string' && !fields[key]) return entry
      const field = fieldOf(fields, key)
      const { label, ...drawer } = field.drawer || {}
      return {
        key,
        label: label || field.label,
        type: DRAWER_TYPE[field.type] || field.type,
        ...(field.options ? { options: field.options } : {}),
        ...(field.max ? { maxlength: field.max } : {}),
        ...(field.required ? { clearable: false } : {}),
        ...(field.allowCreate ? { allowCreate: true } : {}),
        ...drawer,
        ...placement,
      }
    }),
  }))
}

export function headerMenuColumns(fields) {
  return Object.freeze(Object.fromEntries(
    Object.values(fields).filter((field) => field.header).map((field) => [field.key, field.header]),
  ))
}

/** 页面 optionLists 的初值：有静态可选项的字段各拷一份，接口返回后按字段键覆盖。 */
export function fieldOptionLists(fields) {
  return Object.fromEntries(Object.values(fields).filter((field) => field.options).map((field) => [field.key, [...field.options]]))
}

/** 多值字段比较用的文字：数组或分隔串都拆开，按顺序用逗号接起来。 */
export function listFieldText(value) {
  return splitBy(LIST_SEPARATOR, value).join(',')
}

export function fieldStringMax(fields) {
  return Object.fromEntries(Object.values(fields || {}).filter((field) => field.max).map((field) => [field.key, field.max]))
}

export function optionValue(item) {
  return item && typeof item === 'object' ? item.value : item
}

/** 值对应的显示名：{ value, label } 可选项取 label，其余原样返回。 */
export function optionLabel(options, value) {
  const hit = (options || []).find((item) => item && typeof item === 'object' && item.value === value)
  return hit ? hit.label : value
}

/** 按值或显示名匹配可选项，不分大小写；返回可选项的值。 */
export function matchOption(options, text) {
  const value = String(text ?? '').trim()
  const lower = value.toLowerCase()
  const hit = (options || []).find((item) => {
    const candidates = item && typeof item === 'object' ? [item.value, item.label] : [item]
    return candidates.some((candidate) => candidate === value || String(candidate ?? '').toLowerCase() === lower)
  })
  return hit === undefined ? { ok: false, reason: 'option' } : { ok: true, value: optionValue(hit) }
}

/**
 * 表格日期：接受 2026-01-05、2026/1/5、2026.1.5、20260105，可带时间（丢弃），统一成 YYYY-MM-DD；空值返回 null。
 */
export function normalizeSheetDate(text) {
  const raw = String(text ?? '').trim()
  if (!raw) return { ok: true, value: null }
  const match = SHEET_DATE_RE.exec(raw)
  if (!match) return { ok: false, reason: 'date' }
  const year = Number(match[1])
  const month = Number(match[2])
  const day = Number(match[3])
  const date = new Date(Date.UTC(year, month - 1, day))
  const valid = date.getUTCFullYear() === year
    && date.getUTCMonth() === month - 1
    && date.getUTCDate() === day
  if (!valid) return { ok: false, reason: 'date' }
  return { ok: true, value: `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}` }
}

function splitBy(separator, value) {
  const tokens = Array.isArray(value) ? value : String(value ?? '').split(separator)
  return [...new Set(tokens.map((item) => String(item ?? '').trim()).filter(Boolean))]
}

/** tags / users 字段拆成数组：逗号、顿号、加号、换行、制表符都算分隔。 */
export function splitTags(value) {
  return splitBy(TAG_SEPARATOR, value)
}

export function displayTags(value) {
  return splitTags(value).join('、')
}

export function displayCodes(value) {
  return uniqueTargetCodes(value).join(',')
}

/** tags 字段的存储值：可选项里有的（不分大小写）换成可选项写法、按可选项顺序排前，自填的跟在后面，顿号连接；空返回 null。 */
export function joinTags(options, value) {
  const values = (options || []).map(optionValue)
  const byLower = new Map(values.map((item) => [String(item).toLowerCase(), item]))
  const tokens = [...new Set(splitTags(value).map((item) => byLower.get(item.toLowerCase()) ?? item))]
  if (!tokens.length) return null
  const known = new Set(values)
  return [...values.filter((item) => tokens.includes(item)), ...tokens.filter((item) => !known.has(item))].join('、')
}

/** multi 字段的存储值：选中的值按可选项顺序排成数组。 */
export function multiValues(options, value) {
  const tokens = splitBy(LIST_SEPARATOR, value)
  return (options || []).map(optionValue).filter((item) => tokens.includes(item))
}

function limitLength(field, value) {
  if (field.max && String(value ?? '').length > field.max) return { ok: false, reason: 'length' }
  return { ok: true, value }
}

function coerceMulti(input, options) {
  const values = []
  for (const token of splitBy(LIST_SEPARATOR, input)) {
    const result = matchOption(options, token)
    if (!result.ok) return result
    values.push(result.value)
  }
  return { ok: true, value: multiValues(options, values) }
}

function coerceUsers(field, input, options) {
  const names = []
  for (const token of splitTags(input)) {
    const result = matchOption(options, token)
    if (!result.ok) return result
    if (!names.includes(result.value)) names.push(result.value)
  }
  if (!names.length) return field.required ? { ok: false, reason: 'empty' } : { ok: true, value: null }
  return limitLength(field, names.join('、'))
}

/** 存库前整理文字：去首尾空白，多行文本保留换行、其余压成一行，空串记 null；数组等其他值原样。 */
export function cleanFieldValue(field, value) {
  if (typeof value !== 'string') return value ?? null
  return cleanFieldText(value, { keepBreaks: field?.type === 'textarea' }) || null
}

/**
 * 按字段类型把表格里的文字转成要保存的值：返回 { ok: true, value } 或 { ok: false, reason }。
 * reason：empty 必填为空、option 不在可选项、date 日期不对、integer 不是整数、length 超长。
 * options 是这一格的可选项（select / multi / user / users / tags 用），人员列由调用方并入全部人员名单。
 */
export function coerceFieldValue(field, input, options = field.options || []) {
  if (field.type === 'multi') return coerceMulti(input, options)
  if (field.type === 'users') return coerceUsers(field, input, options)
  if (field.type === 'tags') {
    const value = joinTags(options, input)
    if (value === null && field.required) return { ok: false, reason: 'empty' }
    return limitLength(field, value)
  }
  const raw = Array.isArray(input)
    ? input.join(',')
    : cleanFieldText(input, { keepBreaks: field.type === 'textarea' })
  if (field.type === 'sort') return coerceRequiredPositiveInt(raw)
  if (field.type === 'target_codes') return { ok: true, value: uniqueTargetCodes(raw) }
  if (!raw && field.emptyValue !== undefined) return { ok: true, value: field.emptyValue }
  if (!raw) return field.required ? { ok: false, reason: 'empty' } : { ok: true, value: null }
  if (field.type === 'int') return coerceOptionalNonnegInt(raw)
  if (field.type === 'date') return normalizeSheetDate(raw)
  if (field.type === 'select' || field.type === 'user') {
    const result = matchOption(options, raw)
    return result.ok || !field.allowCreate ? result : limitLength(field, raw)
  }
  return limitLength(field, raw)
}
