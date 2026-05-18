from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from models.system import SysUser
from modules.auth.security import hash_password


AUTO_CREATED_PASSWORD_DIGITS = 20

EMPLOYEE_SOURCE_SQL = text(
    """
    SELECT
      e.id AS external_id,
      e.sname AS display_name,
      e.snum AS job_no,
      e.sex AS sex,
      e.mobile AS mobile,
      e.email AS email,
      e.leave_date AS leave_date,
      e.is_locked AS is_locked,
      e.post AS position_title,
      e.cloud_open_id AS openid,
      p.sname AS department,
      d.sname AS group_name
    FROM org_emp e
    LEFT JOIN org_depart d ON e.depart_id = d.id
    LEFT JOIN org_depart p ON d.top_id = p.id
    WHERE e.cloud_open_id IS NOT NULL AND e.cloud_open_id <> ''
    """
)


@dataclass(frozen=True)
class ExternalEmployee:
    external_id: int | None
    openid: str
    job_no: str
    display_name: str | None
    mobile: str | None
    email: str | None
    department: str | None
    group_name: str | None
    position_title: str | None
    gender: str
    is_locked: bool
    leave_date: date | datetime | None


def sync_employee_profiles(db: Session, employee_db: Session, *, dry_run: bool = False) -> dict[str, Any]:
    """Sync basic employee profile fields from the external project-management DB.

    The sync intentionally does not touch passwords, roles, permission overrides, or superuser flags.
    """
    external_employees = _load_external_employees(employee_db)
    duplicate_openids = _find_duplicate_values([employee.openid for employee in external_employees])
    duplicate_mobiles = _find_duplicate_values(
        [employee.mobile for employee in external_employees if employee.mobile]
    )

    existing_users = db.scalars(select(SysUser).where(SysUser.openid.is_not(None))).all()
    users_by_openid = {str(user.openid).strip(): user for user in existing_users if user.openid}
    existing_usernames = set(db.scalars(select(SysUser.username)).all())

    result: dict[str, Any] = {
        "source_total": len(external_employees),
        "created": 0,
        "updated": 0,
        "skipped": {
            "duplicate_openid": 0,
            "job_no_mismatch": 0,
            "missing_job_no": 0,
            "locked_new_user": 0,
            "missing_mobile": 0,
            "duplicate_mobile": 0,
            "username_exists": 0,
        },
        "disabled_on_resignation": 0,
    }

    for employee in external_employees:
        if employee.openid in duplicate_openids:
            result["skipped"]["duplicate_openid"] += 1
            continue

        user = users_by_openid.get(employee.openid)
        if user:
            if not employee.job_no:
                result["skipped"]["missing_job_no"] += 1
                continue
            if user.job_no and user.job_no != employee.job_no:
                result["skipped"]["job_no_mismatch"] += 1
                continue
            changed, disabled_account = _apply_employee_update(user, employee)
            if changed:
                result["updated"] += 1
            if disabled_account:
                result["disabled_on_resignation"] += 1
            continue

        if employee.is_locked:
            result["skipped"]["locked_new_user"] += 1
            continue
        if not employee.mobile:
            result["skipped"]["missing_mobile"] += 1
            continue
        if employee.mobile in duplicate_mobiles:
            result["skipped"]["duplicate_mobile"] += 1
            continue
        if employee.mobile in existing_usernames:
            result["skipped"]["username_exists"] += 1
            continue

        user = SysUser(
            username=employee.mobile,
            display_name=employee.display_name,
            password_hash=hash_password(_generate_random_numeric_password()),
            openid=employee.openid,
            job_no=employee.job_no,
            department=employee.department,
            group_name=employee.group_name,
            position_title=employee.position_title,
            gender=employee.gender,
            employment_status="resigned" if employee.leave_date else "active",
            email=employee.email,
            mobile=employee.mobile,
            status="active",
        )
        db.add(user)
        users_by_openid[employee.openid] = user
        existing_usernames.add(employee.mobile)
        result["created"] += 1

    if dry_run:
        db.rollback()
    else:
        db.commit()
    return result


def _load_external_employees(employee_db: Session) -> list[ExternalEmployee]:
    rows = employee_db.execute(EMPLOYEE_SOURCE_SQL).mappings().all()
    return [_external_employee_from_row(row) for row in rows]


def _external_employee_from_row(row: dict[str, Any]) -> ExternalEmployee:
    return ExternalEmployee(
        external_id=row.get("external_id"),
        openid=_clean(row.get("openid")) or "",
        job_no=_clean(row.get("job_no")) or "",
        display_name=_clean(row.get("display_name")),
        mobile=_clean(row.get("mobile")),
        email=_clean(row.get("email")),
        department=_clean(row.get("department")),
        group_name=_clean(row.get("group_name")),
        position_title=_clean(row.get("position_title")),
        gender=_normalize_gender(row.get("sex")),
        is_locked=bool(row.get("is_locked")),
        leave_date=row.get("leave_date"),
    )


def _apply_employee_update(user: SysUser, employee: ExternalEmployee) -> tuple[bool, bool]:
    changed = False
    disabled_account = False
    updates = {
        "job_no": employee.job_no or user.job_no,
        "display_name": employee.display_name,
        "department": employee.department,
        "group_name": employee.group_name,
        "position_title": employee.position_title,
        "gender": employee.gender,
        "email": employee.email,
        "mobile": employee.mobile,
    }
    if employee.leave_date:
        updates["employment_status"] = "resigned"
        # 仅当本次由在职变为离职时禁用账号；已是离职但仍为启用的历史数据不改动
        if user.employment_status != "resigned":
            updates["status"] = "disabled"
            disabled_account = True

    for field, value in updates.items():
        if getattr(user, field) != value:
            setattr(user, field, value)
            changed = True
    return changed, disabled_account


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text_value = str(value).strip()
    return text_value or None


def _normalize_gender(value: Any) -> str:
    if value == 1 or str(value).strip() in {"1", "男", "male"}:
        return "male"
    if value == 0 or str(value).strip() in {"0", "女", "female"}:
        return "female"
    return "unknown"


def _find_duplicate_values(values: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _generate_random_numeric_password(length: int = AUTO_CREATED_PASSWORD_DIGITS) -> str:
    return "".join(str(secrets.randbelow(10)) for _ in range(length))
