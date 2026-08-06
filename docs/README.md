# Antibody Forge 文档

本目录是**对内文档入口**。根目录 [README.md](../README.md) 只做 GitHub 对外介绍，不写业务现状与运维细节。

| 文档 | 内容 |
|------|------|
| **本文** | 业务现状、模块状态、开发计划 |
| [overview.md](./overview.md) | 仓库地图、已落地路由、设计要点、定时任务 |
| [auth-permissions.md](./auth-permissions.md) | 认证、RBAC、功能开关、血清归属 |
| [backend-structure.md](./backend-structure.md) | 后端目录、API 前缀、响应与错误约定 |
| [deploy.md](./deploy.md) | 环境与端口、配置、启动、Nginx、DRM、验收 |
| [vita-database.sql](./vita-database.sql) | 主库 DDL + 权限/功能开关种子（空库执行一次） |
| [temp_text/](./temp_text/) | 设计稿、对接样例（未定稿） |

`overview` / `auth-permissions` / `backend-structure` / `deploy` 只写**当前已实现**的行为；路线图只在本文维护。

代码：`bbctg_vita_server/` 后端 · `bbctg_vita_web/apps/antibody_vita/` 前端 · `config/` 环境配置 · `repository/` 运行时文件。

---

## 业务概览

### 设计原则

- **按实验阶段垂直切片**：每次打通一条完整链路（数据、API、前端、权限），再进入下一阶段。
- **单一数据源**：同一业务事实只存一处；跨模块用 `experiment_id` 等主键关联，避免双写。
- **工单驱动设备环节**：工单 + 下发快照 + 回传核对（镁伽流式工单已落地）。

### 模块与现状

| 模块 | 状态 | 说明 |
|------|------|------|
| 免疫实验列表 | 已上线 | 项目维护、方案导出、笼位与状态 |
| 效价数据 / 效价实验列表 | 已上线 | FACS、ELISA、附件；效价工单 |
| 效价 → 镁伽流式工单 | 已上线 | 「工单」入口：选鼠向导、样本板预填、`source_id` 关联 |
| 镁伽流式工单 | 已上线 | 编辑、校验、铺板、Payload 下发；Labillion 推送/回调/状态查询 |
| 工单数据回传 | 接收已上线 | `POST /api/order-experiment/sync`；业务解析入库待做 |
| 效价 → 千鼠万抗（「测序」按钮） | 规划中 | 免疫后抗体发现路线总览与登记 |
| 单细胞筛选 / 噬菌体展示 | 规划中 | 筛选与发现子路线 |
| 文库构建 / 测序分析 | 规划中 | NGS、Sanger、序列分析 |
| 分子与细胞 / 抗体评价 | 规划中 | 质粒、表达、纯化、评价 |
| 系统管理 / 认证 | 已上线 | RBAC、审计、云之家登录 |

### 流程与数据关联（简）

```text
experiment_id（免疫实验）
  → titer_order_id（效价工单）
  → 流式工单 source_id + orderType=TITER
  → dispatchId（镁伽下发，设备回传匹配）
```

字段与交互细节见 [temp_text/mega-automation-titer-upstream-flow.md](./temp_text/mega-automation-titer-upstream-flow.md)、[temp_text/mega-automation-flow-work-order.md](./temp_text/mega-automation-flow-work-order.md)。

---

## 开发计划

按实验流程推进；不为未开工模块预先建空菜单或占位表。当前已落地路由见 [overview.md](./overview.md)，下表是目标信息架构，条目随实现逐步补齐。

### 推进顺序

1. **千鼠万抗** — 效价列表「测序」入口；路线登记（Beacon / NGS / 噬菌体）；与 `experiment_id` 关联
2. **筛选路线执行** — 在千鼠万抗上择一条主路线（单细胞或噬菌体）做透
3. **文库构建 + 测序分析** — 与所选路线配套
4. **回传业务入库** — `order_sync` 核对快照后写入效价等业务表
5. **分子与细胞 → 抗体评价** — 随上游产出逐步展开

### 目标菜单结构（规划）

```text
首页

小鼠免疫
├─ 免疫实验列表
└─ 效价实验列表

筛选与发现
├─ 千鼠万抗
├─ 单B细胞筛选
└─ 噬菌体展示筛选

文库构建
├─ NGS文库构建
├─ 噬菌体展示文库构建
└─ 文库质检列表

测序分析
├─ Sanger测序列表
├─ NGS测序列表
└─ 序列分析

分子与细胞
├─ 质粒构建
├─ 质粒制备
├─ 细胞制备
├─ 细胞转染
├─ 抗体表达
└─ 抗体纯化

抗体评价
├─ 结合检测
├─ 分子互作
├─ 功能评价
└─ 成药性评价

模组自动化

系统管理
```
