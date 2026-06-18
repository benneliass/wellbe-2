"""Thread genesis capability (continuity/triage-owned).

Genesis consumes ``genesis.input_ready`` and produces exactly one durable triage
decision per concern, recorded in an append-only, idempotent ledger. The
high-confidence auto-create side effects (C7 thread / C9 candidate) are layered on
top in Story B1; Story B0 is the consumer skeleton + ledger.

Authoritative decisions:
- docs/decisions/thread-genesis-triage-decision-contract.md (WEL-171, S1)
- docs/decisions/thread-genesis-concern-resolution-key.md (WEL-171, S3)
"""

from wellbe_c9_continuity.genesis.concern_key import (
    classify_concern_group,
    decision_inputs_hash,
    derive_concern_key,
)
from wellbe_c9_continuity.genesis.repository import GenesisDecisionRepository
from wellbe_c9_continuity.genesis.service import ThreadGenesisService

__all__ = [
    "GenesisDecisionRepository",
    "ThreadGenesisService",
    "classify_concern_group",
    "decision_inputs_hash",
    "derive_concern_key",
]
