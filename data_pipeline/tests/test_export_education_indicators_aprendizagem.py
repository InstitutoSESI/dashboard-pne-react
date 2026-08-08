import importlib.util
import sys
import types
import unittest
from pathlib import Path

import pandas as pd


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "export_education_indicators.py"
)
SPEC = importlib.util.spec_from_file_location(
    "export_education_indicators_aprendizagem",
    SCRIPT_PATH,
)
UTILS_EDUCACAO = types.ModuleType("utils_educacao")
UTILS_EDUCACAO.get_engine = lambda _database: object()
sys.modules["utils_educacao"] = UTILS_EDUCACAO
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class EducationLearningExportTest(unittest.TestCase):
    def test_preserves_ideb_components_and_official_precision(self):
        municipality_id = "4314902"
        source = pd.DataFrame(
            [
                {
                    "ano": year,
                    "id_municipio": municipality_id,
                    "dependencia": "publica",
                    "etapa_ensino": "fundamental_anos_iniciais",
                    "ideb": ideb,
                    "saeb_lp": portuguese,
                    "saeb_mt": mathematics,
                    "nota_media_padronizada": learning,
                    "indicador_rendimento": flow,
                    "saeb_proficiencia_media": None,
                    "saeb_materia": None,
                    "taxa_alfabetizacao": None,
                    "media_inse": None,
                    "qtd_alunos_inse": None,
                }
                for year, ideb, portuguese, mathematics, learning, flow in (
                    (2005, 3.8, 177.6, 184.0, 4.702913, 0.808456),
                    (2023, 5.2, 201.4, 211.8, 5.603421, 0.936284),
                    (2025, 5.4, 203.1, 210.9, 5.734219, 0.949371),
                )
            ]
        )
        source = pd.concat(
            [source, source.iloc[[-1]].assign(saeb_materia="matematica")],
            ignore_index=True,
        )

        block = MODULE.montar_bloco_aprendizagem(source, municipality_id)
        series = block["series"]["ideb"]["fundamental_anos_iniciais"]

        self.assertEqual(
            series,
            [
                {
                    "ano": 2005,
                    "ideb": 3.8,
                    "saeb_lp": 177.6,
                    "saeb_mt": 184.0,
                    "nota_media_padronizada": 4.702913,
                    "indicador_rendimento": 0.808456,
                },
                {
                    "ano": 2023,
                    "ideb": 5.2,
                    "saeb_lp": 201.4,
                    "saeb_mt": 211.8,
                    "nota_media_padronizada": 5.603421,
                    "indicador_rendimento": 0.936284,
                },
                {
                    "ano": 2025,
                    "ideb": 5.4,
                    "saeb_lp": 203.1,
                    "saeb_mt": 210.9,
                    "nota_media_padronizada": 5.734219,
                    "indicador_rendimento": 0.949371,
                },
            ],
        )
        self.assertAlmostEqual(
            series[-1]["nota_media_padronizada"]
            * series[-1]["indicador_rendimento"],
            series[-1]["ideb"],
            delta=0.05,
        )
        self.assertEqual(
            block["resumo_ultimo_ano"][
                "nota_media_padronizada_fundamental_anos_iniciais"
            ],
            5.734219,
        )
        self.assertEqual(
            block["resumo_ultimo_ano"][
                "indicador_rendimento_fundamental_anos_iniciais"
            ],
            0.949371,
        )
        detail = block["detalhamentos"]["por_etapa_rede"][-1]
        self.assertEqual(
            len(block["detalhamentos"]["por_etapa_rede"]),
            3,
        )
        self.assertEqual(detail["nota_media_padronizada"], 5.734219)
        self.assertEqual(detail["indicador_rendimento"], 0.949371)
        self.assertNotIn("nota_media_padronizada", block["campos_indisponiveis"])
        self.assertNotIn("indicador_rendimento", block["campos_indisponiveis"])


if __name__ == "__main__":
    unittest.main()
