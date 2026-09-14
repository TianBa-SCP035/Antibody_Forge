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
        return _ScalarResult(self.users)

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


_next_external_id = 0


def _row(**overrides):
    global _next_external_id
    _next_external_id += 1
    row = {
        "external_id": _next_external_id,
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
        self.assertEqual(result["disabled_on_resignation"], 1)
        self.assertEqual(user.mobile, "13900000000")
        self.assertEqual(user.employment_status, "resigned")
        self.assertEqual(user.status, "disabled")
        self.assertTrue(db.committed)

    def test_does_not_disable_already_resigned_user_with_active_status(self):
        user = SysUser(
            username="old",
            openid="openid-1",
            job_no="E001",
            display_name="Employee",
            mobile="13900000000",
            email="employee@example.com",
            department="研发部",
            group_name="研发一组",
            position_title="研究员",
            gender="male",
            employment_status="resigned",
            status="active",
        )
        db = _FakeDb([user])
        employee_db = _FakeEmployeeDb(
            [_row(openid="openid-1", mobile="13900000000", leave_date=date(2026, 1, 1))]
        )

        result = employee_sync.sync_employee_profiles(db, employee_db)

        self.assertEqual(result["disabled_on_resignation"], 0)
        self.assertEqual(user.status, "active")
        self.assertEqual(user.employment_status, "resigned")

    def test_updates_job_no_and_department_when_openid_matches(self):
        user = SysUser(
            username="old",
            openid="openid-1",
            job_no="E001",
            display_name="Employee",
            mobile="13800000000",
            department="旧部门",
        )
        db = _FakeDb([user])
        employee_db = _FakeEmployeeDb(
            [_row(openid="openid-1", job_no="E999", mobile="13900000000", department="新部门")]
        )

        result = employee_sync.sync_employee_profiles(db, employee_db)

        self.assertEqual(result["updated"], 1)
        self.assertEqual(result["skipped"]["job_no_mismatch"], 0)
        self.assertEqual(user.job_no, "E999")
        self.assertEqual(user.department, "新部门")
        self.assertEqual(user.mobile, "13900000000")

    def test_creates_only_unlocked_users_and_skips_ambiguous_openid(self):
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

    def test_uses_unlocked_row_when_openid_is_shared(self):
        user = SysUser(
            username="13800000000",
            openid="openid-shared",
            job_no="E001",
            display_name="顾明月",
            mobile="13800000000",
            department="旧部门",
            employment_status="active",
            status="active",
        )
        db = _FakeDb([user])
        employee_db = _FakeEmployeeDb(
            [
                _row(
                    openid="openid-shared",
                    job_no="E001",
                    display_name="顾明月",
                    is_locked=1,
                    department="旧部门",
                ),
                _row(
                    openid="openid-shared",
                    job_no="BJ2289",
                    display_name="顾明月",
                    department="CMC开发部",
                    is_locked=0,
                ),
            ]
        )

        result = employee_sync.sync_employee_profiles(db, employee_db)

        self.assertEqual(result["updated"], 1)
        self.assertEqual(result["skipped"]["duplicate_openid"], 0)
        self.assertEqual(user.job_no, "BJ2289")
        self.assertEqual(user.department, "CMC开发部")

    def test_fallback_matches_name_and_job_no_when_external_openid_cleared(self):
        user = SysUser(
            username="15800002120",
            openid="openid-keep",
            job_no="BJ0839",
            display_name="王申森",
            mobile="15800002120",
            department="抗体产品部",
            employment_status="active",
            status="active",
        )
        db = _FakeDb([user])
        employee_db = _FakeEmployeeDb(
            [
                _row(
                    openid="",
                    job_no="BJ0839",
                    display_name="王申森",
                    mobile="15800002120",
                    department="抗体产品部",
                    is_locked=1,
                    leave_date=date(2026, 8, 21),
                )
            ]
        )

        result = employee_sync.sync_employee_profiles(db, employee_db)

        self.assertEqual(result["updated"], 1)
        self.assertEqual(result["disabled_on_resignation"], 1)
        self.assertEqual(user.openid, "openid-keep")
        self.assertEqual(user.employment_status, "resigned")
        self.assertEqual(user.status, "disabled")
        self.assertEqual(result["created"], 0)

    def test_keeps_local_profile_fields_when_source_is_blank(self):
        user = SysUser(
            username="15800002120",
            openid="openid-keep",
            job_no="BJ0839",
            display_name="王申森",
            mobile="15800002120",
            email="shensen.wang@example.com",
            department="抗体产品部",
            group_name="免疫组",
            position_title="抗体开发研究员",
            gender="female",
            employment_status="active",
            status="active",
        )
        db = _FakeDb([user])
        employee_db = _FakeEmployeeDb(
            [
                _row(
                    openid="",
                    job_no="BJ0839",
                    display_name="王申森",
                    mobile=None,
                    email=None,
                    department=None,
                    group_name=None,
                    position_title=None,
                    sex="",
                    is_locked=1,
                    leave_date=date(2026, 8, 21),
                )
            ]
        )

        result = employee_sync.sync_employee_profiles(db, employee_db)

        self.assertEqual(result["disabled_on_resignation"], 1)
        self.assertEqual(user.mobile, "15800002120")
        self.assertEqual(user.email, "shensen.wang@example.com")
        self.assertEqual(user.department, "抗体产品部")
        self.assertEqual(user.group_name, "免疫组")
        self.assertEqual(user.position_title, "抗体开发研究员")
        self.assertEqual(user.gender, "female")
        self.assertEqual(user.openid, "openid-keep")

    def test_fallback_writes_openid_when_external_has_unused_value(self):
        user = SysUser(
            username="13800000000",
            openid="openid-old",
            job_no="HM1204",
            display_name="张丽",
            mobile="13800000000",
            employment_status="active",
            status="active",
        )
        db = _FakeDb([user])
        employee_db = _FakeEmployeeDb(
            [
                _row(
                    openid="openid-new",
                    job_no="HM1204",
                    display_name="张丽",
                    mobile="13800000000",
                )
            ]
        )

        result = employee_sync.sync_employee_profiles(db, employee_db)

        self.assertEqual(result["updated"], 1)
        self.assertEqual(user.openid, "openid-new")

    def test_does_not_steal_openid_owned_by_another_user(self):
        keeper = SysUser(
            username="13800000001",
            openid="openid-taken",
            job_no="E100",
            display_name="其他人",
            mobile="13800000001",
        )
        user = SysUser(
            username="13800000000",
            openid="openid-old",
            job_no="HM1204",
            display_name="张丽",
            mobile="13800000000",
        )
        db = _FakeDb([keeper, user])
        employee_db = _FakeEmployeeDb(
            [
                _row(
                    openid="openid-taken",
                    job_no="E100",
                    display_name="其他人",
                    mobile="13800000001",
                ),
                _row(
                    openid="openid-taken",
                    job_no="HM1204",
                    display_name="张丽",
                    mobile="13800000000",
                ),
            ]
        )

        result = employee_sync.sync_employee_profiles(db, employee_db)

        self.assertEqual(result["skipped"]["duplicate_openid"], 2)
        self.assertEqual(user.openid, "openid-old")
        self.assertEqual(keeper.openid, "openid-taken")

    def test_reuses_existing_user_with_same_name_and_mobile_instead_of_creating(self):
        user = SysUser(
            username="13800000000",
            openid="openid-old",
            job_no="HB004",
            display_name="郑果立",
            mobile="13800000000",
            department="旧部门",
        )
        db = _FakeDb([user])
        employee_db = _FakeEmployeeDb(
            [
                _row(
                    openid="openid-new",
                    job_no="BB364",
                    display_name="郑果立",
                    mobile="13800000000",
                    department="新部门",
                )
            ]
        )

        result = employee_sync.sync_employee_profiles(db, employee_db)

        self.assertEqual(result["created"], 0)
        self.assertEqual(result["updated"], 1)
        self.assertEqual(user.job_no, "BB364")
        self.assertEqual(user.department, "新部门")
        self.assertEqual(user.openid, "openid-new")
        self.assertEqual(user.username, "13800000000")
        self.assertEqual(db.created, [])

    def test_does_not_reuse_when_mobile_matches_but_name_differs(self):
        user = SysUser(
            username="13800000000",
            openid="openid-old",
            job_no="HB009",
            display_name="王潇筱",
            mobile="13800000000",
        )
        db = _FakeDb([user])
        employee_db = _FakeEmployeeDb(
            [
                _row(
                    openid="openid-new",
                    job_no="BB363",
                    display_name="Shelly Wang",
                    mobile="13800000000",
                )
            ]
        )

        result = employee_sync.sync_employee_profiles(db, employee_db)

        self.assertEqual(result["created"], 0)
        self.assertEqual(result["skipped"]["username_exists"], 1)
        self.assertEqual(user.job_no, "HB009")
        self.assertEqual(user.openid, "openid-old")

    def test_skips_reuse_when_two_local_users_share_name_and_mobile(self):
        first = SysUser(
            username="13800000000",
            openid="openid-a",
            job_no="BB396",
            display_name="Yue Tong",
            mobile="13800000000",
        )
        second = SysUser(
            username="13800000000-2",
            openid="openid-b",
            job_no="BB396",
            display_name="Yue Tong",
            mobile="13800000000",
        )
        db = _FakeDb([first, second])
        employee_db = _FakeEmployeeDb(
            [
                _row(
                    openid="openid-new",
                    job_no="BB396",
                    display_name="Yue Tong",
                    mobile="13800000000",
                )
            ]
        )

        result = employee_sync.sync_employee_profiles(db, employee_db)

        self.assertEqual(result["created"], 0)
        self.assertEqual(result["skipped"]["ambiguous_local_user"], 1)
        self.assertEqual(first.openid, "openid-a")
        self.assertEqual(second.openid, "openid-b")

    def test_does_not_create_when_external_openid_is_missing(self):
        db = _FakeDb([])
        employee_db = _FakeEmployeeDb(
            [_row(openid="", mobile="13800000009", is_locked=0)]
        )

        result = employee_sync.sync_employee_profiles(db, employee_db)

        self.assertEqual(result["created"], 0)
        self.assertEqual(db.created, [])
