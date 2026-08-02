from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import tempfile
import unittest

from data_pipeline.src.state_config import (
    DEFAULT_STATE_CODE,
    StateConfigError,
    load_state_config,
    normalize_state_code,
    resolve_state_config_path,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


class StateConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.valid = json.loads(
            (REPO_ROOT / "config" / "states" / "rs.json").read_text(
                encoding="utf-8"
            )
        )

    def _load(self, payload: dict, *, requested: str = "RS"):
        with tempfile.TemporaryDirectory() as temporary:
            config_dir = Path(temporary)
            path = config_dir / f"{requested.strip().lower()}.json"
            path.write_text(
                json.dumps(payload, ensure_ascii=False),
                encoding="utf-8",
            )
            return load_state_config(requested, config_dir=config_dir)

    def test_loads_valid_rs_and_normalizes_the_requested_code(self) -> None:
        config = load_state_config(" rs ")
        self.assertEqual(DEFAULT_STATE_CODE, "RS")
        self.assertEqual(config.schema_version, "state-config-v1")
        self.assertEqual(config.state_code, "RS")
        self.assertEqual(config.state_name, "Rio Grande do Sul")
        self.assertEqual(config.municipality_ibge_prefix, "43")
        self.assertEqual(config.expected_municipality_count, 497)
        self.assertEqual(config.locale, "pt-BR")
        self.assertEqual(normalize_state_code(" rs "), "RS")
        self.assertEqual(resolve_state_config_path("RS").name, "rs.json")

    def test_rejects_unknown_schema(self) -> None:
        with self.assertRaisesRegex(StateConfigError, "schemaVersion desconhecido"):
            self._load({**self.valid, "schemaVersion": "state-config-v2"})

    def test_rejects_divergent_state_code(self) -> None:
        with self.assertRaisesRegex(StateConfigError, "diverge do estado solicitado"):
            self._load({**self.valid, "stateCode": "SC"})

    def test_rejects_invalid_prefix_and_count(self) -> None:
        for payload, message in (
            ({**self.valid, "municipalityIbgePrefix": "4"}, "dois dígitos"),
            ({**self.valid, "municipalityIbgePrefix": 43}, "texto não vazio"),
            ({**self.valid, "expectedMunicipalityCount": 0}, "inteiro positivo"),
            ({**self.valid, "expectedMunicipalityCount": True}, "inteiro positivo"),
        ):
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(StateConfigError, message):
                    self._load(payload)

    def test_rejects_missing_and_unexpected_fields(self) -> None:
        missing = dict(self.valid)
        missing.pop("locale")
        with self.assertRaisesRegex(StateConfigError, "campos obrigatórios ausentes: locale"):
            self._load(missing)
        with self.assertRaisesRegex(StateConfigError, "campos inesperados: extra"):
            self._load({**self.valid, "extra": "blocked"})

    def test_missing_state_fails_without_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(FileNotFoundError, "não encontrada para AL"):
                load_state_config("AL", config_dir=Path(temporary))

    def test_state_config_is_immutable(self) -> None:
        config = load_state_config()
        with self.assertRaises(FrozenInstanceError):
            config.state_code = "SC"  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
