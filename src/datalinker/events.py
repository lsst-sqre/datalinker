"""Metrics events for datalinker."""

from typing import override

from pydantic import Field
from safir.dependencies.metrics import EventMaker
from safir.metrics import EventManager, EventPayload


class LinksEvent(EventPayload):
    """Retrieval of the DataLink links route for an image.

    This includes a signed URL. For rate-limiting purposes, we may assume that
    the user will follow this signed URL and download the resulting image, and
    therefore log its size.
    """

    username: str = Field(
        ...,
        title="Username",
        description="User who retrieved the links record, possibly indirectly",
    )

    dataset_id: str = Field(
        ...,
        title="Dataset ID",
        description="Dataset identifier for which links were retrieved",
    )

    size: int = Field(
        ...,
        title="Size",
        description="Size of the underlying image file, in bytes",
    )


class Events(EventMaker):
    """Event publishers for datalinker metrics.

    Attributes
    ----------
    links
        Event publisher for retrieval of the DataLink links record for an
        image.
    """

    @override
    async def initialize(self, manager: EventManager) -> None:
        self.links = await manager.create_publisher("links", LinksEvent)
