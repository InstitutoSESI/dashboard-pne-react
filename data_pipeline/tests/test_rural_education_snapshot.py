from __future__ import annotations

import sys
import unittest
from pathlib import Path


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.municipality_registry import load_municipality_registry
from src.rural_education_snapshot import (
    load_rural_education_snapshot,
    resolve_rural_education_snapshot_dir,
    snapshot_digest,
)
from src.state_config import load_state_config


class RuralEducationSnapshotTest(unittest.TestCase):
    def test_preserved_rs_snapshot_is_valid_in_state_directory(self):
        state = load_state_config("RS")
        registry = load_municipality_registry(state)
        directory = resolve_rural_education_snapshot_dir(state)

        loaded = load_rural_education_snapshot(
            state,
            registry,
            expected_years=(2023, 2024, 2025),
        )

        self.assertIsNotNone(loaded)
        population_rows, enrollment_rows, manifest = loaded
        self.assertEqual(directory.name, "rs")
        self.assertEqual(len(population_rows), 497)
        self.assertEqual(len(enrollment_rows), 497 * 3 * 5)
        self.assertEqual(manifest["snapshotSha256"], snapshot_digest(directory))

    def test_state_directories_are_isolated(self):
        rs = resolve_rural_education_snapshot_dir(load_state_config("RS"))
        al = resolve_rural_education_snapshot_dir(load_state_config("AL"))
        self.assertEqual(rs.parent, al.parent)
        self.assertEqual(rs.name, "rs")
        self.assertEqual(al.name, "al")
        self.assertNotEqual(rs, al)

    def test_synced_al_snapshot_covers_the_registry_and_state_query(self):
        state = load_state_config("AL")
        registry = load_municipality_registry(state)
        directory = resolve_rural_education_snapshot_dir(state)

        loaded = load_rural_education_snapshot(
            state,
            registry,
            expected_years=(2023, 2024, 2025),
        )

        self.assertIsNotNone(loaded)
        population_rows, enrollment_rows, manifest = loaded
        self.assertEqual(len(population_rows), 102)
        self.assertEqual(len(enrollment_rows), 102 * 3 * 5)
        self.assertEqual(manifest["population"]["available"], 102)
        self.assertEqual(manifest["snapshotSha256"], snapshot_digest(directory))
        sources = manifest["population"]["sources"]
        self.assertIn("N3[27]", sources["ruralGroups"]["queryUrl"])
        self.assertIn("N3[27]", sources["exactAgeWeights"]["queryUrl"])


if __name__ == "__main__":
    unittest.main()
