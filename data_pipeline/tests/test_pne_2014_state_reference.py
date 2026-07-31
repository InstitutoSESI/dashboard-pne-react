import sys
import unittest
from pathlib import Path

import pandas as pd


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.pne_2014_state_reference import (  # noqa: E402
    BLOCKED_REASONS,
    CENSUS_CONFIGS,
    METHODOLOGY_VERSION,
    RATIO_CONFIGS,
    UNAVAILABLE_REASONS,
    build_registry,
)
from src.pne_state_reference import (  # noqa: E402
    _build_medio_tecnico_participacao_records,
)


class ClosedCycleStateReferenceTests(unittest.TestCase):
    def test_registry_exposes_only_raw_compatible_indicators(self):
        registry = build_registry()
        enabled = set(RATIO_CONFIGS) | set(CENSUS_CONFIGS) | {
            "escolas_integral",
            "medio_tecnico_participacao_publica",
        }

        self.assertEqual(METHODOLOGY_VERSION, "pne2014-rs-reference-v1")
        self.assertEqual(len(registry), 24)
        self.assertEqual(
            set(registry) - enabled - {"alfabetizacao"},
            set(BLOCKED_REASONS),
        )
        self.assertEqual(len(BLOCKED_REASONS), 11)
        self.assertEqual(
            registry["alfabetizacao"]["source_type"],
            "official_state_published_percentage",
        )
        self.assertEqual(
            set(UNAVAILABLE_REASONS),
            {
                "ensino_fundamental_ou_completo_pop_6_14",
                "ensino_medio_ou_basica_completa_pop_15_17",
            },
        )
        for indicator_id in BLOCKED_REASONS:
            self.assertEqual(registry[indicator_id]["comparison_status"], "methodology_pending")
            self.assertIn("Bloqueado", registry[indicator_id]["notes"])

    def test_closed_cycle_ept_uses_2013_state_base(self):
        frame = pd.DataFrame(
            [
                {
                    "ano": 2013,
                    "municipio": "A",
                    "mat_ept_nivel_medio_total": 100,
                    "mat_ept_nivel_medio_publica": 40,
                    "mat_ept_nivel_medio_privada": 60,
                },
                {
                    "ano": 2013,
                    "municipio": "B",
                    "mat_ept_nivel_medio_total": 100,
                    "mat_ept_nivel_medio_publica": 50,
                    "mat_ept_nivel_medio_privada": 50,
                },
                {
                    "ano": 2014,
                    "municipio": "A",
                    "mat_ept_nivel_medio_total": 110,
                    "mat_ept_nivel_medio_publica": 50,
                    "mat_ept_nivel_medio_privada": 60,
                },
                {
                    "ano": 2014,
                    "municipio": "B",
                    "mat_ept_nivel_medio_total": 120,
                    "mat_ept_nivel_medio_publica": 55,
                    "mat_ept_nivel_medio_privada": 65,
                },
            ]
        )

        record = _build_medio_tecnico_participacao_records(
            frame,
            municipalities_expected=2,
            reference_start_year=2013,
            reference_end_year=2024,
        )[1]

        self.assertEqual(record["year"], 2014)
        self.assertEqual(record["aggregation_method"], "state_aggregate_positive_expansions_from_2013")
        self.assertEqual(record["numerator"], 15)
        self.assertEqual(record["denominator"], 30)
        self.assertEqual(record["value"], 50)


if __name__ == "__main__":
    unittest.main()
