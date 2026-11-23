"""员工资料外部同步：匹配优先级、离职停用、空值保留与新建约束。"""

from datetime import date
import itertools

from sqlalchemy import select

from models.system import SysUser
from modules.system import employee_sync
from support import DbTestCase, FakeSourceDb


class EmployeeSyncTests(DbTestCase):
    tables = (SysUser,)

    def setUp(self):
        super().setUp()
        self._external_ids = itertools.count(1)

    def _row(self, **overrides) -> dict:
        row = {
            "external_id": next(self._external_ids),
            "openid": "openid-new",
            "job_no": "E001",
            "display_name": "张三",
            "mobile": "13800000000",
            "email": "zhangsan@example.com",
            "department": "研发部",
            "group_name": "研发一组",
            "position_title": "研究员",
            "sex": 1,
            "is_locked": 0,
            "leave_date": None,
        }
        row.update(overrides)
        return row

    def _seed_users(self, *users: SysUser) -> None:
        self.db.add_all(users)
        self.db.commit()

    def _all_users(self) -> list[SysUser]:
        with self.Session() as db:
            return list(db.scalars(select(SysUser).order_by(SysUser.id)).all())

    def test_matching_openid_with_leave_date_updates_profile_and_disables_account(self):
        self._seed_users(
            SysUser(
                username="13800000000",
                openid="openid-1",
                job_no="E001",
                display_name="张三",
                employment_status="active",
                status="active",
            )
        )
        source_db = FakeSourceDb(
            [self._row(openid="openid-1", mobile="13900000000", leave_date=date(2026, 1, 1))]
        )

        result = employee_sync.sync_employee_profiles(self.db, source_db)

        self.assertFalse(self.db.in_transaction())
        self.assertEqual(result["updated"], 1)
        self.assertEqual(result["disabled_on_resignation"], 1)
        users = self._all_users()
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].mobile, "13900000000")
        self.assertEqual(users[0].employment_status, "resigned")
        self.assertEqual(users[0].status, "disabled")

    def test_already_resigned_active_user_keeps_active_status_on_resync(self):
        # 历史已离职但人工保留启用状态的账号，再次同步不重复停用
        self._seed_users(
            SysUser(
                username="13900000000",
                openid="openid-1",
                job_no="E001",
                display_name="张三",
                mobile="13900000000",
                email="zhangsan@example.com",
                department="研发部",
                group_name="研发一组",
                position_title="研究员",
                gender="male",
                employment_status="resigned",
                status="active",
            )
        )
        source_db = FakeSourceDb(
            [self._row(openid="openid-1", mobile="13900000000", leave_date=date(2026, 1, 1))]
        )

        result = employee_sync.sync_employee_profiles(self.db, source_db)

        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["disabled_on_resignation"], 0)
        users = self._all_users()
        self.assertEqual(users[0].status, "active")
        self.assertEqual(users[0].employment_status, "resigned")

    def test_matching_openid_with_new_job_no_updates_job_no_and_department(self):
        self._seed_users(
            SysUser(
                username="13800000000",
                openid="openid-1",
                job_no="E001",
                display_name="张三",
                mobile="13800000000",
                department="旧部门",
            )
        )
        source_db = FakeSourceDb(
            [self._row(openid="openid-1", job_no="E999", mobile="13900000000", department="新部门")]
        )

        result = employee_sync.sync_employee_profiles(self.db, source_db)

        self.assertEqual(result["updated"], 1)
        self.assertEqual(result["skipped"]["job_no_mismatch"], 0)
        users = self._all_users()
        self.assertEqual(users[0].job_no, "E999")
        self.assertEqual(users[0].department, "新部门")
        self.assertEqual(users[0].mobile, "13900000000")

    def test_unmatched_source_rows_create_only_unlocked_unique_openid_users(self):
        source_db = FakeSourceDb(
            [
                self._row(openid="openid-new", job_no="E001", mobile="13800000001"),
                self._row(openid="openid-locked", job_no="E002", mobile="13800000002", is_locked=1),
                self._row(openid="openid-dup", job_no="E003", mobile="13800000003"),
                self._row(openid="openid-dup", job_no="E004", mobile="13800000004"),
                self._row(openid="", job_no="E005", mobile="13800000009", is_locked=0),
            ]
        )

        result = employee_sync.sync_employee_profiles(self.db, source_db)

        self.assertFalse(self.db.in_transaction())
        self.assertEqual(result["source_total"], 5)
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["skipped"]["locked_new_user"], 1)
        self.assertEqual(result["skipped"]["duplicate_openid"], 2)
        users = self._all_users()
        self.assertEqual(len(users), 1)
        created = users[0]
        self.assertEqual(created.username, "13800000001")
        self.assertEqual(created.openid, "openid-new")
        self.assertEqual(created.department, "研发部")
        self.assertEqual(created.group_name, "研发一组")
        self.assertTrue(created.password_hash.startswith("pbkdf2_sha256$"))
        self.assertEqual(created.status, "active")

        usernames = {user.username for user in users}
        for reason, rejected_mobile in (
            ("locked_new_user", "13800000002"),
            ("duplicate_openid", "13800000003"),
            ("missing_openid", "13800000009"),
        ):
            with self.subTest(reason=reason):
                self.assertNotIn(rejected_mobile, usernames)

    def test_shared_openid_with_single_unlocked_row_updates_from_unlocked_row(self):
        self._seed_users(
            SysUser(
                username="13800000000",
                openid="openid-shared",
                job_no="E001",
                display_name="张三",
                mobile="13800000000",
                department="旧部门",
                employment_status="active",
                status="active",
            )
        )
        source_db = FakeSourceDb(
            [
                self._row(
                    openid="openid-shared",
                    job_no="E001",
                    display_name="张三",
                    department="旧部门",
                    is_locked=1,
                ),
                self._row(
                    openid="openid-shared",
                    job_no="E002",
                    display_name="张三",
                    department="新部门",
                    is_locked=0,
                ),
            ]
        )

        result = employee_sync.sync_employee_profiles(self.db, source_db)

        self.assertEqual(result["updated"], 1)
        self.assertEqual(result["skipped"]["duplicate_openid"], 0)
        users = self._all_users()
        self.assertEqual(users[0].job_no, "E002")
        self.assertEqual(users[0].department, "新部门")

    def test_cleared_external_openid_matches_name_and_job_no_disables_and_keeps_local_fields(self):
        self._seed_users(
            SysUser(
                username="13800000020",
                openid="openid-keep",
                job_no="E003",
                display_name="李四",
                mobile="13800000020",
                email="lisi@example.com",
                department="研发部",
                group_name="免疫组",
                position_title="研究员",
                gender="female",
                employment_status="active",
                status="active",
            )
        )
        source_db = FakeSourceDb(
            [
                self._row(
                    openid="",
                    job_no="E003",
                    display_name="李四",
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

        result = employee_sync.sync_employee_profiles(self.db, source_db)

        self.assertEqual(result["created"], 0)
        self.assertEqual(result["updated"], 1)
        self.assertEqual(result["disabled_on_resignation"], 1)
        users = self._all_users()
        self.assertEqual(len(users), 1)
        user = users[0]
        self.assertEqual(user.openid, "openid-keep")
        self.assertEqual(user.employment_status, "resigned")
        self.assertEqual(user.status, "disabled")
        self.assertEqual(user.mobile, "13800000020")
        self.assertEqual(user.email, "lisi@example.com")
        self.assertEqual(user.department, "研发部")
        self.assertEqual(user.group_name, "免疫组")
        self.assertEqual(user.position_title, "研究员")
        self.assertEqual(user.gender, "female")

    def test_name_and_job_no_fallback_with_unused_openid_rebinds_openid(self):
        self._seed_users(
            SysUser(
                username="13800000000",
                openid="openid-old",
                job_no="E004",
                display_name="王五",
                mobile="13800000000",
                employment_status="active",
                status="active",
            )
        )
        source_db = FakeSourceDb(
            [
                self._row(
                    openid="openid-new",
                    job_no="E004",
                    display_name="王五",
                    mobile="13800000000",
                )
            ]
        )

        result = employee_sync.sync_employee_profiles(self.db, source_db)

        self.assertEqual(result["updated"], 1)
        users = self._all_users()
        self.assertEqual(users[0].openid, "openid-new")

    def test_shared_external_openid_owned_by_another_user_is_not_stolen_on_fallback(self):
        self._seed_users(
            SysUser(
                username="13800000001",
                openid="openid-taken",
                job_no="E100",
                display_name="赵六",
                mobile="13800000001",
            ),
            SysUser(
                username="13800000000",
                openid="openid-old",
                job_no="E004",
                display_name="王五",
                mobile="13800000000",
            ),
        )
        source_db = FakeSourceDb(
            [
                self._row(
                    openid="openid-taken",
                    job_no="E100",
                    display_name="赵六",
                    mobile="13800000001",
                ),
                self._row(
                    openid="openid-taken",
                    job_no="E004",
                    display_name="王五",
                    mobile="13800000000",
                ),
            ]
        )

        result = employee_sync.sync_employee_profiles(self.db, source_db)

        self.assertEqual(result["skipped"]["duplicate_openid"], 2)
        by_job_no = {user.job_no: user for user in self._all_users()}
        self.assertEqual(by_job_no["E100"].openid, "openid-taken")
        self.assertEqual(by_job_no["E004"].openid, "openid-old")

    def test_new_openid_matching_unique_name_and_mobile_reuses_existing_user(self):
        self._seed_users(
            SysUser(
                username="13800000000",
                openid="openid-old",
                job_no="E001",
                display_name="张三",
                mobile="13800000000",
                department="旧部门",
            )
        )
        source_db = FakeSourceDb(
            [
                self._row(
                    openid="openid-new",
                    job_no="E006",
                    display_name="张三",
                    mobile="13800000000",
                    department="新部门",
                )
            ]
        )

        result = employee_sync.sync_employee_profiles(self.db, source_db)

        self.assertEqual(result["created"], 0)
        self.assertEqual(result["updated"], 1)
        users = self._all_users()
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].job_no, "E006")
        self.assertEqual(users[0].department, "新部门")
        self.assertEqual(users[0].openid, "openid-new")
        self.assertEqual(users[0].username, "13800000000")

    def test_new_openid_with_same_mobile_and_different_name_skips_username_conflict(self):
        self._seed_users(
            SysUser(
                username="13800000000",
                openid="openid-old",
                job_no="E001",
                display_name="张三",
                mobile="13800000000",
            )
        )
        source_db = FakeSourceDb(
            [
                self._row(
                    openid="openid-new",
                    job_no="E002",
                    display_name="李四",
                    mobile="13800000000",
                )
            ]
        )

        result = employee_sync.sync_employee_profiles(self.db, source_db)

        self.assertEqual(result["created"], 0)
        self.assertEqual(result["skipped"]["username_exists"], 1)
        users = self._all_users()
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].job_no, "E001")
        self.assertEqual(users[0].openid, "openid-old")
        self.assertEqual(users[0].display_name, "张三")

    def test_duplicate_local_name_and_mobile_skips_ambiguous_reuse(self):
        self._seed_users(
            SysUser(
                username="13800000000",
                openid="openid-a",
                job_no="E003",
                display_name="王五",
                mobile="13800000000",
            ),
            SysUser(
                username="13800000000-2",
                openid="openid-b",
                job_no="E003",
                display_name="王五",
                mobile="13800000000",
            ),
        )
        source_db = FakeSourceDb(
            [
                self._row(
                    openid="openid-new",
                    job_no="E003",
                    display_name="王五",
                    mobile="13800000000",
                )
            ]
        )

        result = employee_sync.sync_employee_profiles(self.db, source_db)

        self.assertEqual(result["created"], 0)
        self.assertEqual(result["skipped"]["ambiguous_local_user"], 1)
        users = self._all_users()
        self.assertEqual(len(users), 2)
        self.assertEqual([user.openid for user in users], ["openid-a", "openid-b"])

    def test_dry_run_rolls_back_created_and_updated_users(self):
        self._seed_users(
            SysUser(
                username="13800000000",
                openid="openid-1",
                job_no="E001",
                display_name="张三",
                department="旧部门",
            )
        )
        source_db = FakeSourceDb(
            [
                self._row(openid="openid-1", job_no="E001", department="新部门"),
                self._row(openid="openid-2", job_no="E002", mobile="13800000002"),
            ]
        )

        result = employee_sync.sync_employee_profiles(self.db, source_db, dry_run=True)

        self.assertFalse(self.db.in_transaction())
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["updated"], 1)
        users = self._all_users()
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].department, "旧部门")
