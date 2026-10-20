import io
import hashlib
import re
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

from fastapi import UploadFile
from sqlalchemy import BigInteger, create_engine, select
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

from db.session import Base
from models.discovery import DiscoveryWorkbench
from models.molecular_cell import (
    MolecularLibraryOrder,
    MolecularLibraryResultFile,
    MolecularLibraryResultLink,
    MolecularLibraryResultPackage,
    MolecularPrimerIndexCatalog,
)
from modules.discovery.workbench import service as discovery_service
from modules.molecular_cell.library_orders import service
from modules.molecular_cell.library_orders.result_upload import (
    FORWARD_ARM_1,
    FORWARD_ARM_2,
    TRACE_EXTENSIONS,
    assembled_primer,
    preview_extension,
    primer_check_sequence,
)


def _long_enough(sequence: str) -> bytes:
    if len(sequence) <= 400:
        sequence += "N" * (401 - len(sequence))
    return sequence.encode()


def _read(primer, direction="F"):
    return _long_enough(f"NN{assembled_primer(primer, direction)}NN")


@compiles(BigInteger, "sqlite")
def _compile_big_integer_for_sqlite(_type, _compiler, **_kwargs):
    return "INTEGER"


LIBRARY_ID_RE = re.compile(r"^LIB-\d{6}-[A-Z0-9]{6}$")
TABLES = [
    DiscoveryWorkbench.__table__,
    MolecularLibraryOrder.__table__,
    MolecularPrimerIndexCatalog.__table__,
    MolecularLibraryResultPackage.__table__,
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

    def test_created_order_lists_oldest_first_on_the_last_page(self):
        first = service.save(self.db, {"build_type": service.BUILD_POOLED_BCR, "library_code": "C1"})
        second = service.save(self.db, {"build_type": service.BUILD_POOLED_BCR, "library_code": "C2"})
        third = service.save(self.db, {"build_type": service.BUILD_POOLED_BCR, "library_code": "C3"})
        newest_first = service.get_list(self.db, {"page": 1, "limit": 2})
        self.assertEqual([item["id"] for item in newest_first["items"]], [third["id"], second["id"]])
        oldest_first = service.get_list(self.db, {"order": "id_asc", "page": 99, "limit": 2})
        self.assertEqual(oldest_first["page"], 2)
        self.assertEqual([item["id"] for item in oldest_first["items"]], [third["id"]])
        self.assertEqual(oldest_first["total"], 3)
        self.assertLess(first["id"], third["id"])

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

    def test_sample_type_follows_mouse_strain(self):
        saved = service.save(
            self.db,
            {"build_type": service.BUILD_POOLED_BCR, "mouse_strain": "RN"},
        )
        self.assertEqual(saved["sample_type"], service.SAMPLE_NANO)
        updated = service.save(self.db, {"id": saved["id"], "mouse_strain": "RL"})
        self.assertEqual(updated["sample_type"], service.SAMPLE_LITE)
        nano_variant = service.save(self.db, {"id": saved["id"], "mouse_strain": "RNVMKO"})
        self.assertEqual(nano_variant["sample_type"], service.SAMPLE_NANO)
        manual = service.save(
            self.db,
            {
                "id": saved["id"],
                "mouse_strain": "RNVM",
                "sample_type": service.SAMPLE_RNVM_BLOOD,
            },
        )
        self.assertEqual(manual["sample_type"], service.SAMPLE_RNVM_BLOOD)
        first_of_many = service.save(
            self.db,
            {"id": saved["id"], "mouse_strain": "RN、RLKO"},
        )
        self.assertEqual(first_of_many["mouse_strain"], "RLKO、RN")
        self.assertEqual(first_of_many["sample_type"], service.SAMPLE_LITE)
        custom = service.save(
            self.db,
            {"id": saved["id"], "mouse_strain": "自建品系、RL"},
        )
        self.assertEqual(custom["mouse_strain"], "RL、自建品系")
        self.assertEqual(custom["sample_type"], service.SAMPLE_LITE)
        unmapped_first = service.save(
            self.db,
            {"id": saved["id"], "mouse_strain": "RM、RN"},
        )
        self.assertEqual(unmapped_first["sample_type"], service.SAMPLE_LITE)
        renmab = service.save(
            self.db,
            {"build_type": service.BUILD_POOLED_BCR, "mouse_strain": "RMB/C"},
        )
        self.assertIsNone(renmab["sample_type"])
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

    def test_status_follows_locations_and_can_be_set_freely(self):
        started = service.save(
            self.db,
            {"build_type": service.BUILD_PLATE, "cdna_location": "C-01"},
        )
        self.assertEqual(started["status"], service.STATUS_IN_PROGRESS)
        self.assertEqual(started["started_at"], date.today().isoformat())
        self.assertIsNone(started["finished_at"])
        dated = service.save(self.db, {"id": started["id"], "started_at": "2020-01-01"})
        self.assertEqual(dated["started_at"], "2020-01-01")
        held = service.save(self.db, {"id": started["id"], "status": service.STATUS_PENDING})
        self.assertEqual(held["status"], service.STATUS_PENDING)
        jumped = service.save(self.db, {"id": started["id"], "status": service.STATUS_DONE})
        self.assertEqual(jumped["status"], service.STATUS_DONE)
        judged = service.save(
            self.db,
            {"build_type": service.BUILD_PHAGE_DISPLAY, "qc_result": "通过"},
        )
        self.assertEqual(judged["status"], service.STATUS_QC_PASS)
        self.assertIsNone(judged["started_at"])
        self.assertIsNone(judged["finished_at"])
        finished = service.save(self.db, {"id": judged["id"], "library_location": "盒 A1"})
        self.assertEqual(finished["status"], service.STATUS_DONE)
        self.assertIsNone(finished["started_at"])
        self.assertEqual(finished["finished_at"], date.today().isoformat())
        parked = service.save(
            self.db,
            {"build_type": service.BUILD_PHAGE_NGS, "library_location": "盒 B1"},
        )
        self.assertEqual(parked["status"], service.STATUS_PENDING)
        self.assertIsNone(parked["started_at"])
        self.assertEqual(parked["finished_at"], date.today().isoformat())

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
        self.assertEqual(item["mouse_strain"], "RN")
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

    def test_gel_and_sequencing_advance_status(self):
        order = service.save(
            self.db,
            {
                "build_type": service.BUILD_POOLED_BARCODE,
                "library_code": "C123",
                "index_mode": service.INDEX_DUAL,
                "i5_sequence": "AAAA",
                "i7_sequence": "CCCC",
            },
        )
        self._upload("C123.png", b"gel", order["id"])
        waiting = self.db.get(MolecularLibraryOrder, order["id"])
        self.assertEqual(waiting.status, service.STATUS_WAIT_QC)
        self._upload("C123_M13F.seq", _read("AAAA"), order["id"])
        still_waiting = self.db.get(MolecularLibraryOrder, order["id"])
        self.assertEqual(still_waiting.status, service.STATUS_WAIT_QC)
        self._upload("C123_M13R.seq", _read("CCCC", "R"), order["id"])
        passed = self.db.get(MolecularLibraryOrder, order["id"])
        self.assertEqual(passed.status, service.STATUS_QC_PASS)
        trace = self._upload("C123_M13F.ab1", b"not-a-trace", order["id"])
        self.assertEqual(trace["sequence_status"], "trace_only")
        link = self.db.scalar(
            select(MolecularLibraryResultLink).where(
                MolecularLibraryResultLink.order_id == order["id"],
                MolecularLibraryResultLink.original_name == "C123_M13F.ab1",
            )
        )
        link.sequence_status = "not_found"
        self.db.commit()
        service._advance_order_status(self.db, self.db.get(MolecularLibraryOrder, order["id"]))
        self.assertEqual(
            self.db.get(MolecularLibraryOrder, order["id"]).status,
            service.STATUS_QC_PASS,
        )
        mismatched = service.save(
            self.db,
            {
                "build_type": service.BUILD_POOLED_BARCODE,
                "library_code": "C456",
                "index_mode": service.INDEX_I5,
                "i5_sequence": "AAAA",
            },
        )
        self._upload("C456.png", b"gel", mismatched["id"])
        self._upload("C456_M13F.seq", b"GGGGGGGG", mismatched["id"])
        held = self.db.get(MolecularLibraryOrder, mismatched["id"])
        self.assertEqual(held.status, service.STATUS_QC_HOLD)

    def test_automatic_qc_does_not_complete_order_with_library_location(self):
        order = self._barcode_order("C123", i5_sequence="AAAA")
        service.save(
            self.db,
            {"id": order["id"], "library_location": "冰箱 A"},
        )
        self._upload("C123.png", b"gel", order["id"])
        self._upload("C123_M13F.seq", _read("AAAA"), order["id"])
        self.assertEqual(
            self.db.get(MolecularLibraryOrder, order["id"]).status,
            service.STATUS_QC_PASS,
        )

    def test_partial_primer_match_outranks_waiting_qc(self):
        order = self._barcode_order("C123", i5_sequence="AAAA")
        self._upload("C123.png", b"gel", order["id"])
        self._upload(
            "C123-1_M13F.seq",
            _read("AAAA"),
            order["id"],
        )
        self.assertEqual(
            self.db.get(MolecularLibraryOrder, order["id"]).status,
            service.STATUS_QC_PASS,
        )
        self._upload("C123-2_M13F.seq", b"GGGGGGGG", order["id"])
        self.assertEqual(
            self.db.get(MolecularLibraryOrder, order["id"]).status,
            service.STATUS_QC_HOLD,
        )
        self.assertEqual(
            service._qc_order_rows(self.db, {order["id"]})[0]["detail"],
            "有文件没对上引物",
        )

    def test_package_matches_only_sequencing_folder(self):
        order = self._barcode_order("C123", i5_sequence="AAAA")
        good = _read("AAAA")
        result = service.upload_batch(
            self.db,
            [
                UploadFile(filename="C123_M13F.seq", file=io.BytesIO(good)),
                UploadFile(filename="C123-assembly_M13F.seq", file=io.BytesIO(b"GGGG")),
                UploadFile(filename="trimmed.txt", file=io.BytesIO(b"trim")),
            ],
            [
                "pkg/测序结果/C123_M13F.seq",
                "pkg/拼接结果/C123-assembly_M13F.seq",
                "pkg/去载体序列/trimmed.txt",
            ],
            "tester",
            order["id"],
        )
        self.assertEqual(
            [item["original_name"] for item in result["items"]],
            ["C123_M13F.seq"],
        )
        self.assertEqual(
            self.db.get(MolecularLibraryOrder, order["id"]).status,
            service.STATUS_WAIT_QC,
        )
        stored = {
            item["relative_path"]
            for item in service.list_files(self.db, order["id"])["packages"][0]["files"]
        }
        self.assertIn("拼接结果/C123-assembly_M13F.seq", stored)
        self.assertIn("测序结果/C123_M13F.seq", stored)

    def test_unmatched_sequence_needs_confirmation_without_gel(self):
        order = self._barcode_order("C123", i5_sequence="AAAA")
        self._upload("C123_M13F.seq", b"GGGG", order["id"])
        self.assertEqual(
            self.db.get(MolecularLibraryOrder, order["id"]).status,
            service.STATUS_QC_HOLD,
        )

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

    def test_long_filename_keeps_extension_for_preview(self):
        original = f"{'C' * 90}.ab1"
        stored = service.safe_path_part(original, "file")
        recognized = TRACE_EXTENSIONS | service.INLINE_PREVIEW_EXTENSIONS

        self.assertTrue(stored.endswith(".ab1"))
        self.assertLessEqual(len(stored), 80)
        self.assertEqual(preview_extension(stored, original, recognized), ".ab1")
        self.assertEqual(
            preview_extension(f"{'C' * 78}.ab", original, recognized),
            ".ab1",
        )

    def test_read_trace_preview_returns_chart_data(self):
        path = self.repo / "sample.ab1"
        path.write_bytes(b"mocked")
        record = type(
            "AbiRecord",
            (),
            {
                "seq": "ACGT",
                "annotations": {
                    "abif_raw": {
                        "FWO_1": b"GATC",
                        "PBAS2": b"ACGT",
                        "PLOC2": (10, 30, 50, 70),
                        "DATA9": tuple(range(100)),
                        "DATA10": tuple(reversed(range(100))),
                        "DATA11": tuple(index % 20 for index in range(100)),
                        "DATA12": tuple((index * 2) % 35 for index in range(100)),
                    }
                },
            },
        )()
        with patch("Bio.SeqIO.read", return_value=record):
            preview = service.read_trace_preview(path)

        self.assertEqual(preview["sample_count"], 100)
        self.assertEqual(preview["bases"][0], {
            "base": "A",
            "position": 10,
            "quality": None,
        })
        self.assertEqual(set(preview["channels"]), {"A", "C", "G", "T"})
        self.assertEqual(len(preview["channels"]["A"]), 100)

    def test_corrupt_trace_preview_is_rejected(self):
        path = self.repo / "broken.ab1"
        path.write_bytes(b"not-an-abi")
        with self.assertRaisesRegex(ValueError, "峰图解析失败"):
            service.read_trace_preview(path)

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

    def _barcode_order(self, library_code, **fields):
        return service.save(
            self.db,
            {
                "build_type": service.BUILD_POOLED_BARCODE,
                "library_code": library_code,
                "index_mode": service.INDEX_DUAL,
                **fields,
            },
        )

    def test_sequencing_files_keep_separate_copies(self):
        order = self._barcode_order("C123", i5_sequence="AAAA")
        first = self._upload("C123-1_M13F.seq", b"same-seq", order["id"])
        second = self._upload("C123-2_M13F.seq", b"same-seq", order["id"])
        self.assertNotEqual(self._file_record(first).id, self._file_record(second).id)
        self.assertIn("/library_results/others/", self._file_record(first).storage_path)
        self.assertIn("/library_results/gels/", self._file_record(self._upload("gel.png", b"gel-bytes")).storage_path)

    def test_qc_page_keeps_unmatched_file_on_current_order(self):
        uploaded = self._upload("trace.ab1", b"trace-bytes")
        record = self._file_record(uploaded)
        self.assertEqual(uploaded["order_id"], self.order["id"])
        self.assertEqual(uploaded["result_kind"], service.FILE_KIND_PRIMER_QC)
        self.assertIn("/library_results/others/", record.storage_path)
        self.assertIn(self.order["library_order_id"], record.storage_path)

    def test_filename_links_the_matched_order_and_checks_primer(self):
        named = self._barcode_order("C123", i5_sequence="AAAA", i7_sequence="CCCC")
        other = self._barcode_order("C456")
        with self.assertRaisesRegex(ValueError, "建库编号 C123 属于其他工单"):
            self._upload("C123-1_M13F.seq", _read("AAAA"), self.order["id"])
        with self.assertRaisesRegex(ValueError, "建库编号 C123、C456 属于其他工单"):
            self._upload("C123-C456.png", b"gel", self.order["id"])
        self.assertEqual(len(service.list_files(self.db, self.order["id"])["items"]), 0)
        self.assertEqual(len(service.list_files(self.db, named["id"])["items"]), 0)
        self.assertEqual(len(service.list_files(self.db, other["id"])["items"]), 0)

        batched = service.upload_batch(
            self.db,
            [UploadFile(filename="C123-2_M13F.seq", file=io.BytesIO(_read("AAAA")))],
            ["C123-2_M13F.seq"],
            "tester",
        )
        self.assertEqual(batched["items"][0]["order_id"], named["id"])

        shared = self._upload("C123-C456.png", b"gel", named["id"])
        self.assertEqual(shared["order_id"], named["id"])
        self.assertEqual(len(service.list_files(self.db, other["id"])["items"]), 0)

        uploaded = self._upload("C123-1_M13F.seq", _read("AAAA"), named["id"])
        self.assertEqual(uploaded["order_id"], named["id"])
        self.assertEqual(uploaded["sequence_check"], "i5 匹配")

        missing = self._upload("C123-1_M13R.seq", _long_enough("NNNN"), named["id"])
        self.assertEqual(missing["sequence_check"], "i7 同源臂未匹配")
        trace = self._upload("C123-1_M13F.ab1", b"chromatogram", named["id"])
        self.assertEqual(trace["sequence_status"], "trace_only")
        self.assertEqual(trace["sequence_target"], "i5")
        self.assertIsNone(trace["sequence_check"])

    def test_sequence_check_treats_n_as_a_literal_base(self):
        order = self._barcode_order("C123", i5_sequence="AAAN")
        mismatch = self._upload("C123-1_M13F.seq", b"ATTT", order["id"])
        matched = self._upload("C123-2_M13F.seq", _read("AAAN"), order["id"])
        self.assertEqual(mismatch["sequence_status"], "not_found_short")
        self.assertEqual(matched["sequence_status"], "matched")

    def test_batch_preflight_uses_paths_without_file_content(self):
        self._barcode_order("C123", i5_sequence="AAAA")
        result = service.preflight_upload(
            self.db,
            [
                "pkg/测序结果/C123-1_M13F.seq",
                "pkg/拼接结果/assembled.seq",
                "pkg/去载体序列/trimmed.txt",
            ],
        )
        self.assertEqual(result["accepted_indexes"], [0, 1, 2])
        self.assertEqual(result["summary"][0]["outcome"], "ready")
        self.assertEqual(result["summary"][0]["matched_count"], 1)
        self.assertEqual(result["summary"][0]["accepted_count"], 3)
        self.assertEqual(result["summary"][0]["matched_codes"], ["C123"])
        self.assertEqual(result["summary"][0]["matched_files"], [{"code": "C123", "count": 1}])

    def test_batch_preflight_enforces_shared_upload_count_limit(self):
        paths = [f"file-{index}.txt" for index in range(service.MAX_UPLOAD_FILES + 1)]
        with self.assertRaisesRegex(ValueError, str(service.MAX_UPLOAD_FILES)):
            service.preflight_upload(self.db, paths)

    def test_preflight_keeps_same_leaf_package_summaries_separate(self):
        self._barcode_order("C123", i5_sequence="AAAA")
        paths = []
        for parent in ("batch-a", "batch-b"):
            paths.extend([
                f"{parent}/pkg/测序结果/C123_M13F.seq",
                f"{parent}/pkg/拼接结果/assembled.txt",
                f"{parent}/pkg/去载体序列/trimmed.txt",
            ])
        result = service.preflight_upload(self.db, paths)
        self.assertEqual(len(result["summary"]), 2)
        self.assertEqual([item["name"] for item in result["summary"]], ["pkg", "pkg"])
        self.assertEqual(len({item["group_id"] for item in result["summary"]}), 2)

    def test_batch_preflight_accepts_a_package_missing_a_folder(self):
        self._barcode_order("C123", i5_sequence="AAAA")
        result = service.preflight_upload(
            self.db,
            [
                "pkg/测序结果/C123_M13F.seq",
                "pkg/拼接结果/assembled.txt",
            ],
        )
        self.assertEqual(result["accepted_indexes"], [0, 1])
        self.assertEqual(result["summary"][0]["outcome"], "ready")
        self.assertEqual(result["summary"][0]["matched_codes"], ["C123"])

    def test_batch_upload_reads_only_preflight_accepted_packages(self):
        self._barcode_order("C123", i5_sequence="AAAA")
        files = [
            UploadFile(filename="C123_M13F.seq", file=io.BytesIO(b"TTTT")),
            UploadFile(filename="assembled.txt", file=io.BytesIO(b"assembled")),
            UploadFile(filename="trimmed.txt", file=io.BytesIO(b"trimmed")),
            UploadFile(filename="C999_M13F.seq", file=io.BytesIO(b"TTTT")),
            UploadFile(filename="assembled.txt", file=io.BytesIO(b"assembled")),
            UploadFile(filename="trimmed.txt", file=io.BytesIO(b"trimmed")),
        ]
        paths = [
            "ready/测序结果/C123_M13F.seq",
            "ready/拼接结果/assembled.txt",
            "ready/去载体序列/trimmed.txt",
            "rejected/测序结果/C999_M13F.seq",
            "rejected/拼接结果/assembled.txt",
            "rejected/去载体序列/trimmed.txt",
        ]
        with patch.object(service, "_read_upload", wraps=service._read_upload) as read_upload:
            result = service.upload_batch(self.db, files, paths, "tester")
        self.assertEqual(read_upload.call_count, 3)
        self.assertEqual(
            {item["name"]: item["outcome"] for item in result["summary"]},
            {"ready": "stored", "rejected": "skipped"},
        )

    def test_batch_keeps_package_and_skips_unassigned_files(self):
        order = self._barcode_order("C123", i5_sequence="AAAA")
        seq = _read("AAAA")
        files = [
            UploadFile(filename="C123.png", file=io.BytesIO(b"shared-gel")),
            UploadFile(filename="C123-1_M13F.seq", file=io.BytesIO(seq)),
            UploadFile(filename="C123-1.seq", file=io.BytesIO(b"assembly")),
            UploadFile(filename="vector.TXT", file=io.BytesIO(b"insert")),
            UploadFile(filename="明细表.xlsx", file=io.BytesIO(b"sheet")),
            UploadFile(filename="plain.png", file=io.BytesIO(b"loose-gel")),
            UploadFile(filename="skip.txt", file=io.BytesIO(b"skip")),
        ]
        paths = [
            "pkg/C123.png",
            "pkg/测序结果/C123-1_M13F.seq",
            "pkg/拼接结果/C123-1.seq",
            "pkg/去载体序列/vector.TXT",
            "pkg/明细表.xlsx",
            "pkg/plain.png",
            "pkg/其他/skip.txt",
        ]
        result = service.upload_batch(self.db, files, paths, "tester")
        names = {item["original_name"]: item for item in result["items"]}
        self.assertNotIn("C123.png", names)
        self.assertNotIn("C123-1.seq", names)
        self.assertEqual(names["C123-1_M13F.seq"]["sequence_check"], "i5 匹配")
        listed = service.list_files(self.db, order["id"])
        self.assertEqual(len(listed["items"]), 1)
        self.assertEqual(len(service.list_files(self.db, self.order["id"])["items"]), 0)
        package = listed["packages"][0]
        self.assertEqual(package["name"], "pkg")
        self.assertEqual(package["qc_count"], 1)
        self.assertEqual(
            {item["original_name"] for item in package["files"]},
            {
                "C123.png",
                "C123-1_M13F.seq",
                "C123-1.seq",
                "vector.TXT",
                "明细表.xlsx",
                "plain.png",
                "skip.txt",
            },
        )
        self.assertEqual(result["summary"][0]["outcome"], "stored")
        self.assertEqual(result["summary"][0]["orders"], [{
            "id": order["id"],
            "library_code": "C123",
            "status": service.STATUS_WAIT_QC,
            "detail": "引物已对上，还没有胶图",
        }])
        again = service.upload_batch(
            self.db,
            [
                UploadFile(filename="C123.png", file=io.BytesIO(b"shared-gel")),
                UploadFile(filename="C123-1_M13F.seq", file=io.BytesIO(seq)),
                UploadFile(filename="C123-1.seq", file=io.BytesIO(b"assembly")),
                UploadFile(filename="vector.TXT", file=io.BytesIO(b"insert")),
                UploadFile(filename="明细表.xlsx", file=io.BytesIO(b"sheet")),
                UploadFile(filename="plain.png", file=io.BytesIO(b"loose-gel")),
                UploadFile(filename="skip.txt", file=io.BytesIO(b"skip")),
            ],
            paths,
            "tester",
        )
        self.assertEqual(again["summary"][0]["outcome"], "already")
        self.assertEqual(
            self.db.query(MolecularLibraryResultPackage).count(),
            1,
        )
        package_files = list((self.repo / "uploads" / "library_results" / "sequencing").rglob("*"))
        relative = [path.relative_to(self.repo / "uploads").as_posix() for path in package_files if path.is_file()]
        self.assertTrue(any(path.endswith("测序结果/C123-1_M13F.seq") for path in relative))
        self.assertTrue(any(path.endswith("拼接结果/C123-1.seq") for path in relative))
        self.assertTrue(any(path.endswith("去载体序列/vector.TXT") for path in relative))

    def test_batch_keeps_a_package_missing_a_folder(self):
        order = self._barcode_order("C123", i5_sequence="AAAA")
        result = service.upload_batch(
            self.db,
            [
                UploadFile(filename="C123_M13F.seq", file=io.BytesIO(b"TTTT")),
                UploadFile(filename="assembled.txt", file=io.BytesIO(b"assembled")),
            ],
            [
                "pkg/测序结果/C123_M13F.seq",
                "pkg/拼接结果/assembled.txt",
            ],
            "tester",
        )
        self.assertEqual(result["summary"][0]["outcome"], "stored")
        self.assertEqual(result["summary"][0]["name"], "pkg")
        self.assertEqual(
            service.list_files(self.db, order["id"])["items"][0]["original_name"],
            "C123_M13F.seq",
        )

    def test_marker_folder_itself_is_a_package(self):
        order = self._barcode_order("C123", i5_sequence="AAAA")
        result = service.upload_batch(
            self.db,
            [UploadFile(filename="C123_M13F.seq", file=io.BytesIO(b"TTTT"))],
            ["测序结果/C123_M13F.seq"],
            "tester",
        )
        self.assertEqual(result["summary"][0]["outcome"], "stored")
        self.assertEqual(result["summary"][0]["name"], "测序结果")
        self.assertEqual(
            service.list_files(self.db, order["id"])["packages"][0]["name"],
            "测序结果",
        )

    def test_company_folders_split_and_match_the_longest_code(self):
        orders = {
            code: self._barcode_order(code, i5_sequence="AAAA", i7_sequence="CCCC")
            for code in ("C782", "C600", "C634", "C601", "X101", "C766", "C766-L169", "C782-1")
        }
        files = [
            ("C782-1-(M13F)(261015).seq", _read("AAAA")),
            ("C782-2-(M13R)(261015).seq", _read("CCCC", "R")),
            ("第一次结果.pdf", b"report"),
            ("C600-KM-1-M13F-77.seq", _read("AAAA")),
            ("C634-K-1-M13F-77.seq", _read("AAAA")),
            ("C601-KM-2-M13F-77.seq", _read("AAAA")),
            ("X101-5_M13F_TSS.seq", _read("AAAA")),
            ("X101-5_TSS.seq", b"assembly"),
            ("X101-5_TSS.TXT", b"trimmed"),
            ("C766-L169_M13F.seq", _read("AAAA")),
            ("C782-10-(M13F).seq", _read("AAAA")),
            ("C766-L169_M13F_M13R.seq", _read("AAAA")),
        ]
        paths = [
            "batch/20261015-050/20261015-050/测序合格结果/C782-1-(M13F)(261015).seq",
            "batch/20261015-050/20261015-050/特殊合格结果/C782-2-(M13R)(261015).seq",
            "batch/20261015-050/20261015-050/第一次结果.pdf",
            "batch/CN/完成/C600-KM-1-M13F-77.seq",
            "batch/CN/完成-套峰/C634-K-1-M13F-77.seq",
            "batch/CN/无信号/C601-KM-2-M13F-77.seq",
            "batch/TJ/测序结果/X101-5_M13F_TSS.seq",
            "batch/TJ/拼接结果/X101-5_TSS.seq",
            "batch/TJ/去载体序列/X101-5_TSS.TXT",
            "batch/old/测序结果/C766-L169_M13F.seq",
            "batch/old/测序结果/C782-10-(M13F).seq",
            "batch/old/测序结果/C766-L169_M13F_M13R.seq",
        ]
        result = service.upload_batch(
            self.db,
            [UploadFile(filename=name, file=io.BytesIO(content)) for name, content in files],
            paths,
            "tester",
        )
        self.assertEqual(
            [item["name"] for item in result["summary"]],
            ["20261015-050", "CN", "TJ", "old"],
        )
        linked = {item["original_name"]: item for item in result["items"]}
        self.assertEqual(linked["C782-1-(M13F)(261015).seq"]["order_id"], orders["C782-1"]["id"])
        self.assertEqual(linked["C782-1-(M13F)(261015).seq"]["sequence_check"], "i5 匹配")
        self.assertEqual(linked["C782-2-(M13R)(261015).seq"]["order_id"], orders["C782"]["id"])
        self.assertEqual(linked["C782-2-(M13R)(261015).seq"]["sequence_check"], "i7 匹配")
        self.assertEqual(linked["C600-KM-1-M13F-77.seq"]["order_id"], orders["C600"]["id"])
        self.assertEqual(linked["C634-K-1-M13F-77.seq"]["order_id"], orders["C634"]["id"])
        self.assertEqual(linked["C634-K-1-M13F-77.seq"]["sequence_target"], "i5")
        self.assertEqual(linked["C601-KM-2-M13F-77.seq"]["order_id"], orders["C601"]["id"])
        self.assertEqual(linked["X101-5_M13F_TSS.seq"]["order_id"], orders["X101"]["id"])
        self.assertNotIn("X101-5_TSS.seq", linked)
        self.assertEqual(linked["C766-L169_M13F.seq"]["order_id"], orders["C766-L169"]["id"])
        self.assertEqual(linked["C782-10-(M13F).seq"]["order_id"], orders["C782"]["id"])
        self.assertEqual(linked["C766-L169_M13F_M13R.seq"]["order_id"], orders["C766-L169"]["id"])
        self.assertFalse(linked["C766-L169_M13F_M13R.seq"]["sequence_check"])
        tj = service.list_files(self.db, orders["X101"]["id"])["packages"][0]
        self.assertEqual(
            {item["original_name"] for item in tj["files"]},
            {"X101-5_M13F_TSS.seq", "X101-5_TSS.seq", "X101-5_TSS.TXT"},
        )

    def test_changed_file_goes_to_a_new_package(self):
        order = self._barcode_order("C123", i5_sequence="AAAA")
        paths = [
            "pkg/测序结果/C123_M13F.seq",
            "pkg/拼接结果/assembled.txt",
            "pkg/去载体序列/trimmed.txt",
        ]

        def upload(sequence, trimmed):
            return service.upload_batch(
                self.db,
                [
                    UploadFile(filename="C123_M13F.seq", file=io.BytesIO(sequence)),
                    UploadFile(filename="assembled.txt", file=io.BytesIO(b"assembled")),
                    UploadFile(filename="trimmed.txt", file=io.BytesIO(trimmed)),
                ],
                paths,
                "tester",
            )

        first = upload(b"TTTT", b"v1")
        second = upload(_read("AAAA"), b"v2")
        self.assertEqual(first["summary"][0]["outcome"], "stored")
        self.assertEqual(second["summary"][0]["outcome"], "stored")
        self.assertEqual(self.db.query(MolecularLibraryResultPackage).count(), 2)
        listed = service.list_files(self.db, order["id"])
        self.assertEqual(len(listed["packages"]), 2)
        self.assertEqual(
            [item["original_name"] for item in listed["items"]].count("C123_M13F.seq"),
            2,
        )
        for package in listed["packages"]:
            paths_in_package = [item["relative_path"] for item in package["files"]]
            self.assertEqual(len(paths_in_package), len(set(paths_in_package)))
        seq_files = [
            path
            for path in (self.repo / "uploads" / "library_results" / "sequencing").rglob("*")
            if path.is_file() and "C123_M13F" in path.name
        ]
        self.assertEqual(len(seq_files), 2)

    def test_added_file_reuses_the_package_without_duplicating_old_links(self):
        first = self._barcode_order("C123", i5_sequence="AAAA")
        seq = _read("AAAA")
        paths = [
            "pkg/测序结果/C123_M13F.seq",
            "pkg/拼接结果/assembled.txt",
            "pkg/去载体序列/trimmed.txt",
        ]
        service.upload_batch(
            self.db,
            [
                UploadFile(filename="C123_M13F.seq", file=io.BytesIO(seq)),
                UploadFile(filename="assembled.txt", file=io.BytesIO(b"assembled")),
                UploadFile(filename="trimmed.txt", file=io.BytesIO(b"trimmed")),
            ],
            paths,
            "tester",
        )
        second = self._barcode_order("C456", i5_sequence="CCCC")
        extended_paths = paths + ["pkg/测序结果/C456_M13F.seq"]
        again = service.upload_batch(
            self.db,
            [
                UploadFile(filename="C123_M13F.seq", file=io.BytesIO(seq)),
                UploadFile(filename="assembled.txt", file=io.BytesIO(b"assembled")),
                UploadFile(filename="trimmed.txt", file=io.BytesIO(b"trimmed")),
                UploadFile(filename="C456_M13F.seq", file=io.BytesIO(_read("CCCC"))),
            ],
            extended_paths,
            "tester",
        )
        self.assertEqual(again["summary"][0]["outcome"], "reused")
        self.assertEqual(again["summary"][0]["newly_linked"], 1)
        self.assertEqual(self.db.query(MolecularLibraryResultPackage).count(), 1)
        self.assertEqual(
            [item["original_name"] for item in service.list_files(self.db, first["id"])["items"]].count("C123_M13F.seq"),
            1,
        )
        self.assertEqual(
            [item["original_name"] for item in service.list_files(self.db, second["id"])["items"]],
            ["C456_M13F.seq"],
        )
        seq_files = [
            path
            for path in (self.repo / "uploads" / "library_results" / "sequencing").rglob("*")
            if path.is_file() and path.name.startswith("C123_M13F")
        ]
        self.assertEqual(len(seq_files), 1)

    def test_reuploading_the_original_after_an_addition_stays_in_the_package(self):
        order = self._barcode_order("C123", i5_sequence="AAAA")
        self._barcode_order("C456", i5_sequence="CCCC")
        base = {
            "pkg/测序结果/C123_M13F.seq": _read("AAAA"),
            "pkg/拼接结果/assembled.txt": b"assembled",
            "pkg/去载体序列/trimmed.txt": b"trimmed",
        }

        def upload(files):
            return service.upload_batch(
                self.db,
                [
                    UploadFile(filename=path.rsplit("/", 1)[1], file=io.BytesIO(content))
                    for path, content in files.items()
                ],
                list(files),
                "tester",
            )

        upload(base)
        upload({**base, "pkg/测序结果/C456_M13F.seq": _read("CCCC")})
        again = upload(base)
        self.assertEqual(again["summary"][0]["outcome"], "already")
        self.assertEqual(self.db.query(MolecularLibraryResultPackage).count(), 1)
        self.assertEqual(len(service.list_files(self.db, order["id"])["items"]), 1)

    def test_same_name_with_different_paths_stays_a_separate_package(self):
        self._barcode_order("C123", i5_sequence="AAAA")
        self._barcode_order("C456", i5_sequence="CCCC")
        service.upload_batch(
            self.db,
            [
                UploadFile(filename="C123_M13F.seq", file=io.BytesIO(b"TTTT")),
                UploadFile(filename="assembled.txt", file=io.BytesIO(b"assembled")),
                UploadFile(filename="trimmed.txt", file=io.BytesIO(b"trimmed")),
                UploadFile(filename="明细表.xlsx", file=io.BytesIO(b"sheet")),
            ],
            [
                "pkg/测序结果/C123_M13F.seq",
                "pkg/拼接结果/assembled.txt",
                "pkg/去载体序列/trimmed.txt",
                "pkg/明细表.xlsx",
            ],
            "tester",
        )
        second = service.upload_batch(
            self.db,
            [
                UploadFile(filename="C456_M13F.seq", file=io.BytesIO(b"GGGG")),
                UploadFile(filename="assembled.txt", file=io.BytesIO(b"other")),
                UploadFile(filename="trimmed.txt", file=io.BytesIO(b"other")),
                UploadFile(filename="明细表.xlsx", file=io.BytesIO(b"sheet")),
            ],
            [
                "pkg/测序结果/C456_M13F.seq",
                "pkg/拼接结果/assembled.txt",
                "pkg/去载体序列/trimmed.txt",
                "pkg/明细表.xlsx",
            ],
            "tester",
        )
        self.assertEqual(second["summary"][0]["outcome"], "stored")
        self.assertEqual(self.db.query(MolecularLibraryResultPackage).count(), 2)

    def test_qc_page_adds_own_reads_to_a_package_owned_by_another_order(self):
        first = self._barcode_order("C111", i5_sequence="AAAA")
        second = self._barcode_order("C222", i5_sequence="CCCC")
        paths = [
            "pkg/测序结果/C999-1_M13F.seq",
            "pkg/明细表.xlsx",
        ]
        pinned = service.upload_batch(
            self.db,
            [
                UploadFile(filename="C999-1_M13F.seq", file=io.BytesIO(b"ATGC")),
                UploadFile(filename="明细表.xlsx", file=io.BytesIO(b"sheet")),
            ],
            paths,
            "tester",
            first["id"],
        )
        self.assertEqual(pinned["summary"][0]["outcome"], "pinned")
        extended = service.upload_batch(
            self.db,
            [
                UploadFile(filename="C999-1_M13F.seq", file=io.BytesIO(b"ATGC")),
                UploadFile(filename="明细表.xlsx", file=io.BytesIO(b"sheet")),
                UploadFile(filename="C222_M13F.seq", file=io.BytesIO(_read("CCCC"))),
            ],
            paths + ["pkg/测序结果/C222_M13F.seq"],
            "tester",
            second["id"],
        )
        self.assertEqual(extended["summary"][0]["outcome"], "reused")
        self.assertEqual(self.db.query(MolecularLibraryResultPackage).count(), 1)
        self.assertEqual(len(service.list_files(self.db, second["id"])["items"]), 1)
        self.assertEqual(len(service.list_files(self.db, first["id"])["packages"]), 1)
        package = self.db.query(MolecularLibraryResultPackage).one()
        self.assertEqual(package.owner_order_id, first["id"])

    def test_shared_package_delete_only_unlinks_current_order(self):
        first = self._barcode_order("C123", i5_sequence="AAAA")
        second = self._barcode_order("C456", i5_sequence="CCCC")
        result = service.upload_batch(
            self.db,
            [
                UploadFile(filename="C123_M13F.seq", file=io.BytesIO(b"TTTT")),
                UploadFile(filename="C456_M13F.seq", file=io.BytesIO(b"GGGG")),
                UploadFile(filename="assembled.txt", file=io.BytesIO(b"assembled")),
                UploadFile(filename="trimmed.txt", file=io.BytesIO(b"trimmed")),
            ],
            [
                "pkg/测序结果/C123_M13F.seq",
                "pkg/测序结果/C456_M13F.seq",
                "pkg/拼接结果/assembled.txt",
                "pkg/去载体序列/trimmed.txt",
            ],
            "tester",
        )
        package_id = result["summary"][0]["id"]
        removed = service.delete_package(self.db, first["id"], package_id)
        self.assertFalse(removed["package_deleted"])
        self.assertEqual(service.list_files(self.db, first["id"])["packages"], [])
        self.assertEqual(service.list_files(self.db, second["id"])["packages"][0]["id"], package_id)
        self.assertIsNotNone(self.db.get(MolecularLibraryResultPackage, package_id))

    def test_final_copy_only_replaces_files_with_the_same_name(self):
        order = self._barcode_order("C123", i5_sequence="AAAA", i7_sequence="CCCC")
        self._upload("C123.png", b"gel", order["id"])
        first = self._upload("C123_M13F.seq", b"GGGGGGGG", order["id"])
        redo = self._upload("C123_M13F.seq", _read("AAAA"), order["id"])
        self._upload("C123_M13R.seq", _read("CCCC", "R"), order["id"])

        def status():
            return self.db.get(MolecularLibraryOrder, order["id"]).status

        self.assertEqual(status(), service.STATUS_QC_HOLD)
        service.update_file_link(self.db, first["id"], order["id"], {"is_final_qc": True})
        self.assertEqual(status(), service.STATUS_QC_HOLD)
        service.update_file_link(self.db, redo["id"], order["id"], {"is_final_qc": True})
        self.assertEqual(status(), service.STATUS_QC_PASS)
        items = {item["id"]: item for item in service.list_files(self.db, order["id"])["items"]}
        self.assertFalse(items[first["id"]]["is_final_qc"])
        self.assertTrue(items[first["id"]]["replaced"])
        self.assertFalse(items[redo["id"]]["replaced"])
        service.update_file_link(self.db, redo["id"], order["id"], {"is_final_qc": False})
        self.assertEqual(status(), service.STATUS_QC_HOLD)

    def test_reupload_keeps_the_name_and_final_mark_already_set(self):
        order = self._barcode_order("C123", i5_sequence="AAAA")
        gel = self._upload("C123.png", b"gel", order["id"])
        service.update_file_link(
            self.db,
            gel["id"],
            order["id"],
            {"original_name": "C123-final.png", "is_final_qc": True},
        )
        again = self._upload("C123-copy.png", b"gel", order["id"])
        self.assertEqual(again["id"], gel["id"])
        self.assertEqual(again["original_name"], "C123-final.png")
        self.assertTrue(again["is_final_qc"])

        files = {
            "pkg/测序结果/C123_M13F.seq": _read("AAAA"),
            "pkg/拼接结果/assembled.txt": b"assembled",
            "pkg/去载体序列/trimmed.txt": b"trimmed",
        }

        def upload_package():
            return service.upload_batch(
                self.db,
                [
                    UploadFile(filename=path.rsplit("/", 1)[1], file=io.BytesIO(content))
                    for path, content in files.items()
                ],
                list(files),
                "tester",
            )

        upload_package()
        read = next(
            item for item in service.list_files(self.db, order["id"])["items"]
            if item["package_id"]
        )
        service.update_file_link(
            self.db,
            read["id"],
            order["id"],
            {"original_name": "C123_M13F_redo.seq"},
        )
        self.assertEqual(upload_package()["summary"][0]["outcome"], "already")
        names = {item["id"]: item["original_name"] for item in service.list_files(self.db, order["id"])["items"]}
        self.assertEqual(names[read["id"]], "C123_M13F_redo.seq")

    def test_unlinking_a_package_file_keeps_it_in_the_package(self):
        order = self._barcode_order("C123", i5_sequence="AAAA")
        service.upload_batch(
            self.db,
            [
                UploadFile(filename="C123-1_M13F.seq", file=io.BytesIO(_read("AAAA"))),
                UploadFile(filename="C123-2_M13F.seq", file=io.BytesIO(_read("AAAA"))),
                UploadFile(filename="assembled.txt", file=io.BytesIO(b"assembled")),
                UploadFile(filename="trimmed.txt", file=io.BytesIO(b"trimmed")),
            ],
            [
                "pkg/测序结果/C123-1_M13F.seq",
                "pkg/测序结果/C123-2_M13F.seq",
                "pkg/拼接结果/assembled.txt",
                "pkg/去载体序列/trimmed.txt",
            ],
            "tester",
        )
        listed = service.list_files(self.db, order["id"])
        target = next(item for item in listed["items"] if item["original_name"] == "C123-1_M13F.seq")
        link = self.db.get(MolecularLibraryResultLink, target["id"])
        record = self.db.get(MolecularLibraryResultFile, link.file_id)
        disk = self.repo / "uploads" / record.storage_path.lstrip("/")
        removed = service.delete_file(self.db, target["id"], order["id"])
        self.assertFalse(removed["file_deleted"])
        self.assertIsNone(self.db.get(MolecularLibraryResultLink, target["id"]))
        self.assertIsNotNone(self.db.get(MolecularLibraryResultFile, record.id))
        self.assertTrue(disk.exists())
        self.assertEqual(self.db.query(MolecularLibraryResultPackage).count(), 1)
        again = service.list_files(self.db, order["id"])
        self.assertEqual(
            {item["original_name"] for item in again["items"]},
            {"C123-2_M13F.seq"},
        )
        stored = {item["original_name"]: item["for_qc"] for item in again["packages"][0]["files"]}
        self.assertFalse(stored["C123-1_M13F.seq"])
        self.assertTrue(stored["C123-2_M13F.seq"])
        self.assertFalse(stored["assembled.txt"])

    def test_folder_preview_delete_removes_the_file_from_every_order(self):
        order = self._barcode_order("C123", i5_sequence="AAAA")
        other = self._barcode_order("C456")
        service.upload_batch(
            self.db,
            [
                UploadFile(filename="C123_M13F.seq", file=io.BytesIO(_read("AAAA"))),
                UploadFile(filename="assembled.txt", file=io.BytesIO(b"assembled")),
            ],
            [
                "pkg/测序结果/C123_M13F.seq",
                "pkg/拼接结果/assembled.txt",
            ],
            "tester",
        )
        listed = service.list_files(self.db, order["id"])
        target = listed["items"][0]
        link = self.db.get(MolecularLibraryResultLink, target["id"])
        record = self.db.get(MolecularLibraryResultFile, link.file_id)
        self.db.add(MolecularLibraryResultLink(
            file_id=record.id,
            order_id=other["id"],
            original_name=target["original_name"],
        ))
        self.db.commit()
        disk = self.repo / "uploads" / record.storage_path.lstrip("/")
        removed = service.delete_stored_file(self.db, order["id"], record.id)
        self.assertTrue(removed["file_deleted"])
        self.assertFalse(disk.exists())
        self.assertIsNone(self.db.get(MolecularLibraryResultFile, record.id))
        self.assertEqual(self.db.query(MolecularLibraryResultLink).count(), 0)
        self.assertEqual(self.db.query(MolecularLibraryResultPackage).count(), 1)
        remaining = list(self.db.scalars(select(MolecularLibraryResultFile)).all())
        self.assertEqual([item.relative_path for item in remaining], ["拼接结果/assembled.txt"])
        self.assertEqual(service.list_files(self.db, order["id"])["items"], [])
        self.assertEqual(service.list_files(self.db, other["id"])["items"], [])

    def test_primer_change_rechecks_existing_sequence(self):
        order = self._barcode_order("C123", i5_sequence="AAAA")
        self._upload("C123.png", b"gel", order["id"])
        self._upload("C123_M13F.seq", _read("AAAA"), order["id"])
        self.assertEqual(
            self.db.get(MolecularLibraryOrder, order["id"]).status,
            service.STATUS_QC_PASS,
        )
        service.save(
            self.db,
            {"id": order["id"], "i5_sequence": "CCCC"},
        )
        changed = self.db.get(MolecularLibraryOrder, order["id"])
        self.assertEqual(changed.status, service.STATUS_QC_HOLD)
        link = self.db.scalar(
            select(MolecularLibraryResultLink).where(
                MolecularLibraryResultLink.order_id == order["id"],
                MolecularLibraryResultLink.sequence_target == "i5",
            )
        )
        self.assertEqual(link.sequence_status, "arm_only")

    def test_opening_qc_page_refreshes_stale_sequence_check(self):
        order = self._barcode_order(
            "C123",
            index_mode=service.INDEX_I5,
            i5_sequence="AAAA",
        )
        self._upload("C123.png", b"gel", order["id"])
        uploaded = self._upload("C123_M13F.seq", _read("AAAA"), order["id"])
        paths = [
            "pkg/测序结果/C123_M13F.seq",
            "pkg/拼接结果/assembled.txt",
            "pkg/去载体序列/trimmed.txt",
        ]
        service.upload_batch(
            self.db,
            [
                UploadFile(filename="C123_M13F.seq", file=io.BytesIO(_read("AAAA"))),
                UploadFile(filename="assembled.txt", file=io.BytesIO(b"assembled")),
                UploadFile(filename="trimmed.txt", file=io.BytesIO(b"trimmed")),
            ],
            paths,
            "tester",
            order["id"],
        )
        fresh = uploaded["sequence_status"]
        links = self.db.scalars(
            select(MolecularLibraryResultLink).where(
                MolecularLibraryResultLink.order_id == order["id"],
                MolecularLibraryResultLink.original_name == "C123_M13F.seq",
            )
        ).all()
        self.assertEqual(len(links), 2)
        for link in links:
            link.sequence_status = "not_found"
        self.db.commit()
        service._advance_order_status(self.db, self.db.get(MolecularLibraryOrder, order["id"]))
        self.db.commit()
        self.assertEqual(
            self.db.get(MolecularLibraryOrder, order["id"]).status,
            service.STATUS_QC_HOLD,
        )

        listed = service.list_files(self.db, order["id"])
        visible = [
            item["sequence_status"]
            for item in listed["items"]
            if item["original_name"] == "C123_M13F.seq"
        ]
        packaged = [
            item["sequence_status"]
            for item in listed["packages"][0]["files"]
            if item["original_name"] == "C123_M13F.seq"
        ]
        self.assertEqual(visible, [fresh, fresh])
        self.assertEqual(packaged, [fresh])
        self.assertEqual(listed["order"]["status"], service.STATUS_QC_PASS)
        self.db.expire_all()
        stored = self.db.scalars(
            select(MolecularLibraryResultLink.sequence_status).where(
                MolecularLibraryResultLink.order_id == order["id"],
                MolecularLibraryResultLink.original_name == "C123_M13F.seq",
            )
        ).all()
        self.assertEqual(set(stored), {fresh})
        self.assertEqual(
            self.db.get(MolecularLibraryOrder, order["id"]).status,
            service.STATUS_QC_PASS,
        )

    def test_hkl_primer_change_rechecks_existing_sequence(self):
        forward = MolecularPrimerIndexCatalog(
            name="H-old",
            family="UDP",
            direction="F",
            short_sequence="AAAA",
            active=True,
        )
        replacement = MolecularPrimerIndexCatalog(
            name="H-new",
            family="UDP",
            direction="F",
            short_sequence="CCCC",
            active=True,
        )
        self.db.add_all([forward, replacement])
        self.db.commit()
        order = service.save(
            self.db,
            {
                "build_type": service.BUILD_POOLED_BCR,
                "library_code": "C223",
                "h_forward_primer_id": forward.id,
            },
        )
        self._upload("C223.png", b"gel", order["id"])
        self._upload("HC223-1_M13F.seq", _read("AAAA"), order["id"])
        self.assertEqual(
            self.db.get(MolecularLibraryOrder, order["id"]).status,
            service.STATUS_QC_PASS,
        )
        service.save(
            self.db,
            {"id": order["id"], "h_forward_primer_id": replacement.id},
        )
        changed = self.db.get(MolecularLibraryOrder, order["id"])
        self.assertEqual(changed.status, service.STATUS_QC_HOLD)
        link = self.db.scalar(
            select(MolecularLibraryResultLink).where(
                MolecularLibraryResultLink.order_id == order["id"],
                MolecularLibraryResultLink.sequence_target == "hF",
            )
        )
        self.assertEqual(link.sequence_status, "arm_only")

    def test_qc_page_pins_unmatched_package_without_file_tiles(self):
        result = service.upload_batch(
            self.db,
            [
                UploadFile(filename="C999-1_M13F.seq", file=io.BytesIO(b"ATGC")),
                UploadFile(filename="明细表.xlsx", file=io.BytesIO(b"sheet")),
            ],
            ["pkg/测序结果/C999-1_M13F.seq", "pkg/明细表.xlsx"],
            "tester",
            self.order["id"],
        )
        self.assertEqual(result["items"], [])
        self.assertEqual(result["summary"][0]["outcome"], "pinned")
        listed = service.list_files(self.db, self.order["id"])
        self.assertEqual(listed["packages"][0]["name"], "pkg")
        self.assertEqual(listed["packages"][0]["qc_count"], 0)
        self.assertEqual(listed["items"], [])
        package = self.db.get(MolecularLibraryResultPackage, listed["packages"][0]["id"])
        self.assertRegex(package.storage_prefix, r"--[0-9a-f]{8}$")
        self.assertNotRegex(package.storage_prefix, r"--[0-9a-f]{9,}$")
        self.db.connection().exec_driver_sql("PRAGMA foreign_keys=ON")
        deleted = service.delete_package(self.db, self.order["id"], listed["packages"][0]["id"])
        self.assertTrue(deleted["package_deleted"])
        after = service.list_files(self.db, self.order["id"])
        self.assertEqual(after["packages"], [])
        self.assertEqual(after["items"], [])

    def test_qc_page_package_stays_on_current_order_even_if_codes_match_others(self):
        current = self._barcode_order("C456", i5_sequence="CCCC")
        other = self._barcode_order("C123", i5_sequence="AAAA")
        result = service.upload_batch(
            self.db,
            [
                UploadFile(filename="C123-1_M13F.seq", file=io.BytesIO(b"ATGC")),
                UploadFile(filename="C456-1_M13F.seq", file=io.BytesIO(b"TTTT")),
                UploadFile(filename="明细表.xlsx", file=io.BytesIO(b"sheet")),
            ],
            [
                "pkg/测序结果/C123-1_M13F.seq",
                "pkg/测序结果/C456-1_M13F.seq",
                "pkg/明细表.xlsx",
            ],
            "tester",
            current["id"],
        )
        self.assertEqual(result["summary"][0]["outcome"], "stored")
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["order_id"], current["id"])
        self.assertEqual(result["items"][0]["original_name"], "C456-1_M13F.seq")
        self.assertEqual(service.list_files(self.db, other["id"])["packages"], [])
        self.assertEqual(service.list_files(self.db, other["id"])["items"], [])
        listed = service.list_files(self.db, current["id"])
        self.assertEqual(listed["packages"][0]["name"], "pkg")
        self.assertEqual(listed["packages"][0]["qc_count"], 1)
        package = self.db.get(MolecularLibraryResultPackage, listed["packages"][0]["id"])
        self.assertEqual(package.owner_order_id, current["id"])

    def test_qc_page_rejects_package_already_pinned_to_another_order(self):
        first = self._barcode_order("C111", i5_sequence="AAAA")
        second = self._barcode_order("C222", i5_sequence="CCCC")
        files = [
            UploadFile(filename="C999-1_M13F.seq", file=io.BytesIO(b"ATGC")),
            UploadFile(filename="明细表.xlsx", file=io.BytesIO(b"sheet")),
        ]
        paths = ["pkg/测序结果/C999-1_M13F.seq", "pkg/明细表.xlsx"]
        first_result = service.upload_batch(self.db, files, paths, "tester", first["id"])
        self.assertEqual(first_result["summary"][0]["outcome"], "pinned")
        second_files = [
            UploadFile(filename="C999-1_M13F.seq", file=io.BytesIO(b"ATGC")),
            UploadFile(filename="明细表.xlsx", file=io.BytesIO(b"sheet")),
        ]
        second_result = service.upload_batch(
            self.db, second_files, paths, "tester", second["id"]
        )
        self.assertEqual(second_result["items"], [])
        self.assertEqual(second_result["summary"][0]["outcome"], "skipped")
        self.assertIn("已挂在其他工单", second_result["summary"][0]["issues"][0]["reason"])
        self.assertEqual(service.list_files(self.db, second["id"])["packages"], [])
        self.assertEqual(len(service.list_files(self.db, first["id"])["packages"]), 1)

    def test_batch_shared_package_can_be_owned_by_one_qc_order(self):
        first = self._barcode_order("C111", i5_sequence="AAAA")
        second = self._barcode_order("C222", i5_sequence="CCCC")
        paths = [
            "pkg/测序结果/C111_M13F.seq",
            "pkg/测序结果/C222_M13F.seq",
            "pkg/拼接结果/assembled.txt",
            "pkg/去载体序列/trimmed.txt",
        ]

        def files():
            return [
                UploadFile(filename="C111_M13F.seq", file=io.BytesIO(b"TTTT")),
                UploadFile(filename="C222_M13F.seq", file=io.BytesIO(b"GGGG")),
                UploadFile(filename="assembled.txt", file=io.BytesIO(b"assembled")),
                UploadFile(filename="trimmed.txt", file=io.BytesIO(b"trimmed")),
            ]

        shared = service.upload_batch(self.db, files(), paths, "tester")
        package_id = shared["summary"][0]["id"]
        package = self.db.get(MolecularLibraryResultPackage, package_id)
        self.assertIsNone(package.owner_order_id)

        owned = service.upload_batch(self.db, files(), paths, "tester", first["id"])
        self.assertEqual(owned["summary"][0]["outcome"], "pinned")
        self.assertEqual(package.owner_order_id, first["id"])
        self.assertEqual(service.list_files(self.db, second["id"])["packages"][0]["id"], package_id)

        again = service.upload_batch(self.db, files(), paths, "tester", second["id"])
        self.assertEqual(again["summary"][0]["outcome"], "already")
        self.assertEqual(package.owner_order_id, first["id"])

    def test_same_named_loose_sequences_remain_separate(self):
        order = self._barcode_order("C123", i5_sequence="AAAA")
        self._upload("C123.png", b"gel", order["id"])
        self._upload("C123_M13F.seq", b"GGGG", order["id"])
        original_link = self.db.scalar(
            select(MolecularLibraryResultLink).where(
                MolecularLibraryResultLink.order_id == order["id"],
                MolecularLibraryResultLink.original_name == "C123_M13F.seq",
            )
        )
        original_record = self.db.get(MolecularLibraryResultFile, original_link.file_id)
        original_record_id = original_record.id
        original_path = self.repo / "uploads" / original_record.storage_path.lstrip("/")
        self.assertTrue(original_path.exists())
        self.assertEqual(
            self.db.get(MolecularLibraryOrder, order["id"]).status,
            service.STATUS_QC_HOLD,
        )

        corrected = self._upload("C123_M13F.seq", _read("AAAA"), order["id"])
        self.assertEqual(corrected["sequence_status"], "matched")
        self.assertEqual(
            self.db.get(MolecularLibraryOrder, order["id"]).status,
            service.STATUS_QC_HOLD,
        )
        visible = service.list_files(self.db, order["id"])["items"]
        self.assertEqual(
            [item["original_name"] for item in visible].count("C123_M13F.seq"),
            2,
        )
        links = self.db.scalars(
            select(MolecularLibraryResultLink).where(
                MolecularLibraryResultLink.order_id == order["id"],
                MolecularLibraryResultLink.original_name == "C123_M13F.seq",
            )
        ).all()
        self.assertEqual(len(links), 2)
        self.assertIn(original_record_id, {link.file_id for link in links})
        self.assertIsNotNone(self.db.get(MolecularLibraryResultFile, original_record_id))
        self.assertTrue(original_path.exists())

    def test_same_named_reads_in_different_packages_stay_visible(self):
        order = self._barcode_order("C123", i5_sequence="AAAA")

        def package(root, sequence):
            paths = [
                f"{root}/测序结果/C123_M13F.seq",
                f"{root}/拼接结果/assembled.txt",
                f"{root}/去载体序列/trimmed.txt",
            ]
            files = [
                UploadFile(filename="C123_M13F.seq", file=io.BytesIO(sequence)),
                UploadFile(filename="assembled.txt", file=io.BytesIO(b"assembled")),
                UploadFile(filename="trimmed.txt", file=io.BytesIO(b"trimmed")),
            ]
            return files, paths

        first_files, first_paths = package("pkg-one", b"TTTT")
        service.upload_batch(self.db, first_files, first_paths, "tester")
        second_files, second_paths = package("pkg-two", b"GGGG")
        service.upload_batch(self.db, second_files, second_paths, "tester")

        listed = service.list_files(self.db, order["id"])
        self.assertEqual(len(listed["packages"]), 2)
        self.assertEqual(
            [item["original_name"] for item in listed["items"]].count("C123_M13F.seq"),
            2,
        )

        repeated_files, repeated_paths = package("pkg-one", b"TTTT")
        repeated = service.upload_batch(
            self.db,
            repeated_files,
            repeated_paths,
            "tester",
        )
        self.assertEqual(repeated["summary"][0]["outcome"], "already")
        self.assertEqual(len(service.list_files(self.db, order["id"])["packages"]), 2)

    def test_orders_without_primers_skip_sequence_check(self):
        order = service.save(
            self.db,
            {
                "build_type": service.BUILD_POOLED_BARCODE,
                "library_code": "C123",
                "index_mode": service.INDEX_NONE,
            },
        )
        uploaded = self._upload("C123_M13F.seq", _read("AAAA"), order["id"])
        self.assertIsNone(uploaded["sequence_status"])
        self._upload("C123.png", b"gel", order["id"])
        self.assertEqual(
            self.db.get(MolecularLibraryOrder, order["id"]).status,
            service.STATUS_QC_PASS,
        )
        self.assertEqual(service._qc_order_rows(self.db, {order["id"]})[0]["detail"], "")

    def test_matching_arms_with_wrong_primer_are_reported_separately(self):
        order = self._barcode_order("C123", i5_sequence="AAAA", i7_sequence="TTTT")
        uploaded = self._upload("C123_M13F.seq", _read("CCCC"), order["id"])
        self.assertEqual(uploaded["sequence_status"], "arm_only")
        self.assertEqual(uploaded["sequence_check"], "i5 引物错误")
        flipped = self._upload(
            "C123-2_M13F.seq",
            _long_enough(f"NN{primer_check_sequence(assembled_primer('CCCC', 'F'))}NN"),
            order["id"],
        )
        self.assertEqual(flipped["sequence_status"], "arm_only_rc")
        self.assertEqual(flipped["sequence_check"], "i5 引物错误-反补")
        expected_reverse = self._upload("C123_M13R.seq", _read("TTTT", "R"), order["id"])
        self.assertEqual(expected_reverse["sequence_check"], "i7 匹配")
        flipped_reverse = self._upload(
            "C123-2_M13R.seq",
            _long_enough(f"NN{primer_check_sequence(assembled_primer('TTTT', 'R'))}NN"),
            order["id"],
        )
        self.assertEqual(flipped_reverse["sequence_status"], "matched_rc")
        self.assertEqual(flipped_reverse["sequence_check"], "i7 匹配-反补")
        self.assertEqual(
            self.db.get(MolecularLibraryOrder, order["id"]).status,
            service.STATUS_QC_HOLD,
        )

    def test_reads_of_400_bases_or_fewer_keep_the_result_and_mark_short(self):
        order = self._barcode_order("C123", i5_sequence="AAAA", i7_sequence="TTTT")
        short = f"NN{assembled_primer('AAAA', 'F')}NN"
        uploaded = self._upload("C123_M13F.seq", short.encode(), order["id"])
        self.assertEqual(uploaded["sequence_status"], "matched_short")
        self.assertEqual(uploaded["sequence_check"], "i5 匹配-过短")

        boundary = short + ("N" * (400 - len(short)))
        exactly = self._upload("C123-2_M13F.seq", boundary.encode(), order["id"])
        self.assertEqual(exactly["sequence_status"], "matched_short")
        self.assertEqual(exactly["sequence_check"], "i5 匹配-过短")

        longer = self._upload("C123-3_M13F.seq", _read("AAAA"), order["id"])
        self.assertEqual(longer["sequence_status"], "matched")
        self.assertEqual(longer["sequence_check"], "i5 匹配")

        spaced = self._upload(
            "C123-4_M13F.seq",
            f"{short}\n{' 12 ' * 30}".encode(),
            order["id"],
        )
        self.assertEqual(spaced["sequence_status"], "matched_short")
        self.assertEqual(spaced["sequence_check"], "i5 匹配-过短")

        flipped = f"NN{primer_check_sequence(assembled_primer('TTTT', 'R'))}NN"
        marked = self._upload("C123_M13R.seq", flipped.encode(), order["id"])
        self.assertEqual(marked["sequence_status"], "matched_rc_short")
        self.assertEqual(marked["sequence_check"], "i7 匹配-反补-过短")

    def test_short_read_holds_qc_when_every_primer_matches(self):
        order = self._barcode_order("C123", i5_sequence="AAAA")
        self._upload("C123.png", b"gel", order["id"])
        self._upload("C123-1_M13F.seq", _read("AAAA"), order["id"])
        self.assertEqual(
            self.db.get(MolecularLibraryOrder, order["id"]).status,
            service.STATUS_QC_PASS,
        )
        short = self._upload(
            "C123-2_M13F.seq",
            f"NN{assembled_primer('AAAA', 'F')}NN".encode(),
            order["id"],
        )
        self.assertEqual(short["sequence_check"], "i5 匹配-过短")
        held = self.db.get(MolecularLibraryOrder, order["id"])
        self.assertEqual(held.status, service.STATUS_QC_HOLD)
        self.assertEqual(
            service._qc_order_rows(self.db, {order["id"]})[0]["detail"],
            "读段过短",
        )
        service.save(self.db, {"id": order["id"], "qc_result": service.QC_PASS})
        self.assertEqual(
            self.db.get(MolecularLibraryOrder, order["id"]).status,
            service.STATUS_QC_PASS,
        )

    def test_short_read_waits_until_every_configured_primer_is_present(self):
        order = self._barcode_order("C123", i5_sequence="AAAA", i7_sequence="TTTT")
        self._upload("C123.png", b"gel", order["id"])
        self._upload(
            "C123_M13F.seq",
            f"NN{assembled_primer('AAAA', 'F')}NN".encode(),
            order["id"],
        )
        self.assertEqual(
            self.db.get(MolecularLibraryOrder, order["id"]).status,
            service.STATUS_WAIT_QC,
        )
        self.assertEqual(
            service._qc_order_rows(self.db, {order["id"]})[0]["detail"],
            "引物还没对全",
        )
        self._upload("C123_M13R.seq", _read("TTTT", "R"), order["id"])
        self.assertEqual(
            self.db.get(MolecularLibraryOrder, order["id"]).status,
            service.STATUS_QC_HOLD,
        )
        self.assertEqual(
            service._qc_order_rows(self.db, {order["id"]})[0]["detail"],
            "读段过短",
        )

    def test_hkl_chain_is_the_prefix_before_the_library_code(self):
        forward = MolecularPrimerIndexCatalog(
            name="H-F",
            family="UDP",
            direction="F",
            short_sequence="AAAA",
            active=True,
        )
        reverse = MolecularPrimerIndexCatalog(
            name="K-F",
            family="UDP",
            direction="F",
            short_sequence="CCCC",
            active=True,
        )
        self.db.add_all([forward, reverse])
        self.db.commit()
        order = service.save(
            self.db,
            {
                "build_type": service.BUILD_POOLED_BCR,
                "library_code": "C223",
                "h_forward_primer_id": forward.id,
                "k_forward_primer_id": reverse.id,
            },
        )
        matched = self._upload("HC223-1_M13F.seq", _read("AAAA"), order["id"])
        self.assertEqual(matched["sequence_target"], "hF")
        self.assertEqual(matched["sequence_status"], "matched")
        self.assertEqual(
            service.list_files(self.db, order["id"])["primer_sequences"],
            {"hF": "AAAA", "kF": "CCCC"},
        )
        shown = _long_enough(f"NN{FORWARD_ARM_1}AAAA{FORWARD_ARM_2}NN")
        display_only = self._upload("HC223-2_M13F.seq", shown, order["id"])
        self.assertEqual(display_only["sequence_status"], "arm_only")
        flipped = _long_enough(f"NN{primer_check_sequence(assembled_primer('AAAA', 'F'))}NN")
        other_strand = self._upload("HC223-3_M13F.seq", flipped, order["id"])
        self.assertEqual(other_strand["sequence_status"], "matched_rc")
        self.assertEqual(other_strand["sequence_check"], "H链正向 匹配-反补")
        other = self._upload("KC223-1_M13F.seq", _read("AAAA"), order["id"])
        self.assertEqual(other["sequence_target"], "kF")
        self.assertEqual(other["sequence_status"], "arm_only")
        old_style = self._upload("C223-H-1_M13F.seq", _read("AAAA"), order["id"])
        self.assertIsNone(old_style["sequence_status"])
        unmarked = self._upload("C223-1_M13F.seq", _read("AAAA"), order["id"])
        self.assertIsNone(unmarked["sequence_status"])


if __name__ == "__main__":
    unittest.main()
