# 镁伽自动化流式工单

## 1. 当前范围

当前模块只负责：

- 手工新建、编辑和校验流式工单；
- 维护样本板、细胞板和 PC 信息；
- 生成设备下发 Payload，并保存每次下发记录；
- 模拟设备确认执行、暂停、恢复、完成和失败。

权限细化、上游业务建单、真实设备通信和检测结果回传暂不在本阶段实现。

## 2. 数据模型

### `mega_flow_work_order`

工单主表保存订单编号、名称、检测类型、优先级、状态和编辑内容。

- `order_no` 必填，但不要求唯一；
- `content` 只保存 `pc_infos`、`sample_plates`、`cell_plates`；
- `project_nos`、`targets`、样本板和细胞板条码数组用于列表筛选；
- `content_hash` 用于检测并发修改。

`detect_plan` 和检测板条码不属于当前工单编辑模型。设备 Payload 中需要的“样本板 × 细胞列”任务在下发时由 `cell_keys` 动态生成。

### `mega_flow_work_order_dispatch`

每次发送生成一条下发记录：

- `dispatch_id` 是下发记录的唯一编号；
- `payload` 和 `payload_hash` 保存当次发送快照；
- `content_hash_at_send` 保存发送时的工单版本；
- `status` 记录 `pending`、`running`、`completed`、`failed` 或 `voided`；
- `pause_state` 记录 `pausing`、`paused` 或 `resuming`。

不增加 `active_key`。代码在锁定工单行后检查当前未终止的下发记录；上一条记录未结束时不能再次发送。

## 3. 编辑与校验

保存要求：

- 订单编号非空；
- `data_type` 和 `priority` 必须是元数据中声明的值；
- 编辑已有工单时必须提交 `expected_content_hash`。

业务校验要求：

- 每块样本板具有非空且不重复的条码；
- 每块样本板恰好包含 A01-H12 共 96 个不重复孔位；
- 孔位类型只能是 `SAMPLE`、`PC`、`NC`、`ISO`、`TAG`、`BLANK`；
- PC、ISO、TAG 孔位可以不选择关联信息；选择后才校验引用是否存在、类型是否匹配；
- 每块细胞板具有非空且不重复的条码；
- 每块细胞板恰好包含编号 1-12 的 12 列；
- 至少存在一个已命名细胞列；
- 每块样本板至少选择一个有效细胞列；
- 样本板与细胞板条码不能重复。

校验问题包含字段路径，前端可定位到对应板、孔位或基础字段。

## 4. 状态流转

```text
draft / failed / execution_failed
  └─ 校验通过 → validated

validated
  └─ 发送 → sent（下发记录 pending）

sent
  ├─ 确认执行 → running（下发记录 running）
  ├─ 执行失败 → execution_failed
  └─ 请求暂停 → paused + pausing

running
  ├─ 完成 → completed
  ├─ 执行失败 → execution_failed
  └─ 请求暂停 → paused + pausing

paused
  ├─ 设备确认暂停 → paused + paused
  ├─ 内容未变化时请求恢复 → paused + resuming
  ├─ 设备确认恢复 → sent 或 running
  └─ 确认保存修改 → validated，原下发记录 voided
```

只有设备已确认暂停（`pause_state=paused`）后才允许编辑和暂停校验。`pausing`、`resuming` 期间禁止修改。

`completed` 和 `cancelled` 是终态。已发送过但未执行中的工单可以在停止后作废；未发送工单直接删除。

## 5. Payload

Payload 沿用工单的平级数据结构：

- `pc_infos`、`sample_plates`、`cell_plates` 各保存一次；
- 样本板通过 `cell_keys` 引用需要使用的细胞板列；
- 发送时补充 `dispatch_id`、订单编号、名称、检测类型和优先级；
- 不提前展开重复的“样本板 × 细胞列”任务，设备可按 `cell_keys` 生成执行任务。

当前阶段不生成或持久化检测板条码，也不发送仅供系统内部使用的状态、摘要和数据库 ID。

## 6. API

```text
GET  /api/mega-automation/flow-work-orders/meta
POST /api/mega-automation/flow-work-orders/list
GET  /api/mega-automation/flow-work-orders/{order_id}
POST /api/mega-automation/flow-work-orders/save
POST /api/mega-automation/flow-work-orders/{order_id}/validate
POST /api/mega-automation/flow-work-orders/{order_id}/dispatch
POST /api/mega-automation/flow-work-orders/{order_id}/confirm-execution
POST /api/mega-automation/flow-work-orders/{order_id}/pause
POST /api/mega-automation/flow-work-orders/{order_id}/pause-ack
POST /api/mega-automation/flow-work-orders/{order_id}/resume
POST /api/mega-automation/flow-work-orders/{order_id}/resume-ack
POST /api/mega-automation/flow-work-orders/{order_id}/complete
POST /api/mega-automation/flow-work-orders/{order_id}/fail
POST /api/mega-automation/flow-work-orders/{order_id}/delete
POST /api/mega-automation/flow-work-orders/{order_id}/cancel
```

## 7. 前端行为

- 新建和复制先进入本地未保存页面，不提前写入空草稿；
- 复制时清空订单编号，保存前要求重新填写；
- 已有工单加载失败时禁止保存，避免误创建新工单；
- 保存失败后不继续校验；
- 从详情页返回列表时重新加载列表；
- 列表不展示下发次数和失败摘要。

## 8. 数据库升级

新建数据库直接使用 `docs/vita-database.sql`。

旧开发库应先清理空订单编号，再执行：

```sql
ALTER TABLE mega_flow_work_order
  MODIFY order_no VARCHAR(255) NOT NULL COMMENT '订单编号';
```

如果开发过程中曾添加订单编号唯一索引或 `active_key`，按 SQL 文件中的迁移注释移除。

## 9. 业务概念与边界

### 9.1 工单的核心对象

当前工单围绕两类实体组织：

1. 样本板：记录样本板条码、项目号、靶点、二抗、96 孔布局以及要检测的细胞；
2. 细胞板：记录细胞板条码以及 1-12 列的细胞信息。

当前阶段的“检测任务”可以理解为：

```text
一块样本板 + 一个已选择的细胞板列 = 一个待下发的检测组合
```

一块样本板可以选择多个细胞列，所以会生成多个检测组合。同一项目和靶点下的组合会在 Payload 中归组。

这里的检测组合不等于已经存在一块有条码的检测板。检测板条码属于后续设备执行或结果回传阶段的数据，当前编辑页面不录入，也不保存在工单 `content` 中。

### 9.2 当前阶段刻意不处理的内容

- 不根据上游订单自动创建流式工单；
- 不调用真实设备 HTTP、消息队列或 SDK；
- 不定义检测板条码生成规则；
- 不自动消费设备结果；
- 不把结果同步到效价等其他业务模块；
- 不在本阶段强制接入细粒度权限。

这些边界的目的，是先把工单自身的数据结构、编辑、校验、状态和下发快照稳定下来。

## 10. 工单内容结构

### 10.1 基础字段

主表基础字段包括：

- `order_no`：订单编号，必填但允许重复；
- `order_name`：订单名称，可选；
- `data_type`：检测类型，目前元数据包括 `TITER`、`PLAS`、`PCR`；
- `priority`：设备优先级，包括 `high`、`normal`、`low`；
- `remark`：备注；
- `status`：工单状态；
- `created_by`、`created_at`、`updated_at`、`sent_at`：操作与时间信息。

订单编号不加唯一约束。业务上可以存在编号相同的工单，系统使用主键 `id` 区分工单，使用 `dispatch_id` 区分下发记录。

### 10.2 `pc_infos`

`pc_infos` 是可以被孔位引用的辅助信息列表，当前支持：

- `SERUM`；
- `ISO`；
- `TAG`。

每项主要字段：

```text
pc_id
pc_type
pc_name
catalog_batch
source
concentration
```

PC 信息本身以及孔位到 PC 信息的关联都不是强制项：

- `PC`、`ISO`、`TAG` 孔位允许不选择 `pc_id`；
- 只有选择了 `pc_id` 时，后端才检查该 ID 是否存在；
- 选择后还会检查孔位类型与 PC 类型是否匹配；
- `PC` 对应 `SERUM`，`ISO` 对应 `ISO`，`TAG` 对应 `TAG`。

前端新建的临时 PC ID 在保存时会转换为后端生成的稳定 ID，并同步更新孔位引用。

### 10.3 `sample_plates`

每块样本板保存：

```text
barcode
project_no
target
secondary_antibody
cell_keys
wells
```

`cell_keys` 表示这块样本板选择的细胞列。键格式为：

```text
细胞板条码|列号
```

例如：

```text
CELL-20260710-01|3
```

前端允许先添加细胞板再填写真实条码。保存时会把“细胞板1”之类的页面占位引用归一成当前细胞板条码。

### 10.4 样本板孔位

每块样本板标准布局为 A01-H12，共 96 孔。孔位字段包括：

```text
well_no
content_type
sample_code
pc_id
batch
generation
```

孔位类型：

- `SAMPLE`：样本；
- `PC`：阳性对照类型孔；
- `NC`：阴性对照类型孔；
- `ISO`：同型对照类型孔；
- `TAG`：标签对照类型孔；
- `BLANK`：空孔。

`SAMPLE` 孔可以填写 `sample_code`。`PC`、`ISO`、`TAG` 孔可以选择 PC 信息，也可以仅保留孔位类型而不关联具体内容。

### 10.5 `cell_plates`

每块细胞板保存：

```text
barcode
columns
```

每块板固定包含编号 1-12 的 12 列。每列可保存：

```text
column_no
cell_name
cell_type
species
batch
generation
cell_count
catalog_no
source
```

未填写 `cell_name` 的列不作为可选择的检测细胞。工单至少需要一个已命名的细胞列，每块样本板至少选择一个有效细胞列。

### 10.6 搜索冗余字段

主表中的以下 JSON 数组由 `content` 自动提取：

- `project_nos`；
- `targets`；
- `sample_plate_barcodes`；
- `cell_plate_barcodes`。

这些字段只用于列表过滤，不是第二份可独立编辑的数据源。保存工单时由后端重新计算，避免与 `content` 不一致。

## 11. 保存、版本与校验流程

### 11.1 保存

新建工单时，前端先保留本地草稿；用户点击保存且订单编号非空后才创建数据库记录。

编辑已有工单时，前端提交当前加载到的 `content_hash`：

```text
expected_content_hash
```

后端锁定工单行，并比较当前数据库版本：

- 一致：继续保存；
- 不一致：拒绝保存，提示刷新；
- 内容没有变化：返回当前详情，不重复更新数据库。

已校验工单只要内容发生变化，就回到 `draft`。执行失败工单修改内容后也回到 `draft`，然后重新校验、重新发送。

### 11.2 校验失败

校验失败时：

- 工单状态变为 `failed`；
- `error_message` 保存合并后的错误描述；
- 接口同时返回带字段路径的 `issues`；
- 前端展示错误列表，并尽可能定位到相关样本板或字段。

`failed` 表示工单内容校验失败，不是设备执行失败。设备执行失败使用 `execution_failed`。

### 11.3 普通状态下校验

普通编辑状态的操作顺序：

```text
保存当前页面内容
  → 保存成功
  → 使用最新 content_hash 发起校验
  → 校验通过后进入 validated
```

如果保存失败，前端不会继续调用校验接口。

### 11.4 暂停状态下校验

暂停后的编辑流程与普通保存不同：

1. 请求停止后，工单进入 `paused`，下发记录进入 `pausing`；
2. 设备确认暂停后，下发记录变为 `paused`；
3. 只有此时页面才可编辑；
4. 用户点击校验时，后端先比较本地内容与发送时的 `content_hash_at_send`；
5. 内容未变时，不保存，可直接继续原下发；
6. 内容变化时，先要求用户确认；
7. 确认后保存修改，将原下发记录置为 `voided`，工单回到 `validated`；
8. 修改后的工单需要重新发送。

这个流程避免把修改后的内容错误地附着到原来的下发记录上。

## 12. 下发记录与状态说明

### 12.1 下发编号

每次发送生成独立 `dispatch_id`，格式由后端生成，例如：

```text
DSP260710482913
```

数据库对 `dispatch_id` 保持唯一约束。工单编号是否重复与下发编号唯一性无关。

### 12.2 为什么保留下发 Payload

工单后续可能被编辑，但历史下发内容不能随之改变。因此每条下发记录保存：

- 完整 Payload；
- Payload 哈希；
- 发送时工单内容哈希；
- 下发状态；
- 暂停状态；
- 发送人和发送时间。

这样可以还原“当时实际发送了什么”，也可以判断暂停后页面内容是否发生变化。

### 12.3 当前下发记录

状态不是 `completed`、`failed`、`voided` 的最新记录视为当前有效下发记录。

发送前会锁定工单并检查当前记录。只要上一条下发仍是 `pending` 或 `running`，就拒绝创建下一条。这里依赖代码事务与工单行锁，不额外增加 `active_key` 数据库字段。

### 12.4 工单状态与下发状态的关系

```text
工单 sent              ↔ 下发 pending
工单 running           ↔ 下发 running
工单 paused            ↔ 下发 pending/running + pause_state
工单 completed         ↔ 下发 completed
工单 execution_failed  ↔ 下发 failed
修改暂停工单后 validated ↔ 原下发 voided
```

## 13. Payload 组织

Payload 顶层包含：

```text
dispatch_id
order_infos
```

当前一次下发对应一个 `order_infos` 项，其中包含：

```text
order_no
order_name
priority
project_infos
```

`project_infos` 按“项目号 + 靶点”分组。每个项目内包含二抗列表和细胞信息：

```text
project_no
data_type
target
secondary_antibody
cell_board_infos
```

每个细胞板列生成一个 `cell_board_infos` 项，其中的 `detect_board_infos` 来自选择了该细胞列的样本板。

当前 `detect_board_infos` 只表达设备要执行的样本板与细胞列组合，包含：

- 样本板条码；
- 二抗；
- 细胞板条码；
- 细胞列号；
- 96 孔信息。

当前不下发检测板条码。将来如果设备协议明确要求该字段，应根据真实协议新增，不能把尚未产生的检测板条码提前持久化到工单中。

## 14. 前端页面设计

### 14.1 列表页

列表页当前提供：

- 订单编号或名称搜索；
- 检测类型筛选；
- 工单状态筛选；
- 项目号筛选；
- 靶点筛选；
- 状态统计；
- 查看、操作和复制入口；
- 分页。

列表展示的是工单概览和当前显示状态。暂停过程中会把 `pause_state` 合并成“暂停中”“已暂停”“恢复中”等显示状态。

列表不展示“下发次数”和“失败摘要”。下发历史属于详情页信息，错误信息也不单独扩展成列表统计字段。

### 14.2 新建

点击新建后直接进入本地未保存页面：

- 页面初始化一块样本板和一块细胞板；
- 不在进入页面时写入空数据库记录；
- 订单编号未填写时不允许保存；
- 第一次保存成功后，路由替换为带数据库 `id` 的编辑地址。

### 14.3 复制

复制时：

1. 跳转到带 `copyFrom` 的本地编辑页；
2. 读取源工单详情；
3. 复制样本板、细胞板、PC 信息和基础配置；
4. 清除主键、状态、下发历史和版本信息；
5. 清空订单编号；
6. 用户确认并保存后才创建新工单。

这样不会因为点击复制就立即产生未整理的数据库草稿。

### 14.4 详情加载失败

带已有工单 ID 的页面如果加载失败：

- 显示明确错误；
- 禁止保存和状态操作；
- 不把页面静默降级成可保存的新草稿。

这用于避免网络错误或不存在的 ID 意外创建一张新工单。

### 14.5 样本板编辑

详情页支持：

- 多样本板切换；
- 板顺序调整；
- 孔位单选、区域拖选；
- 批量设置孔位类型和内容；
- PC 信息维护与可选关联；
- 选择一个或多个细胞列。

### 14.6 细胞板编辑

详情页支持：

- 多细胞板切换；
- 12 列信息维护；
- 列顺序调整；
- 常用字段与扩展字段编辑；
- 样本板对已命名细胞列的选择。

## 15. 后端代码职责

### `models/mega_automation.py`

定义工单主表和下发历史表，只负责 ORM 字段与接口序列化。

### `modules/mega_automation/content.py`

负责：

- 默认 96 孔和 12 列结构；
- 输入归一化；
- 临时 PC ID 转换；
- 细胞列引用归一化；
- 搜索数组提取；
- 工单内容哈希；
- 结构化业务校验。

### `modules/mega_automation/payload.py`

负责根据工单当前 `content` 和 `cell_keys` 构造设备 Payload，不修改数据库状态。

### `modules/mega_automation/dispatch.py`

负责：

- 生成 `dispatch_id`；
- 查询当前下发；
- 创建下发快照；
- 暂停与恢复状态变更；
- 完成、失败和作废下发记录。

### `modules/mega_automation/service.py`

负责工单 CRUD、状态边界、行锁、并发版本校验、校验流程及工单与下发状态联动。

### `modules/mega_automation/routes.py`

负责 FastAPI 路由、认证依赖和统一响应包装。业务规则不放在路由层重复实现。

## 16. 结果回传的后续边界

真实设备接入后，建议结果回传至少携带：

```text
dispatch_id
status
result payload
```

`dispatch_id` 是优先匹配键，因为它唯一标识某次实际下发。不能仅使用可能重复的 `order_no` 匹配一次设备执行。

后续可增加的回调行为：

- 设备接收成功：保持 `pending` 或进入设备定义的接收状态；
- 设备开始执行：工单 `running`，下发 `running`；
- 设备执行完成：工单 `completed`，下发 `completed`；
- 设备执行失败：工单 `execution_failed`，下发 `failed`；
- 保存设备返回的原始结果；
- 根据明确的业务规则向其他模块同步结果。

检测板条码如果来自设备结果，应当作为结果数据保存；是否回写工单、单独建结果表或建立检测板实体，需要在真实回传协议明确后决定。

## 17. 后续待办

在真实联调前仍需确认：

1. 设备发送方式、鉴权方式、超时与重试规则；
2. Payload 字段命名、空值要求和版本号；
3. 设备对暂停、恢复、完成和失败的准确回调定义；
4. 检测板条码在设备侧的产生时机；
5. 结果保存表结构与幂等键；
6. 上游自动建单时各字段的来源；
7. 正式启用后的权限项和操作审计；
8. 是否需要后台任务处理长时间无回调的下发记录。

在这些协议未确认前，不应为假设中的上下游字段继续扩展当前工单表。
