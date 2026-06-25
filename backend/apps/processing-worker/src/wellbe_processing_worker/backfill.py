"""Reprocess-from-raw backfill for structured lab captures (WEL-185).

Before WEL-185, ``capture_type=lab`` captures were flattened to text and typed
``FactType.OTHER`` (→ ``node_type='Other'``), so type-filtered consumers (Home
Signals) reported "no current data" despite the data existing. The fix types new
captures correctly, but historical raw events still resolve to ``Other`` nodes.

Per the approved decision (docs/decisions/structured-capture-extraction-typing.md
§7), we correct history by **reprocess-from-raw**, never by mutating the
immutable raw captures:

1. Find every ``capture_type=lab`` raw event (optionally scoped to one patient).
2. Replay each through the *live* ``_extract_facts`` path — which now dispatches
   to the structured extractor — producing correctly-typed ``LabResult`` /
   ``VitalSign`` facts and graph nodes. This is idempotent (deterministic fact
   ids + ``ON CONFLICT DO NOTHING`` + idempotent node upsert), so it is safe to
   run repeatedly and safe under redelivery.
3. **Supersede** (not delete) the old ``Other`` graph nodes derived from those
   same raw events, preserving the evidence trail.

Run modes (env):
- ``WELLBE_BACKFILL_DRY_RUN=true`` — report what would change, write nothing.
- ``WELLBE_BACKFILL_PATIENT_ID=<uuid>`` — scope to one patient (else all).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

logger = logging.getLogger("wellbe.backfill")

_SUPERSEDED_REASON = "wel-185-structured-typing-backfill"


async def backfill_lab_captures(
    *, patient_id: str | None = None, dry_run: bool = False
) -> dict[str, Any]:
    """Reprocess ``capture_type=lab`` raw events and supersede stale Other nodes."""
    from wellbe_c2_vault.models import RawContextEventRow
    from wellbe_c4_processing.models import ExtractedFactRow
    from wellbe_c6_graph.models import KgNodeRow
    from wellbe_contracts.c2_vault import RawContextEvent
    from wellbe_db import create_engine, create_session_factory

    from wellbe_processing_worker.config import ProcessingWorkerSettings
    from wellbe_processing_worker.tasks import _extract_facts

    settings = ProcessingWorkerSettings()
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    summary: dict[str, Any] = {
        "lab_events": 0,
        "reprocessed": 0,
        "superseded_nodes": 0,
        "dry_run": dry_run,
        "patient_scope": patient_id or "all",
    }

    try:
        # 1. Collect the lab raw events (immutable source of truth).
        async with session_factory() as session:
            stmt = select(RawContextEventRow).where(
                RawContextEventRow.source_metadata["capture_type"].astext == "lab"
            )
            if patient_id:
                stmt = stmt.where(
                    RawContextEventRow.patient_id == uuid.UUID(patient_id)
                )
            rows = list((await session.execute(stmt)).scalars().all())
            events = [RawContextEvent.model_validate(row) for row in rows]

        summary["lab_events"] = len(events)
        if not events:
            logger.info("no capture_type=lab raw events found; nothing to backfill")
            return summary

        if dry_run:
            for ev in events:
                md = ev.source_metadata or {}
                logger.info(
                    "[dry-run] would reprocess raw_event=%s patient=%s test=%r value=%r",
                    ev.id, ev.patient_id, md.get("test_name"), md.get("value"),
                )
            return summary

        # 2. Replay through the live pipeline (idempotent).
        for ev in events:
            await _extract_facts(json.dumps(ev.model_dump(mode="json")))
            summary["reprocessed"] = int(summary["reprocessed"]) + 1
            logger.info("reprocessed raw_event=%s patient=%s", ev.id, ev.patient_id)

        # 3. Supersede the stale Other nodes that originated from these events.
        now = datetime.now(UTC).replace(tzinfo=None)
        async with session_factory() as session:
            for ev in events:
                other_facts = list(
                    (
                        await session.execute(
                            select(ExtractedFactRow).where(
                                ExtractedFactRow.raw_context_event_id == ev.id,
                                ExtractedFactRow.fact_type == "other",
                            )
                        )
                    ).scalars().all()
                )
                for fact in other_facts:
                    node = (
                        await session.execute(
                            select(KgNodeRow).where(
                                KgNodeRow.patient_id == fact.patient_id,
                                KgNodeRow.normalized_key == fact.normalized_key,
                                KgNodeRow.node_type == "Other",
                                KgNodeRow.status == "active",
                            )
                        )
                    ).scalar_one_or_none()
                    if node is None:
                        continue
                    node.status = "superseded"
                    meta = dict(node.node_metadata or {})
                    meta["superseded_reason"] = _SUPERSEDED_REASON
                    meta["superseded_at"] = now.isoformat()
                    node.node_metadata = meta
                    node.updated_at = now
                    summary["superseded_nodes"] = int(summary["superseded_nodes"]) + 1
                    logger.info(
                        "superseded Other node=%s key=%s", node.id, node.normalized_key
                    )
            await session.commit()

        return summary
    finally:
        await engine.dispose()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    patient_id = os.environ.get("WELLBE_BACKFILL_PATIENT_ID") or None
    dry_run = os.environ.get("WELLBE_BACKFILL_DRY_RUN", "").lower() == "true"
    result = asyncio.run(backfill_lab_captures(patient_id=patient_id, dry_run=dry_run))
    logger.info("backfill complete: %s", result)


if __name__ == "__main__":
    main()
