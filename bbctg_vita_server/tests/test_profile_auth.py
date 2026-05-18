from unittest import TestCase
from unittest.mock import MagicMock, patch

from models.system import SysUser
from modules.auth.service import (
    build_user_info,
    change_user_password,
    update_profile_signature,
)


class _FakeDb:
    def __init__(self):
        self.committed = False

    def commit(self):
        self.committed = True

    def refresh(self, _user):
        return None


class ProfileAuthTests(TestCase):
    def _user(self, **overrides) -> SysUser:
        user = SysUser(
            id=1,
            username="u001",
            display_name="测试用户",
            department="研发部",
            group_name="一组",
            job_no="E001",
            position_title="研究员",
            gender="male",
            email="test@example.com",
            mobile="13800000000",
            profile_signature="hello",
            password_hash=None,
            status="active",
        )
        for key, value in overrides.items():
            setattr(user, key, value)
        return user

    @patch("modules.auth.service.build_user_context")
    def test_build_user_info_includes_profile_fields(self, mock_context):
        mock_context.return_value = MagicMock(
            id=1,
            roles=["admin"],
            permissions=["system.user.manage"],
            display_name="测试用户",
            username="u001",
            is_superuser=False,
        )
        user = self._user(password_hash="pbkdf2_sha256$260000$salt$digest")
        user.last_login_at = None
        db = MagicMock()
        info = build_user_info(db, user)
        self.assertEqual(info["department"], "研发部")
        self.assertEqual(info["groupName"], "一组")
        self.assertEqual(info["jobNo"], "E001")
        self.assertEqual(info["profileSignature"], "hello")
        self.assertTrue(info["hasPassword"])
        self.assertNotIn("openid", info)
        self.assertNotIn("status", info)

    @patch("modules.auth.service.build_user_context")
    @patch("modules.auth.service.write_operation_log")
    def test_update_profile_signature(self, mock_log, mock_context):
        mock_context.return_value = MagicMock(
            id=1,
            roles=[],
            permissions=[],
            display_name="测试用户",
            username="u001",
            is_superuser=False,
        )
        db = _FakeDb()
        user = self._user()
        result = update_profile_signature(db, user, "  new sig  ")
        self.assertTrue(db.committed)
        self.assertEqual(user.profile_signature, "new sig")
        self.assertEqual(result["profileSignature"], "new sig")
        mock_log.assert_called_once()

    @patch("modules.auth.service.write_operation_log")
    def test_change_password_without_old_when_no_existing(self, mock_log):
        db = _FakeDb()
        user = self._user(password_hash=None)
        change_user_password(db, user, "secret12")
        self.assertTrue(db.committed)
        self.assertTrue(user.password_hash.startswith("pbkdf2_sha256$"))
        detail = mock_log.call_args[0][4]
        self.assertEqual(detail, {"mode": "set"})

    @patch("modules.auth.service.write_operation_log")
    def test_change_password_logged_in_without_old(self, mock_log):
        db = _FakeDb()
        user = self._user(password_hash="pbkdf2_sha256$260000$salt$old")
        change_user_password(db, user, "newpass9")
        self.assertTrue(db.committed)
        detail = mock_log.call_args[0][4]
        self.assertEqual(detail, {"mode": "change"})
