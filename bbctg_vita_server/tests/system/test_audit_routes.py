"""路由审计：响应结果判定、路由声明解析、写接口覆盖检查与路由清单一致性。"""

import json
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from starlette.routing import compile_path

import modules.mega_automation.routes as mega_routes
import modules.system.audit_config as audit_config
import modules.system.audit_middleware as audit_middleware
from api import api_routes
from modules.auth.permissions import require
from modules.system.audit_config import is_readonly_post
from modules.system.audit_context import AuditAction, AuditContext
from modules.system.audit_coverage import unclassified_write_routes
from modules.system.audit_middleware import _parse_result
from modules.system.audit_routes import audit_quiet, permission_action, route_audit
from server import app


def _route_context(method: str, path: str, routes: list[tuple[str, APIRoute]] | None = None) -> AuditContext:
    context = audit_middleware._build_context(method, path, {}, {"headers": []})
    for full_path, route in api_routes() if routes is None else routes:
        if method in route.methods and compile_path(full_path)[0].match(path):
            audit_middleware.apply_route_audit(context, route)
            break
    return context


class ResultParsingTests(unittest.TestCase):
    def test_business_error_is_failed_even_with_http_200(self):
        self.assertEqual(_parse_result(200, json.dumps({"code": 1, "message": "保存失败"}).encode()), ("failed", "保存失败"))
        self.assertEqual(_parse_result(200, json.dumps({"code": 0, "data": {}}).encode()), ("success", None))

    def test_truncated_json_response_uses_business_code_prefix(self):
        self.assertEqual(
            _parse_result(200, b'{"code":1,"message":"' + b"x" * 1024, response_truncated=True),
            ("failed", "1"),
        )
        self.assertEqual(
            _parse_result(200, b'{"code":0,"data":"' + b"x" * 1024, response_truncated=True),
            ("success", None),
        )


class RouteDeclarationTests(unittest.TestCase):
    def test_explicit_declarations_resolve_to_actions(self):
        for path, action in (
            (
                "/api/mega-automation/flow-work-orders/42/complete",
                AuditAction("mega.flow_work_order.dispatch", "完成流式工单", "dispatch", "flow_work_order"),
            ),
            ("/api/mega-automation/flow-work-orders/12/sync-labillion-status", mega_routes.LABILLION_STATUS_SYNC_AUDIT_ACTION),
        ):
            with self.subTest(path=path):
                context = _route_context("POST", path)
                self.assertEqual(context.actions, (action,))
                self.assertTrue(context.explicitly_audited)
        self.assertEqual(mega_routes.LABILLION_STATUS_SYNC_AUDIT_ACTION.name, "同步镁伽状态")

    def test_quiet_routes_log_only_failures_under_their_name(self):
        for path, name in (
            ("/api/molecular-cell/library-orders/files/list", "刷新质检核对"),
            ("/api/molecular-cell/library-orders/files/preflight", "预检文库构建结果路径"),
        ):
            with self.subTest(path=path):
                context = _route_context("POST", path)
                self.assertEqual(context.actions, ())
                self.assertTrue(context.suppress_noop)
                self.assertEqual((context.fallback_name, context.fallback_resource), (name, "library_file"))

    def test_data_dependent_save_declares_create_and_edit_actions(self):
        context = _route_context("POST", "/api/serum/save")
        self.assertEqual(context.select_action("create").name, "新建免疫项目")
        self.assertEqual(context.select_action("update").name, "编辑免疫项目")

    def test_undeclared_route_has_no_actions(self):
        context = _route_context("POST", "/api/unknown/save")
        self.assertEqual(context.actions, ())
        self.assertFalse(context.suppress_noop)
        self.assertEqual(context.fallback_name, "POST /api/unknown/save")

    def test_real_request_binds_route_declaration_before_permission_check(self):
        client = TestClient(app)
        self.addCleanup(client.close)
        with patch.object(audit_middleware, "_write_attempt_log") as write_log:
            client.post("/api/mega-automation/flow-work-orders/42/complete")
        write_log.assert_called_once()
        context = write_log.call_args.args[0]
        self.assertEqual(context.select_action("update").code, "mega.flow_work_order.dispatch")

    def test_page_permission_cannot_declare_audit(self):
        with self.assertRaises(ValueError):
            require("molecular.page.primer", audit="导出引物库")
        with self.assertRaises(ValueError):
            permission_action("molecular.page.primer", "导出引物库")

    def test_unknown_permission_code_fails_at_declaration(self):
        with self.assertRaises(ValueError):
            require("molecular.primer.edti")


class AuditCoverageTests(unittest.TestCase):
    def test_every_write_route_declares_audit(self):
        self.assertEqual(unclassified_write_routes(api_routes()), set())

    def test_api_routes_match_served_paths(self):
        served = {path for path in app.openapi()["paths"] if path.startswith("/api/")}
        listed = {compile_path(path)[1] for path, route in api_routes() if route.include_in_schema}
        self.assertEqual(listed, served)

    def test_standard_readonly_post_suffixes_are_ignored_and_write_gate_remains_strict(self):
        demo = FastAPI()

        @demo.post("/api/demo/list")
        @demo.post("/api/demo/column_values")
        @demo.post("/api/demo/export_list")
        @demo.post("/api/demo/export")
        @demo.post("/api/demo/stats")
        @demo.post("/api/demo/save")
        @demo.post("/api/demo/delete")
        @demo.put("/api/demo/update")
        def _handler():
            return {}

        @demo.post("/api/demo/check", dependencies=[audit_quiet()])
        def _check():
            return {}

        demo_routes = [(route.path, route) for route in demo.routes if isinstance(route, APIRoute)]
        self.assertEqual(
            unclassified_write_routes(demo_routes),
            {("POST", "/api/demo/save"), ("POST", "/api/demo/delete"), ("PUT", "/api/demo/update")},
        )
        for suffix in audit_config.READ_ONLY_POST_SUFFIXES:
            with self.subTest(suffix=suffix):
                self.assertTrue(_route_context("POST", f"/api/demo{suffix}", demo_routes).suppress_noop)
        self.assertTrue(_route_context("POST", "/api/demo/check", demo_routes).suppress_noop)

    def test_quiet_marker_on_readonly_suffix_must_carry_a_name(self):
        redundant = {
            path
            for path, route in api_routes()
            if is_readonly_post("POST", path)
            and (spec := route_audit(route)) is not None
            and spec.quiet
            and not spec.fallback_name
        }
        self.assertEqual(redundant, set())
