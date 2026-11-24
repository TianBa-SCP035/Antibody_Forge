"""发现工作台既往筛选文字和图片。"""

import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from core.config import get_settings
from core.errors import NotFoundError
from models.discovery import DiscoveryWorkbench
from modules.discovery.workbench import prior_screening, service
from support import DbTestCase

PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


class FakeUpload:
    def __init__(self, name, content):
        self.filename = name
        self.file = BytesIO(content)


class PriorScreeningTests(DbTestCase):
    tables = (DiscoveryWorkbench,)

    def setUp(self):
        super().setUp()
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root_patch = patch.object(get_settings(), "repository_root", temp_dir.name)
        root_patch.start()
        self.addCleanup(root_patch.stop)

    def test_text_and_images(self):
        saved = service.save(self.db, {"project_code": "P1", "prior_screening": "去年 Beacon\n今年达普"})
        self.assertEqual(saved["prior_screening"], "去年 Beacon\n今年达普")
        self.assertEqual(saved["prior_screening_images"], [])

        items = prior_screening.add_image(self.db, saved["id"], FakeUpload("结果.png", PNG))
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0]["file"].endswith(".png"))
        path, name = prior_screening.image_file(self.db, saved["id"], items[0]["file"])
        self.assertEqual(name, "结果.png")
        self.assertEqual(Path(path).read_bytes()[:8], PNG[:8])

        with self.assertRaisesRegex(ValueError, "请上传图片"):
            prior_screening.add_image(self.db, saved["id"], FakeUpload("note.txt", b"abc"))

        left = prior_screening.remove_image(self.db, saved["id"], items[0]["file"])
        self.assertEqual(left, [])
        with self.assertRaises(NotFoundError):
            prior_screening.image_file(self.db, saved["id"], items[0]["file"])
