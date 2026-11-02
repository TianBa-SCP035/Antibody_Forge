"""流式工单列表的表头筛选：JSON 数组列、状态分组、取值列表与按时间排序。"""

import json
import unittest
from datetime import datetime

from models.mega_automation import MegaFlowWorkOrder, MegaFlowWorkOrderDispatch
from modules.mega_automation import service
from support import DbTestCase


class FlowWorkOrderHeaderFilterTests(DbTestCase):
    tables = (MegaFlowWorkOrder, MegaFlowWorkOrderDispatch)

    def setUp(self):
        super().setUp()
        raw = self.db.connection().connection.dbapi_connection
        raw.create_function("json_length", 1, lambda value: len(json.loads(value or "[]")))
        raw.create_function(
            "json_overlaps", 2, lambda left, right: bool(set(json.loads(left or "[]")) & set(json.loads(right or "[]")))
        )
        for num, status, projects, updated in (
            ("F1", "running", ["P1", "P2"], datetime(2026, 10, 1, 9)),
            ("F2", "execution_error", ["P2"], datetime(2026, 10, 2, 9)),
            ("F3", "manual_failed", [], datetime(2026, 10, 2, 18)),
        ):
            self.db.add(MegaFlowWorkOrder(orderNum=num, status=status, project_nos=projects, updated_at=updated))
        self.db.commit()

    def order_nums(self, **query):
        return [item["orderNum"] for item in service.get_work_order_list(self.db, query)["items"]]

    def test_json_array_column_matches_any_value_and_treats_empty_array_as_blank(self):
        self.assertEqual(self.order_nums(field_filters=[{"field": "project_nos", "values": ["P2"]}]), ["F2", "F1"])
        self.assertEqual(self.order_nums(field_filters=[{"field": "project_nos", "values": [""]}]), ["F3"])
        self.assertEqual(self.order_nums(field_filters=[{"field": "project_nos", "exclude": ["P1"]}]), ["F3", "F2"])

    def test_status_header_groups_execution_issues_and_leaves_stats_alone(self):
        result = service.get_work_order_list(
            self.db, {"field_filters": [{"field": "status", "values": ["execution_failed"]}]}
        )
        self.assertEqual([item["orderNum"] for item in result["items"]], ["F3", "F2"])
        self.assertEqual(result["stats"]["total"], 3)
        self.assertEqual(result["stats"]["execution_failed"], 2)

    def test_column_values_count_array_items_and_label_status(self):
        projects = service.get_column_values(self.db, {"field": "project_nos"})["items"]
        self.assertEqual(projects, [{"value": "P1", "count": 1}, {"value": "P2", "count": 2}, {"value": "", "count": 1}])
        statuses = service.get_column_values(self.db, {"field": "status"})["items"]
        self.assertEqual(
            [(item["value"], item["count"], item["label"]) for item in statuses],
            [("running", 1, "执行中"), ("execution_failed", 2, "执行异常")],
        )

    def test_time_column_filters_by_day_and_sorts_by_full_time(self):
        by_day = [{"field": "updated_at", "condition": {"op": "eq", "value": "2026-10-02"}}]
        self.assertEqual(self.order_nums(field_filters=by_day), ["F3", "F2"])
        self.assertEqual(self.order_nums(sort_field="updated_at", sort_dir="asc"), ["F1", "F2", "F3"])
        self.assertEqual(self.order_nums(sort_field="updated_at", sort_dir="desc"), ["F3", "F2", "F1"])


if __name__ == "__main__":
    unittest.main()
