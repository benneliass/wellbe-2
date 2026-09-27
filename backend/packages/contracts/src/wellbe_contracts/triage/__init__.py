"""C13/C10 triage check-in evaluation contract ("Something feels off").

Implements the response-routing contract of the approved decision
``docs/decisions/triage-escalation-safety-rules.md`` (WEL-162):

- A deterministic, versioned, source-linked red-flag rule set (never an LLM)
  selects the route. Each route carries source, jurisdiction, action route,
  urgency wording and a non-diagnostic rationale.
- Copy is template-only: every guidance string is pre-written and passes the
  never-alarm / do-not-diagnose filters. No free-authored escalation prose.
- Emergency and crisis numbers are locale configuration with a generalized
  default ("your local emergency number"); never hard-coded to one country.

The response never echoes the user's answers back and never names a condition,
a probability, or a treatment.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class TriageRoute(StrEnum):
    # No warning sign from the rule set matched: self-care / routine care with the
    # always-present "not all-inclusive" backstop.
    ROUTINE = "route_routine"
    # Warning signs that call for same-day clinician contact.
    SOON = "route_soon"
    # Emergency now (C10 ``route_urgent``) — the only route that may drive
    # ``state.urgent`` UI treatment.
    URGENT = "route_urgent"


class TriageAnswersV2(BaseModel):
    """The check-in answers, in the user's own words (web /triage steps)."""

    what: str = Field(min_length=1, max_length=4000)
    change: str = Field(default="", max_length=4000)
    onset: str = Field(default="", max_length=200)
    onset_note: str = Field(default="", max_length=1000)
    impact: str = Field(default="", max_length=200)
    impact_note: str = Field(default="", max_length=1000)
    worry: str = Field(default="", max_length=4000)


class TriageContextV2(BaseModel):
    # Special-population branch (pregnancy through one year postpartum). ``None``
    # means not asked; the free text is still scanned for pregnancy mentions.
    pregnant_or_postpartum: bool | None = None
    # ISO 3166-1 alpha-2 region for emergency-number substitution. Only set from
    # an explicit user/profile setting — never guessed from browser language.
    region: str | None = Field(default=None, min_length=2, max_length=2)


class TriageEvaluateRequestV2(BaseModel):
    schema_version: Literal["c13.triage.evaluate.request.v2"] = "c13.triage.evaluate.request.v2"
    answers: TriageAnswersV2
    context: TriageContextV2 = Field(default_factory=TriageContextV2)


class TriageSourceV2(BaseModel):
    source_id: str
    publisher: str
    title: str
    url: str


class TriageMatchedRuleV2(BaseModel):
    rule_id: str
    route: TriageRoute
    # Plain, non-diagnostic description of the warning sign, e.g.
    # "Chest pain, pressure or tightness". Never a condition name.
    label: str
    # Which answer the sign was found in ("what", "change", ..., or "context").
    answer_field: str
    source_ids: list[str] = Field(default_factory=list)


class TriageGuidanceV2(BaseModel):
    template_id: str
    headline: str
    # What to do next — always present, action first.
    action: str
    # Why this route appears, framed as non-diagnostic.
    rationale: str
    # The "not all-inclusive; if severe or concerning" safety net.
    backstop: str
    # Resolved emergency number, or ``None`` for the generalized default.
    emergency_number: str | None = None
    # Resolved crisis-line number when the crisis path applies and the region
    # has one configured.
    crisis_line: str | None = None


class TriageEvaluateResponseV2(BaseModel):
    schema_version: Literal["c13.triage.evaluate.v2"] = "c13.triage.evaluate.v2"
    evaluation_id: str
    evaluated_at: datetime
    route: TriageRoute
    # C10 decision for this output: ``route_urgent`` for the urgent route,
    # otherwise ``allow_with_obligations`` (display the backstop + sources).
    safety_gate_decision: Literal["route_urgent", "allow_with_obligations"]
    # Parallel mental-health crisis path (self/other-harm signs).
    crisis_support: bool = False
    matched_rules: list[TriageMatchedRuleV2] = Field(default_factory=list)
    guidance: TriageGuidanceV2
    sources: list[TriageSourceV2] = Field(default_factory=list)
    # "generic" when no region is configured, else the ISO region used.
    jurisdiction: str
    ruleset_version: str
    # The starter rule set and copy have not had clinical sign-off yet.
    clinical_review_status: Literal["pending_clinical_review", "clinically_reviewed"]
    not_diagnosis: bool = True


__all__ = [
    "TriageAnswersV2",
    "TriageContextV2",
    "TriageEvaluateRequestV2",
    "TriageEvaluateResponseV2",
    "TriageGuidanceV2",
    "TriageMatchedRuleV2",
    "TriageRoute",
    "TriageSourceV2",
]
