"""流式工单的内容校验、细胞板列占用、列表筛选与内容哈希冲突。"""

import unittest
from datetime import datetime
from unittest.mock import patch

from core.errors import ConflictError
from models.mega_automation import MegaFlowWorkOrder, MegaFlowWorkOrderDispatch
from modules.mega_automation import service
from modules.mega_automation.content import (
    build_content_body,
    collect_validation_issues,
    default_cell_columns,
    default_sample_wells,
    resolve_cell_plate_usage,
)
from support import DbTestCase

_CONFLICT_MESSAGE = "工单内容已被其他用户修改，请刷新后重试"
_OPERATOR = "测试员"
_PAUSED_CHANGE_MESSAGE = (
    "工单内容已变更。确认后将使此前有效的下发记录失效，且无法再通过「继续」恢复为原发送状态。"
)


def _messages(issues):
    return [item["message"] for item in issues]


def _payload(order_type="TITER", **overrides):
    columns = default_cell_columns()
    columns[0]["cell_name"] = "CHO"
    columns[0]["cell_type"] = "正常"
    columns[1]["cell_name"] = "HEK"
    columns[1]["cell_type"] = "肿瘤"
    payload = {
        "orderNum": "ORD-1",
        "orderType": order_type,
        "orderName": "检测",
        "priority": "normal",
        "base_info": {"orderName": "检测", "remark": "", "pc_infos": []},
        "sample_plates": [
            {
                "barcode": "SMP-1",
                "project_no": "P1",
                "target": "PD1",
                "secondary_antibody": "",
                "cell_keys": [{"barcode": "CELL-1", "column_no": 1}],
                "wells": default_sample_wells(),
            }
        ],
        "cell_plates": [{"barcode": "CELL-1", "columns": columns}],
    }
    payload.update(overrides)
    return payload


class FlowWorkOrderContentTests(unittest.TestCase):
    def test_empty_secondary_antibody_defaults_by_order_type(self):
        titer = build_content_body(_payload("TITER"))
        plasmid = build_content_body(_payload("PLAS"))
        pcr = build_content_body(_payload("PCR"))
        kept = build_content_body({**_payload("TITER"), "sample_plates": [
            {**_payload("TITER")["sample_plates"][0], "secondary_antibody": "猴"}
        ]})
        self.assertEqual(titer["sample_plates"][0]["secondary_antibody"], "鼠")
        self.assertEqual(plasmid["sample_plates"][0]["secondary_antibody"], "人")
        self.assertEqual(pcr["sample_plates"][0]["secondary_antibody"], "人")
        self.assertEqual(kept["sample_plates"][0]["secondary_antibody"], "猴")

    def test_hidden_characters_are_removed_before_charset_checks(self):
        payload = _payload()
        payload["sample_plates"][0]["barcode"] = "SMP\n-1"
        payload["sample_plates"][0]["project_no"] = "P_1\t"
        payload["cell_plates"][0]["barcode"] = "CELL\u200b-1"
        content = build_content_body(payload)
        self.assertEqual(content["sample_plates"][0]["barcode"], "SMP-1")
        self.assertEqual(content["sample_plates"][0]["project_no"], "P_1")
        self.assertEqual(content["cell_plates"][0]["barcode"], "CELL-1")
        self.assertEqual(collect_validation_issues(payload), [])

        chinese = _payload()
        chinese["sample_plates"][0]["project_no"] = "项目1"
        chinese["cell_plates"][0]["barcode"] = "细胞板1"
        messages = _messages(collect_validation_issues(chinese))
        self.assertTrue(any("项目号" in message for message in messages))
        self.assertTrue(any("细胞板[1]条码" in message for message in messages))

    def test_sample_barcode_and_sample_code_charset(self):
        payload = _payload()
        payload["sample_plates"][0]["barcode"] = "SMP_1"
        payload["sample_plates"][0]["wells"][0]["sample_code"] = "A_01"
        payload["sample_plates"][0]["wells"][1]["sample_code"] = "A.02"
        messages = _messages(collect_validation_issues(payload))
        self.assertTrue(any("不能包含下划线" in message for message in messages))
        self.assertFalse(any("A_01" in message for message in messages))
        self.assertTrue(any("A02" in message and "样本编码" in message for message in messages))

        chinese = _payload()
        chinese["sample_plates"][0]["barcode"] = "样本1"
        messages = _messages(collect_validation_issues(chinese))
        self.assertTrue(any("英文括号和中划线" in message for message in messages))

    def test_one_sample_plate_uses_one_cell_plate_and_unique_cell_names(self):
        payload = _payload()
        payload["cell_plates"].append(
            {
                "barcode": "CELL-2",
                "columns": default_cell_columns(),
            }
        )
        payload["cell_plates"][1]["columns"][0]["cell_name"] = "CHO"
        payload["cell_plates"][1]["columns"][0]["cell_type"] = "正常"
        payload["sample_plates"][0]["cell_keys"] = [
            {"barcode": "CELL-1", "column_no": 1},
            {"barcode": "CELL-2", "column_no": 1},
        ]
        messages = _messages(collect_validation_issues(payload))
        self.assertTrue(any("同一块细胞板" in message for message in messages))
        self.assertTrue(any("细胞名称重复" in message for message in messages))

        same_plate = _payload()
        same_plate["sample_plates"][0]["cell_keys"] = [
            {"barcode": "CELL-1", "column_no": 1},
            {"barcode": "CELL-1", "column_no": 2},
        ]
        self.assertFalse(
            any("同一块细胞板" in message for message in _messages(collect_validation_issues(same_plate)))
        )

    def test_pcr_requires_control_plate_for_each_target(self):
        missing = _payload("PCR")
        self.assertTrue(any("-PC" in message for message in _messages(collect_validation_issues(missing))))

        covered = _payload("PCR")
        covered["sample_plates"].append(
            {
                **covered["sample_plates"][0],
                "barcode": "SMP-1-PC",
                "cell_keys": [{"barcode": "CELL-1", "column_no": 2}],
            }
        )
        self.assertFalse(any("-PC" in message for message in _messages(collect_validation_issues(covered))))
        self.assertEqual(collect_validation_issues(_payload("TITER")), [])

    def test_occupied_column_cannot_be_selected_or_rewritten(self):
        payload = _payload()
        usage = {
            "CELL-1": {
                "barcode": "CELL-1",
                "columns": [
                    {
                        "column_no": 1,
                        "locked": True,
                        "conflict": False,
                        "source_order_num": "ORD-OLD",
                        "used_by": [{"id": 9, "orderNum": "ORD-OLD", "status": "validated"}],
                        "cell_name": "CHO",
                        "cell_type": "正常",
                        "species": "",
                        "batch": "",
                        "generation": "",
                        "cell_count": "",
                        "catalog_no": "",
                        "source": "",
                    }
                ],
            }
        }
        messages = _messages(collect_validation_issues(payload, column_usage=usage))
        self.assertTrue(any("已被订单 ORD-OLD 使用" in message for message in messages))
        self.assertFalse(any("不能修改该列信息" in message for message in messages))

        payload["cell_plates"][0]["columns"][0]["cell_name"] = "HEK"
        messages = _messages(collect_validation_issues(payload, column_usage=usage))
        self.assertTrue(any("不能修改该列信息" in message for message in messages))

        payload["sample_plates"][0]["cell_keys"] = [{"barcode": "CELL-1", "column_no": 2}]
        payload["cell_plates"][0]["columns"][0]["cell_name"] = ""
        payload["cell_plates"][0]["columns"][0]["cell_type"] = ""
        self.assertFalse(
            any("ORD-OLD" in message for message in _messages(collect_validation_issues(payload, column_usage=usage)))
        )

    def test_resolve_locks_used_columns_and_merges_unused_ones(self):
        peers = [
            {
                "id": 1,
                "orderNum": "A",
                "status": "draft",
                "updated_at": "2026-10-01 10:00:00",
                "content": {
                    "sample_plates": [{"cell_keys": [{"barcode": "CELL-1", "column_no": 1}]}],
                    "cell_plates": [
                        {
                            "barcode": "CELL-1",
                            "columns": [
                                {"column_no": 1, "cell_name": "CHO", "cell_type": "正常"},
                                {"column_no": 2, "cell_name": "HEK", "cell_type": "肿瘤", "batch": "B1"},
                            ],
                        }
                    ],
                },
            },
            {
                "id": 2,
                "orderNum": "B",
                "status": "validated",
                "updated_at": "2026-10-02 10:00:00",
                "content": {
                    "sample_plates": [],
                    "cell_plates": [
                        {
                            "barcode": "CELL-1",
                            "columns": [
                                {"column_no": 1, "cell_name": "SHOULD-NOT-WIN", "cell_type": "肿瘤", "batch": "full"},
                                {"column_no": 2, "cell_name": "OTHER", "cell_type": "正常"},
                            ],
                        }
                    ],
                },
            },
        ]
        usage = resolve_cell_plate_usage("CELL-1", peers)
        by_no = {item["column_no"]: item for item in usage["columns"]}
        self.assertTrue(by_no[1]["locked"])
        self.assertEqual(by_no[1]["cell_name"], "CHO")
        self.assertEqual(by_no[1]["used_by"][0]["orderNum"], "A")
        self.assertFalse(by_no[2]["locked"])
        self.assertEqual(by_no[2]["cell_name"], "HEK")
        self.assertTrue(by_no[2]["conflict"])
        self.assertEqual(by_no[2]["source_order_num"], "A")


class FlowWorkOrderListTests(DbTestCase):
    tables = (MegaFlowWorkOrder, MegaFlowWorkOrderDispatch)

    def setUp(self):
        super().setUp()
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


class FlowWorkOrderContentHashTests(DbTestCase):
    tables = (MegaFlowWorkOrder, MegaFlowWorkOrderDispatch)

    def _withdrawn_order(self):
        payload = _payload()
        saved = service.save_work_order(self.db, payload, _OPERATOR)
        validated = service.validate_work_order(
            self.db, saved["id"], {"expected_content_hash": saved["content_hash"]}
        )
        self.assertTrue(validated["valid"], validated["errors"])
        service.dispatch_work_order(self.db, saved["id"], _OPERATOR, simulate=True)
        detail = service.pause_work_order(self.db, saved["id"], simulate=True)
        self.assertEqual(detail["status"], "paused")
        self.assertEqual(detail["dispatches"][0]["status"], "pending")
        self.assertEqual(detail["dispatches"][0]["pause_state"], "withdrawn")
        return payload, detail

    def test_stale_expected_content_hash_raises_conflict(self):
        saved = service.save_work_order(self.db, _payload(), _OPERATOR)
        order_id = saved["id"]
        original_hash = saved["content_hash"]

        with self.subTest(action="save"):
            with self.assertRaises(ConflictError) as caught:
                service.save_work_order(
                    self.db,
                    {"id": order_id, "expected_content_hash": "stale", "remark": "别人改过"},
                    _OPERATOR,
                )
            self.assertEqual(str(caught.exception), _CONFLICT_MESSAGE)
            self.db.rollback()
            detail = service.get_work_order_detail(self.db, order_id)
            self.assertEqual(detail["status"], "draft")
            self.assertEqual(detail["remark"], "")
            self.assertEqual(detail["content_hash"], original_hash)

        with self.subTest(action="validate"):
            with self.assertRaises(ConflictError) as caught:
                service.validate_work_order(self.db, order_id, {"expected_content_hash": "stale"})
            self.assertEqual(str(caught.exception), _CONFLICT_MESSAGE)
            self.db.rollback()
            detail = service.get_work_order_detail(self.db, order_id)
            self.assertEqual(detail["status"], "draft")
            self.assertEqual(detail["content_hash"], original_hash)

    def test_stale_hash_on_withdrawn_order_keeps_dispatch(self):
        payload, detail = self._withdrawn_order()
        with self.assertRaises(ConflictError) as caught:
            service.validate_work_order(
                self.db,
                detail["id"],
                {
                    "expected_content_hash": "stale",
                    "confirm_revoke": True,
                    "payload": {**payload, "remark": "别人改过"},
                },
            )
        self.assertEqual(str(caught.exception), _CONFLICT_MESSAGE)
        self.db.rollback()
        fresh = service.get_work_order_detail(self.db, detail["id"])
        self.assertEqual(fresh["status"], "paused")
        self.assertEqual(fresh["remark"], "")
        self.assertEqual(fresh["content_hash"], detail["content_hash"])
        self.assertEqual(fresh["dispatches"][0]["status"], "pending")
        self.assertEqual(fresh["dispatches"][0]["pause_state"], "withdrawn")

    def test_unconfirmed_withdrawn_edit_keeps_previous_dispatch(self):
        payload, detail = self._withdrawn_order()
        result = service.validate_work_order(
            self.db,
            detail["id"],
            {
                "expected_content_hash": detail["content_hash"],
                "payload": {**payload, "remark": "已改"},
            },
        )
        self.assertTrue(result["valid"])
        self.assertTrue(result["needs_confirm"])
        self.assertTrue(result["content_changed"])
        self.assertFalse(result["saved"])
        self.assertFalse(result["can_resume"])
        self.assertEqual(result["message"], _PAUSED_CHANGE_MESSAGE)
        fresh = service.get_work_order_detail(self.db, detail["id"])
        self.assertEqual(fresh["status"], "paused")
        self.assertEqual(fresh["remark"], "")
        self.assertEqual(fresh["content_hash"], detail["content_hash"])
        self.assertEqual(fresh["dispatches"][0]["status"], "pending")
        self.assertEqual(fresh["dispatches"][0]["pause_state"], "withdrawn")

    def test_confirmed_withdrawn_edit_voids_previous_dispatch(self):
        payload, detail = self._withdrawn_order()
        result = service.validate_work_order(
            self.db,
            detail["id"],
            {
                "expected_content_hash": detail["content_hash"],
                "confirm_revoke": True,
                "payload": {**payload, "remark": "已改"},
            },
        )
        self.assertTrue(result["valid"])
        self.assertTrue(result["saved"])
        self.assertTrue(result["content_changed"])
        self.assertFalse(result["needs_confirm"])
        self.assertEqual(result["item"]["status"], "validated")
        self.assertEqual(result["item"]["remark"], "已改")
        self.assertNotEqual(result["item"]["content_hash"], detail["content_hash"])
        self.assertEqual(result["item"]["dispatches"][0]["dispatchId"], detail["dispatches"][0]["dispatchId"])
        self.assertEqual(result["item"]["dispatches"][0]["status"], "voided")
        self.assertEqual(result["item"]["dispatches"][0]["pause_state"], "")
        with self.assertRaises(ValueError) as caught:
            service.resume_work_order(self.db, detail["id"])
        self.assertEqual(str(caught.exception), "仅已撤回或已暂停的工单可以继续")

    def test_unchanged_withdrawn_content_resumes_same_dispatch(self):
        payload, detail = self._withdrawn_order()
        result = service.validate_work_order(
            self.db,
            detail["id"],
            {"expected_content_hash": detail["content_hash"], "payload": payload},
        )
        self.assertTrue(result["valid"])
        self.assertTrue(result["can_resume"])
        self.assertFalse(result["needs_confirm"])
        self.assertFalse(result["content_changed"])
        self.assertFalse(result["saved"])
        dispatch_id = detail["dispatches"][0]["dispatchId"]
        with patch("modules.mega_automation.service.push_flow_work_order") as push:
            resumed = service.resume_work_order(self.db, detail["id"])
        self.assertEqual(push.call_count, 1)
        self.assertEqual(resumed["status"], "sent")
        self.assertEqual(resumed["dispatches"][0]["dispatchId"], dispatch_id)
        self.assertEqual(resumed["dispatches"][0]["status"], "pending")
        self.assertEqual(resumed["dispatches"][0]["pause_state"], "")
