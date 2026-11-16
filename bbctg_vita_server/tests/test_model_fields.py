import unittest
from datetime import date
from decimal import Decimal

from core.errors import ConflictError
from models.discovery import DiscoveryWorkbench
from utils.batch_save import check_expected, normalize_comparable
from utils.header_filters import HeaderColumn, header_columns
from utils.model_fields import clean_field, model_fields

FIELDS = model_fields(DiscoveryWorkbench, readonly=("discovery_id",))


class ModelFieldsTests(unittest.TestCase):
    def test_writable_fields_come_from_columns(self):
        self.assertNotIn("id", FIELDS)
        self.assertNotIn("discovery_id", FIELDS)
        self.assertTrue({"created_by", "created_at", "updated_by", "updated_at"}.isdisjoint(FIELDS))
        remark = FIELDS["remark"]
        self.assertEqual((remark.label, remark.kind, remark.max_length), ("备注", "text", 1000))
        self.assertEqual(FIELDS["harvest_date"].kind, "date")
        self.assertEqual(FIELDS["mouse_count"].kind, "int")
        self.assertEqual(FIELDS["target_codes"].kind, "json")

    def test_unknown_readonly_column_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "no_such_column"):
            model_fields(DiscoveryWorkbench, readonly=("no_such_column",))

    def test_clean_field_by_kind(self):
        self.assertEqual(clean_field(FIELDS["remark"], "  甲\n乙  ", keep_breaks=True), "甲\n乙")
        self.assertIsNone(clean_field(FIELDS["remark"], "   "))
        with self.assertRaisesRegex(ValueError, "免疫用抗原不能超过 1000 个字符"):
            clean_field(FIELDS["immune_antigen"], "A" * 1001)

        self.assertEqual(clean_field(FIELDS["harvest_date"], "2026/1/5"), date(2026, 1, 5))
        with self.assertRaisesRegex(ValueError, "剖鼠取细胞日格式不正确，应为 YYYY-MM-DD：2026-13-01"):
            clean_field(FIELDS["harvest_date"], "2026-13-01")

        self.assertEqual(clean_field(FIELDS["mouse_count"], " 5 "), 5)
        self.assertIsNone(clean_field(FIELDS["mouse_count"], ""))
        for bad in (-1, "1.5", 2.5, True, "五"):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "小鼠只数必须是非负整数"):
                clean_field(FIELDS["mouse_count"], bad)

        with self.assertRaises(TypeError):
            clean_field(FIELDS["target_codes"], ["20R001"])

    def test_header_columns_cover_plain_fields_except_sort(self):
        explicit = HeaderColumn(DiscoveryWorkbench.status, order=("规划中",))
        columns = header_columns(FIELDS, status=explicit)
        self.assertEqual(columns["remark"].kind, "text")
        self.assertEqual(columns["harvest_date"].kind, "date")
        self.assertEqual(columns["mouse_count"].kind, "number")
        self.assertIs(columns["status"], explicit)
        self.assertNotIn("sort_order", columns)
        self.assertNotIn("target_codes", columns)


class CheckExpectedTests(unittest.TestCase):
    def test_normalize_comparable_ignores_format_only(self):
        same = [
            (None, ""),
            (None, []),
            (" 甲 ", "甲"),
            (5, 5.0),
            (Decimal("5.50"), 5.5),
            (date(2026, 1, 5), "2026-01-05"),
            (["人", "猴", "人"], ["人", "猴"]),
        ]
        for left, right in same:
            with self.subTest(left=left, right=right):
                self.assertEqual(normalize_comparable(left), normalize_comparable(right))
        self.assertNotEqual(normalize_comparable("007"), normalize_comparable(7))
        self.assertNotEqual(normalize_comparable(["人", "猴"]), normalize_comparable(["猴", "人"]))

    def test_only_writable_fields_except_sort_are_compared(self):
        current = {"remark": "新", "sort_order": 3, "discovery_id": "DSC-1"}
        check_expected(current, {"sort_order": 9, "discovery_id": "OTHER", "remark": " 新 "}, fields=FIELDS)
        check_expected(current, None, fields=FIELDS)
        with self.assertRaises(ConflictError):
            check_expected(current, {"remark": "旧"}, fields=FIELDS)


if __name__ == "__main__":
    unittest.main()
