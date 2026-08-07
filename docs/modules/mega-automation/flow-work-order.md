# 镁伽自动化 · 流式工单

> **本文**：流式工单**模块本身**——数据模型、校验、状态机、Payload、Labillion 集成、API、前端页面与后端代码。  
> **跨模块流程**（效价列表入口、新建向导、预填、结果回传约定）：见 [titer-upstream-flow.md](./titer-upstream-flow.md)。

## 1. 当前范围

- 手工新建、编辑、校验流式工单；
- 维护样本板、细胞板与 PC 信息；
- 生成并保存设备下发 Payload，向 Labillion（镁伽）推送订单；
- 接收 Labillion 状态回调、主动查询状态；详情页展示 Running 进度（不入库）；
- 撤回（`sent` + 待确认）与继续（已撤回后重推）；
- 保留手动「确认执行 / 设备已暂停 / 设备已恢复 / 完成 / 执行失败」作 fallback；
- 详情提供「工单编辑 / 铺板 / Payload」三个页签。

尚未接入：检测结果业务解析入库、跨模块自动同步。

`source_id` / `orderType` 字段支持关联上游业务单（如效价 `titer_order_id`）；入口与预填逻辑不在本文，见跨模块文档。
## 2. 数据模型

### `mega_flow_work_order`

- `orderNum` 必填，不要求唯一；
- `orderType`：样品来源大类（`TITER` / `PLAS` / `PCR`），工单均为流式实验；
- `source_id`：来源业务主键，可空。效价上游创建时写入 `serum_titer_order.titer_order_id`；手工新建通常为空。同一 `orderType` 下可有多条工单共享同一 `source_id`（1:N）；
- `content` 仅存 `pc_infos`、`sample_plates`、`cell_plates`；
- `project_nos`、`targets`、样本板/细胞板条码数组用于列表筛选；
- `content_hash` 用于并发编辑冲突检测。

检测板条码与 `detect_plan` 不属于工单编辑模型。样本板用 `cell_keys`（`{ barcode, column_no }` 对象数组）引用细胞列；下发 Payload 将其放在 `orderDetail` 内原样携带，服务端不展开嵌套任务树。

### `mega_flow_work_order_dispatch`

- `dispatchId`：下发唯一编号；
- `payload` / `payload_hash`：当次发送快照（hash 供完整性预留）；
- `content_hash_at_send`：发送时的工单版本，用于暂停后“内容是否变更”；
- `status`：`pending` | `running` | `completed` | `failed` | `voided`；
- `pause_state`：`pausing` | `paused` | `resuming` | `withdrawn`（空表示无暂停流程）。

无 `active_key`。工单行锁后，存在未终止下发时不可再次发送。

## 3. 编辑与校验

保存要求：

- 订单编号非空；
- `orderType` 和 `priority` 必须是元数据中声明的值；
- 编辑已有工单时必须提交 `expected_content_hash`。

业务校验要求：

- 每块样本板具有非空且不重复的条码；
- 每块样本板必须填写项目号、靶点；
- 每块样本板恰好包含 A01-H12 共 96 个不重复孔位；
- 孔位类型只能是 `SAMPLE`、`PC`、`NC`、`ISO`、`TAG`、`BLANK`；
- PC、ISO、TAG 孔位可以不填 `pc_id`；填写时须指向已有 `pc_infos` 条目，且类型匹配（`PC`→`SERUM`，`ISO`→`ISO`，`TAG`→`TAG`）；
- 每块细胞板具有非空且不重复的条码；
- 每块细胞板恰好包含编号 1-12 的 12 列；
- 至少存在一个已命名细胞列；有名称的列必须填写细胞类型；
- 每块样本板至少选择一个有效细胞列；
- 样本板与细胞板条码不能重复。

校验问题包含字段路径，前端可定位到对应板、孔位或基础字段。

## 4. 状态流转

### 4.1 本地操作（手动 fallback）

```text
draft / failed / execution_failed
  └─ 校验通过 → validated

validated
  └─ 发送 → sent（下发记录 pending；若已配 Labillion 则同步推送）

sent
  ├─ 确认执行 → running（下发记录 running）
  ├─ 撤回（仅 pending）→ paused + withdrawn（调 Labillion 删除）
  ├─ 停止（running）→ paused + pausing
  ├─ 执行失败 → execution_failed
  └─ Labillion 回调/查询 → 见 §4.2

running
  ├─ 完成 → completed
  ├─ 停止 → paused + pausing
  ├─ 执行失败 → execution_failed
  └─ Labillion 回调/查询 → 见 §4.2

paused
  ├─ 设备确认暂停 → paused + paused
  ├─ 已撤回后继续 → sent（重建 payload 并重推 Labillion）
  ├─ 内容未变化时请求恢复 → paused + resuming
  ├─ 设备确认恢复 → sent 或 running
  └─ 确认保存修改 → validated，原下发记录 voided
```

### 4.2 Labillion 驱动（回调与主动查询共用 `apply_labillion_status`）

| Labillion | 工单 status | 下发 status | pause_state |
|-----------|-------------|-------------|-------------|
| Pending | sent | pending | （清空） |
| Running | running | running | （清空） |
| Paused | paused | running | paused |
| Finished | completed | completed | （清空） |
| Aborted | execution_failed | failed | （清空） |

- 以镁伽状态为准；本地 `withdrawn` 等不拦截回调。
- Running 时的执行进度仅由主动查询返回给前端展示，**不入库**。

只有设备已确认暂停（`pause_state=paused`）后才允许编辑和暂停校验。`pausing`、`resuming` 期间禁止修改。

`completed` 和 `cancelled` 是终态。已发送过但未执行中的工单可以在停止后作废；未发送工单直接删除。

## 5. Payload

发送时补充下发元数据，板数据放在 `orderDetail` 下（与编辑态 `content` 字段同名）：

```text
dispatchId
orderNum
orderName
orderType
priority
replyAddress
orderDetail
  pc_infos
  sample_plates
  cell_plates
```

- `replyAddress` 由 `PUBLIC_API_BASE_URL` + `/mega-automation/labillion/callback` 生成；未配置时 Payload 中为空，发送仍可在本地落库，但不会调 Labillion HTTP。
- `sample_plates[].cell_keys` 为 `{ barcode, column_no }` 对象数组，表达「样本板 × 细胞列」组合；不下发系统内部状态、摘要或数据库 ID。
- 不生成、不持久化检测板条码。
- 详情「Payload」页签通过 `GET .../active-payload` 读取当前未终止下发的快照（懒加载）。

## 6. API

```text
GET  /api/mega-automation/flow-work-orders/meta
POST /api/mega-automation/flow-work-orders/list
POST /api/mega-automation/flow-work-orders/by-source
GET  /api/mega-automation/flow-work-orders/{order_id}
GET  /api/mega-automation/flow-work-orders/{order_id}/active-payload
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
POST /api/mega-automation/flow-work-orders/{order_id}/sync-labillion-status
POST /api/mega-automation/labillion/callback          # 镁伽推送，无需登录，恒 200
```

`sync-labillion-status`：详情页进入时对 `sent/running/paused` 工单异步调用；单工单 10 分钟节流；返回 `execution_progress`（仅 Running 且有值时，供页面展示）。

## 6.1 Labillion 集成（环境变量）

| 变量 | 说明 |
|------|------|
| `LABILLION_BASE_URL` | 镁伽 API 根；留空则不发起任何 Labillion HTTP |
| `LABILLION_USERNAME` / `LABILLION_PASSWORD` | 登录凭据 |
| `PUBLIC_API_BASE_URL` | 本系统对外 API 根，用于 `replyAddress` |

实现：`integrations/labillion.py`（登录、导入、删除、查询）；HTTP 超时 5s。

## 6.2 定时任务

- 功能码：`job.mega_labillion_status_sync`，默认每天 02:00。
- 批量查询非终态工单并应用状态；未配 `LABILLION_BASE_URL` 时 skip 并记日志。
- 开关与时间见系统功能页（改完即写库；cron 重启后端生效）；可 **立即执行** 单次同步。

## 7. 权限

三个权限点（前后端一致）：

| code | 作用 |
|---|---|
| `mega.page.flow_work_order` | 进菜单与页；meta / list / detail / active-payload / sync-labillion-status |
| `mega.flow_work_order.edit` | 保存、校验、删除、作废；表单与铺板解锁编辑 |
| `mega.flow_work_order.dispatch` | 发送及停止/继续/设备已暂停/设备已恢复/确认执行/完成/执行失败 |

路由与功能开关：`menu.mega_automation`、`menu.mega_automation.flow_work_orders`。角色与权限包在系统管理中配置。

## 8. 前端行为

- 新建 / 复制先进入本地未保存页，不写空草稿；复制清空订单编号。
- 已有工单加载失败禁止保存，避免误建新单。
- 详情三个页签：工单编辑、铺板（默认锁定，可解锁改孔与条码）、Payload。
- 列表支持关键字、类型、状态、项目号、靶点、样本板/细胞板条码筛选；返回列表时刷新。
- 列表不展示下发次数与失败摘要。
- 详情加载后对 `sent/running/paused` 异步 sync 镁伽状态；Running 时在状态标签旁显示查询到的进度百分比（无则不显示）。
- `sent + pending` 显示「撤回」；`running` 显示「停止」；`withdrawn` 显示「已撤回」。

## 9. 数据库

空库执行 `docs/vita-database.sql`（含镁伽表、权限点、API 映射与菜单开关种子）。

## 10. 工单内容结构

### 10.1 基础字段

主表基础字段包括：

- `orderNum`：订单编号，必填但允许重复；
- `orderName`：订单名称，可选；
- `orderType`：检测类型，目前元数据包括 `TITER`、`PLAS`、`PCR`；
- `priority`：设备优先级，包括 `high`、`normal`、`low`；
- `remark`：备注；
- `status`：工单状态；
- `created_by`、`created_at`、`updated_at`、`sent_at`：操作与时间信息。

订单编号不加唯一约束。业务上可以存在编号相同的工单，系统使用主键 `id` 区分工单，使用 `dispatchId` 区分下发记录。

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

PC 信息本身以及孔位到 PC 信息的引用都不是强制项：

- 孔类型以 `content_type` 为准；
- 任意孔位都可以不填 `pc_id`；
- 填写了 `pc_id` 时，后端检查该 ID 是否存在，并检查孔位类型与 PC 类型是否匹配：
  `PC` → `SERUM`，`ISO` → `ISO`，`TAG` → `TAG`。

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

`cell_keys` 表示这块样本板选择的细胞列，为对象数组：

```json
{ "barcode": "CELL-20260710-01", "column_no": 3 }
```

前端允许先添加细胞板再填写真实条码。保存时会把“细胞板1”之类的页面占位引用归一成当前细胞板条码。

### 10.4 样本板孔位

每块样本板标准布局为 A01-H12，共 96 孔。孔位字段包括：

```text
well_no
content_type
sample_code
pc_id
```

PC / ISO / TAG 的批次等信息在 `pc_infos` 中维护，通过 `pc_id` 关联；孔位不存 `batch` / `generation`。

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

未填写 `cell_name` 的列视为空列（不可选为检测细胞），保存时 `cell_type` 置为空串；有名称时 `cell_type` 默认为 `正常`（可选 `肿瘤`）。工单至少需要一个已命名的细胞列，每块样本板至少选择一个有效细胞列。

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

暂停后的编辑流程与普通保存不同（**已撤回** `withdrawn` 工单可直接编辑，走 §4.1 继续发送，不适用下列 pausing 流程）：

1. 请求停止（running）后，工单进入 `paused`，下发记录进入 `pausing`；
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

每次发送生成独立 `dispatchId`，格式由后端生成，例如：

```text
DSP260710482913
```

数据库对 `dispatchId` 保持唯一约束。工单编号是否重复与下发编号唯一性无关。

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
工单 paused + withdrawn   ↔ 下发 pending + pause_state=withdrawn（已撤回，可继续重推）
工单 paused            ↔ 下发 pending/running + pause_state（pausing/paused/resuming）
工单 completed         ↔ 下发 completed
工单 execution_failed  ↔ 下发 failed
修改暂停工单后 validated ↔ 原下发 voided
```

## 13. 前端页面

### 13.1 列表

关键字、检测类型、状态、项目号、靶点、样本板条码、细胞板条码；状态统计；详情 / 操作 / 复制。显示态合并 `pause_state`（暂停中 / 已暂停 / 已撤回 / 恢复中）。

### 13.2 详情 · 工单编辑

新建 / 复制本地编辑规则同 §8。支持多样本板拖排序、96 孔划选、PC 维护、细胞列选择；细胞板 12 列编辑与列拖动；加载失败禁止保存。

### 13.3 详情 · 铺板

左右对照：左侧完整样本板 / 细胞板可视化，右侧板总览跳转。默认锁定；可编辑权限下解锁后可改孔内容与板条码（工单编辑页样本板条码仍在表格录入）。

### 13.4 详情 · Payload

展示当前生效下发的 JSON（`active-payload`），可复制。

## 14. 后端代码职责

### `models/mega_automation.py`

工单与下发 ORM 及序列化。

### `modules/mega_automation/content.py`

默认结构、归一化、PC/细胞引用、搜索数组、content 哈希、业务校验。

### `integrations/labillion.py`

Labillion HTTP 客户端：登录、订单导入/删除、状态查询；URL 空则跳过。

### `modules/mega_automation/callback.py`

Labillion 状态归一化、`apply_labillion_status`、回调入口 `handle_labillion_status_push`。

### `modules/mega_automation/labillion_sync.py`

主动单工单 sync（节流）、定时批量 sync；查询结果经同一套 apply 落库。

### `modules/mega_automation/payload.py`

按当前 content 组装下发 Payload，不写库。

### `modules/mega_automation/dispatch.py`

`dispatchId`、当前下发查询、快照创建、暂停/恢复/完成/失败/作废。

### `modules/mega_automation/service.py`

CRUD、状态边界、行锁、版本校验、校验与下发联动。

### `modules/mega_automation/routes.py`

FastAPI 入口、`require_permission`、统一响应；业务规则不放路由层。

## 15. 结果回传

实验结果 JSON 走 `POST /api/order-experiment/sync`（与 Labillion **状态**回调分离）。回传以 `dispatchId` 匹配下发快照；业务解析入库与效价联动见 [titer-upstream-flow.md §8](./titer-upstream-flow.md#8-下游效价数据回传接收已实现业务处理待开发)。回传 JSON 样例见 [order-experiment-sync-api.md](../../temp_text/order-experiment-sync-api.md)。
## 16. 后续待办

1. 检测结果业务解析入库与效价/免疫联动；
2. Payload 字段命名 / 空值 / 版本与设备对齐；
3. 检测板条码产生时机与结果表；
4. 操作审计与长时间无回调兜底（定时 sync 已覆盖状态）；
5. 向 Labillion 主动暂停（协议未提供）。
