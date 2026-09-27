"""Deterministic triage red-flag evaluator (C10 deterministic layer, no LLM).

Routing, per the approved decision (docs/decisions/triage-escalation-safety-rules.md):

1. Every rule is evaluated against every clause of the free-text answers
   (negation-aware) and the structured onset/impact choices.
2. The route is the most urgent route of any matched rule; no match is
   ``route_routine`` with the "not all-inclusive" backstop.
3. The template is chosen by priority: crisis path > general emergency >
   pregnancy/postpartum emergency > same-day > routine.
4. Rendered copy must pass the never-alarm filter or the evaluation fails closed.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from wellbe_contracts.triage import (
    TriageEvaluateRequestV2,
    TriageEvaluateResponseV2,
    TriageMatchedRuleV2,
    TriageRoute,
)

from wellbe_c10_safety.triage.copy import TEMPLATES, render
from wellbe_c10_safety.triage.negation import Segment, affirmed, segments_for
from wellbe_c10_safety.triage.rules import (
    CLINICAL_REVIEW_STATUS,
    PREGNANCY_MENTION,
    RULES,
    RULESET_VERSION,
    RedFlagRule,
)
from wellbe_c10_safety.triage.sources import ROUTINE_SOURCE_IDS, SOURCES

TEXT_FIELDS = ("what", "change", "onset_note", "impact_note", "worry")

_ROUTE_RANK = {TriageRoute.ROUTINE: 0, TriageRoute.SOON: 1, TriageRoute.URGENT: 2}


@dataclass(frozen=True)
class _Hit:
    rule: RedFlagRule
    answer_field: str


def _segments(request: TriageEvaluateRequestV2) -> list[Segment]:
    answers = request.answers
    out: list[Segment] = []
    for name in TEXT_FIELDS:
        out.extend(segments_for(name, getattr(answers, name)))
    return out


def _is_pregnant_or_postpartum(request: TriageEvaluateRequestV2, segs: list[Segment]) -> bool:
    # Either signal is enough: an explicit "no" never hides a pregnancy mention.
    if request.context.pregnant_or_postpartum:
        return True
    return any(affirmed(PREGNANCY_MENTION, s) for s in segs)


def _match(
    rule: RedFlagRule,
    segs: list[Segment],
    request: TriageEvaluateRequestV2,
    pregnant: bool,
) -> _Hit | None:
    if rule.population == "pregnancy" and not pregnant:
        return None
    answers = request.answers
    if not rule.patterns:
        if answers.onset in rule.onset_in and answers.impact in rule.impact_in:
            return _Hit(rule, "impact")
        return None
    if rule.also_requires and not any(
        affirmed(p, s) for p in rule.also_requires for s in segs
    ):
        return None
    onset_qualifies = answers.onset in rule.qualifier_onset
    for seg in segs:
        if not any(affirmed(p, seg) for p in rule.patterns):
            continue
        if (
            not rule.qualifiers
            or onset_qualifies
            or any(affirmed(q, seg) for q in rule.qualifiers)
        ):
            return _Hit(rule, seg.answer_field)
    return None


def match_rules(request: TriageEvaluateRequestV2) -> list[_Hit]:
    segs = _segments(request)
    pregnant = _is_pregnant_or_postpartum(request, segs)
    hits = (_match(rule, segs, request, pregnant) for rule in RULES)
    return [h for h in hits if h is not None]


def _template_for(route: TriageRoute, hits: list[_Hit]) -> str:
    if route is TriageRoute.URGENT:
        urgent = [h.rule for h in hits if h.rule.route is TriageRoute.URGENT]
        if any(r.crisis for r in urgent):
            return "crisis_support.v1"
        if any(r.population == "general" for r in urgent):
            return "emergency_now.v1"
        return "pregnancy_urgent.v1"
    if route is TriageRoute.SOON:
        return "same_day.v1"
    return "routine.v1"


def evaluate_triage(
    request: TriageEvaluateRequestV2,
    *,
    default_region: str | None = None,
    now: datetime | None = None,
) -> TriageEvaluateResponseV2:
    hits = match_rules(request)
    route = max((h.rule.route for h in hits), key=_ROUTE_RANK.__getitem__, default=TriageRoute.ROUTINE)
    region = (request.context.region or default_region or "").upper() or None
    guidance = render(_template_for(route, hits), region=region)

    source_ids: list[str] = []
    for hit in hits:
        source_ids.extend(s for s in hit.rule.source_ids if s not in source_ids)
    if not hits:
        source_ids = list(ROUTINE_SOURCE_IDS)

    return TriageEvaluateResponseV2(
        evaluation_id=str(uuid.uuid4()),
        evaluated_at=now or datetime.now(UTC),
        route=route,
        safety_gate_decision=(
            "route_urgent" if route is TriageRoute.URGENT else "allow_with_obligations"
        ),
        crisis_support=any(h.rule.crisis for h in hits),
        matched_rules=[
            TriageMatchedRuleV2(
                rule_id=h.rule.rule_id,
                route=h.rule.route,
                label=h.rule.label,
                answer_field=h.answer_field,
                source_ids=list(h.rule.source_ids),
            )
            for h in hits
        ],
        guidance=guidance,
        sources=[SOURCES[s] for s in source_ids],
        jurisdiction=region or "generic",
        ruleset_version=RULESET_VERSION,
        clinical_review_status=CLINICAL_REVIEW_STATUS,
    )


def answers_sha256(request: TriageEvaluateRequestV2) -> str:
    """Hash of the answers for the audit trail (the text itself is never logged)."""
    payload = json.dumps(request.answers.model_dump(), sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def ruleset_fingerprint() -> str:
    """Stable hash of the rule set + templates; pinned in the safety-case note."""
    rules = [
        {
            "rule_id": r.rule_id,
            "route": r.route.value,
            "label": r.label,
            "sources": list(r.source_ids),
            "patterns": [p.pattern for p in r.patterns],
            "qualifiers": [q.pattern for q in r.qualifiers],
            "qualifier_onset": sorted(r.qualifier_onset),
            "also_requires": [p.pattern for p in r.also_requires],
            "onset_in": sorted(r.onset_in),
            "impact_in": sorted(r.impact_in),
            "population": r.population,
            "crisis": r.crisis,
        }
        for r in RULES
    ]
    templates = [vars(t) for t in TEMPLATES.values()]
    blob = json.dumps(
        {"version": RULESET_VERSION, "rules": rules, "templates": templates, "pregnancy": PREGNANCY_MENTION.pattern},
        sort_keys=True,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
