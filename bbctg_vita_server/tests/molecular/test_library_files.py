"""覆盖文库结果文件上传、匹配、质检、包管理与峰图预览。"""

import io
import hashlib
import tempfile
from pathlib import Path
from unittest.mock import patch

from fastapi import BackgroundTasks, UploadFile
from sqlalchemy import select

from models.discovery import DiscoveryWorkbench
from models.molecular_cell import (
    MolecularLibraryOrder,
    MolecularLibraryResultFile,
    MolecularLibraryResultLink,
    MolecularLibraryResultPackage,
    MolecularPrimerIndexCatalog,
)
from modules.molecular_cell.library_orders import routes as order_routes
from modules.molecular_cell.library_orders import service
from modules.molecular_cell.library_orders.result_upload import (
    FORWARD_ARM_1,
    FORWARD_ARM_2,
    assembled_primer,
    primer_check_sequence,
)
from support import DbTestCase


def _long_enough(sequence: str) -> bytes:
    if len(sequence) <= 400:
        sequence += "N" * (401 - len(sequence))
    return sequence.encode()


def _read(primer, direction="F"):
    return _long_enough(f"NN{assembled_primer(primer, direction)}NN")


class _UnreadableStream(io.BytesIO):
    def read(self, *args, **kwargs):
        raise AssertionError("被预检拒绝的文件不应读取")


TABLES = (
    DiscoveryWorkbench,
    MolecularLibraryOrder,
    MolecularPrimerIndexCatalog,
    MolecularLibraryResultPackage,
    MolecularLibraryResultFile,
    MolecularLibraryResultLink,
)


class LibraryFileTests(DbTestCase):
    tables = TABLES

    def setUp(self):
        super().setUp()
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.repo = Path(self.tmpdir.name)
        self.settings_patch = patch(
            "modules.molecular_cell.library_orders.service.get_settings",
            return_value=type("S", (), {"repository_root": self.repo})(),
        )
        self.drm_patch = patch(
            "modules.molecular_cell.library_orders.service.drm_service.decrypt_upload_file_if_available"
        )
        self.settings_patch.start()
        self.addCleanup(self.settings_patch.stop)
        self.drm_mock = self.drm_patch.start()
        self.addCleanup(self.drm_patch.stop)
        self.order = service.save(
            self.db,
            {"build_type": service.BUILD_POOLED_BCR, "library_code": "CE4689"},
        )

    def test_gel_upload_waits_for_qc(self):
        order = self._barcode_order("C123", i5_sequence="AAAA", i7_sequence="CCCC")
        self._upload("C123.png", b"gel", order["id"])
        self.assertEqual(
            self.db.get(MolecularLibraryOrder, order["id"]).status,
            service.STATUS_WAIT_QC,
        )

    def test_both_primers_passing_advances_qc(self):
        order = self._barcode_order("C123", i5_sequence="AAAA", i7_sequence="CCCC")
        self._upload("C123.png", b"gel", order["id"])
        self._upload("C123_M13F.seq", _read("AAAA"), order["id"])
        self.assertEqual(
            self.db.get(MolecularLibraryOrder, order["id"]).status,
            service.STATUS_WAIT_QC,
        )
        self._upload("C123_M13R.seq", _read("CCCC", "R"), order["id"])
        self.assertEqual(
            self.db.get(MolecularLibraryOrder, order["id"]).status,
            service.STATUS_QC_PASS,
        )

    def test_trace_only_upload_does_not_downgrade_passed_qc(self):
        order = self._barcode_order("C123", i5_sequence="AAAA", i7_sequence="CCCC")
        self._upload("C123.png", b"gel", order["id"])
        self._upload("C123_M13F.seq", _read("AAAA"), order["id"])
        self._upload("C123_M13R.seq", _read("CCCC", "R"), order["id"])
        trace = self._upload("C123_M13F.ab1", b"not-a-trace", order["id"])
        self.assertEqual(trace["sequence_status"], "trace_only")
        self.assertEqual(
            self.db.get(MolecularLibraryOrder, order["id"]).status,
            service.STATUS_QC_PASS,
        )

    def test_primer_mismatch_holds_qc(self):
        order = self._barcode_order("C456", i5_sequence="AAAA")
        self._upload("C456.png", b"gel", order["id"])
        self._upload("C456_M13F.seq", b"GGGGGGGG", order["id"])
        self.assertEqual(
            self.db.get(MolecularLibraryOrder, order["id"]).status,
            service.STATUS_QC_HOLD,
        )

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
        result = self._upload_result("C123-2_M13F.seq", b"GGGGGGGG", order["id"])
        self.assertEqual(
            self.db.get(MolecularLibraryOrder, order["id"]).status,
            service.STATUS_QC_HOLD,
        )
        self.assertEqual(
            result["summary"][0]["orders"][0]["detail"],
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
        """传一个文件到指定工单；没存上时按第一条原因抛 ValueError。"""
        result = self._upload_result(name, content, order_id)
        if not result["items"]:
            reasons = [issue["reason"] for summary in result["summary"] for issue in summary.get("issues", [])]
            raise ValueError(reasons[0] if reasons else "文件未保存")
        return result["items"][0]

    def _upload_result(self, name, content, order_id=None):
        upload = UploadFile(filename=name, file=io.BytesIO(content))
        return service.upload_batch(
            self.db,
            [upload],
            [name],
            "tester",
            order_id or self.order["id"],
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
        uploaded = self._upload(original, b"trace")
        with patch.object(service, "read_trace_preview", return_value={"sample_count": 1}) as read:
            response = order_routes.file_download(
                BackgroundTasks(),
                id=uploaded["id"],
                file_id=None,
                preview=True,
                thumb=False,
                w=400,
                h=400,
                db=self.db,
            )
        self.assertEqual(response, {"sample_count": 1})
        self.assertEqual(read.call_args.args[0].suffix, ".ab1")

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

    def test_sequencing_files_are_not_hash_merged(self):
        order = self._barcode_order("C123", i5_sequence="AAAA")
        first = self._upload("C123-1_M13F.seq", b"same-seq", order["id"])
        second = self._upload("C123-2_M13F.seq", b"same-seq", order["id"])
        self.assertNotEqual(self._file_record(first).id, self._file_record(second).id)

    def test_qc_page_keeps_unmatched_file_on_current_order(self):
        uploaded = self._upload("trace.ab1", b"trace-bytes")
        record = self._file_record(uploaded)
        self.assertEqual(uploaded["order_id"], self.order["id"])
        self.assertEqual(uploaded["result_kind"], service.FILE_KIND_PRIMER_QC)
        self.assertIn("/library_results/others/", record.storage_path)
        self.assertIn(self.order["library_order_id"], record.storage_path)

    def test_targeted_upload_rejects_other_order_codes(self):
        named = self._barcode_order("C123", i5_sequence="AAAA", i7_sequence="CCCC")
        other = self._barcode_order("C456")
        with self.assertRaisesRegex(ValueError, "建库编号 C123 属于其他工单"):
            self._upload("C123-1_M13F.seq", _read("AAAA"), self.order["id"])
        with self.assertRaisesRegex(ValueError, "建库编号 C123、C456 属于其他工单"):
            self._upload("C123-C456.png", b"gel", self.order["id"])
        self.assertEqual(len(service.list_files(self.db, self.order["id"])["items"]), 0)
        self.assertEqual(len(service.list_files(self.db, named["id"])["items"]), 0)
        self.assertEqual(len(service.list_files(self.db, other["id"])["items"]), 0)
        shared = self._upload("C123-C456.png", b"gel", named["id"])
        self.assertEqual(shared["order_id"], named["id"])
        self.assertEqual(len(service.list_files(self.db, other["id"])["items"]), 0)

    def test_untargeted_upload_routes_by_library_code(self):
        named = self._barcode_order("C123", i5_sequence="AAAA", i7_sequence="CCCC")
        batched = service.upload_batch(
            self.db,
            [UploadFile(filename="C123-2_M13F.seq", file=io.BytesIO(_read("AAAA")))],
            ["C123-2_M13F.seq"],
            "tester",
        )
        self.assertEqual(batched["items"][0]["order_id"], named["id"])

    def test_filename_primer_classification_reports_match_and_trace(self):
        named = self._barcode_order("C123", i5_sequence="AAAA", i7_sequence="CCCC")
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

    def test_batch_upload_does_not_read_rejected_package_streams(self):
        self._barcode_order("C123", i5_sequence="AAAA")
        files = [
            UploadFile(filename="C123_M13F.seq", file=io.BytesIO(b"TTTT")),
            UploadFile(filename="assembled.txt", file=io.BytesIO(b"assembled")),
            UploadFile(filename="trimmed.txt", file=io.BytesIO(b"trimmed")),
            UploadFile(filename="C999_M13F.seq", file=_UnreadableStream(b"TTTT")),
            UploadFile(filename="assembled.txt", file=_UnreadableStream(b"assembled")),
            UploadFile(filename="trimmed.txt", file=_UnreadableStream(b"trimmed")),
        ]
        paths = [
            "ready/测序结果/C123_M13F.seq",
            "ready/拼接结果/assembled.txt",
            "ready/去载体序列/trimmed.txt",
            "rejected/测序结果/C999_M13F.seq",
            "rejected/拼接结果/assembled.txt",
            "rejected/去载体序列/trimmed.txt",
        ]
        result = service.upload_batch(self.db, files, paths, "tester")
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

    def test_package_missing_folder_passes_preflight_and_upload(self):
        order = self._barcode_order("C123", i5_sequence="AAAA")
        paths = [
            "pkg/测序结果/C123_M13F.seq",
            "pkg/拼接结果/assembled.txt",
        ]
        preflight = service.preflight_upload(self.db, paths)
        self.assertEqual(preflight["accepted_indexes"], [0, 1])
        self.assertEqual(preflight["summary"][0]["outcome"], "ready")
        self.assertEqual(preflight["summary"][0]["matched_codes"], ["C123"])
        result = service.upload_batch(
            self.db,
            [
                UploadFile(filename="C123_M13F.seq", file=io.BytesIO(b"TTTT")),
                UploadFile(filename="assembled.txt", file=io.BytesIO(b"assembled")),
            ],
            paths,
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

    def test_package_version_lifecycle_reuses_extension_and_original_upload(self):
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
        original = service.upload_batch(
            self.db,
            [
                UploadFile(filename="C123_M13F.seq", file=io.BytesIO(seq)),
                UploadFile(filename="assembled.txt", file=io.BytesIO(b"assembled")),
                UploadFile(filename="trimmed.txt", file=io.BytesIO(b"trimmed")),
            ],
            paths,
            "tester",
        )
        self.assertEqual(original["summary"][0]["outcome"], "already")
        self.assertEqual(self.db.query(MolecularLibraryResultPackage).count(), 1)
        self.assertEqual(len(service.list_files(self.db, first["id"])["items"]), 1)

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
        for profile in ("barcode", "hkl"):
            with self.subTest(profile=profile):
                if profile == "barcode":
                    order = self._barcode_order("C123", i5_sequence="AAAA")
                    filename = "C123_M13F.seq"
                    update = {"i5_sequence": "CCCC"}
                    target = "i5"
                else:
                    original = MolecularPrimerIndexCatalog(
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
                    self.db.add_all([original, replacement])
                    self.db.commit()
                    order = service.save(
                        self.db,
                        {
                            "build_type": service.BUILD_POOLED_BCR,
                            "library_code": "C223",
                            "h_forward_primer_id": original.id,
                        },
                    )
                    filename = "HC223-1_M13F.seq"
                    update = {"h_forward_primer_id": replacement.id}
                    target = "hF"
                self._upload(f"{order['library_code']}.png", b"gel", order["id"])
                self._upload(filename, _read("AAAA"), order["id"])
                self.assertEqual(
                    self.db.get(MolecularLibraryOrder, order["id"]).status,
                    service.STATUS_QC_PASS,
                )
                service.save(self.db, {"id": order["id"], **update})
                self.assertEqual(
                    self.db.get(MolecularLibraryOrder, order["id"]).status,
                    service.STATUS_QC_HOLD,
                )
                link = self.db.scalar(
                    select(MolecularLibraryResultLink).where(
                        MolecularLibraryResultLink.order_id == order["id"],
                        MolecularLibraryResultLink.sequence_target == target,
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
        self.db.get(MolecularLibraryOrder, order["id"]).status = service.STATUS_QC_HOLD
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
        result = self._upload_result("C123.png", b"gel", order["id"])
        self.assertEqual(
            self.db.get(MolecularLibraryOrder, order["id"]).status,
            service.STATUS_QC_PASS,
        )
        self.assertEqual(result["summary"][0]["orders"][0]["detail"], "")

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
        result = self._upload_result(
            "C123-2_M13F.seq",
            f"NN{assembled_primer('AAAA', 'F')}NN".encode(),
            order["id"],
        )
        short = result["items"][0]
        self.assertEqual(short["sequence_check"], "i5 匹配-过短")
        held = self.db.get(MolecularLibraryOrder, order["id"])
        self.assertEqual(held.status, service.STATUS_QC_HOLD)
        self.assertEqual(
            result["summary"][0]["orders"][0]["detail"],
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
        first = self._upload_result(
            "C123_M13F.seq",
            f"NN{assembled_primer('AAAA', 'F')}NN".encode(),
            order["id"],
        )
        self.assertEqual(
            self.db.get(MolecularLibraryOrder, order["id"]).status,
            service.STATUS_WAIT_QC,
        )
        self.assertEqual(
            first["summary"][0]["orders"][0]["detail"],
            "引物还没对全",
        )
        second = self._upload_result("C123_M13R.seq", _read("TTTT", "R"), order["id"])
        self.assertEqual(
            self.db.get(MolecularLibraryOrder, order["id"]).status,
            service.STATUS_QC_HOLD,
        )
        self.assertEqual(
            second["summary"][0]["orders"][0]["detail"],
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
        self.assertEqual(other_strand["sequence_check"], "H链 i5 匹配-反补")
        other = self._upload("KC223-1_M13F.seq", _read("AAAA"), order["id"])
        self.assertEqual(other["sequence_target"], "kF")
        self.assertEqual(other["sequence_status"], "arm_only")
        old_style = self._upload("C223-H-1_M13F.seq", _read("AAAA"), order["id"])
        self.assertIsNone(old_style["sequence_status"])
        unmarked = self._upload("C223-1_M13F.seq", _read("AAAA"), order["id"])
        self.assertIsNone(unmarked["sequence_status"])


