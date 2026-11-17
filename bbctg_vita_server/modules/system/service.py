"""系统管理：用户、角色、权限包、个人权限覆盖和操作日志查询。"""

from collections.abc import Iterable
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from core.errors import ForbiddenError, NotFoundError
from core.module_spec import Permission
from db.session import Base
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
from modules.auth.permissions import build_user_context, get_role_permissions
from modules.auth.security import hash_password
from modules.registry import PERMISSION_INDEX, RESOURCE_LABELS
from utils.filter_values import filter_terms, like_contains, like_literal, restrict

# 与操作日志表格「操作」列的显示名一致。搜索显示名时要能命中原始动作。
_LOG_ACTION_LABELS = {
    "POST /api/molecular-cell/library-orders/files/list": "刷新质检核对",
    "POST /api/discovery/synthesis-progress/check_remote": "核对外部合成订单",
    "POST /api/auth/user/change_password": "修改密码",
    "PUT /api/auth/user/profile": "更新个人资料",
    "POST /api/order-experiment/sync": "回传工单数据",
    "每天 01:00 自动更新免疫实验状态": "免疫状态自动更新",
    "每天 00:30 同步外部员工基础资料": "员工资料同步",
    "每天 00:45 同步外部靶点主数据": "靶点同步",
    "每天 01:15 自动更新抗体发现状态": "发现状态更新",
    "每天 02:00 同步镁伽非终态工单状态": "镁伽状态同步",
    "每隔 1 小时同步 One 合成订单与交付进度": "合成与验证外部订单同步",
    "Labillion 状态回调": "镁伽状态回调",
    "同步镁伽工单状态": "同步镁伽状态",
}

_USER_TEXT_FIELDS = (
    "display_name",
    "openid",
    "job_no",
    "department",
    "group_name",
    "position_title",
    "gender",
    "profile_signature",
    "employment_status",
    "email",
    "mobile",
    "status",
)


def list_users(
    db: Session,
    *,
    keyword: str = "",
    department: list[str] | None = None,
    group_name: list[str] | None = None,
    gender: list[str] | None = None,
    status: list[str] | None = None,
    employment_status: list[str] | None = None,
    role_id: list[str] | None = None,
    has_admin_role: list[str] | None = None,
    has_permission_override: list[str] | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    stmt = select(SysUser).order_by(SysUser.id.desc())
    compact_keyword = _compact_text(keyword)
    if compact_keyword:
        pattern = f"%{like_literal(compact_keyword)}%"
        stmt = stmt.where(
            (_compact_column(SysUser.username).like(pattern, escape="\\"))
            | (_compact_column(SysUser.display_name).like(pattern, escape="\\"))
            | (_compact_column(SysUser.job_no).like(pattern, escape="\\"))
        )
    stmt = restrict(stmt, department, lambda value: _compact_like(SysUser.department, value))
    stmt = restrict(stmt, group_name, lambda value: _compact_like(SysUser.group_name, value))
    stmt = restrict(stmt, gender, lambda value: SysUser.gender == value)
    stmt = restrict(stmt, status, lambda value: SysUser.status == value)
    stmt = restrict(stmt, employment_status, lambda value: SysUser.employment_status == value)
    stmt = _apply_user_role_filter(stmt, role_id)
    admin_user_ids = (
        select(SysUserRole.user_id)
        .join(SysRole, SysRole.id == SysUserRole.role_id)
        .where(SysRole.name.like("%管理员%"))
    )
    admin_terms = set(filter_terms(has_admin_role))
    if admin_terms == {"yes"}:
        stmt = stmt.where(SysUser.id.in_(admin_user_ids))
    elif admin_terms == {"no"}:
        stmt = stmt.where(SysUser.id.not_in(admin_user_ids))
    override_user_ids = select(SysUserPermissionOverride.user_id)
    override_terms = set(filter_terms(has_permission_override))
    if override_terms == {"yes"}:
        stmt = stmt.where(SysUser.id.in_(override_user_ids))
    elif override_terms == {"no"}:
        stmt = stmt.where(SysUser.id.not_in(override_user_ids))

    page = max(page, 1)
    page_size = min(max(page_size, 1), 200)
    filtered_users = stmt.order_by(None).subquery()
    total = db.scalar(select(func.count()).select_from(filtered_users)) or 0
    active_total = (
        db.scalar(
            select(func.count())
            .select_from(filtered_users)
            .where(filtered_users.c.status == "active")
        )
        or 0
    )
    users = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    role_map = _get_user_role_map(db, [user.id for user in users])
    return {
        "items": [_user_to_dict(user, role_map.get(user.id, [])) for user in users],
        "page": page,
        "page_size": page_size,
        "total": total,
        "active_total": active_total,
    }


def user_suggestions(db: Session, field: str, keyword: str = "", limit: int = 20) -> list[str]:
    compact_keyword = _compact_text(keyword)
    pattern = f"%{like_literal(compact_keyword)}%"
    limit = min(max(limit, 1), 200)

    if field == "department":
        stmt = select(SysUser.department).where(SysUser.department.is_not(None))
        if compact_keyword:
            stmt = stmt.where(_compact_column(SysUser.department).like(pattern, escape="\\"))
        items = db.scalars(stmt.distinct().order_by(SysUser.department).limit(limit)).all()
        return [item for item in items if item]

    if field == "group_name":
        stmt = select(SysUser.group_name).where(SysUser.group_name.is_not(None))
        if compact_keyword:
            stmt = stmt.where(_compact_column(SysUser.group_name).like(pattern, escape="\\"))
        items = db.scalars(stmt.distinct().order_by(SysUser.group_name).limit(limit)).all()
        return [item for item in items if item]

    if field == "keyword":
        stmt = select(SysUser).order_by(SysUser.id.desc())
        if compact_keyword:
            stmt = stmt.where(
                (_compact_column(SysUser.username).like(pattern, escape="\\"))
                | (_compact_column(SysUser.display_name).like(pattern, escape="\\"))
                | (_compact_column(SysUser.job_no).like(pattern, escape="\\"))
            )
        users = db.scalars(stmt.limit(limit)).all()
        values: list[str] = []
        seen: set[str] = set()
        for user in users:
            for value in [user.display_name, user.username, user.job_no]:
                if (
                    value
                    and value not in seen
                    and (not compact_keyword or compact_keyword in _compact_text(value))
                ):
                    values.append(value)
                    seen.add(value)
                if len(values) >= limit:
                    break
            if len(values) >= limit:
                break
        return values

    raise ValueError("不支持的候选字段")


def _get_manageable_user(db: Session, user_id: int, actor: SysUser) -> SysUser:
    """超级管理员账号只有超级管理员能改、重置密码或删除，免得管理用户的人借此拿到全部权限。"""
    user = db.get(SysUser, user_id)
    if not user:
        raise NotFoundError("用户不存在")
    if user.is_superuser and not actor.is_superuser:
        raise ForbiddenError("只有超级管理员可以修改超级管理员账号")
    return user


def save_user(db: Session, data: dict[str, Any], *, actor: SysUser) -> int:
    user_id = data.get("id")
    if user_id:
        user = _get_manageable_user(db, int(user_id), actor)
    else:
        username = data.get("username", "").strip()
        if not username:
            raise ValueError("请输入账号")
        user = SysUser(username=username)
        password = str(data.get("password") or "")
        if len(password) < 6:
            raise ValueError("新增用户密码至少需要 6 位")
        user.password_hash = hash_password(password)
        db.add(user)

    if "is_superuser" in data:
        requested_superuser = bool(data.get("is_superuser"))
        if requested_superuser != bool(user.is_superuser) and not actor.is_superuser:
            raise ForbiddenError("只有超级管理员可以修改超级管理员开关")
        user.is_superuser = requested_superuser

    for field in _USER_TEXT_FIELDS:
        if field in data:
            setattr(user, field, data.get(field) or None)
    user.employment_status = data.get("employment_status") or user.employment_status or "active"
    db.flush()
    if "role_ids" in data:
        role_ids = _unique_ints(data.get("role_ids") or [])
        _ensure_role_ids_exist(db, role_ids)
        _replace_user_roles(db, user.id, role_ids)
    db.commit()
    return user.id


def delete_user(db: Session, user_id: int, *, actor: SysUser) -> None:
    user = _get_manageable_user(db, user_id, actor)
    if user.id == actor.id:
        raise ValueError("不能删除当前登录账号")
    _delete_matching(db, SysUserRole, SysUserRole.user_id == user.id)
    _delete_matching(db, SysUserPermissionOverride, SysUserPermissionOverride.user_id == user.id)
    db.delete(user)
    db.commit()


def batch_update_user_roles(db: Session, data: dict[str, Any]) -> int:
    user_ids = [int(user_id) for user_id in data.get("user_ids") or [] if user_id]
    role_ids = [int(role_id) for role_id in data.get("role_ids") or [] if role_id]
    mode = data.get("mode") or "replace"
    if not user_ids:
        raise ValueError("请选择用户")
    if mode not in {"append", "replace"}:
        raise ValueError("批量设置模式不正确")
    _ensure_user_ids_exist(db, user_ids)
    _ensure_role_ids_exist(db, role_ids)

    for user_id in user_ids:
        if mode == "replace":
            _replace_user_roles(db, user_id, role_ids)
        else:
            existing = set(_get_user_role_map(db, [user_id]).get(user_id, []))
            _replace_user_roles(db, user_id, sorted(existing | set(role_ids)))
    db.commit()
    return len(user_ids)


def reset_password(db: Session, user_id: int, password: str, *, actor: SysUser) -> None:
    user = _get_manageable_user(db, user_id, actor)
    if len(password) < 6:
        raise ValueError("密码至少需要 6 位")
    user.password_hash = hash_password(password)
    db.commit()


def get_user_permission_overrides(db: Session, user_id: int) -> dict[str, Any]:
    user = db.get(SysUser, user_id)
    if not user:
        raise NotFoundError("用户不存在")

    context = build_user_context(db, user)
    role_permissions = get_role_permissions(db, user.id)
    overrides = db.scalars(
        select(SysUserPermissionOverride).where(SysUserPermissionOverride.user_id == user.id)
    ).all()
    return {
        "user": _user_to_dict(user, _get_user_role_map(db, [user.id]).get(user.id, [])),
        "role_permissions": role_permissions,
        "effective_permissions": context.permissions,
        "overrides": [_override_to_dict(override) for override in overrides],
    }


def save_user_permission_overrides(db: Session, user_id: int, data: dict[str, Any]) -> None:
    user = db.get(SysUser, user_id)
    if not user:
        raise NotFoundError("用户不存在")

    allow_codes = {str(code) for code in data.get("allow_codes") or [] if code}
    deny_codes = {str(code) for code in data.get("deny_codes") or [] if code}
    reason = (data.get("reason") or "").strip() or None
    _ensure_permission_codes_exist(allow_codes | deny_codes)

    desired = {
        **{code: "allow" for code in allow_codes - deny_codes},
        **{code: "deny" for code in deny_codes},
    }
    existing = {
        row.permission_code: row
        for row in db.scalars(
            select(SysUserPermissionOverride).where(
                SysUserPermissionOverride.user_id == user.id
            )
        ).all()
    }
    for code, row in existing.items():
        if code not in desired:
            db.delete(row)
        else:
            row.effect = desired[code]
            row.reason = reason
    for code, effect in sorted(desired.items()):
        if code not in existing:
            db.add(
                SysUserPermissionOverride(
                    user_id=user.id,
                    permission_code=code,
                    effect=effect,
                    reason=reason,
                )
            )
    db.commit()


def list_roles(db: Session) -> list[dict[str, Any]]:
    roles = db.scalars(select(SysRole).order_by(SysRole.sort_order, SysRole.id)).all()
    bundle_map = _get_role_bundle_map(db, [role.id for role in roles])
    return [_role_to_dict(role, bundle_map.get(role.id, [])) for role in roles]


def save_role(db: Session, data: dict[str, Any]) -> int:
    role_id = data.get("id")
    if role_id:
        role = db.get(SysRole, int(role_id))
        if not role:
            raise NotFoundError("角色不存在")
    else:
        code = data.get("code", "").strip()
        if not code:
            raise ValueError("请输入角色编码")
        role = SysRole(code=code)
        db.add(role)
    if not str(data.get("name") or "").strip():
        raise ValueError("请输入角色名称")
    for field in ["name", "description", "status", "sort_order"]:
        if field in data:
            setattr(role, field, data.get(field))
    db.flush()
    if "bundle_codes" in data:
        bundle_codes = _unique_strings(data.get("bundle_codes") or [])
        _ensure_bundle_codes_exist(db, bundle_codes)
        _replace_role_bundles(db, role.id, bundle_codes)
    db.commit()
    return role.id


def delete_role(db: Session, role_id: int) -> None:
    role = db.get(SysRole, role_id)
    if not role:
        raise NotFoundError("角色不存在")
    _delete_matching(db, SysUserRole, SysUserRole.role_id == role.id)
    _delete_matching(db, SysRolePermissionBundle, SysRolePermissionBundle.role_id == role.id)
    db.delete(role)
    db.commit()


def list_permissions() -> list[dict[str, Any]]:
    entries = sorted(PERMISSION_INDEX.values(), key=lambda entry: entry[1].sort_order)
    return [_permission_to_dict(access.module, permission) for access, permission in entries]


def list_permission_bundles(db: Session) -> list[dict[str, Any]]:
    bundles = db.scalars(select(SysPermissionBundle).order_by(SysPermissionBundle.sort_order, SysPermissionBundle.id)).all()
    item_map = _get_bundle_item_map(db, [bundle.code for bundle in bundles])
    return [_bundle_to_dict(bundle, item_map.get(bundle.code, [])) for bundle in bundles]


def save_permission_bundle(db: Session, data: dict[str, Any]) -> int:
    bundle_id = data.get("id")
    if bundle_id:
        bundle = db.get(SysPermissionBundle, int(bundle_id))
        if not bundle:
            raise NotFoundError("权限包不存在")
    else:
        code = str(data.get("code") or "").strip()
        if not code:
            raise ValueError("请输入权限包编码")
        bundle = SysPermissionBundle(code=code)
        db.add(bundle)

    for field in ["name", "module", "description", "status", "sort_order"]:
        if field in data:
            setattr(bundle, field, data.get(field))
    if not bundle.name:
        raise ValueError("请输入权限包名称")
    if not bundle.module:
        raise ValueError("请选择所属模块")
    db.flush()

    permission_codes = [str(code) for code in data.get("permission_codes") or [] if code]
    _ensure_permission_codes_exist(permission_codes)
    _replace_bundle_permissions(db, bundle.code, permission_codes)
    db.commit()
    return bundle.id


def delete_permission_bundle(db: Session, data: dict[str, Any]) -> None:
    bundle_id = data.get("id")
    bundle = db.get(SysPermissionBundle, int(bundle_id)) if bundle_id else None
    if not bundle and data.get("code"):
        bundle = db.scalar(select(SysPermissionBundle).where(SysPermissionBundle.code == str(data.get("code"))))
    if not bundle:
        raise NotFoundError("权限包不存在")
    _delete_matching(db, SysRolePermissionBundle, SysRolePermissionBundle.bundle_code == bundle.code)
    _delete_matching(db, SysPermissionBundleItem, SysPermissionBundleItem.bundle_code == bundle.code)
    db.delete(bundle)
    db.commit()


def list_operation_logs(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    operator: str = "",
    action: str = "",
    target_type: list[str] | None = None,
    target: str = "",
    source: list[str] | None = None,
    change: str = "",
    result: list[str] | None = None,
    error_message: str = "",
    operation_type: list[str] | None = None,
    request_id: str = "",
    date_start: str = "",
    date_end: str = "",
) -> dict[str, Any]:
    page = max(int(page or 1), 1)
    page_size = min(max(int(page_size or 50), 1), 500)
    stmt = select(SysOperationLog)
    operator = operator.strip()
    if operator:
        pattern = f"%{like_literal(operator)}%"
        stmt = stmt.where(
            or_(
                SysOperationLog.username.like(pattern, escape="\\"),
                SysOperationLog.operator_name.like(pattern, escape="\\"),
            )
        )
    action = action.strip()
    if action:
        pattern = f"%{like_literal(action)}%"
        action_match = [
            SysOperationLog.operation_name.like(pattern, escape="\\"),
            SysOperationLog.action.like(pattern, escape="\\"),
        ]
        for raw, label in _LOG_ACTION_LABELS.items():
            if action in label:
                action_match.append(SysOperationLog.operation_name == raw)
                action_match.append(SysOperationLog.action == raw)
        stmt = stmt.where(or_(*action_match))
    stmt = restrict(stmt, _expand_target_type_terms(target_type), lambda value: SysOperationLog.target_type == value)
    target = target.strip()
    if target:
        pattern = f"%{like_literal(target)}%"
        stmt = stmt.where(
            or_(
                SysOperationLog.target_label.like(pattern, escape="\\"),
                SysOperationLog.target_id.like(pattern, escape="\\"),
            )
        )
    stmt = restrict(stmt, source, lambda value: SysOperationLog.source == value)
    change = change.strip()
    if change:
        pattern = f"%{like_literal(change)}%"
        stmt = stmt.where(
            func.json_unquote(
                func.json_extract(SysOperationLog.detail, "$.change_summary")
            ).like(pattern, escape="\\")
        )
    stmt = restrict(stmt, result, lambda value: SysOperationLog.result == value)
    error_message = error_message.strip()
    if error_message:
        stmt = stmt.where(like_contains(SysOperationLog.error_message, error_message))
    stmt = restrict(stmt, operation_type, lambda value: SysOperationLog.operation_type == value)
    if request_id:
        stmt = stmt.where(SysOperationLog.request_id == request_id)
    if date_start:
        stmt = stmt.where(SysOperationLog.created_at >= _parse_log_datetime(date_start, end=False))
    if date_end:
        stmt = stmt.where(SysOperationLog.created_at <= _parse_log_datetime(date_end, end=True))
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    logs = db.scalars(stmt.order_by(SysOperationLog.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return {
        "items": [_log_to_dict(log) for log in logs],
        "total": total,
        "page": page,
        "page_size": page_size,
        "target_type_options": sorted(set(_log_target_type_labels().values())),
    }


def get_operation_log_detail(db: Session, log_id: int) -> dict[str, Any]:
    log = db.get(SysOperationLog, log_id)
    if not log:
        raise NotFoundError("操作日志不存在")
    items = db.scalars(
        select(SysOperationLogItem)
        .where(SysOperationLogItem.log_id == log.id)
        .order_by(SysOperationLogItem.id)
    ).all()
    return {**_log_to_dict(log), "items": [_log_item_to_dict(item) for item in items]}


def _log_target_type_labels() -> dict[str, str]:
    """操作日志「对象类型」：资源码（各模块 permissions）或 ORM 类名（模型 __log_label__）。

    按调用时已导入的模型汇总，不在模块 import 时固化，避免后挂载的模块缺中文名。
    """
    return {
        **RESOURCE_LABELS,
        **{
            mapper.class_.__name__: mapper.class_.__log_label__
            for mapper in Base.registry.mappers
            if hasattr(mapper.class_, "__log_label__")
        },
    }


def _log_target_type_codes_by_label() -> dict[str, list[str]]:
    codes: dict[str, list[str]] = {}
    for code, label in _log_target_type_labels().items():
        codes.setdefault(label, []).append(code)
    return codes


def _resolve_log_action_label(log: SysOperationLog) -> str:
    raw = log.operation_name or log.action or ""
    return _LOG_ACTION_LABELS.get(raw, raw)


def _resolve_log_target_type_label(target_type: str | None) -> str:
    if not target_type:
        return ""
    return _log_target_type_labels().get(target_type, target_type)


def _expand_target_type_terms(values: list[str] | None) -> list[str]:
    expanded: list[str] = []
    codes_by_label = _log_target_type_codes_by_label()
    for term in filter_terms(values):
        matched_codes = codes_by_label.get(term)
        if matched_codes:
            expanded.extend(matched_codes)
        else:
            expanded.append(term)
    return list(dict.fromkeys(expanded))


def _compact_text(value: str | None) -> str:
    return "".join(str(value or "").split())


def _compact_column(column):
    return func.replace(func.replace(func.coalesce(column, ""), " ", ""), "　", "")


def _compact_like(column, value: str):
    text = _compact_text(value)
    if not text:
        return None
    return like_contains(_compact_column(column), text)


def _apply_user_role_filter(stmt, role_id):
    terms = filter_terms(role_id)
    if not terms:
        return stmt
    if "all" in terms:
        return stmt.where(SysUser.id.in_(select(SysUserRole.user_id)))
    role_ids = [int(term) for term in terms if term.isdigit()]
    if not role_ids:
        return stmt
    return stmt.where(
        SysUser.id.in_(
            select(SysUserRole.user_id).where(SysUserRole.role_id.in_(role_ids))
        )
    )


def _get_user_role_map(db: Session, user_ids: list[int]) -> dict[int, list[int]]:
    if not user_ids:
        return {}
    rows = db.execute(select(SysUserRole.user_id, SysUserRole.role_id).where(SysUserRole.user_id.in_(user_ids))).all()
    result: dict[int, list[int]] = {}
    for user_id, role_id in rows:
        result.setdefault(user_id, []).append(role_id)
    return result


def _get_role_bundle_map(db: Session, role_ids: list[int]) -> dict[int, list[str]]:
    if not role_ids:
        return {}
    rows = db.execute(
        select(SysRolePermissionBundle.role_id, SysRolePermissionBundle.bundle_code).where(
            SysRolePermissionBundle.role_id.in_(role_ids)
        )
    ).all()
    result: dict[int, list[str]] = {}
    for role_id, bundle_code in rows:
        result.setdefault(role_id, []).append(bundle_code)
    return result


def _get_bundle_item_map(db: Session, bundle_codes: list[str]) -> dict[str, list[str]]:
    if not bundle_codes:
        return {}
    rows = db.execute(
        select(SysPermissionBundleItem.bundle_code, SysPermissionBundleItem.permission_code).where(
            SysPermissionBundleItem.bundle_code.in_(bundle_codes)
        )
    ).all()
    result: dict[str, list[str]] = {}
    for bundle_code, permission_code in rows:
        result.setdefault(bundle_code, []).append(permission_code)
    return result


def _delete_matching(db: Session, model, *criteria) -> None:
    for row in db.scalars(select(model).where(*criteria)).all():
        db.delete(row)


def _replace_user_roles(db: Session, user_id: int, role_ids: list[int]) -> None:
    existing = {
        row.role_id: row
        for row in db.scalars(
            select(SysUserRole).where(SysUserRole.user_id == user_id)
        ).all()
    }
    desired = set(role_ids)
    for role_id in sorted(existing.keys() - desired):
        db.delete(existing[role_id])
    for role_id in sorted(desired - existing.keys()):
        db.add(SysUserRole(user_id=user_id, role_id=role_id))


def _replace_role_bundles(db: Session, role_id: int, bundle_codes: list[str]) -> None:
    existing = {
        row.bundle_code: row
        for row in db.scalars(
            select(SysRolePermissionBundle).where(
                SysRolePermissionBundle.role_id == role_id
            )
        ).all()
    }
    desired = set(bundle_codes)
    for bundle_code in sorted(existing.keys() - desired):
        db.delete(existing[bundle_code])
    for bundle_code in sorted(desired - existing.keys()):
        db.add(SysRolePermissionBundle(role_id=role_id, bundle_code=bundle_code))


def _replace_bundle_permissions(db: Session, bundle_code: str, permission_codes: list[str]) -> None:
    existing = {
        row.permission_code: row
        for row in db.scalars(
            select(SysPermissionBundleItem).where(
                SysPermissionBundleItem.bundle_code == bundle_code
            )
        ).all()
    }
    desired = set(permission_codes)
    for permission_code in sorted(existing.keys() - desired):
        db.delete(existing[permission_code])
    for permission_code in sorted(desired - existing.keys()):
        db.add(
            SysPermissionBundleItem(
                bundle_code=bundle_code,
                permission_code=permission_code,
            )
        )


def _unique_ints(values: list) -> list[int]:
    return list(dict.fromkeys(int(value) for value in values if value))


def _unique_strings(values: list) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if value))


def _ensure_user_ids_exist(db: Session, user_ids: list[int]) -> None:
    if not user_ids:
        return
    existing = set(db.scalars(select(SysUser.id).where(SysUser.id.in_(user_ids))).all())
    missing = sorted(set(user_ids) - existing)
    if missing:
        raise ValueError(f"用户不存在: {', '.join(str(item) for item in missing)}")


def _ensure_role_ids_exist(db: Session, role_ids: list[int]) -> None:
    if not role_ids:
        return
    existing = set(db.scalars(select(SysRole.id).where(SysRole.id.in_(role_ids))).all())
    missing = sorted(set(role_ids) - existing)
    if missing:
        raise ValueError(f"角色不存在: {', '.join(str(item) for item in missing)}")


def _ensure_bundle_codes_exist(db: Session, bundle_codes: list[str]) -> None:
    if not bundle_codes:
        return
    existing = set(db.scalars(select(SysPermissionBundle.code).where(SysPermissionBundle.code.in_(bundle_codes))).all())
    missing = sorted(set(bundle_codes) - existing)
    if missing:
        raise ValueError(f"权限包不存在: {', '.join(missing)}")


def _ensure_permission_codes_exist(permission_codes: Iterable[str]) -> None:
    missing = sorted(set(permission_codes) - PERMISSION_INDEX.keys())
    if missing:
        raise ValueError(f"权限点不存在: {', '.join(missing)}")


def _user_to_dict(user: SysUser, role_ids: list[int]) -> dict:
    data = user.to_dict()
    data["role_ids"] = role_ids
    return data


def _role_to_dict(role: SysRole, bundle_codes: list[str]) -> dict:
    return {
        "id": role.id,
        "code": role.code,
        "name": role.name,
        "description": role.description,
        "status": role.status,
        "sort_order": role.sort_order,
        "bundle_codes": bundle_codes,
    }


def _bundle_to_dict(bundle: SysPermissionBundle, permission_codes: list[str]) -> dict:
    return {
        "id": bundle.id,
        "code": bundle.code,
        "name": bundle.name,
        "module": bundle.module,
        "description": bundle.description,
        "status": bundle.status,
        "sort_order": bundle.sort_order,
        "permission_codes": permission_codes,
    }


def _permission_to_dict(module: str, permission: Permission) -> dict:
    return {
        "code": permission.code,
        "name": permission.name,
        "type": permission.type,
        "module": module,
        "resource": permission.resource,
        "action": permission.action,
        "route_path": permission.route_path,
        "ui_key": permission.ui_key,
        "parent_code": permission.parent_code,
        "sort_order": permission.sort_order,
    }


def _override_to_dict(override: SysUserPermissionOverride) -> dict:
    return {
        "id": override.id,
        "user_id": override.user_id,
        "permission_code": override.permission_code,
        "effect": override.effect,
        "reason": override.reason,
    }


def _log_to_dict(log: SysOperationLog) -> dict:
    return {
        "id": log.id,
        "request_id": log.request_id,
        "user_id": log.user_id,
        "username": log.username,
        "operator_name": log.operator_name,
        "source": log.source,
        "ip_address": log.ip_address,
        "action": log.action,
        "action_label": _resolve_log_action_label(log),
        "operation_name": log.operation_name,
        "operation_type": log.operation_type,
        "target_type": log.target_type,
        "target_type_label": _resolve_log_target_type_label(log.target_type),
        "target_id": log.target_id,
        "target_label": log.target_label,
        "result": log.result,
        "affected_count": log.affected_count,
        "detail": log.detail,
        "error_message": log.error_message,
        "created_at": log.created_at,
    }


def _log_item_to_dict(item: SysOperationLogItem) -> dict:
    return {
        "id": item.id,
        "entity_type": item.entity_type,
        "entity_type_label": _resolve_log_target_type_label(item.entity_type),
        "table_name": item.table_name,
        "entity_id": item.entity_id,
        "entity_label": item.entity_label,
        "change_type": item.change_type,
        "change_count": item.change_count,
        "changes": item.changes or [],
    }


def _parse_log_datetime(value: str, *, end: bool) -> datetime:
    text = str(value or "").strip()
    try:
        if len(text) == 10:
            suffix = " 23:59:59.999999" if end else " 00:00:00"
            return datetime.fromisoformat(f"{text}{suffix}")
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo:
            return parsed.astimezone(ZoneInfo("Asia/Shanghai")).replace(tzinfo=None)
        return parsed
    except ValueError as exc:
        raise ValueError("日志时间格式不正确") from exc
