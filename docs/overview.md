# 项目总览

## 定位

**Antibody Forge**（Vita）— 百奥赛图抗体研发 Web 系统。当前核心：**免疫部小鼠免疫 / 血清实验** + **系统管理**（用户、权限、日志、功能开关）。

技术栈：FastAPI + SQLAlchemy + Vue 3 / Vben Admin + MySQL。

## 仓库结构

```text
Antibody_Forge/
├── bbctg_vita_server/     # 后端
├── bbctg_vita_web/        # 前端 monorepo（业务 app: apps/antibody_vita）
├── config/               # 各环境 vita_server.env
├── repository/           # 上传、日志（gitignore）
├── docs/                 # 文档
└── start_dev.sh          # Linux 一键构建+启动后端
```

## 业务模块

| 模块 | 前端 | 后端 | 说明 |
|------|------|------|------|
| 小鼠免疫 | `/serum/*` | `/api/serum` | 项目、状态、笼位、方案导出（xlsx / 右键 pdf 打印） |
| 效价 | `/serum/titer` | `/api/serum/titer` | 靶点、FACS、附件（可选 DRM 加解密） |
| 细胞库存 | `/serum/cell` | `/api/serum/cell_inventory` | 外部库只读 |
| 系统管理 | `/system/*` | `/api/system` | 用户、角色、权限、日志、功能开关 |
| 认证 | 登录 | `/api/auth` | 密码 / 云之家 JWT |

前端 Serum 请求走 `/serum-api`（代理到后端 `/api`）。

## 刻意未做

- 菜单落库（仍用前端路由 `meta`）
- 站内消息 / 邮件模块
- `sys_user` 组织字段参与权限计算
- `sys_permission_api` 自动鉴权（仅审计归类）
- Docker 一键部署（文档以 systemd + Nginx 为主）

## 定时任务

`employee_profile_sync`（00:30）、`serum_auto_update_status`（01:00）。`APP_ENV=prod` 或 `ENABLE_SCHEDULER=true` 时启动。

详见 [deploy.md](./deploy.md)、[backend-structure.md](./backend-structure.md)。
