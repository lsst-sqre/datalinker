"""Handlers for the app's external root, ``/datalinker/``."""

from typing import Annotated, Literal
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import RedirectResponse
from safir.dependencies.gafaelfawr import (
    auth_dependency,
    auth_logger_dependency,
)
from safir.dependencies.logger import logger_dependency
from safir.metadata import get_metadata
from safir.models import ErrorLocation
from safir.slack.webhook import SlackRouteErrorHandler
from structlog.stdlib import BoundLogger

from ..config import config
from ..constants import (
    ADQL_COMPOUND_TABLE_REGEX,
    ADQL_FOREIGN_COLUMN_REGEX,
    ADQL_IDENTIFIER_REGEX,
)
from ..dependencies.context import RequestContext, context_dependency
from ..dependencies.tap import TAPMetadata, tap_metadata_dependency
from ..events import LinksEvent
from ..exceptions import IdentifierError
from ..models import Band, DataLinkRow, Detail, Index
from ..templates import templates

external_router = APIRouter(route_class=SlackRouteErrorHandler)
"""FastAPI router for all external handlers."""

__all__ = ["external_router"]


def _create_tap_redirect(sql: str, logger: BoundLogger) -> str:
    """Construct the URL for a redirect to TAP to run the provided SQL.

    Parameters
    ----------
    sql
        SQL to run, with all parameters already filled in.
    logger
        Logger to log the redirect action.

    Returns
    -------
    str
        URL to execute a synchronous TAP query.
    """
    params = {"LANG": "ADQL", "REQUEST": "doQuery", "QUERY": sql}
    url = "/api/tap/sync?" + urlencode(params)
    logger.info(f"Redirecting to {url}")
    return url


def _get_tap_columns(table: str, detail: Detail, metadata: TAPMetadata) -> str:
    """Get the list of columns for a TAP query.

    Parameters
    ----------
    table
        Fully-qualified name of the table.
    detail
        Level of detail desired.
    metadata
        Cached TAP table metadata.

    Returns
    -------
    str
        The SQL expresion for columns to retrieve.
    """
    columns_str = "s.*"
    if detail == Detail.minimal:
        columns = metadata.get(table, {}).get("lsst:minimal", [])
        if columns:
            columns_str = ",".join([f"s.{c}" for c in columns])
    elif detail == Detail.principal:
        columns = metadata.get(table, {}).get("tap:principal", [])
        if columns:
            columns_str = ",".join([f"s.{c}" for c in columns])
    return columns_str


@external_router.get(
    "/",
    response_model_exclude_none=True,
    summary="Application metadata",
)
async def get_index() -> Index:
    """GET ``/datalinker/`` (the app's external root).

    By convention, the root of the external API includes a field called
    ``metadata`` that provides the same Safir-generated metadata as the
    internal root endpoint.
    """
    return Index(
        metadata=get_metadata(
            package_name="datalinker", application_name=config.name
        )
    )


@external_router.get("/cone_search", response_class=RedirectResponse)
async def cone_search(
    *,
    table: Annotated[
        str, Query(title="Table name", pattern=ADQL_COMPOUND_TABLE_REGEX)
    ],
    ra_col: Annotated[
        str, Query(title="Column for ra", pattern=ADQL_IDENTIFIER_REGEX)
    ],
    dec_col: Annotated[
        str, Query(title="Column for dec", pattern=ADQL_IDENTIFIER_REGEX)
    ],
    ra_val: Annotated[float, Query(title="ra value")],
    dec_val: Annotated[float, Query(title="dec value")],
    radius: Annotated[float, Query(title="Radius of cone")],
    logger: Annotated[BoundLogger, Depends(auth_logger_dependency)],
) -> str:
    adql = (
        f"SELECT * FROM {table} WHERE"
        f" CONTAINS(POINT('ICRS',{ra_col},{dec_col}),"
        f"CIRCLE('ICRS',{ra_val},{dec_val},{radius})"
        ")=1"
    )
    return _create_tap_redirect(adql, logger)


@external_router.get("/timeseries", response_class=RedirectResponse)
async def timeseries(
    *,
    id: Annotated[int, Query(title="Object identifier")],
    table: Annotated[
        str, Query(title="Table name", pattern=ADQL_COMPOUND_TABLE_REGEX)
    ],
    id_column: Annotated[
        str, Query(title="Object ID column", pattern=ADQL_IDENTIFIER_REGEX)
    ],
    band_column: Annotated[
        str, Query(title="Band column", pattern=ADQL_IDENTIFIER_REGEX)
    ] = "band",
    band: Annotated[Band, Query(title="Abstract filter band")] = Band.all,
    detail: Annotated[Detail, Query(title="Column detail")] = Detail.full,
    join_time_column: Annotated[
        str | None,
        Query(
            title="Foreign column for time variable",
            pattern=ADQL_FOREIGN_COLUMN_REGEX,
        ),
    ] = None,
    join_style: Annotated[
        Literal["ccdVisit", "visit_detector"], Query(title="Join style")
    ] = "ccdVisit",
    tap_metadata: Annotated[TAPMetadata, Depends(tap_metadata_dependency)],
    logger: Annotated[BoundLogger, Depends(logger_dependency)],
) -> str:
    columns = _get_tap_columns(table, detail, tap_metadata)

    # Some time series tables are normalized and don't have a time in them.
    # In those cases we have to join with another table on ccdVisitId.
    if join_time_column:
        join_table, time_column = join_time_column.rsplit(".", 1)
        if join_style == "visit_detector":
            join_clause = "(s.visit = t.visitId AND s.detector = t.detector)"
        else:
            join_clause = "s.ccdVisitId = t.ccdVisitId"
        adql = (
            f"SELECT t.{time_column},{columns} FROM {table} AS s"
            f" JOIN {join_table} AS t ON {join_clause}"
        )
    else:
        adql = f"SELECT {columns} FROM {table} AS s"

    adql += f" WHERE s.{id_column} = {id}"
    if band != Band.all:
        adql += f" AND s.{band_column} = '{band.value}'"

    return _create_tap_redirect(adql, logger)


def datalink_dependency(
    *,
    request: Request,
    id: Annotated[
        list[str] | None,
        Query(
            title="Object ID",
            examples=[
                "butler://dp02/58f56d2e-cfd8-44e7-a343-20ebdc1f4127",
                "ivo://org.rubinobs/usdac/dp1?"
                "repo=dp1&id=58f56d2e-cfd8-44e7-a343-20ebdc1f4127",
            ],
        ),
    ] = None,
    responseformat: Annotated[
        Literal["votable", "application/x-votable+xml"],
        Query(title="Response format"),
    ] = "application/x-votable+xml",
    context: Annotated[RequestContext, Depends(context_dependency)],
) -> list[DataLinkRow]:
    """Get the DataLink details for identifiers.

    This has to be run in a separate dependency so that it can be run
    synchronously in a thread pool, since Butler does not support async.
    """
    links_service = context.factory.create_links_service()
    try:
        return links_service.build_datalink(id or [])
    except IdentifierError as e:
        e.location = ErrorLocation.query
        e.field_path = ["id"]
        raise


@external_router.get(
    "/links",
    responses={404: {"description": "Specified identifier not found"}},
    summary="DataLink links for object",
)
async def links(
    *,
    results: Annotated[list[DataLinkRow], Depends(datalink_dependency)],
    username: Annotated[str, Depends(auth_dependency)],
    context: Annotated[RequestContext, Depends(context_dependency)],
) -> Response:
    # Get the cutout sync URL for the first dataset ID.
    #
    # This is semantically incorrect: Different data releases may have
    # different cutout sync URLs, so each dataset ID from a different data
    # release should have its own set of service descriptors with the cutout
    # sync URL corresponding to that data release. Ignore that for now since
    # at the moment we have one cutout service for all data releases, so just
    # use the first ID.
    #
    # If the first ID is unparsable but subsequent IDs are valid, this will
    # fail to include cutout service descriptors or table entries. This is a
    # bug, but an annoying one to fix. Leave it for now and revisit if we fix
    # the problem of per-data-release cutout URLs.
    cutout_sync_url = None
    if len(results) > 0:
        links_service = context.factory.create_links_service()
        dataset_id = results[0].id
        cutout_sync_url = await links_service.get_cutout_sync_url(dataset_id)

    # Publish a metrics event for each successful result.
    for result in results:
        if result.error:
            continue
        event = LinksEvent(
            username=username, dataset_id=result.id, size=result.image_size
        )
        await context.events.links.publish(event)

    # Construct and return the results.
    lifetime = int(config.links_lifetime.total_seconds())
    include_cutouts = any(not r.is_raw and not r.error for r in results)
    return templates.TemplateResponse(
        context.request,
        "links.xml.jinja",
        {
            "records": results,
            "cutout_sync_url": cutout_sync_url,
            "include_cutouts": include_cutouts,
        },
        headers={"Cache-Control": f"max-age={lifetime}"},
        media_type="application/x-votable+xml;content=datalink",
    )
