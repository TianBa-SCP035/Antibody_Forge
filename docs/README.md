# Antibody Forge 文档

本目录是**项目文档入口**。产品介绍与能力范围见根目录 [README.md](../README.md)；本页维护文档索引、开发约定和待建设事项。

| 文档 | 内容 |
|------|------|
| **本文** | 文档索引、开发约定、待建设事项 |
| [overview.md](./overview.md) | 仓库地图、当前路由、设计要点、快速启动 |
| [auth-permissions.md](./auth-permissions.md) | 认证、RBAC、功能开关、血清归属 |
| [backend-structure.md](./backend-structure.md) | 后端目录、路由注册、测试、响应与错误约定 |
| [deploy.md](./deploy.md) | 环境与端口、配置、启动、Nginx、DRM、验收 |
| [fatfish.md](./fatfish.md) | 桌宠「大肥鱼」：前端模块、本机代理接口、能力与安全边界 |
| [vita-database.sql](./vita-database.sql) | 主库 DDL + 示例权限包和角色（空库执行一次） |
| [modules/](./modules/) | 各业务模块详细说明（按模块分子目录），见下表 |

`overview` / `auth-permissions` / `backend-structure` / `deploy` 只写当前行为；待建设事项集中在本文末尾。

**文档分层**：根目录文档 = 全景与运维概要；`modules/` = 已成型模块的详细设计。

### 模块文档

| 模块 | 文档 |
|------|------|
| 工作台类页面共用约定（表头筛选、视图与列、队列排序、保存并发） | [modules/workbench.md](./modules/workbench.md) |
| 千鼠万抗 · 靶点库 | [modules/atlas/target-library.md](./modules/atlas/target-library.md) |
| 小鼠免疫 · 项目工作台 | [modules/immunology/workbench.md](./modules/immunology/workbench.md) |
| 抗体发现 · 项目工作台 | [modules/discovery/workbench.md](./modules/discovery/workbench.md) |
| 抗体发现 · 合成与验证 | [modules/discovery/synthesis-progress.md](./modules/discovery/synthesis-progress.md) |
| 分子与细胞 · 文库构建 | [modules/molecular-cell/library-construction.md](./modules/molecular-cell/library-construction.md) |
| 分子与细胞 · 引物库 | [modules/molecular-cell/primer-library.md](./modules/molecular-cell/primer-library.md) |
| 分子与细胞 · 转染与表达 | [modules/molecular-cell/transfection.md](./modules/molecular-cell/transfection.md) |
| 镁伽流式工单 | [modules/mega-automation/flow-work-order.md](./modules/mega-automation/flow-work-order.md) |
| 效价 → 流式工单 | [modules/mega-automation/titer-upstream-flow.md](./modules/mega-automation/titer-upstream-flow.md) |
| 工单数据回传接口（对外协议） | [modules/mega-automation/order-experiment-sync-api.md](./modules/mega-automation/order-experiment-sync-api.md) |
| 上清板布局接收接口（对外协议） | [modules/discovery/supernatant-receive-api.md](./modules/discovery/supernatant-receive-api.md) |

免疫实验列表、效价数据、效价实验列表、细胞库存暂无独立模块文档，路由前缀见 [overview.md](./overview.md)，权限见 [auth-permissions.md](./auth-permissions.md)。

代码：`bbctg_vita_server/` 后端 · `bbctg_vita_web/apps/antibody_vita/` 前端 · `config/` 环境配置 · `repository/` 运行时文件。

## 开发约定

越快越好，越简单越好。需求对上现有页面或接口就直接做完，不先出方案，不反复确认，不做优化，不整理提交，不为代码合并或抽公共层花时间。能少一步就少一步。

日常就三步：Agent 改代码时把主库结构变更打进能连上的库；人把代码推到服务器正在跟踪的分支；服务器每分钟拉取并重启，见 [deploy.md](./deploy.md)。文件放哪、权限和库怎么接，以邻近代码为准。Cursor 规则见 `.cursor/rules/fast-iteration.mdc`。

### 代码

- **只做这次要的**：不优化，不重构，不扩大改动，不把几处写法收成一套，不为分支合并或提交历史花时间。
- **前台要干净**：后端能跑即可。页面跟着现有界面做，操作简单、不出错。用已有的颜色和间距，不要粗线、亮色条或过宽的空列。
- **拒绝幽灵代码**：不提交未使用的函数/变量、大段注释掉的旧逻辑、仅为「以后可能用到」的占位实现；临时调试代码不入库。
- **不为未开工功能建壳**：空菜单、空路由、空表、假数据接口等一律不做（路线图见下文「待建设事项」）。
- **单一数据源**：同一业务事实只存一处；跨模块用已有主键关联，避免双写与「两边各改一半」。
- **分层清晰**：业务规则放 service / 领域模块；路由与页面只做参数、权限与展示；对外集成（如 Labillion）独立在 `integrations/`。
- **权限与审计**：新增写接口须显式鉴权，并按 [auth-permissions.md「操作审计」](./auth-permissions.md#6-操作审计) 在路由上声明操作名（`require(..., audit=)`、`audit()` 或 `audit_quiet()`）；主库 ORM 写入自动记操作日志。新模块可先设路由查看权限和全部编辑权限，只加权限点，不改现网角色、权限包及其绑定。
- **测试**：后端与前端测试目录、命名、公共基类和执行命令统一见 [backend-structure.md「测试」](./backend-structure.md#测试)。
- **新模块**：按 [modules/workbench.md「新模块全栈接入清单」](./modules/workbench.md#新模块全栈接入清单) 接入，照参照模块（发现工作台）写，不另起一套结构。

### 注释

- **中文、短句**：注释和 docstring 用中文完整短句；标识符、字段名、权限码、状态值按代码原样写。
- **只写代码表达不了的**：外部接口的特殊行为、加锁和事务顺序、看似多余的判断为什么要有、业务规则的口径。不复述下一行在做什么，不加没有内容的分节标题。
- **不写修改经过**：不写「改为」「修复」「新增」「原来」、日期、需求人，这些写进提交说明。
- **不留旧代码**：不提交注释掉的代码和已经完成的 TODO。
- **随代码一起改**：改行为时同步改相关注释。注释和代码不一致时，按当前代码改注释；这次任务要改的行为直接改代码。
- **前端同样适用**：包括 JSDoc、模板 `<!-- -->` 和样式注释；公共组件对外的 props、事件和方法写 JSDoc。`/* theme-ok */` 这类工具标记保留。

### 文字风格

界面提示和后端业务报错按下面写；文档按正常中文书写，同样用全角标点，引用界面文字时用「」：

- **中文、全角标点，句末不加句号**；一句以上用「，」「；」连接。
- **用界面上的叫法**：字段、状态、按钮用页面显示的中文名，不出现英文、异常类名、SQL 或内部字段名；引用具体值或字段时用「」，如「不支持按「{field}」表头筛选」。
- **报错先说原因，能给下一步就接在后面**：如「工单已完成，不能再改实验状态；需要重新检测请先打回待检测」。常用句式「X不能为空」「X不存在」「仅…可以…」「请先…」。
- **成功提示简短**：「已保存」「X已保存」。
- **后端报错要能直接给用户看**：页面配置的操作级文案优先，没有配置时显示后端 `message`，分层见 [backend-structure.md「前端错误分层」](./backend-structure.md#前端错误分层l0l3)。

### 前端颜色

- **只用变量**：页面颜色用 Element 变量（`--el-*`）和 `src/styles/theme.css` 的 `--vita-*`，暗色自动生效；新的共享色加到 `theme.css`，亮暗各一份。主题色只影响 Vben 外壳，页面内容统一用 Element 蓝。
- **按用途选**：文字 `--el-text-color-*`，底色 `--el-bg-color` / `--el-fill-color-*`，线 `--el-border-color-*`，状态 `--el-color-*`。暗色里 `-light-N` 会变暗，不能当文字色。
- **数据含义色可写死**：文件类型、图表、负责人标签等固定配色直接写；暗色看不清时在该文件样式末尾集中写 `html.dark` 覆盖。
- **测试拦截**：`src/styles/themeColors.test.mjs` 拦截样式里写死的 Element 色板色。它提示的变量只按颜色就近给出，仍按用途选；确属数据含义色的行加 `/* theme-ok */`。

### 数据库

- **结构变更当轮执行**：任务已包含的建表、加列、改类型、加索引，由 Agent 按 `.cursor/rules/database-schema.mdc` 连上能到达的 local / test / prod 主库执行并核对，不再单独确认。当前任务没有要求丢掉业务数据时，不删表、不删列、不改业务行。
- **只加这次要用的**：新表和新字段只为当前需求。不建用不到的占位。
- **全表登记**：主库涉及的所有表（含示例权限包和角色）须维护在 [vita-database.sql](./vita-database.sql)，与 ORM / 业务代码一致；**外部只读库**（细胞库、员工库等）在 SQL 文末注释说明，不在主库脚本中建表。
- **只记录当前状态**：该文件是**空库一次性执行的完整 DDL + 示例权限包和角色**，直接改表定义即可；**不**在此文件堆叠历史 `ALTER`、升级脚本或迁移版本号。已有库与当前定义的差额由 Agent 在当轮执行，不另存升级脚本。
- **注释齐全一致**：每张表、每个字段都写简练的中文 `COMMENT`，只说明业务含义，不在括号中列举可能值。改表时同步改 ORM 与相关模块文档。

### 配置与密钥

- **严禁硬编码泄密项**：代码、文档、注释中**不得**出现数据库密码、JWT `SECRET_KEY`、第三方账号密码、内网 token 等；仅允许读取环境配置。
- **统一走配置文件**：连接串、密钥、各对外/对内 **API 根地址**（如 `DATABASE_URL`、`LABILLION_BASE_URL`、`PUBLIC_API_BASE_URL`、`YUNZHIJIA_*` 等）写在 `config/<local|test|prod>/vita_server.env`（模板见同目录 `*.gitkeep`），**勿提交**真实 env 文件。
- **新增变量**：在 [deploy.md](./deploy.md) 补充变量含义与是否必填；代码通过 `core/config.py`（或现有配置入口）读取，不在业务模块里写死 URL/端口。
- **默认值仅 local 兜底**：`core/config.py` 中的 `database_url`、`secret_key` 等默认值仅供本地无 env 时启动；test / prod 必须在 `config/<env>/vita_server.env` 中配置。prod 启动时会自检（默认库、短密钥、`DEBUG`、`CORS_ORIGINS`），不通过直接拒绝启动；test 不自检，靠人工保证。
- **前端**：业务请求统一走 `/api` 代理；不在源码里写死后端域名或生产端口（本地 Vite 代理配置除外）。

### 接口

- **沿用统一约定**：新接口对齐 [backend-structure.md](./backend-structure.md)——路由前缀与模块目录对应、响应 `{ code, data }` / 业务错误 `{ code: 1, message, data: null }`、HTTP 状态与 `BusinessError` 用法、写操作权限与审计登记。
- **前后端同步**：改后端路径或请求/响应字段时，同步改前端 API 客户端（如 `api/*.ts`）与类型，避免页面内散落裸 URL 或重复封装。
- **对外/设备接口**：特殊格式（如 `order-experiment/sync` multipart）在模块文档或 `backend-structure.md` 中说明，不单独搞一套无文档约定。

### 文档

- **行为变了就改现有文档**：字段、状态、对外协议或权限有变时，改已经在写这块的模块文档。不为此新建文档，不把讨论过程写进去。
- **写到哪里**：表结构 → `vita-database.sql`；全景与路由 → `overview.md`；权限/功能开关 → `auth-permissions.md`；后端约定 → `backend-structure.md`；部署与环境变量 → `deploy.md`；单模块详述 → `modules/<模块>/`。
- **只写已实现**：`overview` 等概要文档描述当前行为；规划与菜单蓝图**仅在本 README「待建设事项」**维护，不在多处重复写「将来可能」。
- **不写修改经过**：文档描述现在是什么样，不写「已修复」「新增了」「之前是」、版本演变和进度。历史截止日期等边界会影响当前逻辑时，直接写当前规则和边界值。
- **简洁直述**：句子短、结构清楚；同一事实不在多篇文档间来回复制——模块内细节一篇为主，跨模块边界文首互链即可（参考 `modules/mega-automation/` 两篇分工）。

### 协作

- **先打通能用的一段**：表、接口、页面、权限一起改完。外部协议还没到时，先交能用的部分，并在现有文档里写清边界。
- **人只推代码**：主库结构由 Agent 在当轮打进能连上的库。代码推到服务器正在跟踪的分支后，由服务器自动拉取重启。
- **提交说明**：写清「为什么改」；主库结构有变时，注明哪些环境已经对齐。

## 待建设事项

后续计划只记录尚未实现的工作，不预建空菜单、空路由或占位表：

1. 建设千鼠万抗的免疫与小鼠计划、发现订单和路线编排。
2. 在单 B 细胞筛选或噬菌体展示中选择一条主路线，打通筛选执行。
3. 建设与筛选路线配套的 Sanger / NGS 测序和序列分析。
4. 镁伽回传目前只导入效价（`TITER`）；`PLAS`、`PCR` 等其他类型仅存档，待对应业务建好后再导入。
5. 随上游产出建设质粒构建、细胞制备与转染、表达、纯化与抗体评价模块（现有细胞库存为外部只读查询，不在此列）。
