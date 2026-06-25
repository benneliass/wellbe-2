"""C1 onboarding service — account, first-run consent, and personal workspace.

Implements docs/decisions/onboarding-consent-identity-flow.md (Spike WEL-183):

  * authenticate-first: an account is the federated identity ``(issuer, subject)``
    resolved before onboarding. ``get_or_create_account`` is idempotent on that key.
  * pending-until-confirmed: ``start`` opens a *pending* onboarding session. No
    consent scope, workspace, or role binding is effective until ``finalize`` flips
    it to ``active`` on explicit final confirmation. Abandoning leaves only a draft.
  * minimal core consent: only the four core personal-workspace purposes are
    captured at first run; everything else is deferred to point-of-use.
  * atomic + idempotent finalize: re-running finalize (refresh, back button,
    at-least-once redelivery) can never create a second personal workspace,
    controller binding, or duplicate core consent row — every write is claim-first
    via ``ON CONFLICT DO NOTHING`` against the migration-021 idempotency indexes.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from wellbe_c1_consent.models import AccountRow, OnboardingSessionRow

CORE_CONSENT_VERSION = "core.v1"

# The only consent captured at first run. Everything else is point-of-use. Each is
# the controller consenting to WellBe processing *their own* data for the named core
# purpose — not a grant to any third party.
CORE_CONSENT_PURPOSES: list[dict[str, str]] = [
    {
        "purpose": "core.workspace",
        "resource_type": "workspace",
        "action": "create",
        "data_category": "account",
        "label": "Create your private personal workspace",
    },
    {
        "purpose": "core.memory",
        "resource_type": "health_memory",
        "action": "store",
        "data_category": "health_memory",
        "label": "Store and retrieve the health information you add",
    },
    {
        "purpose": "core.threads",
        "resource_type": "thread",
        "action": "process",
        "data_category": "health_memory",
        "label": "Organize what you add into your private health threads",
    },
    {
        "purpose": "core.audit",
        "resource_type": "audit",
        "action": "write",
        "data_category": "audit",
        "label": "Keep a private security and activity record only you can see",
    },
]


@dataclass(frozen=True)
class OnboardingState:
    account_id: uuid.UUID
    controller_patient_id: uuid.UUID
    status: str  # 'none' | 'pending' | 'active'
    consent_version: str
    choices: dict[str, Any]
    baseline: dict[str, Any]
    personal_workspace_id: uuid.UUID | None
    display_name: str | None


class OnboardingService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create_account(
        self,
        *,
        issuer: str,
        subject: str,
        display_name: str | None = None,
        contact_email: str | None = None,
        controller_patient_id: uuid.UUID | None = None,
    ) -> AccountRow:
        """Resolve the controller account for a federated identity, creating it if
        absent. Idempotent on (issuer, subject) — concurrent first calls converge."""
        pid = controller_patient_id or uuid.uuid4()
        await self._session.execute(
            text(
                """
                INSERT INTO identity.accounts
                    (id, issuer, subject, controller_patient_id, display_name, contact_email)
                VALUES (:id, :issuer, :subject, :pid, :display_name, :contact_email)
                ON CONFLICT (issuer, subject) DO NOTHING
                """
            ),
            {
                "id": uuid.uuid4(),
                "issuer": issuer,
                "subject": subject,
                "pid": pid,
                "display_name": display_name,
                "contact_email": contact_email,
            },
        )
        row = (
            await self._session.execute(
                select(AccountRow).where(
                    AccountRow.issuer == issuer, AccountRow.subject == subject
                )
            )
        ).scalar_one()
        return row

    async def find_account(self, *, issuer: str, subject: str) -> AccountRow | None:
        """Look up an existing account without creating one (for state reads)."""
        return (
            await self._session.execute(
                select(AccountRow).where(
                    AccountRow.issuer == issuer, AccountRow.subject == subject
                )
            )
        ).scalar_one_or_none()

    async def start(self, account: AccountRow) -> OnboardingSessionRow:
        """Open (or resume) a pending onboarding session. Idempotent per account."""
        await self._session.execute(
            text(
                """
                INSERT INTO identity.onboarding_sessions
                    (id, account_id, status, consent_version)
                VALUES (:id, :account_id, 'pending', :cv)
                ON CONFLICT (account_id) DO NOTHING
                """
            ),
            {"id": uuid.uuid4(), "account_id": account.id, "cv": CORE_CONSENT_VERSION},
        )
        return (
            await self._session.execute(
                select(OnboardingSessionRow).where(
                    OnboardingSessionRow.account_id == account.id
                )
            )
        ).scalar_one()

    async def save_draft(
        self,
        account: AccountRow,
        *,
        choices: dict[str, Any] | None = None,
        baseline: dict[str, Any] | None = None,
    ) -> OnboardingSessionRow:
        sess = await self.start(account)
        if sess.status != "pending":
            return sess
        if choices is not None:
            sess.choices = choices
        if baseline is not None:
            sess.baseline = baseline
        sess.updated_at = datetime.now(UTC)
        await self._session.flush()
        return sess

    async def finalize(self, account: AccountRow) -> OnboardingState:
        """Atomically activate the account: controller role binding, personal
        workspace, membership, and core consent rows — then flip the session to
        active. Every write is claim-first, so re-running is a safe no-op."""
        sess = await self.start(account)
        pid = account.controller_patient_id

        # 1. Controller role binding (one per actor).
        await self._session.execute(
            text(
                """
                INSERT INTO access.role_bindings
                    (id, actor_id, role_type, subject_user_id, status)
                VALUES (:id, :pid, 'individual_controller', :pid, 'active')
                ON CONFLICT (actor_id) WHERE role_type = 'individual_controller'
                DO NOTHING
                """
            ),
            {"id": uuid.uuid4(), "pid": pid},
        )
        rb_id = (
            await self._session.execute(
                text(
                    """
                    SELECT id FROM access.role_bindings
                    WHERE actor_id = :pid AND role_type = 'individual_controller'
                    """
                ),
                {"pid": pid},
            )
        ).scalar_one()

        # 2. Personal workspace (one 'individual' workspace per subject).
        await self._session.execute(
            text(
                """
                INSERT INTO workspace.workspaces
                    (id, workspace_type, controller_model, subject_user_id,
                     created_by_role_binding_id, status)
                VALUES (:id, 'individual', 'single_individual', :pid, :rb, 'active')
                ON CONFLICT (subject_user_id) WHERE workspace_type = 'individual'
                DO NOTHING
                """
            ),
            {"id": uuid.uuid4(), "pid": pid, "rb": rb_id},
        )
        ws_id = (
            await self._session.execute(
                text(
                    """
                    SELECT id FROM workspace.workspaces
                    WHERE subject_user_id = :pid AND workspace_type = 'individual'
                    """
                ),
                {"pid": pid},
            )
        ).scalar_one()

        # 3. Membership (controller in own workspace).
        await self._session.execute(
            text(
                """
                INSERT INTO workspace.workspace_memberships
                    (id, workspace_id, role_binding_id, status)
                VALUES (:id, :ws, :rb, 'active')
                ON CONFLICT (workspace_id, role_binding_id) DO NOTHING
                """
            ),
            {"id": uuid.uuid4(), "ws": ws_id, "rb": rb_id},
        )

        # 4. Core consent rows (one per (subject, resource_type, action, purpose)).
        now = datetime.now(UTC)
        for spec in CORE_CONSENT_PURPOSES:
            await self._session.execute(
                text(
                    """
                    INSERT INTO consent.consent_scopes
                        (id, subject_id, resource_type, action, data_category,
                         purpose, grant_source, valid_from, policy_version)
                    VALUES (:id, :pid, :rt, :action, :dc, :purpose, 'onboarding',
                            :valid_from, 1)
                    ON CONFLICT (subject_id, resource_type, action, purpose)
                    WHERE grant_source = 'onboarding'
                    DO NOTHING
                    """
                ),
                {
                    "id": uuid.uuid4(),
                    "pid": pid,
                    "rt": spec["resource_type"],
                    "action": spec["action"],
                    "dc": spec["data_category"],
                    "purpose": spec["purpose"],
                    "valid_from": now,
                },
            )

        # 5. Flip the session active (idempotent — only the pending->active edge).
        if sess.status == "pending":
            sess.status = "active"
            sess.finalized_at = now
            sess.updated_at = now
            await self._session.flush()

        return OnboardingState(
            account_id=account.id,
            controller_patient_id=pid,
            status="active",
            consent_version=sess.consent_version,
            choices=dict(sess.choices or {}),
            baseline=dict(sess.baseline or {}),
            personal_workspace_id=ws_id,
            display_name=account.display_name,
        )

    async def get_state(self, account: AccountRow) -> OnboardingState:
        sess = (
            await self._session.execute(
                select(OnboardingSessionRow).where(
                    OnboardingSessionRow.account_id == account.id
                )
            )
        ).scalar_one_or_none()
        ws_id: uuid.UUID | None = None
        if sess is not None and sess.status == "active":
            ws_id = (
                await self._session.execute(
                    text(
                        """
                        SELECT id FROM workspace.workspaces
                        WHERE subject_user_id = :pid AND workspace_type = 'individual'
                        """
                    ),
                    {"pid": account.controller_patient_id},
                )
            ).scalar_one_or_none()
        return OnboardingState(
            account_id=account.id,
            controller_patient_id=account.controller_patient_id,
            status=(sess.status if sess is not None else "none"),
            consent_version=(sess.consent_version if sess is not None else CORE_CONSENT_VERSION),
            choices=dict(sess.choices or {}) if sess is not None else {},
            baseline=dict(sess.baseline or {}) if sess is not None else {},
            personal_workspace_id=ws_id,
            display_name=account.display_name,
        )
