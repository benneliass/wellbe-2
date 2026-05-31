from __future__ import annotations

from wellbe_contracts.c3_ingestion import (
    AdapterInput,
    AdapterProvenance,
    NormalizedPayload,
    ValidationResult,
)

from wellbe_c3_ingestion.protocol import BaseAdapter

ALLOWED_MIME_TYPES = {"application/pdf", "image/png", "image/jpeg"}
MAX_DOCUMENT_SIZE = 50 * 1024 * 1024  # 50 MB


class DocumentAdapter(BaseAdapter):
    source_type = "pdf"
    adapter_name = "wellbe-document"
    adapter_version = "0.1.0"

    async def validate(self, raw_input: AdapterInput) -> ValidationResult:
        errors: list[str] = []
        if not raw_input.raw_data:
            errors.append("raw_data must not be empty")

        size = len(raw_input.raw_data)
        if size > MAX_DOCUMENT_SIZE:
            errors.append(
                f"Document size {size} bytes exceeds maximum {MAX_DOCUMENT_SIZE} bytes"
            )

        mime_type = (raw_input.metadata or {}).get("mime_type")
        if mime_type and mime_type not in ALLOWED_MIME_TYPES:
            errors.append(
                f"Unsupported mime_type={mime_type!r}. "
                f"Allowed: {sorted(ALLOWED_MIME_TYPES)}"
            )

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    async def extract(self, raw_input: AdapterInput) -> NormalizedPayload:
        mime_type = (raw_input.metadata or {}).get("mime_type", "application/pdf")
        return NormalizedPayload(
            data=raw_input.raw_data,
            mime_type=mime_type,
            byte_size=len(raw_input.raw_data),
        )

    async def metadata(
        self, raw_input: AdapterInput, payload: NormalizedPayload
    ) -> AdapterProvenance:
        meta = raw_input.metadata or {}
        return AdapterProvenance(
            source_type=self.source_type,
            captured_at=raw_input.captured_at,
            adapter_name=self.adapter_name,
            adapter_version=self.adapter_version,
            mime_type=payload.mime_type,
            original_filename_hash=meta.get("original_filename_hash"),
            source_metadata=raw_input.metadata,
        )
