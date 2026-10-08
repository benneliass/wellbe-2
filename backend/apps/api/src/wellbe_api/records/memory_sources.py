"""Load the original vault wording behind a memory's fact pointers.

C8 stores pointers, not the raw capture. Opening a memory reads the vault event
those facts came from and returns that text (manual captures) or a short note
that a file was kept unchanged (everything else — never the raw bytes).
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from wellbe_contracts.c13_api import MemorySourceTextV2

_FACT_IDS = ARRAY(UUID(as_uuid=True))
_MAX_CHARS = 8000
_FILE_KEPT = "This file was kept unchanged."


def text_for_event(
    *,
    source_type: str,
    original_filename: str | None,
    content: bytes | str | None,
) -> tuple[str, str]:
    """Return ``(label, text)`` for one vault event.

    Manual text is decoded and capped at 8000 characters. A file capture is not
    dumped: the label is the original filename (or "What you added") and the
    text only says the file was kept unchanged. A published sample case uses
    its first line as the label.
    """
    if source_type != "manual_text":
        name = (original_filename or "").strip()
        return name or "What you added", _FILE_KEPT

    raw = content.decode("utf-8", errors="replace") if isinstance(content, bytes) else content or ""
    body = raw[:_MAX_CHARS]
    first = body.split("\n", 1)[0].strip()
    if first.startswith("Published sample case"):
        return first, body
    return "What you added", body


async def source_texts_for_facts(
    session: Any,
    *,
    patient_id: uuid.UUID,
    fact_ids: Sequence[uuid.UUID],
    fetch_text: Callable[[uuid.UUID], Awaitable[bytes | str | None]],
) -> list[MemorySourceTextV2]:
    """Join facts to vault events for this patient, then load manual text.

    ``fetch_text`` is called only for ``manual_text`` events. A ``None`` result
    drops that event's wording; the caller still returns the memories.
    """
    if not fact_ids:
        return []
    statement = text(
        "SELECT f.id AS fact_id, e.id AS event_id, e.source_type, "
        "e.original_filename "
        "FROM processing.extracted_facts AS f "
        "JOIN vault.raw_context_events AS e "
        "ON e.id = f.raw_context_event_id "
        "WHERE f.patient_id = :patient_id "
        "AND f.id = ANY(:fact_ids)"
    ).bindparams(bindparam("fact_ids", type_=_FACT_IDS))
    result = await session.execute(
        statement,
        {"patient_id": patient_id, "fact_ids": list(fact_ids)},
    )
    by_fact = {row.fact_id: row for row in result}
    loaded: dict[uuid.UUID, tuple[str, str] | None] = {}
    out: list[MemorySourceTextV2] = []
    seen: set[str] = set()
    for fact_id in fact_ids:
        row = by_fact.get(fact_id)
        if row is None:
            continue
        event_id = row.event_id
        if event_id not in loaded:
            content: bytes | str | None = None
            if row.source_type == "manual_text":
                content = await fetch_text(event_id)
                if content is None:
                    loaded[event_id] = None
                    continue
            loaded[event_id] = text_for_event(
                source_type=row.source_type,
                original_filename=row.original_filename,
                content=content,
            )
        rendered = loaded[event_id]
        if rendered is None:
            continue
        label, body = rendered
        ref_id = str(fact_id)
        if ref_id in seen:
            continue
        seen.add(ref_id)
        out.append(
            MemorySourceTextV2(
                source_ref_type="c4_extracted_fact",
                source_ref_id=ref_id,
                label=label,
                text=body,
            )
        )
    return out
