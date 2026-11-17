"""登录与权限：有效权限计算、账号密码和云之家登录、个人资料、外部回调来源校验。"""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import select

from models.system import (
    SysFeatureFlag,
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
from modules.auth import service as auth_service
from modules.auth.external import check_external_caller
from modules.auth.permissions import build_user_context, get_role_permissions
from modules.auth.security import hash_password, verify_password
from modules.registry import PERMISSIONS
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


class PermissionResolutionTests(DbTestCase):
    tables = USER_TABLES

    def setUp(self):
        super().setUp()
        self.user = SysUser(id=2, username="operator")
        self.db.add_all([
            self.user,
            SysRole(id=1, code="operator", name="业务员"),
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
        self.db.scalar(select(SysPermissionBundle)).status = "inactive"
        self.db.commit()
        self.assertEqual(build_user_context(self.db, self.user).permissions, ["serum.mouse.export"])

    def test_superuser_has_every_registered_code(self):
        admin = SysUser(id=3, username="admin", is_superuser=True)
        self.assertEqual(build_user_context(self.db, admin).permissions, sorted(PERMISSIONS))


class LoginTests(DbTestCase):
    tables = (*USER_TABLES, SysFeatureFlag, SysOperationLog, SysOperationLogItem)

    def setUp(self):
        super().setUp()
        self.db.add_all([
            SysUser(username="alice", display_name="张三", password_hash=hash_password("secret9"), openid="oid-1"),
            SysUser(username="bob", password_hash=hash_password("secret9"), status="disabled"),
        ])
        self.db.commit()

    def _login_logs(self):
        return [(log.action, log.result, log.error_message) for log in self.db.scalars(select(SysOperationLog))]

    def _yunzhijia(self, user_context):
        client = SimpleNamespace(acquire_user_context=lambda _ticket: {"data": user_context})
        return patch.object(auth_service, "YunzhijiaClient", return_value=client)

    def test_password_login_returns_token_and_marks_login(self):
        result = auth_service.login_with_password(self.db, " alice ", "secret9")
        self.assertTrue(result["accessToken"])
        user = self.db.scalar(select(SysUser).where(SysUser.username == "alice"))
        self.assertIsNotNone(user.last_login_at)
        self.assertEqual(self._login_logs(), [("auth.password_login", "success", None)])

    def test_wrong_password_and_disabled_account_are_rejected_and_logged(self):
        for username, message in (("alice", "用户名或密码错误"), ("nobody", "用户名或密码错误"), ("bob", "账号已被禁用")):
            with self.subTest(username=username):
                with self.assertRaises(HTTPException) as raised:
                    auth_service.login_with_password(self.db, username, "wrong" if username != "bob" else "secret9")
                self.assertEqual(raised.exception.status_code, 401)
                self.assertIn(message, raised.exception.detail)
                self.assertEqual(self._login_logs()[-1], ("auth.password_login", "failed", message))

    def test_yunzhijia_login_matches_bound_openid(self):
        with self._yunzhijia({"openid": "oid-1"}):
            self.assertTrue(auth_service.login_with_yunzhijia_ticket(self.db, "ticket")["accessToken"])

    def test_unbound_yunzhijia_account_needs_auto_provision_feature(self):
        with self._yunzhijia({"openid": "oid-new", "jobNo": "alice", "displayName": "李四"}):
            with self.assertRaises(HTTPException) as raised:
                auth_service.login_with_yunzhijia_ticket(self.db, "ticket")
            self.assertEqual(raised.exception.status_code, 403)

            self.db.add(SysFeatureFlag(code=auth_service.YUNZHIJIA_AUTO_PROVISION_FEATURE, enabled=True, visible=True, config={}))
            self.db.commit()
            auth_service.login_with_yunzhijia_ticket(self.db, "ticket")
        created = self.db.scalar(select(SysUser).where(SysUser.openid == "oid-new"))
        self.assertEqual(created.display_name, "李四")
        self.assertNotEqual(created.username, "alice")


class ProfileTests(DbTestCase):
    tables = USER_TABLES

    def setUp(self):
        super().setUp()
        self.user = SysUser(
            username="u001",
            display_name="测试用户",
            department="研发部",
            group_name="一组",
            job_no="E001",
            openid="oid-1",
            profile_signature="hello",
            password_hash=hash_password("oldpass"),
        )
        self.db.add(self.user)
        self.db.commit()

    def test_user_info_exposes_profile_but_not_account_internals(self):
        info = auth_service.build_user_info(self.db, self.user)
        self.assertEqual((info["department"], info["groupName"], info["jobNo"]), ("研发部", "一组", "E001"))
        self.assertTrue(info["hasPassword"])
        self.assertNotIn("openid", info)
        self.assertNotIn("status", info)

    def test_signature_is_trimmed_and_limited(self):
        result = auth_service.update_profile_signature(self.db, self.user, "  new sig  ")
        self.assertEqual(result["profileSignature"], "new sig")
        self.assertIsNone(auth_service.update_profile_signature(self.db, self.user, "  ")["profileSignature"])
        with self.assertRaisesRegex(ValueError, "255"):
            auth_service.update_profile_signature(self.db, self.user, "x" * 256)

    def test_change_password_needs_no_old_password_and_at_least_six_chars(self):
        auth_service.change_user_password(self.db, self.user, "  newpass9  ")
        self.assertTrue(verify_password("newpass9", self.db.get(SysUser, self.user.id).password_hash))
        with self.assertRaisesRegex(ValueError, "至少需要 6 位"):
            auth_service.change_user_password(self.db, self.user, "12345")


def _request(headers=None, query=None, host="10.0.0.5"):
    return SimpleNamespace(headers=headers or {}, query_params=query or {}, client=SimpleNamespace(host=host))


class ExternalCallerTests(unittest.TestCase):
    def test_unconfigured_allows_everyone(self):
        check_external_caller(_request(), "", "")

    def test_token_is_read_only_from_header(self):
        check_external_caller(_request(headers={"X-Callback-Token": "s3cret"}), "s3cret", "")
        for request in (_request(headers={"X-Callback-Token": "wrong"}), _request(query={"token": "s3cret"})):
            with self.subTest(request=request), self.assertRaises(HTTPException) as raised:
                check_external_caller(request, "s3cret", "")
            self.assertEqual(raised.exception.status_code, 401)

    def test_ip_allowlist(self):
        check_external_caller(_request(host="10.0.0.5"), "", "10.0.0.5, 10.0.0.6")
        with self.assertRaises(HTTPException) as raised:
            check_external_caller(_request(host="10.0.0.9"), "", "10.0.0.5,10.0.0.6")
        self.assertEqual(raised.exception.status_code, 403)
