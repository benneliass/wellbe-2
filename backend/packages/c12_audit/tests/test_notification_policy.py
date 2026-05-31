from __future__ import annotations

from datetime import UTC, datetime

from wellbe_c12_audit import NotificationPolicyEngine
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
    NotificationClass,
)


def _event(
    event_type: str,
    *,
    payload_min: dict | None = None,
    idempotency_key: str = "idem-1",
) -> AuditEventCreateV1:
    return AuditEventCreateV1(
        event_type=event_type,
        event_version="1.0.0",
        producer_component=event_type.split(".", maxsplit=1)[0],
        producer_service="test-service",
        environment="test",
        occurred_at=datetime.now(UTC),
        actor=AuditActorV1(actor_type="service", actor_id_hash="hmac_sha256:service"),
        subject=AuditSubjectV1(
            patient_id_hash="hmac_sha256:patient",
            resource_type="investigation",
            resource_id_hash="hmac_sha256:resource",
        ),
        authority=AuditAuthorityV1(
            entitlement_type="grant",
            access_predicate_hash="sha256:predicate",
            purpose_code="visit_prep",
            scope_codes=["investigation.read"],
            policy_version="c1.policy.2026-06-01",
        ),
        context=AuditContextV1(correlation_id="corr-1", idempotency_key=idempotency_key),
        outcome=AuditOutcomeV1(status=AuditOutcomeStatus.SUCCESS),
        payload_classification=AuditPayloadClassification.METADATA_ONLY,
        payload_min=payload_min or {},
        visibility=[AuditVisibility.CONTROLLER_VISIBLE],
        retention_class=AuditRetentionClass.TRUST_LEDGER,
    )


def test_grant_revoked_creates_immediate_static_closure_notification():
    notification = NotificationPolicyEngine().derive(_event("c1.grant.revoked"))

    assert notification is not None
    assert notification.notification_class == NotificationClass.IMMEDIATE_CLOSURE
    assert notification.template_id == "grant_revoked_v1"
    assert "turned off" in notification.rendered_copy
    assert "diagnosis" not in notification.rendered_copy.lower()


def test_blocked_ai_output_stays_audit_only():
    notification = NotificationPolicyEngine().derive(
        _event("ai_output.blocked", payload_min={"candidate_output_hash": "sha256:abc"})
    )

    assert notification is None


def test_external_evidence_notification_is_digest_and_context_only():
    notification = NotificationPolicyEngine().derive(
        _event(
            "c16.research_watch.source_matched",
            payload_min={
                "external_source_id": "extsrc_1",
                "source_quality_tier": "tier_1",
                "context_only": True,
                "not_personal_evidence": True,
            },
        )
    )

    assert notification is not None
    assert notification.notification_class == NotificationClass.DIGEST
    assert notification.context_only is True
    assert notification.not_personal_evidence is True
    assert "not evidence about you personally" in notification.rendered_copy


def test_digest_notifications_deduplicate_by_policy_key():
    engine = NotificationPolicyEngine()
    event = _event(
        "c14.pending_item.due_soon",
        payload_min={"template_id": "pending_item_due_soon_v1"},
    )

    first = engine.derive(event)
    duplicate = engine.derive(event)

    assert first is not None
    assert duplicate is None
