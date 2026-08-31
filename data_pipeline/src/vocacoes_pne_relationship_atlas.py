"""Congela o universo e a matriz pré-teste do Atlas Educação × Território.

Esta etapa não estima associações. Ela materializa, antes de qualquer ajuste novo,
o inventário de assinaturas, as disposições analíticas, a deduplicação AA1 ↔ Job5i,
as hipóteses, os fences de causalidade e a reauditoria das leituras públicas atuais.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any, Iterable, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = (
    REPO_ROOT / "data_pipeline/contracts/vocacoes-pne-relationship-atlas-v1.json"
)
DEFAULT_OUTPUT_ROOT = (
    REPO_ROOT / ".tmp/vocacoes-pne/relationship-atlas-v1/preregistration"
)
MODULE_PATH = Path(__file__).resolve()

PACKAGE_FILES = (
    "SOURCE_SIGNATURE_DISPOSITIONS.json",
    "ANALYTIC_VARIABLES.json",
    "OVERLAP_MAPPING.json",
    "HYPOTHESIS_MATRIX.json",
    "IDENTIFICATION_AUDIT.json",
    "CURRENT_PROMOTIONS_AUDIT.json",
    "QA_SUMMARY.json",
    "FREEZE.json",
    "MANIFEST.json",
)

IBGE_CODE_RE = re.compile(r"^[0-9]{7}$")
AVAILABILITY_STATES = (
    "observed",
    "observed_zero",
    "unavailable",
    "suppressed",
    "not_applicable",
)
DISPOSITION_PRIORITY = {
    "TEST_PRIMARY": 6,
    "TEST_SECONDARY": 5,
    "DENOMINATOR_OR_QA_ONLY": 4,
    "DESCRIPTIVE_ONLY": 3,
    "BLOCKED_GRAIN_SCOPE_TIME": 2,
    "NOT_THEORETICALLY_JUSTIFIED": 1,
}


class RelationshipAtlasValidationError(RuntimeError):
    """Falha fechada de contrato ou materialização."""


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.write_bytes(_json_bytes(payload))


def _selector(
    source: str,
    metric_id: str,
    *,
    stage: str | Sequence[str] | None = None,
    dimension: str | Sequence[str] | None = None,
    age_group: str | Sequence[str] | None = None,
    scope: str | None = None,
    lens: str | None = None,
    network_scope: str | None = None,
) -> dict[str, Any]:
    return {
        "source": source,
        "metricId": metric_id,
        "stage": stage,
        "dimension": dimension,
        "ageGroup": age_group,
        "coverageScope": scope,
        "territorialLens": lens,
        "networkScope": network_scope,
    }


def _variable(
    variable_id: str,
    *,
    label: str,
    lane: str,
    disposition: str,
    selector: Mapping[str, Any] | None = None,
    components: Sequence[Mapping[str, Any]] = (),
    formula: str = "source_value_preserved",
    unit: str,
    lens: str,
    role: str,
    notes: str = "",
) -> dict[str, Any]:
    if disposition not in DISPOSITION_PRIORITY:
        raise RelationshipAtlasValidationError(
            f"Disposição desconhecida para {variable_id}: {disposition}"
        )
    return {
        "variableId": variable_id,
        "label": label,
        "lane": lane,
        "disposition": disposition,
        "selector": dict(selector) if selector else None,
        "components": [dict(component) for component in components],
        "formula": formula,
        "unit": unit,
        "territorialLens": lens,
        "role": role,
        "notes": notes,
    }


STAGES = {
    "FI": {
        "education": "fundamental_anos_iniciais",
        "population": "age_6_10",
        "populationMetric": "demography.population_age_6_10",
        "label": "anos iniciais",
    },
    "FF": {
        "education": "fundamental_anos_finais",
        "population": "age_11_14",
        "populationMetric": "demography.population_age_11_14",
        "label": "anos finais",
    },
    "HS": {
        "education": "medio",
        "population": "age_15_17",
        "populationMetric": "demography.population_age_15_17",
        "label": "ensino médio",
    },
}


def build_analytic_variables() -> list[dict[str, Any]]:
    variables: list[dict[str, Any]] = []

    for code, stage in STAGES.items():
        pop_selector = _selector(
            "AA1",
            stage["populationMetric"],
            stage=stage["population"],
            dimension="ALL",
            scope="RS_497",
            lens="resident_population",
            network_scope="not_applicable",
        )
        enrollment_selector = _selector(
            "AA1",
            "education.enrollments",
            stage=stage["education"],
            dimension="ALL",
            scope="RS_497",
            lens="school_location",
            network_scope="total_all_dependencies",
        )
        full_time_selector = _selector(
            "AA1",
            "education.full_time_enrollments",
            stage=stage["education"],
            dimension="ALL",
            scope="RS_497",
            lens="school_location",
            network_scope="total_all_dependencies",
        )
        variables.extend(
            [
                _variable(
                    f"POP_{code}",
                    label=f"População residente — {stage['label']}",
                    lane="demography_network",
                    disposition="TEST_PRIMARY",
                    selector=pop_selector,
                    unit="people",
                    lens="resident_population",
                    role="territorial_exposure",
                ),
                _variable(
                    f"ENROLL_{code}",
                    label=f"Matrículas localizadas — {stage['label']}",
                    lane="demography_network",
                    disposition="TEST_PRIMARY",
                    selector=enrollment_selector,
                    unit="enrollments",
                    lens="school_location",
                    role="education_outcome",
                ),
                _variable(
                    f"FULLTIME_SHARE_{code}",
                    label=f"Participação das matrículas em tempo integral — {stage['label']}",
                    lane="demography_network",
                    disposition="TEST_PRIMARY",
                    components=[full_time_selector, enrollment_selector],
                    formula="100 * full_time_enrollments / enrollments; denominator_zero=null",
                    unit="percent",
                    lens="school_location",
                    role="education_outcome_or_condition",
                ),
                _variable(
                    f"PRESSURE_{code}",
                    label=f"Matrículas localizadas por coorte residente — {stage['label']}",
                    lane="demography_network",
                    disposition="TEST_SECONDARY",
                    components=[enrollment_selector, pop_selector],
                    formula="enrollments / resident_age_group; context_only_not_coverage; denominator_zero=null",
                    unit="ratio",
                    lens="school_location_vs_resident_population",
                    role="territorial_context_exposure",
                    notes="Lentes distintas; não é taxa de cobertura ou frequência.",
                ),
            ]
        )
        for metric_key, metric_id, label, disposition in (
            ("DROPOUT", "education.dropout_rate_percent", "Abandono", "TEST_PRIMARY"),
            (
                "DISTORTION",
                "education.age_grade_distortion_rate_percent",
                "Distorção idade-série",
                "TEST_PRIMARY",
            ),
            ("FAILURE", "education.failure_rate_percent", "Reprovação", "TEST_SECONDARY"),
            ("APPROVAL", "education.approval_rate_percent", "Aprovação", "TEST_SECONDARY"),
            (
                "TEACHER",
                "education.teacher_adequacy_percent",
                "Adequação da formação docente",
                "TEST_PRIMARY",
            ),
        ):
            variables.append(
                _variable(
                    f"{metric_key}_{code}",
                    label=f"{label} — {stage['label']}",
                    lane="demography_network",
                    disposition=disposition,
                    selector=_selector(
                        "AA1",
                        metric_id,
                        stage=stage["education"],
                        dimension="ALL",
                        scope="RS_497",
                        lens="school_location",
                        network_scope="total_all_dependencies",
                    ),
                    unit="percent",
                    lens="school_location",
                    role=(
                        "school_condition_exposure"
                        if metric_key == "TEACHER"
                        else "education_outcome"
                    ),
                )
            )

    basic_enrollment = _selector(
        "AA1",
        "education.enrollments",
        stage="education_basic",
        dimension="ALL",
        scope="RS_497",
        lens="school_location",
        network_scope="total_all_dependencies",
    )
    school_count = _selector(
        "AA1",
        "education.school_count",
        stage="education_basic",
        dimension="ALL",
        scope="RS_497",
        lens="school_location",
        network_scope="total_all_dependencies",
    )
    internet_count = _selector(
        "AA1",
        "education.schools_with_internet",
        stage="education_basic",
        dimension="ALL",
        scope="RS_497",
        lens="school_location",
        network_scope="total_all_dependencies",
    )
    total_population = _selector(
        "AA1",
        "demography.total_population",
        stage="all_ages",
        dimension="ALL",
        scope="RS_497",
        lens="resident_population",
        network_scope="not_applicable",
    )
    variables.extend(
        [
            _variable(
                "POP_TOTAL",
                label="População residente total",
                lane="demography_network",
                disposition="TEST_PRIMARY",
                selector=total_population,
                unit="people",
                lens="resident_population",
                role="territorial_exposure",
            ),
            _variable(
                "ENROLL_BASIC",
                label="Matrículas da educação básica",
                lane="demography_network",
                disposition="DENOMINATOR_OR_QA_ONLY",
                selector=basic_enrollment,
                unit="enrollments",
                lens="school_location",
                role="denominator",
            ),
            _variable(
                "SCHOOL_COUNT",
                label="Escolas localizadas",
                lane="demography_network",
                disposition="TEST_PRIMARY",
                selector=school_count,
                unit="schools",
                lens="school_location",
                role="education_offer_outcome",
            ),
            _variable(
                "INTERNET_SHARE",
                label="Participação de escolas com internet",
                lane="demography_network",
                disposition="TEST_PRIMARY",
                components=[internet_count, school_count],
                formula="100 * schools_with_internet / school_count; denominator_zero=null",
                unit="percent",
                lens="school_location",
                role="school_condition_exposure",
            ),
            _variable(
                "ENROLL_PER_SCHOOL",
                label="Matrículas da educação básica por escola",
                lane="demography_network",
                disposition="TEST_SECONDARY",
                components=[basic_enrollment, school_count],
                formula="education_basic_enrollments / school_count; denominator_zero=null",
                unit="enrollments_per_school",
                lens="school_location",
                role="school_scale_context",
            ),
            _variable(
                "INSE",
                label="Indicador de nível socioeconômico escolar",
                lane="demography_network",
                disposition="TEST_PRIMARY",
                selector=_selector(
                    "AA1",
                    "education.inse_value",
                    stage="education_basic_assessed",
                    dimension="ALL",
                    scope="RS_497",
                    lens="school_location",
                    network_scope="total_all_dependencies",
                ),
                unit="inse_scale_points",
                lens="school_location",
                role="social_context_exposure",
            ),
        ]
    )

    adult_population = _selector(
        "AA1",
        "adult.population_count",
        stage="adult_18_or_more",
        dimension="ALL",
        scope="RS_497",
        lens="resident_population",
        network_scope="not_applicable",
    )
    for variable_id, metric_id, label, disposition in (
        (
            "ADULT_HS_COMPLETION",
            "adult.high_school_completion_share_percent",
            "Adultos com ensino médio completo ou mais",
            "TEST_PRIMARY",
        ),
        (
            "ADULT_FUND_COMPLETION",
            "adult.fundamental_completion_share_percent",
            "Adultos com ensino fundamental completo ou mais",
            "TEST_SECONDARY",
        ),
    ):
        variables.append(
            _variable(
                variable_id,
                label=label,
                lane="demography_network",
                disposition=disposition,
                selector=_selector(
                    "AA1",
                    metric_id,
                    stage="adult_18_or_more",
                    dimension="ALL",
                    scope="RS_497",
                    lens="resident_population",
                    network_scope="not_applicable",
                ),
                unit="percent",
                lens="resident_population",
                role="territorial_education_stock_exposure",
            )
        )
    variables.append(
        _variable(
            "ADULT_POPULATION",
            label="População adulta residente",
            lane="economy_work",
            disposition="DENOMINATOR_OR_QA_ONLY",
            selector=adult_population,
            unit="people",
            lens="resident_population",
            role="denominator",
        )
    )

    for suffix, stage, label in (
        ("FUND", "eja_fundamental", "EJA fundamental"),
        ("HS", "eja_high_school", "EJA ensino médio"),
        ("TOTAL", "eja_total_context", "EJA total de contexto"),
    ):
        variables.append(
            _variable(
                f"EJA_{suffix}",
                label=label,
                lane="economy_work",
                disposition=("TEST_PRIMARY" if suffix != "TOTAL" else "DENOMINATOR_OR_QA_ONLY"),
                selector=_selector(
                    "AA1",
                    "education.eja_enrollments",
                    stage=stage,
                    dimension="ALL",
                    scope="VALE_10",
                    lens="school_location",
                    network_scope="total_all_dependencies",
                ),
                unit="enrollments",
                lens="school_location",
                role="education_outcome",
            )
        )

    ept_total_dimension = "grain=municipality_total|school=ALL|axis=ALL|course=ALL"
    for variable_id, metric_id, unit, label, disposition in (
        (
            "EPT_ENROLLMENTS",
            "education.ept_technical_enrollments",
            "enrollments",
            "Matrículas técnicas",
            "TEST_PRIMARY",
        ),
        (
            "EPT_CLASSES",
            "education.ept_class_count",
            "classes",
            "Turmas técnicas",
            "TEST_SECONDARY",
        ),
    ):
        variables.append(
            _variable(
                variable_id,
                label=label,
                lane="economy_work",
                disposition=disposition,
                selector=_selector(
                    "AA1",
                    metric_id,
                    stage="professional_technical",
                    dimension=ept_total_dimension,
                    scope="VALE_10",
                    lens="school_location",
                    network_scope="total_all_dependencies",
                ),
                unit=unit,
                lens="school_location",
                role="education_outcome",
            )
        )

    for age in ("15_17", "18_24"):
        variables.extend(
            [
                _variable(
                    f"RAIS_ACTIVE_{age}",
                    label=f"Vínculos formais ativos de {age.replace('_', ' a ')} anos",
                    lane="economy_work",
                    disposition="TEST_PRIMARY",
                    selector=_selector(
                        "AA1",
                        "labor.youth_rais.active_bonds",
                        stage=f"age_{age}",
                        dimension="ALL",
                        scope="VALE_10",
                        lens="establishment_location_workplace",
                        network_scope="not_applicable",
                    ),
                    unit="active_bonds",
                    lens="establishment_location_workplace",
                    role="territorial_exposure",
                ),
                _variable(
                    f"APPRENTICE_SHARE_{age}",
                    label=f"Participação de contratos de aprendizagem — {age.replace('_', ' a ')} anos",
                    lane="economy_work",
                    disposition="TEST_PRIMARY",
                    selector=_selector(
                        "AA1",
                        "labor.youth_rais.bond_type_composition_share_percent",
                        stage=f"age_{age}",
                        dimension="apprentice_contract",
                        scope="VALE_10",
                        lens="establishment_location_workplace",
                        network_scope="not_applicable",
                    ),
                    unit="percent",
                    lens="establishment_location_workplace",
                    role="territorial_exposure",
                ),
                _variable(
                    f"WEEKLY_HOURS_MEDIAN_{age}",
                    label=f"Jornada semanal mediana — {age.replace('_', ' a ')} anos",
                    lane="economy_work",
                    disposition="TEST_PRIMARY",
                    selector=_selector(
                        "AA1",
                        "labor.youth_rais.contracted_weekly_hours_median",
                        stage=f"age_{age}",
                        dimension="ALL",
                        scope="VALE_10",
                        lens="establishment_location_workplace",
                        network_scope="not_applicable",
                    ),
                    unit="hours_per_week",
                    lens="establishment_location_workplace",
                    role="territorial_exposure",
                ),
                _variable(
                    f"TENURE_MEDIAN_{age}",
                    label=f"Tempo mediano do vínculo — {age.replace('_', ' a ')} anos",
                    lane="economy_work",
                    disposition="TEST_SECONDARY",
                    selector=_selector(
                        "AA1",
                        "labor.youth_rais.bond_tenure_median",
                        stage=f"age_{age}",
                        dimension="ALL",
                        scope="VALE_10",
                        lens="establishment_location_workplace",
                        network_scope="not_applicable",
                    ),
                    unit="months",
                    lens="establishment_location_workplace",
                    role="territorial_exposure",
                ),
            ]
        )
        long_hour_components = [
            _selector(
                "AA1",
                "labor.youth_rais.contracted_hours_band_share_percent",
                stage=f"age_{age}",
                dimension=dimension,
                scope="VALE_10",
                lens="establishment_location_workplace",
                network_scope="not_applicable",
            )
            for dimension in ("41_to_44", "45_or_more")
        ]
        short_hour_components = [
            _selector(
                "AA1",
                "labor.youth_rais.contracted_hours_band_share_percent",
                stage=f"age_{age}",
                dimension=dimension,
                scope="VALE_10",
                lens="establishment_location_workplace",
                network_scope="not_applicable",
            )
            for dimension in ("up_to_20", "21_to_30")
        ]
        variables.extend(
            [
                _variable(
                    f"LONG_HOURS_SHARE_{age}",
                    label=f"Participação de jornadas de 41 horas ou mais — {age.replace('_', ' a ')} anos",
                    lane="economy_work",
                    disposition="TEST_PRIMARY",
                    components=long_hour_components,
                    formula="sum mutually exclusive hours-band shares; unknown preserved",
                    unit="percent",
                    lens="establishment_location_workplace",
                    role="territorial_exposure",
                ),
                _variable(
                    f"SHORT_HOURS_SHARE_{age}",
                    label=f"Participação de jornadas até 30 horas — {age.replace('_', ' a ')} anos",
                    lane="economy_work",
                    disposition="TEST_SECONDARY",
                    components=short_hour_components,
                    formula="sum mutually exclusive hours-band shares; unknown preserved",
                    unit="percent",
                    lens="establishment_location_workplace",
                    role="territorial_exposure",
                ),
            ]
        )
        for dimension, suffix, label, disposition in (
            ("high_school_incomplete", "HS_INCOMPLETE", "médio incompleto", "TEST_PRIMARY"),
            ("high_school_complete", "HS_COMPLETE", "médio completo", "TEST_SECONDARY"),
            (
                "higher_education_incomplete_or_more",
                "HIGHER_ED",
                "superior incompleto ou mais",
                "TEST_SECONDARY",
            ),
        ):
            variables.append(
                _variable(
                    f"WORKER_{suffix}_SHARE_{age}",
                    label=f"Vínculos com {label} — {age.replace('_', ' a ')} anos",
                    lane="economy_work",
                    disposition=disposition,
                    selector=_selector(
                        "AA1",
                        "labor.youth_rais.schooling_composition_share_percent",
                        stage=f"age_{age}",
                        dimension=dimension,
                        scope="VALE_10",
                        lens="establishment_location_workplace",
                        network_scope="not_applicable",
                    ),
                    unit="percent",
                    lens="establishment_location_workplace",
                    role="territorial_exposure_or_outcome",
                )
            )

    remuneration_components = [
        _selector(
            "AA1",
            "labor.youth_rais.nominal_average_monthly_remuneration_by_schooling_median",
            stage="age_18_24",
            dimension=dimension,
            scope="VALE_10",
            lens="establishment_location_workplace",
            network_scope="not_applicable",
        )
        for dimension in ("high_school_complete", "high_school_incomplete")
    ]
    variables.append(
        _variable(
            "WAGE_PREMIUM_HS_18_24",
            label="Razão remuneratória mediana entre médio completo e incompleto",
            lane="economy_work",
            disposition="TEST_SECONDARY",
            components=remuneration_components,
            formula="median_nominal_remuneration_hs_complete / median_nominal_remuneration_hs_incomplete within municipality-year; denominator_zero=null",
            unit="ratio",
            lens="establishment_location_workplace",
            role="territorial_exposure",
            notes="Razão no mesmo município-ano; evita comparação direta de valores nominais entre anos.",
        )
    )

    for metric_id, variable_id, label in (
        ("apprentice_admissions", "CAGED_APPRENTICE_15_17", "Admissões de aprendizes de 15 a 17 anos"),
        ("caged_youth_admissions", "CAGED_ADMISSIONS_15_17", "Admissões Caged de 15 a 17 anos"),
        ("caged_youth_balance", "CAGED_BALANCE_15_17", "Saldo Caged de 15 a 17 anos"),
    ):
        variables.append(
            _variable(
                variable_id,
                label=label,
                lane="economy_work",
                disposition="TEST_PRIMARY",
                selector=_selector(
                    "JOB5I",
                    metric_id,
                    age_group="15_17",
                    lens="workplace",
                    network_scope="total_all_dependencies",
                ),
                unit="adjusted_events",
                lens="workplace",
                role="territorial_exposure",
                notes="Fluxo; nunca somado ou confundido com estoque RAIS.",
            )
        )

    pop_15_17_selector = next(
        variable["selector"]
        for variable in variables
        if variable["variableId"] == "POP_HS"
    )
    pop_18_24_selector = _selector(
        "AA1",
        "demography.population_age_18_24",
        stage="age_18_24",
        dimension="ALL",
        scope="RS_497",
        lens="resident_population",
        network_scope="not_applicable",
    )
    variables.extend(
        [
            _variable(
                "POP_18_24",
                label="População residente de 18 a 24 anos",
                lane="economy_work",
                disposition="TEST_PRIMARY",
                selector=pop_18_24_selector,
                unit="people",
                lens="resident_population",
                role="denominator_or_exposure",
            ),
            _variable(
                "RAIS_INTENSITY_15_17",
                label="Vínculos de 15 a 17 anos por 100 residentes da mesma idade",
                lane="economy_work",
                disposition="TEST_PRIMARY",
                components=[
                    next(
                        variable["selector"]
                        for variable in variables
                        if variable["variableId"] == "RAIS_ACTIVE_15_17"
                    ),
                    pop_15_17_selector,
                ],
                formula="100 * workplace_active_bonds / resident_population_age_15_17; context_not_employment_rate; denominator_zero=null",
                unit="bonds_per_100_residents_context",
                lens="workplace_vs_resident_population",
                role="territorial_exposure",
            ),
            _variable(
                "CAGED_ADMISSION_INTENSITY_15_17",
                label="Admissões de 15 a 17 anos por 100 residentes da mesma idade",
                lane="economy_work",
                disposition="TEST_PRIMARY",
                components=[
                    next(
                        variable["selector"]
                        for variable in variables
                        if variable["variableId"] == "CAGED_ADMISSIONS_15_17"
                    ),
                    pop_15_17_selector,
                ],
                formula="100 * workplace_adjusted_admissions / resident_population_age_15_17; context_not_employment_rate; denominator_zero=null",
                unit="events_per_100_residents_context",
                lens="workplace_vs_resident_population",
                role="territorial_exposure",
            ),
            _variable(
                "CAGED_BALANCE_INTENSITY_15_17",
                label="Saldo Caged de 15 a 17 anos por 100 residentes da mesma idade",
                lane="economy_work",
                disposition="TEST_SECONDARY",
                components=[
                    next(
                        variable["selector"]
                        for variable in variables
                        if variable["variableId"] == "CAGED_BALANCE_15_17"
                    ),
                    pop_15_17_selector,
                ],
                formula="100 * workplace_adjusted_balance / resident_population_age_15_17; context_not_employment_rate; denominator_zero=null",
                unit="events_per_100_residents_context",
                lens="workplace_vs_resident_population",
                role="territorial_exposure",
            ),
            _variable(
                "APPRENTICE_ADMISSION_INTENSITY_15_17",
                label="Admissões de aprendizes de 15 a 17 anos por 100 residentes",
                lane="economy_work",
                disposition="TEST_PRIMARY",
                components=[
                    next(
                        variable["selector"]
                        for variable in variables
                        if variable["variableId"] == "CAGED_APPRENTICE_15_17"
                    ),
                    pop_15_17_selector,
                ],
                formula="100 * workplace_apprentice_admissions / resident_population_age_15_17; context_not_opportunity_rate; denominator_zero=null",
                unit="events_per_100_residents_context",
                lens="workplace_vs_resident_population",
                role="territorial_exposure",
            ),
        ]
    )

    sector_raw = _selector(
        "AA1",
        "labor.sector_active_bonds",
        stage="all_ages",
        dimension="*",
        scope="VALE_10",
        lens="workplace",
        network_scope="not_applicable",
    )
    occupation_raw = _selector(
        "AA1",
        "labor.occupation_active_bonds",
        stage="all_ages",
        dimension="*",
        scope="VALE_10",
        lens="workplace",
        network_scope="not_applicable",
    )
    shift_raw = _selector(
        "AA1",
        "labor.shift_share.local_differential_effect",
        stage="all_ages",
        dimension="*",
        scope="VALE_10",
        lens="workplace",
        network_scope="not_applicable",
    )
    variables.extend(
        [
            _variable(
                "INDUSTRY_SHARE_CHANGE",
                label="Mudança da participação industrial nos vínculos formais",
                lane="economy_work",
                disposition="TEST_SECONDARY",
                components=[sector_raw],
                formula="predeclared industry sector bonds / all sector bonds; endpoint change 2019-2025",
                unit="percentage_point_change",
                lens="workplace",
                role="territorial_exposure",
            ),
            _variable(
                "LOCAL_DIFFERENTIAL_SHIFT_SHARE",
                label="Componente local-diferencial do emprego formal",
                lane="economy_work",
                disposition="TEST_SECONDARY",
                components=[shift_raw],
                formula="sum local differential components within municipality; preserve accounting closure",
                unit="active_bonds",
                lens="workplace",
                role="territorial_exposure",
            ),
            _variable(
                "OCCUPATION_COURSE_BRIDGE_SUPPORT",
                label="Vínculos ocupacionais para ponte normativa curso–CBO",
                lane="economy_work",
                disposition="DESCRIPTIVE_ONLY",
                components=[occupation_raw],
                formula="deduplicated normative correspondence; not employability or demand",
                unit="active_bonds",
                lens="workplace",
                role="descriptive_support",
            ),
        ]
    )

    social_metrics = (
        ("SOC_POVERTY_PEOPLE", "social.vulnerability.registered_people_pbf_poverty_line", "Pessoas registradas na linha de pobreza"),
        ("SOC_REGISTERED_PEOPLE", "social.vulnerability.registered_people", "Pessoas registradas"),
        ("SOC_LOW_INCOME_PEOPLE", "social.vulnerability.low_income_registered_people", "Pessoas registradas de baixa renda"),
        ("SOC_CHILDREN_0_15", "social.vulnerability.registered_people_age_0_15", "Pessoas registradas de 0 a 15 anos"),
        ("SOC_ZERO_INCOME_FAMILIES", "social.vulnerability.updated_families_declared_zero_income", "Famílias atualizadas com renda declarada zero"),
        ("SOC_UPDATED_FAMILIES", "social.vulnerability.updated_families", "Famílias com cadastro atualizado"),
    )
    for variable_id, metric_id, label in social_metrics:
        variables.append(
            _variable(
                variable_id,
                label=label,
                lane="social_access",
                disposition="DENOMINATOR_OR_QA_ONLY",
                selector=_selector(
                    "AA1",
                    metric_id,
                    stage="registered_vulnerability_context",
                    dimension="E_VULNERABILIDADE",
                    scope="VALE_10",
                    lens="registered_residence_or_source_declared_municipality",
                    network_scope="not_applicable",
                ),
                unit="people_or_families",
                lens="registered_residence_or_source_declared_municipality",
                role="derived_component",
            )
        )
    component = lambda variable_id: next(  # noqa: E731
        variable["selector"]
        for variable in variables
        if variable["variableId"] == variable_id
    )
    variables.extend(
        [
            _variable(
                "SOC_POVERTY_SHARE_REGISTERED",
                label="Participação das pessoas registradas na linha de pobreza",
                lane="social_access",
                disposition="TEST_PRIMARY",
                components=[component("SOC_POVERTY_PEOPLE"), component("SOC_REGISTERED_PEOPLE")],
                formula="100 * registered_people_poverty_line / registered_people; denominator_zero=null",
                unit="percent",
                lens="registered_residence_or_source_declared_municipality",
                role="social_exposure",
            ),
            _variable(
                "SOC_LOW_INCOME_PER_POPULATION",
                label="Pessoas registradas de baixa renda por população residente",
                lane="social_access",
                disposition="TEST_PRIMARY",
                components=[component("SOC_LOW_INCOME_PEOPLE"), total_population],
                formula="100 * low_income_registered_people / total_resident_population; administrative_context_not_prevalence; denominator_zero=null",
                unit="registered_people_per_100_residents_context",
                lens="registered_residence_vs_resident_population",
                role="social_exposure",
            ),
            _variable(
                "SOC_CHILDREN_PER_POPULATION",
                label="Pessoas registradas de 0 a 15 anos por população residente",
                lane="social_access",
                disposition="TEST_SECONDARY",
                components=[component("SOC_CHILDREN_0_15"), total_population],
                formula="100 * registered_people_age_0_15 / total_resident_population; administrative_context_not_coverage; denominator_zero=null",
                unit="registered_people_per_100_residents_context",
                lens="registered_residence_vs_resident_population",
                role="social_exposure",
            ),
            _variable(
                "SOC_ZERO_INCOME_SHARE_UPDATED",
                label="Participação de renda zero entre famílias com cadastro atualizado",
                lane="social_access",
                disposition="TEST_PRIMARY",
                components=[component("SOC_ZERO_INCOME_FAMILIES"), component("SOC_UPDATED_FAMILIES")],
                formula="100 * updated_families_zero_income / updated_families; denominator_zero=null",
                unit="percent",
                lens="registered_residence_or_source_declared_municipality",
                role="social_exposure",
            ),
        ]
    )

    rural_basic = _selector(
        "AA1",
        "education.rural_basic_enrollments",
        stage="education_basic",
        dimension="ALL",
        scope="RS_497",
        lens="school_location",
        network_scope="total_all_dependencies",
    )
    variables.append(
        _variable(
            "RURAL_SHARE_STATE",
            label="Participação das matrículas rurais na educação básica",
            lane="social_access",
            disposition="TEST_SECONDARY",
            components=[rural_basic, basic_enrollment],
            formula="100 * rural_basic_enrollments / education_basic_enrollments; denominator_zero=null",
            unit="percent",
            lens="school_location",
            role="rural_context_exposure",
        )
    )
    for stage in ("all", "fundamental", "high_school", "eja"):
        for metric_suffix, metric_id, unit, role, disposition in (
            ("ENROLL", "education.rural.rural_enrollments", "enrollments", "education_outcome", "TEST_PRIMARY"),
            ("SCHOOLS", "education.rural.rural_schools", "schools", "education_offer_exposure", "TEST_PRIMARY"),
            ("CLASSES", "education.rural.rural_classes", "classes", "education_offer_exposure", "TEST_SECONDARY"),
        ):
            variables.append(
                _variable(
                    f"RURAL_{metric_suffix}_{stage.upper()}",
                    label=f"{metric_suffix.title()} rurais — {stage}",
                    lane="social_access",
                    disposition=disposition,
                    selector=_selector(
                        "AA1",
                        metric_id,
                        stage=stage,
                        dimension="ALL",
                        scope="VALE_10",
                        lens="rural_school_location",
                        network_scope="total_all_dependencies",
                    ),
                    unit=unit,
                    lens="rural_school_location",
                    role=role,
                )
            )

    for variable_id, metric_id, label, disposition, role in (
        ("AEE_SPECIAL", "education.special_aee.special_enrollments", "Matrículas da educação especial", "TEST_PRIMARY", "education_outcome"),
        ("AEE_COMMON", "education.special_aee.common_class_enrollments", "Matrículas em classes comuns", "TEST_SECONDARY", "education_outcome"),
        ("AEE_EXCLUSIVE", "education.special_aee.exclusive_class_enrollments", "Matrículas em classes exclusivas", "TEST_SECONDARY", "education_outcome"),
        ("AEE_SCHOOLS", "education.special_aee.schools_offering_aee", "Escolas com oferta de AEE", "TEST_PRIMARY", "education_offer_exposure"),
        ("AEE_RESOURCE_ROOMS", "education.special_aee.schools_with_aee_resource_room", "Escolas com sala de recursos", "TEST_PRIMARY", "education_offer_exposure"),
    ):
        variables.append(
            _variable(
                variable_id,
                label=label,
                lane="social_access",
                disposition=disposition,
                selector=_selector(
                    "AA1",
                    metric_id,
                    stage="all",
                    dimension="ALL",
                    scope="VALE_10",
                    lens="school_location",
                    network_scope="total_all_dependencies",
                ),
                unit="enrollments_or_schools",
                lens="school_location",
                role=role,
            )
        )

    for stage, suffix in (("fundamental", "FUND"), ("high_school", "HS")):
        variables.append(
            _variable(
                f"MOBILITY_{suffix}",
                label=f"Residentes que estudam em outro município — {stage}",
                lane="demography_network",
                disposition="TEST_PRIMARY",
                selector=_selector(
                    "JOB5I",
                    "residents_studying_other_municipality_share",
                    stage=stage,
                    lens="student_residence",
                    network_scope="total_all_dependencies",
                ),
                unit="percent",
                lens="student_residence",
                role="territorial_exposure",
            )
        )

    # Todas as métricas financeiras são deliberadamente mapeadas, mas o fence de
    # executor municipal × educação total impede promoção relacional nesta etapa.
    finance_metrics = (
        "finance.education_committed",
        "finance.education_liquidated",
        "finance.education_paid",
        "finance.fundeb_professional_remuneration_rate",
        "finance.fundeb_revenue_received_declared",
        "finance.fundeb_total_annual_forecast",
        "finance.liquidated_to_committed_rate",
        "finance.mde_applied_amount",
        "finance.mde_applied_rate",
        "finance.mde_margin_from_minimum",
        "finance.paid_to_committed_rate",
        "finance.paid_to_liquidated_rate",
        "finance.qse_distributed_closed_year",
        "finance.qse_distributed_per_enrollment",
        "finance.qse_enrollments_closed_year",
        "finance.qse_official_estimate_current_year",
    )
    for metric_id in finance_metrics:
        variables.append(
            _variable(
                f"FINANCE_{metric_id.split('.', 1)[1].upper()}",
                label=metric_id,
                lane="social_access",
                disposition="BLOCKED_GRAIN_SCOPE_TIME",
                selector=_selector(
                    "AA1",
                    metric_id,
                    stage="municipal_education_finance",
                    dimension="*",
                    scope="RS_497",
                    lens="municipal_executor",
                    network_scope="not_applicable_financial_executor",
                ),
                unit="source_unit",
                lens="municipal_executor",
                role="blocked_context",
                notes="Executor municipal não coincide com educação em todas as dependências; previsões permanecem separadas de execução.",
            )
        )

    # Job5i: componentes PNATE são contexto administrativo e não painel causal.
    for metric_id in (
        "pnate_adjusted_forecast",
        "pnate_authorized_after_discount",
        "pnate_beneficiary_students",
        "pnate_executed_amount",
        "school_transport_students_observed",
    ):
        variables.append(
            _variable(
                f"PNATE_{metric_id.upper()}",
                label=metric_id,
                lane="social_access",
                disposition="DESCRIPTIVE_ONLY",
                selector=_selector(
                    "JOB5I",
                    metric_id,
                    lens="municipal_executor",
                    network_scope="total_all_dependencies",
                ),
                unit="source_unit",
                lens="municipal_executor",
                role="administrative_planning_context",
                notes="Valores previstos/autorizados/executados não são intercambiáveis.",
            )
        )

    ids = [variable["variableId"] for variable in variables]
    if len(ids) != len(set(ids)):
        duplicates = sorted(key for key, count in Counter(ids).items() if count > 1)
        raise RelationshipAtlasValidationError(
            f"IDs de variáveis duplicados: {duplicates}"
        )
    return sorted(variables, key=lambda item: item["variableId"])


def _hypothesis(
    hypothesis_id: str,
    *,
    family_id: str,
    lane: str,
    exposure: str,
    outcome: str,
    method: str,
    window: str,
    priority: str,
    expected_direction: str,
    status: str,
    claim_ceiling: str,
    mechanism_id: str,
    effect_scale: str,
    pandemic_sensitivity: str = "APPLICABLE",
    controls: Sequence[str] = (),
) -> dict[str, Any]:
    alpha = 0.10 if method in {
        "PANEL_VALE",
        "CROSS_SECTION_VALE",
        "CHANGE_CROSS_SECTION_VALE",
        "SHORT_PANEL_VALE",
    } else 0.05
    return {
        "hypothesisId": hypothesis_id,
        "familyId": family_id,
        "lane": lane,
        "exposureVariableId": exposure,
        "outcomeVariableId": outcome,
        "methodPreset": method,
        "effectiveWindow": window,
        "priority": priority,
        "expectedDirection": expected_direction,
        "resultKnowledgeState": status,
        "entryClaimCeiling": claim_ceiling,
        "mechanismId": mechanism_id,
        "effectScale": effect_scale,
        "pandemicSensitivity": pandemic_sensitivity,
        "controls": list(controls),
        "multiplicityFamily": family_id,
        "familyAlpha": alpha,
        "causalEligible": False,
    }


def build_hypotheses() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    append = rows.append

    for code in STAGES:
        append(
            _hypothesis(
                f"R01_{code}_COHORT_ENROLLMENT",
                family_id="R01_DEMOGRAPHY_STAGE_ENROLLMENT",
                lane="demography_network",
                exposure=f"POP_{code}",
                outcome=f"ENROLL_{code}",
                method="PANEL_RS",
                window="2018-2025 levels; 2019-2025 changes",
                priority="PRIMARY",
                expected_direction="positive",
                status="REPLICATION_OR_EXTENSION",
                claim_ceiling="ROBUST_ASSOCIATION",
                mechanism_id="H1_DEMOGRAFIA_REDE",
                effect_scale="enrollment percent change per 10 percent cohort change",
            )
        )
        append(
            _hypothesis(
                f"R02_{code}_COHORT_FULLTIME",
                family_id="R02_DEMOGRAPHY_OFFER_RESPONSE",
                lane="demography_network",
                exposure=f"POP_{code}",
                outcome=f"FULLTIME_SHARE_{code}",
                method="PANEL_RS",
                window="2018-2025",
                priority="SECONDARY",
                expected_direction="ambiguous",
                status="NEW_PRETEST",
                claim_ceiling="PLANNING_SIGNAL",
                mechanism_id="H1_DEMOGRAFIA_REDE",
                effect_scale="full-time share percentage points per 10 percent cohort change",
            )
        )
        for outcome, suffix in ((f"DROPOUT_{code}", "DROPOUT"), (f"DISTORTION_{code}", "DISTORTION")):
            append(
                _hypothesis(
                    f"R03_{code}_PRESSURE_{suffix}",
                    family_id="R03_TERRITORIAL_PRESSURE_TRAJECTORY",
                    lane="demography_network",
                    exposure=f"PRESSURE_{code}",
                    outcome=outcome,
                    method="PANEL_RS",
                    window="2019-2025 for distortion; 2018-2025 otherwise",
                    priority="SECONDARY",
                    expected_direction="positive",
                    status="REPLICATION_OR_EXTENSION",
                    claim_ceiling="EXPLORATORY_ASSOCIATION",
                    mechanism_id="H2_TRAJETORIA_PERMANENCIA",
                    effect_scale="outcome percentage points per 10 percent pressure-context change",
                    controls=[f"POP_{code}"],
                )
            )
        for exposure, exposure_suffix, direction in (
            (f"TEACHER_{code}", "TEACHER", "negative"),
            (f"FULLTIME_SHARE_{code}", "FULLTIME", "negative"),
        ):
            for outcome, outcome_suffix in (
                (f"DROPOUT_{code}", "DROPOUT"),
                (f"DISTORTION_{code}", "DISTORTION"),
            ):
                append(
                    _hypothesis(
                        f"R04_{code}_{exposure_suffix}_{outcome_suffix}",
                        family_id="R04_SCHOOL_CONDITIONS_TRAJECTORY",
                        lane="demography_network",
                        exposure=exposure,
                        outcome=outcome,
                        method="PANEL_RS",
                        window="2019-2025 for distortion; 2018-2025 otherwise",
                        priority="PRIMARY" if outcome_suffix == "DROPOUT" else "SECONDARY",
                        expected_direction=direction,
                        status="REPLICATION_OR_EXTENSION" if exposure_suffix == "TEACHER" and outcome_suffix == "DROPOUT" else "NEW_PRETEST",
                        claim_ceiling="ROBUST_ASSOCIATION",
                        mechanism_id="H2_TRAJETORIA_PERMANENCIA",
                        effect_scale="outcome percentage points per 10 percentage-point condition change",
                        controls=["INSE", f"POP_{code}"],
                    )
                )
        for outcome, outcome_suffix in (
            (f"DROPOUT_{code}", "DROPOUT"),
            (f"DISTORTION_{code}", "DISTORTION"),
        ):
            append(
                _hypothesis(
                    f"R05_{code}_INSE_{outcome_suffix}",
                    family_id="R05_INSE_TRAJECTORY",
                    lane="demography_network",
                    exposure="INSE",
                    outcome=outcome,
                    method="REPEATED_CROSS_SECTION_RS",
                    window="2019, 2021 and 2023 only",
                    priority="PRIMARY" if outcome_suffix == "DROPOUT" else "SECONDARY",
                    expected_direction="negative",
                    status="REPLICATION_OR_EXTENSION",
                    claim_ceiling="CONTEXT_ADJUSTED_COMPARISON",
                    mechanism_id="H2_TRAJETORIA_PERMANENCIA",
                    effect_scale="outcome percentage points per one INSE standard deviation",
                    pandemic_sensitivity="NOT_APPLICABLE_PREDECLARED_THREE_OFFICIAL_CUTS",
                    controls=[f"POP_{code}", "ENROLL_PER_SCHOOL"],
                )
            )
            append(
                _hypothesis(
                    f"R06_{code}_ADULT_HS_{outcome_suffix}",
                    family_id="R06_ADULT_SCHOOLING_TRAJECTORY",
                    lane="demography_network",
                    exposure="ADULT_HS_COMPLETION",
                    outcome=outcome,
                    method="CROSS_SECTION_RS",
                    window="2022",
                    priority="PRIMARY" if outcome_suffix == "DROPOUT" else "SECONDARY",
                    expected_direction="negative",
                    status="NEW_PRETEST",
                    claim_ceiling="DISTRIBUTIONAL_PATTERN",
                    mechanism_id="H4_EJA_DISTRIBUICAO",
                    effect_scale="Spearman rho and adjusted percentage-point contrast",
                    pandemic_sensitivity="NOT_APPLICABLE_PREDECLARED_SNAPSHOT",
                    controls=[f"POP_{code}", "INSE"],
                )
            )

    append(
        _hypothesis(
            "R02_TOTAL_POP_SCHOOLS",
            family_id="R02_DEMOGRAPHY_OFFER_RESPONSE",
            lane="demography_network",
            exposure="POP_TOTAL",
            outcome="SCHOOL_COUNT",
            method="PANEL_RS",
            window="2018-2025",
            priority="PRIMARY",
            expected_direction="positive",
            status="REPLICATION_OR_EXTENSION",
            claim_ceiling="PLANNING_SIGNAL",
            mechanism_id="H1_DEMOGRAFIA_REDE",
            effect_scale="school-count percent change per 10 percent population change",
        )
    )
    for code in STAGES:
        for outcome, suffix in ((f"DROPOUT_{code}", "DROPOUT"), (f"DISTORTION_{code}", "DISTORTION")):
            append(
                _hypothesis(
                    f"R04_{code}_INTERNET_{suffix}",
                    family_id="R04_SCHOOL_CONDITIONS_TRAJECTORY",
                    lane="demography_network",
                    exposure="INTERNET_SHARE",
                    outcome=outcome,
                    method="PANEL_RS",
                    window="2019-2025 for distortion; 2018-2025 otherwise",
                    priority="SECONDARY",
                    expected_direction="negative",
                    status="NEW_PRETEST",
                    claim_ceiling="ROBUST_ASSOCIATION",
                    mechanism_id="H2_TRAJETORIA_PERMANENCIA",
                    effect_scale="outcome percentage points per 10 percentage-point internet-share change",
                    controls=["INSE", "ENROLL_PER_SCHOOL"],
                )
            )

    for code, mobility, pressure in (
        ("FUND", "MOBILITY_FUND", "PRESSURE_FF"),
        ("HS", "MOBILITY_HS", "PRESSURE_HS"),
    ):
        append(
            _hypothesis(
                f"R14_{code}_MOBILITY_MISMATCH",
                family_id="R14_EDUCATIONAL_MOBILITY_OFFER",
                lane="demography_network",
                exposure=mobility,
                outcome=pressure,
                method="CROSS_SECTION_VALE",
                window="2022",
                priority="PRIMARY",
                expected_direction="positive",
                status="REPLICATION_OR_EXTENSION",
                claim_ceiling="DISTRIBUTIONAL_PATTERN",
                mechanism_id="A1_COORTES_REDE",
                effect_scale="Spearman rho and mismatch contrast per 10 percentage points mobility",
                pandemic_sensitivity="NOT_APPLICABLE_PREDECLARED_SNAPSHOT",
            )
        )

    for exposure, suffix, direction, priority in (
        ("RAIS_INTENSITY_15_17", "RAIS", "positive", "PRIMARY"),
        ("CAGED_ADMISSION_INTENSITY_15_17", "CAGED_ADMISSION", "positive", "PRIMARY"),
        ("CAGED_BALANCE_INTENSITY_15_17", "CAGED_BALANCE", "positive", "SECONDARY"),
    ):
        for outcome, outcome_suffix in (("DROPOUT_HS", "DROPOUT"), ("DISTORTION_HS", "DISTORTION")):
            append(
                _hypothesis(
                    f"R07_{suffix}_{outcome_suffix}",
                    family_id="R07_YOUTH_WORK_TRAJECTORY",
                    lane="economy_work",
                    exposure=exposure,
                    outcome=outcome,
                    method="PANEL_VALE",
                    window="2019-2025 for RAIS; 2020-2025 for CAGED; distortion 2019+",
                    priority=priority if outcome_suffix == "DROPOUT" else "SECONDARY",
                    expected_direction=direction,
                    status="REPLICATION_OR_EXTENSION",
                    claim_ceiling="PLANNING_SIGNAL",
                    mechanism_id="H3_TRABALHO_JUVENIL_MEDIO",
                    effect_scale="outcome percentage points per one exposure standard deviation",
                )
            )

    for exposure, suffix, direction, priority in (
        ("APPRENTICE_SHARE_15_17", "APPRENTICE_SHARE", "negative", "PRIMARY"),
        ("APPRENTICE_ADMISSION_INTENSITY_15_17", "APPRENTICE_ADMISSION", "negative", "PRIMARY"),
        ("LONG_HOURS_SHARE_15_17", "LONG_HOURS", "positive", "PRIMARY"),
        ("SHORT_HOURS_SHARE_15_17", "SHORT_HOURS", "negative", "SECONDARY"),
        ("WEEKLY_HOURS_MEDIAN_15_17", "MEDIAN_HOURS", "positive", "PRIMARY"),
        ("TENURE_MEDIAN_15_17", "TENURE", "ambiguous", "SECONDARY"),
    ):
        for outcome, outcome_suffix in (("DROPOUT_HS", "DROPOUT"), ("DISTORTION_HS", "DISTORTION")):
            append(
                _hypothesis(
                    f"R08_{suffix}_{outcome_suffix}",
                    family_id="R08_WORK_STUDY_COMPATIBILITY",
                    lane="economy_work",
                    exposure=exposure,
                    outcome=outcome,
                    method="PANEL_VALE",
                    window="2019-2025 for RAIS; 2020-2025 for CAGED apprenticeship",
                    priority=priority if outcome_suffix == "DROPOUT" else "SECONDARY",
                    expected_direction=direction,
                    status="NEW_PRETEST",
                    claim_ceiling="PLANNING_SIGNAL",
                    mechanism_id="A2_TRABALHO_PERMANENCIA",
                    effect_scale="outcome percentage points per one exposure standard deviation",
                )
            )

    for hypothesis in (
        _hypothesis(
            "R09_WORKER_INCOMPLETE_EJA_HS",
            family_id="R09_WORKER_SCHOOLING_EJA_EPT",
            lane="economy_work",
            exposure="WORKER_HS_INCOMPLETE_SHARE_18_24",
            outcome="EJA_HS",
            method="PANEL_VALE",
            window="2019-2025",
            priority="PRIMARY",
            expected_direction="positive",
            status="NEW_PRETEST",
            claim_ceiling="DISTRIBUTIONAL_PATTERN",
            mechanism_id="H4_EJA_DISTRIBUICAO",
            effect_scale="EJA log-enrollment change per 10 percentage-point worker-schooling change",
            controls=["POP_18_24"],
        ),
        _hypothesis(
            "R09_WORKER_INCOMPLETE_EPT",
            family_id="R09_WORKER_SCHOOLING_EJA_EPT",
            lane="economy_work",
            exposure="WORKER_HS_INCOMPLETE_SHARE_18_24",
            outcome="EPT_ENROLLMENTS",
            method="SHORT_PANEL_VALE",
            window="2023-2025",
            priority="SECONDARY",
            expected_direction="ambiguous",
            status="NEW_PRETEST",
            claim_ceiling="DISTRIBUTIONAL_PATTERN",
            mechanism_id="A3_OCUPACOES_FORMACAO",
            effect_scale="EPT log-enrollment contrast per 10 percentage-point worker-schooling change",
            pandemic_sensitivity="NOT_APPLICABLE_PREDECLARED",
            controls=["POP_18_24"],
        ),
        _hypothesis(
            "R09_ADULT_HS_WORKER_INCOMPLETE",
            family_id="R09_WORKER_SCHOOLING_EJA_EPT",
            lane="economy_work",
            exposure="ADULT_HS_COMPLETION",
            outcome="WORKER_HS_INCOMPLETE_SHARE_18_24",
            method="CROSS_SECTION_VALE",
            window="2022",
            priority="PRIMARY",
            expected_direction="negative",
            status="REPLICATION_OR_EXTENSION",
            claim_ceiling="DISTRIBUTIONAL_PATTERN",
            mechanism_id="H4_EJA_DISTRIBUICAO",
            effect_scale="Spearman rho",
            pandemic_sensitivity="NOT_APPLICABLE_PREDECLARED_SNAPSHOT",
        ),
    ):
        append(hypothesis)

    for exposure, suffix, direction in (
        ("INDUSTRY_SHARE_CHANGE", "INDUSTRY", "positive"),
        ("LOCAL_DIFFERENTIAL_SHIFT_SHARE", "LOCAL_DIFFERENTIAL", "ambiguous"),
    ):
        append(
            _hypothesis(
                f"R10_{suffix}_EPT_CHANGE",
                family_id="R10_ECONOMIC_STRUCTURE_EPT",
                lane="economy_work",
                exposure=exposure,
                outcome="EPT_ENROLLMENTS",
                method="CHANGE_CROSS_SECTION_VALE",
                window="labor endpoints 2019-2025; EPT change 2023-2025",
                priority="SECONDARY",
                expected_direction=direction,
                status="REPLICATION_OR_EXTENSION",
                claim_ceiling="PLANNING_SIGNAL",
                mechanism_id="A3_OCUPACOES_FORMACAO",
                effect_scale="Spearman rho across ten municipalities",
                pandemic_sensitivity="NOT_APPLICABLE_PREDECLARED_ENDPOINT_CHANGE",
                controls=["POP_18_24"],
            )
        )
    append(
        _hypothesis(
            "R10_COURSE_CBO_CORRESPONDENCE",
            family_id="R10_ECONOMIC_STRUCTURE_EPT",
            lane="economy_work",
            exposure="OCCUPATION_COURSE_BRIDGE_SUPPORT",
            outcome="EPT_ENROLLMENTS",
            method="DESCRIPTIVE_IDENTITY",
            window="2025",
            priority="DESCRIPTIVE",
            expected_direction="not_applicable",
            status="REPLICATION_OR_EXTENSION",
            claim_ceiling="DISTRIBUTIONAL_PATTERN",
            mechanism_id="A3_OCUPACOES_FORMACAO",
            effect_scale="normative correspondence share and transparent bounds",
            pandemic_sensitivity="NOT_APPLICABLE_PREDECLARED_DESCRIPTIVE",
        )
    )

    for outcome, suffix, direction in (
        ("EJA_HS", "EJA", "ambiguous"),
        ("EPT_ENROLLMENTS", "EPT", "positive"),
        ("WORKER_HS_COMPLETE_SHARE_18_24", "WORKER_COMPLETION", "positive"),
    ):
        append(
            _hypothesis(
                f"R17_WAGE_PREMIUM_{suffix}",
                family_id="R17_EDUCATION_WAGE_SIGNAL",
                lane="economy_work",
                exposure="WAGE_PREMIUM_HS_18_24",
                outcome=outcome,
                method="PANEL_VALE" if outcome != "EPT_ENROLLMENTS" else "SHORT_PANEL_VALE",
                window="2019-2025; EPT 2023-2025",
                priority="SECONDARY",
                expected_direction=direction,
                status="NEW_PRETEST",
                claim_ceiling="DISTRIBUTIONAL_PATTERN",
                mechanism_id="A2_TRABALHO_PERMANENCIA",
                effect_scale="outcome change per 10 percent within-year wage-premium ratio change",
                pandemic_sensitivity=("NOT_APPLICABLE_PREDECLARED" if outcome == "EPT_ENROLLMENTS" else "APPLICABLE"),
                controls=["POP_18_24"],
            )
        )

    for exposure, suffix in (
        ("APPRENTICE_ADMISSION_INTENSITY_15_17", "ADMISSION"),
        ("APPRENTICE_SHARE_15_17", "STOCK_SHARE"),
    ):
        for outcome, outcome_suffix, direction in (
            ("EPT_ENROLLMENTS", "EPT", "positive"),
            ("DROPOUT_HS", "DROPOUT", "negative"),
        ):
            append(
                _hypothesis(
                    f"R18_APPRENTICE_{suffix}_{outcome_suffix}",
                    family_id="R18_APPRENTICESHIP_EPT_HIGH_SCHOOL",
                    lane="economy_work",
                    exposure=exposure,
                    outcome=outcome,
                    method="SHORT_PANEL_VALE",
                    window="2023-2025",
                    priority="SECONDARY",
                    expected_direction=direction,
                    status="NEW_PRETEST",
                    claim_ceiling="EXPLORATORY_ASSOCIATION",
                    mechanism_id="A3_OCUPACOES_FORMACAO",
                    effect_scale="standardized short-panel association",
                    pandemic_sensitivity="NOT_APPLICABLE_PREDECLARED",
                    controls=["POP_HS"],
                )
            )

    for exposure, outcome, suffix, direction in (
        ("SOC_POVERTY_SHARE_REGISTERED", "DROPOUT_HS", "POVERTY_DROPOUT", "positive"),
        ("SOC_ZERO_INCOME_SHARE_UPDATED", "DISTORTION_HS", "ZERO_INCOME_DISTORTION", "positive"),
        ("SOC_CHILDREN_PER_POPULATION", "FULLTIME_SHARE_HS", "CHILDREN_FULLTIME", "ambiguous"),
        ("SOC_LOW_INCOME_PER_POPULATION", "EJA_HS", "LOW_INCOME_EJA", "positive"),
    ):
        append(
            _hypothesis(
                f"R11_{suffix}",
                family_id="R11_VULNERABILITY_EDUCATION",
                lane="social_access",
                exposure=exposure,
                outcome=outcome,
                method="CROSS_SECTION_VALE",
                window="December 2024 context with 2024 education outcome",
                priority="PRIMARY",
                expected_direction=direction,
                status="REPLICATION_OR_EXTENSION",
                claim_ceiling="EXPLORATORY_ASSOCIATION",
                mechanism_id="H2_TRAJETORIA_PERMANENCIA",
                effect_scale="Spearman rho",
                pandemic_sensitivity="NOT_APPLICABLE_PREDECLARED_SNAPSHOT",
            )
        )

    for outcome, suffix in (("DROPOUT_HS", "DROPOUT"), ("DISTORTION_HS", "DISTORTION")):
        append(
            _hypothesis(
                f"R12_STATE_RURAL_SHARE_{suffix}",
                family_id="R12_RURALITY_ACCESS",
                lane="social_access",
                exposure="RURAL_SHARE_STATE",
                outcome=outcome,
                method="PANEL_RS",
                window="2019-2025 for distortion; 2018-2025 otherwise",
                priority="SECONDARY",
                expected_direction="ambiguous",
                status="REPLICATION_OR_EXTENSION",
                claim_ceiling="PLANNING_SIGNAL",
                mechanism_id="H1_DEMOGRAFIA_REDE",
                effect_scale="outcome percentage points per 10 percentage-point rural-share change",
                controls=["POP_TOTAL"],
            )
        )
    for stage in ("ALL", "FUNDAMENTAL", "HIGH_SCHOOL", "EJA"):
        for exposure_suffix in ("SCHOOLS", "CLASSES"):
            append(
                _hypothesis(
                    f"R12_{stage}_{exposure_suffix}_ENROLL",
                    family_id="R12_RURALITY_ACCESS",
                    lane="social_access",
                    exposure=f"RURAL_{exposure_suffix}_{stage}",
                    outcome=f"RURAL_ENROLL_{stage}",
                    method="PANEL_VALE",
                    window="2014-2025",
                    priority="PRIMARY" if exposure_suffix == "SCHOOLS" and stage == "ALL" else "SECONDARY",
                    expected_direction="positive",
                    status="REPLICATION_OR_EXTENSION",
                    claim_ceiling="PLANNING_SIGNAL",
                    mechanism_id="H1_DEMOGRAFIA_REDE",
                    effect_scale="within-municipality elasticity",
                )
            )

    for exposure, exposure_suffix in (("AEE_SCHOOLS", "SCHOOLS"), ("AEE_RESOURCE_ROOMS", "ROOMS")):
        for outcome, outcome_suffix in (("AEE_SPECIAL", "SPECIAL"), ("AEE_COMMON", "COMMON"), ("AEE_EXCLUSIVE", "EXCLUSIVE")):
            append(
                _hypothesis(
                    f"R13_{exposure_suffix}_{outcome_suffix}",
                    family_id="R13_AEE_CAPACITY_INCLUSION",
                    lane="social_access",
                    exposure=exposure,
                    outcome=outcome,
                    method="PANEL_VALE",
                    window="2014-2025",
                    priority="PRIMARY" if exposure_suffix == "SCHOOLS" and outcome_suffix == "SPECIAL" else "SECONDARY",
                    expected_direction="positive",
                    status="REPLICATION_OR_EXTENSION",
                    claim_ceiling="PLANNING_SIGNAL",
                    mechanism_id="H2_TRAJETORIA_PERMANENCIA",
                    effect_scale="within-municipality log1p elasticity",
                )
            )

    append(
        _hypothesis(
            "R15_EXECUTOR_NETWORK_FENCE",
            family_id="R15_FINANCE_CAPACITY",
            lane="social_access",
            exposure="FINANCE_MDE_APPLIED_AMOUNT",
            outcome="FULLTIME_SHARE_HS",
            method="DESCRIPTIVE_IDENTITY",
            window="2024-2025 separate-year context",
            priority="BLOCKED",
            expected_direction="not_applicable",
            status="BLOCKED_PRETEST_SCOPE_MISMATCH",
            claim_ceiling="NOT_COMPARABLE",
            mechanism_id="H2_TRAJETORIA_PERMANENCIA",
            effect_scale="not estimated",
            pandemic_sensitivity="NOT_APPLICABLE_PREDECLARED_BLOCKED",
        )
    )
    append(
        _hypothesis(
            "R16_PNATE_RURAL_CONTEXT_ONLY",
            family_id="R16_PNATE_RURAL_CONTEXT",
            lane="social_access",
            exposure="PNATE_PNATE_ADJUSTED_FORECAST",
            outcome="RURAL_ENROLL_ALL",
            method="DESCRIPTIVE_IDENTITY",
            window="2024-2026 administrative records kept by state",
            priority="DESCRIPTIVE",
            expected_direction="not_applicable",
            status="DESCRIPTIVE_ONLY_PRETEST",
            claim_ceiling="DESCRIPTIVE_CONTEXT",
            mechanism_id="H1_DEMOGRAFIA_REDE",
            effect_scale="not estimated",
            pandemic_sensitivity="NOT_APPLICABLE_PREDECLARED_DESCRIPTIVE",
        )
    )

    ids = [row["hypothesisId"] for row in rows]
    if len(ids) != len(set(ids)):
        raise RelationshipAtlasValidationError("Hypothesis IDs duplicados")
    return sorted(rows, key=lambda item: item["hypothesisId"])


def _selector_value_matches(expected: Any, actual: str) -> bool:
    if expected is None:
        return True
    if expected == "*":
        return True
    if isinstance(expected, (list, tuple)):
        return actual in expected
    return actual == expected


def _signature_matches(selector: Mapping[str, Any], signature: Mapping[str, Any]) -> bool:
    if selector["source"] != signature["source"]:
        return False
    if selector["metricId"] != signature["metricId"]:
        return False
    if not _selector_value_matches(selector.get("stage"), signature.get("stage", "")):
        return False
    if signature["source"] == "AA1" and not _selector_value_matches(
        selector.get("dimension"), signature.get("dimension", "")
    ):
        return False
    if signature["source"] == "JOB5I" and not _selector_value_matches(
        selector.get("ageGroup"), signature.get("ageGroup", "")
    ):
        return False
    return all(
        _selector_value_matches(selector.get(selector_key), signature.get(signature_key, ""))
        for selector_key, signature_key in (
            ("coverageScope", "coverageScope"),
            ("territorialLens", "territorialLens"),
            ("networkScope", "networkScope"),
        )
    )


def _iter_variable_selectors(variable: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    if variable.get("selector"):
        yield variable["selector"]
    yield from variable.get("components", [])


def _fallback_disposition(signature: Mapping[str, Any]) -> str:
    metric_id = signature["metricId"]
    dimension = signature.get("dimension", "")
    if metric_id.startswith("finance."):
        return "BLOCKED_GRAIN_SCOPE_TIME"
    if signature["source"] == "JOB5I" and metric_id.startswith("pnate_"):
        return "DESCRIPTIVE_ONLY"
    if metric_id in {
        "pnate_executed_amount",
        "school_transport_students_observed",
    }:
        return "DESCRIPTIVE_ONLY"
    if (
        metric_id.endswith("_observed_count")
        or metric_id.endswith("_active_bonds")
        and "composition" in metric_id
        or "unknown" in dimension.lower()
    ):
        return "DENOMINATOR_OR_QA_ONLY"
    if metric_id in {
        "education.ept_technical_enrollments",
        "education.ept_class_count",
        "labor.occupation_active_bonds",
        "labor.sector_active_bonds",
    } and dimension not in {
        "grain=municipality_total|school=ALL|axis=ALL|course=ALL",
        "ALL",
    }:
        return "DENOMINATOR_OR_QA_ONLY"
    if metric_id.startswith("labor.shift_share."):
        return "DESCRIPTIVE_ONLY"
    if metric_id.startswith("labor.youth_rais.establishment_size_"):
        return "NOT_THEORETICALLY_JUSTIFIED"
    if metric_id.startswith("labor.youth_rais.top4_"):
        return "DESCRIPTIVE_ONLY"
    return "DESCRIPTIVE_ONLY"


def _availability_counts(values: Iterable[str]) -> dict[str, int]:
    counts = Counter(values)
    return {state: int(counts.get(state, 0)) for state in AVAILABILITY_STATES}


def _aa1_signatures(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    signature_columns = (
        "metric_id",
        "stage_or_population_group",
        "dimension_id",
        "coverage_scope",
        "territorial_lens",
        "network_scope",
        "universe",
        "unit",
    )
    grouped: dict[tuple[str, ...], dict[str, Any]] = {}
    row_count = 0
    municipality_codes: set[str] = set()
    all_availability: list[str] = []
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = sorted(set(signature_columns) - set(reader.fieldnames or []))
        if missing:
            raise RelationshipAtlasValidationError(
                f"AA1 sem colunas de assinatura: {missing}"
            )
        for row in reader:
            row_count += 1
            code = row["municipality_ibge_code"]
            if not IBGE_CODE_RE.fullmatch(code):
                raise RelationshipAtlasValidationError(
                    f"Código IBGE AA1 inválido: {code!r}"
                )
            municipality_codes.add(code)
            state = row["availability_state"]
            all_availability.append(state)
            key = tuple(row[column] for column in signature_columns)
            bucket = grouped.setdefault(
                key,
                {
                    "rowCount": 0,
                    "municipalities": set(),
                    "periods": set(),
                    "availability": [],
                },
            )
            bucket["rowCount"] += 1
            bucket["municipalities"].add(code)
            bucket["periods"].add(row["year_or_reference_period"])
            bucket["availability"].append(state)
    signatures: list[dict[str, Any]] = []
    for ordinal, (key, bucket) in enumerate(sorted(grouped.items()), start=1):
        values = dict(zip(signature_columns, key, strict=True))
        signatures.append(
            {
                "signatureId": f"AA1-{ordinal:04d}",
                "source": "AA1",
                "metricId": values["metric_id"],
                "stage": values["stage_or_population_group"],
                "dimension": values["dimension_id"],
                "coverageScope": values["coverage_scope"],
                "territorialLens": values["territorial_lens"],
                "networkScope": values["network_scope"],
                "universe": values["universe"],
                "unit": values["unit"],
                "rowCount": bucket["rowCount"],
                "municipalityCount": len(bucket["municipalities"]),
                "periods": sorted(bucket["periods"]),
                "availabilityCounts": _availability_counts(bucket["availability"]),
            }
        )
    return signatures, {
        "rowCount": row_count,
        "signatureCount": len(signatures),
        "municipalityCount": len(municipality_codes),
        "allMunicipalityCodesTextualSevenDigits": all(
            IBGE_CODE_RE.fullmatch(code) for code in municipality_codes
        ),
        "availabilityCounts": _availability_counts(all_availability),
    }


def _job5i_signatures(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = _load_json(path)
    series = payload["series"]
    grouped: dict[tuple[str, ...], dict[str, Any]] = {}
    municipality_codes: set[str] = set()
    aggregate_entity_ids: set[str] = set()
    all_availability: list[str] = []
    point_count = 0
    for item in series:
        entity_id = item["entityId"]
        if IBGE_CODE_RE.fullmatch(entity_id):
            municipality_codes.add(entity_id)
        else:
            aggregate_entity_ids.add(entity_id)
        key = (
            item["metricId"],
            item.get("educationalStage", ""),
            item.get("ageGroup", ""),
            item["territorialLens"],
            item["networkScope"],
            item["offerUniverse"],
            item["unit"],
        )
        bucket = grouped.setdefault(
            key,
            {
                "seriesCount": 0,
                "entities": set(),
                "years": set(),
                "availability": [],
            },
        )
        bucket["seriesCount"] += 1
        bucket["entities"].add(entity_id)
        for point in item["points"]:
            point_count += 1
            bucket["years"].add(str(point["year"]))
            state = point["availabilityState"]
            bucket["availability"].append(state)
            all_availability.append(state)
    signatures: list[dict[str, Any]] = []
    for ordinal, (key, bucket) in enumerate(sorted(grouped.items()), start=1):
        metric, stage, age, lens, network, offer, unit = key
        signatures.append(
            {
                "signatureId": f"JOB5I-{ordinal:03d}",
                "source": "JOB5I",
                "metricId": metric,
                "stage": stage,
                "ageGroup": age,
                "coverageScope": "VALE_10_WITH_AGGREGATES",
                "territorialLens": lens,
                "networkScope": network,
                "offerUniverse": offer,
                "unit": unit,
                "seriesCount": bucket["seriesCount"],
                "entityCount": len(bucket["entities"]),
                "periods": sorted(bucket["years"]),
                "availabilityCounts": _availability_counts(bucket["availability"]),
            }
        )
    return signatures, {
        "seriesCount": len(series),
        "pointCount": point_count,
        "signatureCount": len(signatures),
        "municipalityCount": len(municipality_codes),
        "aggregateEntityIds": sorted(aggregate_entity_ids),
        "allMunicipalityCodesTextualSevenDigits": all(
            IBGE_CODE_RE.fullmatch(code) for code in municipality_codes
        ),
        "availabilityCounts": _availability_counts(all_availability),
    }


def _classify_signatures(
    signatures: Sequence[dict[str, Any]],
    variables: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    classified: list[dict[str, Any]] = []
    for signature in signatures:
        matches: list[tuple[int, str, str]] = []
        for variable in variables:
            if any(
                _signature_matches(selector, signature)
                for selector in _iter_variable_selectors(variable)
            ):
                disposition = variable["disposition"]
                matches.append(
                    (
                        DISPOSITION_PRIORITY[disposition],
                        disposition,
                        variable["variableId"],
                    )
                )
        if matches:
            max_priority = max(item[0] for item in matches)
            top = [item for item in matches if item[0] == max_priority]
            disposition = sorted(top, key=lambda item: (item[1], item[2]))[0][1]
            variable_ids = sorted({item[2] for item in matches})
            reason = "matched_predeclared_analytic_variable"
        else:
            disposition = _fallback_disposition(signature)
            variable_ids = []
            reason = "deterministic_fallback_policy"
        classified.append(
            {
                **signature,
                "disposition": disposition,
                "matchedVariableIds": variable_ids,
                "dispositionReason": reason,
            }
        )
    return classified


def build_overlap_mapping() -> dict[str, Any]:
    mappings = [
        ("education.age_grade_distortion_rate_percent", "age_grade_distortion_rate_percent", "EXACT_METRIC_DIFFERENT_BUNDLE"),
        ("education.approval_rate_percent", "approval_rate_percent", "EXACT_METRIC_DIFFERENT_BUNDLE"),
        ("education.dropout_rate_percent", "dropout_rate_percent", "EXACT_METRIC_DIFFERENT_BUNDLE"),
        ("education.failure_rate_percent", "failure_rate_percent", "EXACT_METRIC_DIFFERENT_BUNDLE"),
        ("education.teacher_adequacy_percent", "teacher_adequacy_percent", "EXACT_METRIC_DIFFERENT_BUNDLE"),
        ("education.enrollments", "located_enrollments", "SEMANTIC_MATCH_STAGE_MAPPING_REQUIRED"),
        ("education.full_time_enrollments", "matriculas_tempo_integral", "SEMANTIC_MATCH_STAGE_MAPPING_REQUIRED"),
        ("education.full_time_enrollments", "percentual_tempo_integral", "DERIVED_SHARE_IN_JOB5I"),
        ("education.schools_with_internet", "schools_with_internet_percent", "COUNT_VS_DERIVED_SHARE"),
        ("education.schools_with_internet", "schools_with_broadband_percent", "RELATED_NOT_DUPLICATE"),
        ("demography.population_age_6_10", "resident_population", "STAGE_MAPPING_REQUIRED"),
        ("demography.population_age_11_14", "resident_population", "STAGE_MAPPING_REQUIRED"),
        ("demography.population_age_15_17", "resident_population", "STAGE_MAPPING_REQUIRED"),
        ("education.eja_enrollments", "fundamental", "EJA_STAGE_MAPPING_REQUIRED"),
        ("education.eja_enrollments", "high_school", "EJA_STAGE_MAPPING_REQUIRED"),
        ("education.ept_technical_enrollments", "technical_enrollments", "MUNICIPAL_TOTAL_MATCH"),
        ("education.rural.rural_enrollments", "rural_enrollments", "STAGE_MAPPING_REQUIRED"),
        ("education.rural.rural_schools", "rural_schools", "STAGE_MAPPING_REQUIRED"),
        ("education.rural.rural_classes", "rural_classes", "STAGE_MAPPING_REQUIRED"),
        ("education.special_aee.special_enrollments", "special_enrollments", "MUNICIPAL_TOTAL_MATCH"),
        ("education.special_aee.schools_offering_aee", "schools_offering_aee", "MUNICIPAL_TOTAL_MATCH"),
        ("labor.youth_rais.active_bonds", "total", "AGE_MAPPING_REQUIRED"),
    ]
    return {
        "schemaVersion": "vocacoes-pne-aa1-job5i-overlap-v1",
        "canonicalAnalyticalSource": "AA1_WHEN_SEMANTICALLY_EQUIVALENT",
        "uniqueJob5iAnalyticalAdditions": [
            "apprentice_admissions",
            "caged_youth_admissions",
            "caged_youth_balance",
            "residents_studying_other_municipality_share",
            "pnate_administrative_context",
        ],
        "deduplicationPolicy": "A hypothesis may use one canonical representation only. Job5i is retained as QA/presentation source when AA1 is the controlling analytical series.",
        "mappings": [
            {
                "aa1MetricId": aa1,
                "job5iMetricId": job5i,
                "relationship": relationship,
                "independentHypothesisAllowed": relationship in {
                    "RELATED_NOT_DUPLICATE",
                },
            }
            for aa1, job5i, relationship in mappings
        ],
        "mappingCount": len(mappings),
    }


def _identification_audit(contract: Mapping[str, Any]) -> dict[str, Any]:
    common_failures = [
        "no_exogenous_assignment_or_rule",
        "time_varying_unobserved_confounding_remains_plausible",
        "ecological_aggregate_data_no_same_person_link",
    ]
    records = []
    for family in contract["familyRegistry"]:
        family_id = family["familyId"]
        failures = list(common_failures)
        if family_id in {"R15_FINANCE_CAPACITY", "R16_PNATE_RURAL_CONTEXT"}:
            failures.append("executor_network_or_temporal_scope_mismatch")
        if family_id in {"R06_ADULT_SCHOOLING_TRAJECTORY", "R11_VULNERABILITY_EDUCATION", "R14_EDUCATIONAL_MOBILITY_OFFER"}:
            failures.append("single_cross_section_no_pretrend")
        if family_id in {"R10_ECONOMIC_STRUCTURE_EPT", "R18_APPRENTICESHIP_EPT_HIGH_SCHOOL"}:
            failures.append("ten_municipalities_and_short_or_endpoint_window")
        records.append(
            {
                "familyId": family_id,
                "identificationState": "NO_DEFENSIBLE_CAUSAL_IDENTIFICATION",
                "causalClaimAllowed": False,
                "theoryMayRaiseCeiling": False,
                "failedRequirements": failures,
                "maximumLanguage": family["entryCeiling"],
            }
        )
    return {
        "schemaVersion": "vocacoes-pne-identification-audit-v1",
        "auditTiming": "FROZEN_BEFORE_NEW_MODEL_RESULTS",
        "familyCount": len(records),
        "causalFamilyCount": 0,
        "conclusion": "Nenhuma família dispõe de experimento, regra exógena, instrumento válido, descontinuidade ou adoção escalonada defensável. Teoria orienta mecanismo, mas não identifica efeito causal.",
        "records": records,
    }


def _current_promotions_audit(
    contract: Mapping[str, Any], bundle_path: Path
) -> dict[str, Any]:
    bundle = _load_json(bundle_path)
    readings = bundle["scopeVariants"]["region"]["readings"]
    decisions = {
        "demografia-matriculas-rede": (
            "RETAIN_PRIMARY_ACCOUNTING_WITH_ROBUST_SUPPORT",
            "A decomposição fecha contabilmente e o apoio demográfico estadual é robusto; o lead placebo impede linguagem de precedência ou causa.",
        ),
        "trajetoria-contexto": (
            "DEMOTE_TO_VISIBLE_NEGATIVE_BOUNDARY",
            "O próprio check é not_confirmed; não é uma relação promovível, embora o resultado nulo seja útil.",
        ),
        "transformacao-economica-ept": (
            "DEMOTE_TO_WATCH_SUPPORTING",
            "O sinal regional não passou o q pré-definido e não pode ocupar o mesmo nível de uma associação robusta.",
        ),
        "escolaridade-adulta-eja": (
            "DEMOTE_TO_VISIBLE_NEGATIVE_BOUNDARY",
            "A relação não passou o gate anterior e a amostra Vale tem baixa potência.",
        ),
        "trabalho-juvenil-permanencia": (
            "DEMOTE_TO_VISIBLE_NEGATIVE_BOUNDARY",
            "A relação não passou o gate anterior; não rejeição não prova ausência de mecanismo.",
        ),
    }
    records = []
    for reading in readings:
        reading_id = reading["id"]
        if reading_id not in decisions:
            raise RelationshipAtlasValidationError(
                f"Leitura pública não registrada na reauditoria: {reading_id}"
            )
        decision, rationale = decisions[reading_id]
        records.append(
            {
                "readingId": reading_id,
                "currentAnalysisStatus": reading["analysisCheck"]["status"],
                "currentEvidenceKind": reading["evidenceClass"]["kind"],
                "gateDecision": decision,
                "rationale": rationale,
                "causalLanguageAllowed": False,
            }
        )
    expected = set(contract["currentPromotionIds"])
    actual = {record["readingId"] for record in records}
    if actual != expected:
        raise RelationshipAtlasValidationError(
            f"Reauditoria incompleta: expected={sorted(expected)} actual={sorted(actual)}"
        )
    return {
        "schemaVersion": "vocacoes-pne-current-promotions-audit-v1",
        "auditTiming": "BEFORE_NEW_MODEL_RESULTS",
        "readingCount": len(records),
        "primaryRetentionCount": sum(
            record["gateDecision"].startswith("RETAIN_PRIMARY") for record in records
        ),
        "demotionCount": sum(
            record["gateDecision"].startswith("DEMOTE") for record in records
        ),
        "records": sorted(records, key=lambda item: item["readingId"]),
    }


def _input_records(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    records = []
    for item in contract["inputs"]:
        path = REPO_ROOT / item["path"]
        if not path.is_file():
            raise RelationshipAtlasValidationError(
                f"Input ausente: {item['inputId']} -> {path}"
            )
        records.append(
            {
                **item,
                "sha256": sha256_file(path),
                "byteSize": path.stat().st_size,
            }
        )
    records.extend(
        [
            {
                "inputId": "RELATIONSHIP_ATLAS_CONTRACT",
                "path": str(CONTRACT_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
                "sha256": sha256_file(CONTRACT_PATH),
                "byteSize": CONTRACT_PATH.stat().st_size,
            },
            {
                "inputId": "RELATIONSHIP_ATLAS_MODULE",
                "path": str(MODULE_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
                "sha256": sha256_file(MODULE_PATH),
                "byteSize": MODULE_PATH.stat().st_size,
            },
        ]
    )
    return sorted(records, key=lambda item: item["inputId"])


def _region_registry_quality(path: Path) -> dict[str, Any]:
    payload = _load_json(path)
    mapping: dict[str, str] = {}
    for region in payload["regions"]:
        for code in region["municipalityIbgeCodes"]:
            if code in mapping:
                raise RelationshipAtlasValidationError(
                    f"Código em duas regiões: {code}"
                )
            if not IBGE_CODE_RE.fullmatch(code):
                raise RelationshipAtlasValidationError(
                    f"Código regional inválido: {code}"
                )
            mapping[code] = region["slug"]
    return {
        "schemaVersion": payload["schemaVersion"],
        "regionCount": len(payload["regions"]),
        "municipalityCount": len(mapping),
        "completeUniqueRs497Mapping": len(mapping) == 497,
        "leaveOneRegionOutAvailable": len(mapping) == 497,
    }


def build_pretest_package() -> dict[str, Any]:
    contract = _load_json(CONTRACT_PATH)
    variables = build_analytic_variables()
    hypotheses = build_hypotheses()
    input_by_id = {
        item["inputId"]: REPO_ROOT / item["path"] for item in contract["inputs"]
    }
    aa1_signatures, aa1_quality = _aa1_signatures(input_by_id["AA1_PANEL"])
    job5i_signatures, job5i_quality = _job5i_signatures(
        input_by_id["JOB5I_SERIES"]
    )
    signatures = _classify_signatures(
        [*aa1_signatures, *job5i_signatures], variables
    )
    dispositions = Counter(item["disposition"] for item in signatures)
    variable_signature_match_counts = {
        variable["variableId"]: sum(
            1
            for signature in signatures
            if any(
                _signature_matches(selector, signature)
                for selector in _iter_variable_selectors(variable)
            )
        )
        for variable in variables
    }
    unmatched_variable_ids = sorted(
        variable_id
        for variable_id, count in variable_signature_match_counts.items()
        if count == 0
    )
    variable_ids = {variable["variableId"] for variable in variables}
    dangling = sorted(
        {
            variable_id
            for row in hypotheses
            for variable_id in (
                row["exposureVariableId"],
                row["outcomeVariableId"],
                *row["controls"],
            )
            if variable_id not in variable_ids
        }
    )
    if dangling:
        raise RelationshipAtlasValidationError(
            f"Hipóteses referenciam variáveis ausentes: {dangling}"
        )
    family_ids = {family["familyId"] for family in contract["familyRegistry"]}
    hypothesis_family_ids = {row["familyId"] for row in hypotheses}
    if family_ids != hypothesis_family_ids:
        raise RelationshipAtlasValidationError(
            f"Famílias divergentes: contract={sorted(family_ids)} matrix={sorted(hypothesis_family_ids)}"
        )
    overlap = build_overlap_mapping()
    identification = _identification_audit(contract)
    current_promotions = _current_promotions_audit(
        contract, input_by_id["CURRENT_OFFICIAL_ADVANCED_BUNDLE"]
    )
    region_quality = _region_registry_quality(input_by_id["RS_REGION_REGISTRY"])
    observation_contract = _load_json(input_by_id["AA1_OBSERVATION_CONTRACT"])[
        "observationContract"
    ]
    quality = {
        "schemaVersion": "vocacoes-pne-relationship-atlas-qa-v1",
        "state": "PASS",
        "classification": contract["classification"],
        "sourceSignatureCount": len(signatures),
        "expectedSourceSignatureCount": 3267,
        "allSourceSignaturesDisposedExactlyOnce": len(signatures) == 3267,
        "dispositionCounts": {
            state: int(dispositions.get(state, 0))
            for state in contract["signatureDispositions"]
        },
        "unknownDispositionCount": sum(
            count
            for state, count in dispositions.items()
            if state not in set(contract["signatureDispositions"])
        ),
        "aa1": aa1_quality,
        "job5i": job5i_quality,
        "availabilityStateContract": {
            "requiredStates": list(AVAILABILITY_STATES),
            "aa1Counts": aa1_quality["availabilityCounts"],
            "job5iCounts": job5i_quality["availabilityCounts"],
            "zeroCountStatesExplicit": True,
            "denominatorZeroProducesNull": observation_contract[
                "denominatorZeroProducesNull"
            ],
        },
        "identity": {
            "aa1AllTextualSevenDigits": aa1_quality[
                "allMunicipalityCodesTextualSevenDigits"
            ],
            "job5iAllMunicipalTextualSevenDigits": job5i_quality[
                "allMunicipalityCodesTextualSevenDigits"
            ],
            "nameJoinUsedByThisStage": False,
        },
        "regions": region_quality,
        "analyticVariableCount": len(variables),
        "analyticVariableSignatureMatchCounts": variable_signature_match_counts,
        "unmatchedAnalyticVariableIds": unmatched_variable_ids,
        "allAnalyticVariablesResolveToSourceSignatures": not unmatched_variable_ids,
        "hypothesisCount": len(hypotheses),
        "familyCount": len(family_ids),
        "allHypothesisVariablesResolved": not dangling,
        "allFamiliesRepresented": family_ids == hypothesis_family_ids,
        "causalFamilyCount": identification["causalFamilyCount"],
        "currentPromotionAuditCount": current_promotions["readingCount"],
        "publicDataWritten": False,
        "networkUsed": False,
        "databaseUsed": False,
        "fullBuildUsed": False,
    }
    if not all(
        (
            quality["allSourceSignaturesDisposedExactlyOnce"],
            quality["unknownDispositionCount"] == 0,
            aa1_quality["signatureCount"] == 3189,
            job5i_quality["signatureCount"] == 78,
            aa1_quality["municipalityCount"] == 497,
            quality["identity"]["aa1AllTextualSevenDigits"],
            quality["identity"]["job5iAllMunicipalTextualSevenDigits"],
            region_quality["completeUniqueRs497Mapping"],
            quality["allAnalyticVariablesResolveToSourceSignatures"],
            observation_contract["denominatorZeroProducesNull"],
            identification["causalFamilyCount"] == 0,
        )
    ):
        quality["state"] = "FAIL"
        raise RelationshipAtlasValidationError(
            "QA pré-teste falhou: " + json.dumps(quality, ensure_ascii=False)
        )
    inputs = _input_records(contract)
    return {
        "contract": contract,
        "inputs": inputs,
        "signatures": signatures,
        "variables": variables,
        "overlap": overlap,
        "hypotheses": hypotheses,
        "identification": identification,
        "currentPromotions": current_promotions,
        "quality": quality,
    }


def _artifact_records(output_dir: Path, names: Sequence[str]) -> list[dict[str, Any]]:
    return [
        {
            "path": name,
            "sha256": sha256_file(output_dir / name),
            "byteSize": (output_dir / name).stat().st_size,
        }
        for name in names
    ]


def _artifact_set_digest(records: Sequence[Mapping[str, Any]]) -> str:
    payload = "\n".join(
        f"{record['path']}:{record['sha256']}:{record['byteSize']}"
        for record in sorted(records, key=lambda item: item["path"])
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def materialize_candidate(output_dir: Path) -> dict[str, Any]:
    package = build_pretest_package()
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        output_dir / "SOURCE_SIGNATURE_DISPOSITIONS.json",
        {
            "schemaVersion": "vocacoes-pne-source-signature-dispositions-v1",
            "signatureCount": len(package["signatures"]),
            "records": package["signatures"],
        },
    )
    _write_json(
        output_dir / "ANALYTIC_VARIABLES.json",
        {
            "schemaVersion": "vocacoes-pne-analytic-variables-v1",
            "variableCount": len(package["variables"]),
            "variables": package["variables"],
        },
    )
    _write_json(output_dir / "OVERLAP_MAPPING.json", package["overlap"])
    _write_json(
        output_dir / "HYPOTHESIS_MATRIX.json",
        {
            "schemaVersion": "vocacoes-pne-hypothesis-matrix-v1",
            "state": "FROZEN_BEFORE_NEW_MODEL_RESULTS",
            "contractPath": str(CONTRACT_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
            "inputHashes": package["inputs"],
            "methodPresets": package["contract"]["methodPresets"],
            "multiplicity": package["contract"]["multiplicity"],
            "promotionGate": package["contract"]["promotionGate"],
            "nominalValuePolicy": package["contract"]["nominalValuePolicy"],
            "hypothesisCount": len(package["hypotheses"]),
            "hypotheses": package["hypotheses"],
        },
    )
    _write_json(output_dir / "IDENTIFICATION_AUDIT.json", package["identification"])
    _write_json(
        output_dir / "CURRENT_PROMOTIONS_AUDIT.json", package["currentPromotions"]
    )
    _write_json(output_dir / "QA_SUMMARY.json", package["quality"])
    pre_freeze_names = PACKAGE_FILES[:7]
    pre_freeze_records = _artifact_records(output_dir, pre_freeze_names)
    freeze = {
        "schemaVersion": "vocacoes-pne-relationship-atlas-freeze-v1",
        "state": "FROZEN_BEFORE_NEW_MODEL_RESULTS",
        "classification": "DATA_LOGIC",
        "hypothesisMatrixSha256": sha256_file(output_dir / "HYPOTHESIS_MATRIX.json"),
        "sourceSignatureDispositionsSha256": sha256_file(
            output_dir / "SOURCE_SIGNATURE_DISPOSITIONS.json"
        ),
        "analyticVariablesSha256": sha256_file(
            output_dir / "ANALYTIC_VARIABLES.json"
        ),
        "identificationAuditSha256": sha256_file(
            output_dir / "IDENTIFICATION_AUDIT.json"
        ),
        "currentPromotionsAuditSha256": sha256_file(
            output_dir / "CURRENT_PROMOTIONS_AUDIT.json"
        ),
        "inputSetDigestSha256": _artifact_set_digest(package["inputs"]),
        "preFreezeArtifactSetDigestSha256": _artifact_set_digest(pre_freeze_records),
        "postResultAdjustmentAllowed": False,
    }
    _write_json(output_dir / "FREEZE.json", freeze)
    artifact_names = PACKAGE_FILES[:-1]
    records = _artifact_records(output_dir, artifact_names)
    manifest = {
        "schemaVersion": "vocacoes-pne-relationship-atlas-manifest-v1",
        "programId": "vocacoes-pne-relationship-atlas-v1",
        "state": "PRETEST_UNIVERSE_AND_HYPOTHESES_FROZEN",
        "classification": "DATA_LOGIC",
        "counts": {
            "sourceSignatureCount": package["quality"]["sourceSignatureCount"],
            "analyticVariableCount": package["quality"]["analyticVariableCount"],
            "hypothesisCount": package["quality"]["hypothesisCount"],
            "familyCount": package["quality"]["familyCount"],
            "currentPromotionAuditCount": package["quality"]["currentPromotionAuditCount"],
            "causalFamilyCount": package["quality"]["causalFamilyCount"],
        },
        "inputs": package["inputs"],
        "artifacts": records,
        "artifactSetDigestSha256": _artifact_set_digest(records),
        "generation": {
            "deterministic": True,
            "manifestWrittenLast": True,
            "networkUsed": False,
            "databaseUsed": False,
            "publicDataWritten": False,
            "fullBuildUsed": False,
        },
    }
    _write_json(output_dir / "MANIFEST.json", manifest)
    return manifest


def validate_existing_output(output_dir: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    missing = [name for name in PACKAGE_FILES if not (output_dir / name).is_file()]
    if missing:
        raise RelationshipAtlasValidationError(
            f"Pacote pré-teste incompleto: {missing}"
        )
    manifest = _load_json(output_dir / "MANIFEST.json")
    if manifest["state"] != "PRETEST_UNIVERSE_AND_HYPOTHESES_FROZEN":
        raise RelationshipAtlasValidationError("Estado do manifesto inválido")
    records = _artifact_records(output_dir, PACKAGE_FILES[:-1])
    if records != manifest["artifacts"]:
        raise RelationshipAtlasValidationError("Hashes de artefatos divergiram")
    if _artifact_set_digest(records) != manifest["artifactSetDigestSha256"]:
        raise RelationshipAtlasValidationError("Digest do conjunto divergiu")
    freeze = _load_json(output_dir / "FREEZE.json")
    expected_hashes = {
        "hypothesisMatrixSha256": sha256_file(output_dir / "HYPOTHESIS_MATRIX.json"),
        "sourceSignatureDispositionsSha256": sha256_file(
            output_dir / "SOURCE_SIGNATURE_DISPOSITIONS.json"
        ),
        "analyticVariablesSha256": sha256_file(
            output_dir / "ANALYTIC_VARIABLES.json"
        ),
        "identificationAuditSha256": sha256_file(
            output_dir / "IDENTIFICATION_AUDIT.json"
        ),
        "currentPromotionsAuditSha256": sha256_file(
            output_dir / "CURRENT_PROMOTIONS_AUDIT.json"
        ),
    }
    for field, expected in expected_hashes.items():
        if freeze[field] != expected:
            raise RelationshipAtlasValidationError(
                f"Freeze divergiu em {field}"
            )
    for input_record in manifest["inputs"]:
        path = REPO_ROOT / input_record["path"]
        if sha256_file(path) != input_record["sha256"]:
            raise RelationshipAtlasValidationError(
                f"Input mudou após freeze: {input_record['inputId']}"
            )
    qa = _load_json(output_dir / "QA_SUMMARY.json")
    if qa["state"] != "PASS":
        raise RelationshipAtlasValidationError("QA não está em PASS")
    return manifest


def materialize_transactionally(
    output_dir: Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="relationship-atlas-prereg-", dir=output_dir.parent
    ) as temporary:
        candidate = Path(temporary) / "candidate"
        candidate_manifest = materialize_candidate(candidate)
        validate_existing_output(candidate)
        if output_dir.exists():
            existing_manifest = validate_existing_output(output_dir)
            if (
                existing_manifest["artifactSetDigestSha256"]
                != candidate_manifest["artifactSetDigestSha256"]
            ):
                raise RelationshipAtlasValidationError(
                    "Freeze existente diverge do candidato; ajuste pós-resultado é proibido"
                )
            return existing_manifest
        os.replace(candidate, output_dir)
    return validate_existing_output(output_dir)


def materialize_twice_and_freeze(
    output_dir: Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="relationship-atlas-determinism-", dir=output_dir.parent
    ) as temporary:
        first = Path(temporary) / "first"
        second = Path(temporary) / "second"
        first_manifest = materialize_candidate(first)
        second_manifest = materialize_candidate(second)
        validate_existing_output(first)
        validate_existing_output(second)
        if (
            first_manifest["artifactSetDigestSha256"]
            != second_manifest["artifactSetDigestSha256"]
        ):
            raise RelationshipAtlasValidationError(
                "Duas materializações independentes divergiram"
            )
        if output_dir.exists():
            existing = validate_existing_output(output_dir)
            if (
                existing["artifactSetDigestSha256"]
                != first_manifest["artifactSetDigestSha256"]
            ):
                raise RelationshipAtlasValidationError(
                    "Freeze existente diverge do candidato; ajuste pós-resultado é proibido"
                )
            return existing
        shutil.move(str(first), str(output_dir))
    return validate_existing_output(output_dir)
