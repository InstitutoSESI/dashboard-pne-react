import sys
from pathlib import Path

import pandas as pd

DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.school_infrastructure_materialization import (
    CONTRACT_VERSION,
    CUT_ORDER,
    INDICATOR_ORDER,
    RESULT_KEYS,
    attach_school_infrastructure_contract,
    adapt_pne_internet_details,
    adapt_pne_internet_yearly,
    build_contracts,
    result_for,
)


def source_frame():
    common = {
        "ano": 2025,
        "id_municipio": "4300001",
        "situacao_funcionamento": 1,
        "in_agua_potavel": 1,
        "in_energia_inexistente": 0,
        "in_biblioteca_sala_leitura": 1,
        "in_quadra_esportes": 1,
        "in_esgoto_rede_publica": 0,
    }
    return pd.DataFrame(
        [
            {
                **common,
                "cod_escola": 1,
                "tp_dependencia": 3,
                "tp_localizacao": 1,
                "in_internet": 1,
            },
            {
                **common,
                "cod_escola": 2,
                "tp_dependencia": 4,
                "tp_localizacao": 2,
                "in_internet": None,
            },
        ]
    )


def contract():
    return build_contracts(source_frame(), ["4300001"])["4300001"]


def education_document():
    return {
        "id_municipio": "4300001",
        "municipio": "Município",
        "blocos": {
            "rede_escolar": {
                "ultimo_ano": 2025,
                "series": {
                    "internet": [
                        {"ano": 2024, "perc_internet": 75.0},
                        {"ano": 2025, "perc_internet": 50.0},
                    ]
                },
                "resumo_ultimo_ano": {"perc_internet": 50.0},
                "infraestrutura": {
                    "ultimo_ano": 2025,
                    "series": {
                        "internet": [
                            {"ano": 2024, "valor": 75.0},
                            {"ano": 2025, "valor": 50.0},
                        ]
                    },
                    "resumo_ultimo_ano": {"internet": 50.0},
                    "por_rede": [
                        {
                            "ano": 2025,
                            "dependencia": "municipal",
                            "escolas": 99,
                            "perc_internet": 0.0,
                        },
                        {
                            "ano": 2025,
                            "dependencia": "privada",
                            "escolas": 99,
                            "perc_internet": 0.0,
                        },
                    ],
                    "por_localizacao": [
                        {
                            "ano": 2025,
                            "localizacao": "urbana",
                            "escolas": 99,
                            "perc_internet": 0.0,
                        },
                        {
                            "ano": 2025,
                            "localizacao": "rural",
                            "escolas": 99,
                            "perc_internet": 0.0,
                        },
                    ],
                },
            }
        },
    }


def test_contract_has_stable_shape_order_and_missing_semantics():
    value = contract()
    assert value["contractVersion"] == CONTRACT_VERSION
    assert list(value["indicatorDefinitions"]) == list(INDICATOR_ORDER)
    assert list(value["years"][0]["cuts"]) == list(CUT_ORDER)
    assert list(result_for(value, "internet")) == list(RESULT_KEYS)
    internet = result_for(value, "internet")
    assert internet == {
        "numerator": 1,
        "denominator": 1,
        "percentage": 100.0,
        "totalActiveSchools": 2,
        "observedSchools": 1,
        "missingSchools": 1,
        "status": "partial",
    }
    empty_cut = result_for(value, "internet", "federal")
    assert empty_cut["totalActiveSchools"] == 0
    assert empty_cut["percentage"] is None
    assert empty_cut["status"] == "unavailable"
    zero_available = result_for(value, "esgoto_rede_publica")
    assert zero_available["percentage"] == 0.0
    assert zero_available["status"] == "published"


def test_contract_attachment_preserves_history_and_uses_current_result():
    original = education_document()
    adapted = attach_school_infrastructure_contract(original, contract())
    infra = adapted["blocos"]["rede_escolar"]["infraestrutura"]
    assert "series" in infra
    assert infra["contractVersion"] == CONTRACT_VERSION
    assert infra["series"]["internet"][0] == {"ano": 2024, "valor": 75.0}
    assert infra["series"]["internet"][1]["valor"] == 100.0
    assert infra["por_rede"][0]["escolas"] == 1
    assert infra["por_rede"][1]["perc_internet"] is None
    assert original["blocos"]["rede_escolar"]["infraestrutura"]["series"]["internet"][1][
        "valor"
    ] == 50.0


def test_pne_adapter_preserves_history_and_uses_raw_canonical_percentage():
    payload = {
        "series_total": [{"ano": 2024, "valor": 3}, {"ano": 2025, "valor": 9}],
        "series_components": [
            {"ano": 2024, "numerador": 3, "denominador": 4, "percentual": 75.0},
            {"ano": 2025, "numerador": 9, "denominador": 9, "percentual": 100.0},
        ],
        "series_dependencia": [{"ano": 2024, "municipal": 3}],
    }
    adapted = adapt_pne_internet_details(payload, contract())
    assert adapted["series_components"][0] == payload["series_components"][0]
    assert adapted["series_components"][-1] == {
        "ano": 2025,
        "numerador": 1,
        "denominador": 1,
        "percentual": 100.0,
    }
    assert adapted["series_dependencia"][-1]["municipal"] == 1
    yearly = pd.DataFrame([{"ano": 2024, "valor": 75.0}, {"ano": 2025, "valor": 1.0}])
    result = adapt_pne_internet_yearly(yearly, contract())
    assert result.to_dict("records") == [
        {"ano": 2024, "valor": 75.0},
        {"ano": 2025, "valor": 100.0},
    ]


def test_existing_pne_internet_result_uses_canonical_2025(monkeypatch):
    import src.pne.calculations_2026 as calculations

    historical = pd.DataFrame(
        [
            {
                "ano": 2024,
                "municipio": "Município",
                "escolas_com_internet": 3,
                "qntd_escolas": 4,
            },
            {
                "ano": 2025,
                "municipio": "Município",
                "escolas_com_internet": 0,
                "qntd_escolas": 2,
            },
        ]
    )
    monkeypatch.setattr(
        calculations, "load_infraestrutura_escolar_data", lambda: historical
    )
    monkeypatch.setattr(
        calculations,
        "load_school_infrastructure_contract",
        lambda _municipality: contract(),
    )
    item = next(item for item in calculations.INFRA_ITEMS if item["key"] == "internet")
    result = calculations._calc_infra_totalizado("Município", item)
    assert result["series"] == [
        {"ano": 2024, "valor": 75.0},
        {"ano": 2025, "valor": result_for(contract(), "internet")["percentage"]},
    ]
