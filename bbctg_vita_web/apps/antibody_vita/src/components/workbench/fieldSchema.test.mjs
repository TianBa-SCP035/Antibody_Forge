import assert from 'node:assert/strict'
import test from 'node:test'

const {
  ACTIONS_COLUMN,
  cleanFieldValue,
  coerceFieldValue,
  defineFields,
  editorSections,
  fieldOptionLists,
  fieldStringMax,
  headerMenuColumns,
  joinTags,
  listFieldText,
  matchOption,
  multiValues,
  PRIORITY_FIELD,
  sheetColumns,
  SORT_FIELD,
  TARGET_DRAWER_FIELD,
  workbenchColumns,
} = await import('./fieldSchema.js')

const FIELDS = defineFields({
  sort_order: SORT_FIELD,
  status: { label: '状态', type: 'select', options: ['规划中', '已完成'], required: true, header: { type: 'enum' } },
  owner: { label: '负责人', type: 'user', max: 64, list: { minWidth: 90 }, sheet: { width: 90 } },
  strain: { label: '品系', type: 'tags', options: ['RM', 'C57BL/6'], max: 12, list: { show: true } },
  count: { label: '只数', type: 'int', sheet: { label: '数量', readonly: true, lockHint: '自动计算' } },
  remark: { label: '备注', type: 'textarea', max: 5, drawer: { wide: true } },
  method: { label: '方式', type: 'multi', options: ['达普', 'NGS'], list: { tooltip: false } },
  kind: { label: '类型', type: 'select', options: [{ value: 'a', label: '甲' }, { value: 'b', label: '乙' }] },
  species: { label: '种属', type: 'multi', options: ['人', '猴'] },
})

test('存库前整理文字：多行文本留换行，空串记 null，其他值原样', () => {
  assert.equal(cleanFieldValue(FIELDS.remark, ' a\r\n b \n'), 'a\n b')
  assert.equal(cleanFieldValue(FIELDS.owner, ' 张\n三 '), '张 三')
  assert.equal(cleanFieldValue(FIELDS.owner, ' \u200B '), null)
  assert.equal(cleanFieldValue(FIELDS.owner, undefined), null)
  assert.deepEqual(cleanFieldValue(FIELDS.method, ['NGS']), ['NGS'])
  assert.equal(cleanFieldValue(FIELDS.count, 3), 3)
})

test('defineFields 带键冻结，工作台列按类型推出并加操作列', () => {
  assert.equal(FIELDS.status.key, 'status')
  assert.ok(Object.isFrozen(FIELDS) && Object.isFrozen(FIELDS.status))
  const columns = workbenchColumns(FIELDS, ['sort_order', 'strain', 'remark', 'method', 'owner', 'species'])
  const [sort, strain, remark, method, owner, species, actions] = columns
  assert.deepEqual(sort, { key: 'sort_order', label: '序号', defaultVisible: true, width: 62, className: 'sort-column-cell' })
  assert.equal(strain.defaultVisible, true)
  assert.equal(strain.format('RM+C57BL/6'), 'RM、C57BL/6')
  assert.equal(remark.keepLineBreaks, true)
  assert.equal(method.prop, undefined)
  assert.deepEqual(owner, { key: 'owner', label: '负责人', prop: 'owner', showOverflowTooltip: true, minWidth: 90 })
  assert.equal(species.format(['人', '猴']), '人、猴')
  assert.equal(actions, ACTIONS_COLUMN)
  assert.throws(() => workbenchColumns(FIELDS, ['nope']), /未定义的字段：nope/)
})

test('Excel 列：edit 由类型推出，只读列带提示', () => {
  const columns = sheetColumns(FIELDS, ['sort_order', 'owner', 'strain', 'count', 'method', 'remark'])
  assert.deepEqual(columns.map((column) => column.edit), ['text', 'select', 'tags', 'readonly', 'multi', 'text'])
  assert.deepEqual(columns[0], { key: 'sort_order', label: '排序', edit: 'text', width: 64, align: 'center' })
  assert.deepEqual(columns[3], { key: 'count', label: '数量', edit: 'readonly', lockHint: '自动计算' })
})

test('抽屉分组：字段属性、本处属性、抽屉独有控件', () => {
  const [section] = editorSections(FIELDS, [
    { title: '基本', queue: true, fields: ['status', 'count', { key: 'remark', sync: true }, TARGET_DRAWER_FIELD] },
  ])
  assert.equal(section.queue, true)
  const [status, count, remark, target] = section.fields
  assert.deepEqual(status, { key: 'status', label: '状态', type: 'select', options: ['规划中', '已完成'], clearable: false })
  assert.equal(count.type, 'number')
  assert.deepEqual(remark, { key: 'remark', label: '备注', type: 'textarea', maxlength: 5, wide: true, sync: true })
  assert.equal(target, TARGET_DRAWER_FIELD)
})

test('表头菜单、长度上限、可选项初值', () => {
  assert.deepEqual(headerMenuColumns(FIELDS), { status: { type: 'enum' } })
  assert.deepEqual(fieldStringMax(FIELDS), { owner: 64, strain: 12, remark: 5 })
  const lists = fieldOptionLists(FIELDS)
  assert.deepEqual(Object.keys(lists), ['status', 'strain', 'method', 'kind', 'species'])
  assert.notEqual(lists.status, FIELDS.status.options)
})

test('可选项匹配不分大小写，对象选项按值或名称', () => {
  assert.deepEqual(matchOption(['NGS'], ' ngs '), { ok: true, value: 'NGS' })
  assert.deepEqual(matchOption(FIELDS.kind.options, '乙'), { ok: true, value: 'b' })
  assert.deepEqual(matchOption(FIELDS.kind.options, 'A'), { ok: true, value: 'a' })
  assert.deepEqual(matchOption(['NGS'], 'x'), { ok: false, reason: 'option' })
})

test('tags：可选项换成标准写法排前，自填跟后，去重', () => {
  assert.equal(joinTags(['RM', 'C57BL/6'], 'x、c57bl/6,rm+RM'), 'RM、C57BL/6、x')
  assert.equal(joinTags(['RM', 'C57BL/6'], 'C57BL/6\nx\trm'), 'RM、C57BL/6、x')
  assert.equal(joinTags([], ' , '), null)
})

test('多值比较文字、multi 存储值按可选项排序', () => {
  assert.equal(listFieldText(['达普', 'NGS']), listFieldText('达普，NGS'))
  assert.deepEqual(multiValues(['人', '猴', '鼠'], '鼠'), ['鼠'])
  assert.deepEqual(multiValues(['人', '猴', '鼠'], ['鼠', '人', 'x']), ['人', '鼠'])
  assert.deepEqual(multiValues(['人'], ''), [])
})

test('按类型校验转换', () => {
  const coerce = (key, input, options) => coerceFieldValue(FIELDS[key], input, options)
  assert.deepEqual(coerce('status', ' '), { ok: false, reason: 'empty' })
  assert.deepEqual(coerce('status', '已完成'), { ok: true, value: '已完成' })
  assert.deepEqual(coerce('owner', ''), { ok: true, value: null })
  assert.deepEqual(coerce('owner', 'alice', ['Alice']), { ok: true, value: 'Alice' })
  assert.deepEqual(coerce('owner', '王五', ['Alice']), { ok: false, reason: 'option' })
  assert.deepEqual(coerce('strain', 'rm、新品系'), { ok: true, value: 'RM、新品系' })
  assert.deepEqual(coerce('strain', '十二个字的品系名正好可以'), { ok: true, value: '十二个字的品系名正好可以' })
  assert.deepEqual(coerce('strain', '十三个字的品系名就超出上限'), { ok: false, reason: 'length' })
  assert.deepEqual(coerce('count', ' 3 '), { ok: true, value: 3 })
  assert.equal(coerce('count', '-1').ok, false)
  assert.deepEqual(coerce('remark', ' a\tb\n'), { ok: true, value: 'a b' })
  assert.deepEqual(coerce('remark', '123456'), { ok: false, reason: 'length' })
  assert.deepEqual(coerce('method', 'ngs、达普'), { ok: true, value: ['达普', 'NGS'] })
  assert.deepEqual(coerce('method', ['NGS']), { ok: true, value: ['NGS'] })
  assert.deepEqual(coerce('method', '其他'), { ok: false, reason: 'option' })
  assert.deepEqual(coerce('sort_order', '2'), { ok: true, value: 2 })
  assert.deepEqual(coerce('kind', '甲'), { ok: true, value: 'a' })
  assert.deepEqual(coerceFieldValue(PRIORITY_FIELD, ' '), { ok: true, value: '正常' })
  assert.deepEqual(coerceFieldValue(PRIORITY_FIELD, '加急'), { ok: true, value: '加急' })
  assert.deepEqual(coerceFieldValue(PRIORITY_FIELD, '很急'), { ok: false, reason: 'option' })
})
