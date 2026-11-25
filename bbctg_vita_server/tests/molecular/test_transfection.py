"""转染与表达：工单状态、转染表导入规则、上下游交接。"""

import re
import unittest
from datetime import date
from unittest.mock import patch

from fastapi import HTTPException
from openpyxl import load_workbook

from core.errors import NotFoundError
from models.discovery import DiscoverySynthesisOrder
from models.molecular_cell import (
    MolecularLibraryOrder,
    MolecularLibraryResultFile,
    MolecularLibraryResultLink,
    MolecularLibraryResultPackage,
    MolecularPrimerIndexCatalog,
    MolecularTransfectionItem,
    MolecularTransfectionOrder,
    MolecularTransfectionProtein,
)
from models.supernatant import SynthesisSupernatantWell
from models.target import Target
from modules.auth.permissions import PermissionRequirement, UserContext
from modules.discovery.synthesis_progress import service as synthesis_service
from modules.molecular_cell.library_orders import service as library_service
from modules.molecular_cell.transfection import proteins, service
from modules.molecular_cell.transfection import routes as transfection_routes
from support import DbTestCase

ORDER_ID_RE = re.compile(r"^TRF-\d{6}-[A-Z0-9]{6}$")
TODAY = date(2026, 11, 17)


def _rows(*triples):
    return [
        {"row": index, "protein_name": name, "heavy_chain": heavy, "light_chain": light}
        for index, (name, heavy, light) in enumerate(triples, start=2)
    ]


class TransfectionTests(DbTestCase):
    tables = (
        Target,
        DiscoverySynthesisOrder,
        MolecularLibraryOrder,
        MolecularPrimerIndexCatalog,
        MolecularLibraryResultPackage,
        MolecularLibraryResultFile,
        MolecularLibraryResultLink,
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

    def _order(self, **fields):
        payload = {"transfection_type": service.TYPE_PLASMID, **fields}
        return service.save(self.db, payload, created_by="张三")

    def _history(self, name, heavy, light=None):
        self.db.add(MolecularTransfectionProtein(protein_name=name, heavy_chain=heavy, light_chain=light))
        self.db.commit()

    def _names(self, order_id):
        return [item["protein_name"] for item in proteins.order_proteins(self.db, order_id)["items"]]

    def _library(self, **fields):
        payload = {
            "build_type": library_service.BUILD_PLATE,
            "source_project_code": "P1",
            "study_type": "抗体发现",
            "target_name": "PD1",
            "target_codes": ["T1"],
            "pm": "李四",
            "mouse_strain": "RL",
            "plate_nos": ["B01", "B02"],
            "priority": "加急",
            **fields,
        }
        return library_service.save(self.db, payload)

    def _done_order(self, **fields):
        order = self._order(**{
            "project_code": "P9",
            "pm": "李四",
            "mouse_strain": "RN",
            "target_name": "PD1",
            "target_codes": ["T1"],
            "transfected_on": "2026-11-10",
            "finished_on": "2026-11-14",
            **fields,
        })
        proteins.import_proteins(self.db, order["id"], _rows(("A1", "H1", "L1"), ("A2", "H2", None)))
        return order

    def test_save_assigns_id_and_requires_type(self):
        saved = self._order(transfection_order_id="TRF-000000-HACK00")
        self.assertRegex(saved["transfection_order_id"], ORDER_ID_RE)
        self.assertEqual(saved["status"], service.STATUS_PENDING)
        self.assertEqual(saved["created_by"], "张三")
        self.assertEqual(saved["protein_count"], 0)
        self.assertIsNone(saved["synthesis_order_id"])
        with self.assertRaisesRegex(ValueError, "转染类型"):
            service.save(self.db, {})

    def test_status_follows_dates_and_explicit_status_fills_dates(self):
        order = self._order()
        saved = service.save(self.db, {"id": order["id"], "transfected_on": "2026-11-10"})
        self.assertEqual(saved["status"], service.STATUS_RUNNING)
        saved = service.save(self.db, {"id": order["id"], "status": service.STATUS_DONE})
        self.assertEqual((saved["status"], saved["finished_on"]), (service.STATUS_DONE, "2026-11-17"))
        saved = service.save(self.db, {"id": order["id"], "status": service.STATUS_RUNNING})
        self.assertEqual((saved["transfected_on"], saved["finished_on"]), ("2026-11-10", None))
        saved = service.save(self.db, {"id": order["id"], "status": service.STATUS_CANCELLED})
        self.assertEqual((saved["status"], saved["transfected_on"]), (service.STATUS_CANCELLED, "2026-11-10"))
        saved = service.save(self.db, {"id": order["id"], "finished_on": "2026-11-12"})
        self.assertEqual(saved["status"], service.STATUS_CANCELLED)
        saved = service.save(self.db, {"id": order["id"], "status": service.STATUS_PENDING})
        self.assertEqual(
            (saved["status"], saved["transfected_on"], saved["finished_on"]), (service.STATUS_PENDING, None, None)
        )
        with self.assertRaisesRegex(ValueError, "请先填写转染日期"):
            service.save(self.db, {"id": order["id"], "finished_on": "2026-11-12"})
        self.db.rollback()
        with self.assertRaisesRegex(ValueError, "完成日期不能早于转染日期"):
            service.save(self.db, {"id": order["id"], "transfected_on": "2026-11-12", "finished_on": "2026-11-11"})
        self.db.rollback()
        with self.assertRaisesRegex(ValueError, "请先填写转染日期"):
            service.save(self.db, {"id": order["id"], "status": service.STATUS_CANCELLED, "finished_on": "2026-11-12"})

    def test_import_registers_proteins_in_file_order(self):
        order = self._order()
        self._history("OLD1", "VH-OLD", "VK-OLD")
        result = proteins.import_proteins(
            self.db, order["id"], _rows(("B2", "H2", None), ("old1", "VH-OLD", "VK-OLD"), ("A1", "H1", "L1"))
        )
        self.assertEqual((result["total"], result["created"]), (3, 2))
        self.assertEqual(result["order"]["protein_count"], 3)
        listed = proteins.order_proteins(self.db, order["id"])["items"]
        self.assertEqual([item["protein_name"] for item in listed], ["B2", "OLD1", "A1"])
        self.assertEqual([item["registered_here"] for item in listed], [True, False, True])

    def test_import_rejects_whole_file_and_lists_every_problem(self):
        order = self._order()
        self._history("OLD1", "VH-OLD", None)
        with self.assertRaises(ValueError) as caught:
            proteins.import_proteins(
                self.db,
                order["id"],
                _rows(
                    ("A1", "H1", None),
                    ("a1", "H9", None),
                    ("", "H3", None),
                    ("A4", "", None),
                    ("OLD1", "VH-OLD", "VK-NEW"),
                    ("A6", "H" * 129, None),
                ),
            )
        message = str(caught.exception)
        self.assertTrue(message.startswith("文件有 5 处问题，整个文件未导入"))
        for line in (
            "第 3 行：蛋白名称 a1 与第 2 行重复",
            "第 4 行：缺少蛋白名称",
            "第 5 行：缺少重链",
            "第 6 行：OLD1 已登记为 重链 VH-OLD、轻链 无，与文件不一致",
            "第 7 行：重链不能超过 128 个字符",
        ):
            self.assertIn(line, message)
        self.db.rollback()
        self.assertEqual(self._names(order["id"]), [])
        self.assertEqual(proteins.list_proteins(self.db)["total"], 1)

    def test_reimport_overwrites_and_drops_only_own_unshared_proteins(self):
        first = self._order()
        second = self._order()
        self._history("OLD1", "VH-OLD")
        proteins.import_proteins(
            self.db, first["id"], _rows(("A1", "H1", None), ("A2", "H2", None), ("A3", "H3", None), ("OLD1", "VH-OLD", None))
        )
        proteins.import_proteins(self.db, second["id"], _rows(("A3", "H3", None)))

        result = proteins.import_proteins(self.db, first["id"], _rows(("A1", "H1-NEW", "L1")))
        self.assertEqual((result["updated"], result["removed"]), (1, 1))
        library = {item["protein_name"]: item for item in proteins.list_proteins(self.db)["items"]}
        self.assertEqual(sorted(library), ["A1", "A3", "OLD1"])
        self.assertEqual((library["A1"]["heavy_chain"], library["A1"]["light_chain"]), ("H1-NEW", "L1"))
        self.assertEqual(library["A3"]["source_order"], first["transfection_order_id"])

        with self.assertRaisesRegex(ValueError, "A3 已登记为 重链 H3"):
            proteins.import_proteins(self.db, first["id"], _rows(("A3", "H3-NEW", None)))

    def test_clear_drops_only_own_unshared_proteins(self):
        first = self._order()
        second = self._order()
        self._history("OLD1", "VH-OLD")
        proteins.import_proteins(
            self.db, first["id"], _rows(("A1", "H1", None), ("A2", "H2", None), ("OLD1", "VH-OLD", None))
        )
        proteins.import_proteins(self.db, second["id"], _rows(("A2", "H2", None)))

        result = proteins.clear_proteins(self.db, first["id"])
        self.assertEqual((result["total"], result["removed"], result["order"]["protein_count"]), (3, 1, 0))
        self.assertEqual(self._names(first["id"]), [])
        self.assertEqual(sorted(item["protein_name"] for item in proteins.list_proteins(self.db)["items"]), ["A2", "OLD1"])
        with self.assertRaisesRegex(ValueError, "本单还没有蛋白"):
            proteins.clear_proteins(self.db, first["id"])

    def test_order_export_uses_import_format(self):
        order = self._order()
        proteins.import_proteins(self.db, order["id"], _rows(("B2", "H2", None), ("A1", "H1", "L1")))
        output, filename = proteins.export_order_proteins(self.db, order["id"])
        self.assertTrue(filename.startswith(f"转染蛋白_{order['transfection_order_id']}_"))
        sheet = load_workbook(output).active
        self.assertEqual(
            [[cell or "" for cell in row] for row in sheet.iter_rows(values_only=True)],
            [["抗体名称", "重链名称", "轻链名称"], ["B2", "H2", ""], ["A1", "H1", "L1"]],
        )

    def test_delete_keeps_proteins_other_orders_still_use(self):
        first = self._order()
        second = self._order()
        proteins.import_proteins(self.db, first["id"], _rows(("A1", "H1", None), ("A2", "H2", None)))
        proteins.import_proteins(self.db, second["id"], _rows(("A2", "H2", None)))
        service.delete_order(self.db, first["id"])
        listed = proteins.list_proteins(self.db)
        self.assertEqual([item["protein_name"] for item in listed["items"]], ["A2"])
        self.assertIsNone(listed["items"][0]["source_order"])
        self.assertEqual(listed["stats"], {"total": 1, proteins.SOURCE_ORDER: 0, proteins.SOURCE_HISTORY: 1})
        self.assertEqual(self._names(second["id"]), ["A2"])

    def test_protein_query_shows_using_orders_and_filters_by_order(self):
        first = self._order()
        second = self._order()
        self._history("OLD1", "VH-OLD")
        proteins.import_proteins(self.db, first["id"], _rows(("A1", "H1", None), ("OLD1", "VH-OLD", None)))
        proteins.import_proteins(self.db, second["id"], _rows(("A1", "H1", None)))

        listed = proteins.list_proteins(self.db)
        self.assertEqual(listed["stats"], {"total": 2, proteins.SOURCE_ORDER: 1, proteins.SOURCE_HISTORY: 1})
        by_name = {item["protein_name"]: item for item in listed["items"]}
        self.assertEqual(by_name["A1"]["orders"], [first["transfection_order_id"], second["transfection_order_id"]])
        history = proteins.list_proteins(self.db, {"source": proteins.SOURCE_HISTORY})
        self.assertEqual([item["protein_name"] for item in history["items"]], ["OLD1"])
        self.assertEqual(history["stats"]["total"], 2)
        by_order = proteins.list_proteins(self.db, {"order_code": second["transfection_order_id"].lower()})
        self.assertEqual([item["protein_name"] for item in by_order["items"]], ["A1"])
        found = service.get_list(self.db, {"protein_name": "OLD"})
        self.assertEqual([item["id"] for item in found["items"]], [first["id"]])

        output, _ = proteins.export_workbook(self.db, {"protein_name": "A1"})
        rows = list(load_workbook(output, read_only=True).active.iter_rows(values_only=True))
        self.assertEqual(rows[0], proteins.EXPORT_HEADERS)
        self.assertEqual(rows[1][:8], ("A1", "H1", None, None, None, None, first["transfection_order_id"],
                                       f"{first['transfection_order_id']}、{second['transfection_order_id']}"))

    def _target(self, external_id, snum, name):
        self.db.add(Target(external_id=external_id, snum=snum, name=name))
        self.db.commit()

    def _protein(self, name):
        return next(item for item in proteins.list_proteins(self.db)["items"] if item["protein_name"] == name)

    def test_protein_targets_follow_first_filled_order(self):
        self._target(1, "T1", "PD-1")
        self._target(2, "T2", "CTLA4")
        first = self._order()
        second = self._order(target_name="PDCD1", target_codes=["T1"], mouse_strain="RL")
        self._history("OLD1", "VH-OLD")
        proteins.import_proteins(self.db, first["id"], _rows(("A1", "H1", None), ("OLD1", "VH-OLD", None)))
        self.assertEqual(
            {key: self._protein("A1")[key] for key in service.PROTEIN_SYNC_FIELDS},
            {"target_name": None, "target_codes": [], "mouse_strain": None},
        )

        proteins.import_proteins(self.db, second["id"], _rows(("A1", "H1", None)))
        a1 = self._protein("A1")
        self.assertEqual((a1["target_name"], a1["target_codes"], a1["mouse_strain"]), ("PD-1", ["T1"], "RL"))

        service.save(self.db, {"id": first["id"], "target_name": "双抗", "target_codes": ["T1", "T2"]})
        a1 = self._protein("A1")
        self.assertEqual((a1["target_name"], a1["target_codes"], a1["mouse_strain"]), ("PD-1&CTLA4", ["T1", "T2"], "RL"))
        self.assertEqual(self._protein("OLD1")["target_codes"], ["T1", "T2"])

        service.batch_save(self.db, [{"id": first["id"], "target_name": "新靶点", "target_codes": [], "mouse_strain": "RN"}])
        a1 = self._protein("A1")
        self.assertEqual((a1["target_name"], a1["target_codes"], a1["mouse_strain"]), ("新靶点", [], "RN"))

        service.delete_order(self.db, first["id"])
        a1 = self._protein("A1")
        self.assertEqual((a1["target_name"], a1["target_codes"], a1["mouse_strain"]), ("PD-1", ["T1"], "RL"))
        filtered = proteins.list_proteins(self.db, {"field_filters": [{"field": "target_name", "values": ["PD-1"]}]})
        self.assertEqual([item["protein_name"] for item in filtered["items"]], ["A1"])

    def test_list_stats_by_status_ignore_status_filter(self):
        self._order()
        self._order(transfected_on="2026-11-10")
        listed = service.get_list(self.db, {"status": service.STATUS_RUNNING})
        self.assertEqual(listed["total"], 1)
        self.assertEqual(listed["stats"][service.STATUS_PENDING], 1)
        self.assertEqual(listed["stats"][service.STATUS_RUNNING], 1)

    def test_library_plate_order_hands_off_once(self):
        library = self._library()
        created = service.handoff_from_library(self.db, library["id"], created_by="王五")
        self.assertEqual(created["transfection_type"], service.TYPE_PCR)
        self.assertEqual(created["source_library_order_id"], library["library_order_id"])
        self.assertEqual(
            (created["project_code"], created["study_type"], created["pm"], created["mouse_strain"], created["priority"]),
            ("P1", "抗体发现", "李四", "RL", "加急"),
        )
        self.assertEqual(
            (created["target_name"], created["target_codes"], created["plate_nos"]),
            ("PD1", ["T1"], ["B01", "B02"]),
        )
        with self.assertRaisesRegex(ValueError, f"已交接为转染工单 {created['transfection_order_id']}"):
            service.handoff_from_library(self.db, library["id"])
        with self.assertRaisesRegex(ValueError, f"已交接为转染工单 {created['transfection_order_id']}，不能删除"):
            library_service.delete_order(self.db, library["id"])

    def test_library_handoff_only_takes_live_plate_orders_in_scope(self):
        pooled = self._library(build_type=library_service.BUILD_POOLED_BCR, plate_nos=[])
        with self.assertRaisesRegex(ValueError, "只有单细胞孔板"):
            service.handoff_from_library(self.db, pooled["id"])
        cancelled = self._library(status=library_service.STATUS_CANCELLED)
        with self.assertRaisesRegex(ValueError, "已取消"):
            service.handoff_from_library(self.db, cancelled["id"])
        with self.assertRaises(NotFoundError):
            service.handoff_from_library(self.db, pooled["id"], scope=frozenset({library_service.BUILD_PLATE}))

    def test_synthesis_handoff_creates_internal_row_waiting_for_assay(self):
        order = self._done_order(study_type="抗体发现", priority="加急")
        result = service.handoff_to_synthesis(self.db, order["id"], created_by="王五")
        synthesis = self.db.query(DiscoverySynthesisOrder).one()
        self.assertEqual(result["synthesis_order_id"], synthesis.synthesis_order_id)
        self.assertEqual(result["order"]["synthesis_order_id"], synthesis.synthesis_order_id)
        self.assertEqual(synthesis.order_no, order["transfection_order_id"])
        self.assertEqual(
            (synthesis.order_kind, synthesis.supply_mode, synthesis.status, synthesis.synthetic_corp),
            ("常规合成", "内部转染", "待检测", "内部"),
        )
        self.assertEqual((synthesis.synthetic_count, synthesis.arrival_count), (2, 2))
        self.assertEqual((str(synthesis.synthetic_date), str(synthesis.arrival_date)), ("2026-11-10", "2026-11-14"))
        self.assertEqual(
            (synthesis.project_code, synthesis.study_type, synthesis.pm, synthesis.mouse_strain, synthesis.priority),
            ("P9", "抗体发现", "李四", "RN", "加急"),
        )
        self.assertEqual((synthesis.target_name, synthesis.target_codes), ("PD1", ["T1"]))

        with self.assertRaisesRegex(ValueError, f"已交接到合成与验证 {synthesis.synthesis_order_id}"):
            service.handoff_to_synthesis(self.db, order["id"])
        self.db.rollback()
        with self.assertRaisesRegex(ValueError, "不能再改状态"):
            service.save(self.db, {"id": order["id"], "status": service.STATUS_CANCELLED})
        self.db.rollback()
        with self.assertRaisesRegex(ValueError, "不能再改完成日期"):
            service.batch_save(self.db, [{"id": order["id"], "finished_on": "2026-11-15"}])
        self.db.rollback()
        self.assertEqual(service.save(self.db, {"id": order["id"], "remark": "已送检"})["remark"], "已送检")
        with self.assertRaisesRegex(ValueError, "蛋白清单不能再改"):
            proteins.import_proteins(self.db, order["id"], _rows(("A1", "H1", "L1")))
        self.db.rollback()
        with self.assertRaisesRegex(ValueError, "蛋白清单不能再改"):
            proteins.clear_proteins(self.db, order["id"])
        self.db.rollback()
        with self.assertRaisesRegex(ValueError, "不能删除"):
            service.delete_order(self.db, order["id"])

    def test_synthesis_order_no_from_transfection_is_handoff_only(self):
        order = self._done_order()
        synthesis_id = service.handoff_to_synthesis(self.db, order["id"])["synthesis_order_id"]
        synthesis = self.db.query(DiscoverySynthesisOrder).one()
        for value in ("CN001", ""):
            with self.assertRaisesRegex(ValueError, "转染工单号，不能修改"):
                synthesis_service.save(self.db, {"id": synthesis.id, "order_no": value})
            self.db.rollback()
        with self.assertRaisesRegex(ValueError, "只能由转染与表达交接写入"):
            synthesis_service.save(self.db, {"order_kind": "常规合成", "order_no": "trf-261117-abcdef"})
        self.db.rollback()
        self.assertEqual(synthesis_service.save(self.db, {"id": synthesis.id, "remark": "已送检"})["remark"], "已送检")

        self.db.delete(self.db.get(DiscoverySynthesisOrder, synthesis.id))
        self.db.commit()
        self.assertIsNone(service.get_list(self.db, {})["items"][0]["synthesis_order_id"])
        self.assertNotEqual(service.handoff_to_synthesis(self.db, order["id"])["synthesis_order_id"], synthesis_id)

    def test_synthesis_handoff_needs_finished_order_with_proteins_and_required_fields(self):
        pending = self._order(pm="李四", mouse_strain="RN", target_name="PD1")
        with self.assertRaisesRegex(ValueError, "只有已完成"):
            service.handoff_to_synthesis(self.db, pending["id"])
        self.db.rollback()
        empty = self._order(
            pm="李四", mouse_strain="RN", target_name="PD1", transfected_on="2026-11-10", finished_on="2026-11-11"
        )
        with self.assertRaisesRegex(ValueError, "请先导入转染蛋白"):
            service.handoff_to_synthesis(self.db, empty["id"])
        self.db.rollback()
        missing = self._done_order(pm="", mouse_strain="")
        with self.assertRaisesRegex(ValueError, "请先填写必填项：小鼠品系、PM"):
            service.handoff_to_synthesis(self.db, missing["id"])
        self.db.rollback()
        self.assertEqual(self.db.query(DiscoverySynthesisOrder).count(), 0)


def _user(permissions, superuser=False) -> UserContext:
    return UserContext(id=1, username="u", display_name="u", roles=[], permissions=permissions, is_superuser=superuser)


class TransfectionRouteTests(unittest.TestCase):
    def _requirement(self, path):
        route = next(route for route in transfection_routes.router.routes if route.path == path)
        return next(dep.dependency for dep in route.dependencies if isinstance(dep.dependency, PermissionRequirement))

    def test_library_editor_can_hand_off_within_library_type_scope(self):
        requirement = self._requirement("/handoff_library")
        requirement(_user(["molecular.library.edit"]))
        requirement(_user(["molecular.transfection.edit"]))
        with self.assertRaises(HTTPException):
            requirement(_user(["molecular.page.library", "molecular.page.transfection"]))
        plate = "molecular.library.type.plate_single_cell"
        self.assertEqual(
            transfection_routes._library_scope(_user(["molecular.library.edit", plate])),
            frozenset({library_service.BUILD_PLATE}),
        )
        self.assertIsNone(transfection_routes._library_scope(_user(["molecular.library.edit"])))

    def test_protein_import_and_remove_need_transfection_edit(self):
        for path in ("/proteins/import", "/proteins/clear"):
            requirement = self._requirement(path)
            with self.assertRaises(HTTPException):
                requirement(_user(["molecular.page.transfection", "molecular.library.edit"]))
