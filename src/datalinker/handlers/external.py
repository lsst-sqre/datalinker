"""Handlers for the app's external root, ``/datalinker/``."""

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from safir.dependencies.logger import logger_dependency
from safir.metadata import get_metadata
from structlog.stdlib import BoundLogger

from ..config import config
from ..models import Index

__all__ = ["get_index", "external_router"]

external_router = APIRouter()
"""FastAPI router for all external handlers."""


@external_router.get(
    "/",
    description=(
        "Document the top-level API here. By default it only returns metadata"
        " about the application."
    ),
    response_model=Index,
    response_model_exclude_none=True,
    summary="Application metadata",
)
async def get_index(
    logger: BoundLogger = Depends(logger_dependency),
) -> Index:
    """GET ``/datalinker/`` (the app's external root).

    Customize this handler to return whatever the top-level resource of your
    application should return. For example, consider listing key API URLs.
    When doing so, also change or customize the response model in
    `datalinker.models.Index`.

    By convention, the root of the external API includes a field called
    ``metadata`` that provides the same Safir-generated metadata as the
    internal root endpoint.
    """
    # There is no need to log simple requests since uvicorn will do this
    # automatically, but this is included as an example of how to use the
    # logger for more complex logging.
    logger.info("Request for application metadata")

    metadata = get_metadata(
        package_name="datalinker",
        application_name=config.name,
    )
    return Index(metadata=metadata)


@external_router.get("/cone_search", response_class=RedirectResponse)
async def cone_search(
    table: str,
    ra_col: str,
    dec_col: str,
    ra_val: str,
    dec_val: str,
    radius: str,
    logger: BoundLogger = Depends(logger_dependency),
) -> RedirectResponse:

    url = (
        "/api/tap/sync?LANG=ADQL&REQUEST=doQuery"
        + f"&QUERY=SELECT+*+FROM+{table}+WHERE+CONTAINS("
        + f"POINT('ICRS',{ra_col},{dec_col}),"
        + f"CIRCLE('ICRS',{ra_val},{dec_val},{radius})"
        + ")=1"
    )

    logger.info(f"Redirecting to {url}")
    return url
