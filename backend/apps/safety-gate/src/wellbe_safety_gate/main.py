"""C10 Safety & Governance Gate — isolated FastAPI service stub.

HARD RULES (see .cursor/rules/infra-constraints.mdc and docs/safety/safety_model.md):
- Timeout from this service → DENY output
- Any exception → DENY output
- Missing provenance → DENY output
- Diagnosis language detected → DENY output
- Panic language detected → DENY output
This service NEVER fails open.
"""
from fastapi import FastAPI

app = FastAPI(
    title="WellBe Safety Gate",
    version="0.1.0",
    description="Fail-closed safety gate. Must pass before any user-facing AI output is rendered.",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
