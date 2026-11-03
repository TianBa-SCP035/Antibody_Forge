import unittest
from unittest.mock import patch

from models.discovery import DiscoverySynthesisOrder
from models.target import Target
from modules.discovery.synthesis_progress import one_sync, service
from support import DbTestCase


class SynthesisProgressServiceTests(DbTestCase):
    tables = (Target, DiscoverySynthesisOrder)

    def _completed_secreted_order(self, db):
        row = service.save(
            db,
            {
                "target_name": "IL-2",
                "target_type": "分泌型",
                "order_no": "CN2602120001585",
                "arrival_date": "2026-03-17",
                "affinity_date": "2026-03-26",
            },
            created_by="测试员",
        )
        self.assertEqual(row["flow_status"], "流式不适用")
        self.assertEqual(row["status"], "已完成")
        return row

    def test_target_type_change_reopens_or_completes_order(self):
        with self.Session() as db:
            row = self._completed_secreted_order(db)
            # 改成非分泌型后要补流式，已完成不能再保留
            row = service.save(db, {"id": row["id"], "target_type": "I型跨膜"})
            self.assertEqual(row["flow_status"], "流式待检测")
            self.assertEqual(row["status"], "检测中")
            self.assertIsNotNone(row["sort_order"])

            row = service.save(db, {"id": row["id"], "target_type": "分泌型"})
            self.assertEqual(row["flow_status"], "流式不适用")
            self.assertEqual(row["status"], "已完成")

            # 同值回写不算靶点类型变化，已完成保持
            row = service.save(db, {"id": row["id"], "target_type": "分泌型", "remark": "复核"})
            self.assertEqual(row["status"], "已完成")

    def test_assay_status_checks_use_values_from_same_payload(self):
        with self.Session() as db:
            row = service.save(
                db,
                {"target_name": "B7-H4", "order_no": "CN1", "arrival_date": "2026-03-17", "report_reason": "抗原重检"},
                created_by="测试员",
            )
            with self.assertRaisesRegex(ValueError, "请先清除未出报告原因"):
                service.save(db, {"id": row["id"], "affinity_status": "亲和力检测中"}, created_by="张赞")

            row = service.save(
                db,
                {"id": row["id"], "report_reason": None, "affinity_status": "亲和力检测中"},
                created_by="张赞",
            )
            self.assertEqual(row["affinity_status"], "亲和力检测中")
            self.assertEqual(row["affinity_owner"], "张赞")

            with self.assertRaisesRegex(ValueError, "分泌型靶点不需要流式实验"):
                service.save(db, {"id": row["id"], "target_type": "分泌型", "flow_status": "流式待检测"})

    def test_status_machine_and_save_workflow(self):
        with self.Session() as db:
            # 1. Create without order_no -> status is 待下单, owner is None before affinity
            row1 = service.save(
                db,
                {
                    "target_name": "B7-H4",
                    "target_codes": ["20R015"],
                    "mouse_strain": ["RNKO", "RN"],
                    "synthesis_code": "20R015_RNBK01",
                    "synthetic_count": "118",
                    "synthetic_date": "2026-02-12",
                },
                created_by="测试员",
            )
            self.assertEqual(row1["status"], "待下单")
            self.assertEqual(row1["target_name"], "B7-H4")
            self.assertEqual(row1["target_codes"], ["20R015"])
            self.assertEqual(row1["mouse_strain"], "RN、RNKO")
            self.assertIsNone(row1["owner"])
            self.assertEqual(row1["synthetic_count"], 118)
            self.assertEqual(row1["synthetic_date"], "2026-02-12")

            # 2. Fill order_no -> auto advances to 合成中
            row1 = service.save(db, {"id": row1["id"], "order_no": "CN2602120001585"})
            self.assertEqual(row1["status"], "合成中")

            # 3. Fill arrival_count / arrival_date -> auto advances to 待检测
            row1 = service.save(
                db,
                {"id": row1["id"], "arrival_count": 113, "arrival_date": "2026-03-17"},
            )
            self.assertEqual(row1["status"], "待检测")
            self.assertEqual(row1["affinity_status"], "亲和力待检测")
            self.assertEqual(row1["flow_status"], "流式待检测")

            # 4. Switching affinity to testing claims it; report_reason forces affinity back to waiting while keeping owner
            row1 = service.save(
                db,
                {"id": row1["id"], "affinity_status": "亲和力检测中"},
                created_by="张赞 Zan Zhang",
                scopes=frozenset({"assay"}),
            )
            self.assertEqual(row1["status"], "检测中")
            self.assertEqual(row1["affinity_status"], "亲和力检测中")
            self.assertEqual(row1["affinity_owner"], "张赞")

            row1 = service.save(
                db,
                {
                    "id": row1["id"],
                    "affinity_date": "2026-03-25",
                    "report_reason": "抗原重检",
                    "selection_method": ["JX_P", "补挑"],
                },
            )
            self.assertEqual(row1["status"], "待检测")
            self.assertEqual(row1["affinity_status"], "亲和力待检测")
            self.assertEqual(row1["affinity_owner"], "张赞")

            # Clearing report_reason with affinity_date completes affinity; flow remains parallel until flow_date is set
            row1 = service.save(
                db,
                {"id": row1["id"], "report_reason": None, "affinity_date": "2026-03-26"},
            )
            self.assertEqual(row1["status"], "检测中")
            self.assertEqual(row1["affinity_status"], "亲和力已完成")
            self.assertEqual(row1["flow_status"], "流式待检测")
            self.assertIsNone(row1["affinity_result"])

            row1 = service.save(db, {"id": row1["id"], "flow_date": "2026-03-28"})
            self.assertEqual(row1["flow_status"], "流式已完成")
            self.assertEqual(row1["status"], "已完成")

            # 5. Engineering order with multi-value eng_type & eng_method joined with '、',
            #    and auto-fills owner and pm from created_by
            row2 = service.save(
                db,
                {
                    "order_kind": "改造",
                    "priority": "加急",
                    "target_name": "SLC3A2",
                    "target_codes": ["20R389"],
                    "order_no": "BAO0000575",
                    "eng_type": ["Tm", "亲和力"],
                    "eng_method": "NGS姐妹克隆 + AI",
                    "eng_parent_seq": "Vh1$0-20R389_RNBK01AACCHS",
                    "eng_requirement": "改造提高亲和力",
                    "flow_note": "缺孔还未补",
                },
                created_by="王子豪 Zihao Wang",
            )
            self.assertEqual(row2["target_name"], "SLC3A2")
            self.assertEqual(row2["target_codes"], ["20R389"])
            self.assertEqual(row2["status"], "合成中")
            self.assertEqual(row2["priority"], "加急")
            self.assertEqual(row2["eng_type"], "亲和力、Tm")
            self.assertEqual(row2["eng_method"], "AI、NGS姐妹克隆")
            self.assertEqual(row2["owner"], "王子豪")
            self.assertEqual(row2["pm"], "王子豪")

            # 6. Default list order is id desc; completed row1 has left the active queue.
            default_list = service.get_list(db, {})["items"]
            self.assertEqual(default_list[0]["id"], row2["id"])
            queue_list = service.get_list(db, {"sort_field": "sort_order"})["items"]
            self.assertEqual(queue_list[0]["id"], row2["id"])
            self.assertEqual(queue_list[0]["sort_order"], 1)
            self.assertIsNone(queue_list[1]["sort_order"])

            # 7. Empty/无人问津 owners can be claimed; same user re-claiming reverts to 无人问津
            claimed = service.claim_order(db, row1["id"], "张赞 Zan Zhang")
            self.assertEqual(claimed["owner"], "张赞")
            with self.assertRaises(ValueError):
                service.claim_order(db, row1["id"], "兰维秋")
            reverted = service.claim_order(db, row1["id"], "张赞 Zan Zhang")
            self.assertEqual(reverted["owner"], "无人问津")

            # 8. PM scope & Assay scope permissions and manual status preservation
            pm_created = service.save(
                db,
                {"target_name": "CD6", "eng_requirement": "提高Tm"},
                created_by="兰维秋",
                scopes=frozenset({"pm"}),
            )
            self.assertEqual(pm_created["owner"], "兰维秋")
            self.assertEqual(pm_created["pm"], "兰维秋")
            with self.assertRaises(PermissionError):
                service.save(
                    db,
                    {"id": pm_created["id"], "arrival_count": 50},
                    scopes=frozenset({"pm"}),
                )

            # Reopening affinity via pill on a completed row moves status back to 检测中 without snapping back to 已完成
            reopened = service.save(
                db,
                {"id": row1["id"], "affinity_status": "亲和力检测中"},
                created_by="张赞",
                scopes=frozenset({"assay"}),
            )
            self.assertEqual(reopened["status"], "检测中")
            self.assertEqual(reopened["affinity_status"], "亲和力检测中")
            with self.assertRaises(PermissionError):
                service.save(
                    db,
                    {"id": row1["id"], "status": "待检测"},
                    scopes=frozenset({"assay"}),
                )

            # Manual assay completion without dates keeps main status in 检测中; manual main status is preserved across note edits
            service.save(
                db,
                {"id": pm_created["id"], "affinity_status": "亲和力已完成", "flow_status": "流式已完成"},
                created_by="兰维秋",
                scopes=frozenset({"assay"}),
            )
            self.assertEqual(
                service.get_list(db, {"status": ["亲和力检测中", "流式已完成"]})["total"],
                1,
            )
            manual_main = service.save(db, {"id": pm_created["id"], "status": "已完成"})
            self.assertEqual(manual_main["status"], "已完成")
            manual_main = service.save(db, {"id": pm_created["id"], "remark": "手工状态保持"})
            self.assertEqual(manual_main["status"], "已完成")

    def test_sync_from_one_and_drift_adoption(self):
        fake_snap = {
            "source_one_type": "ngs",
            "source_one_id": 101,
            "synthesis_code": "20R282_RNBK01",
            "order_no": "CN2602120001585",
            "synthetic_corp": "君跻",
            "synthetic_count": 118,
            "synthetic_date": "2026-02-12",
            "arrival_count": None,
            "arrival_date": None,
            "order_sender": "陶俊先 Junxian Tao",
            "order_state": "进行中",
        }
        with self.Session() as db:
            created = service.save(
                db,
                {
                    "target_name": "CD6",
                    "batch_label": "CD6_RN_B_K_01_20260208_1",
                    "synthesis_code": "20R282_RNBK01",
                },
                created_by="tester",
            )
            row_id = created["id"]
            self.assertEqual(created["status"], "待下单")

            with patch(
                "modules.discovery.synthesis_progress.one_sync.open_one_db"
            ) as mock_open, patch(
                "modules.discovery.synthesis_progress.one_sync.fetch_remote_snapshots_by_ids",
                return_value={},
            ), patch(
                "modules.discovery.synthesis_progress.one_sync._query_candidates_for_rows",
                return_value=[fake_snap],
            ):
                mock_open.return_value.__enter__.return_value = object()
                sync_res = service.sync_from_one(db)
                self.assertEqual(sync_res["linked"], 1)

            items = service.get_list(db, {})["items"]
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["status"], "合成中")
            self.assertEqual(items[0]["order_no"], "CN2602120001585")
            self.assertEqual(items[0]["batch_label"], "CD6_RN_B_K_01_20260208_1")
            self.assertEqual(items[0]["order_sender"], "陶俊先 Junxian Tao")
            self.assertFalse(items[0]["has_drift"])

            updated_remote = {
                ("ngs", 101): {
                    **fake_snap,
                    "order_sender": "任鸿滨 Hongbin Ren",
                    "synthetic_count": 120,
                    "arrival_count": 115,
                    "arrival_date": "2026-03-17",
                }
            }
            with patch(
                "modules.discovery.synthesis_progress.one_sync.open_one_db"
            ) as mock_open2, patch(
                "modules.discovery.synthesis_progress.one_sync.fetch_remote_snapshots_by_ids",
                return_value=updated_remote,
            ):
                mock_open2.return_value.__enter__.return_value = object()
                check_res = service.check_remote_for_local_rows(db, [row_id])
                self.assertTrue(check_res["remote_available"])
                patched = check_res["updated_items"][0]
                self.assertEqual(patched["arrival_count"], 115)
                self.assertEqual(patched["arrival_date"], "2026-03-17")
                self.assertEqual(patched["status"], "待检测")
                self.assertEqual(patched["synthetic_count"], 118)
                self.assertEqual(patched["order_sender"], "任鸿滨 Hongbin Ren")
                self.assertTrue(patched["has_drift"])
                self.assertEqual(patched["drift_fields"][0]["field"], "synthetic_count")
                self.assertEqual(patched["drift_fields"][0]["remote"], "120")

            adopted = service.adopt_source(db, row_id, ["synthetic_count"])
            self.assertEqual(adopted["synthetic_count"], 120)
            self.assertFalse(adopted["has_drift"])
            manual_sender = service.save(db, {"id": row_id, "order_sender": "手填"})
            self.assertEqual(manual_sender["order_sender"], "任鸿滨 Hongbin Ren")

            # A no-op background remote check must not overwrite a manually chosen main status.
            service.save(db, {"id": row_id, "status": "已完成"})
            with patch(
                "modules.discovery.synthesis_progress.one_sync.open_one_db"
            ) as mock_open_same, patch(
                "modules.discovery.synthesis_progress.one_sync.fetch_remote_snapshots_by_ids",
                return_value=updated_remote,
            ):
                mock_open_same.return_value.__enter__.return_value = object()
                service.check_remote_for_local_rows(db, [row_id])
            self.assertEqual(service.get_list(db, {})["items"][0]["status"], "已完成")

            # Duplicate entry check: creating a second row with the same batch_label/order_no
            # when One DB has no other untaken record returns duplicates info
            dup_row = service.save(
                db,
                {
                    "target_name": "CD6",
                    "batch_label": "CD6_RN_B_K_01_20260208_1",
                    "order_no": "CN2602120001585",
                },
                created_by="tester",
            )
            with patch(
                "modules.discovery.synthesis_progress.one_sync.open_one_db"
            ) as mock_open3, patch(
                "modules.discovery.synthesis_progress.one_sync._query_candidates_for_rows",
                return_value=[fake_snap],
            ):
                mock_open3.return_value.__enter__.return_value = object()
                dup_check = service.check_remote_for_local_rows(db, [dup_row["id"]])
                self.assertEqual(dup_check["linked"], 0)
                dup_info = dup_check["duplicates"].get(str(dup_row["id"]), {})
                self.assertIn("CN2602120001585", dup_info.get("batch_label", []))
                self.assertIn("CD6_RN_B_K_01_20260208_1", dup_info.get("order_no", []))

            # Candidate switching check: when a synthesis_code has a second untaken order in One DB,
            # candidates list includes it, and switching order_no replaces auto-filled values cleanly
            second_snap = {
                "source_one_type": "ngs",
                "source_one_id": 102,
                "synthesis_code": "20R282_RNBK01",
                "batch_label": "CD6_RN_B_K_01_20260208_2",
                "order_no": "BAO0000888",
                "synthetic_corp": "擎科",
                "synthetic_count": 66,
                "synthetic_date": "2026-03-01",
                "arrival_count": None,
                "arrival_date": None,
                "order_state": "进行中",
                "task_projectid": "CD6_RN_B_K_01_20260208_2",
            }
            with patch(
                "modules.discovery.synthesis_progress.one_sync.open_one_db"
            ) as mock_open4, patch(
                "modules.discovery.synthesis_progress.one_sync.fetch_remote_snapshots_by_ids",
                return_value=updated_remote,
            ), patch(
                "modules.discovery.synthesis_progress.one_sync._query_candidates_for_rows",
                return_value=[fake_snap, second_snap],
            ):
                mock_open4.return_value.__enter__.return_value = object()
                cand_res = service.check_remote_for_local_rows(db, [row_id])
                cands = cand_res["candidates"].get(str(row_id), [])
                self.assertEqual(len(cands), 1)
                self.assertEqual(cands[0]["order_no"], "BAO0000888")

                # User switches row_id to BAO0000888 -> auto-filled synthetic_corp/date update to second_snap
                service.save(db, {"id": row_id, "order_no": "BAO0000888"})
                switched_res = service.check_remote_for_local_rows(db, [row_id])
                switched_item = switched_res["updated_items"][0]
                self.assertEqual(switched_item["source_one_id"], 102)
                self.assertEqual(switched_item["synthetic_corp"], "擎科")
                self.assertEqual(switched_item["synthetic_date"], "2026-03-01")
                self.assertIsNone(switched_item["order_sender"])

    def test_remote_snapshot_keeps_uploader_as_order_sender(self):
        snap = one_sync.build_remote_snapshot("beacon", {"id": 7, "uploader": "任鸿滨 Hongbin Ren"})
        self.assertEqual(snap["order_sender"], "任鸿滨 Hongbin Ren")
        self.assertIsNone(one_sync.build_remote_snapshot("ngs", {"id": 8})["order_sender"])


class SynthesisHeaderFilterTests(DbTestCase):
    tables = (Target, DiscoverySynthesisOrder)
    ROWS = [
        dict(status="待下单", owner="甲", target_name="PD-L1", target_codes=["20R001"],
             mouse_strain="RN、RNKO", synthesis_code="S001", synthetic_count=10,
             synthetic_date="2026-01-05", remark="首批", target_color="red"),
        dict(status="合成中", owner="乙", target_name="CD274", target_codes=["20R001"],
             mouse_strain="RN", synthesis_code="S002", synthetic_count=50,
             synthetic_date="2026-02-10", remark=None),
        dict(status="已完成", owner=None, target_name="HER2", target_codes=["20R002"],
             mouse_strain="RNKO", synthesis_code="S003", synthetic_count=None,
             synthetic_date=None, remark="补做 100%"),
        dict(status="合成中", owner="甲", target_name="PD-L1&HER2", target_codes=["20R001", "20R002"],
             mouse_strain=None, synthesis_code="S004", synthetic_count=80,
             synthetic_date="2026-03-01", remark=""),
    ]

    def setUp(self):
        super().setUp()
        with self.Session() as db:
            for index, row in enumerate(self.ROWS, start=1):
                db.add(DiscoverySynthesisOrder(
                    synthesis_order_id=f"SO{index:03d}",
                    order_kind="常规",
                    supply_mode="自合成",
                    **row,
                ))
            db.commit()

    def codes(self, *field_filters, **extra):
        with self.Session() as db:
            data = {"limit": 50, "field_filters": list(field_filters), **extra}
            return sorted(item["synthesis_code"] for item in service.get_list(db, data)["items"])

    def values(self, field, **extra):
        with self.Session() as db:
            return service.get_column_values(db, {"field": field, **extra})

    def test_values_and_exclude_handle_blank(self):
        self.assertEqual(self.codes({"field": "owner", "values": ["甲"]}), ["S001", "S004"])
        self.assertEqual(self.codes({"field": "owner", "values": ["乙", ""]}), ["S002", "S003"])
        self.assertEqual(self.codes({"field": "owner", "exclude": ["甲"]}), ["S002", "S003"])
        self.assertEqual(self.codes({"field": "owner", "exclude": ["甲", ""]}), ["S002"])
        self.assertEqual(self.codes({"field": "remark", "exclude": [""]}), ["S001", "S003"])

    def test_conditions(self):
        self.assertEqual(
            self.codes({"field": "remark", "condition": {"op": "contains", "value": "100%"}}),
            ["S003"],
        )
        self.assertEqual(
            self.codes({"field": "remark", "condition": {"op": "not_contains", "value": "首"}}),
            ["S002", "S003", "S004"],
        )
        self.assertEqual(
            self.codes({"field": "synthetic_count", "condition": {"op": "gte", "value": "50"}}),
            ["S002", "S004"],
        )
        self.assertEqual(
            self.codes({"field": "synthetic_date", "condition": {
                "op": "between", "value": "2026-02-01", "value2": "2026-03-31"}}),
            ["S002", "S004"],
        )
        self.assertEqual(
            self.codes({"field": "synthetic_date", "condition": {"op": "blank"}}),
            ["S003"],
        )
        self.assertEqual(
            self.codes({"field": "synthetic_date", "condition": {
                "op": "between", "value": "2026/2/1", "value2": "2026.3.31"}}),
            ["S002", "S004"],
        )
        with self.assertRaises(ValueError):
            self.codes({"field": "synthetic_date", "condition": {"op": "gte", "value": "2026-13-01"}})
        with self.assertRaises(ValueError):
            self.codes({"field": "synthetic_date", "condition": {"op": "gte", "value": "01/01/2026"}})
        with self.assertRaises(ValueError):
            self.codes({"field": "sort_order", "values": ["1"]})

    def test_multi_value_columns(self):
        self.assertEqual(self.codes({"field": "mouse_strain", "values": ["RN"]}), ["S001", "S002"])
        self.assertEqual(self.codes({"field": "mouse_strain", "exclude": ["RN"]}), ["S003", "S004"])
        strains = self.values("mouse_strain")["items"]
        self.assertEqual(
            {item["value"]: item["count"] for item in strains},
            {"RN": 2, "RNKO": 2, "": 1},
        )
        self.assertEqual(
            self.codes({"field": "target_name", "values": ["PD-L1"]}),
            ["S001", "S002", "S004"],
        )
        self.assertEqual(self.codes({"field": "target_name", "exclude": ["HER2"]}), ["S001", "S002"])
        targets = self.values("target_name")["items"]

        def group_count(name):
            hits = [item for item in targets if name in (item["value"], *item["aliases"])]
            self.assertEqual(len(hits), 1, name)
            return hits[0]["count"]

        self.assertEqual(group_count("PD-L1"), 3)
        self.assertEqual(group_count("CD274"), 3)
        self.assertEqual(group_count("HER2"), 2)
        self.assertEqual(group_count("PD-L1&HER2"), 1)
        searched = self.values("target_name", value_keyword="cd274")["items"]
        self.assertEqual(len(searched), 1)
        self.assertIn("PD-L1", (searched[0]["value"], *searched[0]["aliases"]))
        self.assertEqual(
            self.codes({"field": "target_name", "values": [searched[0]["value"]]}),
            ["S001", "S002", "S004"],
        )
        self.assertEqual(
            self.codes({"field": "target_name", "colors": ["red"]}),
            ["S001"],
        )

    def test_value_list_ignores_own_header_filter_and_keeps_others(self):
        own = {"field": "owner", "values": ["甲"]}
        listed = self.values("owner", field_filters=[own])["items"]
        self.assertEqual({item["value"] for item in listed}, {"甲", "乙", ""})
        other = {"field": "status", "values": ["合成中"]}
        listed = self.values("owner", field_filters=[other])["items"]
        self.assertEqual({item["value"]: item["count"] for item in listed}, {"甲": 1, "乙": 1})

    def test_value_orders_and_truncation(self):
        recent = self.values("synthesis_code", value_order="recent", value_limit=2)
        self.assertEqual([item["value"] for item in recent["items"]], ["S004", "S003"])
        self.assertTrue(recent["truncated"])
        dates = self.values("synthetic_date", value_order="value_desc")["items"]
        self.assertEqual(dates[0]["value"], "2026-03-01")
        self.assertEqual(dates[-1], {"value": "", "count": 1})
        statuses = [item["value"] for item in self.values("status")["items"]]
        self.assertEqual(statuses, ["待下单", "合成中", "已完成"])

    def test_header_sort_uses_business_order_and_blanks_last(self):
        with self.Session() as db:
            rows = service.get_list(db, {"limit": 50, "sort_field": "status", "sort_dir": "desc"})["items"]
            self.assertEqual([row["status"] for row in rows], ["已完成", "合成中", "合成中", "待下单"])
            rows = service.get_list(db, {"limit": 50, "sort_field": "owner", "sort_dir": "asc"})["items"]
            self.assertEqual([row["owner"] for row in rows], ["乙", "甲", "甲", None])
            rows = service.get_list(db, {"limit": 50, "sort_field": "owner", "sort_dir": "desc"})["items"]
            self.assertEqual([row["owner"] for row in rows], ["甲", "甲", "乙", None])

    def test_stats_and_export_follow_header_filters(self):
        header = [{"field": "status", "exclude": ["合成中"]}]
        with self.Session() as db:
            data = service.get_list(db, {"limit": 50, "field_filters": header})
            self.assertEqual(data["total"], 2)
            self.assertEqual(data["stats"]["all"], 2)
            self.assertEqual(data["stats"]["synthesizing"], 0)
            with patch.object(service, "build_list_workbook", side_effect=lambda **kw: kw) as built:
                service.export_list_workbook(db, {
                    "field_filters": header, "sort_field": "synthesis_code", "sort_dir": "desc",
                })
            rows = built.call_args.kwargs["rows"]
            code_at = [h for h, _ in service.EXPORT_COLUMNS].index("送测转码")
            self.assertEqual([row[code_at] for row in rows], ["S003", "S001"])

    def test_search_mode_text_columns(self):
        found = self.values("remark", value_keyword="补做", value_order="recent")["items"]
        self.assertEqual(found, [{"value": "补做 100%", "count": 1}])

    def test_value_search_keeps_list_keyword(self):
        listed = self.values("owner", keyword="S00")["items"]
        self.assertEqual({item["value"]: item["count"] for item in listed}, {"甲": 2, "乙": 1, "": 1})
        listed = self.values("owner", keyword="PD-L1", value_keyword="甲")["items"]
        self.assertEqual(listed, [{"value": "甲", "count": 2}])
        self.assertEqual(
            self.codes({"field": "eng_result", "condition": {"op": "blank"}}),
            ["S001", "S002", "S003", "S004"],
        )


if __name__ == "__main__":
    unittest.main()
