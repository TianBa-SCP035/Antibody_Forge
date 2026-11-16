from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import sessionmaker

from models.immunology import (
    SerumImmMouse,
    SerumImmProject,
    SerumImmWorkbench,
)
from models.target import Target
from modules.immunology.serum.service import EXPERIMENT_RELATED_MODELS
import modules.immunology.workbench.service as workbench_service
from support import DbTestCase, memory_engine
from utils.workbench_queue import queue_rows


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
            patch.object(workbench_service, "lock_queue"),
            patch(
                "utils.workbench_queue.queue_rows",
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

    def test_queue_rows_include_draft_and_missing_project_statuses(self):
        workbench_model = workbench_service.SerumImmWorkbench
        project_model = workbench_service.SerumImmProject
        engine = memory_engine(project_model, workbench_model)
        self.addCleanup(engine.dispose)
        with sessionmaker(bind=engine, expire_on_commit=False)() as db:
            default_plan = workbench_model(
                experiment_id="QUEUE-DRAFT-PLAN",
                sort_order=1,
            )
            missing_project = workbench_model(
                experiment_id="QUEUE-MISSING-PROJECT",
                plan_status=workbench_service.PLAN_STATUS_STARTED,
                sort_order=2,
            )
            db.add_all([default_plan, missing_project])
            db.commit()
            queued_ids = {
                row.id for row in queue_rows(db, workbench_service.QUEUE_SPEC)
            }
            self.assertEqual(queued_ids, {default_plan.id, missing_project.id})

    def test_reorder_rejects_started_row_whose_project_ended(self):
        workbench_model = workbench_service.SerumImmWorkbench
        project_model = workbench_service.SerumImmProject
        engine = memory_engine(project_model, workbench_model)
        self.addCleanup(engine.dispose)
        with sessionmaker(bind=engine, expire_on_commit=False)() as db:
            ended = workbench_model(
                experiment_id="QUEUE-ENDED",
                plan_status=workbench_service.PLAN_STATUS_STARTED,
                sort_order=1,
            )
            draft = workbench_model(plan_status="草稿", sort_order=2)
            db.add_all([ended, draft, project_model(experiment_id="QUEUE-ENDED", project_status="结题")])
            db.commit()
            with self.assertRaisesRegex(ValueError, "终态记录不参与排序"):
                workbench_service.reorder(db, draft.id, ended.id)


class HeaderFilterTests(unittest.TestCase):
    def test_started_rows_filter_by_project_values(self):
        workbench_model = workbench_service.SerumImmWorkbench
        project_model = workbench_service.SerumImmProject
        engine = memory_engine(project_model, workbench_model)
        self.addCleanup(engine.dispose)
        with sessionmaker(bind=engine, expire_on_commit=False)() as db:
            db.add_all([
                workbench_model(
                    experiment_id="E1",
                    plan_status=workbench_service.PLAN_STATUS_STARTED,
                    owner="旧人",
                    reviewer="旧审",
                ),
                project_model(experiment_id="E1", owner="张三", reviewer="王五"),
                workbench_model(experiment_id="E2", plan_status="草稿", owner="李四", reviewer="王五"),
                workbench_model(experiment_id="E3", plan_status="草稿"),
            ])
            db.commit()

            started = db.query(workbench_model).filter_by(experiment_id="E1").one()
            overlay = workbench_service._overlay_identity(started.to_dict(), db.query(project_model).one())
            self.assertEqual(overlay["reviewer"], "王五")
            by_reviewer = workbench_service._apply_list_filters(
                workbench_service._count_stmt(), {"reviewer": "王五"}, db=db
            )
            self.assertEqual(db.scalar(by_reviewer), 2)
            stale_reviewer = workbench_service._apply_list_filters(
                workbench_service._count_stmt(), {"reviewer": "旧审"}, db=db
            )
            self.assertEqual(db.scalar(stale_reviewer), 0)

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


class ImmunologyWorkbenchQueueTests(DbTestCase):
    tables = (
        SerumImmProject,
        SerumImmWorkbench,
        *EXPERIMENT_RELATED_MODELS,
        Target,
    )

    def _sorts(self, *row_ids: int) -> list[int | None]:
        self.db.expire_all()
        return [self.db.get(SerumImmWorkbench, rid).sort_order for rid in row_ids]

    def test_queue_placement_priority_reorder_terminal_and_delete(self):
        r1 = workbench_service.save(self.db, {"target_name": "T1"})
        r2 = workbench_service.save(self.db, {"target_name": "T2"})
        r3 = workbench_service.save(self.db, {"target_name": "T3", "priority": "加急"})
        self.assertEqual(self._sorts(r1["id"], r2["id"], r3["id"]), [2, 3, 1])

        # 提高优先级进入加急区末尾；降级回到正常区首位
        workbench_service.save(self.db, {"id": r2["id"], "priority": "加急"})
        self.assertEqual(self._sorts(r1["id"], r2["id"], r3["id"]), [3, 2, 1])
        workbench_service.save(self.db, {"id": r3["id"], "priority": "正常"})
        self.assertEqual(self._sorts(r1["id"], r2["id"], r3["id"]), [3, 1, 2])

        # 同优先级拖动重排；同 id 返回单行；新行指定 sort_order 吸附到对应优先级区间内
        workbench_service.reorder(self.db, r1["id"], r3["id"])
        self.assertEqual(self._sorts(r2["id"], r1["id"], r3["id"]), [1, 2, 3])
        same = workbench_service.reorder(self.db, r1["id"], r1["id"])
        self.assertEqual([item["id"] for item in same["items"]], [r1["id"]])

        r4 = workbench_service.save(self.db, {"target_name": "T4", "sort_order": 2})
        self.assertEqual(self._sorts(r2["id"], r4["id"], r1["id"], r3["id"]), [1, 2, 3, 4])

        # 终态出队并顺移；终态不参与排序；删除后顺移
        workbench_service.save(self.db, {"id": r4["id"], "plan_status": "已取消"})
        self.assertEqual(self._sorts(r2["id"], r4["id"], r1["id"], r3["id"]), [1, None, 2, 3])
        with self.assertRaisesRegex(ValueError, "终态记录不参与排序"):
            workbench_service.reorder(self.db, r4["id"], r1["id"])

        workbench_service.delete(self.db, r1["id"])
        self.assertEqual(self._sorts(r2["id"], r3["id"]), [1, 2])

    def test_expected_conflict_detection_single_and_batch(self):
        from core.errors import ConflictError

        r1 = workbench_service.save(self.db, {"target_name": "T1", "remark": "初版"})
        r2 = workbench_service.save(self.db, {"target_name": "T2", "remark": "二号"})

        # 批量保存中某一行陈旧，整批冲突且任何行都不落库
        with self.assertRaises(ConflictError):
            workbench_service.save_batch(
                self.db,
                {
                    "items": [
                        {"id": r1["id"], "remark": "不应写入", "_expected": {"remark": "初版"}},
                        {"id": r2["id"], "remark": "新二", "_expected": {"remark": "过期"}},
                    ]
                },
            )
        self.db.rollback()
        self.assertEqual(self.db.get(SerumImmWorkbench, r1["id"]).remark, "初版")

        # 匹配 _expected 正常保存，且忽略 sort_order 与只读字段
        updated = workbench_service.save_batch(
            self.db,
            {
                "items": [
                    {
                        "id": r1["id"],
                        "remark": "新版",
                        "_expected": {"remark": " 初版 ", "sort_order": 999, "created_at": "bad"},
                    }
                ]
            },
        )
        self.assertEqual(updated["items"][0]["remark"], "新版")

        # 单行 save 陈旧冲突；不带 _expected 保持兼容
        with self.assertRaises(ConflictError):
            workbench_service.save(
                self.db,
                {"id": r1["id"], "remark": "再改", "_expected": {"remark": "初版"}},
            )
        self.db.rollback()
        plain = workbench_service.save(self.db, {"id": r1["id"], "remark": "无基线覆盖"})
        self.assertEqual(plain["remark"], "无基线覆盖")

    def test_list_rows_round_trip_as_expected(self):
        workbench_service.save(
            self.db,
            {
                "target_name": "T1",
                "species_cross": ["猴", "人"],
                "immuno_method": "LNP，蛋白",
                "mouse_count": 6,
                "remark": "第一行\n第二行",
            },
        )
        workbench_service.save(self.db, {"target_name": "T2"})
        items = workbench_service.get_list(self.db, {})["items"]
        for item in items:
            saved = workbench_service.save(self.db, {"id": item["id"], "remark": "单条", "_expected": dict(item)})
            self.assertEqual(saved["remark"], "单条")
        items = workbench_service.get_list(self.db, {})["items"]
        saved = workbench_service.save_batch(
            self.db,
            {"items": [{"id": item["id"], "remark": "批量", "_expected": dict(item)} for item in items]},
        )
        self.assertEqual([row["remark"] for row in saved["items"]], ["批量", "批量"])

    def test_expected_compares_with_list_values(self):
        from core.errors import ConflictError

        created = workbench_service.save(self.db, {"target_name": "T1"})
        row = self.db.get(SerumImmWorkbench, created["id"])
        row.mouse_strain = "旧表头"
        self.db.add(SerumImmMouse(experiment_id=row.experiment_id, group_id="G1", mouse_strain="BALB/c"))
        self.db.commit()
        listed = workbench_service.get_list(self.db, {})["items"][0]
        self.assertEqual(listed["mouse_strain"], "BALB/c")

        # 前端基线是列表展示值：品系显示方案分组，而不是工作台表头
        saved = workbench_service.save(
            self.db,
            {"id": row.id, "mouse_strain": "DBA", "_expected": {"mouse_strain": "BALB/c"}},
        )
        self.assertEqual(saved["mouse_strain"], "DBA")

        with self.assertRaises(ConflictError):
            workbench_service.save(
                self.db,
                {"id": row.id, "mouse_strain": "C57", "_expected": {"mouse_strain": "BALB/c"}},
            )
        self.db.rollback()

    def test_detail_reorder_and_scheme_save_show_group_strains(self):
        created = workbench_service.save(self.db, {"target_name": "T1"})
        row = self.db.get(SerumImmWorkbench, created["id"])
        row.mouse_strain = "旧表头"
        self.db.add_all([
            SerumImmMouse(experiment_id=row.experiment_id, group_id="G1", mouse_strain="BALB/c"),
            SerumImmMouse(experiment_id=row.experiment_id, group_id="G2", mouse_strain="C57"),
        ])
        self.db.commit()

        detail = workbench_service.get_detail(self.db, row.id)
        self.assertEqual(detail["mouse_strain"], "BALB/c、C57")
        reordered = workbench_service.reorder(self.db, row.id, row.id)["items"][0]
        self.assertEqual(reordered["mouse_strain"], "BALB/c、C57")
        saved = workbench_service.save_scheme(
            self.db,
            {
                "id": row.id,
                "scheme_revision": detail["scheme_revision"],
                **{key: detail.get(key) or [] for key in ("mouse_groups", "antigens", "steps", "titer_targets", "titer_pcs")},
            },
        )
        self.assertEqual(saved["mouse_strain"], "BALB/c、C57")

    def test_multi_options_round_trip_as_list(self):
        from core.errors import ConflictError

        row = workbench_service.save(self.db, {"species_cross": ["猴", "人"], "immuno_method": "LNP，蛋白"})
        self.assertEqual(row["species_cross"], ["人", "猴"])
        self.assertEqual(row["immuno_method"], ["蛋白", "LNP"])
        self.assertEqual(self.db.get(SerumImmWorkbench, row["id"]).species_cross, "人,猴")

        saved = workbench_service.save(
            self.db,
            {"id": row["id"], "species_cross": [], "_expected": {"species_cross": ["人", "猴"]}},
        )
        self.assertEqual(saved["species_cross"], [])
        with self.assertRaises(ConflictError):
            workbench_service.save(self.db, {"id": row["id"], "remark": "冲突", "_expected": {"immuno_method": ["蛋白"]}})
        self.db.rollback()
        with self.assertRaisesRegex(ValueError, "免疫方式包含不允许的选项"):
            workbench_service.save(self.db, {"id": row["id"], "immuno_method": ["自由文本"]})
        self.db.rollback()


if __name__ == "__main__":
    unittest.main()
