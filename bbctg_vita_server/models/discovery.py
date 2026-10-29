from sqlalchemy import BigInteger, DateTime, Integer, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class DiscoveryWorkbench(Base):
    __tablename__ = "discovery_workbench"
    __table_args__ = (
        UniqueConstraint("discovery_id", name="uk_discovery_workbench_discovery_id"),
        {"comment": "抗体发现项目工作台"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    discovery_id: Mapped[str] = mapped_column(String(32), nullable=False, comment="发现安排号")
    project_code: Mapped[str | None] = mapped_column(String(64), comment="项目管理编号")
    experiment_id: Mapped[str | None] = mapped_column(String(64), comment="实验号")
    target_name: Mapped[str | None] = mapped_column(String(128), comment="靶点名称")
    target_codes: Mapped[list[str] | None] = mapped_column(JSON, comment="靶点编号列表")
    study_type: Mapped[str | None] = mapped_column(String(64), comment="课题类型")
    pm: Mapped[str | None] = mapped_column(String(64), comment="PM")
    mouse_strain_category: Mapped[str | None] = mapped_column(String(128), comment="归类鼠型")
    mouse_strain: Mapped[str | None] = mapped_column(String(128), comment="小鼠品系")
    cage_position: Mapped[str | None] = mapped_column(String(64), comment="笼位")
    mouse_count: Mapped[int | None] = mapped_column(Integer, comment="小鼠只数")
    mouse_nos: Mapped[str | None] = mapped_column(String(512), comment="鼠号")
    serum_titer: Mapped[str | None] = mapped_column(String(255), comment="血清效价")
    immune_antigen: Mapped[str | None] = mapped_column(String(255), comment="免疫用抗原")
    screening_methods: Mapped[str | None] = mapped_column(String(64), comment="筛选方式")
    screening_antigen: Mapped[str | None] = mapped_column(String(255), comment="筛选抗原")
    positive_cell_count: Mapped[str | None] = mapped_column(String(64), comment="阳性细胞数")
    plate_nos: Mapped[str | None] = mapped_column(String(512), comment="板号")
    harvest_date: Mapped[str | None] = mapped_column(String(32), comment="剖鼠取细胞日")
    boost_date: Mapped[str | None] = mapped_column(String(32), comment="冲击免日期")
    boost_antigen: Mapped[str | None] = mapped_column(String(255), comment="冲击免抗原")
    boost_cells: Mapped[str | None] = mapped_column(String(255), comment="冲击免细胞")
    owner: Mapped[str | None] = mapped_column(String(64), comment="负责人")
    immune_owner: Mapped[str | None] = mapped_column(String(64), comment="免疫负责人")
    cell_collector: Mapped[str | None] = mapped_column(String(64), comment="细胞收集人")
    status: Mapped[str | None] = mapped_column(String(32), comment="状态")
    priority: Mapped[str | None] = mapped_column(String(32), comment="优先级")
    sort_order: Mapped[int | None] = mapped_column(Integer, comment="排序值")
    remark: Mapped[str | None] = mapped_column(String(500), comment="备注")
    created_by: Mapped[str | None] = mapped_column(String(64), comment="创建人")
    created_at: Mapped[object | None] = mapped_column(DateTime, server_default=func.current_timestamp(), comment="创建时间")
    updated_at: Mapped[object | None] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment="更新时间",
    )

    def to_dict(self) -> dict:
        def format_time(dt):
            if dt is None:
                return None
            return dt.strftime("%Y-%m-%d %H:%M:%S")

        methods = str(self.screening_methods or "").strip()
        method_list = [part for part in methods.split(",") if part]
        codes = self.target_codes if isinstance(self.target_codes, list) else []
        return {
            "id": self.id,
            "discovery_id": self.discovery_id,
            "project_code": self.project_code,
            "experiment_id": self.experiment_id,
            "target_name": self.target_name,
            "target_codes": codes,
            "study_type": self.study_type,
            "pm": self.pm,
            "mouse_strain_category": self.mouse_strain_category,
            "mouse_strain": self.mouse_strain,
            "cage_position": self.cage_position,
            "mouse_count": self.mouse_count,
            "mouse_nos": self.mouse_nos,
            "serum_titer": self.serum_titer,
            "immune_antigen": self.immune_antigen,
            "screening_methods": self.screening_methods,
            "screening_method_list": method_list,
            "screening_antigen": self.screening_antigen,
            "positive_cell_count": self.positive_cell_count,
            "plate_nos": self.plate_nos,
            "harvest_date": self.harvest_date,
            "boost_date": self.boost_date,
            "boost_antigen": self.boost_antigen,
            "boost_cells": self.boost_cells,
            "owner": self.owner,
            "immune_owner": self.immune_owner,
            "cell_collector": self.cell_collector,
            "status": self.status,
            "priority": self.priority,
            "sort_order": self.sort_order,
            "remark": self.remark,
            "created_by": self.created_by,
            "created_at": format_time(self.created_at),
            "updated_at": format_time(self.updated_at),
        }


class DiscoverySynthesisOrder(Base):
    __tablename__ = "discovery_synthesis_order"
    __table_args__ = (
        UniqueConstraint("synthesis_order_id", name="uk_discovery_synthesis_order_id"),
        UniqueConstraint("source_one_type", "source_one_id", name="uk_discovery_synthesis_order_source_one"),
        {"comment": "抗体发现合成与验证单"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    synthesis_order_id: Mapped[str] = mapped_column(String(32), nullable=False, comment="系统单号")
    source_one_type: Mapped[str | None] = mapped_column(String(16), comment="外部来源类型")
    source_one_id: Mapped[int | None] = mapped_column(BigInteger, comment="外部来源记录ID")
    source_snapshot: Mapped[dict | None] = mapped_column(JSON, comment="外部来源当前值快照")
    status: Mapped[str] = mapped_column(String(32), nullable=False, comment="状态")
    priority: Mapped[str | None] = mapped_column(String(32), comment="优先级")
    sort_order: Mapped[int | None] = mapped_column(Integer, comment="排序值")
    order_kind: Mapped[str] = mapped_column(String(32), nullable=False, comment="订单性质")
    supply_mode: Mapped[str] = mapped_column(String(32), nullable=False, comment="供应方式")
    target_name: Mapped[str | None] = mapped_column(String(128), comment="靶点名称")
    target_codes: Mapped[list[str] | None] = mapped_column(JSON, comment="靶点编号列表")
    target_type: Mapped[str | None] = mapped_column(String(64), comment="靶点类型")
    mouse_strain: Mapped[str | None] = mapped_column(String(128), comment="小鼠品系")
    selection_method: Mapped[str | None] = mapped_column(String(128), comment="挑选方式")
    synthesis_code: Mapped[str | None] = mapped_column(String(64), comment="送测转码")
    order_no: Mapped[str | None] = mapped_column(String(64), comment="合成订单号")
    synthetic_corp: Mapped[str | None] = mapped_column(String(64), comment="合成公司")
    synthetic_count: Mapped[int | None] = mapped_column(Integer, comment="合成个数")
    synthetic_date: Mapped[str | None] = mapped_column(String(32), comment="合成日期")
    arrival_count: Mapped[int | None] = mapped_column(Integer, comment="到货个数")
    arrival_date: Mapped[str | None] = mapped_column(String(32), comment="到货日期")
    flow_count: Mapped[int | None] = mapped_column(Integer, comment="流式个数")
    flow_date: Mapped[str | None] = mapped_column(String(32), comment="流式日期")
    affinity_count: Mapped[int | None] = mapped_column(Integer, comment="亲和力个数")
    affinity_date: Mapped[str | None] = mapped_column(String(32), comment="亲和力日期")
    affinity_result: Mapped[str | None] = mapped_column(String(32), comment="亲和力结果")
    owner: Mapped[str | None] = mapped_column(String(64), comment="负责人")
    batch_label: Mapped[str | None] = mapped_column(String(255), comment="工单批次")
    assay_note: Mapped[str | None] = mapped_column(String(500), comment="检测与异常说明")
    remark: Mapped[str | None] = mapped_column(String(1000), comment="备注")
    eng_type: Mapped[str | None] = mapped_column(String(128), comment="改造类型")
    eng_method: Mapped[str | None] = mapped_column(String(128), comment="改造方式")
    eng_parent_seq: Mapped[str | None] = mapped_column(String(500), comment="改造序列或母本")
    eng_requirement: Mapped[str | None] = mapped_column(String(1000), comment="改造要求")
    eng_result: Mapped[str | None] = mapped_column(String(500), comment="改造结果")
    project_code: Mapped[str | None] = mapped_column(String(64), comment="项目管理编号")
    experiment_id: Mapped[str | None] = mapped_column(String(64), comment="实验号")
    study_type: Mapped[str | None] = mapped_column(String(64), comment="课题类型")
    pm: Mapped[str | None] = mapped_column(String(64), comment="PM")
    created_by: Mapped[str | None] = mapped_column(String(64), comment="创建人")
    created_at: Mapped[object | None] = mapped_column(DateTime, server_default=func.current_timestamp(), comment="创建时间")
    updated_at: Mapped[object | None] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment="更新时间",
    )

    def to_dict(self) -> dict:
        def format_time(dt):
            if dt is None:
                return None
            return dt.strftime("%Y-%m-%d %H:%M:%S")

        codes = self.target_codes if isinstance(self.target_codes, list) else []
        snapshot = self.source_snapshot if isinstance(self.source_snapshot, dict) else {}
        return {
            "id": self.id,
            "synthesis_order_id": self.synthesis_order_id,
            "source_one_type": self.source_one_type,
            "source_one_id": self.source_one_id,
            "source_snapshot": snapshot,
            "status": self.status,
            "priority": self.priority,
            "sort_order": self.sort_order,
            "order_kind": self.order_kind,
            "supply_mode": self.supply_mode,
            "target_name": self.target_name,
            "target_codes": codes,
            "target_type": self.target_type,
            "mouse_strain": self.mouse_strain,
            "selection_method": self.selection_method,
            "synthesis_code": self.synthesis_code,
            "order_no": self.order_no,
            "synthetic_corp": self.synthetic_corp,
            "synthetic_count": self.synthetic_count,
            "synthetic_date": self.synthetic_date,
            "arrival_count": self.arrival_count,
            "arrival_date": self.arrival_date,
            "flow_count": self.flow_count,
            "flow_date": self.flow_date,
            "affinity_count": self.affinity_count,
            "affinity_date": self.affinity_date,
            "affinity_result": self.affinity_result,
            "owner": self.owner,
            "batch_label": self.batch_label,
            "assay_note": self.assay_note,
            "remark": self.remark,
            "eng_type": self.eng_type,
            "eng_method": self.eng_method,
            "eng_parent_seq": self.eng_parent_seq,
            "eng_requirement": self.eng_requirement,
            "eng_result": self.eng_result,
            "project_code": self.project_code,
            "experiment_id": self.experiment_id,
            "study_type": self.study_type,
            "pm": self.pm,
            "created_by": self.created_by,
            "created_at": format_time(self.created_at),
            "updated_at": format_time(self.updated_at),
        }

