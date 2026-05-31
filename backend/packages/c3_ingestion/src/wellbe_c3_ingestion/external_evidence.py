from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Protocol


class InvalidSourceQualityTierError(ValueError):
    pass


class ExternalEvidenceRepository(Protocol):
    async def insert_external_source(self, **kwargs: object) -> object: ...


@dataclass(frozen=True)
class ExternalEvidenceSourceInput:
    source_type: str
    source_quality_tier: int
    tier_reason: str
    title: str
    assigned_by: str
    citation_text: str | None = None
    url: str | None = None
    doi: str | None = None
    publisher: str | None = None
    publication_date: date | None = None
    version_label: str | None = None
    source_metadata: dict | None = None


class ExternalEvidenceIngestionService:
    """C3 adapter path for external evidence.

    External medical sources belong in C16 (`external_kg`), never in the
    patient-scoped Raw Context Vault. This service intentionally accepts an
    external repository rather than a vault-writer dependency.
    """

    def __init__(
        self,
        repository: ExternalEvidenceRepository,
        *,
        vault_writer: object | None = None,
    ) -> None:
        self._repository = repository
        self._vault_writer = vault_writer

    async def ingest_source(self, source: ExternalEvidenceSourceInput) -> object:
        if source.source_quality_tier < 1 or source.source_quality_tier > 5:
            raise InvalidSourceQualityTierError(
                "source_quality_tier must be between 1 and 5"
            )

        now = datetime.now(UTC).replace(tzinfo=None)
        return await self._repository.insert_external_source(
            source_type=source.source_type,
            source_quality_tier=source.source_quality_tier,
            tier_reason=source.tier_reason,
            title=source.title,
            citation_text=source.citation_text,
            url=source.url,
            doi=source.doi,
            publisher=source.publisher,
            publication_date=source.publication_date,
            version_label=source.version_label,
            retraction_status="not_retracted",
            assigned_by=source.assigned_by,
            assigned_at=now,
            source_metadata=source.source_metadata,
            created_at=now,
            updated_at=now,
        )
