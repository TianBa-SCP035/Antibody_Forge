from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from copy import deepcopy
import hashlib
import json
import uuid
from typing import Any

from sqlalchemy import JSON, event, inspect
from sqlalchemy.orm import Session, SessionTransaction

from core.logging import is_sensitive_key
from db.session import AuditedSession
from models.system import SysJobRunLog, SysOperationLog, SysOperationLogItem
from modules.system.audit_config import (
    get_audit_field_label,
    get_audit_set_like_fields,
)
from modules.system.audit_context import AuditContext, get_audit_context

_RECORDS_KEY = "_audit_records"
_GENERATED_KEY = "_audit_generated"
_ORIGINALS_KEY = "_audit_originals"
_ROOT_COMMIT_KEY = "_audit_root_commit"
_OUTCOMES_KEY = "_audit_outcomes"
_SAVEPOINTS_KEY = "_audit_savepoints"
_INSTALLED = False
_MISSING = object()
_SUMMARY_CHANGE_LIMIT = 2
_SUMMARY_VALUE_LIMIT = 24
MAX_AUDIT_ENTITIES = 200
MAX_CHANGES_PER_ENTITY = 500
MAX_AUDIT_VALUE_BYTES = 4096
MAX_AUDIT_DETAIL_BYTES = 512 * 1024

_IGNORED_FIELDS = frozenset({"created_at", "updated_at", "last_login_at"})


@dataclass
class PendingEntityChange:
    obj: Any
    entity_type: str
    table_name: str
    change_type: str
    changes: dict[str, dict[str, Any]] = field(default_factory=dict)
    replace_fields: set[str] = field(default_factory=set)
    omitted_by_field: dict[str, int] = field(default_factory=dict)

    @property
    def omitted_change_count(self) -> int:
        return sum(self.omitted_by_field.values())


@dataclass
class PendingAuditOutcome:
    log: SysOperationLog
    context: AuditContext
    result: str
    explicit: bool


@dataclass
class SavepointCheckpoint:
    records: dict[int, PendingEntityChange]
    originals: dict[int, dict[str, Any]]
    outcomes: dict[int, PendingAuditOutcome]
    generated: bool


def setup_session_audit() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    event.listen(AuditedSession, "before_flush", _before_flush)
    event.listen(AuditedSession, "before_commit", _before_commit)
    event.listen(AuditedSession, "loaded_as_persistent", _remember_loaded_state)
    event.listen(AuditedSession, "after_transaction_create", _after_transaction_create)
    event.listen(AuditedSession, "after_commit", _after_commit)
    event.listen(AuditedSession, "after_soft_rollback", _after_soft_rollback)
    _INSTALLED = True


def _is_excluded(obj: Any) -> bool:
    return isinstance(obj, (SysOperationLog, SysOperationLogItem, SysJobRunLog))


def _before_flush(session: Session, _flush_context: Any, _instances: Any) -> None:
    if session.info.get(_GENERATED_KEY):
        return
    _collect_pending_changes(session)


def _collect_pending_changes(session: Session) -> None:
    records: dict[int, PendingEntityChange] = session.info.setdefault(_RECORDS_KEY, {})
    for obj in tuple(session.new):
        if not _is_excluded(obj):
            _merge_record(records, _record_for_object(obj, "create"))
    for obj in tuple(session.dirty):
        if not _is_excluded(obj) and session.is_modified(obj, include_collections=False):
            _merge_record(records, _record_for_object(obj, "update"))
    for obj in tuple(session.deleted):
        if not _is_excluded(obj):
            _merge_record(records, _record_for_object(obj, "delete"))


def _record_for_object(obj: Any, change_type: str) -> PendingEntityChange:
    state = inspect(obj)
    mapper = state.mapper
    record = PendingEntityChange(
        obj=obj,
        entity_type=mapper.class_.__name__,
        table_name=mapper.local_table.name,
        change_type=change_type,
    )
    if change_type in {"create", "delete"}:
        _record_entity_snapshot(record, obj, mapper, change_type)
        return record

    set_like_fields = get_audit_set_like_fields(
        record.entity_type,
        record.table_name,
    )
    budget = {"truncated": False, "omitted": 0}
    for prop in mapper.column_attrs:
        key = prop.key
        if key in _IGNORED_FIELDS:
            continue
        label = get_audit_field_label(
            record.table_name,
            key,
            orm_comment=prop.columns[0].comment,
        )
        history = state.attrs[key].history
        if not history.has_changes():
            continue
        if isinstance(prop.columns[0].type, JSON):
            record.replace_fields.add(key)
        session_original = _original_value(obj, key)
        old_value = (
            session_original
            if session_original is not _MISSING
            else history.deleted[0] if history.deleted else None
        )
        new_value = history.added[0] if history.added else getattr(obj, key, None)
        omitted_before = int(budget["omitted"])
        _append_value_diff(
            record.changes,
            key,
            label,
            old_value,
            new_value,
            key in set_like_fields,
            budget,
        )
        omitted = int(budget["omitted"]) - omitted_before
        if omitted:
            record.omitted_by_field[key] = omitted
    return record


def _record_entity_snapshot(
    record: PendingEntityChange,
    obj: Any,
    mapper: Any,
    change_type: str,
) -> None:
    """Record one row per column. Nested JSON is summarized, not expanded."""
    is_create = change_type == "create"
    for prop in mapper.column_attrs:
        key = prop.key
        if key in _IGNORED_FIELDS:
            continue
        value = getattr(obj, key, None)
        if value is None:
            continue
        if _is_sensitive_path(key):
            compact = "***"
        elif isinstance(value, (dict, list, tuple, set)):
            compact = _container_summary(value)
        else:
            compact = _safe_value(value)
        record.changes[key] = {
            "path": key,
            "label": get_audit_field_label(
                record.table_name,
                key,
                orm_comment=prop.columns[0].comment,
            ),
            "change_kind": "add" if is_create else "remove",
            "before": None if is_create else compact,
            "after": compact if is_create else None,
        }


def _merge_record(records: dict[int, PendingEntityChange], incoming: PendingEntityChange) -> None:
    key = id(incoming.obj)
    current = records.get(key)
    if current is None:
        if (
            incoming.change_type != "update"
            or incoming.changes
            or incoming.omitted_change_count
        ):
            records[key] = incoming
        return
    if current.change_type == "create" and incoming.change_type == "delete":
        records.pop(key, None)
        return
    if incoming.change_type == "delete":
        current.change_type = "delete"
    for field_name in incoming.replace_fields:
        prefixes = (f"{field_name}.", f"{field_name}[")
        for path in tuple(current.changes):
            if path == field_name or path.startswith(prefixes):
                current.changes.pop(path, None)
        current.omitted_by_field.pop(field_name, None)
    current.replace_fields.update(incoming.replace_fields)
    for field_name, omitted in incoming.omitted_by_field.items():
        current.omitted_by_field[field_name] = max(
            current.omitted_by_field.get(field_name, 0),
            omitted,
        )
    for path, change in incoming.changes.items():
        existing = current.changes.get(path)
        if existing is None:
            current.changes[path] = change
        else:
            existing["after"] = change["after"]
            if (
                _audit_values_equal(existing["before"], existing["after"])
                and existing["before"] != "***"
            ):
                current.changes.pop(path, None)
    if (
        current.change_type == "update"
        and not current.changes
        and not current.omitted_change_count
    ):
        records.pop(key, None)


def _append_value_diff(
    target: dict[str, dict[str, Any]],
    path: str,
    label: str,
    before: Any,
    after: Any,
    set_like: bool = False,
    budget: dict[str, Any] | None = None,
) -> None:
    budget = budget if budget is not None else {"truncated": False, "omitted": 0}
    if budget["truncated"]:
        return
    if (
        before is not _MISSING
        and after is not _MISSING
        and _audit_values_equal(before, after)
    ):
        return
    if len(target) >= MAX_CHANGES_PER_ENTITY:
        budget["truncated"] = True
        budget["omitted"] += 1
        return
    if _is_sensitive_path(path):
        target[path] = {
            "path": path,
            "label": label,
            "change_kind": "update",
            "before": "***",
            "after": "***",
        }
        return
    before_kind = _container_kind(before)
    after_kind = _container_kind(after)
    shape_changed = (
        before is not _MISSING
        and after is not _MISSING
        and before_kind != after_kind
        and (before_kind is not None or after_kind is not None)
    )
    empty_container_added = (
        before is _MISSING
        and after_kind is not None
        and not after
    )
    empty_container_removed = (
        after is _MISSING
        and before_kind is not None
        and not before
    )
    if shape_changed or empty_container_added or empty_container_removed:
        target[path] = {
            "path": path,
            "label": label,
            "change_kind": (
                "add"
                if before is _MISSING
                else "remove"
                if after is _MISSING
                else "update"
            ),
            "before": None if before is _MISSING else _safe_shape_value(before),
            "after": None if after is _MISSING else _safe_shape_value(after),
        }
        return
    if isinstance(before, dict) or isinstance(after, dict):
        before_dict = before if isinstance(before, dict) else {}
        after_dict = after if isinstance(after, dict) else {}
        keys = sorted(set(before_dict) | set(after_dict), key=str)
        for index, key in enumerate(keys):
            _append_value_diff(
                target,
                f"{path}.{_escape_path_segment(key)}",
                f"{label} > {key}",
                before_dict.get(key, _MISSING),
                after_dict.get(key, _MISSING),
                set_like,
                budget,
            )
            if budget["truncated"]:
                budget["omitted"] += len(keys) - index - 1
                break
        return
    if isinstance(before, (list, tuple)) or isinstance(after, (list, tuple)):
        before_list = list(before) if isinstance(before, (list, tuple)) else []
        after_list = list(after) if isinstance(after, (list, tuple)) else []
        if set_like and _is_scalar_list(before_list) and _is_scalar_list(after_list):
            removed, added = _list_membership_diff(before_list, after_list)
            for index, value in enumerate(removed):
                _append_value_diff(
                    target,
                    f"{path}[-{index}]",
                    label,
                    value,
                    _MISSING,
                    set_like,
                    budget,
                )
                if budget["truncated"]:
                    budget["omitted"] += len(removed) - index - 1 + len(added)
                    break
            for index, value in enumerate(added):
                if budget["truncated"]:
                    break
                _append_value_diff(
                    target,
                    f"{path}[+{index}]",
                    label,
                    _MISSING,
                    value,
                    set_like,
                    budget,
                )
                if budget["truncated"]:
                    budget["omitted"] += len(added) - index - 1
                    break
            return
        item_count = max(len(before_list), len(after_list))
        for index in range(item_count):
            _append_value_diff(
                target,
                f"{path}[{index}]",
                f"{label}（第 {index + 1} 项）",
                before_list[index] if index < len(before_list) else _MISSING,
                after_list[index] if index < len(after_list) else _MISSING,
                set_like,
                budget,
            )
            if budget["truncated"]:
                budget["omitted"] += item_count - index - 1
                break
        return
    target[path] = {
        "path": path,
        "label": label,
        "change_kind": (
            "add"
            if before is _MISSING
            else "remove"
            if after is _MISSING
            else "update"
        ),
        "before": None if before is _MISSING else _safe_value(before),
        "after": None if after is _MISSING else _safe_value(after),
    }


def _is_scalar_list(values: list[Any]) -> bool:
    return all(not isinstance(value, (dict, list, tuple, set)) for value in values)


def _container_kind(value: Any) -> str | None:
    if isinstance(value, dict):
        return "object"
    if isinstance(value, (list, tuple)):
        return "array"
    return None


def _container_summary(value: Any) -> str:
    if isinstance(value, dict):
        return f"<对象 {len(value)} 个键>"
    if isinstance(value, (list, tuple)):
        return f"<数组 {len(value)} 项>"
    if isinstance(value, set):
        return f"<集合 {len(value)} 项>"
    return _bounded_text(str(value))


def _escape_path_segment(value: str) -> str:
    return value.replace("\\", "\\\\").replace(".", "\\.").replace("[", "\\[")


def _audit_values_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(
            _audit_values_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, (list, tuple)):
        return len(left) == len(right) and all(
            _audit_values_equal(left_item, right_item)
            for left_item, right_item in zip(left, right, strict=True)
        )
    return left == right


def _list_membership_diff(
    before: list[Any],
    after: list[Any],
) -> tuple[list[Any], list[Any]]:
    remaining_after = list(after)
    removed: list[Any] = []
    for value in before:
        match = next(
            (
                index
                for index, candidate in enumerate(remaining_after)
                if _audit_values_equal(value, candidate)
            ),
            None,
        )
        if match is None:
            removed.append(value)
        else:
            remaining_after.pop(match)

    remaining_before = list(before)
    added: list[Any] = []
    for value in after:
        match = next(
            (
                index
                for index, candidate in enumerate(remaining_before)
                if _audit_values_equal(value, candidate)
            ),
            None,
        )
        if match is None:
            added.append(value)
        else:
            remaining_before.pop(match)
    return removed, added


def _safe_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _bounded_text(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Enum):
        return _safe_value(value.value)
    if isinstance(value, bytes):
        return f"<{len(value)} bytes>"
    if isinstance(value, dict):
        return {
            str(key): "***" if is_sensitive_key(key) else _safe_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [_safe_value(item) for item in value]
    return _bounded_text(str(value))


def _safe_shape_value(value: Any) -> Any:
    safe_value = _safe_value(value)
    encoded = json.dumps(
        safe_value,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(encoded) <= MAX_AUDIT_VALUE_BYTES:
        return safe_value
    digest = hashlib.sha256(encoded).hexdigest()[:12]
    return f"<{_container_kind(value)} {len(encoded)} bytes sha256:{digest}>"


def _is_sensitive_path(path: str) -> bool:
    normalized = path.replace("[", ".").replace("]", "")
    return any(is_sensitive_key(part) for part in normalized.split(".") if part)


def _bounded_text(value: str) -> str:
    encoded = value.encode("utf-8")
    if len(encoded) <= MAX_AUDIT_VALUE_BYTES:
        return value
    digest = hashlib.sha256(encoded).hexdigest()[:12]
    suffix = f"… [sha256:{digest}]"
    prefix_bytes = MAX_AUDIT_VALUE_BYTES - len(suffix.encode("utf-8"))
    prefix = encoded[:prefix_bytes].decode("utf-8", errors="ignore")
    return f"{prefix}{suffix}"


def stage_audit_outcome(
    session: Session,
    log: SysOperationLog,
    context: AuditContext | None,
    *,
    explicit: bool,
) -> None:
    if context is None:
        return
    outcomes: dict[int, PendingAuditOutcome] = session.info.setdefault(_OUTCOMES_KEY, {})
    outcomes[id(log)] = PendingAuditOutcome(
        log=log,
        context=context,
        result="failed" if log.result == "failed" else "success",
        explicit=explicit,
    )


def _before_commit(session: Session) -> None:
    if session.in_nested_transaction():
        return
    session.info[_ROOT_COMMIT_KEY] = True
    if session.info.get(_GENERATED_KEY):
        return
    _collect_pending_changes(session)
    records = _active_records(session)
    context = get_audit_context()
    explicit_logs = _explicit_logs(session)
    if explicit_logs:
        if records and any(_entity_id(record.obj) is None for record in records):
            session.flush()
            records = _active_records(session)
        if records:
            _attach_records(
                explicit_logs[0],
                records,
                context=context,
            )
        for log in explicit_logs:
            stage_audit_outcome(session, log, context, explicit=True)
        session.info[_GENERATED_KEY] = True
        return
    if not records:
        return
    if session.new or session.dirty or session.deleted:
        session.flush()
        records = _active_records(session)
        if not records:
            return
    context = context or AuditContext(
        request_id=uuid.uuid4().hex,
        source="system",
        method="SYSTEM",
        path="database.write",
        fallback_action="database.write",
        fallback_name="后台数据变更",
    )
    aggregate_type = _aggregate_change_type(records)
    action_type = _action_change_type(records, context.actions, aggregate_type)
    action = context.select_action(action_type)
    first = records[0]
    log = SysOperationLog(
        request_id=context.request_id,
        user_id=context.user_id,
        username=context.username,
        operator_name=context.operator_name,
        source=context.source,
        ip_address=context.ip_address,
        action=action.code[:128],
        operation_name=(action.name or action.code)[:128],
        operation_type=action_type,
        target_type=(action.resource or first.entity_type)[:64],
        target_id=_entity_id(first.obj),
        target_label=_entity_label(first.obj),
        result="success",
        affected_count=0,
        detail={},
    )
    _attach_records(
        log,
        records,
        context=context,
    )
    session.info[_GENERATED_KEY] = True
    session.add(log)
    stage_audit_outcome(session, log, context, explicit=False)


def _active_records(session: Session) -> list[PendingEntityChange]:
    return [
        record
        for record in session.info.get(_RECORDS_KEY, {}).values()
        if (
            record.change_type != "update"
            or record.changes
            or record.omitted_change_count
        )
    ]


def _explicit_logs(session: Session) -> list[SysOperationLog]:
    outcomes: dict[int, PendingAuditOutcome] = session.info.get(_OUTCOMES_KEY, {})
    logs = [outcome.log for outcome in outcomes.values() if outcome.explicit]
    known_ids = {id(log) for log in logs}
    for obj in session.new:
        if isinstance(obj, SysOperationLog) and id(obj) not in known_ids:
            logs.append(obj)
    return logs


def _attach_records(
    log: SysOperationLog,
    records: list[PendingEntityChange],
    *,
    context: AuditContext | None = None,
) -> None:
    aggregate_type = _aggregate_change_type(records)
    total_changes = sum(_record_change_count(record) for record in records)
    detail = dict(log.detail or {})
    detail.update(
        {
            "changed": True,
            "change_summary": _change_summary(aggregate_type, records),
            "change_count": total_changes,
        }
    )
    if context is not None:
        detail.setdefault("method", context.method)
        detail.setdefault("path", context.path)
    log.affected_count = max(
        int(log.affected_count or 0),
        len(records),
    )
    first = records[0]
    if not log.target_type:
        log.target_type = first.entity_type[:64]
    if not log.target_id:
        log.target_id = _entity_id(first.obj)
    if not log.target_label:
        log.target_label = _entity_label(first.obj)
    remaining_bytes = MAX_AUDIT_DETAIL_BYTES
    stored_entities = 0
    stored_changes = 0
    for record in records[:MAX_AUDIT_ENTITIES]:
        bounded_changes: list[dict[str, Any]] = []
        for change in list(record.changes.values())[:MAX_CHANGES_PER_ENTITY]:
            encoded_size = len(
                json.dumps(
                    change,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
            )
            if encoded_size > remaining_bytes:
                break
            bounded_changes.append(change)
            remaining_bytes -= encoded_size
        log.items.append(
            SysOperationLogItem(
                entity_type=record.entity_type[:128],
                table_name=record.table_name[:128],
                entity_id=_entity_id(record.obj),
                entity_label=_entity_label(record.obj),
                change_type=record.change_type,
                change_count=_record_change_count(record),
                changes=bounded_changes,
            )
        )
        stored_entities += 1
        stored_changes += len(bounded_changes)
        if remaining_bytes <= 0:
            break
    omitted_entities = len(records) - stored_entities
    omitted_changes = total_changes - stored_changes
    if omitted_entities or omitted_changes:
        detail.update(
            {
                "truncated": True,
                "omitted_entity_count": omitted_entities,
                "omitted_change_count": omitted_changes,
            }
        )
    log.detail = detail


def _aggregate_change_type(records: list[PendingEntityChange]) -> str:
    types = {record.change_type for record in records}
    if len(types) == 1:
        return next(iter(types))
    return "update"


def _action_change_type(
    records: list[PendingEntityChange],
    actions: tuple[Any, ...],
    aggregate_type: str,
) -> str:
    """Pick the request-level action type.

    Child-row inserts on an existing parent are still entity creates, but the
    HTTP action should stay "edit" when the route also has a create mapping.
    """
    if aggregate_type != "create":
        return aggregate_type
    create_actions = [action for action in actions if action.operation_type == "create"]
    edit_actions = [
        action
        for action in actions
        if action.operation_type in {"edit", "edit_all", "manage", "update"}
    ]
    if not (create_actions and edit_actions):
        return "create"
    resources = [
        str(action.resource or "").replace("_", "").lower()
        for action in create_actions
        if action.resource
    ]
    if not resources:
        return "create"
    for record in records:
        if record.change_type != "create":
            continue
        entity = record.entity_type.replace("_", "").lower()
        table = record.table_name.replace("_", "").lower()
        if any(resource in entity or resource in table for resource in resources):
            return "create"
    return "update"


def _record_change_count(record: PendingEntityChange) -> int:
    return len(record.changes) + record.omitted_change_count


def _change_summary(change_type: str, records: list[PendingEntityChange]) -> str:
    entities = len(records)
    fields = sum(_record_change_count(record) for record in records)
    labels = {"create": "新增", "delete": "删除", "update": "修改"}
    action = labels.get(change_type, "变更")
    changes = [
        change
        for record in records
        for change in record.changes.values()
    ]
    if changes:
        parts = [_summarize_change(change) for change in changes[:_SUMMARY_CHANGE_LIMIT]]
        if fields > _SUMMARY_CHANGE_LIMIT:
            parts.append(f"另 {fields - _SUMMARY_CHANGE_LIMIT} 处")
        return "；".join(parts)
    return f"{action} {entities} 个对象"


def _summarize_change(change: dict[str, Any]) -> str:
    label = str(change.get("label") or change.get("path") or "字段")
    before = change.get("before")
    after = change.get("after")
    if before == after == "***":
        return f"{label}：已更新（内容已隐藏）"
    if change.get("change_kind") == "add":
        return f"{label}：新增 {_summary_value(after)}"
    if change.get("change_kind") == "remove":
        return f"{label}：移除 {_summary_value(before)}"
    return f"{label}：{_summary_value(before)} → {_summary_value(after)}"


def _summary_value(value: Any) -> str:
    if value is None:
        return "空"
    if isinstance(value, bool):
        return "是" if value else "否"
    text = str(value).strip() or "空"
    if len(text) > _SUMMARY_VALUE_LIMIT:
        return f"{text[:_SUMMARY_VALUE_LIMIT]}…"
    return text


def _entity_id(obj: Any) -> str | None:
    state = inspect(obj)
    identity = state.identity
    if identity:
        return ":".join(str(value) for value in identity)
    values = [getattr(obj, column.key, None) for column in state.mapper.primary_key]
    if values and all(value is not None for value in values):
        return ":".join(str(value) for value in values)
    return None


def _entity_label(obj: Any) -> str | None:
    default_fields = (
        "display_name",
        "name",
        "experiment_id",
        "project_code",
        "project_name",
        "orderNum",
        "code",
        "username",
        "file_name",
        "job_name",
    )
    for key in default_fields:
        value = getattr(obj, key, None)
        if value not in (None, ""):
            return str(value)[:255]
    return _entity_id(obj)


def _remember_loaded_state(session: Session, obj: Any) -> None:
    context = get_audit_context()
    if (
        _is_excluded(obj)
        or session.info.get("audit_read_only")
        or (context is not None and context.suppress_noop)
    ):
        return
    originals: dict[int, dict[str, Any]] = session.info.setdefault(_ORIGINALS_KEY, {})
    originals[id(obj)] = _column_snapshot(obj)


def _original_value(obj: Any, key: str) -> Any:
    session = inspect(obj).session
    if session is None:
        return _MISSING
    return session.info.get(_ORIGINALS_KEY, {}).get(id(obj), {}).get(key, _MISSING)


def _column_snapshot(obj: Any) -> dict[str, Any]:
    state = inspect(obj)
    values: dict[str, Any] = {}
    for prop in state.mapper.column_attrs:
        if prop.key in state.dict and isinstance(prop.columns[0].type, JSON):
            try:
                values[prop.key] = deepcopy(state.dict[prop.key])
            except Exception:
                values[prop.key] = state.dict[prop.key]
    return values


def _after_transaction_create(
    session: Session,
    transaction: SessionTransaction,
) -> None:
    if not transaction.nested:
        return
    checkpoints: dict[int, SavepointCheckpoint] = session.info.setdefault(
        _SAVEPOINTS_KEY,
        {},
    )
    checkpoints[id(transaction)] = SavepointCheckpoint(
        records=_clone_records(session.info.get(_RECORDS_KEY, {})),
        originals=deepcopy(session.info.get(_ORIGINALS_KEY, {})),
        outcomes=dict(session.info.get(_OUTCOMES_KEY, {})),
        generated=bool(session.info.get(_GENERATED_KEY)),
    )


def _after_commit(session: Session) -> None:
    if not session.info.pop(_ROOT_COMMIT_KEY, False):
        return
    outcomes: dict[int, PendingAuditOutcome] = session.info.get(_OUTCOMES_KEY, {})
    for outcome in outcomes.values():
        outcome.context.record_committed_result(outcome.result)
    _clear_transaction_state(session)
    session.info[_ORIGINALS_KEY] = {
        id(obj): _column_snapshot(obj)
        for obj in session.identity_map.values()
        if not _is_excluded(obj)
    }


def _after_soft_rollback(
    session: Session,
    previous_transaction: SessionTransaction,
) -> None:
    if previous_transaction.nested:
        checkpoints: dict[int, SavepointCheckpoint] = session.info.get(
            _SAVEPOINTS_KEY,
            {},
        )
        checkpoint = checkpoints.pop(id(previous_transaction), None)
        if checkpoint is not None:
            session.info[_RECORDS_KEY] = checkpoint.records
            session.info[_ORIGINALS_KEY] = checkpoint.originals
            session.info[_OUTCOMES_KEY] = checkpoint.outcomes
            if checkpoint.generated:
                session.info[_GENERATED_KEY] = True
            else:
                session.info.pop(_GENERATED_KEY, None)
        return
    if previous_transaction.parent is not None:
        return
    originals: dict[int, dict[str, Any]] = session.info.get(_ORIGINALS_KEY, {})
    retained_originals = {
        id(obj): originals[id(obj)]
        for obj in session.identity_map.values()
        if id(obj) in originals and not _is_excluded(obj)
    }
    _clear_transaction_state(session)
    if retained_originals:
        session.info[_ORIGINALS_KEY] = retained_originals
    else:
        session.info.pop(_ORIGINALS_KEY, None)


def _clear_transaction_state(session: Session) -> None:
    session.info.pop(_RECORDS_KEY, None)
    session.info.pop(_GENERATED_KEY, None)
    session.info.pop(_ROOT_COMMIT_KEY, None)
    session.info.pop(_OUTCOMES_KEY, None)
    session.info.pop(_SAVEPOINTS_KEY, None)


def _clone_records(
    records: dict[int, PendingEntityChange],
) -> dict[int, PendingEntityChange]:
    return {
        key: PendingEntityChange(
            obj=record.obj,
            entity_type=record.entity_type,
            table_name=record.table_name,
            change_type=record.change_type,
            changes=deepcopy(record.changes),
            replace_fields=set(record.replace_fields),
            omitted_by_field=dict(record.omitted_by_field),
        )
        for key, record in records.items()
    }
