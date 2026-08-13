# 千鼠万抗 · 靶点库

靶点库是千鼠万抗模块的第一块能力，面向 PM 只读查询项目管理平台中的靶点主数据。

## 数据来源

- 权威来源：外部项目管理库 `xdida_platform_biocytogen.target`。
- 本地镜像：主库 `target`。
- 同步任务：`job.target_master_sync`，默认每天 00:45 全量同步。
- 页面只查询本地主库；外部记录消失时本地仅将 `is_active` 标为 `false`。

源系统枚举已与项目管理页面核对：`status` 为 1 已开发、2 未开发；`type` 为 1 内部-千鼠万抗、2 内部-其他、3 外部、4 NA；`ko_lethal_info` 为 1 致死、2 存活、3 致死数据冲突、4 NA。页面显示对应含义，数据库保留源代码；`is_active` 表示源记录是否仍存在。

人源和鼠源染色体位置不是枚举代码。纯数字代表染色体编号，页面显示为“1号染色体”等易读形式；`X`、`7q34` 等性染色体或具体位点信息按其生物学含义保留。

## 页面

前端路径：`/discovery/targets`

- 顶部提供有效总数和开发状态快捷筛选。
- 搜索覆盖靶点编号、名称、官方全名、人/鼠基因名、别名及 NCBI Gene ID。
- 搜索结果按相关度排序：完全匹配优先，其次是编号或名称前缀、名称包含、别名、官方全名，NCBI Gene ID 的部分匹配最后展示；名称包含结果优先展示更短、更直接的名称，其余同级按名称和编号稳定排序。
- 默认隐藏已下架记录，支持服务端分页。
- 主页面保持左侧靶点列表、右侧 Spotlight，不跳转子页面。
- 完整档案通过开关在主工作台下方展开，无需跳转子页面或打开弹窗。
- 页面启用 KeepAlive；离开后超过 10 分钟再次进入时，按项目统一机制静默刷新当前筛选结果。

首版不提供编辑、手动同步、关注、对比或实验进程。实验进程必须等业务表建立可靠的 `target.id` 关联后再接入，不按名称猜测关联。

## API

```text
POST /api/discovery/targets/list
```

请求体包含 `page`、`limit`、`keyword`、`status` 和 `include_inactive`。`status` 可为 `1`、`2`、`unknown` 或空。接口需要 `discovery.page.target_library` 权限。

## 实现位置

```text
bbctg_vita_server/modules/discovery/
bbctg_vita_web/apps/antibody_vita/src/views/Discovery/TargetLibrary/
bbctg_vita_web/apps/antibody_vita/src/api/discovery.ts
bbctg_vita_web/apps/antibody_vita/src/router/routes/modules/discovery.ts
```

后续免疫与发现流程通过本地 `target.id` 建立关联，不在本页复制业务状态。
