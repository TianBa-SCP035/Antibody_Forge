/** 等高文本框（字段 sync）对齐到内容最高的那个，只有一个时按内容撑高；只算可见的。 */
export function syncTextareaHeights(selector) {
  const nodes = [...document.querySelectorAll(selector)].filter((node) => node.getClientRects().length)
  if (!nodes.length) return
  // 量高时压成一行会冒出滚动条、挤窄可用宽度，刚好一行的文字会被多折一行
  nodes.forEach((node) => {
    node.style.overflowY = 'hidden'
    node.style.height = 'auto'
  })
  const height = Math.max(...nodes.map((node) => node.scrollHeight))
  nodes.forEach((node) => {
    node.style.height = `${height}px`
    node.style.overflowY = ''
  })
}
