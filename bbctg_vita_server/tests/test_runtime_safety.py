import io
import tempfile
import threading
from contextlib import contextmanager, nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from core.config import DEFAULT_SECRET_KEY, Settings
from core.errors import (
    UNEXPECTED_MESSAGE,
    BusinessError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    setup_exception_handlers,
)
from db.session import get_db
from jobs import registry
from modules.auth.external import check_external_caller
from modules.system.features import run_recorded_job
from utils.uploads import contained_path, read_limited, safe_path_part, upload_filename


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


class RuntimeConfigTest(TestCase):
    def test_prod_rejects_defaults(self):
        problems = _settings(secret_key=DEFAULT_SECRET_KEY, cors_origins="*", debug=True).runtime_problems()
        self.assertEqual(len(problems), 3)

    def test_prod_rejects_short_secret_and_example_domain(self):
        problems = _settings(secret_key="abc123", cors_origins="https://your-domain.example").runtime_problems()
        self.assertEqual(len(problems), 2)

    def test_prod_allows_same_origin_deploy(self):
        self.assertEqual(_settings(cors_origins="").runtime_problems(), [])

    def test_non_prod_is_not_checked(self):
        self.assertEqual(_settings(app_env="local", secret_key=DEFAULT_SECRET_KEY).runtime_problems(), [])


def _request(headers=None, query=None, host="10.0.0.5"):
    return SimpleNamespace(headers=headers or {}, query_params=query or {}, client=SimpleNamespace(host=host))


class ExternalCallerTest(TestCase):
    def test_unconfigured_allows_everyone(self):
        check_external_caller(_request(), "", "")

    def test_token_only_from_header(self):
        check_external_caller(_request(headers={"X-Callback-Token": "s3cret"}), "s3cret", "")
        for request in (
            _request(headers={"X-Callback-Token": "wrong"}),
            _request(query={"token": "s3cret"}),
        ):
            with self.assertRaises(HTTPException) as raised:
                check_external_caller(request, "s3cret", "")
            self.assertEqual(raised.exception.status_code, 401)

    def test_ip_allowlist(self):
        check_external_caller(_request(host="10.0.0.5"), "", "10.0.0.5, 10.0.0.6")
        with self.assertRaises(HTTPException) as raised:
            check_external_caller(_request(host="10.0.0.9"), "", "10.0.0.5,10.0.0.6")
        self.assertEqual(raised.exception.status_code, 403)


class UploadHelpersTest(TestCase):
    def test_filename_strips_directories(self):
        self.assertEqual(upload_filename("C:\\fakepath\\..\\结果.xlsx"), "结果.xlsx")
        self.assertEqual(upload_filename("../../etc/passwd"), "passwd")
        with self.assertRaises(ValueError):
            upload_filename("..")

    def test_path_part_rejects_traversal(self):
        self.assertEqual(safe_path_part("25D2545-01"), "25D2545-01")
        for bad in ("..", "a/b", "a\\b", "C:", ""):
            with self.assertRaises(ValueError):
                safe_path_part(bad)

    def test_contained_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(contained_path(root, "/titer_files/E1/a.png"), (root / "titer_files/E1/a.png").resolve())
            with self.assertRaises(ValueError):
                contained_path(root, "/titer_files/../../outside.txt")

    def test_read_limited(self):
        self.assertEqual(read_limited(io.BytesIO(b"abc"), 3), b"abc")
        with self.assertRaises(ValueError):
            read_limited(io.BytesIO(b"abcd"), 3)


class ExceptionHandlerTest(TestCase):
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

    def test_business_errors_map_to_status_and_roll_back(self):
        for kind, status, message in (
            ("value", 422, "实验号已存在"),
            ("business", 422, "锁定"),
            ("forbidden", 403, "没有权限修改该字段"),
            ("missing", 404, "记录不存在"),
            ("conflict", 409, "记录已被其他用户修改，请按最新内容重新填写"),
        ):
            self.db.reset_mock()
            response = self.client.post(f"/raise/{kind}")
            self.assertEqual(response.status_code, status, kind)
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


class RecordedJobTest(TestCase):
    def _run(self, work, **kwargs):
        db = MagicMock()
        with (
            patch("modules.system.features.SessionLocal", return_value=db),
            patch("modules.system.features.record_job_run") as record,
        ):
            run_recorded_job("job.test", "测试任务", work, **kwargs)
        db.close.assert_called_once()
        return db, record.call_args.kwargs

    def test_success_uses_summary(self):
        _, logged = self._run(lambda db: {"created": 2}, summarize=lambda result: f"新增 {result['created']}")
        self.assertEqual((logged["result"], logged["summary"]), ("success", "新增 2"))

    def test_skip_needs_literal_true(self):
        _, logged = self._run(lambda db: {"skipped": True}, skip_summary="未配置，已跳过")
        self.assertEqual((logged["result"], logged["summary"]), ("skipped", "未配置，已跳过"))
        _, logged = self._run(lambda db: {"skipped": {"inactive": 3}, "created": 0})
        self.assertEqual(logged["result"], "success")

    def test_failure_is_logged_not_raised(self):
        def boom(db):
            raise RuntimeError("连接断开")

        db, logged = self._run(boom)
        db.rollback.assert_called_once()
        self.assertEqual((logged["result"], logged["error_message"]), ("failed", "连接断开"))


class RunJobNowTest(TestCase):
    def _run_now(self, acquired):
        ran = threading.Event()
        job = {"id": "demo", "feature_code": "job.demo", "name": "演示", "func": ran.set}

        @contextmanager
        def fake_lock(_job_id):
            yield acquired

        with (
            patch("jobs.registry.get_scheduled_job", return_value=job),
            patch("jobs.registry.job_lock", fake_lock),
            patch("jobs.registry.audit_scope", lambda *args, **kwargs: nullcontext()),
        ):
            registry.run_scheduled_job_now("job.demo")
        return ran.wait(2)

    def test_reports_success_only_after_taking_the_lock(self):
        self.assertTrue(self._run_now(True))

    def test_lock_held_elsewhere_is_reported(self):
        with self.assertRaisesRegex(ValueError, "正在运行"):
            self._run_now(False)
