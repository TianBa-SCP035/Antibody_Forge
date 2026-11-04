# 部署与运维

> 索引 [README.md](./README.md) · 仓库地图 [overview.md](./overview.md) · 权限 [auth-permissions.md](./auth-permissions.md)

## 环境与端口

Linux 上会根据**仓库根的上一级目录名**自动判定环境（`core/config.py`）：上一级叫 `prod` → 生产，否则 → 测试。Windows 固定为本地。也可用 `APP_ENV` 或 `VITA_SERVER_ENV_FILE` 手动指定。

后端实际监听端口写在 `config/<环境>/vita_server.env` 的 `PORT=`，请与下表一致（代码不会按目录自动改端口；`start_dev.sh` 也会按同一规则释放对应端口）。

| 环境 | 识别 | 端口 | Scheduler |
|------|------|------|-----------|
| local | Windows 默认 | 8888 | 关 |
| test | Linux，上级目录非 `prod` | 9527 | 关 |
| prod | Linux，上级目录为 `prod` | 8848 | 开 |

网站访问：test → `http://<主机>:9958`；prod → `http://<主机>:1314`（Nginx，见启动节）；本地开发 → `http://localhost:5555`。Linux 服务器查本机 IP：`hostname -I`

Linux：生产机请将仓库放在上级目录名为 `prod` 的路径下（如 `…/prod/Antibody_Forge`）；测试机放在非 `prod` 的上级目录即可（习惯用 `test`）。
Windows： 无需路径约定，固定环境为 local。

## 配置文件

各环境使用 `config/<local|test|prod>/vita_server.env`。首次使用把同目录模板 `vita_server.env.gitkeep` **复制**为 `vita_server.env`（模板保留在仓库里），只改复制出的文件，勿提交。

| 变量 | 含义 |
|------|------|
| `PORT` / `HOST` | 后端监听端口与地址 |
| `DATABASE_URL` | MySQL 连接串；prod 仍为默认值时拒绝启动 |
| `SECRET_KEY` | JWT 等签名密钥；prod 必须改掉默认值且不短于 32 位，否则拒绝启动 |
| `CORS_ORIGINS` | 允许的前端来源（逗号分隔）。经 Nginx 同域访问时可留空；不能填 `*` |
| `DEBUG` | 只在本地用；prod 开启会拒绝启动 |
| `REPOSITORY_ROOT` | 附件/日志根目录，默认 `repository` |
| `UPLOAD_MAX_MB` | 效价文件等页面上传的单文件上限，默认 50；文库结果文件另有固定上限（单文件 50MB、单次 500MB）。Nginx `client_max_body_size` 需不小于实际单次请求大小 |
| `ENABLE_SCHEDULER` | 是否强制开定时任务；prod 环境即使为 false 也会开 |
| `LABILLION_CALLBACK_TOKEN` / `LABILLION_CALLBACK_IPS` | 镁伽回调校验（可选）。令牌放请求头 `X-Callback-Token`（不收 URL 参数，免得进访问日志），IP 英文逗号分隔；留空不校验，两项都配则都要满足 |
| `ORDER_SYNC_TOKEN` / `ORDER_SYNC_IPS` / `ORDER_SYNC_MAX_MB` | 工单数据回传 `POST /api/order-experiment/sync` 的同类校验与 JSON 文件上限（默认 20MB） |
| `YUNZHIJIA_*` | 云之家（可选） |
| `CELL_DB_URL` / `EMPLOYEE_DB_URL` / `ONE_DB_URL` | 外部只读库（可选）；分别提供细胞库存、员工与靶点主数据、One 合成订单与交付进度 |
| `LABILLION_BASE_URL` / `LABILLION_USERNAME` / `LABILLION_PASSWORD` / `LABILLION_PLATFORM_ID` | 镁伽 Labillion（可选；URL 留空则不推送。`PLATFORM_ID` 是登录后请求头 `Platform`） |
| `PUBLIC_API_BASE_URL` | 本系统对外 API 根，用于生成下发 Payload 的 `replyAddress` |
| `DRM_*` | DRM（可选；另需功能开关） |

一般不用设：`VITA_SERVER_ENV_FILE`（改用别的 env 路径时）、`APP_ENV`（覆盖自动识别时）、`APP_NAME`（接口文档标题）。
首个账号无 env 捷径：须在 `sys_user` 建库（超管见 `vita-database.sql` 文末）；之后可在系统管理里增用户。登录方式：账号密码，或云之家 `openid` 绑定。

## 数据库

1. 在 MySQL 中新建空库，并把 `DATABASE_URL` 指到该库。
2. 对空库执行 [vita-database.sql](./vita-database.sql)（建表 + 权限/功能开关等种子；详见脚本头注释）。
3. 首个超级管理员：按 SQL 文末注释生成 `password_hash` 并插入 `sys_user`。

细胞库、外部平台库为只读库，不在此脚本中创建；需要时再配 `CELL_DB_URL` / `EMPLOYEE_DB_URL`。外部平台库提供员工资料及 `xdida_platform_biocytogen.target` 靶点主数据，本系统分别同步到本地主库。

## 启动

仓库根两个脚本，默认 conda 环境 `Bender`，可用环境变量 `CONDA_ENV` 覆盖。

| 脚本 | 用途 |
|------|------|
| `start_dev.bat` | **Windows 本地**：后端 `8888` + Vite `5555`，各开一个窗口 |
| `start_dev.sh` | **Linux test/prod**：构建前端 dist + nohup 起后端（带 `LD_LIBRARY_PATH`）；不启 Vite |

| 命令 | 作用 |
|------|------|
| 不带参数 / `restart` / `start` | 补依赖 → 停掉旧进程 → 启动。Linux 先构建前端再停后端，构建期间旧后端照常服务，并顺带补齐 crontab 条目（同 `cron`）；`backend.nohup.log` 超过 50MB 时改名为 `.1` |
| `stop` | 只停止。Windows 关掉两个窗口及其进程；Linux 先正常结束后端，10 秒未退出再强杀，并暂停看门狗 |
| `status` | 查看端口是否在监听；Linux 同时请求 `GET /api/health` |
| `ensure`（仅 Linux） | 看门狗：后端没在监听就只启动后端（不构建、不补依赖），5 分钟内最多拉起一次；`stop` 后不拉起 |
| `cron`（仅 Linux） | 写入当前用户 crontab：每分钟 `ensure`、每天 03:30 `backup.sh`，并列出条目；只改本仓库的条目，已存在则不动 |

补依赖（`ensure_deps.py`）：Python 只检查 `requirements.txt` 里的包是否已安装，不比对版本；`pnpm-lock.yaml` 内容变化时重新 `pnpm install --frozen-lockfile`。

### Windows 本地

首次：配好 `config/local/vita_server.env`（conda 环境、pnpm 需事先装好）。日常执行 `start_dev.bat`，停止用 `start_dev.bat stop`。健康检查：`GET /api/health`。

### Linux 服务器

1. 按「环境与端口」放置仓库；维护 `config/test|prod/vita_server.env`（`PORT`：9527 / 8848）。
2. 首次：本机已有 conda 环境和 `pnpm`。
3. 日常：仓库根 `./start_dev.sh`；停止 `./start_dev.sh stop`；查看 `./start_dev.sh status`。
4. 启动后脚本最多等 30 秒探活；启动失败（如 prod 配置检查不通过）会打印 `repository/logs/backend.nohup.log` 最后 30 行并以非零退出。
5. 托管与备份无需单独操作：`restart` 会写好 crontab，之后后端崩溃或服务器重启 1 分钟内自动拉起，每天自动备份（见「备份与恢复」）。`crontab -l` 可查看；不想要时 `crontab -e` 删掉带 `# antibody-forge:` 的行（下次 `restart` 会重新写入）。
6. 配置 Nginx 代理，对外 test `:9958`、prod `:1314`。

## 备份与恢复

`backup.sh`（仓库根）读取当前环境 env 中的 `DATABASE_URL`，用 `mysqldump` 导出主库，并同步 `repository/uploads`、`repository/order_sync`。由 crontab 每天 03:30 执行，也可随时手动 `./backup.sh`。日志：`repository/logs/backup.log`。

| 项 | 规则 |
|----|------|
| 位置 | `~/backups/antibody_forge/<环境>/`，环境为 `test` 或 `prod`（仓库外，同机两套环境互不干扰；可用 `BACKUP_DIR` 覆盖） |
| 数据库 | `db/daily/<库名>_<YYYYMMDD_HHMM>.sql.gz` 保留 14 天；周日另存 `db/weekly/` 保留 8 周 |
| 附件 | `files/uploads/`、`files/order_sync/` 增量同步，系统里删掉的文件在备份中保留 |
| 依赖 | `mysqldump`（缺少时 `sudo apt install -y default-mysql-client`）、`python3` |

主库在独立数据库服务器上，备份落在应用服务器，可防误删误改。需要防整机损坏时，再把 `~/backups/antibody_forge` 定期拷到 NAS 或另一台机器。

恢复（先恢复到新库核对，确认无误再切换或覆盖）：

```bash
mysql -h <主机> -u <账号> -p -e "CREATE DATABASE bbctg_vita_restore DEFAULT CHARSET utf8mb4"
gunzip < ~/backups/antibody_forge/prod/db/daily/bbctg_vita_<时间>.sql.gz | mysql -h <主机> -u <账号> -p bbctg_vita_restore
rsync -a ~/backups/antibody_forge/prod/files/uploads/ <仓库>/repository/uploads/
```

本地开发若不想连生产库，可用同样方式把最新备份导入本机 MySQL，再把 `config/local/vita_server.env` 的 `DATABASE_URL` 指向本机库。

## Nginx配置

仓库已带样例：`bbctg_vita_web/scripts/deploy/nginx-antibody-forge-sites-active.conf`（含 prod / test 两个 `server`，端口与反代如下）。

| 环境 | `listen`（网站） | `proxy_pass`（后端） | `root` |
|------|------------------|----------------------|--------|
| prod | `1314` | `http://127.0.0.1:8848/api/` | 该环境的 `…/apps/antibody_vita/dist` |
| test | `9958` | `http://127.0.0.1:9527/api/` | 同上，指向**本机该环境**的 dist |

未装 Nginx 时（Debian/Ubuntu）：
```bash
sudo apt update && sudo apt install -y nginx
```

在仓库根执行：
```bash
sudo cp bbctg_vita_web/scripts/deploy/nginx-antibody-forge-sites-active.conf \
  /etc/nginx/sites-available/antibody-forge.conf
```

然后编辑该文件：把两处 `root`（样例里有中文注释）改成本机仓库下的绝对路径 `…/bbctg_vita_web/apps/antibody_vita/dist`；`listen` / `proxy_pass` 一般不用改。
改完后：
```bash
sudo ln -sf /etc/nginx/sites-available/antibody-forge.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

访问：test `http://<主机>:9958`，prod `http://<主机>:1314`。

## 文件仓库

效价附件：`repository/uploads/titer_files/<experiment_id>/`，库内路径 `/titer_files/...`。运行用户需对 `repository/` 可写。

工单数据回传 JSON：`repository/order_sync/<YYYYMMDD>/`，库内路径 `/order_sync/...`；接口 `POST /api/order-experiment/sync`。

临时目录：`repository/tmp/scheme_export/`（方案 PDF）、`repository/tmp/drm_download/`（下载加密临时文件）。

## 免疫方案 PDF 打印（Linux test/prod）

详情页「导出方案」：**左键** xlsx，**右键** xlsx→pdf 后浏览器打印。依赖 **LibreOffice headless**（非 pip）。

```bash
sudo apt update
sudo apt install -y libreoffice
# 可选：sudo apt install -y fonts-wqy-microhei
```

固定路径（`scheme_export.py`）：Linux `/usr/lib/libreoffice/program/soffice`；Windows `C:\Program Files\LibreOffice\program\soffice.exe`。未找到 → 打印接口 **503**，xlsx 导出不受影响。

## DRM（Linux）

1. 手动部署 `bbctg_vita_server/integrations/drm/`（`__init__.py` + `lib/`），不提交 Git。
2. env 配置 `DRM_SERVER_*` 等；系统管理开启「DRM 文件安全模块」。
3. 启动前 `LD_LIBRARY_PATH=…/integrations/drm/lib`（`start_dev.sh` 已配则可省略）。备选：`patchelf --set-rpath '$ORIGIN' libdrmedi.so`。
4. 行为：上传密文可解密；Office 附件下载（非 preview）可加密；失败只记日志，不阻断传输。

## 定时任务

| ID | 默认时间 | 作用 |
|----|----------|------|
| `employee_profile_sync` | 00:30 | 外部员工库 → 用户资料；**不改**已有用户的密码/角色/权限覆盖/超管；新建账号会写入随机初始密码 |
| `target_master_sync` | 00:45 | 外部平台 `target` → 本地主库 `target`；全量 upsert，源记录消失时仅停用 |
| `serum_auto_update_status` | 01:00 | 自动更新免疫实验状态 |
| `discovery_auto_update_status` | 01:15 | 自动推进已过期的抗体发现冲击免状态 |
| `labillion_status_sync` | 02:00 | 镁伽非终态流式工单状态批量同步；未配 `LABILLION_BASE_URL` 时 skip 并记日志 |
| `discovery_synthesis_order_sync` | 每隔 1 小时 | One 合成订单与交付进度同步，并把 One 新订单建成合成与验证工单；未配 `ONE_DB_URL` 时 skip 并记日志 |

每个任务（含「立即执行」）运行前先取 MySQL `GET_LOCK`，取不到就跳过并记日志，所以即使误开了多个后端进程也不会重复执行；但仍建议只让一个进程开调度。

开关与时间存于 `sys_feature_flag` 的 `job.*`，在系统功能页修改后写库并立即重排调度，无需重启；调度未启动的进程只写库。系统功能页可对任一任务**立即执行**（不依赖调度是否启动），功能开关见 [auth-permissions.md](./auth-permissions.md) §7。

应用日志：`repository/logs/app.log`（单文件 10MB，保留 5 份轮转）。`start_dev.sh` 另写 `repository/logs/backend.nohup.log`（不轮转）。

## 生产上线检查

- `config/prod/vita_server.env`：`DATABASE_URL`、`SECRET_KEY`（≥32 位随机串）已填；`DEBUG` 未开；`CORS_ORIGINS` 只含实际前端地址或留空。启动日志若提示配置问题，按提示补齐后再启动。
- 调度：只在一个后端进程开（prod 默认开，test/local 默认关）。
- 外部接口：镁伽回调、工单数据回传按需配置令牌或 IP 白名单；经 Nginx 转发时后端看到的来源 IP 来自 `X-Forwarded-For`（样例配置已带）。
- 索引命名：普通索引 `idx_<表>_<列>`，唯一键 `uk_<表>_<列>`。已有表改索引要手写 `ALTER`（`create_all` 不会给已存在的表加索引），只是改名用 `RENAME INDEX`，不要 `DROP` 后重建。
- 上传：Nginx `client_max_body_size` 不小于 `UPLOAD_MAX_MB`。文库批量上传一次请求后端最多收 500MB、990 个文件，样例 Nginx 与线上均配 500m；调小会让大批次被 Nginx 拒掉（413）。

## 验收清单

- `crontab -l` 有本仓库的 `ensure` 与 `backup.sh` 两条；`~/backups/antibody_forge/<环境>/db/daily/` 有当天备份
- 无密钥、上传文件、`config/local|test|prod` 误提交
- env 中 `PORT` 与 Nginx `proxy_pass`、对外端口一致
- prod 定时任务已启；云之家/密码登录、血清与系统管理主链路可用
- Nginx 上传大小与 `/api` 反代、`Authorization` 正确
- Linux DRM：上传密文可解密（日志无 `libhttpcomm.so` 等缺库错误）
- 免疫方案：左键 xlsx；已装 LibreOffice 时右键可打印 pdf
