"""Handlers for the app's external root, ``/datalinker/``."""

from datetime import timedelta
from email.message import Message
from importlib.metadata import metadata
from pathlib import Path
from typing import Dict, Literal, Optional, cast
from urllib.parse import urlencode, urlparse
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from google.cloud import storage
from lsst.daf import butler
from safir.dependencies.logger import logger_dependency
from safir.metadata import Metadata, get_project_url
from structlog.stdlib import BoundLogger

from ..config import config
from ..constants import (
    ADQL_COMPOUND_TABLE_REGEX,
    ADQL_FOREIGN_COLUMN_REGEX,
    ADQL_IDENTIFIER_REGEX,
)
from ..models import Band, Detail, Index

external_router = APIRouter()
"""FastAPI router for all external handlers."""

_BUTLER_CACHE: Dict[str, butler.Butler] = {}
"""Cache of Butlers by label."""

_TEMPLATES = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "templates")
)
"""FastAPI renderer for templated responses."""

__all__ = ["external_router"]


def _get_butler(label: str) -> butler.Butler:
    """Retrieve a cached Butler object or create a new one.

    Don't bother adding a lock in, it's fine to make a couple if there's a
    race condition, they'll get cleaned up.

    Parameters
    ----------
    label : `str`
        Label identifying the Butler repository.

    Returns
    -------
    butler : `lsst.daf.butler.Butler`
        Corresponding Butler.
    """
    global _BUTLER_CACHE

    if label not in _BUTLER_CACHE:
        _BUTLER_CACHE[label] = butler.Butler(label)
    return _BUTLER_CACHE[label]


def _create_tap_redirect(sql: str, logger: BoundLogger) -> str:
    """Construct the URL for a redirect to TAP to run the provided SQL.

    Parameters
    ----------
    sql : `str`
        SQL to run, with all parameters already filled in.
    logger : `structlog.stdlib.BoundLogger`
        Logger to log the redirect action.

    Returns
    -------
    url : `str`
        URL to execute a synchronous TAP query.
    """
    params = {"LANG": "ADQL", "REQUEST": "doQuery", "QUERY": sql}
    url = "/api/tap/sync?" + urlencode(params)
    logger.info(f"Redirecting to {url}")
    return url


@external_router.get(
    "/",
    response_model=Index,
    response_model_exclude_none=True,
    summary="Application metadata",
)
async def get_index(
    logger: BoundLogger = Depends(logger_dependency),
) -> Index:
    """GET ``/datalinker/`` (the app's external root).

    By convention, the root of the external API includes a field called
    ``metadata`` that provides the same Safir-generated metadata as the
    internal root endpoint.
    """
    pkg_metadata = cast(Message, metadata("datalinker"))
    return Index(
        metadata=Metadata(
            name="datalinker",
            version=pkg_metadata["Version"],
            description=pkg_metadata["Summary"],
            repository_url=get_project_url(pkg_metadata, "Source"),
            documentation_url=get_project_url(pkg_metadata, "Homepage"),
        )
    )


@external_router.get("/cone_search", response_class=RedirectResponse)
async def cone_search(
    table: str = Query(
        ..., title="Table name", regex=ADQL_COMPOUND_TABLE_REGEX
    ),
    ra_col: str = Query(
        ..., title="Column for ra", regex=ADQL_IDENTIFIER_REGEX
    ),
    dec_col: str = Query(
        ..., title="Column for dec", regex=ADQL_IDENTIFIER_REGEX
    ),
    ra_val: float = Query(..., title="ra value"),
    dec_val: float = Query(..., title="dec value"),
    radius: float = Query(..., title="Radius of cone"),
    logger: BoundLogger = Depends(logger_dependency),
) -> str:
    sql = (
        f"SELECT * FROM {table} WHERE"
        f" CONTAINS(POINT('ICRS',{ra_col},{dec_col}),"
        f"CIRCLE('ICRS',{ra_val},{dec_val},{radius})"
        ")=1"
    )
    return _create_tap_redirect(sql, logger)


@external_router.get("/timeseries", response_class=RedirectResponse)
async def timeseries(
    id: int = Query(..., title="Object identifier"),
    table: str = Query(
        ..., title="Table name", regex=ADQL_COMPOUND_TABLE_REGEX
    ),
    id_column: str = Query(
        ..., title="Object ID column", regex=ADQL_IDENTIFIER_REGEX
    ),
    band_column: str = Query(
        "band", title="Band column", regex=ADQL_IDENTIFIER_REGEX
    ),
    band: Band = Query(Band.all, title="Abstract filter band"),
    detail: Detail = Query(Detail.full, title="Column detail"),
    join_time_column: Optional[str] = Query(
        None,
        title="Foreign column for time variable",
        regex=ADQL_FOREIGN_COLUMN_REGEX,
    ),
    logger: BoundLogger = Depends(logger_dependency),
) -> str:
    if detail == Detail.minimal:
        # TODO: get from sdm-schemas
        columns = "s.*"
    elif detail == Detail.principal:
        # TODO: get from sdm-schemas
        columns = "s.*"
    elif detail == Detail.full:
        columns = "s.*"

    # Some time series tables are normalized and don't have a time in them.
    # In those cases we have to join with another table on ccdVisitId.
    if join_time_column:
        join_table, time_column = join_time_column.rsplit(".", 1)
        sql = (
            f"SELECT t.{time_column},{columns} FROM {table} AS s"
            f" JOIN {join_table} AS t ON s.ccdVisitId = t.ccdVisitId"
        )
    else:
        sql = f"SELECT {columns} FROM {table} AS s"

    sql += f" WHERE s.{id_column} = {id}"
    if band != Band.all:
        sql += f" AND s.{band_column} = '{band}'"

    return _create_tap_redirect(sql, logger)


@external_router.get(
    "/links",
    responses={404: {"description": "Specified identifier not found"}},
    summary="DataLink links for object",
)
def links(
    request: Request,
    id: str = Query(
        ...,
        title="Object ID",
        example="butler://dp02/58f56d2e-cfd8-44e7-a343-20ebdc1f4127",
        regex="^butler://[^/]+/[a-f0-9-]+$",
    ),
    responseformat: Literal["votable", "application/x-votable+xml"] = Query(
        "application/x-votable+xml", title="Response format"
    ),
    logger: BoundLogger = Depends(logger_dependency),
) -> Response:
    butler_uri = urlparse(id)
    label = butler_uri.netloc
    uuid = butler_uri.path[1:]
    logger.debug("Retrieving object from Butler", label=label, uuid=uuid)

    # Invalid Butler labels will cause the Butler constructor to raise a
    # FileNotFoundError.  Hopefully this will stay consistent, since we want
    # other errors (like problems reaching PostgreSQL) to return 500.
    try:
        butler = _get_butler(label)
    except FileNotFoundError:
        logger.warning("Butler repository does not exist", label=label)
        raise HTTPException(
            status_code=404,
            detail=[
                {
                    "loc": ["query", "id"],
                    "msg": f"Repository for {id} does not exist",
                    "type": "not_found",
                }
            ],
        )

    # This returns lsst.resources.ResourcePath.
    ref = butler.registry.getDataset(UUID(uuid))
    if not ref:
        logger.warning("Dataset does not exist", label=label, id=id)
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
    image_uri = butler.datastore.getURI(ref)
    logger.debug("Got image URI from Butler", image_uri=image_uri)

    # Generate signed URL.
    image_uri_parts = urlparse(str(image_uri))
    storage_client = storage.Client()
    bucket = storage_client.bucket(image_uri_parts.netloc)
    blob = bucket.blob(image_uri_parts.path[1:])
    signed_url = blob.generate_signed_url(
        version="v4",
        # This URL is valid for one hour.
        expiration=timedelta(hours=1),
        # Allow only GET requests using this URL.
        method="GET",
    )

    return _TEMPLATES.TemplateResponse(
        "links.xml",
        {
            "cutout": ref.datasetType.name != "raw",
            "id": id,
            "image_url": signed_url,
            "image_size": image_uri.size(),
            "cutout_url": config.cutout_url,
            "request": request,
        },
        media_type="application/x-votable+xml",
    )
