"""Constants for datalinker."""

__all__ = [
    "ADQL_COMPOUND_TABLE_REGEX",
    "ADQL_FOREIGN_COLUMN_REGEX",
    "ADQL_IDENTIFIER_REGEX",
]

ADQL_COMPOUND_TABLE_REGEX = r"^([a-zA-Z0-9_]+\.)?[a-zA-Z0-9_.]+$"
"""ADQL table with optional prefix."""

ADQL_FOREIGN_COLUMN_REGEX = r"^([a-zA-Z0-9_]+\.){1,2}[a-zA-Z0-9_]+$"
"""ADQL table (without prefix)."""

ADQL_IDENTIFIER_REGEX = r"^[a-zA-Z0-9_]+$"
"""ADQL table (without prefix)."""
