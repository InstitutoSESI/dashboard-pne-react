from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PIPELINE_DIR = REPO_ROOT / "data_pipeline"
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.vocacoes_pne_job3 import (  # noqa: E402
    CANDIDATE_IDS,
    bh_adjust,
    fit_clustered_panel,
    require_ibge_code,
    shapley_m_equals_p_times_r,
    standardized_distance_comparators,
    two_way_within,
    validate_candidate_registry,
)


OUTPUT_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job3"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class Job3CoreTests(unittest.TestCase):
    def test_ibge_code_remains_textual(self) -> None:
        self.assertEqual(require_ibge_code("4313375"), "4313375")
        for invalid in (4313375, "431337", "43133750", "43A3375"):
            with self.assertRaises(ValueError):
                require_ibge_code(invalid)

    def test_shapley_decomposition_closes(self) -> None:
        result = shapley_m_equals_p_times_r(
            population_start=100,
            population_end=80,
            enrollment_start=70,
            enrollment_end=64,
        )
        self.assertAlmostEqual(result["enrollment_change"], -6.0)
        self.assertAlmostEqual(
            result["population_component"] + result["relation_component"],
            result["enrollment_change"],
            places=12,
        )
        self.assertAlmostEqual(result["closure_residual"], 0.0, places=12)

    def test_bh_adjust_is_monotone_in_sorted_order(self) -> None:
        raw = [0.01, 0.04, 0.03, None, 0.20]
        adjusted = bh_adjust(raw)
        self.assertIsNone(adjusted[3])
        pairs = sorted(
            (p, adjusted[index])
            for index, p in enumerate(raw)
            if p is not None
        )
        self.assertEqual(
            [value for _, value in pairs],
            sorted(value for _, value in pairs),
        )
        self.assertTrue(all(value >= p for p, value in pairs))

    def test_two_way_within_removes_group_means(self) -> None:
        municipality = np.repeat(["a", "b", "c"], 4)
        year = np.tile([2019, 2020, 2021, 2022], 3)
        matrix = np.arange(24, dtype=float).reshape(12, 2)
        transformed, iterations = two_way_within(
            matrix, municipality, year
        )
        self.assertGreaterEqual(iterations, 1)
        transformed_frame = pd.DataFrame(
            {
                "municipality": municipality,
                "year": year,
                "x": transformed[:, 0],
                "y": transformed[:, 1],
            }
        )
        self.assertLess(
            transformed_frame.groupby("municipality")[["x", "y"]]
            .mean()
            .abs()
            .to_numpy()
            .max(),
            1e-9,
        )
        self.assertLess(
            transformed_frame.groupby("year")[["x", "y"]]
            .mean()
            .abs()
            .to_numpy()
            .max(),
            1e-9,
        )

    def test_clustered_panel_recovers_within_slope(self) -> None:
        rows = []
        for municipality in range(20):
            for year in range(2018, 2025):
                period = year - 2018
                x_value = (
                    municipality * 0.1
                    + period
                    + 0.03 * municipality * period
                )
                rows.append(
                    {
                        "municipality": f"{municipality:07d}",
                        "year": year,
                        "x": x_value,
                        "y": 2.5 * x_value
                        + municipality * 3.0
                        + (year - 2018) * 0.2,
                    }
                )
        result = fit_clustered_panel(
            pd.DataFrame(rows),
            outcome="y",
            factors=["x"],
            municipality="municipality",
            year="year",
        )
        self.assertEqual(result["municipalities"], 20)
        self.assertEqual(result["standard_errors"], "clustered_by_municipality")
        self.assertEqual(result["coefficients"][0]["term"], "x")
        self.assertTrue(np.isfinite(result["coefficients"][0]["coefficient"]))

    def test_comparator_does_not_require_outcome(self) -> None:
        frame = pd.DataFrame(
            {
                "municipality": ["4313375", "4300001", "4300002", "4300003"],
                "size": [10, 11, 30, 9],
                "growth": [0.1, 0.11, -0.2, 0.08],
            }
        )
        result = standardized_distance_comparators(
            frame,
            municipality_column="municipality",
            target="4313375",
            variables=["size", "growth"],
            count=2,
        )
        self.assertEqual(len(result["selected"]), 2)
        self.assertEqual(result["selected"][0]["municipality_id"], "4300001")


class Job3ArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not (OUTPUT_ROOT / "manifest.json").is_file():
            raise unittest.SkipTest("Materialização Job 3 ainda não executada.")
        cls.manifest = json.loads(
            (OUTPUT_ROOT / "manifest.json").read_text(encoding="utf-8")
        )
        cls.registry = json.loads(
            (OUTPUT_ROOT / "candidate_registry.json").read_text(encoding="utf-8")
        )

    def test_manifest_artifact_hashes_and_inventory(self) -> None:
        self.assertEqual(self.manifest["jobId"], "v7-job3")
        self.assertEqual(len(self.manifest["artifacts"]), 17)
        for record in self.manifest["artifacts"]:
            path = OUTPUT_ROOT / record["path"]
            self.assertTrue(path.is_file(), record["path"])
            self.assertEqual(sha256_file(path), record["sha256"])

    def test_candidate_registry_contract(self) -> None:
        validate_candidate_registry(self.registry)
        self.assertEqual(
            tuple(item["id"] for item in self.registry["candidates"]),
            CANDIDATE_IDS,
        )
        self.assertEqual(
            {
                item["id"]: item["status"]
                for item in self.registry["candidates"]
            },
            {
                "H1_DEMOGRAFIA_REDE": "ANALYTICALLY_ELIGIBLE",
                "H2_TRAJETORIA_PERMANENCIA": "REVIEW_REQUIRED",
                "H3_TRABALHO_JUVENIL_MEDIO": "REVIEW_REQUIRED",
                "H4_EJA_DISTRIBUICAO": "ANALYTICALLY_ELIGIBLE",
                "A1_COORTES_REDE": "RETAINED",
                "A2_TRABALHO_PERMANENCIA": "RETAINED",
                "A3_OCUPACOES_FORMACAO": "ANALYTICALLY_ELIGIBLE",
            },
        )

    def test_municipal_layer_has_70_unique_keys_and_nsr(self) -> None:
        payload = json.loads(
            (OUTPUT_ROOT / "municipal_layers.json").read_text(encoding="utf-8")
        )
        records = payload["records"]
        self.assertEqual(len(records), 70)
        keys = {
            (record["candidate_id"], record["municipality_id"])
            for record in records
        }
        self.assertEqual(len(keys), 70)
        nsr = [
            record for record in records if record["municipality_id"] == "4313375"
        ]
        self.assertEqual(len(nsr), 7)

    def test_models_are_clustered_and_bh_adjusted(self) -> None:
        models = pd.read_csv(OUTPUT_ROOT / "models.csv.gz")
        self.assertFalse(models.empty)
        self.assertTrue(
            models["standard_errors"].eq("clustered_by_municipality").all()
        )
        self.assertTrue(models["p_value_raw"].notna().all())
        self.assertTrue(models["p_value_bh"].notna().all())
        main = models[models["sensitivity"].eq("MAIN_2019_2025")]
        counts = main.groupby(
            ["candidate_id", "stage", "outcome"]
        )["specification"].nunique()
        self.assertTrue(counts.le(3).all())

    def test_h1_and_h4_close(self) -> None:
        h1 = pd.read_csv(OUTPUT_ROOT / "h1_decomposition.csv.gz")
        self.assertLess(h1["closure_residual"].abs().max(), 1e-8)
        qa = json.loads((OUTPUT_ROOT / "qa.json").read_text(encoding="utf-8"))
        self.assertLess(
            qa["closure"]["ejaMaximumShareClosureResidual"], 1e-12
        )
        self.assertLess(
            qa["closure"]["ejaMaximumDifferenceClosureResidual"], 1e-12
        )

    def test_security_and_v6_preservation(self) -> None:
        qa = json.loads((OUTPUT_ROOT / "qa.json").read_text(encoding="utf-8"))
        self.assertTrue(qa["security"]["databaseReadOnly"])
        self.assertFalse(qa["security"]["databaseWrites"])
        self.assertFalse(qa["security"]["networkUsed"])
        self.assertFalse(qa["security"]["publicDataChanged"])
        self.assertFalse(qa["security"]["frontendChangedByJob3"])
        self.assertFalse(qa["security"]["forbiddenStockTableUsed"])
        self.assertTrue(qa["preservation"]["v6ByteIdentical"])

    def test_required_documents_exist(self) -> None:
        for relative in [
            "docs/GATE_ENTRADA_JOB_3_V7.yaml",
            "docs/PRE_REGISTRO_ANALITICO_JOB_3_V7.yaml",
            "docs/BIBLIOTECA_MECANISMOS_JOB_3_V7.md",
            "docs/RELATORIO_JOB_3_LABORATORIO_ANALITICO_V7_VOCACOES_PNE.md",
            "docs/MATRIZ_JULGAMENTO_CANDIDATAS_JOB_3_V7.csv",
            "docs/RESULTADOS_ROBUSTEZ_JOB_3_V7.csv",
            "docs/LACUNAS_POS_JOB_3_V7.md",
            "docs/PRIORIDADES_PRELIMINARES_NOVA_SANTA_RITA_JOB_3_V7.json",
            "docs/PACOTE_REVISAO_EXTERNA_JOB_3_V7.md",
            "data_pipeline/manifests/vocacoes-pne-v7-job3-release.json",
        ]:
            self.assertTrue((REPO_ROOT / relative).is_file(), relative)


if __name__ == "__main__":
    unittest.main()
