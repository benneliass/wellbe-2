from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from wellbe_c12_audit import AuditLedger
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


def _access_event(*, idempotency_key: str = "idem-1") -> AuditEventCreateV1:
    return AuditEventCreateV1(
        event_type="c1.access.allowed",
        event_version="1.0.0",
        producer_component="c1",
        producer_service="consent-service",
        environment="test",
        occurred_at=datetime.now(UTC),
        actor=AuditActorV1(
            actor_type="user",
            actor_id_hash="hmac_sha256:actor",
            role_type="clinician",
            auth_session_id_hash="hmac_sha256:session",
        ),
        subject=AuditSubjectV1(
            patient_id_hash="hmac_sha256:patient",
            controller_user_id_hash="hmac_sha256:controller",
            workspace_id="wrk_1",
            grant_id="grt_1",
            role_binding_id="rb_1",
            resource_type="investigation",
            resource_id_hash="hmac_sha256:inv",
        ),
        authority=AuditAuthorityV1(
            entitlement_type="grant",
            access_predicate_hash="sha256:predicate",
            purpose_code="visit_prep",
            scope_codes=["investigation.read"],
            policy_version="c1.policy.2026-06-01",
        ),
        context=AuditContextV1(
            correlation_id="corr-1",
            trace_id="trace-1",
            request_id="req-1",
            idempotency_key=idempotency_key,
            client_app="wellbe-test",
        ),
        outcome=AuditOutcomeV1(status=AuditOutcomeStatus.SUCCESS, reason_codes=[]),
        payload_classification=AuditPayloadClassification.METADATA_ONLY,
        payload_min={"resource": "investigation"},
        visibility=[AuditVisibility.CONTROLLER_VISIBLE],
        retention_class=AuditRetentionClass.TRUST_LEDGER,
    )


def test_audit_event_rejects_prohibited_payloads():
    with pytest.raises(ValidationError):
        AuditEventCreateV1(
            event_type="c10.output.blocked",
            event_version="1.0.0",
            producer_component="c10",
            producer_service="safety-gate",
            environment="test",
            occurred_at=datetime.now(UTC),
            actor=AuditActorV1(actor_type="service", actor_id_hash="hmac_sha256:service"),
            subject=AuditSubjectV1(patient_id_hash="hmac_sha256:patient"),
            context=AuditContextV1(correlation_id="corr-1"),
            outcome=AuditOutcomeV1(status=AuditOutcomeStatus.REJECTED),
            payload_classification=AuditPayloadClassification.PROHIBITED,
            payload_min={"blocked_text": "You have lupus."},
            visibility=[AuditVisibility.SAFETY_REVIEW],
            retention_class=AuditRetentionClass.SAFETY,
        )


def test_access_sensitive_events_require_authority():
    event = _access_event()
    with pytest.raises(ValidationError):
        AuditEventCreateV1.model_validate({**event.model_dump(), "authority": None})


def test_ledger_records_hash_chained_event_and_replays_idempotency():
    ledger = AuditLedger()

    first = ledger.record(_access_event())
    replay = ledger.record(_access_event())
    second = ledger.record(_access_event(idempotency_key="idem-2"))

    assert replay.event_id == first.event_id
    assert first.payload_hash.startswith("sha256:")
    assert first.event_hash.startswith("sha256:")
    assert first.recorded_at >= first.occurred_at
    assert first.previous_event_hash is None
    assert second.previous_event_hash == first.event_hash
    assert second.event_hash != first.event_hash


def test_ledger_exposes_no_update_or_delete_api():
    ledger = AuditLedger()

    assert not hasattr(ledger, "update")
    assert not hasattr(ledger, "delete")
    assert not hasattr(ledger, "truncate")
