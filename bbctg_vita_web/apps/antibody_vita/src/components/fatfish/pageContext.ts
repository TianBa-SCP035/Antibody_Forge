import { WEATHER_CACHE_KEY } from '#/constants/storageKeys'

export type PageContextSnapshot = {
  path: string
  title: string
  heading: string
  mainText: string
  focused: { tag: string; name: string; placeholder: string; value: string } | null
  fields: Array<{ name: string; placeholder: string; label: string; value: string }>
  summary: string
  interactive: boolean
}

/** index.html's static fallback banner and loading screen (always in the DOM), and the pet itself: never page content. */
function isIgnoredRoot(el: Element | null): boolean {
  return !el || !!el.closest('#unsupported-browser, #__app-loading__, .ff-root')
}

function isDisplayed(el: Element | null): boolean {
  if (!el || !(el instanceof HTMLElement)) return false
  if (isIgnoredRoot(el)) return false
  if (el.getAttribute('aria-hidden') === 'true') return false
  const style = window.getComputedStyle(el)
  if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false
  const rect = el.getBoundingClientRect()
  if (rect.width < 1 && rect.height < 1) return false
  return true
}

function visibleText(el: Element | null, max = 800): string {
  if (!el || !isDisplayed(el)) return ''
  const text = (el as HTMLElement).innerText || ''
  return text.replace(/\s+/g, ' ').trim().slice(0, max)
}

function pickHeading(): string {
  const nodes = Array.from(
    document.querySelectorAll('h1,h2,.page-title,.vben-page-title'),
  ) as HTMLElement[]
  for (const n of nodes) {
    if (!isDisplayed(n)) continue
    const t = (n.innerText || '').replace(/\s+/g, ' ').trim()
    if (!t) continue
    return t.slice(0, 80)
  }
  return ''
}

function pickMain(): Element | null {
  const candidates = [
    document.querySelector('main'),
    document.querySelector('.vben-layout-content'),
    document.querySelector('#app'),
  ]
  for (const c of candidates) {
    if (c && isDisplayed(c) && !isIgnoredRoot(c)) return c
  }
  return null
}

export const SECRET_NAME = /密码|口令|password|passwd|pwd|secret|token/i
/** Contact / identity fields: their values are hidden from the models (the field name is still shown). */
export const PRIVATE_NAME = /手机|电话|联系方式|邮箱|e-?mail|身份证|证件号|open_?id|cookie|authorization|api[_ ]?key|密钥|mobile|phone/i

/** Credential or personal-data field name. */
export function isSensitiveName(name: string): boolean {
  return SECRET_NAME.test(name) || PRIVATE_NAME.test(name)
}

/** Email addresses and mainland mobile numbers in free text. */
export function maskContacts(s: string): string {
  return s.replace(/[\w.+-]+@[\w-]+(\.[\w-]+)+/g, '(邮箱已隐藏)').replace(/(?<!\d)1[3-9]\d{9}(?!\d)/g, '(手机号已隐藏)')
}

/**
 * Inputs whose value must never be read, sent to the models or filled. Element Plus `show-password` turns the
 * input into type="text" while revealed, so the eye icon and the field's name/placeholder count too.
 */
export function isSecretInput(el: Element | null): boolean {
  if (!el) return false
  const input = (el.matches('input, textarea') ? el : el.querySelector('input, textarea')) as HTMLInputElement | null
  if (!input) return false
  const type = (input.getAttribute('type') || '').toLowerCase()
  if (type === 'password' || type === 'file' || type === 'hidden') return true
  if (/password/i.test(input.getAttribute('autocomplete') || '')) return true
  if (input.closest('.el-input')?.querySelector('.el-input__password')) return true
  const names = [input.name, input.id, input.placeholder, input.getAttribute('aria-label') || '']
  return names.some((n) => SECRET_NAME.test(n || ''))
}

export function collectPageContext(): PageContextSnapshot {
  const path = location.pathname + location.search
  const title = document.title || ''
  const heading = pickHeading()
  const main = pickMain()
  const active = document.activeElement as HTMLInputElement | HTMLTextAreaElement | null
  let focused: PageContextSnapshot['focused'] = null
  const activeType = (active?.getAttribute('type') || '').toLowerCase()
  const activeIsSecret = isSecretInput(active)
  if (
    active &&
    isDisplayed(active) &&
    !activeIsSecret &&
    !isIgnoredRoot(active) &&
    (active.tagName === 'TEXTAREA' ||
      active.getAttribute('contenteditable') === 'true' ||
      (active.tagName === 'INPUT' &&
        !['button', 'submit', 'reset', 'image', 'checkbox', 'radio'].includes(activeType)))
  ) {
    const focusName = active.getAttribute('name') || active.id || ''
    const focusPlaceholder = active.getAttribute('placeholder') || ''
    const focusLabel = active.getAttribute('aria-label') || ''
    const rawFocus = String((active as HTMLInputElement).value ?? active.innerText ?? '').slice(0, 120)
    focused = {
      tag: active.tagName.toLowerCase(),
      name: focusName,
      placeholder: focusPlaceholder,
      value: [focusName, focusPlaceholder, focusLabel].some((x) => PRIVATE_NAME.test(x || ''))
        ? '(已隐藏)'
        : maskContacts(rawFocus),
    }
  }
  const fields: PageContextSnapshot['fields'] = []
  const nodes = Array.from(
    document.querySelectorAll(
      'input:not([type=hidden]):not([type=password]):not([type=file]), textarea',
    ),
  ).slice(0, 24) as Array<HTMLInputElement | HTMLTextAreaElement>
  for (const n of nodes) {
    if (!isDisplayed(n)) continue
    if (isIgnoredRoot(n) || isSecretInput(n)) continue
    const rect = n.getBoundingClientRect()
    if (rect.width < 2 || rect.height < 2) continue
    const label =
      (n.labels && n.labels[0]?.innerText) ||
      n.getAttribute('aria-label') ||
      n.placeholder ||
      n.name ||
      n.id ||
      ''
    fields.push({
      name: n.name || n.id || label,
      placeholder: n.placeholder || '',
      label: String(label).slice(0, 40),
      value: [label, n.name, n.placeholder].some((x) => PRIVATE_NAME.test(x || ''))
        ? '(已隐藏)'
        : maskContacts(String(n.value || '').slice(0, 80)),
    })
    if (fields.length >= 12) break
  }
  const mainText = maskContacts(visibleText(main, 1000))

  const interactive = fields.length > 0 || !!focused
  const summary = [
    `页面: ${path}`,
    title ? `标题: ${title}` : '',
    heading ? `标题文案: ${heading}` : '',
    interactive
      ? `交互状态: 页面已加载，有 ${fields.length} 个可见输入框`
      : '交互状态: 未扫到可见输入框（可能未登录、非表单页，或表单尚未渲染）。',
    focused
      ? `焦点字段: ${focused.name || focused.placeholder} = ${focused.value || '(空)'}`
      : '',
    fields.length
      ? `可见表单: ${fields
          .map((f) => `${f.label || f.name}=${f.value || '(空)'}`)
          .join('； ')
          .slice(0, 500)}`
      : '',
    mainText ? `正文摘录: ${mainText.slice(0, 400)}` : '',
  ]
    .filter(Boolean)
    .join('\n')
  return { path, title, heading, mainText, focused, fields, summary, interactive }
}

/** WMO weather code (Open-Meteo, used by the home page widget) → short Chinese. */
function weatherText(code: number): string {
  if (code === 0) return '晴'
  if (code <= 3) return '多云'
  if (code <= 48) return '有雾'
  if (code <= 67 || (code >= 80 && code <= 82)) return '下雨'
  if (code <= 77 || code === 85 || code === 86) return '下雪'
  if (code >= 95) return '雷雨'
  return ''
}

function dayPart(hour: number): string {
  if (hour < 5) return '深夜'
  if (hour < 9) return '早上'
  if (hour < 11) return '上午'
  if (hour < 13) return '中午'
  if (hour < 17) return '下午'
  if (hour < 19) return '傍晚'
  if (hour < 22) return '晚上'
  return '深夜'
}

export type WeatherNow = { sky: string; temp: number | null; aqi: number }

/** The home page's cached weather (it refetches every 30 min while open), if recent enough to call "now". */
export function weatherNow(): WeatherNow | null {
  try {
    const w = JSON.parse(localStorage.getItem(WEATHER_CACHE_KEY) || 'null')
    if (!w || Date.now() - Number(w.savedAt) >= 2 * 3600_000) return null
    const temp = typeof w.temp === 'number' ? w.temp : null
    return { sky: weatherText(Number(w.weatherCode)), temp, aqi: Number(w.aqi) }
  } catch {
    return null
  }
}

/** Time and (when the host page has cached it) weather, so small talk can be about the actual day. */
export function ambientHint(now = new Date()): string {
  const week = '日一二三四五六'[now.getDay()]
  const hm = `${now.getHours()}:${String(now.getMinutes()).padStart(2, '0')}`
  const parts = [`现在是周${week}${dayPart(now.getHours())} ${hm}${now.getDay() % 6 === 0 ? '（周末）' : ''}`]
  const w = weatherNow()
  if (w) {
    const air = w.aqi > 150 ? '，空气很差' : w.aqi > 100 ? '，空气一般' : ''
    const t = w.temp
    const feel = t === null ? '' : t < 3 ? '很冷' : t < 12 ? '偏冷' : t < 26 ? '舒服' : t < 32 ? '偏热' : '很热'
    parts.push(`北京${[w.sky, feel].filter(Boolean).join('，') || '天气未知'}${air}`)
  }
  return parts.join('；')
}
