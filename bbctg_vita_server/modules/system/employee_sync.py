from __future__ import annotations

import secrets
from collections import defaultdict
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

    Identity is resolved in three short passes:
    1. unique Yunzhijia openid (if several source rows share one, keep the unlocked row)
    2. leftover local users by exact name + job number
    3. create only when unlocked and unmatched; reuse one local user with the same name + mobile

    The sync intentionally does not touch passwords, roles, permission overrides, or superuser flags.
    """
    external_employees = _load_external_employees(employee_db)
    existing_users = list(db.scalars(select(SysUser)).all())
    users_by_openid = {str(user.openid).strip(): user for user in existing_users if user.openid}
    existing_usernames = {user.username for user in existing_users if user.username}

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
            "ambiguous_local_user": 0,
        },
        "disabled_on_resignation": 0,
    }

    processed_users: set[int] = set()
    used_employees: set[int] = set()
    ambiguous_openids: set[str] = set()

    def mark_updated(user: SysUser, employee: ExternalEmployee, changed: bool, disabled_account: bool) -> None:
        processed_users.add(id(user))
        used_employees.add(id(employee))
        if changed:
            result["updated"] += 1
        if disabled_account:
            result["disabled_on_resignation"] += 1

    for openid, group in _group_by(external_employees, lambda item: item.openid or None).items():
        chosen = _choose_openid_employee(group)
        if chosen is None:
            ambiguous_openids.add(openid)
            result["skipped"]["duplicate_openid"] += len(group)
            continue
        user = users_by_openid.get(openid)
        if not user:
            continue
        if not chosen.job_no:
            result["skipped"]["missing_job_no"] += 1
            continue
        openid_to_write = _openid_for_update(user, chosen, users_by_openid)
        _bind_openid(user, openid_to_write, users_by_openid)
        changed, disabled_account = _apply_employee_update(user, chosen, openid=openid_to_write)
        mark_updated(user, chosen, changed, disabled_account)

    local_by_name_job = _group_by(existing_users, _user_name_job)
    source_by_name_job = _group_by(external_employees, _employee_name_job)
    for user in existing_users:
        if id(user) in processed_users:
            continue
        key = _user_name_job(user)
        if key is None or len(local_by_name_job.get(key, [])) != 1:
            continue
        hits = source_by_name_job.get(key, [])
        if len(hits) != 1:
            continue
        employee = hits[0]
        openid_to_write = _openid_for_update(user, employee, users_by_openid)
        _bind_openid(user, openid_to_write, users_by_openid)
        changed, disabled_account = _apply_employee_update(user, employee, openid=openid_to_write)
        mark_updated(user, employee, changed, disabled_account)

    create_candidates = [
        employee
        for employee in external_employees
        if employee.openid
        and id(employee) not in used_employees
        and employee.openid not in ambiguous_openids
        and not employee.is_locked
    ]
    duplicate_mobiles = _find_duplicate_values(
        [employee.mobile for employee in create_candidates if employee.mobile]
    )

    for employee in external_employees:
        if id(employee) in used_employees or employee.openid in ambiguous_openids:
            continue
        if not employee.openid:
            continue
        if users_by_openid.get(employee.openid):
            continue
        if employee.is_locked:
            result["skipped"]["locked_new_user"] += 1
            continue
        if not employee.mobile:
            result["skipped"]["missing_mobile"] += 1
            continue

        reuse_candidates = [
            user
            for user in existing_users
            if _clean(user.mobile) == employee.mobile
            and _clean(user.display_name) == employee.display_name
        ]
        if len(reuse_candidates) > 1:
            result["skipped"]["ambiguous_local_user"] += 1
            continue
        if len(reuse_candidates) == 1:
            user = reuse_candidates[0]
            openid_to_write = _openid_for_update(user, employee, users_by_openid)
            _bind_openid(user, openid_to_write, users_by_openid)
            changed, disabled_account = _apply_employee_update(user, employee, openid=openid_to_write)
            mark_updated(user, employee, changed, disabled_account)
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
        existing_users.append(user)
        users_by_openid[employee.openid] = user
        existing_usernames.add(employee.mobile)
        used_employees.add(id(employee))
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


def _apply_employee_update(
    user: SysUser,
    employee: ExternalEmployee,
    *,
    openid: str | None = None,
) -> tuple[bool, bool]:
    changed = False
    disabled_account = False
    updates = {
        "job_no": _prefer(employee.job_no, user.job_no),
        "display_name": _prefer(employee.display_name, user.display_name),
        "department": _prefer(employee.department, user.department),
        "group_name": _prefer(employee.group_name, user.group_name),
        "position_title": _prefer(employee.position_title, user.position_title),
        "gender": _prefer_gender(employee.gender, user.gender),
        "email": _prefer(employee.email, user.email),
        "mobile": _prefer(employee.mobile, user.mobile),
    }
    if openid:
        updates["openid"] = openid
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


def _prefer(new_value: Any, old_value: Any) -> Any:
    return new_value if _clean(new_value) is not None else old_value


def _prefer_gender(new_value: str, old_value: str | None) -> str | None:
    if new_value and new_value != "unknown":
        return new_value
    return old_value or new_value


def _choose_openid_employee(group: list[ExternalEmployee]) -> ExternalEmployee | None:
    if len(group) == 1:
        return group[0]
    unlocked = [employee for employee in group if not employee.is_locked]
    if len(unlocked) == 1:
        return unlocked[0]
    return None


def _openid_for_update(
    user: SysUser,
    employee: ExternalEmployee,
    users_by_openid: dict[str, SysUser],
) -> str | None:
    if not employee.openid:
        return None
    current = users_by_openid.get(employee.openid)
    if current is None or current is user:
        return employee.openid
    return None


def _bind_openid(user: SysUser, openid: str | None, users_by_openid: dict[str, SysUser]) -> None:
    if not openid:
        return
    previous = _clean(user.openid)
    if previous and users_by_openid.get(previous) is user and previous != openid:
        del users_by_openid[previous]
    users_by_openid[openid] = user


def _user_name_job(user: SysUser) -> tuple[str, str] | None:
    name = _clean(user.display_name)
    job_no = _clean(user.job_no)
    if not name or not job_no:
        return None
    return name, job_no


def _employee_name_job(employee: ExternalEmployee) -> tuple[str, str] | None:
    if not employee.display_name or not employee.job_no:
        return None
    return employee.display_name, employee.job_no


def _group_by(items: list[Any], key_fn) -> dict[Any, list[Any]]:
    groups: dict[Any, list[Any]] = defaultdict(list)
    for item in items:
        key = key_fn(item)
        if key is None:
            continue
        groups[key].append(item)
    return groups


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
