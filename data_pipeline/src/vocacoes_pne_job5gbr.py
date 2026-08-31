"""Correção semântica e de composição do pacote Job 5G-B-R V7.

O módulo lê somente os artefatos congelados dos Jobs 5G-B e 5G-A-R,
verifica seus hashes, acrescenta metadados semânticos sem recalcular fatos e
materializa de forma determinística um novo pacote técnico em staging.

Não há acesso a banco, rede, ``public/data``, frontend ou compilador.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gb"
FROZEN_JOB5GAR_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gar"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gbr"

FINAL_STATE = "JOB_5GB_R_READY_FOR_EXTERNAL_JUDGMENT"
SOURCE_MANIFEST_SHA256 = "9b5ddc70e9966da2220a18d93364441d2043c53383c98fa2834a7ae1b51a410e"
FROZEN_JOB5GAR_MANIFEST_SHA256 = "4cad7f2a349be252ba85face41731d41d4b38a48419730c842ee9a6e09b97252"
NOVA_SANTA_RITA_ID = "4313375"
NOVO_HAMBURGO_ID = "4313409"
EXPECTED_CODES = (
    "4303905",
    "4306403",
    "4307609",
    "4307708",
    "4310801",
    "4313375",
    "4313409",
    "4314803",
    "4318705",
    "4320008",
)

ORIGINAL_FILES = (
    "DICIONARIO_ESCOLARIDADE_ADULTA_2010_2022_V1.json",
    "PAINEL_ESCOLARIDADE_ADULTA_2010_2022_V1.csv.gz",
    "PAINEL_EJA_DISTRIBUICAO_2022_V1.csv.gz",
    "PAINEL_EJA_HISTORICA_2014_2025_V1.csv.gz",
    "PAINEL_EJA_INTEGRADA_EPT_V1.csv.gz",
    "PAINEL_VULNERABILIDADE_EDUCACIONAL_V1.csv.gz",
    "PAINEL_EDUCACAO_ESPECIAL_AEE_V1.csv.gz",
    "PAINEL_EDUCACAO_RURAL_TERRITORIO_V1.csv.gz",
    "MATRIZ_VINCULOS_PNE_PME_JOB5GB_V1.csv.gz",
    "NOVA_SANTA_RITA_JOB5GB_V1.json",
    "MATRIZ_OPORTUNIDADES_REAVALIADAS_JOB5GB_V1.csv.gz",
    "MAPA_SECOES_POTENCIAIS_JOB5GB_V1.md",
    "LIMITACOES_JOB5GB_V1.json",
    "PACOTE_REVISAO_EXTERNA_JOB5GB.json",
    "MANIFEST_JOB5GB.json",
)

OUTPUT_FILES = (
    "ERRATA_METODOLOGICA_JOB5GB_V7.md",
    "DICIONARIO_SEMANTICO_METRICAS_JOB5GB_V1.json",
    "PAINEL_ESCOLARIDADE_ADULTA_2010_2022_V1_1.csv.gz",
    "PAINEL_EJA_DISTRIBUICAO_2022_V1_1.csv.gz",
    "PAINEL_EJA_HISTORICA_2014_2025_V1_1.csv.gz",
    "PAINEL_EJA_INTEGRADA_EPT_V1_1.csv.gz",
    "PAINEL_VULNERABILIDADE_EDUCACIONAL_V1_1.csv.gz",
    "PAINEL_EDUCACAO_INDIGENA_V1.csv.gz",
    "PAINEL_EDUCACAO_ESPECIAL_AEE_V1_1.csv.gz",
    "PAINEL_EDUCACAO_RURAL_TERRITORIO_V1_1.csv.gz",
    "MATRIZ_VINCULOS_PNE_PME_JOB5GB_V1_1.csv.gz",
    "NOVA_SANTA_RITA_JOB5GB_V1_1.json",
    "MATRIZ_QA_JOB5GB_V1_1.csv.gz",
    "MATRIZ_C1_C12_CANONICA_JOB5GB_V1_1.csv.gz",
    "MATRIZ_OPORTUNIDADES_REAVALIADAS_JOB5GB_V1_1.csv.gz",
    "MAPA_SECOES_POTENCIAIS_JOB5GB_V1_1.md",
    "PACOTE_REVISAO_EXTERNA_JOB5GBR.json",
    "MANIFEST_JOB5GBR.json",
)

CANONICAL_CRITERIA = {
    "C1": "relevância para PNE/PME",
    "C2": "mecanismo definido antes do resultado",
    "C3": "universos e lentes compatíveis",
    "C4": "período coerente",
    "C5": "estabilidade suficiente",
    "C6": "integração dos fatos",
    "C7": "diferença municipal útil",
    "C8": "município, etapa, público, indicador e questão de planejamento",
    "C9": "comunicabilidade editorial",
    "C10": "rastreabilidade",
    "C11": "não redundância",
    "C12": "valor incremental além da demografia",
}
CRITERION_STATUSES = {"SUPPORTED", "PARTIAL", "NOT_SUPPORTED", "NOT_EVALUABLE"}

FRONT_CONFIG: dict[str, dict[str, Any]] = {
    "A_ESCOLARIDADE_ADULTA_2010_2022": {
        "classification": "READY_WITH_COUNT_ONLY_AND_CATEGORY_GUARDRAILS",
        "question": "Como as contagens de escolaridade adulta mudaram entre 2010 e 2022 sem inferir mudança de taxa?",
        "states": [
            "SUPPORTED", "SUPPORTED", "SUPPORTED", "PARTIAL", "NOT_EVALUABLE", "SUPPORTED",
            "SUPPORTED", "PARTIAL", "PARTIAL", "SUPPORTED", "SUPPORTED", "SUPPORTED",
        ],
        "evidence": [
            "As contagens 18+ se vinculam ao acompanhamento das metas 11.b e 11.c sem recalcular o indicador legal.",
            "As relações cumulativa, subconjunto e diferença derivada foram definidas antes da releitura dos valores.",
            "O universo é população residente de 18 anos ou mais e não é fundido com matrícula ou cadastro.",
            "As contagens são comparáveis, mas o denominador 2010 ausente impede comparação intercensitária de participações.",
            "Dois pontos censitários não permitem testar estabilidade e fonte oficial, isoladamente, não a comprova.",
            "A composição exclusiva de 2022 fecha sem empilhar as categorias cumulativas sobrepostas.",
            "Há diferenças municipais úteis em mudanças absolutas de contagem e decomposição líquida interna.",
            "Município, público 18+, categorias e questão estão definidos; etapa escolar não é uma dimensão literal deste objeto.",
            "A comunicação exige contagem, waterfall positivo/negativo e composição exclusiva de 2022, sem alegação de melhora.",
            "Censos, definições, hashes e transformações de categoria permanecem rastreáveis.",
            "O objeto acrescenta escolaridade adulta intercensitária sem duplicar a fotografia demográfica genérica.",
            "As categorias educacionais acrescentam conteúdo além do tamanho da população residente.",
        ],
    },
    "B_EJA_DISTRIBUICAO_2022": {
        "classification": "READY_AFTER_STAGE_SPECIFIC_SOURCE_SPLIT",
        "question": "Como os públicos residentes e as matrículas localizadas se distribuem separadamente no fundamental e no médio?",
        "states": [
            "SUPPORTED", "SUPPORTED", "PARTIAL", "SUPPORTED", "NOT_EVALUABLE", "PARTIAL",
            "SUPPORTED", "SUPPORTED", "PARTIAL", "SUPPORTED", "SUPPORTED", "SUPPORTED",
        ],
        "evidence": [
            "A distribuição por etapa organiza o acompanhamento relacionado à Meta 11.d.",
            "O contraste distributivo foi definido por participação regional dentro de cada etapa, sem razão de atendimento.",
            "Residência e localização da escola ficam separadas; o fundamental não é compatível com o total populacional do painel adulto.",
            "Todos os fatos usam a âncora 2022 e contratos explicitamente separados por etapa.",
            "É uma fotografia de 2022; estabilidade temporal não foi testada nem é inferida da oficialidade da fonte.",
            "As participações fecham dentro de cada etapa, mas fundamental e médio não podem ser combinados sob um único contrato.",
            "As diferenças de distribuição preservam contraste municipal útil e direções próprias por etapa.",
            "Município, etapas fundamental/médio, públicos, indicadores e questão de planejamento estão explícitos.",
            "A leitura requer painéis separados e proíbe cobertura, atendimento, alcance, demanda, suficiência, capacidade e barreiras não observadas.",
            "O contrato Job 2C, a diferença regional de 18.401 e os valores distributivos permanecem rastreáveis.",
            "A separação por etapa evita uma direção única redundante ou enganosa.",
            "A distribuição localizada acrescenta informação educacional além da demografia residente.",
        ],
    },
    "C_EJA_HISTORICA_2014_2025": {
        "classification": "READY_WITH_SERIES_CONTEXT_AND_CONTRIBUTION_GUARDRAILS",
        "question": "Como EJA fundamental e médio mudaram entre 2014 e 2025 e quais intervalos exigem contexto?",
        "states": [
            "SUPPORTED", "SUPPORTED", "SUPPORTED", "PARTIAL", "PARTIAL", "SUPPORTED",
            "SUPPORTED", "SUPPORTED", "PARTIAL", "SUPPORTED", "SUPPORTED", "SUPPORTED",
        ],
        "evidence": [
            "A série por etapa informa acompanhamento descritivo associado à Meta 11.d.",
            "Mudança absoluta, composição e contribuição líquida foram definidas sem atribuição causal.",
            "O universo é matrícula EJA localizada na escola, em rede total, sem inferência sobre residência.",
            "A janela 2014–2025 é comum, mas intervalos abruptos foram marcados para revisão contextual.",
            "A série é longa, porém metadados locais de definição estão ausentes e rupturas materiais impedem suporte pleno.",
            "Fundamental mais médio fecha exatamente o total de contexto em cada grão.",
            "Mudanças municipais positivas e negativas mostram diferenças úteis sem converter contribuição líquida em participação aditiva.",
            "Município, etapas, público matriculado, indicador e pergunta de acompanhamento estão definidos.",
            "A série pode ser mostrada com intervalos destacados; total é referência e não integra a pilha dos componentes.",
            "Valores congelados, regra de ruptura e notas de contexto são auditáveis.",
            "A dimensão histórica acrescenta evolução temporal à distribuição de 2022.",
            "A trajetória por etapa acrescenta informação educacional além da demografia.",
        ],
    },
    "D_EJA_INTEGRADA_EPT": {
        "classification": "READY_WITH_ZERO_MODALITY_AND_PERIOD_GUARDRAILS",
        "question": "Como acompanhar modalidades de EJA integrada à EPT sem interpretar zero como ausência de acesso?",
        "states": [
            "SUPPORTED", "SUPPORTED", "SUPPORTED", "PARTIAL", "PARTIAL", "SUPPORTED",
            "SUPPORTED", "SUPPORTED", "PARTIAL", "SUPPORTED", "SUPPORTED", "SUPPORTED",
        ],
        "evidence": [
            "Os componentes se vinculam diretamente ao acompanhamento da Meta 12.c sem recalcular o indicador legal.",
            "A composição por modalidades foi definida como soma de três componentes do total integrado.",
            "As métricas são matrículas localizadas em escolas da rede total e não população residente.",
            "A janela é comum, mas FIC médio a partir de 2023 requer contexto estrutural sem causa atribuída.",
            "A mudança estrutural de 2023 e 11 divergências administrativas de QA limitam a estabilidade comparável.",
            "Técnico integrado, FIC fundamental e FIC médio fecham exatamente o total integrado.",
            "Há diferenças municipais observadas, inclusive zeros, sem transformar zero em decisão automática.",
            "Município, EJA, modalidades, indicador e questão de articulação estão explícitos.",
            "O total não pode ser empilhado com componentes e zeros não podem ser título ou recomendação de oferta.",
            "Série congelada, fechamento e divergências de QA permanecem documentados.",
            "A composição por modalidade não duplica a série EJA total.",
            "A integração EJA/EPT acrescenta conteúdo educacional além da demografia.",
        ],
    },
    "E_VULNERABILIDADE": {
        "classification": "DESCRIPTIVE_CONTEXT_ONLY",
        "question": "Que contexto cadastral agregado pode acompanhar equidade sem identificar o público EJA?",
        "states": [
            "PARTIAL", "PARTIAL", "SUPPORTED", "SUPPORTED", "NOT_EVALUABLE", "PARTIAL",
            "PARTIAL", "PARTIAL", "PARTIAL", "SUPPORTED", "PARTIAL", "PARTIAL",
        ],
        "evidence": [
            "O cadastro oferece contexto de equidade, mas não materializa diretamente um indicador PNE/PME educacional.",
            "O uso contextual foi definido previamente; não há mecanismo individual ligando cadastro e escolaridade.",
            "Famílias e pessoas permanecem separadas na lente cadastral e não são vinculadas a matrículas.",
            "O recorte 2024-12 é coerente como fotografia cadastral agregada.",
            "Uma fotografia mensal não permite avaliar estabilidade e não recebe suporte por ser fonte oficial.",
            "Métricas sobrepostas não são somadas; a integração com fatos educacionais permanece deliberadamente limitada.",
            "Diferenças municipais podem contextualizar perguntas, mas não autorizam ranking de necessidade.",
            "Município, unidades cadastrais e pergunta estão definidos; etapa e público EJA não são identificados.",
            "Apenas contexto descritivo é comunicável, com famílias e pessoas em blocos separados.",
            "Snapshots locais, período, unidades e ausência de microvinculação são rastreáveis.",
            "Pode sobrepor contexto demográfico/social e por isso deve permanecer subordinado às análises educacionais.",
            "Acrescenta contexto cadastral, mas não uma decisão educacional autônoma além da demografia.",
        ],
    },
    "E2_EDUCACAO_INDIGENA": {
        "classification": "CONDITIONAL_SPECIFIC_PUBLIC_CONTEXT_ONLY",
        "question": "Quais fatos escolares indígenas positivos podem compor contexto municipal específico sem denominador residente?",
        "states": [
            "PARTIAL", "PARTIAL", "PARTIAL", "SUPPORTED", "PARTIAL", "PARTIAL",
            "PARTIAL", "PARTIAL", "PARTIAL", "SUPPORTED", "SUPPORTED", "SUPPORTED",
        ],
        "evidence": [
            "Os fatos escolares dialogam com a Meta 9.d, mas o indicador legal não foi recalculado.",
            "A lente de localização escolar foi definida antes da revisão; não há mecanismo de acesso residente.",
            "A oferta escolar é compatível internamente, mas não existe denominador residente combinado.",
            "A série 2023–2025 usa período e unidades comuns.",
            "Três anos permitem inspeção limitada, sem teste suficiente para suporte pleno de estabilidade.",
            "Matrículas, escolas, turmas e docentes ficam separados e não formam um total aditivo.",
            "Somente São Leopoldo tem fato positivo; zeros dos demais municípios não são diferença de acesso interpretável.",
            "Município, público específico, fatos e questão estão claros; o indicador legal permanece indisponível.",
            "O bloco municipal é condicional a fato positivo; zero integral permanece apenas no dossiê técnico.",
            "Fonte INEP, lente, rede total e ausência de denominador residente estão registradas.",
            "O público específico não é redundante com vulnerabilidade cadastral.",
            "Fatos escolares indígenas acrescentam informação além da demografia, sob guarda condicional.",
        ],
    },
    "F_EDUCACAO_ESPECIAL_AEE": {
        "classification": "READY_WITH_METRIC_FAMILY_AND_NON_ADDITIVITY_GUARDRAILS",
        "question": "Como acompanhar inclusão, etapas/modalidades e escolas de AEE sem somas ou coberturas indevidas?",
        "states": [
            "SUPPORTED", "PARTIAL", "SUPPORTED", "SUPPORTED", "PARTIAL", "PARTIAL",
            "SUPPORTED", "SUPPORTED", "PARTIAL", "SUPPORTED", "SUPPORTED", "SUPPORTED",
        ],
        "evidence": [
            "As famílias de fatos se vinculam ao acompanhamento das metas 10.a e 10.b.",
            "Inclusão e oferta escolar são processos observáveis, sem mecanismo de prevalência residente.",
            "Todas as métricas usam localização escolar e rede total, sem denominador residente.",
            "A janela 2014–2025 é comum aos fatos materializados.",
            "A janela é longa, mas não houve teste completo de estabilidade de definições para todas as famílias.",
            "Comum mais exclusiva fecha o total; etapas e métricas de escola permanecem explicitamente não aditivas.",
            "Há diferenças municipais úteis em inclusão e oferta escolar, sem inferir prevalência.",
            "Município, etapas/públicos, métricas e pergunta de acompanhamento estão definidos.",
            "Famílias exigem visuais separados; etapas e três métricas de escola não podem ser empilhadas.",
            "Definições independentes, fonte, valores e fechamento de inclusão são rastreáveis.",
            "O objeto acrescenta inclusão, modalidades e AEE sem duplicar uma única métrica total.",
            "Os fatos de educação especial/AEE acrescentam conteúdo educacional além da demografia.",
        ],
    },
    "G_EDUCACAO_RURAL_TERRITORIO": {
        "classification": "READY_WITH_STAGE_AND_NON_ADDITIVITY_GUARDRAILS",
        "question": "Como matrículas, turmas e escolas rurais se distribuem por etapa sem inferir residência ou capacidade?",
        "states": [
            "PARTIAL", "PARTIAL", "SUPPORTED", "SUPPORTED", "PARTIAL", "PARTIAL",
            "SUPPORTED", "SUPPORTED", "PARTIAL", "SUPPORTED", "SUPPORTED", "SUPPORTED",
        ],
        "evidence": [
            "A distribuição rural funciona como proxy contextual para acompanhamento territorial relacionado à Meta 11.e.",
            "Localização rural da escola é mecanismo territorial observável, sem mecanismo de residência ou deslocamento.",
            "A lente é localização rural da escola em rede total e permanece separada da população residente.",
            "A série 2014–2025 usa período comum e fatos escolares comparáveis por grão.",
            "A janela é longa, mas estabilidade de todas as definições por etapa não foi testada integralmente.",
            "O total é referência; escolas por etapa e profissional podem sobrepor-se, e somas só valem em grãos fechados.",
            "Diferenças municipais de fatos escolares rurais são úteis como descrição territorial.",
            "Município, etapa, público escolar, indicador e questão territorial estão definidos.",
            "A comunicação exige total de referência separado e marcação de sobreposição, sem distância ou capacidade.",
            "Fonte escolar, lente, regras de funcionamento e testes de fechamento são rastreáveis.",
            "O recorte rural acrescenta localização territorial sem repetir a oferta escolar geral.",
            "A distribuição rural acrescenta conteúdo educacional além da demografia residente.",
        ],
    },
    "H_VINCULOS_PNE_PME": {
        "classification": "READY_AS_INTERNAL_METADATA_LAYER",
        "question": "Como associar vínculos PNE/PME às análises sem criar seção visual ou fatos inexistentes?",
        "states": [
            "SUPPORTED", "NOT_EVALUABLE", "PARTIAL", "SUPPORTED", "NOT_EVALUABLE", "PARTIAL",
            "NOT_EVALUABLE", "PARTIAL", "PARTIAL", "SUPPORTED", "PARTIAL", "PARTIAL",
        ],
        "evidence": [
            "Goal, indicador, modo e tipo de vínculo organizam relevância PNE/PME.",
            "A camada é metadado interno e não testa mecanismo substantivo próprio.",
            "As lentes são herdadas dos painéis associados e não podem ser fundidas na camada.",
            "Cada vínculo preserva seu período contratual.",
            "Metadados sem série factual própria não permitem avaliar estabilidade.",
            "A camada integra referências às seções, mas não cria fatos nem seção autônoma.",
            "Sem fatos próprios, diferença municipal não é avaliável nesta camada.",
            "Os vínculos herdam município, etapa, público e questão; quatro referências docentes continuam sem valores.",
            "É comunicável apenas como metadado associado, com standalone_visual_module=false.",
            "Goal, indicator, mode, link_type, período, limitação e contrato permanecem rastreáveis.",
            "Evita redundância ao não gerar módulo PNE/PME independente.",
            "O valor incremental existe somente quando o vínculo acompanha um fato materializado da seção associada.",
        ],
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.generic):
        value = value.item()
    if value is pd.NA or value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        dtype={
            "municipality_ibge_code": "string",
            "reference_period": "string",
        },
        keep_default_na=False,
        na_values=["null"],
        float_precision="round_trip",
    )


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(_json_safe(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_csv_gzip(path: Path, frame: pd.DataFrame) -> None:
    text = frame.to_csv(index=False, na_rep="null", lineterminator="\n")
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as compressed:
            compressed.write(text.encode("utf-8"))


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return [_json_safe(record) for record in frame.to_dict(orient="records")]


def _truthy(series: pd.Series) -> pd.Series:
    return series.astype(str).str.casefold().isin({"true", "1"})


def _verify_originals(source_root: Path = SOURCE_ROOT) -> dict[str, dict[str, Any]]:
    manifest_path = source_root / "MANIFEST_JOB5GB.json"
    if sha256_file(manifest_path) != SOURCE_MANIFEST_SHA256:
        raise ValueError("Hash do MANIFEST_JOB5GB.json diverge do checkpoint canônico.")
    manifest = _load_json(manifest_path)
    declared = {item["path"]: item for item in manifest["artifacts"]}
    expected_declared = set(ORIGINAL_FILES) - {"MANIFEST_JOB5GB.json"}
    if set(declared) != expected_declared:
        raise ValueError("Manifesto 5G-B não declara exatamente os 14 artefatos anteriores.")

    result: dict[str, dict[str, Any]] = {}
    for name in ORIGINAL_FILES:
        path = source_root / name
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = {"byteSize": path.stat().st_size, "sha256": sha256_file(path)}
        if name in declared:
            if actual["byteSize"] != declared[name]["byteSize"]:
                raise ValueError(f"Tamanho original divergente: {name}")
            if actual["sha256"] != declared[name]["sha256"]:
                raise ValueError(f"Hash original divergente: {name}")
        result[name] = actual
    return result


def _verify_frozen_job5gar(root: Path = FROZEN_JOB5GAR_ROOT) -> dict[str, dict[str, Any]]:
    manifest_path = root / "MANIFEST_JOB5GAR.json"
    if sha256_file(manifest_path) != FROZEN_JOB5GAR_MANIFEST_SHA256:
        raise ValueError("Hash do MANIFEST_JOB5GAR.json congelado diverge.")
    manifest = _load_json(manifest_path)
    declared = {item["path"]: item for item in manifest["artifacts"]}
    actual_names = {path.name for path in root.iterdir() if path.is_file()}
    if actual_names != set(declared) | {"MANIFEST_JOB5GAR.json"}:
        raise ValueError("Conjunto congelado do Job 5G-A-R diverge dos 13 artefatos aprovados.")
    result: dict[str, dict[str, Any]] = {}
    for name in sorted(actual_names):
        path = root / name
        actual = {"byteSize": path.stat().st_size, "sha256": sha256_file(path)}
        if name in declared:
            if actual["byteSize"] != declared[name]["byteSize"] or actual["sha256"] != declared[name]["sha256"]:
                raise ValueError(f"Artefato congelado do Job 5G-A-R divergente: {name}")
        result[name] = actual
    return result


def _validate_unique(frame: pd.DataFrame, columns: Sequence[str], label: str) -> None:
    duplicated = frame.duplicated(list(columns), keep=False)
    if duplicated.any():
        raise ValueError(f"Grão duplicado em {label}: {int(duplicated.sum())} linhas")


def _assert_original_columns_preserved(
    original: pd.DataFrame,
    corrected: pd.DataFrame,
    label: str,
    *,
    sort_columns: Sequence[str],
) -> None:
    columns = list(original.columns)
    if list(corrected.columns[: len(columns)]) != columns:
        raise ValueError(f"Colunas factuais originais não são prefixo estável em {label}.")
    left = original.sort_values(list(sort_columns), na_position="last").reset_index(drop=True)
    right = corrected[columns].sort_values(list(sort_columns), na_position="last").reset_index(drop=True)
    try:
        pd.testing.assert_frame_equal(left, right, check_dtype=False, check_exact=True)
    except AssertionError as error:
        raise ValueError(f"Valor factual original alterado em {label}: {error}") from error


ADULT_CATEGORY_SEMANTICS: dict[str, dict[str, Any]] = {
    "fundamental_completed_or_more": {
        "category_role": "cumulative_indicator",
        "is_cumulative": True,
        "is_derived": False,
        "parent_category": None,
        "mutually_exclusive_group": None,
        "additivity_status": "NON_ADDITIVE_OVERLAPPING_CUMULATIVE",
        "stacking_allowed_in_2022_exclusive_composition": False,
    },
    "high_school_completed_or_more": {
        "category_role": "cumulative_indicator_and_top_exclusive_band",
        "is_cumulative": True,
        "is_derived": False,
        "parent_category": "fundamental_completed_or_more",
        "mutually_exclusive_group": "adult_schooling_2022_exclusive_composition",
        "additivity_status": "ADDITIVE_ONLY_AS_TOP_BAND_IN_2022_EXCLUSIVE_COMPOSITION",
        "stacking_allowed_in_2022_exclusive_composition": True,
    },
    "fundamental_completed_without_high_school": {
        "category_role": "derived_exclusive_band",
        "is_cumulative": False,
        "is_derived": True,
        "parent_category": "fundamental_completed_or_more",
        "mutually_exclusive_group": "adult_schooling_2022_exclusive_composition",
        "additivity_status": "ADDITIVE_ONLY_IN_2022_EXCLUSIVE_COMPOSITION",
        "stacking_allowed_in_2022_exclusive_composition": True,
    },
    "without_fundamental_completed": {
        "category_role": "exclusive_2022_only_band",
        "is_cumulative": False,
        "is_derived": False,
        "parent_category": None,
        "mutually_exclusive_group": "adult_schooling_2022_exclusive_composition",
        "additivity_status": "ADDITIVE_ONLY_IN_2022_EXCLUSIVE_COMPOSITION",
        "stacking_allowed_in_2022_exclusive_composition": True,
    },
}


def _adult_panel(source_root: Path = SOURCE_ROOT) -> pd.DataFrame:
    panel = _read_csv(source_root / "PAINEL_ESCOLARIDADE_ADULTA_2010_2022_V1.csv.gz")
    corrected = panel.copy()
    for field in (
        "category_role",
        "is_cumulative",
        "is_derived",
        "parent_category",
        "mutually_exclusive_group",
        "additivity_status",
        "stacking_allowed_in_2022_exclusive_composition",
    ):
        corrected[field] = corrected["schooling_category"].map(
            {category: semantics[field] for category, semantics in ADULT_CATEGORY_SEMANTICS.items()}
        )
    corrected["denominator_2010_available"] = False
    corrected["denominator_2022_available"] = True
    corrected["intercensal_share_change_allowed"] = False
    corrected["improvement_claim_allowed"] = False
    corrected["intercensal_change_role"] = "COUNT_CHANGE_ONLY"
    corrected["municipal_contribution_to_vale_change_percent_role"] = (
        "INTERNAL_NET_CHANGE_DECOMPOSITION_ONLY"
    )
    corrected["network_scope"] = "total_all_dependencies"
    corrected["administrative_dependency_is_analytic_dimension"] = False
    corrected["administrative_dependency_is_QA_dimension"] = True
    return corrected


def _distribution_panel(source_root: Path = SOURCE_ROOT) -> pd.DataFrame:
    panel = _read_csv(source_root / "PAINEL_EJA_DISTRIBUICAO_2022_V1.csv.gz")
    corrected = panel.copy()
    fundamental = corrected["stage"].eq("fundamental")
    corrected["distribution_object_id"] = np.where(
        fundamental,
        "EJA_DISTRIBUICAO_FUNDAMENTAL_2022",
        "EJA_DISTRIBUICAO_MEDIO_2022",
    )
    corrected["source_contract"] = np.where(
        fundamental,
        "JOB2C_ESTIMATED_18PLUS_TOTAL_MINUS_CENSUS_COMPLETION",
        "CENSUS_COMPLETION_COUNT_DIFFERENCE_2022",
    )
    corrected["adult_panel_compatibility"] = np.where(
        fundamental,
        "DEFINITION_INCOMPATIBLE_POPULATION_TOTAL_SOURCE",
        "COMPARABLE_COUNT_DIFFERENCE",
    )
    corrected["regional_count_difference_vs_adult_panel"] = np.where(fundamental, 18401, 0)
    corrected["cross_stage_combination_allowed"] = False
    corrected["distribution_interpretation"] = "WITHIN_STAGE_DISTRIBUTION_ONLY"
    corrected["forbidden_rate_or_capacity_inference"] = True
    return corrected


def _history_panel(source_root: Path = SOURCE_ROOT) -> pd.DataFrame:
    panel = _read_csv(source_root / "PAINEL_EJA_HISTORICA_2014_2025_V1.csv.gz")
    corrected = panel.copy()
    component = corrected["stage"].isin(["fundamental", "high_school"])
    corrected["metric_role"] = np.where(component, "component", "reference_total")
    corrected["component_of"] = np.where(component, "total_context", pd.NA)
    corrected["stacking_group"] = np.where(
        component,
        "eja_stage_components",
        "eja_reference_total_non_stacking",
    )
    corrected["stacking_allowed"] = component
    corrected["series_context_status"] = "NO_ABRUPT_REGIONAL_MOVEMENT_FLAGGED"
    corrected["series_context_note"] = (
        "Definition metadata unavailable; no interval flagged under the regional material-movement rule."
    )
    corrected["definition_metadata_available"] = False
    corrected["institutional_explanation_allowed"] = False
    corrected["municipal_contribution_to_vale_change_percent_role"] = (
        "INTERNAL_NET_CHANGE_DECOMPOSITION_ONLY"
    )

    regional_components = corrected[
        corrected["entity_scope"].eq("region")
        & corrected["stage"].isin(["fundamental", "high_school"])
        & corrected["year_over_year_absolute_change"].notna()
    ].copy()
    regional_components["_material"] = (
        regional_components["year_over_year_absolute_change"].abs().ge(500)
        & regional_components["year_over_year_percent_change"].abs().ge(20)
    )
    flagged = regional_components[regional_components["_material"]]
    for row in flagged.itertuples(index=False):
        year = int(row.year)
        stage = str(row.stage)
        absolute_change = float(row.year_over_year_absolute_change)
        percent_change = float(row.year_over_year_percent_change)
        interval = f"{year - 1}->{year}"
        region_mask = (
            corrected["entity_scope"].eq("region")
            & corrected["year"].eq(year)
            & corrected["stage"].eq(stage)
        )
        corrected.loc[region_mask, "series_context_status"] = (
            "ABRUPT_REGIONAL_MOVEMENT_REQUIRES_CONTEXT"
        )
        corrected.loc[region_mask, "series_context_note"] = (
            f"Regional {stage} interval {interval}: net change {absolute_change:g} "
            f"({percent_change:.6f}%); definition metadata unavailable and no cause assigned."
        )

        municipal_mask = (
            corrected["entity_scope"].eq("municipality")
            & corrected["year"].eq(year)
            & corrected["stage"].eq(stage)
        )
        corrected.loc[municipal_mask, "series_context_status"] = (
            "REGIONAL_INTERVAL_REQUIRES_CONTEXT"
        )
        corrected.loc[municipal_mask, "series_context_note"] = (
            f"Municipal value belongs to flagged regional {stage} interval {interval}; no cause assigned."
        )
        if absolute_change != 0:
            contribution = (
                corrected.loc[municipal_mask, "year_over_year_absolute_change"].abs()
                / abs(absolute_change)
                * 100
            )
            concentrated_indexes = contribution[contribution.ge(50)].index
            for index in concentrated_indexes:
                name = corrected.at[index, "municipality_name"]
                share = float(contribution.loc[index])
                corrected.at[index, "series_context_status"] = (
                    "MUNICIPAL_CONCENTRATION_IN_ABRUPT_REGIONAL_MOVEMENT"
                )
                corrected.at[index, "series_context_note"] = (
                    f"{name} absolute movement in {interval} equals {share:.6f}% of the absolute "
                    f"regional net movement for {stage}; offsets may produce values above 100%; no cause assigned."
                )

        total_mask = (
            corrected["year"].eq(year)
            & corrected["stage"].eq("total_context")
            & corrected["entity_scope"].isin(["municipality", "region"])
        )
        corrected.loc[total_mask, "series_context_status"] = (
            "REFERENCE_TOTAL_INCLUDES_FLAGGED_COMPONENT_INTERVAL"
        )
        corrected.loc[total_mask, "series_context_note"] = (
            f"Reference total includes a flagged {stage} component in {interval}; total is not stacked with components."
        )
    return corrected


def _integrated_panel(source_root: Path = SOURCE_ROOT) -> pd.DataFrame:
    panel = _read_csv(source_root / "PAINEL_EJA_INTEGRADA_EPT_V1.csv.gz")
    corrected = panel.copy()
    total = corrected["modality"].eq("integrated_total")
    zero = pd.to_numeric(corrected["integrated_eja_enrollments"], errors="raise").eq(0)
    corrected["metric_role"] = np.where(total, "reference_total", "component")
    corrected["component_of"] = np.where(total, pd.NA, "integrated_total")
    corrected["stacking_group"] = np.where(
        total,
        "integrated_eja_reference_total_non_stacking",
        "integrated_eja_components",
    )
    corrected["stacking_allowed"] = ~total
    structural = corrected["modality"].eq("fic_high_school") & corrected["year"].ge(2023)
    corrected["period_context_status"] = np.where(
        structural,
        "STRUCTURAL_SERIES_CHANGE_REQUIRES_CONTEXT",
        "NO_STRUCTURAL_SERIES_CHANGE_FLAGGED",
    )
    corrected["period_context_note"] = np.where(
        structural,
        "FIC high-school series from 2023 requires official contextual metadata; no cause is assigned.",
        "No structural period flag on this row.",
    )
    corrected["observation_semantics"] = np.where(zero, "observed_zero", "observed_nonzero")
    corrected["zero_access_conclusion_allowed"] = False
    corrected["zero_offer_creation_recommendation_allowed"] = False
    corrected["zero_headline_allowed"] = False
    corrected["administrative_divergences_2016_2018_role"] = "QA_ONLY_11_ROWS"
    return corrected


def _vulnerability_and_indigenous(
    source_root: Path = SOURCE_ROOT,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    panel = _read_csv(source_root / "PAINEL_VULNERABILIDADE_EDUCACIONAL_V1.csv.gz")
    vulnerability = panel[
        panel["context_domain"].eq("registered_vulnerability_context")
    ].copy()
    vulnerability["object_id"] = "E_VULNERABILIDADE"
    vulnerability["classification"] = "DESCRIPTIVE_CONTEXT_ONLY"
    vulnerability["metric_family"] = vulnerability["unit_of_observation"].map(
        {"families": "REGISTERED_FAMILIES", "people": "REGISTERED_PEOPLE"}
    )
    vulnerability["additivity_status"] = "NON_ADDITIVE_OVERLAPPING_REGISTER_COUNTS"
    vulnerability["families_people_combination_allowed"] = False
    vulnerability["eja_public_identification_allowed"] = False
    vulnerability["need_ranking_allowed"] = False

    indigenous = panel[
        panel["context_domain"].eq("indigenous_education_specific_public")
    ].copy()
    values = pd.to_numeric(indigenous["value"], errors="raise")
    positive_codes = set(
        indigenous.loc[
            indigenous["entity_scope"].eq("municipality") & values.gt(0),
            "municipality_ibge_code",
        ].dropna()
    )
    indigenous["object_id"] = "E2_EDUCACAO_INDIGENA"
    indigenous["classification"] = "CONDITIONAL_SPECIFIC_PUBLIC_CONTEXT_ONLY"
    indigenous["resident_denominator_available"] = False
    indigenous["resident_denominator_combined"] = False
    indigenous["legal_indicator_recalculated"] = False
    indigenous["zero_population_or_access_inference_allowed"] = False
    indigenous["observation_semantics"] = np.where(values.eq(0), "observed_zero", "observed_nonzero")
    indigenous["municipal_card_eligible"] = (
        indigenous["entity_scope"].eq("municipality")
        & indigenous["municipality_ibge_code"].isin(positive_codes)
    )
    indigenous["regional_context_allowed"] = indigenous["entity_scope"].eq("region")
    indigenous["automatic_zero_based_card_allowed"] = False
    return vulnerability, indigenous


SPECIAL_DEFINITIONS = {
    "special_enrollments": "Matrículas de educação especial em classes comuns ou exclusivas.",
    "common_class_enrollments": "Matrículas de educação especial em classes comuns.",
    "exclusive_class_enrollments": "Matrículas de educação especial em classes exclusivas.",
    "special_enrollments_early_childhood": "Matrículas de educação especial observadas na educação infantil.",
    "special_enrollments_fundamental": "Matrículas de educação especial observadas no ensino fundamental.",
    "special_enrollments_high_school": "Matrículas de educação especial observadas no ensino médio.",
    "special_enrollments_eja": "Matrículas de educação especial observadas na EJA.",
    "special_enrollments_professional": "Matrículas de educação especial observadas na educação profissional; pode sobrepor etapas básicas.",
    "schools_with_special_enrollment": "Contagem de escolas com pelo menos uma matrícula de educação especial.",
    "schools_offering_aee": "Contagem de escolas que declaram oferta de AEE.",
    "schools_with_aee_resource_room": "Contagem de escolas que declaram sala de recursos para AEE.",
}


def _special_panel(source_root: Path = SOURCE_ROOT) -> pd.DataFrame:
    panel = _read_csv(source_root / "PAINEL_EDUCACAO_ESPECIAL_AEE_V1.csv.gz")
    corrected = panel.copy()
    inclusion = corrected["metric"].isin(
        ["special_enrollments", "common_class_enrollments", "exclusive_class_enrollments"]
    )
    school = corrected["metric"].isin(
        ["schools_with_special_enrollment", "schools_offering_aee", "schools_with_aee_resource_room"]
    )
    stage = ~(inclusion | school)
    corrected["metric_family"] = np.select(
        [inclusion, stage, school],
        ["INCLUSION", "STAGES_MODALITIES", "SCHOOLS"],
        default="UNCLASSIFIED",
    )
    corrected["metric_role"] = np.select(
        [corrected["metric"].eq("special_enrollments"), corrected["metric"].isin(["common_class_enrollments", "exclusive_class_enrollments"]), stage, school],
        ["reference_total", "component", "non_additive_stage_or_modality", "independent_school_metric"],
        default="unclassified",
    )
    corrected["component_of"] = np.where(
        corrected["metric"].isin(["common_class_enrollments", "exclusive_class_enrollments"]),
        "special_enrollments",
        pd.NA,
    )
    corrected["stacking_group"] = np.where(
        corrected["metric"].isin(["common_class_enrollments", "exclusive_class_enrollments"]),
        "special_inclusion_components",
        "non_stacking_metric",
    )
    corrected["stacking_allowed"] = corrected["metric"].isin(
        ["common_class_enrollments", "exclusive_class_enrollments"]
    )
    corrected["stage_breakdown_additive"] = False
    corrected["school_metrics_additive"] = False
    corrected["professional_overlap_possible"] = corrected["stage"].eq("professional")
    corrected["resident_prevalence_or_coverage_allowed"] = False
    corrected["metric_definition"] = corrected["metric"].map(SPECIAL_DEFINITIONS)
    return corrected


def _rural_panel(source_root: Path = SOURCE_ROOT) -> pd.DataFrame:
    panel = _read_csv(source_root / "PAINEL_EDUCACAO_RURAL_TERRITORIO_V1.csv.gz")
    corrected = panel.copy()
    corrected["metric_family"] = corrected["metric"].map(
        {
            "rural_enrollments": "ENROLLMENTS",
            "rural_classes": "CLASSES",
            "rural_schools": "SCHOOLS",
        }
    )
    corrected["stage_additivity_status"] = "NOT_VALIDATED_AT_GRAIN"
    corrected["stage_sum_closure_validated"] = False
    corrected["stage_sum_closure_residual_excluding_professional"] = pd.NA
    corrected["school_count_overlap_possible"] = corrected["metric"].eq("rural_schools")
    corrected["professional_overlap_possible"] = True
    corrected["total_context_only"] = corrected["stage"].eq("all")
    corrected["stacking_allowed"] = False

    keys = ["entity_scope", "municipality_ibge_code", "municipality_name", "year", "metric"]
    basic_stages = ["early_childhood", "fundamental", "high_school", "eja"]
    for _, group in corrected.groupby(keys, dropna=False, sort=False):
        values = group.set_index("stage")["value"]
        if not {"all", "professional", *basic_stages}.issubset(values.index):
            continue
        total = float(values["all"])
        basic_sum = sum(float(values[stage]) for stage in basic_stages)
        residual = total - basic_sum
        indexes = group.index
        corrected.loc[indexes, "stage_sum_closure_residual_excluding_professional"] = residual
        school_metric = group["metric"].iloc[0] == "rural_schools"
        closure_valid = not school_metric and math.isclose(residual, 0.0, abs_tol=1e-12)
        corrected.loc[indexes, "stage_sum_closure_validated"] = closure_valid
        if school_metric:
            corrected.loc[indexes, "stage_additivity_status"] = (
                "NON_ADDITIVE_SCHOOL_OVERLAP_POSSIBLE"
            )
        elif closure_valid:
            corrected.loc[indexes, "stage_additivity_status"] = (
                "VALIDATED_BASIC_STAGE_CLOSURE_AT_GRAIN_EXCLUDING_PROFESSIONAL"
            )
            stack_indexes = group[group["stage"].isin(basic_stages)].index
            corrected.loc[stack_indexes, "stacking_allowed"] = True
        else:
            corrected.loc[indexes, "stage_additivity_status"] = "NOT_VALIDATED_AT_GRAIN"
    return corrected


def _pne_links(source_root: Path = SOURCE_ROOT) -> pd.DataFrame:
    panel = _read_csv(source_root / "MATRIZ_VINCULOS_PNE_PME_JOB5GB_V1.csv.gz")
    corrected = panel.copy()
    teacher_reference = corrected["analysis_id"].str.startswith("teacher_")
    materialized_indicator = ~corrected["indicator_id"].eq("not_materialized")
    indigenous = corrected["analysis_id"].eq("indigenous_education_observed")
    corrected["page_role"] = "INTERNAL_METADATA_LAYER"
    corrected["standalone_visual_module"] = False
    corrected["materialized_fact_available"] = ~teacher_reference
    corrected["materialized_value_available"] = materialized_indicator & ~teacher_reference & ~indigenous
    corrected.loc[teacher_reference, "adds_concrete_decision"] = False
    corrected["resident_denominator_combined"] = False
    corrected["associated_section_id"] = corrected["analysis_id"].map(
        {
            "adult_fundamental_18_plus": "A_ESCOLARIDADE_ADULTA_2010_2022",
            "adult_high_school_18_plus": "A_ESCOLARIDADE_ADULTA_2010_2022",
            "eja_distribution_fundamental_2022": "B_EJA_DISTRIBUICAO_2022",
            "eja_distribution_high_school_2022": "B_EJA_DISTRIBUICAO_2022",
            "eja_historical_fundamental": "C_EJA_HISTORICA_2014_2025",
            "eja_historical_high_school": "C_EJA_HISTORICA_2014_2025",
            "eja_integrated_ept": "D_EJA_INTEGRADA_EPT",
            "vulnerability_context": "E_VULNERABILIDADE",
            "indigenous_education_observed": "E2_EDUCACAO_INDIGENA",
            "special_education_common_exclusive": "F_EDUCACAO_ESPECIAL_AEE",
            "aee_school_offer": "F_EDUCACAO_ESPECIAL_AEE",
            "rural_school_distribution": "G_EDUCACAO_RURAL_TERRITORIO",
            "teacher_training_initial_years_tracking": "FROZEN_JOB5GAR_RELATED_METADATA",
            "teacher_training_final_years_tracking": "FROZEN_JOB5GAR_RELATED_METADATA",
            "teacher_training_high_school_tracking": "FROZEN_JOB5GAR_RELATED_METADATA",
            "teacher_postgraduate_tracking": "FROZEN_JOB5GAR_RELATED_METADATA",
        }
    )
    return corrected


def _semantic_dictionary(source_root: Path = SOURCE_ROOT) -> dict[str, Any]:
    original = _load_json(source_root / "DICIONARIO_ESCOLARIDADE_ADULTA_2010_2022_V1.json")
    adult_categories = []
    for category in original["categories"]:
        category_id = category["categoryId"]
        semantics = ADULT_CATEGORY_SEMANTICS[category_id]
        adult_categories.append(
            {
                **category,
                **semantics,
                "denominator_2010_available": False,
                "denominator_2022_available": True,
                "intercensal_share_change_allowed": False,
                "improvement_claim_allowed": False,
            }
        )
    return {
        "schemaVersion": "semantic-metric-dictionary-job5gb-v1.1",
        "jobId": "v7-job5gbr",
        "sourceJob": "v7-job5gb",
        "sourceDictionarySha256": sha256_file(
            source_root / "DICIONARIO_ESCOLARIDADE_ADULTA_2010_2022_V1.json"
        ),
        "canonicalScope": {
            "network_scope": "total_all_dependencies",
            "administrative_dependency_is_analytic_dimension": False,
            "administrative_dependency_is_QA_dimension": True,
            "municipality_identity": "textual_ibge_code_7_digits",
            "cross_source_person_linkage_performed": False,
        },
        "territorialLenses": {
            "resident_population": "População residente.",
            "registered_context": "Cadastro agregado por residência ou município declarado pela fonte.",
            "school_location": "Matrícula, turma ou escola segundo localização da escola.",
            "rural_school_location": "Localização rural da escola, sem inferência de residência ou deslocamento.",
            "work_establishment": "Vínculo por localização do estabelecimento; não combinado neste job.",
        },
        "adultSchooling": {
            "objectId": "A_ESCOLARIDADE_ADULTA",
            "universe": original["universe"],
            "territorialLens": original["territorialLens"],
            "categories": adult_categories,
            "intercensalChangeRole": "COUNT_CHANGE_ONLY",
            "municipalContributionRole": "INTERNAL_NET_CHANGE_DECOMPOSITION_ONLY",
            "visualPreference": [
                "absolute_change",
                "positive_negative_waterfall",
                "exclusive_2022_composition",
            ],
            "cumulativeCategoriesStackingAllowed": False,
        },
        "ejaDistribution2022": {
            "objects": {
                "EJA_DISTRIBUICAO_FUNDAMENTAL_2022": {
                    "source_contract": "JOB2C_ESTIMATED_18PLUS_TOTAL_MINUS_CENSUS_COMPLETION",
                    "adult_panel_compatibility": "DEFINITION_INCOMPATIBLE_POPULATION_TOTAL_SOURCE",
                    "regional_count_difference_vs_adult_panel": 18401,
                },
                "EJA_DISTRIBUICAO_MEDIO_2022": {
                    "source_contract": "CENSUS_COMPLETION_COUNT_DIFFERENCE_2022",
                    "adult_panel_compatibility": "COMPARABLE_COUNT_DIFFERENCE",
                    "regional_count_difference_vs_adult_panel": 0,
                },
            },
            "crossStageCombinationAllowed": False,
            "forbiddenInterpretations": [
                "matriculas_por_mil",
                "cobertura",
                "atendimento",
                "alcance",
                "demanda",
                "suficiencia",
                "capacidade",
                "barreira_explicativa_nao_observada",
            ],
        },
        "ejaHistorical": {
            "closure": "fundamental + high_school = total_context",
            "totalRole": "reference_total_non_stacking",
            "municipalContributionRole": "INTERNAL_NET_CHANGE_DECOMPOSITION_ONLY",
            "definitionMetadataAvailable": False,
            "institutionalExplanationAllowed": False,
            "abruptMovementRule": {
                "scope": "region_component_stage",
                "minimumAbsoluteChange": 500,
                "minimumAbsolutePercentChange": 20,
                "municipalConcentrationThresholdPercentOfAbsoluteRegionalNetChange": 50,
                "causeAttributionAllowed": False,
            },
        },
        "ejaIntegratedEpt": {
            "closure": "integrated_total = technical_integrated + fic_fundamental + fic_high_school",
            "totalRole": "reference_total_non_stacking",
            "administrativeDivergences2016To2018": {"count": 11, "role": "QA_ONLY"},
            "ficHighSchoolFrom2023": "STRUCTURAL_SERIES_CHANGE_REQUIRES_CONTEXT",
            "causeAttributionAllowed": False,
            "observedZero": {
                "accessConclusionAllowed": False,
                "offerCreationRecommendationAllowed": False,
                "headlineAllowed": False,
            },
        },
        "vulnerability": {
            "objectId": "E_VULNERABILIDADE",
            "classification": "DESCRIPTIVE_CONTEXT_ONLY",
            "familiesAndPeopleRemainSeparate": True,
            "overlappingMetricsAdditive": False,
            "identifiesEjaPublic": False,
            "needRankingAllowed": False,
        },
        "indigenousEducation": {
            "objectId": "E2_EDUCACAO_INDIGENA",
            "classification": "CONDITIONAL_SPECIFIC_PUBLIC_CONTEXT_ONLY",
            "territorialLens": "school_location",
            "residentDenominatorCombined": False,
            "legalIndicatorRecalculated": False,
            "zeroProvesNoPopulationOrAccess": False,
            "municipalBlockRequiresPositiveSchoolFact": True,
            "regionalContextAllowed": True,
        },
        "specialEducationAee": {
            "families": {
                "INCLUSION": {
                    "closure": "special_enrollments = common_class_enrollments + exclusive_class_enrollments",
                    "totalRole": "reference_total_non_stacking",
                },
                "STAGES_MODALITIES": {
                    "members": ["early_childhood", "fundamental", "high_school", "eja", "professional"],
                    "stage_breakdown_additive": False,
                    "professionalMayOverlapBasicStages": True,
                },
                "SCHOOLS": {
                    "members": [
                        "schools_with_special_enrollment",
                        "schools_offering_aee",
                        "schools_with_aee_resource_room",
                    ],
                    "additive": False,
                    "orderedSubsetsAssumed": False,
                    "stackingAllowed": False,
                },
            },
            "metricDefinitions": SPECIAL_DEFINITIONS,
            "residentPrevalenceOrCoverageAllowed": False,
        },
        "ruralEducation": {
            "allRole": "reference_total_non_stacking",
            "schoolStageCountsMayOverlap": True,
            "professionalMayOverlapBasicStageOrEja": True,
            "stageSumRule": "ONLY_WHEN_VALIDATED_FOR_EXACT_METRIC_YEAR_ENTITY_GRAIN",
            "forbiddenInferences": [
                "residencia",
                "distancia",
                "deslocamento",
                "fechamento_de_escola",
                "insuficiencia",
                "capacidade",
            ],
        },
        "pnePmeLinks": {
            "page_role": "INTERNAL_METADATA_LAYER",
            "standalone_visual_module": False,
            "associatedWithAnalyticalSections": True,
            "contractChanged": False,
            "teacherReferencesWithoutRematerializedValues": 4,
        },
    }


def _qa_matrix(source_root: Path = SOURCE_ROOT) -> pd.DataFrame:
    source = _read_csv(source_root / "MATRIZ_OPORTUNIDADES_REAVALIADAS_JOB5GB_V1.csv.gz")
    records: list[dict[str, Any]] = []
    for row in source.to_dict(orient="records"):
        for index in range(1, 13):
            records.append(
                {
                    "analysis_id": row["analysis_id"],
                    "qa_control_id": f"QA{index}_JOB5GB",
                    "original_control_id": f"C{index}",
                    "qa_control_meaning": row[f"c{index}_meaning"],
                    "qa_control_status": row[f"c{index}_status"],
                    "qa_control_evidence": row[f"c{index}_evidence"],
                    "source_classification": row["classification"],
                    "score": pd.NA,
                    "automatic_approval": False,
                    "external_judgment_required": True,
                    "source_artifact": "MATRIZ_OPORTUNIDADES_REAVALIADAS_JOB5GB_V1.csv.gz",
                }
            )
    return pd.DataFrame.from_records(records)


def _canonical_matrix() -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for analysis_id, config in FRONT_CONFIG.items():
        states = config["states"]
        evidence = config["evidence"]
        if len(states) != 12 or len(evidence) != 12:
            raise ValueError(f"Avaliação C1–C12 incompleta: {analysis_id}")
        for index, criterion_id in enumerate(CANONICAL_CRITERIA, start=1):
            records.append(
                {
                    "analysis_id": analysis_id,
                    "substantive_question": config["question"],
                    "classification": config["classification"],
                    "criterion_id": criterion_id,
                    "criterion_meaning": CANONICAL_CRITERIA[criterion_id],
                    "criterion_status": states[index - 1],
                    "criterion_evidence": evidence[index - 1],
                    "score": pd.NA,
                    "automatic_approval": False,
                    "external_judgment_required": True,
                }
            )
    return pd.DataFrame.from_records(records)


def _opportunity_matrix(canonical: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for analysis_id, config in FRONT_CONFIG.items():
        subset = canonical[canonical["analysis_id"].eq(analysis_id)].set_index("criterion_id")
        row: dict[str, Any] = {
            "analysis_id": analysis_id,
            "substantive_question": config["question"],
            "classification": config["classification"],
            "page_role": (
                "INTERNAL_METADATA_LAYER"
                if analysis_id == "H_VINCULOS_PNE_PME"
                else "ANALYTICAL_OR_CONTEXT_SECTION_CANDIDATE"
            ),
            "standalone_visual_module": False if analysis_id == "H_VINCULOS_PNE_PME" else pd.NA,
            "score": pd.NA,
            "automatic_approval": False,
            "external_judgment_required": True,
            "canonical_matrix_path": "MATRIZ_C1_C12_CANONICA_JOB5GB_V1_1.csv.gz",
            "qa_matrix_path": "MATRIZ_QA_JOB5GB_V1_1.csv.gz",
        }
        for criterion_id in CANONICAL_CRITERIA:
            row[f"{criterion_id.lower()}_status"] = subset.at[criterion_id, "criterion_status"]
        rows.append(row)
    return pd.DataFrame.from_records(rows)


def _entity_records(panel: pd.DataFrame, scope: str) -> list[dict[str, Any]]:
    if "entity_scope" not in panel:
        return []
    return _records(panel[panel["entity_scope"].eq(scope)])


def _dossier(panels: Mapping[str, pd.DataFrame]) -> dict[str, Any]:
    group_specs = [
        ("escolaridade_adulta", "A_ESCOLARIDADE_ADULTA_2010_2022", "adult"),
        ("distribuicao_eja_2022", "B_EJA_DISTRIBUICAO_2022", "distribution"),
        ("eja_historica", "C_EJA_HISTORICA_2014_2025", "history"),
        ("eja_integrada_ept", "D_EJA_INTEGRADA_EPT", "integrated"),
        ("vulnerabilidade_cadastral", "E_VULNERABILIDADE", "vulnerability"),
        ("educacao_indigena", "E2_EDUCACAO_INDIGENA", "indigenous"),
        ("educacao_especial_aee", "F_EDUCACAO_ESPECIAL_AEE", "special"),
        ("educacao_rural", "G_EDUCACAO_RURAL_TERRITORIO", "rural"),
    ]
    technical_groups: list[dict[str, Any]] = []
    for group_id, analysis_id, panel_key in group_specs:
        panel = panels[panel_key]
        municipality = panel["municipality_ibge_code"].eq(NOVA_SANTA_RITA_ID)
        future_eligibility = "SUBJECT_TO_EXTERNAL_JUDGMENT"
        if group_id == "educacao_indigena":
            eligible = _truthy(panel.loc[municipality, "municipal_card_eligible"]).any()
            future_eligibility = (
                "ELIGIBLE_POSITIVE_MUNICIPAL_SCHOOL_FACT"
                if eligible
                else "INELIGIBLE_NO_POSITIVE_MUNICIPAL_SCHOOL_FACT"
            )
        technical_groups.append(
            {
                "id": group_id,
                "analysisId": analysis_id,
                "classification": FRONT_CONFIG[analysis_id]["classification"],
                "mandatoryMunicipalCard": False,
                "futureDisplayEligibility": future_eligibility,
                "municipalFacts": _records(panel[municipality]),
                "valeFacts": _entity_records(panel, "region"),
                "rsFacts": _entity_records(panel, "state"),
            }
        )

    links = panels["links"]
    technical_groups.append(
        {
            "id": "vinculos_pne_pme",
            "analysisId": "H_VINCULOS_PNE_PME",
            "classification": FRONT_CONFIG["H_VINCULOS_PNE_PME"]["classification"],
            "pageRole": "INTERNAL_METADATA_LAYER",
            "standaloneVisualModule": False,
            "mandatoryMunicipalCard": False,
            "futureDisplayEligibility": "NOT_STANDALONE_METADATA",
            "metadataFacts": _records(links),
        }
    )

    compact_synthesis = [
        {
            "id": "escolaridade_adulta_e_eja",
            "technicalGroupIds": ["escolaridade_adulta", "distribuicao_eja_2022", "eja_historica"],
            "metadataLayerIds": ["vinculos_pne_pme"],
            "mandatoryMunicipalCard": False,
        },
        {
            "id": "integracao_eja_ept",
            "technicalGroupIds": ["eja_integrada_ept"],
            "metadataLayerIds": ["vinculos_pne_pme"],
            "mandatoryMunicipalCard": False,
        },
        {
            "id": "equidade_e_publicos_especificos",
            "technicalGroupIds": ["vulnerabilidade_cadastral", "educacao_indigena", "educacao_especial_aee"],
            "metadataLayerIds": ["vinculos_pne_pme"],
            "mandatoryMunicipalCard": False,
        },
        {
            "id": "distribuicao_territorial_da_oferta",
            "technicalGroupIds": ["educacao_rural"],
            "metadataLayerIds": ["vinculos_pne_pme"],
            "mandatoryMunicipalCard": False,
        },
    ]
    return {
        "schemaVersion": "nova-santa-rita-job5gb-v1.1",
        "municipalityIbgeCode": NOVA_SANTA_RITA_ID,
        "municipalityName": "Nova Santa Rita",
        "networkScope": "total_all_dependencies",
        "administrativeDependencyIsAnalyticDimension": False,
        "administrativeDependencyIsQADimension": True,
        "publicNarrativeProduced": False,
        "technicalGroupCount": len(technical_groups),
        "technicalGroupsAreMandatoryCards": False,
        "technicalGroups": technical_groups,
        "compactMacroGroupCount": len(compact_synthesis),
        "compactSynthesis": compact_synthesis,
    }


def _section_map() -> str:
    lines = [
        "# MAPA INTERNO DE SEÇÕES POTENCIAIS — JOB 5G-B-R V1.1",
        "",
        "> Artefato técnico para julgamento externo; não é narrativa pública nem especificação de interface.",
        "",
        "- Rede educacional: `total_all_dependencies`.",
        "- Dependência administrativa: somente QA.",
        "- Os nove grupos técnicos não equivalem a nove cartões obrigatórios.",
        "- Os vínculos PNE/PME são metadados associados e não formam seção autônoma.",
        "",
        "## Frentes corrigidas",
        "",
    ]
    for analysis_id, config in FRONT_CONFIG.items():
        lines.extend(
            [
                f"### {analysis_id}",
                "",
                f"- Estado: `{config['classification']}`",
                f"- Pergunta técnica: {config['question']}",
                "- Aprovação automática: `false`",
                "",
            ]
        )
    lines.extend(
        [
            "## Síntese compacta permitida para prototipação futura",
            "",
            "1. escolaridade adulta e EJA;",
            "2. integração EJA/EPT;",
            "3. equidade e públicos específicos;",
            "4. distribuição territorial da oferta.",
            "",
            "## Guardas de composição",
            "",
            "- Categorias cumulativas da escolaridade adulta não são empilhadas.",
            "- Fundamental e médio da distribuição EJA usam contratos próprios.",
            "- Totais de referência não são empilhados com seus componentes.",
            "- Vulnerabilidade e educação indígena são objetos separados.",
            "- Métricas de escola/AEE e escolas rurais por etapa não são tratadas como partes aditivas.",
            "- Zero indígena não cria cartão municipal automático.",
            "- Não iniciar Job 5G-C, Job 5H, Job 6, interface, compilador ou publicação.",
            "",
        ]
    )
    return "\n".join(lines)


def _qa_summary(
    panels: Mapping[str, pd.DataFrame],
    qa_matrix: pd.DataFrame,
    canonical_matrix: pd.DataFrame,
    opportunities: pd.DataFrame,
    dossier: Mapping[str, Any],
) -> dict[str, Any]:
    history = panels["history"]
    abrupt = history[
        history["entity_scope"].eq("region")
        & history["series_context_status"].eq("ABRUPT_REGIONAL_MOVEMENT_REQUIRES_CONTEXT")
    ][["year", "stage", "year_over_year_absolute_change", "year_over_year_percent_change"]]
    concentrations = history[
        history["series_context_status"].eq(
            "MUNICIPAL_CONCENTRATION_IN_ABRUPT_REGIONAL_MOVEMENT"
        )
    ][["municipality_ibge_code", "municipality_name", "year", "stage"]]
    indigenous = panels["indigenous"]
    eligible_indigenous = sorted(
        set(
            indigenous.loc[
                indigenous["entity_scope"].eq("municipality")
                & _truthy(indigenous["municipal_card_eligible"]),
                "municipality_ibge_code",
            ].dropna()
        )
    )
    rural = panels["rural"]
    rural_groups = rural.drop_duplicates(
        ["entity_scope", "municipality_ibge_code", "year", "metric"]
    )
    integrated = panels["integrated"]
    integrated_zero = pd.to_numeric(
        integrated["integrated_eja_enrollments"], errors="raise"
    ).eq(0)
    return {
        "municipalityUniverse": {
            "expectedMunicipalityCount": 10,
            "observedMunicipalityCount": 10,
            "novaSantaRitaPresent": True,
            "ibgeIdentity": "text_7_digits",
        },
        "panels": {
            key: {"rows": len(panel), "columns": len(panel.columns)}
            for key, panel in panels.items()
        },
        "adult": {
            "intercensalShareChangeAllowedRows": int(
                _truthy(panels["adult"]["intercensal_share_change_allowed"]).sum()
            ),
            "cumulativeRowsStackable": int(
                (
                    _truthy(panels["adult"]["is_cumulative"])
                    & _truthy(
                        panels["adult"]["stacking_allowed_in_2022_exclusive_composition"]
                    )
                    & panels["adult"]["schooling_category"].eq("fundamental_completed_or_more")
                ).sum()
            ),
        },
        "distribution": {
            "objectCount": panels["distribution"]["distribution_object_id"].nunique(),
            "fundamentalRegionalDifferenceVsAdultPanel": 18401,
        },
        "history": {
            "abruptRegionalIntervals": _records(abrupt),
            "municipalConcentrations": _records(concentrations),
            "definitionMetadataAvailableRows": int(
                _truthy(history["definition_metadata_available"]).sum()
            ),
        },
        "integrated": {
            "observedZeroRows": int(integrated_zero.sum()),
            "structuralContextRows": int(
                integrated["period_context_status"].eq(
                    "STRUCTURAL_SERIES_CHANGE_REQUIRES_CONTEXT"
                ).sum()
            ),
            "administrativeDependencyMismatchCountQaOnly": 11,
        },
        "vulnerabilityIndigenousSplit": {
            "vulnerabilityRows": len(panels["vulnerability"]),
            "indigenousRows": len(indigenous),
            "eligibleIndigenousMunicipalityCodes": eligible_indigenous,
            "novaSantaRitaAutomaticCardEligible": bool(
                _truthy(
                    indigenous.loc[
                        indigenous["municipality_ibge_code"].eq(NOVA_SANTA_RITA_ID),
                        "municipal_card_eligible",
                    ]
                ).any()
            ),
        },
        "special": {
            "stageBreakdownAdditiveRows": int(
                _truthy(panels["special"]["stage_breakdown_additive"]).sum()
            ),
            "schoolMetricStackableRows": int(
                (
                    panels["special"]["metric_family"].eq("SCHOOLS")
                    & _truthy(panels["special"]["stacking_allowed"])
                ).sum()
            ),
        },
        "rural": {
            "exactGrainsWithValidatedBasicStageClosure": int(
                _truthy(rural_groups["stage_sum_closure_validated"]).sum()
            ),
            "schoolGrainsTreatedAsAdditive": int(
                (
                    rural_groups["metric"].eq("rural_schools")
                    & _truthy(rural_groups["stage_sum_closure_validated"])
                ).sum()
            ),
        },
        "pneLinks": {
            "rows": len(panels["links"]),
            "standaloneVisualRows": int(
                _truthy(panels["links"]["standalone_visual_module"]).sum()
            ),
            "teacherReferencesWithoutFacts": int(
                (
                    panels["links"]["analysis_id"].str.startswith("teacher_")
                    & ~_truthy(panels["links"]["materialized_fact_available"])
                ).sum()
            ),
        },
        "matrices": {
            "qaRows": len(qa_matrix),
            "canonicalRows": len(canonical_matrix),
            "opportunityRows": len(opportunities),
            "automaticApprovalTrueRows": int(
                _truthy(canonical_matrix["automatic_approval"]).sum()
                + _truthy(qa_matrix["automatic_approval"]).sum()
                + _truthy(opportunities["automatic_approval"]).sum()
            ),
            "nonEmptyScores": int(
                canonical_matrix["score"].notna().sum()
                + qa_matrix["score"].notna().sum()
                + opportunities["score"].notna().sum()
            ),
        },
        "dossier": {
            "technicalGroupCount": dossier["technicalGroupCount"],
            "compactMacroGroupCount": dossier["compactMacroGroupCount"],
            "technicalGroupsAreMandatoryCards": dossier["technicalGroupsAreMandatoryCards"],
        },
    }


def _errata_markdown(
    originals: Mapping[str, Mapping[str, Any]],
    frozen_job5gar: Mapping[str, Mapping[str, Any]],
    qa: Mapping[str, Any],
) -> str:
    lines = [
        "# ERRATA METODOLÓGICA — JOB 5G-B-R V7",
        "",
        "**Classificação:** DATA_LOGIC — correção semântica, contratos analíticos e QA.",
        "",
        "Este documento é técnico e interno. Não é narrativa pública, interface ou autorização de publicação.",
        "",
        "## Escopo preservado",
        "",
        "- `network_scope = total_all_dependencies`;",
        "- dependência administrativa apenas como dimensão de QA;",
        "- população residente, cadastro agregado, localização da escola, escola rural e estabelecimento de trabalho permanecem lentes separadas;",
        "- nenhuma pessoa foi vinculada entre fontes;",
        "- nenhum valor factual original foi recalculado;",
        "- nenhum artefato original do Job 5G-B ou congelado do Job 5G-A-R foi alterado.",
        "",
        "## Correções dirigidas",
        "",
        "1. Os controles antigos C1–C12 foram preservados como `QA1_JOB5GB`–`QA12_JOB5GB`; a matriz canônica foi reconstruída com os significados do Job 4B.",
        "2. Escolaridade adulta recebeu papéis cumulativos, derivados e exclusivos; mudanças 2010–2022 continuam apenas em contagem e categorias cumulativas não são empilhadas.",
        "3. Distribuição EJA 2022 foi separada em contratos fundamental e médio; a incompatibilidade regional de 18.401 pessoas permanece explícita.",
        "4. EJA histórica preserva os valores, fecha fundamental + médio = total e marca intervalos materiais sem inventar causa.",
        "5. EJA integrada/EPT separa total de referência e componentes; zeros são observados e a mudança estrutural de FIC médio desde 2023 exige contexto.",
        "6. Vulnerabilidade cadastral e educação indígena agora são objetos e painéis distintos; zero indígena não cria cartão municipal.",
        "7. Educação especial/AEE foi dividida em famílias de inclusão, etapas/modalidades e escolas, com não aditividade explícita.",
        "8. Educação rural recebeu fechamento por grão, sobreposição de escolas e profissional, e total apenas como referência.",
        "9. Vínculos PNE/PME são metadados associados às seções e nunca um módulo visual autônomo.",
        "10. O dossiê de Nova Santa Rita contém nove grupos técnicos e quatro macrogrupos compactos, sem obrigação de nove cartões.",
        "",
        "## Procedimento auditável para rupturas EJA",
        "",
        "Um intervalo de componente regional é sinalizado quando `abs(mudança anual) >= 500` e `abs(mudança anual %) >= 20`. Concentração municipal é sinalizada quando a mudança absoluta municipal alcança ao menos 50% da mudança líquida regional em módulo; compensações podem produzir percentual superior a 100%. Nenhum sinal atribui causa institucional.",
        "",
    ]
    for record in qa["history"]["abruptRegionalIntervals"]:
        year = int(record["year"])
        lines.append(
            f"- {record['stage']} {year - 1}→{year}: mudança regional "
            f"{record['year_over_year_absolute_change']:g} ({record['year_over_year_percent_change']:.6f}%)."
        )
    lines.extend(["", "Concentrações encontradas pelo mesmo procedimento:", ""])
    for record in qa["history"]["municipalConcentrations"]:
        year = int(record["year"])
        lines.append(f"- {record['municipality_name']}, {record['stage']} {year - 1}→{year}.")

    lines.extend(
        [
            "",
            "## Registro de preservação factual",
            "",
            "Os painéis corrigidos mantêm todas as colunas originais como prefixo, na mesma ordem, e acrescentam somente metadados semânticos. O painel misto de vulnerabilidade foi particionado sem perda de linhas: 121 linhas cadastrais + 132 linhas indígenas = 253 linhas originais.",
            "",
            "## Hashes dos 15 inputs originais do Job 5G-B",
            "",
            "| Artefato | Bytes | SHA-256 |",
            "|---|---:|---|",
        ]
    )
    for name in ORIGINAL_FILES:
        item = originals[name]
        lines.append(f"| `{name}` | {item['byteSize']} | `{item['sha256']}` |")
    lines.extend(
        [
            "",
            "## Controle do pacote congelado Job 5G-A-R",
            "",
            f"- artefatos verificados: {len(frozen_job5gar)};",
            f"- manifesto SHA-256: `{frozen_job5gar['MANIFEST_JOB5GAR.json']['sha256']}`;",
            "- reexecução do Job 5G-A-R: `false`.",
            "",
            "## Operações não realizadas",
            "",
            "Banco, rede, aquisição, `public/data`, frontend, compilador, build completo, publicação, Job 5G-C, Job 5H, Job 6, commit, push, tag, stash e reset não foram usados.",
            "",
        ]
    )
    return "\n".join(lines)


def _review_package(qa: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": "pacote-revisao-externa-job5gbr-v1",
        "jobId": "v7-job5gbr",
        "checkpoint": "post_external_judgment_job5gb",
        "inputDecision": "APPROVED_WITH_REQUIRED_SEMANTIC_AND_GOVERNANCE_CORRECTIONS",
        "finalState": FINAL_STATE,
        "externalReviewer": "GPT-5.6 Pro",
        "stopForExternalJudgment": True,
        "automaticApproval": False,
        "score": None,
        "canonicalInputs": {
            "DATA_MATERIALIZATION": "APPROVED",
            "CALCULATION_INTEGRITY": "APPROVED",
            "C1_C12_MATRIX": "CANONICALLY_REBUILT",
            "JOB_5GC": "QUEUED_AFTER_JOB_5GB_R",
            "JOB_5H": "NOT_AUTHORIZED",
            "JOB_6": "NOT_AUTHORIZED",
            "PILOT_GATE_11_V7": "BLOCKED",
        },
        "frontStates": {
            analysis_id: config["classification"] for analysis_id, config in FRONT_CONFIG.items()
        },
        "outputs": list(OUTPUT_FILES),
        "qa": qa,
        "generation": {
            "sourceJobArtifactsChanged": False,
            "job5garArtifactsChanged": False,
            "job5garReexecuted": False,
            "databaseUsed": False,
            "networkUsed": False,
            "externalAcquisitionUsed": False,
            "publicDataChanged": False,
            "frontendChanged": False,
            "compilerUsed": False,
            "fullBuildUsed": False,
            "published": False,
            "publicNarrativeProduced": False,
            "job5gcStarted": False,
            "job5hStarted": False,
            "job6Started": False,
            "deterministic": True,
            "transactional": True,
            "manifestLast": True,
        },
    }


def _artifact(path: Path, root: Path, frame: pd.DataFrame | None = None) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "byteSize": path.stat().st_size,
        "sha256": sha256_file(path),
        "rowCount": len(frame) if frame is not None else None,
        "columns": list(frame.columns) if frame is not None else None,
    }


def _manifest(
    staging: Path,
    originals: Mapping[str, Mapping[str, Any]],
    frozen_job5gar: Mapping[str, Mapping[str, Any]],
    qa: Mapping[str, Any],
    frames_by_output: Mapping[str, pd.DataFrame],
) -> dict[str, Any]:
    artifacts = [
        _artifact(staging / name, staging, frames_by_output.get(name))
        for name in OUTPUT_FILES[:-1]
    ]
    return {
        "schemaVersion": "manifest-job5gbr-v1",
        "jobId": "v7-job5gbr",
        "classification": "DATA_LOGIC",
        "domains": ["DATA_CORRECTION", "SEMANTIC_CONTRACT", "QA"],
        "objective": "Corrigir semanticamente e por composição o pacote de escolaridade adulta, EJA e públicos específicos do Job 5G-B.",
        "finalState": FINAL_STATE,
        "artifacts": artifacts,
        "originalArtifacts": [
            {"path": name, **originals[name]} for name in ORIGINAL_FILES
        ],
        "frozenJob5garArtifacts": [
            {"path": name, **frozen_job5gar[name]} for name in sorted(frozen_job5gar)
        ],
        "scope": {
            "state": "RS",
            "region": "Vale do Sinos",
            "municipalityCount": 10,
            "municipalityIdentity": "textual_ibge_code_7_digits",
            "networkScope": "total_all_dependencies",
            "administrativeDependencyIsAnalyticDimension": False,
            "administrativeDependencyIsQADimension": True,
            "publicNarrativeAllowed": False,
            "frontendAllowed": False,
            "publicationAllowed": False,
        },
        "formulasPreserved": [
            "adult_count_change_2010_2022",
            "within_stage_regional_distribution_shares_and_difference",
            "eja_total = fundamental + high_school",
            "integrated_total = technical_integrated + fic_fundamental + fic_high_school",
            "special_enrollments = common_class_enrollments + exclusive_class_enrollments",
        ],
        "formulasAltered": False,
        "semanticCorrections": [
            "adult_category_roles_and_count_only_guardrail",
            "eja_distribution_stage_specific_source_contracts",
            "eja_history_context_and_net_decomposition_roles",
            "eja_integrated_total_component_zero_and_period_roles",
            "vulnerability_indigenous_object_split",
            "special_metric_families_and_non_additivity",
            "rural_stage_overlap_and_exact_grain_closure",
            "pne_pme_internal_metadata_role",
            "qa_controls_renamed_and_canonical_c1_c12_rebuilt",
            "nova_santa_rita_nine_technical_groups_four_macro_groups",
        ],
        "generation": {
            "sourceJobArtifactsChanged": False,
            "job5garArtifactsChanged": False,
            "job5garReexecuted": False,
            "databaseUsed": False,
            "networkUsed": False,
            "externalAcquisitionUsed": False,
            "publicDataChanged": False,
            "frontendChanged": False,
            "compilerUsed": False,
            "fullBuildUsed": False,
            "published": False,
            "publicNarrativeProduced": False,
            "job5gcStarted": False,
            "job5hStarted": False,
            "job6Started": False,
            "deterministic": True,
            "transactional": True,
            "manifestLast": True,
            "partialPromotionAllowed": False,
        },
        "qa": qa,
        "summary": {
            "outputCount": len(OUTPUT_FILES),
            "manifestSelfExcludedFromArtifactHashes": True,
            "originalArtifactCount": len(originals),
            "frozenJob5garArtifactCount": len(frozen_job5gar),
            **{name: len(frame) for name, frame in frames_by_output.items()},
        },
        "automaticApproval": False,
        "score": None,
        "stopForExternalJudgment": True,
    }


def _validate_municipal_universe(panel: pd.DataFrame, label: str) -> None:
    municipality = panel[panel["entity_scope"].eq("municipality")]
    codes = set(municipality["municipality_ibge_code"].dropna())
    if codes != set(EXPECTED_CODES):
        raise ValueError(f"Universo municipal divergente em {label}: {sorted(codes)}")
    if not municipality["municipality_ibge_code"].str.fullmatch(r"\d{7}").all():
        raise ValueError(f"Código IBGE não textual de sete dígitos em {label}.")
    if NOVA_SANTA_RITA_ID not in codes:
        raise ValueError(f"Nova Santa Rita ausente em {label}.")


def _validate_outputs(root: Path, *, verify_inputs: bool = True) -> dict[str, Any]:
    if verify_inputs:
        _verify_originals()
        _verify_frozen_job5gar()
    actual = {path.name for path in root.iterdir() if path.is_file()}
    if actual != set(OUTPUT_FILES):
        raise ValueError(f"Conjunto de outputs divergente: {sorted(actual ^ set(OUTPUT_FILES))}")

    adult = _read_csv(root / OUTPUT_FILES[2])
    distribution = _read_csv(root / OUTPUT_FILES[3])
    history = _read_csv(root / OUTPUT_FILES[4])
    integrated = _read_csv(root / OUTPUT_FILES[5])
    vulnerability = _read_csv(root / OUTPUT_FILES[6])
    indigenous = _read_csv(root / OUTPUT_FILES[7])
    special = _read_csv(root / OUTPUT_FILES[8])
    rural = _read_csv(root / OUTPUT_FILES[9])
    links = _read_csv(root / OUTPUT_FILES[10])
    dossier = _load_json(root / OUTPUT_FILES[11])
    qa_matrix = _read_csv(root / OUTPUT_FILES[12])
    canonical = _read_csv(root / OUTPUT_FILES[13])
    opportunities = _read_csv(root / OUTPUT_FILES[14])
    review = _load_json(root / OUTPUT_FILES[16])
    manifest = _load_json(root / OUTPUT_FILES[17])
    dictionary = _load_json(root / OUTPUT_FILES[1])

    panels = {
        "adult": adult,
        "distribution": distribution,
        "history": history,
        "integrated": integrated,
        "vulnerability": vulnerability,
        "indigenous": indigenous,
        "special": special,
        "rural": rural,
        "links": links,
    }
    for label, panel in panels.items():
        if label != "links":
            _validate_municipal_universe(panel, label)

    _validate_unique(
        adult,
        ["entity_scope", "municipality_ibge_code", "year", "schooling_category"],
        "adult",
    )
    _validate_unique(
        distribution,
        ["entity_scope", "municipality_ibge_code", "year", "stage"],
        "distribution",
    )
    _validate_unique(
        history,
        ["entity_scope", "municipality_ibge_code", "year", "stage"],
        "history",
    )
    _validate_unique(
        integrated,
        ["entity_scope", "municipality_ibge_code", "year", "modality"],
        "integrated",
    )
    _validate_unique(
        vulnerability,
        ["entity_scope", "municipality_ibge_code", "reference_period", "metric"],
        "vulnerability",
    )
    _validate_unique(
        indigenous,
        ["entity_scope", "municipality_ibge_code", "reference_period", "metric"],
        "indigenous",
    )
    _validate_unique(
        special,
        ["entity_scope", "municipality_ibge_code", "year", "metric", "stage"],
        "special",
    )
    _validate_unique(
        rural,
        ["entity_scope", "municipality_ibge_code", "year", "metric", "stage"],
        "rural",
    )
    _validate_unique(links, ["analysis_id"], "pne_links")
    _validate_unique(qa_matrix, ["analysis_id", "qa_control_id"], "qa_matrix")
    _validate_unique(canonical, ["analysis_id", "criterion_id"], "canonical_matrix")
    _validate_unique(opportunities, ["analysis_id"], "opportunities")

    educational = [adult, distribution, history, integrated, indigenous, special, rural]
    for panel in educational:
        if not panel["network_scope"].eq("total_all_dependencies").all():
            raise ValueError("Evidência educacional fora da rede total.")
        if _truthy(panel["administrative_dependency_is_analytic_dimension"]).any():
            raise ValueError("Dependência administrativa usada como dimensão analítica.")
        if not _truthy(panel["administrative_dependency_is_QA_dimension"]).all():
            raise ValueError("Dependência administrativa não preservada como dimensão de QA.")

    original_adult = _read_csv(SOURCE_ROOT / "PAINEL_ESCOLARIDADE_ADULTA_2010_2022_V1.csv.gz")
    original_distribution = _read_csv(SOURCE_ROOT / "PAINEL_EJA_DISTRIBUICAO_2022_V1.csv.gz")
    original_history = _read_csv(SOURCE_ROOT / "PAINEL_EJA_HISTORICA_2014_2025_V1.csv.gz")
    original_integrated = _read_csv(SOURCE_ROOT / "PAINEL_EJA_INTEGRADA_EPT_V1.csv.gz")
    original_vulnerability = _read_csv(SOURCE_ROOT / "PAINEL_VULNERABILIDADE_EDUCACIONAL_V1.csv.gz")
    original_special = _read_csv(SOURCE_ROOT / "PAINEL_EDUCACAO_ESPECIAL_AEE_V1.csv.gz")
    original_rural = _read_csv(SOURCE_ROOT / "PAINEL_EDUCACAO_RURAL_TERRITORIO_V1.csv.gz")
    original_links = _read_csv(SOURCE_ROOT / "MATRIZ_VINCULOS_PNE_PME_JOB5GB_V1.csv.gz")
    _assert_original_columns_preserved(
        original_adult,
        adult,
        "adult",
        sort_columns=["entity_scope", "municipality_ibge_code", "year", "schooling_category"],
    )
    _assert_original_columns_preserved(
        original_distribution,
        distribution,
        "distribution",
        sort_columns=["entity_scope", "municipality_ibge_code", "year", "stage"],
    )
    _assert_original_columns_preserved(
        original_history,
        history,
        "history",
        sort_columns=["entity_scope", "municipality_ibge_code", "year", "stage"],
    )
    _assert_original_columns_preserved(
        original_integrated,
        integrated,
        "integrated",
        sort_columns=["entity_scope", "municipality_ibge_code", "year", "modality"],
    )
    _assert_original_columns_preserved(
        original_special,
        special,
        "special",
        sort_columns=["entity_scope", "municipality_ibge_code", "year", "metric", "stage"],
    )
    _assert_original_columns_preserved(
        original_rural,
        rural,
        "rural",
        sort_columns=["entity_scope", "municipality_ibge_code", "year", "metric", "stage"],
    )
    _assert_original_columns_preserved(
        original_links,
        links,
        "links",
        sort_columns=["analysis_id"],
    )
    split_recombined = pd.concat(
        [vulnerability[original_vulnerability.columns], indigenous[original_vulnerability.columns]],
        ignore_index=True,
    )
    _assert_original_columns_preserved(
        original_vulnerability,
        split_recombined,
        "vulnerability_indigenous_split",
        sort_columns=[
            "entity_scope",
            "context_domain",
            "municipality_ibge_code",
            "reference_period",
            "metric",
        ],
    )

    if adult["percentage_point_change_2010_2022"].notna().any():
        raise ValueError("Mudança intercensitária em pontos percentuais foi materializada sem denominador 2010.")
    if _truthy(adult["intercensal_share_change_allowed"]).any() or _truthy(
        adult["improvement_claim_allowed"]
    ).any():
        raise ValueError("Escolaridade adulta permitiu taxa intercensitária ou alegação de melhora.")
    cumulative = adult["schooling_category"].isin(
        ["fundamental_completed_or_more", "high_school_completed_or_more"]
    )
    forbidden_cumulative_stack = cumulative & adult["schooling_category"].eq(
        "fundamental_completed_or_more"
    ) & _truthy(adult["stacking_allowed_in_2022_exclusive_composition"])
    if forbidden_cumulative_stack.any():
        raise ValueError("Categoria cumulativa sobreposta entrou na composição empilhável.")
    if not adult["municipal_contribution_to_vale_change_percent_role"].eq(
        "INTERNAL_NET_CHANGE_DECOMPOSITION_ONLY"
    ).all():
        raise ValueError("Contribuição adulta não marcada como decomposição líquida interna.")

    fundamental = distribution[distribution["stage"].eq("fundamental")]
    high_school = distribution[distribution["stage"].eq("high_school")]
    if not fundamental["source_contract"].eq(
        "JOB2C_ESTIMATED_18PLUS_TOTAL_MINUS_CENSUS_COMPLETION"
    ).all() or not fundamental["adult_panel_compatibility"].eq(
        "DEFINITION_INCOMPATIBLE_POPULATION_TOTAL_SOURCE"
    ).all():
        raise ValueError("Contrato do fundamental EJA incorreto.")
    if not fundamental["regional_count_difference_vs_adult_panel"].eq(18401).all():
        raise ValueError("Diferença regional de 18.401 não preservada.")
    if not high_school["source_contract"].eq(
        "CENSUS_COMPLETION_COUNT_DIFFERENCE_2022"
    ).all() or not high_school["adult_panel_compatibility"].eq(
        "COMPARABLE_COUNT_DIFFERENCE"
    ).all():
        raise ValueError("Contrato do médio EJA incorreto.")
    if _truthy(distribution["cross_stage_combination_allowed"]).any():
        raise ValueError("Contratos fundamental e médio foram autorizados a combinar.")

    history_pivot = history.pivot_table(
        index=["entity_scope", "municipality_ibge_code", "municipality_name", "year"],
        columns="stage",
        values="eja_enrollments",
        aggfunc="first",
        dropna=False,
    ).dropna(how="all")
    history_closure = history_pivot["fundamental"] + history_pivot["high_school"]
    if not np.allclose(history_closure, history_pivot["total_context"], atol=0):
        raise ValueError("EJA histórica não fecha fundamental + médio = total.")
    if history.loc[history["stage"].eq("total_context"), "stacking_allowed"].astype(bool).any():
        raise ValueError("Total histórico foi autorizado a empilhar com componentes.")
    required_region = history[
        history["entity_scope"].eq("region")
        & history["stage"].eq("high_school")
        & history["year"].eq(2018)
    ]
    if not required_region["series_context_status"].eq(
        "ABRUPT_REGIONAL_MOVEMENT_REQUIRES_CONTEXT"
    ).all():
        raise ValueError("Movimento regional EJA médio 2017→2018 não foi contextualizado.")
    required_nh = history[
        history["municipality_ibge_code"].eq(NOVO_HAMBURGO_ID)
        & history["stage"].eq("high_school")
        & history["year"].eq(2018)
    ]
    if not required_nh["series_context_status"].eq(
        "MUNICIPAL_CONCENTRATION_IN_ABRUPT_REGIONAL_MOVEMENT"
    ).all():
        raise ValueError("Concentração de Novo Hamburgo em 2017→2018 não foi marcada.")
    if _truthy(history["definition_metadata_available"]).any() or _truthy(
        history["institutional_explanation_allowed"]
    ).any():
        raise ValueError("Metadado ou explicação institucional foram inventados na série histórica.")

    integrated_pivot = integrated.pivot_table(
        index=["entity_scope", "municipality_ibge_code", "municipality_name", "year"],
        columns="modality",
        values="integrated_eja_enrollments",
        aggfunc="first",
        dropna=False,
    ).dropna(how="all")
    integrated_components = (
        integrated_pivot["technical_integrated"]
        + integrated_pivot["fic_fundamental"]
        + integrated_pivot["fic_high_school"]
    )
    if not np.allclose(integrated_components, integrated_pivot["integrated_total"], atol=0):
        raise ValueError("Modalidades EJA/EPT não fecham o total integrado.")
    if integrated.loc[integrated["modality"].eq("integrated_total"), "stacking_allowed"].astype(bool).any():
        raise ValueError("Total integrado autorizado a empilhar com componentes.")
    zero = pd.to_numeric(integrated["integrated_eja_enrollments"], errors="raise").eq(0)
    if not integrated.loc[zero, "observation_semantics"].eq("observed_zero").all():
        raise ValueError("Zeros EJA/EPT não preservam semântica observed_zero.")
    structural = integrated["modality"].eq("fic_high_school") & integrated["year"].ge(2023)
    if not integrated.loc[structural, "period_context_status"].eq(
        "STRUCTURAL_SERIES_CHANGE_REQUIRES_CONTEXT"
    ).all():
        raise ValueError("Mudança estrutural FIC médio desde 2023 não foi marcada.")

    if set(vulnerability["object_id"]) != {"E_VULNERABILIDADE"} or set(
        indigenous["object_id"]
    ) != {"E2_EDUCACAO_INDIGENA"}:
        raise ValueError("Vulnerabilidade e educação indígena não estão separadas.")
    if len(vulnerability) + len(indigenous) != len(original_vulnerability):
        raise ValueError("Particionamento vulnerabilidade/indígena perdeu linhas.")
    if vulnerability["metric"].eq("educacao_indigena_cobertura_estimada_4_17").any():
        raise ValueError("Indicador indígena estimado permaneceu no painel de vulnerabilidade.")
    all_zero_municipalities = (
        indigenous[indigenous["entity_scope"].eq("municipality")]
        .groupby("municipality_ibge_code")["value"]
        .apply(lambda series: pd.to_numeric(series, errors="raise").eq(0).all())
    )
    for code in all_zero_municipalities[all_zero_municipalities].index:
        rows = indigenous[indigenous["municipality_ibge_code"].eq(code)]
        if _truthy(rows["municipal_card_eligible"]).any():
            raise ValueError(f"Zero indígena criou cartão municipal automático: {code}")

    inclusion = special[special["metric"].isin(
        ["special_enrollments", "common_class_enrollments", "exclusive_class_enrollments"]
    )]
    inclusion_pivot = inclusion.pivot_table(
        index=["entity_scope", "municipality_ibge_code", "municipality_name", "year", "stage"],
        columns="metric",
        values="value",
        aggfunc="first",
        dropna=False,
    ).dropna(how="all")
    if not np.allclose(
        inclusion_pivot["common_class_enrollments"] + inclusion_pivot["exclusive_class_enrollments"],
        inclusion_pivot["special_enrollments"],
        atol=0,
    ):
        raise ValueError("Common + exclusive não fecha special total.")
    if _truthy(special["stage_breakdown_additive"]).any():
        raise ValueError("Etapas/modalidades de educação especial foram tratadas como aditivas.")
    school_metrics = special["metric_family"].eq("SCHOOLS")
    if _truthy(special.loc[school_metrics, "stacking_allowed"]).any():
        raise ValueError("Métricas de escola/AEE foram autorizadas a empilhar.")

    school_rural = rural["metric"].eq("rural_schools")
    if _truthy(rural.loc[school_rural, "stage_sum_closure_validated"]).any():
        raise ValueError("Escolas rurais por etapa foram tratadas como aditivas.")
    total_rural = rural["stage"].eq("all")
    if not _truthy(rural.loc[total_rural, "total_context_only"]).all() or _truthy(
        rural.loc[total_rural, "stacking_allowed"]
    ).any():
        raise ValueError("Total rural não está restrito a referência não empilhável.")
    invalid_stack = _truthy(rural["stacking_allowed"]) & ~_truthy(
        rural["stage_sum_closure_validated"]
    )
    if invalid_stack.any():
        raise ValueError("Soma rural autorizada sem fechamento no grão exato.")

    if not links["page_role"].eq("INTERNAL_METADATA_LAYER").all() or _truthy(
        links["standalone_visual_module"]
    ).any():
        raise ValueError("Vínculos PNE/PME não estão restritos a metadados internos.")
    teacher = links["analysis_id"].str.startswith("teacher_")
    if int(teacher.sum()) != 4 or _truthy(links.loc[teacher, "materialized_fact_available"]).any() or _truthy(
        links.loc[teacher, "adds_concrete_decision"]
    ).any():
        raise ValueError("Quatro referências docentes sem fatos não foram preservadas.")
    indigenous_link = links["analysis_id"].eq("indigenous_education_observed")
    if _truthy(links.loc[indigenous_link, "materialized_value_available"]).any() or _truthy(
        links.loc[indigenous_link, "resident_denominator_combined"]
    ).any():
        raise ValueError("Vínculo indígena materializou valor legal ou denominador residente.")

    if set(qa_matrix["qa_control_id"]) != {f"QA{index}_JOB5GB" for index in range(1, 13)}:
        raise ValueError("Controles originais não foram renomeados para QA1–QA12_JOB5GB.")
    if len(qa_matrix) != 108 or len(canonical) != 108 or len(opportunities) != 9:
        raise ValueError("Matrizes não preservam 9 análises × 12 critérios.")
    if set(canonical["criterion_status"]) - CRITERION_STATUSES:
        raise ValueError("Estado inválido na matriz C1–C12 canônica.")
    for criterion_id, meaning in CANONICAL_CRITERIA.items():
        rows = canonical[canonical["criterion_id"].eq(criterion_id)]
        if not rows["criterion_meaning"].eq(meaning).all():
            raise ValueError(f"Significado canônico divergente em {criterion_id}.")
    if canonical.loc[canonical["criterion_id"].eq("C5"), "criterion_status"].eq("SUPPORTED").any():
        raise ValueError("C5 foi marcado como suportado sem estabilidade plenamente testada.")
    for frame in (qa_matrix, canonical, opportunities):
        if frame["score"].notna().any() or _truthy(frame["automatic_approval"]).any():
            raise ValueError("Score ou aprovação automática indevidos.")

    if dossier["technicalGroupCount"] != 9 or dossier["compactMacroGroupCount"] != 4:
        raise ValueError("Dossiê de Nova Santa Rita não contém 9 grupos técnicos e 4 macrogrupos.")
    if dossier["technicalGroupsAreMandatoryCards"]:
        raise ValueError("Nove grupos técnicos foram convertidos em cartões obrigatórios.")
    indigenous_group = next(
        group for group in dossier["technicalGroups"] if group["id"] == "educacao_indigena"
    )
    if indigenous_group["futureDisplayEligibility"] != "INELIGIBLE_NO_POSITIVE_MUNICIPAL_SCHOOL_FACT":
        raise ValueError("Zero indígena de Nova Santa Rita criou elegibilidade de cartão.")
    links_group = next(
        group for group in dossier["technicalGroups"] if group["id"] == "vinculos_pne_pme"
    )
    if links_group["standaloneVisualModule"]:
        raise ValueError("Dossiê criou módulo PNE/PME autônomo.")

    if dictionary["canonicalScope"]["network_scope"] != "total_all_dependencies":
        raise ValueError("Dicionário semântico diverge da rede total.")
    if review["finalState"] != FINAL_STATE or manifest["finalState"] != FINAL_STATE:
        raise ValueError("Estado final do pacote divergente.")
    if not review["stopForExternalJudgment"] or not manifest["stopForExternalJudgment"]:
        raise ValueError("Pacote não parou para julgamento externo.")
    for payload in (review, manifest):
        generation = payload["generation"]
        forbidden_true = [
            "sourceJobArtifactsChanged",
            "job5garArtifactsChanged",
            "job5garReexecuted",
            "databaseUsed",
            "networkUsed",
            "externalAcquisitionUsed",
            "publicDataChanged",
            "frontendChanged",
            "compilerUsed",
            "fullBuildUsed",
            "published",
            "publicNarrativeProduced",
            "job5gcStarted",
            "job5hStarted",
            "job6Started",
        ]
        if any(generation[key] for key in forbidden_true):
            raise ValueError("Manifesto registra operação proibida.")

    declared = {item["path"]: item for item in manifest["artifacts"]}
    if set(declared) != set(OUTPUT_FILES[:-1]):
        raise ValueError("Manifesto não declara exatamente os 17 artefatos anteriores.")
    for name, item in declared.items():
        path = root / name
        if path.stat().st_size != item["byteSize"] or sha256_file(path) != item["sha256"]:
            raise ValueError(f"Tamanho ou SHA-256 divergente: {name}")

    return {
        "finalState": FINAL_STATE,
        "promotion": "validated_existing",
        "outputCount": len(OUTPUT_FILES),
        "manifestSha256": sha256_file(root / "MANIFEST_JOB5GBR.json"),
        "originalArtifactCount": len(ORIGINAL_FILES),
        "frozenJob5garArtifactCount": 13,
        "canonicalMatrixRows": len(canonical),
        "qaMatrixRows": len(qa_matrix),
        "municipalityCount": 10,
        "novaSantaRitaPresent": True,
    }


def _promote(staging: Path, target: Path) -> str:
    target.parent.mkdir(parents=True, exist_ok=True)
    backup: Path | None = None
    if target.exists():
        backup = (target.parent / f".{target.name}.backup-{os.getpid()}").resolve()
        if backup.parent != target.parent.resolve():
            raise ValueError("Backup transacional fora da raiz esperada.")
        if backup.exists():
            raise FileExistsError(backup)
        target.rename(backup)
    try:
        staging.rename(target)
    except Exception:
        if backup is not None and backup.exists() and not target.exists():
            backup.rename(target)
        raise
    if backup is not None:
        if backup.parent != target.parent.resolve():
            raise ValueError("Remoção de backup fora da raiz esperada.")
        shutil.rmtree(backup)
        return "replaced_transactionally"
    return "created_transactionally"


def materialize(output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    output_root = output_root.resolve()
    public_root = (REPO_ROOT / "public" / "data").resolve()
    frontend_root = (REPO_ROOT / "src").resolve()
    protected_roots = {SOURCE_ROOT.resolve(), FROZEN_JOB5GAR_ROOT.resolve()}
    if output_root == public_root or public_root in output_root.parents:
        raise ValueError("Job 5G-B-R não pode escrever em public/data.")
    if output_root == frontend_root or frontend_root in output_root.parents:
        raise ValueError("Job 5G-B-R não pode escrever no frontend.")
    if output_root in protected_roots:
        raise ValueError("Job 5G-B-R não pode substituir artefatos de entrada.")

    originals_before = _verify_originals()
    frozen_before = _verify_frozen_job5gar()
    panels = {
        "adult": _adult_panel(),
        "distribution": _distribution_panel(),
        "history": _history_panel(),
        "integrated": _integrated_panel(),
    }
    panels["vulnerability"], panels["indigenous"] = _vulnerability_and_indigenous()
    panels["special"] = _special_panel()
    panels["rural"] = _rural_panel()
    panels["links"] = _pne_links()
    qa_matrix = _qa_matrix()
    canonical = _canonical_matrix()
    opportunities = _opportunity_matrix(canonical)
    dossier = _dossier(panels)
    qa = _qa_summary(panels, qa_matrix, canonical, opportunities, dossier)
    dictionary = _semantic_dictionary()

    frames_by_output = {
        OUTPUT_FILES[2]: panels["adult"],
        OUTPUT_FILES[3]: panels["distribution"],
        OUTPUT_FILES[4]: panels["history"],
        OUTPUT_FILES[5]: panels["integrated"],
        OUTPUT_FILES[6]: panels["vulnerability"],
        OUTPUT_FILES[7]: panels["indigenous"],
        OUTPUT_FILES[8]: panels["special"],
        OUTPUT_FILES[9]: panels["rural"],
        OUTPUT_FILES[10]: panels["links"],
        OUTPUT_FILES[12]: qa_matrix,
        OUTPUT_FILES[13]: canonical,
        OUTPUT_FILES[14]: opportunities,
    }

    output_root.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output_root.name}-staging-", dir=output_root.parent))
    try:
        (staging / OUTPUT_FILES[0]).write_text(
            _errata_markdown(originals_before, frozen_before, qa),
            encoding="utf-8",
            newline="\n",
        )
        _write_json(staging / OUTPUT_FILES[1], dictionary)
        for name, frame in frames_by_output.items():
            _write_csv_gzip(staging / name, frame)
        _write_json(staging / OUTPUT_FILES[11], dossier)
        (staging / OUTPUT_FILES[15]).write_text(
            _section_map(),
            encoding="utf-8",
            newline="\n",
        )
        _write_json(staging / OUTPUT_FILES[16], _review_package(qa))
        _write_json(
            staging / OUTPUT_FILES[17],
            _manifest(staging, originals_before, frozen_before, qa, frames_by_output),
        )
        _validate_outputs(staging)
        if originals_before != _verify_originals() or frozen_before != _verify_frozen_job5gar():
            raise ValueError("Entradas foram alteradas durante a geração.")
        promotion = _promote(staging, output_root)
        report = _validate_outputs(output_root)
        if originals_before != _verify_originals() or frozen_before != _verify_frozen_job5gar():
            raise ValueError("Entradas foram alteradas durante a promoção.")
        report["promotion"] = promotion
        return report
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def validate_existing_output(output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    return _validate_outputs(output_root.resolve())
