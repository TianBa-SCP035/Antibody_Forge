import logging
from datetime import datetime

from db.session import SessionLocal
from modules.mega_automation.labillion_sync import sync_non_terminal_work_orders
from modules.system.features import record_job_run, summarize_job_result

JOB_CODE = "job.mega_labillion_status_sync"
JOB_NAME = "镁伽工单状态同步"


def labillion_status_sync_job() -> None:
    started_at = datetime.now()
    db = SessionLocal()
    result = None
    try:
        result = sync_non_terminal_work_orders(db)
        logging.info("labillion_status_sync result=%s", result)
        if result.get("skipped"):
            record_job_run(
                job_code=JOB_CODE,
                job_name=JOB_NAME,
                started_at=started_at,
                finished_at=datetime.now(),
                result="skipped",
                summary="未配置 Labillion 地址，已跳过",
                detail=result,
            )
            return
        record_job_run(
            job_code=JOB_CODE,
            job_name=JOB_NAME,
            started_at=started_at,
            finished_at=datetime.now(),
            result="success",
            summary=summarize_job_result(result),
            detail=result if isinstance(result, dict) else {"result": result},
        )
    except Exception as error:
        db.rollback()
        logging.exception("labillion_status_sync failed")
        record_job_run(
            job_code=JOB_CODE,
            job_name=JOB_NAME,
            started_at=started_at,
            finished_at=datetime.now(),
            result="failed",
            summary="执行失败",
            detail=result if isinstance(result, dict) else {},
            error_message=str(error),
        )
    finally:
        db.close()
