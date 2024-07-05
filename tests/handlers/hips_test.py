"""Tests for the HiPS list routes."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import respx
from httpx import AsyncClient, Response
from pydantic import HttpUrl

from datalinker.config import config
from datalinker.constants import HIPS_DATASETS


@pytest.mark.asyncio
async def test_hips_list(
    client: AsyncClient,
    respx_mock: respx.Router,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hips_list_template = (
        Path(__file__).parent.parent / "data" / "hips-properties"
    ).read_text()
    hips_lists = []
    for dataset in HIPS_DATASETS:
        url = f"https://hips.example.com/{dataset}"
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

    monkeypatch.setattr(
        config, "hips_base_url", HttpUrl("https://hips.example.com")
    )
    r = await client.get("/api/hips/list")
    assert r.status_code == 200
    assert r.headers["Content-Type"].startswith("text/plain")
    assert r.text == "\n".join(hips_lists)
