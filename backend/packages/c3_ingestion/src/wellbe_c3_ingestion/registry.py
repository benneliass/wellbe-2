from __future__ import annotations

from wellbe_c3_ingestion.protocol import BaseAdapter


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, BaseAdapter] = {}

    def register(self, adapter: BaseAdapter) -> None:
        self._adapters[adapter.source_type] = adapter

    def get(self, source_type: str) -> BaseAdapter:
        try:
            return self._adapters[source_type]
        except KeyError:
            raise KeyError(
                f"No adapter registered for source_type={source_type!r}. "
                f"Available: {sorted(self._adapters)}"
            ) from None

    def available_types(self) -> list[str]:
        return sorted(self._adapters)
