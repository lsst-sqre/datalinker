"""Configuration definition."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Annotated

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from safir.logging import LogLevel, Profile
from safir.pydantic import HumanTimedelta

__all__ = ["Config", "config"]


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

    links_lifetime: Annotated[
        HumanTimedelta,
        Field(
            title="Lifetime of image links replies",
            description="Should match the lifetime of signed URLs from Butler",
        ),
    ] = timedelta(hours=1)

    log_level: Annotated[
        LogLevel, Field(title="Log level of the application's logger")
    ] = LogLevel.INFO

    log_profile: Annotated[
        Profile, Field(title="Application logging profile")
    ] = Profile.production

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

    tap_metadata_url: Annotated[
        Path | None,
        Field(
            title="URL to TAP schema metadata",
            description=(
                "URL containing TAP schema metadata used to construct queries"
            ),
        ),
    ] = None

    tap_metadata_dir: Annotated[
        Path | None,
        Field(
            title="Path to TAP YAML metadata",
            description=(
                "Directory containing YAML metadata files about TAP schema"
            ),
        ),
    ] = None

    slack_webhook: str | None = Field(
        None,
        title="Slack webhook for alerts",
        description=(
            "If set, failures creating user labs or file servers and any"
            " uncaught exceptions in the Nublado controller will be"
            " reported to Slack via this webhook"
        ),
    )


config = Config()
"""Configuration for datalinker."""
