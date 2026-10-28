from datetime import datetime
from unittest import TestCase

from models.target import Target
from modules.system import target_sync
from utils.target_structure import (
    match_structural_properties_by_keyword,
    parse_target_structure,
    to_serum_target_type,
)


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

    def test_preserves_local_enriched_structure_when_pm_source_is_empty(self):
        existing = _target(
            type=1,
            status=2,
            official_full_name="CD3 epsilon subunit",
            human_gene_official_name="CD3E",
            human_ncbi_gene_id="916",
            mouse_gene_official_name="Cd3e",
            mouse_ncbi_gene_id="12501",
            structural_properties="Single-pass transmembrane protein Type I",
            structure_feature="1",
        )
        db = _FakeDb([existing])
        source_db = _FakeSourceDb([_row(structural_properties=None, structure_feature="NA")])

        result = target_sync.sync_targets(db, source_db)

        self.assertEqual(result["unchanged"], 1)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(
            existing.structural_properties,
            "Single-pass transmembrane protein Type I",
        )
        self.assertEqual(existing.structure_feature, "1")

    def test_pm_non_empty_structure_overrides_local_value_and_clears_conflicting_tm_count(self):
        existing = _target(
            structural_properties="Single-pass transmembrane protein Type I",
            structure_feature="1",
        )
        db = _FakeDb([existing])
        source_db = _FakeSourceDb([_row(structural_properties="Secreted", structure_feature=None)])

        result = target_sync.sync_targets(db, source_db)

        self.assertEqual(result["updated"], 1)
        self.assertEqual(existing.structural_properties, "Secreted")
        self.assertIsNone(existing.structure_feature)

    def test_new_dog_prefix_target_reuses_same_library_target_structure(self):
        pd1 = _target(
            external_id=10,
            snum="20R007",
            name="PD-1",
            structural_properties="Single-pass transmembrane protein Type I",
            structure_feature="1",
        )
        db = _FakeDb([pd1])
        source_db = _FakeSourceDb(
            [
                _row(
                    external_id=10,
                    snum="20R007",
                    name="PD-1",
                    structural_properties="Single-pass transmembrane protein Type I",
                    structure_feature="1",
                ),
                _row(
                    external_id=20,
                    snum="26R184",
                    name="dogPD-1",
                    human_gene_official_name=None,
                    human_ncbi_gene_id=None,
                    mouse_gene_official_name=None,
                    mouse_ncbi_gene_id=None,
                    structural_properties=None,
                    structure_feature=None,
                ),
            ]
        )

        result = target_sync.sync_targets(db, source_db)

        self.assertEqual(result["created"], 1)
        self.assertEqual(result["uniprot_enriched"], 1)
        self.assertEqual(
            db.created[0].structural_properties,
            "Single-pass transmembrane protein Type I",
        )
        self.assertEqual(db.created[0].structure_feature, "1")

    def test_shared_structure_mapping_and_keyword_lookup(self):
        parsed = parse_target_structure("Multi-pass transmembrane protein", "7")
        self.assertEqual(parsed["label"], "多次穿膜")
        self.assertEqual(parsed["full_label"], "多次穿膜（7次跨膜）")
        self.assertEqual(parsed["serum_type"], "多穿")
        self.assertEqual(to_serum_target_type("Single-pass transmembrane protein Type II", "1"), "II型")
        self.assertEqual(
            match_structural_properties_by_keyword("I型"),
            ["Single-pass transmembrane protein Type I"],
        )
        self.assertIn("Secreted", match_structural_properties_by_keyword("分泌"))
