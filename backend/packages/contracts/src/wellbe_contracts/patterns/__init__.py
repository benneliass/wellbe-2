"""C13 non-diagnostic pattern read contracts (WEL-79).

Implements docs/decisions/pattern-detection-semantics.md:

- A surfaced pattern is a **co-occurrence candidate with mandatory caveats**,
  never a diagnosis. The strongest relation phrasing exposed corresponds to the
  `may_explain` edge ("may be related to") — never causal/diagnostic wording.
- Confidence is a **qualitative, source-linked evidence-strength tier** that
  modifies "confidence in this observed pattern" (timing/recurrence/source
  quality/association), NOT disease truth. No numeric percentage is surfaced.
- Each candidate carries explicit alternative explanations (confounder / common
  cause / reverse order / missing data) and source links (no orphan claims).
- Contradictions are surfaced as named objects and are NEVER auto-resolved.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class EvidenceTier(StrEnum):
    """Qualitative evidence strength for an *observed* pattern — not disease truth."""

    STRONGER = "stronger_signal"
    MODERATE = "moderate_signal"
    EARLY = "early_signal"


class PatternSourceRef(BaseModel):
    """A source link back to a graph node the candidate is derived from."""

    ref_type: str = "graph_node"
    source_id: str
    label: str


class PatternCandidateV2(BaseModel):
    id: str
    # Plain-language, non-diagnostic phrasing only:
    #   "appears with" | "often follows" | "may be related to" | "conflicts with"
    subject_label: str
    relation_phrase: str
    object_label: str
    # Underlying edge code, for clients that want it (never shown as causation).
    relation_code: str
    evidence_tier: EvidenceTier
    # Evidence weight in [0,1] — NOT a diagnostic probability.
    evidence_weight: float
    # Mandatory non-diagnostic caveat shown with every candidate.
    caveat: str
    # Explicit alternative explanations the user should keep in mind.
    alternative_explanations: list[str] = Field(default_factory=list)
    # Set when supporting data is sparse (missing-data engine).
    missing_data_note: str | None = None
    # Set when an endpoint is a hub that could be a common factor (confounder engine).
    confounder_note: str | None = None
    # True when this is a preserved contradiction (never auto-resolved).
    is_contradiction: bool = False
    sources: list[PatternSourceRef] = Field(default_factory=list)


class PatternsResponseV2(BaseModel):
    schema_version: Literal["c13.patterns.v2"] = "c13.patterns.v2"
    patterns: list[PatternCandidateV2] = Field(default_factory=list)
    # Shown when there is nothing to surface yet, or a global framing note.
    note: str
    not_diagnosis: bool = True


__all__ = [
    "EvidenceTier",
    "PatternCandidateV2",
    "PatternSourceRef",
    "PatternsResponseV2",
]
