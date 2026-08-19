from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import threading

from db.session import SessionLocal
from jobs.employee_profile_sync import employee_profile_sync_job
from jobs.labillion_status_sync import labillion_status_sync_job
from jobs.serum_status import auto_update_status_job
from jobs.target_master_sync import target_master_sync_job
from modules.system.features import get_job_schedule

_scheduler: BackgroundScheduler | None = None
SCHEDULED_JOBS = [
    {
        "id": "serum_auto_update_status",
        "description": "每天 01:00 自动更新免疫实验状态",
        "feature_code": "job.serum_auto_update_status",
        "default_hour": 1,
        "default_minute": 0,
        "func": auto_update_status_job,
    },
    {
        "id": "employee_profile_sync",
        "description": "每天 00:30 同步外部员工基础资料",
        "feature_code": "job.employee_profile_sync",
        "default_hour": 0,
        "default_minute": 30,
        "func": employee_profile_sync_job,
    },
    {
        "id": "target_master_sync",
        "description": "每天 00:45 同步外部靶点主数据",
        "feature_code": "job.target_master_sync",
        "default_hour": 0,
        "default_minute": 45,
        "func": target_master_sync_job,
    },
    {
        "id": "labillion_status_sync",
        "description": "每天 02:00 同步镁伽非终态工单状态",
        "feature_code": "job.mega_labillion_status_sync",
        "default_hour": 2,
        "default_minute": 0,
        "func": labillion_status_sync_job,
    },
]


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
        _scheduler.configure(
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 300,
            }
        )
        for job in SCHEDULED_JOBS:
            enabled, hour, minute = _scheduled_job_config(
                job["feature_code"],
                job["default_hour"],
                job["default_minute"],
            )
            if not enabled:
                continue
            _scheduler.add_job(
                job["func"],
                trigger=CronTrigger(hour=hour, minute=minute),
                id=job["id"],
                replace_existing=True,
            )
    return _scheduler


def start_scheduler() -> None:
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()


def get_scheduled_job(job_code: str) -> dict | None:
    code = str(job_code or "").strip()
    if not code:
        return None
    for job in SCHEDULED_JOBS:
        if job.get("feature_code") == code:
            return job
    return None


def run_scheduled_job_now(job_code: str) -> None:
    job = get_scheduled_job(job_code)
    if not job:
        raise ValueError("未知定时任务")
    func = job.get("func")
    if not callable(func):
        raise ValueError("定时任务未配置执行函数")
    thread = threading.Thread(
        target=func,
        name=f"manual-{job['id']}",
        daemon=True,
    )
    thread.start()


def _scheduled_job_config(feature_code: str, default_hour: int, default_minute: int) -> tuple[bool, int, int]:
    db = SessionLocal()
    try:
        return get_job_schedule(db, feature_code, default_hour, default_minute)
    finally:
        db.close()
