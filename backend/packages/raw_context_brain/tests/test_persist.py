"""Ledger and projection behavior covered by the lab persist tests.

The postgres pointer sketch is not ported. It stored note text in brain tables.
"""

from __future__ import annotations

from dataclasses import replace

import pytest
from wellbe_raw_context_brain.store import AdvertisementDraft, AdvertisementLog, Projection, Vault
from wellbe_raw_context_brain.types import Judgment, VaultEvent


def _event() -> VaultEvent:
    return VaultEvent(
        id="n1",
        person_id="p1",
        captured_at="2024-01-01",
        source_type="note",
        text="short sleep",
        content_hash="h",
        lineage_id="sleep",
        document_id=None,
    )


def _draft(
    *,
    judgment: Judgment = "link",
    confidence: float = 0.4,
    withdrawn: bool = False,
) -> AdvertisementDraft:
    return AdvertisementDraft(
        person_id="p1",
        origin="model",
        model_version="lab",
        prompt_version=None,
        policy_version="lab-policy-1",
        evidence_ids=("n1", "n2"),
        from_id="n1",
        to_id="n2",
        judgment=judgment,
        reason_code="shared_context",
        relation="possible_semantic_association",
        proposed_confidence=0.4,
        confidence=confidence,
        created_at="2024-01-02",
        supersedes_id=None,
        withdrawn=withdrawn,
    )


def test_refuses_a_second_write_of_the_same_vault_id() -> None:
    vault = Vault()
    vault.append(_event())
    with pytest.raises(ValueError, match="vault is append-only"):
        vault.append(_event())


def test_leaves_an_accepted_edge_when_a_later_model_judgment_abstains() -> None:
    log = AdvertisementLog()
    projection = Projection()
    projection.apply(log.append(_draft()))
    projection.apply(log.append(_draft(judgment="uncertain", confidence=0.1)))
    projection.apply(log.append(_draft(judgment="no_link", confidence=0.1)))
    assert projection.neighbors("n1") == ["n2"]
    projection.apply(log.append(_draft(withdrawn=True)))
    assert projection.neighbors("n1") == []


def test_rebuild_matches_the_live_projection_digest() -> None:
    log = AdvertisementLog()
    ads = [
        log.append(_draft()),
        log.append(_draft(judgment="no_link", confidence=0.1)),
    ]
    live = Projection()
    for ad in ads:
        live.apply(ad)
    rebuilt = Projection()
    rebuilt.rebuild(ads)
    assert rebuilt.digest == live.digest


def test_rebuild_verifies_advertisement_digests_before_folding() -> None:
    log = AdvertisementLog()
    ad = log.append(_draft())
    projection = Projection()
    projection.apply(ad)
    before = projection.digest
    tampered = replace(ad, id="ad-tampered", confidence=0.99, digest="tampered")
    with pytest.raises(ValueError, match="advertisement digest mismatch at ad-tampered"):
        projection.rebuild([tampered])
    kept = projection.edge_between(ad.from_id, ad.to_id)
    assert kept is not None
    assert kept.ad_id == ad.id
    assert kept.confidence == ad.confidence
    assert projection.status == "ready"
    assert projection.digest == before
