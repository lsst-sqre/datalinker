"""Handlers for the app's external root, ``/datalinker/``."""

from typing import Annotated

from fastapi import Depends, Form, Query, Request
from safir.models import ErrorLocation

from ..dependencies.context import RequestContext, context_dependency
from ..exceptions import IdentifierError
from ..models import DataLinkRow

_EXAMPLE_IVOID = (
    "ivo://org.rubinobs/usdac/dp1?"
    "repo=dp1&id=58f56d2e-cfd8-44e7-a343-20ebdc1f4127"
)

__all__ = [
    "datalink_dependency",
    "datalink_list_dependency",
    "datalink_list_post_dependency",
]


def datalink_dependency(
    *,
    id: Annotated[str, Query(title="Object ID", examples=[_EXAMPLE_IVOID])],
    context: Annotated[RequestContext, Depends(context_dependency)],
) -> DataLinkRow:
    """Get the DataLink details for one identifier.

    This has to be run in a separate dependency so that it can be run
    synchronously in a thread pool, since Butler does not support async.
    """
    links_service = context.factory.create_links_service()
    try:
        return links_service.get_datalink_for_id(id)
    except IdentifierError as e:
        e.location = ErrorLocation.query
        e.field_path = ["id"]
        raise


def datalink_list_dependency(
    *,
    id: Annotated[
        list[str] | None,
        Query(title="Object ID", examples=[_EXAMPLE_IVOID]),
    ] = None,
    context: Annotated[RequestContext, Depends(context_dependency)],
) -> list[DataLinkRow]:
    """Get the DataLink details for identifiers.

    This has to be run in a separate dependency so that it can be run
    synchronously in a thread pool, since Butler does not support async.
    """
    links_service = context.factory.create_links_service()
    return links_service.build_datalink(id or [])


def datalink_list_post_dependency(
    *,
    request: Request,
    id: Annotated[
        list[str] | None,
        Form(title="Object ID", examples=[_EXAMPLE_IVOID]),
    ] = None,
    context: Annotated[RequestContext, Depends(context_dependency)],
) -> list[DataLinkRow]:
    """Get the DataLink details for identifiers.

    This has to be run in a separate dependency so that it can be run
    synchronously in a thread pool, since Butler does not support async.
    """
    links_service = context.factory.create_links_service()
    return links_service.build_datalink(id or [])
