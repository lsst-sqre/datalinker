"""Models for datalinker."""

from enum import StrEnum

from pydantic import BaseModel, Field
from safir.metadata import Metadata as SafirMetadata

__all__ = ["Band", "Detail", "Index"]


class Band(StrEnum):
    """An abstract filter band for restricting the scope of a query."""

    all = "all"
    u = "u"
    g = "g"
    r = "r"
    i = "i"
    z = "z"
    y = "y"


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
