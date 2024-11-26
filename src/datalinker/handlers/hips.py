"""Routes for the HiPS list.

This is not part of the DataLink standard, but it is part of the overall
purpose of datalinker to provide links and registries of other services in
the same Science Platform deployment.  This route is a separate router because
it doesn't require authentication and is served with a different prefix.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from safir.slack.webhook import SlackRouteErrorHandler

from ..dependencies.hips import hips_list_dependency

hips_router = APIRouter(route_class=SlackRouteErrorHandler)
"""FastAPI router for HiPS handlers."""

__all__ = ["hips_router"]


@hips_router.get(
    "/list", response_class=PlainTextResponse, include_in_schema=False
)
async def get_hips_list(
    hips_list: Annotated[str, Depends(hips_list_dependency)],
) -> str:
    return hips_list
