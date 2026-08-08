from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from types import MappingProxyType, SimpleNamespace
from unittest.mock import Mock

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = REPO_ROOT / "data_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from src.education_municipality_routes import (  # noqa: E402
    EDUCATION_MUNICIPALITY_ROUTE_COMPATIBILITY_SCHEMA_VERSION,
    EducationMunicipalityRouteCompatibility,
    build_education_municipalities_index_payload,
    load_education_municipality_route_compatibility,
)
from src.education_transactional_publication import (  # noqa: E402
    EDUCATION_BLOCKS,
    EDUCATION_INDEX_BLOCKS,
    EducationPromotionError,
    EducationPublicationError,
    EducationStagingError,
    EducationValidationError,
    iter_managed_education_public_files,
    promote_education_staging,
    publish_education_transactionally,
    render_education_json,
    validate_education_staging,
)
from src.municipality_registry import load_municipality_registry  # noqa: E402
from src.state_config import StateConfig, load_state_config  # noqa: E402


def _load_script(name: str):
    module_name = f"education_publication_{name}"
    spec = importlib.util.spec_from_file_location(
        module_name,
        PIPELINE_ROOT / "scripts" / f"{name}.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Não foi possível carregar {name}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


EXPORTER = _load_script("export_education_indicators")
UPDATE = _load_script("update_static_data")


@pytest.fixture
def contract(tmp_path: Path):
    records = (
        ("4300034", "Aceguá", "acegua"),
        ("4300059", "Água Santa", "agua-santa"),
    )
    state = StateConfig(
        schema_version="state-config-v1",
        state_code="RS",
        state_name="Rio Grande do Sul",
        municipality_ibge_prefix="43",
        expected_municipality_count=len(records),
        locale="pt-BR",
    )
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "schemaVersion": "municipality-registry-v1",
                "stateCode": "RS",
                "municipalityCount": len(records),
                "municipalities": [
                    {"ibgeCode": code, "name": name, "slug": slug}
                    for code, name, slug in records
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    registry = load_municipality_registry(state, registry_path=registry_path)
    compatibility = EducationMunicipalityRouteCompatibility(
        schema_version=(
            EDUCATION_MUNICIPALITY_ROUTE_COMPATIBILITY_SCHEMA_VERSION
        ),
        state_code="RS",
        slug_overrides=MappingProxyType({"4300034": "acegua-legado"}),
    )
    public_root = tmp_path / "public" / "data" / "educacao"
    public_root.mkdir(parents=True)
    return SimpleNamespace(
        state=state,
        registry=registry,
        compatibility=compatibility,
        public_root=public_root,
    )


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(render_education_json(payload))


def _municipal_document(record, *, updated_at: str, marker: str) -> dict:
    return {
        "id_municipio": record.ibge_code,
        "municipio": record.name,
        "updated_at": updated_at,
        "fontes": [],
        "avisos": [],
        "blocos": {
            block: {
                "series": {"fixture": [{"ano": 2025, "valor": marker}]},
                "campos_indisponiveis": [],
            }
            for block in EDUCATION_BLOCKS
        },
    }


def _education_index(registry, *, updated_at: str) -> dict:
    return {
        "updated_at": updated_at,
        "anos_disponiveis": {},
        "total_municipios": registry.municipality_count,
        "fontes": [],
        "avisos_metodologicos": [],
        "blocos_disponiveis": list(EDUCATION_INDEX_BLOCKS),
        "campos_indisponiveis": [],
        "caminhos": {
            "municipios_index": "educacao/municipios_index.json",
            "municipios": "educacao/municipios/{id_municipio}.json",
        },
        "arquivos_gerados": {
            "municipios": registry.municipality_count,
        },
    }


def _write_complete_tree(
    root: Path,
    registry,
    compatibility,
    *,
    updated_at: str = "2026-08-02",
    marker: str = "new",
) -> None:
    _write_json(root / "index.json", _education_index(
        registry,
        updated_at=updated_at,
    ))
    _write_json(
        root / "municipios_index.json",
        build_education_municipalities_index_payload(registry, compatibility),
    )
    for record in registry.ordered_records:
        _write_json(
            root / "municipios" / f"{record.ibge_code}.json",
            _municipal_document(
                record,
                updated_at=updated_at,
                marker=marker,
            ),
        )


def _snapshot(root: Path) -> dict[str, tuple[bytes, int]]:
    return {
        path.relative_to(root).as_posix(): (
            path.read_bytes(),
            path.stat().st_mtime_ns,
        )
        for path in sorted(item for item in root.rglob("*") if item.is_file())
    }


def _materializer(contract, *, updated_at="2026-08-02", marker="new"):
    def materialize(output_root: Path) -> None:
        _write_complete_tree(
            output_root,
            contract.registry,
            contract.compatibility,
            updated_at=updated_at,
            marker=marker,
        )

    return materialize


def test_integral_generation_is_validated_and_can_remain_only_in_staging(
    contract,
    tmp_path,
):
    before = _snapshot(contract.public_root)
    result = publish_education_transactionally(
        registry=contract.registry,
        route_compatibility=contract.compatibility,
        materialize=_materializer(contract),
        public_root=contract.public_root,
        staging_directory=tmp_path / "controlled-stage",
        no_promote=True,
    )

    assert result.stats is None
    assert result.staged_output is not None
    assert result.staged_output.is_dir()
    assert len(result.validation.files) == contract.registry.municipality_count + 2
    assert _snapshot(contract.public_root) == before


def test_first_publication_creates_missing_education_root(contract, tmp_path):
    public_root = tmp_path / "first-publication" / "educacao"
    public_root.parent.mkdir(parents=True)

    result = publish_education_transactionally(
        registry=contract.registry,
        route_compatibility=contract.compatibility,
        materialize=_materializer(contract),
        public_root=public_root,
        staging_directory=tmp_path / "first-publication-stage",
    )

    assert result.stats is not None
    assert result.stats.created == contract.registry.municipality_count + 2
    assert public_root.is_dir()
    assert len(tuple(iter_managed_education_public_files(public_root))) == (
        contract.registry.municipality_count + 2
    )


def test_publication_is_untouched_until_materialization_and_validation_finish(
    contract,
    tmp_path,
):
    _write_complete_tree(
        contract.public_root,
        contract.registry,
        contract.compatibility,
        updated_at="2026-08-01",
        marker="old",
    )
    before = _snapshot(contract.public_root)
    observed_during_generation = []

    def materialize(output_root: Path) -> None:
        _write_complete_tree(
            output_root,
            contract.registry,
            contract.compatibility,
            marker="new",
        )
        observed_during_generation.append(_snapshot(contract.public_root))

    result = publish_education_transactionally(
        registry=contract.registry,
        route_compatibility=contract.compatibility,
        materialize=materialize,
        public_root=contract.public_root,
        staging_directory=tmp_path / "stage-before-validation",
    )

    assert observed_during_generation == [before]
    assert result.stats is not None
    assert _snapshot(contract.public_root) != before


def test_complete_municipal_failure_report_is_nonzero_and_fail_closed(
    contract,
    tmp_path,
    monkeypatch,
):
    _write_complete_tree(
        contract.public_root,
        contract.registry,
        contract.compatibility,
        marker="published",
    )
    before = _snapshot(contract.public_root)
    failures = [
        (record.ibge_code, record.name, f"erro-{position}")
        for position, record in enumerate(
            contract.registry.ordered_records,
            start=1,
        )
    ]

    def fail_after_one(output_root: Path) -> None:
        first = contract.registry.ordered_records[0]
        _write_json(
            output_root / "municipios" / f"{first.ibge_code}.json",
            _municipal_document(
                first,
                updated_at="2026-08-02",
                marker="partial",
            ),
        )
        raise EXPORTER.EducationMunicipalityBatchError(failures)

    with pytest.raises(EXPORTER.EducationMunicipalityBatchError) as error:
        publish_education_transactionally(
            registry=contract.registry,
            route_compatibility=contract.compatibility,
            materialize=fail_after_one,
            public_root=contract.public_root,
            staging_directory=tmp_path / "failed-stage",
        )
    assert error.value.failures == tuple(failures)
    assert _snapshot(contract.public_root) == before
    assert not (tmp_path / "failed-stage").exists()

    monkeypatch.setattr(
        EXPORTER,
        "publish_education_transactionally",
        Mock(side_effect=EXPORTER.EducationMunicipalityBatchError(failures)),
    )
    assert EXPORTER.main(["--state", "RS"]) == 1


def test_staging_write_error_after_partial_output_never_changes_publication(
    contract,
    tmp_path,
):
    _write_complete_tree(
        contract.public_root,
        contract.registry,
        contract.compatibility,
        marker="published",
    )
    before = _snapshot(contract.public_root)

    def fail_write(output_root: Path) -> None:
        first = contract.registry.ordered_records[0]
        _write_json(
            output_root / "municipios" / f"{first.ibge_code}.json",
            _municipal_document(
                first,
                updated_at="2026-08-02",
                marker="partial",
            ),
        )
        raise OSError("falha controlada de escrita no staging")

    with pytest.raises(OSError, match="falha controlada"):
        publish_education_transactionally(
            registry=contract.registry,
            route_compatibility=contract.compatibility,
            materialize=fail_write,
            public_root=contract.public_root,
            staging_directory=tmp_path / "write-error-stage",
        )
    assert _snapshot(contract.public_root) == before


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        (
            lambda root, registry: (
                root / "municipios" / f"{registry.ordered_records[0].ibge_code}.json"
            ).write_text("{}", encoding="utf-8"),
            "objeto JSON nao vazio",
        ),
        (
            lambda root, _registry: (root / "index.json").write_bytes(
                render_education_json({"updated_at": "2026-08-02"})
            ),
            "schema invalido",
        ),
        (
            lambda root, registry: (
                root / "municipios" / f"{registry.ordered_records[0].ibge_code}.json"
            ).unlink(),
            "ausentes",
        ),
        (
            lambda root, registry: _write_json(
                root / "municipios" / "4399999.json",
                _municipal_document(
                    registry.ordered_records[0],
                    updated_at="2026-08-02",
                    marker="extra",
                ),
            ),
            "extras",
        ),
    ),
)
def test_invalid_empty_missing_or_extra_staging_never_promotes(
    contract,
    tmp_path,
    mutation,
    message,
):
    _write_complete_tree(
        contract.public_root,
        contract.registry,
        contract.compatibility,
        marker="published",
    )
    before = _snapshot(contract.public_root)

    def materialize(output_root: Path) -> None:
        _write_complete_tree(
            output_root,
            contract.registry,
            contract.compatibility,
        )
        mutation(output_root, contract.registry)

    with pytest.raises(EducationValidationError, match=message):
        publish_education_transactionally(
            registry=contract.registry,
            route_compatibility=contract.compatibility,
            materialize=materialize,
            public_root=contract.public_root,
            staging_directory=tmp_path / f"invalid-stage-{message.split()[0]}",
        )
    assert _snapshot(contract.public_root) == before


def test_invalid_index_slug_and_nonfinite_document_never_promote(
    contract,
    tmp_path,
):
    _write_complete_tree(
        contract.public_root,
        contract.registry,
        contract.compatibility,
        marker="published",
    )
    before = _snapshot(contract.public_root)

    def invalid_slug(output_root: Path) -> None:
        _write_complete_tree(
            output_root,
            contract.registry,
            contract.compatibility,
        )
        index_path = output_root / "municipios_index.json"
        payload = json.loads(index_path.read_text(encoding="utf-8"))
        payload["municipios"][0]["slug"] = "slug-incompativel"
        _write_json(index_path, payload)

    with pytest.raises(EducationValidationError, match="slugs compativeis"):
        publish_education_transactionally(
            registry=contract.registry,
            route_compatibility=contract.compatibility,
            materialize=invalid_slug,
            public_root=contract.public_root,
            staging_directory=tmp_path / "invalid-index",
        )
    assert _snapshot(contract.public_root) == before

    def nonfinite(output_root: Path) -> None:
        _write_complete_tree(
            output_root,
            contract.registry,
            contract.compatibility,
        )
        record = contract.registry.ordered_records[0]
        path = output_root / "municipios" / f"{record.ibge_code}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["blocos"]["matriculas"]["series"]["fixture"][0]["valor"] = float("nan")
        path.write_text(
            json.dumps(payload, ensure_ascii=False, allow_nan=True),
            encoding="utf-8",
        )

    with pytest.raises(EducationValidationError, match="nao finita"):
        publish_education_transactionally(
            registry=contract.registry,
            route_compatibility=contract.compatibility,
            materialize=nonfinite,
            public_root=contract.public_root,
            staging_directory=tmp_path / "nonfinite-stage",
        )
    assert _snapshot(contract.public_root) == before
    with pytest.raises(ValueError):
        render_education_json({"valor": float("inf")})


def test_successful_promotion_updates_only_main_education_allowlist(
    contract,
    tmp_path,
):
    _write_complete_tree(
        contract.public_root,
        contract.registry,
        contract.compatibility,
        updated_at="2026-08-01",
        marker="old",
    )
    unrelated = {
        contract.public_root / "educacao-especial" / "index.json": b"special",
        contract.public_root / "superior" / "index.json": b"higher",
        contract.public_root / "visao-geral-municipal" / "4300034.json": b"overview",
        contract.public_root / "siope" / "catalogo.json": b"siope",
        contract.public_root / "legado" / "arquivo.json": b"legacy",
        contract.public_root / "municipios" / "README.txt": b"keep",
    }
    for path, content in unrelated.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    result = publish_education_transactionally(
        registry=contract.registry,
        route_compatibility=contract.compatibility,
        materialize=_materializer(contract, marker="new"),
        public_root=contract.public_root,
        staging_directory=tmp_path / "successful-stage",
    )

    assert result.stats is not None
    assert result.stats.updated == 3
    assert result.stats.preserved == 1
    for path, content in unrelated.items():
        assert path.read_bytes() == content
    for record in contract.registry.ordered_records:
        payload = json.loads(
            (
                contract.public_root
                / "municipios"
                / f"{record.ibge_code}.json"
            ).read_text(encoding="utf-8")
        )
        assert payload["blocos"]["matriculas"]["series"]["fixture"][0]["valor"] == "new"
    assert not (tmp_path / "successful-stage").exists()


def test_promotion_failure_rolls_back_bytes_and_mtimes(contract, tmp_path):
    _write_complete_tree(
        contract.public_root,
        contract.registry,
        contract.compatibility,
        updated_at="2026-08-01",
        marker="old",
    )
    before = _snapshot(contract.public_root)

    def fail_second(_kind: str, _relative: Path, position: int) -> None:
        if position == 2:
            raise OSError("falha injetada na promocao")

    with pytest.raises(EducationPromotionError, match="anterior restaurada"):
        publish_education_transactionally(
            registry=contract.registry,
            route_compatibility=contract.compatibility,
            materialize=_materializer(contract, marker="new"),
            public_root=contract.public_root,
            staging_directory=tmp_path / "rollback-stage",
            before_mutation=fail_second,
        )

    assert _snapshot(contract.public_root) == before
    assert not (tmp_path / "rollback-stage").exists()


def test_promotion_failure_removes_managed_directories_created_during_preparation(
    contract,
    tmp_path,
):
    assert list(contract.public_root.iterdir()) == []

    def fail_first(_kind: str, _relative: Path, position: int) -> None:
        if position == 1:
            raise OSError("falha antes da primeira mutacao")

    with pytest.raises(EducationPromotionError, match="anterior restaurada"):
        publish_education_transactionally(
            registry=contract.registry,
            route_compatibility=contract.compatibility,
            materialize=_materializer(contract),
            public_root=contract.public_root,
            staging_directory=tmp_path / "rollback-new-directory-stage",
            before_mutation=fail_first,
        )

    assert list(contract.public_root.iterdir()) == []
    assert not (tmp_path / "rollback-new-directory-stage").exists()


def test_noop_preserves_every_byte_and_mtime(contract, tmp_path):
    _write_complete_tree(
        contract.public_root,
        contract.registry,
        contract.compatibility,
        marker="same",
    )
    before = _snapshot(contract.public_root)
    result = publish_education_transactionally(
        registry=contract.registry,
        route_compatibility=contract.compatibility,
        materialize=_materializer(
            contract,
            updated_at="2026-08-03",
            marker="same",
        ),
        public_root=contract.public_root,
        staging_directory=tmp_path / "noop-stage",
    )

    assert result.stats is not None
    assert result.stats.created == 0
    assert result.stats.updated == 0
    assert result.stats.removed == 0
    assert result.stats.preserved == contract.registry.municipality_count + 2
    assert _snapshot(contract.public_root) == before


def test_created_updated_preserved_removed_stats_and_orphan_timing(
    contract,
    tmp_path,
):
    _write_complete_tree(
        contract.public_root,
        contract.registry,
        contract.compatibility,
        marker="same",
    )
    index_path = contract.public_root / "index.json"
    old_index = json.loads(index_path.read_text(encoding="utf-8"))
    old_index["updated_at"] = "2026-08-01"
    _write_json(index_path, old_index)
    missing_record = contract.registry.ordered_records[1]
    (contract.public_root / "municipios" / f"{missing_record.ibge_code}.json").unlink()
    orphan = contract.public_root / "municipios" / "4399999.json"
    orphan.write_bytes(b"orphan")

    def fail_first(_kind: str, _relative: Path, position: int) -> None:
        if position == 1:
            raise OSError("antes da primeira mutacao")

    with pytest.raises(EducationPromotionError):
        publish_education_transactionally(
            registry=contract.registry,
            route_compatibility=contract.compatibility,
            materialize=_materializer(contract, marker="same"),
            public_root=contract.public_root,
            staging_directory=tmp_path / "orphan-failed-stage",
            before_mutation=fail_first,
        )
    assert orphan.read_bytes() == b"orphan"

    result = publish_education_transactionally(
        registry=contract.registry,
        route_compatibility=contract.compatibility,
        materialize=_materializer(contract, marker="same"),
        public_root=contract.public_root,
        staging_directory=tmp_path / "stats-stage",
    )
    assert result.stats is not None
    assert result.stats.created == 1
    assert result.stats.updated == 1
    assert result.stats.preserved == 2
    assert result.stats.removed == 1
    assert not orphan.exists()


@pytest.mark.parametrize("state", ("RS", "rs"))
def test_cli_accepts_rs_and_dry_run_has_no_database_staging_or_write(
    state,
    monkeypatch,
):
    engine = Mock(side_effect=AssertionError("banco não deve ser acessado"))
    publication = Mock(side_effect=AssertionError("staging não deve ser criado"))
    monkeypatch.setattr(EXPORTER, "_get_education_engine", engine)
    monkeypatch.setattr(EXPORTER, "publish_education_transactionally", publication)

    assert EXPORTER.main(["--state", state, "--dry-run"]) == 0
    engine.assert_not_called()
    publication.assert_not_called()


def test_unknown_state_and_help_stop_before_every_effect(monkeypatch):
    """SP não possui contrato estadual; AL passou a ser um estado configurado."""
    engine = Mock(side_effect=AssertionError("efeito externo"))
    publication = Mock(side_effect=AssertionError("efeito de staging"))
    monkeypatch.setattr(EXPORTER, "_get_education_engine", engine)
    monkeypatch.setattr(EXPORTER, "publish_education_transactionally", publication)

    assert EXPORTER.main(["--state", "SP"]) == 2
    with pytest.raises(SystemExit) as help_exit:
        EXPORTER.main(["--help"])
    assert help_exit.value.code == 0
    engine.assert_not_called()
    publication.assert_not_called()


def test_staging_inside_public_data_is_rejected_before_materialization(
    contract,
):
    materialize = Mock()
    with pytest.raises(EducationStagingError, match="public/data"):
        publish_education_transactionally(
            registry=contract.registry,
            route_compatibility=contract.compatibility,
            materialize=materialize,
            public_root=contract.public_root,
            staging_directory=contract.public_root.parent / "unsafe-stage",
        )
    materialize.assert_not_called()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("id_municipio", 4300034, "codigo IBGE textual"),
        ("municipio", "Nome divergente", "nome diverge"),
    ),
)
def test_ibge_text_identity_and_canonical_name_are_mandatory(
    contract,
    tmp_path,
    field,
    value,
    message,
):
    output_root = tmp_path / f"identity-{field}"
    _write_complete_tree(
        output_root,
        contract.registry,
        contract.compatibility,
    )
    record = contract.registry.ordered_records[0]
    path = output_root / "municipios" / f"{record.ibge_code}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload[field] = value
    _write_json(path, payload)

    with pytest.raises(EducationValidationError, match=message):
        validate_education_staging(
            output_root,
            contract.registry,
            contract.compatibility,
            public_root=contract.public_root,
        )


def test_all_182_historical_slugs_are_preserved_without_public_data_read():
    state = load_state_config("RS")
    registry = load_municipality_registry(state)
    compatibility = load_education_municipality_route_compatibility(
        state,
        registry,
    )
    projected = build_education_municipalities_index_payload(
        registry,
        compatibility,
    )

    assert len(compatibility.slug_overrides) == 182
    assert len(projected["municipios"]) == registry.municipality_count == 497
    assert all(
        item["caminho"]
        == f"educacao/municipios/{item['id_municipio']}.json"
        for item in projected["municipios"]
    )
    assert len({item["slug"].casefold() for item in projected["municipios"]}) == 497


def test_update_static_data_propagates_education_failure_and_stops_later_steps(
    monkeypatch,
):
    args = SimpleNamespace(
        dry_run=False,
        skip_export=False,
        skip_partition=False,
        skip_education=False,
        education_only=True,
        skip_build=False,
        build=True,
        validate_only=False,
        no_include_derived=False,
        profile=False,
        state="RS",
    )
    executed = []

    def fail_education(name, _command, _results):
        executed.append(name)
        if name == "education":
            raise SystemExit(9)
        raise AssertionError(f"Etapa posterior executada indevidamente: {name}")

    monkeypatch.setattr(UPDATE, "parse_args", lambda: args)
    monkeypatch.setattr(UPDATE, "ensure_git_update_safe", lambda *_args: None)
    monkeypatch.setattr(UPDATE, "run_command", fail_education)

    with pytest.raises(SystemExit) as failure:
        UPDATE.main()
    assert failure.value.code == 9
    assert executed == ["education"]


def test_direct_promotion_revalidates_stage_before_any_mutation(
    contract,
    tmp_path,
):
    output_root = tmp_path / "direct-stage"
    _write_complete_tree(
        output_root,
        contract.registry,
        contract.compatibility,
    )
    (output_root / "index.json").unlink()
    before = _snapshot(contract.public_root)

    with pytest.raises(EducationValidationError, match="ausentes"):
        promote_education_staging(
            output_root,
            contract.public_root,
            contract.registry,
            contract.compatibility,
        )
    assert _snapshot(contract.public_root) == before


def test_partial_cli_options_fail_before_staging_or_database(monkeypatch):
    publication = Mock()
    engine = Mock()
    monkeypatch.setattr(EXPORTER, "publish_education_transactionally", publication)
    monkeypatch.setattr(EXPORTER, "_get_education_engine", engine)

    assert EXPORTER.main(["--state", "RS", "--limit", "1"]) == 2
    assert EXPORTER.main(["--state", "RS", "--municipios", "4300034"]) == 2
    publication.assert_not_called()
    engine.assert_not_called()


def test_materialization_rejects_accumulated_municipal_failures_before_indices(
    contract,
    tmp_path,
    monkeypatch,
):
    failures = [
        (record.ibge_code, record.name, "falha")
        for record in contract.registry.ordered_records
    ]
    import pandas as pd

    municipalities = pd.DataFrame(
        [
            {
                "id_municipio": record.ibge_code,
                "municipio": record.name,
            }
            for record in contract.registry.ordered_records
        ]
    )
    monkeypatch.setattr(
        EXPORTER,
        "exportar_municipios",
        lambda *_args, **_kwargs: (0, failures, [], []),
    )
    municipality_index = Mock()
    manifest = Mock()
    monkeypatch.setattr(EXPORTER, "gerar_municipios_index", municipality_index)
    monkeypatch.setattr(EXPORTER, "gerar_index", manifest)

    with pytest.raises(EXPORTER.EducationMunicipalityBatchError) as error:
        EXPORTER.materialize_education_outputs(
            tmp_path / "materialization-stage",
            municipalities,
            {},
            {},
            contract.registry,
            contract.compatibility,
        )
    assert error.value.failures == tuple(failures)
    municipality_index.assert_not_called()
    manifest.assert_not_called()


def test_public_orphan_pattern_never_expands_to_other_files(contract, tmp_path):
    _write_complete_tree(
        contract.public_root,
        contract.registry,
        contract.compatibility,
    )
    lookalikes = {
        contract.public_root / "municipios" / "4300034.json.bak": b"backup",
        contract.public_root / "municipios" / "slug.json": b"slug",
        contract.public_root / "municipios" / "4300034" / "index.json": b"nested",
    }
    for path, content in lookalikes.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    result = publish_education_transactionally(
        registry=contract.registry,
        route_compatibility=contract.compatibility,
        materialize=_materializer(contract),
        public_root=contract.public_root,
        staging_directory=tmp_path / "lookalike-stage",
    )
    assert result.stats is not None
    assert result.stats.removed == 0
    for path, content in lookalikes.items():
        assert path.read_bytes() == content


def test_publication_errors_share_a_fail_closed_base_type():
    assert issubclass(EducationValidationError, EducationPublicationError)
    assert issubclass(EducationPromotionError, EducationPublicationError)
