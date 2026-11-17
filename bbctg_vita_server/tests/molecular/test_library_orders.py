"""覆盖文库工单、字段规则、流转、导出与路由权限。"""

import re
import unittest
from datetime import date, datetime
from unittest.mock import patch

from fastapi import HTTPException
from starlette.routing import compile_path

from api import api_routes
from core.errors import ConflictError, ForbiddenError, NotFoundError

from models.discovery import DiscoveryWorkbench
from models.molecular_cell import (
    MolecularLibraryOrder,
    MolecularLibraryResultFile,
    MolecularLibraryResultLink,
    MolecularLibraryResultPackage,
    MolecularPrimerIndexCatalog,
)
from modules.discovery.workbench import service as discovery_service
from modules.molecular_cell.library_orders import routes as order_routes
from modules.molecular_cell.library_orders import service
import modules.system.audit_middleware as audit_middleware
from modules.molecular_cell.library_orders.result_upload import assembled_primer
from modules.molecular_cell.permissions import LIBRARY_TYPE_PERMISSIONS
from modules.auth.permissions import UserContext
from modules.system.audit_context import AuditContext, reset_audit_context, set_audit_context
from support import DbTestCase


def _long_enough(sequence: str) -> bytes:
    if len(sequence) <= 400:
        sequence += "N" * (401 - len(sequence))
    return sequence.encode()


def _read(primer, direction="F"):
    return _long_enough(f"NN{assembled_primer(primer, direction)}NN")


LIBRARY_ID_RE = re.compile(r"^LIB-\d{6}-[A-Z0-9]{6}$")
TABLES = (
    DiscoveryWorkbench,
    MolecularLibraryOrder,
    MolecularPrimerIndexCatalog,
    MolecularLibraryResultPackage,
    MolecularLibraryResultFile,
    MolecularLibraryResultLink,
)


class LibraryOrderTests(DbTestCase):
    tables = TABLES

    def _discovery(self, **overrides):
        payload = {
            "project_code": "P1",
            "experiment_id": "E1",
            "target_name": "PD1",
            "target_codes": ["T1"],
            "study_type": "抗体发现",
            "pm": "张三",
            "mouse_strain_category": "RL-KO",
            "mouse_strain": "RN",
            "harvest_date": "2026-09-21",
            "positive_cell_count": "120",
            "screening_methods": "达普,噬菌体",
            "status": "待剖鼠",
            "priority": "加急",
            "owner": "发现员",
        }
        payload.update(overrides)
        return discovery_service.save(self.db, payload)

    def test_generate_library_order_id_format(self):
        value = service.generate_library_order_id(datetime(2026, 9, 21, 10, 0, 0))
        self.assertEqual(value[:11], "LIB-260921-")
        self.assertRegex(value, LIBRARY_ID_RE)

    def test_options_match_save_validation(self):
        service.save(self.db, {"build_type": service.BUILD_POOLED_BCR, "owner": " 王五 ", "pm": "张三"})
        service.save(self.db, {"build_type": service.BUILD_POOLED_BCR, "owner": "张三", "qc_owner": "李四"})
        options = service.get_options(self.db)
        self.assertEqual(options["statuses"], list(service.STATUS_OPTIONS))
        self.assertEqual(options["priorities"][0], "正常")
        self.assertEqual(options["qc_results"], list(service.QC_RESULT_OPTIONS))
        self.assertEqual(options["cell_types"], list(service.CELL_TYPE_OPTIONS))
        self.assertIn("RNVM", options["mouse_strains"])
        self.assertEqual(options["people"], sorted(["王五", "张三", "李四"]))

    def test_save_assigns_id_and_defaults(self):
        saved = service.save(
            self.db,
            {
                "build_type": service.BUILD_POOLED_BCR,
                "library_order_id": "LIB-260921-HACK01",
            },
        )
        self.assertRegex(saved["library_order_id"], LIBRARY_ID_RE)
        self.assertNotEqual(saved["library_order_id"], "LIB-260921-HACK01")
        self.assertEqual(saved["status"], service.STATUS_PENDING)
        self.assertEqual(saved["build_type"], service.BUILD_POOLED_BCR)

    def test_library_code_cannot_repeat(self):
        first = service.save(
            self.db,
            {"build_type": service.BUILD_POOLED_BCR, "library_code": "ce4689"},
        )
        self.assertEqual(first["library_code"], "CE4689")
        with self.assertRaisesRegex(ValueError, "建库编号 CE4689 已存在"):
            service.save(
                self.db,
                {"build_type": service.BUILD_PHAGE_DISPLAY, "library_code": "ce4689"},
            )
        service.save(self.db, {"id": first["id"], "library_code": "CE4689"})
        service.save(self.db, {"id": first["id"], "library_code": ""})
        second = service.save(
            self.db,
            {"build_type": service.BUILD_PHAGE_DISPLAY, "library_code": ""},
        )
        self.assertIsNone(second["library_code"])

    def test_list_is_newest_first_and_clamps_page(self):
        first = service.save(self.db, {"build_type": service.BUILD_POOLED_BCR, "library_code": "C1"})
        second = service.save(self.db, {"build_type": service.BUILD_POOLED_BCR, "library_code": "C2"})
        third = service.save(self.db, {"build_type": service.BUILD_POOLED_BCR, "library_code": "C3"})
        newest_first = service.get_list(self.db, {"page": 1, "limit": 2})
        self.assertEqual([item["id"] for item in newest_first["items"]], [third["id"], second["id"]])
        last_page = service.get_list(self.db, {"page": 99, "limit": 2})
        self.assertEqual(last_page["page"], 2)
        self.assertEqual([item["id"] for item in last_page["items"]], [first["id"]])

    def test_type_scope_limits_list_stats_values_and_export(self):
        from openpyxl import load_workbook

        service.save(self.db, {"build_type": service.BUILD_PLATE, "library_code": "P1"})
        service.save(self.db, {"build_type": service.BUILD_POOLED_BCR, "library_code": "B1"})
        plate_only = frozenset({service.BUILD_PLATE})

        listed = service.get_list(self.db, {}, plate_only)
        self.assertEqual([item["library_code"] for item in listed["items"]], ["P1"])
        self.assertEqual(listed["stats"][service.BUILD_PLATE], 1)
        self.assertEqual(listed["stats"][service.BUILD_POOLED_BCR], 0)
        self.assertEqual(service.get_list(self.db, {"build_type": service.BUILD_POOLED_BCR}, plate_only)["items"], [])
        values = service.get_column_values(self.db, {"field": "build_type"}, plate_only)["items"]
        self.assertEqual([item["value"] for item in values], [service.BUILD_PLATE])
        output, _ = service.export_list_workbook(self.db, {}, plate_only)
        rows = list(load_workbook(output, read_only=True).active.iter_rows(min_row=2, values_only=True))
        self.assertEqual(len(rows), 1)

        self.assertEqual(service.get_options(self.db, plate_only)["build_type_scope"], [service.BUILD_PLATE])
        self.assertIsNone(service.get_options(self.db)["build_type_scope"])
        self.assertEqual(len(service.get_list(self.db, {})["items"]), 2)

    def test_type_scope_limits_edits_to_scoped_types(self):
        plate = service.save(self.db, {"build_type": service.BUILD_PLATE, "library_code": "P1"})
        bcr = service.save(self.db, {"build_type": service.BUILD_POOLED_BCR, "library_code": "B1"})
        plate_only = frozenset({service.BUILD_PLATE})

        self.assertEqual(service.save(self.db, {"id": plate["id"], "owner": "王五"}, scope=plate_only)["owner"], "王五")
        created = service.save(self.db, {"build_type": service.BUILD_PLATE}, scope=plate_only)
        self.assertEqual(created["build_type"], service.BUILD_PLATE)
        with self.assertRaisesRegex(NotFoundError, service.MISSING_ROW):
            service.save(self.db, {"id": bcr["id"], "owner": "王五"}, scope=plate_only)
        self.db.rollback()
        with self.assertRaisesRegex(ForbiddenError, service.OUT_OF_SCOPE):
            service.save(self.db, {"build_type": service.BUILD_POOLED_BCR}, scope=plate_only)
        self.db.rollback()
        with self.assertRaisesRegex(ForbiddenError, service.OUT_OF_SCOPE):
            service.save(self.db, {"id": plate["id"], "build_type": service.BUILD_POOLED_BCR}, scope=plate_only)
        self.db.rollback()

        with self.assertRaisesRegex(NotFoundError, service.MISSING_ROW):
            service.batch_save(self.db, [{"id": plate["id"]}, {"id": bcr["id"]}], plate_only)
        self.db.rollback()
        with self.assertRaisesRegex(ForbiddenError, f"{plate['library_order_id']}：{service.OUT_OF_SCOPE}"):
            service.batch_save(self.db, [{"id": plate["id"], "build_type": service.BUILD_POOLED_BCR}], plate_only)
        self.db.rollback()

        with self.assertRaisesRegex(NotFoundError, service.MISSING_ROW):
            service.delete_order(self.db, bcr["id"], plate_only)
        service.delete_order(self.db, created["id"], plate_only)
        self.assertEqual(
            {(item["library_code"], item["build_type"], item["owner"]) for item in service.get_list(self.db, {})["items"]},
            {("P1", service.BUILD_PLATE, "王五"), ("B1", service.BUILD_POOLED_BCR, None)},
        )

    def test_type_scope_limits_handoff(self):
        row = self._discovery(
            screening_methods=",".join(
                (service.SCREENING_METHOD_BEACON, service.SCREENING_METHOD_DAPU, service.SCREENING_METHOD_PHAGE)
            )
        )
        service.handoff(self.db, {
            "discovery_workbench_id": row["id"],
            "items": [{"build_type": service.BUILD_POOLED_BCR, "sample_source": service.SOURCE_DAPU_TUBE}],
        })
        plate_only = frozenset({service.BUILD_PLATE})

        everything = service.list_by_discovery(self.db, discovery_workbench_id=row["id"])
        self.assertEqual(len(everything["items"]), 1)
        self.assertEqual(
            [item["build_type"] for item in everything["suggested_items"]],
            [service.BUILD_PLATE, service.BUILD_PHAGE_DISPLAY],
        )
        self.assertIsNone(everything["build_type_scope"])
        scoped = service.list_by_discovery(self.db, discovery_workbench_id=row["id"], scope=plate_only)
        self.assertEqual(scoped["items"], [])
        self.assertEqual([item["build_type"] for item in scoped["suggested_items"]], [service.BUILD_PLATE])
        self.assertEqual(scoped["build_type_scope"], [service.BUILD_PLATE])

        with self.assertRaisesRegex(ForbiddenError, service.OUT_OF_SCOPE):
            service.handoff(self.db, {
                "discovery_workbench_id": row["id"],
                "items": [{"build_type": service.BUILD_PHAGE_DISPLAY, "sample_source": service.SOURCE_DIRECT}],
            }, scope=plate_only)
        created = service.handoff(self.db, {
            "discovery_workbench_id": row["id"],
            "items": [{"build_type": service.BUILD_PLATE, "sample_source": service.SOURCE_BEACON_DAPU}],
        }, scope=plate_only)
        self.assertEqual([item["build_type"] for item in created["items"]], [service.BUILD_PLATE])

    def test_library_code_fill_rejects_a_code_used_by_another_order(self):
        service.save(self.db, {"build_type": service.BUILD_POOLED_BCR, "library_code": "C124"})
        target = service.save(self.db, {"build_type": service.BUILD_POOLED_BCR, "library_code": "C200"})
        with self.assertRaisesRegex(ValueError, "建库编号 C124 已存在"):
            service.batch_save(self.db, [
                {"id": target["id"], "library_code": "C124"},
            ])
        self.assertEqual(
            self.db.get(MolecularLibraryOrder, target["id"]).library_code,
            "C200",
        )

    def test_batch_save_can_swap_library_codes(self):
        first = service.save(self.db, {"build_type": service.BUILD_POOLED_BCR, "library_code": "C1"})
        second = service.save(self.db, {"build_type": service.BUILD_POOLED_BCR, "library_code": "C2"})
        saved = service.batch_save(self.db, [
            {"id": first["id"], "library_code": "C2"},
            {"id": second["id"], "library_code": "C1"},
        ])
        self.assertEqual([item["library_code"] for item in saved["items"]], ["C2", "C1"])

    def test_unique_key_catches_code_taken_after_the_check(self):
        service.save(self.db, {"build_type": service.BUILD_POOLED_BCR, "library_code": "C1"})
        target = service.save(self.db, {"build_type": service.BUILD_POOLED_BCR})
        with (
            patch.object(service, "_ensure_unique_library_codes"),
            self.assertRaisesRegex(ConflictError, service.LIBRARY_CODE_CONFLICT),
        ):
            service.save(self.db, {"id": target["id"], "library_code": "C1"})
        self.db.rollback()
        self.assertIsNone(self.db.get(MolecularLibraryOrder, target["id"]).library_code)

    def test_mouse_strain_input_is_normalized(self):
        saved = service.save(
            self.db,
            {"build_type": service.BUILD_POOLED_BCR, "mouse_strain": "RN、RLKO"},
        )
        self.assertEqual(saved["mouse_strain"], "RLKO、RN")
        custom = service.save(
            self.db,
            {"id": saved["id"], "mouse_strain": "自建品系、RL"},
        )
        self.assertEqual(custom["mouse_strain"], "RL、自建品系")
        pasted = service.save(
            self.db,
            {"id": saved["id"], "mouse_strain": "自建品系\nRL\tRN"},
        )
        self.assertEqual(pasted["mouse_strain"], "RL、RN、自建品系")

    def test_mouse_strain_sets_default_sample_type(self):
        cases = (
            ("RN", service.SAMPLE_NANO),
            ("RL", service.SAMPLE_LITE),
            ("RNVMKO", service.SAMPLE_NANO),
            ("RN、RLKO", service.SAMPLE_LITE),
            ("RMB/C", None),
        )
        for mouse_strain, expected in cases:
            with self.subTest(mouse_strain=mouse_strain):
                saved = service.save(
                    self.db,
                    {"build_type": service.BUILD_POOLED_BCR, "mouse_strain": mouse_strain},
                )
                self.assertEqual(saved["sample_type"], expected)

    def test_explicit_sample_type_overrides_strain_default(self):
        saved = service.save(
            self.db,
            {"build_type": service.BUILD_POOLED_BCR, "mouse_strain": "RNVM"},
        )
        manual = service.save(
            self.db,
            {"id": saved["id"], "sample_type": service.SAMPLE_RNVM_BLOOD},
        )
        self.assertEqual(manual["sample_type"], service.SAMPLE_RNVM_BLOOD)
        lite = service.save(self.db, {"id": saved["id"], "mouse_strain": "RL"})
        self.assertEqual(lite["sample_type"], service.SAMPLE_LITE)
        unmapped = service.save(self.db, {"id": saved["id"], "mouse_strain": "RM、RN"})
        self.assertEqual(unmapped["sample_type"], service.SAMPLE_LITE)
        typed = service.save(
            self.db,
            {"id": saved["id"], "sample_type": service.SAMPLE_PHAGE},
        )
        self.assertEqual(typed["sample_type"], service.SAMPLE_PHAGE)
        self.assertEqual(typed["mouse_strain"], "RM、RN")

    def test_experiment_type_is_phage_only(self):
        pooled = service.save(
            self.db,
            {
                "build_type": service.BUILD_POOLED_BCR,
                "source_experiment_type": "抗体发现",
            },
        )
        self.assertIsNone(pooled["source_experiment_type"])
        phage = service.save(
            self.db,
            {
                "build_type": service.BUILD_PHAGE_DISPLAY,
                "source_experiment_type": "亲和力改造",
            },
        )
        self.assertEqual(phage["source_experiment_type"], "亲和力改造")

    def test_notebook_is_shared_by_all_build_types(self):
        for build_type in service.BUILD_TYPE_ORDER:
            with self.subTest(build_type=build_type):
                saved = service.save(
                    self.db,
                    {
                        "build_type": build_type,
                        "notebook_no": f"NB-{build_type}",
                    },
                )
                self.assertEqual(saved["notebook_no"], f"NB-{build_type}")

        changed = service.save(
            self.db,
            {
                "build_type": service.BUILD_PHAGE_DISPLAY,
                "notebook_no": "NB-SHARED",
            },
        )
        changed = service.save(
            self.db,
            {"id": changed["id"], "build_type": service.BUILD_PLATE},
        )
        self.assertEqual(changed["notebook_no"], "NB-SHARED")

    def test_change_type_clears_profile_fields(self):
        saved = service.save(
            self.db,
            {
                "build_type": service.BUILD_PHAGE_DISPLAY,
                "sample_source": service.SOURCE_DIRECT,
                "initial_library_size": "3.1E+08",
                "effective_library_size": "2.4E+08",
            },
        )
        updated = service.save(
            self.db,
            {"id": saved["id"], "build_type": service.BUILD_POOLED_BCR},
        )
        self.assertEqual(updated["build_type"], service.BUILD_POOLED_BCR)
        self.assertIsNone(updated["initial_library_size"])
        self.assertIsNone(updated["effective_library_size"])
        self.assertIsNone(updated["sample_source"])

    def test_locations_and_qc_automatically_update_status(self):
        started = service.save(
            self.db,
            {"build_type": service.BUILD_PLATE, "cdna_location": "C-01"},
        )
        self.assertEqual(started["status"], service.STATUS_IN_PROGRESS)
        judged = service.save(
            self.db,
            {"build_type": service.BUILD_PHAGE_DISPLAY, "qc_result": "通过"},
        )
        self.assertEqual(judged["status"], service.STATUS_QC_PASS)
        finished = service.save(self.db, {"id": judged["id"], "library_location": "盒 A1"})
        self.assertEqual(finished["status"], service.STATUS_DONE)
        parked = service.save(
            self.db,
            {"build_type": service.BUILD_PHAGE_NGS, "library_location": "盒 B1"},
        )
        self.assertEqual(parked["status"], service.STATUS_PENDING)

    def test_status_can_be_set_explicitly(self):
        saved = service.save(self.db, {"build_type": service.BUILD_PLATE})
        held = service.save(self.db, {"id": saved["id"], "status": service.STATUS_PENDING})
        self.assertEqual(held["status"], service.STATUS_PENDING)
        jumped = service.save(self.db, {"id": saved["id"], "status": service.STATUS_DONE})
        self.assertEqual(jumped["status"], service.STATUS_DONE)

    def test_status_transitions_stamp_dates(self):
        clock = patch.object(service, "today_local", return_value=date(2026, 11, 17))
        clock.start()
        self.addCleanup(clock.stop)
        expected_date = "2026-11-17"
        started = service.save(
            self.db,
            {"build_type": service.BUILD_PLATE, "cdna_location": "C-01"},
        )
        self.assertEqual(started["started_at"], expected_date)
        self.assertIsNone(started["finished_at"])
        dated = service.save(self.db, {"id": started["id"], "started_at": "2020-01-01"})
        self.assertEqual(dated["started_at"], "2020-01-01")
        judged = service.save(
            self.db,
            {"build_type": service.BUILD_PHAGE_DISPLAY, "qc_result": "通过"},
        )
        self.assertIsNone(judged["started_at"])
        self.assertIsNone(judged["finished_at"])
        finished = service.save(self.db, {"id": judged["id"], "library_location": "盒 A1"})
        self.assertIsNone(finished["started_at"])
        self.assertEqual(finished["finished_at"], expected_date)
        parked = service.save(
            self.db,
            {"build_type": service.BUILD_PHAGE_NGS, "library_location": "盒 B1"},
        )
        self.assertIsNone(parked["started_at"])
        self.assertEqual(parked["finished_at"], expected_date)

    def test_date_filters_include_exact_start_and_finish_days(self):
        matched = service.save(
            self.db,
            {
                "build_type": service.BUILD_POOLED_BCR,
                "started_at": "2026-01-15",
                "finished_at": "2026-02-20",
            },
        )
        service.save(
            self.db,
            {
                "build_type": service.BUILD_POOLED_BCR,
                "started_at": "2026-01-16",
                "finished_at": "2026-02-21",
            },
        )
        for field, value in (("started_at", "2026-01-15"), ("finished_at", "2026-02-20")):
            with self.subTest(field=field):
                result = service.get_list(
                    self.db,
                    {
                        f"{field}_start": value,
                        f"{field}_end": value,
                        "page": 1,
                        "limit": 20,
                    },
                )
                self.assertEqual([item["id"] for item in result["items"]], [matched["id"]])

    def test_cannot_change_type_after_started(self):
        saved = service.save(self.db, {"build_type": service.BUILD_POOLED_BCR})
        service.save(self.db, {"id": saved["id"], "status": service.STATUS_IN_PROGRESS})
        with self.assertRaisesRegex(ValueError, "仅待处理"):
            service.save(
                self.db,
                {"id": saved["id"], "build_type": service.BUILD_PHAGE_DISPLAY},
            )

    def test_batch_save_updates_all_rows(self):
        first = service.save(self.db, {"build_type": service.BUILD_POOLED_BCR})
        second = service.save(self.db, {"build_type": service.BUILD_PHAGE_DISPLAY})
        result = service.batch_save(
            self.db,
            [
                {"id": first["id"], "remark": "甲", "library_order_id": "LIB-HACK"},
                {"id": second["id"], "remark": "乙"},
            ],
        )
        self.assertEqual([item["remark"] for item in result["items"]], ["甲", "乙"])
        self.assertEqual(result["items"][0]["library_order_id"], first["library_order_id"])

    def test_batch_save_rejects_whole_batch_when_one_row_fails(self):
        first = service.save(self.db, {"build_type": service.BUILD_POOLED_BCR})
        started = service.save(self.db, {"build_type": service.BUILD_POOLED_BCR})
        service.save(self.db, {"id": started["id"], "status": service.STATUS_IN_PROGRESS})
        with self.assertRaisesRegex(ValueError, f"{started['library_order_id']}：仅待处理"):
            service.batch_save(
                self.db,
                [
                    {"id": first["id"], "remark": "不应写入"},
                    {"id": started["id"], "build_type": service.BUILD_PHAGE_DISPLAY},
                ],
            )
        self.db.rollback()
        self.assertIsNone(self.db.get(MolecularLibraryOrder, first["id"]).remark)

    def test_batch_save_requires_unique_existing_ids(self):
        saved = service.save(self.db, {"build_type": service.BUILD_POOLED_BCR})
        with self.assertRaisesRegex(ValueError, "重复"):
            service.batch_save(self.db, [{"id": saved["id"]}, {"id": saved["id"]}])
        with self.assertRaisesRegex(ValueError, service.MISSING_ROW):
            service.batch_save(self.db, [{"id": saved["id"] + 100, "remark": "x"}])
        with self.assertRaisesRegex(ValueError, "ID"):
            service.batch_save(self.db, [{"remark": "x"}])

    def test_expected_conflict_detection_single_and_batch(self):

        first = service.save(
            self.db,
            {"build_type": service.BUILD_POOLED_BCR, "remark": "初版", "qc_on": "2026-03-17"},
        )
        second = service.save(
            self.db,
            {"build_type": service.BUILD_PHAGE_DISPLAY, "remark": "二号"},
        )

        with self.assertRaises(ConflictError):
            service.batch_save(
                self.db,
                [
                    {"id": first["id"], "remark": "不应写入", "_expected": {"remark": "初版"}},
                    {"id": second["id"], "remark": "新版", "_expected": {"remark": "过期"}},
                ],
            )
        self.db.rollback()
        self.assertEqual(self.db.get(MolecularLibraryOrder, first["id"]).remark, "初版")

        updated = service.batch_save(
            self.db,
            [
                {
                    "id": first["id"],
                    "remark": "已改",
                    "_expected": {
                        "remark": " 初版 ",
                        "qc_on": date(2026, 3, 17),
                        "library_order_id": "IGNORED",
                    },
                }
            ],
        )
        self.assertEqual(updated["items"][0]["remark"], "已改")

        with self.assertRaises(ConflictError):
            service.save(
                self.db,
                {"id": first["id"], "remark": "冲突", "_expected": {"remark": "过期"}},
            )
        self.db.rollback()
        plain = service.save(self.db, {"id": first["id"], "remark": "无基线覆盖"})
        self.assertEqual(plain["remark"], "无基线覆盖")


    def test_list_rows_round_trip_as_expected(self):
        service.save(
            self.db,
            {
                "build_type": service.BUILD_POOLED_BCR,
                "plate_nos": ["P2", "P1"],
                "qc_on": "2026/3/17",
                "remark": "第一行\n第二行",
            },
        )
        service.save(self.db, {"build_type": service.BUILD_PHAGE_DISPLAY})
        items = service.get_list(self.db, {})["items"]
        for item in items:
            saved = service.save(self.db, {"id": item["id"], "remark": "单条", "_expected": dict(item)})
            self.assertEqual(saved["remark"], "单条")
        items = service.get_list(self.db, {})["items"]
        saved = service.batch_save(
            self.db,
            [{"id": item["id"], "remark": "批量", "_expected": dict(item)} for item in items],
        )
        self.assertEqual([row["remark"] for row in saved["items"]], ["批量", "批量"])

    def test_export_workbook_contains_backend_headers_and_data(self):
        from openpyxl import load_workbook

        service.save(
            self.db,
            {"build_type": service.BUILD_POOLED_BCR, "library_code": "EXPORT-1", "owner": "张三"},
        )
        output, _ = service.export_list_workbook(self.db, {"library_code": "EXPORT-1"})
        sheet = load_workbook(output, read_only=True).active
        self.assertEqual(
            [cell.value for cell in next(sheet.iter_rows())],
            [label for label, _ in service.EXPORT_COLUMNS],
        )
        row = [cell.value for cell in next(sheet.iter_rows(min_row=2, max_row=2))]
        values = dict(zip((key for _, key in service.EXPORT_COLUMNS), row))
        self.assertEqual(values["library_code"], "EXPORT-1")
        self.assertEqual(values["owner"], "张三")

    def test_plate_numbers_are_unique(self):
        saved = service.save(
            self.db,
            {
                "build_type": service.BUILD_PLATE,
                "plate_nos": ["P01", "P02"],
            },
        )
        self.assertEqual(saved["plate_nos"], ["P01", "P02"])
        located = service.save(self.db, {"id": saved["id"], "cdna_location": "C-01"})
        self.assertEqual(located["cdna_location"], "C-01")
        updated = service.save(
            self.db,
            {"id": saved["id"], "plate_nos": ["P01", "P01", "P03"]},
        )
        self.assertEqual(updated["plate_nos"], ["P01", "P03"])

    def test_profile_rejects_wrong_route(self):
        with self.assertRaisesRegex(ValueError, "不匹配"):
            service.save(
                self.db,
                {
                    "build_type": service.BUILD_POOLED_BCR,
                    "sample_source": service.SOURCE_BEACON,
                },
            )

    def test_barcode_stays_only_on_profiles_that_record_it(self):
        saved = service.save(
            self.db,
            {
                "build_type": service.BUILD_PERIPHERAL_BLOOD,
                "index_mode": service.INDEX_DUAL,
                "i7_name": "UDP0205-R",
                "i7_sequence": "AGTCCGAGGA",
                "i5_name": "UDP0055V3-F",
                "i5_sequence": "TGCGCATAGC",
            },
        )
        pooled_barcode = service.save(
            self.db,
            {"id": saved["id"], "build_type": service.BUILD_POOLED_BARCODE},
        )
        self.assertEqual(pooled_barcode["index_mode"], service.INDEX_DUAL)
        self.assertEqual(pooled_barcode["i7_sequence"], "AGTCCGAGGA")
        self.assertEqual(pooled_barcode["i5_sequence"], "TGCGCATAGC")
        for build_type in (
            service.BUILD_PLATE,
            service.BUILD_POOLED_BCR,
            service.BUILD_PLASMA_NGS,
            service.BUILD_PHAGE_DISPLAY,
        ):
            with self.subTest(build_type=build_type):
                cleared = service.save(self.db, {"id": saved["id"], "build_type": build_type})
                self.assertIsNone(cleared["index_mode"])
                self.assertIsNone(cleared["i7_sequence"])
                self.assertIsNone(cleared["i5_sequence"])
                service.save(
                    self.db,
                    {
                        "id": saved["id"],
                        "build_type": service.BUILD_PERIPHERAL_BLOOD,
                        "index_mode": service.INDEX_DUAL,
                        "i7_name": "UDP0205-R",
                        "i7_sequence": "AGTCCGAGGA",
                        "i5_name": "UDP0055V3-F",
                        "i5_sequence": "TGCGCATAGC",
                    },
                )

    def test_phage_profiles_split_locations_and_barcode(self):
        display = service.save(
            self.db,
            {
                "build_type": service.BUILD_PHAGE_DISPLAY,
                "rna_location": "RNA-1",
                "cdna_location": "CDNA-1",
                "index_mode": service.INDEX_I7,
                "i7_name": "I7",
                "i7_sequence": "ACGT",
            },
        )
        self.assertEqual(display["rna_location"], "RNA-1")
        self.assertEqual(display["cdna_location"], "CDNA-1")
        self.assertIsNone(display["index_mode"])
        batched = service.save(
            self.db,
            {"id": display["id"], "library_batch_no": "PH-D-01"},
        )
        self.assertEqual(batched["library_batch_no"], "PH-D-01")
        ngs = service.save(
            self.db,
            {
                "build_type": service.BUILD_PHAGE_NGS,
                "rna_location": "RNA-2",
                "cdna_location": "CDNA-2",
                "library_location": "LIB-2",
                "index_mode": service.INDEX_I7,
                "i7_name": "I7",
                "i7_sequence": "ACGT",
            },
        )
        self.assertIsNone(ngs["rna_location"])
        self.assertIsNone(ngs["cdna_location"])
        self.assertEqual(ngs["library_location"], "LIB-2")
        self.assertEqual(ngs["i7_sequence"], "ACGT")

    def test_plasma_ngs_keeps_locations_and_only_nano_lite(self):
        saved = service.save(
            self.db,
            {
                "build_type": service.BUILD_PLASMA_NGS,
                "sample_source": service.SOURCE_SPLEEN,
                "sample_type": service.SAMPLE_NANO,
                "rna_location": "RNA-P",
                "cdna_location": "CDNA-P",
                "library_location": "LIB-P",
                "index_mode": service.INDEX_I7,
                "i7_name": "I7",
                "i7_sequence": "ACGT",
            },
        )
        self.assertEqual(saved["sample_type"], service.SAMPLE_NANO)
        self.assertEqual(saved["rna_location"], "RNA-P")
        self.assertEqual(saved["cdna_location"], "CDNA-P")
        self.assertEqual(saved["library_location"], "LIB-P")
        self.assertEqual(saved["cell_type"], "浆细胞")
        self.assertIsNone(saved["index_mode"])
        with self.assertRaisesRegex(ValueError, "Nano 或 Lite"):
            service.save(
                self.db,
                {
                    "build_type": service.BUILD_PLASMA_NGS,
                    "sample_type": service.SAMPLE_PHAGE,
                },
            )

    def test_plasma_stats_split_by_sample_type(self):
        service.save(
            self.db,
            {"build_type": service.BUILD_PLASMA_NGS, "sample_type": service.SAMPLE_NANO},
        )
        service.save(
            self.db,
            {"build_type": service.BUILD_PLASMA_NGS, "sample_type": service.SAMPLE_LITE},
        )
        service.save(
            self.db,
            {"build_type": service.BUILD_PLASMA_NGS, "sample_type": service.SAMPLE_LITE},
        )
        result = service.get_list(self.db, {"sample_type": service.SAMPLE_NANO})
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["stats"]["plasma_ngs:nano"], 1)
        self.assertEqual(result["stats"]["plasma_ngs:lite"], 2)
        self.assertEqual(result["stats"][service.BUILD_PLASMA_NGS], 3)

    def test_plasma_handoff_uses_requested_sample_type(self):
        row = self._discovery()
        result = service.handoff(
            self.db,
            {
                "discovery_workbench_id": row["id"],
                "items": [
                    {
                        "build_type": service.BUILD_PLASMA_NGS,
                        "sample_source": service.SOURCE_SPLEEN,
                        "sample_type": service.SAMPLE_LITE,
                    }
                ],
            },
        )
        item = result["items"][0]
        self.assertEqual(item["sample_type"], service.SAMPLE_LITE)
        self.assertEqual(item["instrument_on"], "2026-09-21")
        self.assertEqual(item["positive_cell_count"], "120")
        self.assertEqual(item["cell_type"], "浆细胞")

    def test_catalog_reference_copies_snapshot(self):
        catalog = MolecularPrimerIndexCatalog(
            name="UDP0205-R",
            family="UDP",
            direction="R",
            version="V1",
            short_sequence="AGTCCGAGGA",
            active=True,
        )
        self.db.add(catalog)
        self.db.commit()
        saved = service.save(
            self.db,
            {
                "build_type": service.BUILD_PHAGE_NGS,
                "index_mode": service.INDEX_I7,
                "i7_catalog_id": catalog.id,
            },
        )
        self.assertEqual(saved["i7_name"], "UDP0205-R")
        self.assertEqual(saved["i7_sequence"], "AGTCCGAGGA")

    def test_manual_catalog_name_clears_stale_reference_and_sequence(self):
        catalog = MolecularPrimerIndexCatalog(
            name="UDP0205-R",
            family="UDP",
            direction="R",
            short_sequence="AGTCCGAGGA",
            active=True,
        )
        self.db.add(catalog)
        self.db.commit()
        saved = service.save(
            self.db,
            {
                "build_type": service.BUILD_PHAGE_NGS,
                "index_mode": service.INDEX_I7,
                "i7_catalog_id": catalog.id,
            },
        )
        updated = service.save(
            self.db,
            {"id": saved["id"], "i7_name": "自定义引物"},
        )
        self.assertIsNone(updated["i7_catalog_id"])
        self.assertEqual(updated["i7_name"], "自定义引物")
        self.assertIsNone(updated["i7_sequence"])

    def test_clearing_catalog_id_clears_stale_snapshot(self):
        catalog = MolecularPrimerIndexCatalog(
            name="UDP0205-R",
            family="UDP",
            direction="R",
            short_sequence="AGTCCGAGGA",
            active=True,
        )
        self.db.add(catalog)
        self.db.commit()
        saved = service.save(
            self.db,
            {
                "build_type": service.BUILD_PHAGE_NGS,
                "index_mode": service.INDEX_I7,
                "i7_catalog_id": catalog.id,
            },
        )
        updated = service.save(
            self.db,
            {"id": saved["id"], "i7_catalog_id": None},
        )
        self.assertIsNone(updated["i7_catalog_id"])
        self.assertIsNone(updated["i7_name"])
        self.assertIsNone(updated["i7_sequence"])

    def test_clearing_barcode_mode_clears_index_values(self):
        saved = service.save(
            self.db,
            {
                "build_type": service.BUILD_PHAGE_NGS,
                "index_mode": service.INDEX_DUAL,
                "i7_name": "I7",
                "i7_sequence": "ACGT",
                "i5_name": "I5",
                "i5_sequence": "TGCA",
            },
        )
        updated = service.save(self.db, {"id": saved["id"], "index_mode": None})
        self.assertIsNone(updated["i7_name"])
        self.assertIsNone(updated["i7_sequence"])
        self.assertIsNone(updated["i5_name"])
        self.assertIsNone(updated["i5_sequence"])

    def test_primer_name_without_id_uses_the_active_catalog_row(self):
        catalog = MolecularPrimerIndexCatalog(
            name="UDP0055V3-F",
            family="UDP",
            direction="F",
            short_sequence="TGCGCATAGC",
            active=True,
        )
        self.db.add(catalog)
        self.db.commit()
        saved = service.save(
            self.db,
            {
                "build_type": service.BUILD_POOLED_BARCODE,
                "index_mode": service.INDEX_I5,
                "i5_name": "UDP0055V3-F",
            },
        )
        self.assertEqual(saved["i5_catalog_id"], catalog.id)
        self.assertEqual(saved["i5_name"], "UDP0055V3-F")
        self.assertEqual(saved["i5_sequence"], "TGCGCATAGC")
        pooled = service.save(
            self.db,
            {
                "build_type": service.BUILD_POOLED_BCR,
                "h_forward_primer_name": "UDP0055V3-F",
            },
        )
        self.assertEqual(pooled["h_forward_primer_id"], catalog.id)
        self.assertEqual(pooled["h_forward_primer_name"], "UDP0055V3-F")

    def test_concentrations_keep_experimentalist_text(self):
        saved = service.save(
            self.db,
            {
                "build_type": service.BUILD_POOLED_BCR,
                "cdna_concentration": "约12.5 ng/uL",
                "library_concentration": "ND",
                "h_primer_concentration": "10x",
            },
        )
        self.assertEqual(saved["cdna_concentration"], "约12.5 ng/uL")
        self.assertEqual(saved["library_concentration"], "ND")
        self.assertEqual(saved["h_primer_concentration"], "10x")

    def test_cell_count_and_fragment_keep_line_breaks(self):
        saved = service.save(
            self.db,
            {
                "build_type": service.BUILD_POOLED_BCR,
                "positive_cell_count": "约120\n>100",
                "fragment_size_bp": "450\n380",
            },
        )
        self.assertEqual(saved["positive_cell_count"], "约120\n>100")
        self.assertEqual(saved["fragment_size_bp"], "450\n380")
        with self.assertRaisesRegex(ValueError, "不能超过 64"):
            service.save(self.db, {"id": saved["id"], "fragment_size_bp": "1" * 65})
        long_count = "\n".join(f"达普打管-{i}：8.6E3" for i in range(1, 16))
        self.assertEqual(service.save(self.db, {"id": saved["id"], "positive_cell_count": long_count})["positive_cell_count"], long_count)
        with self.assertRaisesRegex(ValueError, "不能超过 255"):
            service.save(self.db, {"id": saved["id"], "positive_cell_count": "1" * 256})

    def test_target_forms_stay_a_single_choice(self):
        saved = service.save(self.db, {"build_type": service.BUILD_PHAGE_DISPLAY, "target_forms": "分泌"})
        self.assertEqual(saved["target_forms"], "分泌")
        with self.assertRaisesRegex(ValueError, "只能选一个"):
            service.save(self.db, {"id": saved["id"], "target_forms": ["分泌", "多穿"]})
        self.db.rollback()
        with self.assertRaisesRegex(ValueError, "靶点形式不在允许的选项中"):
            service.save(self.db, {"build_type": service.BUILD_PHAGE_DISPLAY, "target_forms": ["膜蛋白"]})

    def test_pooled_bcr_uses_forward_and_reverse_primer_pairs(self):
        forward = MolecularPrimerIndexCatalog(
            name="UDP0055V3-F",
            family="UDP",
            direction="F",
            short_sequence="TGCGCATAGC",
            active=True,
        )
        reverse = MolecularPrimerIndexCatalog(
            name="UDP0205-R",
            family="UDP",
            direction="R",
            short_sequence="AGTCCGAGGA",
            active=True,
        )
        self.db.add_all([forward, reverse])
        self.db.commit()
        saved = service.save(
            self.db,
            {
                "build_type": service.BUILD_POOLED_BCR,
                "cell_type": "浆细胞",
                "h_forward_primer_id": forward.id,
                "h_reverse_primer_id": reverse.id,
                "h_primer_concentration": "2.5",
            },
        )
        self.assertEqual(saved["h_forward_primer_name"], "UDP0055V3-F")
        self.assertEqual(saved["h_reverse_primer_name"], "UDP0205-R")
        self.assertEqual(saved["h_primer_concentration"], "2.5")

    def test_pooled_bcr_drops_cell_type_and_keeps_fragment_size(self):
        saved = service.save(
            self.db,
            {
                "build_type": service.BUILD_POOLED_BCR,
                "cell_type": "浆细胞",
                "fragment_size_bp": 450,
                "library_concentration": "12.5",
            },
        )
        self.assertIsNone(saved["cell_type"])
        self.assertEqual(saved["fragment_size_bp"], "450")
        self.assertEqual(saved["library_concentration"], "12.5")
        cleared = service.save(
            self.db,
            {"id": saved["id"], "build_type": service.BUILD_PLATE, "library_concentration": "1"},
        )
        self.assertIsNone(cleared["library_concentration"])

    def test_plasma_defaults_cell_type_and_rejects_unknown(self):
        saved = service.save(self.db, {"build_type": service.BUILD_PLASMA_NGS})
        self.assertEqual(saved["cell_type"], "浆细胞")
        with self.assertRaisesRegex(ValueError, "细胞类型"):
            service.save(
                self.db,
                {
                    "id": saved["id"],
                    "cell_type": "未知类型",
                },
            )

    def test_phage_display_cell_type_uses_the_three_options(self):
        saved = service.save(
            self.db,
            {"build_type": service.BUILD_PHAGE_DISPLAY, "cell_type": "全细胞"},
        )
        self.assertEqual(saved["cell_type"], "全细胞")
        cleared = service.save(self.db, {"id": saved["id"], "cell_type": ""})
        self.assertIsNone(cleared["cell_type"])
        with self.assertRaisesRegex(ValueError, "细胞类型"):
            service.save(self.db, {"id": saved["id"], "cell_type": "未知类型"})

    def test_handoff_requires_source_date_for_discovery_profiles(self):
        row = self._discovery(harvest_date="")
        with self.assertRaisesRegex(ValueError, "将作为上机日期"):
            service.handoff(
                self.db,
                {
                    "discovery_workbench_id": row["id"],
                    "items": [
                        {
                            "build_type": service.BUILD_POOLED_BCR,
                            "sample_source": service.SOURCE_DAPU_TUBE,
                        }
                    ],
                },
            )

    def test_handoff_requires_explicit_sample_source(self):
        row = self._discovery()
        with self.assertRaisesRegex(ValueError, "样品来源"):
            service.handoff(
                self.db,
                {
                    "discovery_workbench_id": row["id"],
                    "items": [{"build_type": service.BUILD_PLATE}],
                },
            )

    def test_normal_handoff_copies_snapshot_and_updates_status(self):
        row = self._discovery()
        result = service.handoff(
            self.db,
            {
                "discovery_workbench_id": row["id"],
                "items": [
                    {
                        "build_type": service.BUILD_POOLED_BCR,
                        "sample_source": service.SOURCE_DAPU_TUBE,
                    }
                ],
            },
        )
        item = result["items"][0]
        self.assertEqual(item["source_discovery_id"], row["discovery_id"])
        self.assertEqual(item["source_project_code"], "P1")
        self.assertEqual(item["study_type"], "抗体发现")
        self.assertEqual(item["mouse_strain"], "RN")
        self.assertEqual(item["sample_type"], service.SAMPLE_NANO)
        self.assertEqual(item["positive_cell_count"], "120")
        self.assertEqual(item["instrument_on"], "2026-09-21")
        self.assertIsNone(item["owner"])
        self.assertEqual(result["discovery_status"], service.DISCOVERY_WAIT_LIBRARY)

    def test_phage_display_handoff_updates_discovery_status(self):
        row = self._discovery()
        result = service.handoff(
            self.db,
            {
                "discovery_workbench_id": row["id"],
                "items": [
                    {
                        "build_type": service.BUILD_PHAGE_DISPLAY,
                        "sample_source": service.SOURCE_DIRECT,
                    }
                ],
            },
        )
        self.assertEqual(result["discovery_status"], service.DISCOVERY_WAIT_PHAGE)

    def test_plasma_direct_handoff_sets_sample_source_and_type(self):
        row = self._discovery()
        item = service.handoff(
            self.db,
            {
                "discovery_workbench_id": row["id"],
                "items": [
                    {
                        "build_type": service.BUILD_POOLED_BARCODE,
                        "sample_source": service.SOURCE_PLASMA_DIRECT,
                    }
                ],
            },
        )["items"][0]
        self.assertEqual(
            (item["sample_source"], item["sample_type"]),
            (service.SOURCE_PLASMA_DIRECT, service.SAMPLE_NANO),
        )

    def test_handoff_preserves_positive_cell_count_text(self):
        row = self._discovery(positive_cell_count="约120")
        result = service.handoff(
            self.db,
            {
                "discovery_workbench_id": row["id"],
                "items": [
                    {
                        "build_type": service.BUILD_POOLED_BCR,
                        "sample_source": service.SOURCE_DAPU_TUBE,
                    }
                ],
            },
        )
        self.assertEqual(result["items"][0]["positive_cell_count"], "约120")

    def test_handoff_does_not_change_wait_seq(self):
        row = self._discovery(status=service.DISCOVERY_WAIT_SEQ)
        result = service.handoff(
            self.db,
            {
                "discovery_workbench_id": row["id"],
                "items": [
                    {
                        "build_type": service.BUILD_POOLED_BCR,
                        "sample_source": service.SOURCE_DAPU_TUBE,
                    }
                ],
            },
        )
        self.assertEqual(result["discovery_status"], service.DISCOVERY_WAIT_SEQ)

    def test_repeat_handoff_same_type_allowed(self):
        row = self._discovery()
        payload = {
            "discovery_workbench_id": row["id"],
            "items": [
                {
                    "build_type": service.BUILD_POOLED_BCR,
                    "sample_source": service.SOURCE_DAPU_TUBE,
                }
            ],
        }
        first = service.handoff(self.db, payload)
        second = service.handoff(self.db, payload)
        self.assertNotEqual(first["items"][0]["id"], second["items"][0]["id"])

    def test_code_searches_stay_on_their_own_field(self):
        service.save(
            self.db,
            {
                "build_type": service.BUILD_PHAGE_NGS,
                "library_code": "C244",
                "source_project_code": "26D000001",
                "library_batch_no": "BATCH-1",
            },
        )
        service.save(
            self.db,
            {
                "build_type": service.BUILD_PHAGE_NGS,
                "library_code": "C245",
                "source_project_code": "26D000002",
                "library_batch_no": "BATCH-2",
            },
        )
        service.save(
            self.db,
            {
                "build_type": service.BUILD_PHAGE_NGS,
                "library_code": "C300",
                "source_project_code": "C244",
                "library_batch_no": "C245",
            },
        )
        service.save(
            self.db,
            {
                "build_type": service.BUILD_POOLED_BCR,
                "library_code": "C2440",
                "source_project_code": "26D000001-X",
            },
        )

        def codes(payload):
            result = service.get_list(self.db, payload)
            return {item["library_code"] for item in result["items"]}

        self.assertEqual(codes({"library_code": "C244, C245"}), {"C244", "C245"})
        self.assertEqual(codes({"library_code": "C244,"}), {"C244"})
        self.assertEqual(codes({"library_code": "c24"}), {"C244", "C245", "C2440"})
        self.assertEqual(
            codes({"source_project_code": "26D000001\n26D000002"}),
            {"C244", "C245"},
        )
        self.assertEqual(codes({"source_project_code": "C244"}), {"C300"})
        self.assertEqual(codes({"library_batch_no": "BATCH-1 BATCH-2"}), {"C244", "C245"})
        self.assertEqual(codes({"library_batch_no": "C245"}), {"C300"})
        with self.assertRaisesRegex(ValueError, "建库编号一次最多搜索"):
            service.get_list(self.db, {"library_code": ",".join(f"C{index}" for index in range(501))})

    def test_type_stats_match_filtered_list_including_cancelled(self):
        first = service.save(self.db, {"build_type": service.BUILD_POOLED_BCR})
        service.save(self.db, {"build_type": service.BUILD_POOLED_BCR})
        service.save(
            self.db,
            {"id": first["id"], "status": service.STATUS_CANCELLED},
        )
        result = service.get_list(
            self.db,
            {"build_type": service.BUILD_POOLED_BCR},
        )
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["stats"][service.BUILD_POOLED_BCR], 2)
        self.assertNotIn("all", result["stats"])

    def test_header_filter_values_and_sort(self):
        for code, owner in (("C1", "张三"), ("C2", "李四"), ("C3", None)):
            service.save(self.db, {"build_type": service.BUILD_POOLED_BCR, "library_code": code, "owner": owner})

        values = service.get_column_values(self.db, {"field": "owner"})["items"]
        self.assertEqual(sorted((item["value"], item["count"]) for item in values), [("", 1), ("张三", 1), ("李四", 1)])

        excluded = service.get_list(self.db, {"field_filters": [{"field": "owner", "exclude": [""]}]})
        self.assertEqual({item["library_code"] for item in excluded["items"]}, {"C1", "C2"})

        by_owner = service.get_list(self.db, {"sort_field": "owner", "sort_dir": "desc"})
        self.assertEqual([item["library_code"] for item in by_owner["items"]][-1], "C3")
        build_types = service.get_column_values(self.db, {"field": "build_type"})["items"]
        self.assertEqual(build_types, [{"value": service.BUILD_POOLED_BCR, "count": 3, "label": "混管 H/K/L"}])
        with self.assertRaisesRegex(ValueError, "不支持"):
            service.get_column_values(self.db, {"field": "target_codes"})

    def test_discovery_delete_protection(self):
        row = self._discovery()
        created = service.handoff(
            self.db,
            {
                "discovery_workbench_id": row["id"],
                "items": [
                    {
                        "build_type": service.BUILD_POOLED_BCR,
                        "sample_source": service.SOURCE_DAPU_TUBE,
                    }
                ],
            },
        )
        with self.assertRaisesRegex(ValueError, "建库工单"):
            discovery_service.delete(self.db, row["id"])
        service.save(
            self.db,
            {
                "id": created["items"][0]["id"],
                "status": service.STATUS_CANCELLED,
            },
        )
        with self.assertRaisesRegex(ValueError, "建库工单"):
            discovery_service.delete(self.db, row["id"])
        service.delete_order(self.db, created["items"][0]["id"])
        discovery_service.delete(self.db, row["id"])
        self.assertIsNone(self.db.get(DiscoveryWorkbench, row["id"]))




def _route_context(method: str, path: str) -> AuditContext:
    context = audit_middleware._build_context(method, path, {}, {"headers": []})
    for full_path, route in api_routes():
        if method in route.methods and compile_path(full_path)[0].match(path):
            audit_middleware.apply_route_audit(context, route)
            break
    return context


def _user(permissions, superuser=False) -> UserContext:
    return UserContext(id=1, username="u", display_name="u", roles=[], permissions=permissions, is_superuser=superuser)


class LibraryOrderRouteTests(unittest.TestCase):
    def test_type_permissions_map_to_build_types(self):
        self.assertTrue(set(LIBRARY_TYPE_PERMISSIONS.values()) <= set(service.BUILD_TYPE_ORDER))

    def test_type_scope_comes_from_type_permissions(self):
        plate = "molecular.library.type.plate_single_cell"
        self.assertIsNone(order_routes._type_scope(_user(["molecular.page.library", "molecular.library.edit"])))
        self.assertIsNone(order_routes._type_scope(_user([plate], superuser=True)))
        scoped = _user(["molecular.page.library", plate, "molecular.library.edit"])
        self.assertEqual(order_routes._type_scope(scoped), frozenset({service.BUILD_PLATE}))

    def test_every_library_route_applies_type_scope(self):
        def uses_scope(dependant) -> bool:
            return any(dep.call is order_routes._type_scope or uses_scope(dep) for dep in dependant.dependencies)

        routes = order_routes.router.routes
        self.assertTrue(routes)
        self.assertEqual([route.path for route in routes if not uses_scope(route.dependant)], [])

    def test_qc_expected_payload_uses_file_manage_permission(self):
        self.assertTrue(
            order_routes._is_qc_conclusion_only(
                {"id": 1, "qc_result": "通过", "_expected": {"qc_result": "待判定"}}
            )
        )

    def test_library_qc_conclusion_save_is_logged_as_qc_action(self):
        """有权限时按实际操作记录；拒绝日志也使用同一操作。"""
        for superuser in (True, False):
            user = UserContext(
                id=1, username="u", display_name="u", roles=[], permissions=[], is_superuser=superuser
            )
            for qc_only, code in ((True, "molecular.library.file.manage"), (False, "molecular.library.edit")):
                context = _route_context("POST", "/api/molecular-cell/library-orders/save")
                token = set_audit_context(context)
                try:
                    if superuser:
                        order_routes._require_save(user, qc_only)
                    else:
                        with self.assertRaises(HTTPException) as denied:
                            order_routes._require_save(user, qc_only)
                        self.assertEqual(denied.exception.status_code, 403)
                finally:
                    reset_audit_context(token)
                with self.subTest(superuser=superuser, qc_only=qc_only):
                    self.assertEqual([action.code for action in context.actions], [code])

