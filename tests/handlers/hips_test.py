"""Tests for the HiPS list routes."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import respx
from httpx import AsyncClient, Response

from datalinker.config import Config


@pytest.mark.asyncio
async def test_hips_list_serves_default_dataset(
    client: AsyncClient,
    respx_mock: respx.Router,
    config: Config,
) -> None:
    hips_list_template = (
        Path(__file__).parent.parent / "data" / "hips-properties"
    ).read_text()
    hips_lists = []

    default_dataset_config = config.get_default_hips_dataset()
    base_url = str(default_dataset_config.url)

    for path in default_dataset_config.paths:
        url = f"{base_url}/{path}"
        respx_mock.get(url + "/properties").mock(
            return_value=Response(200, text=hips_list_template)
        )
        hips_list = re.sub(
            "^hips_status",
            f"hips_service_url         = {url}\nhips_status",
            hips_list_template,
            flags=re.MULTILINE,
        )
        hips_lists.append(hips_list)

    r = await client.get("/api/hips/list")
    assert r.status_code == 200
    assert r.headers["Content-Type"].startswith("text/plain")
    assert r.text == "\n".join(hips_lists)


@pytest.mark.asyncio
async def test_hips_v2_dataset_list(
    client: AsyncClient,
    respx_mock: respx.Router,
    config: Config,
) -> None:
    hips_list_template = (
        Path(__file__).parent.parent / "data" / "hips-properties"
    ).read_text()

    for dataset_name, dataset_config in config.hips_datasets.items():
        hips_lists = []
        base_url = str(dataset_config.url)
        dataset_paths = dataset_config.paths

        for dataset_path in dataset_paths:
            url = f"{base_url}/{dataset_path}"
            respx_mock.get(url + "/properties").mock(
                return_value=Response(200, text=hips_list_template)
            )
            hips_list = re.sub(
                "^hips_status",
                f"hips_service_url         = {url}\nhips_status",
                hips_list_template,
                flags=re.MULTILINE,
            )
            hips_lists.append(hips_list)

        r = await client.get(f"/api/hips/v2/{dataset_name}/list")
        assert r.status_code == 200
        assert r.headers["Content-Type"].startswith("text/plain")
        assert r.text == "\n".join(hips_lists)

        expected_count = len(dataset_paths)
        actual_sections = [x for x in r.text.split("\n\n") if x.strip()]
        assert len(actual_sections) == expected_count, (
            f"{dataset_name} should have {expected_count} "
            f"datasets, got {len(actual_sections)}"
        )

    r_dp02 = await client.get("/api/hips/v2/dp02/list")
    assert r_dp02.status_code == 200
    assert "images/band_z" in r_dp02.text
    assert "images/2MASS/Color" in r_dp02.text

    r_dp1 = await client.get("/api/hips/v2/dp1/list")
    assert r_dp1.status_code == 200
    assert "images/band_z" not in r_dp1.text
    assert "images/2MASS/Color" not in r_dp1.text

    dp02_sections = [x for x in r_dp02.text.split("\n\n") if x.strip()]
    dp1_sections = [x for x in r_dp1.text.split("\n\n") if x.strip()]
    assert len(dp02_sections) > len(dp1_sections), (
        "DP0.2 should have more datasets than DP1"
    )


@pytest.mark.asyncio
async def test_hips_v2_unknown_dataset(client: AsyncClient) -> None:
    r = await client.get("/api/hips/v2/unknown/list")
    assert r.status_code == 404
    assert "unknown" in r.json()["detail"]
    assert "dp02" in r.json()["detail"]


@pytest.mark.asyncio
async def test_hips_properties_fetch_failure(
    client: AsyncClient,
    respx_mock: respx.Router,
    config: Config,
) -> None:
    default_dataset_config = config.get_default_hips_dataset()
    base_url = str(default_dataset_config.url)
    paths = default_dataset_config.paths

    for dataset_path in paths:
        url = f"{base_url}/{dataset_path}"
        respx_mock.get(url + "/properties").mock(
            return_value=Response(404, text="Not Found")
        )

    r = await client.get("/api/hips/list")
    assert r.status_code == 200
    assert len(r.text) == 0


@pytest.mark.asyncio
async def test_hips_list_caching(
    client: AsyncClient,
    respx_mock: respx.Router,
    config: Config,
) -> None:
    hips_list_template = (
        Path(__file__).parent.parent / "data" / "hips-properties"
    ).read_text()

    default_dataset_config = config.get_default_hips_dataset()
    base_url = str(default_dataset_config.url)

    for path in default_dataset_config.paths:
        respx_mock.get(f"{base_url}/{path}/properties").mock(
            return_value=Response(200, text=hips_list_template)
        )

    r1 = await client.get("/api/hips/list")
    assert r1.status_code == 200

    initial_call_count = len(respx_mock.calls)
    r2 = await client.get("/api/hips/list")
    assert r2.status_code == 200
    assert r2.text == r1.text
    assert len(respx_mock.calls) == initial_call_count
