"""C13 /v2 triage check-in evaluation ("Something feels off").

Runs the deterministic C10 red-flag rule set over the check-in answers and
returns a route (routine / same-day / urgent) with pre-written, source-linked,
non-diagnostic guidance. See docs/decisions/triage-escalation-safety-rules.md and
docs/safety/triage-red-flag-ruleset.md. Nothing is stored except the audit event,
which carries the route, rule ids and a hash of the answers — never the text.
"""

from __future__ import annotations

from fastapi import APIRouter
from wellbe_c10_safety.triage import answers_sha256, evaluate_triage
from wellbe_contracts.triage import TriageEvaluateRequestV2, TriageEvaluateResponseV2

from wellbe_api.config import ApiSettings
from wellbe_api.deps import PrincipalDep, SessionDep, audit_ref, require_access

router = APIRouter(prefix="/v2", tags=["v2-triage"])

_RESOURCE = "raw_context"
_settings = ApiSettings()


@router.post("/triage/evaluate", response_model=TriageEvaluateResponseV2)
async def evaluate_check_in(
    body: TriageEvaluateRequestV2, principal: PrincipalDep, session: SessionDep
) -> TriageEvaluateResponseV2:
    await require_access(principal, session, action="write", resource_type=_RESOURCE)

    result = evaluate_triage(body, default_region=_settings.triage_default_region)

    await audit_ref(
        session,
        event_type="c13.triage.evaluated",
        principal=principal,
        summary=f"Triage check-in evaluated ({result.route.value})",
        extra={
            "evaluation_id": result.evaluation_id,
            "route": result.route.value,
            "c10_decision": result.safety_gate_decision,
            "c10_event": (
                "ai_output.routed_urgent"
                if result.safety_gate_decision == "route_urgent"
                else "ai_output.allowed_with_obligations"
            ),
            "crisis_support": result.crisis_support,
            "rule_ids": [r.rule_id for r in result.matched_rules],
            "template_id": result.guidance.template_id,
            "ruleset_version": result.ruleset_version,
            "clinical_review_status": result.clinical_review_status,
            "jurisdiction": result.jurisdiction,
            "answers_sha256": answers_sha256(body),
        },
    )
    await session.commit()
    return result
