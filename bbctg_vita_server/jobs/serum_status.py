from modules.immunology.serum.service import auto_update_status
from modules.system.features import run_recorded_job

JOB_CODE = "job.serum_auto_update_status"
JOB_NAME = "免疫状态自动更新"


def auto_update_status_job() -> None:
    run_recorded_job(JOB_CODE, JOB_NAME, lambda db: auto_update_status(db, {}))
