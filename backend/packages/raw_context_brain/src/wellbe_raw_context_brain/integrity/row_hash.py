"""Canonical hash of one complete ledger row. Excludes id and digest."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence

from wellbe_raw_context_brain.types import LinkAdvertisement


def row_hash(row: LinkAdvertisement) -> str:
    """SHA-256 of the canonical JSON object. Key order matches the lab row hash."""
    canonical = {
        "person_id": row.person_id,
        "sequence": row.sequence,
        "origin": row.origin,
        "model_version": row.model_version,
        "prompt_version": row.prompt_version,
        "policy_version": row.policy_version,
        "evidence_ids": sorted(row.evidence_ids),
        "from_id": row.from_id,
        "to_id": row.to_id,
        "judgment": row.judgment,
        "reason_code": row.reason_code,
        "relation": row.relation,
        "proposed_confidence": row.proposed_confidence,
        "confidence": row.confidence,
        "created_at": row.created_at,
        "supersedes_id": row.supersedes_id,
        "withdrawn": row.withdrawn,
    }
    payload = json.dumps(canonical, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def assert_advertisement_digests(ads: Sequence[LinkAdvertisement]) -> None:
    for ad in ads:
        if row_hash(ad) != ad.digest:
            raise ValueError(f"advertisement digest mismatch at {ad.id}")
