"""C13 /v1 onboarding routes — the authenticate-first first-run flow.

Implements docs/decisions/onboarding-consent-identity-flow.md (WEL-183 / WEL-181):

  * authenticate-first: every route resolves the federated identity (issuer,
    subject) via ``IdentityDep`` — never an anonymous create.
  * pending-until-confirmed: ``start`` opens a pending draft; nothing is effective
    until ``finalize`` is called with explicit core-consent acceptance.
  * minimal core consent: only the four core purposes are presented and captured.

Personal-first: finalize provisions exactly one private personal workspace for the
controller and is fully idempotent, so a refresh/redelivery never double-creates.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field
from wellbe_c1_consent import CORE_CONSENT_PURPOSES, CORE_CONSENT_VERSION, OnboardingService
from wellbe_c1_consent.onboarding import OnboardingState
from wellbe_contracts.c13_api import ProblemCode

from wellbe_api.deps import IdentityDep, Principal, SessionDep, audit_ref
from wellbe_api.errors import ProblemError

router = APIRouter(prefix="/v1", tags=["v1-onboarding"])


class ConsentPurposeV1(BaseModel):
    purpose: str
    label: str
    resource_type: str
    action: str
    data_category: str


class OnboardingStateV1(BaseModel):
    schema_version: str = "c13.onboarding.v1"
    status: str  # 'none' | 'pending' | 'active'
    account_id: str | None = None
    controller_patient_id: str | None = None
    consent_version: str = CORE_CONSENT_VERSION
    personal_workspace_id: str | None = None
    display_name: str | None = None
    choices: dict = Field(default_factory=dict)
    baseline: dict = Field(default_factory=dict)
    core_consent: list[ConsentPurposeV1] = Field(default_factory=list)


class StartOnboardingRequest(BaseModel):
    display_name: str | None = None
    contact_email: str | None = None


class SaveDraftRequest(BaseModel):
    choices: dict | None = None
    baseline: dict | None = None


class FinalizeRequest(BaseModel):
    accept_core_consent: bool = False
    choices: dict | None = None
    baseline: dict | None = None


def _core_consent() -> list[ConsentPurposeV1]:
    return [ConsentPurposeV1(**spec) for spec in CORE_CONSENT_PURPOSES]


def _to_v1(state: OnboardingState) -> OnboardingStateV1:
    return OnboardingStateV1(
        status=state.status,
        account_id=str(state.account_id),
        controller_patient_id=str(state.controller_patient_id),
        consent_version=state.consent_version,
        personal_workspace_id=(
            str(state.personal_workspace_id) if state.personal_workspace_id else None
        ),
        display_name=state.display_name,
        choices=state.choices,
        baseline=state.baseline,
        core_consent=_core_consent(),
    )


@router.get("/onboarding", response_model=OnboardingStateV1)
async def get_onboarding(identity: IdentityDep, session: SessionDep) -> OnboardingStateV1:
    svc = OnboardingService(session)
    account = await svc.find_account(issuer=identity.issuer, subject=identity.subject)
    if account is None:
        return OnboardingStateV1(status="none", core_consent=_core_consent())
    return _to_v1(await svc.get_state(account))


@router.post("/onboarding/start", response_model=OnboardingStateV1, status_code=201)
async def start_onboarding(
    body: StartOnboardingRequest, identity: IdentityDep, session: SessionDep
) -> OnboardingStateV1:
    svc = OnboardingService(session)
    account = await svc.get_or_create_account(
        issuer=identity.issuer,
        subject=identity.subject,
        display_name=body.display_name or identity.display_name,
        contact_email=body.contact_email or identity.contact_email,
    )
    await svc.start(account)
    await session.commit()
    return _to_v1(await svc.get_state(account))


@router.patch("/onboarding", response_model=OnboardingStateV1)
async def save_onboarding_draft(
    body: SaveDraftRequest, identity: IdentityDep, session: SessionDep
) -> OnboardingStateV1:
    svc = OnboardingService(session)
    account = await svc.get_or_create_account(
        issuer=identity.issuer,
        subject=identity.subject,
        display_name=identity.display_name,
        contact_email=identity.contact_email,
    )
    await svc.save_draft(account, choices=body.choices, baseline=body.baseline)
    await session.commit()
    return _to_v1(await svc.get_state(account))


@router.post("/onboarding/finalize", response_model=OnboardingStateV1)
async def finalize_onboarding(
    body: FinalizeRequest, identity: IdentityDep, session: SessionDep
) -> OnboardingStateV1:
    if not body.accept_core_consent:
        raise ProblemError(
            status=422,
            code=ProblemCode.SCOPE_DENIED,
            title="Core consent required",
            detail="Onboarding cannot finalize without explicit core-consent acceptance.",
            correlation_id=identity.correlation_id,
        )
    svc = OnboardingService(session)
    account = await svc.get_or_create_account(
        issuer=identity.issuer,
        subject=identity.subject,
        display_name=identity.display_name,
        contact_email=identity.contact_email,
    )
    if body.choices is not None or body.baseline is not None:
        await svc.save_draft(account, choices=body.choices, baseline=body.baseline)
    state = await svc.finalize(account)

    # Audit the activation as the new controller acting on their own account.
    now = datetime.now(UTC)
    principal = Principal(
        actor_id=state.controller_patient_id,
        patient_id=state.controller_patient_id,
        actor_type="controller",
        correlation_id=identity.correlation_id,
        trace_id=identity.trace_id,
    )
    await audit_ref(
        session,
        event_type="c1.onboarding.finalized",
        principal=principal,
        summary="Onboarding finalized; personal workspace provisioned",
        extra={
            "account_id": str(state.account_id),
            "personal_workspace_id": str(state.personal_workspace_id),
            "consent_version": state.consent_version,
            "finalized_at": now.isoformat(),
        },
    )
    await session.commit()
    return _to_v1(state)
