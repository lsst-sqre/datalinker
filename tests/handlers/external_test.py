"""Tests for the datalinker.handlers.external module and routes."""

from __future__ import annotations

from unittest.mock import patch
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest
from httpx import AsyncClient
from jinja2 import Environment, PackageLoader, select_autoescape
from lsst.daf import butler

from datalinker.config import config

from ..support.butler import MockButler


@pytest.mark.asyncio
async def test_get_index(client: AsyncClient) -> None:
    """Test ``GET /api/datalink/``"""
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
async def test_links(
    client: AsyncClient, mock_butler: MockButler, mock_google_storage: None
) -> None:
    r = await client.get(
        "/api/datalink/links",
        params={"iD": f"butler://label/{str(mock_butler.uuid)}"},
    )
    assert r.status_code == 200

    env = Environment(
        loader=PackageLoader("datalinker"), autoescape=select_autoescape()
    )
    template = env.get_template("links.xml")
    expected = template.render(
        cutout=True,
        id=f"butler://label/{str(mock_butler.uuid)}",
        image_url=f"https://example.com/{str(mock_butler.uuid)}",
        image_size=len(f"s3://some-bucket/{str(mock_butler.uuid)}") * 10,
        cutout_url=config.cutout_url,
    )
    assert r.text == expected

    # Check the same with explicit RESPONSEFORMAT.
    for response_format in ("votable", "application/x-votable+xml"):
        r = await client.get(
            "/api/datalink/links",
            params={
                "iD": f"butler://label/{str(mock_butler.uuid)}",
                "responseformat": response_format,
            },
        )
        assert r.status_code == 200
        assert r.text == expected


@pytest.mark.asyncio
async def test_links_raw(
    client: AsyncClient, mock_butler: MockButler, mock_google_storage: None
) -> None:
    mock_butler.is_raw = True
    r = await client.get(
        "/api/datalink/links",
        params={"id": f"butler://label-raw/{str(mock_butler.uuid)}"},
    )
    assert r.status_code == 200

    env = Environment(
        loader=PackageLoader("datalinker"), autoescape=select_autoescape()
    )
    template = env.get_template("links.xml")
    expected = template.render(
        cutout=False,
        id=f"butler://label-raw/{str(mock_butler.uuid)}",
        image_url=f"https://example.com/{str(mock_butler.uuid)}",
        image_size=len(f"s3://some-bucket/{str(mock_butler.uuid)}") * 10,
        cutout_url=config.cutout_url,
    )
    assert r.text == expected
    assert "cutout-sync" not in r.text


@pytest.mark.asyncio
async def test_links_errors(
    client: AsyncClient, mock_butler: MockButler, mock_google_storage: None
) -> None:
    uuid = uuid4()

    # Test an invalid IDs and ensure it returns 404.
    r = await client.get(
        "/api/datalink/links",
        params={"id": f"butler://test-butler/{str(uuid)}"},
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
            "id": f"butler://test-butler/{str(uuid)}",
            "responseformat": "text/plain",
        },
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_links_bad_repo(client: AsyncClient) -> None:
    uuid = uuid4()

    # Rather than using the regular mock Butler, mock it out to raise
    # FileNotFoundError from the constructor.  This simulates an invalid
    # label.
    with patch.object(butler, "Butler") as mock_butler:
        mock_butler.side_effect = FileNotFoundError
        r = await client.get(
            "/api/datalink/links",
            params={"id": f"butler://invalid-repo/{str(uuid)}"},
        )
        assert r.status_code == 404
