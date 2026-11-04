# 分子与细胞 · 文库构建
> 承接上游发现交接或手工创建的建库任务，记录各工艺关键数据、产物位置与内部胶图/引物质控。相关：[引物库](./primer-library.md) · [发现工作台](../discovery/workbench.md) · [项目工作台共用约定](../workbench.md)

## 1. 入口与权限

| 项目 | 值 |
|---|---|
| 列表路由 | `/molecular-cell/library-construction`（`LibraryConstructionList.vue`） |
| 质控详情路由 | `/molecular-cell/library-construction/result?id=`（`LibraryConstructionResult.vue`，隐藏菜单，与列表共用标签页组） |
| 一级菜单开关 | `menu.molecular_cell` |
| 列表菜单开关 | `menu.molecular_cell.library` |
| 接口前缀 | `/api/molecular-cell/library-orders` |

| 权限码 | 类型 | 允许的操作 |
|---|---|---|
| `molecular.page.library` | `page` | 访问文库构建列表；查询列表（`/list`）、表头筛选值（`/column_values`）、已录入靶点（`/recorded_targets`）、下拉枚举（`/options`）、启用引物选项（`/catalog/options`）及导出列表（`/export_list`） |
| `molecular.page.library_detail` | `page` | 访问文库质控详情页；查询工单质检文件与测序包（`/files/list`）、下载或在线预览文件（`/files/download`）、查询下拉枚举（`/options`）及启用引物选项（`/catalog/options`） |
| `molecular.library.edit` | `action` | 新建、编辑、取消、删除工单（`/save`、`/batch_save`、`/delete`），以及发现交接查询与创建（`/by-discovery`、`/handoff`） |
| `molecular.library.file.manage` | `action` | 质检文件预检与上传（`/files/preflight`、`/files/upload_batch`）、文件改名/标最终/框选区域（`/files/update`）、删除文件或测序包（`/files/delete`）；更新已有工单且仅修改质检结论四字段（`qc_result`、`qc_owner`、`qc_on`、`qc_note`）时，`/save` 与 `/batch_save` 亦接受本权限 |
| `discovery.workbench.edit` | `action` | 在发现工作台查询已交接工单并发起交接创建（`/by-discovery`、`/handoff`） |

## 2. 数据与编号

### 2.1 工单主表 `molecular_library_order`

一张工单对应一个建库批次，不设独立草稿表。

| 字段 | 含义 | 规则 |
|---|---|---|
| `id` | 主键 ID | 数据库自增主键 |
| `library_order_id` | 系统工单号 | 创建时生成，格式 `LIB-yyMMdd-XXXXXX`（6 位大写字母或数字），全局唯一，保存时只读保护 |
| `library_code` | 建库编号 | 实验员业务编号，自动转大写，最长 64 字符；非空值全局唯一，允许多个工单留空 |
| `source_discovery_id` | 来源发现 ID | 发现交接时写入 `discovery_id`，手工创建为空；保存时只读保护，非空时可在抽屉/详情点击跳回发现工作台 |
| `source_project_code`、`study_type`、`pm` | 项目快照 | 项目编号（最长 64）、课题类型（固定枚举）、PM（最长 64）；不保存来源实验号 |
| `target_name`、`target_codes` | 靶点与靶点编号 | 关联靶点库主数据，`target_codes` 为 JSON 字符串数组 |
| `mouse_strain` | 小鼠品系 | 支持多选预设品系或自填；固定选项按预设顺序排在前面，自填项接在后面，以顿号 `、` 拼接（最长 128 字符） |
| `sample_type` | 样品类型 | `nano`（`Nano`）、`lite`（`Lite`）、`rnvm_blood`（`RNVM眼眶血`）、`phage`（`噬菌体`）；`plasma_ngs` 仅允许 `nano`、`lite` 或空。修改 `mouse_strain` 且未显式提交 `sample_type` 时按首个品系自动推导（见 §6） |
| `build_type` | 建库类型 | 必填，7 种工艺枚举（见 §2.2）；仅 `待处理` 状态可修改，修改后自动清空不适用于新类型的专属字段及不匹配的 `sample_source` |
| `sample_source` | 样品来源 | 按 `build_type` 校验可选范围（见 §2.2） |
| `status`、`priority` | 状态与优先级 | 状态见 §3；优先级为 `正常`、`加急`、`非常紧急`、`吉吉国王`（新建默认 `正常`，列表默认按 `id` 倒序） |
| `owner`、`notebook_no`、`library_batch_no` | 负责人、实验记录本号、建库批号 | 最长 64 字符；`library_batch_no` 仅噬菌体展示和噬菌体 NGS 使用 |
| `received_on`、`instrument_on`、`blood_collected_on`、`started_at`、`finished_at`、`qc_on` | 实验与排程日期 | `DATE`（`YYYY-MM-DD`） |
| `positive_cell_count`、`fragment_size_bp` | 阳性细胞数、片段大小 | 自由文本（阳性细胞数最长 255 字符，片段大小 64 字符），按实验员原文保存并保留换行；抽屉与详情页并排时两框同高 |
| `plate_nos` | 板号 | JSON 字符串数组；前端单框输入，回车、中英文逗号、顿号、制表符均按分隔符解析去重 |
| `cell_type` | 细胞类型 | 最长 64 字符；`plasma_ngs` 与 `phage_display` 限定为 `全细胞`、`浆细胞`、`流穿液`（`plasma_ngs` 为空时默认写入 `浆细胞`） |
| `target_forms` | 靶点形式 | 仅 `phage_display` 使用，单选：`多穿`、`分泌`、`I型`、`II型` |
| `source_experiment_type`、`project_goal` | 实验类型、实验目标 | 仅 `phage_display` 与 `phage_ngs` 使用；实验类型单选 `抗体发现` 或 `亲和力改造`，实验目标最长 1000 字符（保留换行） |
| `immunization_stage` | 免疫阶段 | 仅 `peripheral_blood_bcr` 使用，最长 64 字符 |
| `rna_location`、`cdna_location`、`library_location` | 材料与产物位置 | 最长 255 字符（`library_location` 保留换行） |
| `cdna_concentration`、`library_concentration`、`initial_library_size`、`effective_library_size` | 浓度与库容 | 最长 64 字符，按实验员原文保存 |
| `h/k/l_forward/reverse_primer_id`、`h/k/l_forward/reverse_primer_name`、`h/k/l_primer_concentration` | H/K/L 引物与浓度 | 仅 `pooled_bcr` 使用；保存引物字典 ID、名称快照（最长 128）及浓度文本（最长 64） |
| `index_mode`、`i7_catalog_id`、`i7_name`、`i7_sequence`、`i5_catalog_id`、`i5_name`、`i5_sequence` | Barcode 方式与 i7/i5 | 仅 `pooled_barcode`、`phage_ngs`、`peripheral_blood_bcr` 使用。`index_mode` 可选 `none`（`不加 Barcode`）、`single_i7`（`i7`）、`single_i5`（`i5`）、`dual`（`双端 i7 + i5`），切换时自动清空未启用端字段；序列最长 64 字符，仅允许 IUPAC 碱基字符（`ACGTRYSWKMBDHVN`） |
| `qc_result`、`qc_owner`、`qc_on`、`qc_note` | 质控结果 | `qc_result` 可选 `待判定`、`通过`、`不通过`；前端选择非空 `qc_result` 时，若 `qc_owner`、`qc_on` 为空则自动补当前用户姓名与当天日期；`qc_note` 最长 1000 字符（保留换行） |
| `remark` | 备注 | 最长 1000 字符，保留换行 |
| `created_by`、`created_at`、`updated_at` | 审计字段 | 创建人（保存时只读保护）、创建与更新时间 |

### 2.2 建库类型与专属字段（Profile）

| `build_type` | 显示名 | 允许的 `sample_source` | 专属字段 |
|---|---|---|---|
| `plate_single_cell` | 单细胞孔板 | `beacon`（Beacon）、`dapu_plate`（达普打板）、`beacon_dapu`（Beacon+达普打板） | `instrument_on`、`positive_cell_count`、`plate_nos`、`cdna_location` |
| `pooled_bcr` | 混管 H/K/L | `dapu_tube`（达普打管） | `instrument_on`、`positive_cell_count`、`rna_location`、`cdna_location`、`library_location`、`cdna_concentration`、`library_concentration`、`fragment_size_bp`、H/K/L 正反向引物及浓度 |
| `pooled_barcode` | 混管 Barcode | `dapu_tube`（达普打管） | `instrument_on`、`positive_cell_count`、`rna_location`、`cdna_location`、`library_location`、`cdna_concentration`、`library_concentration`、`fragment_size_bp`、`index_mode` 及 i7/i5 字段 |
| `peripheral_blood_bcr` | 外周血 BCR | `retro_orbital_blood`（眼眶血）、`other_blood`（其他外周血） | `blood_collected_on`、`immunization_stage`、`positive_cell_count`、`rna_location`、`cdna_location`、`library_location`、`cdna_concentration`、`library_concentration`、`fragment_size_bp`、`index_mode` 及 i7/i5 字段 |
| `plasma_ngs` | 浆细胞 NGS | `spleen_grind`（脾脏研磨） | `instrument_on`、`positive_cell_count`、`cell_type`（默认 `浆细胞`）、`rna_location`、`cdna_location`、`library_location`、`library_concentration`、`fragment_size_bp`；`sample_type` 仅限 `nano` 或 `lite` |
| `phage_display` | 噬菌体展示 | `direct`（细胞/核酸） | `source_experiment_type`、`project_goal`、`instrument_on`、`library_batch_no`、`cell_type`、`target_forms`、`rna_location`、`cdna_location`、`library_location`、`initial_library_size`、`effective_library_size` |
| `phage_ngs` | 噬菌体 NGS | `phage_display`（噬菌体展示产物）、`phage_panning`（噬菌体筛选产物） | `source_experiment_type`、`project_goal`、`library_batch_no`、`library_location`、`library_concentration`、`fragment_size_bp`、`index_mode` 及 i7/i5 字段 |

### 2.3 引物引用与测序文件核对

引物与 Index 字典维护见 [引物库](./primer-library.md)。

- **工单关联引物**：前端首次在引物下拉框输入搜索词时，调用 `GET /api/molecular-cell/library-orders/catalog/options?limit=2000` 拉取全部启用引物并缓存，后续在页面内按名称包含、显示序列包含（纯 `A/C/G/T/N` 时同时匹配反向互补）过滤。粘贴或输入引物名称时，若与某条启用引物名称完全一致，后端自动写入对应字典 ID（i7/i5 同时带出 `short_sequence`）；不匹配字典的名称按手填文本保存并清空字典 ID。
- **需核对的工单范围**：
  - `pooled_bcr`：核对已关联字典 ID（`*_primer_id`）的 `hF`、`hR`、`kF`、`kR`、`lF`、`lR` 引物；
  - `pooled_barcode`、`phage_ngs`、`peripheral_blood_bcr`：按 `index_mode` 核对已填写序列的 `i5`（`single_i5` / `dual`）和 `i7`（`single_i7` / `dual`）；
  - 其余建库类型、`index_mode = none` 或未配置引物的方向不核对。
- **方向与链别识别**：
  - 文件名含独立标记 `M13F`（前后非字母或数字）对应正向（`i5` 或 `hF/kF/lF`），含 `M13R` 对应反向（`i7` 或 `hR/kR/lR`）；同时含 `M13F` 与 `M13R` 或均未含时不核对。
  - `pooled_bcr` 仅认建库编号开头的 `H`/`K`/`L` 链前缀（如 `HC223` 识别为建库编号 `C223`、H 链）；无链前缀的文件仅关联工单，不核对 H/K/L 引物。
- **序列拼装与比对规则**：
  - 取引物显示序列的反向互补作为核对序列 `body`。
  - 正向（`F` / `i5`）拼装期待串：`ACCGAGATCTACAC` + `body` + `ACACTCTTTCC`；反向（`R` / `i7`）拼装期待串：`GGCATACGAGAT` + `body` + `GTGACTGGAGTT`。
  - 在读段碱基中按精确子串匹配（`N` 按字面字符，不做模糊错配）：

| 状态码 | 判定条件 | 接口显示文案（`sequence_check`） |
|---|---|---|
| `matched` | 命中期待串 | `<目标> 匹配` |
| `matched_rc` | 命中期待串的反向互补 | `<目标> 匹配-反补` |
| `arm_only` | 左右同源臂按正向顺序命中，且两臂间存在与 `body` 等长但序列不同的片段 | `<目标> 引物错误` |
| `arm_only_rc` | 左右同源臂按反向互补顺序命中，且两臂间存在与 `body` 等长但序列不同的片段 | `<目标> 引物错误-反补` |
| `not_found` | 未命中期待串及上述同源臂对 | `<目标> 同源臂未匹配` |
| `trace_only` | `.ab1`/`.abi` 无法解析出判读碱基 | 无文案（不作结论） |

  - `<目标>` 在 Barcode 工单中为 `i5`、`i7`，在混管 H/K/L 工单中为 `H链正向`、`H链反向`、`K链正向`、`K链反向`、`L链正向`、`L链反向`。
  - 读段有效碱基数 `<= 400` bp 时，状态码追加 `_short` 后缀，显示文案追加 `-过短`。
  - `.ab1`/`.abi` 能读出 `PBAS2`/序列碱基时按上表生成核对文案，但**不参与**工单状态的自动质检判定（自动判定仅依据 `.seq`）。

## 3. 状态与流转

`status` 共 8 档：`待处理`（新建默认）、`建库中`、`待质检`、`质检待确认`、`质检通过`、`已完成`、`质检不通过`、`已取消`。

### 3.1 状态刷新规则（`_advance_order_status`）

工单保存、批量保存、上传/改名/切换最终标记/删除质检文件，以及打开质控详情页重核序列状态发生变化时，按以下优先级刷新状态：

1. **已取消保护**：当前为 `已取消` 时保持不变（除非当次保存显式修改 `status`）。
2. **人工质检结论优先**：
   - `qc_result = 不通过` → `质检不通过`；
   - `qc_result = 通过` → 已填 `library_location` 时为 `已完成`，未填时为 `质检通过`。
3. **手工状态与终态保护**：当次请求显式传入 `status`，或当前状态已为 `已完成`、`质检不通过` 时，不执行自动推导。
4. **实验事实自动推导**（仅统计未被同名「最终」版本替代的文件）：
   - 已有测序文件（`.ab1`/`.abi`/`.seq`），且任一已配置引物方向在 `.seq` 中出现 `not_found` / `arm_only` / `arm_only_rc`，或所有已配置方向均匹配但存在 `<= 400` bp 的 `.seq` → `质检待确认`；
   - 胶图与测序文件均存在，且每个已配置引物方向均有匹配 `.seq`、无失败或过短 `.seq`（未配置引物的工单只需胶图与测序文件齐备）→ `质检通过`；
   - 已有胶图或测序文件之一 → `待质检`；
   - 已填写 `rna_location` 或 `cdna_location` → `建库中`；
   - 以上均不满足且原状态为 `待质检`、`质检待确认`、`质检通过` → 回退为 `待处理`。

自动推导不会将状态直接改为 `质检不通过` 或仅因填写 `library_location` 改为 `已完成`。

### 3.2 开始与完成日期补填（`_stamp_work_dates`）

保存工单时：
- `started_at` 为空且 `rna_location` 或 `cdna_location` 非空 → 自动填入当天日期；
- `finished_at` 为空且 `library_location` 非空 → 自动填入当天日期；
- 已有日期保持不变，清空位置不会撤回已填日期。

## 4. 页面操作

工作台 / Excel 双视图切换、列序持久化、高级操作「显示字段」及公共表头筛选规则见 [../workbench.md](../workbench.md)。

### 4.1 列表、筛选与行操作

- **统计块**：顶部展示 8 个统计块（单细胞孔板、混管 H/K/L、混管 Barcode、外周血 BCR、浆细胞 Nano、浆细胞 Lite、噬菌体展示、噬菌体 NGS）。点击统计块切换 `build_type`（浆细胞 Nano/Lite 同时带入 `sample_type`）；统计计数不受顶部和表头的 `build_type`、`sample_type` 条件影响。
- **筛选条件**：
  - 常驻筛选：建库编号、状态、优先级、负责人、样品来源、靶点（调用 `GET /recorded_targets`）、上机日起止。
  - 高级筛选（齿轮）：项目编号、建库批号、建库类型、PM、课题类型、样品类型、小鼠品系、细胞类型、来源发现 ID、实验记录本号、备注、开始日起止、完成日起止。
  - 建库编号、项目编号、建库批号、来源发现 ID 填单个值时按包含匹配，用逗号、顿号、空格、制表符或换行分隔多个值时按精确值匹配（单次最多 500 个）。
  - 表头筛选覆盖除 `target_codes`（靶点编号）和 `actions`（操作）外的全部列；`plate_nos` 按 JSON 数组包含匹配。
  - 右键「查询」清空全部筛选与表头条件。筛选条件、排序与页码保存在浏览器存储中，从质控详情页返回时恢复。
- **行内编辑与抽屉**：工作台视图默认展示项目编号、靶点、建库类型、样品来源、样品类型、建库编号、负责人、状态、优先级、操作；行内可直接修改 `priority`、`status`、`received_on`。左键点行打开右侧无遮罩抽屉（支持「上一条 / 下一条」切换，字段修改后自动保存）。
- **操作列（`LibraryRowActions.vue`）**：行操作列与抽屉顶部工具栏固定三个按钮：

| 按钮 | 权限 | 行为 |
|---|---|---|
| **质检** | `molecular.page.library_detail` | 跳转 `/molecular-cell/library-construction/result?id=<id>` |
| **交接** | `molecular.library.edit` | 提示「下游测序模块尚未开放」 |
| **删除** | `molecular.library.edit` | 二次确认后调用 `POST /delete`，删除工单并清理无其他工单引用的独占质检文件与测序包 |

### 4.2 新建、Excel 批量编辑与导出

- **新建工单**：点击「新建」弹窗按达普、Beacon、噬菌体、NGS 四行选择工艺（自动写入 `build_type`、`sample_source` 及浆细胞 `sample_type`）。工作台视图创建后打开该行抽屉；Excel 视图创建后刷新到第 1 页，不打开抽屉。
- **Excel 视图与批量粘贴**：
  - 未限定 `build_type` 时展示全部 56 个业务列，每行不适用于自身 `build_type` 或 `index_mode` 的单元格锁定只读；选中单一建库类型后仅展示公共列与该类型适用列。
  - 列表导出的表头与 Excel 视图列名完全一致。粘贴内容带「系统工单号」表头时按单号匹配当前页工单（含不存在或重复单号则整批拒绝）；不带该表头时从当前选中单元格起粘贴。只读或不适用单元格若粘贴值与现值相同则忽略，不同则整批拒绝。校验通过后调用 `POST /batch_save` 单事务保存（单次最多 500 条）。
- **建库编号拖拽填充**：Excel 视图下选中单个 `library_code` 单元格，上下拖动右下角填充柄，按种子编号末尾数字等宽递增填充（如 `C098` → `C099`、`C100`）；若目标行已有编号则先弹窗确认覆盖，确认后调用 `POST /batch_save` 整批保存。

### 4.3 批量质检上传（`LibraryResultUploadDialog.vue`）

高级操作栏点击「批量质检上传」（需 `molecular.library.file.manage`）：
1. 支持拖入文件、文件夹、`.zip` 压缩包，或左键选文件、右键选文件夹；`.zip` 在前端自动展开。
2. 选入后先调用无状态预检接口 `POST /files/preflight`（仅传相对路径列表，不上传文件内容），按拆包与编号规则返回可接收文件下标（`accepted_indexes`）及各组匹配摘要。
3. 点击「上传」仅提交通过预检的文件至 `POST /files/upload_batch`（不传 `order_id`），后端落盘并跨工单关联后返回各工单最新质检状态，点击工单建库编号可新标签页打开对应质控详情页。

### 4.4 质控详情页（`LibraryConstructionResult.vue`）

- **页头**：展示系统工单号、建库类型与靶点、状态与优先级点选器（需 `molecular.library.edit`）、建库编号/负责人/起止日期，以及缺项告警胶囊（`同源臂未匹配`、`引物错误`、`读段过短`、`引物未齐`、`缺测序`、`缺胶图`、`缺 RNA`、`缺 cDNA`）。
- **左侧文件轨**：顶部上传块支持拖入或选择文件/文件夹/`.zip`（附带当前 `order_id` 调用 `POST /files/upload_batch`）。下方依次展示：胶图、成对排序的测序文件（同包或同为散件的同名 `.ab1`/`.abi` 与 `.seq` 按上传先后两两配对）、其他单文件、测序包文件夹。同类文件内标「最终」的排在前面；同名文件已有「最终」版本时，其余同名文件变淡显示且不参与质检。
- **中间预览台**：
  - **胶图查看器**：支持滚轮缩放（20%–800%）、左键平移、左右旋转 90°、适应/填充窗口、全屏、亮度/对比度调节（20%–320%）、反相、增强（亮度 190%、对比度 150%）、复位，以及 `Shift + 左键` 框选质检区域（单文件最多 20 个选区，支持点击标签改名，最长 24 字符）。
  - **测序包双栏浏览器**：左侧按包内相对路径逐级浏览目录，右侧预览选中文件并标注「已关联」或「仅保存」。
  - **序列与峰图预览（`SeqReadPreview.vue`、`AbiTracePreview.vue`）**：显示读段方向胶囊（`正向/反向 · i5 端/i7 端`，`i5` 端直接命中为正向、反补命中为反向，`i7` 端相反）与碱基数（`<= 400 bp` 标红）。打开时按核对结果自动填入搜索串并高亮定位（完全匹配填整段期待串，`arm_only` 填 `左臂......右臂`，反补命中自动开启「反补」状态按钮）；点击方向胶囊循环切换「完整引物 → 两侧同源臂 → 左臂 → 右臂」，搜索框用 `.` 或 `。` 分隔两段时按成对区间查找。峰图无自身核对结果时沿用同包同名 `.seq` 的核对状态。
  - **通用预览（`FilePreviewer.vue`）**：支持图片、文本（`.seq`/`.txt`/`.fa`/`.fasta`/`.md`/`.log`）、表格（`.xls`/`.xlsx`/`.csv`）、`.pdf`、`.docx`、视频（`.mp4`/`.webm`/`.ogg`/`.ogv`/`.mov`）在线预览，其余格式下载查看。
- **右侧工单检查器**：分「质检判读」「样品信息」「建库记录」三个标签页；修改 `qc_result`、`qc_owner`、`qc_on`、`qc_note` 需 `molecular.library.edit` 或 `molecular.library.file.manage`，修改其余字段需 `molecular.library.edit`。

## 5. 文件与存储

### 5.1 存储表与物理路径

物理文件保存在 `{REPOSITORY_ROOT}/uploads/` 下。上传时先写入 `library_results/.tmp/` 临时文件并执行 DRM 解密（若启用），再按实际落盘内容计算 `byte_size` 与 `sha256`。

| 表 / 对象 | 唯一约束与外键 | 物理路径（相对 `uploads/`） | 说明 |
|---|---|---|---|
| `molecular_library_result_package` | `signature` 唯一；`owner_order_id` 外键关联 `molecular_library_order.id` | `library_results/sequencing/{YYYY}/{MM}/{包名}--{signature前8位}/` | 测序结果归档包；记录 `original_name`、`signature`、`storage_prefix`、`owner_order_id` |
| `molecular_library_result_file`（包内文件） | `package_id` 外键关联 `molecular_library_result_package.id` | `library_results/sequencing/{YYYY}/{MM}/{包名}--{signature前8位}/{包内相对路径}` | 保留包内原始目录结构，不跨包去重 |
| `molecular_library_result_file`（包外胶图） | `dedupe_key`（`gel:<sha256>`）唯一 | `library_results/gels/{YYYY}/{MM}/{sha256}{ext}` | 包外图片（`.jpg`/`.jpeg`/`.png`/`.bmp`/`.webp`/`.gif`）按内容哈希去重复用 |
| `molecular_library_result_file`（包外其他单文件） | 无 `package_id`、无 `dedupe_key` | `library_results/others/{YYYY}/{library_order_id}/{文件名}` | 包外 `.ab1`/`.abi`/`.seq` 及质检页上传的其他单文件 |
| `molecular_library_result_link` | `(file_id, order_id)` 唯一；外键关联文件与工单 | 引用 `molecular_library_result_file.storage_path` | 工单级文件视图：存 `original_name`、`is_final_qc`、`qc_regions`、`sequence_status`、`sequence_target` |

- **大小与数量限制**：单文件不超过 `50MB`（`MAX_FILE_BYTES`），单次上传最多 `990` 个文件（`MAX_UPLOAD_FILES`，留余量给框架“一次请求最多 1000 个文件 / 1000 个字段”的默认上限）且总大小不超过 `500MB`（`MAX_BATCH_BYTES`）。
- **文件类型推导（`result_kind`）**：按 `original_name` 扩展名实时计算——图片为 `胶图`；`.ab1`/`.abi`/`.seq`/`.clc`/`.fasta`/`.fa` 为 `引物质检文件`；`.xlsx`/`.xls`/`.csv`/`.ppt`/`.pptx` 为 `PCR检测报告`；其余为 `其他`。

### 5.2 拆包、匹配与删除规则

- **目录拆包与 `.zip` 展开**：路径中含 `测序结果`、`测序合格结果`、`完成` 标记目录时，以其上一层目录为一包（标记目录在最外层时以自身为一包）；无标记目录时，每个顶层文件夹为一包；无文件夹层级的文件为零散文件。`.zip` 在前端解压（过滤 `__MACOSX`、`.DS_Store`、`Thumbs.db`），若无唯一顶层目录或唯一顶层目录即标记目录，自动补一层压缩包名目录后按同一规则拆包。
- **包指纹与只增不改**：`signature` 由首次建包时的规范化包名与排序后的 `(包内相对路径, sha256, byte_size)` 生成。同名文件夹重传时，若原包全部文件在本次上传中路径与 `sha256` 均一致，则沿用原包（不改 `signature`）并仅追加新文件；若原包任一文件缺失或内容变化，则另存新包。
- **建库编号识别与关联**：
  - **测序文件（`.ab1`/`.abi`/`.seq`）**：包内 `拼接结果`、`去载体序列` 子目录中的文件仅归档，不参与匹配；其余测序文件去掉开头可选链字母 `H`/`K`/`L` 后，按工单已填 `library_code` 做最长前缀匹配（编号后须为结尾或分隔符 `-_()（）. `），唯一匹配工单时建立 `molecular_library_result_link` 并执行引物核对。
  - **包外胶图**：识别文件名中所有形如 `[HKL]?[NLCX]\d+`（前无紧邻字母/数字）的建库编号（去掉链前缀），可同时关联多个唯一匹配的工单；包内图片仅作为随包文件保存，不识别为胶图。
  - **入口差异**：列表批量上传的测序包可跨工单关联，无任何文件唯一匹配工单的包或零散非图片/非测序文件直接跳过；质检页上传的测序包在 `owner_order_id` 为空时认领归属当前工单，且仅关联属于当前工单的测序文件（若包已归属其他工单且无文件匹配当前工单则拒绝）；质检页上传的零散文件仅挂当前工单（明确含其他工单编号时拒绝，无建库编号的普通文件保留在当前工单）。
- **最终标记与删除**：
  - 同一工单内同名文件（忽略大小写）最多一份 `is_final_qc = true`，设置新最终文件时自动取消同名其余文件的最终标记。
  - 删除工单文件关联（传 `link_id`）：仅解除当前工单关联；包内文件仍留在包中，包外文件在无其他工单引用时同步删除物理记录与磁盘文件。
  - 测序包预览内删除文件（传 `file_id` + `order_id`）：解除该文件与所有工单的关联，并删除物理记录与磁盘文件。
  - 移除测序包（传 `package_id` + `order_id`）：解除当前工单对该包内文件的关联及 `owner_order_id` 归属；当该包无任何工单关联且 `owner_order_id` 为空时，删除包记录、包内文件记录及磁盘目录。

## 6. 跨模块联动

发现工作台行操作「交接」（`LibraryHandoffDialog.vue`）调用 `GET /by-discovery` 与 `POST /handoff` 批量创建建库工单（`已完成`、`已取消` 的发现安排不可交接）：

- **工艺矩阵与预选**：
  - `达普` 行：单细胞孔板（`dapu_plate`）、混管 H/K/L（`dapu_tube`）、混管 Barcode（`dapu_tube`）；
  - `Beacon` 行：单细胞孔板（`beacon`）、Beacon+达普打板（`beacon_dapu`，与两侧单独的单细胞孔板互斥）；
  - `噬菌体` 行：噬菌体展示（`direct`）、噬菌体测序（`phage_ngs`，默认 `phage_panning`）；
  - `NGS` 行：眼眶血（`retro_orbital_blood`）、其他外周血（`other_blood`）、浆细胞 Nano（`plasma_ngs` + `spleen_grind` + `nano`）、浆细胞 Lite（`plasma_ngs` + `spleen_grind` + `lite`）。
  - 发现安排已填 `screening_methods` 时仅开放对应行（`Beacon+达普打板` 需同时标 `达普` 与 `Beacon`），未填时四行均可选。当对应 `build_type` 尚无非取消工单时：同时含 `Beacon` 与 `达普` 预选 `Beacon+达普打板`，仅含 `Beacon` 预选 `Beacon` 单细胞孔板，含 `噬菌体` 预选 `噬菌体展示`，其余不预选。
- **字段携带与品系推导样品类型**：
  - 新工单写入 `source_discovery_id = discovery_id`，并携带发现安排的 `project_code → source_project_code`、`study_type`、`target_name`、`target_codes`、`pm`、`mouse_strain`、`priority`；不复制发现台负责人和归类鼠型。
  - **首个品系推导 `sample_type`**（交接与工单编辑共用）：`mouse_strain` 按预设品系在前、自填在后以顿号拼接；未显式指定 `sample_type` 时，仅根据拼接后的**第一个**品系推导：
    - `RL`、`RLB/C`、`RLSJL`、`RLKO`、`RLCKO`、`RLDF` → `lite`（`Lite`）；
    - `RN`、`RNKO`、`RNVR`、`RNVM`、`RNVMKO` → `nano`（`Nano`）；
    - 其余品系（如 `RM`、`RMB/C`、`RMSJL`、`RMKO`、`RMCKO` 及自填项）不自动推导或覆盖已有 `sample_type`。手动修改 `sample_type` 不会反向改动 `mouse_strain`。
  - **上机日期与细胞数**：`plate_single_cell`、`pooled_bcr`、`pooled_barcode`、`phage_display` 四类交接时必须先在发现台填写 `harvest_date`（剖鼠日期），交接后写入 `instrument_on`；`plasma_ngs` 有 `harvest_date` 时亦写入 `instrument_on`，无日期不阻断交接。`plate_single_cell`、`pooled_bcr`、`pooled_barcode`、`plasma_ngs`、`peripheral_blood_bcr` 自动复制 `positive_cell_count`。
- **发现状态推进与删除保护**：
  - 交接创建包含 `phage_display` 且发现安排处于 `规划中`、`待冲击`、`待剖鼠`、`待建库` 时，发现状态推进为 `待噬菌体`；否则若处于 `规划中`、`待冲击`、`待剖鼠`，推进为 `待建库`。文库构建完成不会自动将发现安排推进为 `待测序`。
  - 只要 `molecular_library_order` 中存在 `source_discovery_id = discovery_id` 的工单（含 `已取消`），发现工作台即禁止删除该发现安排，需先删除关联的建库工单。

## 7. 接口

引物库 `/api/molecular-cell/library-orders/catalog/*` 接口见 [引物库](./primer-library.md)。

| 方法 | 路径 | 权限 | 用途 |
|---|---|---|---|
| `GET` | `/api/molecular-cell/library-orders/options` | `molecular.page.library` 或 `molecular.page.library_detail` | 获取状态、优先级、质检结论、细胞类型、小鼠品系及本表已有人员选项 |
| `GET` | `/api/molecular-cell/library-orders/recorded_targets` | `molecular.page.library` | 远程搜索本表已录入靶点（`keyword`、`limit` 默认 50、上限 200） |
| `POST` | `/api/molecular-cell/library-orders/list` | `molecular.page.library` | 分页查询工单列表与建库类型统计（`stats`） |
| `POST` | `/api/molecular-cell/library-orders/column_values` | `molecular.page.library` | 获取表头筛选菜单候选值 |
| `GET` | `/api/molecular-cell/library-orders/by-discovery` | `discovery.workbench.edit` 或 `molecular.library.edit` | 按 `discovery_workbench_id` 或 `discovery_id` 查询发现交接预览、已有建库工单及预选建议 |
| `POST` | `/api/molecular-cell/library-orders/save` | `molecular.library.edit`（有 `id` 且仅改 `qc_result`、`qc_owner`、`qc_on`、`qc_note` 时也接受 `molecular.library.file.manage`） | 单条新建或更新工单（取消工单亦通过本接口更新 `status`） |
| `POST` | `/api/molecular-cell/library-orders/batch_save` | `molecular.library.edit`（每条均仅改上述 4 个质检字段时也接受 `molecular.library.file.manage`） | 批量事务更新已有工单（单次最多 500 条，任一条失败整批回滚） |
| `POST` | `/api/molecular-cell/library-orders/export_list` | `molecular.page.library` | 按当前筛选与排序导出工单 Excel |
| `POST` | `/api/molecular-cell/library-orders/handoff` | `discovery.workbench.edit` 或 `molecular.library.edit` | 从发现工作台交接批量创建建库工单并更新发现状态 |
| `POST` | `/api/molecular-cell/library-orders/delete` | `molecular.library.edit` | 删除工单并清理无其他工单引用的独占质检文件与测序包 |
| `POST` | `/api/molecular-cell/library-orders/files/list` | `molecular.page.library_detail` | 查询指定 `order_id` 的工单信息、已配置引物序列、质检文件及测序包（打开时自动按最新规则重核序列） |
| `POST` | `/api/molecular-cell/library-orders/files/upload_batch` | `molecular.library.file.manage` | 批量上传文件或测序包（`order_id` 可选：传则挂当前工单，不传则按预检跨工单关联） |
| `POST` | `/api/molecular-cell/library-orders/files/preflight` | `molecular.library.file.manage` | 列表批量上传前的无状态路径与建库编号预检 |
| `POST` | `/api/molecular-cell/library-orders/files/delete` | `molecular.library.file.manage` | 删除工单文件关联（`link_id`）、测序包内物理文件（`file_id` + `order_id`）或移除测序包（`package_id` + `order_id`） |
| `POST` | `/api/molecular-cell/library-orders/files/update` | `molecular.library.file.manage` | 更新工单文件显示名（`original_name`，保持扩展名）、最终质检标记（`is_final_qc`）或胶图框选区域（`qc_regions`） |
| `GET` | `/api/molecular-cell/library-orders/files/download` | `molecular.page.library_detail` | 按 `id`（关联 ID）或 `file_id`（包内物理文件 ID）下载文件、获取图片缩略图（`thumb=true`）、在线预览（`preview=true`）或解析 ABI/AB1 峰图 JSON |
