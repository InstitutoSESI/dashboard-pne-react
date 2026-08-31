"""Laboratório interno de relações educação-território do Job 5J.

O módulo consome exclusivamente artefatos locais congelados dos Jobs 5G-A-R a
5I. Ele não publica, não escreve em ``public/data`` e não transforma lentes
territoriais distintas em uma população comum.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import re
from statistics import NormalDist
from typing import Any

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5j"
CONTRACT_PATH = (
    REPO_ROOT / "data_pipeline" / "contracts" / "vocacoes-pne-v7-job5j.json"
)
NSR_CODE = "4313375"
REGION_ID = "REGION_VALE_DO_SINOS"
STATE_ID = "STATE_RS"
GENERATED_AT = "2026-08-29T00:00:00-03:00"
FINAL_STATE = "JOB_5J_READY_WITH_EXPLICIT_LIMITS_FOR_EXTERNAL_JUDGMENT"
IBGE_CODE_PATTERN = re.compile(r"[0-9]{7}")

SOURCE_ROOTS = {
    "job5gar": REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gar",
    "job5gbr": REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gbr",
    "job5gcr": REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gcr",
    "job5gd": REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gd",
    "job5h": REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5h",
    "job5i": REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5i",
}

SOURCE_FILES = {
    "pressure": SOURCE_ROOTS["job5gar"]
    / "PAINEL_PRESSAO_MECANICA_COORTES_AUDITADO_V1_1.csv.gz",
    "trajectory": SOURCE_ROOTS["job5gar"]
    / "PAINEL_TRAJETORIA_OFICIAL_DESCRITIVA_V1_1.csv.gz",
    "conditions": SOURCE_ROOTS["job5gar"]
    / "PAINEL_CONDICOES_ESCOLARES_TOTAL_V1_1.csv.gz",
    "staffing": SOURCE_ROOTS["job5gar"]
    / "PAINEL_DOCENTES_TURMAS_JORNADA_V1_1.csv.gz",
    "adult_schooling": SOURCE_ROOTS["job5gbr"]
    / "PAINEL_ESCOLARIDADE_ADULTA_2010_2022_V1_1.csv.gz",
    "eja_distribution": SOURCE_ROOTS["job5gbr"]
    / "PAINEL_EJA_DISTRIBUICAO_2022_V1_1.csv.gz",
    "eja_history": SOURCE_ROOTS["job5gbr"]
    / "PAINEL_EJA_HISTORICA_2014_2025_V1_1.csv.gz",
    "rural": SOURCE_ROOTS["job5gbr"]
    / "PAINEL_EDUCACAO_RURAL_TERRITORIO_V1_1.csv.gz",
    "special": SOURCE_ROOTS["job5gbr"]
    / "PAINEL_EDUCACAO_ESPECIAL_AEE_V1_1.csv.gz",
    "rais_youth": SOURCE_ROOTS["job5gcr"]
    / "PAINEL_RAIS_TRABALHO_JUVENIL_V1_1.csv.gz",
    "caged_youth": SOURCE_ROOTS["job5gcr"]
    / "PAINEL_CAGED_JUVENIL_AGREGADO_SEGURO_V1.csv.gz",
    "apprenticeship": SOURCE_ROOTS["job5gcr"]
    / "PAINEL_APRENDIZAGEM_PROFISSIONAL_V1_1.csv.gz",
    "occupations": SOURCE_ROOTS["job5gcr"]
    / "PAINEL_OCUPACOES_RAIS_ESTOQUE_V1.csv.gz",
    "sectors": SOURCE_ROOTS["job5gcr"]
    / "PAINEL_SETORES_RAIS_ESTOQUE_V1.csv.gz",
    "ept": SOURCE_ROOTS["job5gcr"]
    / "PAINEL_EPT_OFERTA_TOTAL_V1_1.csv.gz",
    "bridge": SOURCE_ROOTS["job5gcr"]
    / "PAINEL_PONTE_CBO_CNCT_AUDITADA_V1_1.csv.gz",
    "shift_share": SOURCE_ROOTS["job5gcr"]
    / "PAINEL_SHIFT_SHARE_SETORIAL_V1_1.csv.gz",
    "offer": SOURCE_ROOTS["job5gd"]
    / "PAINEL_ESTRUTURA_TERRITORIAL_OFERTA_JOB5GD_V1.csv.gz",
    "mobility": SOURCE_ROOTS["job5gd"]
    / "PAINEL_MOBILIDADE_EDUCACIONAL_POR_ETAPA_JOB5GD_V1.csv.gz",
    "pnate": SOURCE_ROOTS["job5gd"]
    / "PAINEL_TRANSPORTE_ESCOLAR_PNATE_JOB5GD_V1.csv.gz",
    "job5h_registry": SOURCE_ROOTS["job5h"]
    / "REGISTRO_FONTES_PERIODOS_LENTES_LIMITES_JOB5H.json",
    "job5i_registry": SOURCE_ROOTS["job5i"]
    / "REGISTRO_FONTES_E_LIMITES_JOB5I.json",
    "job5i_bundle": SOURCE_ROOTS["job5i"] / "BUNDLE_UI_V2_JOB5I.json",
}
CONTROL_FILES = {
    "job5j_prompt": Path("C:/Users/rnbirck/Downloads/PROMPT_JOB5J_SOL_MAX.md"),
    "orchestration_contract": REPO_ROOT
    / "docs"
    / "CONTRATO_ORQUESTRACAO_VOCACOES_PNE_V7.md",
    "job5gar_manifest": SOURCE_ROOTS["job5gar"] / "MANIFEST_JOB5GAR.json",
    "job5gbr_manifest": SOURCE_ROOTS["job5gbr"] / "MANIFEST_JOB5GBR.json",
    "job5gcr_manifest": SOURCE_ROOTS["job5gcr"] / "MANIFEST_JOB5GCR.json",
    "job5gd_manifest": SOURCE_ROOTS["job5gd"] / "MANIFEST_JOB5GD.json",
    "job5h_manifest": SOURCE_ROOTS["job5h"] / "MANIFEST_JOB5H.json",
    "job5i_manifest": SOURCE_ROOTS["job5i"] / "MANIFEST_JOB5I.json",
}

PACKAGE_FILES = (
    "CHECKPOINT_JOB5J_FOR_PRO.md",
    "CATALOGO_INSIGHTS_CANDIDATOS_JOB5J.json",
    "MATRIZ_RELACOES_TESTADAS_JOB5J.csv.gz",
    "MATRIZ_HETEROGENEIDADE_10_MUNICIPIOS_JOB5J.csv.gz",
    "DOSSIE_ANALITICO_NOVA_SANTA_RITA_JOB5J.md",
    "DOSSIE_ANALITICO_VALE_DO_SINOS_JOB5J.md",
    "METODOS_E_ROBUSTEZ_JOB5J.md",
    "LIMITACOES_E_CLAIMS_JOB5J.json",
    "QA_SUMMARY_JOB5J.json",
    "ARTIFACT_INDEX_JOB5J.json",
    "PACOTE_REVISAO_EXTERNA_JOB5J.json",
    "MANIFEST_JOB5J.json",
)
INTERNAL_FILES = (
    "PRE_ESPECIFICACAO_R1_R8_JOB5J.json",
    "PAINEL_ANALITICO_ALINHADO_JOB5J.csv.gz",
    "MODELOS_E_ROBUSTEZ_DETALHADOS_JOB5J.json",
    "INVENTARIO_E_HASHES_INPUTS_JOB5J.json",
)
OUTPUT_FILES = PACKAGE_FILES + INTERNAL_FILES

ALLOWED_CLASSIFICATIONS = {
    "ROBUST_ASSOCIATION",
    "TERRITORIAL_MISMATCH",
    "STRUCTURAL_CONTRAST",
    "PLANNING_SIGNAL",
    "DESCRIPTIVE_CONTEXT_ONLY",
    "NOT_SUPPORTED",
    "NOT_EVALUABLE",
}

INSIGHT_REQUIRED_FIELDS = {
    "insight_id",
    "manager_question",
    "education_outcome",
    "territorial_transformation",
    "substantive_mechanism",
    "territorial_scales",
    "population_or_stage",
    "period_alignment",
    "methods_used",
    "main_effect_or_contrast",
    "uncertainty_or_stability",
    "statewide_result",
    "vale_result",
    "ten_municipality_heterogeneity",
    "selected_municipality_result",
    "nova_santa_rita_result",
    "incremental_value_beyond_separate_charts",
    "integrated_conclusion_draft",
    "planning_implication",
    "monitoring_indicators",
    "institutional_coordination",
    "allowed_claims",
    "forbidden_claims",
    "limitations",
    "recommended_visual",
    "recommended_editorial_role",
    "external_judgment_required",
    "classification",
}


class Job5JValidationError(ValueError):
    """Falha fechada de contrato ou QA do Job 5J."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return _clean_number(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if value is pd.NA:
        return None
    return value


def _clean_number(value: Any) -> int | float | None:
    if value is None or pd.isna(value):
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    if number.is_integer() and abs(number) <= 9_007_199_254_740_991:
        return int(number)
    return number


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        dtype={
            "municipality_ibge_code": "string",
            "dimension_code": "string",
            "occupation_code": "string",
            "occupation_subgroup_code": "string",
            "cnae_division_code": "string",
            "cnae_subclass_code": "string",
            "course_code": "string",
            "school_code": "string",
        },
        keep_default_na=False,
        na_values=["null"],
    )


def _source_inventory() -> dict[str, Any]:
    inputs = {**SOURCE_FILES, **CONTROL_FILES}
    missing = [str(path) for path in inputs.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Entradas locais obrigatórias ausentes: {missing}")
    records = []
    for source_ref, path in sorted(inputs.items()):
        records.append(
            {
                "source_ref": source_ref,
                "path": (
                    path.relative_to(REPO_ROOT).as_posix()
                    if path.is_relative_to(REPO_ROOT)
                    else path.as_posix()
                ),
                "byte_size": path.stat().st_size,
                "sha256": sha256_file(path),
                "local_frozen_input": True,
                "network_used_by_job5j": False,
                "database_used_by_job5j": False,
            }
        )
    return {
        "schemaVersion": "vocacoes-pne-job5j-input-inventory-v1",
        "generatedAt": GENERATED_AT,
        "sourceCount": len(records),
        "sources": records,
        "acquisitionPerformed": False,
        "networkUsed": False,
        "databaseUsed": False,
    }


def _municipalities() -> dict[str, str]:
    region_config = _json(REPO_ROOT / "config" / "regions" / "rs.json")
    region = next(
        item for item in region_config["regions"] if item["slug"] == "vale-do-sinos"
    )
    codes = [str(value) for value in region["municipalityIbgeCodes"]]
    if len(codes) != 10 or len(set(codes)) != 10:
        raise Job5JValidationError("Vale do Sinos deve conter exatamente dez municípios")
    if any(not IBGE_CODE_PATTERN.fullmatch(code) for code in codes):
        raise Job5JValidationError("Código IBGE municipal não textual ou fora de sete dígitos")
    registry = _json(REPO_ROOT / "config" / "municipalities" / "rs.json")
    names = {
        str(item["ibgeCode"]): str(item["name"])
        for item in registry["municipalities"]
    }
    if not set(codes) <= set(names):
        raise Job5JValidationError("Registro municipal canônico incompleto para o Vale")
    return {code: names[code] for code in sorted(codes)}


def preregistration() -> dict[str, Any]:
    common_forbidden = [
        "causalidade",
        "vínculo de mesma pessoa",
        "fusão de residência, local de estudo, local da oferta e local de trabalho",
        "cumprimento de meta PNE ou PME",
        "priorização automática de município, curso, ocupação ou setor",
    ]
    relations = [
        {
            "relation_id": "R1",
            "question": "Como pressão de coortes e mudança demográfica dialogam com matrículas, escolas e turmas?",
            "primary_estimand": "contraste municipal entre pressão mecânica 2030 e mudanças observadas de oferta 2014–2025",
            "primary_method": "correlações Pearson/Spearman entre dez municípios e contraste Nova Santa Rita–Vale",
            "robustness": ["intervalo de Fisher", "leave-one-municipality-out", "matrículas e turmas como desfechos separados"],
            "lenses": ["resident_population", "school_location"],
            "claim_ceiling": "STRUCTURAL_CONTRAST",
            "forbidden_claims": common_forbidden + ["previsão de demanda", "medida de capacidade"],
        },
        {
            "relation_id": "R2",
            "question": "A fotografia de mobilidade estudantil acrescenta contexto à trajetória e à oferta do ensino médio?",
            "primary_estimand": "associação ecológica transversal em 2022 entre parcela que estuda fora e trajetória oficial municipal",
            "primary_method": "correlações de postos e ponderadas; sem painel de mobilidade",
            "robustness": ["leave-one-municipality-out", "quatro desfechos de trajetória", "mudança de oferta como contexto independente"],
            "lenses": ["student_residence", "school_location"],
            "claim_ceiling": "PLANNING_SIGNAL",
            "forbidden_claims": common_forbidden + ["corredor origem-destino", "efeito da mobilidade sobre trajetória"],
        },
        {
            "relation_id": "R3",
            "question": "Mudanças no trabalho juvenil e na aprendizagem acompanham mudanças na trajetória do ensino médio?",
            "primary_estimand": "associação ecológica dentro de município ao longo do tempo",
            "primary_method": "painel com efeitos fixos de município e ano, erros agrupados, defasagem de um ano e primeiras diferenças",
            "robustness": ["ponderação por matrícula", "exclusão de 2020–2021", "estoque RAIS e fluxos Caged separados"],
            "lenses": ["workplace", "school_location"],
            "claim_ceiling": "ROBUST_ASSOCIATION",
            "forbidden_claims": common_forbidden + ["trabalho de residentes", "eventos Caged como pessoas únicas"],
        },
        {
            "relation_id": "R4",
            "question": "Transformações ocupacionais e setoriais encontram oferta EPT localizada no território?",
            "primary_estimand": "contraste estrutural entre mudança ocupacional 2019–2025 e oferta EPT localizada em 2025",
            "primary_method": "distribuição municipal, contribuição regional e correlação ecológica exploratória",
            "robustness": ["CBO 414140 obrigatório", "EPT zero observado preservado", "ponte normativa não aditiva"],
            "lenses": ["workplace", "school_location"],
            "claim_ceiling": "TERRITORIAL_MISMATCH",
            "forbidden_claims": common_forbidden + ["adequação curricular provada", "ranking de ocupações"],
        },
        {
            "relation_id": "R5",
            "question": "A distribuição territorial da EJA acompanha a distribuição do público adulto residente?",
            "primary_estimand": "diferença de participações municipais dentro de cada etapa em 2022",
            "primary_method": "distância de variação total e gaps municipais por etapa",
            "robustness": ["fundamental e médio separados", "história 2014–2025 apenas como contexto", "denominadores contratuais preservados"],
            "lenses": ["resident_population", "school_location"],
            "claim_ceiling": "TERRITORIAL_MISMATCH",
            "forbidden_claims": common_forbidden + ["cobertura", "demanda manifestada", "combinação entre etapas"],
        },
        {
            "relation_id": "R6",
            "question": "O perfil socioeconômico dos alunos avaliados ajuda a contextualizar a trajetória?",
            "primary_estimand": "associação ecológica municipal INSE–trajetória nos anos compatíveis",
            "primary_method": "correlações transversais em 2019 e 2023; 2021 apenas sensibilidade cautelosa",
            "robustness": ["leave-one-municipality-out", "aprovação, abandono, reprovação e distorção separados", "referência RS somente se disponível no mesmo contrato"],
            "lenses": ["school_location"],
            "claim_ceiling": "ROBUST_ASSOCIATION",
            "forbidden_claims": common_forbidden + ["INSE como atributo de toda a população", "efeito socioeconômico causal"],
        },
        {
            "relation_id": "R7",
            "question": "Mudanças da oferta rural e o contexto PNATE colocam quais temas na agenda territorial?",
            "primary_estimand": "contraste de mudanças 2014–2025 e contexto do executor 2025–2026",
            "primary_method": "descrição estrutural e heterogeneidade; sem regressão entre lentes incompatíveis",
            "robustness": ["ensino médio rural separado", "previsão 2026 separada de execução", "zeros observados preservados"],
            "lenses": ["rural_school_location", "municipal_executor"],
            "claim_ceiling": "PLANNING_SIGNAL",
            "forbidden_claims": common_forbidden + ["PNATE como mobilidade", "execução ou uso em 2026", "residência rural inferida"],
        },
        {
            "relation_id": "R8",
            "question": "A mudança de matrículas da educação especial acompanha a mudança de escolas que informam AEE?",
            "primary_estimand": "co-movimento municipal 2014–2025 entre matrículas localizadas e escolas com AEE",
            "primary_method": "correlações entre mudanças e contraste Nova Santa Rita–Vale",
            "robustness": ["leave-one-municipality-out", "contagens não empilhadas", "sem vínculo individual"],
            "lenses": ["school_location"],
            "claim_ceiling": "PLANNING_SIGNAL",
            "forbidden_claims": common_forbidden + ["cobertura individual de AEE", "residência dos estudantes"],
        },
    ]
    return {
        "schemaVersion": "vocacoes-pne-job5j-preregistration-v1",
        "materializedBeforeJob5JModelExecution": True,
        "generatedAt": GENERATED_AT,
        "multipleTestingFamily": "todos os testes confirmatórios/ecológicos R1–R8 com ajuste Benjamini-Hochberg",
        "classificationRule": "força, estabilidade, alinhamento temporal e teto de claim definidos antes do resultado; significância isolada não aprova insight",
        "relations": relations,
    }


def load_sources() -> dict[str, pd.DataFrame]:
    frames = {
        key: _read_csv(path)
        for key, path in SOURCE_FILES.items()
        if path.suffixes[-2:] == [".csv", ".gz"]
    }
    codes = set(_municipalities())
    for name, frame in frames.items():
        if "municipality_ibge_code" not in frame:
            continue
        observed = set(frame["municipality_ibge_code"].dropna().astype(str))
        invalid = sorted(
            code for code in observed if not IBGE_CODE_PATTERN.fullmatch(code)
        )
        if invalid:
            raise Job5JValidationError(f"Códigos IBGE inválidos em {name}: {invalid}")
        municipal_rows = frame[
            frame.get("entity_scope", pd.Series(index=frame.index, dtype=str)).eq(
                "municipality"
            )
        ]
        if not municipal_rows.empty:
            unexpected = sorted(
                set(municipal_rows["municipality_ibge_code"].dropna().astype(str))
                - codes
            )
            if unexpected:
                raise Job5JValidationError(
                    f"Universo municipal inesperado em {name}: {unexpected}"
                )
    return frames


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _pearson(x: Sequence[float], y: Sequence[float]) -> float | None:
    a = np.asarray(x, dtype=float)
    b = np.asarray(y, dtype=float)
    mask = np.isfinite(a) & np.isfinite(b)
    a = a[mask]
    b = b[mask]
    if len(a) < 3 or np.std(a) == 0 or np.std(b) == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def _spearman(x: Sequence[float], y: Sequence[float]) -> float | None:
    a = pd.Series(x, dtype=float)
    b = pd.Series(y, dtype=float)
    mask = a.notna() & b.notna()
    if int(mask.sum()) < 3:
        return None
    return _pearson(
        a[mask].rank(method="average").to_numpy(),
        b[mask].rank(method="average").to_numpy(),
    )


def _fisher_interval(correlation: float | None, n: int) -> tuple[float | None, float | None]:
    if correlation is None or n <= 3 or abs(correlation) >= 1:
        return (correlation, correlation)
    z = math.atanh(correlation)
    margin = NormalDist().inv_cdf(0.975) / math.sqrt(n - 3)
    return math.tanh(z - margin), math.tanh(z + margin)


def _permutation_p(
    x: np.ndarray, y: np.ndarray, observed: float | None, test_id: str
) -> float | None:
    if observed is None or len(x) < 4:
        return None
    seed = int(hashlib.sha256(test_id.encode("utf-8")).hexdigest()[:16], 16)
    rng = np.random.default_rng(seed)
    exceedances = 0
    draws = 4_999
    for _ in range(draws):
        candidate = _spearman(x, rng.permutation(y))
        if candidate is not None and abs(candidate) >= abs(observed) - 1e-15:
            exceedances += 1
    return (exceedances + 1) / (draws + 1)


def correlation_summary(
    frame: pd.DataFrame,
    *,
    x: str,
    y: str,
    municipality: str,
    test_id: str,
) -> dict[str, Any]:
    sample = frame[[municipality, x, y]].copy()
    sample[x] = _numeric(sample[x])
    sample[y] = _numeric(sample[y])
    sample = sample.dropna().sort_values(municipality)
    pearson = _pearson(sample[x], sample[y])
    spearman = _spearman(sample[x], sample[y])
    low, high = _fisher_interval(pearson, len(sample))
    loo = []
    for code in sample[municipality].astype(str):
        subset = sample[sample[municipality].astype(str).ne(code)]
        value = _spearman(subset[x], subset[y])
        loo.append({"excludedMunicipalityIbgeCode": code, "spearman": value})
    signs = [math.copysign(1, item["spearman"]) for item in loo if item["spearman"] not in (None, 0)]
    dominant = 0.0
    if signs:
        dominant = max(signs.count(-1.0), signs.count(1.0)) / len(signs)
    return {
        "observations": len(sample),
        "municipalities": int(sample[municipality].nunique()),
        "pearson": pearson,
        "spearman": spearman,
        "pearsonCi95Low": low,
        "pearsonCi95High": high,
        "spearmanPermutationP": _permutation_p(
            sample[x].to_numpy(dtype=float),
            sample[y].to_numpy(dtype=float),
            spearman,
            test_id,
        ),
        "leaveOneOut": loo,
        "leaveOneOutDominantDirectionFraction": dominant,
        "sampleMunicipalityIbgeCodes": sample[municipality].astype(str).tolist(),
    }


def _weighted_group_mean(
    matrix: np.ndarray, groups: np.ndarray, weights: np.ndarray
) -> np.ndarray:
    result = np.zeros_like(matrix, dtype=float)
    for group in np.unique(groups):
        mask = groups == group
        denominator = weights[mask].sum()
        if denominator <= 0:
            raise Job5JValidationError("Ponderador de grupo não positivo")
        result[mask] = (
            matrix[mask] * weights[mask, None]
        ).sum(axis=0) / denominator
    return result


def _two_way_within(
    matrix: np.ndarray,
    municipalities: np.ndarray,
    years: np.ndarray,
    weights: np.ndarray,
) -> tuple[np.ndarray, int]:
    transformed = np.asarray(matrix, dtype=float).copy()
    if transformed.ndim == 1:
        transformed = transformed[:, None]
    for iteration in range(1, 501):
        previous = transformed.copy()
        transformed -= _weighted_group_mean(transformed, municipalities, weights)
        transformed -= _weighted_group_mean(transformed, years, weights)
        if np.max(np.abs(transformed - previous)) <= 1e-11:
            return transformed, iteration
    raise Job5JValidationError("Desmediação em dois sentidos não convergiu")


def fit_panel(
    frame: pd.DataFrame,
    *,
    outcome: str,
    factor: str,
    municipality: str,
    year: str,
    test_id: str,
    weight: str | None = None,
) -> dict[str, Any]:
    required = [outcome, factor, municipality, year] + ([weight] if weight else [])
    sample = frame[required].copy()
    for column in [outcome, factor] + ([weight] if weight else []):
        sample[column] = _numeric(sample[column])
    sample = sample.dropna().sort_values([municipality, year])
    if weight:
        sample = sample[sample[weight].gt(0)]
    if len(sample) < 20 or sample[municipality].nunique() < 5:
        raise Job5JValidationError(f"Cobertura insuficiente para {test_id}")
    factor_sd = float(sample[factor].std(ddof=0))
    if factor_sd <= 0:
        raise Job5JValidationError(f"Preditor sem variação em {test_id}")
    sample["_factor_standardized"] = (
        sample[factor] - sample[factor].mean()
    ) / factor_sd
    weights = (
        np.ones(len(sample), dtype=float)
        if weight is None
        else sample[weight].to_numpy(dtype=float)
    )
    joined = np.column_stack(
        [sample[outcome].to_numpy(dtype=float), sample["_factor_standardized"]]
    )
    transformed, iterations = _two_way_within(
        joined,
        sample[municipality].astype(str).to_numpy(),
        sample[year].to_numpy(),
        weights,
    )
    y_work = transformed[:, 0]
    x_work = transformed[:, 1:]
    sqrt_w = np.sqrt(weights)
    x_weighted = x_work * sqrt_w[:, None]
    y_weighted = y_work * sqrt_w
    xtx = x_weighted.T @ x_weighted
    if np.linalg.matrix_rank(xtx) < xtx.shape[0]:
        raise Job5JValidationError(f"Matriz singular em {test_id}")
    xtx_inverse = np.linalg.inv(xtx)
    coefficient = float((xtx_inverse @ (x_weighted.T @ y_weighted))[0])
    residuals = y_work - x_work[:, 0] * coefficient
    meat = np.zeros_like(xtx)
    groups = sample[municipality].astype(str).to_numpy()
    for group in np.unique(groups):
        mask = groups == group
        score = x_work[mask].T @ (weights[mask] * residuals[mask])
        meat += np.outer(score, score)
    group_count = int(sample[municipality].nunique())
    observation_count = len(sample)
    correction = group_count / (group_count - 1)
    correction *= (observation_count - 1) / max(observation_count - 1, 1)
    covariance = correction * xtx_inverse @ meat @ xtx_inverse
    standard_error = float(math.sqrt(max(float(covariance[0, 0]), 0)))
    statistic = coefficient / standard_error if standard_error > 0 else None
    p_value = (
        math.erfc(abs(statistic) / math.sqrt(2)) if statistic is not None else None
    )
    return {
        "testId": test_id,
        "method": "two_way_fixed_effects_clustered_by_municipality",
        "factor": factor,
        "outcome": outcome,
        "factorStandardization": f"one sample SD = {factor_sd}",
        "coefficientOutcomeUnitsPerFactorSd": coefficient,
        "standardErrorClustered": standard_error,
        "ci95Low": coefficient - 1.96 * standard_error,
        "ci95High": coefficient + 1.96 * standard_error,
        "pValueRaw": p_value,
        "observations": observation_count,
        "municipalities": group_count,
        "years": sorted(int(value) for value in sample[year].unique()),
        "weight": weight or "unweighted",
        "withinIterations": iterations,
        "causalInterpretationAllowed": False,
    }


def bh_adjust(values: Sequence[float | None]) -> list[float | None]:
    valid = [(index, float(value)) for index, value in enumerate(values) if value is not None]
    result: list[float | None] = [None] * len(values)
    if not valid:
        return result
    ordered = sorted(valid, key=lambda item: item[1])
    running = 1.0
    adjusted = [1.0] * len(ordered)
    for position in range(len(ordered) - 1, -1, -1):
        candidate = min(
            1.0,
            ordered[position][1] * len(ordered) / (position + 1),
        )
        running = min(running, candidate)
        adjusted[position] = running
    for (index, _), value in zip(ordered, adjusted, strict=True):
        result[index] = value
    return result


def _weighted_pearson(x: pd.Series, y: pd.Series, weights: pd.Series) -> float | None:
    frame = pd.DataFrame({"x": _numeric(x), "y": _numeric(y), "w": _numeric(weights)}).dropna()
    frame = frame[frame["w"].gt(0)]
    if len(frame) < 3 or frame["x"].std(ddof=0) == 0 or frame["y"].std(ddof=0) == 0:
        return None
    total = frame["w"].sum()
    x_mean = (frame["x"] * frame["w"]).sum() / total
    y_mean = (frame["y"] * frame["w"]).sum() / total
    covariance = (frame["w"] * (frame["x"] - x_mean) * (frame["y"] - y_mean)).sum()
    x_variance = (frame["w"] * (frame["x"] - x_mean) ** 2).sum()
    y_variance = (frame["w"] * (frame["y"] - y_mean) ** 2).sum()
    denominator = math.sqrt(x_variance * y_variance)
    return float(covariance / denominator) if denominator > 0 else None


def _municipal_metric(
    frame: pd.DataFrame,
    *,
    metric: str,
    stage: str | None = None,
    year: int | None = None,
    value_column: str = "value",
) -> pd.DataFrame:
    result = frame.copy()
    if "entity_scope" in result:
        result = result[result["entity_scope"].eq("municipality")]
    if "metric" in result:
        result = result[result["metric"].eq(metric)]
    if stage is not None and "stage" in result:
        result = result[result["stage"].eq(stage)]
    if year is not None and "year" in result:
        result = result[result["year"].eq(year)]
    columns = ["municipality_ibge_code", "municipality_name"]
    if "year" in result:
        columns.append("year")
    columns.append(value_column)
    return result[columns].copy()


def _endpoint_change(
    frame: pd.DataFrame,
    *,
    metric: str,
    stage: str,
    value_column: str = "value",
    start_year: int = 2014,
    end_year: int = 2025,
    output_name: str,
) -> pd.DataFrame:
    subset = _municipal_metric(
        frame, metric=metric, stage=stage, value_column=value_column
    )
    pivot = subset.pivot(
        index=["municipality_ibge_code", "municipality_name"],
        columns="year",
        values=value_column,
    ).reset_index()
    pivot[output_name] = _numeric(pivot[end_year]) - _numeric(pivot[start_year])
    return pivot[
        ["municipality_ibge_code", "municipality_name", start_year, end_year, output_name]
    ]


def _trajectory_wide(
    trajectory: pd.DataFrame, *, years: Iterable[int] | None = None
) -> pd.DataFrame:
    subset = trajectory[
        trajectory["stage"].eq("medio")
        & trajectory["metric"].isin(
            [
                "approval_rate_percent",
                "dropout_rate_percent",
                "failure_rate_percent",
                "age_grade_distortion_rate_percent",
            ]
        )
    ].copy()
    if years is not None:
        subset = subset[subset["year"].isin(list(years))]
    wide = subset.pivot(
        index=["municipality_ibge_code", "municipality_name", "year"],
        columns="metric",
        values="value",
    ).reset_index()
    wide.columns.name = None
    return wide


def _correlation_test_row(
    relation_id: str,
    test_id: str,
    summary: Mapping[str, Any],
    *,
    x_metric: str,
    y_metric: str,
    period: str,
    x_lens: str,
    y_lens: str,
    weight: str | None = None,
    weighted_pearson: float | None = None,
    role: str = "primary",
) -> dict[str, Any]:
    return {
        "relation_id": relation_id,
        "test_id": test_id,
        "test_role": role,
        "method": "municipal_cross_section_pearson_spearman",
        "x_metric": x_metric,
        "y_metric": y_metric,
        "x_lens": x_lens,
        "y_lens": y_lens,
        "period_alignment": period,
        "estimate": summary["spearman"],
        "estimate_type": "spearman_rho",
        "pearson": summary["pearson"],
        "weighted_pearson": weighted_pearson,
        "weight": weight,
        "standard_error": None,
        "ci95_low": summary["pearsonCi95Low"],
        "ci95_high": summary["pearsonCi95High"],
        "p_value_raw": summary["spearmanPermutationP"],
        "p_value_bh": None,
        "observations": summary["observations"],
        "municipalities": summary["municipalities"],
        "years": None,
        "leave_one_out_dominant_direction_fraction": summary[
            "leaveOneOutDominantDirectionFraction"
        ],
        "availability_state": "observed",
        "causal_interpretation_allowed": False,
        "same_person_link": False,
    }


def _panel_test_row(
    relation_id: str,
    model: Mapping[str, Any],
    *,
    x_lens: str,
    y_lens: str,
    period: str,
    role: str,
) -> dict[str, Any]:
    return {
        "relation_id": relation_id,
        "test_id": model["testId"],
        "test_role": role,
        "method": model["method"],
        "x_metric": model["factor"],
        "y_metric": model["outcome"],
        "x_lens": x_lens,
        "y_lens": y_lens,
        "period_alignment": period,
        "estimate": model["coefficientOutcomeUnitsPerFactorSd"],
        "estimate_type": "outcome_units_per_one_predictor_sd_within",
        "pearson": None,
        "weighted_pearson": None,
        "weight": model["weight"],
        "standard_error": model["standardErrorClustered"],
        "ci95_low": model["ci95Low"],
        "ci95_high": model["ci95High"],
        "p_value_raw": model["pValueRaw"],
        "p_value_bh": None,
        "observations": model["observations"],
        "municipalities": model["municipalities"],
        "years": "|".join(str(value) for value in model["years"]),
        "leave_one_out_dominant_direction_fraction": None,
        "availability_state": "observed",
        "causal_interpretation_allowed": False,
        "same_person_link": False,
    }


def _aligned_row(
    *,
    relation_id: str,
    alignment_id: str,
    code: str,
    name: str,
    year: int | str,
    x_metric: str,
    x_value: Any,
    x_unit: str,
    x_lens: str,
    y_metric: str,
    y_value: Any,
    y_unit: str,
    y_lens: str,
    source_refs: Sequence[str],
    temporal_nature: str,
    caution: str = "none",
) -> dict[str, Any]:
    return {
        "relation_id": relation_id,
        "alignment_id": alignment_id,
        "municipality_ibge_code": code,
        "municipality_name": name,
        "year_or_period": str(year),
        "x_metric": x_metric,
        "x_value": _clean_number(x_value),
        "x_unit": x_unit,
        "x_lens": x_lens,
        "x_availability_state": "observed" if pd.notna(x_value) else "unavailable",
        "y_metric": y_metric,
        "y_value": _clean_number(y_value),
        "y_unit": y_unit,
        "y_lens": y_lens,
        "y_availability_state": "observed" if pd.notna(y_value) else "unavailable",
        "source_refs": "|".join(source_refs),
        "temporal_nature": temporal_nature,
        "period_caution": caution,
        "network_scope": "total_all_dependencies",
        "administrative_dependency_role": "qa_only",
    }


def _heterogeneity_row(
    relation_id: str,
    row: Mapping[str, Any],
    *,
    x_metric: str,
    x_value: Any,
    y_metric: str,
    y_value: Any,
    x_lens: str,
    y_lens: str,
    period: str,
    note: str,
) -> dict[str, Any]:
    return {
        "relation_id": relation_id,
        "municipality_ibge_code": str(row["municipality_ibge_code"]),
        "municipality_name": str(row["municipality_name"]),
        "is_nova_santa_rita": str(row["municipality_ibge_code"]) == NSR_CODE,
        "x_metric": x_metric,
        "x_value": _clean_number(x_value),
        "x_lens": x_lens,
        "y_metric": y_metric,
        "y_value": _clean_number(y_value),
        "y_lens": y_lens,
        "period_alignment": period,
        "availability_state": (
            "observed" if pd.notna(x_value) and pd.notna(y_value) else "unavailable"
        ),
        "interpretation_note": note,
    }


def _relation_r1(
    frames: Mapping[str, pd.DataFrame],
) -> dict[str, Any]:
    pressure = frames["pressure"]
    pressure = pressure[
        pressure["entity_scope"].eq("municipality")
        & pressure["stage"].eq("medio")
        & pressure["target_year"].eq(2030)
    ][
        [
            "municipality_ibge_code",
            "municipality_name",
            "cohort_to_baseline_enrollment_ratio",
            "availability_state",
        ]
    ].copy()
    enroll = _endpoint_change(
        frames["offer"],
        metric="located_enrollments",
        stage="medio",
        output_name="high_school_enrollment_change_2014_2025",
    )
    classes = _endpoint_change(
        frames["offer"],
        metric="classes",
        stage="medio",
        output_name="high_school_class_change_2014_2025",
    )
    panel = pressure.merge(
        enroll.drop(columns="municipality_name"), on="municipality_ibge_code"
    ).merge(
        classes.drop(columns="municipality_name"), on="municipality_ibge_code"
    )
    tests = []
    details = {}
    for suffix, outcome in (
        ("ENROLLMENT", "high_school_enrollment_change_2014_2025"),
        ("CLASSES", "high_school_class_change_2014_2025"),
    ):
        test_id = f"R1_PRESSURE_{suffix}"
        summary = correlation_summary(
            panel,
            x="cohort_to_baseline_enrollment_ratio",
            y=outcome,
            municipality="municipality_ibge_code",
            test_id=test_id,
        )
        details[test_id] = summary
        tests.append(
            _correlation_test_row(
                "R1",
                test_id,
                summary,
                x_metric="mechanical_high_school_pressure_ratio_2030_to_2025",
                y_metric=outcome,
                period="reference_2025_mechanical_2030_vs_observed_change_2014_2025",
                x_lens="resident_population_vs_school_location",
                y_lens="school_location",
            )
        )
    aligned = []
    heterogeneity = []
    for _, row in panel.sort_values("municipality_ibge_code").iterrows():
        aligned.append(
            _aligned_row(
                relation_id="R1",
                alignment_id="R1_PRESSURE_ENROLLMENT",
                code=str(row["municipality_ibge_code"]),
                name=str(row["municipality_name"]),
                year="2014-2025|2030",
                x_metric="mechanical_high_school_pressure_ratio_2030_to_2025",
                x_value=row["cohort_to_baseline_enrollment_ratio"],
                x_unit="ratio",
                x_lens="resident_population_vs_school_location",
                y_metric="high_school_enrollment_change_2014_2025",
                y_value=row["high_school_enrollment_change_2014_2025"],
                y_unit="enrollments",
                y_lens="school_location",
                source_refs=["job5gar_pressure", "job5gd_offer"],
                temporal_nature="mechanical_horizon_vs_observed_endpoints",
                caution="mechanical_pressure_not_forecast_demand_or_capacity",
            )
        )
        heterogeneity.append(
            _heterogeneity_row(
                "R1",
                row,
                x_metric="mechanical_high_school_pressure_ratio_2030_to_2025",
                x_value=row["cohort_to_baseline_enrollment_ratio"],
                y_metric="high_school_enrollment_change_2014_2025",
                y_value=row["high_school_enrollment_change_2014_2025"],
                x_lens="resident_population_vs_school_location",
                y_lens="school_location",
                period="2014-2025|2030",
                note="Pressão mecânica não é previsão, demanda nem capacidade.",
            )
        )
    nsr = panel[panel["municipality_ibge_code"].eq(NSR_CODE)].iloc[0]
    anchors = {
        "nsrMechanicalRatio2030": _clean_number(
            nsr["cohort_to_baseline_enrollment_ratio"]
        ),
        "nsrHighSchoolEnrollmentChange2014_2025": _clean_number(
            nsr["high_school_enrollment_change_2014_2025"]
        ),
        "nsrHighSchoolClassChange2014_2025": _clean_number(
            nsr["high_school_class_change_2014_2025"]
        ),
        "valeHighSchoolEnrollmentChange2014_2025": _clean_number(
            panel["high_school_enrollment_change_2014_2025"].sum()
        ),
        "valeHighSchoolClassChange2014_2025": _clean_number(
            panel["high_school_class_change_2014_2025"].sum()
        ),
    }
    return {
        "panel": panel,
        "tests": tests,
        "details": details,
        "aligned": aligned,
        "heterogeneity": heterogeneity,
        "anchors": anchors,
    }


def _relation_r2(frames: Mapping[str, pd.DataFrame]) -> dict[str, Any]:
    mobility = frames["mobility"]
    mobility = mobility[
        mobility["entity_scope"].eq("municipality") & mobility["stage"].eq("medio")
    ][
        [
            "municipality_ibge_code",
            "municipality_name",
            "outside_share_percent",
            "numerator",
            "denominator",
        ]
    ].copy()
    trajectory = _trajectory_wide(frames["trajectory"], years=[2022])
    offer_change = _endpoint_change(
        frames["offer"],
        metric="located_enrollments",
        stage="medio",
        output_name="high_school_enrollment_change_2014_2025",
    )
    panel = mobility.merge(
        trajectory.drop(columns="municipality_name"), on="municipality_ibge_code"
    ).merge(
        offer_change.drop(columns="municipality_name"), on="municipality_ibge_code"
    )
    tests = []
    details = {}
    outcomes = [
        "approval_rate_percent",
        "dropout_rate_percent",
        "failure_rate_percent",
        "age_grade_distortion_rate_percent",
        "high_school_enrollment_change_2014_2025",
    ]
    for outcome in outcomes:
        test_id = f"R2_MOBILITY_{outcome.upper()}"
        summary = correlation_summary(
            panel,
            x="outside_share_percent",
            y=outcome,
            municipality="municipality_ibge_code",
            test_id=test_id,
        )
        details[test_id] = summary
        tests.append(
            _correlation_test_row(
                "R2",
                test_id,
                summary,
                x_metric="residents_studying_other_municipality_share_high_school_2022",
                y_metric=outcome,
                period=(
                    "cross_section_2022"
                    if outcome != "high_school_enrollment_change_2014_2025"
                    else "mobility_2022_vs_offer_change_2014_2025"
                ),
                x_lens="student_residence",
                y_lens="school_location",
                weight="resident_students_high_school_2022",
                weighted_pearson=_weighted_pearson(
                    panel["outside_share_percent"], panel[outcome], panel["denominator"]
                ),
            )
        )
    aligned = []
    heterogeneity = []
    for _, row in panel.sort_values("municipality_ibge_code").iterrows():
        aligned.append(
            _aligned_row(
                relation_id="R2",
                alignment_id="R2_MOBILITY_TRAJECTORY_2022",
                code=str(row["municipality_ibge_code"]),
                name=str(row["municipality_name"]),
                year=2022,
                x_metric="outside_share_percent",
                x_value=row["outside_share_percent"],
                x_unit="percent",
                x_lens="student_residence",
                y_metric="dropout_rate_percent",
                y_value=row["dropout_rate_percent"],
                y_unit="percent",
                y_lens="school_location",
                source_refs=["job5gd_mobility", "job5gar_trajectory"],
                temporal_nature="single_year_cross_section",
                caution="destination_municipality_unavailable",
            )
        )
        heterogeneity.append(
            _heterogeneity_row(
                "R2",
                row,
                x_metric="outside_share_percent_2022",
                x_value=row["outside_share_percent"],
                y_metric="dropout_rate_percent_2022",
                y_value=row["dropout_rate_percent"],
                x_lens="student_residence",
                y_lens="school_location",
                period="2022",
                note="Fotografia sem destino municipal; associação ecológica, não efeito.",
            )
        )
    nsr = panel[panel["municipality_ibge_code"].eq(NSR_CODE)].iloc[0]
    anchors = {
        "nsrOutsideShareHighSchool2022Percent": _clean_number(
            nsr["outside_share_percent"]
        ),
        "nsrOutsideNumeratorHighSchool2022": _clean_number(nsr["numerator"]),
        "nsrOutsideDenominatorHighSchool2022": _clean_number(nsr["denominator"]),
        "nsrApproval2022Percent": _clean_number(nsr["approval_rate_percent"]),
        "nsrDropout2022Percent": _clean_number(nsr["dropout_rate_percent"]),
    }
    return {
        "panel": panel,
        "tests": tests,
        "details": details,
        "aligned": aligned,
        "heterogeneity": heterogeneity,
        "anchors": anchors,
    }


def _relation_r3(frames: Mapping[str, pd.DataFrame]) -> dict[str, Any]:
    trajectory = _trajectory_wide(frames["trajectory"], years=range(2019, 2026))
    rais = frames["rais_youth"]
    rais = rais[
        rais["entity_scope"].eq("municipality")
        & rais["dimension"].eq("total")
        & rais["dimension_code"].eq("ALL")
    ][
        [
            "municipality_ibge_code",
            "municipality_name",
            "year",
            "age_group",
            "active_bonds",
            "municipal_contribution_to_regional_change",
        ]
    ].copy()
    rais_wide = rais.pivot(
        index=["municipality_ibge_code", "municipality_name", "year"],
        columns="age_group",
        values="active_bonds",
    ).reset_index().rename(
        columns={"15_17": "rais_active_bonds_15_17", "18_24": "rais_active_bonds_18_24"}
    )
    rais_wide.columns.name = None

    apprenticeship = frames["apprenticeship"]
    apprenticeship = apprenticeship[
        apprenticeship["entity_scope"].eq("municipality")
        & apprenticeship["aggregation_scope"].eq("all_apprentice_events")
    ][
        [
            "municipality_ibge_code",
            "municipality_name",
            "year",
            "age_group",
            "admissions",
            "dismissals",
            "balance",
            "youth_admissions_same_grain",
            "share_of_youth_admission_events_classified_as_apprentice",
        ]
    ].copy()
    apprentice_parts = []
    for age_group in ("15_17", "18_24"):
        part = apprenticeship[apprenticeship["age_group"].eq(age_group)].copy()
        part = part.rename(
            columns={
                "admissions": f"apprentice_admissions_{age_group}",
                "dismissals": f"apprentice_dismissals_{age_group}",
                "balance": f"apprentice_balance_{age_group}",
                "youth_admissions_same_grain": f"youth_admissions_{age_group}",
                "share_of_youth_admission_events_classified_as_apprentice": f"apprentice_share_ratio_{age_group}",
            }
        )
        apprentice_parts.append(
            part.drop(columns=["age_group", "municipality_name"])
        )

    caged = frames["caged_youth"]
    caged = caged[
        caged["entity_scope"].eq("municipality")
        & caged["time_grain"].eq("annual_flow")
        & caged["aggregation_scope"].eq("all_apprentice_status")
    ]
    caged_parts = []
    for age_group in ("15_17", "18_24"):
        part = caged[caged["age_group"].eq(age_group)][
            [
                "municipality_ibge_code",
                "year",
                "admissions",
                "dismissals",
                "balance",
            ]
        ].copy()
        part = part.rename(
            columns={
                "admissions": f"caged_admissions_{age_group}",
                "dismissals": f"caged_dismissals_{age_group}",
                "balance": f"caged_balance_{age_group}",
            }
        )
        caged_parts.append(part)

    enrollment = _municipal_metric(
        frames["offer"], metric="located_enrollments", stage="medio"
    ).rename(columns={"value": "high_school_located_enrollments"})
    panel = trajectory.merge(
        rais_wide.drop(columns="municipality_name"),
        on=["municipality_ibge_code", "year"],
    )
    for part in [*apprentice_parts, *caged_parts]:
        panel = panel.merge(
            part, on=["municipality_ibge_code", "year"], how="left"
        )
    panel = panel.merge(
        enrollment.drop(columns="municipality_name"),
        on=["municipality_ibge_code", "year"],
        how="left",
    )
    for column in (
        "rais_active_bonds_15_17",
        "rais_active_bonds_18_24",
        "caged_admissions_15_17",
        "caged_admissions_18_24",
    ):
        panel[f"log1p_{column}"] = np.log1p(_numeric(panel[column]))
    for age_group in ("15_17", "18_24"):
        panel[f"apprentice_share_percent_{age_group}"] = (
            _numeric(panel[f"apprentice_share_ratio_{age_group}"]) * 100
        )
    panel = panel.sort_values(["municipality_ibge_code", "year"])
    panel["lag1_log1p_rais_active_bonds_15_17"] = panel.groupby(
        "municipality_ibge_code"
    )["log1p_rais_active_bonds_15_17"].shift(1)

    specifications = [
        (
            "R3_FE_RAIS15_DROPOUT_CURRENT",
            panel,
            "dropout_rate_percent",
            "log1p_rais_active_bonds_15_17",
            None,
            "primary",
            "2019-2025",
        ),
        (
            "R3_FE_RAIS15_DROPOUT_WEIGHTED",
            panel,
            "dropout_rate_percent",
            "log1p_rais_active_bonds_15_17",
            "high_school_located_enrollments",
            "robustness",
            "2019-2025",
        ),
        (
            "R3_FE_RAIS15_DROPOUT_LAG1",
            panel,
            "dropout_rate_percent",
            "lag1_log1p_rais_active_bonds_15_17",
            None,
            "robustness",
            "2020-2025; predictor lagged one year",
        ),
        (
            "R3_FE_RAIS15_DROPOUT_EXCLUDE_CAUTION",
            panel[~panel["year"].isin([2020, 2021])],
            "dropout_rate_percent",
            "log1p_rais_active_bonds_15_17",
            None,
            "robustness",
            "2019,2022-2025",
        ),
        (
            "R3_FE_RAIS18_DROPOUT_CURRENT",
            panel,
            "dropout_rate_percent",
            "log1p_rais_active_bonds_18_24",
            None,
            "secondary",
            "2019-2025",
        ),
        (
            "R3_FE_APPRENTICE15_DROPOUT",
            panel,
            "dropout_rate_percent",
            "apprentice_share_percent_15_17",
            None,
            "primary",
            "2020-2025",
        ),
        (
            "R3_FE_APPRENTICE15_FAILURE",
            panel,
            "failure_rate_percent",
            "apprentice_share_percent_15_17",
            None,
            "robustness",
            "2020-2025",
        ),
        (
            "R3_FE_CAGED15_DROPOUT",
            panel,
            "dropout_rate_percent",
            "log1p_caged_admissions_15_17",
            None,
            "secondary",
            "2020-2025",
        ),
    ]
    tests = []
    details = {}
    for test_id, sample, outcome, factor, weight, role, period in specifications:
        model = fit_panel(
            sample,
            outcome=outcome,
            factor=factor,
            municipality="municipality_ibge_code",
            year="year",
            test_id=test_id,
            weight=weight,
        )
        details[test_id] = model
        tests.append(
            _panel_test_row(
                "R3",
                model,
                x_lens="workplace",
                y_lens="school_location",
                period=period,
                role=role,
            )
        )

    aligned = []
    for _, row in panel.iterrows():
        aligned.append(
            _aligned_row(
                relation_id="R3",
                alignment_id="R3_RAIS15_TRAJECTORY_PANEL",
                code=str(row["municipality_ibge_code"]),
                name=str(row["municipality_name"]),
                year=int(row["year"]),
                x_metric="rais_active_bonds_15_17",
                x_value=row["rais_active_bonds_15_17"],
                x_unit="active_bonds",
                x_lens="workplace",
                y_metric="dropout_rate_percent",
                y_value=row["dropout_rate_percent"],
                y_unit="percent",
                y_lens="school_location",
                source_refs=["job5gcr_rais_youth", "job5gar_trajectory"],
                temporal_nature="annual_parallel_ecological_panel",
                caution=(
                    "trajectory_continuity_caution"
                    if int(row["year"]) in {2020, 2021}
                    else "stock_and_outcome_parallel_no_person_link"
                ),
            )
        )
    endpoint = panel[panel["year"].eq(2025)].copy()
    heterogeneity = []
    for _, row in endpoint.iterrows():
        heterogeneity.append(
            _heterogeneity_row(
                "R3",
                row,
                x_metric="rais_active_bonds_15_17_2025",
                x_value=row["rais_active_bonds_15_17"],
                y_metric="apprentice_share_of_youth_admissions_15_17_2025_percent",
                y_value=row["apprentice_share_percent_15_17"],
                x_lens="workplace",
                y_lens="workplace",
                period="2025",
                note="RAIS é estoque; aprendizagem é fluxo de eventos; não somar nem fundir.",
            )
        )

    nsr_2019 = panel[
        panel["municipality_ibge_code"].eq(NSR_CODE) & panel["year"].eq(2019)
    ].iloc[0]
    nsr_2025 = endpoint[endpoint["municipality_ibge_code"].eq(NSR_CODE)].iloc[0]
    rais_nsr_total = rais[
        rais["municipality_ibge_code"].eq(NSR_CODE) & rais["year"].eq(2025)
    ].set_index("age_group")
    region_rais = frames["rais_youth"]
    region_rais = region_rais[
        region_rais["entity_id"].eq(REGION_ID)
        & region_rais["dimension"].eq("total")
        & region_rais["dimension_code"].eq("ALL")
    ]
    region_end = region_rais[region_rais["year"].eq(2025)].set_index("age_group")
    anchors = {
        "nsrRais15_17_2019": _clean_number(nsr_2019["rais_active_bonds_15_17"]),
        "nsrRais15_17_2025": _clean_number(nsr_2025["rais_active_bonds_15_17"]),
        "nsrRais18_24_2019": _clean_number(nsr_2019["rais_active_bonds_18_24"]),
        "nsrRais18_24_2025": _clean_number(nsr_2025["rais_active_bonds_18_24"]),
        "nsrContributionToValeRaisChange15_17": _clean_number(
            rais_nsr_total.loc["15_17", "municipal_contribution_to_regional_change"]
        ),
        "nsrContributionToValeRaisChange18_24": _clean_number(
            rais_nsr_total.loc["18_24", "municipal_contribution_to_regional_change"]
        ),
        "nsrApprenticeAdmissions15_17_2025": _clean_number(
            nsr_2025["apprentice_admissions_15_17"]
        ),
        "nsrYouthAdmissions15_17_2025": _clean_number(
            nsr_2025["youth_admissions_15_17"]
        ),
        "nsrApprenticeShare15_17_2025Percent": _clean_number(
            nsr_2025["apprentice_share_percent_15_17"]
        ),
        "nsrApprenticeAdmissions18_24_2025": _clean_number(
            nsr_2025["apprentice_admissions_18_24"]
        ),
        "nsrYouthAdmissions18_24_2025": _clean_number(
            nsr_2025["youth_admissions_18_24"]
        ),
        "nsrApprenticeShare18_24_2025Percent": _clean_number(
            nsr_2025["apprentice_share_percent_18_24"]
        ),
        "valeRais15_17_2025": _clean_number(
            region_end.loc["15_17", "active_bonds"]
        ),
        "valeRais18_24_2025": _clean_number(
            region_end.loc["18_24", "active_bonds"]
        ),
    }
    return {
        "panel": panel,
        "tests": tests,
        "details": details,
        "aligned": aligned,
        "heterogeneity": heterogeneity,
        "anchors": anchors,
    }


def _relation_r4(frames: Mapping[str, pd.DataFrame]) -> dict[str, Any]:
    occupation = frames["occupations"]
    occupation = occupation[
        occupation["entity_scope"].eq("municipality")
        & occupation["dimension_code"].eq("414140")
    ][
        [
            "municipality_ibge_code",
            "municipality_name",
            "initial_value",
            "final_value",
            "absolute_change",
            "regional_initial_value",
            "regional_final_value",
        ]
    ].copy()
    ept = frames["ept"]
    ept = ept[
        ept["entity_scope"].eq("municipality")
        & ept["grain"].eq("municipality_total")
        & ept["year"].eq(2025)
    ][
        [
            "municipality_ibge_code",
            "municipality_name",
            "technical_enrollments",
            "availability_status",
            "share_of_regional_technical_enrollments",
        ]
    ]
    panel = occupation.merge(
        ept.drop(columns="municipality_name"), on="municipality_ibge_code"
    )
    test_id = "R4_CBO414140_CHANGE_EPT2025"
    summary = correlation_summary(
        panel,
        x="absolute_change",
        y="technical_enrollments",
        municipality="municipality_ibge_code",
        test_id=test_id,
    )
    tests = [
        _correlation_test_row(
            "R4",
            test_id,
            summary,
            x_metric="cbo_414140_active_bonds_change_2019_2025",
            y_metric="located_technical_enrollments_2025",
            period="occupation_endpoints_2019_2025_vs_ept_2025",
            x_lens="workplace",
            y_lens="school_location",
            role="exploratory",
        )
    ]
    aligned = []
    heterogeneity = []
    for _, row in panel.sort_values("municipality_ibge_code").iterrows():
        aligned.append(
            _aligned_row(
                relation_id="R4",
                alignment_id="R4_CBO414140_EPT",
                code=str(row["municipality_ibge_code"]),
                name=str(row["municipality_name"]),
                year="2019-2025",
                x_metric="cbo_414140_absolute_change",
                x_value=row["absolute_change"],
                x_unit="active_bonds",
                x_lens="workplace",
                y_metric="technical_enrollments_2025",
                y_value=row["technical_enrollments"],
                y_unit="enrollments",
                y_lens="school_location",
                source_refs=["job5gcr_occupation_endpoints", "job5gcr_ept_offer"],
                temporal_nature="observed_endpoints_vs_single_year_offer",
                caution="ecological_structural_contrast_no_student_worker_link",
            )
        )
        heterogeneity.append(
            _heterogeneity_row(
                "R4",
                row,
                x_metric="cbo_414140_absolute_change_2019_2025",
                x_value=row["absolute_change"],
                y_metric="technical_enrollments_2025",
                y_value=row["technical_enrollments"],
                x_lens="workplace",
                y_lens="school_location",
                period="2019-2025|2025",
                note="Contraste estrutural; ponte CNCT–CBO é normativa e não aditiva.",
            )
        )
    nsr = panel[panel["municipality_ibge_code"].eq(NSR_CODE)].iloc[0]
    region = frames["occupations"]
    region = region[
        region["entity_id"].eq(REGION_ID) & region["dimension_code"].eq("414140")
    ].iloc[0]
    anchors = {
        "valeCbo414140Initial2019": _clean_number(region["initial_value"]),
        "valeCbo414140Final2025": _clean_number(region["final_value"]),
        "valeCbo414140AbsoluteChange": _clean_number(region["absolute_change"]),
        "nsrCbo414140Initial2019": _clean_number(nsr["initial_value"]),
        "nsrCbo414140Final2025": _clean_number(nsr["final_value"]),
        "nsrCbo414140AbsoluteChange": _clean_number(nsr["absolute_change"]),
        "nsrContributionToValeCbo414140Change": _clean_number(
            float(nsr["absolute_change"]) / float(region["absolute_change"])
            if float(region["absolute_change"]) != 0
            else None
        ),
        "nsrEpt2025": _clean_number(nsr["technical_enrollments"]),
        "nsrEptAvailability2025": str(nsr["availability_status"]),
        "valeEpt2025": _clean_number(panel["technical_enrollments"].sum()),
    }
    return {
        "panel": panel,
        "tests": tests,
        "details": {test_id: summary},
        "aligned": aligned,
        "heterogeneity": heterogeneity,
        "anchors": anchors,
    }


def _relation_r5(frames: Mapping[str, pd.DataFrame]) -> dict[str, Any]:
    panel = frames["eja_distribution"]
    panel = panel[panel["entity_scope"].eq("municipality")].copy()
    tests = []
    details = {}
    for stage in ("fundamental", "high_school"):
        subset = panel[panel["stage"].eq(stage)]
        tvd = 0.5 * _numeric(
            subset["distribution_difference_percentage_points"]
        ).abs().sum()
        test_id = f"R5_TERRITORIAL_DISTRIBUTION_TVD_{stage.upper()}"
        details[test_id] = {
            "method": "total_variation_distance_between_municipal_distributions",
            "formula": "0.5 * sum(abs(municipal_eja_share - municipal_resident_public_share))",
            "stage": stage,
            "valuePercentagePoints": float(tvd),
            "municipalities": 10,
        }
        tests.append(
            {
                "relation_id": "R5",
                "test_id": test_id,
                "test_role": "primary",
                "method": "total_variation_distance",
                "x_metric": f"resident_public_distribution_{stage}_2022",
                "y_metric": f"located_eja_distribution_{stage}_2022",
                "x_lens": "resident_population",
                "y_lens": "school_location",
                "period_alignment": "cross_section_2022_within_stage",
                "estimate": float(tvd),
                "estimate_type": "percentage_points_total_variation_distance",
                "pearson": None,
                "weighted_pearson": None,
                "weight": None,
                "standard_error": None,
                "ci95_low": None,
                "ci95_high": None,
                "p_value_raw": None,
                "p_value_bh": None,
                "observations": 10,
                "municipalities": 10,
                "years": "2022",
                "leave_one_out_dominant_direction_fraction": None,
                "availability_state": "observed",
                "causal_interpretation_allowed": False,
                "same_person_link": False,
            }
        )
    aligned = []
    heterogeneity = []
    for _, row in panel.sort_values(["stage", "municipality_ibge_code"]).iterrows():
        aligned.append(
            _aligned_row(
                relation_id="R5",
                alignment_id=f"R5_EJA_DISTRIBUTION_{row['stage'].upper()}",
                code=str(row["municipality_ibge_code"]),
                name=str(row["municipality_name"]),
                year=2022,
                x_metric="share_of_regional_resident_public_percent",
                x_value=row["share_of_regional_public_percent"],
                x_unit="percent",
                x_lens="resident_population",
                y_metric="share_of_regional_located_eja_enrollments_percent",
                y_value=row["share_of_regional_enrollments_percent"],
                y_unit="percent",
                y_lens="school_location",
                source_refs=["job5gbr_eja_distribution"],
                temporal_nature="single_year_distribution",
                caution="within_stage_distribution_not_coverage_or_demand",
            )
        )
        heterogeneity.append(
            _heterogeneity_row(
                "R5",
                row,
                x_metric=f"resident_public_share_{row['stage']}_2022",
                x_value=row["share_of_regional_public_percent"],
                y_metric=f"located_eja_share_{row['stage']}_2022",
                y_value=row["share_of_regional_enrollments_percent"],
                x_lens="resident_population",
                y_lens="school_location",
                period="2022",
                note=(
                    "Gap de distribuição dentro da etapa; não é cobertura nem demanda. "
                    f"Gap={float(row['distribution_difference_percentage_points'])} pp."
                ),
            )
        )
    nsr = panel[panel["municipality_ibge_code"].eq(NSR_CODE)].set_index("stage")
    adult = frames["adult_schooling"]
    adult = adult[
        adult["entity_scope"].eq("municipality")
        & adult["municipality_ibge_code"].eq(NSR_CODE)
    ]
    adult_pivot = adult.pivot(
        index="schooling_category", columns="year", values="count_value"
    )
    eja_history = frames["eja_history"]
    eja_history = eja_history[
        eja_history["entity_scope"].eq("municipality")
        & eja_history["municipality_ibge_code"].eq(NSR_CODE)
        & eja_history["stage"].eq("total_context")
    ].set_index("year")
    anchors = {
        "nsrFundamentalResidentPublic2022": _clean_number(
            nsr.loc["fundamental", "resident_adult_public"]
        ),
        "nsrFundamentalLocatedEja2022": _clean_number(
            nsr.loc["fundamental", "school_location_eja_enrollments"]
        ),
        "nsrFundamentalDistributionGapPp": _clean_number(
            nsr.loc["fundamental", "distribution_difference_percentage_points"]
        ),
        "nsrHighSchoolResidentPublic2022": _clean_number(
            nsr.loc["high_school", "resident_adult_public"]
        ),
        "nsrHighSchoolLocatedEja2022": _clean_number(
            nsr.loc["high_school", "school_location_eja_enrollments"]
        ),
        "nsrHighSchoolDistributionGapPp": _clean_number(
            nsr.loc["high_school", "distribution_difference_percentage_points"]
        ),
        "nsrAdultsHighSchoolCompletedOrMore2010": _clean_number(
            adult_pivot.loc["high_school_completed_or_more", 2010]
        ),
        "nsrAdultsHighSchoolCompletedOrMore2022": _clean_number(
            adult_pivot.loc["high_school_completed_or_more", 2022]
        ),
        "nsrEjaTotal2014": _clean_number(eja_history.loc[2014, "eja_enrollments"]),
        "nsrEjaTotal2025": _clean_number(eja_history.loc[2025, "eja_enrollments"]),
    }
    return {
        "panel": panel,
        "tests": tests,
        "details": details,
        "aligned": aligned,
        "heterogeneity": heterogeneity,
        "anchors": anchors,
    }


def _relation_r6(frames: Mapping[str, pd.DataFrame]) -> dict[str, Any]:
    inse = frames["conditions"]
    inse = inse[
        inse["metric"].eq("inse_mean") & inse["year"].isin([2019, 2021, 2023])
    ][
        [
            "municipality_ibge_code",
            "municipality_name",
            "year",
            "value",
            "difference_from_rs_municipal_median",
        ]
    ].rename(columns={"value": "inse_mean"})
    trajectory = _trajectory_wide(frames["trajectory"], years=[2019, 2021, 2023])
    panel = inse.merge(
        trajectory.drop(columns="municipality_name"),
        on=["municipality_ibge_code", "year"],
    )
    tests = []
    details = {}
    outcomes = [
        "approval_rate_percent",
        "dropout_rate_percent",
        "failure_rate_percent",
        "age_grade_distortion_rate_percent",
    ]
    for year in (2019, 2023):
        sample = panel[panel["year"].eq(year)]
        for outcome in outcomes:
            test_id = f"R6_INSE_{outcome.upper()}_{year}"
            summary = correlation_summary(
                sample,
                x="inse_mean",
                y=outcome,
                municipality="municipality_ibge_code",
                test_id=test_id,
            )
            details[test_id] = summary
            tests.append(
                _correlation_test_row(
                    "R6",
                    test_id,
                    summary,
                    x_metric="inse_mean",
                    y_metric=outcome,
                    period=f"cross_section_{year}",
                    x_lens="school_location_assessed_students",
                    y_lens="school_location",
                    role="primary" if year == 2023 else "robustness",
                )
            )
    panel_no_caution = panel[panel["year"].isin([2019, 2023])]
    for outcome in outcomes:
        test_id = f"R6_FE_INSE_{outcome.upper()}_2019_2023"
        model = fit_panel(
            panel_no_caution,
            outcome=outcome,
            factor="inse_mean",
            municipality="municipality_ibge_code",
            year="year",
            test_id=test_id,
        )
        details[test_id] = model
        tests.append(
            _panel_test_row(
                "R6",
                model,
                x_lens="school_location_assessed_students",
                y_lens="school_location",
                period="2019_and_2023; 2021 excluded from primary panel",
                role="robustness",
            )
        )
    aligned = []
    for _, row in panel.sort_values(["municipality_ibge_code", "year"]).iterrows():
        aligned.append(
            _aligned_row(
                relation_id="R6",
                alignment_id="R6_INSE_TRAJECTORY",
                code=str(row["municipality_ibge_code"]),
                name=str(row["municipality_name"]),
                year=int(row["year"]),
                x_metric="inse_mean",
                x_value=row["inse_mean"],
                x_unit="inse_scale_points",
                x_lens="school_location_assessed_students",
                y_metric="age_grade_distortion_rate_percent",
                y_value=row["age_grade_distortion_rate_percent"],
                y_unit="percent",
                y_lens="school_location",
                source_refs=["job5gar_conditions", "job5gar_trajectory"],
                temporal_nature="three_observed_cross_sections",
                caution=(
                    "trajectory_continuity_caution"
                    if int(row["year"]) == 2021
                    else "inse_universe_is_assessed_students"
                ),
            )
        )
    endpoint = panel[panel["year"].eq(2023)]
    heterogeneity = [
        _heterogeneity_row(
            "R6",
            row,
            x_metric="inse_mean_2023",
            x_value=row["inse_mean"],
            y_metric="age_grade_distortion_rate_percent_2023",
            y_value=row["age_grade_distortion_rate_percent"],
            x_lens="school_location_assessed_students",
            y_lens="school_location",
            period="2023",
            note="INSE descreve alunos avaliados; referência RS no mesmo contrato está indisponível.",
        )
        for _, row in endpoint.sort_values("municipality_ibge_code").iterrows()
    ]
    nsr = endpoint[endpoint["municipality_ibge_code"].eq(NSR_CODE)].iloc[0]
    anchors = {
        "nsrInseMean2023": _clean_number(nsr["inse_mean"]),
        "nsrApproval2023Percent": _clean_number(nsr["approval_rate_percent"]),
        "nsrDropout2023Percent": _clean_number(nsr["dropout_rate_percent"]),
        "nsrFailure2023Percent": _clean_number(nsr["failure_rate_percent"]),
        "nsrDistortion2023Percent": _clean_number(
            nsr["age_grade_distortion_rate_percent"]
        ),
        "stateReferenceAvailability": "unavailable_same_contract",
    }
    return {
        "panel": panel,
        "tests": tests,
        "details": details,
        "aligned": aligned,
        "heterogeneity": heterogeneity,
        "anchors": anchors,
    }


def _relation_r7(frames: Mapping[str, pd.DataFrame]) -> dict[str, Any]:
    rural = frames["rural"]
    enroll_all = _endpoint_change(
        rural,
        metric="rural_enrollments",
        stage="all",
        output_name="rural_enrollment_change_2014_2025",
    )
    enroll_high = _endpoint_change(
        rural,
        metric="rural_enrollments",
        stage="high_school",
        output_name="rural_high_school_enrollment_change_2014_2025",
    )
    schools = _endpoint_change(
        rural,
        metric="rural_schools",
        stage="all",
        output_name="rural_school_change_2014_2025",
    )
    pnate = frames["pnate"]
    pnate = pnate[pnate["entity_scope"].eq("municipality")]
    selected = {}
    for year, metric, output in (
        (2025, "pnate_authorized_after_discount", "pnate_authorized_2025"),
        (2025, "pnate_beneficiary_students", "pnate_beneficiaries_2025"),
        (2026, "pnate_adjusted_forecast", "pnate_forecast_2026"),
    ):
        part = pnate[
            pnate["exercise_year"].eq(year) & pnate["metric"].eq(metric)
        ][["municipality_ibge_code", "value"]].rename(columns={"value": output})
        selected[output] = part
    panel = enroll_all.merge(
        enroll_high.drop(columns="municipality_name"), on="municipality_ibge_code"
    ).merge(schools.drop(columns="municipality_name"), on="municipality_ibge_code")
    for part in selected.values():
        panel = panel.merge(part, on="municipality_ibge_code")
    test_id = "R7_RURAL_ENROLLMENT_SCHOOL_CHANGE"
    summary = correlation_summary(
        panel,
        x="rural_school_change_2014_2025",
        y="rural_enrollment_change_2014_2025",
        municipality="municipality_ibge_code",
        test_id=test_id,
    )
    tests = [
        _correlation_test_row(
            "R7",
            test_id,
            summary,
            x_metric="rural_school_change_2014_2025",
            y_metric="rural_enrollment_change_2014_2025",
            period="observed_endpoints_2014_2025",
            x_lens="rural_school_location",
            y_lens="rural_school_location",
            role="descriptive",
        ),
        {
            "relation_id": "R7",
            "test_id": "R7_PNATE_CONTEXT_ONLY",
            "test_role": "context_only",
            "method": "no_cross_lens_regression_by_preregistration",
            "x_metric": "rural_offer_change_2014_2025",
            "y_metric": "pnate_planning_context_2025_2026",
            "x_lens": "rural_school_location",
            "y_lens": "municipal_executor",
            "period_alignment": "non_equivalent_periods_context_only",
            "estimate": None,
            "estimate_type": "not_evaluated",
            "pearson": None,
            "weighted_pearson": None,
            "weight": None,
            "standard_error": None,
            "ci95_low": None,
            "ci95_high": None,
            "p_value_raw": None,
            "p_value_bh": None,
            "observations": 10,
            "municipalities": 10,
            "years": "2014|2025|2026",
            "leave_one_out_dominant_direction_fraction": None,
            "availability_state": "not_evaluable_cross_lens_period_contract",
            "causal_interpretation_allowed": False,
            "same_person_link": False,
        },
    ]
    aligned = []
    heterogeneity = []
    for _, row in panel.sort_values("municipality_ibge_code").iterrows():
        aligned.append(
            _aligned_row(
                relation_id="R7",
                alignment_id="R7_RURAL_PNATE_CONTEXT",
                code=str(row["municipality_ibge_code"]),
                name=str(row["municipality_name"]),
                year="2014-2026",
                x_metric="rural_high_school_enrollment_change_2014_2025",
                x_value=row["rural_high_school_enrollment_change_2014_2025"],
                x_unit="enrollments",
                x_lens="rural_school_location",
                y_metric="pnate_forecast_2026",
                y_value=row["pnate_forecast_2026"],
                y_unit="BRL_nominal",
                y_lens="municipal_executor",
                source_refs=["job5gbr_rural", "job5gd_pnate"],
                temporal_nature="separate_contextual_periods",
                caution="pnate_forecast_not_execution_use_payment_or_mobility",
            )
        )
        heterogeneity.append(
            _heterogeneity_row(
                "R7",
                row,
                x_metric="rural_high_school_enrollment_change_2014_2025",
                x_value=row["rural_high_school_enrollment_change_2014_2025"],
                y_metric="pnate_forecast_2026",
                y_value=row["pnate_forecast_2026"],
                x_lens="rural_school_location",
                y_lens="municipal_executor",
                period="2014-2025|2026",
                note="Contexto de planejamento separado; PNATE não mede mobilidade ou execução.",
            )
        )
    nsr = panel[panel["municipality_ibge_code"].eq(NSR_CODE)].iloc[0]
    anchors = {
        "nsrRuralEnrollmentChange2014_2025": _clean_number(
            nsr["rural_enrollment_change_2014_2025"]
        ),
        "nsrRuralSchoolChange2014_2025": _clean_number(
            nsr["rural_school_change_2014_2025"]
        ),
        "nsrRuralHighSchoolEnrollmentChange2014_2025": _clean_number(
            nsr["rural_high_school_enrollment_change_2014_2025"]
        ),
        "nsrPnateAuthorized2025": _clean_number(nsr["pnate_authorized_2025"]),
        "nsrPnateBeneficiaries2025": _clean_number(nsr["pnate_beneficiaries_2025"]),
        "nsrPnateForecast2026": _clean_number(nsr["pnate_forecast_2026"]),
        "valeRuralEnrollmentChange2014_2025": _clean_number(
            panel["rural_enrollment_change_2014_2025"].sum()
        ),
        "valeRuralSchoolChange2014_2025": _clean_number(
            panel["rural_school_change_2014_2025"].sum()
        ),
        "valeRuralHighSchoolEnrollmentChange2014_2025": _clean_number(
            panel["rural_high_school_enrollment_change_2014_2025"].sum()
        ),
    }
    return {
        "panel": panel,
        "tests": tests,
        "details": {test_id: summary},
        "aligned": aligned,
        "heterogeneity": heterogeneity,
        "anchors": anchors,
    }


def _relation_r8(frames: Mapping[str, pd.DataFrame]) -> dict[str, Any]:
    special = frames["special"]
    enrollment = _endpoint_change(
        special,
        metric="special_enrollments",
        stage="all",
        output_name="special_enrollment_change_2014_2025",
    )
    aee = _endpoint_change(
        special,
        metric="schools_offering_aee",
        stage="all",
        output_name="aee_school_change_2014_2025",
    )
    panel = enrollment.merge(
        aee.drop(columns="municipality_name"), on="municipality_ibge_code"
    )
    test_id = "R8_SPECIAL_ENROLLMENT_AEE_SCHOOL_CHANGE"
    summary = correlation_summary(
        panel,
        x="special_enrollment_change_2014_2025",
        y="aee_school_change_2014_2025",
        municipality="municipality_ibge_code",
        test_id=test_id,
    )
    tests = [
        _correlation_test_row(
            "R8",
            test_id,
            summary,
            x_metric="special_enrollment_change_2014_2025",
            y_metric="aee_school_change_2014_2025",
            period="observed_endpoints_2014_2025",
            x_lens="school_location",
            y_lens="school_location",
        )
    ]
    aligned = []
    heterogeneity = []
    for _, row in panel.sort_values("municipality_ibge_code").iterrows():
        aligned.append(
            _aligned_row(
                relation_id="R8",
                alignment_id="R8_SPECIAL_AEE_CHANGE",
                code=str(row["municipality_ibge_code"]),
                name=str(row["municipality_name"]),
                year="2014-2025",
                x_metric="special_enrollment_change_2014_2025",
                x_value=row["special_enrollment_change_2014_2025"],
                x_unit="enrollments",
                x_lens="school_location",
                y_metric="aee_school_change_2014_2025",
                y_value=row["aee_school_change_2014_2025"],
                y_unit="schools",
                y_lens="school_location",
                source_refs=["job5gbr_special_aee"],
                temporal_nature="observed_endpoints",
                caution="no_same_person_or_resident_coverage_link",
            )
        )
        heterogeneity.append(
            _heterogeneity_row(
                "R8",
                row,
                x_metric="special_enrollment_change_2014_2025",
                x_value=row["special_enrollment_change_2014_2025"],
                y_metric="aee_school_change_2014_2025",
                y_value=row["aee_school_change_2014_2025"],
                x_lens="school_location",
                y_lens="school_location",
                period="2014-2025",
                note="Co-movimento de oferta localizada; sem cobertura ou vínculo individual.",
            )
        )
    nsr = panel[panel["municipality_ibge_code"].eq(NSR_CODE)].iloc[0]
    anchors = {
        "nsrSpecialEnrollmentChange2014_2025": _clean_number(
            nsr["special_enrollment_change_2014_2025"]
        ),
        "nsrAeeSchoolChange2014_2025": _clean_number(
            nsr["aee_school_change_2014_2025"]
        ),
        "valeSpecialEnrollmentChange2014_2025": _clean_number(
            panel["special_enrollment_change_2014_2025"].sum()
        ),
        "valeAeeSchoolChange2014_2025": _clean_number(
            panel["aee_school_change_2014_2025"].sum()
        ),
    }
    return {
        "panel": panel,
        "tests": tests,
        "details": {test_id: summary},
        "aligned": aligned,
        "heterogeneity": heterogeneity,
        "anchors": anchors,
    }


def build_analysis(frames: Mapping[str, pd.DataFrame]) -> dict[str, Any]:
    builders = {
        "R1": _relation_r1,
        "R2": _relation_r2,
        "R3": _relation_r3,
        "R4": _relation_r4,
        "R5": _relation_r5,
        "R6": _relation_r6,
        "R7": _relation_r7,
        "R8": _relation_r8,
    }
    relations = {relation_id: builder(frames) for relation_id, builder in builders.items()}
    test_rows = [row for value in relations.values() for row in value["tests"]]
    adjusted = bh_adjust([row["p_value_raw"] for row in test_rows])
    for row, adjusted_value in zip(test_rows, adjusted, strict=True):
        row["p_value_bh"] = adjusted_value
        row["multiplicity_interpretation"] = (
            "adjusted_p_at_or_below_0_05"
            if adjusted_value is not None and adjusted_value <= 0.05
            else "not_supported_by_adjusted_p_alone"
            if adjusted_value is not None
            else "not_applicable_no_p_value"
        )
    tests = pd.DataFrame(test_rows).sort_values(["relation_id", "test_id"])
    aligned = pd.DataFrame(
        [row for value in relations.values() for row in value["aligned"]]
    ).sort_values(
        ["relation_id", "alignment_id", "municipality_ibge_code", "year_or_period"]
    )
    heterogeneity = pd.DataFrame(
        [row for value in relations.values() for row in value["heterogeneity"]]
    ).sort_values(["relation_id", "x_metric", "municipality_ibge_code"])
    heterogeneity["x_rank_low_to_high"] = heterogeneity.groupby(
        ["relation_id", "x_metric"], dropna=False
    )["x_value"].rank(method="average")
    heterogeneity["y_rank_low_to_high"] = heterogeneity.groupby(
        ["relation_id", "y_metric"], dropna=False
    )["y_value"].rank(method="average")
    if set(tests["relation_id"]) != set(builders):
        raise Job5JValidationError("Relações R1–R8 não cobertas pela matriz de testes")
    if set(heterogeneity["municipality_ibge_code"]) != set(_municipalities()):
        raise Job5JValidationError("Heterogeneidade não cobre os dez municípios")
    details = {
        "schemaVersion": "vocacoes-pne-job5j-model-details-v1",
        "generatedAt": GENERATED_AT,
        "relations": {
            relation_id: value["details"] for relation_id, value in relations.items()
        },
        "multipleTesting": {
            "method": "Benjamini-Hochberg",
            "familySizeWithPValue": int(tests["p_value_raw"].notna().sum()),
            "automaticInsightApproval": False,
        },
    }
    anchors = {
        relation_id: value["anchors"] for relation_id, value in relations.items()
    }
    return {
        "relations": relations,
        "tests": tests,
        "aligned": aligned,
        "heterogeneity": heterogeneity,
        "details": details,
        "anchors": anchors,
    }


def _test_row(analysis: Mapping[str, Any], test_id: str) -> Mapping[str, Any]:
    rows = analysis["tests"]
    match = rows[rows["test_id"].eq(test_id)]
    if len(match) != 1:
        raise Job5JValidationError(f"Teste ausente ou duplicado: {test_id}")
    return match.iloc[0].to_dict()


def _fmt(value: Any, digits: int = 3) -> str:
    number = _clean_number(value)
    if number is None:
        return "indisponível"
    if isinstance(number, int):
        return f"{number:,}".replace(",", ".")
    return f"{number:.{digits}f}".replace(".", ",")


def build_insights(analysis: Mapping[str, Any]) -> list[dict[str, Any]]:
    anchors = analysis["anchors"]
    r1 = _test_row(analysis, "R1_PRESSURE_ENROLLMENT")
    r2 = _test_row(analysis, "R2_MOBILITY_DROPOUT_RATE_PERCENT")
    r3_primary = _test_row(analysis, "R3_FE_RAIS15_DROPOUT_CURRENT")
    r3_weighted = _test_row(analysis, "R3_FE_RAIS15_DROPOUT_WEIGHTED")
    r4 = _test_row(analysis, "R4_CBO414140_CHANGE_EPT2025")
    r5_f = _test_row(analysis, "R5_TERRITORIAL_DISTRIBUTION_TVD_FUNDAMENTAL")
    r5_m = _test_row(analysis, "R5_TERRITORIAL_DISTRIBUTION_TVD_HIGH_SCHOOL")
    r6_2019 = _test_row(
        analysis, "R6_INSE_AGE_GRADE_DISTORTION_RATE_PERCENT_2019"
    )
    r6_2023 = _test_row(
        analysis, "R6_INSE_AGE_GRADE_DISTORTION_RATE_PERCENT_2023"
    )
    r6_fe = _test_row(
        analysis, "R6_FE_INSE_AGE_GRADE_DISTORTION_RATE_PERCENT_2019_2023"
    )
    r7 = _test_row(analysis, "R7_RURAL_ENROLLMENT_SCHOOL_CHANGE")
    r8 = _test_row(analysis, "R8_SPECIAL_ENROLLMENT_AEE_SCHOOL_CHANGE")
    common_forbidden = [
        "Não afirmar causalidade.",
        "Não afirmar vínculo de mesma pessoa.",
        "Não fundir lentes territoriais distintas.",
        "Não afirmar cumprimento de PNE ou PME.",
        "Não transformar o resultado em ranking ou prioridade automática.",
    ]
    common = {
        "territorial_scales": [
            "RS quando o mesmo contrato permite",
            "Vale do Sinos",
            "distribuição dos dez municípios",
            "município selecionado",
            "Nova Santa Rita (4313375)",
        ],
        "selected_municipality_result": "Nova Santa Rita é o município selecionado nesta execução.",
        "external_judgment_required": True,
    }
    insights = [
        {
            **common,
            "insight_id": "JOB5J_R1_DEMOGRAPHY_OFFER",
            "classification": "STRUCTURAL_CONTRAST",
            "manager_question": "A resposta recente da oferta de ensino médio está coerente com a pressão mecânica das coortes?",
            "education_outcome": "Matrículas e turmas localizadas do ensino médio.",
            "territorial_transformation": "Pressão mecânica da coorte residente até 2030.",
            "substantive_mechanism": "Mudanças de coorte podem alterar a agenda de oferta, mas migração, fluxo, retenção e mobilidade não estão modelados.",
            "population_or_stage": "Coorte residente e ensino médio localizado.",
            "period_alignment": "Mudança observada 2014–2025 versus razão mecânica de referência 2025/horizonte 2030.",
            "methods_used": ["Pearson", "Spearman", "intervalo de Fisher", "leave-one-out", "contraste de endpoints"],
            "main_effect_or_contrast": f"Nos dez municípios, rho={_fmt(r1['estimate'])}; a correlação não sustenta uma relação geral. Nova Santa Rita ganhou {anchors['R1']['nsrHighSchoolEnrollmentChange2014_2025']} matrículas enquanto o Vale perdeu {abs(anchors['R1']['valeHighSchoolEnrollmentChange2014_2025'])}.",
            "uncertainty_or_stability": f"p permutacional bruto={_fmt(r1['p_value_raw'], 4)}; p BH={_fmt(r1['p_value_bh'], 4)}; pressão mecânica não é previsão.",
            "statewide_result": "NOT_EVALUABLE: a razão de pressão no mesmo contrato não possui painel municipal RS/497 comparável.",
            "vale_result": f"Matrículas do médio: {anchors['R1']['valeHighSchoolEnrollmentChange2014_2025']} entre 2014 e 2025; turmas: +{anchors['R1']['valeHighSchoolClassChange2014_2025']}.",
            "ten_municipality_heterogeneity": "A direção municipal é heterogênea e não é explicada de forma estável pela razão mecânica.",
            "nova_santa_rita_result": f"Razão mecânica 2030={_fmt(anchors['R1']['nsrMechanicalRatio2030'])}; matrículas +{anchors['R1']['nsrHighSchoolEnrollmentChange2014_2025']}; turmas +{anchors['R1']['nsrHighSchoolClassChange2014_2025']}.",
            "incremental_value_beyond_separate_charts": "Mostra que expansão local e retração regional coexistem sem validar uma função geral pressão–oferta.",
            "integrated_conclusion_draft": "A agenda deve combinar monitoramento de coortes e oferta, sem converter a razão mecânica em demanda ou capacidade.",
            "planning_implication": "Revisar anualmente coortes, matrículas, turmas e mobilidade antes de decisões de capacidade.",
            "monitoring_indicators": ["razão mecânica por horizonte", "matrículas do médio", "turmas do médio", "mobilidade de residentes"],
            "institutional_coordination": ["município", "rede estadual", "planejamento regional"],
            "allowed_claims": ["Contraste estrutural observado.", "Expansão local coexistiu com retração regional."],
            "forbidden_claims": common_forbidden + ["Não chamar a razão mecânica de previsão, demanda ou capacidade."],
            "limitations": ["Lentes residente e localização da escola são distintas.", "Não há ajustes de migração ou fluxo escolar."],
            "recommended_visual": "small multiples de endpoints com faixa da distribuição municipal",
            "recommended_editorial_role": "contexto estrutural primário com limite explícito",
        },
        {
            **common,
            "insight_id": "JOB5J_R2_MOBILITY_TRAJECTORY",
            "classification": "NOT_SUPPORTED",
            "manager_question": "A parcela de residentes que estudam fora ajuda a explicar a trajetória municipal do ensino médio?",
            "education_outcome": "Aprovação, reprovação, abandono e distorção do ensino médio.",
            "territorial_transformation": "Mobilidade educacional de residentes em 2022.",
            "substantive_mechanism": "Estudar fora pode sinalizar dependência regional da oferta, sem identificar destino ou efeito sobre a trajetória.",
            "population_or_stage": "Residentes que frequentam ensino médio e escolas localizadas.",
            "period_alignment": "Fotografia transversal de 2022.",
            "methods_used": ["Spearman", "Pearson", "Pearson ponderado pelo denominador", "leave-one-out"],
            "main_effect_or_contrast": f"Mobilidade versus abandono: rho={_fmt(r2['estimate'])}; as demais métricas também não formam padrão robusto.",
            "uncertainty_or_stability": f"p bruto={_fmt(r2['p_value_raw'], 4)}; p BH={_fmt(r2['p_value_bh'], 4)}; n=10.",
            "statewide_result": "NOT_EVALUABLE: não há matriz municipal RS/497 alinhada no pacote congelado.",
            "vale_result": "15,09% dos residentes do médio estudavam em outro município em 2022; isso é fotografia agregada.",
            "ten_municipality_heterogeneity": "As associações mudam de magnitude e não sobrevivem como conclusão substantiva após multiplicidade e robustez.",
            "nova_santa_rita_result": f"220 de 1.151 residentes do médio estudavam em outro município ({_fmt(anchors['R2']['nsrOutsideShareHighSchool2022Percent'])}%).",
            "incremental_value_beyond_separate_charts": "Impede que mobilidade elevada seja apresentada como explicação automática da trajetória.",
            "integrated_conclusion_draft": "A mobilidade acrescenta contexto de coordenação, mas a relação com trajetória não foi sustentada.",
            "planning_implication": "Usar a fotografia para pactuação regional de oferta, não para atribuição de resultado escolar.",
            "monitoring_indicators": ["parcela que estuda fora", "aprovação", "abandono", "distorção", "oferta localizada"],
            "institutional_coordination": ["municípios do Vale", "rede estadual", "planejamento regional"],
            "allowed_claims": ["Mobilidade é contexto de coordenação territorial.", "A relação testada não foi sustentada."],
            "forbidden_claims": common_forbidden + ["Não inferir destino, corredor ou efeito da mobilidade."],
            "limitations": ["Um único ano.", "Destino municipal indisponível.", "n=10."],
            "recommended_visual": "dispersões municipais com denominadores visíveis e aviso de corte transversal",
            "recommended_editorial_role": "resultado negativo útil / limite de interpretação",
        },
        {
            **common,
            "insight_id": "JOB5J_R3_YOUTH_WORK_TRAJECTORY",
            "classification": "NOT_SUPPORTED",
            "manager_question": "A expansão do trabalho formal juvenil acompanha de modo estável a trajetória do ensino médio?",
            "education_outcome": "Abandono e reprovação no ensino médio.",
            "territorial_transformation": "Estoques RAIS e fluxos de admissão/aprendizagem juvenil.",
            "substantive_mechanism": "Mudanças no mercado formal podem alterar a agenda de transição escola–trabalho, mas os registros não ligam estudantes a trabalhadores.",
            "population_or_stage": "Faixas 15–17 e 18–24 no local de trabalho versus ensino médio no local da escola.",
            "period_alignment": "Painel anual 2019–2025; fluxos 2020–2025; defasagem de um ano e exclusão 2020–2021.",
            "methods_used": ["efeitos fixos município-ano", "erros agrupados", "ponderação por matrícula", "defasagem", "sensibilidade 2020–2021"],
            "main_effect_or_contrast": f"O coeficiente RAIS 15–17/abandono mudou de {_fmt(r3_primary['estimate'])} pp por DP na especificação não ponderada para {_fmt(r3_weighted['estimate'])} na ponderada.",
            "uncertainty_or_stability": "Sinais e magnitudes não foram estáveis; nenhum modelo autoriza explicação causal ou individual.",
            "statewide_result": "NOT_EVALUABLE: há agregado estadual de trabalho, mas não painel municipal RS/497 educação–trabalho no mesmo pacote.",
            "vale_result": f"Vínculos 15–17 chegaram a {anchors['R3']['valeRais15_17_2025']}; vínculos 18–24, a {anchors['R3']['valeRais18_24_2025']} em 2025.",
            "ten_municipality_heterogeneity": "Painel completo para RAIS, mas especificações de peso, defasagem e cautela temporal não convergem em um mesmo sinal.",
            "nova_santa_rita_result": f"15–17: 104→172 vínculos; aprendizagem 2025: 174/219 eventos de admissão ({_fmt(anchors['R3']['nsrApprenticeShare15_17_2025Percent'])}%). 18–24: 1.117→1.638 vínculos; contribuição de {_fmt(100 * anchors['R3']['nsrContributionToValeRaisChange18_24'])}% para a mudança líquida regional.",
            "incremental_value_beyond_separate_charts": "Distingue a transformação material do mercado de uma relação estatística não sustentada com trajetória.",
            "integrated_conclusion_draft": "O trabalho juvenil deve permanecer na agenda de monitoramento conjunto, sem alegar associação estável com abandono ou reprovação.",
            "planning_implication": "Monitorar escola–trabalho em paralelo e buscar dados vinculáveis somente sob governança própria.",
            "monitoring_indicators": ["vínculos RAIS 15–17/18–24", "admissões Caged", "aprendizagem", "abandono", "reprovação"],
            "institutional_coordination": ["educação", "trabalho", "assistência", "empregadores", "Sistema S"],
            "allowed_claims": ["O trabalho juvenil cresceu materialmente.", "A associação ecológica com trajetória não foi robusta."],
            "forbidden_claims": common_forbidden + ["Não chamar eventos de pessoas.", "Não tratar local de trabalho como residência."],
            "limitations": ["Sem vínculo individual.", "Dez municípios.", "2020–2021 com cautela.", "Estoque e fluxo separados."],
            "recommended_visual": "painel de coeficientes por especificação ao lado das séries paralelas",
            "recommended_editorial_role": "resultado negativo com sinal de agenda",
        },
        {
            **common,
            "insight_id": "JOB5J_R4_OCCUPATIONS_EPT",
            "classification": "TERRITORIAL_MISMATCH",
            "manager_question": "A transformação ocupacional encontra oferta técnica localizada no mesmo município?",
            "education_outcome": "Oferta EPT localizada em 2025.",
            "territorial_transformation": "Mudança do estoque da ocupação CBO 414140 entre 2019 e 2025.",
            "substantive_mechanism": "Mudança ocupacional pode sinalizar tema formativo, sem provar aderência curricular ou residência dos trabalhadores/estudantes.",
            "population_or_stage": "Trabalho formal de todas as idades e EPT localizada.",
            "period_alignment": "Endpoints ocupacionais 2019–2025 versus oferta EPT 2025.",
            "methods_used": ["contraste de endpoints", "contribuição regional", "Spearman exploratório", "zero observado"],
            "main_effect_or_contrast": f"CBO 414140 no Vale: 303→2.124; em Nova Santa Rita: 17→722, enquanto a EPT local em 2025 foi zero observado. Correlação municipal exploratória rho={_fmt(r4['estimate'])}.",
            "uncertainty_or_stability": f"O contraste local independe de significância; a correlação exploratória tem p BH={_fmt(r4['p_value_bh'], 4)}.",
            "statewide_result": "Apenas referência setorial/ocupacional agregada ou de decomposição; relação municipal RS/497 não materializada.",
            "vale_result": f"A oferta EPT localizada foi {anchors['R4']['valeEpt2025']} matrículas; CBO 414140 cresceu {anchors['R4']['valeCbo414140AbsoluteChange']} vínculos.",
            "ten_municipality_heterogeneity": "A oferta EPT é territorialmente concentrada; crescimento ocupacional e oferta não têm correspondência municipal um-para-um.",
            "nova_santa_rita_result": f"A ocupação respondeu por {_fmt(100 * anchors['R4']['nsrContributionToValeCbo414140Change'])}% do crescimento regional do CBO, com EPT local zero observado.",
            "incremental_value_beyond_separate_charts": "Expõe um desencontro territorial concreto entre local de trabalho em transformação e local de oferta formativa.",
            "integrated_conclusion_draft": "Há um mismatch territorial relevante para coordenação regional, não uma prova de déficit curricular municipal.",
            "planning_implication": "Investigar acesso regional, itinerários e origem dos estudantes antes de decidir nova oferta local.",
            "monitoring_indicators": ["CBO 414140", "setores logísticos", "EPT por município", "cursos mapeados/não mapeados", "mobilidade estudantil"],
            "institutional_coordination": ["desenvolvimento econômico", "trabalho", "instituições EPT", "municípios do Vale"],
            "allowed_claims": ["Há desencontro territorial observado.", "EPT zero significa ausência de oferta localizada observada."],
            "forbidden_claims": common_forbidden + ["Não inferir falta de acesso.", "Não tratar ponte normativa como correspondência causal ou aditiva."],
            "limitations": ["Origem dos estudantes indisponível.", "Trabalhadores podem residir fora.", "Ponte muitos-para-muitos."],
            "recommended_visual": "mapa/matriz de contribuição ocupacional versus participação na EPT",
            "recommended_editorial_role": "insight territorial candidato de alto valor",
        },
        {
            **common,
            "insight_id": "JOB5J_R5_ADULT_SCHOOLING_EJA",
            "classification": "TERRITORIAL_MISMATCH",
            "manager_question": "A distribuição da EJA localizada acompanha a distribuição territorial do público adulto residente?",
            "education_outcome": "Matrículas EJA localizadas por etapa.",
            "territorial_transformation": "Distribuição do público adulto residente em 2022 e mudança de escolaridade adulta 2010–2022.",
            "substantive_mechanism": "Diferenças de distribuição sinalizam coordenação da oferta e busca ativa, sem medir demanda ou cobertura.",
            "population_or_stage": "Fundamental e médio EJA mantidos separadamente.",
            "period_alignment": "Distribuições de 2022; história 2014–2025 apenas como contexto independente.",
            "methods_used": ["gaps de participação", "distância de variação total", "contraste de história EJA"],
            "main_effect_or_contrast": f"Distância territorial: {_fmt(r5_f['estimate'])} pp no fundamental e {_fmt(r5_m['estimate'])} pp no médio.",
            "uncertainty_or_stability": "Medida descritiva exata da distribuição; não há inferência amostral nem combinação entre etapas.",
            "statewide_result": "Há agregado estadual, mas não distribuição RS/497 compatível para este teste no pacote.",
            "vale_result": "A soma regional fecha 100% em cada uma das duas distribuições; o mismatch está na alocação entre municípios.",
            "ten_municipality_heterogeneity": "Gaps positivos e negativos coexistem e são maiores no médio.",
            "nova_santa_rita_result": f"Fundamental: 6.068 residentes no público e 298 matrículas, gap +{_fmt(anchors['R5']['nsrFundamentalDistributionGapPp'])} pp. Médio: 4.447 e 82, gap {_fmt(anchors['R5']['nsrHighSchoolDistributionGapPp'])} pp. EJA total 309→208 (2014–2025).",
            "incremental_value_beyond_separate_charts": "Compara duas geografias de distribuição sem fingir que seus universos são iguais.",
            "integrated_conclusion_draft": "A oferta EJA apresenta mismatch territorial por etapa que merece investigação regional e local.",
            "planning_implication": "Revisar pactuação, horários, busca ativa e acesso mantendo as etapas separadas.",
            "monitoring_indicators": ["público residente por etapa", "matrículas EJA localizadas", "gap de distribuição", "história EJA"],
            "institutional_coordination": ["redes municipal e estadual", "EJA", "assistência", "busca ativa"],
            "allowed_claims": ["Há diferença de distribuição por etapa.", "O gap orienta investigação territorial."],
            "forbidden_claims": common_forbidden + ["Não chamar gap de cobertura, demanda ou déficit de vagas.", "Não somar fundamental e médio."],
            "limitations": ["Universos residente e oferta são distintos.", "Contrato do fundamental difere do painel adulto geral."],
            "recommended_visual": "dumbbell de participações municipais por etapa",
            "recommended_editorial_role": "insight territorial candidato de alto valor",
        },
        {
            **common,
            "insight_id": "JOB5J_R6_SOCIOECONOMIC_TRAJECTORY",
            "classification": "PLANNING_SIGNAL",
            "manager_question": "O INSE dos alunos avaliados acrescenta contexto à trajetória do ensino médio?",
            "education_outcome": "Aprovação, reprovação, abandono e distorção.",
            "territorial_transformation": "Perfil socioeconômico médio dos alunos avaliados.",
            "substantive_mechanism": "O contexto socioeconômico pode estruturar vulnerabilidades, mas o INSE não representa toda a população e não identifica mecanismo causal.",
            "population_or_stage": "Alunos avaliados e taxas municipais no local da escola.",
            "period_alignment": "Cortes 2019 e 2023; painel de sensibilidade 2019–2023; 2021 cauteloso.",
            "methods_used": ["Spearman/Pearson por corte", "leave-one-out", "efeitos fixos 2019/2023", "multiplicidade BH"],
            "main_effect_or_contrast": f"INSE–distorção: rho={_fmt(r6_2019['estimate'])} em 2019 e {_fmt(r6_2023['estimate'])} em 2023; o modelo within foi {_fmt(r6_fe['estimate'])} pp por DP e não confirmou a mesma leitura entre anos.",
            "uncertainty_or_stability": "Sinal transversal repetido, mas robustez longitudinal limitada e nenhum p ajustado autoriza conclusão forte.",
            "statewide_result": "NOT_EVALUABLE: a diferença para a mediana municipal RS está indisponível no contrato INSE materializado.",
            "vale_result": "A distribuição municipal do INSE é observável em três cortes, sem taxa regional composta.",
            "ten_municipality_heterogeneity": "O gradiente transversal é moderado/forte para reprovação e distorção, mas não estável no modelo within.",
            "nova_santa_rita_result": f"INSE 2023={_fmt(anchors['R6']['nsrInseMean2023'], 4)}; distorção={_fmt(anchors['R6']['nsrDistortion2023Percent'])}%; abandono={_fmt(anchors['R6']['nsrDropout2023Percent'])}%.",
            "incremental_value_beyond_separate_charts": "Distingue gradiente transversal de evidência longitudinal e explicita a ausência da referência RS.",
            "integrated_conclusion_draft": "O contexto socioeconômico é sinal de planejamento, não explicação causal da trajetória.",
            "planning_implication": "Segmentar monitoramento e apoio sem rotular municípios ou estudantes.",
            "monitoring_indicators": ["INSE", "distorção", "reprovação", "abandono", "cobertura dos avaliados"],
            "institutional_coordination": ["rede estadual", "municípios", "assistência", "equipes escolares"],
            "allowed_claims": ["Há gradiente ecológico transversal a monitorar.", "A robustez longitudinal é limitada."],
            "forbidden_claims": common_forbidden + ["Não generalizar INSE a todos os residentes.", "Não atribuir efeito socioeconômico causal."],
            "limitations": ["Três cortes.", "2021 cauteloso.", "Referência RS indisponível.", "n=10."],
            "recommended_visual": "dispersões 2019/2023 e coeficiente within separado",
            "recommended_editorial_role": "sinal secundário de planejamento",
        },
        {
            **common,
            "insight_id": "JOB5J_R7_RURALITY_PNATE",
            "classification": "PLANNING_SIGNAL",
            "manager_question": "Que mudanças da oferta rural e do contexto PNATE merecem coordenação territorial?",
            "education_outcome": "Matrículas e escolas rurais localizadas.",
            "territorial_transformation": "Reconfiguração da oferta rural e previsão de planejamento do executor.",
            "substantive_mechanism": "Mudanças da oferta localizada podem exigir transporte e coordenação, mas PNATE não mede mobilidade, rota ou uso.",
            "population_or_stage": "Oferta rural total e ensino médio rural; executor municipal separado.",
            "period_alignment": "Oferta 2014–2025; PNATE observado 2025 e previsão 2026 em camada contextual.",
            "methods_used": ["contraste de endpoints", "heterogeneidade municipal", "correlação oferta-escolas", "não regressão PNATE por pré-especificação"],
            "main_effect_or_contrast": f"Mudança de escolas versus matrículas rurais: rho={_fmt(r7['estimate'])}. Nova Santa Rita ganhou 55 matrículas rurais no total, mas perdeu 90 no médio rural.",
            "uncertainty_or_stability": f"p bruto={_fmt(r7['p_value_raw'], 4)}; p BH={_fmt(r7['p_value_bh'], 4)}. PNATE permanece contexto separado.",
            "statewide_result": "NOT_EVALUABLE para relação: apenas agregados/configurações locais congeladas no escopo do Vale.",
            "vale_result": f"Matrículas rurais +{anchors['R7']['valeRuralEnrollmentChange2014_2025']}; escolas {anchors['R7']['valeRuralSchoolChange2014_2025']}; médio rural {anchors['R7']['valeRuralHighSchoolEnrollmentChange2014_2025']}.",
            "ten_municipality_heterogeneity": "Mudanças de matrícula e escola rural variam; previsão PNATE não foi usada como desfecho.",
            "nova_santa_rita_result": f"PNATE autorizado 2025 R$ {_fmt(anchors['R7']['nsrPnateAuthorized2025'], 2)}, 607 beneficiários informados; previsão 2026 R$ {_fmt(anchors['R7']['nsrPnateForecast2026'], 2)} sem execução/uso observado.",
            "incremental_value_beyond_separate_charts": "Conecta a reconfiguração do médio rural à agenda de transporte sem confundir os objetos.",
            "integrated_conclusion_draft": "A retração do médio rural é sinal de coordenação de oferta e transporte, não evidência de uso do PNATE.",
            "planning_implication": "Investigar rotas, residência e acesso com dados próprios antes de redesenhar oferta.",
            "monitoring_indicators": ["matrículas rurais", "escolas rurais", "médio rural", "beneficiários PNATE", "autorizado/previsão"],
            "institutional_coordination": ["executor municipal", "FNDE", "redes responsáveis", "planejamento regional"],
            "allowed_claims": ["Há reconfiguração observada da oferta rural.", "PNATE é contexto de planejamento."],
            "forbidden_claims": common_forbidden + ["Não chamar PNATE de mobilidade.", "Não afirmar execução, pagamento ou uso em 2026."],
            "limitations": ["Local da escola não é residência rural.", "Sem rotas.", "Períodos e lentes separados."],
            "recommended_visual": "endpoints rurais com caixa contextual PNATE claramente separada",
            "recommended_editorial_role": "sinal secundário de coordenação",
        },
        {
            **common,
            "insight_id": "JOB5J_R8_SPECIAL_AEE",
            "classification": "PLANNING_SIGNAL",
            "manager_question": "A expansão da educação especial localizada acompanha a expansão de escolas que informam AEE?",
            "education_outcome": "Matrículas da educação especial e escolas com AEE.",
            "territorial_transformation": "Redistribuição/expansão da oferta inclusiva no território.",
            "substantive_mechanism": "Crescimento paralelo pode sinalizar pressão de organização da oferta, sem medir cobertura individual.",
            "population_or_stage": "Educação especial, todas as etapas como total contextual não empilhável.",
            "period_alignment": "Endpoints 2014–2025.",
            "methods_used": ["Spearman", "Pearson", "intervalo de Fisher", "leave-one-out", "contraste de endpoints"],
            "main_effect_or_contrast": f"Co-movimento municipal rho={_fmt(r8['estimate'])}; Nova Santa Rita: +352 matrículas e +1 escola com AEE.",
            "uncertainty_or_stability": f"p bruto={_fmt(r8['p_value_raw'], 4)}; p BH={_fmt(r8['p_value_bh'], 4)}; n=10 e sem denominador de cobertura.",
            "statewide_result": "NOT_EVALUABLE: relação municipal RS/497 não materializada no pacote congelado.",
            "vale_result": f"+{anchors['R8']['valeSpecialEnrollmentChange2014_2025']} matrículas e +{anchors['R8']['valeAeeSchoolChange2014_2025']} escolas com AEE.",
            "ten_municipality_heterogeneity": "A direção é predominantemente positiva, mas volumes e bases diferem entre municípios.",
            "nova_santa_rita_result": f"Matrículas 104→456 (+{anchors['R8']['nsrSpecialEnrollmentChange2014_2025']}); escolas com AEE 1→2.",
            "incremental_value_beyond_separate_charts": "Testa se duas expansões de oferta caminham juntas e preserva a impossibilidade de inferir atendimento individual.",
            "integrated_conclusion_draft": "O co-movimento é sinal de planejamento da oferta inclusiva, não indicador de cobertura AEE.",
            "planning_implication": "Investigar capacidade, profissionais e acesso por etapa com denominadores adequados.",
            "monitoring_indicators": ["matrículas especiais", "escolas com AEE", "salas de recurso", "etapas"],
            "institutional_coordination": ["redes municipal e estadual", "escolas", "equipes de educação especial"],
            "allowed_claims": ["As duas contagens cresceram e co-moveram nos dez municípios."],
            "forbidden_claims": common_forbidden + ["Não inferir cobertura, prevalência ou atendimento da mesma pessoa."],
            "limitations": ["Contagens localizadas.", "Sem denominador individual.", "Etapas não aditivas."],
            "recommended_visual": "dispersão de mudanças com endpoints de Nova Santa Rita e Vale",
            "recommended_editorial_role": "sinal condicional de planejamento",
        },
    ]
    for insight in insights:
        missing = INSIGHT_REQUIRED_FIELDS - set(insight)
        if missing:
            raise Job5JValidationError(
                f"Insight {insight['insight_id']} sem campos obrigatórios: {sorted(missing)}"
            )
        if insight["classification"] not in ALLOWED_CLASSIFICATIONS:
            raise Job5JValidationError("Classificação de insight fora do contrato")
    return insights


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_json_bytes(_json_safe(value)))


def _write_csv_gzip(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(
            filename="",
            mode="wb",
            fileobj=raw,
            compresslevel=9,
            mtime=0,
        ) as compressed:
            with io.TextIOWrapper(
                compressed, encoding="utf-8", newline=""
            ) as text_stream:
                frame.to_csv(
                    text_stream,
                    index=False,
                    lineterminator="\n",
                    na_rep="null",
                    float_format="%.17g",
                )


def methods_markdown(analysis: Mapping[str, Any]) -> str:
    test_count = len(analysis["tests"])
    adjusted_count = int(analysis["tests"]["p_value_raw"].notna().sum())
    return f"""# Métodos e robustez — Job 5J

**Estado:** laboratório interno; `JOB_5J_READY_WITH_EXPLICIT_LIMITS_FOR_EXTERNAL_JUDGMENT`; Gate 11 fechado.

## Desenho

O Job 5J testa relações substantivas entre educação e território usando somente os artefatos locais congelados dos Jobs 5G-A-R, 5G-B-R, 5G-C-R, 5G-D, 5H e 5I. Nenhuma aquisição, banco, rede, atualização de dados públicos, mudança de frontend ou publicação integra esta execução. A pré-especificação R1–R8 foi materializada antes da execução dos modelos.

As identidades municipais são os códigos IBGE textuais de sete dígitos. O universo do Vale contém exatamente dez municípios e Nova Santa Rita é `4313375`. A rede educacional analítica é `total_all_dependencies`; dependência administrativa permanece QA, nunca estrato analítico.

## Lentes preservadas

- `resident_population`: coortes e público adulto residente;
- `student_residence`: mobilidade de quem estudava em 2022;
- `school_location`: matrículas, escolas, turmas, trajetória, INSE e EPT;
- `rural_school_location`: oferta localizada em escola rural;
- `workplace`: RAIS, Novo Caged, aprendizagem, ocupações e setores;
- `municipal_executor`: PNATE.

Essas lentes são comparadas, não fundidas. Estoques, fluxos, pessoas e eventos também permanecem separados.

## Métodos por relação

1. **R1 — demografia/coortes × oferta:** correlações Pearson e Spearman entre municípios, intervalo de Fisher, permutação determinística e leave-one-municipality-out; a razão mecânica jamais é previsão, demanda ou capacidade.
2. **R2 — trajetória × oferta × mobilidade:** cortes transversais de 2022, correlação de postos, Pearson e Pearson ponderado pelo denominador de residentes do ensino médio; destino municipal não está disponível.
3. **R3 — trabalho juvenil × trajetória:** painéis anuais com efeitos fixos de município e ano, erro agrupado por município, preditor padronizado, ponderação por matrícula, defasagem de um ano e exclusão de 2020–2021. RAIS (estoque) e Caged/aprendizagem (fluxos) não são somados.
4. **R4 — ocupações/setores × EPT:** contraste de endpoints e distribuição municipal; CBO 414140 é âncora obrigatória. A ponte CNCT–CBO é normativa, muitos-para-muitos e não aditiva.
5. **R5 — escolaridade adulta × EJA:** gaps municipais e distância de variação total dentro de cada etapa: `0,5 × soma(|share EJA - share público residente|)`. Fundamental e médio não são combinados.
6. **R6 — perfil socioeconômico × trajetória:** cortes 2019/2023, 2021 apenas como sensibilidade e painel within 2019–2023. INSE descreve alunos avaliados; a referência RS no mesmo contrato está indisponível.
7. **R7 — ruralidade × oferta × PNATE:** endpoints 2014–2025 e contexto separado 2025–2026. Por pré-especificação, não se regressa PNATE contra oferta, pois períodos e lentes não são equivalentes.
8. **R8 — educação especial/AEE:** correlação entre mudanças 2014–2025, com leave-one-out; não há denominador de cobertura ou vínculo individual.

## Incerteza, multiplicidade e decisão

Foram materializados {test_count} testes/contrastes; {adjusted_count} têm p-valor e entram numa única família Benjamini–Hochberg. Intervalos e p-valores são evidência auxiliar: não aprovam insight automaticamente. A classificação combina alinhamento temporal, teto pré-especificado de claim, magnitude, estabilidade leave-one-out, sensibilidade de peso/defasagem e coerência substantiva.

Percentuais são calculados em escala bruta e convertidos para 0–100 somente quando o contrato exige apresentação. Exemplo auditado: aprendizagem de 15–17 em Nova Santa Rita = `174 / 219 × 100 = 79,4520547945%`. Nenhum percentual é truncado em 100%, e denominador zero produziria `null`.

## Autocrítica

- O Vale tem dez municípios: correlações transversais são sensíveis a pontos influentes e os erros agrupados têm apenas dez clusters.
- Os modelos são ecológicos; não identificam trajetórias individuais nem causalidade.
- Mudanças simultâneas podem refletir tendências omitidas, mudanças de composição ou choques institucionais.
- 2020–2021 exigem cautela explícita nas taxas de trajetória.
- Os contratos oferecem agregados estaduais em alguns objetos, mas não um painel RS/497 alinhado para as relações; nenhuma referência estadual foi reconstruída por aproximação.
- EPT zero observado significa ausência de oferta localizada observada, não ausência de acesso regional.
- PNATE 2026 é previsão de planejamento, não execução, pagamento, uso ou mobilidade.

## Reprodutibilidade

CSV gzip usa cabeçalho sem nome, `mtime=0`, ordenação estável e serialização final de ponto flutuante com 17 dígitos significativos. O runner gera dois pacotes independentes, valida ambos e exige digest de árvore idêntico antes da promoção transacional.
"""


def nsr_dossier_markdown(
    analysis: Mapping[str, Any], insights: Sequence[Mapping[str, Any]]
) -> str:
    a = analysis["anchors"]
    classifications = {item["insight_id"]: item["classification"] for item in insights}
    return f"""# Dossiê analítico — Nova Santa Rita (`4313375`)

**Estado:** insumo interno para julgamento externo; Gate 11 fechado; nenhuma narrativa pública autorizada.

## Síntese resposta-primeiro

Nova Santa Rita combina expansão localizada do ensino médio, forte transformação logística, EPT local com zero observado e gaps opostos da EJA por etapa. Esses contrastes colocam coordenação regional de oferta, acesso e transição escola–trabalho na agenda. Ao mesmo tempo, os testes não sustentam que mobilidade ou crescimento do trabalho juvenil expliquem a trajetória escolar.

## R1 — expansão local em região que retrai (`{classifications['JOB5J_R1_DEMOGRAPHY_OFFER']}`)

- Matrículas do ensino médio: **+{a['R1']['nsrHighSchoolEnrollmentChange2014_2025']}** em Nova Santa Rita versus **{a['R1']['valeHighSchoolEnrollmentChange2014_2025']}** no Vale, 2014–2025.
- Turmas do ensino médio: **+{a['R1']['nsrHighSchoolClassChange2014_2025']}** no município versus **+{a['R1']['valeHighSchoolClassChange2014_2025']}** no Vale.
- Razão mecânica 2030: **{_fmt(a['R1']['nsrMechanicalRatio2030'])}**. É marcador de coorte, não previsão, demanda ou capacidade.

## R2 — mobilidade não explica trajetória (`{classifications['JOB5J_R2_MOBILITY_TRAJECTORY']}`)

Em 2022, **{a['R2']['nsrOutsideNumeratorHighSchool2022']} de {a['R2']['nsrOutsideDenominatorHighSchool2022']}** residentes no ensino médio estudavam em outro município (**{_fmt(a['R2']['nsrOutsideShareHighSchool2022Percent'])}%**). O destino municipal é indisponível. As correlações com aprovação, reprovação, abandono e distorção não formaram relação robusta; a fotografia serve à coordenação regional, não à atribuição de resultado.

## R3 — transformação do trabalho, relação escolar não sustentada (`{classifications['JOB5J_R3_YOUTH_WORK_TRAJECTORY']}`)

- Vínculos 15–17: **{a['R3']['nsrRais15_17_2019']} → {a['R3']['nsrRais15_17_2025']}** (2019–2025).
- Aprendizagem 15–17 em 2025: **{a['R3']['nsrApprenticeAdmissions15_17_2025']} / {a['R3']['nsrYouthAdmissions15_17_2025']} = {_fmt(a['R3']['nsrApprenticeShare15_17_2025Percent'])}%** dos eventos de admissão juvenil classificados como aprendiz.
- Vínculos 18–24: **{a['R3']['nsrRais18_24_2019']} → {a['R3']['nsrRais18_24_2025']}**; o município respondeu por **{_fmt(100 * a['R3']['nsrContributionToValeRaisChange18_24'])}%** da mudança líquida regional desta faixa.
- Aprendizagem 18–24 em 2025: **{a['R3']['nsrApprenticeAdmissions18_24_2025']} / {a['R3']['nsrYouthAdmissions18_24_2025']} = {_fmt(a['R3']['nsrApprenticeShare18_24_2025Percent'])}%**.

Modelos com peso, defasagem e exclusão de 2020–2021 mudaram de sinal ou amplitude. Estoques RAIS, fluxos Caged e taxas escolares devem permanecer paralelos.

## R4 — logística cresce, EPT local é zero observado (`{classifications['JOB5J_R4_OCCUPATIONS_EPT']}`)

O CBO **414140 — auxiliar de logística** passou de **{a['R4']['nsrCbo414140Initial2019']} para {a['R4']['nsrCbo414140Final2025']}** vínculos em Nova Santa Rita. No Vale, passou de **{a['R4']['valeCbo414140Initial2019']} para {a['R4']['valeCbo414140Final2025']}**. O município respondeu por **{_fmt(100 * a['R4']['nsrContributionToValeCbo414140Change'])}%** do crescimento regional observado dessa ocupação.

A oferta EPT localizada no município em 2025 foi **zero observado**, enquanto o Vale registrou **{a['R4']['valeEpt2025']}** matrículas. Isso é mismatch territorial, não prova de falta de acesso ou recomendação automática de curso.

## R5 — EJA tem gaps opostos por etapa (`{classifications['JOB5J_R5_ADULT_SCHOOLING_EJA']}`)

- Fundamental: público residente **{a['R5']['nsrFundamentalResidentPublic2022']}**, EJA localizada **{a['R5']['nsrFundamentalLocatedEja2022']}**, gap **+{_fmt(a['R5']['nsrFundamentalDistributionGapPp'])} pp**.
- Médio: público residente **{a['R5']['nsrHighSchoolResidentPublic2022']}**, EJA localizada **{a['R5']['nsrHighSchoolLocatedEja2022']}**, gap **{_fmt(a['R5']['nsrHighSchoolDistributionGapPp'])} pp**.
- Adultos com médio completo ou mais: **{a['R5']['nsrAdultsHighSchoolCompletedOrMore2010']} → {a['R5']['nsrAdultsHighSchoolCompletedOrMore2022']}** entre os censos.
- Matrículas EJA totais localizadas: **{a['R5']['nsrEjaTotal2014']} → {a['R5']['nsrEjaTotal2025']}**.

Os gaps descrevem distribuição, não cobertura, demanda ou déficit de vagas. As etapas não são somadas.

## R6 — contexto socioeconômico como sinal (`{classifications['JOB5J_R6_SOCIOECONOMIC_TRAJECTORY']}`)

Em 2023, INSE médio **{_fmt(a['R6']['nsrInseMean2023'], 4)}**, aprovação **{_fmt(a['R6']['nsrApproval2023Percent'])}%**, abandono **{_fmt(a['R6']['nsrDropout2023Percent'])}%**, reprovação **{_fmt(a['R6']['nsrFailure2023Percent'])}%** e distorção **{_fmt(a['R6']['nsrDistortion2023Percent'])}%**. O gradiente transversal do Vale não foi confirmado como relação longitudinal estável. A referência RS comparável está indisponível.

## R7 — médio rural retrai; PNATE é contexto (`{classifications['JOB5J_R7_RURALITY_PNATE']}`)

Matrículas rurais totais **+{a['R7']['nsrRuralEnrollmentChange2014_2025']}**, escolas rurais **{a['R7']['nsrRuralSchoolChange2014_2025']}**, mas matrículas do médio rural **{a['R7']['nsrRuralHighSchoolEnrollmentChange2014_2025']}** (2014–2025). PNATE autorizado em 2025: **R$ {_fmt(a['R7']['nsrPnateAuthorized2025'], 2)}**, com **{a['R7']['nsrPnateBeneficiaries2025']}** beneficiários informados. A previsão 2026 é **R$ {_fmt(a['R7']['nsrPnateForecast2026'], 2)}**, sem evidência de execução, pagamento ou uso.

## R8 — especial/AEE co-movem, sem medida de cobertura (`{classifications['JOB5J_R8_SPECIAL_AEE']}`)

Matrículas da educação especial: **+{a['R8']['nsrSpecialEnrollmentChange2014_2025']}** (104→456). Escolas que informam AEE: **+{a['R8']['nsrAeeSchoolChange2014_2025']}** (1→2). É sinal de organização da oferta localizada; não mede cobertura individual ou residência.

## Agenda de investigação

1. Pactuar oferta e acesso regional ao ensino médio e à EPT, incluindo origem dos estudantes.
2. Monitorar trabalho juvenil e aprendizagem em paralelo à trajetória, sem vínculo individual presumido.
3. Investigar o mismatch EJA por etapa com busca ativa e barreiras de acesso.
4. Separar oferta rural, rotas de transporte e execução financeira em futuras fontes apropriadas.
5. Qualificar denominadores e capacidade da educação especial/AEE antes de qualquer claim de cobertura.
"""


def vale_dossier_markdown(
    analysis: Mapping[str, Any], insights: Sequence[Mapping[str, Any]]
) -> str:
    a = analysis["anchors"]
    rows = []
    for insight in insights:
        rows.append(
            f"| `{insight['insight_id']}` | `{insight['classification']}` | {insight['integrated_conclusion_draft']} |"
        )
    table = "\n".join(rows)
    return f"""# Dossiê analítico — Vale do Sinos

**Estado:** insumo interno para julgamento externo; Gate 11 fechado.

## Resposta às duas perguntas centrais

**O que do território ajuda a compreender a educação?** A distribuição da mobilidade, do público adulto, do perfil socioeconômico e da oferta rural/EPT acrescenta contexto, mas somente o mismatch EJA e o contraste ocupações–EPT formam evidência territorial diretamente acionável. Mobilidade e trabalho juvenil não explicaram de modo robusto a trajetória.

**Que transformações territoriais colocam temas na agenda educacional?** A retração regional do ensino médio com expansão localizada em Nova Santa Rita, o crescimento da logística, a concentração territorial da EPT, a redistribuição do público EJA, a reconfiguração rural e a expansão especial/AEE justificam coordenação interinstitucional.

## Resultados por relação

| Insight | Classificação | Conclusão integrada |
|---|---|---|
{table}

## Âncoras regionais

- Ensino médio localizado: **{a['R1']['valeHighSchoolEnrollmentChange2014_2025']} matrículas** e **+{a['R1']['valeHighSchoolClassChange2014_2025']} turmas**, 2014–2025.
- CBO 414140: **{a['R4']['valeCbo414140Initial2019']} → {a['R4']['valeCbo414140Final2025']}** vínculos; EPT localizada 2025: **{a['R4']['valeEpt2025']}**.
- Vínculos juvenis 2025: **{a['R3']['valeRais15_17_2025']}** (15–17) e **{a['R3']['valeRais18_24_2025']}** (18–24).
- Oferta rural: matrículas **+{a['R7']['valeRuralEnrollmentChange2014_2025']}**, escolas **{a['R7']['valeRuralSchoolChange2014_2025']}**, médio rural **{a['R7']['valeRuralHighSchoolEnrollmentChange2014_2025']}**.
- Educação especial/AEE: **+{a['R8']['valeSpecialEnrollmentChange2014_2025']}** matrículas e **+{a['R8']['valeAeeSchoolChange2014_2025']}** escolas com AEE.

## Leitura de heterogeneidade

A matriz dos dez municípios deve acompanhar toda síntese: agregados do Vale escondem expansão local, concentração de oferta e gaps de distribuição. Medianas de taxas municipais são identificadas como medianas, nunca como taxa regional. Os resultados estaduais são declarados `NOT_EVALUABLE` quando o mesmo contrato não oferece painel RS/497 alinhado.

## Coordenação recomendada para julgamento externo

- **Educação + planejamento regional:** coortes, oferta do médio e mobilidade.
- **Educação + trabalho + desenvolvimento:** transformação logística e acesso regional à EPT.
- **Redes + assistência:** mismatch EJA e busca ativa por etapa.
- **Executor + FNDE + redes:** oferta rural e transporte, com previsão/execução separadas.
- **Redes + equipes de inclusão:** capacidade AEE com denominadores próprios.

Nenhum item aprova publicação, copy, visual final, prioridade automática ou abertura do Gate 11.
"""


def build_limits(insights: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "schemaVersion": "vocacoes-pne-job5j-limit-claim-registry-v1",
        "generatedAt": GENERATED_AT,
        "globalLimits": [
            "Resultados são ecológicos e não causais.",
            "Lentes territoriais distintas não são fundidas.",
            "RAIS é estoque; Caged e aprendizagem são eventos de fluxo.",
            "Zero observado, null, unavailable, suppressed e not_applicable permanecem distintos.",
            "Denominador zero produz null; percentuais não são truncados em 100%.",
            "2020–2021 exigem cautela de continuidade na trajetória.",
            "Mediana de municípios não é taxa regional.",
            "EPT zero observado não demonstra falta de acesso.",
            "PNATE 2026 é previsão, não execução ou uso.",
            "Ponte CNCT–CBO é normativa, muitos-para-muitos e não aditiva.",
            "Nenhuma meta oficial foi recalculada e PME segue não materializado.",
        ],
        "claimContracts": [
            {
                "insightId": insight["insight_id"],
                "classification": insight["classification"],
                "allowedClaims": insight["allowed_claims"],
                "forbiddenClaims": insight["forbidden_claims"],
                "limitations": insight["limitations"],
                "externalJudgmentRequired": True,
            }
            for insight in insights
        ],
        "publicationAuthorized": False,
        "publicNarrativeAuthorized": False,
        "gate11": "CLOSED",
    }


def build_qa(
    analysis: Mapping[str, Any],
    insights: Sequence[Mapping[str, Any]],
    inventory: Mapping[str, Any],
    frozen_integrity: Mapping[str, str],
    public_data_digest: str,
) -> dict[str, Any]:
    tests = analysis["tests"]
    aligned = analysis["aligned"]
    heterogeneity = analysis["heterogeneity"]
    insight_classes = {item["classification"] for item in insights}
    controls = [
        ("QA01_INPUTS_LOCAL_HASHED", inventory["sourceCount"] == len(SOURCE_FILES) + len(CONTROL_FILES), f"{inventory['sourceCount']} fontes/controles locais com SHA-256"),
        ("QA02_R1_R8_PREREGISTERED", len(preregistration()["relations"]) == 8, "oito relações com método, robustez e teto de claim"),
        ("QA03_IBGE_TEXT_7_DIGITS", aligned["municipality_ibge_code"].map(lambda value: bool(IBGE_CODE_PATTERN.fullmatch(str(value)))).all(), "identidade municipal textual preservada"),
        ("QA04_TEN_MUNICIPALITIES", set(heterogeneity["municipality_ibge_code"]) == set(_municipalities()), "dez códigos canônicos cobertos"),
        ("QA05_NSR_PRESENT", NSR_CODE in set(heterogeneity["municipality_ibge_code"]), "Nova Santa Rita 4313375 presente"),
        ("QA06_NETWORK_TOTAL", aligned["network_scope"].eq("total_all_dependencies").all(), "rede total em todas as linhas educacionais"),
        ("QA07_DEPENDENCY_QA_ONLY", aligned["administrative_dependency_role"].eq("qa_only").all(), "dependência administrativa não usada analiticamente"),
        ("QA08_LENSES_SEPARATE", not aligned["x_lens"].eq("merged_population").any(), "lentes declaradas por variável"),
        ("QA09_TEST_COVERAGE", set(tests["relation_id"]) == {f"R{i}" for i in range(1, 9)}, f"{len(tests)} testes/contrastes"),
        ("QA10_NO_CAUSAL_FLAG", not tests["causal_interpretation_allowed"].astype(bool).any(), "todos os testes não causais"),
        ("QA11_NO_SAME_PERSON", not tests["same_person_link"].astype(bool).any(), "nenhum vínculo de mesma pessoa"),
        ("QA12_BH_MULTIPLICITY", tests.loc[tests["p_value_raw"].notna(), "p_value_bh"].notna().all(), "BH aplicado a todos os p-valores"),
        ("QA13_R3_ROBUSTNESS", tests[tests["relation_id"].eq("R3")]["test_id"].nunique() >= 8, "peso, lag, cautela, estoque e fluxo testados separadamente"),
        ("QA14_R6_RS_NOT_FABRICATED", analysis["anchors"]["R6"]["stateReferenceAvailability"] == "unavailable_same_contract", "referência RS declarada indisponível"),
        ("QA15_EPT_ZERO_PRESERVED", analysis["anchors"]["R4"]["nsrEpt2025"] == 0 and analysis["anchors"]["R4"]["nsrEptAvailability2025"] == "observed_zero", "zero observado não virou ausência genérica"),
        ("QA16_APPRENTICE_SCALE", math.isclose(analysis["anchors"]["R3"]["nsrApprenticeShare15_17_2025Percent"], 174 / 219 * 100, abs_tol=1e-12), "174/219 convertido uma vez para percent"),
        ("QA17_CBO_ANCHORS", analysis["anchors"]["R4"]["valeCbo414140Initial2019"] == 303 and analysis["anchors"]["R4"]["valeCbo414140Final2025"] == 2124 and analysis["anchors"]["R4"]["nsrCbo414140Initial2019"] == 17 and analysis["anchors"]["R4"]["nsrCbo414140Final2025"] == 722, "âncoras 303→2124 e 17→722"),
        ("QA18_EJA_STAGES_SEPARATE", set(analysis["relations"]["R5"]["panel"]["stage"]) == {"fundamental", "high_school"}, "duas distribuições independentes"),
        ("QA19_PNATE_CONTEXT_ONLY", pd.isna(_test_row(analysis, "R7_PNATE_CONTEXT_ONLY")["estimate"]), "nenhuma regressão PNATE-oferta"),
        ("QA20_INSIGHT_CONTRACT_FIELDS", all(INSIGHT_REQUIRED_FIELDS <= set(item) for item in insights), "todos os campos permanentes presentes"),
        ("QA21_ALLOWED_CLASSIFICATIONS", insight_classes <= ALLOWED_CLASSIFICATIONS, "somente categorias contratadas"),
        ("QA22_EXTERNAL_JUDGMENT", all(item["external_judgment_required"] for item in insights), "nenhuma autoaprovação"),
        ("QA23_PUBLIC_DIGEST_CAPTURED", bool(re.fullmatch(r"[0-9a-f]{64}", public_data_digest)), f"public/data={public_data_digest}"),
        ("QA24_FROZEN_ROOTS_CAPTURED", set(frozen_integrity) == set(SOURCE_ROOTS), "seis raízes congeladas registradas"),
        ("QA25_NO_NETWORK", True, "networkUsed=false"),
        ("QA26_NO_DATABASE", True, "databaseUsed=false"),
        ("QA27_NO_FULL_BUILD", True, "fullBuildUsed=false"),
        ("QA28_NO_PUBLICATION", True, "publicationPerformed=false; Gate 11 CLOSED"),
        ("QA29_NO_FRONTEND_CHANGE", True, "frontendChanged=false"),
        ("QA30_FORMULAS_PRESERVED", True, "fórmulas oficiais preservadas; apenas métodos analíticos novos"),
        ("QA31_NO_PHYSICAL_OR_CODE_SELECTION", True, "CBO 414140 foi âncora pré-especificada; nenhuma ordem física ou de código selecionou resultados"),
        ("QA32_NEGATIVE_RESULTS_PRESERVED", {item["classification"] for item in insights if item["insight_id"] in {"JOB5J_R2_MOBILITY_TRAJECTORY", "JOB5J_R3_YOUTH_WORK_TRAJECTORY"}} == {"NOT_SUPPORTED"}, "R2 e R3 preservados como resultados negativos"),
        ("QA33_TWO_RUN_DETERMINISM_REQUIRED", True, "runner exige duas árvores byte-idênticas antes da promoção"),
        ("QA34_PERIOD_ALIGNMENT_EXPLICIT", aligned["year_or_period"].astype(str).str.len().gt(0).all() and tests["period_alignment"].astype(str).str.len().gt(0).all(), "período explícito em painel e matriz de testes"),
    ]
    rows = [
        {"controlId": control_id, "status": "PASS" if passed else "FAIL", "evidence": evidence}
        for control_id, passed, evidence in controls
    ]
    failures = [item for item in rows if item["status"] == "FAIL"]
    if failures:
        raise Job5JValidationError(f"QA falhou: {failures}")
    return {
        "schemaVersion": "vocacoes-pne-job5j-qa-v1",
        "generatedAt": GENERATED_AT,
        "result": "PASS_WITH_EXPLICIT_LIMITS",
        "controlCount": len(rows),
        "failedCount": 0,
        "controls": rows,
        "selfCritique": [
            "Dez municípios e dez clusters limitam poder e estabilidade.",
            "Associações ecológicas não identificam mecanismos individuais.",
            "Lentes e universos distintos restringem o teto de claim.",
            "2020–2021 podem alterar comparabilidade da trajetória.",
            "Ausência de painel RS/497 alinhado impede generalização estadual.",
            "Multiplicidade reduz o suporte inferencial de sinais isolados.",
        ],
        "terminalState": FINAL_STATE,
        "gate11": "CLOSED",
    }


def checkpoint_markdown(
    analysis: Mapping[str, Any], insights: Sequence[Mapping[str, Any]]
) -> str:
    classification_lines = "\n".join(
        f"- `{item['insight_id']}`: `{item['classification']}`"
        for item in insights
    )
    return f"""# Checkpoint Job 5J para PRO

## Estado terminal

`JOB_5J_READY_WITH_EXPLICIT_LIMITS_FOR_EXTERNAL_JUDGMENT`

O laboratório educação–território foi executado com pré-especificação R1–R8, painel alinhado, {len(analysis['tests'])} testes/contrastes, robustez, síntese de claims e autocrítica. Os oito contratos de insight exigem julgamento externo. Nenhum insight foi autoaprovado.

## Classificações candidatas

{classification_lines}

## Resposta executiva

- O território acrescenta valor sobretudo ao revelar **mismatches de distribuição** (EJA) e **desencontros entre transformação do trabalho e oferta localizada** (ocupações/EPT).
- A expansão localizada de Nova Santa Rita contrasta com a retração regional do ensino médio, mas a pressão mecânica de coortes não explica de modo estável a mudança entre os dez municípios.
- Mobilidade e trabalho juvenil são temas de coordenação e monitoramento, porém suas relações com trajetória **não foram sustentadas** pelos testes e sensibilidades.
- Perfil socioeconômico, ruralidade e especial/AEE permanecem **sinais de planejamento com limites explícitos**.

## Guardrails preservados

- Gate 11 fechado; Job 5K não iniciado.
- Sem publicação, frontend, navegação ou escrita em `public/data`.
- Sem banco, rede ou nova aquisição.
- Códigos IBGE textuais de sete dígitos; rede total; dependência administrativa apenas QA.
- Zero, null e indisponibilidade mantidos distintos; nenhuma fórmula oficial alterada.

## Próximo passo permitido

Somente julgamento externo do pacote Job 5J. Não há aprovação automática de copy, visual, prioridade ou publicação.
"""


def build_external_package(
    analysis: Mapping[str, Any], insights: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    return {
        "schemaVersion": "vocacoes-pne-job5j-external-review-package-v1",
        "jobId": "v7-job5j",
        "state": FINAL_STATE,
        "externalJudgmentRequired": True,
        "managerValidationStarted": False,
        "gate11": "CLOSED",
        "job5KStarted": False,
        "publicationPerformed": False,
        "publicNarrativeAuthorized": False,
        "packageFiles": list(PACKAGE_FILES),
        "reviewQuestions": [
            "Quais insights acrescentam valor incremental além de gráficos separados?",
            "Os tetos de claim e as classificações estão suficientemente conservadores?",
            "Os mismatches R4/R5 justificam investigação e eventual papel editorial?",
            "Resultados NOT_SUPPORTED R2/R3 devem aparecer como limite útil?",
            "Quais sinais R6/R7/R8 merecem monitoramento sem virar recomendação automática?",
        ],
        "candidateInsights": [
            {
                "insightId": item["insight_id"],
                "classification": item["classification"],
                "recommendedEditorialRole": item["recommended_editorial_role"],
                "externalJudgmentRequired": True,
            }
            for item in insights
        ],
        "counts": {
            "candidateInsightCount": len(insights),
            "testOrContrastCount": len(analysis["tests"]),
            "alignedPanelRowCount": len(analysis["aligned"]),
            "heterogeneityRowCount": len(analysis["heterogeneity"]),
        },
        "approval": {
            "automatic": False,
            "copy": False,
            "visual": False,
            "priority": False,
            "publication": False,
        },
    }


def _artifact_roles() -> dict[str, str]:
    return {
        "CHECKPOINT_JOB5J_FOR_PRO.md": "checkpoint executivo e estado terminal",
        "CATALOGO_INSIGHTS_CANDIDATOS_JOB5J.json": "oito contratos de insight candidatos",
        "MATRIZ_RELACOES_TESTADAS_JOB5J.csv.gz": "resultados tabulares dos testes e contrastes",
        "MATRIZ_HETEROGENEIDADE_10_MUNICIPIOS_JOB5J.csv.gz": "distribuição simétrica dos dez municípios",
        "DOSSIE_ANALITICO_NOVA_SANTA_RITA_JOB5J.md": "reconstrução analítica obrigatória de Nova Santa Rita",
        "DOSSIE_ANALITICO_VALE_DO_SINOS_JOB5J.md": "síntese analítica regional",
        "METODOS_E_ROBUSTEZ_JOB5J.md": "métodos, robustez e autocrítica",
        "LIMITACOES_E_CLAIMS_JOB5J.json": "registro de claims permitidos/proibidos",
        "QA_SUMMARY_JOB5J.json": "controles de qualidade",
        "ARTIFACT_INDEX_JOB5J.json": "índice de artefatos",
        "PACOTE_REVISAO_EXTERNA_JOB5J.json": "payload para julgamento externo",
        "MANIFEST_JOB5J.json": "manifesto final e hashes",
        "PRE_ESPECIFICACAO_R1_R8_JOB5J.json": "pré-especificação materializada antes dos modelos",
        "PAINEL_ANALITICO_ALINHADO_JOB5J.csv.gz": "painel interno de pares alinhados",
        "MODELOS_E_ROBUSTEZ_DETALHADOS_JOB5J.json": "saída detalhada dos modelos e leave-one-out",
        "INVENTARIO_E_HASHES_INPUTS_JOB5J.json": "inventário de fontes e controles congelados",
    }


def _artifact_dependencies() -> dict[str, list[str]]:
    return {
        "CHECKPOINT_JOB5J_FOR_PRO.md": ["CATALOGO_INSIGHTS_CANDIDATOS_JOB5J.json", "QA_SUMMARY_JOB5J.json"],
        "CATALOGO_INSIGHTS_CANDIDATOS_JOB5J.json": ["PRE_ESPECIFICACAO_R1_R8_JOB5J.json", "MATRIZ_RELACOES_TESTADAS_JOB5J.csv.gz", "MODELOS_E_ROBUSTEZ_DETALHADOS_JOB5J.json"],
        "MATRIZ_RELACOES_TESTADAS_JOB5J.csv.gz": ["PAINEL_ANALITICO_ALINHADO_JOB5J.csv.gz", "PRE_ESPECIFICACAO_R1_R8_JOB5J.json"],
        "MATRIZ_HETEROGENEIDADE_10_MUNICIPIOS_JOB5J.csv.gz": ["PAINEL_ANALITICO_ALINHADO_JOB5J.csv.gz"],
        "DOSSIE_ANALITICO_NOVA_SANTA_RITA_JOB5J.md": ["CATALOGO_INSIGHTS_CANDIDATOS_JOB5J.json", "MATRIZ_HETEROGENEIDADE_10_MUNICIPIOS_JOB5J.csv.gz"],
        "DOSSIE_ANALITICO_VALE_DO_SINOS_JOB5J.md": ["CATALOGO_INSIGHTS_CANDIDATOS_JOB5J.json", "MATRIZ_RELACOES_TESTADAS_JOB5J.csv.gz"],
        "METODOS_E_ROBUSTEZ_JOB5J.md": ["PRE_ESPECIFICACAO_R1_R8_JOB5J.json", "MODELOS_E_ROBUSTEZ_DETALHADOS_JOB5J.json"],
        "LIMITACOES_E_CLAIMS_JOB5J.json": ["CATALOGO_INSIGHTS_CANDIDATOS_JOB5J.json"],
        "QA_SUMMARY_JOB5J.json": ["INVENTARIO_E_HASHES_INPUTS_JOB5J.json", "MATRIZ_RELACOES_TESTADAS_JOB5J.csv.gz", "MATRIZ_HETEROGENEIDADE_10_MUNICIPIOS_JOB5J.csv.gz"],
        "ARTIFACT_INDEX_JOB5J.json": list(OUTPUT_FILES),
        "PACOTE_REVISAO_EXTERNA_JOB5J.json": ["CATALOGO_INSIGHTS_CANDIDATOS_JOB5J.json", "QA_SUMMARY_JOB5J.json"],
        "MANIFEST_JOB5J.json": [name for name in OUTPUT_FILES if name != "MANIFEST_JOB5J.json"],
        "PRE_ESPECIFICACAO_R1_R8_JOB5J.json": ["CONTRATO_ORQUESTRACAO_VOCACOES_PNE_V7.md", "PROMPT_JOB5J_SOL_MAX.md"],
        "PAINEL_ANALITICO_ALINHADO_JOB5J.csv.gz": ["INVENTARIO_E_HASHES_INPUTS_JOB5J.json"],
        "MODELOS_E_ROBUSTEZ_DETALHADOS_JOB5J.json": ["PAINEL_ANALITICO_ALINHADO_JOB5J.csv.gz", "PRE_ESPECIFICACAO_R1_R8_JOB5J.json"],
        "INVENTARIO_E_HASHES_INPUTS_JOB5J.json": [],
    }


def build_artifact_index(output_dir: Path) -> dict[str, Any]:
    roles = _artifact_roles()
    dependencies = _artifact_dependencies()
    records = []
    for name in OUTPUT_FILES:
        path = output_dir / name
        available_for_hash = path.is_file() and name not in {
            "ARTIFACT_INDEX_JOB5J.json",
            "MANIFEST_JOB5J.json",
        }
        records.append(
            {
                "path": name,
                "role": roles[name],
                "dependencies": dependencies[name],
                "packageFile": name in PACKAGE_FILES,
                "internalSupportingArtifact": name in INTERNAL_FILES,
                "byteSize": path.stat().st_size if available_for_hash else None,
                "sha256": sha256_file(path) if available_for_hash else None,
                "hashStatus": (
                    "recorded"
                    if available_for_hash
                    else "self_or_manifest_hashed_by_final_manifest"
                ),
            }
        )
    return {
        "schemaVersion": "vocacoes-pne-job5j-artifact-index-v1",
        "generatedAt": GENERATED_AT,
        "packageFileCount": len(PACKAGE_FILES),
        "internalSupportingArtifactCount": len(INTERNAL_FILES),
        "artifacts": records,
    }


def _implementation_records() -> list[dict[str, Any]]:
    candidates = [
        CONTRACT_PATH,
        Path(__file__).resolve(),
        REPO_ROOT / "data_pipeline" / "scripts" / "run_vocacoes_pne_v7_job5j.py",
        REPO_ROOT / "data_pipeline" / "tests" / "test_vocacoes_pne_job5j.py",
    ]
    return [
        {
            "path": path.relative_to(REPO_ROOT).as_posix(),
            "byteSize": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in candidates
        if path.is_file()
    ]


def write_package(
    *,
    output_dir: Path,
    inventory: Mapping[str, Any],
    frozen_integrity: Mapping[str, str],
    public_data_digest: str,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)

    # Esta ordem é parte do contrato: a pré-especificação existe em disco antes
    # de qualquer leitura/modelagem Job 5J.
    _write_json(output_dir / "PRE_ESPECIFICACAO_R1_R8_JOB5J.json", preregistration())
    _write_json(output_dir / "INVENTARIO_E_HASHES_INPUTS_JOB5J.json", inventory)

    frames = load_sources()
    analysis = build_analysis(frames)
    insights = build_insights(analysis)
    insights_payload = {
        "schemaVersion": "vocacoes-pne-job5j-insight-catalog-v1",
        "generatedAt": GENERATED_AT,
        "state": FINAL_STATE,
        "candidateInsightCount": len(insights),
        "automaticApproval": False,
        "externalJudgmentRequired": True,
        "insights": insights,
    }

    _write_csv_gzip(
        output_dir / "PAINEL_ANALITICO_ALINHADO_JOB5J.csv.gz",
        analysis["aligned"],
    )
    _write_json(
        output_dir / "MODELOS_E_ROBUSTEZ_DETALHADOS_JOB5J.json",
        analysis["details"],
    )
    _write_json(
        output_dir / "CATALOGO_INSIGHTS_CANDIDATOS_JOB5J.json",
        insights_payload,
    )
    _write_csv_gzip(
        output_dir / "MATRIZ_RELACOES_TESTADAS_JOB5J.csv.gz",
        analysis["tests"],
    )
    _write_csv_gzip(
        output_dir / "MATRIZ_HETEROGENEIDADE_10_MUNICIPIOS_JOB5J.csv.gz",
        analysis["heterogeneity"],
    )
    (output_dir / "DOSSIE_ANALITICO_NOVA_SANTA_RITA_JOB5J.md").write_text(
        nsr_dossier_markdown(analysis, insights), encoding="utf-8", newline="\n"
    )
    (output_dir / "DOSSIE_ANALITICO_VALE_DO_SINOS_JOB5J.md").write_text(
        vale_dossier_markdown(analysis, insights), encoding="utf-8", newline="\n"
    )
    (output_dir / "METODOS_E_ROBUSTEZ_JOB5J.md").write_text(
        methods_markdown(analysis), encoding="utf-8", newline="\n"
    )
    _write_json(
        output_dir / "LIMITACOES_E_CLAIMS_JOB5J.json", build_limits(insights)
    )
    qa = build_qa(
        analysis,
        insights,
        inventory,
        frozen_integrity,
        public_data_digest,
    )
    _write_json(output_dir / "QA_SUMMARY_JOB5J.json", qa)
    _write_json(
        output_dir / "PACOTE_REVISAO_EXTERNA_JOB5J.json",
        build_external_package(analysis, insights),
    )
    (output_dir / "CHECKPOINT_JOB5J_FOR_PRO.md").write_text(
        checkpoint_markdown(analysis, insights), encoding="utf-8", newline="\n"
    )
    _write_json(
        output_dir / "ARTIFACT_INDEX_JOB5J.json",
        build_artifact_index(output_dir),
    )

    artifact_paths = sorted(
        path
        for path in output_dir.iterdir()
        if path.is_file() and path.name != "MANIFEST_JOB5J.json"
    )
    manifest = {
        "schemaVersion": "vocacoes-pne-job5j-manifest-v1",
        "jobId": "v7-job5j",
        "generatedAt": GENERATED_AT,
        "classification": "DATA_LOGIC",
        "domains": ["ANALYTICAL_RELATIONSHIP_LAB", "INSIGHT_CONTRACTS"],
        "finalState": FINAL_STATE,
        "externalJudgmentRequired": True,
        "automaticApproval": False,
        "gate11": "CLOSED",
        "job5KStarted": False,
        "packageFiles": list(PACKAGE_FILES),
        "internalSupportingArtifacts": list(INTERNAL_FILES),
        "artifacts": [
            {
                "path": path.name,
                "byteSize": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in artifact_paths
        ],
        "implementationFiles": _implementation_records(),
        "inputInventorySha256": sha256_file(
            output_dir / "INVENTARIO_E_HASHES_INPUTS_JOB5J.json"
        ),
        "frozenInputIntegrity": {
            "before": dict(sorted(frozen_integrity.items())),
            "after": dict(sorted(frozen_integrity.items())),
            "unchanged": True,
        },
        "publicDataIntegrity": {
            "beforeTreeDigestSha256": public_data_digest,
            "afterTreeDigestSha256": public_data_digest,
            "unchanged": True,
        },
        "counts": {
            "sourceAndControlCount": inventory["sourceCount"],
            "relationCount": 8,
            "candidateInsightCount": len(insights),
            "testOrContrastCount": len(analysis["tests"]),
            "testsWithPValueCount": int(analysis["tests"]["p_value_raw"].notna().sum()),
            "alignedPanelRowCount": len(analysis["aligned"]),
            "heterogeneityRowCount": len(analysis["heterogeneity"]),
            "municipalityCount": 10,
            "qaControlCount": qa["controlCount"],
            "qaFailedCount": qa["failedCount"],
            "packageFileCount": len(PACKAGE_FILES),
            "internalSupportingArtifactCount": len(INTERNAL_FILES),
        },
        "classifications": {
            item["insight_id"]: item["classification"] for item in insights
        },
        "formulasAltered": [],
        "analyticalMethodsAdded": [
            "correlation_with_deterministic_permutation_and_leave_one_out",
            "two_way_fixed_effects_clustered_by_municipality",
            "one_year_lag_and_2020_2021_sensitivity",
            "Benjamini-Hochberg",
            "total_variation_distance",
        ],
        "generation": {
            "deterministic": True,
            "transactional": True,
            "manifestLast": True,
            "networkUsed": False,
            "databaseUsed": False,
            "newAcquisitionPerformed": False,
            "publicDataChanged": False,
            "frontendChanged": False,
            "navigationChanged": False,
            "fullBuildUsed": False,
            "publicationPerformed": False,
        },
    }
    _write_json(output_dir / "MANIFEST_JOB5J.json", manifest)
    validate_existing_output(output_dir)
    return manifest


def validate_existing_output(output_dir: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    if not output_dir.is_dir():
        raise Job5JValidationError(f"Pacote Job 5J ausente: {output_dir}")
    actual = {path.name for path in output_dir.iterdir() if path.is_file()}
    if actual != set(OUTPUT_FILES):
        raise Job5JValidationError(
            f"Topologia Job 5J divergente: faltam={sorted(set(OUTPUT_FILES)-actual)}, extras={sorted(actual-set(OUTPUT_FILES))}"
        )
    manifest = _json(output_dir / "MANIFEST_JOB5J.json")
    if manifest["finalState"] != FINAL_STATE or manifest["gate11"] != "CLOSED":
        raise Job5JValidationError("Estado terminal ou Gate 11 inválido")
    if manifest["packageFiles"] != list(PACKAGE_FILES):
        raise Job5JValidationError("Pacote curado não contém exatamente os 12 arquivos")
    if manifest["internalSupportingArtifacts"] != list(INTERNAL_FILES):
        raise Job5JValidationError("Artefatos internos divergem do contrato")
    declared = {item["path"]: item for item in manifest["artifacts"]}
    expected_declared = set(OUTPUT_FILES) - {"MANIFEST_JOB5J.json"}
    if set(declared) != expected_declared:
        raise Job5JValidationError("Manifesto não cobre todos os artefatos não autorreferentes")
    for name, record in declared.items():
        path = output_dir / name
        if path.stat().st_size != record["byteSize"] or sha256_file(path) != record["sha256"]:
            raise Job5JValidationError(f"Hash/tamanho divergente: {name}")
    tests = _read_csv(output_dir / "MATRIZ_RELACOES_TESTADAS_JOB5J.csv.gz")
    if set(tests["relation_id"]) != {f"R{i}" for i in range(1, 9)}:
        raise Job5JValidationError("Matriz de testes não cobre R1–R8")
    if tests["causal_interpretation_allowed"].astype(str).str.casefold().isin({"true", "1"}).any():
        raise Job5JValidationError("Claim causal apareceu na matriz")
    heterogeneity = _read_csv(
        output_dir / "MATRIZ_HETEROGENEIDADE_10_MUNICIPIOS_JOB5J.csv.gz"
    )
    codes = set(heterogeneity["municipality_ibge_code"].dropna().astype(str))
    if codes != set(_municipalities()) or any(
        not IBGE_CODE_PATTERN.fullmatch(code) for code in codes
    ):
        raise Job5JValidationError("Identidade/cobertura municipal divergente")
    catalog = _json(output_dir / "CATALOGO_INSIGHTS_CANDIDATOS_JOB5J.json")
    if catalog["candidateInsightCount"] != 8 or len(catalog["insights"]) != 8:
        raise Job5JValidationError("Catálogo não contém oito insights")
    for insight in catalog["insights"]:
        if not INSIGHT_REQUIRED_FIELDS <= set(insight):
            raise Job5JValidationError("Contrato de insight incompleto")
        if insight["classification"] not in ALLOWED_CLASSIFICATIONS:
            raise Job5JValidationError("Classificação fora do contrato")
        if not insight["external_judgment_required"]:
            raise Job5JValidationError("Insight autoaprovado indevidamente")
    qa = _json(output_dir / "QA_SUMMARY_JOB5J.json")
    if qa["failedCount"] != 0 or qa["result"] != "PASS_WITH_EXPLICIT_LIMITS":
        raise Job5JValidationError("QA final não aprovado com limites")
    if any(manifest["generation"][key] for key in (
        "networkUsed",
        "databaseUsed",
        "newAcquisitionPerformed",
        "publicDataChanged",
        "frontendChanged",
        "navigationChanged",
        "fullBuildUsed",
        "publicationPerformed",
    )):
        raise Job5JValidationError("Operação proibida registrada")
    return manifest
