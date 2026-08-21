-- Antibody Forge / Vita 主库：全表 DDL + 权限点 / 接口审计映射 / 功能开关种子
-- 在 DATABASE_URL 空库执行本文件即可。
--
-- 说明：
--   - 本文件只维护**当前全量 DDL + 种子**（空库执行一次）；不收录历史 ALTER / 升级脚本。
--   - 表、字段 COMMENT 须齐全，风格与现有表一致；有表结构变更时直接改本文件中的 CREATE，勿追加迁移段。
--   - sys_permission / sys_permission_api / sys_feature_flag：与代码约定对齐，建议保持完整。
--   - 文末「权限包 / 角色」仅为克隆空库时的示例种子，方便快速生效；生产环境完全自定义，
--     不必与现网或示例一致，可删改或在系统管理中调整。
--   - 外部细胞库 sam_sample 见文末注释（CELL_DB_URL，models/cell_inventory.py），勿在主库执行。
--   - 外部员工库 org_emp / org_depart 见文末注释（EMPLOYEE_DB_URL，modules/system/employee_sync.py），勿在主库执行。
--
-- 文档：docs/README.md、docs/auth-permissions.md

CREATE TABLE IF NOT EXISTS sys_user (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
  username VARCHAR(64) NOT NULL UNIQUE COMMENT '账号',
  display_name VARCHAR(128) NULL COMMENT '姓名',
  password_hash VARCHAR(255) NULL COMMENT '密码哈希',
  openid VARCHAR(100) NULL UNIQUE COMMENT '云之家OpenID',
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
  KEY idx_sys_user_openid (openid),
  KEY idx_sys_user_department (department),
  KEY idx_sys_user_group_name (group_name),
  KEY idx_sys_user_gender (gender),
  KEY idx_sys_user_employment_status (employment_status),
  KEY idx_sys_user_status (status)
) COMMENT='系统用户表';

CREATE TABLE IF NOT EXISTS sys_role (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
  code VARCHAR(64) NOT NULL UNIQUE COMMENT '角色编码',
  name VARCHAR(128) NOT NULL COMMENT '角色名称',
  description VARCHAR(255) NULL COMMENT '角色描述',
  status VARCHAR(16) NOT NULL DEFAULT 'active' COMMENT '角色状态',
  sort_order INT NOT NULL DEFAULT 0 COMMENT '排序值',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  KEY idx_sys_role_status (status)
) COMMENT='系统角色表';

CREATE TABLE IF NOT EXISTS sys_permission (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
  code VARCHAR(128) NOT NULL UNIQUE COMMENT '权限编码',
  name VARCHAR(128) NOT NULL COMMENT '权限名称',
  type VARCHAR(16) NOT NULL COMMENT '权限类型',
  module VARCHAR(64) NULL COMMENT '所属模块编码',
  resource VARCHAR(64) NULL COMMENT '资源域',
  action VARCHAR(64) NULL COMMENT '动作',
  route_path VARCHAR(255) NULL COMMENT '前端路由路径',
  ui_key VARCHAR(128) NULL COMMENT '前端按钮或区域标识',
  parent_code VARCHAR(128) NULL COMMENT '上级权限编码',
  description VARCHAR(255) NULL COMMENT '权限描述',
  sort_order INT NOT NULL DEFAULT 0 COMMENT '排序值',
  status VARCHAR(16) NOT NULL DEFAULT 'active' COMMENT '权限状态',
  KEY idx_sys_permission_module (module),
  KEY idx_sys_permission_type (type),
  KEY idx_sys_permission_resource_action (resource, action),
  KEY idx_sys_permission_parent (parent_code),
  KEY idx_sys_permission_status (status)
) COMMENT='系统权限点表';

CREATE TABLE IF NOT EXISTS sys_permission_bundle (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
  code VARCHAR(64) NOT NULL UNIQUE COMMENT '权限包编码',
  name VARCHAR(128) NOT NULL COMMENT '权限包名称',
  module VARCHAR(64) NOT NULL COMMENT '所属模块',
  description VARCHAR(255) NULL COMMENT '权限包描述',
  status VARCHAR(16) NOT NULL DEFAULT 'active' COMMENT '权限包状态',
  sort_order INT NOT NULL DEFAULT 0 COMMENT '排序值',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  KEY idx_sys_permission_bundle_module (module),
  KEY idx_sys_permission_bundle_status (status)
) COMMENT='权限包表';

CREATE TABLE IF NOT EXISTS sys_permission_bundle_item (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
  bundle_code VARCHAR(64) NOT NULL COMMENT '权限包编码',
  permission_code VARCHAR(128) NOT NULL COMMENT '权限编码',
  UNIQUE KEY uq_sys_permission_bundle_item (bundle_code, permission_code),
  KEY idx_sys_permission_bundle_item_bundle (bundle_code),
  KEY idx_sys_permission_bundle_item_permission (permission_code)
) COMMENT='权限包权限点关系表';

CREATE TABLE IF NOT EXISTS sys_user_role (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
  user_id BIGINT NOT NULL COMMENT '用户ID',
  role_id BIGINT NOT NULL COMMENT '角色ID',
  UNIQUE KEY uq_sys_user_role (user_id, role_id),
  KEY idx_sys_user_role_user (user_id),
  KEY idx_sys_user_role_role (role_id)
) COMMENT='用户角色关系表';

CREATE TABLE IF NOT EXISTS sys_role_permission_bundle (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
  role_id BIGINT NOT NULL COMMENT '角色ID',
  bundle_code VARCHAR(64) NOT NULL COMMENT '权限包编码',
  UNIQUE KEY uq_sys_role_permission_bundle (role_id, bundle_code),
  KEY idx_sys_role_permission_bundle_role (role_id),
  KEY idx_sys_role_permission_bundle_bundle (bundle_code)
) COMMENT='角色权限包关系表';

CREATE TABLE IF NOT EXISTS sys_user_permission_override (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
  user_id BIGINT NOT NULL COMMENT '用户ID',
  permission_code VARCHAR(128) NOT NULL COMMENT '权限编码',
  effect VARCHAR(8) NOT NULL COMMENT '覆盖效果',
  reason VARCHAR(255) NULL COMMENT '覆盖原因',
  UNIQUE KEY uq_sys_user_permission_override (user_id, permission_code),
  KEY idx_sys_user_permission_override_user (user_id)
) COMMENT='用户权限覆盖表';

CREATE TABLE IF NOT EXISTS sys_operation_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
  user_id BIGINT NULL COMMENT '操作用户ID',
  username VARCHAR(64) NULL COMMENT '操作账号',
  operator_name VARCHAR(128) NULL COMMENT '操作人姓名',
  action VARCHAR(128) NOT NULL COMMENT '操作动作',
  operation_name VARCHAR(128) NULL COMMENT '操作名称',
  operation_type VARCHAR(32) NULL COMMENT '操作类型',
  target_type VARCHAR(64) NULL COMMENT '目标类型',
  target_id VARCHAR(128) NULL COMMENT '目标ID',
  target_label VARCHAR(255) NULL COMMENT '目标名称',
  result VARCHAR(16) NOT NULL DEFAULT 'success' COMMENT '操作结果',
  detail JSON NULL COMMENT '操作详情',
  error_message TEXT NULL COMMENT '错误信息',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
  KEY idx_sys_operation_log_user (user_id),
  KEY idx_sys_operation_log_action (action),
  KEY idx_sys_operation_log_operation_type (operation_type),
  KEY idx_sys_operation_log_created_at (created_at)
) COMMENT='系统操作日志表';

CREATE TABLE IF NOT EXISTS sys_permission_api (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
  permission_code VARCHAR(128) NOT NULL COMMENT '权限编码',
  method VARCHAR(16) NOT NULL COMMENT 'HTTP方法',
  path_pattern VARCHAR(255) NOT NULL COMMENT '接口路径模式',
  description VARCHAR(255) NULL COMMENT '接口说明',
  status VARCHAR(16) NOT NULL DEFAULT 'active' COMMENT '状态',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  UNIQUE KEY uq_sys_permission_api (permission_code, method, path_pattern),
  KEY idx_sys_permission_api_permission (permission_code),
  KEY idx_sys_permission_api_path (path_pattern)
) COMMENT='权限点接口映射表';

CREATE TABLE IF NOT EXISTS sys_feature_flag (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
  code VARCHAR(128) NOT NULL UNIQUE COMMENT '功能编码',
  name VARCHAR(128) NOT NULL COMMENT '功能名称',
  category VARCHAR(32) NOT NULL COMMENT '功能分类',
  description VARCHAR(255) NULL COMMENT '功能说明',
  enabled TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
  visible TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否显示',
  sort_order INT NOT NULL DEFAULT 0 COMMENT '排序值',
  config JSON NULL COMMENT '扩展配置',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) COMMENT='运行时功能配置（菜单可见性、功能开关、定时任务参数、站点偏好等）';

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
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  KEY idx_sys_job_run_log_job (job_code),
  KEY idx_sys_job_run_log_started_at (started_at),
  KEY idx_sys_job_run_log_result (result)
) COMMENT='定时任务运行日志（起止时间、耗时、结果摘要与结构化详情）';

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
  status VARCHAR(64) NOT NULL COMMENT '处理状态',
  error_message TEXT NULL COMMENT '错误信息',
  received_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '接收时间',
  UNIQUE KEY uk_order_sync_trace_id (trace_id),
  KEY idx_order_sync_received_at (received_at),
  KEY idx_order_sync_status (status)
) COMMENT='效价数据回传记录';

-- ---------------------------------------------------------------------------
-- 靶点主数据（models/target.py；外部平台只读同步镜像）
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS target (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  external_id BIGINT NOT NULL COMMENT '外部平台靶点ID',
  snum VARCHAR(100) NOT NULL COMMENT '靶点编号',
  name VARCHAR(100) NOT NULL COMMENT '靶点名称',
  type INT NULL COMMENT '靶点类型：1内部-千鼠万抗，2内部-其他，3外部，4NA',
  status INT NULL COMMENT '开发状态：1已开发，2未开发',
  category VARCHAR(200) NULL COMMENT '靶点分类',
  ko_lethal_info INT NULL COMMENT 'KO致死情况：1致死，2存活，3数据冲突，4NA',
  ko_lethal_info_desc VARCHAR(1000) NULL COMMENT 'KO致死信息备注',
  structural_properties VARCHAR(200) NULL COMMENT '结构特性类别',
  structure_feature VARCHAR(100) NULL COMMENT '结构特性（跨膜次数）',
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
  is_active BOOLEAN NOT NULL DEFAULT TRUE COMMENT '数据状态：1有效，0已下架',
  synced_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最近变更时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_target_external_id (external_id),
  UNIQUE KEY uk_target_snum (snum),
  KEY idx_target_name (name),
  KEY idx_target_human_gene_name (human_gene_official_name),
  KEY idx_target_mouse_gene_name (mouse_gene_official_name),
  KEY idx_target_status_type (status, type)
) COMMENT='靶点表（项目管理同步）';

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
  content_hash CHAR(64) NULL COMMENT 'content摘要',
  error_message TEXT NULL COMMENT '错误信息',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  KEY idx_mega_flow_work_order_status (status),
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
  payload_hash CHAR(64) NOT NULL COMMENT 'payload摘要',
  content_hash_at_send CHAR(64) NOT NULL COMMENT '发送时content摘要',
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
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '自增id',
  experiment_id VARCHAR(64) NULL COMMENT '实验ID',
  project_code VARCHAR(64) NULL COMMENT '项目管理编号',
  project_name VARCHAR(255) NULL COMMENT '项目名称',
  lab_notebook VARCHAR(64) NULL COMMENT '实验记录本号',
  project_purpose VARCHAR(255) NULL COMMENT '项目目的',
  start_date VARCHAR(32) NULL COMMENT '项目开始日期',
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

CREATE TABLE IF NOT EXISTS serum_imm_mouse (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '自增id',
  experiment_id VARCHAR(64) NULL COMMENT '实验ID',
  group_id VARCHAR(32) NULL COMMENT '组别',
  mouse_strain VARCHAR(128) NULL COMMENT '小鼠名称/品系',
  mouse_strain_category VARCHAR(128) NULL COMMENT '归类鼠型',
  mouse_count VARCHAR(32) NULL COMMENT '免疫数量',
  age_weeks VARCHAR(32) NULL COMMENT '周龄',
  sex VARCHAR(32) NULL COMMENT '性别',
  vendor VARCHAR(128) NULL COMMENT '供应商',
  mouse_no_list VARCHAR(512) NULL COMMENT '鼠号列表',
  mouse_registry JSON NULL COMMENT '鼠号明细',
  cage_position VARCHAR(64) NULL COMMENT '笼位',
  remark VARCHAR(255) NULL COMMENT '备注',
  PRIMARY KEY (id),
  KEY idx_serum_imm_mouse_experiment_id (experiment_id)
) COMMENT='小鼠信息表';

CREATE TABLE IF NOT EXISTS serum_file (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '自增id',
  experiment_id VARCHAR(64) NOT NULL COMMENT '实验编号',
  upload_user VARCHAR(64) NULL COMMENT '上传人',
  file_name VARCHAR(255) NOT NULL COMMENT '文件名',
  file_path VARCHAR(1024) NOT NULL COMMENT '文件位置',
  created_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  PRIMARY KEY (id),
  KEY idx_serum_file_experiment_id (experiment_id)
) COMMENT='效价实验文件表';

CREATE TABLE IF NOT EXISTS serum_imm_antigen (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '自增id',
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
  UNIQUE KEY uq_experiment_antigen (experiment_id, antigen_id),
  KEY idx_serum_imm_antigen_experiment_id (experiment_id)
) COMMENT='免疫抗原信息表';

CREATE TABLE IF NOT EXISTS serum_imm_step (
  step_id BIGINT NOT NULL AUTO_INCREMENT COMMENT '自增id',
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
  date_actual VARCHAR(32) NULL COMMENT '实际日期',
  remark VARCHAR(255) NULL COMMENT '备注',
  PRIMARY KEY (step_id),
  KEY idx_serum_imm_step_experiment_id (experiment_id)
) COMMENT='免疫实验步骤表';

CREATE TABLE IF NOT EXISTS serum_titer_pc (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '自增id',
  experiment_id VARCHAR(64) NULL COMMENT '实验ID',
  pc_name VARCHAR(255) NULL COMMENT 'PC名称',
  catalog_batch VARCHAR(128) NULL COMMENT '货号/批次',
  source VARCHAR(128) NULL COMMENT '来源',
  concentration VARCHAR(64) NULL COMMENT '浓度',
  PRIMARY KEY (id),
  KEY idx_serum_titer_pc_experiment_id (experiment_id)
) COMMENT='效价阳性对照表';

CREATE TABLE IF NOT EXISTS serum_titer_target (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '自增id',
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
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '自增id',
  experiment_id VARCHAR(64) NOT NULL COMMENT '实验编号',
  qr_code VARCHAR(128) NULL COMMENT '板二维码编号',
  image_file_id BIGINT NULL COMMENT '图片文件id',
  excel_file_id BIGINT NULL COMMENT 'Excel文件id',
  immune_stage VARCHAR(64) NULL COMMENT '免疫阶段',
  x_axis VARCHAR(64) NULL COMMENT '横坐标参数',
  y_axis VARCHAR(64) NULL COMMENT '纵坐标参数',
  cell_target_id BIGINT NULL COMMENT '细胞标靶id',
  pc_upper_id BIGINT NULL COMMENT '上PC的id',
  pc_lower_id BIGINT NULL COMMENT '下PC的id',
  upper_group VARCHAR(32) NULL COMMENT '上半板组别',
  lower_group VARCHAR(32) NULL COMMENT '下半板组别',
  upper_mouse_list JSON NULL,
  lower_mouse_list JSON NULL,
  upper_slot_groups JSON NULL COMMENT '上半板孔位分组标题',
  lower_slot_groups JSON NULL COMMENT '下半板孔位分组标题',
  positive_well_list JSON NULL,
  instrument_type VARCHAR(64) NULL COMMENT '仪器类型',
  PRIMARY KEY (id),
  KEY idx_serum_facs_plate_experiment_id (experiment_id)
) COMMENT='FACS效价板信息表';

CREATE TABLE IF NOT EXISTS serum_elisa_plate (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  experiment_id VARCHAR(64) NOT NULL COMMENT '实验ID',
  qr_code VARCHAR(128) NULL COMMENT '二维码编号',
  excel_file_id BIGINT NULL COMMENT 'Excel文件id(serum_file)',
  immune_stage VARCHAR(64) NOT NULL DEFAULT '' COMMENT '免疫阶段',
  protein_target_id BIGINT NULL COMMENT '检测标靶id(serum_titer_target)',
  pc_id BIGINT NULL COMMENT 'PC记录id(serum_titer_pc)',
  mouse_group VARCHAR(64) NULL COMMENT '组别-品系',
  antigen_type VARCHAR(64) NULL COMMENT '抗原类型',
  slot_groups JSON NULL COMMENT '上方分组标题',
  upper_slot_list JSON NULL COMMENT '上方鼠号槽位{layout,values}',
  lower_slot_list JSON NULL COMMENT '下方NC/PC槽位{layout,values}',
  positive_well_list JSON NULL COMMENT '阳性孔列表',
  absorbance_1 JSON NULL COMMENT '吸光度1:{wavelength,matrix}',
  PRIMARY KEY (id),
  KEY idx_serum_elisa_plate_experiment (experiment_id)
) COMMENT='ELISA效价板信息表';

CREATE TABLE IF NOT EXISTS serum_titer_order (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  experiment_id VARCHAR(64) NOT NULL COMMENT '免疫实验ID',
  titer_order_id VARCHAR(128) NOT NULL COMMENT '效价工单ID',
  cage_position VARCHAR(64) NULL COMMENT '笼位',
  blood_collection_date VARCHAR(32) NULL COMMENT '采血日期',
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
  priority VARCHAR(64) NULL COMMENT '检测优先级',
  PRIMARY KEY (id),
  UNIQUE KEY uk_serum_titer_order_id (titer_order_id),
  KEY idx_serum_titer_order_experiment_id (experiment_id)
) COMMENT='效价工单';

INSERT IGNORE INTO sys_permission
  (code, name, type, module, resource, action, route_path, ui_key, parent_code, sort_order)
VALUES
  ('discovery.page.target_library', '靶点情报', 'page', 'discovery', 'target', 'view', '/discovery/targets', NULL, NULL, 50),
  ('serum.page.list', '免疫实验列表', 'page', 'serum', 'project', 'view', '/serum/list', NULL, NULL, 100),
  ('serum.page.detail', '免疫实验详情', 'page', 'serum', 'project', 'view_detail', '/serum/detail', NULL, NULL, 110),
  ('serum.page.edit', '免疫实验编辑', 'page', 'serum', 'project', 'edit_page', '/serum/edit', NULL, NULL, 120),
  ('serum.page.titer', '血清效价数据', 'page', 'serum', 'titer', 'view', '/serum/titer', NULL, NULL, 130),
  ('serum.page.titer_order', '效价实验列表', 'page', 'serum', 'titer_order', 'view', '/serum/titer-orders', NULL, NULL, 135),
  ('serum.page.cell', '细胞库存查询', 'page', 'serum', 'cell', 'view', '/serum/cell', NULL, NULL, 140),
  ('serum.project.create', '新建免疫项目', 'action', 'serum', 'project', 'create', NULL, 'serum.project.create_button', 'serum.page.list', 200),
  ('serum.project.edit', '编辑本人负责免疫项目', 'action', 'serum', 'project', 'edit', NULL, 'serum.project.edit_button', 'serum.page.edit', 210),
  ('serum.project.edit_all', '编辑全部免疫项目', 'action', 'serum', 'project', 'edit_all', NULL, 'serum.project.edit_all_button', 'serum.page.edit', 215),
  ('serum.project.delete', '删除免疫项目', 'action', 'serum', 'project', 'delete', NULL, 'serum.project.delete_button', 'serum.page.edit', 220),
  ('serum.status.update', '快速修改状态', 'action', 'serum', 'project_status', 'update', NULL, 'serum.status.update_button', 'serum.page.list', 230),
  ('serum.status.auto_update', '自动更新状态', 'action', 'serum', 'project_status', 'auto_update', NULL, 'serum.status.auto_update_button', 'serum.page.list', 240),
  ('serum.mouse.export', '导出小鼠免疫数据', 'action', 'serum', 'mouse', 'export', NULL, 'serum.mouse.export_button', 'serum.page.list', 250),
  ('serum.cage.update', '更新笼位信息', 'action', 'serum', 'cage', 'update', NULL, 'serum.cage.update_button', 'serum.page.list', 260),
  ('serum.titer.edit', '编辑效价数据', 'action', 'serum', 'titer', 'edit', NULL, 'serum.titer.edit_button', 'serum.page.titer', 270),
  ('serum.titer.edit_all', '编辑全部项目效价数据', 'action', 'serum', 'titer', 'edit_all', NULL, 'serum.titer.edit_all_button', 'serum.page.titer', 275),
  ('serum.file.manage', '管理效价文件', 'action', 'serum', 'file', 'manage', NULL, 'serum.file.manage_button', 'serum.page.titer', 280),
  ('serum.cell.view', '查看细胞库存', 'action', 'serum', 'cell', 'view_inventory', NULL, 'serum.cell.view_button', 'serum.page.cell', 290),
  ('serum.cell.prep_status.update', '更新细胞制备状态', 'action', 'serum', 'cell', 'update_prep_status', NULL, 'serum.cell.prep_status.update_button', 'serum.page.cell', 300),
  ('serum.titer_order.edit', '编辑效价工单', 'action', 'serum', 'titer_order', 'edit', NULL, 'serum.titer_order.edit_button', 'serum.page.titer_order', 305),
  ('serum.titer_order.delete', '删除效价工单', 'action', 'serum', 'titer_order', 'delete', NULL, 'serum.titer_order.delete_button', 'serum.page.titer_order', 315),
  ('serum.titer_order.owner.edit', '编辑效价负责人', 'action', 'serum', 'titer_order', 'owner_edit', NULL, 'serum.titer_order.owner.edit_button', 'serum.page.titer_order', 320),
  ('serum.titer_order.record.edit', '编辑本人工单检测记录', 'action', 'serum', 'titer_order', 'record_edit', NULL, 'serum.titer_order.record.edit_button', 'serum.page.titer_order', 325),
  ('serum.titer_order.record.edit_all', '编辑全部工单检测记录', 'action', 'serum', 'titer_order', 'record_edit_all', NULL, 'serum.titer_order.record.edit_all_button', 'serum.page.titer_order', 326),
  ('mega.page.flow_work_order', '流式工单总览', 'page', 'mega', 'flow_work_order', 'view', '/mega-automation/flow-work-orders', NULL, NULL, 500),
  ('mega.flow_work_order.edit', '编辑流式工单', 'action', 'mega', 'flow_work_order', 'edit', NULL, 'mega.flow_work_order.edit_button', 'mega.page.flow_work_order', 510),
  ('mega.flow_work_order.dispatch', '发送流式工单', 'action', 'mega', 'flow_work_order', 'dispatch', NULL, 'mega.flow_work_order.dispatch_button', 'mega.page.flow_work_order', 520),
  ('system.page.user', '用户管理页面', 'page', 'system', 'user', 'view', '/system/user-permission', NULL, NULL, 900),
  ('system.page.role', '角色管理页面', 'page', 'system', 'role', 'view', '/system/user-permission', NULL, NULL, 910),
  ('system.page.permission', '权限管理页面', 'page', 'system', 'permission', 'view', '/system/user-permission', NULL, NULL, 920),
  ('system.page.operation_log', '操作日志页面', 'page', 'system', 'operation_log', 'view', '/system/user-permission', NULL, NULL, 930),
  ('system.page.feature', '系统功能页面', 'page', 'system', 'feature', 'view', '/system/features', NULL, NULL, 940),
  ('system.user.manage', '管理用户', 'action', 'system', 'user', 'manage', NULL, 'system.user.manage_button', 'system.page.user', 1000),
  ('system.role.manage', '管理角色', 'action', 'system', 'role', 'manage', NULL, 'system.role.manage_button', 'system.page.role', 1010),
  ('system.permission.manage', '管理权限点', 'action', 'system', 'permission', 'manage', NULL, 'system.permission.manage_button', 'system.page.permission', 1020),
  ('system.operation_log.view', '查看操作日志', 'action', 'system', 'operation_log', 'view', NULL, 'system.operation_log.view_button', 'system.page.operation_log', 1030),
  ('system.feature.manage', '管理系统功能', 'action', 'system', 'feature', 'manage', NULL, 'system.feature.manage_button', 'system.page.feature', 1040);

-- 仅登记「会写操作日志」的写接口（POST/PUT/PATCH/DELETE + 非 page/view 权限）。
-- GET / 列表查询即使登记也不会被审计中间件记录，故不写入本表。
INSERT IGNORE INTO sys_permission_api
  (permission_code, method, path_pattern, description)
VALUES
  ('serum.project.create', 'POST', '/api/serum/save', '新建免疫项目'),
  ('serum.project.edit', 'POST', '/api/serum/save', '编辑免疫项目'),
  ('serum.project.edit', 'POST', '/api/serum/update_lab_notebook', '更新实验记录本'),
  ('serum.project.edit_all', 'POST', '/api/serum/update_lab_notebook', '更新他人实验记录本'),
  ('serum.project.delete', 'POST', '/api/serum/delete', '删除免疫项目'),
  ('serum.status.update', 'POST', '/api/serum/update_status', '快速修改状态'),
  ('serum.cage.update', 'POST', '/api/serum/update_cage_position', '更新笼位信息'),
  ('serum.cell.prep_status.update', 'POST', '/api/serum/project/prep_status', '更新细胞制备状态'),
  ('serum.status.auto_update', 'POST', '/api/serum/auto_update_status', '自动更新状态'),
  ('serum.mouse.export', 'POST', '/api/serum/export_mouse', '导出小鼠免疫数据'),
  ('serum.file.manage', 'POST', '/api/serum/titer/file/save', '上传效价文件'),
  ('serum.file.manage', 'POST', '/api/serum/titer/file/delete', '删除效价文件'),
  ('serum.file.manage', 'POST', '/api/serum/titer/file/rename', '重命名效价文件'),
  ('serum.file.manage', 'POST', '/api/serum/titer/file/replace', '替换效价文件'),
  ('serum.titer.edit', 'POST', '/api/serum/titer/target/save', '保存效价标靶'),
  ('serum.titer.edit', 'POST', '/api/serum/titer/pc/save', '保存效价阳性对照'),
  ('serum.titer.edit', 'POST', '/api/serum/titer/plate/save', '保存FACS板'),
  ('serum.titer.edit', 'POST', '/api/serum/titer/plate/delete', '删除FACS板'),
  ('serum.titer.edit', 'POST', '/api/serum/titer/elisa/plate/save', '保存ELISA板'),
  ('serum.titer.edit', 'POST', '/api/serum/titer/elisa/plate/delete', '删除ELISA板'),
  ('serum.titer_order.edit', 'POST', '/api/serum/titer/order/save', '保存效价工单'),
  ('serum.titer_order.delete', 'POST', '/api/serum/titer/order/delete', '删除效价工单'),
  ('serum.project.edit', 'POST', '/api/serum/mouse-registry/save', '保存小鼠鼠号明细'),
  ('mega.flow_work_order.edit', 'POST', '/api/mega-automation/flow-work-orders/save', '保存流式工单'),
  ('mega.flow_work_order.edit', 'POST', '/api/mega-automation/flow-work-orders/{order_id}/validate', '校验流式工单'),
  ('mega.flow_work_order.dispatch', 'POST', '/api/mega-automation/flow-work-orders/{order_id}/dispatch', '发送流式工单'),
  ('mega.flow_work_order.dispatch', 'POST', '/api/mega-automation/flow-work-orders/{order_id}/pause', '请求暂停流式工单'),
  ('mega.flow_work_order.dispatch', 'POST', '/api/mega-automation/flow-work-orders/{order_id}/pause-ack', '确认设备已暂停'),
  ('mega.flow_work_order.dispatch', 'POST', '/api/mega-automation/flow-work-orders/{order_id}/resume', '请求恢复流式工单'),
  ('mega.flow_work_order.dispatch', 'POST', '/api/mega-automation/flow-work-orders/{order_id}/resume-ack', '确认设备已恢复'),
  ('mega.flow_work_order.dispatch', 'POST', '/api/mega-automation/flow-work-orders/{order_id}/confirm-execution', '确认流式工单开始执行'),
  ('mega.flow_work_order.dispatch', 'POST', '/api/mega-automation/flow-work-orders/{order_id}/complete', '完成流式工单'),
  ('mega.flow_work_order.dispatch', 'POST', '/api/mega-automation/flow-work-orders/{order_id}/fail', '标记流式工单执行失败'),
  ('mega.flow_work_order.edit', 'POST', '/api/mega-automation/flow-work-orders/{order_id}/delete', '删除流式工单'),
  ('mega.flow_work_order.edit', 'POST', '/api/mega-automation/flow-work-orders/{order_id}/cancel', '作废流式工单'),
  ('system.user.manage', 'POST', '/api/system/users/save', '新增或编辑用户'),
  ('system.user.manage', 'POST', '/api/system/users/reset_password', '重置用户密码'),
  ('system.user.manage', 'POST', '/api/system/users/delete', '删除用户'),
  ('system.user.manage', 'POST', '/api/system/users/batch_roles', '批量设置用户角色'),
  ('system.role.manage', 'POST', '/api/system/roles/save', '新增或编辑角色'),
  ('system.role.manage', 'POST', '/api/system/roles/delete', '删除角色'),
  ('system.permission.manage', 'POST', '/api/system/permission_bundles/save', '新增或编辑权限包'),
  ('system.permission.manage', 'POST', '/api/system/permission_bundles/delete', '删除权限包'),
  ('system.permission.manage', 'POST', '/api/system/users/{user_id}/permission_overrides', '保存用户个人权限覆盖'),
  ('system.feature.manage', 'POST', '/api/system/features/save', '保存系统功能配置'),
  ('system.feature.manage', 'POST', '/api/system/features/jobs/run', '手动执行定时任务');

INSERT IGNORE INTO sys_feature_flag
  (code, name, category, description, enabled, visible, sort_order, config)
VALUES
  ('menu.discovery', '千鼠万抗', 'menu', '控制千鼠万抗父级菜单显示', 1, 1, 5, JSON_OBJECT('path', '/discovery', 'icon', 'lucide:network')),
  ('menu.discovery.target_library', '靶点情报', 'menu', '控制靶点情报页面显示', 1, 1, 10, JSON_OBJECT('path', '/discovery/targets', 'icon', 'lucide:database', 'parent_code', 'menu.discovery')),
  ('menu.serum', '免疫实验菜单', 'menu', '控制免疫实验模块菜单显示', 1, 1, 10, JSON_OBJECT('path', '/serum', 'icon', 'lucide:test-tube')),
  ('menu.serum.list', '免疫实验列表', 'menu', '控制免疫实验列表菜单显示', 1, 1, 10, JSON_OBJECT('path', '/serum/list', 'icon', 'lucide:list', 'parent_code', 'menu.serum')),
  ('menu.serum.titer_order', '效价实验列表', 'menu', '控制效价实验列表菜单显示', 1, 1, 20, JSON_OBJECT('path', '/serum/titer-orders', 'icon', 'lucide:clipboard-list', 'parent_code', 'menu.serum')),
  ('menu.mega_automation', '镁伽自动化菜单', 'menu', '控制镁伽自动化模块菜单显示', 1, 1, 50, JSON_OBJECT('path', '/mega-automation', 'icon', 'lucide:workflow')),
  ('menu.mega_automation.flow_work_orders', '流式工单总览', 'menu', '控制流式工单总览页面显示', 1, 1, 10, JSON_OBJECT('path', '/mega-automation/flow-work-orders', 'icon', 'lucide:clipboard-list', 'parent_code', 'menu.mega_automation')),
  ('menu.system', '系统管理', 'menu', '控制系统管理父级菜单显示', 1, 1, 90, JSON_OBJECT('path', '/system', 'icon', 'lucide:settings')),
  ('menu.system.user_permission', '用户权限菜单', 'menu', '控制系统管理下用户权限页面显示', 1, 1, 10, JSON_OBJECT('path', '/system/user-permission', 'icon', 'lucide:shield-check', 'parent_code', 'menu.system')),
  ('menu.system.features', '系统功能菜单', 'menu', '控制系统管理下系统功能页面显示', 1, 1, 20, JSON_OBJECT('path', '/system/features', 'icon', 'lucide:sliders-horizontal', 'parent_code', 'menu.system')),
  ('feature.yunzhijia_auto_provision', '云之家自动创建用户', 'feature', '允许云之家登录时自动创建未绑定用户', 0, 1, 110, JSON_OBJECT()),
  ('feature.drm_file_security', 'DRM 文件安全模块', 'feature', '控制上传自动解密、下载前加密等 DRM 文件安全能力', 0, 1, 120, JSON_OBJECT()),
  ('job.employee_profile_sync', '员工资料定时同步', 'job', '每天 00:30 同步外部员工基础资料', 1, 1, 200, JSON_OBJECT('hour', 0, 'minute', 30, 'cron', '30 0 * * *', 'restart_required', true)),
  ('job.target_master_sync', '靶点主数据定时同步', 'job', '每天 00:45 同步外部靶点主数据', 1, 1, 205, JSON_OBJECT('hour', 0, 'minute', 45, 'cron', '45 0 * * *', 'restart_required', true)),
  ('job.serum_auto_update_status', '免疫状态自动更新', 'job', '每天 01:00 自动更新免疫实验状态', 1, 1, 210, JSON_OBJECT('hour', 1, 'minute', 0, 'cron', '0 1 * * *', 'restart_required', true)),
  ('job.mega_labillion_status_sync', '镁伽工单状态同步', 'job', '每天 02:00 同步镁伽非终态工单状态', 1, 1, 220, JSON_OBJECT('hour', 2, 'minute', 0, 'cron', '0 2 * * *', 'restart_required', true));

-- =============================================================================
-- 权限包 / 角色（仅示例三档：访客、业务员、系统管理；生产环境完全自定义）
-- =============================================================================

INSERT IGNORE INTO sys_permission_bundle (code, name, module, description, sort_order) VALUES
  ('guest', '访客', 'common', '示例：各业务模块页面只读', 10),
  ('operator', '业务员', 'business', '示例：血清与镁伽常用编辑权限', 100),
  ('system_admin', '系统管理', 'system', '示例：系统管理模块全部权限', 900);

INSERT IGNORE INTO sys_permission_bundle_item (bundle_code, permission_code) VALUES
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
  ('guest', 'system.page.operation_log'),
  ('guest', 'system.page.feature'),
  ('guest', 'system.operation_log.view'),
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
-- ) COMMENT='细胞样本（外部库，只读）';

-- =============================================================================
-- 外部员工库 EMPLOYEE_DB_URL：org_emp / org_depart（employee_sync.py，勿在主库执行，仅备查）
-- =============================================================================
-- CREATE TABLE IF NOT EXISTS org_depart (
--   id BIGINT NOT NULL COMMENT '部门ID',
--   sname VARCHAR(255) NULL COMMENT '部门名称',
--   top_id BIGINT NULL COMMENT '上级部门ID',
--   PRIMARY KEY (id)
-- ) COMMENT='部门（外部库，只读）';
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
--   depart_id BIGINT NULL COMMENT '部门ID(org_depart.id)',
--   PRIMARY KEY (id),
--   KEY idx_org_emp_depart (depart_id),
--   KEY idx_org_emp_openid (cloud_open_id)
-- ) COMMENT='员工（外部库，只读）';
--
-- 同一 EMPLOYEE_DB_URL 外部平台库还包含正式靶点表
-- xdida_platform_biocytogen.target；本系统只读全量同步至主库 target，
-- 字段选择与同步规则见 modules/system/target_sync.py，勿修改外部表。
