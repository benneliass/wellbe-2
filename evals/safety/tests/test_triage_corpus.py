"""Safety Gate CI harness: triage red-flag corpus (zero false negatives).

Every ``must_route_urgent`` case must return C10 ``route_urgent``; every
``must_not_route_urgent`` case must not. Every guidance template, for every
configured region, must pass the never-alarm / do-not-diagnose filter.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from wellbe_c10_safety.triage import copy_violations, evaluate_triage
from wellbe_c10_safety.triage.copy import CRISIS_LINES, EMERGENCY_NUMBERS, TEMPLATES, render
from wellbe_contracts.triage import TriageEvaluateRequestV2

_CORPUS = json.loads(
    (Path(__file__).resolve().parents[1] / "corpora" / "triage_red_flags.json").read_text()
)


def _request(case: dict[str, Any]) -> TriageEvaluateRequestV2:
    answers = {k: v for k, v in case.items() if k != "context"}
    return TriageEvaluateRequestV2.model_validate(
        {"answers": answers, "context": case.get("context", {})}
    )


@pytest.mark.parametrize("case", _CORPUS["must_route_urgent"], ids=lambda c: c["what"][:40])
def test_zero_false_negatives_for_emergency_signs(case: dict[str, Any]) -> None:
    result = evaluate_triage(_request(case))
    assert result.safety_gate_decision == "route_urgent", case
    assert result.guidance.action


@pytest.mark.parametrize("case", _CORPUS["must_not_route_urgent"], ids=lambda c: c["what"][:40])
def test_negated_and_everyday_cases_are_not_urgent(case: dict[str, Any]) -> None:
    result = evaluate_triage(_request(case))
    assert result.safety_gate_decision != "route_urgent", (case, result.matched_rules)


@pytest.mark.parametrize("template_id", sorted(TEMPLATES))
@pytest.mark.parametrize("region", [None, *sorted(EMERGENCY_NUMBERS), *sorted(CRISIS_LINES)])
def test_guidance_copy_is_never_alarming_or_diagnostic(
    template_id: str, region: str | None
) -> None:
    guidance = render(template_id, region=region)
    for text in (guidance.headline, guidance.action, guidance.rationale, guidance.backstop):
        assert copy_violations(text) == [], (template_id, region, text)
