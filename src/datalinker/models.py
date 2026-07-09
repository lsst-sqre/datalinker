"""Models for datalinker."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, Field
from safir.metadata import Metadata as SafirMetadata

__all__ = [
    "Band",
    "DataLinkError",
    "DataLinkRow",
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


class DataLinkError(StrEnum):
    """Standardized error codes for DataLink 1.1."""

    NOT_FOUND = "NotFoundFault"
    USAGE = "UsageFault"
    TRANSIENT = "TransientFault"
    FATAL = "FatalFault"
    DEFAULT = "DefaultFault"


@dataclass
class DataLinkRow:
    """One row of DataLink results."""

    id: str
    """Identifier."""

    error: str | None
    """Error encountered retrieving this dataset."""

    image_url: str | None
    """Signed URL to the underlying image."""

    image_size: int | None
    """Size of the underlying image in bytes."""

    is_raw: bool
    """Whether this row represents a raw (which cutouts don't support)."""

    @classmethod
    def from_error(
        cls, id: str, error_code: DataLinkError, exc: Exception
    ) -> Self:
        """Construct the DataLink row for an error.

        Parameters
        ----------
        id
            Identifier to an image.
        error_code
            Standardized DataLink error code.
        exc
            Underlying exception.

        Returns
        -------
        DataLinkRow
            Data to construct the row in the results table.
        """
        error = f"{error_code.value}: {exc!s}"
        return cls(
            id=id, error=error, image_url=None, image_size=None, is_raw=False
        )


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
