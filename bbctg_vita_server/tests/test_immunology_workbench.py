from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

from db.session import Base
import modules.immunology.workbench.service as workbench_service


@compiles(BigInteger, "sqlite")
def _compile_big_integer_for_sqlite(_type, _compiler, **_kwargs):
    return "INTEGER"


class ProjectQueueTests(unittest.TestCase):
    def test_project_terminal_transition_only_repairs_required_successors(self):
        terminal = SimpleNamespace(
            id=1,
            plan_status=workbench_service.PLAN_STATUS_STARTED,
            experiment_id="EXP-1",
            sort_order=2,
        )
        positioned = SimpleNamespace(
            id=2,
            plan_status="草稿",
            experiment_id=None,
            sort_order=3,
        )
        db = MagicMock()
        db.scalar.return_value = terminal
        with (
            patch.object(workbench_service, "_lock_queue"),
            patch.object(
                workbench_service,
                "_queue_rows",
                return_value=[terminal, positioned],
            ),
        ):
            workbench_service.sync_project_queue_status(
                db,
                "EXP-1",
                is_terminal=True,
            )
        self.assertIsNone(terminal.sort_order)
        self.assertEqual(positioned.sort_order, 1)

    def test_queue_rows_include_null_and_missing_project_statuses(self):
        workbench_model = workbench_service.SerumImmWorkbench
        project_model = workbench_service.SerumImmProject
        engine = create_engine("sqlite+pysqlite:///:memory:")
        self.addCleanup(engine.dispose)
        Base.metadata.create_all(
            engine,
            tables=[project_model.__table__, workbench_model.__table__],
        )
        with sessionmaker(bind=engine, expire_on_commit=False)() as db:
            default_plan = workbench_model(
                experiment_id="QUEUE-NULL-PLAN",
                plan_status=None,
                sort_order=1,
            )
            missing_project = workbench_model(
                experiment_id="QUEUE-MISSING-PROJECT",
                plan_status=workbench_service.PLAN_STATUS_STARTED,
                sort_order=2,
            )
            db.add_all([default_plan, missing_project])
            db.commit()
            queued_ids = {row.id for row in workbench_service._queue_rows(db)}
            self.assertEqual(queued_ids, {default_plan.id, missing_project.id})


class SchemeStrainTextTests(unittest.TestCase):
    def test_scheme_join_keeps_group_order_with_ideographic_comma(self):
        groups = [
            {"mouse_strain": " RMB/C ", "mouse_strain_category": "RL"},
            {"mouse_strain": "RM", "mouse_strain_category": "RM"},
            {"mouse_strain": "RM", "mouse_strain_category": ""},
        ]
        self.assertEqual(workbench_service._join_strain_parts(groups, "mouse_strain"), "RMB/C、RM")
        self.assertEqual(workbench_service._join_strain_parts(groups, "mouse_strain_category"), "RL、RM")
        self.assertIsNone(workbench_service._join_strain_parts([], "mouse_strain"))


if __name__ == "__main__":
    unittest.main()
