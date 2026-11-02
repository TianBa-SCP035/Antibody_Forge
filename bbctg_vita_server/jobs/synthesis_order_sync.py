from modules.discovery.synthesis_progress.service import sync_from_one
from modules.system.features import run_recorded_job

JOB_CODE = "job.discovery_synthesis_order_sync"
JOB_NAME = "合成与验证外部订单同步"


def synthesis_order_sync_job() -> None:
    run_recorded_job(
        JOB_CODE,
        JOB_NAME,
        lambda db: sync_from_one(db, created_by="system"),
        skip_summary="未配置 ONE_DB_URL，已跳过",
    )
