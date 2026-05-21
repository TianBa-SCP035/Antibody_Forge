-- ELISA 效价板表结构（开发期 ALTER，无旧数据）
ALTER TABLE serum_elisa_plate COMMENT = 'ELISA效价板配置（含吸光度1读数；吸光度2不入库）';

ALTER TABLE serum_elisa_plate
  MODIFY COLUMN id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  MODIFY COLUMN experiment_id VARCHAR(64) NOT NULL COMMENT '实验ID',
  MODIFY COLUMN qr_code VARCHAR(128) NULL COMMENT '二维码编号',
  MODIFY COLUMN excel_file_id BIGINT NULL COMMENT 'Excel文件id(serum_file)',
  MODIFY COLUMN immune_stage VARCHAR(64) NOT NULL DEFAULT '' COMMENT '免疫阶段',
  MODIFY COLUMN protein_target_id BIGINT NULL COMMENT '检测标靶id(serum_titer_target)',
  ADD COLUMN pc_id BIGINT NULL COMMENT 'PC记录id(serum_titer_pc)' AFTER protein_target_id,
  MODIFY COLUMN mouse_group VARCHAR(64) NULL COMMENT '组别-品系',
  ADD COLUMN antigen_type VARCHAR(64) NULL COMMENT '抗原类型' AFTER mouse_group,
  ADD COLUMN slot_groups JSON NULL COMMENT '上方分组标题' AFTER antigen_type,
  ADD COLUMN upper_slot_list JSON NULL COMMENT '上方鼠号槽位{layout,values}' AFTER slot_groups,
  ADD COLUMN lower_slot_list JSON NULL COMMENT '下方NC/PC槽位{layout,values}' AFTER upper_slot_list,
  MODIFY COLUMN positive_well_list JSON NULL COMMENT '阳性孔列表',
  ADD COLUMN absorbance_1 JSON NULL COMMENT '吸光度1:{wavelength,matrix}' AFTER positive_well_list;

ALTER TABLE serum_elisa_plate
  DROP COLUMN mouse_list,
  DROP COLUMN pc_column_list;
