"""Tests for the datalinker.handlers.external module and routes."""

from unittest.mock import patch
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest
from httpx import AsyncClient
from lsst.daf.butler import LabeledButlerFactory
from safir.metrics import MockEventPublisher
from safir.testing.data import Data

from datalinker.config import config
from datalinker.dependencies.context import context_dependency

from ..support.butler import MockButler


@pytest.mark.asyncio
async def test_get_index(client: AsyncClient) -> None:
    """Test ``GET /api/datalink/``."""
    response = await client.get("/api/datalink/")
    assert response.status_code == 200
    data = response.json()
    metadata = data["metadata"]
    assert metadata["name"] == config.name
    assert isinstance(metadata["version"], str)
    assert isinstance(metadata["description"], str)
    assert isinstance(metadata["repository_url"], str)
    assert isinstance(metadata["documentation_url"], str)


@pytest.mark.asyncio
async def test_cone_search(client: AsyncClient) -> None:
    r = await client.get(
        "/api/datalink/cone_search",
        params={
            "table": "table",
            "ra_col": "ra",
            "dec_col": "dec",
            "ra_val": 57.65657741054437,
            "dec_val": -35.999025781137966,
            "radius": 0.1,
        },
    )
    assert r.status_code == 307
    url = urlparse(r.headers["Location"])
    assert url.path == "/api/tap/sync"
    query = parse_qs(url.query)
    assert query == {
        "LANG": ["ADQL"],
        "REQUEST": ["doQuery"],
        "QUERY": [
            (
                "SELECT * FROM table WHERE CONTAINS(POINT('ICRS',ra,dec),"
                "CIRCLE('ICRS',57.65657741054437,-35.999025781137966,0.1))=1"
            )
        ],
    }

    # Check that some SQL injection is rejected.
    r = await client.get(
        "/api/datalink/cone_search",
        params={
            "table": ";drop table foo;-- ",
            "ra_col": "ra",
            "dec_col": "dec",
            "ra_val": 57.65657741054437,
            "dec_val": -35.999025781137966,
            "radius": 0.1,
        },
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_timeseries(client: AsyncClient) -> None:
    r = await client.get(
        "/api/datalink/timeseries",
        params={
            "id": 18446744073709551617,
            "table": "dp02_dc2_catalogs.ForcedSource",
            "id_column": "objectId",
            "detail": "full",
            "join_time_column": "dp02_dc2_catalogs.CcdVisit.expMidptMJD",
        },
    )
    assert r.status_code == 307
    url = urlparse(r.headers["Location"])
    assert url.path == "/api/tap/sync"
    query = parse_qs(url.query)
    assert query == {
        "LANG": ["ADQL"],
        "REQUEST": ["doQuery"],
        "QUERY": [
            (
                "SELECT t.expMidptMJD,s.* FROM dp02_dc2_catalogs.ForcedSource"
                " AS s JOIN dp02_dc2_catalogs.CcdVisit AS t"
                " ON s.ccdVisitId = t.ccdVisitId"
                " WHERE s.objectId = 18446744073709551617"
            )
        ],
    }

    r = await client.get(
        "/api/datalink/timeseries",
        params={
            "id": 18446744073709551617,
            "table": "dp02_dc2_catalogs.DiaSource",
            "id_column": "diaObjectId",
            "band_column": "filterName",
            "detail": "full",
            "band": "u",
        },
    )
    assert r.status_code == 307
    url = urlparse(r.headers["Location"])
    assert url.path == "/api/tap/sync"
    query = parse_qs(url.query)
    assert query == {
        "LANG": ["ADQL"],
        "REQUEST": ["doQuery"],
        "QUERY": [
            (
                "SELECT s.* FROM dp02_dc2_catalogs.DiaSource AS s"
                " WHERE s.diaObjectId = 18446744073709551617"
                " AND s.filterName = 'u'"
            )
        ],
    }


@pytest.mark.asyncio
async def test_timeseries_detail(client: AsyncClient) -> None:
    r = await client.get(
        "/api/datalink/timeseries",
        params={
            "id": 18446744073709551617,
            "table": "dp02_dc2_catalogs.ForcedSourceOnDiaObject",
            "id_column": "diaObjectId",
            "detail": "principal",
            "join_time_column": "dp02_dc2_catalogs.CcdVisit.expMidptMJD",
        },
    )
    assert r.status_code == 307
    url = urlparse(r.headers["Location"])
    assert url.path == "/api/tap/sync"
    query = parse_qs(url.query)
    assert query == {
        "LANG": ["ADQL"],
        "REQUEST": ["doQuery"],
        "QUERY": [
            (
                "SELECT t.expMidptMJD,s.diaObjectId,s.band,s.psfFlux"
                ",s.psfFluxErr,s.psfDiffFlux,s.psfDiffFluxErr,s.ccdVisitId"
                ",s.forcedSourceOnDiaObjectId"
                " FROM dp02_dc2_catalogs.ForcedSourceOnDiaObject"
                " AS s JOIN dp02_dc2_catalogs.CcdVisit AS t"
                " ON s.ccdVisitId = t.ccdVisitId"
                " WHERE s.diaObjectId = 18446744073709551617"
            )
        ],
    }

    r = await client.get(
        "/api/datalink/timeseries",
        params={
            "id": 18446744073709551617,
            "table": "dp02_dc2_catalogs.ForcedSourceOnDiaObject",
            "id_column": "diaObjectId",
            "detail": "minimal",
        },
    )
    assert r.status_code == 307
    url = urlparse(r.headers["Location"])
    assert url.path == "/api/tap/sync"
    query = parse_qs(url.query)
    assert query == {
        "LANG": ["ADQL"],
        "REQUEST": ["doQuery"],
        "QUERY": [
            (
                "SELECT s.diaObjectId,s.band,s.psfFlux"
                " FROM dp02_dc2_catalogs.ForcedSourceOnDiaObject AS s"
                " WHERE s.diaObjectId = 18446744073709551617"
            )
        ],
    }


@pytest.mark.asyncio
async def test_timeseries_join_style(client: AsyncClient) -> None:
    r = await client.get(
        "/api/datalink/timeseries",
        params={
            "id": 18446744073709551617,
            "table": "dp1.ForcedSource",
            "id_column": "diaObjectId",
            "detail": "principal",
            "join_time_column": "dp1.CcdVisit.expMidptMJD",
            "join_style": "ccdVisit",
        },
    )
    assert r.status_code == 307
    url = urlparse(r.headers["Location"])
    assert url.path == "/api/tap/sync"
    query = parse_qs(url.query)
    assert query == {
        "LANG": ["ADQL"],
        "REQUEST": ["doQuery"],
        "QUERY": [
            (
                "SELECT t.expMidptMJD,s.band,s.detector,s.objectId,"
                "s.psfDiffFlux,s.psfDiffFluxErr,s.psfFlux,s.psfFluxErr,s.visit"
                " FROM dp1.ForcedSource"
                " AS s JOIN dp1.CcdVisit AS t ON s.ccdVisitId = t.ccdVisitId"
                " WHERE s.diaObjectId = 18446744073709551617"
            )
        ],
    }

    r = await client.get(
        "/api/datalink/timeseries",
        params={
            "id": 18446744073709551617,
            "table": "dp1.ForcedSource",
            "id_column": "diaObjectId",
            "detail": "principal",
            "join_time_column": "dp1.CcdVisit.expMidptMJD",
            "join_style": "visit_detector",
        },
    )
    assert r.status_code == 307
    url = urlparse(r.headers["Location"])
    assert url.path == "/api/tap/sync"
    query = parse_qs(url.query)
    assert query == {
        "LANG": ["ADQL"],
        "REQUEST": ["doQuery"],
        "QUERY": [
            (
                "SELECT t.expMidptMJD,s.band,s.detector,s.objectId,"
                "s.psfDiffFlux,s.psfDiffFluxErr,s.psfFlux,s.psfFluxErr,s.visit"
                " FROM dp1.ForcedSource AS s JOIN dp1.CcdVisit AS t"
                " ON (s.visit = t.visitId AND s.detector = t.detector)"
                " WHERE s.diaObjectId = 18446744073709551617"
            )
        ],
    }


def get_dataset_uuid(data: Data, dataset_type: str) -> str:
    """Get a dataset UUID of the desired type."""
    butler_data = data.read_json("butler/datasets")
    for uuid, info in butler_data.items():
        if info["type"] == dataset_type:
            return uuid
    raise AssertionError(f"No UUID found for dataset type {dataset_type}")


@pytest.mark.usefixtures("mock_butler")
@pytest.mark.asyncio
async def test_links(data: Data, client: AsyncClient) -> None:
    dataset_uuid = get_dataset_uuid(data, "calexp")
    dataset_id = f"butler://dr1/{dataset_uuid}"
    butler_data = data.read_json("butler/datasets")
    content_type = "application/x-votable+xml;content=datalink"

    # Use iD to test the IVOA requirement of case insensitive parameters.
    r = await client.get("/api/datalink/links", params={"iD": dataset_id})
    assert r.status_code == 200
    lifetime = int(config.links_lifetime.total_seconds())
    assert r.headers["Cache-Control"] == f"max-age={lifetime}"
    assert r.headers["Content-Type"] == content_type
    data.assert_text_matches(r.text, "links/calexp.xml")

    # Check the same with explicit RESPONSEFORMAT.
    for response_format in ("votable", "application/x-votable+xml"):
        r = await client.get(
            "/api/datalink/links",
            params={"id": dataset_id, "responseformat": response_format},
        )
        assert r.status_code == 200
        assert r.headers["Content-Type"] == content_type
        data.assert_text_matches(r.text, "links/calexp.xml")

    # Check that the appropriate metrics events were posted.
    events = context_dependency._events
    assert events
    assert isinstance(events.links, MockEventPublisher)
    event = {
        "username": "some-user",
        "dataset_id": dataset_id,
        "size": butler_data[dataset_uuid]["size"],
    }
    events.links.published.assert_published_all([event] * 3)


@pytest.mark.asyncio
async def test_links_raw(
    data: Data,
    client: AsyncClient,
    mock_butler: MockButler,
) -> None:
    dataset_uuid = get_dataset_uuid(data, "raw")
    dataset_id = f"butler://dr1/{dataset_uuid}"

    r = await client.get("/api/datalink/links", params={"id": dataset_id})
    assert r.status_code == 200
    data.assert_text_matches(r.text, "links/raw.xml")


@pytest.mark.asyncio
async def test_links_no_cutout(
    data: Data,
    client: AsyncClient,
    mock_butler: MockButler,
) -> None:
    dataset_uuid = get_dataset_uuid(data, "calexp")

    # DR2 has no service discovery information for cutouts.
    dataset_id = f"butler://dr2/{dataset_uuid}"

    r = await client.get("/api/datalink/links", params={"id": dataset_id})
    assert r.status_code == 200
    data.assert_text_matches(r.text, "links/calexp-nocutout.xml")


@pytest.mark.asyncio
async def test_links_errors(
    client: AsyncClient, mock_butler: MockButler
) -> None:
    uuid = uuid4()

    # Test an invalid IDs and ensure it returns 404.
    r = await client.get(
        "/api/datalink/links",
        params={"id": f"butler://dr1/{uuid!s}"},
    )
    assert r.status_code == 404

    # Test malformed IDs and ensure they return 422.
    for test_id in ("butler://", "butler://test-butler", "blah-blah"):
        r = await client.get("/api/datalink/links", params={"id": test_id})
        assert r.status_code == 422

    # Test invalid RESPONSEFORMAT.
    r = await client.get(
        "/api/datalink/links",
        params={
            "id": f"butler://dr1/{uuid!s}",
            "responseformat": "text/plain",
        },
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_links_bad_repo(client: AsyncClient) -> None:
    uuid = uuid4()

    # Rather than using the regular mock Butler, mock it out to raise KeyError
    # from the constructor. This simulates an invalid label.
    with patch.object(LabeledButlerFactory, "create_butler") as mock_butler:
        mock_butler.side_effect = KeyError
        r = await client.get(
            "/api/datalink/links",
            params={"id": f"butler://invalid-repo/{uuid!s}"},
        )
        assert r.status_code == 404
