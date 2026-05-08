# bbctg_vita_server 后端结构

新后端使用 Python API 服务，当前按 FastAPI 组织。结构目标是：顶层简单、业务按部门组织、数据库模型统一管理、配置和运行文件放在项目根目录。

## 顶层结构

```text
bbctg_vita_server/
  server.py
  main.py
  api.py
  core/
  db/
  models/
  modules/
  integrations/
  jobs/
  utils/
```

## 职责说明

- `server.py`：极简启动入口，只负责启动服务。
- `main.py`：创建应用，注册 CORS、异常处理、日志、API 路由和定时任务。
- `api.py`：统一汇总各业务模块的 `routes.py`，不写具体业务逻辑。
- `core/`：配置读取、统一响应、统一异常、请求日志等项目基础能力。
- `db/`：数据库连接、主库 session、外部库 session。
- `models/`：统一数据库表定义。当前迁移了用户、血清实验、效价、FACS 板、细胞库存外部表模型。
- `modules/`：业务模块。当前按免疫部拆分为 `serum`、`titer`、`cell`。
- `integrations/`：外部系统适配。当前包含云之家 ticket 登录客户端。
- `jobs/`：定时任务。当前包含血清实验状态自动更新任务。
- `utils/`：少量纯工具函数，避免变成杂物目录。

## 根目录约定

```text
config/
  vita_server.env.example
  vita_web.env.example
  local/
  test/
  prod/

repository/
  uploads/
  exports/
  temp/
  logs/
```

- `config/` 放运行环境配置和密钥。真实配置不提交。
- `repository/` 放上传文件、导出文件、临时文件和日志。整个目录不提交。

## 当前接口兼容策略

为了先接回现有前端，后端暂时保留旧系统响应格式：

```json
{
  "code": 20000,
  "data": {}
}
```

后续等前后端稳定后，再统一评估是否改成新的响应码规范。
