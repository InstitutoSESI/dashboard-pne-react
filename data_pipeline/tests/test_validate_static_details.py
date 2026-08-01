from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


PIPELINE_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_SPEC = importlib.util.spec_from_file_location(
    "validate_static_details_embedded_inequality",
    PIPELINE_ROOT / "scripts" / "validate_static_details.py",
)
validator = importlib.util.module_from_spec(VALIDATOR_SPEC)
assert VALIDATOR_SPEC.loader is not None
sys.modules[VALIDATOR_SPEC.name] = validator
VALIDATOR_SPEC.loader.exec_module(validator)

from data_pipeline.src.municipal_inequality import build_document  # noqa: E402
from src.municipality_registry import load_municipality_registry  # noqa: E402
from src.state_config import StateConfig  # noqa: E402


class ValidateStaticDetailsTests(unittest.TestCase):
    municipalities = {
        "4300034": ("Aceguá", "acegua"),
        "4300059": ("Água Santa", "agua-santa"),
    }

    @classmethod
    def _registry(cls, root: Path):
        state = StateConfig(
            schema_version="state-config-v1",
            state_code="RS",
            state_name="Rio Grande do Sul",
            municipality_ibge_prefix="43",
            expected_municipality_count=len(cls.municipalities),
            locale="pt-BR",
        )
        path = root / "registry.json"
        cls._write(
            path,
            {
                "schemaVersion": "municipality-registry-v1",
                "stateCode": "RS",
                "municipalityCount": len(cls.municipalities),
                "municipalities": [
                    {"ibgeCode": code, "name": name, "slug": slug}
                    for code, (name, slug) in cls.municipalities.items()
                ],
            },
        )
        return load_municipality_registry(state, registry_path=path)

    @staticmethod
    def _document(municipality_id: str, name: str) -> dict:
        return build_document(
            municipality_id=municipality_id,
            municipality_name=name,
            generated_at="2026-08-01T00:00:00+00:00",
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

    @classmethod
    def _details(cls, municipality_id: str, name: str) -> dict:
        return {
            "sample": {"title": "Indicador de teste"},
            "_shared": {
                "privadas_conveniadas": {
                    "ultimo_ano": 2025,
                    "resumo": {},
                    "por_secao": [],
                    "por_categoria": [],
                    "fonte": {},
                    "disponivel_desde": 2025,
                },
                "municipal_inequality": cls._document(municipality_id, name),
            },
        }

    @staticmethod
    def _write(path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def test_valid_embedded_document_and_private_shared_content_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "municipios" / "4300034" / "details.json"
            self._write(path, self._details("4300034", "Aceguá"))
            problems: list[validator.Problem] = []

            validator.validate_detail_file(path, problems)

            self.assertEqual(problems, [])

    def test_missing_document_and_municipality_mismatch_are_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "municipios" / "4300034"
            path = root / "details.json"
            payload = self._details("4300059", "Água Santa")
            self._write(path, payload)
            problems: list[validator.Problem] = []

            validator.validate_detail_file(path, problems)

            messages = "\n".join(problem.message for problem in problems)
            self.assertIn("must match directory 4300034", messages)

            payload["_shared"].pop("municipal_inequality")
            self._write(path, payload)
            problems = []
            validator.validate_detail_file(path, problems)
            self.assertTrue(
                any("municipal_inequality must be an object" in problem.message for problem in problems)
            )

    def test_unknown_publication_state_is_rejected_without_becoming_zero(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "municipios" / "4300034" / "details.json"
            payload = self._details("4300034", "Aceguá")
            group = payload["_shared"]["municipal_inequality"]["inequalityPilot"]["groups"][0]
            group["status"] = "unknown"
            group["publicationStatus"] = "unknown"
            self._write(path, payload)
            problems: list[validator.Problem] = []

            validator.validate_detail_file(path, problems)

            self.assertTrue(any("status is invalid" in problem.message for problem in problems))
            self.assertEqual(group["numerator"], 25)

    def test_shared_coverage_requires_both_documents_for_every_municipality(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            data_dir = Path(temporary)
            registry = self._registry(data_dir)
            paths = []
            for municipality_id, name in (
                ("4300034", "Aceguá"),
                ("4300059", "Água Santa"),
            ):
                path = data_dir / "municipios" / municipality_id / "details.json"
                self._write(path, self._details(municipality_id, name))
                paths.append(path)
            problems: list[validator.Problem] = []

            validator._validate_shared_coverage(
                paths,
                data_dir,
                problems,
                registry,
            )

            self.assertEqual(problems, [])

    def test_registry_name_is_required_in_embedded_document(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "municipios" / "4300034" / "details.json"
            self._write(path, self._details("4300034", "Nome divergente"))
            problems: list[validator.Problem] = []

            validator.validate_detail_file(
                path,
                problems,
                municipality_name="Aceguá",
            )

            self.assertTrue(
                any("must equal registry name 'Aceguá'" in problem.message for problem in problems)
            )

    def test_municipal_index_identity_is_compared_with_registry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            data_dir = Path(temporary)
            registry = self._registry(data_dir)
            record = registry.get_by_id("4300034")
            index_path = data_dir / "municipios" / record.ibge_code / "index.json"
            self._write(
                index_path,
                {
                    "id_municipio": record.ibge_code,
                    "municipio": record.name,
                    "slug": record.slug,
                },
            )
            problems: list[validator.Problem] = []
            validator.validate_municipal_index_identity(data_dir, record, problems)
            self.assertEqual(problems, [])

            payload = json.loads(index_path.read_text(encoding="utf-8"))
            payload["slug"] = "slug-divergente"
            self._write(index_path, payload)
            validator.validate_municipal_index_identity(data_dir, record, problems)
            self.assertTrue(
                any("diverges from registry" in problem.message for problem in problems)
            )


if __name__ == "__main__":
    unittest.main()
