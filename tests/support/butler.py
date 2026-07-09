"""Mock Butler for testing."""

from collections.abc import Iterator
from typing import Any, override
from unittest.mock import Mock, patch
from uuid import UUID

from lsst.daf.butler import Butler, LabeledButlerFactory
from lsst.resources import ResourcePath
from safir.testing.data import Data

__all__ = ["MockButler", "patch_butler"]


class MockDatasetRef:
    """Mock of a Butler DatasetRef."""

    def __init__(self, uuid: UUID, dataset_type: str) -> None:
        self.uuid = uuid
        self.datasetType = self
        self.name = dataset_type


class MockButler(Mock):
    """Mock of Butler for testing."""

    def __init__(self, data: Data) -> None:
        super().__init__(spec=Butler)
        self._data = data.read_json("butler/datasets")

    @override
    def _get_child_mock(self, /, **kwargs: Any) -> Mock:
        return Mock(**kwargs)

    def get_dataset(self, uuid: UUID) -> MockDatasetRef | None:
        if dataset := self._data.get(str(uuid)):
            return MockDatasetRef(uuid, dataset["type"])
        return None

    def getURI(self, ref: MockDatasetRef) -> ResourcePath:
        resource_path = ResourcePath(self._data[str(ref.uuid)]["uri"])
        mock = patch.object(resource_path, "size").start()
        mock.return_value = self._data[str(ref.uuid)]["size"]
        return resource_path


def patch_butler(data: Data) -> Iterator[MockButler]:
    """Mock out Butler for testing."""
    mock_butler = MockButler(data)
    with patch.object(LabeledButlerFactory, "create_butler") as mock:
        mock.return_value = mock_butler
        yield mock_butler
