from __future__ import annotations

import hashlib
from uuid import UUID

import httpx

from wellbe_contracts.c2_vault import VaultWriteRequest, VaultWriteResponse
from wellbe_contracts.c3_ingestion import AdapterInput

from wellbe_c3_ingestion.exceptions import IngestionValidationError
from wellbe_c3_ingestion.registry import AdapterRegistry


class IngestionService:
    def __init__(self, registry: AdapterRegistry, vault_writer_url: str) -> None:
        self._registry = registry
        self._client = httpx.AsyncClient(
            base_url=vault_writer_url, timeout=30.0
        )

    async def ingest(
        self,
        adapter_input: AdapterInput,
        consent_snapshot_id: UUID,
        correlation_id: str,
        trace_id: str,
        share_grant_id: UUID | None = None,
    ) -> VaultWriteResponse:
        adapter = self._registry.get(adapter_input.source_type)

        validation = await adapter.validate(adapter_input)
        if not validation.valid:
            raise IngestionValidationError(validation.errors)

        payload = await adapter.extract(adapter_input)
        provenance = await adapter.metadata(adapter_input, payload)

        payload_hash = hashlib.sha256(payload.data).hexdigest()
        idempotency_key = f"{adapter_input.patient_id}:{payload_hash}"

        write_request = VaultWriteRequest(
            patient_id=adapter_input.patient_id,
            actor_id=adapter_input.actor_id,
            normalized_payload=payload.data,
            adapter_provenance=provenance,
            idempotency_key=idempotency_key,
            consent_snapshot_id=consent_snapshot_id,
            share_grant_id=share_grant_id,
            correlation_id=correlation_id,
            trace_id=trace_id,
            mime_type=payload.mime_type,
            encoding=payload.encoding,
            language=payload.language,
            original_filename_hash=provenance.original_filename_hash,
            source_metadata=provenance.source_metadata,
        )

        response = await self._client.post(
            "/vault/events",
            content=write_request.model_dump_json(),
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return VaultWriteResponse.model_validate(response.json())

    async def close(self) -> None:
        await self._client.aclose()
