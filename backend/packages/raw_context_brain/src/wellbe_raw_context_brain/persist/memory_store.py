"""In-process GraphStore. snapshot() is a JSON copy another lab can be built from."""

from __future__ import annotations

from wellbe_raw_context_brain.persist.graph_store import (
    DurableSnapshot,
    empty_durable_snapshot,
    normalize_durable_snapshot,
)


class MemoryGraphStore:
    def __init__(self) -> None:
        self._current = empty_durable_snapshot()

    def load(self) -> DurableSnapshot:
        return normalize_durable_snapshot(self._current)

    def save(self, snapshot: DurableSnapshot) -> None:
        self._current = normalize_durable_snapshot(snapshot)

    def snapshot(self) -> DurableSnapshot:
        return self.load()

    def replace(self, snapshot: DurableSnapshot) -> None:
        self.save(snapshot)
