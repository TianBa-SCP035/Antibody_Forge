"""发现工作台：安排号生成、排期联动、文本清洗、筛选统计与队列状态。"""

from datetime import date, datetime, timedelta
import re
from unittest.mock import patch

from core.errors import ConflictError
from models.discovery import DiscoveryWorkbench
from models.molecular_cell import MolecularLibraryOrder
from models.target import Target
from modules.discovery.workbench import service
from support import DbTestCase

TABLES = (DiscoveryWorkbench, Target, MolecularLibraryOrder)
DISCOVERY_ID_RE = re.compile(r"^DSC-\d{6}-[A-Z0-9]{6}$")
FIXED_TODAY = date(2026, 11, 17)


class DiscoveryWorkbenchIdTests(DbTestCase):
    tables = TABLES

    def test_generate_discovery_id_format(self):
        value = service.generate_discovery_id(datetime(2026, 9, 17, 10, 26, 0))
        self.assertEqual(value[:11], "DSC-260917-")
        self.assertRegex(value, DISCOVERY_ID_RE)

    def test_save_assigns_discovery_id_and_ignores_client_value(self):
        saved = service.save(
            self.db,
            {"project_code": "P1", "discovery_id": "DSC-260917-HACK01"},
        )
        self.assertRegex(saved["discovery_id"], DISCOVERY_ID_RE)
        self.assertNotEqual(saved["discovery_id"], "DSC-260917-HACK01")

        updated = service.save(
            self.db,
            {
                "id": saved["id"],
                "project_code": "P2",
                "discovery_id": "DSC-260917-HACK02",
            },
        )
        self.assertEqual(updated["discovery_id"], saved["discovery_id"])
        self.assertEqual(updated["project_code"], "P2")

    def test_save_batch_assigns_unique_ids(self):
        result = service.save_batch(
            self.db,
            {"items": [{"project_code": "A"}, {"project_code": "B"}]},
        )
        ids = [item["discovery_id"] for item in result["items"]]
        self.assertEqual(len(ids), 2)
        self.assertEqual(len(set(ids)), 2)
        for value in ids:
            self.assertRegex(value, DISCOVERY_ID_RE)

    def test_assign_retries_on_collision(self):
        values = ["DSC-260917-AAAAAA", "DSC-260917-AAAAAA", "DSC-260917-BBBBBB"]
        with patch.object(service, "generate_discovery_id", side_effect=values):
            first = service.save(self.db, {"project_code": "A"})
            second = service.save(self.db, {"project_code": "B"})
        self.assertEqual(first["discovery_id"], "DSC-260917-AAAAAA")
        self.assertEqual(second["discovery_id"], "DSC-260917-BBBBBB")


class DiscoveryWorkbenchScheduleAndCleanTests(DbTestCase):
    tables = TABLES

    def test_schedule_people_and_antigen_options(self):
        saved = service.save(
            self.db,
            {
                "immune_owner": "张三",
                "cell_collector": "李四",
                "boost_cells": "脾细胞\n淋巴结",
                "immune_antigen": "蛋白甲\n蛋白乙",
                "boost_antigen": "自填抗原",
                "screening_antigen": "筛A\n筛B",
            },
        )
        self.assertEqual(saved["immune_owner"], "张三")
        self.assertEqual(saved["cell_collector"], "李四")
        self.assertEqual(saved["boost_cells"], "脾细胞\n淋巴结")
        self.assertEqual(saved["immune_antigen"], "蛋白甲\n蛋白乙")

        options = service.get_options(self.db)
        self.assertEqual(options["immune_antigens"], ["蛋白乙", "蛋白甲"])
        self.assertEqual(options["boost_antigens"], ["自填抗原"])
        self.assertEqual(options["screening_antigens"], ["筛A", "筛B"])
        self.assertEqual(options["immune_owners"], ["张三"])
        self.assertEqual(options["cell_collectors"], ["李四"])
        self.assertEqual(options["priorities"], ["正常", "加急", "非常紧急", "吉吉国王"])
        self.assertIn("RNVM", options["mouse_strains"])
        self.assertIn("RN-VM", options["mouse_strain_categories"])

    def test_mouse_category_is_joined_text_and_harvest_shifts_boost(self):
        harvest = FIXED_TODAY + timedelta(days=30)
        with patch("modules.discovery.workbench.service.today_local", return_value=FIXED_TODAY):
            saved = service.save(
                self.db,
                {
                    "mouse_strain_category": "RN+RL",
                    "harvest_date": harvest.isoformat(),
                    "boost_date": "2020-01-01",
                },
            )
            self.assertEqual(saved["mouse_strain_category"], "RL、RN")
            self.assertEqual(saved["harvest_date"], harvest.isoformat())
            self.assertEqual(saved["boost_date"], (harvest - timedelta(days=5)).isoformat())
            self.assertEqual(saved["status"], "待冲击")
            self.assertEqual(service.get_list(self.db, {"mouse_strain_category": "RN"})["total"], 1)
            self.assertEqual(service.get_list(self.db, {"mouse_strain_category": "RN-KO"})["total"], 0)

            adjusted = service.save(self.db, {"id": saved["id"], "boost_date": (harvest - timedelta(days=1)).isoformat()})
            self.assertEqual(adjusted["boost_date"], (harvest - timedelta(days=1)).isoformat())
            self.assertEqual(adjusted["harvest_date"], harvest.isoformat())

            untouched = service.save(self.db, {"id": saved["id"], "harvest_date": harvest.isoformat()})
            self.assertEqual(untouched["boost_date"], (harvest - timedelta(days=1)).isoformat())

            moved = (harvest + timedelta(days=2)).isoformat()
            shifted = service.save(self.db, {"id": saved["id"], "harvest_date": moved})
            self.assertEqual(shifted["harvest_date"], moved)
            self.assertEqual(shifted["boost_date"], (harvest + timedelta(days=2) - timedelta(days=5)).isoformat())

            today_row = service.save(self.db, {"id": saved["id"], "harvest_date": FIXED_TODAY.isoformat()})
            self.assertEqual(today_row["harvest_date"], FIXED_TODAY.isoformat())

            yesterday = (FIXED_TODAY - timedelta(days=1)).isoformat()
            locked = service.save(self.db, {"id": saved["id"], "harvest_date": yesterday})
            self.assertEqual(locked["harvest_date"], yesterday)
            with self.assertRaisesRegex(ValueError, "剖鼠日期已过，不能再改"):
                service.save(self.db, {"id": saved["id"], "harvest_date": FIXED_TODAY.isoformat()})
            self.db.rollback()
            self.assertEqual(self.db.get(DiscoveryWorkbench, saved["id"]).harvest_date, yesterday)

            wrapped = service.save(self.db, {"harvest_date": "2026-03-01", "status": "规划中"})
            self.assertEqual(wrapped["boost_date"], "2026-02-24")
            self.assertEqual(wrapped["status"], "规划中")

        custom_category = service.save(self.db, {"mouse_strain_category": "自定鼠型+RN"})
        self.assertEqual(custom_category["mouse_strain_category"], "RN、自定鼠型")

        strain = service.save(self.db, {"mouse_strain": "RMB/C+RM"})
        self.assertEqual(strain["mouse_strain"], "RM、RMB/C")
        self.assertEqual(service.get_list(self.db, {"mouse_strain": "RM"})["total"], 1)
        self.assertEqual(service.get_list(self.db, {"mouse_strain": "RMKO"})["total"], 0)
        custom = service.save(self.db, {"mouse_strain": "自定义+RM"})
        self.assertEqual(custom["mouse_strain"], "RM、自定义")

        legacy = self.db.get(DiscoveryWorkbench, saved["id"])
        legacy.mouse_strain_category = "RN+RL"
        self.db.commit()
        self.assertEqual(service.get_list(self.db, {"mouse_strain_category": "RL"})["total"], 1)
        self.assertEqual(service.get_list(self.db, {"mouse_strain_category": "RN-KO"})["total"], 0)

    def test_missing_date_filter_keeps_rows_with_either_date_blank(self):
        future = (FIXED_TODAY + timedelta(days=30)).isoformat()
        with patch("modules.discovery.workbench.service.today_local", return_value=FIXED_TODAY):
            service.save(self.db, {"project_code": "BOTH", "harvest_date": future})
            service.save(self.db, {"project_code": "NONE"})
            service.save(self.db, {"project_code": "BOOST", "boost_date": future})
            harvest_only = service.save(self.db, {"project_code": "HARVEST", "harvest_date": future})
            service.save(self.db, {"id": harvest_only["id"], "boost_date": ""})
            service.save(self.db, {"project_code": "DONE", "status": "已完成"})

            result = service.get_list(self.db, {"boost_filter": "missing_date", "limit": 50})
            codes = {item["project_code"] for item in result["items"]}
            self.assertEqual(codes, {"NONE", "BOOST", "HARVEST"})
            self.assertEqual(result["stats"]["missing_date"], 3)
            self.assertEqual(result["stats"]["boosting"], 2)

    def test_keyword_can_find_system_discovery_id(self):
        saved = service.save(self.db, {"project_code": "P1"})
        result = service.get_list(self.db, {"keyword": saved["discovery_id"]})
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["id"], saved["id"])

    def test_text_cleanup_keeps_breaks_for_multiline_fields_only(self):
        cases = (
            ("project_code", "\tA1\u200c\r\nB2\t", "A1 B2"),
            ("cage_position", "104-5E\n104-5H\t", "104-5E 104-5H"),
            ("mouse_nos", "35\t37\u00a039\r\n40\u200c", "35 37 39\n40"),
            ("screening_antigen", "\nAg-1\tLot1\r\nAg-2\u00a0Lot2\n", "Ag-1 Lot1\nAg-2 Lot2"),
        )
        for field, raw, expected in cases:
            with self.subTest(field=field):
                saved = service.save(self.db, {field: raw})
                self.assertEqual(saved[field], expected)


class DiscoveryHeaderFilterTests(DbTestCase):
    tables = TABLES
    ROWS = [
        dict(project_code="P1", status="规划中", owner="甲", target_name="PD-L1", target_codes=["20R001"],
             mouse_strain="RN、自定义", screening_methods="达普,NGS", harvest_date="2026-01-05",
             mouse_count=5, remark="首批"),
        dict(project_code="P2", status="待剖鼠", owner="乙", target_name="HER2", target_codes=["20R002"],
             mouse_strain="RN", screening_methods="噬菌体", harvest_date=None, mouse_count=None),
        dict(project_code="P3", status="已取消", owner=None, target_name="PD-L1", target_codes=["20R001"],
             mouse_strain=None, screening_methods=None, harvest_date="2026-03-01", mouse_count=8),
    ]

    def setUp(self):
        super().setUp()
        for index, row in enumerate(self.ROWS, start=1):
            self.db.add(DiscoveryWorkbench(discovery_id=f"DSC-260101-{index:06d}", **row))
        self.db.commit()

    def codes(self, *field_filters, **extra):
        data = {"limit": 50, "field_filters": list(field_filters), **extra}
        return [item["project_code"] for item in service.get_list(self.db, data)["items"]]

    def values(self, field, **extra):
        items = service.get_column_values(self.db, {"field": field, **extra})["items"]
        return {item["value"]: item["count"] for item in items}

    def test_filters_and_conditions(self):
        self.assertEqual(sorted(self.codes({"field": "owner", "exclude": ["甲"]})), ["P2", "P3"])
        self.assertEqual(self.codes({"field": "status", "values": ["规划中"]}), ["P1"])
        self.assertEqual(self.codes({"field": "mouse_strain", "values": ["自定义"]}), ["P1"])
        self.assertEqual(self.codes({"field": "harvest_date", "condition": {"op": "blank"}}), ["P2"])
        self.assertEqual(self.codes({"field": "mouse_count", "condition": {"op": "gte", "value": "6"}}), ["P3"])
        self.assertEqual(sorted(self.codes({"field": "target_name", "values": ["PD-L1"]})), ["P1", "P3"])

    def test_top_csv_filter_accepts_custom_values(self):
        self.assertEqual(self.codes(mouse_strain="自定义"), ["P1"])
        self.assertEqual(self.codes(screening_methods=["NGS", "噬菌体"]), ["P2", "P1"])

    def test_header_sort_uses_business_order_and_blanks_last(self):
        self.assertEqual(self.codes(sort_field="status", sort_dir="asc"), ["P1", "P2", "P3"])
        self.assertEqual(self.codes(sort_field="harvest_date", sort_dir="asc"), ["P1", "P3", "P2"])
        self.assertEqual(self.codes(sort_field="harvest_date", sort_dir="desc"), ["P3", "P1", "P2"])

    def test_value_lists(self):
        self.assertEqual(self.values("screening_methods"), {"达普": 1, "NGS": 1, "噬菌体": 1, "": 1})
        self.assertEqual(self.values("status"), {"规划中": 1, "待剖鼠": 1, "已取消": 1})
        own = {"field": "owner", "values": ["甲"]}
        self.assertEqual(self.values("owner", keyword="P", field_filters=[own]), {"甲": 1, "乙": 1, "": 1})
        other = {"field": "status", "values": ["待剖鼠"]}
        self.assertEqual(self.values("owner", field_filters=[other]), {"乙": 1})
        self.assertEqual(self.values("owner", keyword="P1", value_keyword="甲"), {"甲": 1})

    def test_stats_and_export_follow_header_filters(self):
        header = [{"field": "status", "exclude": ["已取消"]}]
        data = service.get_list(self.db, {"limit": 50, "field_filters": header})
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["stats"]["all"], 2)
        self.assertEqual(data["stats"]["cancelled"], 0)
        with patch("utils.excel.build_list_workbook", side_effect=lambda **kw: kw) as built:
            service.export_list_workbook(self.db, {
                "field_filters": header, "sort_field": "project_code", "sort_dir": "desc",
            })
        rows = built.call_args.kwargs["rows"]
        code_at = [h for h, _ in service.EXPORT_COLUMNS].index("项目编号")
        self.assertEqual([row[code_at] for row in rows], ["P2", "P1"])


class DiscoveryWorkbenchQueueTests(DbTestCase):
    tables = TABLES

    def _sorts(self, *row_ids: int) -> list[int | None]:
        self.db.expire_all()
        return [self.db.get(DiscoveryWorkbench, rid).sort_order for rid in row_ids]

    def test_queue_lifecycle_and_terminal_statuses_leave_queue(self):
        r1 = service.save(self.db, {"project_code": "P1"})
        r2 = service.save(self.db, {"project_code": "P2"})
        r3 = service.save(self.db, {"project_code": "P3", "priority": "加急"})
        self.assertEqual(self._sorts(r1["id"], r2["id"], r3["id"]), [2, 3, 1])

        service.reorder(self.db, r2["id"], r1["id"])
        self.assertEqual(self._sorts(r3["id"], r2["id"], r1["id"]), [1, 2, 3])

        for terminal in ("已完成", "已取消"):
            row = service.save(self.db, {"project_code": terminal})
            service.save(self.db, {"id": row["id"], "status": terminal})
            self.assertEqual(self._sorts(r3["id"], r2["id"], r1["id"], row["id"]), [1, 2, 3, None])
            with self.assertRaisesRegex(ValueError, "终态记录不参与排序"):
                service.reorder(self.db, row["id"], r1["id"])

        service.delete(self.db, r1["id"])
        self.assertEqual(self._sorts(r3["id"], r2["id"]), [1, 2])

    def test_screening_methods_round_trip_as_list(self):
        row = service.save(self.db, {"screening_methods": ["NGS", "达普"]})
        self.assertEqual(row["screening_methods"], ["达普", "NGS"])
        self.assertNotIn("screening_method_list", row)

        saved = service.save(
            self.db,
            {"id": row["id"], "screening_methods": ["噬菌体"], "_expected": {"screening_methods": ["达普", "NGS"]}},
        )
        self.assertEqual(saved["screening_methods"], ["噬菌体"])
        with self.assertRaises(ConflictError):
            service.save(self.db, {"id": row["id"], "remark": "冲突", "_expected": {"screening_methods": ["达普"]}})
        self.db.rollback()

    def test_list_rows_round_trip_as_expected(self):
        service.save(
            self.db,
            {
                "project_code": "P1",
                "target_codes": ["20R001"],
                "screening_methods": ["达普"],
                "mouse_count": 3,
                "harvest_date": "2026/1/5",
                "remark": "第一行\n第二行",
            },
        )
        service.save(self.db, {"project_code": "P2"})
        items = service.get_list(self.db, {})["items"]
        for item in items:
            saved = service.save(self.db, {"id": item["id"], "remark": "单条", "_expected": dict(item)})
            self.assertEqual(saved["remark"], "单条")
        items = service.get_list(self.db, {})["items"]
        saved = service.save_batch(
            self.db,
            {"items": [{"id": item["id"], "remark": "批量", "_expected": dict(item)} for item in items]},
        )
        self.assertEqual([row["remark"] for row in saved["items"]], ["批量", "批量"])
