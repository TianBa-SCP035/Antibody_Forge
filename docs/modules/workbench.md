# 项目工作台（共用约定）

后续大模块若也做「项目工作台」，先对照本文，再写本模块字段与接口。免疫见 [immunology/workbench.md](./immunology/workbench.md)，发现见 [discovery/workbench.md](./discovery/workbench.md)。

## 两种视图

| 称谓 | `viewMode` | 做什么 |
|------|------------|--------|
| **工作台**（默认） | `workbench` | 扫读表格；关键字段行内改；左键点行开右侧抽屉，再点同一行或右键任意行关闭（无全屏遮罩） |
| **Excel** | `excel` | 当前分页内划选、复制、事务性粘贴、键入续写 |

「视图」按钮切换；工作台和 Excel 都是 `Shift` 拖列表头调列顺序，右键该按钮恢复**当前视图**的默认列序（工作台还会恢复显示字段）。两套列序分开存。实现：`apps/antibody_vita/src/components/workbench/`。旧稿里的「快速编辑 / Sheet」即这一对，新文档与界面统一用上表。

## 只抽肯定共用的

已落地、免疫和发现都在用：

| 文件 | 用途 |
|------|------|
| `workbenchExcelMixin.js` | 划选、复制、键入、列拖、选区 overlay；数字格普通输入，提交时由本页校验 |
| `workbenchExcel.css` | 格子、选区、日期/选择器编辑外观 |
| `workbenchDrawer.css` / `workbenchDrawerChrome.css` | 选择器弹出层、无遮罩抽屉 |
| `drawerOverflowTooltip.js` | 抽屉定高控件超长时悬停出全文；备注 / 鼠号等自动高度框不弹 |
| `WorkbenchViewToggle.vue` | 「视图」按钮与提示 |
| `WorkbenchStatusEditor.vue` | 状态标签点选 |
| `WorkbenchMultiTagEditor.vue` | 多选标签（筛选方式） |
| `WorkbenchTargetSelect.vue` | 抽屉靶点远程搜索；检索逻辑在 `targetOptions.js` |
| `columnOrder.js` | 列序 `localStorage`；可钉首列 / 末列；工作台另记隐藏列 `{ order, hidden }` |
| `WorkbenchDataTable.vue` | 工作台视图表：一份字段目录、默认勾选、`Shift` 拖表头；单元格用按 key 的插槽 |
| `viewMode.js` | `workbench` / `excel`（兼容旧值 `sheet`） |
| `workbenchConsole.css` | 页头、阶段条、绿色胶囊 |

优先级排队算法在后端 `utils/workbench_queue.py`（四档、只给未完成行的 `sort_order`、改档挤位；终态 `NULL`）。列表默认 `id` 倒序，表头为「序号」，格子里是本页行号 1..n。点该表头改为「排序」，按队列值排列并显示 `sort_order`，此时才能改号、拖行。拖行是把被拖行放到落点行当前的队列位，筛不筛选都能拖，终态行不参与。再点表头恢复默认。新建 / 复制 / 效价「测序」下发后按当前排序跳到该行所在页并打开抽屉。免疫和发现都用它。人名选择复用 `SerumUserSelect`（系统用户显示名）。抽屉靶点用 `WorkbenchTargetSelect`。Excel 里的靶点远程格、开展 / 下架仍在各页。该列表头左键只切换这两种显示，不再全选该列。

新工作台：`mixins: [workbenchExcelMixin]`，提供 `list`、`sheetColumns`、`canEdit`、`persistSheetColumnOrder`、`finishSheetEdit`、`normalizeRow`。键入默认 `row[key] = 文本`；有双字段或展示转换时再覆写 `sheetDirectTextValue` / `sheetValueSnapshot`。行选择列用 `excelRowSelectKey`（免疫和发现都是 `sort_order`）。粘贴校验与保存仍写在本页。

工作台视图用 `WorkbenchDataTable`：本页给一份 `WORKBENCH_COLUMNS`（与 Excel 同一组业务 key，外加操作列；免疫台「状态」只用 `status`，不要再并列 `plan_status`）。`defaultVisible: true` 的是默认短列，其余默认藏。排序列钉左、操作列钉右，单元格按 key 插槽。不要复用 Excel 的列序 key。右键「视图」按 `viewMode` 清当前这份。高级操作「显示字段」勾选这份目录；序号和操作列不能藏。新字段标了 `defaultVisible` 才默认出现。Excel 仍用自己的 `SHEET_COLUMNS`。

不要把整张 Excel 收成一个组件。列、选项、coerce、接口各台不同，抽出去只会把字段绑定搬来搬去。选项格 `#edit` 模板可以抄免疫 / 发现，不要做成万能选择器。

## Excel 交互（各台相同）

当前分页：点选/拖选单元格，活动格白底，选区浅色底加边框。点行选择列选整行并可上下拖多行；点业务表头选整列并可左右拖多列；`Ctrl+A` 选本页全部格子。选中后直接键入从末尾续写，`Backspace` 删末字符，`Delete` 清空。数字格同样先收下字符，提交或粘贴时校验整数，不合法则提示并打回。双击日期或选项只打开选择器。向多格选区粘贴单个值会填满选区；任一格不合法则整批不保存。

## Excel 实现约定（下一台直接按这个做）

这些是已经踩过的坑，不是各台自己发挥的地方。

1. **行对象身份。** 单格保存只改 `list` 里原来那一行的字段，调用 mixin 的 `patchExistingListRow(saved, fields)`。派生列由本页 `savedFieldKeys` 补上。整行回写（抽屉一次存多项、复制后合并）用 `patchExistingListRow(saved)`，内部是 `Object.assign`。禁止 `list.splice` 换成新对象：VXE 会拆掉编辑器，输入框回到打开前的字，数据其实已经写进去了。只有改排序 / 优先级导致整表重编号时才 `getList`。
2. **键入先写文本。** mixin 默认 `setSheetDirectValue` 就是 `row[key] = text`。不要在键入时拆词、转数组、走 formatter。校验、拆词、写回列表字段放在 `finishSheetEdit` / `coerceSheetValue`。
3. **formatter 少挂。** `sheetFormatter` 只给排序、靶点编号、多选展示这类列返回**稳定的方法引用**（如 `this.formatSortColumnCell`），其余列返回 `undefined`。不要 `return ({ cellValue }) => ...` 包所有列，也不要每次渲染新建函数，否则 VXE 当列配置变了，编辑器重挂。
4. **整数当文本打。** `edit` 只表示 Excel 编辑器（`text` / `select` / `date` / `target` / `readonly`），不要用 `edit: 'number'` 冒充校验。排序号、发现只数都是普通 `VxeInput`，提交时按字段 coerce：排序号必填正整数（`coerceRequiredPositiveInt`），发现只数可空、`0` 合法（`coerceOptionalNonnegInt`）。免疫「数量」仍是自由文本。
5. **编辑器不要反复打开。** 同一格继续敲，mixin 已打开则不再 `setEditCell`。不要往 input 里写值再派发 `input` 去“同步显示”。

本页仍要自己写：列定义、`coerceSheetValue`、`finishSheetEdit`、保存 API、抽屉脏字段。免疫 `saveRow` 另有 `_expected` 冲突链，发现没有，不必合成一个保存函数。
