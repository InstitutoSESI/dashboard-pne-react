#!/usr/bin/env python3
"""Incorpora programas e titulados da pós-graduação stricto sensu de 2024."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from hashlib import sha256
from pathlib import Path
import re
import sys
import tempfile

import requests


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.pne_macro_ingestion import (  # noqa: E402
    DATA_ROOT,
    MANIFEST_SCHEMA,
    canonical_json_bytes,
    load_municipality_universe,
    normalized_snapshot,
    normalize_name,
    raw_file_entry,
    write_source_snapshot,
)


SOURCE_ID = "capes_sucupira_2024"
PROGRAMS_URL = (
    "https://dadosabertos.capes.gov.br/dataset/"
    "414275c0-2056-4a12-b1a6-b525b74850d5/resource/"
    "76ccbd76-7f3a-40c3-a4dc-7d6f65858db8/download/"
    "br-capes-colsucup-prog-2024-2025-12-01.csv"
)
PROGRAMS_METADATA_URL = (
    "https://dadosabertos.capes.gov.br/dataset/"
    "414275c0-2056-4a12-b1a6-b525b74850d5/resource/"
    "88bc19de-d2ce-4ffa-bdcd-776f7c23d6f5/download/"
    "metadados_programas_pos_graduacao_2021_2024.pdf"
)
STUDENTS_URL = (
    "https://dadosabertos.capes.gov.br/dataset/"
    "c6bd4dca-a0fb-499a-9f7f-df0740563333/resource/"
    "8afca354-18d5-4b6c-9158-2695fb26ad86/download/"
    "br-capes-colsucup-discentes-2024-2025-12-01.csv"
)
STUDENTS_METADATA_URL = (
    "https://dadosabertos.capes.gov.br/dataset/"
    "c6bd4dca-a0fb-499a-9f7f-df0740563333/resource/"
    "70633e5c-5294-4cd4-abea-79341c63e406/download/"
    "metadados_discentes_pos_graduacao_2021_2024.pdf"
)
SOURCE_PAGE = "https://dadosabertos.capes.gov.br/"
DESTINATION = DATA_ROOT / "capes_2024"


def _download(url: str, destination: Path) -> Path:
    with requests.get(url, stream=True, timeout=240) as response:
        response.raise_for_status()
        with destination.open("wb") as target:
            for chunk in response.iter_content(1024 * 1024):
                if chunk:
                    target.write(chunk)
    return destination


def _municipality_id(
    name: object,
    ids_by_name: dict[str, str],
    unmatched: Counter[str],
) -> str | None:
    normalized = normalize_name(name)
    municipality_id = ids_by_name.get(normalized)
    if municipality_id is None:
        unmatched[str(name or "")] += 1
    return municipality_id


def parse_capes(
    programs_path: Path,
    students_path: Path,
) -> tuple[dict, dict]:
    municipality_names, ids_by_name = load_municipality_universe()
    headquarter_programs: dict[str, set[str]] = defaultdict(set)
    student_linked_programs: dict[str, set[str]] = defaultdict(set)
    unmatched_programs: Counter[str] = Counter()
    program_statuses: Counter[str] = Counter()
    programs_by_code: dict[str, dict[str, str]] = {}
    with programs_path.open("r", encoding="latin1", errors="strict", newline="") as source:
        reader = csv.DictReader(source, delimiter=";")
        required = {
            "AN_BASE",
            "SG_UF_PROGRAMA",
            "NM_MUNICIPIO_PROGRAMA_IES",
            "CD_PROGRAMA_IES",
            "NM_GRAU_PROGRAMA",
            "NM_MODALIDADE_PROGRAMA",
            "NM_PROGRAMA_IES",
            "IN_REDE",
            "SG_ENTIDADE_ENSINO",
            "NM_ENTIDADE_ENSINO",
            "SG_ENTIDADE_ENSINO_REDE",
            "DS_SITUACAO_PROGRAMA",
        }
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(
                f"Programas CAPES sem colunas: {sorted(required - set(reader.fieldnames or []))}"
            )
        for row in reader:
            if str(row["AN_BASE"]) != "2024":
                continue
            program_id = str(row["CD_PROGRAMA_IES"]).strip()
            if not program_id:
                raise ValueError("Programa CAPES sem CD_PROGRAMA_IES.")
            if program_id in programs_by_code:
                raise ValueError(f"Programa CAPES duplicado: {program_id!r}.")
            programs_by_code[program_id] = dict(row)
            if row["SG_UF_PROGRAMA"] != "RS":
                continue
            status = normalize_name(row["DS_SITUACAO_PROGRAMA"])
            program_statuses[status] += 1
            if status not in {"em funcionamento", "em desativacao"}:
                continue
            municipality_id = _municipality_id(
                row["NM_MUNICIPIO_PROGRAMA_IES"],
                ids_by_name,
                unmatched_programs,
            )
            if municipality_id is None:
                continue
            headquarter_programs[municipality_id].add(program_id)

    titles: dict[str, Counter[str]] = defaultdict(Counter)
    student_rows: Counter[str] = Counter()
    unmatched_students: Counter[str] = Counter()
    student_statuses: Counter[str] = Counter()
    reconciliation: dict[tuple[str, str], dict] = {}
    title_rows = 0
    with students_path.open("r", encoding="latin1", errors="strict", newline="") as source:
        reader = csv.DictReader(source, delimiter=";")
        required = {
            "AN_BASE",
            "SG_UF_PROGRAMA",
            "NM_MUNICIPIO_PROGRAMA_IES",
            "CD_PROGRAMA_IES",
            "ID_PESSOA",
            "NM_GRAU_PROGRAMA",
            "DS_GRAU_ACADEMICO_DISCENTE",
            "NM_SITUACAO_DISCENTE",
            "DT_SITUACAO_DISCENTE",
            "SG_ENTIDADE_ENSINO",
            "NM_ENTIDADE_ENSINO",
        }
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(
                f"Discentes CAPES sem colunas: {sorted(required - set(reader.fieldnames or []))}"
            )
        seen_title_keys: set[tuple[str, str, str, str]] = set()
        for row in reader:
            if row["SG_UF_PROGRAMA"] != "RS" or str(row["AN_BASE"]) != "2024":
                continue
            program_id = str(row["CD_PROGRAMA_IES"] or "").strip()
            program = programs_by_code.get(program_id)
            if program is None:
                raise ValueError(
                    f"Discente CAPES referencia programa inexistente: {program_id!r}."
                )
            municipality_id = _municipality_id(
                row["NM_MUNICIPIO_PROGRAMA_IES"],
                ids_by_name,
                unmatched_students,
            )
            if municipality_id is None:
                continue
            student_rows[municipality_id] += 1
            student_linked_programs[municipality_id].add(program_id)
            status = normalize_name(row["NM_SITUACAO_DISCENTE"])
            student_statuses[status] += 1
            program_location = (
                str(program["SG_UF_PROGRAMA"]).strip(),
                normalize_name(program["NM_MUNICIPIO_PROGRAMA_IES"]),
            )
            student_location = (
                "RS",
                normalize_name(row["NM_MUNICIPIO_PROGRAMA_IES"]),
            )
            if program_location != student_location:
                network = normalize_name(program["IN_REDE"])
                associated = {
                    normalize_name(value)
                    for value in str(program["SG_ENTIDADE_ENSINO_REDE"] or "").split(";")
                    if normalize_name(value)
                }
                associated.add(normalize_name(program["SG_ENTIDADE_ENSINO"]))
                participant = normalize_name(row["SG_ENTIDADE_ENSINO"])
                if network != "sim" or participant not in associated:
                    raise ValueError(
                        "Territorialidade CAPES divergente sem vínculo oficial "
                        f"de rede: programa={program_id!r}, "
                        f"IES={row['SG_ENTIDADE_ENSINO']!r}."
                    )
                reconciliation_key = (program_id, municipality_id)
                entry = reconciliation.setdefault(
                    reconciliation_key,
                    {
                        "programCode": program_id,
                        "programHeadquarterMunicipality": (
                            f"{program['NM_MUNICIPIO_PROGRAMA_IES']}/"
                            f"{program['SG_UF_PROGRAMA']}"
                        ),
                        "studentLinkedInstitutionMunicipality": (
                            f"{row['NM_MUNICIPIO_PROGRAMA_IES']}/RS"
                        ),
                        "programMode": str(program["NM_MODALIDADE_PROGRAMA"]),
                        "programDegree": str(program["NM_GRAU_PROGRAMA"]),
                        "coordinatorInstitution": str(
                            program["NM_ENTIDADE_ENSINO"]
                        ),
                        "participantInstitutions": set(),
                        "studentRows": 0,
                        "enrolled": 0,
                        "mastersAwarded": 0,
                        "doctoratesAwarded": 0,
                        "territorialDecision": (
                            "student_linked_participant_institution_municipality"
                        ),
                        "officialJustification": (
                            "O dicionário de discentes define o campo municipal "
                            "como o município da IES à qual o discente está "
                            "vinculado no programa; a IES consta entre as "
                            "instituições da rede oficial do programa."
                        ),
                    },
                )
                entry["participantInstitutions"].add(
                    f"{row['SG_ENTIDADE_ENSINO']} — {row['NM_ENTIDADE_ENSINO']}"
                )
                entry["studentRows"] += 1
                if status == "matriculado":
                    entry["enrolled"] += 1
            if status != "titulado":
                continue
            date = str(row["DT_SITUACAO_DISCENTE"] or "")
            if not re.search(r"(^|\D)2024(\D|$)", date):
                continue
            degree = normalize_name(row["DS_GRAU_ACADEMICO_DISCENTE"])
            title_key = (
                str(row["ID_PESSOA"] or "").strip(),
                program_id,
                degree,
                date,
            )
            if not title_key[0] or title_key in seen_title_keys:
                raise ValueError(f"Titulação CAPES ausente ou duplicada: {title_key!r}.")
            seen_title_keys.add(title_key)
            if "doutor" in degree:
                titles[municipality_id]["doctorate"] += 1
                if program_location != student_location:
                    reconciliation[(program_id, municipality_id)][
                        "doctoratesAwarded"
                    ] += 1
            elif "mestr" in degree:
                titles[municipality_id]["master"] += 1
                if program_location != student_location:
                    reconciliation[(program_id, municipality_id)][
                        "mastersAwarded"
                    ] += 1
            else:
                titles[municipality_id]["other_degree"] += 1
            title_rows += 1

    if unmatched_programs or unmatched_students:
        raise ValueError(
            "Municípios CAPES/RS não conciliados: "
            f"programas={dict(unmatched_programs)}, "
            f"discentes={dict(unmatched_students)}"
        )
    if sum(counter["other_degree"] for counter in titles.values()):
        raise ValueError("Titulados CAPES com grau não classificado.")

    local_programs = {
        municipality_id: (
            headquarter_programs[municipality_id]
            | student_linked_programs[municipality_id]
        )
        for municipality_id in municipality_names
    }
    active_programs = {
        municipality_id: {
            program_id
            for program_id in local_programs[municipality_id]
            if normalize_name(programs_by_code[program_id]["DS_SITUACAO_PROGRAMA"])
            == "em funcionamento"
        }
        for municipality_id in municipality_names
    }
    program_degrees = {
        municipality_id: Counter(
            normalize_name(programs_by_code[program_id]["NM_GRAU_PROGRAMA"])
            or "unknown"
            for program_id in local_programs[municipality_id]
        )
        for municipality_id in municipality_names
    }
    records = {
        municipality_id: {
            "municipalityId": municipality_id,
            "municipalityName": municipality_names[municipality_id],
            "year": 2024,
            "headquarterProgramCount": len(headquarter_programs[municipality_id]),
            "studentLinkedProgramCount": len(
                student_linked_programs[municipality_id]
            ),
            "localProgramCount": len(local_programs[municipality_id]),
            "activeProgramCount": len(active_programs[municipality_id]),
            "studentRowCount": student_rows[municipality_id],
            "mastersAwarded": titles[municipality_id]["master"],
            "doctoratesAwarded": titles[municipality_id]["doctorate"],
            "programDegreeRows": dict(sorted(program_degrees[municipality_id].items())),
            "sourceCoverageStatus": "complete",
            "territorialityStatus": "homologated",
            "titleDataStatus": "available",
        }
        for municipality_id in municipality_names
    }
    normalized = normalized_snapshot(
        source_id=SOURCE_ID,
        edition="Coleta CAPES/Sucupira 2024",
        records=records,
        municipality_names=municipality_names,
    )
    municipal_reconciliation = []
    for municipality_id, record in sorted(records.items()):
        titles_total = (
            record["mastersAwarded"] + record["doctoratesAwarded"]
        )
        previous_status = (
            "available"
            if record["headquarterProgramCount"] > 0
            else "not_applicable"
        )
        corrected_status = (
            "available"
            if titles_total > 0 or record["localProgramCount"] > 0
            else "not_applicable"
        )
        if previous_status != corrected_status:
            reason = (
                "positive_titles_from_linked_network_institution_were_"
                "blocked_by_headquarter_guard"
            )
        elif (
            record["headquarterProgramCount"]
            != record["localProgramCount"]
        ):
            reason = (
                "network_participant_offer_reconciled_without_value_or_"
                "status_change"
            )
        else:
            reason = "unchanged"
        municipal_reconciliation.append(
            {
                "municipalityId": municipality_id,
                "municipalityName": record["municipalityName"],
                "headquarterProgramCount": record["headquarterProgramCount"],
                "studentLinkedProgramCount": record[
                    "studentLinkedProgramCount"
                ],
                "localProgramCount": record["localProgramCount"],
                "studentRowCount": record["studentRowCount"],
                "mastersAwarded": record["mastersAwarded"],
                "doctoratesAwarded": record["doctoratesAwarded"],
                "previousDataStatus": previous_status,
                "correctedDataStatus": corrected_status,
                "previousValue": (
                    titles_total if previous_status == "available" else None
                ),
                "correctedValue": (
                    titles_total if corrected_status == "available" else None
                ),
                "changeReason": reason,
            }
        )
    audit = {
        "coverage": {
            "municipalityCount": len(records),
            "municipalitiesWithHeadquarterProgram": sum(
                record["headquarterProgramCount"] > 0 for record in records.values()
            ),
            "municipalitiesWithStudentLinkedProgram": sum(
                record["studentLinkedProgramCount"] > 0 for record in records.values()
            ),
            "municipalitiesWithLocalProgram": sum(
                record["localProgramCount"] > 0 for record in records.values()
            ),
            "municipalitiesWithStudentRows": sum(
                record["studentRowCount"] > 0 for record in records.values()
            ),
            "municipalitiesWithTitles": sum(
                record["mastersAwarded"] + record["doctoratesAwarded"] > 0
                for record in records.values()
            ),
            "headquarterProgramCount": sum(
                record["headquarterProgramCount"] for record in records.values()
            ),
            "studentLinkedProgramCount": sum(
                record["studentLinkedProgramCount"] for record in records.values()
            ),
            "localProgramCount": sum(
                record["localProgramCount"] for record in records.values()
            ),
            "activeProgramCount": sum(
                record["activeProgramCount"] for record in records.values()
            ),
            "masterTitles": sum(
                record["mastersAwarded"] for record in records.values()
            ),
            "doctorateTitles": sum(
                record["doctoratesAwarded"] for record in records.values()
            ),
        },
        "programStatuses": dict(sorted(program_statuses.items())),
        "studentStatuses": dict(sorted(student_statuses.items())),
        "titleRows": title_rows,
        "stateAggregation": {
            "municipalTitleSum": sum(
                record["mastersAwarded"] + record["doctoratesAwarded"]
                for record in records.values()
            ),
            "uniqueTitleRows": len(seen_title_keys),
            "duplicateTitleRows": 0,
            "publishable": len(seen_title_keys) == title_rows,
            "rule": (
                "somar uma única vez cada pessoa, programa, grau e data, "
                "territorializados em uma única IES vinculada"
            ),
        },
        "municipalReconciliation": municipal_reconciliation,
        "territorialReconciliation": [
            {
                **entry,
                "participantInstitutions": sorted(entry["participantInstitutions"]),
            }
            for _, entry in sorted(reconciliation.items())
        ],
    }
    return normalized, audit


def materialize(
    programs_path: Path,
    programs_metadata_path: Path,
    students_path: Path,
    students_metadata_path: Path,
) -> dict:
    normalized, audit = parse_capes(programs_path, students_path)
    raw_specs = [
        ("programs2024", programs_path, PROGRAMS_URL),
        ("programsDictionary", programs_metadata_path, PROGRAMS_METADATA_URL),
        ("students2024", students_path, STUDENTS_URL),
        ("studentsDictionary", students_metadata_path, STUDENTS_METADATA_URL),
    ]
    manifest = {
        "schemaVersion": MANIFEST_SCHEMA,
        "sourceId": SOURCE_ID,
        "sourceTitle": "Dados Abertos CAPES — Plataforma Sucupira",
        "organization": "Coordenação de Aperfeiçoamento de Pessoal de Nível Superior",
        "edition": "2024; arquivos publicados em 01/12/2025",
        "sourcePageUrl": SOURCE_PAGE,
        "rawFiles": [
            raw_file_entry(logical_name=name, path=path, official_url=url)
            for name, path, url in raw_specs
        ],
        "dictionary": {
            "programHeadquarterMunicipality": {
                "field": "NM_MUNICIPIO_PROGRAMA_IES",
                "file": "programs2024",
                "officialMeaning": "município sede do programa de pós-graduação",
            },
            "studentLinkedInstitutionMunicipality": {
                "field": "NM_MUNICIPIO_PROGRAMA_IES",
                "file": "students2024",
                "officialMeaning": (
                    "município da IES à qual o discente está vinculado "
                    "no programa de pós-graduação"
                ),
            },
            "networkIndicator": "IN_REDE",
            "networkInstitutions": "SG_ENTIDADE_ENSINO_REDE",
            "studentLinkedInstitution": "SG_ENTIDADE_ENSINO",
            "programId": "CD_PROGRAMA_IES",
            "programStatus": {
                "field": "DS_SITUACAO_PROGRAMA",
                "officialMeaning": "situação do programa no ano de referência",
            },
            "programDegree": "NM_GRAU_PROGRAMA",
            "studentDegree": "DS_GRAU_ACADEMICO_DISCENTE",
            "studentStatus": {
                "field": "NM_SITUACAO_DISCENTE",
                "officialMeaning": (
                    "situação do discente em suas atividades: abandonou, "
                    "desligado, matriculado, mudança de nível ou titulado"
                ),
            },
            "statusDate": {
                "field": "DT_SITUACAO_DISCENTE",
                "officialMeaning": (
                    "data da situação do discente; o ano de titulação é "
                    "derivado desta data quando a situação é TITULADO"
                ),
            },
            "coordinatorInstitution": {
                "field": "NM_ENTIDADE_ENSINO",
                "file": "programs2024",
                "officialMeaning": (
                    "IES do programa; em programa em rede, representa a "
                    "instituição principal"
                ),
            },
            "participantInstitutions": {
                "field": "SG_ENTIDADE_ENSINO_REDE",
                "file": "programs2024",
                "officialMeaning": (
                    "IES associadas à instituição principal quando o programa "
                    "pertence a uma rede"
                ),
            },
        },
        "coverage": audit["coverage"],
        "normalization": {
            "municipalityKey": (
                "nome oficial do município da sede ou da IES vinculada ao "
                "discente, conciliado exclusivamente ao código IBGE RS"
            ),
            "localProgramEvidence": (
                "união de programa com sede municipal e programa com discente "
                "vinculado a IES participante situada no município"
            ),
            "networkReconciliation": (
                "divergência municipal aceita somente quando IN_REDE=SIM e a "
                "IES do discente consta como principal ou associada"
            ),
            "titleStatus": "TITULADO com DT_SITUACAO_DISCENTE em 2024",
            "normalizedSha256": sha256(canonical_json_bytes(normalized)).hexdigest(),
        },
        "absencePolicy": {
            "positiveTitles": "available; localProgramCount não pode anulá-los",
            "confirmedLocalOfferWithNoTitles": "observed_zero",
            "noLocalOfferAndNoStudentRow": "not_applicable",
            "incompleteOrInconclusive": "unavailable",
            "suppressed": "suppressed; never reconstructed",
        },
        "duplicatePolicy": (
            "programa municipal duplicado ou titulação repetida por pessoa, programa, "
            "grau e data invalida a carga"
        ),
        "territoriality": (
            "município da sede do programa ou da IES participante à qual o "
            "discente está vinculado; não equivale à residência do titulado"
        ),
        "audit": {
            "programStatuses": audit["programStatuses"],
            "studentStatuses": audit["studentStatuses"],
            "titleRows": audit["titleRows"],
            "stateAggregation": audit["stateAggregation"],
            "municipalReconciliation": audit["municipalReconciliation"],
            "territorialReconciliation": audit["territorialReconciliation"],
        },
        "status": "approved_complementary",
    }
    write_source_snapshot(
        destination=DESTINATION,
        raw_files={path.name: path for _, path, _ in raw_specs},
        normalized=normalized,
        manifest=manifest,
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--programs-file", type=Path)
    parser.add_argument("--programs-metadata-file", type=Path)
    parser.add_argument("--students-file", type=Path)
    parser.add_argument("--students-metadata-file", type=Path)
    args = parser.parse_args()
    supplied = (
        args.programs_file,
        args.programs_metadata_file,
        args.students_file,
        args.students_metadata_file,
    )
    if any(supplied) and not all(supplied):
        parser.error("Informe os quatro arquivos locais ou nenhum.")
    with tempfile.TemporaryDirectory(
        prefix="pne-capes-",
        ignore_cleanup_errors=True,
    ) as temporary:
        root = Path(temporary)
        files = supplied if all(supplied) else (
            _download(PROGRAMS_URL, root / "programs_2024.csv"),
            _download(PROGRAMS_METADATA_URL, root / "programs_metadata.pdf"),
            _download(STUDENTS_URL, root / "students_2024.csv"),
            _download(STUDENTS_METADATA_URL, root / "students_metadata.pdf"),
        )
        manifest = materialize(*files)
    print(canonical_json_bytes(manifest).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
