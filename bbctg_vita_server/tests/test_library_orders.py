import io
import hashlib
import re
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from fastapi import UploadFile
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

from db.session import Base
from models.discovery import DiscoveryWorkbench
from models.molecular_cell import (
    MolecularLibraryOrder,
    MolecularLibraryResultFile,
    MolecularLibraryResultLink,
    MolecularPrimerIndexCatalog,
)
from modules.discovery.workbench import service as discovery_service
from modules.molecular_cell.library_orders import service


@compiles(BigInteger, "sqlite")
def _compile_big_integer_for_sqlite(_type, _compiler, **_kwargs):
    return "INTEGER"


LIBRARY_ID_RE = re.compile(r"^LIB-\d{6}-[A-Z0-9]{6}$")
TABLES = [
    DiscoveryWorkbench.__table__,
    MolecularLibraryOrder.__table__,
    MolecularPrimerIndexCatalog.__table__,
    MolecularLibraryResultFile.__table__,
    MolecularLibraryResultLink.__table__,
]


class LibraryOrderTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine, tables=TABLES)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _discovery(self, **overrides):
        payload = {
            "project_code": "P1",
            "experiment_id": "E1",
            "target_name": "PD1",
            "target_codes": ["T1"],
            "study_type": "抗体发现",
            "pm": "张三",
            "mouse_strain_category": "RN",
            "mouse_strain": "BALB/c",
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

    def test_library_code_can_repeat(self):
        first = service.save(
            self.db,
            {"build_type": service.BUILD_POOLED_BCR, "library_code": "ce4689"},
        )
        second = service.save(
            self.db,
            {"build_type": service.BUILD_PHAGE_DISPLAY, "library_code": "ce4689"},
        )
        self.assertEqual(first["library_code"], "CE4689")
        self.assertEqual(second["library_code"], "CE4689")
        self.assertNotEqual(first["id"], second["id"])

    def test_sample_type_is_only_auto_mapped_for_rn_and_rl(self):
        saved = service.save(
            self.db,
            {"build_type": service.BUILD_POOLED_BCR, "mouse_model": "RN"},
        )
        self.assertEqual(saved["sample_type"], service.SAMPLE_NANO)
        updated = service.save(self.db, {"id": saved["id"], "mouse_model": "RL"})
        self.assertEqual(updated["sample_type"], service.SAMPLE_LITE)
        manual = service.save(
            self.db,
            {
                "id": saved["id"],
                "mouse_model": "RN-VM",
                "sample_type": service.SAMPLE_RNVM_BLOOD,
            },
        )
        self.assertEqual(manual["sample_type"], service.SAMPLE_RNVM_BLOOD)
        first_of_many = service.save(
            self.db,
            {"id": saved["id"], "mouse_model": "RL-KO，RN-KO"},
        )
        self.assertEqual(first_of_many["sample_type"], service.SAMPLE_LITE)
        unmapped_first = service.save(
            self.db,
            {"id": saved["id"], "mouse_model": "RM、RN"},
        )
        self.assertEqual(unmapped_first["sample_type"], service.SAMPLE_LITE)
        typed = service.save(
            self.db,
            {"id": saved["id"], "sample_type": service.SAMPLE_PHAGE},
        )
        self.assertEqual(typed["sample_type"], service.SAMPLE_PHAGE)
        self.assertEqual(typed["mouse_model"], "RM、RN")

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

    def test_export_headers_match_excel_view_labels(self):
        columns_js = (
            Path(__file__).resolve().parents[2]
            / "bbctg_vita_web/apps/antibody_vita/src/views/MolecularCell/library/libraryColumns.js"
        )
        sheet_labels = dict(
            re.findall(r"def\('(\w+)',\s*'([^']+)'", columns_js.read_text(encoding="utf-8"))
        )
        self.assertEqual(set(sheet_labels), {key for _, key in service.EXPORT_COLUMNS})
        for label, key in service.EXPORT_COLUMNS:
            self.assertEqual(sheet_labels.get(key), label, key)

    def test_plate_numbers_are_unique(self):
        saved = service.save(
            self.db,
            {
                "build_type": service.BUILD_PLATE,
                "plate_nos": ["P01", "P02"],
            },
        )
        self.assertEqual(saved["plate_nos"], ["P01", "P02"])
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

    def test_barcode_is_available_on_all_profiles_except_pooled_bcr(self):
        saved = service.save(
            self.db,
            {
                "build_type": service.BUILD_PLATE,
                "index_mode": service.INDEX_DUAL,
                "i7_name": "UDP0205-R",
                "i7_sequence": "AGTCCGAGGA",
                "i5_name": "UDP0055V3-F",
                "i5_sequence": "TGCGCATAGC",
            },
        )
        changed = service.save(
            self.db,
            {"id": saved["id"], "build_type": service.BUILD_PHAGE_DISPLAY},
        )
        self.assertEqual(changed["index_mode"], service.INDEX_DUAL)
        self.assertEqual(changed["i7_sequence"], "AGTCCGAGGA")
        self.assertEqual(changed["i5_sequence"], "TGCGCATAGC")
        pooled = service.save(
            self.db,
            {"id": saved["id"], "build_type": service.BUILD_POOLED_BCR},
        )
        self.assertIsNone(pooled["index_mode"])
        self.assertIsNone(pooled["i7_sequence"])
        self.assertIsNone(pooled["i5_sequence"])

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

    def test_decimal_zero_is_serialized_as_zero(self):
        saved = service.save(
            self.db,
            {
                "build_type": service.BUILD_POOLED_BCR,
                "cdna_concentration": "0",
            },
        )
        self.assertEqual(saved["cdna_concentration"], "0")

    def test_numeric_fields_reject_non_finite_values(self):
        for field in ("cdna_concentration", "fragment_size_bp"):
            for value in ("NaN", "Infinity"):
                with self.subTest(field=field, value=value):
                    with self.assertRaisesRegex(ValueError, "必须是非负"):
                        service.save(
                            self.db,
                            {
                                "build_type": service.BUILD_PERIPHERAL_BLOOD,
                                field: value,
                            },
                        )
                    self.db.rollback()

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

    def test_pooled_bcr_rejects_unknown_cell_type(self):
        with self.assertRaisesRegex(ValueError, "细胞类型"):
            service.save(
                self.db,
                {
                    "build_type": service.BUILD_POOLED_BCR,
                    "cell_type": "未知类型",
                },
            )

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

    def test_handoff_snapshot_and_status(self):
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
        self.assertEqual(item["mouse_model"], "RN")
        self.assertEqual(item["sample_type"], service.SAMPLE_NANO)
        self.assertEqual(item["positive_cell_count"], "120")
        self.assertEqual(item["instrument_on"], "2026-09-21")
        self.assertIsNone(item["owner"])
        self.assertEqual(result["discovery_status"], service.DISCOVERY_WAIT_LIBRARY)

        phage = service.handoff(
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
        self.assertEqual(phage["discovery_status"], service.DISCOVERY_WAIT_PHAGE)

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


class LibraryFileTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine, tables=TABLES)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)
        self.db = self.Session()
        self.tmpdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmpdir.name)
        self.settings_patch = patch(
            "modules.molecular_cell.library_orders.service.get_settings",
            return_value=type("S", (), {"repository_root": self.repo})(),
        )
        self.drm_patch = patch(
            "modules.molecular_cell.library_orders.service.drm_service.decrypt_upload_file_if_available"
        )
        self.settings_patch.start()
        self.drm_mock = self.drm_patch.start()
        self.order = service.save(
            self.db,
            {"build_type": service.BUILD_POOLED_BCR, "library_code": "CE4689"},
        )

    def tearDown(self):
        self.settings_patch.stop()
        self.drm_patch.stop()
        self.db.close()
        self.engine.dispose()
        self.tmpdir.cleanup()

    def _upload(self, name, content, order_id=None):
        upload = UploadFile(filename=name, file=io.BytesIO(content))
        return service.upload_file(
            self.db,
            upload,
            order_id or self.order["id"],
            "tester",
        )

    def _file_record(self, uploaded):
        link = self.db.get(MolecularLibraryResultLink, uploaded["id"])
        return self.db.get(MolecularLibraryResultFile, link.file_id)

    def test_hash_reuse_unlinks_safely(self):
        first = self._upload("gel.png", b"gel-bytes")
        first_record = self._file_record(first)
        self.assertEqual(first["result_kind"], service.FILE_KIND_GEL)
        disk = self.repo / "uploads" / first_record.storage_path.lstrip("/")
        self.assertTrue(disk.exists())

        other = service.save(
            self.db,
            {"build_type": service.BUILD_PHAGE_DISPLAY, "library_code": "NH9875"},
        )
        second = self._upload(
            "same-content.jpg",
            b"gel-bytes",
            order_id=other["id"],
        )
        second_record = self._file_record(second)
        self.assertEqual(first_record.id, second_record.id)
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(service.list_files(self.db, other["id"])["items"][0]["original_name"], "same-content.jpg")

        deleted = service.delete_file(self.db, first["id"], self.order["id"])
        self.assertFalse(deleted["file_deleted"])
        self.assertIsNotNone(self.db.get(MolecularLibraryResultFile, first_record.id))
        self.assertEqual(len(service.list_files(self.db, other["id"])["items"]), 1)
        self.assertTrue(disk.exists())

        deleted_last = service.delete_file(self.db, second["id"], other["id"])
        self.assertTrue(deleted_last["file_deleted"])
        self.assertIsNone(self.db.get(MolecularLibraryResultFile, first_record.id))
        self.assertFalse(disk.exists())

    def test_file_kind_is_inferred_from_current_name(self):
        for filename in ("trace.ab1", "analysis.clc", "result.fasta"):
            uploaded = self._upload(filename, filename.encode())
            self.assertEqual(uploaded["result_kind"], service.FILE_KIND_PRIMER_QC)

    def test_rename_preserves_file_extension(self):
        uploaded = self._upload("gel.png", b"gel-content")
        renamed = service.update_file_link(
            self.db,
            uploaded["id"],
            self.order["id"],
            {"original_name": "最终胶图"},
        )
        self.assertEqual(renamed["original_name"], "最终胶图.png")
        self.assertEqual(renamed["result_kind"], service.FILE_KIND_GEL)
        with self.assertRaisesRegex(ValueError, "不能修改文件扩展名"):
            service.update_file_link(
                self.db,
                uploaded["id"],
                self.order["id"],
                {"original_name": "最终胶图.xlsx"},
            )

    def test_final_qc_and_regions_belong_to_order_file_link(self):
        first = self._upload("first.png", b"first-gel")
        second = self._upload("second.png", b"second-gel")
        regions = [
            {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.4, "label": "H链"},
            {"x": 0.55, "y": 0.1, "width": 0.2, "height": 0.3},
        ]
        updated = service.update_file_link(
            self.db,
            first["id"],
            self.order["id"],
            {"is_final_qc": True, "qc_regions": regions},
        )
        self.assertTrue(updated["is_final_qc"])
        self.assertEqual(updated["qc_regions"], regions)
        items = service.list_files(self.db, self.order["id"])["items"]
        self.assertEqual([item["id"] for item in items], [first["id"], second["id"]])
        self.assertFalse(items[1]["is_final_qc"])
        self.assertEqual(items[1]["qc_regions"], [])

    def test_qc_regions_must_be_inside_image(self):
        uploaded = self._upload("gel.png", b"gel-content")
        with self.assertRaisesRegex(ValueError, "图片范围内"):
            service.update_file_link(
                self.db,
                uploaded["id"],
                self.order["id"],
                {"qc_regions": [{"x": 0.8, "y": 0.2, "width": 0.4, "height": 0.4}]},
            )
        with self.assertRaisesRegex(ValueError, "不能超过 24 个字符"):
            service.update_file_link(
                self.db,
                uploaded["id"],
                self.order["id"],
                {
                    "qc_regions": [
                        {
                            "x": 0.1,
                            "y": 0.2,
                            "width": 0.3,
                            "height": 0.4,
                            "label": "x" * 25,
                        }
                    ]
                },
            )

    def test_hash_and_size_describe_post_drm_file(self):
        decrypted = b"decrypted-content"

        def replace_content(_db, path):
            path.write_bytes(decrypted)

        self.drm_mock.side_effect = replace_content
        uploaded = self._upload("report.xlsx", b"encrypted-content")
        record = self._file_record(uploaded)
        self.assertEqual(record.sha256, hashlib.sha256(decrypted).hexdigest())
        self.assertEqual(uploaded["byte_size"], len(decrypted))
        disk = self.repo / "uploads" / record.storage_path.lstrip("/")
        self.assertEqual(disk.read_bytes(), decrypted)

    def test_file_payload_hides_storage_fields(self):
        uploaded = self._upload("gel.png", b"gel-content")
        self.assertNotIn("file_id", uploaded)
        self.assertNotIn("storage_path", uploaded)
        self.assertNotIn("sha256", uploaded)

    def test_corrupt_image_has_no_thumbnail(self):
        path = self.repo / "broken.png"
        path.write_bytes(b"not-an-image")
        self.assertIsNone(service.create_thumbnail(path, 240, 160))

    def test_upload_commit_failure_removes_new_file(self):
        with patch.object(self.db, "commit", side_effect=RuntimeError("commit failed")):
            with self.assertRaisesRegex(RuntimeError, "commit failed"):
                self._upload("gel.png", b"new-gel")
        files = [path for path in (self.repo / "uploads").rglob("*") if path.is_file()]
        self.assertEqual(files, [])

    def test_delete_commit_failure_keeps_disk_file(self):
        uploaded = self._upload("gel.png", b"gel-content")
        record = self._file_record(uploaded)
        disk = self.repo / "uploads" / record.storage_path.lstrip("/")
        with patch.object(self.db, "commit", side_effect=RuntimeError("commit failed")):
            with self.assertRaisesRegex(RuntimeError, "commit failed"):
                service.delete_file(self.db, uploaded["id"], self.order["id"])
        self.assertTrue(disk.exists())
        self.db.rollback()

    def test_delete_order_cleans_only_unshared_files(self):
        first = self._upload("gel.png", b"shared-gel")
        first_record = self._file_record(first)
        disk = self.repo / "uploads" / first_record.storage_path.lstrip("/")
        other = service.save(
            self.db,
            {"build_type": service.BUILD_PHAGE_DISPLAY, "library_code": "NH9875"},
        )
        self._upload(
            "shared.png",
            b"shared-gel",
            order_id=other["id"],
        )

        deleted = service.delete_order(self.db, self.order["id"])
        self.assertEqual(deleted["id"], self.order["id"])
        self.assertIsNone(self.db.get(MolecularLibraryOrder, self.order["id"]))
        self.assertIsNotNone(self.db.get(MolecularLibraryResultFile, first_record.id))
        self.assertTrue(disk.exists())

        service.delete_order(self.db, other["id"])
        self.assertIsNone(self.db.get(MolecularLibraryResultFile, first_record.id))
        self.assertFalse(disk.exists())


if __name__ == "__main__":
    unittest.main()
