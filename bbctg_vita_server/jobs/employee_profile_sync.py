from sqlalchemy.orm import Session

from db.external import get_employee_db
from modules.system.employee_sync import sync_employee_profiles
from modules.system.features import run_recorded_job

JOB_CODE = "job.employee_profile_sync"
JOB_NAME = "员工资料定时同步"


def _sync(db: Session) -> dict:
    employee_db_generator = get_employee_db()
    try:
        return sync_employee_profiles(db, next(employee_db_generator))
    finally:
        employee_db_generator.close()


def employee_profile_sync_job() -> None:
    run_recorded_job(JOB_CODE, JOB_NAME, _sync)
