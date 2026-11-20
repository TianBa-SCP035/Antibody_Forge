import { existsSync } from 'node:fs'
import { createRequire } from 'node:module'
import { fileURLToPath, pathToFileURL } from 'node:url'

const SRC = new URL('../', import.meta.url)

const stub = (source) => ({
  url: `data:text/javascript,${encodeURIComponent(source)}`,
  shortCircuit: true,
})

// xlsx 的 ESM 构建才导出 CFB，CommonJS 构建在 Node 下拿不到
let xlsxEsm
try {
  const xlsxJs = createRequire(import.meta.url).resolve('xlsx')
  xlsxEsm = pathToFileURL(xlsxJs.replace(/xlsx\.js$/, 'xlsx.mjs')).href
} catch {
  xlsxEsm = null
}

// 多个测试共用的桩：只放各被测模块都会用到的替身，测试专属状态仍留在各自测试文件里
const STUBS = {
  'element-plus': `
    const log = (entry) => globalThis.crudCalls?.push(entry)
    export const ElMessage = Object.assign(() => {}, {
      warning: (message) => log(['warning', message]),
      success: (message) => log(['success', message]),
      error: () => {},
      info: () => {},
    })
    export const ElMessageBox = {
      confirm: (text) => { log(['confirm', text]); return globalThis.crudConfirm() },
    }
    export const ElIcon = {}
  `,
  '@element-plus/icons-vue': 'export const Filter = {}',
  '#/locales': 'export const $t = (key) => key',
  '@vben/preferences': 'export const preferences = { app: { defaultHomePath: "/home", locale: "zh-CN" } }',
  '#/constants/storageKeys': `
    export const HOME_START_PAGE_STORAGE_KEY = "test-start-page"
    export const WEATHER_CACHE_KEY = "weather"
  `,
  '#/router/routes': 'export const accessRoutes = globalThis.__TEST_ACCESS_ROUTES__ || []',
  '#/utils/auth-session': 'export const isUnauthorizedError = (error) => error?.status === 401',
  '#/api/options': 'export const fetchCatalogTargetOptions = async () => []',
  '#/api/errors': 'export const notifyApiError = (error, { messages }) => globalThis.crudCalls?.push(["error", messages.default])',
  '#/utils/downloadExcel': `
    export const downloadListExcel = (load, name) => { (globalThis.crudCalls ??= []).push(["download", name]); load() }
    export const excelTimestamp = () => "T"
  `,
}

// fatfish 内部的相对导入替身只在 fatfish 目录内生效，避免误伤同名相对导入
function fatfishStub(specifier, context) {
  if (!context.parentURL?.includes('/components/fatfish/')) return null
  if (specifier === './pageTable') return stub('export const readPageTables = () => globalThis.__ffTables || []')
  if (specifier === './session') {
    return stub("export const currentUserKey = () => 'u1'; export const menuPages = () => []; export const openMenuPage = async () => false")
  }
  return null
}

function withExtension(url) {
  const last = url.pathname.split('/').pop() ?? ''
  if (last.includes('.')) return url
  for (const ext of ['.js', '.ts', '.mjs']) {
    const candidate = new URL(`${url.href}${ext}`)
    if (existsSync(fileURLToPath(candidate))) return candidate
  }
  for (const ext of ['.js', '.ts']) {
    const candidate = new URL(`${url.href}/index${ext}`)
    if (existsSync(fileURLToPath(candidate))) return candidate
  }
  return url
}

export async function resolve(specifier, context, next) {
  const scoped = fatfishStub(specifier, context)
  if (scoped) return scoped
  if (specifier === 'xlsx' && xlsxEsm) return next(xlsxEsm, context)
  if (Object.hasOwn(STUBS, specifier)) return stub(STUBS[specifier])
  if (specifier.startsWith('#/')) {
    return next(withExtension(new URL(specifier.slice(2), SRC)).href, context)
  }
  if ((specifier.startsWith('./') || specifier.startsWith('../')) && context.parentURL) {
    const last = specifier.split('/').pop() ?? ''
    if (!last.includes('.')) {
      return next(withExtension(new URL(specifier, context.parentURL)).href, context)
    }
  }
  return next(specifier, context)
}

export async function load(url, context, next) {
  const result = await next(url, context)
  // constants.ts 读 import.meta.env，Node 下没有 Vite 注入，替成固定值
  if (!url.endsWith('/components/fatfish/constants.ts') || result.source == null) return result
  return {
    ...result,
    source: String(result.source).replaceAll('import.meta.env', '({ BASE_URL: "/" })'),
    shortCircuit: true,
  }
}
