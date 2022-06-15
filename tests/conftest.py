"""Test fixtures for datalinker tests."""

from __future__ import annotations

from typing import AsyncIterator, Iterator
from unittest.mock import patch

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import AsyncClient

from datalinker import main

from .support.butler import MockButler, patch_butler
from .support.gcs import MockStorageClient


@pytest_asyncio.fixture
async def app() -> AsyncIterator[FastAPI]:
    """Return a configured test application.

    Wraps the application in a lifespan manager so that startup and shutdown
    events are sent during test execution.
    """
    async with LifespanManager(main.app):
        yield main.app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Return an ``httpx.AsyncClient`` configured to talk to the test app."""
    async with AsyncClient(app=app, base_url="https://example.com/") as client:
        yield client


@pytest.fixture
def mock_butler() -> Iterator[MockButler]:
    """Mock Butler for testing."""
    yield from patch_butler()


@pytest.fixture
def mock_google_storage() -> Iterator[None]:
    """Mock out the Google Cloud Storage API."""
    mock_gcs = MockStorageClient
    with patch("google.auth.impersonated_credentials.Credentials"):
        with patch("google.auth.default", return_value=(None, None)):
            with patch("google.cloud.storage.Client", side_effect=mock_gcs):
                yield
