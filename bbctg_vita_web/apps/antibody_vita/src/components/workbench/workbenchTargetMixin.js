import { ElMessage } from 'element-plus'

import { createLatestRequest } from '#/utils/latestRequest'

import { searchWorkbenchTargets, splitTargetNames, uniqueTargetCodes } from './targetOptions'

/**
 * 工作台的靶点编辑：下拉搜索、按编号或名称解析、表格里改靶点。
 * 页面需提供：list, pasteAnchor, pendingSheetOps, sameSheetValue, cloneSheetValue, sheetValueSnapshot, restoreSheetEditValue。
 * 下拉只放本次搜索结果；解析到的靶点另记在 knownTargets 里补名称，不改动下拉。
 * 异步解析回来后先核对单元格还是提交时的值，用户已经改了别的就丢弃这次结果。
 */
export default {
  data() {
    return {
      targetOptions: [],
    }
  },
  computed: {
    sheetTargetSelectOptions() {
      return this.targetOptions.map((item) => ({
        label: `${item.name}（${item.snum}）`,
        value: item.snum,
      }))
    },
    sheetTargetRemoteConfig() {
      return Object.freeze({
        autoLoad: true,
        queryMethod: this.querySheetTargetOptions,
      })
    },
  },
  created() {
    this.knownTargets = new Map()
    this.targetRequest = createLatestRequest()
  },
  methods: {
    createSheetEditOriginal(row, key) {
      return {
        key,
        rowId: row.id,
        targetCodes: this.cloneSheetValue(row.target_codes),
        targetName: row.target_name,
        value: this.cloneSheetValue(this.sheetValueSnapshot(row, key)),
      }
    },
    /** 编号、名称两列互相补全：在这两列间切换要等上一格解析完，免得拿到旧值。 */
    async flushExcelKeyboardSwitch(previousKey, nextKey) {
      if (
        ['target_codes', 'target_name'].includes(previousKey)
        && ['target_codes', 'target_name'].includes(nextKey)
        && this.pendingSheetOps.size
      ) {
        await Promise.allSettled([...this.pendingSheetOps])
      }
    },
    rememberTargets(items) {
      ;(items || []).forEach((item) => {
        if (item?.snum) this.knownTargets.set(item.snum, item)
      })
    },
    mergeTargetOptions(items) {
      this.rememberTargets(items)
      const map = new Map((this.targetOptions || []).map((item) => [item.snum, item]))
      ;(items || []).forEach((item) => {
        if (item?.snum) map.set(item.snum, item)
      })
      this.targetOptions = [...map.values()]
    },
    targetSearchCodes() {
      return []
    },
    async searchTargetOptions(keyword, selectedCodes) {
      const isLatest = this.targetRequest.begin()
      try {
        const codes = Array.isArray(selectedCodes) ? selectedCodes : this.targetSearchCodes()
        const items = await searchWorkbenchTargets(keyword, codes)
        if (!isLatest()) return
        this.rememberTargets(items)
        this.targetOptions = items
      } catch {
        // 搜索失败保留当前下拉内容，用户可以重新输入再搜
      }
    },
    querySheetTargetOptions({ searchValue }) {
      const row = this.list[this.pasteAnchor?.rowIndex]
      return this.searchTargetOptions(searchValue, row?.target_codes)
    },
    targetNameForCodes(codes) {
      return uniqueTargetCodes(codes)
        .map((code) => (
          this.targetOptions.find((item) => item.snum === code)?.name
          || this.knownTargets.get(code)?.name
          || code
        ))
        .join('&')
    },
    onSheetTargetPickerChange(row) {
      const codes = uniqueTargetCodes(row.target_codes)
      row.target_codes = codes
      row.target_name = this.targetNameForCodes(codes)
    },
    async resolveTargetCodes(codes) {
      const normalized = uniqueTargetCodes(codes)
      if (!normalized.length) return { missing: [], nameByCode: new Map(), names: [] }
      const items = await searchWorkbenchTargets('', normalized)
      this.rememberTargets(items)
      const nameByCode = new Map(items.map((item) => [item.snum, item.name]))
      return {
        missing: normalized.filter((code) => !nameByCode.has(code)),
        nameByCode,
        names: normalized.map((code) => nameByCode.get(code)).filter(Boolean),
      }
    },
    async resolveTargetNames(value) {
      const names = splitTargetNames(value)
      if (!names.length) {
        return { ambiguous: [], itemByName: new Map(), items: [], missing: [] }
      }
      const results = await Promise.all(
        names.map(async (name) => {
          const items = await searchWorkbenchTargets(name)
          const exact = items.filter(
            (item) => String(item.name || '').trim().toLowerCase() === name.toLowerCase(),
          )
          this.rememberTargets(exact)
          return { exact, name }
        }),
      )
      const matched = results.filter((item) => item.exact.length === 1)
      return {
        ambiguous: results.filter((item) => item.exact.length > 1).map((item) => item.name),
        itemByName: new Map(matched.map((item) => [item.name.toLowerCase(), item.exact[0]])),
        items: matched.map((item) => item.exact[0]),
        missing: results.filter((item) => item.exact.length === 0).map((item) => item.name),
      }
    },
    isSheetTargetCurrent(row, codes, name) {
      return this.sameSheetValue('target_codes', row.target_codes, codes)
        && this.sameSheetValue('target_name', row.target_name, name)
    },
    restoreSheetTargetEdit(row, key, originalValue) {
      this.restoreSheetEditValue(row, key, originalValue)
    },
    /** 双击选择器选完：编号来自靶点库，只补名称。返回 true 表示需要保存。 */
    async applySheetTargetPick(row, originalCodes, originalName) {
      const codes = uniqueTargetCodes(row.target_codes)
      const submittedName = String(row.target_name || '')
      if (
        this.sameSheetValue('target_codes', codes, originalCodes)
        && this.sameSheetValue('target_name', submittedName, originalName)
      ) {
        return false
      }
      try {
        const resolved = await this.resolveTargetCodes(codes)
        if (!this.isSheetTargetCurrent(row, codes, submittedName)) return false
        if (resolved.missing.length) throw new Error('target-missing')
        row.target_codes = codes
        row.target_name = resolved.names.join('&')
        return true
      } catch {
        if (!this.isSheetTargetCurrent(row, codes, submittedName)) return false
        row.target_codes = this.cloneSheetValue(originalCodes)
        row.target_name = originalName
        ElMessage.warning('靶点校验失败，本次修改未保存')
        return false
      }
    },
    /** 键入或粘贴靶点编号 / 名称后，补全另一列。返回 true 表示需要保存。 */
    async applySheetTargetText(row, key, originalValue) {
      const submittedCodes = uniqueTargetCodes(row.target_codes)
      const submittedName = String(row.target_name || '').trim()
      const reject = (message) => {
        this.restoreSheetTargetEdit(row, key, originalValue)
        ElMessage.warning(message)
        return false
      }
      try {
        if (key === 'target_codes') {
          const resolved = await this.resolveTargetCodes(submittedCodes)
          if (!this.isSheetTargetCurrent(row, submittedCodes, submittedName)) return false
          if (resolved.missing.length) return reject(`未找到靶点编号：${resolved.missing.join('、')}`)
          row.target_codes = submittedCodes
          row.target_name = resolved.names.join('&')
          return true
        }
        const resolved = await this.resolveTargetNames(submittedName)
        if (!this.isSheetTargetCurrent(row, submittedCodes, submittedName)) return false
        if (resolved.missing.length) return reject(`未找到靶点名称：${resolved.missing.join('、')}`)
        if (resolved.ambiguous.length) {
          return reject(`靶点名称不唯一，请双击选择或改填靶点编号：${resolved.ambiguous.join('、')}`)
        }
        row.target_codes = resolved.items.map((item) => item.snum)
        row.target_name = resolved.items.map((item) => item.name).join('&')
        return true
      } catch {
        if (!this.isSheetTargetCurrent(row, submittedCodes, submittedName)) return false
        return reject('靶点校验失败，本次修改未保存')
      }
    },
  },
}
