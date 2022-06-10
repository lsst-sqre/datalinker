"""Mock Butler for testing."""

from __future__ import annotations

from typing import Any, Iterator, Optional
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

from lsst.daf import butler

__all__ = ["MockButler", "patch_butler"]


class MockResourcePath:
    """Mock version of `lsst.resources.ResourcePath` for testing."""

    def __init__(self, url: str) -> None:
        self.url = url

    def __str__(self) -> str:
        return self.url

    def size(self) -> int:
        """Returns a fairly random number for testing."""
        return len(self.url) * 10


class MockButler(Mock):
    """Mock of Butler for testing."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(spec=butler.Butler, **kwargs)
        self.uuid = uuid4()
        self.registry = self
        self.datastore = self

    def getDataset(self, uuid: UUID) -> Optional[UUID]:
        return uuid if uuid == self.uuid else None

    def getURI(self, ref: UUID) -> MockResourcePath:
        return MockResourcePath(f"s3://some-bucket/{str(ref)}")


def patch_butler() -> Iterator[MockButler]:
    """Mock out Butler for testing."""
    mock_butler = MockButler()
    with patch.object(butler, "Butler") as mock:
        mock.return_value = mock_butler
        yield mock_butler
