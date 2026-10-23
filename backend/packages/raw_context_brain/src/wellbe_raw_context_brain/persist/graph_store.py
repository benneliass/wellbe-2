"""Durable graph snapshot. Sessions and idempotency results are not stored here.

Browser localStorage is not part of this port. Callers persist ``snapshot_to_json``
themselves. Corrupt JSON raises ``ValueError`` and does not return a partial graph.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Protocol, cast

from wellbe_raw_context_brain.types import (
    Independence,
    Judgment,
    LinkAdvertisement,
    Origin,
    PointerKind,
    PointerNode,
    Relation,
    SourceArrival,
    VaultEvent,
)

_UNREADABLE = "graph store snapshot is unreadable"

_ORIGINS: set[Origin] = {"model", "user_correction", "policy"}
_JUDGMENTS: set[Judgment] = {"link", "no_link", "uncertain"}
_RELATIONS: set[Relation] = {
    "explicitly_linked",
    "same_record_group",
    "derived_or_copied",
    "near_in_time",
    "possible_semantic_association",
    "possible_inconsistency",
}
_KINDS: set[PointerKind] = {"event", "pseudonode"}
_INDEPENDENCE: set[Independence] = {"source_family", "unknown"}
_ARRIVALS: set[SourceArrival] = {"typed", "copied", "imported"}


@dataclass(frozen=True)
class LinkAcknowledgement:
    person_id: str
    endpoint_ids: tuple[str, str]
    acknowledged: bool
    updated_at: str


@dataclass(frozen=True)
class DurableSnapshot:
    events: tuple[VaultEvent, ...]
    advertisements: tuple[LinkAdvertisement, ...]
    nodes: tuple[PointerNode, ...]
    acknowledgements: tuple[LinkAcknowledgement, ...]
    projection_revision: int | None = None
    projection_digest: str | None = None
    placed_event_ids: tuple[str, ...] = ()


class GraphStore(Protocol):
    def load(self) -> DurableSnapshot: ...

    def save(self, snapshot: DurableSnapshot) -> None: ...


def empty_durable_snapshot() -> DurableSnapshot:
    return DurableSnapshot(events=(), advertisements=(), nodes=(), acknowledgements=())


def _unreadable() -> ValueError:
    return ValueError(_UNREADABLE)


def _mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise _unreadable()
    return cast(dict[str, object], value)


def _array(parsed: dict[str, object], key: str) -> list[object]:
    value = parsed.get(key)
    if not isinstance(value, list):
        raise _unreadable()
    return cast(list[object], value)


def _required(record: dict[str, object], key: str) -> object:
    if key not in record:
        raise _unreadable()
    return record[key]


def _string(value: object) -> str:
    if not isinstance(value, str):
        raise _unreadable()
    return value


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    return _string(value)


def _bool(value: object) -> bool:
    if not isinstance(value, bool):
        raise _unreadable()
    return value


def _number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise _unreadable()
    return float(value)


def _integer(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise _unreadable()
    if isinstance(value, float) and not value.is_integer():
        raise _unreadable()
    return int(value)


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise _unreadable()
    items = cast(list[object], value)
    if not all(isinstance(item, str) for item in items):
        raise _unreadable()
    return tuple(cast(list[str], items))


def _choice[T](value: object, allowed: set[T]) -> T:
    if isinstance(value, str):
        for item in allowed:
            if item == value:
                return item
    raise _unreadable()


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    if isinstance(value, float) and not value.is_integer():
        return None
    return int(value)


def _optional_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    return value


def _canonical_endpoints(left: str, right: str) -> tuple[str, str]:
    if left <= right:
        return (left, right)
    return (right, left)


def _canonical_acknowledgement(row: LinkAcknowledgement) -> LinkAcknowledgement:
    ordered = _canonical_endpoints(row.endpoint_ids[0], row.endpoint_ids[1])
    if ordered == row.endpoint_ids:
        return row
    return replace(row, endpoint_ids=ordered)


def _event_payload(event: VaultEvent) -> dict[str, object]:
    return {
        "id": event.id,
        "person_id": event.person_id,
        "captured_at": event.captured_at,
        "source_type": event.source_type,
        "text": event.text,
        "keyword": event.keyword,
        "content_hash": event.content_hash,
        "lineage_id": event.lineage_id,
        "independence": event.independence,
        "source_arrival": event.source_arrival,
        "copied_from_id": event.copied_from_id,
        "document_id": event.document_id,
    }


def _advertisement_payload(ad: LinkAdvertisement) -> dict[str, object]:
    return {
        "id": ad.id,
        "person_id": ad.person_id,
        "sequence": ad.sequence,
        "origin": ad.origin,
        "digest": ad.digest,
        "model_version": ad.model_version,
        "prompt_version": ad.prompt_version,
        "policy_version": ad.policy_version,
        "evidence_ids": list(ad.evidence_ids),
        "from_id": ad.from_id,
        "to_id": ad.to_id,
        "judgment": ad.judgment,
        "reason_code": ad.reason_code,
        "relation": ad.relation,
        "proposed_confidence": ad.proposed_confidence,
        "confidence": ad.confidence,
        "created_at": ad.created_at,
        "supersedes_id": ad.supersedes_id,
        "withdrawn": ad.withdrawn,
    }


def _node_payload(node: PointerNode) -> dict[str, object]:
    return {
        "id": node.id,
        "kind": node.kind,
        "vault_event_id": node.vault_event_id,
        "member_event_ids": list(node.member_event_ids),
        "person_id": node.person_id,
    }


def _ack_payload(row: LinkAcknowledgement) -> dict[str, object]:
    return {
        "person_id": row.person_id,
        "endpoint_ids": list(row.endpoint_ids),
        "acknowledged": row.acknowledged,
        "updated_at": row.updated_at,
    }


def _snapshot_payload(snapshot: DurableSnapshot) -> dict[str, object]:
    payload: dict[str, object] = {
        "events": [_event_payload(event) for event in snapshot.events],
        "advertisements": [_advertisement_payload(ad) for ad in snapshot.advertisements],
        "nodes": [_node_payload(node) for node in snapshot.nodes],
        "acknowledgements": [
            _ack_payload(_canonical_acknowledgement(row)) for row in snapshot.acknowledgements
        ],
    }
    if snapshot.projection_revision is not None:
        payload["projection_revision"] = snapshot.projection_revision
    if snapshot.projection_digest is not None:
        payload["projection_digest"] = snapshot.projection_digest
    if snapshot.placed_event_ids:
        payload["placed_event_ids"] = list(snapshot.placed_event_ids)
    return payload


def _parse_event(value: object) -> VaultEvent:
    record = _mapping(value)
    independence: Independence = "source_family"
    if "independence" in record:
        independence = _choice(record["independence"], _INDEPENDENCE)
    arrival: SourceArrival = "typed"
    if "source_arrival" in record:
        arrival = _choice(record["source_arrival"], _ARRIVALS)
    keyword = None
    if "keyword" in record:
        keyword = _string_or_none(record["keyword"])
    copied_from_id = None
    if "copied_from_id" in record:
        copied_from_id = _string_or_none(record["copied_from_id"])
    return VaultEvent(
        id=_string(_required(record, "id")),
        person_id=_string(_required(record, "person_id")),
        captured_at=_string(_required(record, "captured_at")),
        source_type=_string(_required(record, "source_type")),
        text=_string(_required(record, "text")),
        content_hash=_string(_required(record, "content_hash")),
        lineage_id=_string(_required(record, "lineage_id")),
        document_id=_string_or_none(_required(record, "document_id")),
        keyword=keyword,
        independence=independence,
        source_arrival=arrival,
        copied_from_id=copied_from_id,
    )


def _parse_advertisement(value: object) -> LinkAdvertisement:
    record = _mapping(value)
    origin: Origin = _choice(_required(record, "origin"), _ORIGINS)
    judgment: Judgment = _choice(_required(record, "judgment"), _JUDGMENTS)
    relation: Relation = _choice(_required(record, "relation"), _RELATIONS)
    return LinkAdvertisement(
        id=_string(_required(record, "id")),
        person_id=_string(_required(record, "person_id")),
        sequence=_integer(_required(record, "sequence")),
        origin=origin,
        digest=_string(_required(record, "digest")),
        model_version=_string_or_none(_required(record, "model_version")),
        prompt_version=_string_or_none(_required(record, "prompt_version")),
        policy_version=_string(_required(record, "policy_version")),
        evidence_ids=_strings(_required(record, "evidence_ids")),
        from_id=_string(_required(record, "from_id")),
        to_id=_string(_required(record, "to_id")),
        judgment=judgment,
        reason_code=_string(_required(record, "reason_code")),
        relation=relation,
        proposed_confidence=_number(_required(record, "proposed_confidence")),
        confidence=_number(_required(record, "confidence")),
        created_at=_string(_required(record, "created_at")),
        supersedes_id=_string_or_none(_required(record, "supersedes_id")),
        withdrawn=_bool(_required(record, "withdrawn")),
    )


def _parse_node(value: object) -> PointerNode:
    record = _mapping(value)
    kind: PointerKind = _choice(_required(record, "kind"), _KINDS)
    return PointerNode(
        id=_string(_required(record, "id")),
        kind=kind,
        vault_event_id=_string_or_none(_required(record, "vault_event_id")),
        member_event_ids=_strings(_required(record, "member_event_ids")),
        person_id=_string(_required(record, "person_id")),
    )


def _parse_acknowledgement(value: object) -> LinkAcknowledgement:
    record = _mapping(value)
    raw_ids = _required(record, "endpoint_ids")
    if not isinstance(raw_ids, list) or len(raw_ids) != 2:
        raise _unreadable()
    items = cast(list[object], raw_ids)
    left = items[0]
    right = items[1]
    if not isinstance(left, str) or not isinstance(right, str):
        raise _unreadable()
    return LinkAcknowledgement(
        person_id=_string(_required(record, "person_id")),
        endpoint_ids=_canonical_endpoints(left, right),
        acknowledged=_bool(_required(record, "acknowledged")),
        updated_at=_string(_required(record, "updated_at")),
    )


def _snapshot_from_mapping(parsed: dict[str, object]) -> DurableSnapshot:
    events = tuple(_parse_event(item) for item in _array(parsed, "events"))
    advertisements = tuple(_parse_advertisement(item) for item in _array(parsed, "advertisements"))
    nodes = tuple(_parse_node(item) for item in _array(parsed, "nodes"))
    acknowledgements = tuple(
        _parse_acknowledgement(item) for item in _array(parsed, "acknowledgements")
    )
    revision = None
    if "projection_revision" in parsed:
        revision = _optional_int(parsed["projection_revision"])
    digest = None
    if "projection_digest" in parsed:
        digest = _optional_str(parsed["projection_digest"])
    return DurableSnapshot(
        events=events,
        advertisements=advertisements,
        nodes=nodes,
        acknowledgements=acknowledgements,
        projection_revision=revision,
        projection_digest=digest,
        placed_event_ids=_strings(parsed["placed_event_ids"])
        if "placed_event_ids" in parsed
        else (),
    )


def snapshot_to_json(snapshot: DurableSnapshot) -> str:
    return json.dumps(_snapshot_payload(snapshot), separators=(",", ":"))


def snapshot_from_json(raw: str) -> DurableSnapshot:
    try:
        parsed: object = json.loads(raw)
    except json.JSONDecodeError as error:
        raise _unreadable() from error
    if not isinstance(parsed, dict):
        raise _unreadable()
    return _snapshot_from_mapping(cast(dict[str, object], parsed))


def normalize_durable_snapshot(snapshot: DurableSnapshot) -> DurableSnapshot:
    """Copy the four durable arrays. Acknowledgement endpoint ids are stored in canonical order."""
    return snapshot_from_json(snapshot_to_json(snapshot))
