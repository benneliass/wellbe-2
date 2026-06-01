from __future__ import annotations

import pytest
from wellbe_c14_investigation.errors import InvalidInvestigationTransitionError
from wellbe_c14_investigation.state_machine import validate_investigation_edge
from wellbe_contracts.c14_investigation import (
    ALLOWED_INVESTIGATION_TRANSITIONS,
    InvestigationStatus,
    is_investigation_edge_allowed,
)

ALL = list(InvestigationStatus)


def _allowed():
    return [(f, t) for f, ts in ALLOWED_INVESTIGATION_TRANSITIONS.items() for t in ts]


def _disallowed():
    return [
        (f, t) for f in ALL for t in ALL if not is_investigation_edge_allowed(f, t)
    ]


@pytest.mark.parametrize("f,t", _allowed())
def test_allowed_edges(f, t):
    validate_investigation_edge(f, t)


@pytest.mark.parametrize("f,t", _disallowed())
def test_disallowed_edges(f, t):
    with pytest.raises(InvalidInvestigationTransitionError):
        validate_investigation_edge(f, t)


def test_handed_off_only_to_monitoring_or_closed():
    assert ALLOWED_INVESTIGATION_TRANSITIONS[InvestigationStatus.HANDED_OFF] == frozenset(
        {InvestigationStatus.MONITORING, InvestigationStatus.CLOSED}
    )


def test_closed_only_reopens_to_open():
    assert ALLOWED_INVESTIGATION_TRANSITIONS[InvestigationStatus.CLOSED] == frozenset(
        {InvestigationStatus.OPEN}
    )
