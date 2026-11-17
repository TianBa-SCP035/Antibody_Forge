"""公共工具：取值规范化、日期列类型、表头筛选、模型字段推导、冲突比对、撞号重试与队列加锁。"""

import unittest
from datetime import date
from decimal import Decimal

from sqlalchemy import String, event, select, text, update
from sqlalchemy.exc import IntegrityError, StatementError

from core.errors import ConflictError, _validation_error
from models.discovery import DiscoverySynthesisOrder, DiscoveryWorkbench
from models.immunology import SerumImmProject, SerumImmWorkbench
from models.target import Target
from models.types import DateString, date_blank, date_present
from modules.immunology.serum import service as serum
from support import DbTestCase
from utils.batch_save import check_expected, normalize_comparable
from utils.codes import insert_with_retry
from utils.header_filters import HeaderColumn, csv_token_clause, header_columns, header_filter_clauses
from utils.model_fields import clean_field, model_fields
from utils.normalize import (
    join_known_options,
    join_tokens,
    normalize_choice,
    normalize_date,
    normalize_target_codes,
    parse_date,
)
from utils.workbench_queue import lock_queue

FIELDS = model_fields(DiscoveryWorkbench, readonly=("discovery_id",))


class NormalizeTests(unittest.TestCase):
    def test_dates_accept_common_writing_and_store_iso(self):
        self.assertEqual(normalize_date("2026/1/5"), "2026-01-05")
        self.assertEqual(normalize_date("2026.01.05 08:30"), "2026-01-05")
        self.assertEqual(normalize_date("2026-01-05T08:30:00"), "2026-01-05")
        self.assertEqual(parse_date(date(2026, 1, 5)), date(2026, 1, 5))
        self.assertIsNone(normalize_date("  "))

    def test_dates_reject_invalid_values(self):
        for value in ("2026-13-01", "2026-02-30", "01/05/2026", "下周一"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
                normalize_date(value)

    def test_tokens_keep_preset_order_then_custom(self):
        self.assertEqual(join_tokens("自定义+B，A、A", ("A", "B")), "A、B、自定义")
        self.assertIsNone(join_tokens(" , "))

    def test_known_options_reject_unknown(self):
        self.assertEqual(join_known_options("B,A", ("A", "B"), "bad"), "A,B")
        with self.assertRaisesRegex(ValueError, "bad"):
            join_known_options("A,C", ("A", "B"), "bad")

    def test_choice_uses_default_or_allows_blank(self):
        self.assertEqual(normalize_choice("", ("x", "y"), "状态", default="x"), "x")
        self.assertIsNone(normalize_choice(" ", ("x",), "结果", nullable=True))
        with self.assertRaisesRegex(ValueError, "状态不在允许的选项中"):
            normalize_choice("z", ("x",), "状态")

    def test_target_codes_split_and_upper(self):
        self.assertEqual(normalize_target_codes("a1，b2、c3", upper=True), ["A1", "B2", "C3"])
        with self.assertRaisesRegex(ValueError, "数组"):
            normalize_target_codes(12)


class DateColumnTests(DbTestCase):
    tables = (DiscoveryWorkbench,)

    def _row(self, discovery_id: str, **fields) -> DiscoveryWorkbench:
        row = DiscoveryWorkbench(discovery_id=discovery_id, **fields)
        self.db.add(row)
        return row

    def _ids(self, *where):
        stmt = select(DiscoveryWorkbench.discovery_id).where(*where).order_by(DiscoveryWorkbench.discovery_id)
        return list(self.db.scalars(stmt))

    def test_assignment_normalizes_and_round_trips(self):
        row = self._row("D1", harvest_date="2026/1/5", boost_date="")
        self.assertEqual(row.harvest_date, "2026-01-05")
        self.assertIsNone(row.boost_date)
        self.db.commit()
        self.db.expire_all()
        self.assertEqual(self.db.get(DiscoveryWorkbench, row.id).harvest_date, "2026-01-05")

    def test_assignment_rejects_invalid_date(self):
        row = self._row("D1")
        with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
            row.harvest_date = "2026-02-30"

    def test_string_comparisons_and_blank_checks(self):
        self._row("D1", harvest_date="2026-01-05")
        self._row("D2", harvest_date="2026-03-01")
        self._row("D3")
        self.db.commit()
        self.assertEqual(self._ids(DiscoveryWorkbench.harvest_date >= "2026-02-01"), ["D2"])
        self.assertEqual(self._ids(DiscoveryWorkbench.harvest_date.like("2026-01%")), ["D1"])
        self.assertEqual(self._ids(date_present(DiscoveryWorkbench.harvest_date)), ["D1", "D2"])
        self.assertEqual(self._ids(date_blank(DiscoveryWorkbench.harvest_date)), ["D3"])
        self.assertIsInstance(DateString().coerce_compared_value("eq", ""), String)

    def test_bind_rejects_invalid_value_written_without_orm(self):
        with self.assertRaises(StatementError) as ctx:
            self.db.execute(DiscoveryWorkbench.__table__.insert().values(discovery_id="D9", harvest_date="bad"))
        self.db.rollback()
        self.assertIn("YYYY-MM-DD", str(_validation_error(ctx.exception)))
        self.assertEqual(self.db.execute(text("select count(*) from discovery_workbench")).scalar(), 0)


class HeaderFilterTests(DbTestCase):
    tables = (DiscoveryWorkbench,)

    def _ids(self, clauses):
        stmt = select(DiscoveryWorkbench.discovery_id).where(*clauses).order_by(DiscoveryWorkbench.discovery_id)
        return list(self.db.scalars(stmt))

    def test_date_condition_accepts_common_writing_and_blank_ops(self):
        self.db.add_all([DiscoveryWorkbench(discovery_id="D1", harvest_date="2026-01-05"), DiscoveryWorkbench(discovery_id="D2")])
        self.db.commit()
        columns = {"harvest_date": HeaderColumn(DiscoveryWorkbench.harvest_date, "date")}

        def ids(condition):
            return self._ids(header_filter_clauses(self.db, columns, [{"field": "harvest_date", "condition": condition}]))

        self.assertEqual(ids({"op": "gte", "value": "2026/1/1"}), ["D1"])
        self.assertEqual(ids({"op": "blank"}), ["D2"])
        self.assertEqual(ids({"op": "not_blank"}), ["D1"])
        self.assertEqual(ids({"op": "gte", "value": ""}), ["D1", "D2"])
        with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
            ids({"op": "gte", "value": "2026-02-30"})
        with self.assertRaisesRegex(ValueError, "不支持按"):
            header_filter_clauses(self.db, columns, [{"field": "remark", "values": ["x"]}])

    def test_csv_token_matches_whole_tokens_and_escapes_wildcards(self):
        for discovery_id, strain in (("D1", "Balb/c、C57"), ("D2", "C57BL"), ("D3", "A_B"), ("D4", "AxB")):
            self.db.add(DiscoveryWorkbench(discovery_id=discovery_id, mouse_strain=strain))
        self.db.commit()
        self.assertEqual(self._ids([csv_token_clause(DiscoveryWorkbench.mouse_strain, "C57")]), ["D1"])
        self.assertEqual(self._ids([csv_token_clause(DiscoveryWorkbench.mouse_strain, "A_B")]), ["D3"])

    def test_header_columns_cover_plain_fields_except_sort(self):
        explicit = HeaderColumn(DiscoveryWorkbench.status, order=("规划中",))
        columns = header_columns(FIELDS, status=explicit)
        self.assertEqual(columns["remark"].kind, "text")
        self.assertEqual(columns["harvest_date"].kind, "date")
        self.assertEqual(columns["mouse_count"].kind, "number")
        self.assertIs(columns["status"], explicit)
        self.assertNotIn("sort_order", columns)
        self.assertNotIn("target_codes", columns)


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

    def test_text_field_trims_and_checks_length(self):
        self.assertEqual(clean_field(FIELDS["remark"], "  甲\n乙  ", keep_breaks=True), "甲\n乙")
        self.assertIsNone(clean_field(FIELDS["remark"], "   "))
        with self.assertRaisesRegex(ValueError, "免疫用抗原不能超过 1000 个字符"):
            clean_field(FIELDS["immune_antigen"], "A" * 1001)

    def test_date_field_accepts_common_writing_and_names_the_column_on_error(self):
        self.assertEqual(clean_field(FIELDS["harvest_date"], "2026/1/5"), date(2026, 1, 5))
        with self.assertRaisesRegex(ValueError, "剖鼠取细胞日格式不正确，应为 YYYY-MM-DD：2026-13-01"):
            clean_field(FIELDS["harvest_date"], "2026-13-01")

    def test_int_field_accepts_only_non_negative_integers(self):
        self.assertEqual(clean_field(FIELDS["mouse_count"], " 5 "), 5)
        self.assertIsNone(clean_field(FIELDS["mouse_count"], ""))
        for bad in (-1, "1.5", 2.5, True, "五"):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "小鼠只数必须是非负整数"):
                clean_field(FIELDS["mouse_count"], bad)

    def test_json_field_is_left_to_the_module(self):
        with self.assertRaises(TypeError):
            clean_field(FIELDS["target_codes"], ["20R001"])


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


class InsertWithRetryTests(DbTestCase):
    tables = (SerumImmProject, SerumImmWorkbench, Target)

    def test_conflict_retries_and_keeps_earlier_changes(self):
        self.db.add(SerumImmProject(project_code="P1", experiment_id="P101", project_status="规划中"))
        self.db.commit()
        self.db.add(SerumImmProject(project_code="P9", experiment_id="P901", project_status="规划中"))
        self.db.flush()

        project = SerumImmProject(project_code="P1", project_status="规划中")

        def assign(attempt):
            project.experiment_id = "P101" if attempt == 0 else serum.generate_next_id(self.db, "P1")

        insert_with_retry(self.db, project, assign)
        self.db.commit()
        self.assertEqual(project.experiment_id, "P102")
        self.assertEqual(
            sorted(self.db.scalars(select(SerumImmProject.experiment_id)).all()),
            ["P101", "P102", "P901"],
        )

    def test_gives_up_with_business_message(self):
        self.db.add(SerumImmProject(project_code="P1", experiment_id="P101"))
        self.db.commit()
        project = SerumImmProject(project_code="P1")

        def assign(_attempt):
            project.experiment_id = "P101"

        with self.assertRaisesRegex(ValueError, "撞号"):
            insert_with_retry(self.db, project, assign, attempts=2, conflict_message="撞号")

    def test_other_constraint_errors_are_not_retried(self):
        attempts = []
        with self.assertRaises(IntegrityError):
            insert_with_retry(self.db, Target(snum=None), attempts.append)
        self.assertEqual(attempts, [0])


class LockQueueTests(DbTestCase):
    tables = (DiscoverySynthesisOrder,)

    def test_renews_snapshot_only_before_any_write(self):
        row = DiscoverySynthesisOrder(synthesis_order_id="S1", target_name="T1")
        self.db.add(row)
        self.db.commit()
        commits = []
        event.listen(self.db, "after_commit", commits.append)

        # 只读过（如登录校验）就先提交，加锁后的读取不再用等锁前的快照
        self.db.get(DiscoverySynthesisOrder, row.id)
        lock_queue(self.db, DiscoverySynthesisOrder)
        self.assertEqual(len(commits), 1)

        # 已有未提交的改动、flush 过或批量 UPDATE 过都不能提前提交
        self.db.get(DiscoverySynthesisOrder, row.id).remark = "未提交"
        lock_queue(self.db, DiscoverySynthesisOrder)
        self.db.flush()
        lock_queue(self.db, DiscoverySynthesisOrder)
        self.db.rollback()
        self.db.execute(update(DiscoverySynthesisOrder).values(remark="批量"))
        lock_queue(self.db, DiscoverySynthesisOrder)
        self.db.rollback()
        self.assertEqual(len(commits), 1)
        self.assertIsNone(self.db.get(DiscoverySynthesisOrder, row.id).remark)
