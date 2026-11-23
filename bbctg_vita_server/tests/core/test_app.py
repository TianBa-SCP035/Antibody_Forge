"""基础设施：模块注册表完整性、运行配置自检、上传路径、全局异常处理与请求日志脱敏。"""

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

import modules.registry as registry
from core.config import DEFAULT_SECRET_KEY, Settings
from core.errors import (
    UNEXPECTED_MESSAGE,
    BusinessError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    setup_exception_handlers,
)
from core.logging import REDACTED, _redact_sensitive_values, _sanitize_body_for_log, is_sensitive_key
from core.module_spec import ModuleAccess, feature, page
from db.session import get_db
from jobs.registry import SCHEDULED_JOBS
from utils.uploads import contained_path, read_limited, safe_path_part, upload_filename


class ModuleRegistryTests(unittest.TestCase):
    def test_duplicate_permission_code_is_rejected(self):
        duplicated = page("demo.page", "示例", resource="demo", route_path="/demo", sort_order=1, message="无权限")
        with patch.object(registry, "ACCESS", (ModuleAccess("a", (duplicated,)), ModuleAccess("b", (duplicated,)))):
            with self.assertRaises(RuntimeError):
                registry._index_permissions()

    def test_duplicate_feature_code_is_rejected(self):
        flag = feature("feature.demo", "示例", "", sort_order=1, enabled=False)
        with patch.object(registry, "ACCESS", (ModuleAccess("a", features=(flag,)), ModuleAccess("b", features=(flag,)))):
            with self.assertRaises(RuntimeError):
                registry._index_features()

    def test_conflicting_resource_label_is_rejected(self):
        with patch.object(registry, "ACCESS", (ModuleAccess("a", resources={"demo": "示例"}),
                                               ModuleAccess("b", resources={"demo": "别名"}))):
            with self.assertRaises(RuntimeError):
                registry._merge_resources()

    def test_permission_parents_and_resources_are_registered(self):
        for code, permission in registry.PERMISSIONS.items():
            with self.subTest(code=code):
                if permission.parent_code:
                    self.assertIn(permission.parent_code, registry.PERMISSIONS)
                self.assertIn(permission.resource, registry.RESOURCE_LABELS)
                if permission.type == "page":
                    self.assertTrue(permission.route_path)

    def test_menu_parents_are_registered_menus(self):
        menus = {code for code, flag in registry.FEATURE_INDEX.items() if flag["category"] == "menu"}
        for code in menus:
            parent = registry.FEATURE_INDEX[code]["config"].get("parent_code")
            if parent:
                with self.subTest(code=code):
                    self.assertIn(parent, menus)

    def test_every_scheduled_job_declares_its_feature_and_resource(self):
        for job in SCHEDULED_JOBS:
            with self.subTest(job=job["id"]):
                self.assertEqual(registry.FEATURE_INDEX[job["feature_code"]]["category"], "job")
                self.assertIn(job["resource"], registry.RESOURCE_LABELS)


def _settings(**overrides):
    base = {
        "app_env": "prod",
        "database_url": "mysql+pymysql://vita:pw@db:3306/bbctg_vita",
        "secret_key": "x" * 40,
        "cors_origins": "https://vita.biocytogen.local",
        "debug": False,
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)


class RuntimeConfigTests(unittest.TestCase):
    def test_prod_rejects_default_secret_wildcard_cors_and_debug(self):
        problems = _settings(secret_key=DEFAULT_SECRET_KEY, cors_origins="*", debug=True).runtime_problems()
        self.assertEqual(len(problems), 3)

    def test_prod_rejects_short_secret_and_example_domain(self):
        problems = _settings(secret_key="abc123", cors_origins="https://your-domain.example").runtime_problems()
        self.assertEqual(len(problems), 2)

    def test_prod_allows_same_origin_deploy(self):
        self.assertEqual(_settings(cors_origins="").runtime_problems(), [])

    def test_non_prod_is_not_checked(self):
        self.assertEqual(_settings(app_env="local", secret_key=DEFAULT_SECRET_KEY).runtime_problems(), [])


class UploadPathTests(unittest.TestCase):
    def test_filename_strips_directories(self):
        self.assertEqual(upload_filename("C:\\fakepath\\..\\结果.xlsx"), "结果.xlsx")
        self.assertEqual(upload_filename("../../etc/passwd"), "passwd")
        with self.assertRaises(ValueError):
            upload_filename("..")

    def test_path_part_rejects_traversal(self):
        self.assertEqual(safe_path_part("25D2545-01"), "25D2545-01")
        for bad in ("..", "a/b", "a\\b", "C:", ""):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                safe_path_part(bad)

    def test_contained_path_rejects_escaping_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(contained_path(root, "/titer_files/E1/a.png"), (root / "titer_files/E1/a.png").resolve())
            with self.assertRaises(ValueError):
                contained_path(root, "/titer_files/../../outside.txt")

    def test_read_limited_rejects_oversized_stream(self):
        self.assertEqual(read_limited(io.BytesIO(b"abc"), 3), b"abc")
        with self.assertRaises(ValueError):
            read_limited(io.BytesIO(b"abcd"), 3)


class ExceptionHandlerTests(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        app = FastAPI()
        setup_exception_handlers(app)

        @app.post("/raise/{kind}")
        def raise_kind(kind: str, db=Depends(get_db)):
            raise {
                "value": ValueError("实验号已存在"),
                "business": BusinessError("锁定", code=7, error_code="LOCKED"),
                "forbidden": ForbiddenError("没有权限修改该字段"),
                "missing": NotFoundError("记录不存在"),
                "conflict": ConflictError("记录已被其他用户修改，请按最新内容重新填写"),
                "internal": RuntimeError("(pymysql.err.OperationalError) secret dsn"),
            }[kind]

        @app.post("/ok")
        def ok(db=Depends(get_db)):
            return {"code": 0}

        patcher = patch("db.session.SessionLocal", return_value=self.db)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = TestClient(app, raise_server_exceptions=False)
        self.addCleanup(self.client.close)

    def test_business_errors_map_to_status_and_roll_back(self):
        for kind, status, message in (
            ("value", 422, "实验号已存在"),
            ("business", 422, "锁定"),
            ("forbidden", 403, "没有权限修改该字段"),
            ("missing", 404, "记录不存在"),
            ("conflict", 409, "记录已被其他用户修改，请按最新内容重新填写"),
        ):
            with self.subTest(kind=kind):
                self.db.reset_mock()
                response = self.client.post(f"/raise/{kind}")
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.json()["message"], message)
                self.db.rollback.assert_called_once()
                self.db.close.assert_called_once()
        self.assertEqual(self.client.post("/raise/business").json()["code"], 7)

    def test_internal_errors_are_hidden(self):
        with patch("core.errors.logger") as logger:
            response = self.client.post("/raise/internal")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["message"], UNEXPECTED_MESSAGE)
        logger.error.assert_called_once()
        self.db.rollback.assert_called_once()

    def test_success_does_not_roll_back(self):
        self.assertEqual(self.client.post("/ok").status_code, 200)
        self.db.rollback.assert_not_called()
        self.db.close.assert_called_once()


class RequestLoggingTests(unittest.TestCase):
    def test_body_summary_lists_fields_without_values(self):
        body = json.dumps({"username": "alice", "newPassword": "secret", "ticket": "token"}).encode()
        summary = _sanitize_body_for_log(body, "application/json")
        self.assertEqual(summary["bytes"], len(body))
        self.assertEqual(summary["fields"], ["newPassword", "ticket", "username"])
        self.assertNotIn("secret", str(summary))

    def test_sensitive_keys_are_redacted(self):
        for key in ("newPassword", "privateKey", "passwd", "cookie", "ticket"):
            with self.subTest(key=key):
                self.assertTrue(is_sensitive_key(key))
        self.assertFalse(is_sensitive_key("username"))
        self.assertEqual(_redact_sensitive_values({"ticket": "secret"})["ticket"], REDACTED)
