import uuid

import pytest


@pytest.mark.asyncio
async def test_vault_event_not_found_returns_404(vault_client):
    """GET for a non-existent event returns 404."""
    fake_id = uuid.uuid4()
    resp = await vault_client.get(f"/vault/events/{fake_id}")
    assert resp.status_code == 404
