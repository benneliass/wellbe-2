"""Deterministic Dev-workspace seed (local kind only).

Loads a fixed, committed dataset for a single well-known dev controller so the
local cluster comes up with a populated workspace instead of an empty sign-in
state. It drives the **public C13 API over HTTP** (same contract the web app
uses) rather than writing the database directly, so the seed exercises the real
capture -> ingestion -> Vault and thread-lifecycle paths and can never drift
from the production write contract.

Guarantees:

- **Dev-only.** Runs only when ``WELLBE_DEV_SEED_ENABLED=true``. The Helm Job that
  invokes it is gated behind ``devSeed.enabled`` and the chart is the local-kind
  chart; no real environment ships this identity or data.
- **Idempotent.** If the dev patient already has threads, the run is a no-op, so
  the post-install/post-upgrade Helm hook can fire on every ``helm upgrade``
  without duplicating data. Captures additionally use deterministic
  ``Idempotency-Key`` values (uuid5 of the natural key), so even a forced replay
  cannot create duplicate raw records.
- **Self-contained data.** The dataset lives in this file (``THREADS`` /
  ``CAPTURES``) — "the pre-loaded data exists in the repo" — and is plain data,
  reviewable in a diff.

The dev identity is the controller acting on their own data (actor_id ==
patient_id, actor_type "controller"), which the boundary grants self-access to
without any pre-existing grant rows (see resolve_principal / require_access).
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid

import httpx

logger = logging.getLogger("wellbe.dev_seed")

# Namespace for deterministic capture Idempotency-Keys. Fixed so repeated runs
# map the same logical capture to the same key (idempotent at the raw-record
# level on top of the workspace-level skip below).
_SEED_NS = uuid.UUID("5f3b1d22-0c47-4a8e-9b6f-7c2d4e1a9f00")


# ---------------------------------------------------------------------------
# The committed dev dataset.
#
# Threads are walked through their lifecycle so the workspace shows varied,
# realistic statuses (not all "draft"). Each entry's ``walk`` is the ordered
# list of transitions applied after creation; an empty walk leaves the thread in
# ``draft``.
# ---------------------------------------------------------------------------

THREADS: list[dict[str, object]] = [
    {
        "title": "Persistent dry cough and fatigue",
        "walk": ["active_unresolved", "waiting_for_result"],
    },
    {
        "title": "Low vitamin D — follow-up",
        "walk": ["active_unresolved", "watchful_waiting"],
    },
    {
        "title": "Recurring evening tension headaches",
        "walk": ["active_unresolved"],
    },
    {
        "title": "Right knee pain after running",
        "walk": ["active_unresolved"],
    },
    {
        "title": "Borderline cholesterol — monitoring",
        "walk": ["active_unresolved", "chronic_monitoring"],
    },
]

# Captures feed C4 facts / C6 graph (and downstream Signals). Symptom/lab/note
# are user-entered text captures; descriptions are intentionally specific so the
# extractor and signal mapping have real content to work with.
CAPTURES: list[dict[str, object]] = [
    {
        "capture_type": "symptom",
        "payload": {
            "description": (
                "Dry cough most mornings for about three weeks, with unusual "
                "tiredness in the afternoons. No fever."
            ),
            "severity": "moderate",
        },
    },
    {
        "capture_type": "symptom",
        "payload": {
            "description": (
                "Tension headaches in the evening, usually after long screen "
                "time. Dull, both sides, eases with rest."
            ),
            "severity": "mild",
        },
    },
    {
        "capture_type": "symptom",
        "payload": {
            "description": (
                "Right knee aches after runs longer than 5km. Mild swelling, "
                "settles within a day."
            ),
            "severity": "mild",
        },
    },
    {
        "capture_type": "lab",
        "payload": {
            "test_name": "Vitamin D (25-OH)",
            "value": "22",
            "unit": "ng/mL",
            "reference_range": "30-100",
        },
    },
    {
        "capture_type": "lab",
        "payload": {
            "test_name": "LDL cholesterol",
            "value": "165",
            "unit": "mg/dL",
            "reference_range": "<130",
        },
    },
    {
        "capture_type": "lab",
        "payload": {
            "test_name": "Hemoglobin A1c",
            "value": "5.4",
            "unit": "%",
            "reference_range": "4.0-5.6",
        },
    },
    {
        "capture_type": "lab",
        "payload": {
            "test_name": "Blood pressure",
            "value": "128/82",
            "unit": "mmHg",
            "reference_range": "<120/80",
        },
    },
    {
        "capture_type": "note",
        "payload": {
            "text": (
                "Ask the doctor whether the low vitamin D could explain the "
                "ongoing fatigue, and whether the cough needs a chest check."
            ),
        },
    },
    {
        "capture_type": "note",
        "payload": {
            "text": (
                "Want to understand if the knee pain is just overuse or "
                "something that needs physio before it gets worse."
            ),
        },
    },
]


def _capture_idempotency_key(index: int, capture: dict[str, object]) -> str:
    """Deterministic key so a replay maps to the same raw record."""
    payload = capture["payload"]
    natural = f"{index}:{capture['capture_type']}:{sorted(payload.items())!r}"  # type: ignore[union-attr]
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


async def _already_seeded(client: httpx.AsyncClient, patient_id: str) -> bool:
    resp = await client.get("/v1/threads", headers=_headers(patient_id))
    resp.raise_for_status()
    threads = resp.json()
    return bool(threads)


async def _seed_threads(client: httpx.AsyncClient, patient_id: str) -> int:
    created = 0
    for spec in THREADS:
        resp = await client.post(
            "/v1/threads",
            headers=_headers(patient_id),
            json={"title": spec["title"]},
        )
        resp.raise_for_status()
        thread = resp.json()
        thread_id = thread["thread_id"]
        created += 1
        logger.info("created thread %s (%s)", thread_id, spec["title"])

        for target in spec["walk"]:  # type: ignore[union-attr]
            t = await client.post(
                f"/v1/threads/{thread_id}/transition",
                headers=_headers(patient_id),
                json={"target_status": target, "reason_code": "dev_seed"},
            )
            t.raise_for_status()
            logger.info("  transitioned %s -> %s", thread_id, target)
    return created


async def _seed_captures(client: httpx.AsyncClient, patient_id: str) -> int:
    created = 0
    for index, capture in enumerate(CAPTURES):
        key = _capture_idempotency_key(index, capture)
        resp = await client.post(
            "/v1/capture",
            headers=_headers(patient_id, idempotency_key=key),
            json={
                "capture_type": capture["capture_type"],
                "payload": capture["payload"],
            },
        )
        resp.raise_for_status()
        created += 1
        logger.info("captured %s (%s)", resp.json()["capture_id"], capture["capture_type"])
    return created


async def seed() -> None:
    if os.environ.get("WELLBE_DEV_SEED_ENABLED", "").lower() != "true":
        logger.info("WELLBE_DEV_SEED_ENABLED is not 'true'; skipping dev seed")
        return

    patient_id = os.environ.get("WELLBE_DEV_PATIENT_ID")
    if not patient_id:
        raise RuntimeError("WELLBE_DEV_PATIENT_ID is required when dev seed is enabled")
    # Validate early — a malformed id would otherwise fail deep in the API.
    uuid.UUID(patient_id)

    base_url = os.environ.get("WELLBE_DEV_SEED_API_BASE", "http://api:8001")
    logger.info("dev seed starting (patient=%s, api=%s)", patient_id, base_url)

    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        await _wait_for_api(client)
        if await _already_seeded(client, patient_id):
            logger.info("dev patient already has threads; seed is a no-op")
            return
        threads = await _seed_threads(client, patient_id)
        captures = await _seed_captures(client, patient_id)
        logger.info("dev seed complete: %d threads, %d captures", threads, captures)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(seed())


if __name__ == "__main__":
    main()
