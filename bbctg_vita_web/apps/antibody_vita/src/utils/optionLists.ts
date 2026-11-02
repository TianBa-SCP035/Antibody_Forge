/**
 * 用后端 options 接口给出的业务枚举覆盖页面默认值；后端没给或给了空列表时保留默认值。
 * mapping 为「接口字段 -> 页面字段」，传数组表示两边同名。
 */
export function applyOptionLists(
  target: Record<string, unknown>,
  data: null | Record<string, unknown> | undefined,
  mapping: Record<string, string> | string[],
) {
  const pairs = Array.isArray(mapping)
    ? mapping.map((key) => [key, key])
    : Object.entries(mapping);
  for (const [source, field] of pairs) {
    const list = data?.[source as string];
    if (Array.isArray(list) && list.length > 0) {
      target[field as string] = [...list];
    }
  }
}
