import unittest
from datetime import date

from sqlalchemy import String, select, text
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import sessionmaker

from core.errors import route_error
from models.discovery import DiscoveryWorkbench
from models.types import DateString, date_blank, date_present
from utils.header_filters import HeaderColumn, csv_token_clause
from utils.header_filters import _condition_clause as condition_clause
from utils.normalize import (
    join_known_options,
    join_tokens,
    normalize_choice,
    normalize_date,
    normalize_target_codes,
    parse_date,
)
from support import DbTestCase, memory_engine


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

    def test_choice_default_and_nullable(self):
        self.assertEqual(normalize_choice("", ("x", "y"), "状态", default="x"), "x")
        self.assertIsNone(normalize_choice(" ", ("x",), "结果", nullable=True))
        with self.assertRaisesRegex(ValueError, "状态不在允许的选项中"):
            normalize_choice("z", ("x",), "状态")

    def test_target_codes(self):
        self.assertEqual(normalize_target_codes("a1，b2、c3", upper=True), ["A1", "B2", "C3"])
        with self.assertRaisesRegex(ValueError, "数组"):
            normalize_target_codes(12)


class DateStringTests(DbTestCase):
    tables = (DiscoveryWorkbench,)

    def _row(self, discovery_id: str, **fields) -> DiscoveryWorkbench:
        row = DiscoveryWorkbench(discovery_id=discovery_id, **fields)
        self.db.add(row)
        return row

    def test_assignment_normalizes_and_round_trips(self):
        row = self._row("D1", harvest_date="2026/1/5", boost_date="")
        self.assertEqual(row.harvest_date, "2026-01-05")
        self.assertIsNone(row.boost_date)
        self.db.commit()
        self.db.expire_all()
        loaded = self.db.get(DiscoveryWorkbench, row.id)
        self.assertEqual(loaded.harvest_date, "2026-01-05")

    def test_assignment_rejects_invalid_date(self):
        row = self._row("D1")
        with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
            row.harvest_date = "2026-02-30"

    def test_string_comparisons_and_blank_checks(self):
        self._row("D1", harvest_date="2026-01-05")
        self._row("D2", harvest_date="2026-03-01")
        self._row("D3")
        self.db.commit()

        def ids(*where):
            stmt = select(DiscoveryWorkbench.discovery_id).where(*where).order_by(DiscoveryWorkbench.discovery_id)
            return list(self.db.scalars(stmt))

        self.assertEqual(ids(DiscoveryWorkbench.harvest_date >= "2026-02-01"), ["D2"])
        self.assertEqual(ids(DiscoveryWorkbench.harvest_date.like("2026-01%")), ["D1"])
        self.assertEqual(ids(date_present(DiscoveryWorkbench.harvest_date)), ["D1", "D2"])
        self.assertEqual(ids(date_blank(DiscoveryWorkbench.harvest_date)), ["D3"])

    def test_header_filter_on_date_column(self):
        self._row("D1", harvest_date="2026-01-05")
        self._row("D2")
        self.db.commit()
        spec = HeaderColumn(DiscoveryWorkbench.harvest_date, "date")

        def ids(condition):
            stmt = select(DiscoveryWorkbench.discovery_id).where(condition_clause(spec, condition))
            return sorted(self.db.scalars(stmt))

        self.assertEqual(ids({"op": "gte", "value": "2026/1/1"}), ["D1"])
        self.assertEqual(ids({"op": "blank"}), ["D2"])
        self.assertEqual(ids({"op": "not_blank"}), ["D1"])
        self.assertIsNone(condition_clause(spec, {"op": "gte", "value": ""}))
        with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
            condition_clause(spec, {"op": "gte", "value": "2026-02-30"})

    def test_legacy_varchar_value_is_returned_as_is(self):
        column_type = DateString()
        self.assertEqual(column_type.process_result_value(" 2026年1月 ", None), "2026年1月")
        self.assertEqual(column_type.process_result_value(date(2026, 1, 5), None), "2026-01-05")
        self.assertIsInstance(column_type.coerce_compared_value("eq", ""), String)

    def test_bind_rejects_invalid_value_written_without_orm(self):
        with self.assertRaises(StatementError) as ctx:
            self.db.execute(
                DiscoveryWorkbench.__table__.insert().values(discovery_id="D9", harvest_date="bad")
            )
        self.db.rollback()
        result = route_error(ctx.exception, self.db)
        self.assertNotEqual(result["code"], 0)
        self.assertIn("YYYY-MM-DD", result["message"])
        self.assertEqual(self.db.execute(text("select count(*) from discovery_workbench")).scalar(), 0)


class CsvTokenClauseTests(unittest.TestCase):
    def test_matches_whole_tokens_and_escapes_wildcards(self):
        engine = memory_engine(DiscoveryWorkbench)
        db = sessionmaker(bind=engine)()
        try:
            for discovery_id, strain in (("D1", "Balb/c、C57"), ("D2", "C57BL"), ("D3", "A_B"), ("D4", "AxB")):
                db.add(DiscoveryWorkbench(discovery_id=discovery_id, mouse_strain=strain))
            db.commit()

            def ids(token):
                clause = csv_token_clause(DiscoveryWorkbench.mouse_strain, token)
                return sorted(db.scalars(select(DiscoveryWorkbench.discovery_id).where(clause)))

            self.assertEqual(ids("C57"), ["D1"])
            self.assertEqual(ids("A_B"), ["D3"])
        finally:
            db.close()
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
