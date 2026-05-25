# bbctg_vita_server

抗体研发系统后端服务。

## 启动

```bash
pip install -r requirements.txt
python server.py
```

默认自动识别环境并读取项目根目录下的 `config/<env>/vita_server.env`：Windows 为 `local`；Linux 下项目上级目录名为 `prod` 时为 `prod`，否则为 `test`。也可通过 `APP_ENV=local|test|prod` 或 `VITA_SERVER_ENV_FILE` 显式覆盖；不要提交真实账号密码。

推荐后端端口为 `local=8888`、`test=9527`、`prod=8848`。test/prod 经 Nginx 反代时，后端 `HOST` 可设为 `127.0.0.1`。

后台定时任务默认关闭，`APP_ENV=prod` 或 `ENABLE_SCHEDULER=true` 时启动。当前注册 `serum_auto_update_status`（每天 01:00 自动更新血清实验状态）和 `employee_profile_sync`（每天 00:30 同步外部员工基础资料）。

## 运行时目录

- `config/`：环境配置和密钥，例如数据库连接、云之家密钥、开发用户。
- `repository/`：上传文件、导出文件、缓存、日志等运行时数据。

效价文件默认保存到 `repository/uploads/titer_files/`。

## DRM 文件安全模块

`integrations/drm/` 整目录不提交 Git，需在每台机器上手动部署（与 `config/<env>/vita_server.env` 中的 DRM 参数配合使用）。

目录结构：

```text
integrations/drm/
  __init__.py          # SDK Python 封装（必需，不是临时文件）
  lib/
    DrmEdiC.dll        # Windows
    libdrmedi.so       # Linux
    libhttpcomm.so     # Linux，与 libdrmedi.so 同目录
```

业务代码只依赖已提交的 `integrations/drm_service.py`；未部署 `integrations/drm/` 时，上传/下载会静默跳过 DRM 处理。
