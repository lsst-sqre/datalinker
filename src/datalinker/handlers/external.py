"""Handlers for the app's external root, ``/datalinker/``."""

from datetime import timedelta
from email.message import Message
from importlib.metadata import metadata
from pathlib import Path
from typing import Literal, Optional, cast
from urllib.parse import urlencode, urlparse
from uuid import UUID

from boto3 import client
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from google.cloud import storage
from lsst.daf.butler import LabeledButlerFactory
from safir.dependencies.gafaelfawr import auth_delegated_token_dependency
from safir.dependencies.logger import logger_dependency
from safir.metadata import Metadata, get_project_url
from structlog.stdlib import BoundLogger

from ..config import config
from ..constants import (
    ADQL_COMPOUND_TABLE_REGEX,
    ADQL_FOREIGN_COLUMN_REGEX,
    ADQL_IDENTIFIER_REGEX,
)
from ..dependencies.tap import TAPMetadata, tap_metadata_dependency
from ..models import Band, Detail, Index

external_router = APIRouter()
"""FastAPI router for all external handlers."""

_BUTLER_FACTORY = LabeledButlerFactory(config.butler_repositories)
"""Factory for creating Butlers from a label and Gafaelfawr token."""

_TEMPLATES = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "templates")
)
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
        ..., title="Table name", pattern=ADQL_COMPOUND_TABLE_REGEX
    ),
    ra_col: str = Query(
        ..., title="Column for ra", pattern=ADQL_IDENTIFIER_REGEX
    ),
    dec_col: str = Query(
        ..., title="Column for dec", pattern=ADQL_IDENTIFIER_REGEX
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
        ..., title="Table name", pattern=ADQL_COMPOUND_TABLE_REGEX
    ),
    id_column: str = Query(
        ..., title="Object ID column", pattern=ADQL_IDENTIFIER_REGEX
    ),
    band_column: str = Query(
        "band", title="Band column", pattern=ADQL_IDENTIFIER_REGEX
    ),
    band: Band = Query(Band.all, title="Abstract filter band"),
    detail: Detail = Query(Detail.full, title="Column detail"),
    join_time_column: Optional[str] = Query(
        None,
        title="Foreign column for time variable",
        pattern=ADQL_FOREIGN_COLUMN_REGEX,
    ),
    tap_metadata: TAPMetadata = Depends(tap_metadata_dependency),
    logger: BoundLogger = Depends(logger_dependency),
) -> str:
    columns = _get_tap_columns(table, detail, tap_metadata)

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
        sql += f" AND s.{band_column} = '{band.value}'"

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
        examples=["butler://dp02/58f56d2e-cfd8-44e7-a343-20ebdc1f4127"],
        pattern="^butler://[^/]+/[a-f0-9-]+$",
    ),
    responseformat: Literal["votable", "application/x-votable+xml"] = Query(
        "application/x-votable+xml", title="Response format"
    ),
    logger: BoundLogger = Depends(logger_dependency),
    delegated_token: str = Depends(auth_delegated_token_dependency),
) -> Response:
    butler_uri = urlparse(id)
    label = butler_uri.netloc
    uuid = butler_uri.path[1:]
    logger.debug("Retrieving object from Butler", label=label, uuid=uuid)

    # Invalid Butler labels will cause the Butler factory to raise a KeyError.
    # We want other errors (like problems reaching PostgreSQL) to return 500.
    try:
        butler = _BUTLER_FACTORY.create_butler(
            label=label, access_token=delegated_token
        )
    except KeyError:
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
    ref = butler.get_dataset(UUID(uuid))

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
    image_uri = butler.getURI(ref)
    logger.debug("Got image URI from Butler", image_uri=image_uri)

    expires_in = timedelta(hours=1)

    if image_uri.scheme in ("https", "http"):
        # Butler server returns signed URLs directly, so no additional signing
        # is required.
        image_url = str(image_uri)
    elif config.storage_backend == "GCS":
        # If we are using a direct connection to the Butler database, the URIs
        # will be S3 or GCS URIs that need to be signed.
        image_url = _upload_to_gcs(str(image_uri), expires_in)
    elif config.storage_backend == "S3":
        image_url = _upload_to_S3(str(image_uri), expires_in)
    else:
        raise Exception(
            f"Config error: {config.storage_backend} is not a valid backend."
        )

    return _TEMPLATES.TemplateResponse(
        request,
        "links.xml",
        {
            "cutout": ref.datasetType.name != "raw",
            "id": id,
            "image_url": image_url,
            "image_size": image_uri.size(),
            "cutout_url": config.cutout_url,
        },
        media_type="application/x-votable+xml",
    )


def _upload_to_gcs(image_uri: str, expiry: timedelta) -> str:
    """Use GCS to upload a file and get a signed URL.

    Parameters
    ----------
    image_uri
        The URI of the file
    expiry
        Time that the URL will be valid

    Returns
    -------
    str
        The signed URL
    """
    image_uri_parts = urlparse(image_uri)
    storage_client = storage.Client()
    bucket = storage_client.bucket(image_uri_parts.netloc)
    blob = bucket.blob(image_uri_parts.path[1:])
    signed_url = blob.generate_signed_url(
        version="v4",
        # This URL is valid for one hour.
        expiration=expiry,
        # Allow only GET requests using this URL.
        method="GET",
    )

    return signed_url


def _upload_to_S3(image_uri: str, expiry: timedelta) -> str:
    """Use S3 to upload a file and get a signed URL.

    Parameters
    ----------
    image_uri
        The URI of the file
    expiry
        Time that the URL will be valid

    Returns
    -------
    str
        The signed URL
    """
    image_uri_parts = urlparse(image_uri)
    bucket = image_uri_parts.netloc
    key = image_uri_parts.path[1:]

    s3_client = client(
        "s3", endpoint_url=config.s3_endpoint_url, region_name="us-east-1"
    )

    signed_url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expiry.total_seconds(),
    )

    return signed_url
