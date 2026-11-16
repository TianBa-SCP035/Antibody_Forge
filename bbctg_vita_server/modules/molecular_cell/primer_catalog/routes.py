from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from core.response import success
from db.session import get_db
from modules.auth.permissions import require
from modules.molecular_cell.primer_catalog import service
from modules.system.audit_routes import audit_quiet

router = APIRouter()
PAGE_PERMISSION = "molecular.page.primer"
EDIT_PERMISSION = "molecular.primer.edit"
OPTION_PERMISSIONS = (
    "molecular.page.library",
    "molecular.page.library_detail",
    PAGE_PERMISSION,
)


class PrimerListRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=128)
    sequence: str | None = Field(default=None, max_length=64)
    check_keyword: str | None = Field(default=None, max_length=64)
    note: str | None = Field(default=None, max_length=128)
    family: str | list[str] | None = None
    direction: str | list[str] | None = None
    active: bool | None = None
    field_filters: list[dict] | None = None
    sort_field: str | None = Field(default=None, max_length=64)
    sort_dir: Literal["", "asc", "desc"] | None = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=service.DEFAULT_PAGE_LIMIT, ge=1, le=service.MAX_PAGE_LIMIT)


class PrimerColumnValuesRequest(PrimerListRequest):
    field: str = Field(min_length=1, max_length=64)
    value_keyword: str = Field(default="", max_length=128)
    value_limit: int = Field(default=200, ge=1, le=1000)
    value_order: Literal["value", "value_desc", "recent"] = "value"


class PrimerSaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int | None = Field(default=None, gt=0)
    name: str = Field(min_length=1, max_length=service.FIELDS["name"].max_length)
    family: str = Field(min_length=1, max_length=service.FIELDS["family"].max_length)
    direction: str | None = Field(default=None, max_length=service.FIELDS["direction"].max_length)
    version: str | None = Field(default=None, max_length=service.FIELDS["version"].max_length)
    short_sequence: str = Field(min_length=1, max_length=service.FIELDS["short_sequence"].max_length)
    homology_arm_1: str | None = Field(
        default=None, max_length=service.FIELDS["homology_arm_1"].max_length
    )
    homology_arm_2: str | None = Field(
        default=None, max_length=service.FIELDS["homology_arm_2"].max_length
    )
    note: str | None = Field(default=None, max_length=service.FIELDS["note"].max_length)
    active: bool = True


class PrimerDeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(gt=0)


class PrimerBatchIdsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ids: list[int] = Field(min_length=1, max_length=service.MAX_BATCH_IDS)
    active: bool | None = None
    family: str | None = Field(default=None, max_length=service.FIELDS["family"].max_length)
    direction: str | None = Field(default=None, max_length=service.FIELDS["direction"].max_length)


class PrimerBatchSaveRequest(BaseModel):
    items: list[PrimerSaveRequest] = Field(min_length=1, max_length=service.MAX_BATCH_ITEMS)


@router.get("/options", dependencies=[require(*OPTION_PERMISSIONS)])
def primer_options(
    query: str | None = Query(default=None),
    family: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=service.MAX_OPTIONS),
    db: Session = Depends(get_db),
) -> dict:
    return success(service.list_options(db, query, family, limit))


@router.post("/list", dependencies=[require(PAGE_PERMISSION)])
def primer_list(
    data: PrimerListRequest | None = None,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.list_catalog(db, data.model_dump() if data else {}))


@router.post("/column_values", dependencies=[require(PAGE_PERMISSION)])
def primer_column_values(
    data: PrimerColumnValuesRequest,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.get_column_values(db, data.model_dump()))


@router.post("/save", dependencies=[require(EDIT_PERMISSION, audit="保存引物")])
def primer_save(
    data: PrimerSaveRequest,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.save(db, data.model_dump(exclude_unset=True)))


@router.post("/ids", dependencies=[require(PAGE_PERMISSION), audit_quiet()])
def primer_ids(
    data: PrimerListRequest | None = None,
    db: Session = Depends(get_db),
) -> dict:
    return success({"ids": service.list_ids(db, data.model_dump() if data else {})})


@router.post("/batch_update", dependencies=[require(EDIT_PERMISSION, audit="批量修改引物")])
def primer_batch_update(
    data: PrimerBatchIdsRequest,
    db: Session = Depends(get_db),
) -> dict:
    return success(
        service.batch_update(
            db, data.ids, active=data.active, family=data.family, direction=data.direction
        )
    )


@router.post("/batch_delete", dependencies=[require(EDIT_PERMISSION, audit="批量删除引物")])
def primer_batch_delete(
    data: PrimerBatchIdsRequest,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.batch_delete(db, data.ids))


@router.post("/delete", dependencies=[require(EDIT_PERMISSION, audit="删除引物")])
def primer_delete(
    data: PrimerDeleteRequest,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.delete_primer(db, data.id))


@router.post("/batch_save", dependencies=[require(EDIT_PERMISSION, audit="批量导入引物")])
def primer_batch_save(
    data: PrimerBatchSaveRequest,
    db: Session = Depends(get_db),
) -> dict:
    items = [item.model_dump(exclude_unset=True) for item in data.items]
    return success(service.batch_save(db, items))


@router.post("/export", dependencies=[require(PAGE_PERMISSION)])
def primer_export(
    data: PrimerListRequest | None = None,
    db: Session = Depends(get_db),
) -> Response:
    from utils.excel import xlsx_response

    output, filename = service.export_workbook(db, data.model_dump() if data else {})
    return xlsx_response(output, filename)
