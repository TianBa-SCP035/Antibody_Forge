from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from jobs.serum_status import auto_update_status_job

_scheduler: BackgroundScheduler | None = None
SCHEDULED_JOBS = [
    {
        "id": "serum_auto_update_status",
        "description": "每天 01:00 自动更新血清实验状态",
        "trigger": CronTrigger(hour=1, minute=0),
        "func": auto_update_status_job,
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
            _scheduler.add_job(
                job["func"],
                trigger=job["trigger"],
                id=job["id"],
                replace_existing=True,
            )
    return _scheduler


def start_scheduler() -> None:
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
