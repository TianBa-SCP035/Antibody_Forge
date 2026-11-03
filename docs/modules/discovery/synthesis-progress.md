# 抗体发现 · 合成与验证

> 跟踪算法挑选序列的合成下单、到货，以及流式结合与亲和力初筛验证和序列改造进度。一行对应一个合成与验证批次（含常规外送合成、内部转染、改亚型及序列改造）；详细的结合/亲和力数据分析在 One 系统完成，本模块只记录进度与初筛结论。相关：[项目工作台共用约定](../workbench.md) · [发现工作台](./workbench.md) · [千鼠万抗 · 靶点库](../atlas/target-library.md) · [认证与权限](../../auth-permissions.md)

## 1. 入口与权限

- **前端路由**：`/discovery/synthesis-progress`（组件 `src/views/Discovery/synthesis/SynthesisProgress.vue`；启用 `keepAlive`，切走超过 10 分钟再次进入时静默刷新）。
- **菜单功能开关**：`menu.discovery`（抗体发现）、`menu.discovery.synthesis_progress`（合成与验证）。
- **接口前缀**：`/api/discovery/synthesis-progress`。
- **权限控制**：多项编辑权限同时具备时取并集；超级管理员（`is_superuser`）具备全部权限。

| 权限代码 | 作用域 | 允许的操作与字段范围 |
|---|---|---|
| `discovery.page.synthesis_progress` | 只读查看 | 访问页面；调用 `/list`、`/column_values`、`/options`、`/recorded_targets`、`/check_remote`、`/export_list` |
| `discovery.synthesis_progress.edit` | 全部编辑（`full`） | 新建工单、抽屉「加单」、修改全部可写字段（含 `target_color` 靶点底色标记）、调整队列排序、认领/退回批次、删除未关联 One 的任意状态工单、采用外部来源最新值（`/adopt_source`）、手动触发 One 库全量同步（`/sync_now`） |
| `discovery.synthesis_progress.pm_edit` | PM 操作（`pm`） | 新建工单、抽屉「加单」、调整队列排序（`/reorder`）、删除未关联 One 的 `待下单` 工单、认领/退回批次（`/claim`）；可编辑字段（`PM_EDIT_FIELDS`）：`priority`、`sort_order`、`order_kind`、`supply_mode`、`owner`（仅限在空值/`无人问津` 与本人姓名间切换）、`pm`、`project_code`、`experiment_id`、`study_type`、`target_name`、`target_codes`、`target_type`、`mouse_strain`、`eng_type`、`eng_method`、`eng_parent_seq`、`eng_requirement`、`remark`（不可改 `status`、`eng_result`、合成订单及到货验证字段） |
| `discovery.synthesis_progress.assay_edit` | 实验员操作（`assay`） | 仅可修改已有工单（不可新建）；可编辑字段（`ASSAY_EDIT_FIELDS`）：`affinity_status`、`affinity_owner`、`affinity_result`、`affinity_date`、`report_reason`、`flow_status`、`flow_date`、`flow_note`（不可改 `arrival_count`、`arrival_date` 及主状态 `status`） |
| `serum.page.detail` | 跨模块跳转 | 点击行操作「详情」按 `experiment_id` 或 `project_code` 跳转免疫实验详情页（`/serum/detail?id=`） |

## 2. 数据与编号

主表为 `discovery_synthesis_order`，一行对应一个合成与验证批次。唯一约束：`uk_discovery_synthesis_order_id`（`synthesis_order_id`）、`uk_discovery_synthesis_order_source_one`（`source_one_type` + `source_one_id`）。

| 字段 | 含义 | 规则与取值 |
|---|---|---|
| `id` | 主键 ID | 数据库自增 `BigInteger` |
| `synthesis_order_id` | 系统单号 | 格式 `SYN-yyMMdd-XXXXXX`（6 位大写字母数字），创建时自动生成，保存时忽略传入值 |
| `source_one_type` / `source_one_id` | 外部来源标识 | `ngs`（`one_task_ngs_data_analyze.id`）或 `beacon`（`one_task_beacon_data_analyze.id`）；手填未关联记录为 `NULL` |
| `source_snapshot` | 外部来源快照 | JSON，保存最近一次 One 库同步或核对的 8 个字段值（见 §5） |
| `status` | 主状态 | 必填，默认 `待下单`；枚举：`待下单`、`合成中`、`待检测`、`检测中`、`已完成`、`已取消` |
| `priority` / `sort_order` | 优先级与队列号 | 四档：`吉吉国王` > `非常紧急` > `加急` > `正常`（默认 `正常`）；未完成行 `sort_order` 为 `1..N`，终态（`已完成`/`已取消`）为 `NULL`，规则见 [项目工作台共用约定](../workbench.md) |
| `order_kind` | 订单性质 | 必填，默认 `常规合成`（「序列改造」视图下新建默认 `改造`）；枚举：`常规合成`、`改造` |
| `supply_mode` | 供应方式 | 必填，默认 `合成到货`；枚举：`合成到货`、`内部转染`、`改亚型` |
| `target_name` / `target_codes` | 靶点名称与编号 | `target_name` 最长 128；`target_codes` 为大写去重 JSON 数组，关联本地 `target.snum` |
| `target_type` | 靶点类型 | 最长 64；预设 13 项：`分泌型`、`I型跨膜`、`II型跨膜`、`III型跨膜`、`IV型跨膜`、`单次跨膜`、`多次穿膜`、`GPI锚定`、`细胞膜蛋白`、`外周膜蛋白`、`脂锚定蛋白`、`胞内蛋白`、`其他`。保存传入 `target_codes` 且未传 `target_type` 时，按首个编号查 `target` 表自动推导 |
| `target_color` | 靶点颜色标记 | 枚举：`yellow`、`orange`、`red`、`green`、`blue`、`purple`（空或 `none` 清空） |
| `mouse_strain` | 小鼠品系 | 最长 128；多选或自填，按预设顺序在前、自填在后以顿号 `、` 拼接 |
| `selection_method` | 挑选方式 | 最长 128；预设：`补挑`、`EYE`、`DS`、`JX_P`、`JX_C`、`RH_P`、`RH_C`、`D`、`D模型`、`D模型-3轮`、`P`，支持多选与自填，按预设顺序以顿号拼接 |
| `synthesis_code` / `order_no` / `batch_label` | 转码 / 订单号 / 批次 | 送测转码（最长 64）、合成订单号（最长 64）、工单批次（最长 255） |
| `synthetic_corp` | 合成公司 | 最长 64；预设：`君跻`、`擎科`、`金斯瑞`、`百奥`、`内部`，支持自填 |
| `order_sender` | 下单人 | 最长 128；系统内不可编辑，只由 One 同步，原样保存订单文件上传人（多为「中文名 英文名」），见第 5 节 |
| `synthetic_count` / `arrival_count` | 合成个数 / 到货个数 | 可选非负整数（`0` 合法，空为 `NULL`；Excel 输入自动剥离 `个`/`条`） |
| `synthetic_date` / `arrival_date` / `flow_date` / `affinity_date` | 各里程碑日期 | `YYYY-MM-DD`。保存时若清空 `affinity_date` 且当次请求未传 `affinity_result`，后端自动将 `affinity_result` 清空为 `NULL` |
| `affinity_status` | 亲和力检测状态 | 枚举：`亲和力待检测`、`亲和力检测中`、`亲和力已完成`；验证前阶段为 `NULL` |
| `affinity_owner` | 亲和力人员 | 最长 64 |
| `affinity_result` | 亲和力结果 | 可空；枚举：`正常`、`阳性极少`、`全阴` |
| `report_reason` | 未出原因 | 最长 500，保留换行 |
| `flow_status` | 流式检测状态 | 枚举：`流式待检测`、`流式已完成`、`流式不适用`（无检测中状态）；验证前阶段为 `NULL` |
| `flow_note` | 流式说明 | 最长 500，保留换行 |
| `owner` | 负责人 | 最长 64，未认领可记为 `无人问津`。新建 `改造` 单、仅具 `pm_edit` 权限新建工单，或保存将 `order_kind` 设为 `改造` 时，若 `owner` 为空或 `无人问津` 自动填入当前操作人姓名首词（同时若 `pm` 为空也自动填入） |
| `remark` | 检测备注 | 最长 1000，保留换行 |
| `eng_type` | 改造类型 | 最长 128；预设：`亲和力`、`人源化`、`去PTM`、`Tm`、`PI`、`亲水性`、`稳定性`、`CIC`、`HIC`、`Tagg`、`糖基化`、`氧化风险`、`脱酰胺风险`、`同家族交叉`、`VHH序列改造`、`改亚型`、`其他`，支持多选与自填，按预设顺序以顿号拼接 |
| `eng_method` | 改造方式 | 最长 128；预设：`AI`、`NGS姐妹克隆`、`理性设计`、`饱和突变`、`其他`，支持多选与自填，按预设顺序以顿号拼接 |
| `eng_parent_seq` / `eng_requirement` / `eng_result` | 改造详情字段 | 改造序列或母本（最长 500）、改造要求（最长 1000）、改造结果（最长 500），均保留换行 |
| `project_code` / `experiment_id` / `study_type` / `pm` | 项目串联字段 | 各最长 64；`experiment_id` 仅用于跨模块关联与搜索，前端表格与抽屉不展示该列 |
| `created_by` / `created_at` / `updated_at` | 审计字段 | 创建人与创建/更新时间；序列化输出另附计算字段 `drift_fields` 与 `has_drift` |

## 3. 状态与流转

### 自动推导与手动修改规则（`sync_derived_statuses`）

当新建工单，或保存请求未显式传入 `status` 且修改了 `AUTO_STATUS_FIELDS`（`order_no`、`supply_mode`、`arrival_date`、`affinity_owner`、`affinity_date`、`report_reason`、`flow_date`、`target_type`、`target_codes`、`affinity_status`、`flow_status`），或 One 库同步回填/采用 `order_no`、`arrival_date` 时触发自动推导；若请求显式传入 `status`，直接保存人工指定的 `status`。

1. **手动切换实验子状态联动**：
   - 将 `affinity_status` 设为 `亲和力检测中`：自动将 `affinity_owner` 设为当前操作人姓名首词。
   - 将 `affinity_status` 设为 `亲和力待检测`：自动将 `affinity_owner` 清空为 `NULL`。
   - 手动设置的 `affinity_status`、`flow_status` 与 `status` 会被保留，修改备注等普通字段不会将其覆盖回退。
2. **验证前阶段**（`arrival_date`、`affinity_owner`、`affinity_date`、`report_reason`、`flow_date`、`affinity_status`、`flow_status` 均为空；或当次清空 `arrival_date` 且其余验证数据为空、子状态均未处于检测中/已完成）：
   - `affinity_status` 与 `flow_status` 置为 `NULL`。
   - 若 `order_no` 非空，或 `supply_mode` 非空且不等于 `合成到货`（即 `内部转染` 或 `改亚型`），主状态推导为 `合成中`；否则为 `待下单`。
3. **验证阶段子状态推导**：
   - **亲和力子状态**：若 `report_reason` 非空，强制设为 `亲和力待检测`（保留原 `affinity_owner`）；否则当 `affinity_status` 未设置，或当次未显式传 `affinity_status` 但修改了 `affinity_date` / `report_reason` 时，按优先级推导：`report_reason` 非空 → `亲和力待检测`；`affinity_date` 非空 → `亲和力已完成`；`affinity_owner` 非空 → `亲和力检测中`；其余 → `亲和力待检测`。
   - **流式子状态**：若 `target_type == '分泌型'`，强制设为 `流式不适用`；否则当 `flow_status` 未设置（或原为 `流式不适用`），或当次未显式传 `flow_status` 但修改了 `flow_date` 时，有 `flow_date` 为 `流式已完成`，无则为 `流式待检测`。
4. **验证阶段主状态推导**：
   - 亲和力完成判定：`affinity_status == '亲和力已完成'` **且** `affinity_date` 非空。
   - 流式完成判定：`target_type == '分泌型'`，或（`flow_status == '流式已完成'` **且** `flow_date` 非空）。
   - 两项同时满足时，主状态推导为 `已完成`（包括对应日期已填妥、将此前退回的子状态重新手动改回已完成时，也会触发主状态变为 `已完成`；若对应日期为空，仅手动将子状态设为已完成不会使主状态变为 `已完成`）。
   - 未同时满足时：若 `affinity_status` 为 `亲和力检测中`/`亲和力已完成`，或 `flow_status` 为 `流式已完成`，主状态为 `检测中`；否则为 `待检测`。
5. **终态保持规则**：
   - 当前主状态为 `已取消` 时，始终保持 `已取消`。
   - 当前主状态为 `已完成` 时，仅当 `ASSAY_EVIDENCE_FIELDS`（`affinity_status`、`flow_status`、`affinity_date`、`flow_date`、`report_reason`、`arrival_date`、`target_type`）发生实际变更时才重新推导主状态（例如将 `已完成` 的分泌型工单改为 `I型跨膜` 会自动重开为 `检测中` 并重新入队），修改其余字段保持 `已完成`。

### 校验与错误规则

| HTTP 状态码 | 触发条件 | 错误信息 |
|---|---|---|
| `422` | 新建工单（无 `id`）时传入 `affinity_status` 或 `flow_status` | `请先创建工单，再修改实验状态` |
| `422` | `status == '已取消'` 的工单传入 `affinity_status` 或 `flow_status` | `已取消工单不可修改实验状态` |
| `422` | `report_reason` 非空（含当次传入或原值未清空）时手动将 `affinity_status` 设为 `亲和力检测中` 或 `亲和力已完成` | `请先清除未出报告原因，再修改亲和力状态` |
| `422` | 手动将 `affinity_status` 设为 `亲和力检测中` 但当前用户无法解析出姓名 | `无法识别当前亲和力人员姓名` |
| `422` | `target_type == '分泌型'`（含当次传入或原值）时手动传入 `flow_status` | `分泌型靶点不需要流式实验` |
| `422` | 调用 `/claim` 认领已被他人负责（`owner` 非空、非 `无人问津` 且非本人）的批次 | `该批次已被 {cur_owner} 认领，不可重复认领` |
| `422` | 调用 `/reorder` 时任一记录处于终态或 `sort_order` 为空 | `终态记录不参与排序` |
| `422` | 调用 `/adopt_source` 时记录无 `source_snapshot` 或未指定有效可采用字段 | `该记录没有可用的外部来源快照` / `未指定可采用的来源字段` |
| `422` | 删除已关联 One 订单（`source_one_id` 非空）的工单 | `该工单已关联 One 订单，不能删除；不再需要时请把状态改为「已取消」` |
| `403` | 仅具 `pm_edit` 权限修改他人负责的 `owner`、修改范围外字段或删除非 `待下单` 工单 | 对应权限拒绝提示 |
| `404` | 指定 `id` 的记录不存在 | `合成与验证记录不存在` |

## 4. 页面操作

工作台 / Excel 双视图切换、`Shift` 拖列调序、右键「视图」重置列序、首列「序号 / 排序」优先级队列切换与拖拽排序、表头筛选菜单及 `WorkbenchColorMark` 底色标记遵循 [项目工作台共用约定](../workbench.md)。

### 顶部 5 个阶段视图（`STATUS_VIEWS` / `view_group`）

| 阶段编号 | 视图名称 | `view_group` 参数 | 统计键 `stats` | 筛选口径 |
|---|---|---|---|---|
| `00` | 全部批次 | `""`（不传） | `all` | 全部记录（含已完成、已取消） |
| `01` | 合成中 | `synthesizing` | `synthesizing` | `status == '合成中'` |
| `02` | 待测 / 检测中 | `assay` | `assay` | `status IN ('待检测', '检测中')` |
| `03` | 已完成 | `completed` | `completed` | `status == '已完成'` |
| `04` | 序列改造 | `engineering` | `engineering` | `order_kind == '改造'` |

- 点击阶段视图卡片时，自动清空顶部 `status` 筛选和状态列的表头筛选条件。
- 后端 `POST /list` 另支持 `view_group = 'wait_order'`（`status == '待下单'`）与 `'cancelled'`（`status == '已取消'`），并在 `stats` 中返回对应计数。所有 `stats` 计数跟随当前关键字、顶部筛选和表头筛选，忽略 `view_group` 与 `quick_filter`。

### 右上角胶囊快捷筛选（`quick_filter`）

- **左键点击**：切换 `quick_filter = 'unassigned'`，只看 `status != '已取消' AND owner == '无人问津'` 的待认领批次（胶囊文案：`{stats.unassigned} 个批次无人问津待认领`），再次左键取消。
- **右键点击**：切换 `quick_filter = 'has_issue'`，只看 `flow_note` 非空或 `report_reason` 非空的批次（胶囊文案：`{stats.has_issue} 个批次有检测说明或异常`），再次右键取消。

### 搜索、筛选与表头菜单

- **常驻筛选栏（7 项）**：`订单号`、`靶点`（远程搜索本表已录入靶点）、`靶点类型`（含顶部专属项 `非分泌型`，匹配 `target_type` 非空且不含 `"分泌"`）、`小鼠品系`、`负责人`（左键单选、右键追加）、`亲和力结果`、`合成日期区间`。
- **高级筛选区（齿轮展开，3 行）**：
  - 第 1 行：`工单批次`、`送测转码`、`合成公司`、`挑选方式`、`供应方式`、`检测备注`、`未出原因`、`流式说明`。
  - 第 2 行：`项目编号`（同时匹配 `project_code` 与 `experiment_id`）、`PM`、`课题类型`、`优先级`、`状态`（合并主状态、亲和力子状态、流式子状态共 12 项；选中子状态时后端限定 `status IN ('待检测', '检测中')`）、`到货日期区间`、`亲和力日期区间`、`流式日期区间`。
  - 第 3 行：`订单性质`、`改造类型`、`改造方式`；右侧提供「重置全部筛选」按钮（右键点击「查询」按钮同样触发重置，保留阶段视图与队列排序模式）、「显示字段」（工作台视图）、「列表导出」。
- **匹配规则**：单号类（`order_no`、`synthesis_code`、`batch_label`、`project_code`）填单个词按包含匹配，用逗号、空格、分号或换行分隔多个词按精确值 `IN` 匹配；顿号多值字段（`mouse_strain`、`selection_method`、`eng_type`、`eng_method`）按拆分后包含某项匹配；文本说明（`remark`、`report_reason`、`flow_note`）按包含匹配。
- **表头筛选（`HEADER_MENU_COLUMNS`）**：除 `sort_order`、`target_codes`、`order_sender`、`actions` 外的 32 个业务列均开放表头菜单（单号类 `synthesis_code`/`order_no`/`batch_label`/`project_code` 为 `recent` 最近 200 项，长文本 `remark`/`report_reason`/`flow_note`/`eng_parent_seq`/`eng_requirement`/`eng_result` 为 `search` 输入后查询，其余为 `all`）。`status` 表头菜单对亲和力/流式子状态显示 `topOnly` 提示，`target_type` 表头菜单对 `非分泌型` 显示 `topOnly` 提示。
- **批量标记靶点底色**：需 `edit` 权限。在 Excel 视图下框选多行后，点击 `靶点名称` 表头菜单中的颜色圆点或点击选中行内的色点，调用 `POST /save_batch` 批量更新选中行的 `target_color`。

### 状态胶囊、靶点角标与右侧抽屉

- **状态列胶囊（`SynthesisAssayStatusEditor.vue`）**：
  - 主状态为 `待检测` 或 `检测中` 时，工作台状态列与抽屉状态框显示实验状态胶囊；其余主状态显示主状态下拉标签。
  - **非分泌型**（`flow_status != '流式不适用'`）：显示左右双拼胶囊 `亲·待测 / 亲·测中 / 亲·完成`（左弹下拉 `待测 / 测中 / 完成`）与 `流·待测 / 流·完成`（右弹下拉 `待测 / 完成`）。
  - **分泌型**（`flow_status == '流式不适用'`）：显示单胶囊 `亲和力·待测 / 亲和力·测中 / 亲和力·完成`（右弹下拉 `亲和力·待测 / 亲和力·测中 / 亲和力·完成`）。
  - 当 `report_reason` 非空时，亲和力胶囊不可点击修改。
- **靶点类型与右上角微角标**：工作台视图下 `target_type` 含 `"分泌"` 呈玫红色，其余非空值呈青碧色，支持行内点击切换；靶点单元格右上角按条件显示微角标：`改造`（`order_kind == '改造'`）、`转染`（`内部转染`）或 `亚型`（`改亚型`）、`变更`（`has_drift == true`，悬停显示差异详情）。
- **编辑抽屉（540px 无遮罩）**：
  - 分区顺序：`1. 状态 / 归属` → `2. 改造信息`（仅 `order_kind == '改造'` 时展开） → `3. 项目信息` → `4. 合成订单` → `5. 到货与验证`。
  - 顶部工具栏含 `详情`、`认领`、`删除`、`加单`、`全部采用`（`has_drift && canFullEdit` 时显示）及 `上一条 / 下一条`。
  - **新建与「加单」**：右上角「新建工单」在「序列改造」视图下默认创建 `order_kind = '改造'`，其余视图默认创建 `常规合成`。抽屉「加单」复制当前工单的项目、靶点、小鼠品系与改造需求等基础字段（具备 `edit` 权限时额外复制 `selection_method`、`synthesis_code`、`batch_label`；`owner` 为 `无人问津` 或仅具 `pm_edit` 且非本人时不复制），生成新行后立即触发 `check_remote` 尝试自动绑定 One 库同转码/批次的下一笔未关联订单。
- **Excel 粘贴与导出**：Excel 粘贴支持标准列名与别名映射（`SHEET_HEADER_ALIASES`）及靶点名称/编号双向解析校验，通过 `POST /save_batch` 单事务保存；「列表导出」调用 `POST /export_list` 导出 38 列 Excel。

## 5. 跨模块联动 / 外部集成

工单在本系统创建，或由定时同步把 One 库新出现的订单自动建成新行（见第 6 项）。外部数据源为 One 库 `one_task_ngs_data_analyze`（关联 `one_task_ngs_task`）、`one_task_beacon_data_analyze`（关联 `one_task_beacon_task`）及 `orderhis`（当 `orderno` 为空但有 `refstr` 文件名时反查订单号与合成公司）；下单人按 `refstr` 文件名取订单文件上传人（ngs 为 `fileinfoSelected.uploader`，beacon 为 `beacon_upload_file.uploaded_by`）。

1. **两段式加载与即时核对（`POST /check_remote`）**：
   - 首屏先由 `POST /list` 查本地主库立即渲染；随后前端异步调用 `POST /check_remote`（连接/读取超时各 1 秒，最多 500 行），或在单行修改 `order_no`、`synthesis_code`、`batch_label` 及打开抽屉时点查。One 库不可用时返回 `remote_available: false`，页面提示「外部订单库暂时连不上，本次未核对外部订单」。
2. **未绑定行的三轮自动匹配绑定**：
   - 对 `source_one_id` 为空且填有 `order_no`、`synthesis_code` 或 `batch_label` 的行，排除已被其他本地工单占用的 One 记录，且要求双方非空订单号兼容（相同，或 `CN`/`GS` 前缀互为别名且合成个数一致），依次按三轮匹配（同轮多候选优先选 `synthetic_count` 相同者，否则取 `id` 最大者）：
     1. `order_no` 精确匹配 `a.orderno`；
     2. `batch_label`（取 `|` 前主干及剥离 `_数字`/`_C数字` 后基础名）匹配 `t.projectid`、`t.projectcode` 或 `t.batchname`；
     3. `synthesis_code` 匹配 `t.synthesiscode` 或 `t.projectcode`。
3. **快照字段、自动回填与差异采用**：
   - `SNAPSHOT_STORED_FIELDS`（存入 `source_snapshot` 的 **8 个字段**）：`order_no`、`synthetic_corp`、`synthetic_count`、`synthetic_date`、`arrival_count`、`arrival_date`、`synthesis_code`、`batch_label`。
   - `DRIFT_COMPARE_FIELDS`（参与差异比对的 **6 个执行字段**）：`order_no`、`synthetic_corp`、`synthetic_count`、`synthetic_date`、`arrival_count`、`arrival_date`。
   - 本地为空的快照字段（或重新绑定时仍等于上一版快照自动填入值的字段）自动用 One 库值回填，触及 `order_no` 或 `arrival_date` 时自动推导状态并在进入终态时重编队列。
   - `order_sender` 不进快照、不比对差异，每次核对都直接改成 One 当前值（One 没有上传记录时清空）。
   - 本地已有非空值且与快照不一致时（本地 `CN` 与远端 `GS` 前缀订单号除外），不覆盖本地值，返回 `drift_fields` 与 `has_drift = true`；抽屉字段下显示「来源最新」横幅，由具备 `edit` 权限的用户点击「采用」或「全部采用」调用 `POST /adopt_source` 覆盖。
4. **本地重号提示与远端候选补全**：
   - `duplicates`（请求行数 ≤ 50 时返回）：检测当前行与本地其他工单在 `order_no`、`batch_label`、`synthesis_code` 上的重号（已绑定 One 的行前端仅提示 `order_no` 重号，未绑定行提示三项重号），抽屉横幅支持右键复制冲突编号。
   - `candidates`（单行点查 `len(rows) == 1` 时返回，最多 20 条）：返回同 `synthesis_code` 或同 `batch_label` 下尚未被占用的其他 One 库订单快照，供抽屉 `order_no`、`batch_label`、`synthesis_code` 输入框自动补全选择。
5. **修改标识字段自动解绑（`_apply_fields`）**：
   - 已绑定 `source_one_id` 的工单在保存时，若修改了 `order_no`，或修改了 `synthesis_code` / `batch_label`（且当次未传 `order_no`、当前 `order_no` 仍等于原快照 `order_no`，此时一并清空 `order_no`），后端自动将 `source_one_type` 与 `source_one_id` 置为 `NULL` 解除绑定并清空 `order_sender`；若解绑后 `order_no`、`synthesis_code`、`batch_label` 均为空，同时清空 `source_snapshot`。保存后前端立即调用 `check_remote` 按新值重新匹配。
6. **One 新订单自动建单（`collect_new_remote_orders`，随定时任务与 `/sync_now` 执行）**：
   - 范围：ngs 与 beacon 中 `a.created >= ONE_AUTO_CREATE_SINCE`（`2026-11-01`，此前的订单已按总工单 Excel 导入对齐）、未删除且未被本地工单关联的记录。
   - 跳过改造类批次：订单文件名（`refstr`）`_数字clones` 前的前缀（取不到时用 `t.projectcode`）按 `_` 拆分后第 5 段为 `M数字`（如 `23R037_RM_C_W_M1_20261102`）时不建，这类改造/改亚型/转染工单由人工先建空单，再经三轮匹配绑定。
   - 去重：有订单号的按订单号建一条，本地已有同订单号（不区分大小写）时不建；没有订单号的按文件只建一条 `待下单` 行，同文件已有订单号或已有记录在本地时不建。同文件先建了无订单号的 `待下单` 行、后来同文件另一条记录才下单时，改绑那一行（按上一版快照替换自动填入值）而不是再建。
   - 字段：快照 8 个字段与下单人取 One；`priority`、`owner`、`pm`、`project_code`、`experiment_id`、`study_type`、`mouse_strain` 沿用同 `batch_label` 或同 `synthesis_code` 的最新本地行；靶点编号取 `t.target` 中的 `[20R147]`，没有时取文件前缀或转码开头的 `数字数字R数字数字数字`，单个编号时名称取靶点库，否则用 One 的名称，都取不到时沿用同批次行的靶点；仍无小鼠品系时按转码品系标记（如 `RMCW`）取本地同标记行中最多的品系。`created_by` 为 `One同步`，状态按订单号与到货日期自动推导，并按优先级排到同优先级队尾。
   - 删除：已关联 One 的工单不能删除，只能改为 `已取消`；要彻底去掉需在 One 删除对应记录，否则下次同步会重新建出。

## 6. 接口

| 方法 | 路径 | 权限 | 用途 |
|---|---|---|---|
| `POST` | `/api/discovery/synthesis-progress/list` | `discovery.page.synthesis_progress` | 分页查询列表与顶部视图/胶囊统计（支持 `view_group`、`quick_filter`、`field_filters`、`sort_field`、`sort_dir`） |
| `POST` | `/api/discovery/synthesis-progress/column_values` | `discovery.page.synthesis_progress` | 表头筛选取值列表（支持 `field`、`value_keyword`、`value_limit`、`value_order`） |
| `GET` | `/api/discovery/synthesis-progress/options` | `discovery.page.synthesis_progress` | 获取下拉与校验选项：`statuses`、`affinity_statuses`、`flow_statuses`、`priorities`、`order_kinds`、`supply_modes`、`affinity_results`、`target_types`、`mouse_strains`、`selection_methods`（挑选方式）、`synthetic_corps`、`eng_types`、`eng_methods`、`owners`、`pms` |
| `GET` | `/api/discovery/synthesis-progress/recorded_targets` | `discovery.page.synthesis_progress` | 顶部靶点筛选远程搜索本表已录入靶点（`keyword`、`limit` 默认 50、最大 200） |
| `POST` | `/api/discovery/synthesis-progress/check_remote` | `discovery.page.synthesis_progress` | 按本地行 `ids` 核对 One 库快照，返回 `updated_items`、`linked`、`updated`、`duplicates`、`candidates`、`remote_available` |
| `POST` | `/api/discovery/synthesis-progress/save` | `edit` / `pm_edit` / `assay_edit` | 单条新增（无 `id`，需 `edit` 或 `pm_edit`）或按字段范围修改（有 `id`） |
| `POST` | `/api/discovery/synthesis-progress/save_batch` | `edit` / `pm_edit` / `assay_edit` | Excel 视图粘贴或批量颜色标记单事务保存（`items`） |
| `POST` | `/api/discovery/synthesis-progress/claim` | `edit` / `pm_edit` | PM 认领空白/`无人问津` 批次，或将本人批次退回 `无人问津` |
| `POST` | `/api/discovery/synthesis-progress/reorder` | `edit` / `pm_edit` | 优先级队列拖拽排序（`moved_id`、`target_id`） |
| `POST` | `/api/discovery/synthesis-progress/delete` | `edit` / `pm_edit` | 删除工单并重编队列（已关联 One 的工单不可删除；`pm_edit` 仅可删除 `待下单` 状态工单） |
| `POST` | `/api/discovery/synthesis-progress/adopt_source` | `discovery.synthesis_progress.edit` | 采用外部来源快照覆盖本地差异字段（`id`、可选 `fields`） |
| `POST` | `/api/discovery/synthesis-progress/sync_now` | `discovery.synthesis_progress.edit` | 手动立即执行一次定时同步（批量匹配与进度回填，再自动建单），返回 `linked`、`created`、`updated`、`unchanged`、`total` |
| `POST` | `/api/discovery/synthesis-progress/export_list` | `discovery.page.synthesis_progress` | 按当前筛选与排序导出 Excel（`.xlsx`） |

## 7. 定时任务

- **任务代码**：`job.discovery_synthesis_order_sync`（名称：「合成与验证外部订单同步」，实现：`jobs/synthesis_order_sync.py`）。
- **默认周期**：每隔 1 小时执行一次（`schedule: "interval", every: 1, unit: "hour"`，起始时间 `00:20`）。在系统管理页面修改任务开关或调度配置后，通过 `jobs/registry.py` 的 `apply_job_schedule` 立即生效，无需重启服务。
- **执行逻辑**：调用 `service.sync_from_one`，筛选本地主状态处于非终态（`待下单`、`合成中`、`待检测`、`检测中`）且已绑定 `source_one_id` 或 `supply_mode == '合成到货'` 的工单，以 3 秒连接超时、15 秒读取超时批量核对 One 库并回填合成与到货字段；随后按第 5 节第 6 项把 One 新订单建成新行。当环境未配置或无法连接 `ONE_DB_URL` 时自动跳过，运行日志记录为 `skipped`（「未配置 ONE_DB_URL，已跳过」）。
