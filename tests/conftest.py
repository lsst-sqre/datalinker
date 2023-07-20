"""Test fixtures for datalinker tests."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from datetime import timedelta
from pathlib import Path

import boto3
import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import AsyncClient
from moto import mock_s3
from safir.testing.gcs import MockStorageClient, patch_google_storage

from datalinker import main
from datalinker.config import config

from .support.butler import MockButler, patch_butler


@pytest_asyncio.fixture
async def app() -> AsyncIterator[FastAPI]:
    """Return a configured test application.

    Wraps the application in a lifespan manager so that startup and shutdown
    events are sent during test execution.
    """
    config.tap_metadata_dir = str(Path(__file__).parent / "data")
    async with LifespanManager(main.app):
        yield main.app
    config.tap_metadata_dir = ""


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Return an ``httpx.AsyncClient`` configured to talk to the test app."""
    async with AsyncClient(app=app, base_url="https://example.com/") as client:
        yield client


@pytest.fixture
def mock_butler() -> Iterator[MockButler]:
    """Mock Butler for testing."""
    yield from patch_butler()


@pytest.fixture(scope="function")
def aws_credentials() -> None:
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture(scope="function")
def s3(aws_credentials: None) -> boto3.client:
    with mock_s3():
        yield boto3.client("s3", region_name="us-east-1")


@pytest.fixture(scope="function")
def mock_google_storage() -> Iterator[MockStorageClient]:
    """Mock out the Google Cloud Storage API."""
    config.google_credentials = "creds.ini"
    yield from patch_google_storage(
        expected_expiration=timedelta(hours=1),
        bucket_name="some-bucket",
    )
    config.google_credentials = ""
