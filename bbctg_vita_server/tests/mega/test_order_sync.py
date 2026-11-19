"""镁伽结果回传：先留存再核对、trace_id 重推原样返回、逐板核对，以及导入效价时的手工/自动覆盖规则。"""

from datetime import datetime
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import FastAPI, UploadFile
from fastapi.testclient import TestClient

from core.config import get_settings
from db.session import get_db
from models.immunology import (
    SOURCE_MANUAL,
    SOURCE_MEGA,
    SerumFacsPlate,
    SerumFile,
    SerumImmMouse,
    SerumImmProject,
    SerumTiterOrder,
    SerumTiterPc,
    SerumTiterTarget,
)
from models.mega_automation import MegaFlowWorkOrder, MegaFlowWorkOrderDispatch
from models.order_sync import OrderSync, OrderSyncBoard
from modules.immunology.titer import service as titer_service
from modules.order_sync import routes, service, titer_import
from modules.order_sync.heatmap import parse_heatmap
from support import DbTestCase

UPPER_MICE = [f"M{index}" for index in range(1, 11)]
LOWER_MICE = [f"M{index}" for index in range(11, 21)]
IMAGE_PATH = "images/abc/可视化图_SMP-1_261118.png"
CSV_PATH = "csv/abc/热图_SMP-1_261118.csv"


def _heatmap_rows(percent: dict[str, float]) -> list[list[str]]:
    header = ["", *[str(column) for column in range(1, 13)]]
    rows = [["样品", "SMP-1"], ["统计项", "RL1-H Mean"], header]
    rows += [[row, *["100"] * 12] for row in "ABCDEFGH"]
    rows += [["统计项", "%Parent"], header]
    for row in "ABCDEFGH":
        rows.append([row, *[f"{percent.get(f'{row}{column}', 1.0)}%" for column in range(1, 13)]])
    return rows


def _heatmap_csv(percent: dict[str, float]) -> bytes:
    return "\n".join(",".join(row) for row in _heatmap_rows(percent)).encode("utf-8")


def _sample_wells() -> list[dict]:
    wells = []
    for row in "ABCDEFGH":
        for column in range(1, 13):
            well_no = f"{row}{column:02d}"
            if column == 1:
                wells.append({"well_no": well_no, "content_type": "NC", "sample_code": "", "pc_id": None})
            elif column == 12:
                pc_id = "101" if row in "AE" else None
                wells.append({"well_no": well_no, "content_type": "PC", "sample_code": "", "pc_id": pc_id})
            elif row in "AE":
                mice = UPPER_MICE if row == "A" else LOWER_MICE
                wells.append({"well_no": well_no, "content_type": "SAMPLE", "sample_code": mice[column - 2], "pc_id": None})
            else:
                wells.append({"well_no": well_no, "content_type": "BLANK", "sample_code": "", "pc_id": None})
    return wells


def _dispatch_payload() -> dict:
    return {
        "dispatchId": "DSP1",
        "orderNum": "ORD-1",
        "orderDetail": {
            "pc_infos": [
                {
                    "pc_id": "101",
                    "pc_type": "SERUM",
                    "pc_name": "PC-A",
                    "catalog_batch": "B1",
                    "source": "BBCTG",
                    "concentration": "10ug/ml",
                }
            ],
            "sample_plates": [
                {
                    "barcode": "SMP-1",
                    "project_no": "E1",
                    "target": "PD1",
                    "cell_keys": [{"barcode": "CELL-1", "column_no": 1}],
                    "wells": _sample_wells(),
                }
            ],
            "cell_plates": [
                {
                    "barcode": "CELL-1",
                    "columns": [
                        {
                            "column_no": 1,
                            "cell_name": "CHO-hPD1",
                            "cell_type": "正常",
                            "species": "人",
                            "batch": "C1",
                            "generation": "P5",
                            "cell_count": "",
                            "catalog_no": "",
                            "source": "",
                        }
                    ],
                }
            ],
        },
    }


def _well_infos(overrides: dict[str, str] | None = None) -> list[dict]:
    wells = []
    for row, mice in (("A", UPPER_MICE), ("E", LOWER_MICE)):
        for index, mouse in enumerate(mice):
            well_no = f"{row}{index + 2:02d}"
            wells.append({"well_no": well_no, "sample_name": (overrides or {}).get(well_no, mouse), "ppc": 1.0})
    return wells


def _push(order_no: str = "ORD-1", well_overrides: dict[str, str] | None = None, sample_code: str = "SMP-1") -> dict:
    return {
        "order_infos": [
            {
                "order_no": order_no,
                "project_infos": [
                    {
                        "project_no": "E1",
                        "data_type": "TITER",
                        "experiment_date": "20261118",
                        "target": "PD1",
                        "cell_board_infos": [
                            {
                                "cell_name": "cho-hpd1",
                                "detect_board_infos": [
                                    {
                                        "barcode": "DET-1",
                                        "sample_code": sample_code,
                                        "whole_board_img": IMAGE_PATH,
                                        "heatmap_csv": CSV_PATH,
                                        "x_axis": "APC-H",
                                        "y_axis": "FITC-H",
                                        "well_infos": _well_infos(well_overrides),
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ]
    }


def _upload(content: bytes) -> UploadFile:
    return UploadFile(file=io.BytesIO(content), filename="order.json")


class OrderSyncTestCase(DbTestCase):
    tables = (
        OrderSync,
        OrderSyncBoard,
        MegaFlowWorkOrder,
        MegaFlowWorkOrderDispatch,
        SerumImmProject,
        SerumImmMouse,
        SerumTiterOrder,
        SerumFile,
        SerumFacsPlate,
        SerumTiterTarget,
        SerumTiterPc,
    )

    def setUp(self):
        super().setUp()
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.root = Path(temp_dir.name)
        root_patch = patch.object(get_settings(), "repository_root", self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)

        self.db.add(SerumImmProject(experiment_id="E1", project_code="P1"))
        self.db.add(SerumTiterOrder(experiment_id="E1", titer_order_id="T1", test_dates=["2026-11-01"]))
        self.db.add(
            SerumImmMouse(
                experiment_id="E1",
                group_id="G1",
                mouse_strain="RN",
                mouse_registry={"mice": [{"no": mouse} for mouse in UPPER_MICE[:5]]},
            )
        )
        order = MegaFlowWorkOrder(
            orderNum="ORD-1",
            orderType="TITER",
            source_id="T1",
            status="completed",
            sent_at=datetime(2026, 11, 17, 9, 0),
        )
        self.db.add(order)
        self.db.flush()
        self.db.add(
            MegaFlowWorkOrderDispatch(
                dispatchId="DSP1",
                work_order_id=order.id,
                payload=_dispatch_payload(),
                payload_hash="h",
                content_hash_at_send="c",
                status="completed",
            )
        )
        self.db.commit()
        self.work_order_id = order.id

    def receive(self, trace_id: str, payload: dict | bytes) -> service.SyncReply:
        content = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        return service.receive_sync(self.db, trace_id, _upload(content))

    def run_import(self, reply: service.SyncReply, percent: dict[str, float] | None = None) -> None:
        heatmap = _heatmap_csv(percent or {"A2": 30.0, "A3": 16.0})

        def fake_download(relative_path, target, _max_bytes):
            target.write_bytes(heatmap if relative_path.endswith(".csv") else b"png-bytes")

        with patch.object(titer_import.fcs_smb, "download", side_effect=fake_download):
            titer_import._run(self.db, reply.sync_id, reply.plans)


class ReceiveTests(OrderSyncTestCase):
    def test_valid_push_is_verified_stored_and_replayed(self):
        reply = self.receive("TR-1", _push())

        self.assertEqual(reply.http_status, 200)
        data = reply.body["data"]
        self.assertEqual(data["status"], "passed")
        self.assertEqual(data["success_orders"], ["ORD-1"])
        self.assertEqual(data["results"][0]["boards"][0]["status"], "passed")
        self.assertEqual(len(reply.plans), 1)
        plan = reply.plans[0]
        self.assertEqual(plan.experiment_id, "E1")
        self.assertEqual(plan.cell_name, "CHO-hPD1")
        self.assertEqual(plan.upper_mouse_list, ["NC", *UPPER_MICE, "PC"])
        self.assertEqual(plan.upper_pc["pc_name"], "PC-A")

        record = self.db.get(OrderSync, reply.sync_id)
        self.assertEqual((record.status, record.http_status, record.import_status), ("passed", 200, "pending"))
        self.assertEqual(record.response_body, reply.body)
        board = self.db.query(OrderSyncBoard).one()
        self.assertEqual((board.sample_barcode, board.verify_status, board.import_status), ("SMP-1", "passed", "pending"))

        replay = self.receive("TR-1", b"{}")
        self.assertEqual((replay.http_status, replay.body, replay.plans), (200, reply.body, []))
        self.assertEqual(self.db.query(OrderSync).count(), 1)

    def test_invalid_json_is_stored_with_its_reply(self):
        reply = self.receive("TR-BAD", b"{not json")

        self.assertEqual(reply.http_status, 400)
        record = self.db.get(OrderSync, reply.sync_id)
        self.assertEqual(record.status, "invalid")
        self.assertTrue((self.root / record.file_path.lstrip("/")).exists())
        self.assertEqual(self.receive("TR-BAD", _push()).body, reply.body)

    def test_unknown_order_and_mismatched_mouse_are_rejected_with_reasons(self):
        missing = self.receive("TR-2", _push(order_no="ORD-X"))
        self.assertEqual(missing.body["data"]["status"], "rejected")
        self.assertIn("订单不存在", missing.body["data"]["results"][0]["message"])
        self.assertEqual(missing.plans, [])

        mismatch = self.receive("TR-3", _push(well_overrides={"A03": "M99"}))
        board = mismatch.body["data"]["results"][0]["boards"][0]
        self.assertEqual(board["status"], "rejected")
        self.assertIn("A03 应为 M2，回传 M99", board["message"])

    def test_unanswered_record_gets_its_reply_on_reprocess(self):
        record = service._store_raw(self.db, "TR-CUT", json.dumps(_push()).encode("utf-8"))
        with self.assertRaises(service.OrderSyncError) as ctx:
            self.receive("TR-CUT", _push())
        self.assertEqual(ctx.exception.code, 409)

        detail, plans = service.reprocess_sync(self.db, record.id)

        self.assertEqual((detail["status"], detail["http_status"], len(plans)), ("passed", 200, 1))
        replay = self.receive("TR-CUT", b"{}")
        self.assertEqual(replay.http_status, 200)
        self.assertEqual(replay.body["data"]["success_orders"], ["ORD-1"])

    def test_sample_plate_is_matched_by_sample_code_only(self):
        unknown = self.receive("TR-4", _push(sample_code="TSPAN8-1"))
        board = unknown.body["data"]["results"][0]["boards"][0]
        self.assertEqual((board["barcode"], board["sample_code"], board["status"]), ("DET-1", "TSPAN8-1", "rejected"))
        self.assertEqual(board["message"], "样本板 TSPAN8-1 不在下发的样品板中")

        push = _push(sample_code="")
        push["order_infos"][0]["project_infos"][0]["cell_board_infos"][0]["detect_board_infos"][0]["barcode"] = "SMP-1"
        empty = self.receive("TR-5", push)
        self.assertEqual(empty.body["data"]["results"][0]["boards"][0]["message"], "sample_code 为空")


class RouteTests(OrderSyncTestCase):
    def setUp(self):
        super().setUp()
        app = FastAPI()
        app.include_router(routes.router, prefix="/order-experiment")
        app.dependency_overrides[get_db] = lambda: self.db
        patcher = patch(
            "modules.auth.external.get_settings",
            return_value=SimpleNamespace(order_sync_token="", order_sync_ips=""),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_missing_form_fields_get_400_in_reply_format(self):
        resp = self.client.post("/order-experiment/sync", data={"trace_id": "TR-9"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json(), {"code": 400, "message": "缺少 order_json 文件", "trace_id": "TR-9", "data": None})

        resp = self.client.post("/order-experiment/sync", files={"order_json": ("o.json", b"{}", "application/json")})
        self.assertEqual((resp.status_code, resp.json()["message"]), (400, "trace_id 不能为空"))
        self.assertEqual(self.db.query(OrderSync).count(), 0)


class TiterImportTests(OrderSyncTestCase):
    def test_import_creates_mega_files_plate_target_pc_and_test_date(self):
        reply = self.receive("TR-1", _push())
        self.run_import(reply)

        board = self.db.query(OrderSyncBoard).one()
        self.assertEqual(board.import_status, "done", board.import_message)
        plate = self.db.get(SerumFacsPlate, board.facs_plate_id)
        self.assertEqual(plate.source, SOURCE_MEGA)
        self.assertEqual(plate.qr_code, "SMP-1")
        self.assertEqual(plate.positive_well_list, ["A2", "A3"])
        self.assertEqual((plate.x_axis, plate.y_axis, plate.instrument_type), ("APC-H", "FITC-H", "国产"))
        self.assertEqual(plate.upper_slot_groups, [{"start": 1, "end": 5, "label": "G1-RN"}])
        self.assertEqual(self.db.get(SerumTiterTarget, plate.cell_target_id).name, "CHO-hPD1")
        self.assertEqual(plate.pc_upper_id, plate.pc_lower_id)
        image = self.db.get(SerumFile, plate.image_file_id)
        self.assertEqual((image.source, image.file_name), (SOURCE_MEGA, "可视化图_SMP-1_261118.png"))
        self.assertTrue(titer_service.get_full_path(image.file_path).exists())
        order = self.db.query(SerumTiterOrder).one()
        self.assertEqual(order.test_dates, ["2026-11-01", "2026-11-18"])
        self.assertEqual(self.db.get(OrderSync, reply.sync_id).import_status, "done")

    def test_missing_axes_are_left_blank_with_warning(self):
        push = _push()
        detect = push["order_infos"][0]["project_infos"][0]["cell_board_infos"][0]["detect_board_infos"][0]
        del detect["x_axis"], detect["y_axis"]
        reply = self.receive("TR-1", push)
        self.assertIn("x_axis / y_axis 未填", reply.body["data"]["results"][0]["boards"][0]["message"])
        self.run_import(reply)

        plate = self.db.get(SerumFacsPlate, self.db.query(OrderSyncBoard).one().facs_plate_id)
        self.assertEqual((plate.x_axis, plate.y_axis), ("", ""))

    def test_recallback_updates_untouched_auto_plate_in_place(self):
        first = self.receive("TR-1", _push())
        self.run_import(first)
        board = self.db.query(OrderSyncBoard).one()
        old_path = titer_service.get_full_path(self.db.get(SerumFile, board.image_file_id).file_path)

        second = self.receive("TR-2", _push())
        self.run_import(second, {"B5": 50.0})

        boards = self.db.query(OrderSyncBoard).order_by(OrderSyncBoard.id).all()
        self.assertEqual(boards[1].facs_plate_id, boards[0].facs_plate_id)
        self.assertEqual(boards[1].image_file_id, boards[0].image_file_id)
        self.assertEqual(self.db.query(SerumFacsPlate).count(), 1)
        self.assertEqual(self.db.query(SerumFile).count(), 2)
        self.assertEqual(self.db.get(SerumFacsPlate, boards[0].facs_plate_id).positive_well_list, ["B5"])
        self.assertFalse(old_path.exists())

    def test_manually_saved_plate_and_replaced_file_are_not_overwritten(self):
        first = self.receive("TR-1", _push())
        self.run_import(first)
        board = self.db.query(OrderSyncBoard).one()
        plate = self.db.get(SerumFacsPlate, board.facs_plate_id)
        titer_service.save_facs_plate(self.db, {**plate.to_dict(), "immune_stage": "三免"})
        self.assertEqual(self.db.get(SerumFacsPlate, plate.id).source, SOURCE_MANUAL)

        second = self.receive("TR-2", _push())
        self.run_import(second)
        latest = self.db.query(OrderSyncBoard).order_by(OrderSyncBoard.id.desc()).first()
        self.assertEqual(latest.import_status, "skipped")
        self.assertEqual(latest.import_message, "板卡已人工修改，未覆盖")
        self.assertEqual(self.db.get(SerumFacsPlate, plate.id).immune_stage, "三免")

        titer_service.rename_file(self.db, board.image_file_id, "改名.png")
        self.assertEqual(self.db.get(SerumFile, board.image_file_id).source, SOURCE_MANUAL)

    def test_deleted_auto_plate_is_recreated_and_reprocess_reuses_rows(self):
        first = self.receive("TR-1", _push())
        self.run_import(first)
        board = self.db.query(OrderSyncBoard).one()
        titer_service.delete_facs_plate(self.db, board.facs_plate_id)

        _detail, plans = service.reprocess_sync(self.db, first.sync_id)
        self.assertEqual(self.db.query(OrderSyncBoard).count(), 1)
        self.run_import(service.SyncReply(200, {}, plans, first.sync_id))

        board = self.db.query(OrderSyncBoard).one()
        self.assertEqual(board.import_status, "done")
        self.assertIsNotNone(self.db.get(SerumFacsPlate, board.facs_plate_id))
        self.assertEqual(self.db.get(OrderSync, first.sync_id).response_body, first.body)

    def test_download_failure_marks_board_retryable(self):
        reply = self.receive("TR-1", _push())
        with patch.object(titer_import.fcs_smb, "download", side_effect=titer_import.fcs_smb.FcsSmbError("连不上")):
            titer_import._run(self.db, reply.sync_id, reply.plans)
        board = self.db.query(OrderSyncBoard).one()
        self.assertEqual(board.import_status, "download_failed")
        self.assertIn("连不上", board.import_message)
        self.assertEqual(self.db.get(OrderSync, reply.sync_id).import_status, "failed")
        self.assertEqual(self.db.query(SerumFacsPlate).count(), 0)


class HeatmapTests(unittest.TestCase):
    def test_domestic_percent_table_is_read_after_mean_table(self):
        result = parse_heatmap(_heatmap_rows({"A2": 15.0, "A3": 15.5, "H12": 80.0}))
        self.assertEqual((result.positive_wells, result.error), (["A3", "H12"], ""))

    def test_fraction_values_are_scaled_to_percent(self):
        rows = [["统计项", "%Parent"], ["", *[str(column) for column in range(1, 13)]]]
        rows.append(["A", "0.2", *["0.01"] * 11])
        self.assertEqual(parse_heatmap(rows).positive_wells, ["A1"])

    def test_unknown_format_reports_error(self):
        self.assertTrue(parse_heatmap([["Experiment:", "x"]]).error)
