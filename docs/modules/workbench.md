# 项目工作台共用约定

> 适用页面：免疫工作台、发现工作台、发现合成与验证、文库构建、转染与表达使用工作台 / Excel 双视图；免疫实验列表、效价实验列表、流式工单列表、引物库、转染表也使用共用表头菜单。模块事实见 [免疫工作台](./immunology/workbench.md) 与 [发现工作台](./discovery/workbench.md)。

## 页面模式

一级表单页按功能组合模块：要哪项功能就混入哪一层，不要的不混入，页面里不写开关。

| 功能 | 模块 | 免疫工作台 / 发现工作台 / 合成与验证 | 文库构建 / 转染与表达 | 引物库 / 转染表 |
|---|---|---|---|---|
| 划选、复制 | `sheetSelectionMixin`（`workbenchExcelMixin` 已带） | 有 | 有 | 有 |
| Excel 编辑、粘贴、双视图 | `workbenchExcelMixin`、`WorkbenchViewToggle` | 有 | 有 | 无（只读表格） |
| 队列排序 | `workbenchQueueSortMixin`、`WorkbenchSortHeader`、`WorkbenchSortCell` | 有 | 无 | 无 |
| 编辑抽屉 | `workbenchDrawerMixin`、`WorkbenchDrawer` | 有 | 有 | 无 |
| 靶点 | `workbenchTargetMixin`、`WorkbenchTargetSelect` | 有 | 有 | 无 |
| 顶部面板 | 工作台模式 `workbenchConsole.css`（标题和阶段卡片同一张卡，筛选另一张），实验模式 `workbenchPanel.css`（标题带一张卡、每个统计块各一张小卡、筛选条一张卡） | 工作台模式 | 实验模式 | 实验模式 |

混入顺序：`workbenchExcelMixin` 在前，`workbenchQueueSortMixin` 紧随其后（它把行选择列和首列固定改成 `sort_order`）。不排序的页面把 `excelRowSelectKey` 设成自己的首列（如 `id`）。

### 组件选项

接口、字段和列写在组件选项里，混入从 `this.$options` 读取，页面只保留实际业务方法：

| 选项 | 内容 | 读取方 |
|---|---|---|
| `workbenchApi` | `list`、`save`、`saveBatch`、`remove`、`export` / `exportName`、`columnValues`、`reorder`，以及各环节的错误文案 `errors: { load, remove, export, save }` | `workbenchCrudMixin`（列表、删除、导出、`submitRowFields`、`fetchHeaderValues`）、`workbenchExcelMixin`（多格保存）、`workbenchQueueSortMixin`（拖行） |
| `workbenchFields` | `fieldSchema.js` 的 `defineFields` 结果 | 校验、抽屉、请求体 |
| `workbenchSheet` | `{ columns, order, aliases }`：Excel 的全部列、`createColumnOrder` 实例、旧表头别名 | `sheetSelectionMixin`（`sheetColumns` 初值、列序列宽记忆）、`workbenchExcelMixin`（带表头粘贴时识别列） |
| `listFilterKey` | 筛选暂存键 | `listPageMixin` |

视图模式由 `workbenchExcelMixin` 按页面 `name` 记住，切走再回来恢复上次的视图（刷新浏览器后回到工作台视图）；人员名单 `allUserOptions` 切到 Excel 视图时才加载。`viewMode`、`allUserOptions`、`sheetColumns` 由混入提供。

免疫实验列表、效价实验列表只复用表头菜单和靶点筛选（效价实验列表另用顶部面板）；公共模块不为它们加分支，兼容不了的留在页面里。流式工单列表只用顶部面板和表头菜单。

## 组件清单

| 组件 | 职责 | 使用页面 |
|---|---|---|
| `WorkbenchDataTable.vue` | 工作台表格、显示字段、固定首末列、`Shift` 拖列表头 | 免疫、发现、合成与验证、文库构建、转染与表达 |
| `WorkbenchViewToggle.vue`、`viewMode.js` | 切换 `workbench` / `excel`；右键恢复当前视图列设置 | 同上 |
| `columnOrder.js` | `createColumnOrder` 持久化 `{ order, hidden, widths, colors }`，合并新增列并保持固定列 | 双视图页面、引物库、转染表 |
| `WorkbenchSheet.vue`、`workbenchExcel.css` | Excel 表格外壳：外层划选容器、vxe-table 和全部配置事件、三种标准列（靶点 / 选择 / 普通）、选区遮罩和拖列指示；样式只在这里引入 | 双视图页面、引物库、转染表 |
| `sheetSelectionMixin.js` | 只读划选层：选区、复制、整行/整列选择、`Shift` 拖列、列宽和列序记忆 | 引物库、转染表；其余经 `workbenchExcelMixin` 带入 |
| `workbenchExcelMixin.js` | 编辑层（含划选层）：键入、双击编辑、删除、粘贴保存、视图切换、日期和选项校验 | 双视图页面 |
| `workbenchCrudMixin.js` | 列表加载、删除、导出、表头取值，逐字段保存的提交与失败回退（`submitRowFields`） | 双视图页面 |
| `WorkbenchPriorityCell.vue` | 工作台视图的优先级格：可改时行内下拉，不可改时标签，按档位着色；样式在组件里 | 双视图页面 |
| `textareaHeights.js` 的 `syncTextareaHeights(selector)` | 同排多行文本对齐到最高的一个（只有一个时按内容撑高） | 抽屉、文库构建结果页 |
| `workbenchQueueSortMixin.js`、`WorkbenchSortHeader.vue`、`WorkbenchSortCell.vue` | 队列排序：表头切换队列序、排序列显示与改号、工作台视图拖行、锁定提示 | 免疫、发现、合成与验证 |
| `workbenchDrawerMixin.js`、`WorkbenchDrawer.vue`、`workbenchDrawer.css` | 无遮罩编辑抽屉：逐字段保存、按行排队、兜底补存；外壳负责标题栏、上一条 / 下一条、分组卡片 | 双视图页面 |
| `WorkbenchDrawerField.vue` | 抽屉标准字段控件：日期、靶点、靶点编号、人员、下拉、多行文本、数字和单行文本 | 双视图页面 |
| `WorkbenchLineInput.vue` | 一行一项的多行文本框：不自动折行，框高等于行数，不显示滚动条，长行用光标、拖选、Shift+滚轮或触控板左右滚动，失焦回行首；用法同 `ElInput` | 发现（板号、抗原、冲击免细胞）、文库构建与转染与表达（板号） |
| `workbenchPanel.css` | 实验模式顶部：渐变标题卡；统计块每个一张白卡片，直接放在页面底色上，左侧色条和阴影取 `stat-*` 色调或 `--stat-accent`；筛选卡。用得少的筛选放进高级操作栏 | 文库构建、转染与表达、效价实验列表、流式工单列表、引物库、转染表 |
| `WorkbenchHeaderMenu.vue`、`workbenchHeaderMenu.js` | 表头取值筛选、条件筛选、颜色筛选和排序 | 上述双视图页面、免疫实验列表、效价实验列表、流式工单列表、引物库、转染表 |
| `WorkbenchStatusEditor.vue` | 行内状态选择 | 双视图页面、文库构建结果页 |
| `WorkbenchMultiTagEditor.vue` | 行内多选标签 | 发现 |
| `WorkbenchTargetSelect.vue`、`workbenchTargetMixin.js` | 编辑区远程选靶点，联动名称与编号；粘贴时统一解析靶点 | 双视图页面（抽屉里经 `WorkbenchDrawerField`）、文库构建结果页、流式工单编辑 |
| `WorkbenchTargetFilter.vue` | 调用页面的 `GET /recorded_targets` 搜索已录入靶点，并保留已选项显示名 | 双视图页面、免疫实验列表、效价实验列表 |
| `WorkbenchColorMark.vue` | 单元格底色标记 | 发现合成与验证 |

## 抽屉保存约定

全站只有一种保存方式：**字段改完就保存这一个字段**（选择类 `@change`、输入类 `@blur`），不在关闭时攒一批再提交。关闭、切行、做行操作、刷新列表、切换视图前，`flushDrawer` 兜底：先让正在输入的框失焦走自己的保存，再把副本里和基线不同的字段补存，最后等这一行的保存全部完成。

选逐字段保存是因为：改完即入库，别人刷新就能看到；保存失败能定位到具体字段并当场退回；和 Excel 单格编辑、行内下拉走同一个入口，不会出现两条保存路径各管一部分。

页面要做的：

- 混入 `workbenchDrawerMixin`，模板放 `WorkbenchDrawer`，`#field` 插槽里标准字段一行 `<WorkbenchDrawerField v-bind="drawerFieldBind(field)" />`，页面特有的控件（多选标签、引物矩阵等）用 `v-if` 写在它前面；`#actions` 放行操作按钮，`#meta` 放标题下摘要，明细表等放 `#after-fields`。
- 字段定义的 `type` 决定控件：`date`、`target`（靶点选择，联动名称和编号）、`target_codes`（只读编号）、`user`、`select`、`textarea`、`number`，缺省单行文本；`sync: true` 的文本与同排对齐高度（同排只有一个时按内容撑高），`nowrap: true` 的多行文本一行一项、改用 `WorkbenchLineInput`，`maxlength`、`resize`、`clearable: false`、`allowCreate` 写在字段上。终态行的排序号显示 `-`。
- 字段控件的钩子都有默认实现，按需覆写：`drawerFieldOptions(field, row)`（下拉选项，默认 `field.options`）、`drawerUserOptions(field, row)`、`drawerSelectClass(field, row)`（下拉色调；优先级默认按档位着色，页面只管自己的字段）、`drawerSelectProps(field, row)`（可清空、可搜索、可新建）、`isDrawerFieldDisabled(field, row)`（默认看 `canEditField`）、`drawerFieldValue(field, row)`。
- 外观参数：`size` 宽度默认 `520px`、`label-width` 默认 `80px`，字段特别多的页面自行加宽（文库构建 560px / 92px）；分组小标题默认不带色条，要的页面写 `title-mark`（文库构建），单个分组在 `editorSections` 里写 `mark: true` / `mark: false` 覆盖。
- 提供 `editorSections`（名字固定，兜底补存按它找字段；开发环境缺了会在控制台警告）、`canEditField(row, key)`。列表行原样使用接口返回值，数组、状态和优先级默认值由后端序列化和数据库默认值保证，前端不补形。
- 实现 `saveRowField(row, field, options)`：只保存这一个字段（靶点名称和编号一起）。标准写法是 `normalizeDrawerValue` 校验，`rowFieldsUnchanged(row, keys)` 为真时直接返回，最后 `return this.submitRowFields(row, keys, options)`；页面只在中间加自己的联动字段（如审核人、质检人）。没改值或校验不过返回 `undefined`，不算失败。
- `submitRowFields(row, fields, { save, messages, applyFields, reload })`：先把列表行的新值同步到打开着的抽屉副本，再调 `workbenchApi.save(rowSavePayload(row, fields))`；成功后 `applySavedFields(saved, applyFields)` 并返回保存结果（`applyFields` 默认就是 `fields`，传 `null` 整行回填）；失败按 `messages`（默认 `workbenchApi.errors.save`）提示，带上 `reload` 静默刷新列表，再 `revertDrawerFields` 退回这几个字段并返回 `null`，免得兜底补存再提交一次。保存前要确认的（如合成的完成确认）传 `save` 换掉保存函数。
- 所有保存都调 `persistRow(row, field)`，它按行排队后再调 `saveRowField`，避免后发先至。行内下拉直接改值用 `persistRowValue(row, key, value)`（写值后 `persistRow`，返回保存结果），状态、优先级都这样接。前一个保存回填时，`patchExistingListRow` 不覆盖同一行仍在排队的字段，用户刚改的值不会被旧结果冲掉。
- `getList({ flushEditor = true, silent = false })`：`flushEditor` 时先 `await this.flushAllEdits()`，表格或抽屉有存不上的编辑（失败已在保存处提示）就不刷新、返回 `false`；拿到数据赋给 `list` 后调 `acceptListRows()`，抽屉副本里没改过的字段换成新数据，再记基线。抽屉里的已入库行不在新列表里（被删、被筛掉）时关闭抽屉；未入库草稿不受影响。
- `type: 'target'` 的字段由 `WorkbenchDrawerField` 自动接 `onDrawerTargetChange`（`workbenchTargetMixin` 提供），编号和名称一起保存；自己写 `WorkbenchTargetSelect` 时绑 `@change="onDrawerTargetChange(editingRow, $event)"`。
- 行操作（交接、质检等）开头 `if (!await this.flushEditorForAction(row)) return`；删除成功后 `discardDrawer(row.id)`，不执行补存。
- 可覆写：`drawerComparable`（字段比较值）、`drawerValueKeys`（一个字段占用的多个值键，如筛选方法的文本和数组）、`savedFieldKeys`、`onDrawerRowSynced`、`onDrawerOpened`（如加载明细）、`releaseDrawerRow`（切走前处理未入库草稿）。

## 粘贴保存约定

多格保存只有一个实现 `saveSheetCells(cells, { action, skipLocked, record })`，粘贴、批量编辑、Delete 清空、撤回都把要改的格子整理成 `[{ rowIndex, key, text }]`（`text` 是表格显示的文字）交给它：先在副本上逐格校验，任一格不合格整次不保存；和当前显示相同的格子不提交；只读列（`edit: 'readonly'`）直接跳过，结果提示里注明跳过了几格；其余锁定格改了值时，粘贴整次拦下，批量编辑、清空、撤回跳过并提示；靶点统一由 `resolveSheetTargets` 解析，同一行靶点编号和名称只有一列有变化时，另一列也一起提交核对是否匹配；最后一次批量提交、刷新列表并记一步撤回。`onSheetPaste` 只负责识别表头、按单号找行、单个值填满选区。页面只实现钩子（名字沿用 `sheetPaste*`，四种多格保存都用）：

| 钩子 | 默认 | 用途 |
|---|---|---|
| `saveSheetPasteItems(entries)` | 有 `workbenchApi.saveBatch` 时走默认实现 | 调批量保存接口，返回 `{ items }`；特殊请求体（如合成的 `confirm_complete`）时再覆写 |
| `sheetPasteColumns()` | `workbenchSheet.columns`，没写时 `sheetColumns` | 一般不覆写；列随类型变化的页面在 `columns` 里写全所有类型的列，带表头粘贴才认得出 |
| `sheetPasteAliases()` | `workbenchSheet.aliases`，没写时 `{}` | 一般不覆写；旧表头文字到列键 |
| `sheetPasteIdentityKey()` | `''` | 带表头且含该列时按它的值找行（如系统工单号） |
| `sheetPasteLockedReason(row, key)` | `'locked'` | 锁定原因，经 `sheetPasteInvalidMessage` 出文案（`'locked'` 以外的原因走 `sheetValidationMessage`） |
| `expandSheetPasteFields(row, fields)` | 无 | 联动字段，如改质检结果时带上质检人 |
| `applySheetPasteSaved(saved, fields)` | `applySavedFields` | 回填时补派生字段 |
| `sheetPasteErrorMessages()` | `{ default: '表格保存失败' }` | 接口错误文案 |

单行提交内容由 `rowSavePayload(row, fields)` 生成（见下文“保存与并发”），页面的 `saveRowField` 经 `submitRowFields` 也使用该逻辑，无需单独覆写。

日期和选项校验由 `fieldSchema.coerceFieldValue` 统一处理，页面不要再写一份 `normalizeSheetDate` / `matchOption`。

## Excel 表格外壳

Excel 视图的表格一行 `<WorkbenchSheet v-else>`，外层的划选、复制、粘贴、键入事件，vxe-table 的配置和事件，三种标准列和选区遮罩都在里面接好，页面无需编写 `ref` 和事件绑定；混入里用 `sheetEl('table' | 'wrap' | 'stage' | 'rangeOverlay' | 'dropLine' | 'ghost')` 取元素。其余属性（`header-cell-style`、`row-class-name`、`empty-text`、事件）透传给 vxe-table。

标准列按 `SHEET_COLUMNS` 的 `edit` 分：`target` 靶点列，`select` / `multi` 选择列（`isSheetChoiceColumn`），其余普通列（`align` 写在列定义上）。选择列的钩子都有默认实现：

| 钩子 | 默认 | 何时覆写 |
|---|---|---|
| `isUserColumn(column)` | 字段 `type` 为 `user` / `users` | 人员列判定不同（人员列下拉可搜索） |
| `isSheetMultiColumn(column)` | `edit === 'multi'` | 多选判定不同 |
| `sheetChoiceClearable(column)` | 字段非 `required` 时可清空 | 可清空规则不同 |
| `sheetChoiceModelKey(column)` | `column.key` | 下拉绑定另一个字段（发现工作台的筛选方法绑数组） |
| `isSheetPickerCell(column, row)` | `true` | 这一格不给下拉、只能键入（文库构建的细胞类型） |
| `sheetChoiceDirectValue` / `setSheetChoiceDirectValue(row, column, value)` | 走 `sheetDirectTextValue` / `setSheetDirectValue` | 键入时显示值和存储值不同 |
| `sheetPickerDisplayValue(row, column)` | 靶点列走 `sheetTargetDirectValue`，其余 `sheetDirectTextValue` | 下拉上方显示的文字不同 |

插槽：

| 插槽 | 用途 |
|---|---|
| `#actions="{ row }"` | 右侧固定操作列 |
| `#cell-<列键>="{ row, column }"` | 某列的单元格展示（合成与验证的靶点名称带色标） |
| `#picker="{ row, column }"` | 选择列双击时页面自带的编辑器，配合 `isSheetCustomPicker(column, row)`（小鼠品系等逗号多值列）；编辑器写 `ref="sheetSelectEditor"`、`@visible-change="onSheetSelectVisible"` |
| `#column="{ column }"` | 整列自绘，配合 `isSheetCustomColumn(column)`（文库构建的引物目录列） |
| `#columns` | 整组列自己写，不渲染标准列（只读的引物库） |
| `#range-overlay` | 选区遮罩里的附加内容（文库构建的编号填充柄） |

## 单格编辑约定

`workbenchExcelMixin` 自带单格编辑的完整流程。`coerceSheetValue(key, value, row)`（返回 `{ ok, value }` 或 `{ ok: false, reason }`）默认按 `workbenchFields` 的类型、必填、长度和选项校验，页面只为特殊字段覆写。以下方法也都有默认实现，页面有特殊字段时才覆写：

| 方法 | 默认行为 | 何时覆写 |
|---|---|---|
| `finishSheetEdit` | 锁定格退回；双击靶点列走选择器补名称；其余 `coerceSheetValue` 校验、相同值不保存、靶点编号或名称互相补全，最后 `persistRow` | 有目录联动等额外流程（文库构建） |
| `sheetEditInput(row, key, editSource)` | `row[key]` | 一列编辑态和展示态存在不同字段（发现工作台的筛选方法） |
| `assignSheetValue(row, key, text)` | `coerceSheetValue` 后写回 | 一般不覆写；校验要看整行时用 `coerceSheetValue` 的第三个参数 `row`（文库构建） |
| `restoreSheetEditValue(row, key, value)` | 靶点编号去重成数组，其余深拷贝写回 | 一列占多个字段（筛选方法的文本和数组） |
| `sheetValidationMessage(key, reason)` | 日期、整数（0 或正整数）、必填、长度、锁定、未知列、选项不匹配 | 不覆写；页面特有原因写 `sheetValidationExtraMessage(key, reason, label)`，返回空串走默认 |
| `sheetStringMax` | 从字段定义的 `max` 推出 | 只有字段定义拿不到长度时才覆写 |
| `sheetChoiceSelectOptions(column, row)` | `sheetChoiceOptionsMap[column.key]` | 选项随行变化（负责人、样品来源） |
| `setSheetTargetDirectValue` | `row[key] = value`，键入时保留原文 | 一般不覆写；键入中去重会吞掉刚敲的逗号 |

### 批量编辑、清空与撤回

全部在 `workbenchExcelMixin` 里，页面不用写代码：

- **批量编辑**：在多格选区里双击任意一格，选区收成这一格所在的列（行不变），编辑这一格；Enter、Ctrl+Enter 或点别处提交时，把这一格的新值按「单个值粘贴」交给 `saveSheetCells` 填满这几行，不可编辑的格子跳过。在多格选区里直接键入和 Excel 一样：选区同样收成这一列，但 Enter 或点别处只改当前格，按 Ctrl+Enter 才填满，免得想复制时手滑打字覆盖整列。值没改、按 Esc（在下拉面板里按也算）都不同步，Esc 把这一格退回原值；选区只有一行时就是普通单格编辑。未入库的草稿行不参与。
- **清空**：Delete 把选区内可编辑的格子清空，排序列除外，一次提交；优先级（共用字段 `PRIORITY_FIELD`）清空或贴空时回到「正常」，和后端一致；其余必填列清空校验不过时整次不保存。
- **撤回**：Excel 视图里不在输入框时按 Ctrl+Z，撤回最近一步表格修改（单格编辑、粘贴、批量编辑、清空各算一步）。只保留 10 分钟内、最多 20 步；确认框列出「第几行、哪一列、现值 → 原值」，确认后按原文字走 `saveSheetCells` 重新保存，取消或保存失败时这一步留着，可以再按 Ctrl+Z。之后又改过（包括在抽屉里改）的格子不撤回；这一步改的行都不在当前页（翻页、筛选）时这一步也留着，回到那一页再撤回；撤回操作本身不进入撤回记录，也没有重做。抽屉和行内下拉的修改不进撤回。

## 表头筛选与排序

页面通过 `headerMenuColumns` 登记有菜单的列。菜单支持升降序、按值包含/排除、空白/非空白和按类型适用的条件；颜色筛选由 `WorkbenchHeaderMenu.vue` 展示，数据列需在后端登记颜色条件。`WorkbenchColorMark` 只负责合成与验证页的单元格颜色编辑。

`workbenchHeaderMenu.js` 使用 `listQuery.sort_field`、`listQuery.sort_dir` 和 `field_filters`。顶部筛选能表达的条件写回顶部控件；排除、空白、颜色等条件保留为表头条件。工具栏胶囊显示保留在表头的条件数并可一次清除。

取值请求在当前列表条件上增加以下字段：

| 字段 | 含义 |
|---|---|
| `field` | 列键 |
| `value_keyword` | 菜单内搜索词 |
| `value_limit` | 返回上限，后端限制为 1–1000 |
| `value_order` | `value`、`value_desc` 或 `recent` |

`all` 列在前端加载取值后搜索；`recent` 默认取最近出现的 200 个值；`search` 列输入关键字后请求。后端各模块用 `utils/header_filters.py` 的 `header_columns()` 定义自己的 `HEADER_COLUMNS`，列表、统计、导出共用其生成的筛选和排序条件。取值查询保留其他列条件，并排除当前列自身条件。`recent` 最多扫描最近 5000 行。业务枚举按登记顺序排列，空值始终排在末尾。

值在内存里推算、SQL 筛不准的列登记 `sortOnly: true`，菜单只有排序（效价的采血日期，空值在后）；效价笼位不登记。效价的只数、FACS、ELISA 按显示值筛：单上没填跟随方案，只数为全项目小鼠只数之和，空按 0。统计块自己切换的维度（免疫实验的状态、负责人；效价的负责人、血清状态、小结、检测日期）不看这些列的表头条件；效价这四列由统计块改写顶部筛选，表头条件不写回顶部，与顶部同时生效。

Excel 视图中，有菜单的表头单击打开菜单；按住约 350 ms 或拖到其他列后选择整列。未登记菜单的表头直接选择整列。`Shift` 拖动用于调整列序，不打开菜单；`Shift` 单击表头从已有选区的起始列扩选到该列，没有选区时只选该列。窗口尺寸变化后选区框自动重绘。

## 视图与列

| 视图 | 用途 | 列设置 |
|---|---|---|
| 工作台 `workbench` | 扫读、行内编辑、右侧抽屉 | `WORKBENCH_COLUMNS`；`defaultVisible: true` 默认显示；排序列固定左侧，操作列固定右侧 |
| Excel `excel` | 当前分页选区、复制、粘贴、逐格和批量编辑、撤回 | `SHEET_COLUMNS`；使用独立存储键 |

两种视图均通过 `createColumnOrder` 保存列序和拖拽后的列宽。`Shift` 拖动业务列表头调整顺序；有菜单的表头平时显示点击手型，按住 `Shift` 时可拖动的表头才显示抓手。右键“视图”恢复当前视图默认列序和列宽；工作台视图同时恢复默认显示字段。“显示字段”可以调整业务列顺序和可见性，固定列不可隐藏；字段后的圆点循环切换个人列字体颜色（红、橙、绿、蓝、紫，存在同一 `viewPrefsStorageKey`），Excel 视图同样生效；颜色挂在单元格上，原有的标签、状态色、靶点标色等特殊颜色优先。全站表格统一不弹浏览器右键菜单（`utils/tableContextMenu.ts`），输入框里和右键点在选中文字上时除外；抽屉打开时右键行关闭抽屉。

Excel 操作范围是当前分页。单值粘贴到多格选区会填满选区；任一单元格校验失败时整批不保存。批量编辑、清空和撤回见上文“批量编辑、清空与撤回”。日期、枚举和整数字段在提交前默认由 `workbenchExcelMixin` 按 `workbenchFields` 校验，页面只补特殊业务校验。单元格能否编辑由页面的 `sheetCellLockReason` 返回原因，双击或键入不可编辑的单元格时提示该原因。多行文本按页面登记保留换行。

靶点顶部筛选使用 `WorkbenchTargetFilter` 搜索本表已录入值。编辑区使用 `WorkbenchTargetSelect` 或 `workbenchTargetMixin` 搜索靶点主数据，并同时保存靶点名称和编号。

## 队列排序与优先级

免疫工作台、发现工作台和合成与验证使用 `utils/workbench_queue.py`，各自写一个 `QueueSpec`。优先级从高到低为 `吉吉国王`、`非常紧急`、`加急`、`正常`。

列表默认按 `id DESC`，首列显示当前页序号。点击“序号”切换到队列模式：请求 `sort_field=sort_order`，首列显示 `sort_order`，并开放改号和拖行。再次点击恢复默认模式。

`sort_order` 只分配给非终态记录，并保持稠密的 `1..N`。终态记录为 `NULL`，不参与改号或拖行。改排序号和拖行不会改变优先级，目标位置会限制在当前优先级档位内。只改优先级时，升档放到目标档末尾，降档放到目标档开头。新记录按默认优先级加入该档末尾。项目状态写入终态或离开终态时，由写操作同步出队或入队；列表和导出不改队列。重编号时被顺移的其他行用一条批量 `UPDATE` 写入、不进操作审计；直接移动的行和请求中已改过排序的行照常记审计。

写队列前 `lock_queue` 按主键顺序锁住整表的行，并发写入者排队。MySQL 可重复读下，事务里第一次普通查询（如登录校验）就定了读快照，等锁期间别人提交的排序加锁后仍读不到；所以本事务还没写过东西时，加锁前先提交一次，让之后的读取从拿到锁后开始。

前端由 `workbenchQueueSortMixin` 负责，页面只提供：

| 钩子 | 作用 |
|---|---|
| 组件选项 `workbenchApi.reorder(movedId, targetId)` | 只调本模块的 `POST /reorder`；拖完不论成败，混入都会重新加载列表（加载前先存完抽屉里未保存的修改） |
| `isQueueTerminalRow(row)` | 终态行不显示排序号、不能改号或拖行 |
| `canEditField(row, 'sort_order')`、`fieldLockReason(row, 'sort_order')` | 可选；改号权限和无权限时的提示，缺省看 `canEdit` |

模板里排序列用 `WorkbenchSortHeader` / `WorkbenchSortCell`，表格加 `:class="{ 'is-row-sortable': canDragRows }"` 和 `@reorder="scheduleSortable"`，排序列定义写 `className: 'sort-column-cell'` 作为拖拽手柄。拖拽在挂载、切回页面、切到工作台视图和列表刷新后自动重建，页面不用调用。点被锁住的排序号会提示原因（终态、无权限、未切到队列序）。

工作台视图的优先级列用 `<WorkbenchPriorityCell :value :options :editable :lock-reason @change>`：可改时是行内下拉，`@change` 里 `persistRowValue(row, 'priority', value)`；不可改时显示标签，`lock-reason` 有值时点击提示原因。抽屉下拉和 Excel 单元格默认按同一套档位着色，页面不用再写。

## 保存与并发

页面保存后使用 `patchExistingListRow` 在原行对象上合并返回值，保持正在编辑的 VXE 单元格实例。抽屉切行、关闭、筛选和切换视图前会补存脏字段，见上文“抽屉保存约定”。

四个双视图页面的单格、抽屉、粘贴、批量编辑、清空、撤回保存都带 `_expected`：`rowSavePayload(row, fields)` 用 `rowPayload(row, fields)` 组装请求体（默认取 `id` 和这些字段，靶点编号和名称成对提交、编号去重，空串存空值；页面要另行组装时覆写 `rowPayload`），再把这些字段在 `rowBaselines`（最近一次加载或保存后的入库值）里的值放进 `_expected`。同一行的保存由 `persistRow` 排队，基线总是上一次保存后的值，不会自己跟自己冲突。

后端用 `utils/batch_save.py`：带 `_expected` 的 `/save` 先 `FOR UPDATE` 锁住这一行，`/save_batch` 用 `lock_rows_by_id` 按主键顺序锁住涉及的所有行，再对所有行 `check_expected`，全部一致才开始写；任一行不一致抛 `ConflictError`，全局处理器返回 `409`「记录已被其他用户修改，请按最新内容重新填写」，整批不写。比较的当前值是这一行按列表接口序列化的结果（和前端拿到的同一份），`normalize_comparable` 只抹掉格式差异（空值、首尾空白、5 与 5.0、日期写法、列表重复项），只比 `FIELDS` 里的可写字段；`sort_order` 不比较，因为队列重编号会顺带改别的行。请求不带 `_expected` 时不比较。保存失败后页面静默重新加载列表，用户看到最新值再改。免疫工作台的方案保存另用 `scheme_revision`。

## 后端骨架

新模块的列表和写接口直接用这些公共工具，不在模块里再写一份：

| 工具 | 作用 |
|---|---|
| `utils/pagination.py` 的 `parse_page_limit`、`paginate_select` | 解析 `page` / `limit`（上限 500），执行计数和分页查询，返回 `{ items, total, page, limit }`，可附 `stats` |
| `utils/model_fields.py` 的 `model_fields`、`clean_field` | 可写字段从模型列推出（只读列用 `readonly=` 排除），普通文本、日期、整数列的整理和报错文案统一；选项、多值、联动等业务规则在模块里先处理 |
| `utils/header_filters.py` 的 `header_columns` | 普通列的表头筛选按列类型自动生成，枚举顺序、靶点、多值列写在显式参数里 |
| `core/errors.py` | 抛 `ValueError` / `ForbiddenError` / `NotFoundError` / `ConflictError`，全局处理器按 422 / 403 / 404 / 409 返回，`get_db` 出错回滚；路由直接 `return success(service.x(...))` |
| `utils/batch_save.py` | `parse_batch_items` 解析批量请求，`lock_rows_by_id` 锁行，`check_expected` 校验 `_expected` |
| `utils/workbench_queue.py` 的 `QueueSpec`、`apply_queue`、`reorder_queue` | 队列排序：模块只描述模型（带 `sort_order`、`priority` 列）、活动行条件和终态判断，入队、出队、改号、拖行和重编号由它完成 |
| `utils/normalize.py` 的 `parse_row_id`、`modules/auth/dependencies.py` 的 `actor_name` | 解析记录 ID、取当前操作人显示名 |

## Excel 实现约定

以下是 VXE 编辑器踩过的坑，新页面照做：

1. 保存后只用 `patchExistingListRow` 改原行对象，不用 `list.splice` 换成新对象，否则编辑器被拆掉，输入框回到旧值。保存排序或优先级后也保持当前数组顺序，重编号结果等下次刷新再生效。
2. 键入时 `setSheetDirectValue` 只做 `row[key] = 文本`，不拆词、不转数组；校验和转换放在 `finishSheetEdit` / `coerceSheetValue`。有双字段或展示转换时覆写 `sheetDirectTextValue`。
3. `sheetFormatter` 只给少数列返回稳定的方法引用（如 `this.formatSortColumnCell`），其余列返回 `undefined`；每次渲染新建函数会让 VXE 重挂编辑器。
4. 整数列也按文本输入，`edit` 只表示编辑器类型；提交时用 `coerce.js` 校验，例如排序号用 `coerceRequiredPositiveInt`，可空只数用 `coerceOptionalNonnegInt`。
5. 同一格继续键入时不要重复 `setEditCell`，也不要往 input 里写值再派发 `input` 事件。

## 新页面接入清单

实验模式页面照文库构建（`LibraryConstructionList.vue`）抄，工作台模式照发现工作台（`DiscoveryWorkbench.vue` + `discoveryColumns.js`，后端 `modules/discovery/workbench`）抄，它是功能最全、代码最少的一个。下面按功能列出，不要的功能整条跳过。

开发环境下漏了必需的声明会在控制台警告：`workbenchApi`、`buildQuery`（`workbenchCrudMixin`），`workbenchFields`（`workbenchExcelMixin`），`workbenchSheet.order`（`sheetSelectionMixin`），`editorSections`、`saveRowField`（`workbenchDrawerMixin`）。

- [ ] 定义 `WORKBENCH_COLUMNS`、`SHEET_COLUMNS`、独立存储键和 `createColumnOrder`，组件选项写 `workbenchSheet: { columns, order }`（有旧表头再加 `aliases`）；列随类型变化时覆写 `availableSheetColumns()`。
- [ ] 接入 `WorkbenchDataTable`、`WorkbenchViewToggle`、`workbenchExcelMixin`，Excel 视图放 `<WorkbenchSheet v-else>`（见上文“Excel 表格外壳”），实现 `sheetCellLockReason`，特殊字段再覆写 `coerceSheetValue`；特有校验文案写 `sheetValidationExtraMessage`，其余见上文“单格编辑约定”，没有特殊字段就不覆写。
- [ ] 接入 `workbenchDrawerMixin` 和 `WorkbenchDrawer`，字段用 `WorkbenchDrawerField`，按上文“抽屉保存约定”用 `submitRowFields` 实现 `saveRowField`，接口写 `workbenchApi.save`；工作台视图的优先级列用 `WorkbenchPriorityCell`，行内下拉用 `persistRowValue`。
- [ ] 多格保存（粘贴、批量编辑、清空、撤回）配置 `workbenchApi.saveBatch`（或覆写 `saveSheetPasteItems`）和需要的钩子，不覆写 `onSheetPaste`、`saveSheetCells`。
- [ ] 后端 `/save`、`/save_batch` 按上文“保存与并发”锁行并校验 `_expected`，列表用 `paginate_select`，路由不写 try/except。
- [ ] 顶部面板引入 `workbenchPanel.css`（实验模式）或 `workbenchConsole.css`（工作台模式），页面里只写统计块列数和筛选控件宽度。
- [ ] 列表请求、筛选暂存和切回刷新用 `listPageMixin`，见下节。
- [ ] 定义 `headerMenuColumns`，提供 `listQuery.sort_field`、`listQuery.sort_dir`；表头取值接口写 `workbenchApi.columnValues`。
- [ ] `buildQuery()` 合并 `headerFilterPayload()`；重置操作调用 `clearHeaderFilters()`。
- [ ] 后端定义 `HEADER_COLUMNS`，列表、统计和导出共用 `header_filter_clauses` 与 `header_sort_clauses`。
- [ ] 提供查询权限保护的 `POST /api/<module>/column_values`，调用 `header_column_values`；这个后缀自动免审计，不用登记。
- [ ] 靶点页面提供 `GET /api/<module>/recorded_targets`，顶部筛选与编辑区使用对应共用组件。
- [ ] 要队列排序：前端混入 `workbenchQueueSortMixin`，按上文“队列排序与优先级”配置 `workbenchApi.reorder`、实现 `isQueueTerminalRow`；后端接入 `sort_order`、`priority`、`POST /reorder` 和写入时队列同步。

## 普通列表页接入清单（无 Excel、无抽屉）

表格用 `el-table`，新增和编辑走弹窗或详情页时按下面接入，参考流式工单列表。要多格编辑再接 Excel 视图。

- [ ] 混入 `listTableLockMixin`、`listPageMixin`（`utils/listPage.js`）、`workbenchHeaderMenuMixin`，顺序同此。
- [ ] 写组件选项 `listFilterKey`，现有列表页都写了；`listQuery` 和表头条件自动存取，日期区间等别的筛选用 `listFilterExtras()` / `restoreListFilterExtras(state)`。排序和页码一起恢复。
- [ ] `getList()` 开头 `const isLatest = this.beginListRequest()`，响应回来先判断 `isLatest()`，成功后 `markListFetched()`；`activated` 里 `isListDataStale()` 为真时重拉。
- [ ] 顶部筛选调 `handleFilter()`，分页绑 `handleCurrentChange` / `handleSizeChange`；重置清空 `listQuery` 并调 `clearHeaderFilters()`。
- [ ] `el-table` 绑 `:header-cell-class-name="headerCellClassName"` 和 `@header-click="onTableHeaderClick"`，有菜单的列写 `column-key`，表头插槽放 `WorkbenchHeaderLabel`；页面放 `WorkbenchHeaderMenu`，工具栏放 `WorkbenchHeaderFilterChip`。
- [ ] `headerMenuColumns`、`buildQuery()`、后端 `HEADER_COLUMNS` 和 `column_values` 同上节；没有 `workbenchCrudMixin`，页面自己实现 `fetchHeaderValues(query)` 调取值接口。
- [ ] 统计块按自己的维度分组时，后端用 `without_header_fields` 去掉这些列的表头条件。

## 新模块全栈接入清单

以下按「数据库与后端 → 权限与审计 → 前端基础层 → 前端页面与文档」顺序列出新工作台或业务模块的接入位置；能够由模块声明推导的内容无需手工登记。

> 参照模块是发现工作台：前端 `src/views/Discovery/workbench/`，后端 `modules/discovery/workbench/` 与 `modules/discovery/permissions.py`。权限、审计、功能开关和存储键均按模块声明；`sys_permission`、`sys_permission_api` 不是登记入口，已录入靶点接口由各模块自己提供，视图偏好键写在对应 columns 文件里，没有中心清单。

1. **后端 ORM 模型（有新表时必选）**：在 `bbctg_vita_server/models/<module>.py` 新增模型（`__audit_label__` / `__log_label__` 按需），列补齐中文 `comment`；日期字符串优先用 `models/types.py` 的 `DateString`。`models/__init__.py` 当前无运行时引用，不是必需登记点。
2. **数据库 DDL（有新表时必选）**：在 `docs/vita-database.sql` 维护当前态 DDL。现网升级 SQL 单独交付，不放仓库。
3. **模块权限、功能开关与挂载（必选）**：在 `bbctg_vita_server/modules/<module>/permissions.py` 用 `page()` / `action()` / `data()` / `menu()` / `feature()` / `job()` 声明；在 `modules/registry.py` 的 `ACCESS` / `MOUNTS` 各加一项。`api.py` 按登记表挂载，不必再改中心权限/功能/审计文件。
4. **路由与服务（必选）**：`routes.py` 用 `require(..., audit=)`，不写 try/except；可写字段用 `utils/model_fields.model_fields`，表头用 `header_columns`；业务错误抛 `BusinessError` / `ForbiddenError` / `NotFoundError` / `ConflictError`。
5. **公共下拉选项授权**：`GET /api/options/targets` 与 `/users` 对任一业务页面权限放行（`BUSINESS_PAGE_CODES`），新页面用 `page()` 声明后自动包含。
6. **前端路由与 API（必选）**：`src/router/routes/modules/<module>.ts`（`meta.authority` / `featureCode`）；`src/api/<module>.ts` 放权限码常量与接口。`WorkbenchTargetFilter` 的已录入靶点搜索由页面传入函数，不必改公共 options 表。
7. **字段单一定义与页面（必选）**：`src/views/<Module>/<module>Columns.js` 用 `defineFields`；页面接 `workbenchCrudMixin` / `workbenchExcelMixin` / `workbenchDrawerMixin` 等，配置 `workbenchApi`、`workbenchFields` 与 `workbenchSheet`（见上文“组件选项”）。视图偏好键写在 columns 文件的 `VIEW_PREFS_KEY`，不必改 `storageKeys.ts`。
8. **细粒度权限辅助（可选）**：只有真有业务规则时才写 `src/utils/<module>Permission.ts`。
9. **测试（必选）**：在 `bbctg_vita_server/tests/<领域>/` 加 `test_<模块>.py`，继承 `support.DbTestCase`，经 service 或 route 的公开入口覆盖本模块特有的业务规则（状态推导、权限范围、冲突校验等）；公共工具已有的行为不重复测。前端有独立的纯函数逻辑时，在同目录加 `*.test.mjs`。约定见 [backend-structure.md「测试」](../backend-structure.md#测试)。
10. **首页快捷导航与文档（可选/必选）**：首页预设才改 `home-data.ts` 与文案；文档同步 `docs/overview.md`、`docs/backend-structure.md`、`docs/auth-permissions.md` 与 `docs/README.md`。
