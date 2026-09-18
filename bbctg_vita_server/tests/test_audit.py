import json
from pathlib import Path
import re
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy import BigInteger, Integer, JSON, String, create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Mapped, mapped_column, sessionmaker
from sqlalchemy.orm.attributes import flag_modified
import modules.immunology.workbench.service as immunology_workbench_service
import modules.mega_automation.routes as mega_routes
import modules.system.audit_middleware as audit_middleware
import modules.system.audit_config as audit_config
import modules.system.routes as system_routes
from core.logging import (
    REDACTED,
    _is_sensitive_key,
    _redact_sensitive_values,
    _sanitize_body_for_log,
)
from db.session import AuditedSession, Base
from models.system import SysOperationLog, SysOperationLogItem, SysUserRole
from modules.system.audit import write_operation_log
from modules.system.audit_config import audit_path_matches
from modules.system.audit_context import (
    AuditAction,
    AuditContext,
    audit_scope,
    reset_audit_context,
    set_audit_context,
)
from modules.system.audit_coverage import unclassified_write_routes
from modules.system.audit_middleware import _parse_result
from modules.system.audit_session import setup_session_audit
from server import app


@compiles(BigInteger, "sqlite")
def _compile_big_integer_for_sqlite(_type, _compiler, **_kwargs):
    return "INTEGER"


class AuditExample(Base):
    __tablename__ = "test_audit_example"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, comment="名称")
    note: Mapped[str | None] = mapped_column(String(128), comment="备注")
    password_hash: Mapped[str | None] = mapped_column(String(128), comment="密码")
    payload: Mapped[object | None] = mapped_column(JSON, comment="数据")


class AuditSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        setup_session_audit()

    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(
            self.engine,
            tables=[
                AuditExample.__table__,
                SysOperationLog.__table__,
                SysOperationLogItem.__table__,
            ],
        )
        self.Session = sessionmaker(
            bind=self.engine,
            class_=AuditedSession,
            expire_on_commit=False,
        )

    def tearDown(self):
        self.engine.dispose()

    def test_create_update_delete_are_captured_without_model_configuration(self):
        with self.Session() as db:
            with audit_scope("test.example", "测试实体", source="user"):
                row = AuditExample(name="before", note="remove me", payload={"wells": [1, 2]})
                db.add(row)
                db.commit()
            create_log = db.scalars(
                select(SysOperationLog)
                .where(SysOperationLog.operation_type == "create")
                .order_by(SysOperationLog.id.desc())
            ).first()
            create_item = db.scalar(
                select(SysOperationLogItem).where(
                    SysOperationLogItem.log_id == create_log.id
                )
            )
            create_changes = {item["path"]: item for item in create_item.changes}
            self.assertEqual(create_changes["name"]["after"], "before")
            self.assertEqual(create_changes["payload"]["after"], "<对象 1 个键>")
            self.assertNotIn("payload.wells[0]", create_changes)

            with audit_scope("test.example", "测试实体", source="user"):
                row.name = "after"
                row.note = None
                row.payload = {"wells": [1, 3], "status": "ok"}
                db.commit()

            update_log = db.scalars(
                select(SysOperationLog)
                .where(SysOperationLog.operation_type == "update")
                .order_by(SysOperationLog.id.desc())
            ).first()
            self.assertIsNotNone(update_log)
            self.assertEqual(update_log.affected_count, 1)
            self.assertEqual(
                update_log.detail["change_summary"],
                "名称：before → after；备注：remove me → 空；另 2 处",
            )
            update_item = db.scalar(
                select(SysOperationLogItem).where(SysOperationLogItem.log_id == update_log.id)
            )
            changes = {item["path"]: item for item in update_item.changes}
            self.assertEqual(changes["name"]["before"], "before")
            self.assertEqual(changes["name"]["after"], "after")
            self.assertIsNone(changes["note"]["after"])
            self.assertEqual(changes["payload.wells[1]"]["before"], 2)
            self.assertEqual(changes["payload.wells[1]"]["after"], 3)
            self.assertEqual(changes["payload.status"]["after"], "ok")

            with audit_scope("test.example", "测试实体", source="user"):
                db.delete(row)
                db.commit()
            delete_log = db.scalars(
                select(SysOperationLog)
                .where(SysOperationLog.operation_type == "delete")
                .order_by(SysOperationLog.id.desc())
            ).first()
            self.assertEqual(delete_log.target_id, str(row.id))
            delete_item = db.scalar(
                select(SysOperationLogItem).where(
                    SysOperationLogItem.log_id == delete_log.id
                )
            )
            delete_changes = {item["path"]: item for item in delete_item.changes}
            self.assertEqual(delete_changes["name"]["before"], "after")
            self.assertEqual(delete_changes["payload"]["before"], "<对象 2 个键>")
            self.assertNotIn("payload.wells[0]", delete_changes)

    def test_child_inserts_on_shared_create_edit_route_use_edit_action(self):
        create_action = AuditAction(
            code="serum.project.create",
            name="新建免疫项目",
            operation_type="create",
            resource="project",
        )
        edit_action = AuditAction(
            code="serum.project.edit",
            name="编辑免疫项目",
            operation_type="edit",
            resource="project",
        )
        with self.Session() as db:
            token = set_audit_context(
                AuditContext(
                    request_id="child-insert",
                    source="user",
                    method="POST",
                    path="/api/serum/save",
                    actions=(create_action, edit_action),
                )
            )
            try:
                db.add(AuditExample(name="new-group"))
                db.commit()
            finally:
                reset_audit_context(token)
            log = db.scalar(
                select(SysOperationLog).where(SysOperationLog.request_id == "child-insert")
            )
            self.assertEqual(log.action, "serum.project.edit")
            self.assertEqual(log.operation_name, "编辑免疫项目")
            self.assertEqual(log.operation_type, "update")
            self.assertEqual(log.detail["change_summary"], "名称：新增 new-group")

        with self.Session() as db:
            matching_create = AuditAction(
                code="test.example.create",
                name="新建测试实体",
                operation_type="create",
                resource="example",
            )
            matching_edit = AuditAction(
                code="test.example.edit",
                name="编辑测试实体",
                operation_type="edit",
                resource="example",
            )
            token = set_audit_context(
                AuditContext(
                    request_id="parent-create",
                    source="user",
                    method="POST",
                    path="/api/test/save",
                    actions=(matching_create, matching_edit),
                )
            )
            try:
                db.add(AuditExample(name="parent-row"))
                db.commit()
            finally:
                reset_audit_context(token)
            log = db.scalar(
                select(SysOperationLog).where(SysOperationLog.request_id == "parent-create")
            )
            self.assertEqual(log.action, "test.example.create")
            self.assertEqual(log.operation_name, "新建测试实体")
            self.assertEqual(log.operation_type, "create")

    def test_password_values_are_redacted(self):
        with self.Session() as db:
            with audit_scope("test.user", "测试用户", source="user"):
                user = AuditExample(name="user", password_hash="old")
                db.add(user)
                db.commit()
            with audit_scope("test.user", "测试用户", source="user"):
                user.password_hash = "new"
                db.commit()
            log = db.scalars(
                select(SysOperationLog)
                .where(SysOperationLog.operation_type == "update")
                .order_by(SysOperationLog.id.desc())
            ).first()
            item = db.scalar(select(SysOperationLogItem).where(SysOperationLogItem.log_id == log.id))
            self.assertEqual(
                log.detail["change_summary"],
                "密码：已更新（内容已隐藏）",
            )
            self.assertEqual(item.changes[0]["before"], "***")
            self.assertEqual(item.changes[0]["after"], "***")

    def test_batch_commit_creates_one_log_with_multiple_entity_items(self):
        with self.Session() as db:
            with audit_scope("test.batch", "批量测试", source="user"):
                db.add_all([AuditExample(name="one"), AuditExample(name="two")])
                db.commit()
            log = db.scalar(select(SysOperationLog).where(SysOperationLog.action == "test.batch"))
            items = db.scalars(
                select(SysOperationLogItem).where(SysOperationLogItem.log_id == log.id)
            ).all()
            self.assertEqual(log.affected_count, 2)
            self.assertEqual(len(items), 2)
            self.assertTrue(all(item.change_type == "create" for item in items))

    def test_no_actual_change_does_not_create_entity_log(self):
        with self.Session() as db:
            with audit_scope("test.noop", "无变化测试", source="user"):
                row = AuditExample(name="same")
                db.add(row)
                db.commit()
            before = len(db.scalars(select(SysOperationLog)).all())
            with audit_scope("test.noop", "无变化测试", source="user"):
                row.name = "same"
                db.commit()
            self.assertEqual(len(db.scalars(select(SysOperationLog)).all()), before)

    def test_flagged_in_place_json_change_uses_loaded_snapshot(self):
        with self.Session() as db:
            with audit_scope("test.json", "JSON 测试", source="user"):
                row = AuditExample(name="plate", payload={"wells": [1, 2, 3]})
                db.add(row)
                db.commit()
            with audit_scope("test.json", "JSON 测试", source="user"):
                row.payload["wells"][1] = 9
                flag_modified(row, "payload")
                db.commit()
            log = db.scalars(
                select(SysOperationLog)
                .where(SysOperationLog.operation_type == "update")
                .order_by(SysOperationLog.id.desc())
            ).first()
            item = db.scalar(select(SysOperationLogItem).where(SysOperationLogItem.log_id == log.id))
            self.assertEqual(item.change_count, 1)
            self.assertEqual(item.changes[0]["path"], "payload.wells[1]")
            self.assertEqual(item.changes[0]["before"], 2)
            self.assertEqual(item.changes[0]["after"], 9)

    def test_json_reverted_after_flush_does_not_leave_stale_change(self):
        with self.Session() as db:
            row = AuditExample(name="json-revert", payload={"status": "old"})
            db.add(row)
            db.commit()
            with audit_scope("test.json.revert", "JSON 回退", source="user"):
                row.payload = {"status": "temporary"}
                flag_modified(row, "payload")
                db.flush()
                row.payload = {"status": "old"}
                flag_modified(row, "payload")
                db.commit()
            self.assertIsNone(
                db.scalar(
                    select(SysOperationLog).where(
                        SysOperationLog.action == "test.json.revert"
                    )
                )
            )

    def test_list_item_removal_uses_readable_summary(self):
        with patch.dict(
            audit_config.AUDIT_SET_LIKE_FIELDS,
            {"AuditExample": frozenset({"payload"})},
        ):
            with self.Session() as db:
                with audit_scope("test.list", "列表测试", source="user"):
                    row = AuditExample(
                        name="dates",
                        payload={"dates": ["2026-09-04", "2026-09-05"]},
                    )
                    db.add(row)
                    db.commit()
                with audit_scope("test.list", "列表测试", source="user"):
                    row.payload = {"dates": ["2026-09-05"]}
                    db.commit()
                log = db.scalars(
                    select(SysOperationLog)
                    .where(SysOperationLog.operation_type == "update")
                    .order_by(SysOperationLog.id.desc())
                ).first()
                self.assertEqual(
                    log.detail["change_summary"],
                    "数据 > dates：移除 2026-09-04",
                )

    def test_positional_list_and_bool_are_not_treated_as_set_members(self):
        with self.Session() as db:
            row = AuditExample(name="positions", payload={"values": [1, 2]})
            db.add(row)
            db.commit()
            with audit_scope("test.positions", "位置列表测试", source="user"):
                row.payload = {"values": [True, 2]}
                flag_modified(row, "payload")
                db.commit()
            log = db.scalar(
                select(SysOperationLog).where(SysOperationLog.action == "test.positions")
            )
            item = db.scalar(
                select(SysOperationLogItem).where(SysOperationLogItem.log_id == log.id)
            )
            self.assertEqual(item.change_count, 1)
            self.assertEqual(item.changes[0]["before"], 1)
            self.assertIs(item.changes[0]["after"], True)

    def test_request_logging_redacts_sensitive_keys(self):
        body = json.dumps(
            {"username": "alice", "newPassword": "secret", "ticket": "token"}
        ).encode()
        summary = _sanitize_body_for_log(body, "application/json")
        self.assertEqual(summary["bytes"], len(body))
        self.assertEqual(
            summary["fields"],
            ["newPassword", "ticket", "username"],
        )
        self.assertNotIn("secret", str(summary))
        self.assertTrue(_is_sensitive_key("newPassword"))
        self.assertTrue(_is_sensitive_key("privateKey"))
        self.assertTrue(_is_sensitive_key("passwd"))
        self.assertTrue(_is_sensitive_key("cookie"))
        self.assertTrue(_is_sensitive_key("ticket"))
        self.assertEqual(
            _redact_sensitive_values({"ticket": "secret"})["ticket"],
            REDACTED,
        )

    def test_startup_schema_validation_rejects_incomplete_audit_v2(self):
        engine = MagicMock()
        engine.dialect.name = "mysql"
        connection = engine.connect.return_value.__enter__.return_value
        connection.execute.return_value.all.return_value = [
            ("sys_operation_log", "request_id", "请求ID")
        ]
        with self.assertRaisesRegex(RuntimeError, "schema is incomplete"):
            audit_config.load_database_field_labels(engine)
        connection.execute.assert_called_once()

    def test_multiple_transactions_share_request_id(self):
        with self.Session() as db:
            with audit_scope("test.multi", "多事务测试", source="job") as context:
                db.add(AuditExample(name="first"))
                db.commit()
                db.add(AuditExample(name="second"))
                db.commit()
            logs = db.scalars(
                select(SysOperationLog)
                .where(SysOperationLog.action == "test.multi")
                .order_by(SysOperationLog.id)
            ).all()
            self.assertEqual(len(logs), 2)
            self.assertEqual({log.request_id for log in logs}, {context.request_id})
            self.assertTrue(all(log.source == "job" for log in logs))
            self.assertEqual(context.committed_results, {"success"})

    def test_successful_savepoint_is_merged_into_root_transaction_log(self):
        with self.Session() as db:
            with audit_scope("test.savepoint", "保存点测试", source="user"):
                outer = AuditExample(name="outer")
                db.add(outer)
                with db.begin_nested():
                    db.add(AuditExample(name="inner"))
                with db.begin_nested():
                    db.add(AuditExample(name="inner-2"))
                outer.note = "committed"
                db.commit()
            logs = db.scalars(
                select(SysOperationLog).where(SysOperationLog.action == "test.savepoint")
            ).all()
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0].affected_count, 3)

    def test_savepoint_rollback_keeps_only_outer_changes(self):
        with self.Session() as db:
            row = AuditExample(name="before", note="before")
            db.add(row)
            db.commit()
            with audit_scope("test.savepoint.rollback", "保存点回滚", source="user"):
                row.name = "outer"
                try:
                    with db.begin_nested():
                        row.note = "inner"
                        db.flush()
                        raise ValueError("rollback savepoint")
                except ValueError:
                    pass
                db.commit()
            log = db.scalar(
                select(SysOperationLog).where(
                    SysOperationLog.action == "test.savepoint.rollback"
                )
            )
            item = db.scalar(
                select(SysOperationLogItem).where(SysOperationLogItem.log_id == log.id)
            )
            changes = {change["path"]: change for change in item.changes}
            self.assertEqual(changes["name"]["before"], "before")
            self.assertEqual(changes["name"]["after"], "outer")
            self.assertNotIn("note", changes)

    def test_savepoint_flush_error_keeps_outer_changes(self):
        with self.Session() as db:
            row = AuditExample(name="before", note="before")
            db.add(row)
            db.commit()
            with audit_scope("test.savepoint.integrity", "保存点冲突", source="user"):
                row.name = "outer"
                try:
                    with db.begin_nested():
                        db.add(AuditExample(name="outer"))
                        db.flush()
                except IntegrityError:
                    pass
                row.note = "committed"
                db.commit()
            log = db.scalar(
                select(SysOperationLog).where(
                    SysOperationLog.action == "test.savepoint.integrity"
                )
            )
            item = db.scalar(
                select(SysOperationLogItem).where(SysOperationLogItem.log_id == log.id)
            )
            changes = {change["path"]: change for change in item.changes}
            self.assertEqual(changes["name"]["after"], "outer")
            self.assertEqual(changes["note"]["after"], "committed")

    def test_json_original_survives_savepoint_rollback(self):
        with self.Session() as db:
            row = AuditExample(name="json", payload={"status": "old"})
            db.add(row)
            db.commit()
            with audit_scope("test.json.rollback", "JSON 回滚", source="user"):
                try:
                    with db.begin_nested():
                        row.payload = {"status": "rolled-back"}
                        db.flush()
                        raise ValueError("rollback savepoint")
                except ValueError:
                    pass
                row.payload["status"] = "new"
                flag_modified(row, "payload")
                db.commit()
            log = db.scalar(
                select(SysOperationLog).where(SysOperationLog.action == "test.json.rollback")
            )
            item = db.scalar(
                select(SysOperationLogItem).where(SysOperationLogItem.log_id == log.id)
            )
            change = item.changes[0]
            self.assertEqual(change["before"], "old")
            self.assertEqual(change["after"], "new")
            self.assertEqual(change["change_kind"], "update")

    def test_json_original_survives_root_rollback(self):
        with self.Session() as db:
            row = AuditExample(name="json-root", payload={"status": "old"})
            db.add(row)
            db.commit()
            with audit_scope("test.json.root.rollback", "JSON 根回滚", source="user"):
                row.payload = {"status": "rolled-back"}
                flag_modified(row, "payload")
                db.flush()
                db.rollback()
                row.payload["status"] = "new"
                flag_modified(row, "payload")
                db.commit()
            log = db.scalar(
                select(SysOperationLog).where(
                    SysOperationLog.action == "test.json.root.rollback"
                )
            )
            item = db.scalar(
                select(SysOperationLogItem).where(SysOperationLogItem.log_id == log.id)
            )
            change = item.changes[0]
            self.assertEqual(change["before"], "old")
            self.assertEqual(change["after"], "new")

    def test_rolled_back_log_does_not_suppress_failed_attempt(self):
        context = AuditContext(
            request_id="rollback-attempt",
            source="user",
            method="POST",
            path="/api/test/save",
            actions=(
                SimpleNamespace(
                    code="test.save",
                    name="测试保存",
                    operation_type="update",
                    resource="test",
                ),
            ),
        )
        with self.Session() as db:
            token = set_audit_context(context)
            try:
                write_operation_log(db, "test.rollback", result="success")
                db.rollback()
            finally:
                reset_audit_context(token)
        self.assertEqual(context.committed_results, set())
        with patch.object(audit_middleware, "_write_attempt_log") as fallback:
            audit_middleware._finalize_attempt(
                context,
                200,
                json.dumps({"code": 1, "message": "保存失败"}).encode(),
            )
        fallback.assert_called_once()

    def test_failed_audit_insert_does_not_mark_result_committed(self):
        with self.Session() as db:
            row = AuditExample(name="before")
            db.add(row)
            db.commit()

            def fail_audit_insert(
                _connection,
                _cursor,
                statement,
                _parameters,
                _context,
                _executemany,
            ):
                if "INSERT INTO sys_operation_log " in statement:
                    raise RuntimeError("simulated audit insert failure")

            event.listen(self.engine, "before_cursor_execute", fail_audit_insert)
            try:
                with audit_scope(
                    "test.commit.failure",
                    "提交失败测试",
                    source="user",
                ) as context:
                    row.name = "after"
                    with self.assertRaises(RuntimeError):
                        db.commit()
                    db.rollback()
            finally:
                event.remove(self.engine, "before_cursor_execute", fail_audit_insert)

        self.assertEqual(context.committed_results, set())
        with patch.object(audit_middleware, "_write_attempt_log") as fallback:
            audit_middleware._finalize_attempt(context, 500, b"")
        fallback.assert_called_once()

    def test_plain_external_session_is_not_audited(self):
        PlainSession = sessionmaker(bind=self.engine, expire_on_commit=False)
        with PlainSession() as db:
            db.add(AuditExample(name="external"))
            db.commit()
            self.assertEqual(db.scalar(select(SysOperationLog)), None)

    def test_explicit_log_collects_automatic_entity_items(self):
        with self.Session() as db:
            with audit_scope(
                "test.explicit",
                "显式日志测试",
                source="user",
            ) as context:
                db.add(AuditExample(name="created"))
                write_operation_log(
                    db,
                    "test.explicit",
                    operation_name="显式日志测试",
                    operation_type="create",
                )
                db.commit()
            logs = db.scalars(
                select(SysOperationLog).where(SysOperationLog.action == "test.explicit")
            ).all()
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0].affected_count, 1)
            self.assertEqual(len(logs[0].items), 1)
            self.assertEqual(logs[0].target_id, str(logs[0].items[0].entity_id))
            self.assertEqual(context.committed_results, {"success"})

    def test_explicit_failed_result_is_registered_only_after_commit(self):
        with self.Session() as db:
            with audit_scope("test.explicit.failed", "显式失败", source="user") as context:
                write_operation_log(db, "test.explicit.failed", result="failed")
                self.assertEqual(context.committed_results, set())
                db.commit()
            self.assertEqual(context.committed_results, {"failed"})

    def test_unchanged_user_roles_are_preserved_without_unique_conflict(self):
        Base.metadata.create_all(self.engine, tables=[SysUserRole.__table__])
        with self.Session() as db:
            db.add(SysUserRole(user_id=10, role_id=20))
            db.commit()
            with audit_scope("test.roles.same", "角色不变", source="user"):
                system_routes._replace_user_roles(db, 10, [20])
                db.commit()
            rows = db.scalars(
                select(SysUserRole).where(SysUserRole.user_id == 10)
            ).all()
            self.assertEqual([(row.user_id, row.role_id) for row in rows], [(10, 20)])
            self.assertIsNone(
                db.scalar(
                    select(SysOperationLog).where(
                        SysOperationLog.action == "test.roles.same"
                    )
                )
            )

    def test_labillion_failure_is_audited_but_still_acknowledged(self):
        with self.Session() as db:
            with (
                patch.object(
                    mega_routes.callback,
                    "handle_labillion_status_push",
                    side_effect=RuntimeError("internal failure"),
                ),
                patch.object(mega_routes.logger, "exception"),
            ):
                response = mega_routes.labillion_status_callback(
                    {"dispatchId": "dispatch-1", "payload": "secret"},
                    db,
                )
            log = db.scalar(
                select(SysOperationLog).where(
                    SysOperationLog.action == "mega.labillion.callback"
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.body)["data"]["reason"], "internal_error")
            self.assertEqual(log.result, "failed")
            self.assertEqual(log.target_id, "dispatch-1")
            self.assertNotIn("secret", str(log.detail))

    def test_labillion_noop_uses_canonical_audit_identity(self):
        result = {
            "applied": False,
            "reason": "dispatch_terminal",
            "dispatchId": "dispatch-2",
        }
        with self.Session() as db:
            with patch.object(
                mega_routes.callback,
                "handle_labillion_status_push",
                return_value=result,
            ):
                response = mega_routes.labillion_status_callback(
                    {"dispatchId": "dispatch-2"},
                    db,
                )
            log = db.scalar(
                select(SysOperationLog).where(
                    SysOperationLog.action
                    == audit_config.LABILLION_CALLBACK_AUDIT_ACTION.code
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(log.target_id, "dispatch-2")
            self.assertEqual(log.detail["change_summary"], "dispatch_terminal")

    def test_labillion_non_object_body_is_failed_audit_with_200_ack(self):
        db = MagicMock()
        with (
            patch.object(
                mega_routes.callback,
                "handle_labillion_status_push",
            ) as callback_handler,
            patch.object(mega_routes, "write_operation_log") as write_log,
            patch.object(mega_routes.logger, "exception"),
        ):
            response = mega_routes.labillion_status_callback(["invalid"], db)
        callback_handler.assert_not_called()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(write_log.call_args.kwargs["result"], "failed")

    def test_project_terminal_transition_only_repairs_required_successors(self):
        terminal = SimpleNamespace(
            id=1,
            plan_status=immunology_workbench_service.PLAN_STATUS_STARTED,
            experiment_id="EXP-1",
            sort_order=2,
        )
        positioned = SimpleNamespace(
            id=2,
            plan_status="草稿",
            experiment_id=None,
            sort_order=3,
        )
        db = MagicMock()
        db.scalar.return_value = terminal
        with (
            patch.object(immunology_workbench_service, "_lock_queue"),
            patch.object(
                immunology_workbench_service,
                "_queue_rows",
                return_value=[terminal, positioned],
            ),
        ):
            immunology_workbench_service.sync_project_queue_status(
                db,
                "EXP-1",
                is_terminal=True,
            )
        self.assertIsNone(terminal.sort_order)
        self.assertEqual(positioned.sort_order, 1)

    def test_queue_rows_include_null_and_missing_project_statuses(self):
        workbench_model = immunology_workbench_service.SerumImmWorkbench
        project_model = immunology_workbench_service.SerumImmProject
        Base.metadata.create_all(
            self.engine,
            tables=[project_model.__table__, workbench_model.__table__],
        )
        with self.Session() as db:
            default_plan = workbench_model(
                experiment_id="QUEUE-NULL-PLAN",
                plan_status=None,
                sort_order=1,
            )
            missing_project = workbench_model(
                experiment_id="QUEUE-MISSING-PROJECT",
                plan_status=immunology_workbench_service.PLAN_STATUS_STARTED,
                sort_order=2,
            )
            db.add_all([default_plan, missing_project])
            db.commit()
            queued_ids = {
                row.id for row in immunology_workbench_service._queue_rows(db)
            }
            self.assertEqual(queued_ids, {default_plan.id, missing_project.id})


class AuditMiddlewareTests(unittest.TestCase):
    def test_business_error_is_failed_even_with_http_200(self):
        result, message = _parse_result(
            200,
            json.dumps({"code": 1, "message": "保存失败"}).encode(),
        )
        self.assertEqual(result, "failed")
        self.assertEqual(message, "保存失败")
        self.assertEqual(
            _parse_result(200, json.dumps({"code": 0, "data": {}}).encode()),
            ("success", None),
        )

    def test_truncated_json_response_uses_business_code_prefix(self):
        self.assertEqual(
            _parse_result(
                200,
                b'{"code":1,"message":"' + b"x" * 1024,
                response_truncated=True,
            ),
            ("failed", "1"),
        )
        self.assertEqual(
            _parse_result(
                200,
                b'{"code":0,"data":"' + b"x" * 1024,
                response_truncated=True,
            ),
            ("success", None),
        )

    def test_path_parameter_mapping(self):
        self.assertTrue(
            audit_path_matches(
                "/api/mega-automation/flow-work-orders/{order_id}/complete",
                "/api/mega-automation/flow-work-orders/42/complete",
            )
        )

    def test_labillion_status_sync_uses_chinese_audit_name(self):
        with patch.object(audit_middleware, "_get_action_mappings", return_value=()):
            context = audit_middleware._build_context(
                "POST",
                "/api/mega-automation/flow-work-orders/12/sync-labillion-status",
                {},
                {},
            )
        action = context.actions[0]
        self.assertEqual(
            action.code,
            audit_config.LABILLION_STATUS_SYNC_AUDIT_ACTION.code,
        )
        self.assertEqual(action.name, "同步镁伽工单状态")


class AuditCoverageTests(unittest.TestCase):
    def test_all_write_routes_are_classified_from_versioned_schema_seed(self):
        schema_path = Path(__file__).resolve().parents[2] / "docs" / "vita-database.sql"
        sql = schema_path.read_text(encoding="utf-8")
        mappings = re.findall(
            r"\('[^']+',\s*'(DELETE|PATCH|POST|PUT)',\s*'([^']+)'",
            sql,
        )
        self.assertGreater(len(mappings), 40)
        self.assertEqual(unclassified_write_routes(app, mappings), set())


if __name__ == "__main__":
    unittest.main()
