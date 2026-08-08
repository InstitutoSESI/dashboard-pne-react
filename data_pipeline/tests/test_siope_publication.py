from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.siope_publication import (  # noqa: E402
    INDICATOR_DEFINITIONS,
    SIOPE_YEARS,
    build_siope_publication,
)


class SiopePublicationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.municipalities = [
            {"ibgeCode": "2700102", "name": "Água Branca", "slug": "agua-branca"},
            {"ibgeCode": "2705200", "name": "Messias", "slug": "messias"},
        ]
        self.rows_by_year = {}
        for year in SIOPE_YEARS:
            rows = []
            for municipality in self.municipalities:
                if year == 2025 and municipality["ibgeCode"] == "2705200":
                    continue
                for position, definition in enumerate(INDICATOR_DEFINITIONS, start=1):
                    rows.append(
                        {
                            "TIPO": "Municipal",
                            "NUM_ANO": year,
                            "NUM_PERI": 6,
                            "SIG_UF": "AL",
                            "COD_MUNI": int(municipality["ibgeCode"][:6]),
                            "COD_EXIB": definition["codigo_indicador"],
                            "NOM_INDI": f"Indicador oficial {definition['codigo_indicador']}",
                            "VAL_INDI": "0" if position == 1 else f"{position}.25",
                        }
                    )
            self.rows_by_year[year] = rows

    def build(self):
        return build_siope_publication(
            state_code="AL",
            municipality_ibge_prefix="27",
            municipalities=self.municipalities,
            rows_by_year=self.rows_by_year,
        )

    def test_publica_mesma_anatomia_e_universo_municipal(self) -> None:
        artifacts = self.build()
        self.assertEqual(set(artifacts), {"wide", "catalog", "coverage"})
        self.assertEqual(artifacts["wide"]["total_municipios"], 2)
        self.assertEqual(len(artifacts["wide"]["municipios"]), 2)
        self.assertEqual(artifacts["catalog"]["total_indicadores_selecionados"], 14)

    def test_ausencia_de_2025_e_declarada_sem_fabricar_zero(self) -> None:
        artifacts = self.build()
        messias = artifacts["wide"]["municipios"]["2705200"]
        self.assertNotIn("2025", messias["anos"])
        self.assertEqual(
            artifacts["coverage"]["municipios_ausentes_2025_p6"],
            [
                {
                    "id_municipio": "2705200",
                    "municipio": "Messias",
                    "status": "municipio_ausente",
                }
            ],
        )
        agua_branca = artifacts["wide"]["municipios"]["2700102"]
        official_zero = agua_branca["anos"]["2025"]["indicadores"][
            "aplicacao_mde_percentual"
        ]["valor"]
        self.assertEqual(official_zero, 0)

    def test_linha_de_outra_uf_bloqueia_publicacao(self) -> None:
        rows = copy.deepcopy(self.rows_by_year)
        rows[2025][0]["SIG_UF"] = "RS"
        with self.assertRaisesRegex(ValueError, "outra UF"):
            build_siope_publication(
                state_code="AL",
                municipality_ibge_prefix="27",
                municipalities=self.municipalities,
                rows_by_year=rows,
            )


if __name__ == "__main__":
    unittest.main()
