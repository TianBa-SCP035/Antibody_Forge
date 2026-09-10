from sqlalchemy import BigInteger, DateTime, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class DiscoveryWorkbench(Base):
    __tablename__ = "discovery_workbench"
    __table_args__ = {"comment": "抗体发现项目工作台"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
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
    owner: Mapped[str | None] = mapped_column(String(64), comment="负责人")
    status: Mapped[str | None] = mapped_column(String(32), comment="状态")
    priority: Mapped[str | None] = mapped_column(String(32), comment="优先级")
    sort_order: Mapped[int | None] = mapped_column(Integer, comment="排序；终态为空")
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
            "owner": self.owner,
            "status": self.status,
            "priority": self.priority,
            "sort_order": self.sort_order,
            "remark": self.remark,
            "created_by": self.created_by,
            "created_at": format_time(self.created_at),
            "updated_at": format_time(self.updated_at),
        }
