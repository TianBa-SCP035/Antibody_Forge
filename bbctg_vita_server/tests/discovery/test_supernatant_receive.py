from decimal import Decimal
import json
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from db.session import get_db
from models.supernatant import SynthesisSupernatantWell
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
    tables = (SynthesisSupernatantWell,)

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

    def test_repush_replaces_whole_plate(self):
        self.client.post(URL, json=_payload(_well("P1", "A1", "S1"), _well("P1", "A2", "S2"), _well("P2", "A1", "T1")))
        resp = self.client.post(URL, json=_payload(_well("P1", "A1", "S9"), _well("P1", "C3", "S8")))

        self.assertEqual(resp.json()["code"], 1)
        wells = self.wells()
        self.assertEqual(sorted(key[1:] for key in wells), [("P1", "A01"), ("P1", "C03"), ("P2", "A01")])
        self.assertEqual(wells[("BAO0000900", "P1", "A01")].sample_name, "S9")
        self.assertEqual(wells[("BAO0000900", "P2", "A01")].sample_name, "T1")

        self.client.post(URL, json=_payload(_well("P1", "A1", "X1"), order_no="BAO0000901"))
        self.assertEqual(len(self.wells()), 4)

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
