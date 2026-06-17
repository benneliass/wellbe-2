from __future__ import annotations

import hashlib
import uuid
from uuid import UUID

import httpx
from wellbe_contracts.c2_vault import VaultWriteRequest, VaultWriteResponse
from wellbe_contracts.c3_ingestion import AdapterInput

from wellbe_c3_ingestion.exceptions import IngestionValidationError
from wellbe_c3_ingestion.registry import AdapterRegistry

# Stable namespace for deterministic Vault record ids (uuid5). Changing it would
# break idempotency for already-ingested events, so it is frozen.
_VAULT_ID_NAMESPACE = uuid.UUID("6f9b7c2e-8a4d-5c1f-9e3a-2b6d4f8a1c70")


def deterministic_event_id(
    *,
    actor_id: UUID,
    patient_id: UUID,
    capture_type: str,
    payload_sha256: str,
    client_idempotency_key: str,
) -> UUID:
    """uuid5 of the capture natural key — same logical capture => same Vault id."""
    natural_key = (
        f"{actor_id}|{patient_id}|{capture_type}|{payload_sha256}|{client_idempotency_key}"
    )
    return uuid.uuid5(_VAULT_ID_NAMESPACE, natural_key)


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
        client_idempotency_key: str | None = None,
    ) -> VaultWriteResponse:
        adapter = self._registry.get(adapter_input.source_type)

        validation = await adapter.validate(adapter_input)
        if not validation.valid:
            raise IngestionValidationError(validation.errors)

        payload = await adapter.extract(adapter_input)
        provenance = await adapter.metadata(adapter_input, payload)

        payload_hash = hashlib.sha256(payload.data).hexdigest()

        event_id: UUID | None = None
        if client_idempotency_key:
            capture_type = (adapter_input.metadata or {}).get(
                "capture_type", adapter_input.source_type
            )
            # Scope the idempotency key by actor + capture_type so distinct captures
            # never collide, and derive a deterministic Vault id so retries replay.
            idempotency_key = (
                f"{adapter_input.actor_id}:{capture_type}:{client_idempotency_key}"
            )
            event_id = deterministic_event_id(
                actor_id=adapter_input.actor_id,
                patient_id=adapter_input.patient_id,
                capture_type=capture_type,
                payload_sha256=payload_hash,
                client_idempotency_key=client_idempotency_key,
            )
        else:
            idempotency_key = f"{adapter_input.patient_id}:{payload_hash}"

        write_request = VaultWriteRequest(
            patient_id=adapter_input.patient_id,
            actor_id=adapter_input.actor_id,
            normalized_payload=payload.data,
            adapter_provenance=provenance,
            idempotency_key=idempotency_key,
            event_id=event_id,
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
