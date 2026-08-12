from datetime import datetime
from unittest import TestCase

from models.target import Target
from modules.system import target_sync


class _ScalarResult:
    def __init__(self, values):
        self._values = values

    def all(self):
        return self._values


class _MappingsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _ExecuteResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return _MappingsResult(self._rows)


class _FakeDb:
    def __init__(self, targets):
        self.targets = targets
        self.created = []
        self.committed = False
        self.rolled_back = False

    def scalars(self, _stmt):
        return _ScalarResult(self.targets)

    def add(self, target):
        self.created.append(target)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


class _FakeSourceDb:
    def __init__(self, rows):
        self.rows = rows

    def execute(self, _stmt):
        return _ExecuteResult(self.rows)


def _row(**overrides):
    row = {
        "external_id": 1,
        "snum": "25R001",
        "name": "CD3E",
        "type": 1,
        "status": 2,
        "official_full_name": "CD3 epsilon subunit",
        "human_gene_official_name": "CD3E",
        "human_ncbi_gene_id": "916",
        "mouse_gene_official_name": "Cd3e",
        "mouse_ncbi_gene_id": "12501",
    }
    row.update(overrides)
    return row


def _target(**overrides):
    values = {
        "external_id": 1,
        "snum": "25R001",
        "name": "CD3E",
        "is_active": True,
        "synced_at": datetime(2026, 1, 1),
    }
    values.update(overrides)
    return Target(**values)


class TargetSyncTest(TestCase):
    def test_creates_valid_target_and_skips_invalid_rows(self):
        db = _FakeDb([])
        source_db = _FakeSourceDb(
            [
                _row(),
                _row(external_id=None, snum="BAD-1"),
                _row(external_id=2, snum=""),
                _row(external_id=3, snum="BAD-3", name=""),
            ]
        )

        result = target_sync.sync_targets(db, source_db)

        self.assertEqual(result["created"], 1)
        self.assertEqual(result["valid"], 1)
        self.assertEqual(result["skipped"]["missing_external_id"], 1)
        self.assertEqual(result["skipped"]["missing_snum"], 1)
        self.assertEqual(result["skipped"]["missing_name"], 1)
        self.assertEqual(db.created[0].human_gene_official_name, "CD3E")
        self.assertTrue(db.committed)

    def test_updates_existing_target_and_deactivates_missing_target(self):
        existing = _target(name="Old name", status=1)
        missing = _target(external_id=2, snum="25R002", name="MISSING")
        db = _FakeDb([existing, missing])
        source_db = _FakeSourceDb([_row(name="CD3E", human_ncbi_gene_id=" 916 ")])

        result = target_sync.sync_targets(db, source_db)

        self.assertEqual(result["updated"], 1)
        self.assertEqual(result["deactivated"], 1)
        self.assertEqual(existing.name, "CD3E")
        self.assertEqual(existing.human_ncbi_gene_id, "916")
        self.assertFalse(missing.is_active)

    def test_reactivates_returned_target(self):
        existing = _target(is_active=False)
        db = _FakeDb([existing])

        result = target_sync.sync_targets(db, _FakeSourceDb([_row()]))

        self.assertEqual(result["reactivated"], 1)
        self.assertEqual(result["updated"], 1)
        self.assertTrue(existing.is_active)

    def test_rebinds_recreated_source_row_by_unique_snum(self):
        existing = _target(external_id=1, is_active=False)
        db = _FakeDb([existing])

        result = target_sync.sync_targets(db, _FakeSourceDb([_row(external_id=99)]))

        self.assertEqual(result["created"], 0)
        self.assertEqual(result["updated"], 1)
        self.assertEqual(result["reactivated"], 1)
        self.assertEqual(existing.external_id, 99)
        self.assertTrue(existing.is_active)

    def test_updates_snum_when_source_row_identity_is_unchanged(self):
        existing = _target(external_id=1, snum="OLD")
        db = _FakeDb([existing])

        result = target_sync.sync_targets(db, _FakeSourceDb([_row(external_id=1, snum="NEW")]))

        self.assertEqual(result["created"], 0)
        self.assertEqual(result["updated"], 1)
        self.assertEqual(result["skipped"]["identity_conflict"], 0)
        self.assertEqual(existing.snum, "NEW")

    def test_skips_update_when_external_id_and_snum_point_to_different_rows(self):
        by_external_id = _target(external_id=1, snum="OLD")
        by_snum = _target(external_id=2, snum="NEW")
        db = _FakeDb([by_external_id, by_snum])

        result = target_sync.sync_targets(db, _FakeSourceDb([_row(external_id=1, snum="NEW")]))

        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["skipped"]["identity_conflict"], 1)
        self.assertEqual(by_external_id.snum, "OLD")

    def test_rejects_empty_source_without_deactivating_local_data(self):
        existing = _target()
        db = _FakeDb([existing])

        with self.assertRaises(ValueError):
            target_sync.sync_targets(db, _FakeSourceDb([]))

        self.assertTrue(existing.is_active)
        self.assertFalse(db.committed)
