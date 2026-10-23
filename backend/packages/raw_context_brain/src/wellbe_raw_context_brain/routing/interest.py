"""Temporary pending-interest state for one person.

Equivalent in-flight requests share one nonce. The same nonce replays one saved result.
A joined caller keeps the in-flight nonce. Its own nonce is not recorded.
clear drops the session. Nothing here is graph topology.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, replace
from typing import Literal


@dataclass(frozen=True)
class InterestBudgets:
    deadline_ms: int
    max_in_flight: int


@dataclass(frozen=True)
class SemanticInterest:
    person_id: str
    purpose: str
    authorization_epoch: int
    snapshot_revision: int
    snapshot_digest: str
    budgets: InterestBudgets
    operation: str
    nonce: str


@dataclass(frozen=True)
class PendingBegin:
    """Shared slot. The first satisfy resolves it once."""

    state: Literal["pending"]
    nonce: str
    joined: bool
    done: asyncio.Future[object]


@dataclass(frozen=True)
class SatisfiedBegin:
    state: Literal["satisfied"]
    nonce: str
    result: object


@dataclass(frozen=True)
class RejectedBegin:
    state: Literal["rejected"]
    reason: Literal["wrong_purpose"]


BeginResult = PendingBegin | SatisfiedBegin | RejectedBegin


class PendingInterestTable:
    def __init__(self) -> None:
        self._by_nonce: dict[str, _Slot] = {}
        self._by_join: dict[str, str] = {}

    def begin(self, interest: SemanticInterest, work_key: str) -> BeginResult:
        known = self._by_nonce.get(interest.nonce)
        if known is not None:
            if known.interest.purpose != interest.purpose:
                return RejectedBegin(state="rejected", reason="wrong_purpose")
            if known.state == "satisfied":
                return SatisfiedBegin(
                    state="satisfied",
                    nonce=known.interest.nonce,
                    result=known.result,
                )
            return _pending_begin(known, joined=False)

        key = _join_key(interest, work_key)
        in_flight_nonce = self._by_join.get(key)
        in_flight = self._by_nonce.get(in_flight_nonce) if in_flight_nonce is not None else None
        if in_flight is not None and in_flight.state == "pending":
            return _pending_begin(in_flight, joined=True)

        slot = _Slot(
            interest=_copy_interest(interest),
            state="pending",
            deferred=asyncio.get_running_loop().create_future(),
        )
        self._by_nonce[interest.nonce] = slot
        self._by_join[key] = interest.nonce
        return _pending_begin(slot, joined=False)

    def satisfy(self, nonce: str, result: object) -> None:
        slot = self._by_nonce.get(nonce)
        if slot is None or slot.state == "satisfied":
            return
        slot.state = "satisfied"
        slot.result = result
        slot.deferred.set_result(result)

    def clear(self) -> None:
        for slot in self._by_nonce.values():
            if slot.state != "pending":
                continue
            slot.deferred.add_done_callback(_retrieve_exception)
            slot.deferred.set_exception(RuntimeError("session_expired"))
        self._by_nonce.clear()
        self._by_join.clear()


def create_pending_interest_table() -> PendingInterestTable:
    return PendingInterestTable()


@dataclass
class _Slot:
    interest: SemanticInterest
    state: Literal["pending", "satisfied"]
    deferred: asyncio.Future[object]
    result: object = None


def _pending_begin(slot: _Slot, *, joined: bool) -> PendingBegin:
    return PendingBegin(
        state="pending",
        nonce=slot.interest.nonce,
        joined=joined,
        done=slot.deferred,
    )


def _join_key(interest: SemanticInterest, work_key: str) -> str:
    """Nonce is a request id, not part of equivalence."""
    return json.dumps(
        [
            interest.person_id,
            interest.purpose,
            interest.operation,
            interest.snapshot_revision,
            work_key,
        ],
        separators=(",", ":"),
    )


def _copy_interest(interest: SemanticInterest) -> SemanticInterest:
    return replace(interest, budgets=replace(interest.budgets))


def _retrieve_exception(future: asyncio.Future[object]) -> None:
    if not future.cancelled():
        future.exception()
