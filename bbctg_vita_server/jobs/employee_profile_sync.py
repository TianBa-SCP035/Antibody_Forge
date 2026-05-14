import logging
from datetime import datetime

from db.external import get_employee_db
from db.session import SessionLocal
from modules.system.employee_sync import sync_employee_profiles
from modules.system.features import record_job_run, summarize_job_result

JOB_CODE = "job.employee_profile_sync"
JOB_NAME = "员工资料定时同步"


def employee_profile_sync_job() -> None:
    started_at = datetime.now()
    db = SessionLocal()
    employee_db_generator = None
    result = None
    try:
        employee_db_generator = get_employee_db()
        employee_db = next(employee_db_generator)
        result = sync_employee_profiles(db, employee_db)
        logging.info("employee_profile_sync result=%s", result)
        record_job_run(
            job_code=JOB_CODE,
            job_name=JOB_NAME,
            started_at=started_at,
            finished_at=datetime.now(),
            result="success",
            summary=summarize_job_result(result),
            detail=result,
        )
    except Exception as error:
        db.rollback()
        logging.exception("employee_profile_sync failed")
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
        if employee_db_generator is not None:
            employee_db_generator.close()
