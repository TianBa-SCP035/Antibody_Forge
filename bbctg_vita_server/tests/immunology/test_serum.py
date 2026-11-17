"""免疫血清项目统计、并发保存、改号级联与成员匹配规则。"""

import unittest

from sqlalchemy import select

from core.errors import ConflictError
from models.immunology import (
    SerumImmMouse,
    SerumImmProject,
    SerumImmWorkbench,
    SerumTiterOrder,
)
from models.system import SysUser
from models.target import Target
from modules.immunology.project_access import is_project_member, owner_aliases
from modules.immunology.serum import service as serum
from modules.immunology.serum.service import EXPERIMENT_RELATED_MODELS
from support import DbTestCase


class InsertWithRetryTests(DbTestCase):
    tables = (SerumImmProject, SerumImmWorkbench, Target)

    def test_retry_skips_forward_without_rereading(self):
        for eid in ("P101", "P103"):
            self.db.add(SerumImmProject(project_code="P1", experiment_id=eid))
        self.db.commit()
        self.assertEqual(
            [serum.generate_next_id(self.db, "P1", skip=n) for n in range(3)],
            ["P102", "P104", "P105"],
        )


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
            self.db.add(
                SerumImmProject(
                    project_code=eid,
                    experiment_id=eid,
                    owner=owner,
                    pm=pm,
                    project_status=status,
                )
            )
        self.db.commit()

    def test_stats_follow_filters_but_not_own_dimensions(self):
        stats = serum.get_stats(
            self.db,
            {"pm": "PM1", "owner": "甲", "project_status": "completed"},
        )
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["status_counts"]["ongoing"], 2)
        self.assertEqual(stats["status_counts"]["completed"], 1)
        self.assertEqual(
            {item["name"]: item["value"] for item in stats["owner_counts"]},
            {"甲": 2, "乙": 1},
        )

    def test_header_filters_apply_to_list_but_not_own_stat_dimensions(self):
        owners = serum.get_column_values(self.db, {"field": "owner"})["items"]
        self.assertEqual(owners, [{"value": "乙", "count": 2}, {"value": "甲", "count": 2}])
        only_pm1 = {
            "field_filters": [
                {"field": "pm", "values": ["PM1"]},
                {"field": "owner", "values": ["甲"]},
            ]
        }
        listed = serum.get_list(
            self.db,
            {**only_pm1, "sort_field": "project_status", "sort_dir": "desc"},
        )
        self.assertEqual([item["experiment_id"] for item in listed["items"]], ["E2", "E1"])
        self.assertEqual(serum.get_stats(self.db, only_pm1)["total"], 3)

    def test_ongoing_filter_matches_stats_rule(self):
        listed = serum.get_list(self.db, {"project_status": "ongoing"})
        self.assertEqual(
            sorted(item["experiment_id"] for item in listed["items"]),
            ["E1", "E3", "E4"],
        )
        for status in ("待采血", "已检测", "加免中"):
            self.assertTrue(serum.is_ongoing_status(status))
        for status in ("结题", "无效价处死", ""):
            self.assertFalse(serum.is_ongoing_status(status))

    def test_update_status_rejects_blank_and_deleted(self):
        project_id = self.db.scalar(
            select(SerumImmProject.id).where(SerumImmProject.experiment_id == "E1")
        )
        for bad in ("", "  ", "deleted", "x" * 65):
            with self.subTest(status=bad):
                with self.assertRaises(ValueError):
                    serum.update_status(self.db, project_id, bad)


class SerumSaveConflictTests(DbTestCase):
    tables = (
        SerumImmProject,
        SerumImmWorkbench,
        *EXPERIMENT_RELATED_MODELS,
    )

    def _add_project(self) -> SerumImmProject:
        project = SerumImmProject(
            project_code="P1",
            experiment_id="P101",
            project_status="待二免",
            remark="初版",
        )
        self.db.add(project)
        self.db.commit()
        return project

    def test_stale_project_revision_raises_conflict(self):
        project = self._add_project()
        detail = serum.get_detail(self.db, project_id=project.id)
        project.remark = "并发修改"
        self.db.commit()

        with self.assertRaises(ConflictError):
            serum.save_serum(self.db, detail)

    def test_experiment_id_rename_cascades_to_children(self):
        project = self._add_project()
        mouse = SerumImmMouse(experiment_id="P101", group_id="G1")
        order = SerumTiterOrder(
            experiment_id="P101",
            titer_order_id="T1",
            priority="正常",
        )
        self.db.add_all([mouse, order])
        self.db.commit()
        detail = serum.get_detail(self.db, project_id=project.id)
        detail["experiment_id"] = "P199"

        saved = serum.save_serum(self.db, detail)

        self.assertEqual(saved["experiment_id"], "P199")
        self.assertEqual(self.db.get(SerumImmMouse, mouse.id).experiment_id, "P199")
        self.assertEqual(self.db.get(SerumTiterOrder, order.id).experiment_id, "P199")


class ProjectAccessTests(unittest.TestCase):
    def test_member_matching_accepts_username_and_display_name_aliases(self):
        user = SysUser(username="zhangsan", display_name="张三 Li")
        self.assertEqual(owner_aliases(user), {"zhangsan", "张三 Li", "张三"})
        for field, value in (
            ("owner", "zhangsan"),
            ("owner", "张三"),
            ("reviewer", "张三 Li"),
        ):
            with self.subTest(field=field, value=value):
                project = SerumImmProject(**{field: value})
                self.assertTrue(is_project_member(user, project))
