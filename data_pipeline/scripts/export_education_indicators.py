#!/usr/bin/env python3
"""
Exportador JSON para Indicadores da Educacao.

Le as views SQL do banco sesi e gera JSONs estaticos em
public/data/educacao/ para consumo do dashboard React.

Estrutura de saida:
  public/data/educacao/index.json              (metadados leves)
  public/data/educacao/municipios/{id}.json    (1 por municipio RS)
  public/data/educacao/regioes/{slug}.json     (1 por regiao SENAI)
"""

import argparse
import json
import math
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import bindparam, text

DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.config import REPO_ROOT, SESI_DB_DIR  # noqa: E402
from src.education_municipality_routes import (  # noqa: E402
    EducationMunicipalityRouteCompatibilityError,
    build_education_municipalities_index_payload,
    load_education_municipality_route_compatibility,
)
from src.indigenous_education_coverage import build_coverage_contract  # noqa: E402
from src.municipality_registry import (  # noqa: E402
    MunicipalityRegistry,
    MunicipalityRegistryError,
    load_municipality_registry,
)
from src.school_infrastructure_materialization import (  # noqa: E402
    attach_school_infrastructure_contract,
    build_contracts,
)
from src.state_config import (  # noqa: E402
    DEFAULT_STATE_CODE,
    StateConfig,
    StateConfigError,
    load_state_config,
    normalize_state_code,
)
from src.education_transactional_publication import (  # noqa: E402
    EducationPublicationError,
    default_public_root,
    publish_education_transactionally,
    render_education_json,
    validate_education_staging,
)
from src.education_task_fingerprint import (  # noqa: E402
    TASK_ID as EDUCATION_TASK_ID,
    build_input_fingerprint,
    build_output_manifest,
    build_task_state,
    default_task_state_path,
    digest_contract_files,
    digest_education_sources,
    evaluate_shadow_eligibility,
    load_task_state,
    resolve_imported_python_module_contract,
    write_task_state_atomic,
)
from src.pipeline_profiling import (  # noqa: E402
    get_active_profile_session,
    profile_operation,
    profile_query,
    profiled_main_from_environment,
    record_tabular_result,
)

# ── Logging ────────────────────────────────────────────────────────────────

_START_TIME = time.time()


def log(msg, end="\n"):
    ts = datetime.now().strftime("%H:%M:%S")
    elapsed = time.time() - _START_TIME
    if elapsed < 60:
        print(f"[{ts} +{elapsed:.1f}s] {msg}", end=end, flush=True)
    else:
        print(f"[{ts} +{elapsed/60:.1f}min] {msg}", end=end, flush=True)


class Timer:
    def __init__(self, label):
        self.label = label

    def __enter__(self):
        self.start = time.time()
        log(f"Iniciando {self.label}...")
        self.profile_operation = profile_operation(
            "compute",
            f"education.{self.label}",
        )
        self.profile_operation.__enter__()
        return self

    def __exit__(self, *args):
        elapsed = time.time() - self.start
        log(f"{self.label} concluido em {elapsed:.2f}s")
        return self.profile_operation.__exit__(*args)


# ── Caminhos ─────────────────────────────────────────────────────────────

SESI_DB = SESI_DB_DIR
SAIDA: Path | None = None
SAIDA_MUN: Path | None = None
SAIDA_REG: Path | None = None
EDUCATION_RESULT_ENV = "PNE_EDUCATION_RESULT_PATH"
EDUCATION_RESULT_SCHEMA_VERSION = "education-run-result-v1"

sys.path.insert(0, str(SESI_DB))
DATA_EXPORTACAO = datetime.now().strftime("%Y-%m-%d")


def emit_education_result(**values) -> dict:
    """Publica resultado operacional sanitizado sem misturá-lo ao task state."""

    payload = {
        "schemaVersion": EDUCATION_RESULT_SCHEMA_VERSION,
        "reused": bool(values.get("reused", False)),
        "publicationNoop": bool(values.get("publication_noop", False)),
        "reason": str(values.get("reason", "integral")),
        "stagingCreated": int(values.get("staging_created", 0)),
        "municipalitiesMaterialized": int(
            values.get("municipalities_materialized", 0)
        ),
        "filesRendered": int(values.get("files_rendered", 0)),
        "bytesRendered": int(values.get("bytes_rendered", 0)),
        "filesValidated": int(values.get("files_validated", 0)),
        "promoted": bool(values.get("promoted", False)),
        "stateWritten": bool(values.get("state_written", False)),
    }
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    print(f"[education-result] {serialized}", flush=True)
    requested_path = os.environ.get(EDUCATION_RESULT_ENV)
    if not requested_path:
        return payload
    destination = Path(requested_path).resolve()
    forbidden_roots = (
        (REPO_ROOT / "public" / "data").resolve(),
        (DATA_PIPELINE_DIR / "data").resolve(),
    )
    if destination.suffix.casefold() != ".json" or any(
        destination == root or root in destination.parents for root in forbidden_roots
    ):
        raise EducationPublicationError(
            "Destino do resultado operacional educacional e inseguro."
        )
    if not destination.parent.is_dir():
        raise EducationPublicationError(
            "Diretorio do resultado operacional educacional nao existe."
        )
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    if temporary.exists():
        raise EducationPublicationError(
            "Temporario do resultado operacional educacional ja existe."
        )
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(serialized + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()
    return payload


def configure_education_output_root(output_root: Path) -> None:
    """Vincula todas as escritas do exportador a um staging ja isolado."""
    global SAIDA, SAIDA_MUN, SAIDA_REG
    SAIDA = Path(output_root).resolve()
    SAIDA_MUN = SAIDA / "municipios"
    SAIDA_REG = SAIDA / "regioes"

EDUCATION_VIEWS = (
    ("vw_educacao_matriculas", "matriculas"),
    ("vw_educacao_visao_geral_municipal", "matriculas_educacao_basica"),
    ("vw_educacao_matriculas_faixa_etaria", "matriculas_faixa_etaria"),
    ("vw_educacao_matriculas_cor_raca", "matriculas_cor_raca"),
    ("vw_educacao_rede_escolar", "rede_escolar"),
    ("vw_educacao_infraestrutura_escolar_ativa", "school_infrastructure"),
    ("vw_educacao_rede_escolar_etapa", "rede_escolar_etapa"),
    ("vw_educacao_turmas_docentes", "turmas"),
    ("vw_educacao_alunos_turma", "alunos_turma"),
    ("vw_educacao_fluxo", "fluxo"),
    ("vw_educacao_aprendizagem", "aprendizagem"),
    ("vw_educacao_oferta_tecnica", "oferta"),
    ("educacao_indigena_municipal", "educacao_indigena"),
    ("populacao_indigena_faixa_municipal", "populacao_indigena_faixas"),
    ("populacao_indigena_idade_municipal", "populacao_indigena_idades"),
    ("vw_educacao_sistema_s", "sistema_s"),
    ("vw_educacao_sistema_s_escolas", "sistema_s_escolas"),
    ("vw_vaar_municipio_dashboard", "vaar"),
)
ALLOWED_EDUCATION_VIEWS = frozenset(view for view, _key in EDUCATION_VIEWS)

# ── Helpers ───────────────────────────────────────────────────────────────


def limpar_null(valor):
    """Converte NaN/inf/None para None (null no JSON)."""
    if valor is None:
        return None
    try:
        if pd.isna(valor):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(valor, float) and (math.isnan(valor) or math.isinf(valor)):
        return None
    return valor


def r1(valor):
    """Arredonda para 1 casa decimal, preservando null."""
    v = limpar_null(valor)
    if v is None:
        return None
    return round(float(v), 1)


def ri(valor):
    """Converte para inteiro, preservando null."""
    v = limpar_null(valor)
    if v is None:
        return None
    return int(round(float(v)))


def slugify(texto):
    """Gera slug a partir de texto."""
    s = re.sub(r"[^\w\s-]", "", str(texto).lower().strip())
    s = re.sub(r"[\s_-]+", "-", s)
    s = re.sub(r"^-+|-+$", "", s)
    return s


def serie_anual(df, coluna_valor, coluna_extra=None):
    """Constroi serie [{ano, valor, ...}] ordenada por ano.
    Filtra linhas onde valor e null."""
    pontos = []
    for _, row in df.iterrows():
        valor = limpar_null(row.get(coluna_valor))
        if valor is None:
            continue
        ponto = {"ano": int(row["ano"]), "valor": valor}
        if coluna_extra and coluna_extra in row:
            extra = limpar_null(row.get(coluna_extra))
            if extra is not None:
                ponto[coluna_extra] = extra
        pontos.append(ponto)
    return pontos


def detalhamento_matriculas(df, dimensoes, filtros=None):
    """Constroi linhas longas de matriculas por ano e dimensoes.

    Mantem null como null, zero como zero e recalcula percentual_integral a
    partir dos totais agregados quando matriculas_integral estiver disponivel.
    """
    filtros = filtros or {}
    sub = df.copy()
    for coluna, valores in filtros.items():
        if valores is None:
            continue
        if not isinstance(valores, (list, tuple, set)):
            valores = [valores]
        sub = sub[sub[coluna].isin(valores)]

    if sub.empty:
        return []

    group_cols = ["ano", *dimensoes]
    agregados = (
        sub.groupby(group_cols, dropna=False)[["matriculas", "matriculas_integral"]]
        .sum(min_count=1)
        .reset_index()
        .sort_values(group_cols)
    )

    linhas = []
    for _, r in agregados.iterrows():
        matriculas = limpar_null(r["matriculas"])
        if matriculas is None:
            continue
        integral = limpar_null(r["matriculas_integral"])
        linha = {
            "ano": int(r["ano"]),
            "valor": ri(matriculas),
            "matriculas": ri(matriculas),
        }
        for dimensao in dimensoes:
            linha[dimensao] = r[dimensao]
        if integral is not None:
            linha["matriculas_integral"] = ri(integral)
            linha["percentual_integral"] = r1(integral / matriculas * 100) if matriculas > 0 else None
        linhas.append(linha)

    return linhas


def detalhamento_faixa_etaria(df, dimensoes, filtros=None):
    """Constroi recortes de matriculas por faixa etaria.

    As linhas ja chegam segmentadas por etapa e faixa etaria na Sinopse.
    Agregacoes sao apenas somas de matriculas, mantendo null como null.
    """
    filtros = filtros or {}
    sub = df.copy()
    for coluna, valores in filtros.items():
        if valores is None:
            continue
        if not isinstance(valores, (list, tuple, set)):
            valores = [valores]
        sub = sub[sub[coluna].isin(valores)]

    if sub.empty:
        return []

    group_cols = ["ano", *dimensoes]
    agregados = (
        sub.groupby(group_cols, dropna=False)["matriculas"]
        .sum(min_count=1)
        .reset_index()
        .sort_values(group_cols)
    )

    linhas = []
    for _, r in agregados.iterrows():
        matriculas = limpar_null(r["matriculas"])
        if matriculas is None:
            continue
        linha = {
            "ano": int(r["ano"]),
            "valor": ri(matriculas),
            "matriculas": ri(matriculas),
        }
        for dimensao in dimensoes:
            linha[dimensao] = r[dimensao]
        linhas.append(linha)

    return linhas


def detalhamento_cor_raca(df, dimensoes, filtros=None):
    """Constroi recortes de matriculas por cor/raca.

    A fonte preserva sexo e cor/raca; aqui agregamos por soma para permitir
    recortes municipais por etapa e por cor/raca no dashboard.
    """
    filtros = filtros or {}
    sub = df.copy()
    for coluna, valores in filtros.items():
        if valores is None:
            continue
        if not isinstance(valores, (list, tuple, set)):
            valores = [valores]
        sub = sub[sub[coluna].isin(valores)]

    if sub.empty:
        return []

    group_cols = ["ano", *dimensoes]
    agregados = (
        sub.groupby(group_cols, dropna=False)["matriculas"]
        .sum(min_count=1)
        .reset_index()
        .sort_values(group_cols)
    )

    linhas = []
    for _, r in agregados.iterrows():
        matriculas = limpar_null(r["matriculas"])
        if matriculas is None:
            continue
        linha = {
            "ano": int(r["ano"]),
            "valor": ri(matriculas),
            "matriculas": ri(matriculas),
        }
        for dimensao in dimensoes:
            linha[dimensao] = r[dimensao]
        linhas.append(linha)

    return linhas


def detalhamento_tempo_integral(df, dimensoes, filtros=None):
    """Constroi recortes de matriculas em tempo integral.

    Usa matriculas_integral como valor principal e recalcula o percentual a
    partir de somas agregadas: soma(integral) / soma(matriculas) * 100.
    """
    filtros = filtros or {}
    sub = df.copy()
    for coluna, valores in filtros.items():
        if valores is None:
            continue
        if not isinstance(valores, (list, tuple, set)):
            valores = [valores]
        sub = sub[sub[coluna].isin(valores)]

    if sub.empty:
        return []

    group_cols = ["ano", *dimensoes]
    agregados = (
        sub.groupby(group_cols, dropna=False)[["matriculas", "matriculas_integral"]]
        .sum(min_count=1)
        .reset_index()
        .sort_values(group_cols)
    )

    linhas = []
    for _, r in agregados.iterrows():
        integral = limpar_null(r["matriculas_integral"])
        if integral is None:
            continue
        matriculas = limpar_null(r["matriculas"])
        linha = {
            "ano": int(r["ano"]),
            "valor": ri(integral),
            "matriculas_integral": ri(integral),
            "matriculas_total": ri(matriculas),
            "percentual_integral": r1(integral / matriculas * 100) if matriculas and matriculas > 0 else None,
        }
        for dimensao in dimensoes:
            linha[dimensao] = r[dimensao]
        linhas.append(linha)

    return linhas


def detalhamento_rede_escolar(df, dimensoes, filtros=None):
    filtros = filtros or {}
    sub = df.copy()
    for coluna, valores in filtros.items():
        if not isinstance(valores, (list, tuple, set)):
            valores = [valores]
        sub = sub[sub[coluna].isin(valores)]
    if sub.empty:
        return []

    linhas = []
    for _, r in sub.sort_values(["ano", *dimensoes]).iterrows():
        escolas = limpar_null(r.get("escolas"))
        if escolas is None:
            continue
        linha = {
            "ano": int(r["ano"]),
            "valor": ri(escolas),
            "escolas": ri(escolas),
            "perc_internet": r1(limpar_null(r.get("perc_internet"))),
            "perc_banda_larga": r1(limpar_null(r.get("perc_banda_larga"))),
        }
        for dimensao in dimensoes:
            linha[dimensao] = r[dimensao]
        linhas.append(linha)
    return linhas


def detalhamento_escolas_etapa(df, dimensoes, filtros=None):
    """Detalhamento de escolas por etapa sem campos de infraestrutura."""
    filtros = filtros or {}
    sub = df.copy()
    for coluna, valores in filtros.items():
        if not isinstance(valores, (list, tuple, set)):
            valores = [valores]
        sub = sub[sub[coluna].isin(valores)]
    if sub.empty:
        return []
    linhas = []
    for _, r in sub.sort_values(["ano", *dimensoes]).iterrows():
        escolas = limpar_null(r.get("escolas"))
        if escolas is None:
            continue
        linha = {"ano": int(r["ano"]), "valor": ri(escolas), "escolas": ri(escolas)}
        for dimensao in dimensoes:
            linha[dimensao] = r[dimensao]
        linhas.append(linha)
    return linhas


def detalhamento_turmas(df, dimensoes, filtros=None):
    filtros = filtros or {}
    sub = df.copy()
    for coluna, valores in filtros.items():
        if not isinstance(valores, (list, tuple, set)):
            valores = [valores]
        sub = sub[sub[coluna].isin(valores)]
    if sub.empty:
        return []

    group_cols = ["ano", *dimensoes]
    agregados = (
        sub.groupby(group_cols, dropna=False)[["turmas", "docentes", "matriculas"]]
        .sum(min_count=1)
        .reset_index()
        .sort_values(group_cols)
    )
    linhas = []
    for _, r in agregados.iterrows():
        turmas = limpar_null(r.get("turmas"))
        docentes = limpar_null(r.get("docentes"))
        matriculas = limpar_null(r.get("matriculas"))
        if turmas is None and docentes is None and matriculas is None:
            continue
        linha = {
            "ano": int(r["ano"]),
            "valor": ri(turmas) if turmas is not None else None,
            "turmas": ri(turmas),
            "docentes": ri(docentes),
            "matriculas": ri(matriculas),
            "alunos_por_turma": r1(matriculas / turmas) if matriculas is not None and turmas and turmas > 0 else None,
            "alunos_por_docente": r1(matriculas / docentes) if matriculas is not None and docentes and docentes > 0 else None,
        }
        for dimensao in dimensoes:
            linha[dimensao] = r[dimensao]
        linhas.append(linha)
    return linhas


def detalhamento_fluxo(df, dimensoes, filtros=None, incluir_distorcao=True):
    filtros = filtros or {}
    sub = df.copy()
    for coluna, valores in filtros.items():
        if not isinstance(valores, (list, tuple, set)):
            valores = [valores]
        sub = sub[sub[coluna].isin(valores)]
    if sub.empty:
        return []

    linhas = []
    for _, r in sub.sort_values(["ano", *dimensoes]).iterrows():
        linha = {"ano": int(r["ano"])}
        for dimensao in dimensoes:
            linha[dimensao] = r[dimensao]
        for col in ["taxa_aprovacao", "taxa_reprovacao", "taxa_abandono"]:
            linha[col] = r1(limpar_null(r.get(col)))
        linha["valor"] = linha["taxa_aprovacao"]
        if incluir_distorcao:
            linha["taxa_distorcao"] = r1(limpar_null(r.get("taxa_distorcao")))
        if any(not limpar_null(linha.get(col)) is None for col in ["taxa_aprovacao", "taxa_reprovacao", "taxa_abandono", "taxa_distorcao"]):
            linhas.append(linha)
    return linhas


def detalhamento_aprendizagem(df, dimensoes, filtros=None):
    filtros = filtros or {}
    sub = df.copy()
    for coluna, valores in filtros.items():
        if not isinstance(valores, (list, tuple, set)):
            valores = [valores]
        sub = sub[sub[coluna].isin(valores)]
    if sub.empty:
        return []

    linhas = []
    for _, r in sub.sort_values(["ano", *dimensoes]).iterrows():
        linha = {"ano": int(r["ano"])}
        for dimensao in dimensoes:
            linha[dimensao] = r[dimensao]
        for col in ["ideb", "saeb_lp", "saeb_mt", "taxa_alfabetizacao", "media_inse"]:
            linha[col] = r1(limpar_null(r.get(col)))
        linha["qtd_alunos_inse"] = ri(limpar_null(r.get("qtd_alunos_inse")))
        if any(not limpar_null(linha.get(col)) is None for col in ["ideb", "saeb_lp", "saeb_mt", "taxa_alfabetizacao", "media_inse"]):
            linhas.append(linha)
    return linhas


def detalhamento_oferta(df, dimensoes, filtros=None):
    filtros = filtros or {}
    sub = df.copy()
    for coluna, valores in filtros.items():
        if not isinstance(valores, (list, tuple, set)):
            valores = [valores]
        sub = sub[sub[coluna].isin(valores)]
    if sub.empty:
        return []

    linhas = []
    for _, r in sub.sort_values(["ano", *dimensoes]).iterrows():
        matriculas = limpar_null(r.get("matriculas"))
        if matriculas is None:
            continue
        linha = {
            "ano": int(r["ano"]),
            "valor": ri(matriculas),
            "matriculas": ri(matriculas),
            "perc_modalidade": r1(limpar_null(r.get("perc_modalidade"))),
        }
        for dimensao in dimensoes:
            linha[dimensao] = r[dimensao]
        linhas.append(linha)
    return linhas


def safe_json_dump(data, path):
    """Escreve JSON deterministico no staging via arquivo temporario.

    Remove o temporario em caso de erro para nunca deixar lixo.
    """
    def clean(obj):
        if obj is None:
            return None
        try:
            if pd.isna(obj):
                return None
        except (TypeError, ValueError):
            pass
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj
        if isinstance(obj, dict):
            return {k: clean(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [clean(v) for v in obj]
        if isinstance(obj, (pd.Timestamp, datetime)):
            return obj.strftime("%Y-%m-%d")
        if hasattr(obj, "item"):
            return clean(obj.item())
        return obj

    data = clean(data)
    session = get_active_profile_session()
    serialization_started_ns = time.perf_counter_ns() if session is not None else 0
    serialized = render_education_json(data)
    if session is not None:
        session.accumulate_event(
            category="serialization",
            name="education.render_json",
            duration_ns=time.perf_counter_ns() - serialization_started_ns,
            counters={"payloads": 1, "bytesRendered": len(serialized)},
            metadata={"format": "json"},
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    try:
        write_started_ns = time.perf_counter_ns() if session is not None else 0
        with open(temp_path, "wb") as f:
            f.write(serialized)
            f.flush()
        if session is not None:
            session.accumulate_event(
                category="write",
                name="education.staging_writes",
                duration_ns=time.perf_counter_ns() - write_started_ns,
                counters={"filesWritten": 1, "bytesWritten": len(serialized)},
            )
        # Validar serializacao antes de substituir o arquivo do staging.
        validation_started_ns = time.perf_counter_ns() if session is not None else 0
        with open(temp_path, encoding="utf-8") as f:
            json.load(f, parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"Constante JSON nao finita: {value}")
            ))
        if session is not None:
            session.accumulate_event(
                category="validation",
                name="education.serialization_validation",
                duration_ns=time.perf_counter_ns() - validation_started_ns,
                counters={
                    "payloadsVerified": 1,
                    "filesRead": 1,
                    "bytesRead": len(serialized),
                },
            )
        promotion_started_ns = time.perf_counter_ns() if session is not None else 0
        temp_path.replace(path)
        if session is not None:
            session.accumulate_event(
                category="promotion",
                name="education.staging_file_promotion",
                duration_ns=time.perf_counter_ns() - promotion_started_ns,
                counters={"filesPromoted": 1, "bytesPromoted": len(serialized)},
            )
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise


# ── Mapeamento de métricas de infraestrutura ────────────────────────────
# Cada tupla: (key_export, coluna_count_sql, coluna_percentual_export)
# Usa os mesmos campos do censo escolar usados no PNE 2026-2036.
INFRA_METRICAS = [
    ("internet", "escolas_com_internet", "perc_internet"),
    ("internet_alunos", "escolas_com_internet_alunos", "perc_internet_alunos"),
    ("internet_aprendizagem", "escolas_com_internet_aprendizagem", "perc_internet_aprendizagem"),
    ("internet_comunidade", "escolas_com_internet_comunidade", "perc_internet_comunidade"),
    ("acesso_internet_computador", "escolas_com_acesso_internet_computador", "perc_acesso_internet_computador"),
    ("acesso_internet_disp_pessoais", "escolas_com_acesso_internet_disp_pessoais", "perc_acesso_internet_disp_pessoais"),
    ("banda_larga", "escolas_com_banda_larga", "perc_banda_larga"),
    ("rede_local", "escolas_com_rede_local", "perc_rede_local"),
    ("rede_wireless", None, "perc_rede_wireless"),
    ("desktop_aluno", "escolas_com_desktop_aluno", "perc_desktop_aluno"),
    ("comp_portatil_aluno", "escolas_com_comp_portatil_aluno", "perc_comp_portatil_aluno"),
    ("tablet_aluno", "escolas_com_tablet_aluno", "perc_tablet_aluno"),
    ("salas_climatizadas", "qt_salas_utiliza_climatizadas", "perc_salas_climatizadas"),
    ("salas_acessiveis", "qt_salas_utilizadas_acessiveis", "perc_salas_acessiveis"),
]

# ── Ano de inicio por metrica de infra ───────────────────────────────────
# Espelha os ``start_year`` definidos no pipeline PNE 2026-2036
# (data_pipeline/src/pne/calculations_2026.py). Metrica sem entrada aqui
# herda o padrao (primeiro ano disponivel na view).
INFRA_START_YEARS = {
    "internet": 2014,
    "internet_alunos": 2019,
    "internet_aprendizagem": 2019,
    "internet_comunidade": 2019,
    "acesso_internet_computador": 2019,
    "acesso_internet_disp_pessoais": 2019,
    "banda_larga": 2014,
    "rede_local": 2019,
    "rede_wireless": 2019,
    "desktop_aluno": 2019,
    "comp_portatil_aluno": 2019,
    "tablet_aluno": 2019,
    "salas_climatizadas": 2019,
    "salas_acessiveis": 2019,
}

# ── Grupos de infraestrutura ─────────────────────────────────────────────
# Organiza as metricas de INFRA_METRICAS em grupos visuais para o front.
GRUPOS_INFRA = {
    "conectividade": {
        "label": "Conectividade",
        "metricas": [
            "internet", "internet_alunos", "internet_aprendizagem",
            "internet_comunidade", "banda_larga",
        ],
    },
    "rede_e_dispositivos": {
        "label": "Rede e dispositivos",
        "metricas": [
            "acesso_internet_computador", "acesso_internet_disp_pessoais",
            "rede_local", "rede_wireless",
            "desktop_aluno", "comp_portatil_aluno", "tablet_aluno",
        ],
    },
    "ambiente_escolar": {
        "label": "Ambiente escolar",
        "metricas": ["salas_climatizadas", "salas_acessiveis"],
    },
}

# ── Fontes e avisos globais ──────────────────────────────────────────────

FONTES = [
    {"nome": "INEP - Censo Escolar", "tabelas": ["censo", "censo_escolas"]},
    {"nome": "INEP - Media de Alunos por Turma (ATU)", "tabelas": ["alunos_turma"]},
    {"nome": "INEP - Sinopse Estatistica do Censo Escolar", "tabelas": [
        "matriculas_faixa_etaria", "docentes_pos_graduacao",
        "ept_nivel_medio", "eja_integrada_educacao_profissional",
        "educacao_indigena_municipal",
    ]},
    {"nome": "IBGE - Censo Demografico 2022", "tabelas": [
        "populacao_indigena_idade_municipal",
        "populacao_indigena_faixa_municipal",
    ]},
    {"nome": "INEP - Taxas de Rendimento Escolar", "tabelas": ["rendimento_escolar"]},
    {"nome": "INEP - Distorcao Idade-Serie", "tabelas": ["distorcao_idade_serie"]},
    {"nome": "INEP - SAEB/IDEB", "tabelas": ["saeb_ideb", "saeb_proficiencia"]},
    {"nome": "INEP - INSE", "tabelas": ["inse"]},
    {"nome": "INEP - Alfabetizacao", "tabelas": ["alfabetizacao"]},
    {"nome": "INEP - Censo Escolar (Sistema S)", "tabelas": ["censo_escolas"]},
    {"nome": "VAAR/FUNDEB", "tabelas": ["vw_vaar_municipio_dashboard"]},
]

AVISOS_GLOBAIS = [
    "null significa dado ausente, nao zero.",
    "Cobertura varia por indicador: Censo 2014-2025, Rendimento 2018-2025, "
    "Distorcao 2019-2025, IDEB bienal 2011-2025, INSE 2019/2021/2023.",
]

AVISOS_FLUXO = [
    "taxa_distorcao nao tem dimensoes de localizacao na fonte original. "
    "O valor exibido para urbana/rural e o mesmo do total municipal.",
    "Prefira usar localizacao=total para analises de distorcao.",
]

AVISOS_TURMAS = [
    "alunos_por_docente pode apresentar valores altos em EJA e Educacao Infantil "
    "devido a poucos docentes reportados para muitas matriculas.",
]

AVISOS_ALUNOS_TURMA = [
    "ATU usa medias oficiais da planilha do INEP; totais nao sao recalculados "
    "por media de medias.",
]

AVISOS_APRENDIZAGEM = [
    "IDEB e avaliado bienalmente (2011-2025). Anos sem avalicao tem null.",
    "Alfabetizacao disponivel apenas para 2023-2025.",
    "INSE disponivel para 2019, 2021 e 2023.",
]

AVISOS_OFERTA = [
    "perc_modalidade tem alta taxa de null (municipios sem oferta em determinada modalidade).",
]

AVISOS_EDUCACAO_INDIGENA = [
    "A série municipal está disponível de 2023 a 2025 nas tabelas específicas "
    "de Educação Indígena da Sinopse Estatística do Censo Escolar.",
    "Os totais e os recortes por etapa são valores oficiais publicados pelo Inep; "
    "não são recalculados pela soma dos componentes.",
    "Ensino Médio, Educação Profissional e Educação Especial têm quebra conceitual "
    "entre os leiautes de 2024 e 2025 e não recebem variação automática.",
    "O retrato não informa rede administrativa, localização, zona, território, "
    "terra indígena, povo, língua ou categoria diferenciada.",
]


# ── Carregamento de dados ────────────────────────────────────────────────


def _get_education_engine():
    """Importa o adaptador externo somente depois da validação estadual."""
    from utils_educacao import get_engine

    return get_engine("sesi")


def _validate_municipality_codes(
    frame,
    registry,
    *,
    source,
    require_complete=False,
):
    if "id_municipio" not in frame.columns:
        raise ValueError(f"{source}: coluna id_municipio ausente.")
    values = frame["id_municipio"].dropna().tolist()
    invalid = sorted(
        {
            repr(value)
            for value in values
            if not isinstance(value, str) or re.fullmatch(r"\d{7}", value) is None
        }
    )
    if invalid:
        raise ValueError(
            f"{source}: códigos IBGE devem permanecer texto com sete dígitos; "
            f"inválidos={invalid[:5]}."
        )
    observed = set(values)
    extra = sorted(observed - registry.ids)
    missing = sorted(registry.ids - observed) if require_complete else []
    if extra or missing:
        raise ValueError(
            f"{source}: universo municipal diverge do registro de "
            f"{registry.state_code}; ausentes={missing[:5]}, extras={extra[:5]}."
        )


def carregar_municipios(
    engine,
    state_config: StateConfig,
    registry: MunicipalityRegistry,
):
    """Carrega somente atributos regionais; identidade vem do registro."""
    query = text(
        "SELECT id_municipio, municipio, regiao_senai "
        "FROM municipios "
        "WHERE sigla_uf = :state_code "
        "AND id_municipio IN :municipality_ids"
    ).bindparams(bindparam("municipality_ids", expanding=True))
    with profile_query(
        "education.municipalities",
        metadata={
            "datasetId": "municipalities",
            "backend": "postgres_local",
            "parametersBound": True,
            "municipalityFilter": "database",
        },
    ) as query_event:
        frame = pd.read_sql_query(
            query,
            engine,
            params={
                "state_code": state_config.state_code,
                "municipality_ids": tuple(
                    record.ibge_code for record in registry.ordered_records
                ),
            },
        )
        record_tabular_result(query_event, frame)
        query_event.add_counter(
            "municipalitiesRequested", registry.municipality_count
        )
        query_event.add_counter("municipalitiesQueried", len(frame))
    _validate_municipality_codes(
        frame,
        registry,
        source="tabela municipios",
        require_complete=True,
    )
    duplicated = frame["id_municipio"].duplicated(keep=False)
    if duplicated.any():
        raise ValueError(
            "tabela municipios: códigos duplicados: "
            f"{sorted(frame.loc[duplicated, 'id_municipio'].unique())[:5]}."
        )
    rows_by_id = frame.set_index("id_municipio").to_dict("index")
    name_mismatches = [
        record.ibge_code
        for record in registry.ordered_records
        if rows_by_id[record.ibge_code].get("municipio") != record.name
    ]
    if name_mismatches:
        raise ValueError(
            "tabela municipios: nomes divergem do registro canônico: "
            f"{name_mismatches[:5]}."
        )
    return pd.DataFrame(
        [
            {
                "id_municipio": record.ibge_code,
                "municipio": record.name,
                "regiao_senai": rows_by_id[record.ibge_code].get("regiao_senai"),
            }
            for record in registry.ordered_records
        ]
    )


def carregar_view(
    engine,
    view,
    municipality_ids,
    registry: MunicipalityRegistry,
):
    """Carrega uma fonte municipal usando parâmetros vinculados do registro."""
    if view not in ALLOWED_EDUCATION_VIEWS:
        raise ValueError(f"View educacional não autorizada: {view!r}.")
    query = text(
        f"SELECT * FROM {view} WHERE id_municipio IN :municipality_ids"
    ).bindparams(bindparam("municipality_ids", expanding=True))
    with profile_query(
        f"education.view.{view}",
        metadata={
            "datasetId": view,
            "backend": "postgres_local",
            "parametersBound": True,
            "municipalityFilter": "database",
        },
    ) as query_event:
        frame = pd.read_sql_query(
            query,
            engine,
            params={"municipality_ids": tuple(municipality_ids)},
        )
        record_tabular_result(query_event, frame)
        query_event.add_counter("municipalitiesRequested", len(municipality_ids))
        queried = (
            frame["id_municipio"].nunique()
            if "id_municipio" in frame.columns
            else 0
        )
        query_event.add_counter("municipalitiesQueried", int(queried))
    _validate_municipality_codes(frame, registry, source=view)
    return frame


# ── Bloco: VAAR/FUNDEB ────────────────────────────────────────────────

VAAR_CAMPOS_RESUMO = [
    "ano_fundeb",
    "habilitado_condicionalidades",
    "recebe_aprendizagem",
    "recebe_atendimento",
    "melhorou_aprendizagem",
    "melhorou_atendimento",
    "motivo_aprendizagem",
    "motivo_atendimento",
    "coeficiente_total",
    "metodologia_vaar",
]

VAAR_CAMPOS_APRENDIZAGEM = [
    "ano_fundeb",
    "indicador_aprendizagem",
    "delta_aprendizagem",
    "delta_aprendizagem_ajustado",
    "iad",
    "iad_ajustado",
    "proporcao_adequada_saeb_2019",
    "proporcao_adequada_saeb_2023",
    "taxa_aprovacao_penalizada_2019",
    "taxa_aprovacao_penalizada_2023",
    "equidade_2023",
]

VAAR_CAMPOS_ATENDIMENTO = [
    "ano_fundeb",
    "indicador_atendimento_anterior",
    "indicador_atendimento_atual",
    "delta_atendimento",
    "delta_atendimento_ajustado",
    "estudantes_areas_prioritarias_anterior",
    "estudantes_areas_prioritarias_atual",
    "proporcao_abandono_anterior",
    "proporcao_abandono_atual",
    "proporcao_sem_informacao_anterior",
    "proporcao_sem_informacao_atual",
]

VAAR_CAMPOS_METODOLOGIA_ANTERIOR = [
    "ano_fundeb",
    "metodologia_vaar",
    "indicador_atendimento_metodologia_anterior",
    "evolucao_atendimento_metodologia_anterior",
    "coeficiente_atendimento",
    "indicador_aprendizagem_metodologia_anterior",
    "evolucao_aprendizagem_metodologia_anterior",
    "coeficiente_aprendizagem",
    "coeficiente_total",
    "apresentou_evolucao_nos_dois_indicadores",
]

VAAR_CAMPOS_INTEIROS = {
    "ano_fundeb",
    "estudantes_areas_prioritarias_anterior",
    "estudantes_areas_prioritarias_atual",
}

VAAR_CAMPOS_BOOLEANOS = {
    "habilitado_condicionalidades",
    "recebe_aprendizagem",
    "recebe_atendimento",
    "melhorou_aprendizagem",
    "melhorou_atendimento",
    "apresentou_evolucao_nos_dois_indicadores",
}

VAAR_OBSERVACOES_METODOLOGICAS = [
    "Os exercicios de 2023 e 2024 seguem metodologia anterior e nao devem ser comparados diretamente aos indicadores de 2025 e 2026."
]

def _valor_vaar(valor, campo):
    """Converte escalares VAAR para JSON sem transformar ausência em zero."""
    valor = limpar_null(valor)
    if valor is None:
        return None
    if campo in VAAR_CAMPOS_INTEIROS:
        return ri(valor)
    if campo in VAAR_CAMPOS_BOOLEANOS:
        return bool(valor)
    if isinstance(valor, (int, float)) or hasattr(valor, "item"):
        return round(float(valor), 6)
    return valor


def _linha_vaar(row, campos):
    return {campo: _valor_vaar(row.get(campo), campo) for campo in campos}


def montar_bloco_vaar(df, id_mun):
    """Constroi resumo e series anuais VAAR para um municipio."""
    d = df[df["id_municipio"] == id_mun].copy()
    if d.empty:
        return {
            "anos": [],
            "anos_disponiveis": [],
            "ultimo_ano": None,
            "resumo_ultimo_ano": {},
            "historico": [],
            "aprendizagem": [],
            "atendimento": [],
            "historico_recebimento": [],
            "metodologia_anterior": [],
            "metodologias": {},
            "observacoes_metodologicas": VAAR_OBSERVACOES_METODOLOGICAS,
            "series": {},
            "dimensoes_disponiveis": ["ano_fundeb", "componente"],
            "campos_indisponiveis": ["sem_dados"],
            "fonte": "VAAR/FUNDEB",
        }

    d = d.sort_values("ano_fundeb").drop_duplicates("ano_fundeb", keep="last")
    anos = [int(ano) for ano in d["ano_fundeb"].tolist()]
    historico = []
    aprendizagem = []
    atendimento = []
    metodologia_anterior = []
    metodologias = {}

    for _, row in d.iterrows():
        resumo = _linha_vaar(row, VAAR_CAMPOS_RESUMO)
        metodologia = resumo.get("metodologia_vaar")
        if metodologia:
            metodologias[str(int(row["ano_fundeb"]))] = metodologia
        historico.append({
            **resumo,
            "indicador_aprendizagem": _valor_vaar(
                row.get("indicador_aprendizagem"), "indicador_aprendizagem"
            ),
            "delta_aprendizagem": _valor_vaar(
                row.get("delta_aprendizagem"), "delta_aprendizagem"
            ),
            "indicador_atendimento_atual": _valor_vaar(
                row.get("indicador_atendimento_atual"),
                "indicador_atendimento_atual",
            ),
            "delta_atendimento": _valor_vaar(
                row.get("delta_atendimento"), "delta_atendimento"
            ),
            "coeficiente_total": _valor_vaar(
                row.get("coeficiente_total"), "coeficiente_total"
            ),
        })
        if metodologia == "metodologia_atual":
            aprendizagem.append(_linha_vaar(row, VAAR_CAMPOS_APRENDIZAGEM))
            atendimento.append(_linha_vaar(row, VAAR_CAMPOS_ATENDIMENTO))
        elif metodologia == "metodologia_anterior":
            metodologia_anterior.append(
                _linha_vaar(row, VAAR_CAMPOS_METODOLOGIA_ANTERIOR)
            )

    resumo_ultimo_ano = _linha_vaar(d.iloc[-1], VAAR_CAMPOS_RESUMO)
    return {
        "anos": anos,
        "anos_disponiveis": anos,
        "ultimo_ano": anos[-1],
        "resumo_ultimo_ano": resumo_ultimo_ano,
        "historico": historico,
        "aprendizagem": aprendizagem,
        "atendimento": atendimento,
        "historico_recebimento": historico,
        "metodologia_anterior": metodologia_anterior,
        "metodologias": metodologias,
        "observacoes_metodologicas": VAAR_OBSERVACOES_METODOLOGICAS,
        "series": {"historico": historico},
        "dimensoes_disponiveis": ["ano_fundeb", "componente"],
        "campos_indisponiveis": [],
        "fonte": "VAAR/FUNDEB",
    }


# ── Bloco: Matriculas ────────────────────────────────────────────────────


ETAPAS_FUNDAMENTAL_DETALHADAS = {
    "fundamental_anos_iniciais",
    "fundamental_anos_finais",
}

CENSO_DEPENDENCIAS = ("federal", "estadual", "municipal", "privada")
CENSO_LOCALIZACOES = ("urbana", "rural")


def _normalizar_matriculas_educacao_basica(df, id_mun):
    """Agrega QT_MAT_BAS sem recompô-lo pela soma de etapas/modalidades."""
    colunas = [
        "ano",
        "id_municipio",
        "dependencia",
        "localizacao",
        "matriculas",
        "matriculas_integral",
    ]
    if df is None or df.empty:
        return pd.DataFrame(columns=colunas)

    obrigatorias = {
        "ano",
        "id_municipio",
        "dependencia",
        "localizacao",
        "mat_basico",
    }
    ausentes = obrigatorias - set(df.columns)
    if ausentes:
        raise ValueError(
            "Fonte oficial da Educação Básica sem colunas obrigatórias: "
            f"{sorted(ausentes)}"
        )

    base = df[
        (df["id_municipio"] == id_mun)
        & df["dependencia"].isin(CENSO_DEPENDENCIAS)
        & df["localizacao"].isin(CENSO_LOCALIZACOES)
    ][
        ["ano", "id_municipio", "dependencia", "localizacao", "mat_basico"]
    ].copy()
    if base.empty:
        return pd.DataFrame(columns=colunas)

    base = (
        base.groupby(
            ["ano", "id_municipio", "dependencia", "localizacao"],
            as_index=False,
        )["mat_basico"]
        .sum(min_count=1)
        .rename(columns={"mat_basico": "matriculas"})
    )
    publica = (
        base[base["dependencia"].isin(("federal", "estadual", "municipal"))]
        .groupby(["ano", "id_municipio", "localizacao"], as_index=False)[
            "matriculas"
        ]
        .sum(min_count=1)
    )
    publica["dependencia"] = "publica"
    total = (
        base.groupby(["ano", "id_municipio", "localizacao"], as_index=False)[
            "matriculas"
        ]
        .sum(min_count=1)
    )
    total["dependencia"] = "total"

    por_dependencia = pd.concat([base, publica, total], ignore_index=True)
    por_localizacao_total = (
        por_dependencia.groupby(
            ["ano", "id_municipio", "dependencia"],
            as_index=False,
        )["matriculas"]
        .sum(min_count=1)
    )
    por_localizacao_total["localizacao"] = "total"

    normalizada = pd.concat(
        [por_dependencia, por_localizacao_total],
        ignore_index=True,
    )
    normalizada["matriculas_integral"] = pd.NA
    return normalizada[colunas]


def montar_bloco_matriculas(
    df,
    id_mun,
    df_educacao_basica,
    df_faixa_etaria=None,
    df_cor_raca=None,
):
    """Constroi o bloco de matriculas para um municipio."""
    d = df[df["id_municipio"] == id_mun].copy()
    if d.empty:
        return _bloco_vazio("matriculas", ["etapa_ensino", "dependencia", "localizacao"])
    educacao_basica = _normalizar_matriculas_educacao_basica(
        df_educacao_basica,
        id_mun,
    )
    if educacao_basica.empty:
        raise ValueError(
            f"{id_mun}: total oficial de matrículas da Educação Básica indisponível."
        )

    # Os anos iniciais e finais sao recortes do total do ensino fundamental.
    # Mantemos esses recortes nas series por etapa, mas os excluimos de qualquer
    # total para nao contar as mesmas matriculas duas vezes.
    d_sem_sobreposicao = d[
        ~d["etapa_ensino"].isin(ETAPAS_FUNDAMENTAL_DETALHADAS)
    ]

    # Serie total oficial do Censo Escolar (QT_MAT_BAS). Etapas e modalidades
    # permanecem como recortes de leitura e não são somadas para recompor o total.
    total = (
        educacao_basica[
            (educacao_basica["dependencia"] == "total")
            & (educacao_basica["localizacao"] == "total")
        ]
        .sort_values("ano")
    )
    serie_total = [
        {"ano": int(r["ano"]), "valor": ri(r["matriculas"])}
        for _, r in total.iterrows() if limpar_null(r["matriculas"]) is not None
    ]

    # Serie por etapa (total dep, total loc)
    por_etapa = {}
    for etapa in sorted(d["etapa_ensino"].unique()):
        sub = d[
            (d["etapa_ensino"] == etapa)
            & (d["dependencia"] == "total")
            & (d["localizacao"] == "total")
        ].sort_values("ano")
        serie = [
            {"ano": int(r["ano"]), "valor": ri(r["matriculas"])}
            for _, r in sub.iterrows() if limpar_null(r["matriculas"]) is not None
        ]
        if serie:
            por_etapa[etapa] = serie

    # Serie por dependencia (total loc, todas as etapas)
    por_dep = {}
    for dep in ["publica", "privada", "estadual", "municipal", "federal"]:
        sub = educacao_basica[
            (educacao_basica["dependencia"] == dep)
            & (educacao_basica["localizacao"] == "total")
        ].sort_values("ano")
        serie = [
            {"ano": int(r["ano"]), "valor": ri(r["matriculas"])}
            for _, r in sub.iterrows() if limpar_null(r["matriculas"]) is not None
        ]
        if serie:
            por_dep[dep] = serie

    # Serie por localizacao (total dep)
    por_loc = {}
    for loc in ["urbana", "rural"]:
        sub = educacao_basica[
            (educacao_basica["dependencia"] == "total")
            & (educacao_basica["localizacao"] == loc)
        ].sort_values("ano")
        serie = [
            {"ano": int(r["ano"]), "valor": ri(r["matriculas"])}
            for _, r in sub.iterrows() if limpar_null(r["matriculas"]) is not None
        ]
        if serie:
            por_loc[loc] = serie

    # Integral
    integral = (
        d_sem_sobreposicao[
            (d_sem_sobreposicao["dependencia"] == "total")
            & (d_sem_sobreposicao["localizacao"] == "total")
        ]
        .groupby("ano")
        .agg(matriculas=("matriculas", "sum"), integral=("matriculas_integral", "sum"))
        .reset_index()
    )
    serie_integral = []
    for _, r in integral.iterrows():
        mat = limpar_null(r["matriculas"])
        inte = limpar_null(r["integral"])
        if inte is None:
            continue
        perc = r1(inte / mat * 100) if mat and mat > 0 else None
        serie_integral.append({"ano": int(r["ano"]), "valor": ri(inte), "percentual": perc})

    deps_rede = ["publica", "privada", "estadual", "municipal", "federal"]
    locs = ["urbana", "rural"]
    detalhamentos = {
        "por_etapa": detalhamento_matriculas(
            d,
            ["etapa_ensino"],
            {"dependencia": "total", "localizacao": "total"},
        ),
        "por_rede": detalhamento_matriculas(
            educacao_basica,
            ["dependencia"],
            {"dependencia": deps_rede, "localizacao": "total"},
        ),
        "por_localizacao": detalhamento_matriculas(
            educacao_basica,
            ["localizacao"],
            {"dependencia": "total", "localizacao": locs},
        ),
        "por_etapa_rede": detalhamento_matriculas(
            d,
            ["etapa_ensino", "dependencia"],
            {"dependencia": deps_rede, "localizacao": "total"},
        ),
        "por_etapa_localizacao": detalhamento_matriculas(
            d,
            ["etapa_ensino", "localizacao"],
            {"dependencia": "total", "localizacao": locs},
        ),
        "por_rede_localizacao": detalhamento_matriculas(
            educacao_basica,
            ["dependencia", "localizacao"],
            {"dependencia": deps_rede, "localizacao": locs},
        ),
        "tempo_integral_por_etapa": detalhamento_tempo_integral(
            d,
            ["etapa_ensino"],
            {"dependencia": "total", "localizacao": "total"},
        ),
        "tempo_integral_por_rede": detalhamento_tempo_integral(
            d_sem_sobreposicao,
            ["dependencia"],
            {"dependencia": deps_rede, "localizacao": "total"},
        ),
        "tempo_integral_por_localizacao": detalhamento_tempo_integral(
            d_sem_sobreposicao,
            ["localizacao"],
            {"dependencia": "total", "localizacao": locs},
        ),
        "tempo_integral_por_etapa_rede": detalhamento_tempo_integral(
            d,
            ["etapa_ensino", "dependencia"],
            {"dependencia": deps_rede, "localizacao": "total"},
        ),
        "tempo_integral_por_etapa_localizacao": detalhamento_tempo_integral(
            d,
            ["etapa_ensino", "localizacao"],
            {"dependencia": "total", "localizacao": locs},
        ),
    }

    if df_faixa_etaria is not None:
        f = df_faixa_etaria[df_faixa_etaria["id_municipio"] == id_mun].copy()
        if not f.empty:
            detalhamentos["por_faixa_etaria"] = detalhamento_faixa_etaria(
                f,
                ["faixa_etaria"],
            )
            detalhamentos["por_etapa_faixa_etaria"] = detalhamento_faixa_etaria(
                f,
                ["etapa_ensino", "faixa_etaria"],
            )
            if "secao_sinopse" in f.columns:
                detalhamentos["por_etapa_secao_faixa_etaria"] = detalhamento_faixa_etaria(
                    f,
                    ["etapa_ensino", "secao_sinopse", "faixa_etaria"],
                )

    if df_cor_raca is not None:
        c = df_cor_raca[df_cor_raca["id_municipio"] == id_mun].copy()
        if not c.empty:
            detalhamentos["por_cor_raca"] = detalhamento_cor_raca(
                c,
                ["cor_raca"],
            )
            detalhamentos["por_etapa_cor_raca"] = detalhamento_cor_raca(
                c,
                ["etapa_ensino", "cor_raca"],
            )
            if "secao_sinopse" in c.columns:
                detalhamentos["por_etapa_secao_cor_raca"] = detalhamento_cor_raca(
                    c,
                    ["etapa_ensino", "secao_sinopse", "cor_raca"],
                )
    # Ultimo ano
    ultimo_ano = int(total["ano"].max()) if not total.empty else None
    resumo = _resumo_matriculas(d, educacao_basica, ultimo_ano)

    return {
        "series": {
            "total": serie_total,
            "por_etapa": por_etapa,
            "por_dependencia": por_dep,
            "por_localizacao": por_loc,
            "integral": serie_integral,
        },
        "detalhamentos": detalhamentos,
        "ultimo_ano": ultimo_ano,
        "resumo_ultimo_ano": resumo,
        "dimensoes_disponiveis": [
            "etapa_ensino", "dependencia", "localizacao", "faixa_etaria", "cor_raca"
        ],
        "campos_indisponiveis": _campos_indisponiveis_matriculas(d, ultimo_ano),
    }


def _resumo_matriculas(d, educacao_basica, ano):
    if ano is None:
        return {}
    d_ano = d[d["ano"] == ano]
    d_ano_sem_sobreposicao = d_ano[
        ~d_ano["etapa_ensino"].isin(ETAPAS_FUNDAMENTAL_DETALHADAS)
    ]
    total_categorias = d_ano_sem_sobreposicao[
        (d_ano_sem_sobreposicao["dependencia"] == "total")
        & (d_ano_sem_sobreposicao["localizacao"] == "total")
    ]["matriculas"].sum()
    basica_ano = educacao_basica[educacao_basica["ano"] == ano]
    total = basica_ano[
        (basica_ano["dependencia"] == "total")
        & (basica_ano["localizacao"] == "total")
    ]["matriculas"].sum(min_count=1)

    por_etapa = {}
    for etapa in d_ano["etapa_ensino"].unique():
        val = d_ano[
            (d_ano["etapa_ensino"] == etapa)
            & (d_ano["dependencia"] == "total")
            & (d_ano["localizacao"] == "total")
        ]["matriculas"].sum()
        v = limpar_null(val)
        if v is not None:
            por_etapa[etapa] = ri(v)

    publica = basica_ano[(basica_ano["dependencia"] == "publica") & (basica_ano["localizacao"] == "total")][
        "matriculas"
    ].sum(min_count=1)
    privada = basica_ano[(basica_ano["dependencia"] == "privada") & (basica_ano["localizacao"] == "total")][
        "matriculas"
    ].sum(min_count=1)
    urbana = basica_ano[(basica_ano["dependencia"] == "total") & (basica_ano["localizacao"] == "urbana")][
        "matriculas"
    ].sum(min_count=1)
    rural = basica_ano[(basica_ano["dependencia"] == "total") & (basica_ano["localizacao"] == "rural")][
        "matriculas"
    ].sum(min_count=1)

    inte = d_ano_sem_sobreposicao[
        (d_ano_sem_sobreposicao["dependencia"] == "total")
        & (d_ano_sem_sobreposicao["localizacao"] == "total")
    ]["matriculas_integral"].sum()
    perc_integral = (
        r1(inte / total_categorias * 100)
        if limpar_null(total_categorias)
        and total_categorias > 0
        and limpar_null(inte)
        else None
    )

    return {
        "total_matriculas": ri(limpar_null(total)),
        "por_etapa": por_etapa,
        "matriculas_publica": ri(limpar_null(publica)),
        "matriculas_privada": ri(limpar_null(privada)),
        "matriculas_urbana": ri(limpar_null(urbana)),
        "matriculas_rural": ri(limpar_null(rural)),
        "percentual_integral": perc_integral,
    }


def _campos_indisponiveis_matriculas(d, ano):
    if ano is None:
        return ["matriculas", "matriculas_integral"]
    d_ano = d[d["ano"] == ano]
    indisponiveis = []
    if d_ano["matriculas_integral"].isna().all():
        indisponiveis.append("matriculas_integral")
    return indisponiveis


# ── Bloco: Rede Escolar ──────────────────────────────────────────────────


def montar_bloco_rede(df, id_mun, df_etapa=None):
    d = df[df["id_municipio"] == id_mun].copy()
    if d.empty:
        return _bloco_vazio("rede_escolar", ["dependencia", "localizacao"])

    total = (
        d[(d["dependencia"] == "total") & (d["localizacao"] == "total")]
        .sort_values("ano")
    )
    serie_total = [
        {"ano": int(r["ano"]), "valor": ri(r["escolas"])}
        for _, r in total.iterrows() if limpar_null(r["escolas"]) is not None
    ]

    por_dep = {}
    for dep in ["publica", "privada", "estadual", "municipal", "federal"]:
        sub = d[(d["dependencia"] == dep) & (d["localizacao"] == "total")].sort_values("ano")
        serie = [
            {"ano": int(r["ano"]), "valor": ri(r["escolas"])}
            for _, r in sub.iterrows() if limpar_null(r["escolas"]) is not None
        ]
        if serie:
            por_dep[dep] = serie

    por_loc = {}
    for loc in ["urbana", "rural"]:
        sub = d[(d["dependencia"] == "total") & (d["localizacao"] == loc)].sort_values("ano")
        serie = [
            {"ano": int(r["ano"]), "valor": ri(r["escolas"])}
            for _, r in sub.iterrows() if limpar_null(r["escolas"]) is not None
        ]
        if serie:
            por_loc[loc] = serie

    deps_rede = ["publica", "privada", "estadual", "municipal", "federal"]
    locs = ["urbana", "rural"]
    detalhamentos = {
        "por_rede": detalhamento_rede_escolar(d, ["dependencia"], {"dependencia": deps_rede, "localizacao": "total"}),
        "por_localizacao": detalhamento_rede_escolar(d, ["localizacao"], {"dependencia": "total", "localizacao": locs}),
        "por_rede_localizacao": detalhamento_rede_escolar(d, ["dependencia", "localizacao"], {"dependencia": deps_rede, "localizacao": locs}),
        "infraestrutura_por_rede": detalhamento_rede_escolar(d, ["dependencia"], {"dependencia": deps_rede, "localizacao": "total"}),
        "infraestrutura_por_localizacao": detalhamento_rede_escolar(d, ["localizacao"], {"dependencia": "total", "localizacao": locs}),
    }

    # Internet
    serie_internet = [
        {
            "ano": int(r["ano"]),
            "perc_internet": r1(r["perc_internet"]),
            "perc_banda_larga": r1(r["perc_banda_larga"]),
        }
        for _, r in total.iterrows()
        if limpar_null(r["perc_internet"]) is not None
    ]

    ultimo_ano = int(total["ano"].max()) if not total.empty else None
    resumo = _resumo_rede(d, ultimo_ano)

    # ── Escolas por etapa de ensino ──
    por_etapa_series = {}
    por_etapa_resumo = {}
    detalhamentos_etapa = {}

    if df_etapa is not None:
        de = df_etapa[df_etapa["id_municipio"] == id_mun].copy()
        if not de.empty:
            for etapa in sorted(de["etapa_ensino"].unique()):
                sub = de[
                    (de["etapa_ensino"] == etapa)
                    & (de["dependencia"] == "total")
                    & (de["localizacao"] == "total")
                ].sort_values("ano")
                serie = [
                    {"ano": int(r["ano"]), "valor": ri(r["escolas"])}
                    for _, r in sub.iterrows() if limpar_null(r["escolas"]) is not None
                ]
                if serie:
                    por_etapa_series[etapa] = serie
                    por_etapa_resumo[etapa] = serie[-1]["valor"]

            detalhamentos_etapa = {
                "por_etapa": detalhamento_escolas_etapa(
                    de, ["etapa_ensino"],
                    {"dependencia": "total", "localizacao": "total"},
                ),
                "por_etapa_rede": detalhamento_escolas_etapa(
                    de, ["etapa_ensino", "dependencia"],
                    {"dependencia": deps_rede, "localizacao": "total"},
                ),
                "por_etapa_localizacao": detalhamento_escolas_etapa(
                    de, ["etapa_ensino", "localizacao"],
                    {"dependencia": "total", "localizacao": locs},
                ),
            }

    bloco = {
        "series": {
            "total": serie_total,
            "por_dependencia": por_dep,
            "por_localizacao": por_loc,
            "internet": serie_internet,
        },
        "detalhamentos": detalhamentos,
        "ultimo_ano": ultimo_ano,
        "resumo_ultimo_ano": resumo,
        "dimensoes_disponiveis": ["dependencia", "localizacao"],
        "campos_indisponiveis": [],
    }

    infra = montar_bloco_infraestrutura(df, id_mun)
    if infra is not None:
        bloco["infraestrutura"] = infra

    if por_etapa_series:
        bloco["series"]["por_etapa"] = por_etapa_series
        bloco["resumo_ultimo_ano"]["por_etapa"] = por_etapa_resumo
        bloco["detalhamentos"].update(detalhamentos_etapa)
        bloco["dimensoes_disponiveis"].append("etapa_ensino")

    return bloco


def _resumo_rede(d, ano):
    if ano is None:
        return {}
    d_ano = d[d["ano"] == ano]
    total = d_ano[(d_ano["dependencia"] == "total") & (d_ano["localizacao"] == "total")]
    if total.empty:
        return {}
    row = total.iloc[0]
    urbana = d_ano[(d_ano["dependencia"] == "total") & (d_ano["localizacao"] == "urbana")]["escolas"]
    rural = d_ano[(d_ano["dependencia"] == "total") & (d_ano["localizacao"] == "rural")]["escolas"]
    publica = d_ano[(d_ano["dependencia"] == "publica") & (d_ano["localizacao"] == "total")]["escolas"]
    privada = d_ano[(d_ano["dependencia"] == "privada") & (d_ano["localizacao"] == "total")]["escolas"]
    return {
        "total_escolas": ri(limpar_null(row["escolas"])),
        "escolas_urbana": ri(limpar_null(urbana.iloc[0] if len(urbana) else None)),
        "escolas_rural": ri(limpar_null(rural.iloc[0] if len(rural) else None)),
        "escolas_publica": ri(limpar_null(publica.iloc[0] if len(publica) else None)),
        "escolas_privada": ri(limpar_null(privada.iloc[0] if len(privada) else None)),
        "perc_internet": r1(limpar_null(row["perc_internet"])),
        "perc_banda_larga": r1(limpar_null(row["perc_banda_larga"])),
    }


# ── Bloco: Infraestrutura Escolar ────────────────────────────────────────


def _extrair_infra_por_linha(row):
    """Extrai todas as métricas de infraestrutura de uma linha do DataFrame.

    Prefere as colunas de percentual pre-computadas pela view (perc_col).
    Quando a view nao as possui (fallback para views antigas), calcula
    a partir das colunas de contagem (count_col) usando o denominador
    correto: ``escolas`` para metricas de escola, ``qt_salas_utilizadas``
    para metricas de salas.

    Regra de ausencia:
      * ``None`` = dado nao disponivel (coluna ausente ou sem observacao)
      * ``0``    = dado real igual a zero (apenas quando a fonte confirma)
    """
    escolas = limpar_null(row.get("escolas"))
    if escolas is None or escolas <= 0:
        return {}
    dados = {"escolas": int(escolas)}
    for key, count_col, perc_col in INFRA_METRICAS:
        # 1. Tentar percentual pre-computado pela view
        perc_raw = row.get(perc_col)
        if perc_raw is not None:
            p = limpar_null(perc_raw)
            if p is not None:
                dados[perc_col] = r1(p)
            continue

        # 2. Fallback: calcular a partir das colunas de contagem
        #    (so executa se a view nao tiver o percentual pre-computado)
        count = _count_from_row(row, key, count_col)
        if count is None:
            continue

        # Denominador correto por tipo de metrica
        denom = escolas
        if key.startswith("salas_"):
            denom_raw = row.get("qt_salas_utilizadas")
            if denom_raw is not None:
                denom = limpar_null(denom_raw)
            if denom is None or denom <= 0:
                continue

        if denom is not None and denom > 0:
            dados[perc_col] = r1(count / denom * 100) if count > 0 else 0.0
    return dados


def _count_from_row(row, key, count_col):
    """Extrai a contagem de uma linha, preservando ``None`` para ausencia."""
    if key == "rede_wireless":
        c1_raw = row.get("escolas_com_rede_local_wireless")
        c2_raw = row.get("escolas_com_rede_local_cabo_wireless")
        if c1_raw is None or c2_raw is None:
            return None
        c1 = limpar_null(c1_raw)
        c2 = limpar_null(c2_raw)
        if c1 is None and c2 is None:
            return None
        return (c1 or 0) + (c2 or 0)
    count = limpar_null(row.get(count_col))
    return count


def _serie_infra_metricas(total_df):
    """Constrói séries temporais para cada métrica de infraestrutura.

    Respeita ``INFRA_START_YEARS`` para nao exibir 0% artificial em anos
    anteriores ao inicio da coleta da metrica no Censo Escolar.
    """
    metricas = {}
    for key, _, perc_col in INFRA_METRICAS:
        start = INFRA_START_YEARS.get(key, 0)
        serie = []
        for _, r in total_df.iterrows():
            ano = int(r["ano"])
            if ano < start:
                continue
            extraido = _extrair_infra_por_linha(r)
            if perc_col in extraido:
                serie.append({"ano": ano, "valor": extraido[perc_col]})
        if serie:
            metricas[key] = serie
    return metricas


def _resumo_infra(d_ano):
    """Extrai o resumo do último ano para todas as métricas de infraestrutura."""
    if d_ano.empty:
        return {}
    row = d_ano.iloc[0]
    resumo = {}
    extraido = _extrair_infra_por_linha(row)
    for key, _, perc_col in INFRA_METRICAS:
        if perc_col in extraido:
            resumo[key] = extraido[perc_col]
    return resumo


def detalhamento_infraestrutura(df, dimensoes, filtros=None):
    """Detalhamento de infraestrutura por dimensão (rede/localização)."""
    filtros = filtros or {}
    sub = df.copy()
    for coluna, valores in filtros.items():
        if not isinstance(valores, (list, tuple, set)):
            valores = [valores]
        sub = sub[sub[coluna].isin(valores)]
    if sub.empty:
        return []

    linhas = []
    for _, r in sub.sort_values(["ano", *dimensoes]).iterrows():
        escolas = limpar_null(r.get("escolas"))
        if escolas is None:
            continue
        linha = {"ano": int(r["ano"]), "escolas": ri(escolas)}
        extraido = _extrair_infra_por_linha(r)
        linha.update(extraido)
        for dimensao in dimensoes:
            linha[dimensao] = r[dimensao]
        if len(linha) > 2 + len(dimensoes):
            linhas.append(linha)
    return linhas


def montar_bloco_infraestrutura(df, id_mun):
    """Constroi o bloco de infraestrutura para um municipio."""
    d = df[df["id_municipio"] == id_mun].copy()
    if d.empty:
        return None

    total = d[(d["dependencia"] == "total") & (d["localizacao"] == "total")].sort_values("ano")
    if total.empty:
        return None

    series = _serie_infra_metricas(total)

    deps_rede = ["publica", "privada", "estadual", "municipal", "federal"]
    locs = ["urbana", "rural"]

    por_rede = detalhamento_infraestrutura(
        d, ["dependencia"], {"dependencia": deps_rede, "localizacao": "total"}
    )
    por_localizacao = detalhamento_infraestrutura(
        d, ["localizacao"], {"dependencia": "total", "localizacao": locs}
    )

    ultimo_ano = int(total["ano"].max()) if not total.empty else None
    d_ano = total[total["ano"] == ultimo_ano] if ultimo_ano else pd.DataFrame()
    resumo = _resumo_infra(d_ano)

    if not series and not resumo:
        return None

    return {
        "series": series,
        "ultimo_ano": ultimo_ano,
        "resumo_ultimo_ano": resumo,
        "por_rede": por_rede,
        "por_localizacao": por_localizacao,
        "grupos": GRUPOS_INFRA,
    }


# ── Bloco: Turmas e Docentes ─────────────────────────────────────────────


def montar_bloco_turmas(df, id_mun):
    d = df[df["id_municipio"] == id_mun].copy()
    if d.empty:
        return _bloco_vazio(
            "turmas_docentes", ["etapa_ensino", "dependencia", "localizacao"], AVISOS_TURMAS
        )

    total = (
        d[(d["dependencia"] == "total") & (d["localizacao"] == "total")]
        .groupby("ano")
        .agg(turmas=("turmas", "sum"), docentes=("docentes", "sum"), matriculas=("matriculas", "sum"))
        .reset_index()
        .sort_values("ano")
    )
    serie_total = []
    for _, r in total.iterrows():
        t = limpar_null(r["turmas"])
        if t is None:
            continue
        apt = r1(r["matriculas"] / r["turmas"]) if limpar_null(r["turmas"]) and r["turmas"] > 0 else None
        apd = r1(r["matriculas"] / r["docentes"]) if limpar_null(r["docentes"]) and r["docentes"] > 0 else None
        serie_total.append({
            "ano": int(r["ano"]),
            "turmas": ri(t),
            "docentes": ri(limpar_null(r["docentes"])),
            "alunos_por_turma": apt,
            "alunos_por_docente": apd,
        })

    por_etapa = {}
    for etapa in sorted(d["etapa_ensino"].unique()):
        sub = (
            d[(d["etapa_ensino"] == etapa) & (d["dependencia"] == "total") & (d["localizacao"] == "total")]
            .sort_values("ano")
        )
        serie = []
        for _, r in sub.iterrows():
            t = limpar_null(r["turmas"])
            if t is None:
                continue
            apt = r1(r["matriculas"] / r["turmas"]) if limpar_null(r["turmas"]) and r["turmas"] > 0 else None
            serie.append({
                "ano": int(r["ano"]),
                "turmas": ri(t),
                "docentes": ri(limpar_null(r["docentes"])),
                "alunos_por_turma": apt,
            })
        if serie:
            por_etapa[etapa] = serie

    deps_rede = ["publica", "privada", "estadual", "municipal", "federal"]
    locs = ["urbana", "rural"]
    detalhamentos = {
        "por_etapa": detalhamento_turmas(d, ["etapa_ensino"], {"dependencia": "total", "localizacao": "total"}),
        "por_rede": detalhamento_turmas(d, ["dependencia"], {"dependencia": deps_rede, "localizacao": "total"}),
        "por_localizacao": detalhamento_turmas(d, ["localizacao"], {"dependencia": "total", "localizacao": locs}),
        "por_etapa_rede": detalhamento_turmas(d, ["etapa_ensino", "dependencia"], {"dependencia": deps_rede, "localizacao": "total"}),
        "por_etapa_localizacao": detalhamento_turmas(d, ["etapa_ensino", "localizacao"], {"dependencia": "total", "localizacao": locs}),
        "por_rede_localizacao": detalhamento_turmas(d, ["dependencia", "localizacao"], {"dependencia": deps_rede, "localizacao": locs}),
    }

    ultimo_ano = int(total["ano"].max()) if not total.empty else None
    resumo = _resumo_turmas(total, ultimo_ano)

    return {
        "series": {
            "total": serie_total,
            "por_etapa": por_etapa,
        },
        "detalhamentos": detalhamentos,
        "ultimo_ano": ultimo_ano,
        "resumo_ultimo_ano": resumo,
        "dimensoes_disponiveis": ["etapa_ensino", "dependencia", "localizacao"],
        "campos_indisponiveis": [],
        "avisos": AVISOS_TURMAS,
    }


def _resumo_turmas(total, ano):
    if ano is None or total.empty:
        return {}
    row = total[total["ano"] == ano]
    if row.empty:
        return {}
    r = row.iloc[0]
    apt = r1(r["matriculas"] / r["turmas"]) if limpar_null(r["turmas"]) and r["turmas"] > 0 else None
    apd = r1(r["matriculas"] / r["docentes"]) if limpar_null(r["docentes"]) and r["docentes"] > 0 else None
    return {
        "turmas": ri(limpar_null(r["turmas"])),
        "docentes": ri(limpar_null(r["docentes"])),
        "alunos_por_turma": apt,
        "alunos_por_docente": apd,
    }


# ── Bloco: Fluxo ─────────────────────────────────────────────────────────


# ── Bloco: Alunos por Turma (ATU) ────────────────────────────────────────

ATU_SERIE_TOTAL_ETAPA = {
    "infantil": "infantil_total",
    "fundamental": "fundamental_total",
    "medio": "medio_total",
}


def detalhamento_alunos_turma(df, dimensoes, filtros=None):
    """Retorna linhas ATU sem agregacao, preservando as medias oficiais."""
    filtros = filtros or {}
    sub = df.copy()
    for coluna, valores in filtros.items():
        if valores is None:
            continue
        if not isinstance(valores, (list, tuple, set)):
            valores = [valores]
        sub = sub[sub[coluna].isin(valores)]

    if sub.empty:
        return []

    sort_cols = ["ano", *[c for c in dimensoes if c in sub.columns]]
    if "serie_ordem" in sub.columns:
        sort_cols.append("serie_ordem")
    sub = sub.sort_values(sort_cols)

    linhas = []
    for _, r in sub.iterrows():
        valor = limpar_null(r.get("alunos_por_turma"))
        if valor is None:
            continue
        linha = {
            "ano": int(r["ano"]),
            "valor": r1(valor),
            "alunos_por_turma": r1(valor),
        }
        for dimensao in dimensoes:
            if dimensao in r:
                linha[dimensao] = r[dimensao]
        for coluna in ["etapa_ensino", "serie", "serie_label", "serie_ordem", "dependencia", "localizacao"]:
            if coluna in r and coluna not in linha:
                linha[coluna] = limpar_null(r[coluna])
        linhas.append(linha)
    return linhas


def serie_alunos_turma(df, serie=None, dependencia="total", localizacao="total"):
    sub = df[
        (df["dependencia"] == dependencia)
        & (df["localizacao"] == localizacao)
    ].copy()
    if serie:
        sub = sub[sub["serie"] == serie]
    sub = sub.sort_values("ano")

    pontos = []
    for _, r in sub.iterrows():
        valor = limpar_null(r.get("alunos_por_turma"))
        if valor is None:
            continue
        pontos.append({
            "ano": int(r["ano"]),
            "valor": r1(valor),
            "alunos_por_turma": r1(valor),
        })
    return pontos


def montar_bloco_alunos_turma(df, id_mun):
    d = df[df["id_municipio"] == id_mun].copy()
    if d.empty:
        return _bloco_vazio(
            "alunos_turma",
            ["etapa_ensino", "serie", "dependencia", "localizacao"],
            AVISOS_ALUNOS_TURMA,
        )

    d_valid = d[d["alunos_por_turma"].notna()].copy()
    if d_valid.empty:
        return _bloco_vazio(
            "alunos_turma",
            ["etapa_ensino", "serie", "dependencia", "localizacao"],
            AVISOS_ALUNOS_TURMA,
        )

    total_rows = d_valid[(d_valid["dependencia"] == "total") & (d_valid["localizacao"] == "total")]
    series_options_df = (
        total_rows[["etapa_ensino", "serie", "serie_label", "serie_ordem"]]
        .drop_duplicates()
        .sort_values(["etapa_ensino", "serie_ordem", "serie"])
    )
    series_options = [
        {
            "key": row["serie"],
            "label": row["serie_label"],
            "etapa_ensino": row["etapa_ensino"],
            "ordem": ri(limpar_null(row["serie_ordem"])),
        }
        for _, row in series_options_df.iterrows()
    ]

    por_serie = {}
    for serie in sorted(total_rows["serie"].dropna().unique()):
        serie_hist = serie_alunos_turma(d_valid, serie=serie)
        if serie_hist:
            por_serie[serie] = serie_hist

    por_etapa = {}
    for etapa, serie_total in ATU_SERIE_TOTAL_ETAPA.items():
        serie_hist = serie_alunos_turma(d_valid, serie=serie_total)
        if serie_hist:
            por_etapa[etapa] = serie_hist

    serie_total_padrao = por_etapa.get("fundamental") or next(iter(por_etapa.values()), [])

    deps_rede = ["publica", "privada", "estadual", "municipal", "federal"]
    locs = ["urbana", "rural"]
    detalhamentos = {
        "por_etapa": detalhamento_alunos_turma(
            d_valid[d_valid["serie"].isin(ATU_SERIE_TOTAL_ETAPA.values())],
            ["etapa_ensino", "serie"],
            {"dependencia": "total", "localizacao": "total"},
        ),
        "por_serie": detalhamento_alunos_turma(
            d_valid,
            ["etapa_ensino", "serie"],
            {"dependencia": "total", "localizacao": "total"},
        ),
        "por_serie_rede": detalhamento_alunos_turma(
            d_valid,
            ["etapa_ensino", "serie", "dependencia"],
            {"dependencia": deps_rede, "localizacao": "total"},
        ),
        "por_serie_localizacao": detalhamento_alunos_turma(
            d_valid,
            ["etapa_ensino", "serie", "localizacao"],
            {"dependencia": "total", "localizacao": locs},
        ),
    }

    ultimo_ano = int(d_valid["ano"].max()) if not d_valid.empty else None
    resumo = _resumo_alunos_turma(d_valid, ultimo_ano)

    return {
        "series": {
            "total": serie_total_padrao,
            "por_etapa": por_etapa,
            "por_serie": por_serie,
        },
        "detalhamentos": detalhamentos,
        "series_options": series_options,
        "ultimo_ano": ultimo_ano,
        "resumo_ultimo_ano": resumo,
        "dimensoes_disponiveis": ["etapa_ensino", "serie", "dependencia", "localizacao"],
        "campos_indisponiveis": [],
        "avisos": AVISOS_ALUNOS_TURMA,
    }


def _resumo_alunos_turma(d, ano):
    if ano is None or d.empty:
        return {}
    d_ano = d[
        (d["ano"] == ano)
        & (d["dependencia"] == "total")
        & (d["localizacao"] == "total")
    ]
    resumo = {"por_etapa": {}}
    for etapa, serie_total in ATU_SERIE_TOTAL_ETAPA.items():
        row = d_ano[d_ano["serie"] == serie_total]
        if row.empty:
            continue
        valor = limpar_null(row.iloc[0]["alunos_por_turma"])
        if valor is None:
            continue
        chave = f"alunos_por_turma_{etapa}"
        resumo[chave] = r1(valor)
        resumo["por_etapa"][etapa] = r1(valor)
    return resumo


def montar_bloco_fluxo(df, id_mun):
    d = df[df["id_municipio"] == id_mun].copy()
    if d.empty:
        return _bloco_vazio("fluxo", ["etapa_ensino", "dependencia", "localizacao"], AVISOS_FLUXO)

    # Para distorcao, usar apenas localizacao=total
    d_dist = d[d["localizacao"] == "total"].copy()

    # Serie por etapa (dependencia=total, localizacao=total)
    por_etapa = {}
    for etapa in sorted(d["etapa_ensino"].unique()):
        sub = d[
            (d["etapa_ensino"] == etapa)
            & (d["dependencia"] == "total")
            & (d["localizacao"] == "total")
        ].sort_values("ano")
        serie = []
        for _, r in sub.iterrows():
            ponto = {"ano": int(r["ano"])}
            for col in ["taxa_aprovacao", "taxa_reprovacao", "taxa_abandono", "taxa_distorcao"]:
                v = limpar_null(r.get(col))
                if v is not None:
                    ponto[col] = r1(v)
            if len(ponto) > 1:
                serie.append(ponto)
        if serie:
            por_etapa[etapa] = serie

    # Serie por dependencia (etapa=fundamental, localizacao=total)
    por_dep = {}
    for dep in ["publica", "privada", "estadual", "municipal"]:
        sub = d[
            (d["etapa_ensino"] == "fundamental")
            & (d["dependencia"] == dep)
            & (d["localizacao"] == "total")
        ].sort_values("ano")
        serie = []
        for _, r in sub.iterrows():
            ponto = {"ano": int(r["ano"])}
            for col in ["taxa_aprovacao", "taxa_reprovacao", "taxa_abandono", "taxa_distorcao"]:
                v = limpar_null(r.get(col))
                if v is not None:
                    ponto[col] = r1(v)
            if len(ponto) > 1:
                serie.append(ponto)
        if serie:
            por_dep[dep] = serie

    deps_rede = ["publica", "privada", "estadual", "municipal", "federal"]
    locs = ["urbana", "rural"]
    detalhamentos = {
        "por_etapa": detalhamento_fluxo(d, ["etapa_ensino"], {"dependencia": "total", "localizacao": "total"}),
        "por_rede": detalhamento_fluxo(d, ["dependencia"], {"etapa_ensino": "fundamental", "dependencia": deps_rede, "localizacao": "total"}),
        "por_localizacao": detalhamento_fluxo(d, ["localizacao"], {"etapa_ensino": "fundamental", "dependencia": "total", "localizacao": locs}, incluir_distorcao=False),
        "por_etapa_rede": detalhamento_fluxo(d, ["etapa_ensino", "dependencia"], {"dependencia": deps_rede, "localizacao": "total"}),
        "por_etapa_localizacao": detalhamento_fluxo(d, ["etapa_ensino", "localizacao"], {"dependencia": "total", "localizacao": locs}, incluir_distorcao=False),
    }

    ultimo_ano = int(d["ano"].max())
    resumo = _resumo_fluxo(d, ultimo_ano)

    return {
        "series": {
            "por_etapa": por_etapa,
            "por_dependencia": por_dep,
        },
        "detalhamentos": detalhamentos,
        "ultimo_ano": ultimo_ano,
        "resumo_ultimo_ano": resumo,
        "dimensoes_disponiveis": ["etapa_ensino", "dependencia", "localizacao"],
        "campos_indisponiveis": _campos_indisponiveis_fluxo(d, ultimo_ano),
        "avisos": AVISOS_FLUXO,
    }


def _resumo_fluxo(d, ano):
    if ano is None:
        return {}
    d_ano = d[
        (d["ano"] == ano)
        & (d["etapa_ensino"] == "fundamental")
        & (d["dependencia"] == "total")
        & (d["localizacao"] == "total")
    ]
    if d_ano.empty:
        return {}
    r = d_ano.iloc[0]
    return {
        "taxa_aprovacao": r1(limpar_null(r["taxa_aprovacao"])),
        "taxa_reprovacao": r1(limpar_null(r["taxa_reprovacao"])),
        "taxa_abandono": r1(limpar_null(r["taxa_abandono"])),
        "taxa_distorcao": r1(limpar_null(r["taxa_distorcao"])),
    }


def _campos_indisponiveis_fluxo(d, ano):
    if ano is None:
        return ["taxa_aprovacao", "taxa_reprovacao", "taxa_abandono", "taxa_distorcao"]
    d_ano = d[
        (d["ano"] == ano)
        & (d["etapa_ensino"] == "fundamental")
        & (d["dependencia"] == "total")
        & (d["localizacao"] == "total")
    ]
    if d_ano.empty:
        return ["taxa_aprovacao", "taxa_reprovacao", "taxa_abandono", "taxa_distorcao"]
    r = d_ano.iloc[0]
    indisponiveis = []
    for col in ["taxa_aprovacao", "taxa_reprovacao", "taxa_abandono", "taxa_distorcao"]:
        if limpar_null(r.get(col)) is None:
            indisponiveis.append(col)
    return indisponiveis


# ── Bloco: Aprendizagem ──────────────────────────────────────────────────


def montar_bloco_aprendizagem(df, id_mun):
    d = df[df["id_municipio"] == id_mun].copy()
    if d.empty:
        return _bloco_vazio("aprendizagem", ["etapa_ensino", "dependencia"], AVISOS_APRENDIZAGEM)

    # IDEB por etapa
    ideb = {}
    for etapa in sorted(d["etapa_ensino"].dropna().unique()):
        sub = d[
            (d["etapa_ensino"] == etapa)
            & (d["dependencia"].isin(["total", "publica"]))
        ].sort_values("ano")
        serie = []
        for _, r in sub.iterrows():
            v = limpar_null(r.get("ideb"))
            if v is not None:
                serie.append({
                    "ano": int(r["ano"]),
                    "ideb": r1(v),
                    "saeb_lp": r1(limpar_null(r.get("saeb_lp"))),
                    "saeb_mt": r1(limpar_null(r.get("saeb_mt"))),
                })
        if serie:
            ideb[etapa] = serie

    # Alfabetizacao
    alf = d[d["taxa_alfabetizacao"].notna()].sort_values("ano")
    serie_alf = [
        {"ano": int(r["ano"]), "taxa_alfabetizacao": r1(r["taxa_alfabetizacao"])}
        for _, r in alf.iterrows() if limpar_null(r["taxa_alfabetizacao"]) is not None
    ]

    # INSE
    inse = d[d["media_inse"].notna()].sort_values("ano")
    serie_inse = [
        {
            "ano": int(r["ano"]),
            "media_inse": r1(r["media_inse"]),
            "qtd_alunos_inse": ri(limpar_null(r.get("qtd_alunos_inse"))),
        }
        for _, r in inse.iterrows() if limpar_null(r["media_inse"]) is not None
    ]

    ultimo_ideb = max((int(s[-1]["ano"]) for s in ideb.values() if s), default=None)
    ultimo_alf = serie_alf[-1]["ano"] if serie_alf else None
    ultimo_inse = serie_inse[-1]["ano"] if serie_inse else None

    resumo = _resumo_aprendizagem(ideb, serie_alf, serie_inse)
    deps_rede = ["total", "publica", "privada", "estadual", "municipal", "federal"]
    detalhamentos = {
        "por_etapa": detalhamento_aprendizagem(d, ["etapa_ensino"], {"dependencia": ["total", "publica"]}),
        "por_rede": detalhamento_aprendizagem(d, ["dependencia"], {"dependencia": deps_rede}),
        "por_etapa_rede": detalhamento_aprendizagem(d, ["etapa_ensino", "dependencia"], {"dependencia": deps_rede}),
    }

    return {
        "series": {
            "ideb": ideb,
            "alfabetizacao": serie_alf,
            "inse": serie_inse,
        },
        "detalhamentos": detalhamentos,
        "ultimo_ano": {
            "ideb": ultimo_ideb,
            "alfabetizacao": ultimo_alf,
            "inse": ultimo_inse,
        },
        "resumo_ultimo_ano": resumo,
        "dimensoes_disponiveis": ["etapa_ensino", "dependencia"],
        "campos_indisponiveis": _campos_indisponiveis_aprendizagem(d),
        "avisos": AVISOS_APRENDIZAGEM,
    }


def _resumo_aprendizagem(ideb, serie_alf, serie_inse):
    resumo = {}
    # Ultimo IDEB por etapa
    for etapa, serie in ideb.items():
        if serie:
            last = serie[-1]
            resumo[f"ideb_{etapa}"] = last["ideb"]
            resumo[f"saeb_lp_{etapa}"] = last.get("saeb_lp")
            resumo[f"saeb_mt_{etapa}"] = last.get("saeb_mt")
            resumo[f"ano_ideb_{etapa}"] = last["ano"]
    if serie_alf:
        resumo["taxa_alfabetizacao"] = serie_alf[-1]["taxa_alfabetizacao"]
        resumo["ano_alfabetizacao"] = serie_alf[-1]["ano"]
    if serie_inse:
        resumo["media_inse"] = serie_inse[-1]["media_inse"]
        resumo["qtd_alunos_inse"] = serie_inse[-1]["qtd_alunos_inse"]
        resumo["ano_inse"] = serie_inse[-1]["ano"]
    return resumo


def _campos_indisponiveis_aprendizagem(d):
    indisponiveis = []
    if d["ideb"].isna().all():
        indisponiveis.append("ideb")
    if d["taxa_alfabetizacao"].isna().all():
        indisponiveis.append("taxa_alfabetizacao")
    if d["media_inse"].isna().all():
        indisponiveis.append("media_inse")
    return indisponiveis


# ── Bloco: Oferta Tecnica ────────────────────────────────────────────────


def montar_bloco_oferta(df, id_mun, df_faixa_etaria=None):
    d = df[df["id_municipio"] == id_mun].copy()
    if d.empty:
        return _bloco_vazio("oferta_tecnica", ["modalidade", "dependencia", "faixa_etaria"], AVISOS_OFERTA)

    total = d[d["dependencia"] == "total"].copy()
    por_modalidade = {}
    for mod in sorted(total["modalidade"].unique()):
        sub = total[total["modalidade"] == mod].sort_values("ano")
        serie = [
            {"ano": int(r["ano"]), "valor": ri(r["matriculas"])}
            for _, r in sub.iterrows() if limpar_null(r["matriculas"]) is not None
        ]
        if serie:
            por_modalidade[mod] = serie

    serie_total = (
        total.groupby("ano")["matriculas"].sum(min_count=1).reset_index().sort_values("ano")
    )
    serie_total_list = [
        {"ano": int(r["ano"]), "valor": ri(r["matriculas"])}
        for _, r in serie_total.iterrows() if limpar_null(r["matriculas"]) is not None
    ]

    ultimo_ano = int(total["ano"].max()) if not total.empty else None
    resumo = _resumo_oferta(total, ultimo_ano)
    deps_rede = ["total", "publica", "privada", "estadual", "municipal", "federal"]
    detalhamentos = {
        "por_modalidade": detalhamento_oferta(total, ["modalidade"]),
        "por_rede": detalhamento_oferta(d, ["dependencia"], {"dependencia": deps_rede}),
        "por_modalidade_rede": detalhamento_oferta(d, ["modalidade", "dependencia"], {"dependencia": deps_rede}),
    }
    if df_faixa_etaria is not None and not df_faixa_etaria.empty:
        faixa = df_faixa_etaria[
            (df_faixa_etaria["id_municipio"] == id_mun)
            & (df_faixa_etaria["etapa_ensino"] == "profissional")
        ].copy()
        if not faixa.empty:
            detalhamentos["por_faixa_etaria"] = detalhamento_faixa_etaria(faixa, ["faixa_etaria"])
            if "secao_sinopse" in faixa.columns:
                detalhamentos["por_secao_faixa_etaria"] = detalhamento_faixa_etaria(
                    faixa,
                    ["secao_sinopse", "faixa_etaria"],
                )

    return {
        "series": {
            "total": serie_total_list,
            "por_modalidade": por_modalidade,
        },
        "detalhamentos": detalhamentos,
        "ultimo_ano": ultimo_ano,
        "resumo_ultimo_ano": resumo,
        "dimensoes_disponiveis": ["modalidade", "dependencia", "faixa_etaria"],
        "campos_indisponiveis": [],
        "avisos": AVISOS_OFERTA,
    }


def _resumo_oferta(total, ano):
    if ano is None or total.empty:
        return {}
    d_ano = total[total["ano"] == ano]
    total_mat = d_ano["matriculas"].sum()
    por_mod = {}
    for mod in d_ano["modalidade"].unique():
        val = d_ano[d_ano["modalidade"] == mod]["matriculas"].iloc[0]
        v = limpar_null(val)
        if v is not None:
            por_mod[mod] = ri(v)
    return {
        "total_matriculas_tecnicas": ri(limpar_null(total_mat)),
        "por_modalidade": por_mod,
    }


# ── Bloco: Sistema S ──────────────────────────────────────────────────────


EDUCACAO_INDIGENA_UNIDADES = {
    "matriculas": "Matrículas",
    "estabelecimentos": "Estabelecimentos",
    "docentes": "Docentes",
    "turmas": "Turmas",
}

EDUCACAO_INDIGENA_RECORTES = {
    "total": "Total",
    "educacao_infantil": "Educação Infantil",
    "creche": "Creche",
    "pre_escola": "Pré-Escola",
    "ensino_fundamental": "Ensino Fundamental",
    "anos_iniciais": "Anos Iniciais",
    "anos_finais": "Anos Finais",
    "ensino_medio": "Ensino Médio",
    "educacao_profissional": "Educação Profissional",
    "eja": "Educação de Jovens e Adultos",
    "eja_ensino_fundamental": "EJA - Ensino Fundamental",
    "eja_ensino_medio": "EJA - Ensino Médio",
    "educacao_especial": "Educação Especial",
    "classes_comuns": "Classes Comuns",
    "classes_exclusivas": "Classes Exclusivas",
}


def montar_bloco_educacao_indigena(
    df,
    id_mun,
    df_populacao_faixas=None,
    df_populacao_idades=None,
):
    """Constroi o retrato municipal oficial da Educacao Escolar Indigena."""
    d = df[df["id_municipio"] == id_mun].copy()
    population_groups = (
        df_populacao_faixas.to_dict("records")
        if df_populacao_faixas is not None and not df_populacao_faixas.empty
        else []
    )
    population_source_rows = (
        df_populacao_idades.to_dict("records")
        if df_populacao_idades is not None and not df_populacao_idades.empty
        else []
    )
    coverage = build_coverage_contract(
        population_groups + population_source_rows[:1],
        d.to_dict("records") if not d.empty else [],
    )
    if d.empty:
        block = _bloco_vazio_educacao_indigena()
        block["coberturaEstimada"] = coverage
        return block

    d["ano"] = pd.to_numeric(d["ano"], errors="coerce")
    d = d[d["ano"].notna()].copy()
    d["ano"] = d["ano"].astype(int)
    anos = sorted(d["ano"].unique().tolist())
    ultimo_ano = anos[-1] if anos else None

    dados = []
    for _, row in d.sort_values(["ano", "unidade", "recorte"]).iterrows():
        dados.append({
            "ano": int(row["ano"]),
            "unidade": str(row["unidade"]),
            "recorte": str(row["recorte"]),
            "valor": ri(row.get("valor")),
            "tabela_fonte": str(row.get("tabela_fonte") or ""),
            "grupo_comparabilidade": str(row.get("grupo_comparabilidade") or ""),
        })

    series_totais = {}
    resumo = {}
    for unidade in EDUCACAO_INDIGENA_UNIDADES:
        total = d[(d["unidade"] == unidade) & (d["recorte"] == "total")]
        series_totais[unidade] = [
            {
                "ano": int(row["ano"]),
                "valor": ri(row.get("valor")),
                "grupo_comparabilidade": str(row.get("grupo_comparabilidade") or ""),
            }
            for _, row in total.sort_values("ano").iterrows()
        ]
        latest = total[total["ano"] == ultimo_ano] if ultimo_ano is not None else total.iloc[0:0]
        resumo[unidade] = ri(latest.iloc[0]["valor"]) if not latest.empty else None

    fontes = [
        {"ano": ano, "tabela": tabela}
        for ano, tabela in sorted({
            (int(row["ano"]), str(row["tabela_fonte"]))
            for _, row in d.iterrows()
        })
    ]

    return {
        "schema_version": 1,
        "anos_disponiveis": anos,
        "ultimo_ano": ultimo_ano,
        "resumo_ultimo_ano": resumo,
        "series_totais": series_totais,
        "dados": dados,
        "unidades": EDUCACAO_INDIGENA_UNIDADES,
        "recortes": EDUCACAO_INDIGENA_RECORTES,
        "dimensoes_disponiveis": ["ano", "unidade", "recorte"],
        "campos_indisponiveis": [
            "rede_administrativa",
            "localizacao",
            "zona",
            "territorio",
            "terra_indigena",
            "povo",
            "lingua",
            "categoria_diferenciada",
        ],
        "comparabilidade": {
            "variacao_automatica_permitida": [
                "total",
                "educacao_infantil",
                "ensino_fundamental",
                "eja",
            ],
            "quebra_conceitual_2025": [
                "ensino_medio",
                "educacao_profissional",
                "educacao_especial",
            ],
        },
        "coberturaEstimada": coverage,
        "fontes": fontes,
        "avisos": AVISOS_EDUCACAO_INDIGENA,
    }


def _bloco_vazio_educacao_indigena():
    return {
        "schema_version": 1,
        "anos_disponiveis": [],
        "ultimo_ano": None,
        "resumo_ultimo_ano": {
            unidade: None for unidade in EDUCACAO_INDIGENA_UNIDADES
        },
        "series_totais": {
            unidade: [] for unidade in EDUCACAO_INDIGENA_UNIDADES
        },
        "dados": [],
        "unidades": EDUCACAO_INDIGENA_UNIDADES,
        "recortes": EDUCACAO_INDIGENA_RECORTES,
        "dimensoes_disponiveis": ["ano", "unidade", "recorte"],
        "campos_indisponiveis": ["sem_dados"],
        "comparabilidade": {
            "variacao_automatica_permitida": [],
            "quebra_conceitual_2025": [],
        },
        "fontes": [],
        "avisos": AVISOS_EDUCACAO_INDIGENA,
    }


def montar_bloco_sistema_s(df, id_mun, df_escolas=None):
    """Constroi o bloco de escolas do Sistema S para um municipio."""
    d = df[df["id_municipio"] == id_mun].copy()
    if d.empty:
        return _bloco_vazio_sistema_s()

    anos = sorted(d["ano"].unique())
    ultimo_ano = int(anos[-1]) if anos else None

    # Series
    series = {
        "total_escolas": [
            {"ano": int(r["ano"]), "valor": ri(r["total_escolas_sistema_s"])}
            for _, r in d.sort_values("ano").iterrows()
            if limpar_null(r["total_escolas_sistema_s"]) is not None
        ],
        "matriculas": [
            {"ano": int(r["ano"]), "valor": ri(r["total_matriculas"])}
            for _, r in d.sort_values("ano").iterrows()
            if limpar_null(r["total_matriculas"]) is not None
        ],
        "turmas": [
            {"ano": int(r["ano"]), "valor": ri(r["total_turmas"])}
            for _, r in d.sort_values("ano").iterrows()
            if limpar_null(r["total_turmas"]) is not None
        ],
        "docentes": [
            {"ano": int(r["ano"]), "valor": ri(r["total_docentes"])}
            for _, r in d.sort_values("ano").iterrows()
            if limpar_null(r["total_docentes"]) is not None
        ],
    }

    # Resumo do ultimo ano
    resumo = {}
    if ultimo_ano is not None:
        d_ultimo = d[d["ano"] == ultimo_ano]
        if not d_ultimo.empty:
            r = d_ultimo.iloc[0]
            resumo = {
                "total_escolas": ri(limpar_null(r["total_escolas_sistema_s"])),
                "total_matriculas": ri(limpar_null(r["total_matriculas"])),
                "total_turmas": ri(limpar_null(r["total_turmas"])),
                "total_docentes": ri(limpar_null(r["total_docentes"])),
            }

    # Distribuicao por etapa
    distribuicao_etapa = []
    if ultimo_ano is not None:
        d_ultimo = d[d["ano"] == ultimo_ano]
        if not d_ultimo.empty:
            r = d_ultimo.iloc[0]
            etapas = [
                ("Educação Infantil", "mat_infantil"),
                ("Ensino Fundamental", "mat_fundamental"),
                ("Ensino Médio", "mat_medio"),
                ("Educação Profissional", "mat_profissional"),
                ("EJA", "mat_eja"),
            ]
            distribuicao_etapa = [
                {"etapa": nome, "matriculas": ri(limpar_null(r.get(col)))}
                for nome, col in etapas
                if limpar_null(r.get(col)) is not None
            ]

    # Escolas do ultimo ano
    escolas = []
    if df_escolas is not None:
        de = df_escolas[df_escolas["id_municipio"] == id_mun].copy()
        if not de.empty:
            for _, r in de.sort_values("nome_escola").iterrows():
                etapas = r.get("etapas_ofertadas", "")
                escolas.append({
                    "cod_escola": str(r["cod_escola"]),
                    "nome_escola": str(r["nome_escola"]),
                    "matriculas": ri(limpar_null(r.get("matriculas"))),
                    "turmas": ri(limpar_null(r.get("turmas"))),
                    "docentes": ri(limpar_null(r.get("docentes"))),
                    "etapas": [e.strip() for e in etapas.split(",") if e.strip()] if etapas else [],
                })

    avisos = []
    if not series["total_escolas"]:
        avisos.append("Não há escolas do Sistema S registradas para este município nos dados disponíveis.")

    return {
        "series": series,
        "ultimo_ano": ultimo_ano,
        "resumo_ultimo_ano": resumo,
        "distribuicao_etapa": distribuicao_etapa,
        "escolas": escolas,
        "avisos": avisos,
    }


def _bloco_vazio_sistema_s():
    return {
        "series": {
            "total_escolas": [],
            "matriculas": [],
            "turmas": [],
            "docentes": [],
        },
        "ultimo_ano": None,
        "resumo_ultimo_ano": {},
        "distribuicao_etapa": [],
        "escolas": [],
        "avisos": ["Não há escolas do Sistema S registradas para este município nos dados disponíveis."],
    }


# ── Helpers de bloco vazio ──────────────────────────────────────────────


def _bloco_vazio(nome, dimensoes, avisos=None):
    return {
        "series": {},
        "ultimo_ano": None,
        "resumo_ultimo_ano": {},
        "dimensoes_disponiveis": dimensoes,
        "campos_indisponiveis": ["sem_dados"],
        "avisos": avisos or [],
    }


# ── Exportacao municipal ─────────────────────────────────────────────────


def _exportar_municipios_impl(
    mun_rs,
    dfs_views,
    progress_every=0,
):
    """Gera um JSON por municipio RS com tratamento de erro e progresso."""
    log(f"Exportando {len(mun_rs)} municipios...")
    gerados = 0
    falhas = []
    arquivos_escritos = []
    tamanhos = []
    dfs_por_municipio = {}
    for nome, df in dfs_views.items():
        if hasattr(df, "columns") and "id_municipio" in df.columns:
            dfs_por_municipio[nome] = {
                str(id_mun): grupo.copy()
                for id_mun, grupo in df.groupby("id_municipio", sort=False)
            }
        else:
            dfs_por_municipio[nome] = {}

    def view_df(nome, id_mun):
        df = dfs_views.get(nome)
        if df is None:
            return pd.DataFrame()
        return dfs_por_municipio.get(nome, {}).get(str(id_mun), df.iloc[0:0].copy())

    infrastructure_contracts = build_contracts(
        dfs_views["school_infrastructure"],
        mun_rs["id_municipio"].tolist(),
    )

    for idx, (_, mun) in enumerate(mun_rs.iterrows(), 1):
        id_mun = mun["id_municipio"]
        nome = mun["municipio"]

        try:
            blocos = {
                "matriculas": montar_bloco_matriculas(
                    view_df("matriculas", id_mun),
                    id_mun,
                    view_df("matriculas_educacao_basica", id_mun),
                    view_df("matriculas_faixa_etaria", id_mun),
                    view_df("matriculas_cor_raca", id_mun),
                ),
                "rede_escolar": montar_bloco_rede(
                    view_df("rede_escolar", id_mun), id_mun,
                    view_df("rede_escolar_etapa", id_mun),
                ),
                "turmas_docentes": montar_bloco_turmas(view_df("turmas", id_mun), id_mun),
                "alunos_turma": montar_bloco_alunos_turma(view_df("alunos_turma", id_mun), id_mun),
                "fluxo": montar_bloco_fluxo(view_df("fluxo", id_mun), id_mun),
                "aprendizagem": montar_bloco_aprendizagem(view_df("aprendizagem", id_mun), id_mun),
                "oferta_tecnica": montar_bloco_oferta(
                    view_df("oferta", id_mun),
                    id_mun,
                    view_df("matriculas_faixa_etaria", id_mun),
                ),
                "educacao_indigena": montar_bloco_educacao_indigena(
                    view_df("educacao_indigena", id_mun),
                    id_mun,
                    view_df("populacao_indigena_faixas", id_mun),
                    view_df("populacao_indigena_idades", id_mun),
                ),
                "sistema_s": montar_bloco_sistema_s(
                    view_df("sistema_s", id_mun),
                    id_mun,
                    view_df("sistema_s_escolas", id_mun),
                ),
                "vaar": montar_bloco_vaar(
                    view_df("vaar", id_mun),
                    id_mun,
                ),
            }

            dados = {
                "id_municipio": id_mun,
                "municipio": nome,
                "updated_at": DATA_EXPORTACAO,
                "fontes": FONTES,
                "avisos": AVISOS_GLOBAIS,
                "blocos": blocos,
            }
            dados = attach_school_infrastructure_contract(
                dados, infrastructure_contracts[str(id_mun)]
            )

            path = SAIDA_MUN / f"{id_mun}.json"
            safe_json_dump(dados, path)
            gerados += 1
            tamanho = path.stat().st_size
            tamanhos.append((id_mun, nome, tamanho))
            try:
                display_path = path.relative_to(REPO_ROOT)
            except ValueError:
                display_path = path
            arquivos_escritos.append(str(display_path))

            if progress_every and idx % progress_every == 0:
                log(f"Progresso: {idx}/{len(mun_rs)} municipios ({gerados} OK, {len(falhas)} falhas)")
        except Exception as e:
            log(f"ERRO ao exportar {id_mun} ({nome}): {e}")
            falhas.append((id_mun, nome, str(e)))

    # Top 5 maiores
    if tamanhos:
        tamanhos.sort(key=lambda x: x[2], reverse=True)
        log(f"{gerados} arquivos gerados.")
        log(f"5 maiores arquivos:")
        for id_mun, nome, tam in tamanhos[:5]:
            log(f"  {id_mun} {nome:<25} {tam / 1024:.1f} KB")
        log(f"Tamanho medio: {sum(t[2] for t in tamanhos) / len(tamanhos) / 1024:.1f} KB")

    if falhas:
        log(f"Falhas: {len(falhas)} municipios com erro:")
        for id_mun, nome, err in falhas:
            log(f"  {id_mun} {nome}: {err}")

    return gerados, falhas, arquivos_escritos, tamanhos


def exportar_municipios(
    mun_rs,
    dfs_views,
    progress_every=0,
):
    with profile_operation(
        "compute",
        "education.municipal_materialization",
        metadata={
            "eventGranularity": "aggregate",
            "perMunicipalityEvents": False,
        },
    ) as operation:
        result = _exportar_municipios_impl(
            mun_rs,
            dfs_views,
            progress_every,
        )
        generated, failures, written, sizes = result
        rendered_bytes = sum(size for _municipality_id, _name, size in sizes)
        operation.add_counters(
            municipalitiesRequested=len(mun_rs),
            municipalitiesCompleted=generated,
            errors=len(failures),
            filesWritten=len(written),
            bytesRendered=rendered_bytes,
            bytesWritten=rendered_bytes,
        )
        return result


class EducationMunicipalityBatchError(EducationPublicationError):
    """Mantem o relatorio municipal completo e impede indices/promocao."""

    def __init__(self, failures):
        self.failures = tuple(failures)
        preview = "; ".join(
            f"{municipality_id} ({name}): {error}"
            for municipality_id, name, error in self.failures[:10]
        )
        super().__init__(
            f"Falha em {len(self.failures)} municipios; lote rejeitado: {preview}"
        )


def materialize_education_outputs(
    output_root,
    mun_rs,
    dfs,
    anos_por_bloco,
    registry,
    route_compatibility,
    progress_every=0,
):
    """Materializa o lote integral exclusivamente na arvore recebida."""
    observed_ids = mun_rs["id_municipio"].tolist()
    invalid_ids = [
        value
        for value in observed_ids
        if not isinstance(value, str) or re.fullmatch(r"\d{7}", value) is None
    ]
    observed_set = set(observed_ids)
    if invalid_ids or observed_set != registry.ids or len(observed_ids) != len(
        observed_set
    ):
        raise EducationPublicationError(
            "Universo municipal da materializacao diverge do registro; "
            f"invalidos={invalid_ids[:5]}, "
            f"ausentes={sorted(registry.ids - observed_set)[:5]}, "
            f"extras={sorted(observed_set - registry.ids)[:5]}."
        )
    names_by_id = dict(zip(observed_ids, mun_rs["municipio"], strict=True))
    divergent_names = [
        record.ibge_code
        for record in registry.ordered_records
        if names_by_id.get(record.ibge_code) != record.name
    ]
    if divergent_names:
        raise EducationPublicationError(
            "Nomes municipais da materializacao divergem do registro: "
            f"{divergent_names[:5]}."
        )

    configure_education_output_root(Path(output_root))
    gerados_mun, falhas_mun, arquivos_escritos, tamanhos = exportar_municipios(
        mun_rs,
        dfs,
        progress_every,
    )
    if falhas_mun:
        raise EducationMunicipalityBatchError(falhas_mun)
    if gerados_mun != registry.municipality_count:
        raise EducationPublicationError(
            "Quantidade municipal materializada diverge do registro: "
            f"gerados={gerados_mun}, esperado={registry.municipality_count}."
        )
    gerar_municipios_index(registry, route_compatibility)
    gerar_index(mun_rs, anos_por_bloco, gerados_mun)
    return gerados_mun, arquivos_escritos, tamanhos


# ── Exportacao regional ──────────────────────────────────────────────────
# Nota: a pagina de educacao do dashboard usa apenas dados municipais.
# A exportacao regional fica disponivel no script mas nao e chamada por
# padrao. Para reativar, chame exportar_regioes() manualmente.


def exportar_regioes(mun_rs, dfs_views):
    """Gera um JSON por regiao SENAI com dados agregados."""
    regioes = mun_rs.groupby("regiao_senai")
    print(f"\nExportando {len(regioes)} regioes...")
    gerados = 0

    for regiao, grupo in regioes:
        ids_regiao = grupo["id_municipio"].tolist()
        slug = slugify(regiao)

        # Agregar matriculas
        mat_regional = _agregar_matriculas_regional(
            dfs_views["matriculas"],
            dfs_views["matriculas_educacao_basica"],
            ids_regiao,
        )
        rede_regional = _agregar_rede_regional(dfs_views["rede_escolar"], ids_regiao)
        turmas_regional = _agregar_turmas_regional(dfs_views["turmas"], ids_regiao)
        fluxo_regional = _agregar_fluxo_regional(dfs_views["fluxo"], ids_regiao)
        aprend_regional = _agregar_aprendizagem_regional(dfs_views["aprendizagem"], ids_regiao)
        oferta_regional = _agregar_oferta_regional(dfs_views["oferta"], ids_regiao)

        dados = {
            "regiao": regiao,
            "slug": slug,
            "municipios_incluidos": ids_regiao,
            "total_municipios": len(ids_regiao),
            "updated_at": DATA_EXPORTACAO,
            "fontes": FONTES,
            "avisos": AVISOS_GLOBAIS + [
                "Dados regionais sao agregacoes de municipios. "
                "Percentuais foram recalculados a partir dos totais somados.",
                "IDEB/SAEB regional usa media simples dos municipios com dado.",
                "INSE regional usa media ponderada por qtd_alunos_inse.",
            ],
            "blocos": {
                "matriculas": mat_regional,
                "rede_escolar": rede_regional,
                "turmas_docentes": turmas_regional,
                "fluxo": fluxo_regional,
                "aprendizagem": aprend_regional,
                "oferta_tecnica": oferta_regional,
            },
        }

        path = SAIDA_REG / f"{slug}.json"
        safe_json_dump(dados, path)
        gerados += 1
        print(f"  {slug:<25} {len(ids_regiao)} municipios  {path.stat().st_size / 1024:.1f} KB")

    return gerados


def _agregar_matriculas_regional(df, df_educacao_basica, ids):
    """Agrega matriculas somando municipios da regiao."""
    d = df[df["id_municipio"].isin(ids)].copy()
    if d.empty:
        return _bloco_vazio("matriculas", ["etapa_ensino", "dependencia", "localizacao"])

    agg = (
        d.groupby(["ano", "dependencia", "localizacao", "etapa_ensino"])
        .agg(matriculas=("matriculas", "sum"), matriculas_integral=("matriculas_integral", "sum"))
        .reset_index()
    )
    # Reaproveita a funcao municipal com id_municipio dummy
    agg["id_municipio"] = "REGIONAL"
    basica = (
        df_educacao_basica[df_educacao_basica["id_municipio"].isin(ids)]
        .groupby(["ano", "dependencia", "localizacao"], as_index=False)[
            "mat_basico"
        ]
        .sum(min_count=1)
    )
    basica["id_municipio"] = "REGIONAL"
    return montar_bloco_matriculas(agg, "REGIONAL", basica)


def _agregar_rede_regional(df, ids):
    d = df[df["id_municipio"].isin(ids)].copy()
    if d.empty:
        return _bloco_vazio("rede_escolar", ["dependencia", "localizacao"])

    agg = (
        d.groupby(["ano", "dependencia", "localizacao"])
        .agg(
            escolas=("escolas", "sum"),
            escolas_com_internet=("escolas_com_internet", "sum"),
            escolas_com_banda_larga=("escolas_com_banda_larga", "sum"),
        )
        .reset_index()
    )
    # Recalcular percentuais
    agg["perc_internet"] = agg.apply(
        lambda r: r1(r["escolas_com_internet"] / r["escolas"] * 100)
        if limpar_null(r["escolas"]) and r["escolas"] > 0 else None,
        axis=1,
    )
    agg["perc_banda_larga"] = agg.apply(
        lambda r: r1(r["escolas_com_banda_larga"] / r["escolas"] * 100)
        if limpar_null(r["escolas"]) and r["escolas"] > 0 else None,
        axis=1,
    )
    agg["id_municipio"] = "REGIONAL"
    return montar_bloco_rede(agg, "REGIONAL")


def _agregar_turmas_regional(df, ids):
    d = df[df["id_municipio"].isin(ids)].copy()
    if d.empty:
        return _bloco_vazio("turmas_docentes", ["etapa_ensino", "dependencia", "localizacao"], AVISOS_TURMAS)

    agg = (
        d.groupby(["ano", "dependencia", "localizacao", "etapa_ensino"])
        .agg(turmas=("turmas", "sum"), docentes=("docentes", "sum"), matriculas=("matriculas", "sum"))
        .reset_index()
    )
    agg["id_municipio"] = "REGIONAL"
    return montar_bloco_turmas(agg, "REGIONAL")


def _agregar_fluxo_regional(df, ids):
    d = df[df["id_municipio"].isin(ids)].copy()
    if d.empty:
        return _bloco_vazio("fluxo", ["etapa_ensino", "dependencia", "localizacao"], AVISOS_FLUXO)

    # Rendimento: media ponderada pelas matriculas seria ideal, mas usamos media simples
    # Distorcao: media simples
    cols_taxa = ["taxa_aprovacao", "taxa_reprovacao", "taxa_abandono", "taxa_distorcao"]
    agg = (
        d.groupby(["ano", "dependencia", "localizacao", "etapa_ensino"])[cols_taxa]
        .mean()
        .reset_index()
    )
    agg["id_municipio"] = "REGIONAL"
    return montar_bloco_fluxo(agg, "REGIONAL")


def _agregar_aprendizagem_regional(df, ids):
    d = df[df["id_municipio"].isin(ids)].copy()
    if d.empty:
        return _bloco_vazio("aprendizagem", ["etapa_ensino", "dependencia"], AVISOS_APRENDIZAGEM)

    # IDEB/SAEB: media simples
    cols_aprend = ["ideb", "saeb_lp", "saeb_mt", "taxa_alfabetizacao"]
    agg_ideb = (
        d.groupby(["ano", "dependencia", "etapa_ensino"])[cols_aprend]
        .mean()
        .reset_index()
    )

    # INSE: media ponderada por qtd_alunos_inse
    inse_rows = d[d["media_inse"].notna()].copy()
    if not inse_rows.empty:
        inse_rows["peso"] = inse_rows["qtd_alunos_inse"].fillna(0)
        for ano in inse_rows["ano"].unique():
            sub = inse_rows[inse_rows["ano"] == ano]
            for rede in sub["dependencia"].unique():
                sub_r = sub[sub["dependencia"] == rede]
                peso_total = sub_r["peso"].sum()
                if peso_total > 0:
                    media_pond = (sub_r["media_inse"] * sub_r["peso"]).sum() / peso_total
                    agg_ideb = pd.concat([
                        agg_ideb,
                        pd.DataFrame([{
                            "ano": ano,
                            "dependencia": rede,
                            "etapa_ensino": None,
                            "ideb": None,
                            "saeb_lp": None,
                            "saeb_mt": None,
                            "taxa_alfabetizacao": None,
                            "media_inse": media_pond,
                            "qtd_alunos_inse": ri(peso_total),
                        }])
                    ], ignore_index=True)
    else:
        agg_ideb["media_inse"] = None
        agg_ideb["qtd_alunos_inse"] = None

    agg_ideb["id_municipio"] = "REGIONAL"
    return montar_bloco_aprendizagem(agg_ideb, "REGIONAL")


def _agregar_oferta_regional(df, ids):
    d = df[df["id_municipio"].isin(ids)].copy()
    if d.empty:
        return _bloco_vazio("oferta_tecnica", ["modalidade", "dependencia"], AVISOS_OFERTA)

    agg = (
        d.groupby(["ano", "dependencia", "modalidade"])["matriculas"]
        .sum(min_count=1)
        .reset_index()
    )
    agg["id_municipio"] = "REGIONAL"
    return montar_bloco_oferta(agg, "REGIONAL")


# ── Municipios index ─────────────────────────────────────────────────────


def gerar_municipios_index(registry, route_compatibility):
    """Gera a projeção educacional compatível sem usar o índice anterior."""
    dados = build_education_municipalities_index_payload(
        registry,
        route_compatibility,
    )
    path = SAIDA / "municipios_index.json"
    safe_json_dump(dados, path)
    print(f"municipios_index.json gerado: {len(dados['municipios'])} municipios, "
          f"{path.stat().st_size / 1024:.1f} KB")
    return path


# ── Index.json ───────────────────────────────────────────────────────────


def gerar_index(mun_rs, anos_por_bloco, gerados_mun):
    """Gera o index.json leve com metadados."""

    dados = {
        "updated_at": DATA_EXPORTACAO,
        "anos_disponiveis": anos_por_bloco,
        "total_municipios": len(mun_rs),
        "fontes": FONTES,
        "avisos_metodologicos": AVISOS_GLOBAIS + [
            "Distorcao idade-serie nao tem dimensao de localizacao na fonte.",
            "IDEB e bienal; anos sem avaliacao tem null.",
            "alunos_por_docente pode ser alto em EJA/Infantil.",
            "ATU de alunos por turma usa medias oficiais da planilha, sem recalculo de media de medias.",
        ],
        "blocos_disponiveis": [
            "matriculas", "rede_escolar", "alunos_turma", "turmas_docentes",
            "fluxo", "aprendizagem", "oferta_tecnica",
            "educacao_indigena", "sistema_s", "vaar",
        ],
        "campos_indisponiveis": [],
        "caminhos": {
            "municipios_index": "educacao/municipios_index.json",
            "municipios": "educacao/municipios/{id_municipio}.json",
        },
        "arquivos_gerados": {
            "municipios": gerados_mun,
        },
    }

    path = SAIDA / "index.json"
    safe_json_dump(dados, path)
    tamanho = path.stat().st_size
    print(f"\nindex.json gerado: {tamanho / 1024:.1f} KB")
    return path


# ── Validacao ────────────────────────────────────────────────────────────


def validar_jsons(
    gerados_mun,
    registry,
    route_compatibility,
    *,
    output_root=None,
):
    """Executa o validador fail-closed da arvore prospectiva completa."""
    root = Path(output_root) if output_root is not None else SAIDA
    if root is None:
        raise EducationPublicationError(
            "Diretorio de staging educacional nao configurado."
        )
    if gerados_mun != registry.municipality_count:
        raise EducationPublicationError(
            "Validacao recusou lote municipal incompleto: "
            f"gerados={gerados_mun}, esperado={registry.municipality_count}."
        )
    report = validate_education_staging(
        root,
        registry,
        route_compatibility,
        public_root=default_public_root(),
    )
    print(
        "Validacao integral concluida: "
        f"{len(report.files)} arquivos, {report.municipality_count} municipios."
    )
    return report


def diagnosticar_jsons(gerados_mun):
    """Relatorio humano opcional; nao autoriza nem executa promocao."""
    print("\n" + "=" * 60)
    print("VALIDACAO DOS JSONs GERADOS")
    print("=" * 60)

    # 1. JSON valido
    arquivos = list(SAIDA_MUN.glob("*.json")) + [SAIDA / "index.json", SAIDA / "municipios_index.json"]
    print(f"\n1. Total de arquivos: {len(arquivos)}")
    invalidos = 0
    for f in arquivos:
        try:
            with open(f, encoding="utf-8") as fh:
                json.load(fh)
        except Exception as e:
            print(f"  INVALIDO: {f.name} - {e}")
            invalidos += 1
    print(f"  Validos: {len(arquivos) - invalidos}  Invalidos: {invalidos}")

    # 2. NaN/Infinity
    print("\n2. Checagem NaN/Infinity:")
    nan_encontrado = False
    for f in arquivos:
        with open(f, encoding="utf-8") as fh:
            conteudo = fh.read()
        for padrao in ["NaN", "Infinity", "-Infinity"]:
            if padrao in conteudo:
                print(f"  ENCONTRADO '{padrao}' em {f.name}")
                nan_encontrado = True
    if not nan_encontrado:
        print("  OK - nenhum NaN/Infinity encontrado.")

    # 3. Nulls preservados
    print("\n3. Checagem de nulls preservados:")
    amostra = list(SAIDA_MUN.glob("*.json"))[:5]
    for f in amostra:
        with open(f, encoding="utf-8") as fh:
            dados = json.load(fh)
        blocos = dados.get("blocos", {})
        nulls = 0
        for bloco_nome, bloco in blocos.items():
            if isinstance(bloco, dict) and bloco.get("campos_indisponiveis"):
                nulls += len(bloco["campos_indisponiveis"])
        # Verificar se null aparece no JSON
        conteudo = f.read_text(encoding="utf-8")
        if ":null" in conteudo or ": null" in conteudo:
            pass  # null preservado
        print(f"  {f.stem}: nulls preservados={'Sim' if ':null' in conteudo or ': null' in conteudo else 'Nao'}")

    # 4. Tamanhos
    print("\n4. Tamanhos:")
    for f in sorted(arquivos, key=lambda x: x.stat().st_size, reverse=True)[:10]:
        print(f"  {f.relative_to(SAIDA)}: {f.stat().st_size / 1024:.1f} KB")

    # 5. index.json leve
    idx_path = SAIDA / "index.json"
    idx_size = idx_path.stat().st_size
    print(f"\n5. index.json: {idx_size / 1024:.1f} KB ({'LEVE' if idx_size < 50000 else 'PESADO'})")

    # 6. Cobertura por bloco
    print("\n6. Cobertura por bloco (5 municipios amostra):")
    amostra = [f for f in SAIDA_MUN.glob("*.json")][:5]
    for f in amostra:
        with open(f, encoding="utf-8") as fh:
            dados = json.load(fh)
        cobertura = {}
        for bloco, conteudo in dados.get("blocos", {}).items():
            tem_dados = bool(
                conteudo.get("series")
                or conteudo.get("series_totais")
                or conteudo.get("dados")
            )
            indisponiveis = conteudo.get("campos_indisponiveis", [])
            cobertura[bloco] = "OK" if tem_dados and "sem_dados" not in indisponiveis else "SEM_DADOS"
        print(f"  {f.stem}: {cobertura}")

    # 7. Exemplos
    print("\n7. Exemplos de 3 municipios (resumo):")
    for f in amostra[:3]:
        with open(f, encoding="utf-8") as fh:
            dados = json.load(fh)
        print(f"  {dados['id_municipio']} {dados['municipio']}:")
        for bloco, conteudo in dados.get("blocos", {}).items():
            resumo = conteudo.get("resumo_ultimo_ano", {})
            ultimo = conteudo.get("ultimo_ano")
            if isinstance(ultimo, dict):
                ultimo_str = str(ultimo)
            else:
                ultimo_str = str(ultimo)
            print(f"    {bloco}: ultimo_ano={ultimo_str}, resumo={str(resumo)[:80]}")

    # 8. Reconciliacao da oferta tecnica
    print("\n8. Reconciliacao Oferta tecnica (redes = total):")
    divergencias = []
    redes_detalhadas = {"federal", "estadual", "municipal", "privada"}
    for f in SAIDA_MUN.glob("*.json"):
        with open(f, encoding="utf-8") as fh:
            dados = json.load(fh)
        oferta = dados.get("blocos", {}).get("oferta_tecnica", {})
        total_por_ano = {
            int(p["ano"]): limpar_null(p.get("valor"))
            for p in oferta.get("series", {}).get("total", [])
        }
        rede_por_ano = defaultdict(int)
        for row in oferta.get("detalhamentos", {}).get("por_rede", []):
            if row.get("dependencia") not in redes_detalhadas:
                continue
            valor = limpar_null(row.get("matriculas", row.get("valor")))
            if valor is not None:
                rede_por_ano[int(row["ano"])] += valor
        for ano, total in total_por_ano.items():
            if total is None:
                continue
            soma_redes = rede_por_ano.get(ano, 0)
            if ri(total) != ri(soma_redes):
                divergencias.append(
                    (dados["id_municipio"], dados["municipio"], ano, ri(total), ri(soma_redes))
                )
                if len(divergencias) >= 10:
                    break
        if len(divergencias) >= 10:
            break
    if divergencias:
        print("  DIVERGENCIAS encontradas (primeiras 10):")
        for id_mun, nome, ano, total, soma_redes in divergencias:
            print(f"    {id_mun} {nome} {ano}: total={total}, redes={soma_redes}")
        raise ValueError("Oferta tecnica por rede nao reconcilia com a serie principal.")
    print("  OK - soma das redes detalhadas fecha com a serie principal.")


# ── Main ─────────────────────────────────────────────────────────────────


def load_education_inputs(state_config, registry, *, diagnostic=False):
    """Carrega uma unica vez todas as fontes da tarefa educacional."""

    with profile_operation(
        "query",
        "education.sources",
        metadata={"eventGranularity": "aggregate"},
    ) as sources_event:
        engine = _get_education_engine()
        with Timer("carregar_municipios"):
            municipalities = carregar_municipios(
                engine,
                state_config,
                registry,
            )
        municipality_ids = municipalities["id_municipio"].tolist()
        log(
            f"Municipios {state_config.state_code} carregados: "
            f"{len(municipality_ids)}"
        )

        log("Carregando views...")
        frames = {}
        for view_name, key in EDUCATION_VIEWS:
            with Timer(f"Carregar {view_name}"):
                frame = carregar_view(
                    engine,
                    view_name,
                    municipality_ids,
                    registry,
                )
                frames[key] = frame
            log(f"  {view_name}: {len(frame)} linhas")
        sources_event.add_counters(
            sourceFrames=len(frames) + 1,
            sourceRows=len(municipalities)
            + sum(len(frame) for frame in frames.values()),
        )

    available_years = {}
    for name, frame in frames.items():
        if name == "matriculas_educacao_basica":
            continue
        if not frame.empty and "ano" in frame.columns:
            available_years[name] = sorted(frame["ano"].unique().tolist())
        elif not frame.empty and "ano_fundeb" in frame.columns:
            available_years[name] = sorted(
                frame["ano_fundeb"].unique().tolist()
            )
    if diagnostic:
        log(f"Anos disponiveis por view: {available_years}")
    return {
        "municipalities": municipalities,
        "municipalityIds": municipality_ids,
        "frames": frames,
        "availableYears": available_years,
    }


def calculate_education_fingerprint(
    *,
    inputs,
    state_config,
    registry,
    public_root,
    mode,
):
    """Calcula a decisao fail-closed sem criar staging ou escrever state."""

    source_frames = {
        "municipalities": inputs["municipalities"],
        **inputs["frames"],
    }
    with profile_operation(
        "compute",
        "education.fingerprint.sources",
        metadata={"eventGranularity": "aggregate"},
    ) as source_event:
        source_digests = digest_education_sources(source_frames)
        source_event.add_counters(**source_digests["stats"])

    with profile_operation(
        "read",
        "education.fingerprint.contracts",
        metadata={"allowlist": "education-explicit-v1"},
    ) as contract_event:
        utils_contract = resolve_imported_python_module_contract(
            "utils_educacao",
            contract_id="utils_educacao",
        )
        contract_digests = digest_contract_files(
            REPO_ROOT,
            external_python_contracts=(utils_contract,),
        )
        contract_event.add_counters(
            contracts=contract_digests["fileCount"],
            bytesHashed=contract_digests["bytesHashed"],
        )

    with profile_operation(
        "compute",
        "education.fingerprint.input",
        metadata={"taskId": EDUCATION_TASK_ID},
    ) as input_event:
        input_fingerprint = build_input_fingerprint(
            source_digests,
            contract_digests,
            state_code=state_config.state_code,
            execution_parameters={
                "municipalityCount": registry.municipality_count,
                "publicationContract": "transactional-full-v1",
                "outputCount": registry.municipality_count + 2,
            },
        )
        input_event.add_counter("bytesHashed", input_fingerprint["bytesHashed"])

    task_state_path = default_task_state_path(DATA_PIPELINE_DIR)
    previous_state = load_task_state(task_state_path)
    with profile_operation(
        "validation",
        "education.fingerprint.output_integrity",
        metadata={"phase": f"{mode}_decision"},
    ) as output_event:
        decision = evaluate_shadow_eligibility(
            previous_state,
            input_fingerprint,
            contract_digests,
            public_root,
            inputs["municipalityIds"],
        )
        output_event.add_counters(
            managedOutputs=decision.output_integrity.managed_outputs,
            outputBytesVerified=decision.output_integrity.output_bytes_verified,
            manifestInvalid=int(decision.manifest_invalid),
        )
    actually_skipped = mode == "skip" and decision.would_skip
    with profile_operation(
        "orchestration",
        f"education.fingerprint.{mode}_decision",
        counters={
            "fingerprintHit": int(decision.fingerprint_hit),
            "wouldSkip": int(decision.would_skip),
            "actuallySkipped": int(actually_skipped),
            "manifestInvalid": int(decision.manifest_invalid),
        },
        metadata={
            "taskId": EDUCATION_TASK_ID,
            "reason": decision.reason,
            "shadowOnly": mode == "shadow",
        },
    ):
        pass
    log(
        f"Fingerprint {mode}: taskId={EDUCATION_TASK_ID} "
        f"inputFingerprint={input_fingerprint['inputFingerprint']} "
        f"wouldSkip={str(decision.would_skip).lower()} "
        f"reason={decision.reason}"
    )
    return {
        "sourceDigests": source_digests,
        "contractDigests": contract_digests,
        "inputFingerprint": input_fingerprint,
        "decision": decision,
        "taskStatePath": task_state_path,
    }


def record_fingerprint_error(mode, exc):
    with profile_operation(
        "orchestration",
        f"education.fingerprint.{mode}_decision",
        counters={
            "fingerprintHit": 0,
            "wouldSkip": 0,
            "actuallySkipped": 0,
            "manifestInvalid": 1,
        },
        metadata={
            "taskId": EDUCATION_TASK_ID,
            "reason": "fingerprint_error",
            "shadowOnly": mode == "shadow",
        },
    ):
        pass
    log(
        f"Fingerprint {mode} indisponivel; wouldSkip=false "
        f"reason=fingerprint_error ({type(exc).__name__})."
    )


@profiled_main_from_environment("education")
def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Exportador transacional dos Indicadores da Educacao: gera em "
            "staging, valida integralmente e somente entao publica."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemplos:\n"
            "  %(prog)s --state RS                         # gera e publica\n"
            "  %(prog)s --state rs --dry-run               # valida e mostra o plano\n"
            "  %(prog)s --state RS --no-promote            # preserva staging validado\n"
            "  %(prog)s --state RS --staging-dir CAMINHO   # staging exclusivo controlado\n"
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Opção legada reconhecida; lotes parciais são recusados.",
    )
    parser.add_argument(
        "--municipios",
        type=str,
        default=None,
        help="Opção legada reconhecida; lotes parciais são recusados.",
    )
    parser.add_argument(
        "--skip-regioes",
        action="store_true",
        help="Preserva explicitamente os artefatos regionais legados fora do lote.",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=0,
        help="Exibir progresso a cada N municipios.",
    )
    parser.add_argument(
        "--diagnostic",
        action="store_true",
        help="Exibe detalhes dos arquivos materializados no staging.",
    )
    parser.add_argument(
        "--state",
        default=DEFAULT_STATE_CODE,
        help=f"Código estadual configurado (padrão: {DEFAULT_STATE_CODE}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Valida estado e mostra o plano sem banco, staging ou escrita.",
    )
    parser.add_argument(
        "--staging-dir",
        type=Path,
        default=None,
        help="Diretório exclusivo do run; deve estar fora de public/data.",
    )
    parser.add_argument(
        "--no-promote",
        action="store_true",
        help="Gera e valida integralmente, mas preserva o staging sem publicar.",
    )
    fingerprint_group = parser.add_mutually_exclusive_group()
    fingerprint_group.add_argument(
        "--fingerprint-shadow",
        action="store_true",
        help=(
            "Mede se a tarefa educacional seria reutilizavel, mas continua "
            "executando o fluxo integral sem skip real."
        ),
    )
    fingerprint_group.add_argument(
        "--fingerprint-skip",
        action="store_true",
        help=(
            "Reutiliza a publicacao somente quando o fingerprint e os 499 "
            "outputs forem comprovadamente integros."
        ),
    )
    args = parser.parse_args(argv)
    if args.fingerprint_skip and args.no_promote:
        parser.error("--fingerprint-skip nao pode ser combinado com --no-promote.")

    try:
        with profile_operation(
            "validation",
            "education.configuration",
            metadata={"requestedState": args.state},
        ) as configuration_event:
            state_code = normalize_state_code(args.state)
            state_config = load_state_config(state_code)
            registry = load_municipality_registry(state_config)
            route_compatibility = load_education_municipality_route_compatibility(
                state_config,
                registry,
            )
            configuration_event.add_counter(
                "municipalities", registry.municipality_count
            )
    except (
        FileNotFoundError,
        StateConfigError,
        MunicipalityRegistryError,
        EducationMunicipalityRouteCompatibilityError,
    ) as exc:
        print(f"Configuração estadual inválida: {exc}", file=sys.stderr)
        return 2

    if args.limit is not None or args.municipios:
        print(
            "Exportações municipais parciais foram desativadas: o contrato "
            "transacional exige o lote integral.",
            file=sys.stderr,
        )
        return 2

    public_root = default_public_root()
    if args.dry_run:
        planned_staging = (
            args.staging_dir
            if args.staging_dir is not None
            else DATA_PIPELINE_DIR / ".staging" / "education" / "<run-id>"
        )
        print("[education] Dry run: nenhuma fonte, banco ou escrita será acessado.")
        print(f"[education] Estado validado: {state_config.state_code}.")
        print(
            "[education] Universo municipal: "
            f"{registry.municipality_count} códigos IBGE textuais."
        )
        print(f"[education] Staging planejado: {planned_staging}.")
        print(
            "[education] Allowlist: index.json, municipios_index.json e "
            f"{registry.municipality_count} arquivos municipios/<IBGE>.json."
        )
        print(f"[education] Destino após validação integral: {public_root}.")
        if args.no_promote:
            print("[education] Promoção: desativada por --no-promote.")
        if args.fingerprint_shadow or args.fingerprint_skip:
            mode = "shadow" if args.fingerprint_shadow else "skip"
            print(
                f"[education] Fingerprint {mode} solicitado: o dry-run não calcula "
                "digests nem lê ou grava task state."
            )
        with profile_operation(
            "orchestration",
            "education.plan",
            counters={
                "municipalitiesPlanned": registry.municipality_count,
                "processesStarted": 0,
            },
            metadata={"dryRun": True, "stagingCreated": False},
        ):
            pass
        return 0

    generation_summary = {}
    fingerprint_mode = (
        "skip"
        if args.fingerprint_skip
        else "shadow"
        if args.fingerprint_shadow
        else None
    )
    prepared_inputs = None

    if fingerprint_mode == "skip":
        log("Preparando decisao incremental antes de criar staging...")
        prepared_inputs = load_education_inputs(
            state_config,
            registry,
            diagnostic=args.diagnostic,
        )
        try:
            skip_context = calculate_education_fingerprint(
                inputs=prepared_inputs,
                state_config=state_config,
                registry=registry,
                public_root=public_root,
                mode="skip",
            )
            generation_summary["fingerprint"] = skip_context
        except Exception as exc:
            generation_summary["fingerprintError"] = type(exc).__name__
            record_fingerprint_error("skip", exc)
        else:
            decision = skip_context["decision"]
            if decision.would_skip:
                log(
                    "Reutilizacao confirmada: zero staging, materializacao, "
                    "validacao de staging, promocao, backup ou rollback."
                )
                with profile_operation(
                    "orchestration",
                    "education.result",
                    counters={
                        "fingerprintHit": 1,
                        "wouldSkip": 1,
                        "actuallySkipped": 1,
                        "stagingCreated": 0,
                        "municipalitiesMaterialized": 0,
                        "filesRendered": 0,
                        "bytesRendered": 0,
                        "filesValidated": 0,
                    },
                    metadata={"reused": True, "reason": decision.reason},
                ):
                    pass
                emit_education_result(
                    reused=True,
                    publication_noop=False,
                    reason=decision.reason,
                    staging_created=0,
                    municipalities_materialized=0,
                    files_rendered=0,
                    bytes_rendered=0,
                    files_validated=0,
                    promoted=False,
                    state_written=False,
                )
                log("RESUMO FINAL: reused=true, publicationNoop=false")
                return 0
            log(
                "Modo incremental: elegibilidade nao comprovada; "
                "a Educacao sera executada integralmente."
            )

    def materialize(output_root):
        log("=" * 60)
        log("Exportador transacional de Indicadores da Educacao")
        log(f"Estado: {state_config.state_code}")
        log(f"Data: {DATA_EXPORTACAO}")
        log(f"Staging: {output_root}")
        log("Artefatos regionais legados: preservados fora da allowlist ativa")
        if args.diagnostic:
            log("MODO DIAGNOSTICO ativado")
        log("")

        inputs = prepared_inputs or load_education_inputs(
            state_config,
            registry,
            diagnostic=args.diagnostic,
        )
        municipalities = inputs["municipalities"]
        municipality_ids = inputs["municipalityIds"]
        frames = inputs["frames"]
        available_years = inputs["availableYears"]

        if args.fingerprint_shadow:
            try:
                source_frames = {"municipalities": municipalities, **frames}
                with profile_operation(
                    "compute",
                    "education.fingerprint.sources",
                    metadata={"eventGranularity": "aggregate"},
                ) as source_event:
                    source_digests = digest_education_sources(source_frames)
                    source_event.add_counters(**source_digests["stats"])

                with profile_operation(
                    "read",
                    "education.fingerprint.contracts",
                    metadata={"allowlist": "education-explicit-v1"},
                ) as contract_event:
                    utils_contract = resolve_imported_python_module_contract(
                        "utils_educacao",
                        contract_id="utils_educacao",
                    )
                    contract_digests = digest_contract_files(
                        REPO_ROOT,
                        external_python_contracts=(utils_contract,),
                    )
                    contract_event.add_counters(
                        contracts=contract_digests["fileCount"],
                        bytesHashed=contract_digests["bytesHashed"],
                    )

                with profile_operation(
                    "compute",
                    "education.fingerprint.input",
                    metadata={"taskId": EDUCATION_TASK_ID},
                ) as input_event:
                    input_fingerprint = build_input_fingerprint(
                        source_digests,
                        contract_digests,
                        state_code=state_config.state_code,
                        execution_parameters={
                            "municipalityCount": registry.municipality_count,
                            "publicationContract": "transactional-full-v1",
                            "outputCount": registry.municipality_count + 2,
                        },
                    )
                    input_event.add_counter(
                        "bytesHashed", input_fingerprint["bytesHashed"]
                    )

                task_state_path = default_task_state_path(DATA_PIPELINE_DIR)
                previous_state = load_task_state(task_state_path)
                with profile_operation(
                    "validation",
                    "education.fingerprint.output_integrity",
                    metadata={"phase": "shadow_decision"},
                ) as output_event:
                    decision = evaluate_shadow_eligibility(
                        previous_state,
                        input_fingerprint,
                        contract_digests,
                        public_root,
                        municipality_ids,
                    )
                    output_event.add_counters(
                        managedOutputs=decision.output_integrity.managed_outputs,
                        outputBytesVerified=(
                            decision.output_integrity.output_bytes_verified
                        ),
                        manifestInvalid=int(decision.manifest_invalid),
                    )
                with profile_operation(
                    "orchestration",
                    "education.fingerprint.shadow_decision",
                    counters={
                        "fingerprintHit": int(decision.fingerprint_hit),
                        "wouldSkip": int(decision.would_skip),
                        "actuallySkipped": 0,
                        "manifestInvalid": int(decision.manifest_invalid),
                    },
                    metadata={
                        "taskId": EDUCATION_TASK_ID,
                        "reason": decision.reason,
                        "shadowOnly": True,
                    },
                ):
                    pass
                generation_summary["fingerprint"] = {
                    "sourceDigests": source_digests,
                    "contractDigests": contract_digests,
                    "inputFingerprint": input_fingerprint,
                    "decision": decision,
                    "taskStatePath": task_state_path,
                }
                log(
                    "Fingerprint shadow: "
                    f"taskId={EDUCATION_TASK_ID} "
                    f"inputFingerprint={input_fingerprint['inputFingerprint']} "
                    f"wouldSkip={str(decision.would_skip).lower()} "
                    f"reason={decision.reason}"
                )
                log(
                    "Fingerprint shadow não pula trabalho: consultas, materialização, "
                    "validação e promoção continuam."
                )
            except Exception as exc:
                generation_summary["fingerprintError"] = str(exc)
                with profile_operation(
                    "orchestration",
                    "education.fingerprint.shadow_decision",
                    counters={
                        "fingerprintHit": 0,
                        "wouldSkip": 0,
                        "actuallySkipped": 0,
                        "manifestInvalid": 1,
                    },
                    metadata={
                        "taskId": EDUCATION_TASK_ID,
                        "reason": "fingerprint_error",
                        "shadowOnly": True,
                    },
                ):
                    pass
                log(
                    "Fingerprint shadow indisponível; wouldSkip=false "
                    f"reason=fingerprint_error ({type(exc).__name__})."
                )

        generated, written, sizes = materialize_education_outputs(
            output_root,
            municipalities,
            frames,
            available_years,
            registry,
            route_compatibility,
            args.progress_every,
        )
        validation = validar_jsons(
            generated,
            registry,
            route_compatibility,
            output_root=output_root,
        )
        rendered_paths = tuple(
            path for path in Path(output_root).rglob("*") if path.is_file()
        )
        rendered_bytes = sum(path.stat().st_size for path in rendered_paths)
        generation_summary.update(
            generated=generated,
            written=written,
            sizes=sizes,
            validation=validation,
            filesRendered=generated + 2,
            bytesRendered=rendered_bytes,
        )

    try:
        result = publish_education_transactionally(
            registry=registry,
            route_compatibility=route_compatibility,
            materialize=materialize,
            public_root=public_root,
            staging_directory=args.staging_dir,
            no_promote=args.no_promote,
        )
    except EducationMunicipalityBatchError as exc:
        print(f"[education] Lote municipal rejeitado: {exc}", file=sys.stderr)
        return 1
    except EducationPublicationError as exc:
        print(f"[education] Publicação recusada: {exc}", file=sys.stderr)
        return 1

    state_written = False
    if fingerprint_mode:
        fingerprint = generation_summary.get("fingerprint")
        if result.stats is None:
            with profile_operation(
                "write",
                "education.fingerprint.state_write",
                counters={"manifestWritten": 0},
                metadata={"reason": "no_promote"},
            ):
                pass
            log(f"Fingerprint {fingerprint_mode}: task state não gravado por --no-promote.")
        elif fingerprint is None:
            with profile_operation(
                "write",
                "education.fingerprint.state_write",
                counters={"manifestWritten": 0},
                metadata={"reason": "fingerprint_error"},
            ):
                pass
        else:
            try:
                with profile_operation(
                    "validation",
                    "education.fingerprint.output_integrity",
                    metadata={"phase": "post_publication"},
                ) as output_event:
                    output_manifest = build_output_manifest(
                        public_root,
                        (
                            record.ibge_code
                            for record in registry.ordered_records
                        ),
                        state_code=state_config.state_code,
                    )
                    output_event.add_counters(
                        managedOutputs=output_manifest["managedOutputCount"],
                        outputBytesVerified=output_manifest["totalBytes"],
                    )
                task_state = build_task_state(
                    input_fingerprint=fingerprint["inputFingerprint"],
                    source_digests=fingerprint["sourceDigests"],
                    contract_digests=fingerprint["contractDigests"],
                    output_manifest=output_manifest,
                    decision=fingerprint["decision"],
                )
                with profile_operation(
                    "write",
                    "education.fingerprint.state_write",
                    metadata={"taskId": EDUCATION_TASK_ID},
                ) as state_event:
                    write_task_state_atomic(
                        fingerprint["taskStatePath"],
                        task_state,
                    )
                    state_event.add_counters(
                        manifestWritten=1,
                        managedOutputs=output_manifest["managedOutputCount"],
                    )
                state_written = True
                log(
                    f"Fingerprint {fingerprint_mode}: task state atômico gravado somente após "
                    "a publicação final confirmada."
                )
            except Exception as exc:
                print(
                    f"[education] Falha ao confirmar task state {fingerprint_mode}: "
                    f"{type(exc).__name__}.",
                    file=sys.stderr,
                )
                return 1

    log("")
    log("=" * 60)
    log("RESUMO FINAL")
    log("=" * 60)
    log(f"Municipios materializados: {result.validation.municipality_count}")
    log(f"Arquivos validados: {len(result.validation.files)}")
    if result.stats is None:
        log("Promocao: nao executada (--no-promote)")
        log(f"Staging validado preservado: {result.staged_output}")
    else:
        log(f"created: {result.stats.created}")
        log(f"updated: {result.stats.updated}")
        log(f"preserved: {result.stats.preserved}")
        log(f"removed: {result.stats.removed}")
        log("Staging e backups: removidos com seguranca")
    if args.diagnostic:
        log(
            f"Arquivos materializados neste ciclo: "
            f"{len(generation_summary.get('written', []))}"
        )
        for path in generation_summary.get("written", []):
            log(f"  {path}")
    sizes = generation_summary.get("sizes", [])
    rendered_bytes = generation_summary.get(
        "bytesRendered",
        sum(size for _municipality_id, _name, size in sizes),
    )
    files_rendered = generation_summary.get(
        "filesRendered",
        result.validation.municipality_count + 2,
    )
    publication_noop = bool(
        result.stats is not None
        and result.stats.created == 0
        and result.stats.updated == 0
        and result.stats.removed == 0
    )
    result_counters = {
        "municipalities": result.validation.municipality_count,
        "municipalitiesMaterialized": result.validation.municipality_count,
        "filesRendered": files_rendered,
        "filesValidated": len(result.validation.files),
        "bytesRendered": rendered_bytes,
        "stagingCreated": 1,
    }
    result_metadata = {
        "promoted": result.stats is not None,
        "reused": False,
        "publicationNoop": publication_noop,
    }
    result_reason = "integral"
    if fingerprint_mode:
        fingerprint = generation_summary.get("fingerprint")
        decision = fingerprint.get("decision") if fingerprint else None
        result_reason = decision.reason if decision is not None else "fingerprint_error"
        result_counters.update(
            fingerprintHit=int(decision.fingerprint_hit) if decision else 0,
            wouldSkip=int(decision.would_skip) if decision else 0,
            actuallySkipped=0,
        )
        result_metadata["fingerprintMode"] = fingerprint_mode
        result_metadata["reason"] = result_reason
    if result.stats is not None:
        result_counters.update(
            created=result.stats.created,
            updated=result.stats.updated,
            preserved=result.stats.preserved,
            removed=result.stats.removed,
        )
    with profile_operation(
        "orchestration",
        "education.result",
        counters=result_counters,
        metadata=result_metadata,
    ):
        pass
    emit_education_result(
        reused=False,
        publication_noop=publication_noop,
        reason=result_reason,
        staging_created=1,
        municipalities_materialized=result.validation.municipality_count,
        files_rendered=files_rendered,
        bytes_rendered=rendered_bytes,
        files_validated=len(result.validation.files),
        promoted=result.stats is not None,
        state_written=state_written,
    )
    log(
        "Resultado operacional: reused=false "
        f"publicationNoop={str(publication_noop).lower()}"
    )
    elapsed = time.time() - _START_TIME
    log(f"Tempo total: {elapsed:.1f}s")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
