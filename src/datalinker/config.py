"""Configuration definition."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Annotated, Self

import yaml
from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from safir.logging import LogLevel, Profile
from safir.pydantic import HumanTimedelta

__all__ = ["Config"]


class Config(BaseSettings):
    """Configuration for datalinker."""

    model_config = SettingsConfigDict(extra="forbid", populate_by_name=True)

    cutout_sync_url: Annotated[
        HttpUrl,
        Field(
            title="URL to SODA sync API",
            description=(
                "URL to the sync API for the SODA service that does cutouts"
            ),
            validation_alias="cutoutSyncUrl",
        ),
    ]

    links_lifetime: Annotated[
        HumanTimedelta,
        Field(
            title="Lifetime of image links replies",
            description="Should match the lifetime of signed URLs from Butler",
            validation_alias="linksLifetime",
        ),
    ] = timedelta(hours=1)

    log_level: Annotated[
        LogLevel,
        Field(
            title="Log level of the application's logger",
            validation_alias="logLevel",
        ),
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
            validation_alias="pathPrefix",
        ),
    ] = "/api/datalink"

    profile: Annotated[
        Profile,
        Field(title="Application logging profile"),
    ] = Profile.production

    tap_metadata_url: Annotated[
        Path | None,
        Field(
            title="URL to TAP schema metadata",
            description=(
                "URL containing TAP schema metadata used to construct queries"
            ),
            validation_alias="tapMetadataUrl",
        ),
    ] = None

    tap_metadata_dir: Annotated[
        Path | None,
        Field(
            title="Path to TAP YAML metadata",
            description=(
                "Directory containing YAML metadata files about TAP schema"
            ),
            validation_alias="tapMetadataDir",
        ),
    ] = None

    slack_alerts: bool = Field(
        False,
        title="Enable Slack alerts",
        description=(
            "Whether to enable Slack alerts. If true, ``slack_webhook`` must"
            " also be set."
        ),
        validation_alias="slackAlerts",
    )

    slack_webhook: str | None = Field(
        None,
        title="Slack webhook for alerts",
        description=(
            "If set, failures creating user labs or file servers and any"
            " uncaught exceptions in the Nublado controller will be"
            " reported to Slack via this webhook"
        ),
        validation_alias="DATALINKER_SLACK_WEBHOOK",
    )

    @classmethod
    def from_file(cls, path: Path) -> Self:
        """Construct a Configuration object from a configuration file.

        Parameters
        ----------
        path
            Path to the configuration file in YAML.

        Returns
        -------
        Config
            The corresponding `Configuration` object.
        """
        with path.open("r") as f:
            return cls.model_validate(yaml.safe_load(f))
