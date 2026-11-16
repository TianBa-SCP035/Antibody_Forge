import logging
from typing import Any, Literal

from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from core.response import success
from db.session import get_db
from models.system import SysUser
from modules.auth.dependencies import get_current_user
from modules.auth.external import require_labillion_caller
from modules.auth.permissions import require
from modules.mega_automation import callback, service
from modules.system.audit import write_operation_log
from modules.system.audit_context import AuditAction
from modules.system.audit_routes import audit, audit_quiet

router = APIRouter()
logger = logging.getLogger(__name__)
LABILLION_CALLBACK_AUDIT_ACTION = AuditAction("mega.labillion.callback", "镁伽状态回调", "update", "flow_work_order")
LABILLION_STATUS_SYNC_AUDIT_ACTION = AuditAction("mega.labillion.status_sync", "同步镁伽状态", "update", "flow_work_order")


def labillion_callback_success(data: dict[str, Any] | None = None) -> JSONResponse:
    return JSONResponse(status_code=200, content={"success": True, "data": data or {}})


@router.post(
    "/labillion/callback",
    dependencies=[Depends(require_labillion_caller), audit(LABILLION_CALLBACK_AUDIT_ACTION)],
)
def labillion_status_callback(
    data: Any = Body(default=None),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Labillion 订单状态推送；无需登录（来源按配置校验），响应须在 5 秒内返回 2xx。"""
    payload = data if isinstance(data, dict) else {}
    try:
        if data is not None and not isinstance(data, dict):
            raise ValueError("callback body must be a JSON object")
        result = callback.handle_labillion_status_push(db, payload)
        if not result.get("applied"):
            write_operation_log(
                db,
                LABILLION_CALLBACK_AUDIT_ACTION.code,
                operation_name=LABILLION_CALLBACK_AUDIT_ACTION.name,
                operation_type="update",
                target_type=LABILLION_CALLBACK_AUDIT_ACTION.resource,
                target_id=str(result.get("dispatchId") or "")[:128] or None,
                result="success",
                detail={
                    "changed": False,
                    "change_summary": str(result.get("reason") or "状态未变化"),
                    "callback_result": result,
                },
            )
            db.commit()
        return labillion_callback_success(result)
    except Exception as exc:
        db.rollback()
        logger.exception(
            "labillion callback failed dispatchId=%s",
            str(payload.get("dispatchId") or "")[:128] or "-",
        )
        try:
            write_operation_log(
                db,
                LABILLION_CALLBACK_AUDIT_ACTION.code,
                operation_name=LABILLION_CALLBACK_AUDIT_ACTION.name,
                operation_type="update",
                target_type=LABILLION_CALLBACK_AUDIT_ACTION.resource,
                target_id=str(payload.get("dispatchId") or "")[:128] or None,
                result="failed",
                detail={"changed": False, "reason": "internal_error"},
                error_message=str(exc)[:2000] or "internal_error",
            )
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("labillion callback failure audit could not be persisted")
        return labillion_callback_success({"applied": False, "reason": "internal_error"})


@router.get("/flow-work-orders/meta", dependencies=[require("mega.page.flow_work_order")])
def flow_work_order_meta(
    db: Session = Depends(get_db),
) -> dict:
    return success(service.get_meta())


@router.get("/flow-work-orders/cell-plate-usage", dependencies=[require("mega.page.flow_work_order")])
def flow_work_order_cell_plate_usage(
    barcode: str = "",
    exclude_order_id: int | None = None,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.get_cell_plate_usage(db, barcode, exclude_order_id))


@router.post("/flow-work-orders/by-source", dependencies=[require("mega.page.flow_work_order"), audit_quiet()])
def flow_work_orders_by_source(
    data: dict,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.get_work_orders_by_source(db, data or {}))


@router.post("/flow-work-orders/list", dependencies=[require("mega.page.flow_work_order")])
def flow_work_order_list(
    data: dict,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.get_work_order_list(db, data or {}))


class ColumnValuesRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    field: str = Field(min_length=1, max_length=64)
    value_keyword: str = Field(default="", max_length=128)
    value_limit: int = Field(default=200, ge=1, le=1000)
    value_order: Literal["value", "value_desc", "recent"] = "value"


@router.post("/flow-work-orders/column_values", dependencies=[require("mega.page.flow_work_order")])
def flow_work_order_column_values(
    data: ColumnValuesRequest,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.get_column_values(db, data.model_dump()))


@router.post("/flow-work-orders/export", dependencies=[require("mega.page.flow_work_order")])
def flow_work_order_export(
    data: dict,
    db: Session = Depends(get_db),
):
    from utils.excel import xlsx_response

    output, filename = service.export_work_order_list_workbook(db, data or {})
    return xlsx_response(output, filename)


@router.get("/flow-work-orders/{order_id}", dependencies=[require("mega.page.flow_work_order")])
def flow_work_order_detail(
    order_id: int,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.get_work_order_detail(db, order_id))


@router.post(
    "/flow-work-orders/{order_id}/sync-labillion-status",
    dependencies=[require("mega.page.flow_work_order"), audit(LABILLION_STATUS_SYNC_AUDIT_ACTION)],
)
def flow_work_order_sync_labillion_status(
    order_id: int,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.sync_work_order_labillion_status(db, order_id))


@router.get("/flow-work-orders/{order_id}/active-payload", dependencies=[require("mega.page.flow_work_order")])
def flow_work_order_active_payload(
    order_id: int,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.get_active_dispatch_payload(db, order_id))


@router.post("/flow-work-orders/save", dependencies=[require("mega.flow_work_order.edit", audit="保存流式工单")])
def flow_work_order_save(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    return success(service.save_work_order(db, data or {}, current_user))


@router.post("/flow-work-orders/{order_id}/validate", dependencies=[require("mega.flow_work_order.edit", audit="校验流式工单")])
def flow_work_order_validate(
    order_id: int,
    data: dict | None = Body(default=None),
    db: Session = Depends(get_db),
) -> dict:
    return success(service.validate_work_order(db, order_id, data))


@router.post("/flow-work-orders/{order_id}/dispatch", dependencies=[require("mega.flow_work_order.dispatch", audit="发送流式工单")])
def flow_work_order_dispatch(
    order_id: int,
    data: dict | None = Body(default=None),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    simulate = bool((data or {}).get("simulate"))
    return success(
        service.dispatch_work_order(db, order_id, current_user, simulate=simulate)
    )


@router.post("/flow-work-orders/{order_id}/pause", dependencies=[require("mega.flow_work_order.dispatch", audit="请求暂停流式工单")])
def flow_work_order_pause(
    order_id: int,
    data: dict | None = Body(default=None),
    db: Session = Depends(get_db),
) -> dict:
    simulate = bool((data or {}).get("simulate"))
    return success(service.pause_work_order(db, order_id, simulate=simulate))


@router.post("/flow-work-orders/{order_id}/resume", dependencies=[require("mega.flow_work_order.dispatch", audit="请求恢复流式工单")])
def flow_work_order_resume(
    order_id: int,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.resume_work_order(db, order_id))


@router.post("/flow-work-orders/{order_id}/pause-ack", dependencies=[require("mega.flow_work_order.dispatch", audit="确认设备已暂停")])
def flow_work_order_pause_ack(
    order_id: int,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.acknowledge_pause_work_order(db, order_id))


@router.post("/flow-work-orders/{order_id}/resume-ack", dependencies=[require("mega.flow_work_order.dispatch", audit="确认设备已恢复")])
def flow_work_order_resume_ack(
    order_id: int,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.acknowledge_resume_work_order(db, order_id))


@router.post("/flow-work-orders/{order_id}/confirm-execution", dependencies=[require("mega.flow_work_order.dispatch", audit="确认流式工单开始执行")])
def flow_work_order_confirm_execution(
    order_id: int,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.confirm_dispatch_execution(db, order_id))


@router.post("/flow-work-orders/{order_id}/complete", dependencies=[require("mega.flow_work_order.dispatch", audit="完成流式工单")])
def flow_work_order_complete(
    order_id: int,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.complete_work_order(db, order_id))


@router.post("/flow-work-orders/{order_id}/continue-execution", dependencies=[require("mega.flow_work_order.dispatch", audit="继续执行流式工单")])
def flow_work_order_continue_execution(
    order_id: int,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.continue_execution_work_order(db, order_id))


@router.post("/flow-work-orders/{order_id}/fail", dependencies=[require("mega.flow_work_order.dispatch", audit="标记流式工单执行失败")])
def flow_work_order_fail(
    order_id: int,
    data: dict | None = Body(default=None),
    db: Session = Depends(get_db),
) -> dict:
    return success(
        service.fail_work_order(
            db,
            order_id,
            str((data or {}).get("error_message") or ""),
        )
    )


@router.post("/flow-work-orders/{order_id}/delete", dependencies=[require("mega.flow_work_order.edit", audit="删除流式工单")])
def flow_work_order_delete(
    order_id: int,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.delete_work_order(db, order_id))


@router.post("/flow-work-orders/{order_id}/cancel", dependencies=[require("mega.flow_work_order.edit", audit="作废流式工单")])
def flow_work_order_cancel(
    order_id: int,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.cancel_work_order(db, order_id))
