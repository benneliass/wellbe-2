"""Stable operation logs the Loki cron can fingerprint.

Emit ``event=op.start`` then ``op.ok`` / ``op.fail`` / ``op.retry`` / ``op.skip``.
Do not put PHI, tokens, or raw payloads in fields.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

EVENTS = frozenset({"op.start", "op.ok", "op.fail", "op.retry", "op.skip"})

_SAFE_KEY = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
)


def _token(value: Any) -> str:
    text = str(value).replace("\n", " ").replace("\r", " ").strip()
    return (text or "-")[:120]


def _key(name: str) -> str:
    cleaned = "".join(ch if ch in _SAFE_KEY else "_" for ch in str(name))
    return cleaned or "k"


def format_op(
    event: str,
    op: str,
    *,
    fields: Mapping[str, Any] | None = None,
) -> str:
    if event not in EVENTS:
        raise ValueError(f"unknown op event {event!r}")
    parts = [f"event={event}", f"op={_token(op)}"]
    for key, value in (fields or {}).items():
        if value is None:
            continue
        parts.append(f"{_key(key)}={_token(value)}")
    return " ".join(parts)


def log_op(
    logger: logging.Logger,
    event: str,
    op: str,
    *,
    level: int | None = None,
    fields: Mapping[str, Any] | None = None,
    exc_info: bool = False,
) -> None:
    if level is None:
        level = {
            "op.start": logging.INFO,
            "op.ok": logging.INFO,
            "op.skip": logging.INFO,
            "op.retry": logging.WARNING,
            "op.fail": logging.ERROR,
        }[event]
    logger.log(level, format_op(event, op, fields=fields), exc_info=exc_info)


@contextmanager
def op_span(
    logger: logging.Logger,
    op: str,
    *,
    fields: Mapping[str, Any] | None = None,
    start: bool = True,
) -> Iterator[dict[str, Any]]:
    extras: dict[str, Any] = dict(fields or {})
    if start:
        log_op(logger, "op.start", op, fields=extras)
    t0 = time.monotonic()
    try:
        yield extras
    except Exception as exc:
        extras.setdefault("reason", type(exc).__name__)
        extras["duration_ms"] = int((time.monotonic() - t0) * 1000)
        extras["outcome"] = "fail"
        log_op(logger, "op.fail", op, fields=extras, exc_info=True)
        raise
    extras["duration_ms"] = int((time.monotonic() - t0) * 1000)
    extras.setdefault("outcome", "ok")
    event = extras.pop("event", "op.ok")
    if event not in EVENTS:
        event = "op.ok"
    log_op(logger, event, op, fields=extras)
