from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, CHAR, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


def _format_value(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        text = format(value, "f").rstrip("0").rstrip(".")
        return text or "0"
    return value


class MolecularLibraryOrder(Base):
    __tablename__ = "molecular_library_order"
    __table_args__ = (
        UniqueConstraint("library_order_id", name="uk_molecular_library_order_id"),
        {"comment": "文库构建工单"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    library_order_id: Mapped[str] = mapped_column(String(32), nullable=False, comment="系统工单号")
    library_code: Mapped[str | None] = mapped_column(String(64), index=True, comment="建库编号")
    source_discovery_id: Mapped[str | None] = mapped_column(String(32), index=True, comment="来源发现ID")
    source_project_code: Mapped[str | None] = mapped_column(String(64), index=True, comment="来源项目编号")
    study_type: Mapped[str | None] = mapped_column(String(64), comment="课题类型")
    source_experiment_type: Mapped[str | None] = mapped_column(String(64), comment="噬菌体实验类型")
    project_goal: Mapped[str | None] = mapped_column(String(1000), comment="噬菌体实验目标")
    target_name: Mapped[str | None] = mapped_column(String(128), comment="靶点名称")
    target_codes: Mapped[list[str] | None] = mapped_column(JSON, comment="靶点编号列表")
    pm: Mapped[str | None] = mapped_column(String(64), comment="PM")
    mouse_model: Mapped[str | None] = mapped_column(String(128), comment="归类鼠型")
    sample_type: Mapped[str | None] = mapped_column(String(32), index=True, comment="样品类型")

    build_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="建库类型")
    sample_source: Mapped[str | None] = mapped_column(String(32), index=True, comment="样品来源")
    received_on: Mapped[date | None] = mapped_column(Date, comment="样品交接日期")
    instrument_on: Mapped[date | None] = mapped_column(Date, comment="上机日期")
    blood_collected_on: Mapped[date | None] = mapped_column(Date, comment="采血日期")
    positive_cell_count: Mapped[str | None] = mapped_column(String(64), comment="阳性细胞数")
    plate_nos: Mapped[list[str] | None] = mapped_column(JSON, comment="孔板编号列表")
    cell_type: Mapped[str | None] = mapped_column(String(64), comment="细胞类型")
    target_forms: Mapped[list[str] | None] = mapped_column(JSON, comment="靶点形式列表")
    notebook_no: Mapped[str | None] = mapped_column(String(64), comment="实验记录本号")
    immunization_stage: Mapped[str | None] = mapped_column(String(64), comment="免疫阶段")
    library_batch_no: Mapped[str | None] = mapped_column(String(64), index=True, comment="建库批号")

    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True, comment="状态")
    priority: Mapped[str] = mapped_column(String(24), nullable=False, comment="优先级")
    owner: Mapped[str | None] = mapped_column(String(64), comment="负责人")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, comment="工单开始时间")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, comment="工单完成时间")

    pcr_started_at: Mapped[datetime | None] = mapped_column(DateTime, comment="PCR开始时间")
    pcr_finished_at: Mapped[datetime | None] = mapped_column(DateTime, comment="PCR结束时间")
    pcr_owner: Mapped[str | None] = mapped_column(String(64), comment="PCR操作人")
    pcr_qc_owner: Mapped[str | None] = mapped_column(String(64), comment="PCR检测人")
    transfected_at: Mapped[datetime | None] = mapped_column(DateTime, comment="转染时间")
    transfection_owner: Mapped[str | None] = mapped_column(String(64), comment="转染人")

    rna_location: Mapped[str | None] = mapped_column(String(255), comment="RNA存放位置")
    cdna_location: Mapped[str | None] = mapped_column(String(255), comment="cDNA存放位置")
    library_location: Mapped[str | None] = mapped_column(String(255), comment="文库产物位置")
    cdna_concentration: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), comment="cDNA浓度")
    initial_library_size: Mapped[str | None] = mapped_column(String(64), comment="初始库容")
    effective_library_size: Mapped[str | None] = mapped_column(String(64), comment="有效库容")
    fragment_size_bp: Mapped[int | None] = mapped_column(Integer, comment="片段大小bp")

    h_forward_primer_id: Mapped[int | None] = mapped_column(BigInteger, comment="H正向引物字典ID")
    h_forward_primer_name: Mapped[str | None] = mapped_column(String(128), comment="H正向引物名称快照")
    h_reverse_primer_id: Mapped[int | None] = mapped_column(BigInteger, comment="H反向引物字典ID")
    h_reverse_primer_name: Mapped[str | None] = mapped_column(String(128), comment="H反向引物名称快照")
    h_primer_concentration: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), comment="H引物浓度")
    k_forward_primer_id: Mapped[int | None] = mapped_column(BigInteger, comment="K正向引物字典ID")
    k_forward_primer_name: Mapped[str | None] = mapped_column(String(128), comment="K正向引物名称快照")
    k_reverse_primer_id: Mapped[int | None] = mapped_column(BigInteger, comment="K反向引物字典ID")
    k_reverse_primer_name: Mapped[str | None] = mapped_column(String(128), comment="K反向引物名称快照")
    k_primer_concentration: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), comment="K引物浓度")
    l_forward_primer_id: Mapped[int | None] = mapped_column(BigInteger, comment="L正向引物字典ID")
    l_forward_primer_name: Mapped[str | None] = mapped_column(String(128), comment="L正向引物名称快照")
    l_reverse_primer_id: Mapped[int | None] = mapped_column(BigInteger, comment="L反向引物字典ID")
    l_reverse_primer_name: Mapped[str | None] = mapped_column(String(128), comment="L反向引物名称快照")
    l_primer_concentration: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), comment="L引物浓度")
    index_mode: Mapped[str | None] = mapped_column(String(16), comment="Barcode方式")
    i7_catalog_id: Mapped[int | None] = mapped_column(BigInteger, comment="i7字典ID")
    i7_name: Mapped[str | None] = mapped_column(String(128), comment="i7名称快照")
    i7_sequence: Mapped[str | None] = mapped_column(String(64), comment="i7序列快照")
    i5_catalog_id: Mapped[int | None] = mapped_column(BigInteger, comment="i5字典ID")
    i5_name: Mapped[str | None] = mapped_column(String(128), comment="i5名称快照")
    i5_sequence: Mapped[str | None] = mapped_column(String(64), comment="i5序列快照")

    qc_result: Mapped[str | None] = mapped_column(String(16), comment="质检结论")
    qc_owner: Mapped[str | None] = mapped_column(String(64), comment="质检人")
    qc_on: Mapped[date | None] = mapped_column(Date, comment="质检日期")
    qc_note: Mapped[str | None] = mapped_column(String(1000), comment="质检说明")

    remark: Mapped[str | None] = mapped_column(String(1000), comment="备注")
    created_by: Mapped[str | None] = mapped_column(String(64), comment="创建人")
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.current_timestamp(), comment="创建时间"
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment="更新时间",
    )

    def to_dict(self) -> dict:
        data = {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
        data["target_codes"] = self.target_codes if isinstance(self.target_codes, list) else []
        data["target_forms"] = self.target_forms if isinstance(self.target_forms, list) else []
        data["plate_nos"] = self.plate_nos if isinstance(self.plate_nos, list) else []
        return {key: _format_value(value) for key, value in data.items()}


class MolecularPrimerIndexCatalog(Base):
    __tablename__ = "molecular_primer_index_catalog"
    __table_args__ = (
        UniqueConstraint("name", name="uk_molecular_primer_index_name"),
        {"comment": "引物与Barcode字典"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="名称")
    family: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="系列")
    direction: Mapped[str | None] = mapped_column(String(8), comment="原始方向")
    version: Mapped[str | None] = mapped_column(String(16), comment="版本")
    short_sequence: Mapped[str] = mapped_column(String(64), nullable=False, comment="短序列")
    homology_arm_1: Mapped[str | None] = mapped_column(String(128), comment="同源臂1")
    homology_arm_2: Mapped[str | None] = mapped_column(String(128), comment="同源臂2")
    source_file: Mapped[str | None] = mapped_column(String(255), comment="来源文件")
    source_row: Mapped[int | None] = mapped_column(Integer, comment="来源行号")
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        comment="是否启用",
    )
    note: Mapped[str | None] = mapped_column(String(500), comment="备注")
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.current_timestamp(), comment="创建时间"
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment="更新时间",
    )

    def to_dict(self) -> dict:
        return {
            column.name: _format_value(getattr(self, column.name))
            for column in self.__table__.columns
        }


class MolecularLibraryResultFile(Base):
    __tablename__ = "molecular_library_result_file"
    __table_args__ = (
        UniqueConstraint("sha256", name="uk_molecular_library_result_sha256"),
        {"comment": "文库结果文件"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False, comment="存储路径")
    mime_type: Mapped[str | None] = mapped_column(String(128), comment="文件MIME")
    byte_size: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="文件大小")
    sha256: Mapped[str] = mapped_column(CHAR(64), nullable=False, comment="文件哈希")
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.current_timestamp(), comment="首次保存时间"
    )

    def to_dict(self) -> dict:
        return {
            column.name: _format_value(getattr(self, column.name))
            for column in self.__table__.columns
        }


class MolecularLibraryResultLink(Base):
    __tablename__ = "molecular_library_result_link"
    __table_args__ = (
        UniqueConstraint("file_id", "order_id", name="uk_molecular_library_result_link"),
        {"comment": "文库结果关联"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    file_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("molecular_library_result_file.id"),
        nullable=False,
        index=True,
        comment="物理文件ID",
    )
    order_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("molecular_library_order.id"),
        nullable=False,
        index=True,
        comment="文库工单ID",
    )
    original_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="显示文件名")
    is_final_qc: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        comment="是否最终质检文件",
    )
    qc_regions: Mapped[list | None] = mapped_column(
        JSON(none_as_null=True),
        comment="质检选区列表",
    )
    uploaded_by: Mapped[str | None] = mapped_column(String(64), comment="上传人")
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.current_timestamp(), comment="上传时间"
    )

    def to_dict(self) -> dict:
        return {
            column.name: _format_value(getattr(self, column.name))
            for column in self.__table__.columns
        }
