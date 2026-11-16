from fastapi import HTTPException
from support import DbTestCase

import modules.system.routes as system_routes
import modules.system.service as system_service
from core.errors import ForbiddenError
from models.system import (
    SysPermissionBundle,
    SysPermissionBundleItem,
    SysRole,
    SysRolePermissionBundle,
    SysUser,
    SysUserPermissionOverride,
    SysUserRole,
)
from modules.auth.permissions import (
    UserContext,
    build_user_context,
    get_role_permissions,
)
from modules.options.routes import _require_business_access
from modules.registry import BUSINESS_PAGE_CODES, PERMISSIONS


class PermissionResolutionTests(DbTestCase):
    tables = (
        SysUser,
        SysRole,
        SysUserRole,
        SysPermissionBundle,
        SysPermissionBundleItem,
        SysRolePermissionBundle,
        SysUserPermissionOverride,
    )

    def setUp(self):
        super().setUp()
        self.user = SysUser(id=2, username="operator")
        role = SysRole(id=1, code="operator", name="业务员")
        self.db.add_all([
            self.user,
            role,
            SysUserRole(user_id=2, role_id=1),
            SysPermissionBundle(code="ops", name="业务", module="business"),
            SysRolePermissionBundle(role_id=1, bundle_code="ops"),
            SysPermissionBundleItem(bundle_code="ops", permission_code="serum.page.list"),
            SysPermissionBundleItem(bundle_code="ops", permission_code="serum.project.edit"),
            SysPermissionBundleItem(bundle_code="ops", permission_code="legacy.removed"),
            SysUserPermissionOverride(user_id=2, permission_code="serum.mouse.export", effect="allow"),
            SysUserPermissionOverride(user_id=2, permission_code="legacy.other", effect="allow"),
            SysUserPermissionOverride(user_id=2, permission_code="serum.project.edit", effect="deny"),
        ])
        self.db.commit()

    def test_role_bundles_and_overrides_ignore_unregistered_codes(self):
        self.assertEqual(get_role_permissions(self.db, 2), ["serum.page.list", "serum.project.edit"])
        context = build_user_context(self.db, self.user)
        self.assertEqual(context.permissions, ["serum.mouse.export", "serum.page.list"])
        self.assertTrue(context.allows("serum.project.edit_all", "serum.page.list"))
        self.assertFalse(context.allows("serum.project.edit"))

    def test_inactive_bundle_grants_nothing(self):
        self.db.get(SysPermissionBundle, 1).status = "inactive"
        self.db.commit()
        self.assertEqual(build_user_context(self.db, self.user).permissions, ["serum.mouse.export"])

    def test_superuser_has_every_registered_code(self):
        admin = SysUser(id=3, username="admin", is_superuser=True)
        self.assertEqual(build_user_context(self.db, admin).permissions, sorted(PERMISSIONS))

    def test_permission_list_comes_from_registry_with_module(self):
        items = system_routes.list_permissions()["data"]["items"]
        self.assertEqual({item["code"] for item in items}, set(PERMISSIONS))
        self.assertEqual([item["sort_order"] for item in items], sorted(item["sort_order"] for item in items))
        serum_list = next(item for item in items if item["code"] == "serum.page.list")
        self.assertEqual(serum_list["module"], "serum")
        self.assertEqual(serum_list["route_path"], PERMISSIONS["serum.page.list"].route_path)

    def test_options_need_any_business_page(self):
        def context(*permissions):
            return UserContext(id=9, username="u", display_name="u", roles=[], permissions=list(permissions))

        old_pages = {"serum.page.edit", "serum.page.workbench", "discovery.page.synthesis_progress",
                     "molecular.page.library", "mega.page.flow_work_order"}
        self.assertTrue(old_pages <= set(BUSINESS_PAGE_CODES))
        self.assertTrue(all(PERMISSIONS[code].type == "page" for code in BUSINESS_PAGE_CODES))
        self.assertFalse(any(code.startswith("system.") for code in BUSINESS_PAGE_CODES))
        _require_business_access(context("serum.page.list"))
        for denied in (context(), context("system.page.user", "system.user.manage"), context("serum.project.delete")):
            with self.assertRaises(HTTPException) as caught:
                _require_business_access(denied)
            self.assertEqual(caught.exception.status_code, 403)

    def test_only_superuser_can_manage_superuser_accounts(self):
        root = SysUser(id=3, username="root", is_superuser=True)
        other_root = SysUser(id=4, username="root2", is_superuser=True)
        plain = SysUser(id=5, username="plain")
        self.db.add_all([root, other_root, plain])
        self.db.commit()
        attempts = (
            lambda actor: system_service.save_user(self.db, {"id": 4, "display_name": "x"}, actor=actor),
            lambda actor: system_service.reset_password(self.db, 4, "123456", actor=actor),
            lambda actor: system_service.delete_user(self.db, 4, actor=actor),
        )
        for attempt in attempts:
            with self.assertRaises(ForbiddenError):
                attempt(self.user)
        with self.assertRaises(ForbiddenError):
            system_service.save_user(self.db, {"id": 5, "is_superuser": True}, actor=self.user)
        self.assertIsNotNone(self.db.get(SysUser, 4))

        system_service.reset_password(self.db, 5, "123456", actor=self.user)
        system_service.save_user(self.db, {"id": 4, "display_name": "x"}, actor=root)
        system_service.delete_user(self.db, 4, actor=root)
        self.assertIsNone(self.db.get(SysUser, 4))

    def test_bundle_save_rejects_unregistered_codes(self):
        with self.assertRaises(ValueError):
            system_service._ensure_permission_codes_exist(["serum.page.list", "legacy.removed"])
        system_service._ensure_permission_codes_exist(["serum.page.list"])
