"""合成工单查看转染配对、下载合成公司板布局。"""

from datetime import date
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

from openpyxl import load_workbook

from core.errors import NotFoundError
from models.discovery import DiscoverySynthesisOrder
from models.molecular_cell import (
    MolecularTransfectionItem,
    MolecularTransfectionOrder,
    MolecularTransfectionProtein,
)
from models.supernatant import SynthesisSupernatantWell
from modules.discovery.synthesis_progress import order_files
from modules.molecular_cell.transfection import proteins, service
from support import DbTestCase

TODAY = date(2026, 11, 23)


class OrderFileTests(DbTestCase):
    tables = (
        DiscoverySynthesisOrder,
        MolecularTransfectionOrder,
        MolecularTransfectionProtein,
        MolecularTransfectionItem,
        SynthesisSupernatantWell,
    )

    def setUp(self):
        super().setUp()
        clock = patch("modules.molecular_cell.transfection.service.today_local", return_value=TODAY)
        clock.start()
        self.addCleanup(clock.stop)

    def _synthesis(self, **fields):
        row = DiscoverySynthesisOrder(
            synthesis_order_id=fields.pop("synthesis_order_id", "SYN-261123-ABC123"),
            status="合成中",
            priority="正常",
            order_kind="常规合成",
            supply_mode=fields.pop("supply_mode", "合成到货"),
            **fields,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def test_transfection_pairs_follow_the_handoff_order_no(self):
        order = service.save(self.db, {"transfection_type": service.TYPE_PLASMID}, created_by="张三")
        proteins.import_proteins(
            self.db,
            order["id"],
            [{"row": 2, "protein_name": "Ab1", "heavy_chain": "H1", "light_chain": "L1"}],
        )
        synthesis = self._synthesis(order_no=order["transfection_order_id"], supply_mode="内部转染")
        payload = order_files.transfection_pairs(self.db, synthesis.id)
        self.assertEqual(payload["transfection_order_id"], order["transfection_order_id"])
        self.assertEqual(
            [(item["protein_name"], item["heavy_chain"], item["light_chain"]) for item in payload["items"]],
            [("Ab1", "H1", "L1")],
        )
        plain = self._synthesis(synthesis_order_id="SYN-261123-PLAIN01", order_no="BAO1")
        self.assertIsNone(order_files.transfection_pairs(self.db, plain.id)["transfection_order_id"])

    def test_plate_layout_exports_company_wells(self):
        synthesis = self._synthesis(order_no="bao9")
        self.db.add(SynthesisSupernatantWell(
            order_no="BAO9",
            corp_name="擎科",
            plate_no="P1",
            well_no="A01",
            sample_name="Ab1",
            potency=Decimal("100.5000"),
            specs=Decimal("2"),
            volume=Decimal("20"),
            sample_enter_vol=Decimal("1.2500"),
        ))
        self.db.add(SynthesisSupernatantWell(
            order_no="BAO9",
            corp_name="擎科",
            plate_no="P1",
            well_no="A02",
            sample_name="Ab2",
            potency=None,
            specs=None,
            volume=Decimal("1"),
            sample_enter_vol=Decimal("1"),
        ))
        self.db.commit()
        output, filename = order_files.export_plate_layout(self.db, synthesis.id)
        self.assertTrue(filename.startswith("版布局_bao9_"))
        sheet = load_workbook(BytesIO(output.getvalue())).active
        self.assertEqual(sheet["A2"].value, "BAO9")
        self.assertEqual(sheet["E2"].value, "Ab1")
        self.assertEqual(sheet["F2"].value, 100.5)
        self.assertIsNone(sheet["F3"].value)
        self.assertIsNone(sheet["G3"].value)

        empty = self._synthesis(synthesis_order_id="SYN-261123-EMPTY01", order_no="NONE")
        with self.assertRaises(NotFoundError):
            order_files.export_plate_layout(self.db, empty.id)
