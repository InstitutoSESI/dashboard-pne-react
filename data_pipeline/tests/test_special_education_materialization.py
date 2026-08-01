from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


PIPELINE = Path(__file__).resolve().parents[1]
PUBLIC_CONTRACTS = (
    PIPELINE.parent / "public" / "data" / "educacao" / "educacao-especial"
)
sys.path.insert(0, str(PIPELINE))

from src.special_education_materialization import (  # noqa: E402
    ALL_FIELDS,
    build_contract,
    field_availability,
    json_bytes,
    validate_contract,
)


def source() -> pd.DataFrame:
    rows = []
    for school, dependency, location, total, common, exclusive in [
        (1, "municipal", "urbana", 10, 8, 2),
        (2, "privada", "rural", 5, 5, 0),
    ]:
        row = {
            "ano": 2025,
            "cod_escola": school,
            "id_municipio": "4300001",
            "dependencia": dependency,
            "localizacao": location,
            "rede_publica": dependency != "privada",
            "QT_MAT_ESP": total,
            "QT_MAT_ESP_CC": common,
            "QT_MAT_ESP_CE": exclusive,
            "QT_TUR_ESP": 2,
            "QT_TUR_ESP_CC": 1,
            "QT_TUR_ESP_CE": 1,
            "QT_DOC_BAS": 3,
            "QT_DOC_ESP": 4,
            "QT_DOC_ESP_CC": 3,
            "QT_DOC_ESP_CE": 1,
            "TP_AEE": 1 if school == 1 else 0,
            "IN_SALA_ATENDIMENTO_ESPECIAL": 1 if school == 1 else 0,
            "QT_MAT_BAS_LIBRAS": 1 if school == 1 else 0,
            "QT_TUR_BAS_LIBRAS": 1 if school == 1 else 0,
        }
        for field in ALL_FIELDS:
            row.setdefault(field, 0)
            row[f"disponivel_{field.lower()}"] = True
            row[f"valor_extremo_{field.lower()}"] = False
            row[f"vazio_estrutural_{field.lower()}"] = False
        rows.append(row)
    return pd.DataFrame(rows)


def contract(frame: pd.DataFrame | None = None) -> dict:
    frame = source() if frame is None else frame
    return build_contract(
        frame,
        {"id_municipio": "4300001", "municipio": "Teste", "slug": "teste"},
        field_availability(frame),
    )


def year(payload: dict, value: int) -> dict:
    return next(item for item in payload["years"] if item["year"] == value)


def test_uses_sums_for_inclusion_and_distinct_schools():
    payload = contract()
    total = year(payload, 2025)["cuts"]["total"]
    assert total["specialEducation"]["enrollments"]["value"] == 15
    assert total["specialEducation"]["schools"]["value"] == 2
    assert total["specialEducation"]["classes"]["value"] == 4
    assert total["specialEducation"]["commonClassClasses"]["value"] == 2
    assert total["specialEducation"]["exclusiveClassClasses"]["value"] == 2
    assert total["specialEducation"]["teacherAssignments"]["value"] == 8
    assert total["specialEducation"]["commonClassTeacherAssignments"]["value"] == 6
    assert total["specialEducation"]["exclusiveClassTeacherAssignments"]["value"] == 2
    assert total["commonClassInclusionRate"]["numerator"] == 13
    assert total["commonClassInclusionRate"]["denominator"] == 15
    assert total["commonClassInclusionRate"]["value"] == 100 * 13 / 15
    assert validate_contract(payload) == []


def test_missing_bilingual_column_is_unavailable_not_zero():
    frame = source()
    frame["disponivel_qt_mat_bas_libras"] = False
    payload = contract(frame)
    bilingual = year(payload, 2025)["cuts"]["total"]["bilingualDeafEducation"]
    assert bilingual["enrollments"]["state"] == "unavailable"
    assert bilingual["enrollments"]["value"] is None
    assert bilingual["schools"]["state"] == "unavailable"


def test_zero_denominator_is_not_applicable_and_88888_is_not_published():
    frame = source()
    frame.loc[:, ["QT_MAT_ESP", "QT_MAT_ESP_CC", "QT_MAT_ESP_CE"]] = 0
    frame.loc[0, "QT_PROF_TRAD_LIBRAS"] = pd.NA
    frame.loc[0, "valor_extremo_qt_prof_trad_libras"] = True
    payload = contract(frame)
    total = year(payload, 2025)["cuts"]["total"]
    assert total["commonClassInclusionRate"]["state"] == "not_applicable"
    interpreter = total["bilingualDeafEducation"]["interpreterAssignments"]
    assert interpreter["state"] == "partial"
    assert interpreter["value"] is None
    serialized = json_bytes(payload)
    assert b'"value":88888' not in serialized
    assert b'"numerator":88888' not in serialized
    assert b'"denominator":88888' not in serialized


def test_empty_official_counts_are_structural_zero_without_partial_propagation():
    frame = source()
    quantitative = [
        "QT_MAT_ESP",
        "QT_MAT_ESP_CC",
        "QT_MAT_ESP_CE",
        "QT_TUR_ESP",
        "QT_DOC_BAS",
        "QT_MAT_BAS_LIBRAS",
        "QT_TUR_BAS_LIBRAS",
        "QT_DOC_BAS_LIBRAS",
    ]
    frame.loc[1, quantitative] = pd.NA
    frame.loc[
        1, [f"vazio_estrutural_{field.lower()}" for field in quantitative]
    ] = True

    total = year(contract(frame), 2025)["cuts"]["total"]

    assert total["specialEducation"]["enrollments"] == {
        "value": 10,
        "state": "observed",
        "sourceId": "inep_censo_escolar_school_microdata",
        "observedSchools": 2,
        "missingSchools": 0,
    }
    assert total["specialEducation"]["schools"]["state"] == "observed"
    assert total["commonClassInclusionRate"]["state"] == "observed"
    assert total["commonClassInclusionRate"]["value"] == 80
    assert total["bilingualDeafEducation"]["enrollments"]["state"] == "observed"


def test_explicit_zero_and_all_structural_empty_counts_are_observed():
    frame = source()
    quantitative = [field for field in ALL_FIELDS if field.startswith("QT_")]
    frame.loc[:, quantitative] = 0
    frame.loc[1, quantitative] = pd.NA
    frame.loc[
        1, [f"vazio_estrutural_{field.lower()}" for field in quantitative]
    ] = True

    total = year(contract(frame), 2025)["cuts"]["total"]

    assert total["specialEducation"]["enrollments"]["value"] == 0
    assert total["specialEducation"]["enrollments"]["state"] == "observed"
    assert total["specialEducation"]["schools"]["value"] == 0
    assert total["specialEducation"]["schools"]["state"] == "observed"
    assert total["commonClassInclusionRate"]["state"] == "not_applicable"


def test_aee_share_uses_only_schools_with_special_education_enrollments():
    frame = source()
    frame.loc[1, ["QT_MAT_ESP", "QT_MAT_ESP_CC", "QT_MAT_ESP_CE"]] = 0
    frame.loc[1, "TP_AEE"] = 1

    aee = year(contract(frame), 2025)["cuts"]["total"]["aee"]

    assert aee["schoolsOfferingAee"]["value"] == 2
    assert aee["eligibleSchools"]["value"] == 1
    assert aee["shareOfferingAee"]["numerator"] == 1
    assert aee["shareOfferingAee"]["denominator"] == 1
    assert aee["shareOfferingAee"]["value"] == 100


def test_missing_flag_is_partial_only_inside_indicator_eligible_universe():
    frame = source()
    frame.loc[1, ["QT_MAT_ESP", "QT_MAT_ESP_CC", "QT_MAT_ESP_CE"]] = 0
    frame.loc[1, ["TP_AEE", "IN_SALA_ATENDIMENTO_ESPECIAL"]] = pd.NA

    aee = year(contract(frame), 2025)["cuts"]["total"]["aee"]

    assert aee["schoolsOfferingAee"]["state"] == "observed"
    assert aee["schoolsWithResourceRoom"]["state"] == "observed"
    assert aee["shareOfferingAee"]["state"] == "observed"
    assert aee["shareWithResourceRoom"]["state"] == "observed"

    frame.loc[0, "TP_AEE"] = pd.NA
    eligible_missing = year(contract(frame), 2025)["cuts"]["total"]["aee"]
    assert eligible_missing["schoolsOfferingAee"]["state"] == "observed"
    assert eligible_missing["shareOfferingAee"]["state"] == "partial"
    assert eligible_missing["shareOfferingAee"]["reason"] == "unresolved_component"


def test_genuinely_missing_eligible_quantitative_is_partial():
    frame = source()
    frame.loc[0, "QT_MAT_ESP"] = pd.NA

    total = year(contract(frame), 2025)["cuts"]["total"]
    enrollments = total["specialEducation"]["enrollments"]

    assert enrollments["state"] == "partial"
    assert enrollments["reason"] == "incomplete_school_aggregation"
    assert enrollments["observedSchools"] == 1
    assert enrollments["missingSchools"] == 1
    assert total["commonClassInclusionRate"]["state"] == "partial"


def test_extreme_is_local_to_affected_metric():
    frame = source()
    frame.loc[0, "QT_PROF_TRAD_LIBRAS"] = pd.NA
    frame.loc[0, "valor_extremo_qt_prof_trad_libras"] = True

    total = year(contract(frame), 2025)["cuts"]["total"]

    assert (
        total["bilingualDeafEducation"]["interpreterAssignments"]["state"]
        == "partial"
    )
    assert total["specialEducation"]["enrollments"]["state"] == "observed"
    assert total["specialEducation"]["classes"]["state"] == "observed"
    assert total["commonClassInclusionRate"]["state"] == "observed"
    assert total["aee"]["schoolsOfferingAee"]["state"] == "observed"


def test_all_contract_cuts_reconcile_with_structural_zeros():
    frame = source()
    frame.loc[1, [field for field in ALL_FIELDS if field.startswith("QT_")]] = pd.NA
    fields = [field for field in ALL_FIELDS if field.startswith("QT_")]
    frame.loc[
        1, [f"vazio_estrutural_{field.lower()}" for field in fields]
    ] = True
    payload = contract(frame)
    yearly = year(payload, 2025)

    for cut in (
        "total",
        "publica",
        "municipal",
        "estadual",
        "federal",
        "privada",
        "urbana",
        "rural",
    ):
        special = yearly["cuts"][cut]["specialEducation"]
        for metric in (
            "enrollments",
            "commonClassEnrollments",
            "exclusiveClassEnrollments",
            "classes",
            "commonClassClasses",
            "exclusiveClassClasses",
            "teacherAssignments",
            "commonClassTeacherAssignments",
            "exclusiveClassTeacherAssignments",
        ):
            assert special[metric]["state"] in {"observed", "derived_zero"}
    assert validate_contract(payload) == []


def test_contract_serialization_is_byte_deterministic():
    first = json_bytes(contract())
    second = json_bytes(contract(source().sample(frac=1, random_state=7)))

    assert first == second


def published_contract(code: str) -> dict:
    return json.loads(
        (PUBLIC_CONTRACTS / "municipios" / f"{code}.json").read_text(
            encoding="utf-8"
        )
    )


def test_published_reference_municipalities():
    sao = published_contract("4318705")
    expected_sao = {
        2022: (1675, 1520, 155),
        2023: (1977, 1819, 158),
        2024: (2195, 2027, 168),
        2025: (2692, 2520, 172),
    }
    for reference_year, expected in expected_sao.items():
        total = year(sao, reference_year)["cuts"]["total"]
        special = total["specialEducation"]
        points = (
            special["enrollments"],
            special["commonClassEnrollments"],
            special["exclusiveClassEnrollments"],
        )
        assert tuple(point["value"] for point in points) == expected
        assert all(point["state"] == "observed" for point in points)
        assert total["commonClassInclusionRate"]["state"] == "observed"

    alegrete = published_contract("4300406")
    for reference_year in range(2014, 2026):
        special = year(alegrete, reference_year)["cuts"]["total"]["specialEducation"]
        assert special["enrollments"]["state"] == "observed"

    acegua = published_contract("4300034")
    for reference_year in range(2021, 2026):
        special = year(acegua, reference_year)["cuts"]["total"]["specialEducation"]
        assert special["exclusiveClassEnrollments"]["value"] == 0
        assert special["exclusiveClassEnrollments"]["state"] == "observed"
