from sqlalchemy.orm import Session

from db.external import get_employee_db
from modules.system.features import run_recorded_job
from modules.system.target_sync import sync_targets

JOB_CODE = "job.target_master_sync"
JOB_NAME = "靶点主数据定时同步"


def _sync(db: Session) -> dict:
    source_db_generator = get_employee_db()
    try:
        return sync_targets(db, next(source_db_generator), enrich_uniprot=True)
    finally:
        source_db_generator.close()


def _summary(result: dict) -> str:
    summary = f"新增 {result['created']} 条，更新 {result['updated']} 条，下架 {result['deactivated']} 条"
    if result.get("uniprot_enriched"):
        summary += f"，UniProt补齐 {result['uniprot_enriched']} 条"
    skipped = sum(result["skipped"].values())
    if skipped:
        summary += f"，跳过 {skipped} 条"
    return summary


def target_master_sync_job() -> None:
    run_recorded_job(JOB_CODE, JOB_NAME, _sync, summarize=_summary)
