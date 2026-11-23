<script setup>
/**
 * Excel 视图的表格外壳：外层划选容器、vxe-table、四种标准列（靶点 / 多值 / 选择 / 普通）、选区遮罩和拖列指示。
 * 状态和事件全部来自页面混入的 sheetSelectionMixin（只读）或 workbenchExcelMixin（可编辑），组件经 inject 取用，
 * 挂载时把表格和遮罩元素登记回页面（attachSheetView），混入里用 sheetEl(name) 取。
 *
 * 插槽：
 * - columns：整组列自己写（只读表格如引物库），不渲染标准列。
 * - column：页面覆写 isSheetCustomColumn(column) 为 true 的列，参数 { column }。
 * - picker：选择列双击时页面自带的编辑器，页面覆写 isSheetCustomPicker(column, row)，参数 { row, column }。
 * - cell-<列键>：该列的单元格展示，参数 { row, column }。
 * - actions：右侧固定操作列，参数 { row }。
 * - range-overlay：选区遮罩里的附加内容（如填充柄）。
 * 其余属性（header-cell-style、row-class-name、empty-text、事件等）透传给 vxe-table，可覆盖默认配置。
 */
import { inject, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElOption } from 'element-plus'
import { VxeInput, VxeSelect } from 'vxe-pc-ui'
import { VxeColumn, VxeTable } from 'vxe-table'

import ListFilterSelect from '#/components/ListFilterSelect.vue'
import '#/adapter/vxe-table'
import 'vxe-pc-ui/styles/cssvar.scss'
import 'vxe-table/styles/cssvar.scss'

import { WorkbenchHeaderLabel } from './workbenchHeaderMenu'

defineOptions({ inheritAttrs: false })

defineProps({
  actionsWidth: { type: [Number, String], default: 240 },
})

const host = inject('workbenchSheetHost')
const wrap = ref(null)
const stage = ref(null)
const table = ref(null)
const rangeOverlay = ref(null)
const dropLine = ref(null)
const ghost = ref(null)
const selectEditor = ref(null)
const elements = { wrap, stage, table, rangeOverlay, dropLine, ghost, selectEditor }
const view = Object.freeze(Object.fromEntries(
  Object.keys(elements).map((name) => [name, () => elements[name].value]),
))

function onDocumentKeydown(event) {
  host.onSheetDocumentKeydown?.(event)
}

onMounted(() => {
  host.attachSheetView(view)
  document.addEventListener('keydown', onDocumentKeydown, true)
})
onBeforeUnmount(() => {
  host.detachSheetView(view)
  document.removeEventListener('keydown', onDocumentKeydown, true)
})

function minWidth(column) {
  return column.minWidth || column.width || 120
}

function setSelectEditor(el) {
  selectEditor.value = el
}
</script>

<template>
  <div
    ref="wrap"
    class="sheet-wrap"
    :class="{ 'is-column-moving': host.sheetDragMode === 'move-column' }"
    tabindex="0"
    @copy="host.onSheetCopy"
    @paste="host.onSheetPaste"
    @dblclick.capture="host.onSheetDblClickCapture"
    @keydown.capture="host.onSheetKeydownCapture"
    @compositionend.capture="host.onSheetCompositionEnd"
    @mousedown="host.onSheetWrapMouseDown"
    @click="host.onSheetHeaderMenuClick"
    @mouseover="host.onSheetWrapMouseOver"
    @contextmenu="host.onSheetWrapContextMenu"
    @selectstart="host.onSheetSelectStart"
  >
    <div ref="stage" class="sheet-table-stage">
      <VxeTable
        :key="host.sheetColumnOrderKey"
        ref="table"
        v-loading="host.loading"
        :height="host.listTableHeight"
        :data="host.list"
        border
        show-overflow
        size="small"
        :row-config="host.sheetRowConfig"
        :cell-config="host.sheetCellConfig"
        :column-config="host.sheetColumnConfig"
        :mouse-config="host.sheetMouseConfig"
        :keyboard-config="host.sheetKeyboardConfig"
        :virtual-y-config="host.sheetVirtualYConfig"
        :virtual-x-config="host.sheetVirtualXConfig"
        :edit-config="host.sheetEditConfig"
        :header-cell-class-name="host.sheetHeaderCellClassName"
        :cell-class-name="host.sheetCellClass"
        v-bind="$attrs"
        @scroll="host.onSheetScroll"
        @column-resizable-change="host.onSheetColumnResize"
        @cell-selected="host.onSheetCellSelected"
        @edit-actived="host.onSheetEditActived"
        @edit-closed="host.onSheetEditClosed"
        @cell-delete-value="host.onSheetEditClosed"
      >
        <slot name="columns">
          <template v-for="column in host.sheetColumns" :key="column.key">
            <slot v-if="host.isSheetCustomColumn(column)" name="column" :column="column" />
            <VxeColumn
              v-else-if="column.edit === 'target'"
              :field="column.key"
              :title="host.sheetColumnTitle(column)"
              :width="host.sheetColumnWidth(column)"
              :min-width="minWidth(column)"
              :edit-render="host.sheetCustomEditRender"
              :formatter="host.sheetFormatter(column)"
            >
              <template v-if="host.headerMenuStates?.[column.key]" #header>
                <WorkbenchHeaderLabel :label="column.label" v-bind="host.headerMenuStates[column.key]" />
              </template>
              <template v-if="$slots[`cell-${column.key}`]" #default="{ row }">
                <slot :name="`cell-${column.key}`" :row="row" :column="column" />
              </template>
              <template #edit="{ row }">
                <div v-if="host.sheetEditSource === 'dblclick'" class="sheet-picker-editor">
                  <span class="sheet-picker-editor__value">{{ host.sheetPickerDisplayValue(row, column) }}</span>
                  <VxeSelect
                    v-model="row.target_codes"
                    class-name="sheet-grid-editor sheet-picker-control"
                    filterable
                    multiple
                    remote
                    :options="host.sheetTargetSelectOptions"
                    :popup-config="host.sheetTargetPopupConfig"
                    :remote-config="host.sheetTargetRemoteConfig"
                    empty-text="未找到匹配靶点"
                    @change="host.onSheetTargetPickerChange(row)"
                    @visible-change="host.onSheetPickerVisibleChange"
                  />
                </div>
                <VxeInput
                  v-else
                  :model-value="host.sheetTargetDirectValue(row, column.key)"
                  class-name="sheet-grid-editor"
                  @update:model-value="host.setSheetTargetDirectValue(row, column.key, $event)"
                />
              </template>
            </VxeColumn>
            <VxeColumn
              v-else-if="column.edit === 'tags'"
              :field="column.key"
              :title="host.sheetColumnTitle(column)"
              :width="host.sheetColumnWidth(column)"
              :min-width="minWidth(column)"
              :edit-render="host.sheetCustomEditRender"
              :formatter="host.sheetFormatter(column)"
            >
              <template v-if="host.headerMenuStates?.[column.key]" #header>
                <WorkbenchHeaderLabel :label="column.label" v-bind="host.headerMenuStates[column.key]" />
              </template>
              <template v-if="$slots[`cell-${column.key}`]" #default="{ row }">
                <slot :name="`cell-${column.key}`" :row="row" :column="column" />
              </template>
              <template #edit="{ row }">
                <ListFilterSelect
                  v-if="host.sheetEditSource === 'dblclick'"
                  :ref="setSelectEditor"
                  :model-value="host.sheetTagValues(row, column)"
                  joined
                  filterable
                  allow-create
                  default-first-option
                  clearable
                  class="sheet-category-select"
                  popper-class="vxe-table--ignore-clear"
                  @change="host.onSheetTagsChange(row, column, $event)"
                  @visible-change="host.onSheetSelectVisible"
                >
                  <ElOption v-for="item in host.sheetTagOptions(row, column)" :key="item" :label="item" :value="item" />
                </ListFilterSelect>
                <VxeInput
                  v-else
                  :model-value="host.sheetChoiceDirectValue(row, column)"
                  class-name="sheet-grid-editor"
                  @update:model-value="host.setSheetChoiceDirectValue(row, column, $event)"
                />
              </template>
            </VxeColumn>
            <VxeColumn
              v-else-if="host.isSheetChoiceColumn(column)"
              :field="column.key"
              :title="host.sheetColumnTitle(column)"
              :width="host.sheetColumnWidth(column)"
              :min-width="minWidth(column)"
              :edit-render="host.sheetCustomEditRender"
              :formatter="host.sheetFormatter(column)"
            >
              <template v-if="host.headerMenuStates?.[column.key]" #header>
                <WorkbenchHeaderLabel :label="column.label" v-bind="host.headerMenuStates[column.key]" />
              </template>
              <template v-if="$slots[`cell-${column.key}`]" #default="{ row }">
                <slot :name="`cell-${column.key}`" :row="row" :column="column" />
              </template>
              <template #edit="{ row }">
                <slot
                  v-if="host.sheetEditSource === 'dblclick' && host.isSheetCustomPicker(column, row)"
                  name="picker"
                  :row="row"
                  :column="column"
                />
                <div
                  v-else-if="host.sheetEditSource === 'dblclick' && host.isSheetPickerCell(column, row)"
                  class="sheet-picker-editor"
                >
                  <span class="sheet-picker-editor__value">{{ host.sheetPickerDisplayValue(row, column) }}</span>
                  <VxeSelect
                    v-model="row[host.sheetChoiceModelKey(column)]"
                    class-name="sheet-grid-editor sheet-picker-control"
                    :filterable="host.isUserColumn(column)"
                    :multiple="host.isSheetMultiColumn(column)"
                    :clearable="host.sheetChoiceClearable(column)"
                    :options="host.sheetChoiceSelectOptions(column, row)"
                    :popup-config="host.sheetChoicePopupConfig"
                    @visible-change="host.onSheetPickerVisibleChange"
                  />
                </div>
                <VxeInput
                  v-else
                  :model-value="host.sheetChoiceDirectValue(row, column)"
                  class-name="sheet-grid-editor"
                  @update:model-value="host.setSheetChoiceDirectValue(row, column, $event)"
                />
              </template>
            </VxeColumn>
            <VxeColumn
              v-else
              :field="column.key"
              :title="host.sheetColumnTitle(column)"
              :width="host.sheetColumnWidth(column)"
              :min-width="minWidth(column)"
              :align="column.align"
              :header-align="column.align"
              :edit-render="host.sheetEditRender(column)"
              :formatter="host.sheetFormatter(column)"
            >
              <template v-if="host.headerMenuStates?.[column.key]" #header>
                <WorkbenchHeaderLabel :label="column.label" v-bind="host.headerMenuStates[column.key]" />
              </template>
              <template v-if="$slots[`cell-${column.key}`]" #default="{ row }">
                <slot :name="`cell-${column.key}`" :row="row" :column="column" />
              </template>
            </VxeColumn>
          </template>
        </slot>
        <VxeColumn v-if="$slots.actions" title="操作" :width="actionsWidth" fixed="right" align="center">
          <template #default="{ row }">
            <slot name="actions" :row="row" />
          </template>
        </VxeColumn>
      </VxeTable>
      <div ref="rangeOverlay" class="sheet-range-overlay" aria-hidden="true">
        <slot name="range-overlay" />
      </div>
      <div ref="dropLine" class="sheet-column-drop-line" aria-hidden="true" />
      <div ref="ghost" class="sheet-column-ghost" aria-hidden="true" />
    </div>
  </div>
</template>

<style scoped src="./workbenchExcel.css"></style>
