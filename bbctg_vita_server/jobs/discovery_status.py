import logging
from datetime import datetime

from db.session import SessionLocal
from modules.discovery.workbench.service import advance_expired_boosts
from modules.system.features import record_job_run

JOB_CODE = "job.discovery_auto_update_status"
JOB_NAME = "抗体发现状态自动更新"


def discovery_auto_update_status_job() -> None:
    started_at = datetime.now()
    db = SessionLocal()
    updated_count = 0
    try:
        updated_count = advance_expired_boosts(db)
        db.commit()
        result = {"updated_count": updated_count}
        logging.info("discovery_auto_update_status result=%s", result)
        record_job_run(
            job_code=JOB_CODE,
            job_name=JOB_NAME,
            started_at=started_at,
            finished_at=datetime.now(),
            result="success",
            summary=f"更新 {updated_count} 条",
            detail=result,
        )
    except Exception as error:
        db.rollback()
        logging.exception("discovery_auto_update_status failed")
        record_job_run(
            job_code=JOB_CODE,
            job_name=JOB_NAME,
            started_at=started_at,
            finished_at=datetime.now(),
            result="failed",
            summary="执行失败",
            detail={"updated_count": updated_count},
            error_message=str(error),
        )
        raise
    finally:
        db.close()
