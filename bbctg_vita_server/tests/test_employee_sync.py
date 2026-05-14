from datetime import date
from unittest import TestCase

from models.system import SysUser
from modules.system import employee_sync


class _ScalarResult:
    def __init__(self, values):
        self._values = values

    def all(self):
        return self._values


class _MappingsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _ExecuteResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return _MappingsResult(self._rows)


class _FakeDb:
    def __init__(self, users):
        self.users = users
        self.created = []
        self.committed = False
        self.rolled_back = False

    def scalars(self, _stmt):
        if not hasattr(self, "_scalar_calls"):
            self._scalar_calls = 0
        self._scalar_calls += 1
        if self._scalar_calls == 1:
            return _ScalarResult(self.users)
        return _ScalarResult([user.username for user in self.users])

    def add(self, user):
        self.created.append(user)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


class _FakeEmployeeDb:
    def __init__(self, rows):
        self.rows = rows

    def execute(self, _stmt):
        return _ExecuteResult(self.rows)


def _row(**overrides):
    row = {
        "external_id": 1,
        "openid": "openid-new",
        "job_no": "E001",
        "display_name": "Employee",
        "mobile": "13800000000",
        "email": "employee@example.com",
        "department": "研发部",
        "group_name": "研发一组",
        "position_title": "研究员",
        "sex": 1,
        "is_locked": 0,
        "leave_date": None,
    }
    row.update(overrides)
    return row


class EmployeeSyncTest(TestCase):
    def test_updates_existing_user_when_openid_and_job_no_match(self):
        user = SysUser(username="old", openid="openid-1", job_no="E001", employment_status="active")
        db = _FakeDb([user])
        employee_db = _FakeEmployeeDb(
            [_row(openid="openid-1", mobile="13900000000", leave_date=date(2026, 1, 1))]
        )

        result = employee_sync.sync_employee_profiles(db, employee_db)

        self.assertEqual(result["updated"], 1)
        self.assertEqual(user.mobile, "13900000000")
        self.assertEqual(user.employment_status, "resigned")
        self.assertTrue(db.committed)

    def test_skips_job_no_mismatch_without_overwriting(self):
        user = SysUser(username="old", openid="openid-1", job_no="E001", mobile="13800000000")
        db = _FakeDb([user])
        employee_db = _FakeEmployeeDb([_row(openid="openid-1", job_no="E999", mobile="13900000000")])

        result = employee_sync.sync_employee_profiles(db, employee_db)

        self.assertEqual(result["skipped"]["job_no_mismatch"], 1)
        self.assertEqual(user.mobile, "13800000000")

    def test_creates_only_unlocked_users_and_skips_duplicate_openid(self):
        db = _FakeDb([])
        employee_db = _FakeEmployeeDb(
            [
                _row(openid="openid-new", mobile="13800000001"),
                _row(openid="openid-locked", mobile="13800000002", is_locked=1),
                _row(openid="openid-dup", mobile="13800000003"),
                _row(openid="openid-dup", mobile="13800000004"),
            ]
        )

        result = employee_sync.sync_employee_profiles(db, employee_db)

        self.assertEqual(result["created"], 1)
        self.assertEqual(result["skipped"]["locked_new_user"], 1)
        self.assertEqual(result["skipped"]["duplicate_openid"], 2)
        self.assertEqual(db.created[0].username, "13800000001")
        self.assertEqual(db.created[0].department, "研发部")
        self.assertEqual(db.created[0].group_name, "研发一组")
        self.assertTrue(db.created[0].password_hash.startswith("pbkdf2_sha256$"))
        self.assertEqual(db.created[0].status, "active")
