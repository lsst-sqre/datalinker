"""Tests for the datalinker.handlers.download module and routes."""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from safir.metrics import MockEventPublisher
from safir.testing.data import Data

from datalinker.config import config
from datalinker.dependencies.context import context_dependency

from ..support.butler import get_dataset_uuid


@pytest.mark.usefixtures("mock_butler")
@pytest.mark.asyncio
async def test_download_ivoid(data: Data, client: AsyncClient) -> None:
    butler_data = data.read_json("butler/datasets")
    dataset_uuid = get_dataset_uuid(data, "calexp")
    dataset_id = f"butler://dr1/{dataset_uuid}"

    r = await client.get("/download", params={"id": dataset_id})
    assert r.status_code == 307
    lifetime = int(config.links_lifetime.total_seconds())
    assert r.headers["Cache-Control"] == f"max-age={lifetime}"
    assert r.headers["Location"] == butler_data[dataset_uuid]["uri"]

    # Check that the appropriate metrics events were posted.
    events = context_dependency._events
    assert events
    assert isinstance(events.links, MockEventPublisher)
    event = {
        "username": "some-user",
        "dataset_id": dataset_id,
        "size": butler_data[dataset_uuid]["size"],
    }
    events.links.published.assert_published_all([event])

    # A malformed UUID should produce a 422 error.
    r = await client.get("/download", params={"id": "foo"})
    assert r.status_code == 422

    # An unknown IVOID should produce a 404 error.
    bad_id = f"butler://dr1/{uuid4()}"
    r = await client.get("/download", params={"id": bad_id})
    assert r.status_code == 404
