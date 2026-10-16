"""Handlers for the download API."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi.responses import RedirectResponse
from safir.dependencies.gafaelfawr import auth_dependency
from safir.models import ErrorLocation
from safir.slack.webhook import SlackRouteErrorHandler

from ..config import config
from ..dependencies.context import RequestContext, context_dependency
from ..dependencies.datalink import datalink_dependency
from ..events import LinksEvent
from ..exceptions import IdentifierNotFoundError
from ..models import DataLinkRow

download_router = APIRouter(route_class=SlackRouteErrorHandler)

__all__ = ["download_router"]


@download_router.get(
    "",
    response_class=RedirectResponse,
    summary="Download by IVOID",
    description="Download a file from the Butler by IVOID",
)
async def get_download_ivoid(
    *,
    response: Response,
    result: Annotated[DataLinkRow, Depends(datalink_dependency)],
    username: Annotated[str, Depends(auth_dependency)],
    context: Annotated[RequestContext, Depends(context_dependency)],
) -> str:
    lifetime = int(config.links_lifetime.total_seconds())
    if not result.image_url:
        raise IdentifierNotFoundError(result.id, ErrorLocation.query, ["id"])
    event = LinksEvent(
        username=username, dataset_id=result.id, size=result.image_size
    )
    await context.events.links.publish(event)
    response.headers["Cache-Control"] = f"max-age={lifetime}"
    return result.image_url
