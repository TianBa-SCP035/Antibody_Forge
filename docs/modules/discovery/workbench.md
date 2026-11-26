# 发现工作台

> 管理剖鼠取细胞、冲击免疫和筛选路线，并承接效价下发与文库构建交接。相关：[项目工作台共用约定](../workbench.md)、[免疫工作台](../immunology/workbench.md)、[文库构建](../molecular-cell/library-construction.md)

## 1. 入口与权限

前端路由为 `/discovery/workbench`。菜单功能开关为 `menu.discovery.workbench`。

| 权限码 | 范围 |
|---|---|
| `discovery.page.workbench` | 查看页面、列表、选项、靶点、表头取值和导出 |
| `discovery.workbench.edit` | 全部编辑：新建、编辑、批量保存、删除、排序；可从效价下发和交接文库 |
| `discovery.workbench.immune_edit` | 免疫编辑：可新建、改其他字段（含血清效价）、删除、冻存和既往筛选，也可从效价下发新建。不能改状态、优先级、负责人、排序、筛选抗原、阳性细胞数、板号，不能排序，不能交接文库。改剖鼠或冲击日期时，状态仍按日期自动推进。免疫管理员、免疫方案编辑（免疫牛马），以及 PM 张文姣的个人允许，使用这个权限，不再使用全部编辑 |
| `molecular.library.edit` | 可交接文库，但不授予发现工作台编辑权限 |
| `serum.page.detail` | 操作列“详情”进入免疫实验详情 |

## 2. 数据与编号

主表为 `discovery_workbench`。一行是一条发现安排；页面直接读写本表快照，不联查免疫项目。`experiment_id` 可以重复。

| 字段 | 含义 | 规则 |
|---|---|---|
| `discovery_id` | 发现安排号 | 库内唯一；创建时生成；保存请求中的同名字段被忽略 |
| `project_code` / `experiment_id` | 项目编号 / 实验号 | 文本，可在本台修改 |
| `target_name` / `target_codes` | 靶点名称 / 编号 | 远程选择时成对写入 |
| `owner` / `immune_owner` / `cell_collector` | 负责人 / 免疫负责人 / 细胞收集人 | 系统用户名显示值 |
| `mouse_strain_category` / `mouse_strain` | 归类鼠型 / 小鼠品系 | 固定选项优先、自填值随后，按顿号存储；筛选同时识别逗号、顿号和加号 |
| `mouse_count` | 小鼠只数 | 可空非负整数，`0` 合法 |
| `mouse_nos` / `serum_titer` | 鼠号 / 血清效价 | 保留换行 |
| `screening_methods` | 筛选方式 | `达普`、`噬菌体`、`Beacon`、`NGS` 多选，英文逗号存储 |
| `prior_screening` | 既往筛选 | 文字最长 2000 字，可另传最多 12 张图片（png、jpg、gif、webp、bmp）。图片不进文本保存，走 `/prior_screening/upload`、`/remove`、`/file` |
| `harvest_date` | 剖鼠日期 | `YYYY-MM-DD`；文库交接时作为上机日期。早于今天的日期不能再改；今天和之后的日期可以改，方便换项目后重调 |
| `boost_date` | 冲击日期 | 修改剖鼠日期时自动设为剖鼠日期前 5 天；之后可单独修改 |
| `positive_cell_count` | 阳性细胞数 | 保留换行，最长 255 字符 |
| `immune_antigen` / `screening_antigen` / `boost_antigen` / `boost_cells` | 抗原与冲击免细胞 | 保留换行 |
| `priority` / `sort_order` | 优先级与队列位 | 规则见[共用约定](../workbench.md) |

发现安排号格式为 `DSC-yyMMdd-XXXXXX`，后缀是 6 位大写字母或数字。页面新建和效价下发都由后端发号。

## 3. 状态与流转

| 状态 | 含义 |
|---|---|
| `规划中` | 新建默认状态 |
| `待冲击` | 冲击日期为今天或未来 |
| `待剖鼠` | 冲击日期已过 |
| `待建库` | 已交接非噬菌体展示建库 |
| `待噬菌体` | 已交接噬菌体展示 |
| `待测序` | 用户维护的后续状态 |
| `已完成` / `已取消` | 终态，退出队列 |

用户可以直接修改状态。保存剖鼠日期或冲击日期且未同时显式提交状态时，`规划中`、`待冲击`、`待剖鼠`按冲击日期调整：日期为今天或未来时设为 `待冲击`，日期已过时设为 `待剖鼠`；清空冲击日期时，`待冲击`恢复为 `规划中`。另外，不论是否显式提交状态，保存后为 `待冲击` 且冲击日期已过的记录都会推进为 `待剖鼠`。终态不受日期影响。

文库交接会在早期状态上写入 `待建库`；交接内容包含噬菌体展示时优先写入 `待噬菌体`。`待测序`、`已完成`、`已取消`不被交接改写。建库工单完成不会回写发现状态。

列表与导出均为只读查询。过期的 `待冲击`由定时任务推进为 `待剖鼠`。

## 4. 页面操作

关键字搜索发现安排号、项目编号和实验号。单个词按包含匹配；多个词对三类编号做精确匹配。

| 区域 | 控件 |
|---|---|
| 顶部 | 关键字、靶点、PM、筛选方式、状态、优先级、归类鼠型、剖鼠日期范围 |
| 齿轮高级区 | 课题类型、负责人、免疫负责人、细胞收集人、笼位、小鼠品系、鼠号、板号、免疫抗原、筛选抗原、冲击免抗原、备注、冲击日期范围 |
| 表头 | 除序号和操作列外的已登记业务列，靶点编号逐个列出、按含有任一编号匹配；接口为 `POST /api/discovery/workbench/column_values` |

| 阶段卡 | 包含状态 | 右键 |
|---|---|---|
| 全部安排 | 全部状态 | 无 |
| 待剖鼠 | `规划中`、`待冲击`、`待剖鼠` | 在“阶段合集”和“仅 `待剖鼠`”之间切换 |
| 待建库 | `待建库`、`待噬菌体` | 无 |
| 待测序 | `待测序` | 无 |
| 已取消 | `已取消` | 无 |

`已完成`只计入“全部安排”。阶段统计忽略当前阶段和胶囊筛选，保留其他筛选。

绿色胶囊左键切换 `boost_filter=boosting`：冲击日期非空且不早于今天。右键切换 `boost_filter=missing_date`：剖鼠日期或冲击日期任一为空，且状态不是 `已完成`、`已取消`。再次执行同一操作取消胶囊筛选。

工作台和 Excel 交互、列序、显示字段、表头菜单及队列规则见[共用约定](../workbench.md)。工作台行内可编辑优先级、状态、筛选方式和冲击日期。剖鼠日期只在还没填时能写，写上之后列表、Excel 和抽屉都锁住。左键行打开无模态抽屉；再次点击同一行、右键任意行或点击表外关闭。

抽屉按“队列 / 状态、项目、小鼠、筛选、日程”分区编辑全部业务字段。冲击免抗原输入框以本行免疫抗原的各行为候选。鼠号、板号、血清效价、阳性细胞数、四类抗原/细胞文本和备注保留中间换行。板号、三类抗原和冲击免细胞一行一项，输入框不自动折行（长行左右滚动）；板号交接单细胞孔板建库时按行原样带过去。

操作列包括“详情、交接、冻存、删除”。详情按 `experiment_id` 查找并打开免疫实验；交接打开文库核对弹窗；冻存打开留存细胞入库（见下）；已有建库工单的安排不能删除。列表导出沿用当前全部筛选。页面没有导入入口。

工作台和 Excel 视图里，相邻两行的剖鼠日期（交接后作为上机日期）不同时，行与行之间用一条浅灰细线分开。

### 留存细胞冻存

剖鼠后留下的细胞在本页入库，不走外部细胞库存。一条发现安排可以有多条冻存记录，字段为细胞类型（预设脾细胞、淋巴结、骨髓、PBMC、血浆细胞、全细胞、浆细胞、流穿液、其他，也可自填）、鼠号、管数、细胞量、体积、冻存位置、冻存日期、操作人和备注。列表不展示鼠号，展示备注，用来写不同鼠型的细胞。每条记录可以出库一次，记下出库人和当天日期。文库构建也可以按建库工单申请出库，审核通过后由系统写出库人（申请人）和日期，见 [文库构建](../molecular-cell/library-construction.md) §4.5；申请待审核期间，本页出库人显示「审核中」，不能出库或删除这条记录。查看用 `discovery.page.workbench`，入库、出库和删除用 `discovery.workbench.edit` 或 `discovery.workbench.immune_edit`。

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/discovery/workbench/cell_bank?workbench_id=` | 该安排的冻存记录，新的在前 |
| POST | `/api/discovery/workbench/cell_bank/save` | 新增一条 |
| POST | `/api/discovery/workbench/cell_bank/checkout` | 按 `id` 写出库人和出库日期 |
| POST | `/api/discovery/workbench/cell_bank/delete` | 按 `id` 删除 |

## 5. 跨模块联动

### 效价下发

效价实验列表的“测序”按钮始终可点击。缺少 `discovery.workbench.edit` 或 `discovery.workbench.immune_edit` 时显示权限提示；具备权限时打开 `TiterMouseSelectWizard.vue`，并要求至少选择一只小鼠。免疫编辑下发时可以写入血清效价，之后在发现工作台里也可以改血清效价。

`utils/titerDiscoveryHandoff.ts` 使用 `buildFacsConclusionForPage` 和 `summarizeTiterBrief` 生成快照，再调用 `POST /api/discovery/workbench/save`。每次确认都新增一行，不按实验号去重，也不保存效价工单 ID。

| 发现字段 | 来源 |
|---|---|
| 项目编号、实验号、靶点、课题类型、PM | 正式免疫项目当前值 |
| 笼位 | 效价列表当前行 |
| 鼠号、只数 | 向导选中的小鼠；按组生成鼠号行 |
| 归类鼠型、小鼠品系 | 所选小鼠所在分组 |
| 免疫抗原 | 所选分组步骤引用的抗原；名称后优先附货号，其次批号 |
| 免疫负责人 | 正式免疫项目负责人 |
| 血清效价 | 仅按所选小鼠汇总的最新数字阶段简要结论 |
| 状态、优先级 | `规划中`、`正常` |

下发完成后跳转 `/discovery/workbench?created=<id>` 并打开新行。后续修改效价数据不会刷新该快照。

### 文库构建交接

`LibraryHandoffDialog.vue` 通过以下接口加载核对信息并创建工单：

| 方法 | 路径 | 权限 |
|---|---|---|
| GET | `/api/molecular-cell/library-orders/by-discovery` | `discovery.workbench.edit` 或 `molecular.library.edit` |
| POST | `/api/molecular-cell/library-orders/handoff` | `discovery.workbench.edit` 或 `molecular.library.edit` |

弹窗展示项目编号、靶点、课题类型、小鼠品系、优先级、上机日期和阳性细胞数，并列出 `source_discovery_id` 已关联的工单。`已完成`和`已取消`不能交接。

| 筛选方式行 | 可选工艺 |
|---|---|
| 达普 | 单细胞孔板、打管加 Barcode（`pooled_bcr`，文库页称混管 H/K/L）、打管（`pooled_barcode`，文库页称混管 Barcode） |
| Beacon | 单细胞孔板、Beacon+达普打板 |
| 噬菌体 | 噬菌体展示、噬菌体测序 |
| NGS | 眼眶血、其他外周血、浆细胞 Nano、浆细胞 Lite（试剂盒挑选）、浆细胞直测（不挑选，按打管工艺建 `pooled_barcode`，Nano/Lite 按品系带出、可在文库页改） |

发现行存在 `screening_methods` 时，未标记方式对应的整行不可选；该字段为空时四行全部开放。例外：标了 NGS 时也开放达普行的「打管」。Beacon+达普打板要求同时标记达普和 Beacon，并与两个单路线孔板选项互斥。「打管加 Barcode」「打管」只是弹窗内（含「已有」工单）的叫法，文库构建页与其新建弹窗仍显示混管 H/K/L、混管 Barcode。

单细胞孔板、打管加 Barcode、打管、浆细胞直测和噬菌体展示要求 `harvest_date`。弹窗允许重复创建，已有匹配工艺显示“已有”。默认建议为：Beacon+达普同时存在时选 Beacon+达普打板；仅 Beacon 时选 Beacon 单细胞孔板；噬菌体时选噬菌体展示；达普单独和 NGS 不预选。

默认建议只在对应建库类型尚无未取消工单时产生。有 `molecular.page.library` 时，创建后跳到文库构建并打开第一条新工单；否则停留在发现工作台。

## 6. 接口

| 方法 | 路径 | 权限 | 用途 |
|---|---|---|---|
| POST | `/api/discovery/workbench/list` | `discovery.page.workbench` | 分页、筛选和统计 |
| POST | `/api/discovery/workbench/column_values` | `discovery.page.workbench` | 表头取值 |
| GET | `/api/discovery/workbench/options` | `discovery.page.workbench` | 编辑和筛选选项 |
| GET | `/api/discovery/workbench/recorded_targets` | `discovery.page.workbench` | 搜索本工作台已录入靶点 |
| POST | `/api/discovery/workbench/export_list` | `discovery.page.workbench` | 按当前条件导出 |
| POST | `/api/discovery/workbench/save` | `discovery.workbench.edit` 或 `discovery.workbench.immune_edit` | 新建或更新传入字段；免疫编辑不能改锁定字段 |
| POST | `/api/discovery/workbench/save_batch` | `discovery.workbench.edit` 或 `discovery.workbench.immune_edit` | 单事务批量保存；字段限制同上 |
| POST | `/api/discovery/workbench/delete` | `discovery.workbench.edit` 或 `discovery.workbench.immune_edit` | 删除未关联建库工单的安排 |
| POST | `/api/discovery/workbench/reorder` | `discovery.workbench.edit` | 将 `moved_id` 放到 `target_id` 的队列位 |

## 7. 定时任务与外部集成

`job.discovery_auto_update_status` 默认每天 01:15 执行。任务将冲击日期早于当天且状态为 `待冲击` 的记录改为 `待剖鼠`。任务运行由同名功能开关及其调度配置控制；应用启动和列表查询不会执行这次状态推进。
