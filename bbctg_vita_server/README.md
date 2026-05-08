# bbctg_vita_server

抗体研发系统后端服务。

## 启动

```bash
pip install -r requirements.txt
python server.py
```

运行配置从项目根目录 `config/local/vita_server.env` 读取；不要提交真实账号密码。

## 运行时目录

- `config/`：环境配置和密钥，例如数据库连接、云之家密钥、开发用户。
- `repository/`：上传文件、导出文件、缓存、日志等运行时数据。

效价文件默认保存到 `repository/uploads/titer_files/`。如需读取老系统历史文件，可在环境配置中设置 `LEGACY_TITER_UPLOAD_ROOT`。
