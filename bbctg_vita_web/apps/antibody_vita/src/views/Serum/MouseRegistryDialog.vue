<template>
  <el-dialog
    :model-value="modelValue"
    :width="isDualLayout ? '760px' : '520px'"
    class="mouse-registry-dialog"
    destroy-on-close
    @update:model-value="$emit('update:modelValue', $event)"
    @open="handleOpen"
  >
    <template #header>
      <div class="dialog-header">
        <h3 class="dialog-header-title">鼠号明细</h3>
        <div v-if="groupId || mouseStrain" class="dialog-header-meta">
          <span v-if="groupId" class="meta-label">组别</span>
          <span v-if="groupId" class="meta-group">{{ groupId }}</span>
          <span v-if="groupId && mouseStrain" class="meta-sep">|</span>
          <span v-if="mouseStrain" class="meta-label">鼠型</span>
          <span v-if="mouseStrain" class="meta-strain" :title="mouseStrain">{{ mouseStrain }}</span>
        </div>
      </div>
    </template>

    <div v-if="group" class="dialog-summary">
      <div v-if="group.mouse_count" class="summary-chip">
        <span class="chip-label">免疫数量</span>
        <span class="chip-value">{{ group.mouse_count }}</span>
      </div>
      <div v-if="group.sex" class="summary-chip">
        <span class="chip-label">性别</span>
        <span class="chip-value">{{ group.sex }}</span>
      </div>
      <div class="summary-chip">
        <span class="chip-label">已录入</span>
        <span class="chip-value">{{ totalEntered }} 只</span>
      </div>
    </div>

    <div class="sections-layout" :class="{ 'sections-layout--dual': isDualLayout }">
      <div v-for="section in sections" :key="section.key" class="registry-section">
        <div class="section-card" :class="`section-card--${section.key.toLowerCase()}`">
          <div class="section-header">
            <span class="sex-tag" :class="`sex-tag--${section.key.toLowerCase()}`">{{ section.label }}</span>
            <span class="section-count">{{ section.rows.length }} 只</span>
          </div>

          <div v-if="section.rows.length === 0" class="empty-hint">
            <span class="empty-icon">—</span>
            <span>暂无鼠号</span>
            <span class="empty-hint-sub">添加或粘贴</span>
          </div>

          <div v-else class="mouse-list">
            <div
              v-for="(row, idx) in section.rows"
              :key="`${section.key}-${idx}`"
              class="mouse-row"
              :class="{ 'mouse-row--dead': !row.alive }"
            >
              <span class="row-index">{{ idx + 1 }}</span>
              <el-input
                v-model="row.no"
                size="small"
                placeholder="鼠号"
                class="mouse-no-input"
              />
              <el-switch
                v-model="row.alive"
                size="small"
                inline-prompt
                active-text="存活"
                inactive-text="死亡"
              />
              <el-button
                type="danger"
                link
                size="small"
                :icon="Delete"
                class="row-delete"
                title="删除"
                @click="removeRow(section.key, idx)"
              />
            </div>
          </div>

          <div class="section-actions">
            <el-button size="small" :icon="Plus" @click="addRow(section.key)">添加</el-button>
            <el-button size="small" :icon="DocumentCopy" plain @click="pasteToSection(section.key)">
              粘贴
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <el-button @click="handleCancel">取消</el-button>
      <el-button type="primary" @click="handleConfirm">确定</el-button>
    </template>
  </el-dialog>
</template>

<script>
import { Delete, DocumentCopy, Plus } from '@element-plus/icons-vue'
import { ElButton, ElDialog, ElInput, ElMessage, ElMessageBox, ElSwitch } from 'element-plus'

/** 剪贴板 / 旧 mouse_no_list：按换行、逗号、顿号等拆分 */
function splitTokens(text) {
  const normalized = (text || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n').trim()
  if (!normalized) return []

  const lines = normalized.split('\n').map((s) => s.trim()).filter(Boolean)
  if (lines.length > 1) return lines

  const line = lines[0]
  if (/[\t,;，、]/.test(line)) {
    return line.split(/[\t,;，、]+/).map((s) => s.trim()).filter(Boolean)
  }
  return [line]
}

function parseSexLayout(sex) {
  const s = (sex || '').trim().toUpperCase()
  if (s === 'F/M' || s === 'F+M') return { mode: 'dual', defaultSex: null }
  if (s === 'F') return { mode: 'single', defaultSex: 'F' }
  if (s === 'M') return { mode: 'single', defaultSex: 'M' }
  return { mode: 'single', defaultSex: null }
}

function normalizeMice(mice) {
  return (mice || [])
    .map((m) => ({
      no: String(m.no || '').trim(),
      sex: m.sex === 'F' || m.sex === 'M' ? m.sex : null,
      alive: m.alive !== false,
    }))
    .filter((m) => m.no)
}

function importLegacyMouseNoList(str, sex) {
  const tokens = splitTokens(str)
  if (!tokens.length) return []
  const layout = parseSexLayout(sex)
  const defaultSex = layout.mode === 'single' ? layout.defaultSex : null
  return tokens.map((no) => ({ no, sex: defaultSex, alive: true }))
}

function formatMouseNoList(mice, sex) {
  const layout = parseSexLayout(sex)
  const list = normalizeMice(mice)

  if (layout.mode === 'dual') {
    const fNos = list.filter((m) => m.sex === 'F').map((m) => m.no)
    const mNos = list.filter((m) => m.sex === 'M').map((m) => m.no)
    const parts = []
    if (fNos.length) parts.push(`F：${fNos.join('、')}`)
    if (mNos.length) parts.push(`M：${mNos.join('、')}`)
    return parts.join('，')
  }

  return list.map((m) => m.no).join('、')
}

function loadMiceFromGroup(group) {
  if (group?.mouse_registry?.mice?.length) {
    return normalizeMice(group.mouse_registry.mice).map((m) => ({ ...m }))
  }
  if ((group?.mouse_no_list || '').trim()) {
    return importLegacyMouseNoList(group.mouse_no_list, group.sex)
  }
  return []
}

function emptyRow(sex) {
  return { no: '', sex, alive: true }
}

export default {
  name: 'MouseRegistryDialog',
  components: {
    ElButton,
    ElDialog,
    ElInput,
    ElSwitch,
  },
  props: {
    modelValue: {
      type: Boolean,
      default: false,
    },
    group: {
      type: Object,
      default: null,
    },
  },
  emits: ['update:modelValue', 'confirm'],
  data() {
    return {
      sections: [],
      Plus,
      DocumentCopy,
      Delete,
    }
  },
  computed: {
    groupId() {
      return (this.group?.group_id || '').trim()
    },
    mouseStrain() {
      return (this.group?.mouse_strain || '').trim()
    },
    isDualLayout() {
      return (
        this.sections.length === 2
        && this.sections.some((s) => s.key === 'F')
        && this.sections.some((s) => s.key === 'M')
      )
    },
    totalEntered() {
      return this.collectMice().length
    },
  },
  methods: {
    handleOpen() {
      this.initSections()
    },
    initSections() {
      const sex = this.group?.sex
      const layout = parseSexLayout(sex)
      const mice = loadMiceFromGroup(this.group)

      if (layout.mode === 'dual') {
        const fRows = mice
          .filter((m) => m.sex === 'F')
          .map((m) => ({ no: m.no, sex: 'F', alive: m.alive !== false }))
        const mRows = mice
          .filter((m) => m.sex === 'M')
          .map((m) => ({ no: m.no, sex: 'M', alive: m.alive !== false }))
        for (const m of mice.filter((x) => x.sex !== 'F' && x.sex !== 'M')) {
          fRows.push({ no: m.no, sex: 'F', alive: m.alive !== false })
        }
        this.sections = [
          { key: 'F', label: '雌性 F', sex: 'F', rows: fRows },
          { key: 'M', label: '雄性 M', sex: 'M', rows: mRows },
        ]
        return
      }

      const defaultSex = layout.defaultSex
      const label = defaultSex === 'F' ? '雌性 F' : defaultSex === 'M' ? '雄性 M' : '鼠号'
      const sectionKey = defaultSex === 'F' ? 'F' : defaultSex === 'M' ? 'M' : 'all'
      const rows = mice.map((m) => ({
        no: m.no,
        sex: m.sex || defaultSex,
        alive: m.alive !== false,
      }))
      this.sections = [{ key: sectionKey, label, sex: defaultSex, rows }]
    },
    addRow(sectionKey) {
      const section = this.sections.find((s) => s.key === sectionKey)
      if (!section) return
      section.rows.push(emptyRow(section.sex))
    },
    removeRow(sectionKey, idx) {
      const section = this.sections.find((s) => s.key === sectionKey)
      if (!section) return
      section.rows.splice(idx, 1)
    },
    async pasteToSection(sectionKey) {
      const section = this.sections.find((s) => s.key === sectionKey)
      if (!section) return

      let text = ''
      try {
        if (navigator.clipboard?.readText) {
          text = await navigator.clipboard.readText()
        }
      } catch {
        /* use prompt fallback */
      }

      if (!text?.trim()) {
        try {
          const { value } = await ElMessageBox.prompt('粘贴鼠号（多行或逗号、顿号分隔）', '从剪贴板粘贴', {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            inputType: 'textarea',
          })
          text = value || ''
        } catch {
          return
        }
      }

      const tokens = splitTokens(text)
      if (!tokens.length) {
        ElMessage.warning('未识别到鼠号')
        return
      }
      for (const no of tokens) {
        section.rows.push({ no, sex: section.sex, alive: true })
      }
      ElMessage.success(`已添加 ${tokens.length} 个鼠号`)
    },
    collectMice() {
      const result = []
      for (const section of this.sections) {
        for (const row of section.rows) {
          const no = (row.no || '').trim()
          if (!no) continue
          result.push({
            no,
            sex: section.sex,
            alive: row.alive !== false,
          })
        }
      }
      return result
    },
    handleCancel() {
      this.$emit('update:modelValue', false)
    },
    handleConfirm() {
      const mice = this.collectMice()
      const sex = this.group?.sex
      const mouse_registry = { mice: normalizeMice(mice) }
      const mouse_no_list = formatMouseNoList(mice, sex)
      this.$emit('confirm', { mouse_registry, mouse_no_list })
      this.$emit('update:modelValue', false)
    },
  },
}
</script>

<style scoped>
.dialog-header {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px 16px;
  padding-right: 28px;
}

.dialog-header-title {
  margin: 0;
  flex-shrink: 0;
  font-size: 16px;
  font-weight: 600;
  line-height: 1.4;
  color: #303133;
}

.dialog-header-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  min-width: 0;
  font-size: 12px;
  line-height: 1.4;
}

.meta-label {
  color: #a8abb2;
}

.meta-group {
  font-weight: 600;
  color: #67c23a;
}

.meta-sep {
  margin: 0 2px;
  color: #dcdfe6;
}

.meta-strain {
  max-width: min(280px, 50vw);
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dialog-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.summary-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  font-size: 13px;
  background: #f5f7fa;
  border: 1px solid #ebeef5;
  border-radius: 999px;
}

.chip-label {
  font-size: 12px;
  color: #909399;
}

.chip-value {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
}

.sections-layout {
  display: block;
}

.sections-layout--dual {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  align-items: stretch;
}

.sections-layout--dual .registry-section {
  margin-bottom: 0;
  min-width: 0;
}

.registry-section {
  margin-bottom: 0;
}

.section-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 200px;
  padding: 12px 14px;
  background: #fafbfc;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
}

.section-card--f {
  border-color: #fde2e2;
  background: linear-gradient(180deg, #fffbfb 0%, #fafbfc 48px);
}

.section-card--m {
  border-color: #d9ecff;
  background: linear-gradient(180deg, #f8fbff 0%, #fafbfc 48px);
}

.section-card--all {
  border-color: #e4e7ed;
  background: linear-gradient(180deg, #f8f9fa 0%, #fafbfc 48px);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f2f5;
}

.sex-tag {
  font-size: 14px;
  font-weight: 600;
}

.sex-tag--f {
  color: #f56c6c;
}

.sex-tag--m {
  color: #409eff;
}

.sex-tag--all {
  color: #606266;
}

.section-count {
  font-size: 12px;
  color: #909399;
  background: #f5f7fa;
  padding: 2px 8px;
  border-radius: 10px;
}

.empty-hint {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-height: 120px;
  font-size: 13px;
  color: #909399;
}

.empty-icon {
  font-size: 20px;
  color: #dcdfe6;
  line-height: 1;
}

.empty-hint-sub {
  font-size: 12px;
  color: #c0c4cc;
}

.mouse-list {
  flex: 1;
  max-height: 260px;
  margin-bottom: 10px;
  overflow-y: auto;
  padding-right: 2px;
}

.sections-layout--dual .mouse-list {
  max-height: 300px;
}

.mouse-list::-webkit-scrollbar {
  width: 5px;
}

.mouse-list::-webkit-scrollbar-thumb {
  background: #dcdfe6;
  border-radius: 3px;
}

.mouse-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  padding: 5px 6px;
  background: #fafafa;
  border-radius: 6px;
  transition: background 0.15s;
}

.mouse-row:hover {
  background: #f5f7fa;
}

.mouse-row--dead {
  background: #fef0f0;
}

.mouse-row--dead:hover {
  background: #fde2e2;
}

.mouse-row--dead .mouse-no-input :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px #fde2e2 inset;
}

.row-index {
  flex-shrink: 0;
  width: 20px;
  font-size: 11px;
  color: #c0c4cc;
  text-align: center;
}

.mouse-no-input {
  flex: 1 1 0;
  min-width: 64px;
}


.mouse-row :deep(.el-switch__core) {
  width: 50px;
  min-width: 50px;
}


.row-delete {
  flex-shrink: 0;
  padding: 4px;
}

.section-actions {
  display: flex;
  gap: 8px;
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px solid #f0f2f5;
}

.sections-layout--dual .section-actions {
  flex-direction: column;
}

.sections-layout--dual .section-actions .el-button {
  width: 100%;
  margin: 0;
}

.mouse-registry-dialog :deep(.el-dialog__header) {
  margin-right: 0;
  padding: 16px 20px 14px;
  border-bottom: 1px solid #f0f2f5;
}

.mouse-registry-dialog :deep(.el-dialog__headerbtn) {
  top: 14px;
  right: 14px;
}

.mouse-registry-dialog :deep(.el-dialog__body) {
  padding: 14px 20px 10px;
}
</style>
