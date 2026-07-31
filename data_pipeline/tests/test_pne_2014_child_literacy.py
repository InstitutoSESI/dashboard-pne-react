import sys
import unittest
from pathlib import Path
from unittest.mock import patch


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src import data_loader  # noqa: E402
from src.pne import calculations_2014  # noqa: E402
from src.pne_2014_child_literacy import (  # noqa: E402
    NETWORK,
    SOURCE_ID,
    SOURCE_LABEL,
    load_dataframe,
    load_snapshot,
)
from src.pne_2014_state_reference import (  # noqa: E402
    BLOCKED_REASONS,
    build_alfabetizacao_state_reference_entry,
)


class ClosedCycleChildLiteracyTests(unittest.TestCase):
    def test_snapshot_has_canonical_grain_and_never_includes_2025(self):
        municipal, state, manifest = load_snapshot()
        self.assertEqual(len(municipal), 497 * 2)
        self.assertEqual(manifest["availableByYear"], {"2023": 456, "2024": 441})
        self.assertEqual(manifest["canonicalKey"], ["id_municipio", "ano", "rede"])
        keys = {
            (row["id_municipio"], row["ano"], row["rede"])
            for row in municipal
        }
        self.assertEqual(len(keys), len(municipal))
        self.assertEqual({row["ano"] for row in municipal}, {2023, 2024})
        self.assertTrue(
            all(
                len(row["id_municipio"]) == 7
                and row["id_municipio"].isdigit()
                for row in municipal
            )
        )
        self.assertEqual({row["rede"] for row in municipal}, {NETWORK})
        self.assertEqual({row["source_id"] for row in municipal}, {SOURCE_ID})
        self.assertEqual({row["ano"] for row in state}, {2023, 2024})

    def test_sao_leopoldo_uses_official_municipal_network_values(self):
        frame = load_dataframe()
        rows = frame[
            (frame["id_municipio"] == "4318705")
            & frame["taxa_alfabetizacao"].notna()
        ]
        self.assertEqual(
            dict(zip(rows["ano"], rows["taxa_alfabetizacao"])),
            {2023: 57.01, 2024: 37.2},
        )
        self.assertEqual(set(rows["rede"]), {"municipal"})
        self.assertEqual(set(rows["source_id"]), {SOURCE_ID})

    def test_absence_remains_null_and_not_zero(self):
        frame = load_dataframe()
        missing = frame[frame["taxa_alfabetizacao"].isna()]
        self.assertFalse(missing.empty)
        self.assertFalse((missing["taxa_alfabetizacao"] == 0).any())
        unavailable_ids = (
            frame.groupby("id_municipio")["taxa_alfabetizacao"]
            .apply(lambda values: values.isna().all())
        )
        municipality_id = unavailable_ids[unavailable_ids].index[0]
        municipality_name = frame[
            frame["id_municipio"] == municipality_id
        ].iloc[0]["municipio"]
        result = calculations_2014._calc_alfabetizacao(municipality_name)
        self.assertFalse(result["available"])
        self.assertIsNone(result["end_value"])
        self.assertIsNone(result["atingida"])

    def test_closed_cycle_result_is_observed_without_goal_conclusion(self):
        result = calculations_2014._calc_alfabetizacao("São Leopoldo")
        self.assertTrue(result["available"])
        self.assertEqual(result["end_year"], 2024)
        self.assertEqual(result["end_value"], 37.2)
        self.assertEqual(
            result["series"],
            [
                {"ano": 2023, "valor": 57.01},
                {"ano": 2024, "valor": 37.2},
            ],
        )
        self.assertFalse(result["tracks_goal"])
        self.assertIsNone(result["meta"])
        self.assertIsNone(result["distance"])
        self.assertIsNone(result["atingida"])
        self.assertEqual(result["source"], SOURCE_LABEL)
        self.assertEqual(result["network"], "municipal")
        self.assertNotIn(2025, [point["ano"] for point in result["series"]])

    def test_loader_is_cycle_specific_and_population_indicator_is_independent(self):
        closed = data_loader.load_taxa_alfabetizacao_data(
            cycle="pne_2014_2024"
        )
        self.assertEqual(set(closed["ano"]), {2023, 2024})
        with patch.object(data_loader, "load_dataset") as load_dataset:
            data_loader.load_taxa_alfabetizacao_data()
            load_dataset.assert_called_once_with("taxa_alfabetizacao_data")
        self.assertIsNot(
            calculations_2014._calc_alfabetizacao,
            calculations_2014._calc_alfabetizacao_pop_15_mais,
        )

    def test_state_reference_uses_official_state_result(self):
        metadata, indicator = build_alfabetizacao_state_reference_entry()
        self.assertNotIn("alfabetizacao", BLOCKED_REASONS)
        self.assertEqual(metadata["source"], SOURCE_LABEL)
        self.assertEqual(
            {
                point["year"]: point["value"]
                for point in indicator["series"]
            },
            {2023: 63.55, 2024: 44.23},
        )
        self.assertTrue(
            all(
                point["aggregation_method"]
                == "official_state_municipal_network_result"
                for point in indicator["series"]
            )
        )

    def test_sql_contract_rejects_public_network_average(self):
        metrics_sql = (
            DATA_PIPELINE_DIR / "queries" / "pne_2014_2024_metricas.sql"
        ).read_text(encoding="utf-8")
        section = metrics_sql.split("alfabetizacao AS (", 1)[1].split(
            "alfabetizacao_pop_15_mais AS (",
            1,
        )[0]
        self.assertIn("LOWER(TRIM(a.dependencia)) = 'municipal'", section)
        self.assertIn("a.ano <= 2024", section)
        self.assertNotIn("AVG(", section)
        self.assertNotIn("'publica'", section)


if __name__ == "__main__":
    unittest.main()
