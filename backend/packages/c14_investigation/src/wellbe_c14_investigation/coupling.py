"""InvestigationThreadCouplingPolicy.

The single place that decides whether an investigation may close given C7's
authoritative ThreadClosureSnapshots. C14 never recomputes thread closure
criteria (symptom resolution, single-normal-test) — that is C7's job (G4).
"""

from __future__ import annotations

from wellbe_contracts.c7_thread import ThreadClosureSnapshot
from wellbe_contracts.c14_investigation import CloseEvaluation


def evaluate_close(snapshots: list[ThreadClosureSnapshot]) -> CloseEvaluation:
    """An investigation may close only if every relevant linked thread is resolved.

    If any thread is unresolved, closure is denied and the caller should use
    handed_off / monitoring / waiting_for_data instead.
    """
    unmet = [s.thread_id for s in snapshots if not s.is_resolved]
    if unmet:
        return CloseEvaluation(
            allowed=False,
            unmet_thread_ids=unmet,
            reason="linked_threads_unresolved",
        )
    return CloseEvaluation(allowed=True)
