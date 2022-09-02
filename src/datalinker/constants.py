"""Constants for datalinker."""

ADQL_COMPOUND_TABLE_REGEX = r"^([a-zA-Z0-9_]+\.)?[a-zA-Z0-9_.]+$"
"""ADQL table with optional prefix."""

ADQL_FOREIGN_COLUMN_REGEX = r"^([a-zA-Z0-9_]+\.){1,2}[a-zA-Z0-9_]+$"
"""ADQL table (without prefix)."""

ADQL_IDENTIFIER_REGEX = r"^[a-zA-Z0-9_]+$"
"""ADQL table (without prefix)."""

HIPS_DATASETS = (
    "images/color_gri",
    "images/color_riz",
    "images/band_u",
    "images/band_g",
    "images/band_r",
    "images/band_i",
    "images/band_z",
    "images/band_y",
)
"""HiPS data sets to include in the HiPS list."""
