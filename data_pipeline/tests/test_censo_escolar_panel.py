import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pandas as pd


PIPELINE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PIPELINE_ROOT.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))
if str(PIPELINE_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT / "scripts"))

from src.censo_escolar_panel import (  # noqa: E402
    BENTO_GONCALVES_CODE,
    EXPECTED_PANEL_ROWS,
    INDICATOR_NAMES,
    MUNICIPAL_UNIVERSE_BY_YEAR,
    PANEL_COLUMNS,
    PINTO_BANDEIRA_CODE,
    REQUIRED_SOURCE_COLUMNS,
    ReconciliationContractError,
    build_panel,
    derive_indicators,
    load_historical_csv,
    normalize_source_chunk,
    read_panel,
    reconcile,
    validate_manifest,
    validate_panel,
    sha256_file,
)
from build_censo_escolar_panel import (  # noqa: E402
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PANEL_NAME,
    RECONCILIATION_FILE_NAMES,
    _run,
    main,
    promote_artifact_set,
    resolve_artifact_paths,
)


def source_row(**overrides):
    row = {
        "NU_ANO_CENSO": "2025",
        "SG_UF": "RS",
        "CO_MUNICIPIO": "4300001",
        "CO_ENTIDADE": "10000001",
        "TP_SITUACAO_FUNCIONAMENTO": "1",
        "QT_MAT_INF_PRE": "10",
        "QT_MAT_BAS_0_3": "20",
        "QT_MAT_BAS_4_5": "30",
        "QT_MAT_BAS_6_10": "40",
        "QT_MAT_BAS_11_14": "50",
        "QT_MAT_BAS_15_17": "60",
    }
    row.update(overrides)
    return row


def write_source(source_dir: Path, year: int, rows: list[dict]) -> None:
    frame = pd.DataFrame(rows)
    frame["NU_ANO_CENSO"] = str(year)
    frame.to_csv(
        source_dir / f"microdados_ed_basica_{year}.csv",
        sep=";",
        index=False,
        encoding="latin1",
    )


def synthetic_full_panel() -> pd.DataFrame:
    codes = [f"43{number:05d}" for number in range(1, 498)]
    rows = []
    for year in range(2014, 2026):
        for index, code in enumerate(codes, start=1):
            rows.append(
                {
                    "ano": year,
                    "codigo_municipio": code,
                    "mat_infantil_pre": index + year,
                    "mat_basico_0_3": index + 1,
                    "mat_basico_4_5": index + 2,
                    "mat_basico_6_10": index + 3,
                    "mat_basico_11_14": index + 4,
                    "mat_basico_15_17": index + 5,
                }
            )
    return pd.DataFrame(rows, columns=PANEL_COLUMNS)


class CensoEscolarPanelTests(unittest.TestCase):
    def test_selection_and_normalization_use_canonical_columns(self):
        chunk = pd.DataFrame(
            [
                source_row(
                    CO_MUNICIPIO="4300001.0",
                    CO_ENTIDADE="10000001.0",
                    SG_UF=" rs ",
                )
            ]
        )
        result = normalize_source_chunk(chunk, 2025)
        self.assertEqual(result.loc[0, "CO_MUNICIPIO"], "4300001")
        self.assertEqual(result.loc[0, "CO_ENTIDADE"], "10000001")
        self.assertEqual(result.loc[0, "SG_UF"], "RS")
        self.assertEqual(set(result.columns), set(REQUIRED_SOURCE_COLUMNS))

    def test_aggregation_by_municipality_keeps_all_operating_statuses(self):
        with tempfile.TemporaryDirectory() as temporary:
            source_dir = Path(temporary) / "source"
            output_dir = Path(temporary) / "output"
            source_dir.mkdir()
            write_source(
                source_dir,
                2025,
                [
                    source_row(CO_ENTIDADE="1", TP_SITUACAO_FUNCIONAMENTO="1"),
                    source_row(
                        CO_ENTIDADE="2",
                        TP_SITUACAO_FUNCIONAMENTO="2",
                        QT_MAT_BAS_0_3="5",
                    ),
                    source_row(
                        CO_MUNICIPIO="4300002",
                        CO_ENTIDADE="3",
                        TP_SITUACAO_FUNCIONAMENTO="3",
                    ),
                ],
            )
            panel, metadata = build_panel(
                source_dir,
                output_dir / "panel.csv.gz",
                years=[2025],
                chunk_size=2,
            )
            point = panel.loc[panel["codigo_municipio"].eq("4300001")].iloc[0]
            self.assertEqual(point["mat_basico_0_3"], 25)
            self.assertNotIn("qtd_entidades", panel.columns)
            self.assertEqual(metadata["panel"]["validation"]["status"], "warning")
            self.assertEqual(
                metadata["sources"][0]["included_situacao_funcionamento"],
                {"1": 1, "2": 1, "3": 1},
            )
            self.assertEqual(read_panel(output_dir / "panel.csv.gz").columns.tolist(), PANEL_COLUMNS)
            self.assertEqual(metadata["panel"]["rows"], len(panel))
            self.assertEqual(
                metadata["panel"]["size_bytes"],
                (output_dir / "panel.csv.gz").stat().st_size,
            )
            self.assertEqual(metadata["panel"]["sha256"], sha256_file(output_dir / "panel.csv.gz"))
            self.assertEqual(
                metadata["sources"][0]["entity_count_audit"]["panel_column"], None
            )

    def test_empty_value_audit_by_status_does_not_impute(self):
        with tempfile.TemporaryDirectory() as temporary:
            source_dir = Path(temporary) / "source"
            source_dir.mkdir()
            empty = {column: "" for column in [
                "QT_MAT_INF_PRE",
                "QT_MAT_BAS_0_3",
                "QT_MAT_BAS_4_5",
                "QT_MAT_BAS_6_10",
                "QT_MAT_BAS_11_14",
                "QT_MAT_BAS_15_17",
            ]}
            partial = {"QT_MAT_BAS_0_3": ""}
            write_source(
                source_dir,
                2025,
                [
                    source_row(CO_ENTIDADE="1", **empty),
                    source_row(CO_ENTIDADE="2", **partial),
                    source_row(CO_ENTIDADE="3"),
                ],
            )
            panel, metadata = build_panel(
                source_dir,
                Path(temporary) / "panel.csv.gz",
                years=[2025],
            )
            self.assertEqual(panel.iloc[0]["mat_basico_0_3"], 20)
            audit = metadata["sources"][0]["empty_value_audit_by_status"]["1"]
            self.assertEqual(audit["lines_six_empty"], 1)
            self.assertEqual(audit["lines_partial_empty"], 1)
            self.assertEqual(audit["lines_complete"], 1)

    def test_indicator_formulas_match_contract(self):
        panel = pd.DataFrame(
            [
                {
                    "ano": 2025,
                    "codigo_municipio": "4300001",
                    "mat_infantil_pre": 10,
                    "mat_basico_0_3": 20,
                    "mat_basico_4_5": 30,
                    "mat_basico_6_10": 40,
                    "mat_basico_11_14": 50,
                    "mat_basico_15_17": 60,
                }
            ]
        )
        result = derive_indicators(panel).iloc[0]
        self.assertEqual(
            [result[name] for name in INDICATOR_NAMES],
            [20, 10, 150, 60, 50, 180, 90],
        )

    def test_duplicate_entity_is_reported_but_not_deduplicated(self):
        with tempfile.TemporaryDirectory() as temporary:
            source_dir = Path(temporary) / "source"
            source_dir.mkdir()
            write_source(
                source_dir,
                2025,
                [
                    source_row(CO_ENTIDADE="1"),
                    source_row(CO_ENTIDADE="1", QT_MAT_BAS_0_3="5"),
                ],
            )
            panel, metadata = build_panel(
                source_dir,
                Path(temporary) / "panel.csv.gz",
                years=[2025],
                chunk_size=1,
            )
            self.assertEqual(panel.iloc[0]["mat_basico_0_3"], 25)
            self.assertEqual(metadata["sources"][0]["duplicate_entity_keys_count"], 1)
            self.assertEqual(metadata["sources"][0]["duplicate_entity_rows_excess_count"], 1)
            self.assertEqual(metadata["sources"][0]["conflicting_duplicate_entity_keys_count"], 1)

    def test_missing_columns_and_invalid_values_fail(self):
        with self.assertRaises(ValueError):
            normalize_source_chunk(
                pd.DataFrame([source_row()]).drop(columns=["QT_MAT_BAS_0_3"]),
                2025,
            )
        with self.assertRaises(ValueError):
            normalize_source_chunk(
                pd.DataFrame([source_row(QT_MAT_BAS_0_3="-1")]), 2025
            )
        with self.assertRaises(ValueError):
            normalize_source_chunk(
                pd.DataFrame([source_row(QT_MAT_BAS_0_3="not-a-number")]), 2025
            )

    def test_invalid_panel_code_and_duplicate_grain_fail(self):
        base = {
            "ano": 2025,
            "codigo_municipio": "4300001",
            "mat_infantil_pre": 1,
            "mat_basico_0_3": 1,
            "mat_basico_4_5": 1,
            "mat_basico_6_10": 1,
            "mat_basico_11_14": 1,
            "mat_basico_15_17": 1,
        }
        with self.assertRaises(ValueError):
            validate_panel(pd.DataFrame([{**base, "codigo_municipio": "43"}]))
        with self.assertRaises(ValueError):
            validate_panel(pd.DataFrame([base, base]))

    def test_variable_municipal_universe_and_pinto_bandeira_no_imputation(self):
        early_codes = [f"43{number:05d}" for number in range(1, 497)]
        rows = []
        for year, codes in [(2007, early_codes), (2013, early_codes + [PINTO_BANDEIRA_CODE])]:
            for code in codes:
                rows.append(
                    {
                        "ano": year,
                        "codigo_municipio": code,
                        **{column: 1 for column in PANEL_COLUMNS[2:]},
                    }
                )
        validation = validate_panel(pd.DataFrame(rows), expected_years=[2007, 2013])
        self.assertEqual(validation["status"], "ok")
        self.assertEqual(validation["expected_rows"], 496 + 497)
        self.assertEqual(validation["coverage_by_year"], {"2007": 496, "2013": 497})
        self.assertEqual(validation["structural_absences_by_year"]["2007"], [PINTO_BANDEIRA_CODE])
        self.assertEqual(validation["missing_municipalities_by_year"], {})
        self.assertEqual(MUNICIPAL_UNIVERSE_BY_YEAR[2007], 496)
        self.assertEqual(MUNICIPAL_UNIVERSE_BY_YEAR[2013], 497)
        self.assertNotEqual(BENTO_GONCALVES_CODE, PINTO_BANDEIRA_CODE)

    def test_manifest_consistency_and_portable_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            source_dir = Path(temporary) / "source"
            source_dir.mkdir()
            write_source(source_dir, 2025, [source_row()])
            panel_path = Path(temporary) / "panel.csv.gz"
            _panel, metadata = build_panel(source_dir, panel_path, years=[2025])
            self.assertFalse(Path(metadata["sources"][0]["path"]).is_absolute())
            self.assertNotIn("Users", metadata["sources"][0]["path"])
            self.assertEqual(validate_manifest(metadata, panel_path=panel_path)["panel_rows"], 1)

    def test_reconciliation_controlled_sample(self):
        panel = pd.DataFrame(
            [
                {
                    "ano": 2014,
                    "codigo_municipio": "4300001",
                    "mat_infantil_pre": 10,
                    "mat_basico_0_3": 20,
                    "mat_basico_4_5": 30,
                    "mat_basico_6_10": 40,
                    "mat_basico_11_14": 50,
                    "mat_basico_15_17": 60,
                }
            ]
        )
        history = derive_indicators(panel)
        with tempfile.TemporaryDirectory() as temporary:
            result = reconcile(
                panel,
                history,
                Path(temporary) / "audit",
                start_year=2014,
                end_year=2014,
                strict_contract=False,
            )
            self.assertEqual(result["exact_points"], 7)
            self.assertEqual(result["divergence_points"], 0)
            self.assertEqual(result["status"], "reconciled_non_strict")

    def test_official_reconciliation_exact_contract(self):
        panel = synthetic_full_panel()
        history = derive_indicators(panel)
        with tempfile.TemporaryDirectory() as temporary:
            result = reconcile(panel, history, Path(temporary) / "audit")
            self.assertEqual(result["status"], "reconciled")
            self.assertEqual(result["contract"]["expected_points"], 41748)
            self.assertEqual(result["compared_points"], 41748)
            self.assertEqual(result["exact_points"], 41748)

    def test_reconciliation_fails_for_common_omission(self):
        panel = synthetic_full_panel()
        history = derive_indicators(panel)
        keep = ~((panel["ano"] == 2014) & (panel["codigo_municipio"] == "4300001"))
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "audit"
            with self.assertRaises(ReconciliationContractError):
                reconcile(panel.loc[keep], history.loc[keep], output_dir)
            self.assertFalse(output_dir.exists())

    def test_reconciliation_fails_for_municipality_absent_in_one_origin(self):
        panel = synthetic_full_panel()
        history = derive_indicators(panel)
        keep = ~((history["ano"] == 2014) & (history["codigo_municipio"] == "4300001"))
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ReconciliationContractError):
                reconcile(panel, history.loc[keep], Path(temporary) / "audit")

    def test_partial_run_never_resolves_to_canonical_name(self):
        with self.assertRaises(ValueError):
            resolve_artifact_paths([2025], None, None, None)
        with self.assertRaises(ValueError):
            resolve_artifact_paths([2025], DEFAULT_OUTPUT_DIR, None, None)
        output_dir, _report_dir, name = resolve_artifact_paths(
            [2025], Path(tempfile.gettempdir()) / "censo-partial", None, None
        )
        self.assertNotEqual(name, DEFAULT_PANEL_NAME)
        self.assertIn("2025_2025", name)
        self.assertTrue(output_dir.name == "censo-partial")

    def test_cli_years_2025_does_not_overwrite_canonical_panel(self):
        canonical_manifest = DEFAULT_OUTPUT_DIR / "manifest.json"
        before = canonical_manifest.read_bytes() if canonical_manifest.exists() else None
        with patch.object(
            sys,
            "argv",
            ["build_censo_escolar_panel.py", "--years", "2025"],
        ):
            self.assertEqual(main(), 1)
        after = canonical_manifest.read_bytes() if canonical_manifest.exists() else None
        self.assertEqual(after, before)

    def test_promotion_rolls_back_when_second_destination_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old_panel = root / "panel"
            old_reports = root / "reports"
            old_panel.mkdir()
            old_reports.mkdir()
            (old_panel / "manifest.json").write_text("old-panel", encoding="utf-8")
            (old_reports / "audit_report.md").write_text("old-reports", encoding="utf-8")
            staged_root = root / "stage"
            staged_panel = staged_root / "panel"
            staged_reports = staged_root / "reports"
            staged_panel.mkdir(parents=True)
            staged_reports.mkdir(parents=True)
            (staged_panel / "manifest.json").write_text("new-panel", encoding="utf-8")
            (staged_reports / "audit_report.md").write_text("new-reports", encoding="utf-8")
            blocked_parent = root / "blocked-parent"
            blocked_parent.write_text("not-a-directory", encoding="utf-8")
            with self.assertRaises(Exception):
                promote_artifact_set(
                    staged_panel,
                    old_panel,
                    staged_reports,
                    blocked_parent / "reports",
                )
            self.assertEqual(
                (old_panel / "manifest.json").read_text(encoding="utf-8"), "old-panel"
            )
            self.assertEqual(
                (old_reports / "audit_report.md").read_text(encoding="utf-8"), "old-reports"
            )

    def test_skip_reconciliation_replaces_old_reports(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_dir = root / "source"
            output_dir = root / "output"
            report_dir = root / "output_reports"
            source_dir.mkdir()
            write_source(source_dir, 2025, [source_row()])
            report_dir.mkdir()
            for name in [*RECONCILIATION_FILE_NAMES]:
                (report_dir / name).write_text("old", encoding="utf-8")
            result = _run(
                Namespace(
                    source_dir=source_dir,
                    output_dir=output_dir,
                    report_dir=None,
                    panel_name=None,
                    chunksize=2,
                    historical_csv=None,
                    skip_reconciliation=True,
                    years=[2025],
                )
            )
            self.assertEqual(result["reconciliation"]["status"], "skipped")
            self.assertTrue((report_dir / "reconciliation_status.json").exists())
            self.assertFalse((report_dir / "reconciliation_summary.csv").exists())
            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["reconciliation"]["status"], "skipped")
            self.assertEqual(manifest["reports"]["reconciliation_files"], [])


if __name__ == "__main__":
    unittest.main()
