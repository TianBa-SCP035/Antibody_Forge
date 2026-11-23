from sqlalchemy.orm import Session

from modules.discovery.workbench.service import advance_expired_boosts
from modules.system.features import run_recorded_job

JOB_CODE = "job.discovery_auto_update_status"
JOB_NAME = "抗体发现状态自动更新"


def _advance(db: Session) -> dict:
    updated_count = advance_expired_boosts(db)
    db.commit()
    return {"updated_count": updated_count}


def discovery_auto_update_status_job() -> None:
    run_recorded_job(
        JOB_CODE,
        JOB_NAME,
        _advance,
        summarize=lambda result: f"更新 {result['updated_count']} 条",
    )
