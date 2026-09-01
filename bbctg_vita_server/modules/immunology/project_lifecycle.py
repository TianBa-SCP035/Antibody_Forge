from sqlalchemy import select
from sqlalchemy.orm import Session

from models.immunology import SerumImmWorkbench
from modules.immunology.project_lock import lock_project_by_id
from modules.immunology.serum import service as serum_service
from modules.immunology.workbench import service as workbench_service


def delete_or_revert_project(db: Session, project_id: int) -> str:
    """Refuse when titer data exists; otherwise revert to draft or hard-delete."""
    project = lock_project_by_id(db, project_id)
    if not project:
        raise ValueError("项目不存在")

    blocked = workbench_service.effect_data_block_reason(db, project.experiment_id)
    if blocked:
        raise ValueError(f"{blocked}，不能删除")

    workbench_id = db.scalar(
        select(SerumImmWorkbench.id).where(
            SerumImmWorkbench.experiment_id == project.experiment_id
        )
    )
    if workbench_id is not None:
        workbench_service.unlist(db, int(workbench_id), require_planning=False)
        return "reverted"

    serum_service.delete_serum(db, project_id)
    return "deleted"
