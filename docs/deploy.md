# 部署与运维

> 索引 [README.md](./README.md) · 权限 [auth-permissions.md](./auth-permissions.md)

## 环境

| 环境 | 识别 | 端口 | Scheduler |
|------|------|------|-----------|
| local | Windows 默认 | 8888 | 关 |
| test | Linux，上级目录非 `prod` | 9527 | 关 |
| prod | Linux，上级目录为 `prod` | 8848 | 开 |

建议服务器目录：`/srv/antibody-forge/{test|prod}/code` + 独立 `config/`、`repository/`。

## 配置文件

优先级：`VITA_SERVER_ENV_FILE` > `APP_ENV` → `config/<env>/vita_server.env` > 自动识别。

模板：`config/vita_server.env.example`。`config/local|test|prod/` 不提交 Git。

在 **DATABASE_URL** 空库执行 [vita-database.sql](./vita-database.sql) 即可（全表 + 种子；见脚本头说明）。

| 变量 | 说明 |
|------|------|
| `DATABASE_URL` / `SECRET_KEY` | test/prod 必填真实值 |
| `REPOSITORY_ROOT` | 默认 `repository` |
| `ENABLE_SCHEDULER` | prod 默认可不开 env，代码会按 `APP_ENV=prod` 启用 |
| `YUNZHIJIA_*` / `YUNZHIJIA_AUTO_PROVISION` | 云之家登录；未绑定用户默认拒绝 |
| `CELL_DB_URL` / `EMPLOYEE_DB_URL` | 外部只读库；员工库供 `employee_profile_sync` |
| `DRM_*` | DRM SDK 连接；另需系统功能开关 `feature.drm_file_security` |
| `DEV_USER_*` | 仅 local 开发绕过登录 |

## 本地启动

```bash
# 后端
cd bbctg_vita_server && pip install -r requirements.txt && python server.py

# 前端
cd bbctg_vita_web && pnpm -F @bbctg/antibody-vita run dev
```

前端 `5555`，后端 local `8888`。健康检查：`GET /api/health`。

Linux 服务器可用根目录 `start_dev.sh`（构建前端 + nohup 后端）；**须在 exec python 前**设置 DRM 库路径（脚本已含 `LD_LIBRARY_PATH`）。

## 文件仓库

效价附件：`repository/uploads/titer_files/<experiment_id>/`，库内路径 `/titer_files/...`。运行用户需对 `repository/` 可写。

PDF 转换临时目录：`repository/tmp/scheme_export/`（请求结束自动清理；与 `tmp/drm_download` 同级）。

## 免疫方案 PDF 打印（Linux test/prod）

详情页「导出方案」：**左键** xlsx，**右键** xlsx→pdf 后浏览器打印。依赖 **LibreOffice headless**（非 pip 包）。

```bash
sudo apt update
sudo apt install -y libreoffice
# 可选：sudo apt install -y fonts-wqy-microhei
```

代码固定路径（`scheme_export.py`）：Linux `/usr/lib/libreoffice/program/soffice`；Windows 开发 `C:\Program Files\LibreOffice\program\soffice.exe`。未安装或路径不符 → 打印接口 503，xlsx 导出不受影响。

验收：详情页右键能弹出打印预览；`repository/tmp/scheme_export/` 无残留堆积。

## DRM（Linux 生产）

1. 手动部署 `bbctg_vita_server/integrations/drm/`（`__init__.py` + `lib/` 下 SO/DLL），不提交 Git。
2. `config/<env>/vita_server.env` 配置 `DRM_SERVER_*` 等；系统管理开启「DRM 文件安全模块」。
3. **启动 Python 前** `export LD_LIBRARY_PATH=.../integrations/drm/lib`（`start_dev.sh` / systemd 已配则不必重复）。备选：`patchelf --set-rpath '$ORIGIN' libdrmedi.so`。
4. 行为：上传 DRM 密文自动解密；Office 附件下载（非 preview）加密；失败只记日志，不阻断上传下载。

## 定时任务

| ID | 默认时间 | 作用 |
|----|----------|------|
| `employee_profile_sync` | 00:30 | 外部员工库 → 用户资料（不同步角色/密码） |
| `serum_auto_update_status` | 01:00 | 自动更新血清实验状态 |

日志：`repository/logs/app.log`。调度时间可读 `sys_feature_flag` 中 `job.*`。

## 生产部署

1. `git pull` 到固定目录，维护 `config/prod/vita_server.env`。
2. `pnpm -F @bbctg/antibody-vita run build`，Nginx 托管 `dist`。
3. 反代 `/api/` → 后端（保留 HTTP 状态与 `Authorization` 透传）。
4. systemd 管理 `python server.py`；`WorkingDirectory` 为 `bbctg_vita_server`。

```ini
[Service]
WorkingDirectory=/srv/antibody-forge/prod/code/bbctg_vita_server
Environment=VITA_SERVER_ENV_FILE=/srv/antibody-forge/prod/code/config/prod/vita_server.env
Environment=LD_LIBRARY_PATH=/srv/antibody-forge/prod/code/bbctg_vita_server/integrations/drm/lib
ExecStart=/srv/antibody-forge/prod/venv/bin/python server.py
```

Nginx 参考：`bbctg_vita_web/scripts/deploy/nginx-antibody-forge-sites-active.conf`（注意 `client_max_body_size`、超时、`Authorization` 透传）。

## 验收清单

- 无密钥、上传文件、`config/local|prod` 误提交
- prod scheduler、云之家/密码登录、血清与系统管理主链路可用
- Nginx 上传大小与 `/api` 反代正确
- Linux DRM：上传密文可解密（日志无 `libhttpcomm.so` 错误）
- 免疫方案：左键导出 xlsx；Linux 已装 LibreOffice 时右键可打印 pdf
