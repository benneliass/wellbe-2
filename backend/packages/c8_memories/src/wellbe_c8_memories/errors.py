from __future__ import annotations

import uuid


class MemoryError(Exception):
    """Base class for C8 memory errors."""


class MemoryNotFoundError(MemoryError):
    def __init__(self, memory_entry_id: uuid.UUID) -> None:
        self.memory_entry_id = memory_entry_id
        super().__init__(f"Memory entry {memory_entry_id} not found")


class VisibleWithoutEvidenceError(MemoryError):
    """Raised when a derived memory entry is made visible without C5 provenance.

    This is the application-level C5 gate; the deferred DB trigger is the backstop.
    """

    def __init__(self, memory_entry_id: uuid.UUID) -> None:
        self.memory_entry_id = memory_entry_id
        super().__init__(
            f"Derived memory entry {memory_entry_id} cannot be visible without a "
            "C5 evidence link (no orphan derived claims)"
        )
