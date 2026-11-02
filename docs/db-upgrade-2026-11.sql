-- 2026-11 库结构升级：旧环境照此补齐到 vita-database.sql 的结构（正式库 2026-11-02 已执行）。
-- 逐段执行；MySQL 的 DDL 不能回滚，执行前先备份。已存在的列、已删掉的索引对应语句会报错，跳过即可。

-- 1. 合成单两个检测状态列和亲和力人员（旧库没有时才加）
ALTER TABLE discovery_synthesis_order
  ADD COLUMN affinity_status VARCHAR(32) NULL COMMENT '亲和力检测状态' AFTER arrival_date,
  ADD COLUMN affinity_owner VARCHAR(64) NULL COMMENT '亲和力人员' AFTER affinity_status,
  ADD COLUMN flow_status VARCHAR(32) NULL COMMENT '流式检测状态' AFTER flow_date;

-- 2. 日期列 VARCHAR → DATE
-- 2.1 先查不合规的值（应为 0 行；有的话先按原意改成 YYYY-MM-DD 再继续），示例：
--   SELECT id, start_date FROM serum_imm_project
--   WHERE TRIM(start_date) <> '' AND start_date NOT REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}$';
-- 2.2 空串置 NULL（DATE 列不收空串）
UPDATE discovery_workbench SET harvest_date = NULL WHERE TRIM(harvest_date) = '';
UPDATE discovery_workbench SET boost_date = NULL WHERE TRIM(boost_date) = '';
UPDATE discovery_synthesis_order SET synthetic_date = NULL WHERE TRIM(synthetic_date) = '';
UPDATE discovery_synthesis_order SET arrival_date = NULL WHERE TRIM(arrival_date) = '';
UPDATE discovery_synthesis_order SET flow_date = NULL WHERE TRIM(flow_date) = '';
UPDATE discovery_synthesis_order SET affinity_date = NULL WHERE TRIM(affinity_date) = '';
UPDATE serum_imm_project SET start_date = NULL WHERE TRIM(start_date) = '';
UPDATE serum_imm_workbench SET start_date = NULL WHERE TRIM(start_date) = '';
UPDATE serum_imm_workbench SET mouse_birth_date = NULL WHERE TRIM(mouse_birth_date) = '';
UPDATE serum_imm_workbench SET mouse_arrive_date = NULL WHERE TRIM(mouse_arrive_date) = '';
UPDATE serum_imm_step SET date_actual = NULL WHERE TRIM(date_actual) = '';
UPDATE serum_titer_order SET blood_collection_date = NULL WHERE TRIM(blood_collection_date) = '';
-- 2.3 改列类型（旧版后端会写空串，改完尽快上新版）
ALTER TABLE discovery_workbench
  MODIFY COLUMN harvest_date DATE NULL COMMENT '剖鼠取细胞日',
  MODIFY COLUMN boost_date DATE NULL COMMENT '冲击免日期';
ALTER TABLE discovery_synthesis_order
  MODIFY COLUMN synthetic_date DATE NULL COMMENT '合成日期',
  MODIFY COLUMN arrival_date DATE NULL COMMENT '到货日期',
  MODIFY COLUMN flow_date DATE NULL COMMENT '流式日期',
  MODIFY COLUMN affinity_date DATE NULL COMMENT '亲和力日期';
ALTER TABLE serum_imm_project
  MODIFY COLUMN start_date DATE NULL COMMENT '项目开始日期';
ALTER TABLE serum_imm_workbench
  MODIFY COLUMN start_date DATE NULL COMMENT '项目开始日期',
  MODIFY COLUMN mouse_birth_date DATE NULL COMMENT '出生日期',
  MODIFY COLUMN mouse_arrive_date DATE NULL COMMENT '到鼠时间';
ALTER TABLE serum_imm_step
  MODIFY COLUMN date_actual DATE NULL COMMENT '实际日期';
ALTER TABLE serum_titer_order
  MODIFY COLUMN blood_collection_date DATE NULL COMMENT '采血日期';

-- 3. 索引
-- 3.1 同一列只是名字不同的，用 RENAME INDEX 改名（只改元数据），不要 DROP 后重建。
--     旧库里是 MySQL 自动名或 ix_ 前缀的：
ALTER TABLE molecular_library_order
  RENAME INDEX ix_molecular_library_order_library_code TO idx_molecular_library_order_library_code,
  RENAME INDEX ix_molecular_library_order_source_discovery_id TO idx_molecular_library_order_source_discovery_id;
ALTER TABLE molecular_library_result_package
  RENAME INDEX ix_molecular_library_result_package_owner_order_id TO idx_molecular_library_result_package_owner_order_id;
ALTER TABLE molecular_library_result_file
  RENAME INDEX ix_molecular_library_result_file_package_id TO idx_molecular_library_result_file_package_id;
ALTER TABLE molecular_library_result_link
  RENAME INDEX ix_molecular_library_result_link_order_id TO idx_molecular_library_result_link_order_id;
ALTER TABLE serum_file RENAME INDEX idx_experiment TO idx_serum_file_experiment_id;
ALTER TABLE serum_facs_plate RENAME INDEX idx_experiment TO idx_serum_facs_plate_experiment_id;
ALTER TABLE serum_elisa_plate RENAME INDEX idx_experiment TO idx_serum_elisa_plate_experiment_id;
ALTER TABLE sys_user RENAME INDEX username TO uk_sys_user_username, RENAME INDEX openid TO uk_sys_user_openid;
ALTER TABLE sys_role RENAME INDEX code TO uk_sys_role_code;
ALTER TABLE sys_permission RENAME INDEX code TO uk_sys_permission_code;
ALTER TABLE sys_permission_bundle RENAME INDEX code TO uk_sys_permission_bundle_code;
ALTER TABLE sys_feature_flag RENAME INDEX code TO uk_sys_feature_flag_code;
-- 3.2 新增：按实验号整批读写的两张表
ALTER TABLE serum_titer_pc ADD INDEX idx_serum_titer_pc_experiment_id (experiment_id);
ALTER TABLE serum_titer_target ADD INDEX idx_serum_titer_target_experiment_id (experiment_id);
-- 3.3 删除：低区分度、小配置表、被唯一键前缀覆盖、只服务 LIKE '%x%' 的索引
ALTER TABLE discovery_synthesis_order DROP INDEX idx_discovery_synthesis_order_affinity_owner;
ALTER TABLE mega_flow_work_order DROP INDEX idx_mega_flow_work_order_status;
ALTER TABLE molecular_library_order
  DROP INDEX ix_molecular_library_order_build_type,
  DROP INDEX ix_molecular_library_order_library_batch_no,
  DROP INDEX ix_molecular_library_order_sample_source,
  DROP INDEX ix_molecular_library_order_sample_type,
  DROP INDEX ix_molecular_library_order_source_project_code,
  DROP INDEX ix_molecular_library_order_status;
ALTER TABLE molecular_library_result_link DROP INDEX ix_molecular_library_result_link_file_id;
ALTER TABLE molecular_primer_index_catalog DROP INDEX idx_molecular_primer_index_family;
ALTER TABLE order_sync DROP INDEX idx_order_sync_received_at, DROP INDEX idx_order_sync_status;
ALTER TABLE serum_imm_workbench
  DROP INDEX idx_serum_imm_workbench_owner,
  DROP INDEX idx_serum_imm_workbench_plan_status,
  DROP INDEX idx_serum_imm_workbench_pm,
  DROP INDEX idx_serum_imm_workbench_project_code,
  DROP INDEX idx_serum_imm_workbench_sort_order,
  DROP INDEX idx_serum_imm_workbench_target_name;
ALTER TABLE sys_operation_log
  DROP INDEX idx_sys_operation_log_source_time,
  DROP INDEX idx_sys_operation_log_target_time,
  DROP INDEX idx_sys_operation_log_user_time;
ALTER TABLE sys_operation_log_item DROP INDEX idx_sys_operation_log_item_entity;
ALTER TABLE sys_permission
  DROP INDEX idx_sys_permission_module,
  DROP INDEX idx_sys_permission_parent,
  DROP INDEX idx_sys_permission_resource_action,
  DROP INDEX idx_sys_permission_status,
  DROP INDEX idx_sys_permission_type;
ALTER TABLE sys_permission_api DROP INDEX idx_sys_permission_api_path, DROP INDEX idx_sys_permission_api_permission;
ALTER TABLE sys_permission_bundle DROP INDEX idx_sys_permission_bundle_module, DROP INDEX idx_sys_permission_bundle_status;
ALTER TABLE sys_permission_bundle_item
  DROP INDEX idx_sys_permission_bundle_item_bundle,
  DROP INDEX idx_sys_permission_bundle_item_permission;
ALTER TABLE sys_role DROP INDEX idx_sys_role_status;
ALTER TABLE sys_role_permission_bundle
  DROP INDEX idx_sys_role_permission_bundle_bundle,
  DROP INDEX idx_sys_role_permission_bundle_role;
ALTER TABLE sys_user
  DROP INDEX idx_sys_user_department,
  DROP INDEX idx_sys_user_employment_status,
  DROP INDEX idx_sys_user_gender,
  DROP INDEX idx_sys_user_group_name,
  DROP INDEX idx_sys_user_openid,
  DROP INDEX idx_sys_user_status;
ALTER TABLE sys_user_permission_override DROP INDEX idx_sys_user_permission_override_user;
ALTER TABLE sys_user_role DROP INDEX idx_sys_user_role_role, DROP INDEX idx_sys_user_role_user;
ALTER TABLE target
  DROP INDEX idx_target_human_gene_name,
  DROP INDEX idx_target_mouse_gene_name,
  DROP INDEX idx_target_name,
  DROP INDEX idx_target_status_type;
-- 3.4 核对：每张表的索引名应与 vita-database.sql 的 KEY 完全一致
--   SELECT TABLE_NAME, INDEX_NAME FROM information_schema.STATISTICS
--   WHERE TABLE_SCHEMA = DATABASE() AND INDEX_NAME <> 'PRIMARY' GROUP BY TABLE_NAME, INDEX_NAME ORDER BY 1, 2;

-- 4. 合成单检测状态回填：旧版 One 同步只写总状态。新版后端上线后执行，可重复执行。
UPDATE discovery_synthesis_order
SET affinity_status = '亲和力待检测',
    flow_status = IF(target_type = '分泌型', '流式不适用', '流式待检测')
WHERE status = '待检测'
  AND affinity_status IS NULL
  AND flow_status IS NULL
  AND affinity_date IS NULL
  AND flow_date IS NULL
  AND COALESCE(TRIM(affinity_owner), '') = ''
  AND COALESCE(TRIM(report_reason), '') = '';
