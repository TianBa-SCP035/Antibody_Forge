import unittest

from sqlalchemy import select

from models.discovery import DiscoveryWorkbench
from models.system import SysUser
from models.target import Target
from modules.discovery.workbench import service
from modules.options import service as options_service
from support import DbTestCase
from utils.filter_values import recorded_target_search


class RecordedTargetSearchTests(DbTestCase):
    tables = (DiscoveryWorkbench, Target)

    def setUp(self):
        super().setUp()
        rows = [
            ("CD274", ["T1"]),
            ("PD-L1", ["T1"]),
            *[("HER2", ["T2"])] * 12,
            ("自定义靶点", []),
        ]
        with self.Session() as db:
            db.add_all([
                Target(external_id=1, snum="T1", name="PD-L1"),
                Target(external_id=2, snum="T2", name="ERBB2"),
            ])
            for index, (name, codes) in enumerate(rows, start=1):
                db.add(DiscoveryWorkbench(
                    discovery_id=f"DSC-260101-{index:06d}",
                    target_name=name,
                    target_codes=codes,
                ))
            db.commit()

    def search(self, keyword="", limit=50):
        with self.Session() as db:
            return service.search_recorded_targets(db, keyword, limit)

    def labels(self, keyword="", limit=50):
        return [item["label"] for item in self.search(keyword, limit)]

    def test_empty_keyword_groups_aliases_and_ignores_duplicate_rows(self):
        self.assertEqual(sorted(self.labels()), ["ERBB2", "PD-L1", "自定义靶点"])

    def test_keyword_matches_record_name_code_and_catalog_name(self):
        self.assertEqual(self.labels("CD27"), ["PD-L1"])
        self.assertEqual(self.labels("T2"), ["ERBB2"])
        self.assertEqual(self.labels("erbb"), ["ERBB2"])
        her2 = self.search("ERBB2")[0]
        self.assertEqual(her2["value"], "HER2")
        self.assertEqual(self.labels("自定义"), ["自定义靶点"])
        self.assertEqual(self.labels("不存在"), [])

    def test_limit_caps_result(self):
        self.assertEqual(len(self.search(limit=1)), 1)

    def test_like_wildcards_are_literal(self):
        self.assertEqual(self.labels("%"), [])
        self.assertEqual(self.labels("_"), [])

    def test_expression_columns_are_supported(self):
        name_expr = DiscoveryWorkbench.target_name + ""
        with self.Session() as db:
            items = recorded_target_search(
                db, select(name_expr, DiscoveryWorkbench.target_codes), "HER", 10
            )
        self.assertEqual([item["label"] for item in items], ["ERBB2"])


class UserOptionTests(DbTestCase):
    tables = (SysUser,)

    def setUp(self):
        super().setUp()
        with self.Session() as db:
            db.add_all([
                SysUser(username="a", display_name="张三"),
                SysUser(username="b", display_name="张四", employment_status="left"),
                SysUser(username="c", display_name="李五", status="disabled"),
                SysUser(username="d", display_name="王六"),
            ])
            db.commit()

    def test_only_active_employed_users_with_keyword_and_limit(self):
        with self.Session() as db:
            self.assertEqual(options_service.get_user_options(db), ["张三", "王六"])
            self.assertEqual(options_service.get_user_options(db, "张"), ["张三"])
            self.assertEqual(len(options_service.get_user_options(db, "", 1)), 1)
            self.assertEqual(options_service.get_user_options(db, "%"), [])


if __name__ == "__main__":
    unittest.main()
