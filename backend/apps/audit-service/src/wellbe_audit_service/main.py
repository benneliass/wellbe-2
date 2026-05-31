from __future__ import annotations

from fastapi import FastAPI
from wellbe_c12_audit import AuditLedger, NotificationPolicyEngine
from wellbe_contracts.c12_audit import (
    AuditEventCreateV1,
    AuditEventV1,
    NotificationWorkItemV1,
)

app = FastAPI(
    title="WellBe Audit Service",
    version="0.1.0",
    description="C12 append-only audit ledger and closure-oriented notification policy service.",
)

_ledger = AuditLedger()
_notifications = NotificationPolicyEngine()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/internal/c12/audit-events", response_model=AuditEventV1)
async def record_audit_event(event: AuditEventCreateV1) -> AuditEventV1:
    return _ledger.record(event)


@app.post("/internal/c12/notifications/derive", response_model=NotificationWorkItemV1 | None)
async def derive_notification(event: AuditEventCreateV1) -> NotificationWorkItemV1 | None:
    return _notifications.derive(event)
