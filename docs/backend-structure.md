# 后端结构

> 总览 [overview.md](./overview.md) · 权限 [auth-permissions.md](./auth-permissions.md)

## 目录

```text
bbctg_vita_server/
  server.py          # 启动入口
  main.py            # 应用：CORS、日志、路由、定时任务
  api.py             # 汇总各模块 routes
  core/              # 配置、响应、异常、请求日志
  db/                # 主库与外部只读库 session
  models/            # ORM 模型
  modules/           # 业务
    auth/            # 登录、JWT
    system/          # 用户/角色/权限、审计、功能开关
    immunology/      # serum、titer、cell
  integrations/      # 云之家、drm_service（SDK 在 integrations/drm/，gitignore）
  jobs/              # 定时任务
  utils/
```

## 模块要点

- **权限**：RBAC + 权限包 + 个人覆盖；部门等组织字段不参与鉴权（见 auth-permissions）。
- **菜单**：前端路由 `meta` 维护；`sys_feature_flag` 仅控制显隐与任务调度。
- **DRM**：业务只 import `integrations/drm_service.py`；上传密文解密、Office 附件下载加密；失败不阻断传输。Linux 需启动前配置 `LD_LIBRARY_PATH`（见 deploy.md）。
- **定时任务**：`employee_profile_sync`（00:30）、`serum_auto_update_status`（01:00）；`prod` 或 `ENABLE_SCHEDULER=true` 时启动。

## 根目录约定

```text
config/<env>/vita_server.env   # 密钥与连接串（不提交）
repository/
  uploads/titer_files/         # 效价附件
  exports/ cache/ logs/ tmp/   # 导出、DRM 缓存、日志、临时文件（tmp/scheme_export 为方案 PDF 转换）
```

配置：`APP_ENV` 或 `VITA_SERVER_ENV_FILE` 选择 env 文件（详见 deploy.md）。

## API 前缀

| 前缀 | 模块 |
|------|------|
| `/api/auth` | 登录、用户信息、改密 |
| `/api/serum` | 血清项目 |
| `/api/serum/titer` | 效价、FACS、附件 |
| `/api/serum/cell_inventory` | 细胞库存（只读外部库） |
| `/api/system` | 系统管理、功能开关 |
| `/api/user/info` | Vben 用户信息 |

前端开发：全部业务走 `/api`（Vite 代理到后端）。

## 响应格式

- 成功：`{ "code": 0, "data": ... }`
- 业务失败（HTTP 200）：`{ "code": 1, "message": "..." }`
- HTTP 异常（401/403/404/500）：保留 HTTP 状态，body 同为 `{ "code": 1, "message": "..." }`

## 前端错误分层（L0–L3）

| 层 | 位置 | 职责 |
|----|------|------|
| L0 | 各页面 | 权限/表单校验，`ElMessage.warning`，不发请求 |
| L1 | `views/Serum/errors.ts`、`views/System/errors.ts` | 操作级用户文案；`notifyApiError(err, { messages })` |
| L2 | `api/errors.ts` + `api/request.ts` 全局拦截 | 403/404/500/断网/超时兜底 |
| L3 | 后端 `message` | 操作日志、开发调试、L1 未配时的 fallback |

需要定制 UX 的请求设 `skipErrorHandler: true`（可在 API 封装或页面调用处），由 `.catch` 调用 `notifyApiError`。
