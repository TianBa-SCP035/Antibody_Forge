import assert from 'node:assert/strict'
import test from 'node:test'

import { mouseSampleCode } from './titerMouseSelect.js'

test('排机样本号带上归类鼠型，已有前缀不再重复', () => {
  assert.equal(mouseSampleCode('RM', '12'), 'RM-12')
  assert.equal(mouseSampleCode('RM-KO', '3'), 'RM-KO-3')
  assert.equal(mouseSampleCode('RM', 'RM-12'), 'RM-12')
  assert.equal(mouseSampleCode('小鼠', '12'), '12')
  assert.equal(mouseSampleCode('', '12'), '12')
})
