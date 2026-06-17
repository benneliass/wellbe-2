"""C13 Ask WellBe answer-engine contracts (WEL-166).

Implements the approved decision docs/decisions/ask-answer-engine-semantics.md:

- v1 grounds answers in a **closed personal corpus** (C7 threads + C9 pending
  items, source-linked) — no general or model latent medical knowledge.
- Every user-specific claim carries a citation (no orphan claims).
- Answer modes are first-class: a source-grounded answer, a soft refusal stating
  what *can* be answered, an out-of-scope redirect (diagnosis/treatment/etc.),
  or a calm urgent escalation. Diagnosis/treatment/management/medication
  requests are out of scope.
- The generated answer passes the C10 gate before release.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class AskMode(StrEnum):
    ANSWERED = "answered"
    NO_SOURCES = "no_sources"
    OUT_OF_SCOPE_REDIRECT = "out_of_scope_redirect"
    URGENT = "urgent"
    BLOCKED = "blocked"


class AskCitation(BaseModel):
    ref_type: str
    source_id: str
    label: str


class AskRequest(BaseModel):
    schema_version: Literal["c13.ask.request.v1"] = "c13.ask.request.v1"
    question: str = Field(min_length=1, max_length=2000)


class AskAnswerV2(BaseModel):
    schema_version: Literal["c13.ask.answer.v2"] = "c13.ask.answer.v2"
    query: str
    mode: AskMode
    answer_text: str
    citations: list[AskCitation] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    c10_decision: str | None = None
    # Always true in v1: the engine never asserts a diagnosis or draws on
    # general/latent medical knowledge.
    not_diagnosis: bool = True


__all__ = [
    "AskAnswerV2",
    "AskCitation",
    "AskMode",
    "AskRequest",
]
