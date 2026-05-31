from __future__ import annotations

import os
import uuid

import httpx
import pytest
import pytest_asyncio


VAULT_WRITER_URL = os.environ.get("VAULT_WRITER_URL", "http://localhost:8002")
INGESTION_WORKER_URL = os.environ.get("INGESTION_WORKER_URL", "http://localhost:8003")
PROCESSING_WORKER_URL = os.environ.get("PROCESSING_WORKER_URL", "http://localhost:8004")


@pytest_asyncio.fixture
async def vault_client():
    async with httpx.AsyncClient(base_url=VAULT_WRITER_URL, timeout=30.0) as client:
        yield client


@pytest_asyncio.fixture
async def ingestion_client():
    async with httpx.AsyncClient(base_url=INGESTION_WORKER_URL, timeout=30.0) as client:
        yield client


@pytest_asyncio.fixture
async def processing_client():
    async with httpx.AsyncClient(base_url=PROCESSING_WORKER_URL, timeout=30.0) as client:
        yield client


@pytest.fixture
def patient_id():
    return uuid.uuid4()


@pytest.fixture
def actor_id():
    return uuid.uuid4()


@pytest.fixture
def consent_snapshot_id():
    return uuid.uuid4()
