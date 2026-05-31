import pytest


@pytest.mark.asyncio
async def test_vault_writer_health(vault_client):
    resp = await vault_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_ingestion_worker_health(ingestion_client):
    resp = await ingestion_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
