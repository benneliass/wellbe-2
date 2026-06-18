from __future__ import annotations


class GenesisError(Exception):
    """Base class for thread-genesis errors."""


class OrphanCandidateError(GenesisError):
    """Raised when a pending candidate is created with no source provenance.

    A candidate is the lossless destination for a weak signal — but it must still
    trace back to the capture or fact it was noticed from (no orphan claims). A
    candidate with neither a source capture nor a source fact is never created.
    """

    def __init__(self, user_id: object) -> None:
        self.user_id = user_id
        super().__init__(
            f"Pending candidate requires at least one source capture or fact (user {user_id})"
        )


class CandidateNotFoundError(GenesisError):
    """Raised when a candidate lifecycle action targets a missing candidate."""

    def __init__(self, candidate_id: object) -> None:
        self.candidate_id = candidate_id
        super().__init__(f"Candidate {candidate_id} not found")
