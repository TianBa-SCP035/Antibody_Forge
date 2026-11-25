"""免疫抗原活性验证：判定、图片和抗原旁的汇总。"""

import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from core.config import get_settings
from core.errors import NotFoundError
from models.immunology import SerumAntigenCheck, SerumImmAntigen
from models.system import SysFeatureFlag
from modules.immunology.workbench import antigen_check
from support import DbTestCase

PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


class FakeUpload:
    def __init__(self, name, content):
        self.filename = name
        self.file = BytesIO(content)


class AntigenCheckTests(DbTestCase):
    tables = (SerumImmAntigen, SerumAntigenCheck, SysFeatureFlag)

    def setUp(self):
        super().setUp()
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root_patch = patch.object(get_settings(), "repository_root", temp_dir.name)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        self.first = SerumImmAntigen(experiment_id="E1", antigen_id="1", antigen_name="PD1-His")
        self.second = SerumImmAntigen(experiment_id="E1", antigen_id="2", antigen_name="PD1-Fc")
        self.db.add_all([self.first, self.second])
        self.db.commit()

    def _summary(self, antigen_row_id):
        items = antigen_check.experiment_summaries(self.db, "E1")
        return next(item for item in items if item["antigen_row_id"] == antigen_row_id)

    def test_results_and_summary(self):
        detail = antigen_check.detail(self.db, self.first.id)
        self.assertEqual([item["assay"] for item in detail["items"]], list(antigen_check.ASSAYS))
        self.assertIsNone(detail["summary"]["result"])

        detail = antigen_check.save_result(self.db, self.first.id, "SEC-HPLC", "是", "李婉绮")
        self.assertEqual(detail["items"][0]["qualified"], "是")
        self.assertEqual(detail["items"][0]["updated_by"], "李婉绮")
        self.assertEqual(self._summary(self.first.id)["result"], "是")
        self.assertEqual(self._summary(self.first.id)["judged"], 1)

        antigen_check.save_result(self.db, self.first.id, "ELISA", "否", "李婉绮")
        self.assertEqual(self._summary(self.first.id)["result"], "否")
        antigen_check.save_result(self.db, self.first.id, "ELISA", "", "李婉绮")
        self.assertEqual(self._summary(self.first.id), {
            "antigen_row_id": self.first.id, "result": "是", "judged": 1, "total": 5,
        })
        self.assertIsNone(self._summary(self.second.id)["result"])

        with self.assertRaisesRegex(ValueError, "验证项目不正确"):
            antigen_check.save_result(self.db, self.first.id, "WB", "是", "李婉绮")
        with self.assertRaisesRegex(ValueError, "判定只能选"):
            antigen_check.save_result(self.db, self.first.id, "FACS", "合格", "李婉绮")
        with self.assertRaises(NotFoundError):
            antigen_check.detail(self.db, 9999)

    def test_images_per_assay(self):
        detail = antigen_check.add_image(self.db, self.first.id, "SDS-PAGE", FakeUpload("胶图.png", PNG), "李婉绮")
        images = detail["items"][1]["images"]
        self.assertEqual(len(images), 1)
        self.assertIsNone(detail["items"][1]["qualified"])
        path, name = antigen_check.image_file(self.db, self.first.id, images[0]["file"])
        self.assertEqual(name, "胶图.png")
        self.assertEqual(Path(path).read_bytes()[:8], PNG[:8])
        with self.assertRaises(NotFoundError):
            antigen_check.image_file(self.db, self.second.id, images[0]["file"])
        with self.assertRaisesRegex(ValueError, "请上传图片"):
            antigen_check.add_image(self.db, self.first.id, "SDS-PAGE", FakeUpload("note.txt", b"abc"), "李婉绮")

        with self.assertRaises(NotFoundError):
            antigen_check.remove_image(self.db, self.first.id, "ELISA", images[0]["file"], "李婉绮")
        detail = antigen_check.remove_image(self.db, self.first.id, "SDS-PAGE", images[0]["file"], "李婉绮")
        self.assertEqual(detail["items"][1]["images"], [])
        self.assertFalse(Path(path).exists())
