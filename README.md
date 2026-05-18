# Antibody Forge

抗体研发 Web 平台（Vita）：免疫部小鼠免疫 / 血清实验管理，以及用户、角色与权限等系统能力。

## 快速开始

**后端**（需已配置 `config/local/vita_server.env`）：

```bash
cd bbctg_vita_server
pip install -r requirements.txt
python server.py
```

**前端**：

```bash
cd bbctg_vita_web
pnpm install
pnpm -F @bbctg/antibody-vita run dev
```

本地默认：前端 `5555`，后端 `8888`，健康检查 `GET /api/health`。

## 文档

完整说明见 **[docs/README.md](./docs/README.md)**：

- [项目总览](./docs/overview.md)
- [认证与权限](./docs/auth-permissions.md)
- [后端结构](./docs/backend-structure.md)
- [部署运维](./docs/deploy.md)

## 仓库说明

| 路径 | 说明 |
|------|------|
| `bbctg_vita_server/` | FastAPI 后端 |
| `bbctg_vita_web/` | 前端 monorepo，业务应用 `apps/antibody_vita` |
| `config/` | 环境配置（勿提交密钥） |
| `repository/` | 运行时上传与日志（勿提交） |
| `docs/` | 项目文档与数据库 DDL |
