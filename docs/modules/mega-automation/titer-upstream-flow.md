# 效价实验 → 镁伽流式工单
> 说明效价实验如何发起并预填流式工单。相关：[流式工单](./flow-work-order.md)

## 1. 入口与权限

入口位于效价实验列表每行的“工单”按钮。

| 项目 | 值 |
|---|---|
| 效价列表路由 | `/serum/titer-orders` |
| 一级菜单开关 | `menu.serum` |
| 列表菜单开关 | `menu.serum.titer_order` |
| 效价列表权限 | `serum.page.titer_order` |
| 流式页面权限 | `mega.page.flow_work_order` |
| 流式保存权限 | `mega.flow_work_order.edit` |
| 流式发送权限 | `mega.flow_work_order.dispatch` |

新建入口使用效价记录编辑判断：用户须有 `serum.titer_order.record.edit`，并且满足以下一项：

- 有 `serum.titer_order.record.edit_all`；
- 是当前效价负责人；
- 是当前免疫负责人。

没有记录编辑权时，已有流式工单以只读模式打开；没有关联工单时只提示暂无记录。右键仍可查看关联工单列表，但不显示“新建上机工单”。

小鼠分组查询和鼠号保存另行校验权限。`serum.project.edit`、`serum.project.edit_all`、`serum.titer.edit`、`serum.titer.edit_all` 任一权限即可。

## 2. 数据与编号

### 2.1 来源数据

效价列表项提供 `experiment_id`、`titer_order_id`、`project_code`、`target_name` 和 `target_codes`。向导通过 `experiment_id` 读取小鼠分组。

`titer_order_id` 由后端生成：

```text
{YYYYMMDDHHmmss}-{project_code 去空格}-{0000~9999}
```

`project_code` 为空时使用 `experiment_id`，两者都为空时使用 `NO_PROJECT`。生成时检查数据库唯一性。

### 2.2 向导草稿

用户确认后，页面把草稿写入 `sessionStorage` 的 `titer-instrument-wizard-draft`，再跳转：

```text
/mega-automation/flow-work-orders/detail?mode=edit&prefill=titer-wizard&n={timestamp}
```

详情页读取后立即删除该草稿。参与流式预填的字段为：

```json
{
  "experiment_id": "EXP...",
  "titer_order_id": "20260716140322-ABC123-0847",
  "project_code": "ABC123",
  "target_name": "CD33",
  "target_codes": ["CD33"],
  "groups": [
    {
      "group_id": "G1",
      "selected_mouse_nos": ["M001", "M002"]
    }
  ]
}
```

`groups` 按小鼠分组列表顺序生成，只包含有选中小鼠的组。每组鼠号保持组内顺序；选择键使用“组 ID + 组内索引”，相同鼠号可以分别入选。

### 2.3 字段映射与默认值

| 来源 | 流式工单字段 | 规则 |
|---|---|---|
| `experiment_id` | `sample_plates[].project_no` | 每块样本板相同 |
| `target_name` | `sample_plates[].target` | 每块样本板相同 |
| `target_codes` | `sample_plates[].target_codes` | 去空值后写入每块样本板 |
| 选中鼠号 | `sample_plates[].wells[].sample_code` | 按组序、组内序连续装板 |
| `titer_order_id` | `source_id` | 指向来源效价工单 |
| 固定值 | `orderType` | `TITER` |
| `titer_order_id` + 4 位大写 base36 随机后缀 | `orderNum` | 订单编号允许重复 |
| `project_code`、`target_name` | `orderName` | `{project_code}-{target_name}-效价检测`；项目编号为空时使用 `experiment_id` |
| 固定值 | `priority` | `normal` |
| 固定值 | `sample_plates[].secondary_antibody` | `鼠` |

订单名称会忽略空片段；所有片段都为空时使用“效价检测”。

## 3. 页面操作

### 3.1 “工单”按钮

| 操作 | 行为 |
|---|---|
| 左键 | 查询 `orderType=TITER`、`source_id=titer_order_id` 且非 `cancelled` 的工单；按 `id` 倒序打开第一条 |
| 左键且无关联工单 | 有记录编辑权时打开新建向导；否则提示暂无关联工单 |
| 右键 | 打开该效价工单关联的全部流式工单列表，包括已作废工单 |
| 右键列表点行 | 按当前用户是否有记录编辑权，以编辑或只读模式打开详情 |
| 右键列表“新建上机工单” | 关闭列表并打开新建向导 |

### 3.2 新建向导

向导分两部分：

1. 小鼠分组表只读展示组别、品系、性别、数量和鼠号。点击鼠号打开登记弹窗；确认后立即保存鼠号和死活，并同步选择矩阵。
2. 每组使用独立的 10 列矩阵选择待测小鼠。存活小鼠默认全选，死亡小鼠显示但不可选；支持单击和拖拽划选。

未选择小鼠时，“确定”会先要求确认，确认后仍可创建仅含对照孔的样本板。

### 3.3 样本板布局

- 每板 20 个样本孔，顺序为 A02-A11、E02-E11。
- 第 1 列全部为 `NC`，第 12 列全部为 `PC`。
- 其余未放入鼠号的孔为 `BLANK`。
- 鼠号按组序和组内顺序连续填充；装满一板后新建下一板，不按组拆板。
- 0 只小鼠仍创建一块样本板。
- 样本板条码、PC 信息、细胞板内容和 `cell_keys` 不预填。

## 4. 跨模块联动

一条效价工单可以创建多条流式工单。关联保存在流式工单一侧：

```text
mega_flow_work_order.orderType = TITER
mega_flow_work_order.source_id = serum_titer_order.titer_order_id
```

保存已有流式工单时，非空 `source_id` 不能改成其他来源。复制流式工单会清空 `source_id`，避免复制件继续关联原效价工单。

向导勾选只用于生成本地流式草稿，不写入效价业务表。鼠号和死活在鼠号弹窗确认时直接保存到小鼠数据。流式工单的保存、校验、发送、状态和 Labillion 行为见 [流式工单](./flow-work-order.md)。

## 5. 接口

| 方法 | 路径 | 权限 | 用途 |
|---|---|---|---|
| GET | `/api/serum/mouse-groups` | 四种小鼠登记权限任一 | 按 `experiment_id` 读取小鼠分组 |
| POST | `/api/serum/mouse-registry/save` | 四种小鼠登记权限任一 | 保存鼠号和死活 |
| POST | `/api/mega-automation/flow-work-orders/by-source` | `mega.page.flow_work_order` | 查询来源效价工单关联的流式工单 |
| POST | `/api/mega-automation/flow-work-orders/save` | `mega.flow_work_order.edit` | 保存预填后的流式工单及来源关联 |

“四种小鼠登记权限”指 `serum.project.edit`、`serum.project.edit_all`、`serum.titer.edit`、`serum.titer.edit_all`。
