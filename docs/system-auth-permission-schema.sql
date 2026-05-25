-- Antibody Forge：认证与权限表结构 + 种子数据
-- 文档：docs/auth-permissions.md
-- 说明：需在 bbctg_vita 主库手动执行；后端不会自动建表/迁移。

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
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  KEY idx_sys_feature_flag_category (category),
  KEY idx_sys_feature_flag_enabled (enabled),
  KEY idx_sys_feature_flag_visible (visible)
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

INSERT IGNORE INTO sys_permission
  (code, name, type, module, resource, action, route_path, ui_key, parent_code, sort_order)
VALUES
  ('serum.page.list', '血清实验列表', 'page', 'serum', 'project', 'view', '/serum/list', NULL, NULL, 100),
  ('serum.page.detail', '血清实验详情', 'page', 'serum', 'project', 'view_detail', '/serum/detail', NULL, NULL, 110),
  ('serum.page.edit', '血清实验编辑', 'page', 'serum', 'project', 'edit_page', '/serum/edit', NULL, NULL, 120),
  ('serum.page.titer', '血清效价数据', 'page', 'serum', 'titer', 'view', '/serum/titer', NULL, NULL, 130),
  ('serum.page.cell', '细胞库存查询', 'page', 'serum', 'cell', 'view', '/serum/cell', NULL, NULL, 140),
  ('serum.project.create', '新建血清项目', 'action', 'serum', 'project', 'create', NULL, 'serum.project.create_button', 'serum.page.list', 200),
  ('serum.project.edit', '编辑本人负责血清项目', 'action', 'serum', 'project', 'edit', NULL, 'serum.project.edit_button', 'serum.page.edit', 210),
  ('serum.project.edit_all', '编辑全部血清项目', 'action', 'serum', 'project', 'edit_all', NULL, 'serum.project.edit_all_button', 'serum.page.edit', 215),
  ('serum.project.delete', '删除血清项目', 'action', 'serum', 'project', 'delete', NULL, 'serum.project.delete_button', 'serum.page.edit', 220),
  ('serum.status.update', '快速修改状态', 'action', 'serum', 'project_status', 'update', NULL, 'serum.status.update_button', 'serum.page.list', 230),
  ('serum.status.auto_update', '自动更新状态', 'action', 'serum', 'project_status', 'auto_update', NULL, 'serum.status.auto_update_button', 'serum.page.list', 240),
  ('serum.mouse.export', '导出小鼠免疫数据', 'action', 'serum', 'mouse', 'export', NULL, 'serum.mouse.export_button', 'serum.page.list', 250),
  ('serum.cage.update', '更新笼位信息', 'action', 'serum', 'cage', 'update', NULL, 'serum.cage.update_button', 'serum.page.list', 260),
  ('serum.titer.edit', '编辑效价数据', 'action', 'serum', 'titer', 'edit', NULL, 'serum.titer.edit_button', 'serum.page.titer', 270),
  ('serum.titer.edit_all', '编辑全部项目效价数据', 'action', 'serum', 'titer', 'edit_all', NULL, 'serum.titer.edit_all_button', 'serum.page.titer', 275),
  ('serum.file.manage', '管理效价文件', 'action', 'serum', 'file', 'manage', NULL, 'serum.file.manage_button', 'serum.page.titer', 280),
  ('serum.cell.view', '查看细胞库存', 'action', 'serum', 'cell', 'view_inventory', NULL, 'serum.cell.view_button', 'serum.page.cell', 290),
  ('serum.cell.prep_status.update', '更新细胞制备状态', 'action', 'serum', 'cell', 'update_prep_status', NULL, 'serum.cell.prep_status.update_button', 'serum.page.cell', 300),
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

INSERT IGNORE INTO sys_permission_api
  (permission_code, method, path_pattern, description)
VALUES
  ('serum.project.create', 'POST', '/api/serum/save', '新建血清项目'),
  ('serum.project.edit', 'POST', '/api/serum/save', '编辑血清项目'),
  ('serum.project.delete', 'POST', '/api/serum/delete', '删除血清项目'),
  ('serum.status.update', 'POST', '/api/serum/update_status', '快速修改状态'),
  ('serum.cage.update', 'POST', '/api/serum/update_cage_position', '更新笼位信息'),
  ('serum.cell.prep_status.update', 'POST', '/api/serum/project/prep_status', '更新细胞制备状态'),
  ('serum.status.auto_update', 'POST', '/api/serum/auto_update_status', '自动更新状态'),
  ('serum.mouse.export', 'POST', '/api/serum/export_mouse', '导出小鼠免疫数据'),
  ('serum.file.manage', 'POST', '/api/serum/titer/file/save', '上传效价文件'),
  ('serum.file.manage', 'POST', '/api/serum/titer/file/delete', '删除效价文件'),
  ('serum.file.manage', 'POST', '/api/serum/titer/file/rename', '重命名效价文件'),
  ('serum.file.manage', 'POST', '/api/serum/titer/file/replace', '替换效价文件'),
  ('serum.titer.edit', 'POST', '/api/serum/titer/target/save', '保存效价靶点'),
  ('serum.titer.edit', 'POST', '/api/serum/titer/pc/save', '保存效价阳性对照'),
  ('serum.titer.edit', 'POST', '/api/serum/titer/plate/save', '保存FACS板'),
  ('serum.titer.edit', 'POST', '/api/serum/titer/plate/delete', '删除FACS板'),
  ('serum.titer.edit', 'POST', '/api/serum/titer/elisa/plate/save', '保存ELISA板'),
  ('serum.titer.edit', 'POST', '/api/serum/titer/elisa/plate/delete', '删除ELISA板'),
  ('system.user.manage', 'POST', '/api/system/users/save', '新增或编辑用户'),
  ('system.user.manage', 'POST', '/api/system/users/reset_password', '重置用户密码'),
  ('system.user.manage', 'POST', '/api/system/users/delete', '删除用户'),
  ('system.user.manage', 'POST', '/api/system/users/batch_roles', '批量设置用户角色'),
  ('system.role.manage', 'POST', '/api/system/roles/save', '新增或编辑角色'),
  ('system.role.manage', 'POST', '/api/system/roles/delete', '删除角色'),
  ('system.permission.manage', 'POST', '/api/system/permission_bundles/save', '新增或编辑权限包'),
  ('system.permission.manage', 'POST', '/api/system/permission_bundles/delete', '删除权限包'),
  ('system.permission.manage', 'POST', '/api/system/users/{user_id}/permission_overrides', '保存用户个人权限覆盖'),
  ('system.operation_log.view', 'GET', '/api/system/operation_logs', '查看操作日志'),
  ('system.feature.manage', 'GET', '/api/system/features', '查看系统功能配置'),
  ('system.feature.manage', 'GET', '/api/system/features/job_logs', '查看定时任务运行日志'),
  ('system.feature.manage', 'GET', '/api/system/features/system_status', '查看系统基础状态'),
  ('system.feature.manage', 'POST', '/api/system/features/save', '保存系统功能配置');

INSERT IGNORE INTO sys_permission_bundle (code, name, module, description, sort_order) VALUES
  ('serum_readonly', '查看', 'serum', '查看血清列表、详情、效价和细胞库存', 100),
  ('serum_scheme_edit', '方案编辑', 'serum', '创建和编辑血清方案，维护状态、笼位和细胞制备状态', 110),
  ('serum_titer_edit', '效价编辑', 'serum', '维护效价数据、FACS 板和效价附件', 120),
  ('serum_admin', '血清管理员', 'serum', '包含血清相关全部页面和操作权限', 190),
  ('system_admin', '系统管理员', 'system', '管理用户、角色权限、权限点和操作日志', 900);

INSERT IGNORE INTO sys_permission_bundle_item (bundle_code, permission_code) VALUES
  ('serum_readonly', 'serum.page.list'),
  ('serum_readonly', 'serum.page.detail'),
  ('serum_readonly', 'serum.page.titer'),
  ('serum_readonly', 'serum.page.cell'),
  ('serum_readonly', 'serum.cell.view'),
  ('serum_scheme_edit', 'serum.page.list'),
  ('serum_scheme_edit', 'serum.page.detail'),
  ('serum_scheme_edit', 'serum.page.edit'),
  ('serum_scheme_edit', 'serum.project.create'),
  ('serum_scheme_edit', 'serum.project.edit'),
  ('serum_scheme_edit', 'serum.status.update'),
  ('serum_scheme_edit', 'serum.cage.update'),
  ('serum_scheme_edit', 'serum.cell.prep_status.update'),
  ('serum_titer_edit', 'serum.page.list'),
  ('serum_titer_edit', 'serum.page.detail'),
  ('serum_titer_edit', 'serum.page.titer'),
  ('serum_titer_edit', 'serum.titer.edit'),
  ('serum_titer_edit', 'serum.titer.edit_all'),
  ('serum_titer_edit', 'serum.file.manage'),
  ('serum_admin', 'serum.page.list'),
  ('serum_admin', 'serum.page.detail'),
  ('serum_admin', 'serum.page.edit'),
  ('serum_admin', 'serum.page.titer'),
  ('serum_admin', 'serum.page.cell'),
  ('serum_admin', 'serum.project.create'),
  ('serum_admin', 'serum.project.edit'),
  ('serum_admin', 'serum.project.edit_all'),
  ('serum_admin', 'serum.project.delete'),
  ('serum_admin', 'serum.status.update'),
  ('serum_admin', 'serum.status.auto_update'),
  ('serum_admin', 'serum.mouse.export'),
  ('serum_admin', 'serum.cage.update'),
  ('serum_admin', 'serum.titer.edit'),
  ('serum_admin', 'serum.titer.edit_all'),
  ('serum_admin', 'serum.file.manage'),
  ('serum_admin', 'serum.cell.view'),
  ('serum_admin', 'serum.cell.prep_status.update'),
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

INSERT IGNORE INTO sys_feature_flag
  (code, name, category, description, enabled, visible, sort_order, config)
VALUES
  ('menu.serum', '血清实验菜单', 'menu', '控制血清实验模块菜单显示', 1, 1, 10, JSON_OBJECT('path', '/serum', 'icon', 'lucide:test-tube')),
  ('menu.system', '系统管理', 'menu', '控制系统管理父级菜单显示', 1, 1, 90, JSON_OBJECT('path', '/system', 'icon', 'lucide:settings')),
  ('menu.system.user_permission', '用户权限菜单', 'menu', '控制系统管理下用户权限页面显示', 1, 1, 10, JSON_OBJECT('path', '/system/user-permission', 'icon', 'lucide:shield-check', 'parent_code', 'menu.system')),
  ('menu.system.features', '系统功能菜单', 'menu', '控制系统管理下系统功能页面显示', 1, 1, 20, JSON_OBJECT('path', '/system/features', 'icon', 'lucide:sliders-horizontal', 'parent_code', 'menu.system')),
  ('feature.yunzhijia_auto_provision', '云之家自动创建用户', 'feature', '允许云之家登录时自动创建未绑定用户', 0, 1, 110, JSON_OBJECT()),
  ('feature.drm_file_security', 'DRM 文件安全模块', 'feature', '控制上传自动解密、下载前加密等 DRM 文件安全能力', 0, 1, 120, JSON_OBJECT()),
  ('job.employee_profile_sync', '员工资料定时同步', 'job', '每天 00:30 同步外部员工基础资料', 1, 1, 200, JSON_OBJECT('hour', 0, 'minute', 30, 'cron', '30 0 * * *', 'restart_required', true)),
  ('job.serum_auto_update_status', '血清状态自动更新', 'job', '每天 01:00 自动更新血清实验状态', 1, 1, 210, JSON_OBJECT('hour', 1, 'minute', 0, 'cron', '0 1 * * *', 'restart_required', true));

INSERT IGNORE INTO sys_role (code, name, description, sort_order) VALUES
  ('super_admin', '超级管理员', '拥有系统所有权限', 1),
  ('serum_admin', '血清管理员', '管理血清实验相关功能', 10),
  ('serum_user', '血清实验用户', '可创建和编辑本人负责项目', 20),
  ('readonly', '只读用户', '仅可查看数据', 90);

INSERT IGNORE INTO sys_role_permission_bundle (role_id, bundle_code)
SELECT r.id, b.code FROM sys_role r JOIN sys_permission_bundle b WHERE r.code = 'super_admin';

INSERT IGNORE INTO sys_role_permission_bundle (role_id, bundle_code)
SELECT r.id, b.code
FROM sys_role r
JOIN sys_permission_bundle b
WHERE r.code = 'serum_admin' AND b.code = 'serum_admin';

INSERT IGNORE INTO sys_role_permission_bundle (role_id, bundle_code)
SELECT r.id, b.code
FROM sys_role r
JOIN sys_permission_bundle b
WHERE r.code = 'serum_user' AND b.code IN ('serum_scheme_edit', 'serum_titer_edit');

INSERT IGNORE INTO sys_role_permission_bundle (role_id, bundle_code)
SELECT r.id, b.code
FROM sys_role r
JOIN sys_permission_bundle b
WHERE r.code = 'readonly' AND b.code = 'serum_readonly';

-- 首个超级管理员需要先生成 password_hash，再替换下面的占位符执行。
-- 生成方式：
--   python -c "from modules.auth.security import hash_password; print(hash_password('你的密码'))"
-- INSERT INTO sys_user (username, display_name, password_hash, status, is_superuser)
-- VALUES ('admin', '系统管理员', '替换为生成的 password_hash', 'active', TRUE);
-- INSERT INTO sys_user_role (user_id, role_id)
-- SELECT u.id, r.id FROM sys_user u JOIN sys_role r
-- WHERE u.username = 'admin' AND r.code = 'super_admin';

-- -----------------------------------------------------------------------------
-- 可选：表已由旧脚本创建且缺少列/表注释时，在 MySQL 上执行一次以与 ORM 及上文 DDL 对齐
-- （新建库执行上方 CREATE TABLE 即可，无需再跑本节）
-- -----------------------------------------------------------------------------
ALTER TABLE sys_feature_flag
  MODIFY id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  MODIFY code VARCHAR(128) NOT NULL COMMENT '功能编码',
  MODIFY name VARCHAR(128) NOT NULL COMMENT '功能名称',
  MODIFY category VARCHAR(32) NOT NULL COMMENT '功能分类',
  MODIFY description VARCHAR(255) NULL COMMENT '功能说明',
  MODIFY enabled TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
  MODIFY visible TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否显示',
  MODIFY sort_order INT NOT NULL DEFAULT 0 COMMENT '排序值',
  MODIFY config JSON NULL COMMENT '扩展配置',
  MODIFY created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  MODIFY updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  COMMENT = '运行时功能配置（菜单可见性、功能开关、定时任务参数、站点偏好等）';

ALTER TABLE sys_job_run_log
  MODIFY id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  MODIFY job_code VARCHAR(128) NOT NULL COMMENT '任务编码',
  MODIFY job_name VARCHAR(128) NOT NULL COMMENT '任务名称',
  MODIFY started_at DATETIME NULL COMMENT '开始时间',
  MODIFY finished_at DATETIME NULL COMMENT '结束时间',
  MODIFY duration_ms INT NULL COMMENT '耗时毫秒',
  MODIFY result VARCHAR(16) NOT NULL DEFAULT 'success' COMMENT '执行结果',
  MODIFY summary VARCHAR(255) NULL COMMENT '结果摘要',
  MODIFY detail JSON NULL COMMENT '执行详情',
  MODIFY error_message TEXT NULL COMMENT '错误信息',
  MODIFY created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  COMMENT = '定时任务运行日志（起止时间、耗时、结果摘要与结构化详情）';
