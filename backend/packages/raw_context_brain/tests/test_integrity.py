"""Ledger row hash and same_record_group hub checks."""

from __future__ import annotations

from dataclasses import dataclass, replace

import pytest
from wellbe_raw_context_brain.integrity.row_hash import assert_advertisement_digests, row_hash
from wellbe_raw_context_brain.integrity.structural import assert_structural_ledger
from wellbe_raw_context_brain.types import LinkAdvertisement


def _row() -> LinkAdvertisement:
    return LinkAdvertisement(
        id="ad-ignored",
        person_id="p1",
        sequence=1,
        origin="model",
        digest="seed",
        model_version="lab",
        prompt_version="lab-prompt-1",
        policy_version="lab-policy-1",
        evidence_ids=("n2", "n1"),
        from_id="n1",
        to_id="n2",
        judgment="link",
        reason_code="shared_context",
        relation="possible_semantic_association",
        proposed_confidence=0.4,
        confidence=0.4,
        created_at="2024-01-02T00:00:00.000Z",
        supersedes_id=None,
        withdrawn=False,
    )


def _sealed(ad: LinkAdvertisement) -> LinkAdvertisement:
    return replace(ad, digest=row_hash(ad))


def _structural_ad(
    *,
    id: str,
    from_id: str,
    to_id: str,
    withdrawn: bool = False,
) -> LinkAdvertisement:
    unsigned = replace(
        _row(),
        id=id,
        origin="policy",
        model_version=None,
        prompt_version=None,
        reason_code="membership",
        relation="same_record_group",
        evidence_ids=(),
        from_id=from_id,
        to_id=to_id,
        withdrawn=withdrawn,
    )
    return _sealed(unsigned)


@dataclass(frozen=True)
class _Node:
    id: str
    kind: str
    member_event_ids: tuple[str, ...] = ()


_HUB = _Node(id="hub-1", kind="pseudonode", member_event_ids=("evt-1",))
_MEMBER = _Node(id="evt-1", kind="event")


def test_row_hash_changes_when_a_previously_uncovered_field_changes() -> None:
    base_row = _row()
    base = row_hash(base_row)
    assert row_hash(replace(base_row, model_version="lab-2")) != base
    assert row_hash(replace(base_row, prompt_version="lab-prompt-2")) != base
    assert row_hash(replace(base_row, policy_version="lab-policy-2")) != base
    assert row_hash(replace(base_row, proposed_confidence=0.9)) != base
    assert row_hash(replace(base_row, created_at="2024-03-03T00:00:00.000Z")) != base
    assert row_hash(replace(base_row, evidence_ids=("n1", "n2"))) == base
    stored = replace(base_row, id="ad-1", digest="not-part-of-the-row")
    assert row_hash(stored) == base


def test_throws_on_a_tampered_digest_and_does_not_accept_that_row() -> None:
    ad = _sealed(replace(_row(), id="ad-1"))
    assert_advertisement_digests([ad])

    tampered = replace(ad, id="ad-tampered", confidence=0.99, digest="tampered")
    with pytest.raises(ValueError, match="advertisement digest mismatch at ad-tampered"):
        assert_advertisement_digests([tampered])
    with pytest.raises(ValueError, match="advertisement digest mismatch at ad-tampered"):
        assert_advertisement_digests([ad, tampered])

    assert_advertisement_digests([ad])
    assert row_hash(ad) == ad.digest
    assert ad.confidence == 0.4


def test_accepts_a_hub_and_a_member_in_that_hub() -> None:
    ads = [_structural_ad(id="ad-1", from_id="evt-1", to_id="hub-1")]
    assert_structural_ledger(ads, [_HUB, _MEMBER])


def test_rejects_a_hub_link_whose_other_end_is_not_a_member() -> None:
    ads = [_structural_ad(id="ad-1", from_id="evt-9", to_id="hub-1")]
    nodes = [_HUB, _Node(id="evt-9", kind="event")]
    message = "structural link ad-1 does not match source-group membership"
    with pytest.raises(ValueError, match=message):
        assert_structural_ledger(ads, nodes)


def test_rejects_same_record_group_between_two_event_nodes() -> None:
    ads = [_structural_ad(id="ad-1", from_id="evt-1", to_id="evt-2")]
    nodes = [_MEMBER, _Node(id="evt-2", kind="event")]
    message = "structural link ad-1 does not match source-group membership"
    with pytest.raises(ValueError, match=message):
        assert_structural_ledger(ads, nodes)


def test_rejects_a_hub_member_with_no_policy_ledger_row() -> None:
    with pytest.raises(ValueError, match="structural membership evt-1 has no policy ledger row"):
        assert_structural_ledger([], [_HUB])


def test_does_not_treat_a_withdrawn_hub_link_as_the_required_policy_row() -> None:
    ads = [_structural_ad(id="ad-1", from_id="evt-1", to_id="hub-1", withdrawn=True)]
    with pytest.raises(ValueError, match="structural membership evt-1 has no policy ledger row"):
        assert_structural_ledger(ads, [_HUB, _MEMBER])
