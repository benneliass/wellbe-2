from __future__ import annotations

from abc import ABC, abstractmethod

from wellbe_contracts.c3_ingestion import (
    AdapterInput,
    AdapterProvenance,
    NormalizedPayload,
    ValidationResult,
)


class BaseAdapter(ABC):
    @property
    @abstractmethod
    def source_type(self) -> str: ...

    @property
    @abstractmethod
    def adapter_name(self) -> str: ...

    @property
    @abstractmethod
    def adapter_version(self) -> str: ...

    @abstractmethod
    async def validate(self, raw_input: AdapterInput) -> ValidationResult: ...

    @abstractmethod
    async def extract(self, raw_input: AdapterInput) -> NormalizedPayload: ...

    @abstractmethod
    async def metadata(
        self, raw_input: AdapterInput, payload: NormalizedPayload
    ) -> AdapterProvenance: ...
