from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from wellbe_contracts.c5_evidence import EvidenceLinkType


class EdgeCategory(StrEnum):
    CAUSAL = "causal"
    CORRELATION = "correlation"
    TEMPORAL = "temporal"
    THERAPEUTIC = "therapeutic"
    ADVERSE = "adverse"
    CONTRADICTION = "contradiction"
    REFINEMENT = "refinement"


LINK_TYPE_WEIGHTS: dict[EvidenceLinkType, float] = {
    EvidenceLinkType.PRIMARY: 1.0,
    EvidenceLinkType.CORROBORATING: 0.6,
    EvidenceLinkType.CONTRADICTING: -0.4,
    EvidenceLinkType.CONTEXTUAL: 0.2,
}

CONTRADICTION_PENALTY = 0.3


@dataclass(frozen=True)
class ScoreInput:
    link_type: EvidenceLinkType
    confidence: float
    edge_category: str


@dataclass(frozen=True)
class ScoreResult:
    potential_score: float
    score_version: int
    score_inputs: dict


class PotentialScoreComputer:
    """Compute the potential_score for a graph edge based on evidence inputs.

    The score reflects how likely a relationship truly exists between two nodes.
    It is NOT a diagnostic confidence — it is an internal quality/provenance metric.

    Algorithm:
    1. Sum weighted evidence inputs (link_type weight * confidence)
    2. Apply contradiction penalty if contradicting evidence exists
    3. Normalize to [0, 1] range
    """

    VERSION = 1

    def compute(self, inputs: list[ScoreInput]) -> ScoreResult:
        if not inputs:
            return ScoreResult(
                potential_score=0.0,
                score_version=self.VERSION,
                score_inputs={"evidence_count": 0},
            )

        weighted_sum = 0.0
        max_possible = 0.0
        has_contradiction = False

        for inp in inputs:
            weight = LINK_TYPE_WEIGHTS.get(inp.link_type, 0.2)
            if weight < 0:
                has_contradiction = True
                weighted_sum += weight * inp.confidence
            else:
                weighted_sum += weight * inp.confidence
                max_possible += weight

        if max_possible > 0:
            raw_score = weighted_sum / max_possible
        else:
            raw_score = 0.0

        if has_contradiction:
            raw_score = max(0.0, raw_score - CONTRADICTION_PENALTY)

        potential_score = max(0.0, min(1.0, raw_score))

        return ScoreResult(
            potential_score=round(potential_score, 4),
            score_version=self.VERSION,
            score_inputs={
                "evidence_count": len(inputs),
                "has_contradiction": has_contradiction,
                "weighted_sum": round(weighted_sum, 4),
                "max_possible": round(max_possible, 4),
            },
        )
