<template>
  <div class="titer-conclusion-panel">
    <div v-if="!hasData" class="conclusion-empty">
      <el-icon><DataAnalysis /></el-icon>
      <p>暂无效价结论数据</p>
      <span class="sub-text">请先在 TITER 板管理中新建 FACS/ELISA 板并完成阳性孔标注</span>
    </div>

    <template v-else>
      <el-alert
        v-for="(msg, idx) in warnings"
        :key="'warn-' + idx"
        :title="msg"
        type="warning"
        show-icon
        :closable="false"
        class="conclusion-warn"
      />

      <el-tabs v-model="activeStage" type="card" class="stage-tabs">
        <el-tab-pane
          v-for="tab in stageMethodTabs"
          :key="tab.key"
          :label="tab.label"
          :name="tab.key"
        >
          <div
            v-for="table in tab.groupTables"
            :key="table.groupId"
            class="group-table-block"
          >
            <div class="group-table-title">
              <template v-if="isUngrouped(table)">
                <span class="group-chip group-chip--primary">{{ table.antigenLabel }}</span>
              </template>
              <template v-else>
                <span class="group-chip group-chip--primary">
                  组别 {{ table.groupDisplayLabel || table.groupId }}
                </span>
                <span
                  v-if="showGroupAntigen(table)"
                  class="group-chip group-chip--plain"
                  :title="table.antigenLabel"
                >
                  {{ table.antigenLabel }}
                </span>
              </template>
            </div>
            <el-table
              :data="table.rows"
              border
              size="small"
              class="conclusion-table"
            >
              <el-table-column
                label="检测标靶（鼠号）"
                min-width="200"
                fixed="left"
                class-name="target-col-cell"
              >
                <template #default="{ row }">
                  <div class="target-cell-line">
                    <template v-if="row.speciesTiterLabel">
                      <span class="meta-titer">{{ row.speciesTiterLabel }}</span>
                      <span class="meta-sep">|</span>
                    </template>
                    <span class="meta-target" :title="row.targetName">{{ row.targetName }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column
                v-for="mouseNo in table.mouseColumns"
                :key="mouseNo"
                :label="mouseNo"
                min-width="72"
                align="center"
              >
                <template #default="{ row }">
                  <span class="cell-value" :class="cellClass(row.cells[mouseNo])">
                    {{ formatCell(row.cells[mouseNo]) }}
                  </span>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </template>
  </div>
</template>

<script>
import { DataAnalysis } from '@element-plus/icons-vue'
import { ElAlert, ElIcon, ElTabPane, ElTable, ElTableColumn, ElTabs } from 'element-plus'
import {
  formatConclusionCell,
  UNGROUPED_GROUP_ID,
} from '#/utils/serumTiterConclusion'

export default {
  name: 'TiterConclusionPanel',
  components: {
    DataAnalysis,
    ElAlert,
    ElIcon,
    ElTabPane,
    ElTable,
    ElTableColumn,
    ElTabs,
  },
  props: {
    model: {
      type: Object,
      default: null,
    },
  },
  data() {
    return {
      activeStage: '',
    }
  },
  computed: {
    stages() {
      return this.model?.stages || []
    },
    warnings() {
      return this.model?.warnings || []
    },
    hasData() {
      return this.stageMethodTabs.length > 0
    },
    stageMethodTabs() {
      const facs = []
      const elisa = []
      for (const stage of this.stages) {
        const facsBlock = stage.methods?.find((m) => m.method === 'FACS')
        if (facsBlock?.groupTables?.length) {
          facs.push({
            key: `FACS::${stage.stageName}`,
            label: `FACS · ${stage.stageName}`,
            method: 'FACS',
            stageName: stage.stageName,
            groupTables: facsBlock.groupTables,
          })
        }
        const elisaBlock = stage.methods?.find((m) => m.method === 'ELISA')
        if (elisaBlock?.groupTables?.length) {
          elisa.push({
            key: `ELISA::${stage.stageName}`,
            label: `ELISA · ${stage.stageName}`,
            method: 'ELISA',
            stageName: stage.stageName,
            groupTables: elisaBlock.groupTables,
          })
        }
      }
      return [...facs, ...elisa]
    },
    stageNamesKey() {
      return this.stageMethodTabs.map((t) => t.key).join('||')
    },
  },
  watch: {
    stageNamesKey: {
      handler(key) {
        if (!key) {
          this.activeStage = ''
          return
        }
        const names = key.split('||')
        if (!names.includes(this.activeStage)) {
          this.activeStage = names[0]
        }
      },
      immediate: true,
    },
  },
  methods: {
    isUngrouped(table) {
      return table.groupId === UNGROUPED_GROUP_ID
    },
    showGroupAntigen(table) {
      const label = (table.antigenLabel || '').trim()
      return label && label !== table.groupId
    },
    formatCell(value) {
      if (value === undefined || value === null) return 'N/A'
      return formatConclusionCell(value)
    },
    cellClass(value) {
      if (value === 'N/A') return 'is-na'
      if (value === '-') return 'is-negative'
      return 'is-positive'
    },
  },
}
</script>

<style scoped>
.titer-conclusion-panel {
  width: 100%;
  font-size: 13px;
}

.conclusion-warn {
  margin-bottom: 14px;
}

.conclusion-warn :deep(.el-alert__title) {
  font-size: 13px;
}

.conclusion-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 16px;
  color: #c0c4cc;
}

.conclusion-empty .el-icon {
  font-size: 48px;
  margin-bottom: 12px;
  opacity: 0.5;
  color: #a0cfff;
}

.conclusion-empty p {
  margin: 0 0 6px;
  font-size: 15px;
  color: #909399;
  font-weight: 500;
}

.conclusion-empty .sub-text {
  font-size: 13px;
  color: #c0c4cc;
}

/* 与 TITER 板管理 tabs 一致 */
.stage-tabs :deep(.el-tabs__header) {
  margin: 0 0 14px;
}

.stage-tabs :deep(.el-tabs__nav-wrap) {
  padding: 0;
}

.stage-tabs :deep(.el-tabs__item) {
  font-size: 14px;
  height: 38px;
  line-height: 38px;
  padding: 0 18px;
}

.stage-tabs :deep(.el-tabs__item:hover) {
  color: #409eff;
}

.stage-tabs :deep(.el-tabs__item.is-active) {
  color: #409eff;
  font-weight: 600;
}

.stage-tabs :deep(.el-tabs__content) {
  padding: 0;
}

.group-table-block {
  margin-bottom: 14px;
  padding: 12px 14px;
  background: #fbfcfd;
  border: 1px solid #eef1f6;
  border-radius: 8px;
}

.group-table-block:last-child {
  margin-bottom: 0;
}

/* 与鼠号明细弹窗 / FACS 信息区 meta 行一致 */
.group-table-title {
  margin-bottom: 11px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  min-height: 22px;
}

.group-chip {
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  padding: 3px 10px;
  border-radius: 999px;
  border: 1px solid #dfe4ea;
  background: #f7f9fc;
  line-height: 1.2;
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
}

.group-chip--primary {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  border-color: #d2d8e0;
  background: #f2f5f9;
}

.group-chip--plain {
  font-size: 13px;
  font-weight: 500;
  color: #7b8490;
}

/* 与页内 refined-table 一致 */
.conclusion-table {
  width: 100%;
  border-radius: 4px;
  overflow: hidden;
}

.conclusion-table :deep(.target-col-cell .cell) {
  line-height: 1.4;
}

.target-cell-line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  min-width: 0;
  line-height: 1.4;
}

.meta-titer {
  flex-shrink: 0;
  font-size: 13px;
  font-weight: 600;
  color: #67c23a;
}

.meta-target {
  font-size: 13px;
  min-width: 0;
  color: #606266;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conclusion-table :deep(.el-table__header-wrapper th) {
  background-color: #f8f9fb;
  color: #606266;
  font-weight: 600;
  height: 32px;
  border-bottom: 1px solid #eef1f6;
}

.conclusion-table :deep(.el-table__row td) {
  height: 32px;
  border-bottom: 1px solid #f0f0f0;
  color: #606266;
}

.conclusion-table :deep(.el-table__body tr:hover > td) {
  background-color: #f5f9ff;
}

.cell-value {
  font-size: 13px;
}

.cell-value.is-na {
  color: #c0c4cc;
}

.cell-value.is-negative {
  color: #909399;
}

.cell-value.is-positive {
  color: #606266;
  font-weight: 600;
}
</style>
