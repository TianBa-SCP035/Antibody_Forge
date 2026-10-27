import threading

from apscheduler.schedulers.background import BackgroundScheduler
from db.session import SessionLocal
from jobs.discovery_status import discovery_auto_update_status_job
from jobs.employee_profile_sync import employee_profile_sync_job
from jobs.labillion_status_sync import labillion_status_sync_job
from jobs.serum_status import auto_update_status_job
from jobs.synthesis_order_sync import synthesis_order_sync_job
from jobs.target_master_sync import target_master_sync_job
from modules.system.audit_context import audit_scope
from modules.system.features import build_job_trigger, get_job_schedule

_scheduler: BackgroundScheduler | None = None
SCHEDULED_JOBS = [
    {
        "id": "serum_auto_update_status",
        "name": "免疫状态自动更新",
        "resource": "project",
        "feature_code": "job.serum_auto_update_status",
        "default_hour": 1,
        "default_minute": 0,
        "func": auto_update_status_job,
    },
    {
        "id": "employee_profile_sync",
        "name": "员工资料同步",
        "resource": "user",
        "feature_code": "job.employee_profile_sync",
        "default_hour": 0,
        "default_minute": 30,
        "func": employee_profile_sync_job,
    },
    {
        "id": "target_master_sync",
        "name": "靶点同步",
        "resource": "target",
        "feature_code": "job.target_master_sync",
        "default_hour": 0,
        "default_minute": 45,
        "func": target_master_sync_job,
    },
    {
        "id": "discovery_auto_update_status",
        "name": "发现状态更新",
        "resource": "discovery_workbench",
        "feature_code": "job.discovery_auto_update_status",
        "default_hour": 1,
        "default_minute": 15,
        "func": discovery_auto_update_status_job,
    },
    {
        "id": "labillion_status_sync",
        "name": "镁伽状态同步",
        "resource": "flow_work_order",
        "feature_code": "job.mega_labillion_status_sync",
        "default_hour": 2,
        "default_minute": 0,
        "func": labillion_status_sync_job,
    },
    {
        "id": "discovery_synthesis_order_sync",
        "name": "合成与验证外部订单同步",
        "resource": "synthesis_progress",
        "feature_code": "job.discovery_synthesis_order_sync",
        "default_hour": 0,
        "default_minute": 20,
        "func": synthesis_order_sync_job,
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
            enabled, schedule = _scheduled_job_config(
                job["feature_code"],
                job["default_hour"],
                job["default_minute"],
            )
            if not enabled:
                continue
            _register_job(_scheduler, job, schedule)
    return _scheduler


def start_scheduler() -> None:
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()


def scheduler_is_running() -> bool:
    return _scheduler is not None and _scheduler.running


def apply_job_schedule(job_code: str) -> bool:
    scheduler = _scheduler
    if scheduler is None or not scheduler.running:
        return False
    job = get_scheduled_job(job_code)
    if job is None:
        return False
    enabled, schedule = _scheduled_job_config(
        job["feature_code"],
        job["default_hour"],
        job["default_minute"],
    )
    if not enabled:
        if scheduler.get_job(job["id"]):
            scheduler.remove_job(job["id"])
        return True
    if scheduler.get_job(job["id"]):
        scheduler.reschedule_job(job["id"], trigger=build_job_trigger(schedule))
        return True
    _register_job(scheduler, job, schedule)
    return True


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
        target=_run_job_with_audit,
        args=(job,),
        name=f"manual-{job['id']}",
        daemon=True,
    )
    thread.start()


def _run_job_with_audit(job: dict) -> None:
    func = job.get("func")
    if not callable(func):
        raise ValueError("定时任务未配置执行函数")
    action = str(job.get("feature_code") or job.get("id") or "job.unknown")
    name = str(job.get("name") or action)
    with audit_scope(
        action,
        name,
        source="job",
        operation_type="update",
        resource=job.get("resource"),
    ):
        func()


def _register_job(scheduler: BackgroundScheduler, job: dict, schedule: dict) -> None:
    scheduler.add_job(
        _run_job_with_audit,
        args=[job],
        trigger=build_job_trigger(schedule),
        id=job["id"],
        replace_existing=True,
    )


def _scheduled_job_config(feature_code: str, default_hour: int, default_minute: int) -> tuple[bool, dict]:
    db = SessionLocal()
    try:
        return get_job_schedule(db, feature_code, default_hour, default_minute)
    finally:
        db.close()
