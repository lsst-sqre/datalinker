"""Test fixtures for datalinker tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from datalinker import main
from datalinker.config import Config
from datalinker.dependencies.config import config_dependency
from datalinker.dependencies.hips import (
    dataset_hips_list_dependency,
    hips_list_dependency,
)

from .constants import TEST_DATA_DIR
from .support.butler import MockButler, patch_butler


@pytest.fixture
def config(monkeypatch: pytest.MonkeyPatch) -> Config:
    """Return a configured test configuration."""
    config_path = TEST_DATA_DIR / "config" / "base.yaml"
    config_dependency.set_config_path(config_path)
    config = config_dependency.config()
    monkeypatch.setattr(
        config, "tap_metadata_dir", Path(__file__).parent / "data"
    )
    return config


@pytest_asyncio.fixture
async def app(monkeypatch: pytest.MonkeyPatch) -> AsyncGenerator[FastAPI]:
    """Return a configured test application.

    Wraps the application in a lifespan manager so that startup and shutdown
    events are sent during test execution.
    """
    config_path = TEST_DATA_DIR / "config" / "base.yaml"
    config_dependency.set_config_path(config_path)
    config = config_dependency.config()
    monkeypatch.setattr(
        config, "tap_metadata_dir", Path(__file__).parent / "data"
    )
    async with LifespanManager(main.app):
        yield main.app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient]:
    """Return an ``httpx.AsyncClient`` configured to talk to the test app.

    Mock the Gafaelfawr delegated token header, needed by endpoints that use
    Butler.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="https://example.com/",
        headers={"X-Auth-Request-Token": "sometoken"},
    ) as client:
        yield client


@pytest.fixture
def mock_butler() -> Iterator[MockButler]:
    """Mock Butler for testing."""
    yield from patch_butler()


@pytest.fixture(autouse=True)
def clear_hips_cache() -> Iterator[None]:
    """Clear HiPS dependency caches between tests."""
    # Clear caches before test
    hips_list_dependency.clear_cache()
    dataset_hips_list_dependency.clear_cache()

    yield

    # Clear caches after test
    hips_list_dependency.clear_cache()
    dataset_hips_list_dependency.clear_cache()
