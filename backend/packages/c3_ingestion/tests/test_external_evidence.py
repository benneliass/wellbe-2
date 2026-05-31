from __future__ import annotations

import pytest
from wellbe_c3_ingestion.external_evidence import (
    ExternalEvidenceIngestionService,
    ExternalEvidenceSourceInput,
    InvalidSourceQualityTierError,
)


class _ExternalRepo:
    def __init__(self) -> None:
        self.sources: list[dict] = []

    async def insert_external_source(self, **kwargs):
        self.sources.append(kwargs)
        return "external-source-1"


class _VaultWriter:
    def __init__(self) -> None:
        self.called = False

    async def write(self, *args, **kwargs):
        self.called = True


async def test_external_evidence_ingestion_writes_external_graph_not_raw_vault():
    repo = _ExternalRepo()
    vault_writer = _VaultWriter()
    service = ExternalEvidenceIngestionService(repo, vault_writer=vault_writer)

    source_id = await service.ingest_source(
        ExternalEvidenceSourceInput(
            source_type="clinical_guideline",
            source_quality_tier=1,
            tier_reason="Official specialty society guideline",
            title="Migraine guideline",
            citation_text="Guideline citation",
            url="https://example.test/guideline",
            assigned_by="external-evidence-adapter",
        )
    )

    assert source_id == "external-source-1"
    assert vault_writer.called is False
    assert repo.sources[0]["source_quality_tier"] == 1
    assert repo.sources[0]["title"] == "Migraine guideline"


async def test_external_evidence_ingestion_rejects_unknown_quality_tier():
    service = ExternalEvidenceIngestionService(_ExternalRepo())

    with pytest.raises(InvalidSourceQualityTierError):
        await service.ingest_source(
            ExternalEvidenceSourceInput(
                source_type="medical_blog",
                source_quality_tier=9,
                tier_reason="Out of range",
                title="Blog",
                assigned_by="external-evidence-adapter",
            )
        )
