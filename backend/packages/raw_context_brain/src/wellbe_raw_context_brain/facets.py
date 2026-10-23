"""Route kinds a walk may advertise. A neighbour label may vary. These kinds do not."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

RouteKindName = Literal["neighbour", "facet", "temporal", "source", "fallback"]

ROUTE_KINDS: tuple[RouteKindName, ...] = ("neighbour", "facet", "temporal", "source", "fallback")

ALLOWED_FACET_LABELS: tuple[str, ...] = (
    "Earlier context",
    "Later context",
    "Original record",
    "Stop here",
)

_FORBIDDEN_LABEL = re.compile(r"diagnosis|cause|severity|symptom|problem list", re.IGNORECASE)
_RECORD_KIND_FACET = re.compile(r"^Only .+s$")
_NEIGHBOUR_LABEL = re.compile(r"^Open .+$")
_LEGEND = re.compile(
    r'<([a-z0-9]+)[^>]*\bclass="[^"]*\blegend\b[^"]*"[^>]*>(.*?)</\1>',
    re.IGNORECASE | re.DOTALL,
)

_GRAPH_FORBIDDEN = ("linkArrows", "arrowSize", "leads to")


@dataclass(frozen=True)
class PictureContract:
    lines: str
    color: str
    size: str
    legend: tuple[str, ...]


PICTURE_CONTRACT = PictureContract(
    lines="undirected associations",
    color="record kind",
    size="number of links",
    legend=("A line is an association", "the number of links", "not a diagnosis"),
)


def is_allowed_route_label(label: str) -> bool:
    """A fixed label, a record-kind facet such as "Only notes", or a varying neighbour label."""
    if _FORBIDDEN_LABEL.search(label):
        return False
    if label in ALLOWED_FACET_LABELS:
        return True
    if _RECORD_KIND_FACET.search(label):
        return True
    return _NEIGHBOUR_LABEL.search(label) is not None


def assert_picture_contract(html: str, graph_source: str) -> None:
    legend = _legend_text(html)
    for phrase in PICTURE_CONTRACT.legend:
        if phrase not in legend:
            raise ValueError(f"picture contract: legend misses {phrase}")
    for token in _GRAPH_FORBIDDEN:
        if token in graph_source:
            raise ValueError(f"picture contract: graph source contains {token}")


def _legend_text(html: str) -> str:
    match = _LEGEND.search(html)
    if match is None or match.group(2) is None:
        raise ValueError("picture contract: html has no legend")
    return match.group(2)
