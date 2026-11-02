import json
import unittest

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from models.discovery import DiscoverySynthesisOrder
from models.immunology import SerumImmMouse, SerumImmProject, SerumImmStep, SerumImmWorkbench, SerumTiterOrder
from models.mega_automation import MegaFlowWorkOrder
from models.target import Target
from modules.discovery.synthesis_progress import service as synthesis
from modules.immunology.serum import service as serum
from modules.immunology.titer import service as titer
from support import DbTestCase
from utils.codes import insert_with_retry


class InsertWithRetryTests(DbTestCase):
    tables = (SerumImmProject, SerumImmWorkbench, Target)

    def test_conflict_retries_and_keeps_earlier_changes(self):
        self.db.add(SerumImmProject(project_code="P1", experiment_id="P101", project_status="规划中"))
        self.db.commit()
        self.db.add(SerumImmProject(project_code="P9", experiment_id="P901", project_status="规划中"))
        self.db.flush()

        project = SerumImmProject(project_code="P1", project_status="规划中")

        def assign(attempt):
            project.experiment_id = "P101" if attempt == 0 else serum.generate_next_id(self.db, "P1")

        insert_with_retry(self.db, project, assign)
        self.db.commit()
        self.assertEqual(project.experiment_id, "P102")
        self.assertEqual(
            sorted(self.db.scalars(select(SerumImmProject.experiment_id)).all()),
            ["P101", "P102", "P901"],
        )

    def test_retry_skips_forward_without_rereading(self):
        for eid in ("P101", "P103"):
            self.db.add(SerumImmProject(project_code="P1", experiment_id=eid))
        self.db.commit()
        self.assertEqual(
            [serum.generate_next_id(self.db, "P1", skip=n) for n in range(3)],
            ["P102", "P104", "P105"],
        )

    def test_gives_up_with_business_message(self):
        self.db.add(SerumImmProject(project_code="P1", experiment_id="P101"))
        self.db.commit()
        project = SerumImmProject(project_code="P1")

        def assign(_attempt):
            project.experiment_id = "P101"

        with self.assertRaisesRegex(ValueError, "撞号"):
            insert_with_retry(self.db, project, assign, attempts=2, conflict_message="撞号")

    def test_other_constraint_errors_are_not_retried(self):
        attempts = []
        with self.assertRaises(IntegrityError):
            insert_with_retry(self.db, Target(snum=None), attempts.append)
        self.assertEqual(attempts, [0])


class SerumStatsTests(DbTestCase):
    tables = (SerumImmProject, SerumImmMouse, SerumImmWorkbench, SerumTiterOrder, Target)

    def setUp(self):
        super().setUp()
        rows = [
            ("E1", "甲", "PM1", "待二免"),
            ("E2", "甲", "PM1", "结题"),
            ("E3", "乙", "PM1", "加免中"),
            ("E4", "乙", "PM2", "已采血"),
            ("E5", "乙", "PM2", "deleted"),
        ]
        for eid, owner, pm, status in rows:
            self.db.add(SerumImmProject(project_code=eid, experiment_id=eid, owner=owner, pm=pm, project_status=status))
        self.db.commit()

    def test_stats_follow_filters_but_not_own_dimensions(self):
        stats = serum.get_stats(self.db, {"pm": "PM1", "owner": "甲", "project_status": "completed"})
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["status_counts"]["ongoing"], 2)
        self.assertEqual(stats["status_counts"]["completed"], 1)
        self.assertEqual({item["name"]: item["value"] for item in stats["owner_counts"]}, {"甲": 2, "乙": 1})

    def test_header_filters_apply_to_list_but_not_own_stat_dimensions(self):
        owners = serum.get_column_values(self.db, {"field": "owner"})["items"]
        self.assertEqual(owners, [{"value": "乙", "count": 2}, {"value": "甲", "count": 2}])
        only_pm1 = {"field_filters": [{"field": "pm", "values": ["PM1"]}, {"field": "owner", "values": ["甲"]}]}
        listed = serum.get_list(self.db, {**only_pm1, "sort_field": "project_status", "sort_dir": "desc"})
        self.assertEqual([item["experiment_id"] for item in listed["items"]], ["E2", "E1"])
        self.assertEqual(serum.get_stats(self.db, only_pm1)["total"], 3)

    def test_ongoing_filter_matches_stats_rule(self):
        listed = serum.get_list(self.db, {"project_status": "ongoing"})
        self.assertEqual(sorted(item["experiment_id"] for item in listed["items"]), ["E1", "E3", "E4"])
        for status in ("待采血", "已检测", "加免中"):
            self.assertTrue(serum.is_ongoing_status(status))
        for status in ("结题", "无效价处死", ""):
            self.assertFalse(serum.is_ongoing_status(status))

    def test_update_status_rejects_blank_and_deleted(self):
        project_id = self.db.scalar(select(SerumImmProject.id).where(SerumImmProject.experiment_id == "E1"))
        for bad in ("", "  ", "deleted", "x" * 65):
            with self.assertRaises(ValueError):
                serum.update_status(self.db, project_id, bad)


class TiterStatsTests(DbTestCase):
    tables = (SerumImmProject, SerumImmMouse, SerumImmStep, SerumTiterOrder, MegaFlowWorkOrder)

    def setUp(self):
        super().setUp()
        raw = self.db.connection().connection.dbapi_connection
        raw.create_function("json_length", 1, lambda value: len(json.loads(value or "[]")))
        raw.create_function(
            "json_overlaps", 2, lambda left, right: bool(set(json.loads(left or "[]")) & set(json.loads(right or "[]")))
        )

    def test_stats_apply_blood_collection_range_like_list(self):
        self.db.add(SerumImmProject(project_code="P1", experiment_id="E1", project_status="已采血"))
        for code, blood in (("T1", "2026-10-01"), ("T2", "2026-10-20")):
            self.db.add(SerumTiterOrder(experiment_id="E1", titer_order_id=code, blood_collection_date=blood, serum_status="已采血"))
        self.db.commit()

        scope = {"blood_collection_start": "2026-10-15", "blood_collection_end": "2026-10-31"}
        self.assertEqual(titer.get_titer_order_stats(self.db, {})["pending"], 2)
        self.assertEqual(titer.get_titer_order_stats(self.db, scope)["pending"], 1)
        self.assertEqual(titer.get_titer_order_stats(self.db, {**scope, "blood_collection_start": "2026-11-01"})["pending"], 0)

    def test_header_filters_follow_displayed_mouse_count(self):
        for code in ("E1", "E2"):
            self.db.add(SerumImmProject(project_code=code, experiment_id=code, project_status="已采血"))
        self.db.add_all([SerumImmMouse(experiment_id="E1", mouse_count=" 3 "), SerumImmMouse(experiment_id="E1", mouse_count="/")])
        self.db.add(SerumTiterOrder(experiment_id="E1", titer_order_id="T1", serum_status="已采血"))
        self.db.add(SerumTiterOrder(experiment_id="E2", titer_order_id="T2", serum_status="已采血", mouse_count=5))
        self.db.commit()

        values = titer.get_titer_order_column_values(self.db, {"field": "mouse_count"})["items"]
        self.assertEqual(values, [{"value": 3, "count": 1}, {"value": 5, "count": 1}])
        three = {"field_filters": [{"field": "mouse_count", "values": [3]}]}
        self.assertEqual([item["titer_order_id"] for item in titer.get_titer_order_list(self.db, three)["items"]], ["T1"])
        self.assertEqual(titer.get_titer_order_stats(self.db, three)["pending"], 1)
        tested = {"field_filters": [{"field": "serum_status", "values": ["已检测"]}]}
        self.assertEqual(titer.get_titer_order_list(self.db, tested)["total"], 0)
        self.assertEqual(titer.get_titer_order_stats(self.db, tested)["pending"], 2)


class SynthesisSyncQueueTests(DbTestCase):
    tables = (DiscoverySynthesisOrder, Target)

    def _row(self, code, sort_order):
        row = DiscoverySynthesisOrder(
            synthesis_order_id=code,
            status=synthesis.STATUS_WAIT_ORDER,
            order_kind=synthesis.ORDER_KIND_NORMAL,
            supply_mode=synthesis.SUPPLY_MODE_ARRIVAL,
            priority="正常",
            sort_order=sort_order,
        )
        self.db.add(row)
        return row

    def test_terminal_rows_leave_queue_in_same_transaction(self):
        first, done, last = self._row("S1", 1), self._row("S2", 2), self._row("S3", 3)
        self.db.commit()

        done.status = synthesis.STATUS_COMPLETED
        synthesis.settle_queue_after_sync(self.db)
        self.db.commit()
        self.assertEqual((first.sort_order, done.sort_order, last.sort_order), (1, None, 2))


if __name__ == "__main__":
    unittest.main()
