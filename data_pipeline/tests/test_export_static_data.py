import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

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


if __name__ == "__main__":
    unittest.main()
