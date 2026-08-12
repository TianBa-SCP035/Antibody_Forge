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

各环境使用 `config/<local|test|prod>/vita_server.env`。首次使用需将同目录模板 `vita_server.env.gitkeep` 改名为`vita_server.env` 后生效，该文件勿提交。

| 变量 | 含义 |
|------|------|
| `PORT` / `HOST` | 后端监听端口与地址 |
| `DATABASE_URL` | MySQL 连接串 |
| `SECRET_KEY` | JWT 等签名密钥 |
| `CORS_ORIGINS` | 允许的前端来源（逗号分隔） |
| `REPOSITORY_ROOT` | 附件/日志根目录，默认 `repository` |
| `ENABLE_SCHEDULER` | 是否强制开定时任务；prod 环境即使为 false 也会开 |
| `YUNZHIJIA_*` | 云之家（可选） |
| `CELL_DB_URL` / `EMPLOYEE_DB_URL` | 外部只读库（可选）；后者提供员工与靶点主数据 |
| `LABILLION_BASE_URL` / `LABILLION_USERNAME` / `LABILLION_PASSWORD` | 镁伽 Labillion（可选；URL 留空则不推送） |
| `PUBLIC_API_BASE_URL` | 本系统对外 API 根，用于生成下发 Payload 的 `replyAddress` |
| `DRM_*` | DRM（可选；另需功能开关） |

一般不用设：`VITA_SERVER_ENV_FILE`（改用别的 env 路径时）、`APP_ENV`（覆盖自动识别时）。
首个账号无 env 捷径：须在 `sys_user` 建库（超管见 `vita-database.sql` 文末）；之后可在系统管理里增用户。登录方式：账号密码，或云之家 `openid` 绑定。

## 数据库

1. 在 MySQL 中新建空库，并把 `DATABASE_URL` 指到该库。
2. 对空库执行 [vita-database.sql](./vita-database.sql)（建表 + 权限/功能开关等种子；详见脚本头注释）。
3. 首个超级管理员：按 SQL 文末注释生成 `password_hash` 并插入 `sys_user`。

细胞库、外部平台库为只读库，不在此脚本中创建；需要时再配 `CELL_DB_URL` / `EMPLOYEE_DB_URL`。外部平台库提供员工资料及 `xdida_platform_biocytogen.target` 靶点主数据，本系统分别同步到本地主库。

## 启动

仓库根脚本（默认 conda 环境 `Bender`；`start_dev.sh|.bat` 可用 `CONDA_ENV` 覆盖或内变量修改）

| 脚本 | 用途 |
|------|------|
| `start_dev.bat` | **Windows 本地**：清 `8888`/`5555`，开后端 + Vite |
| `start_dev.sh` | **Linux test/prod**：构建前端 + nohup 后端（`LD_LIBRARY_PATH`）；不启 Vite |

### Windows 本地

首次：配好 `config/local/vita_server.env`；`bbctg_vita_server` 内 `pip install -r requirements.txt`；`bbctg_vita_web` 内 `pnpm install`。

日常执行 `start_dev.bat`。前端 `5555`，后端 `8888`。健康检查：`GET /api/health`。

### Linux 服务器

1. 按「环境与端口」放置仓库；维护 `config/test|prod/vita_server.env`（`PORT`：9527 / 8848）。
2. 首次：`bbctg_vita_web` 下 `pnpm install`；在 conda 环境内安装 `bbctg_vita_server/requirements.txt`。
3. 日常：仓库根 `./start_dev.sh`（构建前端 dist、nohup 起后端）。日志：`repository/logs/backend.nohup.log`。
4. 配置 Nginx 代理，对外 test `:9958`、prod `:1314`。

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
| `labillion_status_sync` | 02:00 | 镁伽非终态流式工单状态批量同步；未配 `LABILLION_BASE_URL` 时 skip 并记日志 |

应用日志：`repository/logs/app.log`。`start_dev.sh` 另写 `repository/logs/backend.nohup.log`。调度开关/时间见 `sys_feature_flag` 中 `job.*`（**改完即写库**；cron **重启后端生效**）。系统功能页可对任一 job **立即执行**（不依赖 scheduler 是否启动），见 [auth-permissions.md](./auth-permissions.md)。

## 验收清单

- 无密钥、上传文件、`config/local|test|prod` 误提交
- env 中 `PORT` 与 Nginx `proxy_pass`、对外端口一致
- prod 定时任务已启；云之家/密码登录、血清与系统管理主链路可用
- Nginx 上传大小与 `/api` 反代、`Authorization` 正确
- Linux DRM：上传密文可解密（日志无 `libhttpcomm.so` 等缺库错误）
- 免疫方案：左键 xlsx；已装 LibreOffice 时右键可打印 pdf
