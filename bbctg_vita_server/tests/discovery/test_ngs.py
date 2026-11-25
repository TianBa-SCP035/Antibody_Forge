"""NGS：测序单状态、文库交接、送合成。"""

import re
import unittest

from core.errors import NotFoundError
from models.discovery import DiscoveryNgsRun, DiscoverySynthesisOrder
from models.molecular_cell import MolecularLibraryOrder
from models.target import Target
from modules.auth.permissions import PERMISSIONS
from modules.discovery.permissions import ACCESS
from modules.discovery.ngs import service
from modules.molecular_cell.library_orders import service as library_service
from support import DbTestCase

RUN_ID_RE = re.compile(r"^NGS-\d{6}-[A-Z0-9]{6}$")


class NgsTests(DbTestCase):
    tables = (
        Target,
        DiscoverySynthesisOrder,
        DiscoveryNgsRun,
        MolecularLibraryOrder,
    )

    def _run(self, **fields):
        payload = {"sample_library": service.SAMPLE_NANO_LIB, **fields}
        return service.save(self.db, payload, created_by="张三")

    def _library(self, **fields):
        payload = {
            "build_type": library_service.BUILD_PLASMA_NGS,
            "sample_type": library_service.SAMPLE_NANO,
            "source_project_code": "P1",
            "study_type": "抗体发现",
            "target_name": "PD1",
            "target_codes": ["T1"],
            "pm": "李四",
            "mouse_strain": "RL",
            "library_code": "LIB-1",
            "positive_cell_count": "120",
            **fields,
        }
        return library_service.save(self.db, payload)

    def test_permissions_registered(self):
        self.assertIn("discovery.page.ngs", PERMISSIONS)
        self.assertIn("discovery.ngs.edit", PERMISSIONS)
        self.assertIn("menu.discovery.ngs", {flag["code"] for flag in ACCESS.features})

    def test_save_assigns_id_and_date_moves_status(self):
        saved = self._run(ngs_run_id="NGS-000000-HACK00")
        self.assertRegex(saved["ngs_run_id"], RUN_ID_RE)
        self.assertEqual(saved["status"], service.STATUS_WAIT)
        self.assertEqual(saved["created_by"], "张三")
        dated = service.save(self.db, {"id": saved["id"], "sequencing_date": "2026-11-20"})
        self.assertEqual(dated["status"], service.STATUS_RUN)
        cleared = service.save(self.db, {"id": saved["id"], "sequencing_date": ""})
        self.assertIsNone(cleared["sequencing_date"])
        self.assertEqual(cleared["status"], service.STATUS_WAIT)
        with self.assertRaisesRegex(ValueError, "已送合成"):
            service.save(self.db, {"id": saved["id"], "status": service.STATUS_SENT})
        with self.assertRaisesRegex(ValueError, "样品库"):
            service.save(self.db, {})

    def test_library_handoff_copies_fields_and_allows_repeat(self):
        library = self._library()
        first = service.handoff_from_library(self.db, library["id"], created_by="张三")
        second = service.handoff_from_library(self.db, library["id"], created_by="张三")
        self.assertNotEqual(first["ngs_run_id"], second["ngs_run_id"])
        self.assertEqual(first["sample_library"], service.SAMPLE_NANO_LIB)
        self.assertEqual(first["source_library_order_id"], library["library_order_id"])
        self.assertEqual(first["library_code"], "LIB-1")
        self.assertEqual(first["target_name"], "PD1")
        self.assertEqual(first["pm"], "李四")
        self.assertEqual(first["mouse_strain"], "RL")
        self.assertEqual(first["cell_count"], "120")
        self.assertEqual(first["status"], service.STATUS_WAIT)

    def test_plate_and_cancelled_library_cannot_handoff(self):
        plate = self._library(build_type=library_service.BUILD_PLATE, sample_type=None, library_code="LIB-PLATE")
        with self.assertRaisesRegex(ValueError, "转染与表达"):
            service.handoff_from_library(self.db, plate["id"])
        cancelled = self._library(status=library_service.STATUS_CANCELLED, library_code="LIB-CANCEL")
        with self.assertRaisesRegex(ValueError, "已取消"):
            service.handoff_from_library(self.db, cancelled["id"])
        with self.assertRaises(NotFoundError):
            service.handoff_from_library(self.db, 999999)

    def test_phage_library_maps_to_phage_sample(self):
        library = self._library(
            build_type=library_service.BUILD_PHAGE_NGS,
            sample_type=library_service.SAMPLE_PHAGE,
            library_code="LIB-PHAGE",
            project_goal="富集 PD1",
        )
        saved = service.handoff_from_library(self.db, library["id"])
        self.assertEqual(saved["sample_library"], service.SAMPLE_PHAGE_LIB)
        self.assertEqual(saved["screening_goal"], "富集 PD1")

    def test_send_to_synthesis_then_lock_and_block_delete(self):
        saved = self._run(
            target_name="PD1",
            target_codes=["T1"],
            pm="李四",
            mouse_strain="RL",
            synthesis_code="20R489_RNBW01",
            project_code="P1",
            batch_name="B1",
        )
        with self.assertRaisesRegex(ValueError, "送合成转码"):
            service.handoff_to_synthesis(self.db, service.save(self.db, {"sample_library": service.SAMPLE_LITE_LIB})["id"])
        sent = service.handoff_to_synthesis(self.db, saved["id"], created_by="张三")
        self.assertRegex(sent["synthesis_order_id"], r"^SYN-")
        self.assertEqual(sent["order"]["status"], service.STATUS_SENT)
        order = self.db.query(DiscoverySynthesisOrder).filter_by(synthesis_order_id=sent["synthesis_order_id"]).one()
        self.assertEqual(order.order_kind, "常规合成")
        self.assertEqual(order.supply_mode, "合成到货")
        self.assertEqual(order.synthesis_code, "20R489_RNBW01")
        self.assertEqual(order.pm, "李四")
        self.assertEqual(order.batch_label, "B1")
        with self.assertRaisesRegex(ValueError, "不能再改"):
            service.save(self.db, {"id": saved["id"], "synthesis_code": "OTHER"})
        with self.assertRaisesRegex(ValueError, "不能删除"):
            service.delete_run(self.db, saved["id"])
        done = service.save(self.db, {"id": saved["id"], "status": service.STATUS_DONE})
        self.assertEqual(done["status"], service.STATUS_DONE)

    def test_list_stats_ignore_selected_status(self):
        self._run()
        dated = self._run(sample_library=service.SAMPLE_LITE_LIB)
        service.save(self.db, {"id": dated["id"], "sequencing_date": "2026-11-01"})
        listed = service.get_list(self.db, {"status": service.STATUS_WAIT})
        self.assertEqual(listed["total"], 1)
        self.assertEqual(listed["stats"][service.STATUS_WAIT], 1)
        self.assertEqual(listed["stats"][service.STATUS_RUN], 1)


if __name__ == "__main__":
    unittest.main()
