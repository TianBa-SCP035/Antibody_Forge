# 后端结构

> 仓库地图见 [overview.md](./overview.md) · 权限见 [auth-permissions.md](./auth-permissions.md) · 部署见 [deploy.md](./deploy.md)

本文约定 **`bbctg_vita_server/`** 的目录、API 前缀与响应/错误约定；不写产品路线图。

## 目录

```text
bbctg_vita_server/
  server.py            # 启动入口
  main.py              # CORS、日志、审计中间件、挂载路由、定时任务
  api.py               # 按模块登记表挂载 router，提供 api_routes()（含 /health、/user/info）
  core/                # 配置、统一响应、异常、请求日志
  db/                  # 主库 + 外部只读库 session
  models/              # ORM（types.py：DateString）
  modules/
    registry.py        # ACCESS 权限登记与 MOUNTS 路由挂载表
    auth/              # 登录、JWT、当前用户；external.py 外部回调来源校验
    options/           # 跨模块下拉：靶点库搜索、在职人员搜索
    immunology/        # serum / workbench / titer / cell
    atlas/             # 千鼠万抗
    discovery/         # 抗体发现：workbench / synthesis_progress（合成与验证，含 One 库同步）
    molecular_cell/    # 分子与细胞：library_orders（文库构建）/ primer_catalog（引物库）/ transfection（转染与表达）
    mega_automation/   # 镁伽流式工单（含 callback、labillion_sync）
    order_sync/        # 工单数据回传
    supernatant_receive/  # 合成公司上清板布局接收（service）与向合成公司补查（query）
    system/            # 用户角色权限、审计、功能开关
  integrations/        # 云之家、Labillion、drm_service（SDK 在 drm/，gitignore）
  jobs/                # 定时任务实现与 registry（含手动触发入口）；lock.py 用 MySQL GET_LOCK 防多进程重复执行
  utils/               # 通用工具（Excel 导入导出等）
  tests/               # 按领域分目录：core / system / discovery / immunology / molecular / mega
  pytest.ini           # 测试路径与导入方式
```

## 测试

### 后端

测试位于 `bbctg_vita_server/tests/`，按领域分一级子目录，文件在子目录内按 `test_<功能>.py` 命名：

| 目录 | 覆盖范围 |
|------|------|
| `core/` | `core/`、`utils/` 与模块登记表 |
| `system/` | `modules/system`、`modules/auth`、`modules/options`，以及员工、靶点同步任务 |
| `discovery/` | `modules/discovery` |
| `immunology/` | `modules/immunology` |
| `molecular/` | `modules/molecular_cell` |
| `mega/` | `modules/mega_automation` 与 Labillion 对接 |

新增业务模块时在对应领域目录下加文件；新增领域时新建同名子目录。子目录不放 `__init__.py`：`pytest.ini` 使用 `--import-mode=importlib`，不同目录可以有同名文件（如 `discovery/test_workbench.py` 与 `immunology/test_workbench.py`），并把 `tests/` 加入导入路径，测试统一 `from support import ...`。测试类使用 `unittest` 风格，由 pytest 统一运行。

`tests/support.py` 提供：

- `DbTestCase`：每个测试建立独立的内存 SQLite；子类在 `tables` 中列出需要建表的 ORM 模型；测试库注册业务查询使用的 MySQL JSON 函数。
- `FakeSourceDb`：模拟员工库、靶点源库等外部只读数据库。

在 `bbctg_vita_server/` 下执行：

```powershell
$env:DATABASE_URL='sqlite://'; python -m pytest -q
```

`tests/system/test_audit_routes.py` 检查每个写路由都有审计声明，并检查 `api_routes()` 列出的路径与实际服务路径一致。

测试名称使用 `test_<条件>_<行为>`，每个测试只验证一个行为。测试以公开的 service 或 route 入口为边界；一次性核对和只针对单次修复的临时用例不进入测试集，稳定业务规则需要回归保护时并入对应领域用例。

### 前端

前端测试与源码放在一起，命名为 `src/**/*.test.mjs`，公共加载器位于 `src/test-support/`。在 `bbctg_vita_web/apps/antibody_vita/` 下执行：

```powershell
pnpm run test
pnpm run typecheck
pnpm run lint:components
```

`pnpm run test` 使用 Node test runner；`typecheck` 执行 Vue/TypeScript 类型检查，`lint:components` 使用 ESLint 检查 Vue 组件。

## 公共工具（新代码先找这里，不要在模块里再写一份）

| 位置 | 用途 |
|------|------|
| `utils/normalize.py` | 文本、日期、非负整数、靶点编号、板号（`normalize_plate_nos`，一行一个）、多值拼接、状态、优先级的清洗 |
| `utils/workbench_queue.py` | 优先级常量（`PRIORITY_ORDER` 队列顺序从高到低；`PRIORITY_OPTIONS` 下拉顺序从低到高）、队列锁与重编号；`QueueSpec` 描述一个队列，入队、出队、改号、拖行共用 |
| `utils/pagination.py` | `parse_page_limit`、`paginate_select`：列表分页（上限 500），返回 `{ items, total, page, limit }` |
| `utils/model_fields.py` | `model_fields(Model, readonly=...)` 从模型列推出可写字段（中文名取列注释、长度取 `String(n)`）；`clean_field` / `clean_text` / `clean_date` / `clean_int` 按列类型整理写入值，报错文案全系统一致；`fields_request_model(名, FIELDS)` 生成保存接口的请求模型（接口文档列出全部可写字段，值不转换、未登记的键照常保留，取值必须 `model_dump(exclude_unset=True)`） |
| `utils/batch_save.py` | 批量保存：解析请求、按主键顺序锁行、`check_expected(当前行序列化结果, _expected, fields=FIELDS)` 比对（不一致抛 `ConflictError`） |
| `core/errors.py` | 业务异常：`BusinessError`（422）、`ForbiddenError`（403）、`NotFoundError`（404）、`ConflictError`（409），裸 `ValueError` 也按 422；全局处理器统一返回，`db/session.get_db` 出错即回滚。路由不写 try/except |
| `utils/header_filters.py` | 表头筛选；`header_columns(FIELDS, **显式列)` 按列类型自动生成普通文本/日期/整数列，枚举、靶点、多值写在显式列里；多值字段匹配统一用 `csv_token_clause`（已转义 `%` `_`）；统计块去掉本维度的表头条件用 `without_header_fields` |
| `utils/filter_values.py` | `like_literal`、`recorded_target_search`（各模块 `GET /recorded_targets` 共用，关键字与上限都进 SQL）、`code_search_clause`（编号筛选：单个包含匹配，多个按完整编号，单次最多 500 个） |
| `utils/codes.py` | 编号生成；唯一键冲突时重试 |
| `utils/clock.py` | `now_local()`，固定 Asia/Shanghai，不要再用裸 `datetime.now()` |
| `utils/uploads.py` | 上传文件名清洗、落盘路径必须在上传根目录内、`read_limited` 读取限长 |
| `models/types.py` | `DateString`：Python 侧是 `YYYY-MM-DD` 字符串，库里 `VARCHAR` 或 `DATE` 都能读写；写入非法日期直接报错 |

模块分层：`routes.py` 只写权限（含按记录的归属判断）、审计声明、入参解析和 `success(...)` 包装；列表、保存、删除等查询与写入放同目录 `service.py`，单测直接调服务函数。

未知异常不要把 `str(exc)` 返回前端：全局处理器记日志、返回通用提示。业务校验直接抛 `ValueError` / `BusinessError`，按记录判断的无权限抛 `ForbiddenError`，找不到抛 `NotFoundError`，并发或归属冲突抛 `ConflictError`。

DRM：业务只 import `integrations/drm_service.py`；上传密文解密、Office 附件下载加密，失败不阻断传输。Linux 需配置 `LD_LIBRARY_PATH`（见 deploy.md）。

镁伽 Labillion：`integrations/labillion.py`（HTTP 客户端）；`modules/mega_automation/callback.py`（状态回调与 `apply_labillion_status`）；`modules/mega_automation/labillion_sync.py`（主动查询与定时批量同步）。`LABILLION_BASE_URL` 留空时不发起对外 HTTP，本地工单状态仍可用。细节见 [modules/mega-automation/flow-work-order.md](./modules/mega-automation/flow-work-order.md)。

外部主数据：`EMPLOYEE_DB_URL` 只读连接外部平台库；`modules/system/employee_sync.py` 同步员工资料，`modules/system/target_sync.py` 全量同步靶点至本地 `target`。两者使用独立定时任务，共用外部连接。

## 路由注册与 API 前缀

`modules/registry.py` 的 `MOUNTS` 是业务路由挂载表。`api.py` 逐项导入并挂载这些 router，同时用 `api_routes()` 返回带完整 `/api` 前缀的路由清单。`main.py` 再以 `API_PREFIX="/api"` 调用 `include_router`，并在 `FastAPI` 上注册全局 `bind_route_audit` 依赖，使审计层能在路由匹配后读取各接口的声明。应用启动时通过 `api_routes()` 检查写路由覆盖情况，未声明审计分类的写路由会记录警告。

前后端路径对照统一维护在 [overview.md](./overview.md)；各接口细节见对应模块文档。前端业务请求统一走 `/api`。

## 响应格式

业务接口统一如下；健康检查、设备回传、镁伽回调三处例外列在最后：

- 成功：`{ "code": 0, "data": ... }`
- 业务失败：HTTP 422 / 403 / 404 / 409，`{ "code": 1, "message": "...", "data": null }`（`BusinessError` 可带其他 `code` 和 `errorCode`）；前端对带数字 `code` 的 403/404 直接显示后端文案
- 其他 HTTP 异常（401、未登记路由的 404、500）：保留状态码，body 同上；500 只返回通用提示
- 健康检查 `/api/health`：`{ "status": "ok" }`（不走上述 envelope）
- 设备回传 `/api/order-experiment/sync`：`{ "code", "message", "trace_id", "data" }`（multipart 上传 `order_json`）
- 镁伽状态回调：`{ "success": true, "data": ... }`，按 Labillion 约定返回（`modules/mega_automation/routes.py`）

## 前端错误分层（L0–L3）

| 层 | 位置 | 职责 |
|----|------|------|
| L0 | 各页面 | 权限/表单校验，不发请求 |
| L1 | `views/Serum/shared/errors.ts`、`views/System/errors.ts` | 操作级用户文案 |
| L2 | `api/errors.ts` + `api/request.ts` | 403/404/500/断网/超时兜底 |
| L3 | 后端 `message` | 审计与 L1 未配时的 fallback |

定制 UX：请求设 `skipErrorHandler: true`，在 `.catch` 中调用 `notifyApiError`。

## 配置与运行时目录

位于**仓库根**（非 `bbctg_vita_server/` 内），后端启动依赖：

```text
config/<env>/vita_server.env   # 密钥与连接串（不提交）；选择方式见 deploy.md
repository/
  order_sync/                  # 回传 JSON 原文
  uploads/titer_files/         # 效价附件
  cache/ logs/ tmp/            # DRM 缓存、日志、临时文件（含方案 PDF 转换）
```
