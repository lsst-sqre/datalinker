"""Routes for the HiPS list.

This is not part of the DataLink standard, but it is part of the overall
purpose of datalinker to provide links and registries of other services in
the same Science Platform deployment.  This route is a separate router because
it doesn't require authentication and is served with a different prefix.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path
from fastapi.responses import PlainTextResponse
from safir.slack.webhook import SlackRouteErrorHandler

from ..dependencies.hips import (
    dataset_hips_list_dependency,
    hips_list_dependency,
)

hips_router = APIRouter(route_class=SlackRouteErrorHandler)
"""FastAPI router for HiPS handlers."""

# V2 HiPS router (mounted at hips_v2_path_prefix)
hips_v2_router = APIRouter(route_class=SlackRouteErrorHandler)
"""FastAPI router for v2 HiPS handlers."""

__all__ = ["hips_router", "hips_v2_router"]


@hips_router.get(
    "/list", response_class=PlainTextResponse, include_in_schema=False
)
async def get_hips_list(
    hips_list: Annotated[str, Depends(hips_list_dependency)],
) -> str:
    return hips_list


@hips_v2_router.get(
    "/{dataset}/list",
    response_class=PlainTextResponse,
    include_in_schema=False,
)
async def get_v2_dataset_hips_list(
    *,
    dataset: Annotated[
        str,
        Path(
            title="Dataset name",
            description="Dataset identifier (e.g. 'dp02', 'dp1')",
            examples=["dp02", "dp1"],
        ),
    ],
    hips_list: Annotated[str, Depends(dataset_hips_list_dependency)],
) -> str:
    return hips_list
