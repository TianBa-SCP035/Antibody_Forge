"""用户管理：超级管理员保护、权限包校验、权限列表来源与角色保存审计。"""

from sqlalchemy import select

import modules.system.routes as system_routes
import modules.system.service as system_service
from core.errors import ForbiddenError
from db.session import AuditedSession
from models.system import (
    SysOperationLog,
    SysOperationLogItem,
    SysPermissionBundle,
    SysPermissionBundleItem,
    SysRole,
    SysRolePermissionBundle,
    SysUser,
    SysUserPermissionOverride,
    SysUserRole,
)
from modules.registry import PERMISSIONS
from modules.system.audit_context import audit_scope
from modules.system.audit_session import setup_session_audit
from support import DbTestCase


USER_TABLES = (
    SysUser,
    SysRole,
    SysUserRole,
    SysPermissionBundle,
    SysPermissionBundleItem,
    SysRolePermissionBundle,
    SysUserPermissionOverride,
)


class UserManagementTests(DbTestCase):
    tables = USER_TABLES

    def setUp(self):
        super().setUp()
        self.operator = SysUser(id=2, username="operator")
        self.root = SysUser(id=3, username="root", is_superuser=True)
        self.db.add_all([self.operator, self.root, SysUser(id=4, username="root2", is_superuser=True), SysUser(id=5, username="plain")])
        self.db.commit()

    def test_only_superuser_can_manage_superuser_accounts(self):
        attempts = (
            lambda actor: system_service.save_user(self.db, {"id": 4, "display_name": "x"}, actor=actor),
            lambda actor: system_service.reset_password(self.db, 4, "123456", actor=actor),
            lambda actor: system_service.delete_user(self.db, 4, actor=actor),
        )
        for attempt in attempts:
            with self.assertRaises(ForbiddenError):
                attempt(self.operator)
        self.assertIsNotNone(self.db.get(SysUser, 4))

        system_service.save_user(self.db, {"id": 4, "display_name": "x"}, actor=self.root)
        system_service.delete_user(self.db, 4, actor=self.root)
        self.assertIsNone(self.db.get(SysUser, 4))

    def test_only_superuser_can_grant_superuser(self):
        with self.assertRaises(ForbiddenError):
            system_service.save_user(self.db, {"id": 5, "is_superuser": True}, actor=self.operator)
        system_service.reset_password(self.db, 5, "123456", actor=self.operator)
        system_service.save_user(self.db, {"id": 5, "is_superuser": True}, actor=self.root)
        self.assertTrue(self.db.get(SysUser, 5).is_superuser)

    def test_bundle_save_rejects_unregistered_codes(self):
        with self.assertRaisesRegex(ValueError, "legacy.removed"):
            system_service.save_permission_bundle(
                self.db, {"code": "ops", "name": "业务", "module": "business", "permission_codes": ["serum.page.list", "legacy.removed"]}
            )
        self.db.rollback()
        system_service.save_permission_bundle(
            self.db, {"code": "ops", "name": "业务", "module": "business", "permission_codes": ["serum.page.list"]}
        )
        items = self.db.scalars(select(SysPermissionBundleItem.permission_code)).all()
        self.assertEqual(items, ["serum.page.list"])

    def test_permission_list_comes_from_registry_with_module(self):
        items = system_routes.list_permissions()["data"]["items"]
        self.assertEqual({item["code"] for item in items}, set(PERMISSIONS))
        self.assertEqual([item["sort_order"] for item in items], sorted(item["sort_order"] for item in items))
        serum_list = next(item for item in items if item["code"] == "serum.page.list")
        self.assertEqual(serum_list["module"], "serum")
        self.assertEqual(serum_list["route_path"], PERMISSIONS["serum.page.list"].route_path)


class UserRoleAuditTests(DbTestCase):
    tables = (*USER_TABLES, SysOperationLog, SysOperationLogItem)
    session_options = {"class_": AuditedSession, "expire_on_commit": False}

    @classmethod
    def setUpClass(cls):
        setup_session_audit()

    def test_saving_unchanged_roles_keeps_rows_and_writes_no_log(self):
        root = SysUser(id=1, username="root", is_superuser=True)
        self.db.add_all([root, SysUser(id=10, username="u10"), SysRole(id=20, code="r", name="角色"), SysUserRole(user_id=10, role_id=20)])
        self.db.commit()
        with audit_scope("test.roles.same", "角色不变", source="user"):
            system_service.save_user(self.db, {"id": 10, "role_ids": [20]}, actor=root)
        rows = self.db.scalars(select(SysUserRole).where(SysUserRole.user_id == 10)).all()
        self.assertEqual([(row.user_id, row.role_id) for row in rows], [(10, 20)])
        self.assertIsNone(self.db.scalar(select(SysOperationLog).where(SysOperationLog.action == "test.roles.same")))
