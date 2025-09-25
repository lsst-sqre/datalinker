"""Handlers for the app's external root, ``/datalinker/``."""

from typing import Annotated, Literal
from urllib.parse import urlencode

import jinja2
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from lsst.daf.butler import Butler, LabeledButlerFactory
from rubin.repertoire import DiscoveryClient, discovery_dependency
from safir.dependencies.gafaelfawr import auth_delegated_token_dependency
from safir.dependencies.logger import logger_dependency
from safir.metadata import get_metadata
from safir.slack.webhook import SlackRouteErrorHandler
from structlog.stdlib import BoundLogger

from ..config import config
from ..constants import (
    ADQL_COMPOUND_TABLE_REGEX,
    ADQL_FOREIGN_COLUMN_REGEX,
    ADQL_IDENTIFIER_REGEX,
)
from ..dependencies.tap import TAPMetadata, tap_metadata_dependency
from ..models import Band, Detail, Index

external_router = APIRouter(route_class=SlackRouteErrorHandler)
"""FastAPI router for all external handlers."""

_BUTLER_FACTORY = LabeledButlerFactory()
"""Factory for creating Butlers from a label and Gafaelfawr token."""

_environment = jinja2.Environment(
    loader=jinja2.PackageLoader("datalinker", "templates"),
    undefined=jinja2.StrictUndefined,
    autoescape=True,
)
_TEMPLATES = Jinja2Templates(env=_environment)
"""FastAPI renderer for templated responses."""

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
async def get_index(
    *, logger: Annotated[BoundLogger, Depends(logger_dependency)]
) -> Index:
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
    logger: Annotated[BoundLogger, Depends(logger_dependency)],
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


async def cutout_url_dependency(
    *,
    id: str,
    discovery: Annotated[DiscoveryClient, Depends(discovery_dependency)],
) -> str | None:
    """Get the cutout URL for the provided object ID.

    This has to be kept separate from the links endpoint because the latter
    must be sync due to the Butler client's lack of async support.
    """
    try:
        parsed_uri = Butler.parse_dataset_uri(id)
    except Exception:
        return None
    label = parsed_uri.label
    return await discovery.url_for_data(
        "cutout", label, version="soda-sync-1.0"
    )


@external_router.get(
    "/links",
    responses={404: {"description": "Specified identifier not found"}},
    summary="DataLink links for object",
)
def links(
    *,
    request: Request,
    id: Annotated[
        str,
        Query(
            title="Object ID",
            examples=[
                "butler://dp02/58f56d2e-cfd8-44e7-a343-20ebdc1f4127",
                "ivo://org.rubinobs/usdac/dp1?"
                "repo=dp1&id=58f56d2e-cfd8-44e7-a343-20ebdc1f4127",
            ],
            pattern="^(butler|ivo)://.+$",
        ),
    ],
    responseformat: Annotated[
        Literal["votable", "application/x-votable+xml"],
        Query(title="Response format"),
    ] = "application/x-votable+xml",
    logger: Annotated[BoundLogger, Depends(logger_dependency)],
    cutout_url: Annotated[str | None, Depends(cutout_url_dependency)],
    delegated_token: Annotated[str, Depends(auth_delegated_token_dependency)],
) -> Response:
    bound_factory = _BUTLER_FACTORY.bind(access_token=delegated_token)
    try:
        dataset_result = Butler.get_dataset_from_uri(id, factory=bound_factory)
        logger.debug(
            "Retrieving object from Butler",
            butler=str(dataset_result.butler),
            uuid=str(dataset_result.dataset),
        )
    except FileNotFoundError as e:
        # Invalid Butler labels will cause it to fall back to trying to
        # read a local Butler config.
        logger.warning("Butler repository does not exist")
        raise HTTPException(
            status_code=404,
            detail=[
                {
                    "loc": ["query", "id"],
                    "msg": f"Repository for {id} does not exist",
                    "type": "not_found",
                }
            ],
        ) from e
    except ValueError as e:
        # Bad or missing UUID in URI.
        logger.warning("Butler URI has malformed or missing UUID")
        raise HTTPException(
            status_code=422,
            detail=[
                {
                    "loc": ["query", "id"],
                    "msg": f"Unable to extract valid dataset ID from {id}",
                    "type": "not_found",
                }
            ],
        ) from e

    ref = dataset_result.dataset
    butler = dataset_result.butler

    if not ref:
        logger.warning("Dataset does not exist", label=str(butler), id=id)
        raise HTTPException(
            status_code=404,
            detail=[
                {
                    "loc": ["query", "id"],
                    "msg": f"Dataset {id} does not exist",
                    "type": "not_found",
                }
            ],
        )
    # This returns lsst.resources.ResourcePath.
    image_uri = butler.getURI(ref)
    logger.debug("Got image URI from Butler", image_uri=image_uri)
    if image_uri.scheme not in ("https", "http"):
        logger.error("Image URL from Butler not signed", image_uri=image_uri)
        raise HTTPException(
            status_code=500,
            detail=[
                {
                    "msg": "Image URL from Butler server was not signed",
                    "type": "invalid_butler_response",
                }
            ],
        )

    lifetime = int(config.links_lifetime.total_seconds())
    return _TEMPLATES.TemplateResponse(
        request,
        "links.xml",
        {
            "cutout": ref.datasetType.name != "raw" and cutout_url,
            "id": id,
            "image_url": str(image_uri),
            "image_size": image_uri.size(),
            "cutout_sync_url": cutout_url,
        },
        headers={"Cache-Control": f"max-age={lifetime}"},
        media_type="application/x-votable+xml",
    )
