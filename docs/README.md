# Antibody Forge 文档

抗体研发业务平台（**Antibody Forge**）的技术文档入口。面向新成员快速了解系统，也供日常维护查阅。

## 阅读顺序

| 文档 | 说明 |
|------|------|
| [项目总览](./overview.md) | 仓库结构、业务模块、技术栈与演进边界 |
| [认证与权限](./auth-permissions.md) | 登录、RBAC、前后端鉴权与数据归属规则 |
| [后端结构](./backend-structure.md) | `bbctg_vita_server` 目录与模块职责 |
| [部署运维](./deploy.md) | 环境、配置、Nginx、定时任务与验收清单 |

## 数据库脚本

| 文件 | 说明 |
|------|------|
| [system-auth-permission-schema.sql](./system-auth-permission-schema.sql) | 用户/角色/权限/功能开关等表 DDL 与种子数据（需**手动**在 MySQL 执行） |

## 子项目入口

| 目录 | 说明 |
|------|------|
| `bbctg_vita_server/` | FastAPI 后端，默认端口 local `8888` / test `9527` / prod `8848` |
| `bbctg_vita_web/apps/antibody_vita/` | Vue 3 + Vben Admin 前端应用 |
| `config/` | 各环境 `vita_server.env`（不提交密钥） |
| `repository/` | 上传、导出、日志等运行时目录（不提交） |
