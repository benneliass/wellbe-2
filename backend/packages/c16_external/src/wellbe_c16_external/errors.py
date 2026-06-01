from __future__ import annotations


class ExternalEvidenceError(Exception):
    """Base class for C16 errors."""


class ExternalSourceNotFoundError(ExternalEvidenceError):
    def __init__(self, source_id: object) -> None:
        self.source_id = source_id
        super().__init__(f"External source not found: {source_id}")


class PersonalNodeNotFoundError(ExternalEvidenceError):
    def __init__(self, node_id: object) -> None:
        self.node_id = node_id
        super().__init__(f"Personal node not found: {node_id}")


class TierUpgradeByUsageError(ExternalEvidenceError):
    """Raised if any code path attempts to derive/upgrade a tier from usage."""
