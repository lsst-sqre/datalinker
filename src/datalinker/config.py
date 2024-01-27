"""Configuration definition."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Annotated

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from safir.logging import LogLevel, Profile

__all__ = [
    "Config",
    "StorageBackend",
    "config",
]


class StorageBackend(Enum):
    """Possible choices for a storage backend."""

    GCS = "GCS"
    S3 = "S3"


class Config(BaseSettings):
    """Configuration for datalinker."""

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

    tap_metadata_dir: Annotated[
        Path | None,
        Field(
            title="Path to TAP YAML metadata",
            description=(
                "Directory containing YAML metadata files about TAP schema"
            ),
        ),
    ] = None

    token: Annotated[
        str,
        Field(
            title="Token for API authentication",
            description="Token to use to authenticate to the HiPS service",
        ),
    ]

    storage_backend: Annotated[
        StorageBackend,
        Field(
            title="Storage backend",
            description="Which storage backend to use for uploaded files",
        ),
    ] = StorageBackend.GCS

    s3_endpoint_url: Annotated[
        HttpUrl,
        Field(title="Storage API URL", validation_alias="S3_ENDPOINT_URL"),
    ] = HttpUrl("https://storage.googleapis.com")

    # TODO(DM-42660): butler_repositories can be removed once there is a
    # release of daf_butler available that handles DAF_BUTLER_REPOSITORIES
    # itself.
    butler_repositories: Annotated[
        dict[str, str] | None,
        Field(
            title="Butler repository labels",
            description=(
                "Mapping from label to URI for Butler repositories used by"
                " this service. If not set, Butler will ball back to looking"
                " this up from a file whose URI is given in the"
                " `DAF_BUTLER_REPOSITORY_INDEX` environment variable."
            ),
            validation_alias="DAF_BUTLER_REPOSITORIES",
        ),
    ] = None

    name: Annotated[
        str,
        Field(title="Application name"),
    ] = "datalinker"

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

    hips_path_prefix: Annotated[
        str,
        Field(
            title="URL prefix for HiPS API",
            description="URL prefix used to inject the HiPS list file",
        ),
    ] = "/api/hips"

    profile: Annotated[
        Profile,
        Field(
            title="Application logging profile",
        ),
    ] = Profile.production

    log_level: Annotated[
        LogLevel,
        Field(title="Log level of the application's logger"),
    ] = LogLevel.INFO

    slack_webhook: Annotated[
        HttpUrl | None, Field(title="Slack webhook for exception reporting")
    ] = None

    model_config = SettingsConfigDict(
        env_prefix="DATALINKER_", case_sensitive=False
    )


config = Config()
"""Configuration for datalinker."""
