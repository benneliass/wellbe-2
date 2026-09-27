"""Sanitised display names for uploaded files.

The stored value is a display name only: the last path segment, with control /
format characters removed, whitespace collapsed and length capped. It is never
used to build a filesystem path or blob key.
"""

from __future__ import annotations

import re
import unicodedata

MAX_DISPLAY_FILENAME_CHARS = 120
_MAX_EXTENSION_CHARS = 10
_WHITESPACE = re.compile(r"\s+")


def sanitize_display_filename(raw: object) -> str | None:
    """Return a safe display name for ``raw``, or ``None`` if nothing usable remains."""
    if not isinstance(raw, str):
        return None
    name = unicodedata.normalize("NFC", raw).replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(
        " " if ch.isspace() else ch
        for ch in name
        if ch.isspace() or not unicodedata.category(ch).startswith("C")
    )
    name = _WHITESPACE.sub(" ", name).strip().strip(".").strip()
    if not name:
        return None
    if len(name) <= MAX_DISPLAY_FILENAME_CHARS:
        return name
    stem, dot, ext = name.rpartition(".")
    if dot and stem and 0 < len(ext) <= _MAX_EXTENSION_CHARS:
        keep = MAX_DISPLAY_FILENAME_CHARS - len(ext) - 2
        return f"{stem[:keep].rstrip()}….{ext}"
    return name[: MAX_DISPLAY_FILENAME_CHARS - 1].rstrip() + "…"
