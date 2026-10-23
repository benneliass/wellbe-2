"""One relation from the lab set.

Conflict without comparable claim, time, units, and subject stays a possible association.
same_record_group is only hub membership. The default structural reason is recorded_association.
"""

from __future__ import annotations

from wellbe_raw_context_brain.types import Independence, Origin, Relation, SourceArrival

RELATION_LABEL: dict[Relation, str] = {
    "explicitly_linked": "you linked these",
    "same_record_group": "same record",
    "derived_or_copied": "copied from another record",
    "near_in_time": "close in time",
    "possible_semantic_association": "may relate",
    "possible_inconsistency": "may not match",
}

RECORD_KINDS: dict[str, dict[str, object]] = {
    "note": {"label": "Note", "hex": "#ed9e38", "rgb": (0.93, 0.62, 0.22)},
    "lab_text": {"label": "Result", "hex": "#5494e6", "rgb": (0.33, 0.58, 0.9)},
    "image_caption": {"label": "Image", "hex": "#59c77a", "rgb": (0.35, 0.78, 0.48)},
    "pdf_extract": {"label": "File", "hex": "#b86bd1", "rgb": (0.72, 0.42, 0.82)},
    "hub": {"label": "Record", "hex": "#9ea8b3", "rgb": (0.62, 0.66, 0.7)},
}

LEGEND_KINDS = ("note", "lab_text", "image_caption", "pdf_extract")


def map_relation(origin: Origin, reason_code: str) -> Relation:
    if origin == "user_correction" and reason_code != "withdrawal":
        return "explicitly_linked"
    if reason_code == "membership":
        return "same_record_group"
    if reason_code == "temporal_neighbour":
        return "near_in_time"
    if reason_code == "derived_or_copied":
        return "derived_or_copied"
    if reason_code == "possible_conflict":
        return "possible_inconsistency"
    return "possible_semantic_association"


def arrival_name(arrival: SourceArrival | None) -> str:
    if arrival == "typed":
        return "Typed"
    if arrival == "copied":
        return "Copied"
    if arrival == "imported":
        return "Imported"
    return "—"


def independence_name(independence: Independence | None) -> str:
    """Known independence can support a source family. Unknown must not."""
    if independence == "unknown":
        return "Not known"
    return "Known"


def source_name(source_type: str) -> str:
    """Names a source the way Memory does: Note, Result, Image, or File."""
    known = RECORD_KINDS.get(source_type)
    if known is None:
        return "Record"
    label = known["label"]
    if isinstance(label, str):
        return label
    return "Record"
