from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from support import DbTestCase

import jobs.registry as registry
from models.system import SysFeatureFlag
from modules.registry import FEATURE_INDEX
from modules.system.features import (
    get_job_schedule,
    is_feature_enabled,
    list_feature_flags,
    save_feature_flag,
)


class FeatureFlagTests(DbTestCase):
    tables = (SysFeatureFlag,)

    def test_defaults_come_from_module_declarations(self):
        items = {item["code"]: item for item in list_feature_flags(self.db)}
        self.assertEqual(items.keys(), FEATURE_INDEX.keys())
        self.assertFalse(is_feature_enabled(self.db, "feature.drm_file_security"))
        self.assertEqual(
            get_job_schedule(self.db, "job.discovery_synthesis_order_sync")[1],
            {"schedule": "interval", "hour": 0, "minute": 20, "weekday": 0, "day": 1, "every": 1, "unit": "hour"},
        )

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
