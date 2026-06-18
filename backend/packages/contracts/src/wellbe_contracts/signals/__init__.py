"""Contracts for the Home coverage-aware signals summary (``c13.signals.v2``).

Per docs/decisions/signals-summary-semantics.md (Spike WEL-167, approved), the
Home "signals" line is a **derived health judgment** and must be:

- **Coverage-first** — it foregrounds *what data exists* ("recent data for X of Y
  areas"), never a global/final/diagnostic "all clear".
- **Honest about missing/stale** — an area with no fresh data is ``NO_DATA``
  ("not enough current data"), never counted as in-range/green.
- **Calm/never-alarm** — no urgency is manufactured; normal/sparse data is never
  framed as a warning.
- **Confidence-honest** — confidence is a plain-language label (source + recency
  driven), not a precise-looking number.

The aggregate denominator counts ONLY areas with sufficient current data; the
``areas_total`` is shown separately so coverage is never conflated with status.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class SignalStatus(StrEnum):
    """Per-area data state — strictly coverage/recency, NOT a clinical verdict."""

    RECENT = "recent_data"  # signal-bearing data within the freshness window
    STALE = "stale_data"  # data exists but is older than the freshness window
    NO_DATA = "no_data"  # not enough current data to say anything


class ConfidenceLabel(StrEnum):
    """Plain-language confidence in an area's coverage (no false precision)."""

    GOOD = "good"
    LIMITED = "limited"
    NONE = "none"


class SignalArea(BaseModel):
    """One health area's *coverage* summary, fully source-traceable."""

    id: str
    label: str
    status: SignalStatus
    status_label: str
    confidence: ConfidenceLabel
    confidence_label: str
    last_updated: datetime | None = None
    recency_note: str
    source_count: int = 0


class SignalsSummaryV2(BaseModel):
    schema_version: Literal["c13.signals.v2"] = "c13.signals.v2"
    headline: str
    coverage_label: str
    areas_with_data: int
    areas_total: int
    areas: list[SignalArea] = Field(default_factory=list)
    note: str
    # True when coverage/confidence is too sparse to state any aggregate — the UI
    # shows the calm onboarding/learning state instead of a status line.
    suppressed: bool = False
    not_diagnosis: bool = True
