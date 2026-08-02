"""Instrumentacao opt-in e reproduzivel para o pipeline de dados.

O modulo usa somente a biblioteca padrao e nao cria timers, diretorios ou
eventos quando o perfil esta desabilitado. Processos filhos escrevem fragmentos
independentes; somente o processo raiz consolida o relatorio final.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from functools import wraps
import json
import math
import os
from pathlib import Path
import platform
import re
import sys
import tempfile
import time
from typing import Any, TypeVar
from urllib.parse import urlsplit, urlunsplit
import uuid


PROFILE_SCHEMA_VERSION = "pipeline-profile-v1"
PROFILE_SUMMARY_SCHEMA_VERSION = "pipeline-profile-summary-v1"
PROFILE_FRAGMENT_SCHEMA_VERSION = "pipeline-profile-fragment-v1"

DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = DATA_PIPELINE_DIR.parent
DEFAULT_PROFILE_ROOT = DATA_PIPELINE_DIR / "export" / "profiles"
TEMP_ROOT = Path(tempfile.gettempdir()).resolve()

PROFILE_ENV_ENABLED = "PNE_PIPELINE_PROFILE_ENABLED"
PROFILE_ENV_ROOT_RUN_ID = "PNE_PIPELINE_PROFILE_ROOT_RUN_ID"
PROFILE_ENV_RUN_ID = "PNE_PIPELINE_PROFILE_RUN_ID"
PROFILE_ENV_PARENT_RUN_ID = "PNE_PIPELINE_PROFILE_PARENT_RUN_ID"
PROFILE_ENV_PARENT_EVENT_ID = "PNE_PIPELINE_PROFILE_PARENT_EVENT_ID"
PROFILE_ENV_OUTPUT_DIR = "PNE_PIPELINE_PROFILE_OUTPUT_DIR"
PROFILE_ENV_STATE_CODE = "PNE_PIPELINE_PROFILE_STATE_CODE"
PROFILE_ENV_COMMAND = "PNE_PIPELINE_PROFILE_COMMAND"
PROFILE_ENV_PARAMETERS = "PNE_PIPELINE_PROFILE_PARAMETERS"

PROFILE_CATEGORIES = frozenset(
    {
        "orchestration",
        "subprocess",
        "query",
        "compute",
        "serialization",
        "read",
        "write",
        "validation",
        "promotion",
        "cache",
        "build",
    }
)

_MAX_TEXT_LENGTH = 500
_MAX_METADATA_ITEMS = 50
_SECRET_KEY_PARTS = (
    "password",
    "passwd",
    "senha",
    "secret",
    "credential",
    "databaseurl",
    "connectionurl",
    "supabaseurl",
    "servicekey",
    "apikey",
    "accesskey",
    "dbsenha",
)
_URL_CREDENTIAL_RE = re.compile(
    r"(?P<scheme>[a-z][a-z0-9+.-]*://)(?P<credentials>[^/@\s:]+:[^/@\s]+)@",
    re.IGNORECASE,
)
_INLINE_SECRET_RE = re.compile(
    r"(?i)\b(password|passwd|senha|secret|token|api[_-]?key)\s*[:=]\s*([^\s,;]+)"
)
_WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")

_ACTIVE_SESSION: ContextVar[ProfileSession | None] = ContextVar(
    "pipeline_profile_session",
    default=None,
)

T = TypeVar("T")


class ProfileError(RuntimeError):
    """Base dos erros restritos ao relatorio de perfil."""


class ProfileValidationError(ProfileError):
    """O perfil ou um fragmento nao cumpre o schema seguro."""


class ProfileOutputError(ProfileError):
    """O diretorio ou a escrita do relatorio e inseguro/invalido."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _duration_ms(duration_ns: int) -> float:
    if duration_ns < 0:
        raise ProfileValidationError("Duracao monotonicamente negativa.")
    value = round(duration_ns / 1_000_000, 6)
    if duration_ns > 0 and value == 0:
        return 0.000001
    return value


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _looks_like_absolute_path(value: str) -> bool:
    return value.startswith("/") or bool(_WINDOWS_ABSOLUTE_RE.match(value))


def sanitize_profile_path(value: str | os.PathLike[str]) -> str:
    """Representa paths sem expor diretorios pessoais desnecessarios."""

    raw = os.fspath(value)
    try:
        resolved = Path(raw).expanduser().resolve(strict=False)
    except (OSError, RuntimeError, ValueError):
        return Path(raw).name or "<path>"
    if _is_relative_to(resolved, REPO_ROOT.resolve()):
        return resolved.relative_to(REPO_ROOT.resolve()).as_posix()
    if _is_relative_to(resolved, TEMP_ROOT):
        relative = resolved.relative_to(TEMP_ROOT)
        tail = relative.parts[-2:] if len(relative.parts) > 1 else relative.parts
        return "/".join(("<temp>", *tail)) if tail else "<temp>"
    return f"<external>/{resolved.name}" if resolved.name else "<external>"


def _sanitize_url(value: str) -> str:
    value = _URL_CREDENTIAL_RE.sub(r"\g<scheme>[REDACTED]@", value)
    try:
        parsed = urlsplit(value)
    except ValueError:
        return value
    if not parsed.scheme or not parsed.netloc:
        return value
    hostname = parsed.hostname or ""
    try:
        parsed_port = parsed.port
    except ValueError:
        return _URL_CREDENTIAL_RE.sub(r"\g<scheme>[REDACTED]@", value)
    port = f":{parsed_port}" if parsed_port is not None else ""
    netloc = f"{hostname}{port}"
    if parsed.username is not None or parsed.password is not None:
        netloc = f"[REDACTED]@{netloc}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, ""))


def _is_secret_key(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", key.casefold())
    return any(part in normalized for part in _SECRET_KEY_PARTS)


def _sanitize_string(value: str) -> str:
    sanitized = _INLINE_SECRET_RE.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)
    sanitized = _sanitize_url(sanitized)
    if _looks_like_absolute_path(sanitized):
        sanitized = sanitize_profile_path(sanitized)
    if len(sanitized) > _MAX_TEXT_LENGTH:
        sanitized = sanitized[: _MAX_TEXT_LENGTH - 3] + "..."
    return sanitized


def sanitize_profile_value(value: Any, *, key: str | None = None, depth: int = 0) -> Any:
    """Limita metadados a valores pequenos, finitos e sem credenciais."""

    if key is not None and _is_secret_key(key):
        return "[REDACTED]"
    if depth > 5:
        return "<truncated>"
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ProfileValidationError("Metadado numerico deve ser finito.")
        return value
    if isinstance(value, Path) or isinstance(value, os.PathLike):
        return sanitize_profile_path(value)
    if isinstance(value, str):
        return _sanitize_string(value)
    if isinstance(value, Mapping):
        items = list(value.items())[:_MAX_METADATA_ITEMS]
        return {
            str(child_key): sanitize_profile_value(
                child,
                key=str(child_key),
                depth=depth + 1,
            )
            for child_key, child in items
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        items = list(value)[:_MAX_METADATA_ITEMS]
        return [sanitize_profile_value(child, depth=depth + 1) for child in items]
    return _sanitize_string(str(value))


def sanitize_profile_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not value:
        return {}
    sanitized = sanitize_profile_value(value)
    if not isinstance(sanitized, dict):  # pragma: no cover - defesa de tipo
        raise ProfileValidationError("Mapeamento de perfil invalido.")
    return sanitized


def validate_profile_output_path(
    requested: str | os.PathLike[str] | None,
    *,
    run_id: str,
) -> Path:
    """Aceita somente a raiz ignorada do pipeline ou descendentes do temp."""

    candidate = (
        DEFAULT_PROFILE_ROOT / run_id
        if requested is None
        else Path(requested).expanduser()
    ).resolve(strict=False)
    default_root = DEFAULT_PROFILE_ROOT.resolve(strict=False)
    safe = (
        _is_relative_to(candidate, default_root)
        or _is_relative_to(candidate, TEMP_ROOT)
    )
    forbidden = {
        candidate.anchor and Path(candidate.anchor).resolve(strict=False),
        REPO_ROOT.resolve(strict=False),
        DATA_PIPELINE_DIR.resolve(strict=False),
        DEFAULT_PROFILE_ROOT.resolve(strict=False),
        TEMP_ROOT,
    }
    if not safe or candidate in forbidden:
        raise ProfileOutputError(
            "Diretorio de profile inseguro; use data_pipeline/export/profiles/"
            "<run-id> ou um subdiretorio temporario dedicado."
        )
    for protected in (
        REPO_ROOT / "public" / "data",
        DATA_PIPELINE_DIR / "data",
        DATA_PIPELINE_DIR / ".staging",
    ):
        protected_resolved = protected.resolve(strict=False)
        if candidate == protected_resolved or _is_relative_to(candidate, protected_resolved):
            raise ProfileOutputError(
                f"Diretorio de profile protegido: {sanitize_profile_path(candidate)}."
            )
    return candidate


def new_profile_run_id() -> str:
    timestamp = _utc_now().strftime("%Y%m%dT%H%M%S%fZ")
    return f"{timestamp}-{uuid.uuid4().hex[:12]}"


def _numeric_counter(value: Any) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProfileValidationError("Counters devem ser numericos e nao booleanos.")
    if isinstance(value, float) and not math.isfinite(value):
        raise ProfileValidationError("Counters devem ser finitos.")
    return value


@dataclass(frozen=True, slots=True)
class ProfileMetric:
    name: str
    value: int | float
    unit: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": self.name,
            "value": _numeric_counter(self.value),
        }
        if self.unit:
            payload["unit"] = self.unit
        return payload


@dataclass(frozen=True, slots=True)
class ProfileEvent:
    event_id: str
    parent_event_id: str | None
    category: str
    name: str
    started_at: str
    finished_at: str
    duration_ns: int
    cpu_duration_ns: int | None
    status: str
    process_id: int
    counters: Mapping[str, int | float] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    error_type: str | None = None
    error_message: str | None = None
    sequence: int = 0

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "eventId": self.event_id,
            "category": self.category,
            "name": self.name,
            "startedAt": self.started_at,
            "finishedAt": self.finished_at,
            "durationMs": _duration_ms(self.duration_ns),
            "status": self.status,
            "processId": self.process_id,
            "counters": {
                key: _numeric_counter(value)
                for key, value in sorted(self.counters.items())
            },
            "metadata": sanitize_profile_mapping(self.metadata),
        }
        if self.parent_event_id:
            payload["parentEventId"] = self.parent_event_id
        if self.cpu_duration_ns is not None:
            payload["cpuDurationMs"] = _duration_ms(self.cpu_duration_ns)
        if self.error_type:
            payload["errorType"] = self.error_type
        if self.error_message:
            payload["errorMessage"] = _sanitize_string(self.error_message)
        return payload


@dataclass(frozen=True, slots=True)
class ProfileSummary:
    schema_version: str
    run_id: str
    status: str
    duration_ns: int
    event_count: int
    process_count: int
    categories: Mapping[str, Any]
    counters: Mapping[str, int | float]
    missing_fragments: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "runId": self.run_id,
            "status": self.status,
            "durationMs": _duration_ms(self.duration_ns),
            "eventCount": self.event_count,
            "processCount": self.process_count,
            "categories": self.categories,
            "counters": {
                key: _numeric_counter(value)
                for key, value in sorted(self.counters.items())
            },
            "missingFragments": list(self.missing_fragments),
        }


@dataclass(frozen=True, slots=True)
class ProfileChildContext:
    run_id: str
    parent_event_id: str
    environment: Mapping[str, str]


@dataclass(slots=True)
class _PendingAggregate:
    category: str
    name: str
    parent_event_id: str | None
    metadata: dict[str, Any]
    duration_ns: int = 0
    counters: dict[str, int | float] = field(default_factory=dict)
    operations: int = 0


class NullProfileOperation:
    """Contexto sem timers para o caminho desativado."""

    event_id: str | None = None
    duration_ns = 0
    event: ProfileEvent | None = None

    def __enter__(self) -> NullProfileOperation:
        return self

    def __exit__(self, *_args: Any) -> bool:
        return False

    def add_counter(self, _name: str, _value: int | float) -> None:
        return None

    def add_counters(self, **_values: int | float) -> None:
        return None

    def add_metadata(self, **_values: Any) -> None:
        return None

    def mark_error(self, *_args: Any, **_kwargs: Any) -> None:
        return None


class ProfileOperation:
    def __init__(
        self,
        session: ProfileSession,
        *,
        category: str,
        name: str,
        parent_event_id: str | None = None,
        counters: Mapping[str, int | float] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        if category not in PROFILE_CATEGORIES:
            raise ProfileValidationError(f"Categoria de profile invalida: {category}.")
        self.session = session
        self.category = category
        self.name = _sanitize_string(name)
        self.explicit_parent_event_id = parent_event_id
        self.counters: dict[str, int | float] = {
            str(key): _numeric_counter(value)
            for key, value in (counters or {}).items()
        }
        self.metadata = sanitize_profile_mapping(metadata)
        self.error_type: str | None = None
        self.error_message: str | None = None
        self.event_id: str | None = None
        self.event: ProfileEvent | None = None
        self.duration_ns = 0
        self._entered = False

    def __enter__(self) -> ProfileOperation:
        if self._entered:
            raise ProfileValidationError("Operacao de profile nao pode ser reutilizada.")
        self._entered = True
        self.sequence = self.session.next_sequence()
        self.event_id = f"{self.session.run_id}:{self.sequence:06d}"
        self.parent_event_id = (
            self.explicit_parent_event_id
            or self.session.current_event_id
            or self.session.parent_event_id
        )
        self.started_at_dt = _utc_now()
        self.started_ns = time.perf_counter_ns()
        self.cpu_started_ns = time.process_time_ns()
        self.session.push_event(self.event_id)
        return self

    def add_counter(self, name: str, value: int | float) -> None:
        self.counters[str(name)] = _numeric_counter(value)

    def add_counters(self, **values: int | float) -> None:
        for name, value in values.items():
            self.add_counter(name, value)

    def add_metadata(self, **values: Any) -> None:
        self.metadata.update(sanitize_profile_mapping(values))

    def mark_error(
        self,
        error_type: str,
        error_message: str,
    ) -> None:
        self.error_type = _sanitize_string(error_type)
        self.error_message = _sanitize_string(error_message)

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, _tb: Any) -> bool:
        finished_ns = time.perf_counter_ns()
        cpu_finished_ns = time.process_time_ns()
        finished_at_dt = _utc_now()
        self.duration_ns = max(finished_ns - self.started_ns, 0)
        cpu_duration_ns = max(cpu_finished_ns - self.cpu_started_ns, 0)
        if exc is not None:
            self.error_type = exc_type.__name__ if exc_type is not None else type(exc).__name__
            self.error_message = _sanitize_string(str(exc))
        status = "error" if self.error_type else "success"
        assert self.event_id is not None
        self.event = ProfileEvent(
            event_id=self.event_id,
            parent_event_id=self.parent_event_id,
            category=self.category,
            name=self.name,
            started_at=_utc_text(self.started_at_dt),
            finished_at=_utc_text(finished_at_dt),
            duration_ns=self.duration_ns,
            cpu_duration_ns=cpu_duration_ns,
            status=status,
            process_id=os.getpid(),
            counters=dict(self.counters),
            metadata=dict(self.metadata),
            error_type=self.error_type,
            error_message=self.error_message,
            sequence=self.sequence,
        )
        self.session.pop_event(self.event_id)
        self.session.add_event(self.event)
        return False


class ProfileSession:
    """Sessao em memoria; so grava quando explicitamente finalizada."""

    def __init__(
        self,
        *,
        enabled: bool,
        run_id: str = "disabled",
        root_run_id: str | None = None,
        parent_run_id: str | None = None,
        parent_event_id: str | None = None,
        state_code: str = "RS",
        command: str = "",
        parameters: Mapping[str, Any] | None = None,
        output_dir: Path | None = None,
        is_root: bool = False,
    ) -> None:
        self.enabled = enabled
        self.events: list[ProfileEvent] = []
        self._event_stack: list[str] = []
        self._sequence = 0
        self._pending_aggregates: dict[
            tuple[str, str, str | None, str], _PendingAggregate
        ] = {}
        self.expected_fragments: dict[str, str] = {}
        self._finished = False
        self.status = "disabled" if not enabled else "running"
        self.finished_at: str | None = None
        self.error_type: str | None = None
        self.error_message: str | None = None
        self.duration_ns = 0
        if not enabled:
            self.run_id = run_id
            self.root_run_id = root_run_id or run_id
            self.parent_run_id = parent_run_id
            self.parent_event_id = parent_event_id
            self.state_code = state_code
            self.command = command
            self.parameters = {}
            self.output_dir = None
            self.is_root = False
            self.process_id = os.getpid()
            self.started_at = ""
            self.environment = {}
            return

        if not re.fullmatch(r"[A-Za-z0-9_.:-]+", run_id):
            raise ProfileValidationError("runId contem caracteres inseguros.")
        self.run_id = run_id
        self.root_run_id = root_run_id or run_id
        self.parent_run_id = parent_run_id
        self.parent_event_id = parent_event_id
        self.state_code = _sanitize_string(state_code.upper())
        self.command = _sanitize_string(command)
        self.parameters = sanitize_profile_mapping(parameters)
        self.output_dir = output_dir
        self.is_root = is_root
        self.process_id = os.getpid()
        self._started_at_dt = _utc_now()
        self.started_at = _utc_text(self._started_at_dt)
        self._started_ns = time.perf_counter_ns()
        self._cpu_started_ns = time.process_time_ns()
        self.environment = {
            "pythonVersion": platform.python_version(),
            "pythonImplementation": platform.python_implementation(),
            "platform": sys.platform,
        }

    @classmethod
    def disabled(cls) -> ProfileSession:
        return cls(enabled=False)

    @classmethod
    def create_root(
        cls,
        *,
        state_code: str,
        command: str,
        parameters: Mapping[str, Any] | None = None,
        requested_output: str | os.PathLike[str] | None = None,
        run_id: str | None = None,
    ) -> ProfileSession:
        actual_run_id = run_id or new_profile_run_id()
        output_dir = validate_profile_output_path(requested_output, run_id=actual_run_id)
        return cls(
            enabled=True,
            run_id=actual_run_id,
            root_run_id=actual_run_id,
            state_code=state_code,
            command=command,
            parameters=parameters,
            output_dir=output_dir,
            is_root=True,
        )

    @classmethod
    def from_environment(
        cls,
        *,
        command: str | None = None,
        state_code: str | None = None,
        parameters: Mapping[str, Any] | None = None,
    ) -> ProfileSession:
        if os.environ.get(PROFILE_ENV_ENABLED) != "1":
            return cls.disabled()
        output_raw = os.environ.get(PROFILE_ENV_OUTPUT_DIR)
        run_id = os.environ.get(PROFILE_ENV_RUN_ID)
        root_run_id = os.environ.get(PROFILE_ENV_ROOT_RUN_ID)
        if not output_raw or not run_id or not root_run_id:
            raise ProfileValidationError("Contexto de profile do subprocesso incompleto.")
        environment_parameters: dict[str, Any] = {}
        raw_parameters = os.environ.get(PROFILE_ENV_PARAMETERS)
        if raw_parameters:
            try:
                loaded = json.loads(raw_parameters)
            except json.JSONDecodeError as exc:
                raise ProfileValidationError("Parametros de profile do subprocesso invalidos.") from exc
            if not isinstance(loaded, dict):
                raise ProfileValidationError("Parametros de profile devem ser um objeto.")
            environment_parameters.update(loaded)
        environment_parameters.update(parameters or {})
        output_dir = validate_profile_output_path(output_raw, run_id=root_run_id)
        return cls(
            enabled=True,
            run_id=run_id,
            root_run_id=root_run_id,
            parent_run_id=os.environ.get(PROFILE_ENV_PARENT_RUN_ID),
            parent_event_id=os.environ.get(PROFILE_ENV_PARENT_EVENT_ID),
            state_code=state_code or os.environ.get(PROFILE_ENV_STATE_CODE, "RS"),
            command=command or os.environ.get(PROFILE_ENV_COMMAND, "subprocess"),
            parameters=environment_parameters,
            output_dir=output_dir,
            is_root=False,
        )

    @property
    def current_event_id(self) -> str | None:
        return self._event_stack[-1] if self._event_stack else None

    def next_sequence(self) -> int:
        self._sequence += 1
        return self._sequence

    def push_event(self, event_id: str) -> None:
        self._event_stack.append(event_id)

    def pop_event(self, event_id: str) -> None:
        if not self._event_stack or self._event_stack[-1] != event_id:
            raise ProfileValidationError("Pilha hierarquica de eventos corrompida.")
        self._event_stack.pop()

    def add_event(self, event: ProfileEvent) -> None:
        if any(existing.event_id == event.event_id for existing in self.events):
            raise ProfileValidationError(f"eventId duplicado: {event.event_id}.")
        self.events.append(event)

    def operation(
        self,
        category: str,
        name: str,
        *,
        parent_event_id: str | None = None,
        counters: Mapping[str, int | float] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> ProfileOperation | NullProfileOperation:
        if not self.enabled:
            return NullProfileOperation()
        return ProfileOperation(
            self,
            category=category,
            name=name,
            parent_event_id=parent_event_id,
            counters=counters,
            metadata=metadata,
        )

    def record_aggregate_event(
        self,
        *,
        category: str,
        name: str,
        duration_ns: int,
        counters: Mapping[str, int | float] | None = None,
        metadata: Mapping[str, Any] | None = None,
        status: str = "success",
        parent_event_id: str | None = None,
    ) -> ProfileEvent | None:
        if not self.enabled:
            return None
        if category not in PROFILE_CATEGORIES:
            raise ProfileValidationError(f"Categoria de profile invalida: {category}.")
        sequence = self.next_sequence()
        finished = _utc_now()
        started = finished - timedelta(microseconds=max(duration_ns, 0) / 1_000)
        event = ProfileEvent(
            event_id=f"{self.run_id}:{sequence:06d}",
            parent_event_id=parent_event_id or self.current_event_id or self.parent_event_id,
            category=category,
            name=_sanitize_string(name),
            started_at=_utc_text(started),
            finished_at=_utc_text(finished),
            duration_ns=max(duration_ns, 0),
            cpu_duration_ns=None,
            status=status,
            process_id=self.process_id,
            counters={
                str(key): _numeric_counter(value)
                for key, value in (counters or {}).items()
            },
            metadata=sanitize_profile_mapping(metadata),
            sequence=sequence,
        )
        self.add_event(event)
        return event

    def accumulate_event(
        self,
        *,
        category: str,
        name: str,
        duration_ns: int = 0,
        counters: Mapping[str, int | float] | None = None,
        metadata: Mapping[str, Any] | None = None,
        parent_event_id: str | None = None,
    ) -> None:
        """Agrega operacoes repetitivas sem criar um evento por item."""

        if not self.enabled:
            return
        if category not in PROFILE_CATEGORIES:
            raise ProfileValidationError(f"Categoria de profile invalida: {category}.")
        sanitized_metadata = sanitize_profile_mapping(metadata)
        resolved_parent = parent_event_id or self.current_event_id or self.parent_event_id
        metadata_key = json.dumps(
            sanitized_metadata,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        key = (category, _sanitize_string(name), resolved_parent, metadata_key)
        aggregate = self._pending_aggregates.get(key)
        if aggregate is None:
            aggregate = _PendingAggregate(
                category=category,
                name=key[1],
                parent_event_id=resolved_parent,
                metadata=sanitized_metadata,
            )
            self._pending_aggregates[key] = aggregate
        aggregate.duration_ns += max(int(duration_ns), 0)
        aggregate.operations += 1
        for counter_name, counter_value in (counters or {}).items():
            numeric = _numeric_counter(counter_value)
            aggregate.counters[str(counter_name)] = (
                aggregate.counters.get(str(counter_name), 0) + numeric
            )

    def _flush_pending_aggregates(self) -> None:
        pending = self._pending_aggregates
        self._pending_aggregates = {}
        for key in sorted(pending):
            aggregate = pending[key]
            counters = dict(aggregate.counters)
            counters["operations"] = counters.get("operations", 0) + aggregate.operations
            metadata = dict(aggregate.metadata)
            metadata["aggregated"] = True
            self.record_aggregate_event(
                category=aggregate.category,
                name=aggregate.name,
                duration_ns=aggregate.duration_ns,
                counters=counters,
                metadata=metadata,
                parent_event_id=aggregate.parent_event_id,
            )

    def child_context(
        self,
        *,
        parent_event_id: str,
        command: str,
        parameters: Mapping[str, Any] | None = None,
    ) -> ProfileChildContext:
        if not self.enabled or self.output_dir is None:
            raise ProfileValidationError("Sessao desabilitada nao cria contexto filho.")
        child_run_id = new_profile_run_id()
        self.expected_fragments[child_run_id] = parent_event_id
        environment = {
            PROFILE_ENV_ENABLED: "1",
            PROFILE_ENV_ROOT_RUN_ID: self.root_run_id,
            PROFILE_ENV_RUN_ID: child_run_id,
            PROFILE_ENV_PARENT_RUN_ID: self.run_id,
            PROFILE_ENV_PARENT_EVENT_ID: parent_event_id,
            PROFILE_ENV_OUTPUT_DIR: str(self.output_dir),
            PROFILE_ENV_STATE_CODE: self.state_code,
            PROFILE_ENV_COMMAND: _sanitize_string(command),
            PROFILE_ENV_PARAMETERS: json.dumps(
                sanitize_profile_mapping(parameters),
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        }
        return ProfileChildContext(child_run_id, parent_event_id, environment)

    def finish(
        self,
        status: str,
        error: BaseException | None = None,
    ) -> None:
        if not self.enabled or self._finished:
            return
        if self._event_stack:
            raise ProfileValidationError("Sessao finalizada com eventos abertos.")
        self._flush_pending_aggregates()
        finished_ns = time.perf_counter_ns()
        self.duration_ns = max(finished_ns - self._started_ns, 0)
        self.cpu_duration_ns = max(time.process_time_ns() - self._cpu_started_ns, 0)
        self.finished_at = _utc_text(_utc_now())
        self.status = status
        if error is not None:
            self.error_type = type(error).__name__
            self.error_message = _sanitize_string(str(error))
        self._finished = True

    def event_dicts(self) -> list[dict[str, Any]]:
        return [
            event.to_dict()
            for event in sorted(self.events, key=lambda item: (item.sequence, item.event_id))
        ]

    def fragment_payload(self) -> dict[str, Any]:
        if not self.enabled or not self._finished:
            raise ProfileValidationError("Fragmento exige sessao finalizada.")
        payload: dict[str, Any] = {
            "schemaVersion": PROFILE_FRAGMENT_SCHEMA_VERSION,
            "rootRunId": self.root_run_id,
            "runId": self.run_id,
            "parentRunId": self.parent_run_id,
            "parentEventId": self.parent_event_id,
            "stateCode": self.state_code,
            "command": self.command,
            "startedAt": self.started_at,
            "finishedAt": self.finished_at,
            "durationMs": _duration_ms(self.duration_ns),
            "status": self.status,
            "processId": self.process_id,
            "parameters": self.parameters,
            "environment": self.environment,
            "events": self.event_dicts(),
        }
        if self.error_type:
            payload["errorType"] = self.error_type
        if self.error_message:
            payload["errorMessage"] = self.error_message
        return payload


def get_active_profile_session() -> ProfileSession | None:
    session = _ACTIVE_SESSION.get()
    return session if session is not None and session.enabled else None


@contextmanager
def activate_profile_session(session: ProfileSession) -> Iterator[ProfileSession]:
    if not session.enabled:
        yield session
        return
    token = _ACTIVE_SESSION.set(session)
    try:
        yield session
    finally:
        _ACTIVE_SESSION.reset(token)


def profile_operation(
    category: str,
    name: str,
    *,
    session: ProfileSession | None = None,
    parent_event_id: str | None = None,
    counters: Mapping[str, int | float] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> ProfileOperation | NullProfileOperation:
    selected = session or get_active_profile_session()
    if selected is None or not selected.enabled:
        return NullProfileOperation()
    return selected.operation(
        category,
        name,
        parent_event_id=parent_event_id,
        counters=counters,
        metadata=metadata,
    )


def profile_step(
    name: str,
    *,
    session: ProfileSession | None = None,
    category: str = "orchestration",
    counters: Mapping[str, int | float] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> ProfileOperation | NullProfileOperation:
    return profile_operation(
        category,
        name,
        session=session,
        counters=counters,
        metadata=metadata,
    )


def profile_query(
    name: str,
    *,
    session: ProfileSession | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> ProfileOperation | NullProfileOperation:
    return profile_operation("query", name, session=session, metadata=metadata)


def profile_file_operation(
    category: str,
    name: str,
    *,
    path: Path | str | None = None,
    session: ProfileSession | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> ProfileOperation | NullProfileOperation:
    if category not in {"read", "write", "serialization", "promotion"}:
        raise ProfileValidationError(f"Categoria de arquivo invalida: {category}.")
    merged = dict(metadata or {})
    if path is not None:
        merged["path"] = sanitize_profile_path(path)
    return profile_operation(category, name, session=session, metadata=merged)


def record_tabular_result(operation: ProfileOperation | NullProfileOperation, result: Any) -> None:
    shape = getattr(result, "shape", None)
    if isinstance(shape, tuple) and len(shape) >= 2:
        operation.add_counter("rows", int(shape[0]))
        operation.add_counter("columns", int(shape[1]))
        return
    try:
        operation.add_counter("rows", len(result))
    except (TypeError, AttributeError):
        return


def profiled_query_call(
    name: str,
    callback: Callable[[], T],
    *,
    session: ProfileSession | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> T:
    selected = session or get_active_profile_session()
    if selected is None or not selected.enabled:
        return callback()
    with profile_query(name, session=selected, metadata=metadata) as operation:
        result = callback()
        record_tabular_result(operation, result)
        return result


def profiled_aggregate_query_call(
    name: str,
    callback: Callable[[], T],
    *,
    session: ProfileSession | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> T:
    """Agrega repeticoes da mesma consulta para limitar o tamanho do relatorio."""

    selected = session or get_active_profile_session()
    if selected is None or not selected.enabled:
        return callback()
    started_ns = time.perf_counter_ns()
    try:
        result = callback()
    except BaseException:
        selected.accumulate_event(
            category="query",
            name=name,
            duration_ns=time.perf_counter_ns() - started_ns,
            counters={"errors": 1},
            metadata=metadata,
        )
        raise
    counters: dict[str, int | float] = {}
    shape = getattr(result, "shape", None)
    if isinstance(shape, tuple) and len(shape) >= 2:
        counters.update(rows=int(shape[0]), columns=int(shape[1]))
    else:
        try:
            counters["rows"] = len(result)
        except (TypeError, AttributeError):
            pass
    selected.accumulate_event(
        category="query",
        name=name,
        duration_ns=time.perf_counter_ns() - started_ns,
        counters=counters,
        metadata=metadata,
    )
    return result


def profiled_cache_call(
    name: str,
    callback: Callable[[], T],
    cache_info: Callable[[], Any],
    *,
    session: ProfileSession | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> T:
    """Preserva o retorno do cache e agrega hit/miss somente quando habilitado."""

    selected = session or get_active_profile_session()
    if selected is None or not selected.enabled:
        return callback()
    before = cache_info()
    started_ns = time.perf_counter_ns()
    try:
        result = callback()
    except BaseException:
        selected.accumulate_event(
            category="cache",
            name=name,
            duration_ns=time.perf_counter_ns() - started_ns,
            counters={"errors": 1},
            metadata=metadata,
        )
        raise
    after = cache_info()
    selected.accumulate_event(
        category="cache",
        name=name,
        duration_ns=time.perf_counter_ns() - started_ns,
        counters={
            "hits": max(int(after.hits) - int(before.hits), 0),
            "misses": max(int(after.misses) - int(before.misses), 0),
        },
        metadata=metadata,
    )
    return result


def profiled_aggregate_operation(
    category: str,
    name: str,
    *,
    metadata: Mapping[str, Any] | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decora operacoes repetidas e publica apenas um agregado por contexto."""

    def decorator(function: Callable[..., T]) -> Callable[..., T]:
        @wraps(function)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            session = get_active_profile_session()
            if session is None:
                return function(*args, **kwargs)
            started_ns = time.perf_counter_ns()
            try:
                result = function(*args, **kwargs)
            except BaseException:
                session.accumulate_event(
                    category=category,
                    name=name,
                    duration_ns=time.perf_counter_ns() - started_ns,
                    counters={"errors": 1},
                    metadata=metadata,
                )
                raise
            session.accumulate_event(
                category=category,
                name=name,
                duration_ns=time.perf_counter_ns() - started_ns,
                counters={"completed": 1},
                metadata=metadata,
            )
            return result

        return wrapper

    return decorator


def _ensure_json_finite(value: Any, *, path: str = "root") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ProfileValidationError(f"Valor JSON nao finito em {path}.")
    if isinstance(value, Mapping):
        for key, child in value.items():
            _ensure_json_finite(child, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _ensure_json_finite(child, path=f"{path}[{index}]")


def canonical_profile_json(value: Any) -> str:
    _ensure_json_finite(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        indent=2,
        separators=(",", ": "),
    ) + "\n"


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    if temporary.exists():
        raise ProfileOutputError(f"Temporario de profile ja existe: {temporary.name}.")
    try:
        temporary.write_text(content, encoding="utf-8", newline="\n")
        os.replace(temporary, path)
    except Exception as exc:
        raise ProfileOutputError(
            f"Falha ao escrever {sanitize_profile_path(path)}: {exc}"
        ) from exc
    finally:
        if temporary.exists():
            temporary.unlink()


def write_profile_fragment(session: ProfileSession) -> Path:
    if not session.enabled or session.is_root or session.output_dir is None:
        raise ProfileValidationError("Somente subprocesso habilitado escreve fragmento.")
    fragment_path = session.output_dir / "fragments" / f"{session.run_id}.json"
    _atomic_write(fragment_path, canonical_profile_json(session.fragment_payload()))
    return fragment_path


def _load_json_strict(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda value: (_ for _ in ()).throw(
                ProfileValidationError(f"Constante nao finita: {value}.")
            ),
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ProfileValidationError) as exc:
        raise ProfileValidationError(
            f"Fragmento invalido {sanitize_profile_path(path)}: {exc}"
        ) from exc


def load_profile_fragments(session: ProfileSession) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
    if not session.enabled or not session.is_root or session.output_dir is None:
        return [], ()
    fragment_root = session.output_dir / "fragments"
    fragments: list[dict[str, Any]] = []
    if fragment_root.is_dir():
        for path in sorted(fragment_root.glob("*.json"), key=lambda item: item.name):
            payload = _load_json_strict(path)
            if not isinstance(payload, dict):
                raise ProfileValidationError(f"Fragmento deve ser objeto: {path.name}.")
            if payload.get("schemaVersion") != PROFILE_FRAGMENT_SCHEMA_VERSION:
                raise ProfileValidationError(f"Schema de fragmento invalido: {path.name}.")
            if payload.get("rootRunId") != session.root_run_id:
                raise ProfileValidationError(f"Fragmento pertence a outro run: {path.name}.")
            if payload.get("runId") != path.stem:
                raise ProfileValidationError(f"Nome de fragmento diverge do runId: {path.name}.")
            events = payload.get("events")
            if not isinstance(events, list):
                raise ProfileValidationError(f"Eventos de fragmento invalidos: {path.name}.")
            _ensure_json_finite(payload)
            fragments.append(payload)
    found = {str(fragment.get("runId")) for fragment in fragments}
    missing = tuple(sorted(set(session.expected_fragments) - found))
    return fragments, missing


def _event_sort_key(event: Mapping[str, Any]) -> tuple[str, str]:
    return str(event.get("startedAt", "")), str(event.get("eventId", ""))


def _validate_consolidated_events(events: list[dict[str, Any]]) -> None:
    identifiers = [str(event.get("eventId", "")) for event in events]
    if not all(identifiers) or len(set(identifiers)) != len(identifiers):
        raise ProfileValidationError("eventIds consolidados ausentes ou duplicados.")
    known = set(identifiers)
    for event in events:
        category = event.get("category")
        if category not in PROFILE_CATEGORIES:
            raise ProfileValidationError(f"Categoria consolidada invalida: {category!r}.")
        parent = event.get("parentEventId")
        if parent is not None and parent not in known:
            raise ProfileValidationError(
                f"Evento {event.get('eventId')} referencia pai ausente {parent}."
            )
        counters = event.get("counters", {})
        if not isinstance(counters, dict):
            raise ProfileValidationError("Counters consolidados devem ser objeto.")
        for value in counters.values():
            _numeric_counter(value)


def build_profile_summary(
    session: ProfileSession,
    events: list[dict[str, Any]],
    *,
    process_count: int,
    missing_fragments: tuple[str, ...] = (),
) -> ProfileSummary:
    category_durations: dict[str, float] = defaultdict(float)
    category_events: dict[str, int] = defaultdict(int)
    category_errors: dict[str, int] = defaultdict(int)
    category_counters: dict[str, dict[str, int | float]] = defaultdict(
        lambda: defaultdict(float)
    )
    total_counters: dict[str, int | float] = defaultdict(float)
    for event in events:
        category = str(event["category"])
        category_durations[category] += float(event.get("durationMs", 0))
        category_events[category] += 1
        if event.get("status") == "error":
            category_errors[category] += 1
        for key, value in event.get("counters", {}).items():
            numeric = _numeric_counter(value)
            category_counters[category][key] += numeric
            total_counters[key] += numeric
    categories = {
        category: {
            "durationMs": round(category_durations[category], 6),
            "eventCount": category_events[category],
            "errorCount": category_errors[category],
            "counters": {
                key: value
                for key, value in sorted(category_counters[category].items())
            },
        }
        for category in sorted(category_events)
    }
    return ProfileSummary(
        schema_version=PROFILE_SUMMARY_SCHEMA_VERSION,
        run_id=session.run_id,
        status=session.status,
        duration_ns=session.duration_ns,
        event_count=len(events),
        process_count=process_count,
        categories=categories,
        counters=total_counters,
        missing_fragments=missing_fragments,
    )


def write_profile_report(session: ProfileSession) -> tuple[Path, Path]:
    if not session.enabled or not session.is_root or session.output_dir is None:
        raise ProfileValidationError("Relatorio final exige sessao raiz habilitada.")
    if not session._finished:
        raise ProfileValidationError("Relatorio final exige sessao finalizada.")
    fragments, missing_fragments = load_profile_fragments(session)
    events = session.event_dicts()
    processes = [
        {
            "runId": session.run_id,
            "parentRunId": None,
            "command": session.command,
            "processId": session.process_id,
            "status": session.status,
        }
    ]
    for fragment in fragments:
        events.extend(fragment["events"])
        processes.append(
            {
                "runId": fragment["runId"],
                "parentRunId": fragment.get("parentRunId"),
                "command": fragment.get("command"),
                "processId": fragment.get("processId"),
                "status": fragment.get("status"),
            }
        )
    events.sort(key=_event_sort_key)
    _validate_consolidated_events(events)
    processes.sort(key=lambda item: str(item.get("runId", "")))
    summary = build_profile_summary(
        session,
        events,
        process_count=len(processes),
        missing_fragments=missing_fragments,
    )
    profile: dict[str, Any] = {
        "schemaVersion": PROFILE_SCHEMA_VERSION,
        "runId": session.run_id,
        "stateCode": session.state_code,
        "command": session.command,
        "startedAt": session.started_at,
        "finishedAt": session.finished_at,
        "durationMs": _duration_ms(session.duration_ns),
        "cpuDurationMs": _duration_ms(session.cpu_duration_ns),
        "status": session.status,
        "processId": session.process_id,
        "parameters": session.parameters,
        "environment": session.environment,
        "processes": processes,
        "events": events,
        "summary": summary.to_dict(),
    }
    if session.error_type:
        profile["errorType"] = session.error_type
    if session.error_message:
        profile["errorMessage"] = session.error_message
    profile_path = session.output_dir / "profile.json"
    summary_path = session.output_dir / "summary.json"
    _atomic_write(profile_path, canonical_profile_json(profile))
    _atomic_write(summary_path, canonical_profile_json(summary.to_dict()))
    return profile_path, summary_path


def print_profile_summary(session: ProfileSession) -> None:
    if not session.enabled:
        return
    print("\nPerfil de desempenho")
    for event in sorted(session.events, key=lambda item: item.duration_ns, reverse=True):
        print(f"  - {event.name}: {_duration_ms(event.duration_ns) / 1000:.3f}s")


def profiled_main_from_environment(command: str) -> Callable[[Callable[..., int]], Callable[..., int]]:
    """Ativa e finaliza um fragmento sem alterar o codigo de saida funcional."""

    def decorator(function: Callable[..., int]) -> Callable[..., int]:
        @wraps(function)
        def wrapper(*args: Any, **kwargs: Any) -> int:
            session = ProfileSession.from_environment(command=command)
            if not session.enabled:
                return function(*args, **kwargs)
            result = 1
            failure: BaseException | None = None
            with activate_profile_session(session):
                try:
                    with profile_step(f"{command}.total", session=session) as operation:
                        result = function(*args, **kwargs)
                        operation.add_counter("exitCode", int(result))
                        if result != 0:
                            operation.mark_error("NonZeroExit", f"exit code {result}")
                except BaseException as exc:
                    failure = exc
                    session.finish("error", exc)
                    try:
                        write_profile_fragment(session)
                    except ProfileError as profile_exc:
                        print(f"[profile] Falha ao escrever fragmento: {profile_exc}", file=sys.stderr)
                    raise
                else:
                    session.finish("success" if result == 0 else "error")
            try:
                write_profile_fragment(session)
            except ProfileError as profile_exc:
                print(f"[profile] Falha ao escrever fragmento: {profile_exc}", file=sys.stderr)
            if failure is not None:  # pragma: no cover - retorno impossivel apos raise
                raise failure
            return result

        return wrapper

    return decorator


__all__ = [
    "DEFAULT_PROFILE_ROOT",
    "PROFILE_CATEGORIES",
    "PROFILE_FRAGMENT_SCHEMA_VERSION",
    "PROFILE_SCHEMA_VERSION",
    "PROFILE_SUMMARY_SCHEMA_VERSION",
    "ProfileChildContext",
    "ProfileError",
    "ProfileEvent",
    "ProfileMetric",
    "ProfileOperation",
    "ProfileOutputError",
    "ProfileSession",
    "ProfileSummary",
    "ProfileValidationError",
    "activate_profile_session",
    "build_profile_summary",
    "canonical_profile_json",
    "get_active_profile_session",
    "load_profile_fragments",
    "new_profile_run_id",
    "print_profile_summary",
    "profile_file_operation",
    "profile_operation",
    "profile_query",
    "profile_step",
    "profiled_main_from_environment",
    "profiled_cache_call",
    "profiled_aggregate_query_call",
    "profiled_aggregate_operation",
    "profiled_query_call",
    "record_tabular_result",
    "sanitize_profile_mapping",
    "sanitize_profile_path",
    "sanitize_profile_value",
    "validate_profile_output_path",
    "write_profile_fragment",
    "write_profile_report",
]
