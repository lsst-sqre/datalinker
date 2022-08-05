"""Internal HTTP handlers that serve relative to the root path, ``/``.

These handlers aren't externally visible since the app is available at a path,
``/datalinker``. See `datalinker.handlers.external` for
the external endpoint handlers.

These handlers should be used for monitoring, health checks, internal status,
or other information that should not be visible outside the Kubernetes cluster.
"""

from email.message import Message
from importlib.metadata import metadata
from typing import cast

from fastapi import APIRouter
from safir.metadata import Metadata, get_project_url

__all__ = ["get_index", "internal_router"]

internal_router = APIRouter()
"""FastAPI router for all internal handlers."""


@internal_router.get(
    "/",
    description=(
        "Return metadata about the running application. Can also be used as"
        " a health check. This route is not exposed outside the cluster and"
        " therefore cannot be used by external clients."
    ),
    response_model=Metadata,
    response_model_exclude_none=True,
    summary="Application metadata",
)
async def get_index() -> Metadata:
    """GET ``/`` (the app's internal root).

    By convention, this endpoint returns only the application's metadata.
    """
    pkg_metadata = cast(Message, metadata("datalinker"))
    return Metadata(
        name="datalinker",
        version=pkg_metadata["Version"],
        description=pkg_metadata["Summary"],
        repository_url=get_project_url(pkg_metadata, "Source"),
        documentation_url=get_project_url(pkg_metadata, "Homepage"),
    )
