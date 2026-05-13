# bbctg_vita_server

抗体研发系统后端服务。

## 启动

```bash
pip install -r requirements.txt
python server.py
```

默认自动识别环境并读取项目根目录下的 `config/<env>/vita_server.env`：Windows 为 `local`；Linux 下项目上级目录名为 `prod` 时为 `prod`，否则为 `test`。也可通过 `APP_ENV=local|test|prod` 或 `VITA_SERVER_ENV_FILE` 显式覆盖；不要提交真实账号密码。

推荐后端端口为 `local=8888`、`test=9527`、`prod=8848`。test/prod 经 Nginx 反代时，后端 `HOST` 可设为 `127.0.0.1`。

后台定时任务默认关闭，`APP_ENV=prod` 或 `ENABLE_SCHEDULER=true` 时启动。当前只注册 `serum_auto_update_status`，每天 01:00 自动更新血清实验状态。

## 运行时目录

- `config/`：环境配置和密钥，例如数据库连接、云之家密钥、开发用户。
- `repository/`：上传文件、导出文件、缓存、日志等运行时数据。

效价文件默认保存到 `repository/uploads/titer_files/`。
