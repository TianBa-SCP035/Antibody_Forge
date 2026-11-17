"""公共下拉：业务页面权限门槛、已录入靶点搜索、人员选项。"""

import unittest

from fastapi import HTTPException

from models.discovery import DiscoveryWorkbench
from models.system import SysUser
from models.target import Target
from modules.auth.permissions import UserContext
from modules.discovery.workbench import service as discovery_service
from modules.options import service as options_service
from modules.options.routes import _require_business_access
from modules.registry import BUSINESS_PAGE_CODES, PERMISSIONS
from support import DbTestCase


def _context(*permissions):
    return UserContext(id=9, username="u", display_name="u", roles=[], permissions=list(permissions))


class BusinessAccessTests(unittest.TestCase):
    def test_business_pages_are_non_system_page_codes(self):
        self.assertTrue(BUSINESS_PAGE_CODES)
        self.assertTrue(all(PERMISSIONS[code].type == "page" for code in BUSINESS_PAGE_CODES))
        self.assertFalse(any(code.startswith("system.") for code in BUSINESS_PAGE_CODES))

    def test_options_need_any_business_page(self):
        _require_business_access(_context("serum.page.list"))
        for denied in (_context(), _context("system.page.user", "system.user.manage"), _context("serum.project.delete")):
            with self.subTest(permissions=denied.permissions), self.assertRaises(HTTPException) as caught:
                _require_business_access(denied)
            self.assertEqual(caught.exception.status_code, 403)


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
        self.db.add_all([
            Target(external_id=1, snum="T1", name="PD-L1"),
            Target(external_id=2, snum="T2", name="ERBB2"),
        ])
        for index, (name, codes) in enumerate(rows, start=1):
            self.db.add(DiscoveryWorkbench(discovery_id=f"DSC-260101-{index:06d}", target_name=name, target_codes=codes))
        self.db.commit()

    def search(self, keyword="", limit=50):
        return discovery_service.search_recorded_targets(self.db, keyword, limit)

    def labels(self, keyword="", limit=50):
        return [item["label"] for item in self.search(keyword, limit)]

    def test_empty_keyword_groups_aliases_and_ignores_duplicate_rows(self):
        self.assertEqual(sorted(self.labels()), ["ERBB2", "PD-L1", "自定义靶点"])

    def test_keyword_matches_record_name_code_and_catalog_name(self):
        self.assertEqual(self.labels("CD27"), ["PD-L1"])
        self.assertEqual(self.labels("T2"), ["ERBB2"])
        self.assertEqual(self.labels("erbb"), ["ERBB2"])
        self.assertEqual(self.search("ERBB2")[0]["value"], "HER2")
        self.assertEqual(self.labels("自定义"), ["自定义靶点"])
        self.assertEqual(self.labels("不存在"), [])

    def test_limit_caps_result(self):
        self.assertEqual(len(self.search(limit=1)), 1)

    def test_like_wildcards_are_literal(self):
        self.assertEqual(self.labels("%"), [])
        self.assertEqual(self.labels("_"), [])


class UserOptionTests(DbTestCase):
    tables = (SysUser,)

    def setUp(self):
        super().setUp()
        self.db.add_all([
            SysUser(username="a", display_name="张三"),
            SysUser(username="b", display_name="张四", employment_status="left"),
            SysUser(username="c", display_name="李五", status="disabled"),
            SysUser(username="d", display_name="王六"),
        ])
        self.db.commit()

    def test_only_active_employed_users_with_keyword_and_limit(self):
        self.assertEqual(options_service.get_user_options(self.db), ["张三", "王六"])
        self.assertEqual(options_service.get_user_options(self.db, "张"), ["张三"])
        self.assertEqual(len(options_service.get_user_options(self.db, "", 1)), 1)
        self.assertEqual(options_service.get_user_options(self.db, "%"), [])
