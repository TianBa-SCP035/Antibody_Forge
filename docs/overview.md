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
├── bbctg_vita_web/        # 前端 monorepo（业务 app: apps/antibody_vita；其余为 Vben 基础包）
├── config/                # 各环境 vita_server.env（真实文件不入库，模板 *.gitkeep 入库）
├── repository/            # 上传、回传、日志等运行时文件（gitignore）
├── docs/                  # 文档
├── website/               # 对外展示站，GitHub Pages 发布
├── .github/workflows/     # CI：quality.yml 测试与构建；pages.yml 发布 website/
├── start_dev.bat / .sh    # 启停脚本（restart / stop / status；Linux 另有看门狗与 cron 安装），见 deploy.md
├── backup.sh              # Linux：数据库与附件备份，见 deploy.md「备份与恢复」
└── ensure_deps.py         # 启动脚本调用：补齐缺失的 Python / 前端依赖
```

## 模块路由（已落地）

产品模块是否「规划中」见 [README.md](./README.md)。下表只列**已有真实路径**。

| 模块 | 前端 | 后端 | 说明 |
|------|------|------|------|
| 认证 | `/auth/login`、`/auth/yunzhijia` | `/api/auth`、`/api/user/info` | 密码 / 云之家 ticket |
| 千鼠万抗 · 靶点库 | `/atlas/targets` | `/api/atlas/targets/list` | 本地靶点主数据分页搜索与详情浏览 |
| 小鼠免疫 | `/serum/workbench`、`/serum/list`、`/serum/detail`、`/serum/edit` 等 | `/api/serum`、`/api/serum/workbench` | 项目工作台（开做前准备）、实验列表、笼位、方案导出 |
| 抗体发现 · 项目工作台 | `/discovery/workbench` | `/api/discovery/workbench` | 剖鼠取细胞与筛选安排；工作台 / Excel |
| 抗体发现 · 合成与验证 | `/discovery/synthesis-progress` | `/api/discovery/synthesis-progress` | 合成订单、到货及流式/亲和力初筛验证跟踪；One 库同步与比对 |
| 分子与细胞 · 引物库 | `/molecular-cell/primer-library` | `/api/molecular-cell/library-orders/catalog` | 引物的查看、编辑、导入导出 |
| 分子与细胞 · 文库构建 | `/molecular-cell/library-construction`、`/molecular-cell/library-construction/result` | `/api/molecular-cell/library-orders` | 建库工单、胶图与质检文件；发现交接 |
| 效价数据 | `/serum/titer` | `/api/serum/titer` | 靶点、FACS、ELISA、附件（可选 DRM） |
| 效价实验列表 | `/serum/titer-orders` | `/api/serum/titer/order/*` | 效价工单；「工单」→ 镁伽流式；「测序」→ 发现工作台 |
| 镁伽流式工单 | `/mega-automation/flow-work-orders`（含 `/detail`） | `/api/mega-automation` | 铺板、校验、下发；Labillion 集成见 flow-work-order 文档 |
| 工单数据回传 | 无前端 | `/api/order-experiment` | 设备 JSON → 落盘并记 `order_sync` |
| 细胞库存 | `/serum/cell` | `/api/serum/cell_inventory` | 外部库只读 |
| 系统管理 | `/system/user-permission`、`/system/features` | `/api/system` | 用户、角色、权限、日志、功能开关 |
| 首页 / 个人中心 | `/home`、`/profile` | （复用认证接口） | 非业务主链路 |

前端业务请求统一走 `/api`（开发时由 Vite 代理到后端）。

## 设计要点

- **菜单**：由前端路由 `meta` 维护，不落库；`sys_feature_flag` 控制功能/任务开关（见 [auth-permissions.md](./auth-permissions.md)）。
- **鉴权模型**：RBAC + 权限包 + 个人覆盖；组织字段不参与鉴权；`sys_permission_api` 仅作审计归类，不自动拦接口（详见权限文档）。

## 定时任务

共 6 个，实现位于 `bbctg_vita_server/jobs/`；任务清单、默认时间与启用条件见 [deploy.md](./deploy.md)「定时任务」。
