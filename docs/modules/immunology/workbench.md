# 免疫工作台

> 管理免疫项目开展前的筹备信息与方案，并在开展后关联正式免疫实验。相关：[项目工作台共用约定](../workbench.md)、[发现工作台](../discovery/workbench.md)

## 1. 入口与权限

前端路由为 `/serum/workbench`，方案路由为 `/serum/workbench/scheme?id=<工作台主键>`。菜单功能开关为 `menu.serum.workbench`。

| 权限码 | 范围 |
|---|---|
| `serum.page.workbench` | 查看页面、列表、详情、选项、靶点、表头取值和导出 |
| `serum.workbench.edit` | 编辑全部字段；新建、复制、删除、开展、下架和队列拖动 |
| `serum.workbench.draft_edit` | 新建和复制；维护、删除草稿；不能修改状态、审核人、审核结果和可否开展 |
| `serum.workbench.support_edit` | 编辑已有记录的“小鼠后勤”和“抗原”字段 |
| `serum.project.edit` / `serum.project.edit_all` | 开展时额外校验的正式项目编辑权限 |

多项工作台编辑权限按字段范围合并。

## 2. 数据与编号

| 表 | 用途 |
|---|---|
| `serum_imm_workbench` | 工作台主记录 |
| `serum_imm_project` | 开展后的正式免疫项目 |
| `serum_imm_mouse` | 小鼠分组 |
| `serum_imm_antigen` | 免疫抗原 |
| `serum_imm_step` | 免疫步骤 |
| `serum_titer_target` | 效价标靶 |
| `serum_titer_pc` | 效价阳参 |

| 字段 | 含义 | 规则 |
|---|---|---|
| `experiment_id` | 实验号 | 工作台与正式项目内分别唯一 |
| `project_code` | 项目编号 | 保存时去除全部空白；开展必填 |
| `plan_status` | 工作台状态 | 默认 `草稿`；`已开展` 只能由开展操作写入 |
| `display_status` | 列表展示状态 | 未开展取 `plan_status`；开展后取正式项目 `project_status` |
| `can_start` | 开展条件标记 | `是` / `否`，与状态独立 |
| `priority` / `sort_order` | 优先级与队列位 | 规则见[共用约定](../workbench.md) |
| `species_cross` | 种属交叉 | `人`、`猴`、`鼠`、`狗`、`猫`、`空白`多选，英文逗号存储 |
| `immuno_method` | 免疫方式 | `蛋白`、`DNA`、`LNP`、`细胞`、`混合`多选，英文逗号存储 |
| `mouse_strain_category` / `mouse_strain` | 归类鼠型 / 小鼠品系 | 有小鼠分组时按分组顺序去重后用顿号展示；两组及以上时在工作台只读 |
| `mouse_remark` / `antigen_remark` / `remark` | 备注 | 保留换行，最长 255 字符 |

草稿号格式为 `SCP-YYYYMMDD-HHMMSS-XXXX`，`XXXX` 是 4 位大写字母或数字。首次保存时生成，冲突时重新分配。开展后的正式实验号为 `{project_code}{两位起始序号}`；后缀从 `01` 起选择空闲值，超过两位时按实际数字输出。

方案保存提交 `mouse_groups`、`antigens`、`steps`、`titer_targets`、`titer_pcs` 五个完整集合。子记录 ID 必须属于当前实验号，步骤引用的组别和抗原必须存在于同一份方案。`scheme_revision` 只覆盖方案页编辑的头字段和五类子表；版本不一致返回 `409`，页面提示后重载。

归类鼠型和小鼠品系以小鼠分组为准：没有分组时，工作台保存写入 G1；只有一组时改这一组；两组及以上只能在方案页改。开展时正式项目取全部分组按顺序去重、顿号拼接，没有分组时用工作台的值。筛选命中分组里的值，没有分组时比工作台的值。

未开展记录保存时联动隐藏的方案头字段：改了靶点编号且未提交 `target_type`，按首个编号查靶点库推导靶点类型；改了靶点名称或小鼠品系且未提交项目名称，名称为空或仍是旧的自动名称时，重写为“{靶点}基于{品系}的抗体发现”，手改过的名称不变。

## 3. 状态与流转

| 展示分组 | 判定 |
|---|---|
| 计划中 | 未开展，且 `plan_status` 不是 `已取消` 或 `小鼠KO致死` |
| 进行中 | `plan_status=已开展`，正式项目未到终态 |
| 已完成 | 正式项目状态为 `结题` 或 `无效价处死` |
| 已取消 | 开展前状态为 `已取消` 或 `小鼠KO致死` |

全量编辑用户可把未开展记录设为 `草稿`、`筹备中`、`小鼠KO致死` 或 `已取消`。`已取消` 和 `小鼠KO致死` 不能开展。

开展要求项目编号和负责人，创建 `serum_imm_project`，初始 `project_status=规划中`，把五类方案子表切换到正式实验号，并将工作台设为 `已开展`。正式项目的对齐字段在工作台只读。

审核人 `reviewer` 也是对齐字段，工作台和免疫实验列表都只能从人员下拉中选择：未开展时在工作台维护，改审核结果会自动写入当前用户；开展时复制到正式项目，之后工作台显示正式项目的值，只能在免疫实验列表的“审核人”列修改，改审核结果不再覆盖。效价实验列表的“审核人”列只读取正式项目的值，不单独存储。

下架只接受正式状态 `规划中` 且没有效价工单、FACS 板或 ELISA 板的项目。操作把正式字段写回工作台，为方案分配新的草稿号，删除正式项目，并将工作台恢复为 `草稿`。

正式项目状态写入 `结题` 或 `无效价处死` 时，保存钩子把工作台行移出队列；离开终态时加入当前优先级档末尾。列表与导出不修改状态或队列。

## 4. 页面操作

关键字只搜索项目名称、项目编号、项目集编号和实验号。单个词按包含匹配，并按上述字段顺序计算相关性，再按 `id DESC`；多个词对这四类字段做精确匹配。

| 区域 | 控件 |
|---|---|
| 顶部 | 关键字、靶点、PM、课题类型、免疫方式、归类鼠型、小鼠运输、抗原到货 |
| 齿轮高级区 | 审核结果、开展条件、优先级、开展人、审核人、状态、种属交叉、小鼠品系、纯合/杂合、提供地区、代下扩繁、抗原来源、LNP 下单、冲击细胞、方案内容 |
| 表头 | 已登记业务列的取值、条件和排序；接口为 `POST /api/serum/workbench/column_values` |

“方案内容”看小鼠组、抗原、步骤、效价靶点、阳参五类子表是否至少有一条记录，不代表方案完整；方案页自动生成、尚未保存的 G1 不算。

状态卡为“全部项目、计划中、进行中、已完成、已取消”。点击切换 `view_group`，并清空顶部和表头的状态条件。卡片统计不看状态视图、状态和可开展条件（顶部和表头都不看），保留其他列表条件。绿色胶囊左键在“计划中且可开展”与未启用之间切换。

工作台和 Excel 交互、列序、显示字段、队列排序、靶点组件及 `_expected` 并发控制见[共用约定](../workbench.md)。工作台行内可编辑状态、小鼠运输、抗原到货、审核结果、可否开展和优先级。左键行打开无模态抽屉；再次点击同一行、右键任意行或点击表外关闭。

未开展行的操作为“方案、复制、删除”。开展入口位于方案页。已开展行的操作为“详情、复制、下架”；“详情”左键进入正式项目查看页，右键进入正式项目编辑页，分别校验对应页面和记录编辑权限。

复制会创建 `草稿`、`正常` 优先级和新的草稿号，并复制项目方案骨架及五类子表。小鼠号、笼位和步骤实际日期清空。删除仅适用于未开展且未关联正式项目的记录，并同时删除该草稿号下的方案子表。

“列表导出”沿用当前全部筛选。页面没有导入入口。

## 5. 跨模块联动

开展后，工作台与正式免疫项目通过 `experiment_id` 关联。正式项目改项目编号时，后端生成新的实验号并同步关联记录。

发现工作台的效价下发读取正式免疫项目和效价数据；字段映射见[发现工作台 §5](../discovery/workbench.md#5-跨模块联动)。

## 6. 接口

| 方法 | 路径 | 权限 | 用途 |
|---|---|---|---|
| POST | `/api/serum/workbench/list` | `serum.page.workbench` | 分页、筛选和状态统计 |
| POST | `/api/serum/workbench/column_values` | `serum.page.workbench` | 表头取值 |
| POST | `/api/serum/workbench/export_list` | `serum.page.workbench` | 按当前条件导出 |
| GET | `/api/serum/workbench/options` | `serum.page.workbench` | 编辑和筛选选项 |
| GET | `/api/serum/workbench/recorded_targets` | `serum.page.workbench` | 搜索本工作台已录入靶点 |
| GET | `/api/serum/workbench/detail` | `serum.page.workbench` | 主记录、方案子表和 `scheme_revision` |
| POST | `/api/serum/workbench/save` | 任一工作台编辑权限 | 新建或更新传入字段 |
| POST | `/api/serum/workbench/save_batch` | 任一工作台编辑权限 | 单事务批量保存 |
| POST | `/api/serum/workbench/save_scheme` | `serum.workbench.edit` 或 `serum.workbench.draft_edit` | 按 `scheme_revision` 保存完整草稿方案 |
| POST | `/api/serum/workbench/delete` | `serum.workbench.edit` 或 `serum.workbench.draft_edit` | 删除允许范围内的未开展记录 |
| POST | `/api/serum/workbench/start` | `serum.workbench.edit`，并具备 `serum.project.edit` 或 `serum.project.edit_all` | 开展为正式免疫项目 |
| POST | `/api/serum/workbench/unlist` | `serum.workbench.edit` | 下架正式项目 |
| POST | `/api/serum/workbench/copy` | `serum.workbench.edit` 或 `serum.workbench.draft_edit` | 复制为草稿 |
| POST | `/api/serum/workbench/reorder` | `serum.workbench.edit` | 将 `moved_id` 放到 `target_id` 的队列位 |

## 7. 定时任务与外部集成

`job.serum_auto_update_status` 默认每天 01:00 根据免疫步骤日期更新正式项目状态，并可创建采血节点对应的效价工单。它跳过 `结题`、`无效价处死` 和 `加免中`，不修改工作台 `plan_status`。
