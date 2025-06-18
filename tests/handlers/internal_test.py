"""Tests for the datalinker.handlers.internal module and routes."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from datalinker.config import Config


@pytest.mark.asyncio
async def test_get_index(client: AsyncClient, config: Config) -> None:
    """Test ``GET /``."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == config.name
    assert isinstance(data["version"], str)
    assert isinstance(data["description"], str)
    assert isinstance(data["repository_url"], str)
    assert isinstance(data["documentation_url"], str)
