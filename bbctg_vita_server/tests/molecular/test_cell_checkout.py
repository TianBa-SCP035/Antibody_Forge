"""文库构建冻存细胞出库申请与审核。"""

from core.errors import NotFoundError
from models.discovery import DiscoveryCellBank, DiscoveryWorkbench
from models.molecular_cell import MolecularCellCheckoutItem, MolecularCellCheckoutRequest, MolecularLibraryOrder
from modules.discovery.workbench import cell_bank
from modules.discovery.workbench import service as discovery_service
from modules.molecular_cell.library_orders import cell_checkout, service
from support import DbTestCase


class CellCheckoutTests(DbTestCase):
    tables = (
        DiscoveryWorkbench,
        DiscoveryCellBank,
        MolecularLibraryOrder,
        MolecularCellCheckoutRequest,
        MolecularCellCheckoutItem,
    )

    def _order_with_cells(self, code, *cells, build_type=service.BUILD_POOLED_BCR):
        arrangement = discovery_service.save(self.db, {"project_code": f"P-{code}", "mouse_strain": "RN"})
        order = service.save(self.db, {
            "build_type": build_type,
            "sample_source": service.SOURCE_DAPU_TUBE if build_type == service.BUILD_POOLED_BCR else None,
            "library_code": code,
            "target_name": "PD1",
            "mouse_strain": "RN",
            "instrument_on": "2026-11-20",
        })
        self.db.get(MolecularLibraryOrder, order["id"]).source_discovery_id = arrangement["discovery_id"]
        self.db.commit()
        banks = [
            cell_bank.save_record(self.db, {"workbench_id": arrangement["id"], **cell})
            for cell in cells
        ]
        return order, banks

    def test_filtered_codes_submit_one_request_and_approve_checks_out(self):
        first, first_banks = self._order_with_cells(
            "C101", {"cell_kind": "脾细胞", "cell_count": "1e7", "tube_count": 2, "remark": "RN 鼠"}, {"cell_kind": "淋巴结"}
        )
        _, second_banks = self._order_with_cells("C102", {"cell_kind": "骨髓", "cell_count": "5e6"})
        self._order_with_cells("D900", {"cell_kind": "PBMC"})

        with self.assertRaisesRegex(ValueError, "请先按建库编号筛选"):
            cell_checkout.candidates(self.db, {"filters": {}})
        found = cell_checkout.candidates(self.db, {"filters": {"library_code": "C101,C102"}})
        self.assertEqual(found["order_count"], 2)
        self.assertEqual(len(found["items"]), 3)
        detail = next(item for item in found["items"] if item["cell_bank_id"] == first_banks[0]["id"])
        self.assertEqual(
            (detail["library_code"], detail["target_name"], detail["instrument_on"], detail["mouse_strain"],
             detail["cell_count"], detail["sample_source"]),
            ("C101", "PD1", "2026-11-20", "RN", "1e7", "达普打管"),
        )

        bank_ids = [item["cell_bank_id"] for item in found["items"]]
        request = cell_checkout.submit(
            self.db, {"filters": {"library_code": "C101,C102"}, "cell_bank_ids": bank_ids}, "李四"
        )
        self.assertRegex(request["request_no"], r"^CKO-\d{6}-[A-Z0-9]{6}$")
        self.assertEqual((request["status"], request["applicant"], request["item_count"]), ("待审核", "李四", 3))
        self.assertEqual(len(request["items"]), 3)
        self.assertIn("RN 鼠", [item["remark"] for item in request["items"]])

        self.assertEqual(cell_checkout.candidates(self.db, {"order_ids": [first["id"]]})["items"], [])
        with self.assertRaisesRegex(ValueError, cell_checkout.STALE_SELECTION):
            cell_checkout.submit(self.db, {"order_ids": [first["id"]], "cell_bank_ids": [first_banks[0]["id"]]}, "王五")
        with self.assertRaisesRegex(ValueError, "出库审核中"):
            cell_bank.checkout_record(self.db, second_banks[0]["id"], "王五")
        with self.assertRaisesRegex(ValueError, "出库审核中"):
            cell_bank.delete_record(self.db, second_banks[0]["id"])

        listed = cell_checkout.list_requests(self.db, {"status": "待审核"})
        self.assertEqual([row["id"] for row in listed["items"]], [request["id"]])

        reviewed = cell_checkout.review(self.db, request["id"], True, "管理员")
        self.assertEqual((reviewed["status"], reviewed["reviewer"]), ("已通过", "管理员"))
        stored = self.db.get(DiscoveryCellBank, second_banks[0]["id"])
        self.assertEqual(stored.checked_out_by, "李四")
        self.assertIsNotNone(stored.checked_out_on)
        with self.assertRaisesRegex(ValueError, "申请单已审核"):
            cell_checkout.review(self.db, request["id"], False, "管理员")
        self.assertEqual(cell_checkout.list_requests(self.db, {"status": "待审核"})["items"], [])

    def test_reject_releases_cells_for_a_new_request(self):
        order, banks = self._order_with_cells("C201", {"cell_kind": "脾细胞"})
        request = cell_checkout.submit(self.db, {"order_ids": [order["id"]], "cell_bank_ids": [banks[0]["id"]]}, "李四")
        rejected = cell_checkout.review(self.db, request["id"], False, "管理员", "管数不对")
        self.assertEqual((rejected["status"], rejected["review_note"]), ("已驳回", "管数不对"))
        self.assertIsNone(self.db.get(DiscoveryCellBank, banks[0]["id"]).checked_out_on)
        self.assertEqual(len(cell_checkout.candidates(self.db, {"order_ids": [order["id"]]})["items"]), 1)
        with self.assertRaises(NotFoundError):
            cell_checkout.review(self.db, 999, True, "管理员")

    def test_scope_hides_orders_of_other_build_types(self):
        order, banks = self._order_with_cells("C301", {"cell_kind": "脾细胞"})
        plate_only = frozenset({service.BUILD_PLATE})
        found = cell_checkout.candidates(self.db, {"order_ids": [order["id"]]}, plate_only)
        self.assertEqual((found["order_count"], found["items"]), (0, []))
        request = cell_checkout.submit(self.db, {"order_ids": [order["id"]], "cell_bank_ids": [banks[0]["id"]]}, "李四")
        self.assertEqual(cell_checkout.list_requests(self.db, {}, plate_only)["items"], [])
        with self.assertRaises(NotFoundError):
            cell_checkout.review(self.db, request["id"], True, "管理员", scope=plate_only)

    def test_empty_scope_hides_orders_but_review_stays_open(self):
        order, banks = self._order_with_cells("C302", {"cell_kind": "脾细胞"})
        request = cell_checkout.submit(
            self.db, {"order_ids": [order["id"]], "cell_bank_ids": [banks[0]["id"]]}, "李四",
        )
        blocked = frozenset()
        found = cell_checkout.candidates(self.db, {"order_ids": [order["id"]]}, blocked)
        self.assertEqual((found["order_count"], found["items"]), (0, []))
        listed = cell_checkout.list_requests(self.db, {}, blocked)
        self.assertEqual([row["id"] for row in listed["items"]], [request["id"]])
        reviewed = cell_checkout.review(self.db, request["id"], True, "管理员", scope=blocked)
        self.assertEqual(reviewed["status"], "已通过")
