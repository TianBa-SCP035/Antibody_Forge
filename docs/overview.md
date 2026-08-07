# 项目总览

> 业务全景与开发计划见 [README.md](./README.md)。  
> 本文是**仓库地图**：顶层目录、当前已落地的模块路由、少量易踩坑的设计要点。  
> 后端目录与接口约定见 [backend-structure.md](./backend-structure.md)。

## 技术栈

FastAPI · SQLAlchemy · Vue 3 / Vben Admin · MySQL

## 仓库结构

```text
Antibody_Forge/
├── bbctg_vita_server/     # 后端（内部见 backend-structure.md）
├── bbctg_vita_web/        # 前端 monorepo（业务 app: apps/antibody_vita）
├── config/                # 各环境 vita_server.env（不入库）
├── repository/            # 上传、回传、日志等运行时文件（gitignore）
├── docs/                  # 文档
└── start_dev.sh           # Linux：构建前端 + 启动后端
```

## 模块路由（已落地）

产品模块是否「规划中」见 [README.md](./README.md)。下表只列**已有真实路径**。

| 模块 | 前端 | 后端 | 说明 |
|------|------|------|------|
| 认证 | `/auth/login`、`/auth/yunzhijia` | `/api/auth`、`/api/user/info` | 密码 / 云之家 ticket |
| 小鼠免疫 | `/serum/list`、`/serum/detail`、`/serum/edit` 等 | `/api/serum` | 项目、笼位、方案导出（xlsx / PDF） |
| 效价数据 | `/serum/titer` | `/api/serum/titer` | 靶点、FACS、ELISA、附件（可选 DRM） |
| 效价实验列表 | `/serum/titer-orders` | `/api/serum/titer/order/*` | 效价工单；「工单」→ 镁伽流式 |
| 镁伽流式工单 | `/mega-automation/flow-work-orders`（含 `/detail`） | `/api/mega-automation` | 铺板、校验、下发；详见 [flow-work-order.md](./modules/mega-automation/flow-work-order.md) |
| 工单数据回传 | 无前端 | `/api/order-experiment` | 设备 JSON → 落盘并记 `order_sync` |
| 细胞库存 | `/serum/cell` | `/api/serum/cell_inventory` | 外部库只读 |
| 系统管理 | `/system/user-permission`、`/system/features` | `/api/system` | 用户、角色、权限、日志、功能开关 |
| 首页 / 个人中心 | `/home`、`/profile` | （复用认证接口） | 非业务主链路 |

前端业务请求统一走 `/api`（开发时由 Vite 代理到后端）。

## 设计要点

- **菜单**：由前端路由 `meta` 维护，不落库；`sys_feature_flag` 控制功能/任务开关（见 [auth-permissions.md](./auth-permissions.md)）。
- **鉴权模型**：RBAC + 权限包 + 个人覆盖；组织字段不参与鉴权；`sys_permission_api` 仅作审计归类，不自动拦接口（详见权限文档）。

## 定时任务

| 任务 | 默认时间 | 说明 |
|------|----------|------|
| `employee_profile_sync` | 00:30 | 同步外部员工资料 |
| `serum_auto_update_status` | 01:00 | 自动更新免疫实验状态 |
| `labillion_status_sync` | 02:00 | 镁伽非终态工单状态批量同步（未配 `LABILLION_BASE_URL` 时 skip） |

启用条件与运维见 [deploy.md](./deploy.md)；系统功能页可改开关/时间（改完即写库）并立即执行。实现位于 `bbctg_vita_server/jobs/`。
