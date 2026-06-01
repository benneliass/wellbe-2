from __future__ import annotations

import itertools
import random
import uuid
from datetime import UTC, datetime, timedelta

from wellbe_c11_correction.resolver import CandidateCorrection, resolve_overlays
from wellbe_contracts.c11_correction import (
    AUTHORITY_RANK,
    ActorAuthority,
    CorrectionTargetKind,
    CorrectionType,
)

_T0 = datetime(2026, 6, 1, tzinfo=UTC)
_TARGET = uuid.uuid4()


def _cand(
    *,
    ctype: CorrectionType = CorrectionType.REPLACE_VALUE,
    authority: ActorAuthority = ActorAuthority.CONTROLLER,
    field_path: str | None = None,
    effective: datetime | None = None,
    applied: datetime | None = None,
    supersedes: uuid.UUID | None = None,
    payload: dict | None = None,
    cid: uuid.UUID | None = None,
) -> CandidateCorrection:
    return CandidateCorrection(
        correction_id=cid or uuid.uuid4(),
        correction_type=ctype,
        actor_authority=authority,
        authority_rank=AUTHORITY_RANK[authority],
        semantic_rank=50,
        field_path=field_path,
        effective_at=effective,
        applied_at=applied,
        supersedes_correction_id=supersedes,
        proposed_payload=payload or {},
    )


def _resolve(cands, field_path=None):
    return resolve_overlays(
        target_kind=CorrectionTargetKind.C4_EXTRACTED_FACT,
        target_id=_TARGET,
        field_path=field_path,
        candidates=cands,
    )


def test_no_corrections_returns_base() -> None:
    out = _resolve([])
    assert out.resolved_state == "base"
    assert out.active_correction_id is None
    assert out.explanation_code == "no_applied_corrections"


def test_single_replace_value_overlays() -> None:
    c = _cand(ctype=CorrectionType.REPLACE_VALUE, field_path="dose", payload={"dose": "5mg"})
    out = _resolve([c], field_path="dose")
    assert out.resolved_state == "overlaid"
    assert out.active_correction_id == c.correction_id
    assert out.resolved_value == {"dose": "5mg"}


def test_explicit_supersession_beats_recency() -> None:
    # A applied earlier; B supersedes A even though A is not older by much.
    a = _cand(field_path="dose", applied=_T0, payload={"dose": "A"})
    b = _cand(
        field_path="dose",
        applied=_T0 + timedelta(hours=1),
        payload={"dose": "B"},
        supersedes=a.correction_id,
    )
    out = _resolve([a, b], field_path="dose")
    assert out.active_correction_id == b.correction_id
    assert a.correction_id in out.inactive_correction_ids


def test_authority_rank_controller_beats_delegated() -> None:
    controller = _cand(authority=ActorAuthority.CONTROLLER, field_path="dose", payload={"d": "C"})
    delegated = _cand(
        authority=ActorAuthority.DELEGATED_CONTROLLER, field_path="dose", payload={"d": "D"}
    )
    out = _resolve([delegated, controller], field_path="dose")
    assert out.active_correction_id == controller.correction_id


def test_pending_proposal_excluded_via_authority_threshold() -> None:
    # role_proposed has authority rank 20 < 80 threshold -> not admitted.
    role = _cand(authority=ActorAuthority.ROLE_PROPOSED, field_path="dose", payload={"d": "R"})
    out = _resolve([role], field_path="dose")
    assert out.resolved_state == "base"
    assert out.active_correction_id is None


def test_field_specific_beats_whole_object_for_that_field() -> None:
    whole = _cand(field_path=None, payload={"all": True})
    specific = _cand(field_path="dose", payload={"dose": "specific"})
    out = _resolve([whole, specific], field_path="dose")
    assert out.active_correction_id == specific.correction_id


def test_withdraw_outranks_replace_on_same_field() -> None:
    replace = _cand(ctype=CorrectionType.REPLACE_VALUE, field_path="dose", payload={"dose": "X"})
    withdraw = _cand(ctype=CorrectionType.MARK_INCORRECT, field_path="dose")
    out = _resolve([replace, withdraw], field_path="dose")
    assert out.active_correction_id == withdraw.correction_id
    assert out.resolved_state == "withdrawn"


def test_resolution_is_order_independent() -> None:
    # Build a fixed set; every permutation must produce the same active winner.
    cands = [
        _cand(
            authority=ActorAuthority.CONTROLLER,
            field_path="dose",
            applied=_T0,
            payload={"d": 1},
        ),
        _cand(
            authority=ActorAuthority.CONTROLLER,
            field_path="dose",
            applied=_T0 + timedelta(hours=2),
            payload={"d": 2},
        ),
        _cand(
            authority=ActorAuthority.DELEGATED_CONTROLLER,
            field_path="dose",
            payload={"d": 3},
        ),
        _cand(
            ctype=CorrectionType.ADD_MISSING_CONTEXT,
            field_path="dose",
            payload={"note": "x"},
        ),
    ]
    winners = set()
    for perm in itertools.permutations(cands):
        out = _resolve(list(perm), field_path="dose")
        winners.add(out.active_correction_id)
    assert len(winners) == 1


def test_random_sets_stable_regardless_of_order() -> None:
    rng = random.Random(1234)
    for _ in range(50):
        n = rng.randint(1, 6)
        cands = [
            _cand(
                ctype=rng.choice(list(CorrectionType)),
                authority=rng.choice(
                    [ActorAuthority.CONTROLLER, ActorAuthority.DELEGATED_CONTROLLER]
                ),
                field_path="dose",
                applied=_T0 + timedelta(hours=rng.randint(0, 100)),
                payload={"v": rng.randint(0, 9)},
            )
            for _ in range(n)
        ]
        baseline = _resolve(list(cands), field_path="dose").active_correction_id
        shuffled = cands[:]
        rng.shuffle(shuffled)
        assert _resolve(shuffled, field_path="dose").active_correction_id == baseline
