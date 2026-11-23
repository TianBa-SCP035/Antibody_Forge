import './shiftHeld.css'

// 按住 Shift 期间给 <html> 加 class；不走响应式，按 Shift 打大写字母时不会让整页重渲染。
const CLASS_NAME = 'vita-shift-held'

function sync(event) {
  document.documentElement.classList.toggle(CLASS_NAME, Boolean(event.shiftKey))
}

window.addEventListener('keydown', sync, true)
window.addEventListener('keyup', sync, true)
window.addEventListener('blur', () => document.documentElement.classList.remove(CLASS_NAME))
