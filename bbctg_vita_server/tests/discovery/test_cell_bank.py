"""发现工作台留存细胞冻存入库。"""

from core.errors import NotFoundError
from models.discovery import DiscoveryCellBank, DiscoveryWorkbench
from models.molecular_cell import MolecularCellCheckoutItem, MolecularCellCheckoutRequest
from modules.discovery.workbench import cell_bank, service
from support import DbTestCase


class CellBankTests(DbTestCase):
    tables = (DiscoveryWorkbench, DiscoveryCellBank, MolecularCellCheckoutRequest, MolecularCellCheckoutItem)

    def test_save_lists_and_deletes_for_one_arrangement(self):
        saved = service.save(self.db, {"project_code": "P1", "mouse_nos": "1、2"})
        record = cell_bank.save_record(
            self.db,
            {
                "workbench_id": saved["id"],
                "cell_kind": "脾细胞",
                "mouse_nos": "1",
                "tube_count": "2",
                "frozen_on": "2026/11/23",
                "box_location": "A-1",
            },
            created_by="张三",
        )
        self.assertEqual(record["discovery_id"], saved["discovery_id"])
        self.assertEqual((record["tube_count"], record["frozen_on"], record["created_by"]), (2, "2026-11-23", "张三"))
        listed = cell_bank.list_records(self.db, saved["id"])
        self.assertEqual([item["id"] for item in listed["items"]], [record["id"]])

        checked = cell_bank.checkout_record(self.db, record["id"], " 苏正凤 ")
        self.assertEqual(checked["checked_out_by"], "苏正凤")
        self.assertEqual(len(checked["checked_out_on"]), 10)
        with self.assertRaisesRegex(ValueError, "请填写出库人"):
            cell_bank.checkout_record(self.db, record["id"], " ")

        cell_bank.delete_record(self.db, record["id"])
        self.assertEqual(cell_bank.list_records(self.db, saved["id"])["items"], [])

    def test_rejects_unknown_arrangement_and_bad_count(self):
        with self.assertRaises(NotFoundError):
            cell_bank.list_records(self.db, 99)
        saved = service.save(self.db, {"project_code": "P2"})
        with self.assertRaisesRegex(ValueError, "管数必须是整数"):
            cell_bank.save_record(self.db, {"workbench_id": saved["id"], "cell_kind": "淋巴结", "tube_count": "两管"})
        with self.assertRaisesRegex(ValueError, "请填写细胞类型"):
            cell_bank.save_record(self.db, {"workbench_id": saved["id"], "cell_kind": "  "})
