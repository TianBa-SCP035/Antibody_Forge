from datetime import timedelta

from sqlalchemy import BigInteger, DateTime, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class SerumImmProject(Base):
    __tablename__ = "serum_imm_project"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    experiment_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    project_code: Mapped[str | None] = mapped_column(String(64))
    project_name: Mapped[str | None] = mapped_column(String(255))
    project_purpose: Mapped[str | None] = mapped_column(String(255))
    start_date: Mapped[str | None] = mapped_column(String(32))
    immunization_interval: Mapped[str | None] = mapped_column(String(32))
    target_name: Mapped[str | None] = mapped_column(String(128))
    target_type: Mapped[str | None] = mapped_column(String(64))
    target_size: Mapped[str | None] = mapped_column(String(64))
    owner: Mapped[str | None] = mapped_column(String(64))
    pm: Mapped[str | None] = mapped_column(String(64))
    study_type: Mapped[str | None] = mapped_column(String(64))
    assay_method: Mapped[str | None] = mapped_column(String(64))
    project_status: Mapped[str | None] = mapped_column(String(64))
    remark: Mapped[str | None] = mapped_column(String(255))
    mouse_strain: Mapped[str | None] = mapped_column(String(128))
    mouse_strain_category: Mapped[str | None] = mapped_column(String(128))
    prep_status: Mapped[str | None] = mapped_column(String(16))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "project_code": self.project_code,
            "project_name": self.project_name,
            "project_purpose": self.project_purpose,
            "start_date": self.start_date,
            "immunization_interval": self.immunization_interval,
            "target_name": self.target_name,
            "target_type": self.target_type,
            "target_size": self.target_size,
            "owner": self.owner,
            "pm": self.pm,
            "study_type": self.study_type,
            "assay_method": self.assay_method,
            "project_status": self.project_status,
            "remark": self.remark,
            "mouse_strain": self.mouse_strain,
            "mouse_strain_category": self.mouse_strain_category,
            "prep_status": self.prep_status,
        }


class SerumImmMouse(Base):
    __tablename__ = "serum_imm_mouse"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    experiment_id: Mapped[str | None] = mapped_column(String(64))
    group_id: Mapped[str | None] = mapped_column(String(32))
    mouse_strain: Mapped[str | None] = mapped_column(String(128))
    mouse_strain_category: Mapped[str | None] = mapped_column(String(128))
    mouse_count: Mapped[str | None] = mapped_column(String(32))
    age_weeks: Mapped[str | None] = mapped_column(String(32))
    sex: Mapped[str | None] = mapped_column(String(32))
    vendor: Mapped[str | None] = mapped_column(String(128))
    mouse_no_list: Mapped[str | None] = mapped_column(String(512))
    cage_position: Mapped[str | None] = mapped_column(String(64))
    remark: Mapped[str | None] = mapped_column(String(255))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "group_id": self.group_id,
            "mouse_strain": self.mouse_strain,
            "mouse_strain_category": self.mouse_strain_category,
            "mouse_count": self.mouse_count,
            "age_weeks": self.age_weeks,
            "sex": self.sex,
            "vendor": self.vendor,
            "mouse_no_list": self.mouse_no_list,
            "cage_position": self.cage_position,
            "remark": self.remark,
        }


class SerumFile(Base):
    __tablename__ = "serum_file"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    experiment_id: Mapped[str] = mapped_column(String(64), nullable=False)
    upload_user: Mapped[str | None] = mapped_column(String(64))
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_time: Mapped[object | None] = mapped_column(DateTime, server_default=func.current_timestamp())
    updated_time: Mapped[object | None] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    def to_dict(self) -> dict:
        def format_time(dt):
            if dt is None:
                return None
            return (dt + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")

        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "upload_user": self.upload_user,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "created_time": format_time(self.created_time),
            "updated_time": format_time(self.updated_time),
            "thumb_url": f"/serum/titer/file/download?id={self.id}&preview=true&thumb=1&w=400",
        }


class SerumImmAntigen(Base):
    __tablename__ = "serum_imm_antigen"
    __table_args__ = (UniqueConstraint("experiment_id", "antigen_id", name="uq_experiment_antigen"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    experiment_id: Mapped[str | None] = mapped_column(String(64))
    antigen_id: Mapped[str | None] = mapped_column(String(32))
    species: Mapped[str | None] = mapped_column(String(32))
    antigen_type: Mapped[str | None] = mapped_column(String(64))
    antigen_name: Mapped[str | None] = mapped_column(String(255))
    catalog_no: Mapped[str | None] = mapped_column(String(64))
    lot_no: Mapped[str | None] = mapped_column(String(64))
    stock_conc: Mapped[str | None] = mapped_column(String(64))
    vendor: Mapped[str | None] = mapped_column(String(128))
    adjuvant_type: Mapped[str | None] = mapped_column(String(64))
    adjuvant_source: Mapped[str | None] = mapped_column(String(128))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "antigen_id": self.antigen_id,
            "species": self.species,
            "antigen_type": self.antigen_type,
            "antigen_name": self.antigen_name,
            "catalog_no": self.catalog_no,
            "lot_no": self.lot_no,
            "stock_conc": self.stock_conc,
            "vendor": self.vendor,
            "adjuvant_type": self.adjuvant_type,
            "adjuvant_source": self.adjuvant_source,
        }


class SerumImmStep(Base):
    __tablename__ = "serum_imm_step"

    step_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    experiment_id: Mapped[str | None] = mapped_column(String(64))
    group_id: Mapped[str | None] = mapped_column(String(32))
    stage_name: Mapped[str | None] = mapped_column(String(64))
    antigen_id: Mapped[str | None] = mapped_column(String(32))
    antigen_dose: Mapped[str | None] = mapped_column(String(64))
    adjuvant_name: Mapped[str | None] = mapped_column(String(64))
    cpg_dose: Mapped[str | None] = mapped_column(String(64))
    injection_volume: Mapped[str | None] = mapped_column(String(64))
    route: Mapped[str | None] = mapped_column(String(32))
    injection_site: Mapped[str | None] = mapped_column(String(64))
    day_relative: Mapped[str | None] = mapped_column(String(16))
    date_actual: Mapped[str | None] = mapped_column(String(32))
    remark: Mapped[str | None] = mapped_column(String(255))

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "experiment_id": self.experiment_id,
            "group_id": self.group_id,
            "stage_name": self.stage_name,
            "antigen_id": self.antigen_id,
            "antigen_dose": self.antigen_dose,
            "adjuvant_name": self.adjuvant_name,
            "cpg_dose": self.cpg_dose,
            "injection_volume": self.injection_volume,
            "route": self.route,
            "injection_site": self.injection_site,
            "day_relative": self.day_relative,
            "date_actual": self.date_actual,
            "remark": self.remark,
        }


class SerumTiterPc(Base):
    __tablename__ = "serum_titer_pc"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    experiment_id: Mapped[str | None] = mapped_column(String(64))
    pc_name: Mapped[str | None] = mapped_column(String(255))
    catalog_batch: Mapped[str | None] = mapped_column(String(128))
    source: Mapped[str | None] = mapped_column(String(128))
    concentration: Mapped[str | None] = mapped_column(String(64))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "pc_name": self.pc_name,
            "concentration": self.concentration,
            "catalog_batch": self.catalog_batch,
            "source": self.source,
        }


class SerumTiterTarget(Base):
    __tablename__ = "serum_titer_target"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    experiment_id: Mapped[str | None] = mapped_column(String(64))
    type: Mapped[str | None] = mapped_column(String(32))
    name: Mapped[str | None] = mapped_column(String(255))
    batch_no: Mapped[str | None] = mapped_column(String(64))
    passage: Mapped[str | None] = mapped_column(String(64))
    cell_count: Mapped[str | None] = mapped_column(String(64))
    catalog_no: Mapped[str | None] = mapped_column(String(64))
    source: Mapped[str | None] = mapped_column(String(128))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "type": self.type,
            "name": self.name,
            "cell_count": self.cell_count,
            "batch_no": self.batch_no,
            "passage": self.passage,
            "catalog_no": self.catalog_no,
            "source": self.source,
        }


class SerumElisaPlate(Base):
    __tablename__ = "serum_elisa_plate"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    experiment_id: Mapped[str] = mapped_column(String(64), nullable=False)
    qr_code: Mapped[str | None] = mapped_column(String(128))
    excel_file_id: Mapped[int | None] = mapped_column(BigInteger)
    immune_stage: Mapped[str] = mapped_column(String(64), nullable=False, server_default="")
    protein_target_id: Mapped[int | None] = mapped_column(BigInteger)
    pc_id: Mapped[int | None] = mapped_column(BigInteger)
    mouse_group: Mapped[str | None] = mapped_column(String(64))
    antigen_type: Mapped[str | None] = mapped_column(String(64))
    slot_groups: Mapped[object | None] = mapped_column(JSON)
    upper_slot_list: Mapped[object | None] = mapped_column(JSON)
    lower_slot_list: Mapped[object | None] = mapped_column(JSON)
    positive_well_list: Mapped[object | None] = mapped_column(JSON)
    absorbance_1: Mapped[object | None] = mapped_column(JSON)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "qr_code": self.qr_code,
            "excel_file_id": self.excel_file_id,
            "immune_stage": self.immune_stage,
            "protein_target_id": self.protein_target_id,
            "pc_id": self.pc_id,
            "mouse_group": self.mouse_group,
            "antigen_type": self.antigen_type,
            "slot_groups": self.slot_groups,
            "upper_slot_list": self.upper_slot_list,
            "lower_slot_list": self.lower_slot_list,
            "positive_well_list": self.positive_well_list,
            "absorbance_1": self.absorbance_1,
            "plate_type": "elisa",
        }


class SerumFacsPlate(Base):
    __tablename__ = "serum_facs_plate"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    experiment_id: Mapped[str] = mapped_column(String(64), nullable=False)
    qr_code: Mapped[str | None] = mapped_column(String(128))
    image_file_id: Mapped[int | None] = mapped_column(BigInteger)
    excel_file_id: Mapped[int | None] = mapped_column(BigInteger)
    immune_stage: Mapped[str | None] = mapped_column(String(64))
    x_axis: Mapped[str | None] = mapped_column(String(64))
    y_axis: Mapped[str | None] = mapped_column(String(64))
    cell_target_id: Mapped[int | None] = mapped_column(BigInteger)
    pc_upper_id: Mapped[int | None] = mapped_column(BigInteger)
    pc_lower_id: Mapped[int | None] = mapped_column(BigInteger)
    upper_group: Mapped[str | None] = mapped_column(String(32))
    lower_group: Mapped[str | None] = mapped_column(String(32))
    upper_mouse_list: Mapped[object | None] = mapped_column(JSON)
    lower_mouse_list: Mapped[object | None] = mapped_column(JSON)
    upper_slot_groups: Mapped[object | None] = mapped_column(JSON)
    lower_slot_groups: Mapped[object | None] = mapped_column(JSON)
    positive_well_list: Mapped[object | None] = mapped_column(JSON)
    instrument_type: Mapped[str | None] = mapped_column(String(64))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "qr_code": self.qr_code,
            "image_file_id": self.image_file_id,
            "excel_file_id": self.excel_file_id,
            "immune_stage": self.immune_stage,
            "x_axis": self.x_axis,
            "y_axis": self.y_axis,
            "cell_target_id": self.cell_target_id,
            "pc_upper_id": self.pc_upper_id,
            "pc_lower_id": self.pc_lower_id,
            "upper_group": self.upper_group,
            "lower_group": self.lower_group,
            "upper_mouse_list": self.upper_mouse_list,
            "lower_mouse_list": self.lower_mouse_list,
            "upper_slot_groups": self.upper_slot_groups,
            "lower_slot_groups": self.lower_slot_groups,
            "positive_well_list": self.positive_well_list,
            "instrument_type": self.instrument_type,
            "plate_type": "facs",
        }
