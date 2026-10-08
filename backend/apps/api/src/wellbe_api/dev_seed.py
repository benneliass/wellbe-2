"""Deterministic Dev-workspace seed (local kind only).

Loads a fixed, committed dataset for a single well-known dev controller so the
local cluster comes up with a populated workspace instead of an empty sign-in
state. It drives the **public C13 API over HTTP** (the same contract the web app
uses) rather than writing the database directly, so the seed exercises the real
pipelines and can never drift from the production write contract.

Design principle — seed *inputs and user actions*, never fabricated derived state
==================================================================================
A seed that hand-creates derived objects (e.g. ``POST /v1/threads`` with invented
titles) does not test the system; it bypasses it. WellBe's signature behaviour is
that Health Threads are *born from the pipeline*: a capture is processed into facts
→ a knowledge-graph node → a genesis decision that either auto-opens a thread or
proposes a "thing noticed" candidate, which the user then confirms into a thread.

So this seed only ever:

1. **Injects inputs** — one note per published Research C case through
   ``POST /v1/capture``. These flow through the real C3→C2→C4→C5→C6→genesis
   pipeline asynchronously. The note text is the published case wording; the
   ``source`` is ``published-case:{id}`` so genesis can keep each case on its
   own concern key.
2. **Performs user actions** — when ``CANDIDATE_PLAN`` is empty, confirms every
   pending candidate once and walks it to ``active_unresolved``. Candidates that
   are already confirmed are skipped. No candidate is dismissed, and no
   investigation or visit packet is invented.

Everything else (facts, evidence, graph nodes, candidate creation, thread genesis,
audit) is produced by the system, exactly as in production. The resulting threads
are real: evidence/concern-key-backed and dedup-aware, not invented titles.

Known pipeline limitation (intentionally *not* faked here)
---------------------------------------------------------
With the current MVP extractor, no capture yields a ``finding``/``dx_mention`` fact
or a flagged-abnormal lab, so genesis never takes its high-confidence
``CREATE_NEW_THREAD`` auto-open path — every capture becomes a candidate. The seed
therefore demonstrates the *candidate → confirm* path (the reachable one) and does
not pretend an auto-open happened. See the genesis-pipeline gap ticket.

Guarantees
----------
- **Dev-only.** Runs only when ``WELLBE_DEV_SEED_ENABLED=true``; the Helm Job that
  invokes it is gated behind ``devSeed.enabled`` (local/homeserver charts only).
- **Revision-aware + idempotent.** A marker row records the applied ``SEED_REVISION``.
  When it already matches, the run is a no-op (safe on every ``helm upgrade``). When
  it differs (a new seed revision shipped), the dev workspace's data is reset and
  re-seeded so the committed dataset is exactly reproduced. Captures additionally use
  deterministic ``Idempotency-Key`` values, so even a forced replay cannot create
  duplicate raw records.
- **No reset until the API accepts the seed.** ``/health`` is unauthenticated, so a
  healthy OIDC pod is not proof the seed can write. The run waits until
  ``GET /v1/threads`` with the dev identity headers returns 200, and only then
  reads the marker or truncates. A 401 leaves patient data untouched.
- **Self-contained data.** Published case wording lives in ``published_cases``;
  this file only lists the captures and the (currently empty) user-action plan.

The dev identity is the controller acting on their own data (actor_id ==
patient_id, actor_type "controller"), which the boundary grants self-access to
without any pre-existing grant rows (see resolve_principal / require_access).
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from typing import Any, cast

import httpx
from sqlalchemy import text
from wellbe_c1_consent import OnboardingService
from wellbe_db import create_engine, create_session_factory

from wellbe_api.config import ApiSettings
from wellbe_api.published_cases import PUBLISHED_CASES

logger = logging.getLogger("wellbe.dev_seed")

# Bump this whenever the committed dataset or the seeding flow changes. On the next
# run the marker mismatch triggers a one-time reset + re-seed of the dev workspace
# so the cluster reflects the new dataset (rather than the idempotent no-op).
SEED_REVISION = "4-published-cases"

# The dev identity is a real federated identity, just like any user's. It is one
# selectable workspace — never auto-entered. The web "Dev workspace" sign-in uses
# exactly this (issuer, subject); its account maps to the seeded patient id.
DEV_ISSUER = "dev-local"
DEV_SUBJECT = "dev-controller"

# Namespace for deterministic capture Idempotency-Keys. Fixed so repeated runs
# map the same logical capture to the same key.
_SEED_NS = uuid.UUID("5f3b1d22-0c47-4a8e-9b6f-7c2d4e1a9f00")


# ---------------------------------------------------------------------------
# 1) INPUTS — one published Research C case per note.
#
# The note body is the published wording (no invented labs, quotes, or
# outcomes). ``source`` is what genesis uses to keep two cases from sharing a
# thread. Thread titles still come from the extractor, not the case title.
# ---------------------------------------------------------------------------
CAPTURES: list[dict[str, Any]] = [
    {
        "capture_type": "note",
        "source": f"published-case:{case['case_id']}",
        "payload": {"text": case["text"]},
    }
    for case in PUBLISHED_CASES
]


# ---------------------------------------------------------------------------
# 2) USER ACTIONS — what the controller does with what genesis surfaced.
#
# An empty plan means: confirm every pending candidate once, then walk it with
# ``CONFIRM_WALK``. Nothing is dismissed. A non-empty plan keeps the keyword
# rules (confirm / dismiss / leave) for tests and any future curated dataset.
# ---------------------------------------------------------------------------
CANDIDATE_PLAN: list[dict[str, Any]] = []
CONFIRM_WALK: list[str] = ["active_unresolved"]

# No invented investigation or visit packet. Empty link lists make both seeders
# return without writing.
INVESTIGATION: dict[str, Any] = {
    "primary_question": "",
    "link_threads": [],
    "theory": None,
}
VISIT_PACKET: dict[str, Any] = {
    "title": "",
    "link_threads": [],
    "include_summary": False,
}


def _capture_idempotency_key(index: int, capture: dict[str, Any]) -> str:
    """Deterministic key so a replay maps to the same raw record."""
    items = sorted(capture["payload"].items())
    source = capture.get("source") or ""
    natural = f"{index}:{capture['capture_type']}:{source}:{items!r}"
    return str(uuid.uuid5(_SEED_NS, natural))


def _headers(patient_id: str, *, idempotency_key: str | None = None) -> dict[str, str]:
    headers = {
        "X-Wellbe-Actor-Id": patient_id,
        "X-Wellbe-Patient-Id": patient_id,
        "X-Wellbe-Actor-Type": "controller",
        "X-Correlation-Id": f"dev-seed-{uuid.uuid4().hex[:12]}",
    }
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    return headers


async def _wait_for_api(client: httpx.AsyncClient, *, attempts: int = 60) -> None:
    """Block until the API answers /health (the Job may start before the pod)."""
    for attempt in range(1, attempts + 1):
        try:
            resp = await client.get("/health", timeout=5.0)
            if resp.status_code == 200:
                logger.info("API reachable after %d attempt(s)", attempt)
                return
        except httpx.HTTPError:
            pass
        await asyncio.sleep(2.0)
    raise RuntimeError("API never became reachable; aborting dev seed")


async def _wait_for_dev_header_access(
    client: httpx.AsyncClient, patient_id: str, *, attempts: int = 60
) -> None:
    """Block until this API trusts the seed's dev identity headers.

    /health succeeds on an OIDC pod. Truncating before a patient route accepts
    X-Wellbe-* headers wipes the workspace and then fails the reseed with 401.
    A persistent 401 aborts with patient data still in place. Any other HTTP
    error fails immediately; connection errors retry, same as /health.
    """
    last_status: int | None = None
    for attempt in range(1, attempts + 1):
        try:
            resp = await client.get("/v1/threads", headers=_headers(patient_id), timeout=10.0)
        except httpx.HTTPError:
            await asyncio.sleep(2.0)
            continue
        if resp.status_code == 200:
            logger.info("API accepted dev headers after %d attempt(s)", attempt)
            return
        last_status = resp.status_code
        if resp.status_code != 401:
            resp.raise_for_status()
        logger.info("API still rejecting dev headers (401); attempt %d/%d", attempt, attempts)
        await asyncio.sleep(2.0)
    raise RuntimeError(
        "API did not accept dev headers "
        f"(last status {last_status}). Refusing to reset patient data. "
        "Set auth.mode to dev-headers, wait until the new API pods are serving, then rerun."
    )


async def _seed_captures(client: httpx.AsyncClient, patient_id: str) -> int:
    created = 0
    for index, capture in enumerate(CAPTURES):
        key = _capture_idempotency_key(index, capture)
        body: dict[str, Any] = {
            "capture_type": capture["capture_type"],
            "payload": capture["payload"],
        }
        if capture.get("source"):
            body["source"] = capture["source"]
        resp = await client.post(
            "/v1/capture",
            headers=_headers(patient_id, idempotency_key=key),
            json=body,
        )
        resp.raise_for_status()
        created += 1
        logger.info("captured %s (%s)", resp.json()["capture_id"], capture["capture_type"])
    return created


async def _wait_for_candidates(
    client: httpx.AsyncClient, patient_id: str, *, min_count: int, attempts: int = 45
) -> list[dict[str, Any]]:
    """Poll until genesis has surfaced candidates and the count is stable.

    Genesis runs asynchronously off the outbox, so candidates appear a few seconds
    after the captures land. We wait until at least ``min_count`` exist and the
    count has not changed across two consecutive polls (so a partially-processed
    batch is not acted on)."""
    previous = -1
    for _ in range(attempts):
        resp = await client.get("/v1/things-noticed", headers=_headers(patient_id))
        resp.raise_for_status()
        candidates = cast(list[dict[str, Any]], resp.json())
        count = len(candidates)
        if count >= min_count and count == previous:
            logger.info("genesis surfaced %d candidate(s)", count)
            return candidates
        previous = count
        await asyncio.sleep(2.0)
    # Best effort: return whatever exists rather than hanging the seed forever.
    resp = await client.get("/v1/things-noticed", headers=_headers(patient_id))
    resp.raise_for_status()
    logger.warning("candidate count did not stabilize; proceeding with what exists")
    return cast(list[dict[str, Any]], resp.json())


def _match_candidate(candidates: list[dict[str, Any]], keyword: str) -> dict[str, Any] | None:
    kw = keyword.lower()
    for c in candidates:
        if c.get("status") == "pending" and kw in (c.get("title") or "").lower():
            return c
    return None


async def _walk_thread(
    client: httpx.AsyncClient, patient_id: str, thread_id: str, walk: list[str]
) -> None:
    """Apply an ordered lifecycle walk to a freshly-confirmed thread.

    Best-effort: a transition that the state machine rejects (e.g. because the
    confirmed thread did not start where we assumed) is logged and skipped rather
    than failing the whole seed."""
    for target in walk:
        resp = await client.post(
            f"/v1/threads/{thread_id}/transition",
            headers=_headers(patient_id),
            json={"target_status": target, "reason_code": "dev_seed"},
        )
        if resp.status_code >= 400:
            logger.warning(
                "skip transition %s -> %s (%s): %s",
                thread_id,
                target,
                resp.status_code,
                resp.text[:160],
            )
            return
        logger.info("  transitioned %s -> %s", thread_id, target)


async def _confirm_pending(
    client: httpx.AsyncClient,
    patient_id: str,
    candidate: dict[str, Any],
    walk: list[str],
) -> str | None:
    """Confirm one pending candidate and walk the new thread. Already-confirmed is a skip."""
    cid = candidate["candidate_id"]
    resp = await client.post(f"/v1/things-noticed/{cid}/confirm", headers=_headers(patient_id))
    if resp.status_code == 409:
        logger.info("candidate %s already confirmed; skipping", cid)
        return None
    resp.raise_for_status()
    thread_id = str(resp.json()["thread_id"])
    logger.info("confirmed '%s' -> thread %s", candidate.get("title"), thread_id)
    await _walk_thread(client, patient_id, thread_id, walk)
    return thread_id


async def _act_on_candidates(
    client: httpx.AsyncClient, patient_id: str, candidates: list[dict[str, Any]]
) -> dict[str, str]:
    """Confirm genesis candidates; return {keyword: thread_id} for confirmations.

    An empty ``CANDIDATE_PLAN`` confirms every still-pending candidate once and
    walks it with ``CONFIRM_WALK``. Nothing is dismissed.

    When a plan is set, ``candidates`` is a snapshot and each candidate is claimed
    by the first rule that matches it: a later, broader keyword ("pain") must not
    re-act on a candidate an earlier rule ("knee") already confirmed, which the
    API rejects with 409.
    """
    confirmed: dict[str, str] = {}
    if not CANDIDATE_PLAN:
        for candidate in candidates:
            if candidate.get("status") != "pending":
                continue
            thread_id = await _confirm_pending(client, patient_id, candidate, list(CONFIRM_WALK))
            if thread_id is None:
                continue
            confirmed[str(candidate["candidate_id"])] = thread_id
        return confirmed

    for rule in CANDIDATE_PLAN:
        keyword = str(rule["match"])
        # Own name: the loop above already bound `candidate` as a confirmed dict.
        matched = _match_candidate(candidates, keyword)
        if matched is None:
            logger.info("no pending candidate matched '%s'; skipping", keyword)
            continue
        cid = matched["candidate_id"]
        action = rule["action"]
        matched["status"] = "claimed_by_seed"
        if action == "confirm":
            thread_id = await _confirm_pending(
                client, patient_id, matched, list(rule.get("walk") or [])
            )
            if thread_id is not None:
                confirmed[keyword] = thread_id
        elif action == "dismiss":
            resp = await client.post(
                f"/v1/things-noticed/{cid}/dismiss", headers=_headers(patient_id)
            )
            resp.raise_for_status()
            logger.info("dismissed '%s'", matched["title"])
        else:  # leave
            logger.info("left '%s' pending", matched["title"])
    return confirmed


async def _seed_investigation(
    client: httpx.AsyncClient, patient_id: str, confirmed: dict[str, str]
) -> None:
    link_threads: list[str] = list(INVESTIGATION["link_threads"])
    if not link_threads:
        return
    thread_ids = [confirmed[k] for k in link_threads if k in confirmed]
    resp = await client.post(
        "/v2/investigations",
        headers=_headers(patient_id),
        json={
            "primary_question": INVESTIGATION["primary_question"],
            "thread_ids": thread_ids,
        },
    )
    resp.raise_for_status()
    investigation_id = resp.json()["investigation_id"]
    logger.info("created investigation %s (%d thread link(s))", investigation_id, len(thread_ids))

    theory = INVESTIGATION["theory"]
    resp = await client.post(
        f"/v2/investigations/{investigation_id}/theories",
        headers=_headers(patient_id),
        json={
            "theory_text": theory["theory_text"],
            "theory_type": theory["theory_type"],
        },
    )
    resp.raise_for_status()
    logger.info("recorded theory on investigation %s", investigation_id)


async def _seed_visit_packet(
    client: httpx.AsyncClient, patient_id: str, confirmed: dict[str, str]
) -> None:
    link_threads: list[str] = VISIT_PACKET["link_threads"]
    thread_ids = [confirmed[k] for k in link_threads if k in confirmed]
    if not thread_ids:
        logger.info("no confirmed threads to build a visit packet from; skipping")
        return
    resp = await client.post(
        "/v2/visit-packets",
        headers=_headers(patient_id),
        json={
            "title": VISIT_PACKET["title"],
            "thread_ids": thread_ids,
            "include_summary": VISIT_PACKET["include_summary"],
        },
    )
    resp.raise_for_status()
    logger.info("built visit packet %s (%d thread(s))", resp.json()["packet_id"], len(thread_ids))


# ---------------------------------------------------------------------------
# Account + revision marker + reset (direct DB; dev-only).
# ---------------------------------------------------------------------------

# Data tables cleared on a revision change. TRUNCATE ... CASCADE clears dependent
# child tables (transitions, candidates, evidence, statements, …) automatically and
# never touches lookup/reference tables (they are referenced-by, not referencing).
# Identity / workspace / access rows are intentionally preserved — the account and
# personal workspace persist; Onboarding.get_or_create handles them idempotently.
_RESET_TABLES = (
    "vault.raw_context_events",
    "processing.extracted_facts",
    "processing.health_signals",
    "evidence.evidence_links",
    "graph.kg_nodes",
    "graph.kg_edges",
    "thread.health_threads",
    "genesis.genesis_decisions",
    "genesis.thread_candidates",
    "c8.memory_entries",
    "c9.pending_items",
    "c14.investigations",
    "c15.theories",
    "c11.corrections",
    "visit_packet.packets",
    "events.outbox_events",
)


def _patient_has_other_account(issuer: str | None, subject: str | None) -> bool:
    """True when this patient is already owned by an identity other than the dev seed.

    A patient has at most one controller account. The homeserver demo user is that
    account. Inserting dev-local / dev-controller for the same patient raises, and
    the seed used to die there. Leaving the existing account in place lets the
    captures land on the patient Try the demo already opens.
    """
    if issuer is None:
        return False
    return (issuer, subject) != (DEV_ISSUER, DEV_SUBJECT)


async def _seed_dev_account(patient_id: uuid.UUID) -> None:
    """Provision the dev identity's account + personal workspace (idempotent)."""
    settings = ApiSettings()
    engine = create_engine(settings.database_url.get_secret_value())
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            existing = (
                await session.execute(
                    text(
                        "SELECT issuer, subject FROM identity.accounts "
                        "WHERE controller_patient_id = :pid"
                    ),
                    {"pid": patient_id},
                )
            ).first()
            if existing is not None and _patient_has_other_account(existing[0], existing[1]):
                logger.info(
                    "patient %s already has account (%s, %s); leaving it in place",
                    patient_id,
                    existing[0],
                    existing[1],
                )
                return
            svc = OnboardingService(session)
            account = await svc.get_or_create_account(
                issuer=DEV_ISSUER,
                subject=DEV_SUBJECT,
                display_name="Dev workspace",
                controller_patient_id=patient_id,
            )
            await svc.finalize(account)
            await session.commit()
        logger.info("dev account provisioned (issuer=%s subject=%s)", DEV_ISSUER, DEV_SUBJECT)
    finally:
        await engine.dispose()


async def _read_seed_revision() -> str | None:
    settings = ApiSettings()
    engine = create_engine(settings.database_url.get_secret_value())
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            await session.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS public.dev_seed_marker "
                    "(id int PRIMARY KEY DEFAULT 1, revision text NOT NULL, "
                    "applied_at timestamptz NOT NULL DEFAULT now())"
                )
            )
            await session.commit()
            result = await session.execute(
                text("SELECT revision FROM public.dev_seed_marker WHERE id = 1")
            )
            row = result.first()
            return row[0] if row else None
    finally:
        await engine.dispose()


async def _write_seed_revision(revision: str) -> None:
    settings = ApiSettings()
    engine = create_engine(settings.database_url.get_secret_value())
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            await session.execute(
                text(
                    "INSERT INTO public.dev_seed_marker (id, revision, applied_at) "
                    "VALUES (1, :rev, now()) "
                    "ON CONFLICT (id) DO UPDATE SET revision = :rev, applied_at = now()"
                ),
                {"rev": revision},
            )
            await session.commit()
    finally:
        await engine.dispose()


async def _reset_dev_data() -> None:
    """Clear the dev workspace's patient data so a new revision re-seeds cleanly.

    Dev-only (the caller is already behind WELLBE_DEV_SEED_ENABLED). TRUNCATE with
    CASCADE makes table order irrelevant and resets identity sequences."""
    settings = ApiSettings()
    engine = create_engine(settings.database_url.get_secret_value())
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            # Only truncate tables that actually exist, so schema drift between the
            # seed image and the migrated DB never fails the whole reset. The table
            # list is a trusted in-module constant (no injection surface).
            literals = ",".join(f"'{t}'" for t in _RESET_TABLES)
            result = await session.execute(
                text(
                    f"SELECT n FROM unnest(ARRAY[{literals}]) AS n WHERE to_regclass(n) IS NOT NULL"
                )
            )
            existing = [row[0] for row in result]
            if not existing:
                logger.info("no dev data tables present; reset is a no-op")
                return
            await session.execute(
                text("TRUNCATE TABLE " + ", ".join(existing) + " RESTART IDENTITY CASCADE")
            )
            await session.commit()
        logger.info("dev workspace data reset (%d tables)", len(existing))
    finally:
        await engine.dispose()


async def seed() -> None:
    if os.environ.get("WELLBE_DEV_SEED_ENABLED", "").lower() != "true":
        logger.info("WELLBE_DEV_SEED_ENABLED is not 'true'; skipping dev seed")
        return

    patient_id = os.environ.get("WELLBE_DEV_PATIENT_ID")
    if not patient_id:
        raise RuntimeError("WELLBE_DEV_PATIENT_ID is required when dev seed is enabled")
    patient_uuid = uuid.UUID(patient_id)  # validate early

    base_url = os.environ.get("WELLBE_DEV_SEED_API_BASE", "http://api:8001")
    logger.info(
        "dev seed starting (patient=%s, api=%s, revision=%s)",
        patient_id,
        base_url,
        SEED_REVISION,
    )

    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        await _wait_for_api(client)
        # Prove the serving pods trust dev headers before any database write.
        # A revision mismatch truncates patient tables; doing that against an
        # OIDC pod deletes the workspace and then fails the reseed.
        await _wait_for_dev_header_access(client, patient_id)

        # Ensure the dev account exists (cheap + idempotent) so the "Dev
        # workspace" sign-in works even when the dataset seed is a no-op.
        await _seed_dev_account(patient_uuid)

        current = await _read_seed_revision()
        if current == SEED_REVISION:
            logger.info("dev workspace already at revision %s; seed is a no-op", SEED_REVISION)
            return
        # Any other state — no marker yet, or an older revision — means the workspace is
        # not at the committed dataset (e.g. legacy/hand-seeded data). Reset first so the
        # seed reproduces the dataset exactly. On a truly fresh cluster the tables are
        # empty and the reset is a harmless no-op.
        logger.info("seed revision %s -> %s; resetting dev workspace", current, SEED_REVISION)
        await _reset_dev_data()

        captures = await _seed_captures(client, patient_id)
        # Expect roughly one candidate per concern; wait for the batch to settle.
        candidates = await _wait_for_candidates(client, patient_id, min_count=max(1, captures - 3))
        confirmed = await _act_on_candidates(client, patient_id, candidates)
        await _seed_investigation(client, patient_id, confirmed)
        await _seed_visit_packet(client, patient_id, confirmed)
        logger.info(
            "dev seed complete: %d captures, %d threads confirmed", captures, len(confirmed)
        )

    await _write_seed_revision(SEED_REVISION)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(seed())


if __name__ == "__main__":
    main()
