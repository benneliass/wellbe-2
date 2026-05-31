from __future__ import annotations

from wellbe_contracts.c3_ingestion import (
    AdapterInput,
    AdapterProvenance,
    NormalizedPayload,
    ValidationResult,
)

from wellbe_c3_ingestion.protocol import BaseAdapter


class ManualTextAdapter(BaseAdapter):
    source_type = "manual_text"
    adapter_name = "wellbe-manual-text"
    adapter_version = "0.1.0"

    async def validate(self, raw_input: AdapterInput) -> ValidationResult:
        errors: list[str] = []
        if not raw_input.raw_data:
            errors.append("raw_data must not be empty")
        else:
            try:
                raw_input.raw_data.decode("utf-8")
            except UnicodeDecodeError:
                errors.append("raw_data is not valid UTF-8")
        return ValidationResult(valid=len(errors) == 0, errors=errors)

    async def extract(self, raw_input: AdapterInput) -> NormalizedPayload:
        return NormalizedPayload(
            data=raw_input.raw_data,
            mime_type="text/plain",
            byte_size=len(raw_input.raw_data),
            encoding="utf-8",
        )

    async def metadata(
        self, raw_input: AdapterInput, payload: NormalizedPayload
    ) -> AdapterProvenance:
        return AdapterProvenance(
            source_type=self.source_type,
            captured_at=raw_input.captured_at,
            adapter_name=self.adapter_name,
            adapter_version=self.adapter_version,
            mime_type=payload.mime_type,
            encoding=payload.encoding,
            language=payload.language,
            source_metadata=raw_input.metadata,
        )
