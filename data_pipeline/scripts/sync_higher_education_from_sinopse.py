"""Audita ou materializa os dados municipais da Educacao Superior."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.config import (  # noqa: E402
    EDUCATION_DATA_DIR,
    HIGHER_EDUCATION_SOURCE_DIR,
)
from src.higher_education import (  # noqa: E402
    SUPPORTED_YEARS,
    audit_summary,
    parse_higher_education_sources,
    write_audit_outputs,
)
from src.higher_education_materialization import (  # noqa: E402
    materialize_higher_education,
)
from src.municipality_registry import (  # noqa: E402
    MunicipalityRegistryError,
    load_municipality_registry,
)
from src.state_config import (  # noqa: E402
    DEFAULT_STATE_CODE,
    StateConfigError,
    load_state_config,
    normalize_state_code,
)


def _parse_years(value: str) -> tuple[int, ...]:
    years = tuple(sorted({int(item.strip()) for item in value.split(",") if item.strip()}))
    unsupported = sorted(set(years) - set(SUPPORTED_YEARS))
    if not years or unsupported:
        raise argparse.ArgumentTypeError(
            f"Anos invalidos: {unsupported or value!r}; "
            f"permitidos: {SUPPORTED_YEARS}."
        )
    return years


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Valida as sete tabelas aprovadas da Sinopse da Educacao Superior "
            "e grava somente artefatos temporarios de auditoria."
        )
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=HIGHER_EDUCATION_SOURCE_DIR,
        help=(
            "Diretorio das Sinopses. Padrao: HIGHER_EDUCATION_SOURCE_DIR ou "
            "SESI_DB_DIR/data/sinopse_educacao_superior."
        ),
    )
    parser.add_argument(
        "--years",
        type=_parse_years,
        default=SUPPORTED_YEARS,
        help="Anos separados por virgula. Padrao: 2018,...,2024.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help=(
            "Diretorio de auditoria. Quando omitido, cria um diretorio "
            "temporario fora de public/data."
        ),
    )
    parser.add_argument(
        "--materialize",
        action="store_true",
        help=(
            "Executa a ESUP-2 com staging, validacao, verificacao de "
            "determinismo e substituicao atomica."
        ),
    )
    parser.add_argument(
        "--public-output-dir",
        type=Path,
        default=EDUCATION_DATA_DIR / "superior",
        help="Diretorio publico exclusivo da Educacao Superior.",
    )
    parser.add_argument(
        "--state",
        default=DEFAULT_STATE_CODE,
        help=f"Código estadual configurado (padrão: {DEFAULT_STATE_CODE}).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        state_code = normalize_state_code(args.state)
        state_config = load_state_config(state_code)
        registry = load_municipality_registry(state_config)
    except (FileNotFoundError, StateConfigError, MunicipalityRegistryError) as exc:
        print(f"Configuração estadual inválida: {exc}", file=sys.stderr)
        return 2

    audit = parse_higher_education_sources(
        source_dir=args.source_dir,
        state_config=state_config,
        registry=registry,
        years=args.years,
    )
    if args.materialize:
        if tuple(args.years) != SUPPORTED_YEARS:
            raise ValueError(
                "A ESUP-2 exige a serie integral de 2018 a 2024."
            )
        result = materialize_higher_education(
            audit,
            municipality_universe=registry.names_by_id,
            output_directory=args.public_output_dir,
        )
        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    output_dir = write_audit_outputs(audit, args.output_dir)
    print(
        json.dumps(
            audit_summary(audit, output_dir),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
