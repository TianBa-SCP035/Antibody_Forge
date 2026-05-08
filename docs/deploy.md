# 部署说明

## 环境划分

建议至少区分三类环境：

- `local`：本地开发。
- `test`：Linux 测试环境。
- `prod`：Linux 正式环境。

测试环境和正式环境建议在服务器上使用两套独立运行目录，代码来自同一个 Git 仓库，但配置、数据库、文件目录和端口分开。

```text
/srv/antibody-forge/
  test/
    code/
    config/
    repository/
  prod/
    code/
    config/
    repository/
```

## 后端配置

后端读取项目根目录下的 `config/local/vita_server.env`。可参考：

```text
config/vita_server.env.example
```

真实配置不要提交到 Git。

常用配置项说明：

```text
DATABASE_URL              主业务数据库连接。
CELL_DB_URL               细胞库存外部数据库连接。
REPOSITORY_ROOT           运行时文件仓库根目录，默认 repository。
LEGACY_TITER_UPLOAD_ROOT  老系统效价文件根目录，用于读取历史 /titer_files/... 文件。
DEV_USER_OPENID           本地开发临时登录用户 openid。
DEV_USER_NAME             本地开发临时登录用户名称。
```

## 文件仓库

`repository/` 用于保存运行时文件，不提交到 Git。建议结构：

```text
repository/
  uploads/
    titer_files/
      <experiment_id>/
  exports/
  cache/
  logs/
  tmp/
```

新效价文件保存到 `repository/uploads/titer_files/<experiment_id>/`，数据库只保存 `/titer_files/...` 相对路径。

历史文件有两种处理方式：

- 短期：将 `LEGACY_TITER_UPLOAD_ROOT` 配置为老系统 `upload` 根目录，后端会在新目录找不到文件时回退读取。
- 长期：将老系统 `upload/titer_files/` 迁移到 `repository/uploads/titer_files/`。

当前本地仓库未包含老系统历史效价文件实体，因此 `config/local/vita_server.env` 中 `LEGACY_TITER_UPLOAD_ROOT` 暂时保持为空。

## 本地启动

后端：

```bash
cd bbctg_vita_server
pip install -r requirements.txt
python server.py
```

前端：

```bash
cd bbctg_vita_web
pnpm -F @bbctg/antibody-vita run dev
```

健康检查：

```text
GET /api/health
```

本地联调约定：

- Vben 主框架接口使用 `/api`。
- Serum 业务接口使用 `/serum-api`，由 Vite 代理重写到后端 `/api`。
- 修改 `vite.config.ts` 代理后，需要重启前端 dev server。

## 生产部署建议

生产环境建议：

- 前端由 Nginx 托管 `bbctg_vita_web/apps/antibody_vita/dist`。
- `/api` 反向代理到 `bbctg_vita_server`。
- `/serum-api/` 也需要反向代理到同一个后端，并重写为 `/api/`，以兼容 Serum 页面独立的业务接口前缀。
- 后端使用 `uvicorn` 或 `gunicorn + uvicorn worker` 启动。
- 使用 systemd 管理后端进程。
- 上传文件、导出文件和日志统一放到 `repository/`。

## 迁移差异记录

- 云之家正式自动登录暂未启用，本地开发使用 `DEV_USER_OPENID` 模拟真实用户。
- 自动更新状态接口默认排除 `deleted` 项目；这是新系统更合理的行为，与老定时任务是否完全一致需要生产前确认。
- 删除血清项目暂时保持老系统行为：删除项目主数据和免疫/效价子表，不主动删除 `SerumFile` 和 `SerumFacsPlate`，避免误删历史文件引用。后续如要级联清理，应先做归档/备份策略。

Nginx 代理示例：

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:9091/api/;
}

location /serum-api/ {
    proxy_pass http://127.0.0.1:9091/api/;
}
```
