import logging
from datetime import datetime

from db.session import SessionLocal
from modules.discovery.synthesis_progress.service import sync_from_one
from modules.system.features import record_job_run, summarize_job_result

JOB_CODE = "job.discovery_synthesis_order_sync"
JOB_NAME = "合成与验证外部订单同步"


def synthesis_order_sync_job() -> None:
    started_at = datetime.now()
    db = SessionLocal()
    result = None
    try:
        result = sync_from_one(db, created_by="system")
        logging.info("synthesis_order_sync result=%s", result)
        if result.get("skipped"):
            record_job_run(
                job_code=JOB_CODE,
                job_name=JOB_NAME,
                started_at=started_at,
                finished_at=datetime.now(),
                result="skipped",
                summary=str(result.get("message") or "未配置 ONE_DB_URL，已跳过"),
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
        logging.exception("synthesis_order_sync failed")
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
