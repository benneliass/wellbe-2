"""Navigation facet labels and the undirected picture contract."""

from __future__ import annotations

from pathlib import Path

import pytest
from wellbe_raw_context_brain.facets import (
    ALLOWED_FACET_LABELS,
    PICTURE_CONTRACT,
    ROUTE_KINDS,
    assert_picture_contract,
    is_allowed_route_label,
)

_LAB_ROOT = Path(__file__).resolve().parents[4] / "labs" / "raw-context-brain"
_LEGEND = "".join(
    [
        '<p class="legend">',
        "A line is an association. A larger circle is the number of links. "
        "This is not a diagnosis.",
        "</p>",
    ]
)


def test_locks_route_kinds() -> None:
    assert list(ROUTE_KINDS) == ["neighbour", "facet", "temporal", "source", "fallback"]


def test_recognizes_fixed_labels_record_kind_facets_and_neighbours() -> None:
    assert list(ALLOWED_FACET_LABELS) == [
        "Earlier context",
        "Later context",
        "Original record",
        "Stop here",
    ]
    for label in ALLOWED_FACET_LABELS:
        assert is_allowed_route_label(label) is True
    assert is_allowed_route_label("Only notes") is True
    assert is_allowed_route_label("Only results") is True
    assert is_allowed_route_label("Open lentil soup") is True
    assert is_allowed_route_label("Only note") is False
    assert is_allowed_route_label("lentil soup") is False


def test_rejects_a_label_that_names_a_diagnosis_cause_severity_symptom_or_problem_list() -> None:
    rejected = [
        "Only diagnosis",
        "Only CAUSES",
        "Only high severity notes",
        "Only symptoms",
        "Only problem lists",
        "Open the Diagnosis note",
        "Earlier context because",
    ]
    for label in rejected:
        assert is_allowed_route_label(label) is False


def test_holds_the_picture_on_disk_to_undirected_associations() -> None:
    html = (_LAB_ROOT / "index.html").read_text(encoding="utf8")
    graph_source = (_LAB_ROOT / "src" / "viz" / "main.ts").read_text(encoding="utf8")
    assert PICTURE_CONTRACT.lines == "undirected associations"
    assert PICTURE_CONTRACT.color == "record kind"
    assert PICTURE_CONTRACT.size == "number of links"
    assert list(PICTURE_CONTRACT.legend) == [
        "A line is an association",
        "the number of links",
        "not a diagnosis",
    ]
    assert_picture_contract(html, graph_source)


def test_throws_when_the_legend_drops_a_phrase_or_the_graph_draws_a_direction() -> None:
    graph_source = (_LAB_ROOT / "src" / "viz" / "main.ts").read_text(encoding="utf8")
    with pytest.raises(ValueError, match="legend misses"):
        assert_picture_contract('<p class="legend">Color is the kind of record.</p>', graph_source)
    outside = (
        "<p>A line is an association. A larger circle is the number of links. "
        'This is not a diagnosis.</p><p class="legend">Color only.</p>'
    )
    with pytest.raises(ValueError, match="legend misses"):
        assert_picture_contract(outside, graph_source)
    with pytest.raises(ValueError, match="linkArrows"):
        assert_picture_contract(_LEGEND, f"{graph_source}\nlinkArrows: true")
    with pytest.raises(ValueError, match="arrowSize"):
        assert_picture_contract(_LEGEND, f"{graph_source}\narrowSize: 8")
    with pytest.raises(ValueError, match="leads to"):
        assert_picture_contract(_LEGEND, f"{graph_source}\nthis leads to that")
