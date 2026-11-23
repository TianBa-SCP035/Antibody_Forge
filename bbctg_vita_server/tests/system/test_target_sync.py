"""靶点主数据外部同步与结构特性映射规则。"""

import unittest

from sqlalchemy import select

from models.target import Target
from modules.system import target_sync
from support import DbTestCase, FakeSourceDb
from utils.target_structure import (
    match_structural_properties_by_keyword,
    parse_target_structure,
    to_serum_target_type,
)


class TargetSyncTests(DbTestCase):
    tables = (Target,)

    def _row(self, **overrides) -> dict:
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

    def _target(self, **overrides) -> Target:
        values = {
            "external_id": 1,
            "snum": "25R001",
            "name": "CD3E",
            "is_active": True,
        }
        values.update(overrides)
        return Target(**values)

    def _seed_targets(self, *targets: Target) -> None:
        self.db.add_all(targets)
        self.db.commit()

    def _all_targets(self) -> list[Target]:
        with self.Session() as db:
            return list(db.scalars(select(Target).order_by(Target.id)).all())

    def test_mixed_valid_and_invalid_rows_create_only_valid_target(self):
        source_db = FakeSourceDb(
            [
                self._row(),
                self._row(external_id=None, snum="BAD-1"),
                self._row(external_id=2, snum=""),
                self._row(external_id=3, snum="BAD-3", name=""),
            ]
        )

        result = target_sync.sync_targets(self.db, source_db)

        self.assertFalse(self.db.in_transaction())
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["valid"], 1)
        self.assertEqual(result["skipped"]["missing_external_id"], 1)
        self.assertEqual(result["skipped"]["missing_snum"], 1)
        self.assertEqual(result["skipped"]["missing_name"], 1)
        targets = self._all_targets()
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0].snum, "25R001")
        self.assertEqual(targets[0].human_gene_official_name, "CD3E")
        self.assertTrue(targets[0].is_active)

    def test_missing_local_target_is_deactivated_while_matched_target_updates(self):
        self._seed_targets(
            self._target(name="Old name", status=1),
            self._target(external_id=2, snum="25R002", name="MISSING"),
        )
        source_db = FakeSourceDb([self._row(name="CD3E", human_ncbi_gene_id=" 916 ")])

        result = target_sync.sync_targets(self.db, source_db)

        self.assertEqual(result["updated"], 1)
        self.assertEqual(result["deactivated"], 1)
        by_snum = {target.snum: target for target in self._all_targets()}
        self.assertEqual(by_snum["25R001"].name, "CD3E")
        self.assertEqual(by_snum["25R001"].human_ncbi_gene_id, "916")
        self.assertTrue(by_snum["25R001"].is_active)
        self.assertFalse(by_snum["25R002"].is_active)

    def test_inactive_target_returning_in_source_is_reactivated(self):
        self._seed_targets(self._target(is_active=False))

        result = target_sync.sync_targets(self.db, FakeSourceDb([self._row()]))

        self.assertEqual(result["reactivated"], 1)
        self.assertEqual(result["updated"], 1)
        targets = self._all_targets()
        self.assertTrue(targets[0].is_active)

    def test_recreated_source_row_with_new_external_id_rebinds_by_unique_snum(self):
        self._seed_targets(self._target(external_id=1, snum="25R001", is_active=False))

        result = target_sync.sync_targets(self.db, FakeSourceDb([self._row(external_id=99, snum="25R001")]))

        self.assertEqual(result["created"], 0)
        self.assertEqual(result["updated"], 1)
        self.assertEqual(result["reactivated"], 1)
        targets = self._all_targets()
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0].external_id, 99)
        self.assertEqual(targets[0].snum, "25R001")
        self.assertTrue(targets[0].is_active)

    def test_unchanged_external_id_with_new_snum_updates_snum(self):
        self._seed_targets(self._target(external_id=1, snum="OLD"))

        result = target_sync.sync_targets(self.db, FakeSourceDb([self._row(external_id=1, snum="NEW")]))

        self.assertEqual(result["created"], 0)
        self.assertEqual(result["updated"], 1)
        self.assertEqual(result["skipped"]["identity_conflict"], 0)
        targets = self._all_targets()
        self.assertEqual(targets[0].snum, "NEW")

    def test_conflicting_external_id_and_snum_across_two_rows_skips_update(self):
        self._seed_targets(
            self._target(external_id=1, snum="OLD"),
            self._target(external_id=2, snum="NEW"),
        )

        result = target_sync.sync_targets(self.db, FakeSourceDb([self._row(external_id=1, snum="NEW")]))

        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["skipped"]["identity_conflict"], 1)
        by_external_id = {target.external_id: target for target in self._all_targets()}
        self.assertEqual(by_external_id[1].snum, "OLD")
        self.assertEqual(by_external_id[2].snum, "NEW")

    def test_empty_source_raises_without_deactivating_local_targets(self):
        self._seed_targets(self._target())

        with self.assertRaises(ValueError):
            target_sync.sync_targets(self.db, FakeSourceDb([]))

        self.assertFalse(self.db.in_transaction())
        targets = self._all_targets()
        self.assertEqual(len(targets), 1)
        self.assertTrue(targets[0].is_active)

    def test_blank_pm_structure_preserves_local_enriched_values(self):
        self._seed_targets(
            self._target(
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
        )
        source_db = FakeSourceDb([self._row(structural_properties=None, structure_feature="NA")])

        result = target_sync.sync_targets(self.db, source_db)

        self.assertEqual(result["unchanged"], 1)
        self.assertEqual(result["updated"], 0)
        targets = self._all_targets()
        self.assertEqual(
            targets[0].structural_properties,
            "Single-pass transmembrane protein Type I",
        )
        self.assertEqual(targets[0].structure_feature, "1")

    def test_non_transmembrane_pm_structure_overrides_local_and_clears_tm_count(self):
        self._seed_targets(
            self._target(
                structural_properties="Single-pass transmembrane protein Type I",
                structure_feature="1",
            )
        )
        source_db = FakeSourceDb([self._row(structural_properties="Secreted", structure_feature=None)])

        result = target_sync.sync_targets(self.db, source_db)

        self.assertEqual(result["updated"], 1)
        targets = self._all_targets()
        self.assertEqual(targets[0].structural_properties, "Secreted")
        self.assertIsNone(targets[0].structure_feature)

    def test_new_species_prefixed_target_reuses_same_library_homolog_structure(self):
        self._seed_targets(
            self._target(
                external_id=10,
                snum="20R007",
                name="PD-1",
                structural_properties="Single-pass transmembrane protein Type I",
                structure_feature="1",
            )
        )
        source_db = FakeSourceDb(
            [
                self._row(
                    external_id=10,
                    snum="20R007",
                    name="PD-1",
                    structural_properties="Single-pass transmembrane protein Type I",
                    structure_feature="1",
                ),
                self._row(
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

        result = target_sync.sync_targets(self.db, source_db)

        self.assertEqual(result["created"], 1)
        self.assertEqual(result["uniprot_enriched"], 1)
        by_snum = {target.snum: target for target in self._all_targets()}
        self.assertEqual(
            by_snum["26R184"].structural_properties,
            "Single-pass transmembrane protein Type I",
        )
        self.assertEqual(by_snum["26R184"].structure_feature, "1")

    def test_dry_run_rolls_back_created_and_updated_targets(self):
        self._seed_targets(self._target(external_id=1, snum="25R001", name="Old name"))
        source_db = FakeSourceDb(
            [
                self._row(external_id=1, snum="25R001", name="CD3E"),
                self._row(external_id=2, snum="25R002", name="PD-1"),
            ]
        )

        result = target_sync.sync_targets(self.db, source_db, dry_run=True)

        self.assertFalse(self.db.in_transaction())
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["updated"], 1)
        targets = self._all_targets()
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0].name, "Old name")


class TargetStructureMappingTests(unittest.TestCase):
    def test_structure_properties_map_to_labels_serum_types_and_keywords(self):
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
