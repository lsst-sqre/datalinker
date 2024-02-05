"""Test fixtures for datalinker tests."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from datetime import timedelta
from pathlib import Path

import boto3
import pytest
import pytest_asyncio
from _pytest.monkeypatch import MonkeyPatch
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import AsyncClient
from moto import mock_aws  # type: ignore[attr-defined]
from pydantic import HttpUrl
from safir.testing.gcs import MockStorageClient, patch_google_storage

from datalinker import main
from datalinker.config import StorageBackend, config

from .support.butler import MockButler, patch_butler


@pytest_asyncio.fixture
async def app(monkeypatch: MonkeyPatch) -> AsyncIterator[FastAPI]:
    """Return a configured test application.

    Wraps the application in a lifespan manager so that startup and shutdown
    events are sent during test execution.
    """
    monkeypatch.setattr(
        config, "tap_metadata_dir", Path(__file__).parent / "data"
    )
    async with LifespanManager(main.app):
        yield main.app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Return an ``httpx.AsyncClient`` configured to talk to the test app.

    Mock the Gafaelfawr delegated token header, needed by endpoints that use
    Butler.
    """
    headers = {"X-Auth-Request-Token": "sometoken"}
    async with AsyncClient(
        app=app, base_url="https://example.com/", headers=headers
    ) as client:
        yield client


@pytest.fixture
def mock_butler() -> Iterator[MockButler]:
    """Mock Butler for testing."""
    yield from patch_butler()


@pytest.fixture
def s3(monkeypatch: MonkeyPatch) -> Iterator[boto3.client]:
    """Mock out S3 for testing."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setattr(config, "storage_backend", StorageBackend.S3)
    monkeypatch.setattr(
        config, "s3_endpoint_url", HttpUrl("https://s3.amazonaws.com/bucket")
    )
    with mock_aws():
        yield boto3.client(
            "s3",
            endpoint_url=str(config.s3_endpoint_url),
            region_name="us-east-1",
        )


@pytest.fixture
def mock_google_storage(
    monkeypatch: MonkeyPatch,
) -> Iterator[MockStorageClient]:
    """Mock out the Google Cloud Storage API."""
    monkeypatch.setattr(config, "storage_backend", StorageBackend.GCS)
    monkeypatch.setattr(
        config, "s3_endpoint_url", HttpUrl("https://storage.googleapis.com")
    )
    yield from patch_google_storage(
        expected_expiration=timedelta(hours=1),
        bucket_name="some-bucket",
    )
