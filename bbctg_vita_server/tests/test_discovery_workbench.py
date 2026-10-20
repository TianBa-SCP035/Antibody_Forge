import re
import unittest
from datetime import date, datetime, timedelta
from unittest.mock import patch

from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

from db.session import Base
from models.discovery import DiscoveryWorkbench
from models.target import Target
from modules.discovery.workbench import service


@compiles(BigInteger, "sqlite")
def _compile_big_integer_for_sqlite(_type, _compiler, **_kwargs):
    return "INTEGER"


DISCOVERY_ID_RE = re.compile(r"^DSC-\d{6}-[A-Z0-9]{6}$")


class DiscoveryWorkbenchIdTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(
            self.engine,
            tables=[DiscoveryWorkbench.__table__, Target.__table__],
        )
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

    def test_schedule_people_and_antigen_options(self):
        saved = service.save(
            self.db,
            {
                "immune_owner": "张三",
                "cell_collector": "李四",
                "boost_cells": "脾细胞\n淋巴结",
                "immune_antigen": "蛋白甲\n蛋白乙",
                "boost_antigen": "自填抗原",
                "screening_antigen": "筛A\n筛B",
            },
        )
        self.assertEqual(saved["immune_owner"], "张三")
        self.assertEqual(saved["cell_collector"], "李四")
        self.assertEqual(saved["boost_cells"], "脾细胞\n淋巴结")
        self.assertEqual(saved["immune_antigen"], "蛋白甲\n蛋白乙")
        options = service.get_options(self.db)
        self.assertEqual(options["immune_antigens"], ["蛋白乙", "蛋白甲"])
        self.assertEqual(options["boost_antigens"], ["自填抗原"])
        self.assertEqual(options["screening_antigens"], ["筛A", "筛B"])
        self.assertEqual(options["immune_owners"], ["张三"])
        self.assertEqual(options["cell_collectors"], ["李四"])

    def test_mouse_category_is_joined_text_and_harvest_shifts_boost(self):
        harvest = date.today() + timedelta(days=30)
        saved = service.save(
            self.db,
            {
                "mouse_strain_category": "RN+RL",
                "harvest_date": harvest.isoformat(),
                "boost_date": "2020-01-01",
            },
        )
        self.assertEqual(saved["mouse_strain_category"], "RL、RN")
        self.assertEqual(saved["harvest_date"], harvest.isoformat())
        self.assertEqual(saved["boost_date"], (harvest - timedelta(days=5)).isoformat())
        self.assertEqual(saved["status"], "待冲击")
        self.assertEqual(service.get_list(self.db, {"mouse_strain_category": "RN"})["total"], 1)
        self.assertEqual(service.get_list(self.db, {"mouse_strain_category": "RN-KO"})["total"], 0)

        adjusted = service.save(self.db, {"id": saved["id"], "boost_date": (harvest - timedelta(days=1)).isoformat()})
        self.assertEqual(adjusted["boost_date"], (harvest - timedelta(days=1)).isoformat())
        self.assertEqual(adjusted["harvest_date"], harvest.isoformat())

        untouched = service.save(self.db, {"id": saved["id"], "harvest_date": harvest.isoformat()})
        self.assertEqual(untouched["boost_date"], (harvest - timedelta(days=1)).isoformat())

        cleared = service.save(self.db, {"id": saved["id"], "harvest_date": ""})
        self.assertIsNone(cleared["harvest_date"])
        self.assertIsNone(cleared["boost_date"])
        self.assertEqual(cleared["status"], "规划中")

        wrapped = service.save(self.db, {"harvest_date": "2026-03-01", "status": "规划中"})
        self.assertEqual(wrapped["boost_date"], "2026-02-24")
        self.assertEqual(wrapped["status"], "规划中")

        custom_category = service.save(self.db, {"mouse_strain_category": "自定鼠型+RN"})
        self.assertEqual(custom_category["mouse_strain_category"], "RN、自定鼠型")

        strain = service.save(self.db, {"mouse_strain": "RMB/C+RM"})
        self.assertEqual(strain["mouse_strain"], "RM、RMB/C")
        self.assertEqual(service.get_list(self.db, {"mouse_strain": "RM"})["total"], 1)
        self.assertEqual(service.get_list(self.db, {"mouse_strain": "RMKO"})["total"], 0)
        custom = service.save(self.db, {"mouse_strain": "自定义+RM"})
        self.assertEqual(custom["mouse_strain"], "RM、自定义")

        legacy = self.db.get(DiscoveryWorkbench, saved["id"])
        legacy.mouse_strain_category = "RN+RL"
        self.db.commit()
        self.assertEqual(service.get_list(self.db, {"mouse_strain_category": "RL"})["total"], 1)
        self.assertEqual(service.get_list(self.db, {"mouse_strain_category": "RN-KO"})["total"], 0)

    def test_keyword_can_find_system_discovery_id(self):
        saved = service.save(self.db, {"project_code": "P1"})
        result = service.get_list(self.db, {"keyword": saved["discovery_id"]})
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["id"], saved["id"])


if __name__ == "__main__":
    unittest.main()
