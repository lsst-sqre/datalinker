"""Handlers for the app's external root, ``/datalinker/``."""

from datetime import timedelta
from pathlib import Path
from typing import Dict, Literal
from urllib.parse import urlencode, urlparse
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from google.cloud import storage
from lsst.daf import butler
from safir.dependencies.logger import logger_dependency
from safir.metadata import get_metadata
from structlog.stdlib import BoundLogger

from ..config import config
from ..models import Index

external_router = APIRouter()
"""FastAPI router for all external handlers."""

_BUTLER_CACHE: Dict[str, butler.Butler] = {}
"""Cache of Butlers by label."""

_TEMPLATES = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "templates")
)
"""FastAPI renderer for templated responses."""

__all__ = ["get_index", "external_router"]


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
    metadata = get_metadata(
        package_name="datalinker",
        application_name=config.name,
    )
    return Index(metadata=metadata)


@external_router.get("/cone_search", response_class=RedirectResponse)
async def cone_search(
    table: str = Query(..., title="Table name", regex="^[a-zA-Z0-9_]+$"),
    ra_col: str = Query(..., title="Column for ra", regex="^[a-zA-Z0-9_]+$"),
    dec_col: str = Query(..., title="Column for dec", regex="^[a-zA-Z0-9_]+$"),
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
    params = {"LANG": "ADQL", "REQUEST": "doQuery", "QUERY": sql}
    url = "/api/tap/sync?" + urlencode(params)
    logger.info(f"Redirecting to {url}")
    return url


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
