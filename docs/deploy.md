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

后端会按以下优先级选择配置文件：

1. 设置了 `VITA_SERVER_ENV_FILE` 时，读取该路径指向的 `vita_server.env`。
2. 未设置 `VITA_SERVER_ENV_FILE` 时，如设置了 `APP_ENV=local|test|prod`，读取项目根目录下的 `config/<APP_ENV>/vita_server.env`。
3. 未设置 `APP_ENV` 时自动识别环境：Windows 启动为 `local`；Linux 下项目目录 `Antibody_Forge` 的上级目录名为 `prod` 时为 `prod`，否则为 `test`。

配置模板可参考：

```text
config/vita_server.env.example
```

真实配置不要提交到 Git。`config/local/`、`config/test/`、`config/prod/` 均由本机或服务器单独维护。

常用配置项说明：

```text
APP_ENV                   可选。当前环境：local、test 或 prod；不填时自动识别。
VITA_SERVER_ENV_FILE      可选。显式指定后端配置文件路径，适合 systemd。
DATABASE_URL              主业务数据库连接。
CELL_DB_URL               细胞库存外部数据库连接。
EMPLOYEE_DB_URL           外部员工信息只读库连接，按需配置。
SECRET_KEY                JWT 签名密钥，生产必须替换。
REPOSITORY_ROOT           运行时文件仓库根目录，默认 repository。
ENABLE_SCHEDULER          是否启用后台定时任务；prod 环境也会自动启用。
YUNZHIJIA_AUTO_PROVISION  云之家未绑定用户是否自动创建本系统账号，默认 false。
DEV_USER_OPENID           本地开发临时登录用户 openid。
DEV_USER_NAME             本地开发临时登录用户名称。
```

环境建议：

- `local`：本地或测试库，`PORT=8888`，`DEBUG=true`，`ENABLE_SCHEDULER=false`，可保留 `DEV_USER_*`。
- `test`：单独测试库或临时共用正式库，`PORT=9527`，`DEBUG=false`，`ENABLE_SCHEDULER=false`，禁用 `DEV_USER_*`。
- `prod`：正式库，`PORT=8848`，`DEBUG=false`，强随机 `SECRET_KEY`，禁用 `DEV_USER_*`，后台任务默认启用。

如果 test/prod 在同一台服务器同时运行，后端端口需要不同。公网 IP、域名、HTTPS 和访问入口由 DNS、服务器网络、防火墙和 Nginx 控制；应用配置里的 `HOST`/`PORT` 只决定后端进程监听在哪个地址和端口。若 Nginx 和后端在同一台服务器，生产部署可优先让后端只监听 `127.0.0.1`，避免绕过 Nginx 直接访问。

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

部署时需要确保后端运行用户对 `repository/` 有读写权限：

```bash
sudo mkdir -p /srv/antibody-forge/prod/repository/{uploads,exports,cache,logs,tmp}
sudo chown -R antibody:antibody /srv/antibody-forge/prod/repository
```

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

本地前端开发端口为 `5555`，后端 local 端口为 `8888`。Vite 开发代理默认转发到 `8888`，也可以用 `VITA_DEV_BACKEND=http://127.0.0.1:<port>` 临时覆盖。

健康检查：

```text
GET /api/health
```

本地联调约定：

- Vben 主框架接口使用 `/api`。
- Serum 业务接口使用 `/serum-api`，由 Vite 代理重写到后端 `/api`。
- 修改 `vite.config.ts` 代理后，需要重启前端 dev server。

## 后台定时任务

当前系统只注册一个后台任务：

- `serum_auto_update_status`：每天 01:00 执行 `auto_update_status(db, {})`，自动更新血清实验状态。

启动策略：

- `APP_ENV=local` 和 `APP_ENV=test` 默认不启动定时任务，可在页面手动执行“自动更新状态”验证。
- `APP_ENV=prod` 会启动定时任务。
- 任意环境设置 `ENABLE_SCHEDULER=true` 也会启动定时任务。
- 任务运行结果写入 `repository/logs/app.log`。

后续如果增加员工资料同步任务，建议使用独立任务名 `employee_profile_sync`，例如每天 02:00 执行，并继续只在 prod 或显式开启时运行。

## 云之家登录

新系统同时保留账号密码登录和云之家 ticket 登录：

- `sys_user.id` 是本系统内部主键。
- `sys_user.openid` 是云之家免密登录绑定主键。
- `sys_user.job_no` 用于和公司员工信息库匹配。
- `sys_user.username` 建议使用工号或公司统一账号，不建议使用姓名。
- `sys_user.display_name` 用于展示姓名。

`YUNZHIJIA_AUTO_PROVISION=false` 时，未绑定 `openid` 的云之家用户会被拒绝登录，保持部署前最稳妥的策略。

`YUNZHIJIA_AUTO_PROVISION=true` 时，云之家返回 `openid` 但系统无账号，会自动创建 active 用户，写入 `openid`、`job_no`、`display_name`、`email` 和 `mobile` 等基础字段。自动创建的用户默认不授予角色或权限包，需要管理员在系统管理中开通业务权限。

## 外部员工信息库

员工信息库使用独立只读配置 `EMPLOYEE_DB_URL`，不复用 `CELL_DB_URL`，也不提交真实连接串。

第一阶段建议只做只读查询和字段映射确认，重点确认外部 `sys_user` 是否包含姓名、工号、手机号、部门、岗位、在职状态和 openid。同步策略建议：

- 只同步基础资料，不同步权限、不同步密码。
- 匹配优先级为 `openid`、`job_no`、公司账号字段。
- 可更新本系统 `display_name`、`department`、`group_name`、`position_title`、`employment_status`、`email`、`mobile`。
- 新员工可创建为无角色用户，供管理员快速授权。

后续实现时建议先在系统管理页提供手动“同步员工信息”，稳定后再增加 `employee_profile_sync` 定时任务。

## 生产部署建议

生产环境建议：

- 前端由 Nginx 托管 `bbctg_vita_web/apps/antibody_vita/dist`。
- `/api` 反向代理到 `bbctg_vita_server`。
- `/serum-api/` 也需要反向代理到同一个后端，并重写为 `/api/`，以兼容 Serum 页面独立的业务接口前缀。
- 后端使用 `uvicorn` 或 `gunicorn + uvicorn worker` 启动。
- 使用 systemd 管理后端进程。
- 上传文件、导出文件和日志统一放到 `repository/`。

推荐首次部署流程：

1. 本地确认代码、配置模板和数据库变更。
2. 提交代码到 GitHub 或公司 Git 仓库。
3. 服务器使用 `git clone` 或 `git pull` 到固定目录，例如 `/srv/antibody-forge/prod/code`。
4. 服务器单独维护 `config/prod/vita_server.env`，不进入仓库。
5. 前端执行 `pnpm -F @bbctg/antibody-vita run build`。
6. Nginx 托管 `bbctg_vita_web/apps/antibody_vita/dist`。
7. Nginx 反代 `/api` 和 `/serum-api` 到同一个后端。
8. systemd 管理后端 `python server.py`。

如果服务器不能访问 Git，可以本地打包代码和前端 dist 后用 `scp` 或 `rsync` 上传。不建议长期手动拖文件，容易漏改、覆盖配置且难以回滚。Docker 可作为后续二期方案，不作为首次部署最短路径。

systemd 示例：

```ini
[Unit]
Description=Antibody Forge API
After=network.target

[Service]
User=antibody
Group=antibody
WorkingDirectory=/srv/antibody-forge/prod/code/bbctg_vita_server
Environment=VITA_SERVER_ENV_FILE=/srv/antibody-forge/prod/code/config/prod/vita_server.env
ExecStart=/srv/antibody-forge/prod/venv/bin/python server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## 迁移差异记录

- 云之家 ticket 登录已支持，未绑定用户默认拒绝；如开启 `YUNZHIJIA_AUTO_PROVISION=true`，会自动创建无业务权限用户。
- 自动更新状态接口默认排除 `deleted` 项目；这是新系统更合理的行为，与老定时任务是否完全一致需要生产前确认。
- 删除血清项目会清理项目相关数据库记录，但不会删除 `repository/uploads/titer_files/` 下的磁盘文件。

Nginx 代理示例：

仓库内也提供了当前服务器可直接参考的站点配置：

```text
bbctg_vita_web/scripts/deploy/nginx-antibody-forge-sites-active.conf
```

```nginx
client_max_body_size 200m;
proxy_read_timeout 300s;
proxy_send_timeout 300s;

location / {
    root /srv/antibody-forge/prod/code/bbctg_vita_web/apps/antibody_vita/dist;
    try_files $uri $uri/ /index.html;
}

location /api/ {
    proxy_pass http://127.0.0.1:8848/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Authorization $http_authorization;
}

location /serum-api/ {
    proxy_pass http://127.0.0.1:8848/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Authorization $http_authorization;
}
```

## 部署前验收清单

- `git status` 中没有 `config/local`、`config/prod`、RDS 密码、云之家 secret、上传文件和老系统代码。
- `APP_ENV` 和 `VITA_SERVER_ENV_FILE` 配置路径选择生效。
- local/test 不启动 scheduler，prod 或 `ENABLE_SCHEDULER=true` 启动 scheduler。
- 云之家 ticket 登录在测试环境可用，未绑定用户行为符合 `YUNZHIJIA_AUTO_PROVISION`。
- 账号密码登录仍可作为管理员兜底。
- 血清列表、方案编辑、效价文件/FACS、小鼠导出和系统管理链路手工通过。
- Nginx 上传大小、超时和 `Authorization` 透传配置完成。
- `repository/` 目录权限正确，可写上传文件和日志。
