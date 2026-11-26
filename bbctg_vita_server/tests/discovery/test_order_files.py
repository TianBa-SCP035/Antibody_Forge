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
            order_kind=fields.pop("order_kind", "常规合成"),
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

    def _well(self, plate_no, well_no, sample_name, **fields):
        self.db.add(SynthesisSupernatantWell(
            order_no="BAO9", corp_name="擎科", plate_no=plate_no, well_no=well_no, sample_name=sample_name,
            potency=fields.get("potency", Decimal("100.5000")), specs=fields.get("specs", Decimal("2")),
            volume=Decimal("20"), sample_enter_vol=Decimal("1.2500"),
        ))

    def test_plate_layout_exports_grid_like_company_coa(self):
        synthesis = self._synthesis(order_no="bao9", target_name="CLEC12A")
        self._well("P1", "A01", "Ab1")
        self._well("P1", "B01", "Ab2", potency=None, specs=None)
        self._well("P1", "H12", "Ab3")
        self._well("P2", "A01", "Ab4")
        self.db.add(SynthesisSupernatantWell(order_no="BAO9", corp_name="擎科", sample_name="Ab0", not_synthesized=True))
        self.db.commit()
        output, filename = order_files.export_plate_layout(self.db, synthesis.id)
        self.assertEqual(filename, "bao9孔板上清布局-CLEC12A.xlsx")
        book = load_workbook(BytesIO(output.getvalue()))
        grid, detail = book.worksheets
        self.assertEqual((grid.title, grid["A1"].value, grid["B1"].value), ("bao9布局表", "bao9", "CLEC12A"))
        self.assertEqual((grid["B3"].value, grid["A4"].value, grid["M4"].value), ("P1", "96孔板1", 12))
        self.assertEqual((grid["A5"].value, grid["B5"].value, grid["B6"].value, grid["M12"].value),
                         ("A", "Ab1", "Ab2", "Ab3"))
        self.assertIsNone(grid["A13"].value)
        self.assertEqual((grid["B14"].value, grid["A15"].value, grid["B16"].value), ("P2", "96孔板2", "Ab4"))
        self.assertEqual((grid["A25"].value, grid["B25"].value), ("未合成", "Ab0"))

        self.assertEqual([cell.value for cell in detail[1]][:3], ["板号", "孔号", "蛋白名称"])
        self.assertEqual([detail.cell(row, 3).value for row in range(2, 7)], ["Ab1", "Ab2", "Ab3", "Ab4", "Ab0"])
        self.assertEqual((detail["D2"].value, detail["D3"].value, detail["B6"].value), (100.5, None, "未合成"))

    def test_plate_layout_missing_messages_tell_why(self):
        empty = self._synthesis(synthesis_order_id="SYN-261123-EMPTY01", order_no="NONE")
        with self.assertRaisesRegex(NotFoundError, "还没收到"):
            order_files.export_plate_layout(self.db, empty.id)
        unsynth = self._synthesis(synthesis_order_id="SYN-261123-UNSYN01", order_no="BAO9")
        self.db.add(SynthesisSupernatantWell(order_no="BAO9", corp_name="擎科", sample_name="Ab0", not_synthesized=True))
        self.db.commit()
        with self.assertRaisesRegex(NotFoundError, "都没合成出来"):
            order_files.export_plate_layout(self.db, unsynth.id)

    def test_plate_layout_preview_lists_plates_and_reason(self):
        synthesis = self._synthesis(order_no="bao9", target_name="CLEC12A")
        empty = self._synthesis(synthesis_order_id="SYN-261123-EMPTY01", order_no="NONE")
        self._well("P2", "A01", "Ab4")
        self._well("P1", "B01", "Ab2", potency=None)
        self._well("P1", "A01", "Ab1")
        self.db.add(SynthesisSupernatantWell(order_no="BAO9", corp_name="擎科", sample_name="Ab0", not_synthesized=True))
        self.db.commit()
        preview = order_files.plate_layout_preview(self.db, synthesis.id)
        self.assertEqual((preview["order_no"], preview["target_name"], preview["message"]), ("bao9", "CLEC12A", ""))
        self.assertEqual([plate["plate_no"] for plate in preview["plates"]], ["P1", "P2"])
        self.assertEqual([well["sample_name"] for well in preview["plates"][0]["wells"]], ["Ab1", "Ab2"])
        self.assertIsNone(preview["plates"][0]["wells"][1]["potency"])
        self.assertEqual(preview["missing"], ["Ab0"])
        self.assertNotIn("corp_name", preview["plates"][0]["wells"][0])
        blank = order_files.plate_layout_preview(self.db, empty.id)
        self.assertEqual((blank["plates"], blank["message"]), ([], order_files.LAYOUT_MISSING))

    def test_plate_layout_query_follows_company_order_no_not_supply_mode(self):
        from modules.supernatant_receive import query

        engineering = self._synthesis(
            synthesis_order_id="SYN-261123-ENG0001",
            order_kind="改造",
            supply_mode="内部转染",
            order_no="CN2611180000772",
            synthetic_corp="君跻",
        )
        transfection = self._synthesis(
            synthesis_order_id="SYN-261123-TRF0001",
            supply_mode="内部转染",
            order_no="TRF-261123-ABC123",
        )
        with patch("modules.supernatant_receive.query.pull_order", return_value={"state": query.MISSING, "message": "还没发货"}) as pulled:
            result = order_files.query_plate_layout(self.db, engineering.id)
        pulled.assert_called_once_with(self.db, "君跻", "CN2611180000772")
        self.assertEqual(result["state"], query.MISSING)
        blocked = order_files.query_plate_layout(self.db, transfection.id)
        self.assertEqual(blocked["state"], query.UNSUPPORTED)
