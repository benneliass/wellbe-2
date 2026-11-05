"""Purpose rows, binding rows, and the result a feature receives."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Literal, Protocol

FailureCode = Literal["dependency_unavailable", "invalid_output", "refused"]


@dataclass(frozen=True)
class Binding:
    """One provider. The key stays here. A purpose never carries a URL."""

    name: str
    base_url: str
    api_key: str
    model: str
    headers: tuple[tuple[str, str], ...] = ()
    require_parameters: bool = False
    include_store_false: bool = False
    require_key: bool = True
    completion_tokens: bool = False


@dataclass(frozen=True)
class Field:
    """One payload field. context stays with the check and is not sent."""

    name: str
    kind: Literal["text", "image", "context"]


Check = Callable[[object, Mapping[str, object]], bool]


@dataclass(frozen=True)
class Purpose:
    """A feature registers this. The caller does not name the feature."""

    name: str
    deadline_ms: int
    fields: tuple[Field, ...]
    kind: Literal["schema", "text"]
    instruction: str | None = None
    schema: dict[str, object] | None = None
    check: Check | None = None
    max_tokens: int = 1024


@dataclass(frozen=True)
class HttpResponse:
    status: int
    body: object
    retry_after_s: float | None = None


class Transport(Protocol):
    async def post(
        self,
        url: str,
        payload: dict[str, object],
        headers: dict[str, str],
        timeout_s: float,
    ) -> HttpResponse: ...


@dataclass(frozen=True)
class AskSuccess:
    purpose: str
    value: dict[str, object] | str
    model: str


@dataclass(frozen=True)
class AskFailure:
    purpose: str
    code: FailureCode


AskResult = AskSuccess | AskFailure
