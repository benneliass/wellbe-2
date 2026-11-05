"""One vision transcription per content hash.

The vault file stays the original. This cache is not a context-brain table.
"""

from __future__ import annotations

import hashlib

_stored: dict[str, str] = {}


def content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def recall(content: bytes) -> str | None:
    return _stored.get(content_hash(content))


def remember(content: bytes, text: str) -> None:
    _stored[content_hash(content)] = text


def clear() -> None:
    _stored.clear()
