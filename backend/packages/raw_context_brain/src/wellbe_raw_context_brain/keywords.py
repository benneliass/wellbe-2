"""Keyword anchor and the small context map.

A bar is a count of shared stored keywords. It is not a scan of vault text.
The first pass uses three, the next pass uses two, and the last pass uses one.
A lower pass excludes anchors already tried and does not widen a map already built.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass, field

from wellbe_agent_caller import AskFailure, Binding, Field, Purpose, ask, register_purpose
from wellbe_agent_caller.types import Transport

from wellbe_raw_context_brain.types import MiniMap, MiniMapLink, MiniMapNode

KEYWORD_BAR_X = 3
KEYWORD_BAR_Y = 2
KEYWORD_BAR_FLOOR = 1
KEYWORD_BARS = (KEYWORD_BAR_X, KEYWORD_BAR_Y, KEYWORD_BAR_FLOOR)
MINI_MAP_DEPTH = 10
KEYWORD_PURPOSE = "context_keywords"

_KEYWORD_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["keywords"],
    "properties": {
        "keywords": {
            "type": "array",
            "minItems": 5,
            "maxItems": 10,
            "items": {"type": "string"},
        }
    },
}

_INSTRUCTION = (
    "Read the note and return JSON "
    '{"keywords":["..."]} with five to ten short strings that name what the note is about. '
    "These are routing labels. Do not name a condition, rank severity, or assign cause."
)


def _keyword_list(value: object, _payload: Mapping[str, object]) -> bool:
    if not isinstance(value, dict):
        return False
    words = value.get("keywords")
    if not isinstance(words, list) or not 5 <= len(words) <= 10:
        return False
    return all(isinstance(word, str) and word.strip() != "" for word in words)


register_purpose(
    Purpose(
        name=KEYWORD_PURPOSE,
        deadline_ms=60_000,
        max_tokens=256,
        fields=(Field("note", "text"),),
        kind="schema",
        schema=_KEYWORD_SCHEMA,
        instruction=_INSTRUCTION,
        check=_keyword_list,
    )
)


@dataclass(frozen=True)
class AnchorCandidate:
    node_id: str
    keywords: tuple[str, ...]
    inverse_degree: float


@dataclass
class KeywordSession:
    tried: list[str] = field(default_factory=list)
    bar_index: int = 0
    anchor_id: str | None = None


@dataclass(frozen=True)
class MapSource:
    node_id: str
    keywords: tuple[str, ...]
    source_type: str
    captured_at: str
    category: str | None
    content: str | None
    is_hub: bool


def shared_keyword_count(left: tuple[str, ...], right: tuple[str, ...]) -> int:
    return len(set(left) & set(right))


def choose_anchor(
    new_keywords: tuple[str, ...],
    candidates: Sequence[AnchorCandidate],
    *,
    bar: int,
    tried: Collection[str],
) -> str | None:
    """The same-category record with the greatest overlap that clears ``bar``.

    Overlap is the primary rank. Inverse degree breaks a tie, then node id.
    """
    best: AnchorCandidate | None = None
    best_overlap = -1
    excluded = set(tried)
    for candidate in candidates:
        if candidate.node_id in excluded:
            continue
        overlap = shared_keyword_count(new_keywords, candidate.keywords)
        if overlap < bar:
            continue
        if _prefer(candidate, overlap, best, best_overlap):
            best = candidate
            best_overlap = overlap
    if best is None:
        return None
    return best.node_id


def _prefer(
    candidate: AnchorCandidate,
    overlap: int,
    best: AnchorCandidate | None,
    best_overlap: int,
) -> bool:
    if best is None or overlap > best_overlap:
        return True
    if overlap < best_overlap:
        return False
    if candidate.inverse_degree != best.inverse_degree:
        return candidate.inverse_degree > best.inverse_degree
    return candidate.node_id < best.node_id


def build_mini_map(
    *,
    new_id: str,
    anchor_id: str,
    bar: int,
    nodes: Mapping[str, MapSource],
    neighbors: Callable[[str], Sequence[str]],
    excluded: Collection[str] = (),
    depth: int = MINI_MAP_DEPTH,
) -> MiniMap:
    """The new record, the anchor, and content nodes within ``depth`` steps.

    A hub is not listed. Distance 10 is included and distance 11 is not.
    Only the new record carries content.
    """
    blocked = set(excluded)
    distances: dict[str, int] = {anchor_id: 0}
    queue: deque[str] = deque([anchor_id])
    while queue:
        current = queue.popleft()
        if distances[current] >= depth:
            continue
        for nxt in neighbors(current):
            if nxt in blocked or nxt in distances or nxt not in nodes:
                continue
            distances[nxt] = distances[current] + 1
            queue.append(nxt)
    included = [
        node_id
        for node_id, distance in distances.items()
        if distance <= depth and not nodes[node_id].is_hub
    ]
    if new_id in nodes and new_id not in included:
        included.append(new_id)
    included.sort()
    handles = {node_id: f"ih_{index + 1}" for index, node_id in enumerate(included)}
    listed = set(included)
    built: list[MiniMapNode] = []
    for node_id in included:
        source = nodes[node_id]
        targets = sorted(
            {
                handles[nxt]
                for nxt in neighbors(node_id)
                if nxt in listed and nxt != node_id and nxt in handles
            }
        )
        built.append(
            MiniMapNode(
                handle=handles[node_id],
                node_id=node_id,
                keywords=source.keywords,
                source_type=source.source_type,
                captured_at=source.captured_at,
                category=source.category,
                content=source.content if node_id == new_id else None,
                links=tuple(
                    MiniMapLink(source_handle=handles[node_id], target_handle=target)
                    for target in targets
                ),
            )
        )
    return MiniMap(
        anchor_handle=handles[anchor_id],
        anchor_id=anchor_id,
        bar=bar,
        nodes=tuple(built),
    )


def model_payload(mini: MiniMap) -> dict[str, object]:
    """Run-scoped handles, keywords, and links. Node ids stay with the controller."""
    nodes: list[dict[str, object]] = []
    for node in mini.nodes:
        row: dict[str, object] = {
            "handle": node.handle,
            "keywords": list(node.keywords),
            "sourceType": node.source_type,
            "capturedAt": node.captured_at,
            "category": node.category,
            "links": [
                {"source": link.source_handle, "target": link.target_handle}
                for link in node.links
            ],
        }
        if node.content is not None:
            row["content"] = node.content
        nodes.append(row)
    return {"anchor": mini.anchor_handle, "bar": mini.bar, "nodes": nodes}


async def request_keywords(
    text: str,
    *,
    binding: Binding | None,
    transport: Transport | None,
) -> tuple[str, ...] | AskFailure:
    """Ask for five to ten keywords. A failure stores nothing and guesses nothing."""
    if binding is None or transport is None:
        return AskFailure(purpose=KEYWORD_PURPOSE, code="dependency_unavailable")
    result = await ask(
        KEYWORD_PURPOSE,
        {"note": text},
        binding=binding,
        transport=transport,
    )
    if isinstance(result, AskFailure):
        return result
    if not isinstance(result.value, dict):
        return AskFailure(purpose=KEYWORD_PURPOSE, code="invalid_output")
    words = result.value.get("keywords")
    if not isinstance(words, list):
        return AskFailure(purpose=KEYWORD_PURPOSE, code="invalid_output")
    cleaned = tuple(word.strip() for word in words if isinstance(word, str))
    if not _keyword_list({"keywords": list(cleaned)}, {}):
        return AskFailure(purpose=KEYWORD_PURPOSE, code="invalid_output")
    return cleaned
