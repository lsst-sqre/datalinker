"""Constants for datalinker."""

from pathlib import Path

__all__ = ["CONFIG_PATH", "CONFIG_PATH_ENV_VAR"]

CONFIG_PATH = Path("/etc/datalinker/config.yaml")
"""Default path to configuration."""

CONFIG_PATH_ENV_VAR = "DATALINKER_CONFIG_PATH"
"""Env var to load config path from."""

ADQL_COMPOUND_TABLE_REGEX = r"^([a-zA-Z0-9_]+\.)?[a-zA-Z0-9_.]+$"
"""ADQL table with optional prefix."""

ADQL_FOREIGN_COLUMN_REGEX = r"^([a-zA-Z0-9_]+\.){1,2}[a-zA-Z0-9_]+$"
"""ADQL table (without prefix)."""

ADQL_IDENTIFIER_REGEX = r"^[a-zA-Z0-9_]+$"
"""ADQL table (without prefix)."""
