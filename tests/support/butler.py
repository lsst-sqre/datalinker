"""Mock Butler for testing."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

from lsst.daf.butler import Butler, LabeledButlerFactory
from lsst.resources import ResourcePath

__all__ = ["MockButler", "patch_butler"]


class MockDatasetRef:
    """Mock of a Butler DatasetRef."""

    def __init__(self, uuid: UUID, dataset_type: str) -> None:
        self.uuid = uuid
        self.datasetType = self
        self.name = dataset_type


class MockButler(Mock):
    """Mock of Butler for testing."""

    def __init__(self) -> None:
        super().__init__(spec=Butler)
        self.uuid = uuid4()
        self.is_raw = False
        self.mock_uri: str | None = None

    def _generate_mock_uri(self, ref: MockDatasetRef) -> str:
        if self.mock_uri is None:
            return f"s3://some-bucket/{ref.uuid!s}"
        return self.mock_uri

    def _get_child_mock(self, /, **kwargs: Any) -> Mock:
        return Mock(**kwargs)

    def get_dataset(self, uuid: UUID) -> MockDatasetRef | None:
        dataset_type = "raw" if self.is_raw else "calexp"
        if uuid == self.uuid:
            return MockDatasetRef(uuid, dataset_type)
        else:
            return None

    def getURI(self, ref: MockDatasetRef) -> ResourcePath:
        resource_path = ResourcePath(self._generate_mock_uri(ref))
        # 'size' does I/O, so mock it out
        mock = patch.object(resource_path, "size").start()
        mock.return_value = 1234
        return resource_path


def patch_butler() -> Iterator[MockButler]:
    """Mock out Butler for testing."""
    mock_butler = MockButler()
    with patch.object(LabeledButlerFactory, "create_butler") as mock:
        mock.return_value = mock_butler
        yield mock_butler
