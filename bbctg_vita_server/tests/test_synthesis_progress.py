import unittest
from unittest.mock import patch

from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

from db.session import Base
from models.discovery import DiscoverySynthesisOrder
from models.target import Target
from modules.discovery.synthesis_progress import service


@compiles(BigInteger, "sqlite")
def _compile_big_int_sqlite(_type, _compiler, **_kwargs):
    return "INTEGER"


class SynthesisProgressServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(
            self.engine,
            tables=[
                Target.__table__,
                DiscoverySynthesisOrder.__table__,
            ],
        )
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)

    def tearDown(self):
        self.engine.dispose()

    def test_status_machine_and_save_workflow(self):
        with self.Session() as db:
            # 1. Create without order_no -> status is 待下单
            row1 = service.save(
                db,
                {
                    "target_name": "B7-H4",
                    "target_codes": ["20R015"],
                    "mouse_strain": ["RNKO", "RN"],
                    "synthesis_code": "20R015_RNBK01",
                    "synthetic_count": "118",
                    "synthetic_date": "2026-02-12",
                    "owner": "无人问津",
                },
                created_by="测试员",
            )
            self.assertEqual(row1["status"], "待下单")
            self.assertEqual(row1["target_name"], "B7-H4")
            self.assertEqual(row1["target_codes"], ["20R015"])
            self.assertEqual(row1["mouse_strain"], "RN、RNKO")
            self.assertEqual(row1["owner"], "无人问津")
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

            # 4. Fill flow_date / flow_count -> auto advances to 检测中
            row1 = service.save(
                db,
                {"id": row1["id"], "flow_count": 113, "flow_date": "2026-03-20", "owner": "李卓琳"},
            )
            self.assertEqual(row1["status"], "检测中")
            self.assertEqual(row1["owner"], "李卓琳")

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
                    "assay_note": "缺孔还未补",
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

            # 6. Default list order is id desc (newest row2 is first); queue sort puts 加急 row2 at sort_order=1
            default_list = service.get_list(db, {})["items"]
            self.assertEqual(default_list[0]["id"], row2["id"])
            queue_list = service.get_list(db, {"sort_field": "sort_order"})["items"]
            self.assertEqual(queue_list[0]["id"], row2["id"])
            self.assertEqual(queue_list[0]["sort_order"], 1)
            self.assertEqual(queue_list[1]["sort_order"], 2)

            # 7. Claim order updates owner independently of pm
            claimed = service.claim_order(db, row1["id"], "张赞 Zan Zhang")
            self.assertEqual(claimed["owner"], "张赞")

            # 8. PM scope can edit PM fields & create order, but cannot edit arrival_count
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

            res = service.get_list(db, {})
            self.assertEqual(res["total"], 3)
            self.assertEqual(res["stats"]["assay"], 1)
            self.assertEqual(res["stats"]["synthesizing"], 1)
            self.assertEqual(res["stats"]["engineering"], 1)
            self.assertEqual(res["stats"]["has_issue"], 1)

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
            self.assertFalse(items[0]["has_drift"])

            updated_remote = {
                ("ngs", 101): {
                    **fake_snap,
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
                self.assertTrue(patched["has_drift"])
                self.assertEqual(patched["drift_fields"][0]["field"], "synthetic_count")
                self.assertEqual(patched["drift_fields"][0]["remote"], "120")

            adopted = service.adopt_source(db, row_id, ["synthetic_count"])
            self.assertEqual(adopted["synthetic_count"], 120)
            self.assertFalse(adopted["has_drift"])

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


if __name__ == "__main__":
    unittest.main()
