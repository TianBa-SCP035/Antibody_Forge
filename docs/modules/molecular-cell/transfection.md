# 分子与细胞 · 转染与表达
> 记录 PCR 转染与质粒转染实验，并维护转染表（蛋白与重、轻链质粒的对应）。工单来自文库构建单细胞孔板交接或本模块自建，做完后手动交接到合成与验证。检测、送测暂不在本模块。相关：[文库构建](./library-construction.md) · [合成与验证](../discovery/synthesis-progress.md) · [项目工作台共用约定](../workbench.md)

## 1. 入口与权限

| 项目 | 值 |
|---|---|
| 页面路由 | `/molecular-cell/transfection`（`TransfectionList.vue`）；转染表 `/molecular-cell/transfection/proteins`（`TransfectionProteins.vue`，不进菜单，从列表右上角「新建」旁的「转染表」进入，标签页归在转染与表达下） |
| 一级菜单开关 | `menu.molecular_cell` |
| 页面菜单开关 | `menu.molecular_cell.transfection` |
| 接口前缀 | `/api/molecular-cell/transfection` |

| 权限码 | 类型 | 允许的操作 |
|---|---|---|
| `molecular.page.transfection` | `page` | 访问转染与表达和转染表；查询、表头筛选候选值、导出、工单蛋白清单及其导出 |
| `molecular.transfection.edit` | `action` | 新建、编辑、批量保存、删除工单；导入、删除蛋白清单；交接到合成与验证；在文库构建交接单细胞孔板 |
| `molecular.library.edit` | `action` | 在文库构建交接单细胞孔板（`/handoff_library`），不授予转染工单编辑权限 |

文库交接还受文库构建的建库类型数据范围（`molecular.library.type.*`）约束：范围外的文库工单按「不存在」处理。

## 2. 数据与编号

### 2.1 转染工单 `molecular_transfection_order`

一条工单是一个转染批次。

| 字段 | 含义 | 规则 |
|---|---|---|
| `transfection_order_id` | 系统工单号 | `TRF-YYMMDD-六位随机大写字母数字`，创建时生成，唯一，只读 |
| `transfection_type` | 转染类型 | 必填：`PCR转染`、`质粒转染`；文库交接固定 `PCR转染` |
| `source_library_order_id` | 来源文库工单号 | 文库交接时写入，唯一（一条文库工单只交接一次），只读；自建为空，抽屉显示「自建」 |
| `project_code`、`study_type`、`target_name`、`target_codes`、`pm`、`mouse_strain`、`priority` | 项目与靶点信息 | 文库交接时带过来，之后可改；`mouse_strain` 按预设品系在前、自填在后用顿号拼接 |
| `plate_nos` | 板号 | JSON 数组，一行一个板号，行内原样、去重；文库交接时按行复制 |
| `status` | 状态 | `待转染`、`转染中`、`已完成`、`已取消`，见 2.3 |
| `owner` | 负责人 | 可空 |
| `transfected_on`、`finished_on` | 转染日期、完成日期 | `YYYY-MM-DD`；完成日期不能早于转染日期，填完成日期前需要先有转染日期 |
| `remark` | 备注 | 最长 1000，保留换行 |
| `protein_count`（派生） | 蛋白数 | 不入库，按工单蛋白清单实时统计 |
| `synthesis_order_id`（派生） | 合成与验证单号 | 不入库，按 `discovery_synthesis_order.order_no` 等于本单工单号反查；未交接为空 |

### 2.2 转染表 `molecular_transfection_protein` 与工单蛋白 `molecular_transfection_item`

| 字段 | 含义 | 规则 |
|---|---|---|
| `protein_name` | 蛋白名称 | 必填，最长 128，全库唯一；导入时按不区分大小写比较 |
| `heavy_chain` | 重链 | 必填，最长 128 |
| `light_chain` | 轻链 | 可空，最长 128 |
| `target_name` | 靶点 | 跟随工单，见下方同步规则 |
| `target_codes` | 靶点编号 | JSON 数组，跟随工单 |
| `mouse_strain` | 小鼠品系 | 跟随工单 |
| `source_order_id` | 登记工单 | 首次由工单导入时写入该工单 ID；历史数据直接录库，为空 |

`molecular_transfection_item` 是工单和蛋白的多对多关联，`(order_id, protein_id)` 唯一，按导入行序保存。同一个蛋白可以被多张工单使用。

**靶点、小鼠品系同步**：转染表不单独编辑这三列，取自使用该蛋白的工单。按工单创建先后，靶点（名称和编号一起）取第一个填了靶点的工单，小鼠品系取第一个填了品系的工单。靶点编号都能在靶点库查到时，靶点名称用库里的正式名称（多个用 `&` 连接），否则用工单上填的名称。使用它的工单都没填时保留原值（历史录入的数据不会被清空）。导入蛋白、整批删除、删除工单，以及工单的靶点、靶点编号、小鼠品系被修改（抽屉或 Excel 视图）时重新同步，所以导入蛋白时工单上的这些信息可以后补。

**可改范围**：只有「由本单首次登记，且没有别的工单在用」的蛋白，本单重新导入时才能改重轻链，或从清单去掉时一并从转染表删除。历史录入的蛋白、别的工单在用的蛋白，名称相同时重轻链必须和库里一致。

### 2.3 状态

- 状态跟着日期走：有完成日期为 `已完成`，只有转染日期为 `转染中`，都没有为 `待转染`。只有 `已取消` 单独记，改日期不会改掉已取消。
- 手动选状态等于补齐或清掉对应日期：选 `待转染` 清空两个日期；选 `转染中` 补转染日期（空时取今天）并清空完成日期；选 `已完成` 两个日期空的都补今天。
- 已交接到合成与验证的工单，转染类型、状态、转染日期、完成日期不能再改（合成单的合成、到货日期取自这里），其余字段仍可编辑。

## 3. 页面操作

公共表头筛选、双视图、显示字段规则见 [../workbench.md](../workbench.md)。

### 3.1 列表与筛选

- **统计块**：`待转染`、`转染中`、`已完成`、`已取消` 四块。点击切换状态筛选（同时清掉表头的状态条件）；计数不受顶部和表头状态条件影响。
- **默认显示字段**（工作台视图，顺序同列）：项目编号（固定首列）、靶点、转染类型、蛋白数、负责人、状态、转染日期、完成日期、优先级。小鼠品系、PM、课题类型、靶点编号、来源文库工单、板号、系统工单号、合成与验证单、备注在「显示字段」里打开；是否已交接看行操作的「已交接」和抽屉标题下的说明。
- **常驻筛选**（顺序同列）：项目编号、靶点（`GET /recorded_targets`）、转染类型、蛋白名称（按清单里任一蛋白名称包含匹配）、负责人、转染日期起止、优先级。
- **高级筛选**（齿轮）：完成日期起止、小鼠品系、PM、课题类型、来源文库工单号、系统工单号、备注。从文库构建交接后跳过来时按系统工单号筛选，并展开高级筛选栏。项目编号、来源文库工单号、系统工单号填单个值按包含匹配，用逗号、顿号、空格、制表符或换行分隔多个值时按完整编号匹配（单次最多 500 个）。
- **高级操作栏**：显示字段、列表导出。右上角「新建」旁的「转染表」进入转染表查询页。
- **工作台视图**：行内可改优先级、状态、转染日期、完成日期；点行打开右侧抽屉，字段改完自动保存。**Excel 视图**：批量粘贴调用 `/batch_save`（单次最多 500 条，任一条失败整批回滚），带「系统工单号」表头时按单号匹配；板号单元格只能写一行，多个板号在抽屉里改。

### 3.2 新建、行操作

- **新建**：右上角「新建」选择转染类型（默认 `质粒转染`），工作台视图创建后打开抽屉。
- **行操作**（`TransfectionRowActions.vue`，行操作列与抽屉顶部）：蛋白、交接、删除三个按钮。「蛋白」跳到转染表并按本单工单号筛选。
- **交接**（行操作与抽屉顶部）：只有 `已完成`、已导入蛋白、且合成与验证必填项（小鼠品系、PM、靶点等）已填的工单可交接；确认后新建一条合成与验证单，见第 4 节。已交接的按钮显示「已交接」。
- **删除**：已交接的工单不能删除。删除时一并删除蛋白清单；本单登记的蛋白没有别的工单在用时从转染表删除，仍在用的保留，登记工单置空。

### 3.3 抽屉里的蛋白清单（`TransfectionProteinPanel.vue`）

- 抽屉字段下方列出本单蛋白（序号、蛋白名称、重链、轻链、来源：本单登记 / 已有），提供「整批删除」「导出」和「在转染表中查看」（带 `?order_code=` 跳转转染表）。
- **导出**：本单清单按导入格式（`抗体名称`、`重链名称`、`轻链名称` 三列，按清单顺序）导出，改好后直接导入即可；清单为空时导出的就是导入模板。个别蛋白要改或要去掉，都走「导出 → 改 → 导入」，页面上不逐条编辑。
- **导入**：拖入或选择 `.xlsx`、`.xls`、`.csv`，按表头找三列，列序不限，其他列不读（模板表头为 `抗体名称`、`重链名称`、`轻链名称`）。认的写法（比较时去掉空白和末尾 `*`）：名称列 `抗体名称`、`抗体名`、`蛋白名称`、`蛋白名`；重链列 `重链名称`、`重链名`、`重链`、`重链质粒名称`、`重链质粒名`、`重链质粒`；轻链列同理。表头是第一行同时有这三列的行，上面的说明行不管；三列都空的行跳过；同一行出现两组同名表头时只取左边第一组。前端只找表头和取值，取工作簿中第一张带表头的表，单次最多 5000 行；已有清单时先确认替换。
- **校验在后端统一做**，任何一行有问题整个文件不导入，按 Excel 行号列出全部问题（最多显示 50 条）：缺少蛋白名称或重链、超长、文件内蛋白名称重复（不区分大小写）、和转染表里不可改的同名蛋白重轻链不一致。
- **整单替换**：导入结果就是本单的新清单；新名称登记到转染表，本单可改的蛋白按文件更新重轻链，旧清单里去掉且本单登记、别处没用的蛋白从转染表删除。成功后提示新登记、更新、删除的数量并刷新蛋白数。
- **整批删除**：有编辑权限且清单不为空时显示，确认后清空本单清单；其中本单登记、别的工单没在用的一并从转染表删除，规则同整单替换。
- 已交接的工单清单只读，不显示导入区和整批删除。

### 3.4 转染表查询页（`TransfectionProteins.vue`）

- 只读页面：序号（显示用行号，翻页接着编号，同引物库）、蛋白名称、重链、轻链、靶点、靶点编号、小鼠品系、登记工单、使用工单、登记时间；蛋白名称、重链、轻链、靶点（按名称或编号匹配）、小鼠品系接入表头筛选与排序，默认按登记先后倒序。导出列与页面一致。
- 来源统计块：全部、工单登记、历史录入；计数不随选中的来源收缩。
- 筛选：蛋白名称、重链、轻链（包含匹配）、工单号（单个包含匹配，多个按完整编号匹配使用过该蛋白的工单，单次最多 500 个）；支持单元格划选复制和导出。
- 带 `?order_code=` 进入时只按该工单号筛选。

## 4. 跨模块联动

- **文库构建 → 转染与表达**：文库构建行操作「交接」只对单细胞孔板（`plate_single_cell`）开放，已取消的不能交接，不要求质检结论。交接新建一条 `PCR转染` 工单，带过来项目编号（`source_project_code`）、课题类型、靶点、PM、小鼠品系、板号、优先级。一条文库工单只交接一次，已交接为转染工单的文库工单不能删除。交接成功后有转染页面权限的用户可选择跳到转染与表达（`?order=系统工单号`，只按该单号筛选并打开抽屉）。
- **转染与表达 → 合成与验证**：新建一条 `常规合成` + `内部转染` 的合成单，带过去项目编号、课题类型、PM、靶点、小鼠品系、优先级；合成数量、到货数量取蛋白数，合成日期取转染日期，到货日期取完成日期，状态按合成与验证规则推导为 `待检测`；合成单的订单号写本单工单号，在合成与验证里只读（`TRF-` 开头的订单号不能修改、清空或手填）。合成单被删除后，转染工单回到未交接状态，可重新交接。

## 5. 接口

| 方法 | 路径 | 权限 | 用途 |
|---|---|---|---|
| `GET` | `/api/molecular-cell/transfection/options` | `molecular.page.transfection` | 转染类型、状态、优先级、小鼠品系及本表已有人员 |
| `GET` | `/api/molecular-cell/transfection/recorded_targets` | `molecular.page.transfection` | 远程搜索本表已录入靶点 |
| `POST` | `/api/molecular-cell/transfection/list` | `molecular.page.transfection` | 分页查询工单与状态统计（`stats`） |
| `POST` | `/api/molecular-cell/transfection/column_values` | `molecular.page.transfection` | 表头筛选候选值 |
| `POST` | `/api/molecular-cell/transfection/export_list` | `molecular.page.transfection` | 按当前筛选与排序导出工单 Excel |
| `POST` | `/api/molecular-cell/transfection/save` | `molecular.transfection.edit` | 新建（只传 `transfection_type`）或修改工单 |
| `POST` | `/api/molecular-cell/transfection/batch_save` | `molecular.transfection.edit` | Excel 批量保存（单次最多 500 条，单事务） |
| `POST` | `/api/molecular-cell/transfection/delete` | `molecular.transfection.edit` | 删除未交接的工单 |
| `POST` | `/api/molecular-cell/transfection/handoff_library` | `molecular.transfection.edit` 或 `molecular.library.edit` | 文库单细胞孔板交接为 PCR 转染工单（`library_order_id`） |
| `POST` | `/api/molecular-cell/transfection/handoff_synthesis` | `molecular.transfection.edit` | 交接到合成与验证，返回合成单号和最新工单行 |
| `GET` | `/api/molecular-cell/transfection/order_proteins` | `molecular.page.transfection` | 工单蛋白清单（`order_id`），`registered_here` 表示本单登记 |
| `POST` | `/api/molecular-cell/transfection/proteins/import` | `molecular.transfection.edit` | 整单替换蛋白清单（单次最多 5000 行），返回 `created`、`updated`、`removed` 与最新工单行 |
| `GET` | `/api/molecular-cell/transfection/order_proteins/export` | `molecular.page.transfection` | 按导入格式导出工单蛋白清单（`order_id`），清单为空时即导入模板 |
| `POST` | `/api/molecular-cell/transfection/proteins/clear` | `molecular.transfection.edit` | 整批删除工单蛋白清单（`id`），返回 `total`、`removed` 与最新工单行 |
| `POST` | `/api/molecular-cell/transfection/proteins/list` | `molecular.page.transfection` | 分页查询转染表与来源统计（`stats.total`、`stats.order`、`stats.history`） |
| `POST` | `/api/molecular-cell/transfection/proteins/column_values` | `molecular.page.transfection` | 转染表表头筛选候选值 |
| `POST` | `/api/molecular-cell/transfection/proteins/export` | `molecular.page.transfection` | 导出转染表 Excel |