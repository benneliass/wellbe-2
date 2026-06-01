"""Benchmark corpus seeder.

A faithful Python port of ``tests/fixtures/benchmark/seed.sh`` used by the E2E
harness. It reads the fixture ``raw_events`` for each case in a given mode and POSTs
them to the ingestion-worker, building the exact same payload the shell harness does:

  * ``source_type`` forced to ``manual_text`` (routes to the rule-based text path),
  * text = ``raw_payload.original.event`` when present, else ``json.dumps(raw_payload)``
    (timeline_* events carry prose; obs_* events serialize the whole payload),
  * the text is sent both base64-encoded as ``raw_data`` and verbatim as
    ``metadata.text``.

Keeping the text-selection byte-identical to ``seed.sh`` is what makes the keyword
matcher and the ``OTHER`` fallback hash (``normalized_key``) reproduce the deterministic
expected counts.
"""

from __future__ import annotations

import base64
import json
import uuid
from pathlib import Path

import httpx
import yaml

FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "benchmark"
MANIFEST_PATH = FIXTURE_ROOT / "manifest.yaml"


def _event_text(event: dict) -> str:
    """Mirror seed.sh text selection exactly."""
    raw_payload = event.get("raw_payload", {})
    if isinstance(raw_payload, dict):
        original = raw_payload.get("original", {})
        if isinstance(original, dict) and "event" in original:
            return original["event"]
        return json.dumps(raw_payload)
    return str(raw_payload)


def _build_payload(event: dict, case_id: str, user_id: str, filename: str) -> dict:
    text = _event_text(event)
    return {
        "source_type": "manual_text",
        "raw_data": base64.b64encode(text.encode("utf-8")).decode("utf-8"),
        "captured_at": event.get("captured_at", ""),
        "actor_id": user_id,
        "patient_id": user_id,
        "consent_snapshot_id": str(uuid.uuid4()),
        "correlation_id": str(uuid.uuid4()),
        "trace_id": str(uuid.uuid4()),
        "metadata": {
            "text": text,
            "case_id": case_id,
            "event_file": filename,
        },
    }


def load_cases() -> list[dict]:
    with MANIFEST_PATH.open() as f:
        manifest = yaml.safe_load(f)
    return [
        {
            "case_id": c["case_id"],
            "synthetic_user_id": c["synthetic_user_id"],
            "case_dir": c["case_dir"],
        }
        for c in manifest.get("cases", [])
    ]


def _case_event_files(case_dir_rel: str, mode: str) -> list[Path]:
    events_dir = FIXTURE_ROOT / case_dir_rel / mode / "raw_events"
    if not events_dir.is_dir():
        return []
    return sorted(events_dir.glob("*.json"))


async def seed(
    ingestion_url: str,
    *,
    mode: str = "blind_pre_diagnosis",
    timeout: float = 30.0,
) -> dict[str, int]:
    """Seed every case for ``mode`` into the ingestion-worker.

    Returns a mapping of case_id -> events successfully accepted. Raises on any
    non-2xx response so the E2E run fails loudly rather than silently under-seeding.
    """
    sent_by_case: dict[str, int] = {}
    async with httpx.AsyncClient(base_url=ingestion_url, timeout=timeout) as client:
        for case in load_cases():
            case_id = case["case_id"]
            user_id = case["synthetic_user_id"]
            files = _case_event_files(case["case_dir"], mode)
            sent = 0
            for path in files:
                event = json.loads(path.read_text())
                payload = _build_payload(event, case_id, user_id, path.name)
                resp = await client.post("/ingest", json=payload)
                if resp.status_code not in (200, 201, 202):
                    raise RuntimeError(
                        f"[{case_id}] ingest failed for {path.name}: "
                        f"HTTP {resp.status_code} {resp.text[:200]}"
                    )
                sent += 1
            sent_by_case[case_id] = sent
    return sent_by_case
