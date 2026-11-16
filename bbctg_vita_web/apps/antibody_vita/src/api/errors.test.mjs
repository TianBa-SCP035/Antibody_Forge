import assert from 'node:assert/strict'
import { register } from 'node:module'
import test from 'node:test'

register(`data:text/javascript,${encodeURIComponent(`
const STUBS = {
  'element-plus': 'export const ElMessage = () => {}',
  '#/utils/auth-session': 'export const isUnauthorizedError = () => false',
}
export async function resolve(specifier, context, next) {
  if (STUBS[specifier]) return { url: 'data:text/javascript,' + encodeURIComponent(STUBS[specifier]), shortCircuit: true }
  return next(specifier, context)
}
`)}`)

const { resolveUserMessage } = await import('./errors.ts')

const httpError = (status, data) => ({ response: { status, data } })

test('403/404 show the backend envelope message, otherwise the generic text', () => {
  assert.equal(resolveUserMessage(httpError(403, { code: 1, message: '只有负责人可以修改' })).message, '只有负责人可以修改')
  assert.equal(resolveUserMessage(httpError(404, { code: 1, message: '工作台记录不存在' })).message, '工作台记录不存在')
  assert.equal(resolveUserMessage(httpError(404, { detail: 'Not Found' })).message, '请求的资源不存在')
  assert.equal(resolveUserMessage(httpError(403, { code: 1, message: '' })).message, '没有权限执行此操作')
})

test('page overrides win over the backend message', () => {
  const messages = { forbidden: '没有权限下载此文件', notFound: '文件不存在' }
  assert.equal(resolveUserMessage(httpError(403, { code: 1, message: 'x' }), { messages }).message, '没有权限下载此文件')
  assert.equal(resolveUserMessage(httpError(404, { code: 1, message: 'x' }), { messages }).message, '文件不存在')
})

test('5xx never exposes the backend message', () => {
  assert.equal(resolveUserMessage(httpError(500, { code: 1, message: 'secret' })).message, '服务器异常，请联系管理员')
})
