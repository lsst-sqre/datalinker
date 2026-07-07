"""Test fixtures for datalinker tests."""

from collections.abc import AsyncGenerator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
import respx
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from rubin.repertoire import Discovery, register_mock_discovery
from safir.testing.data import Data

from datalinker import main
from datalinker.config import config

from .support.butler import MockButler, patch_butler


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-test-data",
        action="store_true",
        default=False,
        help="Overwrite expected test output with current results",
    )


@pytest_asyncio.fixture
async def app(
    data: Data, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[FastAPI]:
    """Return a configured test application.

    Wraps the application in a lifespan manager so that startup and shutdown
    events are sent during test execution.
    """
    monkeypatch.setattr(config, "tap_metadata_dir", data.path("metadata"))
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
        headers={
            "X-Auth-Request-Token": "sometoken",
            "X-Auth-Request-User": "some-user",
        },
    ) as client:
        yield client


@pytest.fixture
def data(request: pytest.FixtureRequest) -> Data:
    update = request.config.getoption("--update-test-data")
    return Data(Path(__file__).parent / "data", update_test_data=update)


@pytest.fixture
def mock_butler() -> Iterator[MockButler]:
    """Mock Butler for testing."""
    yield from patch_butler()


@pytest.fixture(autouse=True)
def mock_discovery(
    data: Data, respx_mock: respx.Router, monkeypatch: pytest.MonkeyPatch
) -> Discovery:
    monkeypatch.setenv("REPERTOIRE_BASE_URL", "https://example.com/repertoire")
    return register_mock_discovery(respx_mock, data.path("discovery.json"))
