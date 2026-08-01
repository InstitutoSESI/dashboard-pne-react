from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PIPELINE_ROOT = Path(__file__).resolve().parents[1]
MATERIALIZER_SPEC = importlib.util.spec_from_file_location(
    "materialize_municipal_inequality_details",
    PIPELINE_ROOT / "scripts" / "materialize_municipal_inequality.py",
)
materializer = importlib.util.module_from_spec(MATERIALIZER_SPEC)
assert MATERIALIZER_SPEC.loader is not None
sys.modules[MATERIALIZER_SPEC.name] = materializer
MATERIALIZER_SPEC.loader.exec_module(materializer)

from data_pipeline.src.municipal_inequality import build_document  # noqa: E402


class MaterializeMunicipalInequalityTests(unittest.TestCase):
    municipalities = {
        "4300034": "Aceguá",
        "4300059": "Água Santa",
    }

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.target = self.root / "static_partitioned" / "municipios"
        self.education = self.root / "static_partitioned" / "educacao" / "municipios"
        self.published = self.root / "public" / "data" / "municipios"
        self.registry = self.root / "static_partitioned" / "municipios_index.json"
        self.target.mkdir(parents=True)
        self.education.mkdir(parents=True)
        self._write_json(
            self.registry,
            {
                "generated_at": "2026-08-01T00:00:00+00:00",
                "total_municipios": len(self.municipalities),
                "municipios": [
                    {"id_municipio": municipality_id, "nome": name}
                    for municipality_id, name in self.municipalities.items()
                ],
            },
        )
        for municipality_id in self.municipalities:
            self._write_details(self.target, municipality_id)
            self._write_education(municipality_id, supports_recalculation=True)

        self.allowed_output_patch = patch.object(
            materializer,
            "ALLOWED_OUTPUT_ROOTS",
            frozenset({self.target.resolve()}),
        )
        self.expected_count_patch = patch.object(
            materializer,
            "EXPECTED_MUNICIPALITIES",
            len(self.municipalities),
        )
        self.allowed_output_patch.start()
        self.expected_count_patch.start()
        self.addCleanup(self.allowed_output_patch.stop)
        self.addCleanup(self.expected_count_patch.stop)

    @staticmethod
    def _write_json(path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def _write_details(
        self,
        root: Path,
        municipality_id: str,
        document: dict | None = None,
    ) -> None:
        shared = {
            "privadas_conveniadas": {
                "sentinel": f"private:{municipality_id}",
            }
        }
        if document is not None:
            shared["municipal_inequality"] = document
        self._write_json(
            root / municipality_id / "details.json",
            {
                "sample_indicator": {"title": f"details:{municipality_id}"},
                "_shared": shared,
            },
        )

    def _write_education(
        self,
        municipality_id: str,
        *,
        supports_recalculation: bool,
        embedded_id: str | None = None,
    ) -> None:
        rows = [
            {
                "ano": 2025,
                "dependencia": "publica",
                "localizacao": "urbana",
                "matriculas": 100,
            },
            {
                "ano": 2025,
                "dependencia": "publica",
                "localizacao": "rural",
                "matriculas": 100,
            },
        ]
        if supports_recalculation:
            rows[0]["matriculas_integral"] = 25
            rows[1]["matriculas_integral"] = 30
        self._write_json(
            self.education / f"{municipality_id}.json",
            {
                "id_municipio": embedded_id or municipality_id,
                "updated_at": "2026-08-01T00:00:00+00:00",
                "blocos": {
                    "matriculas": {
                        "detalhamentos": {"por_rede_localizacao": rows}
                    }
                },
            },
        )

    def _existing_document(self, municipality_id: str) -> dict:
        return build_document(
            municipality_id=municipality_id,
            municipality_name=self.municipalities[municipality_id],
            generated_at="2026-07-19T23:50:16-03:00",
            rows=[
                {
                    "ano": 2025,
                    "dependencia": "publica",
                    "localizacao": "urbana",
                    "matriculas_integral": 25,
                    "matriculas": 100,
                },
                {
                    "ano": 2025,
                    "dependencia": "publica",
                    "localizacao": "rural",
                    "matriculas_integral": 30,
                    "matriculas": 100,
                },
            ],
        )

    def _materialize(self, *, check: bool = False) -> dict:
        return materializer.materialize(
            self.target,
            education_root=self.education,
            registry_path=self.registry,
            published_root=self.published,
            check=check,
        )

    def test_merges_document_without_overwriting_shared_and_only_writes_when_changed(self) -> None:
        first = self._materialize()
        self.assertEqual(first["updated"], len(self.municipalities))
        self.assertEqual(first["recalculatedPilotCount"], len(self.municipalities))

        for municipality_id in self.municipalities:
            directory = self.target / municipality_id
            details = json.loads((directory / "details.json").read_text(encoding="utf-8"))
            self.assertEqual(
                details["sample_indicator"],
                {"title": f"details:{municipality_id}"},
            )
            self.assertEqual(
                details["_shared"]["privadas_conveniadas"],
                {"sentinel": f"private:{municipality_id}"},
            )
            self.assertEqual(
                details["_shared"]["municipal_inequality"]["municipality"]["id"],
                municipality_id,
            )
            self.assertFalse((directory / "diagnostico.json").exists())

        second = self._materialize()
        self.assertEqual(second["preserved"], len(self.municipalities))
        self.assertEqual(second["updated"], 0)

    def test_atomic_replace_is_used_for_each_changed_details_file(self) -> None:
        real_replace = os.replace
        with patch.object(materializer.os, "replace", wraps=real_replace) as replace:
            self._materialize()

        self.assertEqual(replace.call_count, len(self.municipalities))
        self.assertEqual(list(self.target.rglob("*.tmp")), [])

    def test_existing_embedded_document_is_used_when_education_cannot_recalculate(self) -> None:
        expected = {}
        for municipality_id in self.municipalities:
            document = self._existing_document(municipality_id)
            expected[municipality_id] = document
            self._write_details(self.target, municipality_id, document)
            self._write_education(municipality_id, supports_recalculation=False)

        result = self._materialize()

        self.assertEqual(result["pilotSource"], "published")
        self.assertEqual(result["preservedPublishedPilotCount"], len(self.municipalities))
        self.assertEqual(result["preserved"], len(self.municipalities))
        for municipality_id, document in expected.items():
            details = json.loads(
                (self.target / municipality_id / "details.json").read_text(encoding="utf-8")
            )
            self.assertEqual(details["_shared"]["municipal_inequality"], document)

    def test_staging_uses_embedded_publication_as_fallback(self) -> None:
        expected = {}
        for municipality_id in self.municipalities:
            document = self._existing_document(municipality_id)
            expected[municipality_id] = document
            self._write_details(self.published, municipality_id, document)
            self._write_education(municipality_id, supports_recalculation=False)

        result = self._materialize()

        self.assertEqual(result["updated"], len(self.municipalities))
        for municipality_id, document in expected.items():
            details = json.loads(
                (self.target / municipality_id / "details.json").read_text(encoding="utf-8")
            )
            self.assertEqual(details["_shared"]["municipal_inequality"], document)

    def test_identity_failure_happens_before_any_details_write(self) -> None:
        invalid_id = next(reversed(self.municipalities))
        self._write_education(
            invalid_id,
            supports_recalculation=True,
            embedded_id="9999999",
        )
        before = {
            path: path.read_bytes()
            for path in self.target.glob("*/details.json")
        }

        with self.assertRaisesRegex(RuntimeError, "Identidade educacional divergente"):
            self._materialize()

        self.assertEqual({path: path.read_bytes() for path in before}, before)

    def test_materializer_has_no_legacy_diagnostic_dependency(self) -> None:
        source = (PIPELINE_ROOT / "scripts" / "materialize_municipal_inequality.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("diagnostico.json", source)


if __name__ == "__main__":
    unittest.main()
