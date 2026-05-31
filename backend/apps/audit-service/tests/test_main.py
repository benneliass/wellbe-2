from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from wellbe_audit_service.main import app
from wellbe_contracts.c12_audit import (
    AuditActorV1,
    AuditAuthorityV1,
    AuditContextV1,
    AuditEventCreateV1,
    AuditOutcomeStatus,
    AuditOutcomeV1,
    AuditPayloadClassification,
    AuditRetentionClass,
    AuditSubjectV1,
    AuditVisibility,
)


def _audit_payload(event_type: str = "c13.output.rendered") -> dict:
    event = AuditEventCreateV1(
        event_type=event_type,
        event_version="1.0.0",
        producer_component="c13",
        producer_service="api",
        environment="test",
        occurred_at=datetime.now(UTC),
        actor=AuditActorV1(actor_type="service", actor_id_hash="hmac_sha256:api"),
        subject=AuditSubjectV1(
            patient_id_hash="hmac_sha256:patient",
            workspace_id="wrk_1",
            grant_id="grt_1",
            role_binding_id="rb_1",
            resource_type="render",
            resource_id_hash="hmac_sha256:render",
        ),
        authority=AuditAuthorityV1(
            entitlement_type="grant",
            access_predicate_hash="sha256:predicate",
            purpose_code="individual_summary",
            scope_codes=["thread.read"],
            policy_version="c1.policy.2026-06-01",
        ),
        context=AuditContextV1(correlation_id="corr-1", idempotency_key="idem-1"),
        outcome=AuditOutcomeV1(status=AuditOutcomeStatus.SUCCESS),
        payload_classification=AuditPayloadClassification.METADATA_ONLY,
        payload_min={"output_hash": "sha256:text"},
        visibility=[AuditVisibility.CONTROLLER_VISIBLE],
        retention_class=AuditRetentionClass.TRUST_LEDGER,
    )
    return event.model_dump(mode="json")


def test_health_returns_ok():
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_record_audit_event_returns_hash_chained_event():
    response = TestClient(app).post("/internal/c12/audit-events", json=_audit_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["event_id"].startswith("aud_")
    assert payload["payload_hash"].startswith("sha256:")
    assert payload["event_hash"].startswith("sha256:")
    assert payload["event_type"] == "c13.output.rendered"


def test_derive_notification_returns_none_for_blocked_output():
    payload = _audit_payload("ai_output.blocked")
    payload["authority"] = None
    payload["payload_min"] = {"candidate_output_hash": "sha256:text"}

    response = TestClient(app).post("/internal/c12/notifications/derive", json=payload)

    assert response.status_code == 200
    assert response.json() is None
