import unittest

from modules.mega_automation.content import (
    build_content_body,
    collect_validation_issues,
    default_cell_columns,
    default_sample_wells,
    resolve_cell_plate_usage,
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


class FlowWorkOrderValidationTests(unittest.TestCase):
    def test_existing_rules_still_pass_for_a_complete_order(self):
        self.assertEqual(collect_validation_issues(_payload()), [])

    def test_empty_secondary_antibody_defaults_by_order_type(self):
        titer = build_content_body(_payload("TITER"))
        plasmid = build_content_body(_payload("PLAS"))
        pcr = build_content_body(_payload("PCR"))
        kept = build_content_body(_payload("TITER"))
        kept["sample_plates"][0]["secondary_antibody"] = "猴"
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
        self.assertFalse(any("同一块细胞板" in message for message in _messages(collect_validation_issues(same_plate))))

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


if __name__ == "__main__":
    unittest.main()
