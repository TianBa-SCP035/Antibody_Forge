# 分子与细胞 · 引物库
> 维护引物与 Barcode 字典（含预置达普Barcode、UDP 及自建系列），供文库构建工单选配与测序读段核对。相关：[文库构建](./library-construction.md) · [项目工作台共用约定](../workbench.md)

## 1. 入口与权限

| 项目 | 值 |
|---|---|
| 页面路由 | `/molecular-cell/primer-library`（`PrimerLibrary.vue`；父路由 `/molecular-cell` 默认重定向至此） |
| 一级菜单开关 | `menu.molecular_cell` |
| 页面菜单开关 | `menu.molecular_cell.primer` |
| 接口前缀 | `/api/molecular-cell/library-orders/catalog` |

| 权限码 | 类型 | 允许的操作 |
|---|---|---|
| `molecular.page.primer` | `page` | 访问引物库页面；查询列表（`/list`）、表头筛选候选值（`/column_values`）、全选 ID（`/ids`）、导出 Excel（`/export`）及引物下拉选项（`/options`） |
| `molecular.primer.edit` | `action` | 单条新增与修改（`/save`）、单条删除（`/delete`）、批量改系列/改方向/启停（`/batch_update`）、批量删除（`/batch_delete`）、Excel 批量导入（`/batch_save`） |
| `molecular.page.library`、`molecular.page.library_detail` | `page` | 在文库构建列表与质控详情页调用 `GET /catalog/options` 查询启用引物 |

## 2. 数据与编号

表：`molecular_primer_index_catalog`（唯一索引 `uk_molecular_primer_index_name (name)`）。

| 字段 | 含义 | 规则 |
|---|---|---|
| `id` | 主键 ID | 数据库自增主键 |
| `name` | 引物名称 | 必填，最长 128 字符，全局唯一 |
| `family` | 系列 | 必填，最长 32 字符；预置 `达普Barcode`（达普仪器）、`UDP`（其他仪器或步骤），支持输入新名称自建系列 |
| `direction` | 方向 | 必填，库内存储 `F`（正向）或 `R`（反向）；写入接口同时接受 `F`、`R`、`正向`、`反向` |
| `short_sequence` | 显示序列 | 必填，最长 64 字符；去除空白并转为大写，仅允许 `A`、`C`、`G`、`T`、`N`，允许不同引物重复 |
| `check_sequence`（派生） | 核对序列 | 不入库，由 `short_sequence` 取反向互补实时计算（`A↔T`、`C↔G`、`N↔N` 并反转），与测序文件读段方向一致 |
| `note` | 备注 | 可空，最长 500 字符，保留换行 |
| `active` | 状态 | 布尔值，默认 `true`（启用）；停用后不出现在 `/catalog/options` 选项中 |
| `version`、`homology_arm_1`、`homology_arm_2`、`source_file`、`source_row` | 版本、同源臂与来源信息 | 库表保留字段；页面弹窗与导入/导出不展示这些列，保存或导入未传非空值时保留库内原值 |
| `created_at`、`updated_at` | 创建与更新时间 | 数据库自动维护 |

**引用保护与停用规则**：
- 未被任何 `molecular_library_order` 引物外键（`h/k/l_forward/reverse_primer_id`、`i7_catalog_id`、`i5_catalog_id`）引用的引物可直接删除。
- 已被文库工单引用的引物禁止删除（单条删除返回 422 提示，批量删除自动跳过并返回跳过名单），只能停用；停用不影响工单上已保存的名称和序列快照。

## 3. 页面操作

公共表头筛选规则见 [../workbench.md](../workbench.md)「表头筛选」。

### 3.1 系列统计与筛选

- **系列统计块**：顶部展示「全部」及各系列统计卡片；预置系列 `达普Barcode`、`UDP` 始终占位，自建系列有数据时按名称排序展示。统计计数受名称、序列、备注、方向、状态等条件约束，不受顶部和表头的 `family`（系列）条件影响。点击系列卡片筛选对应系列（同时清除表头的系列条件）。
- **筛选栏**：支持名称、显示序列、核对序列（输入 `A/C/G/T/N` 串后按其反向互补匹配 `short_sequence`，含非碱基字符时结果为空）、备注、方向（正向/反向）、状态（启用/停用）。右键「查询」或点击「重置」清空全部筛选与表头条件。
- **表头筛选与排序**：名称、系列、方向、显示序列、备注、状态 6 列接入表头筛选菜单；核对序列为派生列，仅通过顶部筛选框过滤。默认按 `family, direction, name` 升序排列。

### 3.2 表格交互与单条维护

- **单元格划选复制**：基于 `useSheetRange` 支持拖拽划选单元格、`Shift` 扩选、`Ctrl+A` 全选当页、`Ctrl+C` 复制、右键取消选中；登记表头菜单的列单击打开表头菜单，长按约 0.35 秒或拖向其他列才选中整列。
- **单条新增与行操作**：点击右上角「新增」、双击任意业务单元格或点击操作列「编辑」打开弹窗（`PrimerEditorDialog.vue`），输入显示序列时实时预览核对序列；操作列另提供「停用/启用」切换与「删除」按钮。

### 3.3 批量编辑（勾选模式）

点击筛选栏齿轮展开高级操作栏（`AdvancedOpsBar`），再点「批量编辑」进入勾选模式（收起高级操作栏自动退出勾选模式并清空选择）：

- **勾选方式**：表格左侧固定勾选列，支持左键单击、按住上下拖拽连选、`Shift` 范围连选；勾选列表头下拉菜单提供「当页全选」「全部全选」（调用 `POST /catalog/ids` 拉取当前筛选条件下的全部引物 ID）和「取消选择」。
- **批量操作**（均需二次确认，单次最多 5000 条 ID）：
  - **改系列**：选择已有系列或输入新系列名（最长 32 字符），调用 `POST /catalog/batch_update`；
  - **改方向**：选择正向（`F`）或反向（`R`），调用 `POST /catalog/batch_update`；
  - **停用 / 启用**：切换 `active` 状态，调用 `POST /catalog/batch_update`；
  - **删除**：调用 `POST /catalog/batch_delete`，删除未被工单引用的记录并提示因工单引用而跳过的引物名称。

### 3.4 导入与导出

- **导出**：点击「导出」调用 `POST /catalog/export`，按当前筛选与排序导出 Excel，表头固定为：`名称`、`系列`、`方向`、`显示序列`、`核对序列`、`备注`、`状态`。
- **导入**（`PrimerImportDialog.vue`）：
  - 支持拖入或选择 `.xlsx`、`.xls`、`.csv`（导出文件可直接再次导入），读取工作簿中第一行包含必填表头（`名称`、`系列`、`方向`、`显示序列`）的工作表，单次最多 1000 条。
  - 前端逐行预检：校验名称非空与批次内不重复、系列非空且 `<= 32` 字符、方向为 `F`/`R`/`正向`/`反向`、显示序列仅含 `A/C/G/T/N`；若表头含 `核对序列` 且单元格非空，额外校验其必须等于显示序列的反向互补；`状态` 列为 `0`/`false`/`停用`/`否` 时记为停用，其余记为启用。
  - 全部行校验通过后方可点击「导入」，调用 `POST /catalog/batch_save` 按 `name` 匹配新增或更新（单事务执行，任一行校验失败整批不写入）。

## 4. 跨模块联动

- 文库构建在抽屉、Excel 视图或质控详情页首次搜索引物时，调用 `GET /api/molecular-cell/library-orders/catalog/options` 拉取全部启用（`active = true`）引物并缓存；引物库每次加载列表时调用 `clearPrimerCatalogCache()` 清空前端缓存，保证文库构建页及时获取最新字典。
- 文库工单如何绑定引物字典 ID、快照序列及核对 `.seq`/`.ab1`/`.abi` 读段（含 `i5`/`i7` 同源臂拼接与反向互补比对）见 [文库构建](./library-construction.md) §2.3。

## 5. 接口

| 方法 | 路径 | 权限 | 用途 |
|---|---|---|---|
| `GET` | `/api/molecular-cell/library-orders/catalog/options` | `molecular.page.library`、`molecular.page.library_detail` 或 `molecular.page.primer` | 搜索启用的引物/Index 字典（`query` 匹配名称包含、显示序列包含或纯 `A/C/G/T/N` 的反向互补包含；`family` 按系列过滤；`limit` 默认 100、上限 2000） |
| `POST` | `/api/molecular-cell/library-orders/catalog/list` | `molecular.page.primer` | 分页查询引物列表及系列统计（`stats.total`、`stats.families`） |
| `POST` | `/api/molecular-cell/library-orders/catalog/column_values` | `molecular.page.primer` | 获取表头筛选菜单候选值 |
| `POST` | `/api/molecular-cell/library-orders/catalog/save` | `molecular.primer.edit` | 单条新增或修改引物 |
| `POST` | `/api/molecular-cell/library-orders/catalog/ids` | `molecular.page.primer` | 按当前筛选条件返回全部匹配引物 ID（供跨页全选） |
| `POST` | `/api/molecular-cell/library-orders/catalog/batch_update` | `molecular.primer.edit` | 按勾选 ID 批量修改系列、方向或启停状态（单次最多 5000 条） |
| `POST` | `/api/molecular-cell/library-orders/catalog/batch_delete` | `molecular.primer.edit` | 按勾选 ID 批量删除引物（单次最多 5000 条，自动跳过已被文库工单使用的引物） |
| `POST` | `/api/molecular-cell/library-orders/catalog/delete` | `molecular.primer.edit` | 删除单条未被文库工单使用的引物 |
| `POST` | `/api/molecular-cell/library-orders/catalog/batch_save` | `molecular.primer.edit` | 按名称批量导入新增或更新引物（单次最多 1000 条，单事务） |
| `POST` | `/api/molecular-cell/library-orders/catalog/export` | `molecular.page.primer` | 按当前筛选与排序导出引物库 Excel |
