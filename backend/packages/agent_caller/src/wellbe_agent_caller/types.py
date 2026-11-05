"""Purpose rows, binding rows, and the result a feature receives."""

from __future__ import annotations

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


@dataclass(frozen=True)
class Purpose:
    """Registration data. A new purpose is another row, not another client."""

    name: str
    kind: Literal["schema", "text"]
    deadline_ms: int
    max_tokens: int
    send_fields: tuple[str, ...] = ()
    image_field: str | None = None
    media_type_field: str | None = None
    check_fields: tuple[str, ...] = ()
    schema: dict[str, object] | None = None
    checks: tuple[str, ...] = ()
    instruction: str | None = None


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
