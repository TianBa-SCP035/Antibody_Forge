import assert from 'node:assert/strict'
import { readdirSync } from 'node:fs'
import { register } from 'node:module'
import { join } from 'node:path'
import test from 'node:test'
import { fileURLToPath, pathToFileURL } from 'node:url'

const SRC = new URL('../', import.meta.url).href

register(`data:text/javascript,${encodeURIComponent(`
const STUBS = {
  '#/locales': 'export const $t = (key) => key',
  '@vben/preferences': 'export const preferences = { app: { defaultHomePath: "/home", locale: "zh-CN" } }',
  '#/constants/storageKeys': 'export const HOME_START_PAGE_STORAGE_KEY = "test-start-page"',
  '#/router/routes': 'export const accessRoutes = globalThis.__TEST_ACCESS_ROUTES__ || []',
  'vue': 'export const computed = (fn) => ({ get value() { return fn() } })',
}
export async function resolve(specifier, context, next) {
  if (STUBS[specifier]) {
    return { url: 'data:text/javascript,' + encodeURIComponent(STUBS[specifier]), shortCircuit: true }
  }
  if (specifier.startsWith('#/')) {
    const rel = specifier.slice(2)
    const suffix = rel.endsWith('.ts') || rel.endsWith('.js') ? '' : '.ts'
    return next(new URL(rel + suffix, ${JSON.stringify(SRC)}).href, context)
  }
  if (
    specifier.startsWith('./') &&
    !specifier.endsWith('.ts') &&
    !specifier.endsWith('.mjs') &&
    context.parentURL?.includes('/src/router/')
  ) {
    return next(new URL(specifier + '.ts', context.parentURL).href, context)
  }
  return next(specifier, context)
}`)}`)

const { canAccessRoutePath } = await import('./routeAccess.ts')
const { setCachedFeatureFilter } = await import('./featureFilter.ts')

const modulesDir = fileURLToPath(new URL('./routes/modules', import.meta.url))
const moduleFiles = readdirSync(modulesDir).filter((file) => file.endsWith('.ts')).sort()
const allRoutes = []
for (const file of moduleFiles) {
  const mod = await import(pathToFileURL(join(modulesDir, file)).href)
  if (Array.isArray(mod.default)) {
    allRoutes.push(...mod.default)
  }
}

function checker(codes) {
  const set = new Set(codes)
  return (required) => required.some((code) => set.has(code))
}

test('all existing start paths resolve to the exact route meta.authority permissions', () => {
  const cases = [
    ['/serum/workbench', 'serum.page.workbench'],
    ['/serum/list', 'serum.page.list'],
    ['/serum/titer-orders', 'serum.page.titer_order'],
    ['/discovery/workbench', 'discovery.page.workbench'],
    ['/discovery/synthesis-progress', 'discovery.page.synthesis_progress'],
    ['/molecular-cell/library-construction', 'molecular.page.library'],
    ['/molecular-cell/primer-library', 'molecular.page.primer'],
    ['/mega-automation/flow-work-orders', 'mega.page.flow_work_order'],
    ['/atlas/targets', 'atlas.page.target_library'],
  ]

  for (const [path, requiredCode] of cases) {
    assert.equal(canAccessRoutePath(path, allRoutes, checker([])), false, `${path} should deny empty permissions`)
    assert.equal(canAccessRoutePath(path, allRoutes, checker(['unrelated.code'])), false, `${path} should deny unrelated permissions`)
    assert.equal(canAccessRoutePath(path, allRoutes, checker([requiredCode])), true, `${path} should allow ${requiredCode}`)
    assert.equal(canAccessRoutePath(`${path}?tab=1`, allRoutes, checker([requiredCode])), true, `${path} with query should allow ${requiredCode}`)
  }
})

test('/system routes derive permissions from system.ts route records', () => {
  const userPermCodes = [
    'system.page.user',
    'system.page.role',
    'system.page.permission',
    'system.page.operation_log',
  ]
  for (const code of userPermCodes) {
    assert.equal(canAccessRoutePath('/system/user-permission', allRoutes, checker([code])), true)
    assert.equal(canAccessRoutePath('/system', allRoutes, checker([code])), true)
  }
  assert.equal(canAccessRoutePath('/system/user-permission', allRoutes, checker(['system.page.feature'])), false)
  assert.equal(canAccessRoutePath('/system/features', allRoutes, checker(['system.page.feature'])), true)
  assert.equal(canAccessRoutePath('/system', allRoutes, checker(['system.page.feature'])), true)
  assert.equal(canAccessRoutePath('/system', allRoutes, checker([])), false)
})

test('public routes without authority and unknown paths remain accessible', () => {
  assert.equal(canAccessRoutePath('/home', allRoutes, checker([])), true)
  assert.equal(canAccessRoutePath('/profile', allRoutes, checker([])), true)
  assert.equal(canAccessRoutePath('/custom/unknown', allRoutes, checker([])), true)
})

test('ancestor authority is enforced just like generateRoutesByFrontend', () => {
  const mockRoutes = [
    {
      path: '/parent',
      meta: { authority: ['parent.view'] },
      children: [
        {
          path: '/parent/child',
          meta: { authority: ['child.view'] },
        },
      ],
    },
  ]
  assert.equal(canAccessRoutePath('/parent/child', mockRoutes, checker(['child.view'])), false)
  assert.equal(canAccessRoutePath('/parent/child', mockRoutes, checker(['parent.view', 'child.view'])), true)
})

test('featureCode filtering mirrors filterRouteTree in router access', () => {
  const disabledChild = new Map([
    ['menu.serum', { code: 'menu.serum', enabled: true, visible: true }],
    ['menu.serum.workbench', { code: 'menu.serum.workbench', enabled: false, visible: true }],
  ])
  assert.equal(
    canAccessRoutePath('/serum/workbench', allRoutes, checker(['serum.page.workbench']), {
      stateMap: disabledChild,
      treatMissingFeatureAsHidden: false,
    }),
    false,
  )
  assert.equal(
    canAccessRoutePath('/serum/list', allRoutes, checker(['serum.page.list']), {
      stateMap: disabledChild,
      treatMissingFeatureAsHidden: false,
    }),
    true,
  )

  const hiddenParent = new Map([
    ['menu.serum', { code: 'menu.serum', enabled: true, visible: false }],
    ['menu.serum.list', { code: 'menu.serum.list', enabled: true, visible: true }],
  ])
  assert.equal(
    canAccessRoutePath('/serum/list', allRoutes, checker(['serum.page.list']), {
      stateMap: hiddenParent,
      treatMissingFeatureAsHidden: false,
    }),
    false,
  )

  assert.equal(
    canAccessRoutePath('/serum/list', allRoutes, checker(['serum.page.list']), {
      stateMap: new Map(),
      treatMissingFeatureAsHidden: true,
    }),
    false,
  )

  // Ensure cached feature state helper updates cleanly without throwing
  setCachedFeatureFilter(disabledChild, false)
})

test('home-data canAccessStartPath delegates to route records and cached feature flags', async () => {
  globalThis.__TEST_ACCESS_ROUTES__ = allRoutes
  const { canAccessStartPath } = await import('#/views/Home/home-data')
  setCachedFeatureFilter(
    new Map([
      ['menu.serum', { code: 'menu.serum', enabled: true, visible: true }],
      ['menu.serum.workbench', { code: 'menu.serum.workbench', enabled: false, visible: true }],
      ['menu.serum.list', { code: 'menu.serum.list', enabled: true, visible: true }],
    ]),
    false,
  )
  assert.equal(canAccessStartPath('/serum/workbench', checker(['serum.page.workbench'])), false)
  assert.equal(canAccessStartPath('/serum/list', checker(['serum.page.list'])), true)
  assert.equal(canAccessStartPath('/serum/list', checker([])), false)
  assert.equal(canAccessStartPath('/home', checker([])), true)
})
