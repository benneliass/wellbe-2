from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

from wellbe_contracts.c12_audit import (
    AuditEventCreateV1,
    AuditEventV1,
    NotificationClass,
    NotificationTemplateV1,
    NotificationWorkItemV1,
)


class AuditLedger:
    """Append-only audit ledger core.

    This in-memory implementation is the contract test double for the production
    C12 writer. It deliberately exposes only append/query behavior.
    """

    def __init__(self) -> None:
        self._events: list[AuditEventV1] = []
        self._idempotency_index: dict[str, AuditEventV1] = {}

    def record(self, event: AuditEventCreateV1) -> AuditEventV1:
        if event.context.idempotency_key:
            existing = self._idempotency_index.get(event.context.idempotency_key)
            if existing is not None:
                return existing

        recorded_at = datetime.now(UTC)
        previous_hash = self._events[-1].event_hash if self._events else None
        payload_hash = _sha256(event.payload_min)
        event_hash = _sha256(
            {
                "event": event.model_dump(mode="json"),
                "payload_hash": payload_hash,
                "previous_event_hash": previous_hash,
                "recorded_at": recorded_at.isoformat(),
            }
        )
        event_data = event.model_dump()
        event_data.pop("schema_version", None)
        recorded = AuditEventV1(
            **event_data,
            event_id=f"aud_{uuid4().hex}",
            recorded_at=recorded_at,
            time_skew_ms=int((recorded_at - event.occurred_at).total_seconds() * 1000),
            payload_hash=payload_hash,
            previous_event_hash=previous_hash,
            event_hash=event_hash,
            hash_chain_scope="patient_stream" if event.subject.patient_id_hash else "global_stream",
        )
        self._events.append(recorded)
        if event.context.idempotency_key:
            self._idempotency_index[event.context.idempotency_key] = recorded
        return recorded

    def list_events(self) -> tuple[AuditEventV1, ...]:
        return tuple(self._events)


def _sha256(payload: object) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"


class NotificationPolicyEngine:
    def __init__(self) -> None:
        self._dedupe_keys: set[str] = set()
        self._templates = {
            "grant_revoked_v1": NotificationTemplateV1(
                template_id="grant_revoked_v1",
                notification_class=NotificationClass.IMMEDIATE_CLOSURE,
                rendered_copy=(
                    "Access for this workspace has been turned off. "
                    "You can review or restore sharing settings anytime."
                ),
            ),
            "external_context_digest_v1": NotificationTemplateV1(
                template_id="external_context_digest_v1",
                notification_class=NotificationClass.DIGEST,
                rendered_copy=(
                    "A new source may be useful context for your investigation. "
                    "It is not evidence about you personally."
                ),
            ),
            "pending_item_due_soon_v1": NotificationTemplateV1(
                template_id="pending_item_due_soon_v1",
                notification_class=NotificationClass.DIGEST,
                rendered_copy=(
                    "A follow-up item in your investigation is coming due. "
                    "Review it when you are ready."
                ),
            ),
        }

    def derive(self, event: AuditEventCreateV1 | AuditEventV1) -> NotificationWorkItemV1 | None:
        if event.event_type in {
            "ai_output.blocked",
            "ai_output.fail_closed",
            "ai_output.manual_review_required",
            "ai_output.rewrite_required",
        }:
            return None

        if event.event_type == "c1.grant.revoked":
            return self._work_item(event, self._templates["grant_revoked_v1"])

        if event.event_type == "c16.research_watch.source_matched":
            if not (
                event.payload_min.get("context_only") is True
                and event.payload_min.get("not_personal_evidence") is True
            ):
                return None
            return self._work_item(
                event,
                self._templates["external_context_digest_v1"],
                context_only=True,
                not_personal_evidence=True,
            )

        if event.event_type == "c14.pending_item.due_soon":
            return self._work_item(event, self._templates["pending_item_due_soon_v1"])

        return None

    def _work_item(
        self,
        event: AuditEventCreateV1 | AuditEventV1,
        template: NotificationTemplateV1,
        *,
        context_only: bool = False,
        not_personal_evidence: bool = False,
    ) -> NotificationWorkItemV1 | None:
        dedupe_key = self._dedupe_key(event, template)
        if (
            template.notification_class == NotificationClass.DIGEST
            and dedupe_key in self._dedupe_keys
        ):
            return None
        self._dedupe_keys.add(dedupe_key)
        return NotificationWorkItemV1(
            notification_id=f"ntf_{uuid4().hex}",
            source_event_type=event.event_type,
            notification_class=template.notification_class,
            template_id=template.template_id,
            rendered_copy=template.rendered_copy,
            dedupe_key=dedupe_key,
            patient_id_hash=event.subject.patient_id_hash,
            resource_id_hash=event.subject.resource_id_hash,
            context_only=context_only,
            not_personal_evidence=not_personal_evidence,
        )

    def _dedupe_key(
        self,
        event: AuditEventCreateV1 | AuditEventV1,
        template: NotificationTemplateV1,
    ) -> str:
        day_bucket = event.occurred_at.date().isoformat()
        return "|".join(
            [
                event.subject.patient_id_hash or "",
                template.notification_class,
                event.event_type.split(".", maxsplit=2)[0],
                event.subject.resource_id_hash or "",
                day_bucket,
                template.template_id,
            ]
        )
