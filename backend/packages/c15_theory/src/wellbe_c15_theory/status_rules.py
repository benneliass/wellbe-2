"""Assign a Theory status from PERSONAL evidence only (G2).

External context never changes personal support status. This is intentionally
conservative per the decision.
"""

from __future__ import annotations

from wellbe_contracts.c15_theory import TheoryStatus


def status_from_personal_evidence(
    *, evidence_for: int, evidence_against: int, has_missing_data: bool
) -> TheoryStatus:
    """Derive status from counts of personal for/against evidence edges.

    - no personal evidence at all          -> needs_more_data
    - support only                          -> partially_supported
    - contradiction only                    -> contradicted_by_current_data
    - both                                  -> needs_more_data (ambiguous)
    Missing data nudges an otherwise-supported theory back to needs_more_data.
    """
    if evidence_for == 0 and evidence_against == 0:
        return TheoryStatus.NEEDS_MORE_DATA
    if evidence_for > 0 and evidence_against == 0:
        return (
            TheoryStatus.NEEDS_MORE_DATA if has_missing_data else TheoryStatus.PARTIALLY_SUPPORTED
        )
    if evidence_against > 0 and evidence_for == 0:
        return TheoryStatus.CONTRADICTED_BY_CURRENT_DATA
    # Mixed signals: never overstate; ask for more data.
    return TheoryStatus.NEEDS_MORE_DATA
