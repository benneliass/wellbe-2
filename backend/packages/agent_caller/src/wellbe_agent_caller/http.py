"""One HTTP post. Retries live in the caller, not in this function."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from email.message import Message

from wellbe_agent_caller.types import HttpResponse


class ConnectionFailure(Exception):
    """The socket failed before a status arrived. The message stays empty."""


def urllib_post(
    url: str,
    payload: dict[str, object],
    headers: dict[str, str],
    timeout_s: float,
) -> HttpResponse:
    body = json.dumps(payload, separators=(",", ":")).encode()
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            raw = response.read()
            status = int(getattr(response, "status", 200))
            return HttpResponse(
                status=status,
                body=_json_object(raw),
                retry_after_s=_retry_after(response.headers),
            )
    except urllib.error.HTTPError as error:
        return HttpResponse(
            status=int(error.code),
            body=_json_object(error.read()),
            retry_after_s=_retry_after(error.headers),
        )
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise ConnectionFailure from error


def _json_object(raw: bytes) -> object:
    try:
        parsed = json.loads(raw.decode())
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _retry_after(headers: Message) -> float | None:
    raw = headers.get("Retry-After")
    if raw is None:
        return None
    try:
        seconds = float(raw)
    except ValueError:
        return None
    if seconds < 0:
        return None
    return seconds
