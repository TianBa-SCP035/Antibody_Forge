import { ElMessage, ElMessageBox } from 'element-plus'
import { extractApiError } from '#/api/errors'
import { fetchCatalogTargetOptions } from '#/api/options'
import { createLatestRequest } from '#/utils/latestRequest'
import { SERUM_MOUSE_STRAIN_CATEGORY_OPTIONS, SERUM_MOUSE_STRAIN_OPTIONS } from '#/utils/serumMouseOptions'
import { inferSerumTargetTypeFromOptions } from '#/utils/targetStructure'

const MIAN_NUMERALS = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']

export function mianNumber(stageName) {
  const name = (stageName || '').trim()
  const idx = MIAN_NUMERALS.findIndex((n) => name === `${n}免`)
  return idx >= 0 ? idx + 1 : null
}

export function isMianStage(stageName) {
  return mianNumber(stageName) !== null
}

export function mianStageName(n) {
  if (n < 1 || n > 10) return ''
  return `${MIAN_NUMERALS[n - 1]}免`
}

export function pickStepsForGroup(steps, groupId) {
  if (!steps || !groupId) return []
  return steps
    .filter((s) => s.group_id === groupId)
    .slice()
    .sort((a, b) => {
      const orderDiff = (Number(a.sort_order) || 0) - (Number(b.sort_order) || 0)
      if (orderDiff !== 0) return orderDiff
      const aid = Number(a.step_id)
      const bid = Number(b.step_id)
      if (Number.isFinite(aid) && Number.isFinite(bid) && aid !== bid) return aid - bid
      return 0
    })
}

export function reindexGroupSortOrder(steps, groupId) {
  pickStepsForGroup(steps, groupId).forEach((step, index) => {
    step.sort_order = index
  })
}

export function nextAppendStage(groupSteps) {
  const names = groupSteps.map((s) => (s.stage_name || '').trim())
  const mianNums = names.map((name) => mianNumber(name)).filter((n) => n !== null)
  const maxMian = mianNums.length ? Math.max(...mianNums) : 0

  if (maxMian === 0) return '一免'

  const readyForBlood =
    maxMian === 4 &&
    !names.includes('采血') &&
    [1, 2, 3, 4].every((n) => mianNums.includes(n))
  if (readyForBlood) return '采血'

  if (maxMian >= 10) return ''

  return mianStageName(maxMian + 1)
}

export function resortMianStepsInGroup(steps, groupId) {
  const ordered = pickStepsForGroup(steps, groupId)
  const sortedMian = ordered
    .filter((s) => isMianStage(s.stage_name))
    .sort((a, b) => (mianNumber(a.stage_name) || 0) - (mianNumber(b.stage_name) || 0))

  let mianIdx = 0
  const rearranged = ordered.map((step) => {
    if (!isMianStage(step.stage_name)) return step
    return sortedMian[mianIdx++] ?? step
  })

  rearranged.forEach((step, index) => {
    step.sort_order = index
  })
}

/**
 * 免疫实验编辑页和工作台方案页共用的方案编辑：分组、步骤日期、抗原、靶点、备注、复制方案。
 * 页面需提供：postForm（各自的空表单）、canEdit、triggerAutoSave、各自的保存、加载与路由守卫。
 */
export default {
  data() {
    return {
      loading: false,
      targetAliasEdit: null,
      targetDisplayNames: {},
      targetLoading: false,
      targetOptions: [],
      mouseStrainCategoryOptions: SERUM_MOUSE_STRAIN_CATEGORY_OPTIONS,
      mouseStrainOptions: SERUM_MOUSE_STRAIN_OPTIONS,
      remarkDialogVisible: false,
      currentRemark: '',
      currentRemarkRow: null,
      copyDialogVisible: false,
      copyFromGroup: '',
      copyToGroups: [],
      overwriteSteps: true,
      mouseRegistryDialogVisible: false,
      mouseRegistryEditingRow: null,
      activeGroupTab: null,
      autoRecalcDates: true,
      groupIdSnapshots: new WeakMap(),
      autoSaveTimer: null,
      autoSaving: false,
      initializing: true,
      applyingServerState: false,
      formRevision: 0,
      savedRevision: 0,
      saveQueued: false,
      savePromise: null,
    }
  },
  watch: {
    postForm: {
      handler() {
        if (this.initializing || this.applyingServerState) return
        this.formRevision += 1
        this.triggerAutoSave()
      },
      deep: true,
    },
  },
  created() {
    this.initRequest = createLatestRequest()
    this.targetRequest = createLatestRequest()
  },
  deactivated() {
    this.onTargetDropdownVisible(false)
    this.clearAutoSaveTimer()
  },
  beforeUnmount() {
    this.onTargetDropdownVisible(false)
    this.clearAutoSaveTimer()
    this.initRequest.cancel()
    this.targetRequest.cancel()
  },
  methods: {
    addDays(date, days) {
      const targetDate = new Date(date)
      targetDate.setDate(date.getDate() + days)
      return targetDate
    },
    addAntigen() {
      if (!this.canEdit) return
      const existingIds = this.postForm.antigens.map((a) => parseInt(a.antigen_id)).filter((id) => !isNaN(id))
      let nextId = 1
      while (existingIds.includes(nextId)) nextId++
      this.postForm.antigens.push({
        antigen_id: nextId.toString(),
        antigen_name: '',
        antigen_type: '',
        species: '',
        catalog_no: '',
        lot_no: '',
        stock_conc: '',
        vendor: 'BBCTG',
        adjuvant_type: '弗氏佐剂',
        adjuvant_source: '进口',
      })
    },
    addPC() {
      if (!this.canEdit) return
      this.postForm.titer_pcs.push({ pc_name: '', catalog_batch: '', source: '', concentration: '' })
    },
    addStepToGroup(groupId) {
      if (!this.canEdit) return
      if (!groupId) {
        ElMessage.warning('请先选择一个分组')
        return
      }

      const groupSteps = this.getStepsForGroup(groupId)
      const nextStageName = nextAppendStage(groupSteps)

      const newStep = {
        group_id: groupId,
        sort_order: groupSteps.length,
        stage_name: nextStageName,
        day_relative: '',
        date_actual: '',
        antigen_id: [],
        antigen_dose: '',
        adjuvant_name: '',
        cpg_dose: '20µg',
        injection_volume: '100µL',
        route: 's.c.',
        injection_site: '颈部+尾根部',
        remark: ''
      }

      if (nextStageName === '采血') {
        newStep.antigen_id = ['N/A']
        newStep.antigen_dose = '-'
        newStep.adjuvant_name = '-'
        newStep.cpg_dose = '-'
        newStep.injection_volume = '-'
        newStep.route = '-'
        newStep.injection_site = '-'
      }

      this.postForm.steps.push(newStep)
      reindexGroupSortOrder(this.postForm.steps, groupId)
      if (this.autoRecalcDates) {
        this.recalculateGroupDates(groupId, groupSteps.length)
      }
    },
    addTarget() {
      if (!this.canEdit) return
      this.postForm.titer_targets.push({ name: '', type: '', species: '', batch_no: '', passage: '', cell_count: '', catalog_no: '', source: '' })
    },
    applyAntigenRouteByType(step, antigen) {
      if (!antigen || step.route === '-') return
      if (antigen.antigen_type === 'LNP') {
        step.route = 'i.m.'
      } else if (antigen.antigen_type === 'DNA') {
        step.route = 'DNA'
      } else {
        return
      }
      this.handleRouteChange(step)
    },
    /** 保存接口按提交顺序回传新建子行的 id，只填给仍在表里且还没有 id 的那一行。 */
    applyChildIds(response, refs) {
      if (!response) return
      const mappings = [
        ['mouse_groups', 'new_mouse_records', 'id'],
        ['antigens', 'new_antigen_records', 'id'],
        ['steps', 'new_step_records', 'step_id'],
        ['titer_targets', 'new_target_records', 'id'],
        ['titer_pcs', 'new_pc_records', 'id'],
      ]
      mappings.forEach(([formKey, responseKey, idField]) => {
        const currentRows = this.postForm[formKey] || []
        const pendingRefs = refs?.[formKey] || []
        const records = response[responseKey] || []
        records.forEach((record, index) => {
          const item = pendingRefs[index]
          if (item && currentRows.includes(item) && !item[idField]) {
            item[idField] = record[idField]
          }
        })
      })
    },
    cacheGroupId(row) {
      this.groupIdSnapshots.set(row, row.group_id)
    },
    calculateStepDate(row) {
      const expected = this.expectedStepDate(row)
      if (!expected) return
      row.date_actual = this.formatDate(expected.targetDate)
      row.day_relative = this.daysBetween(expected.targetDate, expected.startDate).toString()
    },
    captureNewChildRefs() {
      const capture = (key, idField) => (this.postForm[key] || []).filter((item) => !item[idField])
      return {
        mouse_groups: capture('mouse_groups', 'id'),
        antigens: capture('antigens', 'id'),
        steps: capture('steps', 'step_id'),
        titer_targets: capture('titer_targets', 'id'),
        titer_pcs: capture('titer_pcs', 'id'),
      }
    },
    clearAutoSaveTimer() {
      if (!this.autoSaveTimer) return
      clearTimeout(this.autoSaveTimer)
      this.autoSaveTimer = null
    },
    commitFreeTargetName(event) {
      const input = event.target
      const customName = (input?.value || '').trim()
      if (!customName) return
      this.postForm.target_codes = []
      this.targetDisplayNames = {}
      this.postForm.target_name = customName
      if (input) input.value = ''
      this.updateProjectName()
      this.$nextTick(() => this.$refs.targetSelect?.blur())
    },
    confirmTargetAlias() {
      if (!this.targetAliasEdit) return
      const { code, name } = this.targetAliasEdit
      const customName = name.trim()
      if (!customName) {
        ElMessage.warning('请输入自定义名称')
        return
      }
      if (/[&,，]/.test(customName)) {
        ElMessage.warning('自定义名称不能包含 & 或逗号')
        return
      }
      this.targetDisplayNames = {
        ...this.targetDisplayNames,
        [code]: customName,
      }
      if (!this.postForm.target_codes.includes(code)) {
        this.postForm.target_codes = [...this.postForm.target_codes, code]
      }
      this.targetAliasEdit = null
      this.handleTargetChange(this.postForm.target_codes, true)
    },
    daysBetween(targetDate, startDate) {
      return Math.round((targetDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24))
    },
    doCopyScheme() {
      const from = this.copyFromGroup
      const targets = this.copyToGroups || []

      if (!from) return ElMessage.warning('来源分组异常')
      if (targets.length === 0) return ElMessage.warning('请选择至少一个目标分组')
      if (targets.includes(from)) return ElMessage.warning('目标分组不能包含来源分组')

      const fromSteps = this.getStepsForGroup(from)
      if (fromSteps.length === 0) return ElMessage.warning(`来源分组 ${from} 没有步骤可复制`)

      if (this.overwriteSteps) {
        const targetSet = new Set(targets)
        this.postForm.steps = this.postForm.steps.filter(s => !targetSet.has(s.group_id))
      }

      const clonedAll = []
      for (const to of targets) {
        const cloned = fromSteps.map((s) => {
          const { step_id, sort_order, ...rest } = s || {}
          return {
            ...JSON.parse(JSON.stringify(rest)),
            step_id: null,
            group_id: to
          }
        })
        clonedAll.push(...cloned)
      }

      this.postForm.steps.push(...clonedAll)
      targets.forEach((to) => reindexGroupSortOrder(this.postForm.steps, to))
      ElMessage.success(`已将 ${from} 的方案复制到 ${targets.join(', ')}`)
      this.copyDialogVisible = false
    },
    expectedStepDate(row) {
      const startDate = this.parseDateOnly(this.postForm.start_date)
      if (!startDate) return null
      const groupSteps = this.getStepsForGroup(row.group_id)
      const currentIndex = groupSteps.indexOf(row)
      const lastStep = currentIndex > 0 ? groupSteps[currentIndex - 1] : null
      const baseDate = lastStep?.date_actual ? this.parseDateOnly(lastStep.date_actual) : startDate
      if (!baseDate) return null
      const interval = lastStep
        ? (row.stage_name === '采血' ? 7 : parseInt(this.postForm.immunization_interval) || 0)
        : 0
      return { startDate, targetDate: this.addDays(baseDate, interval) }
    },
    formatDate(date) {
      return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
    },
    getAntigenDisplay(antigenIds) {
      const ids = Array.isArray(antigenIds) ? antigenIds : []
      if (!ids.length) return ''

      const names = ids.map(id => {
        const trimmedId = String(id).trim()
        const antigen = this.postForm.antigens && this.postForm.antigens.find(a => String(a.antigen_id) === trimmedId)
        return (antigen && antigen.antigen_name) || trimmedId
      })

      return names.join(' + ')
    },
    getStepsForGroup(groupId) {
      return pickStepsForGroup(this.postForm.steps, groupId)
    },
    handleAntigenAdjuvantTypeChange(antigenRow) {
      if (!antigenRow.antigen_id || !antigenRow.adjuvant_type || antigenRow.adjuvant_type === '无') return

      this.postForm.steps.forEach(step => {
        const ids = Array.isArray(step.antigen_id) ? step.antigen_id.map(String) : []
        if (ids.includes(String(antigenRow.antigen_id))) {
          this.updateStepAdjuvant(step, antigenRow)
        }
      })
    },
    handleAntigenChange(row, value = row.antigen_id) {
      const validIds = new Set((this.postForm.antigens || []).map(a => String(a.antigen_id || '').trim()).filter(Boolean))
      let antigenIds = (Array.isArray(value) ? value : [value])
        .map(id => String(id ?? '').trim())
        .filter(id => id === 'N/A' || validIds.has(id))

      const hasNA = antigenIds.includes('N/A')
      const hasNormalAntigen = antigenIds.some(id => id !== 'N/A')

      if (hasNA && hasNormalAntigen) {
        antigenIds = antigenIds[antigenIds.length - 1] === 'N/A'
          ? ['N/A']
          : antigenIds.filter(id => id !== 'N/A')
      }

      row.antigen_id = antigenIds

      if (antigenIds.length === 1 && antigenIds[0] === 'N/A') {
        row.antigen_dose = '-'
        row.adjuvant_name = '-'
        row.cpg_dose = '-'
        row.injection_volume = '-'
        row.route = '-'
        row.injection_site = '-'
      } else {
        if (row.antigen_dose === '-') row.antigen_dose = ''
        if (row.adjuvant_name === '-') row.adjuvant_name = ''
        if (row.cpg_dose === '-') row.cpg_dose = '20µg'
        if (row.injection_volume === '-') row.injection_volume = '100µL'
        if (row.route === '-') row.route = 's.c.'
        if (row.injection_site === '-') row.injection_site = '颈部+尾根部'

        const firstAntigenId = antigenIds.find(id => id !== 'N/A')
        if (firstAntigenId) {
          const antigen = this.postForm.antigens.find(a => String(a.antigen_id) === String(firstAntigenId))
          this.updateStepAdjuvant(row, antigen)
          this.applyAntigenRouteByType(row, antigen)
        }
      }
    },
    handleAntigenPaste(event, row) {
      event.preventDefault()
      const clipboardData = event.clipboardData || window.clipboardData
      const pastedText = clipboardData.getData('text')

      if (!pastedText) return
      const parts = pastedText.split(/\t|\r?\n/)

      if (parts.length === 0) return
      row.antigen_name = parts[0] || row.antigen_name
      if (parts.length >= 2) row.catalog_no = parts[1]
      if (parts.length >= 3) row.lot_no = parts[2]
      if (parts.length >= 4) row.stock_conc = parts[3]

      ElMessage.success('已自动填充抗原信息')
    },
    handleAntigenTypeChange(antigenRow) {
      if (!antigenRow.antigen_id) return

      this.postForm.steps.forEach((step) => {
        const ids = Array.isArray(step.antigen_id) ? step.antigen_id.map(String) : []
        if (!ids.includes(String(antigenRow.antigen_id))) return
        const firstAntigenId = ids.find((id) => id !== 'N/A')
        if (firstAntigenId !== String(antigenRow.antigen_id)) return
        this.applyAntigenRouteByType(step, antigenRow)
      })
    },
    handleGroupIdChange(row, newId) {
      const oldId = this.groupIdSnapshots.get(row) ?? row.group_id

      if (!newId || !String(newId).trim()) {
        ElMessage.error('组别不能为空')
        row.group_id = oldId
        this.$nextTick(() => { row.group_id = oldId })
        return
      }

      if (!oldId || oldId === newId) return

      const duplicate = this.postForm.mouse_groups.some(g => g !== row && g.group_id === newId)
      if (duplicate) {
        ElMessage.error(`组别 ${newId} 已存在，🤡想卡BUG？哼哼~🫵🤣不存在的~`)
        this.$nextTick(() => { row.group_id = oldId })
        return
      }

      this.postForm.steps.forEach(s => {
        if (s.group_id === oldId) s.group_id = newId
      })

      if (this.activeGroupTab === oldId) this.activeGroupTab = newId
      this.groupIdSnapshots.set(row, newId)
    },
    handleRouteChange(row) {
      const routeSiteMap = {
        's.c.': '颈部+尾根部',
        'i.p.': '腹腔',
        'i.v.': '尾静脉',
        'i.m.': '大腿肌肉',
        'DNA': '肌肉电转'
      }
      if (routeSiteMap[row.route]) {
        row.injection_site = routeSiteMap[row.route]
      }
    },
    handleStageChange(row) {
      if (row.stage_name === '采血') {
        if (!Array.isArray(row.antigen_id) || row.antigen_id.length === 0 || (row.antigen_id.length === 1 && row.antigen_id[0] !== 'N/A')) {
          row.antigen_id = ['N/A']
          row.antigen_dose = '-'
          row.adjuvant_name = '-'
          row.cpg_dose = '-'
          row.injection_volume = '-'
          row.route = '-'
          row.injection_site = '-'
        }
      } else {
        const antigenIds = Array.isArray(row.antigen_id) ? row.antigen_id : []
        const firstAntigenId = antigenIds.find(id => id !== 'N/A')
        if (firstAntigenId) {
          const antigen = this.postForm.antigens.find(a => String(a.antigen_id) === String(firstAntigenId))
          this.updateStepAdjuvant(row, antigen)
          this.applyAntigenRouteByType(row, antigen)
        }
      }
      if (isMianStage(row.stage_name)) {
        resortMianStepsInGroup(this.postForm.steps, row.group_id)
      }
      if (!this.autoRecalcDates) return
      const groupSteps = this.getStepsForGroup(row.group_id)
      const startIndex = isMianStage(row.stage_name)
        ? 0
        : groupSteps.findIndex(s => s === row)
      this.recalculateGroupDates(row.group_id, startIndex > -1 ? startIndex : 0)
    },
    handleStepDateChange(row) {
      this.syncStepRelativeDay(row)
      if (!this.autoRecalcDates) return

      const groupSteps = this.getStepsForGroup(row.group_id)
      const currentIndex = groupSteps.indexOf(row)
      if (currentIndex > -1) {
        this.recalculateGroupDates(row.group_id, currentIndex + 1)
      }
    },
    handleTargetChange(codes, keepOpen = false) {
      const selected = codes || []
      const namesByCode = new Map(this.targetOptions.map((item) => [item.snum, item.name]))
      this.targetDisplayNames = Object.fromEntries(
        selected.map((code) => [
          code,
          this.targetDisplayNames[code] || namesByCode.get(code) || code,
        ]),
      )
      this.postForm.target_name = selected
        .map((code) => this.targetDisplayNames[code] || code)
        .join('&')
      const inferredType = inferSerumTargetTypeFromOptions(selected, this.targetOptions)
      if (inferredType) {
        this.postForm.target_type = inferredType
      }
      this.updateProjectName()
      if (!keepOpen) {
        this.$nextTick(() => this.$refs.targetSelect?.blur())
      }
    },
    handleTargetFocus() {
      if (!this.targetOptions.length) {
        this.searchTargetOptions('')
      }
    },
    isRevisionConflict(err) {
      const { backendMessage, httpStatus } = extractApiError(err)
      return httpStatus === 409 || String(backendMessage || '').includes('已被其他用户修改')
    },
    onMouseRegistryConfirm({ mouse_registry, mouse_no_list }) {
      const row = this.mouseRegistryEditingRow
      if (!row) return
      row.mouse_registry = mouse_registry
      row.mouse_no_list = mouse_no_list
    },
    onTargetDropdownVisible(open) {
      if (this.targetSelectMenu) {
        this.targetSelectMenu.removeEventListener('click', this.onTargetMenuClick, true)
        this.targetSelectMenu.removeEventListener('contextmenu', this.onTargetMenuClick, true)
        this.targetSelectMenu = null
      }
      if (!open) {
        this.targetAliasEdit = null
        return
      }
      this.$nextTick(() => {
        const root = this.$refs.targetSelect?.tooltipRef?.popperRef?.contentRef
        if (!(root instanceof HTMLElement)) return
        this.targetSelectMenu = root
        root.addEventListener('click', this.onTargetMenuClick, true)
        root.addEventListener('contextmenu', this.onTargetMenuClick, true)
      })
    },
    /** 靶点下拉：左键单选并收起，右键多选切换，Shift+右键改显示名。 */
    onTargetMenuClick(event) {
      const targetEl = event.target instanceof Element ? event.target : null
      if (!targetEl || targetEl.closest('.target-option--editing')) return
      const itemEl = targetEl.closest('.el-select-dropdown__item')
      const option = itemEl && this.$refs.targetSelect?.optionsArray?.find((entry) => entry?.$el === itemEl)
      if (!option || itemEl.classList.contains('is-disabled')) return
      event.preventDefault()
      event.stopPropagation()
      if (event.type !== 'contextmenu') {
        this.targetAliasEdit = null
        this.postForm.target_codes = [option.value]
        this.handleTargetChange([option.value], false)
        if (this.$refs.targetSelect) this.$refs.targetSelect.expanded = false
        return
      }
      if (event.shiftKey) {
        const item = this.targetOptions.find((t) => t.snum === option.value) || {
          snum: option.value,
          name: option.currentLabel || option.value,
        }
        this.startTargetAliasEdit(item)
        return
      }
      this.targetAliasEdit = null
      const current = Array.isArray(this.postForm.target_codes) ? this.postForm.target_codes : []
      const next = [...new Set(current.map((code) => String(code || '').trim()).filter(Boolean))]
      const index = next.indexOf(option.value)
      if (index >= 0) next.splice(index, 1)
      else next.push(option.value)
      this.postForm.target_codes = next
      this.handleTargetChange(next, true)
    },
    openCopyDialogFromTab(fromGroupId) {
      if (!this.canEdit) return
      this.copyFromGroup = fromGroupId
      this.copyToGroups = []
      this.overwriteSteps = true
      this.copyDialogVisible = true
    },
    openMouseRegistryDialog(row) {
      this.mouseRegistryEditingRow = row
      this.mouseRegistryDialogVisible = true
    },
    openRemarkDialog(row) {
      this.currentRemarkRow = row
      this.currentRemark = row.remark || ''
      this.remarkDialogVisible = true
    },
    parseDateOnly(value) {
      if (!value) return null
      if (value instanceof Date) {
        if (Number.isNaN(value.getTime())) return null
        return new Date(value.getFullYear(), value.getMonth(), value.getDate())
      }

      const matched = String(value).match(/^(\d{4})-(\d{2})-(\d{2})/)
      if (matched) {
        return new Date(Number(matched[1]), Number(matched[2]) - 1, Number(matched[3]))
      }

      const parsed = new Date(value)
      if (Number.isNaN(parsed.getTime())) return null
      return new Date(parsed.getFullYear(), parsed.getMonth(), parsed.getDate())
    },
    recalculateAllStepDates() {
      if (!this.autoRecalcDates) {
        const startDate = this.parseDateOnly(this.postForm.start_date)
        if (startDate) {
          ;(this.postForm.steps || []).forEach(step => this.syncStepRelativeDay(step, startDate))
        }
        return
      }
      const groupIds = new Set(this.postForm.steps.map(step => step.group_id).filter(Boolean))
      groupIds.forEach(groupId => this.recalculateGroupDates(groupId))
    },
    recalculateGroupDates(groupId, startIndex = 0) {
      const groupSteps = this.getStepsForGroup(groupId)
      for (let index = Math.max(0, startIndex); index < groupSteps.length; index += 1) {
        this.calculateStepDate(groupSteps[index])
      }
    },
    removeAntigen(index) {
      const antigenId = String(this.postForm.antigens[index]?.antigen_id || '').trim()
      let wasReferenced = false
      if (antigenId) {
        this.postForm.steps.forEach((step) => {
          const ids = Array.isArray(step.antigen_id)
            ? step.antigen_id
            : String(step.antigen_id || '').split(',')
          const remaining = ids.filter((id) => String(id).trim() !== antigenId)
          if (remaining.length !== ids.length) {
            step.antigen_id = remaining
            wasReferenced = true
          }
        })
      }
      this.postForm.antigens.splice(index, 1)
      if (wasReferenced) {
        ElMessage.warning('该抗原已被引用，请记得为相关免疫步骤重新选择抗原')
      }
    },
    removeMouseGroup(index) {
      const group = this.postForm.mouse_groups[index]
      if (group && group.group_id) {
        const groupId = group.group_id
        ElMessageBox.confirm(`确定要删除分组 ${groupId} 及其所有步骤吗？`, '确认删除', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        }).then(() => {
          this.postForm.mouse_groups.splice(index, 1)
          this.postForm.steps = this.postForm.steps.filter(s => s.group_id !== groupId)
          if (this.activeGroupTab === groupId) {
            this.activeGroupTab = this.postForm.mouse_groups.length > 0 ? this.postForm.mouse_groups[0].group_id : null
          }
          this.updateProjectName()
        }).catch(() => {
        })
      } else {
        this.postForm.mouse_groups.splice(index, 1)
        this.updateProjectName()
      }
    },
    removePC(index) {
      this.postForm.titer_pcs.splice(index, 1)
    },
    removeStep(row) {
      const groupSteps = this.getStepsForGroup(row.group_id)
      const groupIndex = groupSteps.findIndex(s => s === row)
      const index = this.postForm.steps.indexOf(row)
      if (index > -1) {
        this.postForm.steps.splice(index, 1)
        reindexGroupSortOrder(this.postForm.steps, row.group_id)
        if (this.autoRecalcDates) {
          this.recalculateGroupDates(row.group_id, groupIndex > -1 ? groupIndex : 0)
        }
      }
    },
    removeTarget(index) {
      this.postForm.titer_targets.splice(index, 1)
    },
    resetTransientEditors() {
      this.targetAliasEdit = null
      this.remarkDialogVisible = false
      this.currentRemark = ''
      this.currentRemarkRow = null
      this.copyDialogVisible = false
      this.copyFromGroup = ''
      this.copyToGroups = []
      this.mouseRegistryDialogVisible = false
      this.mouseRegistryEditingRow = null
    },
    saveRemark() {
      if (this.currentRemarkRow) {
        this.currentRemarkRow.remark = this.currentRemark
      }
      this.remarkDialogVisible = false
      this.currentRemarkRow = null
      this.currentRemark = ''
    },
    async searchTargetOptions(keyword) {
      const isLatest = this.targetRequest.begin()
      this.targetLoading = true
      try {
        const response = await fetchCatalogTargetOptions(keyword, this.postForm.target_codes)
        if (isLatest()) this.targetOptions = response?.items || []
      } catch {
        // 无靶点库权限时仍可用 Shift+Enter 录入名称
      } finally {
        if (isLatest()) this.targetLoading = false
      }
    },
    shouldAutoRecalcDates() {
      const steps = (this.postForm.steps || []).filter(step => String(step?.date_actual || '').trim())
      if (!steps.length) return true
      return steps.every((step) => {
        const actual = this.parseDateOnly(step.date_actual)
        const expected = this.expectedStepDate(step)
        return Boolean(actual && expected && this.formatDate(actual) === this.formatDate(expected.targetDate))
      })
    },
    startTargetAliasEdit(item) {
      this.targetAliasEdit = {
        code: item.snum,
        name: this.targetDisplayNames[item.snum] || item.name,
      }
      this.$nextTick(() => {
        const input = Array.isArray(this.$refs.targetAliasInput)
          ? this.$refs.targetAliasInput[0]
          : this.$refs.targetAliasInput
        input?.focus()
        input?.select()
      })
    },
    syncStepRelativeDay(row, startDate = this.parseDateOnly(this.postForm.start_date)) {
      const targetDate = this.parseDateOnly(row?.date_actual)
      if (startDate && targetDate) {
        row.date_actual = this.formatDate(targetDate)
        row.day_relative = this.daysBetween(targetDate, startDate).toString()
      }
    },
    updateProjectName() {
      const targetName = this.postForm.target_name || ''
      const mouseStrains = [...new Set(
        this.postForm.mouse_groups.map((g) => g.mouse_strain).filter((s) => s && s.trim() !== ''),
      )]
      this.postForm.project_name = `${targetName}基于${mouseStrains.join(',')}的抗体发现`
    },
    updateStepAdjuvant(step, antigen) {
      if (!antigen || !antigen.adjuvant_type) return
      if (antigen.adjuvant_type === '弗氏佐剂') {
        step.adjuvant_name = step.stage_name === '一免' ? 'CFA' : 'IFA'
      } else if (antigen.adjuvant_type === 'ADDAVAX') {
        step.adjuvant_name = 'ADDAVAX'
      }
    },
  },
}
