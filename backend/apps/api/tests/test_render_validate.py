from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from wellbe_api.main import app


def _sha256(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode()).hexdigest()}"


def _approval(text: str, *, obligations: list[dict] | None = None) -> dict:
    return {
        "schema_version": "c13.render_approval.v2",
        "render_authorization_ref": "rar_1",
        "binds_request_id": "req_1",
        "binds_text_sha256": _sha256(text),
        "expires_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
        "c10_decision": "allow_with_obligations",
        "obligations": obligations or [],
        "audit_event_id": "aud_c10_1",
    }


# These three failure paths short-circuit before any DB/audit work, so they need
# no live infrastructure. The matching-text success path emits a durable C12 audit
# event through the outbox and is therefore covered by the in-cluster E2E smoke.
_AUTH = {"X-WellBe-Actor-Id": "11111111-1111-1111-1111-111111111111"}


def test_render_validate_requires_render_approval():
    response = TestClient(app).post(
        "/v2/render/validate",
        headers=_AUTH,
        json={"text": "Safe sourced text.", "surface_capabilities": ["show_sources"]},
    )

    assert response.status_code == 428
    assert response.json()["code"] == "c10_token_required"


def test_render_validate_requires_authenticated_principal():
    response = TestClient(app).post(
        "/v2/render/validate",
        json={"text": "Safe sourced text.", "surface_capabilities": ["show_sources"]},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "unauthenticated"


def test_render_validate_blocks_hash_mismatch():
    response = TestClient(app).post(
        "/v2/render/validate",
        headers=_AUTH,
        json={
            "text": "Mutated after C10.",
            "render_approval": _approval("Original C10 text."),
            "surface_capabilities": ["show_sources"],
        },
    )

    assert response.status_code == 409
    assert response.json()["code"] == "c10_token_hash_mismatch"


def test_render_validate_blocks_unfulfilled_obligations():
    response = TestClient(app).post(
        "/v2/render/validate",
        headers=_AUTH,
        json={
            "text": "Safe sourced text.",
            "render_approval": _approval(
                "Safe sourced text.",
                obligations=[
                    {
                        "obligation_code": "show_sources",
                        "required": True,
                        "display_location": "source_panel",
                        "blocking_if_unfulfilled": True,
                    }
                ],
            ),
            "surface_capabilities": [],
        },
    )

    assert response.status_code == 409
    assert response.json()["code"] == "c10_obligations_unfulfilled"
