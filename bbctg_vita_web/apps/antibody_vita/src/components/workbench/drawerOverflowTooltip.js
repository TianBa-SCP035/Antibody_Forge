const CONTENT_SELECTOR = [
  '.el-input__inner',
  '.el-select__selected-item',
  '.target-selected-text',
].join(', ')

function controlText(content) {
  if (content instanceof HTMLInputElement) return content.value.trim()
  return String(content.textContent || '').trim()
}

function isOverflowing(content) {
  const clip = content.closest('.el-select__selection') || content
  return content.scrollWidth > content.clientWidth
    || clip.scrollWidth > clip.clientWidth
    || content.getBoundingClientRect().right > clip.getBoundingClientRect().right
}

export function syncDrawerControlTooltip(event) {
  const target = event.target
  if (!(target instanceof Element)) return
  if (target.closest('.el-textarea')) return
  const control = target.closest('.el-input, .el-select')
  if (!(control instanceof HTMLElement)) return
  const content = control.querySelector(CONTENT_SELECTOR)
  if (!(content instanceof HTMLElement)) {
    control.removeAttribute('title')
    return
  }
  const text = controlText(content)
  if (text && isOverflowing(content)) control.setAttribute('title', text)
  else control.removeAttribute('title')
}
