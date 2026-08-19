import logging
from datetime import datetime

from db.session import SessionLocal
from modules.immunology.serum.service import auto_update_status
from modules.system.features import record_job_run, summarize_job_result

JOB_CODE = "job.serum_auto_update_status"
JOB_NAME = "免疫状态自动更新"


def auto_update_status_job() -> None:
    started_at = datetime.now()
    db = SessionLocal()
    result = None
    try:
        result = auto_update_status(db, {})
        logging.info("serum_auto_update_status result=%s", result)
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
        logging.exception("serum_auto_update_status failed")
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
