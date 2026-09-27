#!/usr/bin/env python3
"""Link a federated (OIDC) identity to an existing WellBe patient — idempotent.

Makes ``identity.accounts(issuer, subject)`` resolve to ``controller_patient_id``
and finalizes C1 onboarding for that account (claim-first, so re-running is a no-op
and the patient keeps its single personal workspace). Used to map the ZITADEL
``demo`` user onto the seeded demo patient so the demo stays usable under real
login. Normal users never need this — they go through onboarding.

A patient has at most one account (``uq_account_controller_patient``). If the
patient is already bound to a *different* identity (the demo patient is bound to
the dev identity ``dev-local/dev-controller``), that account is re-bound to the
new identity only with ``--replace`` — its account id, onboarding state and
workspace are kept. An identity already bound to another patient is refused.

Needs the backend workspace on the import path (it reuses the C1 service), e.g.:

    cd backend && DATABASE_URL=postgresql://... uv run python ../scripts/ops/link_identity.py \\
        --issuer https://wellbe-auth.tail9c487a.ts.net --subject <zitadel user id> \\
        --patient-id de7a0000-0000-4000-8000-000000000001 --display-name Demo --replace

or inside the API pod (its image carries the same packages):

    kubectl -n wellbe exec -i deploy/api -- python - --issuer ... --subject ... \\
        --patient-id ... --replace < scripts/ops/link_identity.py

DATABASE_URL falls back to WELLBE_DATABASE_URL (set in the API pod).
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import uuid

from sqlalchemy import select, text
from wellbe_c1_consent import OnboardingService
from wellbe_c1_consent.models import AccountRow
from wellbe_db import create_engine, create_session_factory


class LinkError(Exception):
    pass


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL") or os.environ.get("WELLBE_DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL (or WELLBE_DATABASE_URL) is required")
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+asyncpg://" + url[len(prefix) :]
    return url


async def link(
    *,
    issuer: str,
    subject: str,
    patient_id: uuid.UUID,
    display_name: str | None,
    email: str | None,
    replace: bool,
) -> str:
    engine = create_engine(_database_url())
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            svc = OnboardingService(session)
            by_identity = await svc.find_account(issuer=issuer, subject=subject)
            by_patient = (
                await session.execute(
                    select(AccountRow).where(AccountRow.controller_patient_id == patient_id)
                )
            ).scalar_one_or_none()

            if by_identity is not None and by_identity.controller_patient_id != patient_id:
                raise LinkError(
                    f"({issuer}, {subject}) is already bound to patient "
                    f"{by_identity.controller_patient_id}; unlink it first"
                )
            if by_identity is not None:
                outcome = "unchanged"
            elif by_patient is not None:
                previous = f"({by_patient.issuer}, {by_patient.subject})"
                if not replace:
                    raise LinkError(
                        f"patient {patient_id} is bound to {previous}; pass --replace to "
                        "re-bind that account to the new identity"
                    )
                await session.execute(
                    text(
                        "UPDATE identity.accounts SET issuer = :issuer, subject = :subject, "
                        "display_name = COALESCE(:display_name, display_name), "
                        "contact_email = COALESCE(:email, contact_email), updated_at = now() "
                        "WHERE id = :id"
                    ),
                    {
                        "issuer": issuer,
                        "subject": subject,
                        "display_name": display_name,
                        "email": email,
                        "id": by_patient.id,
                    },
                )
                session.expire(by_patient)
                outcome = f"re-bound from {previous}"
            else:
                outcome = "created"

            account = await svc.get_or_create_account(
                issuer=issuer,
                subject=subject,
                display_name=display_name,
                contact_email=email,
                controller_patient_id=patient_id,
            )
            state = await svc.finalize(account)
            await session.commit()
            return (
                f"{outcome}: ({issuer}, {subject}) -> patient {state.controller_patient_id} "
                f"[account {state.account_id}, workspace {state.personal_workspace_id}]"
            )
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Link an OIDC identity to an existing WellBe patient (idempotent)."
    )
    parser.add_argument("--issuer", required=True, help="exact OIDC `iss`, no trailing slash")
    parser.add_argument("--subject", required=True, help="OIDC `sub` (ZITADEL user id)")
    parser.add_argument("--patient-id", required=True, type=uuid.UUID)
    parser.add_argument("--display-name")
    parser.add_argument("--email")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="re-bind the patient's existing account from its current identity",
    )
    args = parser.parse_args()
    try:
        print(
            asyncio.run(
                link(
                    issuer=args.issuer.rstrip("/"),
                    subject=args.subject,
                    patient_id=args.patient_id,
                    display_name=args.display_name,
                    email=args.email,
                    replace=args.replace,
                )
            )
        )
    except LinkError as err:
        sys.exit(f"link_identity: {err}")


if __name__ == "__main__":
    main()
