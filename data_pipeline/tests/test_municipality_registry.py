from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import tempfile
import unittest

from data_pipeline.src.municipality_registry import (
    MunicipalityRegistryError,
    load_municipality_registry,
    normalize_municipality_name,
)
from data_pipeline.src.state_config import StateConfig, load_state_config


REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_INDEX_PATH = REPO_ROOT / "public" / "data" / "municipios_index.json"
REGISTRY_PATH = REPO_ROOT / "config" / "municipalities" / "rs.json"


class MunicipalityRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.state = load_state_config()
        cls.registry = load_municipality_registry(cls.state)
        cls.public_index = json.loads(PUBLIC_INDEX_PATH.read_text(encoding="utf-8"))
        cls.raw_registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

    def _load_payload(
        self,
        payload: dict,
        *,
        state_config: StateConfig | None = None,
    ):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "registry.json"
            path.write_text(
                json.dumps(payload, ensure_ascii=False),
                encoding="utf-8",
            )
            return load_municipality_registry(
                state_config or self.state,
                registry_path=path,
            )

    def _mutated(self) -> dict:
        return json.loads(json.dumps(self.raw_registry, ensure_ascii=False))

    def test_real_registry_preserves_all_497_public_identities_in_order(self) -> None:
        self.assertEqual(self.registry.schema_version, "municipality-registry-v1")
        self.assertEqual(self.registry.state_code, "RS")
        self.assertEqual(self.registry.municipality_count, 497)
        self.assertEqual(len(self.registry.ordered_records), 497)
        self.assertEqual(len(self.registry.ids), 497)
        self.assertEqual(
            [record.ibge_code for record in self.registry.ordered_records],
            [entry["id_municipio"] for entry in self.public_index["municipios"]],
        )
        self.assertEqual(
            [record.name for record in self.registry.ordered_records],
            [entry["nome"] for entry in self.public_index["municipios"]],
        )
        self.assertEqual(
            [record.slug for record in self.registry.ordered_records],
            [entry["slug"] for entry in self.public_index["municipios"]],
        )
        self.assertTrue(
            all(
                isinstance(record.ibge_code, str)
                and len(record.ibge_code) == 7
                and record.ibge_code.isdigit()
                and record.ibge_code.startswith("43")
                for record in self.registry.ordered_records
            )
        )
        self.assertEqual(
            len({record.slug.casefold() for record in self.registry.ordered_records}),
            497,
        )

    def test_rejects_divergent_count(self) -> None:
        payload = self._mutated()
        payload["municipalityCount"] = 496
        with self.assertRaisesRegex(MunicipalityRegistryError, "declara 496"):
            self._load_payload(payload)

    def test_rejects_duplicate_code_and_slug_case_insensitively(self) -> None:
        duplicate_code = self._mutated()
        duplicate_code["municipalities"][1]["ibgeCode"] = duplicate_code[
            "municipalities"
        ][0]["ibgeCode"]
        with self.assertRaisesRegex(MunicipalityRegistryError, "ibgeCode duplicado"):
            self._load_payload(duplicate_code)

        duplicate_slug = self._mutated()
        duplicate_slug["municipalities"][1]["slug"] = duplicate_slug[
            "municipalities"
        ][0]["slug"].upper()
        with self.assertRaisesRegex(MunicipalityRegistryError, "slug duplicado"):
            self._load_payload(duplicate_slug)

    def test_rejects_other_state_numeric_code_and_empty_name(self) -> None:
        for field, value, message in (
            ("ibgeCode", "4200035", "não possui o prefixo 43"),
            ("ibgeCode", 4300034, "texto com exatamente sete dígitos"),
            ("name", "  ", "name deve ser texto não vazio"),
        ):
            payload = self._mutated()
            payload["municipalities"][0][field] = value
            with self.subTest(field=field, value=value):
                with self.assertRaisesRegex(MunicipalityRegistryError, message):
                    self._load_payload(payload)

    def test_rejects_unexpected_record_fields(self) -> None:
        payload = self._mutated()
        payload["municipalities"][0]["path"] = "/data/municipios/4300034/index.json"
        with self.assertRaisesRegex(MunicipalityRegistryError, "campos inesperados: path"):
            self._load_payload(payload)

    def test_lookup_and_unique_name_resolution(self) -> None:
        acegua = self.registry.get_by_id("4300034")
        self.assertEqual(acegua.name, "Aceguá")
        self.assertIs(self.registry.resolve_unique_name("Aceguá"), acegua)
        self.assertIs(self.registry.resolve_unique_name("  acegua  "), acegua)
        self.assertEqual(normalize_municipality_name("São José-d'Oeste"), "sao jose d oeste")
        with self.assertRaisesRegex(KeyError, "4399999"):
            self.registry.get_by_id("4399999")
        with self.assertRaisesRegex(MunicipalityRegistryError, "ausente"):
            self.registry.resolve_unique_name("Município inexistente")

    def test_exact_name_precedes_normalized_resolution_and_ambiguity_fails(self) -> None:
        state = StateConfig(
            schema_version="state-config-v1",
            state_code="RS",
            state_name="Rio Grande do Sul",
            municipality_ibge_prefix="43",
            expected_municipality_count=2,
            locale="pt-BR",
        )
        payload = {
            "schemaVersion": "municipality-registry-v1",
            "stateCode": "RS",
            "municipalityCount": 2,
            "municipalities": [
                {"ibgeCode": "4300034", "name": "Água", "slug": "agua-acento"},
                {"ibgeCode": "4300059", "name": "Agua", "slug": "agua-sem-acento"},
            ],
        }
        registry = self._load_payload(payload, state_config=state)
        self.assertEqual(registry.resolve_unique_name("Água").ibge_code, "4300034")
        self.assertEqual(registry.resolve_unique_name("Agua").ibge_code, "4300059")
        with self.assertRaisesRegex(MunicipalityRegistryError, "ambíguo"):
            registry.resolve_unique_name("AGUA")

    def test_public_projection_matches_the_versioned_index_exactly(self) -> None:
        projected = self.registry.build_public_index_payload(
            generated_at=self.public_index["generated_at"]
        )
        self.assertEqual(projected, self.public_index)
        self.assertEqual(
            self.public_index["total_municipios"],
            self.state.expected_municipality_count,
        )
        self.assertTrue(
            all(
                entry["path"]
                == f"/data/municipios/{entry['id_municipio']}/index.json"
                for entry in self.public_index["municipios"]
            )
        )
        public_ids = {
            path.name
            for path in (REPO_ROOT / "public" / "data" / "municipios").iterdir()
            if path.is_dir()
        }
        self.assertEqual(public_ids, self.registry.ids)

    def test_registry_structures_are_immutable(self) -> None:
        with self.assertRaises(FrozenInstanceError):
            self.registry.state_code = "SC"  # type: ignore[misc]
        with self.assertRaises(TypeError):
            self.registry.records_by_id["4399999"] = self.registry.ordered_records[0]  # type: ignore[index]
        with self.assertRaises(FrozenInstanceError):
            self.registry.ordered_records[0].name = "Outro"  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
