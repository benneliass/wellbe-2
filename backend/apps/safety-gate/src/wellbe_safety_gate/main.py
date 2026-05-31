"""C10 Safety & Governance Gate — isolated FastAPI service.

HARD RULES (see .cursor/rules/infra-constraints.mdc and docs/safety/safety_model.md):
- Timeout from this service → DENY output
- Any exception → DENY output
- Missing provenance → DENY output
- Diagnosis language detected → DENY output
- Panic language detected → DENY output
This service NEVER fails open.
"""
from fastapi import FastAPI
from wellbe_c10_safety import SafetyGateEvaluator
from wellbe_contracts.c10_safety import (
    C10SafetyEvaluationRequestV1,
    C10SafetyEvaluationResponseV1,
)

app = FastAPI(
    title="WellBe Safety Gate",
    version="0.1.0",
    description="Fail-closed safety gate. Must pass before any user-facing AI output is rendered.",
)

_evaluator = SafetyGateEvaluator(token_secret="local-dev-c10-render-token-secret")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/evaluate", response_model=C10SafetyEvaluationResponseV1)
async def evaluate(request: C10SafetyEvaluationRequestV1) -> C10SafetyEvaluationResponseV1:
    return _evaluator.evaluate(request)
