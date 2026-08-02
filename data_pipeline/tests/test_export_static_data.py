import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.pne import indicator_details
from src import data_loader
from src.pipeline_profiling import ProfileSession, activate_profile_session

SPEC = importlib.util.spec_from_file_location(
    "export_static_data", DATA_PIPELINE_DIR / "scripts" / "export_static_data.py"
)
exporter = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(exporter)


def result(value):
    return {
        "available": True,
        "start_year": 2024,
        "end_year": 2025,
        "start_value": value - 1,
        "end_value": value,
        "progress_delta": 1,
        "distance": 0,
        "atingida": True,
        "tracks_goal": True,
        "value_mode": "percent",
    }


class FakeShared:
    def _tracks_goal(self, item, result):
        return result.get("tracks_goal", True)

    def _format_metric_value(self, item, value):
        return str(value)

    def _format_metric_distance(self, item, value):
        return str(value)

    def _variation_text(self, result, item):
        return "1"

    def _status_theme(self, result):
        return {"text": "Meta atingida"}

    def _interpretation(self, item, result):
        return "ok"

    def _value_mode(self, item):
        return "percent"

    def _has_time_comparison(self, result):
        return True


class FakeCycle:
    CATEGORY_ORDER = ["categoria"]
    INDICADORES = {
        "categoria": {
            "label": "Categoria",
            "accent": "#000",
            "items": [
                {"key": "indicador_a", "label": "A"},
                {"key": "indicador_b", "label": "B"},
            ],
        }
    }
    calls = 0

    @classmethod
    def _calculate_results(cls, municipio):
        cls.calls += 1
        return {"indicador_a": result(10), "indicador_b": result(20)}

    @classmethod
    def _calculate_results_for_indicators(cls, municipio, indicator_keys):
        cls.calls += 1
        return {
            key: value
            for key, value in {"indicador_a": result(10), "indicador_b": result(20)}.items()
            if key in indicator_keys
        }


class ExportStaticDataTests(unittest.TestCase):
    def setUp(self):
        FakeCycle.calls = 0
        self.shared = FakeShared()

    def test_results_are_reused_when_results_and_rankings_are_exported(self):
        calculate_results = Mock(
            return_value={"indicador_a": result(10), "indicador_b": result(20)}
        )
        cycle = SimpleNamespace(
            CATEGORY_ORDER=FakeCycle.CATEGORY_ORDER,
            INDICADORES=FakeCycle.INDICADORES,
            _calculate_results=calculate_results,
        )
        cache = exporter.ResultsCache()
        errors = []
        exporter._export_cycle_results(
            cycle_key="pne_2026_2036",
            cycle_module=cycle,
            municipios=["Teste"],
            shared=self.shared,
            errors=errors,
            results_cache=cache,
        )
        exporter._export_cycle_rankings(
            cycle_key="pne_2026_2036",
            cycle_module=cycle,
            municipios=["Teste"],
            shared=self.shared,
            errors=errors,
            results_cache=cache,
        )

        calculate_results.assert_called_once_with("Teste")
        self.assertEqual(errors, [])

    def test_targeted_result_matches_full_result_semantically(self):
        full = exporter._export_cycle_results(
            cycle_key="pne_2026_2036",
            cycle_module=FakeCycle,
            municipios=["Teste"],
            shared=self.shared,
            errors=[],
            results_cache=exporter.ResultsCache(),
        )
        targeted = exporter._export_cycle_results(
            cycle_key="pne_2026_2036",
            cycle_module=FakeCycle,
            municipios=["Teste"],
            shared=self.shared,
            errors=[],
            results_cache=exporter.ResultsCache(),
            indicator_keys=("indicador_a",),
        )

        full_result = full["municipios"]["Teste"]["results"]["indicador_a"]
        targeted_result = targeted["municipios"]["Teste"]["results"]["indicador_a"]
        self.assertEqual(targeted_result, full_result)
        self.assertEqual(set(targeted["municipios"]["Teste"]["results"]), {"indicador_a"})
        self.assertEqual(
            set(targeted),
            {
                "generated_at",
                "cycle",
                "total_municipios",
                "municipios_exportados",
                "municipios",
            },
        )

    def test_warning_is_serialized_by_the_ranking_path(self):
        warned = result(120)
        warned["display"] = {"warning": "valor bruto acima de 100%"}
        errors = []
        payload = exporter._build_rankings_payload_for_municipio(
            cycle_key="pne_2026_2036",
            cycle_module=FakeCycle,
            municipio="Teste",
            results={"indicador_a": warned},
            shared=self.shared,
            errors=errors,
        )

        rows = payload["categories"]["categoria"]["top_avancos"]
        self.assertEqual(rows[0]["display"]["warning"], "valor bruto acima de 100%")
        self.assertEqual(errors, [])

    def test_targeted_validation_rejects_result_error_objects(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "export"
            path = output_dir / "pne_2026_2036" / "indicadores_por_municipio.json"
            exporter._write_json(
                path,
                {
                    "municipios": {
                        "Teste": {
                            "results": {"indicador_a": {"error": "falha controlada"}}
                        }
                    }
                },
            )

            problems = exporter._validate_targeted_export(
                export_dir=output_dir,
                cycle_indicators={"pne_2026_2036": ("indicador_a",)},
                municipios=["Teste"],
            )

        self.assertEqual(len(problems), 1)
        self.assertIn("contém erro", problems[0])

    def test_accumulated_calculation_serialization_display_and_ranking_errors_fail_closed(self):
        calculation_cycle = SimpleNamespace(
            CATEGORY_ORDER=FakeCycle.CATEGORY_ORDER,
            INDICADORES=FakeCycle.INDICADORES,
            _calculate_results=Mock(side_effect=RuntimeError("cálculo inválido")),
        )
        calculation_errors = []
        exporter._export_cycle_results(
            cycle_key="pne_2026_2036",
            cycle_module=calculation_cycle,
            municipios=["Teste"],
            shared=self.shared,
            errors=calculation_errors,
            results_cache=exporter.ResultsCache(),
        )
        self.assertEqual(calculation_errors[0]["stage"], "calculate_results")

        serialization_errors = []
        with patch.object(
            exporter,
            "_serialize_result",
            side_effect=RuntimeError("serialização inválida"),
        ):
            serialized = exporter._export_cycle_results(
                cycle_key="pne_2026_2036",
                cycle_module=FakeCycle,
                municipios=["Teste"],
                shared=self.shared,
                errors=serialization_errors,
                results_cache=exporter.ResultsCache(),
            )
        self.assertTrue(
            all(error["stage"] == "serialize_result" for error in serialization_errors)
        )
        self.assertEqual(
            serialized["municipios"]["Teste"]["results"]["indicador_a"],
            {"error": "serialização inválida"},
        )

        display_shared = FakeShared()
        display_shared._format_metric_value = Mock(side_effect=RuntimeError("display inválido"))
        display_errors = []
        exporter._export_cycle_results(
            cycle_key="pne_2026_2036",
            cycle_module=FakeCycle,
            municipios=["Teste"],
            shared=display_shared,
            errors=display_errors,
            results_cache=exporter.ResultsCache(),
        )
        self.assertTrue(any(error["stage"].startswith("display.") for error in display_errors))

        ranking_errors = []
        with patch.object(
            exporter,
            "_build_rankings_payload_for_municipio",
            side_effect=RuntimeError("ranking inválido"),
        ):
            rankings = exporter._export_cycle_rankings(
                cycle_key="pne_2026_2036",
                cycle_module=FakeCycle,
                municipios=["Teste"],
                shared=self.shared,
                errors=ranking_errors,
                results_cache=exporter.ResultsCache(),
            )
        self.assertEqual(ranking_errors[0]["stage"], "rankings")
        self.assertEqual(rankings["municipios_exportados"], 0)

        for errors in (
            calculation_errors,
            serialization_errors,
            display_errors,
            ranking_errors,
        ):
            with tempfile.TemporaryDirectory() as temp_dir:
                output_dir = Path(temp_dir) / "export"
                session = ProfileSession(
                    enabled=True,
                    run_id="fail-closed-test",
                    command="export",
                    output_dir=Path(temp_dir) / "profile",
                    is_root=True,
                )
                with (
                    patch.object(exporter, "EXPORT_DIR", output_dir),
                    activate_profile_session(session),
                ):
                    exit_code = exporter._finalize_export(
                        errors=errors,
                        validation_errors=[],
                        generated_files=[],
                        municipios=["Teste"],
                        profile=exporter.TimingProfile(False),
                        partial_export=True,
                    )
                self.assertEqual(exit_code, 1)
                report = json.loads(
                    (output_dir / "export_errors.json").read_text(encoding="utf-8")
                )
                self.assertEqual(report["total_errors"], len(errors))
                result_event = next(
                    event for event in session.events if event.name == "export.result"
                )
                self.assertEqual(result_event.status, "error")

    def test_clean_finalization_returns_zero_without_error_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "export"
            with patch.object(exporter, "EXPORT_DIR", output_dir):
                exit_code = exporter._finalize_export(
                    errors=[],
                    validation_errors=[],
                    generated_files=[],
                    municipios=["Teste"],
                    profile=exporter.TimingProfile(False),
                    partial_export=True,
                )

            self.assertEqual(exit_code, 0)
            self.assertFalse((output_dir / "export_errors.json").exists())

    def test_targeted_and_full_main_return_nonzero_after_calculation_error(self):
        failing_cycle = SimpleNamespace(
            CATEGORY_ORDER=FakeCycle.CATEGORY_ORDER,
            INDICADORES=FakeCycle.INDICADORES,
            _calculate_results=Mock(side_effect=RuntimeError("cálculo inválido")),
            _calculate_results_for_indicators=Mock(
                side_effect=RuntimeError("cálculo inválido")
            ),
        )
        for targeted in (True, False):
            with self.subTest(targeted=targeted), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir) / "data_pipeline"
                initial_output = root / "export" / "data"
                args = SimpleNamespace(
                    limit=None,
                    municipio=["Teste"] if targeted else None,
                    check_connection=False,
                    include_derived=False,
                    cycle=["pne_2026_2036"] if targeted else None,
                    indicator=["indicador_a"] if targeted else None,
                    profile=False,
                )
                selected_indicators = {
                    "pne_2026_2036": ("indicador_a",) if targeted else None
                }
                with (
                    patch.object(exporter, "BASE_DIR", root),
                    patch.object(exporter, "EXPORT_DIR", initial_output),
                    patch.object(exporter, "_safe_timestamp", return_value="test"),
                    patch.object(exporter, "_parse_args", return_value=args),
                    patch.object(data_loader, "load_municipios", return_value=["Teste"]),
                    patch.object(
                        exporter,
                        "_select_cycles_and_indicators",
                        return_value=(
                            {"pne_2026_2036": failing_cycle},
                            selected_indicators,
                        ),
                    ),
                    patch.object(
                        exporter,
                        "_export_indicator_details_file",
                        return_value=root / "export" / "details.json",
                    ),
                    patch.object(exporter, "_export_state_reference", return_value={}),
                    patch.object(exporter, "_export_projections", return_value={}),
                    patch.object(exporter, "_export_planning_scenarios", return_value={}),
                    patch.object(exporter, "_export_education_attendance", return_value={}),
                    patch.object(exporter, "_export_fundeb_data", return_value={}),
                    patch.object(exporter, "_export_pnate_data", return_value={}),
                ):
                    exit_code = exporter.main()

                self.assertEqual(exit_code, 1)
                error_files = list(root.rglob("export_errors.json"))
                self.assertEqual(len(error_files), 1)
                report = json.loads(error_files[0].read_text(encoding="utf-8"))
                self.assertEqual(report["errors"][0]["stage"], "calculate_results")
                self.assertFalse((Path(temp_dir) / "public" / "data").exists())

    def test_targeted_output_stays_in_debug_and_does_not_create_public_data(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            debug_file = root / "data_pipeline" / "export" / "debug" / "sample.json"
            public_file = root / "public" / "data" / "sample.json"
            exporter._write_json(debug_file, {"ok": True})

            self.assertTrue(debug_file.exists())
            self.assertFalse(public_file.exists())
            self.assertEqual(json.loads(debug_file.read_text(encoding="utf-8")), {"ok": True})

    def test_invalid_cycle_indicator_and_municipio_fail_with_clear_messages(self):
        with self.assertRaisesRegex(ValueError, "Ciclo inexistente: invalido"):
            exporter._select_cycles_and_indicators(
                requested_cycles=["invalido"],
                requested_indicators=None,
                cycle_modules={"pne_2026_2036": FakeCycle},
            )
        with self.assertRaisesRegex(ValueError, "Indicador inexistente"):
            exporter._select_cycles_and_indicators(
                requested_cycles=["pne_2026_2036"],
                requested_indicators=["invalido"],
                cycle_modules={"pne_2026_2036": FakeCycle},
            )
        with self.assertRaisesRegex(ValueError, "Município inexistente: Invalido"):
            exporter._select_municipios(
                available=["Teste"],
                requested=["Invalido"],
                limit=None,
                strict=True,
            )

    def test_default_selection_keeps_all_cycles_and_all_indicators(self):
        modules = {"pne_2014_2024": FakeCycle, "pne_2026_2036": FakeCycle}
        selected, indicators = exporter._select_cycles_and_indicators(
            requested_cycles=None,
            requested_indicators=None,
            cycle_modules=modules,
        )

        self.assertEqual(selected, modules)
        self.assertEqual(indicators, {"pne_2014_2024": None, "pne_2026_2036": None})

    def test_exporter_does_not_generate_the_retired_inequality_placeholder(self):
        source = (DATA_PIPELINE_DIR / "scripts" / "export_static_data.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("desigualdade_por_municipio.json", source)
        self.assertNotIn("_export_inequality_documents", source)
        self.assertNotIn("_build_indicator_details", source)

    def test_indicator_details_export_uses_canonical_builder_and_writes_contract(self):
        municipio = "Município Teste"
        dependency_data = pd.DataFrame(
            [
                {
                    "ano": 2025,
                    "municipio": municipio,
                    "mat_infantil_pre": 42,
                    "dependencia": "municipal",
                }
            ]
        )
        controlled_loader = Mock(return_value=dependency_data)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "export"
            with (
                patch.dict(
                    indicator_details.DETAIL_BUILDERS,
                    {"pre_escola": indicator_details.build_pre_escola_details},
                    clear=True,
                ),
                patch.object(
                    indicator_details,
                    "load_pre_escola_por_dependencia_data",
                    controlled_loader,
                ),
                patch.object(
                    indicator_details,
                    "load_pre_escola_data",
                    return_value=pd.DataFrame(),
                ),
                patch.object(
                    indicator_details,
                    "build_privadas_conveniadas_shared",
                    return_value=None,
                ),
                patch.object(
                    exporter,
                    "build_indicator_details",
                    wraps=indicator_details.build_indicator_details,
                ) as canonical_builder,
            ):
                output_path = exporter._export_indicator_details_file(
                    municipios=[municipio],
                    output_dir=output_dir,
                )

            canonical_builder.assert_called_once_with(municipio)
            controlled_loader.assert_called_once_with()
            self.assertEqual(
                output_path,
                output_dir / "indicator_details_por_municipio.json",
            )
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(
                set(payload),
                {
                    "generated_at",
                    "total_municipios",
                    "municipios_exportados",
                    "municipios",
                },
            )
            self.assertEqual(payload["total_municipios"], 1)
            self.assertEqual(payload["municipios_exportados"], 1)
            details = payload["municipios"][municipio]["indicator_details"]
            self.assertEqual(set(details), {"pre_escola"})
            self.assertEqual(details["pre_escola"]["unit"], "matrículas")
            self.assertEqual(
                details["pre_escola"]["series_total"],
                [{"ano": 2025, "valor": 42}],
            )
            self.assertEqual(
                details["pre_escola"]["series_dependencia"],
                [
                    {
                        "ano": 2025,
                        "municipal": 42,
                        "estadual": 0,
                        "privada": 0,
                        "federal": 0,
                    }
                ],
            )
            self.assertFalse((Path(temp_dir) / "public" / "data").exists())

    def test_indicator_details_builder_error_stops_export_without_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "export"
            output_path = output_dir / "indicator_details_por_municipio.json"
            with patch.object(
                exporter,
                "build_indicator_details",
                side_effect=RuntimeError("falha controlada do builder"),
            ) as canonical_builder:
                with self.assertRaisesRegex(
                    RuntimeError,
                    "falha controlada do builder",
                ):
                    exporter._export_indicator_details_file(
                        municipios=["Município Teste"],
                        output_dir=output_dir,
                    )

            canonical_builder.assert_called_once_with("Município Teste")
            self.assertFalse(output_path.exists())
            self.assertEqual(list(output_dir.rglob("*.json")), [])


if __name__ == "__main__":
    unittest.main()
