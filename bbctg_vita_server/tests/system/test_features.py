"""功能开关与定时任务：登记默认值、保存覆盖、未登记编码、记录运行结果与手动触发。"""

import threading
import unittest
from contextlib import contextmanager, nullcontext
from unittest.mock import MagicMock, patch

from sqlalchemy import select
from sqlalchemy.exc import OperationalError

import jobs.registry as registry
from models.system import SysFeatureFlag
from modules.registry import FEATURE_INDEX
from modules.system.features import (
    get_job_schedule,
    is_feature_enabled,
    list_feature_flags,
    run_recorded_job,
    save_feature_flag,
)
from support import DbTestCase


class FeatureFlagTests(DbTestCase):
    tables = (SysFeatureFlag,)

    def test_defaults_come_from_module_declarations(self):
        items = {item["code"]: item for item in list_feature_flags(self.db)}
        self.assertEqual(items.keys(), FEATURE_INDEX.keys())
        self.assertFalse(is_feature_enabled(self.db, "feature.drm_file_security"))
        code = "job.discovery_synthesis_order_sync"
        enabled, config = get_job_schedule(self.db, code)
        self.assertEqual(enabled, FEATURE_INDEX[code]["enabled"])
        self.assertLessEqual(FEATURE_INDEX[code]["config"].items(), config.items())

    def test_saved_overrides_merge_with_declaration(self):
        saved = save_feature_flag(self.db, {
            "code": "job.serum_auto_update_status",
            "name": "改名无效",
            "enabled": False,
            "visible": True,
            "config": {"schedule": "weekly", "hour": 3, "minute": 5, "weekday": 2},
        })
        self.assertEqual(saved["name"], FEATURE_INDEX["job.serum_auto_update_status"]["name"])
        self.assertEqual(saved["category"], "job")
        self.assertFalse(saved["enabled"])
        self.assertEqual(saved["config"]["schedule"], "weekly")
        self.assertEqual(get_job_schedule(self.db, "job.serum_auto_update_status"),
                         (False, {"schedule": "weekly", "hour": 3, "minute": 5, "weekday": 2, "day": 1,
                                  "every": 1, "unit": "hour"}))

    def test_unreadable_job_flag_is_not_scheduled(self):
        failure = OperationalError("SELECT", {}, Exception("db down"))
        with patch.object(self.db, "scalar", side_effect=failure), self.assertRaises(OperationalError):
            get_job_schedule(self.db, "job.serum_auto_update_status")
        with patch("jobs.registry.get_job_schedule", side_effect=failure), self.assertLogs("jobs.registry", "ERROR"):
            self.assertEqual(registry._scheduled_job_config("job.serum_auto_update_status"), (False, {}))

    def test_undeclared_codes_are_rejected_and_hidden(self):
        with self.assertRaises(ValueError):
            save_feature_flag(self.db, {"code": "setting.site_title", "enabled": True, "visible": True})
        self.db.add(SysFeatureFlag(code="setting.site_title", enabled=True, visible=True, config={}))
        self.db.commit()
        self.assertNotIn("setting.site_title", {item["code"] for item in list_feature_flags(self.db)})

    def test_menu_sort_order_is_saved_as_override(self):
        code = "menu.serum.workbench"
        declared = FEATURE_INDEX[code]["sort_order"]
        saved = save_feature_flag(self.db, {"code": code, "enabled": True, "visible": True, "sort_order": declared + 100})
        self.assertEqual(saved["sort_order"], declared + 100)
        listed = {item["code"]: item for item in list_feature_flags(self.db)}[code]
        self.assertEqual(listed["sort_order"], declared + 100)

        # 调回登记值时不留覆盖，以后代码里改排序仍然生效
        save_feature_flag(self.db, {"code": code, "enabled": True, "visible": True, "sort_order": declared})
        flag = self.db.scalar(select(SysFeatureFlag).where(SysFeatureFlag.code == code))
        self.assertIsNone(flag.sort_order)
        # 只改显示不带排序时，已存的排序不动
        save_feature_flag(self.db, {"code": code, "enabled": True, "visible": True, "sort_order": 7})
        saved = save_feature_flag(self.db, {"code": code, "enabled": True, "visible": False})
        self.assertEqual(saved["sort_order"], 7)


class RecordedJobTests(unittest.TestCase):
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


class RunJobNowTests(unittest.TestCase):
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
