"""Mock Butler for testing."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
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


class MockDatasetRef:
    """Mock of a Butler DatasetRef."""

    def __init__(self, uuid: UUID, dataset_type: str) -> None:
        self.uuid = uuid
        self.datasetType = self
        self.name = dataset_type


class MockButler(Mock):
    """Mock of Butler for testing."""

    def __init__(self) -> None:
        super().__init__(spec=butler.Butler)
        self.uuid = uuid4()
        self.is_raw = False
        self.registry = self
        self.datastore = self

    def _get_child_mock(self, /, **kwargs: Any) -> Mock:
        return Mock(**kwargs)

    def getDataset(self, uuid: UUID) -> MockDatasetRef | None:
        dataset_type = "raw" if self.is_raw else "calexp"
        if uuid == self.uuid:
            return MockDatasetRef(uuid, dataset_type)
        else:
            return None

    def getURI(self, ref: MockDatasetRef) -> MockResourcePath:
        return MockResourcePath(f"s3://some-bucket/{str(ref.uuid)}")


def patch_butler() -> Iterator[MockButler]:
    """Mock out Butler for testing."""
    mock_butler = MockButler()
    with patch.object(butler, "Butler") as mock:
        mock.return_value = mock_butler
        yield mock_butler
