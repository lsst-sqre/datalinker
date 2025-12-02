"""Models for datalinker."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum

from pydantic import BaseModel, Field
from safir.metadata import Metadata as SafirMetadata

__all__ = [
    "Band",
    "DataLink",
    "Detail",
    "Index",
]


class Band(StrEnum):
    """An abstract filter band for restricting the scope of a query."""

    all = "all"
    u = "u"
    g = "g"
    r = "r"
    i = "i"
    z = "z"
    y = "y"


@dataclass
class DataLink:
    """DataLink information for an identifier."""

    id: str
    """Identifier."""

    image_url: str
    """Signed URL to the underlying image."""

    image_size: int
    """Size of the underlying image in bytes."""

    cutout_sync_url: str | None
    """URL to the sync SODA service to create cutouts for this image."""

    def to_dict(self) -> dict[str, str | None]:
        """Convert to a dictionary of template variables."""
        return asdict(self)


class Detail(StrEnum):
    """Amount of column detail to return from a query."""

    minimal = "minimal"
    principal = "principal"
    full = "full"


class Index(BaseModel):
    """Metadata returned by the external root URL of the application.

    Notes
    -----
    As written, this is not very useful. Add additional metadata that will be
    helpful for a user exploring the application, or replace this model with
    some other model that makes more sense to return from the application API
    root.
    """

    metadata: SafirMetadata = Field(..., title="Package metadata")
