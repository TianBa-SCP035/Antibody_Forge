import assert from 'node:assert/strict'
import { readdirSync, readFileSync } from 'node:fs'
import { extname, join, relative } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const SRC = fileURLToPath(new URL('..', import.meta.url))
const TOKEN_FILE = 'styles/theme.css'
// 与色板色差 <= 2 即肉眼不可分辨，应改用变量
const TOLERANCE = 2

const PALETTE = {
  '#ffffff': 'var(--el-bg-color)',
  '#303133': 'var(--el-text-color-primary)',
  '#606266': 'var(--el-text-color-regular)',
  '#909399': 'var(--el-text-color-secondary)',
  '#a8abb2': 'var(--el-text-color-placeholder)',
  '#c0c4cc': 'var(--el-text-color-disabled)',
  '#cdd0d6': 'var(--el-border-color-darker)',
  '#d4d7de': 'var(--el-border-color-dark)',
  '#dcdfe6': 'var(--el-border-color)',
  '#e4e7ed': 'var(--el-border-color-light)',
  '#ebeef5': 'var(--el-border-color-lighter)',
  '#f2f6fc': 'var(--el-border-color-extra-light)',
  '#e6e8eb': 'var(--el-fill-color-darker)',
  '#ebedf0': 'var(--el-fill-color-dark)',
  '#f0f2f5': 'var(--el-fill-color)',
  '#f5f7fa': 'var(--el-fill-color-light)',
  '#fafafa': 'var(--el-fill-color-lighter)',
  '#fafcff': 'var(--el-fill-color-extra-light)',
  '#f2f3f5': 'var(--el-bg-color-page)',
  '#6f4d9c': 'var(--vita-king-text)',
  '#efe8f6': 'var(--vita-king-bg)',
  '#d4c4ea': 'var(--vita-king-border)',
  '#12bbc0': 'var(--vita-library-text)',
  '#e7f8f9': 'var(--vita-library-bg)',
  '#89dde0': 'var(--vita-library-border)',
}
const SERIES = {
  primary: ['#409eff', '#79bbff', '#a0cfff', '#c6e2ff', '#d9ecff', '#ecf5ff', '#337ecc'],
  success: ['#67c23a', '#95d475', '#b3e19d', '#d1edc4', '#e1f3d8', '#f0f9eb', '#529b2e'],
  warning: ['#e6a23c', '#eebe77', '#f3d19e', '#f8e3c5', '#faecd8', '#fdf6ec', '#b88230'],
  danger: ['#f56c6c', '#f89898', '#fab6b6', '#fcd3d3', '#fde2e2', '#fef0f0', '#c45656'],
  info: ['#909399', '#b1b3b8', '#c8c9cc', '#dedfe0', '#e9e9eb', '#f4f4f5', '#73767a'],
}
const STEPS = ['', '-light-3', '-light-5', '-light-7', '-light-8', '-light-9', '-dark-2']
for (const [name, hexes] of Object.entries(SERIES)) {
  hexes.forEach((hex, i) => {
    PALETTE[hex] ??= `var(--el-color-${name}${STEPS[i]})`
  })
}

function normHex(hex) {
  const h = hex.toLowerCase()
  return h.length === 4 ? `#${[...h.slice(1)].map((c) => c + c).join('')}` : h
}

function lab(hex) {
  const lin = (c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)
  const [r, g, b] = [1, 3, 5].map((i) => lin(Number.parseInt(hex.slice(i, i + 2), 16) / 255))
  const f = (t) => (t > 0.008856 ? Math.cbrt(t) : 7.787 * t + 16 / 116)
  const fx = f((0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047)
  const fy = f(0.2126 * r + 0.7152 * g + 0.0722 * b)
  const fz = f((0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883)
  return [116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)]
}

const PALETTE_LAB = Object.entries(PALETTE).map(([hex, use]) => [hex, use, lab(hex)])

function nearestPalette(hex) {
  const target = lab(hex)
  let best = null
  for (const [paletteHex, use, l] of PALETTE_LAB) {
    const d = Math.hypot(...l.map((v, i) => v - target[i]))
    if (d <= TOLERANCE && (!best || d < best.d)) best = { d, hex: paletteHex, use }
  }
  return best
}

function* walk(dir) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name)
    if (entry.isDirectory()) yield* walk(full)
    else if (['.css', '.scss', '.vue'].includes(extname(entry.name))) yield full
  }
}

function styleLines(file, text) {
  const lines = text.split(/\r?\n/)
  if (!file.endsWith('.vue')) return lines.map((line, i) => [i + 1, line])
  const out = []
  let inStyle = false
  lines.forEach((line, i) => {
    if (/^<style\b/.test(line)) inStyle = true
    else if (/^<\/style>/.test(line)) inStyle = false
    else if (inStyle) out.push([i + 1, line])
  })
  return out
}

// 白字写在彩色底上是允许的
const WHITE_TEXT_PROPS = /^(color|fill|stroke|caret-color|--[\w-]*text-color)$/

test('样式里不写死 Element 色板色（及色差 <= 2 的近似色），改用 --el-* / --vita-* 变量', () => {
  const problems = []
  for (const file of walk(SRC)) {
    const rel = relative(SRC, file).replaceAll('\\', '/')
    if (rel === TOKEN_FILE) continue
    for (const [lineNo, line] of styleLines(file, readFileSync(file, 'utf8'))) {
      if (line.includes('theme-ok')) continue
      const code = line.replace(/\/\*.*?\*\//g, '')
      const prop = code.match(/^\s*([\w-]+)\s*:/)?.[1] ?? ''
      for (const raw of code.match(/#[\da-f]{6}\b|#[\da-f]{3}\b/gi) ?? []) {
        const hex = normHex(raw)
        if (hex === '#ffffff' && WHITE_TEXT_PROPS.test(prop)) continue
        const hit = nearestPalette(hex)
        if (hit) problems.push(`${rel}:${lineNo}  ${raw} → ${hit.use}`)
      }
    }
  }
  assert.deepEqual(problems, [], `\n${problems.join('\n')}\n规则见 docs/README.md「前端颜色」`)
})
