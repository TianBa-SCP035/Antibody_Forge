import re
import unittest
from datetime import datetime
from unittest.mock import patch

from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

from db.session import Base
from models.discovery import DiscoveryWorkbench
from modules.discovery.workbench import service


@compiles(BigInteger, "sqlite")
def _compile_big_integer_for_sqlite(_type, _compiler, **_kwargs):
    return "INTEGER"


DISCOVERY_ID_RE = re.compile(r"^DSC-\d{6}-[A-Z0-9]{6}$")


class DiscoveryWorkbenchIdTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine, tables=[DiscoveryWorkbench.__table__])
        self.Session = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_generate_discovery_id_format(self):
        value = service.generate_discovery_id(datetime(2026, 9, 17, 10, 26, 0))
        self.assertEqual(value[:11], "DSC-260917-")
        self.assertRegex(value, DISCOVERY_ID_RE)

    def test_save_assigns_discovery_id_and_ignores_client_value(self):
        saved = service.save(
            self.db,
            {"project_code": "P1", "discovery_id": "DSC-260917-HACK01"},
        )
        self.assertRegex(saved["discovery_id"], DISCOVERY_ID_RE)
        self.assertNotEqual(saved["discovery_id"], "DSC-260917-HACK01")

        updated = service.save(
            self.db,
            {
                "id": saved["id"],
                "project_code": "P2",
                "discovery_id": "DSC-260917-HACK02",
            },
        )
        self.assertEqual(updated["discovery_id"], saved["discovery_id"])
        self.assertEqual(updated["project_code"], "P2")

    def test_save_batch_assigns_unique_ids(self):
        result = service.save_batch(
            self.db,
            {"items": [{"project_code": "A"}, {"project_code": "B"}]},
        )
        ids = [item["discovery_id"] for item in result["items"]]
        self.assertEqual(len(ids), 2)
        self.assertEqual(len(set(ids)), 2)
        for value in ids:
            self.assertRegex(value, DISCOVERY_ID_RE)

    def test_assign_retries_on_collision(self):
        values = ["DSC-260917-AAAAAA", "DSC-260917-AAAAAA", "DSC-260917-BBBBBB"]
        with patch.object(service, "generate_discovery_id", side_effect=values):
            first = service.save(self.db, {"project_code": "A"})
            second = service.save(self.db, {"project_code": "B"})
        self.assertEqual(first["discovery_id"], "DSC-260917-AAAAAA")
        self.assertEqual(second["discovery_id"], "DSC-260917-BBBBBB")


if __name__ == "__main__":
    unittest.main()
