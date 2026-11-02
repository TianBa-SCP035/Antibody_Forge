from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import sessionmaker

import modules.immunology.workbench.service as workbench_service
from support import memory_engine


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
        engine = memory_engine(project_model, workbench_model)
        self.addCleanup(engine.dispose)
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


class HeaderFilterTests(unittest.TestCase):
    def test_started_rows_filter_by_project_values(self):
        workbench_model = workbench_service.SerumImmWorkbench
        project_model = workbench_service.SerumImmProject
        engine = memory_engine(project_model, workbench_model)
        self.addCleanup(engine.dispose)
        with sessionmaker(bind=engine, expire_on_commit=False)() as db:
            db.add_all([
                workbench_model(experiment_id="E1", plan_status=workbench_service.PLAN_STATUS_STARTED, owner="旧人"),
                project_model(experiment_id="E1", owner="张三"),
                workbench_model(experiment_id="E2", plan_status="草稿", owner="李四"),
                workbench_model(experiment_id="E3", plan_status="草稿"),
            ])
            db.commit()

            values = workbench_service.get_column_values(db, {"field": "owner"})["items"]
            self.assertEqual(
                sorted((item["value"], item["count"]) for item in values),
                [("", 1), ("张三", 1), ("李四", 1)],
            )

            filtered = workbench_service._apply_list_filters(
                workbench_service._count_stmt(),
                {"field_filters": [{"field": "owner", "values": ["张三", ""]}]},
                db=db,
            )
            self.assertEqual(db.scalar(filtered), 2)
            with self.assertRaises(ValueError):
                workbench_service.get_column_values(db, {"field": "target_name"})

    def test_stats_ignore_own_status_conditions(self):
        workbench_model = workbench_service.SerumImmWorkbench
        engine = memory_engine(workbench_service.SerumImmProject, workbench_model)
        self.addCleanup(engine.dispose)
        with sessionmaker(bind=engine, expire_on_commit=False)() as db:
            db.add_all([
                workbench_model(experiment_id="E1", plan_status="草稿", owner="张三"),
                workbench_model(experiment_id="E2", plan_status="已取消", owner="张三"),
                workbench_model(experiment_id="E3", plan_status="草稿", owner="李四"),
            ])
            db.commit()

            stats = workbench_service._list_stats(db, {
                "display_status": "草稿",
                "field_filters": [
                    {"field": "status", "values": ["草稿"]},
                    {"field": "owner", "values": ["张三"]},
                ],
            })
            self.assertEqual((stats["all"], stats["planned"], stats["cancelled"]), (2, 1, 1))


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
