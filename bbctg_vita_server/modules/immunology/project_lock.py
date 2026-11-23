from sqlalchemy import select
from sqlalchemy.orm import Session

from models.immunology import SerumImmProject, SerumImmWorkbench


def _lock_linked_workbench(db: Session, experiment_id: str | None) -> None:
    normalized = str(experiment_id or "").strip()
    if not normalized:
        return
    workbench_id = db.scalar(
        select(SerumImmWorkbench.id).where(
            SerumImmWorkbench.experiment_id == normalized
        )
    )
    if workbench_id is not None:
        db.scalar(
            select(SerumImmWorkbench.id)
            .where(SerumImmWorkbench.id == workbench_id)
            .with_for_update()
        )


def lock_project_by_id(
    db: Session,
    project_id: int,
) -> SerumImmProject | None:
    project = db.get(SerumImmProject, int(project_id))
    if not project:
        return None
    _lock_linked_workbench(db, project.experiment_id)
    return db.scalar(
        select(SerumImmProject)
        .where(SerumImmProject.id == int(project_id))
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def lock_experiment_owner(
    db: Session,
    experiment_id: str,
) -> SerumImmProject | None:
    normalized = str(experiment_id or "").strip()
    if not normalized:
        return None
    _lock_linked_workbench(db, normalized)
    return db.scalar(
        select(SerumImmProject)
        .where(SerumImmProject.experiment_id == normalized)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
