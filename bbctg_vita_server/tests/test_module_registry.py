import unittest
from unittest.mock import patch

import modules.registry as registry
from core.module_spec import ModuleAccess, feature, menu, page
from jobs.registry import SCHEDULED_JOBS


class ModuleRegistryTests(unittest.TestCase):
    def test_duplicate_permission_code_is_rejected(self):
        duplicated = page("demo.page", "示例", resource="demo", route_path="/demo", sort_order=1, message="无权限")
        with patch.object(registry, "ACCESS", (ModuleAccess("a", (duplicated,)), ModuleAccess("b", (duplicated,)))):
            with self.assertRaises(RuntimeError):
                registry._index_permissions()

    def test_duplicate_feature_code_is_rejected(self):
        flag = feature("feature.demo", "示例", "", sort_order=1, enabled=False)
        with patch.object(registry, "ACCESS", (ModuleAccess("a", features=(flag,)), ModuleAccess("b", features=(flag,)))):
            with self.assertRaises(RuntimeError):
                registry._index_features()

    def test_conflicting_resource_label_is_rejected(self):
        with patch.object(registry, "ACCESS", (ModuleAccess("a", resources={"demo": "示例"}),
                                               ModuleAccess("b", resources={"demo": "别名"}))):
            with self.assertRaises(RuntimeError):
                registry._merge_resources()

    def test_permission_parents_and_resources_are_registered(self):
        for code, permission in registry.PERMISSIONS.items():
            with self.subTest(code=code):
                if permission.parent_code:
                    self.assertIn(permission.parent_code, registry.PERMISSIONS)
                self.assertIn(permission.resource, registry.RESOURCE_LABELS)
                if permission.type == "page":
                    self.assertTrue(permission.route_path)

    def test_menu_parents_are_registered_menus(self):
        menus = {code for code, flag in registry.FEATURE_INDEX.items() if flag["category"] == "menu"}
        for code in menus:
            parent = registry.FEATURE_INDEX[code]["config"].get("parent_code")
            if parent:
                with self.subTest(code=code):
                    self.assertIn(parent, menus)

    def test_every_scheduled_job_declares_its_feature_and_resource(self):
        for job in SCHEDULED_JOBS:
            with self.subTest(job=job["id"]):
                self.assertEqual(registry.FEATURE_INDEX[job["feature_code"]]["category"], "job")
                self.assertIn(job["resource"], registry.RESOURCE_LABELS)

    def test_menu_helper_records_parent_in_config(self):
        flag = menu("menu.demo.child", "子菜单", "", sort_order=1, path="/demo/child", icon="x",
                    parent_code="menu.demo")
        self.assertEqual(flag["config"], {"path": "/demo/child", "icon": "x", "parent_code": "menu.demo"})
