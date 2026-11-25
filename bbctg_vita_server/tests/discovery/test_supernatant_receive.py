from datetime import datetime
from decimal import Decimal
import json
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from db.session import get_db
from models.discovery import DiscoverySynthesisOrder
from models.supernatant import SynthesisSupernatantWell
from modules.discovery.synthesis_progress.one_sync import apply_remote_snapshot_to_row, compute_drift_fields
from modules.supernatant_receive.routes import router
from support import DbTestCase

URL = "/protein-supernatant/receive"


def _well(plate, well, sample, **overrides):
    row = {"plateno": plate, "wellno": well, "sampleName": sample,
           "potency": "100", "specs": "2", "volume": "20", "sampleEnterVol": "2"}
    row.update(overrides)
    return row


def _payload(*rows, order_no="BAO0000900"):
    return {"orderNo": order_no, "corpName": "擎科", "organCode": "protein_supernatant_temp", "data": list(rows)}


class SupernatantReceiveTest(DbTestCase):
    tables = (SynthesisSupernatantWell, DiscoverySynthesisOrder)

    def setUp(self):
        super().setUp()
        app = FastAPI()
        app.include_router(router, prefix="/protein-supernatant")
        app.dependency_overrides[get_db] = lambda: self.db
        self.settings = SimpleNamespace(supernatant_receive_token="", supernatant_receive_ips="")
        patcher = patch("modules.auth.external.get_settings", return_value=self.settings)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def wells(self):
        return {
            (row.order_no, row.plate_no, row.well_no): row
            for row in self.db.scalars(select(SynthesisSupernatantWell))
            if not row.not_synthesized
        }

    def test_saves_one_row_per_well(self):
        body = _payload(
            _well("P1", "B2", "S3"),
            _well("P1", "A01", "S2"),
            {"PLATENO": "P1", "wellno": "a1", "samplename": "S1", "potency": 85.123456,
             "specs": "2", "volume": "20", "sampleentervol": "2"},
            _well("P2", "H12", "S4"),
        )
        resp = self.client.post(URL, json=body)

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], 0)
        self.assertIn("A01 重复", resp.json()["msg"])

        body["data"][1]["wellno"] = "A2"
        resp = self.client.post(URL, json=body)
        self.assertEqual((resp.status_code, resp.json()), (200, {"code": 1, "msg": "success", "data": None}))
        wells = self.wells()
        self.assertEqual(sorted(key[1:] for key in wells),
                         [("P1", "A01"), ("P1", "A02"), ("P1", "B02"), ("P2", "H12")])
        a1 = wells[("BAO0000900", "P1", "A01")]
        self.assertEqual((a1.corp_name, a1.sample_name), ("擎科", "S1"))
        self.assertEqual((a1.potency, a1.specs, a1.volume, a1.sample_enter_vol),
                         (Decimal("85.1235"), Decimal("2"), Decimal("20"), Decimal("2")))

    def test_batches_of_one_plate_add_up_and_repush_overwrites_wells(self):
        self.client.post(URL, json=_payload(_well("P1", "A1", "S1"), _well("P1", "A2", "S2"), _well("P2", "A1", "T1")))
        resp = self.client.post(URL, json=_payload(_well("P1", "A1", "S9", potency="80"), _well("P1", "C3", "S8")))

        self.assertEqual(resp.json()["code"], 1)
        wells = self.wells()
        self.assertEqual(sorted(key[1:] for key in wells),
                         [("P1", "A01"), ("P1", "A02"), ("P1", "C03"), ("P2", "A01")])
        self.assertEqual(wells[("BAO0000900", "P1", "A01")].sample_name, "S9")
        self.assertEqual(wells[("BAO0000900", "P1", "A01")].potency, Decimal("80"))
        self.assertEqual(wells[("BAO0000900", "P1", "A02")].sample_name, "S2")
        self.assertEqual(wells[("BAO0000900", "P2", "A01")].sample_name, "T1")

        self.client.post(URL, json=_payload(_well("P1", "A1", "X1"), order_no="BAO0000901"))
        self.assertEqual(len(self.wells()), 5)

    def test_invalid_rows_reject_whole_request(self):
        resp = self.client.post(URL, json=_payload(
            _well("P1", "A1", "S1"),
            _well("P1", "I1", "S2"),
            _well("P1", "A13", "S3", potency=""),
            _well("", "B1", "", volume="abc", sampleEnterVol=-1),
            _well("P1", "B2", "S5", specs="1e12"),
        ))

        self.assertEqual((resp.status_code, resp.json()["code"]), (400, 0))
        msg = resp.json()["msg"]
        self.assertIn("data[2]：wellno「I1」不是 96 孔板孔号", msg)
        self.assertIn("data[3]：wellno「A13」", msg)
        self.assertIn("potency 不能为空", msg)
        self.assertIn("data[4]：plateno 不能为空，sampleName 不能为空，volume「abc」不是数字，sampleEnterVol「-1」必须是非负数", msg)
        self.assertIn("data[5]：specs「1e12」超出范围", msg)
        self.assertEqual(self.wells(), {})

    def test_slash_means_potency_and_specs_do_not_apply(self):
        resp = self.client.post(URL, json=_payload(
            _well("P1", "A1", "S1", potency="/", specs="／"),
            _well("P1", "A2", "S2", potency="0", specs="0"),
        ))
        self.assertEqual(resp.json()["code"], 1)
        wells = self.wells()
        blank = wells[("BAO0000900", "P1", "A01")]
        self.assertIsNone(blank.potency)
        self.assertIsNone(blank.specs)
        self.assertEqual(blank.volume, Decimal("20"))
        zero = wells[("BAO0000900", "P1", "A02")]
        self.assertEqual((zero.potency, zero.specs), (Decimal("0"), Decimal("0")))

        marked = self.client.post(URL, json=_payload(
            _well("未合成", "未合成", "S9", potency="M", specs="0", volume="0", sampleEnterVol="0"),
            _well("P1", "noShipping", "S10", potency="M"),
            _well("未合成", "未合成", "S1", potency="M"),
            _well("P1", "A3", "S3"),
        ))
        self.assertEqual(marked.json()["code"], 1)
        rows = list(self.db.scalars(select(SynthesisSupernatantWell)))
        self.assertEqual(sorted(row.well_no for row in rows if not row.not_synthesized), ["A01", "A02", "A03"])
        markers = {row.sample_name: row for row in rows if row.not_synthesized}
        self.assertEqual(sorted(markers), ["S10", "S9"])
        self.assertEqual((markers["S9"].plate_no, markers["S9"].well_no, markers["S9"].volume), (None, None, None))

        self.client.post(URL, json=_payload(_well("未合成", "未合成", "S9"), _well("P2", "B5", "S9")))
        rows = list(self.db.scalars(select(SynthesisSupernatantWell)))
        self.assertEqual(sorted(row.sample_name for row in rows if row.not_synthesized), ["S10"])
        self.assertIn(("P2", "B05", "S9"), {(row.plate_no, row.well_no, row.sample_name) for row in rows})

        self.client.post(URL, json=_payload(_well("未合成", "未合成", "S10")))
        self.assertEqual(sum(1 for row in self.db.scalars(select(SynthesisSupernatantWell)) if row.not_synthesized), 1)

        rejected = self.client.post(URL, json=_payload(_well("P1", "B1", "S3", volume="/")))
        self.assertEqual(rejected.json()["code"], 0)
        self.assertIn("volume「/」不是数字", rejected.json()["msg"])

    def _order(self, order_no, **fields):
        row = DiscoverySynthesisOrder(
            synthesis_order_id=fields.pop("synthesis_order_id", f"SYN-261124-{order_no[-6:]}"),
            status=fields.pop("status", "合成中"),
            priority="正常",
            order_kind="常规合成",
            supply_mode="合成到货",
            order_no=order_no,
            target_type=fields.pop("target_type", "分泌型"),
            **fields,
        )
        self.db.add(row)
        self.db.commit()
        return row

    def test_push_sets_ship_date_and_count_and_one_no_longer_does(self):
        pending = self._order("BAO0000900")
        old_dated = self._order("bao0000901", arrival_date="2026-11-01", arrival_count=192)
        done = self._order("BAO0000902", status="已完成", arrival_date="2026-10-01", arrival_count=5)
        with patch("modules.supernatant_receive.service.now_local", return_value=datetime(2026, 11, 24, 9, 30)):
            self.client.post(URL, json=_payload(_well("P1", "A1", "S1"), _well("未合成", "未合成", "S9")))
            self.client.post(URL, json=_payload(_well("P1", "A1", "S1"), order_no="BAO0000901"))
            self.client.post(URL, json=_payload(_well("P1", "A1", "S1"), order_no="BAO0000902"))
            self.client.post(URL, json=_payload(_well("未合成", "未合成", "S2"), order_no="BAO0000903"))
        for row in (pending, old_dated, done):
            self.db.refresh(row)
        self.assertEqual((pending.arrival_date, pending.arrival_count, pending.status), ("2026-11-24", 1, "待检测"))
        self.assertEqual((old_dated.arrival_date, old_dated.arrival_count), ("2026-11-24", 1))
        self.assertEqual((done.arrival_date, done.arrival_count), ("2026-10-01", 5))

        with patch("modules.supernatant_receive.service.now_local", return_value=datetime(2026, 11, 26, 8, 0)):
            self.client.post(URL, json=_payload(_well("P1", "A2", "S3"), _well("P1", "A1", "S1")))
        self.db.refresh(pending)
        self.assertEqual((pending.arrival_date, pending.arrival_count), ("2026-11-24", 2))

        snapshot = {"order_no": "BAO0000900", "arrival_date": "2026-11-20", "arrival_count": 192}
        apply_remote_snapshot_to_row(pending, snapshot)
        self.assertEqual((pending.arrival_date, pending.arrival_count), ("2026-11-24", 2))
        self.assertNotIn("arrival_date", pending.source_snapshot)
        self.assertEqual(compute_drift_fields(pending), [])

    def test_bad_body_and_missing_order(self):
        cases = (
            (b"{bad", "JSON 格式错误"),
            (b"[]", "请求体必须是 JSON 对象"),
            (json.dumps({"corpName": "擎科", "data": []}).encode(), "orderNo 不能为空；data 必须是非空数组"),
            ("你好".encode("gbk"), "UTF-8"),
        )
        for raw, expected in cases:
            with self.subTest(raw=raw):
                resp = self.client.post(URL, content=raw, headers={"Content-Type": "application/json"})
                self.assertEqual((resp.status_code, resp.json()["code"]), (400, 0))
                self.assertIn(expected, resp.json()["msg"])

    def test_token_is_checked_and_errors_use_partner_codes(self):
        self.settings.supernatant_receive_token = "s3cret"
        body = _payload(_well("P1", "A1", "S1"))

        resp = self.client.post(URL, json=body)
        self.assertEqual((resp.status_code, resp.json()), (401, {"code": 0, "msg": "调用方校验失败", "data": None}))
        resp = self.client.post(URL, json=body, headers={"X-Callback-Token": "s3cret"})
        self.assertEqual(resp.json()["code"], 1)

        with patch("modules.supernatant_receive.service.receive", side_effect=RuntimeError("boom")):
            resp = self.client.post(URL, json=body, headers={"X-Callback-Token": "s3cret"})
        self.assertEqual((resp.status_code, resp.json()["code"]), (500, 0))
