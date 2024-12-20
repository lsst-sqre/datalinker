"""Configuration definition."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from safir.logging import LogLevel, Profile

__all__ = [
    "Config",
    "config",
]


class Config(BaseSettings):
    """Configuration for datalinker."""

    model_config = SettingsConfigDict(
        env_prefix="DATALINKER_", case_sensitive=False
    )

    cutout_sync_url: Annotated[
        HttpUrl,
        Field(
            title="URL to SODA sync API",
            description=(
                "URL to the sync API for the SODA service that does cutouts"
            ),
        ),
    ]

    hips_base_url: Annotated[HttpUrl, Field(title="Base URL for HiPS lists")]

    hips_path_prefix: Annotated[
        str,
        Field(
            title="URL prefix for HiPS API",
            description="URL prefix used to inject the HiPS list file",
        ),
    ] = "/api/hips"

    log_level: Annotated[
        LogLevel,
        Field(title="Log level of the application's logger"),
    ] = LogLevel.INFO

    name: Annotated[str, Field(title="Application name")] = "datalinker"

    path_prefix: Annotated[
        str,
        Field(
            title="URL prefix for DataLink API",
            description=(
                "This URL prefix is used for the IVOA DataLink API and for"
                " any other helper APIs exposed via DataLink descriptors"
            ),
        ),
    ] = "/api/datalink"

    profile: Annotated[
        Profile,
        Field(title="Application logging profile"),
    ] = Profile.production

    tap_metadata_dir: Annotated[
        Path | None,
        Field(
            title="Path to TAP YAML metadata",
            description=(
                "Directory containing YAML metadata files about TAP schema"
            ),
        ),
    ] = None

    slack_webhook: Annotated[
        SecretStr | None, Field(title="Slack webhook for exception reporting")
    ] = None

    token: Annotated[
        str,
        Field(
            title="Token for API authentication",
            description="Token to use to authenticate to the HiPS service",
        ),
    ]


config = Config()
"""Configuration for datalinker."""
