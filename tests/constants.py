"""Constants for crawlspace tests."""

from pathlib import Path

__all__ = ["TEST_DATA_DIR"]


TEST_DATA_DIR = Path(__file__).parent / "data"
"""Directory that contains test data."""
