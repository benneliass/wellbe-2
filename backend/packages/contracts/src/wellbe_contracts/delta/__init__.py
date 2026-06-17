"""C13 "What changed?" delta digest contracts (WEL-56).

Implements docs/decisions/delta-semantics-window.md:

- A typed, source-linked change-event stream, NOT abnormality-first ranking.
- Categories: open-loop continuity changes (C9) rank first, then lifecycle/status
  changes (C7), then new facts. Each item states its ranking reason in plain
  language and carries at least one source cue.
- The surface is a calm digest/indicator: copy says "changed", never "worse",
  unless a source explicitly supports it. No diagnosis, no alarm language.
- Window is comparison-anchored ("since" / recent); per-user "since you last
  looked" read-state persistence is deferred (tracked).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class DeltaCategory(StrEnum):
    # Highest-ranked: open loops the user is waiting on (C9).
    OPEN_LOOP = "open_loop"
    # Lifecycle/status transitions on a thread (C7).
    LIFECYCLE = "lifecycle"
    # A newly started thread / newly tracked concern.
    NEW_FACT = "new_fact"


class DeltaSourceRef(BaseModel):
    ref_type: str  # "health_thread" | "pending_item"
    source_id: str
    label: str


class DeltaEventV2(BaseModel):
    id: str
    category: DeltaCategory
    title: str
    # Plain-language reason this surfaced, e.g. "Status changed", "New result".
    ranking_reason: str
    # Optional calm detail line; never diagnostic, never "worse" by default.
    detail: str | None = None
    occurred_at: datetime
    source: DeltaSourceRef


class DeltaDigestV2(BaseModel):
    schema_version: Literal["c13.delta.v2"] = "c13.delta.v2"
    # The comparison anchor used for this digest.
    window_since: datetime | None = None
    window_label: str
    events: list[DeltaEventV2] = Field(default_factory=list)
    note: str
    not_diagnosis: bool = True


__all__ = [
    "DeltaCategory",
    "DeltaDigestV2",
    "DeltaEventV2",
    "DeltaSourceRef",
]
