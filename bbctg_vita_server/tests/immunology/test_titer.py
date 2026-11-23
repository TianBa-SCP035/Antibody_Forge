"""免疫效价工单统计与列表筛选规则。"""

from models.immunology import (
    SerumImmMouse,
    SerumImmProject,
    SerumImmStep,
    SerumTiterOrder,
)
from models.mega_automation import MegaFlowWorkOrder
from modules.immunology.titer import service as titer
from support import DbTestCase


class TiterStatsTests(DbTestCase):
    tables = (
        SerumImmProject,
        SerumImmMouse,
        SerumImmStep,
        SerumTiterOrder,
        MegaFlowWorkOrder,
    )

    def test_stats_apply_blood_collection_range_like_list(self):
        self.db.add(
            SerumImmProject(
                project_code="P1",
                experiment_id="E1",
                project_status="已采血",
            )
        )
        for code, blood in (("T1", "2026-10-01"), ("T2", "2026-10-20")):
            self.db.add(
                SerumTiterOrder(
                    experiment_id="E1",
                    titer_order_id=code,
                    blood_collection_date=blood,
                    serum_status="已采血",
                )
            )
        self.db.commit()

        scope = {
            "blood_collection_start": "2026-10-15",
            "blood_collection_end": "2026-10-31",
        }
        self.assertEqual(titer.get_titer_order_stats(self.db, {})["pending"], 2)
        self.assertEqual(titer.get_titer_order_stats(self.db, scope)["pending"], 1)
        self.assertEqual(
            titer.get_titer_order_stats(
                self.db,
                {**scope, "blood_collection_start": "2026-11-01"},
            )["pending"],
            0,
        )

    def test_invalid_date_filter_is_rejected_not_ignored(self):
        with self.assertRaisesRegex(ValueError, "日期筛选格式不正确"):
            titer.get_titer_order_stats(
                self.db,
                {"blood_collection_start": "2026/10/15"},
            )

    def test_header_filters_follow_displayed_mouse_count(self):
        for code in ("E1", "E2"):
            self.db.add(
                SerumImmProject(
                    project_code=code,
                    experiment_id=code,
                    project_status="已采血",
                )
            )
        self.db.add_all(
            [
                SerumImmMouse(experiment_id="E1", mouse_count=" 3 "),
                *(
                    SerumImmMouse(experiment_id="E1", mouse_count=text)
                    for text in ("/", "+2", "-1", "５", "10+2")
                ),
            ]
        )
        self.db.add(
            SerumTiterOrder(
                experiment_id="E1",
                titer_order_id="T1",
                serum_status="已采血",
            )
        )
        self.db.add(
            SerumTiterOrder(
                experiment_id="E2",
                titer_order_id="T2",
                serum_status="已采血",
                mouse_count=5,
            )
        )
        self.db.commit()

        values = titer.get_titer_order_column_values(
            self.db,
            {"field": "mouse_count"},
        )["items"]
        self.assertEqual(values, [{"value": 3, "count": 1}, {"value": 5, "count": 1}])
        three = {"field_filters": [{"field": "mouse_count", "values": [3]}]}
        self.assertEqual(
            [
                (item["titer_order_id"], item["mouse_count"])
                for item in titer.get_titer_order_list(self.db, three)["items"]
            ],
            [("T1", 3)],
        )
        self.assertEqual(titer.get_titer_order_stats(self.db, three)["pending"], 1)
        tested = {
            "field_filters": [{"field": "serum_status", "values": ["已检测"]}]
        }
        self.assertEqual(titer.get_titer_order_list(self.db, tested)["total"], 0)
        self.assertEqual(titer.get_titer_order_stats(self.db, tested)["pending"], 2)
