"""发现合成与验证 One 同步：快照映射、建单改绑、差异检测采用及候选切换。"""

import unittest
from unittest.mock import patch

from models.discovery import DiscoverySynthesisOrder
from models.target import Target
from modules.discovery.synthesis_progress import one_sync, service
from support import DbTestCase

TABLES = (Target, DiscoverySynthesisOrder)


class OneSyncMappingTests(unittest.TestCase):
    def test_is_manual_batch_and_parse_one_target(self):
        manual_cases = (
            (("23R037_RM_C_W_M1_20261102_20clones_20261103_to君跻_M.xlsx",), True),
            ((None, "23R037_RM_C_W_M12_20261102"), True),
            (("20R430_RM_C_W_S1_20261102_20clones_20261103_to君跻_M.xlsx",), False),
            (("CD6_M1_20clones.xlsx",), False),
        )
        for args, expected in manual_cases:
            with self.subTest(manual_args=args):
                self.assertEqual(one_sync.is_manual_batch(*args), expected)

        target_cases = (
            (("[20R147]MCSP",), (["20R147"], "MCSP")),
            (("FN1", "21R009_RL_B_K_S1", None), (["21R009"], "FN1")),
            (("FN1", "FN1_RL_B_K_S1"), ([], "FN1")),
        )
        for args, expected in target_cases:
            with self.subTest(target_args=args):
                self.assertEqual(one_sync.parse_one_target(*args), expected)

    def test_build_remote_snapshot_maps_sources_and_fields(self):
        cases = (
            (
                "beacon",
                {"id": 7, "uploader": "任鸿滨 Hongbin Ren"},
                {"order_sender": "任鸿滨 Hongbin Ren"},
            ),
            (
                "ngs",
                {"id": 8},
                {"order_sender": None},
            ),
            (
                "ngs",
                {"id": 9, "selectmethod": "补挑,D_JX", "isrechooseorder": "false"},
                {"selection_method": "D_JX", "is_rechoose": "是"},
            ),
            (
                "ngs",
                {"id": 10, "isrechooseorder": "false"},
                {"is_rechoose": "否"},
            ),
            (
                "ngs",
                {
                    "id": 11,
                    "orderno": "CN2602120001585",
                    "syntheticcount": 96,
                    "supernatantcounts": 192,
                    "syntheticdate": "2026-03-01",
                    "deliverydate": "2026-02-20",
                },
                {"synthetic_count": 96, "synthetic_date": "2026-03-01"},
            ),
        )
        for source_type, raw, expected in cases:
            with self.subTest(source_type=source_type, id=raw["id"]):
                snap = one_sync.build_remote_snapshot(source_type, raw)
                for key, val in expected.items():
                    self.assertEqual(snap[key], val)
                # 发货日期、到货个数只取合成公司上清推送
                self.assertFalse({"arrival_count", "arrival_date"} & set(snap))


class OneSyncServiceTests(DbTestCase):
    tables = TABLES

    def _snap(self, sid: int, refstr: str = "x.xlsx", **extra):
        return {
            "source_one_type": "ngs",
            "source_one_id": sid,
            "refstr": refstr,
            "order_no": None,
            "synthetic_corp": "君跻",
            "synthetic_count": 20,
            "synthetic_date": "2026-11-03",
            "arrival_count": None,
            "arrival_date": None,
            "order_sender": "陶俊先 Junxian Tao",
            **extra,
        }

    def _cd6_snap(self, sid: int = 101, **extra):
        return {
            "source_one_type": "ngs",
            "source_one_id": sid,
            "synthesis_code": "20R282_RNBK01",
            "order_no": "CN2602120001585",
            "synthetic_corp": "君跻",
            "synthetic_count": 118,
            "synthetic_date": "2026-02-12",
            "arrival_count": None,
            "arrival_date": None,
            "order_sender": "陶俊先 Junxian Tao",
            "order_state": "进行中",
            **extra,
        }

    def _run_sync_from_remote(self, remote):
        def fake_fetch(_one_db, condition, params, *_args):
            if "created" in condition:
                return list(remote)
            return [item for item in remote if item["refstr"] in params["refs"]]

        with patch("modules.discovery.synthesis_progress.one_sync.open_one_db") as mock_open, patch(
            "modules.discovery.synthesis_progress.one_sync.fetch_remote_snapshots_by_ids", return_value={}
        ), patch(
            "modules.discovery.synthesis_progress.one_sync._query_candidates_for_rows", return_value=[]
        ), patch("modules.discovery.synthesis_progress.one_sync._fetch_snapshots", side_effect=fake_fetch):
            mock_open.return_value.__enter__.return_value = object()
            return service.sync_from_one(self.db)

    def _create_linked_cd6(self):
        snap = self._cd6_snap()
        created = service.save(
            self.db,
            {
                "target_name": "CD6",
                "batch_label": "CD6_RN_B_K_01_20260208_1",
                "synthesis_code": "20R282_RNBK01",
            },
            created_by="tester",
        )
        with patch("modules.discovery.synthesis_progress.one_sync.open_one_db") as mock_open, patch(
            "modules.discovery.synthesis_progress.one_sync.fetch_remote_snapshots_by_ids", return_value={}
        ), patch("modules.discovery.synthesis_progress.one_sync._query_candidates_for_rows", return_value=[snap]):
            mock_open.return_value.__enter__.return_value = object()
            sync_res = service.sync_from_one(self.db)
        return created["id"], snap, sync_res

    def test_sync_from_one_creates_orders_skips_manual_and_known(self):
        file_a = "20R430_RM_C_W_S1_20261102_20clones_20261103_to君跻_M.xlsx"
        file_b = "21R001_RM_C_W_S2_20261102_10clones_20261103_to君跻_M.xlsx"
        remote = [
            self._snap(
                201, file_a, order_no="CN001", batch_label="20R430_RM_C_W_S1_20261102",
                synthesis_code="20R430_RMCWS1", task_target="[20R430]PD-L1",
            ),
            self._snap(202, file_b, synthesis_code="21R001_RMCWS2", task_target="[21R001]XYZ"),
            self._snap(203, "23R037_RM_C_W_M1_20261102_20clones_20261103_to君跻_M.xlsx", order_no="CN003"),
            self._snap(204, "x_20clones.xlsx", order_no="CN999"),
        ]
        service.save(
            self.db,
            {
                "target_name": "PD-L1",
                "batch_label": "20R430_RM_C_W_S1_20261102",
                "synthesis_code": "20R430_RMCWS1",
                "priority": "加急",
                "owner": "张三",
                "pm": "李四",
                "project_code": "P001",
                "mouse_strain": "RMB/C",
            },
            created_by="tester",
        )
        service.save(self.db, {"target_name": "OLD", "order_no": "cn999"}, created_by="tester")

        res = self._run_sync_from_remote(remote)
        self.assertEqual(res["created"], 2)
        rows = {row.source_one_id: row for row in self.db.query(DiscoverySynthesisOrder).all() if row.source_one_id}
        self.assertEqual(set(rows), {201, 202})

        row_a = rows[201]
        self.assertEqual(row_a.created_by, "One同步")
        self.assertEqual(row_a.status, "合成中")
        self.assertEqual(row_a.order_no, "CN001")
        self.assertEqual(row_a.order_sender, "陶俊先 Junxian Tao")
        self.assertEqual((row_a.owner, row_a.pm, row_a.project_code, row_a.priority), (None, "李四", "P001", "加急"))
        self.assertEqual((row_a.target_codes, row_a.target_name), (["20R430"], "PD-L1"))

        row_b = rows[202]
        self.assertEqual(row_b.status, "待下单")
        self.assertEqual(row_b.target_codes, ["21R001"])
        self.assertEqual(row_b.mouse_strain, "RMB/C")

    def test_sync_from_one_relinks_pending_same_file_order_and_blocks_delete(self):
        file_b = "21R001_RM_C_W_S2_20261102_10clones_20261103_to君跻_M.xlsx"
        remote = [self._snap(202, file_b, synthesis_code="21R001_RMCWS2", task_target="[21R001]XYZ")]
        self.assertEqual(self._run_sync_from_remote(remote)["created"], 1)

        row_b = self.db.query(DiscoverySynthesisOrder).filter_by(source_one_id=202).one()
        with self.assertRaisesRegex(ValueError, "已关联 One 订单"):
            service.delete(self.db, row_b.id)

        # 同文件另一条后来才下单：改绑已建的待下单行，不再新建
        remote.append(self._snap(205, file_b, order_no="CN005", synthesis_code="21R001_RMCWS2"))
        res = self._run_sync_from_remote(remote)
        self.assertEqual(res["created"], 0)
        self.db.refresh(row_b)
        self.assertEqual((row_b.source_one_id, row_b.order_no, row_b.status), (205, "CN005", "合成中"))
        self.assertEqual(self.db.query(DiscoverySynthesisOrder).count(), 1)

    def test_sync_from_one_links_local_order_and_backfills(self):
        _, _, sync_res = self._create_linked_cd6()
        self.assertEqual(sync_res["linked"], 1)
        items = service.get_list(self.db, {})["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["status"], "合成中")
        self.assertEqual(items[0]["order_no"], "CN2602120001585")
        self.assertEqual(items[0]["batch_label"], "CD6_RN_B_K_01_20260208_1")
        self.assertEqual(items[0]["order_sender"], "陶俊先 Junxian Tao")
        self.assertFalse(items[0]["has_drift"])

    def test_remote_check_detects_drift_and_adopt_source_applies_it(self):
        row_id, snap, _ = self._create_linked_cd6()
        updated_remote = {
            ("ngs", 101): {
                **snap,
                "order_sender": "任鸿滨 Hongbin Ren",
                "synthetic_count": 120,
                "arrival_count": 115,
                "arrival_date": "2026-03-17",
            }
        }
        with patch("modules.discovery.synthesis_progress.one_sync.open_one_db") as mock_open, patch(
            "modules.discovery.synthesis_progress.one_sync.fetch_remote_snapshots_by_ids",
            return_value=updated_remote,
        ):
            mock_open.return_value.__enter__.return_value = object()
            check_res = service.check_remote_for_local_rows(self.db, [row_id])

        self.assertTrue(check_res["remote_available"])
        patched = check_res["updated_items"][0]
        self.assertEqual((patched["arrival_count"], patched["arrival_date"]), (None, None))
        self.assertEqual(patched["status"], "合成中")
        self.assertEqual(patched["synthetic_count"], 118)
        self.assertEqual(patched["order_sender"], "任鸿滨 Hongbin Ren")
        self.assertTrue(patched["has_drift"])
        self.assertEqual(patched["drift_fields"][0]["field"], "synthetic_count")
        self.assertEqual(patched["drift_fields"][0]["remote"], "120")

        adopted = service.adopt_source(self.db, row_id, ["synthetic_count"])
        self.assertEqual(adopted["synthetic_count"], 120)
        self.assertFalse(adopted["has_drift"])

        manual_sender = service.save(self.db, {"id": row_id, "order_sender": "手填"})
        self.assertEqual(manual_sender["order_sender"], "任鸿滨 Hongbin Ren")
        for label in ("CD6_RN_B_K_01_20260208_1（补挑）", "CD6_RN_B_K_01_20260208_1"):
            relabeled = service.save(self.db, {"id": row_id, "batch_label": label})
            self.assertEqual(
                (relabeled["source_one_id"], relabeled["order_no"], relabeled["order_sender"]),
                (101, "CN2602120001585", "任鸿滨 Hongbin Ren"),
            )

    def test_remote_check_preserves_manual_completed_status(self):
        row_id, snap, _ = self._create_linked_cd6()
        remote_map = {
            ("ngs", 101): {
                **snap,
                "order_sender": "任鸿滨 Hongbin Ren",
                "synthetic_count": 120,
                "arrival_count": 115,
                "arrival_date": "2026-03-17",
            }
        }
        with patch("modules.discovery.synthesis_progress.one_sync.open_one_db") as mock_open, patch(
            "modules.discovery.synthesis_progress.one_sync.fetch_remote_snapshots_by_ids",
            return_value=remote_map,
        ):
            mock_open.return_value.__enter__.return_value = object()
            service.check_remote_for_local_rows(self.db, [row_id])

        service.save(self.db, {"id": row_id, "status": "已完成"})
        with patch("modules.discovery.synthesis_progress.one_sync.open_one_db") as mock_open, patch(
            "modules.discovery.synthesis_progress.one_sync.fetch_remote_snapshots_by_ids",
            return_value=remote_map,
        ):
            mock_open.return_value.__enter__.return_value = object()
            service.check_remote_for_local_rows(self.db, [row_id])
        self.assertEqual(service.get_list(self.db, {})["items"][0]["status"], "已完成")

    def test_remote_check_reports_local_duplicates_when_unlinked(self):
        _, snap, _ = self._create_linked_cd6()
        dup_row = service.save(
            self.db,
            {
                "target_name": "CD6",
                "batch_label": "CD6_RN_B_K_01_20260208_1",
                "order_no": "CN2602120001585",
            },
            created_by="tester",
        )
        with patch("modules.discovery.synthesis_progress.one_sync.open_one_db") as mock_open, patch(
            "modules.discovery.synthesis_progress.one_sync._query_candidates_for_rows",
            return_value=[snap],
        ):
            mock_open.return_value.__enter__.return_value = object()
            dup_check = service.check_remote_for_local_rows(self.db, [dup_row["id"]])

        self.assertEqual(dup_check["linked"], 0)
        dup_info = dup_check["duplicates"].get(str(dup_row["id"]), {})
        self.assertIn("CN2602120001585", dup_info.get("batch_label", []))
        self.assertIn("CD6_RN_B_K_01_20260208_1", dup_info.get("order_no", []))

    def test_remote_check_lists_candidates_and_switches_order_no(self):
        row_id, snap, _ = self._create_linked_cd6()
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
        remote_map = {("ngs", 101): snap}
        with patch("modules.discovery.synthesis_progress.one_sync.open_one_db") as mock_open, patch(
            "modules.discovery.synthesis_progress.one_sync.fetch_remote_snapshots_by_ids",
            return_value=remote_map,
        ), patch(
            "modules.discovery.synthesis_progress.one_sync._query_candidates_for_rows",
            return_value=[snap, second_snap],
        ):
            mock_open.return_value.__enter__.return_value = object()
            cand_res = service.check_remote_for_local_rows(self.db, [row_id])
            cands = cand_res["candidates"].get(str(row_id), [])
            self.assertEqual(len(cands), 1)
            self.assertEqual(cands[0]["order_no"], "BAO0000888")

            service.save(self.db, {"id": row_id, "order_no": "BAO0000888"})
            switched_res = service.check_remote_for_local_rows(self.db, [row_id])

        switched_item = switched_res["updated_items"][0]
        self.assertEqual(switched_item["source_one_id"], 102)
        self.assertEqual(switched_item["synthetic_corp"], "擎科")
        self.assertEqual(switched_item["synthetic_date"], "2026-03-01")
        self.assertIsNone(switched_item["order_sender"])

    def test_internal_supply_rows_link_only_by_order_or_batch(self):
        remote = {
            "source_one_type": "ngs",
            "source_one_id": 301,
            "synthesis_code": "20R383_RNBK01",
            "order_no": "BAO0000310",
            "synthetic_count": 192,
            "synthetic_date": "2026-03-26",
            "task_projectid": "FCGR2A_RN_B_K_01_20251115",
        }

        def check(row_id):
            with patch("modules.discovery.synthesis_progress.one_sync.open_one_db") as mock_open, patch(
                "modules.discovery.synthesis_progress.one_sync.fetch_remote_snapshots_by_ids", return_value={}
            ), patch(
                "modules.discovery.synthesis_progress.one_sync._query_candidates_for_rows", return_value=[remote]
            ):
                mock_open.return_value.__enter__.return_value = object()
                return service.check_remote_for_local_rows(self.db, [row_id])

        subtype = service.save(
            self.db,
            {
                "target_name": "FCGR2A",
                "supply_mode": "改亚型",
                "synthesis_code": "20R383_RNBK01",
                "batch_label": "FCGR2A_RNBK01",
                "synthetic_count": 564,
            },
        )
        self.assertEqual(check(subtype["id"])["linked"], 0)
        service.save(self.db, {"id": subtype["id"], "batch_label": "FCGR2A_RN_B_K_01_20251115"})
        self.assertEqual(check(subtype["id"])["linked"], 1)
