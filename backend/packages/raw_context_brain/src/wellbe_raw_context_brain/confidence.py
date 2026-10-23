"""Suggestion readings and confidence movement.

link and no_link are suggestions. uncertain abstains: it adds no suggestion
and it is not a no_link. Nothing here removes a kept link.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from wellbe_raw_context_brain.types import Judgment, Origin

_CLINICAL_REASON = re.compile(r"diagnos|severity|caused by|cancer|disease", re.IGNORECASE)


@dataclass(frozen=True)
class SuggestionReading:
    kind: Judgment
    adds_suggestion: bool


@dataclass(frozen=True)
class NextConfidenceInput:
    origin: Origin
    proposed: float
    existing_confidence: float | None
    existing_lineages: Sequence[str]
    evidence_lineages: Sequence[str]


def read_suggestion(judgment: Judgment) -> SuggestionReading:
    if judgment == "uncertain":
        return SuggestionReading(kind="uncertain", adds_suggestion=False)
    if judgment == "no_link":
        return SuggestionReading(kind="no_link", adds_suggestion=True)
    return SuggestionReading(kind="link", adds_suggestion=True)


def next_confidence(confidence_input: NextConfidenceInput) -> float:
    """Model confidence cannot rise on an existing edge without a new lineage.

    A new lineage may move confidence up or down. A user correction is returned as proposed.
    """
    if confidence_input.origin != "model" or confidence_input.existing_confidence is None:
        return confidence_input.proposed
    known = set(confidence_input.existing_lineages)
    independent = any(lineage not in known for lineage in confidence_input.evidence_lineages)
    if (
        not independent
        and confidence_input.existing_confidence is not None
        and confidence_input.proposed > confidence_input.existing_confidence
    ):
        return confidence_input.existing_confidence
    return confidence_input.proposed


def is_clinical_reason(code: str) -> bool:
    """True when this reason code is clinical and not a permitted link reason."""
    return _CLINICAL_REASON.search(code) is not None


def association_phrase() -> str:
    """Short conditional association. Not a diagnosis, cause, or severity claim."""
    return "These notes may be associated."
