"""Append-only vault, advertisement ledger, and accepted-edge projection."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from operator import itemgetter
from typing import Literal

# Digest and source-group checks are owned by the integrity port.
from wellbe_raw_context_brain.integrity.row_hash import assert_advertisement_digests, row_hash
from wellbe_raw_context_brain.types import (
    AcceptedEdge,
    Judgment,
    LinkAdvertisement,
    Origin,
    PointerNode,
    Relation,
    VaultEvent,
)

ProjectionStatus = Literal["ready", "rebuilding"]


@dataclass(frozen=True)
class AdvertisementDraft:
    person_id: str
    origin: Origin
    model_version: str | None
    prompt_version: str | None
    policy_version: str
    evidence_ids: tuple[str, ...]
    from_id: str
    to_id: str
    judgment: Judgment
    reason_code: str
    relation: Relation
    proposed_confidence: float
    confidence: float
    created_at: str
    supersedes_id: str | None
    withdrawn: bool


class Vault:
    def __init__(self) -> None:
        self._events: dict[str, VaultEvent] = {}

    @property
    def size(self) -> int:
        return len(self._events)

    def has(self, event_id: str) -> bool:
        return event_id in self._events

    def append(self, event: VaultEvent) -> None:
        if event.id in self._events:
            raise ValueError("vault is append-only")
        self._events[event.id] = event

    def get(self, event_id: str) -> VaultEvent | None:
        return self._events.get(event_id)

    def replace(self, event: VaultEvent) -> None:
        """Refresh the working excerpt for an id the vault already holds.

        The content hash must match. This does not append a second copy.
        """
        current = self._events.get(event.id)
        if current is None:
            raise ValueError("unknown event")
        if current.content_hash != event.content_hash:
            raise ValueError("vault event hash changed")
        self._events[event.id] = event

    def list(self) -> list[VaultEvent]:
        return list(self._events.values())


class AdvertisementLog:
    def __init__(self) -> None:
        self._sequence = 0
        self.ads: list[LinkAdvertisement] = []
        self._by_id: dict[str, LinkAdvertisement] = {}

    def append(self, draft: AdvertisementDraft) -> LinkAdvertisement:
        self._sequence += 1
        pending = LinkAdvertisement(
            id=f"ad-{self._sequence}",
            person_id=draft.person_id,
            sequence=self._sequence,
            origin=draft.origin,
            digest="",
            model_version=draft.model_version,
            prompt_version=draft.prompt_version,
            policy_version=draft.policy_version,
            evidence_ids=tuple(draft.evidence_ids),
            from_id=draft.from_id,
            to_id=draft.to_id,
            judgment=draft.judgment,
            reason_code=draft.reason_code,
            relation=draft.relation,
            proposed_confidence=draft.proposed_confidence,
            confidence=draft.confidence,
            created_at=draft.created_at,
            supersedes_id=draft.supersedes_id,
            withdrawn=draft.withdrawn,
        )
        ad = replace(pending, digest=row_hash(pending))
        self.ads.append(ad)
        self._by_id[ad.id] = ad
        return ad

    def get(self, advertisement_id: str) -> LinkAdvertisement | None:
        return self._by_id.get(advertisement_id)

    def verify_digests(self) -> None:
        assert_advertisement_digests(self.ads)

    def restore(self, ads: Sequence[LinkAdvertisement]) -> None:
        """Replace the ledger with rows whose digests already match.

        Sequence continues after the last row.
        """
        assert_advertisement_digests(ads)
        self.ads.clear()
        self._by_id.clear()
        self._sequence = 0
        for ad in ads:
            row = replace(ad, evidence_ids=tuple(ad.evidence_ids))
            self.ads.append(row)
            self._by_id[row.id] = row
            if row.sequence > self._sequence:
                self._sequence = row.sequence


def _sha256(message: str) -> str:
    return hashlib.sha256(message.encode()).hexdigest()


def _number_token(value: float) -> str:
    token = json.dumps(value)
    if token.endswith(".0"):
        return token[:-2]
    return token


def _edge_key(left: str, right: str) -> str:
    if left < right:
        return f"{left}|{right}"
    return f"{right}|{left}"


def _canonical_digest(edges: Mapping[str, AcceptedEdge]) -> str:
    lines = [
        f"{key}|{edge.ad_id}|{_number_token(edge.confidence)}|{edge.relation}"
        for key, edge in sorted(edges.items(), key=itemgetter(0))
    ]
    body = "\n".join(lines)
    return _sha256(body if body else "empty")


def _drops_accepted_edge(ad: LinkAdvertisement) -> bool:
    return ad.withdrawn or (ad.origin == "user_correction" and ad.judgment != "link")


def _accepted_edge(ad: LinkAdvertisement) -> AcceptedEdge:
    return AcceptedEdge(
        ad_id=ad.id,
        from_id=ad.from_id,
        to_id=ad.to_id,
        confidence=ad.confidence,
        reason_code=ad.reason_code,
        relation=ad.relation,
        evidence_ids=tuple(ad.evidence_ids),
        origin=ad.origin,
    )


class Projection:
    def __init__(self) -> None:
        self.revision = 0
        self.status: ProjectionStatus = "ready"
        self.digest = _sha256("empty")
        self._edges: dict[str, AcceptedEdge] = {}
        self._adjacency: dict[str, set[str]] = {}

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    def accepted(self) -> list[AcceptedEdge]:
        return [
            replace(edge, evidence_ids=tuple(edge.evidence_ids)) for edge in self._edges.values()
        ]

    def edge_between(self, left: str, right: str) -> AcceptedEdge | None:
        edge = self._edges.get(_edge_key(left, right))
        if edge is None:
            return None
        return replace(edge, evidence_ids=tuple(edge.evidence_ids))

    def neighbors(self, node_id: str) -> list[str]:
        return sorted(self._adjacency.get(node_id, ()))

    def degree(self, node_id: str) -> int:
        adjacent = self._adjacency.get(node_id)
        if adjacent is None:
            return 0
        return len(adjacent)

    def apply(self, ad: LinkAdvertisement) -> bool:
        key = _edge_key(ad.from_id, ad.to_id)
        if _drops_accepted_edge(ad):
            if key not in self._edges:
                return False
            del self._edges[key]
            self._unlink(ad.from_id, ad.to_id)
            self._bump()
            return True
        if ad.judgment != "link":
            return False
        nxt = _accepted_edge(ad)
        previous = self._edges.get(key)
        self._edges[key] = nxt
        self._link(ad.from_id, ad.to_id)
        if (
            previous is not None
            and previous.ad_id == nxt.ad_id
            and previous.confidence == nxt.confidence
        ):
            return False
        self._bump()
        return True

    def rebuild(self, ads: Sequence[LinkAdvertisement]) -> None:
        assert_advertisement_digests(ads)
        self.status = "rebuilding"
        self._edges.clear()
        self._adjacency.clear()
        for ad in ads:
            key = _edge_key(ad.from_id, ad.to_id)
            if _drops_accepted_edge(ad):
                if key in self._edges:
                    del self._edges[key]
                    self._unlink(ad.from_id, ad.to_id)
                continue
            if ad.judgment != "link":
                continue
            self._edges[key] = _accepted_edge(ad)
            self._link(ad.from_id, ad.to_id)
        self.digest = _canonical_digest(self._edges)
        self.revision += 1
        self.status = "ready"

    def _bump(self) -> None:
        self.revision += 1
        self.digest = _canonical_digest(self._edges)

    def _link(self, left: str, right: str) -> None:
        self._adjacency.setdefault(left, set()).add(right)
        self._adjacency.setdefault(right, set()).add(left)

    def _unlink(self, left: str, right: str) -> None:
        left_neighbors = self._adjacency.get(left)
        if left_neighbors is not None:
            left_neighbors.discard(right)
        right_neighbors = self._adjacency.get(right)
        if right_neighbors is not None:
            right_neighbors.discard(left)


def empty_pointer(event: VaultEvent) -> PointerNode:
    return PointerNode(
        id=event.id,
        kind="event",
        vault_event_id=event.id,
        member_event_ids=(),
        person_id=event.person_id,
    )
