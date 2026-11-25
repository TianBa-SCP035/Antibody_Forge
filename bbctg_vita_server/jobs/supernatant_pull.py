from modules.supernatant_receive.query import pull_pending, summarize
from modules.system.features import run_recorded_job

JOB_CODE = "job.discovery_supernatant_pull"
JOB_NAME = "合成公司上清补查"


def supernatant_pull_job() -> None:
    run_recorded_job(JOB_CODE, JOB_NAME, pull_pending, summarize=summarize)
