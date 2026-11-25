-- Antibody Forge / Vita 主库：全表 DDL + 示例角色
-- 在 DATABASE_URL 空库执行本文件即可。
--
-- 说明：
--   - 改表或增删改数据行前，先列出对象、操作、目的和影响，确认后再实施。
--   - 本文件只维护**当前全量 DDL + 种子**（空库执行一次）；修改已有表时直接改对应 CREATE TABLE 定义，不追加 ALTER / 升级脚本，也不标注本次新增。
--   - 表、字段 COMMENT 须齐全且简练，只说明业务含义，不在括号中列举可能值。
--   - 新模块尽量少改数据库；新增表和字段必须有长期业务意义，不建临时占位。
--   - 权限点、接口审计、功能开关默认值都在代码里声明（各模块 permissions.py，modules/registry.py 汇总），不建表、不写种子；
--     sys_feature_flag 只保存管理员改过的开关，sys_permission_bundle_item / sys_user_permission_override 只保存授权关系。
--   - 文末「权限包 / 角色」仅为空库示例，覆盖血清、镁伽与系统管理。其余模块不写入 guest/operator，也不改现网角色/权限包。
--   - 外部细胞库 sam_sample 见文末注释（CELL_DB_URL，models/cell_inventory.py），勿在主库执行。
--   - 外部员工库 org_emp / org_depart 见文末注释（EMPLOYEE_DB_URL，modules/system/employee_sync.py），勿在主库执行。
--
-- 文档：docs/README.md、docs/auth-permissions.md

CREATE TABLE IF NOT EXISTS sys_user (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
  username VARCHAR(64) NOT NULL COMMENT '账号',
  display_name VARCHAR(128) NULL COMMENT '姓名',
  password_hash VARCHAR(255) NULL COMMENT '密码哈希',
  openid VARCHAR(100) NULL COMMENT '云之家OpenID',
  job_no VARCHAR(32) NULL COMMENT '工号',
  department VARCHAR(128) NULL COMMENT '部门',
  group_name VARCHAR(128) NULL COMMENT '组别',
  position_title VARCHAR(128) NULL COMMENT '职位',
  gender VARCHAR(16) NULL COMMENT '性别',
  profile_signature VARCHAR(255) NULL COMMENT '个性名片语句',
  employment_status VARCHAR(32) NOT NULL DEFAULT 'active' COMMENT '在职状态',
  email VARCHAR(128) NULL COMMENT '邮箱',
  mobile VARCHAR(32) NULL COMMENT '手机号',
  status VARCHAR(16) NOT NULL DEFAULT 'active' COMMENT '用户状态',
  is_superuser BOOLEAN NOT NULL DEFAULT FALSE COMMENT '是否超级管理员',
  last_login_at DATETIME NULL COMMENT '最后登录时间',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  UNIQUE KEY uk_sys_user_username (username),
  UNIQUE KEY uk_sys_user_openid (openid)
) COMMENT='系统用户表';

CREATE TABLE IF NOT EXISTS sys_role (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
  code VARCHAR(64) NOT NULL COMMENT '角色编码',
  name VARCHAR(128) NOT NULL COMMENT '角色名称',
  description VARCHAR(255) NULL COMMENT '角色描述',
  status VARCHAR(16) NOT NULL DEFAULT 'active' COMMENT '角色状态',
  sort_order INT NOT NULL DEFAULT 0 COMMENT '排序值',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  UNIQUE KEY uk_sys_role_code (code)
) COMMENT='系统角色表';

CREATE TABLE IF NOT EXISTS sys_permission_bundle (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
  code VARCHAR(64) NOT NULL COMMENT '权限包编码',
  name VARCHAR(128) NOT NULL COMMENT '权限包名称',
  module VARCHAR(64) NOT NULL COMMENT '所属模块',
  description VARCHAR(255) NULL COMMENT '权限包描述',
  status VARCHAR(16) NOT NULL DEFAULT 'active' COMMENT '权限包状态',
  sort_order INT NOT NULL DEFAULT 0 COMMENT '排序值',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  UNIQUE KEY uk_sys_permission_bundle_code (code)
) COMMENT='权限包表';

CREATE TABLE IF NOT EXISTS sys_permission_bundle_item (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
  bundle_code VARCHAR(64) NOT NULL COMMENT '权限包编码',
  permission_code VARCHAR(128) NOT NULL COMMENT '权限编码',
  UNIQUE KEY uq_sys_permission_bundle_item (bundle_code, permission_code)
) COMMENT='权限包权限点关系表';

CREATE TABLE IF NOT EXISTS sys_user_role (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
  user_id BIGINT NOT NULL COMMENT '用户ID',
  role_id BIGINT NOT NULL COMMENT '角色ID',
  UNIQUE KEY uq_sys_user_role (user_id, role_id)
) COMMENT='用户角色关系表';

CREATE TABLE IF NOT EXISTS sys_role_permission_bundle (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
  role_id BIGINT NOT NULL COMMENT '角色ID',
  bundle_code VARCHAR(64) NOT NULL COMMENT '权限包编码',
  UNIQUE KEY uq_sys_role_permission_bundle (role_id, bundle_code)
) COMMENT='角色权限包关系表';

CREATE TABLE IF NOT EXISTS sys_user_permission_override (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
  user_id BIGINT NOT NULL COMMENT '用户ID',
  permission_code VARCHAR(128) NOT NULL COMMENT '权限编码',
  effect VARCHAR(8) NOT NULL COMMENT '覆盖效果',
  reason VARCHAR(255) NULL COMMENT '覆盖原因',
  UNIQUE KEY uq_sys_user_permission_override (user_id, permission_code)
) COMMENT='用户权限覆盖表';

CREATE TABLE IF NOT EXISTS sys_operation_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
  request_id VARCHAR(64) NULL COMMENT '请求或任务追踪ID',
  user_id BIGINT NULL COMMENT '操作用户ID',
  username VARCHAR(64) NULL COMMENT '操作账号',
  operator_name VARCHAR(128) NULL COMMENT '操作人姓名',
  source VARCHAR(16) NOT NULL DEFAULT 'user' COMMENT '操作来源',
  ip_address VARCHAR(64) NULL COMMENT '来源IP',
  action VARCHAR(128) NOT NULL COMMENT '操作动作',
  operation_name VARCHAR(128) NULL COMMENT '操作名称',
  operation_type VARCHAR(32) NULL COMMENT '操作类型',
  target_type VARCHAR(64) NULL COMMENT '目标类型',
  target_id VARCHAR(128) NULL COMMENT '目标ID',
  target_label VARCHAR(255) NULL COMMENT '目标名称',
  result VARCHAR(16) NOT NULL DEFAULT 'success' COMMENT '操作结果',
  affected_count INT NOT NULL DEFAULT 0 COMMENT '受影响实体数量',
  detail JSON NULL COMMENT '操作详情',
  error_message TEXT NULL COMMENT '错误信息',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
  KEY idx_sys_operation_log_created_at (created_at),
  KEY idx_sys_operation_log_request (request_id),
  KEY idx_sys_operation_log_result_time (result, created_at)
) COMMENT='系统操作日志表';

CREATE TABLE IF NOT EXISTS sys_operation_log_item (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
  log_id BIGINT NOT NULL COMMENT '操作日志ID',
  entity_type VARCHAR(128) NOT NULL COMMENT '实体类型',
  table_name VARCHAR(128) NOT NULL COMMENT '数据表名',
  entity_id VARCHAR(128) NULL COMMENT '实体主键',
  entity_label VARCHAR(255) NULL COMMENT '实体业务标识',
  change_type VARCHAR(16) NOT NULL COMMENT '变更类型',
  change_count INT NOT NULL DEFAULT 0 COMMENT '变更字段数量',
  changes JSON NULL COMMENT '字段前后值差异',
  CONSTRAINT fk_sys_operation_log_item_log
    FOREIGN KEY (log_id) REFERENCES sys_operation_log(id) ON DELETE CASCADE,
  KEY idx_sys_operation_log_item_log (log_id)
) COMMENT='操作日志实体变更明细';

CREATE TABLE IF NOT EXISTS sys_feature_flag (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
  code VARCHAR(128) NOT NULL COMMENT '功能编码',
  enabled TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
  visible TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否显示',
  sort_order INT NULL COMMENT '排序值；空则用模块登记的排序',
  config JSON NULL COMMENT '扩展配置',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  UNIQUE KEY uk_sys_feature_flag_code (code)
) COMMENT='功能配置覆盖表';

CREATE TABLE IF NOT EXISTS sys_job_run_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
  job_code VARCHAR(128) NOT NULL COMMENT '任务编码',
  job_name VARCHAR(128) NOT NULL COMMENT '任务名称',
  started_at DATETIME NULL COMMENT '开始时间',
  finished_at DATETIME NULL COMMENT '结束时间',
  duration_ms INT NULL COMMENT '耗时毫秒',
  result VARCHAR(16) NOT NULL DEFAULT 'success' COMMENT '执行结果',
  summary VARCHAR(255) NULL COMMENT '结果摘要',
  detail JSON NULL COMMENT '执行详情',
  error_message TEXT NULL COMMENT '错误信息',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) COMMENT='定时任务运行日志表';

-- ---------------------------------------------------------------------------
-- 工单数据回传（models/order_sync.py）
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS order_sync (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
  trace_id VARCHAR(128) NOT NULL COMMENT '追踪ID',
  file_path VARCHAR(1024) NOT NULL COMMENT '原始JSON路径',
  order_count INT NOT NULL DEFAULT 0 COMMENT '订单数',
  order_nos JSON NULL COMMENT '订单号',
  project_count INT NOT NULL DEFAULT 0 COMMENT '项目数',
  project_infos JSON NULL COMMENT '项目摘要',
  status VARCHAR(64) NOT NULL COMMENT '核对结论',
  error_message TEXT NULL COMMENT '错误信息',
  http_status INT NULL COMMENT '回复HTTP状态',
  response_body JSON NULL COMMENT '回复内容',
  import_status VARCHAR(32) NULL COMMENT '导入进度',
  processed_at DATETIME NULL COMMENT '最近处理时间',
  received_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '接收时间',
  UNIQUE KEY uk_order_sync_trace_id (trace_id)
) COMMENT='工单实验结果回传记录';

CREATE TABLE IF NOT EXISTS order_sync_board (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
  sync_id BIGINT NOT NULL COMMENT '回传记录ID',
  seq INT NOT NULL COMMENT '回传内顺序',
  order_no VARCHAR(255) NOT NULL COMMENT '订单号',
  data_type VARCHAR(32) NULL COMMENT '检测类型',
  work_order_id BIGINT NULL COMMENT '流式工单ID',
  dispatch_id VARCHAR(64) NULL COMMENT '下发编号',
  detect_barcode VARCHAR(128) NULL COMMENT '检测板条码（回传 barcode）',
  sample_barcode VARCHAR(128) NULL COMMENT '样本板条码（回传 sample_code）',
  cell_name VARCHAR(255) NULL COMMENT '细胞',
  experiment_date VARCHAR(32) NULL COMMENT '实验日期',
  image_path VARCHAR(1024) NULL COMMENT '可视化图路径',
  csv_path VARCHAR(1024) NULL COMMENT '热图路径',
  verify_status VARCHAR(32) NOT NULL COMMENT '核对结果',
  verify_message TEXT NULL COMMENT '核对说明',
  import_status VARCHAR(32) NOT NULL COMMENT '导入结果',
  import_message TEXT NULL COMMENT '导入说明',
  experiment_id VARCHAR(64) NULL COMMENT '效价实验编号',
  facs_plate_id BIGINT NULL COMMENT 'FACS板卡ID',
  image_file_id BIGINT NULL COMMENT '可视化图文件ID',
  excel_file_id BIGINT NULL COMMENT '热图文件ID',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  KEY idx_order_sync_board_sync (sync_id),
  KEY idx_order_sync_board_work_order (work_order_id)
) COMMENT='工单回传检测板，一块检测板一行';

-- ---------------------------------------------------------------------------
-- 上清板布局接收（models/supernatant.py）
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS synthesis_supernatant_well (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
  order_no VARCHAR(64) NOT NULL COMMENT '合成订单号',
  corp_name VARCHAR(64) NOT NULL COMMENT '合成公司',
  plate_no VARCHAR(128) NULL COMMENT '板号，未合成时为空',
  well_no VARCHAR(8) NULL COMMENT '孔号，未合成时为空',
  sample_name VARCHAR(128) NOT NULL COMMENT '蛋白名称',
  not_synthesized TINYINT(1) NOT NULL DEFAULT 0 COMMENT '未合成',
  potency DECIMAL(16,4) NULL COMMENT '浓度(ug/mL)，空表示不适用',
  specs DECIMAL(16,4) NULL COMMENT '规格(mL/支)，空表示不适用',
  volume DECIMAL(16,4) NULL COMMENT '体积(mL)，未合成时为空',
  sample_enter_vol DECIMAL(16,4) NULL COMMENT '质粒量(ug)，未合成时为空',
  received_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '接收时间',
  UNIQUE KEY uk_synthesis_supernatant_well_order_plate_well (order_no, plate_no, well_no),
  KEY idx_synthesis_supernatant_well_sample_name (sample_name)
) COMMENT='合成公司推送的上清板布局，一孔一行；未合成的样品一样品一行，不占孔位';

-- ---------------------------------------------------------------------------
-- 靶点主数据（models/target.py；外部平台只读同步镜像）
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS target (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  external_id BIGINT NOT NULL COMMENT '外部平台靶点ID',
  snum VARCHAR(100) NOT NULL COMMENT '靶点编号',
  name VARCHAR(100) NOT NULL COMMENT '靶点名称',
  type INT NULL COMMENT '靶点来源',
  status INT NULL COMMENT '开发状态',
  category VARCHAR(200) NULL COMMENT '靶点分类',
  ko_lethal_info INT NULL COMMENT 'KO致死情况',
  ko_lethal_info_desc VARCHAR(1000) NULL COMMENT 'KO致死信息备注',
  structural_properties VARCHAR(200) NULL COMMENT '结构特性类别',
  structure_feature VARCHAR(100) NULL COMMENT '跨膜次数',
  shape_remark VARCHAR(200) NULL COMMENT '形式备注',
  structure_feature_remark VARCHAR(1000) NULL COMMENT '结构特性备注',
  ko_mgi TEXT NULL COMMENT 'KO鼠表型MGI',
  ko_impc VARCHAR(100) NULL COMMENT 'KO鼠表型IMPC',
  effect_cell VARCHAR(1000) NULL COMMENT '靶点作用细胞',
  ko_gt VARCHAR(100) NULL COMMENT 'KO鼠表型GT',
  official_full_name VARCHAR(300) NULL COMMENT '官方全名',
  human_gene_official_name VARCHAR(200) NULL COMMENT '人基因官方名称',
  human_gene_alias_name VARCHAR(500) NULL COMMENT '人基因别名',
  human_ncbi_gene_id VARCHAR(200) NULL COMMENT '人NCBI Gene ID',
  human_chromosome_position VARCHAR(200) NULL COMMENT '人染色体位置',
  is_homologous_gene BOOLEAN NULL COMMENT '是否有同源基因',
  mouse_gene_official_name VARCHAR(200) NULL COMMENT '小鼠基因官方名称',
  mouse_gene_alias_name VARCHAR(255) NULL COMMENT '小鼠基因别名',
  mouse_ncbi_gene_id VARCHAR(200) NULL COMMENT '小鼠NCBI Gene ID',
  mouse_chromosome_position VARCHAR(200) NULL COMMENT '小鼠染色体位置',
  human_mouse_homology VARCHAR(200) NULL COMMENT '人鼠同源性',
  human_dog_homology VARCHAR(200) NULL COMMENT '人犬同源性',
  human_cat_homology VARCHAR(200) NULL COMMENT '人猫同源性',
  human_monkey_homology VARCHAR(200) NULL COMMENT '人猴同源性',
  human_mouse_homology_expect_functional_domain VARCHAR(200) NULL COMMENT '预期主要功能结构域人鼠同源性',
  gene_functional_desc TEXT NULL COMMENT '基因功能描述',
  is_ko_affect_humoral_immunity BOOLEAN NULL COMMENT 'KO是否影响体液免疫',
  is_ko_affect_humoral_immunity_desc VARCHAR(500) NULL COMMENT 'KO是否影响体液免疫备注',
  is_human_mouse_cross VARCHAR(1000) NULL COMMENT '配体或受体是否人鼠交叉',
  treatment_field VARCHAR(500) NULL COMMENT '治疗领域',
  indication VARCHAR(200) NULL COMMENT '适应症',
  gene_family VARCHAR(200) NULL COMMENT '基因家族',
  signal_path VARCHAR(1000) NULL COMMENT '信号通路',
  remark VARCHAR(2000) NULL COMMENT '备注',
  is_active BOOLEAN NOT NULL DEFAULT TRUE COMMENT '数据是否有效',
  synced_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最近变更时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_target_external_id (external_id),
  UNIQUE KEY uk_target_snum (snum)
) COMMENT='靶点同步表';

-- ---------------------------------------------------------------------------
-- 镁伽自动化 / 流式工单（models/mega_automation.py）
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS mega_flow_work_order (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  orderName VARCHAR(255) NULL COMMENT '订单名称',
  orderNum VARCHAR(255) NOT NULL COMMENT '订单编号',
  orderType VARCHAR(32) NOT NULL DEFAULT 'TITER' COMMENT '检测类型',
  source_id VARCHAR(128) NULL COMMENT '来源业务主键',
  priority VARCHAR(32) NOT NULL DEFAULT 'normal' COMMENT '优先级',
  remark TEXT NULL COMMENT '备注',
  status VARCHAR(64) NOT NULL DEFAULT 'draft' COMMENT '执行状态',
  created_by VARCHAR(128) NULL COMMENT '创建人',
  sent_at DATETIME NULL COMMENT '发送时间',
  project_nos JSON NULL COMMENT '项目号列表',
  targets JSON NULL COMMENT '靶点列表',
  sample_plate_barcodes JSON NULL COMMENT '样本板条码列表',
  cell_plate_barcodes JSON NULL COMMENT '细胞板条码列表',
  content JSON NULL COMMENT '工单编辑内容',
  content_hash CHAR(64) NULL COMMENT '工单内容哈希',
  error_message TEXT NULL COMMENT '错误信息',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  KEY idx_mega_flow_work_order_source (orderType, source_id),
  KEY idx_mega_flow_work_order_project_nos ((CAST(project_nos AS CHAR(128) ARRAY))),
  KEY idx_mega_flow_work_order_targets ((CAST(targets AS CHAR(128) ARRAY))),
  KEY idx_mega_flow_work_order_sample_plate_barcodes ((CAST(sample_plate_barcodes AS CHAR(128) ARRAY))),
  KEY idx_mega_flow_work_order_cell_plate_barcodes ((CAST(cell_plate_barcodes AS CHAR(128) ARRAY)))
) COMMENT='镁伽流式工单';

CREATE TABLE IF NOT EXISTS mega_flow_work_order_dispatch (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  dispatchId VARCHAR(64) NOT NULL COMMENT '下发编号',
  work_order_id BIGINT NOT NULL COMMENT '工单ID',
  payload JSON NOT NULL COMMENT '下发JSON',
  payload_hash CHAR(64) NOT NULL COMMENT '下发内容哈希',
  content_hash_at_send CHAR(64) NOT NULL COMMENT '下发时工单内容哈希',
  status VARCHAR(32) NOT NULL DEFAULT 'pending' COMMENT '状态',
  pause_state VARCHAR(32) NULL COMMENT '暂停状态',
  sent_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '发送时间',
  created_by VARCHAR(128) NULL COMMENT '操作人',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_mega_flow_work_order_dispatch_id (dispatchId),
  KEY idx_mega_flow_work_order_dispatch_order (work_order_id)
) COMMENT='镁伽流式工单下发记录';

-- ---------------------------------------------------------------------------
-- 免疫 / 效价业务（models/immunology.py）
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS serum_imm_project (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  experiment_id VARCHAR(64) NULL COMMENT '实验ID',
  project_code VARCHAR(64) NULL COMMENT '项目管理编号',
  project_name VARCHAR(255) NULL COMMENT '项目名称',
  lab_notebook VARCHAR(64) NULL COMMENT '实验记录本号',
  reviewer VARCHAR(64) NULL COMMENT '审核人',
  project_purpose VARCHAR(255) NULL COMMENT '项目目的',
  start_date DATE NULL COMMENT '项目开始日期',
  immunization_interval VARCHAR(32) NULL COMMENT '免疫间隔',
  target_codes JSON NULL COMMENT '靶点编号列表',
  target_name VARCHAR(128) NULL COMMENT '靶点名称',
  target_type VARCHAR(64) NULL COMMENT '靶点类型',
  target_size VARCHAR(64) NULL COMMENT '靶点大小',
  owner VARCHAR(64) NULL COMMENT '负责人',
  pm VARCHAR(64) NULL COMMENT 'PM',
  study_type VARCHAR(64) NULL COMMENT '课题类型',
  assay_method VARCHAR(128) NULL COMMENT '检测方法',
  facs_plate_count INT NULL COMMENT 'FACS板数',
  elisa_plate_count INT NULL COMMENT 'ELISA板数',
  project_status VARCHAR(64) NULL COMMENT '项目状态',
  remark VARCHAR(255) NULL COMMENT '备注',
  mouse_strain VARCHAR(128) NULL COMMENT '确切鼠型',
  mouse_strain_category VARCHAR(128) NULL COMMENT '归类鼠型',
  prep_status VARCHAR(16) NULL COMMENT '制备状态',
  PRIMARY KEY (id),
  UNIQUE KEY uk_serum_imm_project_experiment_id (experiment_id)
) COMMENT='免疫项目表';

CREATE TABLE IF NOT EXISTS serum_imm_workbench (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  experiment_id VARCHAR(64) NULL COMMENT '实验号',
  project_code VARCHAR(64) NULL COMMENT '项目管理编号',
  project_name VARCHAR(255) NULL COMMENT '项目名称',
  project_purpose VARCHAR(255) NULL COMMENT '项目目的',
  start_date DATE NULL COMMENT '项目开始日期',
  immunization_interval VARCHAR(32) NULL COMMENT '免疫间隔',
  target_codes JSON NULL COMMENT '靶点编号列表',
  target_name VARCHAR(128) NULL COMMENT '靶点名称',
  target_type VARCHAR(64) NULL COMMENT '靶点类型',
  target_size VARCHAR(64) NULL COMMENT '靶点大小',
  owner VARCHAR(64) NULL COMMENT '开展人',
  pm VARCHAR(64) NULL COMMENT 'PM',
  study_type VARCHAR(64) NULL COMMENT '课题类型',
  assay_method VARCHAR(128) NULL COMMENT '检测方法',
  facs_plate_count INT NULL COMMENT 'FACS板数',
  elisa_plate_count INT NULL COMMENT 'ELISA板数',
  remark VARCHAR(255) NULL COMMENT '备注',
  mouse_strain VARCHAR(128) NULL COMMENT '确切鼠型',
  mouse_strain_category VARCHAR(128) NULL COMMENT '归类鼠型',
  sort_order INT NULL COMMENT '排序值',
  priority VARCHAR(32) NOT NULL DEFAULT '正常' COMMENT '优先级',
  plan_status VARCHAR(32) NOT NULL DEFAULT '草稿' COMMENT '工作台状态',
  project_set_code VARCHAR(64) NULL COMMENT '项目集编号',
  species_cross VARCHAR(64) NULL COMMENT '种属交叉',
  immuno_method VARCHAR(64) NULL COMMENT '免疫方式',
  reviewer VARCHAR(64) NULL COMMENT '审核人',
  review_status VARCHAR(32) NOT NULL DEFAULT '未审' COMMENT '审核结果',
  mouse_scheme_no VARCHAR(64) NULL COMMENT '小鼠方案号',
  mouse_count VARCHAR(32) NULL COMMENT '小鼠数量',
  mouse_zygosity VARCHAR(32) NULL COMMENT '小鼠合子状态',
  mouse_birth_date DATE NULL COMMENT '出生日期',
  mouse_age_weeks VARCHAR(32) NULL COMMENT '周龄',
  mouse_expand_requested VARCHAR(16) NULL COMMENT '是否代下扩繁',
  mouse_region VARCHAR(64) NULL COMMENT '提供地区',
  mouse_room VARCHAR(64) NULL COMMENT '房间号',
  mouse_status VARCHAR(32) NOT NULL DEFAULT '未定' COMMENT '运输状态',
  mouse_arrive_date DATE NULL COMMENT '到鼠时间',
  mouse_remark VARCHAR(255) NULL COMMENT '小鼠备注',
  antigen_source VARCHAR(128) NULL COMMENT '抗原来源',
  antigen_ready VARCHAR(16) NOT NULL DEFAULT '否' COMMENT '抗原到货情况',
  antigen_eta VARCHAR(32) NULL COMMENT '抗原预计日',
  lnp_ordered VARCHAR(16) NULL COMMENT 'LNP是否下单',
  cell_prep_status VARCHAR(64) NULL COMMENT '冲击细胞准备',
  antigen_remark VARCHAR(255) NULL COMMENT '抗原备注',
  can_start VARCHAR(16) NOT NULL DEFAULT '否' COMMENT '是否可开展',
  created_by VARCHAR(64) NULL COMMENT '创建人',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_serum_imm_workbench_experiment_id (experiment_id)
) COMMENT='免疫项目工作台';

CREATE TABLE IF NOT EXISTS serum_imm_mouse (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  experiment_id VARCHAR(64) NULL COMMENT '实验ID',
  group_id VARCHAR(32) NULL COMMENT '组别',
  mouse_strain VARCHAR(128) NULL COMMENT '小鼠品系',
  mouse_strain_category VARCHAR(128) NULL COMMENT '归类鼠型',
  mouse_count VARCHAR(32) NULL COMMENT '免疫数量',
  age_weeks VARCHAR(32) NULL COMMENT '周龄',
  sex VARCHAR(32) NULL COMMENT '性别',
  cage_position VARCHAR(64) NULL COMMENT '笼位',
  vendor VARCHAR(128) NULL COMMENT '供应商',
  mouse_no_list VARCHAR(512) NULL COMMENT '鼠号列表',
  mouse_registry JSON NULL COMMENT '鼠号明细',
  remark VARCHAR(255) NULL COMMENT '备注',
  PRIMARY KEY (id),
  KEY idx_serum_imm_mouse_experiment_id (experiment_id)
) COMMENT='小鼠信息表';

CREATE TABLE IF NOT EXISTS serum_file (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  experiment_id VARCHAR(64) NOT NULL COMMENT '实验编号',
  upload_user VARCHAR(64) NULL COMMENT '上传人',
  file_name VARCHAR(255) NOT NULL COMMENT '文件名',
  file_path VARCHAR(1024) NOT NULL COMMENT '文件位置',
  source VARCHAR(16) NOT NULL DEFAULT 'manual' COMMENT '来源：manual 手工，mega 镁伽回传',
  created_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  updated_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  PRIMARY KEY (id),
  KEY idx_serum_file_experiment_id (experiment_id)
) COMMENT='效价实验文件表';

CREATE TABLE IF NOT EXISTS serum_imm_antigen (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  experiment_id VARCHAR(64) NULL COMMENT '实验ID',
  antigen_id VARCHAR(32) NULL COMMENT '抗原ID',
  species VARCHAR(32) NULL COMMENT '抗原种属',
  antigen_type VARCHAR(64) NULL COMMENT '抗原类型',
  antigen_name VARCHAR(255) NULL COMMENT '抗原名称',
  catalog_no VARCHAR(64) NULL COMMENT '货号',
  lot_no VARCHAR(64) NULL COMMENT '批号',
  stock_conc VARCHAR(64) NULL COMMENT '原液浓度',
  vendor VARCHAR(128) NULL COMMENT '供应商',
  adjuvant_type VARCHAR(64) NULL COMMENT '佐剂类型',
  adjuvant_source VARCHAR(128) NULL COMMENT '佐剂来源',
  PRIMARY KEY (id),
  UNIQUE KEY uq_experiment_antigen (experiment_id, antigen_id)
) COMMENT='免疫抗原信息表';

CREATE TABLE IF NOT EXISTS serum_imm_step (
  step_id BIGINT NOT NULL AUTO_INCREMENT COMMENT '步骤主键ID',
  experiment_id VARCHAR(64) NULL COMMENT '实验ID',
  group_id VARCHAR(32) NULL COMMENT '组别',
  sort_order INT NOT NULL DEFAULT 0 COMMENT '组内排序',
  stage_name VARCHAR(64) NULL COMMENT '免疫阶段',
  antigen_id VARCHAR(32) NULL COMMENT '抗原ID',
  antigen_dose VARCHAR(64) NULL COMMENT '抗原剂量',
  adjuvant_name VARCHAR(64) NULL COMMENT '佐剂名称',
  cpg_dose VARCHAR(64) NULL COMMENT 'CpG剂量',
  injection_volume VARCHAR(64) NULL COMMENT '注射体积',
  route VARCHAR(32) NULL COMMENT '给药途径',
  injection_site VARCHAR(64) NULL COMMENT '给药部位',
  day_relative VARCHAR(16) NULL COMMENT '相对天数',
  date_actual DATE NULL COMMENT '实际日期',
  remark VARCHAR(255) NULL COMMENT '备注',
  PRIMARY KEY (step_id),
  KEY idx_serum_imm_step_experiment_id (experiment_id)
) COMMENT='免疫实验步骤表';

CREATE TABLE IF NOT EXISTS serum_titer_pc (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  experiment_id VARCHAR(64) NULL COMMENT '实验ID',
  pc_name VARCHAR(255) NULL COMMENT 'PC名称',
  catalog_batch VARCHAR(128) NULL COMMENT '货号批次',
  source VARCHAR(128) NULL COMMENT '来源',
  concentration VARCHAR(64) NULL COMMENT '浓度',
  PRIMARY KEY (id),
  KEY idx_serum_titer_pc_experiment_id (experiment_id)
) COMMENT='效价阳性对照表';

CREATE TABLE IF NOT EXISTS serum_titer_target (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  experiment_id VARCHAR(64) NULL COMMENT '实验ID',
  type VARCHAR(32) NULL COMMENT '类型',
  species VARCHAR(32) NULL COMMENT '种属',
  name VARCHAR(255) NULL COMMENT '名称',
  batch_no VARCHAR(64) NULL COMMENT '批次',
  passage VARCHAR(64) NULL COMMENT '代次',
  cell_count VARCHAR(64) NULL COMMENT '细胞量',
  catalog_no VARCHAR(64) NULL COMMENT '货号',
  source VARCHAR(128) NULL COMMENT '来源',
  PRIMARY KEY (id),
  KEY idx_serum_titer_target_experiment_id (experiment_id)
) COMMENT='效价检测目标表';

CREATE TABLE IF NOT EXISTS serum_facs_plate (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  experiment_id VARCHAR(64) NOT NULL COMMENT '实验编号',
  qr_code VARCHAR(128) NULL COMMENT '板二维码编号',
  instrument_type VARCHAR(64) NULL COMMENT '仪器类型',
  image_file_id BIGINT NULL COMMENT '图片文件id',
  excel_file_id BIGINT NULL COMMENT 'Excel文件id',
  immune_stage VARCHAR(64) NOT NULL COMMENT '免疫阶段',
  x_axis VARCHAR(64) NULL COMMENT '横坐标参数',
  y_axis VARCHAR(64) NULL COMMENT '纵坐标参数',
  cell_target_id BIGINT NULL COMMENT '细胞标靶id',
  pc_upper_id BIGINT NULL COMMENT '上PC的id',
  pc_lower_id BIGINT NULL COMMENT '下PC的id',
  upper_group VARCHAR(32) NULL COMMENT '上半板组别',
  lower_group VARCHAR(32) NULL COMMENT '下半板组别',
  upper_mouse_list JSON NULL COMMENT '上半板小鼠列表',
  lower_mouse_list JSON NULL COMMENT '下半板小鼠列表',
  upper_slot_groups JSON NULL COMMENT '上半板孔位分组标题',
  lower_slot_groups JSON NULL COMMENT '下半板孔位分组标题',
  positive_well_list JSON NULL COMMENT '阳性孔位列表',
  source VARCHAR(16) NOT NULL DEFAULT 'manual' COMMENT '来源：manual 手工，mega 镁伽回传',
  PRIMARY KEY (id),
  KEY idx_serum_facs_plate_experiment_id (experiment_id)
) COMMENT='FACS效价板信息表';

CREATE TABLE IF NOT EXISTS serum_elisa_plate (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  experiment_id VARCHAR(64) NOT NULL COMMENT '实验ID',
  qr_code VARCHAR(128) NULL COMMENT '二维码编号',
  excel_file_id BIGINT NULL COMMENT 'Excel文件ID',
  immune_stage VARCHAR(64) NOT NULL DEFAULT '' COMMENT '免疫阶段',
  protein_target_id BIGINT NULL COMMENT '检测标靶ID',
  pc_id BIGINT NULL COMMENT '阳性对照ID',
  mouse_group VARCHAR(64) NULL COMMENT '组别-品系',
  antigen_type VARCHAR(64) NULL COMMENT '抗原类型',
  slot_groups JSON NULL COMMENT '上方分组标题',
  upper_slot_list JSON NULL COMMENT '上方小鼠槽位',
  lower_slot_list JSON NULL COMMENT '下方对照槽位',
  positive_well_list JSON NULL COMMENT '阳性孔列表',
  absorbance_1 JSON NULL COMMENT '吸光度数据',
  PRIMARY KEY (id),
  KEY idx_serum_elisa_plate_experiment_id (experiment_id)
) COMMENT='ELISA效价板信息表';

CREATE TABLE IF NOT EXISTS serum_titer_order (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  experiment_id VARCHAR(64) NOT NULL COMMENT '免疫实验ID',
  titer_order_id VARCHAR(128) NOT NULL COMMENT '效价工单ID',
  lab_notebook VARCHAR(64) NULL COMMENT '实验记录本号',
  cage_position VARCHAR(64) NULL COMMENT '笼位',
  blood_collection_date DATE NULL COMMENT '采血日期',
  blood_collection_seq INT NULL COMMENT '第N次采血',
  mouse_count INT NULL COMMENT '只数',
  assay_method VARCHAR(128) NULL COMMENT '检测方法',
  facs_plate_count INT NULL COMMENT 'FACS板数',
  elisa_plate_count INT NULL COMMENT 'ELISA板数',
  titer_owners JSON NULL COMMENT '效价负责人',
  test_dates JSON NULL COMMENT '检测日期',
  serum_status VARCHAR(64) NULL COMMENT '血清状态',
  remark VARCHAR(500) NULL COMMENT '备注',
  summary VARCHAR(500) NULL COMMENT '效价小结',
  priority VARCHAR(64) NOT NULL DEFAULT '正常' COMMENT '检测优先级',
  PRIMARY KEY (id),
  UNIQUE KEY uk_serum_titer_order_id (titer_order_id),
  KEY idx_serum_titer_order_experiment_id (experiment_id)
) COMMENT='效价工单';

CREATE TABLE IF NOT EXISTS discovery_workbench (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  discovery_id VARCHAR(32) NOT NULL COMMENT '发现安排号',
  project_code VARCHAR(64) NULL COMMENT '项目管理编号',
  experiment_id VARCHAR(64) NULL COMMENT '实验号',
  target_name VARCHAR(128) NULL COMMENT '靶点名称',
  target_codes JSON NULL COMMENT '靶点编号列表',
  study_type VARCHAR(64) NULL COMMENT '课题类型',
  pm VARCHAR(64) NULL COMMENT 'PM',
  mouse_strain_category VARCHAR(128) NULL COMMENT '归类鼠型',
  mouse_strain VARCHAR(128) NULL COMMENT '小鼠品系',
  cage_position VARCHAR(64) NULL COMMENT '笼位',
  mouse_count INT NULL COMMENT '小鼠只数',
  mouse_nos VARCHAR(1000) NULL COMMENT '鼠号',
  serum_titer VARCHAR(1000) NULL COMMENT '血清效价',
  immune_antigen VARCHAR(1000) NULL COMMENT '免疫用抗原',
  screening_methods VARCHAR(64) NULL COMMENT '筛选方式',
  screening_antigen VARCHAR(1000) NULL COMMENT '筛选抗原',
  prior_screening VARCHAR(2000) NULL COMMENT '既往筛选',
  prior_screening_images JSON NULL COMMENT '既往筛选图片',
  positive_cell_count VARCHAR(255) NULL COMMENT '阳性细胞数',
  plate_nos VARCHAR(1000) NULL COMMENT '板号',
  harvest_date DATE NULL COMMENT '剖鼠取细胞日',
  boost_date DATE NULL COMMENT '冲击免日期',
  boost_antigen VARCHAR(1000) NULL COMMENT '冲击免抗原',
  boost_cells VARCHAR(1000) NULL COMMENT '冲击免细胞',
  owner VARCHAR(64) NULL COMMENT '负责人',
  immune_owner VARCHAR(64) NULL COMMENT '免疫负责人',
  cell_collector VARCHAR(64) NULL COMMENT '细胞收集人',
  status VARCHAR(32) NOT NULL DEFAULT '规划中' COMMENT '状态',
  priority VARCHAR(32) NOT NULL DEFAULT '正常' COMMENT '优先级',
  sort_order INT NULL COMMENT '排序值',
  remark VARCHAR(1000) NULL COMMENT '备注',
  created_by VARCHAR(64) NULL COMMENT '创建人',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_discovery_workbench_discovery_id (discovery_id)
) COMMENT='抗体发现项目工作台';

CREATE TABLE IF NOT EXISTS discovery_cell_bank (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  workbench_id BIGINT NOT NULL COMMENT '发现安排ID',
  discovery_id VARCHAR(32) NULL COMMENT '发现安排号',
  cell_kind VARCHAR(32) NOT NULL COMMENT '细胞类型',
  mouse_nos VARCHAR(1000) NULL COMMENT '鼠号',
  tube_count INT NULL COMMENT '管数',
  cell_count VARCHAR(64) NULL COMMENT '细胞量',
  volume VARCHAR(64) NULL COMMENT '体积',
  box_location VARCHAR(128) NULL COMMENT '冻存位置',
  frozen_on DATE NULL COMMENT '冻存日期',
  operator VARCHAR(64) NULL COMMENT '操作人',
  checked_out_on DATE NULL COMMENT '出库日期',
  checked_out_by VARCHAR(64) NULL COMMENT '出库人',
  remark VARCHAR(500) NULL COMMENT '备注',
  created_by VARCHAR(64) NULL COMMENT '创建人',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  KEY idx_discovery_cell_bank_workbench_id (workbench_id)
) COMMENT='抗体发现留存细胞冻存';

CREATE TABLE IF NOT EXISTS discovery_synthesis_order (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  synthesis_order_id VARCHAR(32) NOT NULL COMMENT '系统单号',
  source_one_type VARCHAR(16) NULL COMMENT '外部来源类型',
  source_one_id BIGINT NULL COMMENT '外部来源记录ID',
  source_snapshot JSON NULL COMMENT '外部来源当前值快照',
  status VARCHAR(32) NOT NULL DEFAULT '待下单' COMMENT '状态',
  priority VARCHAR(32) NOT NULL DEFAULT '正常' COMMENT '优先级',
  sort_order INT NULL COMMENT '排序值',
  order_kind VARCHAR(32) NOT NULL DEFAULT '常规合成' COMMENT '订单性质',
  supply_mode VARCHAR(32) NOT NULL DEFAULT '合成到货' COMMENT '供应方式',
  target_name VARCHAR(128) NULL COMMENT '靶点名称',
  target_codes JSON NULL COMMENT '靶点编号列表',
  target_type VARCHAR(64) NULL COMMENT '靶点类型',
  target_color VARCHAR(16) NULL COMMENT '靶点颜色标记',
  mouse_strain VARCHAR(128) NULL COMMENT '小鼠品系',
  selection_method VARCHAR(128) NULL COMMENT '挑选方式',
  is_rechoose VARCHAR(16) NULL COMMENT '是否补挑',
  synthesis_code VARCHAR(64) NULL COMMENT '送测转码',
  order_no VARCHAR(64) NULL COMMENT '合成订单号',
  synthetic_corp VARCHAR(64) NULL COMMENT '合成公司',
  synthetic_count INT NULL COMMENT '合成个数',
  synthetic_date DATE NULL COMMENT '合成日期',
  order_sender VARCHAR(128) NULL COMMENT '下单人',
  arrival_count INT NULL COMMENT '发货个数',
  arrival_date DATE NULL COMMENT '发货日期',
  supernatant_checked_at DATETIME NULL COMMENT '上清补查时间',
  affinity_status VARCHAR(32) NULL COMMENT '亲和力检测状态',
  affinity_owner VARCHAR(64) NULL COMMENT '亲和力人员',
  flow_date DATE NULL COMMENT '流式日期',
  flow_status VARCHAR(32) NULL COMMENT '流式检测状态',
  affinity_date DATE NULL COMMENT '亲和力日期',
  affinity_result VARCHAR(32) NULL COMMENT '亲和力结果',
  owner VARCHAR(64) NULL COMMENT '负责人',
  owner_claimed_at DATETIME NULL COMMENT '负责人认领时间',
  batch_label VARCHAR(255) NULL COMMENT '工单批次',
  flow_note VARCHAR(500) NULL COMMENT '流式说明',
  report_reason VARCHAR(500) NULL COMMENT '未出原因',
  remark VARCHAR(1000) NULL COMMENT '备注',
  eng_type VARCHAR(128) NULL COMMENT '改造类型',
  eng_method VARCHAR(128) NULL COMMENT '改造方式',
  eng_parent_seq VARCHAR(500) NULL COMMENT '改造序列或母本',
  eng_requirement VARCHAR(1000) NULL COMMENT '改造要求',
  eng_result VARCHAR(500) NULL COMMENT '改造结果',
  project_code VARCHAR(64) NULL COMMENT '项目管理编号',
  experiment_id VARCHAR(64) NULL COMMENT '实验号',
  study_type VARCHAR(64) NULL COMMENT '课题类型',
  pm VARCHAR(64) NULL COMMENT 'PM',
  created_by VARCHAR(64) NULL COMMENT '创建人',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_discovery_synthesis_order_id (synthesis_order_id),
  UNIQUE KEY uk_discovery_synthesis_order_source_one (source_one_type, source_one_id)
) COMMENT='抗体发现合成与验证单';

CREATE TABLE IF NOT EXISTS molecular_library_order (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  library_order_id VARCHAR(32) NOT NULL COMMENT '系统工单号',
  library_code VARCHAR(64) NULL COMMENT '建库编号',
  source_discovery_id VARCHAR(32) NULL COMMENT '来源发现ID',
  source_project_code VARCHAR(64) NULL COMMENT '来源项目编号',
  study_type VARCHAR(64) NULL COMMENT '课题类型',
  source_experiment_type VARCHAR(64) NULL COMMENT '噬菌体实验类型',
  project_goal VARCHAR(1000) NULL COMMENT '噬菌体实验目标',
  target_name VARCHAR(128) NULL COMMENT '靶点名称',
  target_codes JSON NULL COMMENT '靶点编号列表',
  pm VARCHAR(64) NULL COMMENT 'PM',
  mouse_strain VARCHAR(128) NULL COMMENT '小鼠品系',
  sample_type VARCHAR(32) NULL COMMENT '样品类型',
  build_type VARCHAR(32) NOT NULL COMMENT '建库类型',
  sample_source VARCHAR(32) NULL COMMENT '样品来源',
  received_on DATE NULL COMMENT '样品交接日期',
  instrument_on DATE NULL COMMENT '上机日期',
  blood_collected_on DATE NULL COMMENT '采血日期',
  positive_cell_count VARCHAR(255) NULL COMMENT '阳性细胞数',
  plate_nos JSON NULL COMMENT '孔板编号列表',
  cell_type VARCHAR(64) NULL COMMENT '细胞类型',
  target_forms VARCHAR(16) NULL COMMENT '靶点形式',
  notebook_no VARCHAR(64) NULL COMMENT '实验记录本号',
  immunization_stage VARCHAR(64) NULL COMMENT '免疫阶段',
  library_batch_no VARCHAR(64) NULL COMMENT '建库批号',
  status VARCHAR(24) NOT NULL DEFAULT '待处理' COMMENT '状态',
  priority VARCHAR(24) NOT NULL DEFAULT '正常' COMMENT '优先级',
  owner VARCHAR(64) NULL COMMENT '负责人',
  started_at DATE NULL COMMENT '工单开始日期',
  finished_at DATE NULL COMMENT '工单完成日期',
  rna_location VARCHAR(255) NULL COMMENT 'RNA存放位置',
  cdna_location VARCHAR(255) NULL COMMENT 'cDNA存放位置',
  library_location VARCHAR(255) NULL COMMENT '文库产物位置',
  cdna_concentration VARCHAR(64) NULL COMMENT 'cDNA浓度',
  library_concentration VARCHAR(64) NULL COMMENT '文库浓度',
  initial_library_size VARCHAR(64) NULL COMMENT '初始库容',
  effective_library_size VARCHAR(64) NULL COMMENT '有效库容',
  fragment_size_bp VARCHAR(64) NULL COMMENT '片段大小',
  h_forward_primer_id BIGINT NULL COMMENT 'H正向引物字典ID',
  h_forward_primer_name VARCHAR(128) NULL COMMENT 'H正向引物名称快照',
  h_reverse_primer_id BIGINT NULL COMMENT 'H反向引物字典ID',
  h_reverse_primer_name VARCHAR(128) NULL COMMENT 'H反向引物名称快照',
  h_primer_concentration VARCHAR(64) NULL COMMENT 'H引物浓度',
  k_forward_primer_id BIGINT NULL COMMENT 'K正向引物字典ID',
  k_forward_primer_name VARCHAR(128) NULL COMMENT 'K正向引物名称快照',
  k_reverse_primer_id BIGINT NULL COMMENT 'K反向引物字典ID',
  k_reverse_primer_name VARCHAR(128) NULL COMMENT 'K反向引物名称快照',
  k_primer_concentration VARCHAR(64) NULL COMMENT 'K引物浓度',
  l_forward_primer_id BIGINT NULL COMMENT 'L正向引物字典ID',
  l_forward_primer_name VARCHAR(128) NULL COMMENT 'L正向引物名称快照',
  l_reverse_primer_id BIGINT NULL COMMENT 'L反向引物字典ID',
  l_reverse_primer_name VARCHAR(128) NULL COMMENT 'L反向引物名称快照',
  l_primer_concentration VARCHAR(64) NULL COMMENT 'L引物浓度',
  index_mode VARCHAR(16) NULL COMMENT 'Barcode方式',
  i7_catalog_id BIGINT NULL COMMENT 'i7字典ID',
  i7_name VARCHAR(128) NULL COMMENT 'i7名称快照',
  i7_sequence VARCHAR(64) NULL COMMENT 'i7序列快照',
  i5_catalog_id BIGINT NULL COMMENT 'i5字典ID',
  i5_name VARCHAR(128) NULL COMMENT 'i5名称快照',
  i5_sequence VARCHAR(64) NULL COMMENT 'i5序列快照',
  qc_result VARCHAR(16) NULL COMMENT '质检结论',
  qc_owner VARCHAR(64) NULL COMMENT '质检人',
  qc_on DATE NULL COMMENT '质检日期',
  qc_note VARCHAR(1000) NULL COMMENT '质检说明',
  remark VARCHAR(1000) NULL COMMENT '备注',
  created_by VARCHAR(64) NULL COMMENT '创建人',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_molecular_library_order_id (library_order_id),
  UNIQUE KEY uk_molecular_library_order_library_code (library_code),
  KEY idx_molecular_library_order_source_discovery_id (source_discovery_id)
) COMMENT='文库构建工单';

CREATE TABLE IF NOT EXISTS molecular_primer_index_catalog (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  name VARCHAR(128) NOT NULL COMMENT '名称',
  family VARCHAR(32) NOT NULL COMMENT '系列',
  direction VARCHAR(8) NULL COMMENT '引物方向',
  version VARCHAR(16) NULL COMMENT '版本',
  short_sequence VARCHAR(64) NOT NULL COMMENT '显示序列',
  homology_arm_1 VARCHAR(128) NULL COMMENT '同源臂1',
  homology_arm_2 VARCHAR(128) NULL COMMENT '同源臂2',
  source_file VARCHAR(255) NULL COMMENT '来源文件',
  source_row INT NULL COMMENT '来源行号',
  active TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
  note VARCHAR(500) NULL COMMENT '备注',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_molecular_primer_index_name (name)
) COMMENT='引物与Barcode字典';

CREATE TABLE IF NOT EXISTS molecular_library_result_package (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  original_name VARCHAR(255) NOT NULL COMMENT '原文件夹名',
  signature CHAR(64) NOT NULL COMMENT '包内容指纹',
  storage_prefix VARCHAR(1024) NOT NULL COMMENT '包存储目录',
  owner_order_id BIGINT NULL COMMENT '质检页上传所属工单',
  uploaded_by VARCHAR(64) NULL COMMENT '上传人',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_molecular_library_result_package_signature (signature),
  KEY idx_molecular_library_result_package_owner_order_id (owner_order_id),
  CONSTRAINT fk_molecular_library_result_package_owner_order
    FOREIGN KEY (owner_order_id) REFERENCES molecular_library_order (id)
) COMMENT='文库测序结果包';

CREATE TABLE IF NOT EXISTS molecular_library_result_file (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  package_id BIGINT NULL COMMENT '所属测序包',
  relative_path VARCHAR(1024) NULL COMMENT '包内相对路径',
  storage_path VARCHAR(1024) NOT NULL COMMENT '存储路径',
  mime_type VARCHAR(128) NULL COMMENT '文件MIME',
  byte_size BIGINT NOT NULL COMMENT '文件大小',
  sha256 CHAR(64) NOT NULL COMMENT '文件哈希',
  dedupe_key VARCHAR(80) NULL COMMENT '可复用物理文件去重键',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '首次保存时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_molecular_library_result_dedupe_key (dedupe_key),
  KEY idx_molecular_library_result_sha256 (sha256),
  KEY idx_molecular_library_result_file_package_id (package_id),
  CONSTRAINT fk_molecular_library_result_file_package
    FOREIGN KEY (package_id) REFERENCES molecular_library_result_package (id)
) COMMENT='文库结果文件';

CREATE TABLE IF NOT EXISTS molecular_library_result_link (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  file_id BIGINT NOT NULL COMMENT '物理文件ID',
  order_id BIGINT NOT NULL COMMENT '文库工单ID',
  original_name VARCHAR(255) NOT NULL COMMENT '显示文件名',
  is_final_qc TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否最终质检文件',
  qc_regions JSON NULL COMMENT '质检选区列表',
  uploaded_by VARCHAR(64) NULL COMMENT '上传人',
  sequence_status VARCHAR(32) NULL COMMENT '序列核对状态',
  sequence_target VARCHAR(8) NULL COMMENT '序列核对目标',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_molecular_library_result_link (file_id, order_id),
  KEY idx_molecular_library_result_link_order_id (order_id),
  CONSTRAINT fk_molecular_library_result_link_file
    FOREIGN KEY (file_id) REFERENCES molecular_library_result_file (id),
  CONSTRAINT fk_molecular_library_result_link_order
    FOREIGN KEY (order_id) REFERENCES molecular_library_order (id)
) COMMENT='文库结果关联';

CREATE TABLE IF NOT EXISTS molecular_transfection_order (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  transfection_order_id VARCHAR(32) NOT NULL COMMENT '系统工单号',
  transfection_type VARCHAR(16) NOT NULL COMMENT '转染类型',
  source_library_order_id VARCHAR(32) NULL COMMENT '来源文库工单号',
  project_code VARCHAR(64) NULL COMMENT '项目编号',
  study_type VARCHAR(64) NULL COMMENT '课题类型',
  target_name VARCHAR(128) NULL COMMENT '靶点名称',
  target_codes JSON NULL COMMENT '靶点编号列表',
  pm VARCHAR(64) NULL COMMENT 'PM',
  mouse_strain VARCHAR(128) NULL COMMENT '小鼠品系',
  plate_nos JSON NULL COMMENT '孔板编号列表',
  status VARCHAR(24) NOT NULL DEFAULT '待转染' COMMENT '状态',
  priority VARCHAR(24) NOT NULL DEFAULT '正常' COMMENT '优先级',
  owner VARCHAR(64) NULL COMMENT '负责人',
  transfected_on DATE NULL COMMENT '转染日期',
  finished_on DATE NULL COMMENT '完成日期',
  remark VARCHAR(1000) NULL COMMENT '备注',
  created_by VARCHAR(64) NULL COMMENT '创建人',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_molecular_transfection_order_id (transfection_order_id),
  UNIQUE KEY uk_molecular_transfection_order_source_library (source_library_order_id)
) COMMENT='转染与表达工单';

CREATE TABLE IF NOT EXISTS molecular_transfection_protein (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  protein_name VARCHAR(128) NOT NULL COMMENT '蛋白名称',
  heavy_chain VARCHAR(128) NOT NULL COMMENT '重链',
  light_chain VARCHAR(128) NULL COMMENT '轻链',
  target_name VARCHAR(128) NULL COMMENT '靶点名称',
  target_codes JSON NULL COMMENT '靶点编号列表',
  mouse_strain VARCHAR(128) NULL COMMENT '小鼠品系',
  source_order_id BIGINT NULL COMMENT '登记工单ID',
  created_by VARCHAR(64) NULL COMMENT '创建人',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_molecular_transfection_protein_name (protein_name),
  KEY idx_molecular_transfection_protein_source_order_id (source_order_id),
  CONSTRAINT fk_molecular_transfection_protein_source_order
    FOREIGN KEY (source_order_id) REFERENCES molecular_transfection_order (id)
) COMMENT='转染表：蛋白与重轻链质粒对应';

CREATE TABLE IF NOT EXISTS molecular_transfection_item (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  order_id BIGINT NOT NULL COMMENT '转染工单ID',
  protein_id BIGINT NOT NULL COMMENT '蛋白ID',
  PRIMARY KEY (id),
  UNIQUE KEY uk_molecular_transfection_item (order_id, protein_id),
  KEY idx_molecular_transfection_item_protein_id (protein_id),
  CONSTRAINT fk_molecular_transfection_item_order
    FOREIGN KEY (order_id) REFERENCES molecular_transfection_order (id),
  CONSTRAINT fk_molecular_transfection_item_protein
    FOREIGN KEY (protein_id) REFERENCES molecular_transfection_protein (id)
) COMMENT='转染工单蛋白';

CREATE TABLE IF NOT EXISTS molecular_cell_checkout_request (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  request_no VARCHAR(32) NOT NULL COMMENT '申请单号',
  status VARCHAR(16) NOT NULL DEFAULT '待审核' COMMENT '审核状态',
  applicant VARCHAR(64) NULL COMMENT '出库申请人',
  applied_on DATE NULL COMMENT '申请日期',
  item_count INT NOT NULL DEFAULT 0 COMMENT '冻存记录数量',
  reviewer VARCHAR(64) NULL COMMENT '审核人',
  reviewed_at DATETIME NULL COMMENT '审核时间',
  review_note VARCHAR(500) NULL COMMENT '审核意见',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_molecular_cell_checkout_request_no (request_no),
  KEY idx_molecular_cell_checkout_request_status (status)
) COMMENT='冻存细胞出库申请';

CREATE TABLE IF NOT EXISTS molecular_cell_checkout_item (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  request_id BIGINT NOT NULL COMMENT '申请单ID',
  cell_bank_id BIGINT NOT NULL COMMENT '发现留存细胞ID',
  library_order_id BIGINT NULL COMMENT '文库工单ID',
  library_code VARCHAR(64) NULL COMMENT '建库编号',
  discovery_id VARCHAR(32) NULL COMMENT '发现安排号',
  target_name VARCHAR(128) NULL COMMENT '靶点名称',
  instrument_on DATE NULL COMMENT '上机日期',
  mouse_strain VARCHAR(128) NULL COMMENT '小鼠品系',
  sample_source VARCHAR(32) NULL COMMENT '样品来源',
  cell_kind VARCHAR(32) NULL COMMENT '细胞类型',
  cell_count VARCHAR(64) NULL COMMENT '细胞量',
  tube_count INT NULL COMMENT '管数',
  box_location VARCHAR(128) NULL COMMENT '冻存位置',
  remark VARCHAR(500) NULL COMMENT '冻存备注',
  PRIMARY KEY (id),
  KEY idx_molecular_cell_checkout_item_request_id (request_id),
  KEY idx_molecular_cell_checkout_item_cell_bank_id (cell_bank_id),
  CONSTRAINT fk_molecular_cell_checkout_item_request
    FOREIGN KEY (request_id) REFERENCES molecular_cell_checkout_request (id)
) COMMENT='冻存细胞出库申请明细';


-- =============================================================================
-- 权限包 / 角色（仅示例三档：访客、业务员、系统管理；生产环境完全自定义）
-- 免疫之后的新模块不要再往 guest/operator 里加。
-- =============================================================================

INSERT IGNORE INTO sys_permission_bundle (code, name, module, description, sort_order) VALUES
  ('guest', '访客', 'common', '示例：各业务模块页面只读', 10),
  ('operator', '业务员', 'business', '示例：血清与镁伽常用编辑权限', 100),
  ('system_admin', '系统管理', 'system', '示例：系统管理模块全部权限', 900);

INSERT IGNORE INTO sys_permission_bundle_item (bundle_code, permission_code) VALUES
  ('guest', 'serum.page.workbench'),
  ('guest', 'serum.page.list'),
  ('guest', 'serum.page.detail'),
  ('guest', 'serum.page.titer'),
  ('guest', 'serum.page.titer_order'),
  ('guest', 'serum.page.cell'),
  ('guest', 'serum.cell.view'),
  ('guest', 'mega.page.flow_work_order'),
  ('guest', 'system.page.user'),
  ('guest', 'system.page.role'),
  ('guest', 'system.page.permission'),
  ('guest', 'system.page.feature'),
  ('operator', 'serum.page.workbench'),
  ('operator', 'serum.workbench.draft_edit'),
  ('operator', 'serum.workbench.support_edit'),
  ('operator', 'serum.page.list'),
  ('operator', 'serum.page.detail'),
  ('operator', 'serum.page.edit'),
  ('operator', 'serum.page.titer'),
  ('operator', 'serum.page.titer_order'),
  ('operator', 'serum.page.cell'),
  ('operator', 'serum.project.create'),
  ('operator', 'serum.project.edit'),
  ('operator', 'serum.project.delete'),
  ('operator', 'serum.status.update'),
  ('operator', 'serum.cage.update'),
  ('operator', 'serum.mouse.export'),
  ('operator', 'serum.titer.edit'),
  ('operator', 'serum.file.manage'),
  ('operator', 'serum.titer_order.edit'),
  ('operator', 'serum.titer_order.record.edit'),
  ('operator', 'serum.cell.view'),
  ('operator', 'serum.cell.prep_status.update'),
  ('operator', 'mega.page.flow_work_order'),
  ('operator', 'mega.flow_work_order.edit'),
  ('operator', 'mega.flow_work_order.dispatch'),
  ('system_admin', 'system.page.user'),
  ('system_admin', 'system.page.role'),
  ('system_admin', 'system.page.permission'),
  ('system_admin', 'system.page.operation_log'),
  ('system_admin', 'system.page.feature'),
  ('system_admin', 'system.user.manage'),
  ('system_admin', 'system.role.manage'),
  ('system_admin', 'system.permission.manage'),
  ('system_admin', 'system.operation_log.view'),
  ('system_admin', 'system.feature.manage');

INSERT IGNORE INTO sys_role (code, name, description, sort_order) VALUES
  ('guest', '访客', '示例：各模块只读', 90),
  ('operator', '业务员', '示例：血清与镁伽业务编辑', 10),
  ('system_admin', '系统管理', '示例：系统管理模块', 20);

INSERT IGNORE INTO sys_role_permission_bundle (role_id, bundle_code)
SELECT r.id, r.code FROM sys_role r WHERE r.code IN ('guest', 'operator', 'system_admin');

-- 首个超级管理员：is_superuser=TRUE 即拥有全部权限，无需绑定角色。
-- 在 bbctg_vita_server 目录下生成 password_hash 后执行：
--   python -c "from modules.auth.security import hash_password; print(hash_password('你的密码'))"
-- INSERT INTO sys_user (username, display_name, password_hash, status, is_superuser)
-- VALUES ('admin', '系统管理员', '替换为生成的 password_hash', 'active', TRUE);

-- =============================================================================
-- 外部细胞库 CELL_DB_URL：sam_sample（models/cell_inventory.py，勿在主库执行，仅备查）
-- =============================================================================
-- CREATE TABLE IF NOT EXISTS sam_sample (
--   id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
--   sample_no VARCHAR(20) NULL COMMENT '样本编号',
--   samplename VARCHAR(500) NULL COMMENT '样本名称',
--   sample_type VARCHAR(50) NULL COMMENT '样本类型',
--   sample_storage_vol DECIMAL(20,5) NULL COMMENT '库存体积',
--   organId VARCHAR(20) NULL COMMENT '器官ID',
--   genus VARCHAR(20) NULL COMMENT '种属',
--   target VARCHAR(50) NULL COMMENT '靶点',
--   generations VARCHAR(20) NULL COMMENT '代次',
--   batch_no VARCHAR(50) NULL COMMENT '批次号',
--   PRIMARY KEY (id)
-- ) COMMENT='细胞样本表';

-- =============================================================================
-- 外部员工库 EMPLOYEE_DB_URL：org_emp / org_depart（employee_sync.py，勿在主库执行，仅备查）
-- =============================================================================
-- CREATE TABLE IF NOT EXISTS org_depart (
--   id BIGINT NOT NULL COMMENT '部门ID',
--   sname VARCHAR(255) NULL COMMENT '部门名称',
--   top_id BIGINT NULL COMMENT '上级部门ID',
--   PRIMARY KEY (id)
-- ) COMMENT='部门表';
--
-- CREATE TABLE IF NOT EXISTS org_emp (
--   id BIGINT NOT NULL COMMENT '员工ID',
--   sname VARCHAR(255) NULL COMMENT '姓名',
--   snum VARCHAR(64) NULL COMMENT '工号',
--   sex TINYINT NULL COMMENT '性别',
--   mobile VARCHAR(32) NULL COMMENT '手机号',
--   email VARCHAR(128) NULL COMMENT '邮箱',
--   leave_date DATE NULL COMMENT '离职日期',
--   is_locked TINYINT(1) NULL COMMENT '是否锁定',
--   post VARCHAR(128) NULL COMMENT '职位',
--   cloud_open_id VARCHAR(100) NULL COMMENT '云之家OpenID',
--   depart_id BIGINT NULL COMMENT '部门ID',
--   PRIMARY KEY (id),
--   KEY idx_org_emp_depart (depart_id),
--   KEY idx_org_emp_openid (cloud_open_id)
-- ) COMMENT='员工表';
--
-- 同一 EMPLOYEE_DB_URL 外部平台库还包含正式靶点表
-- xdida_platform_biocytogen.target；本系统只读全量同步至主库 target，
-- 字段选择与同步规则见 modules/system/target_sync.py，勿修改外部表。

-- =============================================================================
-- 外部 One 库 ONE_DB_URL：one_task_ngs_task / one_task_ngs_data_analyze /
-- one_task_beacon_task / one_task_beacon_data_analyze（synthesis_progress/one_sync.py，
-- 勿在主库执行，仅只读同步合成订单与交付进度至 discovery_synthesis_order）
-- =============================================================================

