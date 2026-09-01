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
  models/              # ORM
  modules/
    auth/              # 登录、JWT、当前用户
    immunology/        # serum / workbench / titer / cell
    discovery/         # 千鼠万抗
    mega_automation/   # 镁伽流式工单（含 callback、labillion_sync）
    order_sync/        # 工单数据回传
    system/            # 用户角色权限、审计、功能开关
  integrations/        # 云之家、Labillion、drm_service（SDK 在 drm/，gitignore）
  jobs/                # 定时任务实现与 registry（含手动触发入口）
  utils/               # 通用工具（Excel 导入导出等）
  scripts/             # 预留：一次性脚本
  tests/
```

DRM：业务只 import `integrations/drm_service.py`；上传密文解密、Office 附件下载加密，失败不阻断传输。Linux 需配置 `LD_LIBRARY_PATH`（见 deploy.md）。

镁伽 Labillion：`integrations/labillion.py`（HTTP 客户端）；`modules/mega_automation/callback.py`（状态回调与 `apply_labillion_status`）；`modules/mega_automation/labillion_sync.py`（主动查询与定时批量同步）。`LABILLION_BASE_URL` 留空时不发起对外 HTTP，本地工单状态仍可用。细节见 [modules/mega-automation/flow-work-order.md](./modules/mega-automation/flow-work-order.md)。

外部主数据：`EMPLOYEE_DB_URL` 只读连接外部平台库；`modules/system/employee_sync.py` 同步员工资料，`modules/system/target_sync.py` 全量同步靶点至本地 `target`。两者使用独立定时任务，共用外部连接。

## API 前缀

| 前缀 | 后端位置 |
|------|----------|
| `/api/health` | `api.py` |
| `/api/auth` | `modules/auth` |
| `/api/user/info` | `api.py`（Vben 用户信息） |
| `/api/discovery` | `modules/discovery` |
| `/api/serum` | `modules/immunology/serum` |
| `/api/serum/workbench` | `modules/immunology/workbench` |
| `/api/serum/titer` | `modules/immunology/titer` |
| `/api/serum/cell_inventory` | `modules/immunology/cell` |
| `/api/mega-automation` | `modules/mega_automation` |
| `/api/order-experiment` | `modules/order_sync` |
| `/api/system` | `modules/system` |

前后端路径对照见 [overview.md](./overview.md)。前端开发时业务请求统一走 `/api`。

## 响应格式

业务接口（除健康检查外）统一：

- 成功：`{ "code": 0, "data": ... }`
- 业务失败（HTTP 200）：`{ "code": 1, "message": "..." }`（`BusinessError` 可带 `errorCode`）
- HTTP 异常（401/403/404/500）：保留状态码，body 同上
- 健康检查 `/api/health`：`{ "status": "ok" }`（不走上述 envelope）
- 设备回传 `/api/order-experiment/sync`：`{ "code", "message", "trace_id", "data" }`（multipart 上传 `order_json`）

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
