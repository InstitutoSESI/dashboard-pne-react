from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = REPO_ROOT / "data_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from src.education_municipality_routes import (  # noqa: E402
    EDUCATION_MUNICIPALITY_ROUTE_COMPATIBILITY_SCHEMA_VERSION,
    EducationMunicipalityRouteCompatibilityError,
    build_education_municipalities_index_payload,
    load_education_municipality_route_compatibility,
    render_education_municipalities_index,
    resolve_education_public_slug,
)
from src.municipality_registry import load_municipality_registry  # noqa: E402
from src.state_config import load_state_config  # noqa: E402


def _load_script(name: str):
    module_name = f"education_state_{name}"
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
OVERVIEW = _load_script("materialize_municipal_education_overview")
HIGHER = _load_script("sync_higher_education_from_sinopse")
SPECIAL_MATERIALIZE = _load_script("materialize_special_education")
SPECIAL_VALIDATE = _load_script("validate_special_education")
SPECIAL_AUDIT = _load_script("audit_special_education_completeness")

STATE_CONFIG = load_state_config("RS")
REGISTRY = load_municipality_registry(STATE_CONFIG)
ROUTE_COMPATIBILITY = load_education_municipality_route_compatibility(
    STATE_CONFIG,
    REGISTRY,
)
PUBLIC_EDUCATION_INDEX = REPO_ROOT / "public" / "data" / "educacao" / "municipios_index.json"


class ReachedSideEffect(RuntimeError):
    pass


def _entrypoints(tmp_path: Path):
    return (
        (EXPORTER, "_get_education_engine", []),
        (
            OVERVIEW,
            "get_local_postgres_engine",
            [
                "--censo-2025-csv",
                str(tmp_path / "censo.csv"),
                "--output-dir",
                str(tmp_path / "overview"),
            ],
        ),
        (HIGHER, "parse_higher_education_sources", ["--source-dir", str(tmp_path)]),
        (
            SPECIAL_MATERIALIZE,
            "load_special_education_school_source_data",
            ["--output", str(tmp_path / "special")],
        ),
        (SPECIAL_VALIDATE, "load_special_education_school_source_data", []),
        (
            SPECIAL_AUDIT,
            "load_special_education_school_source_data",
            ["--output", str(tmp_path / "special-audit.json")],
        ),
    )


@pytest.mark.parametrize("state", ("RS", "rs"))
def test_entrypoints_accept_configured_state_before_first_effect(tmp_path, state):
    for module, effect_name, extra_args in _entrypoints(tmp_path):
        with patch.object(module, effect_name, side_effect=ReachedSideEffect):
            with pytest.raises(ReachedSideEffect):
                module.main(["--state", state, *extra_args])
    assert not (tmp_path / "overview").exists()
    assert not (tmp_path / "special").exists()


def test_unknown_state_fails_before_database_source_or_write(tmp_path):
    """SP não possui configuração ativa; AL passou a ser um estado do contrato."""
    for module, effect_name, extra_args in _entrypoints(tmp_path):
        with patch.object(module, effect_name) as effect:
            assert module.main(["--state", "SP", *extra_args]) == 2
        effect.assert_not_called()
    assert list(tmp_path.iterdir()) == []


def test_help_exits_before_database_source_or_write(tmp_path):
    for module, effect_name, _extra_args in _entrypoints(tmp_path):
        with patch.object(module, effect_name) as effect:
            with pytest.raises(SystemExit) as exit_info:
                module.main(["--help"])
        assert exit_info.value.code == 0
        effect.assert_not_called()
    assert list(tmp_path.iterdir()) == []


def test_exporter_uses_bound_state_and_registry_ids_in_registry_order(monkeypatch):
    captured = {}
    reversed_records = list(reversed(REGISTRY.ordered_records))
    frame = pd.DataFrame(
        [
            {
                "id_municipio": record.ibge_code,
                "municipio": record.name,
            }
            for record in reversed_records
        ]
    )

    def fake_read_sql(query, engine, *, params):
        captured.update(query=str(query), engine=engine, params=params)
        return frame

    monkeypatch.setattr(EXPORTER.pd, "read_sql_query", fake_read_sql)
    result = EXPORTER.carregar_municipios(object(), STATE_CONFIG, REGISTRY)

    assert captured["params"]["state_code"] == "RS"
    assert captured["params"]["municipality_ids"] == tuple(
        record.ibge_code for record in REGISTRY.ordered_records
    )
    assert ":state_code" in captured["query"]
    assert "RS" not in captured["query"]
    assert REGISTRY.ordered_records[0].ibge_code not in captured["query"]
    assert result["id_municipio"].tolist() == [
        record.ibge_code for record in REGISTRY.ordered_records
    ]
    assert result["municipio"].tolist() == [
        record.name for record in REGISTRY.ordered_records
    ]
    assert "slug" not in result.columns
    assert "regiao_senai" not in captured["query"]
    assert "regiao_senai" not in result.columns


def test_exporter_rejects_foreign_numeric_and_divergent_name(monkeypatch):
    first = REGISTRY.ordered_records[0]
    foreign = pd.DataFrame(
        [{"id_municipio": "2704302", "municipio": "Maceió"}]
    )
    monkeypatch.setattr(EXPORTER.pd, "read_sql_query", lambda *_args, **_kwargs: foreign)
    with pytest.raises(ValueError, match="diverge do registro"):
        EXPORTER.carregar_municipios(object(), STATE_CONFIG, REGISTRY)

    numeric = pd.DataFrame(
        [{"id_municipio": 4314902, "municipio": "Porto Alegre"}]
    )
    monkeypatch.setattr(EXPORTER.pd, "read_sql_query", lambda *_args, **_kwargs: numeric)
    with pytest.raises(ValueError, match="permanecer texto"):
        EXPORTER.carregar_municipios(object(), STATE_CONFIG, REGISTRY)

    complete = pd.DataFrame(
        [
            {
                "id_municipio": record.ibge_code,
                "municipio": "Nome divergente" if record == first else record.name,
            }
            for record in REGISTRY.ordered_records
        ]
    )
    monkeypatch.setattr(EXPORTER.pd, "read_sql_query", lambda *_args, **_kwargs: complete)
    with pytest.raises(ValueError, match="nomes divergem"):
        EXPORTER.carregar_municipios(object(), STATE_CONFIG, REGISTRY)


def test_subset_is_allowed_only_when_contract_is_not_integral():
    first = REGISTRY.ordered_records[0].ibge_code
    subset = pd.DataFrame({"id_municipio": [first]})
    EXPORTER._validate_municipality_codes(
        subset,
        REGISTRY,
        source="subconjunto",
        require_complete=False,
    )
    with pytest.raises(ValueError, match="ausentes"):
        EXPORTER._validate_municipality_codes(
            subset,
            REGISTRY,
            source="integral",
            require_complete=True,
        )


def test_migrated_sources_do_not_read_public_indexes_as_identity():
    without_public_index = (
        "scripts/materialize_municipal_education_overview.py",
        "src/higher_education.py",
        "src/higher_education_materialization.py",
        "scripts/sync_higher_education_from_sinopse.py",
        "scripts/materialize_special_education.py",
        "src/special_education_materialization.py",
        "scripts/validate_special_education.py",
    )
    for relative in without_public_index:
        source = (PIPELINE_ROOT / relative).read_text(encoding="utf-8")
        assert "municipios_index.json" not in source
    exporter_source = (PIPELINE_ROOT / "scripts/export_education_indicators.py").read_text(
        encoding="utf-8"
    )
    assert "MUNICIPAL_INDEX" not in exporter_source
    assert "load_municipality_registry" in exporter_source


def _published_education_index() -> dict:
    return json.loads(PUBLIC_EDUCATION_INDEX.read_text(encoding="utf-8"))


def _read_top_level_object(path: Path, field: str) -> dict:
    text = path.read_text(encoding="utf-8")
    marker = f'"{field}"'
    marker_position = text.index(marker)
    object_position = text.index("{", marker_position + len(marker))
    value, _end = json.JSONDecoder().raw_decode(text[object_position:])
    return value


def _write_compatibility(tmp_path: Path, payload: object) -> Path:
    path = tmp_path / "rs.json"
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def test_route_compatibility_contains_exactly_the_published_differences():
    published = _published_education_index()["municipios"]
    published_by_id = {item["id_municipio"]: item for item in published}
    expected_overrides = {
        record.ibge_code: published_by_id[record.ibge_code]["slug"]
        for record in REGISTRY.ordered_records
        if record.slug != published_by_id[record.ibge_code]["slug"]
    }

    assert len(expected_overrides) == 182
    assert dict(ROUTE_COMPATIBILITY.slug_overrides) == expected_overrides
    assert ROUTE_COMPATIBILITY.state_code == STATE_CONFIG.state_code == "RS"
    assert (
        ROUTE_COMPATIBILITY.schema_version
        == EDUCATION_MUNICIPALITY_ROUTE_COMPATIBILITY_SCHEMA_VERSION
    )
    assert all(
        isinstance(municipality_id, str)
        and len(municipality_id) == 7
        and municipality_id.isdigit()
        and municipality_id in REGISTRY.ids
        for municipality_id in ROUTE_COMPATIBILITY.slug_overrides
    )
    assert all(
        slug and slug != REGISTRY.get_by_id(municipality_id).slug
        for municipality_id, slug in ROUTE_COMPATIBILITY.slug_overrides.items()
    )


def test_route_resolver_preserves_ibge_identity_and_uses_fallback_or_override():
    overridden_id = next(iter(ROUTE_COMPATIBILITY.slug_overrides))
    fallback_record = next(
        record
        for record in REGISTRY.ordered_records
        if record.ibge_code not in ROUTE_COMPATIBILITY.slug_overrides
    )
    overridden_record = REGISTRY.get_by_id(overridden_id)
    original = (
        overridden_record.ibge_code,
        overridden_record.name,
        overridden_record.slug,
    )

    assert resolve_education_public_slug(
        overridden_record,
        ROUTE_COMPATIBILITY,
    ) == ROUTE_COMPATIBILITY.slug_overrides[overridden_id]
    assert resolve_education_public_slug(
        fallback_record,
        ROUTE_COMPATIBILITY,
    ) == fallback_record.slug
    assert (
        overridden_record.ibge_code,
        overridden_record.name,
        overridden_record.slug,
    ) == original


def test_education_index_projection_is_semantically_and_byte_identical_without_write():
    published_bytes = PUBLIC_EDUCATION_INDEX.read_bytes()
    published_mtime = PUBLIC_EDUCATION_INDEX.stat().st_mtime_ns
    published = json.loads(published_bytes)
    projected = build_education_municipalities_index_payload(
        REGISTRY,
        ROUTE_COMPATIBILITY,
    )

    assert list(projected) == ["municipios"]
    assert len(projected["municipios"]) == REGISTRY.municipality_count == 497
    assert len(published["municipios"]) == len(projected["municipios"])
    for position, (current, expected) in enumerate(
        zip(published["municipios"], projected["municipios"], strict=True)
    ):
        municipality_id = current.get("id_municipio") or expected.get("id_municipio")
        assert list(expected) == ["id_municipio", "municipio", "slug", "caminho"], (
            f"{municipality_id}: campos projetados fora do contrato: {list(expected)}"
        )
        for field in ("id_municipio", "municipio", "slug", "caminho"):
            assert current.get(field) == expected.get(field), (
                f"posição {position}, município {municipality_id}, campo {field}: "
                f"publicado={current.get(field)!r}, projetado={expected.get(field)!r}"
            )

    public_slugs = [item["slug"].casefold() for item in projected["municipios"]]
    assert len(set(public_slugs)) == REGISTRY.municipality_count
    assert render_education_municipalities_index(
        REGISTRY,
        ROUTE_COMPATIBILITY,
    ) == published_bytes
    assert PUBLIC_EDUCATION_INDEX.read_bytes() == published_bytes
    assert PUBLIC_EDUCATION_INDEX.stat().st_mtime_ns == published_mtime


def test_public_route_metadata_matches_each_domain_without_additional_aliases():
    published_index = _published_education_index()["municipios"]
    published_by_id = {item["id_municipio"]: item for item in published_index}
    special_universe = SPECIAL_MATERIALIZE.municipalities(
        REGISTRY,
        ROUTE_COMPATIBILITY,
    )
    special_by_id = {item["id_municipio"]: item for item in special_universe}
    overview_by_id = {
        item["idMunicipality"]: item for item in OVERVIEW._registry_entries(REGISTRY)
    }

    assert all(
        list(item) == ["id_municipio", "municipio", "slug", "caminho"]
        for item in published_index
    )
    for record in REGISTRY.ordered_records:
        public_slug = published_by_id[record.ibge_code]["slug"]
        assert special_by_id[record.ibge_code] == {
            "id_municipio": record.ibge_code,
            "municipio": record.name,
            "slug": public_slug,
        }
        assert overview_by_id[record.ibge_code] == {
            "idMunicipality": record.ibge_code,
            "name": record.name,
            "slug": record.slug,
        }

        special_path = (
            REPO_ROOT
            / "public"
            / "data"
            / "educacao"
            / "educacao-especial"
            / "municipios"
            / f"{record.ibge_code}.json"
        )
        overview_path = (
            REPO_ROOT
            / "public"
            / "data"
            / "educacao"
            / "visao-geral-municipal"
            / f"{record.ibge_code}.json"
        )
        assert _read_top_level_object(special_path, "municipality") == {
            "code": record.ibge_code,
            "name": record.name,
            "slug": public_slug,
        }
        assert _read_top_level_object(overview_path, "municipality") == {
            "idMunicipality": record.ibge_code,
            "name": record.name,
            "slug": record.slug,
        }

    higher_manifest = (
        REPO_ROOT / "public" / "data" / "educacao" / "superior" / "index.json"
    ).read_text(encoding="utf-8")
    assert '"slug"' not in higher_manifest


@pytest.mark.parametrize(
    ("state", "expected_state", "expected_overrides", "expected_municipalities"),
    (
        ("RS", "RS", 182, 497),
        ("rs", "RS", 182, 497),
        ("AL", "AL", 36, 102),
        ("al", "AL", 36, 102),
    ),
)
def test_route_compatibility_loads_for_each_active_state(
    state,
    expected_state,
    expected_overrides,
    expected_municipalities,
):
    state_config = load_state_config(state)
    registry = load_municipality_registry(state_config)
    compatibility = load_education_municipality_route_compatibility(
        state_config,
        registry,
    )
    assert compatibility.state_code == expected_state
    assert len(compatibility.slug_overrides) == expected_overrides
    assert registry.municipality_count == expected_municipalities

    payload = build_education_municipalities_index_payload(registry, compatibility)
    assert len(payload["municipios"]) == expected_municipalities
    slugs = [entry["slug"] for entry in payload["municipios"]]
    assert len(set(slugs)) == len(slugs)


def test_al_route_overrides_preserve_accents_and_elide_apostrophes():
    """A regra pública de AL é a mesma do RS: acento mantido, apóstrofo elidido."""
    state_config = load_state_config("AL")
    registry = load_municipality_registry(state_config)
    compatibility = load_education_municipality_route_compatibility(
        state_config,
        registry,
    )
    expected = {
        "2704302": "maceió",
        "2706406": "pão-de-açúcar",
        "2708501": "são-luís-do-quitunde",
        "2702355": "craíbas",
        "2705705": "olho-dágua-das-flores",
        "2709004": "tanque-darca",
    }
    for municipality_id, public_slug in expected.items():
        assert resolve_education_public_slug(
            registry.get_by_id(municipality_id),
            compatibility,
        ) == public_slug
    # Municípios sem acento nem apóstrofo não recebem override.
    assert "2700201" not in compatibility.slug_overrides


def test_unknown_state_fails_before_route_compatibility_load(tmp_path):
    for module, extra_args in (
        (EXPORTER, []),
        (SPECIAL_MATERIALIZE, ["--output", str(tmp_path / "special")]),
        (SPECIAL_VALIDATE, []),
    ):
        with patch.object(
            module,
            "load_education_municipality_route_compatibility",
            side_effect=ReachedSideEffect,
        ) as compatibility_loader:
            assert module.main(["--state", "SP", *extra_args]) == 2
        compatibility_loader.assert_not_called()


@pytest.mark.parametrize(
    ("mutate", "message"),
    (
        (
            lambda payload: payload["slugOverrides"].update(
                {"2704302": "maceio"}
            ),
            "órfão",
        ),
        (
            lambda payload: payload["slugOverrides"].update(
                {
                    REGISTRY.ordered_records[0].ibge_code:
                    REGISTRY.ordered_records[0].slug
                }
            ),
            "redundante",
        ),
        (
            lambda payload: payload.update({"stateCode": "AL"}),
            "mesmo estado",
        ),
    ),
)
def test_route_compatibility_rejects_orphan_redundant_or_wrong_state(
    tmp_path,
    mutate,
    message,
):
    payload = {
        "schemaVersion": EDUCATION_MUNICIPALITY_ROUTE_COMPATIBILITY_SCHEMA_VERSION,
        "stateCode": "RS",
        "slugOverrides": dict(ROUTE_COMPATIBILITY.slug_overrides),
    }
    mutate(payload)
    path = _write_compatibility(tmp_path, payload)
    with pytest.raises(EducationMunicipalityRouteCompatibilityError, match=message):
        load_education_municipality_route_compatibility(
            STATE_CONFIG,
            REGISTRY,
            compatibility_path=path,
        )


def test_route_compatibility_rejects_duplicate_json_key(tmp_path):
    first_id = REGISTRY.ordered_records[0].ibge_code
    path = tmp_path / "rs.json"
    path.write_text(
        "{"
        '"schemaVersion":"education-municipality-route-compat-v1",'
        '"stateCode":"RS",'
        f'"slugOverrides":{{"{first_id}":"um","{first_id}":"dois"}}'
        "}",
        encoding="utf-8",
    )
    with pytest.raises(EducationMunicipalityRouteCompatibilityError, match="duplicada"):
        load_education_municipality_route_compatibility(
            STATE_CONFIG,
            REGISTRY,
            compatibility_path=path,
        )


def test_route_compatibility_rejects_empty_slug(tmp_path):
    overridden_id = next(iter(ROUTE_COMPATIBILITY.slug_overrides))
    payload = {
        "schemaVersion": EDUCATION_MUNICIPALITY_ROUTE_COMPATIBILITY_SCHEMA_VERSION,
        "stateCode": "RS",
        "slugOverrides": dict(ROUTE_COMPATIBILITY.slug_overrides),
    }
    payload["slugOverrides"][overridden_id] = ""
    path = _write_compatibility(tmp_path, payload)

    with pytest.raises(EducationMunicipalityRouteCompatibilityError, match="inválido"):
        load_education_municipality_route_compatibility(
            STATE_CONFIG,
            REGISTRY,
            compatibility_path=path,
        )


def test_route_compatibility_rejects_resulting_slug_collision(tmp_path):
    overridden_id = next(iter(ROUTE_COMPATIBILITY.slug_overrides))
    fallback_record = next(
        record
        for record in REGISTRY.ordered_records
        if record.ibge_code not in ROUTE_COMPATIBILITY.slug_overrides
    )
    payload = {
        "schemaVersion": EDUCATION_MUNICIPALITY_ROUTE_COMPATIBILITY_SCHEMA_VERSION,
        "stateCode": "RS",
        "slugOverrides": dict(ROUTE_COMPATIBILITY.slug_overrides),
    }
    payload["slugOverrides"][overridden_id] = fallback_record.slug
    path = _write_compatibility(tmp_path, payload)

    with pytest.raises(
        EducationMunicipalityRouteCompatibilityError,
        match="não são únicos",
    ):
        load_education_municipality_route_compatibility(
            STATE_CONFIG,
            REGISTRY,
            compatibility_path=path,
        )
