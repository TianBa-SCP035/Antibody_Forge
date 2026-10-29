# 抗体发现 · 合成与验证

路径 `/discovery/synthesis-progress`，接口前缀 `/api/discovery/synthesis-progress`。

本模块承接抗体发现序列经计算机或算法挑选送合成之后的合成与实验验证阶段：一行对应一个合成与验证批次（含常规外送合成、内部转染、改亚型及序列改造）。流式结合与亲和力检测旨在验证算法挑选结果并筛选出最终阳性分子（详细的结合/亲和力数据分析汇总由 One 系统承接，两边拆分原老工单系统职能）。

## 表 `discovery_synthesis_order`

- **主键与外部关联**：
  - `id`：数据库自增主键；`synthesis_order_id`：系统单号（`SYN-yyMMdd-XXXXXX`，唯一）。
  - `source_one_type`（`ngs` / `beacon`）与 `source_one_id`：对应外部 One 库 `one_task_ngs_data_analyze.id` 或 `one_task_beacon_data_analyze.id`，组合唯一。手填记录为空。
  - `source_snapshot`：外部 One 库最近一次同步或核对的字段快照（JSON），用于比对来源变更。
- **状态、优先级队列与分类**：
  - `status`：7 档阶段状态——`待下单`（防备特殊未下单情况，不在顶部单设统计块）、`合成中`、`待检测`、`检测中`、`亲和力完成`、`已完成`、`已取消`。
    - 自动同步与前半段规则：填订单号或非外送供应方式 → `合成中`；填到货日期（`arrival_date`） → `待检测`；`检测中` 由用户按需手动切换。自动任务仅推进到 `待检测`，不判断亲和力或流式时间。
    - 用户手填验证日期规则：手填 `affinity_date`（亲和力日期）时，若靶点类型为 `分泌型`（无需做细胞流式检测）或已有 `flow_date`，直接变为 `已完成`，否则变为 `亲和力完成`；手填 `flow_date`（流式日期）时直接变为 `已完成`。
  - `priority` / `sort_order`：与免疫工作台、发现工作台同一套四档优先级（`吉吉国王` > `非常紧急` > `加急` > `正常`）与未完成队列编号（`1..N`，终态为 `NULL`）。列表默认按 `id` 倒序（新建工单排在第 1 页首行）；点击首列「序号」表头切换为「排序」队列模式，支持行内改号与拖拽排序。
  - `order_kind`：`常规合成`、`改造`。
  - `supply_mode`：`合成到货`、`内部转染`、`改亚型`。
- **靶点、小鼠品系与挑选方式**：
  - `target_name`、`target_codes`：关联本系统 `target` 主数据表（与发现工作台、免疫工作台一致，前端通过靶点目录检索选择或粘贴校验）。
  - `target_color`：靶点格子底色标记（`yellow`、`orange`、`red`、`green`、`blue`、`purple` 或空），通过公共组件 `WorkbenchColorMark` 与 `WorkbenchColorFilterHeader` 在工作台和 Excel 视图（含框选多行批量标记）中设置，并在靶点表头支持单选/多选颜色筛选；抽屉与筛选栏不展示。
  - `target_type`：靶点类型（与靶点库中文分类一致：`分泌型`、`I型跨膜`、`II型跨膜`、`III型跨膜`、`IV型跨膜`、`单次跨膜`、`多次穿膜`、`GPI锚定`、`细胞膜蛋白`、`外周膜蛋白`、`脂锚定蛋白`、`胞内蛋白`、`其他`）。选定或修改靶点时由后端自动从靶点库带出默认值；抽屉不展示该字段，默认工作台视图以双色胶囊（分泌型玫红、非分泌型青碧）展示并支持点击直接切换，表头支持点击快速切换分泌/非分泌筛选，Excel 视图支持下拉或输入调整。
  - `mouse_strain`：小鼠品系，按系统标准品系选项排序并以顿号拼接。
  - `selection_method`：挑选方式（预设选项：`补挑`、`EYE`、`DS`、`JX_P`、`JX_C`、`RH_P`、`RH_C`、`D`、`D模型`、`D模型-3轮`、`P`，支持多选与自定义输入并以顿号拼接）。
- **送测、合成与验证里程碑（高频核心列，排在前面；默认工作台视图下日期为只读纯文本，通过抽屉或 Excel 视图手改）**：
  - `synthesis_code`（送测转码）、`order_no`（合成订单号）、`synthetic_corp`（合成公司）、`synthetic_count`（合成个数，非负整数）、`synthetic_date`（合成日期，`YYYY-MM-DD`）。
  - `arrival_count`（到货个数，非负整数）、`arrival_date`（到货日期，`YYYY-MM-DD`，单次到货）。
  - `flow_date`（流式日期，`YYYY-MM-DD`）、`flow_note`（流式说明）。
  - `affinity_date`（亲和力日期，`YYYY-MM-DD`）、`affinity_result`（亲和力结果，固定下拉选项：`正常`、`阳性极少`、`全阴`；填写亲和力日期时，若亲和力结果为空自动默认设为 `正常`，若清空亲和力日期则同步回退）、`report_reason`（未出原因）。
  - `owner`（负责人 / PM 认领人；未认领批次可记为 `无人问津`）。
  - `batch_label`（工单批次）、`remark`（备注）。
- **序列改造附加字段（`order_kind = 改造` 时抽屉展开）**：
  - `eng_type`（改造类型，可多选或自创，按固定选项顺序用顿号拼接，同小鼠品系）、`eng_method`（改造方式，可多选或自创，顿号拼接）、`eng_parent_seq`（改造序列或母本）、`eng_requirement`（改造要求）、`eng_result`（改造结果）。
- **系统内流程串联字段（排在工作台「显示字段」、抽屉与 Excel 视图末尾）**：
  - `project_code`（项目管理编号）、`study_type`（课题类型）、`pm`（PM）；底层表保留 `experiment_id`（实验号）用于系统内部跨模块工单关联，前端界面不展示实验号列。

## 外部 One 库关联与两段式加载

工单行始终在本系统创建（或由本系统上游模块交接），不从外部 One 库主动拉取生成新行。列表的筛选、排序、分页完全读取本地 `discovery_synthesis_order`。

1. **首屏两段式加载与即时匹配**：
   - 第一段 `POST /list` 仅查本地主库，首屏立即渲染。
   - 第二段前端异步调用 `POST /check_remote`（或在保存 `工单批次`、`送测转码`、`订单号` 后触发），后端以 1 秒连接/读取超时按 `source_one_id`（未关联行则按 `订单号`、`工单批次` 或 `送测转码` 匹配绑定）查询 One 库 `one_task_ngs_data_analyze` 与 `one_task_beacon_data_analyze`。
   - 本地原本为空的 6 项合成与到货执行字段（订单号、合成公司、合成个数、合成日期、到货个数、到货日期）自动回填并推进状态机；本地已有值且与外部最新值不一致的执行字段，不静默覆盖本地值，仅更新 `source_snapshot` 并返回差异行。前端在靶点右上角显示「变更」微角标，抽屉对应字段下显示来源新值与「采用」按钮。
2. **全量刷新已有未完结工单**：
   - 定时任务 `job.discovery_synthesis_order_sync`（默认每隔 1 小时执行）及页面「同步One数据」按钮调用 `POST /sync_now`，对本系统所有未完结或未绑定 One 的工单执行批量匹配与合成/到货进度更新。

## 页面与抽屉排版

- **筛选与快捷交互**：常驻条含合成日起止；齿轮高级区含到货、流式、亲和力三个日起止，按对应日期闭区间过滤，列表导出沿用同一条件。「待测 / 检测中」统计块支持右键单独筛选 `亲和力完成` 状态，点击「全部批次」时同步清空状态筛选。工作台与 Excel 双视图下的四个日期表头（合成日期、到货日期、亲和力日期、流式日期）复用公共组件 `WorkbenchDateHeader` 与 `workbenchExcelMixin`，支持左键按日期排序（蓝色文字 + `↑ / ↓`）、右键筛选未填写该日期的批次（绿色文字 + `∅`）。
- **操作列三个按钮**：**详情**（primary，按实验号或项目编号跳转免疫项目查看页）、**认领**（success，仅 `owner = 无人问津` 的批次可认领为当前操作人，或将本人已认领批次改回 `无人问津`；已被他人认领或未标无人问津的不可认领）、**删除**（warning）。
- **右上角「新建工单」与抽屉「加单」**：新建改造工单（或由仅具 `pm_edit` 权限的 PM 新建工单，或在抽屉中将订单性质切为 `改造`）时，若 `owner`（负责人）或 `pm`（PM）为空，默认自动填充当前下单人的姓名。抽屉顶部「加单」可一键复制当前工单的项目、靶点及改造需求等基础信息生成新行（若同转码在 One 库有未关联新单则自动关联并拉取）。
- **抽屉分区顺序**：
  1. `状态 / 归属`：状态、优先级、负责人、排序、订单性质、供应方式
  2. `改造信息`（仅 `订单性质 = 改造` 时展开）：改造类型、改造方式、母本序列、改造要求、改造结果
  3. `项目信息`：项目编号、小鼠品系、PM、课题类型、靶点、靶点编号、备注
  4. `合成订单`：挑选方式、送测转码、订单号、合成公司、合成个数、合成日期、工单批次
  5. `到货与验证`：到货个数、到货日期；亲和力结果、亲和力日期；未出原因（整行）；流式日期（半行）；流式说明（整行）

## 接口与权限

查看页面与只读接口使用 `discovery.page.synthesis_progress`。编辑权限分三档（多项同时具备时取并集）：
- `discovery.synthesis_progress.edit`（全部编辑）：可修改所有字段及靶点底色标记、采用来源变更、手动同步 One 数据、删除任意工单。
- `discovery.synthesis_progress.pm_edit`（PM 操作）：可新建/加单、删除 `待下单` 工单、认领 `无人问津` 批次（或将本人已认领批次改回 `无人问津`），可编辑 `项目信息`、`改造信息`（除改造结果）以及 `状态 / 归属` 中的优先级、排序、订单性质、供应方式；不可修改状态、合成订单与到货验证字段。
- `discovery.synthesis_progress.assay_edit`（实验员操作）：仅可编辑已有工单「到货与验证」中除到货个数、到货日期外的 5 个验证字段（`affinity_result`、`affinity_date`、`report_reason`、`flow_date`、`flow_note`）。

- `POST /list`：分页查询与顶部视图/胶囊统计（`discovery.page.synthesis_progress`）。
- `GET /options`：下拉选项与靶点/人员筛选项（`discovery.page.synthesis_progress`）。
- `POST /check_remote`：按当前页行 ID 点查核对 One 库最新快照（`discovery.page.synthesis_progress`）。
- `POST /export_list`：按当前筛选条件导出 Excel（`discovery.page.synthesis_progress`）。
- `POST /save`：单条新增或修改（`edit` / `pm_edit` / `assay_edit`）。
- `POST /save_batch`：Excel 视图批量粘贴保存（`edit` / `pm_edit` / `assay_edit`）。
- `POST /claim`：PM 认领或退回 `无人问津` 合成结果（`edit` 或 `pm_edit`）。
- `POST /reorder`：按优先级队列调整排序（`edit` 或 `pm_edit`）。
- `POST /delete`：删除记录（`edit`；`pm_edit` 仅可删除 `待下单` 状态工单）。
- `POST /adopt_source`：采用外部来源最新值覆盖本地单字段或整行差异字段（`edit`）。
- `POST /sync_now`：手动立即对本地未完结工单向 One 库拉取更新合成与到货信息（`edit`）。
