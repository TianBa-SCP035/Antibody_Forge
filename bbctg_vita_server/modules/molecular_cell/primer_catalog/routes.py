from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from core.response import error, success
from db.session import get_db
from models.system import SysUser
from modules.auth.dependencies import get_current_user
from modules.molecular_cell.primer_catalog import service
from modules.system.permissions import (
    DEFAULT_PERMISSION_MESSAGE,
    PERMISSION_MESSAGES,
    has_any_permission,
    require_permission,
)

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
    family: str | None = Field(default=None, max_length=32)
    direction: str | None = Field(default=None, max_length=8)
    active: bool | None = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=service.DEFAULT_PAGE_LIMIT, ge=1, le=service.MAX_PAGE_LIMIT)


class PrimerSaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int | None = Field(default=None, gt=0)
    name: str = Field(min_length=1, max_length=service.FIELD_LIMITS["name"])
    family: str = Field(min_length=1, max_length=service.FIELD_LIMITS["family"])
    direction: str | None = Field(default=None, max_length=service.FIELD_LIMITS["direction"])
    version: str | None = Field(default=None, max_length=service.FIELD_LIMITS["version"])
    short_sequence: str = Field(min_length=1, max_length=service.FIELD_LIMITS["short_sequence"])
    homology_arm_1: str | None = Field(
        default=None, max_length=service.FIELD_LIMITS["homology_arm_1"]
    )
    homology_arm_2: str | None = Field(
        default=None, max_length=service.FIELD_LIMITS["homology_arm_2"]
    )
    note: str | None = Field(default=None, max_length=service.FIELD_LIMITS["note"])
    active: bool = True


class PrimerDeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(gt=0)


class PrimerBatchIdsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ids: list[int] = Field(min_length=1, max_length=service.MAX_BATCH_IDS)
    active: bool | None = None
    family: str | None = Field(default=None, max_length=service.FIELD_LIMITS["family"])


class PrimerBatchSaveRequest(BaseModel):
    items: list[PrimerSaveRequest] = Field(min_length=1, max_length=service.MAX_BATCH_ITEMS)


def _write(db: Session, action: Callable[[], dict]) -> dict:
    try:
        return success(action())
    except ValueError as exc:
        db.rollback()
        status = 404 if str(exc) == service.MISSING_PRIMER else 422
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        return error(str(exc))


@router.get("/options")
def primer_options(
    query: str | None = Query(default=None),
    family: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=service.MAX_OPTIONS),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    if not has_any_permission(db, current_user, OPTION_PERMISSIONS):
        raise HTTPException(
            status_code=403,
            detail=PERMISSION_MESSAGES.get(OPTION_PERMISSIONS[0], DEFAULT_PERMISSION_MESSAGE),
        )
    return success(service.list_options(db, query, family, limit))


@router.post("/list")
def primer_list(
    data: PrimerListRequest | None = None,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, PAGE_PERMISSION)
    return success(service.list_catalog(db, data.model_dump() if data else {}))


@router.post("/save")
def primer_save(
    data: PrimerSaveRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, EDIT_PERMISSION)
    return _write(db, lambda: service.save(db, data.model_dump(exclude_unset=True)))


@router.post("/ids")
def primer_ids(
    data: PrimerListRequest | None = None,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, PAGE_PERMISSION)
    return success({"ids": service.list_ids(db, data.model_dump() if data else {})})


@router.post("/batch_update")
def primer_batch_update(
    data: PrimerBatchIdsRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, EDIT_PERMISSION)
    return _write(
        db,
        lambda: service.batch_update(db, data.ids, active=data.active, family=data.family),
    )


@router.post("/batch_delete")
def primer_batch_delete(
    data: PrimerBatchIdsRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, EDIT_PERMISSION)
    return _write(db, lambda: service.batch_delete(db, data.ids))


@router.post("/delete")
def primer_delete(
    data: PrimerDeleteRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, EDIT_PERMISSION)
    return _write(db, lambda: service.delete_primer(db, data.id))


@router.post("/batch_save")
def primer_batch_save(
    data: PrimerBatchSaveRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, EDIT_PERMISSION)
    items = [item.model_dump(exclude_unset=True) for item in data.items]
    return _write(db, lambda: service.batch_save(db, items))


@router.post("/export")
def primer_export(
    data: PrimerListRequest | None = None,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> Response:
    from utils.excel import xlsx_response

    require_permission(db, current_user, PAGE_PERMISSION)
    output, filename = service.export_workbook(db, data.model_dump() if data else {})
    return xlsx_response(output, filename)
