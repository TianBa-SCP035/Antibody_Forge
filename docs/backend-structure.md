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
- `db/`：数据库连接、主库 session、细胞库存和员工信息等外部只读库 session。
- `models/`：统一数据库表定义。当前迁移了用户、血清实验、效价、FACS 板、细胞库存外部表模型。
- `modules/`：业务模块。当前按免疫部拆分为 `serum`、`titer`、`cell`。
- `integrations/`：外部系统适配。当前包含云之家 ticket 登录客户端。
- `jobs/`：定时任务。当前只注册 `serum_auto_update_status`，每天 01:00 自动更新血清实验状态。
- `utils/`：少量纯工具函数，避免变成杂物目录。

## 系统管理扩展边界

- `sys_user` 的部门、组别、职位、性别、个性名片和在职状态字段只用于资料展示、筛选和批量选择用户，不参与权限计算。
- 当前权限链路保持为“用户 -> 角色 -> 权限包 -> 权限点”，个人权限覆盖只作为例外允许或拒绝。
- 站内消息、站内邮件、提醒和小群暂不建表，未来业务场景明确后再新增独立 `notification` 或 `message` 模块。
- 菜单管理暂不落库，菜单顺序、图标、可见性继续由前端路由 `meta` 配置维护；以后需要运营配置时再评估 `sys_menu`。

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

- `config/` 放运行环境配置和密钥。后端可通过 `APP_ENV` 选择 `config/<env>/vita_server.env`，也可通过 `VITA_SERVER_ENV_FILE` 显式指定；真实配置不提交。
- `repository/` 放上传文件、导出文件、临时文件和日志。整个目录不提交。

## 外部员工信息同步边界

- 外部员工信息库使用独立 `EMPLOYEE_DB_URL` 只读连接，不复用 `CELL_DB_URL`。
- 第一阶段只同步基础资料，匹配优先级为 `openid`、`job_no`、公司账号字段。
- 同步内容限制为姓名、部门、组别、岗位、在职状态、邮箱、手机号等资料字段，不同步密码、角色和权限。
- 后续定时同步任务建议命名为 `employee_profile_sync`，与血清状态自动更新任务独立。

## 当前接口兼容策略

为了先接回现有前端，后端暂时保留旧系统响应格式：

```json
{
  "code": 20000,
  "data": {}
}
```

后续等前后端稳定后，再统一评估是否改成新的响应码规范。
