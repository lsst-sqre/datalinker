"""Configuration definition."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Annotated, Self

import yaml
from pydantic import BaseModel, Field, HttpUrl, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from safir.logging import LogLevel, Profile
from safir.pydantic import HumanTimedelta

__all__ = ["Config", "HiPSDatasetConfig"]


class HiPSDatasetConfig(BaseModel):
    """Configuration for a single HiPS dataset."""

    url: Annotated[
        HttpUrl,
        Field(title="Base URL", description="Base URL for this HiPS dataset"),
    ]

    paths: Annotated[
        list[str],
        Field(
            title="HiPS paths",
            description="List of available HiPS paths",
        ),
    ]


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

    hips_base_url: Annotated[
        HttpUrl,
        Field(title="Base URL for HiPS lists", validation_alias="hipsBaseUrl"),
    ]

    hips_datasets: Annotated[
        dict[str, HiPSDatasetConfig],
        Field(
            title="HiPS dataset configurations",
            description=(
                "Mapping of dataset names to their configuration. "
                "Each dataset has a base URL and list of available HiPS paths."
            ),
            validation_alias="hipsDatasets",
        ),
    ] = {}

    hips_default_dataset: Annotated[
        str, Field(validation_alias="hipsDefaultDataset")
    ] = ""
    """The dataset to serve from v1 routes. Must be a key in hips_datasets"""

    hips_path_prefix: Annotated[
        str,
        Field(
            title="URL prefix for HiPS API",
            description="URL prefix used to inject the HiPS list file",
            validation_alias="hipsPathPrefix",
        ),
    ] = "/api/hips"

    hips_v2_path_prefix: Annotated[
        str,
        Field(
            title="URL prefix for HiPS API",
            description="URL prefix used to inject the HiPS list file",
            validation_alias="hipsV2PathPrefix",
        ),
    ] = "/api/hips/v2"

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

    token: str = Field(
        title="Token for API authentication",
        description="Token to use to authenticate to the HiPS service",
        validation_alias="DATALINKER_TOKEN",
    )

    def has_hips_datasets(self) -> bool:
        """Check if any HiPS datasets are configured."""
        return bool(self.hips_datasets)

    def get_default_hips_dataset(self) -> HiPSDatasetConfig:
        """Return the HiPS dataset config for the default dataset.

        Returns
        -------
        HiPSDatasetConfig | None
            The default dataset configuration, or None if not configured.
        """
        return self.hips_datasets[self.hips_default_dataset]

    @model_validator(mode="after")
    def validate_default_hips_dataset(self) -> Self:
        """Validate that the default HiPS dataset exists if specified."""
        if self.hips_default_dataset:
            if not self.hips_datasets:
                msg = (
                    f"HiPS dataset key {self.hips_default_dataset} specified "
                    "but no datasets are configured in hips_datasets"
                )
                raise ValueError(msg)
            if self.hips_default_dataset not in self.hips_datasets:
                msg = (
                    f"HiPS dataset key {self.hips_default_dataset} not found. "
                    f"Available datasets: {list(self.hips_datasets.keys())}"
                )
                raise ValueError(msg)
        return self

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
