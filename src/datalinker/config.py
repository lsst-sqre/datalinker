"""Configuration definition."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from pydantic import TypeAdapter

__all__ = ["Configuration", "config"]


def _get_butler_repositories() -> dict[str, str] | None:
    json = os.getenv("DAF_BUTLER_REPOSITORIES", None)
    if json is not None:
        return TypeAdapter(dict[str, str]).validate_json(json)

    return None


@dataclass
class Configuration:
    """Configuration for datalinker."""

    cutout_url: str = os.getenv("DATALINKER_CUTOUT_SYNC_URL", "")
    """The URL to the sync API for the SODA service that does cutouts.

    Set with the ``DATALINKER_CUTOUT_SYNC_URL`` environment variable.
    """

    hips_base_url: str = os.getenv("DATALINKER_HIPS_BASE_URL", "")
    """The base URL for HiPS lists.

    Set with the ``DATALINKER_HIPS_BASE_URL`` environment variable.
    """

    tap_metadata_dir: str = os.getenv("DATALINKER_TAP_METADATA_DIR", "")
    """Directory containing YAML metadata files about TAP schema.

    Set with the ``DATALINKER_TAP_METADATA_DIR`` environment variable.
    """

    token: str = os.getenv("DATALINKER_TOKEN", "")
    """Token to use to authenticate to the HiPS service.

    Set with the ``DATALINKER_TOKEN`` environment variable.
    """

    storage_backend: str = os.getenv("STORAGE_BACKEND", "GCS")
    """Which backend to use for storage buckets to upload
    files into.

    Set with the ``STORAGE_BACKEND`` environment variable to
    either ```GCS``` or ```S3```.
    """

    name: str = os.getenv("SAFIR_NAME", "datalinker")
    """The application's name, which doubles as the root HTTP endpoint path.

    Set with the ``SAFIR_NAME`` environment variable.
    """

    profile: str = os.getenv("SAFIR_PROFILE", "development")
    """Application run profile: "development" or "production".

    Set with the ``SAFIR_PROFILE`` environment variable.
    """

    logger_name: str = os.getenv("SAFIR_LOGGER", "datalinker")
    """The root name of the application's logger.

    Set with the ``SAFIR_LOGGER`` environment variable.
    """

    log_level: str = os.getenv("SAFIR_LOG_LEVEL", "INFO")
    """The log level of the application's logger.

    Set with the ``SAFIR_LOG_LEVEL`` environment variable.
    """

    s3_endpoint_url: str = os.getenv(
        "S3_ENDPOINT_URL", "https://storage.googleapis.com"
    )
    """The S3 endpoint URL to use.

    Set with the ``S3_ENDPOINT_URL`` environment variable.
    """

    # TODO DM-42660: butler_repositories can be removed once there is a release
    # of daf_butler available that handles DAF_BUTLER_REPOSITORIES itself.
    butler_repositories: dict[str, str] | None = field(
        default_factory=_get_butler_repositories
    )
    """Mapping from label to URI for Butler repositories used by this service.

    Set with the ``DAF_BUTLER_REPOSITORIES`` environment variable.  If not set,
    Butler will fall back to looking this up from a file whose URI is given in
    the ``DAF_BUTLER_REPOSITORY_INDEX`` environment variable.
    """


config = Configuration()
"""Configuration for datalinker."""
