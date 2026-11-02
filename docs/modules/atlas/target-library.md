# 千鼠万抗 · 靶点库

> 本地靶点主数据只读检索、摘要预览与完整档案查看工作台。相关：[系统全景](../../overview.md) · [认证与权限](../../auth-permissions.md) · [免疫工作台](../immunology/workbench.md) · [合成与验证](../discovery/synthesis-progress.md)

## 1. 入口与权限

- **前端路由**：`/atlas/targets`（父级 `/atlas` 重定向至 `/atlas/targets`，组件 `src/views/Atlas/TargetLibrary/TargetLibrary.vue`；侧栏菜单名「靶点情报」，页面标题「靶点情报工作台」）。
- **页面缓存**：路由启用 `keepAlive: true`，切走超过 10 分钟再次进入时静默刷新当前筛选结果（`useStaleTabRefresh`）。
- **菜单功能开关**：`menu.atlas`（千鼠万抗）、`menu.atlas.target_library`（靶点情报）。

| 权限代码 | 允许的操作与范围 |
|---|---|
| `atlas.page.target_library` | 访问靶点库页面，调用 `POST /api/atlas/targets/list` 查询靶点列表与状态统计 |
| 任一业务页权限（`OPTION_ACCESS_PERMISSIONS`） | 免疫、发现工作台、合成与验证、文库构建、流式工单等业务页调用公共接口 `GET /api/options/targets` 远程检索靶点下拉选项 |

## 2. 数据与编号

本地主表为 `target`（唯一索引：`uk_target_external_id`、`uk_target_snum`），数据同步自外部只读项目管理库 `xdida_platform_biocytogen.target`（关联 `org_tag` 与 `target_tag`）。页面仅查询本地主库，不直接联查外部库。

| 字段 | 含义 | 规则与前端展示 |
|---|---|---|
| `id` | 本地主键 | 自增 `BigInteger` |
| `external_id` | 外部平台靶点 ID | 对应源表 `target.id`，唯一，必填 |
| `snum` | 靶点编号 | 唯一业务编号（如 `20R015`），必填 |
| `name` / `official_full_name` | 靶点名称 / 官方全名 | `name` 必填；`official_full_name` 为空时列表与摘要显示 `暂无官方全名` |
| `status` | 开发状态 | `1`=`已开发`、`2`=`未开发`、`NULL`=`未标注` |
| `type` | 靶点来源 | `1`=`内部-千鼠万抗`、`2`=`内部-其他`、`3`=`外部`、`4`=`NA`、`NULL`=`未标注`（其余值显示 `未知来源`） |
| `category` | 靶点分类 | 源表 `target.sort` 关联 `org_tag.sname` |
| `structural_properties` | 结构特性类别 | 源表 `target.structural_properties` 关联 `org_tag.sname`，或由同库/UniProt 容错补齐 |
| `structure_feature` | 跨膜次数 | 原始跨膜特征文本；纯数字 `N` 在完整档案展示为 `N次跨膜` |
| `treatment_field` / `indication` | 治疗领域 / 适应症 | `treatment_field` 由 `target_tag` 关联 `org_tag`（`tag_type = 36` 且 `is_delete = 0`）按 `, ` 拼接 |
| `human_gene_official_name` / `human_gene_alias_name` / `human_ncbi_gene_id` / `human_chromosome_position` | 人源基因信息 | 官方名称、别名、NCBI Gene ID、染色体位置（纯数字显示 `{N}号染色体`，`X`/`Y` 显示 `X染色体`/`Y染色体`，其余位点如 `7q34` 原样保留） |
| `mouse_gene_official_name` / `mouse_gene_alias_name` / `mouse_ncbi_gene_id` / `mouse_chromosome_position` | 鼠源基因信息 | 同人源基因展示规则 |
| `is_homologous_gene` | 是否有同源基因 | 布尔值：`true`=`是`、`false`=`否`、`NULL`=`未标注` |
| `human_mouse_homology` / `human_monkey_homology` / `human_dog_homology` / `human_cat_homology` / `human_mouse_homology_expect_functional_domain` | 跨物种同源性 | 人鼠、人猴、人犬、人猫及预期功能结构域人鼠同源性 |
| `ko_lethal_info` / `ko_lethal_info_desc` / `ko_mgi` / `ko_impc` / `ko_gt` | KO 表型信息 | `ko_lethal_info`：`1`=`致死`、`2`=`存活`、`3`=`致死数据冲突`、`4`=`NA`、`NULL`=`未标注`（其余值显示 `未知`） |
| `gene_family` / `effect_cell` / `gene_functional_desc` / `signal_path` | 功能描述 | 基因家族、作用细胞、基因功能描述、信号通路 |
| `is_ko_affect_humoral_immunity` / `is_ko_affect_humoral_immunity_desc` / `is_human_mouse_cross` | 免疫相关特征 | `is_ko_affect_humoral_immunity` 为布尔值（`是`/`否`/`未标注`） |
| `shape_remark` / `structure_feature_remark` / `remark` | 备注字段 | 形式备注、结构特性备注、备注 |
| `is_active` | 数据状态 | 默认 `true`（`有效`）；外部源记录消失时标为 `false`（`已下架`），不物理删除 |
| `synced_at` | 最近变更时间 | 记录新增或字段值变更时自动刷新，内容未变化时不更新；在完整档案底部显示为「最近变更」 |

## 3. 页面操作

### 搜索与相关度排序

- **搜索范围（`SEARCH_FIELDS`）**：大小写不敏感包含匹配（`ILIKE`）12 个字段：`snum`、`name`、`official_full_name`、`human_gene_official_name`、`human_gene_alias_name`、`human_ncbi_gene_id`、`mouse_gene_official_name`、`mouse_gene_alias_name`、`mouse_ncbi_gene_id`、`category`、`structural_properties`、`treatment_field`。
- **中文结构特性别名匹配**：输入搜索词若精确命中中文靶点类型或预设别名（`match_structural_properties_by_keyword`，如 `I型`、`一型跨膜`、`II型`、`III型`、`IV型`、`单次跨膜`、`单穿`、`多次穿膜`、`多穿`、`跨膜`、`跨膜蛋白`、`分泌`、`分泌型`、`可溶性`、`胞内`、`GPI`、`外周膜`、`脂锚定`、`细胞膜`、`其他` 等），自动反查对应英文 `structural_properties` 枚举并纳入过滤与描述性匹配。
- **相关度排序**：无搜索词时按 `name ASC, snum ASC` 排序；有搜索词时按 `relevance ASC, name_match_length ASC, name ASC, snum ASC` 排序：

| 权重 `relevance` | 命中规则 |
|---|---|
| `0` | `snum` 完全匹配 |
| `1` | `name` 完全匹配 |
| `2` | 人/鼠基因官方名称（`human_gene_official_name` / `mouse_gene_official_name`）完全匹配 |
| `3` | 人/鼠 NCBI Gene ID（`human_ncbi_gene_id` / `mouse_ncbi_gene_id`）完全匹配 |
| `4` | `official_full_name` 或人/鼠基因别名（`human_gene_alias_name` / `mouse_gene_alias_name`）完全匹配 |
| `10` | `snum` 前缀匹配 |
| `11` | `name` 或人/鼠基因官方名称前缀匹配 |
| `20` | `name` 包含匹配（同级按 `length(name)` 升序，优先展示更短名称） |
| `21` | 人/鼠基因官方名称包含匹配 |
| `22` | `snum` 包含匹配 |
| `30` | 人/鼠基因别名包含匹配 |
| `40` | `official_full_name` 包含匹配 |
| `45` | 描述性字段（`category`、`structural_properties`、`treatment_field`）包含匹配，或命中中文结构类型别名映射 |
| `50` | 人/鼠 NCBI Gene ID 包含匹配 |
| `60` | 兜底排序 |

### 状态筛选与档案浏览

- **状态卡片与下架开关**：
  - 右上角复选框 **「显示已下架」**（`include_inactive`）：默认不勾选（仅查询 `is_active = true`）；勾选后包含已下架记录。
  - 4 个开发状态快捷卡片：**`全部`**（`""`）、**`已开发`**（`"1"`）、**`未开发`**（`"2"`）、**`未标注`**（`"unknown"`，对应 `status IS NULL`）。卡片统计数（`stats.total / developed / undeveloped / unmarked`）跟随 `keyword` 与 `include_inactive` 实时计算，不受当前选中状态卡片影响。
  - 左上角 **「最近同步」** 读取 `job.target_master_sync` 最近一次成功运行日志的 `finished_at`（无日志时回退为 `max(target.synced_at)`）。
- **左侧列表与右侧「靶点摘要」（Spotlight）**：
  - 左侧列表支持服务端分页（每页 `20 / 50 / 100 / 200 / 500` 条）及「重置筛选」，点击行在右侧渲染摘要。
  - 右侧摘要展示靶点名称（带 UniProt 外部搜索链接：优先按人源 NCBI Gene ID、次选鼠源 NCBI Gene ID、再次选剥离 `dog`/`canine`/`cat`/`feline`/`monkey`/`cyno` 前缀后的官方基因名或靶点名生成）、靶点编号、官方全名、人/鼠源基因、人/鼠 NCBI Gene ID（纯数字带 NCBI Gene 链接）、基因家族、适应症、功能摘要（最多 4 行）及底部 4 个特征胶囊（`靶点类型`、`KO致死`、`同源基因`、`人鼠同源性`）。
- **下方「完整靶点档案」**：点击右侧「完整靶点档案」开关卡片在主工作台下方展开（展开时锁定上方列表与摘要区高度并平滑滚动），右上角提供「项目管理详情」外链（`https://pm.biocytogen.com.cn/#/target/detail/info/{external_id}`），按 `基础信息`、`人源基因`、`鼠源基因`、`跨物种同源性`、`KO与结构特征`、`功能与免疫相关` 6 个分组展示完整字段及底部备注、数据状态（`有效`/`已下架`）、外部平台 ID 与最近变更时间。

## 4. 跨模块联动 / 外部集成

### 靶点结构特性公共映射（`utils/target_structure.py` / `src/utils/targetStructure.ts`）

前后端通过公共纯函数 `parse_target_structure(structural_properties, structure_feature)` 将英文结构特性与跨膜次数解析为中文类型，并支持二次映射为免疫模块 `serum_type`：

| 英文 `structural_properties` | 中文 `label` | 免疫模块 `serum_type` | 大类 `broad_group` |
|---|---|---|---|
| `Single-pass transmembrane protein Type I` | `I型跨膜` | `I型` | `跨膜蛋白` |
| `Single-pass transmembrane protein Type II` | `II型跨膜` | `II型` | `跨膜蛋白` |
| `Single-pass transmembrane protein Type III` | `III型跨膜` | `III型` | `跨膜蛋白` |
| `Single-pass transmembrane protein Type IV` | `IV型跨膜` | `I型` | `跨膜蛋白` |
| `Single-pass transmembrane protein` | `单次跨膜` | `I型` | `跨膜蛋白` |
| `Multi-pass transmembrane protein` | `多次穿膜` | `多穿` | `跨膜蛋白` |
| `Secreted` | `分泌型` | `分泌` | `分泌蛋白` |
| `Intracellular protein` | `胞内蛋白` | `胞内` | `胞内蛋白` |
| `GPI-anchored protein` | `GPI锚定` | `GPI` | `膜关联蛋白` |
| `Peripheral membrane protein` | `外周膜蛋白` | `胞内` | `膜关联蛋白` |
| `lipid-anchor protein` | `脂锚定蛋白` | `胞内` | `膜关联蛋白` |
| `Cell membrane protein` | `细胞膜蛋白` | `I型` | `膜关联蛋白` |
| `Other` | `其他` | `None` | `其他` |

- `Single-pass*` 未填有效跨膜次数时默认 `tm_count = 1`；若 `structural_properties` 为空但有有效跨膜次数（`1` → `单次跨膜`，`>1` → `多次穿膜`）或 `structure_feature` 含 `分泌`/`secreted`/`胞内`，按 `structure_feature` 兜底推导。
- 当 `tm_count > 0` 时，`full_label` 格式为 `{label}（{tm_count}次跨膜）`（靶点库摘要使用 `full_label`；合成与验证模块使用 `label`；免疫模块使用 `serum_type`）。

### 外部 PM 库同步与 UniProt 容错补齐（`modules/system/target_sync.py`）

- **全量比对与防冲突规则**：
  - 源表记录缺失 `external_id`、`snum`、`name` 或发生唯一键冲突时跳过并计入 `skipped`；源表消失的记录仅将本地 `is_active` 置为 `false`。
  - 当源表 `structural_properties` 非空时采用源表值；源表为空时保留本地已有补齐值。
  - 当源表 `structure_feature` 有有效值（非空且非 `NA`/`未知` 等占位符）时采用源表值；源表无有效值且最终生效的 `structural_properties` 为空或仍为跨膜蛋白时，保留本地有效跨膜次数。
- **同库复用与 UniProt 在线补齐（`enrich_missing_targets`）**：
  - 对新增或基因标识字段（`name`、人/鼠 NCBI Gene ID、人/鼠官方基因名）变更且缺失 `structural_properties` 的记录：
    1. 先尝试剥离种属前缀（`dog`/`canine`/`cat`/`feline`/`monkey`/`cyno`/`rhesus`/`equine`/`bovine`）或取连字符 `-` 前首靶点名（长度 ≥ 3），在同库已有结构特性的靶点中匹配复用。
    2. 未命中时调用 UniProt REST API（单次任务最多请求 30 个靶点，单次超时 10 秒），按「人源 NCBI Gene ID → 鼠源 NCBI Gene ID → 人源基因名/剥离前缀名/靶点名 → 鼠源基因名」优先级检索并推导 `structural_properties` 与 `structure_feature`。网络异常时捕获跳过，不中断同步事务。

## 5. 接口

| 方法 | 路径 | 权限 | 用途 |
|---|---|---|---|
| `POST` | `/api/atlas/targets/list` | `atlas.page.target_library` | 分页查询靶点列表与状态统计（请求体：`page`、`limit` 1..500 默认 20、`keyword`、`status`、`include_inactive`） |
| `GET` | `/api/options/targets` | `OPTION_ACCESS_PERMISSIONS` 任一权限 | 跨模块靶点下拉远程搜索（参数：`keyword`、`limit` 1..50 默认 20、`codes` 逗号分隔已选编号置顶返回），复用 `get_target_list` 搜索与排序逻辑 |

## 6. 定时任务

- **任务代码**：`job.target_master_sync`（名称：「靶点主数据定时同步」，实现：`jobs/target_master_sync.py`）。
- **默认周期**：每天 `00:45` 执行（`schedule: "daily", hour: 0, minute: 45`）。在系统管理页面修改任务开关或调度配置后，通过 `jobs/registry.py` 的 `apply_job_schedule` 立即生效，无需重启服务。
- **执行逻辑**：调用 `sync_targets(db, source_db, enrich_uniprot=True)` 同步外部 `xdida_platform_biocytogen.target` 主数据并执行同库/UniProt 结构特性补齐，执行结果记录至 `sys_job_run_log`。
