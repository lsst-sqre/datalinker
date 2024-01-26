"""Configuration definition."""

from __future__ import annotations

import os
from enum import Enum
from typing import Annotated

from pydantic import Field, TypeAdapter
from pydantic_settings import BaseSettings, SettingsConfigDict
from safir.logging import LogLevel, Profile

__all__ = [
    "Config",
    "StorageBackend",
    "config",
]


def _get_butler_repositories() -> dict[str, str] | None:
    json = os.getenv("DAF_BUTLER_REPOSITORIES", None)
    if json is not None:
        return TypeAdapter(dict[str, str]).validate_json(json)

    return None


class StorageBackend(Enum):
    """Possible choices for a storage backend."""

    GCS = "GCS"
    S3 = "S3"


class Config(BaseSettings):
    """Configuration for datalinker."""

    cutout_sync_url: Annotated[
        str,
        Field(
            title="URL to SODA sync API",
            description=(
                "URL to the sync API for the SODA service that does cutouts"
            ),
        ),
    ] = ""

    hips_base_url: Annotated[str, Field(title="Base URL for HiPS lists")] = ""

    tap_metadata_dir: Annotated[
        str,
        Field(
            title="Path to TAP YAML metadata",
            description=(
                "Directory containing YAML metadata files about TAP schema"
            ),
        ),
    ] = ""

    token: Annotated[
        str,
        Field(
            title="Token for API authentication",
            description="Token to use to authenticate to the HiPS service",
        ),
    ] = ""

    storage_backend: Annotated[
        StorageBackend,
        Field(
            title="Storage backend",
            description="Which storage backend to use for uploaded files",
            validation_alias="STORAGE_BACKEND",
        ),
    ] = StorageBackend.GCS

    s3_endpoint_url: Annotated[
        str, Field(title="Storage API URL", validation_alias="S3_ENDPOINT_URL")
    ] = "https://storage.googleapis.com"

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
        Field(
            title="Application name",
            description=(
                "The application's name, which doubles as the root HTTP"
                " endpoint path"
            ),
            validation_alias="SAFIR_NAME",
        ),
    ] = "datalinker"

    profile: Annotated[
        Profile,
        Field(
            title="Application logging profile",
            validation_alias="SAFIR_PROFILE",
        ),
    ] = Profile.development

    log_level: Annotated[
        LogLevel,
        Field(
            title="Log level of the application's logger",
            validation_alias="SAFIR_LOG_LEVEL",
        ),
    ] = LogLevel.INFO

    model_config = SettingsConfigDict(
        env_prefix="DATALINKER_", case_sensitive=False
    )


config = Config()
"""Configuration for datalinker."""
