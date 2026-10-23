"""Source-group checks for same_record_group rows.

same_record_group is hub membership only. A missing policy row is not invented.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol

from wellbe_raw_context_brain.types import LinkAdvertisement


class SourceGroupNode(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def kind(self) -> str: ...

    @property
    def member_event_ids(self) -> Sequence[str]: ...


def assert_structural_ledger(
    ads: Sequence[LinkAdvertisement],
    nodes: Sequence[SourceGroupNode],
) -> None:
    by_id = {node.id: node for node in nodes}
    for ad in ads:
        if not _active_same_record(ad):
            continue
        if not _matches_hub_membership(ad, by_id):
            raise ValueError(f"structural link {ad.id} does not match source-group membership")
    for node in nodes:
        if node.kind != "pseudonode":
            continue
        for member_id in node.member_event_ids:
            if not any(_policy_row_for(ad, node.id, member_id) for ad in ads):
                raise ValueError(f"structural membership {member_id} has no policy ledger row")


def _active_same_record(ad: LinkAdvertisement) -> bool:
    return ad.relation == "same_record_group" and ad.judgment == "link" and not ad.withdrawn


def _matches_hub_membership(
    ad: LinkAdvertisement,
    by_id: Mapping[str, SourceGroupNode],
) -> bool:
    source = by_id.get(ad.from_id)
    target = by_id.get(ad.to_id)
    source_is_hub = source is not None and source.kind == "pseudonode"
    target_is_hub = target is not None and target.kind == "pseudonode"
    if source_is_hub and not target_is_hub:
        return source is not None and ad.to_id in source.member_event_ids
    if target_is_hub and not source_is_hub:
        return target is not None and ad.from_id in target.member_event_ids
    return False


def _policy_row_for(ad: LinkAdvertisement, hub_id: str, member_id: str) -> bool:
    if ad.origin != "policy" or not _active_same_record(ad):
        return False
    if ad.from_id == hub_id:
        other = ad.to_id
    elif ad.to_id == hub_id:
        other = ad.from_id
    else:
        return False
    return other == member_id
