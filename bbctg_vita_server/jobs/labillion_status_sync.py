from modules.mega_automation.labillion_sync import sync_non_terminal_work_orders
from modules.system.features import run_recorded_job

JOB_CODE = "job.mega_labillion_status_sync"
JOB_NAME = "镁伽工单状态同步"


def labillion_status_sync_job() -> None:
    run_recorded_job(
        JOB_CODE,
        JOB_NAME,
        sync_non_terminal_work_orders,
        skip_summary="未配置 Labillion 地址，已跳过",
    )
