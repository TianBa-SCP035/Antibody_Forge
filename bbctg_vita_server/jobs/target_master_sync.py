import logging
from datetime import datetime

from db.external import get_employee_db
from db.session import SessionLocal
from modules.system.features import record_job_run
from modules.system.target_sync import sync_targets


JOB_CODE = "job.target_master_sync"
JOB_NAME = "靶点主数据定时同步"


def target_master_sync_job() -> None:
    started_at = datetime.now()
    db = SessionLocal()
    source_db_generator = None
    result = None
    try:
        source_db_generator = get_employee_db()
        source_db = next(source_db_generator)
        result = sync_targets(db, source_db)
        logging.info("target_master_sync result=%s", result)
        skipped = sum(result["skipped"].values())
        summary = (
            f"新增 {result['created']} 条，"
            f"更新 {result['updated']} 条，"
            f"下架 {result['deactivated']} 条"
        )
        if skipped:
            summary += f"，跳过 {skipped} 条"
        record_job_run(
            job_code=JOB_CODE,
            job_name=JOB_NAME,
            started_at=started_at,
            finished_at=datetime.now(),
            result="success",
            summary=summary,
            detail=result,
        )
    except Exception as error:
        db.rollback()
        logging.exception("target_master_sync failed")
        record_job_run(
            job_code=JOB_CODE,
            job_name=JOB_NAME,
            started_at=started_at,
            finished_at=datetime.now(),
            result="failed",
            summary="执行失败",
            detail=result or {},
            error_message=str(error),
        )
    finally:
        db.close()
        if source_db_generator is not None:
            source_db_generator.close()
