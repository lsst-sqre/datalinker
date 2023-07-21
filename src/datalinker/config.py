"""Configuration definition."""

from __future__ import annotations

import os
from dataclasses import dataclass

__all__ = ["Configuration", "config"]


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


config = Configuration()
"""Configuration for datalinker."""
