# 项目工作台共用约定

> 适用页面：免疫工作台、发现工作台、发现合成与验证、文库构建使用工作台 / Excel 双视图；免疫实验列表、效价实验列表、流式工单列表、引物库也使用共用表头菜单。模块事实见 [免疫工作台](./immunology/workbench.md) 与 [发现工作台](./discovery/workbench.md)。

## 组件清单

| 组件 | 职责 | 使用页面 |
|---|---|---|
| `WorkbenchDataTable.vue` | 工作台表格、显示字段、固定首末列、`Shift` 拖列表头 | 免疫、发现、合成与验证、文库构建 |
| `WorkbenchViewToggle.vue`、`viewMode.js` | 切换 `workbench` / `excel`；右键恢复当前视图列设置 | 免疫、发现、合成与验证、文库构建 |
| `columnOrder.js` | `createColumnOrder` 持久化 `{ order, hidden }`，合并新增列并保持固定列 | 双视图页面的工作台表；免疫、发现、文库构建的 Excel 表 |
| `workbenchExcelMixin.js`、`workbenchExcel.css` | 当前页选区、复制、粘贴、键入、整行/整列选择和列拖动 | 免疫、发现、合成与验证、文库构建 |
| `WorkbenchHeaderMenu.vue`、`workbenchHeaderMenu.js` | 表头取值筛选、条件筛选、颜色筛选和排序 | 上述双视图页面、免疫实验列表、效价实验列表、流式工单列表、引物库 |
| `WorkbenchStatusEditor.vue` | 行内状态选择 | 免疫、发现 |
| `WorkbenchMultiTagEditor.vue` | 行内多选标签 | 发现 |
| `WorkbenchTargetSelect.vue`、`workbenchTargetMixin.js` | 编辑区远程选靶点，联动名称与编号 | 免疫、发现、合成与验证、文库构建 |
| `WorkbenchTargetFilter.vue` | 调用页面的 `GET /recorded_targets` 搜索已录入靶点，并保留已选项显示名 | 免疫、发现、合成与验证、文库构建 |
| `WorkbenchColorMark.vue` | 单元格底色标记 | 发现合成与验证 |
| `workbenchDrawer.css`、`workbenchDrawerChrome.css` | 无遮罩编辑抽屉 | 免疫、发现、合成与验证、文库构建 |

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

`all` 列在前端加载取值后搜索；`recent` 默认取最近出现的 200 个值；`search` 列输入关键字后请求。后端 `utils/header_filters.py` 的 `HEADER_COLUMNS` 生成列表、统计、导出共用的筛选和排序条件。取值查询保留其他列条件，并排除当前列自身条件。`recent` 最多扫描最近 5000 行。业务枚举按登记顺序排列，空值始终排在末尾。

值在内存里推算、SQL 筛不准的列登记 `sortOnly: true`，菜单只有排序（效价的采血日期，空值在后）；效价笼位不登记。效价的只数、FACS、ELISA 按显示值筛：单上没填跟随方案，只数为全项目小鼠只数之和，空按 0。统计块自己切换的维度（免疫实验的状态、负责人；效价的负责人、血清状态、小结、检测日期）不看这些列的表头条件；效价这四列由统计块改写顶部筛选，表头条件不写回顶部，与顶部同时生效。

Excel 视图中，有菜单的表头单击打开菜单；按住约 350 ms 或拖到其他列后选择整列。未登记菜单的表头直接选择整列。`Shift` 拖动用于调整列序，不打开菜单。

## 视图与列

| 视图 | 用途 | 列设置 |
|---|---|---|
| 工作台 `workbench` | 扫读、行内编辑、右侧抽屉 | `WORKBENCH_COLUMNS`；`defaultVisible: true` 默认显示；排序列固定左侧，操作列固定右侧 |
| Excel `excel` | 当前分页选区、复制、批量粘贴和逐格编辑 | `SHEET_COLUMNS`；使用独立存储键 |

两种视图均通过 `createColumnOrder` 保存列序和拖拽后的列宽。`Shift` 拖动业务列表头调整顺序；有菜单的表头平时显示点击手型，按住 `Shift` 时可拖动的表头才显示抓手。右键“视图”恢复当前视图默认列序和列宽；工作台视图同时恢复默认显示字段。“显示字段”可以调整业务列顺序和可见性，固定列不可隐藏；字段后的圆点循环切换个人列字体颜色（红、橙、绿、蓝、紫，存在同一 `viewPrefsStorageKey`），Excel 视图同样生效；颜色挂在单元格上，原有的标签、状态色、靶点标色等特殊颜色优先。全站表格统一不弹浏览器右键菜单（`utils/tableContextMenu.ts`），输入框里和右键点在选中文字上时除外；抽屉打开时右键行关闭抽屉。

Excel 操作范围是当前分页。单值粘贴到多格选区会填满选区；任一单元格校验失败时整批不保存。日期、枚举、正整数和非负整数由页面在提交前校验。单元格能否编辑由页面的 `sheetCellLockReason` 返回原因，双击或键入不可编辑的单元格时提示该原因。多行文本按页面登记保留换行。

靶点顶部筛选使用 `WorkbenchTargetFilter` 搜索本表已录入值。编辑区使用 `WorkbenchTargetSelect` 或 `workbenchTargetMixin` 搜索靶点主数据，并同时保存靶点名称和编号。

## 队列排序与优先级

免疫工作台和发现工作台使用 `utils/workbench_queue.py`。优先级从高到低为 `吉吉国王`、`非常紧急`、`加急`、`正常`。

列表默认按 `id DESC`，首列显示当前页序号。点击“序号”切换到队列模式：请求 `sort_field=sort_order`，首列显示 `sort_order`，并开放改号和拖行。再次点击恢复默认模式。

`sort_order` 只分配给非终态记录，并保持稠密的 `1..N`。终态记录为 `NULL`，不参与改号或拖行。改排序号和拖行不会改变优先级，目标位置会限制在当前优先级档位内。只改优先级时，升档放到目标档末尾，降档放到目标档开头。新记录按默认优先级加入该档末尾。项目状态写入终态或离开终态时，由写操作同步出队或入队；列表和导出不改队列。重编号时被顺移的其他行用一条批量 `UPDATE` 写入、不进操作审计；本次被移动的行和本次请求里已改过排序的行照常记审计。

写队列前 `lock_queue` 按主键顺序锁住整表的行，并发写入者排队。MySQL 可重复读下，事务里第一次普通查询（如登录校验）就定了读快照，等锁期间别人提交的排序加锁后仍读不到；所以本事务还没写过东西时，加锁前先提交一次，让之后的读取从拿到锁后开始。

## 保存与并发

页面保存后使用 `patchExistingListRow` 在原行对象上合并返回值，保持正在编辑的 VXE 单元格实例。抽屉切行、关闭、筛选和切换视图前会提交脏字段。

免疫工作台逐行保存时携带 `_expected`，值来自该行最近一次加载或保存后的基线。后端在行锁内比较本次涉及字段；值不一致返回 `409`。`save_batch` 在写入前校验每行 `_expected`，任一行冲突时整批回滚。方案保存使用独立的 `scheme_revision`。

发现工作台的 `/save` 和 `/save_batch` 不使用 `_expected`。批量保存仍在一个事务中执行，任一行失败时整批回滚。

## Excel 实现约定

以下是 VXE 编辑器踩过的坑，新页面照做：

1. 保存后只用 `patchExistingListRow` 改原行对象，不用 `list.splice` 换成新对象，否则编辑器被拆掉，输入框回到旧值。保存排序或优先级后也保持当前数组顺序，重编号结果等下次刷新再生效。
2. 键入时 `setSheetDirectValue` 只做 `row[key] = 文本`，不拆词、不转数组；校验和转换放在 `finishSheetEdit` / `coerceSheetValue`。有双字段或展示转换时覆写 `sheetDirectTextValue`。
3. `sheetFormatter` 只给少数列返回稳定的方法引用（如 `this.formatSortColumnCell`），其余列返回 `undefined`；每次渲染新建函数会让 VXE 重挂编辑器。
4. 整数列也按文本输入，`edit` 只表示编辑器类型；提交时用 `coerce.js` 校验，例如排序号用 `coerceRequiredPositiveInt`，可空只数用 `coerceOptionalNonnegInt`。
5. 同一格继续键入时不要重复 `setEditCell`，也不要往 input 里写值再派发 `input` 事件。

## 新页面接入清单

- [ ] 定义 `WORKBENCH_COLUMNS`、`SHEET_COLUMNS`、独立存储键和 `createColumnOrder`。
- [ ] 接入 `WorkbenchDataTable`、`WorkbenchViewToggle`、`workbenchExcelMixin`，实现页面字段校验与保存。
- [ ] 列表请求、筛选暂存和切回刷新用 `listPageMixin`，见下节。
- [ ] 定义 `headerMenuColumns`，提供 `listQuery.sort_field`、`listQuery.sort_dir` 和 `fetchHeaderValues(query)`。
- [ ] `buildQuery()` 合并 `headerFilterPayload()`；重置操作调用 `clearHeaderFilters()`。
- [ ] 后端定义 `HEADER_COLUMNS`，列表、统计和导出共用 `header_filter_clauses` 与 `header_sort_clauses`。
- [ ] 提供查询权限保护的 `POST /api/<module>/column_values`，调用 `header_column_values`，并列入审计忽略清单。
- [ ] 靶点页面提供 `GET /api/<module>/recorded_targets`，顶部筛选与编辑区使用对应共用组件。
- [ ] 队列页面接入 `sort_order`、`priority`、终态判定、`POST /reorder` 和写入时队列同步。

## 普通列表页接入清单（无 Excel、无抽屉）

表格用 `el-table`，新增和编辑走弹窗或详情页时按下面接入，参考流式工单列表。要多格编辑再接 Excel 视图。

- [ ] 混入 `listTableLockMixin`、`listPageMixin`（`utils/listPage.js`）、`workbenchHeaderMenuMixin`，顺序同此。
- [ ] 写组件选项 `listFilterKey`，现有列表页都写了；`listQuery` 和表头条件自动存取，日期区间等别的筛选用 `listFilterExtras()` / `restoreListFilterExtras(state)`。排序和页码一起恢复。
- [ ] `getList()` 开头 `const isLatest = this.beginListRequest()`，响应回来先判断 `isLatest()`，成功后 `markListFetched()`；`activated` 里 `isListDataStale()` 为真时重拉。
- [ ] 顶部筛选调 `handleFilter()`，分页绑 `handleCurrentChange` / `handleSizeChange`；重置清空 `listQuery` 并调 `clearHeaderFilters()`。
- [ ] `el-table` 绑 `:header-cell-class-name="headerCellClassName"` 和 `@header-click="onTableHeaderClick"`，有菜单的列写 `column-key`，表头插槽放 `WorkbenchHeaderLabel`；页面放 `WorkbenchHeaderMenu`，工具栏放 `WorkbenchHeaderFilterChip`。
- [ ] `headerMenuColumns`、`fetchHeaderValues`、`buildQuery()`、后端 `HEADER_COLUMNS` 和 `column_values` 同上节。
- [ ] 统计块按自己的维度分组时，后端用 `without_header_fields` 去掉这些列的表头条件。
