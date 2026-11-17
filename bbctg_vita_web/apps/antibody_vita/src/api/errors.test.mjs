import assert from 'node:assert/strict'
import test from 'node:test'

const { resolveUserMessage } = await import('./errors.ts')

const httpError = (status, data) => ({ response: { status, data } })

test('403/404 优先显示后端提示，缺失时用通用文案', () => {
  assert.equal(resolveUserMessage(httpError(403, { code: 1, message: '只有负责人可以修改' })).message, '只有负责人可以修改')
  assert.equal(resolveUserMessage(httpError(404, { code: 1, message: '工作台记录不存在' })).message, '工作台记录不存在')
  assert.equal(resolveUserMessage(httpError(404, { detail: 'Not Found' })).message, '请求的资源不存在')
  assert.equal(resolveUserMessage(httpError(403, { code: 1, message: '' })).message, '没有权限执行此操作')
})

test('页面自定义文案优先于后端提示', () => {
  const messages = { forbidden: '没有权限下载此文件', notFound: '文件不存在' }
  assert.equal(resolveUserMessage(httpError(403, { code: 1, message: 'x' }), { messages }).message, '没有权限下载此文件')
  assert.equal(resolveUserMessage(httpError(404, { code: 1, message: 'x' }), { messages }).message, '文件不存在')
})

test('5xx 不暴露后端提示，只显示通用文案', () => {
  assert.equal(resolveUserMessage(httpError(500, { code: 1, message: 'secret' })).message, '服务器异常，请联系管理员')
})
