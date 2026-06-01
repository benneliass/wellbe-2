"""C14 workflow transition validation (pure, no I/O)."""

from __future__ import annotations

from wellbe_contracts.c14_investigation import (
    InvestigationStatus,
    is_investigation_edge_allowed,
)

from wellbe_c14_investigation.errors import InvalidInvestigationTransitionError


def validate_investigation_edge(
    from_status: InvestigationStatus, to_status: InvestigationStatus
) -> None:
    if not is_investigation_edge_allowed(from_status, to_status):
        raise InvalidInvestigationTransitionError(from_status, to_status)
