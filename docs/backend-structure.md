# 后端结构

> 仓库地图见 [overview.md](./overview.md) · 权限见 [auth-permissions.md](./auth-permissions.md) · 部署见 [deploy.md](./deploy.md)

本文约定 **`bbctg_vita_server/`** 的目录、API 前缀与响应/错误约定；不写产品路线图。

## 目录

```text
bbctg_vita_server/
  server.py            # 启动入口
  main.py              # CORS、日志、审计中间件、挂载路由、定时任务
  api.py               # 汇总各模块 router（含 /health、/user/info）
  core/                # 配置、统一响应、异常、请求日志
  db/                  # 主库 + 外部只读库 session
  models/              # ORM（types.py：DateString）
  modules/
    auth/              # 登录、JWT、当前用户；external.py 外部回调来源校验
    options/           # 跨模块下拉：靶点库搜索、在职人员搜索
    immunology/        # serum / workbench / titer / cell
    atlas/             # 千鼠万抗
    discovery/         # 抗体发现：workbench / synthesis_progress（合成与验证，含 One 库同步）
    molecular_cell/    # 分子与细胞：library_orders（文库构建）/ primer_catalog（引物库）
    mega_automation/   # 镁伽流式工单（含 callback、labillion_sync）
    order_sync/        # 工单数据回传
    system/            # 用户角色权限、审计、功能开关
  integrations/        # 云之家、Labillion、drm_service（SDK 在 drm/，gitignore）
  jobs/                # 定时任务实现与 registry（含手动触发入口）；lock.py 用 MySQL GET_LOCK 防多进程重复执行
  utils/               # 通用工具（Excel 导入导出等）
  tests/
```

## 测试

在 `bbctg_vita_server/` 下运行 `python -m pytest`，用内存 SQLite，几秒跑完，不连任何真实库。`tests/` 只放以后改代码时容易被碰坏的东西：业务规则（状态推导、权限、队列）、口径一致（列表 / 统计 / 导出 / 表头取值）、审计，以及同步、文件归档这类分支多的逻辑的回归。写完功能做的一次性核对（格式、重构前后是否等价、SQL 条数等实现细节）跑完即删，不进 `tests/`；修 bug 只在这条规则容易再被改坏时补断言，优先并进已有用例。

## 公共工具（新代码先找这里，不要在模块里再写一份）

| 位置 | 用途 |
|------|------|
| `utils/normalize.py` | 文本、日期、非负整数、靶点编号、多值拼接、状态、优先级的清洗 |
| `utils/workbench_queue.py` | 优先级常量（`PRIORITY_ORDER` 队列顺序从高到低；`PRIORITY_OPTIONS` 下拉顺序从低到高）、队列锁与重编号 |
| `utils/header_filters.py` | 表头筛选；多值字段匹配统一用 `csv_token_clause`（已转义 `%` `_`）；统计块去掉本维度的表头条件用 `without_header_fields` |
| `utils/filter_values.py` | `like_literal`、`recorded_target_search`（各模块 `GET /recorded_targets` 共用，关键字与上限都进 SQL） |
| `utils/codes.py` | 编号生成；唯一键冲突时重试 |
| `utils/clock.py` | `now_local()`，固定 Asia/Shanghai，不要再用裸 `datetime.now()` |
| `utils/uploads.py` | 上传文件名清洗、落盘路径必须在上传根目录内、`read_limited` 读取限长 |
| `models/types.py` | `DateString`：Python 侧是 `YYYY-MM-DD` 字符串，库里 `VARCHAR` 或 `DATE` 都能读写；写入非法日期直接报错 |

未知异常不要把 `str(exc)` 返回前端：记日志，返回通用提示；业务校验用 `ValueError` / `BusinessError` 照常返回消息。

DRM：业务只 import `integrations/drm_service.py`；上传密文解密、Office 附件下载加密，失败不阻断传输。Linux 需配置 `LD_LIBRARY_PATH`（见 deploy.md）。

镁伽 Labillion：`integrations/labillion.py`（HTTP 客户端）；`modules/mega_automation/callback.py`（状态回调与 `apply_labillion_status`）；`modules/mega_automation/labillion_sync.py`（主动查询与定时批量同步）。`LABILLION_BASE_URL` 留空时不发起对外 HTTP，本地工单状态仍可用。细节见 [modules/mega-automation/flow-work-order.md](./modules/mega-automation/flow-work-order.md)。

外部主数据：`EMPLOYEE_DB_URL` 只读连接外部平台库；`modules/system/employee_sync.py` 同步员工资料，`modules/system/target_sync.py` 全量同步靶点至本地 `target`。两者使用独立定时任务，共用外部连接。

## API 前缀

| 前缀 | 后端位置 |
|------|----------|
| `/api/health` | `api.py` |
| `/api/auth` | `modules/auth` |
| `/api/user/info` | `api.py`（Vben 用户信息） |
| `/api/atlas` | `modules/atlas` |
| `/api/options` | `modules/options`（`/targets`、`/users`） |
| `/api/discovery/workbench` | `modules/discovery/workbench` |
| `/api/discovery/synthesis-progress` | `modules/discovery/synthesis_progress` |
| `/api/molecular-cell/library-orders` | `modules/molecular_cell/library_orders` |
| `/api/molecular-cell/library-orders/catalog` | `modules/molecular_cell/primer_catalog`（引物库） |
| `/api/serum` | `modules/immunology/serum` |
| `/api/serum/workbench` | `modules/immunology/workbench` |
| `/api/serum/titer` | `modules/immunology/titer` |
| `/api/serum/cell_inventory` | `modules/immunology/cell` |
| `/api/mega-automation` | `modules/mega_automation` |
| `/api/order-experiment` | `modules/order_sync` |
| `/api/system` | `modules/system` |

前后端路径对照见 [overview.md](./overview.md)。前端开发时业务请求统一走 `/api`。

## 响应格式

业务接口统一如下；健康检查、设备回传、镁伽回调三处例外列在最后：

- 成功：`{ "code": 0, "data": ... }`
- 业务失败（HTTP 200）：`{ "code": 1, "message": "..." }`（`BusinessError` 可带 `errorCode`）
- HTTP 异常（401/403/404/500）：保留状态码，body 同上
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
